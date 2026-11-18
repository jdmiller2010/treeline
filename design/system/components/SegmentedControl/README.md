# SegmentedControl

Switch between two to four views or modes of the same thing.

**Consumer provides:** `label` (read by screen readers), `options` (`value`, `label`, optional `icon`, `disabled`), `value`/`defaultValue`, `onChange`, optional `fullWidth`, `name`.

- A radio group on a `surface-sunk` pill track; the chosen segment is a raised `surface` pill with `shadow-sm`. 44px tall overall, so each segment is a full tap target.
- Two to four segments with one- or two-word labels. Icons only beside labels, never alone.
- Use it to filter or switch a view in place (Today · This week · All) or for a small mode choice (On · Quiet · Paused). For navigation between places, use NavBar. For a list longer than four, use Select.
- **Under 480px of content** it fills the width and segments share it equally; otherwise it sizes to its labels. `fullWidth` makes it fill at every size.
- Plain HTML needs no JavaScript: the segments are native radios.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Call log filter**

```html
<fieldset class="tl-segmented" aria-label="Show calls from">
  <label class="tl-segmented__opt">
    <input type="radio" name="calls-range" checked="" value="today"/>
    <span>Today</span>
  </label>
  <label class="tl-segmented__opt">
    <input type="radio" name="calls-range" value="week"/>
    <span>This week</span>
  </label>
  <label class="tl-segmented__opt">
    <input type="radio" name="calls-range" value="all"/>
    <span>All</span>
  </label>
</fieldset>
```

**With icons, full width**

```html
<fieldset class="tl-segmented tl-segmented--full" aria-label="Phone mode">
  <label class="tl-segmented__opt">
    <input type="radio" name="phone-mode" checked="" value="on"/>
    <span>
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>On</span>
  </label>
  <label class="tl-segmented__opt">
    <input type="radio" name="phone-mode" value="quiet"/>
    <span>
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>Quiet</span>
  </label>
  <label class="tl-segmented__opt">
    <input type="radio" name="phone-mode" value="paused"/>
    <span>
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5v14M15 5v14"/></svg>Paused</span>
  </label>
</fieldset>
```
