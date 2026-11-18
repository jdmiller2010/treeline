# Skeleton

Soft placeholders that hold the shape of a list or card while it loads.

**Consumer provides:** `variant` (`text`, `title`, `circle`, `row`), optional `width`, `size` (circle).

- `surface-sunk` shapes with a slow, gentle shimmer (still with reduced motion). `row` matches a FriendRow or CallLogItem: a 40px circle and two text lines.
- Show the same number of rows you expect (three is a good guess), inside the same card the content will fill, and mark the container `aria-busy="true"` with an `aria-label`.
- Only after about 300ms of waiting; quicker loads show nothing. For a whole-screen wait, use the LeafLoader.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**List loading**

```html
<div class="tl-card tl-card--list" aria-busy="true" aria-label="Loading friends">
  <div class="tl-skel-row" aria-hidden="true">
    <span class="tl-skel tl-skel--circle" style="width:40px;height:40px">
    </span>
    <span class="tl-skel-row__main">
      <span class="tl-skel tl-skel--text" style="width:45%">
      </span>
      <span class="tl-skel tl-skel--text" style="width:70%">
      </span>
    </span>
  </div>
  <div class="tl-skel-row" aria-hidden="true">
    <span class="tl-skel tl-skel--circle" style="width:40px;height:40px">
    </span>
    <span class="tl-skel-row__main">
      <span class="tl-skel tl-skel--text" style="width:45%">
      </span>
      <span class="tl-skel tl-skel--text" style="width:70%">
      </span>
    </span>
  </div>
  <div class="tl-skel-row" aria-hidden="true">
    <span class="tl-skel tl-skel--circle" style="width:40px;height:40px">
    </span>
    <span class="tl-skel-row__main">
      <span class="tl-skel tl-skel--text" style="width:45%">
      </span>
      <span class="tl-skel tl-skel--text" style="width:70%">
      </span>
    </span>
  </div>
</div>
```

**Card loading**

```html
<div class="tl-card" aria-busy="true" aria-label="Loading">
  <span class="tl-skel tl-skel--text" style="width:30%" aria-hidden="true">
  </span>
  <span class="tl-skel tl-skel--title" aria-hidden="true">
  </span>
  <span class="tl-skel tl-skel--text" style="width:90%" aria-hidden="true">
  </span>
  <span class="tl-skel tl-skel--text" style="width:70%" aria-hidden="true">
  </span>
</div>
```
