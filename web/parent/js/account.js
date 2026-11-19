// Settings, privacy and safety, about, the action log, and the two "arrive by link" screens.
import { api, apiUrl, del, get, patch, post, token } from "/shared/api.js";
import { alert, button, card, emptyState, html, icon, raw, selectField, tag, textField, toast, NO_911 } from "/shared/ui.js";
import { time12, when } from "/shared/format.js";
import { formDialog } from "./dialogs.js";
import { privacyAccordion } from "./privacy-content.js";
import { disablePush, enablePush, pushState } from "./push.js";
import { hasParentCode, newCodeFields, parentCodeDialog, saveNewCode } from "./parentcode.js";
import { redeemDialog, strings } from "./strings.js";

const ZONES = [["America/New_York", "Eastern"], ["America/Chicago", "Central"], ["America/Denver", "Mountain"], ["America/Phoenix", "Arizona"],
  ["America/Los_Angeles", "Pacific"], ["America/Anchorage", "Alaska"], ["Pacific/Honolulu", "Hawaii"]];
const KEEP = [[7, "7 days"], [14, "14 days"], [30, "30 days"], [60, "60 days"], [90, "90 days"], [180, "6 months"], [365, "1 year"]];

const PUSH_TEXT = {
  unsupported: "This browser can't show notifications. Email still works.",
  unconfigured: "Notifications on this device aren't set up on this server. Email still works.",
  denied: "Notifications are blocked for this site. Allow them in your browser's settings to turn them on.",
  on: "On for this device.",
  off: "Off for this device.",
};

export async function account(ctx) {
  const th = ctx.me.treehouse, me = ctx.me, parent = ctx.isParent();
  const push = await pushState().catch(() => "unsupported");
  const zones = ZONES.map(([v, l]) => [v, `${l} (${v.split("/")[1].replace("_", " ")})`]);
  if (!ZONES.some(([v]) => v === th.timezone)) zones.unshift([th.timezone, th.timezone.replace("_", " ")]);
  const keep = KEEP.slice();
  if (!KEEP.some(([v]) => v === th.retention_days)) keep.push([th.retention_days, `${th.retention_days} days`]);

  const content = html`
  <section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">You</h2>
    <dl class="tl-dl">
      <div class="tl-dl__row"><dt>Email</dt><dd>${me.email}</dd></div>
      <div class="tl-dl__row"><dt>Role</dt><dd>${me.grown_up.role === "parent" ? "Parent" : "Sitter"}</dd></div>
      <div class="tl-dl__row"><dt>Treehouse</dt><dd>${th.name}, number <span class="tl-num">${th.number}</span></dd></div>
    </dl>
    <div class="tl-actions">${button({ label: "Sign out", attrs: "data-sign-out-btn" })}</div>
  </div></section>

  ${parent ? html`<form class="tl-card" id="house-form" novalidate><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Treehouse</h2>
    ${textField({ id: "set-name", label: "Name", value: th.name, hint: "Families you're strung with see this." })}
    ${selectField({ id: "set-tz", label: "Time zone", options: zones, value: th.timezone, hint: "Quiet hours and daily minutes follow it." })}
    ${selectField({ id: "set-keep", label: "Keep call records for", options: keep, value: th.retention_days, hint: "Older records are deleted. Treeline never keeps audio." })}
    <div class="tl-actions">${button({ label: "Save", variant: "primary", type: "submit" })}</div>
  </div></form>` : ""}

  ${parent ? html`<section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Parent code</h2>
    <p class="tl-card__body">${hasParentCode(ctx)
      ? "A parent code is set. It is what takes a device out of phone mode, so keep it to yourselves."
      : "Set a code before you add a softphone. It is what takes a device out of phone mode: on a softphone, only someone who knows it can get back to the parent dashboard."}</p>
    <div class="tl-actions">${button({ label: hasParentCode(ctx) ? "Change parent code" : "Set a parent code", variant: hasParentCode(ctx) ? "secondary" : "primary", attrs: "data-parent-code" })}</div>
  </div></section>` : ""}

  <section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Notifications</h2>
    <p class="tl-card__body">We email you when a string needs an answer, a phone goes offline, or someone dials numbers that aren't strung. ${PUSH_TEXT[push]}</p>
    ${push === "on" || push === "off" ? html`<div class="tl-actions">${push === "on" ? button({ label: "Turn off on this device", attrs: "data-push-off" }) : button({ label: "Turn on for this device", attrs: "data-push-on" })}</div>` : ""}
  </div></section>

  ${parent ? html`<section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Records</h2>
    <p class="tl-card__body">Every change a grown-up makes is written to the action log, so you can see who changed what.</p>
    <div class="tl-actions">${button({ label: "Action log", attrs: 'data-href="#/actions"' })}</div>
  </div></section>` : ""}

  ${parent ? html`<section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Leave Treeline</h2>
    <p class="tl-card__body">Leaving ends all your strings and tells those families. Deleting also erases your call records and everything else we hold. Neither can be undone.</p>
    <div class="tl-actions">
      ${button({ label: "Leave the Treeline", variant: "danger", attrs: "data-leave" })}
      ${button({ label: "Delete everything", variant: "danger", attrs: "data-delete" })}
    </div>
  </div></section>` : ""}`;

  return {
    title: "Settings", back: "#/home", nav: null, template: "settings", content,
    mount(root) {
      root.querySelector("[data-sign-out-btn]").addEventListener("click", () => root.querySelector("[data-sign-out]").click());
      root.querySelector("[data-parent-code]")?.addEventListener("click", async () => { if (await parentCodeDialog(ctx)) ctx.render(); });
      root.querySelector("[data-push-on]")?.addEventListener("click", async () => {
        try { await enablePush(); toast("Notifications are on for this device", "success"); ctx.render(); } catch (e) { toast(e.message, "warning"); }
      });
      root.querySelector("[data-push-off]")?.addEventListener("click", async () => {
        try { await disablePush(); toast("Notifications are off for this device", "neutral"); ctx.render(); } catch (e) { toast(e.message, "warning"); }
      });
      root.querySelector("#house-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          ctx.me.treehouse = await patch("/api/treehouse", { name: root.querySelector("#set-name").value, timezone: root.querySelector("#set-tz").value,
            retention_days: Number(root.querySelector("#set-keep").value) });
          toast("Saved", "success"); ctx.render();
        } catch (err) { toast(err.message, "warning"); }
      });
      const typed = (what, verb, run, body) => async () => {
        const ok = await formDialog({
          title: `${verb}?`, intro: body, submit: verb, danger: true,
          body: textField({ id: "confirm-name", name: "confirm", label: `Type "${th.name}" to confirm`, attrs: 'autocomplete="off"' }),
          onSubmit: (f) => run({ confirm: f.querySelector("[name=confirm]").value }),
        });
        if (ok) { token.clear(); ctx.me = null; toast(what, "neutral"); ctx.go("#/signin"); }
      };
      root.querySelector("[data-leave]")?.addEventListener("click", typed("You left the Treeline", "Leave the Treeline",
        (b) => post("/api/treehouse/leave", b), "Your strings end, those families are told, and your phones stop working."));
      root.querySelector("[data-delete]")?.addEventListener("click", typed("Everything was deleted", "Delete everything",
        (b) => del("/api/treehouse", b), "This erases your treehouse, phones, strings and call records for good."));
    },
  };
}

