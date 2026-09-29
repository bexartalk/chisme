/* Chisme — frontend (location-aware) */
(() => {
  "use strict";
  const WEATHER_MS = 10 * 60 * 1000;
  const NEWS_MS = 15 * 60 * 1000;
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
  const rendered = { weather: null, news: null };  // which location each section is showing
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
  const icon = (url, size = "medium") => url ? url.replace(/size=\w+/, "size=" + size) : null;
  const kmBetween = (a, b) => {
    const R = 6371, rad = Math.PI / 180;
    const dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };
  document.addEventListener("error", (e) => { if (e.target.tagName === "IMG" && !e.target.closest(".leaflet-container")) e.target.style.visibility = "hidden"; }, true);

  // Tracks which data came from the service worker's saved copy (offline).
  const offlineFrom = {};
  async function getJSON(url, key = url.split("?")[0]) {
    const r = await fetch(url, { cache: "no-store" });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
    if (r.headers.get("X-Chisme-Offline")) offlineFrom[key] = j.generated || true; else delete offlineFrom[key];
    updateOfflineBanner();
    return j;
  }
  function updateOfflineBanner() {
    const b = $("#offline-banner");
    const saved = Object.values(offlineFrom).filter((v) => typeof v === "number");
    if (!navigator.onLine || saved.length) {
      const when = saved.length ? " Showing saved news & weather from " + dateTimeT(new Date(Math.min(...saved) * 1000)) + "." : "";
      b.textContent = "📴 You're offline." + when + " Chisme will refresh when you're back online.";
      b.hidden = false;
    } else b.hidden = true;
  }
  window.addEventListener("offline", updateOfflineBanner);
  window.addEventListener("online", () => { updateOfflineBanner(); refreshAll(); });

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
  const shortPlace = () => (loc.place && (loc.place.neighborhood || loc.place.city)) || placeName();
  function saveLoc() { localStorage.setItem(LOC_KEY, JSON.stringify(loc)); }
  function renderLocLabel() {
    const pre = loc.source === "default" ? "Default: " : "Near: ";
    $("#loc-label").textContent = pre + placeName();
    $("#loc-btn").setAttribute("aria-label", `${pre}${placeName()}. Change location`);
    const city = loc.place && loc.place.city;
    $("#nav-city").textContent = city ? city : "More news";
    $("#city-title").textContent = city ? `More ${city} news` : "More local news";
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
  let watchId = null;
  function onPos(p) {
    const n = { lat: p.coords.latitude, lon: p.coords.longitude };
    if (loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");
  }
  function onPosErr(err) {
    if (err.code === 1) { stopWatch(); if (loc.source !== "manual") showPanel("denied"); }
    else if (loc.source === "default") showPanel("unavailable");
  }
  function startWatch() {
    if (watchId != null || !("geolocation" in navigator)) return;
    watchId = navigator.geolocation.watchPosition(onPos, onPosErr, { enableHighAccuracy: false, maximumAge: 5 * 60e3, timeout: 30e3 });
  }
  function stopWatch() { if (watchId != null) navigator.geolocation.clearWatch(watchId); watchId = null; }
  function requestGPS(fromButton) {
    if (!window.isSecureContext) { showPanel("insecure"); return; }
    if (!("geolocation" in navigator)) { showPanel("unavailable"); return; }
    if (fromButton) $("#loc-status").textContent = "Finding you…";
    navigator.geolocation.getCurrentPosition((p) => {
      const n = { lat: p.coords.latitude, lon: p.coords.longitude };
      if (fromButton || loc.source !== "gps" || kmBetween(loc, n) > MOVE_KM) setLocation(n, "gps");
      startWatch();
    }, onPosErr, { enableHighAccuracy: false, maximumAge: 5 * 60e3, timeout: 30e3 });
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
  function renderAlerts(w) {
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
  function renderForecast(periods) {
    const box = $("#forecast");
    box.replaceChildren();
    if (!periods || !periods.length) { box.append(el("p", { class: "error", text: "Forecast unavailable right now." })); return; }
    const days = [];
    for (const p of periods) {
      const key = fmt(new Date(p.startTime), { year: "numeric", month: "2-digit", day: "2-digit" });
      let d = days.find((x) => x.key === key);
      if (!d) { d = { key, day: null, night: null }; days.push(d); }
      if (p.isDaytime) d.day = p; else d.night = p;
    }
    for (const d of days.slice(0, 7)) {
      const main = d.day || d.night;
      const pop = Math.max(d.day?.pop || 0, d.night?.pop || 0);
      const temps = el("div", { class: "temps" });
      if (d.day) temps.append(d.day.temperature + "°");
      if (d.night) temps.append(d.day ? " / " : "Low ", el("span", { class: "lo", text: d.night.temperature + "°" }));
      box.append(el("article", { class: "day" },
        el("img", { src: icon(main.icon, "medium"), alt: "" }),
        el("div", { class: "dn", text: d.day ? d.day.name : main.name }), temps,
        el("div", { class: "sf", text: main.shortForecast }),
        pop ? el("div", { class: "pop", text: "💧 " + pop + "% chance of rain" }) : null,
        el("details", {}, el("summary", { text: "Details" }),
          d.day ? el("p", { text: d.day.name + ": " + d.day.detailedForecast }) : null,
          d.night ? el("p", { text: d.night.name + ": " + d.night.detailedForecast }) : null)));
    }
  }
  function renderUnsupported(w) {
    const msg = `${w.message} This location is outside NWS coverage, so there's no forecast here. Radar and news still work.`;
    $("#current").replaceChildren(el("p", { class: "notice", text: "🌎 " + msg }));
    $("#hourly").replaceChildren();
    $("#forecast").replaceChildren(el("p", { class: "notice", text: "Forecasts are available for U.S. locations only." }));
    $("#fc-updated").textContent = "";
    $("#fc-credit").textContent = "Weather data: National Weather Service (U.S. only, api.weather.gov)";
  }
  let wxSeq = 0;
  async function loadWeather() {
    const seq = ++wxSeq;
    if (rendered.weather !== q()) $("#current").replaceChildren(el("p", { class: "loading", text: `Loading weather for ${placeName()}…` }));
    try {
      const w = await getJSON(`/api/weather?${q()}`);
      if (seq !== wxSeq) return;  // a newer location won
      rendered.weather = q();
      lastWeather = w;
      if (w.location && w.location.tz) { TZ = w.location.tz; $("#tz-name").textContent = `${w.location.city || "local"} time (${tzAbbr()})`; }
      else { TZ = DEVICE_TZ; $("#tz-name").textContent = `your device's time (${tzAbbr()})`; }
      renderAlerts(w);
      if (w.supported === false) renderUnsupported(w);
      else {
        renderCurrent(w.current); renderHourly(w.hourly); renderForecast(w.forecast);
        if (w.forecast_updated) $("#fc-updated").textContent = "NWS issued " + dateTimeT(new Date(w.forecast_updated));
        $("#fc-credit").textContent = `Source: National Weather Service ${w.location.office || ""} office, grid ${w.location.grid ? w.location.grid.join(",") : ""} (api.weather.gov)`;
      }
      $("#wx-updated").textContent = offlineFrom["/api/weather"] && w.generated
        ? "Saved copy from " + timeT(new Date(w.generated * 1000)) : "Updated " + timeT(new Date());
    } catch (e) {
      if (seq !== wxSeq) return;
      $("#wx-updated").textContent = "";
      $("#current").replaceChildren(el("p", { class: "error", text: "Couldn't load weather: " + e.message + ". Will retry." }));
    }
  }

  // ---------- radar
  let map = null, youMarker = null, frames = [], layers = {}, idx = 0, timer = null, playing = true, radarHost = "";
  function initMap() {
    map = L.map("map", { center: [loc.lat, loc.lon], zoom: 8, minZoom: 3, maxZoom: 12, scrollWheelZoom: false });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
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
  async function loadRadar() {
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
    if (it.image) {
      const img = el("img", { src: it.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.onerror = () => img.remove();
      kids.push(img);
    }
    return el("article", { class: "story" + (showTags && it.tier === "near" ? " near" : "") }, ...kids);
  }
  let newsSeq = 0;
  async function loadNews() {
    const seq = ++newsSeq;
    $("#near-list").replaceChildren(el("p", { class: "loading", text: `Loading news near ${placeName()}…` }));
    try {
      const n = await getJSON(`/api/news?${q()}`);
      if (seq !== newsSeq) return;
      rendered.news = q();
      const p = n.place || {};
      const names = (p.nearby || []).slice(0, 5).map((x) => x.name);
      $("#near-hint").textContent = "Closest first: " + [names.length ? names.join(", ") : null, p.city, p.county].filter(Boolean).join(" → ") + ".";
      $("#near-list").replaceChildren(...(n.near.length ? n.near.map((i) => story(i, true))
        : [el("p", { class: "loading", text: `No stories naming ${placeName()} in the latest feeds yet.` })]));
      $("#city-list").replaceChildren(...(n.more.length ? n.more.map((i) => story(i, false))
        : [el("p", { class: "loading", text: "No other local stories right now." })]));
      $("#sa-sec").hidden = !(n.san_antonio && n.san_antonio.length);
      $("#sa-list").replaceChildren(...(n.san_antonio || []).map((i) => story(i, false)));
      $("#news-updated").textContent = offlineFrom["/api/news"] && n.generated
        ? "Saved copy from " + timeT(new Date(n.generated * 1000)) : "Updated " + timeT(new Date());
      $("#feeds").replaceChildren(...n.feeds.map((f) => el("li", { class: f.ok ? "" : "bad",
        text: (f.ok ? `${f.name}: ${f.count} items` : `${f.name}: unavailable (${f.error})`) + (f.query ? ` — search: ${f.query}` : "") })));
    } catch (e) {
      if (seq !== newsSeq) return;
      $("#near-list").replaceChildren(el("p", { class: "error", text: "Couldn't load news: " + e.message + ". Will retry." }));
    }
  }

  // ---------- boot + auto refresh
  let lastWx = 0, lastNews = 0;
  function refreshAll() { loadWeather(); loadNews(); loadRadar(); lastWx = lastNews = Date.now(); }
  renderLocLabel();
  initMap();
  refreshAll();
  lookupPlace();
  initGeo();
  setInterval(() => { loadWeather(); loadRadar(); lastWx = Date.now(); }, WEATHER_MS);
  setInterval(() => { loadNews(); lastNews = Date.now(); }, NEWS_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    if (Date.now() - lastWx > WEATHER_MS) { loadWeather(); loadRadar(); lastWx = Date.now(); }
    if (Date.now() - lastNews > NEWS_MS) { loadNews(); lastNews = Date.now(); }
  });

  // ---------- PWA: service worker, install button (Android/desktop Chrome), iOS hint
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch((e) => console.warn("SW failed", e)));
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
    get ready() { return rendered.weather === q() && rendered.news === q(); } };
})();
