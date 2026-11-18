# Menu

A short list of actions behind a button: the account menu, or "more" on a row.

**Consumer provides:** `items` (`icon`, `label`, `href` or `onSelect`, `danger`, or `{ separator: true }`), optional `trigger` (any button; defaults to a "more" IconButton), `label`, `header` (`name`, `meta`), `align` (`end` default, or `start`), `defaultOpen`, `id`. Plain HTML: give the trigger `data-tl-menu="panel-id"`, `aria-haspopup="menu"` and `aria-expanded`, give the panel that id and `hidden`, and `js/treeline.js` does the rest.

- **768 and up:** a popover under its button, right-aligned to it (`align="start"` for left), 232–320px wide, `surface` with `shadow-md`, 44px rows.
- **Under 768 (compact window), in the AppBar or nav:** the same panel becomes an action sheet from the bottom, full width with a grabber, 52px rows and the `scrim` behind it, padded for the home indicator; the bottom tabs drop behind the scrim.
- **Menus inside the page** (a row's "more") stay popovers on phones too, never wider than the column. Main is a size container, so a sheet inside it couldn't reach the bottom of the screen. If a row needs a big list of actions on phones, open a Sheet instead.
- Opens on click or tap, moves focus to the first item, arrow keys move between items, Escape or a tap outside closes it and returns focus to the button.
- **The account menu** sits on the avatar in the AppBar: header with the parent's name and household, then Settings, Household, Privacy and safety, a separator, and Sign out (danger) last. This is where Settings lives on phones.
- At most seven items. Destructive items go last, after a separator, in `berry`. Each item does one thing; no submenus.
- Don't put a menu inside a sheet; use the sheet's actions instead.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Account menu (closed)**

```html
<div class="tl-menu">
  <button type="button" class="tl-avatar-btn" aria-label="Account" aria-haspopup="menu" aria-expanded="false" aria-controls="account-menu" data-tl-menu="account-menu">
    <span class="tl-avatar tl-avatar--sm tl-avatar--petal" role="img" aria-label="Jordan Bennett">JB</span>
  </button>
  <div class="tl-menu__panel" id="account-menu" role="menu" hidden="" aria-label="Account">
    <div class="tl-menu__head">
      <span class="tl-menu__name">Jordan Bennett</span>
      <span class="tl-menu__meta">Bennett house</span>
    </div>
    <a role="menuitem" href="#settings" class="tl-menu__item">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>
      <span>Settings</span>
    </a>
    <a role="menuitem" href="#household" class="tl-menu__item">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>
      <span>Household</span>
    </a>
    <a role="menuitem" href="#privacy" class="tl-menu__item">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 5-3 8.5-7 10-4-1.5-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>
      <span>Privacy and safety</span>
    </a>
    <div class="tl-menu__sep" role="separator">
    </div>
    <button role="menuitem" type="button" class="tl-menu__item tl-menu__item--danger">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 4.5H6.5a1.5 1.5 0 0 0-1.5 1.5v12a1.5 1.5 0 0 0 1.5 1.5H10"/><path d="M15 8l4 4-4 4"/><path d="M19 12H9.5"/></svg>
      <span>Sign out</span>
    </button>
  </div>
</div>
```

**Row actions (open)**

```html
<div class="tl-menu">
  <button type="button" aria-haspopup="menu" aria-expanded="true" aria-controls="row-menu" data-tl-menu="row-menu" aria-label="Actions for Alex" title="Actions for Alex" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md">
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18" cy="12" r="1.2"/></svg>
  </button>
  <div class="tl-menu__panel" id="row-menu" role="menu" aria-label="Actions for Alex">
    <button role="menuitem" type="button" class="tl-menu__item">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5v14M15 5v14"/></svg>
      <span>Pause calls with Alex</span>
    </button>
    <button role="menuitem" type="button" class="tl-menu__item">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
      <span>See call history</span>
    </button>
    <div class="tl-menu__sep" role="separator">
    </div>
    <button role="menuitem" type="button" class="tl-menu__item tl-menu__item--danger">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      <span>Remove Alex</span>
    </button>
  </div>
</div>
```
