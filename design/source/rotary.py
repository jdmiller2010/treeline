# Treeline rotary phone artwork.
# Hand-drawn ink line over watercolor shading, three-dimensional, in three colorways.
# Built as separate layers that share one viewBox, so the dial and the handset can move:
#   tlp-cord      the coiled cord (its path is recomputed when the handset moves)
#   tlp-base      the body, base plate, cradle and shadow
#   tlp-card      the number card under the finger wheel (stays still)
#   tlp-wheel     the clear finger wheel with ten holes (rotates)
#   tlp-glare     the wheel's highlight and the finger stop (stay still)
#   tlp-handset   the handset (lifts and tilts)
# Colors come from CSS variables (--tlp-l/m/d/s), so one drawing serves every colorway.
import math, json

VB = (0, -70, 400, 510)            # extra room on top for the lifted handset
INK = "#2a251c"
COLORWAYS = {                            # light, mid, deep, shadow
    "moss":  ("#b9cdaa", "#7f9e74", "#55704f", "#3a4d36"),
    "ivory": ("#fbf3df", "#e7d8b6", "#c4ad82", "#8d7752"),
    "berry": ("#e9a99c", "#c66d5f", "#97483d", "#6a2f28"),
}
L, M, D, S = "var(--tlp-l)", "var(--tlp-m)", "var(--tlp-d)", "var(--tlp-s)"

# Western Electric 500 seen from the front and a little above: a big dial on the sloped face,
# the classic curved handset across two cradle posts, its caps resting on the shoulders.
CX, CY = 200, 292                        # dial center
LAMP = (300, 362)                        # the line lamp on the body
PLATE_R = 92                             # the printed number ring on the body
R = 73                                   # finger wheel
SQ = 0.93                                # the face's tilt squashes circles a little
STOP = 32                                # finger stop, screen degrees clockwise from 3 o'clock
HOLE_K, HOLE_R = 0.79, 11.5
GAP = 30
DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
HOLE_ANGLE = {d: STOP - 60 - i * GAP for i, d in enumerate(DIGITS)}   # 1 sits 60 degrees before the stop
TRAVEL = {d: 60 + i * GAP for i, d in enumerate(DIGITS)}              # 1 turns 60 degrees, 0 turns 330

def P(a, k=1.0, rad=None):
    t = math.radians(a); rr = (rad or R) * k
    return CX + rr * math.cos(t), CY + rr * SQ * math.sin(t)

LN  = f'fill="none" stroke="{INK}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
LNS = f'fill="none" stroke="{INK}" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round" opacity=".65"'
WOB = 'filter="url(#tlp-wobble)"'
WASH = 'filter="url(#tlp-wash)" transform="translate(1.5 1.5)"'
SQUASH = f'transform="translate({CX} {CY}) scale(1 {SQ:.4f}) translate({-CX} {-CY})"'
def sf(c): return f'style="fill:{c}"'
def ss(c): return f'style="stroke:{c}"'

