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

    // ---- the card file: the front card tips forward over the rod, a blank one after it, and the next is underneath
    var flipping = 0;
    function go(step) {
      if (list.length < 2) return;
      var animate = !reduce && typeof Element.prototype.animate === "function";
      if (animate) all(".tl-desk__card", function (card) {
        if (!card.getBoundingClientRect().width) return;                    // a hidden arrangement
        [1, 0].forEach(function (k) {
          var c = card.cloneNode(true);
          c.classList.remove("tl-desk__card"); c.classList.add("tl-desk__card--falling");
          if (k) Array.prototype.forEach.call(c.querySelectorAll("text"), function (t) { t.textContent = ""; });
          card.parentNode.appendChild(c);
          var a = c.animate([
            { transform: "none", opacity: 1 },
            { transform: "translateY(3%) scaleY(.06)", opacity: 1, offset: .62 },
            { transform: "translateY(10%) scaleY(-.18)", opacity: 0 }], { duration: 300, delay: k * 110 + flipping * 40, easing: "cubic-bezier(.5,0,.75,.4)", fill: "both" });
          a.onfinish = function () { c.remove(); };
        });
      });
      flipping++; setTimeout(function () { flipping = Math.max(0, flipping - 1); }, 420);
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
    function setOnline(on) { online = !!on; all("[data-tl-rotary]", function (r) { r.setAttribute("data-line", online ? "on" : "off"); }); }
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
