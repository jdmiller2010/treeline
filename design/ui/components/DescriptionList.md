# DescriptionList

Label and value pairs on a detail page: a phone's model, last check-in, Wi-Fi.

**Consumer provides:** `items` (`label`, `value`).

- Two columns: labels in `ink-muted` at about a third of the width, values in `ink`, hairline `line` rules between rows, 15/22 text.
- **Under 400px of content** each pair stacks: the label small on top, the value under it.
- Use it inside a Card for facts. For anything a parent can change, use a form; for a list of people or calls, use rows. This is what we use instead of tables.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Phone details**

```html
<dl class="tl-dl">
  <div class="tl-dl__row">
    <dt>Phone</dt>
    <dd>Sam’s rotary phone</dd>
  </div>
  <div class="tl-dl__row">
    <dt>Last check-in</dt>
    <dd>Today, 4:12 pm</dd>
  </div>
  <div class="tl-dl__row">
    <dt>Wi-Fi</dt>
    <dd>Bennett-Home</dd>
  </div>
  <div class="tl-dl__row">
    <dt>Software</dt>
    <dd>1.4.2, up to date</dd>
  </div>
</dl>
```
