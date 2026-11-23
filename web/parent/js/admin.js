// Treeline Admin (docs/ADMIN.md): for the people who run Treeline, never a view into a family. The server decides who may see these
// pages (every /api/admin call is checked there); the menu link only appears for an admin. Log text is set with textContent.
import { get, post, ApiError } from "/shared/api.js";
import { html, card, button, alert, emptyState, selectField, tag, icon, setBusy } from "/shared/ui.js";
import { when as whenRaw } from "/shared/format.js";

/** A date from the machine, shown as a time; anything that is not a date shows as it is (it never breaks the page). */
function when(iso, tz) {
  try { return whenRaw(iso, tz); } catch { return String(iso || ""); }
}

const SOURCE_NAMES = {
  deploy: "Deploys", backup: "Backups", health: "Health ping", certsync: "Certificate copy", caddy: "Web server (Caddy)", bridge: "This helper",
};
const SINCE_NAMES = { "15m": "15 minutes", "1h": "1 hour", "6h": "6 hours", "24h": "24 hours", boot: "Since start-up" };
const ACTION_NAMES = {
  admin_add: (a) => `Made ${a.target_id} an admin`, admin_remove: (a) => `Removed ${a.target_id} as an admin`,
  logs_view: (a) => `Read the ${SOURCE_NAMES[a.target_id] || a.target_id} log (${a.detail || ""})`,
};

const PAGES = [
  ["logs", "Logs", "The machine's logs: deploys, backups, the health ping, the web server.", "info"],
  ["releases", "Releases", "What is running, what has been published, and what failed.", "trend-up"],
  ["admins", "Admins", "Who can open this page.", "key"],
  ["audit", "Audit log", "What admins did here, and when.", "shield-check"],
];

/** The page a session that is too old to use admin pages gets (the server says so); never a sign-in loop. */
function signInAgain(ctx) {
  return {
    title: "Treeline Admin", back: "#/settings", nav: null, template: "settings", noDoodles: true,
    content: html`${alert({ tone: "warning", title: "Sign in again to use the admin page",
      body: "Admin pages need a sign-in from the last 12 hours. Sign out, then sign in again.",
      actions: button({ label: "Sign out and sign in again", size: "sm", attrs: "data-resignin" }) })}`,
    mount(root) { root.querySelector("[data-resignin]").addEventListener("click", () => ctx.signOut()); },
  };
}

async function guarded(ctx, page) {
  if (!ctx.me?.admin) return { redirect: "#/home" };
  try {
    return await page();
  } catch (e) {
    if (e instanceof ApiError && e.code === "needs_fresh_signin") return signInAgain(ctx);
    if (e instanceof ApiError && e.status === 404) return { redirect: "#/home" };       // not an admin (any more)
    throw e;
  }
}

function overview() {
  const content = html`<h2 class="title-lg">Treeline Admin</h2>
  <p class="body">For running Treeline. Nothing here shows a family's calls, strings or settings, and nothing here can add a person or a phone.</p>
  <div class="tl-card tl-card--list">${PAGES.map(([key, label, desc, ic]) => html`<div class="tl-row is-clickable" role="link" tabindex="0" data-href="#/admin/${key}">
    ${icon(ic, 24)}<div class="tl-row__main"><div class="tl-row__title">${label}</div><div class="tl-row__meta"><span>${desc}</span></div></div>${icon("chevron-right")}</div>`)}</div>`;
  return { title: "Treeline Admin", back: "#/settings", nav: null, template: "settings", noDoodles: true, content };
}

async function logsPage() {
  const info = await get("/api/admin/logs/sources");
  const pick = html`<form class="tl-stack tl-stack--group" id="log-form" novalidate>
    ${selectField({ id: "log-source", name: "source", label: "Log", options: info.sources.map((s) => [s, SOURCE_NAMES[s] || s]), value: info.sources[0] })}
    ${selectField({ id: "log-since", name: "since", label: "Time range", options: info.since.map((s) => [s, SINCE_NAMES[s] || s]), value: "1h" })}
    <div class="tl-actions">${button({ label: "Show", variant: "primary", type: "submit", attrs: "data-show" })}</div>
  </form>`;
  const content = html`<h2 class="title-lg">Logs</h2>
  ${info.installed ? "" : alert({ tone: "warning", title: "The helper on the machine is not installed yet",
    body: "Run install.sh once from the release that brought this page (a deploy does not install it)." })}
  ${card({ title: "Which log", children: pick })}
  <div data-result></div>
  <p class="body-sm" style="color:var(--ink-muted)">Only the time since the machine last started: logs are kept in memory, never on the disk. Addresses, emails and
    account numbers are hidden. The app's own call and sign-in logs are not shown here.</p>`;
  return {
    title: "Logs", back: "#/admin", nav: null, template: "settings", noDoodles: true, content,
    mount(root) {
      const form = root.querySelector("#log-form");
      const out = root.querySelector("[data-result]");
      if (!info.installed) form.querySelector("[data-show]").disabled = true;
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const showBtn = form.querySelector("[data-show]");
        const source = form.querySelector("#log-source").value;
        const since = form.querySelector("#log-since").value;
        setBusy(showBtn, true, "Asking");
        out.innerHTML = "";
        try {
          const { id } = await post("/api/admin/logs", { source, since, lines: 500 });
          let r = { status: "pending" };
          for (let i = 0; i < 30 && r.status === "pending"; i++) {
            await new Promise((ok) => setTimeout(ok, i < 5 ? 600 : 1500));
            r = await get(`/api/admin/logs/${id}`);
          }
          out.innerHTML = String(logCard(source, since, r));
          const pre = out.querySelector(".tl-logview");
          if (pre && r.status === "ok") {
            if (r.text.trim()) { pre.textContent = r.text; pre.scrollTop = pre.scrollHeight; }
            else pre.innerHTML = '<span class="tl-logview__empty">Nothing logged in this time range.</span>';
          }
        } catch (err) {
          out.innerHTML = String(alert({ tone: "danger", title: err.message }));
        } finally { setBusy(showBtn, false); }
      });
    },
  };
}

