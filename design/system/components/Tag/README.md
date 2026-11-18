# Tag

A small pill of translucent wash for a state, a category or a count.

**Consumer provides:** `children` (one to three words), `tone` (`neutral` · `canopy` · `bark` · `sky` · `sunbeam` · `berry`), optional `icon`.

- Tones mean something: `canopy` approved or connected, `sky` quiet hours or info, `bark` household or paused, `sunbeam` new or ringing, `berry` blocked or error. Don't use them for decoration.
- Pair a status tone with its icon (`lock` for blocked, `moon` for quiet) so color is never the only signal.
- Sentence case. Never all-caps except `overline` section labels.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Neutral**

```html
<span class="tl-tag tl-tag--neutral">3 friends</span>
```

**Canopy**

```html
<span class="tl-tag tl-tag--canopy">
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 5-3 8.5-7 10-4-1.5-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>Approved</span>
```

**Bark**

```html
<span class="tl-tag tl-tag--bark">
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>Alex&#x27;s house</span>
```

**Sky**

```html
<span class="tl-tag tl-tag--sky">
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>Quiet 8 pm – 7 am</span>
```

**Sunbeam**

```html
<span class="tl-tag tl-tag--sunbeam">
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>New</span>
```

**Berry**

```html
<span class="tl-tag tl-tag--berry">
  <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>Blocked</span>
```
