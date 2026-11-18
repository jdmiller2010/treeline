# ProgressBar

How far along something is that takes a few seconds or more: a phone update, a search for the phone.

**Consumer provides:** `label`, optional `value` (0–100). Leave `value` out when you can't tell how long it'll take.

- An 8px rounded track with a `canopy` fill and the percentage on the right. Without a value it shows a sliding segment (holding still with reduced motion).
- Always with a label that says what's happening. If it takes under a second, show nothing; for a full-screen wait, use the LeafLoader.
- Full width of the card or sheet.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Known progress**

```html
<div class="tl-progress">
  <div class="tl-progress__head">
    <span>Updating the phone</span>
    <span>64%</span>
  </div>
  <div class="tl-progress__track" role="progressbar" aria-label="Updating the phone" aria-valuemin="0" aria-valuemax="100" aria-valuenow="64">
    <div class="tl-progress__fill" style="width:64%">
    </div>
  </div>
</div>
```

**Waiting (indeterminate)**

```html
<div class="tl-progress tl-progress--indeterminate">
  <div class="tl-progress__head">
    <span>Looking for the phone on your Wi-Fi</span>
  </div>
  <div class="tl-progress__track" role="progressbar" aria-label="Looking for the phone on your Wi-Fi" aria-valuemin="0" aria-valuemax="100">
    <div class="tl-progress__fill">
    </div>
  </div>
</div>
```
