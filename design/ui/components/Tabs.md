# Tabs

Switch between sections of one page, like a friend's Overview, Calls and Settings.

**Consumer provides:** `label`, `tabs` (`value`, `label`, `content`, optional `badge`), `value`/`defaultValue`, `onChange`, `id`. Plain HTML: `data-tl-tabs` on the wrapper and `js/treeline.js`.

- A row of 15px semibold labels on a hairline rule; the selected tab is ink with a 3px `canopy` underline. 44px tall. Panels sit `space-6` below.
- Arrow keys move between tabs and select them, Home and End jump to the ends; only the selected tab is in the tab order.
- **On phones** the row scrolls sideways if it doesn't fit (no scrollbar), and it never wraps. Keep to two to four short labels so it rarely needs to.
- Use Tabs to divide one thing's page into sections. Use SegmentedControl to filter the same list (Today · This week), NavBar to move between places.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. Add `js/treeline.js` for the behavior.

**Friend detail**

```html
<div class="tl-tabs" data-tl-tabs="">
  <div class="tl-tabs__list" role="tablist" aria-label="Alex">
    <button type="button" role="tab" id="alex-tab-overview" aria-selected="true" aria-controls="alex-panel-overview" tabindex="0" class="tl-tabs__tab">Overview</button>
    <button type="button" role="tab" id="alex-tab-calls" aria-selected="false" aria-controls="alex-panel-calls" tabindex="-1" class="tl-tabs__tab">Calls<span class="tl-badge tl-badge--quiet">3</span>
    </button>
    <button type="button" role="tab" id="alex-tab-settings" aria-selected="false" aria-controls="alex-panel-settings" tabindex="-1" class="tl-tabs__tab">Settings</button>
  </div>
  <div role="tabpanel" id="alex-panel-overview" aria-labelledby="alex-tab-overview" tabindex="0" class="tl-tabs__panel">
    <p class="tl-card__body">Speed dial 1. Approved by both families.</p>
  </div>
  <div role="tabpanel" id="alex-panel-calls" aria-labelledby="alex-tab-calls" tabindex="0" class="tl-tabs__panel" hidden="">
    <p class="tl-card__body">3 calls this week, 42 minutes.</p>
  </div>
  <div role="tabpanel" id="alex-panel-settings" aria-labelledby="alex-tab-settings" tabindex="0" class="tl-tabs__panel" hidden="">
    <p class="tl-card__body">Pause calls or remove Alex.</p>
  </div>
</div>
```
