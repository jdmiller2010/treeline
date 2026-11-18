/* Treeline UI: the only behavior plain HTML needs.
   Switches toggle on click and fire a "tl-change" event with { checked }.
   Sheets open and close; list and detail switches panes on narrow screens;
   menus open, close and take arrow keys; toasts appear and leave; alerts can be dismissed;
   passwords show and hide; code boxes advance and take a paste; sliders, counters and tabs update;
   rotary phones dial by drag and lift by tap ([data-tl-rotary]).
   Checkboxes and text fields are native inputs and need nothing. */
(function () {
  var CHECK = '<svg class="tl-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
  function setSwitch(btn, on) {
    btn.setAttribute('aria-checked', on ? 'true' : 'false');
    btn.classList.toggle('is-on', on);
    var thumb = btn.querySelector('.tl-switch__thumb');
    if (thumb) thumb.innerHTML = on ? CHECK : '';
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.tl-switch');
    if (!btn || btn.disabled) return;
    var on = btn.getAttribute('aria-checked') !== 'true';
    setSwitch(btn, on);
    btn.dispatchEvent(new CustomEvent('tl-change', { bubbles: true, detail: { checked: on } }));
  });
  // Sheets: <button data-tl-open="sheet-id">, any [data-tl-close] inside, the scrim, or Escape closes.
  // A closed sheet is a .tl-sheet-scrim with the hidden attribute.
  var lastOpener = null;
  function openSheet(id, opener) {
    var s = document.getElementById(id); if (!s) return;
    lastOpener = opener || null; s.hidden = false;
    var f = s.querySelector('button, [href], input, select, textarea'); if (f) f.focus();
  }
  function closeSheet(s) { if (!s || s.hidden) return; s.hidden = true; if (lastOpener) lastOpener.focus(); }
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target : null; if (!t) return;
    var o = t.closest('[data-tl-open]'); if (o) { openSheet(o.getAttribute('data-tl-open'), o); return; }
    var c = t.closest('[data-tl-close], .tl-sheet__close'); if (c) { closeSheet(c.closest('.tl-sheet-scrim')); return; }
    if (t.classList.contains('tl-sheet-scrim')) { closeSheet(t); return; }
    // List and detail: a [data-tl-detail] row shows the detail pane; .tl-listdetail__back returns to the list.
    var d = t.closest('[data-tl-detail]'); if (d) { var ld = d.closest('.tl-listdetail'); if (ld) ld.classList.add('is-detail'); return; }
    var b = t.closest('.tl-listdetail__back'); if (b) { var l2 = b.closest('.tl-listdetail'); if (l2) l2.classList.remove('is-detail'); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open = document.querySelectorAll('.tl-sheet-scrim:not([hidden])'); if (open.length) closeSheet(open[open.length - 1]);
  });
  // Menus: a trigger with data-tl-menu="panel-id" toggles the .tl-menu__panel with that id.
  // Outside clicks and Escape close it; arrow keys move between items; choosing an item closes it.
  function menuItems(panel) { return Array.prototype.slice.call(panel.querySelectorAll('.tl-menu__item')); }
  function setMenu(trigger, open) {
    var panel = document.getElementById(trigger.getAttribute('data-tl-menu')); if (!panel) return;
    panel.hidden = !open; trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) { var first = menuItems(panel)[0]; if (first) first.focus(); }
  }
  function closeMenus(except) {
    document.querySelectorAll('[data-tl-menu][aria-expanded="true"]').forEach(function (t) { if (t !== except) setMenu(t, false); });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-tl-menu]');
    if (t) { var open = t.getAttribute('aria-expanded') !== 'true'; closeMenus(t); setMenu(t, open); return; }
    var item = e.target.closest && e.target.closest('.tl-menu__item');
    if (item || !(e.target.closest && e.target.closest('.tl-menu__panel'))) closeMenus();
  });
  document.addEventListener('keydown', function (e) {
    var panel = document.activeElement && document.activeElement.closest && document.activeElement.closest('.tl-menu__panel');
    if (e.key === 'Escape') {
      var openT = document.querySelector('[data-tl-menu][aria-expanded="true"]');
      if (openT) { setMenu(openT, false); openT.focus(); }
      return;
    }
    if (!panel || (e.key !== 'ArrowDown' && e.key !== 'ArrowUp')) return;
    e.preventDefault();
    var items = menuItems(panel), i = items.indexOf(document.activeElement);
    items[(i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus();
  });

  // Toasts: TreelineUI.toast("Request sent", { tone: "success", action: "Undo", onAction: fn, duration: 5000 }).
  // Needs a <div class="tl-toasts" aria-live="polite"></div> as the last child of .tl-app (one is added if missing).
  var ICON = function (paths) { return '<svg class="tl-icon tl-toast__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>'; };
  var TOAST_ICONS = {
    neutral: ICON('<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5v.01"/>'),
    success: ICON('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
    warning: ICON('<path d="M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z"/><path d="M12 9.5v4.5"/><path d="M12 17v.01"/>')
  };
  function toast(message, opts) {
    opts = opts || {};
    var region = document.querySelector('.tl-toasts');
    if (!region) { region = document.createElement('div'); region.className = 'tl-toasts'; region.setAttribute('aria-live', 'polite'); (document.querySelector('.tl-app') || document.body).appendChild(region); }
    var tone = opts.tone || 'neutral', el = document.createElement('div');
    el.className = 'tl-toast tl-toast--' + tone; el.setAttribute('role', 'status');
    el.innerHTML = (TOAST_ICONS[tone] || TOAST_ICONS.neutral) + '<span class="tl-toast__msg"></span>';
    el.querySelector('.tl-toast__msg').textContent = message;
    function leave() { el.classList.add('is-leaving'); setTimeout(function () { el.remove(); }, 220); }
    if (opts.action) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'tl-toast__action'; b.textContent = opts.action;
      b.addEventListener('click', function () { if (opts.onAction) opts.onAction(); leave(); }); el.appendChild(b);
    }
    region.appendChild(el);
    setTimeout(leave, opts.duration || (opts.action ? 8000 : 5000));
    return el;
  }
  // Any button with data-tl-toast="message" (optional data-tl-toast-tone) shows a toast when clicked.
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-tl-toast]');
    if (t) toast(t.getAttribute('data-tl-toast'), { tone: t.getAttribute('data-tl-toast-tone') || undefined });
  });
  // Alerts: any [data-tl-dismiss] inside a .tl-alert removes it.
  document.addEventListener('click', function (e) {
    var d = e.target.closest && e.target.closest('.tl-alert [data-tl-dismiss]'); if (d) d.closest('.tl-alert').remove();
  });
  // Password fields: [data-tl-password="input-id"] shows and hides the password.
  var EYE = '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>';
  var EYE_OFF = '<path d="M9.9 5.8A9.9 9.9 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.6 3.4M6.5 7.6A16 16 0 0 0 2.5 12S6 18.5 12 18.5a9.6 9.6 0 0 0 4.4-1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><path d="M3 3l18 18"/>';
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-tl-password]'); if (!b) return;
    var input = document.getElementById(b.getAttribute('data-tl-password')); if (!input) return;
    var show = input.type === 'password'; input.type = show ? 'text' : 'password';
    b.setAttribute('aria-pressed', show ? 'true' : 'false'); b.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    var svg = b.querySelector('svg'); if (svg) svg.innerHTML = show ? EYE_OFF : EYE;
  });

  // Code inputs ([data-tl-code]): typing moves to the next box, Backspace goes back, pasting fills every box.
  // The whole code is on the fieldset as data-value, and a "tl-code" event fires when every box is full.
  function codeBoxes(f) { return Array.prototype.slice.call(f.querySelectorAll('.tl-code__box')); }
  function codeSync(f) {
    var v = codeBoxes(f).map(function (b) { return b.value; }).join(''); f.setAttribute('data-value', v);
    if (v.length === codeBoxes(f).length) f.dispatchEvent(new CustomEvent('tl-code', { bubbles: true, detail: { value: v } }));
  }
  document.addEventListener('input', function (e) {
    var box = e.target; if (!box.classList || !box.classList.contains('tl-code__box')) return;
    var f = box.closest('[data-tl-code]'), all = codeBoxes(f), i = all.indexOf(box);
    box.value = box.value.replace(/\D/g, '').slice(-1);
    if (box.value && all[i + 1]) all[i + 1].focus();
    codeSync(f);
  });
  document.addEventListener('keydown', function (e) {
    var box = e.target; if (!box.classList || !box.classList.contains('tl-code__box')) return;
    var all = codeBoxes(box.closest('[data-tl-code]')), i = all.indexOf(box);
    if (e.key === 'Backspace' && !box.value && all[i - 1]) { all[i - 1].focus(); all[i - 1].value = ''; e.preventDefault(); }
    if (e.key === 'ArrowLeft' && all[i - 1]) all[i - 1].focus();
    if (e.key === 'ArrowRight' && all[i + 1]) all[i + 1].focus();
  });
  document.addEventListener('paste', function (e) {
    var box = e.target; if (!box.classList || !box.classList.contains('tl-code__box')) return;
    var f = box.closest('[data-tl-code]'), all = codeBoxes(f), digits = (e.clipboardData.getData('text') || '').replace(/\D/g, '');
    if (!digits) return; e.preventDefault();
    all.forEach(function (b, i) { b.value = digits[i] || ''; });
    (all[Math.min(digits.length, all.length) - 1] || box).focus(); codeSync(f);
  });

  // Sliders ([data-tl-slider="output-id"]): keep the canopy fill and the value label in step. data-tl-unit adds a unit.
  function sliderSync(r) {
    var min = +r.min || 0, max = +r.max || 100, pct = (r.value - min) / (max - min) * 100;
    r.style.setProperty('--tl-fill', pct + '%');
    var out = document.getElementById(r.getAttribute('data-tl-slider')), unit = r.getAttribute('data-tl-unit');
    var text = r.value + (unit ? ' ' + unit : ''); if (out) out.textContent = text; r.setAttribute('aria-valuetext', text);
  }
  document.addEventListener('input', function (e) { if (e.target.matches && e.target.matches('[data-tl-slider]')) sliderSync(e.target); });

  // Textareas with a counter ([data-tl-count="counter-id"] and maxlength).
  document.addEventListener('input', function (e) {
    var t = e.target; if (!t.matches || !t.matches('[data-tl-count]')) return;
    var c = document.getElementById(t.getAttribute('data-tl-count')); if (c) c.textContent = t.value.length + ' / ' + t.maxLength;
  });

  // Tabs ([data-tl-tabs]): click or arrow keys pick a tab; Home and End jump to the ends.
  function selectTab(tab) {
    var root = tab.closest('[data-tl-tabs]');
    root.querySelectorAll('[role="tab"]').forEach(function (t) {
      var on = t === tab; t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1;
      var panel = document.getElementById(t.getAttribute('aria-controls')); if (panel) panel.hidden = !on;
    });
  }
  document.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('[data-tl-tabs] [role="tab"]'); if (t) selectTab(t); });
  document.addEventListener('keydown', function (e) {
    var t = e.target.closest && e.target.closest('[data-tl-tabs] [role="tab"]'); if (!t) return;
    var all = Array.prototype.slice.call(t.parentNode.querySelectorAll('[role="tab"]')), i = all.indexOf(t), n = null;
    if (e.key === 'ArrowRight') n = all[(i + 1) % all.length];
    if (e.key === 'ArrowLeft') n = all[(i - 1 + all.length) % all.length];
    if (e.key === 'Home') n = all[0]; if (e.key === 'End') n = all[all.length - 1];
    if (n) { e.preventDefault(); n.focus(); selectTab(n); }
  });

  // ---------- Rotary phone: drag-to-dial and lift/hang-up ----------
  // Works on markup from components/RotaryPhone.html (or the React RotaryPhone).
  // Fires on the .tl-rotary element:
  //   "tl-rotary-hook"  { offHook }            when the handset is lifted or hung up
  //   "tl-rotary-pulse" { digit, pulse }       once per pulse while the dial returns (for click sounds)
  //   "tl-rotary-digit" { digit, offHook }     when a dialed digit finishes returning
  var ROTARY = {"cx": 200, "cy": 292, "r": 73, "sq": 0.93, "stop": 32, "holeK": 0.79, "holeR": 11.5, "gap": 30, "holeAngle": {"1": -28, "2": -58, "3": -88, "4": -118, "5": -148, "6": -178, "7": -208, "8": -238, "9": -268, "0": -298}, "travel": {"1": 60, "2": 90, "3": 120, "4": 150, "5": 180, "6": 210, "7": 240, "8": 270, "9": 300, "0": 330}, "cordStart": [70, 352], "cordEnd": [62, 192], "lift": {"tx": 4, "ty": -74, "rot": 4, "ox": 94, "oy": 150}};
  function rotaryCordPath(x1, y1, x2, y2) {
    var loops = 16, r = 6.5, n = loops * 12, dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    var nx = -dy / L, ny = dx / L, d = "";
    for (var i = 0; i <= n; i++) {
      var t = i / n, sag = Math.sin(Math.PI * t) * Math.min(60, L * 0.35), a = 2 * Math.PI * loops * t;
      var bx = x1 + dx * t, by = y1 + dy * t + sag;
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
    var api = { lift: function () { setHook(true); }, hangUp: function () { setHook(false); }, dial: dialDigit,
                isOffHook: function () { return state.offHook; }, setHook: setHook };
    root.__tlRotary = api;
    return api;
  }

  function initRotaries() { document.querySelectorAll('[data-tl-rotary]').forEach(function (el) { attachRotary(el); }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initRotaries); else initRotaries();

  window.TreelineUI = { rotary: attachRotary, setSwitch: setSwitch, openSheet: openSheet, closeSheet: closeSheet, toast: toast, openMenu: function (t) { setMenu(t, true); }, closeMenus: closeMenus };
})();
