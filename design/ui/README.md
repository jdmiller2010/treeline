# Treeline UI — plain HTML components

Framework-free building blocks for Treeline, matching the Treeline design system exactly. The markup in `components/` is generated from the same components the design system previews, so the classes and structure are identical.

## Use it

```html
<html lang="en" data-theme="light">  <!-- "dark" for the Lantern theme -->
<head>
  <link rel="stylesheet" href="treeline-ui/css/tokens.css">
  <link rel="stylesheet" href="treeline-ui/css/treeline.css">
</head>
<body>
  …paste components here…
  <script src="treeline-ui/js/treeline.js"></script>  <!-- only needed for switches -->
</body>
</html>
```

- `css/tokens.css`: every color (both themes), type style, space, radius, shadow and size as CSS variables, plus a class per type style (`.display-lg`, `.body`, `.caption`…).
- `css/treeline.css`: every component, the watercolor recipes (`--tl-bloom-sun`, `--tl-dusk`, `--tl-fade-line`…), artwork styles and the leaf loader. Fraunces and Figtree are self-hosted from `fonts/` (variable WOFF2, Latin and Latin Extended, SIL Open Font License), so nothing loads from Google and the app works offline.
- `js/treeline.js`: opens and closes menus (`data-tl-menu="panel-id"`, arrow keys, Escape), shows toasts (`TreelineUI.toast("Saved", { tone, action, onAction })` or `data-tl-toast="…"` on a button), removes dismissed alerts (`data-tl-dismiss`), shows and hides passwords (`data-tl-password`), runs code boxes (`data-tl-code`: auto-advance, Backspace, paste), keeps sliders and textarea counters in step (`data-tl-slider`, `data-tl-count`), switches tabs (`data-tl-tabs`, arrow keys), makes `.tl-switch` toggle (fires `tl-change` with `event.detail.checked`), opens and closes sheets (`data-tl-open="id"`, `data-tl-close`, the scrim, Escape) and switches list and detail panes on narrow screens (`data-tl-detail` rows, `.tl-listdetail__back`).
- **Every page needs a size container.** Use the app shell (`.tl-app`, see `app.html`) or put `class="tl-root"` on `<body>`. Components respond to the width they're given, so without one the phone rules never kick in.
- `LAYOUT.md`: the spacing, sizing, alignment, app layout and phone-versus-desktop rules, with the layout classes that apply them (`.tl-page`, `.tl-stack`, `.tl-cluster`, `.tl-split`, `.tl-grid`, `.tl-actions`, `.tl-measure`).

## App shell: what you must know

These notes are the ones that break a screen if skipped. The full rules are in `LAYOUT.md` (sections 6, 9, 10 and 11) and in `components/AppShell.md`, `NavBar.md`, `AppBar.md`, `Sheet.md`, `ListDetail.md` and `PageTemplates.md`.

1. **Every page sits in a size container.** Signed-in screens use the shell (`.tl-app` › `.tl-app__layout` › `header.tl-appbar`, `main.tl-app__main`, `nav.tl-nav`). Any other page puts `class="tl-root"` on `<body>`. Components respond to the width they're given; without a container the phone rules never apply.
2. **Two sizes, two jobs.** The shell follows the window: bottom tabs under 768, icon rail 768–1023, sidebar 1024 and up. Everything in the page follows the content area: narrow under 600, regular 600–959, wide 960 and up. A 1100px laptop gets the sidebar and regular-width content, on purpose.
3. **Keep `.tl-app__layout`.** The grid lives one level inside `.tl-app` because a container can't restyle itself. Markup without it won't switch layouts.
4. **Sheets go outside main,** as the last child of `.tl-app`. Inside main they're trapped by its containment and can't cover the bar or tabs. Ship them closed with `hidden`; open with `data-tl-open="id"`; close with `data-tl-close`, the scrim or Escape.
5. **Same four nav items, same order:** Home, Friends, Calls, Quiet hours, as links with `aria-current="page"` on the current one. Settings lives behind the avatar on phones and in the sidebar footer on desktop.
6. **One `h1` per screen, in the AppBar.** Pages start with an `h2.title-lg` section or a card. At most two actions in the bar; give Buttons there `tl-btn--collapse` so they go icon-only on phones.
7. **Toasts and sheets live outside main.** Put `<div class="tl-toasts" aria-live="polite"></div>` and any sheets as the last children of `.tl-app`. Don't add `backdrop-filter`, `transform` or `filter` to the AppBar, or the phone account menu can't cover the screen.
8. **Add `viewport-fit=cover`** to the viewport meta tag. Bottom tabs and sheets pad for the home indicator.
9. **Pick a template:** Overview, List and detail, Settings form or Focused task (`components/PageTemplates.html`). `app.html` uses all four, plus the account menu, an alert, the call filter, a time range, a select and toasts.
10. **Test at 360, 390, 768, 1024, 1280 and 1440,** in both themes. Nothing may scroll sideways, and the AppBar title must sit right above the first card.

