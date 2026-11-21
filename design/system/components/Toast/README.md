# Toast

A short, passing confirmation after the parent does something.

**Consumer provides:** `children` (the message, one line), `tone` (`neutral` · `success` · `warning`), optional `action` and `onAction` (one short word, like Undo). Render toasts inside `Toasts`, the fixed region, which goes in AppShell's `overlay`. Plain HTML: `TreelineUI.toast("Request sent", { tone: "success", action: "Undo", onAction })`, or `data-tl-toast="…"` on a button.

- A dark `ink` pill with `surface` text (it flips in Lantern), `shadow-lg`, 48px tall, at most `sheet-max` wide.
- **Phones:** centered just above the bottom tabs and the home indicator. **768 and up:** centered over the page column, `space-8` from the bottom, clear of the rail or sidebar.
- Stays 5 seconds, 8 with an action, then fades. Several stack upward, newest at the bottom. Never more than three at once.
- Says what happened in a few words, past tense: "Request sent", "Riley removed", "Quiet hours saved". No errors that need fixing (use an Alert) and no questions (use a Sheet).
- Announced politely to screen readers (`aria-live="polite"`). Keep the same text visible somewhere if it matters later.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Neutral**

```html
<div class="tl-toast tl-toast--neutral" role="status">
  <svg class="tl-icon tl-toast__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5v.01"/></svg>
  <span class="tl-toast__msg">Request sent to the Chen house</span>
</div>
```

**Success with action**

```html
<div class="tl-toast tl-toast--success" role="status">
  <svg class="tl-icon tl-toast__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-14 14-14 0 9-6 14-14 14z"/><path d="M5 19l8-8"/></svg>
  <span class="tl-toast__msg">Riley removed</span>
  <button type="button" class="tl-toast__action">Undo</button>
</div>
```

**Warning**

```html
<div class="tl-toast tl-toast--warning" role="status">
  <svg class="tl-icon tl-toast__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z"/><path d="M12 9.5v4.5"/><path d="M12 17v.01"/></svg>
  <span class="tl-toast__msg">Sam’s phone is offline</span>
</div>
```

**Region (put it last in .tl-app)**

```html
<div class="tl-toasts" aria-live="polite" aria-atomic="false">
  <div class="tl-toast tl-toast--success" role="status">
    <svg class="tl-icon tl-toast__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-14 14-14 0 9-6 14-14 14z"/><path d="M5 19l8-8"/></svg>
    <span class="tl-toast__msg">Quiet hours saved</span>
  </div>
</div>
```
