/* Chisme · Juegos game 3: "Puro Pinche Lowrider" (v49.16; first built as "Lowrider Hop"). Hop it. Drop it. Don't scrape it.
   A one-thumb arcade game: HOLD to charge the hydraulics, LET GO to hop, TAP right before you land (when the shrinking
   ring meets the dashed one). Landings: PERFECT HOP! · PURO STYLE · AY GÜEY! · YOU SCRAPED IT!. Clean hops build the
   combo (x2, x5, x10, x25) and Feria, earned ONLY by playing (no purchases anywhere), which unlocks rides and paint in the Garage.
   Vector art on a canvas at devicePixelRatio (the title screen's key art + its lettering font are the only files); procedural
   WebAudio music + SFX; speechSynthesis for a few voice lines (else just the text pops). Loaded lazily by juegos.js.
   Everything is data-driven so later updates can add rides (CARS), paint (PAINTS), events (EVENTS), storefront / billboard
   ads (SIGNS: a real sponsor is a one-line swap) and stages (STAGES: "San Antonio" lives in lowrider-sa.js, loaded the
   first time it's picked) without touching the game loop.
   The rides are only inspired by classic lowriders: no real makes, badges, brands, songs or characters.
   Progress lives on this phone in localStorage "lowrider_v1" (versioned). The "Your best runs" board is local; a weekly
   server board can plug in later through the same { list, submit } shape (see BOARD). */
