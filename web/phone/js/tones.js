// The sounds of an old phone, made with Web Audio. Frequencies and rhythms are
// the classic North American ones (see docs/PLAN.md, "Sounds").
let ctx = null;
let master = null;
let toneBus = null;       // every tone goes through here, so one number sets how loud they all are
let mechBus = null;       // the sounds of the dial's mechanism
let current = null;       // the tone playing now: { stop() }
let wanted = null;        // the tone someone asked for while the sound was still locked
let sink = "";            // the speaker the tones go to ("" = the system's default), where the browser can choose

/** How loud things are. The dial tone was too loud, so the tones sit about 6 dB lower than they did. */
export const LEVELS = { master: 0.5, toneBus: 0.7, mechBus: 1.1, dual: 0.13, bell: 0.16, howler: 0.22 };

/** The amplitude one of a tone's two sine waves ends up at, for tests and for tuning. */
export const effectiveLevel = (kind = "dual") => LEVELS.master * LEVELS.toneBus * LEVELS[kind];

export function audioReady() { return !!ctx && ctx.state === "running"; }

/** Can this browser send the tones to a speaker of our choosing? (AudioContext.setSinkId: Chrome and Edge 110+.) */
export const canChooseSpeaker = () => typeof (window.AudioContext && window.AudioContext.prototype.setSinkId) === "function";

/** Send the tones to this speaker ("" for the system's default). Kept and applied when the sound starts, if it hasn't yet.
 *  Applying the same speaker again also re-opens it, which picks up a system default that changed under us. */
export async function setSink(id) {
  sink = id || "";
  if (!ctx || typeof ctx.setSinkId !== "function") return false;
  try { await ctx.setSinkId(sink); return true; } catch { if (sink) { sink = ""; try { await ctx.setSinkId(""); } catch { /* keep going */ } } return false; }
}

/** Browsers only allow sound after a tap, so call this from one. */
export async function unlock() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = LEVELS.master;
    master.connect(ctx.destination);
    toneBus = ctx.createGain(); toneBus.gain.value = LEVELS.toneBus; toneBus.connect(master);
    mechBus = ctx.createGain(); mechBus.gain.value = LEVELS.mechBus; mechBus.connect(master);
    if (sink) await setSink(sink);
  }
  if (ctx.state !== "running") { try { await ctx.resume(); } catch { /* not yet */ } }
  const ok = ctx.state === "running";
  if (ok && wanted && !current) play(wanted);      // a bell that rang while the tap was pending
  return ok;
}

function osc(freq, gain, dest) {
  const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = freq;
  const g = ctx.createGain(); g.gain.value = gain;
  o.connect(g); g.connect(dest); o.start();
  return { o, g };
}

/** One period of a cadenced tone (the beep, then the gap) as samples: two sine waves with 8 ms edges, so the period starts and ends
 *  in silence. Looped by the browser this is sample-accurate: no timers to drift or jitter, and no reset to hear when it comes round. */
export function cadenceSamples(rate, f1, f2, on, off, level = LEVELS.dual) {
  const n = Math.round((on + off) * rate), burst = Math.round(on * rate), ramp = Math.max(1, Math.round(0.008 * rate));
  const d = new Float32Array(n);
  for (let i = 0; i < burst; i++) {
    const env = Math.min(1, i / ramp, (burst - 1 - i) / ramp);
    d[i] = level * (Math.sin(2 * Math.PI * f1 * i / rate) + Math.sin(2 * Math.PI * f2 * i / rate)) * env;
  }
  return d;
}

/** A cadenced tone (busy, fast busy, ringback): that one period, repeated for as long as it plays. */
function cadenced(f1, f2, [on, off], level) {
  const samples = cadenceSamples(ctx.sampleRate, f1, f2, on, off, level);
  const buf = ctx.createBuffer(1, samples.length, ctx.sampleRate);
  buf.copyToChannel(samples, 0);
  const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
  const out = ctx.createGain(); out.gain.value = 1; src.connect(out); out.connect(toneBus);
  src.start();
  return { stop() {
    const t = ctx.currentTime;
    out.gain.cancelScheduledValues(t); out.gain.setTargetAtTime(0, t, 0.015);
    setTimeout(() => { try { src.stop(); out.disconnect(); } catch { /* done */ } }, 120);
  } };
}

