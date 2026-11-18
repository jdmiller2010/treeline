# LeafDivider

A hairline that fades in from both sides and meets at a small sprig of two leaves.

**Consumer provides:** nothing; it fills the width of its container.

- Use it to separate major sections of a screen or a long sheet, at most once or twice per screen.
- Between rows in a list, use the plain fading hairline (`.tl-fade-line`), not the sprig.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Divider**

```html
<div class="tl-leafdiv" role="separator">
  <span class="tl-fade-line tl-leafdiv__line">
  </span>
  <svg class="tl-art tl-leafdiv__sprig" viewBox="0 0 28 18" width="28" height="18" aria-hidden="true"><path class="ln-soft" d="M2 12C10 10 18 8 26 6"/><path class="w-leaf" transform="translate(11.6 9.4) rotate(-55) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="ln" transform="translate(10 8) rotate(-55) scale(.6)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/><path class="w-leaf" transform="translate(19.6 11.4) rotate(45) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="ln" transform="translate(18 10) rotate(45) scale(.6)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/></svg>
  <span class="tl-fade-line tl-leafdiv__line">
  </span>
</div>
```
