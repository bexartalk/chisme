/* Chisme · Juegos game 2: "The Juan That Got Away" (v44; first called "Juan's Long Day"), a side-scrolling runner with smooth vector art on a canvas
   (paths, gradients and anti-aliasing, drawn at the phone's devicePixelRatio so it stays crisp; no image files, no requests).
   v47 story: it's FRIDAY, and Juan grinds through his workday to get to Noche Caliente for beers with the crew. 6 levels:
   Hon Dipo (v47, was Home Dehole; our own parody hardware store. v49.15: repainted as a Southside ferretería with turquoise +
   pink trim, papel picado and a hand-painted arched sign, no orange square, plus a DJ out front on a row of tool chests) → La Chamba (v47: downtown San Antonio, the most ICE agents and
   background SUVs; it ends at a construction site with a cement mixer, a yellow excavator + loader, fencing, cones and a blue
   "COMING SOON Gualmart" parody sign) → Don Pedroes (a Southside Mexican restaurant: cream stucco, red tile roofs, the tall pole sign with the
   specials) → O'Reillees (a green-and-white parody auto-parts store, no real logo) → Juan's Casa (quitting time: wash up,
   boots on) → Noche Caliente, the cantina. Work levels: neon safety-green shirt with orange/silver hi-vis stripes and a
   white hard hat. Level 5: a beige cowboy hat, pearl-snap western shirt, jeans and boots, and floating cold ones to jump
   for (each one gives a little health).
   Nonviolent, neutral, funny obstacles: traffic cones, potholes, runaway shopping carts, a loose chancla, a barking
   chihuahua, sprinklers; pallets and tire stacks to hop onto. Bumping one costs a bit of the health bar; at zero Juan's
   worn out ("¡Ay no!" / "¡Híjole!" / "¡Ándale, otra vez!") and goes back to the last 🚩 checkpoint. ☕ coffee = speed
   boost, breakfast taco = +health, conchas = points. Parallax: the San Antonio skyline far back (Tower of the Americas,
   Tower Life, Frost Tower …), SE Military Dr storefronts in the middle (taquería, raspas, tire shop, pawn shop,
   lavandería, a grocery, the Brooks water tower and arch, palms, power lines), the road up front (v46: now and then a
   black ICE SUV drives by or sits parked in the far lane, scenery only; parked-only and rare with reduce motion). Static layers are
   pre-rendered once per level into tiles, so a frame is a few image blits + the moving art (smooth on iPhone Safari).
   Score + best in localStorage "chisme-juegos-juan". Reduce motion: no parallax, shake, particles or confetti, a bit slower.
   UI chrome (HUD, overlays, badge) uses the Fiesta palette only: turquoise, pink, black, silver, white; no yellow.
   v46: the ICE agents from the old Ice Ice Bebé are back, redrawn in this smooth style (cartoon agents in navy "ICE"
   windbreakers, caps and sunglasses; no weapons, nobody gets hurt). Agents patrol the sidewalk (hop over them: "¡Fuera!",
   they look up "?"); dark unmarked SUVs are parked along the way (hop onto the roof) and, once Juan runs past one, an
   agent hops out and chases him ("¡Vámonos, amigo!") until he's out of breath ("¡Fuera!", Juan got away). Getting
   caught is a big "¡Ay no!" and back to the last 🚩. Old slapstick kept: agents trip over traffic cones (cap rolls off,
   "!?"), and the 🩴 flip-flops power-up is a shield: the next agent who reaches Juan just gets dizzy (stars). */
