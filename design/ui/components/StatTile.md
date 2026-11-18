# StatTile

One number that matters, big, with what it means.

**Consumer provides:** `label`, `value`, optional `unit`, `note`, `trend` (adds an up arrow to the note).

- An overline label, the number in Fraunces 36 with tabular figures and a small unit, and a one-line note. Group them in `.tl-stats`, which fits as many 140px-wide tiles across as there's room for and wraps the rest.
- At most three or four on a screen, inside one Card on Home. Numbers that need comparing across time belong in a chart, not a row of tiles.
- Notes are plain facts ("Up from 30 last week"), never judgments ("Too much!").

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**One stat**

```html
<div class="tl-stat">
  <span class="tl-stat__label">This week</span>
  <span class="tl-stat__value">42<span class="tl-stat__unit">min</span>
  </span>
  <span class="tl-stat__note">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 16l5-5 4 4 7-7"/><path d="M15 8h5v5"/></svg>Up from 30 last week</span>
</div>
```

**A row of stats in a card**

```html
<section class="tl-card">
  <div class="tl-stats">
    <div class="tl-stat">
      <span class="tl-stat__label">Calls</span>
      <span class="tl-stat__value">9</span>
      <span class="tl-stat__note">This week</span>
    </div>
    <div class="tl-stat">
      <span class="tl-stat__label">Talk time</span>
      <span class="tl-stat__value">42<span class="tl-stat__unit">min</span>
      </span>
      <span class="tl-stat__note">This week</span>
    </div>
    <div class="tl-stat">
      <span class="tl-stat__label">Friends</span>
      <span class="tl-stat__value">5</span>
      <span class="tl-stat__note">2 waiting</span>
    </div>
  </div>
</section>
```
