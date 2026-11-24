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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import browsers

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
            if m.type in ("error", "warning") and "Failed to load resource" not in m.text
            and "AudioContext was not allowed to start" not in m.text and "WebSocket" not in m.text else None)   # (the phone page, with no Asterisk here and no tap yet)
    page.on("pageerror", lambda e: errors.append(f"{label} page error: {e}"))
    # A request cut off by the next click or the page closing is not a failure.
    page.on("requestfailed", lambda r: errors.append(f"{label} request failed: {r.url} ({r.failure})")
            if r.failure != "net::ERR_ABORTED" else None)


def api_get(page, path):
    """A GET to the API as whoever is signed in on this page."""
    return page.evaluate("""async (p) => { const t = localStorage.getItem('treeline.token').replace(/"/g, '');
      return (await fetch(p, { headers: { Authorization: 'Bearer ' + t } })).json(); }""", path)


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


DOODLE_JS = """() => {
  const ds = [...document.querySelectorAll('.tl-doodle[data-doodle]')];
  const text = [...document.querySelectorAll('.tl-card__title,.tl-card__eyebrow,.tl-card__body,.tl-btn,input,select,textarea,a,h1,h2,p,.tl-row__title,.tl-tag,.tl-steps__label,.tl-steps__summary')];
  const textRects = (el) => { const out = [], w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { if (!w.currentNode.nodeValue.trim()) continue; const g = document.createRange(); g.selectNodeContents(w.currentNode); out.push(...g.getClientRects()); } return out; };
  const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 3 && a.bottom > b.top + 3;
  const bad = [];
  for (const d of ds) {
    const r = d.getBoundingClientRect();
    if (d.getAttribute('aria-hidden') !== 'true' || getComputedStyle(d).pointerEvents !== 'none') bad.push('not inert');
    for (const t of text) {
      if (d.contains(t)) continue;
      const solid = t.matches('.tl-btn,input,select,textarea,a,.tl-tag');
      const rects = solid ? [t.getBoundingClientRect()] : textRects(t);
      if (rects.some(q => hit(r, q))) bad.push(d.dataset.doodle + ' over ' + (t.textContent || t.tagName).trim().slice(0, 24));
    }
  }
  return { n: ds.length, bad, wide: document.documentElement.scrollWidth > innerWidth + 1,
           sig: ds.map(d => d.dataset.doodle + Math.round(d.getBoundingClientRect().left / 12)).sort().join(',') };
}"""

LAYOUT_JS = """() => {
  const layer = document.querySelector('.tl-doodle-layer');
  const snap = () => [...document.body.querySelectorAll('*')].filter(e => !e.closest('.tl-doodle-layer') && !e.classList.contains('tl-doodle-layer'))
    .map(e => { const r = e.getBoundingClientRect(); return [e.tagName, Math.round(r.left * 10), Math.round(r.top * 10), Math.round(r.width * 10), Math.round(r.height * 10)].join(); })
    .concat([document.documentElement.scrollWidth, document.documentElement.scrollHeight].join()).join('|');
  const inTree = document.querySelectorAll('main .tl-doodle, .tl-card .tl-doodle, #app .tl-doodle').length;
  const withDoodles = snap();
  if (layer) layer.style.display = 'none';
  const without = snap();
  if (layer) layer.style.display = '';
  return { same: withDoodles === without, inTree, layers: document.querySelectorAll('.tl-doodle-layer').length };
}"""

def doodle_check(page, where):
    page.wait_for_timeout(700)
    r = page.evaluate(DOODLE_JS)
    check(not r["bad"] and not r["wide"], f"doodles on {where} stay off text and controls, take no room, and never scroll the page sideways" + (f" ({r['bad'][:2]})" if r["bad"] else ""))
    pc = page.evaluate("""() => { const all = [...document.querySelectorAll('.tl-card')].filter(c => c.offsetParent && !c.parentElement.closest('.tl-card'));
      const is = c => /tl-card--(breeze|blossom|oak|fern|seeds|maple)/.test(c.className);
      let run = 0, worst = 0; for (const c of all) { run = is(c) ? run + 1 : 0; worst = Math.max(worst, run); }
      return { n: all.length, painted: all.filter(is).length, run: worst }; }""")
    check(pc["painted"] <= max(1, pc["n"] // 3) and pc["run"] < 3, f"on {where}, painted cards are reasonable ({pc['painted']} of {pc['n']}, longest run {pc['run']})")
    inside = page.evaluate("""() => [...document.querySelectorAll('.tl-doodle-layer > *')].filter(d => { const r = d.getBoundingClientRect(), cy = r.top + r.height / 2, cx = r.left + r.width / 2;
      return [...document.querySelectorAll('.tl-card')].some(c => { const q = c.getBoundingClientRect(); return cx > q.left && cx < q.right && cy > q.top + 6 && cy < q.bottom - 6; }); }).length""")
    check(inside == 0, f"on {where}, no doodle is drawn inside a card")
    lay = page.evaluate(LAYOUT_JS)
    check(lay["same"] and lay["inTree"] == 0, f"on {where}, every element is exactly where it would be without the doodles, and none are inside the app's own markup")
    check(lay["layers"] <= 1, f"on {where}, there is only ever one doodle layer")
    return r

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
    check(email in page.inner_text("[data-setting-up-as]"), f"{name}: setup says whose account the treehouse will belong to (R6-1)")
    shoot(page, "setup-step1-390")
    page.fill("#th-name", name)
    page.fill("#th-you", "Pat")
    page.click("button[type=submit]")
    page.wait_for_selector("#ack")
    page.wait_for_timeout(900)
    page.mouse.wheel(0, 500); page.wait_for_timeout(250)
    top = page.evaluate("() => Math.round(document.querySelector('.tl-stepsnav--pinned').getBoundingClientRect().top)")
    check(abs(top) <= 1 and page.evaluate("() => window.scrollY") > 100, f"{name}: the setup string stays pinned to the top while the page scrolls ({top}px)")
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=f"{SHOTS}/setup-step2-pinned-390.png")           # the viewport as it is, to see the pinned string over the page
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(300)
    page.screenshot(path=f"{SHOTS}/setup-step2-pinned-1280.png")
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0, 0)")
    check(page.locator("button[type=submit]").is_disabled(), f"{name}: can't continue without the 911 box")
    page.click("label[for=ack]")
    check(page.locator("button[type=submit]").is_disabled(), f"{name}: one box isn't enough, the privacy box is needed too")
    page.click("label[for=consent]")
    page.click("button[type=submit]")
    page.wait_for_selector("[data-skip]")
    return ctx, page


