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
    g = [f'<rect x="0" y="0" width="{w}" height="{h}" fill="url(#tls-wall)"/>']
    for x in range(18, w, 44):          # 90s pinstripe wallpaper, a sage stripe and a fine rule
        g.append(f'<rect x="{x}" y="0" width="14" height="{h}" fill="{STRIPE}" opacity=".7"/>')
        g.append(f'<path d="M{x+29} 0 L{x+29} {h}" stroke="{WALL_D}" stroke-width="1.2" opacity=".8"/>')
    g.append(f'<g opacity=".12" filter="url(#tls-grain)"><rect x="0" y="0" width="{w}" height="{h}" fill="#000"/></g>')
    g.append(f'<ellipse cx="{w/2}" cy="{h*.36:.0f}" rx="{w*.43:.0f}" ry="{h*.25:.0f}" fill="#fff6dd" opacity=".45" filter="url(#tls-soft)"/>')
    return "".join(g)

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

def framed_sketch():
    """A little framed pencil sketch on the wall: two treehouses with a string between them."""
    x, y, w, h = 92, 360, 170, 128
    outer, inner = rrect(x, y, w, h, 4), rrect(x+14, y+14, w-28, h-28, 2)
    s = [shape(outer, WOOD_M, edge=WOOD_S), f'<path d="{inner}" fill="{PAPER}"/>', f'<g {WOB}><path d="{inner}" {LN}/>']
    bx, by = x+14, y+14
    s.append(f'<path d="M{bx+20} {by+90} L{bx+24} {by+40} M{bx+30} {by+90} L{bx+28} {by+40} M{bx+12} {by+44} Q{bx+26} {by+18} {bx+42} {by+42} Z '
             f'M{bx+112} {by+90} L{bx+116} {by+34} M{bx+122} {by+90} L{bx+120} {by+34} M{bx+104} {by+38} Q{bx+118} {by+10} {bx+134} {by+36} Z" {LNS}/>')
    s.append(f'<path d="M{bx+40} {by+48} Q{bx+71} {by+66} {bx+106} {by+44}" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="3 4" opacity=".7"/>')
    s.append(f'<path d="M{bx+4} {by+92} C{bx+50} {by+88} {bx+90} {by+88} {bx+138} {by+92}" {LNS}/></g>')
    s.append(f'<path d="M{bx+8} {by+40} C{bx+16} {by+20} {bx+40} {by+12} {bx+60} {by+16}" fill="{"#cfe0c4"}" opacity=".0"/>')
    return f'<g transform="rotate(1.5 {x+w/2} {y+h/2})">' + "".join(s) + "</g>"

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

def certificate():
    x, y, w, h = 694, 92, 254, 140
    d = rrect(x, y, w, h, 3)
    g = [f'<g transform="rotate(3 {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, "#fbf4e2"),
         f'<path d="{rrect(x+8, y+8, w-16, h-16, 2)}" fill="none" stroke="{CANOPY}" stroke-width="2.2"/>',
         f'<path d="{rrect(x+13, y+13, w-26, h-26, 2)}" fill="none" stroke="{CANOPY}" stroke-width=".9" stroke-dasharray="1 3"/>']
    for cx_, cy_, rot in ((x+20, y+20, 45), (x+w-20, y+20, 135), (x+w-20, y+h-20, 225), (x+20, y+h-20, 315)):   # leaf corners
        g.append(f'<path transform="translate({cx_} {cy_}) rotate({rot})" d="M0 -7 C5 -3 5 3 0 7 C-5 3 -5 -3 0 -7Z" fill="{CANOPY}" opacity=".8"/>')
    g += [f'<text x="{x+w/2}" y="{y+40}" text-anchor="middle" {SERIF} font-size="19" font-weight="600" letter-spacing="2.5" fill="{INK}">GIFT CERTIFICATE</text>',
          f'<path d="M{x+56} {y+50} L{x+w-56} {y+50}" stroke="{CANOPY}" stroke-width="1"/>',
          f'<text x="{x+w/2}" y="{y+75}" text-anchor="middle" {SERIF} font-size="17" font-style="italic" fill="{INK}">Good for one cup of coffee</text>',
          f'<text x="{x+w/2}" y="{y+94}" text-anchor="middle" {SANS} font-size="11.5" fill="#5e5546">for the person who built Treeline</text>',
          f'<text x="{x+w/2}" y="{y+120}" text-anchor="middle" {SANS} font-size="12.5" font-weight="700" letter-spacing=".5" fill="{CANOPY}">REDEEM AT BUY ME A COFFEE</text>',
                    pin(x+w/2, y+10), '</g>']
    return "".join(g)

