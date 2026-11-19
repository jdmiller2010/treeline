"""The tablet softphone's screen, in a headless browser, without Asterisk.

Pairs a tablet through the real API, checks the room is drawn around the phone
(the guide book opens, the cards can be picked up, the card file holds the
strings), that the dial really turns and the handset trembles when it rings,
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

        # ---- what's on the screen: the room, with the phone on its table
        check(tablet.locator(".tl-desk").count() == 1, "the phone sits in the design system's softphone room")
        check(tablet.locator(".tl-rotary .tlp-wheel").count() == 1 and tablet.locator(".tl-rotary .tlp-handset").count() == 1 and tablet.locator(".tlp-wheel").count() == 1, "the design system's wheel and handset are there, once")
        check(tablet.locator(".tl-rotary__notice").count() == 0, "the phone's own notice is off: the room's sticker says it")
        check(tablet.locator(".tl-desk__scene text", has_text="NO 911").count() >= 1, "the no-911 sticker is on the drawer")
        sr = tablet.inner_text(".tl-desk__sr")
        check("can’t call 911" in sr and tablet.locator(".tl-desk__sr").count() == 1, "screen readers hear that it can't call 911, once")
        tablet.wait_for_function("(n) => [...document.querySelectorAll('.tl-desk__name')].every((t) => t.textContent === n)", arg=house["name"], timeout=15000)
        check(True, "the kid's drawing has the treehouse's name on it")
        tablet.wait_for_function("(n) => [...document.querySelectorAll('.tl-desk__cardname')].some((t) => t.textContent === n)", arg=friend["name"], timeout=15000)
        nums = tablet.evaluate("() => [...document.querySelectorAll('.tl-desk__cardnum')].map((t) => t.textContent)")
        check(friend["number"] in nums, "the card file has a card for the string, with its number")
        quiet = tablet.evaluate("() => document.querySelector('.tl-desk__quiettext').textContent")
        check(bool(re.match(r"^(none|\d{1,2}(:\d\d)? [ap]m – \d{1,2}(:\d\d)? [ap]m)$", quiet)), "the sticky note shows the quiet hours", quiet)
        check(tablet.inner_text("#status").strip() == "" and tablet.inner_text("#sub").strip() == "", "an idle phone's wall has no how-to words: the guide book teaches")
        # the clock radio on the desk shows the real time, and the line: no SIP here, so its digits blink
        now = tablet.evaluate("() => { const d = new Date(), h = d.getHours(); return ((h + 11) % 12 + 1) + ':' + String(d.getMinutes()).padStart(2, '0') + ' ' + (h >= 12 ? 'PM' : 'AM'); }")
        shown = tablet.get_attribute("[data-tl-desk]", "data-clock")
        check(shown == now, "the clock radio shows the real time", f"{shown} vs {now}")
        check(tablet.locator(".tl-desk__clock.is-offline").count() == 3 and "reconnecting" in tablet.inner_text("#reg"),
              "while the phone isn't connected the clock blinks and says so to screen readers")
        tablet.evaluate("() => __phone.desk().setOnline(true)")
        check(tablet.locator(".tl-desk__clock.is-offline").count() == 0, "and stops blinking when it's connected")
        tablet.evaluate("() => __phone.desk().setOnline(false)")
        wide = tablet.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
        check(not wide, "nothing scrolls sideways")
        for theme in ("light", "dark"):
            tablet.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            tablet.screenshot(path=f"{SHOTS}/phone-{theme}.png", full_page=True)
        tablet.evaluate("document.documentElement.setAttribute('data-theme','light')")

        # ---- every screen size gets the room that fits it, and the phone stays on screen
        for w, hgt, want in ((360, 740, "tall"), (390, 844, "tall"), (768, 1024, "portrait"), (1024, 768, "wide"), (1280, 800, "wide"), (1440, 900, "wide")):
            tablet.set_viewport_size({"width": w, "height": hgt})
            tablet.wait_for_timeout(150)
            got = tablet.evaluate("() => ['wide','portrait','tall'].find((n) => getComputedStyle(document.querySelector('.tl-desk__scene.tl-desk__l--' + n)).display === 'block')")
            box = tablet.locator(".tl-rotary__svg").bounding_box()
            fits = box and box["x"] >= 0 and box["x"] + box["width"] <= w + 1 and box["y"] + box["height"] <= hgt + 1
            over = tablet.evaluate("document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight")
            check(got == want and fits and not over, f"at {w}×{hgt} the room is '{want}' and the phone fits", f"{got} {box} overflow={over}")
            tablet.screenshot(path=f"{SHOTS}/phone-{w}x{hgt}.png")
        tablet.set_viewport_size({"width": 820, "height": 1100})
        tablet.wait_for_timeout(150)

        # ---- the guide book: it opens into pictures, turns its pages, closes, and dials nothing
        tablet.click('[data-desk-open="book"]')
        tablet.wait_for_function("() => document.querySelector('.tl-book__count').textContent === 'Pages 1–2'", timeout=5000)
        check(True, "the guide book comes up and opens")
        check(tablet.locator(".tl-desk__look--book .tl-book__art[aria-label]").count() >= 10, "its pages are pictures, each described for screen readers")
        tablet.keyboard.press("ArrowRight")
        tablet.wait_for_function("() => document.querySelector('.tl-book__count').textContent === 'Pages 3–4'", timeout=5000)
        check(True, "the pages turn")
        tablet.screenshot(path=f"{SHOTS}/phone-book.png")
        tablet.keyboard.press("3")
        tablet.keyboard.press("Escape")
        tablet.wait_for_function("() => document.querySelector('.tl-desk__look--book').hidden", timeout=5000)
        check(tablet.evaluate("document.activeElement.getAttribute('data-desk-open')") == "book", "Escape closes it and puts focus back on the book")
        check(tablet.evaluate("document.body.dataset.digits") == "" and tablet.evaluate("document.body.dataset.state") == "idle",
              "nothing was dialed while the book was open, and the phone is still idle")

        # ---- the cards you can pick up are the links: support, email, licenses
        for item, href in (("coffee", "https://buymeacoffee.com/jdmiller"), ("card", "mailto:jdmiller2010@gmail.com"), ("licenses", "/phone/licenses.html")):
            tablet.click(f'[data-desk-open="{item}"]')
            tablet.wait_for_selector(f".tl-desk__look--{item}:not([hidden])")
            got = tablet.get_attribute(f".tl-desk__look--{item} .tl-desk__heldart", "href") or ""
            check(got.startswith(href), f"picking up the {item} shows it with its link", got)
            tablet.click(f".tl-desk__look--{item} .tl-desk__putback")
            tablet.wait_for_function("(k) => document.querySelector('.tl-desk__look--' + k).hidden", arg=item, timeout=5000)
        check(True, "and each goes back")
        check("NO 911" not in tablet.inner_text(".tl-desk__look--card"), "the business card is the credit, not a warning")

        # ---- ringing: only the handset trembles, and it stops when the phone stops ringing
        tablet.evaluate("() => { __phone.S.phase = 'ringing'; __phone.render(); }")
        moved = tablet.evaluate("""async () => { const h = document.querySelector('.tlp-handset'), b = document.querySelector('.tlp-base'); const seen = new Set(); let body = false;
          for (let i = 0; i < 12; i++) { seen.add(getComputedStyle(h).transform); body ||= getComputedStyle(b).transform !== 'none'; await new Promise((r) => setTimeout(r, 40)); }
          return { kinds: seen.size, body }; }""")
        check(tablet.locator(".tl-rotary.is-ringing").count() == 1 and moved["kinds"] > 2 and not moved["body"], "a ringing phone's handset trembles, and nothing else moves", str(moved))
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
