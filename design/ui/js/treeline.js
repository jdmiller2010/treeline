/* Treeline UI: the only behavior plain HTML needs.
   Switches toggle on click and fire a "tl-change" event with { checked }.
   Sheets open and close; list and detail switches panes on narrow screens;
   menus open, close and take arrow keys; toasts appear and leave; alerts can be dismissed;
   passwords show and hide; code boxes advance and take a paste; sliders, counters and tabs update.
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

  window.TreelineUI = { setSwitch: setSwitch, openSheet: openSheet, closeSheet: closeSheet, toast: toast, openMenu: function (t) { setMenu(t, true); }, closeMenus: closeMenus };
})();
