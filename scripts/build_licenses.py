#!/usr/bin/env python3
"""Build web/parent/licenses.html and web/phone/licenses.html from
THIRD_PARTY_NOTICES.md, using the design kit's styles.

Run after THIRD_PARTY_NOTICES.md changes:  python3 scripts/build_licenses.py
"""

import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "THIRD_PARTY_NOTICES.md"

PAGE = """<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Open-source licenses · Treeline</title>
<meta name="theme-color" content="#f0e7d3">
<link rel="stylesheet" href="/ui/css/tokens.css">
<link rel="stylesheet" href="/ui/css/treeline.css">
<link rel="icon" href="/ui/logo/exports/favicon.svg" type="image/svg+xml">
</head>
<body class="tl-root" style="margin:0">
<main class="tl-page tl-page--narrow">
<div class="tl-stack tl-stack--sections">
<div class="tl-stack tl-stack--related">
  <a class="tl-btn tl-btn--quiet tl-btn--sm" href="{back}"><span class="tl-btn__label">‹ Back</span></a>
  <h1 class="display-md">Open-source licenses</h1>
</div>
{body}
<p class="caption" style="color:var(--ink-muted)">© 2026 Jordan Miller · <a href="mailto:jdmiller2010@gmail.com" style="color:inherit">jdmiller2010@gmail.com</a> · <a href="https://buymeacoffee.com/jdmiller" style="color:inherit">Support Treeline</a> · Open-source licenses</p>
</div>
</main>
</body>
</html>
"""


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}" rel="noopener">{m.group(1)}</a>', text)
    return text


def render(md):
    out, lines, i = [], md.splitlines(), 0
    section = None
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            i += 1
            continue
        if line.startswith("## "):
            if section:
                out.append("</section>")
            section = True
            out.append(f'<section class="tl-stack"><h2 class="title-lg">{inline(line[3:])}</h2>')
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            out.append('<div class="tl-card"><div class="tl-stack tl-stack--group">')
            for r in body:
                out.append('<dl class="tl-dl">')
                for k, v in zip(head, r):
                    out.append(f'<div class="tl-dl__row"><dt>{inline(k)}</dt><dd>{inline(v)}</dd></div>')
                out.append("</dl>")
            out.append("</div></div>")
            continue
        elif line.startswith("- "):
            out.append('<ul class="tl-measure">')
            while i < len(lines) and lines[i].startswith("- "):
                out.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif line.strip():
            out.append(f'<p class="tl-measure">{inline(line)}</p>')
        i += 1
    if section:
        out.append("</section>")
    return "\n".join(out)


def main():
    body = render(SRC.read_text())
    for app, back in (("parent", "/parent/#/about"), ("phone", "/phone/")):
        path = ROOT / "web" / app / "licenses.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(PAGE.format(body=body, back=back))
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
