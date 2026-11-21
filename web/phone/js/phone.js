// The Treeline softphone, the rotary phone as an app or in a browser: a real dial, real tones, calls over WebRTC.
// The screen is an ordinary Treeline page built from the design system: the brand and tagline, the treehouse's name
// with what the phone is doing, the RotaryPhone on a soft glow with the CardFile of approved strings beside it, the
// plain no-911 line, a "How to dial" sheet with the guide's pictures, and the footer.
import { api, token } from "/shared/api.js";
import { CARDFILE, ROTARY } from "/shared/assets.js";
import { alert, brandLine, button, footer, html, icon, presence, raw, setBusy, sheet, steps, str, tag, textField } from "/shared/ui.js";
import { forgetPhone, pairScreen, savedPhone } from "./pair.js";
import { loggedIn, registerApp } from "/shared/pwa.js";
import * as tones from "./tones.js";

const root = document.getElementById("root");
const remoteAudio = document.getElementById("remote-audio");
const JOIN = "0001";                      // dial this to join the call your line is already on
const HOWL_AFTER = 30000;                 // seconds off the hook, doing nothing, before the howler
const INTERDIGIT = 6000;                  // wait this long for another digit, then send what was dialed

// Under the treehouse's name: what the phone is doing, in a word and a colored dot. While dialing, how far along
// the four numbers are.
const progress = (digits) => "● ".repeat(digits.length) + "○ ".repeat(Math.max(0, 4 - digits.length));

const dark = window.matchMedia("(prefers-color-scheme: dark)");
const applyTheme = () => document.documentElement.setAttribute("data-theme", dark.matches ? "dark" : "light");
applyTheme(); dark.addEventListener?.("change", applyTheme);

const S = {
  creds: null, hook: "on", phase: "idle", digits: "", session: null, incoming: null,
  registered: false, line: "idle", number: "", ua: null, timers: {}, iceServers: [], noJoinUntil: 0, pairing: false,
};
let ui = null;
// Everything start() attaches to the page hangs off this, so starting again (after a
// softphone is removed and added back) doesn't stack listeners and timers.
let life = new AbortController();

const say = (main, sub = "") => { S.words = [main, sub]; showStatus(); document.body.dataset.state = S.phase; };
const hush = () => say("");
/** "20:00" → "8 pm", "19:30" → "7:30 pm": quiet time in a kid's words. */
const clock = (hm) => { const [h, m] = String(hm || "0:0").split(":").map(Number); const h12 = ((h + 11) % 12) + 1; return `${h12}${m ? ":" + String(m).padStart(2, "0") : ""} ${h < 12 ? "am" : "pm"}`; };
const later = (name, ms, fn) => { clearTimeout(S.timers[name]); S.timers[name] = setTimeout(fn, ms); };
const cancel = (...names) => names.forEach((n) => clearTimeout(S.timers[n]));

// ------------------------------------------------------------------ screen

// How to dial: the guide's pictures, one at a time, in a sheet.
const GUIDE = [
  { pic: "light", name: "The light", title: "The little light", lights: true },
  { pic: "lift", name: "Lift", title: "Lift the handset. Hear the hum?" },
  { pic: "finger", name: "Finger in", title: "Put a finger in a number." },
  { pic: "turn", name: "Turn", title: "Turn it to the metal stop. Then let go!" },
  { pic: "numbers", name: "Four numbers", title: "Dial all four numbers to call a friend." },
  { pic: "busy", name: "Busy", title: "Beep, beep, beep? They’re busy. Hang up and try later." },
  { pic: "quiet", name: "Quiet time", title: "At quiet time the phone is asleep." },
  { pic: "no-911", name: "No 911", title: "This phone can’t call 911. In an emergency, find a grown-up." },
  { pic: "hang-up", name: "Hang up", title: "All done? Put the handset back. Bye!" },
];
const LIGHTS = [["on", "Steady green: ready to call"], ["connecting", "Pulsing orange: connecting, wait"], ["off", "Blinking red: ask a grown-up"], ["ring", "Flashing green: a call! Lift it"]];

function guideStep(i) {
  const g = GUIDE[i];
  return html`<div class="ph-guide">${steps(GUIDE.map((x) => x.name), i + 1, "How to dial")}
  <figure class="ph-guide__pic"><img src="/ui/illustrations/guide/${g.pic}.svg" alt="" width="300" height="270"></figure>
  <p class="ph-guide__text">${g.title}</p>
  ${g.lights ? html`<ul class="ph-guide__lights">${LIGHTS.map(([k, t]) => html`<li><span class="ph-lamp ph-lamp--${k}" aria-hidden="true"></span>${t}</li>`)}</ul>` : ""}</div>`;
}

