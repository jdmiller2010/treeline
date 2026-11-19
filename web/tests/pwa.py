"""The installable app: one manifest, one service worker, a launcher that opens the right mode, and the install prompts.

  ./dev ui pwa        (a local API on a throwaway database; no phones or calls are needed)
"""
import base64
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


KEY = base64.urlsafe_b64encode(bytes(65)).decode().rstrip("=")           # a well-formed push key, for the carry-over test
# A fake push service: the old worker's scope (/parent/) has a subscription; the new one (/) can subscribe.
def fake_push(permission):
    """The fake push service, with the notification permission set to a given state (this headless browser reports 'denied' whatever is granted)."""
    return FAKE_PUSH.replace("(() => {", "(() => {\n  Object.defineProperty(Notification, 'permission', { configurable: true, get: () => '" + permission + "' });", 1)


FAKE_PUSH = """(() => {
  Object.defineProperty(ServiceWorkerRegistration.prototype, 'pushManager', { configurable: true, get() {
    const old = new URL(this.scope).pathname === '/parent/';
    return { getSubscription: async () => (old ? { endpoint: 'https://push.example/old', toJSON() { return { endpoint: 'https://push.example/old' }; } } : null),
             subscribe: async () => ({ endpoint: 'https://push.example/new', toJSON() { return { endpoint: 'https://push.example/new', keys: { p256dh: 'p', auth: 'a' } }; } }) };
  } });
})();"""
BLOCK_SESSION_STORAGE = "Object.defineProperty(window, 'sessionStorage', { configurable: true, get() { throw new DOMException('denied', 'SecurityError'); } });"
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
        for label, init in (("in a browser tab", FAKE_PHONE), ("in a browser tab with a parent signed in too", FAKE_PHONE + FAKE_TOKEN)):
            ctx, page = new_page(browser, init)
            page.goto(BASE + "/parent/#/settings"); page.wait_for_url("**/phone/*", timeout=8000)
            check(page.evaluate("() => location.pathname") == "/phone/", f"a phone can't open the dashboard {label} either: a new tab doesn't get it out of phone mode")
            ctx.close()
        ctx, page = new_page(browser, FAKE_TOKEN)
        page.goto(BASE + "/parent/"); page.wait_for_selector("#email, #app-title", timeout=8000)
        check(page.evaluate("() => location.pathname") == "/parent/", "a device that is not a phone opens the dashboard as usual")
        other = ctx.new_page(); other.goto(BASE + "/phone/"); other.wait_for_selector(".ph-code")
        other.evaluate(FAKE_PHONE.replace("localStorage.setItem", "localStorage.setItem"))      # this device becomes a phone, in another tab
        page.wait_for_url("**/phone/*", timeout=8000)
        check(page.evaluate("() => location.pathname") == "/phone/", "and a dashboard tab that was already open is sent to the phone the moment the device becomes one")
        ctx.close()

        # ---- install: a phone or tablet in a browser tab is asked to install first; a computer is not
        IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
        IPAD_DESKTOP = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ctx, page = new_page(browser, ua=IPHONE)
        page.goto(BASE + "/phone/"); page.wait_for_selector("#install-page")
        btn = page.locator("[data-install]")
        check(page.inner_text("h1") == "Install Treeline" and btn.count() == 1 and "tl-btn--primary" in btn.get_attribute("class") and btn.inner_text() == "Show me how to install"
              and page.locator("#install-steps").count() == 0, "an iPhone gets one main button, honestly labelled (Apple lets no page install an app), and nothing else")
        btn.click(); page.wait_for_selector("#install-steps")
        txt = page.inner_text("#install-steps")
        check("Apple" in page.inner_text("#install-why"), "and says why there is no one-tap install on an iPhone")
        check("Share" in txt and "Add to Home Screen" in txt, "which shows Share, then Add to Home Screen")
        check(page.locator(".ph-code").count() == 0 and page.locator("[data-parent-login]").count() == 0, "and sees nothing else first: no QR code, no login")
        link = page.locator("[data-browser]")
        check(link.count() == 1 and "tl-btn" not in (link.get_attribute("class") or "") and link.inner_text() == "Use Treeline in your browser instead",
              "with a quiet link, not a button, to use Treeline in the browser instead")
        link.click(); page.wait_for_selector(".ph-code")
        check(page.inner_text("h1") == "Welcome to Treeline" and page.locator("[data-parent-login]").count() == 1 and page.locator(".ph-qr svg").count() == 1,
              "which opens the first screen: the QR code to add a phone, and Log in")
        ctx.close()
        ctx, page = new_page(browser, ua=IPAD_DESKTOP, has_touch=True)      # an iPad asking for the desktop site
        page.add_init_script("Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });")
        page.goto(BASE + "/phone/"); page.wait_for_selector("#install-page")
        check(page.inner_text("h1") == "Install Treeline", "an iPad that asks for the desktop site is still treated as a tablet")
        ctx.close()
        ctx, page = new_page(browser, ua=ANDROID)
        page.goto(BASE + "/phone/"); page.wait_for_selector("#install-page")
        btn = page.locator("[data-install]")
        check(page.inner_text("h1") == "Install Treeline" and btn.count() == 1 and btn.inner_text() == "Install Treeline" and page.locator("#install-steps").count() == 0,
              "Android shows the Install Treeline button straight away")
        btn.click(); page.wait_for_selector("#install-steps")
        check("Install app" in page.inner_text("#install-steps") and len(page.inner_text("#install-why")) > 20,
              "and if the browser doesn't offer to install within a moment, pressing it shows the menu steps and says why there is no one-tap install")
        if not browsers.CHROMIUM_FAMILY:
            print("skip  the install prompt: only Chromium-family browsers fire beforeinstallprompt (Safari installs through Share)", flush=True)
            ctx.close()
        else:
            page.evaluate("""() => { window.__prompted = false; const e = new Event('beforeinstallprompt', { cancelable: true });
              e.prompt = () => { window.__prompted = true; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }""")
            page.wait_for_function("() => !document.querySelector('#install-steps')")
            btn = page.locator("[data-install]")
            check("tl-btn--primary" in btn.get_attribute("class") and btn.inner_text() == "Install Treeline", "once the browser offers to install, the same button is the one main button")
            btn.click(); page.wait_for_function("() => window.__prompted === true")
            check(True, "and tapping it asks the browser to install the app, with no steps")
            page.evaluate("() => window.dispatchEvent(new Event('appinstalled'))")
            page.wait_for_function("() => document.querySelector('#install-page').innerText.includes('is installed')")
            check(page.locator("[data-browser]").count() == 1, "once installed it says so, and the browser link is still there")
            ctx.close()
        # the steps name the right buttons for each device and browser
        ctx, page = new_page(browser)
        page.goto(BASE + "/phone/"); page.wait_for_load_state("networkidle")
        UAS = [
            ("iPhone, Safari", IPHONE, 5, "Safari on your iPhone", ["Share", "bottom of the screen", "Add to Home Screen"]),
            ("iPad, Safari", "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1", 5, "Safari on your iPad", ["top of the screen", "Add to Home Screen"]),
            ("iPad asking for the desktop site", IPAD_DESKTOP, 5, "Safari on your iPad", ["top of the screen"]),
            ("iPhone, Chrome", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/124.0 Mobile/15E148 Safari/604.1", 5, "Chrome on your iPhone", ["Share", "Add to Home Screen"]),
            ("iPhone, Firefox", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/124.0 Mobile/15E148 Safari/605.1.15", 5, "Firefox on your iPhone", ["menu", "Share"]),
            ("iPhone, Instagram's own browser", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 320.0", 5, "A browser inside another app on your iPhone", ["Open in browser", "Safari"]),
            ("Android phone, Chrome", ANDROID, 5, "Chrome on your Android phone", ["Install app", "Add to Home screen"]),
            ("Android tablet, Chrome", "Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", 5, "Chrome on your Android tablet", ["Install app"]),
            ("Android, Samsung Internet", "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0 Mobile Safari/537.36", 5, "Samsung Internet on your Android phone", ["Add page to", "Home screen"]),
            ("Android, Firefox", "Mozilla/5.0 (Android 14; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0", 5, "Firefox on your Android phone", ["Install"]),
            ("Android, Edge", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 EdgA/124.0", 5, "Edge on your Android phone", ["Add to phone"]),
            ("Android, Facebook's own browser", "Mozilla/5.0 (Linux; Android 14; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/450.0]", 5, "A browser inside another app on your Android phone", ["Chrome"]),
        ]
        for label, ua, touch, who, words in UAS:
            r = page.evaluate("""async ([ua, touch]) => { const { device } = await import('/shared/pwa.js'); const { installRecipe } = await import('/shared/install.js');
              const rec = installRecipe(device(ua, touch)); return { who: rec.who, text: rec.items.join(' ').replace(/<[^>]+>/g, '') + ' ' + (rec.note || '') }; }""", [ua, touch])
            check(r["who"] == who and all(w in r["text"] for w in words), f"the steps for {label} name {who} and the right buttons", str(r))
        ctx.close()

        for label, ua in (("an installed app on an iPhone", IPHONE), ("an installed app on Android", ANDROID)):
            ctx, page = new_page(browser, STANDALONE, ua=ua)
            page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code")
            check(page.locator("#install-page").count() == 0 and page.inner_text("#install-slot").strip() == "", f"{label} skips the install page and shows no install prompt")
            ctx.close()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(BASE + "/"); page.wait_for_selector(".ph-code")
        check(page.locator("#install-page").count() == 0 and page.inner_text("h1") == "Welcome to Treeline",
              "a computer skips the install page and opens straight on adding a phone or logging in")
        ctx.close()

        # ---- a parent who had alerts on keeps them: the old worker's push subscription is carried over, not lost
        for granted in (True, False):
            ctx, page = new_page(browser, FAKE_TOKEN + fake_push("granted" if granted else "default"))
            seen = []
            page.route("**/api/push/key", lambda r: r.fulfill(json={"key": KEY}))
            page.route("**/api/push/subscribe", lambda r: (seen.append((r.request.method, r.request.post_data)), r.fulfill(json={"ok": True}))[1])
            page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code")
            page.evaluate("async () => { await navigator.serviceWorker.register('/sw.js', { scope: '/parent/' }); }")          # the old per-app registration
            res = page.evaluate("""async () => {
              const { registerApp, MOVED_PUSH_KEY } = await import('/shared/pwa.js');
              await registerApp();
              const noted = JSON.parse(localStorage.getItem(MOVED_PUSH_KEY) || '[]');
              const { carryOverPush } = await import('/parent/js/push.js');
              const done = await carryOverPush();
              return { noted, done, left: localStorage.getItem(MOVED_PUSH_KEY), scopes: (await navigator.serviceWorker.getRegistrations()).map((r) => new URL(r.scope).pathname) }; }""")
            if granted:
                posted = [b for m, b in seen if m == "POST"]
                deleted = [b for m, b in seen if m == "DELETE"]
                check(res["noted"] == ["https://push.example/old"] and res["scopes"] == ["/"], "retiring the old worker first notes its push subscription", str(res))
                check(res["done"] is True and res["left"] is None and len(posted) == 1 and "push.example/new" in posted[0] and len(deleted) == 1 and "push.example/old" in deleted[0],
                      "and the device is subscribed again under the new worker and the server is told to drop the old one, so alerts don't stop", str((res, seen)))
            else:
                check(res["noted"] == ["https://push.example/old"] and res["done"] is False and res["left"] is None and not seen,
                      "if notifications aren't allowed there is nothing to carry over, and nothing is sent", str((res, seen)))
            ctx.close()

        # ---- blocked storage (a private window, cleared site data) must not blank the app
        ctx, page = new_page(browser, BLOCK_SESSION_STORAGE)
        problems = []
        page.on("pageerror", lambda e: problems.append(str(e)))
        page.goto(BASE + "/parent/"); page.wait_for_selector("#email", timeout=8000)
        page.goto(BASE + "/phone/"); page.wait_for_selector(".ph-code", timeout=8000)
        check(not problems, "with sessionStorage blocked the dashboard's sign-in and the first screen still draw", str(problems))
        ctx.close()
        browser.close()

    # ---- without JavaScript the launcher still leads somewhere (and / no longer redirects)
    with urllib.request.urlopen(BASE + "/", timeout=10) as r:
        page_html = r.read().decode()
        check(r.geturl() == BASE + "/" and 'src="/launch.js"' in page_html and '<noscript>' in page_html and 'href="/phone/"' in page_html,
              "the launcher is served at / (no redirect), and its noscript fallback links to the first screen")

    # ---- ./dev all runs this test
    dev = open(os.path.join(os.path.dirname(__file__), "..", "..", "dev")).read()
    check("cmd_ui pwa" in [t.strip(";") for t in dev.split("cmd_all()")[1].split("\n")[0].replace("; ", ";").split(";") if t.strip()][0:0] or "cmd_ui pwa;" in dev.split("cmd_all()")[1].split("\n")[0],
          "./dev all runs this test")

    # ---- the static-host build carries the same app
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "build_static.py"), "--api", "https://phone.example.com", "--out", out + "/dist"],
                       capture_output=True, text=True)
    dist = out + "/dist"
    have = all(os.path.exists(f"{dist}/{f}") for f in ("index.html", "launch.js", "sw.js", "manifest.webmanifest", "shared/pwa.js", "shared/install.js"))
    check(r.returncode == 0 and have and "launch.js" in open(f"{dist}/index.html").read(), "the static-host build carries the launcher, the worker, the manifest and the shared files", (r.stderr or r.stdout)[-200:])
    hosting = json.load(open(f"{dist}/firebase.json"))["hosting"]["headers"]
    fresh = {h["source"] for h in hosting if {"key": "Cache-Control", "value": "no-cache"} in h["headers"]}
    check({"**/sw.js", "/", "/index.html", "/launch.js", "/manifest.webmanifest"} <= fresh, "and the static host revalidates the worker, the launcher and the manifest on every load", str(fresh))

    print(f"\n{'all ' + str(count[0]) + ' checks passed' if not errors else str(len(errors)) + ' of ' + str(count[0]) + ' checks failed'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
