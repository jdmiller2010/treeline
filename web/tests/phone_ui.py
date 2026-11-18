"""The tablet softphone's screen, in a headless browser, without Asterisk.

Pairs a tablet through the real API, checks the phone is drawn and the dial
really turns, and checks that a removed tablet notices. Real calls are tested
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

        # ---- a parent claims it
        h, house = parent_session(api, f"phone-parent-{int(__import__('time').time())}@example.com", "Dial house")
        r = api.post(f"{BASE}/api/pair/claim", headers=h, data={"code": code, "name": "Kitchen tablet"})
        check(r.status == 201, "a parent claims the code")
        tablet.wait_for_selector(".tl-rotary", timeout=15000)
        check(tablet.locator(".tl-rotary").count() == 1 and tablet.locator(".ph-code").count() == 0, "the tablet becomes a phone")
        tablet.wait_for_function("(n) => document.querySelector('.tl-rotary__number').textContent === n", arg=house["number"], timeout=15000)
        check(tablet.text_content(".tl-rotary__number") == house["number"], "the number card shows the treehouse's number")

        # ---- what's on the screen
        check(tablet.locator(".tlp-wheel").count() == 1 and tablet.locator(".tlp-handset").count() == 1, "the design system's wheel and handset are there")
        check("Can’t call 911 or outside numbers" in tablet.inner_text(".tl-rotary__notice"), "the phone's main screen says it can't call 911")
        check(tablet.locator("text=Can’t call 911").count() + tablet.locator("text=Can't call 911").count() == 1, "and says it once")
        check("Open-source licenses" in tablet.inner_text("body"), "the footer is there")
        wide = tablet.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
        check(not wide, "nothing scrolls sideways")
        for theme in ("light", "dark"):
            tablet.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            tablet.screenshot(path=f"{SHOTS}/phone-{theme}.png", full_page=True)
        tablet.evaluate("document.documentElement.setAttribute('data-theme','light')")

        # ---- "How do I dial?": a lesson that plays on the phone and dials nothing
        tablet.evaluate("() => __phone.setTutorialSpeed(8)")
        help_button = tablet.locator("[data-help]")
        check(help_button.is_visible(), "an idle phone offers 'How do I dial?'")
        tablet.screenshot(path=f"{SHOTS}/phone-with-help.png", full_page=True)
        help_button.click()
        tablet.wait_for_selector("#tutorial .tl-steps")
        check(not help_button.is_visible(), "the button steps aside while the lesson plays")
        lifted = finger = turned = False
        for _ in range(400):
            st = tablet.evaluate("""() => ({ hook: document.querySelector('.tl-rotary').dataset.hook,
                finger: !!document.querySelector('.ph__finger.is-on'),
                turn: document.querySelector('.tlp-wheel').getAttribute('transform') })""")
            lifted |= st["hook"] == "off"
            finger |= st["finger"]
            turned |= not st["turn"].startswith("rotate(0.00")
            if tablet.locator("#tutorial").inner_text().strip() == "" and (lifted and turned):
                break
            tablet.wait_for_timeout(100)
        check(lifted, "the lesson lifts the handset")
        check(finger, "a fingertip drops into a hole")
        check(turned, "and the wheel winds round and spins back")
        check(tablet.evaluate("document.body.dataset.digits") == "" and tablet.evaluate("document.body.dataset.state") == "idle",
              "nothing was dialed and the phone is still idle")
        tablet.wait_for_function("() => document.querySelector('#tutorial').innerText.trim() === ''", timeout=30000)
        check(tablet.get_attribute(".tl-rotary", "data-hook") == "on", "the handset is back on the hook when it ends")
        check(tablet.evaluate("document.querySelector('.tlp-wheel').getAttribute('transform')").startswith("rotate(0.00"), "and the wheel is at rest")
        check(tablet.locator(".ph__finger").count() == 0, "and the fingertip is gone")
        check(help_button.is_visible(), "the button comes back")
        # Stop ends it at once, wherever it is.
        tablet.evaluate("() => __phone.setTutorialSpeed(1)")
        help_button.click()
        tablet.wait_for_selector("#tutorial .tl-steps")
        tablet.click("[data-tutorial-stop]")
        tablet.wait_for_function("() => document.querySelector('#tutorial').innerText.trim() === ''", timeout=5000)
        check(tablet.get_attribute(".tl-rotary", "data-hook") == "on", "Stop puts the handset back")
        tablet.evaluate("() => __phone.setTutorialSpeed(1)")

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
