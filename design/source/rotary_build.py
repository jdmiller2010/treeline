# Puts the current phone drawing (rotary.py) and its line lamp into the bundles.
import json, re, sys
sys.path.insert(0, "/home/claude/treeline/build/phone")
import rotary

B = "/home/claude/treeline/project/components/bundle.js"
K = "/home/claude/treeline/build/treeline_js.txt"
L = "/home/claude/treeline/build/phone/rotary_logic.js"
CSS = "/home/claude/treeline/project/components/bundle.css"
D = "/home/claude/treeline/project/components/index.d.ts"

tmpl = rotary.svg(number="{{NUMBER}}").replace('class="tl-rotary__svg"', 'class="tl-rotary__svg" tabindex="0" role="img" aria-label="Rotary dial. Drag a number round to the finger stop and let go, or press a number key."', 1)

LINE_A = '    function setRinging(on) { root.classList.toggle("is-ringing", !!on); }'
LINE_B = LINE_A + '\n    // The line lamp on the front: lit when the phone is connected and ready; it flashes while it rings.\n    function setLine(on) { root.setAttribute("data-line", on ? "on" : "off"); }'
API_A = 'setRinging: setRinging, isRinging: function () { return root.classList.contains("is-ringing"); },'
API_B = API_A + ' setLine: setLine, isLineOn: function () { return root.getAttribute("data-line") === "on"; },'
for p in (B, K, L):
    s = open(p).read()
    if "function setLine" not in s:
        assert LINE_A in s and API_A in s, p
        s = s.replace(LINE_A, LINE_B, 1).replace(API_A, API_B, 1)
    if p == B:
        s, n = re.subn(r'var ROTARY_SVG = ".*?";\n', lambda m: "var ROTARY_SVG = " + json.dumps(tmpl) + ";\n", s, count=1, flags=re.S)
        assert n == 1
        a = '"data-tl-rotary": "", "data-hook": p.defaul'
        if '"data-line"' not in s:
            i = s.index(a)
            s = s[:i] + '"data-tl-rotary": "", "data-line": p.online === undefined ? undefined : (p.online ? "on" : "off"), "data-hook": p.defaul' + s[i + len(a):]
    open(p, "w").write(s)

c = open(CSS).read()
if "tl-rotary-lamp" not in c:
    a = '@media (prefers-reduced-motion: reduce) { .tl-rotary.is-ringing[data-hook="on"] .tlp-handset { animation: none; } }'
    assert a in c
    c = c.replace(a, a + '''
/* The line lamp: a little jewel light on the front of the phone. Dark until the app says the line is up
   (online prop, api.setLine); then a soft green. While the phone rings it flashes gently. */
.tl-rotary .tlp-lamp { transition: fill .3s ease; }
.tl-rotary[data-line="on"] .tlp-lamp { fill: #7fe08a; filter: drop-shadow(0 0 3px rgba(127, 224, 138, .85)); }
.tl-rotary.is-ringing .tlp-lamp { fill: #7fe08a; animation: tl-rotary-lamp 1.2s ease-in-out infinite; }
@keyframes tl-rotary-lamp { 0%, 100% { fill: #8ef29a; filter: drop-shadow(0 0 4px rgba(142, 242, 154, .95)); } 50% { fill: #3f6b45; filter: none; } }
@media (prefers-reduced-motion: reduce) { .tl-rotary.is-ringing .tlp-lamp { animation: none; } }''', 1)
    open(CSS, "w").write(c)

d = open(D).read()
if "setLine(" not in d:
    d = d.replace("setRinging(on: boolean): void; isRinging(): boolean }", "setRinging(on: boolean): void; isRinging(): boolean; setLine(on: boolean): void; isLineOn(): boolean }")
    d = d.replace("export interface RotaryPhoneProps {", "export interface RotaryPhoneProps {\n  /** The line lamp: true lights it (connected, ready), false leaves it dark. Unset: dark. */\n  online?: boolean;", 1)
    assert "setLine(" in d
    open(D, "w").write(d)
print("rotary built")
