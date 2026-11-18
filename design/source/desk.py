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
def wall():
    g = [f'<rect x="0" y="0" width="{W}" height="1160" fill="url(#tls-wall)"/>']
    for i, x in enumerate(range(18, W, 44)):          # 90s pinstripe wallpaper, a sage stripe and a fine rule
        g.append(f'<rect x="{x}" y="0" width="14" height="1160" fill="{STRIPE}" opacity=".7"/>')
        g.append(f'<path d="M{x+29} 0 L{x+29} 1160" stroke="{WALL_D}" stroke-width="1.2" opacity=".8"/>')
    g.append(f'<g opacity=".12" filter="url(#tls-grain)"><rect x="0" y="0" width="{W}" height="1160" fill="#000"/></g>')
    g.append(f'<ellipse cx="500" cy="420" rx="430" ry="300" fill="#fff6dd" opacity=".45" filter="url(#tls-soft)"/>')
    # baseboard
    g.append(shape("M0 1122 L1000 1122 L1000 1162 L0 1162 Z", "#efe6d2"))
    g.append(f'<path d="M0 1131 L1000 1131" {LNS}/>')
    return "".join(g)

def floor():
    g = [f'<rect x="0" y="1160" width="{W}" height="140" fill="url(#tls-floor)"/>']
    for y in (1192, 1232, 1278):
        g.append(f'<g {WOB}><path d="M0 {y} L1000 {y}" {LNS}/></g>')
    for y0, y1, xs in ((1162, 1192, (140, 520, 860)), (1192, 1232, (60, 330, 700)), (1232, 1278, (210, 590, 930)), (1278, 1300, (40, 420, 780))):
        for x in xs:
            g.append(f'<g {WOB}><path d="M{x} {y0+2} L{x} {y1-2}" {LNS}/></g>')
    g.append(f'<g opacity=".14" filter="url(#tls-grain)"><rect x="0" y="1160" width="{W}" height="140" fill="#000"/></g>')
    g.append(f'<ellipse cx="500" cy="1172" rx="440" ry="26" fill="{WOOD_S}" opacity=".35" filter="url(#tls-soft)"/>')
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

# ---------------------------------------------------------------- the table
TOP = "M150 588 C150 584 154 582 160 582 L840 582 C846 582 850 584 850 588 L928 696 C930 700 928 702 922 702 L78 702 C72 702 70 700 72 696 Z"
APRON = "M72 702 L928 702 L928 742 C928 748 924 750 918 750 L82 750 C76 750 72 748 72 742 Z"
CARCASS = "M104 750 L896 750 L896 836 L104 836 Z"
DRAWER = rrect(286, 760, 428, 66, 6)
SHELF_TOP = "M132 1022 L868 1022 L902 1048 L98 1048 Z"
SHELF_FRONT = "M98 1048 L902 1048 L902 1072 C902 1076 899 1078 895 1078 L105 1078 C101 1078 98 1076 98 1072 Z"
def leg(x0, x1, y0, y1, taper=4):
    return f"M{x0} {y0} L{x1} {y0} L{x1-taper} {y1} C{x1-taper} {y1+4} {x0+taper} {y1+4} {x0+taper} {y1} Z"

def table_back():
    """Back legs, the shelf and what sits on it. Drawn before the front legs."""
    g = [shape(leg(156, 182, 836, 1136, 2), WOOD_D), shape(leg(818, 844, 836, 1136, 2), WOOD_D),
         shape(SHELF_TOP, "url(#tls-top)")]
    g.append(f'<g {WOB}><path d="M140 1028 C300 1026 700 1026 860 1028" {LNS}/></g>')
    g.append(f'<g transform="translate(0 38)">{shelf_things()}</g>')
    g.append(shape(SHELF_FRONT, "url(#tls-front)", edge=WOOD_S))
    g.append(f'<g opacity=".18" filter="url(#tls-grain)"><path d="{SHELF_TOP} {SHELF_FRONT}" fill="#000"/></g>')
    return "".join(g)

