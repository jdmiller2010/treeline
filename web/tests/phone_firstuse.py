"""A parent makes this device a phone from the dashboard, and the very first call to it must ring on screen and answer;
and the phone's Test audio sheet (microphone level, choosing the microphone and speaker) works and the choice is used.

Reported by hand: the first call after "This device" played the bell but the phone didn't tremble or light up, and lifting
the handset did nothing; after a reload it worked. This drives that exact path with a real call through Asterisk, first with
one tab, then with a second dashboard tab open in the same browser (which also turns into the phone).

Needs the Docker stack:  ./dev web phone_firstuse.py
"""

import time

from playwright.sync_api import sync_playwright

from phone_calls import BASE, Family, Tablet, check, count, errors, string_up

RINGING = "() => document.body.dataset.state === 'ringing' && !!document.querySelector('.is-ringing')"


def make_this_device_a_phone(ctx, family, extra_tab=False):
    """Sign the parent in (their token, as the app keeps it), open Home, and use This device. Returns the page(s) now on /phone/."""
    ctx.add_init_script(f"localStorage.setItem('treeline.token', {family.token!r});")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"dashboard page error: {e}"))
    page.goto(f"{BASE}/parent/#/home")
    page.wait_for_selector("[data-this-device], [data-add-phone]")
    other = None
    if extra_tab:
        other = ctx.new_page()
        other.on("pageerror", lambda e: errors.append(f"second tab page error: {e}"))
        other.goto(f"{BASE}/parent/#/home"); other.wait_for_selector(".tl-home-hero")
    if page.locator("[data-this-device]").count():
        page.click("[data-this-device]")
        page.fill("#dev-name", "This laptop")
    else:                                                        # newer layout: a choice in Add a phone
        page.locator("[data-add-phone]").first.click()
        page.click(".tl-sheet-scrim:not([hidden]) label[for=kind-3]")
        page.fill("#hs-name", "This laptop")
    page.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
    page.wait_for_url("**/phone/**", timeout=15000)
    page.wait_for_selector(".tl-rotary", timeout=15000)
    if other:
        other.reload()                                           # the second tab notices it is a phone now, as it would on its next move
        other.wait_for_url("**/phone/**", timeout=15000); other.wait_for_selector(".tl-rotary", timeout=15000)
    return page, other


def line_up(page):
    """Wait for the phone to be signed in to Asterisk (its light goes steady green)."""
    page.wait_for_function("() => (document.querySelector('#reg')?.textContent || '').includes('is connected')", timeout=30000)


def call_and_answer(caller, callee_page, number, label, other_page=None):
    caller.lift(); caller.wait_phase("dialtone")
    caller.dial(number)
    rang = True
    try:
        callee_page.wait_for_function(RINGING, timeout=20000)
    except Exception:
        rang = False
    elsewhere = bool(other_page and other_page.evaluate(RINGING))
    check(rang, f"{label}: the phone on screen rings (trembles, state ringing)",
          f"state={callee_page.evaluate('() => document.body.dataset.state')} other tab ringing={elsewhere}")
    callee_page.click(".tl-rotary__hook")
    talking = True
    try:
        callee_page.wait_for_function("() => document.body.dataset.state === 'talking'", timeout=15000)
    except Exception:
        talking = False
    check(talking and caller.wait_phase("talking"), f"{label}: lifting the handset answers and both sides are talking")
    if talking:
        time.sleep(3)
        played = callee_page.evaluate("() => { const e = document.getElementById('remote-audio'); return !!e.srcObject && !e.paused && e.currentTime > 0.5; }")
        check(played, f"{label}: the call's audio is playing on the phone that answered")
    callee_page.click(".tl-rotary__hook")                       # hang up
    caller.lift()
    time.sleep(2)


def run(families):
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        alex, sam = Family("first-alex", "First Alex"), Family("first-sam", "First Sam")
        families += [alex, sam]
        string_up(alex, sam)
        caller = Tablet(browser, sam, "Sam tablet")

        # one tab: the dashboard becomes the phone
        ctx = browser.new_context(permissions=["microphone"], viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
        page, _ = make_this_device_a_phone(ctx, alex)
        line_up(page)
        call_and_answer(caller, page, alex.number, "one tab, first call")
        call_and_answer(caller, page, alex.number, "one tab, second call")

        # Test audio: the microphone's level moves (the fake microphone beeps), the choices list the system's devices, and a chosen
        # microphone is kept on this device and used for the next call.
        page.click("#audio-open")
        page.wait_for_selector("#audio:not([hidden]) #mic-track")
        try:
            page.wait_for_function("() => Number(document.querySelector('#mic-track').getAttribute('aria-valuenow')) > 0", timeout=8000)
            moved = True
        except Exception:
            moved = False
        check(moved, "Test audio: the microphone level moves when there is sound")
        inputs = page.locator("#audio-in option").evaluate_all("(os) => os.map((o) => [o.value, o.textContent])")
        check(len(inputs) >= 2 and inputs[0] == ["", "System default"], f"Test audio: the microphones are listed, with System default first ({inputs})")
        if len(inputs) >= 2:
            page.select_option("#audio-in", inputs[1][0])
            saved = page.evaluate("() => JSON.parse(localStorage.getItem('treeline.audio') || '{}')")
            check(saved.get("input") == inputs[1][0], "Test audio: the chosen microphone is kept on this device")
        speaker = page.locator("#audio-out").count()
        check(speaker == 1, "Test audio: this browser can choose the speaker, so the choice is offered")
        page.click("#audio:not([hidden]) [data-tl-close]")
        page.wait_for_selector("#audio", state="hidden")
        call_and_answer(caller, page, alex.number, "one tab, a call with the chosen microphone")
        ctx.close()

        # two tabs in the same browser: both become the phone
        for h in alex.call("GET", "/api/handsets")["handsets"]:
            alex.call("DELETE", f"/api/handsets/{h['id']}")
        ctx = browser.new_context(permissions=["microphone"], viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
        page, other = make_this_device_a_phone(ctx, alex, extra_tab=True)
        # The newest copy (the second tab, which just became the phone) takes it; the first says so instead of silently missing calls.
        line_up(other)
        page.wait_for_selector("#elsewhere:not([hidden])", timeout=10000)
        check("another tab or window" in page.inner_text("#elsewhere"), "two tabs: the older tab steps aside and says the phone is open elsewhere")
        call_and_answer(caller, other, alex.number, "two tabs, the newest tab", other_page=page)
        check(not page.evaluate(RINGING), "two tabs: the tab that stepped aside never rang")
        # "Use it here" takes the phone back
        page.click("#elsewhere-btn")
        line_up(page)
        other.wait_for_selector("#elsewhere:not([hidden])", timeout=10000)
        check(page.locator("#elsewhere").is_hidden(), "Use it here takes the phone back, and the other tab steps aside")
        call_and_answer(caller, page, alex.number, "two tabs, after Use it here", other_page=other)
        ctx.close()


def main():
    families = []
    try:
        run(families)
    finally:
        for f in families:
            try:
                f.call("DELETE", "/api/treehouse", {"confirm": f.house["name"]})
            except Exception:
                pass
    if errors:
        print("\nPROBLEMS:")
        for e in dict.fromkeys(errors):
            print(" -", e)
        raise SystemExit(1)
    print(f"\nall {count[0]} checks passed")


if __name__ == "__main__":
    main()
