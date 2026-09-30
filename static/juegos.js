/* Chisme · 🎲 Juegos: a list of small games that run entirely on the phone (offline, no outside requests).
   Add a game by pushing { id, name, emoji, blurb, mount(el, ctx) } onto GAMES; the tab lists them and mounts one.
   Game 1: Lotería Chismosa, an original chisme-style lotería (our own 40 cards and art, not the traditional deck). */
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
    ["El Cafecito", "☕", "Pa' que aguantes el chisme de la mañana."],
    ["La Comadre", "👩🏽", "La que sabe todo antes que el periódico."],
    ["Los Tubos", "svg:tubos", "Con los tubos puestos y ya en la tienda."],
    ["El Teléfono", "☎️", "Ring, ring… ¿ya supiste?"],
    ["La Vecina", "🪟", "Detrás de la cortina, siempre pendiente."],
    ["El Chisme", "🤫", "Te lo cuento, pero no digas que yo te dije."],
    ["La Chancla", "🩴", "Vuela sin avisar, y nunca falla."],
    ["El Pan Dulce", "svg:concha", "Una concha con cafecito, y a platicar."],
    ["La Novela", "📺", "Se desmayó… ¡y era su gemela!"],
    ["La Raspa", "🍧", "Con chamoy y chilito, pa'l calor."],
    ["El Mariachi", "🎺", "Llegó cantando y sin invitación."],
    ["La Fiesta", "🎉", "Todos invitados, menos el ex."],
    ["El Taco", "🌮", "Uno nunca es suficiente."],
    ["La Abuela", "👵🏽", "¿Ya comiste, mijo? Te sirvo otro plato."],
    ["El Tamal", "🫔", "Envuelto como secreto de familia."],
    ["La Piñata", "🪅", "Dale, dale, dale, no pierdas el tino."],
    ["La Tortilla", "🫓", "Calientita y recién salida del comal."],
    ["El Compadre", "🧔🏽", "Prometió ayudar con la mudanza… y no llegó."],
    ["El Gato Chismoso", "🐈‍⬛", "Lo ve todo desde la barda."],
    ["La Troca", "🛻", "Con bocinas que se oyen en otro barrio."],
    ["La Cumbia", "💃🏽", "Suena la cumbia y nadie se queda sentado."],
    ["El Aguacate", "🥑", "Más caro que la renta."],
    ["La Pulga", "🛍️", "Todo a dos por cinco, mija."],
    ["El Chile", "🌶️", "Pica, pero con cariño."],
    ["La Quinceañera", "👑", "Seis meses ensayando el vals."],
    ["El Tío", "🤠", "Con sus historias de hace treinta años."],
    ["El Radio", "📻", "La estación de siempre, a todo volumen."],
    ["La Nieve", "🍦", "De la troquita que toca la musiquita."],
    ["El Menudo", "🍲", "El remedio de los domingos."],
    ["El Grupo", "💬", "Doscientos mensajes y nadie sabe nada."],
    ["La Selfie", "🤳🏽", "Otra, que salí con los ojos cerrados."],
    ["El Carnal", "🤜🏽", "Siempre hace el paro."],
    ["La Maleta", "🧳", "Lista pa' irse al rancho el fin de semana."],
    ["El Mercado", "🧺", "Donde se sabe todo primero."],
    ["La Veladora", "🕯️", "Pa' que todo salga bien."],
    ["El Elote", "🌽", "Con mayonesa, queso y chile."],
    ["La Bocina", "🔊", "Ahora sí se enteró toda la cuadra."],
    ["El Pozole", "🥣", "Pa' la fiesta del quince de septiembre."],
    ["La Tiendita", "🏪", "Fiado hasta el viernes, ¿sí?"],
    ["La Chismosa", "🗣️", "¡Esa soy yo, mija!"],
  ].map(([name, art, call], i) => ({ id: i + 1, name, art, call, color: FIESTA[i % FIESTA.length] }));
  const BRAG = ["¡Lotería! Te dije que hoy era tu día, mija.", "¡Eso! Ni la vecina lo vio venir.", "¡Lotería! Ya mero te hago mi comadre oficial.",
    "¡Ganaste! Esto lo cuento en el grupo ahorita mismo.", "¡Qué suerte! Pásame tu secreto, ¿eh?"];
  const TEASE_EARLY = "Ay, mija, esa carta todavía no ha salido. Aquí no se hace trampa.";
  const TEASE_NOPE = "Todavía no, corazón. Te falta poquito, sigue jugando.";
  const SPEEDS = { slow: 7000, normal: 4500, fast: 2800 };
  const SPEED_LABEL = { slow: "🐢 Lenta", normal: "🚶 Normal", fast: "🐇 Rápida" };

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
        <img class="lot-tia" src="/static/mascot/avatar-128.webp?art=2" width="64" height="64" alt="Tía Chismosa">
        <div class="lot-bubble" id="lot-bubble" aria-live="polite"><div id="lot-card" class="lot-card"></div><p id="lot-line" class="lot-line">¡Siéntate, mija! Tap <b>Empezar</b> and I'll start calling cards.</p></div>
      </div>
      <p class="lot-count" id="lot-count"></p>
      <div class="lot-controls" role="group" aria-label="Game controls">
        <button type="button" id="lot-play" class="lot-btn lot-main">▶ Empezar</button>
        <button type="button" id="lot-speed" class="lot-btn" aria-label="Calling speed"></button>
        <button type="button" id="lot-new" class="lot-btn">🔀 Nueva tabla</button>
        <button type="button" id="lot-voice" class="lot-btn" aria-pressed="false"></button>
      </div>
      <div id="lot-tabla" class="lot-tabla" role="grid" aria-label="Your tabla: tap a card when it's called to put a ficha on it"></div>
      <button type="button" id="lot-claim" class="lot-claim">¡Lotería!</button>
      <p class="lot-rules">Win with a row, a column, a diagonal or the 4 corners, then tap <b>¡Lotería!</b> A game you don't win (the deck runs out, or you deal a new tabla mid-game) resets your streak.</p>
      <p class="lot-stats" id="lot-stats"></p>
      <div class="lot-hist-wrap"><p class="lot-hist-h">Already called</p><div id="lot-hist" class="lot-hist"></div></div>`;
    const $ = (s) => el.querySelector(s);
    const hasVoice = "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
    let esVoice = null;
    const pickVoice = () => { if (!hasVoice) return; const vs = speechSynthesis.getVoices(); esVoice = vs.find((v) => /^es[-_]MX/i.test(v.lang)) || vs.find((v) => /^es[-_]US/i.test(v.lang)) || vs.find((v) => /^es/i.test(v.lang)) || null; };
    if (hasVoice) { pickVoice(); speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", pickVoice); }
    function say(text) {
      if (!hasVoice || st.muted) return;
      try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.lang = esVoice ? esVoice.lang : "es-MX"; if (esVoice) u.voice = esVoice; u.rate = st.speed === "fast" ? 1.15 : 1; speechSynthesis.speak(u); } catch (e) {}
    }
    const hush = () => { if (hasVoice) try { speechSynthesis.cancel(); } catch (e) {} };
    function stats() { $("#lot-stats").innerHTML = `🏆 Wins <b>${st.wins}</b> · 🔥 Streak <b>${st.streak}</b> · ⭐ Best streak <b>${st.best}</b>`; }
    function controls() {
      $("#lot-play").textContent = over ? "▶ Otra vez" : running ? "⏸ Pausa" : started ? "▶ Seguir" : "▶ Empezar";
      $("#lot-play").setAttribute("aria-pressed", running ? "true" : "false");
      $("#lot-speed").textContent = SPEED_LABEL[st.speed];
      const v = $("#lot-voice");
      v.hidden = !hasVoice;
      v.textContent = st.muted ? "🔇 Voz" : "🔊 Voz"; v.setAttribute("aria-pressed", st.muted ? "false" : "true"); v.setAttribute("aria-label", st.muted ? "Tía's voice is off" : "Tía's voice is on");
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
      if (!first) speak("Tabla nueva, suerte nueva. Tap Empezar when you're ready.", null);
    }
    function callNext() {
      if (!deck.length) { over = true; stop(); st.streak = 0; st.played++; save(st); stats(); controls(); speak("¡Se acabó la baraja! Nadie ganó esta vez… la próxima es tuya.", null); say("Se acabó la baraja."); return; }
      const c = byId(deck.shift()); called.add(c.id);
      speak(c.call, c); say(`${c.name}. ${c.call}`); history(); controls();
    }
    function tick() { callNext(); if (running) timer = setTimeout(tick, SPEEDS[st.speed]); }
    function start() { if (over) { deal(true); } started = true; running = true; controls(); clearTimeout(timer); tick(); }
    function stop() { running = false; clearTimeout(timer); timer = null; if (tabla) controls(); }
    function pause() { if (running) { stop(); hush(); } }
    function confetti() {
      if (reduced()) return;   // reduce motion: the static "¡Lotería!" banner only
      const box = document.createElement("div"); box.className = "lot-confetti"; box.setAttribute("aria-hidden", "true");
      for (let i = 0; i < 70; i++) { const p = document.createElement("i"); p.style.cssText = `left:${Math.random() * 100}%;background:${FIESTA[i % 5]};animation-delay:${(Math.random() * 0.5).toFixed(2)}s;animation-duration:${(1.6 + Math.random() * 1.4).toFixed(2)}s;transform:rotate(${Math.floor(Math.random() * 360)}deg)`; box.appendChild(p); }
      document.body.appendChild(box); setTimeout(() => box.remove(), 3600);
    }
    function claim() {
      if (!started || over) { speak("Primero hay que jugar, mija. Tap Empezar.", null); return; }
      const r = check(tabla, marks, called);
      if (r.win) {
        over = true; stop(); st.wins++; st.streak++; st.played++; st.best = Math.max(st.best, st.streak); save(st);
        for (const i of r.line.cells) el.querySelector(`.lot-cell[data-i="${i}"]`).classList.add("win");
        el.classList.add("won");
        const brag = BRAG[(st.wins - 1) % BRAG.length];
        speak(`${brag} (${r.line.kind === "corners" ? "las 4 esquinas" : r.line.kind === "row" ? "una fila" : r.line.kind === "column" ? "una columna" : "una diagonal"})`, null);
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
      destroy() { stop(); hush(); if (hasVoice && speechSynthesis.removeEventListener) speechSynthesis.removeEventListener("voiceschanged", pickVoice); },
      reload() { Object.assign(st, load()); stats(); controls(); },
      get state() { return { tabla: tabla.slice(), called: [...called], marks: [...marks], running, over, started, stats: { wins: st.wins, streak: st.streak, best: st.best }, muted: st.muted, speed: st.speed }; },
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
    return { open, pause() { if (active && active.pause) active.pause(); }, get game() { return active; }, get id() { return activeId; } };
  }

  const api = { KEY, CARDS, GAMES, LINES, FIESTA, shuffle, newTabla, newDeck, check, load, save, reset, mountTab };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ChismeJuegos = api;
})(typeof window !== "undefined" ? window : this);
