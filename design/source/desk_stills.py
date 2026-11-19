# Flat stills of the room for the design system: the scene, its words and the moss phone in one SVG per layout.
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
DEST = "/home/claude/treeline/project/assets/Illustrations/rotary"
NAMES = {"wide": "softphone-desk.svg", "portrait": "softphone-desk-portrait.svg", "tall": "softphone-desk-phone.svg"}
# 7:30 pm on the clock
ON = {"h2a", "h2b", "h2c", "m1a", "m1b", "m1c", "m1d", "m1g", "m2a", "m2b", "m2c", "m2d", "m2e", "m2f"}

def inner(svg):
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip(), flags=re.S)

phone = open(os.path.join(OUT, "rotary-phone-moss.svg")).read()
pv = re.search(r'viewBox="([^"]+)"', phone).group(1); _, _, vw, vh = map(float, pv.split())
phone_in = re.sub(r'(class="tlp-lamp"[^>]*?)fill="[^"]*"', r'\1fill="#7fd08a"', inner(phone))
for name, fn in NAMES.items():
    L = desk.LAYOUTS[name]; W, H = L["W"], L["H"]
    scene = inner(desk.scene(name))
    words = inner(desk.words(name))
    words = re.sub(r'<polygon class="tl-clk__seg" data-seg="(\w+)"', lambda m: f'<polygon class="tl-clk__seg{" is-on" if m.group(1) in ON else ""}" data-seg="{m.group(1)}"', words)
    words = words.replace('class="tl-clk__seg tl-clk__pm"', 'class="tl-clk__seg tl-clk__pm is-on"')
    p = L["phone"]; ph = p["w"] * vh / vw
    style = "<style>.tl-clk__seg{fill:#2a1613}.tl-clk__seg.is-on{fill:#ff4a32}</style>"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{style}{scene}{words}'
           f'<svg x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{ph:.1f}" viewBox="{pv}">{phone_in}</svg></svg>')
    open(os.path.join(DEST, fn), "w").write(svg)
    print(fn, len(svg))
