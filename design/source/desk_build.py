# Puts the SoftphoneDesk scene, logic, component, styles and types into the design system and the kit JS.
import json, re, sys
sys.path.insert(0, "/home/claude/treeline/build/phone")
import desk

P = "/home/claude/treeline/project/components/"
G = desk.GEOM
def pct(v, d): return f"{v / d * 100:.3f}%"

# Two drawings of the room (wide for tablets, tall for phones). Their filter and gradient ids differ
# (tls- and tlt-) so the hidden one never steals the other's references.
def ids(svg, k): return svg.replace('id="tls-', f'id="tl{k}-').replace("url(#tls-", f"url(#tl{k}-")
scene = desk.scene("wide") + ids(desk.scene("portrait"), "v") + ids(desk.scene("tall"), "t")
words = desk.words_template("wide") + ids(desk.words_template("portrait"), "v") + ids(desk.words_template("tall"), "t")
logic = open("/home/claude/treeline/build/phone/desk_logic.js").read()
import desk_pages
PICK = desk_pages.pickups(); PAGES = desk_pages.pages()
def look(kind, label, href_tok, attr_tok, link_label, note):
    return (f'<div class="tl-desk__look tl-desk__look--{kind}" hidden role="dialog" aria-modal="true" aria-label="{label}">'
            f'<div class="tl-desk__scrim" data-desk-close></div>'
            f'<div class="tl-desk__held tl-desk__held--{kind}"><a class="tl-desk__heldart tl-desk__heldart--{kind}" href="{href_tok}"{attr_tok} aria-label="{link_label}">{PICK[kind]}</a></div>'
            f'<p class="tl-desk__heldnote">{note}</p>'
            f'<button type="button" class="tl-desk__putback" data-desk-close>Put it back</button></div>')
