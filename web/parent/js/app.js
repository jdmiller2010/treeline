// The Treeline parent app: a small hash-routed single page app.
import { get, post, patch, del, token, ApiError } from "/shared/api.js";
import { avatar, brand, footer, TAGLINE, html, icon, iconButton, button, loader, raw, str, alert, toast, textField } from "/shared/ui.js";
import { plural } from "/shared/format.js";
import { lockedToPhone, onInstallChange, registerApp } from "/shared/pwa.js";
import { installAvailable, installSteps, runInstall } from "/shared/install.js";
import { infoDialog } from "./dialogs.js";
import { signIn } from "./signin.js";
import { agree, setup } from "./setup.js";
import { home } from "./home.js";
import { strings } from "./strings.js";
import { calls } from "./calls.js";
import { quiet } from "./quiet.js";
import { phonebook } from "./house.js";
import { profile, privacy, about, actionLog, pairClaim, stringLink } from "./account.js";
import { carryOverPush, forgetPushQuietly } from "./push.js";
import { admin } from "./admin.js";

const root = document.getElementById("root");

export const ctx = {
  signOut: () => signOut(),
  me: null,
  async refreshMe() {
    this.me = await get("/api/me");
    return this.me;
  },
  go(hash) { if (location.hash === hash) render(); else location.hash = hash; },
  toast,
  isParent() { return this.me?.grown_up?.role === "parent"; },
  render: () => render(),
};

const NAV = [
  ["home", "#/home", "Home", "home"],
  ["strings", "#/strings", "Strings", "users"],
  ["calls", "#/calls", "Calls", "phone"],
  ["phonebook", "#/phonebook", "Phone book", "book"],
  ["quiet", "#/quiet", "Quiet hours", "clock"],
];

const ROUTES = {
  home, strings, calls, quiet, phonebook, profile, privacy, about, actions: actionLog,
  settings: async () => ({ redirect: "#/home" }),       // (Settings is part of Home now; old links still land somewhere)
  pair: pairClaim, string: stringLink, ladder: stringLink, admin,   // (#/ladder/ is kept so links already sent still work)
};

function parseHash() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { name: parts[0] || "", params: parts.slice(1) };
}

function accountMenu() {
  const me = ctx.me;
  const who = me.grown_up?.name || me.email;
  return html`<div class="tl-menu">
  <button type="button" class="tl-avatar-btn" aria-label="Account" aria-haspopup="menu" aria-expanded="false" aria-controls="account-menu" data-tl-menu="account-menu">${avatar(who, "sm")}</button>
  <div class="tl-menu__panel" id="account-menu" role="menu" hidden aria-label="Account">
    <div class="tl-menu__head"><span class="tl-menu__name">${who}</span><span class="tl-menu__meta">${me.treehouse.name}</span></div>
    ${[["#/profile", "Profile", "users"],
       ["#/privacy", "Privacy and safety", "shield-check"], ["#/about", "About Treeline", "info"]].map(([href, label, ic]) =>
      html`<a role="menuitem" href="${href}" class="tl-menu__item">${icon(ic)}<span>${label}</span></a>`)}
    ${me.admin ? html`<a role="menuitem" href="#/admin" class="tl-menu__item" data-admin-link>${icon("key")}<span>Treeline Admin</span></a>` : ""}
    <button role="menuitem" type="button" class="tl-menu__item" data-install-app ${installAvailable() ? "" : raw("hidden")}>${icon("plus")}<span>Install the app</span></button>
    <div class="tl-menu__sep" role="separator"></div>
    <button role="menuitem" type="button" class="tl-menu__item tl-menu__item--danger" data-sign-out>${icon("log-out")}<span>Sign out</span></button>
  </div>
</div>`;
}

function navBar(current, badge) {
  const th = ctx.me.treehouse;
  return html`<nav class="tl-nav" aria-label="Main"><div class="tl-nav__inner">
  <div class="tl-nav__brand">${brand("#/home")}</div>
  <ul class="tl-nav__list">${NAV.map(([key, href, label, ic]) => html`<li><a class="tl-nav__item" href="${href}" ${key === current ? raw('aria-current="page"') : ""}>${
    key === "strings" && badge
      ? html`<span class="tl-badge-anchor">${icon(ic, 24)}<span class="tl-badge" aria-hidden="true">${badge}</span><span class="tl-sr">${plural(badge, "approval")} waiting</span></span>`
      : icon(ic, 24)}<span class="tl-nav__label">${label}</span></a></li>`)}</ul>
  <div class="tl-nav__foot"><div class="tl-split"><div class="tl-stack tl-stack--tight"><span class="tl-nav__house">${th.name}</span><span class="tl-nav__meta">Number ${th.number}</span></div></div></div>
</div></nav>`;
}

