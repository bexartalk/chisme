# Chisme

**Chisme** (Spanish slang for gossip, or the neighborhood news) is a local news + weather app for **wherever you are**. It uses your phone's location and shows the place it found in the header, e.g. **📍 Near: South San, San Antonio**.
It uses large, bold, high-contrast text, and it's an **installable phone app (PWA)** that opens full-screen and still works offline.

* **Your location:** uses the browser Geolocation API. Before the browser's permission prompt appears, a friendly card explains why Chisme wants your location. The last location is saved on the device (`localStorage` key `chisme-location`), so the app opens straight to it. While the app is open it watches your position (`watchPosition`) and reloads everything when you've moved **more than ~3 km**. It also re-checks every time the app is opened or brought back to the front. The **📍 Near: … Change** pill in the header lets you switch places any time.
* **No location? No problem.** If location is denied, unavailable, or the page isn't on HTTPS, Chisme shows **San Antonio, TX** as the default ("Default: San Antonio, TX") plus a **city or ZIP search box**. Searches are geocoded through the backend. Pick a result and it's remembered on the device.
* **Weather:** current conditions from the nearest NWS observation station, the next 12 hours, a 7-day forecast and **active NWS alerts for your exact point**. Alerts appear as red banners at the top. Times are shown in the location's own time zone.
* **Outside the U.S.:** the National Weather Service only covers the U.S. and its territories. For other places Chisme says so clearly, and the radar and news keep working.
* **Live rain radar:** a Leaflet map centered on you with a **"You are here"** marker and a **📍 Recenter** button. It uses OpenStreetMap tiles plus RainViewer radar, loops through the past ~2 hours of 10-minute frames, and has play/pause, back/forward and a slider.
* **Local news, ranked by distance:** **Near You** lists stories that name your neighborhood or nearby neighborhoods first, then your city, then your county. Each story has tags like `South San` or `Downtown` / `Austin`. The rest of your city's news goes under **More {city} news**. When you're outside San Antonio, a collapsible **San Antonio headlines** section keeps the SA newsrooms handy.
* **Auto-refresh:** weather + radar every 10 min, news every 15 min, and when you return to the app if the data is stale.
* **Installable and offline:** manifest, icon set and service worker. The **last location's** news and weather are saved on the phone and shown with an "offline, saved copy" banner when there's no signal.
* A−/A+ buttons change the text size (saved on the device).

No API keys are needed. All data is live, with nothing made up.

> **Geolocation needs a secure page.** Browsers only allow `navigator.geolocation` on **HTTPS** or **`http://localhost`**. If you open Chisme from another device on your Wi-Fi (e.g. `http://192.168.1.20:8211`), the browser blocks location. Chisme notices this, explains it, and offers the city/ZIP search instead. Deploy behind HTTPS (Render, Fly and Caddy do this automatically) to get live location on a phone.

## Run locally

```bash
cd chisme
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8211
# open http://localhost:8211
```

Or run `./run.sh [port]`. It creates the venv if needed, (re)starts the server in the background, and writes `server.pid` and `server.log`.

| env var | default | purpose |
| --- | --- | --- |
| `PORT` | 8211 | port for `python app.py` / `run.sh` (hosts like Render/Fly set it for you) |
| `APP_USER_AGENT` | `Chisme/1.0 (...)` | User-Agent sent to api.weather.gov, Nominatim and the feeds. **NWS and Nominatim both ask for contact info**, e.g. `Chisme/1.0 (you@example.com)` |
| `NOMINATIM_URL` | `https://nominatim.openstreetmap.org` | geocoder base URL. Point it at your own Nominatim (or a hosted one) for heavier use |

## Install Chisme on your phone

