// Keeps the phone's own files available offline. The API and WebSocket are never cached.
const CACHE = "treeline-phone-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then((res) => {
    // Only whole, successful pages and files: a partial (206) response can't be cached.
    if (res.status === 200 && res.type === "basic") { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})); }
    return res;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