def defs():
    return f"""<defs>
<filter id="tlp-wobble" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="1.6"/></filter>
<filter id="tlp-wash" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="3" seed="9" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="5"/><feGaussianBlur stdDeviation="0.5"/></filter>
<filter id="tlp-grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 0.16  0 0 0 0 0.13  0 0 0 0 0.08  0 0 0 -1.6 1.05"/><feComposite in2="SourceGraphic" operator="in"/></filter>
<filter id="tlp-edge" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2.2"/></filter>
<filter id="tlp-soft" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="8"/></filter>
<linearGradient id="tlp-body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:{L}"/><stop offset=".5" style="stop-color:{M}"/><stop offset="1" style="stop-color:{D}"/></linearGradient>
<linearGradient id="tlp-side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:{S}" stop-opacity=".6"/><stop offset=".14" style="stop-color:{S}" stop-opacity="0"/><stop offset=".86" style="stop-color:{S}" stop-opacity="0"/><stop offset="1" style="stop-color:{S}" stop-opacity=".65"/></linearGradient>
<linearGradient id="tlp-deck" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:{L}"/><stop offset="1" style="stop-color:{M}"/></linearGradient>
<linearGradient id="tlp-post" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:{L}"/><stop offset=".55" style="stop-color:{M}"/><stop offset="1" style="stop-color:{D}"/></linearGradient>
<linearGradient id="tlp-hand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:{L}"/><stop offset=".5" style="stop-color:{M}"/><stop offset="1" style="stop-color:{D}"/></linearGradient>
<linearGradient id="tlp-cup" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:{L}"/><stop offset=".35" style="stop-color:{M}"/><stop offset="1" style="stop-color:{D}"/></linearGradient>
<radialGradient id="tlp-plate" cx=".45" cy=".35" r=".8"><stop offset="0" stop-color="#fffaf0"/><stop offset="1" stop-color="#eadfc6"/></radialGradient>
<radialGradient id="tlp-card" cx=".45" cy=".35" r=".75"><stop offset="0" stop-color="#fffdf6"/><stop offset="1" stop-color="#f1e7d2"/></radialGradient>
<radialGradient id="tlp-wheelfill" cx=".4" cy=".3" r=".9"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset=".7" stop-color="#ffffff" stop-opacity=".14"/><stop offset="1" style="stop-color:{S}" stop-opacity=".3"/></radialGradient>
<linearGradient id="tlp-metal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6f3ec"/><stop offset=".5" stop-color="#bdb6a8"/><stop offset="1" stop-color="#7d766a"/></linearGradient>
<clipPath id="tlp-faceclip"><path d="{FACE}"/></clipPath>
<clipPath id="tlp-handclip"><path d="{HANDSET}"/></clipPath>
</defs>"""

# ---- body (front layer) and deck (back layer)
FACE  = "M84 214 C86 184 108 168 140 166 L260 166 C292 168 314 184 316 214 C322 262 336 318 338 356 C339 378 326 390 304 390 L96 390 C74 390 61 378 62 356 C64 318 78 262 84 214 Z"
LIP   = "M62 386 C62 380 68 378 76 378 L324 378 C332 378 338 380 338 386 L338 396 C338 402 332 406 324 406 L76 406 C68 406 62 402 62 396 Z"
DECK  = "M122 180 C122 162 130 152 144 150 L256 150 C270 152 278 162 278 180 Z"
SHOULDER_L = "M60 196 C58 178 70 160 96 158 L118 160 L112 176 C100 176 92 184 90 196 Z"
SHOULDER_R = "M340 196 C342 178 330 160 304 158 L282 160 L288 176 C300 176 308 184 310 196 Z"
def post(x):
    return f"M{x-18} 176 L{x-13} 142 C{x-13} 135 {x-8} 131 {x-3} 131 L{x+3} 131 C{x+8} 131 {x+13} 135 {x+13} 142 L{x+18} 176 Z"
POSTS = (152, 248)

def deck():
    g = [f'<ellipse cx="200" cy="410" rx="178" ry="17" {sf(S)} opacity=".3" filter="url(#tlp-soft)"/>',
         f'<g {WASH}><path d="{DECK}" {sf(D)}/><path d="M126 182 C126 168 132 158 144 156 L256 156 C268 158 274 168 274 182 Z" {sf(S)} opacity=".45"/>',
         '</g>',
         f'<g {WOB}><path d="{DECK}" {LN}/></g>']
    return "".join(g)

