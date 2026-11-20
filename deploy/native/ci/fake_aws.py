#!/usr/bin/env python3
"""A fake SSM and S3 for the CI job that imitates the VM. Not AWS, and not a test of AWS: it speaks just enough of the
two wire protocols for boto3 (SSM JSON 1.1: GetParameter/GetParameters; S3 path-style PutObject/GetObject/ListObjectsV2)
so the VM's own tools run unchanged. Every request is appended to /state/requests.log (method, path, target) so a test
can check what the VM sent where. Nothing here is a real secret.

    python3 fake_aws.py PORT PARAMS.json STATE_DIR
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.parse

PORT, PARAMS_PATH, STATE = int(sys.argv[1]), sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(STATE, "s3"), exist_ok=True)


def params():
    with open(PARAMS_PATH) as f:                 # re-read every time: a test changes the parameters while this runs
        return json.load(f)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _log(self):
        with open(os.path.join(STATE, "requests.log"), "a") as f:
            f.write(f"{self.command} {self.path} {self.headers.get('X-Amz-Target', '')}\n")

    def _send(self, code, body=b"", ctype="application/octet-stream", headers=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":     # boto3 may stream with aws-chunked
            out = b""
            while True:
                size = int(self.rfile.readline().split(b";")[0], 16)
                if size == 0:
                    self.rfile.readline()
                    return out
                out += self.rfile.read(size)
                self.rfile.readline()
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_POST(self):
        self._log()
        data = self._body()
        target = self.headers.get("X-Amz-Target", "")
        if target.startswith("AmazonSSM."):
            req = json.loads(data or b"{}")
            op = target.split(".", 1)[1]
            names = req.get("Names") or ([req["Name"]] if "Name" in req else [])
            PARAMS = params()
            found = [{"Name": n, "Type": "SecureString", "Value": PARAMS[n], "Version": 1} for n in names if n in PARAMS]
            if op == "GetParameters":
                body = {"Parameters": found, "InvalidParameters": [n for n in names if n not in PARAMS]}
            elif op == "GetParameter" and found:
                body = {"Parameter": found[0]}
            else:
                return self._send(400, json.dumps({"__type": "ParameterNotFound", "message": "no"}).encode(), "application/x-amz-json-1.1")
            return self._send(200, json.dumps(body).encode(), "application/x-amz-json-1.1")
        self._send(400, b"unsupported")

    def _s3_path(self):
        p = urllib.parse.urlparse(self.path)
        key = urllib.parse.unquote(p.path.lstrip("/"))
        if ".." in key.split("/"):
            return None, p
        return os.path.join(STATE, "s3", key), p

    def do_PUT(self):
        self._log()
        path, _ = self._s3_path()
        data = self._body()
        if not path:
            return self._send(400)
        key = urllib.parse.unquote(urllib.parse.urlparse(self.path).path.lstrip("/")).split("/", 1)[-1]
        if key.startswith(("central/", "households/")):          # what the bucket policy does (infra/treeline_infra/foundation.py)
            if self.headers.get("If-None-Match") != "*":
                return self._send(403, b"<Error><Code>AccessDenied</Code></Error>", "application/xml")
            if os.path.exists(path):
                return self._send(412, b"<Error><Code>PreconditionFailed</Code></Error>", "application/xml")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        self._send(200, b"", headers=[("ETag", '"fake"')])

    def do_GET(self):
        self._log()
        if self.path.startswith("/ping/"):                           # a stand-in for the dead-man monitor
            return self._send(200, b"OK")
        if self.path.startswith("/releases/"):                      # a stand-in for GitHub Releases (install.sh --ci --release-base)
            f = os.path.normpath(os.path.join(STATE, self.path.lstrip("/").split("?")[0]))
            if f.startswith(os.path.join(STATE, "releases") + os.sep) and os.path.isfile(f):
                return self._send(200, open(f, "rb").read())
            return self._send(404, b"not found")
        path, p = self._s3_path()
        q = urllib.parse.parse_qs(p.query)
        if path and "list-type" in q:
            bucket = p.path.strip("/").split("/")[0]
            prefix = q.get("prefix", [""])[0]
            root = os.path.join(STATE, "s3", bucket)
            keys = []
            for d, _, files in os.walk(root):
                for fn in files:
                    k = os.path.relpath(os.path.join(d, fn), root)
                    if k.startswith(prefix):
                        keys.append(k)
            xml = "<ListBucketResult>" + "".join(f"<Contents><Key>{k}</Key></Contents>" for k in sorted(keys)) + \
                  f"<KeyCount>{len(keys)}</KeyCount><IsTruncated>false</IsTruncated></ListBucketResult>"
            return self._send(200, xml.encode(), "application/xml")
        if path and os.path.isfile(path):
            return self._send(200, open(path, "rb").read())
        self._send(404, b"<Error><Code>NoSuchKey</Code></Error>", "application/xml")

    do_HEAD = do_GET


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


Server(("0.0.0.0", PORT), Handler).serve_forever()