function draw() {
  // The phone and the card file come from the design system: a finger wheel that really turns, a handset that really
  // lifts and trembles when it rings, a little light for the line, and a card file that turns. We listen to their events.
  root.innerHTML = str(html`<div class="ph">
  <header class="ph__head">
    ${brandLine()}
    <span id="quiet">${tag("sky", "Quiet time", "moon")}</span>
  </header>
  <main class="ph__main">
    <section class="ph__info ph__sr">
      <h1 class="ph__name" id="name">Your treehouse</h1>
      <div class="ph__status">
        <p class="ph__statusline" id="status" role="status" aria-live="polite"></p>
        <p class="ph__sub" id="sub"></p>
      </div>
    </section>
    <section class="ph__stage" aria-label="The phone">
      <div class="ph__phone"><div class="ph__glow" aria-hidden="true"></div>${raw(ROTARY)}</div>
    </section>
    <div class="ph__cards">${raw(CARDFILE)}</div>
    <div class="ph__notice"></div>
    <div class="ph__bottom">
      <div class="ph__actions">${button({ label: "How to dial", icon: "phone", attrs: { "data-tl-open": "guide", id: "guide-open" } })}${button({ label: "For parents", icon: "key", attrs: { "data-tl-open": "leave", id: "leave-open" } })}</div>
    </div>
  </main>
  <footer class="ph__foot">${footer("/phone/licenses.html")}</footer>
  <span class="ph__sr" id="reg" role="status"></span>
</div>
${sheet({ id: "guide", title: "How to call a friend", body: html`<div id="guide-step"></div>`,
  actions: html`${button({ label: "Back", attrs: { id: "guide-back" } })}${button({ label: "Next", variant: "primary", iconAfter: "chevron-right", attrs: { id: "guide-next" } })}` })}
${sheet({ id: "leave", title: "For parents", body: html`
  <form id="leave-form" class="tl-stack tl-stack--group" novalidate>
    <p class="tl-sheet__body">Enter the parent code to stop using this device as a phone. ${loggedIn() ? "You'll go to the parent dashboard." : "You'll go back to the start screen, where you can add a phone or log in."}</p>
    ${textField({ id: "leave-code", name: "code", label: "Parent code", type: "password", attrs: { inputmode: "numeric", pattern: "[0-9]*", maxlength: "6", autocomplete: "off" } })}
    <div id="leave-error"></div>
    <p class="body" style="margin:0"><a href="#" data-forgot style="color:var(--ink-muted);text-decoration:underline;font-size:14px;display:inline-block;padding:var(--space-2) 0">I don't know the code</a></p></form>
  <div id="leave-forgot" class="tl-stack tl-stack--group" hidden>
    <p class="tl-sheet__body">Without the parent code you can still sign this device out. It stops being a phone and this browser is signed out of the parent dashboard, so the dashboard asks for a login. A parent can add the phone again with the code on the start screen.</p>
    <div id="forgot-error"></div>
    <div class="tl-actions">${button({ label: "Cancel", attrs: "data-tl-close" })}${button({ label: "Sign out of this browser", variant: "primary", attrs: { id: "sign-out-go" } })}</div>
    <p class="body" style="margin:0"><a href="#" data-use-code style="color:var(--ink-muted);text-decoration:underline;font-size:14px;display:inline-block;padding:var(--space-2) 0">I have the parent code</a></p>
  </div>`,
  actions: html`${button({ label: "Cancel", attrs: "data-tl-close" })}${button({ label: "Leave phone mode", variant: "primary", type: "submit", attrs: { form: "leave-form", id: "leave-go" } })}` })}
<div class="ph-wake" id="wake" hidden><div class="tl-card" style="max-width:var(--sheet-max);text-align:center"><div class="tl-stack tl-stack--group">
  <h2 class="tl-card__title">Tap to turn the phone on</h2>
  <p class="tl-card__body">Your device needs one tap before it can ring.</p>
  <div class="tl-actions"><button type="button" class="tl-btn tl-btn--primary tl-btn--lg" id="wake-btn"><span class="tl-btn__label">Turn on</span></button></div>
</div></div></div>`);
  // The no-911 line is part of the phone's own markup, which puts it right under the phone. In the one-column layout it
  // sits below the card file, just above "How to dial"; on a wide screen it stays under the phone.
  const notice = root.querySelector(".tl-rotary__notice"), noticeHome = notice && notice.parentNode, noticeSlot = root.querySelector(".ph__notice");
  const wide = window.matchMedia("(min-width: 900px) and (min-aspect-ratio: 1/1)");
  setLite(liteSaved() || (navigator.deviceMemory && navigator.deviceMemory <= 2) || false);
  const placeNotice = () => { if (notice) (wide.matches ? noticeHome : noticeSlot).appendChild(notice); };
  placeNotice();
  wide.addEventListener("change", placeNotice);
  const el = root.querySelector("[data-tl-rotary]");
  const cardEl = root.querySelector("[data-tl-cardfile]");
  ui = { status: root.querySelector("#status"), sub: root.querySelector("#sub"), name: root.querySelector("#name"), quiet: root.querySelector("#quiet"),
    reg: root.querySelector("#reg"), wake: root.querySelector("#wake"), guide: root.querySelector("#guide"), el, cardEl,
    hookButton: el.querySelector(".tl-rotary__hook"), number: el.querySelector(".tl-rotary__number"),
    api: window.TreelineUI.rotary(el), cards: window.TreelineUI.cardfile(cardEl), strings: "", step: 0 };
  S.dial = (d) => ui.api.dial(d);
  // the guide: Back and Next walk the pictures; Next on the last one closes it
  const showStep = (i) => {
    ui.step = Math.max(0, Math.min(GUIDE.length - 1, i));
    root.querySelector("#guide-step").innerHTML = str(guideStep(ui.step));
    root.querySelector("#guide-back").disabled = ui.step === 0;
    root.querySelector("#guide-next .tl-btn__label").textContent = ui.step === GUIDE.length - 1 ? "Done" : "Next";
  };
  showStep(0);
  root.querySelector("#guide-open").addEventListener("click", () => showStep(0));
  root.querySelector("#guide-back").addEventListener("click", () => showStep(ui.step - 1));
  root.querySelector("#guide-next").addEventListener("click", () => { if (ui.step === GUIDE.length - 1) window.TreelineUI.closeSheet(ui.guide); else showStep(ui.step + 1); });
  el.addEventListener("tl-rotary-hook", async (e) => {
    sampleFrames();                                                          // how smoothly does this device lift the handset?
    if (e.detail.offHook) { await tones.unlock(); ui.wake.hidden = true; lift(); } else hangUp();
  });
  el.querySelector(".tl-rotary__svg").addEventListener("pointerdown", () => sampleFrames(1200));   // ... and turn the dial?
  el.addEventListener("tl-rotary-pulse", () => tones.pulseClick());        // the dial's contacts, once per number
  // The wheel's own sounds: watch it turn. Forward ticks the ratchet; back whirrs; home thunks.
  new MutationObserver(() => {
    const m = /rotate\(([-\d.]+)/.exec(ui.el.querySelector(".tlp-wheel").getAttribute("transform") || "");
    if (m) tones.dialAngle(Number(m[1]), ui.el.classList.contains("is-dialing"));
  }).observe(el.querySelector(".tlp-wheel"), { attributes: true, attributeFilter: ["transform"] });
  el.addEventListener("tl-rotary-digit", (e) => { if (e.detail.offHook) onDigit(e.detail.digit); });
  document.addEventListener("keydown", (e) => {
    // The phone dials number keys itself when it has focus; this is for when it doesn't (and the guide isn't open).
    if (e.target.closest?.(".tl-rotary__svg") || !ui.guide.hidden) return;
    if (/^[0-9]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey && !/input|textarea|select/i.test(e.target.tagName)) S.dial?.(Number(e.key));
  }, { signal: life.signal });
  // For parents: the parent code takes this device out of phone mode. The server checks it (and removes the handset).
  const leaveForm = root.querySelector("#leave-form"), forgot = root.querySelector("#leave-forgot"), leaveActions = root.querySelector("#leave .tl-sheet > .tl-actions");
  const showForgot = (on) => { leaveForm.hidden = on; forgot.hidden = !on; leaveActions.hidden = on; };
  const oops = (sel, m) => { root.querySelector(sel).innerHTML = m ? str(alert({ tone: "danger", title: m })) : ""; };
  root.querySelector("#leave-open").addEventListener("click", () => {
    leaveForm.reset(); showForgot(false); oops("#leave-error", ""); oops("#forgot-error", "");
    setTimeout(() => leaveForm.querySelector("input")?.focus(), 50);
  });
  leaveForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = root.querySelector("#leave-go");
    setBusy(btn, true, "Checking");
    try { await leavePhoneMode(leaveForm.querySelector("[name=code]").value.trim()); }
    catch (err) { oops("#leave-error", err.message || "That didn't work. Try again."); setBusy(btn, false); }
  });
  // Forgot the code: sign the device out. No sign-in happens here, and nothing opens: it just stops being a phone and forgets any parent session.
  root.querySelector("[data-forgot]").addEventListener("click", (e) => { e.preventDefault(); showForgot(true); });
  root.querySelector("[data-use-code]").addEventListener("click", (e) => { e.preventDefault(); showForgot(false); leaveForm.querySelector("input").focus(); });
  root.querySelector("#sign-out-go").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    setBusy(btn, true, "Signing out");
    try { await signOutDevice(); } catch (err) { oops("#forgot-error", err.message || "That didn't work. Try again."); setBusy(btn, false); }
  });
  ui.wake.querySelector("#wake-btn").addEventListener("click", async () => { await tones.unlock(); ui.wake.hidden = true; });
  showLine();
  render();
}

