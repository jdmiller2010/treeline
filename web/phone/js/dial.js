// The rotary phone: art, and a finger wheel you really turn.
import { click } from "./tones.js";

const NS = "http://www.w3.org/2000/svg";
const CX = 180, CY = 292;                 // the dial's centre in the 360 x 470 drawing
const STOP = 120;                         // the finger stop, degrees clockwise from 12 o'clock
const HOLE_R = 92;
const DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0];

/** Where a digit's hole rests (degrees clockwise from 12) and how far it must turn to reach the stop. */
const pulses = (d) => (d === 0 ? 10 : d);
export const holeAngle = (d) => 90 - 30 * pulses(d);
export const travel = (d) => 30 * pulses(d) + 30;      // 1 turns 60 degrees; 0 turns 330

const rad = (deg) => (deg * Math.PI) / 180;
const polar = (deg, r) => [CX + r * Math.sin(rad(deg)), CY - r * Math.cos(rad(deg))];

function svgEl(name, attrs = {}, text) {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text != null) e.textContent = text;
  return e;
}

/** Build the phone. Returns the elements the page needs to drive. */
export function buildPhone(number) {
  const svg = svgEl("svg", { viewBox: "0 0 360 470", class: "rp", role: "group", "aria-label": "Rotary phone" });

  // The body, in warm wood.
  svg.append(svgEl("path", { class: "rp-body", d: "M40 150 Q180 120 320 150 Q352 300 330 430 Q180 456 30 430 Q8 300 40 150Z" }));
  svg.append(svgEl("ellipse", { class: "rp-sheen", cx: 150, cy: 180, rx: 90, ry: 20 }));

  // The cradle and handset.
  svg.append(svgEl("path", { class: "rp-cradle", d: "M70 112 q-14 -10 -6 -30 h232 q8 20 -6 30 q-110 14 -220 0Z" }));
  const handset = svgEl("g", { class: "rp-handset", id: "handset", role: "button", tabindex: "0", "aria-pressed": "false", "aria-label": "Handset, on the hook. Lift it to make a call." });
  handset.append(svgEl("path", { class: "rp-handset-body", d: "M52 74 q-6 -34 22 -34 q20 0 26 14 q60 12 160 0 q6 -14 26 -14 q28 0 22 34 q-4 22 -24 20 q-14 -2 -18 -14 q-90 8 -156 0 q-4 12 -18 14 q-20 2 -24 -20Z" }));
  handset.append(svgEl("path", { class: "rp-handset-shine", d: "M110 60 q70 6 140 0" }));
  svg.append(handset);

  // The number plate under the holes: numbers stay still while the wheel turns.
  svg.append(svgEl("circle", { class: "rp-plate", cx: CX, cy: CY, r: 134 }));
  for (const d of DIGITS) {
    const [x, y] = polar(holeAngle(d), HOLE_R);
    svg.append(svgEl("text", { class: "rp-digit", x, y: y + 7, "text-anchor": "middle" }, String(d)));
  }

  // The finger wheel: a ring with ten holes cut out of it.
  const wheel = svgEl("g", { class: "rp-wheel", id: "wheel" });
  const holes = DIGITS.map((d) => { const [x, y] = polar(holeAngle(d), HOLE_R); return `M${x + 21} ${y}a21 21 0 1 0 -42 0a21 21 0 1 0 42 0Z`; }).join("");
  const ring = `M${CX + 124} ${CY}a124 124 0 1 0 -248 0a124 124 0 1 0 248 0Z M${CX + 50} ${CY}a50 50 0 1 1 -100 0a50 50 0 1 1 100 0Z`;
  wheel.append(svgEl("path", { class: "rp-ring", "fill-rule": "evenodd", d: ring + holes }));
  for (const d of DIGITS) {
    const [x, y] = polar(holeAngle(d), HOLE_R);
    wheel.append(svgEl("circle", { class: "rp-hole", cx: x, cy: y, r: 26, "data-digit": d, tabindex: "0", role: "button", "aria-label": `Dial ${d}` }));
  }
  svg.append(wheel);

  // The finger stop, which does not turn.
  const [sx, sy] = polar(STOP, 134);
  svg.append(svgEl("path", { class: "rp-stop", d: `M${sx - 4} ${sy - 14}q22 -4 22 18q-2 14 -14 18q6 -14 -8 -26Z` }));

  // The number card in the middle.
  svg.append(svgEl("circle", { class: "rp-card", cx: CX, cy: CY, r: 44 }));
  svg.append(svgEl("text", { class: "rp-number", x: CX, y: CY + 7, "text-anchor": "middle", id: "rp-number" }, number || ""));
  return { svg, wheel, handset };
}

/**
 * Make the wheel work. `onDigit(d)` is called as the dial returns home, the
 * way a real one sends its pulses. Returns { dial(d) } so a keyboard can dial too.
 */
export function attachDial(svg, wheel, { enabled, onDigit }) {
  let drag = null;
  let spinning = false;
  const setAngle = (deg) => wheel.setAttribute("transform", `rotate(${deg} ${CX} ${CY})`);

  const pointAngle = (e) => {
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    return (Math.atan2(p.x - CX, -(p.y - CY)) * 180) / Math.PI;
  };

  /** Return home at a steady speed, ticking once per pulse. */
  function spinBack(from, digit, done) {
    spinning = true;
    const ms = Math.max(180, (from / 300) * 1000);
    const t0 = performance.now();
    const n = pulses(digit);
    let ticks = 0;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const step = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      setAngle(from * (1 - k));
      const due = Math.floor(k * n);
      while (ticks < due) { ticks++; click(0.25); }
      if (k < 1 && !reduce) requestAnimationFrame(step);
      else { setAngle(0); spinning = false; done?.(); }
    };
    requestAnimationFrame(step);
  }

  wheel.addEventListener("pointerdown", (e) => {
    const hole = e.target.closest(".rp-hole");
    if (!hole || spinning || !enabled()) return;
    const d = Number(hole.dataset.digit);
    drag = { d, last: pointAngle(e), turned: 0, max: travel(d) };
    svg.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const now = pointAngle(e);
    let delta = now - drag.last;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    drag.last = now;
    drag.turned = Math.max(0, Math.min(drag.max, drag.turned + delta));   // clockwise only, up to the stop
    setAngle(drag.turned);
  });
  const release = () => {
    if (!drag) return;
    const { d, turned, max } = drag;
    drag = null;
    const reached = turned >= max - 14;
    spinBack(turned, d, reached ? () => onDigit(d) : null);
  };
  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);

  const dial = (d) => {
    if (spinning || !enabled()) return false;
    setAngle(0);
    // A keyboard dials by turning the wheel all the way, then letting it go.
    const max = travel(d); const t0 = performance.now(); const ms = 350;
    spinning = true;
    const out = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      setAngle(max * k);
      if (k < 1) requestAnimationFrame(out);
      else { spinning = false; spinBack(max, d, () => onDigit(d)); }
    };
    requestAnimationFrame(out);
    return true;
  };

  // Holes can be reached from the keyboard too.
  wheel.addEventListener("keydown", (e) => {
    const hole = e.target.closest?.(".rp-hole");
    if (hole && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); dial(Number(hole.dataset.digit)); }
  });
  return { dial, busy: () => spinning || !!drag };
}
