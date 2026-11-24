// Managing the treehouse (number, phones, grown-ups: drawn on Home) and the printable phone book.
import { get, post, patch, del } from "/shared/api.js";
import { avatar, button, card, codeInput, codeValue, emptyState, html, icon, iconButton, join, presence, radioGroup, raw, tag,
  textField, toast, nextId, NO_911 } from "/shared/ui.js";
import { plural, relative } from "/shared/format.js";
import { confirmDialog, formDialog, infoDialog } from "./dialogs.js";
import { hasParentCode, newCodeFields, saveNewCode } from "./parentcode.js";

export const KIND = {
  softphone: ["Softphone (app)", "The Treeline rotary phone as an app or in a browser, on a tablet, phone or computer."],
  ata: ["Phone adapter", "A Grandstream adapter with a rotary phone plugged in."],
  rotary: ["Treeline rotary phone", "The Treeline phone, paired with the code printed under it."],
};

/** "This device" in Add a phone: not a kind of its own (it is a softphone), but the one choice that needs no code to type. */
const THIS_DEVICE = ["thisdevice", "This device", "The phone, tablet or computer you're using now. The rotary phone opens here, and this dashboard stays closed on it until someone enters your parent code."];

/** Add a handset: pick the kind, name it, and (for softphones and Treeline phones) enter the code it shows. "This device" makes the
 *  browser in hand a phone, with no code: a parent is already signed in here. */
export async function addHandsetDialog(ctx) {
  const added = await formDialog({
    title: "Add a phone",
    intro: "Pick what you're connecting. Anything you add rings when someone calls your number.",
    submit: "Add phone",
    body: html`
      ${radioGroup({ name: "kind", legend: "What are you adding?", cards: true, value: "softphone",
        options: [["softphone", ...KIND.softphone], ["ata", ...KIND.ata], ["rotary", ...KIND.rotary], THIS_DEVICE] })}
      ${textField({ id: "hs-name", name: "name", label: "Name for this phone", placeholder: "Kitchen phone", hint: "You'll see this in your call log." })}
      <div data-for="code">${codeInput({ legend: "Code on the phone", hint: "Six digits. A softphone shows it on screen; the Treeline phone has it printed underneath." })}</div>
      ${hasParentCode(ctx) ? "" : html`<div class="tl-stack tl-stack--group" data-for="pin" hidden>${newCodeFields("add")}</div>`}`,
    onOpen(scrim) {
      const sync = () => {
        const kind = scrim.querySelector("input[name=kind]:checked").value;
        scrim.querySelector("[data-for=code]").hidden = kind === "ata" || kind === "thisdevice";
        const pin = scrim.querySelector("[data-for=pin]");
        if (pin) pin.hidden = kind !== "softphone" && kind !== "thisdevice";   // a softphone needs a parent code before it can be added
      };
      scrim.querySelectorAll("input[name=kind]").forEach((r) => r.addEventListener("change", sync));
      sync();
    },
    async onSubmit(form) {
      const kind = form.querySelector("input[name=kind]:checked").value;
      const name = form.querySelector("[name=name]").value;
      if ((kind === "softphone" || kind === "thisdevice") && !hasParentCode(ctx)) await saveNewCode(ctx, form);
      if (kind === "thisdevice") return { ...(await makeThisDeviceAPhone(name)), thisDevice: true };
      if (kind === "ata") return post("/api/handsets", { kind, name });
      const code = codeValue(form.querySelector("[data-for=code]"));
      return post("/api/pair/claim", { code, name, kind });
    },
  });
  if (!added) return false;
  if (added.thisDevice) { location.assign("/phone/"); return true; }     // locked to the phone from here on (lockedToPhone)
  if (added.credentials) await showAdapterSettings(added);
  else toast(`${added.handset.name} is connected`, "success");
  return true;
}

async function showAdapterSettings({ handset, credentials: c }) {
  const link = await get(`/api/handsets/${handset.id}/provision`);
  await infoDialog({
    title: `Set up ${handset.name}`,
    body: html`
      <p class="tl-sheet__body">Plug the adapter into your router, open its settings page and point it at this settings link, or type the account in by hand. The password is shown once.</p>
      <dl class="tl-dl">
        <div class="tl-dl__row"><dt>Settings link</dt><dd style="overflow-wrap:anywhere">${link.url}</dd></div>
        <div class="tl-dl__row"><dt>Server</dt><dd>${c.server}</dd></div>
        <div class="tl-dl__row"><dt>User ID</dt><dd>${c.sip_user}</dd></div>
        <div class="tl-dl__row"><dt>Password</dt><dd style="overflow-wrap:anywhere">${c.secret}</dd></div>
      </dl>
      <p class="tl-sheet__body">Step by step: docs/ADAPTER.md in the Treeline project.</p>`,
  });
}

