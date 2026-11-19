"""Real calls between tablet softphones, through Asterisk, in headless browsers.

Needs the Docker stack:  docker compose up -d --build && docker compose run --rm webtests

Each tablet is a browser page with a fake microphone. Calls go over WebRTC
(DTLS-SRTP) to Asterisk, through the control app's rules, and back out.
"""

import json
import os
import sys
import time
import urllib.error
import ssl
import urllib.request

from playwright.sync_api import sync_playwright

# BASE=https://127.0.0.1:8443 runs the same calls through the dev HTTPS proxy (deploy/Caddyfile.dev),
# whose certificate comes from its own authority, so certificate errors are ignored here.
BASE = os.environ.get("BASE", "http://127.0.0.1:8080")
TLS = ssl._create_unverified_context() if BASE.startswith("https") else None
errors, count = [], [0]


def check(cond, what, detail=""):
    count[0] += 1
    print(("ok   " if cond else "FAIL ") + what + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    if not cond:
        errors.append(what)


def api(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body or {}).encode() if method != "GET" else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15, context=TLS) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read()[:200]}")


class Family:
    def __init__(self, tag, name):
        self.email = f"{tag}-{int(time.time())}@example.com"
        code = api("POST", "/api/auth/request", {"email": self.email})["dev_code"]
        self.token = api("POST", "/api/auth/verify", {"email": self.email, "code": code})["token"]
        self.house = api("POST", "/api/treehouse", {"name": name, "ack_911": True, "consent": True}, self.token)["treehouse"]
        # Quiet hours would make results depend on the time of day.
        api("PATCH", "/api/treehouse", {"quiet": {"enabled": False}}, self.token)
        self.number = self.house["number"]

    def call(self, method, path, body=None):
        return api(method, path, body, self.token)


def string_up(a, b):
    code = a.call("POST", "/api/ladder-codes")["code"]
    s = b.call("POST", "/api/strings/redeem", {"code": code})
    a.call("POST", f"/api/strings/{s['id']}/approve")


class Tablet:
    """One browser page running the Treeline phone, paired to a family."""

    def __init__(self, browser, family, name):
        self.family, self.name = family, name
        self.ctx = browser.new_context(permissions=["microphone"], viewport={"width": 820, "height": 1100}, ignore_https_errors=True)
        self.page = self.ctx.new_page()
        self.page.on("pageerror", lambda e: errors.append(f"{name} page error: {e}"))
        self.page.goto(f"{BASE}/phone/?test=1")
        self.page.wait_for_selector(".ph-code")
        code = "".join(c for c in self.page.inner_text(".ph-code") if c.isdigit())
        family.call("POST", "/api/pair/claim", {"code": code, "name": name})
        self.page.wait_for_selector(".tl-rotary", timeout=20000)
        self.page.wait_for_function("() => window.__phone.S.registered === true", timeout=30000)
        self.page.wait_for_function("() => window.__phone.S.number", timeout=15000)

    def phase(self):
        return self.page.evaluate("() => window.__phone.S.phase")

    def wait_phase(self, phase, timeout=20000):
        try:
            self.page.wait_for_function("(p) => window.__phone.S.phase === p", arg=phase, timeout=timeout)
            return True
        except Exception:
            return False

    def tone(self):
        return self.page.evaluate("() => window.__phone.tones.playing()")

    def lift(self):
        self.page.evaluate("() => window.__phone.lift()")

    def dial(self, number):
        """Turn the dial once per digit, waiting for each to come back round like a person would."""
        for i, d in enumerate(number, 1):
            for _ in range(5):
                self.page.evaluate("(d) => window.__phone.dial(Number(d))", d)    # ignored while the wheel is still returning
                try:
                    self.page.wait_for_function("(n) => window.__phone.S.digits.length >= n || ['calling', 'talking', 'after', 'busy', 'sleep'].includes(window.__phone.S.phase)",
                                                arg=i, timeout=3500)
                    break
                except Exception:
                    continue
            time.sleep(0.2)

    def stats(self):
        return self.page.evaluate("() => window.__phone.stats()")

    def close(self):
        self.ctx.close()


def newest_call(family):
    calls = family.call("GET", "/api/calls?range=all")["calls"]
    return calls[0] if calls else None


def main():
    families = []
    try:
        run(families)
    finally:
        for f in families:                         # leave the dev database as we found it
            try:
                f.call("DELETE", "/api/treehouse", {"confirm": f.house["name"]})
            except Exception:
                pass
    if errors:
        print("\nPROBLEMS:")
        for e in dict.fromkeys(errors):
            print(" -", e)
        sys.exit(1)
    print(f"\nall {count[0]} checks passed")


