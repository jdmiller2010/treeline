import { api, post, token } from "/shared/api.js";
import { alert, art, button, card, codeInput, codeValue, html, icon, raw, setBusy, textField, NO_911 } from "/shared/ui.js";

const GOOGLE_MESSAGES = {
  need_code: "That Google account isn't set up yet. If you're new, enter your beta code below, then continue with Google. If a parent added you, ask them to add the email you use with Google.",
  denied: "Google didn't finish signing you in. Try again when you're ready.",
  expired: "That sign-in took too long. Please try again.",
  unverified: "Google says that email address isn't verified, so Treeline can't use it. Verify it with Google, or use another account.",
  token: "Google's answer didn't check out, so you weren't signed in. Please try again.",
  exchange: "Treeline couldn't finish talking to Google. Please try again in a moment.",
};

/** Sign in with Google (production), plus the emailed six-digit code where the server still offers it (development). */
export async function signIn(ctx) {
  let cfg = { google: false, email_code: true };
  try { cfg = await api("GET", "/api/auth/config", undefined, { auth: "none" }); } catch { /* an old server: the emailed code */ }
  // Back from Google: #/signin/x.<one-time word> (a session) or #/signin/e.<reason> (a message). Never a token in the address.
  const back = location.hash.match(/^#\/signin\/([xe])\.([\w-]+)$/) || [];
  let googleNote = "";
  if (back[1] === "e") googleNote = GOOGLE_MESSAGES[back[2]] || "Sign-in didn't finish. Please try again.";
  if (back[1] === "x") {
    history.replaceState(null, "", "#/signin");
    try {
      const r = await post("/api/auth/exchange", { code: back[2] }, { auth: "none" });
      token.set(r.token);
      ctx.me = null;
      let next = "#/home";
      try { next = sessionStorage.getItem("tl-next") || next; sessionStorage.removeItem("tl-next"); } catch { /* fine */ }
      ctx.go(next);
      return { bare: true, title: "Signing in", content: html`<p class="body">Signing you in...</p>`, mount() {} };
    } catch (err) { googleNote = err.message; }
  }
  const googleBox = cfg.google ? html`
      <div class="tl-stack tl-stack--group" id="google-box">
        ${googleNote ? alert({ tone: "danger", title: googleNote }) : ""}
        <div class="tl-actions">${button({ label: "Continue with Google", variant: "primary", attrs: { "data-google": "" } })}</div>
        <details id="new-here">
          <summary class="body">I'm new and have a beta code</summary>
          <form class="tl-stack tl-stack--group" id="step-beta" novalidate>
            ${textField({ id: "beta", label: "Beta code", placeholder: "ABCD-2345", autocomplete: "off", hint: "Eight letters and numbers, from whoever invited you." })}
            <div id="beta-error"></div>
            <div class="tl-actions">${button({ label: "Continue with Google", type: "submit" })}</div>
          </form>
        </details>
      </div>` : "";
  const emailForms = cfg.email_code ? html`
      <form class="tl-stack tl-stack--group" id="step-email" novalidate>
        ${textField({ id: "email", label: "Your email", type: "email", placeholder: "you@example.com", autocomplete: "email", iconName: "users" })}
        <div id="email-error"></div>
        <div class="tl-actions">${button({ label: "Send code", variant: "primary", type: "submit", full: false })}</div>
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
  const lead = cfg.google ? "Use your Google account. There's no password to remember." : "Use your email. We'll send a six-digit code, so there's no password to remember.";

  const content = html`
  <div class="tl-stack tl-stack--related">
    <img src="/ui/logo/treeline-lockup.svg" width="220" height="auto" alt="Treeline" style="max-width:100%;height:auto">
    <p class="tl-tagline">Safe calls for neighborhood kids</p>
  </div>
  <section class="tl-card">
    <div class="tl-stack tl-stack--group">
      <div class="tl-stack tl-stack--related" style="align-items:center;text-align:center">
        <div style="width:min(240px,100%)">${art("treeline")}</div>
        <h1 class="display-md">Sign in</h1>
        <p class="body tl-measure" style="color:var(--ink-muted)">${lead}</p>
      </div>
      ${googleBox}
      ${emailForms}
    </div>
  </section>
  <p class="caption"><a class="tl-footer__link" href="/phone/" data-to-phone>Set this device up as a phone instead</a></p>
  <p class="caption" style="color:var(--ink-muted)">${NO_911}</p>`;

  return {
    bare: true, title: "Sign in", content,
    mount(root) {
      const showError = (sel, msg) => { root.querySelector(sel).innerHTML = msg ? String(alert({ tone: "danger", title: msg })) : ""; };
      const toGoogle = (gate) => { location.assign("/api/auth/google/start" + (gate ? `?gate=${encodeURIComponent(gate)}` : "")); };
      root.querySelector("[data-google]")?.addEventListener("click", () => toGoogle(""));
      root.querySelector("#step-beta")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = e.submitter || e.target.querySelector("button[type=submit]");
        showError("#beta-error", "");
        setBusy(btn, true, "Checking");
        try {
          const r = await post("/api/auth/beta", { code: root.querySelector("#beta").value }, { auth: "none" });
          toGoogle(r.gate);
        } catch (err) { showError("#beta-error", err.message); setBusy(btn, false); }
      });
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
          token.set(r.token);
          ctx.me = null;
          let next = "#/home";
          try { next = sessionStorage.getItem("tl-next") || next; sessionStorage.removeItem("tl-next"); } catch { /* fine */ }
          ctx.go(next);
        } catch (err) { showError("#code-error", err.message); setBusy(btn, false); }
      });
    },
  };
}
