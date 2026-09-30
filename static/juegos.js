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
  const CARDS = LC.CARDS, callText = LC.callText, LINES_ES = LC.LINES_ES;
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
    bar.innerHTML = `<span class="gfs-side" aria-hidden="true"></span><div class="gfs-badge ${opts.badgeClass || ""}">${opts.badge || esc(opts.title)}<span class="sr-only">${esc(opts.title)}</span></div>`
      + `<button type="button" class="gfs-x" aria-label="Exit ${esc(opts.title)} and go back to Juegitos"><span aria-hidden="true">✕</span></button>`;
    bar.querySelector(".gfs-x").addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); exit(); });
    const onKey = (e) => { if (on && e.key === "Escape" && !document.querySelector("dialog[open]")) { e.preventDefault(); exit(); } };
    const onResize = () => { if (on && opts.onResize) opts.onResize(); };
    function enter() {
      if (on || !stageEl.isConnected) return;
      on = true;
      stageEl.prepend(bar);
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
  const byId = (id) => CARDS[id - 1];
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const cardHTML = (c, cls = "") => `<span class="lcard ${cls}" style="--lc:${c.tint}"><span class="lc-n">${c.id}</span><span class="lc-art">${c.svg}</span><span class="lc-name${c.name.length >= 12 ? " long" : ""}" lang="es">${esc(c.name)}</span></span>`;

  function mountLoteria(el, ctx) {
    const reduced = () => (ctx && ctx.reducedMotion ? ctx.reducedMotion() : matchMedia("(prefers-reduced-motion: reduce)").matches);
    const st = load();
    let tabla, deck, called, marks, timer = null, running = false, over = false, started = false;
    el.innerHTML = `
      <div class="lot-top">
        <img class="lot-tia" src="/static/mascot/avatar-128.webp?art=3" width="64" height="64" alt="Tía Chismosa">
        <div class="lot-bubble" id="lot-bubble" aria-live="polite"><div id="lot-card" class="lot-card"></div><p id="lot-line" class="lot-line">Pull up a chair, honey! Tap <b>Start</b> and I'll start calling cards.</p></div>
      </div>
      <p class="lot-count" id="lot-count"></p>
      <div class="lot-controls" role="group" aria-label="Game controls">
        <button type="button" id="lot-play" class="lot-btn lot-main">▶ Start</button>
        <button type="button" id="lot-speed" class="lot-btn" aria-label="Calling speed"></button>
        <button type="button" id="lot-new" class="lot-btn">🔀 New board</button>
        <button type="button" id="lot-voice" class="lot-btn" aria-pressed="false"></button>
      </div>
      <div class="lot-fit"><div id="lot-tabla" class="lot-tabla" role="grid" aria-label="Your board: tap a card when it's called to put a marker on it"></div></div>
      <button type="button" id="lot-claim" class="lot-claim">¡Lotería!</button>
      <p class="lot-rules">Win with a row, a column, a diagonal or the 4 corners, then tap <b>¡Lotería!</b> A game you don't win (the deck runs out, or you deal a new board mid-game) resets your streak.</p>
      <p class="lot-stats" id="lot-stats"></p>
      <div class="lot-hist-wrap"><p class="lot-hist-h">Already called</p><div id="lot-hist" class="lot-hist"></div></div>`;
    const $ = (s) => el.querySelector(s);
    const fs = fullscreen(el, { title: "Lotería Chismosa", badgeClass: "gfs-lot",
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
    function stats() { $("#lot-stats").innerHTML = `🏆 Wins <b>${st.wins}</b> · 🔥 Streak <b>${st.streak}</b> · ⭐ Best streak <b>${st.best}</b>`; }
    function controls() {
      $("#lot-play").textContent = over ? "▶ Play again" : running ? "⏸ Pause" : started ? "▶ Resume" : "▶ Start";
      $("#lot-play").setAttribute("aria-pressed", running ? "true" : "false");
      $("#lot-speed").textContent = SPEED_LABEL[st.speed];
      const v = $("#lot-voice");
      v.textContent = st.muted ? "🔇 Voice" : "🔊 Voice"; v.setAttribute("aria-pressed", st.muted ? "false" : "true"); v.setAttribute("aria-label", st.muted ? "Tía's voice is off" : "Tía's voice is on");
      $("#lot-count").textContent = started ? `${called.size} of ${CARDS.length} cards called` : `${CARDS.length} cards in the deck`;
    }
    function drawTabla() {
      $("#lot-tabla").innerHTML = tabla.map((id, i) => { const c = byId(id), m = marks.has(i);
        return `<button type="button" class="lot-cell${m ? " marked" : ""}" data-i="${i}" aria-pressed="${m}" aria-label="${esc(c.name)}${m ? ", marked" : ""}">${cardHTML(c)}<span class="ficha" aria-hidden="true"></span></button>`; }).join("");
    }
    function history() { $("#lot-hist").innerHTML = [...called].reverse().slice(0, 12).map((id) => cardHTML(byId(id), "mini")).join(""); }
    function speak(line, card, lang) {   // what's on screen: the called card + its verse (Spanish), or Tía's English asides
      $("#lot-card").innerHTML = card ? cardHTML(card, "big") : "";
      const l = $("#lot-line"); l.textContent = line; if (lang) l.setAttribute("lang", lang); else l.removeAttribute("lang");
    }
    function deal(first) {
      if (!first && started && !over && called.size) { st.streak = 0; st.played++; save(st); }
      stop(); tabla = newTabla(); deck = newDeck(); called = new Set(); marks = new Set(); over = false; started = false;
      el.classList.remove("won"); drawTabla(); history(); stats(); controls();
      if (!first) speak("New board, new luck. Tap Start when you're ready.", null);
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
    function start() { if (over) { deal(true); } fs.enter(); started = true; running = true; controls(); clearTimeout(timer); tick(); }
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
    $("#lot-tabla").addEventListener("click", (e) => {
      const b = e.target.closest(".lot-cell"); if (!b || over) return;
      const i = +b.dataset.i; marks.has(i) ? marks.delete(i) : marks.add(i);
      const m = marks.has(i); b.classList.toggle("marked", m); b.setAttribute("aria-pressed", m);
      b.setAttribute("aria-label", byId(tabla[i]).name + (m ? ", marked" : ""));
    });
    $("#lot-play").onclick = () => (running ? pause() : start());
    $("#lot-speed").onclick = () => { st.speed = st.speed === "normal" ? "fast" : st.speed === "fast" ? "slow" : "normal"; save(st); controls(); if (running) schedule(); };
    $("#lot-new").onclick = () => deal(false);
    $("#lot-voice").onclick = () => { st.muted = !st.muted; save(st); if (st.muted) hush(); controls(); };
    $("#lot-claim").onclick = claim;
    deal(true);
    return {
      pause,
      fs, exitFullscreen: (quiet) => fs.exit(quiet),
      destroy() { fs.exit(true); stop(); hush(); if (au) au.removeAttribute("src"); if (hasVoice && speechSynthesis.removeEventListener) speechSynthesis.removeEventListener("voiceschanged", pickVoice); },
      reload() { Object.assign(st, load()); stats(); controls(); },
      get state() { return { tabla: tabla.slice(), called: [...called], marks: [...marks], running, over, started, stats: { wins: st.wins, streak: st.streak, best: st.best }, muted: st.muted, speed: st.speed, fullscreen: fs.on,
        voice: { last: voice.last, clips: voice.clips, fallbacks: voice.fallbacks, bad: [...bad], talking: talking(), src: au ? au.currentSrc || au.src : "" } }; },
      callNext, claim,
    };
  }

  const GAMES = [{ id: "loteria", name: "Lotería Chismosa", emoji: "🎴", blurb: "Tía calls the cards; fill a line and shout ¡Lotería!", mount: mountLoteria }];

  // ---- the Juegos tab: list the games, mount the chosen one (only one for now) ----
  function mountTab(listEl, stageEl, ctx) {
    let active = null, activeId = null;
    const open = (id) => {
      const g = GAMES.find((x) => x.id === id) || GAMES[0];
      if (activeId === g.id) return active;
      if (active && active.exitFullscreen) active.exitFullscreen(true);
      if (active && active.pause) active.pause();
      if (active && active.destroy) active.destroy();   // drop the old game's timers and key listeners
      stageEl.innerHTML = ""; activeId = g.id; active = g.mount(stageEl, ctx);
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

  const api = { KEY, CARDS, GAMES, callText, LINES_ES, LINES, FIESTA, shuffle, newTabla, newDeck, check, load, save, reset, mountTab, fullscreen };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ChismeJuegos = api;
})(typeof window !== "undefined" ? window : this);
