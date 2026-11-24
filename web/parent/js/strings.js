// Strings: the approved connections between two treehouses, drawn as a grove map (list view too).
import { get, post, del } from "/shared/api.js";
import { alert, avatar, button, card, emptyState, html, icon, join, presence, raw, segmented, tag, textField, toast, str, nextId } from "/shared/ui.js";
import { plural, when } from "/shared/format.js";
import { confirmDialog, formDialog, infoDialog } from "./dialogs.js";

const shortCode = (c) => { const k = String(c).replace(/-/g, "").toUpperCase(); return k.length === 8 ? `${k.slice(0, 4)}-${k.slice(4)}` : k; };
const linkFor = (code) => `${location.origin}/parent/#/string/${code}`;
const DAY = 86400000;
/** Strings that just arrived: the next render draws them in (the line grows, the house unfurls). */
let freshIds = [];

/** Ask a family to string with us, from a code someone typed or a QR code someone scanned. Resolves with the new string. */
export async function redeemCode(code) {
  const s = await post("/api/strings/redeem", { code });
  freshIds = [s.id];
  toast(`Request sent to ${s.other.name}`, "success");
  return s;
}

/** The newest code that still has days left, or a fresh one. */
async function ownCode() {
  const { codes } = await get("/api/ladder-codes");
  const keep = codes.find((c) => new Date(c.expires_at).getTime() - Date.now() > 2 * DAY);
  if (keep) return { code: shortCode(keep.code), expires_at: keep.expires_at };
  return post("/api/ladder-codes");
}

/**
 * One sheet for every way to connect: your QR code and code (either family can scan or type), and a box for theirs.
 * Resolves with the string that was made, or null. It also closes itself, with the new string, when the other family
 * redeems the code shown here while the sheet is open.
 */
export function stringConnect(ctx, code = "") {
  const inviteText = (c) => `Join me on Treeline so our kids can call each other. Open Treeline, go to Strings, and enter this string code: ${c}\n${linkFor(c)}`;
  let current = null;
  return formDialog({
    title: "New string connection",
    intro: "Show this to a parent in the other family. They scan it with their phone's camera, or type your code into Treeline.",
    autofocus: false, submit: "Connect", cancel: "Done",
    body: html`<div class="tl-connect tl-stack tl-stack--group">
      <div data-qr class="tl-connect__qr" aria-live="polite"><div class="tl-qr tl-qr--wait" aria-hidden="true"></div></div>
      <div class="tl-codeshow" data-codeshow>
        <span class="tl-codeshow__code" data-code aria-label="Your string code">· · · · · · · ·</span>
        ${button({ label: "Copy invite", size: "sm", attrs: { type: "button", "data-copy": true } })}
        ${button({ label: "New code", size: "sm", variant: "quiet", attrs: { type: "button", "data-renew": true } })}
        <p class="tl-codeshow__note" data-note>Works once, and expires in 7 days.</p>
      </div>
      <div class="tl-connect__or" role="separator"><span class="tl-fade-line"></span><span>or enter theirs</span><span class="tl-fade-line"></span></div>
      ${textField({ id: "string-code", name: "code", label: "Their string code", value: code, placeholder: "ABCD-2345", hint: "If you scan their QR code with your camera, it connects on its own.",
        attrs: 'autocapitalize="characters" autocomplete="off" spellcheck="false" maxlength="9"' })}
    </div>`,
    onSubmit: async (f) => {
      const v = f.querySelector("[name=code]").value.trim();
      if (!v) throw new Error("Type their string code first.");
      return redeemCode(v);
    },
    async onOpen(scrim, close) {
      const q = (sel) => scrim.querySelector(sel);
      let known = null;
      const show = (c) => {
        current = c; const k = c.code;
        q("[data-qr]").innerHTML = `<div class="tl-qr">${window.TLQR.svg(linkFor(k), { label: `QR code for the string code ${k}` })}</div>`;
        q("[data-code]").textContent = k;
        q("[data-code]").setAttribute("aria-label", `Your string code ${k.split("").join(" ")}`);
        const days = Math.max(1, Math.round((new Date(c.expires_at).getTime() - Date.now()) / DAY));
        q("[data-note]").textContent = `Works once, and expires in ${plural(days, "day")}.`;
      };
      const fail = (e) => { q("[data-qr]").innerHTML = ""; q("[data-note]").textContent = e.message || "Couldn't make a code."; };
      try { known = new Set((await get("/api/strings")).strings.map((x) => x.id)); show(await ownCode()); } catch (e) { fail(e); }
      q("[data-copy]").addEventListener("click", async () => {
        if (!current) return;
        try { await navigator.clipboard.writeText(inviteText(current.code)); toast("Copied. Paste it into a text or email.", "success"); }
        catch { toast("Couldn't copy. Select the code and copy it by hand.", "warning"); }
      });
      q("[data-renew]").addEventListener("click", async (e) => {
        e.currentTarget.disabled = true;
        try { const old = current; if (old) await del(`/api/ladder-codes/${old.code}`).catch(() => {}); show(await post("/api/ladder-codes")); }
        catch (err) { toast(err.message, "warning"); }
        finally { e.currentTarget.disabled = false; }
      });
      // The other family redeemed our code: the new string shows up here, so close and let the map draw it in.
      const timer = setInterval(async () => {
        if (!scrim.isConnected || scrim.hidden) { clearInterval(timer); return; }
        try {
          const { strings: now } = await get("/api/strings");
          const arrived = known && now.find((x) => !known.has(x.id));
          if (arrived) { clearInterval(timer); freshIds = [arrived.id]; toast(`${arrived.other.name} used your code`, "success"); close(arrived); }
        } catch { /* try again next time */ }
      }, 4000);
    },
  });
}

