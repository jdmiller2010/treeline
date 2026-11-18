/* @ds-bundle: {"format": 4, "namespace": "Treeline", "components": [{"name": "Icon"}, {"name": "Button"}, {"name": "IconButton"}, {"name": "Tag"}, {"name": "Presence"}, {"name": "Avatar"}, {"name": "Switch"}, {"name": "Checkbox"}, {"name": "TextField"}, {"name": "Card"}, {"name": "FriendRow"}, {"name": "ApprovalCard"}, {"name": "QuietHours"}, {"name": "CallLogItem"}, {"name": "Illustration"}, {"name": "EmptyState"}, {"name": "LeafDivider"}, {"name": "LeafLoader"}, {"name": "NavBar"}, {"name": "AppBar"}, {"name": "AppShell"}, {"name": "Sheet"}, {"name": "Alert"}, {"name": "Toast"}, {"name": "Select"}, {"name": "TimeField"}, {"name": "TimeRange"}, {"name": "SegmentedControl"}, {"name": "Menu"}, {"name": "RadioGroup"}, {"name": "Textarea"}, {"name": "PasswordField"}, {"name": "CodeInput"}, {"name": "Slider"}, {"name": "Badge"}, {"name": "Steps"}, {"name": "ProgressBar"}, {"name": "DescriptionList"}, {"name": "Skeleton"}, {"name": "Disclosure"}, {"name": "Accordion"}, {"name": "StatTile"}, {"name": "Tabs"}, {"name": "RotaryPhone"}]} */
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

  var ROTARY_SVG = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"tl-rotary__svg\" tabindex=\"0\" role=\"img\" aria-label=\"Rotary dial. Drag a number round to the finger stop and let go, or press a number key.\" viewBox=\"0 0 400 440\" width=\"400\" height=\"440\"><defs>\n<filter id=\"tlp-wobble\" x=\"-5%\" y=\"-5%\" width=\"110%\" height=\"110%\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.035\" numOctaves=\"2\" seed=\"4\"/><feDisplacementMap in=\"SourceGraphic\" scale=\"1.6\"/></filter>\n<filter id=\"tlp-wash\" x=\"-10%\" y=\"-10%\" width=\"120%\" height=\"120%\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.022\" numOctaves=\"3\" seed=\"9\" result=\"n\"/><feDisplacementMap in=\"SourceGraphic\" in2=\"n\" scale=\"5\"/><feGaussianBlur stdDeviation=\"0.5\"/></filter>\n<filter id=\"tlp-grain\" x=\"0\" y=\"0\" width=\"100%\" height=\"100%\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"2\" seed=\"3\"/><feColorMatrix values=\"0 0 0 0 0.16  0 0 0 0 0.13  0 0 0 0 0.08  0 0 0 -1.6 1.05\"/><feComposite in2=\"SourceGraphic\" operator=\"in\"/></filter>\n<filter id=\"tlp-edge\" x=\"-5%\" y=\"-5%\" width=\"110%\" height=\"110%\"><feGaussianBlur stdDeviation=\"2.2\"/></filter>\n<filter id=\"tlp-soft\" x=\"-30%\" y=\"-60%\" width=\"160%\" height=\"220%\"><feGaussianBlur stdDeviation=\"8\"/></filter>\n<linearGradient id=\"tlp-body\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" style=\"stop-color:var(--tlp-l)\"/><stop offset=\".5\" style=\"stop-color:var(--tlp-m)\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-d)\"/></linearGradient>\n<linearGradient id=\"tlp-side\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\"><stop offset=\"0\" style=\"stop-color:var(--tlp-s)\" stop-opacity=\".6\"/><stop offset=\".14\" style=\"stop-color:var(--tlp-s)\" stop-opacity=\"0\"/><stop offset=\".86\" style=\"stop-color:var(--tlp-s)\" stop-opacity=\"0\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-s)\" stop-opacity=\".65\"/></linearGradient>\n<linearGradient id=\"tlp-deck\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" style=\"stop-color:var(--tlp-l)\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-m)\"/></linearGradient>\n<linearGradient id=\"tlp-post\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\"><stop offset=\"0\" style=\"stop-color:var(--tlp-l)\"/><stop offset=\".55\" style=\"stop-color:var(--tlp-m)\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-d)\"/></linearGradient>\n<linearGradient id=\"tlp-hand\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" style=\"stop-color:var(--tlp-l)\"/><stop offset=\".5\" style=\"stop-color:var(--tlp-m)\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-d)\"/></linearGradient>\n<linearGradient id=\"tlp-cup\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" style=\"stop-color:var(--tlp-l)\"/><stop offset=\".35\" style=\"stop-color:var(--tlp-m)\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-d)\"/></linearGradient>\n<radialGradient id=\"tlp-plate\" cx=\".45\" cy=\".35\" r=\".8\"><stop offset=\"0\" stop-color=\"#fffaf0\"/><stop offset=\"1\" stop-color=\"#eadfc6\"/></radialGradient>\n<radialGradient id=\"tlp-card\" cx=\".45\" cy=\".35\" r=\".75\"><stop offset=\"0\" stop-color=\"#fffdf6\"/><stop offset=\"1\" stop-color=\"#f1e7d2\"/></radialGradient>\n<radialGradient id=\"tlp-wheelfill\" cx=\".4\" cy=\".3\" r=\".9\"><stop offset=\"0\" stop-color=\"#ffffff\" stop-opacity=\".55\"/><stop offset=\".7\" stop-color=\"#ffffff\" stop-opacity=\".14\"/><stop offset=\"1\" style=\"stop-color:var(--tlp-s)\" stop-opacity=\".3\"/></radialGradient>\n<linearGradient id=\"tlp-metal\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop offset=\"0\" stop-color=\"#f6f3ec\"/><stop offset=\".5\" stop-color=\"#bdb6a8\"/><stop offset=\"1\" stop-color=\"#7d766a\"/></linearGradient>\n<clipPath id=\"tlp-faceclip\"><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\"/></clipPath>\n</defs><g class=\"tlp-deck\"><ellipse cx=\"200\" cy=\"410\" rx=\"178\" ry=\"17\" style=\"fill:var(--tlp-s)\" opacity=\".3\" filter=\"url(#tlp-soft)\"/><g filter=\"url(#tlp-wash)\" transform=\"translate(1.5 1.5)\"><path d=\"M118 182 C118 164 126 150 140 148 L260 148 C274 150 282 164 282 182 Z\" style=\"fill:var(--tlp-d)\"/><path d=\"M126 182 C126 168 132 158 144 156 L256 156 C268 158 274 168 274 182 Z\" style=\"fill:var(--tlp-s)\" opacity=\".45\"/></g><g filter=\"url(#tlp-wobble)\"><path d=\"M118 182 C118 164 126 150 140 148 L260 148 C274 150 282 164 282 182 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></g></g><g class=\"tlp-cord\"><path class=\"tlp-cord-color\" d=\"M76.5 351.7 L74.9 349.1 L71.8 347.0 L67.9 345.9 L64.1 345.6 L61.1 346.2 L59.7 347.2 L60.0 348.1 L61.8 348.4 L64.5 347.8 L67.1 346.3 L68.7 344.1 L68.9 341.4 L67.3 338.8 L64.3 336.7 L60.4 335.5 L56.5 335.3 L53.6 335.9 L52.2 336.8 L52.6 337.7 L54.4 338.1 L57.1 337.5 L59.7 336.0 L61.4 333.7 L61.6 331.0 L60.1 328.4 L57.0 326.4 L53.2 325.2 L49.4 325.0 L46.5 325.5 L45.2 326.5 L45.6 327.4 L47.5 327.7 L50.2 327.2 L52.9 325.7 L54.7 323.4 L54.9 320.7 L53.5 318.1 L50.5 316.0 L46.7 314.8 L43.0 314.6 L40.2 315.2 L38.9 316.1 L39.4 317.0 L41.4 317.3 L44.2 316.8 L46.9 315.3 L48.8 313.0 L49.1 310.3 L47.7 307.7 L44.9 305.6 L41.2 304.4 L37.5 304.2 L34.8 304.7 L33.6 305.7 L34.2 306.6 L36.3 306.9 L39.2 306.3 L42.0 304.8 L44.0 302.5 L44.4 299.8 L43.1 297.2 L40.4 295.1 L36.8 293.9 L33.2 293.7 L30.6 294.3 L29.6 295.2 L30.2 296.1 L32.4 296.4 L35.4 295.8 L38.4 294.3 L40.4 292.0 L41.0 289.3 L39.8 286.7 L37.2 284.6 L33.7 283.4 L30.3 283.2 L27.8 283.7 L26.8 284.7 L27.6 285.5 L29.9 285.8 L33.0 285.2 L36.1 283.7 L38.3 281.4 L39.0 278.7 L37.9 276.1 L35.4 274.0 L32.0 272.8 L28.8 272.5 L26.4 273.1 L25.6 274.0 L26.5 274.9 L28.9 275.2 L32.1 274.6 L35.3 273.1 L37.7 270.8 L38.5 268.0 L37.5 265.4 L35.1 263.3 L31.9 262.1 L28.7 261.9 L26.5 262.4 L25.8 263.3 L26.8 264.2 L29.3 264.5 L32.7 263.9 L36.0 262.3 L38.5 260.0 L39.4 257.3 L38.6 254.7 L36.3 252.6 L33.2 251.3 L30.1 251.1 L28.0 251.6 L27.4 252.5 L28.6 253.4 L31.2 253.7 L34.7 253.1 L38.2 251.5 L40.7 249.2 L41.8 246.5 L41.0 243.8 L38.9 241.7 L35.9 240.5 L32.9 240.3 L30.9 240.8 L30.4 241.7 L31.7 242.5 L34.5 242.8 L38.1 242.2 L41.6 240.7 L44.3 238.3 L45.4 235.6 L44.8 233.0 L42.7 230.9 L39.8 229.6 L37.0 229.4 L35.0 229.9 L34.7 230.8 L36.0 231.6 L38.9 231.9 L42.5 231.3 L46.2 229.8 L48.9 227.4 L50.1 224.7 L49.6 222.0 L47.6 219.9 L44.8 218.7 L42.0 218.4 L40.2 218.9 L39.9 219.8 L41.3 220.7 L44.2 220.9 L48.0 220.3 L51.7 218.8 L54.5 216.4 L55.7 213.7 L55.3 211.0 L53.3 208.9 L50.6 207.7 L47.9 207.4 L46.1 207.9 L45.8 208.8 L47.3 209.7 L50.3 209.9 L54.1 209.3 L57.8 207.8 L60.7 205.4 L62.0 202.7 L61.5 200.0 L59.6 197.9 L56.9 196.7 L54.2 196.4 L52.5 196.9 L52.2 197.8 L53.7 198.7 L56.7 198.9 L60.5 198.3 L64.3 196.8 L67.2 194.4 L68.5 191.7\" fill=\"none\" style=\"stroke:var(--tlp-d)\" stroke-width=\"3.4\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path class=\"tlp-cord-ink\" d=\"M76.5 351.7 L74.9 349.1 L71.8 347.0 L67.9 345.9 L64.1 345.6 L61.1 346.2 L59.7 347.2 L60.0 348.1 L61.8 348.4 L64.5 347.8 L67.1 346.3 L68.7 344.1 L68.9 341.4 L67.3 338.8 L64.3 336.7 L60.4 335.5 L56.5 335.3 L53.6 335.9 L52.2 336.8 L52.6 337.7 L54.4 338.1 L57.1 337.5 L59.7 336.0 L61.4 333.7 L61.6 331.0 L60.1 328.4 L57.0 326.4 L53.2 325.2 L49.4 325.0 L46.5 325.5 L45.2 326.5 L45.6 327.4 L47.5 327.7 L50.2 327.2 L52.9 325.7 L54.7 323.4 L54.9 320.7 L53.5 318.1 L50.5 316.0 L46.7 314.8 L43.0 314.6 L40.2 315.2 L38.9 316.1 L39.4 317.0 L41.4 317.3 L44.2 316.8 L46.9 315.3 L48.8 313.0 L49.1 310.3 L47.7 307.7 L44.9 305.6 L41.2 304.4 L37.5 304.2 L34.8 304.7 L33.6 305.7 L34.2 306.6 L36.3 306.9 L39.2 306.3 L42.0 304.8 L44.0 302.5 L44.4 299.8 L43.1 297.2 L40.4 295.1 L36.8 293.9 L33.2 293.7 L30.6 294.3 L29.6 295.2 L30.2 296.1 L32.4 296.4 L35.4 295.8 L38.4 294.3 L40.4 292.0 L41.0 289.3 L39.8 286.7 L37.2 284.6 L33.7 283.4 L30.3 283.2 L27.8 283.7 L26.8 284.7 L27.6 285.5 L29.9 285.8 L33.0 285.2 L36.1 283.7 L38.3 281.4 L39.0 278.7 L37.9 276.1 L35.4 274.0 L32.0 272.8 L28.8 272.5 L26.4 273.1 L25.6 274.0 L26.5 274.9 L28.9 275.2 L32.1 274.6 L35.3 273.1 L37.7 270.8 L38.5 268.0 L37.5 265.4 L35.1 263.3 L31.9 262.1 L28.7 261.9 L26.5 262.4 L25.8 263.3 L26.8 264.2 L29.3 264.5 L32.7 263.9 L36.0 262.3 L38.5 260.0 L39.4 257.3 L38.6 254.7 L36.3 252.6 L33.2 251.3 L30.1 251.1 L28.0 251.6 L27.4 252.5 L28.6 253.4 L31.2 253.7 L34.7 253.1 L38.2 251.5 L40.7 249.2 L41.8 246.5 L41.0 243.8 L38.9 241.7 L35.9 240.5 L32.9 240.3 L30.9 240.8 L30.4 241.7 L31.7 242.5 L34.5 242.8 L38.1 242.2 L41.6 240.7 L44.3 238.3 L45.4 235.6 L44.8 233.0 L42.7 230.9 L39.8 229.6 L37.0 229.4 L35.0 229.9 L34.7 230.8 L36.0 231.6 L38.9 231.9 L42.5 231.3 L46.2 229.8 L48.9 227.4 L50.1 224.7 L49.6 222.0 L47.6 219.9 L44.8 218.7 L42.0 218.4 L40.2 218.9 L39.9 219.8 L41.3 220.7 L44.2 220.9 L48.0 220.3 L51.7 218.8 L54.5 216.4 L55.7 213.7 L55.3 211.0 L53.3 208.9 L50.6 207.7 L47.9 207.4 L46.1 207.9 L45.8 208.8 L47.3 209.7 L50.3 209.9 L54.1 209.3 L57.8 207.8 L60.7 205.4 L62.0 202.7 L61.5 200.0 L59.6 197.9 L56.9 196.7 L54.2 196.4 L52.5 196.9 L52.2 197.8 L53.7 198.7 L56.7 198.9 L60.5 198.3 L64.3 196.8 L67.2 194.4 L68.5 191.7\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\".9\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".7\"/></g><g class=\"tlp-handset\" ><g filter=\"url(#tlp-wash)\" transform=\"translate(1.5 1.5)\"><path d=\"M96 112 C138 100 262 100 304 112 C310 114 312 124 308 132 C264 124 136 124 92 132 C88 124 90 114 96 112 Z\" fill=\"url(#tlp-hand)\"/><path d=\"M100 108 C140 98 260 98 300 108 L300 118 C260 110 140 110 100 118 Z\" style=\"fill:var(--tlp-l)\" opacity=\".6\"/><path d=\"M124 106 C170 100 230 100 276 106\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".55\" stroke-width=\"3\" stroke-linecap=\"round\"/></g><g filter=\"url(#tlp-wobble)\"><path d=\"M96 112 C138 100 262 100 304 112 C310 114 312 124 308 132 C264 124 136 124 92 132 C88 124 90 114 96 112 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M100 118 C140 110 260 110 300 118\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/></g><g filter=\"url(#tlp-wash)\" transform=\"translate(1.5 1.5)\"><path d=\"M54 120 C54 106 72 100 94 100 C116 100 134 106 134 120 C138 150 140 176 132 194 C124 206 64 206 56 194 C48 176 50 150 54 120 Z\" fill=\"url(#tlp-cup)\"/><path d=\"M66 108 C80 103 108 103 122 108\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".55\" stroke-width=\"3\" stroke-linecap=\"round\"/><path d=\"M60 124 C58 146 58 166 62 184\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".32\" stroke-width=\"5\" stroke-linecap=\"round\"/><path d=\"M54 120 C54 106 72 100 94 100 C116 100 134 106 134 120 C138 150 140 176 132 194 C124 206 64 206 56 194 C48 176 50 150 54 120 Z\" fill=\"none\" style=\"stroke:var(--tlp-s)\" stroke-opacity=\".45\" stroke-width=\"7\" filter=\"url(#tlp-edge)\"/><path d=\"M266 120 C266 106 284 100 306 100 C328 100 346 106 346 120 C350 150 352 176 344 194 C336 206 276 206 268 194 C260 176 262 150 266 120 Z\" fill=\"url(#tlp-cup)\"/><path d=\"M278 108 C292 103 320 103 334 108\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".55\" stroke-width=\"3\" stroke-linecap=\"round\"/><path d=\"M272 124 C270 146 270 166 274 184\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".32\" stroke-width=\"5\" stroke-linecap=\"round\"/><path d=\"M266 120 C266 106 284 100 306 100 C328 100 346 106 346 120 C350 150 352 176 344 194 C336 206 276 206 268 194 C260 176 262 150 266 120 Z\" fill=\"none\" style=\"stroke:var(--tlp-s)\" stroke-opacity=\".45\" stroke-width=\"7\" filter=\"url(#tlp-edge)\"/></g><g filter=\"url(#tlp-wobble)\"><path d=\"M54 120 C54 106 72 100 94 100 C116 100 134 106 134 120 C138 150 140 176 132 194 C124 206 64 206 56 194 C48 176 50 150 54 120 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M266 120 C266 106 284 100 306 100 C328 100 346 106 346 120 C350 150 352 176 344 194 C336 206 276 206 268 194 C260 176 262 150 266 120 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M58 122 C80 114 110 114 132 122\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/><path d=\"M268 122 C290 114 320 114 342 122\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/></g></g><g class=\"tlp-base\"><g filter=\"url(#tlp-wash)\" transform=\"translate(1.5 1.5)\"><path d=\"M62 386 C62 380 68 378 76 378 L324 378 C332 378 338 380 338 386 L338 396 C338 402 332 406 324 406 L76 406 C68 406 62 402 62 396 Z\" style=\"fill:var(--tlp-d)\"/></g><g filter=\"url(#tlp-wobble)\"><path d=\"M62 386 C62 380 68 378 76 378 L324 378 C332 378 338 380 338 386 L338 396 C338 402 332 406 324 406 L76 406 C68 406 62 402 62 396 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></g><path d=\"M70 383 L330 383\" stroke=\"#ffffff\" stroke-opacity=\".35\" stroke-width=\"2\" fill=\"none\"/><g filter=\"url(#tlp-wash)\" transform=\"translate(1.5 1.5)\"><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\" fill=\"url(#tlp-body)\"/><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\" fill=\"url(#tlp-side)\"/><g clip-path=\"url(#tlp-faceclip)\"><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\" fill=\"none\" style=\"stroke:var(--tlp-s)\" stroke-opacity=\".55\" stroke-width=\"12\" filter=\"url(#tlp-edge)\"/></g><path d=\"M96 192 C94 240 90 300 84 360\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".38\" stroke-width=\"6\" stroke-linecap=\"round\"/><path d=\"M100 184 L300 184\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".5\" stroke-width=\"3\" stroke-linecap=\"round\"/><ellipse cx=\"200\" cy=\"297\" rx=\"102\" ry=\"94.9\" style=\"fill:var(--tlp-s)\" opacity=\".35\" filter=\"url(#tlp-edge)\"/><path d=\"M135 182 L138 128 C138 120 143 116 149 116 L155 116 C161 116 166 120 166 128 L169 182 Z\" fill=\"url(#tlp-post)\"/><path d=\"M144 126 L142 176\" stroke=\"#ffffff\" stroke-opacity=\".45\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M231 182 L234 128 C234 120 239 116 245 116 L251 116 C257 116 262 120 262 128 L265 182 Z\" fill=\"url(#tlp-post)\"/><path d=\"M240 126 L238 176\" stroke=\"#ffffff\" stroke-opacity=\".45\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/></g><g opacity=\".16\" filter=\"url(#tlp-grain)\"><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\" fill=\"#000\"/></g><g filter=\"url(#tlp-wobble)\"><path d=\"M80 188 C80 180 88 176 98 176 L302 176 C312 176 320 180 320 188 L334 368 C335 380 327 388 314 388 L86 388 C73 388 65 380 66 368 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M135 182 L138 128 C138 120 143 116 149 116 L155 116 C161 116 166 120 166 128 L169 182 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M231 182 L234 128 C234 120 239 116 245 116 L251 116 C257 116 262 120 262 128 L265 182 Z\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></g><ellipse cx=\"200\" cy=\"292\" rx=\"92\" ry=\"85.56\" fill=\"url(#tlp-plate)\"/><g filter=\"url(#tlp-wobble)\"><ellipse cx=\"200\" cy=\"292\" rx=\"92\" ry=\"85.56\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></g><text x=\"273.7\" y=\"260.5\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">1</text><text x=\"244.2\" y=\"231.1\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">2</text><text x=\"202.9\" y=\"219.4\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">3</text><text x=\"160.8\" y=\"228.4\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">4</text><text x=\"129.2\" y=\"255.8\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">5</text><text x=\"116.6\" y=\"294.3\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">6</text><text x=\"126.3\" y=\"333.5\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">7</text><text x=\"155.8\" y=\"362.9\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">8</text><text x=\"197.1\" y=\"374.6\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">9</text><text x=\"239.2\" y=\"365.6\" text-anchor=\"middle\" font-family=\"Fraunces, Georgia, serif\" font-size=\"14\" font-weight=\"500\" fill=\"#2a251c\">0</text></g><g class=\"tlp-card\"><ellipse cx=\"200\" cy=\"292\" rx=\"73\" ry=\"67.89\" style=\"fill:var(--tlp-s)\" opacity=\".25\"/><ellipse cx=\"200\" cy=\"292\" rx=\"71\" ry=\"66.03\" fill=\"url(#tlp-plate)\"/><circle cx=\"250.9\" cy=\"266.8\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"230.6\" cy=\"246.5\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"202.0\" cy=\"238.4\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"172.9\" cy=\"244.6\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"151.1\" cy=\"263.6\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"142.4\" cy=\"290.1\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"149.1\" cy=\"317.2\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"169.4\" cy=\"337.5\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"198.0\" cy=\"345.6\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><circle cx=\"227.1\" cy=\"339.4\" r=\"1.8\" fill=\"#2a251c\" opacity=\".55\"/><ellipse cx=\"200\" cy=\"292\" rx=\"33\" ry=\"30.69\" fill=\"url(#tlp-card)\"/><g filter=\"url(#tlp-wobble)\"><ellipse cx=\"200\" cy=\"292\" rx=\"33\" ry=\"30.69\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/></g><path d=\"M174 281 C188 276 212 276 226 281\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/><path d=\"M174 305 C188 310 212 310 226 305\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/><text class=\"tl-rotary__number\" x=\"200\" y=\"297.5\" text-anchor=\"middle\" font-family=\"Figtree, Helvetica, sans-serif\" font-size=\"15\" font-weight=\"600\" letter-spacing=\"1.5\" fill=\"#2a251c\">{{NUMBER}}</text></g><g transform=\"translate(200 292) scale(1 0.9300) translate(-200 -292)\"><g class=\"tlp-wheel\" transform=\"rotate(0 200 292)\"><path d=\"M273 292 A73 73 0 1 1 127 292 A73 73 0 1 1 273 292 Z M236 292 A36 36 0 1 0 164 292 A36 36 0 1 0 236 292 Z M262.4 264.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM242.1 243.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM213.5 234.4 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM184.4 241.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM162.6 261.4 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM153.9 290.0 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM160.6 319.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM180.9 340.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM209.5 349.6 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM238.6 342.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 Z\" fill-rule=\"evenodd\" fill=\"url(#tlp-wheelfill)\"/><path d=\"M273 292 A73 73 0 1 1 127 292 A73 73 0 1 1 273 292 Z M236 292 A36 36 0 1 0 164 292 A36 36 0 1 0 236 292 Z M262.4 264.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM242.1 243.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM213.5 234.4 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM184.4 241.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM162.6 261.4 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM153.9 290.0 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM160.6 319.1 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM180.9 340.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM209.5 349.6 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 ZM238.6 342.9 a11.5 11.5 0 1 0 -23.0 0 a11.5 11.5 0 1 0 23.0 0 Z\" fill-rule=\"evenodd\" style=\"fill:var(--tlp-l)\" opacity=\".14\"/><g filter=\"url(#tlp-wobble)\"><circle cx=\"200\" cy=\"292\" r=\"73\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"200\" cy=\"292\" r=\"36\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.1\" stroke-linecap=\"round\" stroke-linejoin=\"round\" opacity=\".65\"/><circle cx=\"250.9\" cy=\"264.9\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M242.3 267.2 A11.5 11.5 0 0 1 253.2 256.3\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"230.6\" cy=\"243.1\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M221.9 245.4 A11.5 11.5 0 0 1 232.9 234.5\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"202.0\" cy=\"234.4\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M193.4 236.7 A11.5 11.5 0 0 1 204.3 225.7\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"172.9\" cy=\"241.1\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M164.3 243.4 A11.5 11.5 0 0 1 175.2 232.5\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"151.1\" cy=\"261.4\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M142.5 263.7 A11.5 11.5 0 0 1 153.4 252.8\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"142.4\" cy=\"290.0\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M133.7 292.3 A11.5 11.5 0 0 1 144.7 281.4\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"149.1\" cy=\"319.1\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M140.5 321.4 A11.5 11.5 0 0 1 151.4 310.4\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"169.4\" cy=\"340.9\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M160.8 343.2 A11.5 11.5 0 0 1 171.7 332.3\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"198.0\" cy=\"349.6\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M189.4 351.9 A11.5 11.5 0 0 1 200.3 341.0\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"227.1\" cy=\"342.9\" r=\"11.5\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.7\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M218.4 345.2 A11.5 11.5 0 0 1 229.4 334.3\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".8\" stroke-width=\"1.5\" stroke-linecap=\"round\"/></g></g></g><g class=\"tlp-glare\"><path d=\"M142 254 C160 232 200 222 230 230\" fill=\"none\" stroke=\"#ffffff\" stroke-opacity=\".6\" stroke-width=\"3.5\" stroke-linecap=\"round\"/><path d=\"M268.8 329.1 Q262.3 320.4 240.9 316.7\" fill=\"none\" stroke=\"url(#tlp-metal)\" stroke-width=\"7\" stroke-linecap=\"round\"/><g filter=\"url(#tlp-wobble)\"><path d=\"M268.8 329.1 Q262.3 320.4 240.9 316.7\" fill=\"none\" stroke=\"#2a251c\" stroke-width=\"1.3\" stroke-linecap=\"round\" opacity=\".8\"/></g></g></svg>";
  var ROTARY_ALERT = '<svg class="tl-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 4.6a2 2 0 0 1 3.4 0l7.4 12.9A2 2 0 0 1 19.4 20.5H4.6a2 2 0 0 1-1.7-3z"/><path d="M12 9.5v4.5"/><path d="M12 17v.01"/></svg>';
  function rotaryMarkup(prefix, number) {
    return ROTARY_SVG.replace(/id="tlp-/g, 'id="' + prefix + '-').replace(/url\(#tlp-/g, "url(#" + prefix + "-").replace("{{NUMBER}}", number || "");
  }
  function RotaryPhone(p) {
    var ref = React.useRef(null), pfx = useId(p.id).replace(/[^a-zA-Z0-9-]/g, "") + "-p";
    var cb = React.useRef(p); cb.current = p;
    React.useEffect(function () {
      var root = ref.current, api = attachRotary(root);
      function hook(e) { if (cb.current.onHook) cb.current.onHook(e.detail.offHook); }
      function digit(e) { if (cb.current.onDigit && e.detail.offHook) cb.current.onDigit(e.detail.digit); }
      function pulse(e) { if (cb.current.onPulse) cb.current.onPulse(e.detail); }
      root.addEventListener("tl-rotary-hook", hook); root.addEventListener("tl-rotary-digit", digit); root.addEventListener("tl-rotary-pulse", pulse);
      if (p.apiRef) p.apiRef.current = api;
      return function () { root.removeEventListener("tl-rotary-hook", hook); root.removeEventListener("tl-rotary-digit", digit); root.removeEventListener("tl-rotary-pulse", pulse); };
    }, []);
    React.useEffect(function () {
      if (p.offHook === undefined || !ref.current || !ref.current.__tlRotary) return;
      ref.current.__tlRotary.setHook(!!p.offHook, true);
    }, [p.offHook]);
    var markup = React.useMemo(function () { return rotaryMarkup(pfx, p.number); }, [pfx, p.number]);
    return h("div", { ref: ref, className: cx("tl-rotary", "tl-rotary--" + (p.colorway || "moss"), p.className), "data-tl-rotary": "", "data-hook": p.defaultOffHook || p.offHook ? "off" : "on" },
      h("div", { className: "tl-rotary__art", dangerouslySetInnerHTML: { __html: markup } }),
      h("button", { type: "button", className: "tl-rotary__hook", "aria-pressed": (p.defaultOffHook || p.offHook) ? "true" : "false", "aria-label": (p.defaultOffHook || p.offHook) ? "Hang up" : "Lift the handset" }),
      p.notice === false ? null : h("p", { className: "tl-rotary__notice" }, h("span", { dangerouslySetInnerHTML: { __html: ROTARY_ALERT } }), "Can’t call 911 or outside numbers"));
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
    Illustration: Illustration, EmptyState: EmptyState, LeafDivider: LeafDivider, LeafLoader: LeafLoader, Alert: Alert, Toast: Toast, Toasts: Toasts, Select: Select, TimeField: TimeField, TimeRange: TimeRange, SegmentedControl: SegmentedControl, Menu: Menu, RadioGroup: RadioGroup, Textarea: Textarea, PasswordField: PasswordField, CodeInput: CodeInput, Slider: Slider, Badge: Badge, Steps: Steps, ProgressBar: ProgressBar, DescriptionList: DescriptionList, Skeleton: Skeleton, Disclosure: Disclosure, Accordion: Accordion, StatTile: StatTile, Tabs: Tabs, RotaryPhone: RotaryPhone, Brand: Brand, NavBar: NavBar, AppBar: AppBar, AppShell: AppShell, Sheet: Sheet, illustrationNames: Object.keys(ART),
    iconNames: Object.keys(ICONS) };
  window.Treeline = Object.assign(window.Treeline || {}, api);
})();
