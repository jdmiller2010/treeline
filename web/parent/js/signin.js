import { post, token } from "/shared/api.js";
import { alert, art, button, card, codeInput, codeValue, html, icon, raw, setBusy, textField, NO_911 } from "/shared/ui.js";

/** Sign in with an emailed six-digit code. */
export async function signIn(ctx) {
  const content = html`
  <div class="tl-stack tl-stack--related">
    <img src="/ui/logo/treeline-lockup.svg" width="220" height="auto" alt="Treeline" style="max-width:100%;height:auto">
  </div>
  <section class="tl-stack">
    <div style="max-width:240px">${art("treeline")}</div>
    <h1 class="display-md">Sign in</h1>
    <p class="body tl-measure" style="color:var(--ink-muted)">Use your email. We'll send a six-digit code, so there's no password to remember.</p>
  </section>
  <section class="tl-card" id="step-email">
    <form class="tl-stack tl-stack--group" novalidate>
      ${textField({ id: "email", label: "Your email", type: "email", placeholder: "you@example.com", autocomplete: "email", iconName: "users" })}
      <div id="email-error"></div>
      <div class="tl-actions tl-actions--stack">${button({ label: "Send code", variant: "primary", type: "submit", full: false })}</div>
    </form>
  </section>
  <section class="tl-card" id="step-code" hidden>
    <form class="tl-stack tl-stack--group" novalidate>
      <p class="tl-card__body" id="sent-note"></p>
      <div id="dev-note"></div>
      ${codeInput({ legend: "Sign-in code", hint: "Six digits from the email." })}
      <div id="code-error"></div>
      <div class="tl-actions tl-actions--stack">
        ${button({ label: "Use a different email", variant: "quiet", attrs: "data-back-to-email" })}
        ${button({ label: "Sign in", variant: "primary", type: "submit" })}
      </div>
    </form>
  </section>
  <p class="caption" style="color:var(--ink-muted)">${NO_911}</p>`;

  return {
    bare: true, title: "Sign in", content,
    mount(root) {
      const emailCard = root.querySelector("#step-email");
      const codeCard = root.querySelector("#step-code");
      const emailInput = root.querySelector("#email");
      let email = "";
      const showError = (sel, msg) => { root.querySelector(sel).innerHTML = msg ? String(alert({ tone: "danger", title: msg })) : ""; };
      emailInput.focus();

      emailCard.querySelector("form").addEventListener("submit", async (e) => {
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
      codeCard.querySelector("form").addEventListener("submit", async (e) => {
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
