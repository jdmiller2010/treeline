# Treeline softphone desk scene: the rotary phone on a little side table against a striped wall,
# drawn in the same ink line over watercolor as the phone. 1000 x 1300, portrait.
#   wall: quiet-time sticky note, a framed treehouse sketch, a corkboard with the gift certificate
#         (Buy Me a Coffee) and the business card (credit, email, copyright)
#   table: the "No 911" sticker, the rotary card file (the treehouse's phone book), label tape
#          with the treehouse's name on the drawer
#   shelf: the guide book, spines, the warranty card (open-source licenses), a little potted tree
# The phone itself is the RotaryPhone component, laid over the table. Text that changes
# (contacts, quiet time, name) lives in a separate overlay; this file is the still picture.
import math, json

W, H = 1000, 1300
INK = "#2a251c"
LN  = f'fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
LNS = f'fill="none" stroke="{INK}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round" opacity=".6"'
WOB = 'filter="url(#tls-wobble)"'
WASH = 'filter="url(#tls-wash)"'
SERIF = 'font-family="Fraunces, Georgia, serif"'
SANS = 'font-family="Figtree, Helvetica, Arial, sans-serif"'
HAND = 'font-family="Caveat, \'Comic Sans MS\', cursive"'
MONO = 'font-family="\'Courier New\', Courier, monospace"'

WALL, WALL_D, STRIPE = "#f1e5c8", "#e4d4ae", "#dfe6cf"
WOOD_L, WOOD_M, WOOD_D, WOOD_S = "#dcb48a", "#bf8f5e", "#8f5f33", "#5f3d1f"
FLOOR_L, FLOOR_D = "#c99e6e", "#a77a4c"
CORK, CORK_D = "#d6ae7c", "#b88c58"
BERRY, SKY, CANOPY, SUN = "#b0372f", "#2a6488", "#2e7051", "#f2c14e"
PAPER = "#fffaf0"

def defs():
    return f"""<defs>
<filter id="tls-wobble" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="1.8"/></filter>
<filter id="tls-wash" x="-8%" y="-8%" width="116%" height="116%"><feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3" seed="11" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="5"/><feGaussianBlur stdDeviation="0.6"/></filter>
<filter id="tls-grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="5"/><feColorMatrix values="0 0 0 0 0.16  0 0 0 0 0.12  0 0 0 0 0.07  0 0 0 -1.5 1.0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
<filter id="tls-edge" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2.4"/></filter>
<filter id="tls-soft" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="10"/></filter>
<linearGradient id="tls-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ead9b4"/><stop offset=".35" stop-color="{WALL}"/><stop offset="1" stop-color="#e9dbbb"/></linearGradient>
<linearGradient id="tls-top" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WOOD_M}"/><stop offset="1" stop-color="{WOOD_L}"/></linearGradient>
<linearGradient id="tls-front" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WOOD_M}"/><stop offset="1" stop-color="{WOOD_D}"/></linearGradient>
<linearGradient id="tls-leg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{WOOD_L}"/><stop offset=".5" stop-color="{WOOD_M}"/><stop offset="1" stop-color="{WOOD_D}"/></linearGradient>
<linearGradient id="tls-floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FLOOR_D}"/><stop offset="1" stop-color="{FLOOR_L}"/></linearGradient>
<linearGradient id="tls-paper" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffdf7"/><stop offset="1" stop-color="#f1e6cf"/></linearGradient>
<linearGradient id="tls-metal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6f3ec"/><stop offset=".5" stop-color="#bdb6a8"/><stop offset="1" stop-color="#7d766a"/></linearGradient>
<radialGradient id="tls-knob" cx=".38" cy=".34" r=".75"><stop offset="0" stop-color="#5a5248"/><stop offset="1" stop-color="#211c16"/></radialGradient>
<pattern id="tls-cork" width="14" height="14" patternUnits="userSpaceOnUse"><rect width="14" height="14" fill="{CORK}"/><circle cx="3" cy="4" r="1.1" fill="{CORK_D}"/><circle cx="10" cy="9" r=".9" fill="{CORK_D}"/><circle cx="7" cy="12" r=".7" fill="#e6c79c"/></pattern>
</defs>"""

def shape(d, fill, edge=None, extra=""):
    """A watercolor-filled shape with its ink line."""
    e = f'<path d="{d}" fill="none" stroke="{edge}" stroke-opacity=".45" stroke-width="8" filter="url(#tls-edge)"/>' if edge else ""
    return f'<g {WASH}><path d="{d}" fill="{fill}"/>{e}{extra}</g><g {WOB}><path d="{d}" {LN}/></g>'

def rrect(x, y, w, h, r):
    return f"M{x+r} {y} L{x+w-r} {y} Q{x+w} {y} {x+w} {y+r} L{x+w} {y+h-r} Q{x+w} {y+h} {x+w-r} {y+h} L{x+r} {y+h} Q{x} {y+h} {x} {y+h-r} L{x} {y+r} Q{x} {y} {x+r} {y} Z"

def pin(x, y, color=BERRY):
    return (f'<ellipse cx="{x+2}" cy="{y+5}" rx="8" ry="4" fill="{INK}" opacity=".18" filter="url(#tls-edge)"/>'
            f'<circle cx="{x}" cy="{y}" r="8" fill="{color}"/><circle cx="{x-2.5}" cy="{y-2.5}" r="2.6" fill="#fff" opacity=".55"/>'
            f'<g {WOB}><circle cx="{x}" cy="{y}" r="8" {LN}/></g>')

# ---------------------------------------------------------------- wall and floor
def wall(w, h):
    """No wallpaper: the room sits on the page's own background (canvas), so it works in light and dark."""
    return ""

# ---------------------------------------------------------------- wall things
def sticky_note():
    x, y = 80, 168
    d = f"M{x} {y} L{x+158} {y+4} L{x+156} {y+150} C{x+120} {y+156} {x+40} {y+152} {x+2} {y+146} Z"
    tape = f"M{x+50} {y-12} L{x+112} {y-9} L{x+110} {y+14} L{x+48} {y+11} Z"
    return (f'<g transform="rotate(-4 {x+80} {y+75})">'
            f'<path d="{d}" fill="{INK}" opacity=".14" transform="translate(4 6)" filter="url(#tls-edge)"/>'
            + shape(d, "#f8e49a", edge="#d9b24a")
            + f'<path d="M{x+4} {y+128} C{x+50} {y+136} {x+110} {y+136} {x+154} {y+130} L{x+156} {y+150} C{x+120} {y+156} {x+40} {y+152} {x+2} {y+146} Z" fill="#e9c860" opacity=".45"/>'
            f'<path d="{tape}" fill="#fff" opacity=".55"/><g {WOB}><path d="{tape}" {LNS}/></g>'
            '</g>')

DRAW = (92, 360, 200, 160)          # the kid's drawing on the wall: x, y, w, h
def crayon(d, color, w=3.2, o=.92):
    """A crayon stroke: a waxy line with a second, thinner pass for texture."""
    return (f'<g {WOB}><path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity="{o}"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w*.45:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity=".55" transform="translate(1.2 -.8)"/></g>')
