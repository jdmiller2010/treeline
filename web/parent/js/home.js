// Home: the Overview template. One toned card, today's summary, what needs a parent's answer.
import { get, patch } from "/shared/api.js";
import { alert, art, button, emptyState, html, icon, join, presence, raw, toast, NO_911, nextId } from "/shared/ui.js";
import { dateText, minutesText, plural, time12 } from "/shared/format.js";
import { bindTreehouse, treehouseSections } from "./house.js";
import { bindHomeSettings, homeSettings } from "./account.js";
import { pushState } from "./push.js";
import { approvalCard, bindStringActions, stringConnect } from "./strings.js";

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
      <p class="tl-card__body">${s.other.name} is on your Treeline now. Their number is ${s.other.number}.</p></section>`;
  }
  return "";
}

export async function home(ctx) {
  const [d, { grown_ups }, push] = await Promise.all([get("/api/home"), get("/api/grown-ups"), pushState().catch(() => "unsupported")]);
  ctx.me.treehouse = d.treehouse;
  ctx.badge = d.strings.waiting_on_me.length;
  const parent = ctx.isParent(), th = d.treehouse;
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
  // (No "add your first phone" card: the Phones section below says it when there are none. And no picture on these cards:
  // the treehouse at the top is this screen's one illustration.)
  if (d.handsets.length && !d.strings.live && !d.strings.waiting_on_me.length && !d.strings.waiting_on_them.length) setupCards.push(html`<section class="tl-card tl-card--seeds" aria-label="Invite a friend's family">
    <header class="tl-card__head"><div><p class="tl-card__eyebrow">First string</p><h3 class="tl-card__title">Invite a friend's family</h3></div></header>
    <p class="tl-card__body">Share a string code with a parent you know. Once you both say yes, the kids can call.</p>
    ${parent ? html`<div class="tl-actions">${button({ label: "New string connection", variant: "primary", icon: "string", attrs: "data-make-code" })}</div>` : ""}</section>`);

  const waiting = [...d.strings.waiting_on_me, ...d.strings.waiting_on_them];
  const content = html`
  <header class="tl-home-hero">
    ${art("treehouse")}
    <p class="tl-home-hero__name" id="home-name" aria-hidden="true">${th.name}</p>
    <p class="tl-home-hero__meta">Joined ${dateText(th.created_at, th.timezone)} · Number <span class="tl-num">${th.number}</span></p>
  </header>
  ${alerts.length ? html`<div class="tl-stack">${alerts}</div>` : ""}
  ${toned ? html`<div class="tl-grid tl-grid--2">${toned}${today}</div>` : today}
  <section class="tl-card" aria-label="This week"><div class="tl-stats">
    <div class="tl-stat"><span class="tl-stat__label">Calls</span><span class="tl-stat__value">${w.calls}</span><span class="tl-stat__note">This week</span></div>
    <div class="tl-stat"><span class="tl-stat__label">Talk time</span><span class="tl-stat__value">${w.minutes}<span class="tl-stat__unit">min</span></span><span class="tl-stat__note">This week</span></div>
    <div class="tl-stat"><span class="tl-stat__label">Strings</span><span class="tl-stat__value">${d.strings.live}</span><span class="tl-stat__note">${waiting.length ? `${waiting.length} waiting` : "All set"}</span></div>
  </div></section>
  ${waiting.length ? html`<section class="tl-stack"><h2 class="title-lg">Waiting on families</h2>${waiting.map((s) => approvalCard(s, parent))}</section>` : ""}
  ${setupCards}
  ${treehouseSections(ctx, d.handsets, grown_ups)}
  ${homeSettings(ctx, push)}
  ${alert({ tone: "info", title: "Treeline can't call 911", body: NO_911 })}`;

  return {
    title: "Home", lockup: true, nav: "home", content,
    mount(root) {
      bindStringActions(root, ctx);
      bindTreehouse(root, ctx, () => ctx.render());
      bindHomeSettings(root, ctx);
      // The name is shown big under the picture. Once that has scrolled up under the title bar, the bar's "Treeline" gives way to it.
      const bar = document.querySelector(".tl-appbar"), big = root.querySelector("#home-name");
      if (bar && big && "IntersectionObserver" in window) {
        new IntersectionObserver(([e]) => bar.classList.toggle("is-title", !e.isIntersecting), { rootMargin: "-64px 0px 0px 0px" }).observe(big);
      } else bar?.classList.add("is-title");
      root.querySelectorAll("[data-make-code]").forEach((b) => b.addEventListener("click", async () => { await stringConnect(ctx); ctx.render(); }));
    },
  };
}
