# CardFile: the softphone's phone book, a rotary card file of approved strings, as a design-system component.
# Builds its markup (from desk.py's drawing), its behavior, its React version, styles and types, into the kit and bundle.
import json, re, sys
sys.path.insert(0, "/home/claude/treeline/build/phone")
import desk

P = "/home/claude/treeline/project/components/"
KJS = "/home/claude/treeline/build/treeline_js.txt"
VB = "636 452 312 296"                       # the drawing's frame: the stand, the fan and the front card

def svg(pfx="tlc"):
    """The card file's drawing with its front card, ids prefixed so several can share a page."""
    x, y, w, h = desk.CARD
    fr = desk.rrect(x, y, w, h, 4)
    hand = "font-family=\"Caveat, 'Comic Sans MS', cursive\""
    card = (f'<g class="tl-cardfile__card">'
            f'<path d="{fr}" fill="#fffaf0"/>'
            f'<path d="M{x+8} {y+26} L{x+w-8} {y+26}" stroke="{desk.BERRY}" stroke-width="1" opacity=".55"/>'
            + "".join(f'<path d="M{x+8} {yy} L{x+w-8} {yy}" stroke="{desk.SKY}" stroke-width=".8" opacity=".4"/>' for yy in (y+52, y+78))
            + f'<g {desk.WOB}><path d="{fr}" {desk.LN}/></g>'
            f'<text class="tl-cardfile__name" x="{x+12}" y="{y+46}" {hand} font-size="25" font-weight="700" fill="{desk.INK}">The Parks</text>'
            f'<text class="tl-cardfile__num" x="{x+12}" y="{y+74}" {hand} font-size="29" fill="{desk.SKY}">3317</text>'
            f'<text class="tl-cardfile__count" x="{x+w-10}" y="{y+19}" text-anchor="end" {desk.SANS} font-size="9.5" fill="#857b6b">1 of 3</text>'
            '</g>')
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-cardfile__art" viewBox="{VB}" aria-hidden="true" focusable="false">'
         f'{desk.defs()}{desk.card_file()}{card}</svg>')
    return s.replace('id="tls-', f'id="{pfx}-').replace("url(#tls-", f"url(#{pfx}-")

ART = svg("TLCPFX")

