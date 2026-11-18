// Keeps the app's own files available offline. The API is never cached: a call log must be live.
const CACHE = "treeline-parent-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request)));
});
self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data.json(); } catch { /* plain text */ }
  e.waitUntil(self.registration.showNotification(data.title || "Treeline", {
    body: data.body || "", icon: "/ui/logo/exports/favicon-48.png", badge: "/ui/logo/exports/favicon-32.png", tag: data.tag || "treeline"
  }));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(clients.openWindow("/parent/#/home"));
});
