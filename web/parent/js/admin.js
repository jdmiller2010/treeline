// Treeline Admin (docs/ADMIN.md): for the people who run Treeline, never a view into a family. The server decides who may see these
// pages (every /api/admin call is checked there); the menu link only appears for an admin. Log text is set with textContent.
import { get, post, ApiError } from "/shared/api.js";
import { html, card, button, alert, emptyState, selectField, textField, tag, icon, raw, setBusy, toast } from "/shared/ui.js";
import { when as whenRaw } from "/shared/format.js";

/** A date from the machine, shown as a time; anything that is not a date shows as it is (it never breaks the page). */
function when(iso, tz) {
  try { return whenRaw(iso, tz); } catch { return String(iso || ""); }
}

const SOURCE_NAMES = {
  deploy: "Deploys", backup: "Backups", health: "Health ping", certsync: "Certificate copy", caddy: "Web server (Caddy)", bridge: "This helper",
};
const SINCE_NAMES = { "15m": "15 minutes", "1h": "1 hour", "6h": "6 hours", "24h": "24 hours", boot: "Since start-up" };
/** Put markup in a placeholder box and show it, or empty and hide it (an empty box would still take the page's spacing). */
function fill(box, markup) {
  box.innerHTML = markup ? String(markup) : "";
  box.hidden = !markup;
  return box;
}

/** Run something that changes things. If the server wants a fresh sign-in first (needs_stepup), get one, then run it again.
 *  With Google the browser leaves for Google and comes back to this page (#/admin/stepup.ok); returns null then. */
async function act(ctx, root, fn) {
  try { return await fn(); } catch (e) {
    if (!(e instanceof ApiError && e.code === "needs_stepup")) throw e;
    if (!(await stepUp(ctx, root))) return null;
    return fn();
  }
}

async function stepUp(ctx, root) {
  const st = await get("/api/admin/stepup");
  if (st.google) {
    const { url } = await post("/api/admin/stepup");
    try { sessionStorage.setItem("tl-stepup-return", location.hash); } catch { /* then back to the overview */ }
    location.assign(url);
    return false;
  }
  // Development and the test suites only (the server refuses this in production): the emailed code stands in for Google.
  const r = await post("/api/auth/request", { email: ctx.me.email });
  const box = root.querySelector("[data-stepup]");
  fill(box, card({ title: "Confirm it's you", children: html`<form class="tl-stack tl-stack--group" id="stepup-form" novalidate>
    ${textField({ id: "stepup-code", name: "code", label: "The code we just emailed you", attrs: { inputmode: "numeric", autocomplete: "one-time-code" } })}
    ${r.dev_code ? html`<p class="body-sm" id="stepup-dev" style="color:var(--ink-muted)">Development: the code is ${r.dev_code}</p>` : ""}
    <div class="tl-actions">${button({ label: "Confirm", type: "submit" })}</div></form>` }));
  const form = box.querySelector("#stepup-form");
  await new Promise((done) => form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await post("/api/admin/stepup/code", { code: form.querySelector("#stepup-code").value }); fill(box, ""); done(); }
    catch (err) { toast(err.message, "warning"); }
  }));
  return true;
}

const ACTION_NAMES = {
  admin_add: (a) => `Made ${a.target_id} an admin`,
  treehouses_viewed: (a) => `Looked at the ${a.target_id} treehouses (${a.detail || ""})`, treehouse_viewed: (a) => `Opened treehouse ${a.target_id}`,
  treehouse_archived: (a) => `Paused treehouse ${a.target_id} (${(a.detail || "").replace("reason=", "")})`,
  treehouse_restored: (a) => `Brought treehouse ${a.target_id} back`, treehouse_erased: (a) => `Treehouse ${a.target_id} was erased (${a.detail || ""})`,
  grown_up_removed: (a) => `Removed a grown-up from treehouse ${a.target_id}`, handset_removed: (a) => `Removed a phone from treehouse ${a.target_id}`,
  release_install: (a) => `Asked to install ${a.target_id}`, admin_remove: (a) => `Removed ${a.target_id} as an admin`,
  logs_view: (a) => `Read the ${SOURCE_NAMES[a.target_id] || a.target_id} log (${a.detail || ""})`,
};