/** The header bar is the same on every page: the logo, the treehouse's name, the pause button and the account menu. What a page is
 *  called is its own hidden h1 and its visible section titles; the page's buttons sit down in the page, by their sections. */
function pauseButton() {
  const th = ctx.me.treehouse;
  return button({ label: th.paused ? "Turn calls back on" : "Pause calls", variant: "secondary", collapse: true, icon: th.paused ? "phone" : "pause", attrs: "data-pause" });
}

/** The signed-in shell around a view. */
function shell(v) {
  const content = v.template === "settings"
    ? html`<div class="tl-page tl-page--narrow"><div class="tl-stack tl-stack--cards">${v.content}${footer()}</div></div>`
    : html`<div class="tl-page"><div class="tl-stack tl-stack--sections">${v.content}${footer()}</div></div>`;
  return html`<div class="tl-app">
  <div class="tl-app__layout">
    <header class="tl-appbar${v.lockup ? " tl-appbar--lockup" : ""}">
      ${v.back ? html`<div class="tl-appbar__lead">${iconButton({ label: "Back", name: "chevron-right", extra: "tl-iconbtn--back", attrs: { "data-back": v.back } })}</div>` : ""}
      <span class="tl-appbar__brand">${brand("#/home")}</span>
      <div class="tl-appbar__text">
        ${v.lockup ? html`<span class="tl-appbar__lockup" aria-hidden="true"><span class="tl-appbar__word">Treeline</span><span class="tl-tagline">${TAGLINE}</span></span>` : ""}
        <span class="tl-appbar__title" id="app-title">${ctx.me.treehouse.name}</span>
      </div>
      <div class="tl-appbar__actions">${pauseButton()}${accountMenu()}</div>
    </header>
    <main class="tl-app__main" id="main"><h1 class="tl-sr">${v.title}</h1>${content}</main>
    ${navBar(v.nav, ctx.badge || 0)}
  </div>
  ${v.sheets || ""}
  <div class="tl-toasts" aria-live="polite"></div>
</div>`;
}

/** A treehouse Treeline staff paused: nothing works but signing out and deleting it (a family can always end things itself). */
function pausedByTreeline(ctx) {
  const th = ctx.me.treehouse;
  const content = html`<h1 class="title-lg">${th.name} is paused</h1>${alert({ tone: "warning", title: `Treeline has paused ${th.name} for now`,
    body: "Its phones can't call or ring while it is paused. Treeline never connects to 911: use a regular phone in an emergency. If you didn't expect this, write to the email address at the bottom of this page." })}
  <form class="tl-card" id="paused-delete" novalidate><div class="tl-stack tl-stack--group">
    <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">Delete your treehouse</h2>
    <p class="tl-card__body">This erases your treehouse, phones, strings and call records now, for good. Type its name to confirm.</p></div>
    ${textField({ id: "paused-name", name: "confirm", label: "Treehouse name", placeholder: th.name })}
    <div data-error></div>
    <div class="tl-actions">${button({ label: "Sign out", attrs: "data-paused-signout" })}${button({ label: "Delete everything", variant: "danger", type: "submit" })}</div>
  </div></form>`;
  return {
    bare: true, title: "Paused", noDoodles: true, content,
    mount(root) {
      root.querySelector("[data-paused-signout]").addEventListener("click", () => ctx.signOut());
      root.querySelector("#paused-delete").addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await del("/api/treehouse", { confirm: root.querySelector("#paused-name").value }); toast("Everything was deleted", "success"); ctx.signOut(); }
        catch (err) { root.querySelector("[data-error]").innerHTML = String(alert({ tone: "danger", title: err.message })); }
      });
    },
  };
}

/** Pages with no shell: sign-in and setup. */
function barePage(v) {
  return html`<main class="tl-page tl-page--narrow tl-page--bare" id="main"><div class="tl-stack tl-stack--sections">${v.content}${footer()}</div></main>${v.sheets || ""}<div class="tl-toasts" aria-live="polite"></div>`;
}

let renderToken = 0;

