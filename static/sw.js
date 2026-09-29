/* Chisme service worker: caches the app shell and the last-loaded news/weather
   so the app opens (and shows the last saved data) without a connection. */
const VERSION = "chisme-v14";
const SHELL_CACHE = `${VERSION}-shell`;
const DATA_CACHE = `${VERSION}-data`;
const SHELL = [
  "/",
  "/manifest.webmanifest",
  "/static/style.css",
  "/static/app.js",
  "/static/vendor/leaflet/leaflet.css",
  "/static/vendor/leaflet/leaflet.js",
  "/static/vendor/leaflet/images/layers.png",
  "/static/vendor/leaflet/images/layers-2x.png",
  "/static/icons/header-icon.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/favicon-32.png",
  "/static/icons/favicon.ico",
  "/static/icons/apple-touch-icon.png",
];
const API_TIMEOUT_MS = 10000;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("timeout")), ms);
    promise.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

// Mark a cached API response so the page can say "showing saved copy".
async function markOffline(resp) {
  const headers = new Headers(resp.headers);
  headers.set("X-Chisme-Offline", "1");
  return new Response(await resp.blob(), { status: resp.status, statusText: resp.statusText, headers });
}

// Saved copies are stored per full URL (lat/lon included) and also under the bare path as
// "latest", so an offline open still shows the last location's data.
async function apiNetworkFirst(request) {
  const cache = await caches.open(DATA_CACHE);
  const url = new URL(request.url);
  const latestKey = url.origin + url.pathname;
  const cacheable = !url.pathname.startsWith("/api/geocode");
  try {
    const resp = await withTimeout(fetch(request), API_TIMEOUT_MS);
    if (resp.ok && cacheable) {
      await cache.put(request, resp.clone());
      await cache.put(latestKey, resp.clone());
    }
    return resp;
  } catch (err) {
    const hit = (await cache.match(request)) || (cacheable && await cache.match(latestKey));
    if (hit) return markOffline(hit);
    return new Response(JSON.stringify({ error: "You're offline and nothing is saved yet." }),
      { status: 503, headers: { "Content-Type": "application/json", "X-Chisme-Offline": "1" } });
  }
}

async function pageNetworkFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const resp = await withTimeout(fetch(request), API_TIMEOUT_MS);
    if (resp.ok) await cache.put("/", resp.clone());
    return resp;
  } catch (err) {
    return (await cache.match("/")) || Response.error();
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(SHELL_CACHE);
  const hit = await cache.match(request);
  const net = fetch(request).then((resp) => {
    if (resp.ok) cache.put(request, resp.clone());
    return resp;
  }).catch(() => null);
  return hit || (await net) || Response.error();
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // map tiles, thumbnails, NWS icons: straight to network
  if (url.pathname.startsWith("/api/")) { event.respondWith(apiNetworkFirst(req)); return; }
  if (req.mode === "navigate") { event.respondWith(pageNetworkFirst(req)); return; }
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    event.respondWith(staleWhileRevalidate(req));
  }
});