def kid_drawing():
    """A kid's crayon drawing of one treehouse, taped to the wall. The treehouse's name is written across
    the top, in the words layer."""
    x, y, w, h = DRAW
    paper = f"M{x} {y+3} L{x+w} {y} L{x+w-2} {y+h} L{x+3} {y+h-2} Z"
    g = [f'<g transform="rotate(-2 {x+w/2} {y+h/2})">',
         f'<path d="{paper}" fill="{INK}" opacity=".13" transform="translate(4 6)" filter="url(#tls-edge)"/>',
         shape(paper, "#fffdf7")]
    gx, gy = x + 100, y + 140                                     # foot of the tree
    g.append(crayon(f"M{x+14} {gy+2} C{x+50} {gy-4} {x+150} {gy+4} {x+w-14} {gy-1} M{x+20} {gy+8} C{x+70} {gy+3} {x+130} {gy+9} {x+w-24} {gy+5}", "#5f9a55", 2.6))
    g.append(crayon(f"M{gx-6} {gy} L{gx-5} {y+104} M{gx+8} {gy} L{gx+7} {y+104} M{gx-4} {gy-12} L{gx+6} {gy-18} M{gx-4} {gy-24} L{gx+6} {gy-28}", "#8a5a2e", 3))
    # the leafy top, scribbled round and round
    cx_, cy_ = x + 102, y + 76
    loop = " ".join(f"{'M' if i == 0 else 'L'}{cx_ + (42 + 5 * math.sin(i * 1.7)) * math.cos(i * .42):.1f} {cy_ + (28 + 4 * math.cos(i * 1.3)) * math.sin(i * .42):.1f}" for i in range(0, 34))
    g.append(f'<g {WOB}><ellipse cx="{cx_}" cy="{cy_}" rx="40" ry="26" fill="#9fca8a" opacity=".55"/></g>')
    g.append(crayon(loop, "#3f8a4a", 2.4))
    # the house, the roof and a door
    hx, hy = x + 80, y + 84
    g.append(f'<g {WOB}><path d="M{hx} {hy} L{hx+44} {hy} L{hx+44} {hy+22} L{hx} {hy+22} Z" fill="#e7b57a" opacity=".85"/></g>')
    g.append(crayon(f"M{hx} {hy} L{hx+44} {hy-1} L{hx+45} {hy+22} L{hx+1} {hy+23} Z", "#8a5a2e", 2.6))
    g.append(f'<g {WOB}><path d="M{hx-6} {hy} L{hx+22} {hy-18} L{hx+50} {hy} Z" fill="#d9534a" opacity=".85"/></g>')
    g.append(crayon(f"M{hx-6} {hy+1} L{hx+22} {hy-18} L{hx+50} {hy}", "#b0372f", 2.8))
    g.append(crayon(f"M{hx+17} {hy+23} L{hx+17} {hy+10} L{hx+27} {hy+10} L{hx+27} {hy+23}", "#2a251c", 1.8))
    g.append(crayon(f"M{hx-10} {hy+23} L{hx+56} {hy+23}", "#8a5a2e", 3.2))            # the platform
    g.append(crayon(f"M{hx-2} {hy+25} L{hx-10} {gy} M{hx+6} {hy+25} L{hx-1} {gy} M{hx-5} {hy+38} L{hx+3} {hy+38} M{hx-7} {hy+50} L{hx+1} {hy+50}", "#8a5a2e", 1.8))   # ladder
    # a sun in the corner
    sx, sy = x + w - 22, y + 24
    g.append(f'<circle cx="{sx}" cy="{sy}" r="8" fill="{SUN}" opacity=".85"/>')
    g.append(crayon(" ".join(f"M{sx + 12 * math.cos(a):.1f} {sy + 12 * math.sin(a):.1f} L{sx + 17 * math.cos(a):.1f} {sy + 17 * math.sin(a):.1f}" for a in [i * math.pi / 4 for i in range(8)]), "#e0a52c", 1.8))
    for tx_, rot in ((x + 6, -35), (x + w - 8, 35)):          # tape on the top corners
        t = rrect(-16, -7, 32, 14, 1)
        g.append(f'<g transform="translate({tx_} {y + 2}) rotate({rot})"><path d="{t}" fill="#fff" opacity=".6"/><g {WOB}><path d="{t}" {LNS}/></g></g>')
    g.append('</g>')
    return "".join(g)

def corkboard():
    x, y, w, h = 676, 64, 290, 340
    outer, inner = rrect(x, y, w, h, 6), rrect(x+14, y+14, w-28, h-28, 3)
    g = [f'<path d="{outer}" fill="{INK}" opacity=".16" transform="translate(6 9)" filter="url(#tls-edge)"/>',
         shape(outer, WOOD_M, edge=WOOD_S), f'<g {WASH}><path d="{inner}" fill="url(#tls-cork)"/></g>',
         f'<path d="{inner}" fill="none" stroke="{WOOD_S}" stroke-opacity=".35" stroke-width="10" filter="url(#tls-edge)"/>',
         f'<g {WOB}><path d="{inner}" {LN}/></g>']
    g.append(certificate())
    g.append(business_card())
    return "".join(g)

def certificate(turn=3):
    x, y, w, h = 694, 92, 254, 140
    d = rrect(x, y, w, h, 3)
    g = [f'<g transform="rotate({turn} {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, "#fbf4e2"),
         f'<path d="{rrect(x+8, y+8, w-16, h-16, 2)}" fill="none" stroke="{CANOPY}" stroke-width="2.2"/>',
         f'<path d="{rrect(x+13, y+13, w-26, h-26, 2)}" fill="none" stroke="{CANOPY}" stroke-width=".9" stroke-dasharray="1 3"/>']
    for cx_, cy_, rot in ((x+20, y+20, 45), (x+w-20, y+20, 135), (x+w-20, y+h-20, 225), (x+20, y+h-20, 315)):   # leaf corners
        g.append(f'<path transform="translate({cx_} {cy_}) rotate({rot})" d="M0 -7 C5 -3 5 3 0 7 C-5 3 -5 -3 0 -7Z" fill="{CANOPY}" opacity=".8"/>')
    g += [f'<text x="{x+w/2}" y="{y+40}" text-anchor="middle" {SERIF} font-size="19" font-weight="600" letter-spacing="2.5" fill="{INK}">BUY ME A COFFEE</text>',
          f'<path d="M{x+56} {y+50} L{x+w-56} {y+50}" stroke="{CANOPY}" stroke-width="1"/>',
          f'<text x="{x+w/2}" y="{y+74}" text-anchor="middle" {SERIF} font-size="17" font-style="italic" fill="{INK}">Say thanks to the</text>',
          f'<text x="{x+w/2}" y="{y+95}" text-anchor="middle" {SERIF} font-size="17" font-style="italic" fill="{INK}">creator of Treeline</text>',
          f'<text x="{x+w/2}" y="{y+120}" text-anchor="middle" {SANS} font-size="11.5" font-weight="700" letter-spacing="2" fill="{CANOPY}">SUPPORT THE PROJECT</text>',
                    pin(x+w/2, y+10), '</g>']
    return "".join(g)