(function (root) {
  "use strict";
  // v49.11: anything that isn't our own fixed text goes into innerHTML only through num() (numbers) or escH() (text)
  const num = (n) => (Number.isFinite(+n) ? +n : 0).toLocaleString("en-US");
  const KEY = "chisme-juegos-juan";
  const VW = 360, ROADH = 176, END = 6000, CHECKS = [0, 2000, 4000], HERO_X = 84, TILE = 500, CAM_END = END - HERO_X - 150;   // the camera stops 150 before the end: the stop's building fills the screen and Juan runs up to its door
  const GRAV = 1750, JUMP = -700, JUMP2 = -480, HP = 100, HERO_W = 32, HERO_H = 88;   // v49.7: a higher jump (was −620 / −540)
  const HANG_V = 170, HANG = 0.5, REL_V = -400, REL = 0.82;   // v49.7: half gravity near the top (a slower hang, longer air time); a short tap trims the jump only a little (was ×0.55, which made a phone tap too low to clear an agent)
  const fall = (vy, dt) => vy + (Math.abs(vy) < HANG_V ? GRAV * HANG : GRAV) * dt;   // one physics step of vertical speed (the game and the tests use this)
  const trim = (vy) => (vy < REL_V ? vy * REL : vy);   // what letting go of the jump does   // v49.5: Juan drawn 1.5× (JS); the box is the body (no hat), a bit forgiving at the sides
  const AG_TALL = 1.18, AGAP = 380, AMIN = 400, AWAY = 0.25;   // v49.7: agents are never back to back: a partner 380 on (was 130), and any agent at least 400 after the last one
  const JS = 1.5, ARCH_X = 196;   // ARCH_X: where Playa Neón's neon arch stands (Juan starts at 140 and runs under it)
  // v49.5 skins: classic is the default; the rest unlock for anyone who has ever made the Top 10 (original parodies, no real names or logos)
  const JSKINS = [["classic", "Classic Juan"], ["jefe", "El Jefe Presidente"], ["raspa", "Robo-Raspa"], ["payaso", "Payaso de la Feria"], ["ufo", "Juan UFO"], ["astro", "Astro Juan"], ["lowrider", "El Lowrider"], ["largo", "Juan Largo"], ["mariachi", "Mariachi Neón"], ["cowboy", "Cocaine Cowboy"]];
  // v49.12: six skins redesigned + renamed (each keeps its slot and gets a new jump); a phone that saved an old one keeps wearing its new version
  const SKIN_RENAMED = { hierro: "raspa", joker: "payaso", master: "astro", armadura: "lowrider", juanby: "largo", vice: "mariachi" };
  const SANS = '"Avenir Next Condensed","Arial Narrow","Roboto Condensed","Helvetica Neue",Arial,sans-serif';
  const UI = '-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif';
  const WEST = 'Rockwell,"American Typewriter",Georgia,"Times New Roman",serif';
  const LEVELS = [
    { name: "Hon Dipo", speed: 188, time: "morning", outfit: "work", hint: "Friday shift, 7 a.m. Load up the supplies and dodge the runaway carts and the ICE agents. Let's go!", done: "Supplies loaded. Nice work!", d: 1, seed: 1,
      mix: { cone: 3, cart: 3, pothole: 2, pallet: 2, agent: 2, suv: 1 }, power: [[900, "coffee"], [2300, "flipflops"], [2700, "taco"], [4400, "coffee"]] },
    { name: "La Chamba", speed: 194, time: "morning", outfit: "work", d: "site", seed: 23, diff: 3, city: true,   // v47: downtown, the most ICE agents, the SUVs out in force
      hint: "Supplies in the truck, now downtown to La Chamba. ICE agents on every corner, so hop 'em! Go, go, go!", done: "Clocked in! Gualmart won't build itself.",
      mix: { agent: 8, cone: 4, pothole: 3, cart: 2, pallet: 2, suv: 2 }, power: [[1100, "coffee"], [2300, "flipflops"], [2800, "taco"], [4500, "coffee"]] },
    { name: "Don Pedroes", speed: 198, time: "noon", outfit: "work", d: 2, seed: 2, hint: "Lunch break! The alambre plate is calling, and the weekend's almost here.", done: "Belly full. Back to work!",
      mix: { pothole: 3, chancla: 2, chihuahua: 2, cone: 2, agent: 2, suv: 1 }, power: [[1250, "taco"], [2350, "flipflops"], [3100, "coffee"], [4700, "taco"]] },
    { name: "O'Reillees", speed: 208, time: "afternoon", outfit: "work", d: 3, seed: 3, hint: "The work truck needs a part before quitting time. Mind the potholes. Hurry!", done: "Part in hand. Almost quitting time!",
      mix: { pothole: 3, tires: 2, cone: 2, cart: 1, chihuahua: 2, agent: 3, suv: 1 }, power: [[1000, "coffee"], [2250, "flipflops"], [2600, "taco"], [4500, "coffee"]] },
    { name: "Juan's Casa", speed: 216, time: "sunset", outfit: "work", d: 4, seed: 4, hint: "Quitting time! Home to wash up, then boots and cowboy hat on.", done: "Boots on, hat on. It's Friday!",
      mix: { sprinkler: 3, chihuahua: 2, chancla: 2, pothole: 2, cone: 1, agent: 3, suv: 2 }, power: [[1300, "taco"], [2300, "flipflops"], [3000, "coffee"], [4600, "taco"]] },
    { name: "Noche Caliente", speed: 222, time: "night", outfit: "western", d: 5, seed: 5, hint: "It's Friday! The crew's saving him a seat. Jump for the cold ones on the way!",
      done: "Cold ones with the crew! Next stop: a vacation at Playa Neón. Woo-hoo!",
      mix: { pothole: 2, cone: 2, chihuahua: 2, chancla: 2, sprinkler: 1, agent: 3, suv: 2 }, power: [[1500, "coffee"], [2300, "flipflops"], [3300, "taco"]], beers: true },
    { name: "Playa Neón", speed: 226, time: "neon", outfit: "western", d: 7, seed: 78, diff: 5, beach: true,   // v49.5: the celebration level, an original neon beach city at sunset
      hint: "Vacation! Juan runs from his hotel to the beach at sunset, with ICE agents and cartoon gangsters on his tail. Martinis and tacos keep him going.", done: "Beach time!", martinis: true,
      mix: { lowcar: 2, sportscar: 2, cone: 3, pothole: 3, chihuahua: 1, agent: 2, suv: 1 }, power: [[1100, "coffee"], [2300, "flipflops"], [3000, "taco"], [4600, "taco"]] },
  ];
  const DEST_H = [210, 256, 312, 150, 150, 232, 240];   // how tall each stop's building is (units), so a short screen can shrink it to fit under the HUD
  const DIM = { feria: [24, 26], cone: [24, 32], pothole: [56, 8], cart: [52, 46], chancla: [30, 14], chihuahua: [36, 28], sprinkler: [18, 12], pallet: [70, 38], tires: [46, 48],
    concha: [22, 16], beer: [24, 32], coffee: [22, 28], taco: [32, 20], flipflops: [30, 18], flag: [10, 70], agent: [30, 64], chaser: [30, 64], suv: [124, 54], lowcar: [92, 30], sportscar: [84, 26] };
  const HAZ = { cone: [10, "Bonk! A cone"], pothole: [15, "¡Híjole! A pothole"], cart: [20, "Runaway cart!"], chancla: [10, "¡La chancla!"], chihuahua: [15, "Yap yap yap!"], sprinkler: [8, "Soaked!"] };
  const HAZARDS = Object.keys(HAZ), SOLID = ["pallet", "tires", "suv", "lowcar", "sportscar"], ICE = ["agent", "suv", "chaser"];   // v46: the ICE agents (not in HAZ: they don't cost health, they catch Juan)
  const OOPS = ["¡Ay no!", "¡Híjole!", "¡Ándale, otra vez!"];
  const FUERA = "¡Fuera!", VAMONOS = "¡Vámonos, amigo!";   // v46: the old Ice Ice Bebé lines (kept in Spanish on purpose)
  // v47: caught by ICE → one of these, picked at random, never the same one twice in a row (the user's picks; the original "¡Ay no!" stays in)
  const CAUGHT = ["¡Ay no!", "¡Ay cabrón!", "¡Chingao!", "¡Pinche ICE!", "¡Ay, vengo mamá!"];
  let lastCaught = "";   // module-wide, so even a fresh game doesn't open with the last one again
  function pickCaught(prev = lastCaught, rnd = Math.random) {
    const pool = CAUGHT.filter((l) => l !== prev);
    return (lastCaught = pool[Math.min(pool.length - 1, Math.floor(rnd() * pool.length))]);
  }
  const SKINS = [["#e3b896", "#c3906c"], ["#c68a5e", "#a5683f"], ["#8d5a3b", "#6e4229"], ["#f2cdb0", "#d5a585"], ["#a8724a", "#87552f"]];
  const SKY = {
    morning: { sky: ["#3f9fe6", "#8fd0f7", "#d9f1ff"], far: ["#8eb3cc", "#b5d0e0"], tint: null, road: 0, sun: "sun" },
    noon: { sky: ["#1f7fd8", "#5fb2f0", "#bfe4ff"], far: ["#86abc6", "#aac8dc"], tint: null, road: 0, sun: "sun" },
    afternoon: { sky: ["#3a8fd6", "#8cc4ea", "#ffd2c2"], far: ["#9aa9c4", "#c4bfd0"], tint: "rgba(255,150,110,.10)", road: 0.05, sun: "low" },
    sunset: { sky: ["#3b2e7a", "#c2548a", "#ff8a5c"], far: ["#6a4a7e", "#9a5a7e"], tint: "rgba(70,30,90,.30)", road: 0.22, sun: "set" },
    night: { sky: ["#070a24", "#1c1648", "#46225e"], far: ["#1e1c46", "#2c2456"], tint: "rgba(8,8,36,.58)", road: 0.45, sun: "moon" },
    neon: { sky: ["#c2306e", "#ff5e8a", "#ff8a5c", "#ffc06a"], far: ["#a98fd8", "#f3a6c8"], tint: null, road: 0.25, sun: "synth", beach: true },   // v49.5 Playa Neón
  };
  const mod = (a, n) => ((a % n) + n) % n;
  function rng(seed) { let s = seed >>> 0 || 1; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }

  // A level's layout is the same every time (seeded by the level number), so a checkpoint restarts the same course.
  function buildLevel(n) {
    const L = LEVELS[n - 1], q = L.diff || L.seed || n, r = rng(1000 + (L.seed || n) * 7919), ents = [], bag = [];
    for (const [k, w] of Object.entries(L.mix)) for (let i = 0; i < w; i++) bag.push(k);
    const clearOf = (x) => CHECKS.some((c) => c && x + 140 > c - 100 && x - 80 < c + 170);   // nothing right at a 🚩
    const add = (t, x, y, extra) => { const [w, h] = DIM[t]; const e = Object.assign({ t, x, y: y == null ? -h : y, w, h }, extra || {}); ents.push(e); return e; };
    for (const [px, kind] of L.power) add(kind, px, -120);
    const deal = [];   // v46: deal from a shuffled bag (refilled when it runs out), so every level gets its share of each kind (agents + an SUV too)
    const next = () => { if (!deal.length) { const d = bag.slice(); for (let i = d.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [d[i], d[j]] = [d[j], d[i]]; } deal.push(...d); } return deal.shift(); };
    let x = 620, ag = 0, lastA = -1e9;   // ag: Playa Neón's agents alternate with cartoon gangsters
    while (x < END - 420) {
      x += 250 - q * 8 + Math.floor(r() * 180);
      if (clearOf(x) || x > END - 460) continue;
      const k = next();
      if (k === "cart") add("cart", x, null, { vx: -75 });
      else if (k === "chihuahua") add("chihuahua", x, null, { vx: -80, home: x, ph: r() * 6 });
      else if (k === "chancla") add("chancla", x, null, { ph: r() * 6, home: x });
      else if (k === "sprinkler") add("sprinkler", x, null, { ph: r() * 2.4 });
      else if (k === "agent") {   // a patrolling agent; sometimes a cone he'll trip over, sometimes a partner a bit further on
        if (x - lastA < AMIN) { x = lastA + AMIN; if (clearOf(x) || x > END - 460) continue; }   // v49.7: never back to back: room to land and jump again
        add("agent", x, null, { vx: -(34 + q * 4), home: x, st: "walk", tt: 0, ph: r() * 6, sk: Math.floor(r() * SKINS.length), st2: r() < 0.5, gang: !!L.beach && ag++ % 2 === 0 }); lastA = x;
        if (r() < 0.3) add("cone", x - 70);
        if (q >= 3 && r() < (L.city ? 0.2 : 0.1) && x + AGAP < END - 460) { x += AGAP; add("agent", x, null, { vx: -(34 + q * 4), home: x, st: "walk", tt: 0, ph: r() * 6, sk: Math.floor(r() * SKINS.length), st2: r() < 0.5, gang: !!L.beach && ag++ % 2 === 0 }); lastA = x; }
      }
      else if (k === "suv") add("suv", x, null, { sk: Math.floor(r() * SKINS.length), night: L.time === "night" });
      else add(k, x);
      if (SOLID.includes(k)) for (let i = 0; i < 2; i++) add("concha", x + 10 + i * 28, -DIM[k][1] - 44);
      else if (!L.beers && r() < 0.55) for (let i = 0; i < 3; i++) add("concha", x - 28 + i * 34, -104 - (i === 1 ? 26 : 0));
    }
    if (L.beach) for (let bx = 980; bx < END - 420; bx += 640) if (!CHECKS.some((c) => c && Math.abs(bx - c) < 90)) add("feria", bx, -150);   // v49.6: money bags (la feria), +25 each
    if (L.martinis) for (let bx = 760; bx < END - 420; bx += 420 + Math.floor(r() * 160)) if (!CHECKS.some((c) => c && Math.abs(bx - c) < 70)) add("beer", bx, -110 - Math.floor(r() * 50), { mt: 1 });   // v49.5 Playa Neón: martinis (+8 health, like a cold one)
    if (L.beers) { for (let bx = 680; bx < END - 420; bx += 210 + Math.floor(r() * 120)) if (!CHECKS.some((c) => c && Math.abs(bx - c) < 70)) add("beer", bx, -100 - Math.floor(r() * 70));
      [[END - 150, -104], [END - 112, -132], [END - 74, -144], [END - 36, -128]].forEach(([bx, by]) => add("beer", bx, by)); }   // a last arc of cold ones by the cantina door
    for (const c of CHECKS.slice(1)) add("flag", c, -70);
    return ents;
  }
  const hit = (a, b, pad = 3) => a.x + pad < b.x + b.w && a.x + a.w - pad > b.x && a.y + pad < b.y + b.h && a.y + a.h - pad > b.y;
  function load() { const d = { best: 0, muted: false, levelMax: 1, wins: 0, beers: 0 }; let o = {}; try { o = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) {}
    Object.assign(d, o); if (SKIN_RENAMED[d.skin]) d.skin = SKIN_RENAMED[d.skin]; if (!o.v6 && d.levelMax >= 2) d.levelMax = Math.min(6, d.levelMax + 1); d.v6 = 1; return d; }   // v47: a save from the 5-stop game: the new level 2 shifts the rest by one
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
  const reset = () => { try { localStorage.removeItem(KEY); } catch (e) {} };

  // ================= drawing helpers (any 2D context, in game units) =================
  function rr(c, x, y, w, h, r) { r = Math.max(0, Math.min(r, w / 2, h / 2)); c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
  function lin(c, x0, y0, x1, y1, cols) { const g = c.createLinearGradient(x0, y0, x1, y1); cols.forEach((col, i) => g.addColorStop(i / Math.max(1, cols.length - 1), col)); return g; }
  function box(c, fill, x, y, w, h, r) { c.fillStyle = fill; if (r) { rr(c, x, y, w, h, r); c.fill(); } else c.fillRect(x, y, w, h); }
  function ell(c, fill, x, y, rx, ry, rot) { c.fillStyle = fill; c.beginPath(); c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), rot || 0, 0, Math.PI * 2); c.fill(); }
  function line(c, col, w, pts, cap) { c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap || "round"; c.lineJoin = "round"; c.beginPath(); c.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) c.lineTo(pts[i], pts[i + 1]); c.stroke(); }
  function poly(c, fill, pts) { c.fillStyle = fill; c.beginPath(); c.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) c.lineTo(pts[i], pts[i + 1]); c.closePath(); c.fill(); }
  const sayText = (...a) => say(...a);
  function say(c, s, x, y, size, col, o = {}) {
    c.font = `${o.italic ? "italic " : ""}${o.weight || 800} ${size}px ${o.font || SANS}`;
    if (o.fit && o.max) { const w = c.measureText(s).width + (o.stroke ? o.sw || 3 : 0); if (w > o.max) { size = Math.max(12, Math.floor(size * o.max / w)); c.font = `${o.italic ? "italic " : ""}${o.weight || 800} ${size}px ${o.font || SANS}`; } } c.textAlign = o.align || "center"; c.textBaseline = "middle";
    if (o.glow) { c.shadowColor = o.glow; c.shadowBlur = o.blur || 8; }
    if (o.stroke) { c.lineWidth = o.sw || 3; c.strokeStyle = o.stroke; c.lineJoin = "round"; c.strokeText(s, x, y, o.max); }
    c.fillStyle = col; c.fillText(s, x, y, o.max);
    if (o.glow) { c.shadowBlur = 0; c.shadowColor = "transparent"; }
  }
  function palm(c, x, h, lean = 0.12, s = 1) {   // a Texas palm: a curved ringed trunk and a crown of drooping fronds
    const tx = x + h * lean, ty = -h;
    c.fillStyle = lin(c, x - 4, 0, x + 4, 0, ["#6b4a2e", "#9a7048", "#6b4a2e"]);
    c.beginPath(); c.moveTo(x - 4 * s, 0); c.quadraticCurveTo(x - 3 * s + h * lean * 0.2, -h * 0.55, tx - 2 * s, ty); c.lineTo(tx + 2 * s, ty); c.quadraticCurveTo(x + 3 * s + h * lean * 0.2, -h * 0.55, x + 4 * s, 0); c.closePath(); c.fill();
    c.strokeStyle = "rgba(60,38,20,.45)"; c.lineWidth = 0.8;
    for (let k = 1; k < 14; k++) { const f = k / 14, px = x + (tx - x) * f * f * 0.9 + h * lean * 0.1 * f, py = -h * f; c.beginPath(); c.moveTo(px - 3.5 * s, py); c.lineTo(px + 3.5 * s, py + 1); c.stroke(); }
    const fronds = [[-2.7, 1], [-2.2, 1.1], [-1.6, 0.9], [-0.9, 0.8], [-0.2, 0.75], [0.5, 0.8], [1.2, 0.95], [1.9, 1.1], [2.5, 1]];
    for (const [a, len] of fronds) {
      const L = 30 * s * len, ex = tx + Math.sin(a) * L, ey = ty - Math.cos(a) * L * 0.55 + L * 0.35;
      const mx = tx + Math.sin(a) * L * 0.55, my = ty - Math.cos(a) * L * 0.6 - 6 * s;
      c.fillStyle = lin(c, tx, ty - 10, ex, ey, ["#3f9a52", "#2b7a3f", "#1f5e30"]);
      c.beginPath(); c.moveTo(tx, ty); c.quadraticCurveTo(mx, my - 4 * s, ex, ey); c.quadraticCurveTo(mx, my + 3 * s, tx, ty + 2); c.fill();
    }
    ell(c, "#5a3d22", tx, ty + 1, 3.2 * s, 2.4 * s);
  }
  function shrub(c, x, w, h, col = "#2f8a46") {   // a fan palm / sago shrub
    for (let i = 0; i < 9; i++) { const a = -1.3 + i * 0.32, L = h * (0.75 + 0.25 * Math.sin(i * 1.7));
      c.fillStyle = i % 2 ? col : "#256f39"; c.beginPath(); c.moveTo(x - 2, 0); c.quadraticCurveTo(x + Math.sin(a) * L * 0.5 - 3, -Math.cos(a) * L * 0.7, x + Math.sin(a) * w * 0.6, -Math.cos(a) * L); c.quadraticCurveTo(x + Math.sin(a) * L * 0.5 + 3, -Math.cos(a) * L * 0.6, x + 2, 0); c.fill(); }
  }
  function pole(c, x, h) {   // a wooden power pole with a crossarm and insulators; returns the 3 wire points
    box(c, lin(c, x - 3, 0, x + 3, 0, ["#5b4430", "#86664a", "#5b4430"]), x - 2.5, -h, 5, h);
    box(c, "#5b4430", x - 22, -h + 8, 44, 4); box(c, "#5b4430", x - 2, -h + 22, 4, 0);
    for (const dx of [-19, 0, 19]) { box(c, "#cfd8de", dx + x - 1.5, -h + 3, 3, 5, 1); }
    ell(c, "#8a939c", x + 6, -h + 30, 4, 5); box(c, "#6c757d", x + 2, -h + 34, 8, 3);   // a transformer can
    return [[x - 19, -h + 4], [x, -h + 4], [x + 19, -h + 4]];
  }
  function wires(c, a, b, col) { c.strokeStyle = col; c.lineWidth = 0.9; for (let i = 0; i < a.length; i++) { c.beginPath(); c.moveTo(a[i][0], a[i][1]); c.quadraticCurveTo((a[i][0] + b[i][0]) / 2, Math.max(a[i][1], b[i][1]) + 14, b[i][0], b[i][1]); c.stroke(); } }
  function glass(c, x, y, w, h, lit) { box(c, lit ? lin(c, 0, y, 0, y + h, ["#ffd9a0", "#ffb46a"]) : lin(c, x, y, x + w, y + h, ["#bfe6f7", "#7fb6d6", "#a9d4ea"]), x, y, w, h); if (!lit) { c.fillStyle = "rgba(255,255,255,.45)"; c.beginPath(); c.moveTo(x + w * 0.15, y + h); c.lineTo(x + w * 0.45, y); c.lineTo(x + w * 0.6, y); c.lineTo(x + w * 0.3, y + h); c.fill(); } }
  function awning(c, x, y, w, cols) { const n = Math.max(2, Math.round(w / 12)), sw = w / n; for (let i = 0; i < n; i++) { poly(c, cols[i % cols.length], [x + i * sw, y, x + (i + 1) * sw, y, x + (i + 1) * sw + 3, y + 14, x + i * sw + 3, y + 14]); c.fillStyle = cols[i % cols.length]; c.beginPath(); c.arc(x + i * sw + sw / 2 + 3, y + 14, sw / 2, 0, Math.PI); c.fill(); } }
  function stucco(c, x, y, w, h, top, bot) { box(c, lin(c, 0, y, 0, y + h, [top, bot]), x, y, w, h); }
  function tire(c, x, y, r) { ell(c, "#1d1f24", x, y, r, r * 0.42); ell(c, "#3a3d44", x, y, r * 0.58, r * 0.22); ell(c, "#14161a", x, y, r * 0.34, r * 0.13); }

  // ---- the far layer: the San Antonio skyline (period 1400). Silhouettes in the haze color, little lit windows at night.
  function farLayer(c, P, night) {
    if (P.beach) return beachFar(c, P);
    const [hz, hz2] = P.far, sil = lin(c, 0, -360, 0, 0, [hz, hz2]), win = night ? "rgba(255,214,150,.85)" : "rgba(255,255,255,.22)";
    const r = rng(77), bldg = (x, w, h, top) => { box(c, sil, x, -h, w, h); if (top) top(x, w, h);
      c.fillStyle = win; for (let yy = -h + 8; yy < -12; yy += 9) for (let xx = x + 3; xx < x + w - 3; xx += 6) if (!night || r() < 0.35) c.fillRect(xx, yy, 2.2, 3.4); };
    c.fillStyle = sil;   // low hills + trees along the base
    c.beginPath(); c.moveTo(0, 0); for (let x = 0; x <= 1400; x += 20) c.lineTo(x, -18 - 8 * Math.sin(x * 0.011) - 5 * Math.sin(x * 0.037)); c.lineTo(1400, 0); c.fill();
    bldg(130, 34, 120); bldg(176, 26, 90); bldg(880, 40, 150); bldg(930, 30, 96);
    // Tower Life Building: an octagonal brick tower with a stepped pyramid roof and a lantern
    bldg(300, 44, 210, (x, w, h) => { poly(c, sil, [x - 2, -h, x + w + 2, -h, x + w - 6, -h - 22, x + 6, -h - 22]); poly(c, sil, [x + 8, -h - 22, x + w - 8, -h - 22, x + w / 2 + 3, -h - 50, x + w / 2 - 3, -h - 50]); box(c, sil, x + w / 2 - 1, -h - 62, 2, 14); box(c, sil, x - 4, -h + 30, w + 8, 4); });
    // Weston Centre: a tall tower with a curved, stepped crown
    bldg(368, 40, 250, (x, w, h) => { c.fillStyle = sil; c.beginPath(); c.moveTo(x, -h); c.quadraticCurveTo(x + w / 2, -h - 34, x + w, -h); c.fill(); });
    bldg(414, 30, 160);
    // Frost Tower: modern glass, a sliced/tilted crown
    bldg(452, 38, 236, (x, w, h) => { poly(c, sil, [x, -h, x + w, -h, x + w, -h - 40, x + 6, -h - 8]); box(c, sil, x + w - 3, -h - 58, 2, 18); });
    bldg(498, 52, 140); bldg(556, 28, 180, (x, w, h) => poly(c, sil, [x, -h, x + w, -h, x + w / 2, -h - 26]));   // a pointed-top hotel
    // San Fernando–style cathedral towers + a mission dome
    box(c, sil, 600, -96, 60, 96); box(c, sil, 604, -140, 14, 44); box(c, sil, 642, -140, 14, 44); poly(c, sil, [602, -140, 620, -140, 611, -158]); poly(c, sil, [640, -140, 658, -140, 649, -158]);
    c.fillStyle = sil; c.beginPath(); c.arc(690, -84, 22, Math.PI, 0); c.fill(); box(c, sil, 668, -84, 44, 84); box(c, sil, 689, -114, 2, 10);
    bldg(730, 36, 130); bldg(772, 30, 104);
    // Tower of the Americas: a tall tapered shaft with the "top hat" observation pod and a mast
    const tx = 236, th = 290;
    poly(c, sil, [tx - 9, 0, tx + 9, 0, tx + 5.5, -th + 40, tx - 5.5, -th + 40]);
    poly(c, sil, [tx - 6, -th + 40, tx + 6, -th + 40, tx + 22, -th + 26, tx - 22, -th + 26]);
    box(c, sil, tx - 24, -th + 4, 48, 23, 4); box(c, sil, tx - 20, -th - 4, 40, 9, 3); box(c, sil, tx - 1.5, -th - 48, 3, 46);
    c.fillStyle = night ? "rgba(255,200,140,.9)" : "rgba(255,255,255,.3)"; for (let i = 0; i < 9; i++) c.fillRect(tx - 21 + i * 4.8, -th + 12, 2.6, 5);
    ell(c, "#ff4d5e", tx, -th - 49, 2, 2);
    bldg(940, 46, 96); bldg(1000, 30, 70); bldg(1080, 40, 110); bldg(1150, 60, 64); bldg(1240, 34, 88);
    // the Hemisfair dome / convention hall roof + far trees
    c.fillStyle = sil; c.beginPath(); c.ellipse(1320, -40, 46, 24, 0, Math.PI, 0); c.fill();
  }

  // ---- the mid layer: SE Military Dr (period 2000). Each storefront; signs and windows glow again at night ("lights" pass).
  function midLayer(c, P, night, pass) {
    const lit = pass === "lights", L = (fn) => { if (!lit) fn(false); else fn(true); };
    const sign = (x, y, w, h, bg, text, fg, o = {}) => { if (!lit) { box(c, "#1d1f26", x - 1.5, y - 1.5, w + 3, h + 3, 4); box(c, bg, x, y, w, h, 3); }
      if (!lit || night) say(c, text, x + w / 2, y + h / 2 + 0.5, o.size || h * 0.62, fg, { max: w - 6, font: o.font, italic: o.italic, weight: o.weight, glow: lit ? o.glow || fg : null, blur: 10 }); };
    const windows = (x, y, w, h, n) => { const gw = (w - (n + 1) * 4) / n; for (let i = 0; i < n; i++) { if (!lit) { box(c, "#2b2f38", x + 4 + i * (gw + 4) - 1, y - 1, gw + 2, h + 2); glass(c, x + 4 + i * (gw + 4), y, gw, h, false); } else if (night) { c.globalAlpha = 0.9; glass(c, x + 4 + i * (gw + 4), y, gw, h, true); c.globalAlpha = 1; } } };
    // power poles every 400 with sagging wires
    // taquería
    if (!lit) { stucco(c, 30, -122, 230, 122, "#ff9a62", "#f07848"); box(c, "#c9563a", 26, -128, 238, 8, 2); awning(c, 40, -72, 210, ["#00b8b0", "#ffffff"]); box(c, "#7a3b2a", 196, -54, 30, 54, 2); }
    sign(70, -114, 150, 30, "#111111", "TAQUERIA", "#ff8fbf", { size: 21, font: WEST });
    windows(40, -54, 150, 40, 3);
    if (!lit) { for (let i = 0; i < 16; i++) { const px = 34 + i * 14; poly(c, ["#ff3d8b", "#00b8b0", "#ff8a00", "#ffffff"][i % 4], [px, -84, px + 12, -84, px + 12, -78, px + 6, -74, px, -78]); } line(c, "#333", 0.8, [30, -84, 262, -84]); say(c, "TACOS · MENUDO · BARBACOA", 145, -92, 8, "#ffffff", { max: 180 }); }
    if (!lit) palm(c, 280, 186, 0.1);
    // raspa stand
    if (!lit) { stucco(c, 300, -70, 110, 70, "#ffffff", "#e3e8ee"); poly(c, "#ff3d8b", [292, -70, 418, -70, 406, -88, 304, -88]); box(c, "#3a3f4a", 318, -50, 74, 26, 2);
      for (let i = 0; i < 5; i++) { const cx = 326 + i * 14; poly(c, "#ffffff", [cx - 5, -32, cx + 5, -32, cx + 3, -24, cx - 3, -24]); ell(c, ["#ff3d8b", "#00b8b0", "#ff8a00", "#7a5cff", "#3ad07a"][i], cx, -34, 6, 4.5); } }
    sign(320, -84, 70, 12, "#ffffff", "RASPAS", "#ff3d8b", { size: 11 });
    // tire shop
    if (!lit) { box(c, lin(c, 0, -112, 0, 0, ["#c7ced6", "#9aa3ad"]), 440, -112, 220, 112); c.strokeStyle = "rgba(0,0,0,.12)"; c.lineWidth = 1; for (let x = 444; x < 660; x += 6) { c.beginPath(); c.moveTo(x, -112); c.lineTo(x, 0); c.stroke(); }
      box(c, "#22252c", 456, -68, 86, 68); box(c, "#3a3f4a", 456, -68, 86, 6); for (let k = 0; k < 4; k++) tire(c, 470 + k * 0, -6 - k * 9, 12); for (let k = 0; k < 3; k++) tire(c, 520, -6 - k * 9, 12);
      for (let k = 0; k < 5; k++) tire(c, 620, -6 - k * 9, 13); }
    sign(470, -104, 170, 28, "#ff3d8b", "TIRE SHOP · LLANTAS", "#ffffff", { size: 17 });
    windows(552, -64, 52, 34, 1);
    if (!lit) palm(c, 690, 168, -0.08);
    // pawn shop
    if (!lit) { box(c, lin(c, 0, -100, 0, 0, ["#a0522d", "#7d3f22"]), 720, -100, 170, 100); c.strokeStyle = "rgba(255,255,255,.12)"; c.lineWidth = 0.8;
      for (let y = -96; y < 0; y += 6) { c.beginPath(); c.moveTo(720, y); c.lineTo(890, y); c.stroke(); } box(c, "#3c2a20", 840, -50, 30, 50, 2);
      for (const bx of [744, 772, 800]) ell(c, lin(c, bx - 6, -96, bx + 6, -84, ["#e8edf2", "#8a939c"]), bx, -82, 6, 6); }
    sign(820, -100, 64, 26, "#111111", "PAWN", "#3ee8eb", { size: 19 });
    windows(728, -60, 104, 40, 2); if (!lit) { c.strokeStyle = "#2b2f38"; c.lineWidth = 1.4; for (let x = 734; x < 832; x += 7) { c.beginPath(); c.moveTo(x, -60); c.lineTo(x, -20); c.stroke(); } say(c, "GOLD · TOOLS · GUITARS", 805, -66, 7.5, "#ffffff", { max: 150 }); }
    // lavandería
    if (!lit) { stucco(c, 910, -96, 200, 96, "#8fd8e0", "#5fbcc8"); box(c, "#ffffff", 906, -100, 208, 6, 2); box(c, "#2a6f78", 1072, -52, 28, 52, 2); }
    sign(930, -92, 160, 24, "#ffffff", "LAVANDERIA", "#0f6d73", { size: 18 });
    windows(916, -60, 150, 44, 3);
    if (!lit) { for (let i = 0; i < 6; i++) { const wx = 932 + i * 22; ell(c, "#e8edf2", wx, -28, 8, 8); ell(c, "#4a5a6a", wx, -28, 5.5, 5.5); ell(c, "rgba(255,255,255,.5)", wx - 2, -30, 2, 1.4); } say(c, "WASH & FOLD", 990, -66, 8, "#0f6d73"); }
    if (!lit) palm(c, 1136, 196, 0.12);
    // a big grocery (H-E-B-ish feel, generic): white block, red sign band, the entrance canopy, carts
    if (!lit) { box(c, lin(c, 0, -140, 0, 0, ["#ffffff", "#e6e9ee"]), 1170, -140, 380, 140); box(c, "#d7262e", 1170, -140, 380, 12); box(c, "#d7262e", 1290, -84, 140, 10, 2);
      for (let x = 1180; x < 1545; x += 40) box(c, "rgba(0,0,0,.05)", x, -128, 2, 128); box(c, "#3a3f4a", 1305, -74, 110, 74); for (let k = 0; k < 4; k++) box(c, "#c9d0d8", 1188 + k * 12, -18, 10, 14, 2); }
    sign(1260, -124, 200, 32, "#ffffff", "SUPERMERCADO", "#d7262e", { size: 24, weight: 900 });
    windows(1310, -70, 100, 60, 3); windows(1440, -72, 96, 40, 2); windows(1180, -72, 100, 40, 2);
    // the Brooks water tower + the arch at the gate (a hint of Brooks City Base)
    if (!lit) { for (const lx of [1588, 1632]) box(c, "#9aa3ad", lx, -150, 4, 150); line(c, "#9aa3ad", 1.4, [1590, -40, 1634, -110, 1590, -110, 1634, -40]);
      c.fillStyle = lin(c, 1578, 0, 1646, 0, ["#cfd8de", "#ffffff", "#b9c2ca"]); rr(c, 1576, -208, 72, 60, 14); c.fill(); poly(c, "#b9c2ca", [1576, -196, 1648, -196, 1612, -224]); box(c, "#00b8b0", 1576, -170, 72, 7);
      say(c, "BROOKS", 1612, -186, 13, "#0f6d73", { weight: 900 });
      c.strokeStyle = lin(c, 1670, 0, 1800, 0, ["#8a939c", "#c9d0d8", "#8a939c"]); c.lineWidth = 7; c.beginPath(); c.moveTo(1672, 0); c.quadraticCurveTo(1736, -150, 1800, 0); c.stroke(); box(c, "#8a939c", 1690, -28, 92, 6, 2); }
    if (lit && night) ell(c, "rgba(255,80,94,.9)", 1612, -226, 2.2, 2.2);
    if (!lit) { palm(c, 1840, 178, -0.1); palm(c, 1900, 150, 0.14); shrub(c, 1960, 22, 26); }
    // power poles and wires (on top, every 400)
    if (!lit) { let prev = null; for (let x = 0; x <= 2000; x += 400) { const p = pole(c, x + 10, 210); if (prev) wires(c, prev, p, night ? "#3a3f55" : "#2b2f38"); prev = p; }
      box(c, "#0f7a3a", 818, -176, 56, 12, 2); say(c, "SE MILITARY DR", 846, -170, 8, "#ffffff", { max: 52, weight: 900 }); }
  }

  // ---- v47: the mid layer for La Chamba: downtown San Antonio (period 2000), office towers, limestone hotels, brick, the River Walk, a parking garage
  function cityLayer(c, P, night, pass) {
    if (pass === "lights") return;
    const grid = (x, y, w, h, cw, ch, gap, col) => { c.fillStyle = col; for (let yy = y; yy + ch <= y + h; yy += ch + gap) for (let xx = x; xx + cw <= x + w; xx += cw + gap) c.fillRect(xx, yy, cw, ch); };
    const tower = (x, w, h, top, bot, win) => { box(c, lin(c, 0, -h, 0, 0, [top, bot]), x, -h, w, h); grid(x + 6, -h + 10, w - 12, h - 40, 6, 9, 4, win); };
    const lamp = (x) => { line(c, "#2b2f38", 2.2, [x, 0, x, -64]); line(c, "#2b2f38", 2, [x, -64, x + 10, -68]); ell(c, "#e8edf2", x + 12, -67, 4, 2.6); };
    const banner = (x, col) => { box(c, col, x + 2, -58, 12, 22, 2); box(c, "#ffffff", x + 4, -50, 8, 2); };
    const tree = (x, s) => { box(c, "#6b4a2e", x - 2, -24 * s, 4, 24 * s); for (const [dx, dy, r] of [[0, -38, 16], [-11, -30, 12], [11, -30, 12]]) ell(c, "#4f8f3e", x + dx * s, dy * s, r * s, r * s * 0.9); ell(c, "rgba(255,255,255,.12)", x - 4 * s, -42 * s, 7 * s, 4 * s); };
    // a blue glass office tower
    tower(20, 170, 232, "#7fb3d6", "#4f7fa6", "rgba(255,255,255,.35)"); box(c, "#3b5f80", 20, -232, 170, 6); box(c, "#2b3f55", 70, -40, 70, 40); glass(c, 76, -36, 58, 36, false);
    // a limestone hotel with arched windows, a cornice and a blade sign
    box(c, lin(c, 0, -160, 0, 0, ["#efe2c8", "#d8c6a4"]), 210, -160, 180, 160); box(c, "#c9b48c", 204, -166, 192, 8, 2); box(c, "#c9b48c", 210, -60, 180, 5);
    for (let k = 0; k < 4; k++) for (let j = 0; j < 4; j++) { const wx = 226 + k * 42, wy = -148 + j * 28; box(c, "#5d6f84", wx, wy, 22, 18); c.fillStyle = "#5d6f84"; c.beginPath(); c.arc(wx + 11, wy, 11, Math.PI, 0); c.fill(); }
    box(c, "#7a1f2b", 270, -46, 60, 46, 3); glass(c, 276, -40, 48, 40, false); box(c, "#7a1f2b", 262, -54, 76, 8, 3);
    box(c, "#7a1f2b", 372, -150, 22, 84, 3); c.save(); c.translate(383, -108); c.rotate(-Math.PI / 2); say(c, "HOTEL", 0, 0, 13, "#ffffff", { weight: 900, max: 76 }); c.restore();
    // red brick with a fire escape and a café awning
    box(c, lin(c, 0, -122, 0, 0, ["#b5523b", "#8f3d2b"]), 410, -122, 150, 122); c.fillStyle = "rgba(255,255,255,.08)"; for (let y = -118; y < 0; y += 5) c.fillRect(410, y, 150, 1);
    for (let k = 0; k < 3; k++) for (let j = 0; j < 3; j++) box(c, "#2f3d4c", 424 + k * 46, -110 + j * 28, 26, 18);
    for (let j = 0; j < 3; j++) { line(c, "#22252c", 1.4, [418, -86 + j * 28, 548, -86 + j * 28]); for (let x = 420; x < 548; x += 8) line(c, "#22252c", 0.8, [x, -86 + j * 28, x, -94 + j * 28]); }
    for (let i = 0; i < 9; i++) poly(c, i % 2 ? "#ffffff" : "#00b8b0", [420 + i * 14, -40, 434 + i * 14, -40, 434 + i * 14, -30, 420 + i * 14, -30]); box(c, "#22252c", 420, -30, 126, 30); glass(c, 428, -26, 50, 26, false); say(c, "CAFÉ", 510, -16, 11, "#3ee8eb", { weight: 900 });
    // the River Walk: a stone wall with a railing, stairs going down, cypress trees and a little sign
    box(c, lin(c, 0, -26, 0, 0, ["#cdbb98", "#b09c78"]), 580, -26, 200, 26); for (let x = 584; x < 780; x += 14) line(c, "#3a3f4a", 1.2, [x, -26, x, -42]); line(c, "#3a3f4a", 2, [580, -42, 780, -42]);
    tree(610, 1.4); tree(700, 1.6); tree(760, 1.2); box(c, "#0f6d73", 640, -78, 70, 18, 3); say(c, "RIVER WALK", 675, -69, 9.5, "#ffffff", { weight: 900, max: 64 }); line(c, "#3a3f4a", 2, [675, -60, 675, -26]);
    // a tall tan tower with a stepped crown
    tower(800, 100, 214, "#d9c3a0", "#b39b78", "rgba(60,70,90,.55)"); poly(c, "#c4ab84", [800, -214, 900, -214, 884, -232, 816, -232]); box(c, "#c4ab84", 840, -248, 20, 16);
    // a parking garage with ribbon openings
    box(c, lin(c, 0, -112, 0, 0, ["#c9ced6", "#a3a9b1"]), 920, -112, 180, 112); for (let j = 0; j < 4; j++) box(c, "#3a3f4a", 928, -104 + j * 26, 164, 12);
    for (let j = 0; j < 4; j++) for (let k = 0; k < 4; k++) box(c, ["#ff3d8b", "#e8edf2", "#3ee8eb", "#7d848e"][(j + k) % 4], 940 + k * 38, -100 + j * 26, 18, 7, 2);
    box(c, "#111111", 1040, -60, 52, 22, 3); say(c, "PARK", 1066, -49, 12, "#3ee8eb", { weight: 900 });
    // a San Fernando–style limestone church front with a bell tower
    box(c, lin(c, 0, -120, 0, 0, ["#f0e4cc", "#d7c4a2"]), 1120, -120, 170, 120); box(c, lin(c, 0, -200, 0, -120, ["#f0e4cc", "#e0cfae"]), 1150, -200, 40, 80); poly(c, "#d7c4a2", [1146, -200, 1194, -200, 1170, -228]);
    c.fillStyle = "#6a5a48"; c.beginPath(); c.arc(1170, -170, 9, Math.PI, 0); c.fill(); box(c, "#6a5a48", 1161, -170, 18, 16); box(c, "#7a3b2a", 1220, -58, 34, 58, 3); c.fillStyle = "#7a3b2a"; c.beginPath(); c.arc(1237, -58, 17, Math.PI, 0); c.fill();
    c.fillStyle = "#5d6f84"; for (const x of [1136, 1270]) { c.beginPath(); c.arc(x + 8, -80, 8, Math.PI, 0); c.fill(); c.fillRect(x, -80, 16, 24); } ell(c, "#5d6f84", 1237, -96, 9, 9);
    // a dark glass tower and an office slab
    tower(1310, 120, 200, "#5a6b80", "#3a4658", "rgba(160,200,230,.45)"); tower(1440, 80, 150, "#a9b6c4", "#7f8c9a", "rgba(40,50,70,.45)");
    // a building going up: steel frame, a tower crane, a hint of where Juan's headed
    c.strokeStyle = "#7d848e"; c.lineWidth = 3; for (let x = 1540; x <= 1700; x += 40) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, -150); c.stroke(); } for (let y = -150; y < 0; y += 30) { c.beginPath(); c.moveTo(1540, y); c.lineTo(1700, y); c.stroke(); }
    line(c, "#ff8a00", 3, [1720, 0, 1720, -224]); line(c, "#ff8a00", 3, [1600, -220, 1790, -220]); line(c, "#ff8a00", 1.4, [1720, -232, 1600, -220]); line(c, "#3a3f4a", 1, [1640, -220, 1640, -170]); box(c, "#3a3f4a", 1634, -170, 12, 8);
    box(c, "#ff8a00", 1540, -18, 160, 18); for (let x = 1548; x < 1700; x += 18) line(c, "#ffffff", 3, [x, -2, x + 8, -16]);
    // lamps, banners and trees along the curb
    for (let x = 200; x < 2000; x += 260) { lamp(x); banner(x - 16, x % 520 ? "#ff3d8b" : "#00b8b0"); }
    tree(1830, 1.5); tree(1930, 1.3); box(c, lin(c, 0, -90, 0, 0, ["#efe2c8", "#d8c6a4"]), 1850, -90, 60, 90); grid(1856, -84, 48, 60, 8, 10, 5, "#5d6f84");
  }

  // ---- each stop's building (drawn once per level into a cache, 360 units wide, ground at y 0)
  // ================= v49.5 level 7 "Playa Neón": an original neon beach-city at sunset (made-up businesses, no real brands) =================
  function beachFar(c, P) {   // a pastel skyline across the bay: art-deco towers in clusters, the ocean shows between them
    const cols = [["#f6b8d2", "#d98ab4"], ["#a9e6ea", "#78c4cf"], ["#c9b6ef", "#9f8ad6"], ["#ffd2b8", "#f0a888"]];
    const tower = (x, w, h, k, cap) => { const [a, b] = cols[k % 4]; box(c, lin(c, 0, -h, 0, 0, [a, b]), x, -h, w, h, cap ? 0 : 3);
      if (cap === "round") ell(c, a, x + w / 2, -h, w / 2, w * 0.3); if (cap === "step") { box(c, a, x + 4, -h - 10, w - 8, 10); box(c, a, x + 9, -h - 18, w - 18, 8); }
      if (cap === "spire") poly(c, a, [x + w / 2 - 3, -h, x + w / 2, -h - 34, x + w / 2 + 3, -h]);
      c.fillStyle = "rgba(255,255,255,.35)"; for (let yy = -h + 10; yy < -8; yy += 12) c.fillRect(x + 3, yy, w - 6, 2); };
    for (const [x0, set] of [[60, [[0, 30, 120, 0, "step"], [34, 24, 86, 1], [62, 36, 160, 2, "spire"], [102, 26, 96, 3, "round"]]],
                             [520, [[0, 40, 140, 1, "round"], [44, 28, 104, 0], [76, 34, 190, 2, "step"], [114, 22, 80, 3]]],
                             [980, [[0, 26, 90, 2], [30, 38, 150, 3, "spire"], [72, 30, 118, 0, "round"], [106, 24, 70, 1]]]])
      for (const [dx, w, h, k, cap] of set) tower(x0 + dx, w, h, k, cap);
    c.fillStyle = "rgba(255,255,255,.18)"; for (let x = 0; x < 1400; x += 46) c.fillRect(x, -3, 22, 2);   // the shoreline glints
  }
  const PIPS = { 1: [[0, 0]], 2: [[-1, -1], [1, 1]], 3: [[-1, -1], [0, 0], [1, 1]], 4: [[-1, -1], [1, -1], [-1, 1], [1, 1]], 5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], 6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]] };
  function die(c, x, y, s, rot, face, col, glow) {   // a giant neon die (Playa Neón signs + the arch): dark glass body, a glowing neon outline, glowing pips
    c.save(); c.translate(x, y); c.rotate(rot); c.shadowColor = col; c.shadowBlur = glow || 0;
    c.fillStyle = "rgba(24,10,44,.92)"; rr(c, -s / 2, -s / 2, s, s, s * 0.2); c.fill(); c.strokeStyle = col; c.lineWidth = Math.max(1.6, s * 0.07); c.stroke();
    c.strokeStyle = "rgba(255,255,255,.85)"; c.lineWidth = Math.max(0.6, s * 0.025); rr(c, -s / 2 + s * 0.06, -s / 2 + s * 0.06, s * 0.88, s * 0.88, s * 0.16); c.stroke();
    for (const [px, py] of PIPS[face]) ell(c, "#ffffff", px * s * 0.26, py * s * 0.26, s * 0.085, s * 0.085);
    c.restore();
  }
  function fuzzy(c, x, y, sw) {   // fuzzy dice hanging from a lowrider's mirror: a string, two plush dice swinging
    line(c, "#ffffff", 0.5, [x, y, x + sw * 0.6, y + 2.2]);
    [[x + sw * 0.6 - 2.3, y + 4.3, 0.3, "#ff6fa8"], [x + sw * 0.6 + 2.2, y + 4.9, -0.25, "#ffffff"]].forEach(([dx, dy, r, col]) => { c.save(); c.translate(dx, dy); c.rotate(r);
      c.fillStyle = col; rr(c, -2.1, -2.1, 4.2, 4.2, 1.2); c.fill(); c.strokeStyle = col; c.lineWidth = 0.7; c.setLineDash([0.5, 0.6]); rr(c, -2.4, -2.4, 4.8, 4.8, 1.4); c.stroke(); c.setLineDash([]);
      const pc = col === "#ffffff" ? "#c21f66" : "#ffffff"; ell(c, pc, -0.9, -0.9, 0.45, 0.45); ell(c, pc, 0.9, 0.9, 0.45, 0.45); c.restore(); });
  }
  function diceArch(c, x, t, rm) {   // v49.5 Playa Neón: the "PLAYA NEÓN" neon arch over the road at the start, giant dice on top (drawn live, only near the start)
    const w = 230, top = -168, flick = rm ? 1 : 0.82 + 0.18 * Math.abs(Math.sin(t * 2.3)), pink = "#ff3d8b", turq = "#3ee8eb";
    for (const px of [x, x + w - 12]) { box(c, lin(c, px, 0, px + 12, 0, ["#b8eef0", "#7fd0d6"]), px, top + 10, 12, -top - 6, 3); box(c, "#f2e6d0", px - 4, -8, 20, 8, 2);
      c.save(); c.shadowColor = pink; c.shadowBlur = 8; line(c, pink, 1.6, [px + 6, top + 22, px + 6, -14]); c.restore(); }
    c.save(); c.globalAlpha = 0.6 + 0.4 * flick; c.fillStyle = "rgba(24,10,44,.9)"; c.beginPath(); c.moveTo(x - 8, top + 26); c.quadraticCurveTo(x + w / 2, top - 30, x + w + 8, top + 26); c.lineTo(x + w + 8, top + 2); c.quadraticCurveTo(x + w / 2, top - 56, x - 8, top + 2); c.closePath(); c.fill();
    c.shadowColor = turq; c.shadowBlur = 10; c.strokeStyle = turq; c.lineWidth = 2.2; c.stroke(); c.restore();
    c.save(); c.globalAlpha = 0.65 + 0.35 * flick; neon(c, "PLAYA NEÓN", x + w / 2, top - 12, 22, pink); c.restore();
    die(c, x + 6, top - 6, 30, -0.3, 5, turq, 10); die(c, x + w - 6, top - 6, 30, 0.35, 6, pink, 10);
  }
  function neon(c, s, x, y, size, col) { say(c, s, x, y, size, "#ffffff", { weight: 900, glow: col, blur: 9, stroke: col, sw: 2.4 }); }
  function beachLayer(c, P, night, pass) {   // the beach strip: pastel art-deco hotels with neon signs, palms between, a sidewalk rail
    if (pass === "lights") return;
    const deco = (x, w, h, a, b, sign, sc) => {
      box(c, lin(c, 0, -h, 0, 0, [a, b]), x, -h, w, h, 4); box(c, "rgba(255,255,255,.55)", x - 3, -h, w + 6, 6, 3);
      for (const yy of [-h + 26, -h + 52]) if (yy < -40) box(c, "rgba(255,255,255,.5)", x + 6, yy, w - 12, 3, 1.5);   // deco "eyebrows"
      for (let yy = -h + 34; yy < -46; yy += 26) for (let xx = x + 12; xx < x + w - 18; xx += 26) glass(c, xx, yy, 14, 12, false);
      box(c, "#2a1a3a", x + w / 2 - 14, -34, 28, 34, 2); glass(c, x + w / 2 - 11, -31, 22, 28, true);
      box(c, "rgba(20,10,40,.82)", x + 8, -h - 30, w - 16, 26, 6); neon(c, sign, x + w / 2, -h - 17, Math.min(15, (w - 24) / sign.length * 1.9), sc);
    };
    deco(20, 160, 150, "#ffc6dc", "#f29ac0", "Taquería Neón", "#3ee8eb");
    palm(c, 210, 150, 0.16, 1);
    deco(250, 130, 120, "#b8eef0", "#7fd0d6", "Motel Las Palmas", "#ff3d8b");
    palm(c, 400, 170, -0.1, 1.1);
    deco(440, 170, 168, "#d8c8f6", "#ab95e2", "Disco Elote", "#3ee8eb");
    palm(c, 640, 140, 0.12, 0.95); palm(c, 676, 160, -0.14, 1);
    deco(720, 140, 130, "#ffd8bf", "#f6ae8e", "Paletas Pastel", "#ff3d8b");
    palm(c, 890, 165, 0.1, 1.05);
    deco(930, 180, 156, "#c4f0dc", "#86d3b2", "Surf y Sol", "#ff3d8b");
    palm(c, 1140, 150, -0.12, 1);
    deco(1180, 150, 140, "#ffc6dc", "#f29ac0", "Club Coquí", "#3ee8eb");
    palm(c, 1360, 172, 0.14, 1.1);
    deco(1400, 160, 124, "#b8eef0", "#7fd0d6", "Mariscos Miau", "#ff3d8b");
    palm(c, 1600, 150, -0.1, 1); palm(c, 1634, 130, 0.16, 0.9);
    deco(1680, 150, 162, "#d8c8f6", "#ab95e2", "Hotel Flamenco", "#3ee8eb");
    palm(c, 1870, 160, 0.12, 1.05);
    die(c, 290, -176, 34, -0.22, 3, "#ff3d8b", 12); die(c, 334, -170, 30, 0.3, 4, "#3ee8eb", 12);   // giant neon dice on the motel roof
    die(c, 1225, -196, 36, 0.2, 6, "#3ee8eb", 12); die(c, 1272, -188, 30, -0.35, 1, "#ff3d8b", 12);   // and on Club Coquí
    line(c, "#6d5a8a", 4, [655, -10, 655, -170]); box(c, "rgba(20,10,40,.85)", 618, -226, 74, 34, 8); neon(c, "DADOS", 655, -209, 15, "#ff3d8b"); die(c, 636, -168, 26, -0.25, 2, "#3ee8eb", 10); die(c, 674, -164, 26, 0.28, 5, "#3ee8eb", 10);   // a pole sign between the palms
    die(c, 1760, -228, 30, -0.18, 4, "#ff3d8b", 12);   // a die on Hotel Flamenco
    box(c, "#f2e6d0", 0, -10, 2000, 10); for (let x = 0; x < 2000; x += 26) box(c, "#ffffff", x, -18, 3, 10); box(c, "#ffffff", 0, -19, 2000, 2.4);   // sidewalk + rail
  }
  function lowcar(c, x, w, t, rm) {   // a candy lowrider, hydraulics hopping (the obstacle box stays put)
    const b = rm ? 0 : Math.abs(Math.sin(t * 5 + x * 0.05)) * 5, col = [["#ff6fa8", "#c21f66"], ["#5ff3f6", "#169aa4"], ["#c79bff", "#7a3fd0"]][Math.floor(x / 7) % 3];
    c.fillStyle = lin(c, 0, -30 - b, 0, -8 - b, [col[0], col[1]]); rr(c, x, -21 - b, w, 13, 6); c.fill(); rr(c, x + 24, -30 - b, w - 46, 12, 6); c.fill();
    glass(c, x + 28, -28 - b, (w - 56) / 2, 8, false); glass(c, x + 32 + (w - 56) / 2, -28 - b, (w - 56) / 2, 8, false);
    fuzzy(c, x + 34 + (w - 56) / 2, -27.5 - b, rm ? 0.6 : 0.6 + Math.sin(t * 6 + x) * 1.4);   // fuzzy dice hanging from the mirror
    line(c, "#ffffff", 1.2, [x + 4, -14 - b, x + w - 4, -14 - b]); line(c, "rgba(255,255,255,.55)", 0.8, [x + 8, -18 - b, x + w - 30, -18 - b]);
    for (const wx of [x + 17, x + w - 17]) { ell(c, "#14161a", wx, -8, 8, 8); ell(c, "#f4f6f8", wx, -8, 5.4, 5.4); ell(c, lin(c, wx - 4, -12, wx + 4, -4, ["#ffffff", "#9aa3ad"]), wx, -8, 4, 4); for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3 + (rm ? 0 : t * 4); line(c, "#7c858f", 0.6, [wx, -8, wx + Math.cos(a) * 4, -8 + Math.sin(a) * 4]); } }
  }
  function sportscar(c, x, w, t, rm) {   // an 80s wedge sports car (our own shape, no badge)
    const col = Math.floor(x / 9) % 2 ? ["#ffffff", "#c9d0d8"] : ["#ff4a5a", "#b81e2e"];
    c.fillStyle = lin(c, 0, -26, 0, -6, col); c.beginPath(); c.moveTo(x, -8); c.lineTo(x + 2, -16); c.lineTo(x + w * 0.36, -24); c.lineTo(x + w * 0.62, -26); c.lineTo(x + w - 4, -18); c.lineTo(x + w, -10); c.lineTo(x + w, -6); c.lineTo(x, -6); c.closePath(); c.fill();
    c.fillStyle = "#1b2a3a"; c.beginPath(); c.moveTo(x + w * 0.38, -23); c.lineTo(x + w * 0.6, -25); c.lineTo(x + w * 0.74, -19); c.lineTo(x + w * 0.42, -18); c.closePath(); c.fill();
    box(c, "#14161a", x + 2, -12, w * 0.3, 2); for (let k = 0; k < 4; k++) box(c, "#14161a", x + w * 0.62 + k * 4, -16, 2.4, 6);   // side strakes
    box(c, "#fff6e0", x + 1, -15, 4, 2, 1); box(c, "#ff3d3d", x + w - 4, -16, 3.5, 2, 1);
    for (const wx of [x + 15, x + w - 16]) { ell(c, "#14161a", wx, -7, 7, 7); ell(c, lin(c, wx - 4, -11, wx + 4, -3, ["#ffffff", "#9aa3ad"]), wx, -7, 3.8, 3.8); }
  }
  // ================= v49.15 the Hon Dipo DJ (level 1, outside the store): a spoof of the Southside DJ-at-the-hardware-store video.
  // A made-up DJ (backwards flat-brim cap, dark tee, headphones) spinning on a row of black rolling tool chests rolled out onto the
  // sidewalk, PA speakers (one on a tripod, one up on the chests) that thump on the beat, a light bar with sweeping beams + a mini
  // disco ball, lumber + stacks of red product boxes. Scenery only: drawn live over the cached building, behind Juan, no hitboxes.
  // Reduce motion: everything holds still (no bob, thump, sweep or floating notes). Fiesta light colors; no real brand anywhere.
  const DJ_COL = ["#00C9CD", "#FF1A7F", "#FF6A0B", "#9b4dff", "#2a7bff"];
  const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a)).toFixed(3)})`; };
  function djBeam(c, x, y, ang, len, w0, w1, col, a) {   // a soft cone of light; ang 0 = straight up, + = to the right
    const dx = Math.sin(ang), dy = -Math.cos(ang), px = -dy, py = dx, ex = x + dx * len, ey = y + dy * len;
    const gr = c.createLinearGradient(x, y, ex, ey); gr.addColorStop(0, rgba(col, a)); gr.addColorStop(0.55, rgba(col, a * 0.45)); gr.addColorStop(1, rgba(col, 0));
    c.fillStyle = gr; c.beginPath(); c.moveTo(x + px * w0, y + py * w0); c.lineTo(ex + px * w1, ey + py * w1); c.lineTo(ex - px * w1, ey - py * w1); c.lineTo(x - px * w0, y - py * w0); c.closePath(); c.fill();
    const g2 = c.createLinearGradient(x, y, ex, ey); g2.addColorStop(0, rgba("#ffffff", a * 0.9)); g2.addColorStop(0.4, rgba(col, a * 0.35)); g2.addColorStop(1, rgba(col, 0));   // the bright core
    c.fillStyle = g2; c.beginPath(); c.moveTo(x + px * w0 * 0.35, y + py * w0 * 0.35); c.lineTo(ex + px * w1 * 0.3, ey + py * w1 * 0.3); c.lineTo(ex - px * w1 * 0.3, ey - py * w1 * 0.3); c.lineTo(x - px * w0 * 0.35, y - py * w0 * 0.35); c.closePath(); c.fill();
  }
  function djGlow(c, x, y, r, col, a) { const gr = c.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, rgba(col, a)); gr.addColorStop(1, rgba(col, 0)); c.fillStyle = gr; c.fillRect(x - r, y - r, r * 2, r * 2); }
  function djSpeaker(c, x, y, w, h, kick, rm) {   // a black PA cabinet: x = center, y = bottom
    box(c, "rgba(0,0,0,.22)", x - w / 2 + 2, y - h + 2, w, h, 3);
    box(c, lin(c, x - w / 2, 0, x + w / 2, 0, ["#34373f", "#1b1d22", "#0e0f12"]), x - w / 2, y - h, w, h, 3);
    box(c, "rgba(255,255,255,.10)", x - w / 2 + 1.5, y - h + 1.2, w - 3, 1.6, 0.8);
    const hy = y - h + h * 0.2; box(c, "#08090b", x - w * 0.34, hy - h * 0.1, w * 0.68, h * 0.2, 2); ell(c, "#30333b", x, hy, w * 0.12, h * 0.055);   // the horn
    const wy = y - h * 0.4, R0 = w * 0.38, R = R0 * (1 + 0.1 * kick);
    ell(c, "#050506", x, wy, R0 + 1.6, R0 + 1.6); ell(c, lin(c, x - R, wy - R, x + R, wy + R, ["#565b66", "#22252b", "#121317"]), x, wy, R, R);
    ell(c, "#0b0c0f", x, wy, R * 0.6, R * 0.6); ell(c, lin(c, x - 3, wy - 3, x + 3, wy + 3, ["#e8edf2", "#7d848e"]), x, wy, R * 0.24, R * 0.24);
    c.strokeStyle = "rgba(255,255,255,.12)"; c.lineWidth = 0.8; c.beginPath(); c.arc(x, wy, R * 0.82, -2.6, -1.2); c.stroke();
    for (let k = 0; k < 4; k++) box(c, "#2a2d34", x - w / 2 + 2 + k * (w - 4) / 3 - 0.6, y - 3.2, 1.2, 1.2, 0.6);   // the bass-port slots
    ell(c, kick > 0.45 ? "#00C9CD" : "#0b6e70", x + w / 2 - 3, y - h + 4, 1, 1);
    if (!rm && kick > 0.15) { c.strokeStyle = `rgba(255,255,255,${(0.75 * kick).toFixed(2)})`; c.lineWidth = 1.3; c.lineCap = "round";   // cartoon thump lines
      for (const s of [-1, 1]) for (let k = 0; k < 2; k++) { const r = w * 0.62 + k * 4 + (1 - kick) * 5; c.beginPath(); c.arc(x, wy, r, s < 0 ? Math.PI - 0.45 : -0.45, s < 0 ? Math.PI + 0.45 : 0.45); c.stroke(); } }
  }
  function djChest(c, x, w, h, glint) {   // a black rolling tool chest (no brand): x = left, ground at 0
    for (const cx of [x + 6, x + w - 6]) { box(c, "#454952", cx - 3, -6.5, 6, 2.6, 0.6); ell(c, "#0b0c0e", cx, -2.8, 2.8, 2.8); ell(c, "#7d848e", cx, -2.8, 1, 1); }
    const top = -h, body = h - 5.5;
    box(c, lin(c, 0, top, 0, top + body, ["#383b43", "#1c1e23", "#101115"]), x, top, w, body, 2);
    box(c, lin(c, 0, top - 3.5, 0, top + 0.5, ["#5a5e68", "#25272d"]), x - 1.2, top - 3.5, w + 2.4, 4, 1.4);   // the lid
    const rows = [4, 4, 4, 5, 5, 6.5, 8], tot = rows.reduce((a, b) => a + b, 0), k = (body - 3) / tot; let yy = top + 2;
    for (const r of rows) { const rh = r * k; box(c, "rgba(0,0,0,.55)", x + 1.5, yy + rh - 0.7, w - 3, 0.8);
      box(c, lin(c, 0, yy + 1, 0, yy + 2.6, ["#f2f5f8", "#8a929c"]), x + w * 0.12, yy + 1, w * 0.76, 1.5, 0.75); yy += rh; }
    box(c, "rgba(255,255,255,.07)", x + w * 0.62, top + 1, w * 0.1, body - 2);   // the glossy reflection
    if (glint) { box(c, glint, x + 1, top, w - 2, body); }   // the party lights reflected in the gloss
    line(c, "#c9d0d8", 1.6, [x + w + 1.2, top + 6, x + w + 2.6, top + 6, x + w + 2.6, top + 16, x + w + 1.2, top + 16]);   // the side handle
  }
  function djNote(c, x, y, s, col, dbl) {   // a little eighth note (or two beamed)
    c.save(); c.translate(x, y); c.scale(s, s); c.fillStyle = col; c.strokeStyle = col; c.lineWidth = 1.3; c.lineCap = "round";
    ell(c, col, 0, 0, 2.6, 2, -0.4); line(c, col, 1.3, [2.3, -0.6, 2.3, -9]);
    if (dbl) { ell(c, col, 6.5, -1.5, 2.6, 2, -0.4); line(c, col, 1.3, [8.8, -2.1, 8.8, -10.5]); line(c, col, 2.4, [2.3, -9, 8.8, -10.5], "butt"); }
    else { c.beginPath(); c.moveTo(2.3, -9); c.quadraticCurveTo(6.5, -7, 5.5, -3.5); c.stroke(); }
    c.restore();
  }
  function djDude(c, x, by, t, rm, part) {   // the made-up DJ, facing us; by = the chest top. part "body" (behind the decks) | "hand" (on the decks)
    const beat = rm ? 0.5 : mod(t * 2, 1), nod = rm ? 0 : Math.sin(beat * Math.PI) * 1.6, sway = rm ? 0 : Math.sin(t * Math.PI) * 1.2;
    const SK = "#b98157", SK2 = "#93603c", TEE = "#25272d", TEE2 = "#17181c";
    c.save(); c.translate(x, by); c.scale(1.5, 1.5);
    if (part === "hand") {   // the right hand scratching the left deck (in front of the controller)
      const sc = rm ? 0 : Math.sin(t * 9) * 2.2, hx = -9 + sc, hy = -4.2;
      line(c, SK, 4.4, [-12 + sway * 0.4, -12, hx, hy]); line(c, TEE, 6.2, [-13.5 + sway * 0.4, -20 + nod * 0.3, -12.6 + sway * 0.4, -13]);
      ell(c, SK, hx, hy, 2.8, 2.3); c.restore(); return; }
    const sy = nod * 0.45;   // the body dips a little on the beat, the head nods more
    c.translate(sway, 0);
    c.fillStyle = lin(c, -12, -24 + sy, 12, 6, [TEE, TEE2]); rr(c, -12, -23.5 + sy, 24, 30, 7); c.fill();   // the dark tee
    line(c, "rgba(255,255,255,.07)", 1, [3, -18 + sy, 6, -6 + sy]);
    ell(c, "#00C9CD", 5.2, -14.5 + sy, 2.6, 2.6); ell(c, TEE, 5.2, -14.5 + sy, 1.5, 1.5); ell(c, "#FF1A7F", 5.2, -14.5 + sy, 0.6, 0.6);   // a little record print
    box(c, SK2, -3, -27 + sy, 6, 5, 2);   // the neck
    // the left arm: up, holding one headphone cup to his ear
    const hx = 9.2, hy = -31 + nod;
    line(c, TEE, 6.2, [10.5, -20 + sy, 13.5, -14 + sy]); line(c, SK, 4.4, [13.2, -15 + sy, 15.5, -21, hx + 2.5, hy + 1.5]);
    // the head
    c.save(); c.translate(0, nod);
    const X = 0, Y = -32;
    ell(c, SK2, X - 7.6, Y + 0.5, 1.8, 2.6); ell(c, SK2, X + 7.6, Y + 0.5, 1.8, 2.6);
    ell(c, lin(c, X - 7, Y - 7, X + 7, Y + 8, ["#c99167", SK, SK2]), X, Y, 7.6, 8.6);
    ell(c, "#24160e", X, Y + 7.4, 2.2, 1.3);   // a little chin-strip goatee
    line(c, "#24160e", 1.1, [X - 4.4, Y - 3.4, X - 1.4, Y - 2.9]); line(c, "#24160e", 1.1, [X + 1.4, Y - 2.9, X + 4.4, Y - 3.4]);
    line(c, "#1b120c", 1.2, [X - 4.2, Y - 0.6, X - 2.8, Y - 1.4, X - 1.4, Y - 0.6]); line(c, "#1b120c", 1.2, [X + 1.4, Y - 0.6, X + 2.8, Y - 1.4, X + 4.2, Y - 0.6]);   // eyes shut, feeling it
    ell(c, SK2, X, Y + 1.8, 1.3, 1);
    c.fillStyle = "#3a1d12"; c.beginPath(); c.moveTo(X - 3.2, Y + 3.4); c.quadraticCurveTo(X, Y + 6.6, X + 3.2, Y + 3.4); c.closePath(); c.fill();   // a big grin
    c.fillStyle = "#ffffff"; c.beginPath(); c.moveTo(X - 2.7, Y + 3.6); c.quadraticCurveTo(X, Y + 4.9, X + 2.7, Y + 3.6); c.closePath(); c.fill();
    // the cap, on backwards: the flat brim sticks out behind, the crown with the strap gap over the forehead
    poly(c, "#0d0e10", [X + 2, Y - 8.6, X + 13.5, Y - 10.8, X + 14, Y - 8.4, X + 3, Y - 6]);
    c.fillStyle = lin(c, X - 8, Y - 14, X + 8, Y - 5, ["#2a2c32", "#141519", "#0b0c0e"]); c.beginPath(); c.ellipse(X, Y - 5.2, 8.3, 8.8, 0, Math.PI, 0); c.closePath(); c.fill();
    box(c, "#0b0c0e", X - 8.3, Y - 6.2, 16.6, 2, 0.8);
    c.fillStyle = "#24160e"; c.beginPath(); c.ellipse(X, Y - 5.2, 2.6, 2.4, 0, Math.PI, 0); c.fill();   // the snapback gap (hair)
    line(c, "#c9d0d8", 0.9, [X - 2.6, Y - 5.2, X + 2.6, Y - 5.2]); ell(c, "#2a2c32", X, Y - 14, 1.1, 0.7);
    // the headphones: a silver band over the cap, his right cup on, the left one held to the ear
    c.strokeStyle = "#c9d0d8"; c.lineWidth = 1.5; c.beginPath(); c.ellipse(X, Y - 3, 9.6, 11.6, 0, Math.PI * 1.05, Math.PI * 1.95); c.stroke();
    ell(c, "#17181c", X - 9, Y + 0.5, 2.8, 3.8); ell(c, "#FF1A7F", X - 9.6, Y + 0.5, 1, 2.2);
    ell(c, "#17181c", X + 9.4, Y + 1, 2.8, 3.8); ell(c, "#00C9CD", X + 10, Y + 1, 1, 2.2);
    c.restore();
    ell(c, SK, hx + 2.6, hy + 1.6, 2.7, 2.4);   // the hand on the cup
    c.restore();
  }
  function djFan(c, x, t, rm) {   // a shopper who stopped to dance (feet at x, 0; facing us): ponytail, pink tee, jeans, a paint can
    const b = rm ? 0.25 : mod(t * 2, 1), up = Math.sin(b * Math.PI), sw = rm ? 0 : Math.sin(t * Math.PI), SK = "#d9a173", SK2 = "#b98157";
    c.save(); c.translate(x, 0); c.scale(1.55, 1.55);
    const hip = -25 + up * 1.4;
    line(c, "#2f5291", 4.6, [-2.6, hip, -3.6 - sw, -12, -3, -1]); line(c, "#2f5291", 4.6, [2.6, hip, 4 - sw * 0.5, -12 + up, 3.2, -1]);
    box(c, "#f4f6f8", -6.4, -2.4, 5.6, 2.6, 1.2); box(c, "#f4f6f8", 0.8, -2.4, 5.6, 2.6, 1.2); box(c, "#00C9CD", -6.4, -0.6, 5.6, 0.9); box(c, "#00C9CD", 0.8, -0.6, 5.6, 0.9);
    c.save(); c.translate(sw * 0.8, hip); c.rotate(sw * 0.06);
    c.fillStyle = lin(c, -7, -20, 7, 2, ["#ff4d97", "#e01a6e"]); rr(c, -6.5, -19, 13, 21, 5); c.fill();
    const wave = rm ? 0 : Math.sin(t * Math.PI * 2);   // arms up, waving on the beat; one holds a paint can
    line(c, SK, 3, [-5.5, -16, -10, -24, -9 + wave * 2, -32]); ell(c, SK, -9 + wave * 2, -33, 1.9, 1.9);
    line(c, SK, 3, [5.5, -16, 10, -23, 8.5 - wave * 2, -31]); ell(c, SK, 8.5 - wave * 2, -32, 1.9, 1.9);
    box(c, lin(c, 0, -40, 0, -32, ["#c9d0d8", "#8a939c"]), 5.5 - wave * 2, -40, 6.5, 7.5, 1); box(c, "#00C9CD", 5.5 - wave * 2, -37.5, 6.5, 2.4); line(c, "#5b6270", 0.6, [5.5 - wave * 2, -40, 8.8 - wave * 2, -43, 12 - wave * 2, -40]);
    box(c, SK2, -1.6, -22, 3.2, 4, 1.2);
    const Y = -27.5 - up * 0.8; ell(c, "#2a1810", 0, Y - 1, 6.6, 6.8); ell(c, "#2a1810", 5.5 + sw * 1.5, Y - 6, 3, 2.4, 0.5);   // hair + a bouncing ponytail
    ell(c, lin(c, -5, Y - 5, 5, Y + 6, ["#e6b48a", SK, SK2]), 0, Y + 0.6, 5.4, 6.2);
    c.fillStyle = "#2a1810"; c.beginPath(); c.ellipse(0, Y - 2.6, 5.8, 3.8, 0, Math.PI, 0); c.fill();
    line(c, "#1b120c", 0.9, [-3.2, Y + 0.4, -2.2, Y - 0.4, -1.2, Y + 0.4]); line(c, "#1b120c", 0.9, [1.2, Y + 0.4, 2.2, Y - 0.4, 3.2, Y + 0.4]);
    c.fillStyle = "#7a2a1a"; c.beginPath(); c.moveTo(-2, Y + 2.8); c.quadraticCurveTo(0, Y + 5.2, 2, Y + 2.8); c.closePath(); c.fill();
    ell(c, "rgba(255,90,120,.35)", -3.4, Y + 2.2, 1.3, 0.8); ell(c, "rgba(255,90,120,.35)", 3.4, Y + 2.2, 1.3, 0.8);
    c.restore(); c.restore();
  }
  function djRig(c, t, rm) {   // in the building's units (360 wide, ground at 0); called each frame for level 1 once the store is on screen
    const beat = rm ? 0.5 : mod(t * 2, 1), kick = rm ? 0.35 : Math.max(0, 1 - beat * 3.2), C = DJ_COL;
    const sweep = (i, sp, amp) => (rm ? 0 : Math.sin(t * sp + i * 1.7) * amp);
    // lumber on a pallet + stacks of red product boxes (left of the door)
    box(c, "#8a6a44", 8, -6, 54, 6); for (let x = 10; x < 60; x += 9) box(c, "#6e5232", x, -5, 4, 5);
    for (let r = 0; r < 7; r++) { const y = -10 - r * 4.4; box(c, lin(c, 0, y, 0, y + 4, ["#f0d29c", "#d6ad6c"]), 9 + (r % 2), y, 52, 4, 0.8); box(c, "rgba(120,80,30,.35)", 9, y + 3.4, 54, 0.8); }
    for (const sx of [20, 48]) box(c, "#9c7748", sx, -41, 2.4, 31);   // the straps
    box(c, "#8a6a44", 66, -6, 34, 6); for (let x = 68; x < 98; x += 8) box(c, "#6e5232", x, -5, 4, 5);
    for (let r = 0; r < 3; r++) for (let k = 0; k < 3; k++) { const bx = 67 + k * 11, by = -17 - r * 11;
      box(c, lin(c, 0, by, 0, by + 11, ["#e5322e", "#b81f22"]), bx, by, 10.6, 10.6, 1); box(c, "#ffffff", bx + 1, by + 6.2, 8.6, 2); box(c, "rgba(0,0,0,.25)", bx + 2, by + 2, 5, 1); }
    box(c, lin(c, 0, -50, 0, -39, ["#e5322e", "#b81f22"]), 78, -50, 10.6, 10.6, 1); box(c, "#ffffff", 79, -43.8, 8.6, 2);
    // party light washing the wall behind the booth (it pulses on the beat)
    djGlow(c, 292, -78, 78, C[Math.floor(rm ? 1 : t) % 2 ? 1 : 0], 0.22 + 0.16 * kick); djGlow(c, 330, -110, 50, C[3], 0.2 + 0.1 * kick);
    djFan(c, 112, t, rm);
    // the light bar on its stand (behind the booth), the disco ball hanging off it
    box(c, lin(c, 340, 0, 345, 0, ["#5b6270", "#c9d0d8", "#5b6270"]), 340.5, -134, 3, 90);
    box(c, lin(c, 0, -137, 0, -131, ["#c9d0d8", "#6c737d"]), 266, -137, 88, 4, 1.5);
    line(c, "#9aa3ad", 0.6, [272, -133, 272, -122]);
    const db = 272, dby = -116; djGlow(c, db, dby, 16, "#ffffff", 0.35);
    c.save(); c.beginPath(); c.arc(db, dby, 6.2, 0, Math.PI * 2); c.clip(); box(c, lin(c, db - 6, dby - 6, db + 6, dby + 6, ["#f4f7fa", "#9aa3ad", "#5b6270"]), db - 7, dby - 7, 14, 14);
    const spin = rm ? 0 : t * 3; for (let r = -3; r <= 3; r++) for (let k = -4; k <= 4; k++) { const fx = db + k * 2 + mod(spin * 2 + r, 2) - 1, fy = dby + r * 2;
      box(c, ["#ffffff", "#c9d0d8", C[(r + k + 9) % 4], "#8a939c"][Math.abs(r * 3 + k + Math.floor(spin)) % 4], fx - 0.8, fy - 0.8, 1.6, 1.6); } c.restore();
    for (let i = 0; i < 5; i++) { const a = (rm ? 0 : t * 1.4) + i * 1.26, r = 22 + (i % 3) * 13; ell(c, rgba(C[i % 4], 0.85), db + Math.cos(a) * r * 1.4, dby + Math.sin(a) * r * 0.5 + 10, 1.4, 1.4); }   // the sparkles it throws
    // two pars on the bar wash down toward the door (behind the booth, so the chests stay black), with pools of light on the sidewalk
    const pars = [[290, 0, 1.75], [314, 1, 1.95], [338, 3, 2.15]];
    for (const [px, i, base] of pars) { const ang = -(base + 0.45 + sweep(i, 1.3, 0.3)); djBeam(c, px, -128, ang, 175, 2.5, 26, C[i], 0.3 + 0.14 * kick);
      const fx = px + Math.sin(ang) * 128 / -Math.cos(ang); c.save(); c.scale(1, 0.22); djGlow(c, fx, -3 / 0.22, 30, C[i], 0.5 + 0.25 * kick); c.restore(); }
    // the DJ behind his booth: a row of black rolling tool chests, the controller on top
    djDude(c, 300, -46, t, rm, "body");
    const glint = rgba(C[Math.floor(rm ? 0 : t * 2) % 3], 0.05 + 0.05 * kick);
    box(c, "#00C9CD", 262, -6, 96, 6); ell(c, "rgba(0,0,0,.3)", 310, -1, 50, 3);   // the store's turquoise base stripe again (hides the cart corral behind the chests) + a shadow
    djChest(c, 264, 45, 46, glint); djChest(c, 310.5, 45, 46, glint);
    poly(c, "#121317", [271, -46, 329, -46, 326, -52, 274, -52]); box(c, lin(c, 0, -53, 0, -51, ["#3a3d44", "#202227"]), 274, -53.2, 52, 2, 1);
    for (const [px, ph] of [[283.5, 0], [316.5, 1.3]]) { ell(c, "#2a2d34", px, -53.6, 8.6, 2.5); ell(c, "#9aa3ad", px, -54, 7.4, 2.1); ell(c, "#1b1d22", px, -54, 5.6, 1.6);
      const a = (rm ? 0.6 : t * 7) + ph; ell(c, "#FF1A7F", px + Math.cos(a) * 4.6, -54 + Math.sin(a) * 1.3, 0.9, 0.5); ell(c, "#c9d0d8", px, -54, 0.9, 0.4); }
    for (let k = 0; k < 4; k++) { const lv = rm ? 2 : Math.round(1 + 3 * kick * (0.6 + 0.4 * Math.sin(k * 2.1 + t * 5))); for (let j = 0; j < 4; j++) box(c, j < lv ? (j > 2 ? "#FF1A7F" : "#00C9CD") : "#2a2d34", 296.5 + k * 2, -48 - j * 1.3, 1.4, 0.9); }
    djDude(c, 300, -46, t, rm, "hand");
    // the speakers: one up on the chests, one on a tripod by the door
    djSpeaker(c, 344, -46, 22, 34, kick, rm);
    line(c, "#1b1d22", 1.6, [250, -34, 238, 0]); line(c, "#1b1d22", 1.6, [250, -34, 262, 0]); line(c, "#2a2d34", 1.6, [250, -34, 251, 0]);
    box(c, lin(c, 248, 0, 252, 0, ["#3a3d44", "#7d848e", "#3a3d44"]), 248.6, -80, 2.8, 48);
    djSpeaker(c, 250, -76, 24, 38, kick, rm);
    // the lights: two pars on the bar wash down toward the door, a moving head on each speaker sweeps a beam up into the sky
    for (const [px, i, base] of pars) { box(c, "#17181c", px - 4, -132, 8, 7, 2); ell(c, C[i], px, -125.5, 3.4, 1.6); djGlow(c, px, -125, 9, C[i], 0.7); }
    [[250, -114, 4, 0.28], [344, -80, 0, -0.32]].forEach(([mx, my, i, base]) => { const ang = base + sweep(i, 0.9, 0.42);
      djBeam(c, mx, my - 6, ang, 280, 2.2, 26, C[i], 0.5 + 0.14 * kick);
      box(c, "#17181c", mx - 5, my - 3, 10, 3, 1); c.save(); c.translate(mx, my - 6); c.rotate(ang); box(c, "#22252b", -3.6, -5, 7.2, 8, 2.5); ell(c, C[i], 0, -5, 2.6, 1.1); c.restore(); djGlow(c, mx + Math.sin(ang) * 6, my - 6 - Math.cos(ang) * 6, 8, C[i], 0.8); });
    // notes floating up off the speakers
    if (!rm) for (let i = 0; i < 6; i++) { const u = mod(t * 0.45 + i / 6, 1), src = i % 2 ? [344, -80] : [250, -116];
      c.globalAlpha = Math.min(1, u * 5) * (1 - u); djNote(c, src[0] + (i % 2 ? -14 - u * 16 : 6 + u * 18) + Math.sin(u * 9 + i) * 4, src[1] - 6 - u * 56, 0.9 + (i % 3) * 0.15, C[i % 4], i % 3 === 0); c.globalAlpha = 1; }   // drifting up, clear of the sign
  }
  function destination(c, n, night) {
    if (n === 7) {   // v49.5 Playa Neón: the finish is the beach: sand, surf, umbrellas, giant inflatable dice and a cheering cartoon crowd in swimwear (PG)
      box(c, lin(c, 0, -150, 0, -40, ["#5fd9e0", "#2bb4c4"]), 0, -150, 360, 112); c.fillStyle = "rgba(255,255,255,.55)"; for (let k = 0; k < 9; k++) { const wx = 8 + k * 42; c.beginPath(); c.ellipse(wx, -60 - (k % 3) * 22, 14, 2, 0, 0, Math.PI * 2); c.fill(); }   // the ocean
      c.fillStyle = "#ffffff"; c.beginPath(); c.moveTo(0, -40); for (let x = 0; x <= 360; x += 20) c.quadraticCurveTo(x + 10, -48, x + 20, -40); c.lineTo(360, -36); c.lineTo(0, -36); c.fill();   // surf
      box(c, lin(c, 0, -40, 0, 0, ["#ffe2b0", "#f4c98a"]), 0, -40, 360, 40); c.fillStyle = "rgba(200,150,90,.35)"; for (let k = 0; k < 30; k++) c.fillRect((k * 53) % 360, -34 + (k * 17) % 30, 3, 1.2);   // sand
      const umb = (x, a, b) => { line(c, "#f4f6f8", 2, [x, 0, x, -86]); for (let k = 0; k < 6; k++) { c.fillStyle = k % 2 ? a : b; c.beginPath(); c.moveTo(x, -92); c.arc(x, -78, 34, Math.PI + k * Math.PI / 6, Math.PI + (k + 1) * Math.PI / 6); c.closePath(); c.fill(); } };
      umb(40, "#ff3d8b", "#ffffff"); umb(330, "#3ee8eb", "#ffffff");
      line(c, "#6d5a8a", 4, [180, -40, 180, -150]); box(c, "rgba(20,10,40,.85)", 110, -196, 140, 42, 10); neon(c, "PLAYA NEÓN", 180, -175, 22, "#ff3d8b");   // the neon sign
      die(c, 128, -150, 26, -0.25, 3, "#3ee8eb", 10); die(c, 232, -150, 26, 0.3, 5, "#3ee8eb", 10);
      const inflate = (x, y, s, rot, face, col) => { c.save(); c.translate(x, y); c.rotate(rot); c.fillStyle = col; rr(c, -s / 2, -s / 2, s, s, s * 0.28); c.fill(); c.fillStyle = "rgba(255,255,255,.35)"; rr(c, -s / 2 + 3, -s / 2 + 3, s * 0.4, s * 0.25, 4); c.fill(); for (const [px, py] of PIPS[face]) ell(c, "#ffffff", px * s * 0.26, py * s * 0.26, s * 0.08, s * 0.08); c.restore(); };
      inflate(76, -16, 30, 0.12, 6, "#ff6fa8"); inflate(286, -15, 28, -0.18, 2, "#c79bff");   // giant inflatable dice on the sand
      const fan = (x, sk, kind, suit, hair, tall) => {   // a cheering beachgoer, arms up (PG cartoon swimwear)
        const [S1, S2] = SKINS[sk], h = tall || 1; c.save(); c.translate(x, 0); c.scale(1.45 * h, 1.45 * h);
        line(c, S2, 4.2, [-2.6, 0, -2.4, -22]); line(c, S1, 4.2, [2.6, 0, 2.4, -22]);
        box(c, S1, -6, -44, 12, 22, 5);
        if (kind === "trunks") box(c, suit, -6.4, -26, 12.8, 10, 2.5);
        else if (kind === "one") { box(c, suit, -6, -40, 12, 17, 4); line(c, suit, 1.4, [-3.5, -40, -4, -44]); line(c, suit, 1.4, [3.5, -40, 4, -44]); }
        else { box(c, suit, -6, -26, 12, 5, 2); ell(c, suit, -3, -37.5, 3.4, 2.6); ell(c, suit, 3, -37.5, 3.4, 2.6); line(c, suit, 1.1, [-5.5, -38, -4.5, -44]); line(c, suit, 1.1, [5.5, -38, 4.5, -44]); }
        line(c, S1, 3.4, [-5, -42, -11, -54, -12, -63]); line(c, S1, 3.4, [5, -42, 11, -54, 12, -63]); ell(c, S1, -12, -64, 2.4, 2.4); ell(c, S1, 12, -64, 2.4, 2.4);
        ell(c, S1, 0, -51, 6, 6.4); c.fillStyle = hair; c.beginPath(); c.ellipse(0, -53, 6.4, 5, 0, Math.PI, 0); c.fill(); if (kind !== "trunks") { ell(c, hair, -5.6, -48, 2, 5); ell(c, hair, 5.6, -48, 2, 5); }
        ell(c, "#1b120c", -2.2, -51.5, 0.8, 0.8); ell(c, "#1b120c", 2.2, -51.5, 0.8, 0.8); c.fillStyle = "#7a2a22"; c.beginPath(); c.arc(0, -48.5, 2.2, 0, Math.PI); c.fill();   // a big open-mouth cheer
        c.restore(); };
      fan(214, 1, "trunks", "#ff8a00", "#2a1c14"); fan(238, 3, "bikini", "#ff3d8b", "#e8b830", 0.95); fan(262, 2, "trunks", "#3ee8eb", "#1b120c", 1.05); fan(286, 0, "one", "#7a3fd0", "#5a2a14");
      fan(308, 4, "bikini", "#00b8b0", "#1b120c", 0.95); fan(332, 1, "trunks", "#ff3d8b", "#3a2414"); fan(352, 3, "one", "#ff6f3a", "#8a4a1a", 0.92);
      say(c, "Woo-hoo!", 262, -118, 16, "#ffffff", { weight: 900, stroke: "#ff3d8b", sw: 3 }); say(c, "Welcome, Juan!", 300, -100, 12, "#ffffff", { weight: 900, stroke: "#00807a", sw: 3 });
      return;
    }
    if (n === "site") {   // v47 La Chamba: a construction site downtown: steel frame + crane, a "COMING SOON Gualmart" parody sign (our own art), fencing, cones, a cement mixer, a yellow excavator and loader
      const BLUE = "#0a5fc2", YEL = "#f5b800", YEL2 = "#d79a00";
      box(c, lin(c, 0, -40, 0, 0, ["#c9a77c", "#a8865c"]), 0, -40, 360, 40); c.fillStyle = "#b8956a"; c.beginPath(); c.moveTo(-10, -36); c.quadraticCurveTo(40, -96, 100, -36); c.fill();   // the dirt lot + a pile
      box(c, lin(c, 0, -190, 0, -30, ["#b9c1ca", "#9aa3ad"]), 196, -190, 70, 160); for (let y = -182; y < -40; y += 32) box(c, "#7d848e", 196, y, 70, 3);   // the concrete core going up
      box(c, "#d6c2a0", 0, -64, 150, 24, 2); for (let x = 6; x < 150; x += 14) box(c, "#c4ab84", x, -64, 2, 24);   // a stack of plywood
      c.strokeStyle = "#8a939c"; c.lineWidth = 4; for (let x = 150; x <= 350; x += 40) { c.beginPath(); c.moveTo(x, -30); c.lineTo(x, -190); c.stroke(); } for (let y = -190; y < -30; y += 32) { c.beginPath(); c.moveTo(150, y); c.lineTo(350, y); c.stroke(); }
      c.strokeStyle = "rgba(138,147,156,.6)"; c.lineWidth = 1.4; for (let x = 150; x < 350; x += 40) for (let y = -190; y < -30; y += 32) { c.beginPath(); c.moveTo(x, y); c.lineTo(x + 40, y + 32); c.stroke(); }
      // the tower crane
      for (let y = -230; y < -30; y += 12) { line(c, YEL2, 1.2, [318, y, 330, y + 12]); line(c, YEL2, 1.2, [330, y, 318, y + 12]); } line(c, YEL, 3, [318, -30, 318, -232]); line(c, YEL, 3, [330, -30, 330, -232]);
      box(c, YEL, 196, -236, 162, 6, 1); line(c, YEL2, 1.2, [324, -250, 200, -236]); line(c, YEL2, 1.2, [324, -250, 356, -236]); box(c, YEL, 321, -252, 6, 16); box(c, "#3a3f4a", 334, -244, 22, 8, 1);
      line(c, "#3a3f4a", 1, [236, -230, 236, -170]); box(c, "#7d848e", 222, -170, 28, 6, 1);   // a beam on the hook
      // the yellow loader, parked behind the fence
      c.save(); c.translate(150, -30); c.scale(0.8, 0.8); box(c, YEL, 0, -36, 70, 22, 4); box(c, YEL, 36, -64, 30, 30, 3); glass(c, 40, -60, 22, 20, false); poly(c, YEL2, [-28, -6, -6, -32, 2, -28, -18, -2]); box(c, "#3a3f4a", -32, -14, 30, 14, 2);
      for (const wx of [14, 58]) { ell(c, "#1d1f24", wx, -10, 14, 14); ell(c, "#7d848e", wx, -10, 6, 6); } c.restore();
      // the sign: COMING SOON Gualmart, white letters on Gualmart blue, with our own four-point sparkle
      for (const px of [42, 166]) box(c, "#6c757d", px, -98, 6, 98);
      box(c, "#073f84", 14, -184, 186, 92, 6); box(c, lin(c, 0, -182, 0, -94, ["#1a74d6", BLUE, "#0750a8"]), 16, -182, 182, 88, 5);
      say(c, "COMING SOON", 107, -166, 15, "#ffffff", { weight: 900, max: 170 });
      line(c, "rgba(255,255,255,.6)", 1.2, [36, -155, 178, -155]);
      say(c, "Gualmart", 96, -132, 33, "#ffffff", { weight: 900, max: 140, font: UI });
      const sp = (x, y, r) => { c.fillStyle = "#ffffff"; c.beginPath(); for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4, rr2 = i % 2 ? r * 0.28 : r; c.lineTo(x + Math.cos(a) * rr2, y + Math.sin(a) * rr2); } c.closePath(); c.fill(); };
      sp(182, -134, 12); sp(170, -150, 4.5);
      say(c, "Pardon our dust · Opening soon", 107, -106, 9, "#dbe9ff", { weight: 800, max: 170 });
      // fencing: chain-link with an orange safety stripe, the gate open where Juan walks in
      for (const [x0, x1] of [[0, 196], [270, 360]]) {
        box(c, "rgba(220,226,234,.22)", x0, -46, x1 - x0, 46); c.strokeStyle = "rgba(120,128,138,.75)"; c.lineWidth = 0.8;
        for (let x = x0; x < x1; x += 7) { c.beginPath(); c.moveTo(x, -46); c.lineTo(x + 7, 0); c.stroke(); c.beginPath(); c.moveTo(x + 7, -46); c.lineTo(x, 0); c.stroke(); }
        line(c, "#7d848e", 2.2, [x0, -46, x1, -46]); for (let x = x0; x <= x1; x += 49) line(c, "#7d848e", 2.6, [x, -48, x, 0]); box(c, "#ff6a00", x0, -24, x1 - x0, 6);
      }
      // the cement mixer truck (left), facing right
      c.save(); c.translate(6, 0);
      box(c, "#3a3f4a", 0, -20, 128, 10, 2); box(c, lin(c, 0, -60, 0, -18, ["#ffffff", "#c9d0d8"]), 92, -58, 34, 40, 4); glass(c, 104, -54, 18, 16, false); box(c, BLUE, 92, -30, 34, 5);
      c.save(); c.translate(48, -46); c.rotate(-0.18); ell(c, lin(c, -40, -20, 40, 20, ["#f2f5f8", "#b9c1ca"]), 0, 0, 42, 22); c.save(); c.beginPath(); c.ellipse(0, 0, 42, 22, 0, 0, Math.PI * 2); c.clip();
      c.strokeStyle = "#ff6a00"; c.lineWidth = 5; for (const dx of [-30, -8, 14, 36]) { c.beginPath(); c.moveTo(dx - 14, 24); c.lineTo(dx + 8, -24); c.stroke(); } c.restore(); ell(c, "rgba(255,255,255,.5)", -10, -12, 18, 4); c.restore();
      poly(c, "#7d848e", [6, -34, -6, -24, 2, -20, 12, -30]); box(c, "#7d848e", 86, -40, 6, 22);
      for (const wx of [24, 50, 110]) { ell(c, "#1d1f24", wx, -9, 10, 10); ell(c, "#c9d0d8", wx, -9, 4.5, 4.5); } c.restore();
      // the yellow excavator (right), the arm reaching up over the fence
      c.save(); c.translate(282, 0);
      box(c, "#2b2f38", 0, -16, 74, 16, 8); for (let x = 8; x < 70; x += 10) ell(c, "#4a4d55", x, -8, 3.5, 3.5);
      box(c, YEL, 6, -44, 62, 28, 4); box(c, YEL, 6, -70, 30, 28, 4); glass(c, 10, -66, 22, 20, false); box(c, YEL2, 40, -36, 26, 4);
      line(c, YEL, 7, [50, -40, 70, -96], "butt"); line(c, YEL, 6, [70, -96, 92, -60], "butt"); ell(c, YEL2, 70, -96, 5, 5);
      poly(c, "#3a3f4a", [86, -64, 102, -56, 96, -40, 84, -48]); c.restore();
      // cones at the gate
      for (const cx of [204, 262, 352]) { poly(c, "#ff6a00", [cx - 7, 0, cx + 7, 0, cx + 3, -22, cx - 3, -22]); box(c, "#ffffff", cx - 5, -14, 10, 4); box(c, "#3a3f4a", cx - 9, -2, 18, 2); }
      return;
    }
    if (n === 1) {   // Hon Dipo (v47; v49.15 repainted so it looks nothing like a real big-box store): our own Southside ferretería. Beige stucco,
      // turquoise + pink Fiesta trim, papel picado under the roofline, and a hand-painted, taquería-style arched sign board (cream, pink +
      // turquoise borders, "Hon Dipo" in painted serif letters with a drop shadow, FERRETERÍA under it). No orange square, no stencil wordmark.
      const TQ = "#00C9CD", TQ2 = "#0a9ea2", PK = "#FF1A7F", PK2 = "#c8125f", OJ = "#FF6A0B", INK = "#3a1d3a";
      box(c, lin(c, 0, -196, 0, 0, ["#e6d7c1", "#d2bfa4"]), 0, -196, 360, 196);
      c.fillStyle = "rgba(120,96,70,.16)"; for (let x = 24; x < 360; x += 24) c.fillRect(x, -180, 1.2, 180);
      box(c, TQ, 0, -196, 360, 12); box(c, TQ2, 0, -184, 360, 3);   // the turquoise roof trim
      box(c, PK, 0, -112, 360, 5); box(c, TQ, 0, -6, 360, 6);        // a pink stripe across the front, turquoise along the bottom
      // papel picado strung under the roofline, both sides of the sign
      for (const [x0, x1] of [[0, 108], [252, 360]]) { const sag = (x) => -178 + 6 * Math.sin(Math.PI * (x - x0) / (x1 - x0));
        line(c, "rgba(60,40,60,.5)", 0.7, [x0, -178, (x0 + x1) / 2, -172, x1, -178]);
        for (let x = x0 + 4, i = 0; x < x1 - 8; x += 11, i++) { const y = sag(x + 4), col = [PK, TQ, OJ, "#9b4dff"][i % 4];
          poly(c, col, [x, y, x + 9, y, x + 9, y + 9, x + 4.5, y + 12, x, y + 9]); ell(c, "rgba(255,255,255,.55)", x + 4.5, y + 4.5, 1.4, 1.4); } }
      for (const [x0, txt, col] of [[10, "LUMBER · TOOLS", PK], [256, "PAINT · GARDEN", TQ2]]) { box(c, col, x0, -158, 94, 22, 11); say(c, txt, x0 + 47, -147, 10, "#ffffff", { weight: 900, max: 84 }); }
      // the hand-painted sign board: an arched top, a pink frame, a turquoise pinstripe, cream inside
      const arch = (x0, x1, top, bot) => { c.beginPath(); c.moveTo(x0, bot); c.lineTo(x0, top + 22); c.quadraticCurveTo((x0 + x1) / 2, top - 14, x1, top + 22); c.lineTo(x1, bot); c.closePath(); };
      c.fillStyle = "rgba(0,0,0,.18)"; arch(111, 255, -191, -97); c.fill();
      c.fillStyle = lin(c, 0, -194, 0, -100, [PK, PK2]); arch(108, 252, -194, -100); c.fill();
      c.fillStyle = TQ; arch(113, 247, -189, -105); c.fill();
      c.fillStyle = lin(c, 0, -186, 0, -108, ["#fff8ec", "#f6e8d2"]); arch(116, 244, -186, -108); c.fill();
      for (const sx of [126, 234]) for (const sy of [-160, -118]) { c.save(); c.translate(sx, sy); c.rotate(Math.PI / 4); poly(c, OJ, [0, -4, 1, -1, 4, 0, 1, 1, 0, 4, -1, 1, -4, 0, -1, -1]); c.restore(); }   // painted sparkles
      c.save(); c.translate(180, -150); c.rotate(-0.04);
      say(c, "Hon Dipo", 2.2, 2.6, 31, TQ2, { font: WEST, weight: 900, italic: true, max: 102 });   // the painted drop shadow
      say(c, "Hon Dipo", 0, 0, 31, PK, { font: WEST, weight: 900, italic: true, max: 102, stroke: INK, sw: 2.6 });
      c.restore();
      c.strokeStyle = OJ; c.lineWidth = 2.4; c.lineCap = "round"; c.beginPath(); c.moveTo(134, -130); c.quadraticCurveTo(180, -138, 226, -131); c.stroke();   // a brushy swash
      say(c, "FERRETERÍA", 180, -118, 10.5, INK, { weight: 900, max: 92 });
      box(c, lin(c, 0, -90, 0, -80, [TQ, TQ2]), 112, -90, 136, 10, 3); box(c, "#6c757d", 120, -80, 120, 74);
      glass(c, 124, -76, 54, 70, false); glass(c, 182, -76, 54, 70, false); box(c, "#6c757d", 178, -76, 4, 70);
      const RL = "#7d848e";   // the cart corrals: plain silver rails
      for (let k = 0; k < 3; k++) for (const cx of [26, 62, 270, 306]) { const y = -16; box(c, RL, cx + k * 4, y - 22, 30, 4, 1); c.strokeStyle = RL; c.lineWidth = 1.2; rr(c, cx + k * 4, y - 20, 30, 18, 2); c.stroke(); for (let g = 4; g < 30; g += 5) { c.beginPath(); c.moveTo(cx + k * 4 + g, y - 20); c.lineTo(cx + k * 4 + g, y - 2); c.stroke(); } ell(c, "#111", cx + k * 4 + 5, -1, 2.5, 2.5); ell(c, "#111", cx + k * 4 + 26, -1, 2.5, 2.5); }
      for (let k = 0; k < 3; k++) box(c, ["#c9b29a", "#b39b81", "#d6c2ab"][k], 92 - k * 2, -12 - k * 10, 22, 10, 3);
      return;
    }
    if (n === 2) {   // Don Pedroes: low cream stucco, red Spanish-tile roofs, the arched block-pattern entry, the tall pole sign
      const tiles = (x, y, w, h) => { poly(c, lin(c, 0, y, 0, y + h, ["#c8432c", "#9e2e1e"]), [x - 8, y + h, x + w + 8, y + h, x + w - 10, y, x + 10, y]);
        c.strokeStyle = "rgba(90,20,10,.45)"; c.lineWidth = 1; for (let k = x - 4; k < x + w + 6; k += 5) { c.beginPath(); c.moveTo(k, y + h); c.lineTo(k + (x + w / 2 - k) * 0.25, y); c.stroke(); }
        c.strokeStyle = "rgba(255,190,170,.35)"; for (let yy = y + 5; yy < y + h; yy += 5) { c.beginPath(); c.moveTo(x - 6 + (y + h - yy) * 0.2, yy); c.lineTo(x + w + 6 - (y + h - yy) * 0.2, yy); c.stroke(); } };
      stucco(c, 0, -74, 250, 74, "#f3e6cf", "#e2d1b4"); tiles(0, -96, 104, 24); tiles(150, -92, 104, 22);
      for (const wx of [14, 50, 176, 212]) { box(c, "#b9a07c", wx - 2, -58, 28, 40, 12); glass(c, wx, -56, 24, 36, night); box(c, "#c8432c", wx - 3, -18, 30, 4, 1); }
      // the arched entry: a tall facade with a decorative block grid
      c.fillStyle = lin(c, 0, -150, 0, 0, ["#efe1c6", "#dccaa8"]); c.beginPath(); c.moveTo(98, 0); c.lineTo(98, -118); c.quadraticCurveTo(126, -152, 154, -118); c.lineTo(154, 0); c.fill();
      c.save(); c.beginPath(); c.moveTo(102, -10); c.lineTo(102, -116); c.quadraticCurveTo(126, -146, 150, -116); c.lineTo(150, -10); c.clip();
      for (let y = -146; y < -10; y += 7) for (let x = 103 + ((y / 7) & 1) * 3; x < 150; x += 7) box(c, "rgba(150,120,80,.35)", x, y, 4.5, 4.5);
      c.restore(); c.fillStyle = "#5a3a26"; c.beginPath(); c.moveTo(114, 0); c.lineTo(114, -40); c.quadraticCurveTo(126, -56, 138, -40); c.lineTo(138, 0); c.fill(); box(c, "#c9a46a", 125, -26, 2, 6);
      shrub(c, 90, 22, 30); shrub(c, 164, 22, 30); shrub(c, 8, 18, 22); shrub(c, 240, 20, 26);
      // the pole sign: a rounded orange-and-red top with the cowboy on his horse + a green banner, a white marquee of specials
      const sx = 292; for (const px of [sx - 22, sx + 22]) box(c, lin(c, px - 3, 0, px + 3, 0, ["#8a939c", "#e1e6ea", "#8a939c"]), px - 3, -186, 6, 186);
      box(c, "#2b2f38", sx - 46, -186, 92, 64, 3); box(c, "#ffffff", sx - 43, -183, 86, 58, 2);
      ["TRY OUR", "ALAMBRE PLATE", "CABRITO PLATE", "COSTILLAS DE RES"].forEach((s, i) => say(c, s, sx, -174 + i * 14, 11, i ? "#1d1f26" : "#c8432c", { weight: 900, max: 80 }));
      box(c, "#8a939c", sx - 4, -196, 8, 10);
      c.fillStyle = "#2b2f38"; rr(c, sx - 38, -300, 76, 110, 36); c.fill(); c.fillStyle = lin(c, 0, -296, 0, -194, ["#ff8a1a", "#ff6a1a", "#d7262e"]); rr(c, sx - 35, -297, 70, 104, 33); c.fill();
      c.fillStyle = "rgba(255,255,255,.18)"; rr(c, sx - 30, -292, 26, 70, 12); c.fill();
      c.fillStyle = "#3a1d12";   // a simple cowboy-on-horse silhouette
      c.beginPath(); c.ellipse(sx + 2, -242, 17, 8, -0.05, 0, Math.PI * 2); c.fill();
      poly(c, "#3a1d12", [sx + 14, -246, sx + 26, -264, sx + 31, -260, sx + 22, -240]); ell(c, "#3a1d12", sx + 28, -262, 6, 4, -0.5);
      for (const [lx, a] of [[-11, 0.15], [-6, -0.1], [9, 0.12], [14, -0.15]]) line(c, "#3a1d12", 3.2, [sx + lx, -238, sx + lx + a * 18, -222]);
      line(c, "#3a1d12", 3, [sx - 14, -244, sx - 22, -230]);
      ell(c, "#3a1d12", sx - 2, -258, 5, 8); ell(c, "#3a1d12", sx - 1, -270, 4, 4.2); ell(c, "#3a1d12", sx - 1, -274, 10, 2.2); box(c, "#3a1d12", sx - 5, -282, 8, 8, 3);
      for (const k of [-1, 1]) { c.fillStyle = "#0a5a2a"; c.beginPath(); c.moveTo(sx + k * 34, -214); c.lineTo(sx + k * 48, -214); c.lineTo(sx + k * 43, -206); c.lineTo(sx + k * 48, -198); c.lineTo(sx + k * 34, -198); c.closePath(); c.fill(); }
      box(c, "#0f7a3a", sx - 37, -218, 74, 20, 3); say(c, "DON PEDROES", sx, -207.5, 14, "#ffffff", { weight: 900, max: 68, font: WEST });
      return;
    }
    if (n === 3) {   // O'Reillees: a green-and-white parody auto-parts store, no logo
      box(c, lin(c, 0, -140, 0, 0, ["#ffffff", "#e9edf0"]), 10, -140, 340, 140); box(c, "#0b7a3e", 10, -140, 340, 40); box(c, "#ffffff", 10, -100, 340, 4); box(c, "#0b7a3e", 10, -96, 340, 6);
      say(c, "O'REILLEES", 180, -122, 32, "#ffffff", { weight: 900, italic: true, max: 300 });
      say(c, "AUTO PARTS", 180, -86, 10, "#0b7a3e", { weight: 900, max: 200 });
      for (let x = 22; x < 340; x += 72) { if (x > 140 && x < 220) continue; box(c, "#2b2f38", x - 1, -71, 58, 50); glass(c, x, -70, 56, 48, night); }
      box(c, "#0b7a3e", 150, -78, 60, 78); glass(c, 156, -72, 48, 72, night); box(c, "#0b7a3e", 179, -72, 2, 72);
      for (let k = 0; k < 4; k++) { box(c, "#1d1f26", 30 + k * 12, -36, 10, 13, 1); box(c, "#d7262e", 32 + k * 12, -38, 2, 2); box(c, "#e1e6ea", 36 + k * 12, -38, 2, 2); }   // batteries in the window
      for (let k = 0; k < 4; k++) tire(c, 300, -6 - k * 9, 14); box(c, "#ffffff", 232, -48, 40, 16, 3); say(c, "OPEN", 252, -40, 11, "#0b7a3e", { weight: 900 });
      return;
    }
    if (n === 4) {   // Juan's Casa: a little house, a chain-link fence, the work truck with a ladder rack
      poly(c, "#4a4f5e", [40, -96, 210, -96, 180, -136, 70, -136]); poly(c, lin(c, 0, -136, 0, -96, ["#5a6070", "#3a3f4c"]), [34, -96, 216, -96, 184, -140, 66, -140]);
      box(c, lin(c, 0, -96, 0, 0, ["#9fe0e0", "#72c2c6"]), 44, -96, 162, 96); c.strokeStyle = "rgba(0,0,0,.08)"; c.lineWidth = 1; for (let y = -92; y < 0; y += 6) { c.beginPath(); c.moveTo(44, y); c.lineTo(206, y); c.stroke(); }
      for (const wx of [56, 160]) { box(c, "#ffffff", wx - 3, -74, 40, 36, 2); glass(c, wx, -71, 34, 30, true); box(c, "#ffffff", wx + 16, -71, 2, 30); }
      box(c, "#ffffff", 104, -66, 42, 66); box(c, "#7a3b2a", 110, -60, 30, 60, 2); ell(c, "#c9d0d8", 134, -30, 1.6, 1.6); box(c, "#e8edf2", 96, -70, 58, 5, 1);
      ell(c, "rgba(255,220,170,.9)", 100, -54, 2.5, 2.5);
      // the work truck
      const tx = 232; box(c, lin(c, 0, -56, 0, -10, ["#ffffff", "#c9d0d8"]), tx, -46, 120, 34, 6); c.fillStyle = lin(c, 0, -76, 0, -46, ["#ffffff", "#dfe4ea"]); rr(c, tx + 70, -76, 44, 32, 7); c.fill();
      glass(c, tx + 78, -72, 30, 18, false); line(c, "#8a939c", 2, [tx + 4, -66, tx + 66, -66]); line(c, "#8a939c", 2, [tx + 8, -66, tx + 8, -46]); line(c, "#8a939c", 2, [tx + 58, -66, tx + 58, -46]);
      box(c, "#d9a066", tx - 2, -72, 90, 4, 1); for (let k = 0; k < 9; k++) box(c, "#b98048", tx + k * 10, -72, 2, 4);
      for (const wx of [tx + 22, tx + 96]) { ell(c, "#1d1f24", wx, -10, 12, 12); ell(c, "#c9d0d8", wx, -10, 5, 5); }
      box(c, "#ff7a00", tx + 116, -40, 4, 6, 1);
      c.strokeStyle = "rgba(200,208,216,.8)"; c.lineWidth = 0.7; for (let x = 0; x < 232; x += 5) { c.beginPath(); c.moveTo(x, -24); c.lineTo(x + 5, 0); c.moveTo(x + 5, -24); c.lineTo(x, 0); c.stroke(); }
      line(c, "#9aa3ad", 2, [0, -24, 230, -24]); for (let x = 0; x < 232; x += 46) line(c, "#9aa3ad", 2.4, [x, -26, x, 0]);
      shrub(c, 24, 18, 24); box(c, "#5b6270", 18, -44, 3, 44); box(c, "#ff3d8b", 12, -52, 16, 10, 3);   // a mailbox
      return;
    }
    // Noche Caliente: the cantina at night: plum adobe, a stepped parapet, string lights, the big neon sign, swinging doors
    poly(c, lin(c, 0, -220, 0, 0, ["#6a2d5a", "#3e1c3c"]), [6, 0, 6, -182, 60, -182, 70, -200, 150, -200, 160, -220, 200, -220, 210, -200, 290, -200, 300, -182, 354, -182, 354, 0]);
    c.fillStyle = "rgba(255,255,255,.05)"; for (let y = -176; y < 0; y += 9) for (let x = 10 + ((y / 9) & 1) * 9; x < 350; x += 18) c.fillRect(x, y, 14, 6);
    rr(c, 24, -172, 312, 44, 10); c.fillStyle = "rgba(10,6,20,.85)"; c.fill();
    say(c, "NOCHE CALIENTE", 180, -150, 32, "#ff5aa5", { weight: 900, font: WEST, max: 296, glow: "#ff3d8b", blur: 16 });
    say(c, "NOCHE CALIENTE", 180, -150, 32, "#ffe3f0", { weight: 900, font: WEST, max: 296, glow: "#ff8fbf", blur: 4 });
    c.strokeStyle = "#3ee8eb"; c.shadowColor = "#00b8b0"; c.shadowBlur = 10; c.lineWidth = 2; rr(c, 28, -168, 304, 36, 8); c.stroke(); c.shadowBlur = 0;
    // a neon chile
    c.shadowColor = "#ff3d3d"; c.shadowBlur = 12; c.fillStyle = "#ff4040"; c.beginPath(); c.moveTo(300, -200); c.quadraticCurveTo(326, -200, 318, -218); c.quadraticCurveTo(312, -208, 296, -208); c.fill(); c.shadowBlur = 0; line(c, "#3ad07a", 2.4, [318, -218, 322, -224]);
    say(c, "CANTINA", 180, -208, 12, "#3ee8eb", { weight: 900, glow: "#00b8b0", blur: 8 });
    // neon cowboy boots on both sides of the door
    for (const bx of [58, 302]) { c.shadowColor = "#3ee8eb"; c.shadowBlur = 10; c.strokeStyle = "#3ee8eb"; c.lineWidth = 2.2; c.lineJoin = "round";
      c.beginPath(); c.moveTo(bx - 8, -128); c.lineTo(bx + 4, -128); c.lineTo(bx + 4, -104); c.quadraticCurveTo(bx + 18, -102, bx + 20, -94); c.lineTo(bx - 4, -94); c.lineTo(bx - 4, -90); c.lineTo(bx - 9, -90); c.lineTo(bx - 9, -104); c.closePath(); c.stroke();
      line(c, "#ff8fbf", 1.6, [bx - 6, -116, bx + 2, -112]); c.shadowBlur = 0; }
    // the swinging doors with warm light behind
    box(c, lin(c, 0, -70, 0, 0, ["#ffb46a", "#ff7a3a"]), 152, -70, 56, 70); for (const dx of [154, 181]) { box(c, "#7a3b2a", dx, -52, 25, 30, 3); line(c, "rgba(0,0,0,.35)", 1, [dx + 4, -46, dx + 21, -46, dx + 21, -28, dx + 4, -28, dx + 4, -46]); }
    for (const wx of [40, 260]) { box(c, "#1d1020", wx - 3, -68, 66, 44, 4); glass(c, wx, -65, 60, 38, true); }
    say(c, "COLD ONES", 70, -46, 11, "#4a1530", { weight: 900, max: 56 }); say(c, "LIVE CONJUNTO", 290, -46, 9.5, "#4a1530", { weight: 900, max: 56 });
    // string lights along the parapet
    c.strokeStyle = "#2b1d2b"; c.lineWidth = 0.8; c.beginPath(); c.moveTo(6, -184); for (let x = 6; x <= 354; x += 29) c.quadraticCurveTo(x + 14.5, -174, x + 29, -184); c.stroke();
    for (let x = 12, i = 0; x < 352; x += 9.6, i++) { const col = ["#ff3d8b", "#3ee8eb", "#ff8a00", "#ffffff", "#7dff6a"][i % 5], y = -184 + Math.abs(Math.sin(((x - 6) / 29) * Math.PI)) * 9 * 0.9;
      c.shadowColor = col; c.shadowBlur = 6; ell(c, col, x, y + 2, 2, 2.6); } c.shadowBlur = 0;
    shrub(c, 140, 18, 26, "#2a6b46"); shrub(c, 222, 18, 26, "#2a6b46");
    for (const bx of [16, 336]) { box(c, "#5b6270", bx, -62, 3, 62); ell(c, "rgba(255,214,160,.95)", bx + 1.5, -64, 4, 4); }
  }

  // ================= v49.5 skins: torso + head for each (inside juan()'s torso frame: hips at 0,0, facing right) =================
  // Original parodies drawn from scratch, no real names, faces or logos. Colors and shapes follow the concept art in
  // screenshots/skin-concepts/ loosely.
  function juanFace(c, X, Y, sk, sk2, hi, mustache) {   // the classic face, re-used under open helmets
    box(c, sk2, -2, -26, 6, 5, 2);
    ell(c, lin(c, X - 6, Y - 6, X + 8, Y + 8, [hi, sk, sk2]), X + 0.5, Y, 8, 8.6);
    ell(c, sk2, X - 3.5, Y + 0.5, 1.8, 2.6); ell(c, "#1b120c", X + 4.4, Y - 1.2, 1.05, 1.4); ell(c, sk2, X + 8.2, Y + 1.2, 1.7, 1.9);
    if (mustache) { c.fillStyle = "#24160e"; c.beginPath(); c.moveTo(X + 2.8, Y + 3.7); c.quadraticCurveTo(X + 6, Y + 2, X + 9.4, Y + 3.8); c.quadraticCurveTo(X + 6.4, Y + 6, X + 2.8, Y + 3.7); c.fill(); line(c, "#7a3b2a", 0.9, [X + 4.6, Y + 6.6, X + 7, Y + 6.2]); }
  }
  function skinBody(c, k, P) {   // P: the jump pulse 0..1 (0 = no jump FX)
    const X = 2.5, Y = -31.5;
    if (k === "jefe") {   // a generic cartoon politician: navy suit, white shirt, a long red tie, a big blond swoop (no real person)
      c.fillStyle = lin(c, -11, -24, 11, 0, ["#2c3d7a", "#1c2a58"]); rr(c, -11.5, -24, 23, 23.5, 6.5); c.fill();
      c.fillStyle = "#ffffff"; c.beginPath(); c.moveTo(-4.5, -24); c.lineTo(5.5, -24); c.lineTo(0.5, -12); c.closePath(); c.fill();
      c.save(); if (P) { c.translate(0.5, -21.5); c.rotate(P * 2.5); c.translate(-0.5, 21.5); }   // jump: the tie flaps up over his shoulder
      c.fillStyle = "#d7262e"; c.beginPath(); c.moveTo(-0.9, -21.5); c.lineTo(1.9, -21.5); c.lineTo(3, -2.5); c.lineTo(0.5, 0.6); c.lineTo(-2, -2.5); c.closePath(); c.fill(); c.restore(); box(c, "#a51d1d", -1.3, -23.2, 3.6, 2.6, 1);
      line(c, "#13204a", 1.1, [-4.5, -24, -1.2, -13, -3, -5]); line(c, "#13204a", 1.1, [5.5, -24, 2.4, -13, 4.5, -5]); ell(c, "#ffffff", 7.2, -18.5, 1.6, 0.7);
      juanFace(c, X, Y, "#efbb94", "#d39b72", "#f8d2b4", false);
      line(c, "#8a4a3a", 1, [X + 3.6, Y + 4.6, X + 6.4, Y + 5.2, X + 8.2, Y + 4.2]); line(c, "#c99a3f", 1.2, [X + 2.4, Y - 4.4, X + 6.4, Y - 4.8]);
      c.save(); if (P) { c.translate(X - 5, Y - 2); c.rotate(-P * 0.55); c.scale(1, 1 + P * 0.35); c.translate(-(X - 5), -(Y - 2)); }   // jump: the swoop flips up
      c.fillStyle = lin(c, X - 9, Y - 15, X + 12, Y - 4, ["#fdebb0", "#f2cc66", "#d9a640"]); c.beginPath(); c.moveTo(X - 8.6, Y + 1.5);
      c.quadraticCurveTo(X - 11, Y - 9.5, X - 3, Y - 13); c.quadraticCurveTo(X + 6.5, Y - 16.5, X + 13, Y - 9.5); c.quadraticCurveTo(X + 9.5, Y - 10.2, X + 8, Y - 7.4);
      c.quadraticCurveTo(X + 2.5, Y - 8.6, X - 1.5, Y - 5.2); c.quadraticCurveTo(X - 4.5, Y - 2.2, X - 5, Y + 2.2); c.closePath(); c.fill();
      line(c, "rgba(170,115,30,.55)", 0.8, [X - 5, Y - 9.5, X + 3, Y - 13, X + 10.5, Y - 10.2]); line(c, "rgba(255,255,255,.6)", 0.9, [X - 3, Y - 11.6, X + 3.5, Y - 13.6]); c.restore();
      return;
    }
    if (k === "raspa") {   // v49.12 Robo-Raspa: a turquoise + white raspa-cart robot: a striped cart awning across the chest, a raspa cup badge, ear pods,
      // and a rainbow snow-cone dome for a helmet (with a spoon-straw). Jump: fizz jets from his boots and palms (jumpFx)
      c.save(); rr(c, -11.5, -24, 23, 23.5, 6); c.fillStyle = lin(c, -11, -24, 11, 0, ["#ffffff", "#e6f2f5", "#bcd3da"]); c.fill(); c.clip();
      for (let i = 0; i < 5; i++) { const x = -11.5 + i * 4.6; c.fillStyle = i % 2 ? "#ffffff" : "#1fb8bf"; c.beginPath(); c.moveTo(x, -24); c.lineTo(x + 4.6, -24); c.lineTo(x + 4.6, -19.6); c.quadraticCurveTo(x + 2.3, -16.6, x, -19.6); c.closePath(); c.fill(); }
      box(c, "#1fb8bf", -11.5, -6.4, 23, 3.4); line(c, "#ffffff", 0.8, [-11.5, -4.7, 11.5, -4.7]); c.restore();
      c.save(); c.beginPath(); c.ellipse(0.5, -13.4, 4.6, 3.8, 0, Math.PI, 0); c.closePath(); c.clip();   // the badge: a raspa in a paper cup, rainbow syrup
      ["#ff3d8b", "#ff8a00", "#ffd23a", "#3ee8eb"].forEach((col, i) => box(c, col, -4.1 + i * 2.3, -17.4, 2.4, 4.2)); c.restore();
      for (const [x, y] of [[-1.6, -15.6], [2.6, -14.8], [0.4, -16.6]]) ell(c, "rgba(255,255,255,.85)", x, y, 0.45, 0.45);
      c.fillStyle = "#f4f7fa"; c.beginPath(); c.moveTo(-4.2, -13.4); c.lineTo(5.2, -13.4); c.lineTo(3.6, -7.6); c.lineTo(-2.6, -7.6); c.closePath(); c.fill();
      c.strokeStyle = "#168c92"; c.lineWidth = 0.6; c.stroke(); line(c, "#1fb8bf", 1, [-3.4, -10.8, 4.4, -10.8]);
      for (const [x, y] of [[-9.6, -15], [-9.6, -9.5], [10.6, -15], [10.6, -9.5]]) ell(c, "#8fb8c2", x, y, 0.7, 0.7);
      box(c, "#d5dbe1", -2, -26, 6, 5, 2);
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true);
      c.save(); c.beginPath(); c.ellipse(X + 0.5, Y - 4.2, 10.2, 10.6, 0, Math.PI, 0); c.closePath(); c.clip();   // the snow-cone dome: rainbow syrup stripes over the ice
      ["#ff3d8b", "#ff8a00", "#ffd23a", "#7cc860", "#3ee8eb"].forEach((col, i) => box(c, col, X - 10 + i * 4.2, Y - 16, 4.4, 12.5));
      c.fillStyle = lin(c, 0, Y - 15, 0, Y - 4, ["rgba(255,255,255,.45)", "rgba(255,255,255,0)"]); c.fillRect(X - 10, Y - 16, 21, 12.5);
      for (const [x, y] of [[-6, -8], [-2, -12], [2.5, -9], [6.5, -11], [8, -6.5], [-8, -5.6], [0, -6]]) ell(c, "rgba(255,255,255,.9)", X + x, Y + y, 0.6, 0.6);
      c.restore();
      line(c, "#f4f7fa", 1.3, [X + 3.6, Y - 13, X + 6.4, Y - 18.6]); box(c, "#f4f7fa", X + 5.4, Y - 19.6, 3, 1.8, 0.8);   // the spoon-straw
      box(c, "#f4f7fa", X - 10.2, Y - 5.8, 21.4, 3.2, 1.5); line(c, "#1fb8bf", 0.9, [X - 9.6, Y - 4.2, X + 10.6, Y - 4.2]);   // the cup rim
      line(c, "#24160e", 1.2, [X + 2.4, Y - 1.9, X + 6.4, Y - 2.2]);
      ell(c, "#1fb8bf", X - 6.6, Y + 0.6, 3.4, 3.4); ell(c, "#ffffff", X - 6.6, Y + 0.6, 1.5, 1.5); ell(c, "#ff3d8b", X - 6.6, Y + 0.6, 0.6, 0.6);
      return;
    }
    if (k === "payaso") {   // v49.12 Payaso de la Feria: a Fiesta rodeo clown: Juan's own face with a red nose and rosy cheeks, a rainbow curly wig,
      // turquoise + pink checkered overalls over a yellow shirt, a big pink polka-dot bow tie. Jump: confetti + a cascarón cracking open (jumpFx)
      c.fillStyle = lin(c, -11, -24, 11, 0, ["#ffe680", "#ffd23a", "#e8b830"]); rr(c, -11, -24, 22, 23.5, 6); c.fill();
      c.save(); rr(c, -8.6, -16.6, 18.2, 17.2, 3); c.clip();
      for (let i = 0; i < 6; i++) for (let j = 0; j < 5; j++) box(c, (i + j) % 2 ? "#ff3d8b" : "#1fb8bf", -8.6 + i * 3.6, -16.6 + j * 3.6, 3.6, 3.6);
      c.restore(); c.strokeStyle = "#13777c"; c.lineWidth = 0.7; rr(c, -8.6, -16.6, 18.2, 17.2, 3); c.stroke();
      box(c, "#ffffff", -2.6, -12, 6.2, 4.6, 1); line(c, "#ff3d8b", 0.7, [-2.2, -10.6, 3.2, -10.6]);   // the bib pocket
      line(c, "#1fb8bf", 2.6, [-6.8, -16.2, -8.4, -24]); line(c, "#1fb8bf", 2.6, [7.8, -16.2, 9.2, -24]);
      ell(c, "#ffd23a", -6.6, -15.2, 1.3, 1.3); ell(c, "#ffd23a", 7.6, -15.2, 1.3, 1.3);
      box(c, "#a5683f", -2, -26, 6, 5, 2);
      for (const [x, y, r, col] of [[-7.4, -6.4, 4.2, "#ff3d8b"], [-2.6, -9.8, 4.2, "#ff8a00"], [2.8, -10.2, 3.9, "#ffd23a"], [7.4, -7.6, 3.3, "#7cc860"], [-9.8, -1, 3.8, "#3ee8eb"], [-9.4, 4.8, 3.2, "#ff3d8b"]]) {   // the wig, behind the face
        ell(c, col, X + x, Y + y, r, r); c.strokeStyle = "rgba(0,0,0,.18)"; c.lineWidth = 0.6; c.beginPath(); c.arc(X + x + 0.4, Y + y + 0.3, r * 0.5, 0.4, 4.6); c.stroke(); }
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true);
      line(c, "#24160e", 1.2, [X + 2.4, Y - 4, X + 6.4, Y - 4.6]);
      ell(c, "rgba(255,90,140,.5)", X + 1.4, Y + 2.4, 1.9, 1.5);   // a rosy cheek
      c.fillStyle = "#1fb8bf"; c.beginPath(); c.moveTo(X + 4.4, Y + 0.6); c.lineTo(X + 5.2, Y + 2.6); c.lineTo(X + 3.6, Y + 2.6); c.closePath(); c.fill();   // a little painted teardrop under the eye
      ell(c, "#e0243a", X + 8.8, Y + 0.8, 2.7, 2.7); ell(c, "rgba(255,255,255,.75)", X + 8, Y - 0.1, 0.8, 0.7);   // the red nose
      for (const [x, y, r, col] of [[-1, -12.4, 3.4, "#3ee8eb"], [4.6, -12.6, 3, "#ff3d8b"], [9.6, -9.6, 2.5, "#ff8a00"]]) ell(c, col, X + x, Y + y, r, r);   // the wig's front curls
      c.fillStyle = "#ff3d8b"; c.beginPath(); c.moveTo(0.6, -22.4); c.lineTo(-7.6, -26.6); c.lineTo(-7, -18.2); c.closePath(); c.moveTo(0.6, -22.4); c.lineTo(8.8, -26.6); c.lineTo(8.2, -18.2); c.closePath(); c.fill();   // the bow tie
      ell(c, "#d42a72", 0.6, -22.4, 2.2, 2.4); for (const [x, y] of [[-5, -23.6], [-4.6, -20.4], [6.2, -23.6], [5.8, -20.4]]) ell(c, "#ffffff", x, y, 0.8, 0.8);
      return;
    }
    if (k === "astro") {   // v49.12 Astro Juan: a white + turquoise retro astronaut, Juan's own face and mustache inside a round clear bubble helmet,
      // a chest control box, a Fiesta-stripe patch, a backpack (drawn in juan()). Jump: the backpack jet
      c.fillStyle = lin(c, -11, -24, 11, 0, ["#ffffff", "#e8eef2", "#c3ccd4"]); rr(c, -11.5, -24, 23, 23.5, 6); c.fill();
      line(c, "#c3ccd4", 0.8, [-11, -7.5, 11, -7.5]); box(c, "#1fb8bf", -11.5, -4, 23, 3.4, 1);
      box(c, "#2d3748", -3, -16.6, 10, 7, 1.6); for (const [x, col] of [[-1, "#ff3d8b"], [2, "#ff8a00"], [5, "#ffd23a"]]) ell(c, col, x, -14.6, 0.9, 0.9);
      box(c, "#3ee8eb", -1.6, -12.2, 7.4, 1.6, 0.6);   // the control box
      c.save(); rr(c, -10, -21, 6, 7, 1.6); c.clip(); ["#3ee8eb", "#ff3d8b", "#ff8a00", "#ffd23a"].forEach((col, i) => box(c, col, -10, -21 + i * 1.75, 6, 1.8)); c.restore();   // the Fiesta-stripe patch
      c.strokeStyle = "#9aa3ad"; c.lineWidth = 1.2; c.beginPath(); c.moveTo(-1, -9.4); c.bezierCurveTo(-7, -6, -10, -12, -8, -19); c.stroke();   // the air hose
      box(c, "#c9d0d8", -6.4, -27.4, 14, 4.6, 2); line(c, "#1fb8bf", 1, [-5.8, -25.1, 7, -25.1]);   // the neck ring
      ell(c, "#24160e", X - 2.2, Y - 0.5, 8, 8.2);
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true); line(c, "#24160e", 1.2, [X + 2.4, Y - 4, X + 6.4, Y - 4.3]);
      ell(c, "rgba(170,230,245,.26)", X + 0.8, Y - 0.6, 12.6, 12.4);   // the bubble helmet
      c.strokeStyle = "rgba(232,246,250,.95)"; c.lineWidth = 1.5; c.beginPath(); c.ellipse(X + 0.8, Y - 0.6, 12.6, 12.4, 0, 0, Math.PI * 2); c.stroke();
      line(c, "rgba(255,255,255,.85)", 1.6, [X - 8, Y - 5.5, X - 6, Y - 9.4, X - 2, Y - 11.4]); ell(c, "rgba(255,255,255,.8)", X + 8, Y - 7.4, 1, 1);
      return;
    }
    if (k === "lowrider") {   // v49.12 El Lowrider: candy purple + teal panels like a custom car, a chrome wire-wheel hubcap on the chest, gold pinstripes,
      // a chrome bumper belt, a closed helmet with a tinted windshield visor, headlight cheeks and a chrome grille mouth. Jump: a hydraulic hop (jumpFx)
      c.fillStyle = lin(c, -14, -25, 14, 0, ["#c78bff", "#8a3ad0", "#4a1a80"]); c.beginPath(); c.moveTo(-14.5, -20); c.quadraticCurveTo(-14.5, -25, -9.5, -25); c.lineTo(10.5, -25);
      c.quadraticCurveTo(15.5, -25, 15.5, -20); c.lineTo(11, 0.4); c.lineTo(-10, 0.4); c.closePath(); c.fill();   // wide shoulders, a narrow waist
      c.fillStyle = lin(c, 0, -12, 0, 0, ["#5ff3e0", "#1fb8bf", "#0f6a70"]); c.beginPath(); c.moveTo(-12.4, -11); c.lineTo(13.4, -11); c.lineTo(11, 0.4); c.lineTo(-10, 0.4); c.closePath(); c.fill();   // the teal lower panel
      line(c, "#e8edf2", 1.1, [-12.4, -11, 13.4, -11]);
      line(c, "#ffd27a", 0.6, [-11.6, -21.6, -8, -23.4, -5.6, -20.4, -8.8, -18.6]); line(c, "#ffd27a", 0.6, [12.6, -21.6, 9, -23.4, 6.6, -20.4, 9.8, -18.6]);   // pinstripe curls
      line(c, "#ffd27a", 0.5, [-9.4, -8.6, -3, -7.4, 4, -7.4, 10.4, -8.6]);
      c.fillStyle = lin(c, -6, -20, 6, -7, ["#ffffff", "#c9d0d8", "#7c858f"]); c.beginPath(); c.arc(0.5, -15.6, 6.4, 0, Math.PI * 2); c.fill();   // the hubcap
      c.strokeStyle = "#5b6270"; c.lineWidth = 0.5; c.beginPath(); for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; c.moveTo(0.5, -15.6); c.lineTo(0.5 + Math.cos(a) * 5.6, -15.6 + Math.sin(a) * 5.6); } c.stroke();
      c.strokeStyle = "#e8edf2"; c.lineWidth = 0.9; c.beginPath(); c.arc(0.5, -15.6, 5.8, 0, Math.PI * 2); c.stroke();
      c.fillStyle = "#ffd27a"; c.beginPath(); c.moveTo(-2.8, -16.4); c.lineTo(3.8, -14.8); c.lineTo(3.8, -16.4); c.lineTo(-2.8, -14.8); c.closePath(); c.fill(); ell(c, "#c99a3f", 0.5, -15.6, 1.2, 1.2);   // the spinner
      box(c, lin(c, 0, -4, 0, -0.5, ["#ffffff", "#9aa3ad"]), -11, -4, 22.5, 3.6, 1.6);   // the chrome bumper belt
      box(c, "#c9d0d8", -3, -30.5, 8, 7, 2);
      const Y = -34;
      c.fillStyle = lin(c, X - 12, Y - 13, X + 12, Y + 11, ["#c78bff", "#8a3ad0", "#4a1a80"]); rr(c, X - 11, Y - 12.5, 23.5, 23, 8); c.fill();
      c.fillStyle = "#e8edf2"; c.beginPath(); c.moveTo(X - 6, Y - 12.2); c.quadraticCurveTo(X + 1, Y - 17.2, X + 9, Y - 12); c.lineTo(X + 1, Y - 11.2); c.closePath(); c.fill();   // a chrome hood-ornament fin
      line(c, "#ffd27a", 0.6, [X - 9.6, Y - 3, X - 6, Y - 7.8, X - 3, Y - 4, X - 6, Y + 1]);
      c.fillStyle = lin(c, X + 2, Y - 9, X + 12, Y - 1, ["#5ff3e0", "#1f8a92", "#123e4a"]); c.beginPath(); c.moveTo(X + 0.5, Y - 8.6); c.lineTo(X + 12.6, Y - 8.6); c.lineTo(X + 13, Y - 2.2); c.lineTo(X - 0.5, Y - 2.2); c.closePath(); c.fill();   // the windshield visor
      line(c, "rgba(255,255,255,.8)", 0.9, [X + 3, Y - 7.4, X + 6.4, Y - 3.6]); line(c, "#e8edf2", 0.8, [X + 0.5, Y - 8.6, X + 12.6, Y - 8.6, X + 13, Y - 2.2, X - 0.5, Y - 2.2, X + 0.5, Y - 8.6]);
      box(c, lin(c, 0, Y, 0, Y + 8, ["#ffffff", "#c9d0d8", "#7c858f"]), X + 2.4, Y + 0.4, 10.6, 7.6, 2.6);   // the grille mouth
      for (let i = 0; i < 5; i++) line(c, "#2b2f36", 0.9, [X + 4.2 + i * 1.8, Y + 1.8, X + 4.2 + i * 1.8, Y + 6.6]);
      c.save(); c.shadowColor = "#ffe9a0"; c.shadowBlur = 6; ell(c, "#fff4c6", X + 0.4, Y + 3.2, 1.8, 1.8); ell(c, "#fff4c6", X + 14.2, Y + 3.2, 1.3, 1.6); c.restore();   // headlights
      return;
    }
    if (k === "mariachi") {   // v49.12 Mariachi Neón: a black charro jacket with turquoise + pink neon piping and silver buttons over a white shirt,
      // a wide pink moño, a black sombrero with a glowing neon rim. Jump: a neon trail (jumpFx)
      box(c, "#f4f6f8", -6, -24, 13, 24, 2);   // the white shirt
      c.fillStyle = lin(c, -12, -24, 12, 0, ["#2b2b36", "#16161e"]);
      c.beginPath(); c.moveTo(-12, -22.4); c.lineTo(-4, -24); c.lineTo(-2.4, -13); c.quadraticCurveTo(-6, -8.4, -11.6, -8.6); c.closePath(); c.fill();   // the short bolero jacket
      c.beginPath(); c.moveTo(6, -24); c.lineTo(12.4, -22); c.lineTo(12.2, -8.6); c.quadraticCurveTo(6.6, -8.4, 3.6, -13); c.closePath(); c.fill();
      box(c, "#16161e", -11.6, -8.6, 23.8, 9, 3);
      box(c, "#ff3d8b", -11.6, -6, 23.8, 3, 1);   // a pink faja sash
      c.save(); c.shadowColor = "#3ee8eb"; c.shadowBlur = 5;
      line(c, "#3ee8eb", 1, [-4, -24, -2.4, -13]); c.strokeStyle = "#3ee8eb"; c.beginPath(); c.moveTo(-2.4, -13); c.quadraticCurveTo(-6, -8.4, -11.6, -8.6); c.stroke();
      line(c, "#3ee8eb", 1, [6, -24, 3.6, -13]); c.beginPath(); c.moveTo(3.6, -13); c.quadraticCurveTo(6.6, -8.4, 12.2, -8.6); c.stroke(); c.shadowColor = "#ff3d8b";
      c.strokeStyle = "#ff6aa8"; c.lineWidth = 0.7; c.beginPath(); c.moveTo(-10.6, -20); c.quadraticCurveTo(-7, -18, -9, -14.6); c.quadraticCurveTo(-11, -12.4, -8, -11.2); c.stroke();
      c.beginPath(); c.moveTo(11, -20); c.quadraticCurveTo(7.6, -18, 9.4, -14.6); c.quadraticCurveTo(11.2, -12.4, 8.6, -11.2); c.stroke(); c.restore();
      for (const y of [-20.6, -17.2, -13.8]) { ell(c, "#e8edf2", -5, y, 0.75, 0.75); ell(c, "#e8edf2", 6.2, y, 0.75, 0.75); }   // the silver botonadura
      box(c, "#a5683f", -2, -26, 6, 5, 2);
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true);
      c.fillStyle = "#1b120c"; c.beginPath(); c.ellipse(X - 0.4, Y - 3.6, 8.6, 6.4, -0.1, Math.PI * 0.9, Math.PI * 2.0); c.fill();
      line(c, "#24160e", 1.2, [X + 2.4, Y - 4, X + 6.4, Y - 4.3]);
      c.save(); c.shadowColor = "#ff3d8b"; c.shadowBlur = 5; c.fillStyle = "#ff3d8b"; c.beginPath();   // the wide moño
      c.moveTo(0.6, -21.2); c.quadraticCurveTo(-6, -25.2, -11, -23.4); c.quadraticCurveTo(-9.4, -21.2, -11, -18.4); c.quadraticCurveTo(-6, -16.8, 0.6, -21.2);
      c.quadraticCurveTo(7, -25.2, 12.2, -23.4); c.quadraticCurveTo(10.6, -21.2, 12.2, -18.4); c.quadraticCurveTo(7, -16.8, 0.6, -21.2); c.fill(); c.restore();
      ell(c, "#d42a72", 0.6, -21.2, 2, 2.1);
      const sY = Y - 8.6;   // the sombrero: a tall black crown with a pink neon band, a wide brim with a turquoise neon rim
      c.fillStyle = lin(c, 0, sY - 14, 0, sY, ["#3a3a46", "#16161e"]); c.beginPath(); c.moveTo(X - 7, sY); c.quadraticCurveTo(X - 6.6, sY - 14.6, X + 0.8, sY - 15); c.quadraticCurveTo(X + 8.2, sY - 14.6, X + 8.6, sY); c.closePath(); c.fill();
      c.save(); c.shadowColor = "#ff3d8b"; c.shadowBlur = 6; line(c, "#ff6aa8", 1.6, [X - 6.6, sY - 3.2, X + 8.2, sY - 3.2]); c.restore();
      for (const x of [-4, 0.8, 5.6]) ell(c, "#e8edf2", X + x, sY - 8, 0.7, 0.7);
      c.fillStyle = lin(c, 0, sY - 4, 0, sY + 4, ["#2b2b36", "#0e0e14"]); c.beginPath(); c.ellipse(X + 0.8, sY + 0.4, 20, 4.2, 0, 0, Math.PI * 2); c.fill();
      c.save(); c.shadowColor = "#3ee8eb"; c.shadowBlur = 8; c.strokeStyle = "#3ee8eb"; c.lineWidth = 1.2; c.beginPath(); c.ellipse(X + 0.8, sY + 0.4, 20, 4.2, 0, 0, Math.PI * 2); c.stroke(); c.restore();
      return;
    }
    if (k === "cowboy") {   // v49.6 Cocaine Cowboy: an 80s Miami look, our own: a white suit over a mint shirt, a beige cowboy hat. Jump: a hat tip
      c.fillStyle = lin(c, -11, -24, 11, 0, ["#c8f5e4", "#8fdcc4"]); rr(c, -11.5, -24, 23, 23.5, 6); c.fill();
      c.fillStyle = lin(c, -12, -24, 12, 0, ["#ffffff", "#f4f1ea", "#d9d4c8"]);
      c.beginPath(); c.moveTo(-12.2, -22.5); c.lineTo(-3.6, -24); c.lineTo(-1.2, -10); c.lineTo(-2.6, 0.4); c.lineTo(-12.2, 0.4); c.closePath(); c.fill();
      c.beginPath(); c.moveTo(6, -24); c.lineTo(12.2, -22); c.lineTo(12.2, 0.4); c.lineTo(5.2, 0.4); c.lineTo(3.4, -10); c.closePath(); c.fill();
      line(c, "#bfb8a8", 1.1, [-3.6, -24, -1.2, -10, -2.6, 0.4]); line(c, "#bfb8a8", 1.1, [6, -24, 3.4, -10, 5.2, 0.4]); box(c, "#ff8fbf", 7.4, -19, 3.4, 1.6, 0.6);   // lapels + a pink pocket square
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true);
      c.save(); if (P) { c.translate(X, Y - 9 - P * 3.5); c.rotate(P * 0.28); c.translate(-X, -(Y - 9)); }   // jump: he tips the hat (a little lift + a forward tilt)
      c.translate(X + 0.5, Y - 7); c.scale(1.22, 1.22); c.translate(-(X + 0.5), -(Y - 7));   // a big, readable cattleman hat
      c.fillStyle = lin(c, 0, Y - 25, 0, Y - 8, ["#f0dfb8", "#d8bf8e", "#c4a676"]); c.beginPath();   // the tall crown: a center crease + a front pinch
      c.moveTo(X - 7.6, Y - 8.5); c.lineTo(X - 7.2, Y - 20.5); c.quadraticCurveTo(X - 5.6, Y - 24.4, X - 2, Y - 23.6); c.quadraticCurveTo(X + 1, Y - 21, X + 3.6, Y - 23.4);
      c.quadraticCurveTo(X + 7.4, Y - 23.6, X + 7.8, Y - 19.6); c.lineTo(X + 8.8, Y - 8.5); c.closePath(); c.fill();
      line(c, "#a88a5a", 1, [X - 4.6, Y - 22.6, X + 0.8, Y - 20.6, X + 4.6, Y - 22.4]);   // the crease
      c.fillStyle = "rgba(120,90,50,.35)"; c.beginPath(); c.ellipse(X + 6.2, Y - 17.6, 1.4, 3.6, 0.2, 0, Math.PI * 2); c.fill();   // the front pinch
      box(c, "#4a2a12", X - 7.6, Y - 12.6, 16.4, 3.6, 0.6); box(c, "#c9a24a", X + 4.6, Y - 12.2, 2.2, 2.8, 0.6);   // a dark brown band + a little buckle
      c.fillStyle = lin(c, 0, Y - 16, 0, Y - 5, ["#ead6aa", "#c9ad7c", "#b09062"]); c.beginPath();   // the wide brim, both sides curled up
      c.moveTo(X - 19, Y - 16.5); c.quadraticCurveTo(X - 15, Y - 8.4, X - 7, Y - 8.2); c.quadraticCurveTo(X + 1, Y - 7.4, X + 9, Y - 8.2); c.quadraticCurveTo(X + 17, Y - 8.4, X + 21, Y - 16.5);
      c.quadraticCurveTo(X + 19.6, Y - 6.6, X + 9, Y - 4.8); c.quadraticCurveTo(X + 1, Y - 3.6, X - 7, Y - 4.8); c.quadraticCurveTo(X - 17.6, Y - 6.6, X - 19, Y - 16.5); c.closePath(); c.fill();
      c.strokeStyle = "#9c7c4e"; c.lineWidth = 0.8; c.stroke();
      c.restore();
      return;
    }
    if (k === "largo") {   // v49.12 Juan Largo: Juan stretched into a ridiculously tall 70s streetball player: a Fiesta jersey (turquoise, pink + orange trim,
      // our own "210" for the 210 area code, no team, no real player), an afro with a pink headband. Jump: the dribble turns into an alley-oop (hoop())
      c.fillStyle = lin(c, -9, -44, 9, 0, ["#7ff6f8", "#1fb8bf", "#168c92"]); rr(c, -8.5, -44, 17, 44.5, 5); c.fill();
      line(c, "#ff3d8b", 1.8, [-3.2, -44, 0.8, -37.5, 4.8, -44]); line(c, "#ff8a00", 0.9, [-2.4, -44, 0.8, -39, 4, -44]);   // the V-neck
      line(c, "#ff3d8b", 1.4, [5.2, -44, 7.2, -36, 8.4, -31]); line(c, "#ff3d8b", 1.4, [-4.6, -44, -7, -36, -8.4, -31]);   // the arm holes
      box(c, "#ff8a00", -8.5, -31, 1.6, 27, 0.8); box(c, "#ff3d8b", -6.9, -31, 1.1, 27, 0.5);   // side stripes
      c.save(); c.font = "900 8px " + SANS; c.textAlign = "center"; c.textBaseline = "middle"; c.lineJoin = "round";
      c.strokeStyle = "#ff3d8b"; c.lineWidth = 2; c.strokeText("210", 1, -25); c.fillStyle = "#ffffff"; c.fillText("210", 1, -25); c.restore();
      box(c, "#ff3d8b", -9, -3.4, 18, 3.4, 1); line(c, "#ff8a00", 0.8, [-9, -1.7, 9, -1.7]);
      c.save(); c.translate(0, -20);   // Juan's own face, mustache and all, way up on top of the long torso
      ell(c, "#1b120c", X - 1, Y - 3.4, 10.4, 8.6);   // the afro, behind the face
      juanFace(c, X, Y, "#c68a5e", "#a5683f", "#d39a6c", true);
      c.fillStyle = "#1b120c"; c.beginPath(); c.ellipse(X - 0.6, Y - 4.4, 9.8, 6.4, 0, Math.PI * 0.95, Math.PI * 2.02); c.fill();
      box(c, "#ff3d8b", X - 9.2, Y - 6.2, 18.8, 3, 1.3); line(c, "#3ee8eb", 0.8, [X - 9, Y - 4.7, X + 9.4, Y - 4.7]);   // the headband
      c.restore();
    }
  }
  function dribble(c, T, bx, by) {   // Juan Largo's basketball (plain orange, black seams), spinning as it bounces
    const R = 5.2; c.save(); c.translate(bx, by); c.rotate(T * 6);
    ell(c, lin(c, -R, -R, R, R, ["#ff9d52", "#e8742c", "#b8501a"]), 0, 0, R, R);
    c.strokeStyle = "#3a1c0c"; c.lineWidth = 0.7; c.beginPath(); c.moveTo(-R, 0); c.lineTo(R, 0); c.moveTo(0, -R); c.lineTo(0, R);
    c.moveTo(-R * 0.55, -R * 0.84); c.quadraticCurveTo(-R * 0.1, 0, -R * 0.55, R * 0.84); c.moveTo(R * 0.55, -R * 0.84); c.quadraticCurveTo(R * 0.1, 0, R * 0.55, R * 0.84); c.stroke(); c.restore();
  }
  // ---- v49.5 jump FX: short, cheap, purely visual (the hitbox never changes); none with reduce motion
  const FIZZ = ["#3ee8eb", "rgba(62,232,235,0)", "#ffffff", "#ff8ad0"], PACK = ["#ff8a00", "rgba(255,138,0,0)", "#fff4d6", "#ffd27a"], UFOJ = ["#3a8bff", "rgba(58,139,255,0)", "#ffffff", "#ff8a00"];
  function jet(c, x, y, len, w, T, cols, tilt = 0) {   // a flickering flame pointing down from (x, y): outer glow + hot core
    const L = len * (0.82 + 0.18 * Math.sin(T * 57 + x * 3));
    const flame = (ww, ll, a, b) => { c.fillStyle = lin(c, x, y, x, y + ll, [a, b]); c.beginPath(); c.moveTo(x - ww, y); c.quadraticCurveTo(x - ww * 0.7, y + ll * 0.55, x + tilt * ll, y + ll); c.quadraticCurveTo(x + ww * 0.7, y + ll * 0.55, x + ww, y); c.closePath(); c.fill(); };
    flame(w, L, cols[0], cols[1]); flame(w * 0.55, L * 0.62, cols[2], cols[3]);
  }
  function hoop(T, ja, shx, shy, UA, FA) {   // Juan Largo's ball + dribbling arm: nonstop dribble; on a jump an alley-oop (toss, catch overhead, slam)
    const R = 5.2, top = shy + 43, AO = 0.8;
    const ik = (tx, ty) => { let vx = tx - shx, vy = ty - shy, d = Math.hypot(vx, vy) || 1; const m = UA + FA - 0.4; if (d > m) { vx *= m / d; vy *= m / d; d = m; }
      const th = Math.atan2(vx, vy), al = Math.acos(Math.max(-1, Math.min(1, (UA * UA + d * d - FA * FA) / (2 * UA * d)))), a = th - al;
      const ex = shx + Math.sin(a) * UA, ey = shy + Math.cos(a) * UA; return [a, Math.atan2(shx + vx - ex, shy + vy - ey) - a]; };
    if (ja < AO) {
      const u = ja / AO;
      if (u < 0.62) { const v = u / 0.62, x0 = shx + 11, y0 = top + R, x1 = shx + 24, y1 = shy - 90, x2 = shx + 7, y2 = shy - 44 + R;
        return { bx: (1 - v) * (1 - v) * x0 + 2 * (1 - v) * v * x1 + v * v * x2, by: (1 - v) * (1 - v) * y0 + 2 * (1 - v) * v * y1 + v * v * y2, arm: ik(shx + 7, shy - 44) }; }
      const e = ((u - 0.62) / 0.38) ** 2, hx = shx + 7 + e * 3, hy = shy - 44 + e * (top + 44 - shy);   // the slam: the arm whips down with the ball
      return { bx: hx + 1, by: hy + R, arm: ik(hx, hy) };
    }
    const bnc = Math.abs(Math.cos((ja < 99 ? ja - AO : T) * 7.5)), bx = shx + 11, by = -R + (top + 2 * R) * bnc;   // y: -R (floor) … top + R (in his hand)
    return { bx, by, arm: ik(bx - 1, Math.min(by - R, top + 6)) };
  }
  function jumpFx(c, k, JF, P, T, feet, palms, sh0, KIT, hy) {
    if (k === "raspa") {   // v49.12 Robo-Raspa: fizzy soda-syrup jets from his boots AND his palms, with bubbles
      for (const [x, y] of feet) { jet(c, x + 1, y + 2.5, 6 + P * 14, 3.4, T, FIZZ);
        for (let i = 0; i < 4; i++) { const u = (JF * 2.2 + i * 0.25) % 1; c.strokeStyle = `rgba(255,255,255,${(0.9 * (1 - u)).toFixed(3)})`; c.lineWidth = 0.7; c.beginPath(); c.arc(x + 1 + Math.sin(T * 23 + i * 2) * 3.2, y + 4 + u * (10 + P * 12), 0.9 + i * 0.35, 0, Math.PI * 2); c.stroke(); } }
      for (const [x, y] of palms) jet(c, x, y + 1.5, 4 + P * 9, 2.2, T, FIZZ);
    } else if (k === "payaso") {   // v49.12 Payaso de la Feria: a puff of Fiesta confetti + a cascarón popping up over his head and cracking open
      const cols = ["#3ee8eb", "#ff3d8b", "#ff8a00", "#ffd23a", "#7cc860"];
      c.save(); c.globalAlpha = Math.max(0, 1 - JF * 0.9);
      for (let i = 0; i < 12; i++) { const a = Math.PI * (-0.15 + 1.3 * i / 11), r = 4 + JF * (16 + (i % 3) * 5);
        c.save(); c.translate(Math.cos(a) * r, -2 - Math.sin(a) * r * 0.45 + JF * JF * 16); c.rotate(T * 9 + i); box(c, cols[i % 5], -1.3, -0.8, 2.6, 1.6, 0.3); c.restore(); }
      c.restore();
      const ex = sh0.x + 4, ey = sh0.y - 24 - Math.min(JF, 0.4) / 0.4 * 8;
      const egg = (top) => { c.beginPath(); if (top) { c.moveTo(-3.6, 0); c.bezierCurveTo(-3.6, -4.2, -2, -5.6, 0, -5.6); c.bezierCurveTo(2, -5.6, 3.6, -4.2, 3.6, 0); }
        else { c.moveTo(-3.6, 0); c.bezierCurveTo(-3.6, 3.4, -2, 4.6, 0, 4.6); c.bezierCurveTo(2, 4.6, 3.6, 3.4, 3.6, 0); }
        for (let i = 3; i >= -3; i--) c.lineTo(i * 1.2, i % 2 ? -1 : 0.8); c.closePath(); c.fillStyle = "#ff8ad0"; c.fill();
        c.strokeStyle = "#3ee8eb"; c.lineWidth = 0.8; c.beginPath(); c.moveTo(-3.2, top ? -2.6 : 2.2); for (let i = -2; i <= 3; i++) c.lineTo(i * 1.1, (top ? -2.6 : 2.2) + (i % 2 ? -0.9 : 0.9)); c.stroke();
        ell(c, "#ffd23a", top ? -1.2 : 1.4, top ? -4 : 3.4, 0.6, 0.6); };
      c.save(); c.translate(ex, ey);
      if (JF < 0.4) { egg(true); egg(false); }
      else { const v = (JF - 0.4) / 0.6; c.globalAlpha = Math.max(0, 1 - v);
        c.save(); c.translate(-v * 7, -v * 6); c.rotate(-v * 1.3); egg(true); c.restore(); c.save(); c.translate(v * 6, v * 8); c.rotate(v * 1.1); egg(false); c.restore();
        for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5 + 0.3, r = 2 + v * 15; c.save(); c.translate(Math.cos(a) * r, Math.sin(a) * r * 0.8 + v * v * 6); c.rotate(T * 8 + i); box(c, cols[i % 5], -1.1, -0.7, 2.2, 1.4, 0.3); c.restore(); } }
      c.restore();
    } else if (k === "mariachi") {   // v49.12 Mariachi Neón: a neon trail behind him
      c.save(); c.globalAlpha = Math.max(0, 1 - JF);
      [hy - 40, hy - 26, hy - 12, hy + 4, hy + 18].forEach((y, i) => { const col = i % 2 ? "#3ee8eb" : "#ff3d8b", x0 = -9 - (i % 2) * 3, x1 = x0 - 14 - P * 30 - (i % 3) * 6;
        c.globalAlpha = Math.max(0, 1 - JF) * 0.35; line(c, col, 5, [x0, y, x1, y + 6]); c.globalAlpha = Math.max(0, 1 - JF); line(c, "#ffffff", 1.1, [x0, y, x1 + 6, y + 5]); line(c, col, 1.8, [x0 - 2, y + 1, x1, y + 6]); });
      c.restore();
    } else if (k === "lowrider") {   // v49.12 El Lowrider: a hydraulic hop: chrome springs pop out under his boots, exhaust puffs out the back
      const L = 4 + P * 15;
      for (const [x, y] of feet) { const x0 = x + 1, y0 = y + 3; c.strokeStyle = "#d5dbe1"; c.lineWidth = 1.5; c.lineJoin = "round"; c.beginPath(); c.moveTo(x0, y0);
        for (let i = 1; i <= 7; i++) c.lineTo(x0 + (i === 7 ? 0 : i % 2 ? -3.4 : 3.4), y0 + i * L / 7); c.stroke(); box(c, "#5b6270", x0 - 4.5, y0 + L, 9, 2, 0.8); }
      for (let i = 0; i < 4; i++) { const a = JF * 1.3 - i * 0.14; if (a <= 0 || a >= 1) continue;
        ell(c, `rgba(200,200,210,${(0.8 * (1 - a)).toFixed(3)})`, -12 - a * 26, hy + 2 - a * 6 + (i % 2) * 3, 2.4 + a * 6, 2 + a * 5); }
    }
  }
  function groundFx(c, k, la) {   // drawn at the landing spot: El Lowrider's ground-shake dust ring (he lands hard off the hydraulics)
    if (k !== "lowrider" || !(la < 0.5)) return;
    const u = la / 0.5, r = 8 + u * 40, a = 1 - u;
    c.strokeStyle = `rgba(120,98,70,${(0.75 * a).toFixed(3)})`; c.lineWidth = 3 * a + 0.6; c.beginPath(); c.ellipse(0, 0, r, r * 0.22, 0, 0, Math.PI * 2); c.stroke();
    c.strokeStyle = `rgba(200,180,150,${(0.6 * a).toFixed(3)})`; c.lineWidth = 1.6 * a + 0.4; c.beginPath(); c.ellipse(0, 0, r * 0.6, r * 0.132, 0, 0, Math.PI * 2); c.stroke();
    for (let i = 0; i < 6; i++) { const s = i < 3 ? -1 : 1, d = r * (0.55 + (i % 3) * 0.2); ell(c, `rgba(170,150,120,${(0.55 * a).toFixed(3)})`, s * d, -2 - u * 6 - (i % 3) * 2, 2.5 + u * 4, 2 + u * 3); }
  }
  function juanUfo(c, o) {   // Juan UFO: a silver flying disk with a glass dome, Juan inside at the wheel, blinking rim lights, a soft beam
    const t = o.t || 0, q = o.ph || 0; let bob = 0, tilt = 0;
    if (o.pose === "run") { bob = Math.sin(q * 0.5) * 1.6; tilt = 0.05; } else if (o.pose === "up") tilt = -0.12; else if (o.pose === "down") tilt = 0.1;
    else if (o.pose === "cheer") { tilt = Math.sin(t * 6) * 0.15; bob = -Math.abs(Math.sin(t * 6)) * 3; } else bob = Math.sin(t * 2.4) * 1.2;
    c.fillStyle = lin(c, 0, -20, 0, 0, ["rgba(62,232,235,.5)", "rgba(62,232,235,0)"]); c.beginPath(); c.moveTo(-7, -19 + bob); c.lineTo(7, -19 + bob); c.lineTo(14, 0); c.lineTo(-14, 0); c.closePath(); c.fill();
    const ja = o.ja == null ? 99 : o.ja;
    if (ja < 0.6) { const JF = ja / 0.6, P = Math.sin(JF * Math.PI);   // jump: a blue/orange flame jet under the disk, the beam flashing
      if (Math.floor(t * 24) % 2) { c.fillStyle = "rgba(160,250,255,.55)"; c.beginPath(); c.moveTo(-8, -19 + bob); c.lineTo(8, -19 + bob); c.lineTo(17, 0); c.lineTo(-17, 0); c.closePath(); c.fill(); }
      jet(c, 1, -24 + bob, 8 + P * 18, 5, t, UFOJ); }
    c.save(); c.translate(1, -30 + bob); c.rotate(tilt);
    c.fillStyle = "rgba(120,215,240,.35)"; c.beginPath(); c.ellipse(0, -2, 12.5, 13.5, 0, Math.PI, 0); c.fill();
    box(c, "#2e9a45", -8, -8.5, 16, 9, 4); line(c, "#ffffff", 0.9, [-1, -8, -1.5, -4]); line(c, "#ffffff", 0.9, [1.5, -8, 2, -4]);
    ell(c, "#a5683f", -0.5, -9.5, 2.4, 2); ell(c, lin(c, -5, -20, 6, -9, ["#d39a6c", "#c68a5e", "#a5683f"]), 0.5, -13.6, 5.6, 6);
    ell(c, "#1b120c", 3.1, -14.6, 0.8, 1.05); c.fillStyle = "#24160e"; c.beginPath(); c.moveTo(1.6, -11.6); c.quadraticCurveTo(3.8, -12.8, 6, -11.5); c.quadraticCurveTo(3.8, -10, 1.6, -11.6); c.fill();
    c.fillStyle = "#151515"; c.beginPath(); c.ellipse(0.3, -16.4, 6, 4.4, 0, Math.PI, 0); c.fill(); box(c, "#151515", 0, -17.4, 9.5, 1.8, 0.9); box(c, "#2e9a45", -1.6, -19.8, 3.4, 2, 0.6);
    line(c, "#222222", 1.6, [-2.5, -4.5, 3, -6.5, 7.5, -4.5]); ell(c, "#c68a5e", -2, -4.8, 1.6, 1.4); ell(c, "#c68a5e", 7, -4.8, 1.6, 1.4);
    c.fillStyle = "rgba(200,245,255,.22)"; c.beginPath(); c.ellipse(0, -2, 12.5, 13.5, 0, Math.PI, 0); c.fill();
    c.strokeStyle = "#a8e4f0"; c.lineWidth = 1.2; c.beginPath(); c.ellipse(0, -2, 12.5, 13.5, 0, Math.PI, 0); c.stroke(); line(c, "rgba(255,255,255,.8)", 1.3, [-8, -9, -6, -12.5, -2.5, -14.5]);
    c.fillStyle = lin(c, 0, -5, 0, 7, ["#f6f8fa", "#c9d0d8", "#7c858f"]); c.beginPath(); c.ellipse(0, 1, 26, 6.8, 0, 0, Math.PI * 2); c.fill();
    line(c, "#9aa3ad", 1, [-25, 1.6, 25, 1.6]); ell(c, "#5b6270", 0, 5, 15, 3.4); c.save(); c.shadowColor = "#5ff3ff"; c.shadowBlur = 6; ell(c, "#8ff8ff", 0, 6.6, 7, 1.7); c.restore();
    const cols = ["#ff3d8b", "#ff8a00", "#3ee8eb", "#7cc860", "#b36bff", "#ffffff", "#ff3d8b"];
    for (let i = 0; i < 7; i++) { const on = Math.floor(t * 5 + i) % 3 !== 0; ell(c, on ? cols[i] : "#5b6270", -19.5 + i * 6.5, -0.2, 1.6, 1.6); }
    c.restore();
  }
  function skinPreview(cv, id) {   // a little standing Juan in that skin, for the picker
    const c = cv.getContext("2d"), d = Math.min(3, Math.max(1, root.devicePixelRatio || 1)), w = cv.clientWidth || 64, h = cv.clientHeight || 84;
    cv.width = Math.round(w * d); cv.height = Math.round(h * d); c.setTransform(d, 0, 0, d, 0, 0); c.clearRect(0, 0, w, h);
    const sc = Math.min(w / 58, h / (id === "largo" ? 150 : 88)); c.translate(w / 2 - 1.5 * sc, h - 4); c.scale(sc, sc); juan(c, { skin: id, pose: "stand", outfit: "work", t: 0.4 });
  }

  // ================= Juan himself (feet at 0,0, facing right) =================
  function juan(c, o) {
    const SKN = o.skin || "classic";
    if (SKN === "ufo") return juanUfo(c, o);
    const KIT = { jefe: { jean: "#22305e", jean2: "#18234a", boot: "#151515", boot2: "#0b0b0b", legW: 8.5, sleeve: "#24336a", sleeveB: "#18234a", hand: "#efbb94", handB: "#d39b72", armW: 6.6, cuff: "#ffffff", dxF: 6, dxB: -4 },
      raspa: { jean: "#f4f7fa", jean2: "#d5dbe1", boot: "#1fb8bf", boot2: "#168c92", legW: 10, sleeve: "#3ee8eb", sleeveB: "#1fb8bf", hand: "#f4f7fa", handB: "#d5dbe1", armW: 8, knee: "#1fb8bf", shoulder: "#ffffff", dxF: 6.5, dxB: -5 },
      payaso: { jean: "#1fb8bf", jean2: "#168c92", boot: "#ff3d8b", boot2: "#d42a72", sole: "#ffd23a", legW: 10, sleeve: "#ffd23a", sleeveB: "#e3b51f", hand: "#ffffff", handB: "#e3e6ea", armW: 7, knee: "#ff3d8b", cuff: "#ff3d8b", dxF: 6, dxB: -4 },
      astro: { jean: "#f4f7fa", jean2: "#d5dbe1", boot: "#1fb8bf", boot2: "#168c92", legW: 10, sleeve: "#f4f7fa", sleeveB: "#d5dbe1", hand: "#3ee8eb", handB: "#1fb8bf", armW: 8, knee: "#1fb8bf", cuff: "#ff8a00", shoulder: "#ffffff" },
      lowrider: { jean: "#1fb8bf", jean2: "#168c92", boot: "#1b1b22", boot2: "#111116", sole: "#f4f7fa", legW: 10.5, sleeve: "#8a3ad0", sleeveB: "#6a2aa8", hand: "#d5dbe1", handB: "#9aa3ad", armW: 8.5, knee: "#d5dbe1", dxF: 9.5, dxB: -7.5 },
      largo: { jean: "#1fb8bf", jean2: "#168c92", boot: "#f4f6f8", boot2: "#d5dbe1", sole: "#ff3d8b", legW: 5.4, sleeve: "#c68a5e", sleeveB: "#a5683f", hand: "#c68a5e", handB: "#a5683f", armW: 5, cuff: "#ff8a00", dxF: 3, dxB: -3 },
      cowboy: { jean: "#f7f5ef", jean2: "#dcd7cb", boot: "#b07a4a", boot2: "#8a5a32", sole: "#5e3820", legW: 8.5, sleeve: "#f7f5ef", sleeveB: "#dcd7cb", hand: "#c68a5e", handB: "#a5683f", armW: 7, cuff: "#c8f5e4", dxF: 6, dxB: -4 },
      mariachi: { jean: "#1b1b22", jean2: "#121218", boot: "#151515", boot2: "#0b0b0b", sole: "#3a3a44", legW: 8.5, sleeve: "#22222c", sleeveB: "#121218", hand: "#c68a5e", handB: "#a5683f", armW: 7, cuff: "#3ee8eb", dxF: 6, dxB: -4 } }[SKN];
    const WEST_FIT = !KIT && o.outfit === "western", SK = "#c68a5e", SK2 = "#a5683f", JE = KIT ? KIT.jean : "#2f5291", JE2 = KIT ? KIT.jean2 : "#22406f";
    const shirt = WEST_FIT ? "#00a7a0" : "#a6ff2e", shirt2 = WEST_FIT ? "#007f7a" : "#78d41a", shirtB = WEST_FIT ? "#00807a" : "#86d424";
    const TALL = SKN === "largo", LEG = TALL ? 40 : 15, UA = TALL ? 25 : 11, FA = TALL ? 24 : 10, TOR = TALL ? 44 : 21;   // Juan Largo: ~2× as tall, same poses
    const ja = o.ja == null ? 99 : o.ja, JF = ja < 0.6 ? ja / 0.6 : -1, P = JF >= 0 ? Math.sin(JF * Math.PI) : 0, T = o.t || 0;   // v49.5 jump FX: seconds since the jump, 0..1
    const feet = [], palms = [];
    const q = o.ph || 0; let bob = 0, lean = 0, lf, lb, af, ab;
    if (o.pose === "run") { lf = [0.75 * Math.sin(q), 0.25 + 1.1 * Math.max(0, Math.cos(q))]; lb = [0.75 * Math.sin(q + Math.PI), 0.25 + 1.1 * Math.max(0, Math.cos(q + Math.PI))];
      af = [-0.85 * Math.sin(q), 1.35]; ab = [0.85 * Math.sin(q), 1.35]; bob = -Math.abs(Math.cos(q)) * 2.4; lean = 0.13; }
    else if (o.pose === "up") { lf = [1.0, 1.5]; lb = [-0.3, 0.8]; af = [2.5, 0.4]; ab = [-0.9, -0.9]; lean = 0.06; }
    else if (o.pose === "down") { lf = [0.5, 0.5]; lb = [-0.3, 0.4]; af = [1.9, 0.4]; ab = [-1.2, -0.6]; lean = 0.08; }
    else if (o.pose === "cheer") { const w = Math.sin((o.t || 0) * 8); lf = [0.18, 0.1]; lb = [-0.18, 0.1]; af = [2.75 + w * 0.2, 0.3]; ab = [-2.75 + w * 0.2, -0.3]; bob = -Math.abs(w) * 3; }
    else { lf = [0.12, 0.06]; lb = [-0.1, 0.05]; af = [0.18, 0.35]; ab = [-0.12, 0.35]; }
    let tuck = 0;   // Juan Largo tucks his knees in the air (a dunk), the body drops so his lowest foot stays at the hitbox bottom: he stays on screen at the top of a double jump
    if (TALL && (o.pose === "up" || o.pose === "down")) { if (o.pose === "down") { lf = [1.1, 1.6]; lb = [-0.2, 1.2]; } const fy = ([a, b]) => Math.cos(a) * LEG + Math.cos(a - b) * LEG; tuck = 2 * LEG - Math.max(fy(lf), fy(lb)); }
    const hx = 0, hy = -2 * LEG + bob + tuck;
    const leg = ([a, b], jean, bootCol) => {
      const kx = hx + Math.sin(a) * LEG, ky = hy + Math.cos(a) * LEG, s = a - b, fx = kx + Math.sin(s) * LEG, fy = ky + Math.cos(s) * LEG; feet.push([fx, fy]);
      if (TALL) {   // long bare legs, 70s short shorts (turquoise, a pink stripe), tall striped tube socks
        const back = jean !== JE, at = (u) => [kx + (fx - kx) * u, ky + (fy - ky) * u]; line(c, back ? "#a5683f" : "#c68a5e", KIT.legW, [hx, hy, kx, ky, fx, fy]);
        line(c, back ? "#d5dbe1" : "#f4f6f8", KIT.legW + 0.8, [...at(0.4), fx, fy]);
        line(c, back ? "#c22e6c" : "#ff3d8b", KIT.legW + 0.9, [...at(0.45), ...at(0.5)], "butt"); line(c, back ? "#c96a00" : "#ff8a00", KIT.legW + 0.9, [...at(0.54), ...at(0.58)], "butt"); line(c, back ? "#168c92" : "#1fb8bf", KIT.legW + 0.9, [...at(0.62), ...at(0.66)], "butt");
        line(c, jean, 11, [hx, hy, hx + (kx - hx) * 0.55, hy + (ky - hy) * 0.55]); line(c, "#ff3d8b", 1.4, [hx - 4, hy + 2, hx + (kx - hx) * 0.55 - 4, hy + (ky - hy) * 0.55]);
      } else line(c, jean, KIT ? KIT.legW : 8.5, [hx, hy, kx, ky, fx, fy]);
      if (KIT && KIT.knee) ell(c, KIT.knee, kx + 0.5, ky, KIT.legW * 0.55, KIT.legW * 0.5);
      if (SKN === "raspa") line(c, jean === JE ? "#3ee8eb" : "#1fb8bf", 3, [kx + (fx - kx) * 0.3, ky + (fy - ky) * 0.3, kx + (fx - kx) * 0.7, ky + (fy - ky) * 0.7]);   // Robo-Raspa: a turquoise shin stripe
      if (SKN === "payaso") for (const [u0, u1] of [[0.18, 0.4], [0.62, 0.84]]) line(c, "#ff3d8b", KIT.legW, [kx + (fx - kx) * u0, ky + (fy - ky) * u0, kx + (fx - kx) * u1, ky + (fy - ky) * u1], "butt");   // checkered overall legs
      if (SKN === "payaso") line(c, "#ff3d8b", KIT.legW, [hx + (kx - hx) * 0.35, hy + (ky - hy) * 0.35, hx + (kx - hx) * 0.65, hy + (ky - hy) * 0.65], "butt");
      if (SKN === "mariachi") { for (const u of [0.2, 0.45, 0.7]) ell(c, "#e8edf2", hx + (kx - hx) * u - 3, hy + (ky - hy) * u, 0.7, 0.7); for (const u of [0.25, 0.55, 0.85]) ell(c, "#e8edf2", kx + (fx - kx) * u - 3, ky + (fy - ky) * u, 0.7, 0.7); }   // silver buttons down the charro pants
      c.save(); c.translate(fx, fy); c.rotate(s * 0.55);
      if (KIT) { const big = KIT.legW >= 10; box(c, bootCol, big ? -6 : -4.5, big ? -6 : -4, big ? 16 : 13.5, big ? 8.6 : 6.6, 3); box(c, KIT.sole || "#22201c", big ? -6.5 : -5, 1.8, big ? 17 : 14.5, 2.8, 1); ell(c, "rgba(255,255,255,.2)", 3, -2.4, 3.4, 1.2); }
      else if (WEST_FIT) { c.fillStyle = bootCol; c.beginPath(); c.moveTo(-4.5, -5); c.lineTo(3.5, -5); c.lineTo(4, -1); c.quadraticCurveTo(10, -0.5, 12, 2.6); c.lineTo(-4.5, 2.6); c.closePath(); c.fill(); box(c, "#2a160c", -4.8, 2.2, 4.6, 2.6, 0.8); line(c, "rgba(255,255,255,.25)", 0.8, [-2, -3.5, 2, -3.5]); }
      else { box(c, bootCol, -4.5, -4, 13.5, 6.6, 3); box(c, "#3a2414", -5, 1.8, 14.5, 2.6, 1); ell(c, "rgba(255,255,255,.18)", 3, -2, 3, 1.2); }
      c.restore();
    };
    const sh0 = { x: hx + Math.sin(lean) * TOR, y: hy - Math.cos(lean) * TOR };
    const arm = ([a, b], sleeve, skin, dx) => {   // dx: skins sit the arms at the chest's edges so the chest art (tie, light, "SA 210") shows
      const sh = dx ? { x: sh0.x + dx, y: sh0.y + (SKN === "lowrider" ? 2.5 : 1) } : sh0;
      const ex = sh.x + Math.sin(a) * UA, ey = sh.y + Math.cos(a) * UA, s = a + b, wx = ex + Math.sin(s) * FA, wy = ey + Math.cos(s) * FA; palms.push([wx + Math.sin(s) * 1.8, wy + Math.cos(s) * 1.8]);
      if (KIT) { if (KIT.rolled) { line(c, sleeve, KIT.armW, [sh.x, sh.y, ex, ey]); line(c, skin, KIT.armW * 0.72, [ex, ey, wx, wy]); line(c, sleeve === KIT.sleeve ? "#ffc6dc" : "#f0a8c0", KIT.armW + 0.8, [ex, ey, ex + (wx - ex) * 0.22, ey + (wy - ey) * 0.22], "butt"); }   // sleeves rolled up
        else line(c, sleeve, KIT.armW, [sh.x, sh.y, ex, ey, wx, wy]); if (KIT.cuff) line(c, KIT.cuff, KIT.armW * 0.9, [wx - Math.sin(s) * 1.2, wy - Math.cos(s) * 1.2, wx, wy], "butt");
        if (SKN === "raspa") line(c, "#f4f7fa", KIT.armW * 0.82, [ex + (wx - ex) * 0.15, ey + (wy - ey) * 0.15, wx, wy]);
        ell(c, skin, wx + Math.sin(s) * 1.8, wy + Math.cos(s) * 1.8, KIT.armW * 0.48, KIT.armW * 0.48);
        if (SKN === "lowrider") {   // a fender-shaped shoulder: a teal half-moon with a chrome trim + a gold pinstripe
          c.fillStyle = lin(c, sh.x - 9, sh.y - 7, sh.x + 9, sh.y + 5, ["#5ff3e0", sleeve === KIT.sleeve ? "#1fb8bf" : "#168c92", "#0f6a70"]);
          c.beginPath(); c.ellipse(sh.x + 0.5, sh.y + 2.5, 9.8, 7.6, -0.08, Math.PI, 0); c.closePath(); c.fill();
          line(c, "#e8edf2", 1.6, [sh.x - 9.2, sh.y + 3.2, sh.x + 10.2, sh.y + 1.6]); line(c, "#ffd27a", 0.6, [sh.x - 5.5, sh.y - 0.5, sh.x, sh.y - 2.8, sh.x + 5.5, sh.y - 1]); }
        else if (KIT.shoulder) ell(c, KIT.shoulder, sh.x + 0.5, sh.y + 1, KIT.armW * 0.75, KIT.armW * 0.6);
        return; }
      if (WEST_FIT) { line(c, sleeve, 6.5, [sh.x, sh.y, ex, ey, wx, wy]); line(c, "rgba(255,255,255,.85)", 1.2, [wx - Math.cos(s) * 3, wy + Math.sin(s) * 3, wx + Math.cos(s) * 3, wy - Math.sin(s) * 3], "butt"); }
      else { line(c, skin, 5.5, [sh.x, sh.y, ex, ey, wx, wy]); line(c, sleeve, 7.5, [sh.x, sh.y, sh.x + Math.sin(a) * 6, sh.y + Math.cos(a) * 6]); }
      ell(c, skin, wx + Math.sin(s) * 1.5, wy + Math.cos(s) * 1.5, 3.1, 3.1);
    };
    if (KIT) { arm(ab, KIT.sleeveB, KIT.handB, KIT.dxB || 0); leg(lb, JE2, KIT.boot2); leg(lf, JE, KIT.boot);
      if (SKN === "astro") { box(c, "#d5dbe1", hx - 17, hy - 24, 7.6, 18, 2.5); box(c, "#1fb8bf", hx - 16.6, hy - 20, 6.8, 2.4, 0.8); box(c, "#5b6270", hx - 16, hy - 8, 6, 3, 1); if (P) jet(c, hx - 13, hy - 5, 8 + P * 20, 4, T, PACK, -0.35); } }
    else { arm(ab, shirtB, SK2); leg(lb, JE2, WEST_FIT ? "#4e2a14" : "#8e6030"); leg(lf, JE, WEST_FIT ? "#6b3b1f" : "#b07a3e"); }
    c.save(); c.translate(hx, hy); c.rotate(lean);
    box(c, JE, -10, -4, 20, 8, 3);
    if (KIT) { skinBody(c, SKN, P); c.restore();
      if (TALL) { const ball = hoop(T, ja, sh0.x + KIT.dxF, sh0.y + 1, UA, FA); dribble(c, T, ball.bx, ball.by); arm(ball.arm, KIT.sleeve, KIT.hand, KIT.dxF); }
      else arm(af, KIT.sleeve, KIT.hand, KIT.dxF || 0);
      if (P) jumpFx(c, SKN, JF, P, T, feet, palms, sh0, KIT, hy);
      return; }
    c.fillStyle = lin(c, -10, -23, 10, 0, [shirt, shirt2]); rr(c, -10.5, -23.5, 21, 22.5, 6); c.fill();
    if (WEST_FIT) {   // pearl-snap western shirt: a white-piped yoke, pearl snaps, flap pockets
      line(c, "#ffffff", 1.3, [-10, -17.5, -4, -15, 0.5, -18.5, 5, -15, 10, -17.5]); line(c, "rgba(0,0,0,.18)", 0.8, [0.5, -21, 0.5, -2]);
      for (const y of [-19.5, -14.5, -9.5, -4.5]) ell(c, "#f4f7fa", 0.5, y, 1.2, 1.2);
      line(c, "#ffffff", 1, [-8, -13, -3, -12]); line(c, "#ffffff", 1, [3.5, -12, 8.5, -13]); ell(c, "#f4f7fa", -5.5, -12.4, 0.8, 0.8); ell(c, "#f4f7fa", 6, -12.4, 0.8, 0.8);
      box(c, "#5a3218", -10, -3.5, 20.5, 3.4, 1); ell(c, lin(c, -2, -4, 4, 0, ["#ffffff", "#9aa3ad"]), 1, -1.8, 3.4, 2.3);
    } else {   // the hi-vis work shirt: neon safety green, orange stripes with a silver reflective strip
      for (const sx of [-6.5, 4]) { box(c, "#ff7a00", sx, -23.5, 3.6, 14.5); box(c, "#e8edf2", sx + 1.1, -23.5, 1.4, 14.5); }
      box(c, "#ff7a00", -10.5, -10.5, 21, 4.6); box(c, "#e8edf2", -10.5, -9, 21, 1.6);
      box(c, "#5a3a22", -10, -3.5, 20.5, 3.2, 1); box(c, "#c9d0d8", -1, -3.3, 3.4, 2.8, 0.6); box(c, "#7a5232", -13, -2, 5.5, 8, 1.5);   // belt + a tool pouch
    }
    // head
    const X = 2.5, Y = -31.5;
    box(c, SK2, -2, -26, 6, 5, 2);
    ell(c, "#24160e", X - 2.2, Y - 0.5, 8, 8.2);
    ell(c, lin(c, X - 6, Y - 6, X + 8, Y + 8, ["#d39a6c", SK, SK2]), X + 0.5, Y, 8, 8.6);
    ell(c, SK2, X - 3.5, Y + 0.5, 1.8, 2.6); ell(c, "#1b120c", X + 4.4, Y - 1.2, 1.05, 1.4); line(c, "#24160e", 1.2, [X + 2.4, Y - 4, X + 6.4, Y - 4.3]);
    ell(c, SK2, X + 8.2, Y + 1.2, 1.7, 1.9);
    c.fillStyle = "#24160e"; c.beginPath(); c.moveTo(X + 2.8, Y + 3.7); c.quadraticCurveTo(X + 6, Y + 2, X + 9.4, Y + 3.8); c.quadraticCurveTo(X + 6.4, Y + 6, X + 2.8, Y + 3.7); c.fill();
    line(c, "#7a3b2a", 0.9, [X + 4.6, Y + 6.6, X + 7, Y + 6.2]);
    c.save(); if (P) { c.translate(X, Y - 6); c.rotate(-P * 0.18); c.translate(-X, -(Y - 6) - P * 5); }   // jump: the hat hops off his head and back
    if (WEST_FIT) {   // a beige cowboy hat
      c.fillStyle = lin(c, 0, Y - 16, 0, Y - 6, ["#efdcb4", "#cdb385"]); c.beginPath(); c.moveTo(X - 7.5, Y - 6.5); c.lineTo(X - 6.6, Y - 16); c.quadraticCurveTo(X + 0.5, Y - 12.5, X + 7.6, Y - 16); c.lineTo(X + 8.5, Y - 6.5); c.closePath(); c.fill();
      box(c, "#5a3218", X - 7, Y - 9, 15, 2.6, 0.5);
      c.fillStyle = lin(c, 0, Y - 9, 0, Y - 3, ["#e6d0a4", "#b99d6e"]); c.beginPath(); c.moveTo(X - 16, Y - 9.5); c.quadraticCurveTo(X + 1, Y - 1.5, X + 18, Y - 9.5); c.quadraticCurveTo(X + 1, Y - 5, X - 16, Y - 9.5); c.fill();
    } else {   // a white construction hard hat
      c.fillStyle = lin(c, X - 8, Y - 14, X + 8, Y - 3, ["#ffffff", "#e9eef2", "#c3ccd4"]); c.beginPath(); c.ellipse(X + 0.5, Y - 3.5, 9.6, 9.6, 0, Math.PI, 0); c.fill();
      ell(c, "#dfe5ea", X + 4, Y - 3.4, 12.5, 2.1); line(c, "rgba(0,0,0,.12)", 1.6, [X + 0.5, Y - 13, X + 0.5, Y - 4]); ell(c, "rgba(255,255,255,.9)", X - 3, Y - 9.5, 2.6, 1.4, -0.6);
    }
    c.restore(); c.restore();
    arm(af, shirt, SK);
  }

  // ================= obstacles & pickups (world units: x right, y up is negative, ground = 0) =================
  function drawEnt(c, e, t, rm) {
    const x = e.x, y = e.y, w = e.w;
    switch (e.t) {
      case "cone": {
        if (e.down) { c.save(); c.translate(x + 12, -5); c.rotate(-1.45); }
        else { c.save(); c.translate(x + 12, 0); }
        ell(c, "rgba(0,0,0,.25)", 0, 0, 15, 3); box(c, "#1d1f24", -14, -4, 28, 4, 1.5);
        const wAt = (yy) => 2.5 + (yy + 32) / 28 * 7;
        poly(c, lin(c, -9, 0, 9, 0, ["#d95a00", "#ff8a1a", "#ff7a00", "#c44e00"]), [-9.5, -4, 9.5, -4, 2.5, -32, -2.5, -32]);
        for (const [a, b] of [[-14, -19], [-23, -26.5]]) poly(c, "#f4f7fa", [-wAt(a), a, wAt(a), a, wAt(b), b, -wAt(b), b]);
        c.restore(); break; }
      case "pothole":
        ell(c, "#4b4f58", x + 28, -1, 30, 6.5); ell(c, "#17191e", x + 28, -0.5, 26, 5); ell(c, "rgba(120,170,220,.35)", x + 24, 0.5, 14, 2.2);
        line(c, "#2a2d34", 0.9, [x - 2, -1, x - 8, 2, x - 14, 1]); line(c, "#2a2d34", 0.9, [x + 56, -2, x + 63, -4]); break;
      case "cart": {
        c.save(); c.translate(x + 26, 0); if (e.bonk) c.rotate(Math.min(0.5, e.bonk * 0.4));
        ell(c, "rgba(0,0,0,.25)", 0, 0, 26, 3);
        const spin = (rm ? 0 : t * 12);
        for (const wx of [-18, 18]) { ell(c, "#1d1f24", wx, -4, 4.2, 4.2); line(c, "#9aa3ad", 1, [wx - Math.cos(spin) * 3, -4 - Math.sin(spin) * 3, wx + Math.cos(spin) * 3, -4 + Math.sin(spin) * 3]); }
        line(c, "#9aa3ad", 2, [-18, -8, -20, -20, 22, -20, 18, -8, -18, -8]);
        c.fillStyle = "rgba(200,208,216,.14)"; poly(c, "rgba(200,208,216,.14)", [-26, -46, 26, -46, 20, -20, -20, -20]);
        c.strokeStyle = "#c9d0d8"; c.lineWidth = 1.2; c.beginPath(); c.moveTo(-26, -46); c.lineTo(26, -46); c.lineTo(20, -20); c.lineTo(-20, -20); c.closePath(); c.stroke();
        c.lineWidth = 0.7; for (let k = -20; k <= 20; k += 6) { c.beginPath(); c.moveTo(k * 1.2, -46); c.lineTo(k, -20); c.stroke(); } for (let yy = -40; yy < -20; yy += 6) { c.beginPath(); c.moveTo(-25 + (yy + 46) * 0.25, yy); c.lineTo(25 - (yy + 46) * 0.25, yy); c.stroke(); }
        line(c, "#c9d0d8", 1.6, [26, -46, 32, -54]); line(c, "#ff3d8b", 3.4, [30, -55, 36, -52]);
        c.restore();
        if (!rm && !e.bonk && e.on) for (let k = 0; k < 3; k++) line(c, "rgba(255,255,255,.65)", 1.4, [x + 62 + k * 4, -36 + k * 10, x + 76 + k * 6, -36 + k * 10]);
        break; }
      case "chancla": {
        c.save(); c.translate(x + 15, y + 7); c.rotate(rm ? 0.2 : Math.sin(t * 6 + e.ph) * 0.9);
        ell(c, lin(c, -15, 0, 15, 0, ["#ff3d8b", "#ff6fa8"]), 0, 0, 15, 5.5); ell(c, "#ffffff", 0, -1.4, 13, 3.2); ell(c, "#ff8fbf", 0, -1.6, 12, 2.6);
        line(c, "#00b8b0", 2, [-2, -1.5, 5, -6, 10, -1.5]); line(c, "#00b8b0", 2, [5, -6, 5, -1.5]);
        c.restore(); if (!rm) ell(c, "rgba(0,0,0,.18)", x + 15, 0, 12, 2.4); break; }
      case "chihuahua": {
        const dir = e.vx > 0 ? 1 : -1, run = rm ? 0 : t * 16 + e.ph;
        c.save(); c.translate(x + 18, 0); c.scale(-dir, 1);   // drawn facing left, flipped when it trots right
        ell(c, "rgba(0,0,0,.22)", 0, 0, 16, 3);
        for (const [lx, p] of [[-8, 0], [-4, Math.PI], [7, Math.PI], [11, 0]]) line(c, "#c48e5c", 2.6, [lx, -10, lx + Math.sin(run + p) * 3, -1]);
        ell(c, lin(c, 0, -22, 0, -8, ["#e3b483", "#c48e5c"]), 2, -14, 13, 7); line(c, "#c48e5c", 2.2, [14, -15, 19, -22, 17, -25]);
        ell(c, "#e3b483", -11, -22, 7.5, 6.5); poly(c, "#c48e5c", [-15, -26, -18, -38, -10, -27]); poly(c, "#c48e5c", [-8, -27, -4, -38, -3, -25]); poly(c, "#ff8fbf", [-14.5, -27, -16.5, -34, -11.5, -27.5]);
        ell(c, "#e3b483", -17, -19, 4, 3); ell(c, "#1b120c", -20.5, -19.5, 1.4, 1.2); ell(c, "#1b120c", -12.5, -23.5, 1.6, 1.8); ell(c, "#ffffff", -12, -24, 0.5, 0.5);
        box(c, "#ff3d8b", -9, -18, 4, 7, 1.5);
        c.restore();
        if (rm || mod(t * 1.4 + e.ph, 1) < 0.45) { box(c, "#ffffff", x - 8, -58, 38, 16, 7); poly(c, "#ffffff", [x + 4, -43, x + 12, -43, x + 6, -36]); say(c, "YAP!", x + 11, -50, 11, "#ff3d8b", { weight: 900 }); }
        break; }
      case "sprinkler": {
        ell(c, "rgba(90,150,210,.28)", x + 9, 0, 36, 4);
        box(c, "#2f8a46", x + 3, -9, 12, 9, 2); box(c, "#1d1f24", x + 7, -13, 4, 5, 1);
        if (e.on) { c.strokeStyle = "rgba(170,225,255,.85)"; c.lineWidth = 1.5;
          for (let k = -3; k <= 3; k++) { if (!k) continue; const dx = k * 11, sway = rm ? 0 : Math.sin(t * 5 + k) * 4; c.beginPath(); c.moveTo(x + 9, -13); c.quadraticCurveTo(x + 9 + dx * 0.4 + sway, -96 + Math.abs(k) * 8, x + 9 + dx + sway, -4); c.stroke(); }
          c.fillStyle = "rgba(220,245,255,.9)"; for (let k = 0; k < 10; k++) { const a = (k * 0.7 + (rm ? 0 : t * 2)) % 1, dx = (k - 4.5) * 7; c.beginPath(); c.arc(x + 9 + dx * a * 1.4, -13 - Math.sin(a * Math.PI) * 70, 1.3, 0, Math.PI * 2); c.fill(); } }
        break; }
      case "lowcar": lowcar(c, x, w, t, rm); break;
      case "sportscar": sportscar(c, x, w, t, rm); break;
      case "pallet":
        box(c, "#a8743f", x, -8, w, 8, 1); for (let k = 0; k < 4; k++) box(c, "#6b4a2e", x + 4 + k * 20, -6, 8, 6);
        for (let row = 0; row < 2; row++) for (let k = 0; k < 2; k++) { const bx = x + 2 + k * 34 + row * 2, by = -8 - (row + 1) * 15;
          box(c, lin(c, 0, by, 0, by + 15, ["#eef1f4", "#c9d0d8"]), bx, by, 32, 15, 5); say(c, "MIX", bx + 16, by + 8, 8, "#ff7a00", { weight: 900 }); }
        break;
      case "tires":
        for (let k = 0; k < 4; k++) { const ty = -12 * (k + 1); box(c, lin(c, x, 0, x + w, 0, ["#14161a", "#3a3d44", "#1d1f24"]), x, ty, w, 12, 5); c.strokeStyle = "rgba(255,255,255,.12)"; c.lineWidth = 0.8; for (let s = x + 4; s < x + w - 2; s += 5) { c.beginPath(); c.moveTo(s, ty + 2); c.lineTo(s + 2, ty + 10); c.stroke(); } }
        ell(c, "#2a2d34", x + w / 2, -48, w / 2, 5); ell(c, "#0d0e11", x + w / 2, -48, w / 4, 2.4); break;
      case "flag": {
        line(c, "#c9d0d8", 2.2, [x + 2, 0, x + 2, -70]); ell(c, "#ffffff", x + 2, -71, 2.4, 2.4);
        const col = e.done ? "#00b8b0" : "#ff3d8b", wv = rm ? 0 : Math.sin(t * 5) * 3;
        c.fillStyle = col; c.beginPath(); c.moveTo(x + 3, -68); c.quadraticCurveTo(x + 16, -66 + wv, x + 30, -60 + wv * 0.5); c.quadraticCurveTo(x + 16, -54 - wv, x + 3, -50); c.fill(); break; }
      case "feria": {   // v49.6: a money bag with a $ (la feria)
        const by = y + (rm ? 0 : Math.sin(t * 3.5 + x * 0.07) * 3);
        ell(c, lin(c, x, by + 6, x + 24, by + 26, ["#d9c08a", "#b8955a"]), x + 12, by + 17, 11.5, 9.5); poly(c, "#c8a76c", [x + 7, by + 9, x + 17, by + 9, x + 20, by + 2, x + 4, by + 2]);
        box(c, "#7a5232", x + 6, by + 7.5, 12, 2.6, 1.2); say(c, "$", x + 12, by + 18, 13, "#2f7a3a", { weight: 900 }); break; }
      case "concha": {
        const by = y + (rm ? 0 : Math.sin(t * 4 + x) * 2.5);
        ell(c, "#d99a5e", x + 11, by + 10, 11, 5.5); c.fillStyle = lin(c, 0, by, 0, by + 10, ["#ffc2db", "#ff8fbf"]); c.beginPath(); c.ellipse(x + 11, by + 9, 10.5, 9, 0, Math.PI, 0); c.fill();
        c.strokeStyle = "rgba(255,255,255,.75)"; c.lineWidth = 0.9; for (let k = -2; k <= 2; k++) { c.beginPath(); c.moveTo(x + 11, by + 1); c.quadraticCurveTo(x + 11 + k * 4, by + 4, x + 11 + k * 4.8, by + 9); c.stroke(); } break; }
      case "beer": {   // a frosty mug of a cold one (Playa Neón: a martini)
        const by = y + (rm ? 0 : Math.sin(t * 3 + x * 0.1) * 4);
        if (e.mt) { if (!rm) { c.fillStyle = "rgba(62,232,235,.22)"; c.beginPath(); c.arc(x + 12, by + 16, 18 + Math.sin(t * 5 + x) * 1.5, 0, Math.PI * 2); c.fill(); }
          poly(c, "rgba(235,250,255,.7)", [x, by + 4, x + 24, by + 4, x + 12, by + 18]); poly(c, "#bff3e6", [x + 3, by + 6, x + 21, by + 6, x + 12, by + 16]);
          line(c, "rgba(235,250,255,.95)", 1.8, [x + 12, by + 18, x + 12, by + 29]); ell(c, "rgba(235,250,255,.95)", x + 12, by + 30, 7, 1.8);
          line(c, "#8a5a2a", 0.9, [x + 6, by - 1, x + 15, by + 11]); ell(c, "#4f8a2a", x + 13.5, by + 9.5, 2.6, 2.6); ell(c, "#d7262e", x + 13.5, by + 9.5, 1, 1);   // an olive on a pick
          box(c, "rgba(255,255,255,.6)", x + 4, by + 6.5, 6, 1.2, 0.6); break; }
        if (!rm) { c.fillStyle = "rgba(255,190,90,.22)"; c.beginPath(); c.arc(x + 12, by + 17, 19 + Math.sin(t * 5 + x) * 1.5, 0, Math.PI * 2); c.fill(); }
        c.strokeStyle = "rgba(235,245,250,.95)"; c.lineWidth = 3; c.beginPath(); c.arc(x + 20, by + 18, 6, -1.2, 1.2); c.stroke();
        box(c, "rgba(230,245,255,.55)", x + 1, by + 6, 20, 26, 4); box(c, lin(c, 0, by + 9, 0, by + 30, ["#ffc94a", "#f0a020", "#d9831a"]), x + 3, by + 9, 16, 21, 3);
        c.fillStyle = "rgba(255,255,255,.75)"; for (let k = 0; k < 5; k++) { c.beginPath(); c.arc(x + 6 + (k * 3.3) % 12, by + 27 - ((k * 7 + (rm ? 0 : t * 20)) % 16), 0.9, 0, Math.PI * 2); c.fill(); }
        for (const [fx, fr] of [[4, 4.2], [9, 5], [15, 4.6], [19, 3.6]]) ell(c, "#fffdf6", x + fx, by + 7, fr, 3.8);
        box(c, "rgba(255,255,255,.55)", x + 4, by + 11, 2, 16, 1); break; }
      case "coffee": {
        const by = y + (rm ? 0 : Math.sin(t * 4) * 3);
        poly(c, "#ffffff", [x + 3, by + 8, x + 19, by + 8, x + 16.5, by + 28, x + 5.5, by + 28]); poly(c, "#00b8b0", [x + 4, by + 13, x + 18, by + 13, x + 17.2, by + 21, x + 4.8, by + 21]);
        box(c, "#e1e6ea", x + 1.5, by + 4, 19, 5, 2); box(c, "#c9d0d8", x + 7, by + 1.5, 8, 3, 1);
        if (!rm) { c.strokeStyle = "rgba(255,255,255,.7)"; c.lineWidth = 1.3; for (let k = 0; k < 2; k++) { const sx = x + 8 + k * 6, ph = t * 3 + k; c.beginPath(); c.moveTo(sx, by); c.bezierCurveTo(sx + 3 * Math.sin(ph), by - 5, sx - 3 * Math.sin(ph), by - 9, sx, by - 14); c.stroke(); } }
        break; }
      case "agent": case "chaser": {
        const pose = e.st === "walk" ? (rm ? "stand" : "walk") : e.st === "chase" ? (e.air ? "air" : "run") : e.st;
        const flip = e.t === "agent" && e.vx < 0; c.save(); c.translate(x + 15, e.y + e.h); if (flip) c.scale(-1, 1); c.scale(1.06, AG_TALL);   // v49.7: drawn a bit taller (the 30×64 hitbox stays inside the drawing)
        iceAgent(c, { pose, flip, ph: e.t === "chaser" ? e.run || 0 : t * 7 + (e.ph || 0), t, rm, sk: e.sk, st2: e.st2, gang: e.gang }); c.restore(); break; }
      case "suv": iceSuv(c, x, w, e.night, e.out); break;
      case "flipflops": flipflops(c, x, y, t, rm); break;
      case "taco": {
        const by = y + (rm ? 0 : Math.sin(t * 4 + 1) * 3);
        ell(c, "#ffd27a", x + 16, by + 11, 12, 7); ell(c, "#ff6a3a", x + 10, by + 8, 4, 2.5); ell(c, "#3ad07a", x + 18, by + 7, 4.5, 2.2); ell(c, "#c8432c", x + 23, by + 9, 3.5, 2);
        c.fillStyle = lin(c, 0, by, 0, by + 20, ["#f1d9a0", "#d9b46a"]); c.beginPath(); c.moveTo(x, by + 12); c.quadraticCurveTo(x + 16, by + 30, x + 32, by + 12); c.quadraticCurveTo(x + 16, by + 20, x, by + 12); c.fill();
        break; }
    }
  }

  // ================= v46: the ICE agents (cartoon, feet at 0,0, facing right; flipped with scale(-1,1)) =================
  // A navy windbreaker with white "ICE" letters, a navy cap, sunglasses, gray cargo pants, boots. No weapons, no badges.
  function iceAgent(c, o) {
    const say = (cc, str, x, y, size, col, opt) => { if (!o.flip) return sayText(cc, str, x, y, size, col, opt); cc.save(); cc.translate(x, y); cc.scale(-1, 1); sayText(cc, str, 0, 0, size, col, opt); cc.restore(); };   // never mirrored
    const G8 = o.gang, [SK, SK2] = SKINS[o.sk || 0], NV = G8 ? "#4a2f5e" : "#1f2c4c", NV2 = G8 ? "#352045" : "#142039", PA = G8 ? "#4a2f5e" : "#565d6b", PA2 = G8 ? "#352045" : "#434955", BT = "#16181d", t = o.t || 0, q = o.ph || 0, rm = o.rm;
    if (o.pose === "trip") {   // flat on his back, boots kicking in the air, the cap rolled off: slapstick, he gets back up
      const kick = rm ? 0 : Math.sin(t * 14) * 0.35;
      ell(c, "rgba(0,0,0,.25)", 2, 0, 30, 3.5);
      line(c, PA, 8, [8, -5, 20, -16 + kick * 8, 28, -24 - kick * 6]); line(c, PA2, 8, [8, -5, 22, -10 - kick * 6, 32, -14 + kick * 8]);
      box(c, BT, 25, -30 - kick * 6, 9, 7, 2.5); box(c, BT, 30, -19 + kick * 8, 9, 7, 2.5);
      c.fillStyle = lin(c, 0, -14, 0, 0, [NV, NV2]); rr(c, -16, -13, 26, 13, 6); c.fill();
      if (!G8) say(c, "ICE", -3, -6.5, 8, "#ffffff", { weight: 900 });
      ell(c, SK, -22, -7, 7.5, 7); box(c, "#0d0f14", -27, -11, 9, 3.4, 1.6); ell(c, SK2, -28.5, -5, 2.2, 1.8);
      const rx = -40 - (rm ? 0 : mod(t * 18, 14)); c.save(); c.translate(rx, -4); c.rotate(rm ? 0 : t * 6); ell(c, NV, 0, 0, 6, 4.5); box(c, NV2, -1, -5, 8, 2.2, 1); c.restore();   // the cap rolling away
      say(c, "!?", 0, -36 - (rm ? 0 : Math.abs(Math.sin(t * 5)) * 4), 15, "#ff3d8b", { weight: 900, stroke: "#ffffff", sw: 3 });
      return;
    }
    let bob = 0, lean = 0, lf, lb, af, ab;
    if (o.pose === "run") { lf = [0.8 * Math.sin(q), 0.25 + 1.1 * Math.max(0, Math.cos(q))]; lb = [0.8 * Math.sin(q + Math.PI), 0.25 + 1.1 * Math.max(0, Math.cos(q + Math.PI))];
      af = [-0.9 * Math.sin(q), 1.4]; ab = [0.9 * Math.sin(q), 1.4]; bob = -Math.abs(Math.cos(q)) * 2.2; lean = 0.2; }
    else if (o.pose === "walk") { lf = [0.38 * Math.sin(q), 0.15 + 0.5 * Math.max(0, Math.cos(q))]; lb = [0.38 * Math.sin(q + Math.PI), 0.15 + 0.5 * Math.max(0, Math.cos(q + Math.PI))];
      af = [-0.45 * Math.sin(q), 0.5]; ab = [0.45 * Math.sin(q), 0.5]; bob = -Math.abs(Math.cos(q)) * 1.2; lean = 0.04; }
    else if (o.pose === "air") { lf = [0.9, 1.4]; lb = [-0.4, 0.9]; af = [2.4, 0.5]; ab = [-1.2, -0.5]; lean = 0.1; }
    else if (o.pose === "tired") { const p = rm ? 0 : Math.sin(t * 7) * 0.05; lf = [0.35, 0.7]; lb = [-0.1, 0.55]; af = [0.55, 0.15]; ab = [0.4, 0.2]; lean = 0.62 + p; bob = 4; }
    else if (o.pose === "grab") { lf = [0.45, 0.4]; lb = [-0.3, 0.3]; af = [1.75, -0.1]; ab = [1.5, 0.1]; lean = 0.08; }
    else if (o.pose === "huh") { lf = [0.08, 0.04]; lb = [-0.08, 0.04]; af = [0.3, 2.3]; ab = [-0.15, 0.3]; lean = -0.12; }
    else { lf = [0.1, 0.05]; lb = [-0.1, 0.05]; af = [0.2, 0.35]; ab = [-0.15, 0.35]; }
    if (o.pose === "dizzy" && !rm) { c.save(); c.rotate(Math.sin(t * 9) * 0.08); }
    const hx = 0, hy = -30 + bob;
    const leg = ([a, b], col) => { const kx = hx + Math.sin(a) * 15, ky = hy + Math.cos(a) * 15, s = a - b, fx = kx + Math.sin(s) * 15, fy = ky + Math.cos(s) * 15;
      line(c, col, 9, [hx, hy, kx, ky, fx, fy]); box(c, col === PA ? "#6a7280" : "#4d5360", kx - 3.5, ky - 3, 7, 5, 2);   // a cargo pocket
      c.save(); c.translate(fx, fy); c.rotate(s * 0.55); box(c, BT, -4.5, -4.5, 14, 7, 3); box(c, "#050608", -5, 1.6, 15, 2.6, 1); c.restore(); };
    const sh = { x: hx + Math.sin(lean) * 22, y: hy - Math.cos(lean) * 22 };
    const arm = ([a, b], col, skin) => { const ex = sh.x + Math.sin(a) * 11, ey = sh.y + Math.cos(a) * 11, s = a + b, wx = ex + Math.sin(s) * 10, wy = ey + Math.cos(s) * 10;
      line(c, col, 7.5, [sh.x, sh.y, ex, ey, wx, wy]); ell(c, skin, wx + Math.sin(s) * 2, wy + Math.cos(s) * 2, 3.3, 3.3); };
    arm(ab, NV2, SK2); leg(lb, PA2); leg(lf, PA);
    c.save(); c.translate(hx, hy); c.rotate(lean);
    box(c, "#22252c", -11, -4, 22, 7, 3);   // belt
    c.fillStyle = lin(c, -12, -26, 12, 0, ["#2c3c63", NV, NV2]); rr(c, -12, -25, 24, 23, 8); c.fill();
    ell(c, "rgba(255,255,255,.07)", -3, -16, 7, 9);   // a little shine on the nylon
    line(c, "rgba(0,0,0,.35)", 0.9, [7, -24, 7, -3]); box(c, "#3a4a72", -9, -26, 18, 4, 2);   // zipper + collar
    if (G8) {   // v49.5 Playa Neón: a cartoon gangster: purple pinstripe suit, white shirt, pink tie (no symbols, no weapons)
      c.strokeStyle = "rgba(255,255,255,.22)"; c.lineWidth = 0.6; for (let k = -9; k <= 9; k += 3.6) { c.beginPath(); c.moveTo(k, -24); c.lineTo(k, -3); c.stroke(); }
      poly(c, "#ffffff", [-5, -25, 5, -25, 0, -13]); poly(c, "#ff3d8b", [-1.4, -23, 1.4, -23, 2, -14, 0, -11.5, -2, -14]);
    } else say(c, "ICE", -1.5, -13, 9.5, "#ffffff", { weight: 900, font: UI });
    c.translate(2.5, -32);   // head
    box(c, SK2, -4, 4, 7, 5, 2);
    ell(c, lin(c, -7, -7, 8, 8, [SK, SK, SK2]), 0.5, 0, 8.4, 8.8);
    ell(c, SK2, -4.5, 1, 1.8, 2.5);   // ear
    ell(c, SK2, 8.4, 2, 2.6, 2.4);   // a big round cartoon nose
    if (o.st2) { c.fillStyle = "#2a1c14"; c.beginPath(); c.moveTo(3.4, 4.6); c.quadraticCurveTo(6.6, 2.6, 9.8, 4.6); c.quadraticCurveTo(6.6, 6.6, 3.4, 4.6); c.fill(); }
    if (o.pose === "tired" || o.pose === "grab") ell(c, "#5a2a22", 6.4, 6.6, 1.8, o.pose === "tired" ? 2.2 : 1.2); else line(c, "#5a2a22", 0.9, [4.6, 7, 7.2, 6.6]);
    if (o.pose === "dizzy") { line(c, "#1b120c", 0.9, [3, -2.5, 6, -0.5]); line(c, "#1b120c", 0.9, [3, -0.5, 6, -2.5]); }
    else { box(c, "#0d0f14", 1.2, -3.6, 8.4, 4.2, 1.8); line(c, "#0d0f14", 1.1, [1.5, -2, -4, -1.6]); ell(c, "rgba(255,255,255,.75)", 6.6, -2.6, 1.1, 0.7, -0.4); }   // sunglasses with a glint
    if (G8) { box(c, "#2a1c2e", -12, -5.6, 26, 2.8, 1.4); box(c, "#3b2a40", -7.5, -14, 16, 9, 3); box(c, "#ff3d8b", -7.5, -7.6, 16, 2.2, 0.6); }   // a fedora with a pink band
    else { c.fillStyle = lin(c, 0, -10, 0, -2, ["#2c3c63", NV2]); c.beginPath(); c.ellipse(0.2, -3, 8.9, 7.6, 0, Math.PI, 0); c.fill();   // the cap
    box(c, NV2, 3, -4.6, 11.5, 2.6, 1.3); box(c, "#3a4a72", -8.6, -4.4, 17.6, 1.6, 0.8); }
    if (o.pose === "run" || o.pose === "tired") { ell(c, "rgba(170,220,255,.9)", -7, -6 - (rm ? 0 : mod(t * 9, 4)), 1.3, 2); ell(c, "rgba(170,220,255,.9)", 11, -9 + (rm ? 0 : mod(t * 7, 3)), 1.1, 1.7); }   // sweat
    c.restore();
    arm(af, NV, SK);
    if (o.pose === "dizzy") { if (!rm) c.restore();
      for (let k = 0; k < 3; k++) { const a = (rm ? 0 : t * 5) + k * 2.1, sx = 3 + Math.cos(a) * 13, sy = -72 + Math.sin(a) * 3.5, col = ["#ff3d8b", "#3ee8eb", "#ffffff"][k];
        poly(c, col, [sx, sy - 4, sx + 1.2, sy - 1.2, sx + 4, sy, sx + 1.2, sy + 1.2, sx, sy + 4, sx - 1.2, sy + 1.2, sx - 4, sy, sx - 1.2, sy - 1.2]); } }
    if (o.pose === "dizzy" || o.pose === "huh") say(c, "?", 4, -86 + (rm ? 0 : Math.sin(t * 6) * 2), 17, "#ff3d8b", { weight: 900, stroke: "#ffffff", sw: 3 });
    if (o.pose === "grab") say(c, "!", 6, -86, 20, "#ff3d8b", { weight: 900, stroke: "#ffffff", sw: 3 });
    if (o.pose === "tired" && !rm) for (let k = 0; k < 2; k++) { const a = mod(t * 1.6 + k * 0.5, 1); ell(c, `rgba(255,255,255,${(0.7 * (1 - a)).toFixed(2)})`, 18 + a * 14, -50 - a * 10, 3 + a * 4, 2.4 + a * 3); }   // huff, puff
  }
  function iceSuv(c, x, w, night, open) {   // a dark unmarked SUV (faces right), the driver's door swings open when an agent hops out
    ell(c, "rgba(0,0,0,.3)", x + w / 2, 0, w / 2 + 4, 4);
    c.fillStyle = lin(c, 0, -54, 0, -8, ["#3a404c", "#20242c", "#121419"]); c.beginPath();
    c.moveTo(x + 4, -12); c.lineTo(x + 2, -34); c.quadraticCurveTo(x + 3, -40, x + 10, -40); c.lineTo(x + 16, -54); c.lineTo(x + w - 34, -54); c.lineTo(x + w - 20, -40);
    c.lineTo(x + w - 6, -38); c.quadraticCurveTo(x + w, -36, x + w, -28); c.lineTo(x + w, -12); c.closePath(); c.fill();
    poly(c, lin(c, x, -52, x + w, -40, ["#2b3a4e", "#4e6680", "#2b3a4e"]), [x + 19, -51, x + 52, -51, x + 52, -41, x + 13, -41]);
    poly(c, lin(c, x, -52, x + w, -40, ["#2b3a4e", "#4e6680", "#2b3a4e"]), [x + 56, -51, x + w - 36, -51, x + w - 25, -41, x + 56, -41]);
    c.fillStyle = "rgba(255,255,255,.22)"; c.beginPath(); c.moveTo(x + 64, -41); c.lineTo(x + 72, -51); c.lineTo(x + 77, -51); c.lineTo(x + 69, -41); c.fill();
    line(c, "#8a939c", 1.2, [x + 6, -27, x + w - 2, -27]); box(c, "#c9d0d8", x + 18, -56, w - 56, 2, 1);   // chrome trim + roof rails
    line(c, "rgba(0,0,0,.45)", 0.9, [x + 54, -41, x + 54, -14]); line(c, "rgba(0,0,0,.45)", 0.9, [x + w - 30, -40, x + w - 30, -14]);
    box(c, "#c9d0d8", x + 44, -34, 6, 1.6, 0.8); box(c, "#c9d0d8", x + w - 42, -34, 6, 1.6, 0.8);
    box(c, "#d7262e", x + 1, -34, 3, 8, 1); ell(c, night ? "#fff6e0" : "#e8edf2", x + w - 3, -31, 3, 2.4);
    if (night) { c.fillStyle = "rgba(255,240,210,.22)"; c.beginPath(); c.moveTo(x + w - 2, -31); c.lineTo(x + w + 90, -44); c.lineTo(x + w + 90, -6); c.closePath(); c.fill(); }
    box(c, "#0b0c0f", x + 2, -14, w - 2, 5, 2);
    for (const wx of [x + 26, x + w - 26]) { ell(c, "#0b0c0f", wx, -10, 13, 13); ell(c, "#14161a", wx, -10, 10.5, 10.5); ell(c, lin(c, wx - 6, -16, wx + 6, -4, ["#e8edf2", "#7d848e"]), wx, -10, 6, 6); ell(c, "#2b2f38", wx, -10, 2, 2); }
    if (open) { poly(c, lin(c, x + w - 30, 0, x + w + 6, 0, ["#2a2f38", "#15171c"]), [x + w - 30, -40, x + w - 4, -48, x + w - 4, -20, x + w - 30, -14]); poly(c, "#3a4a5e", [x + w - 27, -40, x + w - 8, -46, x + w - 8, -36, x + w - 27, -32]); }
  }
  function flipflops(c, x, y, t, rm) {   // the 🩴 shield power-up: a pair of turquoise flip-flops with a twinkle
    const by = y + (rm ? 0 : Math.sin(t * 4 + 2) * 3);
    if (!rm) { c.fillStyle = "rgba(62,232,235,.22)"; c.beginPath(); c.arc(x + 15, by + 9, 19 + Math.sin(t * 5) * 1.5, 0, Math.PI * 2); c.fill(); }
    for (const [dx, rot] of [[8, -0.35], [21, 0.3]]) { c.save(); c.translate(x + dx, by + 9); c.rotate(rot);
      ell(c, lin(c, 0, -9, 0, 9, ["#3ee8eb", "#00a7a0"]), 0, 0, 5.5, 9.5); ell(c, "#ffffff", 0, -0.5, 3.6, 7.2); ell(c, "#7ff2f3", 0, -0.5, 3, 6.6);
      line(c, "#ff3d8b", 1.8, [-3.6, 1.5, 0, -5, 3.6, 1.5]); c.restore(); }
    if (!rm) { const a = t * 3, sx = x + 15 + Math.cos(a) * 17, sy = by + 9 + Math.sin(a) * 12; poly(c, "#ffffff", [sx, sy - 4, sx + 1, sy - 1, sx + 4, sy, sx + 1, sy + 1, sx, sy + 4, sx - 1, sy + 1, sx - 4, sy, sx - 1, sy - 1]); }
  }

  function heart(c, x, y, r, col) { c.fillStyle = col; c.beginPath(); c.moveTo(x, y + r * 0.9); c.bezierCurveTo(x - r * 1.4, y - r * 0.1, x - r * 0.7, y - r * 1.25, x, y - r * 0.45); c.bezierCurveTo(x + r * 0.7, y - r * 1.25, x + r * 1.4, y - r * 0.1, x, y + r * 0.9); c.fill(); }
  function lowrider(c, x, y, night) {   // a candy-pink lowrider cruising the other way (faces left)
    c.fillStyle = lin(c, 0, y - 22, 0, y, ["#ff6fa8", "#ff3d8b", "#c21f66"]); rr(c, x, y - 16, 96, 14, 6); c.fill(); rr(c, x + 26, y - 28, 46, 14, 6); c.fill();
    glass(c, x + 30, y - 26, 18, 10, false); glass(c, x + 51, y - 26, 18, 10, false); line(c, "#e8edf2", 1.4, [x + 4, y - 9, x + 92, y - 9]);
    for (const wx of [x + 20, x + 76]) { ell(c, "#14161a", wx, y - 2, 9, 9); ell(c, lin(c, wx - 6, y - 8, wx + 6, y + 4, ["#ffffff", "#9aa3ad"]), wx, y - 2, 6, 6); ell(c, "#c9d0d8", wx, y - 2, 2, 2); }
    if (night) { c.fillStyle = "rgba(255,240,210,.35)"; c.beginPath(); c.moveTo(x + 2, y - 12); c.lineTo(x - 70, y - 26); c.lineTo(x - 70, y + 4); c.closePath(); c.fill(); ell(c, "#fff6e0", x + 3, y - 12, 2.5, 2.5); }
  }

  function bgSuv(c, x, y, k, dir, night) {   // v46: a far-lane ICE SUV in the street (just scenery): the same dark SUV, smaller, with a small "ICE" on the back door
    c.save(); c.translate(x, y); c.scale(k * dir, k); iceSuv(c, -62, 124, night, false); c.restore();
    c.save(); c.font = `800 ${(11 * k).toFixed(1)}px ${UI}`; c.textAlign = "center"; c.textBaseline = "middle"; c.fillStyle = night ? "rgba(214,222,230,.7)" : "rgba(214,222,230,.85)";
    c.fillText("ICE", x - 30 * k * dir, y - 20 * k); c.restore();   // never mirrored, whichever way it faces
  }

  // v49.4: how to play, short: 4 lines, an emoji each, big and bold (the same list on the title screen and under the game)
  const HOW = [["👆", "Tap to jump (or twice!)"], ["🚧", "Hop cones, carts & ICE"], ["☕", "Grab coffee & tacos"], ["🍻", "Reach Noche Caliente"]];
  const howList = (cls) => `<ul class="juan-how ${cls}" aria-label="How to play">${HOW.map(([i, t]) => `<li><span class="ic" aria-hidden="true">${i}</span><span>${t}</span></li>`).join("")}</ul>`;
  function mount(el, ctx) {
    const reduced = () => (ctx && ctx.reducedMotion ? ctx.reducedMotion() : matchMedia("(prefers-reduced-motion: reduce)").matches);
    const st = load();
    el.innerHTML = `
      <div class="juan-wrap">
        <canvas id="juan-cv" class="juan-cv no-swipe" width="${VW}" height="580" role="img" aria-label="The Juan That Got Away game screen. Tap it, or press Space, to jump."></canvas>
        <div id="juan-ov" class="juan-ov" aria-live="polite"></div>
      </div>
      <p class="juan-note" id="juan-note" aria-live="polite"></p>
      <div class="juan-controls" role="group" aria-label="Game controls">
        <button type="button" id="juan-jump" class="lot-btn lot-main juan-jump no-swipe">⤒ Jump</button>
        <button type="button" id="juan-pause" class="lot-btn"></button>
        <button type="button" id="juan-restart" class="lot-btn" aria-label="Restart level"><span aria-hidden="true">↺</span><span class="juan-lbl"> Restart level</span></button>
        <button type="button" id="juan-sound" class="lot-btn" aria-pressed="true"></button>
      </div>
      <div class="lot-rules juan-rules">${howList("juan-how-page")}</div>
      <p class="lot-stats" id="juan-stats"></p>
      <section class="juan-hs" id="juan-hs" aria-labelledby="juan-hs-t">
        <h3 class="juan-hs-t" id="juan-hs-t"><span aria-hidden="true">🏆</span> Top 10 Metiches</h3>
        <ol class="juan-hs-list" id="juan-hs-list" aria-live="polite"></ol>
        <p class="juan-hs-note" id="juan-hs-note" hidden></p>
        <p class="juan-affil">Parody. All characters are original; any resemblance to other works is parody. Not affiliated with any government agency (including ICE).</p>
        <p class="juan-hs-report"><a href="mailto:bexartalkradio@gmail.com?subject=Report%20a%20Top%2010%20name%20(Chisme)&amp;body=Which%20name%2C%20and%20why%3A%0A">Report a name</a> · nicknames are public; no real names or slurs</p>
      </section>`;
    const cv = el.querySelector("#juan-cv"), g = cv.getContext("2d", { alpha: false }), ov = el.querySelector("#juan-ov"), wrap = el.querySelector(".juan-wrap"), $ = (s) => el.querySelector(s);
    const HAT = `<svg class="gfs-juan-hat" viewBox="0 0 32 20" aria-hidden="true" focusable="false"><path d="M4 15a12 12 0 0 1 24 0z" fill="#fff"/><rect x="1" y="14" width="30" height="4" rx="2" fill="#e1e6ea"/><rect x="14.5" y="3.4" width="3" height="11" rx="1.2" fill="#c9d0d8"/></svg>`;
    const FS = root.ChismeJuegos && root.ChismeJuegos.fullscreen;
    // v49.5: leaving full screen (✕ / Escape) with points ends the run → the Top 10 sheet if the score makes it
    const fs = FS ? FS(el, { title: "The Juan That Got Away", badgeClass: "gfs-juan", badge: `${HAT}<span class="gfs-juan-t" aria-hidden="true">The Juan <b>That Got Away</b></span>`,
      onEnter: () => fit(), onResize: () => fit(), onExit: () => { const m = mode, sc = score, lv = level; pause(); fit(); if (["run", "oops", "paused", "clear", "win"].includes(m) && sc > 0) offer(sc, lv); }, onLeave: () => { pause(); fit(); } }) : { enter() {}, exit() {}, on: false };
    // ---- sound: small WebAudio blips (🔇 mutes)
    let ac = null;
    const audio = () => { if (!ac) { const A = window.AudioContext || window.webkitAudioContext; if (A) try { ac = new A(); } catch (e) {} } if (ac && ac.state === "suspended") ac.resume(); return ac; };
    function beep(f, d = 0.08, f2 = null, type = "square", vol = 0.04, at = 0) {
      if (st.muted) return; const a = audio(); if (!a) return;
      try { const o = a.createOscillator(), v = a.createGain(), t0 = a.currentTime + at;
        o.type = type; o.frequency.setValueAtTime(f, t0); if (f2) o.frequency.exponentialRampToValueAtTime(f2, t0 + d);
        v.gain.setValueAtTime(vol, t0); v.gain.exponentialRampToValueAtTime(0.0008, t0 + d);
        o.connect(v); v.connect(a.destination); o.start(t0); o.stop(t0 + d + 0.02); } catch (e) {}
    }
    const SFX = {
      jump: () => beep(330, 0.11, 660, "triangle", 0.06), jump2: () => beep(520, 0.09, 900, "triangle", 0.05), coin: () => { beep(988, 0.05, null, "square", 0.03); beep(1319, 0.08, null, "square", 0.03, 0.05); },
      power: () => [523, 659, 784, 1047].forEach((f, i) => beep(f, 0.07, null, "triangle", 0.06, i * 0.06)),
      salud: () => { beep(1568, 0.06, null, "sine", 0.06); beep(2093, 0.12, null, "sine", 0.05, 0.06); },
      ouch: () => beep(220, 0.14, 110, "sawtooth", 0.035), yap: () => { beep(1200, 0.04, 900, "square", 0.03); beep(1250, 0.04, 950, "square", 0.03, 0.09); },
      splash: () => beep(900, 0.18, 200, "sawtooth", 0.02),
      oops: () => [392, 330, 262, 196].forEach((f, i) => beep(f, 0.12, null, "triangle", 0.06, i * 0.1)),
      clear: () => [523, 659, 784, 659, 784, 1047].forEach((f, i) => beep(f, 0.1, null, "triangle", 0.06, i * 0.09)),
      check: () => { beep(784, 0.07, null, "triangle", 0.05); beep(1047, 0.1, null, "triangle", 0.05, 0.07); },
      fuera: () => [659, 880, 1175].forEach((f, i) => beep(f, 0.09, null, "triangle", 0.06, i * 0.07)),
      whistle: () => { beep(1760, 0.12, 2200, "sine", 0.05); beep(1760, 0.16, 2400, "sine", 0.05, 0.16); },
      shield: () => beep(700, 0.18, 300, "sawtooth", 0.03), bonk: () => beep(180, 0.12, 90, "square", 0.04),
    };
    // ---- state
    let oopsMsg = OOPS[0], level = 1, ents = [], hero, camX = 0, score = 0, ckScore = 0, ck = 0, mode = "title", t = 0, raf = null, last = 0, shake = 0, parts = [], msgT = 0, msg = "";
    let bgIce = [], bgNext = 4, bgN = 0;   // v46: the ICE SUVs in the far lane (decor: not in ents, they never touch Juan)
    let fx = [], fxMade = 0, dustT = 0, paused = false, beersGot = 0, fueraT = 0, fueras = 0, caughtN = 0, caughtBy = "", forceCaught = "";
    let S = 1, VH = 580, GS = VH - ROADH, dpr = 1, dprCap = 3, cssW = VW, cache = {}, perf = { n: 0, sum: 0 };
    const cam = (x) => Math.min(x - HERO_X, CAM_END);
    const L = () => LEVELS[level - 1], P = () => SKY[L().time], isNight = () => L().time === "night";
    const par = () => (reduced() ? 0 : 1);
    function spawn(atCheck) {
      const x0 = CHECKS[atCheck];
      ents = buildLevel(level).filter((e) => !((e.t === "concha" || e.t === "beer" || e.t === "feria") && e.x < x0));
      for (const e of ents) if (e.t === "flag" && e.x <= x0) e.done = true;
      hero = { x: x0 + 8, y: -HERO_H, w: HERO_W, h: HERO_H, vy: 0, ground: true, jumps: 2, boost: 0, stumble: 0, inv: 0, frame: 0, health: HP, shield: 0 };
      camX = cam(hero.x); score = ckScore; parts = []; fx = []; msgT = 0; shake = 0; fueraT = 0; bgIce = []; bgNext = (reduced() ? 12 + Math.random() * 8 : 3 + Math.random() * 5) * (L().city ? 0.5 : 1);
    }
    // v46: now and then a dark ICE SUV drives by in the far lane, or sits parked at the far curb (drawn with the road, so it scrolls with it).
    // Reduce motion: parked ones only, and rarer.
    const BG_LANE = 50, BG_K = 0.6, BG_W = 124 * BG_K;
    function bgSpawn(kind) {
      const rm = reduced(), drive = kind ? kind === "drive" : !rm && Math.random() < 0.6, dir = drive ? (Math.random() < 0.5 ? -1 : 1) : (Math.random() < 0.5 ? -1 : 1);
      const vx = !drive ? 0 : dir < 0 ? -(60 + Math.random() * 50) : L().speed + 70 + Math.random() * 60;   // toward Juan, or overtaking him
      const x = !drive || dir < 0 ? camX + VW + BG_W / 2 + 10 + (drive ? 0 : Math.random() * 120) : camX - BG_W / 2 - 10;
      bgIce.push({ x, vx, dir, kind: drive ? "drive" : "parked", y: BG_LANE - (drive ? 0 : 12) }); bgN++;
    }
    function bgTick(dt) {
      for (const b of bgIce) b.x += b.vx * dt;
      bgIce = bgIce.filter((b) => b.x - camX > -BG_W - 40 && b.x - camX < VW + BG_W + 260);
      bgNext -= dt;
      if (bgNext <= 0) { const rm = reduced(); if (bgIce.length < 2 && camX < CAM_END - VW) bgSpawn(); bgNext = (rm ? 20 + Math.random() * 14 : 7 + Math.random() * 10) * (L().city ? 0.5 : 1); }
    }
    function startLevel(n, keepScore) {
      if (n !== level) cache = {};
      if (!keepScore) run = { sent: false, offered: 0 };   // v49.5: a fresh run (its score can go on the board once)
      level = n; ck = 0; paused = false; if (!keepScore) ckScore = 0; if (n === 1 && !keepScore) beersGot = 0; spawn(0); mode = "run"; overlay(null); fs.enter(); fit(); healthCheck();
      $("#juan-note").textContent = `Level ${n}: ${L().name}. ${L().hint}`; loop(); ctrl();
    }
    function overlay(html, cls = "") { ov.className = "juan-ov" + (html ? " on " + cls : ""); ov.innerHTML = html || ""; }
    const speed = () => L().speed * (reduced() ? 0.88 : 1) * (hero.boost > 0 ? 1.4 : 1) * (hero.stumble > 0 ? 0.55 : 1);
    const played = () => { try { root.dispatchEvent(new CustomEvent("chisme-game-play", { detail: "juan" })); } catch (e) {} };   // v42: anonymous counts
    function jump() {
      if (mode === "title") { played(); startLevel(1); return; }
      if (mode !== "run") return;
      audio();
      if (hero.ground) { hero.vy = JUMP; hero.ground = false; hero.jumps = 1; hero.jumpAt = t; SFX.jump(); puff(hero.x + 10, 0 + (hero.y + hero.h), skinNow() === "classic" ? 10 : 4, "dust"); }
      else if (hero.jumps > 0) { hero.vy = JUMP2; hero.jumps = 0; hero.jumpAt = t; SFX.jump2(); puff(hero.x + 13, hero.y + hero.h, 6, "spark"); }
    }
    function landed(h) {   // v49.5: for the landing FX (El Lowrider shakes the ground)
      h.landAt = t; h.landX = h.x + h.w / 2; h.landY = h.y + h.h;
      if (skinNow() === "lowrider" && !reduced()) { shake = Math.max(shake, 0.16); puff(h.landX - 6, h.landY, 6, "dust"); }
    }
    function release() { if (mode === "run") hero.vy = trim(hero.vy); }   // a short tap = a slightly shorter hop (v49.7: still clears an agent)
    // ---- particles (none with reduce motion)
    function puff(x, y, n, kind) {
      if (reduced()) return;
      for (let i = 0; i < n; i++) {
        fxMade++;
        if (kind === "dust") fx.push({ k: kind, x: x + Math.random() * 8 - 4, y: y - 2 - Math.random() * 3, vx: -20 - Math.random() * 50, vy: -14 - Math.random() * 30, life: 0.35 + Math.random() * 0.3, r: 2 + Math.random() * 3 });
        else if (kind === "drop") fx.push({ k: kind, x, y, vx: Math.random() * 80 - 40, vy: -60 - Math.random() * 80, life: 0.5, r: 1.6 });
        else { const a = (i / n) * Math.PI * 2 + Math.random() * 0.6, sp = 50 + Math.random() * 90;
          fx.push({ k: "spark", x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 20, life: 0.45 + Math.random() * 0.35, c: ["#ff3d8b", "#3ee8eb", "#ffffff", "#ff8a00"][i % 4] }); }
      }
      if (fx.length > 200) fx.splice(0, fx.length - 200);
    }
    function oops(by) {   // out of health, or (v46) an agent caught up with him: a big "¡Ay no!" (v47: or ¡Ay cabrón! / ¡Chingao! / ¡Pinche ICE! / ¡Ay, vengo mamá!), then back to the last 🚩
      mode = "oops"; oopsMsg = by ? (forceCaught ? (lastCaught = forceCaught) : pickCaught()) : OOPS[Math.floor(Math.random() * OOPS.length)]; forceCaught = ""; SFX.oops(); if (!reduced()) shake = 0.3;
      if (by) { caughtN++; caughtBy = by.t; by.st = "grab"; } fueraT = 0;
      st.best = Math.max(st.best, score); save(st); stats();
      const where = ck ? "checkpoint 🚩" : "start";
      overlay(`<p class="sr-only">${oopsMsg}</p><p class="juan-oops">${by ? `Caught! Juan tries again from the ${where}.` : `Juan's worn out. Try again from the ${where}.`}</p>`, "soft oops");
      setTimeout(() => { if (mode === "oops") { spawn(ck); mode = "run"; overlay(null); } }, 1400);
    }
    function ouch(e) {
      const h = hero, [dmg, label] = HAZ[e.t];
      e.hit = true; if (e.t === "cone") e.down = true; if (e.t === "cart") e.bonk = 0.01; if (e.t === "chancla") e.gone = true;
      if (e.t === "sprinkler") { SFX.splash(); for (let i = 0; i < 6; i++) puff(h.x + 13, h.y + 20, 1, "drop"); } else if (e.t === "chihuahua") SFX.yap(); else SFX.ouch();
      if (h.inv > 0) return;   // still blinking from the last bump
      h.health = Math.max(0, h.health - dmg); h.inv = 1.0; h.stumble = 0.45; msg = `${label} −${dmg}`; msgT = 1.3; if (!reduced()) shake = 0.12;
      puff(h.x + 13, h.y + h.h - 4, 5, "dust");
      if (h.health <= 0) oops();
    }
    function pickup(e) {
      const h = hero; e.gone = true;
      if (e.t === "feria") { score += 25; SFX.coin(); msg = "Money bag! +25"; msgT = 0.9; puff(e.x + 12, e.y + 12, 8, "spark"); }
      else if (e.t === "concha") { score += 10; SFX.coin(); puff(e.x + 11, e.y + 8, 5, "spark"); }
      else if (e.t === "beer") { h.health = Math.min(HP, h.health + 8); score += 15; if (!e.mt) beersGot++; SFX.salud(); msg = e.mt ? "Martini! +8 health" : "Cheers! +8 health"; msgT = 1.1; puff(e.x + 12, e.y + 10, 10, "spark"); }
      else if (e.t === "coffee") { h.boost = 5; score += 50; SFX.power(); msg = "Coffee! Speed boost"; msgT = 1.5; puff(e.x + 11, e.y + 14, 14, "spark"); }
      else if (e.t === "flipflops") { h.shield = 1; score += 50; SFX.power(); msg = "Flip-flops! Shield on"; msgT = 1.5; puff(e.x + 15, e.y + 9, 14, "spark"); }
      else if (e.t === "taco") { h.health = Math.min(HP, h.health + 30); score += 50; SFX.power(); msg = "Breakfast taco! +30 health"; msgT = 1.5; puff(e.x + 16, e.y + 10, 14, "spark"); }
    }
    // ---- v46: the ICE agents
    function fuera(pts) { fueras++; fueraT = 1.1; score += pts; SFX.fuera(); puff(hero.x + 13, hero.y - 6, 10, "spark"); }
    function escape(e) { if (e.away) return; e.away = true; fuera(100); }
    function iceStep(e, h, dt) {   // true = Juan got caught
      e.tt = Math.max(0, (e.tt || 0) - dt);
      if (e.t === "agent") {
        if (e.st === "walk") { e.x += e.vx * (e.vx > 0 ? AWAY : 1) * dt;   // v49.7: heading the same way as Juan he only ambles (¼ pace), so a jump still carries Juan past him
          if (e.x < e.home - 90) e.vx = Math.abs(e.vx); if (e.x > e.home + 10) e.vx = -Math.abs(e.vx);
          const cone = ents.find((k) => k.t === "cone" && !k.down && Math.abs(k.x + 12 - (e.x + 15)) < 7);
          if (cone) { e.st = "trip"; e.tt = 2.4; cone.down = true; SFX.bonk(); puff(e.x + 15, -4, 6, "dust"); } }
        else if (e.tt === 0 && e.st !== "grab") e.st = "walk";
      } else {   // the chaser who hopped out of an SUV
        if (e.st === "chase") {
          const sp = L().speed * (reduced() ? 0.88 : 1); e.x += sp * dt;   // as fast as Juan on a normal stride: a bump (a stumble) lets him gain, ☕ coffee leaves him behind
          e.run = (e.run || 0) + sp * dt * 0.09;
          e.vy = (e.vy || 0) + GRAV * dt; e.y += e.vy * dt; if (e.y >= -e.h) { e.y = -e.h; e.vy = 0; e.air = false; }
          if (!e.air) {
            const cone = ents.find((k) => k.t === "cone" && Math.abs(k.x + 12 - (e.x + 15)) < 7);
            if (cone) { e.st = "trip"; cone.down = true; SFX.bonk(); puff(e.x + 15, -4, 6, "dust"); escape(e); }
            else if (ents.some((k) => k !== e && !k.gone && (HAZ[k.t] || SOLID.includes(k.t) || k.t === "agent") && k.x - (e.x + e.w) > 0 && k.x - (e.x + e.w) < 34)) { e.vy = JUMP * 0.95; e.air = true; }
          }
          if (e.st === "chase" && (e.tt === 0 || h.x - (e.x + e.w) > 150)) { e.st = "tired"; e.y = -e.h; escape(e); }   // out of breath: Juan got away
        }
        else if (e.st === "dizzy" && e.tt === 0) e.st = "tired";
      }
      const danger = (e.t === "agent" && e.st === "walk") || (e.t === "chaser" && e.st === "chase");
      if (danger && h.inv <= 0 && hit(h, e, 5)) {
        if (h.shield > 0) { h.shield = 0; h.inv = 1.2; e.st = "dizzy"; e.tt = 2.5; SFX.shield(); msg = "Flip-flops! He's dizzy"; msgT = 1.3; score += 100; puff(e.x + 15, e.y + 6, 10, "spark"); if (e.t === "chaser") escape(e); }
        else { oops(e); return true; }
      }
      if (e.t === "agent" && !e.passed && h.x > e.x + e.w) { e.passed = true; if (e.st === "walk") { e.st = "huh"; e.tt = 1.3; e.vx = Math.abs(e.vx); } fuera(50); }   // hopped right over him
      return false;
    }
    function clear() {
      const name = L().name; score += 500; ckScore = score; st.best = Math.max(st.best, score);
      SFX.clear(); puff(hero.x + 13, hero.y + 10, 18, "spark");
      if (level === LEVELS.length) {
        mode = "win"; st.levelMax = LEVELS.length; st.beers = Math.max(st.beers || 0, beersGot); save(st); stats();
        if (!reduced()) for (let i = 0; i < 120; i++) parts.push({ x: Math.random() * VW, y: -Math.random() * VH, vy: 40 + Math.random() * 70, vx: Math.random() * 30 - 15, r: Math.random() * 6, c: ["#00b8b0", "#ff3d8b", "#ff8a00", "#c9d0d8", "#ffffff"][i % 5] });
        overlay(`<p class="juan-big">Cheers, Juan!</p><p class="juan-win-line">From Noche Caliente to the beach at Playa Neón: the Juan That Got Away made it to his vacation. Beach time!</p><p class="juan-win-score">Final score <b>${num(score)}</b></p><button type="button" class="lot-btn lot-main" data-act="again">▶ Play again</button><p class="juan-btns">${skinBtn()}${skinHint()}</p>`, "win");
        const final = score; setTimeout(() => { if (el.isConnected) offer(final, LEVELS.length); }, reduced() ? 600 : 1800);   // v49.5: the run's done → the board?
        $("#juan-note").innerHTML = `🎉 Friday shift done, cold ones at Noche Caliente, then a vacation at Playa Neón, from the hotel to the beach. Cheers! <span class="juan-score">Final score <b>${num(score)}</b> · Best <b>${num(st.best)}</b></span> <button type="button" class="lot-btn lot-main" data-act="again">▶ Play again</button>`;
        return;
      }
      if (level === 6) st.wins++;   // v49.5: made it to Noche Caliente (Playa Neón is the celebration after)
      st.levelMax = Math.max(st.levelMax, level + 1); save(st); stats();
      mode = "clear";
      overlay(`<p class="juan-big">You made it to ${name}!</p><p class="juan-story">${L().done}</p><p>+500 · Score <b>${num(score)}</b></p><button type="button" class="lot-btn lot-main" data-act="next">▶ Level ${level + 1}: ${LEVELS[level].name}</button><p class="juan-btns">${OVER}${skinBtn()}${skinHint()}</p>`, "clear");
      $("#juan-note").textContent = `Next up: ${LEVELS[level].name}. ${LEVELS[level].hint}`;
    }
    function update(dt) {
      t += dt;
      for (const p of fx) { p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += (p.k === "dust" ? 40 : 260) * dt; }
      if (fx.length) fx = fx.filter((p) => p.life > 0);
      if (mode === "win") { for (const p of parts) { p.y += p.vy * dt; p.x += p.vx * dt; p.r += dt * 4; if (p.y > VH) p.y -= VH + 10; } return; }
      if (mode !== "run") return;
      const h = hero, vx = speed(), wasGround = h.ground;
      h.boost = Math.max(0, h.boost - dt); h.stumble = Math.max(0, h.stumble - dt); h.inv = Math.max(0, h.inv - dt); fueraT = Math.max(0, fueraT - dt);
      h.x += vx * dt; h.frame += vx * dt * 0.09;
      const prevBottom = h.y + h.h;
      h.vy = fall(h.vy, dt); h.y += h.vy * dt; h.ground = false;
      if (h.y + h.h >= 0) { h.y = -h.h; h.vy = 0; h.ground = true; h.jumps = 2; if (!wasGround) landed(h); }
      for (const e of ents) {
        if (e.gone || e.x > h.x + 760 || e.x + e.w < h.x - 260) continue;
        if (e.t === "cart") { if (!e.on && e.x - h.x < 560) e.on = true; if (e.on) { e.x += (e.bonk ? 150 : e.vx) * dt; if (e.bonk) e.bonk += dt; } }
        else if (e.t === "chihuahua") { e.x += e.vx * dt; if (e.x < e.home - 70) e.vx = Math.abs(e.vx); if (e.x > e.home + 20) e.vx = -Math.abs(e.vx); }
        else if (e.t === "chancla") { e.y = -e.h - Math.abs(Math.sin(t * 3.2 + e.ph)) * 46; if (e.x - h.x < 520) e.x -= 28 * dt; }
        else if (e.t === "sprinkler") e.on = mod(t + e.ph, 2.4) < 1.3;
        if (e.t === "agent" || e.t === "chaser") { if (iceStep(e, h, dt)) return; continue; }
        if (e.t === "suv" && !e.out && h.x > e.x + e.w + 34) {   // an agent hops out and gives chase
          e.out = true; ents.push({ t: "chaser", x: h.x - 74, y: -64, w: 30, h: 64, vy: 0, st: "chase", tt: 3.4, run: 0, sk: e.sk, st2: !!(e.sk % 2) });
          msg = VAMONOS; msgT = 1.3; SFX.whistle();
        }
        if (e.t === "flag") { if (!e.done && h.x >= e.x) { e.done = true; ck = CHECKS.indexOf(e.x); ckScore = score; SFX.check(); msg = "Checkpoint! 🚩"; msgT = 1.2; puff(e.x + 16, -60, 12, "spark"); } continue; }
        if (SOLID.includes(e.t)) {
          if (h.x + h.w - 3 > e.x && h.x + 3 < e.x + e.w) {
            if (h.vy >= 0 && prevBottom <= e.y + 6 && h.y + h.h >= e.y) { h.y = e.y - h.h; h.vy = 0; h.ground = true; h.jumps = 2; if (!wasGround) landed(h); }   // landed on top
            else if (h.y + h.h > e.y + 6 && h.x + h.w - 3 < e.x + 14) { h.x = e.x - h.w + 3; h.stumble = 0.35; }   // bumped the side: a stumble
          }
          continue;
        }
        if (HAZ[e.t]) {
          if (e.hit) continue;
          let touch;
          if (e.t === "pothole") touch = h.ground && h.y + h.h >= -1 && h.x + h.w / 2 > e.x + 8 && h.x + h.w / 2 < e.x + e.w - 8;
          else if (e.t === "sprinkler") touch = e.on && h.x + h.w - 4 > e.x - 22 && h.x + 4 < e.x + e.w + 22 && h.y + h.h > -88;
          else if (e.t === "cone" && e.down) touch = false;
          else touch = hit(h, e, 4);
          if (touch) { ouch(e); if (mode !== "run") return; }
          else if (!e.passed && h.x > e.x + e.w) { e.passed = true; score += 25; }   // a clean hop over it
          continue;
        }
        if (hit(h, e, 0)) pickup(e);
      }
      if (h.ground && !wasGround) puff(h.x + 13, h.y + h.h, 6, "dust");
      else if (h.ground) { dustT -= dt; if (dustT <= 0) { dustT = h.boost > 0 ? 0.06 : 0.14; puff(h.x + 4, h.y + h.h, 1, "dust"); } }
      camX = cam(h.x); bgTick(dt);
      if (h.x >= END) clear();
      msgT = Math.max(0, msgT - dt); shake = Math.max(0, shake - dt);
    }

    // ================= rendering =================
    function makeLayer(period, height, k, fn, tint, night, ls = 1) {   // ls: the layer's size on screen (1.3 = drawn 30% bigger)   // pre-render a repeating strip into tiles (≤ TILE units wide each)
      const tiles = [];
      for (let x0 = 0; x0 < period; x0 += TILE) {
        const tw = Math.min(TILE, period - x0), c2 = document.createElement("canvas");
        const kk = k * ls; c2.width = Math.ceil(tw * kk) + 2; c2.height = Math.ceil(height * kk);
        const c = c2.getContext("2d");
        const pass = (p) => { for (const off of [0, -period, period]) { c.setTransform(kk, 0, 0, kk, (off - x0) * kk, height * kk); fn(c, p); } };
        pass("base");
        if (tint) { c.setTransform(1, 0, 0, 1, 0, 0); c.globalCompositeOperation = "source-atop"; c.fillStyle = tint; c.fillRect(0, 0, c2.width, c2.height); c.globalCompositeOperation = "source-over"; if (night) pass("lights"); }
        tiles.push({ cv: c2, x0 });
      }
      return { tiles, period, height, k: k * ls, ls };
    }
    function blit(Ly, f, baseY, start = 0) {
      const ls = Ly.ls, per = Ly.period * ls, off = mod(start + camX * f * par(), per), y = Math.round((baseY - Ly.height * ls) * S), sc = S * ls / Ly.k;
      for (let m = 0; m < 2; m++) for (const tl of Ly.tiles) {
        const sx = tl.x0 * ls - off + m * per; if (sx > VW || sx + TILE * ls < 0) continue;
        if (Math.abs(sc - 1) < 1e-6) g.drawImage(tl.cv, Math.round(sx * S), y); else g.drawImage(tl.cv, Math.round(sx * S), y, tl.cv.width * sc, tl.cv.height * sc);
      }
    }
    function makeSky() {
      const p = P(), c2 = document.createElement("canvas"); c2.width = cv.width; c2.height = Math.ceil(GS * S) + 2;
      const c = c2.getContext("2d"); c.setTransform(S, 0, 0, S, 0, 0);
      box(c, lin(c, 0, 0, 0, GS, p.sky), 0, 0, VW, GS + 2);
      const glow = (x, y, r, col) => { const gr = c.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, col); gr.addColorStop(1, "rgba(255,255,255,0)"); c.fillStyle = gr; c.fillRect(x - r, y - r, r * 2, r * 2); };
      if (p.sun === "synth") {   // v49.5 Playa Neón: a striped synthwave sun sinking into a pastel ocean
        const sy = GS - 112, R = 62; glow(180, sy, 170, "rgba(255,120,170,.55)");
        c.save(); c.beginPath(); c.arc(180, sy, R, 0, Math.PI * 2); c.clip(); box(c, lin(c, 0, sy - R, 0, sy + R, ["#ffe08a", "#ff9a5c", "#ff3d8b"]), 118, sy - R, 124, R * 2);
        const sk = lin(c, 0, 0, 0, GS, p.sky); for (let k = 0; k < 7; k++) { const yy = sy + 6 + k * 9, hh = 1.5 + k * 0.9; box(c, sk, 110, yy, 140, hh); } c.restore();
        box(c, lin(c, 0, GS - 112, 0, GS, ["#8fdbe6", "#5fb6cf", "#4a8fbf"]), 0, GS - 112, VW, 114);
        for (let k = 0; k < 9; k++) { const yy = GS - 106 + k * 9, ww = 70 - k * 6; box(c, `rgba(255,${150 + k * 8},${190 - k * 6},${(0.75 - k * 0.06).toFixed(2)})`, 180 - ww / 2, yy, ww, 2); }
        c.fillStyle = "rgba(255,255,255,.35)"; for (let k = 0; k < 26; k++) c.fillRect((k * 53) % VW, GS - 100 + ((k * 37) % 80), 10, 1.2); }
      else if (p.sun === "sun") { glow(286, 110, 90, "rgba(255,255,240,.55)"); ell(c, "#fffdf2", 286, 110, 22, 22); }
      else if (p.sun === "low") { glow(300, GS * 0.42, 110, "rgba(255,226,200,.6)"); ell(c, "#fff3e6", 300, GS * 0.42, 24, 24); }
      else if (p.sun === "set") { glow(90, GS - 150, 160, "rgba(255,160,110,.65)"); ell(c, lin(c, 0, GS - 190, 0, GS - 110, ["#ffd9b0", "#ff8a5c"]), 90, GS - 150, 36, 36); }
      else { const r = rng(9); for (let i = 0; i < 90; i++) { const a = 0.35 + r() * 0.65; ell(c, `rgba(255,255,255,${a.toFixed(2)})`, r() * VW, 70 + r() * (GS - 200), 0.5 + r() * 1.1, 0.5 + r() * 1.1); }
        glow(280, 116, 70, "rgba(200,220,255,.35)"); ell(c, "#f2f5fa", 280, 116, 18, 18); ell(c, p.sky[0], 288, 110, 16, 16); }
      return c2;
    }
    function makeCloud() {
      const p = P(); if (p.sun === "moon") return null;
      const k = Math.min(S, 2.5), c2 = document.createElement("canvas"); c2.width = Math.ceil(170 * k); c2.height = Math.ceil(70 * k);
      const c = c2.getContext("2d"); c.setTransform(k, 0, 0, k, 0, 0);
      if (p.sun === "synth") return null;   // a clear neon sky
      const top = p.sun === "set" ? "#ffd6e2" : "#ffffff", bot = p.sun === "set" ? "#e88aa8" : p.sun === "low" ? "#f2d4cc" : "#d6e6f2";
      c.fillStyle = lin(c, 0, 10, 0, 66, [top, top, bot]);
      for (const [x, y, r] of [[40, 44, 22], [70, 32, 28], [104, 36, 26], [130, 46, 20], [86, 50, 22], [56, 52, 18]]) { c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); }
      return { cv: c2, k };
    }
    function makeDest() {
      const c2 = document.createElement("canvas"); c2.width = Math.ceil(VW * S) + 2; c2.height = Math.ceil(360 * S);
      const ds = Math.min(1, (GS - 12 - 70) / DEST_H[level - 1]), c = c2.getContext("2d");
      c.setTransform(S * ds, 0, 0, S * ds, (VW * (1 - ds) / 2) * S, 360 * S); destination(c, L().d, isNight() || L().d === 4); return c2;
    }
    function caches() {
      if (cache.level !== level || cache.S !== S) cache = { level, S };
      if (cache.vh !== VH) { cache.sky = null; cache.dest = null; cache.vh = VH; }
      const p = P(), night = isNight();
      if (!cache.sky) cache.sky = makeSky();
      if (cache.cloud === undefined) cache.cloud = makeCloud();
      if (!cache.far) cache.far = makeLayer(1400, 400, Math.min(S, 2.2), (c) => farLayer(c, p, night), null);
      if (!cache.mid) cache.mid = makeLayer(2000, 240, S, (c, pass) => (L().beach ? beachLayer : L().city ? cityLayer : midLayer)(c, p, night, pass), p.tint, night, 1.1);   // v47: downtown for La Chamba
      if (!cache.dest) cache.dest = makeDest();
    }
    const destX = () => CAM_END;
    function road() {
      const p = P(), nt = isNight(), bot = ROADH, lane = 58;
      box(g, lin(g, 0, -30, 0, -10, ["#dfe3e8", "#c3c9d0"]), 0, -30, VW, 20);
      g.strokeStyle = "rgba(0,0,0,.13)"; g.lineWidth = 1; for (let x = -mod(camX, 64); x < VW; x += 64) { g.beginPath(); g.moveTo(x, -30); g.lineTo(x - 6, -10); g.stroke(); }
      box(g, "#a3a9b1", 0, -10, VW, 4); box(g, "#7d848e", 0, -6, VW, 3);
      box(g, lin(g, 0, -3, 0, bot - 44, ["#4b4e56", "#3b3d44", "#34363c"]), 0, -3, VW, bot - 41);
      const D = L().d, park = D === 1 || (D <= 3 && camX > END - 900);
      if (park) { g.fillStyle = "rgba(240,244,248,.85)"; for (let x = -mod(camX, 74); x < VW; x += 74) { g.save(); g.translate(x, 0); g.transform(1, 0, -0.35, 1, 0, 0); g.fillRect(0, 10, 3, 34); g.fillRect(0, lane + 22, 3, 44); g.restore(); } g.fillRect(0, lane + 6, VW, 2.5); }
      else { g.fillStyle = nt ? "rgba(220,226,234,.75)" : "#eef1f4"; for (let x = -mod(camX, 84); x < VW; x += 84) { rr(g, x, lane, 44, 4, 2); g.fill(); } }
      for (let x = -mod(camX, 560) + 210; x < VW; x += 560) { ell(g, "#2a2c32", x, lane + 34, 16, 4.5); ell(g, "#4a4d55", x, lane + 33.5, 12, 3); }
      for (const b of bgIce) if (b.kind === "parked") bgSuv(g, b.x - camX, b.y, BG_K, b.dir, false);   // (lights off)   // parked at the far curb, then the far-lane traffic
      for (const b of bgIce) if (b.kind === "drive") bgSuv(g, b.x - camX, b.y, BG_K, b.dir, nt);
      if (!reduced()) { const cx = VW + 80 - mod(t * 90 + camX, VW + 300); lowrider(g, cx, lane + 70, nt); }
      box(g, "#a3a9b1", 0, bot - 44, VW, 5); box(g, lin(g, 0, bot - 39, 0, bot, ["#d3d8de", "#b5bbc3"]), 0, bot - 39, VW, 39);
      const fk = reduced() ? 1 : 1.25, fo = -mod(camX * fk, 48);
      g.strokeStyle = "rgba(0,0,0,.14)"; for (let x = fo; x < VW; x += 48) { g.beginPath(); g.moveTo(x, bot - 39); g.lineTo(x + 10, bot); g.stroke(); }
      for (let x = -mod(camX * fk, 130), i = Math.floor(camX * fk / 130); x < VW + 20; x += 130, i++) { const gx = x + (i % 3) * 14;
        for (let k = 0; k < 5; k++) line(g, "#5a9a4a", 1.6, [gx + k * 3, bot - 38, gx + k * 3 + (k - 2) * 2.2, bot - 47 - (k % 2) * 4]); }
      if (p.road) box(g, nt ? `rgba(8,8,36,${p.road})` : `rgba(70,30,90,${p.road})`, 0, -30, VW, bot + 30);
    }
    // v49.5 Playa Neón background (decorative only, no sound, no hitboxes): cartoon car chases on the far coast road (police cars with flashing
    // light bars after a sports car) and a cartoon rooftop standoff between silhouettes: just bright flashes + sparks, nobody gets hurt
    function bgChase() {
      const y = GS - 52;
      g.setTransform(S, 0, 0, S, 0, 0);
      [[1, 120, 0], [-1, 95, 260]].forEach(([dir, sp, ph]) => {
        const span = VW + 420, lead = mod(t * sp + ph, span) - 210, x0 = dir > 0 ? lead : VW - lead;
        const car = (x, cop) => { const f = dir;   // a tiny car seen from the side, facing the way it drives
          g.save(); g.translate(x, y); g.scale(f, 1);
          if (cop) { box(g, "#f4f6f8", -13, -8, 26, 5, 2); box(g, "#1b1f2a", -13, -4, 26, 3, 1.5); box(g, "#f4f6f8", -7, -12, 13, 5, 2);
            const on = Math.floor(t * 8 + x) % 2; box(g, on ? "#ff2a3a" : "#2a7bff", -3, -14.5, 3, 2.4, 1); box(g, on ? "#2a7bff" : "#ff2a3a", 0.5, -14.5, 3, 2.4, 1);
            ell(g, on ? "rgba(255,42,58,.35)" : "rgba(42,123,255,.35)", 0, -13, 9, 5); }
          else { poly(g, "#ff4a5a", [-14, -3, -12, -8, -2, -11, 6, -11, 13, -7, 14, -3]); poly(g, "#1b2a3a", [-1, -10, 5, -10, 8, -7, 0, -7]); }
          ell(g, "#14161a", -8, -2.5, 2.8, 2.8); ell(g, "#14161a", 8, -2.5, 2.8, 2.8); g.restore(); };
        car(x0, false); car(x0 - dir * 44, true); car(x0 - dir * 82, true);
        for (let k = 0; k < 3; k++) ell(g, "rgba(255,255,255,.35)", x0 - dir * (20 + k * 9 + mod(t * 40, 9)), y - 3, 2.6, 1.6);   // dust behind the getaway car
      });
      g.setTransform(1, 0, 0, 1, 0, 0);   // blit() draws with no transform
    }
    function bgRoofs(rm) {   // silhouettes on the hotel roofs, facing off; a flash + a few sparks now and then (pure decoration)
      const ls = 1.1, per = 2000 * ls, off = mod((level - 1) * 520 + camX * 0.4 * par(), per), base = GS - 26;
      for (const [lx, ly, face, ph] of [[170, -150, 1, 0], [262, -120, -1, 0.7], [600, -168, 1, 0.35], [732, -130, -1, 1.05], [1170, -140, 1, 0.5], [1412, -124, -1, 1.2]]) {
        for (let m = -1; m < 2; m++) {
          const sx = lx * ls - off + m * per; if (sx < -30 || sx > VW + 30) continue;
          g.setTransform(S * ls, 0, 0, S * ls, sx * S, (base + ly * ls) * S); g.scale(face, 1);
          const D = "#24102e"; box(g, D, -3.5, -14, 7, 10, 3); line(g, D, 2.4, [-1.5, -4, -2, 0]); line(g, D, 2.4, [1.5, -4, 2.5, 0]); ell(g, D, 0, -17, 3.2, 3.2);
          box(g, D, -5, -19.6, 10, 1.4, 0.7); box(g, D, -2.8, -23, 5.6, 3.6, 1.2); line(g, D, 2, [1, -11, 7, -12]);   // a fedora, an arm out
          const c8 = rm ? 1 : mod(t + ph * 1.3, 1.6);
          if (c8 < 0.14) { const r = 4 + (0.14 - c8) * 20;
            g.fillStyle = "#fff6c0"; g.beginPath(); for (let k = 0; k < 10; k++) { const a = k * Math.PI / 5, rr2 = k % 2 ? r * 0.4 : r; g.lineTo(9 + Math.cos(a) * rr2, -12 + Math.sin(a) * rr2); } g.closePath(); g.fill();
            ell(g, "rgba(255,170,60,.5)", 9, -12, r * 0.9, r * 0.9); }
          if (c8 < 0.5) for (let k = 0; k < 4; k++) { const u = c8 * 2, a = -0.6 + k * 0.4; ell(g, `rgba(255,220,120,${(1 - u).toFixed(2)})`, 9 + Math.cos(a) * (4 + u * 14), -12 + Math.sin(a) * (4 + u * 14) + u * u * 6, 0.9, 0.9); }
        }
      }
    }
    function drawJuanAt() {
      const h = hero, fx0 = h.x + h.w / 2, air = Math.max(0, -(h.y + h.h)), sh = Math.max(0.35, 1 - air / 220);
      const groundY = (() => { for (const e of ents) if (SOLID.includes(e.t) && fx0 > e.x && fx0 < e.x + e.w && h.y + h.h <= e.y + 1) return e.y; return 0; })();
      ell(g, "rgba(0,0,0,.28)", fx0, groundY, 22 * sh, 5 * sh);
      if (h.inv > 0 && !reduced() && Math.floor(t * 14) % 2) return;
      let pose = "run";
      if (mode === "win") pose = "cheer"; else if (mode === "title" || mode === "clear" || mode === "paused" && h.ground && false) pose = "stand";
      else if (!h.ground) pose = h.vy < 0 ? "up" : "down";
      if (mode === "title" || mode === "clear") pose = "stand";
      const fxOn = !reduced() && mode === "run", sk = skinNow();
      if (fxOn && h.landAt != null) { g.save(); g.translate(h.landX, h.landY); g.scale(JS, JS); groundFx(g, sk, t - h.landAt); g.restore(); }
      g.save(); g.translate(fx0, h.y + h.h); g.scale(JS, JS); juan(g, { outfit: L().outfit, pose, ph: h.frame, t, skin: sk, ja: fxOn && h.jumpAt != null ? t - h.jumpAt : undefined }); g.restore();   // v49.5: 1.5× + the skin + its jump FX
      if (h.shield > 0) { const pr = reduced() ? 0 : Math.sin(t * 6) * 2; g.strokeStyle = "rgba(62,232,235,.75)"; g.lineWidth = 2.2; g.beginPath(); g.ellipse(fx0 + 2, h.y + h.h / 2 - 10, 36 + pr, 62 + pr, 0, 0, Math.PI * 2); g.stroke();
        g.fillStyle = "rgba(62,232,235,.10)"; g.fill(); }   // the 🩴 shield bubble
      if (h.boost > 0 && !reduced()) for (let i = 0; i < 4; i++) line(g, i % 2 ? "#3ee8eb" : "#ffffff", 1.6, [h.x - 8 - i * 6 - mod(t * 120, 10), h.y + 14 + i * 9, h.x - 26 - i * 6 - mod(t * 120, 10), h.y + 14 + i * 9]);
    }
    function drawFx() {
      for (const p of fx) {
        if (p.k === "dust") ell(g, `rgba(232,236,240,${Math.min(0.8, p.life * 1.8).toFixed(2)})`, p.x, p.y, p.r, p.r * 0.8);
        else if (p.k === "drop") ell(g, "rgba(170,225,255,.9)", p.x, p.y, p.r, p.r * 1.3);
        else { const r = p.life > 0.3 ? 3.2 : 1.8; g.fillStyle = p.c; g.beginPath(); g.moveTo(p.x, p.y - r); g.lineTo(p.x + r * 0.3, p.y - r * 0.3); g.lineTo(p.x + r, p.y); g.lineTo(p.x + r * 0.3, p.y + r * 0.3); g.lineTo(p.x, p.y + r); g.lineTo(p.x - r * 0.3, p.y + r * 0.3); g.lineTo(p.x - r, p.y); g.lineTo(p.x - r * 0.3, p.y - r * 0.3); g.fill(); }
      }
    }
    function hud() {   // UI chrome: Fiesta colors only (pink, turquoise, white, silver on near-black)
      g.setTransform(S, 0, 0, S, 0, 0);
      g.fillStyle = "rgba(13,15,26,.94)"; rr(g, 6, 6, VW - 12, 54, 12); g.fill(); g.strokeStyle = "rgba(62,232,235,.4)"; g.lineWidth = 1; rr(g, 6.5, 6.5, VW - 13, 53, 12); g.stroke();
      box(g, "#ff3d8b", 13, 12, 38, 18, 9); say(g, `LV ${level}`, 32, 21.5, 11.5, "#ffffff", { font: UI, weight: 900 });
      const sc = String(score); g.font = `900 16px ${UI}`; const sw = g.measureText(sc).width;
      say(g, sc, VW - 14, 21.5, 16, "#3ee8eb", { font: UI, weight: 900, align: "right" });
      say(g, L().name, 58, 21.5, 13, "#eef1f4", { font: UI, weight: 800, align: "left", max: VW - 14 - sw - 70 });
      const px = Math.min(1, Math.max(0, hero.x / END)), pw = 116;
      box(g, "#3a4058", 13, 41, pw, 6, 3); box(g, "#00b8b0", 13, 41, Math.max(6, pw * px), 6, 3);
      for (const c of CHECKS.slice(1)) box(g, hero.x >= c ? "#3ee8eb" : "#ff3d8b", 13 + pw * c / END - 1, 38, 2.4, 12, 1);
      ell(g, "#ffffff", 13 + pw * px, 44, 4.5, 4.5);
      heart(g, 143, 44.5, 6.5, "#ff3d8b");
      const hp = hero.health / HP, hw = 92; box(g, "#3a4058", 153, 40, hw, 9, 4.5);
      if (hp > 0) box(g, lin(g, 153, 0, 153 + hw, 0, ["#ff3d8b", "#ff8fbf"]), 153, 40, Math.max(9, hw * hp), 9, 4.5);
      if (hp < 0.3 && !reduced() && Math.floor(t * 4) % 2) { g.strokeStyle = "#ffffff"; g.lineWidth = 1.2; rr(g, 153, 40, hw, 9, 4.5); g.stroke(); }
      const on = hero.boost > 0, cx = 262;   // ☕ slot
      box(g, on ? "#3ee8eb" : "#5a6078", cx - 6, 38, 11, 11, 2.5); g.strokeStyle = on ? "#3ee8eb" : "#5a6078"; g.lineWidth = 2; g.beginPath(); g.arc(cx + 5.5, 43.5, 3, -1.4, 1.4); g.stroke();
      if (on && !reduced()) line(g, "#ffffff", 1.2, [cx - 2, 35, cx - 1, 32, cx - 2, 29]);
      if (on) box(g, "#3ee8eb", cx - 7, 52.5, 14 * hero.boost / 5, 2, 1);
      const sOn = hero.shield > 0, fx2 = 282;   // 🩴 shield slot
      g.save(); g.translate(fx2, 43.5); g.rotate(-0.4); ell(g, sOn ? "#3ee8eb" : "#5a6078", 0, 0, 3.6, 6.2); line(g, sOn ? "#ff3d8b" : "#3a4058", 1.3, [-2.4, 1, 0, -3, 2.4, 1]); g.restore();
      say(g, `HI ${Math.max(st.best, score)}`, VW - 14, 45, 10.5, "#9aa3b5", { font: UI, weight: 800, align: "right" });
      if (msgT > 0) { g.font = `800 13px ${UI}`; const w = g.measureText(msg).width + 26; box(g, "rgba(13,15,26,.85)", (VW - w) / 2, 68, w, 26, 13); say(g, msg, VW / 2, 81.5, 13, "#3ee8eb", { font: UI, weight: 800 }); }
    }
    // v49.9: the safety net. If a frame throws, or ~2 s after the game starts the canvas has no size, never drew, or the full-screen
    // game is wider than the screen, show a friendly "Tap to reload" instead of a blank screen (100vw × 100vh: on screen even then).
    let drawnN = 0, hcT = 0, brokeEl = null;
    function broken(err) {
      if (brokeEl || !el.isConnected) return; if (err) console.error("Juan:", err);
      brokeEl = document.createElement("button"); brokeEl.type = "button"; brokeEl.className = "game-broken";
      brokeEl.innerHTML = `<span><span aria-hidden="true">😬</span> The Juan That Got Away didn't load right.</span><b>🔄 Tap to reload</b>`;
      brokeEl.onclick = () => location.reload(); document.body.appendChild(brokeEl); brokeEl.focus({ preventScroll: true });
    }
    function healthCheck() {
      clearTimeout(hcT); hcT = setTimeout(() => {
        if (!el.isConnected || document.hidden || (!fs.on && !el.closest(".view.active"))) return;
        const r = cv.getBoundingClientRect(), wide = fs.on && (el.getBoundingClientRect().width > innerWidth + 4 || document.documentElement.scrollWidth > innerWidth + 4);
        if (!cv.width || !cv.height || r.width < 40 || r.height < 40 || !drawnN || wide) broken(wide ? new Error("the page is wider than the screen") : null);
      }, 2000);
    }
    function draw() { drawnN++;
      if (!hero) return;
      caches();
      const sx = shake > 0 && !reduced() ? (Math.random() - 0.5) * 6 : 0;
      g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(cache.sky, 0, 0);
      if (cache.cloud) { const cl = cache.cloud, big = L().time === "noon" ? 1.35 : 1, span = VW + 260;
        [[20, 0.2], [190, 0.34], [330, 0.13], [470, 0.27]].forEach(([x0, fy], i) => { const x = mod(x0 - camX * 0.03 * par() - t * 5 * par(), span) - 200, s = (i % 2 ? 0.75 : 1) * big;
          g.drawImage(cl.cv, Math.round(x * S), Math.round(fy * GS * S), cl.cv.width * S / cl.k * s, cl.cv.height * S / cl.k * s); }); }
      blit(cache.far, 0.06, GS - 34, 60 + (level - 1) * 45);
      blit(cache.mid, 0.4, GS - 26, (level - 1) * 520);
      if (L().beach) { bgRoofs(reduced()); if (!reduced()) bgChase(); }   // v49.5 Playa Neón: background only, no effect on the game
      g.setTransform(S, 0, 0, S, sx * S, GS * S); road();
      const dx = destX() - camX; if (dx < VW + 10) { g.setTransform(1, 0, 0, 1, Math.round((dx + sx) * S), 0); g.drawImage(cache.dest, 0, Math.round((GS - 12 - 360) * S));
        if (L().d === 1) { const ds = Math.min(1, (GS - 12 - 70) / DEST_H[level - 1]); g.setTransform(S * ds, 0, 0, S * ds, Math.round((dx + sx) * S) + (VW * (1 - ds) / 2) * S, (GS - 12) * S); djRig(g, t, reduced()); } }   // v49.15: the Hon Dipo DJ, live (it moves), same spot + scale as the store
      g.setTransform(S, 0, 0, S, (sx - camX) * S, GS * S);
      const rm = reduced();
      if (L().beach && camX < ARCH_X + 260) diceArch(g, ARCH_X, t, rm);   // v49.5: the PLAYA NEÓN arch at the start of level 7
      for (const pass of [0, 1]) for (const e of ents) if (!e.gone && (e.t === "agent" || e.t === "chaser") === !!pass && e.x < camX + VW + 40 && e.x + e.w > camX - 90) drawEnt(g, e, t, rm);   // the agents on top
      drawJuanAt(); drawFx();
      if (mode === "win") { g.setTransform(S, 0, 0, S, 0, 0); for (const p of parts) { g.save(); g.translate(p.x, p.y); g.rotate(p.r); box(g, p.c, -3, -2, 6, 4); g.restore(); } }
      hud();
      if (mode === "oops") say(g, oopsMsg, VW / 2, VH * 0.34, 42, "#ff3d8b", { font: UI, weight: 900, stroke: "#111111", sw: 7, max: VW - 30, fit: true });   // v47: fit = the longest line ("¡Ay, vengo mamá!") shrinks a little instead of getting squished
      else if (fueraT > 0) { const pop = reduced() ? 1 : 1 + Math.max(0, fueraT - 0.9) * 2.2;   // v46: Juan got away
        g.globalAlpha = Math.min(1, fueraT * 3); say(g, FUERA, VW / 2, VH * 0.3, 46 * pop, "#3ee8eb", { font: UI, weight: 900, stroke: "#111111", sw: 7, max: VW - 30 }); g.globalAlpha = 1; }
    }
    // v49.8: the "tiny game" fix. fit() used to measure once, on a window resize, with getBoundingClientRect: on a phone that
    // event often fires mid-rotation / mid URL-bar or full-screen change (and the rect shrinks with a CSS transform), and a
    // snapshot of a short, wide box got pillar-boxed (landscape) into a ~230px-wide canvas that stayed that small. Now it
    // measures the layout box (offsetWidth/Height), and re-fits whenever that box really changes: a ResizeObserver, the visual
    // viewport, rotation, coming back to the tab, plus a check every ~0.5 s while the game runs, so it always recovers.
    let fitKey = "", fitN = 0, refitT = 0;
    const sizeKey = () => wrap.offsetWidth + "x" + wrap.offsetHeight + (fs.on ? "f" : "") + (root.devicePixelRatio || 1);
    const refit = () => { requestAnimationFrame(() => fit()); clearTimeout(refitT); refitT = setTimeout(() => fit(), 350); };
    function fit() {
      let w, h;
      const r = { width: wrap.offsetWidth, height: wrap.offsetHeight };   // the layout box (a CSS transform doesn't shrink it)
      if (fs.on) { w = r.width; h = r.height; if (w < 40 || h < 40) return;
        if (h / w < 520 / VW) w = h * VW / 520;   // a wide screen (landscape, desktop): pillar-box
        if (h / w > 900 / VW) h = w * 900 / VW; }
      else { w = Math.min(r.width || VW, 440); h = w * 580 / VW; }
      w = Math.max(200, Math.floor(w)); h = Math.floor(h); cssW = w;
      cv.style.width = w + "px"; cv.style.height = h + "px";
      let d = Math.min(root.devicePixelRatio || 1, dprCap); while (d > 1 && w * h * d * d > 3.4e6) d -= 0.25;
      const bw = Math.round(w * d), bh = Math.round(h * d);
      if (bw !== cv.width || bh !== cv.height) { cv.width = bw; cv.height = bh; }
      dpr = d; S = bw / VW; VH = bh / S; GS = VH - ROADH; fitKey = sizeKey();
      if (!raf && hero) draw();
    }
    function title() {
      level = 1; cache = {}; spawn(0); hero.x = 140; camX = cam(hero.x); mode = "title"; fit();
      const cont = st.levelMax > 1 ? `<button type="button" class="lot-btn" data-act="cont">▶ Keep going: level ${num(st.levelMax)}</button>` : "";
      $("#juan-note").textContent = "It's Friday! Get Juan through his Friday shift to cold beers at Noche Caliente.";
      overlay(`<p class="juan-big">The Juan That Got Away</p><p class="juan-story">It's Friday! One last shift, then cold ones.</p>
        ${howList("juan-how-ov")}
        <p class="juan-btns${cont ? " has-cont" : ""}"><button type="button" class="lot-btn lot-main" data-act="start">▶ Start at level 1</button>${skinBtn()}${cont}${skinHint()}</p>`, "title");   // v49.5: a compact skin chip beside Start; the best score lives in the HUD (HI) and under the game
    }
    function loop() {
      cancelAnimationFrame(raf); last = performance.now();
      const step = (now) => { const dt = Math.min(0.05, (now - last) / 1000); last = now; if (++fitN % 30 === 0 && sizeKey() !== fitKey) fit();
        try { update(dt); draw(); } catch (err) { raf = null; broken(err); return; }   // v49.9: a crash shows "Tap to reload", not a frozen / blank screen
        if (mode === "run") { perf.n++; perf.sum += dt; if (perf.n >= 90) { const avg = perf.sum / perf.n; perf = { n: 0, sum: 0 };   // a slow phone: draw at a lower resolution
          if (avg > 0.024 && dprCap > 1.5) { dprCap = dprCap > 2 ? 2 : 1.5; fit(); } } }
        if (mode === "run" || mode === "oops" || (mode === "win" && parts.length) || fx.length) raf = requestAnimationFrame(step); else raf = null; };
      raf = requestAnimationFrame(step);
    }
    function pause() {
      if ((mode === "run" || mode === "oops") && !paused) {
        if (mode === "oops") spawn(ck);
        paused = true; mode = "paused"; cancelAnimationFrame(raf); raf = null; draw();
        overlay(`<p class="juan-big">Paused</p><p class="juan-btns"><button type="button" class="lot-btn lot-main" data-act="resume">▶ Resume</button>${OVER}${skinBtn()}${skinHint()}</p>`, "soft");   // v49.8: 👕 Skins here too ctrl();
      }
    }
    function resume() { if (paused) { paused = false; mode = "run"; overlay(null); fs.enter(); fit(); loop(); ctrl(); } }
    function stats() { $("#juan-stats").innerHTML = `⭐ Best score <b>${num(st.best)}</b> · 🤠 Made it to Noche Caliente <b>${num(st.wins)}</b>× · Furthest level <b>${num(st.levelMax)}</b>`; }
    function ctrl() {
      const p = $("#juan-pause");
      p.innerHTML = paused ? '<span aria-hidden="true">▶</span><span class="juan-lbl"> Resume</span>' : '<span aria-hidden="true">⏸</span><span class="juan-lbl"> Pause</span>';
      p.setAttribute("aria-label", paused ? "Resume" : "Pause");
      const s = $("#juan-sound");
      s.innerHTML = `<span aria-hidden="true">${st.muted ? "🔇" : "🔊"}</span><span class="juan-lbl"> Sound</span>`; s.setAttribute("aria-label", st.muted ? "Sound is off" : "Sound is on"); s.setAttribute("aria-pressed", st.muted ? "false" : "true");
    }
    // ---- v49.5 🏆 Top 10 (server board, GET/POST /api/juan/scores). The last board is kept on the phone, so it still shows
    // offline; a name saved offline waits on the phone and goes up when the phone is back online. A run ends when Juan makes
    // it to Noche Caliente, or when you leave the game (✕ / Escape) with points; if the score makes the Top 10 a sheet asks
    // for a name (12 max), Save posts it, then the board refreshes with the new row highlighted.
    const HS_CACHE = "chisme-juan-board", HS_PENDING = "chisme-juan-pending", HS_NAME = "chisme-juan-name";
    const lsGet = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k) || "null"); return v == null ? d : v; } catch (e) { return d; } };
    const lsSet = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
    const escH = (x) => String(x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const fmt = (n) => Number(n || 0).toLocaleString("en-US");
    let board = lsGet(HS_CACHE, null), boardLive = false, hiId = null, run = { sent: false, offered: 0 }, hsDlg = null;
    const pendingRows = () => lsGet(HS_PENDING, []).map((p, i) => ({ id: "pending-" + i, name: p.name, score: p.score, level: p.level, t: p.t, pending: true }));
    const merged = () => [...((board && board.scores) || []), ...pendingRows()].sort((a, b) => b.score - a.score || a.t - b.t).slice(0, 10);
    const listHTML = (rows, hi) => rows.length ? rows.map((r, i) => `<li class="juan-hs-row${r.id === hi ? " me" : ""}${r.pending ? " pending" : ""}"><span class="rk rk${i + 1}">${i + 1}</span><span class="nm">${escH(r.name)}${r.pending ? ' <small>📴 waiting</small>' : ""}</span><span class="sc">${fmt(r.score)}</span></li>`).join("")
      : `<li class="juan-hs-empty">Be the first on the board!</li>`;
    function drawBoard() {
      const list = $("#juan-hs-list"), note = $("#juan-hs-note"); if (!list) return;
      const rows = merged();
      if (!board && !rows.length && !navigator.onLine) list.innerHTML = `<li class="juan-hs-empty">📴 You're offline. The board shows up when you're back online.</li>`;
      else list.innerHTML = listHTML(rows, hiId);
      const off = !boardLive && board;
      note.hidden = !off; note.textContent = off ? "📴 Offline: the last board this phone saw." : "";
    }
    async function loadBoard() {
      try { const r = await fetch("/api/juan/scores", { cache: "no-store" }); const d = await r.json(); if (!r.ok || !d.ok) throw new Error("board");
        board = { scores: d.scores || [], at: Date.now() }; boardLive = true; lsSet(HS_CACHE, board); }
      catch (e) { boardLive = false; }
      drawBoard(); return merged();
    }
    async function postScore(e) {
      const r = await fetch("/api/juan/scores", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(e) });
      const d = await r.json().catch(() => ({})); return { status: r.status, ...d };
    }
    async function flushPending() {
      const left = []; let last = null;
      for (const p of lsGet(HS_PENDING, [])) { try { const d = await postScore(p); if (d.ok) { last = d.id; if (d.rank && d.rank <= 10) unlockSkins(d); } else if (d.status === 429) left.push(p); } catch (e) { left.push(p); } }   // 400 = a bad score: dropped
      lsSet(HS_PENDING, left); if (last) hiId = last; return last;
    }
    // v49.12 (legal audit M5/M6): the same name filter as the server (static/name_blocklist.json, namefilter.py), checked
    // before posting so a blocked nickname gets a friendly "pick another one" instead of a failed save
    let blockList = null;
    const loadBlockList = () => blockList || (blockList = fetch("/static/name_blocklist.json").then((r) => r.json()).catch(() => ({ contains: [], words: [] })));
    const LEET = { "0": "o", "1": "i", "!": "i", "|": "i", "3": "e", "4": "a", "@": "a", "5": "s", "$": "s", "7": "t", "8": "b", "9": "g" };
    const squeeze = (x) => x.replace(/(.)\1+/g, "$1");
    function nameBlocked(name, bl) {
      if (!bl) return false;
      const b = String(name || "").normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f]/g, "").replace(/[0-9!|@$]/g, (c) => LEET[c] || c);
      const joined = b.replace(/[^a-z]/g, ""), W = new Set(bl.words || []);
      if ((bl.contains || []).some((w) => joined.includes(w) || squeeze(joined).includes(w))) return true;
      return b.split(/[^a-z]+/).filter(Boolean).some((w) => W.has(w) || W.has(squeeze(w))) || W.has(joined) || W.has(squeeze(joined));
    }
    const NAME_NO = "Pick another nickname: that one can't go on the public board.";
    const makes = (sc, rows) => sc > 0 && (rows.length < 10 || sc > rows[rows.length - 1].score);
    let offering = false;
    async function offer(sc, lvl) {
      if (offering || hsDlg || run.sent || sc <= run.offered || sc <= 0) return false;
      offering = true; let rows;
      try { rows = navigator.onLine ? await loadBoard() : merged(); } finally { offering = false; }
      if (!makes(sc, rows) || hsDlg || !el.isConnected) return false;
      run.offered = sc; openSheet(sc, Math.max(1, Math.min(LEVELS.length, lvl)), rows.filter((r) => r.score >= sc).length + 1);
      return true;
    }
    function openSheet(sc, lvl, rank) {
      if (hsDlg) hsDlg.remove();
      const d = document.createElement("dialog"); d.className = "juan-hs-sheet"; d.setAttribute("aria-labelledby", "juan-hs-big");
      d.innerHTML = `<form method="dialog" class="juan-hs-card" novalidate>
        <p class="juan-hs-big" id="juan-hs-big"><span aria-hidden="true">🏆</span> New high score!</p>
        <p class="juan-hs-sub">Put your nickname on the board</p>
        <p class="juan-hs-score"><b>${fmt(sc)}</b> points · <span class="juan-hs-rank">#${num(rank)}</span></p>
        <label class="juan-hs-lbl" for="juan-hs-name">Nickname (public) <small>(12 max)</small></label>
        <p class="juan-hs-fine" id="juan-hs-fine">Everyone sees it on the board. Don't use your real name.</p>
        <input id="juan-hs-name" class="juan-hs-in" type="text" maxlength="12" autocomplete="nickname" autocapitalize="words" enterkeyhint="done" spellcheck="false" aria-describedby="juan-hs-fine" placeholder="Nickname" value="${escH(lsGet(HS_NAME, ""))}">
        <button type="submit" class="juan-hs-save" value="save">Save</button>
        <button type="button" class="juan-hs-skip">Not now</button>
        <p class="juan-hs-msg" role="status"></p></form>`;
      document.body.appendChild(d); hsDlg = d;
      const inp = d.querySelector("input"), btn = d.querySelector(".juan-hs-save"), msgEl = d.querySelector(".juan-hs-msg");
      const close = () => { if (d.open) d.close(); d.remove(); if (hsDlg === d) hsDlg = null; };
      d.querySelector(".juan-hs-skip").onclick = close;
      d.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
      d.querySelector("form").addEventListener("submit", async (e) => {
        e.preventDefault(); if (btn.disabled) return;
        const name = inp.value.replace(/\s+/g, " ").trim().slice(0, 12) || "Juan";
        if (nameBlocked(name, await loadBlockList())) { msgEl.textContent = NAME_NO; inp.focus(); return; }
        lsSet(HS_NAME, name === "Juan" ? lsGet(HS_NAME, "") : name);
        const entry = { name, score: sc, level: lvl, t: Math.floor(Date.now() / 1000) };
        btn.disabled = true; btn.textContent = "Saving…"; msgEl.textContent = "";
        let res = null; try { res = await postScore(entry); } catch (err) { res = null; }
        if (res && res.ok) { run.sent = true; hiId = res.id; if (res.rank && res.rank <= 10) unlockSkins(res); await loadBoard(); done(d, `You're <b>#${res.rank || "?"}</b> on the board!`); return; }
        if (!res) {   // offline / no network: keep it on the phone, it goes up later
          const q = lsGet(HS_PENDING, []); q.push(entry); lsSet(HS_PENDING, q.slice(-5)); run.sent = true; hiId = "pending-" + (Math.min(q.length, 5) - 1); drawBoard();
          done(d, "📴 Saved on this phone. It goes on the board when you're back online."); return; }
        btn.disabled = false; btn.textContent = "Save";
        msgEl.textContent = res.status === 429 ? "Too many tries. Wait a minute and tap Save again." : res.error === "name" ? NAME_NO : "That score can't go on the board.";
      });
      loadBlockList();
      d.showModal(); setTimeout(() => { try { inp.focus(); inp.select(); } catch (e) {} }, 60);
    }
    function done(d, line) {
      const card = d.querySelector(".juan-hs-card");
      card.innerHTML = `<p class="juan-hs-big" id="juan-hs-big"><span aria-hidden="true">🎉</span> You made it!</p><p class="juan-hs-sub">${line}</p>
        <ol class="juan-hs-list in-sheet">${listHTML(merged(), hiId)}</ol><button type="submit" class="juan-hs-save" value="done">Done</button>`;
      drawBoard();
      card.querySelector(".juan-hs-save").focus();
      card.onsubmit = (e) => { e.preventDefault(); if (d.open) d.close(); d.remove(); if (hsDlg === d) hsDlg = null; const me = $("#juan-hs .me"); if (me && me.scrollIntoView) me.scrollIntoView({ block: "center", behavior: reduced() ? "auto" : "smooth" }); };
    }
    const onOnline = () => { flushPending().then(() => loadBoard()); };
    root.addEventListener("online", onOnline);
    drawBoard(); (lsGet(HS_PENDING, []).length && navigator.onLine ? flushPending() : Promise.resolve()).then(() => loadBoard());

    // ---- v49.5 skins: Classic Juan is the default; the others unlock (on this phone, for good) once a score of yours posts into
    // the Top 10. The picker is a sheet from the title screen; locked skins show 🔒 and "Make the Top 10 to unlock".
    const SK_UNLOCK = "chisme-juan-top10";
    // v49.8: the owner (signed in to /stats, the same sign-in as the high score admin) gets every skin on that phone to promote
    // the game. The page can't see the real sign-in (an HttpOnly cookie for /stats), so: only when the harmless chisme_admin=1
    // marker is there, ask the server (GET /stats/juan/scores answers 200 only to the signed-in owner). Nothing is written to
    // the Top 10 unlock, so signing out puts the phone back as it was. Everyone else: no marker, no request, nothing changes.
    let owner = false;
    if (/(?:^|;\s*)chisme_admin=1(?:;|$)/.test(document.cookie)) fetch("/stats/juan/scores", { credentials: "same-origin", cache: "no-store" })
      .then((r) => { owner = r.ok; if (owner && mode === "title") title(); }).catch(() => {});
    const skinsOpen = () => owner || !!lsGet(SK_UNLOCK, null);
    function unlockSkins(d) { if (!skinsOpen()) lsSet(SK_UNLOCK, { at: Date.now(), rank: d.rank, score: d.entry && d.entry.score }); }
    const skinName = (id) => (JSKINS.find((k) => k[0] === id) || JSKINS[0])[1];
    function skinNow() { const k = st.skin || "classic"; return k !== "classic" && (!skinsOpen() || !JSKINS.some((x) => x[0] === k)) ? "classic" : k; }
    let skDlg = null;
    function openSkins() {
      if (skDlg) skDlg.remove();
      const open = skinsOpen(), cur = skinNow(), d = document.createElement("dialog"); d.className = "juan-skins"; d.setAttribute("aria-labelledby", "juan-sk-t");
      d.innerHTML = `<form method="dialog" class="juan-sk-card"><p class="juan-sk-t" id="juan-sk-t">👕 Pick your Juan</p>
        <p class="juan-sk-sub">${owner && !lsGet(SK_UNLOCK, null) ? "👑 Owner: every skin is unlocked on this phone." : open ? "🏆 You made the Top 10: every skin is yours." : "🔒 Make the Top 10 to unlock the skins."}</p>
        <div class="juan-sk-grid">${JSKINS.map(([id, name]) => { const lock = id !== "classic" && !open;
          return `<button type="button" class="juan-sk${lock ? " locked" : ""}${id === cur ? " on" : ""}" data-skin="${id}" aria-pressed="${id === cur}" aria-label="${name}${lock ? ", locked: make the Top 10 to unlock" : id === cur ? ", wearing it" : ""}">
            <canvas class="juan-sk-cv" aria-hidden="true"></canvas><span class="juan-sk-tx"><span class="juan-sk-n">${escH(name).replace("Presidente", "Presi\u00addente").replace("Lowrider", "Low\u00adrider")}</span>${lock ? '<span class="juan-sk-why">Make the Top 10 to unlock</span>' : ""}</span>${lock ? '<span class="juan-sk-lock" aria-hidden="true">🔒</span>' : ""}</button>`; }).join("")}</div>
        <button type="submit" class="juan-sk-done">Done</button></form>`;
      document.body.appendChild(d); skDlg = d;
      d.querySelectorAll(".juan-sk").forEach((b) => skinPreview(b.querySelector("canvas"), b.dataset.skin));
      const close = () => { if (d.open) d.close(); d.remove(); if (skDlg === d) skDlg = null; };
      d.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
      d.querySelector("form").addEventListener("submit", (e) => { e.preventDefault(); close(); });
      d.querySelector(".juan-sk-grid").addEventListener("click", (e) => {
        const b = e.target.closest(".juan-sk"); if (!b) return;
        if (b.classList.contains("locked")) { const sub = d.querySelector(".juan-sk-sub"); sub.textContent = "🔒 Make the Top 10 to unlock " + skinName(b.dataset.skin) + "."; sub.classList.remove("nudge"); void sub.offsetWidth; sub.classList.add("nudge"); return; }
        st.skin = b.dataset.skin; save(st);
        d.querySelectorAll(".juan-sk").forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-pressed", String(on)); });
        skinLabel(); if (!raf) draw();
      });
      d.showModal(); const onB = d.querySelector(".juan-sk.on"); if (onB) onB.focus({ preventScroll: true });   // not the first card
    }
    function skinAria() { return "Skins: wearing " + skinName(skinNow()) + (skinsOpen() ? "" : ". Make the Top 10 to unlock more"); }
    // v49.8: the 👕 Skins button on the title, pause and level-clear / win screens (locked: a 🔒 and the Top 10 hint)
    function skinBtn() { return `<button type="button" class="lot-btn juan-sk-btn" data-act="skins" aria-haspopup="dialog" aria-label="${skinAria()}">👕<span class="juan-sk-word"> Skins</span>${skinsOpen() ? "" : ' <span aria-hidden="true">🔒</span>'}</button>`; }
    // v49.8: 🔄 Start over (paused, level clear): level 1 with a fresh score. Skins, the best score (HI) and the Top 10 stay; a
    // score that makes the board gets its "New high score!" sheet first (the game waits, paused, until it's closed)
    const OVER = '<button type="button" class="lot-btn juan-over" data-act="over">🔄 Start over</button>';
    let overBusy = false;
    async function startOver() {
      if (overBusy) return; overBusy = true;
      try { const sc = score, lv = level;
        if (sc > 0 && await offer(sc, lv)) await new Promise((r) => { const k = setInterval(() => { if (!hsDlg) { clearInterval(k); r(); } }, 150); });
        ckScore = 0; startLevel(1); } finally { overBusy = false; }
    }
    function skinHint() { return skinsOpen() ? "" : '<span class="juan-sk-hint" aria-hidden="true">🔒 Make the Top 10 to unlock</span>'; }
    function skinLabel() { const b = $("#juan-ov [data-act=skins]"); if (b) b.setAttribute("aria-label", skinAria()); }

    // ---- input: tap / click the game, the Jump button, Space / ↑ / W
    cv.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); });
    cv.addEventListener("pointerup", release);
    const jb = $("#juan-jump");
    jb.addEventListener("pointerdown", (e) => { e.preventDefault(); jump(); }); jb.addEventListener("pointerup", release);
    jb.addEventListener("click", (e) => { if (e.detail === 0) jump(); });   // keyboard activation
    // v47: a named handler, removed in destroy(): #game-stage is shared, and Juan now mounts first (then maybe Lotería, then Juan
    // again), so a leftover handler from the old Juan would also "start" and put a 2nd full-screen bar on the stage
    const onAct = (e) => { const b = e.target.closest("[data-act]"); if (!b) return; const a = b.dataset.act; audio();
      if (a === "start" || a === "cont" || a === "again") played();
      if (a === "start") startLevel(1); else if (a === "cont") { ckScore = 0; startLevel(st.levelMax); } else if (a === "next") startLevel(level + 1, true); else if (a === "again") startLevel(1); else if (a === "resume") resume(); else if (a === "skins") openSkins(); else if (a === "over") startOver(); };
    el.addEventListener("click", onAct);
    $("#juan-pause").onclick = () => (paused ? resume() : pause());
    $("#juan-restart").onclick = () => { paused = false; ckScore = 0; startLevel(level); ctrl(); };
    $("#juan-sound").onclick = () => { st.muted = !st.muted; save(st); ctrl(); if (!st.muted) SFX.coin(); };
    const onKey = (e) => {
      if (!el.isConnected || !el.closest(".view.active") || document.querySelector("dialog[open]") || e.target.closest && e.target.closest("input, textarea, select, dialog")) return;   // only while Juegos is showing
      if (e.code === "Space" || e.key === "ArrowUp" || e.key === "w" || e.key === "W") { if (e.target.closest && e.target.closest("button") && e.code === "Space" && e.target !== jb) return; e.preventDefault(); if (!e.repeat) jump(); }
      else if (e.key === "p" || e.key === "P") paused ? resume() : pause();
    };
    const onKeyUp = (e) => { if (e.code === "Space" || e.key === "ArrowUp") release(); };
    const onWin = () => refit();
    const onVis = () => { if (!document.hidden) refit(); };
    const ro = root.ResizeObserver ? new ResizeObserver(() => { if (sizeKey() !== fitKey) fit(); }) : null; if (ro) ro.observe(wrap);
    const vv = root.visualViewport; if (vv) vv.addEventListener("resize", onWin);
    root.addEventListener("orientationchange", onWin); root.addEventListener("pageshow", onWin); document.addEventListener("visibilitychange", onVis);
    // v48: Android drops a canvas's pixels while the app is in the background (the GPU process is reclaimed; Chrome
    // restores the canvas blank and fires "contextrestored"). A paused or idle game never redrew it, so the app came
    // back to an empty dark screen. Redraw whenever the canvas comes back or the page is shown again.
    const repaint = () => { if (!el.isConnected) return; cache = {}; fit(); if (!raf) draw(); };
    const onShow = () => { if (document.visibilityState === "visible") repaint(); };
    cv.addEventListener("contextrestored", repaint);
    document.addEventListener("visibilitychange", onShow); root.addEventListener("pageshow", repaint);
    document.addEventListener("keydown", onKey); document.addEventListener("keyup", onKeyUp); root.addEventListener("resize", onWin);
    stats(); ctrl(); title(); healthCheck();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { cache = {}; if (!raf) draw(); }).catch(() => {});
    return {
      pause, resume, jump,
      fs, exitFullscreen: (quiet) => fs.exit(quiet),
      destroy() { fs.exit(true); cancelAnimationFrame(raf); clearTimeout(hcT); if (brokeEl) brokeEl.remove(); document.removeEventListener("keydown", onKey); document.removeEventListener("keyup", onKeyUp); root.removeEventListener("resize", onWin); if (ro) ro.disconnect(); if (vv) vv.removeEventListener("resize", onWin); root.removeEventListener("orientationchange", onWin); root.removeEventListener("pageshow", onWin); document.removeEventListener("visibilitychange", onVis); clearTimeout(refitT); el.removeEventListener("click", onAct);
        document.removeEventListener("visibilitychange", onShow); root.removeEventListener("pageshow", repaint); root.removeEventListener("online", onOnline); if (hsDlg) hsDlg.remove(); if (skDlg) skDlg.remove(); cache = {}; },
      skins: { open: openSkins, get now() { return skinNow(); }, get unlocked() { return skinsOpen(); }, get owner() { return owner; }, list: JSKINS.map((k) => k[0]) },   // v49.5 (tests)
      hs: { loadBoard, offer, flushPending, get rows() { return merged(); }, get live() { return boardLive; }, get hi() { return hiId; }, get run() { return { ...run }; } },   // v49.5 (tests)
      repaint,
      get state() { return { oopsMsg, msg, mode, level, name: L().name, outfit: L().outfit, x: hero.x, y: hero.y, hw: hero.w, hh: hero.h, skin: skinNow(), ja: hero.jumpAt != null ? t - hero.jumpAt : null, la: hero.landAt != null ? t - hero.landAt : null, view: { S, GS, VH, dpr }, ground: hero.ground, score, ck, best: st.best, muted: st.muted, boost: hero.boost, health: hero.health, beers: beersGot, shield: hero.shield, fuera: fueraT > 0, fueras, caught: caughtN, caughtBy,
        chase: ents.some((e) => e.t === "chaser" && e.st === "chase"),
        levelMax: st.levelMax, parallax: !reduced(), overlay: ov.textContent.trim(), fullscreen: fs.on, W: VW, H: VH, dpr, cssW, backing: [cv.width, cv.height], fx: fx.length, fxMade }; },
      // test hooks: jump to a spot in a level (as if you'd run there), set the health bar
      warp(n, x) { if (n !== level || mode === "title" || mode === "win" || mode === "clear") startLevel(n, true); if (paused) resume(); hero.x = x; hero.y = -HERO_H; hero.vy = 0; camX = cam(x);
        for (const e of ents) if (e.t === "flag" && e.x <= x) { e.done = true; ck = CHECKS.indexOf(e.x); }
        for (const e of ents) if (HAZARDS.includes(e.t) && e.x > x) { e.hit = false; e.down = false; }   // v46: the road ahead as new (an agent may have knocked a cone over)
        ents = ents.filter((e) => !(HAZARDS.includes(e.t) || SOLID.includes(e.t)) || e.x > x + 90 || e.x + e.w < x - 60);
        ents = ents.filter((e) => !ICE.includes(e.t) || e.t === "suv" && e.x + e.w < x - 60 || e.x > x + 320); },   // v46: no agent right on top of him either
      air(y) { hero.y = y - HERO_H; hero.vy = 0; hero.ground = false; hero.jumps = 1; },   // test hooks: put Juan in the air…
      clearAhead(d) { ents = ents.filter((e) => !(HAZARDS.includes(e.t) || SOLID.includes(e.t) || e.t === "agent") || e.x > hero.x + d || e.x + e.w < hero.x - 40); },   // …clear the road ahead…
      stumble(s) { hero.stumble = s; },
      bgIce: () => ({ n: bgN, next: bgNext, cars: bgIce.map((b) => ({ kind: b.kind, x: b.x, sx: b.x - camX, vx: b.vx, dir: b.dir, y: b.y })) }),   // v46: the far-lane ICE SUVs (scenery)…
      bgSpawn(kind, sx) { bgSpawn(kind); if (sx != null) bgIce[bgIce.length - 1].x = camX + sx; },   // …make one now (at a screen x)   // …or slow him down (so a chaser catches up)
      setHealth(v) { hero.health = Math.max(0, Math.min(HP, v)); },
      caughtNext(line) { forceCaught = line; },   // v47 test hook: the next catch says this line (for a screenshot)
      captionBox() { g.font = `900 42px ${UI}`; const w = g.measureText(oopsMsg).width + 7, sz = w > VW - 30 ? Math.max(12, Math.floor(42 * (VW - 30) / w)) : 42; g.font = `900 ${sz}px ${UI}`; return { size: sz, w: g.measureText(oopsMsg).width + 7, max: VW - 30, VW, cssW }; },
      ents: () => ents.filter((e) => !e.gone).map((e) => ({ t: e.t, x: e.x, y: e.y, w: e.w, st: e.hit ? "hit" : e.on ? "on" : ICE.includes(e.t) ? e.st || (e.out ? "out" : "") : "" })),
    };
  }

  const game = { id: "juan", name: "The Juan That Got Away", emoji: "👢", blurb: "It's Friday! Get Juan through his Friday shift and on to beers with the crew at Noche Caliente.", mount };
  const api = { GRAV, JUMP, JUMP2, fall, trim, DIM, drawAgent: iceAgent, AG_TALL, AWAY, KEY, LEVELS, END, CHECKS, VW, HP, HAZ, ICE, CAUGHT, pickCaught, FUERA, buildLevel, load, save, reset, game, drawJuan: juan, groundFx, JS, SKINS: JSKINS };   // v49.5: drawJuan/groundFx for the skin tests
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.ChismeJuan = api; if (root.ChismeJuegos) root.ChismeJuegos.GAMES.unshift(game); }   // v47: first in the list = the game Juegos opens on
})(typeof window !== "undefined" ? window : this);
