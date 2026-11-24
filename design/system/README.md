Treeline is a house-to-house phone network for kids who live near each other, with parents holding the keys. It should feel like a watercolor sketch of the best treehouse on the block: warm papyrus, ink line drawings, soft pigment that pools and fades, light coming through leaves. Airy first; playful in small, deliberate touches.

## The feel

- **Airy.** Lots of bare paper, generous spacing (`space-6` card padding, `space-8` between cards), one idea per card. When in doubt, take something away.
- **Watercolor.** Color arrives as translucent washes that pool in one corner and fade to clear paper. Edges stay soft: a faint `card-edge`, dividers that fade at both ends, warm shadows.
- **Paper, not screen.** The ground is solid warm papyrus (`canvas`). Cards are brighter sheets laid on top, clearly lifted by `card-edge` and `shadow-sm`. No texture.
- **Natural.** Leaf green (`canopy`) is for accents only, never a background. Warm wood (`bark`), sky (`sky`) and sunlight (`sunbeam`) do the washing.
- **Playful, quietly.** Round pebble shapes, slightly uneven hand-cut corners, a springy switch thumb, Fraunces' soft curves and the single `sunbeam` glow. Never confetti, emoji or mascots.
- **Trustworthy for parents.** Every rule a parent sets is visible and plain: who can call whom, when, and why a call didn't connect.

## Voice and writing

**Tagline:** *Safe calls for neighborhood kids.* It goes under the name wherever the name stands on its own: the top of the softphone page, the sign-in screen, the About card, the app's store and page descriptions. Set it in Fraunces italic, smaller than the name and in `ink-muted`, on one line where it fits (two on the business card). Don't reword it or add an exclamation mark.

Two readers: **kids** (on the phone itself and its prompts) and **parents** (in the app). Both get short, warm, plain sentences.

- Sentence case everywhere: "Quiet hours", "Approve Alex". The only all-caps text is the `overline` style.
- Use names, not roles: "Sam can call Alex", not "Child can call contact".
- Say what happens, not what the system does: "Calls wait until 7 am", not "Inbound routing suspended".
- Never scold or alarm. A blocked call is "Not approved by Riley's house", not "Unauthorized attempt". Waiting is calm ("Waiting"), never red.
- No exclamation marks, no emoji, no baby talk. Kids are smart; treat them that way.
- Numbers are digits ("3 friends", "12 min"); times are "7:30 pm" with a lowercase am/pm.
- Treehouse words are seasoning, not the meal: "Alex is in the treehouse" on a success card is fine; "Climb the ladder to settings" is not.

Real copy:

| Situation | Write |
| --- | --- |
| Mutual approval waiting | "Calls connect once Riley's house approves too." |
| Both approved | "Sam and Alex can call each other" |
| Quiet hours | "Calls wait until 7:00 am." |
| Blocked call in the log | "Not approved by Riley's house" |
| Paused phone | "No calls in or out until you turn this off." |
| Phone prompt (spoken) | "Sam's phone is sleeping right now. Try again in the morning." |

## Color

Two themes: **Daylight** (`light`, the default) and **Lantern** (`dark`, a treehouse at night). Always use tokens, never hex values, so both themes work.

- **Grounds.** `canvas` is warm papyrus for the page; `surface` is a lighter sheet for cards, inputs and dialogs; `surface-sunk` for wells and tracks; `surface-hover` for hover tints. Every card and sheet gets a 1px `card-edge` and `shadow-sm` so it stands clearly off the page.
- **No green backgrounds.** Pages, cards, rows and panels are never tinted green. Green appears only on buttons, switches, checkmarks, tags and small icon wells.
- **Cards must stand apart from the page.** A card is always a `surface` sheet with `card-edge` and `shadow-sm`. Never fill a card, panel or sheet with a color close to `canvas` (cream, sand, beige, pale yellow). Washes on a card pool in one corner and cover less than half of it, so the rest stays bright `surface`. Check it at arm's length: if the card's edge disappears, the wash is too big.
- **Text.** `ink` for primary text and icons; `ink-muted` for meta, hints and timestamps (4.5:1 on all grounds); `ink-faint` only for placeholders and disabled labels.
- **Lines.** `line` for decorative hairlines, always faded at both ends. `line-strong` for anything a person must see to use a control: input, checkbox and switch borders (3:1).
- **Canopy, the brand.** `canopy` is for primary actions, "on" states, checkmarks and links. Use **one** canopy button per view. Filled canopy is lit from above (`canopy-light` to `canopy`); text on it is `on-canopy`. `wash-leaf` and `canopy-soft` are for small things only: tags and icon wells, with `canopy-strong` text.
- **Bark, warmth.** `bark` and `bark-soft` mark households and anything parent-set like "Paused". Use them for warmth, not for actions.
- **Sky, calm.** `sky` and `sky-soft` mean quiet hours, night and information.
- **Sunbeam, play.** `sunbeam` is the one bright moment: a ringing phone, the Answer button, something new. Text on it is `on-sunbeam`. Sunbeam is a fill only. Never set text in sunbeam on light grounds.
- **Berry, danger.** `berry` for blocked calls, errors, End call and Remove. Text on it is `on-berry`. `berry-soft` sits behind error messages.
- **Avatars.** `avatar-moss`, `avatar-acorn`, `avatar-pond`, `avatar-petal` and `avatar-sun` are identity fills picked from a name. They never mean status.
- **Night.** `night`, `night-low`, `on-night`, `on-night-muted` and `moon` make the nighttime card, which is the one dark card allowed in Daylight. Use night only when it really is night for the kid (quiet hours on now, phone sleeping).
- **Washes.** `wash-sun`, `wash-sky`, `wash-bark`, `wash-petal`, `wash-leaf` and `wash-mist` are translucent pigments. Layer them over paper; they're tuned so `ink` and `ink-muted` stay readable on one or two overlapping layers.
- **Overlays.** `scrim` behind sheets and dialogs: a soft veil, not a blackout.

