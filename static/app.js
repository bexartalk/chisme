/* Chisme — frontend (location-aware) */
(() => {
  "use strict";
  const WEATHER_MS = 10 * 60 * 1000;
  const NEWS_MS = 15 * 60 * 1000;
  const EVENTS_MS = 30 * 60 * 1000;
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
  const bump = (d) => { const px = Math.min(30, Math.max(16, Math.round(curFs() + d))); applyFs(px); localStorage.setItem(FS_KEY, px); map && map.invalidateSize(); };
  $("#font-up").onclick = () => bump(2);
  $("#font-down").onclick = () => bump(-2);

  // ---------- location state
  let loc = (() => { try { const s = JSON.parse(localStorage.getItem(LOC_KEY)); if (s && isFinite(s.lat) && isFinite(s.lon)) return s; } catch {} return { ...DEFAULT_LOC }; })();
  const q = () => `lat=${(+loc.lat).toFixed(3)}&lon=${(+loc.lon).toFixed(3)}`;
  const placeName = () => loc.label || "your area";
  const shortPlace = () => (loc.source === "default" ? loc.place && loc.place.city
    : loc.place && (loc.place.neighborhood || loc.place.city)) || placeName();
  function saveLoc() { localStorage.setItem(LOC_KEY, JSON.stringify(loc)); }
  function renderLocLabel() {
    const pre = loc.source === "default" ? "Default: " : "Near: ";
    $("#loc-label").textContent = pre + placeName();
    $("#loc-btn").setAttribute("aria-label", `${pre}${placeName()}. Change location`);
    const city = loc.place && loc.place.city;
    $("#city-title").textContent = city ? `More ${city} news` : "More local news";
    renderGreeting();
    if (lastWeather && rendered.weather === q()) renderAlerts(lastWeather);  // keep alert wording in sync
  }
  async function lookupPlace() {
    const forQ = q();
    try {
      const p = await getJSON(`/api/place?${forQ}`);
      if (forQ !== q()) return;  // location changed while we were waiting
      loc.place = { neighborhood: p.neighborhood, city: p.city, county: p.county, state: p.state_abbr || p.state, country_code: p.country_code };
      // manual searches keep their typed label (e.g. a ZIP) unless we have something nicer
      if (loc.source !== "manual" || !loc.label || /^\d{5}/.test(loc.label)) loc.label = p.label || loc.label;
      if (loc.source === "default") loc.label = DEFAULT_LOC.label;
      saveLoc(); renderLocLabel();
    } catch { /* offline: keep the saved label */ }
  }
  async function setLocation(n, source) {
    const moved = kmBetween(loc, n);
    loc = { lat: +(+n.lat).toFixed(4), lon: +(+n.lon).toFixed(4), source, label: n.label || null, ts: Date.now() };
    saveLoc(); renderLocLabel();
    hidePanel();
    if (map) recenter(moved > 50 ? 8 : null);
    refreshAll();          // start loading right away (shows "Loading…" instead of the old place)
    await lookupPlace();   // then fill in the neighborhood/city label
  }


  // ---------- personality (UI copy only — headlines and story text are never rewritten)
  const pick = (arr) => arr[Math.floor(Date.now() / 36e5) % arr.length];   // changes hourly, stable between renders
  function localHour() { try { return +fmt(new Date(), { hour: "numeric", hourCycle: "h23" }); } catch { return new Date().getHours(); } }
  // Greeting: "¡Buenos días / Buenas tardes / Buenas noches, chismoso!" (or chismosa — the
  // switch next to the greeting; saved on this device, default chismoso).
  const GREET_KEY = "chisme-greeting-word";
  const greetWord = () => (localStorage.getItem(GREET_KEY) === "chismosa" ? "chismosa" : "chismoso");
  function renderGreeting() {
    const h = localHour(), w = greetWord();
    const hi = h >= 5 && h < 12 ? `¡Buenos días, ${w}!` : h >= 12 && h < 18 ? `¡Buenas tardes, ${w}!` : `¡Buenas noches, ${w}!`;
    $("#greet-hi").textContent = hi;
    for (const b of document.querySelectorAll(".greet-switch button")) b.setAttribute("aria-pressed", String(b.dataset.word === w));
    $("#greet-sub").textContent = h >= 22 || h < 5 ? "Here's the latest from around the barrio while the city sleeps."
      : pick(["Here's what the neighborhood is talking about.", "Your local news, closest stories first.", "Pull up a chair — here's the latest from around town."]);
  }
  for (const b of document.querySelectorAll(".greet-switch button")) {
    b.onclick = () => { localStorage.setItem(GREET_KEY, b.dataset.word); renderGreeting(); };
  }

  // ---------- location panel (friendly pre-prompt, denied fallback, change location)
  const PANEL = {
    ask: ["Show news & weather for where you are?",
      "Chisme uses your location only to look up your forecast, weather alerts, radar and nearby stories. It's saved on this device, and you can change it any time. Until then we're showing San Antonio, TX."],
    denied: ["Location is turned off for Chisme",
      "No problem — type a city or ZIP code below. (To use your location later, allow it for this site in your browser or phone settings, then tap “Use my location.”)"],
    unavailable: ["Couldn't find your location",
      "Your device didn't share a location. Type a city or ZIP code below, or try again."],
    insecure: ["Location needs a secure (https) connection",
      "Browsers only share location with https sites. Type a city or ZIP code below instead."],
    change: ["Change location", "Use your current location, or type a city or ZIP code."],
  };
  function showPanel(mode) {
    const [t, m] = PANEL[mode] || PANEL.change;
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
  $("#loc-btn").onclick = () => { if ($("#loc-panel").hidden) { showPanel("change"); $("#loc-panel").scrollIntoView({ block: "start" }); } else hidePanel(); };
  $("#loc-close").onclick = () => { hidePanel(); if (loc.source === "default") sessionStorage.setItem("chisme-ask-later", "1"); };
  $("#loc-gps").onclick = () => requestGPS(true);
  $("#loc-form").onsubmit = async (e) => {
    e.preventDefault();
    const text = $("#loc-q").value.trim();
    if (text.length < 2) return;
    $("#loc-status").textContent = "Searching…";
    $("#loc-results").replaceChildren();
    try {
      const { results } = await getJSON(`/api/geocode?q=${encodeURIComponent(text)}`);
      if (!results.length) { $("#loc-status").textContent = `No places found for “${text}”. Try “City, State” or a 5-digit ZIP.`; return; }
      if (results.length === 1) { $("#loc-status").textContent = ""; setLocation(results[0], "manual"); return; }
      $("#loc-status").textContent = "Pick one:";
      $("#loc-results").replaceChildren(...results.map((r) => {
        const b = el("button", { type: "button", class: "loc-result" }, el("b", { text: r.label }), el("span", { text: r.display_name || "" }));
        b.onclick = () => setLocation(r, "manual");
        return el("li", {}, b);
      }));
    } catch (err) {
      $("#loc-status").textContent = navigator.onLine ? "Search failed: " + err.message : "You're offline — search needs a connection.";
    }
  };

  // ---------- geolocation
  let watchId = null, gpsBusy = false, lastFixAt = 0;
  const GPS_WAIT_MS = 12000;
  function onPos(p) {
    lastFixAt = Date.now();
    const n = { lat: p.coords.latitude, lon: p.coords.longitude };
    if (loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");
  }
  function onPosErr(err, fromButton) {
    if (err.code === 1) { stopWatch(); if (loc.source !== "manual") showPanel("denied"); }
    else if (loc.source === "default") showPanel("unavailable");
    else if (fromButton) $("#loc-status").textContent = `Couldn't get a location fix — still showing ${placeName()}. Try again, or type a city or ZIP.`;
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
    if (fromButton) $("#loc-status").textContent = "Finding you…";
    gpsBusy = true;
    let settled = false;
    const t = setTimeout(() => { if (settled) return; settled = true; gpsBusy = false; onPosErr({ code: 3 }, fromButton); }, GPS_WAIT_MS);
    navigator.geolocation.getCurrentPosition((p) => {
      settled = true; gpsBusy = false; clearTimeout(t); lastFixAt = Date.now();   // a late fix is still welcome
      const n = { lat: p.coords.latitude, lon: p.coords.longitude };
      if (fromButton || loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");
      else if (fromButton) $("#loc-status").textContent = "";
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
    else if (!sessionStorage.getItem("chisme-ask-later")) showPanel("ask");  // friendly pre-prompt
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
    loading: () => $("#current").replaceChildren(el("p", { class: "loading", text: `Checking the sky over ${placeName()}…` })),
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
  let map = null, youMarker = null, frames = [], layers = {}, idx = 0, timer = null, playing = true, radarHost = "";
  function initMap() {
    map = L.map("map", { center: [loc.lat, loc.lon], zoom: 8, minZoom: 3, maxZoom: 12, scrollWheelZoom: false });
    const base = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
    // offline: don't request map tiles that can't load; add them once the connection is back
    if (navigator.onLine) base.addTo(map); else window.addEventListener("online", () => base.addTo(map), { once: true });
    youMarker = L.circleMarker([loc.lat, loc.lon], { radius: 10, color: "#000", weight: 3, fillColor: "#EF426F", fillOpacity: 1 })
      .addTo(map).bindTooltip("You are here", { permanent: true, direction: "right", className: "zip-label" });
    map.attributionControl.addAttribution('Radar &copy; <a href="https://www.rainviewer.com/" target="_blank" rel="noopener">RainViewer</a>');
  }
  function recenter(zoom) {
    youMarker.setLatLng([loc.lat, loc.lon]);
    map.setView([loc.lat, loc.lon], zoom || map.getZoom());
    youMarker.setTooltipContent(loc.source === "default" ? placeName() : "You are here");
  }
  $("#r-center").onclick = () => recenter(8);
  function radarLayer(frame) {
    if (!layers[frame.path]) {
      // RainViewer's free tiles only go to zoom 7; Leaflet upsamples beyond that.
      layers[frame.path] = L.tileLayer(radarHost + frame.path + "/256/{z}/{x}/{y}/2/1_1.png", {
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
    for (const [p, l] of Object.entries(layers)) l.setOpacity(p === f.path ? 0.75 : 0);
    $("#radar-time").textContent = (f.nowcast ? "Forecast " : "") + timeT(new Date(f.time * 1000)) + (idx === frames.length - 1 ? " (latest)" : "");
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
      const next = (j.radar?.past || []).map((f) => ({ ...f, nowcast: false })).concat((j.radar?.nowcast || []).map((f) => ({ ...f, nowcast: true })));
      const keep = new Set(next.map((f) => f.path));
      for (const [p, l] of Object.entries(layers)) if (!keep.has(p)) { map.removeLayer(l); delete layers[p]; }
      frames = next;
      $("#r-slider").max = Math.max(0, frames.length - 1);
      showFrame(frames.length - 1);
      setPlaying(playing);
    } catch (e) {
      $("#radar-time").textContent = navigator.onLine ? "Radar unavailable: " + e.message : "Radar needs a connection";
      clearTimeout(radarRetry); radarRetry = setTimeout(loadRadar, 30000);
    }
  }
  $("#r-play").onclick = () => setPlaying(!playing);
  $("#r-prev").onclick = () => { setPlaying(false); showFrame(idx - 1); };
  $("#r-next").onclick = () => { setPlaying(false); showFrame(idx + 1); };
  $("#r-slider").oninput = (e) => { setPlaying(false); showFrame(+e.target.value); };

  // ---------- news
  function story(it, showTags) {
    const d = it.published ? new Date(it.published * 1000) : null;
    const body = el("div", { class: "body" },
      el("h3", {}, el("a", { href: it.link, target: "_blank", rel: "noopener", text: it.title })),
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
    return el("article", { class: "story" + (showTags && it.tier === "near" ? " near" : "") }, ...kids);
  }

  // Links at the end of each story: the original article, the same story from other outlets we
  // fetched, and a Google News search for the topic. Every URL comes from the feeds/server.
  const ext = (href, text, cls) => el("a", { href, target: "_blank", rel: "noopener", class: cls, text });
  function digDeeper(it) {
    const viaGoogle = /^https:\/\/news\.google\.com\//.test(it.link);
    const read = ext(it.link, `Read full story · ${it.source} ↗`, "btnlink primary");
    if (viaGoogle) read.title = "Opens the original article through Google News";
    const more = it.search_url ? ext(it.search_url, "🔎 More coverage ↗", "btnlink") : null;
    if (more) more.setAttribute("aria-label", "More coverage: search Google News for this story");
    const row = el("div", { class: "dig-row" }, read, more);
    const box = el("div", { class: "dig" });
    if (it.related && it.related.length) {
      box.append(el("p", { class: "related-h", text: "Also reported by" }),
        el("ul", { class: "related" }, ...it.related.map((r) => el("li", {},
          el("a", { href: r.link, target: "_blank", rel: "noopener" }, el("span", { class: "rsrc", text: r.source + ": " }), r.title + " ↗")))));
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
    const lic = a.license_url ? ext(a.license_url, a.license) : el("span", { text: a.license });
    const fig = el("figure", { class: "art" + (a.mural ? " mural" : ""), "data-art": String(a.n) },
      el("div", { class: "art-frame" }, img),
      el("figcaption", {},
        el("p", { class: "art-kicker", text: a.mural ? "🎨 Arte local" : "📍 Postal de Texas" }),
        el("p", { class: "art-cap", text: `${a.subject} · ${a.city}` }),
        a.artist ? el("p", { class: "art-artist", text: a.artist }) : null,
        el("p", { class: "art-credit" }, "Photo: ", el("b", { text: a.author }), " · ", lic, " · ",
          ext(a.source_url, "Source: Wikimedia Commons ↗"))));
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
    loading: () => $("#near-list").replaceChildren(el("p", { class: "loading", text: `Gathering the chisme near ${placeName()}…` })),
    fail: (e) => $("#near-list").replaceChildren(el("p", { class: "error", text: "¡Ay, no! Couldn't reach the news (" + e.message + "). We'll keep trying." })),
    apply: (n, { saved }) => {
      if (!ART.length && !artWait) { artWait = artReady.then(() => { artWait = null; if (lastNewsData) renderNews(lastNewsData, lastNewsSaved); }); }
      if (!saved) rendered.news = q();
      renderNews(n, saved);
    },
  });
  let lastNewsData = null, lastNewsSaved = false;
  function renderNews(n, saved) {
    lastNewsData = n; lastNewsSaved = saved;
    {
      const p = n.place || {};
      const names = (p.nearby || []).slice(0, 5).map((x) => x.name);
      $("#near-hint").textContent = "Closest first: " + [names.length ? names.join(", ") : null, p.city, p.county].filter(Boolean).join(" → ") + ".";
      $("#near-list").replaceChildren(...(n.near.length ? withArt(n.near.map((i) => story(i, true)))
        : [el("p", { class: "loading", text: `No stories naming ${placeName()} in the latest feeds yet — check back in a bit.` })]));
      $("#city-list").replaceChildren(...(n.more.length ? withArt(n.more.map((i) => story(i, false)))
        : [el("p", { class: "loading", text: "No other local stories right now. The newsrooms must be on a coffee break. ☕" })]));
      $("#sa-sec").hidden = !(n.san_antonio && n.san_antonio.length);
      $("#sa-list").replaceChildren(...withArt((n.san_antonio || []).map((i) => story(i, false))));
      saveArtCursor();
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
    const a = el("a", { class: "minimap", href, target: "_blank", rel: "noopener", "aria-label": `Map: ${e.venue || "event location"} (opens OpenStreetMap)` }, img, pin);
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
    return ext(e.url, "Check price ↗", "price check");
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
    const also = (e.also || []).map((a, k) => [k ? ", " : " · also on ", ext(a.url, a.source)]).flat();
    return el("article", { class: "ev" }, media,
      el("div", { class: "ev-body" },
        el("h3", {}, ext(e.url, e.title)),
        el("div", { class: "ev-line" }, el("span", { text: "🗓", "aria-hidden": "true" }), el("span", { text: whenText(e) })),
        venue,
        el("div", { class: "ev-line" }, el("span", { text: "🎟", "aria-hidden": "true" }), priceBadge(e)),
        outlook(e),
        e.summary ? el("p", { class: "ev-sum", text: e.summary }) : null,
        el("div", { class: "ev-links" }, ext(e.url, `Event page (${e.source}) ↗`, "primary"),
          gmaps ? ext(gmaps, "🗺 Map & directions ↗") : null,
          e.website && e.website !== e.url ? ext(e.website, "Organizer site ↗") : null),
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
    food: { test: (e) => (e.tags || []).includes("food"),
      intro: () => "🌮 ¡Provecho! What local food creators are eating, plus food & drink events coming up.",
      empty: "No food & drink events on the calendars right now — the reviews above will have to hold you over. 🌮" },
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
    $("#food-block").hidden = evCat !== "food";
    if (evCat === "food") renderFood();
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
  }
  for (const b of document.querySelectorAll("#ev-chips .chip")) {
    b.onclick = () => {
      evCat = b.dataset.cat; localStorage.setItem(CAT_KEY, evCat);
      renderEventList();
      if (evCat === "food" && !foodData) loadFood();
    };
  }
  const shortDate = (t) => fmt(new Date(t * 1000), { month: "short", day: "numeric" });
  function foodItem(it) {
    const thumb = el("a", { class: "fr-thumb", href: it.url, target: "_blank", rel: "noopener", tabindex: "-1", "aria-hidden": "true" });
    const ph = () => el("div", { class: "ev-ph", role: "img", "aria-label": it.image ? "Photo loads when you're online" : "No photo in the feed" },
      el("b", { text: it.video ? "🎥" : "📰", "aria-hidden": "true" }), el("span", { text: it.image ? "offline" : "no photo" }));
    if (it.image && navigator.onLine) {
      const img = el("img", { src: it.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.replaceWith(ph());
      thumb.append(img);
      if (it.video) thumb.append(el("span", { class: "play", text: "▶" }));
    } else thumb.append(ph());
    const by = it.kind === "creator" ? `${it.creator}` : [it.outlet, it.author].filter(Boolean).join(" · ");
    return el("article", { class: "fr" + (it.kind === "creator" ? " fr-card" : "") }, thumb,
      el("div", { class: "fr-body" },
        el("h4", {}, ext(it.url, it.title)),
        el("p", { class: "fr-by" }, el("b", { text: by }), it.published ? " · " + shortDate(it.published) : ""),
        it.summary ? el("p", { class: "fr-sum", text: it.summary }) : null,
        ext(it.url, it.video ? "▶ Watch on YouTube ↗" : "Read it ↗", "fr-go")));
  }
  function renderFood() {
    const n = foodData;
    if (!n) return;
    if (n.message) {
      $("#food-creators").replaceChildren(el("p", { class: "loading", text: n.message + " ¡Lo siento!" }));
      $("#food-outlets").replaceChildren();
      return;
    }
    const cr = n.items.filter((i) => i.kind === "creator"), out = n.items.filter((i) => i.kind === "outlet");
    const group = (items, max, emptyText) => {
      if (!items.length) return [el("p", { class: "loading", text: emptyText })];
      const first = items.slice(0, max).map(foodItem), rest = items.slice(max);
      if (!rest.length) return first;
      return [...first, el("details", { class: "more-food" }, el("summary", { text: `${rest.length} more` }), ...rest.map(foodItem))];
    };
    $("#food-creators").replaceChildren(...(cr.length ? cr.map(foodItem) : [el("p", { class: "loading", text: "The creators are between bites — no new videos lately." })]));
    $("#food-outlets").replaceChildren(...group(out, 5, "No new food coverage in the feeds right now."));
    $("#food-sources").replaceChildren(...(n.sources || []).map((f) => el("li", { class: f.ok ? "" : "bad" },
      ext(f.home, f.name), f.ok ? `: ${f.count} recent ${f.kind === "creator" ? "videos" : "stories"}` : `: unavailable right now (${f.error})`)));
  }
  section("food", {
    url: () => `/api/food?${q()}`,
    apply: (n, { saved }) => { foodData = n; foodFresh = foodFresh || !saved; renderFood(); },
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

  // ---------- views: News | Weather | Events (tap the sticky buttons or swipe sideways)
  const VIEWS = ["news", "weather", "events"];
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
    if (VIEWS[i] === "events" && rendered.events !== q()) loadEvents();
    if (scrollId) { const t = document.getElementById(scrollId); if (t) window.scrollTo({ top: t.getBoundingClientRect().top + window.scrollY - tabsH() - 8, behavior: "instant" }); }
    localStorage.setItem("chisme-swiped", "1");
  }
  let animT = null;
  function goView(name, opts = {}) {
    const i = typeof name === "number" ? name : VIEWS.indexOf(name);
    if (i < 0) return;
    if (i === cur) { unpeek(); track.classList.add("animating"); pos(i); if (opts.scrollTo) finish(i, opts.scrollTo); else updateTabs(); return; }
    if (opts.instant || matchMedia("(prefers-reduced-motion: reduce)").matches) { peek(i); finish(i, opts.scrollTo); return; }
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
  const NO_SWIPE = ".leaflet-container, .hourly, .forecast, .chips, .food-strip, input, select, textarea, .no-swipe";
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
  // Deep links (manifest shortcuts): #weather, #radar-sec, #events. Otherwise News opens first.
  const HASH_VIEW = { "#weather": ["weather"], "#forecast-sec": ["weather", "forecast-sec"], "#radar-sec": ["weather", "radar-sec"],
    "#alerts": ["weather", "alerts"], "#events": ["events"], "#food": ["events"], "#near": ["news", "near"], "#city": ["news", "city"] };
  pos(0); updateTabs();

  // ---------- boot + auto refresh
  let lastWx = 0, lastNews = 0, lastEv = 0, evBoot = null;
  function refreshAll() {
    loadNews(); loadWeather(); loadRadar(); lastWx = lastNews = Date.now();
    // events load right after news (and immediately if the Events view is open), so they're saved for offline too
    clearTimeout(evBoot);
    if (VIEWS[cur] === "events") loadEvents(); else evBoot = setTimeout(loadEvents, 1200);
    lastEv = Date.now();
  }
  renderLocLabel();
  initMap();
  if (location.hash === "#food") { evCat = "food"; localStorage.setItem(CAT_KEY, evCat); }
  const hv = HASH_VIEW[location.hash];
  if (hv && hv[0] !== "news") goView(hv[0], { instant: true });
  refreshAll();
  if (hv && hv[1]) setTimeout(() => goView(hv[0], { scrollTo: hv[1] }), 50);
  lookupPlace();
  initGeo();
  setInterval(() => { loadWeather(); loadRadar(); lastWx = Date.now(); }, WEATHER_MS);
  setInterval(() => { loadNews(); lastNews = Date.now(); renderGreeting(); }, NEWS_MS);
  setInterval(() => { loadEvents(); lastEv = Date.now(); }, EVENTS_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    renderGreeting();
    if (Date.now() - lastWx > WEATHER_MS) { loadWeather(); loadRadar(); lastWx = Date.now(); }
    if (Date.now() - lastNews > NEWS_MS) { loadNews(); lastNews = Date.now(); }
    if (Date.now() - lastEv > EVENTS_MS) { loadEvents(); lastEv = Date.now(); }
    retryFailed();   // back in the app: don't wait out the backoff
  });
  // Manual refresh (pull down at the top, "Retry now", or Settings → Refresh now)
  function refreshNow() {
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
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!hadController) return;           // first install, nothing changed on screen
      pendingReload = true;
      $("#update-toast").hidden = false;
    });
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
  window.__chisme = { get frames() { return frames; }, get map() { return map; }, get loc() { return loc; },
    // ready = showing this location's news + weather (fresh or the saved copy); fresh = straight from the server
    get ready() { return secs.weather.shownUrl === secs.weather.url() && secs.news.shownUrl === secs.news.url(); },
    get fresh() { return rendered.weather === q() && rendered.news === q(); },
    get eventsReady() { return secs.events.shownUrl === secs.events.url(); }, get foodReady() { return !!foodData; },
    get sync() { return { busy: [...Sync.busy], failed: [...Sync.failed.keys()], lastOk: Sync.lastOk }; }, refreshNow, get evCat() { return evCat; }, get view() { return VIEWS[cur]; }, goView };
})();
