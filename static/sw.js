/* Chisme service worker: caches the app shell and the last-loaded news/weather
   so the app opens instantly (and shows the last saved data) even when the server is asleep
   or there's no connection. */
const VERSION = "chisme-v19";
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
// Texas art & landmark photos shown between stories (~2 MB): precached best-effort so they work offline.
const ART = ["/static/art/art.json", ...Array.from({ length: 13 }, (_, i) => `/static/art/${String(i + 1).padStart(2, "0")}.webp`)];
// Only cache real Chisme responses (the server marks them), never a hosting "waking up" page.
const ours = (resp) => resp && resp.ok && resp.headers.get("X-Chisme") === "1";

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const c = await caches.open(SHELL_CACHE);
    // cache: "reload" skips the HTTP cache, so a new version never precaches yesterday's app.js
    await Promise.all(SHELL.map(async (u) => {
      const resp = await fetch(new Request(u, { cache: "reload" }));
      if (!ours(resp)) throw new Error("bad shell response for " + u);
      await c.put(u, resp);
    }));
    await Promise.allSettled(ART.map(async (u) => {
      const resp = await fetch(new Request(u, { cache: "reload" }));
      if (ours(resp)) await c.put(u, resp);
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

// Mark a cached API response so the page can say "showing saved copy".
async function markOffline(resp) {
  const headers = new Headers(resp.headers);
  headers.set("X-Chisme-Offline", "1");
  return new Response(await resp.blob(), { status: resp.status, statusText: resp.statusText, headers });
}

// API: network first with NO short timeout — a sleeping free server can take ~50 s to answer,
// and the page already shows the saved copy meanwhile (it reads the cache itself). The saved
// copy is only returned here when the network actually fails. Copies are stored per full URL
// (lat/lon included) and under the bare path as "latest" for an offline first open.
async function apiNetworkFirst(request) {
  const cache = await caches.open(DATA_CACHE);
  const url = new URL(request.url);
  const latestKey = url.origin + url.pathname;
  const cacheable = !url.pathname.startsWith("/api/geocode");
  try {
    const resp = await fetch(request);
    if (ours(resp) && cacheable && /json/.test(resp.headers.get("content-type") || "")) {
      await cache.put(request, resp.clone());
      await cache.put(latestKey, resp.clone());
    }
    return resp;
  } catch (err) {
    if (request.signal && request.signal.aborted) throw err;
    const hit = (await cache.match(request)) || (cacheable && await cache.match(latestKey));
    if (hit) return markOffline(hit);
    return new Response(JSON.stringify({ error: "You're offline and nothing is saved yet." }),
      { status: 503, headers: { "Content-Type": "application/json", "X-Chisme-Offline": "1" } });
  }
}

// Pages: the cached app shell opens instantly (no waiting on a sleeping server). New versions
// arrive through a service worker update (precached above), so HTML and JS always match.
async function pageCacheFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  const hit = await cache.match("/");
  if (hit) return hit;
  try {
    const resp = await fetch(request);
    if (ours(resp)) await cache.put("/", resp.clone());
    return resp;
  } catch (err) {
    return Response.error();
  }
}

// Static files: this version's shell straight from cache (it only changes with a new service
// worker, so HTML, JS and CSS always match); anything else stale-while-revalidate.
async function staticCacheFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  const path = new URL(request.url).pathname;
  const hit = await cache.match(request, { ignoreSearch: true });
  if (hit && (SHELL.includes(path) || ART.includes(path))) return hit;
  const net = fetch(request, { cache: "no-cache" }).then((resp) => {
    if (ours(resp)) cache.put(request, resp.clone());
    return resp;
  }).catch(() => null);
  return hit || (await net) || Response.error();
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // map tiles, thumbnails, NWS icons: straight to network
  if (url.pathname === "/sw.js") return;
  if (url.pathname.startsWith("/api/")) { event.respondWith(apiNetworkFirst(req)); return; }
  if (req.mode === "navigate") { event.respondWith(pageCacheFirst(req)); return; }
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    event.respondWith(staticCacheFirst(req));
  }
});
