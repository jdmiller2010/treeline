#!/usr/bin/env python3
"""A tiny SIP phone for the VM-imitation job, standard library only. It registers a handset with digest authentication over TLS,
and places a call that Treeline's dialplan hands to the controller, as a real phone adapter would:

    sip_probe.py --host app.treeline.test --cafile /shared/root.crt --user h1234 --secret S [--dial 0001] [--hold 20] [--bad-password]

It prints one JSON line: whether it registered, what the INVITE was answered with, and how long it held the call. Nothing here is
a SIP implementation; it knows exactly one dialog: REGISTER, INVITE (with an SDES crypto offer, as the production endpoints
require), ACK, BYE. The audio is never sent: what is under test is signalling, authentication, TLS, the hand-off to Stasis
and the controller, and that Asterisk negotiates SRTP.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import ssl
import sys
import time

REALM_DEFAULT = "treeline"


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def digest(user, secret, realm, nonce, method, uri, qop=None, nc="00000001", cnonce=None):
    ha1, ha2 = md5(f"{user}:{realm}:{secret}"), md5(f"{method}:{uri}")
    if qop:
        response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
        return (f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}", '
                f'algorithm=MD5, qop={qop}, nc={nc}, cnonce="{cnonce}"')
    return f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{md5(f"{ha1}:{nonce}:{ha2}")}", algorithm=MD5'


def parse_challenge(value):
    fields = dict(re.findall(r'(\w+)="?([^",]*)"?', value))
    return fields.get("realm", REALM_DEFAULT), fields["nonce"], ("auth" if "auth" in fields.get("qop", "") else None)


class Phone:
    def __init__(self, host, port, cafile, user, secret, server_name=None, timeout=15):
        raw = socket.create_connection((host, port), timeout=timeout)
        ctx = ssl.create_default_context(cafile=cafile)
        self.sock = ctx.wrap_socket(raw, server_hostname=server_name or host)
        self.sock.settimeout(timeout)
        self.host, self.user, self.secret = host, user, secret
        self.ip, self.port = self.sock.getsockname()[:2]
        self.buf = b""
        self.cseq = 0
        self.tag = os.urandom(5).hex()

    def read_message(self):
        while b"\r\n\r\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("the server closed the connection")
            self.buf += chunk
        head, _, rest = self.buf.partition(b"\r\n\r\n")
        m = re.search(rb"(?im)^(?:content-length|l)\s*:\s*(\d+)", head)
        n = int(m.group(1)) if m else 0
        while len(rest) < n:
            rest += self.sock.recv(65536)
        self.buf = rest[n:]
        lines = head.decode(errors="replace").split("\r\n")
        headers = {}
        for l in lines[1:]:
            k, _, v = l.partition(":")
            headers.setdefault(k.strip().lower(), []).append(v.strip())
        return {"start": lines[0], "headers": headers, "body": rest[:n].decode(errors="replace")}

    def final_response(self):
        while True:
            msg = self.read_message()
            m = re.match(r"SIP/2\.0 (\d+) ", msg["start"])
            if m and int(m.group(1)) >= 200:
                return int(m.group(1)), msg
            if not m:                       # a request from the server (OPTIONS qualify, BYE): answer it and keep waiting
                self.reply_ok(msg)

    def reply_ok(self, req):
        h = req["headers"]
        out = ["SIP/2.0 200 OK"] + [f"Via: {v}" for v in h.get("via", [])] + [f"From: {h['from'][0]}", f"To: {h['to'][0]}",
               f"Call-ID: {h['call-id'][0]}", f"CSeq: {h['cseq'][0]}", "Content-Length: 0", "", ""]
        self.sock.sendall("\r\n".join(out).encode())

    def send(self, method, uri, call_id, extra_headers, body="", to_tag=None, cseq_method=None):
        self.cseq += 1
        branch = "z9hG4bK" + os.urandom(6).hex()
        to = f"<sip:{self.user}@{self.host}>" if method == "REGISTER" else f"<{uri}>"
        if to_tag:
            to += f";tag={to_tag}"
        head = [f"{method} {uri} SIP/2.0", f"Via: SIP/2.0/TLS {self.ip}:{self.port};branch={branch};rport",
                "Max-Forwards: 70", f"From: <sip:{self.user}@{self.host}>;tag={self.tag}", f"To: {to}", f"Call-ID: {call_id}",
                f"CSeq: {self.cseq} {cseq_method or method}", f"Contact: <sip:{self.user}@{self.ip}:{self.port};transport=tls>",
                "User-Agent: treeline-ci-probe", *extra_headers, f"Content-Length: {len(body.encode())}", "", body]
        self.sock.sendall("\r\n".join(head).encode())

    def authed(self, method, uri, call_id, headers, body="", content_type=None, bad_password=False):
        """Send, answer one digest challenge, return (status, message)."""
        ct = [f"Content-Type: {content_type}"] if content_type else []
        self.send(method, uri, call_id, headers + ct, body)
        status, msg = self.final_response()
        if status not in (401, 407):
            return status, msg
        header = "www-authenticate" if status == 401 else "proxy-authenticate"
        realm, nonce, qop = parse_challenge(msg["headers"][header][0])
        secret = "not-the-password" if bad_password else self.secret
        cnonce = os.urandom(4).hex()
        auth = digest(self.user, secret, realm, nonce, method, uri, qop, cnonce=cnonce)
        self.send(method, uri, call_id, headers + ct + [("Authorization: " if status == 401 else "Proxy-Authorization: ") + auth], body)
        return self.final_response()

    def register(self, bad_password=False):
        status, _ = self.authed("REGISTER", f"sip:{self.host}", "reg-" + self.tag, ["Expires: 120"], bad_password=bad_password)
        return status

    def call(self, number, hold, bad_password=False, stop_file=None):
        """INVITE with an SDES offer, hold the call for `hold` seconds (or until `stop_file` exists), hang up. Returns (status, seconds held)."""
        key = base64.b64encode(os.urandom(30)).decode()
        sdp = "\r\n".join(["v=0", f"o=- 1 1 IN IP4 {self.ip}", "s=-", f"c=IN IP4 {self.ip}", "t=0 0",
                           "m=audio 40000 RTP/SAVP 0 8", "a=rtpmap:0 PCMU/8000", "a=rtpmap:8 PCMA/8000",
                           f"a=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:{key}", "a=sendrecv", ""])
        call_id = "call-" + self.tag
        uri = f"sip:{number}@{self.host}"
        status, msg = self.authed("INVITE", uri, call_id, [], sdp, "application/sdp", bad_password)
        if status != 200:
            return status, 0.0
        to_tag = re.search(r"tag=([^;>\s]+)", msg["headers"]["to"][0]).group(1)
        self.send("ACK", uri, call_id, [], to_tag=to_tag, cseq_method="ACK")
        self.cseq -= 1                      # ACK reuses the INVITE's number
        started, held = time.time(), 0.0
        self.sock.settimeout(1)
        while time.time() - started < hold and not (stop_file and os.path.exists(stop_file)):
            try:
                req = self.read_message()
                if not req["start"].startswith("SIP/2.0"):
                    self.reply_ok(req)
                    if req["start"].startswith("BYE"):
                        return 200, time.time() - started
            except socket.timeout:
                continue
        held = time.time() - started
        self.sock.settimeout(10)
        self.cseq += 1
        self.send("BYE", uri, call_id, [], to_tag=to_tag)
        try:
            self.final_response()
        except (socket.timeout, ConnectionError):
            pass
        return 200, held


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=5061)
    ap.add_argument("--cafile", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--secret", required=True)
    ap.add_argument("--dial")
    ap.add_argument("--hold", type=float, default=2)
    ap.add_argument("--bad-password", action="store_true")
    ap.add_argument("--stop-file", help="hang up as soon as this file exists (the caller decides how long the call lasts)")
    args = ap.parse_args(argv)
    out = {"registered": None, "invite": None, "held": 0.0}
    try:
        phone = Phone(args.host, args.port, args.cafile, args.user, args.secret)
        out["register"] = phone.register(args.bad_password)
        out["registered"] = out["register"] == 200
        if args.dial:
            out["invite"], out["held"] = phone.call(args.dial, args.hold, args.bad_password, args.stop_file)
    except (OSError, ssl.SSLError, ConnectionError, KeyError) as err:
        out["error"] = f"{type(err).__name__}: {err}"
    print(json.dumps(out), flush=True)
    return 0 if out.get("registered") and (not args.dial or out.get("invite") == 200) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