export async function privacy(ctx) {
  const content = html`
  ${alert({ tone: "info", title: "Treeline can't call 911", body: NO_911 })}
  <section class="tl-stack"><h2 class="title-lg">How Treeline treats your family's information</h2>
  <p class="tl-measure" style="color:var(--ink-muted)">Plain answers. If something here isn't clear, write to jdmiller2010@gmail.com.</p>
  <div class="tl-card">${privacyAccordion()}</div></section>`;
  return { title: "Privacy and safety", back: "#/home", nav: null, content };
}

export async function about(ctx) {
  const content = html`
  <section class="tl-card"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Treeline</h2>
    <p class="tl-tagline">Safe calls for neighborhood kids</p>
    <p class="tl-card__body">A house-to-house phone for kids who live near each other, with parents holding the keys.</p>
    <dl class="tl-dl">
      <div class="tl-dl__row"><dt>Made by</dt><dd>Jordan Miller</dd></div>
      <div class="tl-dl__row"><dt>Questions</dt><dd><a href="mailto:jdmiller2010@gmail.com">jdmiller2010@gmail.com</a></dd></div>
      <div class="tl-dl__row"><dt>Code license</dt><dd>PolyForm Noncommercial 1.0.0</dd></div>
      <div class="tl-dl__row"><dt>Design license</dt><dd>CC BY-NC 4.0, "Treeline by Jordan Miller"</dd></div>
    </dl>
    <div class="tl-actions">
      ${button({ label: "Open-source licenses", attrs: "data-licenses" })}
      <a class="tl-btn tl-btn--primary tl-btn--md" href="https://buymeacoffee.com/REPLACE-ME" target="_blank" rel="noopener"><span class="tl-btn__label">Support Treeline</span></a>
    </div>
  </div></section>
  ${alert({ tone: "info", title: "Treeline can't call 911", body: NO_911 })}`;
  return { title: "About Treeline", back: "#/home", nav: null, template: "settings", content, mount(root) { root.querySelector("[data-licenses]").addEventListener("click", () => { location.href = "/parent/licenses.html"; }); } };
}

