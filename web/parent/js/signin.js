// The front door: what Treeline is (three small pictures), Sign in with Google, and setting a device up as a phone.
// A new person signs in with Google first and is then asked for the beta code; nothing about them is saved until it is accepted.
import { api, get, post, token } from "/shared/api.js";
import { alert, art, button, codeInput, codeValue, googleButton, html, raw, setBusy, str, tag, textField, welcome, NO_911 } from "/shared/ui.js";
import { formDialog } from "./dialogs.js";
import { savePhone } from "/phone/js/pair.js";

const GOOGLE_MESSAGES = {
  need_code: "Treeline is invite only. Sign in, then enter your invite code.",
  denied: "Google didn't finish signing you in. Try again when you're ready.",
  expired: "That sign-in took too long. Please try again.",
  unverified: "Google says that email address isn't verified, so Treeline can't use it. Verify it with Google, or use another account.",
  token: "Google's answer didn't check out, so you weren't signed in. Please try again.",
  exchange: "Treeline couldn't finish talking to Google. Please try again in a moment.",
};

const logo = html`<img src="/ui/logo/treeline-lockup.svg" width="220" height="auto" alt="Treeline" style="max-width:100%;height:auto">`;

function finishSignIn(ctx, t) {
  token.set(t);
  ctx.me = null;
  let next = "#/home";
  try { next = sessionStorage.getItem("tl-next") || next; sessionStorage.removeItem("tl-next"); } catch { /* fine */ }
  ctx.go(next);
}

