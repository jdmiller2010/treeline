// First-run setup: your treehouse, the 911 notice, a first phone, a first friend.
import { get, post } from "/shared/api.js";
import { alert, art, button, checkRow, html, raw, selectField, setBusy, steps, textField, NO_911, str, icon } from "/shared/ui.js";
import { KIND, addHandsetDialog } from "./house.js";
import { stringConnect } from "./strings.js";
import { privacyAccordion } from "./privacy-content.js";

const NAMES = ["Your treehouse", "No 911", "First phone", "First string"];
const COMMON_ZONES = [["America/New_York", "Eastern"], ["America/Chicago", "Central"], ["America/Denver", "Mountain"],
  ["America/Phoenix", "Arizona"], ["America/Los_Angeles", "Pacific"], ["America/Anchorage", "Alaska"], ["Pacific/Honolulu", "Hawaii"]];

function zoneOptions() {
  const mine = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const opts = COMMON_ZONES.map(([v, l]) => [v, `${l} (${v.split("/")[1].replace("_", " ")})`]);
  if (mine && !COMMON_ZONES.some(([v]) => v === mine)) opts.unshift([mine, mine.replace("_", " ")]);
  return { opts, mine: mine || "America/Los_Angeles" };
}

export async function setup(ctx) {
  const state = { step: 1, name: "", yourName: "", tz: zoneOptions().mine, house: null };

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
        const { opts } = zoneOptions();
        body.innerHTML = str(html`${stepper()}
        <section class="tl-stack">
          <h1 class="display-md">Name your treehouse</h1>
          <p class="caption" data-setting-up-as>You're setting this up as <strong>${ctx.me?.email || ""}</strong>. Not you? <a class="tl-footer__link" href="#/signin" data-not-me>Sign out</a></p>
          <p class="body tl-measure" style="color:var(--ink-muted)">Families you string with see this name. Treeline gives your treehouse a four-digit number, and friends dial it to reach you.</p>
        </section>
        <section class="tl-card" data-scene="sprout"><form class="tl-stack tl-stack--group" novalidate>
          ${textField({ id: "th-name", label: "Treehouse name", placeholder: "Bennett house", value: state.name, hint: "Most families use the family name." })}
          ${textField({ id: "th-you", label: "Your first name", value: state.yourName, placeholder: "Jordan" })}
          ${selectField({ id: "th-tz", label: "Time zone", options: opts, value: state.tz, hint: "Quiet hours follow this time zone, daylight saving included." })}
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
          state.tz = body.querySelector("#th-tz").value;
          if (!state.name) return error("Add a name for your treehouse.");
          state.step = 2; step2();
        });
      }

      function step2() {
        body.innerHTML = str(html`${stepper()}
        <section class="tl-stack">
          <h1 class="display-md">Treeline can't call 911</h1>
          <p class="body tl-measure">${NO_911}</p>
          <p class="body tl-measure" style="color:var(--ink-muted)">Phones on Treeline only reach treehouses strung to yours. Outside numbers can't call in, either. Make sure your kids know who to ask, and how to reach help, when they need it.</p>
        </section>
        <section class="tl-card"><form class="tl-stack tl-stack--group" novalidate>
          ${checkRow({ id: "ack", label: "I understand Treeline can't call 911 or any outside number" })}
          <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">How Treeline treats your family's information</h2><p class="tl-card__body">Short answers. You can read them again any time under Privacy and safety.</p></div>
          ${privacyAccordion()}
          ${checkRow({ id: "consent", label: "I'm a parent or guardian, and I've read how Treeline handles our information", desc: "You need to tick both boxes to continue." })}
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
            ctx.me = await post("/api/treehouse", { name: state.name, your_name: state.yourName, timezone: state.tz, ack_911: true, consent: true });
            state.house = ctx.me.treehouse; state.step = 3; step3();
          } catch (err) { error(err.message); setBusy(submit, false); }
        });
      }

      function step3() {
        body.innerHTML = str(html`${stepper()}
        <section class="tl-card tl-card--breeze">
          <header class="tl-card__head"><div><p class="tl-card__eyebrow">Your treehouse is ready</p><h2 class="tl-card__title">${state.house.name}</h2></div></header>
          <p class="tl-card__body">Your number is <strong class="tl-num">${state.house.number}</strong>. Friends will dial it.</p>
        </section>
        <section class="tl-stack">
          <h1 class="display-md">Put a phone in your treehouse</h1>
          <p class="body tl-measure" style="color:var(--ink-muted)">Pick the first phone to hang up. You can add more later, and they all ring together.</p>
        </section>
        <section class="tl-stack">
          <div class="tl-card tl-card--list" aria-label="Kinds of phone">
            ${["softphone", "ata", "rotary"].map((k) => html`<div class="tl-row tl-log tl-log--bark">
              <span class="tl-log__icon" aria-hidden="true">${icon("phone")}</span>
              <div class="tl-row__main"><div class="tl-row__title">${KIND[k][0]}</div><p class="tl-card__body" style="margin:0;color:var(--ink-muted)">${KIND[k][1]}</p></div>
            </div>`)}
          </div>
          <div data-error></div>
          <div class="tl-actions">
            ${button({ label: "Skip for now", attrs: "data-skip" })}
            ${button({ label: "Add a phone", variant: "primary", icon: "plus", attrs: "data-add" })}
          </div>
        </section>`);
        body.querySelector("[data-skip]").addEventListener("click", () => { state.step = 4; step4(); });
        body.querySelector("[data-add]").addEventListener("click", async () => { if (await addHandsetDialog(ctx)) { state.step = 4; step4(); } });
      }

      function step4() {
        body.innerHTML = str(html`${stepper()}
        <section class="tl-stack">
          <h1 class="display-md">Stretch a string to a friend</h1>
          <p class="body tl-measure" style="color:var(--ink-muted)">A string is the line between your treehouse and a friend's. Make a string code and send it to a parent you know. When they enter it, you both say yes, and the kids can call each other.</p>
        </section>
        <section class="tl-stack">
          <div class="tl-setup-art" style="width:min(240px,100%);margin-inline:auto;padding-block:var(--space-4)">${art("connection")}</div>
          <div data-error></div>
          <div class="tl-actions">
            ${button({ label: "I'll do this later", attrs: "data-later" })}
            ${button({ label: "New string connection", variant: "primary", icon: "string", attrs: "data-code" })}
          </div>
        </section>`);
        const finish = () => ctx.go("#/home");
        body.querySelector("[data-later]").addEventListener("click", finish);
        body.querySelector("[data-code]").addEventListener("click", async () => { await stringConnect(ctx); finish(); });
      }

      step1();
    },
  };
}