logic = r'''  // ---------- CardFile: the phone book, a rotary card file of approved strings ----------
  // Markup: [data-tl-cardfile] with data-contacts='[{"name":"The Parks","number":"3317"}]' and a button holding the drawing.
  // Tap it (or press an arrow key on it) and it turns to the next card. Event: "tl-cardfile-card" { index, contact }.
  function attachCardFile(root) {
    if (root.__tlCardFile) return root.__tlCardFile;
    var list = [];
    try { list = JSON.parse(root.getAttribute("data-contacts") || "[]") || []; } catch (e) { list = []; }
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var i = 0, btn = root.querySelector(".tl-cardfile__btn"), hint = root.querySelector(".tl-cardfile__hint"), flipping = 0;
    function all(sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); }
    function show() {
      var c = list[i];
      all(".tl-cardfile__name", function (n) { n.textContent = c ? c.name : "No strings yet"; });
      all(".tl-cardfile__num", function (n) { n.textContent = c ? c.number : "ask a grown-up"; n.setAttribute("font-size", c ? "29" : "21"); });
      all(".tl-cardfile__count", function (n) { n.textContent = list.length > 1 ? (i + 1) + " of " + list.length : ""; });
      if (hint) hint.hidden = list.length < 2;
      if (btn) btn.setAttribute("aria-label", c
        ? "Phone book card: " + c.name + ", " + String(c.number).split("").join(" ") + (list.length > 1 ? ". Card " + (i + 1) + " of " + list.length + ". Tap for the next card." : ".")
        : "Phone book: no strings yet. A grown-up can add one in the parent app.");
    }
    // It turns like a real one: the front card tips toward you off the rod and drops away, the next swings up out of
    // the fan behind and settles with a small tick, and the fan rocks. Back: the same, reversed. Reduced motion: it just changes.
    function go(step) {
      if (list.length < 2) return;
      var animate = !reduce && typeof Element.prototype.animate === "function", fwd = step > 0, lag = flipping * 50;
      if (animate) {
        all(".tl-cardfile__card", function (card) {
          var old = card.cloneNode(true);
          old.classList.remove("tl-cardfile__card"); old.classList.add("tl-cardfile__card--falling");
          Array.prototype.forEach.call(old.querySelectorAll("[class]"), function (n) { n.removeAttribute("class"); });
          card.parentNode.appendChild(old);
          var away = fwd
            ? [{ transform: "none", opacity: 1 }, { transform: "translateY(2%) scaleY(.35)", opacity: 1, offset: .55 }, { transform: "translateY(9%) scaleY(-.12)", opacity: 0 }]
            : [{ transform: "none", opacity: 1 }, { transform: "translate(5%, -3%) scaleY(.82) skewX(-10deg)", opacity: .6, offset: .6 }, { transform: "translate(9%, -5%) scaleY(.7) skewX(-16deg)", opacity: 0 }];
          var a = old.animate(away, { duration: 320, delay: lag, easing: "cubic-bezier(.45,0,.8,.45)", fill: "both" });
          a.onfinish = function () { old.remove(); };
          var come = fwd
            ? [{ transform: "translate(9%, -5%) scaleY(.7) skewX(-16deg)", opacity: 0 }, { transform: "translate(2%, -1%) scaleY(.95) skewX(-4deg)", opacity: 1, offset: .55 }, { transform: "translateY(-1.5%) scaleY(1.02)", offset: .82 }, { transform: "none", opacity: 1 }]
            : [{ transform: "translateY(9%) scaleY(-.12)", opacity: 0 }, { transform: "translateY(2%) scaleY(.4)", opacity: 1, offset: .45 }, { transform: "translateY(-1.5%) scaleY(1.02)", offset: .82 }, { transform: "none", opacity: 1 }];
          card.animate(come, { duration: 420, delay: lag + 140, easing: "cubic-bezier(.2,.7,.3,1)", fill: "backwards" });
        });
        all(".tl-cf-fan", function (f) { f.animate([{ transform: "none" }, { transform: "rotate(" + (fwd ? -3 : 3) + "deg)", offset: .4 }, { transform: "none" }], { duration: 520, delay: lag, easing: "ease-in-out" }); });
      }
      flipping++; setTimeout(function () { flipping = Math.max(0, flipping - 1); }, 480);
      i = (i + step + list.length) % list.length; show();
      root.dispatchEvent(new CustomEvent("tl-cardfile-card", { bubbles: true, detail: { index: i, contact: list[i] } }));
    }
    if (btn) {
      btn.addEventListener("click", function () { go(1); });
      btn.addEventListener("keydown", function (e) {
        if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); go(1); }
        if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); go(-1); }
      });
    }
    show();
    var api = {
      next: function () { go(1); }, prev: function () { go(-1); }, index: function () { return i; },
      setContacts: function (c) { list = Array.isArray(c) ? c.slice() : []; i = Math.min(i, Math.max(0, list.length - 1)); root.setAttribute("data-contacts", JSON.stringify(list)); show(); }
    };
    root.__tlCardFile = api;
    return api;
  }
'''

component = r'''  var CARDFILE_SVG = __ART__;
  function CardFile(p) {
    var ref = React.useRef(null), pfx = useId(p.id).replace(/[^a-zA-Z0-9-]/g, "") + "-c";
    var cb = React.useRef(p); cb.current = p;
    var key = JSON.stringify(p.contacts || []);
    React.useEffect(function () {
      var root = ref.current, api = attachCardFile(root);
      function card(e) { if (cb.current.onCard) cb.current.onCard(e.detail.contact, e.detail.index); }
      root.addEventListener("tl-cardfile-card", card);
      if (p.apiRef) p.apiRef.current = api;
      return function () { root.removeEventListener("tl-cardfile-card", card); };
    }, []);
    React.useEffect(function () { if (ref.current && ref.current.__tlCardFile) ref.current.__tlCardFile.setContacts(p.contacts || []); }, [key]);
    var art = React.useMemo(function () { return CARDFILE_SVG.split("TLCPFX").join(pfx); }, [pfx]);
    return h("div", { ref: ref, className: cx("tl-cardfile", p.className), "data-tl-cardfile": "", "data-contacts": key },
      h("button", { type: "button", className: "tl-cardfile__btn", "aria-label": "Phone book", dangerouslySetInnerHTML: { __html: art } }),
      p.hint === false ? null : h("p", { className: "tl-cardfile__hint", hidden: (p.contacts || []).length < 2 }, p.hint || "Tap for the next card"));
  }
'''.replace("__ART__", json.dumps(ART))

