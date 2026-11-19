# Icon

A 24-grid line icon drawn with `currentColor`, so it takes the color of the text around it.

**Consumer provides:** `name` (one of `Treeline.iconNames`), optional `size` (16 / 20 / 24, from `icon-sm`…`icon-lg`), optional `label` when the icon stands alone and means something.

- 1.75 stroke, round caps and joins, no fills. Never mix in filled or two-tone icons.
- Pair an icon with a word for any status (ringing, blocked, quiet hours). Color alone never carries meaning.
- Decorative icons are `aria-hidden`; pass `label` only when there is no visible text.
- Use the SVG files in the Icons asset group where React isn't available. They are drawn in `ink` (#2a251c); recolor them in your tool.

| Name | Means |
| --- | --- |
| `phone` | Call, on a call: a rotary phone, Treeline's signature object |
| `phone-incoming` / `phone-outgoing` | Call log direction: the rotary phone with an arrow in or out |
| `phone-off` | Offline, missed, end call: the rotary phone struck through |
| `bell` | Ringing |
| `moon` / `sun` | Quiet hours / daytime |
| `pause` | Paused by a parent |
| `lock` | Blocked |
| `shield-check` | Approved, safe |
| `leaf` | Connected friends |
| `ladder` | Treehouse, invite in |
| `key` | Enter a code |
| `home` | Household |
| `users` | Friends list |
| `clock` | Time limits, waiting |
| `check` · `close` · `plus` · `chevron-right` | Utility |

## HTML

Inline any icon as an SVG. This is `phone`; every icon's markup is in the HTML kit's `components/Icon.html`.

```html
<svg class="tl-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z"/><path d="M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z"/><circle cx="12" cy="15.2" r="2.6"/></svg>
```