const PHONE_KEY = "treeline.phone";            // where the softphone keeps its sign-in (same browser, same origin)

/** Turn this browser into a phone for the treehouse, with no QR code: a parent is already signed in. From then on this device is
 *  locked to the phone in every tab (see lockedToPhone), so the page goes straight to it. Only the parent code, typed on the phone, ends that. */
async function makeThisDeviceAPhone(name) {
  const made = await post("/api/handsets", { kind: "softphone", name: name || "This device" });
  const c = made.credentials;
  try {
    localStorage.setItem(PHONE_KEY, JSON.stringify({ sip_user: c.sip_user, secret: c.secret, server: c.server, ws_url: c.ws_url, realm: c.realm, handset_id: made.handset.id }));
  } catch {
    await del(`/api/handsets/${made.handset.id}`);                      // don't leave a phone behind that nothing can use
    throw new Error("This browser wouldn't save the phone's sign-in, so it can't be used as a phone.");
  }
  return made;
}

function handsetRow(h, parent = true) {
  const [kindName] = KIND[h.kind];
  const menuId = nextId("hm");
  const off = h.disabled;
  const status = off ? "Disconnected: no calls in or out" : h.online ? "Connected" : h.last_seen ? `Last seen ${relative(h.last_seen)}` : "Hasn't connected yet";
  return html`<div class="tl-row tl-log tl-log--${off ? "bark" : h.online ? "canopy" : "bark"}">
  <span class="tl-log__icon" aria-hidden="true">${icon(off ? "phone-off" : "phone")}</span>
  <div class="tl-row__main">
    <div class="tl-row__title">${h.name}</div>
    <div class="tl-row__meta"><span>${kindName}</span><span>${status}</span></div>
  </div>
  ${off ? presence("bark", "Disconnected") : presence(h.online ? "canopy" : "bark", h.online ? "Online" : "Offline")}
  <button type="button" role="switch" aria-checked="${off ? "false" : "true"}" aria-label="${h.name} connected" class="tl-switch${off ? "" : " is-on"}" data-handset-switch data-id="${h.id}" data-name="${h.name}"><span class="tl-switch__thumb">${off ? "" : icon("check", 12)}</span></button>
  <div class="tl-menu">
    <button type="button" class="tl-iconbtn tl-btn--quiet tl-iconbtn--md" aria-label="More for ${h.name}" title="More" aria-haspopup="menu" aria-expanded="false" aria-controls="${menuId}" data-tl-menu="${menuId}">${icon("more")}</button>
    <div class="tl-menu__panel" id="${menuId}" role="menu" hidden aria-label="${h.name}">
      ${off ? "" : html`<button role="menuitem" type="button" class="tl-menu__item" data-handset="ring" data-id="${h.id}">${icon("bell")}<span>Ring test</span></button>`}
      ${parent ? html`<button role="menuitem" type="button" class="tl-menu__item" data-handset="rename" data-id="${h.id}" data-name="${h.name}">${icon("settings")}<span>Rename</span></button>
      <div class="tl-menu__sep" role="separator"></div>
      <button role="menuitem" type="button" class="tl-menu__item tl-menu__item--danger" data-handset="remove" data-id="${h.id}" data-name="${h.name}">${icon("close")}<span>Remove</span></button>` : ""}
    </div>
  </div>
</div>`;
}

