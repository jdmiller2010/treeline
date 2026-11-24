# Hint

A small speech bubble that points at what to do next, right where the person is trying something that won't work yet: "Pick up the handset first, then dial", pointing at the handset. Tapping it does that next thing for them.

**Consumer provides:** `children` (one short line, an instruction in plain words), `icon` (optional, from the set), `onClick` (does the thing the hint asks for), `points` (`down`, the default, or `up`: which way the tail points), `open`. Plain HTML: a `<button class="tl-hint">`, placed absolutely by the page next to what it points at, shown and hidden with `hidden`.

- A `surface` bubble with a hairline `card-edge` border, `radius-lg` and `shadow-md`, 15/20 semibold `ink` text, an icon at 20; a small tail on one side points at the thing. It pops in over 200ms (no motion with reduced motion).
- **One at a time, and only when it helps:** shown after the person has tried the wrong way (for example, four digits dialed with the handset down), never as decoration. It goes away by itself after about 10 seconds, when they do the thing themselves, or when they tap it.
- The whole bubble is the button: at least 44px tall, a visible focus ring, and its text is its name. Say the same words in the page's live status line so screen readers hear it.
- Words: an instruction for a child, short and kind ("Pick up the handset first, then dial"). No questions, no errors (use an Alert), nothing that needs a choice (use a Sheet).

## HTML

```html
<button type="button" class="tl-hint tl-hint--down">
  <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><!-- phone --></svg>
  <span class="tl-hint__text">Pick up the handset first, then dial</span>
</button>
```
