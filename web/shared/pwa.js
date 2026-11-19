// One installable app for the parent dashboard and the softphone. This holds what both modes share: which mode this device is in, whether
// it is installed, which kind of device it is, and the install prompt.
export const PHONE_KEY = "treeline.phone";      // the softphone's sign-in, present when this device is a phone
export const TOKEN_KEY = "treeline.token";      // a parent's session, present when a parent is signed in

const read = (k) => { try { return localStorage.getItem(k); } catch { return null; } };

/** This device's softphone sign-in, or null. */
export function phoneCreds() { try { return JSON.parse(read(PHONE_KEY)); } catch { return null; } }
export const isPhone = () => !!phoneCreds();
export const loggedIn = () => !!read(TOKEN_KEY);

/** Where the installed app opens: the phone if this device is one, else the dashboard if a parent is signed in, else the first screen. */
export const appHome = () => (isPhone() ? "/phone/" : loggedIn() ? "/parent/" : "/phone/");

const localTest = () => ["localhost", "127.0.0.1"].includes(location.hostname);

/** Running as an installed app (from the Home Screen), not in a browser tab. */
export function isStandalone() {
  if (localTest() && sessionStorage.getItem("treeline.test.standalone") === "1") return true;      // for the browser tests, on this machine only
  return ["standalone", "fullscreen", "minimal-ui"].some((m) => matchMedia(`(display-mode: ${m})`).matches) || navigator.standalone === true;
}

/** An installed app that is a phone is locked to the phone: a parent code is needed to leave it. In a browser tab nothing is locked. */
export const lockedToPhone = () => isStandalone() && isPhone();

export function platform(ua = navigator.userAgent, touchPoints = navigator.maxTouchPoints || 0) {
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && touchPoints > 1)) return "ios";     // (an iPad asks for the desktop site)
  if (/Android/.test(ua)) return "android";
  return "other";
}

/** Register the app's one service worker, and retire the old per-app ones from before the two apps were joined. */
export async function registerApp() {
  if (!("serviceWorker" in navigator)) return null;
  try {
    for (const r of await navigator.serviceWorker.getRegistrations()) if (new URL(r.scope).pathname !== "/") await r.unregister();
    return await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch { return null; }
}

// The install prompt (Android and desktop Chrome). iPhones and iPads have none: they use Share, then Add to Home Screen.
let deferred = null;
const listeners = new Set();
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; listeners.forEach((f) => f()); });
window.addEventListener("appinstalled", () => { deferred = null; listeners.forEach((f) => f()); });
export const canPromptInstall = () => !!deferred;
export async function promptInstall() {
  if (!deferred) return false;
  const ev = deferred; deferred = null;
  ev.prompt();
  const choice = await ev.userChoice;
  listeners.forEach((f) => f());
  return choice && choice.outcome === "accepted";
}
export function onInstallChange(f) { listeners.add(f); return () => listeners.delete(f); }