def body():
    g = [f'<g {WASH}><path d="{LIP}" {sf(D)}/></g>', f'<g {WOB}><path d="{LIP}" {LN}/></g>',
         f'<path d="M70 383 L330 383" stroke="#ffffff" stroke-opacity="0.17" stroke-width="2" fill="none"/>',
         f'<g {WASH}><path d="{FACE}" fill="url(#tlp-body)"/><path d="{FACE}" fill="url(#tlp-side)"/>',
         f'<g clip-path="url(#tlp-faceclip)"><path d="{FACE}" fill="none" {ss(S)} stroke-opacity=".55" stroke-width="12" filter="url(#tlp-edge)"/></g>',
         f'<path d="M100 206 C96 250 86 306 80 356" fill="none" stroke="#ffffff" stroke-opacity="0.19" stroke-width="6" stroke-linecap="round"/>',
         f'<path d="M120 180 C150 174 250 174 280 180" fill="none" stroke="#ffffff" stroke-opacity="0.25" stroke-width="3" stroke-linecap="round"/>',
         f'<ellipse cx="{CX}" cy="{CY+5}" rx="{PLATE_R+10}" ry="{(PLATE_R+10)*SQ:.1f}" {sf(S)} opacity=".35" filter="url(#tlp-edge)"/>']
    for x in POSTS:
        g.append(f'<path d="{post(x)}" fill="url(#tlp-post)"/>')
        g.append(f'<path d="M{x-7} 140 L{x-10} 172" stroke="#ffffff" stroke-opacity="0.23" stroke-width="3" stroke-linecap="round" fill="none"/>')
    g += ['</g>', 
          f'<g {WOB}><path d="{FACE}" {LN}/>'] + [f'<path d="{post(x)}" {LN}/>' for x in POSTS] + ['</g>']
    # The line lamp: a little jewel light on the front, lower right. Dark glass until the app lights it
    # (data-line="on": ready, a soft green); it flashes gently while the phone rings. See bundle.css.
    lx, ly = LAMP
    g += [f'<circle cx="{lx}" cy="{ly}" r="7.5" fill="#5b5248"/><circle cx="{lx}" cy="{ly}" r="7.5" fill="none" stroke="#2a251c" stroke-width="1.2"/>',
          f'<circle class="tlp-lamp" cx="{lx}" cy="{ly}" r="5" fill="#3a3530"/>',
          f'<circle cx="{lx-1.8}" cy="{ly-1.8}" r="1.5" fill="#ffffff" opacity=".55"/>']
    # the number ring printed on the body, outside the finger wheel
    g.append(f'<ellipse cx="{CX}" cy="{CY}" rx="{PLATE_R}" ry="{PLATE_R*SQ:.2f}" fill="url(#tlp-plate)"/>')
    g.append(f'<g {WOB}><ellipse cx="{CX}" cy="{CY}" rx="{PLATE_R}" ry="{PLATE_R*SQ:.2f}" {LN}/></g>')
    for d in DIGITS:
        x, y = P(HOLE_ANGLE[d], 1.0, (R + PLATE_R) / 2 + 1)
        g.append(f'<text x="{x:.1f}" y="{y+5:.1f}" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-size="14" font-weight="500" fill="{INK}">{d}</text>')
    return "".join(g)

def card(number=""):
    """The card in the middle and the paper behind the holes; stays still while the wheel turns."""
    g = [f'<ellipse cx="{CX}" cy="{CY}" rx="{R}" ry="{R*SQ:.2f}" {sf(S)} opacity=".25"/>',
         f'<ellipse cx="{CX}" cy="{CY}" rx="{R-2}" ry="{(R-2)*SQ:.2f}" fill="url(#tlp-plate)"/>']
    for d in DIGITS:   # a small dot at the back of each hole, as on the real dial
        x, y = P(HOLE_ANGLE[d], HOLE_K)
        g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{INK}" opacity=".55"/>')
    g += [f'<ellipse cx="{CX}" cy="{CY}" rx="33" ry="{33*SQ:.2f}" fill="url(#tlp-card)"/>',
          f'<g {WOB}><ellipse cx="{CX}" cy="{CY}" rx="33" ry="{33*SQ:.2f}" {LNS}/></g>',
          f'<path d="M{CX-26} {CY-11} C{CX-12} {CY-16} {CX+12} {CY-16} {CX+26} {CY-11}" {LNS}/>',
          f'<path d="M{CX-26} {CY+13} C{CX-12} {CY+18} {CX+12} {CY+18} {CX+26} {CY+13}" {LNS}/>',
          f'<text class="tl-rotary__number" x="{CX}" y="{CY+5.5}" text-anchor="middle" font-family="Figtree, Helvetica, sans-serif" font-size="15" font-weight="600" letter-spacing="1.5" fill="{INK}">{number}</text>']
    return "".join(g)

