/* Chisme · 🎲 Juegos: a list of small games that run entirely on the phone (offline, no outside requests).
   Add a game by pushing { id, name, emoji, blurb, mount(el, ctx) } onto GAMES; the tab lists them and mounts one.
   Game 1: Lotería Chismosa, an original chisme-style lotería (our own 40 cards and art, not the traditional deck).
   v40: the tab is called 🎲 Juegitos (the view id stays "juegos"); games play full screen in portrait (fullscreen() below). */
(function (root) {
  "use strict";
  const KEY = "chisme-juegos";
  const FIESTA = ["#00b8b0", "#ff3d8b", "#ff8a00", "#111111", "#b9c0c7"];   // turquoise, pink, orange, black, silver
  // Two cards have no good emoji, so they get small inline SVGs (Fiesta colors).
  const SVG = {
    tubos: '<svg viewBox="0 0 64 64" aria-hidden="true"><g stroke="#111" stroke-width="3"><rect x="6" y="14" width="16" height="36" rx="8" fill="#ff3d8b"/><rect x="24" y="10" width="16" height="40" rx="8" fill="#00b8b0"/><rect x="42" y="14" width="16" height="36" rx="8" fill="#ff8a00"/></g><g stroke="#fff" stroke-width="2" opacity=".8"><path d="M10 24h8M10 32h8M10 40h8M28 20h8M28 30h8M28 40h8M46 24h8M46 32h8M46 40h8"/></g></svg>',
    concha: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M6 44c0-16 12-28 26-28s26 12 26 28z" fill="#ff3d8b" stroke="#111" stroke-width="3"/><path d="M6 44h52v6c0 3-2 5-5 5H11c-3 0-5-2-5-5z" fill="#e8b27a" stroke="#111" stroke-width="3"/><g stroke="#fff" stroke-width="2.5" fill="none" opacity=".9"><path d="M32 18v24M18 26l8 16M46 26l-8 16M11 36l12 6M53 36l-12 6"/></g></svg>',
  };
  // [name, art (emoji or SVG key), Tía's call line]
  const CARDS = [
    ["The Coffee", "☕", "To get you through the morning chisme."],
    ["The Best Friend", "👩🏽", "She knows everything before the newspaper does."],
    ["The Rollers", "svg:tubos", "Rollers still in, and already at the store."],
    ["The Phone", "☎️", "Ring, ring… did you hear?"],
    ["The Neighbor", "🪟", "Behind the curtain, always watching."],
    ["The Gossip", "🤫", "I'll tell you, but you didn't hear it from me."],
    ["The Flip-Flop", "🩴", "It flies without warning, and it never misses."],
    ["The Sweet Bread", "svg:concha", "A sweet roll with coffee, and let's talk."],
    ["The Soap Opera", "📺", "She fainted… and it was her twin!"],
    ["The Snow Cone", "🍧", "With a little chili on top, for the heat."],
    ["The Mariachi", "🎺", "Showed up singing, and nobody invited him."],
    ["The Party", "🎉", "Everybody's invited, except the ex."],
    ["The Taco", "🌮", "One is never enough."],
    ["The Grandma", "👵🏽", "Did you eat yet? Let me fix you another plate."],
    ["The Tamale", "🫔", "Wrapped up tight, like a family secret."],
    ["The Piñata", "🪅", "Swing, swing, swing, and don't lose your aim."],
    ["The Tortilla", "🫓", "Warm and fresh off the griddle."],
    ["The Buddy", "🧔🏽", "Promised to help you move… and never showed up."],
    ["The Nosy Cat", "🐈‍⬛", "Sees everything from the top of the fence."],
    ["The Pickup Truck", "🛻", "Speakers you can hear three blocks away."],
    ["The Dance", "💃🏽", "The music starts, and nobody stays sitting down."],
    ["The Avocado", "🥑", "Pricier than the rent."],
    ["The Flea Market", "🛍️", "Everything's two for five, honey."],
    ["The Chili Pepper", "🌶️", "It stings, but with love."],
    ["The Sweet Fifteen", "👑", "Six months of rehearsing the waltz."],
    ["The Uncle", "🤠", "With his stories from thirty years ago."],
    ["The Radio", "📻", "Same station as always, at full blast."],
    ["The Ice Cream", "🍦", "From the little truck with the little song."],
    ["The Sunday Soup", "🍲", "The cure for every Sunday morning."],
    ["The Group Chat", "💬", "Two hundred messages and nobody knows anything."],
    ["The Selfie", "🤳🏽", "One more, my eyes were closed."],
    ["The Brother", "🤜🏽", "Always has your back."],
    ["The Suitcase", "🧳", "Packed for the ranch this weekend."],
    ["The Market", "🧺", "Where everybody hears everything first."],
    ["The Candle", "🕯️", "So everything turns out all right."],
    ["The Street Corn", "🌽", "With mayo, cheese and chili."],
    ["The Speaker", "🔊", "Now the whole block knows."],
    ["The Stew", "🥣", "For the big September party."],
    ["The Corner Store", "🏪", "Put it on my tab till Friday, okay?"],
    ["The Gossip Queen", "🗣️", "That's me, honey!"],
  ].map(([name, art, call], i) => ({ id: i + 1, name, art, call, color: FIESTA[i % FIESTA.length] }));
  // v39: everything in English except the word "Lotería" (said with a Spanish voice; see say())
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
  const art = (c) => c.art.startsWith("svg:") ? SVG[c.art.slice(4)] : `<span class="lc-emo" aria-hidden="true">${c.art}</span>`;
  const cardHTML = (c, cls = "") => `<span class="lcard ${cls}" style="--lc:${c.color}"><span class="lc-n">${c.id}</span>${art(c)}<span class="lc-name">${esc(c.name)}</span></span>`;

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
    const hasVoice = "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
    // v39: Tía calls in English; only the word "Lotería" is said with a Spanish voice
    let enVoice = null, esVoice = null;
    const pickVoice = () => { if (!hasVoice) return; const vs = speechSynthesis.getVoices();
      enVoice = vs.find((v) => /^en[-_]US/i.test(v.lang)) || vs.find((v) => /^en/i.test(v.lang)) || null;
      esVoice = vs.find((v) => /^es[-_]MX/i.test(v.lang)) || vs.find((v) => /^es[-_]US/i.test(v.lang)) || vs.find((v) => /^es/i.test(v.lang)) || null; };
    if (hasVoice) { pickVoice(); speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", pickVoice); }
    function say(text) {
      if (!hasVoice || st.muted) return;
      try {
        speechSynthesis.cancel();
        for (const [t, lang] of voicePartsOf(text)) {
          const u = new SpeechSynthesisUtterance(t), v = lang === "es" ? esVoice : enVoice;
          u.lang = v ? v.lang : lang === "es" ? "es-MX" : "en-US"; if (v) u.voice = v; u.rate = st.speed === "fast" ? 1.15 : 1;
          speechSynthesis.speak(u);
        }
      } catch (e) {}
    }
    const hush = () => { if (hasVoice) try { speechSynthesis.cancel(); } catch (e) {} };
    function stats() { $("#lot-stats").innerHTML = `🏆 Wins <b>${st.wins}</b> · 🔥 Streak <b>${st.streak}</b> · ⭐ Best streak <b>${st.best}</b>`; }
    function controls() {
      $("#lot-play").textContent = over ? "▶ Play again" : running ? "⏸ Pause" : started ? "▶ Resume" : "▶ Start";
      $("#lot-play").setAttribute("aria-pressed", running ? "true" : "false");
      $("#lot-speed").textContent = SPEED_LABEL[st.speed];
      const v = $("#lot-voice");
      v.hidden = !hasVoice;
      v.textContent = st.muted ? "🔇 Voice" : "🔊 Voice"; v.setAttribute("aria-pressed", st.muted ? "false" : "true"); v.setAttribute("aria-label", st.muted ? "Tía's voice is off" : "Tía's voice is on");
      $("#lot-count").textContent = started ? `${called.size} of ${CARDS.length} cards called` : `${CARDS.length} cards in the deck`;
    }
    function drawTabla() {
      $("#lot-tabla").innerHTML = tabla.map((id, i) => { const c = byId(id), m = marks.has(i);
        return `<button type="button" class="lot-cell${m ? " marked" : ""}" data-i="${i}" aria-pressed="${m}" aria-label="${esc(c.name)}${m ? ", marked" : ""}">${cardHTML(c)}<span class="ficha" aria-hidden="true"></span></button>`; }).join("");
    }
    function history() { $("#lot-hist").innerHTML = [...called].reverse().slice(0, 12).map((id) => cardHTML(byId(id), "mini")).join(""); }
    function speak(line, card) {
      $("#lot-card").innerHTML = card ? cardHTML(card, "big") : "";
      $("#lot-line").textContent = line;
    }
    function deal(first) {
      if (!first && started && !over && called.size) { st.streak = 0; st.played++; save(st); }
      stop(); tabla = newTabla(); deck = newDeck(); called = new Set(); marks = new Set(); over = false; started = false;
      el.classList.remove("won"); drawTabla(); history(); stats(); controls();
      if (!first) speak("New board, new luck. Tap Start when you're ready.", null);
    }
    function callNext() {
      if (!deck.length) { over = true; stop(); st.streak = 0; st.played++; save(st); stats(); controls(); speak("The deck ran out! Nobody won this time… the next one's yours.", null); say("The deck ran out."); return; }
      const c = byId(deck.shift()); called.add(c.id);
      speak(c.call, c); say(`${c.name}. ${c.call}`); history(); controls();
    }
    function tick() { callNext(); if (running) timer = setTimeout(tick, SPEEDS[st.speed]); }
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
        say(brag); stats(); controls(); confetti();
        return;
      }
      speak(r.early.length ? TEASE_EARLY : TEASE_NOPE, null); say(r.early.length ? TEASE_EARLY : TEASE_NOPE);
    }
    $("#lot-tabla").addEventListener("click", (e) => {
      const b = e.target.closest(".lot-cell"); if (!b || over) return;
      const i = +b.dataset.i; marks.has(i) ? marks.delete(i) : marks.add(i);
      const m = marks.has(i); b.classList.toggle("marked", m); b.setAttribute("aria-pressed", m);
      b.setAttribute("aria-label", byId(tabla[i]).name + (m ? ", marked" : ""));
    });
    $("#lot-play").onclick = () => (running ? pause() : start());
    $("#lot-speed").onclick = () => { st.speed = st.speed === "normal" ? "fast" : st.speed === "fast" ? "slow" : "normal"; save(st); controls(); if (running) { clearTimeout(timer); timer = setTimeout(tick, SPEEDS[st.speed]); } };
    $("#lot-new").onclick = () => deal(false);
    $("#lot-voice").onclick = () => { st.muted = !st.muted; save(st); if (st.muted) hush(); controls(); };
    $("#lot-claim").onclick = claim;
    deal(true);
    return {
      pause,
      fs, exitFullscreen: (quiet) => fs.exit(quiet),
      destroy() { fs.exit(true); stop(); hush(); if (hasVoice && speechSynthesis.removeEventListener) speechSynthesis.removeEventListener("voiceschanged", pickVoice); },
      reload() { Object.assign(st, load()); stats(); controls(); },
      get state() { return { tabla: tabla.slice(), called: [...called], marks: [...marks], running, over, started, stats: { wins: st.wins, streak: st.streak, best: st.best }, muted: st.muted, speed: st.speed, fullscreen: fs.on }; },
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

  // "¡Lotería! I told you…" → [["Lotería", "es"], ["I told you…", "en"]]
  const voicePartsOf = (text) => String(text).split(/(¡?Lotería!?)/).map((t) => t.trim()).filter(Boolean).map((t) => (/^¡?Lotería!?$/.test(t) ? ["Lotería", "es"] : [t, "en"]));
  const api = { KEY, CARDS, GAMES, voicePartsOf, LINES, FIESTA, shuffle, newTabla, newDeck, check, load, save, reset, mountTab, fullscreen };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ChismeJuegos = api;
})(typeof window !== "undefined" ? window : this);
