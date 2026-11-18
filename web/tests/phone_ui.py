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


def digits_become(page, want, timeout=5000):
    try:
        page.wait_for_function("(d) => document.body.dataset.digits === d", arg=want, timeout=timeout)
        return True
    except Exception:
        return False


def wheel_center(page):
    return page.evaluate("""() => { const r = document.querySelector('.rp').getBoundingClientRect();
      return { x: r.left + r.width * 180 / 360, y: r.top + r.height * 292 / 470, k: r.width / 360 }; }""")


def drag_digit(page, digit):
    """Turn the wheel with the mouse the way a finger would: grab the hole, go clockwise to the stop."""
    c = wheel_center(page)
    hole = page.locator(f'.rp-hole[data-digit="{digit}"]').bounding_box()
    hx, hy = hole["x"] + hole["width"] / 2, hole["y"] + hole["height"] / 2
    start = math.degrees(math.atan2(hx - c["x"], -(hy - c["y"])))
    pulses = 10 if digit == 0 else digit
    total = 30 * pulses + 30
    r = math.hypot(hx - c["x"], hy - c["y"])
    page.mouse.move(hx, hy)
    page.mouse.down()
    for step in range(1, 25):
        a = math.radians(start + total * step / 24)
        page.mouse.move(c["x"] + r * math.sin(a), c["y"] - r * math.cos(a))
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
        tablet.wait_for_selector(".rp", timeout=15000)
        check(tablet.locator(".rp").count() == 1 and tablet.locator(".ph-code").count() == 0, "the tablet becomes a phone")
        tablet.wait_for_function("(n) => document.querySelector('#rp-number').textContent === n", arg=house["number"], timeout=15000)
        check(tablet.text_content("#rp-number") == house["number"], "the number card shows the treehouse's number")

        # ---- what's on the screen
        check(tablet.locator(".rp-hole").count() == 10, "ten finger holes")
        check(tablet.locator(".rp-digit").count() == 10, "ten numerals under the holes")
        check("Can't call 911 or outside numbers" in tablet.inner_text("body"), "the phone's main screen says it can't call 911")
        check("Open-source licenses" in tablet.inner_text("body"), "the footer is there")
        wide = tablet.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
        check(not wide, "nothing scrolls sideways")
        for theme in ("light", "dark"):
            tablet.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
            tablet.screenshot(path=f"{SHOTS}/phone-{theme}.png", full_page=True)
        tablet.evaluate("document.documentElement.setAttribute('data-theme','light')")

        # ---- the dial really turns (pretend we're off the hook, with a dial tone)
        tablet.evaluate("() => { __phone.S.hook = 'off'; __phone.S.phase = 'dialtone'; document.querySelector('.rp').classList.add('is-off'); }")
        tablet.screenshot(path=f"{SHOTS}/phone-lifted.png", full_page=True)
        drag_digit(tablet, 7)
        check(digits_become(tablet, "7"), "turning the wheel to the stop dials the digit")
        before = tablet.evaluate("document.body.dataset.digits")
        # A short turn that doesn't reach the stop dials nothing.
        c = wheel_center(tablet)
        hole = tablet.locator('.rp-hole[data-digit="3"]').bounding_box()
        hx, hy = hole["x"] + hole["width"] / 2, hole["y"] + hole["height"] / 2
        tablet.mouse.move(hx, hy); tablet.mouse.down()
        tablet.mouse.move(hx + 6, hy + 6); tablet.mouse.up()
        tablet.wait_for_timeout(600)
        check(tablet.evaluate("document.body.dataset.digits") == before, "a short turn dials nothing")
        drag_digit(tablet, 0)
        check(digits_become(tablet, "70"), "0 takes the long way round and still counts")
        tablet.keyboard.press("5")
        check(digits_become(tablet, "705"), "a keyboard can dial too")
        angle = tablet.evaluate("document.querySelector('#wheel').getAttribute('transform')")
        check(angle in ("rotate(0 180 292)", None), "the wheel is back at rest after dialing", str(angle))

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
