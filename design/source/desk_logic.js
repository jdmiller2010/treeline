  // ---------- Softphone desk: the phone on its table, with the paper props as links ----------
  // Markup: [data-tl-desk] with data-contacts='[{"name":"The Parks","number":"3317"}]'.
  // The card file (.tl-desk__cardfile) flips to the next string; events: "tl-desk-card" { index, contact }.
  // The treehouse's name, written across the top of the kid's drawing: long names are written smaller.
  function deskNameSize(name) { var n = Math.max(1, String(name || "").length); return Math.max(13, Math.min(26, 150 / (n * 0.42))).toFixed(1); }
  function attachDesk(root) {
    if (root.__tlDesk) return root.__tlDesk;
    var list = [];
    try { list = JSON.parse(root.getAttribute("data-contacts") || "[]") || []; } catch (e) { list = []; }
    // The room is drawn three ways (wide, portrait, tall) and CSS shows one, so every word is set in each.
    var i = 0, btn = root.querySelector(".tl-desk__cardfile");
    function all(sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); }
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    function show() {
      var c = list[i];
      all(".tl-desk__cardname", function (n) { n.textContent = c ? c.name : "No strings yet"; });
      all(".tl-desk__cardnum", function (n) { n.textContent = c ? c.number : "ask a grown-up"; n.setAttribute("font-size", c ? "29" : "21"); });
      all(".tl-desk__cardcount", function (n) { n.textContent = list.length > 1 ? (i + 1) + " of " + list.length : ""; });
      if (btn) btn.setAttribute("aria-label", c
        ? "Phone book card: " + c.name + ", " + String(c.number).split("").join(" ") + (list.length > 1 ? ". Card " + (i + 1) + " of " + list.length + ". Tap for the next card." : ".")
        : "Phone book: no strings yet. A grown-up can add one in the parent app.");
    }
    function go(step) {
      if (list.length < 2) return;
      var next = function () { i = (i + step + list.length) % list.length; show(); root.dispatchEvent(new CustomEvent("tl-desk-card", { bubbles: true, detail: { index: i, contact: list[i] } })); };
      if (reduce) return next();
      all(".tl-desk__card", function (n) { n.classList.remove("is-flipping"); void n.getBoundingClientRect(); n.classList.add("is-flipping"); });
      setTimeout(next, 150);
    }
    if (btn) {
      btn.addEventListener("click", function () { go(1); });
      btn.addEventListener("keydown", function (e) { if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); go(1); } if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); go(-1); } });
    }
    show();
    var api = { next: function () { go(1); }, prev: function () { go(-1); }, setContacts: function (c) { list = c || []; i = 0; show(); }, index: function () { return i; } };
    root.__tlDesk = api;
    return api;
  }
