"""The installable app: one manifest, one service worker, a launcher that opens the right mode, and the install prompts.

  ./dev ui pwa        (a local API on a throwaway database; no phones or calls are needed)
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import urllib.request

from playwright.sync_api import sync_playwright

import browsers

BASE = os.environ.get("BASE", "http://127.0.0.1:8080")
errors, count = [], [0]


def check(cond, what, detail=""):
    count[0] += 1
    print(("ok   " if cond else "FAIL ") + what + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    if not cond:
        errors.append(what)


def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, dict(r.headers), r.read()


def png_size(data):
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def new_page(browser, init=None, ua=None, **kw):
    ctx = browser.new_context(user_agent=ua, viewport={"width": 390, "height": 844}, **kw) if ua else browser.new_context(viewport={"width": 390, "height": 844}, **kw)
    if init:
        ctx.add_init_script(init)
    return ctx, ctx.new_page()


FAKE_PHONE = "localStorage.setItem('treeline.phone', JSON.stringify({sip_user:'hfake', secret:'x', server:'127.0.0.1', ws_url:'ws://127.0.0.1:1/ws', realm:'treeline', handset_id:1}));"
FAKE_TOKEN = "localStorage.setItem('treeline.token', 'not-a-real-token');"
STANDALONE = "sessionStorage.setItem('treeline.test.standalone', '1');"


def main():
    # ---- the manifest: one, for the whole app
    status, headers, body = fetch("/manifest.webmanifest")
    m = json.loads(body)
    check(status == 200 and "manifest+json" in headers.get("Content-Type", ""), "the manifest is served as a web manifest", headers.get("Content-Type", ""))
    check(m["start_url"] == "/" and m["scope"] == "/" and m["display"] == "standalone" and m.get("id") == "/" and m["name"] == "Treeline",
          "it starts at the root, covers the whole app, and opens as an app (no browser bar)", json.dumps({k: m.get(k) for k in ("start_url", "scope", "display", "id")}))
    sizes = {}
    for icon in m["icons"]:
        st, hd, data = fetch(icon["src"])
        sizes[icon["sizes"]] = (st, hd.get("Content-Type"), png_size(data))
    check(sizes.get("192x192") == (200, "image/png", (192, 192)) and sizes.get("512x512") == (200, "image/png", (512, 512)), "its 192 and 512 icons are real PNGs of those sizes", str(sizes))
    check(m["background_color"] and m["theme_color"] and m["short_name"], "it has colors and a short name for the splash screen and the Home Screen")
    for gone in ("/parent/manifest.webmanifest", "/phone/manifest.webmanifest"):
        try:
            fetch(gone); missing = False
        except urllib.error.HTTPError as e:
            missing = e.code == 404
        check(missing, f"the old {gone} is gone")
    st, hd, sw = fetch("/sw.js")
    check(st == 200 and "no-cache" in hd.get("Cache-Control", "") and b"showNotification" in sw, "the one service worker is served fresh and can show notifications", hd.get("Cache-Control", ""))

    with sync_playwright() as p:
        browser = browsers.launch(p)
        print(f"(browser: {browsers.NAME})", flush=True)

        # ---- every page links that one manifest and nothing else
        ctx, page = new_page(browser)
        for path in ("/", "/phone/", "/parent/"):
            page.goto(BASE + path); page.wait_for_load_state("networkidle")
            hrefs = page.evaluate("() => [...document.querySelectorAll('link[rel=manifest]')].map((l) => l.getAttribute('href'))")
            check(hrefs == ["/manifest.webmanifest"], f"{path}: links the one manifest", str(hrefs))
        meta = page.evaluate("() => !!document.querySelector('meta[name=apple-mobile-web-app-capable]') && !!document.querySelector('link[rel=apple-touch-icon]')")
        check(meta, "and is set up to be added to an iPhone or iPad Home Screen (touch icon, app-capable)")
        ctx.close()

        # ---- the launcher opens the right mode for each state of the device
        cases = [("a new device (nothing saved)", None, "/phone/"), ("a parent signed in, not a phone", FAKE_TOKEN, "/parent/"),
                 ("a phone", FAKE_PHONE, "/phone/"), ("a phone with a parent signed in", FAKE_PHONE + FAKE_TOKEN, "/phone/")]
        for label, init, want in cases:
            ctx, page = new_page(browser, init)
            page.goto(BASE + "/"); page.wait_for_url(f"**{want}*", timeout=8000)
            check(page.evaluate("() => location.pathname") == want, f"the app opens {want} for {label}", page.url)
            ctx.close()

        # ---- the first screen: the QR code to add this softphone, and Log in
        ctx, page = new_page(browser)
        page.goto(BASE + "/"); page.wait_for_selector(".ph-code")
        login = page.locator("[data-parent-login]")
        check(page.locator(".ph-qr svg").count() == 1 and login.count() == 1 and login.get_attribute("href") == "/parent/" and "tl-btn--primary" in login.get_attribute("class"),
              "a new device opens on the QR code to add a softphone, with one main button: Log in to the parent dashboard")
        login.click(); page.wait_for_selector("#email")
        check(page.evaluate("() => location.pathname") == "/parent/", "Log in goes to the parent dashboard's sign-in")
        link = page.locator("[data-to-phone]")
        check(link.count() == 1 and link.get_attribute("href") == "/phone/", "which has a way back to the first screen")
        ctx.close()

        # ---- one service worker for everything, and the old per-app ones are retired
        ctx, page = new_page(browser)
        page.goto(BASE + "/phone/"); page.wait_for_load_state("networkidle")
        page.evaluate("async () => { await navigator.serviceWorker.register('/sw.js', { scope: '/parent/' }); }")     # an old per-app registration
        page.goto(BASE + "/"); page.wait_for_selector(".ph-code")
        page.wait_for_function("async () => { const r = await navigator.serviceWorker.getRegistrations(); return r.length === 1 && new URL(r[0].scope).pathname === '/'; }", timeout=10000)
        sw = page.evaluate("async () => { const r = await navigator.serviceWorker.ready; return { scope: new URL(r.scope).pathname, script: new URL((r.active || r.waiting || r.installing).scriptURL).pathname }; }")
        check(sw == {"scope": "/", "script": "/sw.js"}, "there is one service worker for the whole app, and the old per-app ones were retired", str(sw))
        page.reload(); page.wait_for_load_state("networkidle")
        check(page.evaluate("() => !!navigator.serviceWorker.controller"), "and it controls the page after a reload")
        ctx.close()

        # ---- an installed phone stays a phone; in a browser tab nothing is locked
        ctx, page = new_page(browser, FAKE_PHONE + FAKE_TOKEN + STANDALONE)
        page.goto(BASE + "/parent/"); page.wait_for_url("**/phone/*", timeout=8000)
        check(page.evaluate("() => location.pathname") == "/phone/", "an installed app that is a phone can't be opened as the dashboard: it stays the phone")
        ctx.close()
        ctx, page = new_page(browser, FAKE_PHONE)
        page.goto(BASE + "/parent/"); page.wait_for_selector("#email, #app-title", timeout=8000)
        check(page.evaluate("() => location.pathname") == "/parent/", "in a browser tab, the dashboard still opens (nothing is locked there)")
        ctx.close()

        # ---- install: an iPhone is told how, Android gets the prompt, an installed app gets neither
        ctx, page = new_page(browser, ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1")
        page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code")
        txt = page.inner_text("#install-slot")
        check("Add to Home Screen" in txt and page.locator("[data-install]").count() == 0, "an iPhone is told to use Share, then Add to Home Screen", txt[:80])
        ctx.close()
        ctx, page = new_page(browser, ua="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")
        page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code")
        check(page.inner_text("#install-slot").strip() == "", "Android shows nothing until the browser says Treeline can be installed")
        if not browsers.CHROMIUM_FAMILY:
            print("skip  the install prompt: only Chromium-family browsers fire beforeinstallprompt (Safari installs through Share)", flush=True)
            ctx.close()
        else:
            page.evaluate("""() => { window.__prompted = false; const e = new Event('beforeinstallprompt', { cancelable: true });
              e.prompt = () => { window.__prompted = true; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }""")
            page.wait_for_selector("[data-install]")
            page.click("[data-install]"); page.wait_for_function("() => window.__prompted === true")
            page.wait_for_function("() => document.querySelector('#install-slot').innerText.trim() === ''")
            check(True, "then it offers Install Treeline, and asks the browser to install it when tapped")
            ctx.close()
        ctx, page = new_page(browser, STANDALONE, ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1")
        page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code")
        check(page.inner_text("#install-slot").strip() == "", "an installed app shows no install prompt")
        ctx.close()
        browser.close()

    # ---- the static-host build carries the same app
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "build_static.py"), "--api", "https://phone.example.com", "--out", out + "/dist"],
                       capture_output=True, text=True)
    dist = out + "/dist"
    have = all(os.path.exists(f"{dist}/{f}") for f in ("index.html", "launch.js", "sw.js", "manifest.webmanifest", "shared/pwa.js", "shared/install.js"))
    check(r.returncode == 0 and have and "launch.js" in open(f"{dist}/index.html").read(), "the static-host build carries the launcher, the worker, the manifest and the shared files", (r.stderr or r.stdout)[-200:])

    print(f"\n{'all ' + str(count[0]) + ' checks passed' if not errors else str(len(errors)) + ' of ' + str(count[0]) + ' checks failed'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
