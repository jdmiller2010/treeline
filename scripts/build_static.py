#!/usr/bin/env python3
"""Build the parent app and the softphone as plain files for a static host
(Firebase Hosting, GitHub Pages, any bucket).

  python3 scripts/build_static.py --api https://phone.example.com [--out dist]

The API and Asterisk still run on your server (see docs/DEPLOY.md). This only
moves the web pages. On the server, set TREELINE_CORS_ORIGINS to the static
site's address so the pages may call the API.
"""

import argparse
import json
import pathlib
import shutil
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
UI_KEEP = ("css", "js", "fonts", "logo")          # the parts of design/ui the apps use


def build(api, out):
    parsed = urlparse(api)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise SystemExit("--api must be an https address with no path, like https://phone.example.com")
    api = f"https://{parsed.netloc}"
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for app in ("parent", "phone", "shared"):
        shutil.copytree(ROOT / "web" / app, out / app)
    for f in ("index.html", "launch.js", "sw.js", "manifest.webmanifest"):          # the launcher, the one worker and the one manifest
        shutil.copy(ROOT / "web" / f, out / f)
    for part in UI_KEEP:
        shutil.copytree(ROOT / "design" / "ui" / part, out / "ui" / part)
    shutil.copy(ROOT / "design" / "LICENSE-ASSETS.txt", out / "ui" / "LICENSE-ASSETS.txt")
    (out / "config.js").write_text(f'// Written by scripts/build_static.py\nwindow.TREELINE_API_BASE = {json.dumps(api)};\n')
    (out / "404.html").write_text('<!doctype html><meta charset="utf-8"><title>Not here</title>'
                                  '<p style="font-family:sans-serif;padding:2rem">That page isn\'t here. <a href="/parent/">Open Treeline</a></p>\n')
    (out / ".nojekyll").write_text("")
    host = parsed.netloc
    csp = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
           f"font-src 'self'; connect-src 'self' https://{host} wss://{host}; media-src 'self' blob:; "
           "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    headers = [{"key": "Content-Security-Policy", "value": csp}, {"key": "X-Content-Type-Options", "value": "nosniff"},
               {"key": "Referrer-Policy", "value": "no-referrer"}]
    (out / "firebase.json").write_text(json.dumps({"hosting": {
        "public": ".", "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
        "headers": [{"source": "**", "headers": headers},
                    # the worker, the launcher and the manifest are always revalidated, so a deploy reaches devices at once
                    *[{"source": src, "headers": [{"key": "Cache-Control", "value": "no-cache"}]}
                      for src in ("**/sw.js", "/", "/index.html", "/launch.js", "/manifest.webmanifest")]]}}, indent=2) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    out = build(args.api, args.out)
    print(f"built {out}  ({sum(1 for f in out.rglob('*') if f.is_file())} files)\n"
          f"set TREELINE_CORS_ORIGINS on the server to your static site's address")
