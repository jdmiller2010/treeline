# Welcome

What Treeline is, in four small plates with a few words each: your treehouse, a string to a friend, kids pick up and dial, just a phone call. Read in under 20 seconds, a parent should know what it is and feel it is safe and simple. Only on the sign-in page.

**Consumer provides:** three steps, each `{ art, title, body }`. Build it with `welcome(steps)` from `web/shared/ui.js`.

- The four plates are read as one picture: the sign-in page's one plate (README, "Art direction"). They are existing art at 112px (`treehouse`, `connection`, the moss rotary phone lifted, and its handset alone), never new mascots.
- Each plate sits on its own soft white shape (`surface`, a hand-cut rounded blob, a light shadow), so they read as cards on a table. A title of two to five words in the display face and one or two short sentences under it. Not a feature list: the core idea, and enough to feel good about signing up.
- A plate is decoration (`aria-hidden`); the words carry the meaning. The list is labelled "How Treeline works".
- No picture touches the edge of its shape.
- Rows on every width: plate on the left, words on the right.

## HTML

See `ui/components/Welcome.html`.