LOGO_INNER = None
CARD_BOX = (690, 250, 234, 132)     # the business card on the corkboard: x, y, w, h
TAGLINE = "A safe phone line for neighborhood kids"
def business_card(turn=-3):
    """Treeline's business card: logo, name and tagline, then Jordan's name, email and the copyright,
    with a generous white border all round."""
    x, y, w, h = CARD_BOX
    m = 20                                         # the white border
    d = rrect(x, y, w, h, 3)
    logo = open("/home/claude/treeline/project/assets/Logos/treeline-logo.svg").read()
    logo = logo.replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 14 222 146" width="444" height="292">', f'<svg x="{x+m}" y="{y+m}" width="50" height="33" viewBox="10 14 222 146">')
    g = [f'<g transform="rotate({turn} {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, PAPER), logo,
         f'<text x="{x+m+60}" y="{y+m+17}" {SERIF} font-size="21" font-weight="600" fill="{INK}">Treeline</text>',
         f'<text x="{x+m+60}" y="{y+m+30}" {SERIF} font-size="8.6" font-style="italic" fill="#5e5546">A safe phone line</text>',
         f'<text x="{x+m+60}" y="{y+m+40}" {SERIF} font-size="8.6" font-style="italic" fill="#5e5546">for neighborhood kids</text>',
         f'<path d="M{x+m} {y+m+54} L{x+w-m} {y+m+54}" stroke="{INK}" stroke-width=".8" opacity=".3"/>',
         f'<text x="{x+m}" y="{y+m+73}" {SANS} font-size="12.5" font-weight="600" fill="{INK}">Jordan Miller</text>',
         f'<text x="{x+m}" y="{y+m+87}" {SANS} font-size="11" fill="#5e5546">jdmiller2010@gmail.com</text>',
         f'<text x="{x+m}" y="{y+m+99}" {SANS} font-size="8.5" fill="#857b6b">© 2026 Jordan Miller · noncommercial use</text>',
         pin(x+w-22, y+12, SKY), '</g>']
    return "".join(g)


def sticker(cx, cy, sx=.9, sy=.72, rot=-5):
    """The no-911 sticker. On a table top it's squashed for perspective; on a drawer front it isn't."""
    w, h = 196, 118
    d = rrect(-w/2, -h/2, w, h, 16)
    curl = f"M{w/2-30} {h/2} Q{w/2-6} {h/2-6} {w/2} {h/2-30} L{w/2} {h/2-16} Q{w/2} {h/2} {w/2-16} {h/2} Z"
    return (f'<g transform="translate({cx} {cy}) rotate({rot}) scale({sx} {sy})">'
            f'<path d="{d}" fill="{INK}" opacity=".12" transform="translate(2 4)" filter="url(#tls-edge)"/>'
            + shape(d, "#fffdf6")
            + f'<path d="{rrect(-w/2+7, -h/2+7, w-14, h-14, 11)}" fill="none" stroke="{BERRY}" stroke-width="5"/>'
            f'<text x="0" y="-16" text-anchor="middle" {SANS} font-size="33" font-weight="800" letter-spacing="1" fill="{BERRY}">NO 911</text>'
            f'<text x="0" y="6" text-anchor="middle" {SANS} font-size="14" font-weight="700" fill="{INK}">No outside calls.</text>'
            f'<text x="0" y="25" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">In an emergency, use</text>'
            f'<text x="0" y="41" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">a grown-up’s phone.</text>'
            f'<path d="{curl}" fill="#e9dfc8"/><g {WOB}><path d="{curl}" {LNS}/></g>'
            '</g>')

CARD = (722, 506, 156, 100)        # the front card in the card file: x, y, w, h
# The card file is a rotary one, seen a little from its right end: the cards fan back round the rod like a wheel,
# with the big knob at the hub, so it reads as a Rolodex. The front card (and its words) stand square to you.
CF_TURN = ""
def cf_turn_pt(x, y): return (x, y)
CF_ROD = 610
def _cf_card(theta, R=100):
    """One card on the rod, tipped back by theta degrees: (bottom-left, bottom-right, top-right, top-left)."""
    t = math.radians(theta); z = R * math.sin(t)
    dx, dy = .78 * z, -.3 * z
    top = CF_ROD - R * math.cos(t) + dy
    x0, x1 = CARD[0], CARD[0] + CARD[2]
    return [(x0, CF_ROD), (x1, CF_ROD), (x1 + dx, top), (x0 + dx, top)]
def card_file():
    """A rotary card file: the treehouse's phone book. The front card's words go in the overlay."""
    x, y, w, h = CARD
    g = [f'<ellipse cx="808" cy="668" rx="124" ry="13" fill="{WOOD_S}" opacity=".35" filter="url(#tls-soft)"/>']
    # the cards fanned back round the rod, furthest first; a few have index tabs
    tabs = {30: "#c9a24a", 60: "#6f8f5a", 90: "#b0372f"}
    for th in range(110, 0, -10):
        pts = _cf_card(th)
        d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + " Z"
        shade = 250 - int(th * .3)
        col = f"#{shade:02x}{shade-8:02x}{shade-26:02x}"
        g.append(f'<g {WASH}><path d="{d}" fill="{col}"/></g><g {WOB}><path d="{d}" {LNS}/></g>')
        if th in tabs:
            (_, _), (_, _), (tx, ty_), (_, _) = pts
            g.append(f'<path d="M{tx-30:.1f} {ty_:.1f} L{tx-28:.1f} {ty_-8:.1f} L{tx-10:.1f} {ty_-8:.1f} L{tx-8:.1f} {ty_:.1f} Z" fill="{tabs[th]}" stroke="{INK}" stroke-width=".9"/>')
    # the rod
    g.append(f'<path d="M708 {CF_ROD} L894 {CF_ROD}" stroke="url(#tls-metal)" stroke-width="7" stroke-linecap="round"/>')
    # the cradle: a low base with arms up to the knobs; its right end shows
    base = "M700 640 C700 633 705 630 712 630 L892 630 C898 630 902 633 902 640 L904 662 C905 667 902 670 896 670 L706 670 C700 670 697 667 698 662 Z"
    side = "M902 638 L922 626 L924 652 L904 668 Z"
    g += [shape(side, "#262420", edge="#000"), shape(base, "#3d3a35", edge="#000"),
          f'<path d="M712 637 L888 637" stroke="#fff" stroke-opacity=".22" stroke-width="2"/>',
          shape("M698 632 L710 632 L708 604 L700 604 Z", "#2f2c28", edge="#000"),
          shape("M892 632 L904 632 L906 604 L898 604 Z", "#2f2c28", edge="#000")]
    # the front card's shadow on the cards behind it
    g.append(f'<path d="{rrect(x, y, w, h, 4)}" fill="{INK}" opacity=".14" transform="translate(3 3)" filter="url(#tls-edge)"/>')
    # knobs: the near one big, at the hub of the fan; the far one smaller
    for kx, r in ((704, 20), (900, 26)):
        g.append(f'<circle cx="{kx+2}" cy="{CF_ROD+3}" r="{r}" fill="{INK}" opacity=".3"/>'
                 f'<circle cx="{kx}" cy="{CF_ROD}" r="{r}" fill="url(#tls-knob)"/><circle cx="{kx-r*.25:.1f}" cy="{CF_ROD-r*.3:.1f}" r="{r*.25:.1f}" fill="#fff" opacity=".22"/>'
                 f'<circle cx="{kx}" cy="{CF_ROD}" r="{r*.3:.1f}" fill="url(#tls-metal)"/>'
                 f'<g {WOB}><circle cx="{kx}" cy="{CF_ROD}" r="{r}" {LN}/><circle cx="{kx}" cy="{CF_ROD}" r="{r*.3:.1f}" {LNS}/></g>')
    for k in range(12):                                       # grip ridges on the big knob
        a_ = k / 12 * math.tau
        g.append(f'<path d="M{900+19*math.cos(a_):.1f} {CF_ROD+19*math.sin(a_):.1f} L{900+25*math.cos(a_):.1f} {CF_ROD+25*math.sin(a_):.1f}" stroke="#6b6258" stroke-width="1.5"/>')
    return "".join(g)

