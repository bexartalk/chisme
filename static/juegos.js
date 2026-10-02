/* Chisme · 🎲 Juegos: a list of small games that run entirely on the phone (offline, no outside requests).
   Add a game by pushing { id, name, emoji, blurb, mount(el, ctx) } onto GAMES; the tab lists them and mounts one.
   Game 1: Lotería Chismosa. v41: the 54 traditional cards and verses, called in Spanish, with our own original art
   (static/loteria_cards.js); the UI around the game stays English.
   v40: the tab is called 🎲 Juegitos (the view id stays "juegos"); games play full screen in portrait (fullscreen() below). */
(function (root) {
  "use strict";
  const KEY = "chisme-juegos";
  const FIESTA = ["#00b8b0", "#ff3d8b", "#ff8a00", "#111111", "#b9c0c7"];   // turquoise, pink, orange, black, silver
  // v41: the 54 traditional cards (names + folk verses) with our own original SVG art, from static/loteria_cards.js
  const LC = typeof module === "object" && module.exports ? require("./loteria_cards.js") : root.ChismeLoteriaCards;
  const CARDS = LC.CARDS, callText = LC.callText, LINES_ES = LC.LINES_ES, PRESETS = LC.PRESETS || [];
  // the UI text is English; what Tía says out loud (the calls, ¡Lotería!) is Spanish
  const BRAG = ["¡Lotería! I told you today was your day, honey.", "That's it! Not even the neighbor saw that coming.", "¡Lotería! I'm making you my official best friend.",
    "You won! I'm telling the group chat right now.", "What luck! Share your secret with me, okay?"];
  const TEASE_EARLY = "Oh honey, that card hasn't been called yet. No cheating at this table.";
  const TEASE_NOPE = "Not yet, sweetheart. You're almost there, keep playing.";
  const SPEEDS = { slow: 7000, normal: 4500, fast: 2800 };
  const SPEED_LABEL = { slow: "🐢 Slow", normal: "🚶 Normal", fast: "🐇 Fast" };

  // ---- pure game logic (tested in Node) ----
  function shuffle(a, rand = Math.random) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  const newTabla = (rand) => shuffle(CARDS.map((c) => c.id), rand).slice(0, 16);   // 4×4, row by row
  const newDeck = (rand) => shuffle(CARDS.map((c) => c.id), rand);
  const LINES = [];
  for (let r = 0; r < 4; r++) LINES.push({ kind: "row", cells: [0, 1, 2, 3].map((c) => r * 4 + c) });
  for (let c = 0; c < 4; c++) LINES.push({ kind: "column", cells: [0, 1, 2, 3].map((r) => r * 4 + c) });
  LINES.push({ kind: "diagonal", cells: [0, 5, 10, 15] }, { kind: "diagonal", cells: [3, 6, 9, 12] }, { kind: "corners", cells: [0, 3, 12, 15] });
  // marks: Set of cell indexes (0–15); called: Set of card ids already called. A line only counts when every card
  // in it was both marked and actually called.
  function check(tabla, marks, called) {
    const early = [...marks].filter((i) => !called.has(tabla[i]));
    for (const L of LINES) if (L.cells.every((i) => marks.has(i) && called.has(tabla[i]))) return { win: true, line: L, early };
    return { win: false, line: null, early };
  }

  function load() { try { return Object.assign({ wins: 0, streak: 0, best: 0, played: 0, muted: false, speed: "normal" }, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) { return { wins: 0, streak: 0, best: 0, played: 0, muted: false, speed: "normal" }; } }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  const reset = () => { try { localStorage.removeItem(KEY); } catch (e) {} };

  // ---- v40: full-screen portrait play (shared by every game) ----
  // A fixed overlay over the whole screen (100dvh + the safe areas), the tab bar, footer and Tía's button hidden, a small
  // title badge at the top center and a ✕ at the top right that stops the game and goes back to the Juegitos list.
  // The overlay alone works on iPhone Safari and the home-screen app; the Fullscreen API is only a bonus where a phone
  // has it (Android), and it's never required.
  function fullscreen(stageEl, opts) {
    let on = false;
    const bar = document.createElement("div");
    bar.className = "gfs-bar";
    const items = opts.barItems || [];   // v43: controls that live in the bar while full screen (Lotería: the tabla picker + the bean count)
    if (items.length) bar.classList.add("gfs-bar-x");
    bar.innerHTML = (items.length ? "" : `<span class="gfs-side" aria-hidden="true"></span>`) + `<div class="gfs-badge ${opts.badgeClass || ""}">${opts.badge || esc(opts.title)}<span class="sr-only">${esc(opts.title)}</span></div>`
      + (items.length ? `<div class="gfs-extra"></div>` : "")
      + `<button type="button" class="gfs-x" aria-label="Exit ${esc(opts.title)} and go back to Juegitos"><span aria-hidden="true">✕</span></button>`;
    const homes = items.map((n) => ({ n, parent: n.parentNode, next: n.nextSibling }));
    bar.querySelector(".gfs-x").addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); exit(); });
    const onKey = (e) => { if (on && e.key === "Escape" && !document.querySelector("dialog[open]")) { e.preventDefault(); exit(); } };
    const onResize = () => { if (on && opts.onResize) opts.onResize(); };
    function enter() {
      if (on || !stageEl.isConnected) return;
      on = true;
      stageEl.prepend(bar);
      for (const h of homes) bar.querySelector(".gfs-extra").append(h.n);
      stageEl.classList.add("gfs", "no-swipe"); stageEl.setAttribute("aria-label", opts.title + ", full screen");
      document.documentElement.classList.add("game-fs");
      document.addEventListener("keydown", onKey); window.addEventListener("resize", onResize);
      try {   // optional: real browser full screen where it exists (not iPhone); harmless if it's refused
        const d = document.documentElement;
        if (opts.native !== false && d.requestFullscreen && !document.fullscreenElement && matchMedia("(pointer: coarse)").matches
          && !matchMedia("(display-mode: standalone)").matches)
          d.requestFullscreen({ navigationUI: "hide" }).then(() => { try { screen.orientation.lock("portrait").catch(() => {}); } catch (e) {} }).catch(() => {});
      } catch (e) {}
      if (opts.onEnter) opts.onEnter();
    }
    // quiet = leaving because the tab changed or the game was swapped (no scrolling, no onExit)
    function exit(quiet) {
      if (!on) return;
      on = false;
      bar.remove();
      for (const h of homes) if (h.parent) h.parent.insertBefore(h.n, h.next && h.next.parentNode === h.parent ? h.next : null);
      stageEl.classList.remove("gfs", "no-swipe"); stageEl.setAttribute("aria-label", "Game");
      document.documentElement.classList.remove("game-fs");
      document.removeEventListener("keydown", onKey); window.removeEventListener("resize", onResize);
      try { if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {}); } catch (e) {}
      if (quiet === true) { if (opts.onLeave) opts.onLeave(); return; }
      if (opts.onExit) opts.onExit();
      const list = document.querySelector("#juegos");   // back to the list of games
      if (list) { const top = parseFloat(getComputedStyle(document.body).paddingTop) || 70; window.scrollTo(0, Math.max(0, list.getBoundingClientRect().top + window.scrollY - top - 8)); }
    }
    return { enter, exit, get on() { return on; } };
  }

  // ---- Lotería Chismosa UI ----
  // v41: the marker is a pinto bean (frijolito): a kidney shape, pale pinkish-tan with reddish-brown mottling, the little hilum
  // on its inner curve and a soft shadow. Drawn once (<symbol>) and reused on every card.
  const BEAN_DEFS = `<svg class="bean-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs>
    <radialGradient id="bean-body" cx="42%" cy="34%" r="72%"><stop offset="0" stop-color="#f4dcd0"/><stop offset=".5" stop-color="#ddb39c"/><stop offset=".85" stop-color="#b98068"/><stop offset="1" stop-color="#8f5a47"/></radialGradient>
    <radialGradient id="bean-shine" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
    <radialGradient id="bean-shade" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#000" stop-opacity=".38"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
    <clipPath id="bean-clip"><path d="M5 22C5 13 15 9.5 30 10.5C44 11.5 55 14 55 22.5C55 30 47 34 39 33.5C35 33.2 32.5 30.8 29.5 30.8C26.5 30.8 23.5 33.5 17 33.5C9.5 33.5 5 28.5 5 22z"/></clipPath>
    <symbol id="bean" viewBox="0 0 60 44"><ellipse cx="31" cy="36" rx="26" ry="4.5" fill="url(#bean-shade)"/>
      <path d="M5 22C5 13 15 9.5 30 10.5C44 11.5 55 14 55 22.5C55 30 47 34 39 33.5C35 33.2 32.5 30.8 29.5 30.8C26.5 30.8 23.5 33.5 17 33.5C9.5 33.5 5 28.5 5 22z" fill="url(#bean-body)"/>
      <g clip-path="url(#bean-clip)"><ellipse cx="22.2" cy="15.0" rx="5.0" ry="1.0" transform="rotate(2 22.2 15.0)" fill="#a5563a" opacity=".8"/><ellipse cx="10.6" cy="22.1" rx="2.4" ry="1.6" transform="rotate(-22 10.6 22.1)" fill="#8e3f24" opacity=".8"/><ellipse cx="26.7" cy="28.5" rx="2.7" ry="1.2" transform="rotate(6 26.7 28.5)" fill="#8e3f24" opacity=".8"/><ellipse cx="33.8" cy="13.0" rx="3.2" ry="1.7" transform="rotate(-18 33.8 13.0)" fill="#94452a" opacity=".55"/><ellipse cx="31.8" cy="23.4" rx="4.6" ry="1.9" transform="rotate(-20 31.8 23.4)" fill="#7a3420" opacity=".7"/><ellipse cx="12.3" cy="26.2" rx="4.6" ry="1.8" transform="rotate(-0 12.3 26.2)" fill="#94452a" opacity=".7"/><ellipse cx="28.5" cy="30.5" rx="3.8" ry="1.3" transform="rotate(-16 28.5 30.5)" fill="#7a3420" opacity=".55"/><ellipse cx="33.3" cy="22.5" rx="6.0" ry="2.0" transform="rotate(-11 33.3 22.5)" fill="#8e3f24" opacity=".55"/><ellipse cx="30.5" cy="15.3" rx="3.7" ry="2.3" transform="rotate(-4 30.5 15.3)" fill="#8e3f24" opacity=".8"/><ellipse cx="33.2" cy="29.5" rx="3.5" ry="1.9" transform="rotate(5 33.2 29.5)" fill="#94452a" opacity=".55"/><ellipse cx="45.0" cy="30.9" rx="4.2" ry="1.9" transform="rotate(-22 45.0 30.9)" fill="#a5563a" opacity=".8"/><ellipse cx="33.4" cy="25.6" rx="4.1" ry="2.0" transform="rotate(19 33.4 25.6)" fill="#a5563a" opacity=".55"/><ellipse cx="49.4" cy="19.1" rx="4.8" ry="1.6" transform="rotate(-14 49.4 19.1)" fill="#a5563a" opacity=".55"/><ellipse cx="40.5" cy="20.0" rx="6.1" ry="1.6" transform="rotate(-17 40.5 20.0)" fill="#94452a" opacity=".8"/><ellipse cx="20.2" cy="14.7" rx="4.1" ry="1.7" transform="rotate(10 20.2 14.7)" fill="#a5563a" opacity=".8"/><ellipse cx="46.9" cy="31.2" rx="2.8" ry="1.2" transform="rotate(-13 46.9 31.2)" fill="#7a3420" opacity=".55"/><ellipse cx="29.3" cy="23.8" rx="3.3" ry="0.9" transform="rotate(-4 29.3 23.8)" fill="#a5563a" opacity=".8"/><ellipse cx="32.9" cy="31.1" rx="5.2" ry="1.7" transform="rotate(6 32.9 31.1)" fill="#8e3f24" opacity=".7"/><ellipse cx="47.6" cy="27.6" rx="6.0" ry="2.1" transform="rotate(-5 47.6 27.6)" fill="#94452a" opacity=".7"/><ellipse cx="12.6" cy="24.7" rx="2.5" ry="1.0" transform="rotate(-15 12.6 24.7)" fill="#7a3420" opacity=".55"/><ellipse cx="23.0" cy="13.1" rx="2.2" ry="1.1" transform="rotate(-20 23.0 13.1)" fill="#a5563a" opacity=".8"/><ellipse cx="9.1" cy="29.5" rx="4.8" ry="1.1" transform="rotate(-12 9.1 29.5)" fill="#a5563a" opacity=".8"/><ellipse cx="24.0" cy="14.5" rx="5.9" ry="2.4" transform="rotate(-2 24.0 14.5)" fill="#94452a" opacity=".7"/><ellipse cx="11.8" cy="14.0" rx="3.7" ry="1.3" transform="rotate(16 11.8 14.0)" fill="#7a3420" opacity=".8"/><ellipse cx="9.0" cy="31.0" rx="4.5" ry="1.1" transform="rotate(2 9.0 31.0)" fill="#8e3f24" opacity=".8"/><ellipse cx="21.1" cy="24.9" rx="2.6" ry="2.2" transform="rotate(1 21.1 24.9)" fill="#7a3420" opacity=".7"/><circle cx="42.0" cy="22.7" r="1.0" fill="#6e2e1b" opacity=".6"/><circle cx="22.5" cy="16.5" r="1.0" fill="#6e2e1b" opacity=".6"/><circle cx="51.3" cy="29.1" r="1.0" fill="#6e2e1b" opacity=".6"/><circle cx="44.0" cy="26.8" r="0.6" fill="#6e2e1b" opacity=".6"/><circle cx="30.8" cy="19.1" r="0.5" fill="#6e2e1b" opacity=".6"/><circle cx="9.2" cy="17.6" r="0.7" fill="#6e2e1b" opacity=".6"/><circle cx="38.5" cy="31.1" r="0.8" fill="#6e2e1b" opacity=".6"/><circle cx="49.2" cy="31.8" r="1.1" fill="#6e2e1b" opacity=".6"/><circle cx="24.0" cy="16.4" r="0.6" fill="#6e2e1b" opacity=".6"/><circle cx="16.7" cy="16.1" r="0.9" fill="#6e2e1b" opacity=".6"/><circle cx="47.6" cy="28.8" r="0.8" fill="#6e2e1b" opacity=".6"/><circle cx="36.7" cy="28.0" r="0.6" fill="#6e2e1b" opacity=".6"/><circle cx="37.1" cy="30.2" r="1.0" fill="#6e2e1b" opacity=".6"/><circle cx="41.0" cy="21.6" r="0.6" fill="#6e2e1b" opacity=".6"/><circle cx="42.7" cy="18.7" r="1.0" fill="#6e2e1b" opacity=".6"/><circle cx="50.8" cy="19.9" r="0.7" fill="#6e2e1b" opacity=".6"/><circle cx="49.7" cy="26.5" r="0.6" fill="#6e2e1b" opacity=".6"/><circle cx="13.6" cy="15.0" r="1.0" fill="#6e2e1b" opacity=".6"/>
        <path d="M5 22C5 13 15 9.5 30 10.5C44 11.5 55 14 55 22.5C55 30 47 34 39 33.5C35 33.2 32.5 30.8 29.5 30.8C26.5 30.8 23.5 33.5 17 33.5C9.5 33.5 5 28.5 5 22z" fill="none" stroke="#6b3524" stroke-width="3" opacity=".25"/></g>
      <ellipse cx="29.5" cy="29.6" rx="3.6" ry="1.1" fill="#f2eeec"/><ellipse cx="29.5" cy="29.9" rx="3.6" ry=".5" fill="#8f5a47" opacity=".6"/>
      <ellipse cx="24" cy="15" rx="13" ry="3.4" fill="url(#bean-shine)" transform="rotate(-5 24 15)"/>
      <path d="M5 22C5 13 15 9.5 30 10.5C44 11.5 55 14 55 22.5C55 30 47 34 39 33.5C35 33.2 32.5 30.8 29.5 30.8C26.5 30.8 23.5 33.5 17 33.5C9.5 33.5 5 28.5 5 22z" fill="none" stroke="#5a2a18" stroke-width=".7" opacity=".7"/></symbol></defs></svg>`;
  const BEAN = '<svg viewBox="0 0 60 44" focusable="false"><use href="#bean"/></svg>';
  const byId = (id) => CARDS[id - 1];
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // v43: a card is its finished vintage picture (static/loteria/cards/NN.webp: number + name banner drawn in); the name stays as text for screen readers
  const cardHTML = (c, cls = "") => `<span class="lcard ${cls}"><img class="lc-img" src="${c.img}" alt="" decoding="async" draggable="false" width="200" height="300"><span class="lc-name sr-only" lang="es">${esc(c.name)}</span></span>`;

  function mountLoteria(el, ctx) {
    // v49.5: warm all 54 card pictures (~400 KB total, the service worker also precaches them) when the browser is idle, so each called card shows instantly
    const warm = () => { for (const c of CARDS) { const im = new Image(); im.decoding = "async"; im.src = c.img; } };
    if ("requestIdleCallback" in window) requestIdleCallback(warm, { timeout: 2500 }); else setTimeout(warm, 600);
    const reduced = () => (ctx && ctx.reducedMotion ? ctx.reducedMotion() : matchMedia("(prefers-reduced-motion: reduce)").matches);
    const st = load();
    let tabla, deck, called, marks, timer = null, running = false, over = false, started = false;
    // v43: laid out like a real tabla app: the tabla picker + the bean count (in the top bar while playing), the called card in a
    // strip with ▶/⏸ and ¡Lotería!, a 4×4 tabla of big cards, then Limpiar (beans off) and Nueva tabla (a random new mix)
    el.innerHTML = `${BEAN_DEFS}
      <div class="lot-app">
        <div class="lot-head"><button type="button" id="lot-pick" class="lot-pick" aria-haspopup="dialog" aria-expanded="false" aria-controls="lot-sheet"><span id="lot-pick-t"></span><span class="lot-caret" aria-hidden="true"></span></button>
          <span id="lot-marked" class="lot-marked" role="status" aria-label="Beans on your tabla">0 / 16</span></div>
        <div class="lot-now" id="lot-bubble" aria-live="polite"><div id="lot-card" class="lot-card"></div>
          <div class="lot-say"><p id="lot-line" class="lot-line">Pull up a chair, honey! Tap <b>Start</b> and I'll start calling cards.</p><p class="lot-count" id="lot-count"></p></div>
          <div class="lot-now-btns"><button type="button" id="lot-play" class="lot-btn lot-main">▶ Start</button><button type="button" id="lot-claim" class="lot-claim">¡Lotería!</button></div></div>
        <div class="lot-fit"><div id="lot-tabla" class="lot-tabla" role="grid" aria-label="Your tabla: when Tía calls one of your cards, tap it to drop a bean on it"></div></div>
        <div class="lot-actions lot-controls" role="group" aria-label="Game controls">
          <button type="button" id="lot-voice" class="lot-btn lot-icon" aria-pressed="false"></button>
          <button type="button" id="lot-clear" class="lot-btn lot-clear" aria-label="Limpiar: take all the beans off">Limpiar</button>
          <button type="button" id="lot-new" class="lot-btn lot-new" aria-label="Nueva tabla: a new random mix of 16 cards">Nueva tabla</button>
        </div>
        <div class="lot-sheet" id="lot-sheet" role="dialog" aria-labelledby="lot-sheet-t" hidden><div class="lot-sheet-in">
          <div class="lot-sheet-h"><h3 id="lot-sheet-t">Pick your tabla</h3><button type="button" id="lot-sheet-x" class="lot-sheet-x" aria-label="Close"><span aria-hidden="true">✕</span></button></div>
          <div class="lot-picks" id="lot-picks"></div>
          <div class="lot-sheet-row"><span>Calling speed</span><button type="button" id="lot-speed" class="lot-btn" aria-label="Calling speed"></button></div>
        </div></div>
      </div>
      <p class="lot-rules">When Tía calls a card that's on your tabla, tap it to drop a bean on it (tap again to take it off). Win with a row, a column, a diagonal or the 4 corners, then tap <b>¡Lotería!</b> <b>Limpiar</b> takes the beans off; <b>Nueva tabla</b> deals a random new mix, or pick one of the ready-made tablas at the top. A game you don't win (the deck runs out, or you deal a new tabla mid-game) resets your streak.</p>
      <p class="lot-stats" id="lot-stats"></p>
      <div class="lot-hist-wrap"><p class="lot-hist-h">Already called</p><div id="lot-hist" class="lot-hist"></div></div>`;
    const $ = (s) => el.querySelector(s);
    const fs = fullscreen(el, { title: "Lotería Chismosa", badgeClass: "gfs-lot", barItems: [el.querySelector("#lot-pick"), el.querySelector("#lot-marked")],
      badge: '<span class="gfs-lot-emo" aria-hidden="true">🎴</span><span class="gfs-lot-t" aria-hidden="true">Lotería <b>Chismosa</b></span>',
      onExit: () => { pause(); hush(); speak(started && !over ? "Game paused. Tap Resume when you're back, honey." : "Pull up a chair, honey! Tap Start and I'll start calling cards.", null); },
      onLeave: () => { pause(); } });
    // v41: Tía's voice is recorded ahead of time with a natural neural voice (Piper es_MX, tools/make_loteria_audio.py): one short
    // mp3 per card (the verse, then the name) plus the intro, ¡Lotería! and the end of the deck, cached offline by the service
    // worker. They play on ONE reused <audio>: the first clip starts inside the Start tap, which unlocks it on iPhone for the
    // rest of the game. A clip that can't load or play falls back to the phone's own Spanish voice (speechSynthesis).
    const AUDIO = "/static/loteria/audio/", bad = new Set(), voice = { last: null, clips: 0, fallbacks: 0 };
    const hasVoice = "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
    let esVoice = null, au = null, queue = [], cur = null;
    const pickVoice = () => { if (!hasVoice) return; const vs = speechSynthesis.getVoices();
      esVoice = vs.find((v) => /^es[-_]MX/i.test(v.lang)) || vs.find((v) => /^es[-_]US/i.test(v.lang)) || vs.find((v) => /^es/i.test(v.lang)) || null; };
    if (hasVoice) { pickVoice(); speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", pickVoice); }
    const clipOf = (c) => ({ key: String(c.id).padStart(2, "0"), text: callText(c) });
    function audioEl() {
      if (au || typeof Audio !== "function") return au;
      au = new Audio(); au.preload = "auto"; au.setAttribute("playsinline", "");
      au.addEventListener("ended", () => { cur = null; nextClip(); });
      au.addEventListener("error", () => { if (cur && !cur.fell) { bad.add(cur.key); fallback(cur); } });   // the file didn't load
      return au;
    }
    function say(items) { hush(); if (st.muted) return; queue = items.slice(); nextClip(); }
    function nextClip() {
      const it = queue.shift(); cur = it || null;
      if (!it) return;
      const a = audioEl();
      if (!a || bad.has(it.key)) { fallback(it); return; }
      voice.last = it.key; voice.clips++;
      let p;
      try { a.src = AUDIO + it.key + ".mp3"; a.playbackRate = st.speed === "fast" ? 1.1 : 1; p = a.play(); } catch (e) { fallback(it); return; }
      if (p && p.catch) p.catch((e) => { if (cur === it && !it.fell && !(e && e.name === "AbortError")) fallback(it); });   // blocked or unplayable
    }
    function fallback(it) {   // the phone's own Spanish voice for this one line, then on with the queue
      it.fell = true; voice.fallbacks++;
      if (!hasVoice || st.muted) { cur = null; nextClip(); return; }
      try {
        const u = new SpeechSynthesisUtterance(it.text);
        u.lang = esVoice ? esVoice.lang : "es-MX"; if (esVoice) u.voice = esVoice; u.rate = st.speed === "fast" ? 1.1 : 0.95;
        u.onend = u.onerror = () => { if (cur === it) { cur = null; nextClip(); } };
        speechSynthesis.cancel(); speechSynthesis.speak(u);
      } catch (e) { cur = null; }
    }
    const talking = () => !!cur || queue.length > 0 || (!!au && !au.paused && !au.ended);
    const hush = () => { queue = []; cur = null; if (au) try { au.pause(); } catch (e) {} if (hasVoice) try { speechSynthesis.cancel(); } catch (e) {} };
    function stats() { $("#lot-stats").innerHTML = `🏆 Wins <b>${+st.wins || 0}</b> · 🔥 Streak <b>${+st.streak || 0}</b> · ⭐ Best streak <b>${+st.best || 0}</b>`; }
    function controls() {
      $("#lot-play").textContent = over ? "▶ Play again" : running ? "⏸ Pause" : started ? "▶ Resume" : "▶ Start";
      $("#lot-play").setAttribute("aria-pressed", running ? "true" : "false");
      $("#lot-speed").textContent = SPEED_LABEL[st.speed];
      const v = $("#lot-voice");
      v.innerHTML = st.muted ? '🔇<span class="lb-x"> Sound</span>' : '🔊<span class="lb-x"> Sound</span>'; v.setAttribute("aria-pressed", st.muted ? "false" : "true");
      v.setAttribute("aria-label", st.muted ? "Sound is off (Tía's voice and the beans)" : "Sound is on (Tía's voice and the beans)");
      $("#lot-count").textContent = started ? `${called.size} of ${CARDS.length} cards called` : `${CARDS.length} cards in the deck`;
      $("#lot-marked").textContent = `${marks ? marks.size : 0} / 16`;
      const pr = PRESETS.find((x) => x.id === st.pick);
      const pt = $("#lot-pick-t");
      if (pr) pt.textContent = pr.name;
      else pt.innerHTML = '<span class="lot-pick-emo" aria-hidden="true">🔀 </span>Random';
      $("#lot-pick").setAttribute("aria-label", `Pick your tabla (now: ${pr ? pr.name : "a random mix"})`);
    }
    const cellLabel = (i) => byId(tabla[i]).name + (marks.has(i) ? ", bean on it" : called.has(tabla[i]) ? ", called: tap to put a bean on it" : "");
    function drawTabla() {   // each cell's bean lands a little differently (turned, nudged, sometimes flipped), like a real one
      $("#lot-tabla").innerHTML = tabla.map((id, i) => { const c = byId(id), m = marks.has(i), r = Math.round(Math.random() * 50 - 25), dx = Math.round(Math.random() * 6 - 3), dy = Math.round(Math.random() * 6 - 3);
        return `<button type="button" class="lot-cell${m ? " marked" : ""}" data-i="${i}" aria-pressed="${m}" aria-label="${esc(cellLabel(i))}">${cardHTML(c)}`
          + `<span class="frijol" aria-hidden="true" style="--r:${r}deg;--dx:${dx}%;--dy:${dy}%;--fx:${Math.random() < 0.5 ? -1 : 1}">${BEAN}</span></button>`; }).join("");
    }
    function history() { $("#lot-hist").innerHTML = [...called].reverse().slice(0, 12).map((id) => cardHTML(byId(id), "mini")).join(""); }
    function speak(line, card, lang) {   // what's on screen: the called card + its verse (Spanish), or Tía's English asides
      $("#lot-card").innerHTML = card ? cardHTML(card, "big") : "";
      const l = $("#lot-line"); l.textContent = line; if (lang) l.setAttribute("lang", lang); else l.removeAttribute("lang");
    }
    function deal(first) {
      if (!first && started && !over && called.size) { st.streak = 0; st.played++; save(st); }
      const pr = PRESETS.find((x) => x.id === st.pick);
      stop(); tabla = pr ? pr.cards.slice() : newTabla(); deck = newDeck(); called = new Set(); marks = new Set(); over = false; started = false;
      el.classList.remove("won"); drawTabla(); history(); stats(); controls();
      if (!first) speak(pr ? `${pr.name}: new tabla, new luck. Tap Start when you're ready.` : "New tabla, new luck. Tap Start when you're ready.", null);
    }
    function callNext() {
      if (!deck.length) { over = true; stop(); st.streak = 0; st.played++; save(st); stats(); controls(); speak("The deck ran out! Nobody won this time… the next one's yours.", null); say([{ key: "over", text: LINES_ES.over }]); return; }
      const first = !called.size, c = byId(deck.shift()); called.add(c.id);
      speak(c.verse, c, "es"); say(first ? [{ key: "intro", text: LINES_ES.intro }, clipOf(c)] : [clipOf(c)]); history(); controls();
    }
    function tick() { callNext(); if (running) schedule(); }
    // the next card comes after the chosen pace, and never while she's still saying the last one (then a short breath)
    function schedule() {
      clearTimeout(timer); const t0 = Date.now(), ms = SPEEDS[st.speed];
      const wait = () => { if (!running) return; if (talking() && Date.now() - t0 < ms + 9000) { timer = setTimeout(wait, 150); return; }
        timer = setTimeout(() => { if (running) tick(); }, Date.now() - t0 > ms + 100 ? 700 : 0); };
      timer = setTimeout(wait, ms);
    }
    function start() { if (!started || over) { try { root.dispatchEvent(new CustomEvent("chisme-game-play", { detail: "loteria" })); } catch (e) {} }   // v42: a new game (not a resume), for the anonymous counts
      if (over) { deal(true); } fs.enter(); started = true; running = true; controls(); clearTimeout(timer); tick(); }
    function stop() { running = false; clearTimeout(timer); timer = null; if (tabla) controls(); }
    function pause() { if (running) { stop(); hush(); } }
    function confetti() {
      if (reduced()) return;   // reduce motion: the static "¡Lotería!" banner only
      const box = document.createElement("div"); box.className = "lot-confetti"; box.setAttribute("aria-hidden", "true");
      for (let i = 0; i < 70; i++) { const p = document.createElement("i"); p.style.cssText = `left:${Math.random() * 100}%;background:${FIESTA[i % 5]};animation-delay:${(Math.random() * 0.5).toFixed(2)}s;animation-duration:${(1.6 + Math.random() * 1.4).toFixed(2)}s;transform:rotate(${Math.floor(Math.random() * 360)}deg)`; box.appendChild(p); }
      document.body.appendChild(box); setTimeout(() => box.remove(), 3600);
    }
    function claim() {
      if (!started || over) { speak("You have to play first, honey. Tap Start.", null); return; }
      const r = check(tabla, marks, called);
      if (r.win) {
        over = true; stop(); st.wins++; st.streak++; st.played++; st.best = Math.max(st.best, st.streak); save(st);
        for (const i of r.line.cells) el.querySelector(`.lot-cell[data-i="${i}"]`).classList.add("win");
        el.classList.add("won");
        const brag = BRAG[(st.wins - 1) % BRAG.length];
        speak(`${brag} (${r.line.kind === "corners" ? "the 4 corners" : r.line.kind === "row" ? "a row" : r.line.kind === "column" ? "a column" : "a diagonal"})`, null);
        say([{ key: "loteria", text: LINES_ES.loteria }]); stats(); controls(); confetti();
        return;
      }
      speak(r.early.length ? TEASE_EARLY : TEASE_NOPE, null);
    }
    // v41: a bean only goes on a card Tía already called; an uncalled card just gives a little shake. Tap again: the bean comes off.
    $("#lot-tabla").addEventListener("click", (e) => {
      const b = e.target.closest(".lot-cell"); if (!b || over) return;
      const i = +b.dataset.i;
      if (!marks.has(i) && !called.has(tabla[i])) {
        b.classList.remove("nope"); void b.offsetWidth; b.classList.add("nope"); setTimeout(() => b.classList.remove("nope"), 450);
        return;
      }
      if (marks.has(i)) { marks.delete(i); plink(false); } else { marks.add(i); plink(true); }
      const m = marks.has(i); b.classList.toggle("marked", m); b.setAttribute("aria-pressed", m); b.setAttribute("aria-label", cellLabel(i));
      controls();
    });
    function clearBeans() {   // Limpiar: every bean off (same tabla, same game)
      if (!marks.size) return;
      marks = new Set(); plink(false);
      for (const b of el.querySelectorAll(".lot-cell")) { b.classList.remove("marked", "win"); b.setAttribute("aria-pressed", "false"); b.setAttribute("aria-label", cellLabel(+b.dataset.i)); }
      controls();
    }
    // "Pick your tabla": a random mix or a ready-made one (remembered)
    const sheet = $("#lot-sheet");
    $("#lot-picks").innerHTML = [{ id: "random", name: "🔀 Random mix", note: "16 cards, mixed up every time", cards: [] }, ...PRESETS].map((p) =>
      `<button type="button" class="lot-pickopt" data-pick="${p.id}" aria-pressed="false"><span class="lpo-t"><b>${esc(p.name)}</b><small>${p.note || p.cards.slice(0, 4).map((id) => esc(byId(id).name)).join(" · ") + " …"}</small></span>`
      + `<span class="lpo-cards" aria-hidden="true">${p.cards.length ? p.cards.slice(0, 4).map((id) => `<img src="${byId(id).img}" alt="" width="200" height="300" loading="lazy">`).join("") : '<span class="lpo-rand">🔀</span>'}</span></button>`).join("");
    function sheetOpen(on) {
      sheet.hidden = !on; $("#lot-pick").setAttribute("aria-expanded", on ? "true" : "false");
      for (const b of sheet.querySelectorAll(".lot-pickopt")) b.setAttribute("aria-pressed", b.dataset.pick === (st.pick || "random") ? "true" : "false");
      if (on) (sheet.querySelector('.lot-pickopt[aria-pressed="true"]') || sheet.querySelector(".lot-pickopt")).focus({ preventScroll: true });
      else if (sheet.contains(document.activeElement)) $("#lot-pick").focus({ preventScroll: true });
    }
    $("#lot-pick").onclick = () => sheetOpen(sheet.hidden);
    $("#lot-sheet-x").onclick = () => sheetOpen(false);
    sheet.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); sheetOpen(false); } });
    sheet.addEventListener("click", (e) => { if (e.target === sheet) sheetOpen(false); });
    $("#lot-picks").addEventListener("click", (e) => {
      const b = e.target.closest(".lot-pickopt"); if (!b) return;
      st.pick = b.dataset.pick === "random" ? "random" : b.dataset.pick; save(st); sheetOpen(false); deal(false);
    });
    // the bean's little "tock" on the card (made on the phone with Web Audio; off with 🔇 Sound)
    let actx = null;
    function plink(on) {
      if (st.muted) return;
      try {
        const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
        actx = actx || new AC(); if (actx.state === "suspended") actx.resume();
        const t = actx.currentTime + (on && !reduced() ? 0.2 : 0), o = actx.createOscillator(), g = actx.createGain();   // lands at the end of the drop
        o.type = "triangle"; o.frequency.setValueAtTime(on ? 420 : 300, t); o.frequency.exponentialRampToValueAtTime(on ? 150 : 520, t + 0.07);
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(on ? 0.5 : 0.25, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.1);
        o.connect(g).connect(actx.destination); o.start(t); o.stop(t + 0.12);
        const n = actx.createBufferSource(), buf = actx.createBuffer(1, Math.floor(actx.sampleRate * 0.03), actx.sampleRate), d = buf.getChannelData(0);
        for (let k = 0; k < d.length; k++) d[k] = (Math.random() * 2 - 1) * Math.pow(1 - k / d.length, 3);
        const f = actx.createBiquadFilter(), ng = actx.createGain(); f.type = "bandpass"; f.frequency.value = on ? 2200 : 3200; f.Q.value = 1.2; ng.gain.value = on ? 0.35 : 0.18;
        n.buffer = buf; n.connect(f).connect(ng).connect(actx.destination); n.start(t);
        plinks++;
      } catch (e) {}
    }
    let plinks = 0;
    $("#lot-play").onclick = () => (running ? pause() : start());
    $("#lot-speed").onclick = () => { st.speed = st.speed === "normal" ? "fast" : st.speed === "fast" ? "slow" : "normal"; save(st); controls(); if (running) schedule(); };
    $("#lot-new").onclick = () => { st.pick = "random"; save(st); deal(false); };   // Nueva tabla: always a random new mix
    $("#lot-clear").onclick = clearBeans;
    $("#lot-voice").onclick = () => { st.muted = !st.muted; save(st); if (st.muted) hush(); controls(); };
    $("#lot-claim").onclick = claim;
    deal(true);
    return {
      pause,
      fs, exitFullscreen: (quiet) => fs.exit(quiet),
      destroy() { fs.exit(true); stop(); hush(); if (au) au.removeAttribute("src"); if (actx) try { actx.close(); } catch (e) {} if (hasVoice && speechSynthesis.removeEventListener) speechSynthesis.removeEventListener("voiceschanged", pickVoice); },
      reload() { Object.assign(st, load()); stats(); controls(); },
      clearBeans, pick: (id) => { st.pick = id; save(st); deal(false); },
      get state() { return { pick: st.pick || "random", tabla: tabla.slice(), called: [...called], marks: [...marks], running, over, started, stats: { wins: st.wins, streak: st.streak, best: st.best }, muted: st.muted, speed: st.speed, fullscreen: fs.on, plinks,
        voice: { last: voice.last, clips: voice.clips, fallbacks: voice.fallbacks, bad: [...bad], talking: talking(), src: au ? au.currentSrc || au.src : "" } }; },
      callNext, claim,
    };
  }

  const GAMES = [{ id: "loteria", name: "Lotería Chismosa", emoji: "🎴", blurb: "Tía calls the cards; fill a line and shout ¡Lotería!", mount: mountLoteria }];

  // ---- the Juegos tab: list the games, mount the chosen one (GAMES[0] by default: v47 The Juan That Got Away, unshifted by juan.js) ----
  function mountTab(listEl, stageEl, ctx) {
    let active = null, activeId = null;
    const open = (id) => {
      const g = GAMES.find((x) => x.id === id) || GAMES[0];
      if (activeId === g.id) return active;
      if (active && active.exitFullscreen) active.exitFullscreen(true);
      if (active && active.pause) active.pause();
      if (active && active.destroy) active.destroy();   // drop the old game's timers and key listeners
      stageEl.innerHTML = ""; activeId = g.id;
      try { active = g.mount(stageEl, ctx); }
      catch (err) {   // v49.9: a game that can't start shows "Tap to reload" (e.g. a half-updated app), never a blank stage
        console.error(g.id, err); active = null;
        stageEl.innerHTML = `<button type="button" class="game-broken" style="position:static;width:100%;height:auto;min-height:320px"><span><span aria-hidden="true">😬</span> ${esc(g.name)} didn't load right.</span><b>🔄 Tap to reload</b></button>`;
        stageEl.querySelector(".game-broken").onclick = () => location.reload(); }
      for (const b of listEl.querySelectorAll(".game-pick")) b.setAttribute("aria-pressed", b.dataset.game === g.id ? "true" : "false");
      return active;
    };
    listEl.innerHTML = GAMES.map((g) => `<button type="button" class="game-pick" data-game="${g.id}" aria-pressed="false"><span class="gp-emo" aria-hidden="true">${g.emoji}</span><span><b>${esc(g.name)}</b><small>${esc(g.blurb)}</small></span></button>`).join("")
      + `<p class="game-more">More games coming soon.</p>`;
    listEl.addEventListener("click", (e) => { const b = e.target.closest(".game-pick"); if (b) open(b.dataset.game); });
    open(GAMES[0].id);
    return { open, pause() { if (active && active.pause) active.pause(); },
      leave() { if (active && active.exitFullscreen) active.exitFullscreen(true); if (active && active.pause) active.pause(); },   // another tab opened
      get game() { return active; }, get id() { return activeId; } };
  }

  const api = { KEY, CARDS, PRESETS, GAMES, callText, LINES_ES, LINES, FIESTA, shuffle, newTabla, newDeck, check, load, save, reset, mountTab, fullscreen };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ChismeJuegos = api;
})(typeof window !== "undefined" ? window : this);