/** What the phone is doing, as the design system's Presence: a dot and a word, with a line under it. */
function showStatus() {
  if (!ui) return;
  const [main, sub] = S.words || ["", ""];
  let tone = "available", word = main;
  if (S.phase === "ringing") tone = "ringing";
  else if (S.phase === "talking" || S.phase === "calling") tone = "on-call";
  else if (S.phase === "sleep" || (S.phase === "idle" && S.line === "quiet")) tone = "quiet";
  else if (S.phase === "off" || (S.phase === "idle" && S.line === "disconnected")) tone = "paused";
  else if (S.phase === "busy" || (S.phase === "idle" && S.lineLight !== "on")) tone = "offline";
  if (!word) word = tone === "offline" ? (S.lineLight === "off" ? "Can’t connect. Ask a grown-up." : "Connecting…") : S.phase === "dialing" ? "Dialing" : S.hook === "off" ? "Ready to dial" : "Ready to call";
  let line = sub;
  if (!line && S.phase === "idle" && tone === "available") line = "Lift the handset and dial a friend’s four numbers.";
  if (S.phase === "dialing") line = progress(S.digits).trim();
  ui.status.innerHTML = str(presence(tone, word));
  ui.sub.textContent = line;
  ui.sub.classList.toggle("ph__sub--dots", S.phase === "dialing");
}