/** The number, the phones and the grown-ups: everything for managing the treehouse, drawn on Home. */
export function treehouseSections(ctx, handsets, grown_ups) {
  const th = ctx.me.treehouse, parent = ctx.isParent();
  return html`
  <section class="tl-card tl-card--plank" aria-label="Your number">
    <header class="tl-card__head"><div><p class="tl-card__eyebrow">Your number</p><h2 class="tl-card__title numeral tl-num" style="font-size:42px;line-height:50px">${th.number}</h2></div></header>
    <p class="tl-card__body">Friends dial this to reach ${th.name}. It only rings through when both families have approved the string.</p>
    ${parent ? html`<div class="tl-actions">${button({ label: "Change number", attrs: "data-change-number" })}</div>` : ""}
  </section>

  <section class="tl-stack" aria-label="Phones">
    <div class="tl-split"><h2 class="title-lg">Phones</h2>${parent ? button({ label: "Add a phone", size: "sm", icon: "plus", attrs: "data-add-phone" }) : ""}</div>
    ${handsets.length
      ? html`<div class="tl-card tl-card--list">${handsets.map((h) => handsetRow(h, parent))}</div>
        <p class="tl-card__body tl-measure" style="color:var(--ink-muted)">Use the switch to disconnect a phone for now. A disconnected phone doesn't ring and can't call out; your other phones carry on as usual.</p>`
      : emptyState({ art: null, title: "No phones yet", body: "Add a softphone, a phone adapter, the Treeline phone, or this device. They all ring together when a friend calls.",
          action: parent ? button({ label: "Add a phone", variant: "primary", icon: "plus", attrs: "data-add-phone" }) : null })}
  </section>

  <section class="tl-stack" aria-label="Grown-ups">
    <div class="tl-split"><h2 class="title-lg">Grown-ups</h2>${parent ? button({ label: "Add a grown-up", size: "sm", icon: "plus", attrs: "data-add-grownup" }) : ""}</div>
    <div class="tl-card tl-card--list">${grown_ups.map((g) => html`<div class="tl-row">
      ${avatar(g.name || g.email, "md")}
      <div class="tl-row__main"><div class="tl-row__title">${g.name || g.email}${g.you ? " (you)" : ""}</div><div class="tl-row__meta"><span>${g.name ? g.email : ""}</span></div></div>
      ${tag(g.role === "parent" ? "bark" : "neutral", g.role === "parent" ? "Parent" : "Sitter")}
      ${parent && !g.you ? iconButton({ label: `Remove ${g.name || g.email}`, name: "close", attrs: { "data-remove-grownup": g.id, "data-name": g.name || g.email } }) : ""}
    </div>`)}</div>
    <p class="tl-card__body tl-measure" style="color:var(--ink-muted)">Sitters can see today's calls, pause the line, turn quiet hours on or off, and disconnect or ring a phone. Only parents can change anything else.</p>
  </section>`;
}

/** The buttons and menus drawn by treehouseSections. */
export function bindTreehouse(root, ctx, refresh) {
  root.querySelectorAll("[data-add-phone]").forEach((b) => b.addEventListener("click", async () => { if (await addHandsetDialog(ctx)) refresh(); }));
  bindPhoneSwitches(root, refresh);
  root.querySelector("[data-change-number]")?.addEventListener("click", async () => { if (await changeNumber(ctx)) { await ctx.refreshMe(); refresh(); } });
  root.querySelector("[data-add-grownup]")?.addEventListener("click", async () => { if (await addGrownUp(ctx)) refresh(); });
  root.querySelectorAll("[data-remove-grownup]").forEach((b) => b.addEventListener("click", async () => {
    const ok = await confirmDialog({ title: `Remove ${b.dataset.name}?`, body: "They'll be signed out and won't see your treehouse anymore.", confirm: "Remove", danger: true,
      onConfirm: () => del(`/api/grown-ups/${b.dataset.removeGrownup}`) });
    if (ok) refresh();
  }));
  root.querySelectorAll("[data-handset]").forEach((b) => b.addEventListener("click", async () => {
    const { handset, id, name } = b.dataset;
    if (handset === "ring") {
      try { await post(`/api/handsets/${id}/ring-test`); toast(`${name} is ringing`, "success"); } catch (e) { toast(e.message, "warning"); }
    } else if (handset === "rename") {
      const r = await formDialog({ title: "Rename phone", submit: "Save",
        body: textField({ id: "rn", name: "name", label: "Name", value: name }),
        onSubmit: (f) => patch(`/api/handsets/${id}`, { name: f.querySelector("[name=name]").value }) });
      if (r) refresh();
    } else if (handset === "remove") {
      const ok = await confirmDialog({ title: `Remove ${name}?`, body: "It stops working right away, even in the middle of a call. You can add it again later.", confirm: "Remove phone", danger: true,
        onConfirm: () => del(`/api/handsets/${id}`) });
      if (ok) refresh();
    }
  }));
}