assert len(PAGES) % 2 == 1, "the leaves take pages in pairs; the last page is the inside of the back cover"
sheets = "".join(f'<div class="tl-book__sheet"><div class="tl-book__face tl-book__face--front">{PAGES[2*k]}</div><div class="tl-book__face tl-book__face--back">{PAGES[2*k+1]}</div></div>' for k in range(len(PAGES) // 2))
book_look = ('<div class="tl-desk__look tl-desk__look--book" hidden role="dialog" aria-modal="true" aria-label="Rotary Phones the easy way">'
             '<div class="tl-desk__scrim" data-desk-close></div>'
             f'<div class="tl-book"><div class="tl-book__fly"><div class="tl-book__spread"><div class="tl-book__base">{PAGES[-1]}</div>{sheets}</div></div></div>'
             '<div class="tl-book__nav"><button type="button" class="tl-book__turn tl-book__prev" aria-label="Turn back a page">‹</button>'
             '<p class="tl-book__count" aria-live="polite"></p>'
             '<button type="button" class="tl-book__turn tl-book__next" aria-label="Turn the page">›</button></div>'
             '<button type="button" class="tl-desk__putback" data-desk-close>Close the book</button></div>')
looks = (book_look
         + look("coffee", "The Buy Me a Coffee certificate", "{{COFFEE}}", "{{COFFEEATTR}}", "Say thanks to the creator of Treeline: support the project on Buy Me a Coffee", "Tap it to say thanks")
         + look("card", "The business card", "mailto:{{EMAIL}}", "", "Email Jordan Miller, who made Treeline: {{EMAIL}}", "Tap it to send Jordan an email")
         + look("licenses", "The owner’s warranty", "{{LICENSES}}", "", "Read the open-source licenses", "Tap it to read every license"))

component = r'''
  var DESK_SVG = __SCENE__;
  var DESK_WORDS = __WORDS__;
  var DESK_LOOKS = __LOOKS__;
  function deskEsc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function deskMarkup(prefix, p) {
    var list = p.contacts || [], c = list[0], name = String(p.treehouseName || "Our treehouse");
    var art = DESK_SVG.replace(/id="tl([stv])-/g, 'id="' + prefix + '-$1-').replace(/url\(#tl([stv])-/g, "url(#" + prefix + "-$1-");
    var w = DESK_WORDS.split("{{NAME}}").join(deskEsc(name)).split("{{NAMESIZE}}").join(deskNameSize(name))
      .split("{{QUIET}}").join(deskEsc(p.quietTime || "not set"))
      .split("{{CNAME}}").join(deskEsc(c ? c.name : "No strings yet")).split("{{CNUM}}").join(deskEsc(c ? c.number : "ask a grown-up"))
      .split("{{CCOUNT}}").join(list.length > 1 ? "1 of " + list.length : "");
    w = w.replace(/id="tl([stv])-/g, 'id="' + prefix + '-$1-').replace(/url\(#tl([stv])-/g, "url(#" + prefix + "-$1-");
    return art + w;
  }
  function deskLooks(prefix, p) {
    var coffee = p.coffeeHref || "https://buymeacoffee.com/jdmiller";
    return DESK_LOOKS.replace(/id="tl([stvkb])-/g, 'id="' + prefix + '-$1-').replace(/url\(#tl([stvkb])-/g, "url(#" + prefix + "-$1-")
      .split("{{COFFEE}}").join(deskEsc(coffee)).split("{{COFFEEATTR}}").join(coffee.charAt(0) === "#" ? "" : ' target="_blank" rel="noopener"')
      .split("{{EMAIL}}").join(deskEsc(p.email || "jdmiller2010@gmail.com")).split("{{LICENSES}}").join(deskEsc(p.licensesHref || "#licenses"));
  }
  function SoftphoneDesk(p) {
    var ref = React.useRef(null), pfx = useId(p.id).replace(/[^a-zA-Z0-9-]/g, "") + "-d";
    var cb = React.useRef(p); cb.current = p;
    var key = JSON.stringify(p.contacts || []);
    React.useEffect(function () {
      var root = ref.current, api = attachDesk(root);
      function card(e) { if (cb.current.onCard) cb.current.onCard(e.detail.contact, e.detail.index); }
      function opened(e) { if (cb.current.onOpen) cb.current.onOpen(e.detail.item); if (e.detail.item === "book" && cb.current.onGuide) cb.current.onGuide(); }
      function closed(e) { if (cb.current.onClose) cb.current.onClose(e.detail.item); }
      function link(e) {
        var a = e.target.closest && e.target.closest(".tl-desk__heldart"); if (!a) return;
        if (a.classList.contains("tl-desk__heldart--licenses") && cb.current.onLicenses) cb.current.onLicenses(e);
        if (a.classList.contains("tl-desk__heldart--coffee") && cb.current.onCoffee) cb.current.onCoffee(e);
      }
      root.addEventListener("tl-desk-card", card); root.addEventListener("tl-desk-open", opened); root.addEventListener("tl-desk-close", closed); root.addEventListener("click", link);
      if (p.deskRef) p.deskRef.current = api;
      return function () { root.removeEventListener("tl-desk-card", card); root.removeEventListener("tl-desk-open", opened); root.removeEventListener("tl-desk-close", closed); root.removeEventListener("click", link); };
    }, []);
    React.useEffect(function () { if (ref.current && ref.current.__tlDesk) ref.current.__tlDesk.setContacts(p.contacts || []); }, [key]);
    var markup = React.useMemo(function () { return deskMarkup(pfx, p); }, [pfx, p.treehouseName, p.quietTime, key]);
    var looks = React.useMemo(function () { return deskLooks(pfx, p); }, [pfx, p.coffeeHref, p.email, p.licensesHref]);
    return h("div", { ref: ref, className: cx("tl-desk", p.fill && "tl-desk--fill", p.className), "data-tl-desk": "", "data-contacts": key },
      h("div", { className: "tl-desk__stage" },
        h("div", { className: "tl-desk__art", dangerouslySetInnerHTML: { __html: markup } }),
        h("div", { className: "tl-desk__phone" },
          h(RotaryPhone, { id: pfx + "-phone", number: p.number, colorway: p.colorway, ringing: p.ringing, online: p.online === undefined ? true : p.online, offHook: p.offHook, defaultOffHook: p.defaultOffHook,
            onDigit: p.onDigit, onHook: p.onHook, onPulse: p.onPulse, apiRef: p.apiRef, notice: false })),
        p.children ? h("div", { className: "tl-desk__slot" }, p.children) : null,
        h("p", { className: "tl-desk__sr" }, "This phone can’t call 911 or outside numbers. In an emergency, use a grown-up’s phone."),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--guide", "data-desk-open": "book", "data-turn": "0", "aria-haspopup": "dialog", "aria-label": "Open the guide book, Rotary Phones the easy way" }),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--cardfile tl-desk__cardfile", "aria-label": "Phone book" }),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--coffee", "data-desk-open": "coffee", "data-turn": "3", "aria-haspopup": "dialog", "aria-label": "Pick up the gift certificate" }),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--card", "data-desk-open": "card", "data-turn": "-3", "aria-haspopup": "dialog", "aria-label": "Pick up the business card: Treeline, made by Jordan Miller" }),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--licenses", "data-desk-open": "licenses", "data-turn": "-8", "aria-haspopup": "dialog", "aria-label": "Pick up the owner’s warranty card: open-source licenses" })),
      h("div", { className: "tl-desk__layers", dangerouslySetInnerHTML: { __html: looks } }));
  }
'''.replace("__SCENE__", json.dumps(scene)).replace("__WORDS__", json.dumps(words)).replace("__LOOKS__", json.dumps(looks))

BEGIN, END = "  // >>> desk\n", "  // <<< desk\n"
def put(src, block, anchor):
    if BEGIN in src:
        a, b = src.index(BEGIN), src.index(END) + len(END)
        return src[:a] + BEGIN + block + END + src[b:]
    i = src.index(anchor)
    return src[:i] + BEGIN + block + END + src[i:]

js = open(P + "bundle.js").read()
js = put(js, logic + component, "  // ---------- app layout ----------")
if "SoftphoneDesk: SoftphoneDesk" not in js:
    js = js.replace("RotaryPhone: RotaryPhone", "RotaryPhone: RotaryPhone, SoftphoneDesk: SoftphoneDesk", 1)
    assert "SoftphoneDesk: SoftphoneDesk" in js
if '{"name": "SoftphoneDesk"}' not in js.split("\n", 1)[0]:
    first, rest = js.split("\n", 1)
    assert '{"name": "RotaryPhone"}' in first
    js = first.replace('{"name": "RotaryPhone"}', '{"name": "RotaryPhone"}, {"name": "SoftphoneDesk"}', 1) + "\n" + rest
open(P + "bundle.js", "w").write(js)

kt = open("/home/claude/treeline/build/treeline_js.txt").read()
kt = put(kt, logic, "  function initRotaries()")
kt = kt.replace("function initRotaries() { document.querySelectorAll('[data-tl-rotary]').forEach(function (el) { attachRotary(el); }); }",
                "function initRotaries() { document.querySelectorAll('[data-tl-rotary]').forEach(function (el) { attachRotary(el); }); document.querySelectorAll('[data-tl-desk]').forEach(function (el) { attachDesk(el); }); }")
if "desk: attachDesk" not in kt:
    kt = kt.replace("window.TreelineUI = { rotary: attachRotary,", "window.TreelineUI = { rotary: attachRotary, desk: attachDesk,")
assert "desk: attachDesk" in kt and "attachDesk(el)" in kt
open("/home/claude/treeline/build/treeline_js.txt", "w").write(kt)

def layout_css(n, sel=""):
    g = G[n]; W, H = g["w"], g["h"]; ph = g["phone"]
    out = [f"{sel}.tl-desk__stage {{ width: min(100cqw, {W / H * 100:.3f}cqh); aspect-ratio: {W} / {H}; }}",
           f"{sel}.tl-desk__phone {{ left: {pct(ph['x'], W)}; top: {pct(ph['y'], H)}; width: {pct(ph['w'], W)}; }}"]
    out += [f"{sel}.tl-desk__hot--{k} {{ left: {pct(x, W)}; top: {pct(y, H)}; width: {pct(w, W)}; height: {pct(h, H)}; }}" for k, (x, y, w, h) in g["hotspots"].items()]
    return "\n".join(out)
css = f"""
/* >>> SoftphoneDesk — the tablet softphone screen: the phone on a side table in a 90s room.
   The room is a still picture drawn three ways, chosen by the screen's shape: wide (1100 × 890) for
   landscape tablets and desktops, portrait (1000 × 1304) for upright tablets, tall (600 × 1340) for phones.
   No wallpaper: the room sits on the page's canvas, so it works in Daylight and Lantern.
   Each is zoomed in on the phone and the table top so the dial and handset stay big. The phone and the props on it are live. */
.tl-desk {{ container-type: size; position: relative; width: 100%; height: 100dvh; overflow: hidden; display: flex; align-items: flex-end; justify-content: center;
  background: var(--canvas); }}
.tl-desk--fill {{ height: 100%; }}
.tl-desk__stage {{ position: relative; flex: none; }}
.tl-desk__art, .tl-desk__art > svg {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.tl-desk__art > .tl-desk__l--tall, .tl-desk__art > .tl-desk__l--portrait {{ display: none; }}
.tl-desk__phone {{ position: absolute; }}
.tl-desk__phone .tl-rotary {{ max-width: none; gap: 0; }}
.tl-desk__hot {{ position: absolute; display: block; padding: 0; border: 0; border-radius: 14px; background: none; cursor: pointer; -webkit-tap-highlight-color: transparent; }}
.tl-desk__hot:focus-visible {{ outline: var(--border-focus, 3px) solid var(--focus); outline-offset: 2px; }}
{layout_css("wide")}
/* The slot: the wall above the phone. For the app's few words (what the phone is doing, the connection
   light, a sleeping card). Keep it short: two lines. */
.tl-desk__slot {{ position: absolute; left: 2.5%; right: 77%; top: 50%; display: flex; flex-direction: column; align-items: center; gap: var(--space-2); text-align: center; color: var(--ink); }}
@container (aspect-ratio < 0.95) {{
.tl-desk__art > .tl-desk__l--wide {{ display: none; }}
.tl-desk__art > .tl-desk__l--portrait {{ display: block; }}
{layout_css("portrait")}
.tl-desk__slot {{ left: 2%; right: 79%; top: 46%; }}
}}
@container (aspect-ratio < 0.65) {{
.tl-desk__art > .tl-desk__l--wide, .tl-desk__art > .tl-desk__l--portrait {{ display: none; }}
.tl-desk__art > .tl-desk__l--tall {{ display: block; }}
{layout_css("tall")}
.tl-desk__slot {{ left: 32%; right: 42%; top: 2%; }}
}}
.tl-desk__card, .tl-desk__card--falling {{ transform-box: fill-box; transform-origin: 50% 100%; }}
.tl-cf-knob {{ transform-box: fill-box; transform-origin: 50% 50%; }}
.tl-cf-fan {{ transform-box: fill-box; transform-origin: 0% 100%; }}

/* Picking things up. Everything here is laid over the whole room. */
.tl-desk__layers {{ position: absolute; inset: 0; pointer-events: none; z-index: 20; }}
.tl-desk__look {{ position: absolute; inset: 0; pointer-events: auto; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-4); padding: var(--space-6) var(--space-4); }}
.tl-desk__look[hidden] {{ display: none; }}
.tl-desk__scrim {{ position: absolute; inset: 0; background: rgba(28, 22, 14, .58); opacity: 0; transition: opacity .32s ease; cursor: pointer; }}
.tl-desk__look.is-in .tl-desk__scrim {{ opacity: 1; }}
.tl-desk__held {{ position: relative; width: min(88cqw, 64cqh * 1.7, 620px); }}
.tl-desk__held--card {{ width: min(84cqw, 64cqh * 1.7, 560px); }}
.tl-desk__held--licenses {{ width: min(70cqw, 56cqh * .8, 400px); }}
.tl-desk__heldart {{ display: block; border-radius: 10px; filter: drop-shadow(0 22px 34px rgba(0, 0, 0, .35)); -webkit-tap-highlight-color: transparent; }}
.tl-desk__heldart svg {{ display: block; width: 100%; height: auto; }}
.tl-desk__heldart:focus-visible {{ outline: var(--border-focus, 3px) solid var(--focus); outline-offset: 6px; }}
.tl-desk__heldnote {{ position: relative; margin: 0; font: 700 26px/1.1 Caveat, "Comic Sans MS", cursive; color: #fff8ea; text-align: center; opacity: 0; transition: opacity .3s ease .25s; }}
.tl-desk__look.is-in .tl-desk__heldnote {{ opacity: 1; }}
.tl-desk__putback {{ position: relative; font: 600 16px/1 var(--font-sans); color: #2a251c; background: #fffaf0; border: 1.5px solid #2a251c; border-radius: 999px; padding: 12px 20px; min-height: 44px; cursor: pointer; box-shadow: 0 3px 0 #2a251c; opacity: 0; transition: opacity .3s ease .25s; }}
.tl-desk__look.is-in .tl-desk__putback {{ opacity: 1; }}
.tl-desk__putback:active {{ transform: translateY(2px); box-shadow: 0 1px 0 #2a251c; }}
.tl-desk__putback:focus-visible, .tl-book__turn:focus-visible {{ outline: var(--border-focus, 3px) solid var(--focus); outline-offset: 3px; }}
/* The guide book: two pages side by side, leaves that turn over from right to left. */
.tl-book {{ --p: min(46cqw, 38cqh, 340px); position: relative; width: calc(var(--p) * 2); height: calc(var(--p) * 450 / 300); cursor: pointer; touch-action: pan-y; }}
.tl-book__fly, .tl-book__spread {{ position: absolute; inset: 0; }}
.tl-book__spread {{ perspective: calc(var(--p) * 5); transform: translateX(calc(var(--p) * -.5)); transition: transform .6s ease; }}
.tl-book.is-open .tl-book__spread {{ transform: none; }}
.tl-book__base, .tl-book__sheet {{ position: absolute; left: 50%; top: 0; width: 50%; height: 100%; }}
.tl-book__base {{ border-radius: 0 6px 6px 0; overflow: hidden; box-shadow: 0 18px 30px rgba(0, 0, 0, .3); opacity: 0; transition: opacity .2s; }}
.tl-book.is-open .tl-book__base {{ opacity: 1; }}
.tl-book__sheet {{ transform-origin: left center; transform-style: preserve-3d; transition: transform .62s cubic-bezier(.45, .05, .25, 1); }}
.tl-book__sheet.is-turned {{ transform: rotateY(-180deg); }}
.tl-book__face {{ position: absolute; inset: 0; overflow: hidden; backface-visibility: hidden; -webkit-backface-visibility: hidden; background: #fbf6e9; }}
.tl-book__face--front {{ border-radius: 0 6px 6px 0; box-shadow: 0 18px 30px rgba(0, 0, 0, .28); }}
.tl-book__face--back {{ transform: rotateY(180deg); border-radius: 6px 0 0 6px; box-shadow: 0 18px 30px rgba(0, 0, 0, .28); }}
.tl-book__face--front::after, .tl-book__face--back::after {{ content: ""; position: absolute; top: 0; bottom: 0; width: 14%; pointer-events: none; }}
.tl-book__face--front::after {{ left: 0; background: linear-gradient(90deg, rgba(0, 0, 0, .16), transparent); }}
.tl-book__face--back::after {{ right: 0; background: linear-gradient(270deg, rgba(0, 0, 0, .16), transparent); }}
.tl-book__face svg {{ display: block; width: 100%; height: 100%; }}
.tl-book.is-instant .tl-book__sheet, .tl-book.is-instant .tl-book__spread {{ transition: none; }}
.tl-book__nav {{ position: relative; display: flex; align-items: center; gap: var(--space-4); opacity: 0; transition: opacity .3s ease .4s; }}
.tl-desk__look.is-in .tl-book__nav {{ opacity: 1; }}
.tl-book__turn {{ width: 48px; height: 48px; border-radius: 50%; border: 1.5px solid #2a251c; background: #fffaf0; color: #2a251c; font: 600 28px/1 var(--font-display); cursor: pointer; box-shadow: 0 3px 0 #2a251c; }}
.tl-book__turn:disabled {{ opacity: .35; cursor: default; }}
.tl-book__count {{ margin: 0; min-width: 7em; text-align: center; font: 700 22px/1 Caveat, "Comic Sans MS", cursive; color: #fff8ea; }}
@media (prefers-reduced-motion: reduce) {{ .tl-book__sheet, .tl-book__spread, .tl-desk__scrim, .tl-desk__heldnote, .tl-desk__putback, .tl-book__nav {{ transition: none; }} }}
.tl-desk__sr {{ position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
/* <<< SoftphoneDesk */
"""
c = open(P + "bundle.css").read()
c = re.sub(r"\n/\* >>> SoftphoneDesk.*?/\* <<< SoftphoneDesk \*/\n", "", c, flags=re.S)
open(P + "bundle.css", "w").write(c.rstrip() + "\n" + css)

d = open(P + "index.d.ts").read()
d = re.sub(r"\nexport interface DeskContact.*?\n}\n\n(?=export interface RotaryPhoneProps)", "\n", d, flags=re.S)
d = d.replace("\nexport declare function SoftphoneDesk(props: SoftphoneDeskProps): React.ReactElement;", "").replace(" SoftphoneDesk: typeof SoftphoneDesk;", "")
if "SoftphoneDeskProps" not in d:
    types = '''
export interface DeskContact { name: string; number: string; }
export interface SoftphoneDeskApi { setOnline(on: boolean | "connecting"): void; isOnline(): boolean; next(): void; prev(): void; setContacts(c: DeskContact[]): void; index(): number; open(item: "book" | "coffee" | "card" | "licenses"): void; close(): void; isOpen(): string | null; setName(name: string): void; setQuiet(text: string): void; setLinks(l: { coffee?: string; email?: string; licenses?: string }): void; }
export interface SoftphoneDeskProps {
  /** The treehouse's own 4 digits, shown in the middle of the dial. */
  number?: string;
  colorway?: "berry" | "moss" | "ivory";
  /** Written across the top of the kid's drawing on the wall. */
  treehouseName?: string;
  /** The approved strings, one card each in the card file (the phone book). */
  contacts?: DeskContact[];
  /** Written on the sticky note, e.g. "8 pm – 7 am". */
  quietTime?: string;
  guideHref?: string; onGuide?: (e: any) => void;
  coffeeHref?: string;
  licensesHref?: string; onLicenses?: (e: any) => void;
  email?: string;
  /** Passed to the RotaryPhone on the table. */
  offHook?: boolean; defaultOffHook?: boolean;
  onDigit?: (digit: number) => void; onHook?: (offHook: boolean) => void; onPulse?: (detail: any) => void;
  apiRef?: { current: RotaryPhoneApi | null };
  onCard?: (contact: DeskContact, index: number) => void;
  /** The phone is ringing: its handset trembles. */
  ringing?: boolean;
  /** Something was picked up ("book", "coffee", "card", "licenses") or put back. */
  onOpen?: (item: string) => void; onClose?: (item: string) => void; onCoffee?: (e: any) => void;
  deskRef?: { current: SoftphoneDeskApi | null };
  /** The line lamp on the phone: true (default, steady green), "connecting" (pulsing orange), false (blinking red: can't connect). */
  online?: boolean | "connecting";
  /** A few words on the wall (what the phone is doing). */
  children?: any;
  /** Fill the parent's height instead of the screen's. */
  fill?: boolean;
  id?: string; className?: string;
}
'''
    d = d.replace("export interface RotaryPhoneProps", types.strip() + "\n\nexport interface RotaryPhoneProps", 1)
    d = d.replace("export declare function RotaryPhone(props: RotaryPhoneProps): React.ReactElement;", "export declare function RotaryPhone(props: RotaryPhoneProps): React.ReactElement;\nexport declare function SoftphoneDesk(props: SoftphoneDeskProps): React.ReactElement;", 1)
    d = d.replace("RotaryPhone: typeof RotaryPhone;", "RotaryPhone: typeof RotaryPhone; SoftphoneDesk: typeof SoftphoneDesk;", 1)
    assert "SoftphoneDesk: typeof SoftphoneDesk" in d
    open(P + "index.d.ts", "w").write(d)
print("desk built", "SoftphoneDesk" in d)
