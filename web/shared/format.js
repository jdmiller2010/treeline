// Dates, times and small words, in the voice the design system asks for:
// "7:30 pm" with a lowercase am/pm, digits for numbers, sentence case.

export function time12(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "pm" : "am";
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${suffix}`;
}

export function plural(n, one, many) { return `${n} ${n === 1 ? one : (many || one + "s")}`; }

export function minutesText(m) {
  if (m == null) return "No limit";
  if (m < 60) return `${Number.isInteger(m) ? m : m.toFixed(1)} min`;
  const h = Math.floor(m / 60), r = Math.round(m % 60);
  return r ? `${h} h ${r} min` : plural(h, "hour");
}

function parts(date, tz) {
  const f = new Intl.DateTimeFormat("en-US", { timeZone: tz, year: "numeric", month: "numeric", day: "numeric" });
  const [mo, d, y] = f.format(date).split("/").map(Number);
  return { y, mo, d };
}

/** "Today, 4:12 pm", "Yesterday, 3:40 pm", "Nov 12, 3:40 pm" in the treehouse's time zone. */
export function when(iso, tz) {
  if (!iso) return "";
  const date = new Date(iso);
  const clock = new Intl.DateTimeFormat("en-US", { timeZone: tz, hour: "numeric", minute: "2-digit" })
    .format(date).replace(/\s?([AP])M/, (_, a) => " " + a.toLowerCase() + "m");
  const now = new Date();
  const a = parts(date, tz), b = parts(now, tz);
  const dayNum = (p) => Date.UTC(p.y, p.mo - 1, p.d) / 86400000;
  const diff = dayNum(b) - dayNum(a);
  if (diff === 0) return `Today, ${clock}`;
  if (diff === 1) return `Yesterday, ${clock}`;
  const day = new Intl.DateTimeFormat("en-US", { timeZone: tz, month: "short", day: "numeric" }).format(date);
  return `${day}, ${clock}`;
}

export function relative(iso) {
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 90) return "just now";
  if (secs < 3600) return `${Math.round(secs / 60)} min ago`;
  if (secs < 86400) return `${Math.round(secs / 3600)} h ago`;
  return `${Math.round(secs / 86400)} days ago`;
}

export function initials(name) {
  const w = String(name || "?").replace(/['’]s\b.*$/, "").trim().split(/\s+/).filter(Boolean);
  return ((w[0] || "?")[0] + (w.length > 1 ? w[w.length - 1][0] : "")).toUpperCase();
}

export const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const DAY_LETTERS = ["M", "T", "W", "T", "F", "S", "S"];

export function quietSummary(q) {
  return `${time12(q.start)} to ${time12(q.end)}`;
}

export function daysSummary(days) {
  if (days === "1111111") return "Every night";
  if (days === "0000000") return "No days";
  return DAY_NAMES.filter((_, i) => days[i] === "1").join(", ");
}

/** "4821" -> "4821". Numbers are four digits; kept as text so a leading zero survives. */
export const fmtNumber = (n) => String(n || "");
