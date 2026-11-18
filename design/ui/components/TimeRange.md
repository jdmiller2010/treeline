# TimeRange

A start and end time, like quiet hours or homework time.

**Consumer provides:** `label` (the legend), `start`/`end` or `defaultStart`/`defaultEnd` (`HH:MM`), `onStartChange`, `onEndChange`, optional `startLabel` (default "From"), `endLabel` (default "Until"), `hint`, `id`.

- A fieldset: the legend, then two TimeFields side by side with "to" between them, then a hint.
- **Under 400px of content** the two fields stack and "to" drops; the "From" and "Until" labels carry it.
- Ranges that cross midnight are allowed and expected (8:00 pm until 7:00 am); say so in the hint.
- Used inside QuietHours' edit sheet and the Settings form. Capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Quiet hours**

```html
<fieldset class="tl-timerange">
  <legend>Quiet hours</legend>
  <div class="tl-timerange__row">
    <div class="tl-textfield tl-timefield">
      <label for="qh-start" class="tl-textfield__label">From</label>
      <div class="tl-textfield__control">
        <svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
        <input id="qh-start" class="tl-textfield__input" type="time" value="20:00"/>
      </div>
    </div>
    <span class="tl-timerange__to" aria-hidden="true">to</span>
    <div class="tl-textfield tl-timefield">
      <label for="qh-end" class="tl-textfield__label">Until</label>
      <div class="tl-textfield__control">
        <svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
        <input id="qh-end" class="tl-textfield__input" type="time" value="07:00"/>
      </div>
    </div>
  </div>
  <p class="tl-textfield__hint">Overnight is fine: 8:00 pm to 7:00 am.</p>
</fieldset>
```