/** The words for a hung-up, idle phone: they follow the line's state. */
function idleWords() {
  if (S.line === "disconnected") return ["This phone is switched off"];
  if (S.line === "quiet") return ["The phone is sleeping"];
  return [""];
}

// ------------------------------------------------------------------ older devices
// The artwork's hand-painted texture (SVG turbulence filters) is the costly part to redraw, and an old tablet that has to
// redraw it every frame while the handset lifts or the dial turns feels laggy. So the phone times its own animations: if
// they run slowly twice, it drops the texture (the phone stays the same shape and colors) and remembers that.
const LITE_KEY = "treeline.lite";
/** Frame gaps (ms) from an animation: slow if the typical frame took longer than about 26 ms (under ~38 frames a second). */
export function isSlow(gaps) {
  if (gaps.length < 8) return false;
  const sorted = [...gaps].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] > 26;
}
function liteSaved() { try { return localStorage.getItem(LITE_KEY) === "1"; } catch { return false; } }
function setLite(on, remember) {
  S.lite = on;
  root.querySelector(".ph")?.classList.toggle("ph--lite", on);
  if (remember) { try { localStorage.setItem(LITE_KEY, on ? "1" : "0"); } catch { /* it just starts full again next time */ } }
}
let slowSamples = 0, sampling = false;
function sampleFrames(ms = 900) {
  if (sampling || S.lite) return;
  sampling = true;
  const gaps = []; let last = performance.now(); const end = last + ms; let hidden = false;
  const tick = (t) => {
    if (document.hidden) hidden = true;
    gaps.push(t - last); last = t;
    if (t < end) { requestAnimationFrame(tick); return; }
    sampling = false; gaps.shift();
    if (!hidden && isSlow(gaps) && ++slowSamples >= 2) setLite(true, true);
  };
  requestAnimationFrame(tick);
}

function render() {
  if (!ui) return;
  ui.api.setRinging(S.phase === "ringing");                        // only the handset trembles
  if (ui.number) ui.number.textContent = S.number || "";
  // The kit labels the handset button "Lift the handset"; a ringing phone should say what lifting does.
  if (S.hook === "on" && ui.hookButton) ui.hookButton.setAttribute("aria-label", S.phase === "ringing" ? "Answer the phone" : "Lift the handset");
  if (S.hook === "on" && S.phase === "idle") say(...idleWords());
  showStatus();
  document.body.dataset.state = S.phase;
  document.body.dataset.digits = S.digits;
}

/** The page's words from the line: the treehouse's name, its quiet hours, its card file. */
function fillPage(r) {
  if (!ui) return;
  if (r.treehouse) { ui.name.textContent = r.treehouse; document.title = `${r.treehouse} · Treeline Phone`; }
  if (r.quiet) {
    ui.quiet.hidden = !r.quiet.enabled;
    if (r.quiet.enabled) ui.quiet.innerHTML = str(tag("sky", `Quiet time ${clock(r.quiet.start)} – ${clock(r.quiet.end)}`, "moon"));
  }
  const cards = JSON.stringify(r.strings || []);
  if (cards !== ui.strings) { ui.strings = cards; ui.cards.setContacts(r.strings || []); }
}

