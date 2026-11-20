# Logos

**Tree + line.** Two treehouses, each in its own tree, joined by a dotted string with a leaf on it. It reads the name literally (trees, and the line between them) and says what the product does: a string between two houses, like a tin-can phone. It's drawn with the same hand as the illustrations (the crowns are the ones from `connection`). Full usage rules (which file where, backgrounds, clear space, minimum sizes, don'ts) are in the brand book under **Logo and app icon**.

| File | Use | Size | Background |
| --- | --- | --- | --- |
| `treeline-logo.svg` | The mark in full color | 96px / 25mm and up | `canvas`, `surface`, white or cream |
| `treeline-lockup.svg` | Mark + "Treeline" wordmark (text already outlined, no font needed): sign-in, onboarding, website and email headers | 160px wide and up | Same as above |
| `treeline-lockup-reversed.svg` | The lockup for dark grounds | 160px wide and up | `night`, Lantern, dark plain grounds |
| `treeline-logo-mono.svg` | One color, ink only | 96px / 25mm and up | Light grounds without color |
| `treeline-logo-reversed.svg` | `on-night` line, `moon` dots and leaf | 96px and up | `night`, Lantern, dark plain grounds |
| `treeline-app-icon.svg` | App icon, 512 × 512, dotted string; export 1024 PNG for stores | 96px and up | Its own `canvas` square |
| `treeline-app-icon-small.svg` | Small icon: no houses, solid string, a touch heavier line | 16–95px, favicon | Its own `canvas` square |
| `treeline-app-icon-night.svg` | Optional dark icon | 96px and up | Its own `night` square |

- Clear space: one left-crown width (about a fifth of the mark) on every side.
- Never on green, sky, sunbeam, berry, a wash, a toned card, a gradient or a photo.

## Exports

Ready-made PNG and ICO files are in the HTML kit under `logo/exports/`: `app-icon-1024.png` for the App Store and Play Store (a full square; the stores round the corners), `app-icon-512.png` and `app-icon-192.png` for a web app manifest (full square, so `"purpose": "any maskable"` is safe: the mark sits inside the 80% safe zone), `apple-touch-icon.png` (180), `favicon.svg`, `favicon.ico` (16, 32, 48), `favicon-16/32/48.png`, and transparent `logo-1200.png` and `lockup-1600.png` for docs and slides.

## Web logo tiles

For websites, social profiles, link previews and any place that needs one self-contained image. Each sits on its own `canvas` rounded tile, like the app icon, so it reads on light and dark pages alike. SVGs open in Inkscape and Illustrator: the lettering is outlined, the washes use `fill-opacity`, and the tile is its own shape (delete it for a transparent logo, light grounds only).

| File | What it is | Sizes |
| --- | --- | --- |
| `treeline-web-logo.svg` | The mark alone on the tile | `treeline-web-logo-120.png`, `-240.png` (square) |
| `treeline-web-logo-name.svg` | The mark with "Treeline" under it | `treeline-web-logo-name-120.png`, `-240.png`, `-512.png`, `-1024.png` (square) |
| `treeline-web-logo-wide.svg` | The mark with "Treeline" beside it | `treeline-web-logo-wide-120h.png`, `-240h.png` (120 and 240 px tall) |

Use the 240 as the 2x image for a 120 slot.