function stateTag(s) {
  if (s.state === "live") return tag("canopy", "Strung", "leaf");
  if (s.state === "paused") return tag("bark", s.paused_by_me ? "Paused by you" : "Paused by them", "pause");
  return tag("neutral", s.mine_approved ? "Waiting on them" : "Needs your answer", "clock");
}

function row(s, selected) {
  return html`<div class="tl-row" role="link" tabindex="0" data-href="#/strings/${s.id}" data-tl-detail ${selected ? raw('aria-current="true"') : ""}>
  ${avatar(s.other.name, "md")}
  <div class="tl-row__main"><div class="tl-row__title">${s.other.name}</div><div class="tl-row__meta"><span class="tl-num">${s.other.number}</span></div></div>
  ${stateTag(s)}
</div>`;
}

export function approvalCard(s, parent) {
  const theirs = s.other.name;
  return html`<section class="tl-card tl-approval">
  <div class="tl-approval__people">${avatar("Your house", "md")}<span class="tl-approval__link" aria-hidden="true">${icon("plus", 16)}</span>${avatar(theirs, "md")}</div>
  <h3 class="tl-card__title">${theirs}</h3>
  <div class="tl-approval__sides">
    <div class="tl-approval__side ${s.mine_approved ? "is-yes" : "is-waiting"}"><span class="tl-approval__mark" aria-hidden="true">${icon(s.mine_approved ? "check" : "clock", 16)}</span><span><span class="tl-approval__who">Your house</span><span class="tl-approval__state">${s.mine_approved ? "Approved" : "Waiting"}</span></span></div>
    <div class="tl-approval__side ${s.theirs_approved ? "is-yes" : "is-waiting"}"><span class="tl-approval__mark" aria-hidden="true">${icon(s.theirs_approved ? "check" : "clock", 16)}</span><span><span class="tl-approval__who">${theirs}</span><span class="tl-approval__state">${s.theirs_approved ? "Approved" : "Waiting"}</span></span></div>
  </div>
  <p class="tl-approval__note">${s.mine_approved ? `Calls connect once ${theirs} approves too.` : `${theirs} would like to string with you. Calls connect once you approve.`}</p>
  ${parent ? html`<div class="tl-approval__actions">
    ${s.mine_approved
      ? button({ label: "Withdraw", variant: "quiet", size: "sm", icon: "close", attrs: { "data-string": "cut", "data-id": s.id, "data-name": theirs, "data-withdraw": true } })
      : html`${button({ label: "Not now", variant: "quiet", size: "sm", attrs: { "data-string": "decline", "data-id": s.id, "data-name": theirs } })}${button({ label: "Approve", variant: "primary", size: "sm", icon: "check", attrs: { "data-string": "approve", "data-id": s.id, "data-name": theirs } })}`}
  </div>` : ""}
</section>`;
}

