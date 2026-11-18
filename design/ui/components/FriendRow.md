# FriendRow

One approved friend in a list: avatar, name, household, speed dial and what their phone is doing.

**Consumer provides:** `name`, optional `household`, `speedDial` (the digit kids press), `status` (as Presence), `action` (a node, usually an IconButton), `onClick` for opening details.

- Rows stack inside a Card, separated by hairlines that fade in and out at the ends (`--tl-fade-line`). No borders around single rows.
- The household is in `bark` with the `home` icon: it reminds parents whose family they approved.
- The speed-dial key looks like a phone key, so kids learn it: "Press 1 for Alex."

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**List of friends**

```html
<div class="tl-card tl-card--list">
  <div class="tl-row">
    <span class="tl-avatar tl-avatar--md tl-avatar--sun" role="img" aria-label="Alex">A<span class="tl-avatar__status tl-presence--canopy" aria-hidden="true">
      </span>
    </span>
    <div class="tl-row__main">
      <div class="tl-row__title">Alex</div>
      <div class="tl-row__meta">
        <span class="tl-household">
          <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>Alex&#x27;s house</span>
        <span class="tl-speeddial" aria-label="Speed dial 1">1</span>
        <span class="tl-presence tl-presence--canopy tl-row__presence-inline">
          <span class="tl-presence__dot" aria-hidden="true">
          </span>
          <span>Available</span>
        </span>
      </div>
    </div>
    <span class="tl-presence tl-presence--canopy">
      <span class="tl-presence__dot" aria-hidden="true">
      </span>
      <span>Available</span>
    </span>
    <button type="button" aria-label="Call Alex" title="Call Alex" class="tl-iconbtn tl-btn--primary tl-iconbtn--md">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
    </button>
  </div>
  <div class="tl-row">
    <span class="tl-avatar tl-avatar--md tl-avatar--moss" role="img" aria-label="Grandma Jo">GJ<span class="tl-avatar__status tl-presence--sunbeam" aria-hidden="true">
      </span>
    </span>
    <div class="tl-row__main">
      <div class="tl-row__title">Grandma Jo</div>
      <div class="tl-row__meta">
        <span class="tl-household">
          <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>Grandma</span>
        <span class="tl-speeddial" aria-label="Speed dial 2">2</span>
        <span class="tl-presence tl-presence--sunbeam tl-row__presence-inline">
          <span class="tl-presence__dot" aria-hidden="true">
          </span>
          <span>Ringing</span>
        </span>
      </div>
    </div>
    <span class="tl-presence tl-presence--sunbeam">
      <span class="tl-presence__dot" aria-hidden="true">
      </span>
      <span>Ringing</span>
    </span>
    <button type="button" aria-label="Call Grandma" title="Call Grandma" class="tl-iconbtn tl-btn--secondary tl-iconbtn--md">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
    </button>
  </div>
  <div class="tl-row">
    <span class="tl-avatar tl-avatar--md tl-avatar--pond" role="img" aria-label="Riley Park">RP<span class="tl-avatar__status tl-presence--sky" aria-hidden="true">
      </span>
    </span>
    <div class="tl-row__main">
      <div class="tl-row__title">Riley Park</div>
      <div class="tl-row__meta">
        <span class="tl-household">
          <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>Riley&#x27;s house</span>
        <span class="tl-speeddial" aria-label="Speed dial 3">3</span>
        <span class="tl-presence tl-presence--sky tl-row__presence-inline">
          <span class="tl-presence__dot" aria-hidden="true">
          </span>
          <span>Quiet hours</span>
        </span>
      </div>
    </div>
    <span class="tl-presence tl-presence--sky">
      <span class="tl-presence__dot" aria-hidden="true">
      </span>
      <span>Quiet hours</span>
    </span>
    <button type="button" aria-label="Riley details" title="Riley details" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md">
      <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
    </button>
  </div>
</div>
```
