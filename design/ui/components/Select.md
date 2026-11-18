# Select

Pick one option from a short list.

**Consumer provides:** `label`, `options` (`value`, `label`, `disabled`, or plain strings), optional `hint`, `error`, `value`/`defaultValue`, `onChange`, `id`.

- A native `<select>` dressed exactly like TextField: same height, border, radius, shadow, label and hint. The chevron is drawn by the component. On phones the system picker opens, which is what parents expect.
- Use it for 4–12 options. Two or three options read better as a SegmentedControl; more than 12 need a search field.
- Options are short and parallel ("15 minutes", "30 minutes", "1 hour"). Put "No limit" or "None" last.
- Error and disabled states match TextField. Full width of the card; capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**With hint**

```html
<div class="tl-textfield">
  <label for="longest-call" class="tl-textfield__label">Longest call</label>
  <div class="tl-textfield__control">
    <select id="longest-call" class="tl-textfield__input tl-select" aria-describedby="longest-call-hint">
      <option value="15">15 minutes</option>
      <option value="30" selected="">30 minutes</option>
      <option value="45">45 minutes</option>
      <option value="60">1 hour</option>
      <option value="none">No limit</option>
    </select>
    <svg class="tl-icon tl-textfield__chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
  </div>
  <p id="longest-call-hint" class="tl-textfield__hint">A gentle beep plays a minute before.</p>
</div>
```

**With error**

```html
<div class="tl-textfield has-error">
  <label for="which-phone" class="tl-textfield__label">Which phone</label>
  <div class="tl-textfield__control">
    <select id="which-phone" class="tl-textfield__input tl-select" aria-invalid="true" aria-describedby="which-phone-hint">
      <option value="" selected="">Choose…</option>
      <option value="sam">Sam’s phone</option>
      <option value="ivy">Ivy’s phone</option>
    </select>
    <svg class="tl-icon tl-textfield__chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
  </div>
  <p id="which-phone-hint" class="tl-textfield__hint">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>Pick a phone to continue.</p>
</div>
```
