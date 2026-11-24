# Spacing, sizing and alignment

Treeline feels airy because space is used **consistently**, not just generously. These rules say which token to use, where and why. When a screen feels off, it's usually one of these rules being broken.

## 1. The grid

- **Everything sits on a 4px grid.** Use only the spacing tokens: `space-1` 4 · `space-2` 8 · `space-3` 12 · `space-4` 16 · `space-5` 20 · `space-6` 24 · `space-8` 32 · `space-10` 40 · `space-12` 48 · `space-16` 64 · `space-20` 80 · `space-24` 96.
- `space-0-5` (2px) is only for nudges inside a component (an icon beside text, a title and its meta). Never between components.
- **No in-between values.** If 24 feels too tight and 32 too loose, the content is probably grouped wrong; fix the grouping rather than inventing 28.
- Heights of controls, avatars and icons are multiples of 4 (`control-sm` 36, `control-md` 44, `control-lg` 52; `avatar-sm` 28, `avatar-md` 40, `avatar-lg` 72).

## 2. Spacing by relationship

Pick space by **how related two things are**. Closer means more related. Each step out the ladder gets more space than the one inside it, so grouping reads without lines or boxes.

| Relationship | Space | Token | Layout class |
| --- | --- | --- | --- |
| Icon beside its label; title and its meta line | 4–8 | `space-1`–`space-2` | `.tl-stack--tight` |
| Label and its field; heading and one line under it | 8 | `space-2` | `.tl-stack--related` |
| Items in one group (tags, buttons side by side) | 8–12 | `space-2`–`space-3` | `.tl-cluster`, `.tl-cluster--actions` |
| Fields in a form; settings in a list | 20 | `space-5` | `.tl-stack--group` |
| Section heading to its content | 16 | `space-4` | `.tl-stack` |
| Between cards | 32 | `space-8` | `.tl-stack--cards` |
| Cards in a grid (gap) | 24 | `space-6` | `.tl-grid` |
| Between sections of a screen | 48 (40 on phones) | `space-12` / `space-10` | `.tl-stack--sections` |
| Above a hero or empty state | 80–96 | `space-20`–`space-24` | |

- **Space outside a group is always bigger than space inside it.** A card's padding (24) is smaller than the gap to the next card (32). A form's field gap (20) is smaller than the gap to the next section (48).
- **Use gap, not margins.** Lay out siblings with a stack, cluster or grid gap. Don't put margins on components. Component tokens assume nothing outside them.
- **Text spacing comes from line height, not padding.** Paragraphs in a stack get `space-4` between them. Don't add top or bottom margins to type.

## 3. Insets (padding inside things)

| Element | Padding | Notes |
| --- | --- | --- |
| Card | `space-6` (24) all sides | Compact cards in dense lists: `space-5` (20) |
| List card (rows inside) | `space-1` (4) | The rows carry their own padding |
| Row | `space-4` (16) vertical, `space-5` (20) horizontal | Hairline dividers inset by `space-5` on both ends |
| Dialog / sheet | `space-8` (32) | `space-6` on phones |
| Button | `space-4` / `space-5` / `space-6` horizontal for sm / md / lg | Height comes from `control-*`, never from vertical padding |
| Tag | `space-3` horizontal, 26px tall | |
| Text field | `space-4` horizontal; `44px` left with an icon | |
| Empty state | `space-12` top and bottom, `space-6` sides | |
| Page | `gutter-sm` 20 / `gutter-md` 32 / `gutter-lg` 48 sides; `space-10`–`space-12` top | `.tl-page` |

- **Inset is even.** Use the same padding on all four sides of a card unless a row or full-bleed element needs to touch the edge.
- **Nested corners never exceed the outer corner minus the padding between them,** and never go below `radius-xs`. A row (`radius-md` 14) inside a list card (`radius-lg` 24, 4 padding) fits because 14 ≤ 20.

## 4. Sizing

**Controls**
- Default height is `control-md` (44). Use `control-lg` (52) for the main action on phones and `control-sm` (36) only in dense parent lists on desktop.
- Every tap target is at least `touch-min` (44 × 44), even when the visible control is smaller (a 36px icon button gets invisible padding or spacing to make up the rest).
- Buttons size to their label. Make them full width (`fullWidth`) only for the main action at the bottom of a phone screen or sheet.
- One size per row: don't mix `sm` and `md` buttons side by side.