/** Sign in with Google (production), plus the emailed six-digit code where the server still offers it (development). */
export async function signIn(ctx) {
  let cfg = { google: false, email_code: true };
  try { cfg = await api("GET", "/api/auth/config", undefined, { auth: "none" }); } catch { /* an old server: the emailed code */ }
  // Back from Google: #/signin/x.<word> (a session), #/signin/p.<word> (a new person, asked for the beta code next) or
  // #/signin/e.<reason> (a message). Never a token in the address.
  const back = location.hash.match(/^#\/signin\/([xpe])\.([\w-]+)$/) || [];
  let googleNote = "";
  if (back[1] === "e") googleNote = GOOGLE_MESSAGES[back[2]] || "Sign-in didn't finish. Please try again.";
  if (back[1] === "x") {
    history.replaceState(null, "", "#/signin");
    try {
      const r = await post("/api/auth/exchange", { code: back[2] }, { auth: "none" });
      finishSignIn(ctx, r.token);
      return { bare: true, title: "Signing in", content: html`<p class="body">Signing you in...</p>`, mount() {} };
    } catch (err) { googleNote = err.message; }
  }
  if (back[1] === "p") {
    try {
      const { email } = await post("/api/auth/pending", { pending: back[2] }, { auth: "none" });
      return betaChallenge(ctx, back[2], email);
    } catch (err) { history.replaceState(null, "", "#/signin"); googleNote = err.message; }
  }

  const emailForms = cfg.email_code ? html`
      <form class="tl-stack tl-stack--group" id="step-email" novalidate>
        ${textField({ id: "email", label: "Your email", type: "email", placeholder: "you@example.com", autocomplete: "email", iconName: "users" })}
        <div id="email-error"></div>
        <div class="tl-actions">${button({ label: "Send code", variant: cfg.google ? "secondary" : "primary", type: "submit", full: false })}</div>
      </form>
      <form class="tl-stack tl-stack--group" id="step-code" novalidate hidden>
        <p class="tl-card__body" id="sent-note"></p>
        <div id="dev-note"></div>
        ${codeInput({ legend: "Sign-in code", hint: "Six digits from the email." })}
        <div id="code-error"></div>
        <div class="tl-actions">
          ${button({ label: "Use a different email", attrs: "data-back-to-email" })}
          ${button({ label: "Sign in", variant: "primary", type: "submit" })}
        </div>
      </form>` : "";

  const content = html`<div class="tl-front">
  <div class="tl-front__head">
    <img src="/ui/logo/treeline-lockup.svg" alt="Treeline">
    <h1 class="display-md">Safe, simple calls.</h1>
  </div>
  <div class="tl-welcome-wrap">${welcome([
    { art: art("treehouse"), title: "Your treehouse", body: "Your home gets its own number. Every phone in the house rings together." },
    { art: art("connection"), title: "A string to another treehouse", body: "Both parents say yes before kids can call." },
    { art: html`<img src="/ui/illustrations/rotary/rotary-phone-moss-lifted.svg" alt="">`, title: "Kids pick up and dial", body: "On a rotary phone, only to friends you've approved." },
    { art: html`<svg viewBox="30 60 340 200"><image href="/ui/illustrations/rotary/rotary-part-3-handset.svg" x="0" y="-70" width="400" height="510"/></svg>`, title: "Just a phone call", body: "No texts, no voicemail, no caller ID, no group calls. Never recorded." },
  ])}</div>
  <section class="tl-card tl-login" aria-labelledby="signin-title">
    <div class="tl-login__head"><h2 class="tl-card__title" id="signin-title">Log in to Treeline</h2>${tag("sunbeam", "Closed beta")}</div>
    ${googleNote ? alert({ tone: "danger", title: googleNote }) : ""}
    <div class="tl-actions">
      ${cfg.google ? googleButton({ attrs: { "data-google": "" } }) : ""}
      ${button({ label: "Use as a phone", icon: "phone", attrs: { "data-phone-setup": "", title: "Use this device as a phone" } })}
    </div>
    ${emailForms}
    <p class="tl-login__911">${NO_911}</p>
  </section>
  </div>`;

  return {
    bare: true, title: "Sign in", content,
    mount(root) {
      const showError = (sel, msg) => { root.querySelector(sel).innerHTML = msg ? String(alert({ tone: "danger", title: msg })) : ""; };
      root.querySelector("[data-google]")?.addEventListener("click", () => location.assign("/api/auth/google/start"));
      root.querySelector("[data-phone-setup]").addEventListener("click", (e) => { e.preventDefault(); phoneSetup(); });
      const emailCard = root.querySelector("#step-email");
      if (!emailCard) return;
      const codeCard = root.querySelector("#step-code");
      const emailInput = root.querySelector("#email");
      let email = "";
      if (!cfg.google) emailInput.focus();

      emailCard.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = e.submitter || emailCard.querySelector("button[type=submit]");
        email = emailInput.value.trim();
        showError("#email-error", "");
        setBusy(btn, true, "Sending");
        try {
          const r = await post("/api/auth/request", { email }, { auth: "none" });
          root.querySelector("#sent-note").textContent = `We sent a code to ${email}. It works for 10 minutes.`;
          if (r.dev_code) root.querySelector("#dev-note").innerHTML = String(alert({ tone: "info", title: "Development mode", body: `Your code is ${r.dev_code}. This only shows on a test server.` }));
          emailCard.hidden = true; codeCard.hidden = false;
          codeCard.querySelector(".tl-code__box").focus();
        } catch (err) { showError("#email-error", err.message); }
        setBusy(btn, false);
      });

      codeCard.querySelector("[data-back-to-email]").addEventListener("click", () => {
        codeCard.hidden = true; emailCard.hidden = false; emailInput.focus();
      });
      codeCard.addEventListener("submit", async (e) => {
        e.preventDefault();
        const code = codeValue(codeCard);
        showError("#code-error", "");
        if (code.length !== 6) return showError("#code-error", "Enter all six digits.");
        const btn = codeCard.querySelector("button[type=submit]");
        setBusy(btn, true, "Signing in");
        try {
          const r = await post("/api/auth/verify", { email, code }, { auth: "none" });
          finishSignIn(ctx, r.token);
        } catch (err) { showError("#code-error", err.message); setBusy(btn, false); }
      });
    },
  };
}