## Logo and illustrations

- **Logo:** `logo/README.md` says which file goes where. In short: the app icon at 96px and up, the small icon below 96px and for the favicon, the lockup for headers (160px wide minimum), reversed on dark grounds. Keep one crown's width clear all round. Never on green, sky, sunbeam, berry, washes, toned cards, gradients or photos.
- **Illustrations:** `illustrations/README.md`. One per screen, 160–280px, centered above the title with `space-6` between, on `canvas` or a `surface` card only. Inline the markup from `components/Illustration.html` so they follow the theme; the SVG files are Daylight-only.
- The brand book (the design system's README) has the full rules, and its **BrandUsage** page shows them.

## Files

| Folder | What |
| --- | --- |
| `app.html` | A working app screen: shell, nav, four pages, list and detail, and a sheet. Resize the window to see phone, tablet and desktop. |
| `index.html` | Gallery of every component and variant, live, with copyable HTML and a theme toggle. Open it in a browser. |
| `components/*.html` | Ready-to-paste markup for each component, one block per variant. `components/Layout.html` is a full screen built from the layout classes. |
| `components/*.md` | The rules for each component (what it's for, how it behaves on phones and desktop, do's and don'ts) with the same markup. |
| `icons/*.svg` | The 19 line icons, drawn in `currentColor`. Inline them to color with CSS. |
| `illustrations/*.svg` | Spot illustrations and the animated leaf loader, in Daylight colors. Use the inline markup in `components/Illustration.html` for theme-aware art. |
| `logo/exports/` | Ready-made exports: `app-icon-1024.png` (App Store and Play Store, full square), `app-icon-512.png` and `app-icon-192.png` (web app manifest, full square so they mask safely), `apple-touch-icon.png` (180), `favicon.svg`, `favicon.ico` (16, 32, 48) and PNGs, `logo-1200.png` and `lockup-1600.png` (transparent, for docs and slides). |
| `fonts/` | Self-hosted Fraunces and Figtree, with their licenses. |
| `logo/*.svg` | The Treeline logo: full color, lockup with the wordmark, one-color, reversed, and app icons (regular for 56px and up, small for 48px and down and the favicon, optional night). Rules in `logo/README.md`. |

## Rules that keep it matching

- Keep the class names and nesting exactly as in `components/`. Change only text, `id`s, `href`s and `aria-label`s.
- Ids in the snippets (`quiet-hours`, `kid-name`…) are examples: give each instance a unique id and keep `label for` / `aria-describedby` pointing at it.
- Switch state lives in `aria-checked` plus the `is-on` class; set both, or call `TreelineUI.setSwitch(button, true)`.
- Variants are modifier classes: `tl-btn--primary`, `tl-tag--sky`, `tl-card--night`, `tl-presence--sunbeam`, and so on.
- Lay out with the layout classes and their gaps, not margins on components (see `LAYOUT.md`).
- Use tokens for anything new (`var(--space-6)`, `var(--surface)`), never raw values, so both themes keep working.