function logCard(source, since, r) {
  const title = `${SOURCE_NAMES[source] || source}, ${SINCE_NAMES[since] || since}`;
  if (r.status === "pending") return alert({ tone: "warning", title: "The helper did not answer", body: "Try again in a minute. If it keeps happening, the helper's units may be stopped." });
  if (r.status !== "ok") return alert({ tone: "danger", title: "The helper refused that request", body: r.reason || "" });
  return card({ title, head: r.truncated ? tag("neutral", "Newest part only") : "",
    children: html`<pre class="tl-logview" tabindex="0" aria-label="${title}"></pre>` });
}

async function releasesPage(ctx) {
  const r = await get("/api/admin/releases");
  const rep = r.report;
  const tz = ctx.me.treehouse?.timezone;
  const facts = html`<dl class="tl-dl">
    <div class="tl-dl__row"><dt>Running</dt><dd>${r.running || "a development build"}</dd></div>
    ${rep ? html`<div class="tl-dl__row"><dt>Asterisk</dt><dd>${rep.asterisk || "not running"}</dd></div>
    <div class="tl-dl__row"><dt>Before this</dt><dd>${rep.previous || "none"}</dd></div>
    <div class="tl-dl__row"><dt>Checked</dt><dd>${rep.at ? when(rep.at, tz) : "never"}</dd></div>` : ""}
  </dl>`;
  const list = rep && rep.published.length ? html`<div class="tl-card tl-card--list">${rep.published.map((p) => html`<div class="tl-row">
    <div class="tl-row__main"><div class="tl-row__title">${p.version}</div>
      <div class="tl-row__meta">${p.published_at ? html`<span>Published ${when(p.published_at, tz)}</span>` : ""}</div></div>
    ${p.version === rep.current ? tag("canopy", "Running") : p.failed ? tag("berry", "Failed before") : p.newer ? tag("sky", "Newer") : ""}
  </div>`)}</div>` : emptyState({ title: "No releases listed", body: rep ? (rep.error || "Nothing has been published yet.") : "The helper has not reported yet. It checks every 15 minutes." });
  const content = html`<h2 class="title-lg">Releases</h2>
  ${r.installed ? "" : alert({ tone: "warning", title: "The helper on the machine is not installed yet", body: "Run install.sh once from the release that brought this page." })}
  ${rep && rep.error && rep.published.length ? alert({ tone: "warning", title: "The last check did not finish", body: rep.error }) : ""}
  ${card({ title: "This machine", children: facts })}
  <h2 class="title-md">Published</h2>
  ${list}
  <p class="body-sm" style="color:var(--ink-muted)">A newer release is installed by the machine itself, between 09:00 and 12:00 UTC when no call is in progress.
    Installing one from this page is the next step of the admin page; until then, run <code>sudo treeline-deploy --version vX.Y.Z</code> on the machine.</p>`;
  return { title: "Releases", back: "#/admin", nav: null, template: "settings", noDoodles: true, content };
}

async function adminsPage() {
  const { admins } = await get("/api/admin/admins");
  const content = html`<h2 class="title-lg">Admins</h2>
  <div class="tl-card tl-card--list">${admins.map((a) => html`<div class="tl-row"><div class="tl-row__main"><div class="tl-row__title">${a.email}</div>
    <div class="tl-row__meta"><span>Added ${when(a.created_at)}</span><span>by ${a.added_by}</span></div></div></div>`)}</div>
  <p class="body-sm" style="color:var(--ink-muted)">Admins are added and removed on the machine for now: <code>sudo treeline-admin add EMAIL</code>.</p>`;
  return { title: "Admins", back: "#/admin", nav: null, template: "settings", noDoodles: true, content };
}

async function auditPage(ctx, before) {
  const r = await get("/api/admin/audit" + (before ? `?before=${encodeURIComponent(before)}` : ""));
  const tz = ctx.me.treehouse?.timezone;
  const content = html`<h2 class="title-lg">Audit log</h2>
  ${r.audit.length ? html`<div class="tl-card tl-card--list">${r.audit.map((a) => html`<div class="tl-row"><div class="tl-row__main">
    <div class="tl-row__title">${(ACTION_NAMES[a.action] || (() => a.action.replaceAll("_", " ")))(a)}</div>
    <div class="tl-row__meta"><span>${a.email}</span><span>${when(a.at, tz)}</span></div></div></div>`)}</div>`
    : emptyState({ title: "Nothing yet", body: "What admins do here shows up in this list." })}
  ${r.next ? html`<div class="tl-actions">${button({ label: "Older", attrs: { "data-href": `#/admin/audit/${r.next}` } })}</div>` : ""}`;
  return { title: "Audit log", back: "#/admin", nav: null, template: "settings", noDoodles: true, content };
}

export async function admin(ctx, params) {
  const [page, arg] = params;
  return guarded(ctx, () => {
    if (!page) return overview();
    if (page === "logs") return logsPage();
    if (page === "releases") return releasesPage(ctx);
    if (page === "admins") return adminsPage();
    if (page === "audit") return auditPage(ctx, /^\d+$/.test(arg || "") ? arg : null);
    return { redirect: "#/admin" };
  });
}
