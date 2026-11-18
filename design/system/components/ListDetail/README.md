# ListDetail

The layout for Friends and Calls: a list, and the details of whatever row you picked.

**Consumer provides:** a `.tl-listdetail` with two children, `.tl-listdetail__list` and `.tl-listdetail__detail`, plus a `.tl-listdetail__back` button inside the detail. Plain HTML: add `data-tl-detail` to each row and `js/treeline.js` handles the switching. React: toggle the `is-detail` class yourself.

- **Content under 960 (phones, tablets, laptops with a sidebar):** one pane at a time. The list fills the page; tapping a row adds `is-detail`, which hides the list and shows the detail with its back link. The back link removes `is-detail`.
- **Content 960 and up:** both panes, list at `list-pane` (360) on the left, detail beside it, `space-8` apart. The back link hides and the detail stays put under the AppBar while the list scrolls.
- The list pane is its own size container, so rows inside it use their compact layout (presence under the name) even on a wide screen.
- The detail is a Card with the friend's or call's facts and up to two actions. Don't put a second list in the detail.
- On wide screens with nothing picked, show the first row's detail or an `EmptyState` ("Pick a friend to see their calls"), never a blank pane.
- Keep the AppBar title as the section name (Friends), not the picked friend.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**List and detail (list showing)**

```html
<div class="tl-listdetail">
  <section class="tl-listdetail__list tl-stack">
    <h2 class="title-lg">Approved friends</h2>
    <div class="tl-card tl-card--list">
      <div data-tl-detail="">
        <div class="tl-row">
          <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Alex">A<span class="tl-avatar__status tl-presence--canopy" aria-hidden="true">
            </span>
          </span>
          <div class="tl-row__main">
            <div class="tl-row__title">Alex</div>
            <div class="tl-row__meta">
              <span class="tl-household">
                <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>Alex&#x27;s house</span>
              <span class="tl-speeddial" aria-label="Speed dial 1">1</span>
              <span class="tl-presence tl-presence--canopy tl-row__presence-inline">
                <span class="tl-presence__dot" aria-hidden="true">
                </span>
                <span>Available</span>
              </span>
            </div>
          </div>
          <span class="tl-presence tl-presence--canopy">
            <span class="tl-presence__dot" aria-hidden="true">
            </span>
            <span>Available</span>
          </span>
        </div>
      </div>
    </div>
  </section>
  <section class="tl-listdetail__detail tl-stack">
    <button type="button" class="tl-btn tl-btn--quiet tl-btn--sm tl-listdetail__back">
      <span class="tl-btn__label">‹ All friends</span>
    </button>
    <section class="tl-card">
      <header class="tl-card__head">
        <div>
          <p class="tl-card__eyebrow">Alex&#x27;s house</p>
          <h3 class="tl-card__title">Alex</h3>
        </div>
      </header>
      <p class="tl-card__body">Speed dial 1. Approved by both families.</p>
      <div class="tl-actions tl-actions--stack">
        <button type="button" class="tl-btn tl-btn--secondary tl-btn--md">
          <span class="tl-btn__label">Pause calls</span>
        </button>
        <button type="button" class="tl-btn tl-btn--primary tl-btn--md">
          <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
          <span class="tl-btn__label">Call Alex</span>
        </button>
      </div>
    </section>
  </section>
</div>
```