def wheel():
    ring = f"M{CX+R} {CY} A{R} {R} 0 1 1 {CX-R} {CY} A{R} {R} 0 1 1 {CX+R} {CY} Z"
    hub = f"M{CX+36} {CY} A36 36 0 1 0 {CX-36} {CY} A36 36 0 1 0 {CX+36} {CY} Z"
    def hole(d):
        t = math.radians(HOLE_ANGLE[d]); return CX + HOLE_K*R*math.cos(t), CY + HOLE_K*R*math.sin(t)
    holes = "".join(f"M{hole(d)[0]+HOLE_R:.1f} {hole(d)[1]:.1f} a{HOLE_R} {HOLE_R} 0 1 0 {-2*HOLE_R} 0 a{HOLE_R} {HOLE_R} 0 1 0 {2*HOLE_R} 0 Z" for d in DIGITS)
    g = [f'<path d="{ring} {hub} {holes}" fill-rule="evenodd" fill="url(#tlp-wheelfill)"/>',
         f'<path d="{ring} {hub} {holes}" fill-rule="evenodd" {sf(L)} opacity=".14"/>',
         f'<g {WOB}><circle cx="{CX}" cy="{CY}" r="{R}" {LN}/><circle cx="{CX}" cy="{CY}" r="36" {LNS}/>']
    for d in DIGITS:
        x, y = hole(d)
        g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{HOLE_R}" {LN}/>')
        g.append(f'<path d="M{x-HOLE_R*.75:.1f} {y+HOLE_R*.2:.1f} A{HOLE_R} {HOLE_R} 0 0 1 {x+HOLE_R*.2:.1f} {y-HOLE_R*.75:.1f}" fill="none" stroke="#ffffff" stroke-opacity=".8" stroke-width="1.5" stroke-linecap="round"/>')
    g.append('</g>')
    return "".join(g)

def glare_and_stop():
    x, y = P(STOP, 1.03); x2, y2 = P(STOP, .66)
    q = f"M{x+5:.1f} {y:.1f} Q{(x+x2)/2+10:.1f} {(y+y2)/2-2:.1f} {x2:.1f} {y2+1:.1f}"
    return (f'<path d="M{CX-58} {CY-38} C{CX-40} {CY-60} {CX} {CY-70} {CX+30} {CY-62}" fill="none" stroke="#ffffff" stroke-opacity=".6" stroke-width="3.5" stroke-linecap="round"/>'
            f'<path d="{q}" fill="none" stroke="url(#tlp-metal)" stroke-width="7" stroke-linecap="round"/>'
            f'<g {WOB}><path d="{q}" fill="none" stroke="{INK}" stroke-width="1.3" stroke-linecap="round" opacity=".8"/></g>')

# ---- handset: the classic one-piece shape, a handle arching between two bell-shaped caps
HANDSET = ("M56 200 C48 172 50 134 66 116 C80 100 102 96 126 96 C162 86 238 86 274 96 "
           "C298 96 320 100 334 116 C350 134 352 172 344 200 C338 216 294 218 284 202 "
           "C280 180 274 158 258 146 C228 132 172 132 142 146 C126 158 120 180 116 202 C106 218 62 216 56 200 Z")
HANDSET_TOP = "M78 112 C92 102 110 100 128 101 C164 92 236 92 272 101 C290 100 308 102 322 112 C300 106 284 106 272 108 C236 100 164 100 128 108 C116 106 100 106 78 112 Z"
RIM_L, RIM_R = (86, 204, 31, 8), (314, 204, 31, 8)
CORD_END = (70, 206)                     # under the earpiece
CORD_START = (68, 350)                   # the base's left side
LIFT = {"tx": -4, "ty": -50, "rot": 24, "ox": 318, "oy": 200}

def handset():
    rims = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" {sf(S)} opacity=".55"/>' for x, y, rx, ry in (RIM_L, RIM_R))
    rimlines = "".join(f'<path d="M{x-rx+3} {y-1} C{x-rx/2:.0f} {y+ry} {x+rx/2:.0f} {y+ry} {x+rx-3} {y-1}" {LNS}/>' for x, y, rx, ry in (RIM_L, RIM_R))
    return "".join([
        f'<g {WASH}><path d="{HANDSET}" fill="url(#tlp-hand)"/><path d="{HANDSET_TOP}" {sf(L)} opacity=".7"/>',
        f'<g clip-path="url(#tlp-handclip)"><path d="{HANDSET}" fill="none" {ss(S)} stroke-opacity=".5" stroke-width="10" filter="url(#tlp-edge)"/></g>',
        '<path d="M64 136 C60 158 62 178 68 194" fill="none" stroke="#ffffff" stroke-opacity="0.17" stroke-width="5" stroke-linecap="round"/>',
        '<path d="M300 112 C318 116 330 126 336 140" fill="none" stroke="#ffffff" stroke-opacity="0.20" stroke-width="3" stroke-linecap="round"/>',
        '<path d="M130 100 C168 92 232 92 270 100" fill="none" stroke="#ffffff" stroke-opacity="0.30" stroke-width="3" stroke-linecap="round"/>',
        rims, '</g>',
        f'<g {WOB}><path d="{HANDSET}" {LN}/>{rimlines}',
        '<path d="M60 150 C80 140 112 140 128 150" ' + LNS + '/><path d="M272 150 C288 140 320 140 340 150" ' + LNS + '/></g>'])

