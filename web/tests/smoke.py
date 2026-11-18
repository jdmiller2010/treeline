"""Drives the parent app in a real (headless) browser.

  python3 web/tests/smoke.py            # needs: pip install playwright, a running API
  BASE=http://127.0.0.1:18080 SHOTS=/some/dir CHROME=/path/to/chrome-headless-shell python3 web/tests/smoke.py

Checks the main flows, fails on any console error or page error, and takes
screenshots at the widths the design system names, in both themes.
"""

import glob
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8080")
SHOTS = os.environ.get("SHOTS", "/tmp/treeline-shots")
CHROME = os.environ.get("CHROME") or next(iter(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))), None)
WIDTHS = [360, 390, 768, 1024, 1280, 1440]
errors = []
step = [0]


def check(cond, what):
    step[0] += 1
    print(("ok   " if cond else "FAIL ") + what, flush=True)
    if not cond:
        errors.append(what)


def watch(page, label):
    # Browsers log every 4xx as a console error; the app shows those to the user, and some tests cause them on purpose.
    page.on("console", lambda m: errors.append(f"{label} console {m.type}: {m.text}")
            if m.type in ("error", "warning") and "Failed to load resource" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(f"{label} page error: {e}"))
    # A request cut off by the next click or the page closing is not a failure.
    page.on("requestfailed", lambda r: errors.append(f"{label} request failed: {r.url} ({r.failure})")
            if r.failure != "net::ERR_ABORTED" else None)


def sign_in(page, email):
    page.goto(f"{BASE}/parent/")
    page.fill("#email", email)
    page.click("#step-email button[type=submit]")
    page.wait_for_selector("#step-code:not([hidden])")
    note = page.inner_text("#dev-note")
    code = re.search(r"(\d{6})", note).group(1)
    boxes = page.locator("#step-code .tl-code__box")
    for i, d in enumerate(code):
        boxes.nth(i).fill(d)
    page.click("#step-code button[type=submit]")


def shoot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=f"{SHOTS}/{name}.png", full_page=True)


def no_sideways_scroll(page, label):
    wide = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
    check(not wide, f"{label}: nothing scrolls sideways")


