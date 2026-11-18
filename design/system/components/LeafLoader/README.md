# LeafLoader

Three leaves blowing across two gusts of wind: Treeline's loading and connecting indicator.

**Consumer provides:** optional `size` (width in px, default 64), `label` (default "Loading"; read by screen readers), `showLabel` to show it under the leaves, or `label={false}` when the surrounding text already says what's happening.

- Use while connecting a call, saving rules or loading a list. For waits over about 8 seconds, add text saying what's taking a while.
- The leaves drift in, tumble and fade out over 2.4s; the wind lines draw and fade behind them.
- With reduced motion, the leaves hold still and gently breathe in opacity instead.
- Don't use more than one loader on screen, and never inside a button: show the button's own state instead.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**With label**

```html
<span class="tl-loader" role="status">
  <svg class="tl-art tl-loader__svg" viewBox="0 0 64 48" width="96" height="72" aria-hidden="true"><path class="tl-loader__wind ln-soft" d="M4 16C14 11 26 12 36 17S54 22 60 18"/><path class="tl-loader__wind tl-loader__wind--2 ln-soft" d="M2 30C12 26 22 27 32 31S50 35 58 32"/><g class="tl-loader__leaf tl-loader__leaf--1"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g><g class="tl-loader__leaf tl-loader__leaf--2"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g><g class="tl-loader__leaf tl-loader__leaf--3"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g></svg>
  <span class="tl-loader__label">Calling Alex…</span>
</span>
```

**Default**

```html
<span class="tl-loader" role="status">
  <svg class="tl-art tl-loader__svg" viewBox="0 0 64 48" width="64" height="48" aria-hidden="true"><path class="tl-loader__wind ln-soft" d="M4 16C14 11 26 12 36 17S54 22 60 18"/><path class="tl-loader__wind tl-loader__wind--2 ln-soft" d="M2 30C12 26 22 27 32 31S50 35 58 32"/><g class="tl-loader__leaf tl-loader__leaf--1"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g><g class="tl-loader__leaf tl-loader__leaf--2"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g><g class="tl-loader__leaf tl-loader__leaf--3"><path class="w-leaf" transform="translate(1.2 1) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="lf" transform="scale(.55)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></g></svg>
  <span class="tl-sr">Loading</span>
</span>
```
