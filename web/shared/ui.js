// Builds the design system's markup. Classes and nesting match design/ui/components exactly.
// `html` escapes every interpolated value unless it is already markup built here.
import { ART, BRAND, ICONS } from "./assets.js";
import { initials } from "./format.js";

class Safe { constructor(s) { this.s = s; } toString() { return this.s; } }
export const raw = (s) => new Safe(String(s));
export function esc(v) {
  return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function one(v) {
  if (v == null || v === false) return "";
  if (v instanceof Safe) return v.s;
  if (Array.isArray(v)) return v.map(one).join("");
  return esc(v);
}
export function html(strings, ...vals) {
  let out = strings[0];
  vals.forEach((v, i) => { out += one(v) + strings[i + 1]; });
  return new Safe(out);
}
export const join = (items, sep = "") => raw(items.map(one).join(sep));
export const str = (v) => one(v);

// ---------------------------------------------------------------- atoms

/**
 * Extra attributes for a control. Pass an object ({ "data-name": theirName }) for
 * anything that comes from data: every value is escaped. A plain string is for
 * fixed markup the developer wrote ('data-add-phone') and is NOT escaped, so never
 * build one from names, emails or anything a user can type.
 */
export function attrList(attrs) {
  if (!attrs) return raw("");
  if (typeof attrs === "string") return raw(attrs);
  return raw(Object.entries(attrs).map(([k, v]) => (v === true ? ` ${k}` : ` ${k}="${esc(v)}"`)).join(""));
}

export function icon(name, size = 20) {
  if (!ICONS[name]) throw new Error("no icon " + name);
  return raw(`<svg class="tl-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`);
}
export const art = (name, width) => raw(width ? ART[name].replace("<svg ", `<svg style="width:${width}px;height:auto" `) : ART[name]);
export const brand = (href = "#/home") => raw(BRAND.replace('href="#home"', `href="${esc(href)}"`));

export function button({ label, variant = "secondary", size = "md", icon: ic, iconAfter, type = "button", full, collapse, attrs = "", disabled }) {
  const cls = `tl-btn tl-btn--${variant} tl-btn--${size}${full ? " tl-btn--full" : ""}${collapse ? " tl-btn--collapse" : ""}`;
  return html`<button type="${type}" class="${cls}" ${attrList(attrs)}${disabled ? raw(" disabled") : ""}>${ic ? icon(ic, size === "sm" ? 16 : 20) : ""}<span class="tl-btn__label">${label}</span>${iconAfter ? icon(iconAfter, size === "sm" ? 16 : 20) : ""}</button>`;
}

export function iconButton({ label, name, variant = "quiet", size = "md", attrs = "", extra = "" }) {
  return html`<button type="button" aria-label="${label}" title="${label}" class="tl-iconbtn tl-btn--${variant} tl-iconbtn--${size} ${extra}" ${attrList(attrs)}>${icon(name, size === "sm" ? 16 : 20)}</button>`;
}

export function tag(tone, text, ic) {
  return html`<span class="tl-tag tl-tag--${tone}">${ic ? icon(ic, 16) : ""}${text}</span>`;
}

const AVATARS = ["moss", "acorn", "pond", "petal", "sun"];
export function avatar(name, size = "md", status) {
  let h = 0;
  for (const c of String(name)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const tone = AVATARS[h % AVATARS.length];
  return html`<span class="tl-avatar tl-avatar--${size} tl-avatar--${tone}" role="img" aria-label="${name}">${initials(name)}${status ? html`<span class="tl-avatar__status tl-presence--${status}" aria-hidden="true"></span>` : ""}</span>`;
}

export function presence(tone, text) {
  return html`<span class="tl-presence tl-presence--${tone}"><span class="tl-presence__dot" aria-hidden="true"></span><span>${text}</span></span>`;
}

export function alert({ tone = "info", title, body, actions, id, dismiss }) {
  const ic = { info: "info", success: "check", warning: "alert", danger: "alert" }[tone];
  const role = tone === "warning" || tone === "danger" ? "alert" : "status";
  return html`<div class="tl-alert tl-alert--${tone}" role="${role}" ${id ? raw(`data-alert="${esc(id)}"`) : ""}>
  <span class="tl-alert__icon" aria-hidden="true">${icon(ic)}</span>
  <div>
    <p class="tl-alert__title">${title}</p>
    ${body ? html`<p class="tl-alert__body">${body}</p>` : ""}
    ${actions ? html`<div class="tl-alert__actions">${actions}</div>` : ""}
  </div>
  <span>${dismiss ? iconButton({ label: "Dismiss", name: "close", size: "sm", attrs: { "data-dismiss": dismiss } }) : ""}</span>
</div>`;
}

// ---------------------------------------------------------------- fields

let uid = 0;
export const nextId = (p = "f") => `${p}-${++uid}`;

export function textField({ id = nextId(), label, hint, type = "text", value = "", placeholder = "", error, name, iconName, attrs = "", autocomplete }) {
  const hid = hint || error ? id + "-hint" : null;
  return html`<div class="tl-textfield${error ? " has-error" : ""}">
  <label for="${id}" class="tl-textfield__label">${label}</label>
  <div class="tl-textfield__control">
    ${iconName ? html`<svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${raw(ICONS[iconName])}</svg>` : ""}
    <input id="${id}" name="${name || id}" class="tl-textfield__input" type="${type}" value="${value}" placeholder="${placeholder}" ${autocomplete ? raw(`autocomplete="${esc(autocomplete)}"`) : ""} ${error ? raw('aria-invalid="true"') : ""} ${hid ? raw(`aria-describedby="${hid}"`) : ""} ${attrList(attrs)}/>
  </div>
  ${hid ? html`<p id="${hid}" class="tl-textfield__hint">${error ? icon("close", 16) : ""}${error || hint}</p>` : ""}
</div>`;
}

export function selectField({ id = nextId(), label, hint, options, value, name, iconName }) {
  const hid = hint ? id + "-hint" : null;
  return html`<div class="tl-textfield">
  <label for="${id}" class="tl-textfield__label">${label}</label>
  <div class="tl-textfield__control">
    <select id="${id}" name="${name || id}" class="tl-textfield__input tl-select" ${hid ? raw(`aria-describedby="${hid}"`) : ""}>
      ${options.map(([v, text]) => html`<option value="${v}" ${String(v) === String(value) ? raw("selected") : ""}>${text}</option>`)}
    </select>
    <svg class="tl-icon tl-textfield__chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${raw(ICONS["chevron-down"])}</svg>
  </div>
  ${hid ? html`<p id="${hid}" class="tl-textfield__hint">${hint}</p>` : ""}
</div>`;
}

export function timeField({ id, label, value }) {
  return html`<div class="tl-textfield tl-timefield">
  <label for="${id}" class="tl-textfield__label">${label}</label>
  <div class="tl-textfield__control">
    <svg class="tl-icon tl-textfield__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${raw(ICONS.clock)}</svg>
    <input id="${id}" name="${id}" class="tl-textfield__input" type="time" value="${value}"/>
  </div>
</div>`;
}

export function switchRow({ id, label, desc, on, name }) {
  const check = on ? icon("check", 12) : "";
  return html`<div class="tl-field-row">
  <button id="${id}" type="button" role="switch" aria-checked="${on ? "true" : "false"}" class="tl-switch${on ? " is-on" : ""}" ${name ? raw(`data-name="${esc(name)}"`) : ""}><span class="tl-switch__thumb">${check}</span></button>
  <label for="${id}" class="tl-field-row__text"><span class="tl-field-row__label">${label}</span>${desc ? html`<span class="tl-field-row__desc">${desc}</span>` : ""}</label>
</div>`;
}

export function checkRow({ id, label, desc, checked, name, value }) {
  return html`<div class="tl-field-row">
  <span class="tl-check"><input id="${id}" type="checkbox" class="tl-check__input" ${name ? raw(`name="${esc(name)}"`) : ""} ${value != null ? raw(`value="${esc(value)}"`) : ""} ${checked ? raw("checked") : ""}/><span class="tl-check__box" aria-hidden="true">${icon("check", 14)}</span></span>
  <label for="${id}" class="tl-field-row__text"><span class="tl-field-row__label">${label}</span>${desc ? html`<span class="tl-field-row__desc">${desc}</span>` : ""}</label>
</div>`;
}

export function radioGroup({ name, legend, options, value, cards }) {
  return html`<fieldset class="tl-radiogroup${cards ? " tl-radiogroup--cards" : ""}">
  <legend>${legend}</legend>
  ${options.map(([v, label, desc], i) => html`<div class="tl-field-row">
    <span class="tl-radio"><input id="${name}-${i}" type="radio" name="${name}" class="tl-radio__input" value="${v}" ${String(v) === String(value) ? raw("checked") : ""}/><span class="tl-radio__dot" aria-hidden="true"></span></span>
    <label for="${name}-${i}" class="tl-field-row__text"><span class="tl-field-row__label">${label}</span>${desc ? html`<span class="tl-field-row__desc">${desc}</span>` : ""}</label>
  </div>`)}
</fieldset>`;
}

export function segmented({ name, label, options, value }) {
  return html`<fieldset class="tl-segmented" aria-label="${label}">
  ${options.map(([v, text]) => html`<label class="tl-segmented__opt"><input type="radio" name="${name}" value="${v}" ${v === value ? raw("checked") : ""}/><span>${text}</span></label>`)}
</fieldset>`;
}

export function codeInput({ legend, hint, error, id = "code" }) {
  const box = (i, extra = "") => html`<input ${i === 1 ? raw(`id="${id}"`) : ""} class="tl-code__box" inputmode="numeric" pattern="[0-9]*" maxlength="1" autocomplete="${i === 1 ? "one-time-code" : "off"}" aria-label="Digit ${i} of 6"/>`;
  return html`<fieldset class="tl-code${error ? " has-error" : ""}" data-tl-code>
  <legend>${legend}</legend>
  <div class="tl-code__boxes">${box(1)}${box(2)}${box(3)}<span class="tl-code__gap" aria-hidden="true"></span>${box(4)}${box(5)}${box(6)}</div>
  ${hint || error ? html`<p class="tl-textfield__hint">${error ? icon("close", 16) : ""}${error || hint}</p>` : ""}
</fieldset>`;
}

export function codeValue(root) {
  return [...root.querySelectorAll(".tl-code__box")].map((b) => b.value).join("");
}

// ---------------------------------------------------------------- containers

export function card({ eyebrow, title, body, head, toned, children, list, label }) {
  const cls = `tl-card${toned ? " tl-card--" + toned : ""}${list ? " tl-card--list" : ""}`;
  return html`<section class="${cls}" ${label ? raw(`aria-label="${esc(label)}"`) : ""}>
  ${eyebrow || title ? html`<header class="tl-card__head"><div>${eyebrow ? html`<p class="tl-card__eyebrow">${eyebrow}</p>` : ""}${title ? html`<h3 class="tl-card__title">${title}</h3>` : ""}</div>${head || ""}</header>` : ""}
  ${body ? html`<p class="tl-card__body">${body}</p>` : ""}
  ${children || ""}
</section>`;
}

export function sheet({ id, title, body, actions, stackActions }) {
  return html`<div class="tl-sheet-scrim" id="${id}" hidden>
  <div class="tl-sheet" role="dialog" aria-modal="true" aria-labelledby="${id}-title">
    <span class="tl-sheet__grabber" aria-hidden="true"></span>
    <div class="tl-sheet__head"><h2 class="tl-sheet__title" id="${id}-title">${title}</h2>${iconButton({ label: "Close", name: "close", extra: "tl-sheet__close" })}</div>
    <div class="tl-stack tl-stack--group">${body}</div>
    ${actions ? html`<div class="tl-actions">${actions}</div>` : ""}
  </div>
</div>`;
}

export function emptyState({ art: name, title, body, action }) {
  return html`<section class="tl-card"><div class="tl-empty">
  <div class="tl-empty__art">${art(name)}</div>
  <h3 class="tl-empty__title">${title}</h3>
  <p class="tl-empty__body">${body}</p>
  ${action ? html`<div class="tl-empty__action">${action}</div>` : ""}
</div></section>`;
}

export function steps(names, current) {
  return html`<nav class="tl-stepsnav" aria-label="Setup progress">
  <p class="tl-steps__summary">Step ${current} of ${names.length}: ${names[current - 1]}</p>
  <ol class="tl-steps">${names.map((n, i) => html`<li class="tl-steps__item${i + 1 < current ? " is-done" : ""}" ${i + 1 === current ? raw('aria-current="step"') : ""}><span class="tl-steps__bar" aria-hidden="true"></span><span class="tl-steps__label">${n}</span></li>`)}</ol>
</nav>`;
}

export function loader(label = "Loading") {
  return html`<div class="tl-loader" role="status"><span class="tl-loader__label">${label}</span></div>`;
}

export function toast(message, tone = "neutral", opts = {}) {
  if (window.TreelineUI) window.TreelineUI.toast(message, { tone, ...opts });
}

/** The line every page ends with. */
/** Who made Treeline and how to help: the footer's links, and the softphone room's cards. */
export const CONTACT = "jdmiller2010@gmail.com";
export const SUPPORT_URL = "https://buymeacoffee.com/jdmiller";

export function footer(licenses = "/parent/licenses.html") {
  return html`<p class="caption tl-footer" style="color:var(--ink-muted)">© 2026 Jordan Miller · <a href="mailto:${CONTACT}" style="color:inherit">${CONTACT}</a> · <a href="${SUPPORT_URL}" style="color:inherit" target="_blank" rel="noopener">Support Treeline</a> · <a href="${licenses}" style="color:inherit">Open-source licenses</a></p>`;
}

/** The plain statement the design system requires wherever a phone or the app is used. */
export const NO_911 = "Treeline can't call 911 or any outside number. Kids need another way to reach help.";

export function setBusy(button, busy, label) {
  if (!button) return;
  button.disabled = busy;
  const l = button.querySelector(".tl-btn__label");
  if (l && label) { if (busy) { button.dataset.label = l.textContent; l.textContent = label; } else { l.textContent = button.dataset.label || l.textContent; } }
}
