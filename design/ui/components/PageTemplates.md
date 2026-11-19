# PageTemplates

Every parent screen is one of four templates. Pick the template first, then fill it with components.

- **Overview (Home):** `.tl-page` › `.tl-stack--sections`. The one toned card (breeze or night) comes first, then the day's summary, in a `.tl-grid--2`; then "Waiting on families" (ApprovalCards); then "Approved friends" (a list card). One column on phones, two summary cards side by side from 640 content.
- **List and detail (Friends, Calls):** see ListDetail.
- **Settings form (Quiet hours, a kid's phone, the household):** `.tl-page.tl-page--narrow` › `.tl-stack--cards` of cards, each with `.tl-stack--group` fields and a `.tl-actions--stack` row. The column keeps the page's left edge (it lines up with the AppBar title) and caps at `sheet-max`. Actions are one left-aligned row at every width, the primary first.
- **Focused task (approve, pause, confirm):** a Sheet over whatever screen you're on. See Sheet.
- Section headings are `h2.title-lg`; the page's `h1` is the AppBar title. A screen shows at most one toned card.
- Empty pages put an `EmptyState` in a card, centered in the column.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Overview (Home)**

```html
<div class="tl-page">
  <div class="tl-stack tl-stack--sections">
    <div class="tl-grid tl-grid--2">
      <section class="tl-card tl-card--breeze">
        <header class="tl-card__head">
          <div>
            <p class="tl-card__eyebrow">Good news</p>
            <h3 class="tl-card__title">Alex is in the treehouse</h3>
          </div>
        </header>
        <p class="tl-card__body">Both families approved.</p>
      </section>
      <section class="tl-card">
        <header class="tl-card__head">
          <div>
            <p class="tl-card__eyebrow">Today</p>
            <h3 class="tl-card__title">3 calls, 42 minutes</h3>
          </div>
        </header>
        <p class="tl-card__body">Sam talked with Alex and Grandma.</p>
      </section>
    </div>
    <section class="tl-stack">
      <h2 class="title-lg">Waiting on families</h2>…ApprovalCards…</section>
    <section class="tl-stack">
      <h2 class="title-lg">Approved friends</h2>
      <div class="tl-card tl-card--list">…FriendRows…</div>
    </section>
  </div>
</div>
```

**Settings form**

```html
<div class="tl-page tl-page--narrow">
  <div class="tl-stack tl-stack--cards">
    <section class="tl-card">
      <div class="tl-stack tl-stack--group">
        <div class="tl-stack tl-stack--tight">
          <h2 class="tl-card__title">Call limits</h2>
          <p class="tl-card__body">Applies to every friend.</p>
        </div>
        <div class="tl-textfield">
          <label for="longest" class="tl-textfield__label">Longest call</label>
          <div class="tl-textfield__control">
            <input id="longest" class="tl-textfield__input" placeholder="30 minutes"/>
          </div>
        </div>
        <div class="tl-field-row">
          <button id="warn" type="button" role="switch" aria-checked="true" class="tl-switch is-on">
            <span class="tl-switch__thumb">
              <svg class="tl-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
            </span>
          </button>
          <label for="warn" class="tl-field-row__text">
            <span class="tl-field-row__label">Warn before ending</span>
            <span class="tl-field-row__desc">One beep, one minute before the limit.</span>
          </label>
        </div>
      </div>
      <div class="tl-actions tl-actions--stack">
        <button type="button" class="tl-btn tl-btn--quiet tl-btn--md">
          <span class="tl-btn__label">Cancel</span>
        </button>
        <button type="button" class="tl-btn tl-btn--primary tl-btn--md">
          <span class="tl-btn__label">Save</span>
        </button>
      </div>
    </section>
  </div>
</div>
```
