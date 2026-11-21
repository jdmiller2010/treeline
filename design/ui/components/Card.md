# Card

A sheet of paper laid on the papyrus that groups related content.

**Consumer provides:** `children`, optional `title`, `eyebrow` (overline above the title), `action` (a node top-right), `tone` (`breeze` · `plank` · `dusk` · `night`, organic corners), `elevated` (`shadow-md`), `sprig` (a small pencil sprig in the top-right corner), `as` (element, default `section`).

- Default card: `surface` with paper grain and a faint mist bloom, no border, `radius-lg`, `shadow-sm`, `space-6` padding. Titles in Fraunces.
- Tones are for meaning. One toned card per view. Never a green card.
  - `breeze`: good news and play (a friend connected, kids out at the park). A watercolor leafy branch reaches in from the top-right corner and sways gently, with two loose leaves on the wind and a touch of warm sunlight behind it (`canopy-light`, `canopy-soft`, `wash-leaf`, `ink-muted`). The sway stops under reduced motion.
  - `night`: nighttime (the phone is sleeping, quiet hours are on now). A deep night-sky sheet (`night` to `night-low`) with a crescent `moon` and a few stars; text is `on-night` and `on-night-muted`, and the focus ring switches to `on-night`.
  - `dusk`: quiet hours as a setting, scheduled but not happening now. A sky wash over the sheet.
  - `plank`: households and parent notes. A wood wash in the top-left corner.
- Breeze cards reserve 96px of extra right padding so text never runs under the branch (the branch shrinks to 120 × 96 in narrow content); night cards reserve 44px for the moon.
- A toned card is still a bright `surface` sheet: its wash pools in one corner and covers less than half the card, so it never blends into the page.
- `sprig` is for the few cards about the treehouse itself (Treehouse settings, About). One or two a page, never on a toned card (the breeze branch and the moon already own that corner) and never on a card with an action or tag top-right.
- `data-scene="…"` on a card (`sprout`, `acorn`, `forest`, `fern`, `bloom`) lets the artist's layer draw a small scene on its top edge when there is room (see the design system README, "The artist's layer"). It changes nothing about the card.
- Space cards `space-8` apart. Don't nest cards; use rows inside.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. The branch, moon, stars and watercolor washes are all drawn by the stylesheet: no images or extra markup.

**Default**

```html
<section class="tl-card">
  <header class="tl-card__head">
    <div>
      <p class="tl-card__eyebrow">Today</p>
      <h3 class="tl-card__title">3 calls, 42 minutes</h3>
    </div>
    <button type="button" aria-label="Open call log" title="Open call log" class="tl-iconbtn tl-btn--quiet tl-iconbtn--sm">
      <svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
    </button>
  </header>
  <p class="tl-card__body">Sam talked with Alex and Grandma. No blocked calls.</p>
</section>
```

**Breeze (good news, out playing)**

```html
<section class="tl-card tl-card--breeze">
  <header class="tl-card__head">
    <div>
      <p class="tl-card__eyebrow">Good news</p>
      <h3 class="tl-card__title">Alex is in the treehouse</h3>
    </div>
  </header>
  <p class="tl-card__body">Both families approved. Speed dial 1.</p>
</section>
```

**Dusk (quiet hours setting)**

```html
<section class="tl-card tl-card--dusk">
  <header class="tl-card__head">
    <div>
      <p class="tl-card__eyebrow">Quiet hours</p>
      <h3 class="tl-card__title">8:00 pm – 7:00 am</h3>
    </div>
  </header>
  <p class="tl-card__body">Calls wait until morning.</p>
</section>
```

**Plank (household)**

```html
<section class="tl-card tl-card--plank">
  <header class="tl-card__head">
    <div>
      <p class="tl-card__eyebrow">Your house</p>
      <h3 class="tl-card__title">Parents: Jordan and Alex</h3>
    </div>
  </header>
  <p class="tl-card__body">Two kids, two phones, five approved friends.</p>
</section>
```

**Night (it is night now)**

```html
<section class="tl-card tl-card--night">
  <header class="tl-card__head">
    <div>
      <p class="tl-card__eyebrow">Tonight</p>
      <h3 class="tl-card__title">Sam’s phone is sleeping</h3>
    </div>
  </header>
  <p class="tl-card__body">Calls wait until 7:00 am.</p>
</section>
```
