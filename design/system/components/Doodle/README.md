# Doodle

A tiny pencil-and-wash drawing placed on the page by hand, as if an artist had been through the screen with a pencil: a snail on a card's top edge, a butterfly in the gap between two cards. Decoration only: it takes no room, covers no text or control, and the page works the same without it.

**Consumer provides:** `name` (one of the set), and where it goes (`x`, `y`, `rotate`, `scale`, `flip`).
**Kinds:** `grounded` (stands on a surface, shadow tight below), `air` (flies in empty space, shadow far below, bobs), `cling` (attached at one end). The kind comes from the doodle's name.

The whole approach (physics, rules that never bend, different every day, scenes, adding one) is in the design system README under **The artist's layer**. In the app it is automatic: `TLDoodles.scatter(main, pageKey)` from `/ui/js/doodles.js`, and `data-scene` on cards that have a scene.

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

## On a card's top edge, never over the card

Doodles stand on a card's top edge or fly in the gap above it, and are never drawn over a card's surface (a painted card gets none). Only a card standing in a `.tl-stack--sections` with something above it gets one: the room above it is then the stack's 48px gap (`--space-12`), and every doodle is drawn to fit 46px. `TLDoodles.scatter` adds an absolutely placed `.tl-doodle-spot` inside the card (it takes no room), and CSS places each doodle across the card by percentage, `--space-6` in from both edges. Nothing is measured. The paintings no longer appear in this layer: they don't fit the gap. All of it follows the sprinkle (often none). See the design system README, "The artist's layer".

## HTML

What `TLDoodles.scatter` writes into a chosen card:

```html
<section class="tl-card">
  …the card's own content…
  <span class="tl-doodle-spot" aria-hidden="true">
    <!-- a grounded doodle standing on the card's top edge, 62% of the way across -->
    <svg class="tl-doodle tl-doodle--grounded" data-doodle="snail" style="--at:62%;--hw:22px;--lift:0px;--fx:1;--r:-1deg" viewBox="0 0 44 30" width="44" height="30" aria-hidden="true" focusable="false">…</svg>
  </span>
</section>
```

A hand-placed doodle on a design page can still use `tl-doodle--free` with `--x`/`--y` (the React `Doodle` component does).
