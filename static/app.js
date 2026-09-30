/* Chisme — frontend (location-aware) */
// Build of this file. Must equal the number in sw.js VERSION ("chisme-v22"); the page compares it
// with the build the HTML was served for and reloads once if an old cached app.js got mixed in.
window.CHISME_APP_BUILD = "40";
(() => {
  "use strict";
  const WEATHER_MS = 10 * 60 * 1000;
  const NEWS_MS = 4 * 60 * 1000;          // while the app is open and on screen: check for new stories every 4 min
  const NEWS_FOCUS_MS = 60 * 1000;        // …and when you come back to it (focus / visible), if the last check is over a minute old
  const EVENTS_MS = 30 * 60 * 1000;
  const SPORTS_MS = 5 * 60 * 1000;
  const MOVE_KM = 3;                      // refresh when the user moves farther than this
  const DEFAULT_LOC = { lat: 29.4241, lon: -98.4936, source: "default", label: "San Antonio, TX" };
  const LOC_KEY = "chisme-location";
  const $ = (s) => document.querySelector(s);

  // ---------- helpers
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const k of kids) if (k != null) n.append(k);
    return n;
  };
  // Times use the location's time zone (from NWS) or the device's.
  const DEVICE_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;
  let TZ = DEVICE_TZ;
  let lastWeather = null;
  const rendered = { weather: null, news: null, events: null };  // which location each section is showing
  const tzAbbr = (d = new Date()) => {
    try { return new Intl.DateTimeFormat("en-US", { timeZone: TZ, timeZoneName: "short" }).formatToParts(d).find((p) => p.type === "timeZoneName").value; }
    catch { return ""; }
  };
  const fmt = (d, opts) => new Intl.DateTimeFormat("en-US", { timeZone: TZ, ...opts }).format(d);
  const timeT = (d) => fmt(d, { hour: "numeric", minute: "2-digit" }) + " " + tzAbbr(d);
  const dateTimeT = (d) => fmt(d, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) + " " + tzAbbr(d);
  const ago = (d) => {
    const s = (Date.now() - d.getTime()) / 1000;
    if (s < 90) return "just now";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " hr ago";
    const days = Math.round(s / 86400);
    return days + (days === 1 ? " day ago" : " days ago");
  };
  const cToF = (c) => (c == null ? null : Math.round(c * 9 / 5 + 32));
  const kmhToMph = (k) => (k == null ? null : Math.round(k * 0.621371));
  const compass = (deg) => deg == null ? "" :
    ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"][Math.round(deg / 22.5) % 16];
  const icon = (url, size = "medium") => url && navigator.onLine ? url.replace(/size=\w+/, "size=" + size) : null;
  const kmBetween = (a, b) => {
    const R = 6371, rad = Math.PI / 180;
    const dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };
  const RM_KEY = "chisme-reduce-motion";
  const reducedMotion = () => document.documentElement.classList.contains("reduce-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.addEventListener("error", (e) => { if (e.target.tagName === "IMG" && !e.target.closest(".leaflet-container")) e.target.style.visibility = "hidden"; }, true);

  // Tracks which data came from the service worker's saved copy (network unreachable).
  const offlineFrom = {};
  // A free Render instance can take ~50 s to wake up, then a few seconds to build the news, so
  // requests get a generous timeout (and the saved copy is on screen meanwhile).
  const API_TIMEOUT = 75000;
  async function getJSON(url, { key = url.split("?")[0], timeout = API_TIMEOUT } = {}) {
    const ctl = "AbortController" in window ? new AbortController() : null;
    const t = ctl && setTimeout(() => ctl.abort(), timeout);
    try {
      const r = await fetch(url, { cache: "no-store", signal: ctl && ctl.signal });
      const json = /json/.test(r.headers.get("content-type") || "");
      const j = json ? await r.json().catch(() => null) : null;
      if (!r.ok || !j) throw Object.assign(new Error(j && j.error ? j.error : r.ok || r.status >= 502 ? "the server is waking up" : "HTTP " + r.status), { status: r.status });
      if (r.headers.get("X-Chisme-Offline")) offlineFrom[key] = j.generated || true; else delete offlineFrom[key];
      updateOfflineBanner();
      return j;
    } catch (e) {
      if (e.name === "AbortError") throw new Error("the server took too long to answer");
      if (e instanceof TypeError) throw new Error(navigator.onLine ? "couldn't connect" : "you're offline");
      throw e;
    } finally { clearTimeout(t); }
  }
  // The last good copy the service worker saved for this exact URL (or, first time, for any location).
  async function fromCache(url, anyLocation) {
    if (!("caches" in window)) return null;
    try {
      const u = new URL(url, location.href);
      const r = (await caches.match(u.href)) || (anyLocation ? await caches.match(u.origin + u.pathname) : null);
      const j = r && r.ok ? await r.json() : null;
      return j && !j.error ? j : null;
    } catch { return null; }
  }
  function updateOfflineBanner() {
    const b = $("#offline-banner");
    const saved = Object.values(offlineFrom).filter((v) => typeof v === "number");
    if (!navigator.onLine || saved.length) {
      const when = saved.length ? " No worries — here's your saved chisme from " + dateTimeT(new Date(Math.min(...saved) * 1000)) + "." : "";
      b.textContent = (navigator.onLine ? "📴 Can't reach Chisme right now." : "📴 You're offline.") + when + " We'll refresh as soon as we can.";
      b.hidden = false;
    } else b.hidden = true;
  }
  window.addEventListener("offline", updateOfflineBanner);
  window.addEventListener("online", () => { updateOfflineBanner(); refreshAll(); });

  // ---------- sync: show the saved copy right away, refresh in the background, retry with backoff
  // Status pill under the nav: "Updating…" → (slow) "Waking up the server…" → "✓ Updated 8:45 AM".
  const BACKOFF = [5e3, 15e3, 30e3, 60e3, 120e3, 300e3];
  const secs = {}, Sync = { busy: new Set(), failed: new Map(), lastOk: 0, slow: false, slowT: null, hideT: null };
  const clock = (d) => d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  function syncUI() {
    const box = $("#sync"), msg = $("#sync-msg"), retry = $("#sync-retry");
    clearTimeout(Sync.hideT);
    if (Sync.busy.size) {
      box.dataset.state = "busy"; retry.hidden = true;
      msg.textContent = Sync.slow ? "Waking up the server — this can take up to a minute. Your saved chisme is below." : "Updating…";
    } else if (Sync.failed.size) {
      const f = [...Sync.failed.values()].sort((a, b) => a.at - b.at)[0];
      const s = Math.max(1, Math.round((f.at - Date.now()) / 1000));
      box.dataset.state = "fail"; retry.hidden = false;
      msg.textContent = `Couldn't update (${f.why}). Showing the saved copy; trying again in ${s < 90 ? s + " s" : Math.round(s / 60) + " min"}.`;
    } else if (Sync.lastOk) {
      box.dataset.state = "ok"; retry.hidden = true;
      msg.textContent = "Updated " + clock(new Date(Sync.lastOk));
      Sync.hideT = setTimeout(() => { box.dataset.state = "done"; }, 4000);
    } else { box.dataset.state = "done"; }
    box.hidden = false;
    const note = $("#set-refresh-note");
    if (note) note.textContent = Sync.busy.size ? "Updating…" : Sync.failed.size ? msg.textContent : Sync.lastOk ? "Last updated " + clock(new Date(Sync.lastOk)) + "." : "";
  }
  function setBusy(name, on) {
    if (on) Sync.busy.add(name); else Sync.busy.delete(name);
    if (on && !Sync.slowT && !Sync.slow) Sync.slowT = setTimeout(() => { Sync.slowT = null; if (Sync.busy.size) { Sync.slow = true; syncUI(); } }, 8000);
    if (!Sync.busy.size) { clearTimeout(Sync.slowT); Sync.slowT = null; Sync.slow = false; }
    syncUI();
  }
  // name → { url(), apply(data, {saved}), loading(), fail(err), key }
  function section(name, o) { secs[name] = { seq: 0, tries: 0, timer: null, shownUrl: null, key: o.key || "/api/" + name, ...o }; }
  async function load(name) {
    const s = secs[name], url = s.url(), seq = ++s.seq;
    clearTimeout(s.timer); s.timer = null;
    if (s.shownUrl !== url) {
      const c = await fromCache(url, s.shownUrl == null);
      if (seq !== s.seq) return;
      if (c) { try { s.apply(c, { saved: true }); s.shownUrl = url; } catch (e) { console.warn("saved copy", e); } }
      else s.loading && s.loading();
    }
    setBusy(name, true);
    try {
      const j = await getJSON(url, { key: s.key });
      if (seq !== s.seq) return;
      const saved = !!offlineFrom[s.key];
      if (!(saved && s.shownUrl === url)) { s.apply(j, { saved }); s.shownUrl = url; }
      if (saved) throw Object.assign(new Error(navigator.onLine ? "couldn't reach Chisme" : "you're offline"), { soft: true });
      s.tries = 0; s.okAt = Date.now(); Sync.failed.delete(name); Sync.lastOk = Date.now();
    } catch (e) {
      if (seq !== s.seq) return;
      if (s.shownUrl !== url && s.fail) s.fail(e);
      const d = BACKOFF[Math.min(s.tries++, BACKOFF.length - 1)];
      Sync.failed.set(name, { at: Date.now() + d, why: e.message });
      s.timer = setTimeout(() => load(name), d);
    } finally { if (seq === s.seq) setBusy(name, false); }
  }
  const retryFailed = () => { for (const n of Sync.failed.keys()) load(n); };
  setInterval(() => { if (!Sync.busy.size && Sync.failed.size) syncUI(); }, 5000);  // keep the countdown honest

  // ---------- text size
  const FS_KEY = "chisme-font-px";
  const applyFs = (px) => document.documentElement.style.setProperty("--fs", px + "px");
  const savedFs = +localStorage.getItem(FS_KEY);
  if (savedFs) applyFs(savedFs);
  const curFs = () => parseFloat(getComputedStyle(document.documentElement).fontSize);
  const showFs = () => { const px = Math.round(curFs()); $("#font-now").textContent = `${px} px${px === 19 || px === 21 ? " (default)" : ""}`; };
  const bump = (d) => { const px = Math.min(30, Math.max(16, Math.round(curFs() + d))); applyFs(px); localStorage.setItem(FS_KEY, px); showFs(); map && map.invalidateSize(); };
  $("#font-up").onclick = () => bump(2);
  $("#font-down").onclick = () => bump(-2);

  // ---------- location state
  let loc = (() => { try { const s = JSON.parse(localStorage.getItem(LOC_KEY)); if (s && isFinite(s.lat) && isFinite(s.lon)) return s; } catch {} return { ...DEFAULT_LOC }; })();
  const q = () => `lat=${(+loc.lat).toFixed(3)}&lon=${(+loc.lon).toFixed(3)}`;
  const placeName = () => loc.label || "your area";
  // v39: greetings and chatty lines (Tía, the Events/concert intros, loading quips) name only the city, e.g.
  // "San Antonio", never a neighborhood like "Port San Antonio (Kelly), San Antonio". Settings/alerts keep the full label.
  const greetCity = () => {
    const p = loc.place || {}, c = loc.source === "default" ? "San Antonio" : p.city || (metroOf() && metroOf().city) || p.county || "";
    return String(c).replace(/\s*\([^)]*\)/g, "").split(",")[0].trim() || "your area";
  };
  const shortPlace = () => greetCity();
  function saveLoc() { localStorage.setItem(LOC_KEY, JSON.stringify(loc)); }
  // The home screen asks about location only on first launch. Once a place is set (or the
  // user says "Not now"), location lives only in Settings.
  const SETUP_KEY = "chisme-location-setup";
  const hadSavedPlace = loc.source === "gps" || loc.source === "manual";
  if (hadSavedPlace && !localStorage.getItem(SETUP_KEY)) localStorage.setItem(SETUP_KEY, "1");
  const firstRun = () => !localStorage.getItem(SETUP_KEY);
  const finishSetup = () => { localStorage.setItem(SETUP_KEY, "1"); };
  // Where are we? The server tells us the metro (San Antonio, Houston, Austin, Dallas–Fort Worth, Miami, or none).
  const metroOf = () => (loc.place && loc.place.metro) || null;
  const inSA = () => loc.source === "default" || (metroOf() ? metroOf().id === "sa" : kmBetween(loc, DEFAULT_LOC) < 60);
  const cityName = () => (loc.source === "default" ? "San Antonio" : (metroOf() && metroOf().city) || (loc.place && (loc.place.city || loc.place.county)) || "your area");
  // Header skyline: San Antonio's (Tower of the Americas) for SA, the default and while the place is loading;
  // simple silhouettes for Houston, Austin, Dallas and Miami; a generic skyline anywhere else.
  function renderSkyline() {
    const p = loc.place || {}, m = metroOf();
    const sky = loc.source === "default" ? "sa" : m ? m.skyline : (!p.city && !p.county) ? (kmBetween(loc, DEFAULT_LOC) < 60 ? "sa" : "city") : "city";
    $("#topbar").dataset.skyline = sky;
  }
  function renderLocLabel() {
    renderSkyline();
    const city = loc.place && loc.place.city;
    $("#city-title").textContent = city ? `More ${city} news` : "More local news";
    $("#set-loc-now").textContent = (loc.source === "default" ? "Showing the default: " : loc.source === "gps" ? "Using your location: " : "Showing: ") + placeName();
    renderGreeting();
    if (lastWeather && rendered.weather === q()) renderAlerts(lastWeather);  // keep alert wording in sync
  }
  async function lookupPlace() {
    const forQ = q();
    try {
      const p = await getJSON(`/api/place?${forQ}`);
      if (forQ !== q()) return;  // location changed while we were waiting
      if (p.tz) TZ = p.tz;       // the new place's time zone, before its weather arrives
      loc.place = { neighborhood: p.neighborhood, city: p.city, county: p.county, state: p.state_abbr || p.state, country_code: p.country_code, metro: p.metro || null };
      // manual searches keep their typed label (e.g. a ZIP) unless we have something nicer
      if (loc.source !== "manual" || !loc.label || /^\d{5}/.test(loc.label)) loc.label = p.label || loc.label;
      if (loc.source === "default") loc.label = DEFAULT_LOC.label;
      saveLoc(); renderLocLabel();
    } catch { /* offline: keep the saved label */ }
  }
  async function setLocation(n, source) {
    // Bug fix (v24): picking a city in Settings used to leave the GPS watch running, and its next update
    // (iOS sends them often) switched the app straight back to the phone's position. Manual = GPS off.
    if (source === "manual") stopWatch();
    const moved = kmBetween(loc, n);
    if (moved > 50) TZ = DEVICE_TZ;   // don't label the new city's times with the old city's zone
    loc = { lat: +(+n.lat).toFixed(4), lon: +(+n.lon).toFixed(4), source, label: n.label || null, ts: Date.now() };
    saveLoc(); renderLocLabel();
    finishSetup(); hidePanel();
    if (map) recenter(moved > 50 ? 8 : null);
    refreshAll();          // start loading right away (shows "Loading…" instead of the old place)
    pushResync();          // alerts follow you to the new place
    await lookupPlace();   // then fill in the neighborhood/city label
  }


  // ---------- personality (UI copy only — headlines and story text are never rewritten)
  const pick = (arr) => arr[Math.floor(Date.now() / 36e5) % arr.length];   // changes hourly, stable between renders
  function localHour() { try { return +fmt(new Date(), { hour: "numeric", hourCycle: "h23" }); } catch { return new Date().getHours(); } }
  // Greeting: "¡Buenos días / Buenas tardes / Buenas noches, chismosos!" (plural, for everyone, by the
  // place's time of day). The old chismoso/chismosa choice (v22–v23) is gone; its saved key is cleared.
  try { localStorage.removeItem("chisme-greeting-word"); } catch {}
  function renderGreeting() {
    const h = localHour();
    $("#greet-hi").textContent = h >= 5 && h < 12 ? "¡Buenos días, chismosos!" : h >= 12 && h < 18 ? "¡Buenas tardes, chismosos!" : "¡Buenas noches, chismosos!";
    $("#greet-sub").textContent = "Pull up a chair, grab the tea, here’s the latest chisme.";
  }

  // ---------- location panel (friendly pre-prompt, denied fallback, change location)
  const PANEL = {
    ask: ["Show news & weather for where you are?",
      "Chisme uses your location only to look up your forecast, weather alerts, radar and nearby stories. It's saved on this device. You'll only be asked once: to change it later, tap the Chisme bubble at the top for Settings. Until then we're showing San Antonio, TX."],
    denied: ["Location is turned off for Chisme",
      "No problem — type a city or ZIP code below. (To use your location later, allow it for this site in your browser or phone settings, then tap “Use my location.”)"],
    unavailable: ["Couldn't find your location",
      "Your device didn't share a location. Type a city or ZIP code below, or try again."],
    insecure: ["Location needs a secure (https) connection",
      "Browsers only share location with https sites. Type a city or ZIP code below instead."],
  };
  // First-run card on the home screen. After setup, messages go to Settings instead (never the home screen).
  function showPanel(mode) {
    if (!firstRun()) {
      if (inSettings() && mode !== "ask") locStatus().textContent = (PANEL[mode] || [""])[0] + ". " + ((PANEL[mode] || [])[1] || "");
      return;
    }
    const [t, m] = PANEL[mode] || PANEL.ask;
    $("#loc-title").textContent = t;
    $("#loc-msg").textContent = m;
    $("#loc-panel").dataset.mode = mode;
    $("#loc-close").textContent = mode === "ask" ? "Not now" : "Close";
    $("#loc-gps").hidden = mode === "insecure" || !("geolocation" in navigator);
    $("#loc-status").textContent = "";
    $("#loc-results").replaceChildren();
    $("#loc-panel").hidden = false;
  }
  function hidePanel() { $("#loc-panel").hidden = true; }
  const inSettings = () => $("#settings").open;
  const locStatus = () => inSettings() ? $("#set-loc-status") : $("#loc-status");
  $("#loc-close").onclick = () => { hidePanel(); finishSetup(); };   // "Not now": keep San Antonio; change it in Settings
  $("#loc-gps").onclick = () => requestGPS(true);
  async function searchPlaces(text, status, results) {
    if (text.length < 2) return;
    status.textContent = "Searching…";
    results.replaceChildren();
    const pickIt = (r) => { results.replaceChildren(); status.textContent = inSettings() ? `Now showing ${r.label}.` : ""; setLocation(r, "manual"); };
    try {
      const { results: list } = await getJSON(`/api/geocode?q=${encodeURIComponent(text)}`, { timeout: 30000 });
      if (!list.length) { status.textContent = `No places found for “${text}”. Try “City, State” or a 5-digit ZIP.`; return; }
      if (list.length === 1) { pickIt(list[0]); return; }
      status.textContent = "Pick one:";
      results.replaceChildren(...list.map((r) => {
        const b = el("button", { type: "button", class: "loc-result" }, el("b", { text: r.label }), el("span", { text: r.display_name || "" }));
        b.onclick = () => pickIt(r);
        return el("li", {}, b);
      }));
    } catch (err) {
      status.textContent = navigator.onLine ? "Search failed: " + err.message : "You're offline — search needs a connection.";
    }
  }
  $("#loc-form").onsubmit = (e) => { e.preventDefault(); searchPlaces($("#loc-q").value.trim(), $("#loc-status"), $("#loc-results")); };
  $("#set-loc-form").onsubmit = (e) => { e.preventDefault(); searchPlaces($("#set-loc-q").value.trim(), $("#set-loc-status"), $("#set-loc-results")); };

  // ---------- geolocation
  let watchId = null, gpsBusy = false, lastFixAt = 0;
  const GPS_WAIT_MS = 12000;
  function onPos(p) {
    lastFixAt = Date.now();
    const n = { lat: p.coords.latitude, lon: p.coords.longitude };
    if (loc.source === "manual") { stopWatch(); return; }   // a typed city wins until "Use my location" is tapped again
    if (loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");   // live GPS follows you city to city
  }
  function onPosErr(err, fromButton) {
    if (fromButton && inSettings()) {
      locStatus().textContent = err.code === 1 ? "Location is turned off for Chisme. Allow it in your browser or phone settings, or enter a city or ZIP."
        : `Couldn't get a location fix — still showing ${placeName()}. Try again, or enter a city or ZIP.`;
      if (err.code === 1) stopWatch();
      return;
    }
    if (err.code === 1) { stopWatch(); if (loc.source !== "manual") showPanel("denied"); }
    else if (loc.source === "default") showPanel("unavailable");
    else if (fromButton) locStatus().textContent = `Couldn't get a location fix — still showing ${placeName()}. Try again, or type a city or ZIP.`;
  }
  function startWatch() {
    if (watchId != null || !("geolocation" in navigator)) return;
    watchId = navigator.geolocation.watchPosition(onPos, onPosErr, { enableHighAccuracy: false, maximumAge: 5 * 60e3, timeout: 30e3 });
  }
  function stopWatch() { if (watchId != null) navigator.geolocation.clearWatch(watchId); watchId = null; }
  function requestGPS(fromButton) {
    if (!window.isSecureContext) { showPanel("insecure"); return; }
    if (!("geolocation" in navigator)) { showPanel("unavailable"); return; }
    // iOS home-screen apps can leave getCurrentPosition hanging forever, so we keep our own timer.
    // News/weather never wait for this: they load for the saved (or default) location first.
    if (!fromButton && (gpsBusy || Date.now() - lastFixAt < 5 * 60e3)) return;
    if (fromButton) locStatus().textContent = "Finding you…";
    gpsBusy = true;
    let settled = false;
    const t = setTimeout(() => { if (settled) return; settled = true; gpsBusy = false; onPosErr({ code: 3 }, fromButton); }, GPS_WAIT_MS);
    navigator.geolocation.getCurrentPosition((p) => {
      settled = true; gpsBusy = false; clearTimeout(t); lastFixAt = Date.now();   // a late fix is still welcome
      if (!fromButton && loc.source === "manual") return;   // the user typed a place meanwhile: keep it
      const n = { lat: p.coords.latitude, lon: p.coords.longitude };
      if (fromButton || loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");
      if (fromButton) locStatus().textContent = inSettings() ? "Using your current location." : "";
      startWatch();
    }, (err) => { if (settled) return; settled = true; gpsBusy = false; clearTimeout(t); onPosErr(err, fromButton); },
    { enableHighAccuracy: false, maximumAge: 10 * 60e3, timeout: GPS_WAIT_MS - 2000 });
  }
  async function initGeo() {
    if (!window.isSecureContext || !("geolocation" in navigator)) {
      if (loc.source === "default") showPanel(window.isSecureContext ? "unavailable" : "insecure");
      return;
    }
    let state = "prompt";
    try { state = (await navigator.permissions.query({ name: "geolocation" })).state; } catch {}
    if (loc.source === "manual") return;                     // user picked a place; don't override
    if (state === "granted") requestGPS(false);               // refresh on app open, then watch
    else if (state === "denied") showPanel("denied");
    else if (loc.source === "gps") requestGPS(false);          // previously allowed
    else if (firstRun()) showPanel("ask");                      // one-time friendly pre-prompt
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && loc.source === "gps") requestGPS(false);
  });

  // ---------- weather
  function renderAlertStrip(w) {
    const strip = $("#alert-strip"), alerts = (w && w.alerts) || [];
    if (!alerts.length) { strip.hidden = true; strip.replaceChildren(); return; }
    const b = el("button", { type: "button", text: `⚠ ${alerts[0].event}${alerts.length > 1 ? ` (+${alerts.length - 1} more)` : ""} for your area — tap for details` });
    b.onclick = () => goView("weather", { scrollTo: "alerts" });
    strip.replaceChildren(b);
    strip.hidden = false;
  }
  function weatherBlurb(w) {
    const box = $("#wx-blurb");
    box.classList.remove("serious");
    if (!w || w.supported === false) { box.hidden = true; return; }
    if ((w.alerts || []).length) {
      box.textContent = "Heads up: the National Weather Service has active alerts for your area. Please read the details below and stay safe.";
      box.classList.add("serious"); box.hidden = false; return;
    }
    const t = cToF(w.current && w.current.temp_c);
    const today = (w.forecast || [])[0] || {};
    const pop = Math.max(today.pop || 0, ((w.forecast || [])[1] || {}).pop || 0);
    const sky = (today.shortForecast || "").toLowerCase();
    let line;
    if (/thunder/.test(sky) && pop >= 40) line = "Thunderstorms in the forecast — keep an eye on the radar and the sky. ⛈️";
    else if (pop >= 50) line = "Rain's in the chisme today — bring the paraguas. ☔";
    else if (t == null) line = pick(["Here's the sky report.", "Your forecast, fresh from the National Weather Service."]);
    else if (t >= 100) line = "¡Qué calor! Triple digits — agua, shade and sunscreen, mija. 🥵";
    else if (t >= 90) line = "Hot one out there. Keep the agua fría handy. 🌞";
    else if (t >= 78) line = "Warm and pleasant — patio weather, ¿qué no? 😎";
    else if (t >= 62) line = "Sweater-optional weather. Enjoy it while it lasts!";
    else if (t >= 45) line = "Chilly out — grab a chaqueta on the way out. 🧥";
    else line = "¡Brrr! Bundle up, it's legit cold out there. 🥶";
    box.textContent = line; box.hidden = false;
  }
  function renderAlerts(w) {
    renderAlertStrip(w);
    const box = $("#alerts");
    box.replaceChildren();
    if (w && w.supported === false) {
      box.append(el("div", { class: "no-alerts info", text: "ℹ︎ Weather alerts come from the U.S. National Weather Service and aren't available for " + placeName() + "." }));
      return;
    }
    const alerts = (w && w.alerts) || [];
    if (!alerts.length) {
      box.append(el("div", { class: "no-alerts", text: "✓ No active National Weather Service alerts for " + placeName() + "." }));
      return;
    }
    for (const a of alerts) {
      const ends = a.ends || a.expires;
      const meta = [a.severity, a.urgency, ends ? "Until " + dateTimeT(new Date(ends)) : null].filter(Boolean).join(" · ");
      const det = el("details", {}, el("summary", { text: "Read full alert" }),
        el("pre", { text: (a.description || "") + (a.instruction ? "\n\nWHAT TO DO:\n" + a.instruction : "") }),
        el("p", { class: "meta", text: "Areas: " + (a.areaDesc || "") }));
      box.append(el("article", { class: "alert sev-" + (a.severity || "Unknown"), role: "alert" },
        el("h3", { text: "⚠ " + a.event }), el("p", { class: "meta", text: meta }),
        a.headline ? el("p", { text: a.headline }) : null, det));
    }
  }
  function renderCurrent(c) {
    const box = $("#current");
    box.replaceChildren();
    if (!c) { box.append(el("p", { class: "error", text: "Current observations are unavailable right now." })); return; }
    const t = cToF(c.temp_c), feels = cToF(c.heat_index_c ?? c.wind_chill_c);
    const wind = kmhToMph(c.wind_kmh), gust = kmhToMph(c.wind_gust_kmh), dew = cToF(c.dewpoint_c);
    const main = el("div", { class: "now-main" },
      c.icon ? el("img", { src: icon(c.icon, "large"), alt: "" }) : null,
      el("div", {}, el("div", { class: "now-temp", text: t + "°F" }), el("div", { class: "now-text", text: c.text || "" }),
        feels != null && feels !== t ? el("div", { class: "now-feels", text: "Feels like " + feels + "°F" }) : null));
    const cell = (label, val) => val == null || val === "" ? null : el("div", {}, el("b", { text: label }), el("span", { text: val }));
    const grid = el("div", { class: "now-grid" },
      cell("Wind", wind == null ? null : (wind === 0 ? "Calm" : `${compass(c.wind_dir)} ${wind} mph`) + (gust ? `, gusts ${gust}` : "")),
      cell("Humidity", c.humidity == null ? null : Math.round(c.humidity) + "%"),
      cell("Dew point", dew == null ? null : dew + "°F"),
      cell("Pressure", c.pressure_pa == null ? null : (c.pressure_pa / 3386.39).toFixed(2) + " in"),
      cell("Visibility", c.visibility_m == null ? null : Math.round(c.visibility_m / 1609.34) + " mi"));
    box.append(main, grid, el("p", { class: "station",
      text: `Observed at ${c.station_name || c.station} (${c.station}) · ${c.timestamp ? dateTimeT(new Date(c.timestamp)) : ""}` }));
  }
  function renderHourly(hours) {
    const box = $("#hourly");
    box.replaceChildren();
    for (const h of hours || []) {
      const d = new Date(h.startTime);
      box.append(el("div", { class: "hour", title: h.shortForecast },
        el("div", { class: "h", text: fmt(d, { hour: "numeric" }) }),
        h.icon ? el("img", { src: icon(h.icon, "medium"), alt: h.shortForecast || "" }) : null,
        el("div", { class: "t", text: h.temperature + "°" }),
        el("div", { class: "p", text: h.pop ? "💧" + h.pop + "%" : "\u00a0" })));
    }
  }
  let fcOpen = null;   // key of the day whose details are showing
  function renderForecast(periods) {
    const box = $("#forecast"), detail = $("#fc-detail");
    box.replaceChildren();
    if (!periods || !periods.length) { detail.hidden = true; box.append(el("p", { class: "error", text: "Forecast unavailable right now." })); return; }
    const days = [];
    for (const p of periods) {
      const key = fmt(new Date(p.startTime), { year: "numeric", month: "2-digit", day: "2-digit" });
      let d = days.find((x) => x.key === key);
      if (!d) { d = { key, day: null, night: null }; days.push(d); }
      if (p.isDaytime) d.day = p; else d.night = p;
    }
    const today = fmt(new Date(), { year: "numeric", month: "2-digit", day: "2-digit" });
    const list = days.slice(0, 7);
    if (!list.some((d) => d.key === fcOpen)) fcOpen = null;
    const show = (d) => {
      detail.replaceChildren(el("h3", { text: (d.day || d.night).name + (d.day && d.night ? " & night" : "") }),
        d.day ? el("p", {}, el("b", { text: d.day.name + ": " }), d.day.detailedForecast) : null,
        d.night ? el("p", {}, el("b", { text: d.night.name + ": " }), d.night.detailedForecast) : null);
      detail.hidden = false;
    };
    for (const d of list) {
      const main = d.day || d.night;
      const pop = Math.max(d.day?.pop || 0, d.night?.pop || 0);
      const name = d.key === today ? (d.day ? "Today" : "Tonight") : fmt(new Date(main.startTime), { weekday: "short" });
      const temps = el("div", { class: "temps" });
      if (d.day) temps.append(d.day.temperature + "°");
      if (d.night) temps.append(d.day ? " / " : "Low ", el("span", { class: "lo", text: d.night.temperature + "°" }));
      const card = el("button", { type: "button", class: "day", "aria-controls": "fc-detail", "aria-expanded": String(d.key === fcOpen),
        "aria-label": `${main.name}: ${main.shortForecast}. ${d.day ? "High " + d.day.temperature + "°" : ""}${d.night ? (d.day ? ", low " : "Low ") + d.night.temperature + "°" : ""}. ${pop ? pop + "% chance of rain" : "Little or no rain"}. Show details` },
        el("span", { class: "dn", text: name }),
        icon(main.icon, "medium") ? el("img", { src: icon(main.icon, "medium"), alt: "" }) : null,
        temps,
        el("span", { class: "pop" + (pop ? "" : " dry"), text: pop ? "💧 " + pop + "%" : "💧 0%" }));
      card.title = main.shortForecast;
      card.onclick = () => {
        fcOpen = fcOpen === d.key ? null : d.key;
        for (const c of box.querySelectorAll(".day")) c.setAttribute("aria-expanded", "false");
        if (fcOpen) { card.setAttribute("aria-expanded", "true"); show(d); } else detail.hidden = true;
      };
      box.append(card);
      if (d.key === fcOpen) show(d);
    }
    if (!fcOpen) detail.hidden = true;
  }
  function renderUnsupported(w) {
    const msg = `${w.message} This location is outside NWS coverage, so there's no forecast here. Radar and news still work.`;
    $("#current").replaceChildren(el("p", { class: "notice", text: "🌎 " + msg }));
    $("#hourly").replaceChildren();
    $("#forecast").replaceChildren(el("p", { class: "notice", text: "Forecasts are available for U.S. locations only." }));
    $("#fc-detail").hidden = true;
    $("#fc-updated").textContent = "";
    $("#fc-credit").textContent = "Weather data: National Weather Service (U.S. only, api.weather.gov)";
  }
  const stampFor = (saved, n) => saved && n.generated ? "Saved copy from " + timeT(new Date(n.generated * 1000)) : "Updated " + timeT(new Date());
  section("weather", {
    url: () => `/api/weather?${q()}`,
    loading: () => $("#current").replaceChildren(el("p", { class: "loading", text: `Checking the sky over ${greetCity()}…` })),
    fail: (e) => {
      $("#wx-updated").textContent = "";
      $("#current").replaceChildren(el("p", { class: "error", text: "¡Ay! Couldn't reach the weather service (" + e.message + "). We'll keep trying." }));
    },
    apply: (w, { saved }) => {
      if (!saved) rendered.weather = q();
      lastWeather = w;
      if (w.location && w.location.tz) { TZ = w.location.tz; $("#tz-name").textContent = `${w.location.city || "local"} time (${tzAbbr()})`; }
      else { TZ = DEVICE_TZ; $("#tz-name").textContent = `your device's time (${tzAbbr()})`; }
      renderAlerts(w);
      weatherBlurb(w);
      if (w.supported === false) renderUnsupported(w);
      else {
        renderCurrent(w.current); renderHourly(w.hourly); renderForecast(w.forecast);
        if (w.forecast_updated) $("#fc-updated").textContent = "NWS issued " + dateTimeT(new Date(w.forecast_updated));
        $("#fc-credit").textContent = `Source: National Weather Service ${w.location.office || ""} office, grid ${w.location.grid ? w.location.grid.join(",") : ""} (api.weather.gov)`;
      }
      $("#wx-updated").textContent = stampFor(saved, w);
    },
  });
  const loadWeather = () => load("weather");

  // ---------- radar
  // A radar-app look: a muted, desaturated basemap (dark in dark mode) so the rain colors pop,
  // time badge + dBZ legend, and you as an Apple Maps-style blue dot. The basemap is the standard
  // OpenStreetMap tiles with a CSS filter (keyless; CARTO's basemaps now need an API key).
  let map = null, youMarker = null, frames = [], layers = {}, idx = 0, timer = null, playing = !reducedMotion(), radarHost = "";
  let baseLayer = null;
  function setBasemap() {
    if (!map || baseLayer) return;       // the look follows the theme through CSS
    baseLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, className: "basemap",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' });
    // offline: don't request map tiles that can't load; add them once the connection is back
    if (navigator.onLine) baseLayer.addTo(map); else window.addEventListener("online", () => baseLayer.addTo(map), { once: true });
  }
  // A touch that lands on the radar while the page is still momentum-scrolling can't be cancelled;
  // Leaflet tries anyway and Chrome logs an error. The page is scrolling, so the map shouldn't pan:
  // those moves never reach Leaflet. (Our swipe / pull-to-refresh already ignore touches on the map.)
  window.addEventListener("touchmove", (e) => {
    if (!e.cancelable && e.target && e.target.closest && e.target.closest(".leaflet-container")) e.stopImmediatePropagation();
  }, { capture: true, passive: true });
  function initMap() {
    map = L.map("map", { center: [loc.lat, loc.lon], zoom: 8, minZoom: 3, maxZoom: 12, scrollWheelZoom: false, zoomControl: false });
    L.control.zoom({ position: "topright" }).addTo(map);
    setBasemap();
    const dot = L.divIcon({ className: "me-marker", iconSize: [22, 22], iconAnchor: [11, 11],
      html: '<span class="me-halo"></span><span class="me-dot"></span>' });
    youMarker = L.marker([loc.lat, loc.lon], { icon: dot, keyboard: false, interactive: false, zIndexOffset: 1000, alt: "Your location" }).addTo(map);
    map.attributionControl.setPrefix(false);
    map.attributionControl.addAttribution('Radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a>');
  }
  function recenter(zoom) {
    youMarker.setLatLng([loc.lat, loc.lon]);
    map.setView([loc.lat, loc.lon], zoom || map.getZoom());
  }
  // v37: no yellow in the app. RainViewer only serves its "Universal Blue" scheme (moderate rain = yellow), so each
  // tile is drawn to a canvas and yellow/amber (hue 36–70°) is shifted to orange (22–36°), keeping lightness; the
  // legend in index.html uses the same colors. If a tile can't be read (no CORS), it's shown as it came.
  function radarColor(r, g, b) {
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if (d < 40) return null;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4);
    if (h < 0) h += 360;
    if (h < 36 || h > 70) return null;
    const nh = 22 + (h - 36) / 34 * 14, l = (mx + mn) / 510, sat = d / 255 / (1 - Math.abs(2 * l - 1) || 1);
    const c = (1 - Math.abs(2 * l - 1)) * sat, x = c * (1 - Math.abs((nh / 60) % 2 - 1)), m = l - c / 2;   // nh < 60: (c, x, 0)
    return [Math.round((c + m) * 255), Math.round((x + m) * 255), Math.round(m * 255)];
  }
  const RadarTiles = !window.L ? null : L.TileLayer.extend({
    createTile(coords, done) {
      const cv = document.createElement("canvas"), img = new Image();
      cv.width = cv.height = 256; img.crossOrigin = "anonymous"; img.decoding = "async";
      img.onload = () => {
        const g = cv.getContext("2d"); g.drawImage(img, 0, 0, 256, 256);
        try {
          const id = g.getImageData(0, 0, 256, 256), px = id.data;
          for (let i = 0; i < px.length; i += 4) {
            if (!px[i + 3]) continue;
            const o = radarColor(px[i], px[i + 1], px[i + 2]);
            if (o) { px[i] = o[0]; px[i + 1] = o[1]; px[i + 2] = o[2]; }
          }
          g.putImageData(id, 0, 0);
        } catch (e) { /* tainted canvas: keep the original colors */ }
        done(null, cv);
      };
      img.onerror = (e) => done(e, cv);
      img.src = this.getTileUrl(coords);
      return cv;
    },
  });
  function radarLayer(frame) {
    if (!layers[frame.path]) {
      // RainViewer's free tiles only go to zoom 7; Leaflet upsamples beyond that.
      layers[frame.path] = new (RadarTiles || L.TileLayer)(radarHost + frame.path + "/256/{z}/{x}/{y}/2/1_1.png", {
        tileSize: 256, opacity: 0, maxNativeZoom: 7, maxZoom: 12, zIndex: 10, className: "radar-tiles" });
    }
    return layers[frame.path];
  }
  function showFrame(i) {
    if (!frames.length) return;
    idx = (i + frames.length) % frames.length;
    const f = frames[idx], lyr = radarLayer(f);
    if (!map.hasLayer(lyr)) lyr.addTo(map);
    const nxt = radarLayer(frames[(idx + 1) % frames.length]);
    if (!map.hasLayer(nxt)) nxt.addTo(map);
    for (const [p, l] of Object.entries(layers)) l.setOpacity(p === f.path ? 0.8 : 0);
    const latest = idx === frames.length - 1;
    $("#radar-time").textContent = (f.nowcast ? "Forecast " : "") + timeT(new Date(f.time * 1000)) + (latest ? " · Latest" : " · " + Math.round((frames[frames.length - 1].time - f.time) / 60) + " min ago");
    $(".radar-time").classList.toggle("latest", latest);
    $("#r-slider").value = idx;
  }
  function setPlaying(p) {
    playing = p;
    clearInterval(timer);
    $("#r-play").textContent = p ? "❚❚ Pause" : "► Play";
    if (p) timer = setInterval(() => {
      showFrame(idx + 1);
      if (idx === frames.length - 1) { clearInterval(timer); setTimeout(() => playing && setPlaying(true), 1500); }
    }, 700);
  }
  let radarRetry = null;
  async function loadRadar() {
    clearTimeout(radarRetry);
    try {
      const j = await getJSON("/api/radar");
      if (offlineFrom["/api/radar"]) { $("#radar-time").textContent = "Radar needs a connection"; return; }
      radarHost = j.host;
      $("#radar-stamp").textContent = "RainViewer · updated " + timeT(new Date());
      const next = (j.radar?.past || []).map((f) => ({ ...f, nowcast: false })).concat((j.radar?.nowcast || []).map((f) => ({ ...f, nowcast: true })));
      const keep = new Set(next.map((f) => f.path));
      for (const [p, l] of Object.entries(layers)) if (!keep.has(p)) { map.removeLayer(l); delete layers[p]; }
      frames = next;
      $("#r-slider").max = Math.max(0, frames.length - 1);
      showFrame(frames.length - 1);
      setPlaying(playing && !reducedMotion());
    } catch (e) {
      $("#radar-time").textContent = navigator.onLine ? "Radar unavailable: " + e.message : "Radar needs a connection";
      clearTimeout(radarRetry); radarRetry = setTimeout(loadRadar, 30000);
    }
  }
  $("#r-play").onclick = () => setPlaying(!playing);
  $("#r-prev").onclick = () => { setPlaying(false); showFrame(idx - 1); };
  $("#r-next").onclick = () => { setPlaying(false); showFrame(idx + 1); };
  $("#r-slider").oninput = (e) => { setPlaying(false); showFrame(+e.target.value); };

  // ---------- mid-list donate card: on every 5th app open (static/donatelines.js counts opens and picks a line that
  // wasn't one of the last 5), an inline card (not a pop-up) in the middle of the tab Chisme opened on, after about the
  // 5th item. It stays in that list while it re-renders; switching tabs never adds another. ✕ hides it for the session.
  const MID_KEY = "chisme-donate-mid-x";
  let midTab = null, midCard = null, midLaunch = { opens: 0, line: null };
  const midGone = () => { try { return sessionStorage.getItem(MID_KEY) === "1"; } catch (e) { return false; } };
  // Where it goes → [node, "after" | "before"]. In a list (News' Near You, Sports, Events) it's after about the 5th item,
  // but never next to a serious story: it moves to the nearest slot where the item before and after are both light,
  // or if there's none, to the end of the tab, just above the bottom donate card. (v34; ChismeDonate.serious / slot)
  let midWhere = null;
  const itemText = (n) => { const h = n.querySelector("h3, h4, .title"), s = n.querySelector(".sum"); return h ? h.textContent + " " + (s ? s.textContent : "") : n.textContent; };
  function midInList(tab, items) {
    if (items.length < 2) return null;   // still loading
    const D = window.ChismeDonate, flags = items.map((n) => !!D && D.serious(itemText(n), n.querySelector(".src")?.textContent));
    const k = D ? D.slot(flags) : Math.min(5, Math.ceil(items.length / 2));
    const bottom = [...$("#view-" + tab).children].filter((n) => n.matches("aside.donate") && n !== midCard).pop();
    midWhere = { tab, k, n: items.length, serious: flags.filter(Boolean).length };
    if (k) return [items[k - 1], "after"];
    return bottom ? [bottom, "before"] : [items[items.length - 1], "after"];
  }
  function midSpot(tab) {
    const kids = (box, sel) => box ? [...box.children].filter((n) => n !== midCard && n.matches(sel)) : [];
    const at = (n) => (n ? [n, "after"] : null);
    if (tab === "news") return midInList(tab, kids($("#near-list"), ".story"));
    if (tab === "sports") return midInList(tab, kids($("#sports-body"), ":not(.loading):not(.error)"));
    if (tab === "events") return midInList(tab, kids($("#events-list"), ":not(.ev-day):not(.loading):not(.error)"));
    if (tab === "weather") return at($("#radar-sec"));      // between the radar and the 7-day forecast
    if (tab === "antojos") return at($("#food-block"));     // after the videos, before the food news desk
    if (tab === "juegos") return at($("#juegos"));          // between the list of games and the game
    return null;
  }
  function placeMid() {
    if (!midTab || midGone()) return;
    const spot = midSpot(midTab);
    if (!spot || !spot[0].parentNode) return;
    const [ref, how] = spot;
    if (!midCard) {
      midCard = el("aside", { class: "card donate donate-mid", id: "donate-mid", "aria-labelledby": "donate-mid-t" });
      midCard.innerHTML = `<button type="button" class="donate-x" aria-label="Dismiss this for now">✕</button>
        <p class="donate-text" id="donate-mid-t"></p>
        <div class="donate-btns"><a class="donate-btn cashapp" href="https://cash.app/$Slurmkaos" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">💸</span> Donate on Cash App<span class="sr-only"> (opens Cash App)</span></a><a class="donate-btn bmc" href="https://buymeacoffee.com/Chismoso" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">☕</span> Buy Me a Coffee<span class="sr-only"> (opens Buy Me a Coffee)</span></a><!-- room for one more: <a class="donate-btn venmo"> (add venmo.com to DIRECT_HOSTS in app.js) --></div>
        <p class="donate-tag">$Slurmkaos</p>`;
      midCard.querySelector(".donate-text").textContent = midLaunch.line;
      midCard.querySelector(".donate-x").onclick = () => {
        try { sessionStorage.setItem(MID_KEY, "1"); } catch (e) {}
        const next = midCard.nextElementSibling; midCard.remove(); midTab = null;
        const f = next && (next.matches("a, button") ? next : next.querySelector("a, button"));
        if (f) f.focus({ preventScroll: true });
      };
    }
    if ((how === "after" ? ref.nextSibling : ref.previousSibling) !== midCard) ref[how](midCard);
  }

  // ---------- news order: when nothing's new, each visit shows the stories in a different order (static/newsorder.js).
  // What you've seen/opened stays on this phone; Settings → Reset my feed and Forget me clear it.
  const NO = window.ChismeNewsOrder;
  let nsState = NO ? NO.load() : null, nsTimer = null;
  if (NO) { if (NO.isNewVisit(nsState)) NO.beginVisit(nsState); else nsState.active = Date.now(); NO.save(nsState); }
  const nsSaveSoon = () => { if (!NO) return; clearTimeout(nsTimer); nsTimer = setTimeout(() => { nsState.active = Date.now(); NO.save(nsState); }, 800); };
  function newsVisit() { if (NO) { NO.beginVisit(nsState); NO.save(nsState); } }
  function newsForget() { if (NO) { nsState = NO.reset(); NO.beginVisit(nsState); NO.save(nsState); } }
  const ordered = (list) => (NO && nsState ? NO.order(list || [], nsState) : list || []);
  setInterval(() => { if (NO && document.visibilityState === "visible") { nsState.active = Date.now(); NO.save(nsState); } }, 60000);
  document.addEventListener("visibilitychange", () => {
    if (!NO) return;
    if (document.visibilityState === "hidden") { nsState.active = Date.now(); NO.save(nsState); return; }
    if (NO.isNewVisit(nsState)) { newsVisit(); if (lastNewsData && !newsHold) renderNews(lastNewsData, lastNewsSaved); }   // back after 10+ min
  });
  const seenIO = NO && "IntersectionObserver" in window ? new IntersectionObserver((ents) => {
    let ch = false;
    for (const e of ents) if (e.isIntersecting) { NO.markSeen(nsState, e.target.dataset.sid); seenIO.unobserve(e.target); ch = true; }
    if (ch) nsSaveSoon();
  }, { threshold: 0.6 }) : null;
  function trackNews(lists) {
    if (!NO) return;
    NO.markRendered(nsState, lists.flat()); nsSaveSoon();
    if (seenIO) { seenIO.disconnect(); for (const a of document.querySelectorAll("#view-news .story[data-sid]")) seenIO.observe(a); }
  }

  // ---------- news
  function story(it, showTags) {
    const d = it.published ? new Date(it.published * 1000) : null;
    const body = el("div", { class: "body" },
      el("h3", {}, ext(it.link, it.title, null, storyMeta(it))),
      el("div", { class: "meta" }, el("span", { class: "src", text: it.source }), d ? " · " + ago(d) + " · " + dateTimeT(d) : ""),
      it.summary ? el("p", { class: "sum", text: it.summary }) : null);
    if (showTags && it.local_terms?.length) {
      body.append(el("div", { class: "tags" }, ...it.local_terms.slice(0, 4).map((t) => el("span", { class: "tag", text: t }))));
    }
    const kids = [body];
    if (it.image && navigator.onLine) {
      const img = el("img", { src: it.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.remove();
      kids.push(img);
    }
    kids.push(digDeeper(it));
    return el("article", { class: "story" + (showTags && it.tier === "near" ? " near" : ""), "data-sid": NO ? NO.idOf(it.link) : null }, ...kids);
  }

  // Links at the end of each story: the original article, the same story from other outlets we
  // fetched, and a Google News search for the topic. Every URL comes from the feeds/server.
  // Every outside link stays inside Chisme: a tap opens the in-app reader (framed where the site allows it,
  // else a headline card) or the map sheet, with the headline/source/summary we already have. Long-press and
  // ⌘/Ctrl-click still get the real URL. The only links that leave on purpose are the donate buttons (Cash App and
  // Buy Me a Coffee; later a Venmo button: add venmo.com here).
  const DIRECT_HOSTS = new Set(["cash.app", "buymeacoffee.com"]);
  const linkMeta = new WeakMap();
  const ext = (href, text, cls, meta) => {
    const a = el("a", { href, class: cls, text: text == null ? null : String(text).replace(/\s*↗\s*$/, ""), "aria-haspopup": "dialog" });
    if (meta) linkMeta.set(a, meta);
    return a;
  };
  const storyMeta = (it) => ({ title: it.title, source: it.source, published: it.published || null, summary: it.summary || null, image: it.image || null });
  function digDeeper(it) {
    const viaGoogle = /^https:\/\/news\.google\.com\//.test(it.link);
    const read = ext(it.link, `Read full story · ${it.source}`, "btnlink primary", storyMeta(it));
    if (viaGoogle) read.title = "Opens the story inside Chisme (the link goes through Google News)";
    const more = it.search_url ? ext(it.search_url, "🔎 More coverage", "btnlink", { title: "More coverage: " + it.title, source: "Google News search",
      summary: "Other outlets' reporting on this story, from a Google News search." }) : null;
    if (more) more.setAttribute("aria-label", "More coverage: search Google News for this story");
    const row = el("div", { class: "dig-row" }, read, more);
    const box = el("div", { class: "dig" });
    if (it.related && it.related.length) {
      box.append(el("p", { class: "related-h", text: "Also reported by" }),
        el("ul", { class: "related" }, ...it.related.map((r) => el("li", {},
          (() => { const a = ext(r.link, null, null, { title: r.title, source: r.source, published: r.published || null, summary: r.summary || null });
            a.append(el("span", { class: "rsrc", text: r.source + ": " }), r.title); return a; })()))));
    }
    box.append(row);
    return box;
  }
  // ---------- Texas art & landmark photos between stories (Wikimedia Commons, credited on each card)
  const ART_EVERY = 4, ART_KEY = "chisme-art-next";
  let ART = [];
  const artReady = fetch("/static/art/art.json").then((r) => r.json()).then((j) => { ART = j.items || []; }).catch(() => {});
  function artCard(a) {
    const img = el("img", { src: a.src, alt: a.alt, width: a.w, height: a.h, loading: "lazy", decoding: "async", draggable: "false" });
    img.onerror = () => fig.remove();
    const artMeta = { title: `${a.subject} · ${a.city}`, source: "Wikimedia Commons", summary: `Photo: ${a.author} · ${a.license}`, image: a.src };
    const lic = a.license_url ? ext(a.license_url, a.license, null, { title: a.license, source: "License", summary: `The license for this photo by ${a.author}.` }) : el("span", { text: a.license });
    const fig = el("figure", { class: "art" + (a.mural ? " mural" : ""), "data-art": String(a.n) },
      el("div", { class: "art-frame" }, img),
      el("figcaption", {},
        el("p", { class: "art-kicker", text: a.mural ? "🎨 Arte local" : "📍 Postal de Texas" }),
        el("p", { class: "art-cap", text: `${a.subject} · ${a.city}` }),
        a.artist ? el("p", { class: "art-artist", text: a.artist }) : null,
        el("p", { class: "art-credit" }, "Photo: ", el("b", { text: a.author }), " · ", lic, " · ",
          ext(a.source_url, "Source: Wikimedia Commons", null, artMeta))));
    return fig;
  }
  // One photo after every 4 stories (only between stories), rotating through the set; the next
  // starting photo is saved so each refresh shows different ones.
  let artCursor = +localStorage.getItem(ART_KEY) || 0, artStart = artCursor;
  function withArt(nodes) {
    if (!ART.length || nodes.length <= ART_EVERY) return nodes;
    const out = [];
    nodes.forEach((n, i) => {
      out.push(n);
      if ((i + 1) % ART_EVERY === 0 && i < nodes.length - 1) out.push(artCard(ART[artCursor++ % ART.length]));
    });
    return out;
  }
  function saveArtCursor() {
    const N = ART.length || 1;
    artCursor %= N;
    if (artCursor === artStart % N) artCursor = (artCursor + 1) % N;  // used a whole number of rounds: still move on
    artStart = artCursor;
    localStorage.setItem(ART_KEY, String(artCursor));
  }

  // Existing stories stay on screen while the news refreshes (no more blank "Gathering…" on every
  // refresh); the saved copy shows first on a cold start.
  let artWait = null;
  section("news", {
    url: () => `/api/news?${q()}`,
    loading: () => $("#near-list").replaceChildren(el("p", { class: "loading", text: `Gathering the chisme near ${greetCity()}…` })),
    fail: (e) => $("#near-list").replaceChildren(el("p", { class: "error", text: "¡Ay, no! Couldn't reach the news (" + e.message + "). We'll keep trying." })),
    apply: (n, { saved }) => {
      if (!ART.length && !artWait) { artWait = artReady.then(() => { artWait = null; if (lastNewsData) renderNews(lastNewsData, lastNewsSaved); }); }
      // Already reading live stories for this place? Don't jump the list: new stories wait behind the
      // "New chisme ↑" pill; a check with nothing new only updates the time. (Pull to refresh / Refresh now,
      // a new location, or the first live load after the saved copy render right away.)
      if (!saved && !newsManual && lastNewsData && !lastNewsSaved && rendered.news === q()) {
        const have = new Set(storyLinks(lastNewsData)), fresh = storyLinks(n).filter((u) => !have.has(u));
        $("#news-updated").textContent = stampFor(false, n);
        if (fresh.length) { newsHold = n; updateNewsPill(fresh.length); }
        return;
      }
      if (!saved) { rendered.news = q(); newsManual = false; newsHold = null; updateNewsPill(); }
      renderNews(n, saved);
    },
  });
  let lastNewsData = null, lastNewsSaved = false, newsHold = null, newsManual = false, newsHoldN = 0;
  const storyLinks = (n) => [...(n.near || []), ...(n.more || []), ...(n.metro_other || n.san_antonio || [])].map((i) => i.link).filter(Boolean);
  function updateNewsPill(count) {
    const pill = $("#news-pill");
    if (!pill) return;
    if (count != null) newsHoldN = count;
    pill.hidden = !newsHold || VIEWS[cur] !== "news";
    $("#news-pill-n").textContent = newsHold ? ` — ${newsHoldN} new ${newsHoldN === 1 ? "story" : "stories"}, show ${newsHoldN === 1 ? "it" : "them"}` : "";
  }
  function showHeldNews() {
    if (!newsHold) return;
    const n = newsHold; newsHold = null; updateNewsPill();
    rendered.news = q(); renderNews(n, false);
    const near = $("#near");
    window.scrollTo({ top: Math.max(0, near.getBoundingClientRect().top + window.scrollY - tabsH() - 8), behavior: reducedMotion() ? "instant" : "smooth" });
    (near.querySelector(".story h3 a") || near).focus({ preventScroll: true });
  }
  $("#news-pill").onclick = showHeldNews;
  function renderNews(n, saved) {
    lastNewsData = n; lastNewsSaved = saved;
    {
      const p = n.place || {};
      const names = (p.nearby || []).slice(0, 5).map((x) => x.name);
      $("#near-hint").textContent = "Closest first: " + [names.length ? names.join(", ") : null, p.city, p.county].filter(Boolean).join(" → ") + ".";
      const nearO = ordered(n.near), moreO = ordered(n.more), otherO = ordered(n.metro_other || n.san_antonio || []);
      $("#near-list").replaceChildren(...(n.near.length ? withArt(nearO.map((i) => story(i, true)))
        : [el("p", { class: "loading", text: `No stories naming ${placeName()} in the latest feeds yet — check back in a bit.` })]));
      $("#city-list").replaceChildren(...(n.more.length ? withArt(moreO.map((i) => story(i, false)))
        : [el("p", { class: "loading", text: "No other local stories right now. The newsrooms must be on a coffee break. ☕" })]));
      const other = n.metro_other || n.san_antonio || [];   // the metro's outlets, for suburbs outside its core
      $("#sa-sec").hidden = !other.length;
      $("#sa-title").textContent = `${(n.metro && n.metro.name) || "San Antonio"} headlines`;
      $("#sa-list").replaceChildren(...withArt(otherO.map((i) => story(i, false))));
      saveArtCursor();
      trackNews([nearO, moreO, otherO]);
      placeMid();
      $("#news-updated").textContent = stampFor(saved, n);
      $("#feeds").replaceChildren(...(n.feeds || []).map((f) => el("li", { class: f.ok ? "" : "bad",
        text: (f.ok ? `${f.name}: ${f.count} items` : `${f.name}: unavailable (${f.error})`) + (f.query ? ` — search: ${f.query}` : "") })));
    }
  }
  const loadNews = () => load("news");

  // ---------- events
  const CAT_EMOJI = [[/music|concert|band|jazz|dj|tour/i, "🎶"], [/food|culinary|cooking|taco|wine|beer|brew|dinner|market/i, "🌮"],
    [/art|museum|exhibit|gallery|lecture|theat|dance|film/i, "🎨"], [/kid|family|zoo|halloween|boo/i, "🎃"],
    [/run|5k|sport|fitness|yoga|pilates|scrimmage|game/i, "🏃"], [/career|job|business|workshop|training|expo/i, "💼"]];
  const catEmoji = (e) => { const t = e.title + " " + (e.categories || []).join(" "); for (const [rx, em] of CAT_EMOJI) if (rx.test(t)) return em; return "🎉"; };
  const dayKey = (d) => fmt(d, { year: "numeric", month: "2-digit", day: "2-digit" });
  function dayLabel(d) {
    const k = dayKey(d), today = dayKey(new Date()), tmr = dayKey(new Date(Date.now() + 864e5));
    const long = fmt(d, { weekday: "long", month: "short", day: "numeric" });
    return k === today ? "Today · " + long : k === tmr ? "Tomorrow · " + long : long;
  }
  function whenText(e) {
    const s = new Date(e.start), en = e.end ? new Date(e.end) : null;
    const dShort = (d) => fmt(d, { weekday: "short", month: "short", day: "numeric" });
    const multi = en && dayKey(en) !== dayKey(s);
    if (e.ongoing) return "Through " + dShort(en) + (e.recurrence ? " · " + e.recurrence : "");
    let t = dShort(s);
    if (e.has_time) t += " · " + fmt(s, { hour: "numeric", minute: "2-digit" });
    if (multi) t += " – " + dShort(en);
    else if (!e.has_time) t += " · time on the event page";
    return t;
  }
  function tileFor(lat, lon, z = 15) {
    const n = 2 ** z, r = lat * Math.PI / 180;
    const x = (lon + 180) / 360 * n, y = (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n;
    return { z, x: Math.floor(x), y: Math.floor(y), px: (x % 1) * 256, py: (y % 1) * 256 };
  }
  function miniMap(e, href) {
    const W = 112, H = 84, t = tileFor(e.lat, e.lon);
    const left = Math.min(0, Math.max(W - 256, W / 2 - t.px)), top = Math.min(0, Math.max(H - 256, H / 2 - t.py));
    const img = el("img", { src: `https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`, alt: "", loading: "lazy", width: 256, height: 256 });
    img.style.left = left + "px"; img.style.top = top + "px";
    const pin = el("span", { class: "pin" }); pin.style.left = (t.px + left) + "px"; pin.style.top = (t.py + top) + "px";
    const a = el("a", { class: "minimap", href, "aria-haspopup": "dialog", "aria-label": `Map: ${e.venue || "event location"} (opens the map)` }, img, pin);
    linkMeta.set(a, evMapMeta(e));
    img.onerror = () => a.remove();
    return a;
  }
  // Not a photo, and it says so: shown when the listing has no picture (or we're offline).
  function placeholder(e) {
    const why = e.image ? "Photo loads when you're online" : "No photo from the listing";
    return el("div", { class: "ev-ph", role: "img", "aria-label": why },
      el("b", { text: catEmoji(e), "aria-hidden": "true" }), el("span", { text: why }));
  }
  function priceBadge(e) {
    const p = e.price;
    if (p && p.free) return el("span", { class: "price free", text: p.text && !/^free$/i.test(p.text) ? "FREE · " + p.text : "FREE" });
    if (p && p.text) return el("span", { class: "price paid", text: /^[\d.]+$/.test(p.text) ? "Admission: " + p.text : p.text });
    return ext(e.url, "Check price", "price check", evMeta(e));
  }
  function outlook(e) {
    const w = e.weather || {};
    if (w.available) {
      return el("div", { class: "ev-wx" }, w.icon ? el("img", { src: icon(w.icon, "small"), alt: "", loading: "lazy" }) : null,
        el("span", { text: `${w.name}: ${w.short}, ${w.day ? "high" : "low"} ${w.temp}°${w.unit || "F"}${w.pop ? ` · 💧 ${w.pop}% chance of rain` : ""}` }));
    }
    return el("div", { class: "ev-wx na", text: w.reason === "beyond" ? "🔮 Forecast not available yet — the National Weather Service forecasts 7 days out."
      : "Forecast unavailable for this spot right now." });
  }
  const evMeta = (e) => ({ title: e.title, source: e.source, when: whenText(e), summary: e.summary || null, image: e.image || null,
    lat: e.approx ? null : e.lat, lon: e.approx ? null : e.lon, venue: e.venue || null, address: e.address || null });
  const evMapMeta = (e) => ({ map: true, name: e.venue || e.title, address: e.address || null, lat: e.approx ? null : e.lat, lon: e.approx ? null : e.lon, city: cityName() });
  function eventCard(e) {
    const hasGeo = e.lat != null && e.lon != null && !e.approx;
    const osm = hasGeo ? `https://www.openstreetmap.org/?mlat=${e.lat.toFixed(5)}&mlon=${e.lon.toFixed(5)}#map=17/${e.lat.toFixed(5)}/${e.lon.toFixed(5)}` : null;
    const q = [e.venue, e.address].filter(Boolean).join(", ");
    const gmaps = hasGeo ? `https://www.google.com/maps/search/?api=1&query=${e.lat.toFixed(5)}%2C${e.lon.toFixed(5)}`
      : q ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}` : null;
    const media = el("div", { class: "ev-media" });
    if (e.image && navigator.onLine) {
      const img = el("img", { src: e.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.replaceWith(placeholder(e));
      media.append(img);
    } else media.append(placeholder(e));
    const venueTxt = el("div", { class: "txt" },
      e.venue ? el("div", {}, el("b", { text: e.address && e.address.toLowerCase().startsWith(e.venue.toLowerCase()) ? e.address : e.venue })) : null,
      e.address && !(e.venue && e.address.toLowerCase().startsWith(e.venue.toLowerCase())) ? el("div", { text: e.address }) : null,
      e.km != null && !e.approx ? el("div", { text: `${(e.km * 0.621371).toFixed(1)} mi from you` }) : null,
      !e.venue && !e.address ? el("div", { text: "Location on the event page" }) : null);
    const venue = el("div", { class: "ev-line ev-venue" }, el("span", { text: "📍", "aria-hidden": "true" }), venueTxt, hasGeo && navigator.onLine ? miniMap(e, osm) : null);
    const also = (e.also || []).map((a, k) => [k ? ", " : " · also on ", ext(a.url, a.source, null, { ...evMeta(e), source: a.source })]).flat();
    return el("article", { class: "ev" }, media,
      el("div", { class: "ev-body" },
        el("h3", {}, ext(e.url, e.title, null, evMeta(e))),
        el("div", { class: "ev-line" }, el("span", { text: "🗓", "aria-hidden": "true" }), el("span", { text: whenText(e) })),
        venue,
        el("div", { class: "ev-line" }, el("span", { text: "🎟", "aria-hidden": "true" }), priceBadge(e)),
        outlook(e),
        e.summary ? el("p", { class: "ev-sum", text: e.summary }) : null,
        el("div", { class: "ev-links" }, ext(e.url, `Event page (${e.source})`, "primary", evMeta(e)),
          gmaps ? ext(gmaps, "🗺 Map & directions", null, evMapMeta(e)) : null,
          e.website && e.website !== e.url ? ext(e.website, "Organizer site", null, { ...evMeta(e), source: hostOf(e.website) + " (organizer)" }) : null),
        el("p", { class: "ev-src" }, "Listed on " + e.source, ...also)));
  }
  // ---------- event categories + food reviews
  const CAT_KEY = "chisme-events-cat";
  const CATS = {
    all: { test: () => true },
    concerts: { test: (e) => (e.tags || []).includes("concerts"),
      intro: (k) => `🎸 Turn it up: ${k} ${k === 1 ? "show" : "shows"} coming up around ${shortPlace()}.`,
      empty: "No concerts on the calendars right now. Hum something to yourself and check back soon. 🎶" },
    festivals: { test: (e) => (e.tags || []).includes("festivals"),
      intro: (k) => `🎉 Fiesta mode: ${k} ${k === 1 ? "festival or market" : "festivals & markets"} on the way.`,
      empty: "No festivals listed right now — ¡pero ya viene Fiesta! Check back soon." },
    "free-classes": { test: (e) => (e.tags || []).includes("classes") && e.free,
      intro: (k) => `🎓 Learn something, pay nothing: ${k} free ${k === 1 ? "class, talk or workshop" : "classes, talks & workshops"}.`,
      empty: "No free classes or workshops on the calendars right now. Check back soon — or tap “All” for paid ones." },
  };
  let evData = null, evIntro = "", foodData = null, foodSeq = 0;
  let evCat = CATS[localStorage.getItem(CAT_KEY)] ? localStorage.getItem(CAT_KEY) : "all";
  function renderEventList() {
    const n = evData;
    if (!n) return;
    const c = CATS[evCat], all = n.events || [], ongoingAll = n.ongoing || [];
    for (const b of document.querySelectorAll("#ev-chips .chip")) b.setAttribute("aria-pressed", String(b.dataset.cat === evCat));
    for (const k of Object.keys(CATS)) {
      const span = $("#n-" + k);
      if (span) { const cnt = [...all, ...ongoingAll].filter(CATS[k].test).length; span.textContent = cnt ? `(${cnt})` : "(0)"; }
    }
    const list = all.filter(c.test), ongoing = ongoingAll.filter(c.test);
    $("#events-intro").textContent = evCat === "all" || !(all.length + ongoingAll.length) ? evIntro : c.intro(list.length + ongoing.length);
    const kids = [];
    let last = null;
    for (const e of list) {
      const k = dayKey(new Date(e.start));
      if (k !== last) { kids.push(el("h3", { class: "ev-day", text: dayLabel(new Date(e.start)) })); last = k; }
      kids.push(eventCard(e));
    }
    const empty = evCat === "all" ? "No events on the calendar yet. ¡Ni modo! Try again later." : c.empty;
    $("#events-list").replaceChildren(...(kids.length ? kids : n.message && evCat === "all" ? []
      : ongoing.length ? [el("p", { class: "loading", text: "Nothing new coming up in this category — see “Still going on” below." })]
      : [el("p", { class: "loading", text: empty })]));
    $("#ongoing-sec").hidden = !ongoing.length;
    $("#ongoing-list").replaceChildren(...ongoing.map(eventCard));
    placeMid();
  }
  for (const b of document.querySelectorAll("#ev-chips .chip")) {
    b.onclick = () => {
      evCat = b.dataset.cat; localStorage.setItem(CAT_KEY, evCat);
      renderEventList();
    };
  }
  const shortDate = (t) => fmt(new Date(t * 1000), { month: "short", day: "numeric" });
  // ---------- saved food spots: kept in localStorage so they outlive feed refreshes and work offline
  const SAVED_KEY = "chisme-food-saved", FV_KEY = "chisme-food-view";
  let foodView = localStorage.getItem(FV_KEY) === "saved" ? "saved" : "latest";
  const readSaved = () => {
    try { const a = JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"); return Array.isArray(a) ? a.filter((x) => x && x.url && x.title) : []; }
    catch { return []; }
  };
  let savedSpots = readSaved(), lastRemoved = null;
  const writeSaved = () => { try { localStorage.setItem(SAVED_KEY, JSON.stringify(savedSpots)); return true; } catch { return false; } };
  const isSaved = (url) => savedSpots.some((s) => s.url === url);
  const cleanPlace = (p) => {
    const name = ((p && p.name) || "").trim().slice(0, 80), address = ((p && p.address) || "").trim().slice(0, 160);
    return name || address ? { name: name || null, address: address || null, guessed: !!(p && p.guessed) } : null;
  };
  const snapshot = (it) => it.savedAt ? { ...it, savedAt: Date.now() } : ({   // (re-saving an item from the Saved list keeps it as is)
    url: it.url, title: it.title, image: it.image || null, video: !!it.video, kind: it.kind,
    source: it.kind === "creator" ? it.creator : [it.outlet, it.author].filter(Boolean).join(" · "),
    published: it.published || null, place: it.place ? cleanPlace({ ...it.place, guessed: true }) : null,
    summary: it.summary || null, frame: !!it.frame, savedAt: Date.now(),
    city: it.elsewhere ? "San Antonio, TX" : [cityName(), loc.place && loc.place.state].filter(Boolean).join(", "),   // for Directions by name
  });
  const mapMeta = (p, city) => ({ map: true, name: p.name || null, address: p.address || null, city: city || "San Antonio, TX", lat: p.lat ?? null, lon: p.lon ?? null });
  const mapsUrl = (p, city) => "https://maps.apple.com/?daddr=" + encodeURIComponent(p.address || `${p.name}, ${city || "San Antonio, TX"}`) + "&dirflg=d";
  const bmIcon = () => {
    const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg"), path = document.createElementNS(NS, "path");
    svg.setAttribute("viewBox", "0 0 12 16"); svg.setAttribute("class", "bm"); svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false");
    path.setAttribute("d", "M1.5 1.5h9v13L6 11l-4.5 3.5z");
    svg.append(path);
    return svg;
  };
  function saveButton(it) {
    const b = el("button", { type: "button", class: "fr-save", "data-url": it.url, "data-title": it.title });
    b.onclick = () => toggleSaved(it);
    paintSave(b);
    return b;
  }
  function paintSave(b) {
    const on = isSaved(b.dataset.url);
    b.setAttribute("aria-pressed", String(on));
    b.replaceChildren(bmIcon(), on ? "Saved" : "Save", el("span", { class: "sr-only", text: ": " + (b.dataset.title || "") }));
  }
  function syncSaved() {
    for (const b of document.querySelectorAll(".fr-save")) paintSave(b);
    $("#n-saved").textContent = `(${savedSpots.length})`;
    renderSaved();
  }
  function flash(msg, undo) {
    const box = $("#food-saved-status");
    box.replaceChildren(msg ? el("span", { text: msg }) : "");
    if (undo) {
      const u = el("button", { type: "button", class: "fs-undo", text: "Undo" });
      u.onclick = () => { undo(); box.replaceChildren(); };
      box.append(" ", u);
      return u;
    }
  }
  function toggleSaved(it) {
    const had = isSaved(it.url);
    savedSpots = had ? savedSpots.filter((s) => s.url !== it.url) : [snapshot(it), ...savedSpots];
    if (!writeSaved()) { savedSpots = readSaved(); flash("Couldn't save — this phone's storage is full."); }
    else if (it.video) fySignal(had ? "unsave" : "save", it);   // For You learns from saves (videos only)
    syncSaved();
  }
  function removeSaved(s) {
    const i = savedSpots.findIndex((x) => x.url === s.url);
    if (i < 0) return;
    savedSpots.splice(i, 1); writeSaved(); syncSaved();
    const u = flash(`Removed “${s.title}”.`, () => { if (!isSaved(s.url)) { savedSpots.splice(Math.min(i, savedSpots.length), 0, s); writeSaved(); syncSaved(); } });
    if (u) u.focus();
  }
  function placeForm(s, row) {
    const f = el("form", { class: "fs-form" });
    const id = "fs" + Math.random().toString(36).slice(2, 8);
    const nm = el("input", { id: id + "n", type: "text", autocomplete: "off", maxlength: "80", placeholder: "e.g. Losoya’s Taqueria" });
    const ad = el("input", { id: id + "a", type: "text", autocomplete: "street-address", maxlength: "160", placeholder: "Street address (optional)" });
    nm.value = (s.place && s.place.name) || ""; ad.value = (s.place && s.place.address) || "";
    const cancel = el("button", { type: "button", text: "Cancel" });
    f.append(el("label", { for: id + "n", text: "Restaurant" }), nm, el("label", { for: id + "a", text: "Address" }), ad,
      el("div", { class: "fs-act" }, el("button", { type: "submit", class: "primary", text: "Save place" }), cancel));
    f.onsubmit = (e) => {
      e.preventDefault();
      const x = savedSpots.find((y) => y.url === s.url);
      if (x) { x.place = cleanPlace({ name: nm.value, address: ad.value }); writeSaved(); }
      syncSaved();
      const again = [...document.querySelectorAll("#food-saved .fs")].find((a) => a.dataset.url === s.url);
      if (again) (again.querySelector(".fs-dir") || again.querySelector(".fs-edit")).focus();
    };
    cancel.onclick = () => { f.remove(); row.querySelector(".fs-edit").focus(); };
    return f;
  }
  function savedItem(s) {
    const open = (a) => openPlayer(s, a);
    const thumb = el("a", { class: "fr-thumb", href: s.url, tabindex: "-1", "aria-hidden": "true" });
    thumb.onclick = (e) => { e.preventDefault(); open(row.querySelector("h4 a")); };
    const ph = () => el("div", { class: "ev-ph", role: "img", "aria-label": s.image ? "Photo loads when you're online" : "No photo in the feed" },
      el("b", { text: s.video ? "🎥" : "📰", "aria-hidden": "true" }), el("span", { text: s.image ? "offline" : "no photo" }));
    if (s.image) {  // try even offline: the browser cache often still has it
      const img = el("img", { src: s.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.replaceWith(ph());
      thumb.append(img);
      if (s.video) thumb.append(el("span", { class: "play", text: "▶" }));
    } else thumb.append(ph());
    const p = s.place;
    const row = el("article", { class: "fr fs", "data-url": s.url }, thumb,
      el("div", { class: "fr-body" },
        el("h4", {}, openLink(s.url, s.title, null, open)),
        el("p", { class: "fr-by" }, el("b", { text: s.source || "" }), s.published ? " · " + shortDate(s.published) : ""),
        p ? el("p", { class: "fs-place" }, ...placeLine(p)) : null));
    const edit = el("button", { type: "button", class: "fs-edit", text: p ? "Edit place" : "📍 Add place" });
    edit.setAttribute("aria-label", (p ? "Edit place for " : "Add place for ") + s.title);
    edit.onclick = () => {
      const open = row.querySelector(".fs-form");
      if (open) { open.remove(); return; }
      const f = placeForm(s, row); row.append(f); f.querySelector("input").focus();
    };
    const rm = el("button", { type: "button", class: "fs-rm", text: "Remove" });
    rm.setAttribute("aria-label", "Remove " + s.title);
    rm.onclick = () => removeSaved(s);
    const dir = p ? ext(mapsUrl(p, s.city), "Directions", "fs-dir", mapMeta(p, s.city)) : null;
    if (dir) dir.setAttribute("aria-label", `Map and directions to ${p.name || p.address}`);
    row.append(el("div", { class: "fs-act" }, openLink(s.url, s.video ? "▶ Watch" : "Read", "fs-open", open), dir, edit, rm));
    return tapCard(row, open);
  }
  function renderSaved() {
    const box = $("#food-saved");
    if (!box) return;
    box.replaceChildren(...(savedSpots.length ? savedSpots.map(savedItem)
      : [el("p", { class: "loading", text: "Nothing saved yet. Tap 🔖 Save on any review and it'll wait here — even offline." })]));
  }
  function syncFoodView() {
    const sv = foodView === "saved";
    for (const b of document.querySelectorAll("#food-view .chip")) b.setAttribute("aria-pressed", String(b.dataset.fv === foodView));
    $("#food-saved-view").hidden = !sv; $("#food-latest").hidden = sv;
    $("#food-desk").hidden = sv || !$("#food-outlets").children.length;   // desk reports: Latest only, at the bottom
  }
  for (const b of document.querySelectorAll("#food-view .chip")) {
    b.onclick = () => {
      foodView = b.dataset.fv; localStorage.setItem(FV_KEY, foodView);
      syncFoodView();
    };
  }
  addEventListener("storage", (e) => { if (e.key === SAVED_KEY) { savedSpots = readSaved(); syncSaved(); } });
  syncSaved(); syncFoodView();
  // ---------- in-app player / reader sheet: food videos play inside Chisme (YouTube's privacy-enhanced embed),
  // articles open in a reader sheet (framed only where the site allows it)
  const ytId = (u) => { const m = /(?:youtube(?:-nocookie)?\.com\/(?:watch\?(?:[^#]*&)?v=|shorts\/|embed\/|live\/)|youtu\.be\/)([\w-]{11})/.exec(u || ""); return m ? m[1] : null; };
  const isShort = (u) => /youtube\.com\/shorts\//.test(u || "");
  const ttId = (u) => { const m = /tiktok\.com\/(?:@[\w.]+\/video|player\/v1|embed(?:\/v2)?)\/(\d{15,20})/.exec(u || ""); return m ? m[1] : null; };
  const vidOf = (it) => { if (!it.video) return null; const y = ytId(it.url); if (y) return { yt: y }; const t = ttId(it.url); return t ? { tt: t } : null; };
  const hostOf = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return ""; } };
  function openLink(href, text, cls, open) {   // a real link (long-press/copy still work), but a tap opens the sheet
    const a = el("a", { href, class: cls, text, "aria-haspopup": "dialog" });
    a.onclick = (e) => { if (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return; e.preventDefault(); open(a); };
    return a;
  }
  function tapCard(card, open) {   // tapping anywhere on the card (not on its buttons/links) opens it too
    card.classList.add("tappable");
    card.addEventListener("click", (e) => { if (!e.target.closest("a, button, input, form, summary")) open(card.querySelector("h4 a") || card); });
    return card;
  }
  const player = $("#player");
  let playerItem = null, playerOpener = null;
  function placeLine(p) {
    return [el("span", { "aria-hidden": "true", text: "📍 " }), el("b", { text: p.name || p.address }), p.name && p.address ? " · " + p.address : "",
      p.guessed ? el("span", { class: "fs-guess", text: " (from the title)" }) : ""];
  }
  function renderPlayerMedia() {
    const it = playerItem, box = $("#player-media"), v = vidOf(it), id = v && (v.yt || v.tt);
    box.className = "player-media " + (id ? "video" + (v.tt || isShort(it.url) ? " tall" : "") + (v.tt ? " tiktok" : "") : it.frame ? "article framed" : "article");
    if (!navigator.onLine) {
      box.className = "player-media offline";
      box.replaceChildren(el("div", { class: "player-off", role: "status" },
        el("b", { text: "📡 You're offline" }),
        el("span", { text: id ? "This video will play here as soon as you're back online." : "The article will load when you're back online." }),
        it.noSave ? "" : el("span", { text: isSaved(it.url) ? "It's safe in 🔖 Saved spots." : "Tap 🔖 Save to keep it for later." })));
      return;
    }
    if (v && v.tt) {   // TikTok's official embed player (developers.tiktok.com/doc/embed-player)
      box.replaceChildren(el("iframe", { src: `https://www.tiktok.com/player/v1/${v.tt}?autoplay=1&rel=0&music_info=0&description=0`,
        title: "TikTok video: " + it.title, allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: "",
        referrerpolicy: "strict-origin-when-cross-origin" }));
    } else if (id) {
      box.replaceChildren(el("iframe", { src: `https://www.youtube-nocookie.com/embed/${id}?playsinline=1&rel=0&modestbranding=1&autoplay=1`,
        title: "YouTube video: " + it.title, allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: "",
        referrerpolicy: "strict-origin-when-cross-origin" }));
    } else if (it.checking) {   // asking the server whether this site can be shown inside Chisme
      box.className = "player-media article checking";
      box.replaceChildren(el("div", { class: "reader-wait", role: "status" }, el("span", { class: "spin", "aria-hidden": "true" }), "Opening inside Chisme…"));
    } else if (it.frame) {   // sandboxed: the page can't navigate Chisme away
      box.replaceChildren(el("iframe", { src: it.frameUrl || it.url, title: (it.reader ? "Page: " : "Article: ") + it.title, referrerpolicy: "strict-origin-when-cross-origin",
        sandbox: "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms" }));
    } else if (it.reader) {   // the site doesn't allow framing: a headline card (image, and a map when there's a place)
      const kids = [];
      if (it.image) { const img = el("img", { src: it.image, alt: "", referrerpolicy: "no-referrer", class: "player-img" }); img.onerror = () => img.remove(); kids.push(img); }
      else kids.push(el("div", { class: "reader-ph", "aria-hidden": "true", text: it.kind === "game" ? "🏟" : it.kind === "profile" ? "👤" : "📰" }));
      if (it.lat != null && it.lon != null) {   // events: where it is, on a small map (tap for the map sheet)
        const mm = miniMap({ lat: it.lat, lon: it.lon, venue: it.venue, address: it.address, title: it.title },
          `https://www.openstreetmap.org/?mlat=${it.lat.toFixed(5)}&mlon=${it.lon.toFixed(5)}#map=17/${it.lat.toFixed(5)}/${it.lon.toFixed(5)}`);
        mm.classList.add("reader-map"); kids.push(mm);
      }
      box.className = "player-media article card" + (kids.length > 1 ? " with-map" : "");
      box.replaceChildren(...kids);
    } else if (it.image) {
      const img = el("img", { src: it.image, alt: "", referrerpolicy: "no-referrer", class: "player-img" });
      img.onerror = () => img.remove();
      box.replaceChildren(img);
    } else box.replaceChildren();
  }
  function renderPlayer() {
    const it = playerItem, v = vidOf(it), vid = !!v;
    const saved = savedSpots.find((s) => s.url === it.url);
    const p = saved ? saved.place : it.place ? cleanPlace({ ...it.place, guessed: it.place.guessed !== false }) : null;
    $("#player-kind").textContent = vid ? "▶ Video" : it.kind === "game" ? "🏟 Game" : it.kind === "profile" ? "👤 Profile" : it.reader && it.frame ? "🔗 " + hostOf(it.frameUrl || it.url) : "📰 Article";
    $("#player-close").setAttribute("aria-label", vid ? "Close video" : "Close article");
    $("#player-title").textContent = it.title;
    $("#player-by").replaceChildren(el("b", { text: it.source || hostOf(it.url) }), it.site && it.source && !it.source.includes(it.site) ? " · " + it.site : "",
      it.when ? " · " + it.when : it.published ? " · " + shortDate(it.published) : "");
    $("#player-place").hidden = !p; $("#player-place").replaceChildren(...(p ? placeLine(p) : []));
    const sum = !vid && it.summary && !(it.reader && it.frame) && it.summary;
    $("#player-sum").hidden = !sum; $("#player-sum").textContent = sum || "";
    const acts = it.noSave ? [] : [saveButton(saved || it.raw || it)];
    if (p) { const city = saved ? saved.city : it.elsewhere ? "San Antonio, TX" : [cityName(), loc.place && loc.place.state].filter(Boolean).join(", ");
      const d = ext(mapsUrl(p, city), "Directions", "fs-dir", mapMeta(p, city)); d.setAttribute("aria-label", `Map and directions to ${p.name || p.address}`); acts.push(d); }
    const orig = $("#player-orig");
    orig.hidden = vid;
    if (!vid) {
      const host = hostOf(it.url), gn = host === "news.google.com";
      const site = it.source ? it.source.split(" · ")[0] : host;
      $("#player-note").hidden = !!it.checking;
      $("#player-note").textContent = it.frame ? `Showing ${hostOf(it.frameUrl || it.url)} inside Chisme. It's ${site}'s page, credited to them.`
        : !navigator.onLine ? `From ${site}. The full page needs a connection.`
        : gn ? `From ${site}, via Google News (it can't be shown inside other apps). Chisme shows the headline and the feed's summary, never the article itself.`
        : `From ${site}. Their site doesn't allow being shown inside other apps, so Chisme shows the headline and the site's own summary, never the article itself.`;
      const o = el("a", { href: it.url, class: "fs-open orig-link", target: "_blank", rel: "noopener", text: `Open original on ${hostOf(it.frameUrl || it.url) || site} ↗` });
      o.setAttribute("aria-label", `Open the original on ${hostOf(it.frameUrl || it.url) || site} (leaves Chisme)`);
      orig.replaceChildren(o);
    } else if (v.tt) {
      $("#player-note").hidden = false;
      $("#player-note").textContent = "Playing in TikTok's official player. Chisme only shows TikToks picked for this list.";
    } else $("#player-note").hidden = true;
    $("#player-actions").replaceChildren(...acts);
    renderPlayerMedia();
  }
  function openPlayer(raw, opener, opts = {}) {
    playerItem = { ...raw, raw, noSave: !!opts.noSave, source: raw.source || (raw.kind === "creator" ? raw.creator : [raw.outlet, raw.author].filter(Boolean).join(" · ")) };
    playerOpener = opener || document.activeElement;
    if (!opts.noSave && vidOf(raw) && !(feed && feed.open)) fySignal("open", raw);   // opened from the strip / Saved spots
    renderPlayer();
    if (!player.open) player.showModal();
    player.scrollTop = 0; player.style.transform = "";
  }
  // ---------- every outside link opens here (see ext()): the reader for pages, the map sheet for places
  const readerInfo = new Map();   // url -> /api/reader answer, for this session (the server caches too)
  const MAPISH = /^(maps\.apple\.com|(www\.)?google\.[a-z.]+\/maps|maps\.google\.|(www\.)?openstreetmap\.org\/(\?|$|#))/;
  function metaFromLink(a) {
    const m = linkMeta.get(a) || {};
    const txt = (a.textContent || "").replace(/[↗▶🔎🗺]/gu, "").replace(/\s+/g, " ").trim();
    return { url: a.href, ...m, title: m.title || a.getAttribute("data-title") || txt || hostOf(a.href), fromLink: !m.title };
  }
  document.addEventListener("click", (e) => {
    if (e.defaultPrevented || e.button > 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a || a.matches(".donate-btn, .orig-link")) return;
    let u; try { u = new URL(a.href); } catch { return; }
    if (DIRECT_HOSTS.has(u.hostname.replace(/^www\./, ""))) return;   // donate links leave on purpose
    if (u.origin === location.origin || !/^https?:$/.test(u.protocol)) return;
    e.preventDefault();
    const m = metaFromLink(a);
    const sEl = a.closest(".story[data-sid]");
    if (sEl && NO) { NO.markOpened(nsState, sEl.dataset.sid); nsSaveSoon(); }   // opened: it'll make room at the top next visit
    if (!m.map) tiaLearn(m, linkKind(a));   // what you read teaches la Tía (kept on this phone)
    if (m.map || MAPISH.test(u.host + u.pathname + u.search.slice(0, 1))) openMapSheet(m, a); else openReader(m, a);
  });
  function openReader(m, opener) {
    const url = m.url;
    const it = { url, title: m.title, source: m.source || hostOf(url), published: m.published || null, when: m.when || null, summary: m.summary || null,
      image: m.image || null, kind: m.kind || null, reader: true, frame: false, checking: navigator.onLine && !readerInfo.has(url),
      lat: m.lat ?? null, lon: m.lon ?? null, venue: m.venue || null, address: m.address || null };
    openPlayer(it, opener, { noSave: true });
    const done = (j) => {
      if (!playerItem || playerItem.url !== url) return;
      Object.assign(playerItem, { frame: !!j.frame, checking: false, frameUrl: j.final_url || url, site: j.site || null,
        title: m.fromLink && j.title ? j.title : playerItem.title, summary: playerItem.summary || j.description || null,
        image: playerItem.image || j.image || null, published: playerItem.published || j.published || null });
      renderPlayer();
    };
    if (!navigator.onLine) return;
    if (readerInfo.has(url)) return done(readerInfo.get(url));
    fetch("/api/reader?url=" + encodeURIComponent(url)).then((r) => r.json()).then((j) => { if (!j.limited) readerInfo.set(url, j); done(j); })
      .catch(() => done({ frame: false }));
  }
  // Map sheet: an OpenStreetMap map with a pin, inside Chisme; "Open in Maps" (Apple Maps directions) is the small link below.
  const mapDlg = $("#mapsheet");
  let sheetMap = null, sheetPin = null, mapOpener = null;
  function mapQuery(m) {   // name/address from the meta, else from the link itself (Apple ?daddr=, Google ?query=)
    if (m.address || m.name) return [m.address || m.name, m.address ? null : m.city].filter(Boolean).join(", ");
    try { const u = new URL(m.url); return u.searchParams.get("daddr") || u.searchParams.get("query") || u.searchParams.get("q") || ""; } catch { return ""; }
  }
  async function openMapSheet(m, opener) {
    mapOpener = opener || document.activeElement;
    const q = mapQuery(m), name = m.name || q.split(",")[0] || "Map";
    $("#ms-title").textContent = name;
    $("#ms-addr").textContent = m.address && m.address !== name ? m.address : q && q !== name ? q : "";
    $("#ms-status").textContent = "";
    const apple = "https://maps.apple.com/?daddr=" + encodeURIComponent(m.lat != null ? `${m.lat},${m.lon}` : q) + "&dirflg=d";
    const o = el("a", { href: /maps\.apple\.com/.test(m.url || "") ? m.url : apple, class: "orig-link", target: "_blank", rel: "noopener", text: "Open in Maps ↗" });
    o.setAttribute("aria-label", `Directions to ${name} in Apple Maps (leaves Chisme)`);
    $("#ms-orig").replaceChildren(o);
    if (!mapDlg.open) mapDlg.showModal();
    if (!sheetMap) {
      sheetMap = L.map("ms-map", { zoomControl: false, scrollWheelZoom: false, attributionControl: true }).setView([loc.lat, loc.lon], 13);
      L.control.zoom({ position: "topright" }).addTo(sheetMap);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(sheetMap);
      sheetMap.attributionControl.setPrefix(false);
    }
    setTimeout(() => sheetMap.invalidateSize(), 60);
    let lat = m.lat, lon = m.lon;
    if ((lat == null || lon == null) && q) {
      $("#ms-status").textContent = navigator.onLine ? "Finding it on the map…" : "The map needs a connection.";
      try {
        const j = await fetch("/api/geocode?q=" + encodeURIComponent(q.slice(0, 120))).then((r) => r.json());
        const r = (j.results || [])[0]; if (r) { lat = r.lat; lon = r.lon; }
      } catch {}
    }
    if (!mapDlg.open) return;
    if (lat == null || lon == null) { $("#ms-status").textContent = navigator.onLine ? "Couldn't find that address on the map. “Open in Maps” can still search for it." : "The map needs a connection."; return; }
    $("#ms-status").textContent = "";
    if (sheetPin) sheetPin.remove();
    sheetPin = L.marker([lat, lon], { keyboard: false, alt: name, icon: L.divIcon({ className: "ms-pin", iconSize: [26, 26], iconAnchor: [13, 26], html: "<span></span>" }) }).addTo(sheetMap);
    sheetMap.setView([lat, lon], 16);
    setTimeout(() => sheetMap.invalidateSize(), 250);
  }
  mapDlg.addEventListener("click", (e) => { if (e.target === mapDlg) mapDlg.close(); });
  $("#ms-close").onclick = () => mapDlg.close();
  mapDlg.addEventListener("close", () => { if (mapOpener && mapOpener.isConnected) mapOpener.focus({ preventScroll: true }); });
  player.addEventListener("close", () => {
    $("#player-media").replaceChildren();   // stops the video
    player.style.transform = ""; player.classList.remove("dragging"); playerItem = null;
    if (playerOpener && playerOpener.isConnected) playerOpener.focus({ preventScroll: true });
  });
  player.addEventListener("click", (e) => { if (e.target === player) player.close(); });   // tap outside the sheet
  $("#player-close").onclick = () => player.close();
  addEventListener("online", () => { if (player.open && playerItem && $("#player-media").classList.contains("offline")) renderPlayerMedia(); });
  // swipe down to close (from the top bar, or anywhere while the sheet is scrolled to the top; the video itself keeps its own touches)
  let sheetDrag = null;
  player.addEventListener("touchstart", (e) => {
    if (e.touches.length !== 1 || (player.scrollTop > 0 && !e.target.closest(".player-head"))) { sheetDrag = null; return; }
    sheetDrag = { y: e.touches[0].clientY, x: e.touches[0].clientX, dy: 0, lock: null };
  }, { passive: true });
  player.addEventListener("touchmove", (e) => {
    if (!sheetDrag) return;
    const dy = e.touches[0].clientY - sheetDrag.y, dx = e.touches[0].clientX - sheetDrag.x;
    if (!sheetDrag.lock) { if (Math.abs(dy) < 8 && Math.abs(dx) < 8) return; sheetDrag.lock = dy > 0 && dy > Math.abs(dx) ? "y" : "no"; }
    if (sheetDrag.lock !== "y") return;
    e.preventDefault();
    sheetDrag.dy = Math.max(0, dy);
    player.classList.add("dragging"); player.style.transform = `translateY(${sheetDrag.dy}px)`;
  }, { passive: false });
  const endSheetDrag = () => {
    if (!sheetDrag) return;
    const go = sheetDrag.lock === "y" && sheetDrag.dy > 90;
    player.classList.remove("dragging"); player.style.transform = "";
    sheetDrag = null;
    if (go) player.close();
  };
  player.addEventListener("touchend", endSheetDrag); player.addEventListener("touchcancel", endSheetDrag);
  // ---------- ¿Cuál dieta? For You: a full-screen vertical feed (one video per screen, scroll-snap), ranked on this
  // phone by static/foryou.js from what you watch, save and skip. Nothing is sent to the server.
  const FY = window.ChismeForYou || null;
  let fyProfile = FY ? FY.load() : null;
  const fySignal = (kind, it, opts) => { if (!FY || !it || !it.url) return; fyProfile = FY.signal(FY.load(), kind, it, opts); FY.save(fyProfile); renderForYouCard(); };
  const feed = $("#feed"), feedScroll = $("#feed-scroll");
  let feedList = [], feedCur = -1, feedT0 = 0, feedMuted = true, feedPlaying = true, feedTimer = null, feedPushed = false, feedOpener = null;
  // the local creators' videos + cooking / recipe videos from many cooks (the ranker mixes them: every 3rd is a recipe)
  const feedVideos = () => (foodData && foodData.items ? foodData.items.concat(foodData.recipes || []).filter((i) => vidOf(i)) : []);
  const canAutoplay = () => navigator.onLine && !reducedMotion() && !(navigator.connection && navigator.connection.saveData);
  // Rotation: every visit (and every time you close the feed) a different creator leads, and the one who led
  // last time never leads again. The banner cover and the feed come from the same ranked list, so they match.
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch {} };
  let fyRot = (+lsGet("chisme-foryou-rot") || 0) + 1, fyAvoid = lsGet("chisme-foryou-lead"), fyList = [];
  lsSet("chisme-foryou-rot", String(fyRot));
  const fyRank = () => FY.rank(fyProfile || FY.load(), feedVideos(), { rot: fyRot, lastLead: fyAvoid });
  function renderCover() {
    const cover = $("#fy-cover"), next = $("#fy-next");
    if (!cover) return;
    const top = fyList.slice(0, 3);
    cover.replaceChildren(...top.map((r, i) => {
      const t = el("span", { class: "fy-tile" });
      if (r.item.image && navigator.onLine) { const im = el("img", { src: r.item.image, alt: "", referrerpolicy: "no-referrer", loading: "eager" }); im.onerror = () => im.remove(); t.append(im); }
      t.append(el("span", { class: "fy-tile-by", text: r.item.creator || r.item.source || "" }));
      t.onclick = () => openFeed($("#fy-start"), i);
      return t;
    }));
    cover.hidden = !top.length;
    const people = new Set(fyList.map((r) => r.crew)).size, more = people - new Set(top.map((r) => r.crew)).size;
    next.textContent = top.length ? `Up next: ${top.map((r) => r.item.creator || r.item.source).join(" · ")}${more > 0 ? ` + ${more} more creators` : ""}` : "";
    next.hidden = !top.length;
  }
  function renderForYouCard() {
    const card = $("#foryou-card");
    if (!card) return;
    const vids = feedVideos();
    card.hidden = !FY || !foodData || !!foodData.message;
    if (card.hidden) return;
    const sa = !foodData.metro || !!foodData.metro.in_sa;
    $("#fy-sub").textContent = sa
      ? "SA's food spots plus easy recipes to cook at home. Swipe up for the next bite; every save and skip makes it smarter, right on your phone."
      : "San Antonio's food creators plus easy recipes to cook at home, one video at a time. It learns what you crave from what you watch, save and skip.";
    if (!feed.open) {
      fyList = vids.length ? fyRank() : [];
      if (fyList[0]) lsSet("chisme-foryou-lead", fyList[0].crew);   // next visit leads with someone else
      renderCover();
    }
    const n = fyList.length || vids.length;
    const likes = FY.interests(fyProfile || FY.load(), 3);
    $("#fy-meta").textContent = !vids.length ? "No videos in the feeds right now — check back soon."
      : likes.length ? `Tuned to you: ${likes.join(", ")}. ${n} videos ready.`
      : `${n} videos ready. No account, no tracking: it all stays on this phone.`;
    $("#fy-start").disabled = !vids.length;
  }
  // ---------- the players, TikTok-style. The video on screen plays by itself (always started muted: that's the only
  // autoplay iPhone Safari allows; sound goes on once it's playing, if you asked for it and the browser lets it). The next
  // PRELOAD_AHEAD players are created ahead of time and warmed: started muted and held on their first frame, so a swipe
  // lands on a video that's ready. The one you just left stays (paused) for a quick swipe back; farther ones are unloaded.
  const PRELOAD_AHEAD = 2, KEEP_BEHIND = 1, PREFETCH_AHEAD = 3;
  let soundWanted = false;   // you turned 🔊 on: every next video tries sound too
  function ytCmd(frame, func, args = []) { try { frame.contentWindow.postMessage(JSON.stringify({ event: "command", func, args }), "*"); } catch {} }
  function ttCmd(frame, type, value) { try { frame.contentWindow.postMessage({ "x-tiktok-player": true, type, value }, "*"); } catch {} }
  function feedCommand(slide, what) {   // what: play | pause | mute | unmute | rewind
    const f = slide && slide.querySelector(".vf-frame");
    if (!f) return;
    if (f.dataset.kind === "yt") {
      if (what === "rewind") ytCmd(f, "seekTo", [0, true]);
      else ytCmd(f, { play: "playVideo", pause: "pauseVideo", mute: "mute", unmute: "unMute" }[what]);
    } else if (what === "rewind") ttCmd(f, "seekTo", 0);
    else ttCmd(f, { play: "play", pause: "pause", mute: "mute", unmute: "unMute" }[what]);
  }
  const isCur = (s) => !!s && slides()[feedCur] === s;
  function setUi(s, playing) {   // playing: the info overlay gets out of the way; paused: it's back (tap toggles)
    s.classList.toggle("vf-playing", !!playing); s.classList.toggle("vf-paused", !playing);
    const st = s.querySelector(".vf-state");
    if (st) { st.textContent = "▶"; st.classList.toggle("hold", !playing && !s.classList.contains("vf-tap") && !s.classList.contains("vf-loading")); }
  }
  function armReveal(s) {   // the thumbnail stays on top until the player says it's playing; after 5 s, show the player + "Tap to play"
    clearTimeout(s._reveal);
    if (!s.classList.contains("vf-loading")) return;
    s._reveal = setTimeout(() => { if (s.classList.contains("vf-loading")) { s.classList.remove("vf-loading"); s.classList.add("vf-tap"); if (isCur(s)) setUi(s, false); } }, 5000);
  }
  function mountFrame(slide, it, mode) {   // mode: "play" (on screen) or "warm" (preloaded, held on its first frame)
    const v = vidOf(it), media = slide.querySelector(".vf-media");
    if (mode === "play") { media.querySelector(".vf-play")?.remove(); media.querySelector(".vf-off")?.remove(); }
    if (!navigator.onLine) { if (mode === "play") media.append(el("p", { class: "vf-off", role: "status", text: "📡 You're offline — this video plays as soon as you're back." })); return; }
    if (slide.querySelector(".vf-frame")) return;
    media.querySelector(".vf-play")?.remove();
    const origin = encodeURIComponent(location.origin);
    const src = v.tt
      ? `https://www.tiktok.com/player/v1/${v.tt}?autoplay=1&loop=1&rel=0&music_info=0&description=0&controls=0&play_button=0&volume_control=0&fullscreen_button=0&progress_bar=1`
      : `https://www.youtube-nocookie.com/embed/${v.yt}?playsinline=1&rel=0&modestbranding=1&controls=0&loop=1&playlist=${v.yt}&autoplay=1&mute=1&enablejsapi=1&origin=${origin}`;
    const f = el("iframe", { class: "vf-frame", src, title: (v.tt ? "TikTok video: " : "YouTube video: ") + it.title, "data-kind": v.tt ? "tt" : "yt",
      allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: "", referrerpolicy: "strict-origin-when-cross-origin" });
    if (mode === "warm") { f.tabIndex = -1; slide.dataset.warm = "1"; }
    f.addEventListener("load", () => {
      if (v.yt) try { f.contentWindow.postMessage(JSON.stringify({ event: "listening", id: 1, channel: "widget" }), "*"); } catch {}   // ask YouTube for state events
      feedCommand(slide, "mute");
      if (isCur(slide) && feedPlaying) feedCommand(slide, "play");
    });
    slide.classList.add("vf-loading");
    media.append(f);
    // the shield takes the touches so vertical swipes scroll the feed; a tap pauses/plays and shows/hides the info
    const shield = el("button", { type: "button", class: "vf-shield", "aria-label": "Pause or play" }), st = el("span", { class: "vf-state", "aria-hidden": "true" });
    if (mode === "warm") shield.tabIndex = -1;
    shield.onclick = () => {
      if (!isCur(slide)) return;
      if (slide.classList.contains("vf-tap")) {   // autoplay didn't start: this tap starts it
        slide.classList.remove("vf-tap"); feedPlaying = true; feedCommand(slide, "play"); setUi(slide, true); fySignal("open", it); return;
      }
      feedPlaying = !feedPlaying; feedCommand(slide, feedPlaying ? "play" : "pause"); setUi(slide, feedPlaying);
    };
    media.append(shield, st);
    if (mode === "play") armReveal(slide);
  }
  function onPlayerState(s, state) {
    s._st = state;
    const now = Date.now();
    if (state === 1) {   // playing
      s.classList.remove("vf-loading", "vf-tap"); s.dataset.playing = "1"; clearTimeout(s._reveal);
      if (!isCur(s)) { feedCommand(s, "pause"); s.dataset.warm = "ready"; return; }   // preloaded: hold it on its first frame (rewound when it comes on)
      if (!feedPlaying) { feedCommand(s, "pause"); return; }
      setUi(s, true); warmSoon(0);   // the one on screen is playing: now warm up the next ones
      if (soundWanted && !s._soundBlocked && !s._triedSound) { s._triedSound = now; feedCommand(s, "unmute"); }
    } else if (state === 2 && isCur(s) && feedPlaying && soundWanted && s._triedSound && now - s._triedSound < 2500) {
      // the browser stopped it as soon as sound went on (iPhone Safari does this without a tap): back to muted, keep playing
      s._soundBlocked = true; feedCommand(s, "mute"); feedCommand(s, "play"); updateSoundBtn();
    }
  }
  addEventListener("message", (e) => {   // play-state events from the YouTube / TikTok players in the feed
    if (!feed.open || !/youtube-nocookie\.com$|tiktok\.com$/.test(hostOf(e.origin))) return;
    let d = e.data; if (typeof d === "string") { try { d = JSON.parse(d); } catch { return; } }
    if (!d) return;
    const state = d["x-tiktok-player"] ? (d.type === "onStateChange" ? d.value : null)
      : d.event === "onStateChange" ? d.info : d.event === "infoDelivery" && d.info && "playerState" in d.info ? d.info.playerState : null;
    if (state == null) return;
    const s = [...document.querySelectorAll(".vf-frame")].find((f) => f.contentWindow === e.source)?.closest(".vf-slide");
    if (s) onPlayerState(s, state);
  });
  function unmountFrame(slide) {
    if (!slide) return;
    clearTimeout(slide._reveal); slide.classList.remove("vf-loading", "vf-tap", "vf-playing", "vf-paused");
    delete slide.dataset.playing; delete slide.dataset.warm; slide._st = null; slide._triedSound = 0; slide._soundBlocked = false;
    slide.querySelectorAll(".vf-frame, .vf-shield, .vf-state, .vf-off").forEach((n) => n.remove());
    const thumb = slide.querySelector(".vf-thumb"); if (thumb) thumb.hidden = false;
    if (!slide.querySelector(".vf-play") && slide.dataset.url) addPlayButton(slide);
  }
  function addPlayButton(slide) {
    const it = feedList.find((x) => x.item.url === slide.dataset.url)?.item;
    if (!it) return;
    const b = el("button", { type: "button", class: "vf-play" }, el("b", { text: "▶", "aria-hidden": "true" }), "Tap to play");
    b.setAttribute("aria-label", "Play: " + it.title);
    b.onclick = () => { fySignal("open", it); feedPlaying = true; mountFrame(slide, it, "play"); setUi(slide, true); slide.querySelector(".vf-shield")?.focus(); };
    slide.querySelector(".vf-media").append(b);
  }
  function feedSlide(r, i) {
    const it = r.item, v = vidOf(it), tall = !!(v.tt || isShort(it.url));
    const saved = savedSpots.find((s) => s.url === it.url);
    const p = saved ? saved.place : it.place ? cleanPlace({ ...it.place, guessed: it.place.guessed !== false }) : null;
    const media = el("div", { class: "vf-media" });
    if (it.image) {
      const bg = el("img", { class: "vf-bg", src: it.image, alt: "", referrerpolicy: "no-referrer", loading: i < 2 ? "eager" : "lazy" });
      const th = el("img", { class: "vf-thumb", src: it.image, alt: "", referrerpolicy: "no-referrer", loading: i < 2 ? "eager" : "lazy" });
      bg.onerror = () => bg.remove(); th.onerror = () => th.remove();
      media.append(bg, th);
    }
    const whyId = "why" + i;
    const chip = el("button", { type: "button", class: "why-chip " + r.why.kind, "aria-expanded": "false", "aria-controls": whyId },
      el("span", { "aria-hidden": "true", text: r.explore ? "🧭" : "✨" }), r.why.text);
    chip.setAttribute("aria-label", "Why you're seeing this: " + r.why.text);
    const more = el("p", { class: "why-more", id: whyId, hidden: "" ,
      text: (r.explore ? "About 1 in 5 videos is something different, so your feed doesn't get stuck on one thing. " : "")
        + "Bigger the Pansa, Better the Chansa ranks these videos on this phone from what you watch, save and skip. Nothing leaves your phone; reset it anytime in Settings." });
    chip.onclick = () => { const o = more.hidden; more.hidden = !o; chip.setAttribute("aria-expanded", String(o)); };
    const by = [it.creator || it.source, v.tt ? "TikTok" : "YouTube"].filter(Boolean).join(" · ") + (it.published ? " · " + shortDate(it.published) : "");
    const info = el("div", { class: "vf-info" }, chip, more, el("h3", { text: it.title }), el("p", { class: "vf-by", text: by }),
      p ? el("p", { class: "vf-place" }, ...placeLine(p)) : null,
      it.recipe ? el("p", { class: "vf-place vf-recipe" }, el("span", { "aria-hidden": "true", text: "🍳 " }), "Recipe · cook it at home") : null,
      it.elsewhere ? el("p", { class: "vf-by", text: "A San Antonio spot" }) : null);
    const rail = el("div", { class: "vf-rail" });
    const sv = saveButton(saved || it); rail.append(sv);
    if (p) {
      const city = saved ? saved.city : it.elsewhere ? "San Antonio, TX" : [cityName(), loc.place && loc.place.state].filter(Boolean).join(", ");
      const d = ext(mapsUrl(p, city), "", "vf-dir", mapMeta(p, city));
      d.replaceChildren(el("span", { class: "ic", "aria-hidden": "true", text: "📍" }), "Directions");
      d.setAttribute("aria-label", `Map and directions to ${p.name || p.address}`);
      rail.append(d);
    }
    const ni = el("button", { type: "button", class: "vf-ni" }, el("span", { class: "ic", "aria-hidden": "true", text: "🙅" }), "Not for me");
    ni.setAttribute("aria-label", "Not interested: " + it.title);
    ni.onclick = () => notInterested(r);
    const full = el("button", { type: "button", class: "vf-full" }, el("span", { class: "ic", "aria-hidden": "true", text: "⤢" }), "Details");
    full.setAttribute("aria-label", "Open the full player: " + it.title);
    full.onclick = () => { unmountFrame(slides()[feedCur]); openPlayer(it, full); };
    rail.append(ni, full);
    const slide = el("section", { class: "vf-slide" + (tall ? " tall" : ""), "data-url": it.url, "aria-roledescription": "video", "aria-label": `${i + 1} of ${feedList.length}: ${it.title}` }, media, info, rail);
    return slide;
  }
  const slides = () => [...feedScroll.querySelectorAll(".vf-slide")];
  function endSlide() {
    const again = el("button", { type: "button", class: "fy-start" }, el("span", { "aria-hidden": "true", text: "↺" }), "Watch again from the top");
    again.onclick = () => { feedScroll.scrollTo({ top: 0, behavior: "instant" }); };
    const back = el("button", { type: "button", class: "feed-btn", text: "Back to ¿Cuál dieta?" });
    back.onclick = () => closeFeed();
    return el("section", { class: "vf-slide vf-end", "aria-label": "End of the feed" }, el("h3", { text: "¡Ya! You're all caught up." }),
      el("p", { text: "Keep saving and skipping — the next batch of videos lines up around what you liked." }), again, back);
  }
  function finishCurrent(moving) {   // turn the time spent on the current video into a signal
    const s = slides()[feedCur];
    if (!s || !s.dataset.url || !feedT0) return;
    const it = feedList.find((x) => x.item.url === s.dataset.url)?.item, secs = (Date.now() - feedT0) / 1000;
    feedT0 = 0;
    if (!it) return;
    if (secs >= 3) fySignal("watch", it, { seconds: secs });
    else if (moving && secs < 2) fySignal("skip", it);
  }
  function startSlide(s, it) {   // the video on screen: play it from the top, muted first; the info hides while it plays
    s._triedSound = 0; s._soundBlocked = false; feedPlaying = true;
    s.querySelector(".vf-play")?.remove();
    const f = s.querySelector(".vf-frame");
    if (!f) mountFrame(s, it, "play");
    else {
      f.tabIndex = 0; s.querySelector(".vf-shield")?.removeAttribute("tabindex");
      if (!s.dataset.playing) { s.classList.add("vf-loading"); armReveal(s); }   // a warmed player is already on its first frame: no spinner
      feedCommand(s, "mute"); feedCommand(s, "rewind"); feedCommand(s, "play");
      if (s._st === 1 && soundWanted) { s._triedSound = Date.now(); feedCommand(s, "unmute"); }
    }
    setUi(s, true); updateSoundBtn();
  }
  // the video on screen gets the network first; the next ones are warmed once it plays (or after 1.2 s at most)
  let warmTimer = null;
  function warmSoon(ms) { clearTimeout(warmTimer); warmTimer = setTimeout(() => { if (feed.open) syncWindow(true); }, ms); }
  function syncWindow(preload) {   // preload the next PRELOAD_AHEAD, keep KEEP_BEHIND, unload the rest; warm the pictures a bit farther
    const all = slides(), warm = canAutoplay();
    all.forEach((s, k) => {
      if (!s.dataset.url || k === feedCur) return;
      const ahead = k > feedCur && k <= feedCur + PRELOAD_AHEAD, behind = k < feedCur && k >= feedCur - KEEP_BEHIND;
      if (k > feedCur && k <= feedCur + PREFETCH_AHEAD) s.querySelectorAll('img[loading="lazy"]').forEach((im) => { im.loading = "eager"; });
      if (warm && ahead && !preload) return;   // not yet: leave it as it is until warmSoon()
      if (warm && ahead) { const r = feedList.find((x) => x.item.url === s.dataset.url); if (r && !s.querySelector(".vf-frame")) mountFrame(s, r.item, "warm"); }
      else if (behind && s.querySelector(".vf-frame")) { feedCommand(s, "pause"); s.classList.remove("vf-playing"); }
      else if (s.querySelector(".vf-frame, .vf-shield, .vf-off")) unmountFrame(s);
    });
  }
  function activate(i) {
    const all = slides();
    i = Math.max(0, Math.min(all.length - 1, i));
    if (i === feedCur) return;
    finishCurrent(true);
    const prev = all[feedCur];
    if (prev) { feedCommand(prev, "pause"); feedCommand(prev, "mute"); prev.classList.remove("vf-playing", "vf-paused"); prev.querySelector(".vf-state")?.classList.remove("hold"); }
    feedCur = i;
    const s = all[i], r = s && feedList.find((x) => x.item.url === s.dataset.url);
    $("#feed-pos").textContent = r ? `${feedList.indexOf(r) + 1} / ${feedList.length}` : "";
    if (r) {
      feedT0 = Date.now();
      if (canAutoplay()) startSlide(s, r.item);
      else { s.querySelector(".vf-play")?.remove(); if (s.querySelector(".vf-frame")) { feedPlaying = true; feedCommand(s, "play"); setUi(s, true); } else addPlayButton(s); }
    }
    syncWindow(); warmSoon(1200); updateSoundBtn();
  }
  const nearest = () => Math.round(feedScroll.scrollTop / Math.max(1, feedScroll.clientHeight));
  feedScroll.addEventListener("scroll", () => { clearTimeout(feedTimer); feedTimer = setTimeout(() => activate(nearest()), 140); }, { passive: true });
  function notInterested(r) {
    const s = slides().find((x) => x.dataset.url === r.item.url);
    if (!s) return;
    const idx = feedList.indexOf(r);
    feedT0 = 0; fySignal("not_interested", r.item);
    unmountFrame(s); const next = s.nextElementSibling; s.remove(); feedList.splice(idx, 1);
    feedCur = -1; activate(nearest());
    const toast = $("#feed-toast"), u = el("button", { type: "button", text: "Undo" });
    u.onclick = () => {
      fySignal("undo_not_interested", r.item);
      feedList.splice(idx, 0, r); (next && next.isConnected ? next.before(s) : feedScroll.append(s)); s.querySelector(".vf-play")?.remove();
      feedCur = -1; s.scrollIntoView({ behavior: "instant", block: "start" }); activate(slides().indexOf(s)); toast.replaceChildren();
    };
    toast.replaceChildren(el("span", { text: "Got it — fewer like this." }), u);
    clearTimeout(notInterested.t); notInterested.t = setTimeout(() => toast.replaceChildren(), 6000);
    (slides()[feedCur]?.querySelector(".vf-rail button") || $("#feed-close")).focus({ preventScroll: true });
  }
  function openFeed(opener, startAt) {
    if (!FY) return;
    const vids = feedVideos();
    if (!vids.length) return;
    fyProfile = FY.load();
    feedList = fyRank();   // same list as the banner cover
    feedOpener = opener || document.activeElement;
    feedScroll.replaceChildren(...feedList.map(feedSlide), endSlide());
    feedCur = -1; $("#feed-toast").replaceChildren();
    document.documentElement.classList.add("feed-open");
    if (!feed.open) feed.showModal();
    if (!feedPushed) { history.pushState({ chismeFeed: 1 }, ""); feedPushed = true; }
    const at = Math.max(0, Math.min(feedList.length - 1, startAt || 0));
    feedScroll.scrollTop = at * feedScroll.clientHeight; activate(at);
    $("#feed-close").focus({ preventScroll: true });
  }
  function closeFeed(fromHistory) {
    if (!feed.open) return;
    finishCurrent(false); slides().forEach(unmountFrame);
    feedScroll.replaceChildren(); feedCur = -1;
    feed.close(); document.documentElement.classList.remove("feed-open");
    if (feedList[0]) fyAvoid = feedList[0].crew;   // next time, someone else leads
    fyRot += 1; lsSet("chisme-foryou-rot", String(fyRot));
    if (feedPushed) { feedPushed = false; if (!fromHistory && history.state && history.state.chismeFeed) history.back(); }
    renderForYouCard();
    if (feedOpener && feedOpener.isConnected) feedOpener.focus({ preventScroll: true });
  }
  addEventListener("popstate", () => { if (feed.open) { feedPushed = false; closeFeed(true); } });
  feed.addEventListener("cancel", (e) => { e.preventDefault(); if (!player.open) closeFeed(); });   // Esc / iOS back gesture on the dialog
  $("#feed-close").onclick = () => closeFeed();
  $("#fy-start").onclick = (e) => openFeed(e.currentTarget, 0);
  function updateSoundBtn() {
    const b = $("#feed-sound"), s = slides()[feedCur], blocked = soundWanted && !!(s && s._soundBlocked);
    feedMuted = !soundWanted || blocked;
    b.setAttribute("aria-pressed", String(!feedMuted));
    b.replaceChildren(el("span", { "aria-hidden": "true", text: feedMuted ? "🔇" : "🔊" }), blocked ? " Tap for sound" : feedMuted ? " Muted" : " Sound on");
  }
  $("#feed-sound").onclick = () => {   // a real tap: the one moment every browser lets sound start
    const s = slides()[feedCur];
    if (soundWanted && s && s._soundBlocked) { s._soundBlocked = false; s._triedSound = 0; feedCommand(s, "unmute"); feedCommand(s, "play"); }
    else {
      soundWanted = !soundWanted;
      if (s) { s._triedSound = soundWanted ? Date.now() : 0; s._soundBlocked = false; feedCommand(s, soundWanted ? "unmute" : "mute"); }
    }
    updateSoundBtn();
  };
  feed.addEventListener("keydown", (e) => {
    if (player.open || e.target.closest("input, textarea")) return;
    const step = { ArrowDown: 1, PageDown: 1, j: 1, ArrowUp: -1, PageUp: -1, k: -1 }[e.key];
    if (step) { e.preventDefault(); const t = slides()[Math.max(0, Math.min(slides().length - 1, nearest() + step))]; if (t) feedScroll.scrollTo({ top: t.offsetTop, behavior: reducedMotion() ? "instant" : "smooth" }); }
  });
  player.addEventListener("close", () => { if (feed.open && feedCur >= 0) { const s = slides()[feedCur]; feedCur = -1; if (s) { s.querySelector(".vf-play")?.remove(); activate(slides().indexOf(s)); } } });
  addEventListener("online", () => { if (feed.open) { const i = feedCur; feedCur = -1; activate(i); } });
  function foodItem(it) {
    const open = (a) => openPlayer(it, a);
    const thumb = el("a", { class: "fr-thumb", href: it.url, tabindex: "-1", "aria-hidden": "true" });
    thumb.onclick = (e) => { e.preventDefault(); open(thumb.parentNode.querySelector("h4 a")); };
    const ph = () => el("div", { class: "ev-ph", role: "img", "aria-label": it.image ? "Photo loads when you're online" : "No photo in the feed" },
      el("b", { text: it.video ? "🎥" : "📰", "aria-hidden": "true" }), el("span", { text: it.image ? "offline" : "no photo" }));
    if (it.image && navigator.onLine) {
      const img = el("img", { src: it.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.replaceWith(ph());
      thumb.append(img);
      if (it.video) thumb.append(el("span", { class: "play", text: "▶" }));
    } else thumb.append(ph());
    const by = it.kind === "creator" ? `${it.creator}` + (it.platform === "tiktok" ? " · TikTok" : "") : [it.outlet, it.author].filter(Boolean).join(" · ");
    return tapCard(el("article", { class: "fr" + (it.kind === "creator" ? " fr-card" : "") }, thumb,
      el("div", { class: "fr-body" },
        el("h4", {}, openLink(it.url, it.title, null, open)),
        el("p", { class: "fr-by" }, el("b", { text: by }), it.published ? " · " + shortDate(it.published) : ""),
        it.summary ? el("p", { class: "fr-sum", text: it.summary }) : null,
        el("div", { class: "fr-actions" }, openLink(it.url, it.video ? "▶ Watch" : "Read", "fr-go", open), saveButton(it)))), open);
  }
  function deskItem(it) {   // food desk reports: a compact text list (most come without photos)
    const open = (a) => openPlayer(it, a);
    return tapCard(el("article", { class: "desk" },
      el("div", { class: "desk-body" },
        el("h4", {}, openLink(it.url, it.title, null, open)),
        el("p", { class: "fr-by" }, el("b", { text: [it.outlet, it.author].filter(Boolean).join(" · ") }), it.published ? " · " + shortDate(it.published) : "")),
      saveButton(it)), open);
  }
  function renderCrew(list, sa) {   // profile link cards for every creator Chisme follows (Instagram-only ones included)
    $("#food-crew").hidden = !list.length;
    $("#food-crew-list").replaceChildren(...list.map((c) => {
      const links = [];
      const cm = (net, h) => ({ title: `${c.name} on ${net}`, source: net + (h ? " · @" + h : ""), kind: "profile",
        summary: [c.person, c.uses, sa ? null : c.city].filter(Boolean).join(" · ") || null });
      if (c.youtube) links.push(ext(c.youtube, "▶ YouTube", "crew-link", cm("YouTube")));
      if (c.tiktok) links.push(ext("https://www.tiktok.com/@" + c.tiktok, "TikTok", "crew-link", cm("TikTok", c.tiktok)));
      if (c.instagram) links.push(ext("https://www.instagram.com/" + c.instagram + "/", (c.youtube || c.tiktok ? "Instagram" : "See their posts on Instagram"), "crew-link" + (c.youtube || c.tiktok ? "" : " primary"), cm("Instagram", c.instagram)));
      for (const l of links) l.setAttribute("aria-label", `${l.textContent.replace(/[▶↗]/g, "").trim()}: ${c.name} (opens in Chisme)`);
      const handle = c.instagram || c.tiktok;
      return el("li", { class: "crew" },
        el("p", { class: "crew-name" }, el("b", { text: c.name }), handle ? el("span", { class: "crew-h", text: " @" + handle }) : ""),
        el("p", { class: "crew-by", text: [c.person, sa ? null : c.city].filter(Boolean).join(" · ") }),
        el("p", { class: "crew-uses" + (/only/i.test(c.uses || "") ? " ig" : ""), text: c.uses || "" }),
        el("div", { class: "crew-links" }, ...links));
    }));
  }
  function renderFood() {
    const n = foodData;
    if (!n) return;
    if (n.message) {
      $("#food-creators").replaceChildren(el("p", { class: "loading", text: n.message + " ¡Lo siento!" }));
      $("#food-outlets").replaceChildren(); syncFoodView();
      return;
    }
    const m = n.metro || {}, sa = n.metro ? !!m.in_sa : true, city = n.city || m.city || "your area";
    const cr = n.items.filter((i) => i.kind === "creator"), out = n.items.filter((i) => i.kind === "outlet");
    // San Antonio: its creators first, the food desks at the bottom. Elsewhere: that city's food news first, then
    // San Antonio's creators, clearly labeled as San Antonio (they review SA spots).
    $("#antojos-intro").textContent = sa
      ? "Diet? Not today. San Antonio's food creators taste-test so you don't have to guess. Watch right here, and 🔖 save the spots worth the drive."
      : `Diet? Not today. Here's what's cooking in ${city}: fresh from the local food desks. Tap to read right here, and 🔖 save the spots worth the drive.`;
    $("#food-latest-h").textContent = sa ? "Fresh from local food creators" : "Road-trip picks: San Antonio's food creators";
    $("#food-intro").textContent = sa ? "Swipe sideways for more. The reviews are theirs; tap one to watch it right here, or 🔖 Save it for later."
      : `These creators review San Antonio spots, not ${city} — save one for your next trip to SA. Swipe sideways for more.`;
    $("#food-desk-h").textContent = sa ? "From the food desks" : `${city} food news`;
    if (sa) $("#food-block").after($("#food-desk")); else $("#food-latest").before($("#food-desk"));
    $("#food-creators").replaceChildren(...(cr.length ? cr.map(foodItem) : [el("p", { class: "loading", text: "The creators are between bites — no new videos lately." })]));
    const bySrc = {}; for (const i of out) (bySrc[i.source_id] = bySrc[i.source_id] || []).push(i);
    const desk = [], queues = Object.values(bySrc);   // take the newest from each food desk in turn, 5 max
    while (desk.length < 5 && queues.some((q) => q.length)) for (const q of queues) if (q.length && desk.length < 5) desk.push(q.shift());
    desk.sort((a, b) => (b.published || 0) - (a.published || 0));
    $("#food-outlets").replaceChildren(...(desk.length ? desk.map(deskItem) : [el("p", { class: "loading", text: "No new food coverage in the feeds right now." })]));
    renderCrew(n.creators || [], sa);
    syncFoodView(); renderForYouCard();
    $("#food-sources").replaceChildren(...(n.sources || []).map((f) => el("li", { class: f.ok ? "" : "bad" },
      ext(f.home, f.name), f.elsewhere && !(n.metro || {}).in_sa ? " (San Antonio creator)" : "", f.ok ? (f.platform === "tiktok" ? `: ${f.count} hand-picked TikTok${f.count === 1 ? "" : "s"}` : `: ${f.count} recent ${f.kind === "creator" ? "videos" : "stories"}`) : `: unavailable right now (${f.error})`)));
  }
  section("food", {
    url: () => `/api/food?${q()}`,
    apply: (n, { saved }) => { foodData = n; foodFresh = foodFresh || !saved; renderFood(); $("#food-updated").textContent = stampFor(saved, n); },
    fail: (e) => { if (!foodData) $("#food-creators").replaceChildren(el("p", { class: "error", text: "¡Ay! Couldn't reach the food feeds (" + e.message + "). We'll keep trying." })); },
  });
  let foodFresh = false;
  const loadFood = () => load("food");

  let evRetry = null, evRetries = 0;
  section("events", {
    url: () => `/api/events?${q()}`,
    loading: () => $("#events-list").replaceChildren(el("p", { class: "loading", text: `Rounding up the pachangas near ${shortPlace()}…` })),
    fail: (e) => $("#events-list").replaceChildren(el("p", { class: "error", text: "¡Ay! Couldn't reach the event calendars (" + e.message + "). We'll keep trying." })),
    apply: (n, { saved }) => {
      clearTimeout(evRetry);
      if (!saved) rendered.events = q();
      const where = shortPlace();
      const list = n.events || [], ongoing = n.ongoing || [];
      $("#events-title").textContent = n.place && n.place.city ? `What's happening in ${n.place.city}` : "What's happening";
      $("#events-intro").textContent = list.length
        ? pick([`¡Órale! ${list.length} things going on around ${where} in the next few weeks.`,
                `¿Qué hay de nuevo? ${list.length} upcoming events near ${where} — pick your pachanga.`,
                `Get off the couch, ${where}! ${list.length} events coming up nearby.`])
        : n.message ? `${n.message} ¡Lo siento! News, radar and search still work here.`
        : `Quiet around here, huh? No upcoming events found near ${where} right now — check back soon.`;
      evData = n;
      evIntro = $("#events-intro").textContent;
      renderEventList();
      $("#events-updated").textContent = stampFor(saved, n);
      $("#event-sources").replaceChildren(...(n.sources || []).map((f) => el("li", { class: f.ok ? "" : "bad" },
        ext(f.url, f.name), f.ok ? `: ${f.count} listings` : `: unavailable (${f.error})`)));
      // prices/venues are still being looked up in the background: check back shortly
      if (saved) return;
      if (n.pending && evRetries < 4) { evRetries++; evRetry = setTimeout(() => load("events"), 35000); }
      else evRetries = 0;
    },
  });
  function loadEvents() { loadFood(); return load("events"); }

  // ---------- sports: NFL · NBA (Spurs first) · MLB · San Antonio Missions
  // Photos: freely licensed Wikimedia Commons images (credited) + the thumbnails ESPN publishes
  // with its own stories. No team logos, no press photos.
  const SP_PHOTOS = {
    spursArena: { src: "/static/sports/spurs-arena.webp", w: 800, h: 532, alt: "A packed arena seen from high in the upper deck during a Spurs playoff game, the court lit up in the middle.",
      cap: "Spurs vs. Mavericks, 2014 NBA Playoffs — the arena now called Frost Bank Center", author: "Katie Haugland", license: "CC BY 2.0",
      license_url: "https://creativecommons.org/licenses/by/2.0", source_url: "https://commons.wikimedia.org/wiki/File:2014_NBA_Playoffs_Dallas_Mavericks_vs._San_Antonio_Spurs.jpg" },
    spursBlue: { src: "/static/sports/spurs-bluehour.webp", w: 800, h: 641, alt: "Fans silhouetted outside the arena at dusk, its lit sign glowing against a deep blue sky.",
      cap: "Blue hour before a Spurs game, 2012 (then the AT&T Center, now Frost Bank Center)", author: "Mark Bonica", license: "CC BY 2.0",
      license_url: "https://creativecommons.org/licenses/by/2.0", source_url: "https://commons.wikimedia.org/wiki/File:Blue_hour_at_the_AT%26T_center_(6734460031).jpg" },
    wolff: { src: "/static/sports/missions-wolff.webp", w: 800, h: 600, alt: "Evening at Nelson W. Wolff Municipal Stadium: fans along the first-base line, the field glowing under the lights.",
      cap: "Nelson W. Wolff Municipal Stadium, home of the Missions, at dusk (2006)", author: "b r e n t (Flickr)", license: "CC BY 2.0",
      license_url: "https://creativecommons.org/licenses/by/2.0", source_url: "https://commons.wikimedia.org/wiki/File:Wolff_Stadium_2006.jpg" },
    missionsOF: { src: "/static/sports/missions-game.webp", w: 800, h: 533, alt: "Two San Antonio Missions outfielders in gray road uniforms converge on a fly ball.",
      cap: "Missions outfielders chase a popup, 2019 (road game at Werner Park, Nebraska)", author: "Minda Haas Kuhlmann", license: "CC BY 2.0",
      license_url: "https://creativecommons.org/licenses/by/2.0", source_url: "https://commons.wikimedia.org/wiki/File:San_Antonio_Missions_(48116648172).jpg" },
    missions26: { src: "/static/sports/missions-2026.webp", w: 800, h: 533, alt: "A man in a red shirt pedals a tricycle past the visitors' dugout while players in red uniforms laugh.",
      cap: "Between-innings tricycle ride at a Missions game, Wolff Stadium, Aug. 2026", author: "Airman Shayla Pham, U.S. Air National Guard", license: "Public domain",
      license_url: null, source_url: "https://commons.wikimedia.org/wiki/File:149th_Fighter_Wing_at_San_Antonio_Missions_Game_(260808-Z-XB550-1212).jpg" },
  };
  function spPhoto(ph) {
    const img = el("img", { src: ph.src, alt: ph.alt, width: ph.w, height: ph.h, loading: "lazy", decoding: "async", draggable: "false" });
    const fig = el("figure", { class: "sp-photo" }, img,
      el("figcaption", {}, el("span", { class: "sp-cap", text: ph.cap }), el("span", { class: "art-credit" }, "Photo: ", el("b", { text: ph.author }), " · ",
        ph.license_url ? ext(ph.license_url, ph.license) : ph.license, " · ", ext(ph.source_url, "Wikimedia Commons ↗"))));
    img.onerror = () => fig.remove();
    return fig;
  }
  const SP_KEY = "chisme-sports-league";
  const LEAGUES = ["nba", "nfl", "mlb", "missions"];
  let spData = null, spLg = LEAGUES.includes(localStorage.getItem(SP_KEY)) ? localStorage.getItem(SP_KEY) : "nba";
  const ord = (n) => n + (["th", "st", "nd", "rd"][(n % 100 > 10 && n % 100 < 14) ? 0 : n % 10] || "th");
  function gameWhen(d) {
    const k = dayKey(d), today = dayKey(new Date()), tmr = dayKey(new Date(Date.now() + 864e5)), yst = dayKey(new Date(Date.now() - 864e5));
    const day = k === today ? "Today" : k === tmr ? "Tomorrow" : k === yst ? "Yesterday" : fmt(d, { weekday: "short", month: "short", day: "numeric" });
    return { day, time: fmt(d, { hour: "numeric", minute: "2-digit" }) + " " + tzAbbr(d) };
  }
  function gameCard(g, opts = {}) {
    const d = new Date(g.date), w = gameWhen(d);
    const scoreOf = (t) => (t && t.score != null ? t.score : "");
    const won = (t, o) => g.state === "post" && t && o && (t.winner === true || (t.winner == null && +t.score > +o.score));
    const row = (t, o, home) => el("div", { class: "gt" + (won(t, o) ? " win" : "") },
      el("span", { class: "gn" }, el("span", { class: "ha", text: home ? "vs" : "@", "aria-hidden": "true" }), t ? t.short || t.name : "TBD"),
      t && t.record ? el("span", { class: "gr", text: t.record }) : null,
      el("span", { class: "gs", text: g.state === "pre" ? "" : scoreOf(t) }));
    const status = g.state === "in" ? el("span", { class: "live" }, el("span", { class: "live-dot", "aria-hidden": "true" }), "LIVE · " + (g.detail || ""))
      : g.state === "post" ? el("span", { text: `${g.detail || "Final"} · ${w.day}` })
      : el("span", { text: `${w.day} · ${w.time}` });
    const a = g.away || {}, h = g.home || {};
    const label = `${a.name || "TBD"} at ${h.name || "TBD"}. ` + (g.state === "pre" ? `${w.day} ${w.time}` : `${a.short} ${a.score ?? ""}, ${h.short} ${h.score ?? ""}. ${g.state === "in" ? "Live, " + (g.detail || "") : g.detail || "Final"}`);
    const card = el("article", { class: "game" + (g.texas ? " tx" : "") + (g.state === "in" ? " is-live" : "") + (opts.wide ? " wide" : ""), "aria-label": label },
      g.note ? el("p", { class: "gnote", text: g.note }) : null,
      row(g.away, g.home, false), row(g.home, g.away, true),
      el("p", { class: "gstat" }, status, g.tv && g.state !== "post" ? el("span", { class: "tv", text: " · " + g.tv }) : null),
      g.link ? ext(g.link, g.league === "milb" || g.league === "mlb" ? "Gameday" : "Gamecast", "glink",
        { title: `${a.name || "TBD"} at ${h.name || "TBD"}`, source: g.league === "milb" || g.league === "mlb" ? "MLB Gameday" : "ESPN Gamecast", summary: label, kind: "game" }) : null);
    return card;
  }
  const scoreStrip = (games, label) => games.length
    ? el("div", { class: "scores", role: "group", "aria-label": label + ", scroll sideways" }, ...games.map((g) => gameCard(g)))
    : null;
  const vidLink = (href, text, meta) => ytId(href)   // Sports YouTube clips play in the in-app player (no Save: not a food spot)
    ? openLink(href, text, null, (a) => openPlayer({ url: href, video: true, ...meta }, a, { noSave: true })) : ext(href, text, null, meta);
  function spNews(it) {
    const d = it.published ? new Date(it.published * 1000) : null;
    const kids = [el("div", { class: "sn-body" },
      el("h4", {}, vidLink(it.link, it.title, storyMeta(it))),
      el("p", { class: "sn-meta" }, el("b", { text: it.source }), d ? " · " + ago(d) : "", it.video ? el("span", { class: "vtag", text: " ▶ Video" }) : null),
      it.summary ? el("p", { class: "sn-sum", text: it.summary }) : null)];
    if (it.image && it.source === "ESPN" && navigator.onLine) {   // only ESPN's own story thumbnails
      const a = el("a", { class: "sn-thumb", href: it.link, tabindex: "-1", "aria-hidden": "true" },
        el("img", { src: it.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" }));
      linkMeta.set(a, storyMeta(it));
      a.firstChild.onerror = () => a.remove();
      kids.push(a);
    }
    return el("article", { class: "sn" }, ...kids);
  }
  const newsList = (items, empty) => el("div", { class: "sn-list" }, ...(items.length ? items.map(spNews) : [el("p", { class: "loading", text: empty })]));
  const h3 = (t, id) => el("h3", { class: "sp-h", id, text: t });
  const linkList = (items, cls, max) => el("ul", { class: "sp-links " + (cls || "") }, ...items.slice(0, max || 8).map((i) => {
    const d = i.published ? new Date(i.published * 1000) : null;
    return el("li", {}, vidLink(i.link, (i.video ? "▶ " : "") + i.title, storyMeta(i)), el("span", { class: "sn-meta", text: (d ? " · " + ago(d) : "") }));
  }));
  function standingsTable(st, caption, cols) {
    const t = el("table", { class: "standings" }, el("caption", { text: caption }),
      el("thead", {}, el("tr", {}, ...cols.map((c) => el("th", { scope: "col", text: c[0] })))),
      el("tbody", {}, ...st.map((r) => el("tr", { class: r.spurs ? "us" : "" }, ...cols.map((c, k) => el(k === 1 ? "th" : "td", k === 1 ? { scope: "row" } : {}, String(c[1](r) ?? "")))))));
    return el("div", { class: "table-wrap" }, t);
  }
  // Your NBA team: the Spurs in San Antonio, the nearest team anywhere else (the server picks it).
  function renderSpurs(sp, nba) {
    const out = [];
    const T = sp.team || { abbr: "SA", name: "San Antonio Spurs", short: "Spurs", conf: "West" }, isSA = T.abbr === "SA", nm = T.short;
    const st = sp.standings, us = st && st.rows.find((r) => r.spurs);
    const lines = [];
    if (sp.live.length) lines.push(`Game on — the ${nm} are playing right now.`);
    if (st && st.final && us) lines.push(`${st.season}: ${us.w}-${us.l}, ${ord(us.seed)} in the ${T.conf || "West"}.`);
    else if (sp.record && sp.record !== "0-0") lines.push(`${sp.season}: ${sp.record}${sp.standing ? ", " + sp.standing : ""}.`);
    const last = sp.last[0];
    if (last && /Finals/.test(last.note || "") && last.home && last.away) {
      const spurs = [last.home, last.away].find((t) => t.abbr === T.abbr), opp = [last.home, last.away].find((t) => t.abbr !== T.abbr);
      if (spurs && opp) lines.push(spurs.winner ? `Won the ${last.note.replace(/ - Game \d+/, "")} against the ${opp.short}.` : `The season ended in the ${last.note.replace(/ - Game \d+/, "")}, falling to the ${opp.short}.`);
    }
    const next = sp.upcoming[0];
    if (next) { const w = gameWhen(new Date(next.date)); const home = next.home && next.home.abbr === T.abbr; const opp = home ? next.away : next.home;
      lines.push(`Next: ${next.note ? next.note + " " : ""}${home ? "vs." : "at"} ${opp ? opp.short : "TBD"}, ${w.day} at ${w.time}.`); }
    out.push(el("div", { class: "spurs-hero" + (isSA ? "" : " no-photo") }, isSA ? spPhoto(SP_PHOTOS.spursArena) : null,
      el("div", { class: "spurs-card" }, el("p", { class: "kicker", text: T.name }), el("h3", { text: sp.live.length ? "Live now" : `The latest on the ${nm}` }),
        ...lines.map((l) => el("p", { class: "spurs-line", text: l })))));
    if (sp.live.length) { out.push(h3("Live")); out.push(...sp.live.map((g) => gameCard(g, { wide: true }))); }
    if (sp.last.length) {
      out.push(h3(sp.last_season ? `Latest scores (${sp.last_season} season)` : "Latest scores"));
      out.push(scoreStrip(sp.last, `Latest ${nm} scores`));
    }
    if (sp.upcoming.length) {
      out.push(h3(`Schedule · ${sp.season || "this season"}`));
      out.push(el("ol", { class: "sched" }, ...sp.upcoming.map((g) => {
        const w = gameWhen(new Date(g.date)), home = g.home && g.home.abbr === T.abbr, opp = home ? g.away : g.home;
        return el("li", {}, el("span", { class: "sd", text: w.day }), el("span", { class: "so" }, el("b", { text: (home ? "vs " : "@ ") + (opp ? opp.short : "TBD") }),
          g.note ? el("span", { class: "tag", text: g.note }) : null), el("span", { class: "st", text: w.time + (g.tv ? " · " + g.tv : "") }));
      })));
    }
    if (st) {
      out.push(h3(`${st.conference || T.conf + "ern Conference"} standings${st.final ? ` (${st.season} final)` : ""}`));
      const rows = st.rows.slice(0, 10);
      out.push(standingsTable(rows, `${st.conference} standings, ${st.season}`, [["#", (r) => r.seed || ""], ["Team", (r) => r.team], ["W", (r) => r.w], ["L", (r) => r.l], ["GB", (r) => r.gb]]));
    }
    out.push(h3(`${nm} news`));
    out.push(newsList(sp.news, isSA ? "No fresh Spurs stories right now — even Coyote takes a day off." : `No fresh ${nm} stories right now.`));
    if (isSA) out.push(spPhoto(SP_PHOTOS.spursBlue));
    const fans = sp.fans || {};
    const trend = el("div", { class: "trend" });
    if (sp.reddit.length) trend.append(el("p", { class: "trend-h", text: `🔥 Top on ${fans.reddit || "r/NBASpurs"} this week` }), linkList(sp.reddit, "reddit", 6));
    else if (isSA) trend.append(el("p", { class: "hint" }, "Reddit isn't answering our server right now — ", ext("https://www.reddit.com/r/NBASpurs/top/?t=week", "see the top r/NBASpurs posts", null, { title: "Top r/NBASpurs posts this week", source: "Reddit" }), "."));
    if (sp.videos.length) trend.append(el("p", { class: "trend-h", text: `▶ New from the ${nm} on YouTube` }), linkList(sp.videos.map((v) => ({ ...v, video: true })), "yt", 6));
    if (sp.blog.length) trend.append(el("p", { class: "trend-h", text: `📝 ${fans.blog || "Pounding The Rock (SB Nation)"}` }), linkList(sp.blog, "blog", 5));
    if (trend.children.length) { out.push(h3(isSA ? "Trending in Spurs Nation" : `Trending with ${nm} fans`)); out.push(trend); }
    out.push(h3("Around the NBA"));
    const strip = scoreStrip(nba.games || [], "NBA scores");
    out.push(strip || el("p", { class: "hint", text: "No NBA games on the board today." }));
    out.push(newsList((nba.news || []).slice(0, 8), "No NBA headlines right now."));
    return out;
  }
  // Your Minor League club: the Missions in San Antonio, the nearest MiLB team (within 60 km) elsewhere.
  function renderMissions(m) {
    const T = m.team || { id: 510, name: "San Antonio Missions", short: "Missions", parent: "San Diego Padres" }, isSA = T.id === 510, nm = T.short;
    const out = isSA ? [spPhoto(SP_PHOTOS.wolff)] : [];
    const us = m.standings && m.standings.rows.find((r) => r.spurs);
    const place = us ? m.standings.rows.indexOf(us) + 1 : null;
    const parent = (T.parent || "").replace(/^.* /, "");
    out.push(el("p", { class: "blurb", text: m.season_over
      ? `The ${m.standings ? m.standings.season : ""} season is in the books: ${m.record || ""}${place ? `, ${ord(place)} in the ${m.standings.division}` : ""}. ${isSA ? "Baseball returns to Wolff Stadium in April. 🌵" : "Baseball returns in April. ⚾"}`
      : isSA ? `Double-A ball, big-league dreams: the Padres' top prospects, right here in San Antonio.${m.record ? " Record: " + m.record + "." : ""}`
        : `${m.level || "Minor League"} ball close to home: the ${T.name}${parent ? `, the ${parent}' affiliate` : ""}.${m.record ? " Record: " + m.record + "." : ""}` }));
    if (m.upcoming.length) { out.push(h3("Up next")); out.push(scoreStrip(m.upcoming, `Upcoming ${nm} games`)); }
    if (m.last.length) { out.push(h3(m.season_over ? "Final games of the season" : "Latest scores")); out.push(scoreStrip(m.last, `Latest ${nm} scores`)); }
    if (m.standings) {
      out.push(h3(`${m.standings.division} standings`));
      out.push(standingsTable(m.standings.rows, `${m.standings.division}, ${m.standings.season}`, [["", (r) => ""], ["Team", (r) => r.short], ["W", (r) => r.w], ["L", (r) => r.l], ["GB", (r) => r.gb]]));
    }
    out.push(h3(`${nm} news`));
    out.push(newsList(m.news, `No ${nm} headlines lately — the bullpen's quiet.`));
    if (isSA) { out.push(spPhoto(SP_PHOTOS.missions26)); out.push(spPhoto(SP_PHOTOS.missionsOF)); }
    return out;
  }
  const teamList = (ts) => { const n = (ts || []).map((t) => t.short); return n.length > 1 ? n.slice(0, -1).join(", ") + " and " + n[n.length - 1] : n[0] || ""; };
  const isTX = (d) => !d.teams || d.teams.state === "TX";
  const INTROS = {
    nba: (d) => { const T = d.nba.spurs.team; if (T && T.abbr !== "SA") return d.nba.spurs.live.length ? `¡Ándale! The ${T.short} are on right now. 🏀`
        : pick([`Scores, schedule and the real reporting on the ${T.short}, with a side of fan chisme. 🏀`, `The latest on the ${T.name}, then the rest of the league.`]);
      return INTROS.spurs(d); },
    spurs: (d) => (d.nba.spurs.live.length ? "¡Ándale! The Spurs are on right now. 🏀" : pick(["Go Spurs Go! Scores, schedule and the real reporting, with a side of fan chisme. 🏀",
      "Spurs Nation, this one's for you: the latest on Wemby & company, then the rest of the league.", "Silver and black and read all over — your Spurs report."])),
    nfl: (d) => isTX(d) ? pick(["Football, Texas style: Cowboys and Texans first, then everybody else. 🏈", "Tailgate-ready: the scores and stories from around the NFL, Texas teams up top."])
      : `Tailgate-ready: the ${teamList(d.teams.nfl)} up top, then everybody else. 🏈`,
    mlb: (d) => { const who = isTX(d) ? "Rangers and Astros" : `the ${teamList(d.teams.mlb)}`;
      return (d.mlb.games || []).some((g) => /Wild Card|Division|Championship|World Series/.test(g.note || ""))
        ? `October baseball! 🎉 ${who[0].toUpperCase() + who.slice(1)} first, then the rest of the playoff picture.`
        : `Peanuts, Cracker Jack and box scores — ${who} first. ⚾`; },
    missions: (d) => { const T = d.missions && d.missions.team; return !T || T.id === 510 ? "San Antonio's own: the Double-A Missions of the Texas League. 🌵"
      : `The home team: the ${d.missions.level || "Minor League"} ${T.name} of the ${T.league}. ⚾`; },
  };
  function renderSports() {
    const d = spData;
    if (d && d.teams) {   // chips follow your teams: "NBA · Rockets", the local MiLB club (hidden if there isn't one)
      if (!d.missions && spLg === "missions") spLg = "nba";
      const nb = document.querySelector('#sp-chips [data-lg="nba"]'), mi = document.querySelector('#sp-chips [data-lg="missions"]');
      nb.replaceChildren(el("span", { "aria-hidden": "true", text: "🏀" }), ` NBA · ${d.teams.nba.short}`);
      mi.hidden = !d.missions;
      if (d.missions) mi.replaceChildren(el("span", { "aria-hidden": "true", text: d.missions.team.id === 510 ? "🌵" : "⚾" }), ` ${d.missions.team.short}`);
    }
    for (const b of document.querySelectorAll("#sp-chips .chip")) b.setAttribute("aria-pressed", String(b.dataset.lg === spLg));
    if (!d) return;
    $("#sports-intro").textContent = INTROS[spLg](d);
    let kids;
    if (spLg === "nba") kids = renderSpurs(d.nba.spurs, d.nba);
    else if (spLg === "nfl") {
      kids = [h3("Scores" + (d.nfl.games.length ? "" : "")), scoreStrip(d.nfl.games, "NFL scores") || el("p", { class: "hint", text: "No NFL games on the board." }),
        h3("NFL news"), newsList(d.nfl.news, "No NFL headlines right now.")];
    } else if (spLg === "mlb") {
      const m = d.mlb, day = m.date ? fmt(new Date(m.date + "T12:00:00"), { weekday: "long", month: "short", day: "numeric" }) : "";
      kids = [h3(`Scores · ${day}`), scoreStrip(m.games || [], "MLB scores") || el("p", { class: "hint", text: "No MLB games today." })];
      if ((m.next || []).length) kids.push(h3("Next up · " + fmt(new Date(m.next_date + "T12:00:00"), { weekday: "long", month: "short", day: "numeric" })), scoreStrip(m.next, "Next MLB games"));
      kids.push(h3("MLB news"), newsList(m.news || [], "No MLB headlines right now."));
    } else kids = renderMissions(d.missions);
    $("#sports-body").replaceChildren(...kids.filter(Boolean));
    $("#sports-body").dataset.lg = spLg;
    placeMid();
  }
  for (const b of document.querySelectorAll("#sp-chips .chip")) {
    b.onclick = () => { spLg = b.dataset.lg; localStorage.setItem(SP_KEY, spLg); renderSports(); };
  }
  section("sports", {
    url: () => `/api/sports?${q()}`,   // your teams follow your location
    loading: () => $("#sports-body").replaceChildren(el("p", { class: "loading", text: "Warming up in the bullpen…" })),
    fail: (e) => $("#sports-body").replaceChildren(el("p", { class: "error", text: "¡Ay! Couldn't reach the scoreboards (" + e.message + "). We'll keep trying." })),
    apply: (d, { saved }) => {
      spData = d;
      if (!saved) rendered.sports = true;
      renderSports();
      $("#sports-updated").textContent = stampFor(saved, d);
      $("#sports-sources").replaceChildren(...(d.sources || []).map((f) => el("li", { class: f.ok ? "" : "bad" },
        ext(f.home, f.name), f.ok ? (f.count != null ? `: ${f.count} items` : ": ok") : `: unavailable right now (${f.error})`)));
    },
  });
  const loadSports = () => load("sports");

  // ---------- views: News | Sports | Weather | ¿Cuál dieta? | Juegitos | Events (tap the fixed buttons, swipe sideways or ←/→ on the tabs)
  const VIEWS = ["news", "sports", "weather", "antojos", "juegos", "events"];
  // 🎲 Juegos: mounted the first time the tab opens (static/juegos.js lists the games; icebebe.js adds game 2).
  let juegos = null;
  function juegosOpen(game) {
    if (!juegos && window.ChismeJuegos) juegos = window.ChismeJuegos.mountTab($("#games-list"), $("#game-stage"), { reducedMotion });
    if (juegos && game) juegos.open(game);
    return juegos;
  }
  const juegosPause = () => { if (juegos) juegos.pause(); };
  const juegosLeave = () => { if (juegos) (juegos.leave || juegos.pause)(); };   // another tab: drop full-screen play too
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") juegosPause(); });
  const GAP = 24;
  const track = $("#track"), viewsEl = $("#views"), tabsEl = $("#tabs");
  const panes = VIEWS.map((v) => $("#view-" + v));
  let cur = 0;
  const savedY = {};
  const tabsH = () => tabsEl.offsetHeight;
  const setTabsVar = () => document.documentElement.style.setProperty("--tabs-h", tabsH() + "px");
  setTabsVar(); window.addEventListener("resize", setTabsVar);
  if ("ResizeObserver" in window) new ResizeObserver(setTabsVar).observe(tabsEl);  // A−/A+ or rotation changes its height
  const viewsTop = () => viewsEl.getBoundingClientRect().top + window.scrollY;
  const pos = (i, dx = 0) => { track.style.transform = `translateX(calc(${-i} * (100% + ${GAP}px) + ${dx}px))`; };
  function updateTabs(scrollId) {
    for (const t of document.querySelectorAll(".tab")) {
      const on = t.dataset.view === VIEWS[cur] && !t.dataset.scroll;
      t.toggleAttribute("aria-current", false);
      if (on) t.setAttribute("aria-current", "page");
      t.classList.toggle("sub-current", !!t.dataset.scroll && t.dataset.scroll === scrollId);
    }
  }
  // Where the page should be scrolled once view i is showing (keeps the header if it's visible).
  function targetY(i, beforeDocH, activeH) {
    const top = Math.max(0, viewsTop() - tabsH());
    let t = window.scrollY <= top ? window.scrollY : (savedY[VIEWS[i]] ?? top);
    const afterDocH = beforeDocH - activeH + panes[i].offsetHeight;
    return Math.max(0, Math.min(t, afterDocH - window.innerHeight));
  }
  let peekI = null, peekY = 0;
  function peek(i) {
    if (peekI === i) return;
    unpeek();
    if (i < 0 || i >= VIEWS.length) return;
    const docH = document.documentElement.scrollHeight, activeH = panes[cur].offsetHeight;
    panes[i].classList.add("peek");
    peekY = targetY(i, docH, activeH);
    panes[i].style.transform = `translateY(${window.scrollY - peekY}px)`;
    peekI = i;
  }
  function unpeek() {
    if (peekI != null && peekI !== cur) { panes[peekI].classList.remove("peek"); panes[peekI].style.transform = ""; }
    peekI = null;
  }
  function finish(i, scrollId) {
    savedY[VIEWS[cur]] = window.scrollY;
    const y = peekI === i ? peekY : window.scrollY;
    panes.forEach((p, k) => { p.classList.toggle("active", k === i); p.classList.remove("peek"); p.style.transform = ""; p.inert = k !== i; });
    peekI = null;
    cur = i;
    track.classList.remove("animating");
    pos(i);
    window.scrollTo({ top: y, behavior: "instant" });
    updateTabs(scrollId);
    if (VIEWS[i] === "weather" && map) map.invalidateSize();
    updateNewsPill();
    if (VIEWS[i] === "events" && rendered.events !== q()) loadEvents();
    if (VIEWS[i] === "juegos") juegosOpen(juegosWant); else juegosLeave();
    juegosWant = null;
    if (VIEWS[i] === "sports" && !rendered.sports) loadSports();
    if (VIEWS[i] === "antojos" && (!foodData || secs.food.shownUrl !== secs.food.url())) loadFood();   // new place → new city's food
    if (scrollId) { const t = document.getElementById(scrollId); if (t) window.scrollTo({ top: t.getBoundingClientRect().top + window.scrollY - tabsH() - 8, behavior: "instant" }); }
    localStorage.setItem("chisme-swiped", "1");
  }
  let animT = null, juegosWant = null;
  function goView(name, opts = {}) {
    const i = typeof name === "number" ? name : VIEWS.indexOf(name);
    if (i < 0) return;
    if (i === cur) { unpeek(); track.classList.add("animating"); pos(i); if (opts.scrollTo) finish(i, opts.scrollTo); else updateTabs(); return; }
    if (opts.instant || reducedMotion()) { peek(i); finish(i, opts.scrollTo); return; }
    peek(i);
    track.classList.add("animating");
    pos(i);
    clearTimeout(animT);
    const done = () => { clearTimeout(animT); track.removeEventListener("transitionend", onEnd); finish(i, opts.scrollTo); };
    const onEnd = (ev) => { if (ev.target === track) done(); };
    track.addEventListener("transitionend", onEnd);
    animT = setTimeout(done, 450);
  }
  for (const t of document.querySelectorAll(".tab")) t.onclick = () => goView(t.dataset.view, { scrollTo: t.dataset.scroll });

  // Swipe: only horizontal touch drags that start outside the radar map, the hourly strip and
  // form controls. touch-action: pan-y (CSS) leaves vertical scrolling to the browser.
  const NO_SWIPE = ".leaflet-container, .hourly, .forecast, .chips, .food-strip, .scores, .table-wrap, input, select, textarea, .no-swipe";
  let drag = null, justDragged = false;
  viewsEl.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" || !e.isPrimary || e.target.closest(NO_SWIPE)) { drag = null; return; }
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), lock: null, dx: 0 };
  });
  window.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.lock) {
      if (Math.abs(dx) < 12 && Math.abs(dy) < 12) return;
      if (Math.abs(dx) > Math.abs(dy) * 1.3) { drag.lock = "x"; track.classList.remove("animating"); }
      else { drag = null; return; }
    }
    const nb = cur + (dx < 0 ? 1 : -1);
    const edge = nb < 0 || nb >= VIEWS.length;
    if (!edge) peek(nb); else unpeek();
    drag.dx = edge ? dx / 3 : dx;
    drag.lastX = e.clientX; drag.lastT = performance.now();
    pos(cur, drag.dx);
  }, { passive: true });
  function endDrag(e, cancelled) {
    if (!drag || e.pointerId !== drag.id) return;
    const d = drag; drag = null;
    if (d.lock !== "x") return;
    justDragged = true; setTimeout(() => { justDragged = false; }, 350);
    const w = viewsEl.clientWidth, v = d.dx / Math.max(1, performance.now() - d.t);
    const nb = cur + (d.dx < 0 ? 1 : -1);
    if (!cancelled && nb >= 0 && nb < VIEWS.length && (Math.abs(d.dx) > w * 0.22 || Math.abs(v) > 0.45)) goView(nb);
    else { track.classList.add("animating"); pos(cur); setTimeout(() => { if (!drag) unpeek(); }, 340); }
  }
  window.addEventListener("pointerup", (e) => endDrag(e, false));
  window.addEventListener("pointercancel", (e) => endDrag(e, !drag || drag.lock !== "x"));
  window.addEventListener("click", (e) => { if (justDragged) { e.preventDefault(); e.stopPropagation(); } }, true);
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea, select, .leaflet-container") || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === "ArrowRight" && e.target.closest(".tabs")) goView(Math.min(VIEWS.length - 1, cur + 1));
    if (e.key === "ArrowLeft" && e.target.closest(".tabs")) goView(Math.max(0, cur - 1));
  });
  if (localStorage.getItem("chisme-swiped")) $("#swipe-hint").hidden = true;
  // Deep links (manifest shortcuts): #sports, #weather, #radar-sec, #events. Otherwise the default tab (News unless changed in Settings).
  const HASH_VIEW = { "#weather": ["weather"], "#forecast-sec": ["weather", "forecast-sec"], "#radar-sec": ["weather", "radar-sec"], "#radar": ["weather", "radar-sec"],
    "#alerts": ["weather", "alerts"], "#events": ["events"], "#antojos": ["antojos"], "#cual-dieta": ["antojos"], "#dieta": ["antojos"], "#food": ["antojos"], "#near": ["news", "near"], "#city": ["news", "city"],
    "#sports": ["sports"], "#spurs": ["sports"], "#nfl": ["sports"], "#mlb": ["sports"], "#missions": ["sports"], "#news": ["news"],
    "#juegos": ["juegos"], "#juegitos": ["juegos"], "#games": ["juegos"], "#loteria": ["juegos", null, "loteria"], "#ice": ["juegos", null, "icebebe"], "#icebebe": ["juegos", null, "icebebe"] };
  pos(0); updateTabs();

  // ---------- settings sheet (tap the Chisme icon in the header)
  const THEME_KEY = "chisme-theme", TAB_KEY = "chisme-default-tab";
  const themePref = () => localStorage.getItem(THEME_KEY) || "system";
  const darkMQ = matchMedia("(prefers-color-scheme: dark)");
  function defaultTab() { const t = localStorage.getItem(TAB_KEY); return VIEWS.includes(t) ? t : "news"; }
  function applyTheme() {
    const pref = themePref();
    const dark = pref === "dark" || (pref === "system" && darkMQ.matches);
    if (document.documentElement.dataset.theme !== (dark ? "dark" : "light")) {
      document.documentElement.dataset.theme = dark ? "dark" : "light";
      setBasemap();
    }
  }
  if (darkMQ.addEventListener) darkMQ.addEventListener("change", () => { if (themePref() === "system") applyTheme(); });
  const dlg = $("#settings");
  function syncSettings() {
    for (const r of dlg.querySelectorAll('input[name="theme"]')) r.checked = r.value === themePref();
    for (const r of dlg.querySelectorAll('input[name="deftab"]')) r.checked = r.value === defaultTab();
    $("#set-motion").checked = localStorage.getItem(RM_KEY) === "1";
    $("#set-motion-note").textContent = matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "Your device already asks for reduced motion, so Chisme keeps things still."
      : "Turns off swipe animations, the pulsing location dot and radar autoplay.";
    $("#set-loc-status").textContent = ""; $("#set-loc-results").replaceChildren();
    showFs(); renderLocLabel(); syncUI();
  }
  $("#settings-btn").onclick = () => { syncSettings(); dlg.showModal(); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });   // tap outside the sheet
  for (const r of dlg.querySelectorAll('input[name="theme"]')) r.onchange = () => { localStorage.setItem(THEME_KEY, r.value); applyTheme(); };
  for (const r of dlg.querySelectorAll('input[name="deftab"]')) r.onchange = () => localStorage.setItem(TAB_KEY, r.value);
  $("#set-motion").onchange = (e) => {
    localStorage.setItem(RM_KEY, e.target.checked ? "1" : "0");
    document.documentElement.classList.toggle("reduce-motion", e.target.checked);
    if (reducedMotion()) setPlaying(false);
  };
  $("#set-gps").onclick = () => requestGPS(true);
  $("#set-refresh").onclick = () => { refreshNow(); $("#set-refresh-note").textContent = "Updating…"; };
  $("#set-fy-reset").onclick = () => {
    newsForget();   // also forgets which stories you've seen/opened (News order)
    if (!FY) return;
    fyProfile = FY.reset(); renderForYouCard();
    $("#set-fy-note").textContent = "Done: your Bigger the Pansa, Better the Chansa feed forgot everything and starts fresh.";
  };
  $("#set-version").textContent = "· build " + window.CHISME_APP_BUILD;

  // ---------- alerts: Web Push ("New chisme, grab the tea! ☕" + NWS warnings). Opt-in only, from a tap
  // (iOS asks for permission only from a tap, and only in the Home Screen app, iOS 16.4+). See push.py.
  const PUSH_KEY = "chisme-push", PUSH_ASKED = "chisme-push-asked", VISITS = "chisme-visits";
  const pushPrefs = () => { try { return { on: false, news: true, wx: true, ...JSON.parse(lsGet(PUSH_KEY) || "{}") }; } catch { return { on: false, news: true, wx: true }; } };
  const savePushPrefs = (p) => lsSet(PUSH_KEY, JSON.stringify(p));
  const isStandalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const pushCapable = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  let pushCfg = null, pushBusy = false;
  const pushCfgReady = fetch("/api/push/config", { cache: "no-store" }).then((r) => r.ok ? r.json() : null).then((c) => { pushCfg = c; return c; }).catch(() => null);
  const u8key = (b64) => { const p = "=".repeat((4 - b64.length % 4) % 4), b = atob((b64 + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(b, (c) => c.charCodeAt(0)); };
  async function pushSub() { if (!pushCapable()) return null; try { const reg = await navigator.serviceWorker.ready; return await reg.pushManager.getSubscription(); } catch { return null; } }
  async function pushPost(path, body) {
    const r = await fetch("/api/push/" + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.ok === false) throw new Error(j.error || "the server said " + r.status);
    return j;
  }
  const pushBody = (sub) => { const p = pushPrefs(); return { subscription: sub.toJSON(), lat: loc.lat, lon: loc.lon, tz: DEVICE_TZ, news: p.news, weather: p.wx }; };
  let pushLocKey = null;
  async function pushResync() {   // every open and every move: the server's copy follows you (and heals if it was lost)
    const p = pushPrefs();
    if (!p.on || !pushCapable() || Notification.permission !== "granted") return;
    const sub = await pushSub();
    if (!sub) { savePushPrefs({ ...p, on: false }); renderAlertsUI(); return; }
    const key = q() + p.news + p.wx;
    if (key === pushLocKey) return;
    try { await pushPost("subscribe", pushBody(sub)); pushLocKey = key; } catch (e) { console.warn("alerts resync", e); }
  }
  const pushNote = (t) => { $("#set-push-note").textContent = t; };
  // Called straight from a tap: the permission prompt comes first, before any network wait.
  async function turnOnAlerts(from) {
    if (pushBusy) return;
    if (!pushCapable() || !pushCfg || !pushCfg.enabled) { renderAlertsUI(); return; }
    pushBusy = true;
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { pushNote(perm === "denied" ? "Alerts are blocked for Chisme. You can allow notifications for Chisme in your phone's or browser's settings." : "No problem: alerts stay off."); return; }
      const reg = await navigator.serviceWorker.ready;
      const sub = (await reg.pushManager.getSubscription()) || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: u8key(pushCfg.publicKey) });
      savePushPrefs({ ...pushPrefs(), on: true });
      await pushPost("subscribe", pushBody(sub)); pushLocKey = q() + pushPrefs().news + pushPrefs().wx;
      pushNote(`Done: alerts are on for ${placeName()}. 🔔`);
      if (from === "ask") { const a = $("#push-ask"); a.replaceChildren(el("p", { class: "push-ask-t", role: "status", text: "🔔 Alerts are on. Change them anytime in Settings." })); setTimeout(() => { a.hidden = true; }, 6000); }
    } catch (e) {
      savePushPrefs({ ...pushPrefs(), on: false });
      pushNote("Couldn't turn on alerts (" + e.message + "). Try again in a bit.");
    } finally { pushBusy = false; renderAlertsUI(); }
  }
  async function turnOffAlerts() {
    pushBusy = true;
    try {
      const sub = await pushSub();
      if (sub) { await pushPost("unsubscribe", { endpoint: sub.endpoint }).catch(() => {}); await sub.unsubscribe().catch(() => {}); }
      savePushPrefs({ ...pushPrefs(), on: false }); pushLocKey = null;
      pushNote("Alerts are off, and your area was removed from the server.");
    } finally { pushBusy = false; renderAlertsUI(); }
  }
  function renderAlertsUI() {
    const p = pushPrefs(), btn = $("#set-push"), st = $("#set-push-status"), test = $("#set-push-test");
    const on = p.on && pushCapable() && Notification.permission === "granted";
    $("#set-push-news").checked = p.news; $("#set-push-wx").checked = p.wx;
    $("#set-push-news").disabled = $("#set-push-wx").disabled = !on;
    test.hidden = !on;
    btn.disabled = false; btn.classList.toggle("primary", !on);
    btn.replaceChildren(on ? "Turn off alerts" : "Turn on alerts 🔔");
    if (!pushCapable()) {
      btn.disabled = true;
      st.textContent = isIOS && !isStandalone()
        ? "On iPhone and iPad, alerts work in the Home Screen app (iOS 16.4 or newer): tap Share → Add to Home Screen, open Chisme from your Home Screen, then turn alerts on here."
        : "This browser can't show push alerts. Try Chrome, Edge, Firefox or Safari on a computer or Android phone, or the Home Screen app on iPhone.";
    } else if (pushCfg && !pushCfg.enabled) {
      btn.disabled = true; st.textContent = "Alerts aren't switched on for this server yet.";
    } else if (Notification.permission === "denied") {
      btn.disabled = true; st.textContent = "Notifications are blocked for Chisme. Allow them for Chisme in your phone's or browser's settings, then come back here.";
    } else st.textContent = on ? `Alerts are on for ${placeName()}.` : "Get a heads-up when there's new local chisme or an NWS warning near you. Nothing is sent until you turn it on.";
  }
  $("#set-push").onclick = () => { if (pushPrefs().on && Notification.permission === "granted") turnOffAlerts(); else turnOnAlerts("settings"); };
  for (const [id, k] of [["#set-push-news", "news"], ["#set-push-wx", "wx"]]) {
    $(id).onchange = (e) => { savePushPrefs({ ...pushPrefs(), [k]: e.target.checked }); pushResync().then(() => pushNote("Saved.")); };
  }
  $("#set-push-test").onclick = async () => {
    const sub = await pushSub();
    if (!sub) { renderAlertsUI(); return; }
    pushNote("Sending a test…");
    try { await pushPost("test", { endpoint: sub.endpoint }); pushNote("Test sent: it should pop up in a few seconds."); }
    catch (e) { pushNote("Couldn't send a test (" + e.message + ")."); }
  };
  // One-time soft prompt: on your second visit (never the first), only where alerts can work, never a popup.
  const visits = (+lsGet(VISITS) || 0) + 1; lsSet(VISITS, String(visits));
  pushCfgReady.then((c) => {
    renderAlertsUI();
    pushResync();
    const ask = $("#push-ask");
    if (!ask || visits < 2 || lsGet(PUSH_ASKED) || !c || !c.enabled || !pushCapable() || Notification.permission === "denied" || pushPrefs().on) return;
    lsSet(PUSH_ASKED, String(Date.now()));   // shown once, whatever you pick
    ask.hidden = false;
    $("#push-ask-yes").onclick = () => turnOnAlerts("ask");
    $("#push-ask-no").onclick = () => { ask.hidden = true; };
  });
  // Tapping a notification: the story opens in Chisme's reader (or the weather alerts), never another app.
  function openFromAlert(href) {
    let u; try { u = new URL(href, location.origin); } catch { return; }
    if (u.origin !== location.origin) return;
    const link = u.searchParams.get("story");
    if (link && /^https?:\/\//.test(link)) {
      goView("news", { instant: true });
      const all = lastNewsData ? [...(lastNewsData.near || []), ...(lastNewsData.more || []), ...(lastNewsData.metro_other || lastNewsData.san_antonio || [])] : [];
      const hit = all.find((i) => i.link === link);
      openReader(hit ? { url: hit.link, ...storyMeta(hit) }
        : { url: link, title: u.searchParams.get("t") || "New chisme", source: u.searchParams.get("s") || "", published: +u.searchParams.get("p") || null }, null);
    } else if (HASH_VIEW[u.hash]) {
      const hv = HASH_VIEW[u.hash]; juegosWant = hv[2] || null; goView(hv[0], { scrollTo: hv[1] || undefined });
      if (hv[2] && VIEWS[cur] === "juegos") juegosOpen(hv[2]);
    }
  }
  if (navigator.serviceWorker) navigator.serviceWorker.addEventListener("message", (e) => { if (e.data && typeof e.data.chismeOpen === "string") openFromAlert(e.data.chismeOpen); });
  if (new URLSearchParams(location.search).has("story")) {
    const href = location.href;
    history.replaceState(history.state, "", location.pathname + location.hash);   // a reload doesn't reopen it
    setTimeout(() => openFromAlert(href), 60);
  }

  // ---------- boot + auto refresh
  let lastWx = 0, lastNews = 0, lastEv = 0, evBoot = null;
  let spBoot = null;
  function refreshAll() {
    loadNews(); loadWeather(); loadRadar(); lastWx = lastNews = Date.now();
    // events + sports load right after (immediately if their view is open), so they're saved for offline too
    clearTimeout(evBoot); clearTimeout(spBoot);
    if (VIEWS[cur] === "events") loadEvents(); else evBoot = setTimeout(loadEvents, 1200);
    if (VIEWS[cur] === "sports") loadSports(); else spBoot = setTimeout(loadSports, 1800);
    if (VIEWS[cur] === "antojos") loadFood();
    lastEv = Date.now();
  }
  renderLocLabel();
  initMap();
  const LG_HASH = { "#spurs": "nba", "#nfl": "nfl", "#mlb": "mlb", "#missions": "missions" };
  if (LG_HASH[location.hash]) { spLg = LG_HASH[location.hash]; localStorage.setItem(SP_KEY, spLg); }
  const hv = HASH_VIEW[location.hash] || [defaultTab()];
  juegosWant = hv[2] || null;
  if (hv[0] !== "news") goView(hv[0], { instant: true });
  if (window.ChismeDonate) midLaunch = window.ChismeDonate.launch();
  if (midLaunch.line) { midTab = VIEWS[cur]; placeMid(); }   // a 5th open: the launch tab gets the one mid-list donate card
  window.addEventListener("hashchange", () => {   // #juegos, #loteria, #ice … typed or tapped while Chisme is open
    const h = HASH_VIEW[location.hash]; if (!h) return;
    juegosWant = h[2] || null; goView(h[0], { scrollTo: h[1] || undefined });
    if (h[2] && VIEWS[cur] === "juegos") juegosOpen(h[2]);
  });
  refreshAll();
  if (hv[1]) setTimeout(() => goView(hv[0], { scrollTo: hv[1] }), 50);
  lookupPlace();
  initGeo();
  setInterval(() => { loadWeather(); loadRadar(); lastWx = Date.now(); }, WEATHER_MS);
  setInterval(() => { renderGreeting(); if (document.visibilityState === "visible") { loadNews(); lastNews = Date.now(); } }, NEWS_MS);
  const newsOnReturn = () => { if (document.visibilityState === "visible" && Date.now() - lastNews > NEWS_FOCUS_MS) { loadNews(); lastNews = Date.now(); } };
  addEventListener("focus", newsOnReturn);
  setInterval(() => { loadEvents(); lastEv = Date.now(); }, EVENTS_MS);
  setInterval(() => { if (VIEWS[cur] === "sports" || document.visibilityState === "visible") loadSports(); }, SPORTS_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    renderGreeting();
    if (Date.now() - lastWx > WEATHER_MS) { loadWeather(); loadRadar(); lastWx = Date.now(); }
    newsOnReturn();
    if (Date.now() - lastEv > EVENTS_MS) { loadEvents(); lastEv = Date.now(); }
    retryFailed();   // back in the app: don't wait out the backoff
  });
  // Manual refresh (pull down at the top, "Retry now", or Settings → Refresh now)
  function refreshNow() {
    newsManual = true;   // you asked: show the new stories right away
    newsVisit();         // ...and a fresh order if nothing's new
    for (const s of Object.values(secs)) s.tries = 0;
    Sync.failed.clear();
    refreshAll();
  }
  $("#sync-retry").onclick = refreshNow;

  // ---------- pull to refresh (home-screen apps have no browser reload button)
  const ptr = $("#ptr"), PTR_GO = 70;
  let pull = null;
  document.addEventListener("touchstart", (e) => {
    if (e.touches.length !== 1 || window.scrollY > 0 || e.target.closest(NO_SWIPE + ", dialog")) { pull = null; return; }
    pull = { x: e.touches[0].clientX, y: e.touches[0].clientY, dy: 0, lock: null };
  }, { passive: true });
  document.addEventListener("touchmove", (e) => {
    if (!pull) return;
    const dx = e.touches[0].clientX - pull.x, dy = e.touches[0].clientY - pull.y;
    if (!pull.lock) {
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
      pull.lock = dy > 0 && dy > Math.abs(dx) * 1.3 && window.scrollY <= 0 ? "y" : "no";
    }
    if (pull.lock !== "y") return;
    pull.dy = Math.max(0, dy);
    const d = Math.min(110, pull.dy * 0.55);
    ptr.hidden = false;
    ptr.style.transform = `translate(-50%, ${d}px) rotate(${d * 3}deg)`;
    ptr.classList.toggle("go", d >= PTR_GO);
  }, { passive: true });
  const endPull = () => {
    if (!pull) return;
    const go = pull.lock === "y" && pull.dy * 0.55 >= PTR_GO;
    pull = null;
    ptr.classList.remove("go");
    if (go) { ptr.classList.add("spin"); refreshNow(); setTimeout(() => { ptr.classList.remove("spin"); ptr.hidden = true; ptr.style.transform = ""; }, 900); }
    else { ptr.hidden = true; ptr.style.transform = ""; }
  };
  document.addEventListener("touchend", endPull);
  document.addEventListener("touchcancel", endPull);

  // ---------- PWA: service worker, install button (Android/desktop Chrome), iOS hint
  // The app shell is served from the service worker's cache (instant open, even on a sleeping
  // server). A new version installs in the background; we offer a reload, and reload by
  // ourselves the next time the app is reopened.
  if ("serviceWorker" in navigator) {
    const hadController = !!navigator.serviceWorker.controller;
    let reg = null, lastCheck = 0, pendingReload = false;
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" })
      .then((r) => { reg = r; lastCheck = Date.now(); }).catch((e) => console.warn("SW failed", e)));
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") return;
      if (pendingReload) { location.reload(); return; }
      if (reg && Date.now() - lastCheck > 60e3) { lastCheck = Date.now(); reg.update().catch(() => {}); }
    });
    // A new version took over. Ask it which build it is: if it isn't this page's build, reload once
    // right away so HTML, JS and CSS all come from the new version (or, if you're in the middle of
    // something, offer it with the toast and reload the next time the app is reopened).
    navigator.serviceWorker.addEventListener("message", (e) => {
      const v = e.data && e.data.chismeVersion;
      if (!v || v === "chisme-v" + window.CHISME_APP_BUILD) return;
      const busy = $("#settings").open || $("#player").open || (document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName));
      if (!busy && document.visibilityState === "visible") { location.reload(); return; }
      pendingReload = true;
      $("#update-toast").hidden = false;
    });
    const askVersion = () => { const c = navigator.serviceWorker.controller; if (c) c.postMessage("chisme-version"); };
    navigator.serviceWorker.addEventListener("controllerchange", () => { if (hadController) askVersion(); });
    if (navigator.serviceWorker.startMessages) navigator.serviceWorker.startMessages();   // WebKit queues them otherwise
    askVersion();                            // also catches a page that opened under an older worker
    $("#update-reload").onclick = () => location.reload();
  }
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let deferredPrompt = null;
  const INSTALL_KEY = "chisme-install-card-dismissed";
  const hideInstall = () => { $("#install-btn").hidden = true; $("#install-card").hidden = true; };
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    $("#install-btn").hidden = false;
    if (!localStorage.getItem(INSTALL_KEY)) $("#install-card").hidden = false;
  });
  const doInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice.catch(() => null);
    deferredPrompt = null;
    hideInstall();
  };
  $("#install-btn").onclick = doInstall;
  $("#install-card-btn").onclick = doInstall;
  $("#install-card-close").onclick = () => { $("#install-card").hidden = true; localStorage.setItem(INSTALL_KEY, "1"); };
  window.addEventListener("appinstalled", () => { hideInstall(); deferredPrompt = null; });
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
  const HINT_KEY = "chisme-ios-hint-dismissed";
  if (isIOS && !standalone && !localStorage.getItem(HINT_KEY)) $("#ios-hint").hidden = false;
  $("#ios-hint-close").onclick = () => { $("#ios-hint").hidden = true; localStorage.setItem(HINT_KEY, "1"); };

  // expose for testing
  // ---------- Tía Chismosa: the chat mascot (floating button → chat sheet).
  // Her art is /static/mascot/* (tools/make_mascot_assets.py builds it from one picture, so it can be swapped).
  // Chat history and what she learns about your interests live ONLY on this phone (localStorage); the server
  // gets the current conversation + the app's current feed items for each message and keeps nothing.
  const TIA = { name: "Tía Chismosa", avatar: (px) => `/static/mascot/avatar-${px}.webp?art=3` };
  const TIA_CHAT = "chisme-tia-chat", TIA_PROF = "chisme-tia-profile", TIA_MAX = 40;
  const tiaDlg = $("#tia"), tiaLog = $("#tia-log"), tiaForm = $("#tia-form"), tiaIn = $("#tia-in");
  let tiaBusy = false, tiaOpener = null;
  const TIA_STOP = new Set(("that this with from have what when where your their they there about after over into more than will says said just been were also " +
    "news video watch live update today tonight week year new san antonio texas".split(" ")));
  const tiaWords = (t) => ((t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").match(/[a-z0-9']{4,}/g) || []).filter((w) => !TIA_STOP.has(w));
  function tiaProfile() {
    try { const p = JSON.parse(localStorage.getItem(TIA_PROF)); if (p && p.t) return p; } catch {}
    return { t: {}, k: {}, at: Date.now() };
  }
  function tiaLearn(m, kind) {   // a tap on a story / game / event: remember its words (fading over ~2 weeks), not the link
    const p = tiaProfile(), now = Date.now(), f = Math.pow(0.5, (now - (p.at || now)) / (14 * 864e5));
    for (const k of Object.keys(p.t)) { p.t[k] *= f; if (p.t[k] < 0.05) delete p.t[k]; }
    for (const k of Object.keys(p.k)) p.k[k] *= f;
    for (const w of new Set(tiaWords(m.title))) p.t[w] = (p.t[w] || 0) + 1;
    p.k[kind] = (p.k[kind] || 0) + 1; p.at = now;
    p.t = Object.fromEntries(Object.entries(p.t).sort((a, b) => b[1] - a[1]).slice(0, 150));
    try { localStorage.setItem(TIA_PROF, JSON.stringify(p)); } catch {}
  }
  const linkKind = (a) => a.closest("#view-sports") ? "sports" : a.closest("#view-events") ? "event" : a.closest("#view-antojos, #feed") ? "food" : "news";
  // everything the app is showing right now, as plain items (the server numbers them S1..Sn and cites them)
  function tiaItems() {
    const n = lastNewsData || {}, out = { stories: [], events: [], sports: [], food: [], weather: null };
    for (const i of [...(n.near || []), ...(n.more || [])].slice(0, 15))
      out.stories.push({ kind: "news", url: i.link, title: i.title, source: i.source, published: i.published || null, when: i.published ? ago(new Date(i.published * 1000)) : "", summary: i.summary || "", image: i.image || null, near: i.tier === "near" });
    const w = lastWeather;
    if (w && w.current) {
      const c = w.current, f0 = (w.forecast || [])[0], tf = c.temp_c != null ? Math.round(c.temp_c * 9 / 5 + 32) : null;
      out.weather = { place: greetCity(), now: [c.text, tf != null ? tf + "°F" : null].filter(Boolean).join(", "),
        today: f0 ? `${f0.name}: ${f0.shortForecast}, ${f0.isDaytime ? "high" : "low"} ${f0.temperature}°${f0.temperatureUnit}` : "",
        alerts: (w.alerts || []).map((a) => a.event).filter(Boolean).slice(0, 3).join(", ") };
    }
    for (const e of ((evData && evData.events) || []).slice(0, 8))
      out.events.push({ kind: "event", url: e.url, title: e.title, source: e.source, when: whenText(e), venue: e.venue || "", summary: e.summary || "", image: e.image || null,
        price: e.price ? (e.price.free ? "free" : e.price.text || "") : "", lat: e.approx ? null : e.lat, lon: e.approx ? null : e.lon, address: e.address || null });
    const sp = spData;
    if (sp) {
      const games = [...((sp.nba && sp.nba.games) || []), ...((sp.nfl && sp.nfl.games) || []), ...((sp.mlb && sp.mlb.games) || [])].filter((g) => g.texas).slice(0, 5);
      for (const g of games) {
        const a = g.away || {}, h = g.home || {};
        out.sports.push({ kind: "sports", url: g.link || null, title: `${a.name} at ${h.name}`, source: "ESPN",
          line: g.state === "pre" ? g.detail : `${a.short} ${a.score}, ${h.short} ${h.score} (${g.state === "in" ? "live, " + (g.detail || "") : g.detail || "final"})`, game: true });
      }
      for (const lg of ["nba", "nfl", "mlb"]) for (const i of ((sp[lg] && sp[lg].news) || []).slice(0, 2))
        out.sports.push({ kind: "sports", url: i.link, title: i.title, source: i.source || "ESPN", published: i.published || null, summary: i.summary || "", line: i.summary || "" });
    }
    for (const i of ((foodData && foodData.items) || []).slice(0, 8))
      out.food.push({ kind: "food", url: i.url, title: i.title, source: i.kind === "creator" ? i.creator : i.outlet, published: i.published || null, summary: i.summary || "",
        place: i.place && i.place.name || "", video: !!i.video, raw: i });
    return out;
  }
  // "Chisme del día": today's top 3 for you, ranked on the phone from your taps (and the For You food profile)
  function chismeDelDia(items) {
    const p = tiaProfile(), now = Date.now(), FY = window.ChismeForYou, fyp = FY ? FY.load() : null;
    const kTot = Object.values(p.k).reduce((a, b) => a + b, 0) || 1;
    const score = (it) => {
      const age = it.published ? Math.max(0, now / 1000 - it.published) / 3600 : 24;
      let s = Math.pow(0.5, age / 18) + (it.near ? 0.4 : 0) + 0.8 * ((p.k[it.kind] || 0) / kTot);
      for (const w of new Set(tiaWords(it.title))) s += Math.min(1.2, 0.35 * (p.t[w] || 0));
      if (it.kind === "food" && fyp && it.raw) s += 0.25 * Math.max(-2, Math.min(4, FY.scoreOf(fyp, it.raw, now)));
      if (it.kind === "event") s += 0.3;
      return s;
    };
    const pool = [...items.stories, ...items.sports.filter((s) => !s.game), ...items.events.slice(0, 5), ...items.food].filter((i) => i.url && i.title);
    const ranked = pool.map((it) => ({ it, s: score(it) })).sort((a, b) => b.s - a.s), out = [], per = {};
    for (const { it } of ranked) {
      if (out.length >= 3) break;
      if ((per[it.kind] || 0) >= 2 || out.some((o) => o.title === it.title)) continue;
      per[it.kind] = (per[it.kind] || 0) + 1; out.push(it);
    }
    return out;
  }
  const tiaGreet = (h) => h >= 5 && h < 12 ? "Buenos días" : h >= 12 && h < 18 ? "Buenas tardes" : "Buenas noches";
  const TIA_EMO = { news: "📰", sports: "🏀", event: "🎉", food: "🌮", weather: "🌤️" };
  function tiaLoad() { try { const h = JSON.parse(localStorage.getItem(TIA_CHAT)); return Array.isArray(h) ? h : []; } catch { return []; } }
  function tiaSave(h) { try { localStorage.setItem(TIA_CHAT, JSON.stringify(h.slice(-TIA_MAX))); } catch {} }
  function citeChip(c) {
    const b = el("button", { type: "button", class: "tia-cite" }, el("span", { class: "ct" }, el("span", { "aria-hidden": "true", text: (TIA_EMO[c.kind] || "🔗") + " " }),
      el("b", { text: c.source || c.kind }), " " + (c.title || "")));
    if (c.sub) b.append(el("small", { class: "cs", text: c.sub }));   // v39: when · venue · price, or a game's status
    b.setAttribute("aria-label", `Open ${c.kind === "weather" ? "the weather" : "“" + c.title + "” from " + (c.source || "the app")} in Chisme`);
    b.onclick = () => {
      if (c.kind === "weather" || !c.url) { tiaDlg.close(); goView(c.kind === "weather" ? "weather" : c.kind === "event" ? "events" : c.kind === "sports" ? "sports" : c.kind === "food" ? "antojos" : "news"); return; }
      tiaLearn(c, c.kind);
      if (c.kind === "food" && c.video && c.raw) openPlayer(c.raw, b); else openReader({ ...c }, b);
    };
    return b;
  }
  function tiaBubble(m) {
    const who = m.role === "tia";
    const body = el("div", { class: "tia-text" });
    for (const [k, line] of (m.text || "").split("\n").entries()) { if (k) body.append(el("br")); body.append(line); }
    return el("li", { class: "tia-msg " + (who ? "from-tia" : "from-me") + (m.mode === "safety" ? " safety" : "") },
      who ? el("img", { class: "tia-mini", src: TIA.avatar(64), srcset: `${TIA.avatar(64)} 1x, ${TIA.avatar(128)} 2x, ${TIA.avatar(192)} 3x`, alt: "", width: 28, height: 28 }) : null,
      el("div", { class: "tia-bub" }, el("span", { class: "sr-only", text: who ? TIA.name + ": " : "You: " }), body,
        m.cites && m.cites.length ? el("div", { class: "tia-cites" }, ...m.cites.map(citeChip)) : null));
  }
  function tiaRender() {
    const h = tiaLoad();
    tiaLog.replaceChildren(...h.map(tiaBubble));
    requestAnimationFrame(() => { tiaLog.scrollTop = tiaLog.scrollHeight; });
  }
  const citeOf = (it) => ({ kind: it.kind, url: it.url, title: it.title, source: it.source, published: it.published || null, summary: it.summary || null,
    image: it.image || null, when: it.when || null, lat: it.lat ?? null, lon: it.lon ?? null, venue: it.venue || null, address: it.address || null,
    video: !!it.video, raw: it.kind === "food" && it.video ? it.raw : undefined });
  function tiaDaily() {   // once a day, the first time you open her: a greeting + chisme del día (no AI call needed)
    const today = dayKey(new Date()), h = tiaLoad();
    if (h.some((m) => m.daily === today)) return;
    const items = tiaItems(), top = chismeDelDia(items), hr = new Date().getHours();
    const wx = items.weather && items.weather.now ? ` It's ${items.weather.now} in ${items.weather.place}${items.weather.alerts ? ", and fíjate: " + items.weather.alerts : ""}.` : "";
    const text = top.length
      ? `${tiaGreet(hr)}, mija! ☕ Tía Chismosa here, your comadre.${wx}\nYour chisme del día, picked for you:`
      : `${tiaGreet(hr)}, mija! ☕ Tía Chismosa here. The feeds are still loading, so ask me in a minute and I'll have the chisme.`;
    h.push({ role: "tia", text, cites: top.map(citeOf), daily: today, t: Date.now() });
    tiaSave(h);
  }
  async function tiaSend(text) {
    text = (text || "").trim().slice(0, 500);
    if (!text || tiaBusy) return;
    const h = tiaLoad(); h.push({ role: "user", text, t: Date.now() }); tiaSave(h); tiaRender();
    tiaBusy = true; $("#tia-send").disabled = true;
    const typing = el("li", { class: "tia-msg from-tia typing", role: "status" }, el("div", { class: "tia-bub" }, el("span", { class: "dots", "aria-hidden": "true" }, el("i"), el("i"), el("i")), el("span", { class: "sr-only", text: TIA.name + " is typing" })));
    tiaLog.append(typing); tiaLog.scrollTop = tiaLog.scrollHeight;
    const items = tiaItems(), byUrl = new Map();
    for (const list of [items.stories, items.events, items.sports, items.food]) for (const it of list) if (it.url) byUrl.set(it.url, it);
    let reply;
    try {
      const r = await fetch("/api/mascot/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: h.slice(-12).map((m) => ({ role: m.role, text: m.text })), hour: new Date().getHours(),
          // v39: the server adds everything it has for this spot (all news sections, sports, weather, events, food)
          loc: { lat: +(+loc.lat).toFixed(3), lon: +(+loc.lon).toFixed(3) }, tz: (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { return null; } })(),
          context: { stories: items.stories, weather: items.weather, events: items.events, sports: items.sports.map((s) => ({ ...s, raw: undefined })), food: items.food.map((f) => ({ ...f, raw: undefined })) } }) });
      const j = await r.json();
      const src = new Map((j.sources || []).map((s) => [s.id, s]));
      let wx = 0;   // one weather chip is enough (they all open the Weather tab)
      const cites = (j.cites || []).map((id) => src.get(id)).filter(Boolean).filter((s) => s.kind !== "weather" || !wx++)
        .map((s) => s.kind === "weather" ? { kind: "weather", title: s.title.startsWith("⚠️") ? s.title : "Weather: " + (s.title.split(" in ").pop() || "forecast"), source: "NWS" }
          : { ...(byUrl.has(s.url) ? citeOf(byUrl.get(s.url)) : { kind: s.kind, url: s.url, title: s.title, source: s.source }), sub: s.sub || null });
      reply = { role: "tia", text: (j.reply || "").replace(/\s*\[S\d{1,3}\]/g, "").trim(), cites, mode: j.mode, t: Date.now() };
    } catch {
      const top = chismeDelDia(items);
      reply = { role: "tia", mode: "offline", t: Date.now(), cites: top.map(citeOf),
        text: navigator.onLine ? "Ay, my signal is fuzzy right now. Try me again in a minute. Meanwhile, here's what's in the app:" : "You're offline, mija. I'll be back when you are. Here's what I saved:" };
    }
    typing.remove();
    const h2 = tiaLoad(); h2.push(reply); tiaSave(h2); tiaRender();
    tiaBusy = false; $("#tia-send").disabled = false;
  }
  function openTia() {
    tiaOpener = document.activeElement;
    tiaDaily(); tiaRender();
    if (!tiaDlg.open) tiaDlg.showModal();
  }
  $("#tia-btn").onclick = openTia;
  $("#tia-close").onclick = () => tiaDlg.close();
  tiaDlg.addEventListener("click", (e) => { if (e.target === tiaDlg) tiaDlg.close(); });
  tiaDlg.addEventListener("close", () => { if (tiaOpener && tiaOpener.isConnected) tiaOpener.focus({ preventScroll: true }); });
  tiaForm.addEventListener("submit", (e) => { e.preventDefault(); const t = tiaIn.value; tiaIn.value = ""; tiaSend(t); });
  for (const b of document.querySelectorAll("#tia-quick button")) b.onclick = () => tiaSend(b.dataset.q);
  // Settings → Forget me: two taps (no pop-up), then everything she knows about you is gone from this phone
  let forgetArm = 0;
  $("#set-forget").onclick = () => {
    const b = $("#set-forget");
    if (Date.now() - forgetArm > 5000) { forgetArm = Date.now(); b.textContent = "Tap again to forget everything"; $("#set-forget-note").textContent = ""; return; }
    forgetArm = 0;
    for (const k of [TIA_CHAT, TIA_PROF]) localStorage.removeItem(k);
    newsForget();
    if (window.ChismeForYou) window.ChismeForYou.reset();
    b.textContent = "Forget me";
    $("#set-forget-note").textContent = "Done. Tía forgot your chats and your interests, and the Bigger the Pansa, Better the Chansa feed starts fresh.";
    if (tiaDlg.open) tiaRender();
  };
  // ---------- Share Chisme: a small pill in the footer. The phone's own share sheet (Web Share API) where there is
  // one; otherwise the link is copied and a toast says so. Nothing opens outside the app.
  const SHARE = { title: "Chisme", text: "Pull up a chair, grab the tea ☕ Local chisme, weather, food & events:", url: "https://chisme.onrender.com/" };
  let shareT = null;
  function shareToast(msg) {
    const t = $("#share-toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(shareT); shareT = setTimeout(() => { t.hidden = true; }, 2600);
  }
  async function copyLink(url) {
    try { await navigator.clipboard.writeText(url); return true; } catch {}
    const ta = el("textarea", { readonly: "", "aria-hidden": "true", class: "sr-only" }); ta.value = url;
    document.body.append(ta); ta.select();
    let ok = false; try { ok = document.execCommand("copy"); } catch {}
    ta.remove(); return ok;
  }
  $("#share-btn").onclick = async () => {
    if (navigator.share) {
      try { await navigator.share(SHARE); return; }
      catch (e) { if (e && e.name === "AbortError") return; }   // closed the share sheet: nothing to do
    }
    shareToast(await copyLink(SHARE.url) ? "Link copied!" : "Copy this link: " + SHARE.url);
  };
  window.__chisme = { get newsPill() { return { held: !!newsHold, n: newsHoldN, shown: !$("#news-pill").hidden }; }, checkNews: () => { loadNews(); lastNews = Date.now(); }, openFromAlert, get pushPrefs() { return pushPrefs(); },
    get frames() { return frames; }, get map() { return map; }, get loc() { return loc; },
    // ready = showing this location's news + weather (fresh or the saved copy); fresh = straight from the server
    get ready() { return secs.weather.shownUrl === secs.weather.url() && secs.news.shownUrl === secs.news.url(); },
    get fresh() { return rendered.weather === q() && rendered.news === q(); },
    get newsReady() { return secs.news.shownUrl === secs.news.url(); }, get sportsReady() { return secs.sports.shownUrl === secs.sports.url(); }, get eventsReady() { return secs.events.shownUrl === secs.events.url(); }, get foodReady() { return !!foodData; },
    get sync() { return { busy: [...Sync.busy], failed: [...Sync.failed.keys()], lastOk: Sync.lastOk }; }, refreshNow, get evCat() { return evCat; }, get view() { return VIEWS[cur]; }, radarColor: (r, g, b) => radarColor(r, g, b), get donateMid() { const c = document.getElementById("donate-mid"); return { opens: midLaunch.opens, line: midLaunch.line, tab: midTab, where: midWhere, placed: !!(c && c.isConnected), dismissed: midGone() }; }, goView, get juegos() { return juegosOpen(); }, get forYou() { return { profile: FY && FY.load(), feed: feedList.map((r) => ({ url: r.item.url, title: r.item.title, creator: r.item.creator, crew: r.crew, place: r.place, why: r.why.text, explore: r.explore, recipe: !!r.item.recipe })), cur: feedCur, open: feed.open, cover: fyList.slice(0, 3).map((r) => r.item.url), coverCrews: fyList.slice(0, 3).map((r) => r.crew) }; }, openFeed, closeFeed,
    get sportsReady() { return !!rendered.sports; }, get spLg() { return spLg; } };
  window.__chismeBooted = true;
})();
