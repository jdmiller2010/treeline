// The Treeline softphone, the rotary phone as an app or in a browser: a real dial, real tones, calls over WebRTC.
// The screen is the design system's softphone room (components/SoftphoneDesk): the phone on a side table, with the
// guide book, the card file of strings, the no-911 sticker and the cards for credit, support and licenses around it.
import { api } from "/shared/api.js";
import { DESK } from "/shared/assets.js";
import { CONTACT, SUPPORT_URL, html, raw, str } from "/shared/ui.js";
import { forgetPhone, pairScreen, savedPhone } from "./pair.js";
import * as tones from "./tones.js";

const root = document.getElementById("root");
const remoteAudio = document.getElementById("remote-audio");
const JOIN = "0001";                      // dial this to join the call your line is already on
const HOWL_AFTER = 30000;                 // seconds off the hook, doing nothing, before the howler
const INTERDIGIT = 6000;                  // wait this long for another digit, then send what was dialed

// The wall says only what's happening (ringing, talking, asleep): how to dial is the guide book's job.
// While dialing it shows how far along the four numbers are.
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

const say = (main, sub = "") => { if (ui) { ui.status.textContent = main; ui.sub.textContent = sub; } document.body.dataset.state = S.phase; };
const hush = () => say("");
/** "20:00" → "8 pm", "19:30" → "7:30 pm": the sticky note is in a kid's words. */
const clock = (hm) => { const [h, m] = String(hm || "0:0").split(":").map(Number); const h12 = ((h + 11) % 12) + 1; return `${h12}${m ? ":" + String(m).padStart(2, "0") : ""} ${h < 12 ? "am" : "pm"}`; };
const later = (name, ms, fn) => { clearTimeout(S.timers[name]); S.timers[name] = setTimeout(fn, ms); };
const cancel = (...names) => names.forEach((n) => clearTimeout(S.timers[n]));

// ------------------------------------------------------------------ screen

function draw() {
  // The room and the phone in it come from the design system: a drawing, a finger wheel that really turns,
  // a handset that really lifts and trembles when it rings, and things to pick up. We listen to their events.
  root.innerHTML = str(html`${raw(DESK)}
  <div class="ph-wake" id="wake" hidden><div class="tl-card" style="max-width:var(--sheet-max);text-align:center"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Tap to turn the phone on</h2>
    <p class="tl-card__body">Your device needs one tap before it can ring.</p>
    <div class="tl-actions"><button type="button" class="tl-btn tl-btn--primary tl-btn--lg" id="wake-btn"><span class="tl-btn__label">Turn on</span></button></div>
  </div></div></div>`);
  const deskEl = root.querySelector("[data-tl-desk]");
  // What the phone is doing goes on the wall, in the room's slot. The connection is the little light on the
  // phone itself (green: ready; dark: getting online; flashing: ringing); screen readers get it in words.
  deskEl.querySelector(".tl-desk__stage").insertAdjacentHTML("beforeend", str(html`<div class="tl-desk__slot ph__slot">
    <span class="ph__sr" id="reg" role="status"></span>
    <p class="ph__status" id="status" role="status" aria-live="polite"></p>
    <p class="ph__sub" id="sub"></p>
  </div>`));
  const el = deskEl.querySelector("[data-tl-rotary]");
  ui = { status: root.querySelector("#status"), sub: root.querySelector("#sub"),
    reg: root.querySelector("#reg"), wake: root.querySelector("#wake"), el, deskEl,
    hookButton: el.querySelector(".tl-rotary__hook"), number: el.querySelector(".tl-rotary__number"),
    api: window.TreelineUI.rotary(el), desk: window.TreelineUI.desk(deskEl), strings: "" };
  ui.desk.setLinks({ coffee: SUPPORT_URL, email: CONTACT, licenses: "/phone/licenses.html" });
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
    // The phone dials number keys itself when it has focus; this is for when it doesn't (and nothing is picked up).
    if (e.target.closest?.(".tl-rotary__svg") || ui.desk.isOpen()) return;
    if (/^[0-9]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey && !/input|textarea|select/i.test(e.target.tagName)) S.dial?.(Number(e.key));
  }, { signal: life.signal });
  ui.wake.querySelector("#wake-btn").addEventListener("click", async () => { await tones.unlock(); ui.wake.hidden = true; });
  showLine();
  render();
}

/** The words for a hung-up, idle phone: they follow the line's state. */
function idleWords() {
  if (S.line === "disconnected") return ["This phone is switched off"];
  if (S.line === "quiet") return ["The phone is sleeping"];
  return [""];
}

function render() {
  if (!ui) return;
  ui.api.setRinging(S.phase === "ringing");                        // only the handset trembles
  if (ui.number) ui.number.textContent = S.number || "";
  // The kit labels the handset button "Lift the handset"; a ringing phone should say what lifting does.
  if (S.hook === "on" && ui.hookButton) ui.hookButton.setAttribute("aria-label", S.phase === "ringing" ? "Answer the phone" : "Lift the handset");
  if (S.hook === "on" && S.phase === "idle") say(...idleWords());
  document.body.dataset.state = S.phase;
  document.body.dataset.digits = S.digits;
}

/** The room's words from the line: the treehouse's name on the drawing, its quiet hours, its card file. */
function fillRoom(r) {
  if (!ui) return;
  if (r.treehouse) ui.desk.setName(r.treehouse);
  if (r.quiet) ui.desk.setQuiet(r.quiet.enabled ? `${clock(r.quiet.start)} – ${clock(r.quiet.end)}` : "none");
  const cards = JSON.stringify(r.strings || []);
  if (cards !== ui.strings) { ui.strings = cards; ui.desk.setContacts(r.strings || []); }
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
}

// ------------------------------------------------------------------ line state

async function refreshLine() {
  if (!S.creds) return;
  try {
    const r = await api("GET", "/api/line", undefined, { auth: "basic", basic: `${S.creds.sip_user}:${S.creds.secret}` });
    S.line = r.state; if (r.number !== S.number) { S.number = r.number; }
    S.removed = false;
    fillRoom(r);
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
  if (!S.ua || !S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now"); render(); return; }
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
  if (ui?.desk.isOpen()) ui.desk.close();                       // put down the book or card: the phone is ringing
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
  start(await pairScreen(root));
}

// A hook for the browser tests, on this machine only, and without the SIP secret.
if (location.search.includes("test=1") && ["localhost", "127.0.0.1"].includes(location.hostname)) {
  const view = new Proxy(S, { get: (t, k) => (k === "creds" ? undefined : t[k]), set: (t, k, v) => { t[k] = v; return true; } });
  window.__phone = { S: view, render: () => render(), desk: () => ui.desk, tonesLevel: () => tones.effectiveLevel(), lift: () => (ui.api.isOffHook() ? ui.api.hangUp() : ui.api.lift()), dial: (d) => S.dial?.(d), rotary: () => ui.api, tones,
    async stats() { const pc = S.session?.connection; if (!pc) return null; const r = await pc.getStats(); let rx = 0, tx = 0; r.forEach((x) => { if (x.type === "inbound-rtp" && x.kind === "audio") rx += x.bytesReceived; if (x.type === "outbound-rtp" && x.kind === "audio") tx += x.bytesSent; }); return { rx, tx }; } };
}

boot();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/phone/sw.js").catch(() => {});