**Icons and text**
- Pair icon sizes with text sizes: `icon-sm` 16 with 12–14px text (tags, meta, small buttons), `icon-md` 20 with 15–16px text (buttons, rows), `icon-lg` 24 standalone or in icon buttons.
- The only smaller marks are the checks inside a switch thumb (12) and a checkbox (14), and the icons inside the small round wells of an ApprovalCard (16).
- Icons keep their 24 grid at every size. Never stretch, crop or re-stroke them.

**Widths**
- Running text never exceeds `reading-max` (560, about 65 characters). Use `.tl-measure`.
- Forms, dialogs and single cards are at most `sheet-max` (440).
- The parent app's content column is at most `content-max` (960), centered.
- Illustrations are 160–280px wide; one per screen.
- Avatars: `avatar-md` (40) in rows, `avatar-sm` (28) in tags and dense lists, `avatar-lg` (72) in profile headers.

## 5. Alignment

- **One left edge.** Inside a card, text, fields and rows share the card's left padding edge. Don't indent sub-content unless it's a nested list.
- **Left-align text.** Center only empty states, onboarding steps and the illustration area of a dialog. Never center paragraphs longer than two lines.
- **Trailing actions align right** and center vertically on the row (`.tl-split`). In a card header, the action aligns to the title's first line (`.tl-split--top`).
- **Icons center on their text line.** With one line, use `align-items: center`. When text wraps, align the icon to the first line, not the middle of the block.
- **Numbers align right and use tabular figures** (`font-variant-numeric: tabular-nums`) wherever they're compared: durations in the call log, times, counts.
- **Rows align on their content,** not their borders: avatars, titles and trailing items line up down a list because every row uses the same padding and gap.
- **Actions go at the end, in one row, aligned left.** A card's, form's, sheet's or dialog's actions (`.tl-actions`) sit side by side at the bottom, aligned with each other and left-aligned as a group, at every width and in every container. The primary shows first (leftmost; write it last in the markup), the secondary after it. Buttons keep their natural width; the row wraps only if it can't fit. Never right-aligned, never stacked as full-width bars (`.tl-actions--stack` is kept for old markup and does nothing).
- **Optical alignment wins over math** for round things: a pebble avatar or a circular icon well can sit 1px off the grid to look centered. Nothing else should.

## 6. Responsive behavior

Treeline uses two kinds of size, and each rule says which one it means.

**Window size** is the width of the whole app (`.tl-app`). It decides the shell: where navigation goes and how big the top bar is.

| Window | Width | Navigation | Top bar | Sheets |
| --- | --- | --- | --- | --- |
| Compact (phones) | under 768 | Bottom tabs, `tabbar-h` | `appbar-h` 56, Figtree title, icon-only actions | Bottom sheet |
| Medium (tablets) | 768–1023 | Icon rail, `rail-w` 88 | `appbar-h-lg` 64, Fraunces title, labeled actions | Centered dialog |
| Expanded (desktop) | 1024 and up | Labeled sidebar, `sidebar-w` 248 | 64, aligned to the page column | Centered dialog |

**Content size** is the width of the area a component sits in (`.tl-app__main`, or `.tl-root` without the shell). It decides everything inside the page. Components never look at the window.

| Content | Width | Gutters | Card columns | Other |
| --- | --- | --- | --- | --- |
| Narrow | under 600 | `gutter-sm` 20 | 1 | Actions stack full width; sections `space-10` apart |
| Regular | 600–959 | `gutter-md` 32 | 2 from 640 (`.tl-grid--2`, `--3`) | List and detail show one pane at a time |
| Wide | 960 and up | `gutter-lg` 48 | 3 from 900 (`.tl-grid--3`); content centers at `content-max` | List and detail side by side; sections `space-12` apart |

A 1100px laptop has an expanded window (sidebar) but regular content (852px beside the sidebar), and that's intended: the page lays out for the room it actually has.

