"""Which browser a test drives. Set BROWSER to one of:

  chromium   (default) what Chrome, and Chrome on Android, are built on. Uses the headless shell installed with Playwright.
  msedge     Microsoft Edge itself (needs Edge installed: `playwright install msedge`, or a Windows/Ubuntu CI runner).
  webkit     the engine Safari is built on (`playwright install webkit`). It is the nearest automated stand-in for Safari, but it is
             not Safari and not iOS: installing to the Home Screen, push, the microphone prompt and the audio session need a real device.
  firefox    (`playwright install firefox`)

  BROWSER=webkit ./dev ui pwa
"""
import glob
import os

NAME = os.environ.get("BROWSER", "chromium").lower()
CHROME = os.environ.get("CHROME") or next(iter(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))), None)


def launch(p, **kw):
    if NAME == "chromium":
        return p.chromium.launch(executable_path=CHROME, **kw)
    if NAME == "msedge":
        return p.chromium.launch(channel="msedge", **kw)
    if NAME == "webkit":
        return p.webkit.launch(**kw)
    if NAME == "firefox":
        return p.firefox.launch(**kw)
    raise SystemExit(f"BROWSER={NAME!r}: use chromium, msedge, webkit or firefox")


# Chromium and Edge share an engine; things only they have (the install prompt event) are checked only there.
CHROMIUM_FAMILY = NAME in ("chromium", "msedge")
