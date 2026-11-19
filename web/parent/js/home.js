// Home: the Overview template. One toned card, today's summary, what needs a parent's answer.
import { get, patch } from "/shared/api.js";
import { alert, art, button, emptyState, html, icon, join, presence, raw, toast, NO_911, nextId } from "/shared/ui.js";
import { minutesText, plural, time12 } from "/shared/format.js";
import { addHandsetDialog, bindPhoneSwitches, deviceButton, thisDevice, useThisDevice } from "./house.js";
import { KIND } from "./house.js";
import { approvalCard, bindStringActions, showLadderCode } from "./strings.js";

const NOTICE_TONE = { string_request: "info", string_live: "success", string_ended: "info", number_changed: "info",
  handset_offline: "warning", not_strung_attempt: "warning", unstrung_dials: "warning", no_911: "danger" };

function tonedCard(d, tz) {
  const th = d.treehouse;
  if (th.paused) {
    return html`<section class="tl-card tl-card--plank"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Paused</p><h3 class="tl-card__title">Calls are paused</h3></div></header>
      <p class="tl-card__body">No calls in or out until you turn this off.</p></section>`;
  }
  if (th.quiet_now) {
    return html`<section class="tl-card tl-card--night"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Tonight</p><h3 class="tl-card__title">Your phones are sleeping</h3></div></header>
      <p class="tl-card__body">Calls wait until ${time12(th.quiet.end)}.</p></section>`;
  }
  const s = d.strings.newest_live;
  if (s && Date.now() - new Date(s.updated_at).getTime() < 7 * 86400000) {
    return html`<section class="tl-card tl-card--breeze"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Good news</p><h3 class="tl-card__title">Newly strung</h3></div></header>
      <p class="tl-card__body">${s.other.name} is in the treehouse. Their number is ${s.other.number}.</p></section>`;
  }
  return "";
}