- Spacing tokens don't change between sizes. Only gutters, columns, section gaps and the shell do.
- Never shrink body type or controls on small screens. Reflow instead. The one heading that steps down is the AppBar title (Fraunces 24 to Figtree 19).
- These are container queries, so every screen must sit in `.tl-app` or `.tl-root`. Without one, the narrow rules never apply.

## 7. Layout classes

The HTML kit and `bundle.css` include these classes so the rules above don't have to be remembered:

| Class | Does |
| --- | --- |
| `.tl-app` / `.tl-app__layout` / `.tl-app__main` | The app shell (see section 9) |
| `.tl-root` | Size container for pages without the shell; put it on `<body>` |
| `.tl-listdetail` (+ `__list`, `__detail`, `__back`, `.is-detail`) | List and detail: one pane at a time under 960 content, side by side from 960 |
| `.tl-page` (+ `--narrow`: same left edge, content capped at `sheet-max`) | Centered page column with responsive gutters and top/bottom space |
| `.tl-stack` (+ `--tight`, `--related`, `--group`, `--cards`, `--sections`) | Vertical stack with the gap for that relationship |
| `.tl-cluster` (+ `--actions`) | Wrapping row of tags or buttons |
| `.tl-split` (+ `--top`) | Content left, trailing item right |
| `.tl-grid` (+ `--2`, `--3`) | Card grid: 1 column under 640 content, 2 from 640, 3 from 900 |
| `.tl-actions` | End-of-card, form, sheet or dialog actions: one row, left-aligned as a group, primary first, at every width (`--stack` is a no-op) |
| `.tl-measure` | Caps running text at `reading-max` |

```html
<main class="tl-page">
  <div class="tl-stack tl-stack--sections">
    <section class="tl-stack">
      <h2 class="title-lg">Approved friends</h2>
      <div class="tl-card tl-card--list">…FriendRows…</div>
    </section>
    <section class="tl-stack">
      <h2 class="title-lg">Schedules</h2>
      <div class="tl-grid tl-grid--2">…QuietHours…</div>
    </section>
  </div>
</main>
```

## 8. Review checklist

Before a screen ships, check:

1. Every gap and padding is a spacing token, with no 6, 10, 28 or 30.
2. Space grows outward: inside a control < between controls < card padding < between cards < between sections.
3. Every card has the same padding on all sides.
4. All text in a card starts at the same left edge.
5. Trailing actions line up down the list, and numbers are right-aligned with tabular figures.
6. Every tap target is at least 44 × 44.
7. No running text is wider than 560px, no form wider than 440px.
8. Only one primary (canopy) button, placed last in its actions row.
9. At 360px nothing scrolls sideways, main actions are full width and the bottom tabs are visible. At 1280px the page is centered and lines up with the AppBar.
10. Every card is clearly brighter than the page around it, with its edge visible.

## 9. App layout

### The shell

```
Phone (compact)          Tablet (medium)              Desktop (expanded)
┌──────────────────┐     ┌────┬─────────────────┐     ┌──────────┬──────────────────────┐
│ AppBar           │     │ ◦  │ AppBar          │     │ Treeline │   AppBar (aligned)   │
├──────────────────┤     │ ⌂  ├─────────────────┤     │ ⌂ Home   │                      │
│                  │     │ ☺  │                 │     │ ☺ Friends│    page column at    │
│  page, 1 column  │     │ ☎  │  page, 2 cols   │     │ ☎ Calls  │    content-max,      │
│                  │     │ ◷  │                 │     │ ◷ Quiet  │    2–3 cols          │
├──────────────────┤     │    │                 │     │──────────│                      │
│ ⌂   ☺   ☎   ◷    │     │    │                 │     │ Household│                      │
└──────────────────┘     └────┴─────────────────┘     └──────────┴──────────────────────┘
```