/** The connect/disconnect switch on a phone's row. */
export function bindPhoneSwitches(root, refresh) {
  root.querySelectorAll("[data-handset-switch]").forEach((sw) => sw.addEventListener("tl-change", async (e) => {
    const { id, name } = sw.dataset, connected = e.detail.checked;
    try {
      await patch(`/api/handsets/${id}`, { disabled: !connected });
      toast(connected ? `${name} is connected again` : `${name} is disconnected. It won't ring or place calls.`, connected ? "success" : "neutral");
      refresh();
    } catch (err) {
      window.TreelineUI?.setSwitch(sw, !connected);          // put the switch back; nothing changed
      toast(err.message, "warning");
    }
  }));
}

async function changeNumber(ctx) {
  const r = await formDialog({
    title: "Change your number",
    intro: "Families you're strung with get a note with your new number.",
    submit: "Change number", danger: false,
    body: html`${radioGroup({ name: "how", legend: "New number", value: "random", options: [["random", "Pick one for me", "A random four-digit number."], ["own", "I'll choose", "Four digits, not starting with 0."]] })}
      <div data-for="own" hidden>${textField({ id: "newnum", name: "number", label: "Number", attrs: 'inputmode="numeric" maxlength="4"' })}</div>`,
    onOpen(scrim) {
      scrim.querySelectorAll("input[name=how]").forEach((r) => r.addEventListener("change", () => {
        scrim.querySelector("[data-for=own]").hidden = scrim.querySelector("input[name=how]:checked").value !== "own";
      }));
    },
    async onSubmit(f) {
      const own = f.querySelector("input[name=how]:checked").value === "own";
      return post("/api/treehouse/number", own ? { number: f.querySelector("[name=number]").value } : {});
    },
  });
  if (r) toast(`Your number is now ${r.number}`, "success");
  return !!r;
}

async function addGrownUp(ctx) {
  const r = await formDialog({
    title: "Add a grown-up", intro: "They sign in with this email address.", submit: "Add",
    body: html`${textField({ id: "gu-email", name: "email", label: "Email", type: "email", placeholder: "name@example.com", hint: "The address they sign in to Google with. Treeline uses Google to sign in." })}
      ${textField({ id: "gu-name", name: "name", label: "Name (optional)" })}
      ${radioGroup({ name: "role", legend: "Role", value: "parent", options: [["parent", "Parent", "Can change everything, approve strings and add phones."], ["sitter", "Sitter", "Can see today's calls, pause the line, turn quiet hours on or off, and disconnect or ring a phone."]] })}`,
    onSubmit: (f) => post("/api/grown-ups", { email: f.querySelector("[name=email]").value, name: f.querySelector("[name=name]").value,
      role: f.querySelector("input[name=role]:checked").value }),
  });
  if (r) toast("Added. We sent them an email.", "success");
  return !!r;
}

export async function phonebook(ctx) {
  const book = await get("/api/phonebook");
  const content = html`
  <section class="tl-card tl-card--blossom">
    <header class="tl-card__head"><div><p class="tl-card__eyebrow">Phone book</p><h2 class="tl-card__title">${book.treehouse}</h2></div></header>
    <dl class="tl-dl"><div class="tl-dl__row"><dt>Our number</dt><dd class="tl-num"><strong>${book.number}</strong></dd></div></dl>
  </section>
  <section class="tl-stack">
    <h2 class="title-lg">Friends</h2>
    ${book.entries.length
      ? html`<div class="tl-card"><dl class="tl-dl">${book.entries.map((e) => html`<div class="tl-dl__row"><dt>${e.name}${e.state === "paused" ? " (paused)" : ""}</dt><dd class="tl-num"><strong>${e.number}</strong></dd></div>`)}</dl></div>`
      : emptyState({ art: "neighborhood", title: "No friends yet", body: "Once a string is approved, their number shows up here, ready to print and keep by the phone.",
          action: button({ label: "Go to Strings", variant: "primary", attrs: 'data-href="#/strings"' }) })}
  </section>
  <p class="caption" style="color:var(--ink-muted)">${NO_911}</p>
  <div class="tl-actions tl-noprint">${button({ label: "Print", variant: "primary", attrs: "data-print" })}</div>`;
  return { title: "Phone book", nav: "home", back: "#/home", content, mount(root) { root.querySelector("[data-print]")?.addEventListener("click", () => window.print()); } };
}
