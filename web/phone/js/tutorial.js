// "How do I dial?": a short animated lesson that plays on the phone itself.
// It lifts the handset, drops a fingertip into a hole, winds the wheel to the stop, lets it spin back,
// dials a few more numbers and hangs up. The wheel's own sounds come along because the phone listens to
// the wheel turning. Nothing here is dialed: the phone ignores its own events while the lesson runs.
import { button, html, steps, str } from "/shared/ui.js";

const NAMES = ["Lift", "Pick", "Turn", "Let go", "Four numbers"];
const GAP = 30;                         // degrees between holes, and per pulse as the dial returns
const RETURN_SPEED = 295;               // degrees a second: a real dial's pace (same as design/ui/js/treeline.js)
const travel = (d) => GAP * (d === 0 ? 10 : d) + GAP;
const CANCEL = Symbol("cancelled");
const speed = () => window.__tutorialSpeed || 1;          // only the browser tests change this

let run = null;                          // the lesson in progress, if any

export const isRunning = () => !!run;

/** The ten hole centres, read from the drawing itself so the fingertip lands where the picture says. */
function holeCenters(el) {
  const path = el.querySelector(".tlp-wheel path").getAttribute("d");
  const holes = [];
  const re = /M\s*([\d.]+)\s+([\d.]+)\s*a\s*([\d.]+)/g;      // a hole is "M x y a r ...": x is its right edge
  let m;
  while ((m = re.exec(path))) holes.push({ x: +m[1] - +m[3], y: +m[2] });
  return holes;                                              // in the order 1 2 3 4 5 6 7 8 9 0
}

function wheelCentre(el) {
  const m = /rotate\(\s*[-\d.]+\s+([\d.]+)\s+([\d.]+)/.exec(el.querySelector(".tlp-wheel").getAttribute("transform") || "");
  return m ? { x: +m[1], y: +m[2] } : { x: 200, y: 292 };
}

export function stopTutorial() {
  if (!run) return;
  run.cancelled = true;
}

/**
 * Play the lesson. `d` supplies the phone: { ui, S, tones, say, panel, onEnd }.
 * Resolves when it finishes or is stopped.
 */
export async function startTutorial(d) {
  if (run) return;
  const { ui, S, tones, say, panel } = d;
  const me = (run = { cancelled: false });
  const el = ui.el, svg = el.querySelector(".tl-rotary__svg"), wheel = el.querySelector(".tlp-wheel");
  const holes = holeCenters(el), c = wheelCentre(el);
  const finger = document.createElement("div");
  finger.className = "ph__finger";
  ui.glow.appendChild(finger);
  S.tutorial = true;
  el.classList.add("is-tutorial");
  tones.stop();

  const sleep = (ms) => new Promise((resolve, reject) => {
    if (me.cancelled) return reject(CANCEL);
    setTimeout(() => (me.cancelled ? reject(CANCEL) : resolve()), ms / speed());
  });
  /** Run fn(value) from `from` to `to` over `ms`, easing optional. */
  const tween = (from, to, ms, fn, ease = (k) => k) => new Promise((resolve, reject) => {
    const t0 = performance.now(), len = ms / speed();
    const frame = (now) => {
      if (me.cancelled) return reject(CANCEL);
      const k = Math.min(1, len <= 0 ? 1 : (now - t0) / len);
      fn(from + (to - from) * ease(k));
      if (k < 1) requestAnimationFrame(frame); else resolve();
    };
    requestAnimationFrame(frame);
  });
  const easeInOut = (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);

  const setWheel = (a) => wheel.setAttribute("transform", `rotate(${a.toFixed(2)} ${c.x} ${c.y})`);
  /** Where the hole for `digit` is on screen once the wheel has turned `turned` degrees. */
  const holeOnScreen = (digit, turned) => {
    const h = holes[digit === 0 ? 9 : digit - 1], r = (turned * Math.PI) / 180;
    const dx = h.x - c.x, dy = h.y - c.y;
    const p = svg.createSVGPoint();
    p.x = c.x + dx * Math.cos(r) - dy * Math.sin(r);
    p.y = c.y + dx * Math.sin(r) + dy * Math.cos(r);
    const q = p.matrixTransform(svg.getScreenCTM()), box = ui.glow.getBoundingClientRect();
    return { x: q.x - box.left, y: q.y - box.top };
  };
  const placeFinger = (digit, turned) => {
    const p = holeOnScreen(digit, turned);
    finger.style.left = `${p.x}px`; finger.style.top = `${p.y}px`;
  };
  const showFinger = (on) => finger.classList.toggle("is-on", on);

  const step = (n, title, sub) => {
    say(title, sub);
    panel.innerHTML = str(html`${steps(NAMES, n)}<div class="tl-actions"><button type="button" class="tl-btn tl-btn--quiet tl-btn--sm" data-tutorial-stop><span class="tl-btn__label">Stop</span></button></div>`);
    panel.querySelector("[data-tutorial-stop]").addEventListener("click", stopTutorial);
  };

  /** Wind a number round to the stop and hold it there. */
  async function wind(digit, { slow }) {
    placeFinger(digit, 0); showFinger(true);
    await sleep(slow ? 900 : 120);
    await tween(0, travel(digit), slow ? 2600 : 520, (a) => { setWheel(a); placeFinger(digit, a); }, easeInOut);   // the ratchet ticks
    await sleep(slow ? 700 : 120);
  }

  /** Let go: the dial spins back at a real dial's pace, one click per number. */
  async function release(digit, { slow }) {
    const max = travel(digit);
    if (slow) showFinger(false);
    let pulses = 0;
    await tween(max, 0, (max / RETURN_SPEED) * 1000, (a) => {
      setWheel(a);
      if (!slow) placeFinger(digit, a);
      const due = Math.min(digit === 0 ? 10 : digit, Math.floor((max - a) / GAP));
      while (pulses < due) { pulses++; tones.pulseClick(); }
    });
    setWheel(0);
    showFinger(false);
  }

  try {
    step(1, "Lift the handset", "Tap the handset. Then listen for the dial tone.");
    await sleep(900);
    ui.api.setHook(true, true);                       // lifts, without telling the phone it's a real call
    tones.click();
    await sleep(1300);
    tones.play("dial");
    await sleep(2200);
    tones.stop();

    step(2, "Pick a number", "Put a finger in the number's hole. This one is a 4.");
    placeFinger(4, 0); showFinger(true);
    await sleep(2400);

    step(3, "Turn it to the metal stop", "Turn the wheel clockwise, the way the numbers read, until your finger hits the metal stop.");
    await wind(4, { slow: true });

    step(4, "Let go", "Take your finger away. The dial spins back on its own. Wait until it's home before the next number.");
    await release(4, { slow: true });
    await sleep(1400);

    step(5, "Dial all four numbers", "Do the same for each number of your friend's number. A 0 takes nearly all the way round.");
    for (const n of [4, 7, 0]) { await wind(n, { slow: false }); await release(n, { slow: false }); await sleep(450); }
    await sleep(900);
    say("Hang up when you're done", "Put the handset back. Dialing four numbers calls your friend.");
    await sleep(1800);
  } catch (e) {
    if (e !== CANCEL) throw e;
  } finally {
    // Put everything back the way a quiet phone is.
    me.cancelled = true;
    tones.stop();
    setWheel(0);
    finger.remove();
    ui.api.setHook(false, true);
    el.classList.remove("is-tutorial");
    S.tutorial = false;
    run = null;
    panel.innerHTML = "";
    d.onEnd?.();
  }
}
