  // ---------- Rotary phone: drag-to-dial and lift/hang-up ----------
  // Works on markup from components/RotaryPhone.html (or the React RotaryPhone).
  // Fires on the .tl-rotary element:
  //   "tl-rotary-hook"  { offHook }            when the handset is lifted or hung up
  //   "tl-rotary-pulse" { digit, pulse }       once per pulse while the dial returns (for click sounds)
  //   "tl-rotary-digit" { digit, offHook }     when a dialed digit finishes returning
  var ROTARY = __GEOMETRY__;
  function rotaryCordPath(x1, y1, x2, y2) {
    var loops = 15, r = 6.5, n = loops * 12, dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    var nx = -dy / L, ny = dx / L, d = "";
    for (var i = 0; i <= n; i++) {
      var t = i / n, b = Math.sin(Math.PI * t) * -34 * Math.min(1, L / 160), a = 2 * Math.PI * loops * t;
      var bx = x1 + dx * t + nx * b, by = y1 + dy * t + ny * b;
      var px = bx + nx * r * Math.cos(a) + dx / L * r * 0.55 * Math.sin(a);
      var py = by + ny * r * Math.cos(a) + dy / L * r * 0.55 * Math.sin(a);
      d += (i ? " L" : "M") + px.toFixed(1) + " " + py.toFixed(1);
    }
    return d;
  }
  function attachRotary(root) {
    if (!root || root.__tlRotary) return root && root.__tlRotary;
    var svg = root.querySelector("svg"), wheel = root.querySelector(".tlp-wheel"), hand = root.querySelector(".tlp-handset");
    var cords = root.querySelectorAll(".tlp-cord path"), hookBtn = root.querySelector(".tl-rotary__hook");
    var G = ROTARY, reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var state = { offHook: root.getAttribute("data-hook") === "off", lift: 0, turn: 0, busy: false, drag: null };
    function emit(name, detail) { root.dispatchEvent(new CustomEvent(name, { bubbles: true, detail: detail })); }
    function setTurn(a) { state.turn = a; wheel.setAttribute("transform", "rotate(" + a.toFixed(2) + " " + G.cx + " " + G.cy + ")"); }
    function liftPoint(px, py, t) {
      var a = G.lift.rot * t * Math.PI / 180, ox = G.lift.ox, oy = G.lift.oy;
      return [ox + (px - ox) * Math.cos(a) - (py - oy) * Math.sin(a) + G.lift.tx * t,
              oy + (px - ox) * Math.sin(a) + (py - oy) * Math.cos(a) + G.lift.ty * t];
    }
    function setLift(t) {
      state.lift = t;
      hand.setAttribute("transform", "translate(" + (G.lift.tx * t).toFixed(2) + " " + (G.lift.ty * t).toFixed(2) + ") rotate(" + (G.lift.rot * t).toFixed(2) + " " + G.lift.ox + " " + G.lift.oy + ")");
      var e = liftPoint(G.cordEnd[0], G.cordEnd[1], t), d = rotaryCordPath(G.cordStart[0], G.cordStart[1], e[0], e[1]);
      for (var i = 0; i < cords.length; i++) cords[i].setAttribute("d", d);
    }
    function animate(from, to, ms, step, done) {
      if (reduce || ms <= 0) { step(to); if (done) done(); return; }
      var t0 = null;
      function f(ts) {
        if (t0 === null) t0 = ts;
        var k = Math.min(1, (ts - t0) / ms), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        step(from + (to - from) * e);
        if (k < 1) requestAnimationFrame(f); else if (done) done();
      }
      requestAnimationFrame(f);
    }
    function setHook(off, quiet) {
      if (off === state.offHook) return;
      state.offHook = off; root.setAttribute("data-hook", off ? "off" : "on");
      if (hookBtn) { hookBtn.setAttribute("aria-pressed", off ? "true" : "false"); hookBtn.setAttribute("aria-label", off ? "Hang up" : "Lift the handset"); }
      animate(state.lift, off ? 1 : 0, 380, setLift);
      if (!quiet) emit("tl-rotary-hook", { offHook: off });
    }
    // The dial returns at a real phone's pace: ten pulses a second, one hole-gap per pulse.
    function returnDial(digit) {
      state.busy = true;
      var start = state.turn, speed = 295, pulses = digit === 0 ? 10 : digit, sent = 0, t0 = null;
      function f(ts) {
        if (t0 === null) t0 = ts;
        var a = Math.max(0, start - speed * (ts - t0) / 1000);
        setTurn(a);
        if (digit !== null) {
          var due = Math.min(pulses, Math.floor((start - a) / G.gap));
          while (sent < due) { sent++; emit("tl-rotary-pulse", { digit: digit, pulse: sent }); }
        }
        if (a > 0) requestAnimationFrame(f);
        else { state.busy = false; if (digit !== null) emit("tl-rotary-digit", { digit: digit, offHook: state.offHook }); }
      }
      if (reduce) { setTurn(0); state.busy = false; if (digit !== null) emit("tl-rotary-digit", { digit: digit, offHook: state.offHook }); return; }
      requestAnimationFrame(f);
    }
    function dialDigit(digit) {                 // keyboard or programmatic: turn to the stop, then let go
      if (state.busy || state.drag) return;
      state.busy = true;
      animate(0, G.travel[digit], reduce ? 0 : 260 + G.travel[digit], setTurn, function () { returnDial(digit); });
    }
    function toSvg(ev) {
      var p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY;
      var q = p.matrixTransform(svg.getScreenCTM().inverse()); return { x: q.x, y: q.y };
    }
    function angleAt(pt) { return Math.atan2((pt.y - G.cy) / G.sq, pt.x - G.cx) * 180 / Math.PI; }
    svg.addEventListener("pointerdown", function (ev) {
      if (state.busy) return;
      var pt = toSvg(ev), dx = pt.x - G.cx, dy = (pt.y - G.cy) / G.sq;
      var best = null, bestD = G.holeR * 1.7;
      Object.keys(G.holeAngle).forEach(function (k) {
        var a = G.holeAngle[k] * Math.PI / 180, hx = G.holeK * G.r * Math.cos(a), hy = G.holeK * G.r * Math.sin(a);
        var d = Math.hypot(dx - hx, dy - hy); if (d < bestD) { bestD = d; best = +k; }
      });
      if (best === null) return;
      ev.preventDefault(); svg.setPointerCapture(ev.pointerId);
      state.drag = { digit: best, last: angleAt(pt), turn: 0 };
      root.classList.add("is-dialing");
    });
    svg.addEventListener("pointermove", function (ev) {
      var d = state.drag; if (!d) return;
      var a = angleAt(toSvg(ev)), delta = a - d.last;
      if (delta > 180) delta -= 360; if (delta < -180) delta += 360;
      d.last = a; d.turn = Math.max(0, Math.min(G.travel[d.digit], d.turn + delta));
      setTurn(d.turn);
    });
    function release() {
      var d = state.drag; if (!d) return;
      state.drag = null; root.classList.remove("is-dialing");
      returnDial(d.turn >= G.travel[d.digit] - 6 ? d.digit : null);
    }
    svg.addEventListener("pointerup", release);
    svg.addEventListener("pointercancel", release);
    // The handset lifts with a tap (on the handset or its button) and hangs up the same way.
    hand.addEventListener("click", function () { setHook(!state.offHook); });
    if (hookBtn) hookBtn.addEventListener("click", function () { setHook(!state.offHook); });
    svg.addEventListener("keydown", function (ev) {
      if (/^[0-9]$/.test(ev.key)) { ev.preventDefault(); dialDigit(+ev.key); }
    });
    setLift(state.offHook ? 1 : 0); setTurn(0);
    // Ringing: only the handset trembles, a little, in bursts like the bell (see bundle.css).
    function setRinging(on) { root.classList.toggle("is-ringing", !!on); }
    // The line lamp on the front: lit when the phone is connected and ready; it flashes while it rings.
    function setLine(on) { root.setAttribute("data-line", on ? "on" : "off"); }
    var api = { lift: function () { setHook(true); }, hangUp: function () { setHook(false); }, dial: dialDigit, setRinging: setRinging, isRinging: function () { return root.classList.contains("is-ringing"); }, setLine: setLine, isLineOn: function () { return root.getAttribute("data-line") === "on"; },
                isOffHook: function () { return state.offHook; }, setHook: setHook };
    root.__tlRotary = api;
    return api;
  }
