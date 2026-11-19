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
  var ROTARY = {"cx": 200, "cy": 292, "r": 73, "sq": 0.93, "stop": 32, "holeK": 0.79, "holeR": 11.5, "gap": 30, "holeAngle": {"1": -28, "2": -58, "3": -88, "4": -118, "5": -148, "6": -178, "7": -208, "8": -238, "9": -268, "0": -298}, "travel": {"1": 60, "2": 90, "3": 120, "4": 150, "5": 180, "6": 210, "7": 240, "8": 270, "9": 300, "0": 330}, "cordStart": [68, 350], "cordEnd": [70, 206], "lift": {"tx": -4, "ty": -50, "rot": 24, "ox": 318, "oy": 200}};
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
    // The line lamp on the front: steady green when connected, pulsing orange while connecting, blinking red when
    // it can't connect; it flashes green while it rings. setLine(true | false | "on" | "connecting" | "off").
    function setLine(state) { root.setAttribute("data-line", state === "connecting" ? "connecting" : (state === true || state === "on") ? "on" : "off"); }
    var api = { lift: function () { setHook(true); }, hangUp: function () { setHook(false); }, dial: dialDigit, setRinging: setRinging, isRinging: function () { return root.classList.contains("is-ringing"); }, setLine: setLine, isLineOn: function () { return root.getAttribute("data-line") === "on"; }, lineState: function () { return root.getAttribute("data-line") || "off"; },
                isOffHook: function () { return state.offHook; }, setHook: setHook };
    root.__tlRotary = api;
    return api;
  }

  // >>> desk
  // ---------- Softphone desk: the phone on its table, with the room's things to pick up ----------
  // Markup: [data-tl-desk] with data-contacts='[{"name":"The Parks","number":"3317"}]'.
  // [data-desk-open="book|coffee|card|licenses"] picks a thing up; [data-desk-close] puts it back.
  // The card file (.tl-desk__cardfile) flips to the next string.
  // Events on the wrapper: "tl-desk-card" { index, contact }, "tl-desk-open" { item }, "tl-desk-close" { item }.
  // The treehouse's name, written across the top of the kid's drawing: long names are written smaller.
  function deskNameSize(name) { var n = Math.max(1, String(name || "").length); return Math.max(13, Math.min(26, 150 / (n * 0.42))).toFixed(1); }
  function attachDesk(root) {
    if (root.__tlDesk) return root.__tlDesk;
    var list = [];
    try { list = JSON.parse(root.getAttribute("data-contacts") || "[]") || []; } catch (e) { list = []; }
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // The room is drawn three ways (wide, portrait, tall) and CSS shows one, so every word is set in each.
    var i = 0, btn = root.querySelector(".tl-desk__cardfile");
    function all(sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); }
    function emit(name, detail) { root.dispatchEvent(new CustomEvent(name, { bubbles: true, detail: detail })); }
    function show() {
      var c = list[i];
      all(".tl-desk__cardname", function (n) { n.textContent = c ? c.name : "No strings yet"; });
      all(".tl-desk__cardnum", function (n) { n.textContent = c ? c.number : "ask a grown-up"; n.setAttribute("font-size", c ? "29" : "21"); });
      all(".tl-desk__cardcount", function (n) { n.textContent = list.length > 1 ? (i + 1) + " of " + list.length : ""; });
      if (btn) btn.setAttribute("aria-label", c
        ? "Phone book card: " + c.name + ", " + String(c.number).split("").join(" ") + (list.length > 1 ? ". Card " + (i + 1) + " of " + list.length + ". Tap for the next card." : ".")
        : "Phone book: no strings yet. A grown-up can add one in the parent app.");
    }

    // ---- the card file turns like a real rotary file. Forward: the front card tips toward you off the rod and
    // drops away; the next card swings up out of the fan behind and settles upright with a small tick; the fan
    // rocks with it. Back: the same, reversed. Reduced motion: the card just changes.
    var flipping = 0;
    function go(step) {
      if (list.length < 2) return;
      var animate = !reduce && typeof Element.prototype.animate === "function";
      var fwd = step > 0, lag = flipping * 50;
      if (animate) {
        all(".tl-desk__card", function (card) {
          if (!card.getBoundingClientRect().width) return;                  // a hidden arrangement
          var old = card.cloneNode(true);                                   // the card going away, still showing its words
          old.classList.remove("tl-desk__card"); old.classList.add("tl-desk__card--falling");
          Array.prototype.forEach.call(old.querySelectorAll("[class]"), function (n) { n.removeAttribute("class"); });   // keep its old words
          card.parentNode.appendChild(old);
          var away = fwd
            ? [{ transform: "none", opacity: 1 }, { transform: "translateY(2%) scaleY(.35)", opacity: 1, offset: .55 }, { transform: "translateY(9%) scaleY(-.12)", opacity: 0 }]
            : [{ transform: "none", opacity: 1 }, { transform: "translate(5%, -3%) scaleY(.82) skewX(-10deg)", opacity: .6, offset: .6 }, { transform: "translate(9%, -5%) scaleY(.7) skewX(-16deg)", opacity: 0 }];
          var a = old.animate(away, { duration: 320, delay: lag, easing: "cubic-bezier(.45,0,.8,.45)", fill: "both" });
          a.onfinish = function () { old.remove(); };
          var come = fwd
            ? [{ transform: "translate(9%, -5%) scaleY(.7) skewX(-16deg)", opacity: 0 }, { transform: "translate(2%, -1%) scaleY(.95) skewX(-4deg)", opacity: 1, offset: .55 }, { transform: "translateY(-1.5%) scaleY(1.02)", offset: .82 }, { transform: "none", opacity: 1 }]
            : [{ transform: "translateY(9%) scaleY(-.12)", opacity: 0 }, { transform: "translateY(2%) scaleY(.4)", opacity: 1, offset: .45 }, { transform: "translateY(-1.5%) scaleY(1.02)", offset: .82 }, { transform: "none", opacity: 1 }];
          card.animate(come, { duration: 420, delay: lag + 140, easing: "cubic-bezier(.2,.7,.3,1)", fill: "backwards" });
        });
        all(".tl-cf-fan", function (f) { f.animate([{ transform: "none" }, { transform: "rotate(" + (fwd ? -3 : 3) + "deg)", offset: .4 }, { transform: "none" }], { duration: 520, delay: lag, easing: "ease-in-out" }); });
      }
      flipping++; setTimeout(function () { flipping = Math.max(0, flipping - 1); }, 480);
      i = (i + step + list.length) % list.length; show();
      emit("tl-desk-card", { index: i, contact: list[i] });
    }
    if (btn) {
      btn.addEventListener("click", function () { go(1); });
      btn.addEventListener("keydown", function (e) { if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); go(1); } if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); go(-1); } });
    }

    // ---- picking things up: the thing flies from where it sits to the middle, and back again
    var opened = null;
    function fly(el, measure, from, turn, dir, done) {
      if (reduce || typeof el.animate !== "function") { if (done) done(); return; }
      var to = measure.getBoundingClientRect();
      var s = Math.max(.05, Math.min(from.width / to.width, from.height / to.height));
      var dx = from.left + from.width / 2 - (to.left + to.width / 2), dy = from.top + from.height / 2 - (to.top + to.height / 2);
      var frames = [{ transform: "translate(" + dx + "px," + dy + "px) scale(" + s + ") rotate(" + turn + "deg)", opacity: .85 },
                    { transform: "translate(0,-1.5%) scale(1.03) rotate(" + (-turn * .2) + "deg)", opacity: 1, offset: .72 },
                    { transform: "none", opacity: 1 }];
      if (dir < 0) frames.reverse();
      var a = el.animate(frames, { duration: dir > 0 ? 480 : 380, easing: dir > 0 ? "cubic-bezier(.2,.8,.25,1)" : "cubic-bezier(.5,0,.6,1)", fill: "both" });
      a.onfinish = function () { if (done) done(); a.cancel(); };
    }
    function focusables(el) { return Array.prototype.filter.call(el.querySelectorAll("a[href], button:not([disabled])"), function (n) { return n.getClientRects().length; }); }
    function open(kind, hot) {
      if (opened) return;
      var el = root.querySelector(".tl-desk__look--" + kind); if (!el) return;
      el.hidden = false; root.classList.add("is-looking");
      requestAnimationFrame(function () { el.classList.add("is-in"); });
      opened = { el: el, hot: hot, kind: kind };
      var from = hot.getBoundingClientRect(), turn = Number(hot.getAttribute("data-turn")) || 0;
      if (kind === "book") {
        setPage(0, true);
        fly(el.querySelector(".tl-book__fly"), el.querySelector(".tl-book__sheet"), from, turn, 1, function () { setTimeout(function () { if (opened && opened.kind === "book") setPage(1); }, 60); });
        if (reduce) setPage(1, true);
        var nx = el.querySelector(".tl-book__next"); if (nx) nx.focus({ preventScroll: true });
      } else {
        fly(el.querySelector(".tl-desk__held"), el.querySelector(".tl-desk__held"), from, turn, 1);
        var art = el.querySelector(".tl-desk__heldart"); if (art) art.focus({ preventScroll: true });
      }
      emit("tl-desk-open", { item: kind });
    }
    function close() {
      var o = opened; if (!o) return; opened = null;
      o.el.classList.remove("is-in");
      var from = o.hot.getBoundingClientRect(), turn = Number(o.hot.getAttribute("data-turn")) || 0;
      function done() { o.el.hidden = true; root.classList.remove("is-looking"); o.hot.focus({ preventScroll: true }); emit("tl-desk-close", { item: o.kind }); }
      if (o.kind === "book") {
        var wasOpen = page > 0; setPage(0, reduce);
        setTimeout(function () { fly(o.el.querySelector(".tl-book__fly"), o.el.querySelector(".tl-book__sheet"), from, turn, -1, done); }, wasOpen && !reduce ? 640 : 0);
      } else fly(o.el.querySelector(".tl-desk__held"), o.el.querySelector(".tl-desk__held"), from, turn, -1, done);
    }

    // ---- the book: leaves turn over from right to left
    var look = root.querySelector(".tl-desk__look--book"), page = 0, sheets = look ? look.querySelectorAll(".tl-book__sheet") : [];
    var bookEl = look && look.querySelector(".tl-book"), count = look && look.querySelector(".tl-book__count");
    var prevB = look && look.querySelector(".tl-book__prev"), nextB = look && look.querySelector(".tl-book__next");
    function setPage(n, instant) {
      if (!look) return;
      n = Math.max(0, Math.min(sheets.length, n));
      if (opened && opened.kind === "book" && n === 0 && page > 0 && !instant) { /* closing the cover */ }
      var moving = [];
      if (instant) { bookEl.classList.add("is-instant"); }
      Array.prototype.forEach.call(sheets, function (sh, k) {
        var turned = k < n;
        if (turned !== sh.classList.contains("is-turned")) moving.push(sh);
        sh.classList.toggle("is-turned", turned);
        sh.__z = turned ? k + 1 : sheets.length - k;
        sh.style.zIndex = sh.__z;
      });
      if (!instant && !reduce) {
        moving.forEach(function (sh) { sh.style.zIndex = 100; });
        setTimeout(function () { moving.forEach(function (sh) { sh.style.zIndex = sh.__z; }); }, 620);
      }
      bookEl.classList.toggle("is-open", n > 0);
      if (instant) { void bookEl.offsetWidth; bookEl.classList.remove("is-instant"); }
      page = n;
      Array.prototype.forEach.call(sheets, function (sh, k) {
        sh.querySelector(".tl-book__face--front").setAttribute("aria-hidden", k === n ? "false" : "true");
        sh.querySelector(".tl-book__face--back").setAttribute("aria-hidden", k === n - 1 ? "false" : "true");
      });
      var base = look.querySelector(".tl-book__base"); if (base) base.setAttribute("aria-hidden", n === sheets.length ? "false" : "true");
      if (prevB) prevB.disabled = n <= 1;
      if (nextB) nextB.disabled = n >= sheets.length;
      if (count) count.textContent = n === 0 ? "" : n === sheets.length ? "The end" : "Pages " + (2 * n - 1) + "–" + (2 * n);
    }
    if (look) {
      if (prevB) prevB.addEventListener("click", function () { setPage(page - 1); });
      if (nextB) nextB.addEventListener("click", function () { setPage(page + 1); });
      var sx = null;
      bookEl.addEventListener("pointerdown", function (e) { sx = e.clientX; });
      bookEl.addEventListener("pointerup", function (e) {
        if (sx === null) return; var dx = e.clientX - sx; sx = null;
        if (Math.abs(dx) > 40) return setPage(page + (dx < 0 ? 1 : -1));
        var r = bookEl.getBoundingClientRect();                        // a tap: the right page turns forward, the left back
        var next = page + (e.clientX > r.left + r.width / 2 ? 1 : -1);
        if (next >= 1) setPage(next);
      });
    }

    root.addEventListener("click", function (e) {
      var h = e.target.closest("[data-desk-open]");
      if (h && root.contains(h)) { e.preventDefault(); open(h.getAttribute("data-desk-open"), h); return; }
      if (e.target.closest("[data-desk-close]")) { e.preventDefault(); close(); }
    });
    root.addEventListener("keydown", function (e) {
      if (!opened) return;
      if (e.key === "Escape") { e.preventDefault(); close(); return; }
      if (opened.kind === "book" && (e.key === "ArrowRight" || e.key === "ArrowLeft")) { e.preventDefault(); var n = page + (e.key === "ArrowRight" ? 1 : -1); if (n >= 1) setPage(n); return; }
      if (e.key === "Tab") {                                           // keep the keyboard in the open thing
        var f = focusables(opened.el); if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
    show();
    var online = true;
    // The line: lights the lamp on the phone on the table (the kit's demo starts it lit).
    function setOnline(on) { var v = on === "connecting" ? "connecting" : on ? "on" : "off"; online = v === "on"; all("[data-tl-rotary]", function (r) { r.setAttribute("data-line", v); }); }
    if (!root.querySelector('[data-tl-rotary][data-line]')) setOnline(true);

    // Words the app fills in: the name on the kid's drawing, the sticky note, and where the cards' links go.
    function setName(name) { name = String(name || ""); all(".tl-desk__name", function (n) { n.textContent = name; n.setAttribute("font-size", deskNameSize(name)); }); }
    function setQuiet(text) { all(".tl-desk__quiettext", function (n) { n.textContent = String(text || ""); }); }
    function setLinks(l) {
      l = l || {};
      var c = root.querySelector(".tl-desk__heldart--coffee"), k = root.querySelector(".tl-desk__heldart--card"), w = root.querySelector(".tl-desk__heldart--licenses");
      if (c && l.coffee) { c.setAttribute("href", l.coffee); if (l.coffee.charAt(0) !== "#") { c.setAttribute("target", "_blank"); c.setAttribute("rel", "noopener"); } }
      if (k && l.email) k.setAttribute("href", "mailto:" + l.email);
      if (w && l.licenses) w.setAttribute("href", l.licenses);
    }
    var api = { next: function () { go(1); }, prev: function () { go(-1); }, setContacts: function (c) { list = c || []; i = 0; show(); }, index: function () { return i; },
                setName: setName, setQuiet: setQuiet, setLinks: setLinks, setOnline: setOnline, isOnline: function () { return online; },
                open: function (kind) { var h = root.querySelector('[data-desk-open="' + kind + '"]'); if (h) open(kind, h); }, close: close,
                isOpen: function () { return opened ? opened.kind : null; } };
    root.__tlDesk = api;
    return api;
  }
  // <<< desk
  function initRotaries() { document.querySelectorAll('[data-tl-rotary]').forEach(function (el) { attachRotary(el); }); document.querySelectorAll('[data-tl-desk]').forEach(function (el) { attachDesk(el); }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initRotaries); else initRotaries();

  window.TreelineUI = { rotary: attachRotary, desk: attachDesk, setSwitch: setSwitch, openSheet: openSheet, closeSheet: closeSheet, toast: toast, openMenu: function (t) { setMenu(t, true); }, closeMenus: closeMenus };
})();
