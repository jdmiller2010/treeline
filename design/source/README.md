# Drawing sources

The scripts that draw the softphone art. Run with Python 3; they write SVG.

- `rotary.py`: the rotary phone (layers, colorways, geometry the dial logic reads).
- `rotary_logic.js`: drag-to-dial and lift/hang-up, built into `components/bundle.js` and `ui/js/treeline.js`.
- `desk.py`: the softphone room (wall, corkboard, table, shelf, props) and its words layer.
- `cover.jpg`: a picture of the guide's real cover (page 0 of `desk_pages.py`, rendered with its fonts), laid onto the book on the table.
- `desk_pages.py`: the guide book's picture pages and the close-ups of the cards you can pick up.
- `desk_logic.js`: the card file's riffle, picking things up, and the book's pages, built into both bundles.
- `desk_build.py`: puts the room, logic, component, styles and types into the bundles (paths point at the design workspace).

The shipped results are in `design/system` and `design/ui`; edit there only through these.