/** Wire up Approve / Not now / Withdraw buttons anywhere they appear. */
export function bindStringActions(root, ctx) {
  root.querySelectorAll("[data-string]").forEach((b) => b.addEventListener("click", async () => {
    const { string: action, id, name } = b.dataset;
    try {
      if (action === "approve") { await post(`/api/strings/${id}/approve`); toast(`${name} is on your Treeline`, "success"); }
      else if (action === "decline") { await post(`/api/strings/${id}/cut`); toast("Request declined", "neutral"); }
      else if (action === "cut") { await post(`/api/strings/${id}/cut`); toast("Request withdrawn", "neutral"); }
      else if (action === "pause") { await post(`/api/strings/${id}/pause`); toast(`String with ${name} paused`, "neutral"); }
      else if (action === "resume") { await post(`/api/strings/${id}/resume`); toast(`String with ${name} is back on`, "success"); }
      else if (action === "end") {
        const ok = await confirmDialog({ title: `End the string with ${name}?`, body: "Calls between your treehouses stop right away. To connect again you'd both approve a new string.",
          confirm: "End string", danger: true, onConfirm: () => post(`/api/strings/${id}/cut`) });
        if (!ok) return;
        toast(`String with ${name} ended`, "neutral");
        ctx.go("#/strings"); return;
      }
      ctx.render();
    } catch (e) { toast(e.message, "warning"); }
  }));
}

const MAP_MAX = 12;   // what window.TLGrove draws; past it the page is a list
const MODE_KEY = "treeline.stringsView";
const viewMode = () => { try { return localStorage.getItem(MODE_KEY) === "list" ? "list" : "map"; } catch { return "map"; } };
const nodeState = (s) => s.state === "live" ? "live" : s.state === "paused" ? "paused" : s.mine_approved ? "wait" : "ask";

function detailCard(ctx, s, parent) {
  if (s.state === "waiting") return approvalCard(s, parent);
  return html`<div class="tl-card">
    <header class="tl-card__head"><div><p class="tl-card__eyebrow">String</p><h3 class="tl-card__title">${s.other.name}</h3></div>${stateTag(s)}</header>
    <dl class="tl-dl">
      <div class="tl-dl__row"><dt>Their number</dt><dd class="tl-num">${s.other.number}</dd></div>
      <div class="tl-dl__row"><dt>Since</dt><dd>${when(s.created_at, ctx.me.treehouse.timezone)}</dd></div>
      <div class="tl-dl__row"><dt>Calls</dt><dd>${s.state === "live" ? "Connect when both lines are free and awake." : s.paused_by_me ? "No calls connect until you turn it back on." : "Paused by them. Calls connect again when they turn it back on."}</dd></div>
    </dl>
    ${parent ? html`<div class="tl-actions">
      ${button({ label: "End string", variant: "danger", icon: "close", attrs: { "data-string": "end", "data-id": s.id, "data-name": s.other.name } })}
      ${s.state === "live" ? button({ label: "Pause string", attrs: { "data-string": "pause", "data-id": s.id, "data-name": s.other.name } })
        : s.paused_by_me ? button({ label: "Turn back on", variant: "primary", attrs: { "data-string": "resume", "data-id": s.id, "data-name": s.other.name } }) : ""}
    </div>` : ""}
  </div>`;
}

