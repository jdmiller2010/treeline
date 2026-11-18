# Textarea

Several lines of text: a note with a request, a report, feedback.

**Consumer provides:** everything a native textarea takes, plus `label`, `hint`, `error`, `maxLength` (shows a live counter), `id`.

- TextField's anatomy: same border, radius, shadow, label and hint. 112px tall to start (four lines), and the parent can drag it taller.
- With `maxLength` a counter ("42 / 200") sits at the right of the hint line. Plain HTML: the counter needs `data-tl-count` on the textarea and `js/treeline.js`.
- Placeholder shows an example, never the instructions; instructions go in the hint.
- Full width of the card, capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**With counter**

```html
<div class="tl-textfield">
  <label for="note" class="tl-textfield__label">Note to the Chen family</label>
  <div class="tl-textfield__control">
    <textarea id="note" rows="4" maxLength="200" class="tl-textfield__input tl-textarea" aria-describedby="note-hint" data-tl-count="note-hint-count" placeholder="Hi! Sam would love to call Maya after school.">
    </textarea>
  </div>
  <p id="note-hint" class="tl-textfield__hint">
    <span>They see this with your request.</span>
    <span class="tl-textfield__count" id="note-hint-count">0 / 200</span>
  </p>
</div>
```

**With error**

```html
<div class="tl-textfield has-error">
  <label for="report" class="tl-textfield__label">What happened?</label>
  <div class="tl-textfield__control">
    <textarea id="report" rows="4" class="tl-textfield__input tl-textarea" aria-invalid="true" aria-describedby="report-hint">
    </textarea>
  </div>
  <p id="report-hint" class="tl-textfield__hint">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
    <span>Tell us a little so we can help.</span>
  </p>
</div>
```