# ---------------------------------------------------------------- the shelf
def book():
    """The guide: an original 90s how-to book, leaning face-out. Origin: its bottom-left corner."""
    w, h = 150, 178
    x, y = 0, -h
    cover = rrect(x, y, w, h, 3)
    spine = f"M{w} {y+2} L{w+14} {y+10} L{w+14} {-2} L{w} {0} Z"
    burst = " ".join(f"{'M' if i == 0 else 'L'}{(26 if i % 2 == 0 else 19) * math.cos(math.radians(i * 18 - 90)):.1f} {(26 if i % 2 == 0 else 19) * math.sin(math.radians(i * 18 - 90)):.1f}" for i in range(20)) + " Z"
    g = [f'<ellipse cx="{w/2+6}" cy="0" rx="{w/2+14}" ry="6" fill="{INK}" opacity=".16" filter="url(#tls-edge)"/>', '<g>',
         f'<path d="{cover}" fill="{INK}" opacity=".16" transform="translate(8 2)" filter="url(#tls-edge)"/>',
         shape(spine, "#d9cfb8"), f'<g {WOB}><path d="M{w+3} {y+8} L{w+3} -4 M{w+7} {y+9} L{w+7} -3 M{w+11} {y+10} L{w+11} -2" {LNS}/></g>',
         shape(cover, "#fbf3df"),
         f'<g {WASH}><path d="M0 {y+3} Q0 {y} 3 {y} L{w-3} {y} Q{w} {y} {w} {y+3} L{w} {y+56} L0 {y+56} Z" fill="{SKY}"/></g>',
         f'<text x="12" y="{y+25}" {SERIF} font-size="15" font-weight="700" letter-spacing="1.4" fill="#fff">ROTARY</text>',
         f'<text x="12" y="{y+45}" {SERIF} font-size="15" font-weight="700" letter-spacing="1.4" fill="#fff">PHONES</text>',
         f'<text x="12" y="{y+78}" {SERIF} font-size="18" font-style="italic" fill="{INK}">the easy way</text>',
         f'<text x="12" y="{y+94}" {SANS} font-size="8.5" fill="#5e5546">Dialing, strings &amp; quiet time</text>',
         # a little dial on the cover
         f'<g {WOB}><circle cx="{w-42}" cy="{y+132}" r="26" {LN}/><circle cx="{w-42}" cy="{y+132}" r="9" {LNS}/>'
         + "".join(f'<circle cx="{w-42 + 18*math.cos(math.radians(a)):.1f}" cy="{y+132 + 18*math.sin(math.radians(a)):.1f}" r="3.6" {LNS}/>' for a in range(-150, 150, 30)) + '</g>',
         f'<path d="M0 {y+h-22} L{w} {y+h-22}" stroke="{SKY}" stroke-width="1.2"/>',
         f'<text x="12" y="{y+h-8}" {SANS} font-size="8" font-weight="700" letter-spacing="1" fill="{SKY}">TREELINE PRESS · 2ND ED.</text>',
         f'<text x="12" y="{y+118}" {SANS} font-size="9" font-weight="700" fill="{INK}">FOR KIDS</text>',
         f'<text x="12" y="{y+130}" {SANS} font-size="9" font-weight="700" fill="{INK}">&amp; GROWN-UPS</text>',
         f'<g transform="translate({w-14} {y+58}) rotate(12)"><path d="{burst}" fill="{BERRY}"/><g {WOB}><path d="{burst}" {LNS}/></g>'
         f'<text x="0" y="-2" text-anchor="middle" {SANS} font-size="7.5" font-weight="800" fill="#fff">4-DIGIT</text>'
         f'<text x="0" y="7" text-anchor="middle" {SANS} font-size="7.5" font-weight="800" fill="#fff">DIALING!</text></g>',
         f'<g opacity=".12" filter="url(#tls-grain)"><path d="{cover}" fill="#000"/></g>',
         '</g>']
    return "".join(g)

def spines():
    g = []
    for x, w, h, col in ((392, 30, 160, "#55704f"), (423, 26, 150, "#8f5f33"), (450, 34, 166, "#97483d"), (485, 24, 140, "#2a6488")):   # spines
        d = rrect(x, 1000 - h, w, h, 2)
        g.append(shape(d, col, edge="#000"))
        g.append(f'<path d="M{x+4} {1000-h+18} L{x+w-4} {1000-h+18} M{x+4} {1000-h+24} L{x+w-4} {1000-h+24} M{x+4} {1000-26} L{x+w-4} {1000-26}" stroke="{SUN}" stroke-width="1.6" opacity=".8"/>')
        g.append(f'<path d="M{x+w/2} {1000-h+40} L{x+w/2} {1000-50}" stroke="#fff" stroke-width="3" opacity=".25" stroke-linecap="round"/>')
    return "".join(g)

def warranty():
    g = []
    wx, wy, ww, wh = 0, -150, 118, 150
    card = rrect(wx, wy, ww, wh, 2)
    lines = "".join(f'<path d="M10 {wy+y_} L{ww-10 - (14 if i % 3 == 2 else 0)} {wy+y_}" stroke="{INK}" stroke-width="1.6" opacity=".22"/>' for i, y_ in enumerate(range(80, 132, 7)))
    g.append(f'<ellipse cx="{ww/2+4}" cy="0" rx="{ww/2+8}" ry="5" fill="{INK}" opacity=".16" filter="url(#tls-edge)"/><g>'
             f'<path d="{card}" fill="{INK}" opacity=".14" transform="translate(5 2)" filter="url(#tls-edge)"/>' + shape(card, "#fdfaf2")
             + f'<path d="M{wx} {wy+22} L{ww} {wy+22}" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3" opacity=".5"/>'
             f'<text x="{ww/2}" y="{wy+15}" text-anchor="middle" {MONO} font-size="8" fill="{INK}" opacity=".7">DETACH HERE</text>'
             f'<text x="10" y="{wy+44}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Owner’s</text>'
             f'<text x="10" y="{wy+60}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Warranty</text>'
             f'<text x="10" y="{wy+74}" {SANS} font-size="7.4" font-weight="700" fill="{CANOPY}">&amp; OPEN-SOURCE LICENSES</text>'
             + lines + f'<text x="10" y="{wy+wh-8}" {SANS} font-size="7.5" fill="{INK}" opacity=".7">Treeline Telephone Co.</text>'
             '</g>')
    return "".join(g)

