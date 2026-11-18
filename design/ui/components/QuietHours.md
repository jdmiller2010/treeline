# QuietHours

A schedule when a kid's phone rests: times, days and an on/off switch.

**Consumer provides:** `title` (default "Quiet hours"), `start`, `end` (display strings like "8:00 pm"), `days` (labels, default M–S), `activeDays` (indexes), `on` + `onToggle(next)`, `id`.

- Lives on a dusk wash (`--tl-dusk`: sky pooling at the top, warming to petal) with organic corners and the `moon` icon: night belongs to `sky`.
- Times are set in the `numeral` style (Fraunces) with tabular figures so they don't jump.
- Days are small pills: filled `sky` when on, outlined when off.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**On, every day**

```html
<div class="tl-quiet">
  <span class="tl-quiet__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
  </span>
  <div class="tl-quiet__main">
    <div class="tl-row__title">Quiet hours</div>
    <div class="tl-quiet__time">
      <span class="tl-num">8:00 pm</span>
      <span class="tl-quiet__to">to</span>
      <span class="tl-num">7:00 am</span>
    </div>
    <div class="tl-quiet__days" aria-label="Days">
      <span class="tl-day is-on">M</span>
      <span class="tl-day is-on">T</span>
      <span class="tl-day is-on">W</span>
      <span class="tl-day is-on">T</span>
      <span class="tl-day is-on">F</span>
      <span class="tl-day is-on">S</span>
      <span class="tl-day is-on">S</span>
    </div>
  </div>
  <div class="tl-field-row">
    <button id="qh-night" type="button" role="switch" aria-checked="true" class="tl-switch is-on">
      <span class="tl-switch__thumb">
        <svg class="tl-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      </span>
    </button>
  </div>
</div>
```

**Off, weekdays**

```html
<div class="tl-quiet">
  <span class="tl-quiet__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
  </span>
  <div class="tl-quiet__main">
    <div class="tl-row__title">Homework time</div>
    <div class="tl-quiet__time">
      <span class="tl-num">4:00</span>
      <span class="tl-quiet__to">to</span>
      <span class="tl-num">5:00 pm</span>
    </div>
    <div class="tl-quiet__days" aria-label="Days">
      <span class="tl-day is-on">M</span>
      <span class="tl-day is-on">T</span>
      <span class="tl-day is-on">W</span>
      <span class="tl-day is-on">T</span>
      <span class="tl-day">F</span>
      <span class="tl-day">S</span>
      <span class="tl-day">S</span>
    </div>
  </div>
  <div class="tl-field-row">
    <button id="qh-homework" type="button" role="switch" aria-checked="false" class="tl-switch">
      <span class="tl-switch__thumb">
      </span>
    </button>
  </div>
</div>
```
