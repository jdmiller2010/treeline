// Notifications on this device (Web Push). Email always works; this adds a nudge on the phone or computer.
import { ApiError, del, get, post } from "/shared/api.js";
import { MOVED_PUSH_KEY } from "/shared/pwa.js";

const b64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));

/** One of: unsupported, unconfigured, denied, on, off. */
export async function pushState() {
  if (!("serviceWorker" in navigator && "PushManager" in window && "Notification" in window)) return "unsupported";
  try { await get("/api/push/key"); } catch (e) { if (e instanceof ApiError && e.status === 404) return "unconfigured"; throw e; }
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration("/");
  const sub = reg && (await reg.pushManager.getSubscription());
  if (!sub) return "off";
  // The browser keeps its subscription when someone signs out. Tie it to whoever is signed in
  // now, so a shared device's alerts go to the right person.
  await post("/api/push/subscribe", sub.toJSON()).catch(() => {});
  return "on";
}

export async function enablePush() {
  const { key } = await get("/api/push/key");
  if ((await Notification.requestPermission()) !== "granted") throw new Error("Notifications are blocked for this site. Allow them in your browser's settings and try again.");
  await subscribeThisDevice(key);
}

async function subscribeThisDevice(key) {
  key = key || (await get("/api/push/key")).key;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) });
  await post("/api/push/subscribe", sub.toJSON());
}

/** A parent who had alerts on before the two apps were joined: the old worker's subscription went with it. Subscribe this device again
 *  (permission was already given, so nothing is asked), and tell the server to forget the old endpoint. Tries again next time if it cannot. */
export async function carryOverPush() {
  let moved = [];
  try { moved = JSON.parse(localStorage.getItem(MOVED_PUSH_KEY) || "[]"); } catch { return false; }
  if (!moved.length) return false;
  if (!("Notification" in window) || Notification.permission !== "granted") { try { localStorage.removeItem(MOVED_PUSH_KEY); } catch { /* fine */ } return false; }
  try {
    await subscribeThisDevice();
    for (const endpoint of moved) await del("/api/push/subscribe", { endpoint }).catch(() => {});
    localStorage.removeItem(MOVED_PUSH_KEY);
    return true;
  } catch { return false; }
}

/** Quietly forget this device's subscription (when signing out). */
export async function forgetPushQuietly() {
  try { await disablePush(); } catch { /* signing out regardless */ }
}

export async function disablePush() {
  const reg = await navigator.serviceWorker.getRegistration("/");
  const sub = reg && (await reg.pushManager.getSubscription());
  if (!sub) return;
  await del("/api/push/subscribe", { endpoint: sub.endpoint });
  await sub.unsubscribe();
}
