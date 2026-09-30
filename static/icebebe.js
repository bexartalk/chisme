/* Chisme · Juegos game 2: "Ice Ice Bebé", an original 8-bit side-scrolling runner on a canvas (no images, no requests).
   Our hero, a cheerful Tejano in a sombrero, runs across San Antonio: tap / Space / ↑ to jump (again in the air for a
   double jump) over traffic cones and past generic, faceless uniformed agents and their SUVs. Nobody gets hurt: if
   he's caught it's a random big pixel "¡Ay no!" / "¡Fuera!" / "¡Vámonos, amigo!", then back to the last checkpoint. Agents are slapstick (they trip over
   cones, get dizzy), with no logos, badges or weapons. Five levels, each ending at a San Antonio-style spot:
   Home Dehole (a parody big-box hardware store) → La Taquería → La Tiendita → La Plaza → Casa de Mamá (the family party).
   Power-ups: ☕ cafecito (speed boost) and 🩴 chancla (shield: the next agent just gets confused). Chiptune beeps
   (WebAudio square waves, mutable). Score + best score in localStorage "chisme-juegos-ice". Reduce motion: no
   parallax, no screen shake/flashes, no confetti, and a slightly gentler speed. */
(function (root) {
  "use strict";
  const KEY = "chisme-juegos-ice";
  const W = 192, H = 108, OFFY = 36, GROUND = 124, END = 2400, CHECKS = [0, 800, 1600], HERO_X = 46;   // world y 36–144 is on screen
  const GRAV = 720, JUMP = -250, JUMP2 = -215;
  const LEVELS = [
    { name: "Home Dehole", sign: "HOME DEHOLE", speed: 78, sky: ["#8fd8ff", "#d6f3ff"], agents: 0.42, suv: 0.12, hint: "The big-box parking lot. ¡Vámonos!" },
    { name: "La Taquería", sign: "TAQUERIA", speed: 86, sky: ["#6cc6f0", "#fff0c2"], agents: 0.48, suv: 0.15, hint: "Tacos de trompo are waiting." },
    { name: "La Tiendita", sign: "LA TIENDITA", speed: 92, sky: ["#ffb36b", "#ffe2b8"], agents: 0.52, suv: 0.18, hint: "Pick up tortillas for Mamá." },
    { name: "La Plaza", sign: "LA PLAZA", speed: 98, sky: ["#ff7aa8", "#ffc98a"], agents: 0.55, suv: 0.2, hint: "Past the church and the plaza." },
    { name: "Casa de Mamá", sign: "CASA DE MAMA", speed: 104, sky: ["#1b1f4a", "#5a3a7a"], agents: 0.58, suv: 0.22, hint: "Almost home. The party's starting!" },
  ];
  const C = { k: "#111111", h: "#e8c170", H: "#b8903f", b: "#ff3d8b", s: "#b0754a", S: "#8f5a36", e: "#1b1b1b", m: "#6e2f22", w: "#00b8b0", c: "#007f7a",
    j: "#2d4a8a", J: "#223a6e", o: "#6b3b1f", n: "#2b3346", g: "#5b6270", v: "#1f2a3d", l: "#c9d0d8", t: "#b9a27a", a: "#3d4658", y: "#ffd23f", p: "#ff3d8b", r: "#ff8a00", W: "#ffffff" };
  // sprites: one char per pixel ('.' = clear), palette above. The hero faces right.
  const HERO_TOP = [
    "....hhhh....",
    "...hHhhhh...",
    "...bbbbbbb..",
    ".hhhhhhhhhhh",
    "..H.sssss...",
    "....sssses..",
    "....sssssS..",
    ".....smmS...",
    "....wwwww...",
    "...wcwwcww..",
    "..s.wcwwc.s.",
    "....wwwww...",
    "....jjjjj...",
  ];
  const HERO_LEGS = [
    ["...jj..jj...", "..jj....jj..", "..oo....oo.."],
    ["....jjjj....", "....jJjj....", "....oo.oo..."],
    ["....jj.jj...", "...jj..jj...", "..oo...oo..."],
  ];
  const HERO_JUMP = ["...jj..jj...", "..oo...jj...", "........oo.."];
  const AGENT = [
    "...nnnn...",
    "..nnnnnn..",
    ".nnnnnnnnn",
    "...gggg...",
    "...gggg...",
    "...gggg...",
    "..vvvvvv..",
    ".avvvvvva.",
    ".avllllva.",
    ".avvvvvva.",
    "..vvvvvv..",
    "..tttttt..",
    "..tt..tt..",
    "..tt..tt..",
    ".kk...kk..",
  ];
  const AGENT_LEGS2 = ["..tttttt..", "...tttt...", "...tt.tt..", "..kk..kk.."];
  const CONE = ["...r...", "..rrr..", "..WWW..", ".rrrrr.", ".WWWWW.", "rrrrrrr", "kkkkkkk"];
  const CUP = ["..W.W...", "...W....", "WWWWWW..", "WooooWW.", "WooooW.W", "WWWWWWW.", ".WWWW..."];
  const CHANCLA = ["..pppppp.", ".ppppppppp", "pWpppppppp", ".ppppppppp", "..kkkkkkk."];
  const CONCHA = [".ppppp.", "pWpWpWp", "ppppppp", "yyyyyyy"];
  // 3×5 pixel font for signs and the HUD
  const F = { A: "010101111101101", B: "110101110101110", C: "011100100100011", D: "110101101101110", E: "111100110100111", F: "111100110100100", G: "011100101101011",
    H: "101101111101101", I: "111010010010111", J: "001001001101010", K: "101101110101101", L: "100100100100111", M: "101111111101101", N: "110101101101101",
    O: "010101101101010", P: "110101110100100", Q: "010101101110011", R: "110101110101101", S: "011100010001110", T: "111010010010010", U: "101101101101111",
    V: "101101101101010", W: "101101111111101", X: "101101010101101", Y: "101101010010010", Z: "111001010100111", 0: "111101101101111", 1: "010110010010111",
    2: "110001010100111", 3: "110001010001110", 4: "101101111001001", 5: "111100110001110", 6: "011100111101111", 7: "111001010010010", 8: "111101111101111",
    9: "111101111001110", "!": "010010010000010", "¡": "010000010010010", "?": "110001010000010", ".": "000000000000010", ":": "000010000010000", "'": "010010000000000",
    "-": "000000111000000", ",": "000000000010100", " ": "000000000000000", "/": "001001010100100", "x": "000101010101000" };

  function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
  // A level's layout is the same every time (seeded by level number), so checkpoints restart the same course.
  function buildLevel(n) {
    const L = LEVELS[n - 1], r = rng(1000 + n * 7919), ents = [];
    let x = 240;
    const clearOf = (x) => CHECKS.some((c) => c && x + 90 > c - 40 && x - 40 < c + 60);   // the whole group (cone before, pair/SUV after) stays off the flag
    const power = { 1: [[520, "cup"], [1250, "chancla"]], 2: [[700, "chancla"], [1400, "cup"]], 3: [[450, "cup"], [1100, "chancla"], [1900, "cup"]],
      4: [[600, "chancla"], [1300, "cup"], [2000, "chancla"]], 5: [[500, "cup"], [1000, "chancla"], [1700, "chancla"], [2100, "cup"]] }[n];
    for (const [px, kind] of power) ents.push({ t: kind, x: px, y: GROUND - 34, w: 9, h: 8 });
    while (x < END - 160) {
      const gap = 92 - n * 5 + Math.floor(r() * 70);
      x += gap;
      if (clearOf(x) || x > END - 170) continue;
      const roll = r();
      if (roll < L.suv) {
        ents.push({ t: "suv", x, y: GROUND - 22, w: 40, h: 22 });
        for (let k = 0; k < 3; k++) ents.push({ t: "coin", x: x + 8 + k * 11, y: GROUND - 36, w: 7, h: 4 });
        x += 30;
      } else if (roll < L.suv + L.agents) {
        ents.push({ t: "agent", x, y: GROUND - 15, w: 10, h: 15, vx: -14 - n * 2, st: "walk", tt: 0, home: x });
        if (n >= 3 && r() < 0.3) { ents.push({ t: "agent", x: x + 44, y: GROUND - 15, w: 10, h: 15, vx: -14 - n * 2, st: "walk", tt: 0, home: x + 44 }); x += 44; }
        if (r() < 0.35) ents.push({ t: "cone", x: x - 34, y: GROUND - 7, w: 7, h: 7 });   // an agent may trip on it: slapstick
      } else if (roll < 0.85) {
        ents.push({ t: "cone", x, y: GROUND - 7, w: 7, h: 7 });
        if (r() < 0.5) for (let k = 0; k < 3; k++) ents.push({ t: "coin", x: x - 10 + k * 11, y: GROUND - 30 - (k === 1 ? 6 : 0), w: 7, h: 4 });
      } else {
        const hh = 18 + Math.floor(r() * 10);
        ents.push({ t: "crate", x, y: GROUND - hh, w: 24, h: hh });
        for (let k = 0; k < 2; k++) ents.push({ t: "coin", x: x + 3 + k * 11, y: GROUND - hh - 12, w: 7, h: 4 });
      }
    }
    for (const c of CHECKS.slice(1)) ents.push({ t: "flag", x: c, y: GROUND - 26, w: 6, h: 26 });
    return ents;
  }
  const hit = (a, b, pad = 2) => a.x + pad < b.x + b.w && a.x + a.w - pad > b.x && a.y + pad < b.y + b.h && a.y + a.h - pad > b.y;

  function load() { try { return Object.assign({ best: 0, muted: false, levelMax: 1, wins: 0 }, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) { return { best: 0, muted: false, levelMax: 1, wins: 0 }; } }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  const reset = () => { try { localStorage.removeItem(KEY); } catch (e) {} };

  function mount(el, ctx) {
    const reduced = () => (ctx && ctx.reducedMotion ? ctx.reducedMotion() : matchMedia("(prefers-reduced-motion: reduce)").matches);
    const st = load();
    el.innerHTML = `
      <div class="ice-wrap">
        <canvas id="ice-cv" class="ice-cv no-swipe" width="${W}" height="${H}" role="img" aria-label="Ice Ice Bebé game screen. Tap it, or press Space, to jump."></canvas>
        <div id="ice-ov" class="ice-ov" aria-live="polite"></div>
      </div>
      <p class="ice-note" id="ice-note" aria-live="polite"></p>
      <div class="ice-controls" role="group" aria-label="Game controls">
        <button type="button" id="ice-jump" class="lot-btn lot-main ice-jump no-swipe">⤒ Jump</button>
        <button type="button" id="ice-pause" class="lot-btn">⏸ Pause</button>
        <button type="button" id="ice-restart" class="lot-btn">↺ Restart level</button>
        <button type="button" id="ice-sound" class="lot-btn" aria-pressed="true"></button>
      </div>
      <p class="lot-rules">Tap the game (or Space / ↑) to jump; tap again in the air for a double jump. ☕ Cafecito = speed boost · 🩴 Chancla = shield (the next agent just gets confused). Cones slow you down. Get caught and it's back to the last 🚩 checkpoint. Nobody gets hurt.</p>
      <p class="lot-stats" id="ice-stats"></p>`;
    const cv = el.querySelector("#ice-cv"), g = cv.getContext("2d"), ov = el.querySelector("#ice-ov");
    g.imageSmoothingEnabled = false;
    // ---- sound: tiny square-wave beeps
    let ac = null;
    const audio = () => { if (!ac) { const A = window.AudioContext || window.webkitAudioContext; if (A) try { ac = new A(); } catch (e) {} } if (ac && ac.state === "suspended") ac.resume(); return ac; };
    function beep(f, d = 0.08, f2 = null, type = "square", vol = 0.045, at = 0) {
      if (st.muted) return; const a = audio(); if (!a) return;
      try { const o = a.createOscillator(), v = a.createGain(), t0 = a.currentTime + at;
        o.type = type; o.frequency.setValueAtTime(f, t0); if (f2) o.frequency.exponentialRampToValueAtTime(f2, t0 + d);
        v.gain.setValueAtTime(vol, t0); v.gain.exponentialRampToValueAtTime(0.0008, t0 + d);
        o.connect(v); v.connect(a.destination); o.start(t0); o.stop(t0 + d + 0.02); } catch (e) {}
    }
    const SFX = {
      jump: () => beep(330, 0.11, 660), jump2: () => beep(520, 0.09, 900), coin: () => { beep(988, 0.05); beep(1319, 0.08, null, "square", 0.04, 0.05); },
      power: () => [523, 659, 784, 1047].forEach((f, i) => beep(f, 0.07, null, "square", 0.045, i * 0.06)),
      caught: () => [392, 330, 262, 196].forEach((f, i) => beep(f, 0.12, null, "triangle", 0.06, i * 0.1)),
      cone: () => beep(200, 0.08, 120, "square", 0.04), shield: () => beep(700, 0.15, 300, "sawtooth", 0.03),
      clear: () => [523, 659, 784, 659, 784, 1047].forEach((f, i) => beep(f, 0.1, null, "square", 0.045, i * 0.09)),
      check: () => { beep(784, 0.07); beep(1047, 0.1, null, "square", 0.04, 0.07); },
    };
    // ---- game state
    const CAUGHT = ["¡Ay no!", "¡Fuera!", "¡Vámonos, amigo!"];   // one at random, in big pixel text
    let caughtMsg = CAUGHT[0];
    let level = 1, ents = [], hero, camX = 0, score = 0, ckScore = 0, ck = 0, mode = "title", t = 0, raf = null, last = 0, shake = 0, parts = [], msgT = 0, msg = "";
    function spawn(atCheck) {
      ents = buildLevel(level);
      const x0 = CHECKS[atCheck];
      ents = ents.filter((e) => !(e.t === "coin" && e.x < x0));
      hero = { x: x0 + 8, y: GROUND - 18, w: 10, h: 18, vy: 0, ground: true, jumps: 2, boost: 0, shield: 0, stumble: 0, inv: 0, frame: 0 };
      camX = hero.x - HERO_X; score = ckScore; parts = [];
    }
    function startLevel(n, keepScore) { level = n; ck = 0; if (!keepScore) ckScore = 0; spawn(0); mode = "run"; overlay(null); el.querySelector("#ice-note").textContent = `Level ${n}: run to ${LEVELS[n - 1].name}. ${LEVELS[n - 1].hint}`; loop(); }
    function overlay(html, cls = "") { ov.className = "ice-ov" + (html ? " on " + cls : ""); ov.innerHTML = html || ""; }
    const speed = () => LEVELS[level - 1].speed * (reduced() ? 0.85 : 1) * (hero.boost > 0 ? 1.45 : 1) * (hero.stumble > 0 ? 0.5 : 1);
    function jump() {
      if (mode === "title") { startLevel(Math.min(st.levelMax, 1)); return; }
      if (mode !== "run") return;
      audio();
      if (hero.ground) { hero.vy = JUMP; hero.ground = false; hero.jumps = 1; SFX.jump(); }
      else if (hero.jumps > 0) { hero.vy = JUMP2; hero.jumps = 0; SFX.jump2(); }
    }
    function release() { if (mode === "run" && hero.vy < -110) hero.vy *= 0.55; }   // short tap = short hop
    function caught() {
      mode = "caught"; caughtMsg = CAUGHT[Math.floor(Math.random() * CAUGHT.length)]; SFX.caught(); if (!reduced()) shake = 0.25;
      st.best = Math.max(st.best, score); save(st); stats();
      overlay(`<p class="sr-only">${caughtMsg}</p><p class="ice-caught">Try again, from the ${ck ? "checkpoint 🚩" : "start"}.</p>`, "soft caught");
      setTimeout(() => { if (mode === "caught") { spawn(ck); mode = "run"; overlay(null); } }, 1400);
    }
    function clear() {
      const L = LEVELS[level - 1]; score += 500; ckScore = score; st.best = Math.max(st.best, score);
      SFX.clear();
      if (level === 5) {
        mode = "win"; st.wins++; st.levelMax = 5; save(st); stats();
        if (!reduced()) for (let i = 0; i < 90; i++) parts.push({ x: Math.random() * W, y: -Math.random() * H, vy: 20 + Math.random() * 40, c: ["#00b8b0", "#ff3d8b", "#ff8a00", "#ffd23f", "#c9d0d8"][i % 5] });
        overlay(`<p class="ice-big">¡Bienvenido a casa, mijo!</p>`, "win");
        el.querySelector("#ice-note").innerHTML = `🎉 He made it to Mamá's house, and the whole family's celebrating. ¡Qué fiesta! <span class="ice-score">Final score <b>${score}</b> · Best <b>${st.best}</b></span> <button type="button" class="lot-btn lot-main" data-act="again">▶ Play again</button>`;
        return;
      }
      st.levelMax = Math.max(st.levelMax, level + 1); save(st); stats();
      mode = "clear";
      overlay(`<p class="ice-big">¡Llegaste a ${L.name}!</p><p>+500 · Score <b>${score}</b></p><button type="button" class="lot-btn lot-main" data-act="next">▶ Level ${level + 1}: ${LEVELS[level].name}</button>`, "clear");
      el.querySelector("#ice-note").textContent = `Next up: ${LEVELS[level].name}. ${LEVELS[level].hint}`;
    }
    function update(dt) {
      t += dt;
      if (mode === "win") { for (const p of parts) { p.y += p.vy * dt; if (p.y > H) p.y -= H + 10; } return; }
      if (mode !== "run") return;
      const h = hero, vx = speed();
      h.boost = Math.max(0, h.boost - dt); h.stumble = Math.max(0, h.stumble - dt); h.inv = Math.max(0, h.inv - dt);
      h.x += vx * dt; h.frame += vx * dt / 9;
      const prevBottom = h.y + h.h;
      h.vy += GRAV * dt; h.y += h.vy * dt; h.ground = false;
      if (h.y + h.h >= GROUND) { h.y = GROUND - h.h; h.vy = 0; h.ground = true; h.jumps = 2; }
      for (const e of ents) {
        if (e.gone) continue;
        if (e.t === "agent") {
          e.tt = Math.max(0, e.tt - dt);
          if (e.st === "walk") { e.x += e.vx * dt; if (e.x < e.home - 60 || e.x > e.home + 10) e.vx = -e.vx;
            const cone = ents.find((c) => c.t === "cone" && !c.down && Math.abs(c.x - e.x) < 5);
            if (cone) { e.st = "tripped"; e.tt = 2.2; cone.down = true; } }
          else if (e.tt === 0) e.st = "walk";
        }
        if (e.t === "flag" && !e.done && h.x >= e.x) { e.done = true; ck = CHECKS.indexOf(e.x); ckScore = score; SFX.check(); msg = "¡Checkpoint!"; msgT = 1.2; }
        if ((e.t === "suv" || e.t === "crate") && h.x + h.w - 2 > e.x && h.x + 2 < e.x + e.w) {
          if (h.vy >= 0 && prevBottom <= e.y + 3 && h.y + h.h >= e.y) { h.y = e.y - h.h; h.vy = 0; h.ground = true; h.jumps = 2; }   // landed on the roof
          else if (h.y + h.h > e.y + 3 && h.x + h.w - 2 < e.x + 8) {
            if (h.shield > 0 || h.inv > 0) { if (!h.inv) { h.shield = 0; h.inv = 1; SFX.shield(); } h.vy = JUMP; h.y = e.y - h.h - 1; }
            else if (e.t === "suv") { caught(); return; }
            else { h.x = e.x - h.w + 1; h.stumble = 0.4; }   // bumped a crate: a stumble
          }
        }
        if (!hit(h, e)) continue;
        if (e.t === "coin") { e.gone = true; score += 10; SFX.coin(); }
        else if (e.t === "cup") { e.gone = true; h.boost = 5; score += 50; SFX.power(); msg = "¡Cafecito! Speed boost"; msgT = 1.5; }
        else if (e.t === "chancla") { e.gone = true; h.shield = 1; score += 50; SFX.power(); msg = "¡La chancla! Shield on"; msgT = 1.5; }
        else if (e.t === "cone" && !e.down) { e.down = true; h.stumble = 0.6; SFX.cone(); }
        else if (e.t === "agent" && e.st === "walk" && hit(h, e, 3)) {
          if (h.inv > 0) continue;
          if (h.shield > 0) { h.shield = 0; h.inv = 1.2; e.st = "dizzy"; e.tt = 2.5; SFX.shield(); msg = "¿Qué pasó? ¡Se mareó!"; msgT = 1.3; score += 100; }
          else { caught(); return; }
        }
      }
      // a clean hop over an agent: a few bonus points
      for (const e of ents) if (e.t === "agent" && !e.passed && h.x > e.x + e.w) { e.passed = true; score += 25; }
      score += Math.round(vx * dt * 0.1) ? 0 : 0;
      camX = h.x - HERO_X;
      if (h.x >= END) clear();
      msgT = Math.max(0, msgT - dt); shake = Math.max(0, shake - dt);
    }
    // ---- drawing
    function spr(rows, x, y, flip = false, pal = C) {
      for (let r = 0; r < rows.length; r++) { const row = rows[r];
        for (let c = 0; c < row.length; c++) { const ch = row[c]; if (ch === ".") continue; g.fillStyle = pal[ch] || ch; g.fillRect(Math.round(x + (flip ? row.length - 1 - c : c)), Math.round(y + r), 1, 1); } }
    }
    function text(s, x, y, col = "#fff", sc = 1, shadow = "#111") {
      s = s.toUpperCase(); x = Math.round(x); y = Math.round(y);
      const draw = (ox, oy, colr) => { g.fillStyle = colr; let cx = x + ox;
        for (const ch0 of s) { const acc = "ÁÉÍÓÚÑ".includes(ch0), ch = { Á: "A", É: "E", Í: "I", Ó: "O", Ú: "U", Ñ: "N" }[ch0] || ch0, f = F[ch] || F["?"];
          for (let i = 0; i < 15; i++) if (f[i] === "1") g.fillRect(cx + (i % 3) * sc, y + oy + Math.floor(i / 3) * sc, sc, sc);
          if (acc) g.fillRect(cx + (ch0 === "Ñ" ? 0 : 1) * sc, y + oy - 2 * sc, (ch0 === "Ñ" ? 3 : 1) * sc, sc);
          cx += 4 * sc; } };
      if (shadow) draw(sc, sc, shadow); draw(0, 0, col);
    }
    const tw = (s, sc = 1) => s.length * 4 * sc - sc;
    function sky() {
      const L = LEVELS[level - 1], gr = g.createLinearGradient(0, OFFY, 0, GROUND);
      gr.addColorStop(0, L.sky[0]); gr.addColorStop(1, L.sky[1]); g.fillStyle = gr; g.fillRect(0, 0, W, GROUND);
      const par = reduced() ? 0 : 1;
      if (level === 5) { g.fillStyle = "#fff"; for (let i = 0; i < 30; i++) g.fillRect((i * 53 + 7) % W, OFFY + (i * 29) % 50, 1, 1); g.fillStyle = "#f5f0d0"; g.fillRect(160, 48, 10, 10); g.fillStyle = L.sky[0]; g.fillRect(164, 46, 8, 9); }
      // far skyline: a generic observation tower, a mission-style dome, rooftops
      const off = -((camX * 0.15 * par) % 320);
      g.fillStyle = level === 5 ? "#2a2550" : "#9bb7c9";
      for (let k = -1; k < 3; k++) { const b = off + k * 320;
        g.fillRect(b + 20, 70, 26, 54); g.fillRect(b + 50, 84, 30, 40); g.fillRect(b + 120, 78, 22, 46); g.fillRect(b + 200, 88, 40, 36);
        g.fillRect(b + 95, 38, 4, 86); g.fillRect(b + 89, 32, 16, 8); g.fillRect(b + 93, 28, 8, 4);   // the tower
        g.fillRect(b + 160, 96, 30, 28); g.fillRect(b + 166, 88, 18, 8); g.fillRect(b + 172, 82, 6, 6);   // a mission-style dome
        g.fillRect(b + 260, 92, 34, 32); }
      const off2 = -((camX * 0.4 * par) % 160);
      g.fillStyle = level === 5 ? "#3b2f63" : "#6fa36a";
      for (let k = -1; k < 4; k++) { const b = off2 + k * 160; g.fillRect(b + 10, 108, 30, 16); g.fillRect(b + 18, 100, 14, 8); g.fillRect(b + 90, 104, 40, 20); }
      // papel picado string lights on the last level
      if (level >= 4) { const cols = ["#ff3d8b", "#00b8b0", "#ff8a00", "#ffd23f"]; for (let i = 0; i < 16; i++) { g.fillStyle = cols[i % 4]; g.fillRect(((i * 17 - camX * 0.6 * par) % (W + 20) + W + 20) % (W + 20) - 10, 50 + (i % 2), 6, 5); } }
    }
    function ground() {
      g.fillStyle = "#3a3a42"; g.fillRect(0, GROUND, W, H + OFFY - GROUND);
      g.fillStyle = "#c9d0d8"; g.fillRect(0, GROUND, W, 2);
      g.fillStyle = "#f5d33b"; for (let x = -((camX) % 24); x < W; x += 24) g.fillRect(Math.round(x), GROUND + 9, 12, 2);
    }
    const destW = () => (level === 1 ? 170 : 110);
    const destX = () => END - HERO_X + Math.round((W - destW()) / 2);   // centered on screen when he arrives
    function destination() {
      const L = LEVELS[level - 1], x = Math.round(destX() - camX); if (x > W + 10) return;
      if (level === 1) {   // Home Dehole: a parody big-box store. Beige block, wide orange banner, white pixel letters. No logo.
        const bw1 = 170, top1 = 50;
        g.fillStyle = "#e3d3b0"; g.fillRect(x, top1, bw1, GROUND - top1);
        g.fillStyle = "#c9b68e"; g.fillRect(x, top1, bw1, 4); for (let i = 0; i < bw1; i += 14) g.fillRect(x + i, top1 + 4, 1, GROUND - top1 - 4);
        g.fillStyle = "#ff7a00"; g.fillRect(x + 16, top1 + 8, 138, 17); g.fillStyle = "#c95f00"; g.fillRect(x + 16, top1 + 23, 138, 2);
        text("HOME DEHOLE", x + 16 + Math.round((138 - tw("HOME DEHOLE", 2)) / 2), top1 + 12, "#ffffff", 2, null);
        g.fillStyle = "#8a929c"; g.fillRect(x + 56, GROUND - 34, 58, 34); g.fillStyle = "#bfe6f5"; g.fillRect(x + 59, GROUND - 31, 25, 31); g.fillRect(x + 86, GROUND - 31, 25, 31);
        g.fillStyle = "#ff7a00"; g.fillRect(x + 50, GROUND - 38, 70, 4);   // entrance canopy
        g.fillStyle = "#ff7a00"; for (const cx of [x + 14, x + 26, x + 140, x + 152]) g.fillRect(cx, GROUND - 14, 8, 14);   // stacked carts, just blocks
        g.fillStyle = "#fff"; for (let i = -60; i < 0; i += 20) g.fillRect(x + i, GROUND + 3, 2, 8);   // parking-lot stripes
        return;
      }
      const bw = 110, top = level === 4 ? 62 : 58;
      const wall = ["#ff8a00", "#00b8b0", "#ff3d8b", "#e9dcc3", "#ff3d8b"][level - 1];
      g.fillStyle = wall; g.fillRect(x, top, bw, GROUND - top);
      g.fillStyle = "#111"; g.fillRect(x, top, bw, 2);
      if (level === 4) {   // a plaza church facade: bell tower + arch
        g.fillStyle = "#e9dcc3"; g.fillRect(x + 40, top - 18, 30, 18); g.fillStyle = "#111"; g.fillRect(x + 50, top - 14, 10, 8); g.fillStyle = "#e9dcc3"; g.fillRect(x + 52, top - 24, 6, 6); g.fillStyle = "#111"; g.fillRect(x + 54, top - 28, 2, 4);
        g.fillStyle = "#6b3b1f"; g.fillRect(x + 44, GROUND - 30, 22, 30); g.fillStyle = "#111"; g.fillRect(x + 54, GROUND - 30, 2, 30);
      } else if (level === 5) {   // Mamá's house: pitched roof, porch, papel picado, the family party
        g.fillStyle = "#b03a2e"; for (let i = 0; i < 16; i++) g.fillRect(x - 6 + i * 3, top - i * 1.2, bw + 12 - i * 6, 2);
        g.fillStyle = "#ffd23f"; g.fillRect(x + 14, top + 16, 16, 12); g.fillRect(x + 80, top + 16, 16, 12);
        g.fillStyle = "#6b3b1f"; g.fillRect(x + 48, GROUND - 32, 16, 32);
        const cols = ["#ff3d8b", "#00b8b0", "#ff8a00", "#ffd23f", "#c9d0d8"]; for (let i = 0; i < 18; i++) { g.fillStyle = cols[i % 5]; g.fillRect(x - 30 + i * 9, top - 4 + (i % 2), 6, 6); }
      } else {
        g.fillStyle = "#111"; g.fillRect(x + 10, GROUND - 34, 30, 34); g.fillStyle = "#9fd8ff"; g.fillRect(x + 12, GROUND - 32, 26, 20);
        g.fillStyle = "#9fd8ff"; g.fillRect(x + 56, top + 20, 40, 20);
        if (level === 2) { g.fillStyle = "#fff"; for (let i = 0; i < 6; i++) g.fillRect(x + 50 + i * 8, top + 8, 4, 8); }   // an awning
      }
      const sign = L.sign, sw = tw(sign) + 8;
      g.fillStyle = "#111"; g.fillRect(x + (bw - sw) / 2, top + 4, sw, 11); text(sign, x + (bw - sw) / 2 + 4, top + 7, "#ffd23f", 1, null);
    }
    function family(x) {   // the party at Mamá's: generic pixel family members, arms up
      const kin = [["#ff3d8b", "#8f5a36", 14], ["#00b8b0", "#b0754a", 12], ["#ff8a00", "#6e4428", 10], ["#ffd23f", "#b0754a", 16], ["#c9d0d8", "#8f5a36", 13]];
      kin.forEach(([shirt, skin, hgt], i) => { const fx = x + i * 13, fy = GROUND - hgt, bob = (!reduced() && mode === "win") ? Math.round(Math.sin(t * 8 + i) ) : 0;
        g.fillStyle = skin; g.fillRect(fx + 1, fy - 5 + bob, 5, 5); g.fillStyle = "#111"; g.fillRect(fx + 1, fy - 6 + bob, 5, 2);
        g.fillStyle = shirt; g.fillRect(fx, fy + bob, 7, hgt - 5); g.fillStyle = skin; g.fillRect(fx - 1, fy - 3 + bob, 1, 4); g.fillRect(fx + 7, fy - 3 + bob, 1, 4);
        g.fillStyle = "#223a6e"; g.fillRect(fx + 1, GROUND - 5, 5, 5); });
    }
    function drawEnt(e) {
      const x = Math.round(e.x - camX); if (x < -50 || x > W + 10 || e.gone) return;
      if (e.t === "cone") { if (e.down) { g.fillStyle = "#ff8a00"; g.fillRect(x - 1, GROUND - 3, 9, 3); g.fillStyle = "#fff"; g.fillRect(x + 2, GROUND - 3, 2, 3); } else spr(CONE, x, e.y); }
      else if (e.t === "coin") spr(CONCHA, x, e.y + (reduced() ? 0 : Math.round(Math.sin(t * 5 + e.x) * 1)));
      else if (e.t === "cup") spr(CUP, x, e.y + (reduced() ? 0 : Math.round(Math.sin(t * 4) * 1.5)), false, Object.assign({}, C, { o: "#6b3b1f" }));
      else if (e.t === "chancla") spr(CHANCLA, x, e.y + (reduced() ? 0 : Math.round(Math.sin(t * 4 + 1) * 1.5)));
      else if (e.t === "crate") { g.fillStyle = "#b8793a"; g.fillRect(x, e.y, e.w, e.h); g.fillStyle = "#7a4a1f"; g.fillRect(x, e.y, e.w, 2); g.fillRect(x, e.y + e.h - 2, e.w, 2); g.fillRect(x + 2, e.y, 2, e.h); g.fillRect(x + e.w - 4, e.y, 2, e.h); }
      else if (e.t === "flag") { g.fillStyle = "#c9d0d8"; g.fillRect(x, e.y, 1, e.h); g.fillStyle = e.done ? "#00b8b0" : "#ff3d8b"; g.fillRect(x + 1, e.y, 8, 6); }
      else if (e.t === "suv") {   // a generic dark SUV: no markings
        g.fillStyle = "#1a1d24"; g.fillRect(x, e.y + 6, e.w, 12); g.fillRect(x + 4, e.y, e.w - 10, 7);
        g.fillStyle = "#3a4a5a"; g.fillRect(x + 6, e.y + 1, 10, 5); g.fillRect(x + 18, e.y + 1, 10, 5);
        g.fillStyle = "#c9d0d8"; g.fillRect(x, e.y + 12, e.w, 1); g.fillRect(x + e.w - 2, e.y + 8, 2, 2);
        g.fillStyle = "#111"; g.fillRect(x + 5, e.y + 16, 8, 6); g.fillRect(x + e.w - 13, e.y + 16, 8, 6);
        g.fillStyle = "#8a929c"; g.fillRect(x + 8, e.y + 18, 2, 2); g.fillRect(x + e.w - 10, e.y + 18, 2, 2);
      } else if (e.t === "agent") {
        const flip = e.vx > 0;
        if (e.st === "tripped") {   // flat on the ground, legs in the air: slapstick, gets back up
          g.fillStyle = "#1f2a3d"; g.fillRect(x - 3, GROUND - 5, 12, 5); g.fillStyle = "#5b6270"; g.fillRect(x - 7, GROUND - 5, 4, 4); g.fillStyle = "#b9a27a"; g.fillRect(x + 9, GROUND - 9, 3, 6);
          g.fillStyle = "#2b3346"; g.fillRect(x - 10, GROUND - 3 - (Math.floor(t * 6) % 2), 5, 2);   // the cap rolled off
          text("!?", x - 2, GROUND - 16, "#ffd23f");
        } else {
          const legs = Math.floor(t * 6) % 2 && e.st === "walk" ? AGENT.slice(0, 11).concat(AGENT_LEGS2) : AGENT;
          const wob = e.st === "dizzy" && !reduced() ? Math.round(Math.sin(t * 14)) : 0;
          spr(legs, x + wob, e.y, flip);
          if (e.st === "dizzy") { text("?", x + 2, e.y - 8 + (reduced() ? 0 : Math.round(Math.sin(t * 6))), "#ffd23f"); g.fillStyle = "#ffd23f"; g.fillRect(x - 2 + (reduced() ? 0 : Math.round(Math.sin(t * 9) * 5)) + 5, e.y - 2, 2, 2); }
        }
      }
    }
    function drawHero() {
      const h = hero, x = Math.round(h.x - camX), y = Math.round(h.y);
      if (h.inv > 0 && !reduced() && Math.floor(t * 12) % 2) return;
      const legs = !h.ground ? HERO_JUMP : HERO_LEGS[Math.floor(h.frame) % 3];
      if (h.shield > 0) { g.fillStyle = "rgba(255,61,139,.35)"; g.fillRect(x - 3, y - 2, h.w + 8, h.h + 3); }
      spr(HERO_TOP.concat(mode === "win" ? HERO_LEGS[1] : legs), x - 1, y - 2);
      if (h.boost > 0 && !reduced()) { g.fillStyle = "#fff"; for (let i = 0; i < 3; i++) g.fillRect(x - 4 - i * 4, y + 6 + i * 3, 3, 1); }
    }
    function hud() {
      g.fillStyle = "rgba(0,0,0,.55)"; g.fillRect(0, 0, W, 10);
      text(`LV${level} ${LEVELS[level - 1].sign}`, 3, 3, "#fff", 1, null);
      const sc = `${score}`, bs = `HI ${Math.max(st.best, score)}`;
      text(sc, W - tw(sc) - 3, 3, "#ffd23f", 1, null); text(bs, W - tw(sc) - tw(bs) - 10, 3, "#c9d0d8", 1, null);
      // progress to the destination
      const px = Math.min(1, Math.max(0, hero.x / END)); g.fillStyle = "#555"; g.fillRect(3, 12, 60, 2); g.fillStyle = "#00b8b0"; g.fillRect(3, 12, Math.round(60 * px), 2);
      for (const c of CHECKS.slice(1)) { g.fillStyle = "#ff3d8b"; g.fillRect(3 + Math.round(60 * c / END), 11, 1, 4); }
      if (hero.boost > 0) { spr(CUP, 68, 11, false, Object.assign({}, C, { o: "#6b3b1f" })); g.fillStyle = "#ffd23f"; g.fillRect(78, 14, Math.round(hero.boost * 4), 2); }
      if (hero.shield > 0) spr(CHANCLA, 100, 12);
      if (msgT > 0) { const w = tw(msg); g.fillStyle = "rgba(0,0,0,.6)"; g.fillRect((W - w) / 2 - 4, 28, w + 8, 11); text(msg, (W - w) / 2, 31, "#ffd23f", 1, null); }
    }
    function draw() {
      g.save();
      g.translate(shake > 0 && !reduced() ? Math.round((Math.random() - 0.5) * 4) : 0, -OFFY);
      sky(); destination(); ground();
      if (level === 5 && destX() - camX < W) family(Math.round(destX() + 62 - camX));
      for (const e of ents) drawEnt(e);
      drawHero();
      g.restore();
      if (mode === "win") for (const p of parts) { g.fillStyle = p.c; g.fillRect(Math.round(p.x), Math.round(p.y), 2, 2); }
      hud();
      if (mode === "caught") { const sc = tw(caughtMsg, 3) > W - 12 ? 2 : 3, w = tw(caughtMsg, sc); g.fillStyle = "rgba(0,0,0,.55)"; g.fillRect((W - w) / 2 - 6, 34, w + 12, 5 * sc + 12);
        text(caughtMsg, Math.round((W - w) / 2), 40, "#ffd23f", sc, "#b03a2e"); }
    }
    function title() {
      level = st.levelMax > 1 ? st.levelMax : 1; spawn(0); mode = "title"; draw();
      const cont = st.levelMax > 1 ? `<button type="button" class="lot-btn" data-act="cont">▶ Keep going: level ${st.levelMax}</button>` : "";
      el.querySelector("#ice-note").textContent = "Run home to Mamá's across 5 San Antonio stops: jump the cones, skip past the agents, grab a cafecito.";
      overlay(`<p class="ice-big">Ice Ice Bebé</p><p class="ice-btns"><button type="button" class="lot-btn lot-main" data-act="start">▶ Start at level 1</button>${cont}</p>${st.best ? `<p class="ice-score">Best score <b>${st.best}</b></p>` : ""}`, "title");
    }
    function loop() {
      cancelAnimationFrame(raf); last = performance.now();
      const step = (now) => { const dt = Math.min(0.05, (now - last) / 1000); last = now; update(dt); draw();
        if (mode === "run" || mode === "caught" || (mode === "win" && parts.length)) raf = requestAnimationFrame(step); else raf = null; };
      raf = requestAnimationFrame(step);
    }
    let paused = false;
    function pause() { if (mode === "run" && !paused) { paused = true; mode = "paused"; cancelAnimationFrame(raf); raf = null; overlay(`<p class="ice-big">Paused</p><button type="button" class="lot-btn lot-main" data-act="resume">▶ Resume</button>`, "soft"); ctrl(); } }
    function resume() { if (paused) { paused = false; mode = "run"; overlay(null); loop(); ctrl(); } }
    function stats() { el.querySelector("#ice-stats").innerHTML = `⭐ Best score <b>${st.best}</b> · 🏠 Made it home <b>${st.wins}</b>× · Furthest level <b>${st.levelMax}</b>`; }
    function ctrl() { el.querySelector("#ice-pause").textContent = paused ? "▶ Resume" : "⏸ Pause"; const s = el.querySelector("#ice-sound"); s.textContent = st.muted ? "🔇 Sound" : "🔊 Sound"; s.setAttribute("aria-pressed", st.muted ? "false" : "true"); }
    // ---- input: tap / click the game, the Jump button, Space / ↑ / W
    cv.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); });
    cv.addEventListener("pointerup", release);
    const jb = el.querySelector("#ice-jump");
    jb.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); }); jb.addEventListener("pointerup", release);
    jb.addEventListener("click", (e) => { if (e.detail === 0) jump(); });   // keyboard activation
    el.addEventListener("click", (e) => { const b = e.target.closest("[data-act]"); if (!b) return; const a = b.dataset.act; audio();
      if (a === "start") startLevel(1); else if (a === "cont") { ckScore = 0; startLevel(st.levelMax); } else if (a === "next") startLevel(level + 1, true); else if (a === "again") startLevel(1); else if (a === "resume") resume(); });
    el.querySelector("#ice-pause").onclick = () => (paused ? resume() : pause());
    el.querySelector("#ice-restart").onclick = () => { paused = false; ckScore = 0; startLevel(level); ctrl(); };
    el.querySelector("#ice-sound").onclick = () => { st.muted = !st.muted; save(st); ctrl(); if (!st.muted) SFX.coin(); };
    const onKey = (e) => {
      if (!el.isConnected || !el.closest(".view.active") || document.querySelector("dialog[open]") || e.target.closest && e.target.closest("input, textarea, select, dialog")) return;   // only while Juegos is showing
      if (e.code === "Space" || e.key === "ArrowUp" || e.key === "w" || e.key === "W") { if (e.target.closest && e.target.closest("button") && e.code === "Space" && e.target !== jb) return; e.preventDefault(); if (!e.repeat) jump(); }
      else if (e.key === "p" || e.key === "P") paused ? resume() : pause();
    };
    const onKeyUp = (e) => { if (e.code === "Space" || e.key === "ArrowUp") release(); };
    document.addEventListener("keydown", onKey); document.addEventListener("keyup", onKeyUp);
    stats(); ctrl(); title();
    return {
      pause, resume, jump,
      destroy() { cancelAnimationFrame(raf); document.removeEventListener("keydown", onKey); document.removeEventListener("keyup", onKeyUp); },
      get state() { return { caughtMsg, mode, level, x: hero.x, y: hero.y, ground: hero.ground, score, ck, best: st.best, muted: st.muted, boost: hero.boost, shield: hero.shield, levelMax: st.levelMax, parallax: !reduced(), overlay: ov.textContent.trim() }; },
      // test hooks: jump to a spot in a level (as if you'd run there)
      warp(n, x) { if (n !== level || mode === "title" || mode === "win" || mode === "clear") startLevel(n, true); hero.x = x; camX = x - HERO_X; for (const e of ents) if (e.t === "flag" && e.x <= x) { e.done = true; ck = CHECKS.indexOf(e.x); } ents = ents.filter((e) => !["agent", "cone", "suv", "crate"].includes(e.t) || e.x > x + 30 || e.x < x - 40); },
      ents: () => ents.map((e) => ({ t: e.t, x: e.x, st: e.st })),
    };
  }

  const game = { id: "icebebe", name: "Ice Ice Bebé", emoji: "🤠", blurb: "8-bit runner: get home to Mamá's in 5 levels.", mount };
  const api = { KEY, LEVELS, END, CHECKS, buildLevel, load, save, reset, game };
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.ChismeIceBebe = api; if (root.ChismeJuegos) root.ChismeJuegos.GAMES.push(game); }
})(typeof window !== "undefined" ? window : this);