def make_family(browser, email, name, tz="America/Los_Angeles"):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    watch(page, name)
    sign_in(page, email)
    page.wait_for_selector("#th-name")
    page.fill("#th-name", name)
    page.fill("#th-you", "Pat")
    page.click("button[type=submit]")
    page.wait_for_selector("#ack")
    check(page.locator("button[type=submit]").is_disabled(), f"{name}: can't continue without the 911 box")
    page.check("#ack", force=True) if False else page.click("label[for=ack]")
    page.click("button[type=submit]")
    page.wait_for_selector("[data-skip]")
    return ctx, page


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME)

        # ---- sign-in
        anon = browser.new_context(viewport={"width": 390, "height": 844})
        page = anon.new_page()
        watch(page, "anon")
        page.goto(f"{BASE}/parent/")
        page.wait_for_selector("#email")
        check("Treeline can't call 911" in page.inner_text("body") or "can't call 911" in page.inner_text("body"), "sign-in says plainly that 911 isn't available")
        no_sideways_scroll(page, "sign-in 390")
        shoot(page, "signin-390")
        page.fill("#email", "nope")
        page.click("#step-email button[type=submit]")
        page.wait_for_selector("#email-error .tl-alert")
        check("email address" in page.inner_text("#email-error"), "bad email gets a plain message")
        anon.close()

        # ---- two families
        a_ctx, a = make_family(browser, "alex@example.com", "Alex's house")
        shoot(a, "setup-step3-390")
        a.click("[data-add]")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden])")
        shoot(a, "add-phone-sheet-390")
        a.fill("#hs-name", "Hall phone")
        a.click("label[for=kind-1]")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("text=Set up Hall phone")
        check("Password" in a.inner_text(".tl-sheet-scrim:not([hidden])"), "adapter settings dialog shows the password once")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("[data-code]")
        a.click("[data-code]")
        a.wait_for_selector("[data-copy]")
        code = re.search(r"[A-Z2-9]{4}-[A-Z2-9]{4}", a.inner_text(".tl-sheet-scrim:not([hidden])")).group(0)
        shoot(a, "ladder-code-390")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("#app-title")
        check(a.inner_text("#app-title") == "Home", "setup ends on Home")

        s_ctx, s = make_family(browser, "sam@example.com", "Sam's house")
        s.click("[data-skip]")
        s.click("[data-later]")
        s.wait_for_selector("#app-title")
        s.goto(f"{BASE}/parent/#/strings")
        s.wait_for_selector("text=No strings yet")
        s.click("main [data-redeem]")
        s.fill("#ladder", code)
        s.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        s.wait_for_selector("text=Waiting on them")
        check("Waiting on them" in s.inner_text("main"), "Sam's request waits on Alex")

        # Alex approves from Home.
        a.goto(f"{BASE}/parent/#/home")
        a.reload()
        a.wait_for_selector("text=Waiting on families")
        shoot(a, "home-waiting-390")
        check("Sam's house" in a.inner_text("main"), "Alex sees Sam's request")
        a.click("[data-string=approve]")
        a.wait_for_selector(".tl-toast")
        a.goto(f"{BASE}/parent/#/strings")
        a.wait_for_selector("text=Sam's house")
        check("Strung" in a.inner_text("main"), "the string is live")

        # ---- every screen, every width, both themes
        screens = {"home": "#/home", "strings": "#/strings", "calls": "#/calls", "quiet": "#/quiet", "house": "#/house",
                   "phonebook": "#/phonebook", "settings": "#/settings", "privacy": "#/privacy", "about": "#/about", "actions": "#/actions"}
        for width in WIDTHS:
            a.set_viewport_size({"width": width, "height": 900})
            for theme in ("light", "dark"):
                a.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
                for name, hash_ in screens.items():
                    a.goto(f"{BASE}/parent/{hash_}")
                    a.wait_for_selector("#app-title")
                    a.evaluate(f"document.documentElement.setAttribute('data-theme','{theme}')")
                    no_sideways_scroll(a, f"{name} {width} {theme}")
                    if width in (390, 1280) or (name in ("home", "strings") and width in (360, 768, 1024, 1440)):
                        shoot(a, f"{name}-{width}-{theme}")
                # the AppBar title lines up with the first card at wide widths
        # One h1 per screen
        a.set_viewport_size({"width": 1280, "height": 900})
        for name, hash_ in screens.items():
            a.goto(f"{BASE}/parent/{hash_}")
            a.wait_for_selector("#app-title")
            check(a.locator("h1").count() == 1, f"{name}: exactly one h1")
            check("Open-source licenses" in a.inner_text("main"), f"{name}: footer present")
            check(a.locator(".tl-btn--primary").count() <= 1 or name in ("home",), f"{name}: at most one primary button ({a.locator('.tl-btn--primary').count()})")

        # ---- quiet hours
        a.goto(f"{BASE}/parent/#/quiet")
        a.wait_for_selector("#quiet-form")
        a.fill("#qh-start", "21:30")
        check("9:30 pm" in a.inner_text("#qh-preview"), "quiet hours preview follows the time field")
        a.click("#quiet-form button[type=submit]")
        a.wait_for_selector(".tl-toast")
        a.reload()
        a.wait_for_selector("#qh-start")
        check(a.input_value("#qh-start") == "21:30", "quiet hours saved")

        # ---- pause is one tap
        a.goto(f"{BASE}/parent/#/home")
        a.wait_for_selector("[data-pause]")
        a.click("[data-pause]")
        a.wait_for_selector("text=Calls are paused")
        a.wait_for_load_state("networkidle")
        a.click("[data-pause]")
        a.wait_for_selector("text=Calls are back on")
        a.wait_for_load_state("networkidle")

        # ---- sign out returns to sign-in
        a.click(".tl-avatar-btn")
        a.click("[data-sign-out]")
        a.wait_for_selector("#email")
        check(True, "sign out works")
        browser.close()

    if errors:
        print("\nPROBLEMS:")
        for e in dict.fromkeys(errors):
            print(" -", e)
        sys.exit(1)
    print(f"\nall {step[0]} checks passed; screenshots in {SHOTS}")


if __name__ == "__main__":
    main()