def run(families):
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                          "--autoplay-policy=no-user-gesture-required"])
        alex, sam = Family("alex", "Alex's house"), Family("sam", "Sam's house")
        families += [alex, sam]
        string_up(alex, sam)
        a = Tablet(browser, alex, "Alex tablet")
        s = Tablet(browser, sam, "Sam tablet")
        check(a.page.evaluate("() => window.__phone.S.registered"), "both tablets register with Asterisk over WebSocket")

        # ---- dial tone on pickup
        s.lift()
        check(s.wait_phase("dialtone"), "lifting the handset gives a dial tone")
        check(s.tone() == "dial", "the dial tone is playing")

        # ---- a call: Sam dials Alex; Alex's tablet rings; Alex answers; audio flows both ways
        s.dial(alex.number)
        check(s.wait_phase("calling"), "four digits place the call")
        check(a.wait_phase("ringing"), "the called tablet rings")
        check(a.tone() == "bell", "it plays the bell")
        check(s.tone() == "ringback", "the caller hears ringback")
        # The room marks a ringing phone with `is-ringing` (the kit's own state; it styles the handset).
        ringing = "() => !!document.querySelector('.is-ringing')"
        check(a.page.evaluate(ringing), "a ringing phone is marked as ringing")
        a.lift()
        check(a.wait_phase("talking") and s.wait_phase("talking"), "answering connects both tablets")
        time.sleep(1.0)
        check(not a.page.evaluate(ringing), "and it stops ringing when it's answered")
        time.sleep(3)
        sa, ss = a.stats(), s.stats()
        check(sa and sa["rx"] > 1000 and sa["tx"] > 1000, "audio flows both ways (called side)", str(sa))
        check(ss and ss["rx"] > 1000 and ss["tx"] > 1000, "audio flows both ways (calling side)", str(ss))
        # Packets arriving isn't hearing them: the page's audio element must actually be playing (a browser can refuse to start it).
        playing = "() => { const e = document.getElementById('remote-audio'); return !!e.srcObject && !e.paused && e.currentTime > 0.5; }"

        def plays(tab, ms=8000):
            """Audio can lag the packets a little: wait for the element to be playing rather than reading it once."""
            try:
                tab.page.wait_for_function(playing, timeout=ms)
                return True
            except Exception:
                return False
        state = "() => { const e = document.getElementById('remote-audio'); return { src: !!e.srcObject, paused: e.paused, time: Math.round(e.currentTime * 10) / 10, ready: e.readyState, muted: e.muted, vol: e.volume, tracks: e.srcObject ? e.srcObject.getAudioTracks().map((t) => t.readyState + '/' + (t.muted ? 'muted' : 'live') + '/' + t.enabled) : null }; }"
        check(plays(a) and plays(s), "and both tablets are really playing what they receive, not just receiving it",
              f"callee {a.page.evaluate(state)} | caller {s.page.evaluate(state)}")

        # ---- someone else on the line joins mid-call
        s2 = Tablet(browser, sam, "Sam second tablet")
        time.sleep(1)
        s2.lift()
        check(s2.wait_phase("talking", 25000), "a second tablet on the same line joins the call in progress")
        s2.page.evaluate("() => window.__phone.lift()")        # hang up the extra one

        # ---- hang up: the other side gets a click, then dial tone
        s.lift()
        check(a.wait_phase("after", 15000) or a.wait_phase("dialtone", 15000), "when one side hangs up, the other hears the click")
        check(a.wait_phase("dialtone", 15000), "and then the dial tone comes back")
        gone = "() => !document.getElementById('remote-audio').srcObject"
        check(a.page.evaluate(gone) and s.page.evaluate(gone), "after the call neither tablet is left holding its audio, so the next call can't replay it")
        a.lift()                                               # put it back
        time.sleep(1)
        c = newest_call(alex)
        check(c and c["result"] == "connected" and c["talk_sec"] >= 3, "the call is in the audit as connected", str(c))
        detail = alex.call("GET", f"/api/calls/{c['id']}")
        kinds = [e["event"] for e in detail["events"]]
        check("joined" in kinds or "joined" in [e["event"] for e in sam.call("GET", f"/api/calls/{newest_call(sam)['id']}")["events"]],
              "the join is in the audit")

        # ---- a disconnected tablet is simply off: no ringing in, no calling out
        ah = alex.call("GET", "/api/handsets")["handsets"][0]["id"]
        alex.call("PATCH", f"/api/handsets/{ah}", {"disabled": True})
        a.lift()
        check(a.wait_phase("off", 15000), "a disconnected tablet says it's switched off on pickup")
        check(a.tone() == "fastbusy", "and plays fast busy")
        a.lift()
        s.lift()
        s.wait_phase("dialtone")
        s.dial(alex.number)
        s.wait_phase("after", 20000)
        check(newest_call(sam)["result"] == "offline", "calling a treehouse whose only phone is disconnected goes nowhere")
        s.lift()
        alex.call("PATCH", f"/api/handsets/{ah}", {"disabled": False})
        a.lift()
        check(a.wait_phase("dialtone", 15000), "reconnected, the tablet gives a dial tone again")
        a.lift()

        # ---- rules apply to tablets as they do to every phone
        s.lift()
        s.wait_phase("dialtone")
        s.dial("0199")
        heard, played = 0, False
        for _ in range(16):                                      # the tones and the message are real audio, and it plays
            st = s.stats()
            heard = max(heard, (st or {}).get("rx", 0))
            played = played or s.page.evaluate("() => { const e = document.getElementById('remote-audio'); return !!e.srcObject && !e.paused && e.currentTime > 0.5; }")
            if heard > 2000 and played:
                break
            time.sleep(0.3)
        check(heard > 2000, "the caller hears the three tones and the message", str(heard))
        check(played, "and the operator's message is really playing in the caller's browser, not just arriving")
        check(s.wait_phase("after", 20000) or s.wait_phase("dialtone", 20000), "an unknown number gets a message, then the line is free again")
        check(newest_call(sam)["result"] == "not_in_service", "unknown numbers are blocked and audited")
        s.lift()
        time.sleep(0.5)

        # ---- quiet hours: lifting the handset just gives fast busy
        sam.call("PATCH", "/api/treehouse", {"paused": True})
        time.sleep(0.3)
        s.page.evaluate("() => { window.__phone.S.line = 'idle'; }")
        s.lift()
        check(s.wait_phase("sleep", 15000), "a paused line says the phone is sleeping on pickup")
        check(s.tone() == "fastbusy", "and plays fast busy")
        s.lift()
        sam.call("PATCH", "/api/treehouse", {"paused": False})

        # ---- 911
        s.page.evaluate("() => { window.__phone.S.line = 'idle'; }")
        s.lift()
        s.wait_phase("dialtone")
        s.dial("911")
        check(s.wait_phase("after", 25000) or s.wait_phase("dialtone", 25000), "dialing 911 plays the message and ends")
        check(newest_call(sam)["result"] == "no_911", "911 is audited as not available")
        s.lift()

        # ---- "use this device as a phone": the parent app makes the account and the browser keeps it
        made = sam.call("POST", "/api/handsets", {"kind": "softphone", "name": "This device"})
        c = made["credentials"]
        dev = browser.new_context(permissions=["microphone"], ignore_https_errors=True)
        pg = dev.new_page()
        pg.goto(f"{BASE}/phone/?test=1")
        pg.evaluate("(c) => localStorage.setItem('treeline.phone', JSON.stringify(c))",
                    {"sip_user": c["sip_user"], "secret": c["secret"], "server": c["server"], "ws_url": c["ws_url"],
                     "realm": c["realm"], "handset_id": made["handset"]["id"]})
        pg.reload()
        pg.wait_for_selector(".tl-rotary", timeout=20000)
        pg.wait_for_function("() => window.__phone.S.registered === true", timeout=30000)
        check(pg.evaluate("() => window.__phone.S.registered === true"), "a browser given its sign-in by the parent app becomes a working phone")
        dev.close()

        # ---- removing a tablet drops it at once
        hs = sam.call("GET", "/api/handsets")["handsets"]
        for h in hs:
            sam.call("DELETE", f"/api/handsets/{h['id']}")
        time.sleep(1)
        a.lift()
        a.wait_phase("dialtone")
        a.dial(sam.number)
        time.sleep(4)
        check(newest_call(alex)["result"] == "offline", "calling a treehouse with no phones fails cleanly")
        a.lift()

        # ---- the removed tablet notices on its next pickup, and can be added again
        s.lift()
        try:
            s.page.wait_for_selector(".ph-code", timeout=20000)
            gone = True
        except Exception:
            gone = False
        check(gone and "removed" in s.page.inner_text("body"), "a removed tablet goes back to the pairing screen and says why")
        if gone:
            code = "".join(c for c in s.page.inner_text(".ph-code") if c.isdigit())
            sam.call("POST", "/api/pair/claim", {"code": code, "name": "Sam tablet again"})
            s.page.wait_for_selector(".tl-rotary", timeout=20000)
            s.page.wait_for_function("() => window.__phone.S.registered === true", timeout=30000)
            s.page.wait_for_function("() => window.__phone.S.number", timeout=15000)
            s.lift()
            check(s.wait_phase("dialtone"), "once added again it works, with no leftover state")
            s.lift()
        browser.close()


if __name__ == "__main__":
    main()
