/* @ds-bundle: {"format": 4, "namespace": "Treeline", "components": [{"name": "Icon"}, {"name": "Button"}, {"name": "IconButton"}, {"name": "Tag"}, {"name": "Presence"}, {"name": "Avatar"}, {"name": "Switch"}, {"name": "Checkbox"}, {"name": "TextField"}, {"name": "Card"}, {"name": "FriendRow"}, {"name": "ApprovalCard"}, {"name": "QuietHours"}, {"name": "CallLogItem"}, {"name": "Illustration"}, {"name": "EmptyState"}, {"name": "LeafDivider"}, {"name": "LeafLoader"}, {"name": "NavBar"}, {"name": "AppBar"}, {"name": "AppShell"}, {"name": "Sheet"}, {"name": "Alert"}, {"name": "Toast"}, {"name": "Select"}, {"name": "TimeField"}, {"name": "TimeRange"}, {"name": "SegmentedControl"}, {"name": "Menu"}, {"name": "RadioGroup"}, {"name": "Textarea"}, {"name": "PasswordField"}, {"name": "CodeInput"}, {"name": "Slider"}, {"name": "Badge"}, {"name": "Steps"}, {"name": "ProgressBar"}, {"name": "DescriptionList"}, {"name": "Skeleton"}, {"name": "Disclosure"}, {"name": "Accordion"}, {"name": "StatTile"}, {"name": "Tabs"}]} */
(function () {
  var React = window.React, h = React.createElement;
  var ICONS = {"phone": ["<path d=\"M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z\"/>", "<path d=\"M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z\"/>", "<circle cx=\"12\" cy=\"15.2\" r=\"2.6\"/>"], "phone-incoming": ["<path d=\"M2.5 10.4v-.7C2.5 7.8 5.6 6.3 9.5 6.3s7 1.5 7 3.4v.7a.8.8 0 0 1-.8.8h-2a.8.8 0 0 1-.8-.8V9.3H6.1v1.1a.8.8 0 0 1-.8.8h-2a.8.8 0 0 1-.8-.8z\"/>", "<path d=\"M6.2 11.2h6.6l2.9 7a.8.8 0 0 1-.7 1.1H4a.8.8 0 0 1-.7-1.1z\"/>", "<circle cx=\"9.5\" cy=\"15.5\" r=\"2.1\"/>", "<path d=\"M21.5 2.5l-5 5\"/>", "<path d=\"M16.5 3.5v4h4\"/>"], "phone-outgoing": ["<path d=\"M2.5 10.4v-.7C2.5 7.8 5.6 6.3 9.5 6.3s7 1.5 7 3.4v.7a.8.8 0 0 1-.8.8h-2a.8.8 0 0 1-.8-.8V9.3H6.1v1.1a.8.8 0 0 1-.8.8h-2a.8.8 0 0 1-.8-.8z\"/>", "<path d=\"M6.2 11.2h6.6l2.9 7a.8.8 0 0 1-.7 1.1H4a.8.8 0 0 1-.7-1.1z\"/>", "<circle cx=\"9.5\" cy=\"15.5\" r=\"2.1\"/>", "<path d=\"M16.5 7.5l5-5\"/>", "<path d=\"M17.5 2.5h4v4\"/>"], "phone-off": ["<path d=\"M3.5 9.2V8.4C3.5 6.2 7.3 4.5 12 4.5s8.5 1.7 8.5 3.9v.8a1 1 0 0 1-1 1H17a1 1 0 0 1-1-1V8H8v1.2a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1z\"/>", "<path d=\"M8 10.2h8l3.5 8.3a1 1 0 0 1-.9 1.5H5.4a1 1 0 0 1-.9-1.5z\"/>", "<circle cx=\"12\" cy=\"15.2\" r=\"2.6\"/>", "<path d=\"M3 3l18 18\"/>"], "bell": ["<path d=\"M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z\"/>", "<path d=\"M10 20a2 2 0 0 0 4 0\"/>"], "moon": ["<path d=\"M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z\"/>"], "sun": ["<circle cx=\"12\" cy=\"12\" r=\"4\"/>", "<path d=\"M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4\"/>"], "pause": ["<path d=\"M9 5v14M15 5v14\"/>"], "check": ["<path d=\"M5 12.5l4.5 4.5L19 7.5\"/>"], "close": ["<path d=\"M6 6l12 12M18 6L6 18\"/>"], "plus": ["<path d=\"M12 5v14M5 12h14\"/>"], "clock": ["<circle cx=\"12\" cy=\"12\" r=\"9\"/>", "<path d=\"M12 7v5l3 2\"/>"], "leaf": ["<path d=\"M5 19c0-8 5-14 14-14 0 9-6 14-14 14z\"/>", "<path d=\"M5 19l8-8\"/>"], "users": ["<circle cx=\"9\" cy=\"8\" r=\"3\"/>", "<path d=\"M3 19a6 6 0 0 1 12 0\"/>", "<circle cx=\"17\" cy=\"9\" r=\"2.5\"/>", "<path d=\"M16.5 14.2A5 5 0 0 1 21 19\"/>"], "lock": ["<rect x=\"5\" y=\"11\" width=\"14\" height=\"9\" rx=\"2\"/>", "<path d=\"M8 11V8a4 4 0 0 1 8 0v3\"/>"], "chevron-right": ["<path d=\"M9 6l6 6-6 6\"/>"], "shield-check": ["<path d=\"M12 3l7 3v5c0 5-3 8.5-7 10-4-1.5-7-5-7-10V6z\"/>", "<path d=\"M9 12l2 2 4-4\"/>"], "ladder": ["<path d=\"M8 3v18M16 3v18M8 7.5h8M8 12h8M8 16.5h8\"/>"], "home": ["<path d=\"M4 11l8-6 8 6\"/>", "<path d=\"M6 10v9h12v-9\"/>", "<path d=\"M10 19v-5h4v5\"/>"], "chevron-down": ["<path d=\"M6 9l6 6 6-6\"/>"], "info": ["<circle cx=\"12\" cy=\"12\" r=\"9\"/>", "<path d=\"M12 11v5.5\"/>", "<path d=\"M12 7.5v.01\"/>"], "alert": ["<path d=\"M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z\"/>", "<path d=\"M12 9.5v4.5\"/>", "<path d=\"M12 17v.01\"/>"], "settings": ["<path d=\"M4 7h9M17 7h3M4 17h3M11 17h9\"/>", "<circle cx=\"15\" cy=\"7\" r=\"2\"/>", "<circle cx=\"9\" cy=\"17\" r=\"2\"/>"], "log-out": ["<path d=\"M10 4.5H6.5a1.5 1.5 0 0 0-1.5 1.5v12a1.5 1.5 0 0 0 1.5 1.5H10\"/>", "<path d=\"M15 8l4 4-4 4\"/>", "<path d=\"M19 12H9.5\"/>"], "more": ["<circle cx=\"6\" cy=\"12\" r=\"1.2\"/>", "<circle cx=\"12\" cy=\"12\" r=\"1.2\"/>", "<circle cx=\"18\" cy=\"12\" r=\"1.2\"/>"], "eye": ["<path d=\"M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z\"/>", "<circle cx=\"12\" cy=\"12\" r=\"3\"/>"], "eye-off": ["<path d=\"M9.9 5.8A9.9 9.9 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.6 3.4M6.5 7.6A16 16 0 0 0 2.5 12S6 18.5 12 18.5a9.6 9.6 0 0 0 4.4-1\"/>", "<path d=\"M9.9 9.9a3 3 0 0 0 4.2 4.2\"/>", "<path d=\"M3 3l18 18\"/>"], "trend-up": ["<path d=\"M4 16l5-5 4 4 7-7\"/>", "<path d=\"M15 8h5v5\"/>"]};

  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(" "); }

  // ---------- atoms ----------
  function Icon(p) {
    var size = p.size || 20, parts = ICONS[p.name] || [];
    return h("svg", {
      className: cx("tl-icon", p.className), width: size, height: size, viewBox: "0 0 24 24",
      fill: "none", stroke: "currentColor", strokeWidth: 1.75, strokeLinecap: "round", strokeLinejoin: "round",
      "aria-hidden": p.label ? undefined : true, role: p.label ? "img" : undefined, "aria-label": p.label,
      dangerouslySetInnerHTML: { __html: parts.join("") }
    });
  }

  function Button(p) {
    var variant = p.variant || "secondary", size = p.size || "md";
    var rest = Object.assign({}, p);
    ["variant", "size", "icon", "iconEnd", "fullWidth", "collapse", "className", "children"].forEach(function (k) { delete rest[k]; });
    var iconSize = size === "sm" ? 16 : 20;
    return h("button", Object.assign({ type: "button" }, rest, {
      className: cx("tl-btn", "tl-btn--" + variant, "tl-btn--" + size, p.fullWidth && "tl-btn--full", p.collapse && "tl-btn--collapse", p.className)
    }),
      p.icon ? h(Icon, { name: p.icon, size: iconSize }) : null,
      h("span", { className: "tl-btn__label" }, p.children),
      p.iconEnd ? h(Icon, { name: p.iconEnd, size: iconSize }) : null);
  }

  function IconButton(p) {
    var variant = p.variant || "quiet", size = p.size || "md";
    var rest = Object.assign({}, p);
    ["variant", "size", "icon", "label", "className"].forEach(function (k) { delete rest[k]; });
    return h("button", Object.assign({ type: "button" }, rest, {
      "aria-label": p.label, title: p.label,
      className: cx("tl-iconbtn", "tl-btn--" + variant, "tl-iconbtn--" + size, p.className)
    }), h(Icon, { name: p.icon, size: size === "sm" ? 16 : size === "lg" ? 24 : 20 }));
  }

  function Tag(p) {
    var tone = p.tone || "neutral";
    return h("span", { className: cx("tl-tag", "tl-tag--" + tone, p.className) },
      p.icon ? h(Icon, { name: p.icon, size: 16 }) : null, p.children);
  }

  var PRESENCE = {
    available: { label: "Available", tone: "canopy", icon: "check" },
    ringing: { label: "Ringing", tone: "sunbeam", icon: "bell" },
    "on-call": { label: "On a call", tone: "canopy", icon: "phone" },
    quiet: { label: "Quiet hours", tone: "sky", icon: "moon" },
    paused: { label: "Paused", tone: "bark", icon: "pause" },
    offline: { label: "Offline", tone: "neutral", icon: "phone-off" }
  };
  function Presence(p) {
    var s = PRESENCE[p.status] || PRESENCE.offline;
    return h("span", { className: cx("tl-presence", "tl-presence--" + s.tone, p.className) },
      h("span", { className: "tl-presence__dot", "aria-hidden": true }),
      p.showIcon ? h(Icon, { name: s.icon, size: 16 }) : null,
      h("span", null, p.label || s.label));
  }

  var AVATAR_TONES = ["moss", "acorn", "pond", "petal", "sun"];
  function initials(name) {
    var bits = String(name || "?").trim().split(/\s+/);
    return (bits[0][0] + (bits.length > 1 ? bits[bits.length - 1][0] : "")).toUpperCase();
  }
  function toneFor(name) {
    var sum = 0, s = String(name || "");
    for (var i = 0; i < s.length; i++) sum += s.charCodeAt(i);
    return AVATAR_TONES[sum % AVATAR_TONES.length];
  }
  function Avatar(p) {
    var size = p.size || "md", tone = p.tone || toneFor(p.name);
    return h("span", { className: cx("tl-avatar", "tl-avatar--" + size, "tl-avatar--" + tone, p.className), role: "img", "aria-label": p.name },
      initials(p.name),
      p.status ? h("span", { className: "tl-avatar__status tl-presence--" + (PRESENCE[p.status] || PRESENCE.offline).tone, "aria-hidden": true }) : null);
  }

  // ---------- inputs ----------
  var uid = 0;
  function useId(given) { var r = React.useRef(given || "tl-" + (++uid)); return r.current; }

  function Switch(p) {
    var id = useId(p.id);
    var st = React.useState(!!p.defaultChecked), on = p.checked !== undefined ? p.checked : st[0];
    function toggle() { if (p.disabled) return; if (p.checked === undefined) st[1](!on); if (p.onChange) p.onChange(!on); }
    return h("div", { className: cx("tl-field-row", p.disabled && "is-disabled", p.className) },
      h("button", { id: id, type: "button", role: "switch", "aria-checked": on, disabled: p.disabled, onClick: toggle, className: cx("tl-switch", on && "is-on") },
        h("span", { className: "tl-switch__thumb" }, on ? h(Icon, { name: "check", size: 12 }) : null)),
      p.label ? h("label", { htmlFor: id, className: "tl-field-row__text" },
        h("span", { className: "tl-field-row__label" }, p.label),
        p.description ? h("span", { className: "tl-field-row__desc" }, p.description) : null) : null);
  }

  function Checkbox(p) {
    var id = useId(p.id);
    var st = React.useState(!!p.defaultChecked), on = p.checked !== undefined ? p.checked : st[0];
    function change(e) { if (p.checked === undefined) st[1](e.target.checked); if (p.onChange) p.onChange(e.target.checked); }
    return h("div", { className: cx("tl-field-row", p.disabled && "is-disabled", p.className) },
      h("span", { className: "tl-check" },
        h("input", { id: id, type: "checkbox", checked: on, disabled: p.disabled, onChange: change, className: "tl-check__input" }),
        h("span", { className: "tl-check__box", "aria-hidden": true }, h(Icon, { name: "check", size: 14 }))),
      p.label ? h("label", { htmlFor: id, className: "tl-field-row__text" },
        h("span", { className: "tl-field-row__label" }, p.label),
        p.description ? h("span", { className: "tl-field-row__desc" }, p.description) : null) : null);
  }

  function TextField(p) {
    var id = useId(p.id), hintId = id + "-hint";
    var rest = Object.assign({}, p);
    ["label", "hint", "error", "icon", "className", "id"].forEach(function (k) { delete rest[k]; });
    return h("div", { className: cx("tl-textfield", p.error && "has-error", p.className) },
      p.label ? h("label", { htmlFor: id, className: "tl-textfield__label" }, p.label) : null,
      h("div", { className: "tl-textfield__control" },
        p.icon ? h(Icon, { name: p.icon, size: 20, className: "tl-textfield__icon" }) : null,
        h("input", Object.assign({ id: id, className: "tl-textfield__input", "aria-invalid": p.error ? true : undefined, "aria-describedby": (p.error || p.hint) ? hintId : undefined }, rest))),
      (p.error || p.hint) ? h("p", { id: hintId, className: "tl-textfield__hint" },
        p.error ? h(Icon, { name: "close", size: 16 }) : null, p.error || p.hint) : null);
  }

  // ---------- containers ----------
  function Card(p) {
    var El = p.as || "section";
    return h(El, { className: cx("tl-card", p.elevated && "tl-card--raised", p.tone && "tl-card--" + p.tone, p.className) },
      (p.title || p.eyebrow || p.action) ? h("header", { className: "tl-card__head" },
        h("div", null,
          p.eyebrow ? h("p", { className: "tl-card__eyebrow" }, p.eyebrow) : null,
          p.title ? h("h3", { className: "tl-card__title" }, p.title) : null),
        p.action || null) : null,
      p.children);
  }

  // ---------- patterns ----------
  function FriendRow(p) {
    return h("div", { className: cx("tl-row", p.onClick && "is-clickable", p.className), onClick: p.onClick },
      h(Avatar, { name: p.name, status: p.status }),
      h("div", { className: "tl-row__main" },
        h("div", { className: "tl-row__title" }, p.name),
        h("div", { className: "tl-row__meta" },
          p.household ? h("span", { className: "tl-household" }, h(Icon, { name: "home", size: 16 }), p.household) : null,
          p.speedDial ? h("span", { className: "tl-speeddial", "aria-label": "Speed dial " + p.speedDial }, p.speedDial) : null,
          p.status ? h(Presence, { status: p.status, className: "tl-row__presence-inline" }) : null)),
      p.status ? h(Presence, { status: p.status }) : null,
      p.action || null);
  }

  function ApprovalSide(label, ok) {
    return h("div", { className: cx("tl-approval__side", ok ? "is-yes" : "is-waiting") },
      h("span", { className: "tl-approval__mark", "aria-hidden": true }, h(Icon, { name: ok ? "check" : "clock", size: 16 })),
      h("span", null, h("span", { className: "tl-approval__who" }, label), h("span", { className: "tl-approval__state" }, ok ? "Approved" : "Waiting")));
  }
  function ApprovalCard(p) {
    var both = p.yours && p.theirs;
    return h("section", { className: cx("tl-card tl-approval", both && "is-connected", p.className) },
      h("div", { className: "tl-approval__people" },
        h(Avatar, { name: p.kid }), h("span", { className: "tl-approval__link", "aria-hidden": true }, h(Icon, { name: both ? "leaf" : "plus", size: 16 })), h(Avatar, { name: p.friend })),
      h("h3", { className: "tl-card__title" }, both ? p.kid + " and " + p.friend + " can call each other" : p.kid + " and " + p.friend),
      h("div", { className: "tl-approval__sides" }, ApprovalSide(p.yourHousehold || "Your house", p.yours), ApprovalSide(p.theirHousehold || "Their house", p.theirs)),
      !both ? h("p", { className: "tl-approval__note" }, p.yours ? "Calls connect once " + (p.theirHousehold || "their house") + " approves too." : p.theirs ? (p.theirHousehold || "Their house") + " said yes. Calls connect once you approve." : "Nothing connects until both houses approve.") : null,
      p.actions ? h("div", { className: "tl-approval__actions" }, p.actions) : null);
  }

  function QuietHours(p) {
    var days = p.days || ["M", "T", "W", "T", "F", "S", "S"], active = p.activeDays || [0, 1, 2, 3, 4, 5, 6];
    return h("div", { className: cx("tl-quiet", p.className) },
      h("span", { className: "tl-quiet__icon", "aria-hidden": true }, h(Icon, { name: "moon", size: 20 })),
      h("div", { className: "tl-quiet__main" },
        h("div", { className: "tl-row__title" }, p.title || "Quiet hours"),
        h("div", { className: "tl-quiet__time" }, h("span", { className: "tl-num" }, p.start), h("span", { className: "tl-quiet__to" }, "to"), h("span", { className: "tl-num" }, p.end)),
        h("div", { className: "tl-quiet__days", "aria-label": "Days" }, days.map(function (d, i) {
          return h("span", { key: i, className: cx("tl-day", active.indexOf(i) >= 0 && "is-on") }, d);
        }))),
      h(Switch, { checked: p.on, defaultChecked: p.on === undefined ? true : undefined, onChange: p.onToggle, id: p.id }));
  }

  var LOG = {
    incoming: { icon: "phone-incoming", tone: "canopy", word: "Incoming" },
    outgoing: { icon: "phone-outgoing", tone: "canopy", word: "Outgoing" },
    missed: { icon: "phone-off", tone: "bark", word: "Missed" },
    blocked: { icon: "lock", tone: "berry", word: "Blocked" },
    "time-limit": { icon: "clock", tone: "sky", word: "Time limit" }
  };
  function CallLogItem(p) {
    var k = LOG[p.kind] || LOG.incoming;
    return h("div", { className: cx("tl-row tl-log", "tl-log--" + k.tone, p.className) },
      h("span", { className: "tl-log__icon", "aria-hidden": true }, h(Icon, { name: k.icon, size: 20 })),
      h("div", { className: "tl-row__main" },
        h("div", { className: "tl-row__title" }, p.from, h("span", { className: "tl-log__arrow", "aria-hidden": true }, " → "), p.to),
        h("div", { className: "tl-row__meta" }, h("span", null, p.time), p.reason ? h("span", null, p.reason) : null)),
      p.kind === "blocked" || p.kind === "missed" || p.kind === "time-limit" ? h(Tag, { tone: k.tone === "berry" ? "berry" : k.tone, icon: k.icon }, k.word) : h("span", { className: "tl-log__dur tl-num" }, p.duration));
  }


  // ---------- nature ----------
  var ART = {"treehouse": {"vb": "0 0 240 180", "els": ["<path class=\"w-sky\" d=\"M228.0 58.0C228.2 69.3 230.2 84.3 218.5 92.1C206.9 100.0 176.6 106.1 158.0 105.2C139.4 104.4 119.6 94.9 106.6 87.0C93.6 79.1 80.6 67.9 80.1 58.0C79.6 48.1 90.6 35.0 103.6 27.3C116.6 19.7 139.0 12.6 158.0 12.1C177.0 11.6 205.9 16.7 217.6 24.4C229.3 32.0 227.9 46.7 228.0 58.0Z\"/>", "<circle class=\"w-sun\" cx=\"196\" cy=\"34\" r=\"15\"/>", "<path class=\"w-leaf\" d=\"M200.4 66.0C201.8 76.7 190.9 94.6 178.5 101.0C166.1 107.4 141.6 105.8 126.0 104.5C110.4 103.3 96.8 99.9 84.8 93.5C72.7 87.1 55.2 76.1 53.8 66.0C52.4 55.9 64.2 40.5 76.2 32.8C88.3 25.1 110.3 19.3 126.0 19.9C141.7 20.5 157.8 28.9 170.2 36.6C182.6 44.2 199.0 55.3 200.4 66.0Z\"/>", "<path class=\"w-bark\" d=\"M155.5 118.0C155.2 121.0 153.6 124.7 148.3 126.6C143.1 128.5 132.2 129.5 124.0 129.6C115.8 129.6 105.1 128.7 99.3 126.7C93.4 124.8 88.2 120.7 88.8 118.0C89.4 115.3 97.0 112.3 102.9 110.5C108.7 108.8 116.1 107.9 124.0 107.6C131.9 107.3 145.1 107.0 150.3 108.7C155.6 110.4 155.8 115.0 155.5 118.0Z\"/>", "<path class=\"ln\" d=\"M85.6 98.1A18.0 18.0 0 0 1 61.9 78.6A8.6 8.6 0 0 1 55.9 66.5A21.6 21.6 0 0 1 67.1 37.6A21.8 21.8 0 0 1 95.5 25.2A10.0 10.0 0 0 1 112.3 19.3A32.7 32.7 0 0 1 158.7 27.4A17.2 17.2 0 0 1 179.9 42.8A11.2 11.2 0 0 1 185.3 59.9A12.8 12.8 0 0 1 178.3 80.9A20.3 20.3 0 0 1 154.7 98.5\"/>", "<path class=\"ln\" d=\"M114 116C113 132 110 146 104 160M128 116C129 132 132 146 138 160\"/>", "<path class=\"ln-soft\" d=\"M100 100C96 94 90 90 82 88M142 100C148 92 156 88 164 88\"/>", "<path class=\"ln\" d=\"M97.0 116H147.0\"/>", "<path class=\"ln\" d=\"M105.0 116V100H139.0V116\"/>", "<path class=\"ln\" d=\"M101.0 101L122 88L143.0 101\"/>", "<path class=\"ln\" d=\"M118 116V107H126V116\"/>", "<path class=\"ln\" d=\"M92 116L88 160M101 116L98 160\"/>", "<path class=\"ln-soft\" d=\"M90.6 128H99.8M89.6 140H98.8M88.6 152H97.8\"/>", "<path class=\"ln-soft\" d=\"M56 160C100 156 152 156 200 160\"/>", "<path class=\"w-leaf\" transform=\"translate(187.6 119.2) rotate(40) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(186 118) rotate(40) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(205.6 141.2) rotate(-20) scale(0.735)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(204 140) rotate(-20) scale(0.7)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>"]}, "connection": {"vb": "0 0 240 180", "els": ["<path class=\"w-sun\" d=\"M157.0 70.0C156.1 76.0 151.3 82.1 145.1 86.3C139.0 90.5 128.4 95.2 120.0 95.2C111.6 95.3 100.3 90.8 94.4 86.6C88.6 82.4 85.2 75.7 84.9 70.0C84.5 64.3 86.6 57.0 92.5 52.1C98.4 47.3 110.3 41.3 120.0 41.0C129.7 40.6 144.5 45.2 150.7 50.1C156.8 54.9 158.0 64.0 157.0 70.0Z\"/>", "<path class=\"w-leaf\" d=\"M97.3 60.0C97.7 67.3 93.2 77.2 86.7 82.6C80.1 88.1 67.8 92.3 58.0 92.5C48.2 92.7 34.6 89.3 27.8 83.8C21.0 78.4 17.4 67.9 17.4 60.0C17.5 52.1 21.2 40.6 28.0 36.3C34.7 31.9 48.6 33.5 58.0 34.0C67.4 34.4 78.1 34.7 84.6 39.0C91.2 43.3 97.0 52.7 97.3 60.0Z\"/>", "<path class=\"w-leaf\" d=\"M225.0 64.0C225.0 71.1 220.2 80.9 213.8 85.6C207.3 90.2 194.6 92.4 186.0 91.9C177.4 91.4 167.4 87.1 162.2 82.5C157.1 77.8 155.5 70.5 155.0 64.0C154.6 57.5 154.2 47.9 159.4 43.3C164.5 38.7 177.0 36.3 186.0 36.2C195.0 36.1 206.8 38.1 213.3 42.8C219.8 47.4 224.9 56.9 225.0 64.0Z\"/>", "<path class=\"ln\" d=\"M36.7 82.0A15.3 15.3 0 0 1 20.5 65.5A13.1 13.1 0 0 1 23.5 46.4A11.9 11.9 0 0 1 40.0 34.3A14.9 14.9 0 0 1 63.5 31.4A19.0 19.0 0 0 1 89.0 44.9A15.4 15.4 0 0 1 89.8 66.9A12.6 12.6 0 0 1 75.2 81.9\"/>", "<path class=\"ln\" d=\"M166.3 83.7A14.6 14.6 0 0 1 151.4 69.1A9.8 9.8 0 0 1 152.9 51.8A15.5 15.5 0 0 1 175.1 38.0A13.0 13.0 0 0 1 195.3 38.1A12.4 12.4 0 0 1 213.6 50.1A9.0 9.0 0 0 1 219.3 64.1A17.1 17.1 0 0 1 202.4 84.5\"/>", "<path class=\"ln\" d=\"M51 98C50 120 48 140 44 160M61 98C62 120 64 140 68 160\"/>", "<path class=\"ln\" d=\"M179 100C178 122 176 140 172 160M189 100C190 122 192 140 196 160\"/>", "<path class=\"ln\" d=\"M35.0 98H77.0\"/>", "<path class=\"ln\" d=\"M43.0 98V86H69.0V98\"/>", "<path class=\"ln\" d=\"M39.0 87L56 77L73.0 87\"/>", "<path class=\"ln\" d=\"M52 98V89H60V98\"/>", "<path class=\"ln\" d=\"M163.0 100H205.0\"/>", "<path class=\"ln\" d=\"M171.0 100V88H197.0V100\"/>", "<path class=\"ln\" d=\"M167.0 89L184 79L201.0 89\"/>", "<path class=\"ln\" d=\"M180 100V91H188V100\"/>", "<path class=\"ln-accent\" d=\"M74 90Q120 122 166 92\"/>", "<path class=\"lf\" transform=\"translate(120 104) rotate(70) scale(0.65)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln-soft\" d=\"M20 160C80 156 160 156 220 160\"/>"]}, "quiet": {"vb": "0 0 240 180", "els": ["<path class=\"w-sky\" d=\"M223.3 62.0C222.1 73.7 208.5 86.1 193.2 95.2C178.0 104.2 152.2 116.3 132.0 116.2C111.8 116.1 88.4 103.4 72.2 94.4C56.1 85.3 36.0 73.3 35.0 62.0C34.1 50.7 50.5 34.2 66.7 26.6C82.8 19.0 109.8 16.7 132.0 16.4C154.2 16.2 184.8 17.6 200.0 25.2C215.2 32.7 224.4 50.3 223.3 62.0Z\"/>", "<path class=\"w-petal\" d=\"M187.6 134.0C189.7 140.3 190.0 150.9 177.1 154.8C164.2 158.6 131.6 157.5 110.0 157.3C88.4 157.1 59.6 157.3 47.2 153.4C34.8 149.6 34.5 140.1 35.8 134.0C37.0 127.9 42.4 121.9 54.8 116.9C67.2 112.0 91.7 104.3 110.0 104.4C128.3 104.4 151.6 112.2 164.6 117.1C177.5 122.1 185.5 127.7 187.6 134.0Z\"/>", "<path class=\"w-leaf\" d=\"M153.5 78.0C154.0 86.7 147.0 99.3 139.4 105.3C131.8 111.3 119.2 113.3 108.0 114.0C96.8 114.6 78.7 115.2 72.1 109.2C65.5 103.2 67.8 87.9 68.4 78.0C68.9 68.1 68.8 57.1 75.4 49.7C82.1 42.3 97.8 33.0 108.0 33.5C118.2 34.1 129.1 45.6 136.7 53.0C144.3 60.4 153.1 69.3 153.5 78.0Z\"/>", "<path class=\"ln\" d=\"M81.7 110.5A17.8 17.8 0 0 1 63.7 90.8A19.4 19.4 0 0 1 61.4 57.4A12.7 12.7 0 0 1 76.7 40.8A18.4 18.4 0 0 1 107.4 33.2A18.7 18.7 0 0 1 133.3 41.6A14.3 14.3 0 0 1 148.5 59.4A21.4 21.4 0 0 1 142.9 94.3A13.2 13.2 0 0 1 125.6 109.3\"/>", "<path class=\"ln\" d=\"M99 112C98 128 96 144 92 160M109 112C110 128 112 144 116 160\"/>", "<path class=\"ln\" d=\"M184 26A16 16 0 1 0 198 50A12 12 0 1 1 184 26Z\"/>", "<path class=\"ln-soft\" d=\"M160 52V60M156 56H164M206 78V84M203 81H209M146 22V28M143 25H149\"/>", "<path class=\"ln-soft\" d=\"M40 160C90 156 150 156 210 160\"/>"]}, "sprig": {"vb": "0 0 120 40", "els": ["<path class=\"ln\" d=\"M6 30C40 24 80 16 114 8\"/>", "<path class=\"w-leaf\" transform=\"translate(29.6 23.2) rotate(-60) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(28 22) rotate(-60) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(47.6 31.2) rotate(40) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(46 30) rotate(40) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(63.6 17.2) rotate(-50) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(62 16) rotate(-50) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(81.6 23.2) rotate(50) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(80 22) rotate(50) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(97.6 9.2) rotate(-40) scale(0.8400000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(96 8) rotate(-40) scale(0.8)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>"]}, "lookout": {"vb": "0 0 240 180", "els": ["<path class=\"w-sky\" d=\"M224.3 62.0C224.8 73.1 223.4 88.3 211.1 96.3C198.7 104.2 169.8 110.1 150.0 109.7C130.2 109.4 104.9 102.3 92.4 94.3C79.8 86.4 75.4 73.3 74.5 62.0C73.7 50.7 74.7 35.1 87.3 26.8C99.8 18.5 129.8 11.6 150.0 12.0C170.2 12.5 195.8 21.0 208.2 29.4C220.6 37.7 223.8 50.9 224.3 62.0Z\"/>", "<circle class=\"w-sun\" cx=\"52\" cy=\"40\" r=\"13\"/>", "<path class=\"w-leaf\" d=\"M203.0 74.0C202.5 84.9 181.7 98.6 168.5 105.8C155.3 113.0 140.8 115.9 124.0 117.3C107.2 118.7 78.2 121.5 67.6 114.3C57.0 107.1 58.2 86.0 60.2 74.0C62.2 62.0 69.1 51.1 79.8 42.4C90.4 33.7 108.7 22.3 124.0 21.9C139.3 21.5 158.2 31.5 171.4 40.2C184.5 48.9 203.5 63.1 203.0 74.0Z\"/>", "<path class=\"w-bark\" d=\"M155.6 104.0C156.4 106.4 151.5 110.1 145.9 112.0C140.3 113.8 129.1 115.4 122.0 115.1C114.9 114.8 108.4 112.1 103.3 110.2C98.1 108.4 91.6 106.2 91.2 104.0C90.9 101.8 96.1 98.8 101.2 97.1C106.4 95.4 115.4 93.8 122.0 93.9C128.6 94.0 135.4 96.0 141.0 97.7C146.6 99.3 154.8 101.6 155.6 104.0Z\"/>", "<path class=\"ln\" d=\"M86.4 115.1A16.9 16.9 0 0 1 61.2 100.8A11.6 11.6 0 0 1 55.9 83.0A16.2 16.2 0 0 1 50.1 60.8A17.2 17.2 0 0 1 64.8 41.5A20.3 20.3 0 0 1 88.3 24.9A17.7 17.7 0 0 1 118.8 20.8A18.5 18.5 0 0 1 147.4 26.2A14.0 14.0 0 0 1 168.9 35.2A22.6 22.6 0 0 1 188.3 61.8A10.8 10.8 0 0 1 192.0 77.1A18.3 18.3 0 0 1 176.3 98.8A20.0 20.0 0 0 1 151.3 112.0\"/>", "<path class=\"ln\" d=\"M113 116C112 131 110 147 107 160M129 116C130 131 132 147 135 160\"/>", "<path class=\"ln-soft\" d=\"M104 112C98 106 92 103 84 102M138 112C146 104 154 101 162 101\"/>", "<path class=\"ln\" d=\"M96.0 102H146.0\"/>", "<path class=\"ln\" d=\"M104.0 102V86H138.0V102\"/>", "<path class=\"ln\" d=\"M100.0 87L121 74L142.0 87\"/>", "<path class=\"ln\" d=\"M117 102V93H125V102\"/>", "<path class=\"ln\" d=\"M121 74V62L130 65.5L121 69\"/>", "<path class=\"ln\" d=\"M95 102L90 160M104 102L100 160\"/>", "<path class=\"ln-soft\" d=\"M93.4 114H103M92.4 126H102M91.4 138H101M90.4 150H100\"/>", "<path class=\"ln-soft\" d=\"M44 160C96 156 150 156 204 160\"/>", "<path class=\"w-leaf\" transform=\"translate(41.6 105.2) rotate(30) scale(0.7875000000000001)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(40 104) rotate(30) scale(0.75)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>", "<path class=\"w-leaf\" transform=\"translate(59.6 133.2) rotate(-35) scale(0.651)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(58 132) rotate(-35) scale(0.62)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>"]}, "treeline": {"vb": "0 0 240 180", "els": ["<path class=\"w-sky\" d=\"M213.8 70.0C211.6 81.1 204.5 92.5 189.6 100.3C174.6 108.0 147.8 115.7 124.0 116.6C100.2 117.5 62.3 113.4 46.7 105.7C31.1 97.9 28.6 81.0 30.5 70.0C32.5 59.0 42.9 47.1 58.4 39.7C74.0 32.3 99.9 26.6 124.0 25.6C148.1 24.6 187.9 26.2 202.8 33.6C217.8 41.0 216.0 58.9 213.8 70.0Z\"/>", "<circle class=\"w-sun\" cx=\"196\" cy=\"36\" r=\"12\"/>", "<path class=\"w-leaf\" d=\"M86.5 96.0C86.2 102.3 83.9 109.8 79.5 114.2C75.1 118.6 67.2 121.8 60.0 122.5C52.8 123.1 41.4 122.4 36.4 118.0C31.4 113.6 29.9 103.2 30.0 96.0C30.2 88.8 32.5 79.1 37.5 75.0C42.5 70.8 52.7 70.9 60.0 71.1C67.3 71.3 76.9 72.0 81.3 76.2C85.7 80.3 86.7 89.7 86.5 96.0Z\"/>", "<path class=\"w-leaf\" d=\"M166.8 70.0C167.4 79.2 161.9 92.1 154.8 99.3C147.7 106.6 133.8 114.0 124.0 113.6C114.2 113.1 103.5 103.8 96.2 96.5C88.9 89.3 81.1 79.6 80.2 70.0C79.4 60.4 83.8 46.1 91.1 38.6C98.3 31.2 114.0 24.5 124.0 25.4C134.0 26.4 144.0 36.8 151.1 44.2C158.2 51.6 166.2 60.8 166.8 70.0Z\"/>", "<path class=\"w-leaf\" d=\"M214.2 100.0C214.3 105.7 211.2 113.0 206.8 117.4C202.5 121.8 194.5 126.1 188.0 126.3C181.5 126.6 172.4 123.2 167.6 118.9C162.8 114.5 158.8 105.9 159.2 100.0C159.7 94.1 165.5 88.2 170.3 83.7C175.1 79.2 182.1 73.0 188.0 73.0C193.9 72.9 201.6 78.9 206.0 83.4C210.4 87.9 214.1 94.3 214.2 100.0Z\"/>", "<path class=\"ln\" d=\"M43.6 119.0A16.0 16.0 0 0 1 31.0 99.9A11.2 11.2 0 0 1 32.2 80.9A17.7 17.7 0 0 1 53.2 67.1A11.3 11.3 0 0 1 72.3 69.0A9.5 9.5 0 0 1 82.1 80.0A11.9 11.9 0 0 1 87.2 97.2A14.3 14.3 0 0 1 71.4 117.2\"/>", "<path class=\"ln\" d=\"M103.8 101.9A13.0 13.0 0 0 1 87.9 87.0A15.9 15.9 0 0 1 83.7 61.5A16.6 16.6 0 0 1 93.9 36.9A12.5 12.5 0 0 1 107.7 24.7A14.8 14.8 0 0 1 132.6 27.6A17.3 17.3 0 0 1 155.9 40.9A9.1 9.1 0 0 1 161.1 55.8A16.8 16.8 0 0 1 159.2 84.7A17.7 17.7 0 0 1 140.3 102.2\"/>", "<path class=\"ln\" d=\"M172.7 121.0A13.3 13.3 0 0 1 160.8 100.7A6.9 6.9 0 0 1 161.7 89.7A11.1 11.1 0 0 1 174.4 75.1A16.2 16.2 0 0 1 199.8 75.1A6.6 6.6 0 0 1 206.3 83.2A10.8 10.8 0 0 1 212.7 101.3A14.7 14.7 0 0 1 199.2 120.9\"/>", "<path class=\"ln\" d=\"M53 120C52 134 50 148 50 160M63 120C64 134 66 148 66 160\"/>", "<path class=\"ln\" d=\"M115 106C114 125 112 144 110 160M129 106C130 125 132 144 134 160\"/>", "<path class=\"ln\" d=\"M181 122C180 135 178 149 178 160M191 122C192 135 194 149 194 160\"/>", "<path class=\"ln\" d=\"M99.0 104H145.0\"/>", "<path class=\"ln\" d=\"M107.0 104V90H137.0V104\"/>", "<path class=\"ln\" d=\"M103.0 91L122 79L141.0 91\"/>", "<path class=\"ln\" d=\"M118 104V95H126V104\"/>", "<path class=\"ln-soft\" d=\"M20 160C80 156 164 156 222 160\"/>", "<path class=\"w-leaf\" transform=\"translate(215.6 129.2) rotate(35) scale(0.63)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln\" transform=\"translate(214 128) rotate(35) scale(0.6)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8\"/>"]}, "neighborhood": {"vb": "0 0 330 170", "els": ["<path class=\"w-sky\" d=\"M305.2 62.0C305.7 71.3 295.3 84.3 272.1 90.3C248.9 96.3 203.0 97.8 166.0 98.2C129.0 98.6 73.5 98.9 50.4 92.8C27.3 86.8 26.0 71.9 27.3 62.0C28.6 52.1 35.3 40.8 58.4 33.3C81.5 25.8 130.9 17.0 166.0 17.2C201.1 17.4 245.8 27.1 269.0 34.5C292.2 42.0 304.7 52.7 305.2 62.0Z\"/>", "<circle class=\"w-sun\" cx=\"164\" cy=\"28\" r=\"11\"/>", "<path class=\"w-leaf\" d=\"M75.1 88.0C74.9 93.8 70.8 101.1 66.3 105.0C61.8 108.9 54.7 111.0 48.0 111.6C41.3 112.2 30.7 112.4 25.9 108.5C21.1 104.6 19.2 94.6 19.4 88.0C19.6 81.4 22.4 73.0 27.1 68.6C31.9 64.2 41.3 61.4 48.0 61.6C54.7 61.9 62.6 65.8 67.2 70.2C71.7 74.6 75.2 82.2 75.1 88.0Z\"/>", "<path class=\"w-leaf\" d=\"M163.4 68.0C163.3 75.0 154.3 83.5 148.1 88.8C141.8 94.2 133.6 99.6 126.0 99.9C118.4 100.1 108.9 95.5 102.5 90.2C96.1 84.9 88.2 75.9 87.6 68.0C87.1 60.1 92.9 49.1 99.3 42.8C105.7 36.5 117.8 29.6 126.0 30.3C134.2 30.9 142.3 40.5 148.5 46.7C154.7 53.0 163.5 61.0 163.4 68.0Z\"/>", "<path class=\"w-leaf\" d=\"M232.1 84.0C232.3 90.8 232.7 100.7 228.4 104.9C224.0 109.1 213.2 109.4 206.0 109.2C198.8 109.0 190.2 107.8 185.0 103.6C179.8 99.4 174.9 90.8 174.6 84.0C174.2 77.2 177.8 67.2 183.0 62.6C188.3 58.0 198.6 56.1 206.0 56.4C213.4 56.6 222.8 59.6 227.2 64.2C231.6 68.8 231.9 77.2 232.1 84.0Z\"/>", "<path class=\"w-leaf\" d=\"M317.1 66.0C317.7 73.1 313.8 83.0 308.3 88.9C302.8 94.8 291.7 101.6 284.0 101.2C276.3 100.9 267.4 92.5 262.1 86.6C256.9 80.7 252.5 72.7 252.6 66.0C252.8 59.3 257.9 51.1 263.1 46.4C268.4 41.6 277.1 37.4 284.0 37.4C290.9 37.5 299.2 41.7 304.7 46.5C310.3 51.2 316.5 58.9 317.1 66.0Z\"/>", "<path class=\"ln\" d=\"M33.1 106.3A11.8 11.8 0 0 1 20.3 92.6A13.1 13.1 0 0 1 21.6 72.8A8.4 8.4 0 0 1 31.7 62.2A19.2 19.2 0 0 1 58.7 60.0A9.4 9.4 0 0 1 68.5 69.5A11.9 11.9 0 0 1 71.7 87.2A16.1 16.1 0 0 1 58.6 105.9\"/>", "<path class=\"ln\" d=\"M41 102C40 119 38 136 38 150M51 102C52 119 54 136 54 150\"/>", "<path class=\"ln\" d=\"M26.0 100H66.0\"/>", "<path class=\"ln\" d=\"M34.0 100V89H58.0V100\"/>", "<path class=\"ln\" d=\"M30.0 90L46 81L62.0 90\"/>", "<path class=\"ln\" d=\"M42 100V91H50V100\"/>", "<path class=\"ln\" d=\"M107.0 93.4A12.8 12.8 0 0 1 94.9 79.3A15.3 15.3 0 0 1 90.3 56.9A20.5 20.5 0 0 1 107.5 33.4A14.0 14.0 0 0 1 129.0 29.1A11.8 11.8 0 0 1 144.1 37.5A16.5 16.5 0 0 1 159.2 61.2A11.1 11.1 0 0 1 153.6 79.7A10.6 10.6 0 0 1 141.4 94.2\"/>", "<path class=\"ln\" d=\"M118 98C117 116 115 134 115 150M130 98C131 116 133 134 133 150\"/>", "<path class=\"ln\" d=\"M104.0 96H144.0\"/>", "<path class=\"ln\" d=\"M112.0 96V85H136.0V96\"/>", "<path class=\"ln\" d=\"M108.0 86L124 77L140.0 86\"/>", "<path class=\"ln\" d=\"M120 96V87H128V96\"/>", "<path class=\"ln\" d=\"M189.4 105.3A15.9 15.9 0 0 1 175.5 83.1A8.4 8.4 0 0 1 177.4 69.0A14.2 14.2 0 0 1 193.7 54.8A13.7 13.7 0 0 1 216.5 54.2A14.9 14.9 0 0 1 230.3 72.3A9.5 9.5 0 0 1 230.2 86.0A14.8 14.8 0 0 1 217.9 104.1\"/>", "<path class=\"ln\" d=\"M199 104C198 120 196 136 196 150M209 104C210 120 212 136 212 150\"/>", "<path class=\"ln\" d=\"M184.0 102H224.0\"/>", "<path class=\"ln\" d=\"M192.0 102V91H216.0V102\"/>", "<path class=\"ln\" d=\"M188.0 92L204 83L220.0 92\"/>", "<path class=\"ln\" d=\"M200 102V93H208V102\"/>", "<path class=\"ln\" d=\"M265.7 90.2A15.3 15.3 0 0 1 249.8 71.4A9.7 9.7 0 0 1 250.5 55.3A16.6 16.6 0 0 1 265.0 34.9A10.1 10.1 0 0 1 281.4 31.5A15.0 15.0 0 0 1 304.5 37.5A12.5 12.5 0 0 1 313.1 57.2A14.6 14.6 0 0 1 308.4 77.4A10.8 10.8 0 0 1 297.5 88.8\"/>", "<path class=\"ln\" d=\"M276 96C275 115 273 134 273 150M288 96C289 115 291 134 291 150\"/>", "<path class=\"ln\" d=\"M262.0 94H302.0\"/>", "<path class=\"ln\" d=\"M270.0 94V83H294.0V94\"/>", "<path class=\"ln\" d=\"M266.0 84L282 75L298.0 84\"/>", "<path class=\"ln\" d=\"M278 94V85H286V94\"/>", "<path class=\"ln-accent\" d=\"M62 94Q85.0 114 108 90\"/>", "<path class=\"lf\" transform=\"translate(85.0 102.0) rotate(70) scale(0.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln-accent\" d=\"M140 90Q164.0 116 188 96\"/>", "<path class=\"lf\" transform=\"translate(164.0 103.0) rotate(70) scale(0.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln-accent\" d=\"M220 96Q243.0 116 266 88\"/>", "<path class=\"lf\" transform=\"translate(243.0 102.0) rotate(70) scale(0.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/>", "<path class=\"ln-soft\" d=\"M14 150C100 146 230 146 318 150\"/>"]}};
  function Illustration(p) {
    var a = ART[p.name] || ART.treehouse;
    return h("svg", {
      className: cx("tl-art", p.className), viewBox: a.vb, width: p.width || undefined, style: p.width ? null : { width: "100%", height: "auto" },
      role: p.label ? "img" : undefined, "aria-label": p.label, "aria-hidden": p.label ? undefined : true,
      dangerouslySetInnerHTML: { __html: a.els.join("") }
    });
  }

  function EmptyState(p) {
    return h("div", { className: cx("tl-empty", p.className) },
      h("div", { className: "tl-empty__art" }, h(Illustration, { name: p.illustration || "treehouse" })),
      p.title ? h("h3", { className: "tl-empty__title" }, p.title) : null,
      p.children ? h("p", { className: "tl-empty__body" }, p.children) : null,
      p.action ? h("div", { className: "tl-empty__action" }, p.action) : null);
  }

  var SPRIG = '<path class="ln-soft" d="M2 12C10 10 18 8 26 6"/>' +
    '<path class="w-leaf" transform="translate(11.6 9.4) rotate(-55) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/>' +
    '<path class="ln" transform="translate(10 8) rotate(-55) scale(.6)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/>' +
    '<path class="w-leaf" transform="translate(19.6 11.4) rotate(45) scale(.62)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/>' +
    '<path class="ln" transform="translate(18 10) rotate(45) scale(.6)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/>';
  function LeafDivider(p) {
    return h("div", { className: cx("tl-leafdiv", p.className), role: "separator" },
      h("span", { className: "tl-fade-line tl-leafdiv__line" }),
      h("svg", { className: "tl-art tl-leafdiv__sprig", viewBox: "0 0 28 18", width: 28, height: 18, "aria-hidden": true, dangerouslySetInnerHTML: { __html: SPRIG } }),
      h("span", { className: "tl-fade-line tl-leafdiv__line" }));
  }

  var LOADER = "<path class=\"tl-loader__wind ln-soft\" d=\"M4 16C14 11 26 12 36 17S54 22 60 18\"/><path class=\"tl-loader__wind tl-loader__wind--2 ln-soft\" d=\"M2 30C12 26 22 27 32 31S50 35 58 32\"/><g class=\"tl-loader__leaf tl-loader__leaf--1\"><path class=\"w-leaf\" transform=\"translate(1.2 1) scale(.62)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/><path class=\"lf\" transform=\"scale(.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/></g><g class=\"tl-loader__leaf tl-loader__leaf--2\"><path class=\"w-leaf\" transform=\"translate(1.2 1) scale(.62)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/><path class=\"lf\" transform=\"scale(.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/></g><g class=\"tl-loader__leaf tl-loader__leaf--3\"><path class=\"w-leaf\" transform=\"translate(1.2 1) scale(.62)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/><path class=\"lf\" transform=\"scale(.55)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/></g>";
  function LeafLoader(p) {
    var size = p.size || 64;
    return h("span", { className: cx("tl-loader", p.className), role: "status" },
      h("svg", { className: "tl-art tl-loader__svg", viewBox: "0 0 64 48", width: size, height: size * 0.75, "aria-hidden": true, dangerouslySetInnerHTML: { __html: LOADER } }),
      p.label !== false ? h("span", { className: p.showLabel ? "tl-loader__label" : "tl-sr" }, p.label || "Loading") : null);
  }


  // ---------- feedback, choice and menus ----------
  var ALERT_ICON = { info: "info", success: "check", warning: "alert", danger: "alert" };
  function Alert(p) {
    var tone = p.tone || "info";
    return h("div", { className: cx("tl-alert", "tl-alert--" + tone, p.className), role: tone === "danger" || tone === "warning" ? "alert" : "status" },
      h("span", { className: "tl-alert__icon", "aria-hidden": true }, h(Icon, { name: p.icon || ALERT_ICON[tone], size: 20 })),
      h("div", null,
        p.title ? h("p", { className: "tl-alert__title" }, p.title) : null,
        p.children ? h("p", { className: "tl-alert__body" }, p.children) : null,
        p.actions ? h("div", { className: "tl-alert__actions" }, p.actions) : null),
      (p.onClose || p.dismissible) ? h(IconButton, { icon: "close", label: "Dismiss", size: "sm", className: "tl-alert__close", onClick: p.onClose, "data-tl-dismiss": "" }) : h("span"));
  }
  function Toast(p) {
    var tone = p.tone || "neutral";
    return h("div", { className: cx("tl-toast", "tl-toast--" + tone, p.className), role: "status" },
      h(Icon, { name: p.icon || (tone === "warning" ? "alert" : tone === "success" ? "check" : "info"), size: 20, className: "tl-toast__icon" }),
      h("span", { className: "tl-toast__msg" }, p.children),
      p.action ? h("button", { type: "button", className: "tl-toast__action", onClick: p.onAction }, p.action) : null);
  }
  function Toasts(p) { return h("div", { className: "tl-toasts", "aria-live": "polite", "aria-atomic": "false" }, p.children); }

  function Select(p) {
    var id = useId(p.id), hintId = id + "-hint";
    var rest = Object.assign({}, p);
    ["label", "hint", "error", "options", "className", "id", "children"].forEach(function (k) { delete rest[k]; });
    return h("div", { className: cx("tl-textfield", p.error && "has-error", p.className) },
      p.label ? h("label", { htmlFor: id, className: "tl-textfield__label" }, p.label) : null,
      h("div", { className: "tl-textfield__control" },
        h("select", Object.assign({ id: id, className: "tl-textfield__input tl-select", "aria-invalid": p.error ? true : undefined, "aria-describedby": (p.error || p.hint) ? hintId : undefined }, rest),
          (p.options || []).map(function (o) { o = typeof o === "string" ? { value: o, label: o } : o; return h("option", { key: o.value, value: o.value, disabled: o.disabled }, o.label); })),
        h(Icon, { name: "chevron-down", size: 20, className: "tl-textfield__chevron" })),
      (p.error || p.hint) ? h("p", { id: hintId, className: "tl-textfield__hint" }, p.error ? h(Icon, { name: "close", size: 16 }) : null, p.error || p.hint) : null);
  }
  function TimeField(p) {
    var rest = Object.assign({}, p); delete rest.className;
    return h(TextField, Object.assign({ type: "time", icon: "clock", className: cx("tl-timefield", p.className) }, rest, { className: cx("tl-timefield", p.className) }));
  }
  function TimeRange(p) {
    var id = useId(p.id);
    return h("fieldset", { className: cx("tl-timerange", p.className) },
      h("legend", null, p.label || "Time"),
      h("div", { className: "tl-timerange__row" },
        h(TimeField, { id: id + "-start", label: p.startLabel || "From", value: p.start, defaultValue: p.defaultStart, onChange: p.onStartChange }),
        h("span", { className: "tl-timerange__to", "aria-hidden": true }, "to"),
        h(TimeField, { id: id + "-end", label: p.endLabel || "Until", value: p.end, defaultValue: p.defaultEnd, onChange: p.onEndChange })),
      p.hint ? h("p", { className: "tl-textfield__hint" }, p.hint) : null);
  }
  function SegmentedControl(p) {
    var name = useId(p.name);
    var st = React.useState(p.defaultValue !== undefined ? p.defaultValue : ((p.options || [])[0] || {}).value);
    var val = p.value !== undefined ? p.value : st[0];
    return h("fieldset", { className: cx("tl-segmented", p.fullWidth && "tl-segmented--full", p.className), "aria-label": p.label },
      (p.options || []).map(function (o) {
        o = typeof o === "string" ? { value: o, label: o } : o;
        return h("label", { key: o.value, className: "tl-segmented__opt" },
          h("input", { type: "radio", name: name, value: o.value, checked: val === o.value, disabled: o.disabled,
            onChange: function () { st[1](o.value); if (p.onChange) p.onChange(o.value); } }),
          h("span", null, o.icon ? h(Icon, { name: o.icon, size: 16 }) : null, o.label));
      }));
  }
  function Menu(p) {
    var id = useId(p.id), st = React.useState(!!p.defaultOpen), open = st[0], setOpen = st[1];
    var ref = React.useRef(null);
    React.useEffect(function () {
      if (!open) return;
      function away(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
      function key(e) { if (e.key === "Escape") setOpen(false); }
      document.addEventListener("mousedown", away); document.addEventListener("keydown", key);
      return function () { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", key); };
    }, [open]);
    var trigger = p.trigger || h(IconButton, { icon: "more", label: p.label || "More" });
    return h("div", { className: cx("tl-menu", p.align === "start" && "tl-menu--start", p.className), ref: ref },
      React.cloneElement(trigger, { "aria-haspopup": "menu", "aria-expanded": open ? "true" : "false", "aria-controls": id, "data-tl-menu": id,
        onClick: function () { setOpen(!open); } }),
      h("div", { className: "tl-menu__panel", id: id, role: "menu", hidden: !open || undefined, "aria-label": p.label },
        p.header ? h("div", { className: "tl-menu__head" }, h("span", { className: "tl-menu__name" }, p.header.name), p.header.meta ? h("span", { className: "tl-menu__meta" }, p.header.meta) : null) : null,
        (p.items || []).map(function (it, i) {
          if (it.separator) return h("div", { key: "s" + i, className: "tl-menu__sep", role: "separator" });
          var El = it.href ? "a" : "button";
          return h(El, { key: it.label, role: "menuitem", href: it.href, type: it.href ? undefined : "button", className: cx("tl-menu__item", it.danger && "tl-menu__item--danger"),
            onClick: function (e) { setOpen(false); if (it.onSelect) it.onSelect(e); } }, it.icon ? h(Icon, { name: it.icon, size: 20 }) : null, h("span", null, it.label));
        })));
  }

  // ---------- more inputs, status and structure ----------
  function RadioGroup(p) {
    var name = useId(p.name);
    var st = React.useState(p.defaultValue), val = p.value !== undefined ? p.value : st[0];
    return h("fieldset", { className: cx("tl-radiogroup", p.variant === "cards" && "tl-radiogroup--cards", p.className) },
      h("legend", null, p.label),
      (p.options || []).map(function (o) {
        var id = name + "-" + o.value;
        return h("div", { key: o.value, className: cx("tl-field-row", o.disabled && "is-disabled") },
          h("span", { className: "tl-radio" },
            h("input", { id: id, type: "radio", name: name, value: o.value, checked: val === o.value, disabled: o.disabled, className: "tl-radio__input",
              onChange: function () { st[1](o.value); if (p.onChange) p.onChange(o.value); } }),
            h("span", { className: "tl-radio__dot", "aria-hidden": true })),
          h("label", { htmlFor: id, className: "tl-field-row__text" },
            h("span", { className: "tl-field-row__label" }, o.label),
            o.description ? h("span", { className: "tl-field-row__desc" }, o.description) : null));
      }));
  }
  function Textarea(p) {
    var id = useId(p.id), hintId = id + "-hint";
    var st = React.useState((p.defaultValue || "").length);
    var rest = Object.assign({}, p);
    ["label", "hint", "error", "className", "id", "maxLength", "onChange"].forEach(function (k) { delete rest[k]; });
    return h("div", { className: cx("tl-textfield", p.error && "has-error", p.className) },
      p.label ? h("label", { htmlFor: id, className: "tl-textfield__label" }, p.label) : null,
      h("div", { className: "tl-textfield__control" },
        h("textarea", Object.assign({ id: id, rows: 4, maxLength: p.maxLength, className: "tl-textfield__input tl-textarea", "aria-invalid": p.error ? true : undefined,
          "aria-describedby": hintId, "data-tl-count": p.maxLength ? hintId + "-count" : undefined,
          onChange: function (e) { st[1](e.target.value.length); if (p.onChange) p.onChange(e); } }, rest))),
      (p.error || p.hint || p.maxLength) ? h("p", { id: hintId, className: "tl-textfield__hint" },
        p.error ? h(Icon, { name: "close", size: 16 }) : null, h("span", null, p.error || p.hint || ""),
        p.maxLength ? h("span", { className: "tl-textfield__count", id: hintId + "-count" }, st[0] + " / " + p.maxLength) : null) : null);
  }
  function PasswordField(p) {
    var id = useId(p.id), hintId = id + "-hint";
    var st = React.useState(false), shown = st[0];
    var rest = Object.assign({}, p);
    ["label", "hint", "error", "className", "id"].forEach(function (k) { delete rest[k]; });
    return h("div", { className: cx("tl-textfield tl-password", p.error && "has-error", p.className) },
      p.label ? h("label", { htmlFor: id, className: "tl-textfield__label" }, p.label) : null,
      h("div", { className: "tl-textfield__control" },
        h("input", Object.assign({ id: id, type: shown ? "text" : "password", autoComplete: "current-password", spellCheck: false, className: "tl-textfield__input",
          "aria-invalid": p.error ? true : undefined, "aria-describedby": (p.error || p.hint) ? hintId : undefined }, rest)),
        h("button", { type: "button", className: "tl-iconbtn tl-btn--quiet tl-iconbtn--sm tl-password__toggle", "aria-label": shown ? "Hide password" : "Show password",
          "aria-pressed": shown ? "true" : "false", "aria-controls": id, "data-tl-password": id, onClick: function () { st[1](!shown); } },
          h(Icon, { name: shown ? "eye-off" : "eye", size: 16 }))),
      (p.error || p.hint) ? h("p", { id: hintId, className: "tl-textfield__hint" }, p.error ? h(Icon, { name: "close", size: 16 }) : null, p.error || p.hint) : null);
  }
  function CodeInput(p) {
    var id = useId(p.id), n = p.length || 6, half = p.split === false ? -1 : Math.floor(n / 2);
    var boxes = [];
    for (var i = 0; i < n; i++) {
      if (i === half) boxes.push(h("span", { key: "g", className: "tl-code__gap", "aria-hidden": true }));
      boxes.push(h("input", { key: i, id: i === 0 ? id : undefined, className: "tl-code__box", inputMode: "numeric", pattern: "[0-9]*", maxLength: 1,
        autoComplete: i === 0 ? "one-time-code" : "off", "aria-label": "Digit " + (i + 1) + " of " + n, defaultValue: (p.defaultValue || "")[i] }));
    }
    return h("fieldset", { className: cx("tl-code", p.error && "has-error", p.className), "data-tl-code": "" },
      h("legend", null, p.label || "Code"),
      h("div", { className: "tl-code__boxes" }, boxes),
      (p.error || p.hint) ? h("p", { className: "tl-textfield__hint" }, p.error ? h(Icon, { name: "close", size: 16 }) : null, p.error || p.hint) : null);
  }
  function Slider(p) {
    var id = useId(p.id), min = p.min || 0, max = p.max === undefined ? 100 : p.max;
    var st = React.useState(p.defaultValue !== undefined ? p.defaultValue : min), val = p.value !== undefined ? p.value : st[0];
    var fmt = p.format || function (v) { return String(v); };
    return h("div", { className: cx("tl-slider", p.className) },
      h("div", { className: "tl-slider__head" },
        h("label", { htmlFor: id, className: "tl-slider__label" }, p.label),
        h("output", { htmlFor: id, className: "tl-slider__value", id: id + "-out" }, fmt(val))),
      h("input", { id: id, type: "range", min: min, max: max, step: p.step || 1, value: val, className: "tl-slider__input", "data-tl-slider": id + "-out",
        "data-tl-unit": p.unit, "aria-valuetext": fmt(val), style: { "--tl-fill": ((val - min) / (max - min) * 100) + "%" },
        onChange: function (e) { var v = Number(e.target.value); st[1](v); if (p.onChange) p.onChange(v); } }),
      (p.minLabel || p.maxLabel) ? h("div", { className: "tl-slider__ends", "aria-hidden": true }, h("span", null, p.minLabel), h("span", null, p.maxLabel)) : null);
  }
  function Badge(p) {
    var tone = p.tone || "alert";
    var b = h("span", { className: cx("tl-badge", tone === "quiet" && "tl-badge--quiet", p.dot && "tl-badge--dot", p.className), "aria-hidden": p.label ? true : undefined }, p.dot ? null : p.count);
    var sr = p.label ? h("span", { className: "tl-sr" }, p.label) : null;
    if (!p.children) return h(React.Fragment, null, b, sr);
    return h("span", { className: "tl-badge-anchor" }, p.children, b, sr);
  }
  function Steps(p) {
    var cur = p.current || 1, steps = p.steps || [];
    return h("nav", { className: cx("tl-stepsnav", p.className), "aria-label": p.label || "Setup progress" },
      h("p", { className: "tl-steps__summary" }, "Step " + cur + " of " + steps.length + ": " + (steps[cur - 1] || "")),
      h("ol", { className: "tl-steps" }, steps.map(function (s, i) {
        return h("li", { key: s, className: cx("tl-steps__item", i + 1 < cur && "is-done"), "aria-current": i + 1 === cur ? "step" : undefined },
          h("span", { className: "tl-steps__bar", "aria-hidden": true }), h("span", { className: "tl-steps__label" }, s));
      })));
  }
  function ProgressBar(p) {
    var pct = p.value === undefined ? null : Math.max(0, Math.min(100, p.value));
    return h("div", { className: cx("tl-progress", pct === null && "tl-progress--indeterminate", p.className) },
      p.label ? h("div", { className: "tl-progress__head" }, h("span", null, p.label), pct !== null ? h("span", null, Math.round(pct) + "%") : null) : null,
      h("div", { className: "tl-progress__track", role: "progressbar", "aria-label": p.label, "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": pct === null ? undefined : pct },
        h("div", { className: "tl-progress__fill", style: pct === null ? undefined : { width: pct + "%" } })));
  }
  function DescriptionList(p) {
    return h("dl", { className: cx("tl-dl", p.className) }, (p.items || []).map(function (it) {
      return h("div", { key: it.label, className: "tl-dl__row" }, h("dt", null, it.label), h("dd", null, it.value));
    }));
  }
  function Skeleton(p) {
    var v = p.variant || "text";
    if (v === "row") return h("div", { className: "tl-skel-row", "aria-hidden": true },
      h("span", { className: "tl-skel tl-skel--circle", style: { width: 40, height: 40 } }),
      h("span", { className: "tl-skel-row__main" }, h("span", { className: "tl-skel tl-skel--text", style: { width: "45%" } }), h("span", { className: "tl-skel tl-skel--text", style: { width: "70%" } })));
    if (v === "circle") return h("span", { className: "tl-skel tl-skel--circle", style: { width: p.size || 40, height: p.size || 40 }, "aria-hidden": true });
    return h("span", { className: cx("tl-skel", "tl-skel--" + v, p.className), style: { width: p.width }, "aria-hidden": true });
  }
  function Disclosure(p) {
    return h("details", { className: cx("tl-disclosure", p.className), open: p.defaultOpen },
      h("summary", null, h("span", null, p.title), h(Icon, { name: "chevron-down", size: 20 })),
      h("div", { className: "tl-disclosure__body" }, p.children));
  }
  function Accordion(p) { return h("div", { className: cx("tl-accordion", p.className) }, p.children); }
  function StatTile(p) {
    return h("div", { className: cx("tl-stat", p.className) },
      h("span", { className: "tl-stat__label" }, p.label),
      h("span", { className: "tl-stat__value" }, p.value, p.unit ? h("span", { className: "tl-stat__unit" }, p.unit) : null),
      p.note ? h("span", { className: "tl-stat__note" }, p.trend ? h(Icon, { name: "trend-up", size: 16 }) : null, p.note) : null);
  }
  function Tabs(p) {
    var id = useId(p.id), tabs = p.tabs || [];
    var st = React.useState(p.defaultValue || (tabs[0] || {}).value), cur = p.value !== undefined ? p.value : st[0];
    function pick(v) { st[1](v); if (p.onChange) p.onChange(v); }
    return h("div", { className: cx("tl-tabs", p.className), "data-tl-tabs": "" },
      h("div", { className: "tl-tabs__list", role: "tablist", "aria-label": p.label }, tabs.map(function (t) {
        var sel = t.value === cur;
        return h("button", { key: t.value, type: "button", role: "tab", id: id + "-tab-" + t.value, "aria-selected": sel ? "true" : "false", "aria-controls": id + "-panel-" + t.value,
          tabIndex: sel ? 0 : -1, className: "tl-tabs__tab", onClick: function () { pick(t.value); } }, t.label, t.badge !== undefined ? h(Badge, { count: t.badge, tone: "quiet" }) : null);
      })),
      tabs.map(function (t) {
        return h("div", { key: t.value, role: "tabpanel", id: id + "-panel-" + t.value, "aria-labelledby": id + "-tab-" + t.value, tabIndex: 0, className: "tl-tabs__panel", hidden: t.value !== cur || undefined }, t.content);
      }));
  }

  // ---------- app layout ----------
  var BRAND_MARK = "<svg class=\"tl-brand__mark\" viewBox=\"10 14 222 146\" width=\"40\" height=\"27\" aria-hidden=\"true\"><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"5.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M37.6 91.5A16.9 16.9 0 0 1 20.6 72.6A14.9 14.9 0 0 1 23.7 50.7A12.9 12.9 0 0 1 41.1 37.0A15.8 15.8 0 0 1 65.9 33.6A20.5 20.5 0 0 1 92.9 49.1A17.7 17.7 0 0 1 93.7 74.2A13.9 13.9 0 0 1 78.3 91.3\"/><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"5.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M157.8 86.5A14.4 14.4 0 0 1 141.0 68.9A13.3 13.3 0 0 1 140.8 48.2A15.8 15.8 0 0 1 158.0 26.2A13.0 13.0 0 0 1 179.2 20.6A17.4 17.4 0 0 1 205.7 25.7A10.7 10.7 0 0 1 218.6 40.0A17.0 17.0 0 0 1 221.6 67.3A15.2 15.2 0 0 1 201.2 85.1\"/><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"5.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M53 102C52 122 50 138 46 152M63 102C64 122 66 138 70 152M175 100C174 120 172 138 168 152M185 100C186 120 188 138 192 152\"/><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"5.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M26 152C90 148 150 148 214 152\"/><path fill=\"none\" stroke=\"var(--bark)\" stroke-width=\"4.16\" stroke-linecap=\"round\" d=\"M78 94Q119 132 158 92\"/><path fill=\"var(--canopy)\" transform=\"translate(118 112) rotate(64) scale(1.2)\" d=\"M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z\"/></svg>";
  function Brand(p) {
    return h("a", { className: cx("tl-brand", p.className), href: p.href || "#", "aria-label": "Treeline home" },
      h("span", { className: "tl-brand__markwrap", dangerouslySetInnerHTML: { __html: BRAND_MARK } }), h("span", { className: "tl-brand__word" }, "Treeline"));
  }
  function NavBar(p) {
    return h("nav", { className: cx("tl-nav", p.className), "aria-label": p.label || "Main" },
      h("div", { className: "tl-nav__inner" },
        h("div", { className: "tl-nav__brand" }, p.brand || h(Brand)),
        h("ul", { className: "tl-nav__list" }, (p.items || []).map(function (it) {
          return h("li", { key: it.label },
            h("a", { className: "tl-nav__item", href: it.href || "#", "aria-current": it.current ? "page" : undefined, onClick: it.onClick },
              it.badge !== undefined ? h(Badge, { count: it.badge, label: it.badgeLabel || (it.badge + " waiting") }, h(Icon, { name: it.icon, size: 24 })) : h(Icon, { name: it.icon, size: 24 }), h("span", { className: "tl-nav__label" }, it.label)));
        })),
        p.footer ? h("div", { className: "tl-nav__foot" }, p.footer) : null));
  }
  function AppBar(p) {
    return h("header", { className: cx("tl-appbar", p.className) },
      p.lead ? h("div", { className: "tl-appbar__lead" }, p.lead) : null,
      h("h1", { className: "tl-appbar__title" }, p.title),
      p.actions ? h("div", { className: "tl-appbar__actions" }, p.actions) : null);
  }
  function AppShell(p) {
    return h("div", { className: cx("tl-app", p.className), style: p.style },
      h("div", { className: "tl-app__layout" },
        p.bar || null,
        h("main", { className: "tl-app__main" }, p.children),
        p.nav || null),
      p.overlay || null);
  }
  function Sheet(p) {
    if (p.open === false) return null;
    return h("div", { className: "tl-sheet-scrim", id: p.id, hidden: p.hidden || undefined, onClick: function (e) { if (e.target === e.currentTarget && p.onClose) p.onClose(); } },
      h("div", { className: cx("tl-sheet", p.className), role: "dialog", "aria-modal": "true", "aria-labelledby": p.id ? p.id + "-title" : undefined },
        h("span", { className: "tl-sheet__grabber", "aria-hidden": true }),
        h("div", { className: "tl-sheet__head" },
          h("h2", { className: "tl-sheet__title", id: p.id ? p.id + "-title" : undefined }, p.title),
          h(IconButton, { icon: "close", label: "Close", className: "tl-sheet__close", onClick: p.onClose })),
        p.children,
        p.actions ? h("div", { className: "tl-actions" }, p.actions) : null));
  }
  var api = { Icon: Icon, Button: Button, IconButton: IconButton, Tag: Tag, Presence: Presence, Avatar: Avatar,
    Switch: Switch, Checkbox: Checkbox, TextField: TextField, Card: Card,
    FriendRow: FriendRow, ApprovalCard: ApprovalCard, QuietHours: QuietHours, CallLogItem: CallLogItem,
    Illustration: Illustration, EmptyState: EmptyState, LeafDivider: LeafDivider, LeafLoader: LeafLoader, Alert: Alert, Toast: Toast, Toasts: Toasts, Select: Select, TimeField: TimeField, TimeRange: TimeRange, SegmentedControl: SegmentedControl, Menu: Menu, RadioGroup: RadioGroup, Textarea: Textarea, PasswordField: PasswordField, CodeInput: CodeInput, Slider: Slider, Badge: Badge, Steps: Steps, ProgressBar: ProgressBar, DescriptionList: DescriptionList, Skeleton: Skeleton, Disclosure: Disclosure, Accordion: Accordion, StatTile: StatTile, Tabs: Tabs, Brand: Brand, NavBar: NavBar, AppBar: AppBar, AppShell: AppShell, Sheet: Sheet, illustrationNames: Object.keys(ART),
    iconNames: Object.keys(ICONS) };
  window.Treeline = Object.assign(window.Treeline || {}, api);
})();
