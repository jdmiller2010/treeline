# TextField

A labeled single-line input with an optional hint or error.

**Consumer provides:** `label`, optional `hint`, `error` (replaces the hint and turns the field `berry`), optional leading `icon`, and native input props (`value`, `onChange`, `placeholder`, `type`).

- Always a visible label above the field; placeholders are examples, never instructions.
- Hints are short and calm. Errors say how to fix it: "Use a time like 7:30 pm."
- 40px tall (`control-md`), `radius-sm`, `line-strong` border.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**With hint**

```html
<div class="tl-textfield">
  <label for="kid-name" class="tl-textfield__label">Kid’s first name</label>
  <div class="tl-textfield__control">
    <input id="kid-name" class="tl-textfield__input" aria-describedby="kid-name-hint" placeholder="Sam"/>
  </div>
  <p id="kid-name-hint" class="tl-textfield__hint">Friends see this on their phone.</p>
</div>
```

**With icon**

```html
<div class="tl-textfield">
  <label for="find-family" class="tl-textfield__label">Find a family</label>
  <div class="tl-textfield__control">
    <svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="8" r="3"/><path d="M3 19a6 6 0 0 1 12 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2A5 5 0 0 1 21 19"/></svg>
    <input id="find-family" class="tl-textfield__input" placeholder="Search by name"/>
  </div>
</div>
```

**Error**

```html
<div class="tl-textfield has-error">
  <label for="quiet-start" class="tl-textfield__label">Quiet hours start</label>
  <div class="tl-textfield__control">
    <input id="quiet-start" class="tl-textfield__input" aria-invalid="true" aria-describedby="quiet-start-hint" value="25:00"/>
  </div>
  <p id="quiet-start-hint" class="tl-textfield__hint">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>Use a time like 7:30 pm.</p>
</div>
```