export async function strings(ctx, params) {
  const { strings: list } = await get("/api/strings");
  const parent = ctx.isParent();
  const crowded = list.length > MAP_MAX;
  const waitingOnMe = list.filter((s) => s.state === "waiting" && !s.mine_approved);
  ctx.badge = waitingOnMe.length;
  const fresh = freshIds; freshIds = [];
  const selected = params[0] ? list.find((s) => String(s.id) === params[0]) : null;
  const mode = crowded ? "list" : fresh.length ? "map" : viewMode();
  const th = ctx.me.treehouse;

  const newButton = parent ? button({ label: "New string connection", variant: waitingOnMe.length ? "secondary" : "primary", icon: "string", attrs: "data-connect" }) : "";
  const toggle = list.length && !crowded ? segmented({ name: "strings-view", label: "Show strings as", value: mode, options: [["map", "Map"], ["list", "List"]] }) : "";

  const map = raw(window.TLGrove.html({
    me: { name: th.name, number: th.number },
    friends: list.map((s) => ({ id: s.id, name: s.other.name, number: s.other.number, state: nodeState(s), href: `#/strings/${s.id}` })),
    selectedId: selected && selected.id, newIds: fresh, 
  }));
  const detail = selected ? detailCard(ctx, selected, parent)
    : list.length ? html`<p class="tl-grove__caption tl-measure" data-pick>Tap a treehouse to see its number and pause or end the string.</p>` : "";

  const body = !list.length
    ? html`<section class="tl-stack">${map}<p class="tl-grove__caption tl-measure">${parent
        ? "A string connects your treehouse to a friend's. Make a connection to show your code, or type one they sent you."
        : "A string connects your treehouse to a friend's. A parent can make the first one."}</p></section>`
    : mode === "map"
      ? html`<div class="tl-strings-map"><section class="tl-stack">${map}</section><section class="tl-stack" data-detail>${detail}</section></div>`
      : html`<div class="tl-listdetail${selected ? " is-detail" : ""}">
          <section class="tl-listdetail__list tl-stack"><div class="tl-card tl-card--list">${list.map((s) => row(s, selected && selected.id === s.id))}</div></section>
          <section class="tl-listdetail__detail tl-stack">${selected ? html`<button class="tl-btn tl-btn--quiet tl-btn--sm tl-listdetail__back" type="button" data-back-list><span class="tl-btn__label">‹ All strings</span></button>${detail}` : emptyState({ art: "connection", title: "Pick a string", body: "Choose a treehouse to see its number and pause or end the string." })}</section>
        </div>`;

  const content = html`
    ${waitingOnMe.length && !selected ? html`<section class="tl-stack"><h2 class="title-lg">Waiting on you</h2>${waitingOnMe.map((s) => approvalCard(s, parent))}</section>` : ""}
    <section class="tl-stack">
      <div class="tl-strings-head"><h2 class="title-lg">Your grove</h2>${newButton}</div>
      ${crowded ? html`<p class="tl-grove__caption" data-crowded>The map draws up to ${MAP_MAX} families. With ${list.length}, here they all are as a list.</p>` : ""}
      ${toggle}
      ${body}
    </section>`;

  return {
    title: "Strings", nav: "strings", content,
    mount(root) {
      bindStringActions(root, ctx);
      root.querySelectorAll("[data-connect]").forEach((b) => b.addEventListener("click", async () => { const made = await stringConnect(ctx); if (made && made.id) ctx.go(`#/strings/${made.id}`); }));
      root.querySelectorAll("input[name=strings-view]").forEach((r) => r.addEventListener("change", (e) => { try { localStorage.setItem(MODE_KEY, e.target.value); } catch { /* ignore */ } ctx.go("#/strings"); }));
      root.querySelector("[data-back-list]")?.addEventListener("click", () => ctx.go("#/strings"));
      if (selected) root.querySelector("[data-detail]")?.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    },
  };
}
