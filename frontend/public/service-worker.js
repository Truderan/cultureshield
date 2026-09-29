const CACHE_NAME = "cultureshield-v2";
const BASE = new URL(self.registration.scope).pathname;
const APP_SHELL = ["", "index.html", "manifest.json", "icon-192.svg", "icon-512.svg"].map((file) => BASE + file);

const isCacheableRequest = (request) => {
  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  const isApiRequest = sameOrigin && url.pathname.startsWith("/api");
  const hasAuthHeader = request.headers.has("authorization");
  const isStaticDestination = ["style", "script", "image", "font"].includes(request.destination);
  const isShellFile = sameOrigin && APP_SHELL.includes(url.pathname);

  return sameOrigin && !isApiRequest && !hasAuthHeader && (isStaticDestination || isShellFile);
};

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  if (!isCacheableRequest(event.request)) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse.ok) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});