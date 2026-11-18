// The sounds of an old phone, made with Web Audio. Frequencies and rhythms are
// the classic North American ones (see docs/PLAN.md, "Sounds").
let ctx = null;
let master = null;
let current = null;       // the tone playing now: { stop() }
let wanted = null;        // the tone someone asked for while the sound was still locked

export function audioReady() { return !!ctx && ctx.state === "running"; }

/** Browsers only allow sound after a tap, so call this from one. */
export async function unlock() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);
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

/** Two sine waves, on and off in a cadence (seconds). cadence = null means steady. */
function dual(f1, f2, cadence, level = 0.18) {
  const out = ctx.createGain(); out.gain.value = 0; out.connect(master);
  const a = osc(f1, 1, out), b = osc(f2, 1, out);
  let timer = null, stopped = false;
  if (!cadence) out.gain.setTargetAtTime(level, ctx.currentTime, 0.01);
  else {
    const [on, off] = cadence;
    const cycle = () => {
      if (stopped) return;
      const t = ctx.currentTime;
      out.gain.cancelScheduledValues(t);
      out.gain.setTargetAtTime(level, t, 0.01);
      out.gain.setTargetAtTime(0, t + on, 0.01);
      timer = setTimeout(cycle, (on + off) * 1000);
    };
    cycle();
  }
  return { stop() {
    stopped = true; clearTimeout(timer);
    const t = ctx.currentTime;
    out.gain.cancelScheduledValues(t); out.gain.setTargetAtTime(0, t, 0.015);
    setTimeout(() => { try { a.o.stop(); b.o.stop(); out.disconnect(); } catch { /* done */ } }, 120);
  } };
}

/** The bell of a phone being called: two clappers, 2 s on and 4 s off. */
function bell() {
  const out = ctx.createGain(); out.gain.value = 0.22; out.connect(master);
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
  const out = ctx.createGain(); out.gain.value = 0; out.connect(master);
  const oscs = [1400, 2060, 2450, 2600].map((f) => osc(f, 0.25, out));
  const t = ctx.currentTime;
  out.gain.setTargetAtTime(0.35, t, 0.2);
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