LOGO_INNER = None
def business_card():
    x, y, w, h = 694, 254, 222, 124
    d = rrect(x, y, w, h, 3)
    logo = open("/home/claude/treeline/project/assets/Logos/treeline-logo.svg").read()
    logo = logo.replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 14 222 146" width="444" height="292">', f'<svg x="{x+14}" y="{y+16}" width="66" height="44" viewBox="10 14 222 146">')
    g = [f'<g transform="rotate(-3 {x+w/2} {y+h/2})">',
         f'<path d="{d}" fill="{INK}" opacity=".15" transform="translate(3 5)" filter="url(#tls-edge)"/>',
         shape(d, PAPER), logo,
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
            + shape(d, "#fffdf6")
            + f'<path d="{rrect(-w/2+7, -h/2+7, w-14, h-14, 11)}" fill="none" stroke="{BERRY}" stroke-width="5"/>'
            f'<text x="0" y="-16" text-anchor="middle" {SANS} font-size="33" font-weight="800" letter-spacing="1" fill="{BERRY}">NO 911</text>'
            f'<text x="0" y="6" text-anchor="middle" {SANS} font-size="14" font-weight="700" fill="{INK}">No outside calls.</text>'
            f'<text x="0" y="25" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">In an emergency, use</text>'
            f'<text x="0" y="41" text-anchor="middle" {SANS} font-size="12.5" fill="{INK}">a grown-up’s phone.</text>'
            f'<path d="{curl}" fill="#e9dfc8"/><g {WOB}><path d="{curl}" {LNS}/></g>'
            '</g>')

CARD = (722, 506, 156, 100)        # the front card in the card file: x, y, w, h
def card_file():
    """A rotary card file: the treehouse's phone book. The front card's words go in the overlay."""
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
    g.append(shape(front, "url(#tls-paper)"))
    g.append(f'<path d="M{x+8} {y+26} L{x+w-8} {y+26}" stroke="{BERRY}" stroke-width="1" opacity=".55"/>')
    for yy in (y+52, y+78):
        g.append(f'<path d="M{x+8} {yy} L{x+w-8} {yy}" stroke="{SKY}" stroke-width=".8" opacity=".4"/>')
    g.append(f'<path d="M{x+w/2-20} {y+h} L{x+w/2-14} {y+h-9} L{x+w/2-6} {y+h-9} L{x+w/2} {y+h} M{x+w/2} {y+h} L{x+w/2+6} {y+h-9} L{x+w/2+14} {y+h-9} L{x+w/2+20} {y+h}" fill="#3d3a35"/>')
    for kx in (704, 896):           # knobs
        g.append(f'<circle cx="{kx}" cy="610" r="24" fill="url(#tls-knob)"/><circle cx="{kx-6}" cy="603" r="6" fill="#fff" opacity=".22"/><circle cx="{kx}" cy="610" r="7" fill="url(#tls-metal)"/>')
        g.append(f'<g {WOB}><circle cx="{kx}" cy="610" r="24" {LN}/><circle cx="{kx}" cy="610" r="7" {LNS}/></g>')
    return "".join(g)

