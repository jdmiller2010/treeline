# Doodle

A tiny pencil-and-wash drawing placed on the page by hand, as if an artist had been through the screen with a pencil: a snail on a card's top edge, a butterfly in the gap between two cards. Decoration only: it takes no room, covers no text or control, and the page works the same without it.

**Consumer provides:** `name` (one of the set), and where it goes (`x`, `y`, `rotate`, `scale`, `flip`).
**Kinds:** `grounded` (stands on a surface, shadow tight below), `air` (flies in empty space, shadow far below, bobs), `cling` (attached at one end). The kind comes from the doodle's name.

The whole approach (physics, rules that never bend, different on every load, scenes, adding one) is in the design system README under **The artist's layer**. In the app it is automatic: `TLDoodles.scatter(main, pageKey)` from `/ui/js/doodles.js`, and `data-scene` on cards that have a scene.

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

## Always outside cards

Doodles stand on a card's top edge, sit in the gaps between cards, or drift in the margins, and are never drawn inside a card (a painted card keeps its own painting). A scene can be upgraded to a small watercolor painting on the card's top edge when the room above already holds it. All of it lives in the overlay layer and follows the sprinkle (often none). See the design system README, "The artist's layer".

## HTML

```html
<section class="tl-card">
  <!-- a grounded doodle: anchored by its feet to the card's top edge (--y:0) -->
  <svg class="tl-doodle tl-doodle--grounded tl-doodle--free" style="--x:84px;--y:0px;--r:-2deg;--s:1;--fx:1" viewBox="0 0 44 30" width="44" height="30" aria-hidden="true" focusable="false">…</svg>
  …
</section>
```

Static SVG exports of every doodle are in `assets/Doodles/`.