def cord_path(x1, y1, x2, y2, loops=15, r=6.5, bow=-34):
    """A coiled cord from (x1,y1) to (x2,y2), bowing sideways by `bow` (negative: to the left of the line from start to end)."""
    n = loops * 12; dx, dy = x2 - x1, y2 - y1; Ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / Ln, dx / Ln; pts = []
    for i in range(n + 1):
        t = i / n; b = math.sin(math.pi * t) * bow * min(1.0, Ln / 160); a = 2 * math.pi * loops * t
        bx, by = x1 + dx * t + nx * b, y1 + dy * t + ny * b
        pts.append((bx + nx * r * math.cos(a) + dx / Ln * r * .55 * math.sin(a), by + ny * r * math.cos(a) + dy / Ln * r * .55 * math.sin(a)))
    return "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)

def lifted_point(px, py):
    a = math.radians(LIFT["rot"]); ox, oy = LIFT["ox"], LIFT["oy"]
    rx = ox + (px - ox) * math.cos(a) - (py - oy) * math.sin(a)
    ry = oy + (px - ox) * math.sin(a) + (py - oy) * math.cos(a)
    return rx + LIFT["tx"], ry + LIFT["ty"]

def svg(number="4821", lifted=False, colors=None, wheel_turn=0, cls="tl-rotary__svg"):
    end = lifted_point(*CORD_END) if lifted else CORD_END
    cordd = cord_path(*CORD_START, *end)
    hs = f'transform="translate({LIFT["tx"]} {LIFT["ty"]}) rotate({LIFT["rot"]} {LIFT["ox"]} {LIFT["oy"]})"' if lifted else ''
    body_ = (f'<g class="tlp-deck">{deck()}</g>'
             f'<g class="tlp-cord"><path class="tlp-cord-color" d="{cordd}" fill="none" {ss(D)} stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>'
             f'<path class="tlp-cord-ink" d="{cordd}" fill="none" stroke="{INK}" stroke-width=".9" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/></g>'
             f'<g class="tlp-handset" {hs}>{handset()}</g>'
             f'<g class="tlp-base">{body()}</g>'
             f'<g class="tlp-card">{card(number)}</g>'
             f'<g {SQUASH}><g class="tlp-wheel" transform="rotate({wheel_turn} {CX} {CY})">{wheel()}</g></g>'
             f'<g class="tlp-glare">{glare_and_stop()}</g>')
    out = f'<svg xmlns="http://www.w3.org/2000/svg" class="{cls}" viewBox="{VB[0]} {VB[1]} {VB[2]} {VB[3]}" width="{VB[2]}" height="{VB[3]}">{defs()}{body_}</svg>'
    if colors:
        l, m, d, s_ = COLORWAYS[colors]
        out = out.replace("var(--tlp-l)", l).replace("var(--tlp-m)", m).replace("var(--tlp-d)", d).replace("var(--tlp-s)", s_)
    return out

GEOMETRY = {"cx": CX, "cy": CY, "r": R, "sq": SQ, "stop": STOP, "holeK": HOLE_K, "holeR": HOLE_R, "gap": GAP,
            "holeAngle": HOLE_ANGLE, "travel": TRAVEL, "cordStart": CORD_START, "cordEnd": CORD_END, "lift": LIFT}

if __name__ == "__main__":
    import os
    out = "/home/claude/treeline/build/phone/out"; os.makedirs(out, exist_ok=True)
    for c in COLORWAYS:
        open(f"{out}/rotary-phone-{c}.svg", "w").write(svg(colors=c))
        open(f"{out}/rotary-phone-{c}-lifted.svg", "w").write(svg(colors=c, lifted=True))
    open(f"{out}/rotary-template.svg", "w").write(svg(number=""))
    json.dump(GEOMETRY, open(f"{out}/geometry.json", "w"))
    print("written")
