# NavBar

Main navigation between the parent app's top-level places. One component, three looks.

**Consumer provides:** `items` (`icon`, `label`, `href`, `current`, `onClick`, optional `badge` count and `badgeLabel`), optional `brand` (defaults to the Treeline leaf and wordmark), `footer` (household name and a settings button; sidebar only), `label` (`aria-label`, default "Main").

- **Four destinations, always the same four, in this order:** Home (`home`), Friends (`users`), Calls (`phone`), Quiet hours (`clock`). Settings is not a tab: it lives behind the avatar in the AppBar on phones and in the sidebar footer on desktop.
- **Under 768, bottom tabs:** icon over a 12px label, equal widths, `tabbar-h` tall, a `surface` bar with a `card-edge` top line. The current tab gets a `canopy` bar along its top edge and a `canopy-strong` icon.
- **768–1023, icon rail:** `rail-w` wide, the leaf mark on top, icon over label, 64px tall items. The current item gets a `surface-sunk` pill and a `canopy` bar on its left edge.
- **1024 and up, sidebar:** `sidebar-w` wide, leaf and wordmark, icon beside a 15px label, 44px rows, household footer pinned to the bottom.
- A `badge` (berry count) marks a place that needs the parent, like waiting approvals on Friends: on the icon in the tabs and rail, at the end of the row in the sidebar. Plain HTML: wrap the icon in `.tl-badge-anchor` with a `.tl-badge` and a `.tl-sr` label (see Badge).
- Labels never disappear. Every item is a link with `aria-current="page"` on the current one.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Brand (inside the nav, or alone)**

```html
<a class="tl-brand" href="#home" aria-label="Treeline home">
  <span class="tl-brand__markwrap">
    <svg class="tl-brand__mark" viewBox="10 14 222 146" width="40" height="27" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M37.6 91.5A16.9 16.9 0 0 1 20.6 72.6A14.9 14.9 0 0 1 23.7 50.7A12.9 12.9 0 0 1 41.1 37.0A15.8 15.8 0 0 1 65.9 33.6A20.5 20.5 0 0 1 92.9 49.1A17.7 17.7 0 0 1 93.7 74.2A13.9 13.9 0 0 1 78.3 91.3"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M157.8 86.5A14.4 14.4 0 0 1 141.0 68.9A13.3 13.3 0 0 1 140.8 48.2A15.8 15.8 0 0 1 158.0 26.2A13.0 13.0 0 0 1 179.2 20.6A17.4 17.4 0 0 1 205.7 25.7A10.7 10.7 0 0 1 218.6 40.0A17.0 17.0 0 0 1 221.6 67.3A15.2 15.2 0 0 1 201.2 85.1"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M53 102C52 122 50 138 46 152M63 102C64 122 66 138 70 152M175 100C174 120 172 138 168 152M185 100C186 120 188 138 192 152"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M26 152C90 148 150 148 214 152"/><path fill="none" stroke="var(--bark)" stroke-width="4.16" stroke-linecap="round" d="M78 94Q119 132 158 92"/><path fill="var(--canopy)" transform="translate(118 112) rotate(64) scale(1.2)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></svg>
  </span>
  <span class="tl-brand__word">Treeline</span>
</a>
```

**Navigation (tabs, rail or sidebar by width)**

```html
<nav class="tl-nav" aria-label="Main">
  <div class="tl-nav__inner">
    <div class="tl-nav__brand">
      <a class="tl-brand" href="#" aria-label="Treeline home">
        <span class="tl-brand__markwrap">
          <svg class="tl-brand__mark" viewBox="10 14 222 146" width="40" height="27" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M37.6 91.5A16.9 16.9 0 0 1 20.6 72.6A14.9 14.9 0 0 1 23.7 50.7A12.9 12.9 0 0 1 41.1 37.0A15.8 15.8 0 0 1 65.9 33.6A20.5 20.5 0 0 1 92.9 49.1A17.7 17.7 0 0 1 93.7 74.2A13.9 13.9 0 0 1 78.3 91.3"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M157.8 86.5A14.4 14.4 0 0 1 141.0 68.9A13.3 13.3 0 0 1 140.8 48.2A15.8 15.8 0 0 1 158.0 26.2A13.0 13.0 0 0 1 179.2 20.6A17.4 17.4 0 0 1 205.7 25.7A10.7 10.7 0 0 1 218.6 40.0A17.0 17.0 0 0 1 221.6 67.3A15.2 15.2 0 0 1 201.2 85.1"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M53 102C52 122 50 138 46 152M63 102C64 122 66 138 70 152M175 100C174 120 172 138 168 152M185 100C186 120 188 138 192 152"/><path fill="none" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" stroke-linejoin="round" d="M26 152C90 148 150 148 214 152"/><path fill="none" stroke="var(--bark)" stroke-width="4.16" stroke-linecap="round" d="M78 94Q119 132 158 92"/><path fill="var(--canopy)" transform="translate(118 112) rotate(64) scale(1.2)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/></svg>
        </span>
        <span class="tl-brand__word">Treeline</span>
      </a>
    </div>
    <ul class="tl-nav__list">
      <li>
        <a class="tl-nav__item" href="#home" aria-current="page">
          <svg class="tl-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>
          <span class="tl-nav__label">Home</span>
        </a>
      </li>
      <li>
        <a class="tl-nav__item" href="#friends">
          <svg class="tl-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="8" r="3"/><path d="M3 19a6 6 0 0 1 12 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2A5 5 0 0 1 21 19"/></svg>
          <span class="tl-nav__label">Friends</span>
        </a>
      </li>
      <li>
        <a class="tl-nav__item" href="#calls">
          <svg class="tl-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
          <span class="tl-nav__label">Calls</span>
        </a>
      </li>
      <li>
        <a class="tl-nav__item" href="#quiet">
          <svg class="tl-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
          <span class="tl-nav__label">Quiet hours</span>
        </a>
      </li>
    </ul>
    <div class="tl-nav__foot">
      <div class="tl-split">
        <div class="tl-stack tl-stack--tight">
          <span class="tl-nav__house">Bennett house</span>
          <span class="tl-nav__meta">2 kids · 2 phones</span>
        </div>
        <button type="button" aria-label="Settings" title="Settings" class="tl-iconbtn tl-btn--quiet tl-iconbtn--sm">
          <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
        </button>
      </div>
    </div>
  </div>
</nav>
```
