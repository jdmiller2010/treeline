# TimeField

Enter a time of day.

**Consumer provides:** everything TextField takes; `type` is always `time` and the clock icon is built in. `value` is `HH:MM` (24-hour); the browser shows it in the parent's own format (8:00 PM or 20:00).

- A native time input inside TextField's anatomy, so phones open their own wheel or clock. Tap anywhere on the field to open it.
- Numbers use tabular figures so times line up in a column.
- For a start and end, use TimeRange.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Time**

```html
<div class="tl-textfield tl-timefield">
  <label for="bedtime" class="tl-textfield__label">Bedtime</label>
  <div class="tl-textfield__control">
    <svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
    <input id="bedtime" class="tl-textfield__input" aria-describedby="bedtime-hint" type="time" value="20:00"/>
  </div>
  <p id="bedtime-hint" class="tl-textfield__hint">Calls wait after this.</p>
</div>
```
