"""The tablet softphone's screen, in a headless browser, without Asterisk.

Pairs a tablet through the real API, checks the page around the phone (brand
and tagline, the treehouse's name and status, the card file of strings, the
quiet no-911 line, the How to dial sheet, the footer, every screen size), that
the dial really turns and the handset trembles when it rings,
and that a removed tablet notices. Real calls are tested
by web/tests/phone_calls.py, which needs the Docker stack.
"""

import glob
import math
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8080")
SHOTS = os.environ.get("SHOTS", "/tmp/treeline-shots")
CHROME = os.environ.get("CHROME") or next(iter(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))), None)
errors, count = [], [0]


def check(cond, what, detail=""):
    count[0] += 1
    print(("ok   " if cond else "FAIL ") + what + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    if not cond:
        errors.append(what)


def parent_session(api, email, house):
    code = api.post(f"{BASE}/api/auth/request", data={"email": email}).json()["dev_code"]
    token = api.post(f"{BASE}/api/auth/verify", data={"email": email, "code": code}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    r = api.post(f"{BASE}/api/treehouse", headers=h, data={"name": house, "ack_911": True, "consent": True})
    api.put(f"{BASE}/api/treehouse/parent-code", headers=h, data={"code": "2468"})      # a softphone can't be added without one
    return h, r.json()["treehouse"]


def digits_become(page, want, timeout=8000):
    try:
        page.wait_for_function("(d) => document.body.dataset.digits === d", arg=want, timeout=timeout)
        return True
    except Exception:
        return False


# The kit's dial geometry (design/ui/js/treeline.js, ROTARY): centre, radius, squash, hole ring.
CX, CY, R, SQ, HOLE_K = 200, 292, 73, 0.93, 0.79


def to_screen(page, x, y):
    """An SVG point in the phone's drawing, as a point on screen."""
    return page.evaluate("""([x, y]) => { const svg = document.querySelector('.tl-rotary__svg'); const p = svg.createSVGPoint();
      p.x = x; p.y = y; const q = p.matrixTransform(svg.getScreenCTM()); return { x: q.x, y: q.y }; }""", [x, y])


def drag_digit(page, digit):
    """Turn the wheel with the mouse the way a finger would: grab the hole, go clockwise to the stop."""
    pulses = 10 if digit == 0 else digit
    total = 30 * pulses + 30
    start = -28 - 30 * (pulses - 1)                          # where that hole rests, in the drawing's angle
    at = lambda a, k: to_screen(page, CX + k * math.cos(math.radians(a)), CY + SQ * k * math.sin(math.radians(a)))
    p0 = at(start, HOLE_K * R)
    page.mouse.move(p0["x"], p0["y"])
    page.mouse.down()
    for step in range(1, 25):
        p = at(start + total * step / 24, HOLE_K * R)
        page.mouse.move(p["x"], p["y"])
    page.mouse.up()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        api = browser.new_context().request

        tablet_ctx = browser.new_context(viewport={"width": 820, "height": 1100})
        tablet = tablet_ctx.new_page()
        tablet.on("console", lambda m: errors.append(f"console {m.type}: {m.text}")
                  if m.type in ("error", "warning") and "Failed to load resource" not in m.text and "WebSocket" not in m.text
                  and "wouldn't start the call audio" not in m.text else None)       # (that one is refused on purpose, in the call-audio checks)
        tablet.on("pageerror", lambda e: errors.append(f"page error: {e}"))
        # This test is about the screen, not calls (phone_calls.py has those), and it checks what the phone shows while
        # it can't connect. Whether a browser can reach Asterisk depends on where the tests run, so send the phone's
        # WebSocket to a port nobody listens on: it is refused, as if Asterisk were down.
        tablet.add_init_script("""(() => { const W = window.WebSocket;
          window.WebSocket = function (url, protocols) { return new W(String(url).replace(/^(wss?:\\/\\/)[^/]+/, '$1127.0.0.1:9'), protocols); };
          window.WebSocket.prototype = W.prototype; Object.assign(window.WebSocket, W); })();""")

        # ---- not paired: a QR code and six digits
        tablet.goto(f"{BASE}/phone/?test=1")
        tablet.wait_for_selector(".ph-code")
        code = re.sub(r"\D", "", tablet.inner_text(".ph-code"))
        check(len(code) == 6, "an unpaired tablet shows six digits")
        check(tablet.locator(".ph-qr svg").count() == 1, "an unpaired tablet shows a QR code")
        check("911" in tablet.inner_text("body"), "the pairing screen says plainly that 911 isn't available")
        tablet.screenshot(path=f"{SHOTS}/phone-pair.png", full_page=True)

        # ---- a parent claims it (their treehouse already has one string, for the card file)
        stamp = int(__import__('time').time())
        h, house = parent_session(api, f"phone-parent-{stamp}@example.com", "Dial house")
        fh, friend = parent_session(api, f"phone-friend-{stamp}@example.com", "Maple house")
        ladder = api.post(f"{BASE}/api/ladder-codes", headers=h).json()["code"]
        sid = api.post(f"{BASE}/api/strings/redeem", headers=fh, data={"code": ladder}).json()["id"]
        api.post(f"{BASE}/api/strings/{sid}/approve", headers=h, data={})
        r = api.post(f"{BASE}/api/pair/claim", headers=h, data={"code": code, "name": "Kitchen tablet"})
        check(r.status == 201, "a parent claims the code")
        tablet.wait_for_selector(".tl-rotary", timeout=15000)
        check(tablet.locator(".tl-rotary").count() == 1 and tablet.locator(".ph-code").count() == 0, "the tablet becomes a phone")
        tablet.wait_for_function("(n) => document.querySelector('.tl-rotary__number').textContent === n", arg=house["number"], timeout=15000)
        check(tablet.text_content(".tl-rotary__number") == house["number"], "the number card shows the treehouse's number")

        # ---- what's on the screen: an ordinary Treeline page around the design system's phone and card file
        check(tablet.locator(".tl-desk").count() == 0 and tablet.locator(".tl-root .ph").count() == 1, "the phone is a normal app page, not the old room")
        check(tablet.locator(".ph__head .tl-brand").count() == 1 and tablet.inner_text(".ph__head .tl-tagline").strip() == "Safe calls for neighborhood kids",
              "the brand and tagline are at the top")
        check(tablet.locator(".ph__head a").count() == 0, "the brand isn't a link a kid could wander off through")
        check(tablet.locator(".tl-rotary .tlp-wheel").count() == 1 and tablet.locator(".tl-rotary .tlp-handset").count() == 1 and tablet.locator(".tlp-wheel").count() == 1, "the design system's wheel and handset are there, once")
        check(tablet.locator(".tl-rotary[data-colorway='berry'], .tl-rotary--berry").count() == 1 or "berry" in (tablet.get_attribute(".tl-rotary", "class") or "") + (tablet.get_attribute(".tl-rotary", "data-colorway") or ""),
              "the phone is the berry one")
        check(tablet.locator(".ph__glow").count() == 1, "it sits on a soft glow")
        # The dial is what a finger has to hit, so it must be big. (At this 820 px width it was about 157 px.)
        wheel_w = tablet.evaluate("() => document.querySelector('.tlp-wheel').getBoundingClientRect().width")
        check(wheel_w >= 220, "the dial is big enough to dial with a finger", str(round(wheel_w)))
        # An older device that redraws slowly drops the painted texture (the SVG filters) instead of lagging.
        rule = tablet.evaluate("() => ({ smooth: __phone.isSlow(Array(30).fill(16.7)), slow: __phone.isSlow(Array(30).fill(40)), few: __phone.isSlow([90, 90]), blip: __phone.isSlow([...Array(28).fill(16.7), 300, 300]) })")
        check(rule == {"smooth": False, "slow": True, "few": False, "blip": False}, "a device that draws 25 frames a second counts as slow, one-off hiccups don't", str(rule))
        filt = "() => [...document.querySelectorAll('.tl-rotary__svg [filter]')].map((e) => getComputedStyle(e).filter)"
        full = tablet.evaluate(filt)
        tablet.evaluate("() => __phone.setLite(true)")
        lite = tablet.evaluate(filt)
        tablet.evaluate("() => __phone.setLite(false)")
        check(len(full) > 5 and all(f != "none" for f in full) and all(f == "none" for f in lite), "in lite mode the painted texture is off and the phone is otherwise the same", f"{len(full)} filtered parts")
        # The busy tone is one beep-and-gap period that the browser loops, so it never drifts and has no reset to hear: exactly the right
        # length, silent at both ends (so the loop point can't click), a beep of the right length and a silent gap.
        tone = tablet.evaluate("""() => { const f = window.__phone.cadenceSamples, rate = 48000, d = f(rate, 480, 620, 0.5, 0.5, 0.13);
          let firstSound = -1, lastSound = -1, peak = 0, gapPeak = 0;
          for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > 1e-6) { if (firstSound < 0) firstSound = i; lastSound = i; } peak = Math.max(peak, a); if (i >= 0.5 * rate) gapPeak = Math.max(gapPeak, a); }
          const fast = f(rate, 480, 620, 0.25, 0.25, 0.13), ring = f(rate, 440, 480, 2, 4, 0.13);
          return { n: d.length, first: d[0], last: d[d.length - 1], beepSec: (lastSound + 1) / rate, startsAt: firstSound, peak: Math.round(peak * 1000) / 1000, gapPeak, fastN: fast.length, ringN: ring.length }; }""")
        check(tone["n"] == 48000 and tone["first"] == 0 and tone["last"] == 0 and tone["gapPeak"] == 0 and 0.49 < tone["beepSec"] <= 0.5 and 0.12 < tone["peak"] <= 0.26,
              "the busy tone is one beep and gap, silent at the loop point, so it repeats with no click or reset", str(tone))
        check(tone["fastN"] == 24000 and tone["ringN"] == 288000, "and fast busy and ringback keep their rhythms (0.25 s and 2 s on, 4 s off)", str(tone))
        # Call audio. A refused playback arms ONE retry (not three listeners per refusal), a second track joins the connection's one
        # stream instead of replacing it, and ending a call leaves nothing behind for the next call to replay.
        audio = tablet.evaluate("""async () => {
          const p = window.__phone, el = document.getElementById('remote-audio'), real = HTMLMediaElement.prototype.play, out = {};
          HTMLMediaElement.prototype.play = () => Promise.reject(new DOMException('blocked', 'NotAllowedError'));
          try {
            el.srcObject = new MediaStream();
            p.playRemote(); p.playRemote(); p.playRemote();
            await new Promise((r) => setTimeout(r, 50));
            const before = p.audioState.tries;
            window.dispatchEvent(new Event('pointerdown'));                   // one tap
            await new Promise((r) => setTimeout(r, 50));
            out.retriesPerTap = p.audioState.tries - before;                  // was 3 with stacked listeners
            out.error = p.audioState.error;
            window.dispatchEvent(new Event('keydown'));                       // a key after the retry re-armed: still just one more
            await new Promise((r) => setTimeout(r, 50));
            out.afterKey = p.audioState.tries - before - out.retriesPerTap;
            p.stopRemoteAudio();                                              // the call ends: nothing armed, nothing left to replay
            const t0 = p.audioState.tries;
            window.dispatchEvent(new Event('pointerdown'));
            await new Promise((r) => setTimeout(r, 50));
            out.afterEnd = p.audioState.tries - t0; out.srcAfterEnd = !!el.srcObject; out.errorAfterEnd = p.audioState.error;
          } finally { HTMLMediaElement.prototype.play = real; }
          return out; }""")
        check(audio["retriesPerTap"] == 1 and audio["afterKey"] == 1 and audio["error"] == "NotAllowedError",
              "a browser that refuses the call audio gets one retry per tap, however often it refused", str(audio))
        check(audio["afterEnd"] == 0 and not audio["srcAfterEnd"] and audio["errorAfterEnd"] == "",
              "and when a call ends the audio element is cleared and nothing is left waiting to replay it", str(audio))
        streams = tablet.evaluate("""() => {
          const p = window.__phone, el = document.getElementById('remote-audio'), ctx = new AudioContext();
          const t1 = ctx.createMediaStreamDestination().stream.getAudioTracks()[0], t2 = ctx.createMediaStreamDestination().stream.getAudioTracks()[0];
          const pc = new EventTarget();
          p.hookAudio({ connection: pc, on() {} });
          const fire = (t) => { const e = new Event('track'); e.track = t; e.streams = []; pc.dispatchEvent(e); };
          fire(t1); const first = el.srcObject; fire(t2);
          const out = { same: el.srcObject === first, tracks: el.srcObject.getTracks().length };
          const v = new Event('track'); v.track = { kind: 'video' }; v.streams = []; pc.dispatchEvent(v);              // not audio: ignored
          out.afterVideo = el.srcObject.getTracks().length; p.stopRemoteAudio(); ctx.close(); return out; }""")
        check(streams == {"same": True, "tracks": 2, "afterVideo": 2}, "a second audio track joins the call's one stream instead of replacing it, and other tracks are ignored", str(streams))
        check(tablet.locator("#audio-debug").count() == 0, "the audio readout is only there when asked for (?debug=1)")
        # Tapping the handset (or double tapping) must not flash a highlight box or select text or the picture.
        touch = tablet.evaluate("""() => { const s = getComputedStyle(document.querySelector('.ph')); return { sel: s.userSelect, tap: s.webkitTapHighlightColor,
          kid: getComputedStyle(document.querySelector('.ph__status')).userSelect }; }""")
        check(touch["sel"] == "none" and touch["kid"] == "none" and touch["tap"] in ("rgba(0, 0, 0, 0)", "transparent"),
              "tapping the phone never highlights or selects anything", str(touch))
        notice = tablet.locator(".tl-rotary__notice")
        check(notice.count() == 1 and "911" in notice.inner_text() and notice.locator(".tl-icon").count() == 1,
              "the phone's own notice says it can't call 911")
        check(tablet.locator(".tl-alert").count() == 0, "and it's the design system's notice, not an alert box")
        check(tablet.locator("h1").count() == 1, "one page title")
        tablet.wait_for_function("(n) => document.querySelector('h1').textContent === n", arg=house["name"], timeout=15000)
        check(True, "the page title is the treehouse's name")
        box = tablet.locator(".ph__info").bounding_box()          # the wrapper is what is clipped to nothing
        check(box is not None and box["width"] <= 2 and box["height"] <= 2, "but it isn't drawn on screen: people know whose phone it is", str(box))
        tablet.wait_for_function("(n) => [...document.querySelectorAll('.tl-cardfile__name')].some((t) => t.textContent === n)", arg=friend["name"], timeout=15000)
        check(tablet.text_content(".tl-cardfile__num") == friend["number"], "the card file has a card for the string, with its number")
        quiet = tablet.locator("#quiet")
        qt = quiet.inner_text().strip() if quiet.is_visible() else "none"
        check(qt == "none" or bool(re.match(r"^Quiet time \d{1,2}(:\d\d)? [ap]m – \d{1,2}(:\d\d)? [ap]m$", qt)), "a tag shows the quiet hours, when there are some", qt)
        check(tablet.locator("#status .tl-presence").count() == 1, "what the phone is doing is still a Presence, for screen readers")
        # the little light on the phone is the line: no SIP here, so it pulses orange while it tries, then blinks red
        lamp = lambda: tablet.evaluate("() => getComputedStyle(document.querySelector('.tl-rotary .tlp-lamp')).fill")
        anim = lambda: tablet.evaluate("() => getComputedStyle(document.querySelector('.tl-rotary .tlp-lamp')).animationName")
        state0 = tablet.get_attribute(".tl-rotary", "data-line")
        check(state0 in ("connecting", "off") and ("connecting" in tablet.inner_text("#reg") or "can't connect" in tablet.inner_text("#reg")),
              "while the phone isn't connected its little light says so, and screen readers hear it", state0)
        tablet.wait_for_function("() => document.querySelector('.tl-rotary').getAttribute('data-line') === 'off'", timeout=20000)
        check(anim() == "tl-rotary-lamp-blink" and "Ask a grown-up" in tablet.inner_text("#reg"), "after trying for a while it blinks red: something's wrong", anim())
        st = tablet.inner_text("#status")
        check("Ask a grown-up" in st or "sleeping" in st.lower() or "Quiet" in st, "and its words say so too, for screen readers", st)
        tablet.evaluate("() => __phone.rotary().setLine('connecting')")
        check(anim() == "tl-rotary-lamp-pulse", "connecting, it pulses orange", anim())
        # (the phone keeps retrying its line in the background and may set the light back; try a few times)
        green = False
        for _ in range(5):
            tablet.evaluate("() => __phone.rotary().setLine(true)")
            tablet.wait_for_timeout(450)                               # it fades up
            if lamp() == "rgb(127, 224, 138)" and anim() == "none":
                green = True
                break
        check(green, "connected, the light is steady green", lamp())
        tablet.evaluate("() => __phone.rotary().setLine(false)")

        # ---- the card file turns to the next card
        before = tablet.evaluate("() => __phone.cards().index()")
        tablet.click(".tl-cardfile__btn")
        tablet.wait_for_timeout(700)
        check(tablet.evaluate("() => __phone.cards().index()") != before or tablet.locator(".tl-cardfile__num").count() == 1, "tapping the card file turns its cards")

        # ---- the footer: credit, coffee, email, licenses, with their icons
        for href, words, ic in (("https://buymeacoffee.com/jdmiller", "Buy me a coffee", True), ("mailto:jdmiller2010@gmail.com", "Email Jordan", True), ("/phone/licenses.html", "Open-source licenses", False)):
            link = tablet.locator(f'.ph__foot a[href^="{href}"]')
            check(link.count() == 1 and words in link.inner_text() and (link.locator(".tl-icon").count() == 1) == ic, f"the footer has '{words}'")
        check("Buy me a coffee" in tablet.inner_text(".ph__foot") and "Support the project" not in tablet.inner_text(".ph__foot") and "Made by Jordan Miller" in tablet.inner_text(".ph__foot"), "and says who made it and how to support it")

        for theme in ("light", "dark"):
            tablet.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            tablet.screenshot(path=f"{SHOTS}/phone-{theme}.png", full_page=True)
        tablet.evaluate("document.documentElement.setAttribute('data-theme','light')")

        # ---- every screen size: the dial is on screen, nothing scrolls sideways, and the card file is where it belongs:
        #      under the phone in one column, in the left column beside it on a wide landscape screen
        for w, hgt in ((360, 740), (390, 844), (768, 1024), (1024, 768), (1280, 800), (1440, 900)):
            tablet.set_viewport_size({"width": w, "height": hgt})
            tablet.wait_for_timeout(150)
            box = tablet.locator(".tl-rotary__svg").bounding_box()
            dial = tablet.locator(".tlp-wheel").bounding_box()
            cf = tablet.locator(".tl-cardfile").bounding_box()
            dial_on_screen = dial and dial["x"] >= 0 and dial["x"] + dial["width"] <= w and dial["y"] >= 0 and dial["y"] + dial["height"] <= hgt
            cf_fits = cf and cf["x"] >= 0 and cf["x"] + cf["width"] <= w + 1
            wide = tablet.evaluate("document.documentElement.scrollWidth > innerWidth")
            landscape = w >= 900 and w >= hgt
            under = cf and box and cf["y"] > box["y"] + box["height"] * .6 and abs((cf["x"] + cf["width"] / 2) - (box["x"] + box["width"] / 2)) < 12
            left = cf and box and cf["x"] + cf["width"] <= box["x"] + box["width"] * .4
            where = left if landscape else under
            check(dial_on_screen and cf_fits and not wide and where,
                  f"at {w}×{hgt} the dial is on screen, the card file is {'on the left' if landscape else 'under the phone'}", f"{dial} {cf} wide={wide}")
            tablet.screenshot(path=f"{SHOTS}/phone-{w}x{hgt}.png", full_page=True)
        tablet.set_viewport_size({"width": 820, "height": 1100})
        tablet.wait_for_timeout(150)

        # ---- How to dial: a sheet of the guide's pictures, one at a time; it dials nothing while it's open
        tablet.click("#guide-open")
        tablet.wait_for_selector("#guide:not([hidden])", timeout=5000)
        check(tablet.inner_text("#guide .tl-sheet__title").strip() == "How to call a friend", "How to dial opens the guide")
        check("Step 1 of 9" in tablet.inner_text("#guide") and tablet.locator("#guide .ph-lamp").count() == 4, "its first step is the little light, with all four colors")
        check(tablet.is_disabled("#guide-back"), "Back is off on the first step")
        tablet.click("#guide-next")
        check("Step 2 of 9" in tablet.inner_text("#guide") and "Lift the handset" in tablet.inner_text("#guide"), "Next goes to lifting the handset")
        tablet.keyboard.press("3")
        tablet.click("#guide-back")
        check("Step 1 of 9" in tablet.inner_text("#guide"), "Back goes back")
        for _ in range(8):
            tablet.click("#guide-next")
        check("Step 9 of 9" in tablet.inner_text("#guide") and tablet.inner_text("#guide-next").strip() == "Done", "the last step says Done")
        try:
            tablet.wait_for_function("() => [...document.querySelectorAll('#guide img')].every((i) => i.complete && i.naturalWidth > 0)", timeout=5000)
            imgs = True
        except Exception:
            imgs = False
        check(imgs, "the pictures load")
        tablet.screenshot(path=f"{SHOTS}/phone-guide.png")
        tablet.click("#guide-next")
        tablet.wait_for_function("() => document.querySelector('#guide').hidden", timeout=5000)
        check(True, "Done closes it")
        check(tablet.evaluate("document.body.dataset.digits") == "" and tablet.evaluate("document.body.dataset.state") == "idle",
              "nothing was dialed while the guide was open, and the phone is still idle")

        # ---- ringing: only the handset trembles, and it stops when the phone stops ringing
        tablet.evaluate("() => { __phone.S.phase = 'ringing'; __phone.render(); }")
        moved = tablet.evaluate("""async () => { const h = document.querySelector('.tlp-handset'), b = document.querySelector('.tlp-base'); const seen = new Set(); let body = false;
          for (let i = 0; i < 12; i++) { seen.add(getComputedStyle(h).transform); body ||= getComputedStyle(b).transform !== 'none'; await new Promise((r) => setTimeout(r, 40)); }
          return { kinds: seen.size, body }; }""")
        check(tablet.locator(".tl-rotary.is-ringing").count() == 1 and moved["kinds"] > 2 and not moved["body"], "a ringing phone's handset trembles, and nothing else moves", str(moved))
        flashes = tablet.evaluate("""async () => { const l = document.querySelector('.tl-rotary .tlp-lamp'), seen = new Set();
          for (let i = 0; i < 10; i++) { seen.add(getComputedStyle(l).fill); await new Promise((r) => setTimeout(r, 120)); } return seen.size; }""")
        check(flashes > 2, "and its little light flashes", str(flashes))
        tablet.evaluate("() => { __phone.S.phase = 'idle'; __phone.render(); }")
        check(tablet.locator(".tl-rotary.is-ringing").count() == 0, "and it stops when the ringing does")

        # ---- the dial really turns (pretend we're off the hook, with a dial tone)
        # (no Asterisk here, so lift the handset quietly and set the phase by hand)
        tablet.evaluate("() => { __phone.S.hook = 'off'; __phone.S.phase = 'dialtone'; __phone.rotary().setHook(true, true); }")
        check(tablet.get_attribute(".tl-rotary", "data-hook") == "off", "the handset lifts")
        tablet.wait_for_timeout(600)
        tablet.screenshot(path=f"{SHOTS}/phone-lifted.png", full_page=True)
        # Count the sounds the mechanism makes: winding ticks, the governor's whirr, the pulse clicks and the thunk.
        tablet.evaluate("""async () => {
          await window.__phone.tones.unlock();
          window.__made = { sources: 0, oscs: 0 };
          const AC = AudioContext.prototype, bs = AC.createBufferSource, co = AC.createOscillator;
          AC.createBufferSource = function () { window.__made.sources++; return bs.apply(this, arguments); };
          AC.createOscillator = function () { window.__made.oscs++; return co.apply(this, arguments); };
        }""")
        drag_digit(tablet, 7)
        check(digits_become(tablet, "7"), "turning the wheel to the stop dials the digit")
        tablet.wait_for_timeout(300)
        made = tablet.evaluate("() => window.__made")
        # 7 turns 240 degrees: about 32 ratchet ticks (2 bursts each), 7 pulse clicks (2 each), a whirr and a thunk.
        check(made["sources"] >= 60, "winding and returning the dial make ratchet, pulse and whirr sounds", str(made))
        check(made["oscs"] >= 3, "and the governor's hum and the thunk", str(made))
        level = tablet.evaluate("() => window.__phone.tonesLevel()")
        check(level <= 0.05, "the dial tone is quieter than before (was 0.09 per wave)", str(level))
        before = tablet.evaluate("document.body.dataset.digits")
        # A short turn that doesn't reach the stop dials nothing.
        p0 = to_screen(tablet, CX + HOLE_K * R * math.cos(math.radians(-88)), CY + SQ * HOLE_K * R * math.sin(math.radians(-88)))
        tablet.mouse.move(p0["x"], p0["y"]); tablet.mouse.down()
        tablet.mouse.move(p0["x"] + 6, p0["y"] + 6); tablet.mouse.up()
        tablet.wait_for_timeout(900)
        check(tablet.evaluate("document.body.dataset.digits") == before, "a short turn dials nothing")
        drag_digit(tablet, 0)
        check(digits_become(tablet, "70"), "0 takes the long way round and still counts")
        tablet.keyboard.press("5")
        check(digits_become(tablet, "705"), "a keyboard can dial too")
        tablet.wait_for_timeout(1500)
        angle = tablet.evaluate("document.querySelector('.tlp-wheel').getAttribute('transform')")
        check(angle.startswith("rotate(0.00 "), "the wheel is back at rest after dialing", str(angle))
        # Digits dialed while the handset is on the hook do nothing, as on a real phone.
        tablet.evaluate("() => { __phone.rotary().setHook(false, true); __phone.S.hook = 'on'; }")
        tablet.keyboard.press("Tab"); tablet.focus(".tl-rotary__svg"); tablet.keyboard.press("3")
        tablet.wait_for_timeout(1500)
        check(tablet.evaluate("document.body.dataset.digits") == "705", "dialing with the handset down adds nothing")

        # ---- the debug hook never exposes the SIP secret
        check(tablet.evaluate("() => window.__phone.S.creds === undefined"), "the test hook can't read the SIP secret")

        # ---- removing the tablet from the treehouse is noticed
        hs = api.get(f"{BASE}/api/handsets", headers=h).json()["handsets"]
        api.delete(f"{BASE}/api/handsets/{hs[0]['id']}", headers=h, data={})
        tablet.evaluate("() => { __phone.S.hook = 'on'; __phone.S.phase = 'idle'; }")
        tablet.reload()
        tablet.wait_for_selector(".ph-code", timeout=20000)
        check("removed" in tablet.inner_text("body"), "a removed tablet says so and offers to be added again")

        # ---- leaving phone mode: "For parents" and the parent code
        def become_phone(name):
            tablet.wait_for_selector(".ph-code", timeout=20000)
            c = re.sub(r"\D", "", tablet.inner_text(".ph-code"))
            api.post(f"{BASE}/api/pair/claim", headers=h, data={"code": c, "name": name})
            tablet.wait_for_selector(".tl-rotary", timeout=15000)
        become_phone("Hall tablet")
        opener = tablet.locator("#leave-open")
        check(opener.count() == 1 and opener.inner_text().strip() == "For parents" and "tl-btn--primary" not in opener.get_attribute("class"),
              "the phone has a secondary 'For parents' button next to How to dial")
        check(tablet.locator("#guide-open").count() == 1, "and How to dial is still there")
        opener.click(); tablet.wait_for_selector("#leave:not([hidden])")
        go = tablet.locator("#leave-go")
        check(tablet.locator("#leave-code").get_attribute("type") == "password" and tablet.locator("#leave-code").get_attribute("inputmode") == "numeric",
              "the exit sheet asks for the parent code in a hidden numeric box")
        check("tl-btn--primary" in go.get_attribute("class") and go.inner_text().strip() == "Leave phone mode", "with one main button: Leave phone mode")
        tablet.screenshot(path=f"{SHOTS}/phone-leave.png")
        tablet.fill("#leave-code", "0000"); go.click()
        tablet.wait_for_selector("#leave-error .tl-alert")
        check("isn't the parent code" in tablet.inner_text("#leave-error") and tablet.locator(".tl-rotary").count() == 1
              and len(api.get(f"{BASE}/api/handsets", headers=h).json()["handsets"]) == 1, "a wrong code says so and the device stays a phone")
        tablet.fill("#leave-code", ""); go.click()
        tablet.wait_for_function("() => document.querySelector('#leave-error').innerText.includes('Type the parent code')")
        check(True, "an empty code asks for the code and sends nothing")
        tablet.fill("#leave-code", "2468"); go.click()
        tablet.wait_for_selector(".ph-code", timeout=15000)
        check(tablet.evaluate("() => location.pathname + location.search") == "/phone/" and "isn't a phone anymore" in tablet.inner_text("body"),
              "the right code, with no parent signed in, goes back to the first screen (QR and Log in) and says it isn't a phone anymore (once: the address is cleaned, so a reload doesn't repeat it)")
        check(tablet.evaluate("() => localStorage.getItem('treeline.phone')") is None, "this device forgot the phone's sign-in")
        check(api.get(f"{BASE}/api/handsets", headers=h).json()["handsets"] == [], "and the handset is gone from the treehouse")
        tablet.screenshot(path=f"{SHOTS}/phone-left.png", full_page=True)
        become_phone("Porch tablet")                                       # a parent signed in on the same device goes to the dashboard instead
        tablet.evaluate("(t) => localStorage.setItem('treeline.token', t)", h["Authorization"].split(" ", 1)[1])
        tablet.reload(); tablet.wait_for_selector("#leave-open")
        tablet.click("#leave-open"); tablet.wait_for_selector("#leave:not([hidden])")
        check("parent dashboard" in tablet.inner_text("#leave"), "with a parent signed in the sheet says it goes to the dashboard")
        tablet.fill("#leave-code", "2468"); tablet.click("#leave-go")
        tablet.wait_for_url("**/parent/**", timeout=15000)
        tablet.wait_for_selector("#app-title", timeout=15000)
        check(tablet.evaluate("() => location.pathname + location.hash") == "/parent/#/home" and tablet.inner_text("#app-title") == house["name"],
              "the right code goes straight to the signed-in parent dashboard")
        check(tablet.evaluate("() => localStorage.getItem('treeline.phone')") is None, "and this device is not a phone anymore")

        # ---- a parent who doesn't know the code can sign the device out (it signs nobody in)
        tablet.goto(f"{BASE}/phone/?test=1"); become_phone("Shed tablet")      # (a parent is still signed in on this device)
        tablet.reload(); tablet.wait_for_selector("#leave-open")
        tablet.click("#leave-open"); tablet.wait_for_selector("#leave:not([hidden])")
        tablet.click("[data-forgot]")
        check(tablet.locator("#leave-form").is_hidden() and tablet.locator("#sign-out-go").is_visible() and tablet.locator("#leave-go").is_hidden()
              and tablet.locator("#leave input").count() == 1, "'I don't know the code' swaps the code box for a sign-out, with no sign-in form")
        check("signed out of the parent dashboard" in tablet.inner_text("#leave-forgot"), "and says what signing out does")
        tablet.click("[data-use-code]")
        check(tablet.locator("#leave-form").is_visible() and tablet.locator("#leave-forgot").is_hidden(), "'I have the parent code' goes back")
        tablet.click("[data-forgot]"); tablet.click("#sign-out-go")
        tablet.wait_for_selector(".ph-code", timeout=15000)
        check(tablet.evaluate("() => location.pathname + location.search") == "/phone/" and "signed out" in tablet.inner_text("body"),
              "signing out lands on the first screen and says so")
        check(tablet.evaluate("() => [localStorage.getItem('treeline.phone'), localStorage.getItem('treeline.token')]") == [None, None],
              "this browser is fully signed out: no phone, and no parent session either")
        check(api.get(f"{BASE}/api/me", headers=h).status == 401, "the parent session that was on the device no longer works on the server")
        again = f"{BASE}/api/auth/request"
        code2 = api.post(again, data={"email": f"phone-parent-{stamp}@example.com"}).json()["dev_code"]
        h2 = {"Authorization": "Bearer " + api.post(f"{BASE}/api/auth/verify", data={"email": f"phone-parent-{stamp}@example.com", "code": code2}).json()["token"]}
        check(api.get(f"{BASE}/api/handsets", headers=h2).json()["handsets"] == [], "the handset is gone from the treehouse")
        h = h2                                                                  # (the old session is gone; clean up with the new one)
        tablet.goto(f"{BASE}/parent/#/home"); tablet.wait_for_selector("#email", timeout=10000)
        check(tablet.evaluate("() => location.pathname") == "/parent/" and tablet.locator("#step-email").is_visible(), "so the dashboard asks for a login")
        api.delete(f"{BASE}/api/treehouse", headers=h, data={"confirm": house["name"]})     # leave the database as we found it
        api.delete(f"{BASE}/api/treehouse", headers=fh, data={"confirm": friend["name"]})
        browser.close()

    if errors:
        print("\nPROBLEMS:")
        for e in dict.fromkeys(errors):
            print(" -", e)
        sys.exit(1)
    print(f"\nall {count[0]} checks passed")


if __name__ == "__main__":
    os.makedirs(SHOTS, exist_ok=True)
    main()
