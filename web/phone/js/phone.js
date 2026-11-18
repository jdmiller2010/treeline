// The Treeline rotary phone for a tablet: a real dial, real tones, calls over WebRTC.
import { api } from "/shared/api.js";
import { brand, footer, html, presence, raw, str, tag } from "/shared/ui.js";
import { attachDial, buildPhone } from "./dial.js";
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
  registered: false, line: "idle", number: "", ua: null, timers: {}, iceServers: [], talkBytes: 0,
};
let ui = null;

const say = (main, sub = "") => { if (ui) { ui.status.textContent = main; ui.sub.textContent = sub; } document.body.dataset.state = S.phase; };
const later = (name, ms, fn) => { clearTimeout(S.timers[name]); S.timers[name] = setTimeout(fn, ms); };
const cancel = (...names) => names.forEach((n) => clearTimeout(S.timers[n]));

// ------------------------------------------------------------------ screen

function draw() {
  const { svg, wheel, handset } = buildPhone(S.number);
  root.innerHTML = str(html`<main class="ph">
    <div class="ph__top">${brand("#")}<span id="reg"></span></div>
    <div class="ph__stage"><div class="ph__glow" id="glow"></div></div>
    <p class="ph__status" id="status" role="status" aria-live="polite"></p>
    <p class="ph__sub body" id="sub"></p>
    <div class="ph__night" id="night"></div>
    <div class="ph__bottom">
      <p class="caption ph__911">Can't call 911 or outside numbers.</p>
      ${footer("/phone/licenses.html")}
    </div>
  </main>
  <div class="ph-wake" id="wake" hidden><div class="tl-card" style="max-width:var(--sheet-max);text-align:center"><div class="tl-stack tl-stack--group">
    <h2 class="tl-card__title">Tap to turn the phone on</h2>
    <p class="tl-card__body">Your tablet needs one tap before it can ring.</p>
    <div class="tl-actions"><button type="button" class="tl-btn tl-btn--primary tl-btn--lg" id="wake-btn"><span class="tl-btn__label">Turn on</span></button></div>
  </div></div></div>`);
  root.querySelector("#glow").appendChild(svg);
  ui = { glow: root.querySelector("#glow"), status: root.querySelector("#status"), sub: root.querySelector("#sub"),
    night: root.querySelector("#night"), reg: root.querySelector("#reg"), wake: root.querySelector("#wake"), svg, wheel, handset };
  const dialer = attachDial(svg, wheel, { enabled: () => S.hook === "off" && ["dialtone", "dialing"].includes(S.phase), onDigit });
  S.dial = dialer.dial;
  handset.addEventListener("click", toggleHook);
  handset.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleHook(); } });
  document.addEventListener("keydown", (e) => {
    if (/^[0-9]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey && !/input|textarea|select/i.test(e.target.tagName)) S.dial?.(Number(e.key));
  });
  ui.wake.querySelector("#wake-btn").addEventListener("click", async () => { await tones.unlock(); ui.wake.hidden = true; });
  setRegistration();
  render();
}

function render() {
  if (!ui) return;
  ui.svg.classList.toggle("is-off", S.hook === "off");
  ui.svg.parentElement.classList.toggle("is-off", S.hook === "off");
  ui.handset.setAttribute("aria-pressed", String(S.hook === "off"));
  ui.handset.setAttribute("aria-label", S.hook === "off" ? "Handset, lifted. Put it back to hang up." : S.phase === "ringing" ? "Handset, ringing. Lift it to answer." : "Handset, on the hook. Lift it to make a call.");
  ui.glow.classList.toggle("is-ringing", S.phase === "ringing");
  const n = root.querySelector("#rp-number"); if (n) n.textContent = S.number || "";
  ui.night.innerHTML = S.line === "quiet" && S.hook === "on"
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
  forgetPhone(); stopUa();
  tones.stop();
  pairScreen(root, "This tablet was removed from its treehouse. Add it again to keep using it.").then((c) => start(c));
}

// ------------------------------------------------------------------ hook

async function toggleHook() {
  await tones.unlock();
  ui.wake.hidden = true;
  if (S.hook === "on") lift(); else hangUp();
}

async function lift() {
  S.hook = "off"; S.digits = "";
  tones.stop();
  if (S.incoming) { answer(); return; }
  // Use what we knew, then check: the line may have changed since we last asked.
  S.phase = "dialtone"; render();
  decideLift(S.line);
  const before = S.line;
  await refreshLine();
  if (S.hook === "off" && S.phase === "dialtone" && S.line !== before) decideLift(S.line);
}

