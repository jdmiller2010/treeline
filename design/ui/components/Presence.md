# Presence

A dot and a word showing what a kid's phone is doing right now.

**Consumer provides:** `status` (`available` · `ringing` · `on-call` · `quiet` · `paused` · `offline`), optional `label` to override the word, optional `showIcon`.

- The word is always shown. The dot alone isn't enough: `canopy` and `berry` sit at the same lightness.
- `ringing` uses `sunbeam` with a soft halo. It's the only presence that glows.
- Write words from the kid's point of view: "Quiet hours", "Paused", never "Disabled" or "Unavailable".

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**available**

```html
<span class="tl-presence tl-presence--canopy">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <span>Available</span>
</span>
```

**ringing**

```html
<span class="tl-presence tl-presence--sunbeam">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>
  <span>Ringing</span>
</span>
```

**on-call**

```html
<span class="tl-presence tl-presence--canopy">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <span>On a call</span>
</span>
```

**quiet**

```html
<span class="tl-presence tl-presence--sky">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <span>Quiet hours</span>
</span>
```

**paused**

```html
<span class="tl-presence tl-presence--bark">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <span>Paused</span>
</span>
```

**offline**

```html
<span class="tl-presence tl-presence--neutral">
  <span class="tl-presence__dot" aria-hidden="true">
  </span>
  <span>Offline</span>
</span>
```
