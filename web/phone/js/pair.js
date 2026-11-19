// The screen a softphone shows until a parent adds it to a treehouse: a QR code and six digits.
import { alert, art, footer, html, raw, str } from "/shared/ui.js";
import { mountInstall, mountInstallPage } from "/shared/install.js";
import { chooseBrowser, isMobileOrTablet, showInstallPage } from "/shared/pwa.js";
import { get, post } from "/shared/api.js";

export function savedPhone() {
  try { return JSON.parse(localStorage.getItem("treeline.phone")); } catch { return null; }
}
export function savePhone(c) { try { localStorage.setItem("treeline.phone", JSON.stringify(c)); } catch { /* private window */ } }
export function forgetPhone() { try { localStorage.removeItem("treeline.phone"); } catch { /* ignore */ } }

function qrSvg(text) {
  const q = window.qrcode(0, "M");
  q.addData(text);
  q.make();
  // currentColor follows the theme, so the code stays readable in Lantern.
  return q.createSvgTag({ cellSize: 4, margin: 0, scalable: true }).replace(/fill="black"/g, 'fill="currentColor"').replace(/fill="white"/g, 'fill="none"');
}

/** Show the pairing screen. Resolves with the saved credentials once a parent approves. */
export function pairScreen(root, notice) {
  return new Promise((resolve) => {
    let stopped = false, timer = null;
    // The notice ("you're signed out…") is a one-time message: it goes away by itself after a few minutes and is not drawn again.
    let note = notice;
    if (note) setTimeout(() => { note = null; root.querySelector("[data-alert='notice']")?.remove(); }, 3 * 60 * 1000);
    async function newCode() {
      if (showInstallPage()) { installPage(); return; }          // nothing to pair until they choose the browser
      let start;
      try { start = await post("/api/pair/start", {}, { auth: "none" }); }
      catch (e) { show(null, e.message); timer = setTimeout(newCode, 5000); return; }
      show(start);
      const until = new Date(start.expires_at).getTime();
      const poll = async () => {
        if (stopped) return;
        try {
          const r = await get(`/api/pair/status?token=${encodeURIComponent(start.token)}`, { auth: "none" });
          if (r.status === "paired") {
            stopped = true;
            const phone = { sip_user: r.sip_user, secret: r.secret, server: r.server, ws_url: r.ws_url, realm: r.realm };
            savePhone(phone);
            return resolve(phone);
          }
        } catch { /* try again */ }
        if (Date.now() > until - 15000) return newCode();    // a fresh code before this one runs out
        timer = setTimeout(poll, 2000);
      };
      timer = setTimeout(poll, 2000);
    }

    // A phone or tablet in a browser tab is asked to install the app first; a computer goes straight to adding a phone or logging in.
    function installPage() {
      root.innerHTML = str(html`<main class="ph-pair"><div class="tl-stack tl-stack--sections" style="max-width:var(--sheet-max);width:100%">
        <div class="tl-stack tl-stack--related"><img src="/ui/logo/treeline-lockup.svg" width="200" alt="Treeline" style="max-width:100%;height:auto"></div>
        <section class="tl-stack">
          <div style="max-width:220px">${art("treehouse")}</div>
          <h1 class="display-md">Install Treeline</h1>
          <p class="body" style="color:var(--ink-muted)">Treeline works best as an app. Install it to ring for calls, send alerts and open right from your Home Screen.</p>
        </section>
        ${note ? alert({ tone: "info", title: note, id: "notice" }) : ""}
        <div id="install-page"></div>
        <p class="caption" style="color:var(--ink-muted)">Treeline can't call 911 or any outside number.</p>
        ${footer("/phone/licenses.html")}
      </div></main>`);
      mountInstallPage(root.querySelector("#install-page"), { onBrowser: () => { chooseBrowser(); newCode(); } });
    }

    function show(start, error) {
      if (showInstallPage()) return installPage();
      const url = start ? `${start.origin || location.origin}/parent/#/pair/${start.code}` : "";   // the server knows the secure address
      root.innerHTML = str(html`<main class="ph-pair"><div class="tl-stack tl-stack--sections" style="max-width:var(--sheet-max);width:100%">
        <div class="tl-stack tl-stack--related"><img src="/ui/logo/treeline-lockup.svg" width="200" alt="Treeline" style="max-width:100%;height:auto"></div>
        <section class="tl-stack">
          <h1 class="display-md">Welcome to Treeline</h1>
          <p class="body" style="color:var(--ink-muted)">Safe calls for neighborhood kids, with parents holding the keys. Use this device as one of your treehouse's phones, or log in to manage the treehouse.</p>
        </section>
        ${note ? alert({ tone: "info", title: note, id: "notice" }) : ""}
        ${error ? alert({ tone: "danger", title: error }) : ""}
        <section class="tl-card" aria-labelledby="pair-title"><div class="tl-stack tl-stack--group">
          <div class="tl-stack tl-stack--tight">
            <h2 class="tl-card__title" id="pair-title">Use this device as a phone</h2>
            <p class="tl-card__body">On a parent's phone, open Treeline, then Home, then Add a phone. Scan this code, or choose Softphone (app) and type the six digits.</p>
          </div>
          ${start ? html`<div class="tl-stack tl-stack--group" style="align-items:center;text-align:center">
            <div class="ph-qr" role="img" aria-label="QR code for ${start.code}" style="color:var(--ink)">${raw(qrSvg(url))}</div>
            <p class="ph-code" aria-label="Code ${start.code.split("").join(" ")}">${start.code.slice(0, 3)} ${start.code.slice(3)}</p>
            <p class="tl-card__body">Waiting for a parent. This code changes every few minutes.</p>
          </div>` : html`<p class="tl-card__body">Getting a code…</p>`}
        </div></section>
        <section class="tl-card" aria-labelledby="login-title"><div class="tl-stack tl-stack--group">
          <div class="tl-stack tl-stack--tight">
            <h2 class="tl-card__title" id="login-title">Parents</h2>
            <p class="tl-card__body">Log in to the parent dashboard to add phones, approve strings and set quiet hours.</p>
          </div>
          <div class="tl-actions"><a class="tl-btn tl-btn--primary tl-btn--md" href="/parent/" data-parent-login><span class="tl-btn__label">Log in to the parent dashboard</span></a></div>
        </div></section>
        <div id="install-slot"></div>
        <p class="caption" style="color:var(--ink-muted)">Treeline can't call 911 or any outside number.</p>
        ${footer("/phone/licenses.html")}
      </div></main>`);
      if (!isMobileOrTablet()) mountInstall(root.querySelector("#install-slot"));      // a phone or tablet that chose the browser was already asked
    }
    newCode();
  });
}