def table_front():
    g = [shape(leg(104, 142, 836, 1150), "url(#tls-leg)", edge=WOOD_S), shape(leg(858, 896, 836, 1150), "url(#tls-leg)", edge=WOOD_S),
         shape(CARCASS, "url(#tls-front)", edge=WOOD_S),
         shape(DRAWER, WOOD_M, edge=WOOD_S, extra=f'<path d="M300 770 L700 770" stroke="#fff" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>'),
         # label tape on the drawer: the treehouse's name goes in the overlay
         f'<path d="M356 770 L644 768 L645 800 L355 802 Z" fill="{CANOPY}"/><path d="M356 770 L644 768 L644 776 L356 778 Z" fill="#fff" opacity=".14"/>',
         f'<g {WOB}><path d="M356 770 L644 768 L645 800 L355 802 Z" {LNS}/></g>',
         # knob
         f'<ellipse cx="500" cy="815" rx="11" ry="7" fill="{WOOD_S}" opacity=".5" transform="translate(1 3)"/>',
         f'<circle cx="500" cy="813" r="9" fill="url(#tls-metal)"/><g {WOB}><circle cx="500" cy="813" r="9" {LN}/></g>',
         shape(APRON, "url(#tls-front)", edge=WOOD_S),
         shape(TOP, "url(#tls-top)", extra=f'<path d="M160 590 L840 590" stroke="#fff" stroke-opacity=".25" stroke-width="3"/>')]
    for y, x0, x1 in ((604, 168, 834), (628, 150, 856), (655, 126, 878), (684, 96, 906)):   # wood grain
        g.append(f'<g {WOB}><path d="M{x0} {y} C{x0+150} {y-3} {x0+260} {y+3} {(x0+x1)/2} {y} S{x1-120} {y-3} {x1} {y+1}" fill="none" stroke="{WOOD_D}" stroke-width="1" opacity=".35"/></g>')
    g.append(f'<g opacity=".16" filter="url(#tls-grain)"><path d="{TOP} {APRON} {CARCASS}" fill="#000"/></g>')
    g.append(f'<g {WOB}><path d="M80 712 L920 712" {LNS}/></g>')
    return "".join(g)

