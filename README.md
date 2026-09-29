# Chisme

**Chisme** (Spanish slang for gossip, or the neighborhood news) is a local news + weather app for **ZIP 78211: South Side, San Antonio, TX**.
It uses large, bold, high-contrast text, and it's an **installable phone app (PWA)** that opens full-screen and still works offline.

* **Weather:** current conditions from the nearest NWS station (usually Kelly Field, KSKF), the next 12 hours, a 7-day forecast (NWS grid EWX 124,51) and **active NWS alerts** for the 78211 point. Alerts appear as red banners at the top.
* **Live rain radar:** a Leaflet map centered on 78211 with OpenStreetMap tiles and RainViewer radar. It loops through the past ~2 hours of 10-minute frames and has play/pause, back/forward and a slider.
* **Local news:** RSS from San Antonio newsrooms. Stories that mention South Side places go under **Near 78211** and get tags like `Harlandale` or `Port San Antonio`. Everything else goes under **San Antonio**.
* **Auto-refresh:** weather + radar every 10 min, news every 15 min. It also refreshes when you return to the app if the data is stale.
* **Installable and offline:** a web app manifest, an icon set and a service worker. The last-loaded news and weather are saved on the phone and shown with an "offline, saved copy" banner when there's no signal.
* A−/A+ buttons change the text size (saved on the device).

No API keys are needed. All data is live, with nothing made up.

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
| `APP_USER_AGENT` | `Chisme/1.0 (...)` | User-Agent sent to api.weather.gov and the feeds. **NWS asks for contact info**, e.g. `Chisme/1.0 (you@example.com)` |

## Install Chisme on your phone

Installing needs **HTTPS**, so deploy it first (see [Deploy](#deploy)). Render and Fly both give you an `https://…` address automatically. (`http://localhost` counts as secure for testing on a computer, but a phone on your Wi-Fi hitting `http://192.168.x.x:8211` won't be allowed to install.)

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

**Offline:** once you've opened Chisme with a connection, the service worker keeps the app itself plus the latest news and weather. With no signal you'll see that saved copy and a yellow "You're offline" banner. The radar needs a live connection.

## How it works

`app.py` is a small FastAPI server. It exists because RSS feeds block browser CORS and because browsers can't set the `User-Agent` header that NWS requires.

| endpoint | what | server cache |
| --- | --- | --- |
| `GET /` | the single-page app (`static/index.html`, `app.js`, `style.css`; Leaflet is bundled in `static/vendor`) | – |
| `GET /manifest.webmanifest` | PWA manifest (name, turquoise theme `#00C9CD`, icons, screenshots, shortcuts) | – |
| `GET /sw.js` | service worker, served from the root so it covers the whole site | – |
| `GET /api/weather` | `/points/29.35,-98.56` → forecast, hourly forecast, latest observation (nearest station, with fallback), `/alerts/active?point=…` | 5 min |
| `GET /api/news` | fetches all feeds in parallel, cleans them up, drops duplicates by headline, classifies Near 78211 vs San Antonio | 10 min |
| `GET /api/radar` | RainViewer `weather-maps.json` (list of frames) | 2 min |
| `GET /healthz` | health check | – |

If an upstream request fails, the server keeps serving the last good copy. A feed that fails is skipped and listed as unavailable under "News sources" at the bottom of the page.

**Service worker (`static/sw.js`):**
* **Pre-caches the app shell** (page, CSS, JS, Leaflet, icons).
* `/api/*` is **network-first**: it waits up to 10 s, stores the response, and falls back to the saved copy marked `X-Chisme-Offline`.
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

| Source | Feed |
| --- | --- |
| KSAT 12 | `https://www.ksat.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml` |
| KENS 5 | `https://www.kens5.com/feeds/syndication/rss/news/local` (times out with a Chrome-style User-Agent; works with the app's UA) |
| San Antonio Report | `https://sanantonioreport.org/feed/` |
| Texas Public Radio | `https://www.tpr.org/news.rss` |
| News 4 San Antonio (WOAI) | `https://news4sanantonio.com/news/local.rss` (FOX San Antonio's feed carries the same stories, so it isn't used) |
| San Antonio Current | `https://sacurrent.com/sanantonio/Rss.xml` |
| Express-News | Has no public RSS (old `/rss/feed/*.php` URLs return 404). Pulled through a Google News RSS search, `site:expressnews.com/news when:3d` |
| South Side searches | 3 short Google News RSS searches for South Side terms, last 14 days. A result is kept **only if its headline** matches a local term. |

Near-78211 terms (regexes in `LOCAL_TERMS` in `app.py`): 78211, South Side / south-side, South San, Harlandale, Palm Heights, Nogalitos, Zarzamora, Commerce/Zarzamora, SW Military, Military Dr, Kelly Field/KellyUSA, Port San Antonio, Quintana Rd, Somerset Rd, Southcross, Pleasanton Rd, Frio City Rd, Stinson, Palo Alto College, South Park Mall, Cassiano, Villa Coronado, Southwest ISD. Obituaries and MaxPreps roster pages are filtered out. To add feeds, edit `FEEDS`.

## Checks

```bash
./venv/bin/pip install playwright            # uses system Chrome at /usr/bin/google-chrome
./venv/bin/python shoot.py                   # desktop 1280x900 + phone 390x844 screenshots + radar/news/forecast checks
./venv/bin/python pwa_check.py               # manifest + Chrome installability errors, SW control, offline reload, install/iOS UI
npx lighthouse@11 http://localhost:8211/ --only-categories=pwa,accessibility,best-practices   # v11 still has the PWA category
```

Last run (2026-09-29, about 4:28 AM CT):
* Chrome `Page.getInstallabilityErrors`: **none**.
* Lighthouse 11: **PWA 100, Accessibility 100, Best Practices 100** (report in `screenshots/lighthouse.report.html`).
* Offline reload kept all news and the forecast.

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

* **Radar resolution:** RainViewer's free tiles stop at **zoom 7** (higher zooms return a "Zoom Level Not Supported" image). Leaflet stretches the zoom-7 image (`maxNativeZoom: 7`), so the radar gets blocky at neighborhood scale. There are no nowcast frames right now. The radar isn't available offline.
* **OpenStreetMap tiles:** `tile.openstreetmap.org` is fine for personal use but has a [usage policy](https://operations.osmfoundation.org/policies/tiles/). For a public, high-traffic deployment, use a tile provider.
* **Express-News and South Side search** results come through Google News RSS. Their links go through `news.google.com` redirects, they have no thumbnails, and Google could rate-limit or change the format. Some articles are paywalled.
* **"Near 78211" is keyword-based.** It can miss stories that don't name a place. It can also pick up nearby South Side stories outside 78211 (Southeast Side, Brooks) and South San ISD sports scores.
* **Current conditions** come from the nearest airport station and are usually 30–60 minutes old.
* **iOS:** there's no automatic install prompt (Apple doesn't allow one), only the Share → Add to Home Screen hint. iOS may clear saved offline data for a home-screen app that hasn't been opened in a few weeks.
* The Android install button only appears when Chrome decides the app is installable (HTTPS, not already installed). Headless tests confirm the page has **no installability errors** and that the button calls Chrome's prompt, but a real phone install still has to be done by hand after deploying.
