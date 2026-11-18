// The screen a tablet shows until a parent adds it to a treehouse: a QR code and six digits.
import { alert, art, footer, html, raw, str } from "/shared/ui.js";
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
    async function newCode() {
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

    function show(start, error) {
      const url = start ? `${location.origin}/parent/#/pair/${start.code}` : "";
      root.innerHTML = str(html`<main class="ph-pair"><div class="tl-stack tl-stack--sections" style="max-width:var(--sheet-max);width:100%">
        <div class="tl-stack tl-stack--related"><img src="/ui/logo/treeline-lockup.svg" width="200" alt="Treeline" style="max-width:100%;height:auto"></div>
        <section class="tl-stack">
          <div style="max-width:220px">${art("treehouse")}</div>
          <h1 class="display-md">Add this tablet to your treehouse</h1>
          <p class="body" style="color:var(--ink-muted)">On a parent's phone, open Treeline, then Our treehouse, then Add a phone. Scan this code, or choose Tablet and type the six digits.</p>
        </section>
        ${notice ? alert({ tone: "info", title: notice }) : ""}
        ${error ? alert({ tone: "danger", title: error }) : ""}
        ${start ? html`<section class="tl-card"><div class="tl-stack tl-stack--group" style="align-items:center;text-align:center">
          <div class="ph-qr" role="img" aria-label="QR code for ${start.code}" style="color:var(--ink)">${raw(qrSvg(url))}</div>
          <p class="ph-code" aria-label="Code ${start.code.split("").join(" ")}">${start.code.slice(0, 3)} ${start.code.slice(3)}</p>
          <p class="tl-card__body">Waiting for a parent. This code changes every few minutes.</p>
        </div></section>` : ""}
        <p class="caption" style="color:var(--ink-muted)">Treeline can't call 911 or any outside number.</p>
        ${footer("/phone/licenses.html")}
      </div></main>`);
    }
    newCode();
  });
}