- Use `AppShell` (or its markup) for every signed-in parent screen. It holds `AppBar`, `NavBar`, the main area and an `overlay` slot for sheets.
- **Navigation** is the same five places in the same order everywhere: Home, Strings, Calls, Phone book, Quiet hours. There is no Settings page: the treehouse's settings (details, notifications, parent code, records, leaving) are sections at the bottom of Home, and Profile (the signed-in person) sits behind the avatar. Nothing else goes in the nav.
- **One `h1` per screen**, in the AppBar. Pages start with their first card or section heading (`title-lg`, as `h2`).
- **Scrolling:** the page scrolls; the AppBar and bottom tabs stay put. On desktop the sidebar stays put and the page scrolls beside it. Nothing inside a card scrolls on its own.
- **Safe areas:** bottom tabs and bottom sheets add `env(safe-area-inset-bottom)`. Add `viewport-fit=cover` to the page's viewport meta tag.
- **Keyboard:** the nav is a list of links in tab order before the page; sheets trap focus and close on Escape.

### Page templates

Every screen is one of these four. Pick the template, then fill it with components.

| Template | Used for | Phone (narrow) | Desktop (wide) |
| --- | --- | --- | --- |
| **Overview** | Home | One column: the one toned card (breeze or night) first, then today's summary, then waiting approvals, then sections | `.tl-grid--2` for the summary cards; sections below at full column width |
| **List and detail** | Friends, Calls | The list fills the screen; tapping a row opens its detail as the whole screen with a back button (`.tl-listdetail.is-detail`) | List at `list-pane` (360) on the left, detail beside it, sticky under the AppBar |
| **Settings form** | Quiet hours, a kid's phone, household | One column, cards full width, actions in a left-aligned row at the bottom | One column at `sheet-max` (`.tl-page--narrow`), left-aligned under the AppBar title, actions in a left-aligned row |
| **Focused task** | Approve a friend, pause a phone, confirm a change | Bottom sheet | Centered dialog |

- A screen shows at most one toned card (breeze, night, dusk or plank).
- Primary actions are reachable with a thumb on phones: in the AppBar, at the end of the content, or in a sheet. Never only in a hover menu.
- Empty screens use `EmptyState` inside a card, centered in the column, at every size.

### Markup

```html
<body>
  <div class="tl-app">
    <div class="tl-app__layout">
      <header class="tl-appbar">…</header>         <!-- AppBar -->
      <main class="tl-app__main">
        <div class="tl-page">…</div>               <!-- the template -->
      </main>
      <nav class="tl-nav" aria-label="Main">…</nav> <!-- NavBar -->
    </div>
    <!-- sheets go here, outside main, closed with hidden -->
  </div>
</body>
```

Full markup for each part is in the AppShell, AppBar, NavBar, Sheet, ListDetail and PageTemplates pages, and `app.html` in the HTML kit is a working screen that uses all four templates.

### Rules that break a screen if skipped

1. **A size container around every page.** Signed-in screens use `.tl-app`; anything else puts `.tl-root` on `<body>`. Content rules are container queries, so without one the phone layout never applies.
2. **No `backdrop-filter`, `transform` or `filter` on the AppBar or anything around a Menu.** They make a new containing block and trap the phone menu's bottom sheet.
3. **Keep `.tl-app__layout`.** The shell's grid sits one level in because a container can't restyle itself from its own query.
4. **Sheets and the toast region (`.tl-toasts`) are the last children of `.tl-app`, never inside main.** Main is a size container, and size containment traps fixed elements and z-index inside it. In plain HTML ship them closed with `hidden` and open them with `data-tl-open`.
5. **Sticky only works without a clipping ancestor.** Don't put `overflow: hidden` on `.tl-app`, `.tl-app__layout` or main, or the bar and tabs stop sticking.
6. **The list pane is a container; the detail pane isn't.** Rows in the list go compact in its 360px; the detail's back link and actions follow main's width.
7. **`viewport-fit=cover`** in the viewport meta tag, so bottom tabs and sheets can pad for the home indicator.
8. **Don't add width media queries to components.** If something needs to change with size, use `@container` with the content thresholds (480, 600, 640, 900, 960) or the shell thresholds on `tl-app` (768, 1024).
9. **Nothing scrolls sideways at 360.** Give flex and grid children `min-width: 0` and let text wrap.

## 10. Mobile and desktop, component by component