// The little light on the phone: steady green when connected; pulsing orange while it's connecting (starting up,
// or retrying after the line drops); blinking red once it has tried for a while without getting through.
const GIVE_UP_MS = 15000;
function setRegistration() {
  if (S.registered) { clearTimeout(S.timers.lineLost); S.timers.lineLost = 0; S.lineLight = "on"; }
  else if (!S.timers.lineLost && S.lineLight !== "off") {          // timed from when the line was lost, not from each retry
    S.lineLight = "connecting";
    S.timers.lineLost = setTimeout(() => { S.timers.lineLost = 0; if (!S.registered) { S.lineLight = "off"; showLine(); } }, GIVE_UP_MS);
  }
  showLine();
}
function showLine() {
  if (!ui) return;
  ui.reg.textContent = S.lineLight === "on" ? "The phone is connected." : S.lineLight === "connecting" ? "The phone is connecting." : "The phone can't connect. Ask a grown-up.";
  ui.api.setLine(S.lineLight);
  showStatus();
}

// ------------------------------------------------------------------ line state

async function refreshLine() {
  if (!S.creds) return;
  try {
    const r = await api("GET", "/api/line", undefined, { auth: "basic", basic: `${S.creds.sip_user}:${S.creds.secret}` });
    S.line = r.state; if (r.number !== S.number) { S.number = r.number; }
    S.removed = false;
    fillPage(r);
  } catch (e) {
    if (e.code === "removed") return removed();
    // Offline: keep what we knew.
  }
  render();
}

function removed() {
  if (S.pairing || S.leaving) return;               // leaving on purpose: the server has dropped this handset, the page is about to go
  S.pairing = true;
  forgetPhone(); stopUa(); tones.stop();
  life.abort(); clearInterval(S.timers.refresh);
  S.creds = null; S.registered = false; S.session = null; S.incoming = null; S.hook = "on"; S.phase = "idle";
  pairScreen(root, "This softphone was removed from its treehouse. Add it again to keep using it.")
    .then((c) => { S.pairing = false; return start(c); })
    .catch(() => { S.pairing = false; });
}

/** Stop being a phone: the server checks the parent code and removes this handset; then this device forgets its sign-in. A parent who is
 *  signed in on this device lands in the dashboard, anyone else on the start screen. */
async function leavePhoneMode(code) {
  if (!code) throw new Error("Type the parent code.");
  S.leaving = true;                                  // until the server answers, a "removed" from the line or SIP must not start a pairing screen
  try { await api("POST", "/api/phone/leave", { code }, { basic: `${S.creds.sip_user}:${S.creds.secret}` }); }
  catch (e) { if (e.code !== "removed") { S.leaving = false; throw e; } }       // already removed by a parent: it is a plain device now
  goodbye(loggedIn() ? "/parent/#/home" : "/phone/?left=1");
}

/** The parent code is forgotten: sign this device out. It stops being a phone (the server drops the handset; nothing is opened by this) and the
 *  browser forgets any parent session, so any dashboard page now asks for a login. */
async function signOutDevice() {
  S.leaving = true;
  try { await api("POST", "/api/phone/sign-out", {}, { basic: `${S.creds.sip_user}:${S.creds.secret}` }); }
  catch (e) { if (e.code !== "removed") { S.leaving = false; throw e; } }
  if (token.get()) { try { await api("POST", "/api/auth/signout", {}); } catch { /* signing out anyway */ } }
  token.clear();
  goodbye("/phone/?left=out");
}

function goodbye(where) {
  forgetPhone(); stopUa(); tones.stop(); life.abort(); clearInterval(S.timers.refresh);
  location.replace(where);
}

// ------------------------------------------------------------------ hook

async function lift() {
  S.hook = "off"; S.digits = "";
  tones.stop();
  if (S.incoming) { answer(); return; }
  // Use what we knew, then check: the line may have changed since we last asked.
  S.phase = "dialtone"; render();
  // Joining a call is the one decision that must not rest on what we knew a moment ago: hanging up asks the server who is on the
  // line, and can ask before the server has noticed the call is over, so the answer we hold may say "in a call" for up to 15
  // seconds after it ended. A phone that then joins gets a fast busy instead of a dial tone. Ask first.
  if (S.line === "in_call") {
    await refreshLine();
    if (S.hook !== "off") return;                // put down again while we asked
  }
  decideLift(S.line);
  const before = S.line;
  await refreshLine();
  // The answer may differ from what we knew (a phone just reconnected, quiet hours just ended): follow it.
  if (S.hook === "off" && ["dialtone", "off", "sleep"].includes(S.phase) && S.line !== before) decideLift(S.line);
}

