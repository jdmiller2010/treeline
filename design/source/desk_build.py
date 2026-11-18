# Puts the SoftphoneDesk scene, logic, component, styles and types into the design system and the kit JS.
import json, re, sys
sys.path.insert(0, "/home/claude/treeline/build/phone")
import desk

P = "/home/claude/treeline/project/components/"
G = desk.GEOM
W, H = G["w"], G["h"]
def pct(v, d): return f"{v / d * 100:.3f}%"

scene = desk.scene()
words = desk.words_template()
logic = open("/home/claude/treeline/build/phone/desk_logic.js").read()

component = r'''
  var DESK_SVG = __SCENE__;
  var DESK_WORDS = __WORDS__;
  function deskEsc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function deskMarkup(prefix, p) {
    var list = p.contacts || [], c = list[0], name = String(p.treehouseName || "Our treehouse").toUpperCase();
    var art = DESK_SVG.replace(/id="tls-/g, 'id="' + prefix + '-').replace(/url\(#tls-/g, "url(#" + prefix + "-");
    var w = DESK_WORDS.replace("{{NAME}}", deskEsc(name)).replace("{{NAMESIZE}}", deskNameSize(name))
      .replace("{{QUIET}}", deskEsc(p.quietTime || "not set"))
      .replace("{{CNAME}}", deskEsc(c ? c.name : "No strings yet")).replace("{{CNUM}}", deskEsc(c ? c.number : "ask a grown-up"))
      .replace("{{CCOUNT}}", list.length > 1 ? "1 of " + list.length : "");
    return art + w;
  }
  function SoftphoneDesk(p) {
    var ref = React.useRef(null), pfx = useId(p.id).replace(/[^a-zA-Z0-9-]/g, "") + "-d";
    var cb = React.useRef(p); cb.current = p;
    var key = JSON.stringify(p.contacts || []);
    React.useEffect(function () {
      var root = ref.current, api = attachDesk(root);
      function card(e) { if (cb.current.onCard) cb.current.onCard(e.detail.contact, e.detail.index); }
      root.addEventListener("tl-desk-card", card);
      if (p.deskRef) p.deskRef.current = api;
      return function () { root.removeEventListener("tl-desk-card", card); };
    }, []);
    React.useEffect(function () { if (ref.current && ref.current.__tlDesk) ref.current.__tlDesk.setContacts(p.contacts || []); }, [key]);
    var markup = React.useMemo(function () { return deskMarkup(pfx, p); }, [pfx, p.treehouseName, p.quietTime, key]);
    var email = p.email || "jdmiller2010@gmail.com";
    return h("div", { ref: ref, className: cx("tl-desk", p.fill && "tl-desk--fill", p.className), "data-tl-desk": "", "data-contacts": key },
      h("div", { className: "tl-desk__stage" },
        h("div", { className: "tl-desk__art", dangerouslySetInnerHTML: { __html: markup } }),
        h("div", { className: "tl-desk__phone" },
          h(RotaryPhone, { id: pfx + "-phone", number: p.number, colorway: p.colorway, offHook: p.offHook, defaultOffHook: p.defaultOffHook,
            onDigit: p.onDigit, onHook: p.onHook, onPulse: p.onPulse, apiRef: p.apiRef, notice: false })),
        p.children ? h("div", { className: "tl-desk__slot" }, p.children) : null,
        h("p", { className: "tl-desk__sr" }, "This phone can’t call 911 or outside numbers. In an emergency, use a grown-up’s phone."),
        h("a", { className: "tl-desk__hot tl-desk__hot--guide", href: p.guideHref || "#guide", onClick: p.onGuide, "aria-label": "The guide book: Rotary Phones the Easy Way" }),
        h("button", { type: "button", className: "tl-desk__hot tl-desk__hot--cardfile tl-desk__cardfile", "aria-label": "Phone book" }),
        h("a", { className: "tl-desk__hot tl-desk__hot--coffee", href: p.coffeeHref || "#support", target: p.coffeeHref ? "_blank" : undefined, rel: p.coffeeHref ? "noopener" : undefined,
          "aria-label": "Gift certificate: buy the person who built Treeline a coffee, on Buy Me a Coffee" }),
        h("a", { className: "tl-desk__hot tl-desk__hot--card", href: "mailto:" + email, "aria-label": "Business card: Treeline, made by Jordan Miller, " + email + ". Copyright 2026 Jordan Miller." }),
        h("a", { className: "tl-desk__hot tl-desk__hot--licenses", href: p.licensesHref || "#licenses", onClick: p.onLicenses, "aria-label": "Owner’s warranty and open-source licenses" })));
  }
'''.replace("__SCENE__", json.dumps(scene)).replace("__WORDS__", json.dumps(words))

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

