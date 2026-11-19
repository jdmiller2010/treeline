// Quiet hours, call limits and pause: the Settings form template.
import { get, patch } from "/shared/api.js";
import { alert, checkRow, html, icon, raw, selectField, str, switchRow, timeField, toast } from "/shared/ui.js";
import { DAY_LETTERS, DAY_NAMES, daysSummary, minutesText, time12 } from "/shared/format.js";

const LENGTHS = [5, 10, 15, 20, 30, 45, 60, 90, 120];
const DAILY = [null, 30, 60, 90, 120, 180, 240];

function quietPreview(q) {
  return html`<div class="tl-quiet" id="qh-preview">
  <span class="tl-quiet__icon" aria-hidden="true">${icon("moon")}</span>
  <div class="tl-quiet__main">
    <div class="tl-row__title">Quiet hours</div>
    <div class="tl-quiet__time"><span class="tl-num" data-qh="start">${time12(q.start)}</span><span class="tl-quiet__to">to</span><span class="tl-num" data-qh="end">${time12(q.end)}</span></div>
    <div class="tl-quiet__days" aria-label="Days">${DAY_LETTERS.map((l, i) => html`<span class="tl-day${q.days[i] === "1" ? " is-on" : ""}" data-day="${i}">${l}</span>`)}</div>
  </div>
  <div class="tl-field-row"><button id="qh-enabled" type="button" role="switch" aria-checked="${q.enabled ? "true" : "false"}" aria-label="Quiet hours on" class="tl-switch${q.enabled ? " is-on" : ""}"><span class="tl-switch__thumb">${q.enabled ? icon("check", 12) : ""}</span></button></div>
</div>`;
}

function banner(th) {
  return th.quiet_now && !th.paused ? alert({ tone: "info", title: "Quiet hours are on right now", body: `Calls wait until ${time12(th.quiet.end)}.` }) : "";
}

