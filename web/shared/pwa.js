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
  try { if (localTest() && sessionStorage.getItem("treeline.test.standalone") === "1") return true; } catch { /* storage blocked: not a test */ }   // for the browser tests, on this machine only
  return ["standalone", "fullscreen", "minimal-ui"].some((m) => matchMedia(`(display-mode: ${m})`).matches) || navigator.standalone === true;
}

/** A device that is a phone is locked to the phone, in the installed app and in any browser tab: the dashboard and every other page send it
 *  back to the phone, so a new tab is no way out. Only the parent code, on the phone, ends phone mode (see leavePhoneMode in phone.js). */
export const lockedToPhone = () => isPhone();

export function platform(ua = navigator.userAgent, touchPoints = navigator.maxTouchPoints || 0) {
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && touchPoints > 1)) return "ios";     // (an iPad asks for the desktop site)
  if (/Android/.test(ua)) return "android";
  return "other";
}

/** Which kind of device and browser this is, so the install steps can name the right buttons.
 *  os: "ios" | "android" | "other". browser: safari, chrome, firefox, edge, samsung, opera or other. inApp: inside another app's own browser
 *  (Facebook, Instagram, a webview...), which can't install anything. tablet: an iPad, or an Android that isn't "Mobile". */
export function device(ua = navigator.userAgent, touchPoints = navigator.maxTouchPoints || 0) {
  const os = platform(ua, touchPoints);
  const inApp = /FBAN|FBAV|FB_IAB|Instagram|Snapchat|TikTok|MicroMessenger|Line\/|; wv\)/.test(ua) || (os === "ios" && !/Safari|CriOS|FxiOS|EdgiOS|OPiOS/.test(ua));
  let browser = "other";
  if (os === "ios") browser = /CriOS/.test(ua) ? "chrome" : /FxiOS/.test(ua) ? "firefox" : /EdgiOS/.test(ua) ? "edge" : /OPiOS/.test(ua) ? "opera" : "safari";
  else if (os === "android") browser = /SamsungBrowser/.test(ua) ? "samsung" : /EdgA/.test(ua) ? "edge" : /OPR|OPT\//.test(ua) ? "opera" : /Firefox/.test(ua) ? "firefox" : /Chrome/.test(ua) ? "chrome" : "other";
  const tablet = os === "ios" ? /iPad/.test(ua) || /Macintosh/.test(ua) : os === "android" && !/Mobile/.test(ua);
  return { os, browser, inApp, tablet };
}

export const MOVED_PUSH_KEY = "treeline.push.moved";     // endpoints of alert subscriptions that belonged to a retired worker

/** Register the app's one service worker, and retire the old per-app ones from before the two apps were joined.
 *  Unregistering a worker removes its push subscription, so each one is noted first: the dashboard re-subscribes this device under the
 *  new worker and tells the server to drop the old endpoint (see carryOverPush), and a parent's alerts do not stop. */
export async function registerApp() {
  if (!("serviceWorker" in navigator)) return null;
  try {
    for (const r of await navigator.serviceWorker.getRegistrations()) {
      if (new URL(r.scope).pathname === "/") continue;
      try {
        const sub = await r.pushManager.getSubscription();
        if (sub) {
          const moved = new Set(JSON.parse(localStorage.getItem(MOVED_PUSH_KEY) || "[]"));
          moved.add(sub.endpoint);
          localStorage.setItem(MOVED_PUSH_KEY, JSON.stringify([...moved]));
        }
      } catch { /* no push here, or storage blocked */ }
      await r.unregister();
    }
    return await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch { return null; }
}

/** A phone or a tablet (an iPad that asks for the desktop site counts). Computers are not: the install page is for devices that
 *  can hold the app on a Home Screen, and a computer can just use the browser. */
export const isMobileOrTablet = () => platform() !== "other";

// "Use Treeline in your browser instead": remembered for this visit only, so the install page comes back next time.
let browserChosen = false;
export const chooseBrowser = () => { browserChosen = true; try { sessionStorage.setItem("treeline.use.browser", "1"); } catch { /* blocked: the variable holds it */ } };
export const usingBrowser = () => { try { return browserChosen || sessionStorage.getItem("treeline.use.browser") === "1"; } catch { return browserChosen; } };

/** Should a device that isn't a phone yet be asked to install the app first? Only a phone or tablet in a browser tab, and only until it picks the browser. */
export const showInstallPage = () => !isStandalone() && isMobileOrTablet() && !usingBrowser();

// The install prompt (Android and desktop Chrome). iPhones and iPads have none: they use Share, then Add to Home Screen.
let deferred = null;
const listeners = new Set();
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; listeners.forEach((f) => f()); });
let installed = false;
window.addEventListener("appinstalled", () => { deferred = null; installed = true; listeners.forEach((f) => f()); });
export const justInstalled = () => installed;
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
