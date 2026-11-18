# CodeInput

One box per digit, for pairing a phone and for sign-in codes.

**Consumer provides:** `label`, `length` (default 6), `split` (a dash in the middle, default on), `defaultValue`, `hint`, `error`, `id`.

- Six 48 × 56 boxes in Fraunces with tabular figures, a short dash between the two halves. The first box has `autocomplete="one-time-code"` so phones can fill it from a text message.
- Typing moves to the next box, Backspace goes back, arrow keys move, and pasting a whole code fills every box. When all boxes are full the fieldset fires a `tl-code` event with the value (also on `data-value`). Plain HTML needs `js/treeline.js`.
- **Under 400px of content** the boxes shrink and close up so six still fit at 320px.
- Say where the code is ("Printed under the phone", "We emailed it to you"). Errors go under the boxes and turn their borders `berry`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Pairing code**

```html
<fieldset class="tl-code" data-tl-code="">
  <legend>Code on the phone’s card</legend>
  <div class="tl-code__boxes">
    <input id="pair-code" class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="one-time-code" aria-label="Digit 1 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 2 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 3 of 6"/>
    <span class="tl-code__gap" aria-hidden="true">
    </span>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 4 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 5 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 6 of 6"/>
  </div>
  <p class="tl-textfield__hint">Six digits, printed under the phone.</p>
</fieldset>
```

**With error**

```html
<fieldset class="tl-code has-error" data-tl-code="">
  <legend>Sign-in code</legend>
  <div class="tl-code__boxes">
    <input id="signin-code" class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="one-time-code" aria-label="Digit 1 of 6" value="4"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 2 of 6" value="8"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 3 of 6" value="2"/>
    <span class="tl-code__gap" aria-hidden="true">
    </span>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 4 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 5 of 6"/>
    <input class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxLength="1" autocomplete="off" aria-label="Digit 6 of 6"/>
  </div>
  <p class="tl-textfield__hint">
    <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>That code didn’t match. Check your email and try again.</p>
</fieldset>
```
