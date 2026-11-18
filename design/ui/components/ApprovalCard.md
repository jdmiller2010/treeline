# ApprovalCard

Shows the two halves of a mutual approval: a call connects only when both households say yes.

**Consumer provides:** `kid`, `friend` (names), `yourHousehold`, `theirHousehold`, `yours` and `theirs` (booleans), `actions` (Buttons for the next step).

- Always show both halves, even when one is done. Parents need to see whose turn it is.
- Waiting halves are dashed and calm (`clock`, "Waiting"), never red. Nothing is wrong yet.
- Once both approve, warm sunlight blooms in the corner (`--tl-bloom-sun`), the link becomes a green leaf, and the title says what's now possible. The card itself never turns green.
- Actions belong to the current parent only: "Approve", "Not now", or later "Remove".

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Waiting on them**

```html
<section class="tl-card tl-approval">
  <div class="tl-approval__people">
    <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Sam">S</span>
    <span class="tl-approval__link" aria-hidden="true">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
    </span>
    <span class="tl-avatar tl-avatar--md tl-avatar--pond" role="img" aria-label="Riley">R</span>
  </div>
  <h3 class="tl-card__title">Sam and Riley</h3>
  <div class="tl-approval__sides">
    <div class="tl-approval__side is-yes">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Your house</span>
        <span class="tl-approval__state">Approved</span>
      </span>
    </div>
    <div class="tl-approval__side is-waiting">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Riley&#x27;s house</span>
        <span class="tl-approval__state">Waiting</span>
      </span>
    </div>
  </div>
  <p class="tl-approval__note">Calls connect once Riley&#x27;s house approves too.</p>
  <div class="tl-approval__actions">
    <button type="button" class="tl-btn tl-btn--quiet tl-btn--sm">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      <span class="tl-btn__label">Withdraw</span>
    </button>
  </div>
</section>
```

**Your turn**

```html
<section class="tl-card tl-approval">
  <div class="tl-approval__people">
    <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Sam">S</span>
    <span class="tl-approval__link" aria-hidden="true">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
    </span>
    <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Alex">A</span>
  </div>
  <h3 class="tl-card__title">Sam and Alex</h3>
  <div class="tl-approval__sides">
    <div class="tl-approval__side is-waiting">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Your house</span>
        <span class="tl-approval__state">Waiting</span>
      </span>
    </div>
    <div class="tl-approval__side is-yes">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Alex&#x27;s house</span>
        <span class="tl-approval__state">Approved</span>
      </span>
    </div>
  </div>
  <p class="tl-approval__note">Alex&#x27;s house said yes. Calls connect once you approve.</p>
  <div class="tl-approval__actions">
    <button type="button" class="tl-btn tl-btn--primary tl-btn--md">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      <span class="tl-btn__label">Approve</span>
    </button>
    <button type="button" class="tl-btn tl-btn--secondary tl-btn--md">
      <span class="tl-btn__label">Not now</span>
    </button>
  </div>
</section>
```

**Connected**

```html
<section class="tl-card tl-approval is-connected">
  <div class="tl-approval__people">
    <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Sam">S</span>
    <span class="tl-approval__link" aria-hidden="true">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-14 14-14 0 9-6 14-14 14z"/><path d="M5 19l8-8"/></svg>
    </span>
    <span class="tl-avatar tl-avatar--md tl-avatar--moss" role="img" aria-label="Grandma Jo">GJ</span>
  </div>
  <h3 class="tl-card__title">Sam and Grandma Jo can call each other</h3>
  <div class="tl-approval__sides">
    <div class="tl-approval__side is-yes">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Your house</span>
        <span class="tl-approval__state">Approved</span>
      </span>
    </div>
    <div class="tl-approval__side is-yes">
      <span class="tl-approval__mark" aria-hidden="true">
        <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
      </span>
      <span>
        <span class="tl-approval__who">Grandma</span>
        <span class="tl-approval__state">Approved</span>
      </span>
    </div>
  </div>
</section>
```
