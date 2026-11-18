# RadioGroup

Pick exactly one of a few choices, each of which needs a sentence to explain it.

**Consumer provides:** `label` (the legend), `options` (`value`, `label`, `description`, `disabled`), `value`/`defaultValue`, `onChange`, optional `variant` (`plain` default, or `cards`), `name`.

- A fieldset with a legend, then stacked rows: a 24px round control and a label with an optional description, `space-4` apart. The chosen dot is `canopy`; it pops in with the same spring as the switch.
- **Cards** variant: each choice is a bordered `surface` row; the chosen one gets a 2px `canopy` edge. Use it when there are two or three weighty choices.
- Use it for 2–5 choices that need a description. For a quick view switch use SegmentedControl; for many plain options use Select; for on/off use Switch.
- Always one option selected by default (the safest one). Labels say what happens, not "Option 1".
- Phones and desktop: the same, full width of the card, capped at `sheet-max`.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Plain**

```html
<fieldset class="tl-radiogroup">
  <legend>Who can call Sam</legend>
  <div class="tl-field-row">
    <span class="tl-radio">
      <input id="who-calls-approved" type="radio" name="who-calls" class="tl-radio__input" checked="" value="approved"/>
      <span class="tl-radio__dot" aria-hidden="true">
      </span>
    </span>
    <label for="who-calls-approved" class="tl-field-row__text">
      <span class="tl-field-row__label">Approved friends only</span>
      <span class="tl-field-row__desc">Both families said yes.</span>
    </label>
  </div>
  <div class="tl-field-row">
    <span class="tl-radio">
      <input id="who-calls-family" type="radio" name="who-calls" class="tl-radio__input" value="family"/>
      <span class="tl-radio__dot" aria-hidden="true">
      </span>
    </span>
    <label for="who-calls-family" class="tl-field-row__text">
      <span class="tl-field-row__label">Approved friends and family</span>
      <span class="tl-field-row__desc">Grandparents and relatives you add.</span>
    </label>
  </div>
  <div class="tl-field-row">
    <span class="tl-radio">
      <input id="who-calls-nobody" type="radio" name="who-calls" class="tl-radio__input" value="nobody"/>
      <span class="tl-radio__dot" aria-hidden="true">
      </span>
    </span>
    <label for="who-calls-nobody" class="tl-field-row__text">
      <span class="tl-field-row__label">Nobody right now</span>
      <span class="tl-field-row__desc">The phone can still call you.</span>
    </label>
  </div>
</fieldset>
```

**Cards**

```html
<fieldset class="tl-radiogroup tl-radiogroup--cards">
  <legend>Ring style</legend>
  <div class="tl-field-row">
    <span class="tl-radio">
      <input id="ring-style-classic" type="radio" name="ring-style" class="tl-radio__input" checked="" value="classic"/>
      <span class="tl-radio__dot" aria-hidden="true">
      </span>
    </span>
    <label for="ring-style-classic" class="tl-field-row__text">
      <span class="tl-field-row__label">Classic bell</span>
      <span class="tl-field-row__desc">The rotary phone’s own ring.</span>
    </label>
  </div>
  <div class="tl-field-row">
    <span class="tl-radio">
      <input id="ring-style-soft" type="radio" name="ring-style" class="tl-radio__input" value="soft"/>
      <span class="tl-radio__dot" aria-hidden="true">
      </span>
    </span>
    <label for="ring-style-soft" class="tl-field-row__text">
      <span class="tl-field-row__label">Soft chime</span>
      <span class="tl-field-row__desc">Gentler, for little sisters asleep.</span>
    </label>
  </div>
</fieldset>
```
