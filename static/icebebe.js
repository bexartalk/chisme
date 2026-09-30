/* Chisme · Juegitos game 2: "Ice Ice Bebé", an original 8-bit side-scrolling runner on a canvas (no images, no requests).
   Our hero, a cheerful Tejano in a sombrero, runs across San Antonio: tap / Space / ↑ to jump (again in the air for a
   double jump) over traffic cones and past generic, faceless uniformed agents and their SUVs. Nobody gets hurt: if
   he's caught it's a random big pixel "¡Ay no!" / "¡Fuera!" / "¡Vámonos, amigo!", then back to the last checkpoint. Agents are slapstick (they trip over
   cones, get dizzy), with no logos, badges or weapons. Five levels, each ending at a San Antonio-style spot:
   Home Dehole (a parody big-box hardware store) → The Taco Shop → The Corner Store → The Plaza → Mom's House (the family party).
   Power-ups: ☕ coffee (speed boost) and 🩴 flip-flop (shield: the next agent just gets confused). Chiptune beeps
   (WebAudio square waves, mutable). Score + best score in localStorage "chisme-juegos-ice". Reduce motion: no
   parallax, no screen shake/flashes, no particles or confetti, and a slightly gentler speed.
   v40: a tall PORTRAIT screen (156 px wide, 220–340 tall) that goes full screen while playing (ChismeJuegos.fullscreen:
   fixed overlay, ✕ exit, pixel "ICE ICE BEBÉ" badge), richer backgrounds per level (sky, sun/moon/stars, drifting
   clouds, far skyline, mid-rise row with a billboard, storefronts with awnings and signs, sidewalk props, street with a
   passing car), more animation frames (4-step run with arm swing and bounce, jump/fall poses, a cheer, 4-step agent
   walk, spinning conchas, waving flags), dust and sparkle particles, and a two-row HUD (level, score, progress,
   power-up slots, best). Colors: Fiesta pink / turquoise / orange, whites and grays only. */