const ACTIONS = {
  treehouse_created: () => "Created the treehouse",
  ladder_code_created: () => "Made a string code",
  changed_name: (a) => `Renamed the treehouse from ${a.before} to ${a.after}`,
  changed_timezone: (a) => `Changed the time zone to ${a.after}`,
  changed_paused: (a) => (a.after === "1" ? "Paused calls" : "Turned calls back on"),
  changed_max_call_minutes: (a) => `Changed the longest call from ${+a.before} to ${+a.after} minutes`,
  changed_daily_minutes: (a) => (a.after === "None" ? "Removed the daily minutes limit" : `Changed daily minutes to ${+a.after}`),
  changed_retention_days: (a) => `Changed how long call records are kept to ${a.after} days`,
  changed_quiet_start: (a) => `Changed quiet hours to start at ${time12(a.after)}`,
  changed_quiet_end: (a) => `Changed quiet hours to end at ${time12(a.after)}`,
  changed_quiet_days: () => "Changed which nights are quiet",
  changed_quiet_enabled: (a) => (a.after === "1" ? "Turned quiet hours on" : "Turned quiet hours off"),
  changed_parent_code: () => "Set or changed the parent code",
  handset_left: (a) => `${a.target} left phone mode`,
  changed_number: (a) => `Changed the number from ${a.before} to ${a.after}`,
  ladder_code_created: () => "Made a ladder code",
  string_requested: (a) => `Asked to string with ${a.target}`,
  string_approved: (a) => `Approved the string with ${a.target}`,
  string_paused: (a) => `Paused the string with ${a.target}`,
  string_resumed: (a) => `Turned the string with ${a.target} back on`,
  string_cut: (a) => `Ended the string with ${a.target}`,
  handset_added: (a) => `Added ${a.target}`,
  handset_renamed: (a) => `Renamed a phone to ${a.target}`,
  handset_removed: (a) => `Removed ${a.target}`,
  handset_disconnected: (a) => `Disconnected ${a.target}`,
  handset_reconnected: (a) => `Connected ${a.target} again`,
  grown_up_added: (a) => `Added ${a.target} as a ${a.after}`,
  grown_up_removed: (a) => `Removed ${a.target}`,
  calls_exported: () => "Exported the call log",
  left_treeline: () => "Left the Treeline",
};

export async function actionLog(ctx) {
  if (!ctx.isParent()) return { redirect: "#/home" };       // the action log is for parents
  const { actions } = await get("/api/actions");
  const tz = ctx.me.treehouse.timezone;
  const content = html`<h2 class="title-lg">Action log</h2>${actions.length ? html`<div class="tl-card tl-card--list">${actions.map((a) => html`<div class="tl-row">
    <div class="tl-row__main"><div class="tl-row__title">${(ACTIONS[a.action] || (() => a.action.replaceAll("_", " ")))(a)}</div>
    <div class="tl-row__meta"><span>${a.email || "Treeline"}</span><span>${when(a.at, tz)}</span></div></div></div>`)}</div>`
    : emptyState({ art: "sprig", title: "Nothing yet", body: "Changes you make, like approving a string or setting quiet hours, show up here." })}`;
  return { title: "Action log", back: "#/settings", nav: null, content };
}

/** Arrive from a QR code or link on a softphone: add it to this treehouse. */
export async function pairClaim(ctx, params) {
  const code = (params[0] || "").replace(/\D/g, "");
  const content = html`<form class="tl-card" id="pair-form" novalidate><div class="tl-stack tl-stack--group">
    <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">Add this softphone?</h2><p class="tl-card__body">The softphone is showing the code <strong class="tl-num">${code}</strong>. Check it matches, then add it to ${ctx.me.treehouse.name}.</p></div>
    ${textField({ id: "pair-name", name: "name", label: "Name for this softphone", placeholder: "Living room softphone", value: "" })}
    ${hasParentCode(ctx) ? "" : html`<div class="tl-stack tl-stack--group">${newCodeFields("pair")}</div>`}
    <div data-error></div>
    <div class="tl-actions">${button({ label: "Not now", attrs: 'data-href="#/home"' })}${button({ label: "Add softphone", variant: "primary", type: "submit" })}</div>
  </div></form>`;
  return {
    title: "Add a softphone", back: "#/home", nav: null, template: "settings", content,
    mount(root) {
      root.querySelector("#pair-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          if (!hasParentCode(ctx)) await saveNewCode(ctx, root.querySelector("#pair-form"));
          const r = await post("/api/pair/claim", { code, name: root.querySelector("#pair-name").value || "Softphone" });
          toast(`${r.handset.name} is connected`, "success"); ctx.go("#/home");
        } catch (err) { root.querySelector("[data-error]").innerHTML = String(alert({ tone: "danger", title: err.message })); }
      });
    },
  };
}

/** Arrive from a shared string-code link: show Strings with the code filled in. */
export async function stringLink(ctx, params) {
  const v = await strings(ctx, []);
  const mount = v.mount;
  v.mount = (root) => { mount(root); redeemDialog(ctx, params[0] || "").then(() => ctx.go("#/strings")); };
  return v;
}
