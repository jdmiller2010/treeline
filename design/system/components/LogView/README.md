# LogView

Machine text shown exactly as it came: the Treeline Admin page's logs (`journalctl` output from the root helper). Admin screens only.

**Consumer provides:** the text (set as `textContent`, never as HTML), and optionally an `aria-label` naming what it shows.

- A quiet sunk panel (`surface-sunk`, a `line` border, `radius-md`) inside the Card that carries the title, the choices and the button.
- `--font-mono` at 13/20 (12/18 under 400px of content). Long lines wrap (`pre-wrap`, `overflow-wrap: anywhere`): the page never scrolls sideways.
- At most about 70% of the viewport tall; it scrolls inside itself. It is focusable (`tabindex="0"`) so a keyboard can scroll it.
- Empty: one line in `ink-muted`, the sans face (`.tl-logview__empty`): "Nothing logged in this time range."
- No doodles on it or near it (it is a working screen). No colours for log levels: the text is shown as it is.
