# Art for the softphone room's close-ups: the three paper cards you can pick up, and the pages of the
# guide book (a picture tutorial). Same ink line over watercolor as the room.
import math, re, sys
sys.path.insert(0, "/home/claude/treeline/build/phone")
import desk, rotary
from desk import INK, LN, LNS, WOB, WASH, SERIF, SANS, HAND, SKY, BERRY, CANOPY, SUN, rrect, shape, crayon

def defs(prefix):
    return desk.defs().replace('id="tls-', f'id="{prefix}-').replace("url(#tls-", f"url(#{prefix}-")

def fix(svg, prefix):
    return svg.replace('id="tls-', f'id="{prefix}-').replace("url(#tls-", f"url(#{prefix}-")

# ---------------------------------------------------------------- picked up
def warranty_detail():
    """The warranty card up close: the same card with its fine print you can actually read."""
    ww, wh = 118, 150
    card = rrect(0, 0, ww, wh, 2)
    fine = ["Treeline is free for",
            "families to use, not to sell.",
            "Code: PolyForm Noncommercial.",
            "Pictures: CC BY-NC 4.0.",
            "Made with Fraunces, Figtree",
            "and Caveat (OFL), JsSIP and",
            "qrcode-generator (MIT).",
            "Tap to read every license."]
    t = "".join(f'<text x="10" y="{84 + i*7.4:.1f}" {SANS} font-size="5.6" fill="{INK}" opacity=".8">{l}</text>' for i, l in enumerate(fine))
    return (shape(card, "#fdfaf2")
            + f'<path d="M0 22 L{ww} 22" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3" opacity=".5"/>'
            f'<text x="{ww/2}" y="15" text-anchor="middle" font-family="\'Courier New\', Courier, monospace" font-size="8" fill="{INK}" opacity=".7">DETACH HERE</text>'
            f'<text x="10" y="44" {SERIF} font-size="14" font-weight="600" fill="{INK}">Owner’s</text>'
            f'<text x="10" y="60" {SERIF} font-size="14" font-weight="600" fill="{INK}">Warranty</text>'
            f'<text x="10" y="74" {SANS} font-size="7.4" font-weight="700" fill="{CANOPY}">&amp; OPEN-SOURCE LICENSES</text>'
            + t + f'<rect x="10" y="{wh-14}" width="9" height="9" fill="none" stroke="{INK}" stroke-width="1"/><text x="24" y="{wh-6}" {SANS} font-size="7.5" fill="{INK}">I have read the fine print</text>')

def pickups():
    k = "tlk"
    cert = fix(desk.certificate(0), k); card = fix(desk.business_card(0), k)
    war = fix(warranty_detail(), k)
    out = {
        "coffee": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="686 84 270 156" aria-hidden="true" focusable="false">{defs(k)}{cert}</svg>',
        "card": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="686 246 238 140" aria-hidden="true" focusable="false">{defs(k)}{card}</svg>',
        "licenses": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 126 158" aria-hidden="true" focusable="false">{defs(k)}{war}</svg>',
    }
    return out

# ---------------------------------------------------------------- the book
PW, PH = 300, 356                      # one page (the cover is 150 x 178, so the same shape)
def dial_window(n, svg, cx=150, cy=140, r=116):
    """A round window onto the dial, for the close-ups."""
    return (f'<clipPath id="tlb-dw{n}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath><g clip-path="url(#tlb-dw{n})">{svg}</g>'
            f'<g {WOB}><circle cx="{cx}" cy="{cy}" r="{r}" {LN}/></g>')

def phone(n, lifted=False, x=40, y=10, w=220, view="0 -70 400 510", extra=""):
    s = rotary.svg(number="4821", lifted=lifted, colors="moss", cls="x")
    s = s.replace('id="tlp-', f'id="tlb-p{n}-').replace("url(#tlp-", f"url(#tlb-p{n}-").replace(' class="x"', "")
    vb = [float(v) for v in view.split()]
    h = w * vb[3] / vb[2]
    s = re.sub(r'^<svg [^>]*>', f'<svg x="{x}" y="{y}" width="{w}" height="{h:.1f}" viewBox="{view}">', s)
    return s[:-6] + extra + "</svg>"

def caption(lines, y=300):
    return "".join(f'<text x="{PW/2}" y="{y + i*26}" text-anchor="middle" {SERIF} font-size="21" font-style="italic" fill="{INK}">{t}</text>' for i, t in enumerate(lines))