def admin_pages(browser, a, s, central, tdb, ui_db):
    """Treeline Admin (docs/ADMIN.md): the menu link only for an admin, the pages, the sign-in-again page for an old session, and a log
    read through the REAL helper code (this script plays root, in the folders ./dev gave the local API) with a hostile line in it."""
    import json as _json
    import time as _time
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy", "native", "bin"))
    import treeline_bridge
    bridge = os.path.join(os.path.dirname(ui_db), "bridge")
    req, out = os.path.join(bridge, "req"), os.path.join(bridge, "out")
    # Sam is not an admin: no link, and the page is not there for them
    s.goto(f"{BASE}/parent/#/home"); s.wait_for_selector(".tl-avatar-btn"); s.click(".tl-avatar-btn")
    check(s.locator("[data-admin-link]").count() == 0, "the account menu has no Treeline Admin link for someone who is not an admin")
    s.keyboard.press("Escape")
    s.goto(f"{BASE}/parent/#/admin"); s.wait_for_timeout(800)
    check("#/home" in s.url, "and #/admin sends them home")
    check(api_get(s, "/api/admin/admins").get("error") == "That page isn't here.", "the API gives them what an unknown address gets")
    tdb.add_admin(central, "alex@example.com", "ssh:smoke")
    a.goto(f"{BASE}/parent/"); a.wait_for_selector(".tl-avatar-btn")             # a full load, so /api/me is asked again
    a.click(".tl-avatar-btn")
    check(a.locator("[data-admin-link]").is_visible(), "an admin's account menu has Treeline Admin")
    a.click("[data-admin-link]"); a.wait_for_selector("text=For running Treeline")
    check(a.locator(".tl-row[data-href]").count() == 5, "the overview lists Treehouses, Logs, Releases, Admins and the audit log")
    a.wait_for_timeout(600)
    check(a.locator(".tl-doodle-layer svg").count() == 0, "no doodles on the admin pages (working screens)")
    check(a.locator("h1").count() == 1, "one h1 on the admin overview")
    for w in WIDTHS:
        a.set_viewport_size({"width": w, "height": 900}); a.wait_for_timeout(150)
        no_sideways_scroll(a, f"admin overview {w}")
    a.set_viewport_size({"width": 390, "height": 844})
    shoot(a, "admin-overview-390")
    # Logs, through the real helper, with a line that would be markup if it were ever set as HTML
    a.goto(f"{BASE}/parent/#/admin/logs"); a.wait_for_selector("#log-form")
    check(a.locator(".tl-alert--warning").count() == 0, "with the helper's folders present the page does not say it is missing")
    a.select_option("#log-since", "6h")
    a.click("[data-show]")
    deadline = _time.time() + 10
    while not os.listdir(req) and _time.time() < deadline:
        _time.sleep(0.1)
    hostile = 'started <img src=x onerror="window.__xss=1"> from 203.0.113.7 for parent@example.com\n' * 3
    done = treeline_bridge.run_once(os.getuid(), req_dir=req, out_dir=out, audit_path=os.path.join(bridge, "audit.log"),
                                    journal=lambda r: (hostile, False))
    check(len(done) == 1 and done[0][1] == "ok", f"the page's request is one the real helper accepts ({done})")
    a.wait_for_selector(".tl-logview")
    text = a.inner_text(".tl-logview")
    check("<img src=x" in text and a.locator(".tl-logview img").count() == 0 and not a.evaluate("() => window.__xss"),
          "a log line that looks like markup is shown as text, never run")
    check("203.0.113.7" not in text and "parent@example.com" not in text and "[ip]" in text and "[email]" in text, "addresses and emails are hidden")
    for w in WIDTHS:
        a.set_viewport_size({"width": w, "height": 900}); a.wait_for_timeout(150)
        no_sideways_scroll(a, f"admin logs {w}")
    for theme in ("light", "dark"):
        a.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
        a.set_viewport_size({"width": 390, "height": 844}); shoot(a, f"admin-logs-390-{theme}")
        a.set_viewport_size({"width": 1280, "height": 900}); shoot(a, f"admin-logs-1280-{theme}")
    a.evaluate("() => document.documentElement.removeAttribute('data-theme')")
    a.set_viewport_size({"width": 390, "height": 844})
    # Releases: what the helper last reported
    rep = {"current": "v0.2.0", "previous": None, "failed": [], "asterisk": "24.0.0-t1", "error": None,
           "published": [{"version": "v0.3.0", "published_at": "2026-11-24T10:00:00Z", "newer": True, "failed": False},
                         {"version": "v0.2.0", "published_at": "2026-11-22T02:58:38Z", "newer": False, "failed": False}]}
    import subprocess as _sp
    treeline_bridge.refresh_releases(out_dir=out, run=lambda *x, **k: _sp.CompletedProcess(x, 0, _json.dumps(rep), ""))
    a.goto(f"{BASE}/parent/#/admin/releases"); a.wait_for_selector("text=Published")
    body = a.inner_text("main")
    check("v0.3.0" in body and "Newer" in body and "Running" in body and "24.0.0-t1" in body, "Releases shows what runs and what is newer")
    shoot(a, "admin-releases-390")
    a.goto(f"{BASE}/parent/#/admin/admins"); a.wait_for_selector("text=alex@example.com")
    check("ssh:smoke" in a.inner_text("main"), "Admins lists who added whom")
    a.goto(f"{BASE}/parent/#/admin/audit"); a.wait_for_selector(".tl-row")
    check("log" in a.inner_text("main").lower(), "the audit log has the log view")
    # Adding and removing an admin: refused until a fresh sign-in (the emailed code stands in for Google here), then done
    a.goto(f"{BASE}/parent/#/admin/admins"); a.wait_for_selector("#add-admin")
    check(a.locator(".tl-btn--primary").count() == 1, "one main button on the Admins page")
    a.fill("#admin-email", "helper@example.com"); a.click("#add-admin button[type=submit]")
    a.wait_for_selector("#stepup-form")
    check(not tdb.is_admin(central, "helper@example.com"), "nothing changes before the fresh sign-in")
    code = re.search(r"(\d{6})", a.inner_text("#stepup-dev")).group(1)
    a.fill("#stepup-code", code); a.click("#stepup-form button[type=submit]")
    a.wait_for_selector("text=helper@example.com is an admin")
    a.wait_for_selector("[data-admin='helper@example.com']")
    check(tdb.is_admin(central, "helper@example.com"), "after it, the admin is added")
    a.click("[data-remove='helper@example.com']"); a.wait_for_selector("[data-yes]")
    a.click("[data-yes]"); a.wait_for_selector("text=helper@example.com is no longer an admin")
    check(not tdb.is_admin(central, "helper@example.com"), "and removed again, without a second sign-in inside the 15 minutes")
    check(a.locator("[data-remove]").count() == 0, "the last admin has no Remove button")
    shoot(a, "admin-admins-390")
    # Treehouses: find Sam's, pause it, see what Sam sees, bring it back (inside the step-up's 15 minutes)
    try:
        a.evaluate("() => sessionStorage.removeItem('tl-admin-q')")
    except Exception:
        pass
    a.goto(f"{BASE}/parent/#/admin/treehouses"); a.wait_for_selector("#th-search")
    a.fill("#th-q", "sam@example.com"); a.click("#th-search button[type=submit]")
    a.wait_for_selector("text=Sam's house")
    check(a.locator(".tl-btn--primary").count() == 1, "one main button on Treehouses")
    a.click("text=Sam's house"); a.wait_for_selector("#archive-form")
    detail = a.inner_text("main")
    check("sam@example.com" in detail and "Phone 1" in detail or "No phones" in detail, "the detail lists the grown-ups and the phones by position")
    for w in WIDTHS:
        a.set_viewport_size({"width": w, "height": 900}); a.wait_for_timeout(120)
        no_sideways_scroll(a, f"admin treehouse {w}")
    a.set_viewport_size({"width": 390, "height": 844}); shoot(a, "admin-treehouse-390")
    a.fill("#archive-confirm", "Sam's house"); a.select_option("#archive-reason", "cleanup")
    a.click("#archive-form button[type=submit]"); a.wait_for_selector("text=Sam's house is paused")
    sam_tid = central.execute("SELECT id FROM treehouse WHERE name=?", ("Sam's house",)).fetchone()[0]
    check(tdb.archived_treehouse(central, sam_tid) is not None, "the treehouse is archived")
    s.goto(f"{BASE}/parent/"); s.wait_for_selector("text=Treeline has paused Sam's house for now")
    check("911" in s.inner_text("main") and s.locator("[data-paused-signout]").count() == 1 and s.locator("#paused-delete").count() == 1,
          "Sam sees a plain paused page that says Treeline never connects to 911, and can still sign out or delete")
    s.wait_for_timeout(500)
    check(s.locator(".tl-doodle-layer svg").count() == 0 and s.locator("h1").count() == 1, "the paused page has one h1 and no doodles")
    shoot(s, "paused-family-390")
    a.wait_for_selector("[data-restore]"); a.click("[data-restore]"); a.wait_for_selector("text=Sam's house is back")
    s.goto(f"{BASE}/parent/#/home"); s.wait_for_selector("[data-pause]")
    check(tdb.archived_treehouse(central, sam_tid) is None, "brought back: Sam's home works again")
    # Installing a release from the page (still inside the 15 minutes of the step-up above): the real root helper with the agent replaced
    rep2 = {"current": "v0.2.0", "previous": None, "failed": [], "asterisk": "24.0.0-t1", "error": None,
            "published": [{"version": "v0.3.0", "published_at": "2026-11-24T10:00:00Z", "newer": True, "failed": False},
                          {"version": "v0.2.0", "published_at": None, "newer": False, "failed": False}]}
    treeline_bridge.refresh_releases(out_dir=out, run=lambda *x, **k: _sp.CompletedProcess(x, 0, _json.dumps(rep2), ""))
    a.goto(f"{BASE}/parent/#/admin/releases"); a.wait_for_selector("[data-install='v0.3.0']")
    check(a.locator("[data-install]").count() == 1, "only the newer release has an Install button")
    a.click("[data-install='v0.3.0']"); a.wait_for_selector("[data-yes]")
    check("never cut" in a.inner_text("[data-confirm]"), "the confirmation says calls are never cut and it rolls back by itself")
    a.click("[data-yes]")
    dreq = os.path.join(bridge, "deploy-req")
    deadline = _time.time() + 10
    while not os.listdir(dreq) and _time.time() < deadline:
        _time.sleep(0.1)
    asked = []
    def fake_agent(cmd, **k):
        asked.append(cmd)
        if cmd[1:] == ["releases"]:
            return _sp.CompletedProcess(cmd, 0, _json.dumps(rep2), "")
        return _sp.CompletedProcess(cmd, 0, "<b>switched</b> from 203.0.113.4\nv0.3.0 is healthy", "")
    outcome = treeline_bridge.deploy_once(os.getuid(), req_dir=dreq, out_dir=out, run=fake_agent, audit_path=os.path.join(bridge, "audit.log"),
                                          state_path=os.path.join(bridge, "deploy-state.json"))
    check(outcome == "healthy" and asked[-1] == ["/usr/local/sbin/treeline-deploy", "--version", "v0.3.0", "--wait", "600"],
          f"the page's request makes the helper run the agent with that version only ({outcome}, {asked[-1:]})")
    a.wait_for_selector("text=v0.3.0 is installed and healthy", timeout=15000)
    out_text = a.inner_text("[data-output]")
    check("<b>switched</b>" in out_text and a.locator("[data-output] b").count() == 0 and "203.0.113.4" not in out_text,
          "the machine's answer is shown as text, cleaned")
    shoot(a, "admin-releases-installed-390")
    # An admin session older than 12 hours: one plain page, not a loop
    token = a.evaluate("() => localStorage.getItem('treeline.token').replace(/\"/g, '')")
    import hashlib
    central.execute("UPDATE session SET created_at='2000-01-01T00:00:00+00:00' WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
    a.goto(f"{BASE}/parent/#/admin/logs"); a.wait_for_selector("text=Sign in again to use the admin page")
    a.wait_for_timeout(1500)
    check(a.locator("text=Sign in again to use the admin page").count() == 1 and "#/admin/logs" in a.url, "an old session gets one sign-in-again page, not a loop")
    check(a.locator("[data-resignin]").count() == 1, "with a button that signs out")
    central.execute("UPDATE session SET created_at=? WHERE token_hash=?", (tdb.iso(), hashlib.sha256(token.encode()).hexdigest()))
    a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("[data-pause]")


def main():
    with sync_playwright() as p:
        browser = browsers.launch(p)

        # ---- sign-in
        anon = browser.new_context(viewport={"width": 390, "height": 844})
        page = anon.new_page()
        watch(page, "anon")
        page.goto(f"{BASE}/parent/")
        page.wait_for_selector("#email")
        check("Treeline can't call 911" in page.inner_text("body") or "can't call 911" in page.inner_text("body"), "sign-in says plainly that 911 isn't available")
        check(page.locator("a[href='/privacy/']").count() >= 1, "the sign-in page links to the public privacy policy (Google checks the home page for it)")
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
        # ---- sign in with Google (production's screen): the server's config is stubbed, because the real Google is not reachable here
        gctx = browser.new_context(viewport={"width": 390, "height": 844})
        gp = gctx.new_page()
        watch(gp, "google")
        gp.route("**/api/auth/config", lambda r: r.fulfill(json={"google": True, "email_code": False, "dev": False}))
        gp.route("**/api/auth/beta", lambda r: r.fulfill(status=400, json={"error": "That code didn't work. Check it and try again, or ask whoever gave it to you.", "code": "bad_beta_code"}))
        gp.goto(f"{BASE}/parent/")
        gp.wait_for_selector("[data-google]")
        check(gp.locator("#email").count() == 0 and gp.locator("#step-email").count() == 0, "with Google on and the emailed code off, there is no email form")
        check(gp.locator("[data-google]").count() == 1 and gp.locator("button.tl-btn--primary").count() == 1, "one main button: Continue with Google")
        check(not gp.locator("#step-beta").is_visible(), "the beta code form stays folded away until someone says they are new")
        gp.click("#new-here summary")
        gp.fill("#beta", "AAAA-AAAA"); gp.click("#step-beta button[type=submit]")
        gp.wait_for_selector("#beta-error .tl-alert")
        check("didn't work" in gp.inner_text("#beta-error"), "a wrong beta code says so and does not leave the page")
        no_sideways_scroll(gp, "google sign-in 390")
        gp.goto(f"{BASE}/parent/#/signin/e.need_code"); gp.reload(); gp.wait_for_selector("#google-box .tl-alert")
        check("beta code" in gp.inner_text("#google-box"), "coming back from Google without being set up explains what to do")
        shoot(gp, "signin-google-390")
        gctx.close()

        # ---- the public privacy policy: the link Google's sign-in setup asks for, readable without signing in
        pctx = browser.new_context(viewport={"width": 390, "height": 844})
        pp = pctx.new_page()
        watch(pp, "privacy")
        pp.goto(f"{BASE}/privacy/")
        pp.wait_for_selector("#policy h2")
        body = pp.inner_text("main")
        check(pp.locator("h1").count() == 1 and "Privacy and safety" in pp.inner_text("h1"), "the privacy policy opens without signing in, with one h1")
        for words in ("never records", "What does Treeline get from Google?", "Amazon Web Services", "Delete everything", "can't call 911", "@gmail.com"):
            check(words in body, f"the privacy policy covers: {words}")
        check(pp.locator("#policy details").count() == 0, "on the public page every answer is open, not folded away")
        check(pp.locator(".tl-footer a[href='/privacy/']").count() == 1, "its footer links back to it, with the contact address")
        no_sideways_scroll(pp, "privacy 390")
        shoot(pp, "privacy-390")
        pctx.close()
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
        sheet = ".tl-sheet-scrim:not([hidden])"
        done_btn = a.locator(f"{sheet} button[data-tl-close]:has-text('Done')")
        a.wait_for_selector(f"{sheet} .tl-qr__svg")
        code = re.search(r"[A-Z2-9]{4}-[A-Z2-9]{4}", a.inner_text(f"{sheet} [data-code]")).group(0)
        check("string code" in a.inner_text(sheet).lower() and "ladder" not in a.inner_text(sheet).lower(), "the new code is called a string code")
        check(a.inner_text(f"{sheet} .tl-sheet__title") == "New string connection" and a.locator(f"{sheet} .tl-qr__svg").count() == 1
              and a.locator(f"{sheet} #string-code").count() == 1, "one sheet: a QR code, your code, and a box for theirs")
        a.wait_for_timeout(600)                                        # let the sheet finish sliding up before measuring
        connect_btn = a.locator(f"{sheet} button[type=submit]:has-text('Connect')")
        cb, db_ = connect_btn.bounding_box(), done_btn.bounding_box()
        check(a.locator(f"{sheet} .tl-actions").count() == 1 and abs(cb["y"] - db_["y"]) < 4 and cb["x"] < db_["x"],
              f"the sheet has one row of buttons, Connect first with Done beside it ({cb['x']:.0f},{cb['y']:.0f} / {db_['x']:.0f},{db_['y']:.0f})")
        check(a.evaluate("document.activeElement && document.activeElement.id !== 'string-code'"), "opening the sheet doesn't pop the keyboard (the QR code stays in view)")
        a.wait_for_timeout(600); shoot(a, "string-code-390")
        a.click(f"{sheet} [data-copy]"); a.wait_for_timeout(300)
        check(a.locator(sheet).count() == 1, "copying leaves the sheet open")
        a.click(f"{sheet} button[type=submit]"); a.wait_for_selector(f"{sheet} .tl-alert")
        check("their string code" in a.inner_text(f"{sheet} .tl-alert").lower(), "Connect with nothing typed asks for their code")
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
        check(s.locator(".tl-art:not(.tl-leafdiv__sprig)").count() == 1 and s.locator(".tl-empty__art").count() == 0,
              "and one picture on the screen: the treehouse at the top")
        # With a phone but no strings, Home invites a friend's family on a seeds card (a seed on its way), and the text clears the painting.
        s.evaluate("""async () => { await fetch('/api/handsets', { method: 'POST', headers: { 'Content-Type': 'application/json',
          Authorization: 'Bearer ' + localStorage.getItem('treeline.token') }, body: JSON.stringify({ kind: 'ata', name: 'Hall phone' }) }); }""")
        s.reload(); s.wait_for_selector(".tl-card--seeds [data-make-code]")
        check(s.locator(".tl-card--seeds .tl-card__title").inner_text() == "Invite a friend's family", "with a phone and no strings, Home invites a friend's family on a seeds card")
        s.set_viewport_size({"width": 390, "height": 900}); s.wait_for_timeout(300)
        shoot(s, "home-invite-seeds-390")
        s.goto(f"{BASE}/parent/#/phonebook"); s.wait_for_selector(".tl-card--blossom")
        shoot(s, "phonebook-blossom-390")
        s.goto(f"{BASE}/parent/#/strings")
        s.wait_for_selector("main .tl-grove")
        check(s.locator("main .tl-grove__node--me").count() == 1 and s.locator("main .tl-grove button.tl-grove__node").count() == 0, "with no strings the map shows only your own treehouse")
        s.click("main [data-connect]")
        s.fill("#string-code", code)
        s.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        s.wait_for_selector("main .tl-grove__node[data-state=wait]")
        check("waiting" in s.inner_text("main").lower() and s.locator("main .tl-grove__node[data-state=wait] .tl-grove__name").inner_text() == "Alex's house",
              "Sam's request waits on Alex, and Alex's treehouse hangs on the map as waiting")

        # Alex approves from Home.
        a.goto(f"{BASE}/parent/#/home")
        a.reload()
        a.wait_for_selector("text=Waiting on families")
        shoot(a, "home-waiting-390")
        check("Sam's house" in a.inner_text("main"), "Alex sees Sam's request")
        a.click("[data-string=approve]")
        a.wait_for_selector(".tl-toast")
        a.goto(f"{BASE}/parent/#/strings")
        a.wait_for_selector(".tl-grove__node[data-state=live]")
        check(a.locator(".tl-grove__node[data-state=live] .tl-grove__name").inner_text() == "Sam's house", "the string is live on the map")
        a.click(".tl-grove__node[data-state=live]")
        a.wait_for_selector("main [data-detail] .tl-card")
        check("Strung" in a.inner_text("main"), "tapping a house shows its string")
        # The map is real buttons on a drawing that scales: nothing scrolls sideways, every house is a thumb-sized target with its name as text.
        vp0 = a.viewport_size
        for w in (360, 768, 1280):
            a.set_viewport_size({"width": w, "height": 900}); a.wait_for_timeout(250)
            m = a.evaluate("""() => { const c = document.querySelector('.tl-grove').getBoundingClientRect(), n = [...document.querySelectorAll('button.tl-grove__node')].map((b) => b.getBoundingClientRect());
              return { sideways: document.documentElement.scrollWidth > innerWidth, min: Math.min(...n.map((r) => Math.min(r.width, r.height))), inside: n.every((r) => r.left >= c.left - 1 && r.right <= c.right + 1),
                       named: [...document.querySelectorAll('button.tl-grove__node')].every((b) => b.getAttribute('aria-label') && b.querySelector('.tl-grove__name').textContent.length > 0) }; }""")
            check(not m["sideways"] and m["min"] >= 44 and m["inside"] and m["named"], f"the map at {w}px: nothing scrolls sideways, houses are 44px+ buttons inside it, each named ({m})")
        # A crowded grove: 7 to 12 families, drawn in a throwaway block, never overlap (houses, tags) or leave the drawing, at phone and desktop widths.
        for w in (360, 1280):
            a.set_viewport_size({"width": w, "height": 900})
            for n in (7, 9, 10, 12):
                bad = a.evaluate("""(n) => { const names = ['The Okafors','The Nguyens','The Hartleys','The Morenos','The Lindqvists','The Brightwater family','The Abernathys','The Castillos','The Yamadas','The Pembertons','The Ellisons','The Fitzgeralds'];
                  const st = ['live','live','paused','ask','wait','live','live','paused','live','wait','live','live'];
                  const box = document.createElement('div'); box.id = 'crowd'; box.innerHTML = TLGrove.html({ me: { name: 'The Parks', number: '3317' }, friends: names.slice(0, n).map((x, i) => ({ id: i, name: x, number: String(2000 + i * 137), state: st[i] })) });
                  document.querySelector('main').appendChild(box); const c = box.querySelector('.tl-grove').getBoundingClientRect(), rs = [];
                  box.querySelectorAll('.tl-grove__node').forEach((nd, i) => { rs.push([i + 't', nd.querySelector('.tl-grove__tag').getBoundingClientRect()]); rs.push([i + 'h', nd.querySelector('.tl-house__canopy').getBoundingClientRect()]); });
                  const bad = []; rs.forEach(([k, r]) => { if (r.left < c.left - 1 || r.right > c.right + 1 || r.top < c.top - 1 || r.bottom > c.bottom + 1) bad.push('out ' + k); });
                  for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) { const a = rs[i][1], b = rs[j][1]; if (parseInt(rs[i][0]) === parseInt(rs[j][0])) continue;
                    if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2) bad.push(rs[i][0] + '/' + rs[j][0]); }
                  box.remove(); return bad; }""", n)
                check(not bad, f"{n} families at {w}px: no houses or name tags overlap and none leave the drawing ({bad})")
        # The kit never draws more than twelve houses (the page shows a list from the thirteenth family).
        more = a.evaluate("""() => { const f = Array.from({ length: 15 }, (_, i) => ({ id: i, name: 'Family ' + i, number: String(2000 + i), state: i === 14 ? 'ask' : i % 2 ? 'paused' : 'live' }));
          const box = document.createElement('div'); box.innerHTML = TLGrove.html({ me: { name: 'Me', number: '1' }, friends: f });
          return { nodes: box.querySelectorAll('button.tl-grove__node').length, more: box.querySelectorAll('[data-more]').length }; }""")
        check(more["nodes"] == 12 and more["more"] == 0, f"fifteen families: the kit draws twelve houses and no overflow button ({more})")
        a.set_viewport_size({"width": 390, "height": 900}); a.wait_for_timeout(250); shoot(a, "strings-map-390")
        a.set_viewport_size(vp0)

        # Scanning the QR code is opening its link: the same as typing the code and pressing Connect. The sheet on the other phone closes by itself.
        a.goto(f"{BASE}/parent/#/strings"); a.wait_for_selector("main [data-connect]")
        a.click("main [data-connect]"); a.wait_for_selector(".tl-sheet-scrim:not([hidden]) .tl-qr__svg")
        scan = a.inner_text(".tl-sheet-scrim:not([hidden]) [data-code]")
        f_ctx, f = make_family(browser, "fern@example.com", "Fern's house")
        f.click("[data-skip]"); f.click("[data-later]"); f.wait_for_selector("#app-title")
        f.goto(f"{BASE}/parent/#/string/{scan}")
        f.wait_for_selector("main .tl-grove__node[data-state=wait]")
        check(f.evaluate("location.hash") == "#/strings" and f.locator(".tl-toast").count() >= 1, "opening a string link sends the request and lands on Strings")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden])", state="detached", timeout=15000)
        a.wait_for_selector("main .tl-grove__node[data-state=ask]")
        check(a.locator("main .tl-grove__node[data-state=ask] .tl-grove__name").inner_text() == "Fern's house", "Alex's sheet closed when Fern scanned, and Fern's house is on the map waiting for Alex")
        f_ctx.close()

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
        r = doodle_check(a, "Home"); shoot(a, "doodles-home-390")
        a.goto(f"{BASE}/parent/#/quiet"); a.wait_for_selector("#quiet-form")
        sigs = set()
        for _ in range(8):
            a.reload(); a.wait_for_selector("#quiet-form"); r = doodle_check(a, "Quiet hours"); sigs.add(r["sig"])
        check(len(sigs) > 1, "the doodles are drawn differently on each load of the same page")
        shoot(a, "doodles-quiet-390")
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
        # no parent code yet: the dialog asks for one (twice), and checks it, before the phone is made
        check(a.locator(".tl-sheet-scrim:not([hidden]) #dev-new").count() == 1 and a.locator(".tl-sheet-scrim:not([hidden]) #dev-new").get_attribute("type") == "password",
              "with no parent code yet, making this device a phone asks for one (hidden, numeric)")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden]) [data-error] .tl-alert")
        check("4 to 6 digits" in a.inner_text(".tl-sheet-scrim:not([hidden]) [data-error]"), "an empty code is refused with the rule")
        a.fill("#dev-new", "2468"); a.fill("#dev-again", "2469")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_function("() => document.querySelector('.tl-sheet-scrim:not([hidden]) [data-error]').innerText.includes(\"don't match\")")
        check(len(api_get(a, "/api/handsets")["handsets"]) == 1, "two codes that differ are refused, and no phone is made")
        a.fill("#dev-new", "2468"); a.fill("#dev-again", "2468")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_url("**/phone/**", timeout=15000)
        a.wait_for_selector(".tl-rotary", timeout=15000)
        saved = a.evaluate("() => JSON.parse(localStorage.getItem('treeline.phone'))")
        check(bool(saved and saved.get("handset_id") and saved.get("sip_user") and saved.get("secret")), "the browser keeps the new phone's sign-in")
        check(a.locator(".ph-code").count() == 0, "and goes straight to the phone it just made, with no QR code and no extra dialog")
        # A device that is a phone can't get out by going somewhere else: the dashboard, in this tab or a new one, sends it back to the phone.
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_url("**/phone/**", timeout=8000)
        a.wait_for_selector(".tl-rotary")
        check(a.evaluate("() => location.pathname") == "/phone/", "going to the dashboard in the same tab lands back on the phone")
        for path in ("/parent/#/settings", "/parent/#/strings", "/parent/"):
            tab = a.context.new_page(); tab.goto(f"{BASE}{path}"); tab.wait_for_url("**/phone/**", timeout=8000); tab.wait_for_selector(".tl-rotary")
            check(tab.evaluate("() => location.pathname") == "/phone/", f"a new tab on {path} lands on the phone, signed in as a parent or not")
            tab.close()
        # (The parent code on the phone is what ends this: phone_ui.py tests that. Here the browser just forgets the phone, to carry on with the dashboard.)
        a.evaluate("() => localStorage.removeItem('treeline.phone')")
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("[aria-label='Phones']")
        check(a.evaluate("() => location.pathname") == "/parent/", "once it isn't a phone any more the dashboard opens again")
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
        e.wait_for_selector("main [data-connect]")
        e.click("main [data-connect]")
        e.fill("#string-code", r)
        e.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        e.wait_for_selector("main .tl-grove__node[data-state=wait]")
        a.reload()
        a.wait_for_selector("text=Waiting on families")
        a.click("[data-string=decline]")
        a.wait_for_selector(".tl-toast")
        check(a.evaluate("window.pwned") is None, "a hostile treehouse name runs no script")
        check(a.locator("[onfocus]").count() == 0, "a hostile treehouse name adds no attributes")
        e_ctx.close()

        # ---- every screen, every width, both themes
        screens = {"home": "#/home", "strings": "#/strings", "calls": "#/calls", "quiet": "#/quiet",
                   "phonebook": "#/phonebook", "profile": "#/profile", "privacy": "#/privacy", "about": "#/about", "actions": "#/actions"}
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
        # ---- Home's parent code card
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("[data-parent-code]")
        pc = a.locator("section.tl-card:has([data-parent-code])")
        check("A parent code is set" in pc.inner_text() and pc.locator(".tl-card__title").inner_text() == "Parent code" and pc.locator("[data-parent-code]").inner_text() == "Change parent code"
              and "tl-btn--primary" not in pc.locator("[data-parent-code]").get_attribute("class"), "Home has a Parent code card that says the code is set, with a Change button")
        pc.locator("[data-parent-code]").click(); a.wait_for_selector(".tl-sheet-scrim:not([hidden]) #pc-current")
        a.fill("#pc-current", "0000"); a.fill("#pc-new", "135790"); a.fill("#pc-again", "135790")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector(".tl-sheet-scrim:not([hidden]) [data-error] .tl-alert")
        check("isn't the parent code" in a.inner_text(".tl-sheet-scrim:not([hidden]) [data-error]"), "changing it needs the current code: a wrong one is refused")
        a.fill("#pc-current", "2468")
        a.click(".tl-sheet-scrim:not([hidden]) button[type=submit]")
        a.wait_for_selector("text=The parent code was changed")
        check(True, "with the current code it changes")
        check(a.locator(".tl-sheet-scrim:not([hidden])").count() == 0, "and the dialog closes")
        shoot(a, "settings-parent-code-390")
        # ---- Settings is part of Home: the old address lands there, the quiet hours page has no pause switch, the phone book has a tab
        a.goto(f"{BASE}/parent/#/settings"); a.wait_for_function("() => location.hash === '#/home'", timeout=5000)
        check(a.locator("#house-form").count() == 1, "the old Settings address goes to Home, which now holds the treehouse settings")
        a.goto(f"{BASE}/parent/#/quiet"); a.wait_for_selector("#quiet-form")
        check(a.locator("#pause").count() == 0, "the quiet hours page has no pause switch (the title bar has the pause button)")
        a.goto(f"{BASE}/parent/#/phonebook"); a.wait_for_selector(".tl-nav a[aria-current=page]:has-text('Phone book')")
        check(a.locator(".tl-nav a[aria-current=page]").inner_text().strip() == "Phone book", "the phone book is a tab in the main navigation")
        a.goto(f"{BASE}/parent/#/profile"); a.wait_for_selector("h2:has-text('You')")
        check(a.locator("[data-parent-code], #house-form").count() == 0 and a.locator("[data-sign-out-btn]").count() == 1, "the profile page is only about the signed-in person")
        # ---- the account menu offers to install the app, once the browser says it can
        a.click("[data-tl-menu='account-menu']")
        check(not a.locator("[data-install-app]").is_visible(), "the account menu has no Install the app while the browser hasn't offered it")
        if browsers.CHROMIUM_FAMILY:
            a.evaluate("""() => { window.__prompted = false; const e = new Event('beforeinstallprompt', { cancelable: true });
              e.prompt = () => { window.__prompted = true; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }""")
            a.wait_for_selector("[data-install-app]:visible")
            check("Install the app" in a.inner_text("#account-menu"), "once it can, the account menu shows Install the app")
            a.click("[data-install-app]"); a.wait_for_function("() => window.__prompted === true")
            check(True, "and choosing it asks the browser to install")
            a.evaluate("() => window.dispatchEvent(new Event('appinstalled'))")
            a.wait_for_function("() => document.querySelector('[data-install-app]').hidden")
            check(True, "after it is installed the item goes away")
        a.keyboard.press("Escape")
        # A released number is free to claim again at once, so nothing should talk about it resting.
        a.goto(f"{BASE}/parent/#/home"); a.wait_for_selector("text=Leave Treeline")
        # Shortening how long call records are kept deletes the older ones at once, so the page says so before it is saved.
        a.wait_for_selector("#set-keep")
        warn = a.locator("[data-keep-warning]")
        check(warn.is_hidden(), "the retention warning is hidden while the time is unchanged")
        was = a.input_value("#set-keep")
        a.select_option("#set-keep", "7")
        check(warn.is_visible() and "7 days" in warn.inner_text() and "right away" in warn.inner_text() and "backups" in warn.inner_text()
              and "tl-alert--warning" in (warn.locator(".tl-alert").get_attribute("class") or ""), "a shorter time shows a warning: removed right away, backups take up to a week")
        a.select_option("#set-keep", "365")
        check(warn.is_hidden(), "a longer time shows no warning")
        a.select_option("#set-keep", was)
        txt = a.inner_text("main").lower()
        check("year of rest" not in txt and "frees your number" not in txt and "ladder" not in txt, "the Leave Treeline card doesn't talk about a number resting (or ladder codes)")
        # ---- a sitter: pause, the quiet-hours switch, disconnect and ring a phone, today's calls. Nothing else.
        a.evaluate("""async () => { const t = localStorage.getItem('treeline.token').replace(/"/g, '');
          const r = await fetch('/api/grown-ups', { method: 'POST', headers: { Authorization: 'Bearer ' + t, 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'sitter@example.com', name: 'Sam the sitter', role: 'sitter' }) });
          if (!r.ok) throw new Error(await r.text()); }""")
        sit_ctx = browser.new_context(viewport={"width": 1280, "height": 900}); sit = sit_ctx.new_page(); watch(sit, "sitter")
        sign_in(sit, "sitter@example.com")
        sit.wait_for_selector(".tl-home-hero"); sit.wait_for_selector("[data-handset-switch]")
        n = lambda sel: sit.locator(sel).count()
        check(n("[data-add-phone]") == 0 and n("[data-this-device]") == 0 and n("[data-change-number]") == 0 and n("[data-add-grownup]") == 0,
              "a sitter's Home has no Add a phone, Use this device, Change number or Add a grown-up")
        menu = sit.locator("button[aria-label^='More for']").first
        menu.click()
        check(n("[data-handset='ring']") >= 1 and n("[data-handset='rename']") == 0 and n("[data-handset='remove']") == 0, "a phone's menu offers only the ring test to a sitter (no rename, no remove)")
        sit.keyboard.press("Escape")
        switch = sit.locator("[data-handset-switch]").first
        switch.click(); sit.wait_for_selector("text=is disconnected")
        check(sit.locator("[data-handset-switch]").first.get_attribute("aria-checked") == "false", "a sitter can disconnect a phone")
        sit.locator("[data-handset-switch]").first.click(); sit.wait_for_selector("text=is connected again")
        sit.click("[data-pause]"); sit.wait_for_selector("text=Calls are paused")
        check(True, "and pause all calls")
        sit.click("[data-pause]"); sit.wait_for_selector("text=Calls are back on")
        sit.goto(f"{BASE}/parent/#/quiet"); sit.wait_for_selector("#qh-enabled")
        check(not sit.locator("#qh-enabled").is_disabled() and all(sit.locator(sel).first.is_disabled() for sel in ("#qh-start", "#qh-end", "#day-0", "#longest", "#daily")),
              "on Quiet hours a sitter gets the on/off switch, and the times, nights and limits are locked")
        with sit.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/api/treehouse"), timeout=8000) as resp:
            sit.click("#qh-enabled")
        check(resp.value.status == 200, "and the switch works for a sitter")
        with sit.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/api/treehouse"), timeout=8000):
            sit.click("#qh-enabled")
        sit.goto(f"{BASE}/parent/#/calls"); sit.wait_for_selector("text=Call log")
        check(n("input[name=calls-range]") == 0 and n("[data-export]") == 0 and "today's calls" in sit.inner_text("main").lower(), "a sitter's call log is today only: no range choice, no export")
        sit.goto(f"{BASE}/parent/#/home"); sit.wait_for_selector("text=Notifications")
        check("Action log" not in sit.inner_text("main") and sit.locator("#house-form, [data-parent-code], [data-leave]").count() == 0, "a sitter's Home has no action log, treehouse form, parent code or leave button")
        sit.goto(f"{BASE}/parent/#/actions"); sit.wait_for_function("() => location.hash === '#/home'", timeout=5000)
        check(True, "and the action log's address goes to Home")
        sit_ctx.close()
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
        # (Real 911 dials are tested with real calls in testphones; here the call and its note go in the way the call
        # engine writes them: a ledger row copied into the family's own file by households.record_call, and a note in
        # that file. This script runs on the host, so it uses the same code the server does, pointed at the same files.)
        ui_db = os.environ.get("TREELINE_UI_DB")
        if ui_db and os.path.exists(ui_db):
            from datetime import datetime, timezone
            os.environ["TREELINE_DB"] = ui_db                     # assigned, not setdefault: the households sit next to it
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "controller"))
            from treeline import db as tdb, households
            now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
            central = tdb.connect(ui_db)
            tid = central.execute("SELECT id FROM treehouse WHERE name=?", ("Alex's house",)).fetchone()[0]

            def attempt(dialed="911", result="no_911", reason="911"):
                cid = central.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,ended_at,result,reason) VALUES(?,?,?,?,?,?,?)",
                                      (now_iso, tid, dialed, "ended", now_iso, result, reason)).lastrowid
                households.record_call(central, cid)
            attempt()
            households.add_notice(tid, "no_911", "Someone tried to call 911", "Someone on Hall phone dialed 911 at Wed 3:42 pm. The call didn't go anywhere.", "smoke-911")
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
            # ---- a long history is paged: 50 at a time under "All", with a Show older button
            for i in range(60):
                attempt(dialed=f"{1000 + i}", result="not_in_service", reason="no_such_number")
            a.goto(f"{BASE}/parent/#/calls"); a.wait_for_selector("input[name=calls-range]")
            a.click("label:has(input[value=all])"); a.wait_for_selector("[data-show-older]")
            check(a.locator(".tl-log").count() == 50, f"All shows the newest 50 calls ({a.locator('.tl-log').count()})")
            a.click("[data-show-older]")
            a.wait_for_function("() => document.querySelectorAll('.tl-log').length > 50")
            check(a.locator(".tl-log").count() == 61 and a.locator("[data-show-older]").count() == 0,
                  f"Show older loads the rest (all 61) and the button goes away ({a.locator('.tl-log').count()})")
            a.click("label:has(input[value=week])"); a.wait_for_selector(".tl-log")
            check(a.locator(".tl-log").count() == 61 and a.locator("[data-show-older]").count() == 0, "This week shows them all at once")
            admin_pages(browser, a, s, central, tdb, ui_db)
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