(function (root) {
  "use strict";
  const SAVE_KEY = "lowrider_v1", SAVE_V = 2;   // v2: rides you unlock + paint per ride
  const COL = { turq: "#00C9CD", pink: "#FF1A7F", orange: "#FF6A0B", black: "#000000", white: "#FFFFFF", silver: "#C9CED6", purple: "#7B2CBF", night: "#14072B" };
  const UPM = 34;                 // world units per meter (the '64 is ~200 units ≈ 5.9 m)
  const MILE = 1609.34;
  const TITLE = "Puro Pinche Lowrider";
  const TITLE_FONT = '"PPL Display", "UnifrakturCook", "Old English Text MT", serif';   // static/fonts/ppl-display.woff2: a subset of UnifrakturCook Bold (OFL)
  const BUILD = (() => { try { const m = /[?&]v=([^&]+)/.exec((document.currentScript && document.currentScript.src) || ""); return m ? m[1] : ""; } catch (e) { return ""; } })();
  const FONT = '"Lowrider Display", "Chisme Site Display", "Arial Rounded MT Bold", "Arial Black", system-ui, sans-serif';
  const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif';

  // ---------------------------------------------------------------- data (add rides / paint / events / signs here)
  // Paint for any ride you've unlocked (bought once, then it's yours on every ride). No gold: no yellow in Chisme's UI.
  const PAINTS = [
    { id: "candy", name: "Candy red", price: 0, deep: "#3d0010", base: "#9a0b22", mid: "#dd1636", hi: "#ff7d8e", flake: "#ffd0d8", trim: "#ffffff", seat: "#f4f1f4", pipe: "#c4132f" },
    { id: "turq", name: "Turquoise", price: 120, deep: "#00363b", base: "#00818a", mid: "#00bcc4", hi: "#9ef9fb", flake: "#e6ffff", trim: "#ffffff", seat: "#f4fbfb", pipe: "#00a3ab" },
    { id: "purple", name: "Purple", price: 250, deep: "#1b0540", base: "#46148e", mid: "#7a32d4", hi: "#cfa8ff", flake: "#f1e4ff", trim: "#ffffff", seat: "#efe6fb", pipe: "#6a26c0" },
    { id: "cherry", name: "Black cherry", price: 400, deep: "#0d0106", base: "#33061a", mid: "#6a0f33", hi: "#d4628a", flake: "#ffb0cc", trim: "#ffffff", seat: "#5a0c2a", pipe: "#ff4f8f" },
    { id: "pearl", name: "Pearl white", price: 600, deep: "#7f7b96", base: "#cfccdf", mid: "#f1eff8", hi: "#ffffff", flake: "#ffd6ee", trim: "#ffffff", seat: "#d81b60", pipe: "#ffffff", pearl: true },
  ];
  // Rides, unlocked with Feria (earned only by playing). Same wheelbase + hydraulics for now (phys can differ per ride later);
  // body: which art; wheel: "bronze" (warm, never yellow) or "chrome"; orig: the ride's own factory look ("Original").
  const PHYS = { g: 1500, vMin: 470, vMax: 930, chargeT: 0.82, spring: 230, damp: 15 };
  const CARS = [
    { id: "primer", name: "The '64 (Primer)", blurb: "Rusty, patched and proud. Every patch has a story.", price: 0, body: "64", wheel: "bronze", paint: "orig", matte: true,
      orig: { id: "orig", name: "Original", patch: true, deep: "#3b3f46", base: "#7c828b", mid: "#a2a8b0", hi: "#d3d7dc", flake: "#ffffff", trim: "#e9edf1", seat: "#5a2a2e", pipe: "#8a3a3e" }, phys: PHYS },
    { id: "64", name: "The '64 (Candy)", blurb: "Restored, candy paint, way too clean.", price: 900, body: "64", wheel: "chrome", paint: "candy", phys: PHYS },
    { id: "jefe", name: "El Jefe '76", blurb: "A '70s land yacht: vinyl top, opera windows, zero shame.", price: 2400, body: "76", wheel: "chrome", paint: "orig",
      orig: { id: "orig", name: "Original", deep: "#0a1430", base: "#1c2d5a", mid: "#30508f", hi: "#a3b8e8", flake: "#e6eeff", trim: "#ffffff", seat: "#efe9f2", pipe: "#7b2cbf", roof: "#f1eff8" }, phys: PHYS },
  ];
  const carById = (id) => CARS.find((c) => c.id === id) || CARS[0];
  const paintFor = (car, id) => (id === "orig" && car.orig) || PAINTS.find((p) => p.id === id) || car.orig || PAINTS[0];
  // Stages, picked on the title screen. file: loaded the first time it's played (it registers ChismeLowrider.stages[id]).
  const STAGES = [
    { id: "blvd", name: "Boulevard", blurb: "Southside cruise night." },
    { id: "sa", name: "San Antonio", blurb: "The Alamo, the Missions, traffic. Watch your gas.", file: "lowrider-sa.js" },
  ];
  // Obstacles: w × h in world units; pit = only a wheel on the ground drops in; soft = a jolt, no wheel lost.
  const OBST = { // v49.27: low road hazards and jumpable cartoon patrol
    pallet: { w: 62, h: 18, min: 0.05 }, copcar: { w: 116, h: 38, min: 0.1 },
    bump: { w: 54, h: 9, min: 0 }, hump: { w: 64, h: 13, min: 0 }, pothole: { w: 50, h: 0, pit: true, min: 0 },
    cone: { w: 18, h: 30, min: 0 }, cones: { w: 64, h: 30, min: 0.12 }, rails: { w: 56, h: 9, min: 0.1 },
    tires: { w: 36, h: 34, min: 0.18 }, cooler: { w: 32, h: 24, min: 0.08 }, mattress: { w: 72, h: 20, min: 0.25 },
    couch: { w: 74, h: 40, min: 0.35 }, pinata: { w: 40, h: 34, min: 0.2 }, barricade: { w: 36, h: 52, min: 0.5 },
  };
  // Random events: Abuela Crossing + La Chancla (every stage), Trail Ride (stage: "sa"). first/every are seconds of play.
  const EVENTS = {
    abuela: { name: "Abuela Crossing", first: 17, every: [26, 42], bonus: 500, feria: 10 },
    chancla: { name: "La Chancla", first: 26, every: [15, 27], bonus: 300, feria: 5 },
    // San Antonio only, rare: a line of riders crosses; the car always stops (like for Abuela), and every hop while they cross is a salute.
    trail: { name: "Trail Ride", stage: "sa", first: 70, every: [100, 160], chance: 0.45, bonus: 150, max: 6, feria: 3, horses: 10 },
  };
  // Storefront + billboard ads along the boulevard. All made up (each checked against San Antonio businesses before use);
  // swap in a real sponsor by replacing one line (keep slot + kind; set sponsor: true). house: Chisme's own ad spot.
  // slot: "store" (painted sign on a building of that kind) or "billboard" (the back billboards). Fiesta colors, no yellow.
  const SIGNS = [
    { name: "Tacos El Chismoso", tagline: "Our salsa talks.", colors: ["#FF1A7F", "#FFFFFF", "#00C9CD"], slot: "store", kind: "taco", sponsor: false },
    { name: "Llantera La Rueda Chismosa", tagline: "Flat? Not our fault.", colors: ["#000000", "#FFFFFF", "#FF6A0B"], slot: "store", kind: "tires", sponsor: false },
    { name: "Ice House La Metiche", tagline: "Cold drinks. Hot chisme.", colors: ["#00C9CD", "#000000", "#FF1A7F"], slot: "store", kind: "icehouse", sponsor: false },
    { name: "Piñatería Pégale", tagline: "Hit it like it owes you money.", colors: ["#7B2CBF", "#FFFFFF", "#FF1A7F"], slot: "store", kind: "pinata", sponsor: false },
    { name: "Carnicería Don Metiche", tagline: "Fresh cuts. Zero secrets.", colors: ["#D81B3C", "#FFFFFF", "#000000"], slot: "store", kind: "shop", sponsor: false },
    { name: "Barbería El Fade Chueco", tagline: "We fix your tío's haircut.", colors: ["#000000", "#00C9CD", "#FF1A7F"], slot: "store", kind: "barber", sponsor: false },
    { name: "Lavandería La Burbuja Chismosa", tagline: "We air your dirty laundry.", colors: ["#00C9CD", "#FFFFFF", "#7B2CBF"], slot: "store", kind: "shop", sponsor: false },
    { name: "Hidráulicas El Brinco", tagline: "We make it bounce.", colors: ["#FF6A0B", "#000000", "#FFFFFF"], slot: "store", kind: "shop", sponsor: false },
    { name: "Raspas Tía Chismosa", tagline: "Brain freeze, con cariño.", colors: ["#FF1A7F", "#FFFFFF", "#00C9CD"], slot: "billboard", kind: "", sponsor: false },
    { name: "Paletería Ay Mija", tagline: "Cool down, mija.", colors: ["#00C9CD", "#FFFFFF", "#FF1A7F"], slot: "billboard", kind: "", sponsor: false },
    { name: "Panadería La Abuela Sabe", tagline: "She knows what you did.", colors: ["#7B2CBF", "#FFFFFF", "#FF6A0B"], slot: "billboard", kind: "", sponsor: false },
    { name: "Tortillería Doña Metiche", tagline: "Hot off the comal. Hotter gossip.", colors: ["#FF6A0B", "#FFFFFF", "#000000"], slot: "billboard", kind: "", sponsor: false },
    { name: "YOUR BUSINESS HERE", tagline: "Ask Chisme", colors: ["#000000", "#FFFFFF", "#00C9CD"], slot: "billboard", kind: "", sponsor: false, house: true },
  ];
  // v49.27: text-only sponsor inventory; the house rotation always stays available.
  const SPONSOR_SLOTS = SIGNS.map((s, i) => ({ id: "slot-" + i, name: s.name, line: s.tagline, colors: [...s.colors], art: "text", sponsor: false, house: !!s.house }));
  let sponsors = SPONSOR_SLOTS;
  function setSponsors(list) {
    const text = (v, n) => typeof v === "string" && v.length > 0 && v.length <= n && !/[<>\x00-\x1f]|(?:https?:|www\.|[a-z0-9-]+\.[a-z]{2,}(?:\b|\/)|data:|javascript:|\/\/)/i.test(v);
    if (!Array.isArray(list) || list.length > 40 || list.some((s) => !s || !text(s.id, 40) || !text(s.name, 64) || !text(s.line, 100) || (s.art != null && s.art !== "text") || !Array.isArray(s.colors) || s.colors.length !== 3 || s.colors.some((c) => !["#000000", "#FFFFFF", "#00C9CD", "#FF1A7F", "#7B2CBF", "#FF6A0B"].includes(c)))) return false;
    if (new Set(list.map((s) => s.id)).size !== list.length) return false;
    sponsors = list.map((s) => ({ id: s.id, name: s.name, line: s.line, colors: [...s.colors], art: "text", sponsor: s.sponsor === true }));
    if (!sponsors.length) sponsors = SPONSOR_SLOTS;
    if (lib.current) lib.current.debug.refreshSponsors(); return true;
  }
  const godSaves = new WeakSet(); // v49.27: sandbox every save path during an owner run
  const ACH = [
    { id: "first", name: "First Hop", desc: "Land your first hop." },
    { id: "puro", name: "Puro Pinche Style", desc: "10 PERFECT HOPs in a row." },
    { id: "scratch", name: "Not a Scratch", desc: "Cruise 1 mile in one run without scraping." },
    { id: "ayguey", name: "Ay Güey", desc: "Completely destroy a landing (scrape a full-power hop)." },
    { id: "addict", name: "Hydraulic Addiction", desc: "1,000 hops, total.", goal: 1000, of: "hops" },
    { id: "elders", name: "Respect Your Elders", desc: "Stop for 25 Abuela Crossings.", goal: 25, of: "abuelas" },
  ];
  const GRADES = {
    perfect: { text: "PERFECT HOP!", pts: 100, feria: 2, color: COL.turq, edge: COL.black, icon: "flame" },
    puro: { text: "PURO STYLE", pts: 60, feria: 1, color: COL.white, edge: COL.black, icon: "shades" },
    ay: { text: "AY GÜEY!", pts: 25, feria: 0, color: COL.orange, edge: COL.black, icon: "burst" },
    scraped: { text: "YOU SCRAPED IT!", pts: 0, feria: 0, color: COL.pink, edge: COL.black, icon: "skull" },
  };
  const TIERS = [{ at: 0, x: 1, f: 1 }, { at: 3, x: 2, f: 2 }, { at: 6, x: 5, f: 3 }, { at: 10, x: 10, f: 5 }, { at: 16, x: 25, f: 8 }];
  const WIN = { perfect: 0.11, puro: 0.24, ay: 0.42, late: 0.09, lateOk: 0.045 };   // landing windows, seconds before touchdown
  const CHEERS = ["¡NO MAMES!", "¡ÓRALE!", "¡ESO!", "¡AJÚA!", "¡QUÉ CHULO!", "Damn, that '64 is clean."];
  const WINCES = ["¡AY GÜEY!", "Ooof.", "¡Híjole!", "My tío felt that."];
  const OVER_LINES = ["Tow truck's on the way, güey.", "The '64 needs a minute.", "Your tío is gonna hear about this.", "Puro style. Mostly.", "Abuela saw that. She's not mad, just disappointed."];

  // ---------------------------------------------------------------- save (localStorage, versioned)
  function fresh() {
    return { v: SAVE_V, feria: 0, best: 0, owned: { car: ["primer"], paint: ["candy"] }, equip: { car: "primer", paint: "orig" }, carPaint: {}, stage: "blvd", ach: {}, runs: [],
      totals: { hops: 0, perfects: 0, abuelas: 0, runs: 0, meters: 0, feria: 0, chanclas: 0, cops: 0, trails: 0 }, laps: {}, howto: false, muted: null };
  }
  function migrate(o) {   // v1 → v2: you keep everything; the v1 ride (the candy '64) stays yours next to the free Primer
    const d = fresh();
    if (!o || typeof o !== "object" || (o.v !== SAVE_V && o.v !== 1)) return d;
    const n = (v, def = 0) => (typeof v === "number" && isFinite(v) && v >= 0 ? Math.min(Number.MAX_SAFE_INTEGER, Math.floor(v)) : def);
    d.feria = n(o.feria); d.best = n(o.best);
    if (o.owned && Array.isArray(o.owned.paint)) d.owned.paint = [...new Set(["candy", ...o.owned.paint.filter((p) => PAINTS.some((x) => x.id === p))])];
    if (o.v === 1) { d.owned.car = ["primer", "64"]; d.equip.car = "64"; d.equip.paint = o.equip && d.owned.paint.includes(o.equip.paint) ? o.equip.paint : "candy"; }
    else {
      if (o.owned && Array.isArray(o.owned.car)) d.owned.car = [...new Set(["primer", ...o.owned.car.filter((c) => CARS.some((x) => x.id === c))])];
      const ok = (car, p) => (p === "orig" && !!car.orig) || d.owned.paint.includes(p);
      if (o.carPaint && typeof o.carPaint === "object") for (const c of CARS) if (d.owned.car.includes(c.id) && typeof o.carPaint[c.id] === "string" && ok(c, o.carPaint[c.id])) d.carPaint[c.id] = o.carPaint[c.id];
      if (o.equip && d.owned.car.includes(o.equip.car)) d.equip.car = o.equip.car;
      const ec = carById(d.equip.car); d.equip.paint = d.carPaint[ec.id] || (o.equip && ok(ec, o.equip.paint) ? o.equip.paint : ec.paint); // v49.26: recover valid v2 equipped paint
      if (STAGES.some((s) => s.id === o.stage)) d.stage = o.stage;
    }
    if (o.ach && typeof o.ach === "object") for (const a of ACH) if (o.ach[a.id]) d.ach[a.id] = n(o.ach[a.id], 1);
    if (o.laps && typeof o.laps === "object") for (const s of STAGES) if (o.laps[s.id]) d.laps[s.id] = Math.min(9, n(o.laps[s.id], 1));   // finished a stage's run (San Antonio: unlocks Otra vuelta)
    if (Array.isArray(o.runs)) d.runs = o.runs.filter((r) => r && typeof r.score === "number").slice(0, 10).map((r) => ({ fin: r.fin === true, lap: Math.max(1, Math.min(2, n(r.lap, 1))), score: n(r.score), meters: n(r.meters), feria: n(r.feria), perfects: n(r.perfects), combo: n(r.combo, 1), car: CARS.some((c) => c.id === r.car) ? r.car : "64", paint: String(r.paint || "candy").slice(0, 12), stage: STAGES.some((s) => s.id === r.stage) ? r.stage : "blvd", at: n(r.at), week: String(r.week || "").slice(0, 10) }));
    if (o.totals) for (const k of Object.keys(d.totals)) d.totals[k] = n(o.totals[k]);
    d.howto = !!o.howto; d.muted = typeof o.muted === "boolean" ? o.muted : null;
    return d;
  }
  const walletSaved = new WeakMap(); // v49.26: retain unsaved earnings if storage writes fail
  function load() { let s; try { s = migrate(JSON.parse(localStorage.getItem(SAVE_KEY) || "null")); } catch (e) { s = fresh(); } walletSaved.set(s, s.feria); return s; }
  function save(s) { if (godSaves.has(s)) return; try { localStorage.setItem(SAVE_KEY, JSON.stringify(s)); walletSaved.set(s, s.feria); } catch (e) {} }
  function reset() { try { localStorage.removeItem(SAVE_KEY); } catch (e) {} }
  // ISO week ("2026-W40"): what a later weekly board would group runs by
  function isoWeek(ms) { const d = new Date(ms); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7)); const w1 = new Date(d.getFullYear(), 0, 4);
    return d.getFullYear() + "-W" + String(1 + Math.round(((d - w1) / 864e5 - 3 + ((w1.getDay() + 6) % 7)) / 7)).padStart(2, "0"); }
  // "Your best runs": local only for now. A server board can implement the same two calls later.
  const BOARD = {
    list(st) { return st.runs.slice(0, 10); },
    submit(st, run) { st.runs.push(run); st.runs.sort((a, b) => b.score - a.score || a.at - b.at); st.runs = st.runs.slice(0, 10); return st.runs.indexOf(run); },
  };
  const tierOf = (streak) => { let t = 0; for (let i = 0; i < TIERS.length; i++) if (streak >= TIERS[i].at) t = i; return t; };
  function gradeFor(dt, late) {   // dt = seconds the TAP came before touchdown (late: it came after)
    if (late) return dt <= WIN.lateOk ? "puro" : dt <= WIN.late ? "ay" : "scraped";
    return dt <= WIN.perfect ? "perfect" : dt <= WIN.puro ? "puro" : dt <= WIN.ay ? "ay" : "scraped";
  }
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Math.round(+n || 0).toLocaleString("en-US");
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }

  // ---------------------------------------------------------------- sound: everything made on the phone with WebAudio
  // An original laid-back cruising groove (~94 BPM, A minor dorian vamp Am7 → D9): bass line, kick/snare/hats, congas,
  // clave, güiro, cowbell and a light combo organ; it builds with the combo and slows + muffles for Abuela.
  function makeAudio(clock) {
    let ac = null, master, music, musicLP, sfx, organBus, noise, muted = false, playing = false, timer = null;
    let step = 0, nextT = 0, bpm = 94, wantBpm = 94, intensity = 0, bars = 0, pump = null;
    const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
    function ctx() {
      if (!ac) {
        const A = root.AudioContext || root.webkitAudioContext; if (!A) return null;
        try { ac = new A(); } catch (e) { return null; }
        master = ac.createGain(); master.gain.value = muted ? 0 : 0.85; master.connect(ac.destination);
        musicLP = ac.createBiquadFilter(); musicLP.type = "lowpass"; musicLP.frequency.value = 18000; musicLP.Q.value = 0.7;
        music = ac.createGain(); music.gain.value = 0.5; music.connect(musicLP); musicLP.connect(master);
        sfx = ac.createGain(); sfx.gain.value = 0.9; sfx.connect(master);
        organBus = ac.createGain(); organBus.gain.value = 0.16; organBus.connect(music);
        const lfo = ac.createOscillator(), lg = ac.createGain(); lfo.frequency.value = 5.6; lg.gain.value = 0.05; lfo.connect(lg).connect(organBus.gain); lfo.start();
        const len = ac.sampleRate; noise = ac.createBuffer(1, len, ac.sampleRate); const d = noise.getChannelData(0); for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      }
      if (ac.state === "suspended") { try { ac.resume().catch(() => {}); } catch (e) {} }
      return ac;
    }
    const env = (g, t, a, peak, dec, floor = 0.0001) => { g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(floor, t + a + dec); };
    function osc(type, f, t, dur, peak, dest, a = 0.004, f2 = null, fdur = null) {
      const o = ac.createOscillator(), g = ac.createGain(); o.type = type; o.frequency.setValueAtTime(f, t);
      if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + (fdur || dur)); env(g, t, a, peak, dur); o.connect(g).connect(dest); o.start(t); o.stop(t + a + dur + 0.05); return o;
    }
    function nz(t, dur, peak, dest, type, f, q = 1, a = 0.002, f2 = null) {
      const s = ac.createBufferSource(), fl = ac.createBiquadFilter(), g = ac.createGain(); s.buffer = noise; s.loop = true;
      fl.type = type; fl.frequency.setValueAtTime(f, t); if (f2) fl.frequency.exponentialRampToValueAtTime(f2, t + dur); fl.Q.value = q;
      env(g, t, a, peak, dur); s.connect(fl).connect(g).connect(dest); s.start(t, Math.random() * 0.5); s.stop(t + a + dur + 0.05); return { s, fl, g };
    }
    // --- drum kit + Latin percussion
    const kick = (t, v = 1) => { osc("sine", 130, t, 0.32, 0.9 * v, music, 0.002, 42, 0.13); nz(t, 0.02, 0.15 * v, music, "lowpass", 900); };
    const snare = (t, v = 1) => { nz(t, 0.17, 0.32 * v, music, "bandpass", 1900, 0.8); osc("triangle", 200, t, 0.08, 0.25 * v, music, 0.002, 150); };
    const hat = (t, open, v = 1) => nz(t, open ? 0.2 : 0.035, (open ? 0.09 : 0.07) * v, music, "highpass", 7500, 0.7);
    const conga = (t, f, v = 1) => { osc("sine", f * 1.18, t, 0.26, 0.32 * v, music, 0.002, f, 0.03); nz(t, 0.012, 0.05 * v, music, "bandpass", 2600, 2); };
    const clave = (t) => osc("triangle", 2100, t, 0.045, 0.09, music, 0.001);
    const cowbell = (t, v = 1) => { const bp = ac.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 900; bp.Q.value = 2.5; bp.connect(music);
      osc("square", 562, t, 0.14, 0.06 * v, bp, 0.002); osc("square", 845, t, 0.14, 0.05 * v, bp, 0.002); };
    function guiro(t, dur) { const n = nz(t, dur, 0.06, music, "bandpass", 3600, 3, 0.01); const am = ac.createOscillator(), ag = ac.createGain(); am.type = "square"; am.frequency.value = 42; ag.gain.value = 0.5;
      am.connect(ag).connect(n.g.gain); am.start(t); am.stop(t + dur + 0.05); }
    function bass(t, m, dur) {
      const f = mtof(m), o = ac.createOscillator(), s = ac.createOscillator(), lp = ac.createBiquadFilter(), g = ac.createGain();
      o.type = "sawtooth"; o.frequency.value = f; s.type = "sine"; s.frequency.value = f;
      lp.type = "lowpass"; lp.Q.value = 6; lp.frequency.setValueAtTime(1300, t); lp.frequency.exponentialRampToValueAtTime(260, t + 0.18);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.3, t + 0.008); g.gain.setTargetAtTime(0.0001, t + dur * 0.8, 0.05);
      const sg = ac.createGain(); sg.gain.value = 0.9; o.connect(lp); s.connect(sg).connect(lp); lp.connect(g).connect(music);
      o.start(t); s.start(t); o.stop(t + dur + 0.3); s.stop(t + dur + 0.3);
    }
    function organ(t, notes, dur, v = 1) {   // drawbar-ish: fundamental + octave + fifth above, a little key click
      for (const m of notes) { const f = mtof(m); for (const [mul, lv] of [[1, 0.5], [2, 0.32], [3, 0.16], [4, 0.08]]) {
        const o = ac.createOscillator(), g = ac.createGain(); o.type = "sine"; o.frequency.value = f * mul;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(lv * v, t + 0.012); g.gain.setTargetAtTime(0.0001, t + dur, 0.05);
        o.connect(g).connect(organBus); o.start(t); o.stop(t + dur + 0.4); } }
      nz(t, 0.01, 0.03 * v, organBus, "highpass", 3000);
    }
    const CH = [[57, 60, 64, 67], [54, 57, 60, 64]];   // Am7, D9 (no root)
    const BASS = { 0: [33, 3], 3: [33, 1], 6: [40, 2], 8: [43, 1], 10: [45, 1], 11: [43, 1], 12: [40, 2], 14: [36, 2],
      16: [38, 3], 19: [38, 1], 22: [42, 2], 24: [45, 1], 26: [47, 1], 27: [45, 1], 28: [42, 2], 30: [40, 1], 31: [38, 1] };
    const LICK = [[69, 72, 74, 76, 79, 76, 74, 72], [76, 74, 72, 69, 67, 69, 72, 69]];
    function playStep(s, t, sd) {
      const i = s % 32, b = i % 16, bar = i < 16 ? 0 : 1, it = intensity;
      if (b === 0 || b === 10 || (it >= 1 && b === 14 && bar === 1)) kick(t);
      if (b === 4 || b === 12) snare(t);
      if (it >= 2 && (b === 7 || b === 15)) snare(t, 0.25);
      if (b % 2 === 0) hat(t, b === 14, b % 4 === 0 ? 1 : 0.7);
      else if (it >= 1) hat(t, false, 0.35);
      if (b === 6 || b === 7) conga(t, 330, 0.8); if (b === 14 || b === 15) conga(t, 220, 0.9); if (b === 3 && it >= 1) conga(t, 390, 0.5);
      if ((bar === 0 && (b === 4 || b === 8)) || (bar === 1 && (b === 0 || b === 6 || b === 12))) clave(t);
      if (it >= 1 && b % 4 === 0) guiro(t, b === 0 ? sd * 2.6 : sd * 1.1);
      if (it >= 2 && b % 4 === 0) cowbell(t, b === 0 ? 1 : 0.6);
      const bn = BASS[i]; if (bn) bass(t, bn[0], bn[1] * sd);
      if (b === 0) organ(t, CH[bar], sd * 3.5, 0.45);
      if (b === 6 || b === 14) organ(t, CH[bar], sd * 0.7, 0.8);
      if (it >= 3 && bars % 4 === 3) { const L = LICK[(bars >> 2) & 1]; if (b % 2 === 0) organ(t, [L[b >> 1]], sd * 1.6, 0.9); }
      if (i === 31) bars++;
    }
    function tick() {
      if (!ac || !playing) return;
      bpm += (wantBpm - bpm) * 0.08;
      const base = 60 / bpm / 4;
      while (nextT < ac.currentTime + 0.14) {
        const sd = base * (step % 2 === 0 ? 1.14 : 0.86);   // a little swing
        try { playStep(step, nextT, base); } catch (e) {}
        nextT += sd; step++;
      }
    }
    // --- effects
    const fx = {
      pssh(p = 1) { if (!ctx() || muted) return; const t = ac.currentTime;
        nz(t, 0.42, 0.33 * (0.5 + p * 0.5), sfx, "highpass", 2600, 0.8, 0.004, 900);
        osc("sine", 120, t + 0.035, 0.22, 0.85, sfx, 0.002, 42, 0.18); nz(t + 0.035, 0.06, 0.4, sfx, "lowpass", 500); },
      thunk(p = 1) { if (!ctx() || muted) return; const t = ac.currentTime; osc("sine", 95, t, 0.22, 0.7 * clamp(p, 0.3, 1), sfx, 0.002, 36, 0.2); nz(t, 0.08, 0.35 * p, sfx, "lowpass", 380); },
      ding() { if (!ctx() || muted) return; const t = ac.currentTime; for (const [m, v] of [[1, 0.22], [2.76, 0.08], [5.4, 0.04], [2, 0.06]]) osc("sine", 1760 * m, t, 1.1, v, sfx, 0.002); },
      oooh(big = 1) { if (!ctx() || muted) return; const t = ac.currentTime, d = 1.25 + big * 0.4;
        const f1 = ac.createBiquadFilter(), f2 = ac.createBiquadFilter(), g = ac.createGain(); f1.type = f2.type = "bandpass"; f1.frequency.value = 360; f2.frequency.value = 820; f1.Q.value = 5; f2.Q.value = 6;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.5 * big, t + 0.18); g.gain.setTargetAtTime(0.0001, t + d - 0.4, 0.18); f1.connect(g); f2.connect(g); g.connect(sfx);
        for (let i = 0; i < 9; i++) { const o = ac.createOscillator(), f = 150 + Math.random() * 140; o.type = "sawtooth"; o.frequency.setValueAtTime(f * 0.92, t);
          o.frequency.linearRampToValueAtTime(f * 1.12, t + d * 0.45); o.frequency.linearRampToValueAtTime(f * 0.88, t + d); o.connect(f1); o.connect(f2); o.start(t + Math.random() * 0.06); o.stop(t + d + 0.2); }
        nz(t, d, 0.04 * big, sfx, "bandpass", 1200, 0.6, 0.15); },
      cheer() { if (!ctx() || muted) return; const t = ac.currentTime; for (let i = 0; i < 16; i++) nz(t + Math.random() * 1.1, 0.03, 0.12, sfx, "bandpass", 1400 + Math.random() * 900, 1.2); fx.oooh(0.5); },
      skrrt() { if (!ctx() || muted) return; const t = ac.currentTime, d = 0.75;
        const n = nz(t, d, 0.42, sfx, "bandpass", 1600, 4, 0.01); const cv = new Float32Array(32); for (let i = 0; i < 32; i++) cv[i] = 900 + Math.random() * 1900;
        try { n.fl.frequency.cancelScheduledValues(t); n.fl.frequency.setValueCurveAtTime(cv, t, d); } catch (e) {}
        const o = osc("sawtooth", 1500, t, d, 0.045, sfx, 0.01); const c2 = new Float32Array(24); for (let i = 0; i < 24; i++) c2[i] = 1250 + Math.random() * 500;
        try { o.frequency.cancelScheduledValues(t); o.frequency.setValueCurveAtTime(c2, t, d); } catch (e) {} },
      bonk() { if (!ctx() || muted) return; const t = ac.currentTime; osc("square", 170, t, 0.12, 0.12, sfx, 0.002, 80); nz(t, 0.06, 0.3, sfx, "lowpass", 700); },
      coin() { if (!ctx() || muted) return; const t = ac.currentTime; osc("triangle", 1320, t, 0.07, 0.16, sfx, 0.002); osc("triangle", 1980, t + 0.06, 0.16, 0.14, sfx, 0.002); },
      whoosh() { if (!ctx() || muted) return; const t = ac.currentTime; nz(t, 0.7, 0.22, sfx, "bandpass", 400, 1.5, 0.2, 2200); },
      thwap() { if (!ctx() || muted) return; const t = ac.currentTime; nz(t, 0.09, 0.6, sfx, "lowpass", 1400); osc("sine", 220, t, 0.14, 0.5, sfx, 0.002, 70); },
      tier(n = 1) { if (!ctx() || muted) return; const t = ac.currentTime; [69, 72, 76, 81, 84].slice(0, 2 + n).forEach((m, i) => organ(t + i * 0.06, [m], 0.25, 1.2)); },
      click() { if (!ctx() || muted) return; const t = ac.currentTime; osc("triangle", 900, t, 0.04, 0.08, sfx, 0.001); },
      pumpStart() { if (!ctx() || muted || pump) return; const t = ac.currentTime, o = ac.createOscillator(), bp = ac.createBiquadFilter(), g = ac.createGain(), am = ac.createOscillator(), ag = ac.createGain();
        o.type = "sawtooth"; o.frequency.value = 55; bp.type = "bandpass"; bp.frequency.value = 380; bp.Q.value = 2; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.09, t + 0.05);
        am.type = "square"; am.frequency.value = 13; ag.gain.value = 0.05; am.connect(ag).connect(g.gain); o.connect(bp).connect(g).connect(sfx); o.start(t); am.start(t); pump = { o, g, am, bp }; },
      pumpLevel(c) { if (pump && ac) { pump.o.frequency.setTargetAtTime(55 + 120 * c, ac.currentTime, 0.05); pump.bp.frequency.setTargetAtTime(380 + 900 * c, ac.currentTime, 0.05); pump.am.frequency.setTargetAtTime(13 + 14 * c, ac.currentTime, 0.05); } },
      pumpStop() { if (!pump || !ac) { pump = null; return; } const t = ac.currentTime, p = pump; pump = null; try { p.g.gain.cancelScheduledValues(t); p.g.gain.setTargetAtTime(0.0001, t, 0.02); p.o.stop(t + 0.15); p.am.stop(t + 0.15); } catch (e) {} },
    };
    // voice lines: the phone's own voice if it has one (else the text pops are all there is)
    let lastSay = -Infinity, voices = []; // v49.26: simulation milliseconds, including across restarts
    const hasVoice = () => "speechSynthesis" in root && typeof root.SpeechSynthesisUtterance === "function";
    const pickV = () => { try { voices = speechSynthesis.getVoices() || []; } catch (e) { voices = []; } };
    if (hasVoice()) { pickV(); try { speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", pickV); } catch (e) {} }
    function say(text, lang = "en-US", o = {}) {
      if (muted || !hasVoice() || (!o.force && speechSynthesis.speaking)) return false; const now = clock(); // v49.26: let the current line finish without queuing chatter
 if (!o.force && now - lastSay < (o.gap == null ? 1800 : o.gap)) return false; lastSay = now;
      try { const u = new SpeechSynthesisUtterance(text); u.lang = lang; const v = voices.find((x) => x.lang && x.lang.replace("_", "-").toLowerCase().startsWith(lang.toLowerCase())) || voices.find((x) => x.lang && x.lang.slice(0, 2) === lang.slice(0, 2));
        if (v) u.voice = v; u.pitch = o.pitch || 1; u.rate = o.rate || 1; u.volume = o.volume == null ? 0.9 : o.volume; if (o.force) speechSynthesis.cancel(); speechSynthesis.speak(u); return true; } catch (e) { return false; }
    }
    return {
      fx, say, synth: { osc, nz, get on() { return !muted && !!ctx(); }, get ac() { return ac; }, get out() { return sfx; } },   // a stage adds its own sounds (lowrider-sa.js: honks, clops)
      unlock() { ctx(); },
      get ready() { return !!ac; }, get state() { return ac ? ac.state : "none"; }, get playing() { return playing; },
      setMuted(m) { muted = !!m; if (m) { fx.pumpStop(); try { hasVoice() && speechSynthesis.cancel(); } catch (e) {} } if (ac) master.gain.setTargetAtTime(m ? 0 : 0.85, ac.currentTime, 0.03); if (m) this.stopMusic(); },
      startMusic() { if (muted || !ctx()) return; if (playing) return; playing = true; step = 0; bars = 0; nextT = ac.currentTime + 0.06; clearInterval(timer); timer = setInterval(tick, 25); tick(); },
      stopMusic() { playing = false; clearInterval(timer); timer = null; },
      intensity(n) { intensity = n; },
      muffle(on) { if (!ac) return; musicLP.frequency.setTargetAtTime(on ? 520 : 18000, ac.currentTime, on ? 0.15 : 0.3); },
      tempo(f) { wantBpm = 94 * f; },
      close() { this.setMuted(true); this.stopMusic(); fx.pumpStop(); if (ac) try { const closing = ac.close(); if (closing && closing.catch) closing.catch(() => {}); } catch (e) {} ac = null; if (hasVoice() && speechSynthesis.removeEventListener) try { speechSynthesis.removeEventListener("voiceschanged", pickV); } catch (e) {} },
    };
  }

  // ---------------------------------------------------------------- art helpers (all vector, drawn on the canvas)
  function rr(g, x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function lg(g, x0, y0, x1, y1, stops) { const G = g.createLinearGradient(x0, y0, x1, y1); for (const [o, c] of stops) G.addColorStop(o, c); return G; }
  function rg(g, x, y, r0, r1, stops) { const G = g.createRadialGradient(x, y, r0, x, y, r1); for (const [o, c] of stops) G.addColorStop(o, c); return G; }
  const chromeV = (g, y0, y1) => lg(g, 0, y0, 0, y1, [[0, "#ffffff"], [0.35, "#c3cad3"], [0.5, "#4b525c"], [0.62, "#9aa3ad"], [0.85, "#f4f7fa"], [1, "#8d96a1"]]);
  function fitText(g, text, maxW, size, weight = "900", fam = FONT) { let s = size; g.font = `${weight} ${s}px ${fam}`; while (s > 6 && g.measureText(text).width > maxW) { s -= 0.5; g.font = `${weight} ${s}px ${fam}`; } return s; }
  function outlined(g, text, x, y, fill, stroke, lw) { g.lineJoin = "round"; g.miterLimit = 2; if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.strokeText(text, x, y); } g.fillStyle = fill; g.fillText(text, x, y); }
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }

  // ---------------------------------------------------------------- The '64 (car coords: x 0 = rear bumper … 200 = front, y 0 = the ground at rest, up is negative)
  const R64 = { rear: 42, front: 160, r: 14, arch: 18.5 };
  function bodyPath(g) {
    g.beginPath(); g.moveTo(4, -13);
    g.quadraticCurveTo(-1.5, -19, 0.5, -29); g.lineTo(2.5, -36); g.quadraticCurveTo(4, -40.5, 11, -40.8);
    g.lineTo(52, -41.4); g.lineTo(146, -42.2); g.lineTo(184, -41.2); g.quadraticCurveTo(196.5, -40.6, 198.4, -35.5);
    g.lineTo(199.6, -20); g.quadraticCurveTo(199.8, -13.5, 194.5, -13);
    g.lineTo(180, -13); g.arc(R64.front, -14, R64.arch, -0.05, Math.PI + 0.05, true);
    g.lineTo(138.5, -10.2); g.lineTo(64.5, -10.2); g.lineTo(60.4, -13.2);
    g.arc(R64.rear, -14, R64.arch, -0.05, Math.PI + 0.05, true); g.lineTo(4, -13); g.closePath();
  }
  function openingPath(g) { g.beginPath(); g.moveTo(63, -41.6); g.lineTo(77.5, -57); g.quadraticCurveTo(80, -59.6, 84, -59.6); g.lineTo(126, -59.8); g.lineTo(139.5, -42.4); g.closePath(); }
  function roofPath(g) { g.beginPath(); g.moveTo(49, -41.5); g.quadraticCurveTo(59, -55, 71.5, -62); g.quadraticCurveTo(80, -66.4, 93, -66.4); g.lineTo(119, -65.9);
    g.quadraticCurveTo(127.5, -65.4, 131, -61.2); g.lineTo(126.5, -59.6); g.lineTo(84, -59.6); g.quadraticCurveTo(80, -59.3, 77, -56.4); g.lineTo(63.5, -41.5); g.closePath(); }
  const FLAKES = (() => { const r = rng(64); return Array.from({ length: 46 }, () => ({ x: 6 + r() * 188, y: -40 + r() * 28, p: r() * 6.28, s: 0.35 + r() * 0.5 })); })();
  // wire wheels: chrome, or the Primer's warm bronze (every stop sits at hue ≈ 20-23°, so no blend of it ever reads yellow)
  const WHEEL_CHROME = { dish: [[0, "#ffffff"], [0.45, "#aeb6c0"], [0.75, "#5d6570"], [0.9, "#e9eef4"], [1, "#7b848f"]], spokeL: "rgba(255,255,255,.95)", spokeD: "rgba(70,78,90,.85)", lip: "rgba(255,255,255,.7)" };
  const WHEEL_BRONZE = { dish: [[0, "#f6d2bc"], [0.4, "#c47a4e"], [0.72, "#7a3f22"], [0.9, "#e6a57e"], [1, "#8f4f2e"]], spokeL: "rgba(233,176,140,.95)", spokeD: "rgba(110,58,32,.9)", lip: "rgba(246,210,188,.8)",
    hub: [[0, "#f6d2bc"], [0.45, "#b8693e"], [0.55, "#6e3a20"], [1, "#e6a57e"]] };
  function drawWheel(g, cx, cy, rot, o = {}) {
    const R = R64.r;
    g.save(); g.translate(cx, cy);
    g.fillStyle = rg(g, 0, 0, R * 0.55, R, [[0, "#3a3a40"], [0.7, "#141418"], [1, "#050507"]]); g.beginPath(); g.arc(0, 0, R, 0, 6.2832); g.fill();
    g.strokeStyle = "rgba(255,255,255,.08)"; g.lineWidth = 0.6; g.beginPath(); g.arc(0, 0, R - 0.8, 3.6, 5.6); g.stroke();
    g.fillStyle = "#f5f4ef"; g.beginPath(); g.arc(0, 0, 11.7, 0, 6.2832); g.arc(0, 0, 8.8, 0, 6.2832, true); g.fill();   // whitewall
    g.strokeStyle = "rgba(0,0,0,.25)"; g.lineWidth = 0.5; g.beginPath(); g.arc(0, 0, 10.2, 0, 6.2832); g.stroke();
    const W = o.style === "bronze" ? WHEEL_BRONZE : WHEEL_CHROME;
    g.fillStyle = rg(g, -1.5, -2, 0.5, 8.9, W.dish); g.beginPath(); g.arc(0, 0, 8.9, 0, 6.2832); g.fill();
    g.rotate(rot);
    g.lineWidth = 0.32;
    for (let k = 0; k < 2; k++) {   // cross-laced wire spokes
      g.strokeStyle = k ? W.spokeD : W.spokeL;
      g.beginPath();
      for (let i = 0; i < 18; i++) { const a = (i / 18) * 6.2832 + k * 0.17; g.moveTo(Math.cos(a) * 2.1, Math.sin(a) * 2.1); g.lineTo(Math.cos(a + (k ? -0.62 : 0.62)) * 8.3, Math.sin(a + (k ? -0.62 : 0.62)) * 8.3); }
      g.stroke();
    }
    g.strokeStyle = W.lip; g.lineWidth = 0.6; g.beginPath(); g.arc(0, 0, 8.3, 0, 6.2832); g.stroke();
    g.fillStyle = W.hub ? lg(g, 0, -3, 0, 3, W.hub) : chromeV(g, -3, 3); g.beginPath(); g.arc(0, 0, 2.6, 0, 6.2832); g.fill();   // knock-off spinner
    g.beginPath(); g.ellipse(0, -3.3, 1.1, 2.4, 0, 0, 6.2832); g.ellipse(0, 3.3, 1.1, 2.4, 0, 0, 6.2832); g.fill();
    g.fillStyle = "#3d434c"; g.beginPath(); g.arc(0, 0, 0.9, 0, 6.2832); g.fill();
    g.restore();
    if (o.blur) { g.save(); g.globalAlpha = Math.min(0.35, o.blur); g.strokeStyle = "#dfe5ec"; g.lineWidth = 3.5; g.beginPath(); g.arc(cx, cy, 5.4, 0, 6.2832); g.stroke(); g.restore(); }
  }
  // the interior seen through the open (pillarless) windows: the far door's tuck-and-roll, the bench seats, the driver
  function drawInterior(g, P, o) {
    g.save(); openingPath(g); g.clip();
    g.fillStyle = lg(g, 0, -60, 0, -42, [[0, "#3b2a5a"], [0.45, "#6b3a74"], [1, "#2a1530"]]); g.fillRect(60, -62, 82, 22);   // the far window: dusk outside
    g.fillStyle = "rgba(255,255,255,.12)"; g.beginPath(); g.moveTo(90, -60); g.lineTo(98, -60); g.lineTo(84, -44); g.lineTo(76, -44); g.fill();
    const door = -49.5;
    g.fillStyle = P.seat; g.fillRect(60, door, 82, 10);
    for (let x = 63; x < 141; x += 3.2) { g.fillStyle = "rgba(0,0,0,.18)"; g.fillRect(x, door + 0.5, 0.7, 9); g.fillStyle = "rgba(255,255,255,.35)"; g.fillRect(x + 1.1, door + 0.5, 0.6, 9); }
    g.fillStyle = P.pipe; g.fillRect(60, door - 1.2, 82, 1.4);
    const seat = (x0, x1, top) => {
      g.fillStyle = lg(g, x0, 0, x1, 0, [[0, shade(P.seat, -0.25)], [0.5, P.seat], [1, shade(P.seat, -0.15)]]);
      g.beginPath(); g.moveTo(x0, -41); g.lineTo(x0 + 1, top + 3); g.quadraticCurveTo(x0 + 2, top, (x0 + x1) / 2, top); g.quadraticCurveTo(x1 - 1, top, x1, top + 3); g.lineTo(x1 + 1, -41); g.closePath(); g.fill();
      g.strokeStyle = "rgba(0,0,0,.2)"; g.lineWidth = 0.45; g.beginPath(); for (let x = x0 + 2.2; x < x1; x += 2.2) { g.moveTo(x, top + 1.6); g.lineTo(x + 0.4, -41.5); } g.stroke();
      g.strokeStyle = P.pipe; g.lineWidth = 0.8; g.beginPath(); g.moveTo(x0 + 1, top + 3); g.quadraticCurveTo(x0 + 2, top, (x0 + x1) / 2, top); g.quadraticCurveTo(x1 - 1, top, x1, top + 3); g.stroke();
    };
    seat(70, 82, -52.5);
    if (o.driver !== false) {   // the driver: leaned back, shades on, one arm on the door
      const bob = o.bob || 0;
      g.save(); g.translate(0, bob);
      g.fillStyle = "#151515"; g.beginPath(); g.moveTo(108, -42); g.quadraticCurveTo(110, -54, 115.5, -55.5); g.lineTo(120, -54); g.quadraticCurveTo(121, -47, 123, -42); g.fill();
      g.fillStyle = "#ffffff"; g.globalAlpha = 0.9; g.fillRect(113, -54.6, 1.2, 12); g.globalAlpha = 1;
      g.fillStyle = "#8a5a3c"; g.beginPath(); g.arc(119.2, -58.6, 4.1, 0, 6.2832); g.fill();
      g.fillStyle = "#111"; g.beginPath(); g.ellipse(118.2, -61.6, 4.6, 2.2, -0.1, 3.1, 6.3); g.fill(); g.fillRect(118, -62.2, 6.6, 1.3);   // cap, brim forward
      g.fillStyle = "#050505"; rr(g, 119.4, -59.6, 4.2, 1.6, 0.6); g.fill();
      g.fillStyle = "rgba(255,255,255,.55)"; g.fillRect(121.6, -59.3, 1.3, 0.5);
      g.restore();
    }
    seat(104, 116.5, -54);
    g.strokeStyle = chromeV(g, -57, -44); g.lineWidth = 1.1; g.beginPath(); g.ellipse(129.5, -50.5, 1.8, 6.2, 0.18, 0, 6.2832); g.stroke();   // chain steering wheel
    g.strokeStyle = "#2a2a2a"; g.lineWidth = 1; g.beginPath(); g.moveTo(130, -50.5); g.lineTo(136, -44); g.stroke();
    g.restore();
    if (o.driver !== false) { g.fillStyle = "#151515"; g.beginPath(); g.moveTo(118, -43.6); g.quadraticCurveTo(124, -46, 128, -43.2); g.lineTo(127.5, -41.5); g.lineTo(118.5, -41.5); g.fill(); g.fillStyle = "#8a5a3c"; g.beginPath(); g.arc(128.6, -42.6, 1.4, 0, 6.2832); g.fill(); }
  }
  function shade(hex, f) { const n = parseInt(hex.slice(1), 16); let r = n >> 16, gg = (n >> 8) & 255, b = n & 255;
    if (f < 0) { r *= 1 + f; gg *= 1 + f; b *= 1 + f; } else { r += (255 - r) * f; gg += (255 - gg) * f; b += (255 - b) * f; }
    return "#" + [r, gg, b].map((v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, "0")).join(""); }
  const paintGrad = (g, P, y0, y1) => lg(g, 0, y0, 0, y1, [[0, P.hi], [0.1, P.mid], [0.34, P.base], [0.43, P.deep], [0.48, P.mid], [0.7, P.base], [1, P.deep]]);
  // the Primer's patchwork (from Goonie's key art): grey primer, a faded red door, turquoise + cream patches on the rear quarter.
  // (cream is kept pale and greyish: no yellow)
  const PATCH = { red: ["#c4544a", "#9e3a34", "#6e2622"], turq: ["#7fc4c4", "#4f9a9e", "#2d6a70"], cream: ["#e2d6cb", "#c9b9aa", "#a8968a"] };
  function patchwork(g, P) {
    const fill = (c, path) => { g.fillStyle = lg(g, 0, -42, 0, -10, [[0, c[0]], [0.45, c[1]], [1, c[2]]]); g.beginPath(); path(); g.fill(); };
    fill(PATCH.red, () => { g.moveTo(65, -42); g.lineTo(133.5, -42); g.quadraticCurveTo(136, -26, 134.5, -10); g.lineTo(65.5, -10); g.quadraticCurveTo(63.5, -26, 65, -42); });
    fill(PATCH.turq, () => { g.moveTo(22, -41); g.lineTo(64.6, -41.5); g.quadraticCurveTo(63.2, -26, 65.2, -10); g.lineTo(30, -10); g.quadraticCurveTo(24, -24, 22, -41); });
    fill(PATCH.cream, () => { g.moveTo(30, -27); g.quadraticCurveTo(44, -30, 63.5, -27.5); g.lineTo(64.8, -12); g.lineTo(46, -12); g.quadraticCurveTo(34, -16, 30, -27); });
    fill(PATCH.cream, () => { g.moveTo(84, -40); g.quadraticCurveTo(96, -42, 104, -38); g.lineTo(100, -33); g.quadraticCurveTo(90, -31, 84, -40); });   // a scuffed spot on the door
    g.fillStyle = "rgba(255,255,255,.08)"; g.fillRect(65, -41, 70, 9);
  }
  const RUST = (() => { const r = rng(1964); return Array.from({ length: 34 }, () => ({ x: 4 + r() * 192, y: -40 + r() * 28, w: 0.7 + r() * 2.4, h: 0.6 + r() * 1.6, d: r() })); })();
  function rust(g, k) {   // rust spots + a streak over each wheel arch (hue ≈ 15-20°, never yellow)
    for (let i = 0; i < RUST.length * k; i++) { const s = RUST[i]; g.fillStyle = s.d < 0.5 ? "rgba(122,52,26,.85)" : "rgba(166,78,40,.75)"; g.beginPath(); g.ellipse(s.x, s.y, s.w, s.h, 0, 0, 6.2832); g.fill(); }
    g.strokeStyle = "rgba(122,52,26,.55)"; g.lineWidth = 1.6; for (const cx of [R64.rear, R64.front]) { g.beginPath(); g.arc(cx, -14, R64.arch + 1.4, Math.PI + 0.3, -0.3); g.stroke(); }
  }
  // the body (in car coords). o: { t, lights, sparkle, driver, bob, brake }
  function drawBody64(g, P, o) {
    const t = o.t || 0;
    // wheel wells (behind the wheels)
    g.fillStyle = "#07060a"; g.beginPath(); g.arc(R64.rear, -14, R64.arch - 0.5, Math.PI, 0); g.arc(R64.front, -14, R64.arch - 0.5, Math.PI, 0); g.fill();
    if (o.wheels) o.wheels();
    // interior, roof, glass
    drawInterior(g, P, o);
    roofPath(g); g.fillStyle = lg(g, 0, -67, 0, -41, [[0, P.hi], [0.25, P.mid], [0.7, P.base], [1, P.deep]]); g.fill();
    g.save(); roofPath(g); g.clip(); g.fillStyle = "rgba(255,255,255,.45)"; g.beginPath(); g.ellipse(100, -65.5, 26, 1.3, 0, 0, 6.2832); g.fill(); g.restore();
    g.strokeStyle = chromeV(g, -61, -58); g.lineWidth = 0.9; g.beginPath(); g.moveTo(77.5, -57); g.quadraticCurveTo(80, -59.6, 84, -59.6); g.lineTo(126.5, -59.7); g.stroke();
    g.fillStyle = lg(g, 128, -61, 144, -42, [[0, "rgba(160,235,240,.55)"], [0.5, "rgba(60,40,90,.6)"], [1, "rgba(200,250,255,.5)"]]);
    g.beginPath(); g.moveTo(126.5, -59.7); g.lineTo(131, -61.2); g.lineTo(146.5, -42.3); g.lineTo(139.5, -42.4); g.closePath(); g.fill();
    g.strokeStyle = "#e9eef3"; g.lineWidth = 0.9; g.beginPath(); g.moveTo(131, -61.2); g.lineTo(146.5, -42.3); g.stroke();
    // the body: candy paint (sky reflection on top, a sharp horizon line, the dark lower side)
    const matte = !!(o.car && o.car.matte);
    bodyPath(g);
    g.fillStyle = paintGrad(g, P, -42, -10); g.fill();
    g.save(); bodyPath(g); g.clip();
    if (P.patch) patchwork(g, P);
    g.fillStyle = lg(g, 0, 0, 200, 0, [[0, "rgba(0,0,0,.35)"], [0.12, "rgba(0,0,0,0)"], [0.85, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,.3)"]]); g.fillRect(-5, -45, 210, 40);
    g.globalAlpha = matte ? 0.35 : 1;
    g.fillStyle = lg(g, 0, -41, 0, -34, [[0, "rgba(255,255,255,.75)"], [1, "rgba(255,255,255,0)"]]); g.beginPath(); g.ellipse(102, -38.4, 86, 2.6, 0, 0, 6.2832); g.fill();
    g.fillStyle = "rgba(255,255,255,.22)"; g.beginPath(); g.moveTo(30, -41); g.lineTo(44, -41); g.lineTo(30, -12); g.lineTo(20, -12); g.fill(); g.beginPath(); g.moveTo(150, -42); g.lineTo(156, -42); g.lineTo(146, -12); g.lineTo(142, -12); g.fill();
    g.globalAlpha = 1;
    if (P.pearl) { g.globalAlpha = 0.28; g.fillStyle = lg(g, 0, -42, 200, -10, [[0, "#ff9fd0"], [(Math.sin(t * 0.8) + 1) / 4 + 0.25, "#a0fbff"], [1, "#d9b8ff"]]); g.fillRect(-5, -45, 210, 40); g.globalAlpha = 1; }
    if (!matte) for (const f of FLAKES) { const a = 0.5 + 0.5 * Math.sin(t * 3 + f.p); if (a < 0.6) continue; g.fillStyle = hexA(P.flake === "#ffffff" ? "#ffffff" : P.flake, (a - 0.6) * 2.2); g.fillRect(f.x, f.y, f.s, f.s); }
    if (matte) rust(g, P.patch ? 1 : 0.45);
    g.strokeStyle = "rgba(0,0,0,.35)"; g.lineWidth = 0.6;
    g.beginPath(); g.moveTo(65, -41); g.quadraticCurveTo(63.5, -26, 65.5, -10.5); g.moveTo(133.5, -42); g.quadraticCurveTo(136, -26, 134.5, -10.5); g.stroke();   // door cuts
    g.strokeStyle = "rgba(255,255,255,.35)"; g.lineWidth = 0.5; g.beginPath(); g.moveTo(6, -31.5); g.lineTo(196, -32.5); g.stroke();
    g.restore();
    g.strokeStyle = "rgba(0,0,0,.45)"; g.lineWidth = 0.8; g.beginPath(); g.arc(R64.rear, -14, R64.arch, Math.PI + 0.05, -0.05); g.stroke(); g.beginPath(); g.arc(R64.front, -14, R64.arch, Math.PI + 0.05, -0.05); g.stroke();
    // chrome: the side spear, the beltline, rocker, door handle, bumpers
    g.fillStyle = chromeV(g, -30.2, -27.6);
    g.beginPath(); g.moveTo(14, -29.2); g.lineTo(186, -29.8); g.lineTo(192, -28.9); g.lineTo(186, -28); g.lineTo(18, -27.7); g.closePath(); g.fill();
    g.fillStyle = chromeV(g, -42.6, -40.9); g.fillRect(50, -42.4, 96, 1.3);
    g.fillStyle = chromeV(g, -13.6, -10.4); g.fillRect(64, -13.2, 75, 2.6);
    g.fillStyle = chromeV(g, -38, -35.6); rr(g, 70, -37.6, 7, 1.8, 0.8); g.fill();
    g.fillStyle = chromeV(g, -25, -14); rr(g, -4.5, -24.5, 15, 10.5, 4.5); g.fill(); rr(g, 186, -25, 18.5, 10.5, 4.5); g.fill();
    g.fillStyle = "rgba(0,0,0,.35)"; g.fillRect(-4, -19.6, 14, 0.6); g.fillRect(187, -20, 17, 0.6);
    g.fillStyle = "#1a1a1f"; g.fillRect(197.2, -33.5, 2.6, 8);   // grille + headlight
    g.fillStyle = chromeV(g, -34, -24); for (let y = -33; y < -25.5; y += 2) g.fillRect(197, y, 3, 0.7);
    g.fillStyle = chromeV(g, -36, -28); g.beginPath(); g.arc(196.6, -32, 3.2, -1.6, 1.6); g.fill();
    g.fillStyle = o.lights ? "#ffffff" : "#d8e6ef"; g.beginPath(); g.arc(197, -32, 2.1, -1.6, 1.6); g.fill();
    g.fillStyle = o.brake ? "#ff2a3a" : "#c3102a"; rr(g, 0.6, -35.5, 3.2, 5, 1); g.fill();
    // the antenna with a little pink flag
    const sw = Math.sin(t * 7) * 2.5 + (o.lean || 0) * 10;
    g.strokeStyle = "#cfd5dc"; g.lineWidth = 0.5; g.beginPath(); g.moveTo(16, -40.5); g.quadraticCurveTo(14 + sw * 0.4, -62, 8 + sw, -84); g.stroke();
    g.fillStyle = COL.pink; g.beginPath(); g.moveTo(8 + sw, -84); g.lineTo(1 + sw * 1.3, -81 + Math.sin(t * 11)); g.lineTo(8.3 + sw, -79); g.fill();
  }
  // El Jefe '76: a long, square '70s luxury sedan (made up: no real make or badge) on the same wheelbase. Formal roof with a
  // vinyl top + a landau bar, an opera window, big bumpers, a waterfall grille and a stand-up hood ornament (a plain diamond).
  function body76Path(g) {
    g.beginPath(); g.moveTo(0.5, -13); g.lineTo(-1.5, -35); g.quadraticCurveTo(-1, -40.5, 4, -40.8); g.lineTo(60, -41.4); g.lineTo(146, -41.8); g.lineTo(197, -40.2);
    g.quadraticCurveTo(202, -39.6, 202.4, -35); g.lineTo(202.6, -16); g.quadraticCurveTo(202.4, -12.6, 198, -12.6); g.lineTo(180, -13); g.arc(R64.front, -14, R64.arch, -0.05, Math.PI + 0.05, true);
    g.lineTo(138.5, -10.4); g.lineTo(64.5, -10.4); g.lineTo(60.4, -13.2); g.arc(R64.rear, -14, R64.arch, -0.05, Math.PI + 0.05, true); g.lineTo(0.5, -13); g.closePath();
  }
  function drawBody76(g, P, o) {
    const t = o.t || 0;
    g.fillStyle = "#07060a"; g.beginPath(); g.arc(R64.rear, -14, R64.arch - 0.5, Math.PI, 0); g.arc(R64.front, -14, R64.arch - 0.5, Math.PI, 0); g.fill();
    if (o.wheels) o.wheels();
    // greenhouse: formal roof, windshield, glass
    const roof = () => { g.beginPath(); g.moveTo(56, -41.5); g.lineTo(64, -62.5); g.quadraticCurveTo(65, -64.6, 68, -64.6); g.lineTo(121, -64.6); g.quadraticCurveTo(124, -64.4, 126, -62); g.lineTo(143, -41.8); g.closePath(); };
    roof(); g.fillStyle = paintGrad(g, P, -65, -41); g.fill();
    g.fillStyle = lg(g, 0, -61, 0, -43, [[0, "rgba(150,220,235,.7)"], [0.5, "rgba(40,30,70,.85)"], [1, "rgba(170,230,245,.55)"]]);
    g.beginPath(); g.moveTo(103, -43); g.lineTo(103, -60.5); g.lineTo(122.5, -60.5); g.lineTo(137, -43); g.closePath(); g.fill();   // front door glass
    g.beginPath(); g.moveTo(84, -43); g.lineTo(84, -60.5); g.lineTo(100, -60.5); g.lineTo(100, -43); g.closePath(); g.fill();   // rear door glass
    if (o.driver !== false) { const b = o.bob || 0; g.fillStyle = "#8a5a3c"; g.beginPath(); g.arc(117, -53.5 + b, 4, 0, 6.2832); g.fill(); g.fillStyle = "#111"; g.beginPath(); g.ellipse(116, -56.6 + b, 4.6, 2.2, -0.1, 3.1, 6.3); g.fill(); g.fillRect(116, -57.2 + b, 6.6, 1.3);
      g.fillStyle = "#050505"; rr(g, 117.2, -54.6 + b, 4.2, 1.6, 0.6); g.fill(); g.fillStyle = "#151515"; g.fillRect(112, -49.5 + b, 10, 7); }
    // the vinyl top over the back half, the landau bar, the opera window
    g.save(); roof(); g.clip(); g.fillStyle = P.roof || shade(P.deep, 0.15); g.fillRect(54, -66, 47, 26);
    g.fillStyle = "rgba(0,0,0,.12)"; for (let x = 58; x < 100; x += 3) g.fillRect(x, -66, 0.5, 25); g.restore();
    g.fillStyle = "#16121e"; g.beginPath(); g.ellipse(74, -53, 4.2, 3.4, 0, 0, 6.2832); g.fill(); g.strokeStyle = chromeV(g, -57, -49); g.lineWidth = 0.8; g.stroke();
    g.strokeStyle = chromeV(g, -50, -45); g.lineWidth = 1.1; g.beginPath(); g.moveTo(60, -46); g.quadraticCurveTo(66, -50, 70, -47); g.stroke();
    g.strokeStyle = chromeV(g, -66, -60); g.lineWidth = 0.8; g.beginPath(); g.moveTo(64, -62.5); g.quadraticCurveTo(65, -64.6, 68, -64.6); g.lineTo(121, -64.6); g.quadraticCurveTo(124, -64.4, 126, -62); g.stroke();
    g.strokeStyle = "#e9eef3"; g.lineWidth = 0.9; g.beginPath(); g.moveTo(126, -62); g.lineTo(143, -41.8); g.stroke();
    g.fillStyle = "#e9eef3"; g.fillRect(101, -61, 2, 18.5); g.fillRect(82, -61, 2, 18.5);
    // the body slab
    body76Path(g); g.fillStyle = paintGrad(g, P, -42, -10); g.fill();
    g.save(); body76Path(g); g.clip();
    g.fillStyle = lg(g, 0, 0, 204, 0, [[0, "rgba(0,0,0,.35)"], [0.12, "rgba(0,0,0,0)"], [0.85, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,.3)"]]); g.fillRect(-5, -45, 212, 40);
    g.fillStyle = lg(g, 0, -41, 0, -35, [[0, "rgba(255,255,255,.7)"], [1, "rgba(255,255,255,0)"]]); g.fillRect(0, -41.5, 204, 5);
    for (const f of FLAKES) { const a = 0.5 + 0.5 * Math.sin(t * 3 + f.p); if (a < 0.6) continue; g.fillStyle = hexA(P.flake, (a - 0.6) * 2.2); g.fillRect(f.x, f.y, f.s, f.s); }
    g.strokeStyle = "rgba(0,0,0,.35)"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(82, -41.5); g.lineTo(82.5, -10.6); g.moveTo(102.5, -41.6); g.lineTo(103, -10.6); g.moveTo(138, -41.8); g.lineTo(138.5, -10.6); g.stroke();
    g.strokeStyle = P.pipe; g.lineWidth = 0.7; g.beginPath(); g.moveTo(4, -36.5); g.lineTo(198, -37); g.stroke();   // pinstripe
    g.restore();
    // chrome: side molding, rocker, handles, the big bumpers, waterfall grille, square headlights, vertical taillight, hood ornament
    g.fillStyle = chromeV(g, -26.5, -24.5); g.fillRect(2, -26.2, 199, 1.8);
    g.fillStyle = chromeV(g, -12.8, -10.4); g.fillRect(64, -12.6, 75, 2.2);
    g.fillStyle = chromeV(g, -36, -34); rr(g, 88, -35.6, 6, 1.6, 0.7); g.fill(); rr(g, 106, -35.6, 6, 1.6, 0.7); g.fill();
    g.fillStyle = chromeV(g, -24, -12); rr(g, -5, -23.5, 16, 11.5, 3); g.fill(); rr(g, 190, -24, 17, 11.5, 3); g.fill();
    g.fillStyle = "#15121c"; g.fillRect(200.6, -38, 2.4, 12); g.fillStyle = chromeV(g, -38, -26); for (let y = -37.5; y < -26; y += 1.6) g.fillRect(200.4, y, 2.8, 0.6);
    g.fillStyle = o.lights ? "#ffffff" : "#d8e6ef"; g.fillRect(199.6, -36.5, 1.8, 4);
    g.fillStyle = o.brake ? "#ff2a3a" : "#c3102a"; g.fillRect(-1.2, -37, 2.6, 11);
    g.strokeStyle = chromeV(g, -46, -40); g.lineWidth = 0.7; g.beginPath(); g.moveTo(190, -40.5); g.lineTo(190.5, -44); g.stroke();
    g.fillStyle = chromeV(g, -48, -44); g.beginPath(); g.moveTo(190.6, -48); g.lineTo(192.2, -45.8); g.lineTo(190.6, -43.6); g.lineTo(189, -45.8); g.closePath(); g.fill();
    g.strokeStyle = "rgba(0,0,0,.45)"; g.lineWidth = 0.8; for (const cx of [R64.rear, R64.front]) { g.beginPath(); g.arc(cx, -14, R64.arch, Math.PI + 0.05, -0.05); g.stroke(); }
    const sw = Math.sin(t * 7) * 2.5 + (o.lean || 0) * 10;
    g.strokeStyle = "#cfd5dc"; g.lineWidth = 0.5; g.beginPath(); g.moveTo(10, -40.8); g.quadraticCurveTo(8 + sw * 0.4, -62, 2 + sw, -84); g.stroke();
    g.fillStyle = COL.pink; g.beginPath(); g.moveTo(2 + sw, -84); g.lineTo(-5 + sw * 1.3, -81 + Math.sin(t * 11)); g.lineTo(2.3 + sw, -79); g.fill();
  }
  function drawGlow(g, x, y, r, col, a) { g.save(); g.globalCompositeOperation = "lighter"; g.globalAlpha = a; g.fillStyle = rg(g, x, y, 0, r, [[0, col], [1, "rgba(0,0,0,0)"]]); g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.fill(); g.restore(); }
  // the whole car in world space. c: { x (rear bumper), gy (ground), y (air), sR, sF, ang, rot, t, P, lights, scrape }
  function drawCar(g, c) {
    const rwx = c.x + R64.rear, rwy = c.gy - c.y - R64.r;
    const base = Math.atan2(c.sF - c.sR, R64.front - R64.rear), ang = base + c.ang;
    const ca = Math.cos(c.ang), sa = Math.sin(c.ang);
    const fwx = rwx + (R64.front - R64.rear) * ca, fwy = Math.min(c.gy - R64.r, rwy - (R64.front - R64.rear) * sa + (c.y > 0 ? 0 : 0));
    // shadow
    const air = clamp(c.y / 320, 0, 1);
    g.fillStyle = `rgba(0,0,0,${0.5 - air * 0.3})`; g.beginPath(); g.ellipse(c.x + 100, c.gy + 1.5, 104 - air * 30, 6 - air * 2, 0, 0, 6.2832); g.fill();
    if (c.lights) {   // headlight beam on the road
      g.save(); g.globalCompositeOperation = "lighter"; g.globalAlpha = 0.18;
      g.fillStyle = lg(g, fwx + 40, 0, fwx + 260, 0, [[0, "#e8f7ff"], [1, "rgba(0,0,0,0)"]]);
      g.beginPath(); g.moveTo(fwx + 36, rwy - 18 - c.sF); g.lineTo(fwx + 300, c.gy - 4); g.lineTo(fwx + 300, c.gy + 18); g.lineTo(fwx + 36, c.gy + 2); g.fill(); g.restore();
    }
    g.save();
    g.translate(rwx, rwy - c.sR); g.rotate(-ang); g.translate(-R64.rear, R64.r);
    const wheels = () => {
      g.save(); g.translate(R64.rear, -R64.r); g.rotate(ang); g.translate(-rwx, -(rwy - c.sR));
      const ws = { blur: c.blur, style: c.car ? c.car.wheel : "chrome" }; drawWheel(g, rwx, rwy, c.rot, ws); drawWheel(g, fwx, fwy, c.rot, ws);
      g.restore();
    };
    (c.car && c.car.body === "76" ? drawBody76 : drawBody64)(g, c.P, { t: c.t, lights: c.lights, wheels, driver: c.driver, bob: c.bob, brake: c.brake, lean: c.ang, car: c.car });
    g.restore();
    if (c.lights) { const hx = fwx + 37 * Math.cos(ang), hy = rwy - c.sR - 18 - (R64.front - R64.rear + 37) * Math.sin(ang); drawGlow(g, hx, hy, 16, "#dff6ff", 0.55); drawGlow(g, c.x + 1, rwy - c.sR - 20 + 0 * sa, 10, "#ff2a3a", c.brake ? 0.7 : 0.4); }
    return { rwx, rwy, fwx, fwy, ang, frontX: c.x + 200 * Math.cos(ang), frontY: rwy - c.sR - (200 - R64.rear) * Math.sin(ang) + 2, rearX: c.x - 4, rearY: rwy - c.sR + 4 };
  }

  // ---------------------------------------------------------------- people on the sidewalk
  const SKIN = ["#f1c7a8", "#d9a07a", "#b97a52", "#8d5a3b", "#6b4029", "#e8b58f"];
  const HAIR = ["#16100c", "#2b1a10", "#4a2c1a", "#0a0a0a", "#7a4a2a", "#b9b9c2"];
  const SHIRT = [COL.pink, COL.turq, COL.orange, "#ffffff", "#111111", COL.purple, "#e64a6b", "#2fb7a9", "#9b5de5", "#c9ced6"];
  const PANTS = ["#1d2a4a", "#222222", "#3a3f4a", "#5b3a78", "#0f3b4a", "#e9e9ee"];
  function makePerson(r, x, y, o = {}) {
    const kid = o.kid != null ? o.kid : r() < 0.18;
    return { x, y, s: (kid ? 0.68 : 0.9 + r() * 0.16) * (o.s || 1), skin: SKIN[(r() * SKIN.length) | 0], hair: HAIR[(r() * HAIR.length) | 0], hs: (r() * 6) | 0,
      shirt: SHIRT[(r() * SHIRT.length) | 0], pants: PANTS[(r() * PANTS.length) | 0], phone: r() < 0.3, cap: r() < 0.25 ? SHIRT[(r() * SHIRT.length) | 0] : null,
      shades: r() < 0.3, ph: r() * 6.28, react: 0, mood: 0, dance: o.dance || false, face: r() < 0.5 ? 1 : -1, bubble: null, kid };
  }
  function drawPerson(g, p, sx, t) {
    const s = p.s, rx = p.react > 0 ? 1 : 0, jump = rx ? Math.abs(Math.sin(p.react * 9)) * 7 * s * (p.mood > 0 ? 1 : 0.3) : p.dance ? Math.abs(Math.sin(t * 5 + p.ph)) * 2.5 : 0;
    g.save(); g.translate(sx, p.y - jump); g.scale(s * p.face, s);
    const sway = Math.sin(t * 1.6 + p.ph) * 0.8;
    g.fillStyle = "rgba(0,0,0,.25)"; g.beginPath(); g.ellipse(0, jump / s, 7, 1.6, 0, 0, 6.2832); g.fill();
    g.fillStyle = p.pants; rr(g, -4.6, -20, 4.2, 20, 1.6); g.fill(); rr(g, 0.4, -20, 4.2, 20, 1.6); g.fill();
    g.fillStyle = "#101010"; rr(g, -5.4, -2, 5.6, 2.4, 1); g.fill(); rr(g, 0.2, -2, 5.6, 2.4, 1); g.fill();
    g.fillStyle = p.shirt; rr(g, -6, -37, 12, 19, 4); g.fill();
    g.fillStyle = "rgba(0,0,0,.12)"; g.fillRect(-6, -24, 12, 2);
    const arm = (side, up) => {
      g.strokeStyle = p.shirt; g.lineCap = "round"; g.lineWidth = 3.6; g.beginPath(); g.moveTo(side * 5, -34);
      let hx, hy;
      if (up === 2) { hx = side * 3; hy = -48; } else if (up) { hx = side * 9; hy = -49 - Math.sin(t * 14 + side) * 2; } else { hx = side * 7 + sway * side * 0.3; hy = -21; }
      g.lineTo((side * 5 + hx) / 2 + side * 1.5, (-34 + hy) / 2); g.lineTo(hx, hy); g.stroke();
      g.fillStyle = p.skin; g.beginPath(); g.arc(hx, hy, 1.9, 0, 6.2832); g.fill(); return [hx, hy];
    };
    const cheering = p.react > 0 && p.mood > 0, wince = p.react > 0 && p.mood < 0;
    if (p.phone && !cheering) { arm(-1, false); const [hx, hy] = arm(1, 2); g.fillStyle = "#111"; rr(g, hx - 2.2, hy - 6.5, 4.4, 6.5, 0.8); g.fill(); g.fillStyle = "#bff6ff"; g.fillRect(hx - 1.5, hy - 5.9, 3, 5.2); }
    else if (wince) { arm(-1, 2); arm(1, 2); }
    else { arm(-1, cheering || (p.dance && Math.sin(t * 5 + p.ph) > 0.3)); arm(1, cheering); }
    g.fillStyle = p.skin; g.fillRect(-1.6, -40, 3.2, 3.5);
    g.beginPath(); g.arc(0, -44.5, 5.4, 0, 6.2832); g.fill();
    g.fillStyle = p.hair;
    if (p.cap) { g.fillStyle = p.cap; g.beginPath(); g.arc(0, -45.5, 5.6, 3.14, 6.28); g.fill(); g.fillRect(0, -46.2, 8.5, 1.6); }
    else if (p.hs === 0) { g.beginPath(); g.arc(0, -45.5, 5.7, 3.0, 6.4); g.fill(); }
    else if (p.hs === 1) { g.beginPath(); g.arc(0, -45.5, 5.8, 2.6, 6.6); g.fill(); g.fillRect(-5.8, -46, 3.4, 9); }
    else if (p.hs === 2) { g.beginPath(); g.arc(0, -45.5, 5.7, 3.0, 6.4); g.fill(); g.beginPath(); g.arc(-3.5, -51, 3.1, 0, 6.2832); g.fill(); }
    else if (p.hs === 3) { g.beginPath(); g.arc(0, -45.8, 5.8, 2.8, 6.5); g.fill(); g.beginPath(); g.moveTo(-5, -46); g.quadraticCurveTo(-10, -40, -7, -34); g.lineTo(-4.5, -41); g.fill(); }
    else if (p.hs === 4) { g.beginPath(); g.arc(0, -47, 5.2, 3.3, 6.1); g.fill(); }
    else { g.fillStyle = "#f2f2f2"; g.beginPath(); g.ellipse(0, -50.4, 9.5, 1.6, 0, 0, 6.2832); g.fill(); rr(g, -4.6, -56, 9.2, 6.2, 2.5); g.fill(); g.fillStyle = "#111"; g.fillRect(-4.6, -51.8, 9.2, 1.1); }
    if (p.shades) { g.fillStyle = "#050505"; rr(g, 0.6, -46, 5.2, 1.9, 0.8); g.fill(); }
    else { g.fillStyle = "#1a1a1a"; g.fillRect(2.4, -45.6, 1.1, 1.3); }
    if (cheering) { g.fillStyle = "#3a0d16"; g.beginPath(); g.ellipse(3.4, -41.6, 1.4, 1.2, 0, 0, 6.2832); g.fill(); }
    g.restore();
  }
  // v49.26: one wrapped, edge-safe speech card; return the bounds used for drawing.
  function bubble(g, x, y, text, t0, maxX, maxW = 170) {
    g.save(); let size = 13, lines, limit = Math.min(maxW, maxX - 20) - 16;
    const wrap = () => { const out = []; let line = ""; for (const word of text.split(/\s+/)) { const tryL = line ? line + " " + word : word; if (g.measureText(tryL).width <= limit || !line) line = tryL; else { out.push(line); line = word; } } if (line) out.push(line); return out; };   // v49.26: wrap on spaces only (no mid-word breaks)
    do { g.font = `900 ${size}px ${FONT}`; lines = wrap(); if (lines.length <= 2) break; size -= 0.5; } while (size > 1);
    const w = Math.max(...lines.map((l) => g.measureText(l).width)) + 16, h = lines.length * (size + 3) + 10;
    const bx = clamp(x - w / 2, 8, maxX - w - 8), by = Math.max(8, y - h - 8);
    g.fillStyle = "#fff"; g.strokeStyle = "#000"; g.lineWidth = 2.2; rr(g, bx, by, w, h, 9); g.fill(); g.stroke();
    const tx = clamp(x, bx + 8, bx + w - 8); g.beginPath(); g.moveTo(tx - 4, by + h - 1); g.lineTo(tx, by + h + 6); g.lineTo(tx + 4, by + h - 1); g.fill(); g.stroke();
    g.fillStyle = "#000"; g.textAlign = "center"; g.textBaseline = "middle";
    lines.forEach((l, i) => g.fillText(l, bx + w / 2, by + 5 + (i + 0.5) * (size + 3))); g.restore();
    return { x: bx - 2, y: by - 2, w: w + 4, h: h + 10, lines };
  }

  // ---------------------------------------------------------------- Abuela + La Chancla
  function drawAbuela(g, x, y, s, t, walking, wave) {
    g.save(); g.translate(x, y); g.scale(s, s);
    const step = walking ? Math.sin(t * 5) : 0, bob = walking ? Math.abs(Math.sin(t * 5)) * 0.8 : 0;
    g.fillStyle = "rgba(0,0,0,.3)"; g.beginPath(); g.ellipse(0, 0, 11, 2.2, 0, 0, 6.2832); g.fill();
    g.translate(0, -bob);
    g.fillStyle = "#1a1a1a"; rr(g, -4 + step * 1.5, -6, 4, 6, 1.2); g.fill(); rr(g, 0.5 - step * 1.5, -6, 4, 6, 1.2); g.fill();
    g.fillStyle = "#3b1d4f"; g.beginPath(); g.moveTo(-8, -6); g.quadraticCurveTo(-8.5, -24, -5.5, -36); g.lineTo(5.5, -36); g.quadraticCurveTo(8.5, -24, 8, -6); g.closePath(); g.fill();   // dress
    g.fillStyle = "#ff8fc0"; for (let i = 0; i < 9; i++) { g.beginPath(); g.arc(-5 + (i % 3) * 5 + (i > 2 && i < 6 ? 2.5 : 0), -10 - Math.floor(i / 3) * 7, 1.1, 0, 6.2832); g.fill(); }
    g.fillStyle = "#6a2c91"; g.beginPath(); g.moveTo(-7, -40); g.quadraticCurveTo(-10, -26, -6, -20); g.lineTo(6, -20); g.quadraticCurveTo(10, -26, 7, -40); g.closePath(); g.fill();   // rebozo
    g.strokeStyle = COL.pink; g.lineWidth = 0.9; g.beginPath(); for (let i = -6; i <= 6; i += 1.5) { g.moveTo(i, -20.5); g.lineTo(i + 0.3, -17.5); } g.stroke();
    g.strokeStyle = "#cfd5dc"; g.lineWidth = 1.6; g.lineCap = "round"; g.beginPath(); g.moveTo(9, -27); g.lineTo(11 + step * 1.2, 0); g.stroke();   // cane
    g.beginPath(); g.moveTo(9, -27); g.quadraticCurveTo(9, -30, 6.5, -29.5); g.stroke();
    g.fillStyle = "#e8d9cf"; g.strokeStyle = "#cbb8ac"; g.lineWidth = 0.6; rr(g, -14, -26, 7, 9, 1.5); g.fill(); g.stroke();   // bag of pan dulce
    g.fillStyle = COL.pink; g.beginPath(); g.arc(-10.5, -26, 2.6, 3.14, 6.28); g.fill();
    g.fillStyle = "#c48d6c"; g.beginPath(); g.arc(0, -44, 5.6, 0, 6.2832); g.fill();
    g.fillStyle = "#d9d9de"; g.beginPath(); g.arc(0, -45.5, 5.9, 3.0, 6.4); g.fill(); g.beginPath(); g.arc(-4.2, -48.5, 2.8, 0, 6.2832); g.fill();
    g.strokeStyle = "#222"; g.lineWidth = 0.6; g.beginPath(); g.arc(2.2, -44.2, 1.3, 0, 6.2832); g.moveTo(3.5, -44.2); g.lineTo(5, -44.6); g.stroke();
    g.strokeStyle = "#5a2a1e"; g.beginPath(); g.arc(2, -41.5, 1.4, 0.2, 2.6); g.stroke();
    if (wave) { g.strokeStyle = "#6a2c91"; g.lineWidth = 3; g.beginPath(); g.moveTo(-5, -36); g.lineTo(-10, -46 + Math.sin(t * 12) * 2); g.stroke(); g.fillStyle = "#c48d6c"; g.beginPath(); g.arc(-10.5, -47 + Math.sin(t * 12) * 2, 1.8, 0, 6.2832); g.fill(); }
    g.restore();
  }
  function drawChancla(g, x, y, ang, s = 1) {
    g.save(); g.translate(x, y); g.rotate(ang); g.scale(s, s);
    g.fillStyle = "#0d6e73"; g.beginPath(); g.ellipse(0, 1.5, 24, 10, 0, 0, 6.2832); g.fill();   // sole edge
    g.fillStyle = lg(g, -24, 0, 24, 0, [[0, "#ff4f9a"], [0.5, COL.pink], [1, "#d40f62"]]);
    g.beginPath(); g.moveTo(-23, 0); g.bezierCurveTo(-23, -9, -8, -10, 0, -7); g.bezierCurveTo(8, -5, 23, -10, 23, 0); g.bezierCurveTo(23, 9, 8, 6, 0, 6); g.bezierCurveTo(-8, 7, -23, 9, -23, 0); g.fill();
    g.strokeStyle = "#ffffff"; g.lineWidth = 3.2; g.lineCap = "round"; g.beginPath(); g.moveTo(12, 0); g.quadraticCurveTo(0, -9, -6, -6); g.moveTo(12, 0); g.quadraticCurveTo(0, 8, -6, 5); g.stroke();
    g.strokeStyle = COL.turq; g.lineWidth = 1.4; g.beginPath(); g.moveTo(12, 0); g.quadraticCurveTo(0, -9, -6, -6); g.moveTo(12, 0); g.quadraticCurveTo(0, 8, -6, 5); g.stroke();
    g.fillStyle = "#fff"; g.beginPath(); g.arc(12, 0, 2, 0, 6.2832); g.fill();
    g.restore();
  }

  // ---------------------------------------------------------------- obstacles (base at the ground line y)
  function drawObstacle(g, o, sx, gy, t) {
    const k = o.kind, w = o.w;
    g.save();
    if (o.knock) { g.translate(o.knock.x, -o.knock.y); g.translate(sx + w / 2, gy - o.h / 2); g.rotate(o.knock.a); g.translate(-(sx + w / 2), -(gy - o.h / 2)); g.globalAlpha = clamp(1 - o.knock.t / 1.2, 0, 1); }
    // v49.27: no badges or real logos; low bodies leave a generous hop window.
    if (k === "pallet") { g.fillStyle = "#8d5267"; g.fillRect(sx, gy - 5, w, 5); for (let i = 0; i < 4; i++) { g.fillStyle = i % 2 ? "#b47e8e" : "#744057"; g.fillRect(sx + i * w / 4, gy - 18, w / 4 - 3, 10); } }
    else if (k === "copcar") { g.fillStyle = "#171b30"; rr(g, sx, gy - 26, w, 23, 7); g.fill(); g.fillStyle = "#f4efff"; g.fillRect(sx + 28, gy - 25, 48, 21); g.fillStyle = "#748bab"; rr(g, sx + 23, gy - 35, 65, 16, 5); g.fill(); for (let i = 0; i < 2; i++) { g.fillStyle = i ? "#467dff" : "#ff287f"; g.fillRect(sx + 48 + i * 13, gy - 39, 12, 5); g.fillStyle = "#11121d"; g.beginPath(); g.arc(sx + 22 + i * 72, gy - 5, 10, 0, 6.2832); g.fill(); } }
    else if (k === "bump") { g.fillStyle = "#3d3946"; g.beginPath(); g.ellipse(sx + w / 2, gy, w / 2, o.h, 0, 3.14, 6.28); g.fill(); g.strokeStyle = "rgba(255,255,255,.18)"; g.lineWidth = 1; g.beginPath(); g.ellipse(sx + w / 2, gy, w / 2 - 2, o.h - 1.5, 0, 3.4, 6.0); g.stroke(); }
    else if (k === "hump") {
      g.fillStyle = "#34303d"; g.beginPath(); g.ellipse(sx + w / 2, gy, w / 2, o.h, 0, 3.14, 6.28); g.fill();
      g.save(); g.beginPath(); g.ellipse(sx + w / 2, gy, w / 2, o.h, 0, 3.14, 6.28); g.clip();
      for (let i = 0; i < 5; i++) { g.fillStyle = i % 2 ? COL.orange : "#ffffff"; g.beginPath(); const x0 = sx + 6 + i * (w - 12) / 5; g.moveTo(x0, gy); g.lineTo(x0 + 6, gy - o.h); g.lineTo(x0 + 12, gy - o.h); g.lineTo(x0 + 6, gy); g.fill(); }
      g.restore();
    } else if (k === "pothole") {
      g.fillStyle = "#0b0a10"; g.beginPath(); g.ellipse(sx + w / 2, gy + 2, w / 2, 7, 0, 0, 6.2832); g.fill();
      g.fillStyle = lg(g, sx, 0, sx + w, 0, [[0, "rgba(255,26,127,.35)"], [0.5, "rgba(0,201,205,.25)"], [1, "rgba(255,106,11,.3)"]]); g.beginPath(); g.ellipse(sx + w / 2, gy + 3, w / 2 - 6, 3.6, 0, 0, 6.2832); g.fill();
      g.strokeStyle = "#5b5666"; g.lineWidth = 1.2; g.beginPath(); g.ellipse(sx + w / 2, gy + 2, w / 2, 7, 0, 3.3, 6.1); g.stroke();
      g.strokeStyle = "#1d1b23"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(sx - 4, gy - 2); g.lineTo(sx + 3, gy); g.moveTo(sx + w + 5, gy + 4); g.lineTo(sx + w - 2, gy + 1); g.stroke();
    } else if (k === "cone" || k === "cones") {
      const n = k === "cones" ? 3 : 1;
      for (let i = 0; i < n; i++) { const cx = sx + 9 + i * (w - 18) / Math.max(1, n - 1) * (n > 1 ? 1 : 0);
        g.fillStyle = "#1a1a1a"; g.fillRect(cx - 10, gy - 3, 20, 3);
        g.fillStyle = lg(g, cx - 8, 0, cx + 8, 0, [[0, "#c94d00"], [0.4, COL.orange], [1, "#b33f00"]]); g.beginPath(); g.moveTo(cx - 8, gy - 3); g.lineTo(cx - 1.6, gy - 30); g.lineTo(cx + 1.6, gy - 30); g.lineTo(cx + 8, gy - 3); g.fill();
        g.fillStyle = "#f4f4f4"; g.beginPath(); g.moveTo(cx - 5.6, gy - 12); g.lineTo(cx - 3.7, gy - 19); g.lineTo(cx + 3.7, gy - 19); g.lineTo(cx + 5.6, gy - 12); g.fill(); }
    } else if (k === "rails") {
      g.fillStyle = "#2a2730"; g.fillRect(sx - 8, gy - 2, w + 16, 6);
      for (const rx of [sx + 6, sx + w - 14]) { g.fillStyle = chromeV(g, gy - 9, gy); g.fillRect(rx, gy - 9, 8, 9); g.fillStyle = "#555"; g.fillRect(rx - 3, gy - 2, 14, 2); }
    } else if (k === "tires") {
      for (let i = 0; i < 3; i++) { const ty = gy - 6 - i * 11; g.fillStyle = "#151418"; rr(g, sx + 1 + (i % 2) * 1.5, ty - 5.5, w - 2, 11, 5); g.fill(); g.fillStyle = "#2c2a31"; rr(g, sx + 6, ty - 2, w - 12, 4, 2); g.fill(); g.strokeStyle = "rgba(255,255,255,.15)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(sx + 5, ty - 4.5); g.lineTo(sx + w - 5, ty - 4.5); g.stroke(); }
    } else if (k === "cooler") {
      g.fillStyle = COL.turq; rr(g, sx, gy - 24, w, 24, 3); g.fill(); g.fillStyle = "#ffffff"; rr(g, sx - 1, gy - 26, w + 2, 6, 2); g.fill(); g.fillStyle = "#007f86"; g.fillRect(sx + 3, gy - 14, w - 6, 2); g.fillStyle = "#fff"; g.fillRect(sx + w / 2 - 5, gy - 29, 10, 3);
    } else if (k === "mattress") {
      g.fillStyle = "#e9eef6"; g.beginPath(); g.moveTo(sx, gy); g.quadraticCurveTo(sx + 4, gy - 22, sx + 26, gy - 20); g.lineTo(sx + w, gy - 9); g.lineTo(sx + w, gy); g.closePath(); g.fill();
      g.strokeStyle = "#7fd4e0"; g.lineWidth = 1.2; g.beginPath(); for (let i = 1; i < 6; i++) { g.moveTo(sx + i * w / 6, gy); g.lineTo(sx + i * w / 6 - 3, gy - 20 + i * 2); } g.stroke();
      g.fillStyle = "rgba(0,0,0,.1)"; g.fillRect(sx, gy - 3, w, 3);
    } else if (k === "couch") {
      g.fillStyle = "#6a2c91"; rr(g, sx, gy - 30, w, 24, 5); g.fill(); g.fillStyle = "#8d44c0"; rr(g, sx + 4, gy - 40, w - 8, 14, 5); g.fill(); rr(g, sx - 3, gy - 30, 12, 20, 5); g.fill(); rr(g, sx + w - 9, gy - 30, 12, 20, 5); g.fill();
      g.fillStyle = "#3a1650"; g.fillRect(sx + 4, gy - 7, 4, 7); g.fillRect(sx + w - 8, gy - 7, 4, 7); g.strokeStyle = "rgba(0,0,0,.25)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(sx + w / 2, gy - 28); g.lineTo(sx + w / 2, gy - 9); g.stroke();
      g.fillStyle = "#e9eef6"; g.beginPath(); g.moveTo(sx + 20, gy - 30); g.lineTo(sx + 26, gy - 36); g.lineTo(sx + 30, gy - 30); g.fill();
    } else if (k === "pinata") {
      const cx = sx + w / 2, cy = gy - 17;
      g.fillStyle = COL.pink; g.beginPath(); g.arc(cx, cy, 11, 0, 6.2832); g.fill();
      const cols = [COL.turq, COL.orange, COL.purple, "#ffffff", COL.pink];
      for (let i = 0; i < 5; i++) { const a = -1.57 + i * 1.2566 + 0.35; g.fillStyle = cols[i]; g.beginPath(); g.moveTo(cx + Math.cos(a - 0.3) * 10, cy + Math.sin(a - 0.3) * 10); g.lineTo(cx + Math.cos(a) * 19, cy + Math.sin(a) * 19); g.lineTo(cx + Math.cos(a + 0.3) * 10, cy + Math.sin(a + 0.3) * 10); g.fill(); }
      g.strokeStyle = "#ffffff"; g.lineWidth = 1; g.beginPath(); g.moveTo(cx - 8, cy + 8); g.lineTo(cx - 13, gy); g.moveTo(cx + 6, cy + 9); g.lineTo(cx + 12, gy); g.stroke();
    } else if (k === "barricade") {
      g.fillStyle = "#e9eef6"; g.fillRect(sx + 3, gy - 52, 3, 52); g.fillRect(sx + w - 6, gy - 52, 3, 52);
      for (const by of [gy - 48, gy - 30]) { g.save(); rr(g, sx - 3, by, w + 6, 11, 2); g.clip(); g.fillStyle = "#ffffff"; g.fillRect(sx - 3, by, w + 6, 11); g.fillStyle = COL.orange; for (let i = -2; i < 8; i++) { g.beginPath(); g.moveTo(sx + i * 9, by + 11); g.lineTo(sx + i * 9 + 5, by + 11); g.lineTo(sx + i * 9 + 14, by); g.lineTo(sx + i * 9 + 9, by); g.fill(); } g.restore(); }
      const on = Math.sin(t * 8) > 0; g.fillStyle = on ? "#ff4a2a" : "#7a2014"; g.beginPath(); g.arc(sx + 5, gy - 55, 3, 0, 6.2832); g.fill(); if (on) drawGlow(g, sx + 5, gy - 55, 12, "#ff4a2a", 0.6);
    }
    g.restore();
  }
  function drawCoin(g, x, y, t, s = 1) {
    const sq = Math.abs(Math.cos(t * 4)) * 0.75 + 0.25;
    g.save(); g.translate(x, y); g.scale(sq * s, s);
    g.fillStyle = "#6e7782"; g.beginPath(); g.arc(0.8, 0.8, 8, 0, 6.2832); g.fill();
    g.fillStyle = lg(g, -8, -8, 8, 8, [[0, "#ffffff"], [0.45, "#cfd5dc"], [1, "#8a939d"]]); g.beginPath(); g.arc(0, 0, 8, 0, 6.2832); g.fill();
    g.strokeStyle = COL.turq; g.lineWidth = 1.6; g.beginPath(); g.arc(0, 0, 6, 0, 6.2832); g.stroke();
    g.fillStyle = COL.pink; g.font = `900 9px ${FONT}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("F", 0, 0.5);
    g.restore();
  }
  // HUD icons (vector so nothing yellow sneaks in from an emoji font)
  function icon(g, kind, x, y, s) {
    g.save(); g.translate(x, y); g.scale(s, s);
    if (kind === "flame") { g.fillStyle = COL.orange; g.beginPath(); g.moveTo(0, 10); g.bezierCurveTo(-9, 8, -9, -2, -3, -10); g.bezierCurveTo(-2, -4, 1, -4, 2, -7); g.bezierCurveTo(8, -2, 9, 8, 0, 10); g.fill(); g.fillStyle = COL.pink; g.beginPath(); g.moveTo(0, 9); g.bezierCurveTo(-4, 7, -4, 2, -1, -2); g.bezierCurveTo(0, 1, 2, 1, 3, 0); g.bezierCurveTo(5, 4, 4, 8, 0, 9); g.fill(); }
    else if (kind === "shades") { g.fillStyle = "#000"; g.strokeStyle = "#fff"; g.lineWidth = 1.4; rr(g, -11, -4, 9.5, 7, 3); g.fill(); g.stroke(); rr(g, 1.5, -4, 9.5, 7, 3); g.fill(); g.stroke(); g.beginPath(); g.moveTo(-1.5, -2); g.lineTo(1.5, -2); g.stroke(); g.fillStyle = "rgba(255,255,255,.6)"; g.fillRect(-9, -2.5, 3, 1.2); g.fillRect(3.5, -2.5, 3, 1.2); }
    else if (kind === "burst") { g.fillStyle = COL.pink; g.beginPath(); for (let i = 0; i < 16; i++) { const a = i * 0.3927, r = i % 2 ? 5 : 11; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); g.fillStyle = COL.orange; g.beginPath(); for (let i = 0; i < 16; i++) { const a = i * 0.3927 + 0.2, r = i % 2 ? 3 : 6.5; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); }
    else if (kind === "skull") { g.fillStyle = "#fff"; g.strokeStyle = "#000"; g.lineWidth = 1.2; g.beginPath(); g.arc(0, -2, 8, 0, 6.2832); g.fill(); g.stroke(); rr(g, -4.5, 3, 9, 6, 2); g.fill(); g.stroke(); g.fillStyle = "#000"; g.beginPath(); g.arc(-3, -2, 2.4, 0, 6.2832); g.arc(3, -2, 2.4, 0, 6.2832); g.fill(); g.fillStyle = COL.pink; g.beginPath(); g.arc(-3, -2, 0.9, 0, 6.2832); g.arc(3, -2, 0.9, 0, 6.2832); g.fill(); }
    else if (kind === "wheel") { g.fillStyle = "#111"; g.beginPath(); g.arc(0, 0, 8, 0, 6.2832); g.fill(); g.fillStyle = "#fff"; g.beginPath(); g.arc(0, 0, 6.6, 0, 6.2832); g.arc(0, 0, 5, 0, 6.2832, true); g.fill(); g.fillStyle = "#c9ced6"; g.beginPath(); g.arc(0, 0, 5, 0, 6.2832); g.fill(); g.strokeStyle = "#fff"; g.lineWidth = 0.5; g.beginPath(); for (let i = 0; i < 10; i++) { const a = i * 0.628; g.moveTo(0, 0); g.lineTo(Math.cos(a) * 4.8, Math.sin(a) * 4.8); } g.stroke(); }
    else if (kind === "wheelx") { g.strokeStyle = "rgba(255,255,255,.35)"; g.lineWidth = 1.5; g.beginPath(); g.arc(0, 0, 7, 0, 6.2832); g.stroke(); }
    g.restore();
  }

  // ---------------------------------------------------------------- the boulevard: buildings + signs (each lot is drawn once into its own canvas)
  function stucco(g, x, y, w, h, col, seed) {
    g.fillStyle = lg(g, 0, y, 0, y + h, [[0, shade(col, 0.08)], [1, shade(col, -0.18)]]); g.fillRect(x, y, w, h);
    const r = rng(seed || 7); g.fillStyle = "rgba(0,0,0,.06)"; for (let i = 0; i < w * h / 60; i++) g.fillRect(x + r() * w, y + r() * h, 1, 1);
    g.fillStyle = "rgba(255,255,255,.06)"; for (let i = 0; i < w * h / 90; i++) g.fillRect(x + r() * w, y + r() * h, 1, 1);
  }
  function glowWin(g, x, y, w, h, bars) {
    g.fillStyle = "#1b1026"; g.fillRect(x - 2, y - 2, w + 4, h + 4);
    g.fillStyle = lg(g, 0, y, 0, y + h, [[0, "#ffe3ef"], [0.6, "#ffb3d1"], [1, "#e47aa8"]]); g.fillRect(x, y, w, h);
    g.fillStyle = "rgba(60,20,60,.35)"; g.fillRect(x, y + h * 0.55, w, h * 0.45);
    if (bars) { g.fillStyle = "#2a2230"; for (let i = 1; i < 5; i++) g.fillRect(x + i * w / 5 - 0.6, y, 1.2, h); }
    else { g.fillStyle = "#2a2230"; g.fillRect(x + w / 2 - 0.8, y, 1.6, h); }
    g.fillStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.moveTo(x + 2, y + h); g.lineTo(x + w * 0.35, y); g.lineTo(x + w * 0.45, y); g.lineTo(x + 6, y + h); g.fill();
  }
  function signBoard(g, x, y, w, h, s, opt = {}) {
    const [bg, fg, ac] = s.colors;
    g.fillStyle = "rgba(0,0,0,.35)"; rr(g, x + 2, y + 3, w, h, 6); g.fill();
    g.fillStyle = bg; rr(g, x, y, w, h, 6); g.fill();
    g.strokeStyle = ac; g.lineWidth = 3; rr(g, x + 3, y + 3, w - 6, h - 6, 4); g.stroke();
    g.textAlign = "center"; g.textBaseline = "middle";
    const sz = fitText(g, s.name, w - 18, opt.size || h * 0.36);
    outlined(g, s.name, x + w / 2, y + h * (s.tagline ? 0.4 : 0.5), fg, bg === "#000000" ? null : "rgba(0,0,0,.35)", 2.5);
    if (s.tagline) { fitText(g, s.tagline, w - 22, Math.min(sz * 0.55, h * 0.22), "800", SANS); g.fillStyle = ac === bg ? fg : ac; g.fillText(s.tagline, x + w / 2, y + h * 0.76); }
  }
  function awning(g, x, y, w, h, c1, c2) {
    const n = Math.max(4, Math.round(w / 14)), sw = w / n;
    for (let i = 0; i < n; i++) { g.fillStyle = i % 2 ? c2 : c1; g.beginPath(); g.moveTo(x + i * sw, y); g.lineTo(x + (i + 1) * sw, y); g.lineTo(x + (i + 1) * sw + 3, y + h); g.arc(x + i * sw + sw / 2 + 3, y + h, sw / 2, 0, 3.14); g.closePath(); g.fill(); }
    g.fillStyle = "rgba(0,0,0,.2)"; g.fillRect(x, y, w, 2);
  }
  function stringLights(g, x0, x1, y, sag) {
    g.strokeStyle = "#1a1a1a"; g.lineWidth = 0.7; g.beginPath(); g.moveTo(x0, y); g.quadraticCurveTo((x0 + x1) / 2, y + sag * 2, x1, y); g.stroke();
    const cols = ["#ffffff", COL.pink, COL.turq, COL.orange, "#c9a2ff"];
    for (let i = 1; i < 12; i++) { const tt = i / 12, bx = lerp(x0, x1, tt), by = (1 - tt) * (1 - tt) * y + 2 * tt * (1 - tt) * (y + sag * 2) + tt * tt * y + 2;
      g.fillStyle = cols[i % 5]; g.beginPath(); g.arc(bx, by, 1.6, 0, 6.2832); g.fill(); g.fillStyle = hexA(cols[i % 5], 0.25); g.beginPath(); g.arc(bx, by, 4, 0, 6.2832); g.fill(); }
  }
  function papelPicado(g, x0, x1, y) {
    const cols = [COL.pink, COL.orange, COL.turq, COL.purple, "#ffffff"]; g.strokeStyle = "#222"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(x0, y); g.quadraticCurveTo((x0 + x1) / 2, y + 8, x1, y); g.stroke();
    for (let x = x0 + 4, i = 0; x < x1 - 8; x += 13, i++) { const tt = (x - x0) / (x1 - x0), yy = y + 8 * 2 * tt * (1 - tt) + 0.5;
      g.fillStyle = cols[i % 5]; g.beginPath(); g.moveTo(x, yy); g.lineTo(x + 10, yy); g.lineTo(x + 10, yy + 11); for (let k = 0; k < 4; k++) g.lineTo(x + 10 - k * 2.5 - 1.25, yy + (k % 2 ? 11 : 13)); g.lineTo(x, yy + 11); g.fill();
      g.fillStyle = "rgba(0,0,0,.35)"; g.fillRect(x + 3, yy + 3, 1.4, 1.4); g.fillRect(x + 6, yy + 3, 1.4, 1.4); g.fillRect(x + 4.3, yy + 6, 1.4, 1.4); }
  }
  function marigolds(g, x, y, n = 5) {
    const r = rng(x | 0); for (let i = 0; i < n; i++) { const fx = x + i * 5 + r() * 2, fy = y - 2 - r() * 4; g.fillStyle = "#1f6b3a"; g.fillRect(fx - 0.4, fy, 0.8, 4);
      g.fillStyle = "#ff6a0b"; g.beginPath(); g.arc(fx, fy, 2.6, 0, 6.2832); g.fill(); g.fillStyle = "#ff8a3d"; g.beginPath(); g.arc(fx - 0.6, fy - 0.6, 1.4, 0, 6.2832); g.fill(); }
  }
  function palm(g, x, y, h, r) {
    g.strokeStyle = "#4a3326"; g.lineWidth = 5; g.lineCap = "round"; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + 10, y - h * 0.5, x + 4, y - h); g.stroke();
    g.strokeStyle = "rgba(0,0,0,.25)"; g.lineWidth = 0.8; for (let i = 8; i < h; i += 7) { g.beginPath(); g.moveTo(x + 6 * Math.sin(i / h * 3) - 2, y - i); g.lineTo(x + 6 * Math.sin(i / h * 3) + 3, y - i); g.stroke(); }
    for (let i = 0; i < 8; i++) { const a = -3.14 + i * 0.45 + (r ? r() * 0.2 : 0), L = 26 + (i % 2) * 6; g.strokeStyle = i % 2 ? "#1f5e3c" : "#2a7a4d"; g.lineWidth = 3;
      g.beginPath(); g.moveTo(x + 4, y - h); g.quadraticCurveTo(x + 4 + Math.cos(a) * L * 0.6, y - h + Math.sin(a) * L * 0.4 - 8, x + 4 + Math.cos(a) * L, y - h + Math.sin(a) * L * 0.5 + 6); g.stroke(); }
  }
  function oldTruck(g, x, y, col) {   // a faded 50s-style pickup parked in a driveway (scenery)
    g.fillStyle = "rgba(0,0,0,.3)"; g.beginPath(); g.ellipse(x + 46, y, 50, 3, 0, 0, 6.2832); g.fill();
    g.fillStyle = col; g.beginPath(); g.moveTo(x, y - 8); g.lineTo(x, y - 24); g.lineTo(x + 46, y - 24); g.lineTo(x + 50, y - 40); g.quadraticCurveTo(x + 52, y - 43, x + 58, y - 43); g.lineTo(x + 70, y - 43); g.quadraticCurveTo(x + 74, y - 42, x + 76, y - 30); g.quadraticCurveTo(x + 92, y - 29, x + 94, y - 22); g.lineTo(x + 94, y - 8); g.closePath(); g.fill();
    g.fillStyle = "rgba(120,60,40,.45)"; g.beginPath(); g.ellipse(x + 20, y - 14, 8, 4, 0.2, 0, 6.2832); g.ellipse(x + 84, y - 18, 5, 3, 0, 0, 6.2832); g.fill();   // rust
    g.fillStyle = "#2a2a3a"; g.beginPath(); g.moveTo(x + 53, y - 39); g.lineTo(x + 70, y - 39); g.lineTo(x + 72, y - 30); g.lineTo(x + 51, y - 30); g.fill();
    g.fillStyle = chromeV(g, y - 14, y - 8); g.fillRect(x + 88, y - 14, 8, 6); g.fillRect(x - 2, y - 14, 5, 6);
    for (const wx of [x + 18, x + 76]) { g.fillStyle = "#111"; g.beginPath(); g.arc(wx, y - 8, 9, 0, 6.2832); g.fill(); g.fillStyle = "#9aa3ad"; g.beginPath(); g.arc(wx, y - 8, 4, 0, 6.2832); g.fill(); }
  }
  function dog(g, x, y, t, run, col = "#7a4a2a") {
    const leg = run ? Math.sin(t * 22) * 3 : 0;
    g.save(); g.translate(x, y);
    g.strokeStyle = col; g.lineWidth = 2.2; g.lineCap = "round"; g.beginPath(); g.moveTo(-6, -4); g.lineTo(-7 + leg, 0); g.moveTo(-3, -4); g.lineTo(-2 - leg, 0); g.moveTo(5, -4); g.lineTo(6 - leg, 0); g.moveTo(8, -4); g.lineTo(8 + leg, 0); g.stroke();
    g.fillStyle = col; rr(g, -8, -10, 18, 7, 3.5); g.fill(); g.beginPath(); g.arc(12, -12, 4, 0, 6.2832); g.fill(); g.beginPath(); g.moveTo(10, -15); g.lineTo(11, -19); g.lineTo(13, -15); g.fill();
    g.beginPath(); g.moveTo(-8, -8); g.quadraticCurveTo(-13, -13 - (run ? Math.sin(t * 25) * 2 : 0), -12, -15); g.lineWidth = 1.6; g.strokeStyle = col; g.stroke();
    g.fillStyle = "#000"; g.beginPath(); g.arc(15.6, -11.6, 0.9, 0, 6.2832); g.fill(); g.fillRect(12.6, -13.6, 1, 1);
    g.restore();
  }
  // lot kinds → width; their signs come from SIGNS (slot "store", same kind; "shop" rotates through the general stores)
  const LOTS = { taco: 214, icehouse: 262, tires: 222, pinata: 206, shop: 196, barber: 176, mural: 236, corner: 214, house: 206, party: 270, construction: 238, vacant: 110 };
  const LOT_BAG = ["taco", "shop", "house", "icehouse", "mural", "tires", "party", "pinata", "corner", "barber", "shop", "vacant", "house", "construction", "shop"];
  function drawLot(g, L, season) {
    const w = L.w, r = rng(L.seed), s = L.sign;
    g.lineJoin = "round";
    if (L.kind === "taco") {
      stucco(g, 6, -118, w - 12, 118, "#14b8b0", L.seed); g.fillStyle = COL.pink; g.fillRect(6, -122, w - 12, 6); g.fillRect(6, -8, w - 12, 8);
      signBoard(g, 16, -176, w - 32, 50, s);
      g.fillStyle = "#2a2230"; g.fillRect(28, -92, 86, 52); glowWin(g, 32, -88, 78, 44);
      g.fillStyle = "#111"; rr(g, 126, -113, 78, 46, 4); g.fill(); g.fillStyle = "#fff"; g.font = `800 7.2px ${SANS}`; g.textAlign = "left"; g.textBaseline = "top";
      ["TACOS ......... 2", "TORTAS ........ 6", "AGUAS FRESCAS", "BREAKFAST TACOS"].forEach((l, i) => g.fillText(l, 131, -109 + i * 10));
      awning(g, 22, -104, 98, 14, COL.pink, "#ffffff");
      g.fillStyle = "#5a3d2a"; g.fillRect(140, -30, 50, 4); g.fillRect(146, -26, 3, 26); g.fillRect(182, -26, 3, 26); g.fillRect(136, -14, 58, 3);
      g.strokeStyle = "#ddd"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(165, -30); g.lineTo(165, -58); g.stroke(); g.fillStyle = COL.orange; g.beginPath(); g.moveTo(141, -50); g.quadraticCurveTo(165, -67, 189, -50); g.closePath(); g.fill();
      stringLights(g, 6, w - 6, -120, 6);
    } else if (L.kind === "icehouse") {
      g.fillStyle = "#3a2f48"; g.fillRect(4, -112, w - 8, 112);
      g.fillStyle = lg(g, 0, -126, 0, -110, [[0, "#c9ced6"], [1, "#7b8390"]]); g.beginPath(); g.moveTo(-4, -110); g.lineTo(10, -128); g.lineTo(w - 10, -128); g.lineTo(w + 4, -110); g.fill();
      g.strokeStyle = "rgba(0,0,0,.2)"; g.lineWidth = 0.8; for (let x = 0; x < w; x += 6) { g.beginPath(); g.moveTo(x, -110); g.lineTo(x + 2, -127); g.stroke(); }
      for (let i = 0; i < 3; i++) { const ox = 16 + i * ((w - 32) / 3); g.fillStyle = lg(g, 0, -96, 0, -10, [[0, "#ffc3dc"], [1, "#6b2a58"]]); g.fillRect(ox, -96, (w - 32) / 3 - 10, 86);
        g.fillStyle = "rgba(0,0,0,.25)"; for (let k = 0; k < 4; k++) g.fillRect(ox, -96 + k * 4, (w - 32) / 3 - 10, 1.4); }
      signBoard(g, 20, -178, w - 40, 48, s);
      for (const tx of [40, w / 2 + 10]) { g.fillStyle = "#6b4630"; g.fillRect(tx, -26, 56, 4); g.fillRect(tx + 4, -22, 3, 22); g.fillRect(tx + 48, -22, 3, 22); g.fillRect(tx - 4, -12, 64, 3); }
      g.fillStyle = "#ffffff"; rr(g, w - 54, -28, 30, 28, 3); g.fill(); g.fillStyle = COL.turq; g.fillRect(w - 54, -20, 30, 6); g.fillStyle = "#000"; g.font = `900 6px ${SANS}`; g.textAlign = "center"; g.fillText("ICE", w - 39, -15);
      stringLights(g, 4, w - 4, -110, 7);
    } else if (L.kind === "tires") {
      g.fillStyle = "#e9e9ee"; g.fillRect(6, -120, w - 12, 120); g.strokeStyle = "rgba(0,0,0,.08)"; g.lineWidth = 0.7; for (let y = -116; y < 0; y += 6) { g.beginPath(); g.moveTo(6, y); g.lineTo(w - 6, y); g.stroke(); }
      g.fillStyle = COL.orange; g.fillRect(6, -124, w - 12, 8);
      signBoard(g, 14, -114, w - 28, 40, s);
      g.fillStyle = "#1d1b23"; g.fillRect(24, -66, 80, 66); g.fillStyle = "#2c2a33"; for (let y = -64; y < 0; y += 6) g.fillRect(24, y, 80, 3);
      g.fillStyle = "#111"; g.font = `900 9px ${FONT}`; g.textAlign = "center"; g.fillText("NUEVAS Y USADAS", w - 52, -58);
      for (let i = 0; i < 3; i++) for (let k = 0; k < 4 - i; k++) { const tx = w - 92 + i * 24, ty = -6 - k * 10; g.fillStyle = "#151418"; rr(g, tx, ty - 5, 22, 10, 5); g.fill(); g.fillStyle = "#34313b"; rr(g, tx + 5, ty - 1.6, 12, 3.2, 1.6); g.fill(); }
      g.strokeStyle = "#151418"; g.lineWidth = 5; g.beginPath(); g.arc(w - 32, -137, 11, 0, 6.2832); g.stroke(); g.fillStyle = "#34313b"; g.beginPath(); g.arc(w - 32, -137, 4, 0, 6.2832); g.fill();   // a tire on the roof
    } else if (L.kind === "pinata") {
      stucco(g, 6, -124, w - 12, 124, "#ff6aa8", L.seed); g.fillStyle = COL.purple; g.fillRect(6, -128, w - 12, 7);
      signBoard(g, 14, -182, w - 28, 50, s);
      glowWin(g, 22, -86, 70, 50); g.fillStyle = "#3a1d4f"; g.fillRect(110, -74, 34, 74); g.fillStyle = COL.turq; g.fillRect(110, -74, 34, 4);
      g.strokeStyle = "#333"; g.lineWidth = 0.7; g.beginPath(); g.moveTo(8, -118); g.lineTo(w - 8, -118); g.stroke();
      const cols = [COL.turq, COL.orange, "#ffffff", COL.purple, "#ff1a7f"];
      for (let i = 0; i < 4; i++) { const px = 30 + i * ((w - 50) / 3.6), py = -100 + (i % 2) * 6; g.beginPath(); g.moveTo(px, -118); g.lineTo(px, py - 10); g.stroke();
        g.fillStyle = cols[i]; g.beginPath(); g.arc(px, py, 7, 0, 6.2832); g.fill();
        for (let k = 0; k < 5; k++) { const a = -1.57 + k * 1.2566; g.fillStyle = cols[(i + k + 1) % 5]; g.beginPath(); g.moveTo(px + Math.cos(a - 0.35) * 6, py + Math.sin(a - 0.35) * 6); g.lineTo(px + Math.cos(a) * 13, py + Math.sin(a) * 13); g.lineTo(px + Math.cos(a + 0.35) * 6, py + Math.sin(a + 0.35) * 6); g.fill(); } }
    } else if (L.kind === "shop" || L.kind === "barber") {
      const col = [COL.turq, "#f1eff8", "#ff8fbf", "#c9a2ff", "#ff9a5c"][L.seed % 5];
      stucco(g, 6, -128, w - 12, 128, col, L.seed); g.fillStyle = "#2a2230"; g.fillRect(2, -134, w - 4, 8);
      signBoard(g, 12, -122, w - 24, 44, s);
      glowWin(g, 18, -70, w * 0.46, 46, true); g.fillStyle = "#2a2230"; g.fillRect(w * 0.62, -70, 34, 70); g.fillStyle = "rgba(255,255,255,.12)"; g.fillRect(w * 0.62 + 3, -66, 12, 40);
      g.fillStyle = COL.pink; g.font = `900 8px ${FONT}`; g.textAlign = "center"; g.fillText("ABIERTO", w * 0.62 + 17, -74); drawGlow(g, w * 0.62 + 17, -76, 16, COL.pink, 0.35);
      awning(g, 12, -76, w * 0.52, 10, s.colors[0] === "#000000" ? COL.turq : s.colors[0], "#ffffff");
      if (L.kind === "barber") { const px = w - 22; g.fillStyle = "#fff"; rr(g, px, -66, 9, 38, 4); g.fill(); g.save(); rr(g, px, -66, 9, 38, 4); g.clip(); g.strokeStyle = COL.pink; g.lineWidth = 2.5; for (let y = -76; y < -20; y += 7) { g.beginPath(); g.moveTo(px - 2, y); g.lineTo(px + 11, y + 9); g.stroke(); } g.strokeStyle = COL.turq; for (let y = -72; y < -20; y += 7) { g.beginPath(); g.moveTo(px - 2, y); g.lineTo(px + 11, y + 9); g.stroke(); } g.restore(); g.fillStyle = chromeV(g, -70, -64); g.fillRect(px - 1, -70, 11, 4); g.fillRect(px - 1, -29, 11, 4); }
    } else if (L.kind === "mural") {
      g.fillStyle = "#e9e5ef"; g.fillRect(4, -132, w - 8, 132);
      g.save(); rr(g, 12, -124, w - 24, 112, 4); g.clip();
      g.fillStyle = lg(g, 0, -124, 0, -12, [[0, "#3b0f5c"], [0.45, COL.pink], [0.8, COL.orange], [1, "#ff8a3d"]]); g.fillRect(12, -124, w - 24, 112);
      g.fillStyle = "#ffc1d9"; g.beginPath(); g.arc(w / 2, -52, 30, 3.14, 6.28); g.fill(); g.fillStyle = "#ff8ab8"; for (let i = 0; i < 4; i++) g.fillRect(w / 2 - 32, -60 + i * 6, 64, 2);
      g.fillStyle = "#2a0d3a"; g.beginPath(); g.moveTo(12, -40); for (let x = 12; x <= w - 12; x += 16) g.lineTo(x, -40 - Math.abs(Math.sin(x * 0.07)) * 18); g.lineTo(w - 12, -12); g.lineTo(12, -12); g.fill();
      g.fillStyle = "#14072b"; g.beginPath(); g.moveTo(w / 2 - 48, -22); g.lineTo(w / 2 - 44, -31); g.lineTo(w / 2 - 14, -32); g.lineTo(w / 2 - 6, -42); g.lineTo(w / 2 + 18, -42); g.lineTo(w / 2 + 26, -32); g.lineTo(w / 2 + 50, -30); g.lineTo(w / 2 + 50, -22); g.fill();
      g.beginPath(); g.arc(w / 2 - 28, -22, 6, 0, 6.2832); g.arc(w / 2 + 32, -22, 6, 0, 6.2832); g.fill();
      g.fillStyle = COL.turq; g.font = `900 30px ${FONT}`; g.textAlign = "center"; outlined(g, "PURO 210", w / 2, -86, "#ffffff", COL.black, 5);
      g.fillStyle = COL.pink; g.beginPath(); const hx = 34, hy = -104; g.moveTo(hx, hy + 6); g.bezierCurveTo(hx - 12, hy - 4, hx - 4, hy - 14, hx, hy - 6); g.bezierCurveTo(hx + 4, hy - 14, hx + 12, hy - 4, hx, hy + 6); g.fill();
      g.restore(); g.strokeStyle = "#ffffff"; g.lineWidth = 3; rr(g, 12, -124, w - 24, 112, 4); g.stroke();
    } else if (L.kind === "corner") {
      stucco(g, 6, -122, w - 12, 122, "#f3f0f7", L.seed); g.fillStyle = COL.turq; g.fillRect(6, -126, w - 12, 8); g.fillStyle = COL.pink; g.fillRect(6, -10, w - 12, 10);
      g.fillStyle = COL.black; g.font = `900 22px ${FONT}`; g.textAlign = "center"; outlined(g, "ABARROTES", w / 2, -96, COL.pink, "#000", 4);
      g.fillStyle = "#333"; g.font = `800 8px ${SANS}`; g.fillText("RASPAS · ICE · PAN DULCE · OPEN LATE", w / 2, -82);
      glowWin(g, 18, -72, 66, 44, true); glowWin(g, w - 84, -72, 66, 44, true); g.fillStyle = "#2a2230"; g.fillRect(w / 2 - 14, -72, 28, 72);
      g.fillStyle = "#ffffff"; rr(g, w - 60, -26, 40, 26, 2); g.fill(); g.fillStyle = COL.turq; g.font = `900 9px ${FONT}`; g.fillText("ICE", w - 40, -11);
    } else if (L.kind === "house" || L.kind === "party") {
      const hw = L.kind === "party" ? 120 : 130, col = ["#ffb3cf", "#9ef0ec", "#d9c4ff", "#ffffff", "#ffc09a"][L.seed % 5];
      g.fillStyle = "#3d2c45"; g.beginPath(); g.moveTo(0, -78); g.lineTo(hw / 2, -112); g.lineTo(hw, -78); g.fill();
      stucco(g, 8, -80, hw - 16, 80, col, L.seed);
      glowWin(g, 20, -62, 30, 26); g.fillStyle = "#4a2a20"; g.fillRect(64, -58, 22, 58); g.fillStyle = chromeV(g, -32, -28); g.fillRect(81, -31, 2.5, 2.5);
      g.fillStyle = "#c9ced6"; g.fillRect(56, -64, 40, 3); g.fillRect(58, -64, 2.5, 64); g.fillRect(92, -64, 2.5, 64);
      for (let i = 0; i < 3; i++) { g.fillStyle = "#b5462a"; rr(g, 14 + i * 9, -8, 7, 8, 1); g.fill(); g.fillStyle = "#2f7d4b"; g.beginPath(); g.arc(17.5 + i * 9, -11, 4.5, 0, 6.2832); g.fill(); g.fillStyle = COL.pink; g.beginPath(); g.arc(17 + i * 9, -13, 1.6, 0, 6.2832); g.fill(); }
      if (L.kind === "house") oldTruck(g, hw + 2, 0, ["#5aa9a6", "#9a6a8e", "#7b8390"][L.seed % 3]);
      else {
        g.fillStyle = "#e9eef6"; g.beginPath(); g.moveTo(hw + 8, -60); g.lineTo(w - 10, -60); g.lineTo(w - 4, -48); g.lineTo(hw + 2, -48); g.fill();
        g.fillStyle = COL.pink; for (let x = hw + 4; x < w - 6; x += 12) { g.beginPath(); g.moveTo(x, -48); g.lineTo(x + 12, -48); g.lineTo(x + 6, -42); g.fill(); }
        g.fillStyle = "#c9ced6"; g.fillRect(hw + 6, -48, 2, 48); g.fillRect(w - 8, -48, 2, 48);
        g.fillStyle = COL.pink; g.fillRect(hw + 20, -22, 70, 4); g.fillStyle = "#ff8fbf"; g.fillRect(hw + 20, -18, 70, 6); g.fillStyle = "#555"; g.fillRect(hw + 24, -12, 2, 12); g.fillRect(hw + 84, -12, 2, 12);
        g.fillStyle = "#111"; rr(g, w - 30, -34, 14, 34, 2); g.fill(); g.fillStyle = "#444"; g.beginPath(); g.arc(w - 23, -24, 4.5, 0, 6.2832); g.arc(w - 23, -10, 4.5, 0, 6.2832); g.fill();
        g.fillStyle = "#222"; g.fillRect(hw + 2, -18, 12, 3); g.fillRect(hw + 7, -15, 2, 15);
        stringLights(g, hw - 6, w - 4, -70, 6); stringLights(g, hw + 10, w - 20, -86, 8);
        g.strokeStyle = "#2a2a2a"; g.lineWidth = 0.6; g.beginPath(); g.moveTo(w - 50, -86); g.lineTo(w - 50, -74); g.stroke();
        g.fillStyle = COL.turq; g.beginPath(); g.arc(w - 50, -68, 6, 0, 6.2832); g.fill(); for (let k = 0; k < 5; k++) { const a = -1.57 + k * 1.2566; g.fillStyle = [COL.pink, COL.orange, "#fff", COL.purple, COL.pink][k]; g.beginPath(); g.moveTo(w - 50 + Math.cos(a - 0.35) * 5, -68 + Math.sin(a - 0.35) * 5); g.lineTo(w - 50 + Math.cos(a) * 11, -68 + Math.sin(a) * 11); g.lineTo(w - 50 + Math.cos(a + 0.35) * 5, -68 + Math.sin(a + 0.35) * 5); g.fill(); }
      }
      g.strokeStyle = "rgba(200,206,214,.7)"; g.lineWidth = 0.6; for (let x = 0; x < w; x += 4) { g.beginPath(); g.moveTo(x, -22); g.lineTo(x + 4, -16); g.moveTo(x + 4, -22); g.lineTo(x, -16); g.stroke(); }
      g.fillStyle = "#c9ced6"; g.fillRect(0, -23, w, 1.4); for (let x = 0; x <= w; x += 46) g.fillRect(x, -24, 2, 24);
    } else if (L.kind === "construction") {
      g.fillStyle = "#6b4e3a"; g.beginPath(); g.moveTo(20, 0); g.quadraticCurveTo(70, -44, 120, 0); g.fill();
      g.fillStyle = "#e46a10"; g.fillRect(130, -40, 54, 22); g.fillStyle = "#1d1b23"; rr(g, 126, -18, 62, 14, 7); g.fill(); g.fillStyle = "#444"; for (let x = 132; x < 186; x += 8) { g.beginPath(); g.arc(x, -11, 3, 0, 6.2832); g.fill(); }
      g.fillStyle = "#2a2a3a"; g.fillRect(166, -38, 14, 12); g.strokeStyle = "#e46a10"; g.lineWidth = 6; g.lineCap = "round"; g.beginPath(); g.moveTo(140, -36); g.lineTo(110, -78); g.lineTo(84, -52); g.stroke();
      g.fillStyle = "#e46a10"; g.beginPath(); g.moveTo(80, -56); g.lineTo(92, -48); g.lineTo(78, -40); g.fill();
      signBoard(g, w - 88, -110, 80, 50, { name: "FUTURE SITE", tagline: "Another ice house", colors: ["#ffffff", "#000000", COL.orange] });
      g.fillStyle = "#c9ced6"; g.fillRect(w - 50, -60, 3, 60);
      g.fillStyle = "rgba(255,106,11,.55)"; for (let x = 0; x < w; x += 5) g.fillRect(x, -30, 2.5, 30); g.fillStyle = COL.orange; g.fillRect(0, -31, w, 2); g.fillRect(0, -2, w, 2);
    } else {   // vacant: weeds, a palm, a for-sale sign
      g.fillStyle = "#2c4a32"; for (let x = 0; x < w; x += 3) { const hh = 3 + r() * 8; g.fillRect(x, -hh, 1.4, hh); }
      palm(g, w * 0.55, 0, 150, r);
      g.fillStyle = "#fff"; rr(g, 10, -44, 40, 22, 2); g.fill(); g.fillStyle = COL.pink; g.font = `900 9px ${FONT}`; g.textAlign = "center"; g.fillText("SE VENDE", 30, -30); g.fillStyle = "#c9ced6"; g.fillRect(28, -22, 3, 22);
    }
    if (season && L.kind !== "vacant") { papelPicado(g, 4, w - 4, L.kind === "construction" ? -64 : -136); marigolds(g, 10, 0, 4); marigolds(g, w - 34, 0, 4); }
  }
  // back billboards (parallax): name + tagline on a lit board on two poles
  function drawBillboard(g, s, w, h) {
    const bw = w, bh = h * 0.56, x = 0, y = 0;
    g.fillStyle = "#2a1d3a"; g.fillRect(bw * 0.25 - 3, bh, 6, h - bh); g.fillRect(bw * 0.75 - 3, bh, 6, h - bh);
    g.fillStyle = "#3a2d4a"; g.fillRect(-4, bh + 2, bw + 8, 4); for (let i = 0; i < 3; i++) { g.fillStyle = "#3a2d4a"; g.fillRect(bw * (0.2 + i * 0.3), -8, 2, 8); g.fillRect(bw * (0.2 + i * 0.3) - 4, -10, 10, 3); }
    g.fillStyle = s.colors[0]; g.fillRect(x, y, bw, bh); g.strokeStyle = "#ffffff"; g.lineWidth = 3; g.strokeRect(x + 1.5, y + 1.5, bw - 3, bh - 3);
    g.textAlign = "center"; g.textBaseline = "middle";
    if (s.draw) s.draw(g, bw, bh);   // a stage's own board art (San Antonio: Chisme's App Store goal)
    else if (s.house) {
      g.fillStyle = "#ffffff"; fitText(g, s.name, bw - 24, bh * 0.3); g.fillText(s.name, bw / 2, bh * 0.36);
      fitText(g, s.tagline, bw * 0.6, bh * 0.26); const tw = g.measureText(s.tagline).width + 20;
      g.fillStyle = s.colors[2]; rr(g, bw / 2 - tw / 2, bh * 0.56, tw, bh * 0.3, bh * 0.15); g.fill(); g.beginPath(); g.moveTo(bw / 2 - tw / 2 + 10, bh * 0.82); g.lineTo(bw / 2 - tw / 2 + 4, bh * 0.95); g.lineTo(bw / 2 - tw / 2 + 20, bh * 0.84); g.fill();
      g.fillStyle = "#000"; g.fillText(s.tagline, bw / 2, bh * 0.715);
    } else {
      g.fillStyle = s.colors[2]; g.fillRect(x + 3, bh * 0.72, bw - 6, bh * 0.28 - 3);
      // v49.27: two high-contrast lines beat shrinking a long business name to tiny type.
      const lines = (text) => { const words = text.split(/\s+/); let a = "", b = ""; for (const w of words) { if (a.length < text.length / 2) a += (a ? " " : "") + w; else b += (b ? " " : "") + w; } return b ? [a, b] : [a]; };
      g.fillStyle = "#100c1c"; g.fillRect(5, 8, bw - 10, bh - 16);
      const names = lines(s.name), tag = lines(s.tagline); g.fillStyle = "#ffffff";
      names.forEach((line, i) => { fitText(g, line, bw - 22, 23); g.fillText(line, bw / 2, bh * 0.25 + i * 25); });
      tag.forEach((line, i) => { fitText(g, line, bw - 22, 15, "800", SANS); g.fillText(line, bw / 2, bh * 0.72 + i * 17); });
    }
    for (let i = 0; i < 3; i++) drawGlow(g, bw * (0.2 + i * 0.3) + 1, 0, 26, "#ffffff", 0.22);
  }

  // ---------------------------------------------------------------- the game
  function mount(el, ctx) {
    ctx = ctx || {};
    const reduced = () => { try { return ctx.reducedMotion ? !!ctx.reducedMotion() : matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } };
    const season = (() => { try { return !!(root.__chismeSeason && root.__chismeSeason.on); } catch (e) { return false; } })();
    const st = load();
    const appMuted = () => { try { return localStorage.getItem("chisme-feed-sound") === "off"; } catch (e) { return false; } };   // Settings → ChismeTV sound, the app's one sound switch
    let muted = st.muted === null ? appMuted() : st.muted;
    let voiceT = 0; // v49.26: monotonic sim clock (world T resets between runs)
    const audio = makeAudio(() => voiceT * 1000); audio.setMuted(muted);
    const timers = new Set(); // v49.26: mount-owned delayed effects
    function later(fn, ms) { const id = setTimeout(() => { timers.delete(id); if (alive) fn(); }, ms); timers.add(id); return id; }
    function clearLater() { for (const id of timers) clearTimeout(id); timers.clear(); }
    const spoken = [];
    const sayLine = (text, lang, o) => { const ok = audio.say(text, lang, o); if (ok) { spoken.push(text); if (spoken.length > 60) spoken.shift(); } return ok; };
    el.innerHTML = `
      <div class="lr-wrap no-swipe">
        <canvas class="lr-cv no-swipe" role="img" aria-label="Puro Pinche Lowrider game screen. Hold anywhere to charge the hydraulics, let go to hop, and tap again right before you land."></canvas>
        <div class="lr-ov" aria-live="polite"></div>
        <div class="lr-toasts" aria-live="polite"></div>
      </div>
      <div class="lr-controls" role="group" aria-label="Game controls">
        <button type="button" class="lr-cbtn" data-act="pause" aria-label="Pause"><span aria-hidden="true">❚❚</span></button>
        <button type="button" class="lr-cbtn" data-act="sound" aria-pressed="true"></button>
      </div>
      <p class="lr-note">Hold to charge the hydraulics, let go to hop, tap right before you land. Feria is earned only by playing (nothing to buy with money) and unlocks rides and paint. Your progress stays on this phone.</p>
      <p class="lr-credit">An original game made for Chisme. The rides are only inspired by classic lowriders (no real makes or badges), every business is made up or a parody, and the San Antonio landmarks are our own cartoons.</p>`;
    const $ = (s) => el.querySelector(s);
    const wrap = $(".lr-wrap"), cv = $(".lr-cv"), ov = $(".lr-ov"), toasts = $(".lr-toasts"), g = cv.getContext("2d", { alpha: false });
    const pauseBtn = $('[data-act="pause"]'), soundBtn = $('[data-act="sound"]');
    const BADGE = `<svg class="gfs-lr-car" viewBox="0 0 40 16" aria-hidden="true" focusable="false"><path d="M2 11 Q1 7 4 6.5 L12 6 L16 2.5 L27 2.5 L30 6 L37 6.5 Q39.5 7 39 11 Z" fill="#FF1A7F"/><circle cx="9" cy="12" r="3" fill="#000"/><circle cx="9" cy="12" r="1.6" fill="#fff"/><circle cx="32" cy="12" r="3" fill="#000"/><circle cx="32" cy="12" r="1.6" fill="#fff"/></svg>`;
    const FS = root.ChismeJuegos && root.ChismeJuegos.fullscreen;
    const fs = FS ? FS(el, { title: TITLE, badgeClass: "gfs-lr", badge: `${BADGE}<span class="gfs-lr-t" aria-hidden="true">Puro Pinche <b>Lowrider</b></span>`, barItems: [pauseBtn, soundBtn],
      onEnter: () => fit(), onResize: () => fit(), onExit: () => { if (!alive) return; if (ovKind === "loading") { ++stageRequest; showTitle(); } if (mode === "run" || mode === "paused" || mode === "crash") endRun("quit"); fit(); }, onLeave: () => { if (!alive) return; if (ovKind === "loading") { ++stageRequest; showTitle(); } pause(); fit(); } }) : { enter() {}, exit() {}, on: false };

    // ---- stages (STAGES; a stage file registers lib.stages[id] = { back, lot, billboards, traffic, picks, … })
    const native = () => !!root.ChismeNative || /ChismeNative/i.test((root.navigator && root.navigator.userAgent) || "");   // the store app: no donation asks (Apple's rules)
    let stage = STAGES.find((s) => s.id === st.stage) || STAGES[0], SM = null, SX = null, stageLoading = null;
    // v49.26: load both SA modules before install; failed requests can be retried.
    let stageRequest = 0; const stageCancels = new Set(); // v49.26: detach pending script handlers on destroy
    function loadStage(s) {
      if (!s.file) return Promise.resolve(null);
      if (lib.stages[s.id] && lib.saChase) return Promise.resolve(lib.stages[s.id]);
      if (stageLoading) return stageLoading;
      const script = (file, ready) => ready() ? Promise.resolve() : new Promise((ok, no) => {
        const sc = document.createElement("script"); sc.src = "/static/" + file + (BUILD ? "?v=" + encodeURIComponent(BUILD) : ""); sc.async = true;
        const done = (err) => { stageCancels.delete(cancel); sc.onload = sc.onerror = null; sc.remove(); err ? no(err) : ok(); };
        const cancel = () => done(new Error("stage cancelled")); stageCancels.add(cancel);
        sc.onload = () => done(ready() ? null : new Error(file)); sc.onerror = () => done(new Error(file)); document.head.appendChild(sc);
      });
      stageLoading = script(s.file, () => !!lib.stages[s.id]).then(() => { if (!alive) throw new Error("stage cancelled"); return script("lowrider-sa-chase.js", () => !!lib.saChase); })
        .then(() => lib.stages[s.id]).finally(() => { stageLoading = null; });
      return stageLoading;
    }
    function useStage(id) {
      const s = STAGES.find((x) => x.id === id) || STAGES[0], request = ++stageRequest;
      return loadStage(s).then((m) => { if (!alive || request !== stageRequest || (mode !== "title" && ovKind !== "loading")) return;
        stage = s; SM = s.file ? m : null; SX = SM && SM.install ? SM.install(kernel()) : null; if (st.stage !== s.id) { st.stage = s.id; save(st); }
        lotI = 0; signI = { shop: 0, billboard: 0 }; houseIn = 2; resetWorld(); buildBack(); lotCache.clear(); bbCache.clear(); camX = car.x - carSX; spawnAhead(); draw(); return s; });
    }
    const H = { drawCar, rr, lg, rg, fitText, outlined, hexA, shade, drawGlow, drawPerson, makePerson, bubble, papelPicado, marigolds, palm, glowWin, stucco, signBoard, awning, stringLights, drawBillboard, rng, COL, FONT, SANS, TITLE_FONT, clamp, lerp };

    // ---- sizing: a 480-unit-wide view on phones (more road shows on wide screens), drawn at devicePixelRatio
    let cssW = 360, cssH = 600, dpr = 1, S = 1, LW = 480, LH = 640, GY = 490, K = 1, carSX = 24;
    let skyC = null, skyH = 0, skylineC = null, midC = null;
    const lotCache = new Map(), bbCache = new Map(), bbLog = [];
    function mk(wl, hl) { const c = document.createElement("canvas"); c.width = Math.max(1, Math.ceil(wl * K)); c.height = Math.max(1, Math.ceil(hl * K)); const x = c.getContext("2d"); x.setTransform(K, 0, 0, K, 0, 0); return [c, x]; }
    function fit() {
      const oldGY = GY; // v49.26: keep existing actors on the sidewalk after rotation
      const r = wrap.getBoundingClientRect(); cssW = Math.max(240, Math.round(r.width)); cssH = Math.max(320, Math.round(r.height));
      dpr = Math.min(3, root.devicePixelRatio || 1);
      const bw = Math.round(cssW * dpr), bh = Math.round(cssH * dpr);
      if (cv.width !== bw || cv.height !== bh) { cv.width = bw; cv.height = bh; }
      cv.style.width = cssW + "px"; cv.style.height = cssH + "px";
      S = Math.min(cssW / 430, cssH / 600); LW = cssW / S; LH = cssH / S; GY = LH - Math.max(150, Math.min(210, (LH - 640) * 0.4 + 150)); K = dpr * S; wrap.style.setProperty("--lr-toast-top", `${104 * S}px`); carSX = 18 + Math.max(0, LW - 430) * 0.18;
      const moved = new Set([...people, ...dogs, ...bubbles.map((b) => b.p)]); for (const p of moved) p.y += GY - oldGY;
      buildBack(); lotCache.clear(); bbCache.clear(); camX = car.x - carSX; draw();
    }
    function buildBack() {
      skyH = Math.ceil(GY - 40); let x;
      if (SM && SM.back) { [skyC, x] = mk(LW, skyH); SM.back.sky(x, LW, skyH, H); [skylineC, x] = mk(1000, 260); SM.back.skyline(x, H); [midC, x] = mk(1000, 170); SM.back.mid(x, H); return; }
      [skyC, x] = mk(LW, skyH);
      x.fillStyle = lg(x, 0, 0, 0, skyH, [[0, "#0e0424"], [0.3, "#250a4a"], [0.55, "#5a1868"], [0.75, "#a8246f"], [0.88, "#f0406a"], [1, "#ff7a45"]]); x.fillRect(0, 0, LW, skyH);
      const rs = rng(77); for (let i = 0; i < 70; i++) { const y = rs() * skyH * 0.55; x.fillStyle = `rgba(255,255,255,${0.25 + rs() * 0.6 * (1 - y / (skyH * 0.55))})`; x.fillRect(rs() * LW, y, 1.3, 1.3); }
      const sx = LW * 0.7, sy = skyH - 165, sr = 72;
      x.fillStyle = rg(x, sx, sy, 0, sr * 2.6, [[0, "rgba(255,120,140,.45)"], [1, "rgba(255,90,120,0)"]]); x.fillRect(0, 0, LW, skyH);
      x.save(); x.beginPath(); x.arc(sx, sy, sr, 0, 6.2832); x.clip();
      x.fillStyle = lg(x, 0, sy - sr, 0, sy + sr, [[0, "#ff8fb8"], [0.5, "#ff5a7a"], [1, "#ff6a2b"]]); x.fillRect(sx - sr, sy - sr, sr * 2, sr * 2);
      for (let i = 0; i < 6; i++) { x.fillStyle = "rgba(168,36,111,.9)"; x.fillRect(sx - sr, sy + 6 + i * 10, sr * 2, 2 + i * 1.1); }
      x.restore();
      const r = rng(11); for (let i = 0; i < 9; i++) { const cy = skyH * (0.35 + r() * 0.5), cx = r() * LW, cw = 60 + r() * 160; x.fillStyle = `rgba(${r() < 0.5 ? "255,150,190" : "190,120,230"},${0.12 + r() * 0.18})`; rr(x, cx, cy, cw, 3 + r() * 4, 3); x.fill(); }
      // far skyline strip (parallax 0.06), a 1000-unit tile
      [skylineC, x] = mk(1000, 260);
      const r2 = rng(5); x.fillStyle = "#3d1658";
      for (let bx = 0; bx < 1000;) { const w = 18 + r2() * 46, h = 30 + r2() * 120; if (bx + w > 1000) break; x.fillRect(bx, 260 - h, w, h); if (r2() < 0.3) x.fillRect(bx + w * 0.4, 260 - h - 10, 3, 10);
        x.fillStyle = "rgba(255,170,210,.55)"; for (let wy = 260 - h + 6; wy < 252; wy += 7) for (let wx = bx + 4; wx < bx + w - 4; wx += 6) if (r2() < 0.22) x.fillRect(wx, wy, 2, 2.4); x.fillStyle = "#3d1658"; bx += w + r2() * 8; }
      x.fillRect(612, 60, 7, 200); x.beginPath(); x.ellipse(615.5, 62, 15, 7, 0, 0, 6.2832); x.fill(); x.fillRect(609, 48, 13, 9); x.fillRect(614.5, 14, 2, 36);   // the tall tower with the pod
      drawGlow(x, 615.5, 15, 6, "#ff4a6a", 0.9);
      x.beginPath(); x.arc(330, 230, 26, 3.14, 6.28); x.fill(); x.fillRect(304, 230, 52, 30);
      // mid layer (parallax 0.22): live oaks, rooftops, a water tower
      [midC, x] = mk(1000, 170);
      const r3 = rng(9); x.fillStyle = "#22092f";
      for (let tx = 0; tx < 1000; tx += 26 + r3() * 30) { const tr = 16 + r3() * 22; x.beginPath(); x.arc(tx, 170 - tr * 0.8, tr, 0, 6.2832); x.arc(tx + tr * 0.8, 170 - tr * 0.6, tr * 0.8, 0, 6.2832); x.fill(); }
      x.fillRect(0, 150, 1000, 20);
      x.fillRect(720, 70, 4, 100); x.fillRect(748, 70, 4, 100); x.beginPath(); x.ellipse(736, 64, 26, 16, 0, 0, 6.2832); x.fill(); x.fillRect(733, 40, 6, 12);
      for (let hx = 80; hx < 980; hx += 150 + r3() * 90) { x.beginPath(); x.moveTo(hx, 150); x.lineTo(hx + 30, 120); x.lineTo(hx + 60, 150); x.fill(); x.fillRect(hx + 4, 135, 52, 20); }
    }

    // ---- state
    const car = { x: 0, y: 0, vy: 0, v: 260, sR: 0, sF: 0, vR: 0, vF: 0, ang: 0, rot: 0, charge: 0, charging: false, air: false, tapped: false, tapT: 0, launchC: 0, pend: null, hurt: 0, scrape: 0, bob: 0 };
    const P = () => { if (garage.open) { const c = gCar(); return paintFor(c, garage.preview || st.carPaint[c.id] || c.paint); } return paintFor(curCar(), st.equip.paint); };
    const garage = { open: false, preview: null, car: null, t: 0 };
    let inputLagMs = 0, inputDownAt = 0, held = false, bufferedAt = -9, groundedAt = 0, prevCam = 0, prevX = 0, prevY = 0, god = null, godUi = null, godSnapshot = null; // v49.27
    let evOn = true, mode = "title", T = 0, camX = 0, run = null, ev = null, shake = 0, frozen = false, auto = true, zoom = 1, lastGrade = null, gradeCounts = { perfect: 0, puro: 0, ay: 0, scraped: 0 };
    let popList = [], bubbleList = [], finishTitle = false; // v49.26: drawn screen bounds for tests
    let obs = [], coins = [], picks = [], people = [], dogs = [], props = [], lots = [], bbs = [], parts = [], pops = [], bubbles = [];
    let nextObs = 0, lotEnd = -400, bbEnd = -300, houseIn = 2, signI = { shop: 0, billboard: 0 }, lotI = 0, hold = 0, lastCheer = -9, events = { abuela: 0, chancla: 0 };
    const rand = Math.random;
    function resetWorld() {
      clearLater(); toasts.replaceChildren(); lotCache.clear(); bbCache.clear(); // v49.26: discard callbacks and cached canvases from the previous world
      held = false; bufferedAt = -9; groundedAt = 0;
      car.x = 0; car.y = 0; car.vy = 0; car.v = 260; car.sR = car.sF = car.vR = car.vF = 0; car.ang = 0; car.charge = 0; car.charging = false; car.air = false; car.tapped = false; car.pend = null; car.hurt = 0; car.scrape = 0;
      obs = []; coins = []; picks = []; people = []; dogs = []; props = []; lots = []; bbs = []; parts = []; pops = []; bubbles = []; ev = null; hold = 0;
      lotEnd = -carSX - 300; bbEnd = -carSX * 0.35 - 200; nextObs = 900; camX = car.x - carSX; T = 0; lastCheer = -9; // v49.26: cheers use the reset world clock
    }
    resetWorld();

    // ---- the world ahead (lots, billboards, people, obstacles)
    function addLot(want) {
      if (SM) {   // the stage hands out its own lots (landmarks with a name tag, parody stores, taquerías, fillers)
        const L = SM.lot(lotI++, rand, want); L.x = lotEnd + (L.gap != null ? L.gap : 8); L.seed = (lotI * 7919 + 13) % 100000; lots.push(L); lotEnd = L.x + L.w;
        const r = rng(L.seed + 3); for (let i = 0; i < (L.crowd || 0); i++) people.push(makePerson(r, L.x + 20 + r() * (L.w - 40), GY - 51 + r() * 3));
        if (L.pole !== false && lotI % 2 === 0) props.push({ kind: "pole", x: L.x - 3 });
        return;
      }
      const kind = LOT_BAG[lotI++ % LOT_BAG.length], w = LOTS[kind], x = lotEnd + 6 + (rand() < 0.3 ? 40 : 0);
      let sign = null;
      if (["taco", "tires", "icehouse", "pinata", "barber"].includes(kind)) sign = SIGNS.find((s) => s.slot === "store" && s.kind === kind);
      else if (kind === "shop") { const list = SIGNS.filter((s) => s.slot === "store" && s.kind === "shop"); sign = list[signI.shop++ % list.length]; }
      const L = { kind, w, x, seed: (lotI * 7919 + 13) % 100000, sign };
      lots.push(L); lotEnd = x + w;
      const r = rng(L.seed + 3), sy = GY - 51;
      const crowd = { taco: 3, icehouse: 3, party: 4, pinata: 1, shop: 1, barber: 1, corner: 2, mural: 2, house: 0, construction: 0, vacant: 1, tires: 1 }[kind] || 0;
      for (let i = 0; i < crowd; i++) {
        if (kind === "party" || kind === "icehouse") people.push(makePerson(r, x + (kind === "party" ? 140 : 40) + i * (kind === "party" ? 28 : 44) + r() * 10, GY - 60, { s: 0.86, dance: kind === "party" }));
        else people.push(makePerson(r, x + 20 + r() * (w - 40), sy + r() * 3));
      }
      if (kind === "house" && r() < 0.7) dogs.push({ x: x + 30 + r() * 60, y: GY - 50, run: 0, done: false, col: ["#7a4a2a", "#e9e5ef", "#2a2a2a"][(r() * 3) | 0] });
      if (lotI % 2 === 0) props.push({ kind: "pole", x: x - 3 });
    }
    function addBillboard() {
      const x = bbEnd + 330 + rand() * 260;
      let s;
      const own = sponsors !== SPONSOR_SLOTS ? sponsors.map((q) => ({ ...q, tagline: q.line })) : SM && SM.billboards ? SM.billboards(native()) : null;   // a stage's own boards (San Antonio: Chisme's App Store goal; none in the store app)
      if (--houseIn <= 0 || (own && !own.length)) { s = SIGNS.find((q) => q.house); houseIn = 3 + (rand() < 0.5 ? 1 : 0); }
      else { const list = own || SPONSOR_SLOTS.filter((q) => !q.house).map((q) => ({ ...q, tagline: q.line })); s = list[signI.billboard++ % list.length]; }
      bbs.push({ x, s, w: 196, h: 236 }); bbEnd = x + 196; bbLog.push(s.name); if (bbLog.length > 60) bbLog.shift();
    }
    const difficulty = () => (run ? clamp(run.meters / 1900 + (run.boost || 0), 0, 1) : 0.08);   // boost: a harder lap (Otra vuelta)
    const cruise = (d) => 262 + 215 * d;
    function addObstacles() {
      const d = difficulty();
      if (ev && (ev.stop || ev.type === "abuela" || ev.type === "party")) { nextObs += cruise(d) * 3.5; return; } // v49.27
      if (SX && SX.obstacle && SX.obstacle(d)) return;   // a stage's own (San Antonio: oncoming traffic)
      const kinds = Object.keys(OBST).filter((k) => OBST[k].min <= d + 0.001);
      const kind = kinds[(rand() * kinds.length) | 0], O = OBST[kind];
      const o = { kind, vx: kind === "copcar" && rand() < 0.5 ? -40 - rand() * 40 : 0, x: nextObs, w: O.w, h: O.h, pit: !!O.pit, soft: !!O.soft, hit: false, cleared: false, knock: null };
      obs.push(o);
      if (kind === "rails") props.push({ kind: "xing", x: nextObs + 10 });
      if (run && SX && SX.afterObstacle && SX.afterObstacle(o)) {}
      else if (run && rand() < 0.38) { const apex = 120 + rand() * 70; for (let i = 0; i < 5; i++) { const u = (i - 2) / 2.4; coins.push({ x: o.x + o.w / 2 + (i - 2) * 40, h: apex * (1 - u * u) + 40, got: false }); } }
      const gapT = 3.1 + rand() * 1.2; // v49.27: never pair hard obstacles inside a hop
      nextObs += cruise(d) * gapT + o.w + (run ? 0 : 120);
    }
    function spawnAhead() {
      while (lotEnd < camX * 0.6 + LW + 300) addLot();
      while (bbEnd < camX * 0.35 + LW + 300) addBillboard();
      if (mode === "run" || mode === "title") while (nextObs < camX + LW + 320) { if (hold && nextObs < hold) { nextObs = hold; continue; } addObstacles(); }
      if (SX && SX.ahead) SX.ahead();
      const gone = camX - 320;
      lots = lots.filter((L) => { const keep = L.x + L.w > camX * 0.6 - 320; if (!keep) lotCache.delete(L); return keep; });
      bbs = bbs.filter((b) => { const keep = b.x + b.w > camX * 0.35 - 60; if (!keep) bbCache.delete(b); return keep; });
      obs = obs.filter((o) => o.x + o.w > gone); coins = coins.filter((c) => c.x > gone && !c.got); picks = picks.filter((c) => c.x > gone && !c.got); people = people.filter((p) => p.x > gone); dogs = dogs.filter((d) => d.x > gone - 200); props = props.filter((p) => p.x > gone - 400);
    }

    // ---- juice
    function burst(x, y, n, kind, o = {}) {
      if (reduced()) n = Math.ceil(n / 3);
      for (let i = 0; i < n && parts.length < 420; i++) {
        const a = (o.a != null ? o.a : -1.57) + (rand() - 0.5) * (o.spread || 3.14), sp = (o.sp || 160) * (0.4 + rand() * 0.8);
        parts.push({ x, y, vx: Math.cos(a) * sp + (o.vx || 0), vy: Math.sin(a) * sp, life: 0, max: (o.life || 0.6) * (0.6 + rand() * 0.6), kind, col: o.col || (kind === "confetti" ? [COL.pink, COL.turq, COL.orange, "#fff", COL.purple][(rand() * 5) | 0] : null), s: o.s || 1, a: rand() * 6.28, va: (rand() - 0.5) * 14 });
      }
    }
    const shakeIt = (a) => { if (!reduced()) shake = Math.max(shake, a); };
    function pop(text, o = {}) { if (o.big && pops.filter((p) => p.big).length >= 2) pops.splice(pops.findIndex((p) => p.big), 1); pops.push({ text, x: o.x, y: o.y, t: 0, life: o.life || 1.1, col: o.col || "#fff", size: o.size || 22, big: !!o.big, icon: o.icon || null, rise: o.rise == null ? 40 : o.rise, edge: o.edge || "#000" }); if (pops.length > 14) pops.splice(pops.findIndex((p) => !p.big), 1); }
    function crowd(mood, power, text) {
      const vis = people.filter((p) => p.x - camX > 0 && p.x - camX < LW);
      for (const p of vis) { p.react = 0.9 + power * 0.5; p.mood = mood; }
      if (text && vis.length) { const p = vis[(rand() * vis.length) | 0]; bubbles.push({ p, text, t: 0, life: 1.6 }); if (bubbles.length > 8) bubbles.pop(); }
    }
    function toast(title, sub) {
      const d = document.createElement("div"); d.className = "lr-toast"; d.setAttribute("role", "status");
      d.innerHTML = `<span class="lr-toast-ic" aria-hidden="true"></span><span><b>${esc(title)}</b><small>${esc(sub)}</small></span>`;
      toasts.replaceChildren(d); d.title = sub; d.setAttribute("aria-label", title + ". " + sub); later(() => d.classList.add("out"), 1700); later(() => d.remove(), 2000); // v49.26: compact, short trophy notice
    }
    function unlock(id) {
      if (st.ach[id]) return; const a = ACH.find((x) => x.id === id); if (!a) return;
      st.ach[id] = Date.now(); save(st); toast("Trophy: " + a.name, a.desc); audio.fx.tier(2);
    }

    // ---- a run
    function startRun(opt) {
      if (!alive) return; // v49.26: lazy loads may finish after unmount
      audio.unlock(); fs.enter();
      if (!st.howto) { showHowto(true); return; }
      if (stage.file && !SM) { overlay(`<div class="lr-card"><p class="lr-sub"><span class="lr-spin" aria-hidden="true"></span> Loading ${esc(stage.name)}…</p></div>`, "loading");
        useStage(stage.id).then((s) => { if (s) startRun(opt); }, () => { if (!alive) return; toast("Couldn't load " + stage.name, "Cruising the Boulevard instead."); useStage("blvd").then((s) => { if (s) startRun(opt); }); }); return; }
      mode = "run"; auto = false; resetWorld(); garage.open = false; garage.preview = null;
      run = { score: 0, meters: 0, feria: 0, streak: 0, tier: 0, bestTier: 0, perfects: 0, perfectRow: 0, hops: 0, lives: 3, cleanFrom: 0, t: 0, abuelas: 0, dodges: 0, clears: 0, maxStreak: 0, nextAbuela: EVENTS.abuela.first + rand() * 6, nextChancla: EVENTS.chancla.first + rand() * 6, over: false,
        stage: stage.id, lap: (opt && opt.lap) || 1, boost: 0, fuel: 1, out: false, nextGas: 1e12, nextTrail: 1e9, trails: 0, salutes: 0, cops: 0, traffic: 0, picks: { gas: 0, soda: 0, taco: 0 } };
      run.cleared = {}; run.god = !!(god && god.on); if (run.god) sandboxGod(); // v49.27
      if (SX && SX.runStart) SX.runStart(run);
      gradeCounts = { perfect: 0, puro: 0, ay: 0, scraped: 0 }; lastGrade = null;
      overlay(""); audio.intensity(0); audio.tempo(1); audio.muffle(false); if (!muted) audio.startMusic();
      try { root.dispatchEvent(new CustomEvent("chisme-game-play", { detail: "lowrider" })); } catch (e) {}
      if (document.hidden) { pause(); audio.setMuted(true); } // v49.26: a lazy stage can finish loading in the background
      ctrl(); kick();
    }
    function endRun(reason) {
      if (!run || run.over) return; run.over = true;
      car.charging = false; audio.fx.pumpStop();
      const bonus = Math.floor(run.meters / 100); run.feria += bonus;
      if (!run.god) { syncWallet(); st.feria += run.feria; st.totals.runs++; st.totals.meters += Math.round(run.meters); st.totals.feria += run.feria;
      }
      const newBest = !run.god && run.score > st.best; if (newBest) st.best = Math.round(run.score);
      const rec = { score: Math.round(run.score), meters: Math.round(run.meters), fin: reason === "finish", lap: run.lap, feria: run.feria, perfects: run.perfects, combo: TIERS[run.bestTier].x, car: st.equip.car, paint: st.equip.paint, stage: run.stage, at: Date.now(), week: isoWeek(Date.now()) };
      const rank = run.god ? null : BOARD.submit(st, rec);
      restoreGod();
      save(st);
      mode = "over"; audio.stopMusic(); audio.muffle(false); audio.tempo(1);
      showOver(rec, newBest, rank, bonus, reason);
      ctrl();
    }
    function pause() {
      try { if (root.speechSynthesis) speechSynthesis.cancel(); } catch (e) {} // v49.26
      if (mode !== "run") { if (mode === "title" || mode === "over") audio.stopMusic(); return; }
      mode = "paused"; car.charging = false; audio.fx.pumpStop(); audio.stopMusic();
      overlay(`<div class="lr-card lr-pausecard"><h3 class="lr-h">Paused</h3><p class="lr-sub">${esc(curCar().name)} is idling. Take your time.</p>
        <button type="button" class="lr-btn lr-go" data-act="resume">▶ Resume</button>
        <div class="lr-row"><button type="button" class="lr-btn lr-turq" data-act="restart">Restart</button><button type="button" class="lr-btn lr-ghost" data-act="quit">End run</button></div>${donateBtn()}</div>`);
      ctrl();
    }
    function resume() { if (mode !== "paused") return; fs.enter(); mode = "run"; overlay(""); if (!muted) audio.startMusic(); ctrl(); kick(); }

    // ---- input: HOLD = charge, RELEASE = hop, TAP in the air = set the landing
    function press() {
      if (mode !== "run") return;
      audio.unlock();
      held = true; // v49.27: landing taps are consumed once, including the 150ms pre-landing buffer
      if (car.pend) { resolve(gradeFor(T - car.pend.T, true)); if (T - groundedAt > 0.1 || !held) return; }
      if (car.air && T - groundedAt > 0.1) { if (tLand() <= 0.15) bufferedAt = T; if (!car.tapped) { car.tapped = true; car.tapT = T; audio.fx.click(); } return; }
      if (!car.charging) { car.charging = true; car.charge = 0; inputLagMs = inputDownAt ? Math.max(0, performance.now() - inputDownAt) : 0; audio.fx.pumpStart(); }
    }
    function release() { held = false; if (mode !== "run" || !car.charging) return; launch(); }
    function launch() {
      const ph = curCar().phys, c = Math.max(0.12, car.charge);
      car.charging = false; audio.fx.pumpStop();
      car.air = true; groundedAt = -9; car.tapped = false; car.pend = null; car.launchC = c; car.vy = ph.vMin + (ph.vMax - ph.vMin) * c; car.y = 0.5;
      car.vF += 260 + 380 * c; car.vR += 120 + 160 * c;
      audio.fx.pssh(c);
      if (run) { run.hops++; st.totals.hops++; if (st.totals.hops >= 1000) unlock("addict"); }
      if (run && ev && ev.press) ev.press();
      if (c > 0.55) burst(car.x - 2, GY - 6, 10 + c * 14, "spark", { a: -2.6, spread: 1.2, sp: 260, vx: -car.v * 0.4, life: 0.5 });
      burst(car.x + R64.rear, GY - 1, 5, "dust", { a: -2.4, spread: 1.4, sp: 60, life: 0.7, s: 1.2 });
    }
    const tLand = () => (car.air ? (car.vy + Math.sqrt(Math.max(0, car.vy * car.vy + 2 * curCar().phys.g * car.y))) / curCar().phys.g : 0);
    function land() {
      groundedAt = T; // v49.27: 100ms grace after touchdown
      const imp = -car.vy; car.vy = 0; car.air = false; car.y = 0;
      car.vF -= imp * 0.16; car.vR -= imp * 0.2;
      shakeIt(clamp(imp / 90, 1.5, 9)); audio.fx.thunk(clamp(imp / 900, 0.3, 1));
      burst(car.x + R64.rear, GY - 2, 6, "dust", { a: -2.8, spread: 1.6, sp: 90, life: 0.8, s: 1.4 }); burst(car.x + R64.front, GY - 2, 6, "dust", { a: -0.4, spread: 1.6, sp: 90, life: 0.8, s: 1.4 });
      if (!run) { if (auto) resolveAuto(); return; }
      if (bufferedAt >= T - 0.15) { car.tapped = true; car.tapT = bufferedAt; } bufferedAt = -9;
      if (car.tapped) resolve(gradeFor(T - car.tapT, false)); else car.pend = { T, until: T + WIN.late };
    }
    function resolveAuto() { car.pend = null; if (car.launchC > 0.6 && rand() < 0.6) { audio.fx.ding(); crowd(1, 0.6, rand() < 0.4 ? "¡ÓRALE!" : null); } }
    function resolve(grade) {
      car.pend = null; lastGrade = grade; gradeCounts[grade]++;
      if (!run) return;
      const G = GRADES[grade], c = car.launchC, prevTier = run.tier;
      if (grade === "perfect" || grade === "puro") { run.streak++; run.perfectRow = grade === "perfect" ? run.perfectRow + 1 : 0; }
      else if (grade === "ay") { run.streak = Math.max(0, run.streak - 3); run.perfectRow = 0; }
      else { run.streak = 0; run.perfectRow = 0; }
      run.maxStreak = Math.max(run.maxStreak, run.streak);
      run.tier = tierOf(run.streak); run.bestTier = Math.max(run.bestTier, run.tier);
      const tier = TIERS[run.tier], pts = Math.round(G.pts * (0.5 + c) * tier.x);
      let feria = G.feria * tier.f; if (c < 0.3) feria = Math.floor(feria / 2);
      run.score += pts; run.feria += feria;
      if (grade === "perfect") { run.perfects++; st.totals.perfects++; }
      const gx = LW / 2, gy = Math.max(150, GY - 262);
      pop(G.text, { x: gx, y: gy, col: G.color, size: grade === "scraped" ? 34 : 40, big: true, icon: G.icon, life: 1.15, rise: 14 });
      if (pts) pop("+" + num(pts), { x: car.x - camX + 100, y: GY - 100, col: "#ffffff", size: 18, life: 0.9 });
      if (feria) pop("+" + feria + " Feria", { x: car.x - camX + 150, y: GY - 80, col: COL.turq, size: 14, life: 1 });
      if (grade === "perfect") {
        audio.fx.ding(); burst(car.x + 100, GY - 40, 16, "star", { sp: 200, life: 0.7 });
        const big = c > 0.72; crowd(1, big ? 1 : 0.6, big && T - lastCheer > 3.5 ? "¡NO MAMES!" : rand() < 0.35 ? CHEERS[(rand() * (CHEERS.length - 1) + 1) | 0] : null);
        if (big && T - lastCheer > 3.5) { lastCheer = T; sayLine("¡No mames!", "es-MX", { rate: 1.1, pitch: 1.15, gap: 3000 }); }
      } else if (grade === "puro") { crowd(1, 0.3, rand() < 0.2 ? "Damn, that '64 is clean." : null); }
      else if (grade === "ay") { audio.fx.bonk(); burst(car.x + 196, GY - 14, 10, "spark", { a: -0.6, spread: 1.4, sp: 200, life: 0.4 }); crowd(-1, 0.3, rand() < 0.4 ? "¡AY GÜEY!" : null); }
      else { scrapeFx(c); if (c >= 0.8) unlock("ayguey"); }
      if (run.tier > prevTier) {
        pop("x" + tier.x + " COMBO!", { x: gx, y: gy + 46, col: COL.pink, size: 26, big: true, life: 1.3, rise: 8 }); audio.fx.oooh(run.tier >= 3 ? 1 : 0.7); audio.fx.tier(run.tier);
        burst(LW / 2 + camX, GY - 120, 40, "confetti", { sp: 260, spread: 3.14, life: 1.6 }); audio.intensity(run.tier >= 4 ? 3 : run.tier);
        if (run.tier >= 3 && T - lastCheer > 2) { lastCheer = T; crowd(1, 1, "¡NO MAMES!"); sayLine("¡No mames!", "es-MX", { rate: 1.1, pitch: 1.15, gap: 3000 }); }
      } else if (run.tier < prevTier) audio.intensity(run.tier);
      if ((grade === "perfect" || grade === "puro") && run.streak > 0 && run.streak % 10 === 0 && run.lives < 3) { run.lives++; pop("+1 WHEEL · Primo fixed it", { x: LW / 2, y: gy + 84, col: "#fff", size: 15, life: 1.4 }); }
      unlock("first");
      if (run.perfectRow >= 10) unlock("puro");
    }
    function scrapeFx(c) {
      car.vF -= 140; car.scrape = 0.5; car.v *= 0.86; shakeIt(8); audio.fx.skrrt();
      if (run) run.cleanFrom = run.meters;
      crowd(-1, 0.6, WINCES[(rand() * WINCES.length) | 0]);
      later(() => { if (mode === "run" || mode === "crash") sayLine("Damn.", "en-US", { pitch: 0.55, rate: 0.8, volume: 0.55, gap: 2500 }); }, 650);
      pop("Damn.", { x: car.x - camX + 40, y: GY + 30, col: "#c9ced6", size: 13, life: 1.6, rise: 6 });
    }
    function hurt(why, o) {
      if ((god && god.on && god.invincible) || !run || car.hurt > 0 || mode !== "run") return;
      run.streak = 0; run.perfectRow = 0; run.tier = 0; audio.intensity(0); run.cleanFrom = run.meters;
      car.hurt = 1.1; shakeIt(10); burst(o ? o.x + o.w / 2 : car.x + 190, GY - 12, 18, "spark", { a: -1.2, spread: 2, sp: 260, life: 0.5 });
      if (why === "soft") { audio.fx.bonk(); pop("BONK!", { x: car.x - camX + 170, y: GY - 80, col: COL.orange, size: 20 }); car.vF -= 160; car.hurt = 0.5; return; }
      run.lives--; audio.fx.thwap(); audio.fx.skrrt(); car.vF -= 200; car.v *= 0.65;
      crowd(-1, 0.8, WINCES[(rand() * WINCES.length) | 0]);
      pop(why === "chancla" ? "¡LA CHANCLA!" : "OUCH! −1 WHEEL", { x: LW / 2, y: Math.max(130, GY - 236), col: COL.pink, size: 28, big: true, icon: "burst", life: 1.2, rise: 10 });
      if (run.lives <= 0) { mode = "crash"; car.charging = false; audio.fx.pumpStop(); audio.stopMusic(); later(() => { if (mode === "crash") endRun("wrecked"); }, 1300); ctrl(); }
    }

    // ---- events (data in EVENTS): Abuela Crossing, La Chancla
    function startEvent(type, opt = {}) {
      if (ev) return false;
      if (type === "abuela") {
        const x = car.x + 200 + Math.max(260, car.v * 2.4) + 80;
        obs = obs.filter((o) => o.x + o.w < car.x + 200 || o.x > x + 520); coins = coins.filter((c) => c.x < car.x + 200 || c.x > x + 520);
        hold = x + 560; if (nextObs < hold) nextObs = hold;
        ev = { type, x, phase: "warn", t: 0, d: 0 }; props.push({ kind: "abuelasign", x: x - 120 });
        
      } else if (SX && SX.event && !["chancla", "abuela"].includes(type)) {   // a stage's own (San Antonio: the Trail Ride)
        const e = SX.event(type, opt); if (!e) return false; ev = e;
      } else if (type === "chancla") {
        const high = opt.high != null ? opt.high : (events.chancla > 0 && rand() < 0.45);
        obs = obs.filter((o) => o.x + o.w < car.x - 10 || o.x > car.x + 200 + car.v * 2.6 + 200);
        hold = car.x + 200 + car.v * 2.6 + 260; if (nextObs < hold) nextObs = hold;
        ev = { type, high, phase: "warn", t: 0, cx: 0, h: high ? 96 : 21, a: 0, vy: 0, hit: false, dodged: false };
        audio.fx.whoosh();
      }
      events[type]++; return true;
    }
    function updateEvent(dt) {
      if (!ev) return;
      ev.t += dt;
      if (ev.type === "abuela") {
        if (ev.phase === "warn" && ev.t > 0.6) { ev.phase = "cross"; ev.t = 0; audio.tempo(0.62); audio.muffle(true); }
        if (ev.phase === "cross") { ev.d = clamp(ev.t / 3.4, 0, 1); if (ev.d >= 1) { ev.phase = "done"; ev.t = 0; finishAbuela(); } }
        if (ev.phase === "done" && ev.t > 2.2) ev = null;
      } else if (ev.update) { ev.update(dt);
      } else {
        if (ev.phase === "warn" && ev.t > 1.25) { ev.phase = "fly"; ev.t = 0; ev.cx = camX + LW + 40; audio.fx.whoosh(); }
        if (ev.phase === "fly") {
          ev.a += dt * (ev.hit ? 22 : 13);
          if (ev.hit) { ev.cx -= (car.v * 0.2) * dt; ev.vy -= 900 * dt; ev.h += ev.vy * dt; }
          else ev.cx -= 300 * dt;
          if (!ev.hit && run && mode === "run") {
            const inX = ev.cx > car.x + 4 && ev.cx < car.x + 196, lo = ev.h - 10, hi = ev.h + 10, cb = car.y + 7, ct = car.y + 64;
            if (inX && hi > cb && lo < ct && car.hurt <= 0) { ev.hit = true; ev.vy = 420; hurt("chancla"); }
            if (ev.cx < car.x - 30 && !ev.dodged) { ev.dodged = true; run.score += EVENTS.chancla.bonus; run.feria += EVENTS.chancla.feria; run.dodges++; st.totals.chanclas++;
              pop("DODGED LA CHANCLA! +" + EVENTS.chancla.bonus, { x: LW / 2, y: Math.max(130, GY - 236), col: COL.turq, size: 22, big: true, life: 1.3, rise: 10 }); crowd(1, 0.7, "¡ESO!"); audio.fx.cheer(); }
          }
          if (ev.cx < camX - 80 || ev.h < -40) ev = null;
        }
      }
    }
    function finishAbuela() {
      audio.tempo(1); audio.muffle(false); audio.fx.cheer();
      if (run) { run.score += EVENTS.abuela.bonus; run.feria += EVENTS.abuela.feria; run.abuelas++; st.totals.abuelas++; if (st.totals.abuelas >= 25) unlock("elders"); save(st); }
      pop("+500 RESPETO", { x: LW / 2, y: Math.max(140, GY - 256), col: COL.turq, size: 30, big: true, life: 1.6, rise: 10 });
      crowd(1, 0.8, "¡Respeto!"); sayLine("Gracias, mijo.", "es-MX", { pitch: 1.35, rate: 0.85, force: true });   // she always gets her thanks
    }

    // ---- autopilot (the title screen's attract mode; also a test hook)
    function autopilot() {
      const ph = CARS[0].phys, v = Math.max(120, car.v), inRun = !!run && mode === "run";
      if (car.air) { if (!car.tapped && tLand() < 0.06) { if (inRun) press(); else { car.tapped = true; car.tapT = T; } } return; }
      if (car.pend && inRun) { press(); return; }
      if (ev && ev.type === "chancla") {
        if (ev.high) { if (car.charging && ev.phase === "fly") { if (inRun) release(); else launch(); } return; }
        if (ev.phase === "fly" && !ev.dodged) { const tt = (ev.cx - (car.x + 200)) / (300 + v); if (!car.charging && tt < 0.62) startCharge(); if (car.charging && (car.charge >= 0.45 || tt < 0.2)) inRun ? release() : launch(); return; }
      }
      if (ev && ev.type === "abuela" && ev.phase !== "done") return;
      if (ev && ev.auto && ev.auto(inRun)) return;
      const o = obs.find((q) => !q.hit && !q.knock && !q.cleared && q.x + q.w > car.x + 20);
      if (!o) { if (car.charging) inRun ? release() : launch(); return; }
      // the stretch of road where the car would touch it, and the hop that clears it with its apex in the middle
      const tall = o.h > 20, fr = o.pit ? R64.front + 6 : tall ? 194 : R64.front + R64.r, rr0 = o.pit ? R64.rear - 6 : tall ? 6 : R64.rear - R64.r;
      const vr = Math.max(60, v - (o.vx || 0)), a = o.x - fr - 14, b = o.x + o.w - rr0 + 14, hh = o.h + 10, Tn = (b - a) / vr;
      let vy0 = Math.sqrt(Math.pow(ph.g * Tn / 2, 2) + 2 * ph.g * hh);
      let c = clamp((vy0 - ph.vMin) / (ph.vMax - ph.vMin), 0.12, 1);
      if (!run) c = Math.max(c, 0.3 + ((o.x | 0) % 7) / 11);
      vy0 = ph.vMin + (ph.vMax - ph.vMin) * c;
      const launchX = (a + b) / 2 - vr * (vy0 / ph.g);
      if (!car.charging && car.x >= launchX - vr * c * ph.chargeT - 4 && car.x < b) { startCharge(); car.autoWant = c; }
      if (car.charging && (car.charge >= (car.autoWant || c) - 0.004 || car.x >= launchX)) inRun ? release() : launch();
    }
    function startCharge() { if (mode === "run") press(); else if (!car.air) { car.charging = true; car.charge = 0; } }

    // ---- simulation
    function step(dt) {
      if (!car.air && !car.pend) groundedAt = T; // v49.27: last road contact, 100ms coyote grace
      prevCam = camX; prevX = car.x; prevY = car.y; // v49.27: fixed-step render snapshots
      if (god && god.on) { if (run) { run.god = true; if (god.gas) { run.fuel = 1; run.out = false; } } dt *= god.speed || 1; }
      const ph = CARS[0].phys;
      if (ev && ev.type === "abuela" && ev.phase === "cross") dt *= 0.7;
      T += dt; voiceT += dt;
      const inRun = mode === "run" && run;
      if (mode === "run" || mode === "title" || mode === "crash") {
        let target = mode === "crash" || (run && run.out) ? 0 : cruise(difficulty());
        if (ev && (ev.type === "abuela" || ev.stop) && ev.phase !== "done") { const left = ev.x - 22 - (car.x + 200); target = Math.min(target, Math.max(0, left * 1.7)); }
        if (obs.some((o) => o.kind === "bump" && !o.hit && car.v < 150 && o.x < car.x + 210 && o.x + o.w > car.x)) target = Math.min(target, 100); // v49.27: creep over a speed bump
        car.v += clamp(target - car.v, -520 * dt, 140 * dt);
        car.x += car.v * dt;
        if (ev && (ev.type === "abuela" || ev.stop) && ev.phase !== "done") car.x = Math.min(car.x, ev.x - 22 - 200);   // never hits her (or a horse)
        car.rot += (car.v * dt) / R64.r;
      }
      for (const o of obs) if (o.kind === "copcar" && !o.hit) o.x += (o.vx || 0) * dt; // v49.27: parked or oncoming
      if (auto || mode === "title") autopilot();
      if (car.charging) { car.charge = Math.min(1, car.charge + dt / ph.chargeT); audio.fx.pumpLevel(car.charge); if (car.charge >= 1 && rand() < dt * 30) burst(car.x + rand() * 200, GY - 4, 1, "spark", { a: -1.57, spread: 2.4, sp: 120, life: 0.3 }); }
      // body on its springs (hydraulics squat while charging, sag a little when hurt)
      const sq = car.charging ? -11 * car.charge : car.air ? 6 : 0, hurtSag = car.hurt > 0 ? -3 : 0;
      car.vR += ((sq + hurtSag - car.sR) * ph.spring - car.vR * ph.damp) * dt; car.sR += car.vR * dt;
      car.vF += ((sq * 0.8 - car.sF) * ph.spring - car.vF * ph.damp) * dt; car.sF += car.vF * dt;
      if (car.air) {
        car.vy -= ph.g * dt; car.y += car.vy * dt;
        const tgt = car.tapped ? 0 : car.vy > 0 ? 0.06 * car.launchC : -0.085;
        car.ang += (tgt - car.ang) * Math.min(1, dt * 6);
        if (car.y <= 0 && car.vy < 0) { car.y = 0; land(); }
      } else car.ang += (0 - car.ang) * Math.min(1, dt * 12);
      if (car.pend && T > car.pend.until) { if (inRun) resolve("scraped"); else car.pend = null; }
      car.hurt = Math.max(0, car.hurt - dt); car.scrape = Math.max(0, car.scrape - dt);
      if (car.scrape > 0 && rand() < dt * 50) burst(car.x + 196, GY - 3, 1, "spark", { a: -0.3, spread: 0.8, sp: 220, life: 0.35 });
      camX = lerp(camX, car.x - carSX, 1 - Math.exp(-18 * dt)); // v49.27: subpixel camera
      if (inRun) {
        run.t += dt; run.meters = car.x / UPM;
        // obstacles
        const W = [[car.x + R64.rear - R64.r, car.x + R64.rear + R64.r], [car.x + R64.front - R64.r, car.x + R64.front + R64.r]];
        for (const o of obs) {
          if (o.hit || o.knock || o.cleared) continue;
          let hit = false;
          if (o.pit) hit = car.y < 2 && W.some(([a, b]) => (a + b) / 2 > o.x + 6 && (a + b) / 2 < o.x + o.w - 6);
          else if (o.h > 20) hit = car.x + 6 < o.x + o.w && car.x + 194 > o.x && car.y + 6 < o.h;
          else hit = W.some(([a, b]) => a < o.x + o.w && b > o.x) && car.y < o.h;
          if (car.air && car.x + 194 > o.x && car.x < o.x + o.w) o.jumped = true; // v49.27
          if (o.kind === "bump" && car.v < 150) hit = false;
          if (hit) { o.hit = true; if (o.T && SX) SX.say(o, "hit"); if (!o.pit && !o.noKnock) o.knock = { x: 0, y: 0, a: 0, vx: car.v * 0.7 + 80, vy: 260, va: (rand() - 0.5) * 9, t: 0 }; hurt(o.soft ? "soft" : "hit", o); continue; }
          if (o.x + o.w < car.x) { o.cleared = true; run.clears++; const kind = o.T && o.T.cop ? "copcar" : o.kind; run.cleared[kind] = (run.cleared[kind] || 0) + 1; const clean = !!o.jumped && ["pothole", "bump", "pallet", "copcar"].includes(kind); const p = (clean ? kind === "copcar" ? 150 : 50 : o.T ? o.T.pts || 80 : 40) * TIERS[run.tier].x; run.score += p; pop((clean ? kind === "copcar" ? "+COP HOP " : "+CLEAN " : "+") + p, { x: o.x - camX + o.w / 2, y: GY - 40, col: "#fff", size: 13, life: 0.7, rise: 26 });
            if (o.T && SX) SX.over(o); }
        }
        for (const c of coins) if (!c.got && c.x > car.x && c.x < car.x + 200 && c.h > car.y && c.h < car.y + 76) { c.got = true; run.feria++; run.score += 10; audio.fx.coin(); burst(c.x, GY - c.h, 5, "star", { sp: 90, life: 0.4 }); }
        if (SX && SX.run) SX.run(dt);
        if (god && god.on && god.gas) { run.fuel = 1; run.out = false; }   // a stage's own (San Antonio: pickups, the gas tank, the Trail Ride)
        if (run.out && car.v < 4 && mode === "run" && !(god && god.on && god.invincible)) { mode = "crash"; later(() => { if (mode === "crash") endRun("gas"); }, 900); ctrl(); }
        if (run.meters - run.cleanFrom >= MILE) unlock("scratch");
        // events
        if (!evOn) {} else if (!ev && run.t > run.nextAbuela) { if (startEvent("abuela")) { const E = EVENTS.abuela.every; run.nextAbuela = run.t + E[0] + rand() * (E[1] - E[0]); if (run.nextChancla < run.t + 6) run.nextChancla = run.t + 6; } }
        else if (!ev && run.t > run.nextChancla) { if (startEvent("chancla")) { const E = EVENTS.chancla.every; run.nextChancla = run.t + E[0] + rand() * (E[1] - E[0]); if (run.nextAbuela < run.t + 6) run.nextAbuela = run.t + 6; } }
        if (hold && car.x > hold) hold = 0;
      }
      updateEvent(dt);
      if (SX && SX.tick) SX.tick(dt);
      for (const o of obs) if (o.knock) { const k = o.knock; k.t += dt; k.x += k.vx * dt; k.vy -= 900 * dt; k.y = Math.max(-30, k.y + k.vy * dt); k.a += k.va * dt; }
      for (const p of people) { if (p.react > 0) p.react = Math.max(0, p.react - dt); }
      for (const d of dogs) if (!d.done && d.x - car.x < 260 && d.x > car.x - 60) d.run = 1;
      for (const d of dogs) if (d.run) { d.x += 140 * dt; d.y += 4 * dt; }
      for (const p of parts) { p.life += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += (p.kind === "dust" ? -10 : p.kind === "confetti" ? 140 : 520) * dt; if (p.kind === "confetti") p.vx *= 1 - dt * 1.5; p.a += p.va * dt; }
      parts = parts.filter((p) => p.life < p.max);
      for (const p of pops) p.t += dt; pops = pops.filter((p) => p.t < p.life);
      // v49.26: only the head ages; waiting speech keeps its full short turn.
      if (bubbles.length) { const b = bubbles[0]; b.t += dt; if (b.t >= Math.min(b.life, 1.6)) bubbles.shift(); }
      shake = Math.max(0, shake - dt * 30);
      spawnAhead();
    }

    // ---- drawing
    function tileX(img, par, y, w) { const off = ((camX * par) % w + w) % w; for (let x = -off; x < LW; x += w) g.drawImage(img, x, y, w, img.height / K); }
    function cached(map, key, w, h, ox, oy, fn) {
      let c = map.get(key); if (!c) { const [cc, x] = mk(w, h); x.translate(ox, oy); fn(x); c = cc; map.set(key, c); } return c;
    }
    function draw() {
      const t = T;
      popList = []; bubbleList = []; finishTitle = false; // v49.26: clear geometry when the HUD is hidden.
      g.setTransform(dpr * S, 0, 0, dpr * S, 0, 0);
      g.save();
      if (shake > 0) g.translate((rand() - 0.5) * shake, (rand() - 0.5) * shake);
      if (zoom !== 1) { const zx = car.x - camX + 100, zy = GY - 40; g.translate(LW / 2, zy); g.scale(zoom, zoom); g.translate(-zx, -zy); }
      // sky + far layers
      if (skyC) g.drawImage(skyC, 0, 0, LW, skyH);
      g.fillStyle = "#22092f"; g.fillRect(0, skyH - 2, LW, GY - skyH);
      if (skylineC) tileX(skylineC, 0.035, GY - 70 - 260, 1000);
      if (midC) tileX(midC, 0.13, GY - 60 - 170, 1000);
      // back billboards (parallax 0.45; the house ad is Chisme's own spot)
      for (const b of bbs) { const sx = b.x - camX * 0.35; if (sx > LW + 10 || sx + b.w < -10) continue;
        g.drawImage(cached(bbCache, b, b.w + 20, b.h + 20, 10, 10, (x) => drawBillboard(x, b.s, b.w, b.h)), sx - 10, GY - 374 - 10, b.w + 20, b.h + 20); }
      // the boulevard's far side: lots on the sidewalk
      for (const L of lots) { const sx = L.x - camX * 0.6; if (sx > LW + 10 || sx + L.w < -10) continue; const top = L.top || 240;
        g.drawImage(cached(lotCache, L, L.w + 40, top + 20, 20, top, (x) => (L.draw ? L.draw(x, L, season, H) : drawLot(x, L, season))), sx - 20, GY - 62 - top, L.w + 40, top + 20); }
      g.fillStyle = lg(g, 0, GY - 62, 0, GY - 46, [[0, "#4a3b5a"], [1, "#3a2d4a"]]); g.fillRect(0, GY - 62, LW, 16);
      g.fillStyle = "#6a5a7c"; g.fillRect(0, GY - 47, LW, 2);
      if (SX && SX.draw) SX.draw(g, t, "lot");
      for (const p of props) { const sx = p.x - camX; if (sx < -60 || sx > LW + 60) continue; drawProp(p, sx, t); }
      for (const L of lots) if (L.tag) { const sx = L.x - camX * 0.6; if (sx < LW && sx + L.w > 0) nameTag(L.tag, sx, sx + L.w, Math.max(84, GY - 62 - (L.tagY || L.top || 200) - 10)); }   // landmark name tags ride over the poles
      for (const d of dogs) { const sx = d.x - camX; if (sx > -30 && sx < LW + 30) dog(g, sx, d.y, t, d.run, d.col); }
      for (const p of people) { const sx = p.x - camX; if (sx > -30 && sx < LW + 30) drawPerson(g, p, sx, t); }
      // road
      g.fillStyle = lg(g, 0, GY - 46, 0, GY + 46, [[0, "#1d1828"], [0.5, "#262033"], [1, "#1a1524"]]); g.fillRect(0, GY - 45, LW, 91);
      g.fillStyle = "rgba(255,255,255,.75)"; const dOff = ((camX % 90) + 90) % 90; for (let x = -dOff; x < LW; x += 90) g.fillRect(x, GY - 24, 44, 2.5);
      g.fillStyle = "rgba(0,0,0,.25)"; for (let x = -((camX * 1) % 37 + 37) % 37; x < LW; x += 37) g.fillRect(x, GY + 14 + ((x * 7) % 9), 8, 1);
      if (ev && ev.drawRoad) ev.drawRoad(g, t);
      if (ev && ev.type === "abuela") { const sx = ev.x - camX; g.fillStyle = "rgba(255,255,255,.85)"; for (let i = 0; i < 6; i++) { g.save(); g.translate(sx, GY - 44 + i * 15.2); g.transform(1, 0, -0.35, 1, 0, 0); g.fillRect(0, 0, 46, 9); g.restore(); } }
      // abuela on the far half walks behind the car, the near half in front
      const ab = ev && ev.type === "abuela" && ev.phase !== "warn" ? { x: ev.x - camX + 22 + ev.d * 10, y: GY - 44 + ev.d * 88 } : null;
      const abFrame = () => ab && drawAbuela(g, ab.x, ab.y, 1.4, t, ev.phase === "cross", ev.phase === "done");
      if (ab && ab.y < GY + 2) abFrame();
      if (ev && ev.draw) ev.draw(g, t, false);
      for (const o of obs) { const sx = o.x - camX; if (sx > LW + 20 || sx + o.w < -80) continue; if (o.T && SM) SM.drawTraffic(g, o, sx, GY, t, reduced(), H); else drawObstacle(g, o, sx, GY, t); }
      for (const c of coins) { const sx = c.x - camX; if (!c.got && sx > -20 && sx < LW + 20) drawCoin(g, sx, GY - c.h, t); }
      if (SM && SM.drawPick) for (const c of picks) { const sx = c.x - camX; if (!c.got && sx > -30 && sx < LW + 30) SM.drawPick(g, c.kind, sx, GY - c.h, t + c.t, H); }
      // landing ring (where the front wheel will touch down): tap when the white ring meets the dashed one
      if (car.air && mode === "run" && !car.tapped) {
        const tl = tLand(), fx = car.x - camX + R64.front, rad = 13 + tl * 140, tgt = 13 + WIN.perfect * 140, inP = tl <= WIN.perfect;
        g.save(); g.strokeStyle = "rgba(255,255,255,.55)"; g.lineWidth = 1.5; g.setLineDash([4, 4]); g.beginPath(); g.ellipse(fx, GY, tgt, tgt * 0.28, 0, 0, 6.2832); g.stroke(); g.setLineDash([]);
        if (rad < 160) { g.strokeStyle = inP ? COL.turq : "#ffffff"; g.lineWidth = inP ? 3.5 : 2.2; g.beginPath(); g.ellipse(fx, GY, rad, rad * 0.28, 0, 0, 6.2832); g.stroke(); }
        g.restore();
      }
      const geo = drawCar(g, { x: car.x - camX, gy: GY, y: car.y, sR: car.sR, sF: car.sF, ang: car.ang, rot: car.rot, t, P: P(), car: curCar(), lights: true, blur: car.v > 330, brake: (ev && (ev.type === "abuela" || ev.stop) && ev.phase !== "done") || (run && run.out), bob: car.air ? 0 : Math.sin(t * 6) * 0.6, driver: true });
      if (car.hurt > 0 && Math.floor(t * 14) % 2 === 0 && mode !== "crash") { g.save(); g.globalAlpha = 0.25; g.fillStyle = "#fff"; g.fillRect(geo.rearX, GY - car.y - 80, 210, 80); g.restore(); }
      if (ab && ab.y >= GY + 2) abFrame();
      if (ev && ev.draw) ev.draw(g, t, true);
      if (SX && SX.draw) SX.draw(g, t, "front");   // a stage's own (San Antonio: the chase behind you, the helicopters, the party)
      if (ev && ev.type === "chancla" && ev.phase === "fly") { const cx = ev.cx - camX, cy = GY - ev.h;
        if (!ev.hit) { g.strokeStyle = "rgba(255,255,255,.55)"; g.lineWidth = 2; g.lineCap = "round"; for (let i = 0; i < 3; i++) { g.beginPath(); g.moveTo(cx + 34 + i * 6, cy - 9 + i * 9); g.lineTo(cx + 70 + i * 10, cy - 9 + i * 9); g.stroke(); } }
        drawChancla(g, cx, cy, -ev.a, 1.35); }
      // near curb + sidewalk
      g.fillStyle = "#ff1a7f"; g.fillRect(0, GY + 45, LW, 3);
      g.fillStyle = lg(g, 0, GY + 48, 0, LH, [[0, "#3e3050"], [1, "#1c1428"]]); g.fillRect(0, GY + 48, LW, LH - GY - 48);
      g.fillStyle = "rgba(0,0,0,.25)"; const sOff = ((camX * 1.15) % 60 + 60) % 60; for (let x = -sOff; x < LW; x += 60) g.fillRect(x, GY + 48, 1.5, LH);
      if (season) { g.globalAlpha = 0.9; for (let x = -(((camX * 1.15) % 140) + 140) % 140; x < LW; x += 140) marigolds(g, x + 20, GY + 70, 4); g.globalAlpha = 1; }
      { const fy = Math.min(LH - 8, GY + 150), P0 = camX * 1.15, k0 = Math.floor(P0 / 230); for (let k = k0; k < k0 + Math.ceil(LW / 230) + 2; k++) fgProp(k, k * 230 - P0 + 60, fy, t); }
      // particles (world space)
      for (const p of parts) { const sx = p.x - camX, a = 1 - p.life / p.max;
        if (p.kind === "spark") { g.strokeStyle = (p.a * 10 | 0) % 3 ? `rgba(255,255,255,${a})` : `rgba(255,106,11,${a})`; g.lineWidth = 1.6; g.beginPath(); g.moveTo(sx, p.y); g.lineTo(sx - p.vx * 0.02, p.y - p.vy * 0.02); g.stroke(); }
        else if (p.kind === "dust") { g.fillStyle = `rgba(200,180,220,${a * 0.35})`; g.beginPath(); g.arc(sx, p.y, 4 + (1 - a) * 10 * p.s, 0, 6.2832); g.fill(); }
        else if (p.kind === "star") { g.save(); g.translate(sx, p.y); g.rotate(p.a); g.fillStyle = a > 0.5 ? "#ffffff" : COL.turq; g.globalAlpha = a; star(g, 5); g.restore(); }
        else { g.save(); g.translate(sx, p.y); g.rotate(p.a); g.globalAlpha = Math.min(1, a * 2); g.fillStyle = p.col; g.fillRect(-3, -1.5, 6, 3); g.restore(); } }
      bubbleList = []; // v49.26: queued speakers remain visible even as their car leaves.
      if (bubbles.length) { const b = bubbles[0]; bubbleList.push(bubble(g, b.p.x - camX, Math.min(LH - 12, b.p.y - 46 * b.p.s), b.text, b.t, LW, 170 / S)); }
      g.restore();
      hud(t);
    }
    function nameTag(text, x0, x1, y) {   // the little name tag over a San Antonio landmark as it passes (kept over the part of the lot you can see)
      g.font = `900 11px ${SANS}`; const w = g.measureText(text).width + 26; let x = clamp((x0 + x1) / 2, Math.max(x0, 0) + w / 2 + 4, Math.min(x1, LW) - w / 2 - 4); x = clamp(x, w / 2 + 6, LW - w / 2 - 6);
      g.fillStyle = "rgba(0,0,0,.82)"; rr(g, x - w / 2, y - 11, w, 22, 11); g.fill(); g.strokeStyle = COL.turq; g.lineWidth = 1.5; rr(g, x - w / 2, y - 11, w, 22, 11); g.stroke();
      g.fillStyle = COL.pink; g.beginPath(); g.arc(x - w / 2 + 11, y - 2, 4, 3.14, 0); g.lineTo(x - w / 2 + 11, y + 6); g.closePath(); g.fill(); g.fillStyle = "#000"; g.beginPath(); g.arc(x - w / 2 + 11, y - 2, 1.5, 0, 6.2832); g.fill();
      g.fillStyle = "#fff"; g.textAlign = "left"; g.textBaseline = "middle"; g.fillText(text, x - w / 2 + 19, y + 0.5);
    }
    function star(x, r) { x.beginPath(); for (let i = 0; i < 10; i++) { const a = -1.5708 + i * 0.6283, rr2 = i % 2 ? r * 0.45 : r; x.lineTo(Math.cos(a) * rr2, Math.sin(a) * rr2); } x.closePath(); x.fill(); }
    function fgProp(k, x, y, t) {   // the near sidewalk: planters, a hydrant, a bench, a newspaper box (closest layer, a bit darker)
      const kind = ((k * 2654435761) >>> 0) % 5; g.save(); g.globalAlpha = 0.92;
      if (kind === 0) { g.fillStyle = "#c2185b"; rr(g, x - 16, y - 18, 32, 18, 3); g.fill(); g.fillStyle = "#1f6b3a"; for (const [dx, dy, r] of [[-6, -30, 8], [5, -38, 7], [10, -26, 6]]) { g.beginPath(); g.ellipse(x + dx, y + dy, r * 0.7, r, dx * 0.04, 0, 6.2832); g.fill(); }
        g.fillStyle = COL.pink; g.beginPath(); g.arc(x + 5, y - 46, 2.5, 0, 6.2832); g.fill(); }
      else if (kind === 1) { g.fillStyle = "#e9e5ef"; rr(g, x - 6, y - 26, 12, 26, 3); g.fill(); g.fillStyle = COL.pink; g.beginPath(); g.arc(x, y - 26, 7, 3.14, 6.28); g.fill(); g.fillRect(x - 10, y - 18, 20, 4); g.fillStyle = "#8a8f99"; g.fillRect(x - 7, y - 3, 14, 3); }
      else if (kind === 2) { g.fillStyle = "#3a221e"; g.fillRect(x - 30, y - 16, 60, 4); g.fillRect(x - 30, y - 28, 60, 4); g.fillStyle = "#111"; g.fillRect(x - 26, y - 12, 3, 12); g.fillRect(x + 23, y - 12, 3, 12); }
      else if (kind === 3) { g.fillStyle = COL.turq; rr(g, x - 11, y - 34, 22, 34, 3); g.fill(); g.fillStyle = "#0d2a2c"; g.fillRect(x - 8, y - 28, 16, 9); g.fillStyle = "#fff"; g.font = `900 5px ${SANS}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("CHISME", x, y - 13); }
      else { g.fillStyle = "#5b3a78"; rr(g, x - 14, y - 14, 28, 14, 3); g.fill(); g.fillStyle = "#2e8b57"; for (let i = -2; i <= 2; i++) { g.beginPath(); g.moveTo(x + i * 4, y - 13); g.quadraticCurveTo(x + i * 7, y - 30, x + i * 9, y - 34 + Math.abs(i) * 4); g.lineWidth = 2; g.strokeStyle = "#2e8b57"; g.stroke(); } }
      g.restore();
    }
    function drawProp(p, sx, t) {
      if (p.kind === "pole") {
        g.fillStyle = "#2a2138"; g.fillRect(sx, GY - 62 - 170, 4, 172);
        g.fillRect(sx, GY - 62 - 170, 34, 3); g.fillStyle = "#3a3048"; rr(g, sx + 26, GY - 62 - 172, 16, 6, 3); g.fill();
        drawGlow(g, sx + 34, GY - 62 - 165, 26, "#ffd9ec", 0.35);
        g.save(); g.globalAlpha = 0.06; g.fillStyle = "#ffd9ec"; g.beginPath(); g.moveTo(sx + 28, GY - 228); g.lineTo(sx - 10, GY - 50); g.lineTo(sx + 80, GY - 50); g.closePath(); g.fill(); g.restore();
        const birds = (p.x | 0) % 3; g.fillStyle = "#0e0818"; for (let i = 0; i < birds; i++) { const bx = sx + 10 + i * 11, by = GY - 62 - 173; g.beginPath(); g.ellipse(bx, by, 4, 2.6, 0, 0, 6.2832); g.fill(); g.beginPath(); g.moveTo(bx + 3, by - 1); g.lineTo(bx + 8, by - 3 - Math.sin(t * 3 + i) * 0.8); g.lineTo(bx + 4, by + 1); g.fill(); g.fillRect(bx - 7, by - 1, 5, 1.4); }
      } else if (p.kind === "xing") {
        g.fillStyle = "#e9e5ef"; g.fillRect(sx, GY - 62 - 70, 3, 72);
        g.save(); g.translate(sx + 1.5, GY - 120); for (const a of [0.6, -0.6]) { g.save(); g.rotate(a); g.fillStyle = "#fff"; g.fillRect(-22, -3.5, 44, 7); g.fillStyle = "#000"; g.font = `900 5px ${SANS}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(a > 0 ? "RAILROAD" : "CROSSING", 0, 0.3); g.restore(); } g.restore();
      } else if (p.kind === "abuelasign") {
        g.fillStyle = "#c9ced6"; g.fillRect(sx, GY - 62 - 64, 3, 66);
        g.save(); g.translate(sx + 1.5, GY - 62 - 78); g.rotate(0.7854); g.fillStyle = COL.turq; g.fillRect(-14, -14, 28, 28); g.strokeStyle = "#000"; g.lineWidth = 1.5; g.strokeRect(-12, -12, 24, 24); g.restore();
        drawAbuela(g, sx + 1.5, GY - 62 - 68, 0.38, 0, false, false);
      }
    }
    function txt(s, x, y, size, fill, align = "left", edge = "#000", font = FONT, w = "900") {
      g.font = `${w} ${size}px ${font}`; g.textAlign = align; g.textBaseline = "middle"; g.lineJoin = "round";
      if (edge) { g.strokeStyle = edge; g.lineWidth = Math.max(2, size / 5); g.strokeText(s, x, y); } g.fillStyle = fill; g.fillText(s, x, y);
    }
    function hud(t) {
      if (zoom !== 1) return;
      if (mode === "run" || mode === "paused" || mode === "crash") {
        txt(num(run.score), 14, 26, 26, "#ffffff");
        txt((run.meters / MILE).toFixed(2) + " mi", 15, 50, 13, COL.turq, "left", "#000", SANS, "800");
        drawCoin(g, LW - 74, 24, 0, 1.15); txt(num(st.feria + run.feria), LW - 60, 25, 19, "#ffffff");
        if (SX && SX.hud) SX.hud(g, t, txt);   // a stage's own (San Antonio: the gas gauge)
        for (let i = 0; i < 3; i++) icon(g, i < run.lives ? "wheel" : "wheelx", LW - 66 + i * 24, 52, 1.25);
        // combo pill
        const tier = TIERS[run.tier], nxt = TIERS[run.tier + 1];
        if (run.streak > 0 || run.tier > 0) {
          const cx = LW / 2, w = 92, y = 18; g.fillStyle = run.tier ? COL.pink : "rgba(0,0,0,.55)"; rr(g, cx - w / 2, y, w, 26, 13); g.fill(); g.strokeStyle = "#fff"; g.lineWidth = 1.5; rr(g, cx - w / 2, y, w, 26, 13); g.stroke();
          txt(run.tier ? "x" + tier.x + " COMBO" : "STREAK " + run.streak, cx, y + 13.5, run.tier ? 14 : 12, "#fff", "center", null);
          if (nxt) { const f = (run.streak - tier.at) / (nxt.at - tier.at); g.fillStyle = "rgba(0,0,0,.45)"; rr(g, cx - 34, y + 30, 68, 4, 2); g.fill(); g.fillStyle = COL.turq; rr(g, cx - 34, y + 30, 68 * clamp(f, 0, 1), 4, 2); g.fill(); }
        }
        // event banners: La Chancla incoming (which way to dodge) · Abuela crossing (wait for it)
        if (ev && ev.type === "chancla" && ev.phase === "warn") {
          const on = Math.floor(t * 6) % 2 === 0, bw = 176, bx = LW - bw - 10, by = (SX && SX.bannerY) || 74;
          g.fillStyle = "rgba(0,0,0,.85)"; rr(g, bx, by, bw, 56, 12); g.fill(); g.strokeStyle = on ? COL.pink : "#ffffff"; g.lineWidth = 3; rr(g, bx, by, bw, 56, 12); g.stroke();
          drawChancla(g, bx + 30, by + 28 + (ev.high ? -8 : 8), on ? -0.3 : 0.3, 0.75);
          txt("LA CHANCLA!", bx + 104, by + 18, 16, COL.pink, "center", null);
          txt(ev.high ? "HIGH · STAY LOW!" : "LOW · HOP IT!", bx + 104, by + 39, 13, "#ffffff", "center", null, SANS, "900");
        }
        if (ev && ev.banner) ev.banner(g, t, txt);
        if (ev && ev.type === "abuela" && ev.phase !== "done") {
          const bw = 236, bx = (LW - bw) / 2, by = (SX && SX.bannerY) || 74;
          g.fillStyle = "rgba(0,0,0,.8)"; rr(g, bx, by, bw, 50, 12); g.fill(); g.strokeStyle = COL.turq; g.lineWidth = 3; rr(g, bx, by, bw, 50, 12); g.stroke();
          txt("ABUELA CROSSING", LW / 2, by + 18, 16, COL.turq, "center", null);
          txt("Stop and wait for her · +500 RESPETO", LW / 2, by + 37, 11, "#ffffff", "center", null, SANS, "800");
        }
        // charge meter + hints (on the near sidewalk)
        const my = GY + 74, mw = Math.min(260, LW - 60), mx = (LW - mw) / 2;
        if (car.charging) {
          g.fillStyle = "rgba(0,0,0,.55)"; rr(g, mx, my, mw, 16, 8); g.fill();
          g.fillStyle = lg(g, mx, 0, mx + mw, 0, [[0, COL.turq], [0.6, COL.pink], [1, COL.orange]]); rr(g, mx, my, mw * car.charge, 16, 8); g.fill();
          g.strokeStyle = "#fff"; g.lineWidth = 1.5; rr(g, mx, my, mw, 16, 8); g.stroke();
          txt(car.charge >= 1 ? "FULL PSI · LET GO!" : "CHARGING…", LW / 2, my + 30, 12, "#fff", "center", "#000", SANS, "900");
        } else if (st.totals.hops < 14 && mode === "run" && zoom === 1) {
          txt(car.air ? (car.tapped ? "Nice. Now stick it." : "TAP when the rings meet!") : "HOLD to charge · LET GO to hop", LW / 2, my + 10, 13, "#fff", "center", "#000", SANS, "900");
        }
      }
      // v49.26: reserve measured rectangles every frame, big awards first (maximum two).
      popList = []; finishTitle = !!(ev && ev.type === "party" && ev.phase === "party" && (mode === "run" || mode === "paused" || mode === "crash"));
      const boxes = bubbleList.map((b) => ({ ...b }));   // v49.26: pops also steer clear of the speech bubble
      if (finishTitle) { const y = ((SX && SX.bannerY) || 150) + 82;
        txt("¡LLEGASTE!", LW / 2, y, 40, "#FF1A7F", "center", "#000");
        boxes.push({ x: 8, y: y - 28, w: LW - 16, h: 56 }); }
      for (const p of [...pops].sort((a, b) => Number(b.big) - Number(a.big))) {
        const k = p.t / p.life, a = k > 0.75 ? 1 - (k - 0.75) / 0.25 : 1;
        g.font = `900 ${p.size}px ${FONT}`; const tw = g.measureText(p.text).width, pad = p.size / 5 + 4, iw = p.icon ? 32 : 0;
        const w = tw + pad * 2 + iw, h = p.size * 1.4 + pad * 2, x = clamp((p.x == null ? LW / 2 : p.x) - w / 2, 8, Math.max(8, LW - w - 8));
        let y = Math.max(64, (p.y == null ? GY - 200 : p.y) - p.rise * k - h / 2), hit;
        do { hit = boxes.find((b) => x < b.x + b.w + 6 && x + w + 6 > b.x && y < b.y + b.h + 6 && y + h + 6 > b.y); if (hit) y = hit.y + hit.h + 6; } while (hit);
        if (y + h > LH - 8) continue;
        const box = { text: p.text, x, y, w, h }; boxes.push(box); popList.push(box);
        g.save(); g.globalAlpha = a; const cx = x + iw + (w - iw) / 2, cy = y + h / 2;
        if (p.icon) icon(g, p.icon, cx - tw / 2 - 16, cy, p.size / 22);
        txt(p.text, cx, cy, p.size, p.col, "center", p.edge); g.restore();
      }
      if (paused()) { g.fillStyle = "rgba(10,4,24,.35)"; g.fillRect(0, 0, LW, LH); }
    }
    const paused = () => mode === "paused";

    // ---- overlays (DOM cards over the canvas). Every value that goes in is esc()'d / num()'d or our own markup.
    let ovKind = "";
    function overlay(html, kind) { ov.innerHTML = html; ovKind = html ? kind || "card" : ""; ov.dataset.kind = ovKind; ov.classList.toggle("on", !!html); wrap.classList.toggle("lr-has-ov", !!html); }
    const SVGF = `<svg class="lr-f" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="9" fill="#C9CED6"/><circle cx="10" cy="10" r="6.6" fill="none" stroke="#00C9CD" stroke-width="1.8"/><text x="10" y="13.6" text-anchor="middle" font-size="10" font-weight="900" fill="#FF1A7F" font-family="system-ui,sans-serif">F</text></svg>`;
    // the title lettering: Goonie's key art, rebuilt as live type (chrome fill, a heavy black outline, a bronze rim, the crown, a sparkle)
    // over the cleaned key art (badges patched out, its painted lettering taken off). Placed in the art's own 1536 × 1024 frame.
    const LOGO = `<svg class="lr-logo-svg" viewBox="0 0 1536 1024" role="img" aria-label="${TITLE}" focusable="false"><defs>
      <linearGradient id="lrChrome" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".32" stop-color="#e4e8ee"/><stop offset=".5" stop-color="#8b949f"/><stop offset=".54" stop-color="#5d6672"/><stop offset=".72" stop-color="#d9dee5"/><stop offset=".88" stop-color="#ffffff"/><stop offset="1" stop-color="#a7afb9"/></linearGradient>
      <linearGradient id="lrCrown" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3c9a3"/><stop offset=".45" stop-color="#d98a4e"/><stop offset=".75" stop-color="#9c5428"/><stop offset="1" stop-color="#f0b98c"/></linearGradient>
      <g id="lrWords"><text x="430" y="196" font-size="206" textLength="420" lengthAdjust="spacingAndGlyphs">Puro</text><text x="1068" y="196" font-size="206" textLength="470" lengthAdjust="spacingAndGlyphs">Pinche</text><text x="785" y="425" font-size="262" textLength="1010" lengthAdjust="spacingAndGlyphs">Lowrider</text></g></defs>
      <g class="lr-lt" font-family='"PPL Display","UnifrakturCook",serif' font-weight="700" text-anchor="middle" stroke-linejoin="round" paint-order="stroke">
        <use href="#lrWords" stroke="#b86a3e" stroke-width="54" fill="#b86a3e"/><use href="#lrWords" stroke="#000" stroke-width="40" fill="url(#lrChrome)"/><use href="#lrWords" fill="none" stroke="#ffffff" stroke-opacity=".55" stroke-width="3"/></g>
      <g class="lr-crown" transform="translate(748 104)"><path d="M-92 18 L-104 -54 L-56 -18 L-28 -82 L0 -30 L28 -82 L56 -18 L104 -54 L92 18 Z" fill="url(#lrCrown)" stroke="#000" stroke-width="14" stroke-linejoin="round"/>
        <path d="M-96 18 Q0 50 96 18 L92 40 Q0 70 -92 40 Z" fill="url(#lrCrown)" stroke="#000" stroke-width="12" stroke-linejoin="round"/><circle cx="-28" cy="-88" r="11" fill="#f3c9a3" stroke="#000" stroke-width="7"/><circle cx="28" cy="-88" r="11" fill="#f3c9a3" stroke="#000" stroke-width="7"/><circle cx="-104" cy="-60" r="9" fill="#f3c9a3" stroke="#000" stroke-width="6"/><circle cx="104" cy="-60" r="9" fill="#f3c9a3" stroke="#000" stroke-width="6"/>
        <circle cx="0" cy="8" r="9" fill="#00C9CD" stroke="#000" stroke-width="5"/><circle cx="-46" cy="6" r="7" fill="#FF1A7F" stroke="#000" stroke-width="5"/><circle cx="46" cy="6" r="7" fill="#FF1A7F" stroke="#000" stroke-width="5"/></g>
      <g class="lr-spark" transform="translate(826 30)"><path d="M0 -38 L7 -7 L38 0 L7 7 L0 38 L-7 7 L-38 0 L-7 -7 Z" fill="#ffffff"/><circle r="9" fill="#ffffff" opacity=".6"/></g>
      <g class="lr-spark lr-spark2" transform="translate(420 300) scale(.45)"><path d="M0 -38 L7 -7 L38 0 L7 7 L0 38 L-7 7 L-38 0 L-7 -7 Z" fill="#ffffff"/></g></svg>`;
    const ART = "/static/lowrider/title.webp" + (BUILD ? "?v=" + encodeURIComponent(BUILD) : "");
    function lrStages() {
      return `<div class="lr-stages" role="radiogroup" aria-label="Stage">` + STAGES.map((s) => `<button type="button" class="lr-stg${s.id === stage.id ? " on" : ""}" role="radio" aria-checked="${s.id === stage.id ? "true" : "false"}" data-act="stage" data-id="${esc(s.id)}"><b>${esc(s.name)}</b><small>${esc(s.blurb)}</small></button>`).join("") + `</div>`;
    }
    function showTitle() {
      if (run && !run.over) endRunQuiet(); clearLater(); toasts.replaceChildren(); car.charging = false; audio.fx.pumpStop(); // v49.26
      mode = "title"; auto = true; run = null; garage.open = false; garage.preview = null; garage.car = null; audio.stopMusic();
      overlay(`<div class="lr-card lr-title">
        <div class="lr-hero"><img class="lr-hero-img" src="${ART}" alt="" width="1100" height="733" decoding="async">${LOGO}</div>
        <h2 class="lr-sr">${TITLE}</h2>
        <p class="lr-tag">Hop it. Drop it. Don't scrape it.</p>
        ${lrStages()}
        <button type="button" class="lr-btn lr-go lr-big" data-act="start">▶ Cruise</button>
        ${lapBtn()}
        <div class="lr-row"><button type="button" class="lr-btn lr-turq" data-act="garage">Garage</button><button type="button" class="lr-btn lr-ghost" data-act="runs">Best runs</button><button type="button" class="lr-btn lr-ghost" data-act="trophies">Trophies</button></div>
        <p class="lr-meta"><span class="lr-fbal">${SVGF}<b>${num(st.feria)}</b> Feria</span><span class="lr-dot" aria-hidden="true">·</span>Best <b>${num(st.best)}</b></p>
        <button type="button" class="lr-link" data-act="howto">How to play</button></div>`, "title");
      ctrl();
    }
    function showHowto(thenStart) {
      overlay(`<div class="lr-card lr-howto"><h3 class="lr-h">How to hop</h3>
        <ol class="lr-steps">
          <li><b>HOLD</b> anywhere to charge the hydraulics. Longer = higher.</li>
          <li><b>LET GO</b> to hop over potholes, cones, couches and whatever your cousin left in the street.</li>
          <li><b>TAP</b> right before you land, when the white ring meets the dashed one. Nail it for a <b>PERFECT HOP!</b> and build the combo.</li>
        </ol>
        <p class="lr-sub">Stop for Abuela. Hop the low chancla, stay low for the high one. Three wheels and you're done.${SM && SM.fuel ? " In San Antonio, hop the traffic and grab gas cans before the tank runs dry." : ""}</p>
        <button type="button" class="lr-btn lr-go lr-big" data-act="${thenStart ? "gotit" : "title"}">${thenStart ? "Let's ride" : "Got it"}</button></div>`, "howto");
    }
    function lrRows() {
      if (!st.runs.length) return `<p class="lr-empty">No runs yet. Go cruise.</p>`;
      return `<ol class="lr-runs">` + st.runs.map((r, i) => `<li><span class="lr-rk">${num(i + 1)}</span><span class="lr-rs"><b>${num(r.score)}</b><small>${esc((r.meters / MILE).toFixed(2))} mi · ${num(r.perfects)} perfect · x${num(r.combo)}</small></span><span class="lr-rd">${esc(new Date(r.at).toLocaleDateString("en-US", { month: "short", day: "numeric" }))}</span></li>`).join("") + `</ol>`;
    }
    function showRuns() {
      overlay(`<div class="lr-card lr-list"><h3 class="lr-h">Your best runs</h3>${lrRows()}<p class="lr-sub">Saved on this phone.</p><button type="button" class="lr-btn lr-ghost" data-act="title">Back</button></div>`, "runs");
    }
    function lrTrophies() {
      return `<ul class="lr-trophies">` + ACH.map((a) => { const got = !!st.ach[a.id], prog = a.goal ? Math.min(a.goal, st.totals[a.of] || 0) : null;
        return `<li class="${got ? "got" : ""}"><span class="lr-tic" aria-hidden="true"></span><span><b>${esc(a.name)}</b><small>${esc(a.desc)}${prog != null && !got ? " · " + num(prog) + " / " + num(a.goal) : ""}</small></span><span class="lr-tst">${got ? "Unlocked" : "Locked"}</span></li>`; }).join("") + `</ul>`;
    }
    function showTrophies() {
      overlay(`<div class="lr-card lr-list"><h3 class="lr-h">Trophies</h3>${lrTrophies()}<button type="button" class="lr-btn lr-ghost" data-act="title">Back</button></div>`, "trophies");
    }
    function overEnd(fin, bonus) {   // the bonus line + the big button (a stage's finish: its bonus, then Otra vuelta)
      if (fin) return `<p class="lr-sub lr-small lr-finbonus">${esc(fin.bonus)}</p><button type="button" class="lr-btn lr-go lr-big" data-act="lap">${esc(fin.again)}</button>`;
      return (bonus > 0 ? `<p class="lr-sub lr-small">Includes distance bonus Feria.</p>` : "") + `<button type="button" class="lr-btn lr-go lr-big" data-act="start">Play again</button>`;
    }
    function showOver(rec, newBest, rank, bonus, reason) {
      const line = OVER_LINES[(rand() * OVER_LINES.length) | 0], fin = reason === "finish" && SX && SX.finish ? SX.finish(rec) : null;   // a stage's finish (San Antonio: ¡LLEGASTE!)
      overlay(`<div class="lr-card lr-over${fin ? " lr-fin" : ""}"><h3 class="lr-h">${esc(fin ? fin.title : reason === "quit" ? "Parked" : reason === "gas" ? "Out of gas" : "Game over")}</h3><p class="lr-sub">${esc(fin ? fin.sub : reason === "quit" ? "You parked " + curCar().name + "." : reason === "gas" ? "Running on fumes, güey. Grab more gas cans next time." : line)}</p>
        <div class="lr-score"><small>Score</small><b>${num(rec.score)}</b>${newBest ? `<span class="lr-new">NEW BEST!</span>` : ""}</div>
        <dl class="lr-stats"><div><dt>Distance</dt><dd>${esc((rec.meters / MILE).toFixed(2))} mi</dd></div><div><dt>Best</dt><dd>${num(st.best)}</dd></div><div><dt>Feria earned</dt><dd>+${num(rec.feria)}</dd></div>
        <div><dt>Perfect hops</dt><dd>${num(rec.perfects)}</dd></div><div><dt>Best combo</dt><dd>x${num(rec.combo)}</dd></div><div><dt>Your rank</dt><dd>#${num(rank + 1)}</dd></div></dl>
        ${overEnd(fin, bonus)}
        <div class="lr-row"><button type="button" class="lr-btn lr-turq" data-act="garage">Garage</button><button type="button" class="lr-btn lr-pink" data-act="share">Share</button><button type="button" class="lr-btn lr-ghost" data-act="title">Back</button></div>${donateBtn()}</div>`, "over");
      lastRec = rec;
    }
    let lastRec = null, lastShare = null;

    // ---- the App Store goal (San Antonio's billboards): the same Buy Me a Coffee goal + in-app reader as the feed's From Chisme card
    // (app.js window.__chismeGoal). Never in the store app (Apple's rules): there the boards are Chisme's own house ad.
    function lapBtn() { return stage.id === "sa" && st.laps[stage.id] ? `<button type="button" class="lr-btn lr-pink lr-lap" data-act="lap">${esc(SM ? SM.lapLabel : "🔁 Otra vuelta (harder)")}</button>` : ""; } // v49.26: show saved unlocks before the lazy stage loads
    function donateOn() { return !!(SM && SM.billboards && !native()); }
    function donateBtn() { const G = root.__chismeGoal; if (!donateOn() || !G || G.native) return "";   // the goal + its link come from app.js (the From Chisme card's), never from the game
      return `<a class="lr-donate" href="${esc(G.url)}" data-act="donate" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">☕</span> ${esc(G.title)}, $${num(G.amount)}<small>Buy Me a Coffee</small></a>`; }
    function donate(a) { const G = root.__chismeGoal; try { fs.exit(true); } catch (e) {} if (G && G.open) G.open(a); else root.open(a.href, "_blank", "noopener"); }

    // ---- garage: rides (unlocked with Feria) + paint for any ride you own
    let gcv = null, gg = null;
    const curCar = () => carById(st.equip.car);
    const gCar = () => carById(garage.car || st.equip.car);
    const ownsCar = (id) => st.owned.car.includes(id);
    function lrCars() {
      return `<div class="lr-cars" role="radiogroup" aria-label="Rides">` + CARS.map((c) => { const own = ownsCar(c.id), on = gCar().id === c.id, eq = st.equip.car === c.id;
        return `<button type="button" class="lr-car${on ? " on" : ""}${own ? "" : " locked"}" role="radio" aria-checked="${on ? "true" : "false"}" data-act="car" data-id="${esc(c.id)}" aria-label="${esc(c.name)}${own ? (eq ? ", riding" : ", unlocked") : ", locked, " + num(c.price) + " Feria"}"><b>${esc(c.name)}</b><small>${eq ? "Riding" : own ? "Unlocked" : (st.feria >= c.price ? "" : "🔒 ") + num(c.price) + " F"}</small></button>`; }).join("") + `</div>`;
    }
    function lrSwatches() {
      const c = gCar(), cur = garage.preview || st.carPaint[c.id] || c.paint, list = [...(c.orig ? [c.orig] : []), ...PAINTS];
      return list.map((p) => { const own = p.id === "orig" || st.owned.paint.includes(p.id), on = cur === p.id, eq = ownsCar(c.id) && (st.carPaint[c.id] || c.paint) === p.id;
        const chip = p.patch ? `background:linear-gradient(90deg,#a2a8b0 0 28%,#9e3a34 28% 56%,#4f9a9e 56% 80%,#c9b9aa 80%)` : `background:linear-gradient(135deg,${esc(p.hi)},${esc(p.mid)} 45%,${esc(p.deep)})`;
        return `<button type="button" class="lr-sw${on ? " on" : ""}" data-act="paint" data-id="${esc(p.id)}" aria-pressed="${on ? "true" : "false"}" aria-label="${esc(p.name)}${own ? "" : ", " + num(p.price) + " Feria"}"><span class="lr-chip" style="${chip}"></span><span class="lr-swn">${esc(p.name)}</span><span class="lr-swp">${eq ? "On it" : own ? "Owned" : num(p.price) + " F"}</span></button>`; }).join("");
    }
    function lrAction() {
      const c = gCar(), pid = garage.preview || st.carPaint[c.id] || c.paint, p = paintFor(c, pid);
      if (!ownsCar(c.id)) return st.feria >= c.price ? `<button type="button" class="lr-btn lr-go" data-act="buycar">Unlock for ${num(c.price)} Feria</button>`
        : `<button type="button" class="lr-btn lr-go" data-act="buycar" disabled>🔒 ${num(c.price)} Feria · earn ${num(c.price - st.feria)} more</button>`;
      const ownP = pid === "orig" || st.owned.paint.includes(pid), riding = st.equip.car === c.id, onIt = (st.carPaint[c.id] || c.paint) === pid;
      if (!ownP) return st.feria >= p.price ? `<button type="button" class="lr-btn lr-go" data-act="buy">Buy ${esc(p.name)} for ${num(p.price)} Feria</button>` : `<button type="button" class="lr-btn lr-go" data-act="buy" disabled>${num(p.price)} Feria · earn ${num(p.price - st.feria)} more</button>`;
      if (riding && onIt) return `<button type="button" class="lr-btn lr-ghost" disabled>Riding it</button>`;
      return `<button type="button" class="lr-btn lr-turq" data-act="equip">${riding ? "Paint it " + esc(p.name) : "Ride it"}</button>`;
    }
    function showGarage() {
      garage.open = true; if (!garage.car) garage.car = st.equip.car; garage.t = 0;
      const c = gCar(), own = ownsCar(c.id), p = paintFor(c, garage.preview || st.carPaint[c.id] || c.paint);
      overlay(`<div class="lr-card lr-garage"><div class="lr-ghead"><h3 class="lr-h">Garage</h3><span class="lr-fbal">${SVGF}<b>${num(st.feria)}</b> Feria</span></div>
        <canvas class="lr-gcv" aria-hidden="true"></canvas>
        <p class="lr-gname"><b>${esc(c.name)}</b> · ${own ? esc(p.name) : "Locked"}</p><p class="lr-sub lr-small lr-blurb">${esc(c.blurb)}</p>
        ${lrCars()}
        ${own ? `<div class="lr-sws${c.orig ? " lr-sws6" : ""}" role="group" aria-label="Paint">${lrSwatches()}</div>` : `<p class="lr-sub lr-small">Unlock it to paint it. Paint you own works on every ride.</p>`}
        ${lrAction()}
        <p class="lr-sub lr-small">Feria is earned only by playing. Nothing here costs real money.</p>
        <button type="button" class="lr-btn lr-ghost" data-act="title">Back</button></div>`, "garage");
      gcv = ov.querySelector(".lr-gcv"); gg = gcv.getContext("2d"); sizeGarage();
    }
    function sizeGarage() { if (!gcv) return; const w = Math.max(200, gcv.clientWidth || 300), h = Math.round(w * 0.5); gcv.width = Math.round(w * dpr); gcv.height = Math.round(h * dpr); gcv.style.height = h + "px"; }
    function drawGarage(t) {
      if (!gcv || !gcv.isConnected) return;
      const W = gcv.width / dpr, H = gcv.height / dpr, s = Math.min(W / 300, H / 150);
      gg.setTransform(dpr, 0, 0, dpr, 0, 0);
      gg.fillStyle = lg(gg, 0, 0, 0, H, [[0, "#1a0a2e"], [0.7, "#2a1240"], [1, "#120822"]]); gg.fillRect(0, 0, W, H);
      gg.fillStyle = "rgba(255,255,255,.05)"; for (let x = 0; x < W; x += 22) gg.fillRect(x, 0, 1, H * 0.72);
      gg.fillStyle = "#0d0618"; gg.fillRect(0, H * 0.78, W, H);
      gg.fillStyle = rg(gg, W / 2, H * 0.8, 4, W * 0.45, [[0, "rgba(255,26,127,.35)"], [1, "rgba(255,26,127,0)"]]); gg.fillRect(0, H * 0.5, W, H * 0.5);
      gg.save(); gg.font = `900 ${14 * s}px ${FONT}`; gg.textAlign = "center"; gg.fillStyle = "rgba(0,201,205,.85)"; gg.fillText("PURO 210 · HYDRAULICS", W / 2, 22 * s); gg.restore();
      gg.save(); gg.translate(W / 2 - 100 * s, 0); gg.scale(s, s);
      const reduce = reduced(), d = reduce ? 0 : t;
      const sR = Math.max(0, Math.sin(d * 3.2)) * 7, sF = Math.max(0, Math.sin(d * 3.2 + 1.6)) * 9, bounce = reduce ? 0 : Math.max(0, Math.sin(d * 1.6)) * 6;
      const gc = gCar(), locked = !ownsCar(gc.id);
      drawCar(gg, { x: 0, gy: 132, y: locked ? 0 : bounce, sR: locked ? 0 : sR, sF: locked ? 0 : sF, ang: 0, rot: 0, t, P: P(), car: gc, lights: !locked, blur: false, brake: false, bob: 0, driver: !locked });
      gg.restore();
      if (locked) { gg.fillStyle = "rgba(10,4,24,.45)"; gg.fillRect(0, 0, W, H); const lx = W / 2, ly = H * 0.48;
        gg.fillStyle = "rgba(0,0,0,.8)"; rr(gg, lx - 64 * s, ly - 16 * s, 128 * s, 32 * s, 16 * s); gg.fill(); gg.strokeStyle = "#fff"; gg.lineWidth = 2; rr(gg, lx - 64 * s, ly - 16 * s, 128 * s, 32 * s, 16 * s); gg.stroke();
        gg.font = `900 ${13 * s}px ${SANS}`; gg.textAlign = "center"; gg.textBaseline = "middle"; gg.fillStyle = "#fff"; gg.fillText("LOCKED · " + num(gc.price) + " F", lx, ly + 0.5); }
    }

    // ---- share (Chisme's own share sheet when available)
    function share() {
      const sc = lastRec ? lastRec.score : st.best, base = (root.__chismeShare && root.__chismeShare.base) || location.origin, where = lastRec && lastRec.stage === "sa" ? "San Antonio" : "the boulevard";
      const text = `I ${lastRec && lastRec.fin ? "made it to the Hon Dipo party in San Antonio" : "hopped " + where} for ${num(sc)} in ${TITLE} 🚘 Think you can beat it? Download Chisme 👀 San Antonio's news, weather, sports and events in one free app:`;
      const data = { title: TITLE + " · Chisme", text, url: base + "/#puro-pinche-lowrider" }; lastShare = data;
      try { if (root.__chismeShare && root.__chismeShare.share) return Promise.resolve(root.__chismeShare.share(data)).catch(() => {}); } catch (e) {}
      try { if (navigator.share) return navigator.share(data).catch(() => {}); } catch (e) {}
      try { Promise.resolve(navigator.clipboard.writeText(text + " " + data.url)).then(() => { if (alive) toast("Link copied", "Send it to the group chat."); }, () => {}); } catch (e) {}
    }

    // ---- controls
    function setMute(m, user) { muted = m; audio.setMuted(m); if (user) { st.muted = m; save(st); } if (!m && mode === "run") audio.startMusic(); ctrl(); }
    function ctrl() {
      soundBtn.innerHTML = muted ? `<span aria-hidden="true">🔇</span>` : `<span aria-hidden="true">🔊</span>`; soundBtn.setAttribute("aria-label", muted ? "Sound off" : "Sound on"); soundBtn.setAttribute("aria-pressed", muted ? "false" : "true");
      pauseBtn.disabled = !(mode === "run" || mode === "paused"); pauseBtn.setAttribute("aria-label", mode === "paused" ? "Resume" : "Pause");
    }
    function setRide(c, pid) { st.carPaint[c.id] = pid; if (st.equip.car === c.id) st.equip.paint = pid; }
    // v49.26: another mounted tab may have spent or earned Feria since this mount.
    function syncWallet() { try { const raw = localStorage.getItem(SAVE_KEY); if (!raw) return; const o = migrate(JSON.parse(raw)), previous = walletSaved.get(st); if (previous != null) st.feria = Math.max(0, st.feria + o.feria - previous); walletSaved.set(st, o.feria); // v49.26: apply external changes without discarding unsaved local Feria
      st.owned.car = [...new Set([...st.owned.car, ...o.owned.car])]; st.owned.paint = [...new Set([...st.owned.paint, ...o.owned.paint])]; } catch (e) {} }
    function buy() {
      syncWallet();
      const c = gCar(), p = PAINTS.find((x) => x.id === garage.preview); if (!p || !ownsCar(c.id) || st.owned.paint.includes(p.id) || st.feria < p.price) { showGarage(); return; } // v49.26: refresh stale purchase button states
      st.feria -= p.price; st.owned.paint.push(p.id); setRide(c, p.id); st.equip.car = c.id; st.equip.paint = p.id; save(st); audio.fx.coin(); audio.fx.tier(2); toast("Fresh paint", p.name + " on " + c.name + "."); showGarage();
    }
    function buyCar() {
      syncWallet();
      const c = gCar(); if (ownsCar(c.id) || st.feria < c.price) { showGarage(); return; } // v49.26
      st.feria -= c.price; st.owned.car.push(c.id); st.equip.car = c.id; st.equip.paint = st.carPaint[c.id] || c.paint; garage.preview = null; save(st);
      audio.fx.coin(); audio.fx.tier(3); toast("New ride unlocked", c.name + " is in the garage."); showGarage();
    }
    function act(a, btn) {
      audio.unlock(); audio.fx.click();
      if (a === "start") startRun();
      else if (a === "lap") startRun({ lap: 2 });   // Otra vuelta: the harder lap (unlocked by finishing San Antonio)
      else if (a === "gotit") { st.howto = true; save(st); startRun(); }
      else if (a === "howto") showHowto(false);
      else if (a === "title") showTitle();
      else if (a === "garage") { if (mode === "over") { mode = "title"; run = null; auto = true; } fs.enter(); showGarage(); }
      else if (a === "runs") showRuns();
      else if (a === "trophies") showTrophies();
      else if (a === "paint") { garage.preview = btn.dataset.id; showGarage(); }
      else if (a === "car") { garage.car = btn.dataset.id; garage.preview = null; showGarage(); }
      else if (a === "buy") buy();
      else if (a === "buycar") buyCar();
      else if (a === "equip") { const c = gCar(), pid = garage.preview || st.carPaint[c.id] || c.paint; if (ownsCar(c.id) && (pid === "orig" || st.owned.paint.includes(pid))) { setRide(c, pid); st.equip.car = c.id; st.equip.paint = pid; garage.preview = null; save(st); showGarage(); } }
      else if (a === "stage") { const id = btn.dataset.id; if (id !== stage.id || stageLoading || (stage.file && !SM)) { const s = STAGES.find((x) => x.id === id); if (s && s.file && !lib.stages[s.id]) { btn.classList.add("busy"); } useStage(id).then((s) => { if (alive && s && mode === "title") showTitle(); }, () => { if (!alive) return; toast("Couldn't load " + (s ? s.name : id), "Check your connection and try again."); if (mode === "title") showTitle(); }); } } // v49.26: allow loading the saved selection on a fresh mount
      else if (a === "donate") donate(btn);
      else if (a === "share") share();
      else if (a === "resume") resume();
      else if (a === "restart") { const lap = run && run.lap; endRunQuiet(); startRun({ lap }); } // v49.26: preserve Otra vuelta difficulty
      else if (a === "quit") endRun("quit");
      else if (a === "pause") { mode === "paused" ? resume() : pause(); }
      else if (a === "sound") setMute(!muted, true);
    }
    function endRunQuiet() { if (run && !run.over && !run.god) { run.over = true; syncWallet(); st.feria += run.feria; st.totals.runs++; st.totals.meters += Math.round(run.meters); st.totals.feria += run.feria; save(st); } restoreGod(); run = null; }
    const onClick = (e) => { const b = e.target.closest("[data-act]"); if (!b || b.disabled) return; e.preventDefault(); e.stopPropagation(); act(b.dataset.act, b); };
    ov.addEventListener("click", onClick); pauseBtn.addEventListener("click", onClick); soundBtn.addEventListener("click", onClick);
    const onDown = (e) => { if (e.target.closest("button,a,.lr-card,.lr-god")) return; if (mode !== "run") return; e.preventDefault(); inputDownAt = performance.now(); try { wrap.setPointerCapture(e.pointerId); } catch (x) {} press(); };
    const onUp = (e) => { if (mode !== "run") return; release(); };
    // v49.27: cancel touch scrolling at contact; pointer browsers must not double-press.
    wrap.style.touchAction = "none"; wrap.style.userSelect = "none"; wrap.style.webkitUserSelect = "none";
    const onTouch = (e) => { if (e.target.closest("button,a,.lr-card,.lr-god")) return; e.preventDefault(); if (!root.PointerEvent) { if (e.type === "touchstart") { inputDownAt = performance.now(); press(); } else release(); } };
    for (const type of ["touchstart", "touchend", "touchcancel"]) wrap.addEventListener(type, onTouch, { passive: false });
    wrap.addEventListener("pointerdown", onDown); wrap.addEventListener("pointerup", onUp); wrap.addEventListener("pointercancel", onUp);
    const onContext = (e) => e.preventDefault(); wrap.addEventListener("contextmenu", onContext);
    const keyOk = () => el.isConnected && (fs.on || el.getBoundingClientRect().top < innerHeight) && !/INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || "");
    const onKey = (e) => {
      if (!keyOk()) return; const k = e.key, hop = k === " " || k === "ArrowUp" || k === "w" || k === "W";
      if (hop && mode === "run") { e.preventDefault(); if (e.type === "keydown") { if (!e.repeat) press(); } else release(); }
      else if ((k === "p" || k === "P" || k === "Escape") && e.type === "keydown" && (mode === "run" || mode === "paused")) { if (k === "Escape" && mode === "paused") return; e.preventDefault(); mode === "paused" ? resume() : pause(); }
    };
    addEventListener("keydown", onKey); addEventListener("keyup", onKey);
    const onVis = () => { if (document.hidden) { pause(); audio.setMuted(true); audio.stopMusic(); } else { audio.setMuted(muted); last = 0; kick(); } }; // v49.26
    document.addEventListener("visibilitychange", onVis);
    const onFullscreen = () => { if (fs.on && !document.fullscreenElement) fs.exit(true); }; // v49.26: native browser exit also pauses the CSS fullscreen game
    document.addEventListener("fullscreenchange", onFullscreen);
    const onStorage = (e) => { if (e.key === "chisme-feed-sound" && st.muted === null) setMute(appMuted(), false); };
    addEventListener("storage", onStorage);
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(() => { fit(); sizeGarage(); }) : null; if (ro) ro.observe(wrap);

    // ---- loop
    let raf = 0, last = 0, acc = 0, alive = true;
    function frame(now) {
      raf = 0; if (!alive) return;
      const dt = Math.min(1 / 15, last ? (now - last) / 1000 : 0.016); last = now;
      const visible = !document.hidden && el.isConnected;
      if (visible && !frozen && mode !== "paused" && mode !== "over") { acc += dt; while (acc >= 1 / 120) { step(1 / 120); acc -= 1 / 120; } }
      else if (visible && mode === "over" && !frozen) { acc += dt; while (acc >= 1 / 120) { step(1 / 120); acc -= 1 / 120; } }
      if (garage.open) { garage.t += dt; drawGarage(garage.t); }
      // v49.27: interpolate drawing only; collision and gameplay stay at 120Hz.
      const snap = [camX, car.x, car.y], a = frozen ? 1 : acc * 120;
      camX = lerp(prevCam, camX, a); car.x = lerp(prevX, car.x, a); car.y = lerp(prevY, car.y, a); draw();
      [camX, car.x, car.y] = snap;
      if (visible) kick();
    }
    function kick() { if (!raf && alive) raf = requestAnimationFrame(frame); } // v49.26: retain frame timestamps

    // ---- public surface (juegos.js: pause/destroy/exitFullscreen; tests: state + debug)
    // the kernel a stage file plugs into (see lowrider-sa.js install): the live world through getters / setters, and the game's helpers
    function kernel() {
      const K = { st, H, TIERS, UPM, MILE, audio, rand, pop, burst, crowd, sayLine, num, tierOf, difficulty, cruise, reduced, bubble, startCharge, release, launch, startEvent, endRun, save: () => save(st) };
      const v = { run: () => run, car: () => car, camX: () => camX, mode: () => mode, LW: () => LW, LH: () => LH, GY: () => GY, evOn: () => evOn, stage: () => stage }, w = { ev: [() => ev, (x) => (ev = x)], obs: [() => obs, (x) => (obs = x)],
        coins: [() => coins, (x) => (coins = x)], picks: [() => picks, (x) => (picks = x)], bubbles: [() => bubbles, (x) => (bubbles = x)], hold: [() => hold, (x) => (hold = x)], nextObs: [() => nextObs, (x) => (nextObs = x)] };
      for (const n in v) Object.defineProperty(K, n, { get: v[n] }); for (const n in w) Object.defineProperty(K, n, { get: w[n][0], set: w[n][1] });
      return K;
    }
    // v49.27: only the authenticated private script receives these closures.
    function sandboxGod() { if (!godSnapshot) godSnapshot = JSON.stringify(st); godSaves.add(st); if (run) run.god = true; }
    function restoreGod() { if (godSnapshot) { const old = JSON.parse(godSnapshot); for (const k of Object.keys(st)) delete st[k]; Object.assign(st, old); godSnapshot = null; } godSaves.delete(st); }
    const godHooks = { el: wrap, get: () => ({ ...god }), set(o) { god = { ...god, ...o }; if (![0.5, 1, 2, 3].includes(god.speed)) god.speed = 1; if (god.on) sandboxGod(); },
      async skip(to) { sandboxGod(); if (stage.id !== "sa") { endRunQuiet(); mode = "title"; await useStage("sa"); } if (!alive) return; if (!run || mode !== "run") startRun(); if (!run) return; run.god = true;
        if (to === "lap") { const lap = run.lap + 1; endRunQuiet(); startRun({ lap }); sandboxGod(); }
        else if (to === "party") { ev = null; startEvent("party"); }
        else { car.x = Math.max(car.x, run.goal * 0.25 * UPM); run.meters = car.x / UPM; } }, };
    let godLoading = false, godButton = null;
    const godFlag = () => /(?:[?&#])god=1(?:[&#]|$)/.test(location.search + location.hash);
    function loadGod() { if (native() || godLoading || !/(?:^|;\s*)chisme_admin=1(?:;|$)/.test(document.cookie)) return; godLoading = true;
      const script = document.createElement("script"); script.src = "/stats/lowrider/god.js"; script.async = true;
      script.onload = () => { if (alive && !native() && root.ChismeLowriderGod) godUi = root.ChismeLowriderGod.attach(godHooks, godFlag()); script.remove(); };
      script.onerror = () => { godLoading = false; script.remove(); }; document.head.appendChild(script); }
    if (!native() && /(?:^|;\s*)chisme_admin=1(?:;|$)/.test(document.cookie)) { godButton = document.createElement("button"); godButton.type = "button"; godButton.textContent = "Owner controls"; godButton.onclick = loadGod; el.appendChild(godButton); if (godFlag()) loadGod(); }
    const api = {
      pause() { pause(); },
      exitFullscreen() { fs.exit(true); },
      destroy() {
        if (!alive) return; alive = false; ++stageRequest; for (const cancel of stageCancels) cancel(); clearLater(); if (raf) cancelAnimationFrame(raf); raf = 0; if (run && !run.over && mode !== "over") endRunQuiet();
        removeEventListener("keydown", onKey); removeEventListener("keyup", onKey); document.removeEventListener("visibilitychange", onVis); document.removeEventListener("fullscreenchange", onFullscreen); removeEventListener("storage", onStorage);
        ov.removeEventListener("click", onClick); pauseBtn.removeEventListener("click", onClick); soundBtn.removeEventListener("click", onClick);
        for (const type of ["touchstart", "touchend", "touchcancel"]) wrap.removeEventListener(type, onTouch);
        if (godUi) godUi.destroy(); if (godButton) godButton.remove(); restoreGod();
        wrap.removeEventListener("pointerdown", onDown); wrap.removeEventListener("pointerup", onUp); wrap.removeEventListener("pointercancel", onUp); wrap.removeEventListener("contextmenu", onContext);
        if (ro) ro.disconnect(); audio.close(); try { fs.exit(true); } catch (e) {}
        if (lib.current === api) lib.current = null; el.innerHTML = "";
      },
      get state() {
        return { mode, score: run ? Math.round(run.score) : 0, meters: run ? run.meters : 0, runFeria: run ? run.feria : 0, feria: st.feria, best: st.best, streak: run ? run.streak : 0, mult: run ? TIERS[run.tier].x : 1,
          god: !!(god && god.on), godRun: !!(run && run.god), inputLagMs, cleared: { ...(run && run.cleared) }, sponsorSlots: sponsors.map((s) => ({ ...s, colors: [...s.colors] })), lives: run ? run.lives : 3, air: car.air, charging: car.charging, charge: car.charge, y: car.y, tLand: tLand(), tapped: car.tapped, pend: !!car.pend, lastGrade, grades: { ...gradeCounts }, hops: st.totals.hops,
          paint: st.equip.paint, owned: [...st.owned.paint], car: st.equip.car, cars: [...st.owned.car], carPaint: { ...st.carPaint }, stage: stage.id, stageLoaded: !!SM, native: native(),
          fuel: run ? run.fuel : null, outOfGas: run ? run.out : false, picks: run ? { ...run.picks } : null, cops: run ? run.cops : 0, trafficCleared: run ? run.traffic : 0, salutes: run ? run.salutes : 0, trails: run ? run.trails : 0, chase: SX && SX.state ? SX.state() : null, laps: { ...st.laps }, lap: run ? run.lap : null, boost: run ? run.boost || 0 : 0,
          traffic: obs.filter((o) => o.T).map((o) => ({ id: o.T.id, name: o.T.name, x: Math.round(o.x - car.x), vx: Math.round(o.vx), hit: o.hit, cleared: o.cleared })), bubbles: bubbles.map((b) => b.text),
          tags: lots.filter((L) => L.tag).map((L) => L.tag), lotKinds: lots.map((L) => L.kind), pickList: picks.filter((c) => !c.got).map((c) => ({ kind: c.kind, x: Math.round(c.x - car.x), h: Math.round(c.h) })), event: ev ? { type: ev.type, phase: ev.phase, high: !!ev.high } : null, overlay: ovKind, overlayText: ov.textContent.replace(/\s+/g, " ").trim(),
          pops: popList.map((p) => ({ ...p })), bubbleList: bubbleList.map((b) => ({ ...b, lines: [...b.lines] })), finishTitle, // v49.26
          fullscreen: !!fs.on, LW, LH, GY, dpr, backing: [cv.width, cv.height], css: [cssW, cssH], muted, audio: audio.state, music: audio.playing, spoken: [...spoken], ach: Object.keys(st.ach),
          lastShare, garage: garage.open ? garage.preview : null, obstacles: obs.map((o) => ({ kind: o.kind, x: Math.round(o.x - car.x), hit: o.hit, cleared: o.cleared })),
          signs: { lots: lots.filter((L) => L.sign).map((L) => L.sign.name), billboards: bbs.map((b) => b.s.name), log: [...bbLog] }, season, carPos: { x: car.x, front: car.x + 200, v: car.v }, crosswalk: ev && (ev.type === "abuela" || ev.stop) ? ev.x : null };
      },
      debug: {
        refreshSponsors() { bbs = []; bbCache.clear(); bbEnd = camX * 0.35; houseIn = 2; spawnAhead(); draw(); },
        auto(on) { auto = !!on; }, events(on) { evOn = !!on; }, freeze(on) { frozen = !!on; if (!on) kick(); }, zoom(z) { zoom = z || 1; draw(); }, draw() { draw(); }, step(sec = 0.1) { const n = Math.round(sec * 120); for (let i = 0; i < n; i++) step(1 / 120); draw(); },
        clear() { obs = []; coins = []; bubbles = []; pops = []; nextObs = car.x + 99999; hold = 0; }, spawn(kind, dx = 360) { const O = OBST[kind]; obs.push({ kind, x: car.x + 200 + dx, w: O.w, h: O.h, pit: !!O.pit, soft: !!O.soft, hit: false, cleared: false, knock: null }); },
        hold(on) { hold = on ? car.x + 1e9 : 0; nextObs = on ? car.x + 1e9 : car.x + 600; }, event(type, opt) { ev = null; return startEvent(type, opt || {}); },
        set(o) { if (o.feria != null) st.feria = o.feria; if (o.best != null) st.best = o.best; if (run && o.streak != null) { run.streak = o.streak; run.tier = tierOf(o.streak); } if (run && o.score != null) run.score = o.score; if (run && o.meters != null) { car.x = o.meters * UPM; run.meters = o.meters; } if (run && o.lives != null) run.lives = o.lives; if (o.y != null) car.y = o.y; save(st); },
        feria(n) { st.feria = n; save(st); }, end(reason) { endRun(reason || "wrecked"); }, press, release, launch(c) { car.charging = true; car.charge = c; launch(); },
        crowd(mood, text) { crowd(mood, 1, text); }, pop(grade) { resolve(grade); },
        billboards(names) { bbs = []; bbCache.clear(); let x = camX * 0.35 + 12; for (const n of names) { const s = SIGNS.find((q) => q.name === n) || (SM && SM.billboards ? SM.billboards(native()).find((q) => q && q.name === n) : null); if (s) { bbs.push({ x, s, w: 196, h: 236 }); x += 222; } } bbEnd = x + 9999; draw(); },
        lots(kinds, dx = -10) { lots = []; lotCache.clear(); people = []; dogs = []; props = []; let x = camX * 0.6 + dx; for (const k of kinds) { if (!SM) lotI = LOT_BAG.indexOf(k); lotEnd = x; addLot(SM ? k : undefined); if (SM) lots[lots.length - 1].gap = 0; x = lotEnd; } lotEnd = x + 99999; draw(); },
        stage(id) { return useStage(id); }, traffic(id, dx = 360, vx) { const T = SM && SM.traffic.find((q) => q.id === id); if (!T || !SX) return false; const o = SX.addTraffic(T, car.x + 200 + dx, difficulty()); o.x = car.x + 200 + dx; if (vx != null) o.vx = vx; return true; },
        pick(kind, dx = 300, h = 30) { if (SX) SX.addPick(kind, car.x + 200 + dx, h); }, fuel(f) { if (run) { run.fuel = f; if (f > 0) run.out = false; } }, picksClear(noGas) { picks = []; if (run && noGas) run.nextGas = 1e12; },
        unlockAll() { st.owned.car = CARS.map((c) => c.id); save(st); }, ride(id, paint) { const c = carById(id); st.equip.car = c.id; st.equip.paint = paint || st.carPaint[c.id] || c.paint; st.carPaint[c.id] = st.equip.paint; save(st); draw(); },
        garageCar(id) { garage.car = id; garage.preview = null; showGarage(); },
        sim(sec = 0.1) { const n = Math.round(sec * 120); for (let i = 0; i < n; i++) step(1 / 120); }, get obs() { return obs; }, title() { showTitle(); }, fs() { fs.enter(); fit(); }, garage() { showGarage(); }, howto() { showHowto(true); }, mode() { return mode; }, car,
      },
    };
    lib.current = api;
    try { if (document.fonts && document.fonts.load) Promise.all([document.fonts.load('400 24px "Lowrider Display"'), document.fonts.load('700 24px "PPL Display"')]).then(() => { if (alive) { lotCache.clear(); bbCache.clear(); draw(); } }, () => {}); } catch (e) {}
    fit(); showTitle(); kick();
    return api;
  }

  const lib = { mount, TITLE, STAGES, stages: {}, carById, PAINTS, CARS, WHEELS: { chrome: WHEEL_CHROME, bronze: WHEEL_BRONZE }, PATCH, OBST, EVENTS, SIGNS, SPONSOR_SLOTS, setSponsors, ACH, GRADES, TIERS, WIN, SAVE_KEY, load, save, reset, migrate, fresh, BOARD, isoWeek, gradeFor, tierOf, current: null };
  root.ChismeLowrider = lib;
})(window);