BEGIN, END = "  // >>> cardfile\n", "  // <<< cardfile\n"
def put(src, block, anchor):
    if BEGIN in src:
        a, b = src.index(BEGIN), src.index(END) + len(END)
        return src[:a] + BEGIN + block + END + src[b:]
    i = src.index(anchor)
    return src[:i] + BEGIN + block + END + src[i:]

js = open(P + "bundle.js").read()
js = put(js, logic + component, "  // ---------- app layout ----------")
if "CardFile: CardFile" not in js:
    js = js.replace("RotaryPhone: RotaryPhone", "RotaryPhone: RotaryPhone, CardFile: CardFile", 1)
    assert "CardFile: CardFile" in js
first, rest = js.split("\n", 1)
if '{"name": "CardFile"}' not in first:
    assert '{"name": "RotaryPhone"}' in first
    first = first.replace('{"name": "RotaryPhone"}', '{"name": "RotaryPhone"}, {"name": "CardFile"}', 1)
open(P + "bundle.js", "w").write(first + "\n" + rest)

kt = open(KJS).read()
kt = put(kt, logic, "  function initRotaries()")
a = "function initRotaries() { document.querySelectorAll('[data-tl-rotary]').forEach(function (el) { attachRotary(el); });"
assert a in kt
if "attachCardFile(el)" not in kt:
    kt = kt.replace(a, a + " document.querySelectorAll('[data-tl-cardfile]').forEach(function (el) { attachCardFile(el); });", 1)
if "cardfile: attachCardFile" not in kt:
    kt = kt.replace("window.TreelineUI = { rotary: attachRotary,", "window.TreelineUI = { rotary: attachRotary, cardfile: attachCardFile,", 1)
assert "cardfile: attachCardFile" in kt
open(KJS, "w").write(kt)

css = '''
/* >>> CardFile — the phone book: a rotary card file of approved strings, drawn in the room's ink line and loose wash.
   It's an object, not UI chrome: it keeps its own colors in Lantern. The whole drawing is one button. */
.tl-cardfile { display: inline-flex; flex-direction: column; align-items: center; gap: var(--space-1); }
.tl-cardfile__btn { appearance: none; display: block; width: 100%; margin: 0; padding: 0; border: 0; background: none; cursor: pointer;
  border-radius: var(--radius-md); -webkit-tap-highlight-color: transparent; }
.tl-cardfile__btn:focus-visible { outline: 3px solid var(--focus); outline-offset: 4px; }
.tl-cardfile__art { display: block; width: 100%; height: auto; overflow: visible; }
.tl-cardfile__card, .tl-cardfile__card--falling { transform-box: fill-box; transform-origin: 50% 100%; }
.tl-cardfile .tl-cf-fan { transform-box: fill-box; transform-origin: 0% 100%; }
.tl-cardfile__hint { margin: 0; font: 400 13px/18px var(--font-sans); color: var(--ink-muted); }
.tl-cardfile__hint[hidden] { display: none; }
/* <<< CardFile */
'''
c = open(P + "bundle.css").read()
c = re.sub(r"\n/\* >>> CardFile.*?/\* <<< CardFile \*/\n", "", c, flags=re.S)
open(P + "bundle.css", "w").write(c.rstrip() + "\n" + css)

d = open(P + "index.d.ts").read()
if "CardFileProps" not in d:
    block = '''
export interface CardFileApi { next(): void; prev(): void; index(): number; setContacts(c: { name: string; number: string }[]): void }
export interface CardFileProps {
  /** The approved strings, one card each: a name and the 4-digit number. Empty: "No strings yet, ask a grown-up". */
  contacts?: { name: string; number: string }[];
  /** The line under it (default "Tap for the next card"; shown only with two or more cards); false for none. */
  hint?: string | false;
  /** Called when it turns to another card. */
  onCard?: (contact: { name: string; number: string }, index: number) => void;
  apiRef?: { current: CardFileApi | null };
  id?: string; className?: string;
}
export declare function CardFile(props: CardFileProps): any;
'''
    d = d.rstrip() + "\n" + block
    open(P + "index.d.ts", "w").write(d)
print("cardfile built", len(ART))