def page(n, body, label, num=None):
    paper = (f'<rect width="{PW}" height="{PH}" fill="#fbf6e9"/>'
             f'<rect width="{PW}" height="{PH}" fill="url(#tlb-pagegrad)"/>'
             f'<g opacity=".1" filter="url(#tlb-grain)"><rect width="{PW}" height="{PH}" fill="#000"/></g>')
    foot = f'<text x="{PW/2}" y="{PH-14}" text-anchor="middle" {SANS} font-size="10" fill="#857b6b">{num}</text>' if num else ""
    grad = '<linearGradient id="tlb-pagegrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".06"/><stop offset=".12" stop-color="#000" stop-opacity="0"/><stop offset=".9" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".04"/></linearGradient>'
    d = defs("tlb").replace("</defs>", grad + "</defs>").replace('id="tlb-', f'id="tlb-{n}').replace("url(#tlb-", f"url(#tlb-{n}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="tl-book__art" viewBox="0 0 {PW} {PH}" role="img" aria-label="{label}">'
            + d + paper.replace("url(#tlb-", f"url(#tlb-{n}") + body.replace('url(#tlb-', f'url(#tlb-{n}').replace('id="tlb-', f'id="tlb-{n}') + foot + '</svg>')

def finger(cx, cy, r=15):
    return (f'<circle cx="{cx+3}" cy="{cy+5}" r="{r}" fill="{INK}" opacity=".18"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#f2c9b8"/><path d="M{cx-r*.5} {cy-r*.3} q{r*.5} {-r*.6} {r} 0" fill="none" stroke="#fff" stroke-width="2.5" opacity=".6" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" {LN}/>')

def hole(d):
    return rotary.P(rotary.HOLE_ANGLE[d], rotary.HOLE_K)