# ---------------------------------------------------------------- the shelf
def book():
    """The guide: an original 90s how-to book, leaning face-out. Origin: its bottom-left corner."""
    w, h = 150, 178
    x, y = 0, -h
    cover = rrect(x, y, w, h, 3)
    spine = f"M{w} {y+2} L{w+14} {y+10} L{w+14} {-2} L{w} {0} Z"
    burst = " ".join(f"{'M' if i == 0 else 'L'}{(26 if i % 2 == 0 else 19) * math.cos(math.radians(i * 18 - 90)):.1f} {(26 if i % 2 == 0 else 19) * math.sin(math.radians(i * 18 - 90)):.1f}" for i in range(20)) + " Z"
    g = [f'<g transform="rotate(-6)">',
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
    g.append(f'<g transform="rotate(7)">'
             f'<path d="{card}" fill="{INK}" opacity=".14" transform="translate(5 2)" filter="url(#tls-edge)"/>' + shape(card, "#fdfaf2")
             + f'<path d="M{wx} {wy+22} L{ww} {wy+22}" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3" opacity=".5"/>'
             f'<text x="{ww/2}" y="{wy+15}" text-anchor="middle" {MONO} font-size="8" fill="{INK}" opacity=".7">DETACH HERE</text>'
             f'<text x="10" y="{wy+44}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Owner’s</text>'
             f'<text x="10" y="{wy+60}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Warranty</text>'
             f'<text x="10" y="{wy+74}" {SANS} font-size="8.6" font-weight="700" fill="{CANOPY}">&amp; OPEN-SOURCE LICENSES</text>'
             + lines + f'<rect x="10" y="{wy+wh-14}" width="9" height="9" fill="none" stroke="{INK}" stroke-width="1"/><text x="24" y="{wy+wh-6}" {SANS} font-size="7.5" fill="{INK}">I have read the fine print</text>'
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
    tx, ty_, tw = t["tape"]
    front = [shape(leg(x0+32, x0+70, cb, H + 10), "url(#tls-leg)", edge=WOOD_S), shape(leg(x1-70, x1-32, cb, H + 10), "url(#tls-leg)", edge=WOOD_S),
             shape(CARC, "url(#tls-front)", edge=WOOD_S),
             shape(DRAWER, WOOD_M, edge=WOOD_S, extra=f'<path d="M{dx+14} {dy+10} L{dx+dw-14} {dy+10}" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>'),
             f'<path d="M{tx} {ty_+2} L{tx+tw} {ty_} L{tx+tw+1} {ty_+32} L{tx-1} {ty_+34} Z" fill="{CANOPY}"/><path d="M{tx} {ty_+2} L{tx+tw} {ty_} L{tx+tw} {ty_+8} L{tx} {ty_+10} Z" fill="#fff" opacity=".14"/>',
             f'<g {WOB}><path d="M{tx} {ty_+2} L{tx+tw} {ty_} L{tx+tw+1} {ty_+32} L{tx-1} {ty_+34} Z" {LNS}/></g>']
    kx, ky = t["knob"]
    front += [f'<ellipse cx="{kx}" cy="{ky+2}" rx="11" ry="7" fill="{WOOD_S}" opacity=".5" transform="translate(1 3)"/>',
              f'<circle cx="{kx}" cy="{ky}" r="9" fill="url(#tls-metal)"/><g {WOB}><circle cx="{kx}" cy="{ky}" r="9" {LN}/></g>',
              shape(APRON, "url(#tls-front)", edge=WOOD_S),
              shape(TOP, "url(#tls-top)", extra=f'<path d="M{x0+inset+10} {ty+8} L{x1-inset-10} {ty+8}" stroke="#fff" stroke-opacity=".25" stroke-width="3"/>')]
    for f in (.2, .41, .65, .9):     # wood grain
        y = ty + 114 * f; a = x0 + inset * (1 - f); b = x1 - inset * (1 - f)
        front.append(f'<g {WOB}><path d="M{a:.0f} {y:.0f} C{a+150:.0f} {y-3:.0f} {a+260:.0f} {y+3:.0f} {(a+b)/2:.0f} {y:.0f} S{b-120:.0f} {y-3:.0f} {b:.0f} {y+1:.0f}" fill="none" stroke="{WOOD_D}" stroke-width="1" opacity=".35"/></g>')
    front.append(f'<g opacity=".16" filter="url(#tls-grain)"><path d="{TOP} {APRON} {CARC}" fill="#000"/></g>')
    front.append(f'<g {WOB}><path d="M{x0+8} {F+16} L{x1-8} {F+16}" {LNS}/></g>')
    return "".join(back), "".join(sfront), "".join(front)

# ---------------------------------------------------------------- the two layouts
# Every prop is drawn once, in the wide room's coordinates, and placed in a layout by
# translate + scale: place = (old x, old y, new x, new y, scale).
BOX = {   # each prop's box in the wide room's coordinates (what its link covers)
    "sticky": (72, 150, 176, 176), "sketch": (92, 360, 170, 128), "cork": (676, 64, 290, 340),
    "coffee": (688, 80, 268, 166), "card": (688, 246, 236, 142), "cardfile": (684, 470, 232, 204),
    "book": (-14, -186, 186, 196), "warranty": (-10, -155, 150, 160),
}
def placed(content, pl):
    ox, oy, nx, ny, s = pl
    return f'<g transform="translate({nx} {ny}) scale({s}) translate({-ox} {-oy})">{content}</g>'
def moved(box, pl):
    ox, oy, nx, ny, s = pl; bx, by, bw, bh = box
    return (round(nx + (bx - ox) * s, 1), round(ny + (by - oy) * s, 1), round(bw * s, 1), round(bh * s, 1))

LAYOUTS = {
    # Landscape tablets and desktops: zoomed in on the phone and the table top. No shelf: the guide book and
    # the warranty card stand on the table, and the legs run off the bottom just under the drawer.
    "wide": {"W": 1100, "H": 840,
        "table": {"x0": 40, "x1": 1060, "ty": 590, "inset": 80, "ch": 86, "sy": 2000, "H": 840,
                  "drawer": (336, 768, 428, 66), "tape": (406, 776, 288), "knob": (550, 821)},
        "phone": {"x": 270, "y": 2, "w": 560},
        "sticker": (196, 684, .82, .66, -5),
        "place": {"sticky": (72, 150, 34, 40, 1), "sketch": (92, 360, 52, 252, .9), "cork": (676, 64, 800, 40, 1),
                  "cardfile": (684, 674, 776, 672, .85), "book": (0, 0, 118, 632, .82), "warranty": (0, 0, 968, 704, .64)},
        "shelf": [], "table_items": ["book", "cardfile", "warranty"], "sketch": True},
    # Tablets held upright: the same side table, the phone much bigger, the corkboard down beside it.
    "portrait": {"W": 1000, "H": 1270,
        "table": {"x0": 60, "x1": 940, "ty": 800, "inset": 78, "ch": 86, "sy": 1190, "H": 1270,
                  "drawer": (286, 978, 428, 66), "tape": (356, 986, 288), "knob": (500, 1031)},
        "phone": {"x": 170, "y": 49, "w": 660},
        "sticker": (160, 882, .8, .64, -5),
        "place": {"sticky": (72, 150, 20, 60, 1), "sketch": (92, 360, 34, 290, .9), "cork": (676, 64, 788, 180, .72),
                  "cardfile": (684, 674, 768, 888, .78), "book": (0, 0, 196, 1206, .76), "warranty": (0, 0, 455, 1207, .76),
                  "spines": (0, 0, 30, 406, .8), "plant": (0, 0, 142, 419, .8)},
        "shelf": ["spines", "book", "warranty", "plant"], "table_items": ["cardfile"], "sketch": True},
    # Phones: a narrow nightstand, the phone across nearly the whole width, the wall things above it,
    # the sticker on the drawer and the card file on the shelf.
    "tall": {"W": 600, "H": 1340,
        "table": {"x0": 8, "x1": 592, "ty": 812, "inset": 50, "ch": 138, "sy": 1270, "H": 1340,
                  "drawer": (70, 990, 460, 118), "tape": (156, 998, 288), "knob": (452, 1076)},
        "phone": {"x": 28, "y": 245, "w": 544},
        "sticker": (196, 1074, .74, .74, -4),
        "place": {"sticky": (72, 150, 12, 28, .96), "sketch": (0, 0, 0, 0, 1), "cork": (676, 64, 334, 12, .86),
                  "cardfile": (684, 674, 236, 1286, .68), "book": (0, 0, 96, 1286, .74), "warranty": (0, 0, 414, 1287, .72)},
        "shelf": ["book", "cardfile", "warranty"], "table_items": [], "sketch": False},
}

def scene(name):
    L = LAYOUTS[name]; W_, H_ = L["W"], L["H"]; pl = L["place"]
    back, sfront, front = table(L["table"])
    draw = {"book": book, "warranty": warranty, "spines": spines, "plant": plant, "cardfile": card_file}
    item = lambda k: placed(draw[k](), pl[k])
    body = (wall(W_, H_) + placed(sticky_note(), pl["sticky"]) + (placed(framed_sketch(), pl["sketch"]) if L["sketch"] else "")
            + placed(corkboard(), pl["cork"]) + back + "".join(item(k) for k in L["shelf"]) + sfront + front
            + sticker(*L["sticker"]) + "".join(item(k) for k in L["table_items"]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__scene tl-desk__l tl-desk__l--{name}" viewBox="0 0 {W_} {H_}" '
            f'preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">{defs()}{body}</svg>')

def words(name, nm="SAM’S TREEHOUSE", quiet="8 pm – 7 am", contact=("The Parks", "3317"), count="1 of 3", size="21"):
    """The words that change, in their own layer: label tape, the sticky note, the card file's front card."""
    L = LAYOUTS[name]; pl = L["place"]; tx, ty_, tw = L["table"]["tape"]
    x, y, w, h = CARD
    q = (f'<g transform="rotate(-4 160 243)"><text x="160" y="214" text-anchor="middle" {HAND} font-size="30" font-weight="700" fill="{INK}">Quiet time</text>'
         f'<text class="tl-desk__quiettext" x="160" y="256" text-anchor="middle" {HAND} font-size="30" fill="{INK}">{quiet}</text>'
         f'<path d="M108 270 Q160 278 212 268" fill="none" stroke="{BERRY}" stroke-width="2" stroke-linecap="round"/></g>')
    c = (f'<g class="tl-desk__card"><text class="tl-desk__cardname" x="{x+12}" y="{y+46}" {HAND} font-size="25" font-weight="700" fill="{INK}">{contact[0]}</text>'
         f'<text class="tl-desk__cardnum" x="{x+12}" y="{y+74}" {HAND} font-size="29" fill="{SKY}">{contact[1]}</text>'
         f'<text class="tl-desk__cardcount" x="{x+w-10}" y="{y+19}" text-anchor="end" {SANS} font-size="9.5" fill="#857b6b">{count}</text></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__words tl-desk__l tl-desk__l--{name}" viewBox="0 0 {L["W"]} {L["H"]}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">'
            f'<text class="tl-desk__name" x="{tx + tw/2}" y="{ty_ + 24}" text-anchor="middle" {MONO} font-size="{size}" font-weight="700" letter-spacing="3" fill="#f5f1e6">{nm}</text>'
            + placed(q, pl["sticky"]) + placed(c, pl["cardfile"]) + '</svg>')

def words_template(name):
    return words(name, nm="{{NAME}}", quiet="{{QUIET}}", contact=("{{CNAME}}", "{{CNUM}}"), count="{{CCOUNT}}", size="{{NAMESIZE}}")

def geometry(name):
    L = LAYOUTS[name]; pl = L["place"]
    hot = {"guide": moved(BOX["book"], pl["book"]), "licenses": moved(BOX["warranty"], pl["warranty"]),
           "coffee": moved(BOX["coffee"], pl["cork"]), "card": moved(BOX["card"], pl["cork"]), "cardfile": moved(BOX["cardfile"], pl["cardfile"])}
    return {"w": L["W"], "h": L["H"], "phone": L["phone"], "hotspots": hot}

GEOM = {n: geometry(n) for n in LAYOUTS}

if __name__ == "__main__":
    out = "/home/claude/treeline/build/phone/out"
    for n in LAYOUTS:
        open(f"{out}/desk-{n}.svg", "w").write(scene(n))
        open(f"{out}/desk-{n}-words.svg", "w").write(words(n))
    json.dump(GEOM, open(f"{out}/desk-geometry.json", "w"), indent=1)
    print(json.dumps(GEOM))
