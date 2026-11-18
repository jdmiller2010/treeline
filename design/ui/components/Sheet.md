# Sheet

A focused question or short form over the current screen: approve a friend, edit quiet hours, confirm a pause.

**Consumer provides:** `title`, `children` (a `.tl-sheet__body` paragraph, fields), `actions` (up to two Buttons, primary last), `onClose`, `id` (for the title's label), `open`.

- **Under 768, bottom sheet:** full width, rounded `radius-xl` top corners, a grabber, `gutter-sm` side padding plus the safe area. Actions are stacked full width with the primary on top.
- **768 and up, dialog:** centered, `sheet-max` (440) wide, `radius-xl`, `space-8` padding, a close button top-right, actions in a right-aligned row with the primary last.
- The `scrim` covers the whole app. Tapping it or pressing Escape closes the sheet unless it's mid-save.
- Render it in AppShell's `overlay`, never inside main.
- One sheet at a time. If a flow needs more than one screen, make it a page.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Closed, opened by a button (plain HTML)**

```html
<div>
  <button type="button" data-tl-open="approve" class="tl-btn tl-btn--secondary tl-btn--md">
    <span class="tl-btn__label">Review request</span>
  </button>
  <div class="tl-sheet-scrim" id="approve" hidden="">
    <div class="tl-sheet" role="dialog" aria-modal="true" aria-labelledby="approve-title">
      <span class="tl-sheet__grabber" aria-hidden="true">
      </span>
      <div class="tl-sheet__head">
        <h2 class="tl-sheet__title" id="approve-title">Approve Maya?</h2>
        <button type="button" aria-label="Close" title="Close" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md tl-sheet__close">
          <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
      </div>
      <p class="tl-sheet__body">Maya Chen from the Chen house wants to call Sam.</p>
      <div class="tl-actions">
        <button type="button" data-tl-close="" class="tl-btn tl-btn--secondary tl-btn--md">
          <span class="tl-btn__label">Not now</span>
        </button>
        <button type="button" data-tl-close="" class="tl-btn tl-btn--primary tl-btn--md">
          <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
          <span class="tl-btn__label">Approve</span>
        </button>
      </div>
    </div>
  </div>
</div>
```

**Open**

```html
<div class="tl-sheet-scrim" id="approve-open">
  <div class="tl-sheet" role="dialog" aria-modal="true" aria-labelledby="approve-open-title">
    <span class="tl-sheet__grabber" aria-hidden="true">
    </span>
    <div class="tl-sheet__head">
      <h2 class="tl-sheet__title" id="approve-open-title">Approve Maya?</h2>
      <button type="button" aria-label="Close" title="Close" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md tl-sheet__close">
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
    <p class="tl-sheet__body">Maya Chen from the Chen house wants to call Sam. Both families need to say yes.</p>
    <div class="tl-actions">
      <button type="button" class="tl-btn tl-btn--secondary tl-btn--md">
        <span class="tl-btn__label">Not now</span>
      </button>
      <button type="button" class="tl-btn tl-btn--primary tl-btn--md">
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
        <span class="tl-btn__label">Approve</span>
      </button>
    </div>
  </div>
</div>
```