/** Two sine waves, steady (the dial tone) or in a cadence (seconds on, off). */
function dual(f1, f2, cadence, level = LEVELS.dual) {
  if (cadence) return cadenced(f1, f2, cadence, level);
  const out = ctx.createGain(); out.gain.value = 0; out.connect(toneBus);
  const a = osc(f1, 1, out), b = osc(f2, 1, out);
  out.gain.setTargetAtTime(level, ctx.currentTime, 0.01);
  return { stop() {
    const t = ctx.currentTime;
    out.gain.cancelScheduledValues(t); out.gain.setTargetAtTime(0, t, 0.015);
    setTimeout(() => { try { a.o.stop(); b.o.stop(); out.disconnect(); } catch { /* done */ } }, 120);
  } };
}

/** The bell of a phone being called: two clappers, 2 s on and 4 s off. */
function bell() {
  const out = ctx.createGain(); out.gain.value = LEVELS.bell; out.connect(toneBus);
  let timer = null, stopped = false, burst = null;
  const strike = (freq, at) => {
    const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = freq;
    const h = ctx.createOscillator(); h.type = "sine"; h.frequency.value = freq * 2.76;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(1, at + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.045);
    const hg = ctx.createGain(); hg.gain.value = 0.35;
    o.connect(g); h.connect(hg); hg.connect(g); g.connect(out);
    o.start(at); h.start(at); o.stop(at + 0.06); h.stop(at + 0.06);
  };
  const cycle = () => {
    if (stopped) return;
    const t0 = ctx.currentTime + 0.02;
    for (let i = 0; i < 40; i++) strike(i % 2 ? 1480 : 1180, t0 + i * 0.05);   // about 20 strikes a second for 2 s
    timer = setTimeout(cycle, 6000);
  };
  cycle();
  return { stop() { stopped = true; clearTimeout(timer); out.gain.setTargetAtTime(0, ctx.currentTime, 0.02); } };
}

/** The loud off-hook warning: four tones together, then silence. */
function howler() {
  const out = ctx.createGain(); out.gain.value = 0; out.connect(toneBus);
  const oscs = [1400, 2060, 2450, 2600].map((f) => osc(f, 0.25, out));
  const t = ctx.currentTime;
  out.gain.setTargetAtTime(LEVELS.howler, t, 0.2);
  out.gain.setTargetAtTime(0, t + 8, 0.1);
  let done = false;
  const end = () => {
    if (done) return; done = true; clearTimeout(timer);
    out.gain.cancelScheduledValues(ctx.currentTime); out.gain.setTargetAtTime(0, ctx.currentTime, 0.02);
    setTimeout(() => { oscs.forEach((x) => { try { x.o.stop(); } catch { /* done */ } }); out.disconnect(); }, 120);
  };
  const timer = setTimeout(end, 9000);
  return { stop: end };
}

const TONES = {
  dial: () => dual(350, 440, null),
  ringback: () => dual(440, 480, [2, 4]),
  busy: () => dual(480, 620, [0.5, 0.5]),
  fastbusy: () => dual(480, 620, [0.25, 0.25]),
  bell,
  howler,
};

export function play(name) {
  stop();
  wanted = name;
  if (!ctx || ctx.state !== "running") return;
  current = TONES[name]();
  current.name = name;
}

export function stop() {
  wanted = null;
  if (current) { current.stop(); current = null; }
}

export const playing = () => (current ? current.name : null);

/** The click of a handset going back on the hook (or a dial returning). */
export function click(level = 0.5) {
  if (!ctx || ctx.state !== "running") return;
  const n = Math.floor(ctx.sampleRate * 0.012);
  const buf = ctx.createBuffer(1, n, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3);
  const src = ctx.createBufferSource(); src.buffer = buf;
  const g = ctx.createGain(); g.gain.value = level;
  src.connect(g); g.connect(master); src.start();
}

// ---------------------------------------------------------------- the dial's mechanism
// A real dial makes three sounds. Winding it round, a ratchet ticks as the wheel passes each tooth.
// Letting go, a governor spins up and whirrs at a steady pace while the wheel returns, and a pair of
// contacts opens and closes once per number (the sharp clicks you hear as pulses). The wheel ends
// with a soft thunk against its rest.

let noise = null;
const mech = { last: 0, acc: 0, whirr: null };