Colors never carry meaning alone. `canopy` and `berry` have about the same lightness, so every status also gets a word and an icon (`lock` for blocked, `moon` for quiet hours, `bell` for ringing).

## Watercolor

All of this lives in `components/bundle.css` as named recipes built from the wash tokens, so it works in both themes. Use them by name; don't hand-mix new gradients.

| Recipe | What it is | Use for |
| --- | --- | --- |
| `--tl-bloom-sun` | Sunlight pooling top-right, fading to clear | "Good news" cards: connected friends, a fun call |
| `--tl-bloom-sky` | Sky pooling in two corners | Information, night |
| `--tl-bloom-bark` | Wood wash from the top-left | Household and parent cards |
| `--tl-bloom-mist` | Warm neutral haze | Skeletons, waiting states |
| `--tl-dusk` | Sky at the top warming to petal at the bottom | Quiet hours |
| `.tl-card--breeze` | A watercolor leafy branch swaying in from the corner, loose leaves on the wind, warm light behind | Good news, play, a friend connected |
| `.tl-card--blossom` · `--oak` · `--fern` · `--seeds` · `--maple` | The same painted corner as breeze, in petal, bark, teal, sky or amber pigments | See "Art direction: one hand, three scales" |
| `.tl-card--night` | Deep night sky, crescent moon and a few stars | It's night for the kid right now |
| `--tl-fade-line` | A hairline that fades in and out | Dividers between rows |
| `--tl-canopy-fill` | `canopy-light` to `canopy` | Primary buttons, switches on, checkmarks |
| `--tl-organic` / `--tl-organic-sm` | Slightly uneven corners | Toned cards, panels, approval halves |

- **One bloom per card,** pooled in a corner and fading out before the middle. At least half of every card stays bright `surface`, so the card never blends into the papyrus page. Warm washes (`wash-sun`, `wash-bark`) are closest to the page color, so keep them tightest to their corner.
- **Washes fade to transparent,** never to another color, except `--tl-dusk`.
- **Toned cards keep their sheet:** the wash sits over `surface`, never directly on the page, so the card still stands out.
- **The page stays solid** `canvas`. No textures, noise or page-wide gradients.
- **Utility classes:** `.tl-wash--sun`, `.tl-wash--sky`, `.tl-wash--bark`, `.tl-wash--dusk`, `.tl-fade-line`.
- **Avoid:** hard gradient stripes, gradients on text, rainbow or blue-purple gradients, glassy blur effects.

## Typography

Two families, both under the SIL Open Font License. The HTML kit self-hosts them from `fonts/` (variable WOFF2, Latin and Latin Extended), so the app loads nothing from Google; the design system previews load them from Google Fonts:

- **Fraunces** (`--font-display`) for display, titles and clock times. A soft, old-style serif: the hand-lettered sign on the treehouse door. Always set `font-variation-settings: "SOFT" 100` for its rounded, ink-on-paper feel, at light weights (420–500).
- **Figtree** (`--font-sans`) for everything else, including avatar initials. Clean, round and very readable at small sizes.
- **The system monospace** (`--font-mono`, no web font), only for machine text a person reads as it is: the admin page's logs (`LogView`). Never for interface text.
- **Caveat**, only for handwriting drawn into a picture: the card file's cards (and the old softphone room's notes and drawing). Never for interface text.

