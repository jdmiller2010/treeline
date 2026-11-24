/* Treeline grove: your treehouse in the middle, a string out to every family it is strung with.
 *
 * Markup only. window.TLGrove.html(options) returns the HTML for one map; styling is .tl-grove in treeline.css, so it
 * follows the theme, the type and the art direction like every other component. Nothing here draws a line of text: names and
 * numbers are real HTML in real buttons, the strings and houses are a decorative SVG behind them.
 *
 *   TLGrove.html({
 *     me:       { name: "The Parks", number: "3317" },
 *     friends:  [{ id: 3, name: "The Okafors", number: "5120", state: "live" | "paused" | "wait" | "ask", href: "#/strings/3" }],
 *     selectedId: 3,            // the friend whose button is aria-current
 *     newIds: [7],              // friends that grow in (string draws itself, house unfurls, leaves drift)
 *   })
 *
 * States: live (a strung family: solid string with a leaf), paused (quiet house, dashed string), wait (we asked, they have not
 * answered: a faint house on a dotted string), ask (they asked, it is ours to answer: a ? and a sun-yellow dotted string).
 * The map is for 12 families at most (MAX): pass more and only the first twelve are drawn, so the app shows its list instead from the thirteenth on. */
(function () {
  "use strict";
  const W = 390, CX = 195, MAX = 12;
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const PIGMENTS = ["leaf", "sky", "petal", "sun", "bark"];
  const STATE_WORD = { live: "strung", paused: "paused", wait: "waiting on them", ask: "needs your answer" };

  const PRESET = { 1: [-55], 2: [-125, -55], 3: [-125, -55, 90], 4: [-125, -55, 55, 125], 5: [-125, -55, -5, 55, 125], 6: [-125, -55, -5, 55, 125, 185] };
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const hit = (a, b, pad) => a.x0 < b.x1 + pad && b.x0 < a.x1 + pad && a.y0 < b.y1 + pad && b.y0 < a.y1 + pad;
  const inside = (pt, r, pad) => pt.x > r.x0 - pad && pt.x < r.x1 + pad && pt.y > r.y0 - pad && pt.y < r.y1 + pad;

  /**
   * Where every house goes, in a drawing 390 wide and H tall. Up to six families sit on hand-picked spots around you (an ellipse).
   * More than six are placed one at a time, nearest first to their even share of the ring, on the first spot where the house and its
   * name tag overlap no other house or tag and no string passes through another house. Houses and tags shrink a little (scale s) as
   * the grove fills, and the drawing grows taller. Returns { H, cy, s, items: [{ x, y, above, node, tag }], me: { node, tag } }.
   */
  function layout(list) {
    const n = list.length, dense = n > 9, s = n <= 6 ? 1 : n <= 9 ? 0.85 : 0.72, H = n <= 6 ? 470 : n <= 9 ? 580 : 680, cy = H / 2;
    const nodeW = 66 * s * 0.8, nodeH = 85 * s, tagH = dense ? 36 : 40;
    const tagW = (f) => clamp(String(f.name).length * (dense ? 7.3 : 8) + 22, 64, dense ? 105 : 118);
    const mk = (x, y, w, f, above) => {
      const node = { x0: x - nodeW / 2, x1: x + nodeW / 2, y0: y - nodeH / 2, y1: y + nodeH / 2 }, tw = w, ty0 = above ? node.y0 - 2 - tagH : node.y1 + 2 - nodeH * 0.04;
      return { x, y, above, node, tag: { x0: x - tw / 2, x1: x + tw / 2, y0: above ? y - nodeH * 0.48 - tagH : y + nodeH * 0.48, y1: above ? y - nodeH * 0.48 : y + nodeH * 0.48 + tagH } };
    };
    const meNode = { x0: CX - 62, x1: CX + 62, y0: cy - 82, y1: cy + 26 };
    const me = { node: meNode, tag: { x0: CX - 52, x1: CX + 52, y0: cy + 26, y1: cy + 26 + 40 } };
    const items = [];
    if (n <= 6) {
      list.forEach((f, i) => { const a = (PRESET[n][i] * Math.PI) / 180, x = CX + 135 * Math.cos(a), sn = Math.sin(a), y = cy + (sn > 0 ? 140 : 165) * sn; items.push(mk(x, y, tagW(f), f, y - cy < -60)); });
      return { H, cy, s, items, me };
    }
    const placed = [me.node, me.tag], segs = [];
    const inBounds = (r) => r.x0 >= 3 && r.x1 <= W - 3 && r.y0 >= 3 && r.y1 <= H - 3;
    const stringOk = (c) => {   // a string from you to c may not run through another house or tag, nor may an older string run through c
      const dx = c.x - CX, dy = c.y - cy;
      for (let k = 0.28; k <= 0.88; k += 0.06) { const pt = { x: CX + dx * k, y: cy + dy * k }; if (items.some((o) => inside(pt, o.node, 4) || inside(pt, o.tag, 4))) return false; }
      return segs.every((sg) => { for (let k = 0.28; k <= 0.88; k += 0.06) { const pt = { x: CX + sg.dx * k, y: cy + sg.dy * k }; if (inside(pt, c.node, 4) || inside(pt, c.tag, 4)) return false; } return true; });
    };
    const rings = [[1, 1], [0.84, 0.88], [1.06, 1.02], [0.68, 0.74], [0.92, 0.6], [0.5, 0.55], [1.06, 0.7], [0.76, 1.04]];
    const cands = [];
    rings.forEach(([fx, fy]) => { for (let a = 0; a < 360; a += 4) { const r = (a * Math.PI) / 180; cands.push({ x: CX + 150 * fx * Math.cos(r), y: cy + (cy - 78) * fy * Math.sin(r) }); } });
    list.forEach((f, i) => {
      const ia = ((-90 + (360 * (i + 0.5)) / n) * Math.PI) / 180, ix = CX + 150 * Math.cos(ia), iy = cy + (cy - 78) * Math.sin(ia);
      const ranked = cands.map((c) => ({ c, d: Math.hypot(c.x - ix, c.y - iy) })).sort((p, q) => p.d - q.d);
      let best = null;
      for (const strict of [true, false]) {
        for (const { c } of ranked) {
          for (const above of c.y < cy ? [true, false] : [false, true]) {
            const it = mk(c.x, c.y, tagW(f), f, above);
            if (!inBounds(it.node) || !inBounds(it.tag)) continue;
            if (placed.some((r) => hit(it.node, r, 5) || hit(it.tag, r, 6))) continue;
            if (strict && !stringOk(it)) continue;
            best = it; break;
          }
          if (best) break;
        }
        if (best) break;
      }
      if (!best) best = mk(ix, iy, tagW(f), f, iy < cy);
      items.push(best); placed.push(best.node, best.tag); segs.push({ dx: best.x - CX, dy: best.y - cy });
    });
    return { H, cy, s, items, me };
  }

  function hash(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; }

  /** One string, as in illustrations/connection.svg: a dotted bark line that sags between two platforms, a leaf hanging at the middle. */
  function stringGeom(to, i, cy, rects, k) {
    // From your platform to theirs; the houses are drawn over the ends (the strings layer is masked by every canopy and house), so each line simply goes behind a tree and ends.
    const x0 = CX, y0 = cy, x1 = to.x, y1 = to.y + 10.8 * k;
    const sag = 16 + (i % 3) * 5, cx = (x0 + x1) / 2, cyy = (y0 + y1) / 2 + sag, f = (n) => n.toFixed(1);
    const at = (t) => ({ x: (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cx + t * t * x1, y: (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * cyy + t * t * y1 });
    let t = 0.5;                                  // the leaf hangs at the middle, or as near it as no name tag covers
    for (const c of [0.5, 0.42, 0.58, 0.34, 0.66, 0.27, 0.73]) { const pt = at(c); if (!rects.some((r) => inside(pt, r, 6))) { t = c; break; } }
    const m = at(t), ang = (Math.atan2((1 - t) * (cyy - y0) + t * (y1 - cyy), (1 - t) * (cx - x0) + t * (x1 - cx)) * 180) / Math.PI;
    return { d: "M" + f(x0) + " " + f(y0) + " Q" + f(cx) + " " + f(cyy) + " " + f(x1) + " " + f(y1), mx: m.x, my: m.y, ang };
  }
  const LEAF = "M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z M0 -9L0 9";


  /* The house is the left treehouse of illustrations/connection.svg, path for path (bumpy canopy, trunk, platform, house, roof, door),
     so the map is drawn by the same hand as every plate. Nothing is added to the drawing. */
  const GLYPH =
    '<svg class="tl-house" viewBox="10 26 92 114" aria-hidden="true" focusable="false">' +
    '<ellipse class="tl-house__ground" cx="56" cy="130" rx="24" ry="4.5"/>' +
        '<path class="tl-house__canopy" d="M97.3 60.0C97.7 67.3 93.2 77.2 86.7 82.6C80.1 88.1 67.8 92.3 58.0 92.5C48.2 92.7 34.6 89.3 27.8 83.8C21.0 78.4 17.4 67.9 17.4 60.0C17.5 52.1 21.2 40.6 28.0 36.3C34.7 31.9 48.6 33.5 58.0 34.0C67.4 34.4 78.1 34.7 84.6 39.0C91.2 43.3 97.0 52.7 97.3 60.0Z"/>' +
    '<g class="tl-house__ink"><path d="M36.7 82.0A15.3 15.3 0 0 1 20.5 65.5A13.1 13.1 0 0 1 23.5 46.4A11.9 11.9 0 0 1 40.0 34.3A14.9 14.9 0 0 1 63.5 31.4A19.0 19.0 0 0 1 89.0 44.9A15.4 15.4 0 0 1 89.8 66.9A12.6 12.6 0 0 1 75.2 81.9"/><path d="M51 98C50 110 49 120 47 130M61 98C62 110 63 120 65 130"/><path d="M35.0 98H77.0"/><path class="tl-house__body" d="M43.0 98V86H69.0V98"/><path d="M39.0 87L56 77L73.0 87"/><path d="M52 98V89H60V98"/></g>' +
    '</svg>';

  /* Ours is the hero treehouse of illustrations/treehouse.svg (the big canopy, branches, ladder and sun) : it is
     bigger than the rest and the only one with a ladder, so you always know which is yours. */
  const ME_GLYPH =
    '<svg class="tl-house tl-house--me" viewBox="48 8 162 142" aria-hidden="true" focusable="false">' +
    '<path class="tl-house__sky" d="M228.0 58.0C228.2 69.3 230.2 84.3 218.5 92.1C206.9 100.0 176.6 106.1 158.0 105.2C139.4 104.4 119.6 94.9 106.6 87.0C93.6 79.1 80.6 67.9 80.1 58.0C79.6 48.1 90.6 35.0 103.6 27.3C116.6 19.7 139.0 12.6 158.0 12.1C177.0 11.6 205.9 16.7 217.6 24.4C229.3 32.0 227.9 46.7 228.0 58.0Z"/>' +
    '<ellipse class="tl-house__ground" cx="118" cy="148" rx="34" ry="5"/>' +
    '<path class="tl-house__canopy" d="M200.4 66.0C201.8 76.7 190.9 94.6 178.5 101.0C166.1 107.4 141.6 105.8 126.0 104.5C110.4 103.3 96.8 99.9 84.8 93.5C72.7 87.1 55.2 76.1 53.8 66.0C52.4 55.9 64.2 40.5 76.2 32.8C88.3 25.1 110.3 19.3 126.0 19.9C141.7 20.5 157.8 28.9 170.2 36.6C182.6 44.2 199.0 55.3 200.4 66.0Z"/>' +
    '<g class="tl-house__ink"><path d="M85.6 98.1A18.0 18.0 0 0 1 61.9 78.6A8.6 8.6 0 0 1 55.9 66.5A21.6 21.6 0 0 1 67.1 37.6A21.8 21.8 0 0 1 95.5 25.2A10.0 10.0 0 0 1 112.3 19.3A32.7 32.7 0 0 1 158.7 27.4A17.2 17.2 0 0 1 179.9 42.8A11.2 11.2 0 0 1 185.3 59.9A12.8 12.8 0 0 1 178.3 80.9A20.3 20.3 0 0 1 154.7 98.5"/><path d="M114 116C113 128 111 138 108 148M128 116C129 128 131 138 134 148"/><path class="tl-house__branch" d="M100 100C96 94 90 90 82 88M142 100C148 92 156 88 164 88"/><path d="M97.0 116H147.0"/><path class="tl-house__body" d="M105.0 116V100H139.0V116"/><path d="M101.0 101L122 88L143.0 101"/><path d="M118 116V107H126V116"/><path d="M92 116L89 148M101 116L98 148"/><path class="tl-house__branch" d="M90.6 128H99.8M89.6 138H98.8"/></g>' +
    '</svg>';

  const FR_CAN = /tl-house__canopy" d="([^"]+)"/.exec(GLYPH)[1], ME_CAN = /tl-house__canopy" d="([^"]+)"/.exec(ME_GLYPH)[1];
  let maskN = 0;
  const BADGE = {
    ask: '<span class="tl-grove__badge" aria-hidden="true">?</span>',
    paused: '<span class="tl-grove__badge" aria-hidden="true"><svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 2.5v7M8 2.5v7"/></svg></span>',
    wait: '<span class="tl-grove__badge" aria-hidden="true"><svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="6" cy="6" r="4.4"/><path d="M6 3.6V6l1.6 1"/></svg></span>',
  };
  const LEAVES = '<span class="tl-grove__leaf" aria-hidden="true"></span><span class="tl-grove__leaf tl-grove__leaf--b" aria-hidden="true"></span>';

  const pct = (x, y, H) => "left:" + ((x / W) * 100).toFixed(2) + "%;top:" + ((y / H) * 100).toFixed(2) + "%";
  const tag = (name, number, above) =>
    '<span class="tl-grove__tag tl-grove__tag--' + (above ? "above" : "below") + '"><span class="tl-grove__name">' + esc(name) + '</span><span class="tl-grove__num">' + esc(number) + "</span></span>";

  function html(opts) {
    const me = opts.me || {}, all = (opts.friends || []).slice(), isNew = new Set((opts.newIds || []).map(String));
    const shown = all.slice(0, MAX), extra = all.length - shown.length, L = layout(shown), H = L.H, CY = L.cy, tagRects = [L.me.tag].concat(L.items.map((it) => it.tag));
    let strings = "", nodes = "";
    shown.forEach((f, i) => {
      const p = L.items[i], st = STATE_WORD[f.state] ? f.state : "live", fresh = isNew.has(String(f.id)), above = p.above;
      const g = stringGeom(p, i, CY, tagRects, L.s), mid = "tl-grove-m" + i;
      strings += '<g class="tl-string tl-string--' + st + (fresh ? " is-new" : "") + '">' +
        (fresh ? '<mask id="' + mid + '" maskUnits="userSpaceOnUse" x="0" y="0" width="' + W + '" height="' + H + '"><path class="tl-string__reveal" pathLength="100" d="' + g.d + '"/></mask>' : "") +
        '<g' + (fresh ? ' mask="url(#' + mid + ')"' : "") + '><path class="tl-string__wash" d="' + g.d + '"/><path class="tl-string__line" d="' + g.d + '"/></g>' +
        (st === "live" ? '<path class="tl-string__leaf" d="' + LEAF + '" transform="translate(' + g.mx.toFixed(1) + " " + g.my.toFixed(1) + ") rotate(" + (g.ang + 70).toFixed(0) + ') scale(.7)"/>' : "") + "</g>";
      const label = f.name + ", " + f.number + ", " + STATE_WORD[st];
      const attrs = (f.href ? ' data-href="' + esc(f.href) + '"' : "") + (String(opts.selectedId) === String(f.id) ? ' aria-current="true"' : "") + (f.id != null ? ' data-id="' + esc(f.id) + '"' : "");
      nodes += '<button type="button" class="tl-grove__node tl-house--' + PIGMENTS[hash(f.name + f.number) % 5] + (fresh ? " is-new" : "") + '" data-state="' + st + '" style="' + pct(p.x, p.y, H) + '" aria-label="' + esc(label) + '"' + attrs + ">" +
        GLYPH + (BADGE[st] || "") + tag(f.name, f.number, above) + (fresh ? LEAVES : "") + "</button>";
    });
    if (!shown.length) strings += '<g class="tl-string tl-string--loose"><path class="tl-string__line" d="M195 235 Q250 238 252 170"/></g><g class="tl-grove__seed" transform="translate(252 160)"><path d="M0,10 L0,0" /><circle r="2.4" cy="-2"/><path d="M0,-2 l-7,-10 M0,-2 l0,-11 M0,-2 l7,-10" fill="none"/></g>';
    // Hide every string where it passes behind a canopy or a house: black shapes, drawn where the houses are, on a white mask.
    const kf = (66.3 * L.s) / 92, km = 124.8 / 162, mid0 = "tl-grove-hide" + ++maskN;
    const hide = '<mask id="' + mid0 + '" maskUnits="userSpaceOnUse" x="0" y="0" width="' + W + '" height="' + H + '"><rect width="' + W + '" height="' + H + '" fill="#fff"/>' +
      '<g fill="#000" transform="translate(' + CX + " " + CY + ") scale(" + km.toFixed(3) + ') translate(-118 -116)"><path d="' + ME_CAN + '"/><rect x="95" y="84" width="54" height="34"/></g>' +
      L.items.map((it) => '<g fill="#000" transform="translate(' + it.x.toFixed(1) + " " + it.y.toFixed(1) + ") scale(" + kf.toFixed(3) + ') translate(-56 -83)"><path d="' + FR_CAN + '"/><rect x="33" y="76" width="46" height="23"/></g>').join("") + "</mask>";
    return '<div class="tl-grove' + (shown.length > 9 ? " tl-grove--dense" : "") + '" style="aspect-ratio:' + W + " / " + H + ";--grove-s:" + L.s + '" role="group" aria-label="' + esc((me.name || "Your treehouse") + " and its strings") + '" data-count="' + shown.length + '">' +
      '<svg class="tl-grove__strings" viewBox="0 0 ' + W + " " + H + '" aria-hidden="true" focusable="false">' +
      '' + hide + '<g mask="url(#' + mid0 + ')">' + strings + "</g></svg>" +
      '<div class="tl-grove__node tl-grove__node--me tl-house--leaf" data-state="me" style="' + pct(CX, CY, H) + '">' + ME_GLYPH + tag(me.name || "Your treehouse", me.number || "", false) + "</div>" + nodes + "</div>";
  }

  window.TLGrove = { html, layout, MAX };
})();
