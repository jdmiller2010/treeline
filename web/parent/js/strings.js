// Strings: the approved connections between two treehouses.
import { get, post, del } from "/shared/api.js";
import { alert, avatar, button, card, emptyState, html, icon, join, presence, raw, tag, textField, toast, str, nextId } from "/shared/ui.js";
import { plural, when } from "/shared/format.js";
import { confirmDialog, formDialog, infoDialog } from "./dialogs.js";

/** Make a string code and show it, ready to copy and send. */
export async function showStringCode(ctx) {
  const made = await post("/api/ladder-codes");
  const link = `${location.origin}/parent/#/string/${made.code}`;
  const message = `Join me on Treeline so our kids can call each other. Open Treeline, go to Strings, and enter this string code: ${made.code}\n${link}`;
  // One row of buttons in the sheet's own footer: Copy message is the main action, Done sits beside it.
  await formDialog({
    title: "Your string code",
    body: html`<p class="tl-sheet__body">Send this to a parent in the other family. It works once and expires in 7 days.</p>
      <p class="numeral tl-num" style="text-align:center;font-size:42px;line-height:50px;letter-spacing:.06em" aria-label="String code ${made.code.split("").join(" ")}">${made.code}</p>`,
    submit: "Copy message", cancel: "Done", keepOpen: true,
    async onSubmit() {
      try { await navigator.clipboard.writeText(message); toast("Copied. Paste it into a text or email.", "success"); }
      catch { toast("Couldn't copy. Select the code and copy it by hand.", "warning"); }
      return true;
    },
  });
}

/** Enter a string code from another family. */
export async function redeemDialog(ctx, code = "") {
  const s = await formDialog({
    title: "Enter a string code", intro: "Another parent shared this with you. Their family approves next, and calls connect once both of you have said yes.",
    submit: "Send request",
    body: textField({ id: "string-code", name: "code", label: "String code", value: code, placeholder: "ABCD-2345", attrs: 'autocapitalize="characters" autocomplete="off" spellcheck="false" maxlength="9"' }),
    onSubmit: (f) => post("/api/strings/redeem", { code: f.querySelector("[name=code]").value }),
  });
  if (s) toast(`Request sent to ${s.other.name}`, "success");
  return s;
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

export async function strings(ctx, params) {
  const { strings: list } = await get("/api/strings");
  const parent = ctx.isParent();
  const waitingOnMe = list.filter((s) => s.state === "waiting" && !s.mine_approved);
  ctx.badge = waitingOnMe.length;
  const selected = params[0] ? list.find((s) => String(s.id) === params[0]) : null;

  const detail = selected ? html`
    <button class="tl-btn tl-btn--quiet tl-btn--sm tl-listdetail__back" type="button" data-back-list><span class="tl-btn__label">‹ All strings</span></button>
    ${selected.state === "waiting" ? approvalCard(selected, parent) : html`<div class="tl-card"${selected.state === "live" ? raw(' data-scene="bloom"') : ""}>
      <header class="tl-card__head"><div><p class="tl-card__eyebrow">String</p><h3 class="tl-card__title">${selected.other.name}</h3></div>${stateTag(selected)}</header>
      <dl class="tl-dl">
        <div class="tl-dl__row"><dt>Their number</dt><dd class="tl-num">${selected.other.number}</dd></div>
        <div class="tl-dl__row"><dt>Since</dt><dd>${when(selected.created_at, ctx.me.treehouse.timezone)}</dd></div>
        <div class="tl-dl__row"><dt>Calls</dt><dd>${selected.state === "live" ? "Connect when both lines are free and awake." : selected.paused_by_me ? "No calls connect until you turn it back on." : "Paused by their family."}</dd></div>
      </dl>
      ${parent ? html`<div class="tl-actions">
        ${button({ label: "End string", variant: "danger", icon: "close", attrs: { "data-string": "end", "data-id": selected.id, "data-name": selected.other.name } })}
        ${selected.state === "live" ? button({ label: "Pause string", attrs: { "data-string": "pause", "data-id": selected.id, "data-name": selected.other.name } })
          : selected.paused_by_me ? button({ label: "Turn back on", variant: "primary", attrs: { "data-string": "resume", "data-id": selected.id, "data-name": selected.other.name } }) : ""}
      </div>` : ""}
    </div>`}` : emptyState({ art: "connection", title: "Pick a string", body: "Choose a treehouse to see its number and pause or end the string." });

  const content = list.length ? html`
    ${waitingOnMe.length ? html`<section class="tl-stack"><h2 class="title-lg">Waiting on you</h2>${waitingOnMe.map((s) => approvalCard(s, parent))}</section>` : ""}
    <div class="tl-listdetail${selected ? " is-detail" : ""}">
      <section class="tl-listdetail__list tl-stack">
        <div class="tl-stack tl-stack--tight"><h2 class="title-lg">Your strings</h2>${parent ? html`<div class="tl-cluster">${button({ label: "Enter a string code", variant: "secondary", size: "sm", icon: "key", attrs: "data-redeem" })}${button({ label: "Make a string code", variant: "secondary", size: "sm", icon: "plus", attrs: "data-make-code" })}</div>` : ""}</div>
        <div class="tl-card tl-card--list">${list.map((s) => row(s, selected && selected.id === s.id))}</div>
      </section>
      <section class="tl-listdetail__detail tl-stack">${detail}</section>
    </div>`
    : emptyState({ art: "neighborhood", title: "No strings yet", body: "A string connects your treehouse to a friend's. Share a string code with their parent, or enter one they sent you.",
        action: parent ? html`<div class="tl-cluster tl-cluster--actions">${button({ label: "Enter a string code", attrs: "data-redeem" })}${button({ label: "Make a string code", variant: "primary", icon: "plus", attrs: "data-make-code" })}</div>` : null });

  return {
    title: "Strings", nav: "strings", content,
    mount(root) {
      bindStringActions(root, ctx);
      root.querySelectorAll("[data-make-code]").forEach((b) => b.addEventListener("click", async () => { await showStringCode(ctx); ctx.render(); }));
      root.querySelectorAll("[data-redeem]").forEach((b) => b.addEventListener("click", async () => { if (await redeemDialog(ctx)) ctx.render(); }));
      root.querySelector("[data-back-list]")?.addEventListener("click", () => ctx.go("#/strings"));
    },
  };
}
