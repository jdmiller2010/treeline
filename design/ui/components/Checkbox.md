# Checkbox

A choice that's saved with a form, alone or in a list.

**Consumer provides:** `label`, optional `description`, `checked` + `onChange(next)` or `defaultChecked`, `disabled`, `id`.

- Use for picking several things before confirming ("Which friends can Sam call?"). For an instant setting, use Switch.
- The whole label is clickable. Keep labels short and positive.
- Checked = `canopy` fill with an `on-canopy` check; unchecked = `surface` with a `line-strong` edge.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Checked**

```html
<div class="tl-field-row">
  <span class="tl-check">
    <input id="friend-alex" type="checkbox" class="tl-check__input" checked=""/>
    <span class="tl-check__box" aria-hidden="true">
      <svg class="tl-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
    </span>
  </span>
  <label for="friend-alex" class="tl-field-row__text">
    <span class="tl-field-row__label">Alex</span>
    <span class="tl-field-row__desc">Alex&#x27;s house</span>
  </label>
</div>
```

**Unchecked**

```html
<div class="tl-field-row">
  <span class="tl-check">
    <input id="friend-riley" type="checkbox" class="tl-check__input"/>
    <span class="tl-check__box" aria-hidden="true">
      <svg class="tl-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
    </span>
  </span>
  <label for="friend-riley" class="tl-field-row__text">
    <span class="tl-field-row__label">Riley</span>
    <span class="tl-field-row__desc">Waiting for their family to approve</span>
  </label>
</div>
```