def sticker():
    """The no-911 sticker, stuck to the table top and seen in perspective."""
    w, h = 196, 118
    d = rrect(-w/2, -h/2, w, h, 16)
    curl = f"M{w/2-30} {h/2} Q{w/2-6} {h/2-6} {w/2} {h/2-30} L{w/2} {h/2-16} Q{w/2} {h/2} {w/2-16} {h/2} Z"
    return (f'<g transform="translate(190 662) rotate(-5) scale(.9 .72)">'
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
    """The guide: an original 90s how-to book, leaning face-out."""
    w, h = 150, 178
    x, y = 0, -h
    cover = rrect(x, y, w, h, 3)
    spine = f"M{w} {y+2} L{w+14} {y+10} L{w+14} {-2} L{w} {0} Z"
    burst = " ".join(f"{'M' if i == 0 else 'L'}{(26 if i % 2 == 0 else 19) * math.cos(math.radians(i * 18 - 90)):.1f} {(26 if i % 2 == 0 else 19) * math.sin(math.radians(i * 18 - 90)):.1f}" for i in range(20)) + " Z"
    g = [f'<g transform="translate(206 1000) rotate(-6)">',
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

def shelf_things():
    g = [book()]
    for x, w, h, col in ((392, 30, 160, "#55704f"), (423, 26, 150, "#8f5f33"), (450, 34, 166, "#97483d"), (485, 24, 140, "#2a6488")):   # spines
        d = rrect(x, 1000 - h, w, h, 2)
        g.append(shape(d, col, edge="#000"))
        g.append(f'<path d="M{x+4} {1000-h+18} L{x+w-4} {1000-h+18} M{x+4} {1000-h+24} L{x+w-4} {1000-h+24} M{x+4} {1000-26} L{x+w-4} {1000-26}" stroke="{SUN}" stroke-width="1.6" opacity=".8"/>')
        g.append(f'<path d="M{x+w/2} {1000-h+40} L{x+w/2} {1000-50}" stroke="#fff" stroke-width="3" opacity=".25" stroke-linecap="round"/>')
    # the warranty card (open-source licenses), leaning against the spines
    wx, wy, ww, wh = 0, -150, 118, 150
    card = rrect(wx, wy, ww, wh, 2)
    lines = "".join(f'<path d="M10 {wy+y_} L{ww-10 - (14 if i % 3 == 2 else 0)} {wy+y_}" stroke="{INK}" stroke-width="1.6" opacity=".22"/>' for i, y_ in enumerate(range(80, 132, 7)))
    g.append(f'<g transform="translate(522 1001) rotate(7)">'
             f'<path d="{card}" fill="{INK}" opacity=".14" transform="translate(5 2)" filter="url(#tls-edge)"/>' + shape(card, "#fdfaf2")
             + f'<path d="M{wx} {wy+22} L{ww} {wy+22}" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3" opacity=".5"/>'
             f'<text x="{ww/2}" y="{wy+15}" text-anchor="middle" {MONO} font-size="8" fill="{INK}" opacity=".7">DETACH HERE</text>'
             f'<text x="10" y="{wy+44}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Owner’s</text>'
             f'<text x="10" y="{wy+60}" {SERIF} font-size="14" font-weight="600" fill="{INK}">Warranty</text>'
             f'<text x="10" y="{wy+74}" {SANS} font-size="8.6" font-weight="700" fill="{CANOPY}">&amp; OPEN-SOURCE LICENSES</text>'
             + lines + f'<rect x="10" y="{wy+wh-14}" width="9" height="9" fill="none" stroke="{INK}" stroke-width="1"/><text x="24" y="{wy+wh-6}" {SANS} font-size="7.5" fill="{INK}">I have read the fine print</text>'
             '</g>')
    # two books lying flat with a little potted tree on top
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

# ---------------------------------------------------------------- assemble
PHONE = {"x": 265, "y": 101, "w": 470}       # where the RotaryPhone sits, in scene units (its base on the table)
HOTSPOTS = {                                  # x, y, w, h in scene units
    "guide":    (192, 852, 186, 196),
    "licenses": (512, 884, 150, 160),
    "coffee":   (688, 80, 268, 166),
    "card":     (688, 246, 236, 142),
    "cardfile": (684, 470, 232, 204),
}
def scene():
    body = (wall() + floor() + sticky_note() + framed_sketch() + corkboard()
            + table_back() + table_front() + sticker() + card_file())
    return f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__scene" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">{defs()}{body}</svg>'

def overlay(name="SAM’S TREEHOUSE", quiet="8 pm – 7 am", contact=("The Parks", "3317"), count="1 of 3"):
    """The words that change: label tape, quiet-time note and the card file's front card."""
    x, y, w, h = CARD
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-desk__words" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">'
            f'<text class="tl-desk__name" x="500" y="792" text-anchor="middle" {MONO} font-size="21" font-weight="700" letter-spacing="3" fill="#f5f1e6">{name}</text>'
            f'<g transform="rotate(-4 160 243)" class="tl-desk__quiet"><text x="160" y="214" text-anchor="middle" {HAND} font-size="30" font-weight="700" fill="{INK}">Quiet time</text>'
            f'<text class="tl-desk__quiettext" x="160" y="256" text-anchor="middle" {HAND} font-size="30" fill="{INK}">{quiet}</text>'
            f'<path d="M108 270 Q160 278 212 268" fill="none" stroke="{BERRY}" stroke-width="2" stroke-linecap="round"/></g>'
            f'<g class="tl-desk__card"><text class="tl-desk__cardname" x="{x+12}" y="{y+46}" {HAND} font-size="25" font-weight="700" fill="{INK}">{contact[0]}</text>'
            f'<text class="tl-desk__cardnum" x="{x+12}" y="{y+74}" {HAND} font-size="29" fill="{SKY}">{contact[1]}</text>'
            f'<text class="tl-desk__cardcount" x="{x+w-10}" y="{y+19}" text-anchor="end" {SANS} font-size="9.5" fill="#857b6b">{count}</text></g>'
            '</svg>')

GEOM = {"w": W, "h": H, "phone": PHONE, "hotspots": HOTSPOTS}

def words_template():
    t = overlay(name="{{NAME}}", quiet="{{QUIET}}", contact=("{{CNAME}}", "{{CNUM}}"), count="{{CCOUNT}}")
    return t.replace('font-size="21" font-weight="700" letter-spacing="3"', 'font-size="{{NAMESIZE}}" font-weight="700" letter-spacing="3"')

if __name__ == "__main__":
    out = "/home/claude/treeline/build/phone/out"
    open(f"{out}/desk-scene.svg", "w").write(scene())
    open(f"{out}/desk-words.svg", "w").write(overlay())
    json.dump(GEOM, open(f"{out}/desk-geometry.json", "w"))
    print("desk written")