export async function quiet(ctx) {
  const { treehouse: th } = await get("/api/home");
  ctx.me.treehouse = th;
  const parent = ctx.isParent(), q = th.quiet, dis = parent ? "" : "disabled";
  const lengthOpts = LENGTHS.map((m) => [m, minutesText(m)]);
  if (!LENGTHS.includes(th.max_call_minutes)) lengthOpts.push([th.max_call_minutes, minutesText(th.max_call_minutes)]);
  const dailyOpts = DAILY.map((m) => [m ?? "", m == null ? "No limit" : minutesText(m)]);
  if (th.daily_minutes && !DAILY.includes(th.daily_minutes)) dailyOpts.push([th.daily_minutes, minutesText(th.daily_minutes)]);

  const content = html`
  ${!parent ? alert({ tone: "info", title: "You can turn quiet hours on or off", body: "You can also pause the line. Only a parent can change the times, nights and limits." }) : ""}
  <h2 class="title-lg">Quiet hours</h2>
  <div id="qh-banner">${banner(th)}</div>
  ${quietPreview(q)}
  <form class="tl-stack tl-stack--cards" id="quiet-form" novalidate>
    <section class="tl-card"><div class="tl-stack tl-stack--group">
      <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">When it's quiet</h2><p class="tl-card__body">Phones don't ring and can't call out. Callers hear a gentle message instead.</p></div>
      <fieldset class="tl-timerange"><legend>Quiet hours</legend>
        <div class="tl-timerange__row">${timeField({ id: "qh-start", label: "From", value: q.start })}<span class="tl-timerange__to" aria-hidden="true">to</span>${timeField({ id: "qh-end", label: "Until", value: q.end })}</div>
        <p class="tl-textfield__hint">Overnight is fine: 8:00 pm to 7:00 am.</p>
      </fieldset>
      <fieldset class="tl-radiogroup" id="qh-days"><legend>Nights it applies</legend>
        <div class="tl-cluster">${DAY_NAMES.map((n, i) => checkRow({ id: `day-${i}`, label: n, checked: q.days[i] === "1", name: "day", value: i }))}</div>
      </fieldset>
    </div></section>

    <section class="tl-card"><div class="tl-stack tl-stack--group">
      <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">Call limits</h2><p class="tl-card__body">A gentle beep plays a minute before a call ends.</p></div>
      ${selectField({ id: "longest", label: "Longest call", options: lengthOpts, value: th.max_call_minutes, hint: "The shorter limit of the two families applies." })}
      ${selectField({ id: "daily", label: "Minutes per day", options: dailyOpts, value: th.daily_minutes ?? "", hint: "Counts calls in both directions. Resets at midnight." })}
    </div>
    ${parent ? html`<p class="tl-card__body tl-measure" style="color:var(--ink-muted)" id="qh-note">Changes are saved as you make them.</p>` : ""}</section>
  </form>

  <section class="tl-card"><div class="tl-stack tl-stack--group">
    ${switchRow({ id: "pause", label: "Pause calls", on: th.paused, desc: "No calls in or out until you turn this off." })}
  </div></section>`;

  return {
    title: "Quiet hours", nav: "quiet", template: "settings", content,
    mount(root) {
      const form = root.querySelector("#quiet-form");
      const enabled = root.querySelector("#qh-enabled");
      if (!parent) form.querySelectorAll("input, select").forEach((i) => (i.disabled = true));   // a sitter gets the on/off switch and nothing else
      const days = () => [0, 1, 2, 3, 4, 5, 6].map((i) => (form.querySelector(`#day-${i}`).checked ? "1" : "0")).join("");
      const refresh = () => {
        root.querySelector('[data-qh="start"]').textContent = time12(form.querySelector("#qh-start").value || q.start);
        root.querySelector('[data-qh="end"]').textContent = time12(form.querySelector("#qh-end").value || q.end);
        const d = days();
        root.querySelectorAll("[data-day]").forEach((el) => el.classList.toggle("is-on", d[el.dataset.day] === "1"));
      };
      // Everything saves as soon as it changes. Typing in a time box waits for a short pause; a switch, a night or a limit
      // saves at once. The page isn't redrawn (that would take the cursor away), so the banner is updated in place.
      let timer = null, saving = false, again = false;
      const save = async () => {
        if (saving) { again = true; return; }
        const start = form.querySelector("#qh-start").value, end = form.querySelector("#qh-end").value;
        if (!start || !end) return;                                     // a time box that's mid-edit isn't a time yet
        saving = true;
        const on = enabled.getAttribute("aria-checked") === "true";
        try {
          const r = await patch("/api/treehouse", !parent ? { quiet: { enabled: on } } : {      // a sitter sends only the switch
            quiet: { enabled: on, start, end, days: days() },
            max_call_minutes: Number(form.querySelector("#longest").value),
            daily_minutes: form.querySelector("#daily").value || null,
          });
          ctx.me.treehouse = r;
          root.querySelector("#qh-banner").innerHTML = str(banner(r));
          toast("Saved", "success");
        } catch (err) { toast(err.message, "warning"); }
        saving = false;
        if (again) { again = false; save(); }
      };
      const soon = (ms) => { clearTimeout(timer); timer = setTimeout(save, ms); };
      form.addEventListener("input", (e) => { refresh(); if (e.target.matches("input[type=time], input[type=text]")) soon(700); });
      form.addEventListener("change", (e) => {
        refresh();
        if (e.target.name === "day" && days() === "0000000") {            // at least one night, or turn quiet hours off
          e.target.checked = true; refresh();
          return toast("Pick at least one night, or turn quiet hours off.", "warning");
        }
        soon(e.target.matches("input[type=time]") ? 700 : 0);
      });
      form.addEventListener("submit", (e) => e.preventDefault());
      enabled.addEventListener("tl-change", () => soon(0));

      root.querySelector("#pause").addEventListener("tl-change", async (e) => {
        try {
          ctx.me.treehouse = await patch("/api/treehouse", { paused: e.detail.checked });
          toast(e.detail.checked ? "Calls are paused" : "Calls are back on", e.detail.checked ? "neutral" : "success");
        } catch (err) { window.TreelineUI?.setSwitch(e.target.closest(".tl-switch"), !e.detail.checked); toast(err.message, "warning"); }
      });
    },
  };
}