/** What to do the moment the handset comes up, given the line's state. */
function decideLift(state) {
  cancel("howl", "inter", "after");
  if (S.insecure) { S.phase = "busy"; tones.play("fastbusy"); say("This device can't use its microphone", "Open the phone from a secure (https) address."); render(); return; }
  if (!S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now"); render(); return; }
  if (state === "disconnected") { S.phase = "off"; tones.play("fastbusy"); say("This phone is switched off"); render(); return; }
  if (state === "quiet") { S.phase = "sleep"; tones.play("fastbusy"); say("The phone is sleeping"); render(); return; }
  if (state === "in_call" && Date.now() >= S.noJoinUntil) { joinCall(); return; }
  S.phase = "dialtone"; tones.play("dial"); hush(); render();
  later("howl", HOWL_AFTER, howl);
}

function howl() {
  if (S.hook === "off" && S.phase === "dialtone") { S.phase = "howl"; tones.play("howler"); hush(); render(); }
}

function hangUp() {
  S.hook = "on"; cancel("howl", "inter", "after");
  tones.stop();
  if (S.session) { try { S.session.terminate(); } catch { /* already over */ } S.session = null; }
  tones.click();
  S.phase = S.incoming ? "ringing" : "idle";
  S.digits = "";
  if (S.phase === "ringing") { tones.play("bell"); say("Ringing"); }
  else say(...idleWords());
  render();
  refreshLine();
}

// ------------------------------------------------------------------ dialing

function onDigit(d) {
  if (S.hook !== "off") return;
  if (S.phase === "dialtone" || S.phase === "howl") { tones.stop(); cancel("howl"); S.phase = "dialing"; }
  if (S.phase !== "dialing") return;
  S.digits += String(d);
  say(progress(S.digits).trim());
  render();
  cancel("inter");
  if (S.digits.length >= 4 || S.digits === "911") return place(S.digits);
  later("inter", INTERDIGIT, () => place(S.digits));
}

/** Play what the other end (or the operator) says. A browser may refuse to start playback until the person has tapped the page
 *  (its autoplay rules); that used to fail silently and the audio began only after some later tap. Now the refusal is
 *  remembered, playback is retried at the next tap or key press and when the call connects, and ?debug=1 shows what happened. */
const audioState = { error: "", tries: 0 };
// One retry at the next tap or key press, however many times playback is refused: the three listeners are added together,
// removed together, and never doubled.
const RETRY_EVENTS = ["pointerdown", "keydown", "touchend"];
let retryArmed = false;
function retryPlay() { disarmRetry(); playRemote(); }
function armRetry() {
  if (retryArmed) return;
  retryArmed = true;
  RETRY_EVENTS.forEach((t) => window.addEventListener(t, retryPlay, { capture: true }));
}
function disarmRetry() {
  if (!retryArmed) return;
  retryArmed = false;
  RETRY_EVENTS.forEach((t) => window.removeEventListener(t, retryPlay, { capture: true }));
}
/** The call is over (or a new one is starting): nothing may be left to play or retry, so the next call can't replay this one's stream. */
function stopRemoteAudio() {
  disarmRetry();
  try { remoteAudio.pause(); } catch { /* nothing playing */ }
  remoteAudio.srcObject = null;
  audioState.error = "";
}
function playRemote() {
  if (!remoteAudio.srcObject) return;
  remoteAudio.muted = false; remoteAudio.volume = 1;
  audioState.tries++;
  const p = remoteAudio.play?.();
  if (p && p.catch) p.then(() => { audioState.error = ""; }, (err) => {
    if (err && err.name === "AbortError") return;           // we stopped or replaced the audio while it was starting: not a refusal
    audioState.error = (err && err.name) || "blocked";
    console.warn("The browser wouldn't start the call audio yet:", audioState.error);
    armRetry();
  });
}
const hooked = new WeakSet();
function hookAudio(session) {
  // A call's audio arrives as a "track" on its peer connection. Two things used to leave the calling phone with nothing to play:
  // the track can come with no stream attached (so streams[0] is undefined), and an outgoing call can create its connection
  // before we are listening for it. Handle both: wrap a lone track in a stream, and attach to a connection that already exists.
  stopRemoteAudio();                                    // a new call starts from a clean element
  const attach = (pc) => {
    if (!pc || hooked.has(pc)) return;
    hooked.add(pc);
    let stream = null;                                  // one stream per connection: a later track joins it, it isn't replaced
    pc.addEventListener("track", (ev) => {
      if (ev.track && ev.track.kind !== "audio") return;
      if (ev.streams && ev.streams[0]) stream = ev.streams[0];
      else { stream = stream || new MediaStream(); if (!stream.getTracks().includes(ev.track)) stream.addTrack(ev.track); }
      if (remoteAudio.srcObject !== stream) remoteAudio.srcObject = stream;
      playRemote();
    });
  };
  attach(session.connection);
  session.on("peerconnection", (e) => attach(e.peerconnection));
}

function callOptions(extra = {}) {
  return { mediaConstraints: { audio: true, video: false }, pcConfig: { iceServers: S.iceServers }, rtcOfferConstraints: { offerToReceiveAudio: true },
    sessionTimersExpires: 3600, ...extra };
}

function place(number) {
  cancel("inter");
  if (!S.ua || !S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now"); render(); return; }
  S.phase = "calling"; say("Ringing", ""); render();
  let session = null;
  const mine = (fn) => (...args) => { if (session && S.session === session) fn(...args); };
  try {
    session = S.ua.call(`sip:${number}@${S.creds.server}`, callOptions({
      eventHandlers: {
        progress: mine(() => { if (S.phase === "calling") tones.play("ringback"); }),
        accepted: mine(() => { tones.stop(); S.phase = "talking"; say("Talking", ""); render(); }),
        confirmed: mine(() => { tones.stop(); playRemote(); S.phase = "talking"; say("Talking", ""); render(); }),
        failed: mine(() => ended()),
        ended: mine(() => ended()),
      },
    }));
    S.session = session;
    hookAudio(session);
  } catch { ended(); }
}

function joinCall() {
  S.phase = "calling"; say("Joining the call", ""); render();
  const startedAt = Date.now();
  let session = null;
  const mine = (fn) => (...args) => { if (session && S.session === session) fn(...args); };
  try {
    session = S.ua.call(`sip:${JOIN}@${S.creds.server}`, callOptions({
      eventHandlers: {
        confirmed: mine(() => { playRemote(); S.phase = "talking"; say("Talking", ""); render(); }),
        failed: mine(() => { S.noJoinUntil = Date.now() + 10000; ended(); }),   // don't try again at once: fall back to dial tone
        ended: mine(() => { if (Date.now() - startedAt < 3000) S.noJoinUntil = Date.now() + 10000; ended(); }),
      },
    }));
    S.session = session; hookAudio(session);
  } catch { S.noJoinUntil = Date.now() + 10000; ended(); }
}

/** The other side hung up, or the call failed. A click, a moment of quiet, then dial tone. */
function ended() {
  S.session = null;
  stopRemoteAudio();
  tones.stop();
  if (S.hook !== "off") return;
  S.phase = "after"; S.digits = "";
  tones.click(); say("", ""); render();
  later("after", 1200, async () => {
    if (S.hook !== "off") return;
    await refreshLine();
    if (S.hook === "off") decideLift(S.line);
  });
}

// ------------------------------------------------------------------ answering and ringing

function onIncoming(session) {
  if (ui && !ui.guide.hidden) window.TreelineUI.closeSheet(ui.guide);   // close the guide: the phone is ringing
  // Off the hook and busy with something else, or already ringing for another caller: not now.
  const busy = S.hook === "off" && !["dialtone", "dialing", "howl"].includes(S.phase);
  if (busy || S.incoming) { session.terminate({ status_code: 486 }); return; }
  S.incoming = session;
  hookAudio(session);
  const over = () => {
    if (S.incoming === session) {                      // it stopped ringing before we answered
      S.incoming = null;
      if (S.phase === "ringing") { tones.stop(); S.phase = "idle"; render(); }
    } else if (S.session === session) ended();         // it ended or failed after we answered
  };
  session.on("failed", over);
  session.on("ended", over);
  session.on("confirmed", () => { if (S.session === session) { S.phase = "talking"; say("Talking", ""); render(); } });
  if (S.hook === "off") { answer(); return; }
  S.phase = "ringing"; tones.play("bell"); say("Ringing"); render();
}

function answer() {
  const session = S.incoming; if (!session) return;
  S.incoming = null; S.session = session;
  tones.stop(); cancel("howl", "inter");
  S.phase = "talking"; say("Talking", ""); render();
  try { session.answer(callOptions()); } catch { ended(); }
}

// ------------------------------------------------------------------ SIP

function stopUa() { try { S.ua?.stop(); } catch { /* ignore */ } S.ua = null; }

function startUa() {
  const c = S.creds;
  window.JsSIP.debug.disable("JsSIP:*");
  const socket = new window.JsSIP.WebSocketInterface(c.ws_url);
  S.ua = new window.JsSIP.UA({ sockets: [socket], uri: `sip:${c.sip_user}@${c.server}`, authorization_user: c.sip_user, password: c.secret,
    register: true, register_expires: 120, user_agent: "Treeline Phone", connection_recovery_min_interval: 2, connection_recovery_max_interval: 20 });
  S.ua.on("registered", () => { S.registered = true; setRegistration(); });
  S.ua.on("unregistered", () => { S.registered = false; setRegistration(); });
  S.ua.on("registrationFailed", () => { S.registered = false; setRegistration(); });
  S.ua.on("disconnected", () => { S.registered = false; setRegistration(); });
  S.ua.on("newRTCSession", (e) => { if (e.originator === "remote") onIncoming(e.session); });
  S.ua.start();
}

async function start(creds) {
  life.abort(); life = new AbortController(); clearInterval(S.timers.refresh);
  S.creds = creds; S.hook = "on"; S.phase = "idle"; S.incoming = null; S.session = null; S.registered = false; S.lineLight = "connecting";
  S.insecure = !window.isSecureContext || !navigator.mediaDevices;
  try { const cfg = await api("GET", "/api/phone/config", undefined, { auth: "none" }); S.iceServers = cfg.ice_servers || []; } catch { /* a LAN needs none */ }
  draw();
  say(...idleWords());
  if (S.insecure) say("This device can't use its microphone", "Open the phone from a secure (https) address. See docs/DEPLOY.md.");   // for the grown-up setting it up
  stopUa(); clearTimeout(S.timers.lineLost); S.timers.lineLost = 0; startUa(); setRegistration();
  refreshLine();
  S.timers.refresh = setInterval(() => { if (S.hook === "on") refreshLine(); }, 15000);
  // Keep the device awake: a phone that sleeps can't ring.
  const keepAwake = async () => { try { await navigator.wakeLock?.request("screen"); } catch { /* not allowed here */ } };
  keepAwake();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") keepAwake(); }, { signal: life.signal });
  // The browser wants one tap before it will make sound.
  if (!(await tones.unlock())) ui.wake.hidden = false;
  document.addEventListener("pointerdown", () => tones.unlock(), { once: true, signal: life.signal });
  window.addEventListener("pagehide", () => { try { S.session?.terminate(); } catch { /* closing */ } }, { signal: life.signal });
}

async function boot() {
  const saved = savedPhone();
  if (saved && saved.sip_user) return start(saved);
  const left = new URLSearchParams(location.search).get("left");
  if (left) history.replaceState(null, "", location.pathname + location.hash);   // a reload or a later visit shouldn't show it again
  start(await pairScreen(root, left === "out" ? "You're signed out, and this device isn't a phone anymore. You can add it again any time."
    : left ? "This device isn't a phone anymore. You can add it again any time." : undefined));
}

// ?debug=1 on the phone's address shows a small readout of the call audio, to say what the browser is doing when a call is silent.
// It is opt-in and works on any address on purpose: it is for a real device on your network, where the page is not on localhost.
if (location.search.includes("debug=1")) {
  const box = document.createElement("pre");
  box.id = "audio-debug";
  box.style.cssText = "position:fixed;left:8px;bottom:72px;z-index:9999;margin:0;padding:6px 8px;border-radius:8px;background:#000c;color:#9f9;font:11px/15px monospace;pointer-events:none;white-space:pre-wrap;max-width:92vw";
  document.body.appendChild(box);
  const timer = setInterval(() => {
    if (!box.isConnected) return clearInterval(timer);             // the readout is gone: stop updating it
    const t = remoteAudio.srcObject && remoteAudio.srcObject.getAudioTracks ? remoteAudio.srcObject.getAudioTracks()[0] : null;
    box.textContent = [`call audio: ${remoteAudio.srcObject ? (remoteAudio.paused ? "NOT playing" : "playing") : "no call"}${audioState.error ? "  (browser said " + audioState.error + ")" : ""}`,
      `  track: ${t ? t.readyState + (t.muted ? ", muted" : ", live") : "none"}   time: ${remoteAudio.currentTime.toFixed(1)}s   tries: ${audioState.tries}`,
      `  phase: ${S.phase}   tones: ${tones.audioReady() ? "sound on" : "sound OFF (tap the page)"}`].join("\n");
  }, 400);
}

// A hook for the browser tests, on this machine only, and without the SIP secret.
if (location.search.includes("test=1") && ["localhost", "127.0.0.1"].includes(location.hostname)) {
  const view = new Proxy(S, { get: (t, k) => (k === "creds" ? undefined : t[k]), set: (t, k, v) => { t[k] = v; return true; } });
  window.__phone = { isSlow, setLite, cadenceSamples: tones.cadenceSamples, hookAudio, playRemote, stopRemoteAudio, audioState, S: view, render: () => render(), cards: () => ui.cards, tonesLevel: () => tones.effectiveLevel(), lift: () => (ui.api.isOffHook() ? ui.api.hangUp() : ui.api.lift()), dial: (d) => S.dial?.(d), rotary: () => ui.api, tones,
    async stats() { const pc = S.session?.connection; if (!pc) return null; const r = await pc.getStats(); let rx = 0, tx = 0; r.forEach((x) => { if (x.type === "inbound-rtp" && x.kind === "audio") rx += x.bytesReceived; if (x.type === "outbound-rtp" && x.kind === "audio") tx += x.bytesSent; }); return { rx, tx }; } };
}

boot();
registerApp();