| Style | Use for |
| --- | --- |
| `display-xl` 60/66 | Marketing heroes, the wordmark. One per screen at most. |
| `display-lg` 42/50 | Onboarding and empty-state headlines |
| `display-md` 32/40 | Screen titles in the parent app |
| `title-lg` 24/32 | Section and dialog titles |
| `title-md` 19/28 | Card titles in the sans; cards in Treeline components use Fraunces at 21/28 |
| `title-sm` 16/24 | Row titles (a friend's name) |
| `body-lg` 18/30 | Lead paragraphs, onboarding |
| `body` 16/26 | Default UI text |
| `body-sm` 14/22 | Meta lines, hints |
| `label` 14/20 | Buttons, tabs, field labels |
| `caption` 12/16 | Tags, timestamps, durations |
| `overline` 11/14 | Tiny section labels, uppercase, +0.08em |
| `numeral` 30/36 | Clock times and big counts, in Fraunces, with `font-variant-numeric: tabular-nums` |

- Headlines get slight negative tracking (built into the display styles). Body text is never tracked. Generous line heights keep text airy.
- Keep lines around 45–70 characters. Copy blocks stay under about 560px wide.
- Bold means a name or a key fact, not emphasis for its own sake.

## Spacing and layout

A 4px grid with spacing chosen by relationship: the closer two things are related, the less space between them, and space always grows from inside a control, to between controls, to card padding (`space-6`), to between cards (`space-8`), to between sections (`space-12`). Controls are 44px by default, every tap target is at least `touch-min`, text stays under `reading-max` and forms under `sheet-max`.

The full rules, with tables for spacing, insets, sizing, alignment, responsive behavior, app layout, phone and desktop versions of each component, the layout classes (`.tl-page`, `.tl-stack`, `.tl-cluster`, `.tl-split`, `.tl-grid`, `.tl-actions`) and a review checklist, are in the **Spacing, sizing and alignment** section.

## App layout and screen sizes

Every parent screen sits in one shell (`AppShell`): bottom tabs on phones, an icon rail on tablets, a labeled sidebar on desktop, always the same five places (Home, Strings, Calls, Phone book, Quiet hours). The shell follows the **window size** (compact under 768, medium 768–1023, expanded 1024+). Everything inside the page follows its **content size**, the room it actually has (narrow under 600, regular 600–959, wide 960+), so a card grid beside a sidebar behaves like it does on a tablet. Every screen is one of four templates: Overview, List and detail, Settings form, or Focused task (a bottom sheet on phones, a dialog on desktop). The section on spacing, sizing and alignment has the full rules and a phone-versus-desktop table for every component.

## Shape

Soft and organic, like river stones and hand-torn paper: nothing is sharp, and nothing is perfectly regular.

| Radius | Use for |
| --- | --- |
| `radius-xs` 6 | Checkboxes, speed-dial keys |
| `radius-sm` 10 | Small controls |
| `radius-md` 14 | Inputs, rows, menus |
| `radius-lg` 24 | Cards |
| `radius-xl` 36 | Sheets, dialogs, hero panels |
| `radius-pill` | Buttons, tags, switches, status dots, icon buttons, day pills |
| `--tl-organic` | Toned cards and panels: corners that differ by a few pixels, like a hand-cut sheet |

- Avatars and call-log icon wells are pebbles: almost round, a touch uneven (`48% 52% 50% 50% / 52% 48% 52% 48%`).

- Nested corners shrink: a `radius-md` row inside a `radius-lg` card.
- Cards and sheets have a 1px `card-edge`. Controls use `border-control` (1.5px) in `line-strong`, because people need to see them to use them.

## Elevation

Sheets of paper resting on paper. Shadows are a wide, warm haze, never a hard drop.

- `shadow-none`: anything on `surface-sunk`.
- `shadow-sm`: every card at rest (toned ones too), inputs, secondary buttons. A close contact shadow plus a wide warm haze.
- `shadow-md`: hovered cards, menus, the ringing card.
- `shadow-lg`: sheets and dialogs only, over `scrim`.
- `shadow-glow`: sunlight around a ringing phone and the Answer button. Nowhere else.
- Lantern (dark) shadows are deeper and darker so they still read on a dark `canvas`.

## Motion

Things fade in like pigment soaking into paper, and fade away rather than snapping off.

- Arrive: fade in and rise 6px over 420ms (`.tl-arrive`, easing `--tl-ease`). Stagger lists by 40ms.
- Leave: fade out over 240ms. Nothing slides off screen.
- Hover and press: 200ms. Buttons sink 1px on press; shadows bloom wider on hover.
- Switch thumb: 280ms with a slight overshoot (`cubic-bezier(.3, 1.4, .5, 1)`), the one bouncy moment.
- Sheets: slide up 240ms ease-out; fade the `scrim` in over 160ms.
- Ringing: a gentle `shadow-glow` that breathes every 1.6s. No shaking.
- Respect `prefers-reduced-motion`: drop transitions, arrivals and the glow entirely.

## Art direction: one hand, three scales

Everything pictorial in Treeline is by the same hand: a patient illustrator with a soft pencil and a small box of watercolors, working at a kitchen table. There are three scales of work, and they obey one grammar so they always sit well together.

| Scale | What | Where | How much |
| --- | --- | --- | --- |
| **Plates** | Illustrations, the logo, empty states | Page headers, empty and first-run states | One per page at most |
| **Painted cards** | Toned cards: breeze, blossom, oak, fern, seeds, maple (and plank, dusk, night as plain washes) | Cards whose meaning the painting carries | At most a third of the cards, never three in a row |
| **Marginalia** | Doodles, scenes and paintings (the artist's layer) | The edges of ordinary cards and the gaps between them, always outside the cards | A sprinkle: often none |

**The grammar (shared by all three)**

1. **Pencil line, then wash.** A soft graphite line (`ink-muted`, 1.2 to 1.5px, round caps) with one to three watercolor washes laid slightly off the line, as if painted without looking. Never a hard fill, never an outline in a bright color.
2. **Pigments come from the tokens.** Greens (`canopy`), warm browns (`bark`), sun yellows (`sun`), sky blues (`sky`), petal pinks (`petal`, `berry`). Nothing outside the palette; each tone has a pigment trio (a dark, a light, a wash) that flips for dark mode.
3. **Light comes from the top-right.** (A plant that grows from the ground, like the fern or the dandelion, rises from the bottom-right instead.) Washes pool in the top-right corner and fade out before the middle; shadows fall down and a little left. At least half of any card stays bright `surface`.
4. **Things are in the world.** A branch or a stem is attached to something; a plant stands on a surface; a butterfly may float. Nothing hovers without a reason.
5. **Drawn from life.** Plants are drawn as the plant really is: an oak leaf has rounded lobes and a midrib with side veins, an acorn a scaled cap and a pointed nut, a dandelion seed a tiny achene under a fan of fine rays, a fern pinnae that shrink toward the tip. If it could be any leaf, redraw it. **Botanical, never mascot.** Leaves, blossoms, acorns, ferns, seeds, maple leaves, small creatures at a glance. No faces, no cartoon characters, no emoji.
6. **The UI is never the picture.** Art goes in corners, on edges and in the gaps between cards; the artist's doodles never go inside a card. It never covers text or a control, and never changes spacing, alignment or size of a component; where a painting needs room, the words keep clear of it.
7. **Less is the style.** A page can have a few painted cards (at most a third of its cards, never three in a row) and a sprinkle of marginalia. When two pictures compete, the quieter one is removed.
8. **Gentle motion.** A branch sways, a butterfly bobs, a snail inches. Nothing loops fast; everything stops under reduced motion.

**Painted cards: which one, when**

| Tone | The meaning | Pigments | Used in the app |
| --- | --- | --- | --- |
| `breeze` | Good news, play: a friend connected | canopy greens | Home: newly strung |
| `blossom` | A welcome, a first, a celebration | petal pinks | Phone book: the header card (a directory of neighbors is a welcome). Also first-run and milestones |
| `oak` | Kept safe, kept close. A white-oak twig: lobed leaves with veins, acorns with scaled caps | bark browns | Home: Parent code |
| `fern` | Quiet, calm, nothing needed from you. Grows up from the lower-right corner (ferns come from the ground), the one painted card that is not top-right | teal greens | Home: Notifications |
| `seeds` | On its way, in the air, waiting on someone. A dandelion rooted at the lower-right, its seeds (a tiny achene under a fan of fine rays) floating up and away; the second painted card that grows from the bottom | sky blues | Home: Invite a friend's family (a first string on its way). Also "waiting on them" states |
| `maple` | The turning of the year, records, memory | sun and amber | Available |

The rule: at most a third of a page's cards are painted, never three in a row, and never every card. Choose the ones whose meaning the painting carries; the rest stay plain `surface`. The artist's layer leaves painted cards alone: no doodle is drawn on, in or from a toned card. To add a tone, draw it on a 150 × 120 canvas anchored top-right (a stem or branch, five to nine elements, a few loose pieces on the wind), keep the same line weight, give it a pigment trio and a meaning, and add it to the table above before using it.

## Nature touches

Treeline is a treehouse, and the interface says so quietly. Two layers do it, and neither changes the UI itself:

- **In the components.** `Steps` is a gust of wind carrying leaves along a line (the LeafLoader's look used as progress; a leaf only on a finished step). `LeafDivider` ends every page above the footer. The success `Toast` and the live "Strung" `Tag` carry a leaf instead of a check. `Card` with `sprig` puts a small pencil sprig in the corner of a treehouse card. All are drawn in the pencil-and-wash style, in existing tokens, with the LeafLoader's motion and nothing new.
- **Over the page: the artist's layer.** Doodles and scenes, below.

## The artist's layer: doodles and scenes

Treeline's interface is ordinary and calm. On top of it, an artist has been through the pages with a pencil and a little watercolor, drawing as if the screen were paper: a snail crawling along the top of a card, a bluebird on its edge, a butterfly drifting in the gap between two cards. The artist is not bound by the interface's rules (they cross a card's border, hang over a corner, trail a dotted path between two cards), but is bound by how the physical world works.

**The UI never changes.** A doodle is decoration laid over the page. It takes no room, moves nothing, and the product works exactly the same without it. This is enforced, not hoped for: doodles are drawn into one overlay layer at the end of `<body>` (placed by page coordinates), never inside the app's own markup, and the smoke test checks that every element sits exactly where it would without them.

### The set

Eighteen pieces in one hand (pencil `ink-muted` line, one to three washes, paper showing through). Exported as static SVGs in `assets/Doodles/` for graphics editors; drawn live from `ui/js/doodles.js` (`TLDoodles.SET`) and the React `Doodle` component.

| Doodle | Role | Means |
|---|---|---|
| `snail` | grounded | slow, patient (crawls the top of a card) |
| `ladybug` | grounded | luck, small and cheerful |
| `tuft` | grounded | grass with a wildflower |
| `sprout` | grounded | new, just started |
| `acorn` | grounded | kept safe, saved for later |
| `seeds` | air | carried on the wind |
| `bee` | air | busy, on its way |
| `butterfly` | air | change, something light |
| `blossom` | cling | friends, a twig reaching in |
| `tulip` | grounded | a gift, a welcome |
| `bow` | grounded | a little care, tied on |
| `pebbles` | grounded | a quiet stop |
| `mushroom` | grounded | the forest floor |
| `fern` | grounded | quiet, unfurling |
| `pinecone` | grounded | autumn, tucked away |
| `maple` | air | a leaf drifting down |
| `bluebird` | grounded | good news, perched |
| `owl` | grounded | watching over, night |

### Physics: how a doodle sits on the page

The interface already has a light from above (its shadows fall straight down). Doodles live in the same world.

- **Grounded** doodles stand or crawl on a surface: a card's top edge, a row divider, a button. They are anchored by their feet to that exact point, stay level (a few degrees of tilt at most), and cast a tight shadow straight down.
- **Air** doodles fly or drift through empty space: the gap between cards, the margin. They never touch a surface, bob very slowly, and cast a faint shadow far below to show how high they are. A bee leaves a dotted flight path.
- **Cling** doodles grow from or hang on an edge, attached at one end (a blossom twig over a card's corner).
- A doodle may be hidden by what is in front of it (an owl behind a card shows only its head), and may overhang an edge. That is the point of the layer.

### Rules that never bend

1. **Never over text or a control.** A doodle never covers a heading, body text, button, field, link or tag. Surfaces are chosen so it sits in the empty space around them.
2. **Takes no room.** Lives in the overlay layer (`.tl-doodle-layer`), never inside a component; adds no padding, margin or reflow; never makes the page scroll sideways. Scenes appear only where room already exists and are skipped otherwise; never add space for a doodle.
3. **Inert.** `aria-hidden`, no pointer events, no focus. Hidden when printed.
4. **Few, and a sprinkle.** Far between: often none, at most one on a phone, one or two on a wide screen, and many pages have none. Never on or inside a toned card. A spot that could take a doodle usually does not get one: the fun is in not knowing where, or whether. Quiet beats busy.
5. **Still when asked.** Under reduced motion nothing moves. Otherwise motion is tiny and slow: a bob of a few pixels, a snail that inches along over minutes.
6. **Fits or skips.** A doodle only appears where its surface has room for it. It is never shrunk to fit and never squeezed in.

### Alive: different every load

Placement is drawn at random every time the page loads, within the rules above: which doodles, which cards they stand on, where along the edge, which way they face, how big (a little). It stays put while you use the page (a re-render does not move them) and changes on reload and between pages. `TLDoodles.scatter(root, key)` does it; the seed is per page load, mixed with the page key.

### Scenes: a doodle that belongs to its card

Some cards have a small scene that fits what the card is about. Mark the card with `data-scene` and the artist draws that scene on its top edge when there is room, still within the rules. A page shows at most one scene on a phone and two on a wide screen (picked at random among its scened cards), so it never becomes a pattern.

| `data-scene` | Where | What |
|---|---|---|
| `sprout` | Setup, name your treehouse | a seedling with a butterfly above |
| `acorn` | Free (the app's Parent code is an `oak` card) | acorns and a sprout: kept safe, will grow |
| `forest` | Free | mushroom, grass tuft, pebbles: the forest floor |
| `fern` | Free | a fern and a ladybug: quiet |
| `bloom` | Free | a tulip, grass and a butterfly: a friendship in bloom |

### Always outside the cards, and paintings

- **Outside, always.** Doodles stand on a card's top edge, sit in the gaps between cards, or drift in the margins. They are never drawn inside a card: the card's own surface belongs to its content and, on a painted card, to its painting.
- **Paintings.** A scene can be upgraded to a small watercolor painting (`sprout` to a seedling, `forest` to mushrooms, `fern` to a fern, `bloom` to a meadow). The painting stands on the card's top edge and is used only when the room above the card already holds it at 60% of full size or more; otherwise the card keeps its doodle scene. Paintings are drawn from the same hand as the doodles. They share the same overlay layer and rules, and never add space for themselves.
- **The test.** The smoke suite measures every element with the doodles shown and hidden and fails on any difference, fails if a doodle is inside the app's own markup, fails if one covers text, and fails if one sits inside a card.

### Using it

- **App (HTML):** include `/ui/js/doodles.js`; call `TLDoodles.scatter(mainElement, pageKey)` after rendering a page. Add `data-scene="..."` to cards that have a scene. Nothing else.
- **React:** `<Doodle name="snail" kind="grounded" x={120} />` for a hand-placed one (design pages, docs). Props: `name`, `x`, `y`, `rotate`, `scale`, `flip`.
- **Adding a doodle:** draw it in the same hand (viewBox ~24 to 52 wide, a ground line at the bottom for grounded ones, 1.3 line, washes from `wash-*` tokens), give it a role (grounded, air or cling) and a meaning, add the SVG to `assets/Doodles/`, to `ui/js/doodles.js` and to the `Doodle` component, then list it in the table above.
- **Adding a scene:** add an entry to `SCENES` in `ui/js/doodles.js` and list it above. Name it for the card's meaning, not its look.
- **What not to do:** no doodles on forms the person is filling in, on error or safety copy (911, delete, danger), or on the phone screen. Do not add one to "fill space". Do not animate beyond a bob.

### Words go with it

Copy follows the same theme, plainly. A treehouse is a household, a string is a connection, a string code is how you make one, "the line" is the network. Safety, money and error copy stays plain: no cleverness where someone needs to be sure.

## Iconography

- Treeline icons are a single family: 24px grid, 1.75 stroke, round caps and joins, no fills. Every phone icon is the rotary phone, Treeline's signature object: `phone`, `phone-incoming` and `phone-outgoing` (with an arrow), and `phone-off` (struck through). Never use a modern handset. They're in the **Icons** asset group as SVG, and in the bundle as `Treeline.Icon` (drawn in `currentColor`).
- Sizes: `icon-sm` 16 in tags and small buttons, `icon-md` 20 in buttons and rows, `icon-lg` 24 standalone.
- Icons support words. They never replace them, except in well-known IconButtons (call, close, pause) with a `label`.
- No emoji as icons, ever. No filled or two-tone icons mixed in.

## Artwork and illustration

Treeline's art is **ink line drawing with loose watercolor** behind it, like a sketchbook page. The Illustration component (`treehouse`, `connection`, `quiet`, `sprig`) is the reference for everything new.

**Line**
- One ink line (`ink`, 1.6 at 240px wide), round caps and joins, the same family as the icons. Secondary lines (branches, ground, stars) use `ink-muted` at 1.3.
- Lines are hand-drawn but calm: tree crowns are uneven scallops, and shapes are left slightly open (a crown doesn't close at the trunk; the ground fades out).
- No fills inside line shapes, except tiny canopy leaves used as the one accent.

**Wash**
- Two or three washes per picture, from `wash-sky`, `wash-sun`, `wash-leaf`, `wash-bark`, `wash-petal`. Layer one wash over another for depth.
- Washes are offset from the lines, a few pixels off-register, as if painted after inking. They never fill a shape exactly.
- Leave paper showing. At least half of every picture is bare `canvas` or `surface`.

**Subjects**
- Trees and tree crowns, leaves and sprigs, treehouses, ladders, the string line between two houses, the rotary phone, sun, moon and sky.
- No people, faces, hands or characters. No animals with faces. Kids are present through what they make and use.
- No text inside artwork.

**Composition and use**
- One illustration per screen: empty states, onboarding, success moments. 160–280px wide, centered, with `space-8` or more around it.
- Never behind text, never cropped by a card edge, never as a full-bleed background.
- Leaves may drift (LeafLoader, falling leaves in `treehouse`), but artwork is otherwise still.

## Logo and app icon

**The logo: tree + line.** Two treehouses, each in its own tree, joined by a dotted string with a leaf hanging from it. It says the name literally (trees, and the line between them) and what Treeline does: a string between two houses, the tin-can phone every kid has made. It's drawn with the same hand as the illustrations, so the logo, the art and the UI read as one family.

- **Construction:** two open, scalloped crowns of different heights (the right one taller), simple roof-and-box treehouses with no windows on platforms tucked under each crown, two-line trunks, one hand-drawn ground line. The string runs from house to house as round dots, a little heavier than the line, and sags to a single leaf in the middle.
- **Line weight:** the same fine line as the illustrations (about 1.6 at illustration scale), so the logo and the art match. The dots are 1.5 × the line, spaced 2.2 × their width. Because the line is fine, the full logo starts at 96px; below that the small icon takes over: no houses, a solid string, and a line only a touch heavier so it still feels like the same drawing.
- **Color:** ink line; `bark` dots; `canopy` leaf; `wash-leaf` in each crown, `wash-sky` behind the right tree and a little `wash-sun` under the string, all slightly off the line.
- **Wordmark:** "Treeline" in Fraunces (weight 420, `SOFT` 100, -0.02em) to the right of the mark, its baseline on the treehouse platforms and its cap height about half the mark's height, with a gap of half a crown's width. Never stack the word under the mark, and never set the word without the mark in a header. The lockup files already have the word outlined, so they need no font.

### Which file, where

| Where | File | Size |
| --- | --- | --- |
| Phone home screen, app stores | `treeline-app-icon.svg`; for the stores use the kit's `logo/exports/app-icon-1024.png` (a full square; the stores round it) | 96px and up |
| Web app manifest | the kit's `logo/exports/app-icon-512.png` and `app-icon-192.png`, maskable | as listed |
| Favicon, notifications, tabs, anything under 96px | `treeline-app-icon-small.svg`: no houses, a solid string (dots disappear when small), the same light line just a touch heavier | 16–95px |
| Dark home screens (optional, iOS dark icon) | `treeline-app-icon-night.svg` | 96px and up |
| Sign-in, onboarding, website header, email header | `treeline-lockup.svg` (`treeline-lockup-reversed.svg` on dark) | 160–280px wide |
| App sidebar and rail | the `Brand` component (small mark + wordmark, theme-aware) | as built |
| Splash or loading screen | `treeline-logo.svg` centered, no wordmark, `LeafLoader` below it | 120–160px wide |
| Printed flyers, permission slips, stickers | `treeline-logo-mono.svg` or the full-color logo on white or cream paper | at least 25mm wide |
| On `night`, Lantern or any dark ground | `treeline-logo-reversed.svg` | 96px and up |

### Backgrounds

- **Full color** goes only on light, plain grounds: `canvas`, `surface`, `surface-sunk`, white or cream paper.
- **Reversed** goes on `night`, Lantern's `canvas` and `surface`, and any dark plain ground.
- **One color (ink)** goes on light grounds where color isn't available, or where the washes would muddy (kraft paper, a colored envelope that is still light).
- **Never on:** `canopy` or any green, `sky`, `sunbeam`, `berry`, a watercolor wash, a toned card (breeze, dusk, plank, night card content), a gradient, or a photo. If it must sit near a photo, put it on a `surface` plate with `radius-lg` and its clear space inside the plate.

### Clear space and minimum size

- **Clear space:** keep a margin of one left-crown width (about a fifth of the mark's width) clear on every side; nothing, not even text, inside it. In the lockup, the word sits half a crown's width from the right crown.
- **Inside the app icon,** the mark fills about 70% of the square's width, centered, the ground line about 30% up from the bottom edge. Don't add a border or a second background; the platform masks the corners.
- **Minimum size:** the full-color mark 96px wide on screen and 25mm in print; the lockup 160px wide; below that use the small icon (down to 16px).
- **Placement:** in headers, top-left, its left edge on the page gutter and vertically centered on the bar. On splash and sign-in, centered in the column with `space-12` above and below.

### Don'ts

Don't fill the crowns solid, make the string a solid line in the full-size logo, straighten or tighten the string, add a third tree, add windows or a door, flip or rotate it, stretch it, recolor the leaf or dots, add gradients, glows, shadows or outlines, outline the washes, animate it (the LeafLoader is the motion), or place it on a busy photo.

The rough concepts (tree line, lookout, string line, connected tree line) live on as illustrations: `treeline`, `lookout`, `connection` and `neighborhood`.

## Using illustrations

### Which one, when

| Illustration | Moment |
| --- | --- |
| `treehouse` | Welcome, first run, "no friends yet" |
| `lookout` | A kid's own page and household headers ("Sam's treehouse") |
| `treeline` | Sign-in, onboarding, about, the website hero on small screens |
| `connection` | An approval landing, "you're connected", a friend's first call |
| `neighborhood` | "Invite another family", a full friends list, the website hero on wide screens |
| `quiet` | Quiet hours, paused phones, night |
| `sprig` | A small ornament beside section headings and in `LeafDivider` |

### Size and spacing

- **One illustration per screen,** never two side by side and never repeated in a list.
- **Width:** 160–280px; `neighborhood` 280–360px; `sprig` 80–140px. Under 600px of content, never wider than the column minus its gutters, and never smaller than 120px (`sprig` 64px).
- **With text:** illustration first, then `space-6`, then the title, `space-3`, the body, `space-6`, the action. All centered, text capped at 420px (EmptyState does this).
- **In a header** (`lookout`, a section `sprig`): the art sits to the right of the title at 600px of content and up, top-aligned with the title, `space-6` between them; under 600 it moves above the title, left-aligned, at 160px.
- **Breathing room:** keep at least `space-8` of plain paper between the art and any card edge, and `space-10` from other art or imagery.

### Backgrounds

- **On screen,** use the `Illustration` component (or its HTML). It draws from tokens, so it's right in both Daylight and Lantern, on `canvas` or inside a `surface` card.
- **The SVG files** are drawn in Daylight colors: use them only on light grounds (`canvas`, `surface`, white or cream paper), such as emails, print and the website.
- **Never** on a toned card, a wash, a gradient, a photo, `night` (use `quiet` art in Lantern via the component instead), or behind text. Never as a repeating pattern or a full-bleed background.

### Don'ts

Don't recolor the line or the washes, crop the ground line, fill the crowns, add drop shadows or outlines, mix them with photos, emoji or clip art, stretch them, or combine pieces from two illustrations into one. New art follows the Artwork and illustration rules and matches the existing hand.

## States and accessibility

- **Contrast.** Every text pairing named in a token's usage note meets 4.5:1 in both Daylight and Lantern. Control borders, icons and the focus ring meet 3:1.
- **Focus.** One ring everywhere: a 2px solid `focus` outline (`border-focus`) with a 2px offset. Never remove it.
- **Disabled.** The whole control drops to `opacity-disabled` (0.45) and the cursor becomes not-allowed. Say why somewhere nearby.
- **Status.** Always a word plus an icon plus a tone (see Presence and Tag). Never color alone.
- **Hover** uses `wash-mist`. **Pressed primary** uses `canopy-strong`. **Selected** shows a canopy check or a lifted `surface` sheet, never a green background.
- **Errors** turn the field border and message `berry`, with a `close` icon and a message saying how to fix it.

## Using this system

- Load `tokens.css` (CSS variables for both themes; set `data-theme="dark"` on `<html>` for Lantern), then `components/bundle.css`, then React 18 and `components/bundle.js`. That last one exposes `window.Treeline`.
- `bundle.css` imports Fraunces and Figtree from Google Fonts, and defines the watercolor recipes and the artwork styles.
- Components: `Icon`, `Button`, `IconButton`, `Tag`, `Presence`, `Avatar`, `Switch`, `Checkbox`, `TextField`, `Card` (atoms and containers); `FriendRow`, `ApprovalCard`, `QuietHours`, `CallLogItem` (Treeline patterns); and `Illustration`, `EmptyState`, `LeafDivider`, `LeafLoader` (nature). Each has guidelines, a live preview and plain-HTML markup.
- **No React?** Every component's guidelines end with its exact HTML. Use it with `tokens.css`, `components/bundle.css` and, for switches, the few lines of script shown in Switch.
- Build anything new from tokens first, then from these components. If you need a new color, size or radius, add a token rather than a one-off value.
