# The phone's little light has three line states: on (steady green), connecting (pulsing orange), off (blinking red).
B = "/home/claude/treeline/project/components/bundle.js"
K = "/home/claude/treeline/build/treeline_js.txt"
L = "/home/claude/treeline/build/phone/rotary_logic.js"
DL = "/home/claude/treeline/build/phone/desk_logic.js"
CSS = "/home/claude/treeline/project/components/bundle.css"
D = "/home/claude/treeline/project/components/index.d.ts"
OLD_FN = '    // The line lamp on the front: lit when the phone is connected and ready; it flashes while it rings.\n    function setLine(on) { root.setAttribute("data-line", on ? "on" : "off"); }'
NEW_FN = ('    // The line lamp on the front: steady green when connected, pulsing orange while connecting, blinking red when\n'
          '    // it can\'t connect; it flashes green while it rings. setLine(true | false | "on" | "connecting" | "off").\n'
          '    function setLine(state) { root.setAttribute("data-line", state === "connecting" ? "connecting" : (state === true || state === "on") ? "on" : "off"); }')
OLD_API = 'setLine: setLine, isLineOn: function () { return root.getAttribute("data-line") === "on"; },'
NEW_API = OLD_API + ' lineState: function () { return root.getAttribute("data-line") || "off"; },'
for p in (B, K, L):
    s = open(p).read()
    if NEW_FN not in s:
        assert OLD_FN in s and OLD_API in s, p
        s = s.replace(OLD_FN, NEW_FN, 1).replace(OLD_API, NEW_API, 1)
    if p == B:
        a = '"data-line": p.online === undefined ? undefined : (p.online ? "on" : "off")'
        if a in s: s = s.replace(a, '"data-line": p.online === undefined ? undefined : (p.online === "connecting" ? "connecting" : p.online ? "on" : "off")', 1)
    open(p, "w").write(s)
s = open(DL).read()
a = '    function setOnline(on) { online = !!on; all("[data-tl-rotary]", function (r) { r.setAttribute("data-line", online ? "on" : "off"); }); }'
if a in s:
    s = s.replace(a, '    function setOnline(on) { var v = on === "connecting" ? "connecting" : on ? "on" : "off"; online = v === "on"; all("[data-tl-rotary]", function (r) { r.setAttribute("data-line", v); }); }', 1)
    open(DL, "w").write(s)
c = open(CSS).read()
a = '''/* The line lamp: a little jewel light on the front of the phone. Dark until the app says the line is up
   (online prop, api.setLine); then a soft green. While the phone rings it flashes gently. */
.tl-rotary .tlp-lamp { transition: fill .3s ease; }
.tl-rotary[data-line="on"] .tlp-lamp { fill: #7fe08a; filter: drop-shadow(0 0 3px rgba(127, 224, 138, .85)); }
.tl-rotary.is-ringing .tlp-lamp { fill: #7fe08a; animation: tl-rotary-lamp 1.2s ease-in-out infinite; }
@keyframes tl-rotary-lamp { 0%, 100% { fill: #8ef29a; filter: drop-shadow(0 0 4px rgba(142, 242, 154, .95)); } 50% { fill: #3f6b45; filter: none; } }
@media (prefers-reduced-motion: reduce) { .tl-rotary.is-ringing .tlp-lamp { animation: none; } }'''
b = '''/* The line lamp: a little jewel light on the front of the phone (online prop, api.setLine). Steady green:
   connected, ready to call. Pulsing orange: connecting, wait. Blinking red: it can't connect, something's wrong.
   Flashing green: a call is ringing. With reduced motion the colors stay but nothing pulses or blinks. */
.tl-rotary .tlp-lamp { transition: fill .3s ease; }
.tl-rotary[data-line="on"] .tlp-lamp { fill: #7fe08a; filter: drop-shadow(0 0 3px rgba(127, 224, 138, .85)); }
.tl-rotary[data-line="connecting"] .tlp-lamp { fill: #f2a24a; animation: tl-rotary-lamp-pulse 1.8s ease-in-out infinite; }
.tl-rotary[data-line="off"] .tlp-lamp { fill: #e5534b; animation: tl-rotary-lamp-blink 1s steps(1, end) infinite; }
.tl-rotary.is-ringing .tlp-lamp { fill: #7fe08a; animation: tl-rotary-lamp 1.2s ease-in-out infinite; }
@keyframes tl-rotary-lamp { 0%, 100% { fill: #8ef29a; filter: drop-shadow(0 0 4px rgba(142, 242, 154, .95)); } 50% { fill: #3f6b45; filter: none; } }
@keyframes tl-rotary-lamp-pulse { 0%, 100% { fill: #f6b860; filter: drop-shadow(0 0 4px rgba(246, 184, 96, .9)); } 50% { fill: #9a6a35; filter: none; } }
@keyframes tl-rotary-lamp-blink { 0% { fill: #ef5a50; filter: drop-shadow(0 0 4px rgba(239, 90, 80, .9)); } 50% { fill: #5a2a26; filter: none; } }
@media (prefers-reduced-motion: reduce) { .tl-rotary.is-ringing .tlp-lamp, .tl-rotary[data-line] .tlp-lamp { animation: none; } }'''
if b not in c:
    assert a in c; c = c.replace(a, b, 1); open(CSS, "w").write(c)
d = open(D).read()
d = d.replace("setLine(on: boolean): void; isLineOn(): boolean }", 'setLine(state: boolean | "on" | "connecting" | "off"): void; isLineOn(): boolean; lineState(): "on" | "connecting" | "off" }')
d = d.replace("  /** The line lamp: true lights it (connected, ready), false leaves it dark. Unset: dark. */\n  online?: boolean;",
              '  /** The line lamp: true (steady green, connected), "connecting" (pulsing orange), false (blinking red, can\'t connect). Unset: dark. */\n  online?: boolean | "connecting";')
open(D, "w").write(d)
print("lamp states in")
