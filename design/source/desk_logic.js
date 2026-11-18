  // ---------- Softphone desk: the phone on its table, with the paper props as links ----------
  // Markup: [data-tl-desk] with data-contacts='[{"name":"The Parks","number":"3317"}]'.
  // The card file (.tl-desk__cardfile) flips to the next string; events: "tl-desk-card" { index, contact }.
  function deskNameSize(name) { var n = Math.max(1, String(name || "").length); return Math.max(11, Math.min(21, (270 / n - 3) / 0.6)).toFixed(1); }
  function attachDesk(root) {
    if (root.__tlDesk) return root.__tlDesk;
    var list = [];
    try { list = JSON.parse(root.getAttribute("data-contacts") || "[]") || []; } catch (e) { list = []; }
    var i = 0, btn = root.querySelector(".tl-desk__cardfile"), card = root.querySelector(".tl-desk__card");
    var nm = root.querySelector(".tl-desk__cardname"), num = root.querySelector(".tl-desk__cardnum"), cnt = root.querySelector(".tl-desk__cardcount");
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    function show() {
      var c = list[i];
      if (nm) nm.textContent = c ? c.name : "No strings yet";
      if (num) num.textContent = c ? c.number : "ask a grown-up";
      if (num) num.setAttribute("font-size", c ? "29" : "21");
      if (cnt) cnt.textContent = list.length > 1 ? (i + 1) + " of " + list.length : "";
      if (btn) btn.setAttribute("aria-label", c
        ? "Phone book card: " + c.name + ", " + String(c.number).split("").join(" ") + (list.length > 1 ? ". Card " + (i + 1) + " of " + list.length + ". Tap for the next card." : ".")
        : "Phone book: no strings yet. A grown-up can add one in the parent app.");
    }
    function go(step) {
      if (list.length < 2) return;
      var next = function () { i = (i + step + list.length) % list.length; show(); root.dispatchEvent(new CustomEvent("tl-desk-card", { bubbles: true, detail: { index: i, contact: list[i] } })); };
      if (reduce || !card) return next();
      card.classList.remove("is-flipping"); void card.getBoundingClientRect(); card.classList.add("is-flipping");
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