def pages():
    out = []
    # 0 the cover (front of the first leaf)
    cover = desk.book()
    inner = cover[cover.index('<g>') + 3: cover.rindex('</g>')]
    inner = re.sub(r'<path d="M0 -178[^>]*translate\(8 2\)[^>]*/>', '', inner)
    inner = re.sub(r'<g filter="url\(#tls-wash\)"><path d="M150 -176[^<]*</g>', '', inner)
    inner = inner.replace("translate(136 -120) rotate(12)", "translate(124 -150) rotate(12)")
    cov = f'<g transform="scale(2) translate(0 178)">{fix(inner, "tlb")}</g>'
    out.append(page("c", cov, "Rotary Phones the easy way. A Treeline guide."))
    # 1 title page
    t = (f'<text x="{PW/2}" y="110" text-anchor="middle" {SERIF} font-size="28" font-weight="700" letter-spacing="2" fill="{SKY}">ROTARY PHONES</text>'
         f'<text x="{PW/2}" y="146" text-anchor="middle" {SERIF} font-size="24" font-style="italic" fill="{INK}">the easy way</text>'
         f'<path d="M110 172 L190 172" stroke="{SKY}" stroke-width="1.2"/>'
         f'<text x="{PW/2}" y="204" text-anchor="middle" {SANS} font-size="13" fill="#5e5546">How to call a friend</text>'
         f'<text x="{PW/2}" y="222" text-anchor="middle" {SANS} font-size="13" fill="#5e5546">from your treehouse</text>'
         f'<text x="{PW/2}" y="320" text-anchor="middle" {SANS} font-size="10" font-weight="700" letter-spacing="1.5" fill="{SKY}">TREELINE PRESS</text>')
    out.append(page("t", t, "Rotary Phones the easy way: how to call a friend from your treehouse."))
    # 2 lift the handset
    hum = crayon("M40 66 q8 -8 16 0 t16 0 t16 0 M34 86 q8 -8 16 0 t16 0 t16 0", SKY, 2.4)
    out.append(page(2, phone(2, True, 46, 20, 212) + hum + caption(["Lift the handset.", "Hear the hum?"], 300), "Step 1: lift the handset and listen for the hum of the dial tone.", 1))
    # 3 finger in a number
    hx, hy = hole(4)
    out.append(page(3, dial_window(3, phone(3, False, 30, 22, 240, "102 196 196 192", finger(hx, hy, 13))) + caption(["Put a finger", "in a number."], 300), "Step 2: put a finger in the hole for the first number.", 2))
    # 4 turn to the stop
    a0 = rotary.HOLE_ANGLE[4]; tr = rotary.TRAVEL[4]
    pts = [rotary.P(a0 + tr * i / 20, 1.18) for i in range(21)]
    arc = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    ex, ey = pts[-1]; px_, py_ = pts[-3]; ang = math.atan2(ey - py_, ex - px_)
    head = f"M{ex:.1f} {ey:.1f} L{ex - 9*math.cos(ang - .5):.1f} {ey - 9*math.sin(ang - .5):.1f} M{ex:.1f} {ey:.1f} L{ex - 9*math.cos(ang + .5):.1f} {ey - 9*math.sin(ang + .5):.1f}"
    sx, sy = rotary.P(rotary.STOP, 1.0)
    arrow = (f'<path d="{arc}" fill="none" stroke="{BERRY}" stroke-width="4" stroke-linecap="round"/><path d="{head}" fill="none" stroke="{BERRY}" stroke-width="4" stroke-linecap="round"/>'
             + finger(*rotary.P(a0 + tr, rotary.HOLE_K), 13))
    out.append(page(4, dial_window(4, phone(4, False, 30, 22, 240, "96 184 208 204", arrow)) + caption(["Turn it to the metal stop.", "Then let go!"], 300), "Step 3: turn the number round to the metal stop, then let go.", 3))
    # 5 four numbers
    cardx, cardy = 54, 50
    cardd = rrect(cardx, cardy, 192, 120, 6)
    c = (shape(cardd, "#fffaf0") + f'<path d="M{cardx+10} {cardy+30} L{cardx+182} {cardy+30}" stroke="{BERRY}" stroke-width="1" opacity=".55"/>'
         + "".join(f'<path d="M{cardx+10} {yy} L{cardx+182} {yy}" stroke="{SKY}" stroke-width=".8" opacity=".4"/>' for yy in (cardy + 62, cardy + 94))
         + f'<text x="{cardx+14}" y="{cardy+56}" {HAND} font-size="30" font-weight="700" fill="{INK}">The Parks</text>'
         + f'<text x="{cardx+14}" y="{cardy+90}" {HAND} font-size="34" fill="{SKY}">3317</text>')
    for i, dgt in enumerate("3317"):
        cx_ = 72 + i * 52; cy_ = 220
        c += f'<circle cx="{cx_}" cy="{cy_}" r="20" fill="#fffaf0"/><g {WOB}><circle cx="{cx_}" cy="{cy_}" r="20" {LN}/></g><text x="{cx_}" y="{cy_+8}" text-anchor="middle" {SERIF} font-size="22" font-weight="600" fill="{INK}">{dgt}</text>'
    out.append(page(5, c + caption(["Dial all four numbers", "to call a friend."], 300), "Step 4: dial all four numbers from the card file to call a friend.", 4))
    # 6 busy
    beep = (f'<text x="22" y="62" {HAND} font-size="24" font-weight="700" fill="{BERRY}" transform="rotate(-10 22 62)">beep</text>'
            f'<text x="34" y="96" {HAND} font-size="24" font-weight="700" fill="{BERRY}" transform="rotate(-6 34 96)">beep</text>'
            f'<text x="20" y="130" {HAND} font-size="24" font-weight="700" fill="{BERRY}" transform="rotate(-12 20 130)">beep</text>')
    out.append(page(6, phone(6, True, 66, 24, 200) + beep + caption(["Beep, beep? They’re busy.", "Hang up, try later."], 300), "If you hear beep, beep, beep, they are busy. Hang up and try again later.", 5))
    # 7 quiet time
    moon = (f'<path d="M232 40 A26 26 0 1 0 256 78 A20 20 0 1 1 232 40 Z" fill="{SUN}" opacity=".8"/><g {WOB}><path d="M232 40 A26 26 0 1 0 256 78 A20 20 0 1 1 232 40 Z" {LN}/></g>'
            f'<text x="192" y="104" {HAND} font-size="22" fill="{SKY}">z</text><text x="206" y="88" {HAND} font-size="26" fill="{SKY}">z</text><text x="222" y="70" {HAND} font-size="30" fill="{SKY}">z</text>')
    out.append(page(7, phone(7, False, 50, 6, 200) + moon + caption(["At quiet time", "the phone is asleep."], 300), "At quiet time the phone is asleep and can't ring or call.", 6))
    # 8 no 911
    st = fix(desk.sticker(150, 132, 1.25, 1.25, -4), "tlb")
    out.append(page(8, st + caption(["No 911 on this phone.", "In an emergency, find", "a grown-up and use theirs."], 264), "This phone can't call 911. In an emergency, find a grown-up and use their phone.", 7))
    # 9 hang up
    heart = crayon("M232 60 C222 44 200 52 210 70 L232 92 L254 70 C264 52 242 44 232 60 Z", BERRY, 2.6)
    out.append(page(9, phone(9, False, 50, 6, 200) + heart + caption(["All done? Hang up.", "Bye!"], 300), "All done? Put the handset back to hang up. Bye!", 8))
    # 10 the end (the inside of the back cover)
    end = (f'<text x="{PW/2}" y="150" text-anchor="middle" {SERIF} font-size="30" font-style="italic" fill="{INK}">The end.</text>'
           f'<text x="{PW/2}" y="190" text-anchor="middle" {HAND} font-size="28" fill="{SKY}">Now go call a friend!</text>'
           + crayon("M100 250 C130 236 170 236 200 250", "#5f9a55", 2.6))
    out.append(page("e", end, "The end. Now go call a friend!"))
    return out

if __name__ == "__main__":
    import json
    p = pages(); k = pickups()
    print(len(p), sum(len(x) for x in p) // 1024, "KB pages;", sum(len(x) for x in k.values()) // 1024, "KB pickups")
    for i, x in enumerate(p):
        open(f"/home/claude/treeline/build/phone/out/page-{i}.svg", "w").write(x)
    for n, x in k.items():
        open(f"/home/claude/treeline/build/phone/out/pick-{n}.svg", "w").write(x)
