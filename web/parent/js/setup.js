// First-run setup, two short steps: name your treehouse, then the 911 notice and consent. A first phone and a first string are
// suggested on Home afterwards. Nothing is created until "Create my treehouse", so leaving before then leaves nothing behind.
import { post } from "/shared/api.js";
import { alert, button, checkRow, html, setBusy, steps, textField, NO_911, str } from "/shared/ui.js";
import { policyLinks, privacyAccordion } from "./privacy-content.js";

const NAMES = ["Your treehouse", "No 911"];

/** The device's own time zone. Quiet hours follow it; a parent can change it later under Quiet hours. */
function deviceZone() {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Los_Angeles"; } catch { return "America/Los_Angeles"; }
}

export async function setup(ctx) {
  const state = { step: 1, name: "", yourName: "" };

  const content = html`
  <div class="tl-stack tl-stack--related"><img src="/ui/logo/treeline-lockup.svg" width="220" alt="Treeline" style="max-width:100%;height:auto"></div>
  <div id="setup-body" class="tl-stack tl-stack--sections"></div>`;

  return {
    bare: true, title: "Set up your treehouse", content,
    mount(root) {
      const body = root.querySelector("#setup-body");

      const redraw = () => window.TLDoodles?.scatter(root.closest("main") || root.querySelector("main") || document.getElementById("main"), "setup" + state.step);
      new MutationObserver(() => requestAnimationFrame(redraw)).observe(body, { childList: true });
      const stepper = () => steps(NAMES, state.step, "Setting up your treehouse", true);
      const error = (msg) => body.querySelector("[data-error]").innerHTML = msg ? str(alert({ tone: "danger", title: msg })) : "";

      function step1() {
        body.innerHTML = str(html`${stepper()}
        <section class="tl-stack">
          <h1 class="display-md">Name your treehouse</h1>
          <p class="caption" data-setting-up-as>Signed in as <strong>${ctx.me?.email || ""}</strong> · Not you? <a class="tl-footer__link" href="#/signin" data-not-me>Sign out</a></p>
        </section>
        <section class="tl-card" data-scene="sprout"><form class="tl-stack tl-stack--group" novalidate>
          ${textField({ id: "th-name", label: "Treehouse name", placeholder: "Bennett house", value: state.name, hint: "Friends see this name." })}
          ${textField({ id: "th-you", label: "Your first name", value: state.yourName, placeholder: "Jordan" })}
          <div data-error></div>
          <div class="tl-actions">${button({ label: "Continue", variant: "primary", type: "submit" })}</div>
        </form></section>`);
        body.querySelector("#th-name").focus();
        // Whose account this treehouse will belong to, in plain sight: someone signed in as the wrong person must notice here (R6-1).
        body.querySelector("[data-not-me]")?.addEventListener("click", (e) => { e.preventDefault(); ctx.signOut(); });
        body.querySelector("form").addEventListener("submit", (e) => {
          e.preventDefault();
          state.name = body.querySelector("#th-name").value.trim();
          state.yourName = body.querySelector("#th-you").value.trim();
          if (!state.name) return error("Add a name for your treehouse.");
          state.step = 2; step2();
        });
      }

      function step2() {
        body.innerHTML = str(html`${stepper()}
        <section class="tl-stack">
          <h1 class="display-md">Treeline can't call 911</h1>
          <p class="body tl-measure">${NO_911}</p>
        </section>
        <section class="tl-card"><form class="tl-stack tl-stack--group" novalidate>
          <h2 class="tl-card__title">Your family's information</h2>
          ${privacyAccordion()}
          <div class="tl-stack tl-stack--tight">
            ${checkRow({ id: "ack", label: "I understand Treeline can't call 911" })}
            ${checkRow({ id: "consent", label: "I'm a parent or guardian, I've read this, and I agree to Treeline's terms and policies" })}
          </div>
          <p class="caption">The full ${policyLinks()} say the same things in more detail. Each opens in a new tab.</p>
          <div data-error></div>
          <div class="tl-actions">
            ${button({ label: "Back", attrs: "data-back" })}
            ${button({ label: "Create my treehouse", variant: "primary", type: "submit", disabled: true })}
          </div>
        </form></section>`);
        const form = body.querySelector("form"), submit = form.querySelector("[type=submit]");
        const ready = () => { submit.disabled = !(form.querySelector("#ack").checked && form.querySelector("#consent").checked); };
        form.querySelector("#ack").addEventListener("change", ready);
        form.querySelector("#consent").addEventListener("change", ready);
        form.querySelector("[data-back]").addEventListener("click", () => { state.step = 1; step1(); });
        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          setBusy(submit, true, "Creating");
          try {
            ctx.me = await post("/api/treehouse", { name: state.name, your_name: state.yourName, timezone: deviceZone(), ack_911: true, consent: true });
            ctx.go("#/home");
          } catch (err) { error(err.message); setBusy(submit, false); }
        });
      }

      step1();
    },
  };
}

/** A grown-up who hasn't agreed to the current terms and policies: someone a parent added (a co-parent or a sitter), or anyone after
 *  the documents changed. Shown before anything else, like setup's last step; agreeing is recorded in the family's own file. */
export async function agree(ctx) {
  const th = ctx.me.treehouse;
  const content = html`
  <div class="tl-stack tl-stack--related"><img src="/ui/logo/treeline-lockup.svg" width="220" alt="Treeline" style="max-width:100%;height:auto"></div>
  <section class="tl-stack">
    <h1 class="display-md">Treeline can't call 911</h1>
    <p class="body tl-measure">${NO_911}</p>
    <p class="caption">Before you use ${th.name}'s treehouse, please read how Treeline works and agree to its terms. Signed in as <strong>${ctx.me.email}</strong> · Not you? <a class="tl-footer__link" href="#/signin" data-not-me>Sign out</a></p>
  </section>
  <section class="tl-card"><form class="tl-stack tl-stack--group" novalidate>
    <h2 class="tl-card__title">Your family's information</h2>
    ${privacyAccordion()}
    <div class="tl-stack tl-stack--tight">
      ${checkRow({ id: "ack", label: "I understand Treeline can't call 911" })}
      ${checkRow({ id: "consent", label: "I've read this, and I agree to Treeline's terms and policies" })}
    </div>
    <p class="caption">The full ${policyLinks()} say the same things in more detail. Each opens in a new tab.</p>
    <div data-error></div>
    <div class="tl-actions">${button({ label: "Agree and continue", variant: "primary", type: "submit", disabled: true })}</div>
  </form></section>`;
  return {
    bare: true, title: "Before you start", content,
    mount(root) {
      const form = root.querySelector("form"), submit = form.querySelector("[type=submit]");
      const ready = () => { submit.disabled = !(form.querySelector("#ack").checked && form.querySelector("#consent").checked); };
      form.querySelector("#ack").addEventListener("change", ready);
      form.querySelector("#consent").addEventListener("change", ready);
      root.querySelector("[data-not-me]").addEventListener("click", (e) => { e.preventDefault(); ctx.signOut(); });
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        setBusy(submit, true, "Saving");
        try {
          ctx.me = await post("/api/agreement", { ack_911: true, consent: true });
          // Back to where they were going: a string or pairing link (or the page saved at sign-in) opens now, it isn't lost.
          const here = location.hash;
          ctx.go(here && !here.startsWith("#/signin") ? here : "#/home");
        } catch (err) {
          form.querySelector("[data-error]").innerHTML = str(alert({ tone: "danger", title: err.message }));
          setBusy(submit, false);
        }
      });
    },
  };
}
