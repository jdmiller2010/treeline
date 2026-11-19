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
        # The design guide: a main (canopy) button once per view, and the button beside it is secondary, not quiet.
        page.fill("#email", f"variant-{__import__('time').time_ns()}@example.com"); page.click("#step-email button[type=submit]"); page.wait_for_selector("#step-code:not([hidden])")
        cls = lambda sel: page.locator(sel).get_attribute("class") or ""
        check("tl-btn--secondary" in cls("[data-back-to-email]") and "tl-btn--primary" in cls("#step-code button[type=submit]"),
              "on the sign-in code step, Use a different email is a secondary button beside the one main button")
        page.click("[data-back-to-email]"); page.wait_for_selector("#step-email:not([hidden])")
        check(page.locator("form#step-email").count() == 1 and page.locator("section.tl-card:has(h1):has(.tl-art):has(#email)").count() == 1,
              "the picture, the title and the email box are all in one card")
        for w, h in ((768, 1024), (1024, 768), (1440, 900)):
            page.set_viewport_size({"width": w, "height": h}); page.wait_for_timeout(250)
            card = page.locator("section.tl-card:has(#email)").bounding_box()
            check(abs((card["x"] + card["width"] / 2) - w / 2) < 6 and card["width"] > 300, f"on a {w}px screen the sign-in card is centered on the page, not pushed left ({card['x']:.0f}, {card['width']:.0f})")
            check(abs(page.locator(".tl-footer").first.bounding_box()["x"] + page.locator(".tl-footer").first.bounding_box()["width"] / 2 - w / 2) < 6, f"and so is the footer at {w}px")
            logo = page.locator("img[alt='Treeline']").bounding_box()
            check(abs(logo["x"] - card["x"]) < 4, f"the Treeline logo and tagline stay left-aligned, level with the card's left edge, at {w}px ({logo['x']:.0f} vs {card['x']:.0f})")
        page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
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
        check("tl-btn--secondary" in (a.locator("[data-skip]").get_attribute("class") or "") and "tl-btn--quiet" not in (a.locator("[data-skip]").get_attribute("class") or ""),
              "setup step 3: Skip for now is a secondary button beside the main one")
        gap3 = a.evaluate("() => Math.round(document.querySelector('#setup-body .tl-actions').getBoundingClientRect().top - document.querySelector('[aria-label=\"Kinds of phone\"]').getBoundingClientRect().bottom)")
        check(gap3 < 64, f"setup step 3: the buttons sit right under the list they act on, not floating far below it ({gap3}px)")
        check(a.locator("#setup-body .tl-btn--primary").count() == 1, "setup step 3: one main (canopy) button")
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
        st4 = a.evaluate("""() => { const r = (e) => e.getBoundingClientRect(); const art = r(document.querySelector('.tl-setup-art')), body = r(document.querySelector('#setup-body')), act = r(document.querySelector('#setup-body .tl-actions'));
          return { artMid: Math.round(art.left + art.width / 2), bodyMid: Math.round(body.left + body.width / 2), artW: Math.round(art.width), gap: Math.round(act.top - art.bottom),
                   arts: document.querySelectorAll('#setup-body .tl-art').length, primaries: document.querySelectorAll('#setup-body .tl-btn--primary').length }; }""")
        check(abs(st4["artMid"] - st4["bodyMid"]) < 4 and 160 <= st4["artW"] <= 280 and st4["arts"] == 1 and st4["primaries"] == 1 and st4["gap"] < 64,
              f"setup step 4: one picture, 160-280px wide and centered, the buttons right under it, one main button ({st4})")
        a.click("[data-code]")
        copy_btn = a.locator(".tl-sheet-scrim:not([hidden]) button[type=submit]:has-text('Copy message')")
        done_btn = a.locator(".tl-sheet-scrim:not([hidden]) button[data-tl-close]:has-text('Done')")
        copy_btn.wait_for()
        code = re.search(r"[A-Z2-9]{4}-[A-Z2-9]{4}", a.inner_text(".tl-sheet-scrim:not([hidden])")).group(0)
        check("string code" in a.inner_text(".tl-sheet-scrim:not([hidden])").lower() and "ladder" not in a.inner_text(".tl-sheet-scrim:not([hidden])").lower(), "the new code is called a string code")
        cb, db_ = copy_btn.bounding_box(), done_btn.bounding_box()
        check(a.locator(".tl-sheet-scrim:not([hidden]) .tl-actions").count() == 1 and abs(cb["y"] - db_["y"]) < 4 and cb["x"] < db_["x"],
              f"the string code dialog has one row of buttons, Copy message first with Done beside it ({cb['x']:.0f},{cb['y']:.0f} / {db_['x']:.0f},{db_['y']:.0f})")
        a.wait_for_timeout(600); shoot(a, "string-code-390")
        copy_btn.click(); a.wait_for_timeout(300)
        check(a.locator(".tl-sheet-scrim:not([hidden])").count() == 1, "copying leaves the dialog open")
        done_btn.click()
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
        s.fill("#string-code", code)
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
        check(a.inner_text("#app-title") == "Alex's house" and a.locator("h1").count() == 1 and a.inner_text("h1") == "Home", "the bar shows the treehouse's name; the page's own title, Home, is a hidden h1")
        op = lambda sel: a.evaluate(f"() => getComputedStyle(document.querySelector('{sel}')).opacity")
        check(op("#app-title") == "0" and op(".tl-appbar__lockup") == "1", "at the top the title bar says Treeline, not the name (the big name is right there under the picture)")
        a.evaluate("() => window.scrollTo(0, 99999)"); a.wait_for_timeout(600)
        check(op("#app-title") == "1" and op(".tl-appbar__lockup") == "0" and a.evaluate("() => document.querySelector('.tl-home-hero').getBoundingClientRect().bottom < 64"),
              "scrolled down, the picture is gone and the name has taken the place of the word Treeline")
        bar = a.evaluate("""() => { const r = (s) => document.querySelector(s).getBoundingClientRect(); const b = r('.tl-appbar__brand'), t = r('#app-title'), bar = r('.tl-appbar');
          return { barTop: Math.round(bar.top), brandRight: Math.round(b.right), titleLeft: Math.round(t.left), brandW: Math.round(b.width) }; }""")
        check(bar["barTop"] == 0 and bar["brandW"] > 20 and 0 <= bar["titleLeft"] - bar["brandRight"] <= 24,
              f"the bar stays pinned, with the logo kept and the name next to it ({bar})")
        a.evaluate("() => window.scrollTo(0, 0)"); a.wait_for_timeout(500)
        check(op("#app-title") == "0" and op(".tl-appbar__lockup") == "1", "and back at the top it says Treeline again")
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
        sheet = ".tl-sheet-scrim:not([hidden])"
        not_now, open_phone = a.locator(f"{sheet} button[data-tl-close]:has-text('Not now')"), a.locator(f"{sheet} a[href='/phone/']:has-text('Open the phone')")
        check(not_now.count() == 1 and open_phone.count() == 1 and "tl-btn--primary" in (open_phone.get_attribute("class") or "")
              and "tl-btn--primary" not in (not_now.get_attribute("class") or ""), "Open the phone is the main action and Not now the secondary one")
        # The design system's rule: actions are one row, left-aligned as a group, the primary first, at every width.
        sheet_box = a.locator(f"{sheet} .tl-sheet").bounding_box()
        for width, label in ((390, "on a phone"), (1024, "on a tablet or computer")):
            a.set_viewport_size({"width": width, "height": 800}); a.wait_for_timeout(300)
            nb, ob, sb = not_now.bounding_box(), open_phone.bounding_box(), a.locator(f"{sheet} .tl-sheet").bounding_box()
            check(abs(nb["y"] - ob["y"]) < 4 and ob["x"] < nb["x"], f"{label} the two buttons sit side by side, the main one first ({ob['x']:.0f}/{nb['x']:.0f}, {ob['y']:.0f}/{nb['y']:.0f})")
            check(ob["x"] - sb["x"] < 64 and nb["x"] + nb["width"] < sb["x"] + sb["width"] - 24, f"{label} they are left-aligned as a group, not pushed to the right edge or full width")
        a.set_viewport_size({"width": 390, "height": 844}); a.wait_for_timeout(200)
        # The main action is a real link, and it opens the phone just made (not the pairing QR code page).
        with a.context.expect_page(timeout=8000) as opened:
            open_phone.click()
        phone_tab = opened.value
        phone_tab.wait_for_load_state(); phone_tab.wait_for_timeout(800)
        check(phone_tab.locator(".tl-rotary").count() == 1 and phone_tab.locator(".ph-code").count() == 0,
              "Open the phone opens the phone just made, not the pairing QR code page")
        phone_tab.close()
        check(a.locator(f"{sheet}").count() == 0, "and the dialog closes behind it")
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
        e.fill("#string-code", r)
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
                    if theme == "light" and width in (390, 1280):
                        hb = a.evaluate("""() => ({ name: document.querySelector('#app-title').textContent, pause: document.querySelectorAll('.tl-appbar [data-pause]').length,
                          avatar: document.querySelectorAll('.tl-appbar .tl-avatar-btn').length, avatarH: Math.round(document.querySelector('.tl-appbar .tl-avatar-btn .tl-avatar').getBoundingClientRect().height), pauseH: Math.round(document.querySelector('.tl-appbar [data-pause]').getBoundingClientRect().height), h1s: document.querySelectorAll('h1').length, h1w: document.querySelector('h1').getBoundingClientRect().width,
                          h2: [...document.querySelectorAll('main h2')].filter((h) => h.getBoundingClientRect().width > 2).length,
                          buttonsInBar: [...document.querySelectorAll('.tl-appbar__actions .tl-btn')].map((b) => b.getAttribute('data-pause') !== null ? '' : b.textContent.trim()).filter(Boolean) })""")
                        check(hb["name"] == "Alex's house" and hb["pause"] == 1 and hb["avatar"] == 1 and hb["avatarH"] == hb["pauseH"] and hb["h1s"] == 1 and hb["h1w"] <= 2 and hb["h2"] >= 1 and not hb["buttonsInBar"],
                              f"{name} {width}: the header bar is the same on every page (name, pause, account, the account circle as tall as the pause button); the page's title is hidden and it has its own section titles; no page buttons up in the bar ({hb})")
                    # The logo: in the title bar from the very top on a phone (with the pause button and the avatar on the same row);
                    # the side rail has it from 768 up.
                    if theme == "light" and name in ("home", "quiet"):
                        logo = a.evaluate("""() => { const q = (s) => document.querySelector(s); const r = (e) => e.getBoundingClientRect(); const b = r(q('.tl-appbar__brand')), av = r(q('.tl-appbar .tl-avatar-btn'));
                          const lock = q('.tl-appbar__lockup'); return { brandW: Math.round(b.width), brandMid: Math.round(b.top + b.height / 2), avatarMid: Math.round(av.top + av.height / 2), avatarTop: Math.round(av.top),
                          lockup: lock ? getComputedStyle(lock).display : null, lockupText: lock ? lock.textContent : "" }; }""")
                        if width < 768:
                            check(logo["brandW"] > 20 and logo["avatarTop"] < 40 and abs(logo["brandMid"] - logo["avatarMid"]) < 6,
                                  f"{name} {width}: the logo is in the title bar from the very top, on the same row as the avatar ({logo})")
                            if name == "home":
                                check(logo["lockup"] == "flex" and "Treeline" in logo["lockupText"],
                                      f"home {width}: the bar says Treeline until the name scrolls up to it")
                                # the tagline is whole or left out, never cut off
                                tag = a.evaluate("""() => { const t = document.querySelector('.tl-appbar__lockup .tl-tagline'); const c = getComputedStyle(t); return c.display === 'none' ? 'hidden' : (t.scrollWidth <= t.clientWidth + 1 && t.getBoundingClientRect().right <= document.querySelector('.tl-appbar__text').getBoundingClientRect().right + 1 ? 'whole' : 'cut off'); }""")
                                check(tag in ("whole", "hidden"), f"home {width}: the tagline in the bar is whole or left out, never cut off ({tag})")
                        else:
                            check(logo["brandW"] == 0 and logo["lockup"] != "flex", f"{name} {width}: no logo in the bar (the side rail has it)")
                    if width in (390, 1280) or (name in ("home", "strings") and width in (360, 768, 1024, 1440)):
                        shoot(a, f"{name}-{width}-{theme}")
                # the AppBar title lines up with the first card at wide widths
        # A released number is free to claim again at once, so nothing should talk about it resting.
        a.goto(f"{BASE}/parent/#/settings"); a.wait_for_selector("text=Leave Treeline")
        txt = a.inner_text("main").lower()
        check("year of rest" not in txt and "frees your number" not in txt and "ladder" not in txt, "the Leave Treeline card doesn't talk about a number resting (or ladder codes)")
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
