# The guide's pictures, without their book pages' captions, for the softphone's "How to dial" sheet.
import re, os
SRC = "/home/claude/treeline/build/phone/out"
DEST = "/home/claude/treeline/project/assets/Illustrations/guide"
# page index -> (file, crop in page units: x y w h). Pages are 300 x 450; the pictures sit in the top part.
PICS = {2: ("light", "34 105 232 158"), 3: ("lift", "20 52 260 272"), 4: ("finger", "20 52 260 256"), 5: ("turn", "20 52 260 256"),
        6: ("numbers", "20 52 260 256"), 7: ("busy", "0 52 280 272"), 8: ("quiet", "20 52 260 272"), 9: ("no-911", "20 52 260 256"),
        10: ("hang-up", "20 52 260 272")}
os.makedirs(DEST, exist_ok=True)
for i, (name, vb) in PICS.items():
    s = open(f"{SRC}/page-{i}.svg").read()
    _, _, vw, vh = vb.split()
    s = re.sub(r'viewBox="0 0 300 450"', f'viewBox="{vb}" width="{vw}" height="{vh}"', s, count=1)
    s = re.sub(r'<svg ([^>]*?)class="tl-book__art" ', r'<svg \1', s, count=1)
    s = re.sub(r' role="img" aria-label="[^"]*"', ' aria-hidden="true"', s, count=1)
    if 'xmlns="http://www.w3.org/2000/svg"' not in s[:200]: s = s.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    # drop the page's own paper, so the picture sits on the sheet's well
    s = re.sub(r'<rect width="300" height="450" fill="#fbf6e9"/>', "", s, count=1)
    s = re.sub(r'<g opacity="\.1" filter="url\(#tlb-[^"]*grain\)"><rect width="300" height="450" fill="#000"/></g>', "", s, count=1)
    s = re.sub(r'<rect width="300" height="450" fill="url\(#tlb-[^)]*pagegrad\)"/>', "", s)
    # the captions are words on the page now, not in the picture
    s = re.sub(r'<text [^>]*font-size="21" font-style="italic"[^>]*>.*?</text>', "", s)
    open(f"{DEST}/{name}.svg", "w").write(s)
    print(name, len(s))
