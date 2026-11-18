# Slider

Pick a value on a range where the exact number matters less than the feel: ringer volume, call length.

**Consumer provides:** `label`, `min`, `max`, `step`, `value`/`defaultValue`, `onChange`, optional `unit` or `format`, `minLabel`, `maxLabel`, `id`.

- A native range input with a 6px track that fills with `canopy` up to a 24px paper thumb. The current value shows at the top right; end labels (Quiet · Loud) sit under the track.
- The whole control is 44px tall so it's easy to grab on a phone. Arrow keys step it.
- Plain HTML: `data-tl-slider="output-id"` (and `data-tl-unit`) on the input, and `js/treeline.js`, keep the fill and the number in step.
- If the exact value matters (a time, a count), use a Select or a field instead. Full width of the card, capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Ringer volume**

```html
<div class="tl-slider">
  <div class="tl-slider__head">
    <label for="ringer" class="tl-slider__label">Ringer volume</label>
    <output for="ringer" class="tl-slider__value" id="ringer-out">6</output>
  </div>
  <input id="ringer" type="range" min="0" max="10" step="1" class="tl-slider__input" data-tl-slider="ringer-out" aria-valuetext="6" style="--tl-fill:60%" value="6"/>
  <div class="tl-slider__ends" aria-hidden="true">
    <span>Quiet</span>
    <span>Loud</span>
  </div>
</div>
```

**Call length with unit**

```html
<div class="tl-slider">
  <div class="tl-slider__head">
    <label for="call-len" class="tl-slider__label">Longest call</label>
    <output for="call-len" class="tl-slider__value" id="call-len-out">30 min</output>
  </div>
  <input id="call-len" type="range" min="5" max="60" step="5" class="tl-slider__input" data-tl-slider="call-len-out" data-tl-unit="min" aria-valuetext="30 min" style="--tl-fill:45.45454545454545%" value="30"/>
</div>
```