export async function home(ctx) {
  const d = await get("/api/home");
  ctx.me.treehouse = d.treehouse;
  ctx.badge = d.strings.waiting_on_me.length;
  const parent = ctx.isParent(), th = d.treehouse;
  const thisId = (d.handsets.find((h) => h.id === thisDevice()?.handset_id) || {}).id;
  const toned = tonedCard(d);
  const t = d.today, w = d.week;
  const today = html`<section class="tl-card"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Today</p>
    <h3 class="tl-card__title">${t.calls ? `${plural(t.calls, "call")}, ${t.minutes} min` : "No calls yet"}</h3></div></header>
    <p class="tl-card__body">${t.calls ? "Time on the phone with friends today." : "Calls show up here as they happen."}</p></section>`;

  // A 911 attempt is the one thing a parent must not miss, so it goes above everything else, with a way to the log.
  const noticeActions = (n) => n.kind === "string_request" ? button({ label: "Review", size: "sm", attrs: 'data-href="#/strings"' })
    : n.kind === "no_911" ? button({ label: "See the call log", size: "sm", attrs: 'data-href="#/calls"' }) : null;
  const alerts = [...d.notices].sort((x, y) => (y.kind === "no_911") - (x.kind === "no_911")).map((n) => alert({
    tone: NOTICE_TONE[n.kind] || "info", title: n.title, body: n.body, dismiss: String(n.id), actions: noticeActions(n) }));

  const setupCards = [];
  if (!d.handsets.length) setupCards.push(emptyState({ art: "treehouse", title: "Add your first phone",
    body: "Connect a softphone, a phone adapter or the Treeline phone. Friends can't call until something is plugged in.",
    action: parent ? button({ label: "Add a phone", variant: "primary", icon: "plus", attrs: "data-add-phone" }) : null }));
  else if (!d.strings.live && !d.strings.waiting_on_me.length && !d.strings.waiting_on_them.length) setupCards.push(emptyState({
    art: "neighborhood", title: "Invite a friend's family", body: "Share a ladder code with a parent you know. Once you both say yes, the kids can call.",
    action: parent ? button({ label: "Make a ladder code", variant: "primary", icon: "plus", attrs: "data-make-code" }) : null }));

  const waiting = [...d.strings.waiting_on_me, ...d.strings.waiting_on_them];
  const content = html`
  ${alerts.length ? html`<div class="tl-stack">${alerts}</div>` : ""}
  ${toned ? html`<div class="tl-grid tl-grid--2">${toned}${today}</div>` : today}
  <section class="tl-card" aria-label="This week"><div class="tl-stats">
    <div class="tl-stat"><span class="tl-stat__label">Calls</span><span class="tl-stat__value">${w.calls}</span><span class="tl-stat__note">This week</span></div>
    <div class="tl-stat"><span class="tl-stat__label">Talk time</span><span class="tl-stat__value">${w.minutes}<span class="tl-stat__unit">min</span></span><span class="tl-stat__note">This week</span></div>
    <div class="tl-stat"><span class="tl-stat__label">Strings</span><span class="tl-stat__value">${d.strings.live}</span><span class="tl-stat__note">${waiting.length ? `${waiting.length} waiting` : "All set"}</span></div>
  </div></section>
  ${d.handsets.length ? html`<section class="tl-stack">
    <div class="tl-split"><h2 class="title-lg">Phones</h2>${button({ label: "Manage", variant: "quiet", size: "sm", attrs: 'data-href="#/house"' })}</div>
    <div class="tl-card tl-card--list">${d.handsets.map((h) => html`<div class="tl-row tl-log tl-log--${h.disabled ? "bark" : h.online ? "canopy" : "bark"}">
      <span class="tl-log__icon" aria-hidden="true">${icon(h.disabled ? "phone-off" : "phone")}</span>
      <div class="tl-row__main"><div class="tl-row__title">${h.name}${h.id === thisId ? " (this device)" : ""}</div><div class="tl-row__meta"><span>${KIND[h.kind][0]}</span><span>${h.disabled ? "Disconnected" : h.online ? "Online" : "Offline"}</span></div></div>
      ${h.disabled ? presence("bark", "Disconnected") : presence(h.online ? "canopy" : "bark", h.online ? "Online" : "Offline")}
      <button type="button" role="switch" aria-checked="${h.disabled ? "false" : "true"}" aria-label="${h.name} connected" class="tl-switch${h.disabled ? "" : " is-on"}" data-handset-switch data-id="${h.id}" data-name="${h.name}"><span class="tl-switch__thumb">${h.disabled ? "" : icon("check", 12)}</span></button>
    </div>`)}</div>
    ${parent ? deviceButton(thisId) : ""}
  </section>` : ""}
  ${waiting.length ? html`<section class="tl-stack"><h2 class="title-lg">Waiting on families</h2>${waiting.map((s) => approvalCard(s, parent))}</section>` : ""}
  ${setupCards}
  ${alert({ tone: "info", title: "Treeline can't call 911", body: NO_911 })}`;

  const pauseLabel = th.paused ? "Turn calls back on" : "Pause calls";
  const actions = button({ label: pauseLabel, variant: "secondary", collapse: true, icon: th.paused ? "phone" : "pause", attrs: "data-pause" });
  return {
    title: "Home", nav: "home", content, actions,
    mount(root) {
      bindStringActions(root, ctx);
      root.querySelector("[data-pause]").addEventListener("click", async () => {
        try {
          const r = await patch("/api/treehouse", { paused: !th.paused });
          ctx.me.treehouse = r;
          toast(r.paused ? "Calls are paused" : "Calls are back on", r.paused ? "neutral" : "success");
          ctx.render();
        } catch (e) { toast(e.message, "warning"); }
      });
      bindPhoneSwitches(root, () => ctx.render());
      root.querySelectorAll("[data-this-device]").forEach((b) => b.addEventListener("click", async () => { if (await useThisDevice(ctx)) ctx.render(); }));
      root.querySelectorAll("[data-add-phone]").forEach((b) => b.addEventListener("click", async () => { if (await addHandsetDialog(ctx)) ctx.render(); }));
      root.querySelectorAll("[data-make-code]").forEach((b) => b.addEventListener("click", async () => { await showLadderCode(ctx); ctx.render(); }));
    },
  };
}