async function render() {
  if (lockedToPhone()) { location.replace("/phone/"); return; }      // a phone can't use the dashboard, in any tab, until a parent code is entered on it
  const mine = ++renderToken;
  const { name, params } = parseHash();
  document.body.className = "tl-root";
  try {
    if (!token.get()) {
      if (name !== "signin" && name) { try { sessionStorage.setItem("tl-next", location.hash); } catch { /* fine */ } }
      return show(await signIn(ctx), mine);
    }
    if (!ctx.me) {
      root.innerHTML = str(loader("Opening Treeline"));
      await ctx.refreshMe();
    } else if (ctx.me.archived) {
      await ctx.refreshMe();                    // paused by Treeline: ask again on every move, so a restore shows at once
    }
    if (ctx.me.archived) return show(pausedByTreeline(ctx), mine);
    if (!ctx.me.treehouse) return show(await setup(ctx), mine);
    if (ctx.me.agreed === false) return show(await agree(ctx), mine);     // a grown-up added later, or the documents changed
    if (name === "setup") return ctx.go("#/home");
    const route = ROUTES[name];
    if (!route) return ctx.go("#/home");
    document.body.className = "";
    show(await route(ctx, params), mine);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) { ctx.me = null; return render(); }
    // The documents changed while this app was open (or a parent just added this grown-up): ask again, here, before anything else.
    if (e instanceof ApiError && e.code === "agreement_needed") { ctx.me = null; return render(); }
    root.innerHTML = str(barePage({ content: alert({ tone: "danger", title: "That didn't load", body: e.message,
      actions: button({ label: "Try again", size: "sm", attrs: "data-retry" }) }) }));
    root.querySelector("[data-retry]")?.addEventListener("click", () => render());
  }
}

/** The artist's layer: doodles on the top edge of a few cards, the same all day for a page. Purely decoration: with the script missing,
 *  nothing changes. Nothing is measured, so there is nothing to redo when fonts load or the window resizes. */
function decorate(v) {
  if (v.noDoodles) return;                    // working screens (Treeline Admin)
  window.TLDoodles?.scatter(root.querySelector(".tl-app__main") || root.querySelector("main"), (v.title || "") + location.hash);
}

function show(v, mine) {
  if (mine !== renderToken) return;       // a newer navigation won
  if (v.redirect) return ctx.go(v.redirect);
  const markup = v.bare ? barePage(v) : shell(v);
  // A toast shown just before a re-render ("Saved") must survive it.
  const liveToasts = [...root.querySelectorAll(".tl-toast")];
  root.innerHTML = str(markup);
  const region = root.querySelector(".tl-toasts");
  if (region) liveToasts.forEach((t) => region.appendChild(t));
  document.title = (v.title ? v.title + " · " : "") + "Treeline";
  window.scrollTo(0, 0);
  decorate(v);
  root.querySelector("[data-sign-out]")?.addEventListener("click", signOut);
  root.querySelector("[data-install-app]")?.addEventListener("click", async () => {
    if (await runInstall() === "steps") await infoDialog({ title: "Install Treeline", body: installSteps() });
  });
  root.querySelector("[data-pause]")?.addEventListener("click", async () => {
    try {
      const r = await patch("/api/treehouse", { paused: !ctx.me.treehouse.paused });
      ctx.me.treehouse = r;
      toast(r.paused ? "Calls are paused" : "Calls are back on", r.paused ? "neutral" : "success");
      ctx.render();
    } catch (e) { toast(e.message, "warning"); }
  });
  root.querySelector("[data-back]")?.addEventListener("click", (e) => ctx.go(e.currentTarget.dataset.back));
  root.querySelectorAll("[data-dismiss]").forEach((b) => b.addEventListener("click", async () => {
    const id = b.dataset.dismiss;
    b.closest(".tl-alert")?.remove();
    try { await post(`/api/notices/${id}/dismiss`); } catch { /* it will show again next time */ }
  }));
  root.querySelectorAll("[data-href]").forEach((row) => {
    const go = () => ctx.go(row.dataset.href);
    row.addEventListener("click", go);
    row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  });
  v.mount?.(root);
  // Move focus to the page's start for keyboard and screen reader users.
  document.getElementById("app-title")?.setAttribute("tabindex", "-1");
}

async function signOut() {
  await forgetPushQuietly();                 // this device shouldn't keep buzzing for someone who signed out
  try { await post("/api/auth/signout"); } catch { /* signing out anyway */ }
  token.clear(); ctx.me = null; ctx.go("#/signin");
}

// The browser may offer the install prompt after the page drew: show or hide the menu item as that changes.
onInstallChange(() => { const item = document.querySelector("[data-install-app]"); if (item) item.hidden = !installAvailable(); });
window.addEventListener("hashchange", render);
window.addEventListener("tl-signed-out", () => { ctx.me = null; render(); });
// A device that is a phone stays a phone in every tab until a parent code is entered there. (A tab that was already open finds out when
// the phone's sign-in is saved in another one.)
window.addEventListener("storage", () => { if (lockedToPhone()) location.replace("/phone/"); });
if (lockedToPhone()) location.replace("/phone/");
else { registerApp().then(() => { if (token.get()) carryOverPush(); }); render(); }
