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
PAPER = "#f4e9d0"

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


_CLIPS = [0]
def _clip(d):
    _CLIPS[0] += 1
    cid = f"tls-wx{_CLIPS[0]}"
    return cid, f'<clipPath id="{cid}"><path d="{d}"/></clipPath>'

def grime(d, box, seed=1, n=10, color="#4a3216", dust=40):
    """Dirt ground into a surface: soft brown blotches and specks, kept inside the shape d."""
    import random
    rnd = random.Random(seed)
    x, y, w, h = box
    cid, cp = _clip(d)
    g = [cp, f'<g clip-path="url(#{cid})">']
    for i in range(n):
        cx_, cy_ = x + rnd.random() * w, y + rnd.random() * h
        g.append(f'<ellipse cx="{cx_:.0f}" cy="{cy_:.0f}" rx="{8 + rnd.random() * w * .12:.0f}" ry="{5 + rnd.random() * h * .18:.0f}" fill="{color}" opacity="{.06 + rnd.random() * .09:.2f}" filter="url(#tls-soft)"/>')
    for i in range(dust):
        g.append(f'<circle cx="{x + rnd.random() * w:.1f}" cy="{y + rnd.random() * h:.1f}" r="{.5 + rnd.random() * 1.1:.1f}" fill="{color}" opacity="{.2 + rnd.random() * .3:.2f}"/>')
    g.append('</g>')
    return "".join(g)

def aged(d, box, seed=1, ring=None):
    """Old paper: browned edges, a water stain or two, and maybe a cup ring."""
    import random
    rnd = random.Random(seed)
    x, y, w, h = box
    cid, cp = _clip(d)
    g = [cp, f'<g clip-path="url(#{cid})">',
         f'<path d="{d}" fill="none" stroke="#9c7a3e" stroke-opacity=".38" stroke-width="{max(8, min(w, h) * .12):.0f}" filter="url(#tls-edge)"/>']
    for i in range(2):
        cx_, cy_ = x + rnd.uniform(.2, .8) * w, y + rnd.uniform(.2, .8) * h; r = min(w, h) * rnd.uniform(.12, .22)
        g.append(f'<ellipse cx="{cx_:.0f}" cy="{cy_:.0f}" rx="{r:.0f}" ry="{r*.8:.0f}" fill="#b8955a" opacity=".1" filter="url(#tls-soft)"/>'
                 f'<ellipse cx="{cx_:.0f}" cy="{cy_:.0f}" rx="{r:.0f}" ry="{r*.8:.0f}" fill="none" stroke="#a5813f" stroke-width="1" opacity=".22"/>')
    if ring:
        rx_, ry_, rr = ring
        g.append(f'<g {WOB}><circle cx="{rx_}" cy="{ry_}" r="{rr}" fill="none" stroke="#7a4f22" stroke-width="3" stroke-dasharray="{rr*2.2:.0f} 5 {rr*1.4:.0f} 7" opacity=".28"/></g>')
    for i in range(18):
        g.append(f'<circle cx="{x + rnd.random() * w:.1f}" cy="{y + rnd.random() * h:.1f}" r="{.4 + rnd.random() * .8:.1f}" fill="#6b4a22" opacity=".25"/>')
    g.append('</g>')
    return "".join(g)

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
            + shape(d, "#ecd585", edge="#c9a03e") + aged(d, (x, y, 158, 156), 23)
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
         shape(paper, "#f3e9d2"), aged(paper, (x, y, w, h), 24)]
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
    g.append(stick_frame(x - 4, y - 4, w + 8, h + 8, 8, 11))
    g.append('</g>')
    return "".join(g)

def corkboard():
    x, y, w, h = 676, 64, 290, 340
    outer, inner = rrect(x, y, w, h, 6), rrect(x+14, y+14, w-28, h-28, 3)
    g = [f'<path d="{inner}" fill="{INK}" opacity=".16" transform="translate(6 9)" filter="url(#tls-edge)"/>',
         f'<g {WASH}><path d="{inner}" fill="url(#tls-cork)"/></g>',
         f'<path d="{inner}" fill="none" stroke="{WOOD_S}" stroke-opacity=".35" stroke-width="10" filter="url(#tls-edge)"/>',
         grime(inner, (x+14, y+14, w-28, h-28), 31, 12, "#3e2a12", 30),
         f'<g {WOB}><path d="{inner}" {LN}/></g>', stick_frame(x+14, y+14, w-28, h-28, 11, 5)]
    g.append(certificate())
    g.append(business_card())
    return "".join(g)

