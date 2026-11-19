// The Treeline app's one service worker (the parent dashboard and the softphone are one installable app).
// It keeps the app's own files available offline, and shows notifications from Web Push:
//   - kind "call": a call is waiting for a softphone that was asleep. Shown until someone taps it; tapping opens the phone.
//   - anything else: an alert for a parent (a 911 attempt, a phone offline, a string to approve); tapping opens the dashboard.
// The API is never cached: a call log must be live.
const CACHE = "treeline-app-v2";

self.addEventListener("install", () => { self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  e.respondWith(
    fetch(e.request).then((res) => {
      // Only whole, successful pages and files: a partial (206) response can't be cached.
      if (res.status === 200 && res.type === "basic") { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})); }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});

self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data.json(); } catch { /* plain text */ }
  const call = data.kind === "call";
  e.waitUntil(self.registration.showNotification(data.title || (call ? "Incoming call" : "Treeline"), {
    body: data.body || "",
    icon: "/ui/logo/exports/app-icon-192.png", badge: "/ui/logo/exports/favicon-32.png",
    tag: data.tag || (call ? "treeline-call" : "treeline"),
    data: { kind: data.kind || "alert", url: data.url || (call ? "/phone/" : "/parent/#/home") },
    // A call waits for someone, so it stays until tapped, buzzes again if another one replaces it, and vibrates like a ring.
    requireInteraction: call, renotify: call, vibrate: call ? [400, 200, 400, 200, 400] : undefined,
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const { kind, url } = e.notification.data || {};
  e.waitUntil((async () => {
    const wins = await clients.matchAll({ type: "window", includeUncontrolled: true });
    const onPhone = wins.find((w) => new URL(w.url).pathname.startsWith("/phone/"));
    // A call goes to the phone. An alert never takes a phone away from the phone: it just brings it forward.
    if (onPhone && (kind === "call" || !url.startsWith("/phone/"))) { await onPhone.focus(); return; }
    const open = wins[0];
    if (open && kind !== "call") { await open.focus(); if ("navigate" in open) await open.navigate(url).catch(() => {}); return; }
    await clients.openWindow(url);
  })());
});