const PAGES = [
  ["treehouses", "Treehouses", "Find a family by name, number or a grown-up's email; pause one, bring it back, remove a person or a phone.", "home"],
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
  <div data-result hidden></div>
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
        fill(out, "");
        try {
          const { id } = await post("/api/admin/logs", { source, since, lines: 500 });
          let r = { status: "pending" };
          for (let i = 0; i < 30 && r.status === "pending"; i++) {
            await new Promise((ok) => setTimeout(ok, i < 5 ? 600 : 1500));
            r = await get(`/api/admin/logs/${id}`);
          }
          fill(out, logCard(source, since, r));
          const pre = out.querySelector(".tl-logview");
          if (pre && r.status === "ok") {
            if (r.text.trim()) { pre.textContent = r.text; pre.scrollTop = pre.scrollHeight; }
            else pre.innerHTML = '<span class="tl-logview__empty">Nothing logged in this time range.</span>';
          }
        } catch (err) {
          fill(out, alert({ tone: "danger", title: err.message }));
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

const DEPLOY_SAYS = {
  running: ["info", (d) => `Installing ${d.version}`, "It waits for calls to end (it never cuts one), then switches and checks the new release. If it is not healthy it goes back to the one that was running, by itself. This page keeps checking."],
  healthy: ["success", (d) => `${d.version} is installed and healthy`, ""],
  rolled_back: ["warning", (d) => `${d.version} was not healthy, so the machine went back to ${d.from || "the one before"}`, "Nothing else changed. Its log is below."],
  refused: ["warning", () => "The machine did not install it", ""],
  busy: ["warning", (d) => `${d.version} was not installed: a call was still going after 10 minutes, or another install was running`, "Nothing changed. Try again later."],
  needs_operator: ["danger", (d) => `Installing ${d.version} needs you on the machine`, "The machine could not finish or undo the change by itself. Over ssh: sudo treeline-deploy status, and the Deploys log."],
};

function deployPanel(d) {
  if (!d) return "";
  const [tone, title, body] = DEPLOY_SAYS[d.state] || ["warning", () => d.state, ""];
  return html`<div class="tl-stack tl-stack--cards">${alert({ tone, title: title(d), body: d.state === "refused" ? d.reason || "" : body })}
    ${d.output ? card({ title: "What the machine said", children: html`<pre class="tl-logview" tabindex="0" aria-label="Install output" data-output></pre>` }) : ""}</div>`;
}

async function releasesPage(ctx) {
  const r = await get("/api/admin/releases");
  const rep = r.report;
  const tz = ctx.me.treehouse?.timezone;
  const busy = r.deploy?.state === "running";
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
    ${p.newer && p.version !== rep.current && r.can_install && !busy ? button({ label: p.failed ? "Try again" : "Install", size: "sm",
      attrs: { "data-install": p.version, "data-retry": p.failed ? "1" : "" } }) : ""}
  </div>`)}</div>` : emptyState({ title: "No releases listed", body: rep ? (rep.error || "Nothing has been published yet.") : "The helper has not reported yet. It checks every 15 minutes." });
  const content = html`<h2 class="title-lg">Releases</h2>
  ${r.installed ? "" : alert({ tone: "warning", title: "The helper on the machine is not installed yet", body: "Run install.sh once from the release that brought this page." })}
  <div data-deploy ${r.deploy ? "" : raw("hidden")}>${deployPanel(r.deploy)}</div>
  <div data-confirm hidden></div>
  <div data-stepup hidden></div>
  ${rep && rep.error && rep.published.length ? alert({ tone: "warning", title: "The last check did not finish", body: rep.error }) : ""}
  ${card({ title: "This machine", children: facts })}
  <h2 class="title-md">Published</h2>
  ${list}
  <p class="body-sm" style="color:var(--ink-muted)">The machine also installs a newer release by itself, between 09:00 and 12:00 UTC when no call is in progress.
    Installing asks you to sign in with Google again first.</p>`;
  return {
    title: "Releases", back: "#/admin", nav: null, template: "settings", noDoodles: true, content,
    mount(root) {
      const out = root.querySelector("[data-output]");
      if (out) out.textContent = r.deploy.output;
      if (busy) pollDeploy(ctx, root);
      root.querySelectorAll("[data-install]").forEach((b) => b.addEventListener("click", () => {
        const version = b.dataset.install, retry = b.dataset.retry === "1";
        const box = root.querySelector("[data-confirm]");
        fill(box, alert({ tone: "info", title: `Install ${version}?`,
          body: "Calls in progress are never cut: it waits up to 10 minutes for them to end. If the new release is not healthy, the machine goes back to the one running now, by itself.",
          actions: html`${button({ label: "Not now", size: "sm", attrs: "data-keep" })}${button({ label: "Install", variant: "primary", size: "sm", attrs: "data-yes" })}` }));
        box.querySelector("[data-keep]").addEventListener("click", () => fill(box, ""));
        box.querySelector("[data-yes]").addEventListener("click", async (e) => {
          const yes = e.currentTarget;
          setBusy(yes, true, "Asking");
          try {
            const ok = await act(ctx, root, () => post("/api/admin/releases/install", { version, retry }));
            if (ok) { fill(box, ""); toast(`Asked the machine to install ${version}`, "success"); setTimeout(() => ctx.render(), 2500); }
          } catch (err) { toast(err.message, "warning"); setBusy(yes, false); }
        });
      }));
    },
  };
}

/** While an install runs the API itself restarts: keep asking, quietly, until the machine says how it ended. */
function pollDeploy(ctx, root) {
  let tries = 0;
  const tick = async () => {
    if (!document.body.contains(root.querySelector("[data-deploy]"))) return;       // the page was left
    tries += 1;
    try {
      const r = await get("/api/admin/releases");
      if (r.deploy?.state !== "running") { ctx.render(); return; }
    } catch { /* the API is restarting */ }
    if (tries < 600) setTimeout(tick, 4000);
  };
  setTimeout(tick, 4000);
}

const REASON_NAMES = [["family_asked", "The family asked"], ["safety", "A safety report"], ["security", "A security problem"], ["cleanup", "Clean-up or a test"]];

async function treehousesPage(ctx, state = "active") {
  const q = (() => { try { return sessionStorage.getItem("tl-admin-q") || ""; } catch { return ""; } })();
  const r = await get(`/api/admin/treehouses?state=${state}` + (q ? `&q=${encodeURIComponent(q)}` : ""));
  const tz = ctx.me.treehouse?.timezone;
  const rows = r.treehouses.length ? html`<div class="tl-card tl-card--list">${r.treehouses.map((t) => html`<div class="tl-row is-clickable" role="link" tabindex="0"
      ${raw(`data-href="#/admin/treehouse/${Number(t.id)}"`)}>
    <div class="tl-row__main"><div class="tl-row__title">${t.name} <span class="tl-num">${t.number}</span></div>
      <div class="tl-row__meta"><span>${t.grown_ups.map((g) => g.email).join(", ")}</span>
        <span>${t.handset_count} phone${t.handset_count === 1 ? "" : "s"}${t.last_checkin ? html`, last seen ${when(t.last_checkin, tz)}` : ""}</span>
        ${t.erase_after ? html`<span>erased after ${when(t.erase_after, tz)}</span>` : ""}</div></div>
    ${t.yours ? tag("canopy", "Yours") : t.archived_at ? tag("sunbeam", "Paused") : ""}${icon("chevron-right")}</div>`)}</div>`
    : emptyState({ title: q ? "Nothing matches" : state === "archived" ? "No paused treehouses" : "No treehouses yet", body: q ? "Try a name, a four-digit number or a grown-up's full email." : "" });
  const content = html`<h2 class="title-lg">Treehouses</h2>
  ${card({ children: html`<form class="tl-stack tl-stack--group" id="th-search" novalidate>
    ${textField({ id: "th-q", name: "q", label: "Find", value: q, placeholder: "Name, number or a grown-up's email" })}
    <div class="tl-actions">${button({ label: "Find", variant: "primary", type: "submit" })}${button({ label: state === "active" ? "Paused ones" : "Active ones", attrs: { "data-href": state === "active" ? "#/admin/treehouses/archived" : "#/admin/treehouses" } })}</div></form>` })}
  <h2 class="title-md">${state === "archived" ? "Paused" : "Active"}</h2>
  ${rows}
  ${r.capped ? html`<p class="body-sm" style="color:var(--ink-muted)">Only the newest 200 are listed: search to find others.</p>` : ""}
  <p class="body-sm" style="color:var(--ink-muted)">Each look at a family is written in the audit log. Admins never see calls, strings, notes, settings or phone names.</p>`;
  return {
    title: "Treehouses", back: "#/admin", nav: null, template: "settings", noDoodles: true, content,
    mount(root) {
      root.querySelector("#th-search").addEventListener("submit", (e) => {
        e.preventDefault();
        try { sessionStorage.setItem("tl-admin-q", root.querySelector("#th-q").value.trim()); } catch { /* fine */ }
        ctx.render();
      });
    },
  };
}

async function treehousePage(ctx, tid) {
  const t = await get(`/api/admin/treehouses/${tid}`);
  const tz = ctx.me.treehouse?.timezone;
  const facts = html`<dl class="tl-dl">
    <div class="tl-dl__row"><dt>Number</dt><dd class="tl-num">${t.number}</dd></div>
    <div class="tl-dl__row"><dt>Made</dt><dd>${when(t.created_at, tz)}</dd></div>
    <div class="tl-dl__row"><dt>Phones</dt><dd>${t.handset_count}${t.last_checkin ? html`, last seen ${when(t.last_checkin, tz)}` : ""}</dd></div>
    ${t.archived_at ? html`<div class="tl-dl__row"><dt>Paused</dt><dd>${when(t.archived_at, tz)}; erased after ${when(t.erase_after, tz)}</dd></div>` : ""}
  </dl>`;
  const people = html`<div class="tl-card tl-card--list">${t.grown_ups.map((g) => html`<div class="tl-row"><div class="tl-row__main">
    <div class="tl-row__title">${g.email}</div><div class="tl-row__meta"><span>${g.role}</span></div></div>
    ${t.yours ? "" : button({ label: "Remove", size: "sm", attrs: { "data-remove-gu": String(g.id), "data-label": g.email } })}</div>`)}</div>`;
  const phones = t.handsets.length ? html`<div class="tl-card tl-card--list">${t.handsets.map((h) => html`<div class="tl-row"><div class="tl-row__main">
    <div class="tl-row__title">Phone ${h.position}</div><div class="tl-row__meta"><span>${h.kind}</span>${h.last_seen ? html`<span>last seen ${when(h.last_seen, tz)}</span>` : ""}</div></div>
    ${t.yours ? "" : button({ label: "Remove", size: "sm", attrs: { "data-remove-phone": String(h.id), "data-label": `Phone ${h.position}` } })}</div>`)}</div>`
    : emptyState({ title: "No phones", body: "" });
  const pause = t.yours ? alert({ tone: "info", title: "This is your own treehouse", body: "An admin cannot pause or change their own family here." })
    : t.archived_at ? card({ title: "Bring it back",
      children: html`<p class="tl-card__body">Its phones, grown-ups and strings come back as they were. Its phones work again within a minute.</p><div class="tl-actions">${button({ label: "Bring it back", variant: "primary", attrs: "data-restore" })}</div>` })
    : card({ title: "Pause this treehouse",
      children: html`<form class="tl-stack tl-stack--group" id="archive-form" novalidate>
        <p class="tl-card__body">Its phones stop at once (a call in progress ends). Its grown-ups see a "paused" page and can still delete it themselves. Other families see a number nobody has. After 14 days it is erased. The family is not emailed.</p>
        ${selectField({ id: "archive-reason", name: "reason", label: "Why", options: REASON_NAMES, value: "family_asked" })}
        ${textField({ id: "archive-confirm", name: "confirm", label: `Type ${t.name} to confirm` })}
        <div class="tl-actions">${button({ label: "Pause treehouse", variant: "danger", type: "submit" })}</div></form>` });
  const content = html`<h2 class="title-lg">${t.name}</h2>
  ${card({ children: facts })}
  <div data-confirm hidden></div>
  <div data-stepup hidden></div>
  <h2 class="title-md">Grown-ups</h2>${people}
  <h2 class="title-md">Phones</h2>${phones}
  ${pause}`;
  const refresh = () => ctx.render();
  return {
    title: t.name, back: t.archived_at ? "#/admin/treehouses/archived" : "#/admin/treehouses", nav: null, template: "settings", noDoodles: true, content,
    mount(root) {
      const run = async (fn, done) => {
        try { const r = await act(ctx, root, fn); if (r) { toast(done, "success"); refresh(); } } catch (err) { toast(err.message, "warning"); }
      };
      root.querySelector("#archive-form")?.addEventListener("submit", (e) => {
        e.preventDefault();
        const f = e.currentTarget;
        run(() => post(`/api/admin/treehouses/${t.id}/archive`, { reason: f.querySelector("#archive-reason").value, confirm: f.querySelector("#archive-confirm").value }),
          `${t.name} is paused`);
      });
      root.querySelector("[data-restore]")?.addEventListener("click", () => run(() => post(`/api/admin/treehouses/${t.id}/restore`), `${t.name} is back`));
      const confirmRemove = (what, path, note) => {
        const box = root.querySelector("[data-confirm]");
        fill(box, card({ title: `Remove ${what}?`, body: note,
          children: html`<div class="tl-stack tl-stack--group">${selectField({ id: "remove-reason", name: "reason", label: "Why", options: REASON_NAMES, value: "family_asked" })}
          <div class="tl-actions">${button({ label: "Keep", size: "sm", attrs: "data-keep" })}${button({ label: "Remove", variant: "danger", size: "sm", attrs: "data-yes" })}</div></div>` }));
        box.querySelector("[data-keep]").addEventListener("click", () => fill(box, ""));
        box.querySelector("[data-yes]").addEventListener("click", () => run(() => post(path, { reason: box.querySelector("#remove-reason").value }), `${what} was removed`));
        box.scrollIntoView({ block: "nearest" });
      };
      root.querySelectorAll("[data-remove-gu]").forEach((b) => b.addEventListener("click", () =>
        confirmRemove(b.dataset.label, `/api/admin/treehouses/${t.id}/grown-ups/${Number(b.dataset.removeGu)}/remove`,
          "Their sign-ins end at once. The last parent cannot be removed (pause the treehouse instead). The family is not emailed.")));
      root.querySelectorAll("[data-remove-phone]").forEach((b) => b.addEventListener("click", () =>
        confirmRemove(b.dataset.label, `/api/admin/treehouses/${t.id}/handsets/${Number(b.dataset.removePhone)}/remove`,
          "It stops at once (a call in progress ends) and has to be added again by a parent to come back. The family is not emailed.")));
    },
  };
}

async function adminsPage(ctx) {
  const { admins } = await get("/api/admin/admins");
  const content = html`<h2 class="title-lg">Admins</h2>
  <div class="tl-card tl-card--list">${admins.map((a) => html`<div class="tl-row" data-admin="${a.email}"><div class="tl-row__main"><div class="tl-row__title">${a.email}</div>
    <div class="tl-row__meta"><span>Added ${when(a.created_at)}</span><span>by ${a.added_by}</span></div></div>
    ${admins.length > 1 ? button({ label: "Remove", size: "sm", attrs: { "data-remove": a.email } }) : ""}</div>`)}</div>
  <div data-confirm hidden></div>
  ${card({ title: "Add an admin", children: html`<form class="tl-stack tl-stack--group" id="add-admin" novalidate>
    ${textField({ id: "admin-email", name: "email", type: "email", label: "Their email", hint: "The address they sign in to Treeline with. An admin can read the machine's logs and manage releases and admins; never a family's calls or settings." })}
    <div class="tl-actions">${button({ label: "Add admin", variant: "primary", type: "submit" })}</div></form>` })}
  <div data-stepup hidden></div>
  <p class="body-sm" style="color:var(--ink-muted)">Adding or removing an admin asks you to sign in with Google again first. The last admin cannot be removed; on the machine, <code>sudo treeline-admin</code> always works.</p>`;
  return {
    title: "Admins", back: "#/admin", nav: null, template: "settings", noDoodles: true, content,
    mount(root) {
      root.querySelector("#add-admin").addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = root.querySelector("#admin-email").value.trim();
        try {
          const r = await act(ctx, root, () => post("/api/admin/admins", { email }));
          if (r) { toast(`${email} is an admin`, "success"); ctx.render(); }
        } catch (err) { toast(err.message, "warning"); }
      });
      root.querySelectorAll("[data-remove]").forEach((b) => b.addEventListener("click", () => {
        const email = b.dataset.remove;
        const box = root.querySelector("[data-confirm]");
        fill(box, alert({ tone: "warning", title: `Remove ${email} as an admin?`, body: "They keep their treehouse and their sign-in; only the admin page goes.",
          actions: html`${button({ label: "Keep", size: "sm", attrs: "data-keep" })}${button({ label: "Remove", size: "sm", attrs: "data-yes" })}` }));
        box.querySelector("[data-keep]").addEventListener("click", () => fill(box, ""));
        box.querySelector("[data-yes]").addEventListener("click", async () => {
          try {
            const r = await act(ctx, root, () => post("/api/admin/admins/remove", { email }));
            if (r) { toast(`${email} is no longer an admin`, "success"); ctx.render(); }
          } catch (err) { toast(err.message, "warning"); }
        });
      }));
    },
  };
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
  if (page === "stepup.ok" || page === "stepup.failed") {          // back from Google
    let back = "#/admin";
    try { back = sessionStorage.getItem("tl-stepup-return") || back; sessionStorage.removeItem("tl-stepup-return"); } catch { /* fine */ }
    toast(page === "stepup.ok" ? "Confirmed. Do it again now (for 15 minutes you won't be asked)." : "That didn't confirm it was you. Try again.",
      page === "stepup.ok" ? "success" : "warning");
    return { redirect: /^#\/admin(\/[a-z]+)?$/.test(back) ? back : "#/admin" };
  }
  return guarded(ctx, () => {
    if (!page) return overview();
    if (page === "logs") return logsPage();
    if (page === "treehouses") return treehousesPage(ctx, arg === "archived" ? "archived" : "active");
    if (page === "treehouse" && /^\d+$/.test(arg || "")) return treehousePage(ctx, Number(arg));
    if (page === "releases") return releasesPage(ctx);
    if (page === "admins") return adminsPage(ctx);
    if (page === "audit") return auditPage(ctx, /^\d+$/.test(arg || "") ? arg : null);
    return { redirect: "#/admin" };
  });
}