/** What to do the moment the handset comes up, given the line's state. */
function decideLift(state) {
  cancel("howl", "inter", "after");
  if (!S.registered) { S.phase = "busy"; tones.play("fastbusy"); say("Can't connect right now", "The phone is still getting online."); render(); return; }
  if (state === "quiet") { S.phase = "sleep"; tones.play("fastbusy"); say("The phone is sleeping", "Try again later."); render(); return; }
  if (state === "in_call") { joinCall(); return; }
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
  try {
    const session = S.ua.call(`sip:${number}@${S.creds.server}`, callOptions({
      eventHandlers: {
        progress: () => { if (S.phase === "calling") tones.play("ringback"); },
        accepted: () => { if (S.session) { tones.stop(); S.phase = "talking"; say("Talking", ""); render(); } },
        confirmed: () => { tones.stop(); S.phase = "talking"; say("Talking", ""); render(); },
        failed: (e) => ended(e.cause),
        ended: () => ended("ended"),
      },
    }));
    S.session = session;
    hookAudio(session);
  } catch (e) { ended("error"); }
}

function joinCall() {
  S.phase = "calling"; say("Joining the call", ""); render();
  try {
    const session = S.ua.call(`sip:${JOIN}@${S.creds.server}`, callOptions({
      eventHandlers: { confirmed: () => { S.phase = "talking"; say("Talking", ""); render(); }, failed: (e) => ended(e.cause), ended: () => ended("ended") },
    }));
    S.session = session; hookAudio(session);
  } catch { ended("error"); }
}

/** The other side hung up, or the call failed. A click, a moment of quiet, then dial tone. */
function ended(cause) {
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
  // Off the hook and busy with something else: tell the caller we can't take it.
  if (S.hook === "off" && !["dialtone", "dialing", "howl"].includes(S.phase)) { session.terminate({ status_code: 486 }); return; }
  S.incoming = session;
  hookAudio(session);
  const gone = () => { if (S.incoming === session) { S.incoming = null; if (S.phase === "ringing") { tones.stop(); S.phase = "idle"; say("Lift the handset to make a call", ""); render(); } } };
  session.on("failed", gone);
  session.on("ended", () => { if (S.session === session) ended("ended"); gone(); });
  session.on("confirmed", () => { S.phase = "talking"; say("Talking", ""); render(); });
  if (S.hook === "off") { answer(); return; }
  S.phase = "ringing"; tones.play("bell"); say("Ringing", "Lift the handset to answer."); render();
}

function answer() {
  const session = S.incoming; if (!session) return;
  S.incoming = null; S.session = session;
  tones.stop(); cancel("howl", "inter");
  S.phase = "talking"; say("Talking", ""); render();
  try { session.answer(callOptions()); } catch { ended("error"); }
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
  S.creds = creds; S.hook = "on"; S.phase = "idle"; S.incoming = null; S.session = null;
  try { const cfg = await api("GET", "/api/phone/config", undefined, { auth: "none" }); S.iceServers = cfg.ice_servers || []; } catch { /* LAN needs none */ }
  draw();
  say("Lift the handset to make a call", "");
  startUa();
  refreshLine();
  setInterval(() => { if (S.hook === "on") refreshLine(); }, 15000);
  // Keep the tablet awake: a phone that sleeps can't ring.
  const keepAwake = async () => { try { await navigator.wakeLock?.request("screen"); } catch { /* not allowed here */ } };
  keepAwake(); document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") keepAwake(); });
  // The browser wants one tap before it will make sound.
  if (!(await tones.unlock())) ui.wake.hidden = false;
  document.addEventListener("pointerdown", () => tones.unlock(), { once: true });
  window.addEventListener("pagehide", () => { try { S.session?.terminate(); } catch { /* closing */ } });
}

async function boot() {
  const saved = savedPhone();
  if (saved && saved.sip_user) return start(saved);
  start(await pairScreen(root));
}

if (location.search.includes("test=1")) {
  window.__phone = { S, lift: () => toggleHook(), dial: (d) => S.dial?.(d), tones,
    async stats() { const pc = S.session?.connection; if (!pc) return null; const r = await pc.getStats(); let rx = 0, tx = 0; r.forEach((s) => { if (s.type === "inbound-rtp" && s.kind === "audio") rx += s.bytesReceived; if (s.type === "outbound-rtp" && s.kind === "audio") tx += s.bytesSent; }); return { rx, tx }; } };
}

boot();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/phone/sw.js").catch(() => {});
