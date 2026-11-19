// Retired: the parent dashboard and the softphone are now one app with one service worker, /sw.js. This stub removes the old
// registration on a device that installed the earlier version.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.registration.unregister()));
