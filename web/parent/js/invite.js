// A family's string code that someone opened before they had a treehouse: a QR code they scanned, or a link in a message. It is
// kept on this device for up to 7 days (a string code's own life) so that it fills in the invite box at the beta screen (a string
// code is also a way into the closed beta) and is sent with setup, which strings the new treehouse to that family.
// localStorage, not sessionStorage: signing in with Google or installing the app must not lose it. The server also remembers a
// code claimed at the beta screen, so this is the convenience, not the only copy.
const KEY = "treeline.invite";
const LIFE = 7 * 86400000;
const norm = (c) => String(c || "").replace(/[-\s]/g, "").toUpperCase();

export function rememberInvite(code) {
  const k = norm(code);
  if (!/^[A-Z0-9]{8}$/.test(k)) return;
  try { localStorage.setItem(KEY, JSON.stringify({ code: k, at: Date.now() })); } catch { /* private mode: the server's copy is enough */ }
}

/** The remembered code as ABCD-2345, or "". */
export function pendingInvite() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "null");
    if (v && /^[A-Z0-9]{8}$/.test(v.code) && Date.now() - v.at < LIFE) return `${v.code.slice(0, 4)}-${v.code.slice(4)}`;
    localStorage.removeItem(KEY);
  } catch { /* fine */ }
  return "";
}

export function forgetInvite() {
  try { localStorage.removeItem(KEY); } catch { /* fine */ }
}
