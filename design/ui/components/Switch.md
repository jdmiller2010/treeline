# Switch

An instant on/off setting with a label and an optional description.

**Consumer provides:** `label`, optional `description`, `checked` + `onChange(next)` (controlled) or `defaultChecked`, `disabled`, `id`.

- For settings that apply right away (quiet hours on, phone paused). For choices that wait for a Save, use Checkbox.
- Label the setting, not the action: "Quiet hours", not "Turn on quiet hours".
- The description says what happens in plain words: "Calls wait until 7 am."
- On = `canopy` track with a check in the thumb; off = `surface-sunk` with a `line-strong` edge.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**On**

```html
<div class="tl-field-row">
  <button id="quiet-hours" type="button" role="switch" aria-checked="true" class="tl-switch is-on">
    <span class="tl-switch__thumb">
      <svg class="tl-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
    </span>
  </button>
  <label for="quiet-hours" class="tl-field-row__text">
    <span class="tl-field-row__label">Quiet hours</span>
    <span class="tl-field-row__desc">Calls wait until 7:00 am.</span>
  </label>
</div>
```

**Off**

```html
<div class="tl-field-row">
  <button id="pause-sam" type="button" role="switch" aria-checked="false" class="tl-switch">
    <span class="tl-switch__thumb">
    </span>
  </button>
  <label for="pause-sam" class="tl-field-row__text">
    <span class="tl-field-row__label">Pause Sam&#x27;s phone</span>
    <span class="tl-field-row__desc">No calls in or out until you turn this off.</span>
  </label>
</div>
```

**Disabled**

```html
<div class="tl-field-row is-disabled">
  <button id="group-calls" type="button" role="switch" aria-checked="false" disabled="" class="tl-switch">
    <span class="tl-switch__thumb">
    </span>
  </button>
  <label for="group-calls" class="tl-field-row__text">
    <span class="tl-field-row__label">Group calls</span>
    <span class="tl-field-row__desc">Coming soon.</span>
  </label>
</div>
```
