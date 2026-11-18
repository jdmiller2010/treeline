# Treeline design system: notes for Claude Code

This folder is the Treeline design system. Build every parent-app screen from it; don't invent new styles.

- `ui/` is the plain-HTML kit: `css/tokens.css` + `css/treeline.css` (self-hosted fonts in `fonts/`), `js/treeline.js` (menus, sheets, toasts, tabs, code boxes, sliders, password toggle), `components/*.html` (exact markup for every variant) and `components/*.md` (the rules for each). `ui/app.html` is a working screen that uses the shell and all four page templates. Open `ui/index.html` to see everything.
- `system/` is the source: `README.md` (brand book: color, type, watercolor, logo and illustration rules), `Layout.md` (spacing, sizing, app layout, phone vs desktop for every component), `tokens.json`, `components/bundle.js` (React versions on `window.Treeline`, typed in `components/index.d.ts`) and `assets/` (logos, exports, illustrations, icons).

## Rules to follow when writing UI

1. Copy markup from `ui/components/<Name>.html` and keep its classes and nesting. Use tokens (`var(--space-4)`, `var(--ink)`), never raw values.
2. Every screen sits in `.tl-app` (the shell: `.tl-app > .tl-app__layout > header.tl-appbar, main.tl-app__main, nav.tl-nav`) or has `class="tl-root"` on `<body>`. Components use container queries, so without one the phone layout never applies.
3. Sheets and the `.tl-toasts` region are the last children of `.tl-app`, never inside main. No `backdrop-filter`, `transform` or `filter` on the app bar.
4. Navigation is always Home, Friends, Calls, Quiet hours. One `h1` per screen, in the app bar. Each screen is one template: Overview, List and detail, Settings form or Focused task (a sheet).
5. No light-green backgrounds; green (`canopy`) is for accents and the primary button only. One toned card per screen. Every phone icon is the rotary phone.
6. Test at 360, 390, 768, 1024, 1280 and 1440 in both themes (`data-theme="light"` / `"dark"` on `<html>`): nothing may scroll sideways, and the app bar title lines up with the first card.
7. **No 911, said plainly.** The softphone shows "Can't call 911 or outside numbers" on its main screen. The parent app says it during setup (the parent ticks "I understand"), on Home, and in About. Never hide it in settings.
8. **Footer in every app:** a small `caption`-size line at the bottom of the page, in `ink-muted`: "© 2026 Jordan Miller · jdmiller2010@gmail.com · Support Treeline · Open-source licenses". "Support Treeline" links to the Buy Me a Coffee page (placeholder until it exists: `https://buymeacoffee.com/REPLACE-ME`). "Open-source licenses" opens a plain page built from `THIRD_PARTY_NOTICES.md`, listing each component, its license and copyright, with Treeline's own licenses first.
