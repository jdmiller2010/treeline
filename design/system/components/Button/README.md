# Button

A labeled action. Secondary is the default; Primary (`canopy`) appears at most once per view, for the thing the screen is for.

**Consumer provides:** `children` (the label), `variant` (`primary` · `secondary` · `quiet` · `danger` · `ring`), `size` (`sm` 32px · `md` 40px · `lg` 48px), optional `icon` / `iconEnd` (icon names), `fullWidth`, and any native button props (`onClick`, `disabled`, `type`).

- Labels are verbs, sentence case, short: "Approve", "Call Alex", "Pause Sam's phone". No exclamation marks.
- `danger` (`berry`) only for removing a friend, ending a call or blocking. Always name what happens: "Remove Riley", not "Delete".
- `ring` (`sunbeam`) is reserved for answering a ringing call. Nowhere else.
- A button beside the main action is `secondary` (the default), never `quiet`: `quiet` is for a small extra action on its own ("Manage", "‹ All calls"), not the other half of a pair. On phones the main action is `lg`, at its natural width in the left-aligned `.tl-actions` row, never a full-width bar.
- Disabled buttons drop to `opacity-disabled`. Say why nearby rather than leaving people guessing.
- Buttons are pills. Primary is lit from above (`--tl-canopy-fill`); `ring` glows with `shadow-glow`.
- Focus shows the `focus` ring, 2px with a 2px offset.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Primary**

```html
<button type="button" class="tl-btn tl-btn--primary tl-btn--md">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
  <span class="tl-btn__label">Approve</span>
</button>
```

**Secondary**

```html
<button type="button" class="tl-btn tl-btn--secondary tl-btn--md">
  <span class="tl-btn__label">Not now</span>
</button>
```

**Quiet**

```html
<button type="button" class="tl-btn tl-btn--quiet tl-btn--md">
  <span class="tl-btn__label">See call log</span>
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
</button>
```

**Danger**

```html
<button type="button" class="tl-btn tl-btn--danger tl-btn--md">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
  <span class="tl-btn__label">Remove Riley</span>
</button>
```

**Ring (answer)**

```html
<button type="button" class="tl-btn tl-btn--ring tl-btn--md">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
  <span class="tl-btn__label">Answer</span>
</button>
```

**Small**

```html
<button type="button" class="tl-btn tl-btn--primary tl-btn--sm">
  <span class="tl-btn__label">Small</span>
</button>
```

**Large, full width**

```html
<button type="button" class="tl-btn tl-btn--primary tl-btn--lg tl-btn--full">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
  <span class="tl-btn__label">Call Grandma</span>
</button>
```

**Disabled**

```html
<button type="button" disabled="" class="tl-btn tl-btn--secondary tl-btn--md">
  <span class="tl-btn__label">Disabled</span>
</button>
```

**Collapse (icon-only in compact top bars)**

```html
<button type="button" class="tl-btn tl-btn--secondary tl-btn--md tl-btn--collapse">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
  <span class="tl-btn__label">Add friend</span>
</button>
```
