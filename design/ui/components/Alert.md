# Alert

An inline notice on the page: something the parent should know or fix.

**Consumer provides:** `tone` (`info` · `success` · `warning` · `danger`), `title`, `children` (one or two sentences), optional `actions` (up to two small Buttons), `onClose` or `dismissible`, `icon` (to override the tone's icon).

- A `surface` sheet with a `card-edge` and `shadow-sm`, a 4px tone edge on the left and the tone's icon in a small pebble-shaped well. The title carries the message; the body says what happens or what to do. Never a tinted background: a green or blue sheet would blend into the page and break the no-green-backgrounds rule.
- Tones: `info` (`sky`, a fact about now), `success` (`canopy`, something worked and stays true), `warning` (`bark` on `wash-sun`, needs attention soon), `danger` (`berry`, something failed or is blocked).
- Place it at the top of the page or directly above the thing it's about, full width of the column, `space-8` from the next card. One alert per page.
- `warning` and `danger` announce themselves (`role="alert"`); `info` and `success` are polite (`role="status"`).
- Use a Toast instead for a passing confirmation ("Saved"). Use an Alert when the state lasts until someone acts.
- Phones and desktop: the same, full width of the column. Actions wrap under the body.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior. The dismiss button needs `data-tl-dismiss`.

**Info**

```html
<div class="tl-alert tl-alert--info" role="status">
  <span class="tl-alert__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5v.01"/></svg>
  </span>
  <div>
    <p class="tl-alert__title">Quiet hours start at 8:00 pm</p>
    <p class="tl-alert__body">Calls to Sam will wait until 7:00 am.</p>
  </div>
  <span>
  </span>
</div>
```

**Success**

```html
<div class="tl-alert tl-alert--success" role="status">
  <span class="tl-alert__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
  </span>
  <div>
    <p class="tl-alert__title">Maya’s family approved</p>
    <p class="tl-alert__body">Sam and Maya can call each other now. Speed dial 3.</p>
  </div>
  <span>
  </span>
</div>
```

**Warning, with actions**

```html
<div class="tl-alert tl-alert--warning" role="alert">
  <span class="tl-alert__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z"/><path d="M12 9.5v4.5"/><path d="M12 17v.01"/></svg>
  </span>
  <div>
    <p class="tl-alert__title">Sam’s phone is offline</p>
    <p class="tl-alert__body">It hasn’t checked in since 3:40 pm. Calls can’t reach it.</p>
    <div class="tl-alert__actions">
      <button type="button" class="tl-btn tl-btn--secondary tl-btn--sm">
        <span class="tl-btn__label">How to fix it</span>
      </button>
      <button type="button" class="tl-btn tl-btn--quiet tl-btn--sm">
        <span class="tl-btn__label">Remind me later</span>
      </button>
    </div>
  </div>
  <span>
  </span>
</div>
```

**Danger, dismissible**

```html
<div class="tl-alert tl-alert--danger" role="alert">
  <span class="tl-alert__icon" aria-hidden="true">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z"/><path d="M12 9.5v4.5"/><path d="M12 17v.01"/></svg>
  </span>
  <div>
    <p class="tl-alert__title">Couldn’t save quiet hours</p>
    <p class="tl-alert__body">Check your connection and try again.</p>
  </div>
  <button type="button" data-tl-dismiss="" aria-label="Dismiss" title="Dismiss" class="tl-iconbtn tl-btn--quiet tl-iconbtn--sm tl-alert__close">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
  </button>
</div>
```
