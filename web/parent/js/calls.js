// Calls: the full audit of every attempt, allowed or not. Never any audio.
import { api, apiUrl, get, token } from "/shared/api.js";
import { alert, button, emptyState, html, icon, raw, segmented, tag, toast } from "/shared/ui.js";
import { plural, when } from "/shared/format.js";

let range = "week";

function title(c) {
  const other = c.other ? (c.other.name || c.other.number) : "Unknown";
  return `${c.direction === "out" ? "To" : "From"} ${other}`;
}

function logRow(c, ctx, selected) {
  const tz = ctx.me.treehouse.timezone;
  const connected = c.result === "connected";
  return html`<div class="tl-row tl-log tl-log--${c.tone}${c.urgent ? " tl-log--urgent" : ""}" role="link" tabindex="0" data-href="#/calls/${c.id}" data-tl-detail ${selected ? raw('aria-current="true"') : ""}>
  <span class="tl-log__icon" aria-hidden="true">${icon(c.icon)}</span>
  <div class="tl-row__main"><div class="tl-row__title">${title(c)}</div>
    <div class="tl-row__meta"><span>${when(c.started_at, tz)}</span>${connected ? "" : html`<span>${c.detail}</span>`}</div></div>
  ${connected ? html`<span class="tl-log__dur tl-num">${c.detail}</span>` : tag(c.tone, c.label, c.icon)}
</div>`;
}

const EVENT = {
  dialed: (e) => `Dialed${e.handset ? " from " + e.handset : ""}`,
  rang: (e) => e.theirs ? "Rang their phone" : `Rang ${e.handset || "a phone"}`,
  answered: (e) => e.theirs ? "They answered" : `Answered on ${e.handset || "a phone"}`,
  joined: (e) => e.theirs ? "Another phone on their line joined" : `${e.handset || "A phone"} joined the call`,
  left: (e) => e.theirs ? "A phone on their line hung up" : `${e.handset || "A phone"} hung up`,
  declined: (e) => e.theirs ? "A phone on their line didn't answer" : `${e.handset || "A phone"} didn't answer`,
  pips: () => "One-minute warning beeps",
  ended: () => "Call ended",
};

async function detailCard(c, ctx) {
  const d = await get(`/api/calls/${c.id}`);
  const tz = ctx.me.treehouse.timezone;
  return html`<div class="tl-card">
  <header class="tl-card__head"><div><p class="tl-card__eyebrow">${when(d.started_at, tz)}</p><h3 class="tl-card__title">${d.label}</h3></div>${tag(d.tone, d.label, d.icon)}</header>
  <dl class="tl-dl">
    <div class="tl-dl__row"><dt>${d.direction === "out" ? "Called" : "Called by"}</dt><dd>${d.other ? (d.other.name || "Not a treehouse you're strung with") : "Unknown"}</dd></div>
    <div class="tl-dl__row"><dt>Number</dt><dd class="tl-num">${d.other?.number || ""}</dd></div>
    ${d.result === "connected" ? "" : html`<div class="tl-dl__row"><dt>What happened</dt><dd>${d.detail}</dd></div>`}
    ${d.talk_sec ? html`<div class="tl-dl__row"><dt>Talk time</dt><dd class="tl-num">${Math.floor(d.talk_sec / 60)}:${String(d.talk_sec % 60).padStart(2, "0")}</dd></div>` : ""}
    ${d.hung_up_first ? html`<div class="tl-dl__row"><dt>Hung up first</dt><dd>${d.hung_up_first === "you" ? "Your side" : "Their side"}</dd></div>` : ""}
  </dl>
  ${d.events.length ? html`<h4 class="title-sm">Timeline</h4><dl class="tl-dl">${d.events.map((e) => html`<div class="tl-dl__row"><dt class="tl-num">${new Intl.DateTimeFormat("en-US", { timeZone: tz, hour: "numeric", minute: "2-digit", second: "2-digit" }).format(new Date(e.at)).replace(/\s?([AP])M/, (_, a) => " " + a.toLowerCase() + "m")}</dt><dd>${(EVENT[e.event] || (() => e.event))(e)}</dd></div>`)}</dl>` : ""}
  <p class="tl-card__body" style="color:var(--ink-muted)">Treeline never records what's said on a call.</p>
</div>`;
}

async function downloadCsv() {
  const res = await fetch(apiUrl("/api/calls.csv"), { headers: { Authorization: "Bearer " + token.get() } });
  if (!res.ok) throw new Error("Couldn't export your calls. Try again.");
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: "treeline-calls.csv" });
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function calls(ctx, params) {
  const sitter = !ctx.isParent();
  if (sitter) range = "today";                                  // a sitter sees only today's calls
  const { calls: list } = await get(`/api/calls?range=${range}`);
  const selected = params[0] ? list.find((c) => String(c.id) === params[0]) : null;
  const detail = selected ? html`<button class="tl-btn tl-btn--quiet tl-btn--sm tl-listdetail__back" type="button" data-back-list><span class="tl-btn__label">‹ All calls</span></button>${await detailCard(selected, ctx)}`
    : emptyState({ art: "connection", title: "Pick a call", body: "Choose a call to see how it went, minute by minute." });

  const tries911 = list.filter((c) => c.urgent);
  const content = html`
  ${tries911.length ? alert({ tone: "danger", title: tries911.length === 1 ? "Someone tried to call 911" : `Someone tried to call 911 ${tries911.length} times`,
    body: "Treeline can't call 911, so those calls went nowhere. If anyone needs emergency help, call 911 from another phone. They're marked in red below." }) : ""}
  <div class="tl-split"><h2 class="title-lg">Call log</h2>${ctx.isParent() ? button({ label: "Export CSV", variant: "secondary", size: "sm", attrs: "data-export" }) : ""}</div>
  ${sitter ? html`<p class="tl-card__body" style="color:var(--ink-muted)">You're seeing today's calls. A parent can see the rest.</p>`
    : segmented({ name: "calls-range", label: "Show calls from", value: range, options: [["today", "Today"], ["week", "This week"], ["all", "All"]] })}
  ${list.length ? html`<div class="tl-listdetail${selected ? " is-detail" : ""}">
    <section class="tl-listdetail__list tl-stack"><div class="tl-card tl-card--list">${list.map((c) => logRow(c, ctx, selected && selected.id === c.id))}</div></section>
    <section class="tl-listdetail__detail tl-stack">${detail}</section></div>`
    : emptyState({ art: "quiet", title: range === "today" ? "No calls today" : "No calls yet", body: "Every call attempt shows up here, connected or not, so you always know what happened." })}`;

  return {
    title: "Calls", nav: "calls", content,
    mount(root) {
      root.querySelectorAll("input[name=calls-range]").forEach((r) => r.addEventListener("change", (e) => { range = e.target.value; ctx.go("#/calls"); }));
      root.querySelector("[data-back-list]")?.addEventListener("click", () => ctx.go("#/calls"));
      root.querySelector("[data-export]")?.addEventListener("click", async () => {
        try { await downloadCsv(); toast("Your calls were saved as a CSV file", "success"); } catch (e) { toast(e.message, "warning"); }
      });
    },
  };
}
