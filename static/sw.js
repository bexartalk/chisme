/* Chisme service worker: caches the app shell and the last-loaded news/weather
   so the app opens instantly (and shows the last saved data) even when the server is asleep
   or there's no connection. */
const VERSION = "chisme-v39";
const BUILD = VERSION.replace("chisme-v", "");          // index.html asks for app.js?v=<BUILD>
const SHELL_CACHE = `${VERSION}-shell`;
const DATA_CACHE = `${VERSION}-data`;
const SHELL = [
  "/",
  "/manifest.webmanifest",
  `/static/style.css?v=${BUILD}`,
  `/static/foryou.js?v=${BUILD}`,
  `/static/newsorder.js?v=${BUILD}`,
  `/static/donatelines.js?v=${BUILD}`,
  `/static/juegos.js?v=${BUILD}`,
  `/static/icebebe.js?v=${BUILD}`,
  `/static/app.js?v=${BUILD}`,
  "/static/vendor/leaflet/leaflet.css",
  "/static/vendor/leaflet/leaflet.js",
  "/static/vendor/leaflet/images/layers.png",
  "/static/vendor/leaflet/images/layers-2x.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/favicon-32.png",
  "/static/icons/favicon.ico",
  "/static/icons/apple-touch-icon.png",
];
// Texas art & landmark photos shown between stories (~2 MB): precached best-effort so they work offline.
const ART = ["/static/art/art.json", ...Array.from({ length: 13 }, (_, i) => `/static/art/${String(i + 1).padStart(2, "0")}.webp`)];
// Freely licensed Commons photos on the Sports tab (~290 KB).
ART.push(...["spurs-arena", "spurs-bluehour", "missions-wolff", "missions-game", "missions-2026"].map((n) => `/static/sports/${n}.webp`));
// Tía Chismosa's avatar + chat header (~85 KB), so her button shows offline too.
// ?art=N changes whenever tools/make_mascot_assets.py rebuilds her (same query in index.html, app.js, juegos.js)
ART.push(...["avatar-64", "avatar-128", "avatar-192", "header-480", "header-960"].map((n) => `/static/mascot/${n}.webp?art=3`));
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
    const old = keys.filter((k) => !k.startsWith(VERSION + "-"));
    await Promise.all(old.map((k) => caches.delete(k)));
    await self.clients.claim();
    // Tell open pages which version now controls them; a page from another build reloads itself
    // once. (WindowClient.navigate() is not used: WebKit can leave that navigation hanging.)
    await tellVersion();
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
  const cacheable = !url.pathname.startsWith("/api/geocode") && !url.pathname.startsWith("/api/reader");
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
  const u = new URL(request.url);
  // Exact match (query included): app.js?v=22 never gets an older build's copy.
  const hit = await cache.match(request);
  if (hit && (SHELL.includes(u.pathname + u.search) || ART.includes(u.pathname))) return hit;
  const net = fetch(request, { cache: "no-cache" }).then((resp) => {
    if (ours(resp)) cache.put(request, resp.clone());
    return resp;
  }).catch(() => null);
  return hit || (await net) || Response.error();
}

async function tellVersion(client) {
  const to = client ? [client] : await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const c of to) { try { c.postMessage({ chismeVersion: VERSION }); } catch (e) {} }
}
self.addEventListener("message", (event) => {
  if (event.data === "chisme-version") event.waitUntil(tellVersion(event.source || null));
});

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

// ---------- Web Push (push.py): "New chisme, grab the tea! ☕" and NWS warnings/watches for your area.
// Tapping a notification opens Chisme itself (never another site): the story opens in the in-app reader.
self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { body: event.data ? event.data.text() : "" }; }
  const opts = { body: d.body || "", tag: d.tag || "chisme", renotify: !!d.tag, icon: "/static/icons/icon-192.png",
    badge: "/static/icons/favicon-32.png", data: { url: d.url || "/" }, requireInteraction: !!d.urgent };
  event.waitUntil(self.registration.showNotification(d.title || "Chisme", opts));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let url;
  try { url = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin); } catch (e) { url = new URL("/", self.location.origin); }
  if (url.origin !== self.location.origin) url = new URL("/", self.location.origin);
  event.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const w = wins.find((c) => new URL(c.url).origin === self.location.origin);
    if (w) {
      try { w.postMessage({ chismeOpen: url.pathname + url.search + url.hash }); } catch (e) {}
      try { return await w.focus(); } catch (e) {}
    }
    return self.clients.openWindow(url.href);
  })());
});
const b64u = (s) => { const p = "=".repeat((4 - s.length % 4) % 4), b = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(b, (c) => c.charCodeAt(0)); };
self.addEventListener("pushsubscriptionchange", (event) => {   // the browser rotated the subscription: keep alerts working
  event.waitUntil((async () => {
    const cfg = await fetch("/api/push/config").then((r) => r.json()).catch(() => null);
    if (!cfg || !cfg.publicKey) return;
    const sub = event.newSubscription || await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u(cfg.publicKey) });
    await fetch("/api/push/renew", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old: event.oldSubscription && event.oldSubscription.endpoint, subscription: sub.toJSON() }) }).catch(() => {});
  })());
});
