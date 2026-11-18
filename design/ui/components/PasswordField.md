# PasswordField

A password with a show/hide button.

**Consumer provides:** everything a native input takes, plus `label`, `hint`, `error`, `id`. Set `autoComplete` to `current-password` (sign-in, the default) or `new-password` (create or change).

- TextField with an eye button inside on the right (44px tap target). It starts hidden; the button says "Show password" or "Hide password" and is `aria-pressed`. Plain HTML: `data-tl-password="input-id"` on the button and `js/treeline.js`.
- Never block pasting, never limit length below 64, and put any rules in the hint ("At least 10 characters"), not only in an error.
- Full width of the card, capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Sign in**

```html
<div class="tl-textfield tl-password">
  <label for="password" class="tl-textfield__label">Password</label>
  <div class="tl-textfield__control">
    <input id="password" type="password" autocomplete="current-password" spellcheck="false" class="tl-textfield__input" placeholder="••••••••"/>
    <button type="button" class="tl-iconbtn tl-btn--quiet tl-iconbtn--sm tl-password__toggle" aria-label="Show password" aria-pressed="false" aria-controls="password" data-tl-password="password">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/></svg>
    </button>
  </div>
</div>
```

**New password with hint**

```html
<div class="tl-textfield tl-password">
  <label for="new-password" class="tl-textfield__label">New password</label>
  <div class="tl-textfield__control">
    <input id="new-password" type="password" autocomplete="new-password" spellcheck="false" class="tl-textfield__input" aria-describedby="new-password-hint"/>
    <button type="button" class="tl-iconbtn tl-btn--quiet tl-iconbtn--sm tl-password__toggle" aria-label="Show password" aria-pressed="false" aria-controls="new-password" data-tl-password="new-password">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/></svg>
    </button>
  </div>
  <p id="new-password-hint" class="tl-textfield__hint">At least 10 characters.</p>
</div>
```