/** The beta access challenge: signed in with Google, not yet let in. A wrong code turns the box red and the sign-in keeps waiting. */
function betaChallenge(ctx, pending, email) {
  const content = html`
  <div class="tl-stack tl-stack--related">${logo}</div>
  <section class="tl-stack">
    <h1 class="display-md">Enter your invite code</h1>
    <p class="body tl-measure" style="color:var(--ink-muted)">From whoever invited you.</p>
  </section>
  <section class="tl-card"><form class="tl-stack tl-stack--group" id="beta-form" novalidate>
    <p class="caption" data-signed-in-as>Signed in as <strong>${email}</strong> · <a class="tl-footer__link" href="#/signin" data-other-account>Use a different account</a></p>
    <div data-field>${textField({ id: "beta", label: "Invite code", placeholder: "ABCD-2345", autocomplete: "off" })}</div>
    <div class="tl-actions">${button({ label: "Continue", variant: "primary", type: "submit" })}</div>
  </form></section>
  <p class="caption" style="color:var(--ink-muted)">${NO_911}</p>`;
  return {
    bare: true, title: "Enter your invite code", content,
    mount(root) {
      const form = root.querySelector("#beta-form"), slot = form.querySelector("[data-field]");
      const field = (error, value = "") => {
        slot.innerHTML = str(textField({ id: "beta", label: "Invite code", placeholder: "ABCD-2345", autocomplete: "off", value, error }));
        const input = slot.querySelector("#beta");
        input.focus();
        if (error) input.select();
        input.addEventListener("input", () => { if (slot.querySelector(".has-error")) field("", input.value); }, { once: true });
      };
      root.querySelector("#beta").focus();
      root.querySelector("[data-other-account]").addEventListener("click", (e) => { e.preventDefault(); history.replaceState(null, "", "#/signin"); ctx.render(); });
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = form.querySelector("button[type=submit]"), value = slot.querySelector("#beta").value;
        setBusy(btn, true, "Checking");
        try {
          const r = await post("/api/auth/beta", { pending, code: value }, { auth: "none" });
          history.replaceState(null, "", "#/signin");
          finishSignIn(ctx, r.token);
        } catch (err) {
          setBusy(btn, false);
          if (err.code === "expired_signin") { history.replaceState(null, "", "#/signin/e.expired"); ctx.render(); return; }
          field(err.message, value);
        }
      });
    },
  };
}

/**
 * Set this device up as a phone: a sheet with a QR code that a parent's phone, signed in to Treeline, scans to add it. When the
 * parent says yes, this device becomes the softphone.
 */
async function phoneSetup() {
  let stopped = false, timer = null;
  const body = html`<div class="tl-stack tl-stack--group" style="align-items:center;text-align:center" data-pair>
    <p class="tl-card__body">Getting a code…</p></div>
    <p class="tl-sheet__body">Scan with a parent's phone that's signed in to Treeline.</p>`;
  await formDialog({
    title: "Set up this phone", body, submit: null, cancel: "Cancel", autofocus: false,
    onSubmit: async () => true,
    onOpen(scrim) {
      const slot = scrim.querySelector("[data-pair]");
      const show = (start) => {
        const url = `${start.origin || location.origin}/parent/#/pair/${start.code}`;
        slot.innerHTML = str(html`<div class="tl-qr" style="width:min(224px,100%)">${raw(window.TLQR.svg(url, { label: `QR code for the phone code ${start.code}` }))}</div>
          <p class="tl-codeshow__code" aria-label="Code ${start.code.split("").join(" ")}">${start.code.slice(0, 3)} ${start.code.slice(3)}</p>
          <p class="tl-card__body">Waiting for a parent…</p>`);
      };
      const begin = async () => {
        if (stopped) return;
        let start;
        try { start = await post("/api/pair/start", {}, { auth: "none" }); }
        catch (e) { slot.innerHTML = str(alert({ tone: "danger", title: e.message })); timer = setTimeout(begin, 5000); return; }
        show(start);
        const until = new Date(start.expires_at).getTime();
        const poll = async () => {
          if (stopped) return;
          try {
            const r = await get(`/api/pair/status?token=${encodeURIComponent(start.token)}`, { auth: "none" });
            if (r.status === "paired") {
              stopped = true;
              savePhone({ sip_user: r.sip_user, secret: r.secret, server: r.server, ws_url: r.ws_url, realm: r.realm });
              location.assign("/phone/");
              return;
            }
          } catch { /* try again */ }
          if (Date.now() > until - 15000) return begin();
          timer = setTimeout(poll, 2000);
        };
        timer = setTimeout(poll, 2000);
      };
      begin();
    },
  });
  stopped = true;
  clearTimeout(timer);
}