def plant():
    g = []
    g.append(shape(rrect(672, 966, 178, 18, 2), "#c4ad82", edge="#000"))
    g.append(shape(rrect(684, 948, 160, 18, 2), "#7f9e74", edge="#000"))
    g.append(f'<path d="M690 957 L838 957" stroke="{SUN}" stroke-width="1.4" opacity=".7"/>')
    pot = "M732 948 L728 906 L800 906 L796 948 Z"
    g.append(shape(pot, "#c9744f", edge="#6a2f28"))
    g.append(shape("M724 896 L804 896 L804 910 L724 910 Z", "#d98a63", edge="#6a2f28"))
    g.append(f'<g {WOB}><path d="M764 896 C762 870 766 850 764 828" {LN}/><path d="M764 862 C752 856 744 848 740 838 M765 850 C776 842 784 832 786 822" {LN}/></g>')
    for cx_, cy_, r_, c in ((738, 832, 17, "#7f9e74"), (790, 820, 18, "#7f9e74"), (764, 808, 24, "#9db88e"), (762, 836, 14, "#6c8c62")):
        g.append(f'<g {WASH}><circle cx="{cx_}" cy="{cy_}" r="{r_}" fill="{c}"/></g><g {WOB}><circle cx="{cx_}" cy="{cy_}" r="{r_}" {LNS}/></g>')
    return "".join(g)


# ---------------------------------------------------------------- the table, any size
def leg(x0, x1, y0, y1, taper=4):
    return f"M{x0} {y0} L{x1} {y0} L{x1-taper} {y1} L{x0+taper} {y1} Z"

def table(t):
    """Returns (behind the shelf things, the shelf's front edge, the front of the table)."""
    x0, x1, ty, inset, ch, sy, H = t["x0"], t["x1"], t["ty"], t["inset"], t["ch"], t["sy"], t["H"]
    cx = (x0 + x1) / 2; F = ty + 114; cb = F + 54 + ch
    TOP = (f"M{x0+inset} {ty+6} C{x0+inset} {ty+2} {x0+inset+4} {ty} {x0+inset+10} {ty} L{x1-inset-10} {ty} C{x1-inset-4} {ty} {x1-inset} {ty+2} {x1-inset} {ty+6} "
           f"L{x1} {F} C{x1+2} {F+4} {x1} {F+6} {x1-6} {F+6} L{x0+6} {F+6} C{x0} {F+6} {x0-2} {F+4} {x0} {F} Z")
    APRON = f"M{x0} {F+6} L{x1} {F+6} L{x1} {F+46} C{x1} {F+52} {x1-4} {F+54} {x1-10} {F+54} L{x0+10} {F+54} C{x0+4} {F+54} {x0} {F+52} {x0} {F+46} Z"
    CARC = f"M{x0+32} {F+54} L{x1-32} {F+54} L{x1-32} {cb} L{x0+32} {cb} Z"
    dx, dy, dw, dh = t["drawer"]
    DRAWER = rrect(dx, dy, dw, dh, 6)
    STOP = f"M{x0+60} {sy} L{x1-60} {sy} L{x1-26} {sy+26} L{x0+26} {sy+26} Z"
    SFRONT = f"M{x0+26} {sy+26} L{x1-26} {sy+26} L{x1-26} {sy+50} C{x1-26} {sy+54} {x1-29} {sy+56} {x1-33} {sy+56} L{x0+33} {sy+56} C{x0+29} {sy+56} {x0+26} {sy+54} {x0+26} {sy+50} Z"
    back = [shape(leg(x0+84, x0+110, cb, H + 10, 2), WOOD_D), shape(leg(x1-110, x1-84, cb, H + 10, 2), WOOD_D), shape(STOP, "url(#tls-top)"),
            f'<g {WOB}><path d="M{x0+68} {sy+6} C{x0+230} {sy+4} {x1-230} {sy+4} {x1-68} {sy+6}" {LNS}/></g>']
    sfront = [shape(SFRONT, "url(#tls-front)", edge=WOOD_S), f'<g opacity=".18" filter="url(#tls-grain)"><path d="{STOP} {SFRONT}" fill="#000"/></g>']
    front = [shape(leg(x0+32, x0+70, cb, H + 10), "url(#tls-leg)", edge=WOOD_S), shape(leg(x1-70, x1-32, cb, H + 10), "url(#tls-leg)", edge=WOOD_S),
             shape(CARC, "url(#tls-front)", edge=WOOD_S),
             shape(DRAWER, WOOD_M, edge=WOOD_S, extra=f'<path d="M{dx+14} {dy+10} L{dx+dw-14} {dy+10}" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>'),
             ]
    kx, ky = t["knob"]
    front += [f'<ellipse cx="{kx}" cy="{ky+2}" rx="11" ry="7" fill="{WOOD_S}" opacity=".5" transform="translate(1 3)"/>',
              f'<circle cx="{kx}" cy="{ky}" r="9" fill="url(#tls-metal)"/><g {WOB}><circle cx="{kx}" cy="{ky}" r="9" {LN}/></g>',
              shape(APRON, "url(#tls-front)", edge=WOOD_S),
              shape(TOP, "url(#tls-top)", extra=f'<path d="M{x0+inset+10} {ty+8} L{x1-inset-10} {ty+8}" stroke="#fff" stroke-opacity=".25" stroke-width="3"/>')]
    for f in (.2, .41, .65, .9):     # wood grain
        y = ty + 114 * f; a = x0 + inset * (1 - f); b = x1 - inset * (1 - f)
        front.append(f'<g {WOB}><path d="M{a:.0f} {y:.0f} C{a+150:.0f} {y-3:.0f} {a+260:.0f} {y+3:.0f} {(a+b)/2:.0f} {y:.0f} S{b-120:.0f} {y-3:.0f} {b:.0f} {y+1:.0f}" fill="none" stroke="{WOOD_D}" stroke-width="1" opacity=".35"/></g>')
    front.append(f'<g opacity=".16" filter="url(#tls-grain)"><path d="{TOP} {APRON} {CARC}" fill="#000"/></g>')
    front.append(wear(t, TOP, F, cb, cx))
    front.append(f'<g {WOB}><path d="M{x0+8} {F+16} L{x1-8} {F+16}" {LNS}/></g>')
    return "".join(back), "".join(sfront), "".join(front)