(function (root) {
  "use strict";
  const KEY = "chisme-juegos-ice";
  const W = 156, H0 = 276, STREET = 70, GROUND = 124, END = 2400, CHECKS = [0, 800, 1600], HERO_X = 36;   // the ground line sits STREET px above the bottom
  const GRAV = 720, JUMP = -250, JUMP2 = -215;
  const LEVELS = [
    { name: "Home Dehole", sign: "HOME DEHOLE", speed: 78, sky: ["#4fb0e8", "#d6f3ff"], far: "#a3c3d8", mid: "#7fa3bd", win: "#c4dbe8",
      near: ["#dfe4ea", "#c9ced6", "#e0d2c0", "#b7c4cf"], shops: ["PAINT", "LUMBER", "GARDEN", "TOOLS"], board: "BIG SALE", agents: 0.42, suv: 0.12, hint: "The big-box parking lot. Let's go!" },
    { name: "The Taco Shop", sign: "TACO SHOP", speed: 86, sky: ["#3fa9e0", "#ffd6e6"], far: "#9cc0d9", mid: "#6f97b8", win: "#bcd6e8",
      near: ["#ff8a00", "#00b8b0", "#ff3d8b", "#dfe4ea"], shops: ["TACOS", "BAKERY", "BOOTS", "LAUNDRY"], board: "HOT TAMALES", agents: 0.48, suv: 0.15, hint: "Hot tacos are waiting." },
    { name: "The Corner Store", sign: "CORNER STORE", speed: 92, sky: ["#ff9a6b", "#ffc9dc"], far: "#e69aa8", mid: "#c77a8e", win: "#f2bccb",
      near: ["#6fb7c9", "#ff3d8b", "#dfe4ea", "#ff8a00"], shops: ["MARKET", "TIRES", "BARBER", "ICE"], board: "COLD DRINKS", agents: 0.52, suv: 0.18, hint: "Pick up tortillas for Mom." },
    { name: "The Plaza", sign: "THE PLAZA", speed: 98, sky: ["#c2548a", "#ffa07a"], far: "#8e4a7a", mid: "#6f3d6b", win: "#c27aa6",
      near: ["#dfe4ea", "#00b8b0", "#ff8a00", "#ff3d8b"], shops: ["CAFE", "FLOWERS", "MUSIC", "SWEETS"], board: "LIVE MUSIC", agents: 0.55, suv: 0.2, hint: "Past the church and the plaza." },
    { name: "Mom's House", sign: "MOM'S HOUSE", speed: 104, sky: ["#141a3f", "#4a2f6e"], far: "#221f4a", mid: "#2e2858", win: "#7ff0f2",
      near: ["#3d6b8a", "#8a3d6b", "#3d8a7a", "#6b4a8a"], shops: [], board: "", agents: 0.58, suv: 0.22, hint: "Almost home. The party's starting!" },
  ];
  const C = { k: "#111111", h: "#d9a877", H: "#a8743f", b: "#ff3d8b", s: "#b0754a", S: "#8f5a36", e: "#1b1b1b", m: "#6e2f22", w: "#00b8b0", c: "#007f7a",
    j: "#2d4a8a", J: "#223a6e", o: "#6b3b1f", n: "#2b3346", g: "#5b6270", v: "#1f2a3d", l: "#c9d0d8", t: "#9c8f80", a: "#3d4658", y: "#d98a4a", p: "#ff3d8b", r: "#ff8a00", W: "#ffffff" };
  const DIM = Object.fromEntries(Object.keys(C).map((k) => [k, "#4a5068"]));
  // sprites: one char per pixel ('.' = clear), palette above. The hero faces right: head (8 rows) + torso (4) + belt + legs (3) = 16 rows.
  const HERO_HEAD = ["....hhhh....", "...hHhhhh...", "...bbbbbbb..", ".hhhhhhhhhhh", "..H.sssss...", "....sssses..", "....sssssS..", ".....smmS..."];
  const TORSO = {
    n: ["....wwwww...", "...wcwwcww..", "..s.wcwwc.s.", "....wwwww..."],   // arms down
    f: ["....wwwww...", "...wcwwcwws.", "....wcwwc.s.", "..s.wwwww..."],   // front arm forward
    b: ["....wwwww...", "..swcwwcww..", "..s.wcwwc...", "....wwwww.s."],   // front arm back
    u: ["..s.wwwww.s.", "..swcwwcws..", "....wcwwc...", "....wwwww..."],   // arms up (jump, cheer)
  };
  const BELT = "....jjljj...";
  const RUN = [   // 4-step run: legs + which arm pose + a 1 px bounce on the passing steps
    [["...jj..jj...", "..jj....jj..", "..oo....oo.."], "f", 0],
    [["....jjjj....", "....jJjj....", "....oo.oo..."], "n", -1],
    [["....jj.jj...", "...jj..jj...", "..oo...oo..."], "b", 0],
    [["....jjjj....", "....jjJj....", "...oo.oo...."], "n", -1],
  ];
  const LEGS_UP = ["...jj..jj...", "..oo...jj...", "........oo.."], LEGS_DOWN = ["...jjjjj....", "..jj...jj...", ".oo.....oo.."], LEGS_STAND = ["....jj.jj...", "....jj.jj...", "...oo..oo..."];
  const AG_HEAD = ["...nnnn...", "..nnnnnn..", ".nnnnnnnnn", "...gggg...", "...gggg...", "...gggg..."];   // cap + a faceless head
  const AG_TORSO = [["..vvvvvv..", ".avvvvvva.", ".avllllva.", ".avvvvvva.", "..vvvvvv.."], ["..vvvvvv..", "..vvvvvva.", ".avllllva.", ".avvvvvva.", ".a.vvvvv.."]];
  const AG_LEGS = [
    ["..tttttt..", "..tt..tt..", "..tt..tt..", ".kk...kk.."],
    ["..tttttt..", "...tttt...", "...tt.tt..", "..kk..kk.."],
    ["..tttttt..", ".tt....tt.", ".tt....tt.", "kk.....kk."],
    ["..tttttt..", "...tttt...", "..tt.tt...", "..kk.kk..."],
  ];
  const CONE = ["...r...", "..rrr..", "..WWW..", ".rrrrr.", ".WWWWW.", "rrrrrrr", "kkkkkkk"];
  const CUP = ["..W.W...", "...W....", "WWWWWW..", "WooooWW.", "WooooW.W", "WWWWWWW.", ".WWWW..."];
  const CHANCLA = ["..pppppp.", ".ppppppppp", "pWpppppppp", ".ppppppppp", "..kkkkkkk."];
  const CONCHA = [[".ppppp.", "pWpWpWp", "ppppppp", "yyyyyyy"], ["..ppp..", ".pWpWp.", ".ppppp.", ".yyyyy."], ["...p...", "..pWp..", "..ppp..", "..yyy.."]];   // a 3-step spin
  // 3×5 pixel font for signs and the HUD
  const F = { A: "010101111101101", B: "110101110101110", C: "011100100100011", D: "110101101101110", E: "111100110100111", F: "111100110100100", G: "011100101101011",
    H: "101101111101101", I: "111010010010111", J: "001001001101010", K: "101101110101101", L: "100100100100111", M: "101111111101101", N: "110101101101101",
    O: "010101101101010", P: "110101110100100", Q: "010101101110011", R: "110101110101101", S: "011100010001110", T: "111010010010010", U: "101101101101111",
    V: "101101101101010", W: "101101111111101", X: "101101010101101", Y: "101101010010010", Z: "111001010100111", 0: "111101101101111", 1: "010110010010111",
    2: "110001010100111", 3: "110001010001110", 4: "101101111001001", 5: "111100110001110", 6: "011100111101111", 7: "111001010010010", 8: "111101111101111",
    9: "111101111001110", "!": "010010010000010", "¡": "010000010010010", "?": "110001010000010", ".": "000000000000010", ":": "000010000010000", "'": "010010000000000",
    "-": "000000111000000", ",": "000000000010100", " ": "000000000000000", "/": "001001010100100", "x": "000101010101000" };
  const FIESTA = ["#ff3d8b", "#00b8b0", "#ff8a00", "#ffffff"];
  const mod = (a, n) => ((a % n) + n) % n;

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
    let H = H0;
    el.innerHTML = `
      <div class="ice-wrap">
        <canvas id="ice-cv" class="ice-cv no-swipe" width="${W}" height="${H}" role="img" aria-label="Ice Ice Bebé game screen. Tap it, or press Space, to jump."></canvas>
        <div id="ice-ov" class="ice-ov" aria-live="polite"></div>
      </div>
      <p class="ice-note" id="ice-note" aria-live="polite"></p>
      <div class="ice-controls" role="group" aria-label="Game controls">
        <button type="button" id="ice-jump" class="lot-btn lot-main ice-jump no-swipe">⤒ Jump</button>
        <button type="button" id="ice-pause" class="lot-btn"></button>
        <button type="button" id="ice-restart" class="lot-btn" aria-label="Restart level"><span aria-hidden="true">↺</span><span class="ice-lbl"> Restart level</span></button>
        <button type="button" id="ice-sound" class="lot-btn" aria-pressed="true"></button>
      </div>
      <p class="lot-rules">Tap the game (or Space / ↑) to jump; tap again in the air for a double jump. ☕ Coffee = speed boost · 🩴 Flip-flop = shield (the next agent just gets confused). Cones slow you down. Get caught and it's back to the last 🚩 checkpoint. Nobody gets hurt.</p>
      <p class="lot-stats" id="ice-stats"></p>`;
    const cv = el.querySelector("#ice-cv"), g = cv.getContext("2d"), ov = el.querySelector("#ice-ov"), wrap = el.querySelector(".ice-wrap");
    g.imageSmoothingEnabled = false;
    // ---- full screen while playing (portrait): the canvas grows to the screen's shape
    const FS = root.ChismeJuegos && root.ChismeJuegos.fullscreen;
    const fs = FS ? FS(el, { title: "Ice Ice Bebé", badgeClass: "gfs-ice", badge: `<canvas class="gfs-ice-cv" width="60" height="15" aria-hidden="true"></canvas>`,
      onEnter: () => { badge(); fit(); }, onResize: () => fit(), onExit: () => { pause(); fit(); }, onLeave: () => { pause(); fit(); } }) : { enter() {}, exit() {}, on: false };
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
    const CAUGHT = ["¡Ay no!", "¡Fuera!", "¡Vámonos, amigo!"];   // one at random, in big pixel text (v39: kept in Spanish on purpose; everything else is English)
    let caughtMsg = CAUGHT[0];
    let level = 1, ents = [], hero, camX = 0, score = 0, ckScore = 0, ck = 0, mode = "title", t = 0, raf = null, last = 0, shake = 0, parts = [], msgT = 0, msg = "";
    let fx = [], fxMade = 0, dustT = 0, paused = false;
    const oy = () => GROUND - (H - STREET);   // world y at the top of the screen
    function spawn(atCheck) {
      ents = buildLevel(level);
      const x0 = CHECKS[atCheck];
      ents = ents.filter((e) => !(e.t === "coin" && e.x < x0));
      hero = { x: x0 + 8, y: GROUND - 18, w: 10, h: 18, vy: 0, ground: true, jumps: 2, boost: 0, shield: 0, stumble: 0, inv: 0, frame: 0 };
      camX = hero.x - HERO_X; score = ckScore; parts = []; fx = []; msgT = 0; shake = 0;
    }
    function startLevel(n, keepScore) {
      level = n; ck = 0; paused = false; if (!keepScore) ckScore = 0; spawn(0); mode = "run"; overlay(null); fs.enter(); fit();
      el.querySelector("#ice-note").textContent = `Level ${n}: run to ${LEVELS[n - 1].name}. ${LEVELS[n - 1].hint}`; loop(); ctrl();
    }
    function overlay(html, cls = "") { ov.className = "ice-ov" + (html ? " on " + cls : ""); ov.innerHTML = html || ""; }
    const speed = () => LEVELS[level - 1].speed * (reduced() ? 0.85 : 1) * (hero.boost > 0 ? 1.45 : 1) * (hero.stumble > 0 ? 0.5 : 1);
    function jump() {
      if (mode === "title") { try { root.dispatchEvent(new CustomEvent("chisme-game-play", { detail: "icebebe" })); } catch (e) {} startLevel(Math.min(st.levelMax, 1)); return; }
      if (mode !== "run") return;
      audio();
      if (hero.ground) { hero.vy = JUMP; hero.ground = false; hero.jumps = 1; SFX.jump(); puff(hero.x + 4, hero.y + hero.h, 3, "dust"); }
      else if (hero.jumps > 0) { hero.vy = JUMP2; hero.jumps = 0; SFX.jump2(); puff(hero.x + 5, hero.y + hero.h, 4, "spark"); }
    }
    function release() { if (mode === "run" && hero.vy < -110) hero.vy *= 0.55; }   // short tap = short hop
    // ---- particles: dust when he runs and lands, sparkles on conchas and power-ups (none with reduce motion)
    function puff(x, y, n, kind) {
      if (reduced()) return;
      for (let i = 0; i < n; i++) {
        fxMade++;
        if (kind === "dust") fx.push({ k: "dust", x: x + Math.random() * 4 - 2, y: y - 1 - Math.random() * 2, vx: -6 - Math.random() * 20, vy: -6 - Math.random() * 14, life: 0.3 + Math.random() * 0.25, c: Math.random() < 0.5 ? "#e8edf2" : "#b7bdc6" });
        else { const a = (i / n) * Math.PI * 2 + Math.random() * 0.6, sp = 24 + Math.random() * 40;
          fx.push({ k: "spark", x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 8, life: 0.4 + Math.random() * 0.35, c: FIESTA[i % 4] }); }
      }
      if (fx.length > 180) fx.splice(0, fx.length - 180);
    }
    function caught() {
      mode = "caught"; caughtMsg = CAUGHT[Math.floor(Math.random() * CAUGHT.length)]; SFX.caught(); if (!reduced()) shake = 0.25;
      st.best = Math.max(st.best, score); save(st); stats();
      overlay(`<p class="sr-only">${caughtMsg}</p><p class="ice-caught">Try again, from the ${ck ? "checkpoint 🚩" : "start"}.</p>`, "soft caught");
      setTimeout(() => { if (mode === "caught") { spawn(ck); mode = "run"; overlay(null); } }, 1400);
    }
    function clear() {
      const L = LEVELS[level - 1]; score += 500; ckScore = score; st.best = Math.max(st.best, score);
      SFX.clear(); puff(hero.x + 5, hero.y, 16, "spark");
      if (level === 5) {
        mode = "win"; st.wins++; st.levelMax = 5; save(st); stats();
        if (!reduced()) for (let i = 0; i < 110; i++) parts.push({ x: Math.random() * W, y: -Math.random() * H, vy: 20 + Math.random() * 40, c: ["#00b8b0", "#ff3d8b", "#ff8a00", "#c9d0d8", "#ffffff"][i % 5] });
        overlay(`<p class="ice-big">Welcome home, kid!</p><p class="ice-win-score">Final score <b>${score}</b></p><button type="button" class="lot-btn lot-main" data-act="again">▶ Play again</button>`, "win");
        el.querySelector("#ice-note").innerHTML = `🎉 He made it to Mom's house, and the whole family's celebrating. What a party! <span class="ice-score">Final score <b>${score}</b> · Best <b>${st.best}</b></span> <button type="button" class="lot-btn lot-main" data-act="again">▶ Play again</button>`;
        return;
      }
      st.levelMax = Math.max(st.levelMax, level + 1); save(st); stats();
      mode = "clear";
      overlay(`<p class="ice-big">You made it to ${L.name}!</p><p>+500 · Score <b>${score}</b></p><button type="button" class="lot-btn lot-main" data-act="next">▶ Level ${level + 1}: ${LEVELS[level].name}</button>`, "clear");
      el.querySelector("#ice-note").textContent = `Next up: ${LEVELS[level].name}. ${LEVELS[level].hint}`;
    }
    function update(dt) {
      t += dt;
      for (const p of fx) { p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += (p.k === "dust" ? 18 : 70) * dt; }
      if (fx.length) fx = fx.filter((p) => p.life > 0);
      if (mode === "win") { for (const p of parts) { p.y += p.vy * dt; if (p.y > H) p.y -= H + 10; } return; }
      if (mode !== "run") return;
      const h = hero, vx = speed(), wasGround = h.ground;
      h.boost = Math.max(0, h.boost - dt); h.stumble = Math.max(0, h.stumble - dt); h.inv = Math.max(0, h.inv - dt);
      h.x += vx * dt; h.frame += vx * dt / 7;
      const prevBottom = h.y + h.h;
      h.vy += GRAV * dt; h.y += h.vy * dt; h.ground = false;
      if (h.y + h.h >= GROUND) { h.y = GROUND - h.h; h.vy = 0; h.ground = true; h.jumps = 2; }
      for (const e of ents) {
        if (e.gone) continue;
        if (e.t === "agent") {
          e.tt = Math.max(0, e.tt - dt);
          if (e.st === "walk") { e.x += e.vx * dt; if (e.x < e.home - 60 || e.x > e.home + 10) e.vx = -e.vx;
            const cone = ents.find((c) => c.t === "cone" && !c.down && Math.abs(c.x - e.x) < 5);
            if (cone) { e.st = "tripped"; e.tt = 2.2; cone.down = true; puff(e.x + 4, GROUND, 4, "dust"); } }
          else if (e.tt === 0) e.st = "walk";
        }
        if (e.t === "flag" && !e.done && h.x >= e.x) { e.done = true; ck = CHECKS.indexOf(e.x); ckScore = score; SFX.check(); msg = "Checkpoint!"; msgT = 1.2; puff(e.x + 4, e.y + 3, 10, "spark"); }
        if ((e.t === "suv" || e.t === "crate") && h.x + h.w - 2 > e.x && h.x + 2 < e.x + e.w) {
          if (h.vy >= 0 && prevBottom <= e.y + 3 && h.y + h.h >= e.y) { h.y = e.y - h.h; h.vy = 0; h.ground = true; h.jumps = 2; }   // landed on the roof
          else if (h.y + h.h > e.y + 3 && h.x + h.w - 2 < e.x + 8) {
            if (h.shield > 0 || h.inv > 0) { if (!h.inv) { h.shield = 0; h.inv = 1; SFX.shield(); puff(h.x + 5, h.y + 8, 8, "spark"); } h.vy = JUMP; h.y = e.y - h.h - 1; }
            else if (e.t === "suv") { caught(); return; }
            else { h.x = e.x - h.w + 1; h.stumble = 0.4; puff(h.x + 8, h.y + h.h, 3, "dust"); }   // bumped a crate: a stumble
          }
        }
        if (!hit(h, e)) continue;
        if (e.t === "coin") { e.gone = true; score += 10; SFX.coin(); puff(e.x + 3, e.y + 2, 5, "spark"); }
        else if (e.t === "cup") { e.gone = true; h.boost = 5; score += 50; SFX.power(); msg = "Coffee! Speed boost"; msgT = 1.5; puff(e.x + 4, e.y + 4, 16, "spark"); }
        else if (e.t === "chancla") { e.gone = true; h.shield = 1; score += 50; SFX.power(); msg = "Flip-flop! Shield on"; msgT = 1.5; puff(e.x + 4, e.y + 3, 16, "spark"); }
        else if (e.t === "cone" && !e.down) { e.down = true; h.stumble = 0.6; SFX.cone(); puff(e.x + 3, GROUND, 4, "dust"); }
        else if (e.t === "agent" && e.st === "walk" && hit(h, e, 3)) {
          if (h.inv > 0) continue;
          if (h.shield > 0) { h.shield = 0; h.inv = 1.2; e.st = "dizzy"; e.tt = 2.5; SFX.shield(); msg = "Huh? He's dizzy!"; msgT = 1.3; score += 100; puff(e.x + 5, e.y, 10, "spark"); }
          else { caught(); return; }
        }
      }
      // a clean hop over an agent: a few bonus points
      for (const e of ents) if (e.t === "agent" && !e.passed && h.x > e.x + e.w) { e.passed = true; score += 25; }
      // dust: little puffs behind his boots while he runs, a bigger one when he lands
      if (h.ground && !wasGround) puff(h.x + 5, h.y + h.h, 6, "dust");
      else if (h.ground) { dustT -= dt; if (dustT <= 0) { dustT = h.boost > 0 ? 0.06 : 0.13; puff(h.x + 1, h.y + h.h, 1, "dust"); } }
      camX = h.x - HERO_X;
      if (h.x >= END) clear();
      msgT = Math.max(0, msgT - dt); shake = Math.max(0, shake - dt);
    }
    // ---- drawing (inside draw(), world y is translated so GROUND sits STREET px above the bottom)
    function spr(rows, x, y, flip = false, pal = C) {
      for (let r = 0; r < rows.length; r++) { const row = rows[r];
        for (let c = 0; c < row.length; c++) { const ch = row[c]; if (ch === ".") continue; g.fillStyle = pal[ch] || ch; g.fillRect(Math.round(x + (flip ? row.length - 1 - c : c)), Math.round(y + r), 1, 1); } }
    }
    function text(s, x, y, col = "#fff", sc = 1, shadow = "#111", gc = g) {
      s = s.toUpperCase(); x = Math.round(x); y = Math.round(y);
      const draw = (ox, oy2, colr) => { gc.fillStyle = colr; let cx = x + ox;
        for (const ch0 of s) { const acc = "ÁÉÍÓÚÑ".includes(ch0), ch = { Á: "A", É: "E", Í: "I", Ó: "O", Ú: "U", Ñ: "N" }[ch0] || ch0, f = F[ch] || F["?"];
          for (let i = 0; i < 15; i++) if (f[i] === "1") gc.fillRect(cx + (i % 3) * sc, y + oy2 + Math.floor(i / 3) * sc, sc, sc);
          if (acc) gc.fillRect(cx + (ch0 === "Ñ" ? 0 : 1) * sc, y + oy2 - 2 * sc, (ch0 === "Ñ" ? 3 : 1) * sc, sc);
          cx += 4 * sc; } };
      if (shadow) draw(sc, sc, shadow); draw(0, 0, col);
    }
    const tw = (s, sc = 1) => s.length * 4 * sc - sc;
    const rect = (c, x, y, w, h) => { g.fillStyle = c; g.fillRect(Math.round(x), Math.round(y), w, h); };
    function disc(c, cx, cy, r) { g.fillStyle = c; for (let dy = -r; dy <= r; dy++) { const w = Math.floor(Math.sqrt(r * r - dy * dy)); g.fillRect(Math.round(cx - w), Math.round(cy + dy), 2 * w + 1, 1); } }
    const par = () => (reduced() ? 0 : 1);
    const layerX = (f, period) => -Math.round(mod(camX * f * par(), period));   // whole pixels: no blended (off-palette) edges
    const night = () => level === 5;
    function sky() {
      const L = LEVELS[level - 1], top = oy(), gr = g.createLinearGradient(0, top, 0, GROUND);
      gr.addColorStop(0, L.sky[0]); gr.addColorStop(1, L.sky[1]); g.fillStyle = gr; g.fillRect(0, top, W, GROUND - top);
      if (night()) {   // stars (a few twinkle) and the moon
        for (let i = 0; i < 46; i++) { const sx = (i * 53 + 7) % W, sy = top + 26 + (i * 29) % Math.max(40, GROUND - top - 110);
          if (!reduced() && i % 5 === 0 && Math.floor(t * 2 + i) % 3 === 0) continue;
          rect(i % 7 === 0 ? "#7ff0f2" : "#ffffff", sx, sy, 1, 1); }
        disc("#e6ecf2", 120, top + 46, 8); rect("#c9d0d8", 116, top + 43, 3, 2); rect("#c9d0d8", 122, top + 49, 2, 2); rect("#c9d0d8", 118, top + 50, 2, 1);
      } else if (level <= 2) { disc("#eaf8ff", 122, top + 44, 10); disc("#ffffff", 122, top + 44, 6); }
      else if (level === 3) { disc("#ffb8a6", 42, GROUND - 58, 13); disc("#ff9e8a", 42, GROUND - 58, 10); }
      else disc("#ff7aa8", 112, GROUND - 46, 11);
      if (!night()) {   // drifting pixel clouds (still with reduce motion)
        const col = level >= 3 ? ["#ffe6ef", "#f4bfd3"] : ["#ffffff", "#d7e6f0"], span = W + 80;
        [[10, 30, 1], [70, 52, 0], [128, 22, 1], [190, 70, 0], [240, 40, 1]].forEach(([cx, cy, big]) => {
          const x = Math.round(mod(cx - camX * 0.05 * par() - t * 3 * par(), span)) - 40, y = top + cy;
          rect(col[0], x + 4, y, big ? 16 : 10, 3); rect(col[0], x, y + 3, big ? 28 : 18, 4); rect(col[0], x + 8, y - 3, big ? 8 : 5, 3); rect(col[1], x + 1, y + 7, big ? 26 : 16, 1);
        });
        if (!reduced()) for (let i = 0; i < 3; i++) {   // grackles flapping across
          const bx = Math.round(mod(60 * i - t * (10 + i * 3) - camX * 0.08, W + 40)) - 20, by = top + 58 + i * 13 + Math.round(Math.sin(t * 2 + i) * 2), up = Math.floor(t * 6 + i) % 2;
          rect("#2b3346", bx, by + (up ? 0 : 1), 2, 1); rect("#2b3346", bx + 2, by + 1, 1, 1); rect("#2b3346", bx + 3, by + (up ? 0 : 1), 2, 1);
        }
      }
    }
    function farRow() {   // far skyline: a generic observation tower, a mission-style dome, high-rises
      const L = LEVELS[level - 1], off = layerX(0.12, 300), lit = night() ? ["#ff8fbf", "#7ff0f2"] : null;
      for (let k = -1; k < 2; k++) { const b = off + k * 300;
        rect(L.far, b + 10, GROUND - 104, 24, 104); rect(L.far, b + 80, GROUND - 128, 22, 128); rect(L.far, b + 190, GROUND - 116, 30, 116); rect(L.far, b + 240, GROUND - 146, 18, 146); rect(L.far, b + 262, GROUND - 98, 26, 98);
        rect(L.far, b + 243, GROUND - 152, 12, 6); rect(L.far, b + 248, GROUND - 160, 2, 8); rect(L.far, b + 84, GROUND - 134, 14, 6);   // rooftops + an antenna
        rect(L.far, b + 142, GROUND - 168, 4, 168); rect(L.far, b + 136, GROUND - 177, 16, 10); rect(L.far, b + 140, GROUND - 181, 8, 4); rect(L.far, b + 143, GROUND - 188, 2, 7);   // the tower
        rect(L.far, b + 40, GROUND - 86, 32, 86); rect(L.far, b + 46, GROUND - 94, 20, 8); rect(L.far, b + 50, GROUND - 99, 12, 5); rect(L.far, b + 54, GROUND - 103, 4, 4);   // a dome
        if (lit) for (let i = 0; i < 15; i++) rect(lit[i % 2], b + 84 + (i % 3) * 6, GROUND - 122 + Math.floor(i / 3) * 10, 2, 3);
        else { g.fillStyle = L.win; for (let i = 0; i < 10; i++) g.fillRect(b + 243 + (i % 2) * 7, GROUND - 140 + Math.floor(i / 2) * 11, 4, 5);
          for (let i = 0; i < 8; i++) g.fillRect(b + 13 + (i % 3) * 7, GROUND - 98 + Math.floor(i / 3) * 10, 3, 4); rect(L.win, b + 136, GROUND - 174, 16, 1); }
      }
    }
    function midRow() {   // mid-rise blocks with windows, a water tower, a billboard, palms
      const L = LEVELS[level - 1], off = layerX(0.3, 240);
      for (let k = -1; k < 2; k++) { const b = off + k * 240;
        rect(L.mid, b, GROUND - 108, 46, 108); rect(L.mid, b + 4, GROUND - 112, 38, 4); rect(L.mid, b + 180, GROUND - 94, 52, 94);
        g.fillStyle = night() ? "#ff8fbf" : L.win;
        for (let i = 0; i < 16; i++) if (!night() || i % 3 !== 1) g.fillRect(b + 5 + (i % 4) * 10, GROUND - 102 + Math.floor(i / 4) * 11, 5, 6);
        g.fillStyle = night() ? "#7ff0f2" : L.win; for (let i = 0; i < 12; i++) if (!night() || i % 4 !== 2) g.fillRect(b + 186 + (i % 4) * 11, GROUND - 88 + Math.floor(i / 4) * 11, 6, 6);
        // water tower on legs
        rect(L.mid, b + 58, GROUND - 102, 18, 16); rect(L.mid, b + 60, GROUND - 107, 14, 5); rect(L.mid, b + 66, GROUND - 110, 2, 3);
        rect(L.mid, b + 60, GROUND - 86, 2, 86); rect(L.mid, b + 72, GROUND - 86, 2, 86); rect(L.mid, b + 62, GROUND - 70, 10, 1); rect(L.mid, b + 62, GROUND - 52, 10, 1);
        if (L.board) {   // a billboard (plain words, no brands)
          const bw = Math.max(50, tw(L.board) + 12), bx = b + 98;
          rect(L.mid, bx + 8, GROUND - 82, 2, 82); rect(L.mid, bx + bw - 10, GROUND - 82, 2, 82);
          rect("#111111", bx, GROUND - 104, bw, 22); rect("#ffffff", bx + 2, GROUND - 102, bw - 4, 18); rect("#ff3d8b", bx + 2, GROUND - 88, bw - 4, 4);
          text(L.board, bx + Math.round((bw - tw(L.board)) / 2), GROUND - 98, "#111111", 1, null);
          if (level === 4) { rect("#ffe0ec", bx + 6, GROUND - 106, 2, 2); rect("#ffe0ec", bx + bw - 8, GROUND - 106, 2, 2); }
        }
        if (level !== 5) for (const px of [b + 88, b + 172]) {   // palm trees
          rect("#8f5a36", px, GROUND - 76, 2, 76); for (let k = 1; k < 7; k++) rect("#6e4428", px, GROUND - 76 + k * 11, 2, 1);
          g.fillStyle = "#2f8f5a"; g.fillRect(px - 8, GROUND - 79, 8, 2); g.fillRect(px + 2, GROUND - 79, 8, 2); g.fillRect(px - 11, GROUND - 77, 3, 2); g.fillRect(px + 10, GROUND - 77, 3, 2); g.fillRect(px - 3, GROUND - 83, 8, 3);
          g.fillRect(px - 13, GROUND - 75, 2, 2); g.fillRect(px + 13, GROUND - 75, 2, 2);
        }
      }
    }
    function shop(x, i, L) {   // a storefront: facade, sign, striped awning, window display, door
      const hh = [58, 50, 62, 54][i], top = GROUND - 6 - hh, wall = L.near[i], stripe = FIESTA[(i + level) % 3];
      rect(wall, x, top, 70, hh); rect("#111111", x, top, 70, 2); rect("#ffffff", x, top + 2, 70, 1);
      const word = L.shops[i] || "", sw = Math.max(tw(word) + 8, 26);
      rect("#111111", x + Math.round((70 - sw) / 2), top + 6, sw, 11); text(word, x + Math.round((70 - tw(word)) / 2), top + 9, ["#3ee8eb", "#ffffff", "#ff8fbf", "#3ee8eb"][i], 1, null);
      for (let s = 0; s < 70; s += 6) { rect(Math.floor(s / 6) % 2 ? "#ffffff" : stripe, x + s, top + 21, 6, 6); rect(Math.floor(s / 6) % 2 ? "#ffffff" : stripe, x + s + 1, top + 27, 4, 1); }
      rect("#111111", x + 5, top + 31, 38, GROUND - 6 - top - 33); rect("#9fd8ff", x + 7, top + 33, 34, GROUND - 6 - top - 37);
      rect("#ffffff", x + 10, top + 35, 1, 6); rect("#ffffff", x + 11, top + 34, 1, 2);   // glass glint
      for (let d = 0; d < 3; d++) rect(FIESTA[(d + i) % 3], x + 12 + d * 9, GROUND - 16, 6, 5);   // goods in the window
      rect("#2b3346", x + 48, top + 31, 16, GROUND - 6 - top - 31); rect("#9fd8ff", x + 51, top + 34, 10, 10); rect("#c9d0d8", x + 60, GROUND - 22, 2, 2);
    }
    function house(x, i, L) {   // Mom's street at night: little houses with porches and lit windows
      const top = GROUND - 44 - (i % 2) * 6, wall = L.near[i];
      rect(wall, x + 4, top, 62, GROUND - 6 - top);
      g.fillStyle = "#1a1530"; for (let r = 0; r < 12; r++) g.fillRect(x + 4 + r * 2 - 4, top - r, 70 - r * 4 + 0, 1);   // roof
      rect("#7ff0f2", x + 10, top + 10, 12, 10); rect(wall, x + 15, top + 10, 1, 10); rect(wall, x + 10, top + 15, 12, 1);
      rect("#ff8fbf", x + 46, top + 10, 12, 10); rect(wall, x + 51, top + 10, 1, 10);
      rect("#2b1d17", x + 28, GROUND - 26, 12, 20); rect("#ffe0ec", x + 26, GROUND - 30, 2, 2);   // door + porch light
      rect("#c9d0d8", x, GROUND - 14, 70, 1); for (let f = 0; f < 70; f += 5) rect("#8a93a8", x + f, GROUND - 14, 1, 8);   // chain-link fence
    }
    function nearRow() {
      const L = LEVELS[level - 1], per = 4 * 74, off = layerX(0.6, per);
      for (let k = -1; k < 2; k++) for (let i = 0; i < 4; i++) { const x = off + k * per + i * 74; if (x > W || x + 72 < 0) continue; (night() ? house : shop)(x, i, L); }
      if (level >= 4) {   // papel picado / string lights across the street (blinking at night)
        const off2 = layerX(0.6, 20), y0 = GROUND - 78;
        rect("#111111", 0, y0, W, 1);
        for (let x = off2 - 20, i = 0; x < W + 20; x += 10, i++) { const c = FIESTA[mod(i + Math.round(camX * 0.6 * par() / 10), 4)];
          if (night()) { if (reduced() || Math.floor(t * 3 + i) % 4) rect(c, x + 2, y0 + 1 + (i % 2), 3, 3); }
          else { rect(c, x, y0 + 1, 7, 6); rect(c === "#ffffff" ? "#ff3d8b" : "#ffffff", x + 2, y0 + 3, 3, 2); } }
      }
    }
    function street() {
      const bot = oy() + H, nt = night(), road = GROUND + 14, lane = road + Math.round((bot - road - 16) / 2);
      rect(nt ? "#4a4f63" : "#b9bec7", 0, GROUND - 6, W, 6);             // the back of the sidewalk (props stand here)
      rect(nt ? "#626882" : "#d5d9df", 0, GROUND, W, 11); rect(nt ? "#8a93a8" : "#eef1f4", 0, GROUND, W, 1);
      for (let x = -Math.round(mod(camX, 16)); x < W; x += 16) { rect(nt ? "#4a4f63" : "#aeb3bb", x, GROUND + 1, 1, 10); rect(nt ? "#4a4f63" : "#aeb3bb", x - 6, GROUND - 6, 1, 6); }
      rect("#8a8f99", 0, GROUND + 11, W, 3); rect("#c9ced6", 0, GROUND + 11, W, 1);   // curb
      rect(nt ? "#26283a" : "#3a3a42", 0, road, W, bot - road);
      if (level === 1) {   // the big-box parking lot: white stall lines
        for (let x = -Math.round(mod(camX, 22)); x < W; x += 22) { rect("#e8edf2", x, road + 4, 1, 16); rect("#e8edf2", x, bot - 26, 1, 16); }
        rect("#e8edf2", 0, lane + 1, W, 1);
      } else for (let x = -Math.round(mod(camX, 24)); x < W; x += 24) rect(nt ? "#9aa3b5" : "#e8edf2", x, lane, 12, 2);
      for (let x = -Math.round(mod(camX, 190)) + 60; x < W; x += 190) { rect("#22232b", x, lane + 10, 12, 3); rect("#4a4d57", x + 2, lane + 11, 8, 1); }   // a manhole
      if (!reduced()) {   // a lowrider cruising by the other way
        const cx = Math.round(W + 40 - mod(t * 34 + camX, W + 110)), cy = lane + 6;
        rect("#ff3d8b", cx, cy + 3, 30, 5); rect("#ff3d8b", cx + 6, cy, 16, 4); rect("#9fd8ff", cx + 8, cy + 1, 5, 2); rect("#9fd8ff", cx + 15, cy + 1, 5, 2);
        rect("#00b8b0", cx + 2, cy + 5, 26, 1); rect("#ffffff", cx, cy + 4, 2, 1);
        rect("#111111", cx + 4, cy + 7, 6, 3); rect("#111111", cx + 21, cy + 7, 6, 3); rect("#c9d0d8", cx + 6, cy + 8, 2, 1); rect("#c9d0d8", cx + 23, cy + 8, 2, 1);
      }
      // the near curb and a talavera-tile planter wall in the foreground (a touch faster: it's closer)
      rect("#8a8f99", 0, bot - 14, W, 2); rect(nt ? "#3a3f52" : "#e8edf2", 0, bot - 12, W, 12);
      const fk = reduced() ? 1 : 1.25, fo = -Math.round(mod(camX * fk, 12));
      for (let x = fo - 12, i = Math.floor(camX * fk / 12) - 1; x < W + 12; x += 12, i++) {
        const c = ["#00b8b0", "#ff3d8b", "#2d4a8a", "#ff8a00"][mod(i, 4)], wht = nt ? "#3a3f52" : "#ffffff";
        rect(c, x + 1, bot - 11, 10, 10); rect(wht, x + 4, bot - 8, 4, 4); rect(c, x + 5, bot - 7, 2, 2); rect(wht, x + 1, bot - 11, 2, 2); rect(wht, x + 9, bot - 3, 2, 2);
      }
      rect("#111111", 0, bot - 12, W, 1);
    }
    function props() {   // sidewalk props, behind the runner: lamp posts, hydrants, benches, palms, bins, news boxes, meters
      const step = 64, first = Math.floor((camX - 30) / step);
      for (let i = first; i < first + 5; i++) {
        const wx = i * step + 20, x = Math.round(wx - camX), b = GROUND - 2; if (wx < 30 || wx > END - 140) continue;
        const kind = (Math.imul(i + level * 13, 2654435761) >>> 0) % 7;
        if (kind === 0) { rect("#5b6270", x, b - 44, 2, 44); rect("#5b6270", x, b - 44, 8, 1); rect(night() ? "#ffe0ec" : "#ffffff", x + 6, b - 43, 4, 2); rect("#5b6270", x - 1, b - 2, 4, 2);
          if (night()) { rect("#3a3260", x + 4, b - 41, 8, 1); } }
        else if (kind === 1) { rect("#e0453a", x, b - 7, 5, 7); rect("#e0453a", x - 1, b - 5, 7, 2); rect("#b0302a", x, b - 8, 5, 1); }
        else if (kind === 2) { rect("#3d8a7a", x, b - 9, 7, 9); rect("#2c6a5e", x - 1, b - 10, 9, 2); rect("#2c6a5e", x + 2, b - 6, 3, 1); }
        else if (kind === 3) { rect("#8f5a36", x, b - 6, 14, 2); rect("#8f5a36", x, b - 10, 14, 1); rect("#5b6270", x + 1, b - 4, 1, 4); rect("#5b6270", x + 12, b - 4, 1, 4); rect("#5b6270", x + 1, b - 10, 1, 4); }
        else if (kind === 4 && !night()) { rect("#c9d0d8", x - 3, b - 6, 10, 6); rect("#8f5a36", x + 1, b - 28, 2, 22); g.fillStyle = "#2f8f5a"; g.fillRect(x - 5, b - 31, 6, 2); g.fillRect(x + 3, b - 31, 6, 2); g.fillRect(x - 1, b - 34, 6, 3); g.fillRect(x - 7, b - 29, 2, 2); g.fillRect(x + 9, b - 29, 2, 2); }
        else if (kind === 5) { rect("#00b8b0", x, b - 9, 6, 9); rect("#9fd8ff", x + 1, b - 8, 4, 3); rect("#007f7a", x, b - 1, 6, 1); }
        else { rect("#5b6270", x + 1, b - 9, 1, 9); rect("#8a929c", x, b - 13, 3, 4); rect("#3ee8eb", x + 1, b - 12, 1, 1); }
      }
    }
    const destW = () => (level === 1 ? 150 : 120);
    const destX = () => END - HERO_X + Math.round((W - destW()) / 2);   // centered on screen when he arrives
    function destination() {
      const L = LEVELS[level - 1], x = Math.round(destX() - camX); if (x > W + 10) return;
      if (level === 1) {   // Home Dehole: a parody big-box store. Beige block, wide orange banner, white pixel letters. No logo.
        const bw = 150, top = GROUND - 96;
        rect("#e0d2c0", x, top, bw, GROUND - top); rect("#bfae98", x, top, bw, 5);
        g.fillStyle = "#cdbfae"; for (let i = 15; i < bw; i += 15) g.fillRect(x + i, top + 5, 1, GROUND - top - 5);
        rect("#ff7a00", x + 9, top + 11, 132, 20); rect("#c95f00", x + 9, top + 29, 132, 2);
        text("HOME DEHOLE", x + 9 + Math.round((132 - tw("HOME DEHOLE", 2)) / 2), top + 16, "#ffffff", 2, null);
        rect("#ff7a00", x + 44, GROUND - 46, 62, 4); rect("#c95f00", x + 44, GROUND - 42, 62, 1);   // entrance canopy
        rect("#8a929c", x + 50, GROUND - 41, 50, 41); rect("#bfe6f5", x + 53, GROUND - 38, 21, 38); rect("#bfe6f5", x + 76, GROUND - 38, 21, 38);
        rect("#ffffff", x + 56, GROUND - 35, 1, 8); rect("#ffffff", x + 79, GROUND - 35, 1, 8); rect("#8a929c", x + 74, GROUND - 38, 2, 38);
        for (const cx of [x + 8, x + 20, x + 122, x + 134]) { rect("#ff7a00", cx, GROUND - 14, 9, 14); rect("#c95f00", cx + 2, GROUND - 11, 5, 1); rect("#c95f00", cx + 2, GROUND - 7, 5, 1); }   // stacked carts, just blocks
        g.fillStyle = "#c9b8a6"; g.fillRect(x + 108, GROUND - 8, 10, 8); g.fillRect(x + 109, GROUND - 14, 8, 6);   // bags of soil by the door
        return;
      }
      const bw = 120, top = level === 4 ? GROUND - 78 : GROUND - 84;
      const wall = ["#ff8a00", "#00b8b0", "#ff3d8b", "#dfe4ea", "#ff3d8b"][level - 1];
      rect(wall, x, top, bw, GROUND - top); rect("#111111", x, top, bw, 2);
      if (level === 4) {   // a plaza church facade: bell tower, round window, arched wooden door
        rect("#dfe4ea", x + 44, top - 26, 32, 26); rect("#111111", x + 54, top - 21, 12, 10); rect("#c9d0d8", x + 58, top - 18, 4, 5);
        rect("#dfe4ea", x + 52, top - 34, 16, 8); rect("#dfe4ea", x + 57, top - 40, 6, 6);
        disc("#111111", x + 60, top + 26, 6); disc("#00b8b0", x + 60, top + 26, 4);
        rect("#6b3b1f", x + 48, GROUND - 34, 24, 34); rect("#6b3b1f", x + 51, GROUND - 37, 18, 3); rect("#111111", x + 59, GROUND - 34, 2, 34);
        for (const tx of [x + 8, x + 98]) { rect("#8f5a36", tx + 6, GROUND - 16, 2, 16); disc("#2f8f5a", tx + 7, GROUND - 22, 8); }   // plaza trees
      } else if (level === 5) {   // Mom's house: pitched roof, porch, papel picado, balloons, the family party
        g.fillStyle = "#b03a2e"; for (let i = 0; i < 18; i++) g.fillRect(x - 6 + i * 3, top - Math.round(i * 1.3), bw + 12 - i * 6, 2);
        rect("#7ff0f2", x + 12, top + 18, 18, 14); rect("#7ff0f2", x + 90, top + 18, 18, 14); rect("#ff3d8b", x + 20, top + 18, 1, 14); rect("#ff3d8b", x + 98, top + 18, 1, 14);
        rect("#6b3b1f", x + 52, GROUND - 34, 16, 34); rect("#ffffff", x + 64, GROUND - 18, 2, 2);
        rect("#dfe4ea", x + 38, GROUND - 40, 44, 3); rect("#dfe4ea", x + 40, GROUND - 37, 2, 37); rect("#dfe4ea", x + 78, GROUND - 37, 2, 37);   // porch
        const cols = ["#ff3d8b", "#00b8b0", "#ff8a00", "#ffffff", "#c9d0d8"]; for (let i = 0; i < 20; i++) rect(cols[i % 5], x - 30 + i * 9, top - 4 + (i % 2), 6, 6);
        [[x + 6, "#ff3d8b"], [x + 112, "#00b8b0"], [x + 118, "#ff8a00"]].forEach(([bx, c], i) => { const by = top + 2 + (reduced() ? 0 : Math.round(Math.sin(t * 2 + i) * 1.5));
          rect("#c9d0d8", bx + 2, by + 8, 1, 12); disc(c, bx + 2, by + 4, 3); rect("#ffffff", bx + 1, by + 2, 1, 1); });
      } else {
        rect("#111111", x + 10, GROUND - 38, 32, 38); rect("#9fd8ff", x + 12, GROUND - 36, 28, 22); rect("#ffffff", x + 15, GROUND - 34, 1, 7);
        rect("#9fd8ff", x + 56, top + 24, 52, 24); rect("#111111", x + 56, top + 35, 52, 1);
        if (level === 2) { for (let i = 0; i < 9; i++) rect(i % 2 ? "#ffffff" : "#ff3d8b", x + 52 + i * 6, top + 17, 6, 6);   // an awning
          rect("#111111", x + 64, top + 38, 20, 8); text("OPEN", x + 66, top + 40, "#ff8fbf", 1, null); }
        if (level === 3) { rect("#ffffff", x + 70, GROUND - 16, 30, 16); rect("#9fd8ff", x + 70, GROUND - 16, 30, 3); text("ICE", x + 79, GROUND - 11, "#00b8b0", 1, null); }
      }
      const sign = L.sign, sw = tw(sign) + 8;
      rect("#111111", x + (bw - sw) / 2, top + 4, sw, 11); text(sign, x + (bw - sw) / 2 + 4, top + 7, "#3ee8eb", 1, null);
    }
    function family(x) {   // the party at Mom's: generic pixel family members, arms up and dancing
      const kin = [["#ff3d8b", "#8f5a36", 14], ["#00b8b0", "#b0754a", 12], ["#ff8a00", "#6e4428", 10], ["#ff8fbf", "#b0754a", 16], ["#c9d0d8", "#8f5a36", 13]];
      kin.forEach(([shirt, skin, hgt], i) => { const fx0 = x + i * 13, fy = GROUND - hgt, move = !reduced() && mode === "win", bob = move ? Math.round(Math.sin(t * 8 + i)) : 0, up = move ? Math.floor(t * 4 + i) % 2 : 1;
        rect(skin, fx0 + 1, fy - 5 + bob, 5, 5); rect("#111111", fx0 + 1, fy - 6 + bob, 5, 2);
        rect(shirt, fx0, fy + bob, 7, hgt - 5);
        rect(skin, fx0 - 1, fy - (up ? 4 : 0) + bob, 1, 4); rect(skin, fx0 + 7, fy - (up ? 0 : 4) + bob, 1, 4);
        rect("#223a6e", fx0 + 1, GROUND - 5, 5, 5); });
    }
    function shadow(x, w, air) { rect("rgba(0,0,0,.25)", x + Math.round(air / 2), GROUND - 1, Math.max(3, w - air), 2); }
    function drawEnt(e) {
      const x = Math.round(e.x - camX); if (x < -50 || x > W + 10 || e.gone) return;
      const tick = reduced() ? 0 : Math.floor(t * 6);
      if (e.t === "cone") { if (e.down) { rect("#ff8a00", x - 1, GROUND - 3, 9, 3); rect("#ffffff", x + 2, GROUND - 3, 2, 3); } else spr(CONE, x, e.y); }
      else if (e.t === "coin") { const f = reduced() ? 0 : [0, 1, 2, 1][mod(Math.floor(t * 8 + e.x / 11), 4)];
        spr(CONCHA[f], x, e.y + (reduced() ? 0 : Math.round(Math.sin(t * 5 + e.x) * 1))); }
      else if (e.t === "cup" || e.t === "chancla") {
        const y = e.y + (reduced() ? 0 : Math.round(Math.sin(t * 4 + (e.t === "cup" ? 0 : 1)) * 1.5));
        if (e.t === "cup") { spr(CUP, x, y, false, Object.assign({}, C, { o: "#6b3b1f" })); if (!reduced()) { rect("#ffffff", x + 2, y - 3 - (tick % 3), 1, 2); rect("#ffffff", x + 4, y - 4 - ((tick + 1) % 3), 1, 2); } }   // steam
        else spr(CHANCLA, x, y);
        if (!reduced()) { const a = t * 3, sx = x + 4 + Math.round(Math.cos(a) * 8), sy = y + 3 + Math.round(Math.sin(a) * 6);   // an orbiting twinkle
          rect("#ffffff", sx, sy - 1, 1, 3); rect("#ffffff", sx - 1, sy, 3, 1); rect(tick % 2 ? "#3ee8eb" : "#ff8fbf", x + 10, y - 2, 1, 1); }
      }
      else if (e.t === "crate") { rect("#b8793a", x, e.y, e.w, e.h); rect("#7a4a1f", x, e.y, e.w, 2); rect("#7a4a1f", x, e.y + e.h - 2, e.w, 2); rect("#7a4a1f", x + 2, e.y, 2, e.h); rect("#7a4a1f", x + e.w - 4, e.y, 2, e.h);
        rect("#9a6430", x + 5, e.y + Math.round(e.h / 2), e.w - 10, 1); rect("#e8edf2", x + 3, e.y + 3, 1, 1); rect("#e8edf2", x + e.w - 4, e.y + 3, 1, 1); }
      else if (e.t === "flag") { rect("#c9d0d8", x, e.y, 1, e.h); rect("#8a8f99", x - 1, GROUND - 2, 3, 2); const c = e.done ? "#00b8b0" : "#ff3d8b";
        if (tick % 2) { rect(c, x + 1, e.y, 8, 5); rect(c, x + 3, e.y + 5, 5, 1); } else { rect(c, x + 1, e.y + 1, 8, 5); rect(c, x + 1, e.y, 5, 1); } }
      else if (e.t === "suv") {   // a generic dark SUV: no markings
        shadow(x, e.w, 0);
        rect("#1a1d24", x, e.y + 6, e.w, 12); rect("#1a1d24", x + 4, e.y, e.w - 10, 7);
        rect("#3a4a5a", x + 6, e.y + 1, 10, 5); rect("#3a4a5a", x + 18, e.y + 1, 10, 5); rect("#6a7a8a", x + 7, e.y + 2, 1, 2); rect("#6a7a8a", x + 19, e.y + 2, 1, 2);
        rect("#c9d0d8", x, e.y + 12, e.w, 1); rect("#c9d0d8", x + e.w - 2, e.y + 8, 2, 2); rect("#ff3d8b", x, e.y + 8, 1, 2);
        rect("#111111", x + 5, e.y + 16, 8, 6); rect("#111111", x + e.w - 13, e.y + 16, 8, 6);
        rect("#8a929c", x + 8, e.y + 18, 2, 2); rect("#8a929c", x + e.w - 10, e.y + 18, 2, 2);
      } else if (e.t === "agent") {
        const flip = e.vx > 0;
        if (e.st === "tripped") {   // flat on the ground, legs kicking in the air: slapstick, gets back up
          const kick = tick % 2;
          rect("#1f2a3d", x - 3, GROUND - 5, 12, 5); rect("#5b6270", x - 7, GROUND - 5, 4, 4);
          rect("#9c8f80", x + 9, GROUND - 9 - kick, 3, 6); rect("#9c8f80", x + 12, GROUND - 7 + kick, 3, 4); rect("#111111", x + 9, GROUND - 10 - kick, 3, 1);
          rect("#2b3346", x - 10 - (tick % 4), GROUND - 3 - kick, 5, 2);   // the cap rolled off
          text("!?", x - 2, GROUND - 16, "#ff3d8b");
        } else {
          shadow(x, e.w, 0);
          const walk = e.st === "walk" && !reduced(), f = walk ? mod(Math.floor(t * 8), 4) : 0;
          const rows = AG_HEAD.concat(AG_TORSO[walk ? f % 2 : 0], AG_LEGS[f]);
          const wob = e.st === "dizzy" && !reduced() ? Math.round(Math.sin(t * 14)) : 0;
          spr(rows, x + wob, e.y + (walk && f % 2 ? -1 : 0) + 0, flip);
          if (e.st === "dizzy") {   // little stars circling his cap
            for (let k = 0; k < 3; k++) { const a = (reduced() ? 0 : t * 5) + k * 2.1, sx = x + 5 + Math.round(Math.cos(a) * 7), sy = e.y - 3 + Math.round(Math.sin(a) * 2);
              rect(["#ff3d8b", "#3ee8eb", "#ffffff"][k], sx, sy - 1, 1, 3); rect(["#ff3d8b", "#3ee8eb", "#ffffff"][k], sx - 1, sy, 3, 1); }
            text("?", x + 2, e.y - 11 + (reduced() ? 0 : Math.round(Math.sin(t * 6))), "#ff3d8b");
          }
        }
      }
    }
    function drawHero() {
      const h = hero, x = Math.round(h.x - camX), top = Math.round(h.y + h.h - 16);
      const air = h.ground ? 0 : Math.min(6, Math.round((GROUND - h.y - h.h) / 8));
      shadow(x, 10, air);
      if (h.inv > 0 && !reduced() && Math.floor(t * 12) % 2) return;
      let legs, arms, bob = 0;
      if (mode === "win") { const w = reduced() ? 0 : Math.floor(t * 4) % 2; legs = LEGS_STAND; arms = w ? "u" : "f"; bob = w ? -1 : 0; }
      else if (mode === "title" || mode === "clear") { legs = LEGS_STAND; arms = "n"; }
      else if (!h.ground) { legs = h.vy < 0 ? LEGS_UP : LEGS_DOWN; arms = h.vy < 0 ? "u" : "f"; }
      else { const r = RUN[mod(Math.floor(h.frame), 4)]; legs = r[0]; arms = r[1]; bob = r[2]; }
      if (h.shield > 0) { rect("rgba(255,61,139,.30)", x - 3, top - 2, 16, 19); if (!reduced() && Math.floor(t * 8) % 2) rect("#ffffff", x - 3 + Math.floor(t * 20) % 16, top - 2, 1, 1); }
      spr(HERO_HEAD.concat(TORSO[arms], [BELT], legs), x - 1, top + bob);
      if (mode === "win" && arms === "u") { rect("#b0754a", x + 1, top + bob + 4, 1, 3); rect("#b0754a", x + 10, top + bob + 4, 1, 3); }   // hands up: ¡fiesta!
      if (h.boost > 0 && !reduced()) { for (let i = 0; i < 3; i++) rect(i % 2 ? "#3ee8eb" : "#ffffff", x - 5 - i * 4 - (Math.floor(t * 20) % 3), top + 5 + i * 3, 3, 1); }   // speed lines
    }
    function drawFx() {
      for (const p of fx) { const x = Math.round(p.x - camX), y = Math.round(p.y); g.fillStyle = p.c;
        if (p.k === "dust") g.fillRect(x, y, p.life > 0.2 ? 2 : 1, p.life > 0.2 ? 2 : 1);
        else if (p.life > 0.3) { g.fillRect(x, y - 1, 1, 3); g.fillRect(x - 1, y, 3, 1); } else g.fillRect(x, y, 1, 1); }
    }
    function slot(x, pic, on, frac) {   // HUD power-up slot: lit when active
      rect(on ? "#ff3d8b" : "#3a4058", x, 11, 22, 10); rect("#141726", x + 1, 12, 20, 8);
      if (pic === "cup") spr(CUP, x + 2, 13, false, on ? Object.assign({}, C, { o: "#6b3b1f" }) : DIM); else spr(CHANCLA, x + 2, 14, false, on ? C : DIM);
      if (pic === "cup" && on) rect("#ff8a00", x + 12, 18, Math.max(1, Math.round(8 * frac)), 1);
    }
    function hud() {
      rect("#141726", 0, 0, W, 23); rect("#ff3d8b", 0, 23, W, 1);
      rect("#ff3d8b", 2, 2, 17, 8); text(`LV${level}`, 4, 3, "#ffffff", 1, null);
      const sc = `${score}`; let nm = LEVELS[level - 1].sign; while (nm.length && 23 + tw(nm) > W - tw(sc) - 8) nm = nm.slice(0, -1);
      text(nm, 23, 3, "#c9d0d8", 1, null); text(sc, W - tw(sc) - 3, 3, "#3ee8eb", 1, null);
      const px = Math.min(1, Math.max(0, hero.x / END)), pw = 58;   // progress to the destination
      rect("#3a4058", 3, 15, pw, 3); rect("#00b8b0", 3, 15, Math.round(pw * px), 3);
      for (const c of CHECKS.slice(1)) rect(hero.x >= c ? "#00b8b0" : "#ff3d8b", 3 + Math.round(pw * c / END), 13, 1, 6);
      rect("#ffffff", 2 + Math.round(pw * px), 13, 2, 7);
      rect("#ff8a00", pw + 4, 15, 5, 4); rect("#ff8a00", pw + 5, 14, 3, 1); rect("#141726", pw + 6, 17, 1, 2);   // a tiny house = home
      slot(72, "cup", hero.boost > 0, hero.boost / 5); slot(96, "chancla", hero.shield > 0, 1);
      const bs = `HI${Math.max(st.best, score)}`; text(bs, W - tw(bs) - 3, 14, "#8a93a8", 1, null);
      if (msgT > 0) { const w = tw(msg); rect("rgba(0,0,0,.65)", (W - w) / 2 - 4, 28, w + 8, 11); text(msg, (W - w) / 2, 31, "#3ee8eb", 1, null); }
    }
    function draw() {
      g.save();
      g.translate(shake > 0 && !reduced() ? Math.round((Math.random() - 0.5) * 4) : 0, -oy());
      sky(); farRow(); midRow(); nearRow(); street(); props(); destination();
      if (level === 5 && destX() - camX < W) family(Math.round(destX() + 44 - camX));
      for (const e of ents) drawEnt(e);
      drawHero(); drawFx();
      g.restore();
      if (mode === "win") for (const p of parts) rect(p.c, p.x, p.y, 2, 2);
      hud();
      if (mode === "caught") { const sc = tw(caughtMsg, 3) > W - 12 ? 2 : 3, w = tw(caughtMsg, sc), y = Math.round(H * 0.3);
        rect("rgba(0,0,0,.6)", (W - w) / 2 - 6, y - 6, w + 12, 5 * sc + 12); text(caughtMsg, Math.round((W - w) / 2), y, "#ff3d8b", sc, "#111111"); }
    }
    // the pixel "ICE ICE BEBÉ" badge at the top of the full-screen game
    let badgeDone = false;
    function badge() {
      const b = el.querySelector(".gfs-ice-cv"); if (!b || badgeDone) return; const bg = b.getContext("2d"); badgeDone = true;
      bg.fillStyle = "#00b8b0"; bg.fillRect(1, 0, 58, 15); bg.fillRect(0, 1, 60, 13);
      bg.fillStyle = "#111111"; bg.fillRect(2, 1, 56, 13); bg.fillRect(1, 2, 58, 11);
      bg.fillStyle = "#ff8a00"; bg.fillRect(3, 12, 54, 1);
      text("ICE ICE BEBÉ", 7, 5, "#ffffff", 1, "#ff3d8b", bg);
    }
    function fit() {
      let nh = H0;
      if (fs.on) {
        const r = wrap.getBoundingClientRect();
        if (r.width > 40 && r.height > 40) {
          nh = Math.max(220, Math.min(340, Math.round(W * r.height / r.width)));
          const sc = Math.min(r.width / W, r.height / nh);
          cv.style.width = Math.floor(W * sc) + "px"; cv.style.height = Math.floor(nh * sc) + "px";
        }
      } else { cv.style.width = ""; cv.style.height = ""; }
      if (nh !== H) { H = nh; cv.height = H; g.imageSmoothingEnabled = false; }
      if (!raf && hero) draw();
    }
    function title() {
      level = st.levelMax > 1 ? st.levelMax : 1; spawn(0); mode = "title"; draw();
      const cont = st.levelMax > 1 ? `<button type="button" class="lot-btn" data-act="cont">▶ Keep going: level ${st.levelMax}</button>` : "";
      el.querySelector("#ice-note").textContent = "Run home to Mom's across 5 San Antonio stops: jump the cones, skip past the agents, grab a coffee.";
      overlay(`<p class="ice-big">Ice Ice Bebé</p><p class="ice-btns"><button type="button" class="lot-btn lot-main" data-act="start">▶ Start at level 1</button>${cont}</p>${st.best ? `<p class="ice-score">Best score <b>${st.best}</b></p>` : ""}`, "title");
    }
    function loop() {
      cancelAnimationFrame(raf); last = performance.now();
      const step = (now) => { const dt = Math.min(0.05, (now - last) / 1000); last = now; update(dt); draw();
        if (mode === "run" || mode === "caught" || (mode === "win" && parts.length) || fx.length) raf = requestAnimationFrame(step); else raf = null; };
      raf = requestAnimationFrame(step);
    }
    function pause() {
      if ((mode === "run" || mode === "caught") && !paused) {
        if (mode === "caught") { spawn(ck); }   // caught right as you leave: come back at the checkpoint
        paused = true; mode = "paused"; cancelAnimationFrame(raf); raf = null; draw();
        overlay(`<p class="ice-big">Paused</p><button type="button" class="lot-btn lot-main" data-act="resume">▶ Resume</button>`, "soft"); ctrl();
      }
    }
    function resume() { if (paused) { paused = false; mode = "run"; overlay(null); fs.enter(); fit(); loop(); ctrl(); } }
    function stats() { el.querySelector("#ice-stats").innerHTML = `⭐ Best score <b>${st.best}</b> · 🏠 Made it home <b>${st.wins}</b>× · Furthest level <b>${st.levelMax}</b>`; }
    function ctrl() {
      const p = el.querySelector("#ice-pause");
      p.innerHTML = paused ? '<span aria-hidden="true">▶</span><span class="ice-lbl"> Resume</span>' : '<span aria-hidden="true">⏸</span><span class="ice-lbl"> Pause</span>';
      p.setAttribute("aria-label", paused ? "Resume" : "Pause");
      const s = el.querySelector("#ice-sound");
      s.innerHTML = `<span aria-hidden="true">${st.muted ? "🔇" : "🔊"}</span><span class="ice-lbl"> Sound</span>`; s.setAttribute("aria-label", st.muted ? "Sound is off" : "Sound is on"); s.setAttribute("aria-pressed", st.muted ? "false" : "true");
    }
    // ---- input: tap / click the game, the Jump button, Space / ↑ / W
    cv.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); });
    cv.addEventListener("pointerup", release);
    const jb = el.querySelector("#ice-jump");
    jb.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); }); jb.addEventListener("pointerup", release);
    jb.addEventListener("click", (e) => { if (e.detail === 0) jump(); });   // keyboard activation
    el.addEventListener("click", (e) => { const b = e.target.closest("[data-act]"); if (!b) return; const a = b.dataset.act; audio();
      if (a === "start" || a === "cont" || a === "again") { try { root.dispatchEvent(new CustomEvent("chisme-game-play", { detail: "icebebe" })); } catch (e) {} }   // v42: anonymous counts
      if (a === "start") startLevel(1); else if (a === "cont") { ckScore = 0; startLevel(st.levelMax); } else if (a === "next") startLevel(level + 1, true); else if (a === "again") startLevel(1); else if (a === "resume") resume(); });
    el.querySelector("#ice-pause").onclick = () => (paused ? resume() : pause());
    el.querySelector("#ice-restart").onclick = () => { paused = false; ckScore = 0; startLevel(level); ctrl(); };
    el.querySelector("#ice-sound").onclick = () => { st.muted = !st.muted; save(st); ctrl(); if (!st.muted) SFX.coin(); };
    const onKey = (e) => {
      if (!el.isConnected || !el.closest(".view.active") || document.querySelector("dialog[open]") || e.target.closest && e.target.closest("input, textarea, select, dialog")) return;   // only while Juegitos is showing
      if (e.code === "Space" || e.key === "ArrowUp" || e.key === "w" || e.key === "W") { if (e.target.closest && e.target.closest("button") && e.code === "Space" && e.target !== jb) return; e.preventDefault(); if (!e.repeat) jump(); }
      else if (e.key === "p" || e.key === "P") paused ? resume() : pause();
    };
    const onKeyUp = (e) => { if (e.code === "Space" || e.key === "ArrowUp") release(); };
    document.addEventListener("keydown", onKey); document.addEventListener("keyup", onKeyUp);
    stats(); ctrl(); title();
    return {
      pause, resume, jump,
      fs, exitFullscreen: (quiet) => fs.exit(quiet),
      destroy() { fs.exit(true); cancelAnimationFrame(raf); document.removeEventListener("keydown", onKey); document.removeEventListener("keyup", onKeyUp); },
      get state() { return { caughtMsg, msg, mode, level, x: hero.x, y: hero.y, ground: hero.ground, score, ck, best: st.best, muted: st.muted, boost: hero.boost, shield: hero.shield, levelMax: st.levelMax, parallax: !reduced(), overlay: ov.textContent.trim(),
        fullscreen: fs.on, W, H, fx: fx.length, fxMade }; },
      // test hooks: jump to a spot in a level (as if you'd run there)
      warp(n, x) { if (n !== level || mode === "title" || mode === "win" || mode === "clear") startLevel(n, true); hero.x = x; camX = x - HERO_X; for (const e of ents) if (e.t === "flag" && e.x <= x) { e.done = true; ck = CHECKS.indexOf(e.x); } ents = ents.filter((e) => !["agent", "cone", "suv", "crate"].includes(e.t) || e.x > x + 30 || e.x < x - 40); },
      ents: () => ents.map((e) => ({ t: e.t, x: e.x, st: e.st })),
    };
  }

  const game = { id: "icebebe", name: "Ice Ice Bebé", emoji: "🤠", blurb: "8-bit runner: get home to Mom's in 5 levels.", mount };
  const api = { KEY, LEVELS, END, CHECKS, W, H0, buildLevel, load, save, reset, game };
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.ChismeIceBebe = api; if (root.ChismeJuegos) root.ChismeJuegos.GAMES.push(game); }
})(typeof window !== "undefined" ? window : this);
