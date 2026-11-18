# AppBar

The top of every screen: where you are and the one or two things you can do here.

**Consumer provides:** `title`, optional `lead` (a back IconButton with `tl-iconbtn--back`), `actions` (Buttons with `collapse`, IconButtons, the parent's Avatar).

- **Under 768:** `appbar-h` (56) tall, title in Figtree 19/28 semibold, one line with an ellipsis. Action Buttons with `collapse` show their icon only, at 40 × 40, and keep the label for screen readers.
- **768 and up:** `appbar-h-lg` (64) tall, title in Fraunces 24/32 (`title-lg`), Buttons show their labels.
- **1024 and up:** the bar's content lines up with the page column (`content-max`, centered), so the title sits right above the first card.
- At most two actions plus the avatar. More than that belongs in the page.
- Top-level pages have no back button; detail pages have back and no avatar.
- This is the page's only `h1`. Don't repeat the title inside the page.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Top-level page**

```html
<header class="tl-appbar">
  <h1 class="tl-appbar__title">Home</h1>
  <div class="tl-appbar__actions">
    <button type="button" class="tl-btn tl-btn--secondary tl-btn--md tl-btn--collapse">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
      <span class="tl-btn__label">Add friend</span>
    </button>
    <span class="tl-avatar tl-avatar--sm tl-avatar--petal" role="img" aria-label="Jordan Bennett">JB</span>
  </div>
</header>
```

**Detail page with back**

```html
<header class="tl-appbar">
  <div class="tl-appbar__lead">
    <button type="button" aria-label="Back" title="Back" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md tl-iconbtn--back">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
    </button>
  </div>
  <h1 class="tl-appbar__title">Alex Rivera</h1>
</header>
```