def wear(t, TOP, F, cb, cx):
    """A well-loved table: varnish worn off the edges, scratches, cup rings, a chipped corner, dents,
    a knot, scuffed legs and a worn patch round the knob."""
    import random
    rnd = random.Random(int(t["x1"] * 7 + t["ty"]))
    x0, x1, ty, inset = t["x0"], t["x1"], t["ty"], t["inset"]
    w = x1 - x0
    g = [f'<clipPath id="tls-topclip{int(ty)}"><path d="{TOP}"/></clipPath>', f'<g clip-path="url(#tls-topclip{int(ty)})">']
    # varnish worn pale along the front edge, where hands and elbows go
    for i in range(7):
        a = x0 + 20 + rnd.random() * (w - 120); l = 30 + rnd.random() * 80
        g.append(f'<path d="M{a:.0f} {F-4-rnd.random()*6:.0f} q{l/2:.0f} {-2-rnd.random()*3:.1f} {l:.0f} {rnd.random()*2:.1f}" stroke="#f3d9b4" stroke-width="{3+rnd.random()*5:.1f}" stroke-linecap="round" opacity=".55" fill="none"/>')
    # scratches
    for i in range(24):
        a = x0 + inset + rnd.random() * (w - 2 * inset); b = ty + 10 + rnd.random() * 96; l = 12 + rnd.random() * 46; ang = rnd.uniform(-.35, .35)
        g.append(f'<path d="M{a:.0f} {b:.0f} l{l*math.cos(ang):.1f} {l*math.sin(ang)*.5:.1f}" stroke="#f8e6c9" stroke-width="1.1" opacity=".85" fill="none"/>'
                 f'<path d="M{a:.0f} {b+1.2:.1f} l{l*math.cos(ang):.1f} {l*math.sin(ang)*.5:.1f}" stroke="{WOOD_S}" stroke-width=".6" opacity=".35" fill="none"/>')
    # two old cup rings
    for cxr, cyr, r in ((x0 + w * .16, ty + 70, 22), (x1 - w * .2, ty + 96, 19)):
        g.append(f'<g {WOB}><ellipse cx="{cxr:.0f}" cy="{cyr:.0f}" rx="{r}" ry="{r*.42:.1f}" fill="none" stroke="#7a4a22" stroke-width="2.2" stroke-dasharray="{r*1.6:.0f} 6 {r*.7:.0f} 4" opacity=".3"/></g>')
    # a knot in the wood
    kx, ky = x0 + w * .63, ty + 34
    g.append(f'<g {WOB}><ellipse cx="{kx:.0f}" cy="{ky}" rx="9" ry="4" fill="{WOOD_D}" opacity=".5"/><ellipse cx="{kx:.0f}" cy="{ky}" rx="17" ry="7" fill="none" stroke="{WOOD_D}" stroke-width="1" opacity=".35"/><ellipse cx="{kx:.0f}" cy="{ky}" rx="26" ry="10" fill="none" stroke="{WOOD_D}" stroke-width=".8" opacity=".25"/></g>')
    g.append('</g>')
    # a chip out of the front-left corner of the top: bare, paler wood
    g.append(f'<g {WOB}><path d="M{x0+2} {F-14} L{x0+18} {F-8} L{x0+14} {F+6} L{x0+2} {F+6} Z" fill="#e8c597"/><path d="M{x0+2} {F-14} L{x0+18} {F-8} L{x0+14} {F+6}" {LNS}/></g>')
    # dents and dings along the apron's edge
    for i in range(9):
        a = x0 + 14 + rnd.random() * (w - 28); yy = F + 10 + rnd.random() * 36
        g.append(f'<path d="M{a:.0f} {yy:.0f} q3 2 6 0" stroke="{WOOD_S}" stroke-width="1.3" opacity=".5" fill="none"/><path d="M{a:.0f} {yy+1.5:.1f} q3 2 6 0" stroke="#f1d6ae" stroke-width=".8" opacity=".5" fill="none"/>')
    # scuffs low on the legs, from feet and toys
    for lx in (x0 + 36, x1 - 66):
        for i in range(4):
            yy = cb + 30 + rnd.random() * 200
            g.append(f'<path d="M{lx+rnd.random()*10:.0f} {yy:.0f} l{14+rnd.random()*10:.0f} {rnd.uniform(-2,2):.1f}" stroke="#f3d9b4" stroke-width="1.6" opacity=".45" stroke-linecap="round"/>')
    # worn round the knob
    kx2, ky2 = t["knob"]
    g.append(f'<ellipse cx="{kx2}" cy="{ky2}" rx="26" ry="18" fill="#e9c99c" opacity=".35" filter="url(#tls-edge)"/>')
    return "".join(g)

# ---------------------------------------------------------------- the two layouts
# Every prop is drawn once, in the wide room's coordinates, and placed in a layout by
# translate + scale: place = (old x, old y, new x, new y, scale).
BOX = {   # each prop's box in the wide room's coordinates (what its link covers)
    "sticky": (72, 150, 176, 176), "sketch": (92, 360, 200, 160), "cork": (676, 64, 290, 340),
    "coffee": (688, 80, 268, 166), "card": (688, 246, 240, 152), "cardfile": (680, 470, 282, 204),
    "book": (-14, -186, 186, 196), "warranty": (-10, -155, 150, 160),
}
def placed(content, pl):
    ox, oy, nx, ny, s = pl
    return f'<g transform="translate({nx} {ny}) scale({s}) translate({-ox} {-oy})">{content}</g>'
def moved(box, pl):
    ox, oy, nx, ny, s = pl; bx, by, bw, bh = box
    return (round(nx + (bx - ox) * s, 1), round(ny + (by - oy) * s, 1), round(bw * s, 1), round(bh * s, 1))

# ---------------------------------------------------------------- the guide book, spine out
BOOK_W, BOOK_T = 200, 30          # length of the spine, thickness of the book
def book_spine(x0, by, w=BOOK_W, t=BOOK_T, depth=60):
    """The guide lying flat on its back cover, spine toward you: the title reads across the spine."""
    x1 = x0 + w; top = by - t - depth
    face = f"M{x0} {top} L{x1} {top} L{x1} {top+depth} L{x0} {top+depth} Z"      # square, so the cover picture fills it exactly
    spine = (f"M{x0} {top+depth} L{x1} {top+depth} C{x1+5} {top+depth+t*.3} {x1+5} {by-t*.3} {x1} {by} "
             f"L{x0} {by} C{x0-5} {by-t*.3} {x0-5} {top+depth+t*.3} {x0} {top+depth} Z")
    g = [f'<ellipse cx="{x0+w/2}" cy="{by+2}" rx="{w/2+16}" ry="8" fill="{INK}" opacity=".2" filter="url(#tls-edge)"/>',
         shape(face, "#fbf3df"),
         # the front cover, seen from above: the same design as the book's real cover (desk_pages), lying with
         # its spine edge toward you, so its top points left. Plain shapes only: no ids, since the room is drawn three ways.
         f'<clipPath id="tls-bookface{int(x0)}{int(by)}"><path d="{face}"/></clipPath>',
         f'<g clip-path="url(#tls-bookface{int(x0)}{int(by)})"><g transform="translate({x0} {top+depth}) scale({w/450:.4f} {depth/300:.4f}) rotate(-90)">'
         f'<image href="{COVER_IMAGE}" width="300" height="450" preserveAspectRatio="none"/></g></g>',
         f'<g {WOB}><path d="{face}" {LN}/></g>',
         shape(spine, SKY, edge="#0f2c40"),
         f'<path d="M{x0+4} {top+depth+7} L{x1-4} {top+depth+7}" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>',
         f'<path d="M{x0+30} {top+depth+4} L{x0+30} {by-4} M{x0+34} {top+depth+4} L{x0+34} {by-4} M{x1-34} {top+depth+4} L{x1-34} {by-4} M{x1-30} {top+depth+4} L{x1-30} {by-4}" stroke="{SUN}" stroke-width="1.6"/>',
         f'<text x="{x0+42}" y="{by-t/2+1}" {SERIF} font-size="{15*min(1, (w-84)/116):.1f}" font-weight="700" letter-spacing="1.2" fill="#fff" textLength="{w-84}" lengthAdjust="spacingAndGlyphs">ROTARY PHONES</text>',
         f'<text x="{x0+42}" y="{by-t/2+15}" {SERIF} font-size="10.5" font-style="italic" fill="#fff" opacity=".92">the easy way</text>',
         f'<text x="{x0+15}" y="{by-t/2+4}" text-anchor="middle" {SANS} font-size="9" font-weight="800" fill="{SUN}">2</text>',
         f'<g transform="translate({x1-15} {by-t/2})"><path d="M0 -8 C5 -4 5 4 0 8 C-5 4 -5 -4 0 -8Z" fill="#7fc49a"/></g>',
         f'<g opacity=".14" filter="url(#tls-grain)"><path d="{spine}" fill="#000"/></g>']
    return "".join(g)