| Component | Phone (narrow content, compact window) | Desktop (wide content, expanded window) |
| --- | --- | --- |
| AppShell | Bar on top, tabs at the bottom, one column | Sidebar on the left, bar and page on one centered column |
| NavBar | Bottom tabs: icon over 12px label, current tab marked on its top edge | Sidebar: icon beside 15px label, 44px rows, household footer. Tablets get the icon rail |
| AppBar | 56 tall, Figtree 19 title, `collapse` buttons show icons only | 64 tall, Fraunces 24 title, labeled buttons, aligned to the page column |
| Sheet | Bottom sheet, grabber, actions in a left-aligned row, primary first | Centered 440 dialog, close button, actions in a left-aligned row, primary first |
| Menu | In the AppBar: action sheet from the bottom, 52px rows, scrim, tabs drop behind it. In the page: a popover, never wider than the column | Popover under its button, 44px rows, right-aligned |
| Alert | Full column width; actions wrap under the body | Full column width, top of the page or above what it's about |
| Toast | Centered just above the bottom tabs and the home indicator | Centered over the page column, `space-8` from the bottom, clear of the rail or sidebar |
| Select, TimeField | Full width of the card; the phone's own picker opens | Capped at `sheet-max`; the browser's picker opens |
| TimeRange | Under 400 content the two times stack and "to" drops | Two times side by side with "to" between |
| SegmentedControl | Under 480 content it fills the width, segments equal | Sizes to its labels unless `fullWidth` |
| RadioGroup, Textarea, PasswordField | Full width of the card | Capped at `sheet-max` |
| CodeInput | Under 400 content the boxes shrink and close up so six fit at 320 | Six 48 × 56 boxes |
| Slider | Full width; the whole control is 44px tall to grab | Capped at `sheet-max` |
| Steps | Under 560 content the names fold into one line: "Step 2 of 4: Add a kid" | Each bar has its name under it |
| ProgressBar, Skeleton | Full width of the card | Same |
| DescriptionList | Under 400 content each pair stacks, label on top | Two columns, labels at about a third |
| Disclosure / Accordion | Same | Same; answers capped at `reading-max` |
| StatTile | Tiles wrap to as many 140px columns as fit, often one or two | Three or four across |
| Tabs | The tab row scrolls sideways if it doesn't fit; never wraps | One row |
| Badge | On the icon in the bottom tabs | On the icon in the rail; at the end of the row in the sidebar |
| RotaryPhone | Fills the width up to 460, centered; the notice under it | Same, centered on the softphone screen |
| ListDetail | One pane at a time; tapping a row shows the detail with a back link | List at 360 beside the detail; no back link |
| Page templates | Single column; summary cards stack | Overview gets two summary cards; Settings form caps at 440 on the page's left edge |
| Button | In `.tl-actions` (cards, forms, sheets): natural width, in a left-aligned row, primary first | The same |
| IconButton | 40 visible, 44 tap area | Same |
| Card | Under 481 content: `space-5` padding; list cards keep `space-1` | `space-6` padding |
| Card grid | One column | Two columns from 640, three from 900 |
| FriendRow | Presence moves under the name; padding `space-4` | Presence trails on the right, aligned down the list |
| CallLogItem | Row padding tightens to `space-4`; the meta line wraps | Duration trails on the right, aligned down the list |
| ApprovalCard | The two households stack below 401px | Side by side |
| QuietHours | Time range and day pills wrap; the moon well drops | One row with the moon well |
| TextField, Switch, Checkbox | Full width of the card; labels never truncate | Capped at `sheet-max` (forms live in `.tl-page--narrow`) |
| Tag, Presence, Avatar | Same; clusters wrap | Same |
| EmptyState | Under 481 content: illustration at 180, action full width | Illustration at 220, action at natural width |
| Illustration | Never wider than its column | Drawn at its set width |
| LeafDivider, LeafLoader | Same | Same |
| Text | Running text fills the column | Capped at `reading-max` (560) |

## 11. Test widths

Check every screen at **360, 390, 768, 1024, 1280 and 1440**, in Daylight and Evening:

- 360 and 390: no sideways scroll, tabs visible, main actions full width, nothing under the home indicator.
- 768: the rail appears, cards go to two columns where the template says so.
- 1024: the sidebar appears; content may still be regular width, and that's correct.
- 1280 and 1440: the page centers at `content-max`; the AppBar title sits right above the first card; list and detail sit side by side.
