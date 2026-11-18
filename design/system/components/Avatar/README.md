# Avatar

A friend's initials on a watercolor pebble, with an optional presence dot.

**Consumer provides:** `name` (initials and fill come from it), `size` (`sm` 28 · `md` 40 · `lg` 64), optional `status` (as Presence), optional `tone` to pin a fill.

- No photos. Kids' faces never appear in Treeline; initials keep it friendly and private.
- The fill (`avatar-moss` · `acorn` · `pond` · `petal` · `sun`) is picked from the name, so the same friend always looks the same. It never means status.
- The pebble is almost round and a touch uneven, lit from the top-left with pigment pooling at the edge, like a dab of paint.
- Initials are set in Figtree semibold, `ink` on every fill in both themes. Not in Fraunces: its old-style letters (J, Q) drop below the line and sit off-center in a circle.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Large with status**

```html
<span class="tl-avatar tl-avatar--lg tl-avatar--sun" role="img" aria-label="Sam Lee">SL<span class="tl-avatar__status tl-presence--canopy" aria-hidden="true">
  </span>
</span>
```

**Medium**

```html
<span class="tl-avatar tl-avatar--md tl-avatar--moss" role="img" aria-label="Grandma Jo">GJ</span>
```

**Small**

```html
<span class="tl-avatar tl-avatar--sm tl-avatar--pond" role="img" aria-label="Ivy">I</span>
```