def certificate(turn=3):
    x, y, w, h = 694, 92, 254, 140
    d = rrect(x, y, w, h, 3)
    g = [f'<g transform="rotate({turn} {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, "#f1e3c2"), aged(d, (x, y, w, h), 21, ring=(x + w - 46, y + h - 34, 24)),
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
def business_card(turn=-3):
    x, y, w, h = 694, 254, 222, 124
    d = rrect(x, y, w, h, 3)
    logo = open("/home/claude/treeline/project/assets/Logos/treeline-logo.svg").read()
    logo = logo.replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 14 222 146" width="444" height="292">', f'<svg x="{x+14}" y="{y+16}" width="66" height="44" viewBox="10 14 222 146">')
    g = [f'<g transform="rotate({turn} {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, PAPER), aged(d, (x, y, w, h), 22), logo,
         f'<text x="{x+90}" y="{y+44}" {SERIF} font-size="24" font-weight="600" fill="{INK}">Treeline</text>',
         f'<path d="M{x+14} {y+70} L{x+w-14} {y+70}" stroke="{INK}" stroke-width=".8" opacity=".35"/>',
         f'<text x="{x+16}" y="{y+89}" {SANS} font-size="13" font-weight="600" fill="{INK}">Made by Jordan Miller</text>',
         f'<text x="{x+16}" y="{y+105}" {SANS} font-size="12" fill="#5e5546">jdmiller2010@gmail.com</text>',
         f'<text x="{x+16}" y="{y+118}" {SANS} font-size="9.5" fill="#857b6b">© 2026 Jordan Miller · noncommercial use</text>',
         pin(x+w-24, y+14, SKY), '</g>']
    return "".join(g)


def sticker(cx, cy, sx=.9, sy=.72, rot=-5):
    """The no-911 sticker. On a table top it's squashed for perspective; on a drawer front it isn't."""
    w, h = 196, 118
    d = rrect(-w/2, -h/2, w, h, 16)
    curl = f"M{w/2-30} {h/2} Q{w/2-6} {h/2-6} {w/2} {h/2-30} L{w/2} {h/2-16} Q{w/2} {h/2} {w/2-16} {h/2} Z"
    return (f'<g transform="translate({cx} {cy}) rotate({rot}) scale({sx} {sy})">'
            f'<path d="{d}" fill="{INK}" opacity=".12" transform="translate(2 4)" filter="url(#tls-edge)"/>'
            + shape(d, "#f6efe0")
            + f'<path d="{rrect(-w/2+7, -h/2+7, w-14, h-14, 11)}" fill="none" stroke="{BERRY}" stroke-width="5"/>'
            + aged(d, (-w/2, -h/2, w, h), 26)
            + f'<text x="0" y="-16" text-anchor="middle" {SANS} font-size="33" font-weight="800" letter-spacing="1" fill="{BERRY}">NO 911</text>'
            f'<text x="0" y="6" text-anchor="middle" {SANS} font-size="14" font-weight="700" fill="{INK}">No outside calls.</text>'
            f'<text x="0" y="25" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">In an emergency, use</text>'
            f'<text x="0" y="41" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">a grown-up’s phone.</text>'
            f'<path d="{curl}" fill="#e9dfc8"/><g {WOB}><path d="{curl}" {LNS}/></g>'
            '</g>')

CARD = (722, 506, 156, 100)        # the front card in the card file: x, y, w, h
def card_file_old():
    """(Replaced by the angled card file below.)"""
    x, y, w, h = CARD
    g = [f'<ellipse cx="800" cy="668" rx="118" ry="13" fill="{WOOD_S}" opacity=".35" filter="url(#tls-soft)"/>']
    base = "M716 640 C716 632 722 628 730 628 L870 628 C878 628 884 632 884 640 L890 662 C891 667 888 670 882 670 L718 670 C712 670 709 667 710 662 Z"
    g.append(shape(base, "#3d3a35", edge="#000"))
    g.append(f'<path d="M726 636 L874 636" stroke="#fff" stroke-opacity=".25" stroke-width="2"/>')
    g.append(f'<path d="M712 610 L888 610" stroke="url(#tls-metal)" stroke-width="7" stroke-linecap="round"/><g {WOB}><path d="M712 607 L888 607 M712 613 L888 613" {LNS}/></g>')
    for i, (dx, dy, rot) in enumerate(((-6, -34, -7), (4, -26, 5), (-2, -18, -3), (5, -10, 3))):   # the cards behind
        cx_, cy_ = x + w/2 + dx, y + h/2 + dy
        d = rrect(x + dx, y + dy, w, h, 4)
        g.append(f'<g transform="rotate({rot} {cx_} {cy_ + 40})"><g {WASH}><path d="{d}" fill="{["#f7efdc","#fbf6ea","#f3ead6","#faf3e4"][i]}"/></g><g {WOB}><path d="{d}" {LN}/></g></g>')
    front = rrect(x, y, w, h, 4)
    g.append(f'<path d="{front}" fill="{INK}" opacity=".12" transform="translate(2 4)" filter="url(#tls-edge)"/>')
    g.append(f'<path d="M{x+w/2-20} {y+h} L{x+w/2-14} {y+h-9} L{x+w/2-6} {y+h-9} L{x+w/2} {y+h} M{x+w/2} {y+h} L{x+w/2+6} {y+h-9} L{x+w/2+14} {y+h-9} L{x+w/2+20} {y+h}" fill="#3d3a35"/>')
    for kx in (704, 896):           # knobs
        g.append(f'<circle cx="{kx}" cy="610" r="24" fill="url(#tls-knob)"/><circle cx="{kx-6}" cy="603" r="6" fill="#fff" opacity=".22"/><circle cx="{kx}" cy="610" r="7" fill="url(#tls-metal)"/>')
        g.append(f'<g {WOB}><circle cx="{kx}" cy="610" r="24" {LN}/><circle cx="{kx}" cy="610" r="7" {LNS}/></g>')
    return "".join(g)


BARK, BARK_D, BARK_L = "#6e4b2e", "#4a3120", "#94693f"
ENDG, RING = "#e6c08a", "#a97543"
def stick(x0, y0, x1, y1, w=9, seed=1):
    """A hand-cut stick: bark-brown, a little crooked, a pale cut at each end and a knot or two."""
    import random
    rnd = random.Random(seed)
    mx, my = (x0 + x1) / 2 + rnd.uniform(-3, 3), (y0 + y1) / 2 + rnd.uniform(-3, 3)
    d = f"M{x0:.1f} {y0:.1f} Q{mx:.1f} {my:.1f} {x1:.1f} {y1:.1f}"
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    g = [f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w+2.6:.1f}" stroke-linecap="round" filter="url(#tls-wobble)"/>',
         f'<path d="{d}" fill="none" stroke="{BARK}" stroke-width="{w:.1f}" stroke-linecap="round"/>',
         f'<path d="{d}" fill="none" stroke="{BARK_L}" stroke-width="{w*.3:.1f}" stroke-linecap="round" opacity=".8" transform="translate({nx*w*.22:.1f} {ny*w*.22:.1f})"/>']
    for k in range(int(L // 70) + 1):                     # knots
        t = rnd.uniform(.2, .8); kx, ky = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        g.append(f'<ellipse cx="{kx:.1f}" cy="{ky:.1f}" rx="{w*.32:.1f}" ry="{w*.22:.1f}" fill="{BARK_D}" opacity=".8"/>')
    for ex, ey in ((x0, y0), (x1, y1)):                  # the cut ends
        g.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{w*.42:.1f}" fill="{ENDG}" stroke="{INK}" stroke-width="1"/>')
    return "".join(g)

def stick_frame(x, y, w, h, t=10, seed=3):
    """Four sticks lashed at the corners with twine, overhanging a little."""
    o = 12
    g = [stick(x - o, y, x + w + o, y + 1, t, seed), stick(x - o + 2, y + h, x + w + o - 1, y + h - 1, t, seed + 1),
         stick(x, y - o, x + 1, y + h + o, t, seed + 2), stick(x + w, y - o + 1, x + w - 1, y + h + o, t, seed + 3)]
    for cx_, cy_ in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
        g.append(f'<path d="M{cx_-7} {cy_-5} L{cx_+7} {cy_+5} M{cx_-7} {cy_+5} L{cx_+7} {cy_-5} M{cx_-8} {cy_} L{cx_+8} {cy_}" stroke="#d9c58f" stroke-width="2.2" stroke-linecap="round"/>'
                 f'<path d="M{cx_-7} {cy_-5} L{cx_+7} {cy_+5} M{cx_-7} {cy_+5} L{cx_+7} {cy_-5}" stroke="{INK}" stroke-width=".6" opacity=".5"/>')
    return "".join(g)

def end_grain(cx, cy, rx, ry):
    """The sawn end of a log: pale wood with growth rings and a bark rim."""
    g = [f'<ellipse cx="{cx}" cy="{cy}" rx="{rx+3}" ry="{ry+3}" fill="{BARK_D}"/>', f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{ENDG}"/>']
    for k in (.78, .56, .34, .14):
        g.append(f'<ellipse cx="{cx+rx*.05:.1f}" cy="{cy-ry*.04:.1f}" rx="{rx*k:.1f}" ry="{ry*k:.1f}" fill="none" stroke="{RING}" stroke-width="1" opacity=".75"/>')
    g.append(f'<path d="M{cx} {cy} L{cx+rx*.7:.1f} {cy-ry*.1:.1f}" stroke="{RING}" stroke-width=".8" opacity=".6"/>')
    g.append(f'<path d="M{cx} {cy} L{cx-rx*.5:.1f} {cy+ry*.55:.1f} M{cx} {cy} L{cx+rx*.1:.1f} {cy-ry*.8:.1f}" stroke="#5a3a1c" stroke-width="1.1" opacity=".7"/>')
    g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#5a3a1c" opacity=".14"/>')
    g.append(f'<g {WOB}><ellipse cx="{cx}" cy="{cy}" rx="{rx+3}" ry="{ry+3}" {LN}/></g>')
    return "".join(g)

def log_leg(x0, x1, y0, y1, seed=1):
    """A round log leg with its bark on."""
    import random
    rnd = random.Random(seed)
    d = f"M{x0} {y0} L{x1} {y0} L{x1-2} {y1} L{x0+2} {y1} Z"
    g = [f'<g {WASH}><path d="{d}" fill="{BARK}"/></g>',
         f'<path d="M{x0+6} {y0} L{x0+8} {y1}" stroke="{BARK_L}" stroke-width="{(x1-x0)*.18:.1f}" opacity=".7"/>',
         f'<path d="M{x1-6} {y0} L{x1-7} {y1}" stroke="{BARK_D}" stroke-width="{(x1-x0)*.22:.1f}" opacity=".8"/>']
    for k in range(9):                                     # bark furrows
        bx = rnd.uniform(x0 + 5, x1 - 5); by0 = rnd.uniform(y0, y1 - 60)
        g.append(f'<path d="M{bx:.0f} {by0:.0f} q{rnd.uniform(-3,3):.1f} 25 {rnd.uniform(-2,2):.1f} {rnd.uniform(40,90):.0f}" stroke="{BARK_D}" stroke-width="1.6" fill="none" opacity=".75"/>')
    ky = rnd.uniform(y0 + 40, y1 - 40)
    g.append(f'<ellipse cx="{(x0+x1)/2:.0f}" cy="{ky:.0f}" rx="5" ry="7" fill="{BARK_D}"/><ellipse cx="{(x0+x1)/2:.0f}" cy="{ky:.0f}" rx="2.4" ry="3.5" fill="{ENDG}" opacity=".7"/>')
    g.append(grime(d, (x0, y0, x1 - x0, y1 - y0), seed + 40, 7, "#2e2414", 30))
    g.append(f'<path d="M{x0+3} {y1-70} L{x1-3} {y1-70}" stroke="#8c9a6a" stroke-width="26" opacity=".18" filter="url(#tls-soft)"/>')   # a little green weather at the foot
    g.append(f'<g {WOB}><path d="M{x0} {y0} L{x0+2} {y1} M{x1} {y0} L{x1-2} {y1}" {LN}/></g>')
    return "".join(g)

def front_log(x0, x1, y0, y1):
    """A whole log laid along the front of the table top, its sawn ends showing."""
    r = (y1 - y0) / 2; cy = (y0 + y1) / 2
    body = f"M{x0} {y0} L{x1} {y0} L{x1} {y1} L{x0} {y1} Z"
    g = [f'<g {WASH}><path d="{body}" fill="{BARK}"/></g>',
         f'<path d="M{x0} {y0+r*.45:.1f} L{x1} {y0+r*.45:.1f}" stroke="{BARK_L}" stroke-width="{r*.35:.1f}" opacity=".55"/>',
         f'<path d="M{x0} {y1-r*.3:.1f} L{x1} {y1-r*.3:.1f}" stroke="{BARK_D}" stroke-width="{r*.45:.1f}" opacity=".6"/>']
    import random
    rnd = random.Random(int(x1 + y0))
    for k in range(int((x1 - x0) / 26)):
        bx = rnd.uniform(x0 + 20, x1 - 40); by_ = rnd.uniform(y0 + 4, y1 - 6)
        g.append(f'<path d="M{bx:.0f} {by_:.0f} q12 {rnd.uniform(-2,2):.1f} {rnd.uniform(24,50):.0f} {rnd.uniform(-1.5,1.5):.1f}" stroke="{BARK_D}" stroke-width="1.5" fill="none" opacity=".7"/>')
    g.append(grime(body, (x0, y0, x1 - x0, y1 - y0), int(x1 + y1), 12, "#2e2414", 50))
    g.append(f'<g {WOB}><path d="M{x0} {y0} L{x1} {y0} M{x0} {y1} L{x1} {y1}" {LN}/></g>')
    g.append(end_grain(x0, cy, r * .55, r))
    g.append(end_grain(x1, cy, r * .55, r))
    return "".join(g)

LEAF_D = "M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"
def leaf(cx, cy, rot=0, sc=2, color="#9fbf86", squash=1):
    """A Treeline leaf, lying flat (squash < 1 tips it onto the surface)."""
    return (f'<g transform="translate({cx} {cy}) scale(1 {squash}) rotate({rot}) scale({sc})">'
            f'<path d="{LEAF_D}" fill="{INK}" opacity=".16" transform="translate(1.2 1.6)"/>'
            f'<g {WASH}><path d="{LEAF_D}" fill="{color}"/></g>'
            f'<path d="M0 -8 L0 9" stroke="{INK}" stroke-width=".55" opacity=".7"/>'
            f'<path d="M0 -2 L3 -5 M0 2 L-3 -1 M0 5 L2.6 2.5" stroke="{INK}" stroke-width=".4" opacity=".5"/>'
            f'<path d="{LEAF_D}" fill="none" stroke="{INK}" stroke-width=".7"/></g>')
LEAF_COLORS = ("#9fbf86", "#7fa56c", "#c9a958", "#b7cf9a")

# ------------------------------------------------------------------ the card file, angled, like a real Rolodex
CF_W, CF_H = 260, 230                       # local drawing; its base sits on the surface at y = CF_H
CF_CARD = (78, 4, 196, 13, 76, 76)          # the front card's top-left, top-right and bottom-left corners (as seen)
CF_MIRROR = f"translate({CF_W} 0) scale(-1 1)"
def cf_card_matrix():
    x, y, w, h = CARD
    tlx, tly, trx, try_, blx, bly = CF_CARD
    a, b = (trx - tlx) / w, (try_ - tly) / w
    c, d = (blx - tlx) / h, (bly - tly) / h
    return f"translate({tlx} {tly}) matrix({a:.4f} {b:.4f} {c:.4f} {d:.4f} 0 0) translate({-x} {-y})"

_TAN, _TAN_D, _TAN_L = "#b9a273", "#8f7a50", "#d7c597"
_DRUM = "M34 150 C22 128 22 86 46 62 C60 52 80 50 98 52 L176 58 C196 62 206 80 204 104 C204 124 198 140 190 150 Z"
# the near part of the drum, below where the cards go in: drawn again over the front card so it sits down inside
_DRUM_FRONT = "M30 86 C70 84 150 78 205 72 C206 88 205 100 204 104 C204 124 198 140 190 150 L34 150 C24 132 23 106 30 86 Z"

def _cf_front():
    """The front of the card file (in its unmirrored drawing): the near half of the drum with its card edges and
    index tabs, the case front and side, and the knobs."""
    front = "M8 150 L174 162 L174 228 L10 214 Z"
    side = "M174 162 L248 136 L248 200 L174 228 Z"
    g = [shape(_DRUM_FRONT, "#ecd7a8", edge="#b08a4a")]
    for k in range(11):                                    # card edges round the near side of the drum
        yy = 92 + k * 5
        g.append(f'<path d="M{30 + 3*k/10:.1f} {yy+2 - k*0.4:.1f} C80 {yy+4} 150 {yy-2} {204 - 2*k/10:.1f} {yy-12 + k*1.1:.1f}" fill="none" stroke="#b9925a" stroke-width=".8" opacity=".75"/>')
    for k, (ty_, col, lab) in enumerate(((98, "#c9a24a", "A"), (110, "#6f8f5a", "F"), (122, "#c9a24a", "M"), (134, "#6f8f5a", "S"))):
        tx = 44 + k * 30
        g.append(f'<path d="M{tx} {ty_} L{tx+18} {ty_-1} L{tx+18} {ty_+7} L{tx} {ty_+8} Z" fill="{col}" stroke="{INK}" stroke-width=".8"/>'
                 f'<g transform="translate({2*tx+18} 0) scale(-1 1)"><text x="{tx+9}" y="{ty_+6}" text-anchor="middle" {SANS} font-size="6" font-weight="800" fill="#fff">{lab}</text></g>')
    g += [shape(front, _TAN, edge=_TAN_D), shape(side, _TAN_D, edge="#000"),
          f'<path d="M12 156 L172 167" stroke="{_TAN_L}" stroke-width="3" opacity=".8"/>',
          f'<path d="M30 196 L150 205" stroke="{_TAN_D}" stroke-width="1" opacity=".6"/>',
          f'<g opacity=".22" filter="url(#tls-grain)"><path d="{front} {side}" fill="#000"/></g>',
          f'<path d="M20 172 l26 2 M60 190 l40 3 M190 180 l30 -10" stroke="#e8dbb4" stroke-width="1.2" opacity=".6"/>',
          f'<path d="M14 210 L172 222 M176 224 L246 198" stroke="#3b2a12" stroke-width="5" opacity=".18"/>']   # grime along the bottom
    for kcx, kcy, rx, ry in ((214, 106, 20, 30), (30, 104, 9, 18)):
        g.append(f'<ellipse cx="{kcx+3}" cy="{kcy+3}" rx="{rx}" ry="{ry}" fill="{INK}" opacity=".35"/>')
        g.append(f'<ellipse cx="{kcx}" cy="{kcy}" rx="{rx}" ry="{ry}" fill="url(#tls-knob)"/>')
        g.append(f'<g {WOB}><ellipse cx="{kcx}" cy="{kcy}" rx="{rx}" ry="{ry}" {LN}/></g>')
    for k in range(10):
        a = k / 10 * math.tau
        g.append(f'<path d="M{214 + 13*math.cos(a):.1f} {106 + 20*math.sin(a):.1f} L{214 + 19*math.cos(a):.1f} {106 + 28.5*math.sin(a):.1f}" stroke="#6b6258" stroke-width="1.6"/>')
    g.append('<ellipse cx="214" cy="106" rx="10" ry="15" fill="#2c2722" stroke="#6b6258" stroke-width="1"/><ellipse cx="211" cy="100" rx="3.5" ry="5" fill="#fff" opacity=".2"/>')
    return "".join(g)

def cf_front():
    """The front of the card file as seen (mirrored), for the words layer: drawn over the front card."""
    return f'<g transform="{CF_MIRROR}">{_cf_front()}</g>'

def card_file():
    """A rotary card file like the classic desk ones, turned toward the phone: a tan metal case, a drum of tabbed
    cards on a rod, black knobs, and the front card standing up in it. That card's paper and words, and the near
    half of the drum over its foot, are in the words layer."""
    rim = "M8 150 L84 126 L248 136 L174 162 Z"
    upright = "M196 154 L246 136 L246 58 L232 46 L212 64 Z"
    g = [f'<ellipse cx="132" cy="{CF_H-2}" rx="136" ry="11" fill="{INK}" opacity=".26" filter="url(#tls-soft)"/>',
         f'<path d="{rim}" fill="#3a3024"/>', shape(upright, _TAN_D),
         f'<g opacity=".2" filter="url(#tls-grain)"><path d="{upright}" fill="#000"/></g>',
         shape(_DRUM, "#ecd7a8", edge="#b08a4a")]
    for k in range(5):                                     # the tops of the cards across the drum
        yy = 58 + k * 6
        g.append(f'<path d="M{44 - k*3} {yy+4} C80 {yy} 150 {yy+2} {196 + k*1.5} {yy+6}" fill="none" stroke="#b9925a" stroke-width=".8" opacity=".75"/>')
    # two cards standing up behind the front one (in the unmirrored drawing: the front card is at 64..182)
    for dx_, dy_, col in ((-12, -7, "#efe2c5"), (-6, -3, "#f5ecd8")):
        d = f"M{64+dx_} {13+dy_} L{182+dx_} {4+dy_} L{184+dx_} {80+dy_} L{66+dx_} {90+dy_} Z"
        g.append(f'<g {WASH}><path d="{d}" fill="{col}"/></g><g {WOB}><path d="{d}" {LNS}/></g>')
    g.append(_cf_front())
    return f'<g transform="{CF_MIRROR}">{"".join(g)}</g>'

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
             f'<path d="{card}" fill="{INK}" opacity=".14" transform="translate(5 2)" filter="url(#tls-edge)"/>' + shape(card, "#f2e8d2") + aged(card, (wx, wy, ww, wh), 25)
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
    back = [log_leg(x0+86, x0+116, cb, H + 10, 7), log_leg(x1-116, x1-86, cb, H + 10, 8), shape(STOP, "url(#tls-top)"),
            f'<g {WOB}><path d="M{x0+68} {sy+6} C{x0+230} {sy+4} {x1-230} {sy+4} {x1-68} {sy+6}" {LNS}/></g>']
    for f in (.35, .7):                                   # the shelf is a split slab: two seams
        a_, b_ = x0 + 60 - 34 * f, x1 - 60 + 34 * f
        back.append(f'<path d="M{a_:.0f} {sy+26*f:.1f} L{b_:.0f} {sy+26*f:.1f}" stroke="{WOOD_S}" stroke-width="1.6" opacity=".6"/>')
    sfront = [front_log(x0 + 26, x1 - 26, sy + 26, sy + 58), f'<g opacity=".14" filter="url(#tls-grain)"><path d="{STOP}" fill="#000"/></g>']
    # the carcass: split boards standing side by side
    li = t.get("leg_in", 28)
    front = [log_leg(x0+li, x0+li+50, cb - 4, H + 10, 3), log_leg(x1-li-50, x1-li, cb - 4, H + 10, 4),
             shape(CARC, "url(#tls-front)", edge=WOOD_S)]
    bx = x0 + 32
    import random
    rnd = random.Random(int(x0 + ty))
    while bx < x1 - 60:
        bw = rnd.uniform(60, 90); bx += bw
        if bx < x1 - 40:
            front.append(f'<g {WOB}><path d="M{bx:.0f} {F+56} L{bx+rnd.uniform(-2,2):.0f} {cb}" stroke="{WOOD_S}" stroke-width="2" opacity=".7"/></g>'
                         f'<path d="M{bx+2:.0f} {F+56} L{bx+2:.0f} {cb}" stroke="#f1d0a0" stroke-width="1" opacity=".5"/>')
    front.append(shape(DRAWER, WOOD_M, edge=WOOD_S, extra=f'<path d="M{dx+14} {dy+10} L{dx+dw-14} {dy+10}" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>'))
    for k in (1, 2):                                       # the drawer front is two planks
        yy = dy + dh * k / 3
        front.append(f'<path d="M{dx+6} {yy:.0f} L{dx+dw-6} {yy:.0f}" stroke="{WOOD_S}" stroke-width="1.4" opacity=".55"/>')
    kx, ky = t["knob"]                                     # a wooden peg for a knob
    front += [f'<ellipse cx="{kx+2}" cy="{ky+4}" rx="11" ry="8" fill="{WOOD_S}" opacity=".45"/>', end_grain(kx, ky, 8, 8),
              front_log(x0 - 4, x1 + 4, F + 4, F + 56),
              shape(TOP, "url(#tls-top)", extra=f'<path d="M{x0+inset+10} {ty+8} L{x1-inset-10} {ty+8}" stroke="#fff" stroke-opacity=".25" stroke-width="3"/>')]
    for f in (.3, .58, .82):                               # the top is split planks: dark seams with a pale lip
        y = ty + 114 * f; a_ = x0 + inset * (1 - f); b_ = x1 - inset * (1 - f)
        front.append(f'<g {WOB}><path d="M{a_:.0f} {y:.0f} L{b_:.0f} {y:.0f}" stroke="{WOOD_S}" stroke-width="2.4" opacity=".75"/></g>'
                     f'<path d="M{a_+2:.0f} {y+2:.0f} L{b_-2:.0f} {y+2:.0f}" stroke="#f3d6a8" stroke-width="1.2" opacity=".55"/>')
    for f in (.14, .44, .7, .93):     # wood grain along the planks
        y = ty + 114 * f; a_ = x0 + inset * (1 - f); b_ = x1 - inset * (1 - f)
        front.append(f'<g {WOB}><path d="M{a_:.0f} {y:.0f} C{a_+150:.0f} {y-3:.0f} {a_+260:.0f} {y+3:.0f} {(a_+b_)/2:.0f} {y:.0f} S{b_-120:.0f} {y-3:.0f} {b_:.0f} {y+1:.0f}" fill="none" stroke="{WOOD_D}" stroke-width="1" opacity=".35"/></g>')
    front.append(f'<g opacity=".22" filter="url(#tls-grain)"><path d="{TOP} {CARC}" fill="#000"/></g>')
    front.append(grime(TOP, (x0, ty, x1 - x0, 114), int(ty) + 1, 16, "#4a3216", 70))
    front.append(grime(CARC, (x0 + 32, F + 54, x1 - x0 - 64, cb - F - 54), int(ty) + 2, 10, "#3d2810", 50))
    front.append(grime(DRAWER, (dx, dy, dw, dh), int(ty) + 3, 6, "#3d2810", 20))
    front.append(wear(t, TOP, F, cb, cx))
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
    "coffee": (688, 80, 268, 166), "card": (688, 246, 236, 142), "cardfile": (684, 470, 232, 204),
    "book": (-14, -186, 186, 196), "warranty": (-10, -155, 150, 160),
}
def placed(content, pl):
    ox, oy, nx, ny, s = pl
    return f'<g transform="translate({nx} {ny}) scale({s}) translate({-ox} {-oy})">{content}</g>'
def moved(box, pl):
    ox, oy, nx, ny, s = pl; bx, by, bw, bh = box
    return (round(nx + (bx - ox) * s, 1), round(ny + (by - oy) * s, 1), round(bw * s, 1), round(bh * s, 1))

# ---------------------------------------------------------------- the guide book, spine out
BOOK_W, BOOK_T = 200, 46          # length of the spine, thickness of the book
def book_t(w): return BOOK_T * (w / BOOK_W) ** .5
def book_depth(w): return 60 * (w / BOOK_W) ** .6
def book_spine(x0, by, w=BOOK_W, t=None, depth=None):
    t = book_t(w) if t is None else t
    depth = book_depth(w) if depth is None else depth
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
         f'<g clip-path="url(#tls-bookface{int(x0)}{int(by)})"><g transform="translate({x0} {top+depth}) scale({w/356:.4f} {depth/300:.4f}) rotate(-90)">'
         f'<image href="{COVER_IMAGE}" width="300" height="356" preserveAspectRatio="none"/></g></g>',
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

# ---------------------------------------------------------------- the clock radio
# A late-80s/90s digital clock radio: dark plastic, a woodgrain grille on top, a row of little buttons and the
# alarm slide switch, a long snooze bar, red seven-segment digits behind smoked glass, and the AM/FM scale.
# Local drawing: 200 x 80, the bottom edge on the surface. The digits and the line light are in the words layer.
CLOCK_W, CLOCK_H = 200, 80
SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
CELLS = (("h1", 30), ("h2", 52), ("m1", 82), ("m2", 104))    # x of each digit in the window
def seg_paths(x, y, w=18, h=26, t=3.2):
    """The seven segments of one digit, as polygons (a top, b top-right, c bottom-right, d bottom, e bottom-left, f top-left, g middle)."""
    def hz(yy):
        return f"{x+1:.1f},{yy+t/2:.1f} {x+1+t/2:.1f},{yy:.1f} {x+w-1-t/2:.1f},{yy:.1f} {x+w-1:.1f},{yy+t/2:.1f} {x+w-1-t/2:.1f},{yy+t:.1f} {x+1+t/2:.1f},{yy+t:.1f}"
    def vt(xx, y0, y1):
        return f"{xx+t/2:.1f},{y0:.1f} {xx+t:.1f},{y0+t/2:.1f} {xx+t:.1f},{y1-t/2:.1f} {xx+t/2:.1f},{y1:.1f} {xx:.1f},{y1-t/2:.1f} {xx:.1f},{y0+t/2:.1f}"
    m = y + h / 2
    return {"a": hz(y), "g": hz(m - t / 2), "d": hz(y + h - t), "f": vt(x, y + 1, m - .6), "b": vt(x + w - t, y + 1, m - .6),
            "e": vt(x, m + .6, y + h - 1), "c": vt(x + w - t, m + .6, y + h - 1)}

def clock_radio():
    """The clock radio's body, at 0,0 (200 x 80)."""
    W_, H_ = CLOCK_W, CLOCK_H
    top = "M10 2 L190 2 C195 2 198 4 198 8 L200 22 L0 22 L2 8 C2 4 5 2 10 2 Z"
    slope = "M0 22 L200 22 L200 34 L0 34 Z"
    front = "M0 34 L200 34 L200 74 C200 78 197 80 192 80 L8 80 C3 80 0 78 0 74 Z"
    g = [f'<ellipse cx="100" cy="80" rx="108" ry="6" fill="{INK}" opacity=".25" filter="url(#tls-edge)"/>',
         f'<path d="{front}" fill="#2a221d"/><path d="{slope}" fill="#3a302a"/><path d="{top}" fill="#3b2f28"/>',
         # the woodgrain grille on top
         f'<path d="M12 5 L132 5 L134 19 L8 19 Z" fill="#7a4326"/>']
    for i in range(7):
        yy = 6.5 + i * 1.9
        g.append(f'<path d="M{11 - i*.35:.1f} {yy:.1f} L{132 + i*.3:.1f} {yy:.1f}" stroke="#2a1a10" stroke-width=".9" opacity=".85"/>')
    g += [f'<path d="M14 7 C50 6 90 8 128 7" stroke="#a5653d" stroke-width=".6" fill="none" opacity=".6"/>',
          # the snooze bar
          f'<path d="M144 9 C144 7 146 6 149 6 L188 6 C191 6 193 7 193 9 L194 14 C194 16 192 17 189 17 L148 17 C145 17 143 16 143 14 Z" fill="#171310"/>',
          f'<path d="M147 8 L189 8" stroke="#fff" stroke-opacity=".25" stroke-width="1.2" stroke-linecap="round"/>',
          f'<text x="168" y="31" text-anchor="middle" {SANS} font-size="3.6" letter-spacing=".6" fill="#b9ab98" transform="rotate(180 168 30)">SNOOZE</text>',
          f'<path d="M0 33.6 L200 33.6" stroke="#9a3a2a" stroke-width=".7" opacity=".9"/>']
    for i, lab in enumerate(("SLEEP", "WAKE", "HOUR", "MINUTE")):              # the little buttons
        bx = 10 + i * 16
        g.append(f'<path d="M{bx} 24 L{bx+10} 24 L{bx+11} 28 L{bx-1} 28 Z" fill="#1c1714"/><path d="M{bx} 24 L{bx+10} 24" stroke="#fff" stroke-opacity=".22" stroke-width=".6"/>')
        g.append(f'<text x="{bx+5}" y="32" text-anchor="middle" {SANS} font-size="2.6" fill="#b9ab98">{lab}</text>')
    g += [f'<rect x="78" y="24.5" width="16" height="4" rx="1" fill="#14100d"/><rect x="80" y="23.6" width="5" height="5.6" rx="1" fill="#5b4f47"/>',
          f'<text x="98" y="27" {SANS} font-size="2.4" fill="#b9ab98">ON · OFF · MUSIC · ALARM</text>',
          f'<text x="10" y="44" {SANS} font-size="3.4" font-weight="700" letter-spacing=".3" fill="#b9ab98" opacity="0"></text>',
          # the smoked display window
          f'<rect x="7" y="38" width="122" height="36" rx="3" fill="#0c0807"/>',
          f'<rect x="7" y="38" width="122" height="36" rx="3" fill="none" stroke="#5b4f47" stroke-width=".8"/>',
          f'<path d="M10 40 L60 40" stroke="#fff" stroke-opacity=".08" stroke-width="2" stroke-linecap="round"/>',
          f'<text x="12" y="49.5" {SANS} font-size="4" fill="#b9ab98">AM</text><text x="12" y="67" {SANS} font-size="4" fill="#b9ab98">PM</text>',
          f'<text x="68" y="78" text-anchor="middle" {SANS} font-size="2.6" letter-spacing=".5" fill="#8d8173">DIGITAL CLOCK RADIO</text>',
          # the tuning scale
          f'<rect x="134" y="38" width="60" height="36" rx="2" fill="#120e0c"/>',
          f'<rect x="136" y="56" width="56" height="3" fill="#b0372f" opacity=".45"/>',
          f'<text x="137" y="53" {SANS} font-size="4.2" fill="#d8ccbb">FM 88 92 96 100 108</text>',
          f'<text x="137" y="68" {SANS} font-size="4.2" fill="#d8ccbb">AM 55 65 80 100 160</text>',
          f'<path d="M168 55 L168 60" stroke="#ff5a3c" stroke-width="1.2"/>',
          f'<g {WOB}><path d="{front} {top}" fill="none" stroke="{INK}" stroke-width="1.6"/></g>',
          f'<g opacity=".16" filter="url(#tls-grain)"><path d="{front} {top} {slope}" fill="#fff"/></g>',
          grime(top + " " + slope, (0, 2, 200, 32), 61, 5, "#d9c9a8", 40)]
    return "".join(g)

def clock_words():
    """The clock's live parts: the seven-segment digits, the colon, AM/PM and the line light. At 0,0 like the body."""
    g = ['<g class="tl-desk__clock" data-time="">', '<g class="tl-clk__digits">']
    for cell, x in CELLS:
        for k, pts in seg_paths(x, 42).items():
            g.append(f'<polygon class="tl-clk__seg" data-seg="{cell}{k}" points="{pts}"/>')
    g.append('<rect class="tl-clk__seg is-on" x="75.6" y="49" width="3.2" height="3.2"/><rect class="tl-clk__seg is-on" x="75.6" y="58" width="3.2" height="3.2"/>')
    g.append('<circle class="tl-clk__seg tl-clk__am" cx="23" cy="48" r="1.6"/><circle class="tl-clk__seg tl-clk__pm" cx="23" cy="65.6" r="1.6"/>')
    g.append('</g></g>')
    return "".join(g)

def book_box(x0, by, w=BOOK_W):
    """The spine is the book's link (a clock may sit on its cover)."""
    t = book_t(w)
    return (x0 - 8, by - t - 10, w + 16, t + 18)

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
    # Landscape tablets and desktops, zoomed in on the table top. The card file at the back left, the phone in
    # the middle, the guide book on the right with the clock radio sitting on it. No shelf.
    "wide": {"W": 1240, "H": 890,
        "table": {"x0": 20, "x1": 1220, "ty": 590, "inset": 80, "ch": 120, "sy": 2000, "H": 890,
                  "drawer": (406, 768, 428, 100), "knob": (444, 818)},
        "phone": {"x": 262, "y": 2, "w": 560},
        "sticker": (580, 820, .78, .78, -3),
        "bookspine": (806, 704, 384), "peek": (738, 768),
        "clock": (812, 0, 384),
        "cardfile": (4, 668, 1.0),
        "leaves": [(236, 706, 28, 1.7, 0), (760, 706, -60, 1.5, 2), (910, 404, 160, 1.6, 1)],
        "place": {"sticky": (72, 150, 34, 30, 1), "sketch": (92, 360, 40, 236, .9), "cork": (676, 64, 930, 40, 1)},
        "shelf": [], "table_items": ["cardfile"], "sketch": True},
    # Tablets held upright: the side table with the clock radio beside the phone; the card file and the
    # guide book on the shelf.
    "portrait": {"W": 1000, "H": 1420,
        "table": {"x0": 60, "x1": 940, "ty": 800, "inset": 78, "ch": 120, "sy": 1338, "H": 1420,
                  "drawer": (286, 978, 428, 100), "knob": (324, 1028)},
        "phone": {"x": 96, "y": 140, "w": 620},
        "sticker": (466, 1030, .78, .78, -3),
        "bookspine": (712, 906, 214), "peek": (624, 978),
        "clock": (352, 1356, 440),
        "cardfile": (84, 1356, .9),
        "leaves": [(96, 892, 30, 1.7, 0), (690, 912, -40, 1.4, 2), (880, 1362, 70, 1.5, 3)],
        "place": {"sticky": (72, 150, 20, 60, 1), "sketch": (92, 360, 30, 286, .9), "cork": (676, 64, 788, 180, .72),
                  "plant": (0, 0, 170, 569, .8)},
        "shelf": [], "table_items": [], "sketch": True},
    # Phones: a narrow nightstand, the phone across nearly the whole width, the wall things above it; on the
    # shelf, the card file, and the guide book with the clock radio sitting on it.
    "tall": {"W": 600, "H": 1412,
        "table": {"x0": 8, "x1": 592, "ty": 812, "inset": 50, "ch": 138, "sy": 1334, "H": 1412, "leg_in": 4,
                  "drawer": (70, 990, 460, 118), "knob": (108, 1049)},
        "phone": {"x": 28, "y": 245, "w": 544},
        "sticker": (290, 1050, .85, .85, -3),
        "bookspine": (62, 1356, 150), "peek": (452, 990),
        "clock": (206, 1356, 330),
        "cardfile": (66, 1276, .54), "cf_on": "shelf-top",
        "leaves": [(54, 884, 30, 1.5, 0), (548, 888, -50, 1.4, 2), (548, 1362, 80, 1.3, 1)],
        "place": {"sticky": (72, 150, 12, 28, .96), "sketch": (92, 360, 14, 214, .85), "cork": (676, 64, 350, 12, .82)},
        "shelf": [], "table_items": [], "sketch": True},
}

def cf_place(L):
    x, by, sc = L["cardfile"]
    return f"translate({x} {by - CF_H * sc:.1f}) scale({sc})"
def cf_on_shelf(L): return L.get("cf_on", "shelf" if L["cardfile"][1] > L["table"]["sy"] else "table") == "shelf"
def cf_box(L):
    x, by, sc = L["cardfile"]
    return (x, by - CF_H * sc, CF_W * sc, CF_H * sc)
def leaves_for(L):
    return "".join(leaf(x, y, r, sc, LEAF_COLORS[c], .55) for x, y, r, sc, c in L["leaves"])

def clock_bottom(L):
    cx, by, w = L["clock"]
    if by: return by
    bx, bb, bw = L["bookspine"]
    return bb - book_t(bw) - book_depth(bw) * .2
def clock_place(L):
    cx, _, w = L["clock"]; by = clock_bottom(L); sc = w / CLOCK_W
    return f'translate({cx} {by - CLOCK_H * sc:.1f}) scale({sc:.4f})'
def clock_on_shelf(L): return clock_bottom(L) > L["table"]["sy"] - 40
def clock_at(L): return f'<g transform="{clock_place(L)}">{clock_radio()}</g>'

def scene(name):
    L = LAYOUTS[name]; W_, H_ = L["W"], L["H"]; pl = L["place"]
    back, sfront, front = table(L["table"])
    draw = {"spines": spines, "plant": plant}
    item = lambda k: placed(draw[k](), pl[k])
    bx, by, bw = L["bookspine"]; px, py = L["peek"]; dx, dy, dw, dh = L["table"]["drawer"]
    book_here = book_spine(bx, by, bw)
    book_shelf = by > L["table"]["sy"]
    cf = f'<g transform="{cf_place(L)}">{card_file()}</g>'
    clock = clock_at(L)
    on_book = L.get("cf_on") == "shelf-top"
    shelf = ("".join(item(k) for k in L["shelf"]) + (cf if cf_on_shelf(L) else "") + (book_here if book_shelf else "")
             + (cf if on_book else "") + (clock if clock_on_shelf(L) else "") + "".join(leaf(x, y, r, sc, LEAF_COLORS[c], .55) for x, y, r, sc, c in L["leaves"] if y > L["table"]["sy"]))
    tabletop = ((cf if not cf_on_shelf(L) and not on_book else "") + (book_here if not book_shelf else "") + (clock if not clock_on_shelf(L) else "")
                + "".join(leaf(x, y, r, sc, LEAF_COLORS[c], .55) for x, y, r, sc, c in L["leaves"] if L["table"]["ty"] < y < L["table"]["sy"]))
    wall_leaves = "".join(leaf(x, y, r, sc, LEAF_COLORS[c], 1) for x, y, r, sc, c in L["leaves"] if y < L["table"]["ty"])
    body = (wall(W_, H_) + placed(sticky_note(), pl["sticky"]) + (placed(kid_drawing(), pl["sketch"]) if L["sketch"] else "")
            + placed(corkboard(), pl["cork"]) + wall_leaves + back + shelf + sfront + front
            + drawer_peek(px, py, dx, dx + dw, "") + sticker(*L["sticker"]) + tabletop)
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
            + placed(nmg, pl["sketch"]) + placed(q, pl["sticky"]) + f'<g transform="{cf_place(L)} {cf_card_matrix()}">{c}</g><g transform="{cf_place(L)}">{cf_front()}</g>'
            + f'<g transform="{clock_place(L)}">{clock_words()}</g>' + '</svg>')

def words_template(name):
    return words(name, nm="{{NAME}}", quiet="{{QUIET}}", contact=("{{CNAME}}", "{{CNUM}}"), count="{{CCOUNT}}", size="{{NAMESIZE}}")

def geometry(name):
    L = LAYOUTS[name]; pl = L["place"]
    bx, by, bw = L["bookspine"]; px, py = L["peek"]
    hot = {"guide": book_box(bx, by, bw), "licenses": peek_box(px, py),
           "coffee": moved(BOX["coffee"], pl["cork"]), "card": moved(BOX["card"], pl["cork"]), "cardfile": cf_box(L)}
    return {"w": L["W"], "h": L["H"], "phone": L["phone"], "hotspots": hot}

GEOM = {n: geometry(n) for n in LAYOUTS}

if __name__ == "__main__":
    out = "/home/claude/treeline/build/phone/out"
    for n in LAYOUTS:
        open(f"{out}/desk-{n}.svg", "w").write(scene(n))
        open(f"{out}/desk-{n}-words.svg", "w").write(words(n))
    json.dump(GEOM, open(f"{out}/desk-geometry.json", "w"), indent=1)
    print(json.dumps(GEOM))