function noiseBuffer() {
  if (!noise) {
    noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  return noise;
}

/** A short burst of filtered noise: the body of every mechanical click. */
function burst({ freq, q = 1, ms, gain, type = "bandpass", at = ctx.currentTime }) {
  const src = ctx.createBufferSource(); src.buffer = noiseBuffer();
  const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
  const g = ctx.createGain();
  g.gain.setValueAtTime(gain, at);
  g.gain.exponentialRampToValueAtTime(0.0001, at + ms / 1000);
  src.connect(f); f.connect(g); g.connect(mechBus);
  src.start(at, Math.random() * 0.5); src.stop(at + ms / 1000 + 0.01);
}

/** One tooth of the winding ratchet: a dry, light tick, a little different each time. */
function ratchet() {
  burst({ freq: 2300 + Math.random() * 500, q: 2.5, ms: 9, gain: 0.5 + Math.random() * 0.15 });
  burst({ freq: 700, q: 1.5, ms: 14, gain: 0.12 });
}

/** One pulse of the dial's contacts as the wheel returns: a sharper, snappier click than the ratchet. */
export function pulseClick() {
  if (!ctx || ctx.state !== "running") return;
  const t = ctx.currentTime;
  burst({ freq: 3200 + Math.random() * 400, q: 1.2, ms: 5, gain: 0.7, type: "highpass", at: t });
  burst({ freq: 1100, q: 3, ms: 11, gain: 0.35, at: t + 0.004 });                 // the contacts closing again
}

function startWhirr() {
  if (mech.whirr) return;
  const src = ctx.createBufferSource(); src.buffer = noiseBuffer(); src.loop = true;
  const band = ctx.createBiquadFilter(); band.type = "bandpass"; band.frequency.value = 620; band.Q.value = 1.4;
  const g = ctx.createGain(); g.gain.value = 0;
  // The governor's gear teeth chop the sound at a steady rate: a purr, not a hiss.
  const lfo = ctx.createOscillator(); lfo.frequency.value = 52;
  const depth = ctx.createGain(); depth.gain.value = 0.045;
  lfo.connect(depth); depth.connect(g.gain);
  const hum = ctx.createOscillator(); hum.type = "triangle"; hum.frequency.value = 96;
  const humGain = ctx.createGain(); humGain.gain.value = 0.012;
  hum.connect(humGain); humGain.connect(g);
  src.connect(band); band.connect(g); g.connect(mechBus);
  g.gain.setValueAtTime(0, ctx.currentTime);
  g.gain.linearRampToValueAtTime(0.07, ctx.currentTime + 0.06);
  src.start(); lfo.start(); hum.start();
  mech.whirr = { g, stop() {
    const t = ctx.currentTime;
    g.gain.cancelScheduledValues(t); g.gain.setTargetAtTime(0, t, 0.025);
    setTimeout(() => { try { src.stop(); lfo.stop(); hum.stop(); g.disconnect(); } catch { /* done */ } }, 160);
  } };
}

function stopWhirr() { if (mech.whirr) { mech.whirr.stop(); mech.whirr = null; } }

/** The wheel arriving back at rest: a soft, low knock. */
function thunk() {
  const t = ctx.currentTime;
  const o = ctx.createOscillator(); o.type = "sine"; o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(70, t + 0.09);
  const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.5, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.13);
  o.connect(g); g.connect(mechBus); o.start(t); o.stop(t + 0.15);
  burst({ freq: 900, q: 0.8, ms: 25, gain: 0.25, at: t });
}

/**
 * Tell the mechanism where the wheel is (degrees from rest). Called each time the wheel moves:
 * turning forward ticks the ratchet; turning back whirrs, and arriving at rest thunks.
 * `dragging` is true while a finger holds the wheel, which never makes the governor whirr.
 */
export function dialAngle(angle, dragging = false) {
  const delta = angle - mech.last;
  mech.last = angle;
  if (!ctx || ctx.state !== "running" || delta === 0) return;
  if (delta > 0) {
    stopWhirr();
    mech.acc += delta;
    while (mech.acc >= 7.5) { mech.acc -= 7.5; ratchet(); }
    return;
  }
  mech.acc = 0;
  if (dragging) return;
  startWhirr();
  if (angle <= 0.01) { stopWhirr(); thunk(); }
}
