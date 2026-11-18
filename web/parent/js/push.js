// Notifications on this device (Web Push). Email always works; this adds a nudge on the phone or tablet.
import { ApiError, del, get, post } from "/shared/api.js";

const b64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));

/** One of: unsupported, unconfigured, denied, on, off. */
export async function pushState() {
  if (!("serviceWorker" in navigator && "PushManager" in window && "Notification" in window)) return "unsupported";
  try { await get("/api/push/key"); } catch (e) { if (e instanceof ApiError && e.status === 404) return "unconfigured"; throw e; }
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration("/parent/");
  const sub = reg && (await reg.pushManager.getSubscription());
  return sub ? "on" : "off";
}

export async function enablePush() {
  const { key } = await get("/api/push/key");
  if ((await Notification.requestPermission()) !== "granted") throw new Error("Notifications are blocked for this site. Allow them in your browser's settings and try again.");
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) });
  await post("/api/push/subscribe", sub.toJSON());
}

export async function disablePush() {
  const reg = await navigator.serviceWorker.getRegistration("/parent/");
  const sub = reg && (await reg.pushManager.getSubscription());
  if (!sub) return;
  await del("/api/push/subscribe", { endpoint: sub.endpoint });
  await sub.unsubscribe();
}