ph = G["phone"]
hot = "\n".join(f".tl-desk__hot--{k} {{ left: {pct(x, W)}; top: {pct(y, H)}; width: {pct(w, W)}; height: {pct(h, H)}; }}" for k, (x, y, w, h) in G["hotspots"].items())
css = f"""
/* >>> SoftphoneDesk — the tablet softphone screen: the phone on a side table in a 90s room.
   The room is a still picture (1000 × 1300); the phone and the props on it are live. */
.tl-desk {{ container-type: size; position: relative; width: 100%; height: 100dvh; overflow: hidden; display: flex; align-items: flex-end; justify-content: center;
  background:
    linear-gradient(to bottom, transparent 0 86.3%, #efe6d2 86.3% 89.3%, #a77a4c 89.3%, #c99e6e 100%),
    repeating-linear-gradient(90deg, transparent 0 1.06cqh, #dfe6cf 1.06cqh 2.14cqh, transparent 2.14cqh 3.38cqh),
    linear-gradient(to bottom, #ead9b4, #f1e5c8 35%, #e9dbbb 86%); }}
.tl-desk--fill {{ height: 100%; }}
.tl-desk__stage {{ position: relative; flex: none; width: min(100cqw, {W / H * 100:.3f}cqh); aspect-ratio: {W} / {H}; }}
.tl-desk__art, .tl-desk__art > svg {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
.tl-desk__phone {{ position: absolute; left: {pct(ph["x"], W)}; top: {pct(ph["y"], H)}; width: {pct(ph["w"], W)}; }}
.tl-desk__phone .tl-rotary {{ max-width: none; gap: 0; }}
/* The slot: the wall above the phone, between the sticky note and the corkboard. For the app's few words
   (what the phone is doing, the connection light, a lesson or a sleeping card). Keep it short: two lines. */
.tl-desk__slot {{ position: absolute; left: 26%; right: 31.5%; top: 1.6%; display: flex; flex-direction: column; align-items: center; gap: var(--space-2); text-align: center; color: #2a251c; }}
.tl-desk__hot {{ position: absolute; display: block; padding: 0; border: 0; border-radius: 14px; background: none; cursor: pointer; -webkit-tap-highlight-color: transparent; }}
.tl-desk__hot:focus-visible {{ outline: var(--border-focus, 3px) solid var(--focus); outline-offset: 2px; }}
{hot}
.tl-desk__card {{ transform-box: fill-box; transform-origin: 50% 100%; }}
.tl-desk__card.is-flipping {{ animation: tl-desk-flip .3s ease; }}
@keyframes tl-desk-flip {{ 50% {{ opacity: 0; transform: translateY(-10px); }} }}
@media (prefers-reduced-motion: reduce) {{ .tl-desk__card.is-flipping {{ animation: none; }} }}
.tl-desk__sr {{ position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
/* <<< SoftphoneDesk */
"""
c = open(P + "bundle.css").read()
c = re.sub(r"\n/\* >>> SoftphoneDesk.*?/\* <<< SoftphoneDesk \*/\n", "", c, flags=re.S)
open(P + "bundle.css", "w").write(c.rstrip() + "\n" + css)

d = open(P + "index.d.ts").read()
if "SoftphoneDeskProps" not in d:
    types = '''
export interface DeskContact { name: string; number: string; }
export interface SoftphoneDeskApi { next(): void; prev(): void; setContacts(c: DeskContact[]): void; index(): number; }
export interface SoftphoneDeskProps {
  /** The treehouse's own 4 digits, shown in the middle of the dial. */
  number?: string;
  colorway?: "moss" | "ivory" | "berry";
  /** Printed on the label tape on the drawer, in capitals. */
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
  deskRef?: { current: SoftphoneDeskApi | null };
  /** A few words on the wall above the phone (status, connection light). */
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