Installing (and live location) need **HTTPS**, so deploy it first (see [Deploy](#deploy)). Render and Fly both give you an `https://…` address automatically. (`http://localhost` counts as secure for testing on a computer, but a phone on your Wi-Fi hitting `http://192.168.x.x:8211` won't be allowed to install.)

**iPhone / iPad (Safari):**
1. Open your Chisme address (e.g. `https://chisme.onrender.com`) in **Safari**.
2. Tap the **Share** button (square with an arrow ↑) at the bottom of the screen.
3. Scroll down and tap **Add to Home Screen**, then **Add**.
4. Open Chisme from the turquoise icon. It runs full-screen like an app.

The app shows a short reminder card on iPhone with these steps. Tap ✕ to hide it.

**Android (Chrome):**
1. Open your Chisme address in **Chrome**.
2. Tap the orange **Install** button in the "Get the Chisme app" card (on bigger screens it's in the header). You can also use Chrome's menu ⋮ → **Install app** / **Add to Home screen**.
3. Confirm. Chisme shows up in your app drawer and on your home screen.

**Desktop Chrome/Edge:** click **📲 Install** in the header, or the install icon in the address bar.

**Offline:** once you've opened Chisme with a connection, the service worker keeps the app itself plus the latest news and weather **for the last location you viewed**. With no signal you'll see that saved copy and a yellow "You're offline" banner. The radar needs a live connection.

## How it works

`app.py` is a small FastAPI server. It exists because RSS feeds block browser CORS, because browsers can't set the `User-Agent` header that NWS and Nominatim require, and so geocoding can be cached and rate-limited in one place. Every data endpoint takes `lat` and `lon`. Caches are keyed by a **rounded grid cell** (0.01°, about 1 km), so nearby users and small GPS jitter share cached results.

| endpoint | what | server cache |
| --- | --- | --- |
| `GET /` | the single-page app (`static/index.html`, `app.js`, `style.css`; Leaflet is bundled in `static/vendor`) | – |
| `GET /manifest.webmanifest` | PWA manifest (name, turquoise theme `#00C9CD`, icons, screenshots, shortcuts) | – |
| `GET /sw.js` | service worker, served from the root so it covers the whole site | – |
| `GET /api/place?lat&lon` | reverse geocode (Nominatim `/reverse`, zoom 16). Returns `label` ("South San, San Antonio"), neighborhood, city, county, state, country, ZIP and a list of **nearby neighborhoods** with distances | 7 days per cell |
| `GET /api/geocode?q=` | city/ZIP search for the manual fallback. A 5-digit ZIP is looked up as a U.S. postal code; anything else is a free-text search. Up to 5 results | 30 days |
| `GET /api/weather?lat&lon` | NWS `/points/{lat},{lon}` (per cell, 24 h) → forecast + hourly (per NWS grid), latest observation (nearest station, with fallback), `/alerts/active?point=…` (per cell). Outside NWS coverage it returns `supported:false` and a message | 5 min, alerts 3 min |
| `GET /api/news?lat&lon` | builds the feed list for the place (below), fetches it in parallel, cleans it up, drops near-duplicate headlines, and ranks it | 10 min per feed |
| `GET /api/radar` | RainViewer `weather-maps.json` (list of frames) | 2 min |
| `GET /healthz` | health check | – |

If an upstream request fails, the server keeps serving the last good copy. A feed that fails is skipped and listed as unavailable under "News sources" at the bottom of the page.

**Geocoding (Nominatim / OpenStreetMap):** requests follow the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). They send an identifying `User-Agent`, are serialized to **at most 1 request per second**, and every result is cached. Place data © OpenStreetMap contributors (ODbL). The neighborhood list comes from the reverse-geocode result plus a few extra reverse lookups around the point. San Antonio's neighborhoods aren't mapped as areas in OSM, so `data/sa_neighborhoods.json` adds a small gazetteer of **40 SA neighborhoods/landmarks** (Harlandale, Palm Heights, Nogalitos, Port San Antonio, Southtown, Alamo Heights, …). Any within 5 km count as "nearby". It was built with `tools/build_sa_gazetteer.py`.

**News ranking ("Near You"):**
1. **Neighborhood tier:** the headline or summary names your neighborhood or a nearby one (closest first), or your ZIP. Common names like "Downtown" or "Midtown" only count if the city is also named. Within the SA newsrooms' feeds, the city is implied when you're in San Antonio.
2. **City tier:** names your city (e.g. "Austin", but not "Austin College").
3. **County tier:** names your county.

Near You shows up to 18 neighborhood stories, filled with city/county stories up to 30, newest first within each tier. **South Side boost:** only when you're on San Antonio's South Side, the classic South Side word list (South Side, South San, Harlandale, Palm Heights, Nogalitos, Zarzamora, SW Military, Kelly Field, Port San Antonio, Southcross, Pleasanton Rd, Palo Alto College, South Park Mall, …) also counts as neighborhood tier, and two extra South Side searches are added.

**Service worker (`static/sw.js`):**
* **Pre-caches the app shell** (page, CSS, JS, Leaflet, icons).
* `/api/*` is **network-first**: it waits up to 10 s and stores the response. When offline it falls back to the saved copy for that exact location, or else the **last location's** copy, marked `X-Chisme-Offline`. Geocode searches aren't cached.
* Pages are network-first with the cached shell as fallback. Static files use stale-while-revalidate.
* Cross-origin requests (map/radar tiles, news thumbnails, NWS icons) always go to the network.
* When you change front-end files, bump `VERSION` in `sw.js` so phones pick up the update.

### App icon

Icons are built from the chosen artwork, `assets/chisme-icon-original.png`: a turquoise rounded square with a black "Chisme" speech bubble and pink/orange confetti. `tools/make_icons.py` fills the white outside the rounded corners with the icon's own turquoise (sampled from the artwork: `#00C9CD`), so there's no white rim. It then exports these to `static/icons/`:

| file | use |
| --- | --- |
| `icon-192.png`, `icon-512.png` | manifest icons (`purpose: any`) |
| `maskable-192.png`, `maskable-512.png` | Android adaptive icons: artwork padded with turquoise so the bubble is inside the 80% safe zone |
| `apple-touch-icon.png` (180×180) | iPhone home screen |
| `favicon.ico` (16/32/48), `favicon-32.png` | browser tab |
| `header-icon.png` | logo in the app header |

Re-run with `./venv/bin/pip install pillow numpy scipy && ./venv/bin/python tools/make_icons.py`.

Theme: turquoise header (`#00C9CD`), black type, hot pink `#EF426F` and orange `#FF8200` accents (papel picado strip, map marker, install button).

### News sources (verified 2026-09-29)

Always included (San Antonio newsrooms):

| Source | Feed |
| --- | --- |
| KSAT 12 | `https://www.ksat.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml` |
| KENS 5 | `https://www.kens5.com/feeds/syndication/rss/news/local` (times out with a Chrome-style User-Agent; works with the app's UA) |
| San Antonio Report | `https://sanantonioreport.org/feed/` |
| Texas Public Radio | `https://www.tpr.org/news.rss` |
| News 4 San Antonio (WOAI) | `https://news4sanantonio.com/news/local.rss` |
| San Antonio Current | `https://sacurrent.com/sanantonio/Rss.xml` |
| Express-News | No public RSS. Pulled through a Google News RSS search, `site:expressnews.com/news when:3d` |

**Dynamic local searches** (Google News RSS `https://news.google.com/rss/search?q=…`), built for the detected place so Chisme works in any city:

| search | query | when |
| --- | --- | --- |
| city | `"{city}" {state} when:3d` | outside San Antonio (the SA feeds already cover SA) |
| county | `"{county}" {state} when:7d` | always |
| neighborhoods | `"{neighborhood}" "{city}" when:30d` for the 2 closest specific neighborhoods | always |
| downtown/midtown… | `"Downtown {city}" when:14d` | when the nearest name is generic |
| South Side | 2 searches for South Side SA terms, last 14 days | only on SA's South Side |

For the "strict" searches (county, neighborhood, South Side), a result is kept only if its **headline** names the place. Obituaries, social-media posts and roster pages are filtered out. Feeds are listed in `SA_FEEDS` / `feeds_for()` in `app.py`.

## Checks

```bash
./venv/bin/pip install playwright            # uses system Chrome at /usr/bin/google-chrome
./venv/bin/python shoot.py                   # desktop 1280x900 + phone 390x844 screenshots + radar/news/forecast checks
./venv/bin/python location_test.py           # geolocation: South Side SA, Austin, moving, permission denied + manual search, Paris
./venv/bin/python pwa_check.py               # manifest + Chrome installability errors, SW control, offline reload, install/iOS UI
npx lighthouse@11 http://localhost:8211/ --only-categories=pwa,accessibility,best-practices   # v11 still has the PWA category
```

Last run (2026-09-29, about 5:02 AM CT):
* Chrome `Page.getInstallabilityErrors`: **none**.
* Lighthouse 11: **PWA 100, Accessibility 100, Best Practices 100** (report in `screenshots/lighthouse.report.html`).
* Offline reload kept all news and the forecast.
* `location_test.py`: South Side SA → "Near: South San, San Antonio"; Austin → "Near: Downtown, Austin" (also via watchPosition when moving); denied → default San Antonio + search ("Houston, TX", ZIP 78211 → South San); Paris → clear non-US weather message. No page errors.

## Deploy

The app is one stateless Python process with an in-memory cache. Both options below give you HTTPS, which the phone install needs.

**Render:**
1. Push this folder to a GitHub repo.
2. In Render, choose **New → Blueprint** and pick the repo. It reads `render.yaml`: service `chisme`, build `pip install -r requirements.txt`, start `uvicorn app:app --host 0.0.0.0 --port $PORT`, health check `/healthz`.
3. Set `APP_USER_AGENT` to include your email.
4. Open `https://chisme.onrender.com` (or whatever URL Render shows) on your phone and install it as described above.

Free instances sleep when idle, so the first open after a nap takes a few seconds. After you've installed it, the saved copy shows right away.

**Fly.io:** uses the included `Dockerfile` and `fly.toml` (app `chisme`, region `dfw`):
```bash
fly launch --copy-config --no-deploy   # pick a unique app name if "chisme" is taken
fly secrets set APP_USER_AGENT="Chisme/1.0 (you@example.com)"
fly deploy
# → https://<app>.fly.dev
```

**Any Docker host** (Railway, Cloud Run, a VPS behind Caddy for automatic HTTPS):
```bash
docker build -t chisme . && docker run -p 8080:8080 -e APP_USER_AGENT="Chisme/1.0 (you@example.com)" chisme
```

**Vercel:** can run FastAPI as a Python serverless function, but each cold function starts with an empty cache, so Render or Fly is a better fit.

## Limitations

* **Geolocation needs HTTPS or localhost.** On plain `http://` from another device, the browser refuses, and Chisme falls back to the city/ZIP search. iOS Safari asks again in some situations, and the in-app "Use my location" button re-requests it. If you've blocked location for the site, it has to be re-allowed in browser/phone settings.
* **Nominatim is rate-limited (1 request/second) and shared.** The first visit to a new ~1 km area makes a few lookups (place + nearby neighborhoods), so the first load there can take **~5–8 s**. After that it's cached. For a busy public deployment, use your own or a commercial geocoder (`NOMINATIM_URL`).
* **Neighborhood names are approximate.** OSM has few neighborhood boundaries in Texas cities, so "Near:" uses the nearest named place from Nominatim, which can be a subdivision name or the ZIP's area. San Antonio uses the built-in gazetteer's *points*, not boundaries. The Overpass API (for full neighborhood polygons) wasn't reachable from the build box, so it isn't used.
* **"Near You" is keyword-based.** It can miss stories that don't name a place, and it can match a different place with the same name. Common names are guarded by requiring the city too, but some false positives remain (e.g. a story about a "Downtown Austin" altercation involving San Marcos officials).
* **Google News RSS** results (Express-News and all dynamic searches) link through `news.google.com` redirects, often have no thumbnails, and Google could rate-limit or change the format. Some articles are paywalled.
* **NWS is U.S.-only.** Outside the U.S. (and in some offshore spots) there's no forecast, observation or alerts, only a clear message. Radar coverage outside the U.S. depends on RainViewer.
* **Radar resolution:** RainViewer's free tiles stop at **zoom 7** (higher zooms return a "Zoom Level Not Supported" image). Leaflet stretches the zoom-7 image (`maxNativeZoom: 7`), so the radar gets blocky at neighborhood scale. The radar isn't available offline.
* **OpenStreetMap tiles:** `tile.openstreetmap.org` is fine for personal use but has a [usage policy](https://operations.osmfoundation.org/policies/tiles/). For a public, high-traffic deployment, use a tile provider.
* **Offline** shows only the **last location's** saved data. Moving to a new place while offline keeps showing the old place until you're back online.
* **Current conditions** come from the nearest airport station and are usually 30–60 minutes old.
* **iOS:** there's no automatic install prompt (Apple doesn't allow one), only the Share → Add to Home Screen hint. iOS may clear saved offline data for a home-screen app that hasn't been opened in a few weeks.
* The Android install button only appears when Chrome decides the app is installable (HTTPS, not already installed). A real phone install still has to be done by hand after deploying.