# The book's real cover, exactly as it is when you pick the book up (desk_pages page 0, with its fonts),
# as a picture: laid on the book on the table, turned and squashed to the table's angle.
import base64, os
_here = os.path.dirname(os.path.abspath(__file__))
_cov = next((f for f in (os.path.join(_here, "cover.jpg"), os.path.join(_here, "out", "cover.jpg")) if os.path.exists(f)), "")
COVER_IMAGE = "data:image/jpeg;base64," + base64.b64encode(open(_cov, "rb").read()).decode() if _cov else ""

def cover_top():
    """The guide's front cover (300 x 356): the same design as the cover in the book (desk_pages), drawn
    here with plain shapes, for the top of the book on the table."""
    burst = " ".join(f"{'M' if i == 0 else 'L'}{(31 if i % 2 == 0 else 24) * math.cos(math.radians(i * 15 - 90)):.1f} {(31 if i % 2 == 0 else 24) * math.sin(math.radians(i * 15 - 90)):.1f}" for i in range(24)) + " Z"
    holes = "".join(f'<circle cx="{216 + 17 * math.cos(math.radians(a)):.1f}" cy="{276 + 15 * math.sin(math.radians(a)):.1f}" r="3.4" fill="#fbf6ea" stroke="#3a4d36" stroke-width="1"/>' for a in range(-150, 150, 30))
    phone = (f'<ellipse cx="216" cy="312" rx="56" ry="7" fill="{INK}" opacity=".18"/>'
             f'<path d="M168 306 C166 270 172 250 192 246 L240 246 C260 250 266 270 264 306 C264 312 260 314 254 314 L178 314 C172 314 168 312 168 306 Z" fill="#7f9e74" stroke="{INK}" stroke-width="1.6"/>'
             f'<path d="M160 236 C158 226 164 220 174 220 C196 214 236 214 258 220 C268 220 274 226 272 236 C266 246 254 246 250 238 C236 232 196 232 182 238 C178 246 166 246 160 236 Z" fill="#55704f" stroke="{INK}" stroke-width="1.6"/>'
             f'<ellipse cx="216" cy="276" rx="25" ry="22" fill="#f3ead6" stroke="{INK}" stroke-width="1.4"/>' + holes
             + f'<ellipse cx="216" cy="276" rx="8" ry="7" fill="#fbf6ea" stroke="#3a4d36" stroke-width="1"/>'
             f'<path d="M166 262 c-8 4 -8 12 0 14 c-8 4 -8 12 0 14 c-8 4 -8 12 0 14" fill="none" stroke="#55704f" stroke-width="2.4"/>')
    return (f'<rect width="300" height="356" fill="#fbf3df"/><rect width="300" height="122" fill="{SKY}"/><rect y="122" width="300" height="5" fill="{SUN}"/>'
            f'<text x="26" y="56" {SERIF} font-size="36" font-weight="700" letter-spacing="3" fill="#fff">ROTARY</text>'
            f'<text x="26" y="98" {SERIF} font-size="36" font-weight="700" letter-spacing="3" fill="#fff">PHONES</text>'
            f'<text x="26" y="166" {SERIF} font-size="30" font-style="italic" fill="{INK}">the easy way</text>'
            f'<path d="M26 182 L138 182" stroke="{SKY}" stroke-width="1.6"/>'
            f'<text x="26" y="204" {SANS} font-size="12" fill="#5e5546">How to call a friend</text>'
            f'<text x="26" y="220" {SANS} font-size="12" fill="#5e5546">from your treehouse</text>'
            f'<text x="26" y="286" {SANS} font-size="11" font-weight="700" letter-spacing="1.2" fill="{INK}">FOR KIDS</text>'
            f'<text x="26" y="302" {SANS} font-size="11" font-weight="700" letter-spacing="1.2" fill="{INK}">&amp; GROWN-UPS</text>'
            + phone +
            f'<g transform="translate(246 122) rotate(14)"><path d="{burst}" fill="{BERRY}"/>'
            f'<text x="0" y="-3" text-anchor="middle" {SANS} font-size="10" font-weight="800" fill="#fff">4-DIGIT</text>'
            f'<text x="0" y="9" text-anchor="middle" {SANS} font-size="10" font-weight="800" fill="#fff">DIALING!</text></g>'
            f'<path d="M26 326 L274 326" stroke="{SKY}" stroke-width="1.4"/>'
            f'<text x="26" y="344" {SANS} font-size="10" font-weight="700" letter-spacing="1.6" fill="{SKY}">TREELINE PRESS</text>'
            f'<text x="274" y="344" text-anchor="end" {SANS} font-size="10" font-weight="700" letter-spacing="1.6" fill="{SKY}">2ND EDITION</text>'
            f'<rect width="300" height="356" fill="none" stroke="{INK}" stroke-width="2" opacity=".5"/>')

def book_box(x0, by, w=BOOK_W, t=BOOK_T, depth=60):
    return (x0 - 8, by - t - depth - 6, w + 16, t + depth + 14)

# ---------------------------------------------------------------- the warranty card, sticking out of the drawer
def warranty_face(turn=0):
    src = warranty()
    inner = src[src.index('<g>') + 3: src.rindex('</g>')]
    return f'<g transform="translate(0 150)">{inner}</g>'

def drawer_peek(x, y, x0, x1, k):
    """The drawer is open a crack (a dark gap along its top) and the warranty card sticks up out of it."""
    gap = f'<path d="M{x0+6} {y} L{x1-6} {y} L{x1-8} {y+9} L{x0+8} {y+9} Z" fill="#2a1d10" opacity=".78"/>'
    card = f'<g transform="translate({x-20} {y+8}) rotate(-8)"><g transform="translate(0 -74) scale(.72)">{warranty_face()}</g></g>'
    clip = f'<clipPath id="tls-peek{k}"><rect x="{x-160}" y="{y-220}" width="320" height="226"/></clipPath>'
    return gap + f'<defs>{clip}</defs><g clip-path="url(#tls-peek{k})">{card}</g>'

def peek_box(x, y):
    return (x - 34, y - 84, 112, 92)

