# Illustrations

Ink line art over watercolor washes, drawn in Daylight colors for use as images. In code, use `Treeline.Illustration`, which draws the same pictures from tokens so they also work in Lantern.

- `treehouse.svg`: welcome, onboarding, "no friends yet"
- `connection.svg`: two treehouses joined by a string line; approvals and "you're connected"
- `quiet.svg`: a tree under the moon; quiet hours, paused phones
- `lookout.svg`: one big crown holding the treehouse, a ladder down and a pennant on the roof; profile and household headers, "your kid's treehouse"
- `treeline.svg`: three trees of different heights on one ground, the treehouse in the tallest; the name, onboarding, about
- `neighborhood.svg`: four treehouses strung together, a leaf on every string; the whole network, "invite another family", the friends list when it's full
- `sprig.svg`: a small branch ornament for headers
- `leaf-loader.svg`: the animated LeafLoader as a standalone image (CSS animation inside the SVG; it holds still with reduced motion)

## How to use them

- **One per screen,** 160–280px wide (`neighborhood` 280–360, `sprig` 80–140). Never below 120px (`sprig` 64), never wider than the column.
- **With text:** art, then `space-6`, the title, `space-3`, the body, `space-6`, the action; all centered, text capped at 420px.
- **In a header:** to the right of the title from 600px of content (top-aligned, `space-6` apart); above it, left-aligned at 160px, on phones.
- **Room:** at least `space-8` of plain paper to any card edge, `space-10` to other art.
- **Backgrounds:** these files are Daylight colors, so only light plain grounds: `canvas`, `surface`, white or cream paper (emails, print, the website). In the app use the `Illustration` component, which follows the theme.
- **Never** on a toned card, a wash, a gradient, a photo or `night`; never behind text, tiled, cropped, recolored, shadowed or combined with another illustration.

Full rules: the brand book, **Using illustrations**.


## Rotary phone (`rotary/`)

The softphone's 1960s desk phone, drawn in the same ink-and-watercolor hand but fully three-dimensional. In the app, use the `RotaryPhone` component, which turns the dial and lifts the handset; these files are for docs, the website, print and other tools.

- `rotary-phone-{moss,ivory,berry}.svg` and `…-lifted.svg`: the whole phone, on the hook and with the handset lifted.
- `softphone-desk.svg`, `softphone-desk-portrait.svg` and `softphone-desk-phone.svg`: the whole softphone room in one still picture, wide for landscape (1100 × 840), portrait for upright tablets (1000 × 1270) and tall for phones (600 × 1340): wall, corkboard, table, shelf and the moss phone on the hook, with sample words. For mockups and the store listing; the live screen is the `SoftphoneDesk` component.
- `rotary-part-1-deck.svg` … `rotary-part-7-glare-and-stop.svg`: the seven layers, back to front (deck, cord, handset, body with the number ring, the card behind the wheel, the finger wheel, the glare and finger stop), all on one 400 × 510 canvas (viewBox `0 -70 400 510`, with room on top for the lifted handset) so they stack exactly. The finger wheel turns about (200, 292) inside the dial's tilt (scale 1 × 0.93); the handset lifts and tips open by `translate(-4 -50) rotate(24 318 200)`, pivoting near the mouthpiece, and the cord is redrawn to follow it. Moss colors; the component sets any colorway through `--tlp-l/m/d/s`.
