// The Treeline softphone, the rotary phone as an app or in a browser: a real dial, real tones, calls over WebRTC.
import { api } from "/shared/api.js";
import { ROTARY } from "/shared/assets.js";
import { brand, footer, html, presence, raw, str } from "/shared/ui.js";
import { forgetPhone, pairScreen, savedPhone } from "./pair.js";
import * as tones from "./tones.js";

const root = document.getElementById("root");
const remoteAudio = document.getElementById("remote-audio");
const JOIN = "0001";                      // dial this to join the call your line is already on
const HOWL_AFTER = 30000;                 // seconds off the hook, doing nothing, before the howler
const INTERDIGIT = 6000;                  // wait this long for another digit, then send what was dialed

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

const say = (main, sub = "") => { if (ui) { ui.status.textContent = main; ui.sub.textContent = sub; } document.body.dataset.state = S.phase; };
const later = (name, ms, fn) => { clearTimeout(S.timers[name]); S.timers[name] = setTimeout(fn, ms); };
const cancel = (...names) => names.forEach((n) => clearTimeout(S.timers[n]));

// ------------------------------------------------------------------ screen

function draw() {
  // The phone itself, its dial and its handset come from the design system (components/RotaryPhone):
  // a drawing, a finger wheel that really turns, and a handset that really lifts. We listen to its events.
  root.innerHTML = str(html`<main class="ph">
    <div class="ph__top">${brand("#")}<span id="reg"></span></div>
    <div class="ph__stage"><div class="ph__glow" id="glow">${raw(ROTARY)}</div></div>
    <p class="ph__status" id="status" role="status" aria-live="polite"></p>
    <p class="ph__sub body" id="sub"></p>
    <div class="ph__night" id="night"></div>
    <div class="ph__bottom">${footer("/phone/licenses.html")}</div>
  </main>
  <div class="ph-wake" id="wake" hidden><div class="tl-card" style="max-width:var(--sheet-max);text-align:center"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Tap to turn the phone on</h2>
    <p class="tl-card__body">Your device needs one tap before it can ring.</p>
    <div class="tl-actions"><button type="button" class="tl-btn tl-btn--primary tl-btn--lg" id="wake-btn"><span class="tl-btn__label">Turn on</span></button></div>
  </div></div></div>`);
  const el = root.querySelector("[data-tl-rotary]");
  ui = { glow: root.querySelector("#glow"), status: root.querySelector("#status"), sub: root.querySelector("#sub"),
    night: root.querySelector("#night"), reg: root.querySelector("#reg"), wake: root.querySelector("#wake"), el,
    hookButton: el.querySelector(".tl-rotary__hook"), number: el.querySelector(".tl-rotary__number"),
    api: window.TreelineUI.rotary(el) };
  S.dial = (d) => ui.api.dial(d);
  el.addEventListener("tl-rotary-hook", async (e) => {
    if (e.detail.offHook) { await tones.unlock(); ui.wake.hidden = true; lift(); } else hangUp();
  });
  el.addEventListener("tl-rotary-pulse", () => tones.pulseClick());        // the dial's contacts, once per number
  // The wheel's own sounds: watch it turn. Forward ticks the ratchet; back whirrs; home thunks.
  new MutationObserver(() => {
    const m = /rotate\(([-\d.]+)/.exec(ui.el.querySelector(".tlp-wheel").getAttribute("transform") || "");
    if (m) tones.dialAngle(Number(m[1]), ui.el.classList.contains("is-dialing"));
  }).observe(el.querySelector(".tlp-wheel"), { attributes: true, attributeFilter: ["transform"] });
  el.addEventListener("tl-rotary-digit", (e) => { if (e.detail.offHook) onDigit(e.detail.digit); });
  document.addEventListener("keydown", (e) => {
    // The phone dials number keys itself when it has focus; this is for when it doesn't.
    if (e.target.closest?.(".tl-rotary__svg")) return;
    if (/^[0-9]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey && !/input|textarea|select/i.test(e.target.tagName)) S.dial?.(Number(e.key));
  }, { signal: life.signal });
  ui.wake.querySelector("#wake-btn").addEventListener("click", async () => { await tones.unlock(); ui.wake.hidden = true; });
  setRegistration();
  render();
}

function render() {
  if (!ui) return;
  ui.glow.classList.toggle("is-ringing", S.phase === "ringing");
  if (ui.number) ui.number.textContent = S.number || "";
  // The kit labels the handset button "Lift the handset"; a ringing phone should say what lifting does.
  if (S.hook === "on" && ui.hookButton) ui.hookButton.setAttribute("aria-label", S.phase === "ringing" ? "Answer the phone" : "Lift the handset");
  ui.night.innerHTML = S.line === "disconnected" && S.hook === "on"
    ? str(html`<section class="tl-card tl-card--plank"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Switched off</p><h3 class="tl-card__title">This phone is off for now</h3></div></header><p class="tl-card__body">A parent turned it off. It won't ring or call out until they turn it back on.</p></section>`)
    : S.line === "quiet" && S.hook === "on"
    ? str(html`<section class="tl-card tl-card--night"><header class="tl-card__head"><div><p class="tl-card__eyebrow">Tonight</p><h3 class="tl-card__title">The phone is sleeping</h3></div></header><p class="tl-card__body">Calls wait until morning.</p></section>`) : "";
  document.body.dataset.state = S.phase;
  document.body.dataset.digits = S.digits;
}

function setRegistration() {
  if (!ui) return;
  ui.reg.innerHTML = str(S.registered ? presence("canopy", "Connected") : presence("bark", "Reconnecting"));
}

// ------------------------------------------------------------------ line state

async function refreshLine() {
  if (!S.creds) return;
  try {
    const r = await api("GET", "/api/line", undefined, { auth: "basic", basic: `${S.creds.sip_user}:${S.creds.secret}` });
    S.line = r.state; if (r.number !== S.number) { S.number = r.number; }
    S.removed = false;
  } catch (e) {
    if (e.code === "removed") return removed();
    // Offline: keep what we knew.
  }
  render();
}

function removed() {
  if (S.pairing) return;
  S.pairing = true;
  forgetPhone(); stopUa(); tones.stop();
  life.abort(); clearInterval(S.timers.refresh);
  S.creds = null; S.registered = false; S.session = null; S.incoming = null; S.hook = "on"; S.phase = "idle";
  pairScreen(root, "This softphone was removed from its treehouse. Add it again to keep using it.")
    .then((c) => { S.pairing = false; return start(c); })
    .catch(() => { S.pairing = false; });
}

// ------------------------------------------------------------------ hook

async function lift() {
  S.hook = "off"; S.digits = "";
  tones.stop();
  if (S.incoming) { answer(); return; }
  // Use what we knew, then check: the line may have changed since we last asked.
  S.phase = "dialtone"; render();
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
  if (!S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now", "The phone is still getting online."); render(); return; }
  if (state === "disconnected") { S.phase = "off"; tones.play("fastbusy"); say("This phone is switched off", "A parent turned it off for now."); render(); return; }
  if (state === "quiet") { S.phase = "sleep"; tones.play("fastbusy"); say("The phone is sleeping", "Try again later."); render(); return; }
  if (state === "in_call" && Date.now() >= S.noJoinUntil) { joinCall(); return; }
  S.phase = "dialtone"; tones.play("dial"); say("Dial a number", ""); render();
  later("howl", HOWL_AFTER, howl);
}

function howl() {
  if (S.hook === "off" && S.phase === "dialtone") { S.phase = "howl"; tones.play("howler"); say("Put the handset back", "Or dial a number."); render(); }
}

function hangUp() {
  S.hook = "on"; cancel("howl", "inter", "after");
  tones.stop();
  if (S.session) { try { S.session.terminate(); } catch { /* already over */ } S.session = null; }
  tones.click();
  S.phase = S.incoming ? "ringing" : "idle";
  S.digits = "";
  if (S.phase === "ringing") { tones.play("bell"); say("Ringing", "Lift the handset to answer."); }
  else say("Lift the handset to make a call", "");
  render();
  refreshLine();
}

// ------------------------------------------------------------------ dialing

function onDigit(d) {
  if (S.hook !== "off") return;
  if (S.phase === "dialtone" || S.phase === "howl") { tones.stop(); cancel("howl"); S.phase = "dialing"; }
  if (S.phase !== "dialing") return;
  S.digits += String(d);
  say("Dial a number", "•".repeat(S.digits.length));
  render();
  cancel("inter");
  if (S.digits.length >= 4 || S.digits === "911") return place(S.digits);
  later("inter", INTERDIGIT, () => place(S.digits));
}

function hookAudio(session) {
  session.on("peerconnection", (e) => {
    e.peerconnection.addEventListener("track", (ev) => { remoteAudio.srcObject = ev.streams[0]; remoteAudio.play?.().catch(() => {}); });
  });
}

function callOptions(extra = {}) {
  return { mediaConstraints: { audio: true, video: false }, pcConfig: { iceServers: S.iceServers }, rtcOfferConstraints: { offerToReceiveAudio: true },
    sessionTimersExpires: 3600, ...extra };
}

function place(number) {
  cancel("inter");
  if (!S.ua || !S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now", ""); render(); return; }
  S.phase = "calling"; say("Ringing", ""); render();
  let session = null;
  const mine = (fn) => (...args) => { if (session && S.session === session) fn(...args); };
  try {
    session = S.ua.call(`sip:${number}@${S.creds.server}`, callOptions({
      eventHandlers: {
        progress: mine(() => { if (S.phase === "calling") tones.play("ringback"); }),
        accepted: mine(() => { tones.stop(); S.phase = "talking"; say("Talking", ""); render(); }),
        confirmed: mine(() => { tones.stop(); S.phase = "talking"; say("Talking", ""); render(); }),
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
        confirmed: mine(() => { S.phase = "talking"; say("Talking", ""); render(); }),
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
  // Off the hook and busy with something else, or already ringing for another caller: not now.
  const busy = S.hook === "off" && !["dialtone", "dialing", "howl"].includes(S.phase);
  if (busy || S.incoming) { session.terminate({ status_code: 486 }); return; }
  S.incoming = session;
  hookAudio(session);
  const over = () => {
    if (S.incoming === session) {                      // it stopped ringing before we answered
      S.incoming = null;
      if (S.phase === "ringing") { tones.stop(); S.phase = "idle"; say("Lift the handset to make a call", ""); render(); }
    } else if (S.session === session) ended();         // it ended or failed after we answered
  };
  session.on("failed", over);
  session.on("ended", over);
  session.on("confirmed", () => { if (S.session === session) { S.phase = "talking"; say("Talking", ""); render(); } });
  if (S.hook === "off") { answer(); return; }
  S.phase = "ringing"; tones.play("bell"); say("Ringing", "Lift the handset to answer."); render();
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
  S.creds = creds; S.hook = "on"; S.phase = "idle"; S.incoming = null; S.session = null; S.registered = false;
  S.insecure = !window.isSecureContext || !navigator.mediaDevices;
  try { const cfg = await api("GET", "/api/phone/config", undefined, { auth: "none" }); S.iceServers = cfg.ice_servers || []; } catch { /* a LAN needs none */ }
  draw();
  say("Lift the handset to make a call", "");
  if (S.insecure) say("This device can't use its microphone", "Open the phone from a secure (https) address. See docs/DEPLOY.md.");
  stopUa(); startUa();
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
  start(await pairScreen(root));
}

// A hook for the browser tests, on this machine only, and without the SIP secret.
if (location.search.includes("test=1") && ["localhost", "127.0.0.1"].includes(location.hostname)) {
  const view = new Proxy(S, { get: (t, k) => (k === "creds" ? undefined : t[k]), set: (t, k, v) => { t[k] = v; return true; } });
  window.__phone = { S: view, tonesLevel: () => tones.effectiveLevel(), lift: () => (ui.api.isOffHook() ? ui.api.hangUp() : ui.api.lift()), dial: (d) => S.dial?.(d), rotary: () => ui.api, tones,
    async stats() { const pc = S.session?.connection; if (!pc) return null; const r = await pc.getStats(); let rx = 0, tx = 0; r.forEach((x) => { if (x.type === "inbound-rtp" && x.kind === "audio") rx += x.bytesReceived; if (x.type === "outbound-rtp" && x.kind === "audio") tx += x.bytesSent; }); return { rx, tx }; } };
}

boot();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/phone/sw.js").catch(() => {});