LAYOUTS = {
    # Landscape tablets and desktops: zoomed in on the phone and the table top. No shelf: the guide book lies
    # on the table, and the legs run off the bottom just under the drawer.
    "wide": {"W": 1100, "H": 890,
        "table": {"x0": 40, "x1": 1060, "ty": 590, "inset": 80, "ch": 120, "sy": 2000, "H": 890,
                  "drawer": (336, 768, 428, 100), "knob": (374, 818)},
        "phone": {"x": 270, "y": 2, "w": 560},
        "sticker": (510, 820, .78, .78, -3),
        "bookspine": (70, 692, 228), "peek": (668, 768),
        "place": {"sticky": (72, 150, 34, 40, 1), "sketch": (92, 360, 46, 252, .92), "cork": (676, 64, 800, 40, 1),
                  "cardfile": (684, 674, 738, 650, .8)},
        "shelf": [], "table_items": ["cardfile"], "sketch": True},
    # Tablets held upright: the same side table, the phone much bigger, the corkboard down beside it.
    "portrait": {"W": 1000, "H": 1304,
        "table": {"x0": 60, "x1": 940, "ty": 800, "inset": 78, "ch": 120, "sy": 1224, "H": 1304,
                  "drawer": (286, 978, 428, 100), "knob": (324, 1028)},
        "phone": {"x": 170, "y": 49, "w": 660},
        "sticker": (466, 1030, .78, .78, -3),
        "bookspine": (66, 898, 186), "peek": (624, 978),
        "place": {"sticky": (72, 150, 20, 60, 1), "sketch": (92, 360, 30, 290, .9), "cork": (676, 64, 788, 180, .72),
                  "cardfile": (684, 674, 700, 888, .78), "spines": (0, 0, 120, 440, .8), "plant": (0, 0, 172, 453, .8)},
        "shelf": ["spines", "plant"], "table_items": ["cardfile"], "sketch": True},
    # Phones: a narrow nightstand, the phone across nearly the whole width, the wall things above it,
    # the book and the card file on the shelf.
    "tall": {"W": 600, "H": 1340,
        "table": {"x0": 8, "x1": 592, "ty": 812, "inset": 50, "ch": 138, "sy": 1270, "H": 1340,
                  "drawer": (70, 990, 460, 118), "knob": (108, 1049)},
        "phone": {"x": 28, "y": 245, "w": 544},
        "sticker": (290, 1050, .85, .85, -3),
        "bookspine": (82, 1290, 150), "peek": (452, 990),
        "place": {"sticky": (72, 150, 12, 28, .96), "sketch": (92, 360, 14, 214, .85), "cork": (676, 64, 350, 12, .82),
                  "cardfile": (684, 674, 238, 1286, .6)},
        "shelf": ["cardfile"], "table_items": [], "sketch": True},
}

def scene(name):
    L = LAYOUTS[name]; W_, H_ = L["W"], L["H"]; pl = L["place"]
    back, sfront, front = table(L["table"])
    draw = {"book": book, "warranty": warranty, "spines": spines, "plant": plant, "cardfile": card_file}
    item = lambda k: placed(draw[k](), pl[k])
    bx, by, bw = L["bookspine"]; px, py = L["peek"]; dx, dy, dw, dh = L["table"]["drawer"]
    book_here = book_spine(bx, by, bw)
    on_shelf = by > L["table"]["sy"]
    body = (wall(W_, H_) + placed(sticky_note(), pl["sticky"]) + (placed(kid_drawing(), pl["sketch"]) if L["sketch"] else "")
            + placed(corkboard(), pl["cork"]) + back + "".join(item(k) for k in L["shelf"]) + (book_here if on_shelf else "") + sfront + front
            + drawer_peek(px, py, dx, dx + dw, "") + sticker(*L["sticker"]) + (book_here if not on_shelf else "") + "".join(item(k) for k in L["table_items"]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__scene tl-desk__l tl-desk__l--{name}" viewBox="0 0 {W_} {H_}" '
            f'preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">{defs()}{body}</svg>')

def words(name, nm="Sam’s treehouse", quiet="8 pm – 7 am", contact=("The Parks", "3317"), count="1 of 3", size="24"):
    """The words that change, in their own layer: the name on the kid's drawing, the sticky note, the card file's front card."""
    L = LAYOUTS[name]; pl = L["place"]
    x, y, w, h = CARD
    dx, dy, dw, dh = DRAW
    nmg = (f'<g transform="rotate(-2 {dx+dw/2} {dy+dh/2})"><text class="tl-desk__name" x="{dx+14}" y="{dy+32}" {HAND} font-size="{size}" font-weight="700" fill="{SKY}">{nm}</text></g>')
    q = (f'<g transform="rotate(-4 160 243)"><text x="160" y="214" text-anchor="middle" {HAND} font-size="30" font-weight="700" fill="{INK}">Quiet time</text>'
         f'<text class="tl-desk__quiettext" x="160" y="256" text-anchor="middle" {HAND} font-size="30" fill="{INK}">{quiet}</text>'
         f'<path d="M108 270 Q160 278 212 268" fill="none" stroke="{BERRY}" stroke-width="2" stroke-linecap="round"/></g>')
    fr = rrect(x, y, w, h, 4)
    paper = (f'<path d="{fr}" fill="#fffaf0"/><path d="{fr}" fill="url(#tls-wpaper)"/>'
             f'<path d="M{x+8} {y+26} L{x+w-8} {y+26}" stroke="{BERRY}" stroke-width="1" opacity=".55"/>'
             + "".join(f'<path d="M{x+8} {yy} L{x+w-8} {yy}" stroke="{SKY}" stroke-width=".8" opacity=".4"/>' for yy in (y+52, y+78))
             + f'<path d="{fr}" {LN} filter="url(#tls-wwob)"/>')
    c = (f'<g class="tl-desk__card">{paper}<text class="tl-desk__cardname" x="{x+12}" y="{y+46}" {HAND} font-size="25" font-weight="700" fill="{INK}">{contact[0]}</text>'
         f'<text class="tl-desk__cardnum" x="{x+12}" y="{y+74}" {HAND} font-size="29" fill="{SKY}">{contact[1]}</text>'
         f'<text class="tl-desk__cardcount" x="{x+w-10}" y="{y+19}" text-anchor="end" {SANS} font-size="9.5" fill="#857b6b">{count}</text></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__words tl-desk__l tl-desk__l--{name}" viewBox="0 0 {L["W"]} {L["H"]}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">'
            f'<defs><filter id="tls-wwob" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="1.8"/></filter>'
            f'<linearGradient id="tls-wpaper" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffdf7"/><stop offset="1" stop-color="#f1e6cf"/></linearGradient></defs>'
            + placed(nmg, pl["sketch"]) + placed(q, pl["sticky"]) + placed(f'<g transform="{CF_TURN}">{c}</g>', pl["cardfile"])
            + '</svg>')

def words_template(name):
    return words(name, nm="{{NAME}}", quiet="{{QUIET}}", contact=("{{CNAME}}", "{{CNUM}}"), count="{{CCOUNT}}", size="{{NAMESIZE}}")

def turned_box(b):
    x, y, w, h = b
    pts = [cf_turn_pt(px, py) for px in (x, x + w) for py in (y, y + h)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs) - min(xs) + 6, max(ys) - min(ys))
def geometry(name):
    L = LAYOUTS[name]; pl = L["place"]
    bx, by, bw = L["bookspine"]; px, py = L["peek"]
    hot = {"guide": book_box(bx, by, bw), "licenses": peek_box(px, py),
           "coffee": moved(BOX["coffee"], pl["cork"]), "card": moved(BOX["card"], pl["cork"]), "cardfile": moved(turned_box(BOX["cardfile"]), pl["cardfile"])}
    return {"w": L["W"], "h": L["H"], "phone": L["phone"], "hotspots": hot}

GEOM = {n: geometry(n) for n in LAYOUTS}

if __name__ == "__main__":
    out = "/home/claude/treeline/build/phone/out"
    for n in LAYOUTS:
        open(f"{out}/desk-{n}.svg", "w").write(scene(n))
        open(f"{out}/desk-{n}-words.svg", "w").write(words(n))
    json.dump(GEOM, open(f"{out}/desk-geometry.json", "w"), indent=1)
    print(json.dumps(GEOM))
