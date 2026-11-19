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
    page.click("label[for=ack]")
    check(page.locator("button[type=submit]").is_disabled(), f"{name}: one box isn't enough, the privacy box is needed too")
    page.click("label[for=consent]")
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
        check(page.locator("#step-email").is_visible() and not page.locator("#step-code").is_visible(),
              "sign-in shows the email step only: the code step stays hidden until a code is sent")
        check(page.locator("form#step-email").count() == 1 and page.locator("section.tl-card:has(h1):has(.tl-art):has(#email)").count() == 1,
              "the picture, the title and the email box are all in one card")
        shoot(page, "signin-390")
        # The green fill is a design token (--tl-canopy-fill). A stray character in treeline.css once made the
        # browser drop the whole block of --tl-* variables, and every green button, switch and checkbox became
        # transparent: an outline that only turned green while pressed.
        fill = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--tl-canopy-fill').trim()")
        bg = page.evaluate("() => getComputedStyle(document.querySelector('button.tl-btn--primary')).backgroundImage")
        check(bool(fill) and "gradient" in bg, "the primary button is filled green (the design tokens loaded)")
        page.fill("#email", "nope")
        page.click("#step-email button[type=submit]")
        page.wait_for_selector("#email-error .tl-alert")
        check("email address" in page.inner_text("#email-error"), "bad email gets a plain message")
        anon.close()

        # ---- two families
        a_ctx, a = make_family(browser, "alex@example.com", "Alex's house")
        check(a.locator("[aria-label='Kinds of phone'] .tl-row").count() == 3 and a.locator("section.tl-card:has([data-add])").count() == 0,
              "the add-a-phone step lists the three kinds of phone, and its buttons aren't in a card of their own")
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
        check(a.inner_text("#app-title") == "Alex's house" and a.locator(".tl-home-hero").count() == 1, "setup ends on Home, titled with the treehouse")

        s_ctx, s = make_family(browser, "sam@example.com", "Sam's house")
        s.click("[data-skip]")
        s.click("[data-later]")
        s.wait_for_selector("#app-title")
        s.wait_for_selector(".tl-home-hero")
        check(s.locator("h2:has-text('Phones')").count() == 1 and s.locator("text=Add your first phone").count() == 0,
              "with no phones yet, Home has one Phones section, not a second 'add your first phone' prompt")
        check(s.locator(".tl-art").count() == 1 and s.locator(".tl-empty__art").count() == 0,
              "and one picture on the screen: the treehouse at the top")
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

        # ---- one switch disconnects a phone; one tap makes this browser a phone
        a.goto(f"{BASE}/parent/#/home")
        a.wait_for_selector("[data-handset-switch]")
        sw = a.locator("[data-handset-switch]").first
        check(sw.get_attribute("aria-checked") == "true", "a phone starts connected")
        sw.click()
        a.wait_for_selector("text=It won't ring or place calls")
        a.wait_for_selector("main >> text=Disconnected: no calls in or out")
        a.reload(); a.wait_for_selector("[data-handset-switch]")
        check(a.locator("[data-handset-switch]").first.get_attribute("aria-checked") == "false", "the phone stays disconnected after a reload")
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("h2:has-text('Phones')")
        check("Disconnected" in a.inner_text("main"), "Home lists the phones and shows it's disconnected")
        a.locator("[data-handset-switch]").first.click()
        a.wait_for_selector("text=is connected again")
        # Home opens with the treehouse: the picture, the name under it, when it joined and its number (the brand guide's
        # picture-with-text, centered). Scrolled up under the title bar, the name moves into the title bar instead.
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector(".tl-home-hero")
        a.set_viewport_size({"width": 390, "height": 700}); a.wait_for_timeout(400)
        check(a.locator(".tl-home-hero .tl-art").count() == 1 and a.inner_text("#home-name") == "Alex's house", "Home opens with the treehouse picture and its name under it")
        meta = a.inner_text(".tl-home-hero__meta")
        check(meta.startswith("Joined ") and "Number " in meta and bool(re.search(r"\d{4}$", meta)), f"with when it joined and its number ({meta})")
        check(a.evaluate("() => getComputedStyle(document.querySelector('.tl-home-hero')).textAlign") == "center", "all centered")
        check(a.inner_text("#app-title") == "Alex's house" and a.locator("h1").count() == 1 and a.inner_text("h1") != "Home", "the page title is the treehouse's name, not Home (the nav says Home)")
        check(a.evaluate("() => getComputedStyle(document.querySelector('#app-title')).opacity") == "0", "at the top the title bar doesn't repeat the name")
        a.evaluate("() => window.scrollTo(0, 99999)"); a.wait_for_timeout(600)
        check(a.evaluate("() => getComputedStyle(document.querySelector('#app-title')).opacity") == "1" and a.evaluate("() => document.querySelector('.tl-home-hero').getBoundingClientRect().bottom < 64"),
              "scrolled down, the picture is gone and the name is in the title bar")
        a.evaluate("() => window.scrollTo(0, 0)")
        # Home is where the treehouse is managed: the number, the phones, the other grown-ups. No separate page.
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("[aria-label='Grown-ups']")
        check(all(a.locator(f"[aria-label='{n}']").count() == 1 for n in ("Your number", "Phones", "Grown-ups")),
              "Home has the number, the phones and the grown-ups")
        check(a.locator("[data-change-number]").count() == 1 and a.locator("[data-add-phone]").count() >= 1 and a.locator("[data-add-grownup]").count() == 1
              and a.locator("[data-handset='rename']").count() >= 1, "and a parent can change the number, add or rename a phone, and add a grown-up there")
        check("Pat" in a.inner_text("[aria-label='Grown-ups']") and "(you)" in a.inner_text("[aria-label='Grown-ups']"), "the grown-ups are listed on Home")
        # A number that isn't valid shows the reason, and the button goes back to what it said (it used to stay on "Working").
        a.click("[data-change-number]")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden]) input[name=how]")
        a.click(".tl-sheet-scrim:not([hidden]) label[for=how-1]")
        a.fill(".tl-sheet-scrim:not([hidden]) [name=number]", "0123")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden]) [data-error] .tl-alert")
        btn = a.locator(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        check("Change number" in btn.inner_text() and "Working" not in btn.inner_text() and btn.is_enabled(),
              "a number that isn't valid shows why, and the button goes back to Change number")
        a.keyboard.press("Escape")
        a.goto(f"{BASE}/parent/#/house"); a.wait_for_function("() => location.hash === '#/home'", timeout=5000)
        check(True, "the old treehouse address goes to Home")
        a.click("[data-tl-menu='account-menu']")
        check("Our treehouse" not in a.inner_text("#account-menu"), "the account menu has no treehouse page")
        a.keyboard.press("Escape")
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("[data-this-device]")
        a.click("[data-this-device]")
        a.fill("#dev-name", "My laptop")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("text=My laptop is ready")
        saved = a.evaluate("() => JSON.parse(localStorage.getItem('treeline.phone'))")
        check(bool(saved and saved.get("handset_id") and saved.get("sip_user") and saved.get("secret")), "the browser keeps the new phone's sign-in")
        check(a.locator(".tl-sheet-scrim:not([hidden]) a[href='/phone/']").count() == 1, "there's a link to open the phone")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("text=(this device)")
        check(a.locator("a:has-text('Open the phone on this device')").count() == 1, "it now offers to open the phone instead")
        p2 = a.context.new_page()
        p2.goto(f"{BASE}/phone/")
        p2.wait_for_selector(".tl-rotary", timeout=15000)
        check(p2.locator(".tl-rotary").count() == 1, "the phone opens straight away, with no QR code")
        p2.close()
        a.goto(f"{BASE}/parent/#/actions"); a.wait_for_selector(".tl-row")
        check("Disconnected" in a.inner_text("main") and "again" in a.inner_text("main"), "disconnecting and reconnecting are in the action log")

        # ---- a hostile treehouse name must stay text (stored XSS regression)
        evil = 'a" autofocus onfocus="pwned=1'
        e_ctx, e = make_family(browser, "evil@example.com", evil)
        e.click("[data-skip]")
        e.click("[data-later]")
        e.wait_for_selector("#app-title")
        a.goto(f"{BASE}/parent/#/home")
        code2 = None
        a.evaluate("() => 0")
        # Alex makes a code and the hostile family redeems it, then Alex looks at the request.
        r = a.evaluate("""async () => { const t = localStorage.getItem('treeline.token');
          const res = await fetch('/api/ladder-codes', {method:'POST', headers:{Authorization:'Bearer '+t,'Content-Type':'application/json'}, body:'{}'});
          return (await res.json()).code; }""")
        e.goto(f"{BASE}/parent/#/strings")
        e.wait_for_selector("main [data-redeem]")
        e.click("main [data-redeem]")
        e.fill("#ladder", r)
        e.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        e.wait_for_selector("text=Waiting on them")
        a.reload()
        a.wait_for_selector("text=Waiting on families")
        a.click("[data-string=decline]")
        a.wait_for_selector(".tl-toast")
        check(a.evaluate("window.pwned") is None, "a hostile treehouse name runs no script")
        check(a.locator("[onfocus]").count() == 0, "a hostile treehouse name adds no attributes")
        e_ctx.close()

        # ---- every screen, every width, both themes
        screens = {"home": "#/home", "strings": "#/strings", "calls": "#/calls", "quiet": "#/quiet",
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
                    # The logo and tagline: at the top on a phone (the side rail has them from 768 up).
                    brand_on = a.locator(".tl-app__brandline").is_visible()
                    if theme == "light" and name in ("home", "quiet"):
                        check(brand_on == (width < 768) and (width >= 768 or "Safe calls for neighborhood kids" in a.inner_text(".tl-app__brandline")),
                              f"{name} {width}: the logo and tagline are at the top on a phone, in the rail from 768 up")
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

        # ---- quiet hours: no Save button, everything saves the moment it changes
        def saved(act):
            """Do something, and wait for the save it causes to finish."""
            with a.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/api/treehouse"), timeout=8000):
                act()
        a.goto(f"{BASE}/parent/#/quiet")
        a.wait_for_selector("#quiet-form")
        saved(lambda: a.fill("#qh-start", "21:30"))
        check("9:30 pm" in a.inner_text("#qh-preview"), "quiet hours preview follows the time field")
        check(a.locator("#quiet-form button[type=submit]").count() == 0, "there's no Save button: quiet hours save by themselves")
        a.reload()
        a.wait_for_selector("#qh-start")
        check(a.input_value("#qh-start") == "21:30", "a changed time saved itself")
        # a night, the limits and the switch each save the moment they change
        saved(lambda: a.click("label[for=day-6]"))
        saved(lambda: a.select_option("#longest", "10"))
        saved(lambda: a.select_option("#daily", "60"))
        a.reload(); a.wait_for_selector("#qh-start")
        check(not a.locator("#day-6").is_checked() and a.locator("#day-5").is_checked(), "a night turned off saved itself")
        check(a.input_value("#longest") == "10" and a.input_value("#daily") == "60", "the call limits saved themselves")
        saved(lambda: a.click("label[for=day-6]"))                              # put the night back
        for i in range(6):                                                      # turn nights off one at a time: the last one stays
            saved(lambda i=i: a.click(f"label[for=day-{i}]"))
        a.click("label[for=day-6]"); a.wait_for_selector(".tl-toast:has-text('at least one night')")
        check(a.locator("#day-6").is_checked(), "the last night can't be turned off (turn quiet hours off instead)")
        for i in range(6):                                                      # all back on
            saved(lambda i=i: a.click(f"label[for=day-{i}]"))
        saved(lambda: a.click("#qh-enabled")); a.reload(); a.wait_for_selector("#qh-start")
        check(a.get_attribute("#qh-enabled", "aria-checked") == "false", "the quiet hours switch saved itself")
        saved(lambda: a.click("#qh-enabled")); a.reload(); a.wait_for_selector("#qh-start")
        check(a.get_attribute("#qh-enabled", "aria-checked") == "true", "and turns back on the same way")
        saved(lambda: a.select_option("#longest", "30")); saved(lambda: a.select_option("#daily", ""))   # leave the limits as they were
        on_bg = a.evaluate("() => getComputedStyle(document.querySelector('#qh-enabled')).backgroundImage")
        check(a.get_attribute("#qh-enabled", "aria-checked") == "true" and "gradient" in on_bg,
              "the quiet hours switch shows green when it's on (it looked off, so people turned it off)")
        day_bg = a.evaluate("() => getComputedStyle(document.querySelector('#day-0 + .tl-check__box, #day-0 ~ .tl-check__box')).backgroundImage")
        check("gradient" in day_bg, "a checked night is filled green")

        # ---- a 911 attempt: a danger alert first on Home, and a louder row and a summary in the log.
        # (Real 911 dials are tested with real calls in testphones; here the call and its note go in the database the way
        # the call engine writes them, and the screens are checked.)
        ui_db = os.environ.get("TREELINE_UI_DB")
        if ui_db and os.path.exists(ui_db):
            import sqlite3
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
            db = sqlite3.connect(ui_db, timeout=15)
            tid = db.execute("SELECT id FROM treehouse WHERE name=?", ("Alex's house",)).fetchone()[0]
            db.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,result,reason) VALUES(?,?,?,?,?,?)", (now_iso, tid, "911", "ended", "no_911", "911"))
            db.execute("INSERT INTO notice(treehouse_id,kind,title,body,created_at,key) VALUES(?,?,?,?,?,?)",
                       (tid, "no_911", "Someone tried to call 911", "Someone on Hall phone dialed 911 at Wed 3:42 pm. The call didn't go anywhere.", now_iso, "smoke-911"))
            db.commit(); db.close()
            a.goto(f"{BASE}/parent/#/home")
            a.wait_for_selector(".tl-alert--danger")
            first = a.locator(".tl-alert").first
            check("tried to call 911" in first.inner_text().lower() and "tl-alert--danger" in (first.get_attribute("class") or ""),
                  f"a 911 attempt is the first thing on Home, as a danger alert (first alert: {first.inner_text()[:30]!r}, class {first.get_attribute("class")!r})")
            check(a.locator(".tl-alert--danger [data-href='#/calls']").count() == 1, "and it leads to the call log")
            a.set_viewport_size({"width": 390, "height": 844}); shoot(a, "911-home-390")
            a.goto(f"{BASE}/parent/#/calls")
            a.wait_for_selector(".tl-log--urgent")
            check(a.locator(".tl-log--urgent").count() == 1 and "Tried to call 911" in a.locator(".tl-log--urgent").inner_text(), "the log row for it is marked urgent")
            check(a.locator(".tl-alert--danger").count() == 1 and "tried to call 911" in a.locator(".tl-alert--danger").inner_text().lower(), "and the log opens with a danger summary")
            shoot(a, "911-calls-390")
            urgent_bg = a.evaluate("() => getComputedStyle(document.querySelector('.tl-log--urgent')).backgroundColor")
            check(urgent_bg not in ("rgba(0, 0, 0, 0)", "transparent"), f"the urgent row has its own background ({urgent_bg})")
            a.goto(f"{BASE}/parent/#/home")
            a.wait_for_selector(".tl-alert--danger [data-dismiss]")
            a.click(".tl-alert--danger [data-dismiss]")
            a.wait_for_function("() => !document.querySelector('.tl-alert--danger')", timeout=5000)
            check(True, "a parent can dismiss the note (the call stays in the log)")
        else:
            print("skip  911 alert screens: run through ./dev ui smoke (it gives the test database's path)", flush=True)

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
        check(a.locator("#email").count() == 1 and a.locator("#app-title").count() == 0, "sign out returns to the sign-in screen")
        browser.close()

    if errors:
        print("\nPROBLEMS:")
        for e in dict.fromkeys(errors):
            print(" -", e)
        sys.exit(1)
    print(f"\nall {step[0]} checks passed; screenshots in {SHOTS}")


if __name__ == "__main__":
    main()
