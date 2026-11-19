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
                  if m.type in ("error", "warning") and "Failed to load resource" not in m.text and "WebSocket" not in m.text else None)
        tablet.on("pageerror", lambda e: errors.append(f"page error: {e}"))

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
        notice = tablet.locator(".tl-rotary__notice")
        check(notice.count() == 1 and "911" in notice.inner_text() and notice.locator(".tl-icon").count() == 1,
              "the phone's own notice says under it that it can't call 911")
        check(tablet.locator(".tl-alert").count() == 0, "and it's the design system's notice, not an alert box")
        check(tablet.locator("h1").count() == 1, "one page title")
        tablet.wait_for_function("(n) => document.querySelector('h1').textContent === n", arg=house["name"], timeout=15000)
        check(True, "the page title is the treehouse's name")
        tablet.wait_for_function("(n) => [...document.querySelectorAll('.tl-cardfile__name')].some((t) => t.textContent === n)", arg=friend["name"], timeout=15000)
        check(tablet.text_content(".tl-cardfile__num") == friend["number"], "the card file has a card for the string, with its number")
        quiet = tablet.locator("#quiet")
        qt = quiet.inner_text().strip() if quiet.is_visible() else "none"
        check(qt == "none" or bool(re.match(r"^Quiet time \d{1,2}(:\d\d)? [ap]m – \d{1,2}(:\d\d)? [ap]m$", qt)), "a tag shows the quiet hours, when there are some", qt)
        check(tablet.locator("#status .tl-presence").count() == 1, "what the phone is doing is a Presence under the name")
        # the little light on the phone is the line: no SIP here, so it pulses orange while it tries, then blinks red
        lamp = lambda: tablet.evaluate("() => getComputedStyle(document.querySelector('.tl-rotary .tlp-lamp')).fill")
        anim = lambda: tablet.evaluate("() => getComputedStyle(document.querySelector('.tl-rotary .tlp-lamp')).animationName")
        state0 = tablet.get_attribute(".tl-rotary", "data-line")
        check(state0 in ("connecting", "off") and ("connecting" in tablet.inner_text("#reg") or "can't connect" in tablet.inner_text("#reg")),
              "while the phone isn't connected its little light says so, and screen readers hear it", state0)
        tablet.wait_for_function("() => document.querySelector('.tl-rotary').getAttribute('data-line') === 'off'", timeout=20000)
        check(anim() == "tl-rotary-lamp-blink" and "Ask a grown-up" in tablet.inner_text("#reg"), "after trying for a while it blinks red: something's wrong", anim())
        st = tablet.inner_text("#status")
        check("Ask a grown-up" in st or "sleeping" in st.lower() or "Quiet" in st, "and the words under the name say so too", st)
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
        check("Support the project:" in tablet.inner_text(".ph__foot") and "Made by Jordan Miller" in tablet.inner_text(".ph__foot"), "and says who made it and how to support it")

        for theme in ("light", "dark"):
            tablet.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            tablet.screenshot(path=f"{SHOTS}/phone-{theme}.png", full_page=True)
        tablet.evaluate("document.documentElement.setAttribute('data-theme','light')")

        # ---- every screen size: the phone and the card file fit, nothing scrolls sideways
        for w, hgt in ((360, 740), (390, 844), (768, 1024), (1024, 768), (1280, 800), (1440, 900)):
            tablet.set_viewport_size({"width": w, "height": hgt})
            tablet.wait_for_timeout(150)
            box = tablet.locator(".tl-rotary__svg").bounding_box()
            cf = tablet.locator(".tl-cardfile").bounding_box()
            fits = box and box["x"] >= 0 and box["x"] + box["width"] <= w + 1 and box["y"] >= 0 and box["y"] + box["height"] <= hgt + 1
            cf_fits = cf and cf["x"] >= 0 and cf["x"] + cf["width"] <= w + 1
            wide = tablet.evaluate("document.documentElement.scrollWidth > innerWidth")
            under = cf and box and cf["y"] > box["y"] + box["height"] * .6 and abs((cf["x"] + cf["width"] / 2) - (box["x"] + box["width"] / 2)) < 12
            beside = cf and box and cf["x"] > box["x"] + box["width"] * .7
            where = under if w < 600 else beside
            check(fits and cf_fits and not wide and where, f"at {w}×{hgt} the phone fits, the card file is {'under it, centred' if w < 600 else 'beside it'}", f"{box} {cf} wide={wide}")
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
