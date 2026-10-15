/* Chisme · Puro Pinche Lowrider: the "San Antonio" stage (v49.16). Loaded the first time it's picked on the title screen, then it
   registers itself on window.ChismeLowrider.stages.sa. Everything here is data + cartoon canvas drawing in the game's own style:
   LANDMARKS (silhouettes with a name tag as each one rolls by; add more by pushing to the list), parody stores (Hon Dipo from the Juan
   game, Gualmart, H-E-Bae), made-up taquerías, TRAFFIC to hop (each vehicle has a driver, a speed range, a wobble, a horn and its own
   comic lines), PICKS (gas cans fill the tank, a glass-bottle refresco pays Feria, tacos pay points + combo), the rare Trail Ride
   (10 horses, the car always stops, every hop is a salute: +YEEHAW), and Chisme's own App Store goal on the billboards (hidden in
   the store app, where the house ad takes the slot). No photos, no logos, no real brands, no yellow. */
(function (root) {
  "use strict";
  const LIB = root.ChismeLowrider; if (!LIB) return;
  let H = null;   // the game's drawing helpers, handed in on every draw call (rr, lg, rg, shade, hexA, fitText, outlined, drawPerson…)
  const PI = Math.PI, TAU = 6.2832;
  const C = { stone: "#cdbfb3", stoneD: "#a8968e", lime: "#e3d9d2", sand: "#c9ab95", brick: "#9a4a3a", tile: "#b04a36", ink: "#1b1228", dark: "#2a1d3a",
    white: "#eeeaf2", green: "#2f6b4a", leaf: "#1f5e3c", water: "#2f7fb0", pink: "#FF1A7F", turq: "#14b8b0", orange: "#ff6a0b", purple: "#7a3fd1", red: "#d8322a" };

  // ---- tiny drawing helpers (lot space: x from the lot's left edge, y = 0 at the sidewalk, up is negative)
  function face(g, x, y, w, h, col) { g.fillStyle = H.lg(g, 0, y, 0, y + h, [[0, H.shade(col, 0.1)], [1, H.shade(col, -0.22)]]); g.fillRect(x, y, w, h); }
  function box(g, col, x, y, w, h, r) { g.fillStyle = col; if (r) { H.rr(g, x, y, w, h, r); g.fill(); } else g.fillRect(x, y, w, h); }
  function poly(g, col, p) { g.fillStyle = col; g.beginPath(); g.moveTo(p[0], p[1]); for (let i = 2; i < p.length; i += 2) g.lineTo(p[i], p[i + 1]); g.closePath(); g.fill(); }
  function arch(g, col, x, y, w, h) { g.fillStyle = col; g.beginPath(); g.moveTo(x, y + h); g.lineTo(x, y + w / 2); g.arc(x + w / 2, y + w / 2, w / 2, PI, 0); g.lineTo(x + w, y + h); g.closePath(); g.fill(); }
  function litArch(g, x, y, w, h) { arch(g, C.ink, x - 1.5, y - 1.5, w + 3, h + 1.5); g.fillStyle = H.lg(g, 0, y, 0, y + h, [[0, "#ffd6e6"], [0.6, "#ff9cc2"], [1, "#d86a9c"]]); arch(g, g.fillStyle, x, y, w, h); }
  function darkArch(g, x, y, w, h) { arch(g, "#1a1222", x, y, w, h); }
  function win(g, x, y, w, h, lit) { box(g, C.ink, x - 1, y - 1, w + 2, h + 2); box(g, lit ? H.lg(g, 0, y, 0, y + h, [[0, "#ffd6e6"], [1, "#e07aa6"]]) : "#3a3150", x, y, w, h); }
  function cross(g, x, y, s, col) { box(g, col || C.ink, x - s * 0.12, y - s, s * 0.24, s); box(g, col || C.ink, x - s * 0.35, y - s * 0.75, s * 0.7, s * 0.2); }
  function dome(g, col, x, y, r, sq) { g.fillStyle = H.lg(g, x - r, 0, x + r, 0, [[0, H.shade(col, 0.15)], [1, H.shade(col, -0.25)]]); g.beginPath(); g.ellipse(x, y, r, r * (sq || 1), 0, PI, TAU); g.fill(); }
  function oak(g, x, y, s) { box(g, "#3a2420", x - 3 * s, y - 26 * s, 6 * s, 26 * s); for (const [dx, dy, r] of [[-14, -34, 15], [10, -38, 17], [0, -48, 16], [-4, -30, 13], [18, -28, 11]]) { g.fillStyle = dy < -40 ? "#2f6b4a" : "#24583c"; g.beginPath(); g.arc(x + dx * s, y + dy * s, r * s, 0, TAU); g.fill(); } }
  function txt(g, t, x, y, size, col, o = {}) { g.textAlign = o.align || "center"; g.textBaseline = "middle"; H.fitText(g, t, o.max || 999, size, o.weight || "900", o.font || H.SANS); if (o.sx) { g.save(); g.translate(x, y); g.scale(o.sx, 1); H.outlined(g, t, 0, 0, col, o.stroke, o.lw || 2); g.restore(); } else H.outlined(g, t, x, y, col, o.stroke, o.lw || 2); }
  function rim(g, x, y, w, h) { g.fillStyle = "rgba(255,120,150,.18)"; g.fillRect(x, y, Math.min(6, w), h); }   // a sunset rim light on the left edge
  function flag(g, x, y) { box(g, "#3a3150", x, y, 2, 30); box(g, "#ffffff", x + 2, y, 20, 12); box(g, "#c8102e", x + 2, y + 6, 20, 6); box(g, "#1f3a93", x + 2, y, 7, 12); g.fillStyle = "#fff"; g.beginPath(); g.arc(x + 5.5, y + 3, 1.6, 0, TAU); g.fill(); }
  function people(g, xs, cols) { for (let i = 0; i < xs.length; i++) { box(g, cols[i % cols.length], xs[i] - 3, -14, 6, 10, 2); g.fillStyle = "#6a3a2a"; g.beginPath(); g.arc(xs[i], -17, 3, 0, TAU); g.fill(); } }

  // ---- LANDMARKS: { id, name (the tag), w, top (drawing height), tagY?, draw(g, w) }. Cartoon silhouettes, not photos.
  const LANDMARKS = [
    { id: "alamo", name: "The Alamo", w: 250, top: 176, draw(g, w) {
      face(g, 20, -130, w - 40, 130, C.lime); rim(g, 20, -130, w - 40, 130);
      g.fillStyle = H.lg(g, 0, -170, 0, -126, [[0, H.shade(C.lime, 0.12)], [1, H.shade(C.lime, -0.05)]]); g.beginPath(); g.moveTo(w / 2 - 70, -128); g.bezierCurveTo(w / 2 - 66, -150, w / 2 - 34, -146, w / 2 - 24, -160); g.quadraticCurveTo(w / 2, -176, w / 2 + 24, -160); g.bezierCurveTo(w / 2 + 34, -146, w / 2 + 66, -150, w / 2 + 70, -128); g.closePath(); g.fill();   // the hump
      box(g, H.shade(C.lime, -0.12), 20, -132, w - 40, 5); box(g, H.shade(C.lime, -0.12), w / 2 - 74, -130, 148, 4);
      darkArch(g, w / 2 - 20, -76, 40, 76); box(g, "#5a3424", w / 2 - 17, -48, 34, 48);   // the door
      for (const dx of [-60, -40, 40, 60]) { box(g, H.shade(C.lime, -0.08), w / 2 + dx - 4, -112, 8, 112); box(g, "rgba(0,0,0,.08)", w / 2 + dx + 2, -112, 2, 112); }   // the columns
      for (const dx of [-50, 50]) { darkArch(g, w / 2 + dx - 7, -104, 14, 26); darkArch(g, w / 2 + dx - 7, -60, 14, 26); }   // niches
      darkArch(g, w / 2 - 12, -118, 24, 30); box(g, "rgba(0,0,0,.1)", 20, -6, w - 40, 6);
      oak(g, 12, 0, 1.1); oak(g, w - 10, 0, 0.9); flag(g, w / 2 - 1, -206 + 30); } },
    { id: "tower", name: "Tower of the Americas", w: 150, top: 330, tagY: 300, draw(g, w) {
      const cx = w / 2; poly(g, "#bdb4c6", [cx - 16, 0, cx - 7, -262, cx + 7, -262, cx + 16, 0]); poly(g, "rgba(0,0,0,.18)", [cx + 2, 0, cx + 2, -262, cx + 7, -262, cx + 16, 0]);
      for (let y = -30; y > -250; y -= 24) box(g, "rgba(255,255,255,.18)", cx - 6, y, 2, 10);   // the elevator glass
      box(g, "#9a8fa8", cx - 34, -270, 68, 6, 3); box(g, "#e9e3ee", cx - 40, -292, 80, 22, 6); for (let i = 0; i < 9; i++) box(g, "#ff9cc2", cx - 36 + i * 8.4, -286, 6, 9, 1);   // the top house, lit
      box(g, "#9a8fa8", cx - 30, -304, 60, 12, 5); box(g, "#7a7088", cx - 2, -330, 4, 28); g.fillStyle = "#ff3355"; g.beginPath(); g.arc(cx, -331, 2.6, 0, TAU); g.fill();
      oak(g, 20, 0, 0.8); oak(g, w - 18, 0, 0.7); } },
    { id: "sanfernando", name: "San Fernando Cathedral", w: 230, top: 236, draw(g, w) {
      face(g, 30, -150, w - 60, 150, C.stone); rim(g, 30, -150, w - 60, 150);
      for (const x of [14, w - 60]) { face(g, x, -196, 46, 196, H.shade(C.stone, 0.04)); poly(g, H.shade(C.stone, -0.1), [x - 2, -196, x + 23, -226, x + 48, -196]); cross(g, x + 23, -224, 16); darkArch(g, x + 15, -176, 16, 30); litArch(g, x + 16, -110, 14, 26); }
      poly(g, H.shade(C.stone, 0.06), [60, -150, w / 2, -186, w - 60, -150]); cross(g, w / 2, -184, 18);
      g.fillStyle = C.ink; g.beginPath(); g.arc(w / 2, -150, 15, 0, TAU); g.fill(); g.fillStyle = "#ff9cc2"; g.beginPath(); g.arc(w / 2, -150, 12, 0, TAU); g.fill();   // the rose window
      g.strokeStyle = C.ink; g.lineWidth = 1.2; for (let a = 0; a < 8; a++) { g.beginPath(); g.moveTo(w / 2, -150); g.lineTo(w / 2 + Math.cos(a * 0.785) * 12, -150 + Math.sin(a * 0.785) * 12); g.stroke(); }
      for (const dx of [-36, 36]) litArch(g, w / 2 + dx - 8, -116, 16, 44); darkArch(g, w / 2 - 18, -74, 36, 74); box(g, "#4a2a26", w / 2 - 15, -48, 30, 48); } },
    { id: "sanjose", name: "Mission San José", w: 250, top: 200, draw(g, w) {
      face(g, 70, -120, w - 80, 120, C.sand); rim(g, 70, -120, w - 80, 120); dome(g, H.shade(C.sand, 0.05), 190, -120, 34, 0.8); box(g, H.shade(C.sand, -0.05), 186, -160, 8, 14); cross(g, 190, -160, 12);
      face(g, 20, -170, 54, 170, H.shade(C.sand, 0.04)); box(g, H.shade(C.sand, -0.12), 18, -172, 58, 6); darkArch(g, 36, -160, 22, 36); dome(g, C.sand, 47, -172, 14, 0.9); cross(g, 47, -184, 10);   // the bell tower
      darkArch(g, 110, -80, 34, 80); for (const dx of [96, 150]) box(g, H.shade(C.sand, -0.1), dx, -104, 6, 104);
      // the Rose Window: carved stone curls around a small window
      const rx = 210, ry = -66; g.fillStyle = H.shade(C.sand, -0.18); g.beginPath(); g.ellipse(rx, ry, 18, 24, 0, 0, TAU); g.fill();
      g.strokeStyle = "#f0d6c8"; g.lineWidth = 2; for (let i = 0; i < 6; i++) { const a = i * 1.05; g.beginPath(); g.arc(rx + Math.cos(a) * 15, ry + Math.sin(a) * 19, 4, a, a + 4.2); g.stroke(); }
      litArch(g, rx - 7, ry - 12, 14, 24); g.fillStyle = "rgba(255,255,255,.6)"; g.font = `800 6px ${H.SANS}`; g.textAlign = "center"; g.fillText("ROSE WINDOW", rx, ry + 34); } },
    { id: "espada", name: "Espada Aqueduct", w: 250, top: 120, draw(g, w) {
      box(g, H.lg(g, 0, -20, 0, 0, [[0, "#3f8fc0"], [1, "#2a6a96"]]), 0, -18, w, 18); g.fillStyle = "rgba(255,255,255,.35)"; for (let x = 6; x < w; x += 22) g.fillRect(x, -10, 10, 1.2);   // the creek
      face(g, 10, -86, w - 20, 34, C.sand); box(g, H.shade(C.sand, -0.15), 10, -88, w - 20, 5); box(g, "#3a84b5", 14, -94, w - 28, 6);   // the channel on top
      for (let i = 0; i < 2; i++) { const x = 40 + i * 92; face(g, x - 30, -52, 12, 34, C.sand); face(g, x + 62, -52, 12, 34, C.sand); g.fillStyle = H.shade(C.sand, -0.05); g.beginPath(); g.moveTo(x - 18, -52); g.arc(x + 22, -52, 40, PI, 0); g.lineTo(x + 62, -52); g.lineTo(x + 62, -70); g.lineTo(x - 18, -70); g.fill(); }
      for (let i = 0; i < 2; i++) { const x = 40 + i * 92; g.fillStyle = "#1a2a3a"; g.beginPath(); g.moveTo(x - 18, -18); g.lineTo(x - 18, -52); g.arc(x + 22, -52, 40, PI, 0, false); g.lineTo(x + 62, -18); g.fill(); }
      oak(g, w - 20, 0, 0.9); } },
    { id: "mercado", name: "Market Square · El Mercado", w: 260, top: 150, draw(g, w) {
      face(g, 6, -110, w - 12, 110, "#e8a0a8"); rim(g, 6, -110, w - 12, 110); box(g, "#b9435a", 6, -116, w - 12, 8);
      for (let i = 0; i < 5; i++) { const x = 18 + i * 48; arch(g, "#7a2a4a", x, -84, 36, 84); arch(g, i % 2 ? "#ffb3c8" : "#ff9a62", x + 3, -80, 30, 80); people(g, [x + 12, x + 24], ["#14b8b0", "#7a3fd1", "#ff1a7f"]); }
      txt(g, "EL MERCADO", w / 2, -100, 13, "#ffffff", { stroke: "#7a2a4a", lw: 3, max: 150 });
      H.papelPicado(g, 0, w / 2, -136); H.papelPicado(g, w / 2, w, -136); } },
    { id: "riverwalk", name: "River Walk", w: 270, top: 140, draw(g, w) {
      box(g, H.lg(g, 0, -40, 0, 0, [[0, "#2e8a8a"], [1, "#1d5e66"]]), 0, -36, w, 36); g.fillStyle = "rgba(255,255,255,.3)"; for (let x = 4; x < w; x += 18) g.fillRect(x, -22 + (x % 3), 8, 1);
      face(g, 0, -40, w, 6, C.stone); face(g, 0, -6, w, 6, C.stone);
      for (const [x, c] of [[24, C.pink], [196, C.turq]]) { box(g, "#5a3424", x + 16, -86, 3, 46); g.fillStyle = c; g.beginPath(); g.moveTo(x, -84); g.quadraticCurveTo(x + 18, -104, x + 36, -84); g.fill(); box(g, "#3a2a40", x + 6, -60, 24, 3); }   // café umbrellas
      g.fillStyle = C.stone; g.beginPath(); g.moveTo(90, -40); g.quadraticCurveTo(140, -96, 190, -40); g.lineTo(190, -52); g.quadraticCurveTo(140, -112, 90, -52); g.fill(); box(g, "#3a3150", 92, -110, 96, 2);   // a stone footbridge
      // a river barge with riders
      const bx = 110; box(g, "#1f6b8a", bx, -30, 96, 12, 4); box(g, "#e9e3ee", bx + 4, -32, 88, 3); box(g, "#3a3150", bx + 10, -48, 2, 16); box(g, "#3a3150", bx + 84, -48, 2, 16); box(g, C.turq, bx + 6, -50, 84, 4, 2);
      people(g, [bx + 22, bx + 36, bx + 50, bx + 64, bx + 78].map((x) => x), [C.pink, "#ffffff", C.orange, C.purple]); for (let i = 0; i < 5; i++) {} 
      oak(g, 60, -40, 0.8); oak(g, 240, -40, 0.9); H.stringLights(g, 0, w, -118, 6); } },
    { id: "hays", name: "Hays Street Bridge", w: 280, top: 130, draw(g, w) {
      box(g, "#5a4a5e", 0, -34, w, 8); for (const x of [30, w - 40]) box(g, C.stoneD, x, -34, 12, 34);
      g.strokeStyle = "#a8432e"; g.lineWidth = 4; g.lineJoin = "round"; g.beginPath(); g.moveTo(8, -36); g.lineTo(30, -104); g.lineTo(w - 30, -104); g.lineTo(w - 8, -36); g.stroke();
      g.lineWidth = 2.4; g.beginPath(); for (let i = 0; i <= 8; i++) { const x = 30 + i * (w - 60) / 8; g.moveTo(x, -104); g.lineTo(x, -36); if (i < 8) { g.moveTo(x, -104); g.lineTo(x + (w - 60) / 8, -36); g.moveTo(x + (w - 60) / 8, -104); g.lineTo(x, -36); } } g.stroke();
      box(g, "#7a2e22", 26, -108, w - 52, 4); people(g, [80, 96, 190], [C.turq, C.pink, "#ffffff"]); } },
    { id: "majestic", name: "Majestic Theatre", w: 150, top: 250, draw(g, w) {
      face(g, 10, -200, w - 20, 200, "#b88a7e"); rim(g, 10, -200, w - 20, 200); for (let y = -186; y < -70; y += 26) for (let x = 22; x < w - 20; x += 22) win(g, x, y, 12, 16, (x + y) % 3 === 0);
      box(g, "#7a1428", w / 2 - 15, -244, 30, 160, 4); box(g, "#ff3355", w / 2 - 12, -240, 24, 152, 3);
      [..."MAJESTIC"].forEach((ch, i) => txt(g, ch, w / 2, -230 + i * 18.6, 15, "#ffffff", { stroke: "#7a1428", lw: 2 })); H.drawGlow(g, w / 2, -160, 50, "#ff3355", 0.25);
      box(g, C.ink, 4, -74, w - 8, 22, 3); for (let x = 8; x < w - 8; x += 7) box(g, Math.floor(x / 7) % 2 ? "#ffffff" : "#ff9cc2", x, -72, 3, 3); txt(g, "TONIGHT", w / 2, -60, 10, "#ffffff", { max: w - 30 }); darkArch(g, w / 2 - 22, -50, 44, 50); } },
    { id: "aztec", name: "Aztec Theatre", w: 170, top: 210, draw(g, w) {
      face(g, 8, -170, w - 16, 170, "#c98c72"); rim(g, 8, -170, w - 16, 170);
      for (let i = 0; i < 6; i++) poly(g, "#8a3a2a", [8 + i * (w - 16) / 6, -170, 8 + (i + 0.5) * (w - 16) / 6, -186, 8 + (i + 1) * (w - 16) / 6, -170]);   // stepped crest
      for (let x = 16; x < w - 16; x += 14) { box(g, "#8a3a2a", x, -160, 10, 4); box(g, C.turq, x + 3, -152, 4, 4); }
      box(g, "#1f6b6a", w / 2 - 14, -200, 28, 104, 4); [..."AZTEC"].forEach((ch, i) => txt(g, ch, w / 2, -188 + i * 20, 16, "#ffffff", { stroke: "#0f3d3c", lw: 2 })); H.drawGlow(g, w / 2, -150, 46, "#14b8b0", 0.25);
      box(g, C.ink, 4, -86, w - 8, 20, 3); for (let x = 8; x < w - 8; x += 7) box(g, Math.floor(x / 7) % 2 ? "#ffffff" : "#5ad6cf", x, -84, 3, 3); darkArch(g, w / 2 - 24, -64, 48, 64); } },
    { id: "library", name: "Central Library", w: 230, top: 180, draw(g, w) {
      face(g, 10, -130, 150, 130, "#d2312e"); rim(g, 10, -130, 150, 130); face(g, 110, -164, 70, 60, "#e04a38"); face(g, 150, -100, 70, 100, "#c42a30"); face(g, 60, -150, 40, 30, "#7a3fd1");
      g.fillStyle = "#ff9a62"; g.beginPath(); g.arc(196, -132, 16, 0, TAU); g.fill(); box(g, "#a8203a", 192, -116, 8, 16);   // the orange ball on a stand
      for (let i = 0; i < 4; i++) win(g, 26 + i * 30, -92, 18, 30, i % 2 === 0); box(g, "#1a1222", 170, -60, 34, 60); box(g, C.purple, 10, -16, 150, 6);
      g.fillStyle = "rgba(255,255,255,.7)"; g.font = `800 7px ${H.SANS}`; g.textAlign = "left"; g.fillText("“ENCHILADA RED”", 20, -112); } },
    { id: "torch", name: "Torch of Friendship", w: 140, top: 220, draw(g, w) {
      const cx = w / 2; g.fillStyle = H.lg(g, cx - 30, 0, cx + 30, 0, [[0, "#ff5a3a"], [1, "#c0262a"]]);
      g.beginPath(); g.moveTo(cx - 26, 0); g.bezierCurveTo(cx - 30, -80, cx + 30, -110, cx - 6, -200); g.bezierCurveTo(cx + 14, -150, cx - 10, -90, cx - 8, 0); g.fill();
      g.fillStyle = H.lg(g, cx - 30, 0, cx + 30, 0, [[0, "#e0332e"], [1, "#9a1a2a"]]); g.beginPath(); g.moveTo(cx + 26, 0); g.bezierCurveTo(cx + 30, -90, cx - 30, -120, cx + 10, -206); g.bezierCurveTo(cx - 16, -150, cx + 12, -86, cx + 6, 0); g.fill();
      box(g, "#7a7088", cx - 34, -6, 68, 6, 2); } },
    { id: "boots", name: "World's Largest Cowboy Boots", w: 170, top: 190, draw(g, w) {
      const boot = (x, col) => { g.fillStyle = col; g.beginPath(); g.moveTo(x, -150); g.lineTo(x + 46, -150); g.lineTo(x + 44, -40); g.quadraticCurveTo(x + 76, -36, x + 80, -6); g.lineTo(x + 80, 0); g.lineTo(x - 4, 0); g.lineTo(x - 2, -40); g.closePath(); g.fill();
        g.strokeStyle = "#f0d6c8"; g.lineWidth = 2; for (let y = -136; y < -50; y += 20) { g.beginPath(); g.moveTo(x + 8, y); g.quadraticCurveTo(x + 23, y + 10, x + 38, y); g.stroke(); }
        box(g, "#3a1f1a", x - 4, -8, 84, 8, 2); box(g, H.shade(col, 0.2), x, -150, 46, 8); };
      boot(10, "#8a4a2e"); boot(78, "#7a3f2a"); box(g, "#7a7088", 0, -2, w, 4); } },
    { id: "alamodome", name: "Alamodome", w: 300, top: 170, draw(g, w) {
      g.fillStyle = H.lg(g, 0, -120, 0, 0, [[0, "#f1eef6"], [1, "#bdb6c9"]]); g.beginPath(); g.moveTo(30, 0); g.lineTo(30, -70); g.quadraticCurveTo(w / 2, -130, w - 30, -70); g.lineTo(w - 30, 0); g.fill();
      for (let i = 1; i < 8; i++) { g.strokeStyle = "rgba(0,0,0,.12)"; g.lineWidth = 1; g.beginPath(); g.moveTo(30 + i * (w - 60) / 8, -70 - Math.sin(i / 8 * PI) * 30); g.lineTo(30 + i * (w - 60) / 8, 0); g.stroke(); }
      for (const x of [22, 70, w - 78, w - 30]) { box(g, "#d9d3e2", x, -162, 8, 162); box(g, "#ff3355", x + 2, -166, 4, 4); g.strokeStyle = "rgba(60,50,80,.6)"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(x + 4, -158); g.lineTo(w / 2, -100); g.stroke(); }
      box(g, "#8a83a0", 30, -22, w - 60, 22); for (let x = 44; x < w - 44; x += 20) win(g, x, -18, 12, 12, true); } },
    { id: "teagarden", name: "Japanese Tea Garden", w: 260, top: 170, draw(g, w) {
      box(g, H.lg(g, 0, -20, 0, 0, [[0, "#3f8fc0"], [1, "#2a6a96"]]), 120, -16, 130, 16); for (const [x, c] of [[150, "#ff6a0b"], [190, "#ffffff"], [222, "#ff6a0b"]]) { g.fillStyle = c; g.beginPath(); g.ellipse(x, -8, 5, 2, 0, 0, TAU); g.fill(); }   // koi
      face(g, 20, -100, 16, 100, C.stoneD); face(g, 92, -100, 16, 100, C.stoneD); face(g, 14, -116, 100, 16, C.stone);   // the stone gate
      g.fillStyle = "#3a2a40"; g.beginPath(); g.moveTo(4, -116); g.quadraticCurveTo(64, -128, 124, -116); g.lineTo(118, -132); g.quadraticCurveTo(64, -142, 10, -132); g.fill();
      for (let k = 0; k < 3; k++) { const y = -60 - k * 26, ww = 52 - k * 10, x = 190; box(g, "#b9435a", x - ww / 2 + 6, y, ww - 12, 18); g.fillStyle = "#2a1d3a"; g.beginPath(); g.moveTo(x - ww / 2 - 6, y); g.quadraticCurveTo(x, y - 10, x + ww / 2 + 6, y); g.lineTo(x + ww / 2 - 2, y - 8); g.lineTo(x - ww / 2 + 2, y - 8); g.fill(); }   // a little pagoda
      box(g, "#2a1d3a", 188, -152, 4, 14); oak(g, 140, -16, 0.7); H.marigolds(g, 40, 0, 6); } },
    { id: "pearl", name: "Pearl Brewery", w: 180, top: 240, draw(g, w) {
      face(g, 10, -150, w - 20, 150, "#9a4a3a"); rim(g, 10, -150, w - 20, 150); for (let y = -136; y < -20; y += 30) for (let x = 24; x < w - 24; x += 26) arch(g, C.ink, x, y, 14, 22);
      face(g, w / 2 - 30, -206, 60, 56, "#a8543f"); g.fillStyle = "#3a3150"; g.beginPath(); g.moveTo(w / 2 - 36, -206); g.quadraticCurveTo(w / 2 - 30, -232, w / 2, -236); g.quadraticCurveTo(w / 2 + 30, -232, w / 2 + 36, -206); g.fill();   // the mansard tower
      box(g, "#3a3150", w / 2 - 2, -248, 4, 14); g.fillStyle = "#f1eef6"; g.beginPath(); g.arc(w / 2, -186, 12, 0, TAU); g.fill(); g.strokeStyle = C.ink; g.lineWidth = 1.4; g.beginPath(); g.moveTo(w / 2, -186); g.lineTo(w / 2, -194); g.moveTo(w / 2, -186); g.lineTo(w / 2 + 6, -184); g.stroke();
      H.stringLights(g, 10, w - 10, -150, 4); } },
    { id: "tobin", name: "Tobin Center", w: 250, top: 190, draw(g, w) {
      face(g, 20, -110, w - 40, 110, "#d8c4b6"); for (let i = 0; i < 4; i++) darkArch(g, 44 + i * 44, -80, 30, 80);
      g.fillStyle = H.lg(g, 0, -170, w, 0, [[0, "#7a3fd1"], [0.5, "#ff1a7f"], [1, "#14b8b0"]]); g.beginPath(); g.moveTo(10, -110); g.quadraticCurveTo(w / 2, -190, w - 10, -110); g.lineTo(w - 10, -96); g.quadraticCurveTo(w / 2, -170, 10, -96); g.fill();   // the lit metal skin
      g.globalAlpha = 0.5; for (let i = 0; i < 18; i++) box(g, "#ffffff", 22 + i * 12, -132 - Math.sin(i / 17 * PI) * 30, 2, 8); g.globalAlpha = 1; H.drawGlow(g, w / 2, -140, 90, "#ff1a7f", 0.2); } },
    { id: "concepcion", name: "Mission Concepción", w: 240, top: 210, draw(g, w) {
      face(g, 50, -120, w - 100, 120, C.sand); rim(g, 50, -120, w - 100, 120); poly(g, H.shade(C.sand, 0.06), [70, -120, w / 2, -150, w - 70, -120]); dome(g, C.sand, w / 2 + 40, -126, 22, 0.9);
      for (const x of [16, w - 64]) { face(g, x, -160, 48, 160, H.shade(C.sand, 0.03)); box(g, H.shade(C.sand, -0.12), x - 2, -162, 52, 6); darkArch(g, x + 14, -152, 20, 30); dome(g, C.sand, x + 24, -162, 16, 0.8); cross(g, x + 24, -176, 10); }
      darkArch(g, w / 2 - 20, -76, 40, 76); g.fillStyle = C.ink; g.beginPath(); g.arc(w / 2, -98, 7, 0, TAU); g.fill(); } },
    { id: "villita", name: "La Villita", w: 260, top: 130, draw(g, w) {
      for (const [x, ww, c] of [[10, 70, "#e3c9b8"], [90, 80, "#cdbfb3"], [180, 70, "#e8b4a8"]]) { face(g, x, -60, ww, 60, c); poly(g, "#7a4a3e", [x - 4, -60, x + ww / 2, -84, x + ww + 4, -60]); win(g, x + 10, -44, 14, 18, true); darkArch(g, x + ww - 28, -40, 18, 40); }
      H.stringLights(g, 0, w, -96, 8); H.papelPicado(g, 20, w - 20, -108); } },
    { id: "courthouse", name: "Bexar County Courthouse", w: 260, top: 230, draw(g, w) {
      const red = "#b4534a"; face(g, 10, -140, w - 20, 140, red); rim(g, 10, -140, w - 20, 140);
      for (const [x, ww, hh] of [[20, 54, 200], [w - 74, 54, 176]]) { face(g, x, -hh, ww, hh, H.shade(red, 0.05)); poly(g, "#5a3a4a", [x - 4, -hh, x + ww / 2, -hh - 30, x + ww + 4, -hh]); darkArch(g, x + 16, -hh + 20, 22, 30); }
      for (let i = 0; i < 4; i++) darkArch(g, 88 + i * 24, -58, 18, 58); for (let i = 0; i < 4; i++) litArch(g, 88 + i * 24, -116, 16, 30); } },
    { id: "buckhorn", name: "Buckhorn Saloon", w: 200, top: 170, draw(g, w) {
      face(g, 10, -120, w - 20, 120, "#8a5a46"); rim(g, 10, -120, w - 20, 120); box(g, "#5a3424", 6, -130, w - 12, 12); box(g, "#3a2420", 10, -70, w - 20, 6);
      for (let i = 0; i < 3; i++) win(g, 26 + i * 54, -110, 30, 32, true); darkArch(g, w / 2 - 18, -60, 36, 60); box(g, "#6a3a2a", w / 2 - 16, -34, 14, 22); box(g, "#6a3a2a", w / 2 + 2, -34, 14, 22);   // swinging doors
      g.strokeStyle = "#f0e0d6"; g.lineWidth = 4; g.lineCap = "round"; g.beginPath(); g.moveTo(w / 2, -140); g.quadraticCurveTo(w / 2 - 30, -150, w / 2 - 50, -168); g.moveTo(w / 2, -140); g.quadraticCurveTo(w / 2 + 30, -150, w / 2 + 50, -168); g.stroke();   // longhorns over the door
      g.fillStyle = "#6a3a2a"; g.beginPath(); g.ellipse(w / 2, -138, 10, 13, 0, 0, TAU); g.fill(); } },
    { id: "menger", name: "Menger Hotel", w: 230, top: 180, draw(g, w) {
      face(g, 10, -150, w - 20, 150, "#d8cbc4"); rim(g, 10, -150, w - 20, 150); box(g, "#a8968e", 6, -156, w - 12, 8);
      for (let r = 0; r < 3; r++) { const y = -136 + r * 44; for (let x = 24; x < w - 24; x += 26) win(g, x, y, 14, 24, (x + r) % 3 === 0); box(g, "#3a3150", 14, y + 28, w - 28, 3); for (let x = 16; x < w - 16; x += 6) box(g, "#3a3150", x, y + 20, 1.2, 8); }
      darkArch(g, w / 2 - 16, -40, 32, 40); flag(g, w / 2 - 1, -186); } },
    { id: "mcnay", name: "McNay Art Museum", w: 250, top: 170, draw(g, w) {
      face(g, 20, -90, w - 40, 90, "#efe9ee"); rim(g, 20, -90, w - 40, 90); poly(g, C.tile, [12, -90, w / 2, -116, w - 12, -90]);
      face(g, w - 90, -140, 46, 50, "#efe9ee"); poly(g, C.tile, [w - 96, -140, w - 67, -162, w - 38, -140]); litArch(g, w - 78, -130, 20, 30);
      for (let i = 0; i < 4; i++) litArch(g, 40 + i * 36, -70, 20, 40); oak(g, 10, 0, 1); H.palm(g, w - 10, 0, 110); } },
    { id: "witte", name: "Witte Museum", w: 260, top: 170, draw(g, w) {
      face(g, 90, -100, w - 100, 100, "#d8c4b6"); rim(g, 90, -100, w - 100, 100); box(g, C.tile, 86, -106, w - 92, 8); for (let i = 0; i < 4; i++) darkArch(g, 108 + i * 36, -66, 22, 66);
      g.strokeStyle = "#e9e3ee"; g.lineWidth = 3.4; g.lineCap = "round"; g.beginPath(); g.moveTo(10, -50); g.quadraticCurveTo(30, -60, 50, -56); g.quadraticCurveTo(70, -48, 74, -110); g.quadraticCurveTo(78, -128, 92, -126); g.stroke();   // a dinosaur skeleton out front
      g.lineWidth = 2; for (let x = 24; x < 66; x += 7) { g.beginPath(); g.moveTo(x, -56); g.lineTo(x + 2, -40); g.stroke(); } g.beginPath(); g.moveTo(38, -50); g.lineTo(34, 0); g.moveTo(58, -50); g.lineTo(62, 0); g.stroke();
      g.fillStyle = "#e9e3ee"; g.beginPath(); g.ellipse(96, -126, 7, 4, 0, 0, TAU); g.fill(); } },
    { id: "rubycity", name: "Ruby City", w: 220, top: 180, draw(g, w) {
      g.fillStyle = H.lg(g, 0, -170, 0, 0, [[0, "#e0303a"], [1, "#8a1424"]]); g.beginPath(); g.moveTo(20, 0); g.lineTo(30, -110); g.lineTo(90, -170); g.lineTo(120, -120); g.lineTo(200, -130); g.lineTo(206, 0); g.fill();
      g.fillStyle = "rgba(255,255,255,.25)"; const r = H.rng(5); for (let i = 0; i < 120; i++) g.fillRect(24 + r() * 176, -r() * 120 - 4, 1.2, 1.2);   // the sparkle in the concrete
      box(g, "#2a0d18", 140, -50, 40, 50); } },
    { id: "bluestar", name: "Blue Star Arts Complex", w: 260, top: 150, draw(g, w) {
      for (const [x, ww] of [[6, 120], [130, 124]]) { face(g, x, -84, ww, 84, "#9a8f97"); poly(g, "#5a5068", [x - 2, -84, x + ww / 2, -104, x + ww + 2, -84]); for (let k = 0; k < 3; k++) win(g, x + 12 + k * 36, -64, 24, 22, k === 1); }
      const sx = 190, sy = -126, R = 20; g.fillStyle = "#2f6bd6"; g.beginPath(); for (let i = 0; i < 10; i++) { const a = -PI / 2 + i * PI / 5, rr = i % 2 ? R * 0.45 : R; g.lineTo(sx + Math.cos(a) * rr, sy + Math.sin(a) * rr); } g.fill(); H.drawGlow(g, sx, sy, 40, "#2f6bd6", 0.3); box(g, "#3a3150", sx - 1, sy + 18, 2, 24); } },
    { id: "frost", name: "Frost Bank Center", w: 300, top: 150, draw(g, w) {
      g.fillStyle = H.lg(g, 0, -110, 0, 0, [[0, "#c9c3d6"], [1, "#6a6080"]]); g.beginPath(); g.moveTo(10, 0); g.lineTo(20, -86); g.quadraticCurveTo(w / 2, -124, w - 20, -86); g.lineTo(w - 10, 0); g.fill();
      box(g, "#1a1222", 30, -64, w - 60, 26); for (let x = 36; x < w - 36; x += 10) box(g, x % 20 ? "#ff9cc2" : "#9ad8ff", x, -58, 6, 14); box(g, "#3a3150", 10, -12, w - 20, 12); } },
    { id: "wolff", name: "Wolff Stadium", w: 280, top: 200, draw(g, w) {
      g.fillStyle = "#8a83a0"; g.beginPath(); g.moveTo(20, 0); g.lineTo(40, -70); g.lineTo(w - 40, -70); g.lineTo(w - 20, 0); g.fill(); for (let y = -60; y < 0; y += 10) box(g, "rgba(255,255,255,.18)", 40, y, w - 80, 2);
      for (const x of [26, w - 34]) { box(g, "#bdb6c9", x, -190, 6, 190); box(g, "#3a3150", x - 18, -196, 42, 24, 2); for (let k = 0; k < 8; k++) box(g, "#ffffff", x - 15 + (k % 4) * 9, -193 + Math.floor(k / 4) * 11, 7, 8); H.drawGlow(g, x + 3, -184, 50, "#ffffff", 0.4); }
      box(g, "#2f6b4a", 40, -10, w - 80, 10); } },
    { id: "fortsam", name: "Fort Sam Houston Clock Tower", w: 170, top: 230, draw(g, w) {
      face(g, 10, -70, w - 20, 70, C.stone); rim(g, 10, -70, w - 20, 70); for (let x = 22; x < w - 20; x += 22) win(g, x, -56, 12, 20, false);
      face(g, w / 2 - 22, -186, 44, 186, H.shade(C.stone, 0.05)); poly(g, "#5a5068", [w / 2 - 26, -186, w / 2, -214, w / 2 + 26, -186]); box(g, "#3a3150", w / 2 - 1, -226, 2, 14);
      g.fillStyle = "#f1eef6"; g.beginPath(); g.arc(w / 2, -160, 13, 0, TAU); g.fill(); g.strokeStyle = C.ink; g.lineWidth = 1.6; g.stroke(); g.beginPath(); g.moveTo(w / 2, -160); g.lineTo(w / 2, -169); g.moveTo(w / 2, -160); g.lineTo(w / 2 + 7, -157); g.stroke(); darkArch(g, w / 2 - 10, -130, 20, 30); } },
    { id: "hangar9", name: "Hangar 9", w: 260, top: 130, draw(g, w) {
      g.fillStyle = "#8a5a46"; g.beginPath(); g.moveTo(14, 0); g.lineTo(14, -60); g.lineTo(w / 2, -100); g.lineTo(w - 14, -60); g.lineTo(w - 14, 0); g.fill();
      g.strokeStyle = "rgba(0,0,0,.2)"; g.lineWidth = 1; for (let x = 20; x < w - 14; x += 8) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, -60 - (1 - Math.abs(x - w / 2) / (w / 2 - 14)) * 40); g.stroke(); }
      box(g, "#3a2420", 50, -54, w - 100, 54); box(g, "#5a3a2e", 52, -52, (w - 104) / 2 - 1, 52); txt(g, "9", w / 2, -78, 16, "#ffffff", { stroke: "#3a2420", lw: 3 }); } },
    { id: "guenther", name: "Guenther House", w: 220, top: 160, draw(g, w) {
      face(g, 20, -100, w - 40, 100, "#f1eef6"); rim(g, 20, -100, w - 40, 100); poly(g, "#5a6e8a", [12, -100, w / 2, -136, w - 12, -100]);
      box(g, "#3a3150", 20, -50, w - 40, 4); for (let x = 24; x < w - 24; x += 8) box(g, "#e9e3ee", x, -50, 2, 50); for (let i = 0; i < 3; i++) win(g, 40 + i * 54, -86, 20, 26, i !== 1); darkArch(g, w / 2 - 12, -40, 24, 40);
      oak(g, 6, 0, 0.9); H.marigolds(g, 30, 0, 8); } },
    { id: "littleflower", name: "Little Flower Basilica", w: 240, top: 236, draw(g, w) {
      face(g, 30, -130, w - 60, 130, "#c98c72"); rim(g, 30, -130, w - 60, 130); dome(g, "#7a8fa8", w / 2, -130, 46, 0.8); box(g, "#5a6e8a", w / 2 - 4, -178, 8, 12); cross(g, w / 2, -180, 14);
      face(g, w - 70, -196, 40, 196, "#c98c72"); dome(g, "#7a8fa8", w - 50, -196, 18, 1); cross(g, w - 50, -212, 12); darkArch(g, w - 60, -180, 20, 30);
      g.fillStyle = C.ink; g.beginPath(); g.arc(w / 2 - 20, -96, 14, 0, TAU); g.fill(); g.fillStyle = "#ff9cc2"; g.beginPath(); g.arc(w / 2 - 20, -96, 11, 0, TAU); g.fill(); darkArch(g, w / 2 - 38, -60, 36, 60); } },
  ];

  // ---- parody stores (our own made-up names + marks; no real logos, wordmarks or slogans)
  const HV = '"Avenir Next Condensed","Roboto Condensed","Arial Narrow","Helvetica Neue",Arial,sans-serif';
  function glass(g, x, y, w, h) { box(g, "#3a4f6e", x, y, w, h); g.fillStyle = "rgba(255,255,255,.22)"; g.beginPath(); g.moveTo(x + 3, y + h); g.lineTo(x + w * 0.5, y); g.lineTo(x + w * 0.7, y); g.lineTo(x + 8, y + h); g.fill(); }
  function burst(g, x, y, R, n, c1, c2) { g.fillStyle = c1; g.beginPath(); for (let i = 0; i < n * 2; i++) { const a = -PI / 2 + i * PI / n, r = i % 2 ? R * 0.55 : R; g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } g.fill(); g.fillStyle = c2; g.beginPath(); g.arc(x, y, R * 0.34, 0, TAU); g.fill(); }
  const STORES = [
    { id: "hondipo", name: "Hon Dipo", w: 300, top: 220, draw(g, w) {   // the Juan game's Hon Dipo: beige block, bright orange trim, the square orange sign, HON over DIPO
      const OR = "#f96302", OR2 = "#d95400"; box(g, H.lg(g, 0, -170, 0, 0, [[0, "#e0d6cc"], [1, "#cfc2b4"]]), 0, -170, w, 170); g.fillStyle = "rgba(120,96,70,.16)"; for (let x = 20; x < w; x += 20) g.fillRect(x, -160, 1, 156);
      box(g, H.lg(g, 0, -196, 0, -170, [[0, "#e9dbc6"], [1, "#ddcbb1"]]), w / 2 - 54, -196, 108, 26); box(g, OR, 0, -170, w, 10); box(g, OR2, 0, -160, w, 3); box(g, OR, w / 2 - 58, -198, 116, 8);
      box(g, OR, 0, -96, w, 12); txt(g, "LUMBER · TOOLS", 52, -90, 8, "#ffffff", { max: 84 }); txt(g, "PAINT · GARDEN", w - 52, -90, 8, "#ffffff", { max: 84 }); box(g, OR, 0, -5, w, 5);
      box(g, "rgba(0,0,0,.18)", w / 2 - 35, -215, 74, 74, 6); box(g, OR2, w / 2 - 38, -218, 74, 74, 6); box(g, H.lg(g, 0, -216, 0, -146, [[0, "#ff7a1f"], [0.5, OR], [1, "#ec5a00"]]), w / 2 - 36, -216, 70, 70, 5);
      for (const [t, y] of [["HON", -198], ["DIPO", -164]]) txt(g, t, w / 2 - 1, y, 30, "#ffffff", { font: HV, sx: 0.84, max: 92 }); box(g, "rgba(255,255,255,.85)", w / 2 - 26, -182, 50, 2);
      for (const x0 of [14, w - 84]) { box(g, H.lg(g, 0, -80, 0, -70, [[0, "#ff8a1a"], [1, OR2]]), x0 - 5, -80, 80, 10, 3); box(g, "#6c757d", x0, -70, 70, 70); glass(g, x0 + 3, -67, 31, 67); glass(g, x0 + 36, -67, 31, 67); }
      box(g, OR, w / 2 - 30, -40, 26, 28, 3); box(g, OR, w / 2 + 4, -40, 26, 28, 3); box(g, "#5a3a2e", w / 2 - 36, -12, 72, 4); } },   // carts out front
    { id: "gualmart", name: "Gualmart", w: 320, top: 170, draw(g, w) {   // a blue-and-white big box, our own orange + pink piñata starburst
      box(g, H.lg(g, 0, -130, 0, 0, [[0, "#e9eef6"], [1, "#c9d2e2"]]), 0, -130, w, 130); box(g, "#1f5fc4", 0, -130, w, 34); box(g, "#174a9a", 0, -96, w, 4);
      txt(g, "Gualmart", w / 2 - 20, -113, 26, "#ffffff", { font: H.FONT, max: 180, stroke: "#123a7a", lw: 3 }); burst(g, w / 2 + 92, -114, 17, 8, "#ff6a0b", "#FF1A7F"); g.fillStyle = "#ffffff"; g.beginPath(); g.arc(w / 2 + 92, -114, 3, 0, TAU); g.fill();
      box(g, "#1f5fc4", 0, -6, w, 6); txt(g, "SUPER BARATO · TODO EL DÍA", w / 2, -84, 8, "#1f5fc4", { max: 220 });
      box(g, "#174a9a", w / 2 - 50, -70, 100, 70); glass(g, w / 2 - 46, -66, 45, 66); glass(g, w / 2 + 1, -66, 45, 66); for (let i = 0; i < 4; i++) win(g, 18 + i * 22, -64, 14, 30, true); for (let i = 0; i < 4; i++) win(g, w - 96 + i * 22, -64, 14, 30, true);
      box(g, "#9aa6b8", 20, -12, 40, 3); box(g, "#9aa6b8", w - 60, -12, 40, 3); } },
    { id: "hebae", name: "H-E-Bae", w: 300, top: 180, draw(g, w) {   // our own red heart badge (not the real logo), a made-up slogan
      box(g, H.lg(g, 0, -126, 0, 0, [[0, "#efe9ee"], [1, "#d6ccd6"]]), 0, -126, w, 126); box(g, "#c8102e", 0, -126, w, 10); box(g, "#c8102e", 0, -8, w, 8);
      const hx = w / 2, hy = -132; g.fillStyle = "#c8102e"; g.beginPath(); g.moveTo(hx, hy + 32); g.bezierCurveTo(hx - 66, hy - 8, hx - 34, hy - 52, hx, hy - 22); g.bezierCurveTo(hx + 34, hy - 52, hx + 66, hy - 8, hx, hy + 32); g.fill();
      g.strokeStyle = "#ffffff"; g.lineWidth = 3; g.stroke(); txt(g, "H-E-Bae", hx, hy - 6, 20, "#ffffff", { font: H.FONT, max: 86 });
      txt(g, "Your Grocery Crush", w / 2, -88, 11, "#c8102e", { max: 220 }); box(g, "#8a0a20", w / 2 - 48, -72, 96, 72); glass(g, w / 2 - 44, -68, 43, 68); glass(g, w / 2 + 1, -68, 43, 68);
      for (const x of [16, w - 76]) { box(g, "#c8102e", x - 2, -76, 64, 8, 2); for (let i = 0; i < 3; i++) box(g, ["#2f8a4a", "#e0303a", "#ff6a0b"][i], x + i * 20, -40, 18, 12, 3); box(g, "#7a5a4a", x, -28, 60, 28); } } },   // produce stands
  ];
  // Made-up taquerías (each name was web-searched with "San Antonio" before shipping; no real business uses it).
  const TAQS = [
    { id: "tia", name: "Tacos La Tía Metiche", tagline: "Barbacoa · Chisme gratis", colors: ["#FF1A7F", "#FFFFFF", "#14b8b0"], wall: "#14b8b0" },
    { id: "metichon", name: "Taquería El Metichón", tagline: "Al pastor · Since forever", colors: ["#7a3fd1", "#FFFFFF", "#ff6a0b"], wall: "#e8a0a8" },
    { id: "domingo", name: "Barbacoa El Domingo Sagrado", tagline: "Sundays only · Bring a cooler", colors: ["#000000", "#FFFFFF", "#FF1A7F"], wall: "#c98c72" },
  ];
  function drawTaq(g, w, s, season) {
    face(g, 6, -110, w - 12, 110, s.wall); rim(g, 6, -110, w - 12, 110); box(g, s.colors[0], 6, -114, w - 12, 6); box(g, s.colors[0], 6, -8, w - 12, 8);
    H.signBoard(g, 14, -168, w - 28, 50, s); box(g, "#2a2230", 22, -88, 92, 52); H.glowWin(g, 26, -84, 84, 44);
    H.awning(g, 18, -96, 100, 12, s.colors[0], "#ffffff"); box(g, "#1a1222", w - 74, -80, 46, 80);
    box(g, "#111", w - 76, -104, 50, 18, 3); txt(g, "OPEN", w - 51, -95, 9, "#ff3355", { max: 44 }); H.drawGlow(g, w - 51, -95, 22, "#ff3355", 0.3);
    if (season) { H.papelPicado(g, 6, w - 6, -126); H.marigolds(g, 12, 0, 4); }
  }

  // ---- the lot sequence: a landmark, then a store / taquería / a neighborhood filler, then the next landmark… (want: an id or kind, for the debug hook)
  const FILL = ["store", "house", "taq", "mural", "store", "taq", "vacant", "house", "taq"], WIDE = { house: 206, mural: 236, vacant: 110 };
  function lmLot(M) { return { kind: "landmark", id: M.id, tag: M.name, w: M.w, top: M.top + 10, tagY: M.tagY, gap: 14, crowd: M.w > 200 ? 2 : 1, pole: false, draw(g, L, season, h) { H = h; M.draw(g, M.w); if (season && M.id === "alamo") H.marigolds(g, 30, 0, 6); } }; }
  function storeLot(S) { return { kind: "store", id: S.id, w: S.w, top: S.top + 10, gap: 12, crowd: 3, draw(g, L, season, h) { H = h; S.draw(g, S.w); if (season) H.marigolds(g, 8, 0, 4); } }; }
  function taqLot(T) { return { kind: "taco", id: T.id, sign: T, w: 214, top: 190, gap: 8, crowd: 3, draw(g, L, season, h) { H = h; drawTaq(g, 214, T, season); } }; }
  const seq = { lm: 0, st: 0, tq: 0, f: 0 };
  function lot(i, rand, want) {
    if (i === 0) { seq.lm = seq.st = seq.tq = seq.f = 0; }
    if (partyNear && i > 0) return partyLot();   // the party's block (drawn by the party scene)
    if (want) { const M = LANDMARKS.find((q) => q.id === want); if (M) return lmLot(M); const S = STORES.find((q) => q.id === want); if (S) return storeLot(S); const T = TAQS.find((q) => q.id === want); if (T) return taqLot(T);
      if (WIDE[want]) return { kind: want, w: WIDE[want], crowd: 1 }; }
    if (i % 2 === 0) return lmLot(LANDMARKS[seq.lm++ % LANDMARKS.length]);
    const k = FILL[seq.f++ % FILL.length];
    if (k === "store") return storeLot(STORES[seq.st++ % STORES.length]);
    if (k === "taq") return taqLot(TAQS[seq.tq++ % TAQS.length]);
    return { kind: k, w: WIDE[k], crowd: k === "vacant" ? 0 : 1 };
  }

  // ---- the sky (a sunset like the key art: deep blue → purple → hot pink → orange; no yellow), the downtown skyline, the oaks
  const back = {
    sky(x, W, Hh, h) { H = h;
      x.fillStyle = H.lg(x, 0, 0, 0, Hh, [[0, "#141d5a"], [0.28, "#33287a"], [0.52, "#7a2a86"], [0.72, "#d23a78"], [0.88, "#ff5a6a"], [1, "#ff8a50"]]); x.fillRect(0, 0, W, Hh);
      const r = H.rng(41); for (let i = 0; i < 60; i++) { const y = r() * Hh * 0.45; x.fillStyle = `rgba(255,255,255,${0.2 + r() * 0.6 * (1 - y / (Hh * 0.45))})`; x.fillRect(r() * W, y, 1.3, 1.3); }
      const sx = W * 0.72, sy = Hh - 150, sr = 64; x.fillStyle = H.rg(x, sx, sy, 0, sr * 2.8, [[0, "rgba(255,120,140,.5)"], [1, "rgba(255,90,120,0)"]]); x.fillRect(0, 0, W, Hh);
      x.save(); x.beginPath(); x.arc(sx, sy, sr, 0, TAU); x.clip(); x.fillStyle = H.lg(x, 0, sy - sr, 0, sy + sr, [[0, "#ff9ab0"], [0.55, "#ff6a7a"], [1, "#ff5a3a"]]); x.fillRect(sx - sr, sy - sr, sr * 2, sr * 2);
      x.fillStyle = "#d23a78"; for (let k = 0; k < 6; k++) x.fillRect(sx - sr, sy + 6 + k * 10, sr * 2, 2 + k * 0.9); x.restore();
      for (let k = 0; k < 7; k++) { const cy = Hh * (0.3 + r() * 0.5), cx = r() * W, cw = 60 + r() * 140; x.fillStyle = `rgba(255,${120 + (r() * 40) | 0},${150 + (r() * 30) | 0},${0.12 + r() * 0.16})`; H.rr(x, cx, cy, cw, 4 + r() * 4, 4); x.fill(); } },
    skyline(x, h) { H = h; const base = 260, ink = "#2b1f52", ink2 = "#3a2a66";
      const tw = (cx, top, w, fn) => { x.fillStyle = ink; x.fillRect(cx - w / 2, base - top, w, top); if (fn) fn(cx, top, w); const r = H.rng(cx | 0); x.fillStyle = "rgba(255,158,196,.7)"; for (let y = base - top + 8; y < base - 8; y += 9) for (let xx = cx - w / 2 + 4; xx < cx + w / 2 - 4; xx += 7) if (r() < 0.35) x.fillRect(xx, y, 2.4, 3.2); };
      for (let i = 0; i < 1000; i += 46) { x.fillStyle = ink2; x.fillRect(i, base - 40 - ((i * 7) % 30), 40, 70); }
      tw(120, 170, 40, (cx, top) => { x.fillStyle = ink; x.beginPath(); x.moveTo(cx - 20, base - top); x.lineTo(cx, base - top - 34); x.lineTo(cx + 20, base - top); x.fill(); });   // a pyramid-top tower (Tower Life)
      tw(210, 190, 46, (cx, top) => { x.fillStyle = ink; x.beginPath(); x.moveTo(cx - 23, base - top); x.quadraticCurveTo(cx, base - top - 40, cx + 23, base - top - 10); x.lineTo(cx + 23, base - top); x.fill(); });   // the curved-top bank tower
      tw(290, 150, 54); tw(350, 200, 36, (cx, top) => { x.fillStyle = ink; x.fillRect(cx - 12, base - top - 14, 24, 14); x.fillRect(cx - 5, base - top - 24, 10, 10); });   // a stepped crown
      tw(430, 130, 64); tw(520, 170, 42, (cx, top) => { x.fillStyle = "#ff3355"; x.fillRect(cx - 1, base - top - 12, 2, 2); x.fillStyle = ink; x.fillRect(cx - 1, base - top - 10, 2, 10); });
      // the Tower of the Americas, far away
      x.fillStyle = ink; x.beginPath(); x.moveTo(640, base); x.lineTo(645, base - 215); x.lineTo(651, base - 215); x.lineTo(656, base); x.fill(); x.fillRect(632, base - 234, 32, 18); x.fillStyle = "rgba(255,158,196,.9)"; x.fillRect(634, base - 228, 28, 4); x.fillStyle = ink; x.fillRect(647, base - 252, 2, 18);
      tw(740, 120, 50); tw(820, 160, 38); tw(900, 110, 60); },
    mid(x, h) { H = h; const base = 170;
      for (let i = -20; i < 1020; i += 34) { x.fillStyle = i % 68 ? "#22183c" : "#271c44"; x.beginPath(); x.arc(i, base - 34 - ((i * 13) % 18), 26 + ((i * 7) % 10), 0, TAU); x.fill(); }   // live oaks
      x.fillStyle = "#22183c"; x.fillRect(0, base - 30, 1000, 30);
      for (const px of [150, 470, 820]) { x.strokeStyle = "#22183c"; x.lineWidth = 4; x.beginPath(); x.moveTo(px, base); x.quadraticCurveTo(px + 8, base - 70, px + 3, base - 130); x.stroke(); for (let k = 0; k < 7; k++) { const a = -3.1 + k * 0.5; x.lineWidth = 3; x.beginPath(); x.moveTo(px + 3, base - 130); x.quadraticCurveTo(px + 3 + Math.cos(a) * 16, base - 136 + Math.sin(a) * 10, px + 3 + Math.cos(a) * 28, base - 126 + Math.sin(a) * 14 + 8); x.stroke(); } } },
  };

  // ---- billboards: Chisme's own App Store goal (it's a real donation, so it's hidden in the store app, where the house ad takes the slot)
  const goal = () => root.__chismeGoal || {};
  const DONATE = { name: "Help get Chisme on the App Store", tagline: "Buy Me a Coffee", colors: ["#000000", "#FFFFFF", "#FF1A7F"], slot: "billboard", sponsor: false, donate: true,
    draw(g, bw, bh) { const amt = goal().amount || 99;
      g.fillStyle = H.lg(g, 0, 0, bw, bh, [[0, "#1a0b2a"], [1, "#3a0f3a"]]); g.fillRect(3, 3, bw - 6, bh - 6);
      txt(g, "Help get Chisme", bw / 2 + 18, bh * 0.2, 17, "#ffffff", { font: H.FONT, max: bw - 64 }); txt(g, "on the App Store", bw / 2 + 18, bh * 0.41, 14, "#14b8b0", { font: H.FONT, max: bw - 64 });
      const cx = 26, cy = bh * 0.34; box(g, "#ffffff", cx - 12, cy - 8, 22, 22, 4); g.strokeStyle = "#ffffff"; g.lineWidth = 3; g.beginPath(); g.arc(cx + 12, cy + 3, 5, -1.4, 1.4); g.stroke(); box(g, "#6a2a1a", cx - 10, cy - 6, 18, 4, 2);
      g.strokeStyle = "rgba(255,255,255,.7)"; g.lineWidth = 1.4; for (const dx of [-5, 1]) { g.beginPath(); g.moveTo(cx + dx, cy - 12); g.quadraticCurveTo(cx + dx + 4, cy - 17, cx + dx, cy - 22); g.stroke(); }   // a coffee cup, steaming
      const pill = "$" + amt + " goal"; g.font = `900 13px ${H.FONT}`; const pw = g.measureText(pill).width + 20; box(g, "#FF1A7F", bw / 2 - pw / 2, bh * 0.56, pw, 22, 11); txt(g, pill, bw / 2, bh * 0.56 + 11.5, 13, "#ffffff", { font: H.FONT });
      txt(g, "Buy Me a Coffee · pause to chip in", bw / 2, bh * 0.88, 9, "#ffffff", { max: bw - 20 }); } };
  function billboards(native) {
    const own = LIB.SIGNS.filter((q) => !q.house && q.slot === "billboard"), house = LIB.SIGNS.find((q) => q.house), out = [];
    for (let i = 0; i < own.length; i += 2) out.push(native ? house : DONATE, own[i], own[i + 1] || own[0]);
    return out;
  }

  // ---- TRAFFIC to hop: data-driven. w/h = the hop box; speed = how fast it rolls your way (capped by the game so a full hop always clears);
  // weight/min = how often / from what difficulty; pts = points per clear; talk/honk = chances when you get close; lines = the comic bubbles.
  // No guns, no violence, no department logos: the cops just flash red + blue and get flustered.
  const TRAFFIC = [
    { id: "cop", name: "City patrol car", body: "sedan", w: 150, h: 46, weight: 3, min: 0, speed: [30, 110], pts: 120, cop: true, talk: 0.75, honk: 0.15, horn: 2, mouthY: 58,
      paint: { top: "#f1eef6", low: "#16141c", door: "#f1eef6" }, word: "POLICE", lights: true,
      lines: { near: ["Nice hydraulics, sir.", "Is that… legal?", "Pull over! …never mind.", "License and… wow."], over: ["I'll allow it.", "Did he just…?", "Respect.", "¡Órale!"], hit: ["Ay, the paperwork.", "My bumper!"] } },
    { id: "trooper", name: "State trooper", body: "sedan", w: 156, h: 46, weight: 2, min: 0.1, speed: [40, 140], pts: 140, cop: true, talk: 0.75, honk: 0.1, horn: 2, mouthY: 58,
      paint: { top: "#3a4a6e", low: "#2a3550", door: "#c9c3d6" }, word: "STATE TROOPER", lights: true, hat: "campaign",
      lines: { near: ["Howdy. Nice ride.", "Easy on the bounce.", "Ma'am, I mean, sir."], over: ["Well, I'll be.", "Yeehaw, son.", "That's a first."], hit: ["Dadgum!", "Well, shoot."] } },
    { id: "fbi", name: "Black FBI SUV", body: "suv", w: 170, h: 60, weight: 1.4, min: 0.2, speed: [20, 90], pts: 180, cop: true, talk: 0.8, honk: 0.05, horn: 2, mouthY: 72,
      paint: { top: "#14121a", low: "#0a090e", door: "#14121a" }, word: "FBI", lights: true, shades: true,
      lines: { near: ["We're watching… the bounce.", "Suspect is… stylish.", "Copy that. Nice paint."], over: ["Add it to the file.", "He's good.", "Abort. He's too smooth."], hit: ["That's going in the report."] } },
    { id: "construction", name: "Construction truck", body: "truck", w: 200, h: 56, weight: 2, min: 0, speed: [0, 60], pts: 130, talk: 0.7, honk: 0.4, horn: 3, mouthY: 70,
      paint: { top: "#ff6a0b", low: "#e9e3ee", door: "#ff6a0b" }, word: "ROAD WORK", wordCol: "#c2410c", cones: true,
      lines: { near: ["Slow down, mijo!", "Road work ahead… eventually.", "¡Cuidado con los conos!"], over: ["¡Ándale!", "Nice clearance!", "Over the cones!"], hit: ["My cones!", "¡Ay, no!"] } },
    { id: "beater", name: "The Beater Sedan", body: "sedan", w: 150, h: 46, weight: 2.2, min: 0, speed: [60, 160], pts: 110, talk: 0.95, honk: 0.85, horn: 3, scream: true, mouthY: 70,
      paint: { top: "#5e7f86", low: "#4a666c", door: "#a8968e" }, dents: true, lady: true,
      lines: { near: ["¡MUÉVETE!", "AYYY!", "¡Quítate, menso!", "¡¿Qué haces?!"], over: ["AYYY!", "¡¿EN SERIO?!", "¡Ay, Diosito!"], hit: ["¡MI CARRO!", "AYYY!"] } },
    { id: "cuh", name: "Cuh", body: "coupe", w: 146, h: 40, weight: 2, min: 0, speed: [40, 130], pts: 100, talk: 0.95, honk: 0, mouthY: 56,
      paint: { top: "#6e2a3a", low: "#4e1e2a", door: "#6e2a3a" }, dents: true, bowl: true,
      lines: { near: ["Cuh."], over: ["Cuh.", "…cuh."], hit: ["Cuh!"] } },
    { id: "troca", name: "Old two-tone troca", body: "pickup", w: 170, h: 50, weight: 1.6, min: 0, speed: [20, 100], pts: 110, talk: 0.7, honk: 0.5, horn: 1, mouthY: 64,
      paint: { top: "#e9e3ee", low: "#2f6b8a", door: "#2f6b8a" },
      lines: { near: ["¡Órale, compa!", "¡Qué bonito!", "Back in my day…"], over: ["¡Eso!", "¡Ajúa!", "Puro estilo."], hit: ["¡Mi troca!"] } },
  ];
  // where the driver's mouth is, from the (mirrored) drawing's left edge: the comic bubbles come from there
  for (const T of TRAFFIC) T.mouth = T.lady ? T.w * 0.26 : T.body === "truck" ? 34 : T.body === "pickup" ? 48 : T.w * 0.34;
  const SKIN = ["#f1c7a8", "#d9a07a", "#b97c55", "#8a5a3c", "#5e3a26"], HAIR = ["#1a1414", "#3a2420", "#6a3a2a", "#8a8a96"];
  function driver(rand) { return { skin: SKIN[(rand() * SKIN.length) | 0], hair: HAIR[(rand() * HAIR.length) | 0], cap: rand() < 0.35 ? ["#14b8b0", "#FF1A7F", "#2a2a2a", "#e9e3ee"][(rand() * 4) | 0] : null, shades: rand() < 0.4, mood: rand() } }
  function trafficRate(d) { return 0.42 + d * 0.25; }

  function wheel(g, x, y, r, spin) { g.fillStyle = "#121014"; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); g.fillStyle = "#8a8496"; g.beginPath(); g.arc(x, y, r * 0.52, 0, TAU); g.fill(); g.strokeStyle = "#4a4458"; g.lineWidth = 1.2; for (let k = 0; k < 3; k++) { const a = spin + k * 2.09; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * r * 0.5, y + Math.sin(a) * r * 0.5); g.stroke(); } }
  function head(g, x, y, d, T, t, reduced) {   // the driver in the window, facing right
    const nod = T.bowl && !reduced ? Math.max(0, Math.sin(t * 6)) * 2 : 0; g.save(); g.translate(x, y + nod);
    g.fillStyle = d.skin; g.beginPath(); g.arc(0, 0, 6.5, 0, TAU); g.fill();
    if (T.bowl) { g.fillStyle = "#1a1414"; g.beginPath(); g.arc(0, -1, 7.4, PI, TAU); g.fill(); g.fillRect(-7.4, -1.5, 14.8, 3.2); }   // the bowl cut
    else if (T.hat === "campaign") { g.fillStyle = "#6a4a3a"; g.beginPath(); g.ellipse(0, -5, 11, 2.4, 0, 0, TAU); g.fill(); poly(g, "#6a4a3a", [-5, -5, -3, -13, 0, -11, 3, -13, 5, -5]); }
    else if (d.cap) { g.fillStyle = d.cap; g.beginPath(); g.arc(0, -1.5, 6.8, PI, TAU); g.fill(); g.fillRect(0, -2.6, 10, 2); }
    else { g.fillStyle = d.hair; g.beginPath(); g.arc(-0.5, -1.5, 6.8, PI * 0.95, TAU * 1.01); g.fill(); }
    if (T.shades || d.shades) { box(g, "#050505", 1, -2, 6.4, 2.4, 1); if (T.id === "fbi") { g.strokeStyle = "#c9c3d6"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(-5, 1); g.quadraticCurveTo(-7, 6, -4, 8); g.stroke(); } }
    else { box(g, "#1a1414", 3, -1.6, 1.4, 1.6); }
    if (T.bowl) { box(g, "#3a1a1a", 3, 3, 3.4, 0.9); } else { g.fillStyle = "#3a0d16"; g.beginPath(); g.ellipse(4.2, 3.2, 1.3, 0.9, 0, 0, TAU); g.fill(); }
    g.restore();
  }
  function lady(g, x, y, t, reduced, loud) {   // the Beater's passenger, leaning out the window, hair in curlers, mid-scream
    const lean = reduced ? 0 : Math.sin(t * 9) * 1.5; g.save(); g.translate(x, y); g.rotate(-0.25 + lean * 0.03);
    box(g, "#c8102e", -5, 0, 12, 14, 4); g.fillStyle = "#d9a07a"; g.beginPath(); g.arc(2, -6, 7, 0, TAU); g.fill();
    g.fillStyle = "#2a1414"; g.beginPath(); g.arc(1, -9, 7.5, PI, TAU); g.fill(); for (const [cx, cy, c] of [[-4, -15, C.pink], [2, -17, C.turq], [8, -14, C.pink]]) { g.fillStyle = c; g.beginPath(); g.arc(cx, cy, 2.6, 0, TAU); g.fill(); }
    g.fillStyle = "#3a0d16"; g.beginPath(); g.ellipse(6.4, -3.4, 2.4, loud ? 3 : 1.6, 0, 0, TAU); g.fill(); box(g, "#1a1414", 5, -9, 1.6, 1.8);
    g.strokeStyle = "#d9a07a"; g.lineWidth = 3; g.lineCap = "round"; g.beginPath(); g.moveTo(4, 4); g.lineTo(14, -6 + lean); g.stroke(); g.restore();   // a waving arm
  }
  let partyLights = false;   // at the Hon Dipo party the light bars cycle the party colors
  function lightBar(g, x, y, w, t, reduced) { const on = reduced ? 0 : Math.floor(t * 7) % 2, P = partyLights ? PARTY_COL : null, k = Math.floor(t * 4);
    const a = P ? P[k % 4] : on ? "#ff2a3a" : "#7a1420", b = P ? P[(k + 2) % 4] : on ? "#1f3a93" : "#2f6bff";
    box(g, "#2a2a32", x, y + 4, w, 3); box(g, a, x, y, w / 2 - 1, 5, 2); box(g, b, x + w / 2 + 1, y, w / 2 - 1, 5, 2);
    if (!reduced) { H.drawGlow(g, on ? x + w / 4 : x + w * 0.75, y + 2, 28, P ? (on ? a : b) : on ? "#ff2a3a" : "#2f6bff", 0.55); } }
  function drawTraffic(g, o, sx, GY, t, reduced, h) {
    H = h; const T = o.T, P = T.paint, w = T.w, d = o.driver || { skin: SKIN[1], hair: HAIR[0] }, wob = reduced ? 0 : Math.sin(t * 3.1 + o.wob) * 1.2, shake = o.hit && !reduced ? Math.sin(t * 40) * 1.5 : 0;
    // drawn facing right, then mirrored: it's oncoming (the words on the doors are drawn after, unmirrored); o.same: going your way (the chase)
    const x0 = sx - (o.dx || 0); g.save(); g.translate(x0 + (o.same ? 0 : w) + shake, GY - 9 + wob * 0.4); if (!o.same) g.scale(-1, 1); g.rotate(reduced ? 0 : Math.sin(t * 2.3 + o.wob) * 0.012);
    g.fillStyle = "rgba(0,0,0,.35)"; g.beginPath(); g.ellipse(w / 2, 9, w * 0.52, 4, 0, 0, TAU); g.fill();
    const tall = T.body === "suv" ? 16 : T.body === "truck" ? 18 : T.body === "coupe" ? -4 : 0, low = 22 + (T.body === "suv" ? 6 : 0) - (T.body === "coupe" ? 4 : 0), roofY = -low - 22 - tall;
    // lower body
    g.fillStyle = H.lg(g, 0, -low, 0, 0, [[0, H.shade(P.low, 0.15)], [1, H.shade(P.low, -0.2)]]); H.rr(g, 0, -low, w, low, 7); g.fill();
    if (T.body === "truck") {   // a cab up front, a flatbed of cones behind
      box(g, H.lg(g, 0, roofY, 0, -low, [[0, H.shade(P.top, 0.1)], [1, H.shade(P.top, -0.15)]]), w - 66, roofY, 56, -low - roofY, 6); box(g, "#3a4f6e", w - 56, roofY + 6, 36, 18, 3);
      head(g, w - 34, roofY + 16, d, T, t, reduced); box(g, "#ff6a0b", 0, -low - 6, w - 70, 6); for (let x = 6; x < w - 76; x += 22) box(g, x % 44 < 22 ? "#ff6a0b" : "#ffffff", x, -low + 4, 11, 8);
      for (let k = 0; k < 4; k++) { const cx = 14 + k * 30; poly(g, "#ff6a0b", [cx - 7, -low - 6, cx - 2, -low - 30, cx + 2, -low - 30, cx + 7, -low - 6]); box(g, "#ffffff", cx - 4.5, -low - 20, 9, 4); }
      box(g, "#ff6a0b", w - 46, roofY - 6, 14, 6, 3); if (!reduced && Math.floor(t * 5) % 2) H.drawGlow(g, w - 39, roofY - 3, 22, "#ff6a0b", 0.6);
    } else if (T.body === "pickup") {
      box(g, H.lg(g, 0, roofY, 0, -low, [[0, H.shade(P.top, 0.1)], [1, H.shade(P.top, -0.15)]]), w - 80, roofY, 50, -low - roofY, 8); box(g, "#3a4f6e", w - 72, roofY + 5, 36, 17, 4); head(g, w - 48, roofY + 15, d, T, t, reduced);
      box(g, P.top, 4, -low - 8, w - 86, 8, 2); box(g, "#e9e3ee", 4, -low + 6, w - 8, 4);
    } else {
      g.fillStyle = H.lg(g, 0, roofY, 0, -low, [[0, H.shade(P.top, 0.12)], [1, H.shade(P.top, -0.12)]]); g.beginPath(); g.moveTo(w * 0.2, -low); g.lineTo(w * 0.3, roofY); g.lineTo(w * 0.72, roofY); g.lineTo(w * 0.84, -low); g.fill();
      box(g, "#3a4f6e", w * 0.33, roofY + 4, w * 0.18, -low - roofY - 6, 2); box(g, "#3a4f6e", w * 0.54, roofY + 4, w * 0.2, -low - roofY - 6, 2); head(g, w * 0.66, roofY + 14, d, T, t, reduced);
      if (T.body !== "coupe") box(g, P.door, w * 0.3, -low + 2, w * 0.44, low - 8, 3);   // the doors (the Beater's are mismatched primer)
      if (T.lady) lady(g, w * 0.74, roofY + 4, t, reduced, Math.floor(t * 4) % 2 === 0);
    }
    if (T.lights) { if (T.body === "suv") { const on = reduced ? 0 : Math.floor(t * 8) % 2; box(g, on ? "#ff2a3a" : "#2f6bff", w - 8, -low + 4, 6, 4, 1); box(g, on ? "#2f6bff" : "#ff2a3a", w - 8, -low + 10, 6, 4, 1); if (!reduced) H.drawGlow(g, w - 5, -low + 8, 24, on ? "#ff2a3a" : "#2f6bff", 0.5); } else lightBar(g, w * 0.4, roofY - 6, w * 0.24, t, reduced); }
    if (T.dents) { g.strokeStyle = "rgba(0,0,0,.4)"; g.lineWidth = 1.2; for (const [x, y] of [[w * 0.16, -14], [w * 0.8, -10], [w * 0.5, -18]]) { g.beginPath(); g.arc(x, y, 5, 0.3, 2.6); g.stroke(); } box(g, "#8a4a3a", w * 0.08, -low + 6, 8, 5, 2); }
    box(g, "#ff3355", 1, -low + 5, 5, 6, 2); box(g, "#f1eef6", w - 6, -low + 5, 5, 6, 2);   // tail light (back), head light (front)
    const spin = reduced ? 0 : -t * 8; wheel(g, w * 0.2, 0, 10, spin); wheel(g, w * 0.82, 0, 10, spin);
    g.restore();
    if (T.word) { g.save(); g.translate(x0 + shake, GY - 9 + wob * 0.4); g.textAlign = "center"; g.textBaseline = "middle"; H.fitText(g, T.word, w * 0.4, T.word.length > 6 ? 8 : 11, "900", H.SANS);
      const cx = o.same ? w * 0.51 : T.body === "truck" ? w * 0.36 : w * 0.49, cy = T.body === "truck" ? -low + 10 : -low + 9;
      if (T.id === "cop") box(g, P.top, cx - w * 0.21, cy - 6, w * 0.42, 11, 2); g.fillStyle = T.wordCol || (T.id === "cop" ? "#16141c" : "#ffffff"); g.fillText(T.word, cx, cy); g.restore(); }
  }

  // ---- PICKS: gas = more tank; the refresco (a plain straight-sided glass bottle, our own label) = Feria; tacos = points + a combo step
  const PICKS = { gas: { fuel: 0.4, pts: 50, text: "+GAS", col: "#14b8b0" }, soda: { feria: 3, pts: 60, text: "+3 FERIA · ¡REFRESCO!", col: "#FF1A7F" }, taco: { pts: 150, streak: 1, text: "+TACO", col: "#ff6a0b" } };
  const FUEL = { range: 430, first: 2600, gasEvery: [4200, 6200] };   // meters per full tank; world units to the first can; then a can every…
  function drawPick(g, kind, x, y, t, h) {
    H = h; const bob = Math.sin(t * 3) * 2; g.save(); g.translate(x, y + bob); H.drawGlow(g, 0, 0, 24, kind === "gas" ? "#14b8b0" : kind === "soda" ? "#FF1A7F" : "#ff6a0b", 0.35);
    if (kind === "gas") { box(g, "#000", -10, -12, 21, 25, 4); box(g, "#d8322a", -9, -11, 19, 23, 3); box(g, "#a8202a", -9, -11, 19, 4, 2); box(g, "#3a3150", 3, -16, 4, 6, 1); box(g, "#3a3150", -7, -15, 8, 3, 1); txt(g, "GAS", 0.5, 3, 7.5, "#ffffff", { max: 16 }); }
    else if (kind === "soda") { g.scale(1.3, 1.3); g.fillStyle = "rgba(220,240,235,.55)"; g.strokeStyle = "#000"; g.lineWidth = 1.4; H.rr(g, -5.5, -12, 11, 24, 2.5); g.fill(); g.stroke(); box(g, "#5a1e10", -4.4, -6, 8.8, 17, 2); box(g, "rgba(220,240,235,.6)", -2.4, -21, 4.8, 9); g.strokeRect(-2.4, -21, 4.8, 9); box(g, "#c9c3d6", -3, -23, 6, 3, 1);
      box(g, "#e0303a", -5.5, -2, 11, 7); txt(g, "VIDRIO", 0, 1.6, 4.2, "#ffffff", { max: 10 }); box(g, "rgba(255,255,255,.55)", -4, -10, 1.4, 18); }
    else { g.fillStyle = "#000"; g.beginPath(); g.arc(0, 4, 13, PI, TAU); g.fill(); g.fillStyle = "#d9a679"; g.beginPath(); g.arc(0, 4, 11.5, PI, TAU); g.fill(); g.fillStyle = "#2f8a4a"; g.beginPath(); g.arc(0, 3, 9, PI * 1.05, TAU * 0.975); g.fill();
      g.fillStyle = "#7a3a1e"; g.beginPath(); g.arc(0, 4, 7, PI, TAU); g.fill(); for (const dx of [-5, 0, 5]) { g.fillStyle = "#e0303a"; g.beginPath(); g.arc(dx, -2, 1.6, 0, TAU); g.fill(); } box(g, "#000", -13, 3, 26, 2); }
    g.restore();
  }

  // ---- the Trail Ride: 10 horses (no two coats alike), each with a cowboy (hat + shirt). They cross at the crosswalk; the car always stops.
  const COATS = [
    { id: "bay", coat: "#7a3e22", mane: "#1a1414", legs: "#1a1414" }, { id: "black", coat: "#1c1a22", mane: "#0a090e", legs: "#0a090e" },
    { id: "white", coat: "#ecebf0", mane: "#d6d3dc", legs: "#ecebf0" }, { id: "palomino", coat: "#c8a080", mane: "#efe9ee", legs: "#c8a080" },   // palomino-ish: tan with a cream mane (no yellow)
    { id: "paint", coat: "#efe9ee", mane: "#3a2420", legs: "#efe9ee", spots: "#8a4a2e", big: true }, { id: "appaloosa", coat: "#e3dde6", mane: "#3a3150", legs: "#5a5068", spots: "#3a2a40", rump: true },
    { id: "chestnut", coat: "#a0482a", mane: "#7a3420", legs: "#a0482a" }, { id: "grey", coat: "#9a9aa6", mane: "#5a5a66", legs: "#7a7a86", dapple: true },
    { id: "buckskin", coat: "#b88a62", mane: "#1a1414", legs: "#1a1414" }, { id: "roan", coat: "#8e6e72", mane: "#3a2a2e", legs: "#3a2a2e", flecks: true },
  ];
  const HATS = [["#f1eef6", "white felt"], ["#1a1414", "black felt"], ["#7a4a2e", "brown felt"], ["#cfc6ba", "palm straw"], ["#8a8a96", "silver belly"], ["#5a3424", "chocolate"], ["#e9e3ee", "white straw"], ["#2a2230", "charcoal"], ["#a86a4e", "tan suede"], ["#3a4a6e", "navy"]];
  const SHIRTS = ["#FF1A7F", "#14b8b0", "#e0303a", "#7a3fd1", "#f1eef6", "#ff6a0b", "#2f6bd6", "#2f8a4a", "#1a1414", "#ff9cc2"];
  function riders(n, rand) {
    const hats = HATS.slice().sort(() => rand() - 0.5), shirts = SHIRTS.slice().sort(() => rand() - 0.5);
    return COATS.slice(0, n).map((c, i) => ({ ...c, hat: hats[i % hats.length][0], hatName: hats[i % hats.length][1], shirt: shirts[i % shirts.length], plaid: rand() < 0.4, skin: SKIN[(rand() * SKIN.length) | 0], ph: rand() * 6 }));
  }
  function horse(g, r, x, y, s, t, reduced, h) {   // side view facing right; feet at y
    H = h; const ph = reduced ? 0 : t * 7 + r.ph, bob = reduced ? 0 : Math.abs(Math.sin(ph)) * 1.4;
    g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = "rgba(0,0,0,.3)"; g.beginPath(); g.ellipse(0, 0, 30, 4, 0, 0, TAU); g.fill(); g.translate(0, -bob);
    g.lineCap = "round";
    const leg = (lx, a, col) => { g.strokeStyle = col; g.lineWidth = 4.6; g.beginPath(); g.moveTo(lx, -30); g.lineTo(lx + Math.sin(a) * 6, -14); g.lineTo(lx + Math.sin(a) * 8, -1); g.stroke(); box(g, "#1a1414", lx + Math.sin(a) * 8 - 3, -3, 6, 3, 1); };
    leg(-18, Math.sin(ph + 1.6), H.shade(r.legs, -0.2)); leg(16, Math.sin(ph + 3.1), H.shade(r.legs, -0.2));
    g.fillStyle = r.coat; g.beginPath(); g.ellipse(0, -36, 27, 12, 0, 0, TAU); g.fill();   // the barrel
    g.save(); g.clip(); if (r.spots) { const q = H.rng(7); g.fillStyle = r.spots; for (let i = 0; i < (r.big ? 4 : 14); i++) { const sx = r.rump ? -22 + q() * 20 : -20 + q() * 40, sy = -44 + q() * 16; g.beginPath(); g.ellipse(sx, sy, r.big ? 9 + q() * 5 : 1.8, r.big ? 6 + q() * 4 : 1.8, q(), 0, TAU); g.fill(); } }
      if (r.dapple) { g.fillStyle = "rgba(255,255,255,.25)"; const q = H.rng(9); for (let i = 0; i < 12; i++) { g.beginPath(); g.arc(-20 + q() * 40, -44 + q() * 14, 2.6, 0, TAU); g.fill(); } }
      if (r.flecks) { g.fillStyle = "rgba(255,255,255,.35)"; const q = H.rng(11); for (let i = 0; i < 50; i++) g.fillRect(-26 + q() * 52, -48 + q() * 24, 1, 1); }
    g.restore();
    leg(-12, Math.sin(ph), r.legs); leg(21, Math.sin(ph + 1.6 + 3.1), r.legs);
    g.fillStyle = r.coat; g.beginPath(); g.moveTo(18, -44); g.quadraticCurveTo(28, -62, 34, -66); g.lineTo(44, -58); g.quadraticCurveTo(46, -54, 42, -52); g.lineTo(32, -54); g.quadraticCurveTo(28, -40, 22, -30); g.fill();   // neck + head
    g.fillStyle = r.mane; g.beginPath(); g.moveTo(18, -46); g.quadraticCurveTo(26, -62, 32, -68); g.lineTo(30, -62); g.quadraticCurveTo(24, -50, 20, -40); g.fill(); poly(g, r.coat, [31, -66, 33, -73, 36, -66]);
    g.strokeStyle = r.mane; g.lineWidth = 4; g.beginPath(); g.moveTo(-26, -40); g.quadraticCurveTo(-36, -30 + (reduced ? 0 : Math.sin(ph) * 2), -32, -16); g.stroke();   // tail
    box(g, "#1a1414", 37, -62, 2, 2); g.strokeStyle = "#3a2420"; g.lineWidth = 1; g.beginPath(); g.moveTo(42, -54); g.lineTo(6, -52); g.stroke();   // eye, reins
    box(g, "#5a3424", -10, -50, 20, 7, 3); box(g, "#3a2420", -4, -42, 3, 14);   // saddle + stirrup strap
    // the cowboy
    g.fillStyle = "#2f4a7a"; H.rr(g, -6, -56, 9, 18, 3); g.fill(); g.strokeStyle = "#2f4a7a"; g.lineWidth = 4; g.beginPath(); g.moveTo(-1, -46); g.lineTo(4, -34); g.stroke(); box(g, "#3a2420", 1, -35, 7, 4, 1);   // jeans + boot
    box(g, r.shirt, -7, -76, 14, 22, 4); if (r.plaid) { g.fillStyle = "rgba(0,0,0,.18)"; for (let k = 0; k < 3; k++) { g.fillRect(-7, -72 + k * 6, 14, 1.6); g.fillRect(-4 + k * 4, -76, 1.6, 22); } }
    g.strokeStyle = r.shirt; g.lineWidth = 3.6; g.beginPath(); g.moveTo(4, -70); g.lineTo(14, -60); g.lineTo(22, -58); g.stroke();
    g.fillStyle = r.skin; g.beginPath(); g.arc(1, -83, 6, 0, TAU); g.fill(); box(g, "#1a1414", 4, -85, 1.4, 1.6);
    g.fillStyle = r.hat; g.beginPath(); g.ellipse(0, -88, 12, 2.6, -0.06, 0, TAU); g.fill(); poly(g, r.hat, [-6, -88, -5, -97, -1, -95, 2, -97, 6, -88]); box(g, "rgba(0,0,0,.35)", -5.6, -90.5, 11.4, 1.6);
    g.restore();
  }


  // ---- the Hon Dipo party (v49.16): the Juan game's Hon Dipo store + its DJ rig (static/juan.js, v49.15), ported as-is so the two
  // games match (same drawing code, its own scope); the cream wall is a touch cooler here (no cream-yellow under the party lights).
  const DJ = (() => {
    const SANS = 'system-ui,-apple-system,"Segoe UI",Roboto,sans-serif';
    const mod = (a, n) => ((a % n) + n) % n;
    function rr(c, x, y, w, h, r) { r = Math.max(0, Math.min(r, w / 2, h / 2)); c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
    function lin(c, x0, y0, x1, y1, cols) { const g = c.createLinearGradient(x0, y0, x1, y1); cols.forEach((col, i) => g.addColorStop(i / Math.max(1, cols.length - 1), col)); return g; }
    function box(c, fill, x, y, w, h, r) { c.fillStyle = fill; if (r) { rr(c, x, y, w, h, r); c.fill(); } else c.fillRect(x, y, w, h); }
    function ell(c, fill, x, y, rx, ry, rot) { c.fillStyle = fill; c.beginPath(); c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), rot || 0, 0, Math.PI * 2); c.fill(); }
    function line(c, col, w, pts, cap) { c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap || "round"; c.lineJoin = "round"; c.beginPath(); c.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) c.lineTo(pts[i], pts[i + 1]); c.stroke(); }
    function poly(c, fill, pts) { c.fillStyle = fill; c.beginPath(); c.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) c.lineTo(pts[i], pts[i + 1]); c.closePath(); c.fill(); }
    function say(c, s, x, y, size, col, o = {}) {
      c.font = `${o.italic ? "italic " : ""}${o.weight || 800} ${size}px ${o.font || SANS}`;
      if (o.fit && o.max) { const w = c.measureText(s).width + (o.stroke ? o.sw || 3 : 0); if (w > o.max) { size = Math.max(12, Math.floor(size * o.max / w)); c.font = `${o.italic ? "italic " : ""}${o.weight || 800} ${size}px ${o.font || SANS}`; } } c.textAlign = o.align || "center"; c.textBaseline = "middle";
      if (o.glow) { c.shadowColor = o.glow; c.shadowBlur = o.blur || 8; }
      if (o.stroke) { c.lineWidth = o.sw || 3; c.strokeStyle = o.stroke; c.lineJoin = "round"; c.strokeText(s, x, y, o.max); }
      c.fillStyle = col; c.fillText(s, x, y, o.max);
      if (o.glow) { c.shadowBlur = 0; c.shadowColor = "transparent"; }
    }
    function glass(c, x, y, w, h, lit) { box(c, lit ? lin(c, 0, y, 0, y + h, ["#ffd9a0", "#ffb46a"]) : lin(c, x, y, x + w, y + h, ["#bfe6f7", "#7fb6d6", "#a9d4ea"]), x, y, w, h); if (!lit) { c.fillStyle = "rgba(255,255,255,.45)"; c.beginPath(); c.moveTo(x + w * 0.15, y + h); c.lineTo(x + w * 0.45, y); c.lineTo(x + w * 0.6, y); c.lineTo(x + w * 0.3, y + h); c.fill(); } }
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
    function djDude(c, x, by, t, rm, part, K) {   // the made-up DJ, facing us: a big, heavyset Southside guy (broad shoulders, a round belly resting on the
      // table), backwards black cap, thick black glasses, black tee, headphones. by = the DJ table's top (about his hips); K = his size (Juan is 1.5)
      const beat = rm ? 0.5 : mod(t * 2, 1), nod = rm ? 0 : Math.sin(beat * Math.PI) * 1.4, sway = rm ? 0 : Math.sin(t * Math.PI) * 0.9;
      const SK = "#a86f47", SK2 = "#8a5634", HAIR = "#1e130c", TEE = "#1d1e23", TEE2 = "#0f1013", INK = "#08080a";
      c.save(); c.translate(x, by); c.scale(K, K);
      if (part === "hand") {   // his left hand (our left) scratching the left deck, in front of the controller
        const sc = rm ? 0 : Math.sin(t * 9) * 2, hx = -10.5 + sc + sway * 0.5, hy = -2.6;
        line(c, SK, 5.6, [-16.5 + sway, -13, hx, hy]); line(c, TEE, 8.4, [-16.6 + sway, -21, -16.4 + sway, -13.4]);
        ell(c, SK, hx, hy, 3.4, 2.8); line(c, "rgba(0,0,0,.18)", 0.6, [hx - 1.6, hy + 0.6, hx + 1.6, hy + 0.6]); c.restore(); return; }
      const sy = nod * 0.4; c.translate(sway, 0);
      c.fillStyle = lin(c, -18, -26, 18, 8, ["#2c2e35", TEE, TEE2]);   // the body: broad shoulders, a big round belly
      c.beginPath(); c.moveTo(-14, -26 + sy); c.lineTo(14, -26 + sy); c.quadraticCurveTo(18.5, -25 + sy, 17.5, -19 + sy);
      c.quadraticCurveTo(22.5, -6 + sy, 16, 7); c.lineTo(-16, 7); c.quadraticCurveTo(-22.5, -6 + sy, -17.5, -19 + sy); c.quadraticCurveTo(-18.5, -25 + sy, -14, -26 + sy); c.closePath(); c.fill();
      c.strokeStyle = "rgba(255,255,255,.09)"; c.lineWidth = 1.2; c.beginPath(); c.arc(0, -3 + sy, 14, -2.7, -0.45); c.stroke();
      c.lineWidth = 1.3; c.lineCap = "round";   // the party lights catch the edges of his shirt (pink on our left, turquoise on our right)
      c.strokeStyle = "rgba(255,26,127,.75)"; c.beginPath(); c.moveTo(-14, -25.6 + sy); c.quadraticCurveTo(-18.2, -24.6 + sy, -17.3, -19 + sy); c.quadraticCurveTo(-21.8, -7 + sy, -18.5, 0); c.stroke();
      c.strokeStyle = "rgba(0,201,205,.8)"; c.beginPath(); c.moveTo(14, -25.6 + sy); c.quadraticCurveTo(18.2, -24.6 + sy, 17.3, -19 + sy); c.quadraticCurveTo(21.8, -7 + sy, 18.5, 0); c.stroke();
      ell(c, "#00C9CD", -7, -16 + sy, 2.6, 2.6); ell(c, TEE, -7, -16 + sy, 1.5, 1.5); ell(c, "#FF1A7F", -7, -16 + sy, 0.55, 0.55);   // a little record print
      box(c, SK2, -5.5, -31 + sy, 11, 7, 3.5);   // the neck
      const hx = 12, hy = -37 + nod;   // his right arm (our right): up, holding the right headphone cup
      line(c, TEE, 8.6, [14.5, -23.5 + sy, 18.5, -16.5 + sy]); line(c, SK, 5.6, [18, -17.5 + sy, 20.5, -26, hx + 2, hy + 1.6]);
      c.save(); c.translate(0, nod);
      const X = 0, Y = -38;
      ell(c, SK2, X - 9.6, Y + 1, 2, 2.8); ell(c, SK2, X + 9.6, Y + 1, 2, 2.8);
      ell(c, lin(c, X - 8, Y - 8, X + 8, Y + 10, ["#c48a5e", SK, SK2]), X, Y, 9.8, 10.2);
      line(c, "rgba(90,50,30,.5)", 0.8, [X - 4.5, Y + 9.6, X, Y + 10.9, X + 4.5, Y + 9.6]);   // a little double chin
      ell(c, SK2, X, Y + 1.4, 1.9, 1.5);
      ell(c, "#1b120c", X - 3.7, Y - 1.4, 1, 1.15); ell(c, "#1b120c", X + 3.7, Y - 1.4, 1, 1.15);
      c.fillStyle = "#3a1d12"; c.beginPath(); c.moveTo(X - 3.8, Y + 5.2); c.quadraticCurveTo(X, Y + 9, X + 3.8, Y + 5.2); c.closePath(); c.fill();   // a big grin
      c.fillStyle = "#ffffff"; c.beginPath(); c.moveTo(X - 3.2, Y + 5.4); c.quadraticCurveTo(X, Y + 6.8, X + 3.2, Y + 5.4); c.closePath(); c.fill();
      c.fillStyle = HAIR; c.beginPath(); c.moveTo(X - 5.8, Y + 5); c.quadraticCurveTo(X - 3.2, Y + 2.3, X, Y + 3.1); c.quadraticCurveTo(X + 3.2, Y + 2.3, X + 5.8, Y + 5);
      c.quadraticCurveTo(X + 2.6, Y + 4.2, X, Y + 4.7); c.quadraticCurveTo(X - 2.6, Y + 4.2, X - 5.8, Y + 5); c.fill();   // a thick mustache
      ell(c, HAIR, X, Y + 9.3, 1.9, 1);   // + a chin-strip
      line(c, HAIR, 1.4, [X - 7.2, Y - 6.6, X - 2.4, Y - 7.2]); line(c, HAIR, 1.4, [X + 2.4, Y - 7.2, X + 7.2, Y - 6.6]);
      // thick black glasses
      c.fillStyle = "rgba(200,230,255,.18)"; rr(c, X - 8.3, Y - 4.8, 6.9, 5.8, 2); c.fill(); rr(c, X + 1.4, Y - 4.8, 6.9, 5.8, 2); c.fill();
      c.strokeStyle = INK; c.lineWidth = 1.6; c.lineJoin = "round"; rr(c, X - 8.3, Y - 4.8, 6.9, 5.8, 2); c.stroke(); rr(c, X + 1.4, Y - 4.8, 6.9, 5.8, 2); c.stroke();
      line(c, INK, 1.4, [X - 1.4, Y - 2.6, X + 1.4, Y - 2.6]); line(c, INK, 1.3, [X - 8.3, Y - 3.4, X - 9.8, Y - 2.6]); line(c, INK, 1.3, [X + 8.3, Y - 3.4, X + 9.8, Y - 2.6]);
      line(c, "rgba(255,255,255,.75)", 0.6, [X - 6.8, Y - 2.4, X - 5.4, Y - 3.8]); line(c, "rgba(255,255,255,.75)", 0.6, [X + 2.9, Y - 2.4, X + 4.3, Y - 3.8]);
      // the cap, on backwards: the flat brim sticks out behind, the crown with the snapback gap over the forehead
      poly(c, INK, [X + 2.5, Y - 9.6, X + 16.5, Y - 12.4, X + 17, Y - 9.6, X + 3.5, Y - 6.6]);
      c.fillStyle = lin(c, X - 9, Y - 16, X + 9, Y - 6, ["#2a2c32", "#141519", INK]); c.beginPath(); c.ellipse(X, Y - 6, 10, 10.2, 0, Math.PI, 0); c.closePath(); c.fill();
      box(c, INK, X - 10, Y - 7.2, 20, 2.4, 1);
      c.fillStyle = HAIR; c.beginPath(); c.ellipse(X, Y - 6, 3.1, 2.7, 0, Math.PI, 0); c.fill(); line(c, "#c9d0d8", 1, [X - 3.1, Y - 6, X + 3.1, Y - 6]);
      ell(c, "#2a2c32", X, Y - 16.1, 1.3, 0.8);
      // the headphones: a silver band over the cap, the cups on his ears
      c.strokeStyle = "#7d848e"; c.lineWidth = 2; c.beginPath(); c.ellipse(X, Y - 3, 11.2, 12.8, 0, Math.PI * 1.06, Math.PI * 1.94); c.stroke();
      c.strokeStyle = "#d5dbe1"; c.lineWidth = 0.7; c.beginPath(); c.ellipse(X, Y - 3, 11.2, 12.8, 0, Math.PI * 1.2, Math.PI * 1.5); c.stroke();
      ell(c, "#17181c", X - 10.8, Y + 1, 3.2, 4.4); ell(c, "#FF1A7F", X - 11.5, Y + 1, 1.2, 2.6);
      ell(c, "#17181c", X + 11.2, Y + 1, 3.2, 4.4); ell(c, "#00C9CD", X + 11.9, Y + 1, 1.2, 2.6);
      c.restore();
      ell(c, SK, hx + 1.8, hy + 1.4, 3.4, 3);   // the hand on the cup
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
    function djPallet(c, x, w, y) {   // a wooden pallet: top at y − 8, bottom at y
      box(c, "#8a6a44", x, y - 1.8, w, 1.8);
      for (const bx of [x + 2, x + w / 2 - 4, x + w - 10]) box(c, "#9c7748", bx, y - 6, 8, 4.4);
      box(c, "#6e5232", x, y - 8, w, 2.4); for (let k = x + 1.5; k < x + w - 4; k += 9) box(c, lin(c, 0, y - 8, 0, y - 5.4, ["#d9b077", "#b98d55"]), k, y - 8, 7.4, 2.6, 0.6);
    }
    function djTripod(c, x, top) {   // a black tripod stand from the ground up to `top`
      line(c, "#1b1d22", 1.8, [x, -40, x - 12, 0]); line(c, "#1b1d22", 1.8, [x, -40, x + 12, 0]); line(c, "#2a2d34", 1.8, [x, -40, x + 1, 0]);
      box(c, lin(c, x - 2, 0, x + 2, 0, ["#3a3d44", "#7d848e", "#3a3d44"]), x - 1.6, top, 3.2, -top - 38);
    }
    function djRig(c, t, rm) {   // in the building's units (360 wide, ground at 0); called each frame for level 1 once the store is on screen
      const beat = rm ? 0.5 : mod(t * 2, 1), kick = rm ? 0.35 : Math.max(0, 1 - beat * 3.2), C = DJ_COL;
      const sweep = (i, sp, amp) => (rm ? 0 : Math.sin(t * sp + i * 1.7) * amp);
      const DX = 180, TOP = -124, K = 2.4;   // the DJ's spot (center stage), his table's top, his size (Juan is 1.5)
      // party light on the wall behind the stage (it pulses on the beat)
      djGlow(c, DX, -170, 130, C[Math.floor(rm ? 1 : t) % 2 ? 1 : 0], 0.2 + 0.14 * kick); djGlow(c, DX, -232, 70, C[3], 0.16 + 0.1 * kick);
      // two light trees (a T-bar on a tall stand) at the ends; their pars cross their beams down over the stage, pools of light on the sidewalk
      const pars = [[16, 0, 2.55], [44, 1, 2.3], [316, 3, -2.3], [344, 2, -2.55]];
      for (const px of [30, 330]) { box(c, lin(c, px - 2, 0, px + 2, 0, ["#5b6270", "#c9d0d8", "#5b6270"]), px - 1.5, -236, 3, 236); box(c, lin(c, 0, -240, 0, -235, ["#c9d0d8", "#6c737d"]), px - 22, -240, 44, 4.4, 1.6); }
      for (const [px, i, base] of pars) { const ang = base + sweep(i, 1.3, 0.2) * Math.sign(base), dn = -Math.cos(ang); djBeam(c, px, -228, ang, 300, 3, 34, C[i], 0.26 + 0.14 * kick);
        if (dn > 0.2) { const fx = px + Math.sin(ang) * 228 / dn; c.save(); c.scale(1, 0.22); djGlow(c, fx, -3 / 0.22, 34, C[i], 0.5 + 0.25 * kick); c.restore(); } }
      for (const [px, i] of pars) { box(c, "#17181c", px - 5, -236, 10, 9, 2.5); ell(c, C[i], px, -227.5, 4, 1.8); djGlow(c, px, -227, 11, C[i], 0.7); }
      // a moving head on each speaker sweeps a beam up into the sky, out to the sides (the beams go behind the DJ, the fixtures come with the speakers)
      const heads = [[118, -118, 4, -0.5], [242, -118, 0, 0.5]].map(([mx, my, i, base], j) => [mx, my, i, base + sweep(i + j, 0.9, 0.2)]);
      for (const [mx, my, i, ang] of heads) djBeam(c, mx, my - 7, ang, 320, 2.4, 30, C[i], 0.48 + 0.14 * kick);
      // the stage: a pallet, two rolling tool chests, a pallet deck on top, and up there his DJ table (a third chest) with the decks
      const glint = rgba(C[Math.floor(rm ? 0 : t * 2) % 3], 0.05 + 0.05 * kick);
      djPallet(c, DX - 80, 160, 0);
      c.save(); c.translate(0, -8); djChest(c, DX - 76, 75, 56, glint); djChest(c, DX + 1, 75, 56, glint); c.restore();
      djPallet(c, DX - 80, 160, -64);
      djDude(c, DX, TOP, t, rm, "body", K);
      c.save(); c.translate(0, -72); djChest(c, DX - 42, 84, 52, glint); c.restore();
      poly(c, "#121317", [DX - 37, TOP, DX + 37, TOP, DX + 34, TOP - 7, DX - 34, TOP - 7]); box(c, lin(c, 0, TOP - 8.5, 0, TOP - 6, ["#3a3d44", "#202227"]), DX - 34, TOP - 8.4, 68, 2.4, 1);
      for (const [px, ph] of [[DX - 20, 0], [DX + 20, 1.3]]) { ell(c, "#2a2d34", px, TOP - 8.6, 12, 3.4); ell(c, "#9aa3ad", px, TOP - 9, 10.4, 2.9); ell(c, "#1b1d22", px, TOP - 9, 7.8, 2.2);
        const a = (rm ? 0.6 : t * 7) + ph; ell(c, "#FF1A7F", px + Math.cos(a) * 6.4, TOP - 9 + Math.sin(a) * 1.8, 1.2, 0.7); ell(c, "#c9d0d8", px, TOP - 9, 1.2, 0.5); }
      for (let k = 0; k < 4; k++) { const lv = rm ? 2 : Math.round(1 + 3 * kick * (0.6 + 0.4 * Math.sin(k * 2.1 + t * 5))); for (let j = 0; j < 4; j++) box(c, j < lv ? (j > 2 ? "#FF1A7F" : "#00C9CD") : "#2a2d34", DX - 4 + k * 2.2, TOP - 2.5 - j * 1.4, 1.6, 1); }
      djDude(c, DX, TOP, t, rm, "hand", K);
      // lumber + red product boxes by the left door, a shopper dancing by the right door
      djPallet(c, 44, 52, 0);
      for (let r = 0; r < 4; r++) { const y = -12 - r * 4.4; box(c, lin(c, 0, y, 0, y + 4, ["#e8c2a8", "#cc9a7e"]), 45 + (r % 2), y, 50, 4, 0.8); box(c, "rgba(120,80,30,.35)", 45, y + 3.4, 51, 0.8); }
      for (let r = 0; r < 2; r++) for (let k = 0; k < 4; k++) { const bx = 46 + k * 12, by = -36 - r * 12;
        box(c, lin(c, 0, by, 0, by + 12, ["#e5322e", "#b81f22"]), bx, by, 11.6, 11.6, 1); box(c, "#ffffff", bx + 1, by + 6.8, 9.6, 2.2); box(c, "rgba(0,0,0,.25)", bx + 2, by + 2, 5, 1.1); }
      // the speakers: two up on the stage beside him, two on tripods
      djSpeaker(c, 118, -72, 30, 46, kick, rm); djSpeaker(c, 242, -72, 30, 46, kick, rm);
      djTripod(c, 30, -110); djSpeaker(c, 30, -106, 28, 44, kick, rm);   // (the light trees' poles carry on up behind them)
      djTripod(c, 330, -110); djSpeaker(c, 330, -106, 28, 44, kick, rm);
      heads.forEach(([mx, my, i, ang]) => {
        box(c, "#17181c", mx - 6, my - 3.5, 12, 3.5, 1); c.save(); c.translate(mx, my - 7); c.rotate(ang); box(c, "#22252b", -4.4, -6, 8.8, 9.6, 3); ell(c, C[i], 0, -6, 3.2, 1.3); c.restore(); djGlow(c, mx + Math.sin(ang) * 7, my - 7 - Math.cos(ang) * 7, 10, C[i], 0.8); });
      djFan(c, 292, t, rm);
      // the mini disco ball, hanging off the sign, and the sparkles it throws
      const db = 254, dby = -232; line(c, "#9aa3ad", 0.7, [db, -254, db, dby - 9]); djGlow(c, db, dby, 22, "#ffffff", 0.35);
      c.save(); c.beginPath(); c.arc(db, dby, 9, 0, Math.PI * 2); c.clip(); box(c, lin(c, db - 9, dby - 9, db + 9, dby + 9, ["#f4f7fa", "#9aa3ad", "#5b6270"]), db - 10, dby - 10, 20, 20);
      const spin = rm ? 0 : t * 3; for (let r = -4; r <= 4; r++) for (let k = -5; k <= 5; k++) { const fx = db + k * 2.2 + mod(spin * 2 + r, 2.2) - 1.1, fy = dby + r * 2.2;
        box(c, ["#ffffff", "#c9d0d8", C[(r + k + 9) % 4], "#8a939c"][Math.abs(r * 3 + k + Math.floor(spin)) % 4], fx - 0.9, fy - 0.9, 1.8, 1.8); } c.restore();
      for (let i = 0; i < 6; i++) { const a = (rm ? 0 : t * 1.4) + i * 1.05, r = 22 + (i % 3) * 14; ell(c, rgba(C[i % 4], 0.85), db + Math.cos(a) * r * 1.4, dby + Math.sin(a) * r * 0.5 + 16, 1.6, 1.6); }
      // notes floating up off the speakers
      if (!rm) for (let i = 0; i < 8; i++) { const u = mod(t * 0.45 + i / 8, 1), src = [[118, -124], [242, -124], [30, -156], [330, -156]][i % 4], side = src[0] < DX ? -1 : 1;
        c.globalAlpha = Math.min(1, u * 5) * (1 - u); djNote(c, src[0] + side * (4 + u * 16) + Math.sin(u * 9 + i) * 4, src[1] - 6 - u * 50, 1.2 + (i % 3) * 0.2, C[i % 4], i % 3 === 0); c.globalAlpha = 1; }
    }
    function store(c) {   // the building, 360 wide, ground at 0 (juan.js destination 1)
        // bright orange trim, a raised entry tower carrying the square orange sign with HON over DIPO in heavy condensed white letters (as v47),
        // an orange band with the departments, a door with an orange canopy at each end. The DJ stage (djRig) stands in the middle, under the sign.
        const OR = "#f96302", OR2 = "#d95400";
        box(c, lin(c, 0, -322, 0, 0, ["#e0d6cc", "#cfc2b4"]), 0, -322, 360, 322);
        c.fillStyle = "rgba(120,96,70,.16)"; for (let x = 24; x < 360; x += 24) c.fillRect(x, -306, 1.2, 300);
        box(c, lin(c, 0, -352, 0, -322, ["#e9dbc6", "#ddcbb1"]), 116, -352, 128, 32);   // the raised entry tower behind the sign
        box(c, OR, 0, -322, 360, 12); box(c, OR2, 0, -310, 360, 3);   // the orange roof trim…
        box(c, OR, 112, -352, 136, 10); box(c, OR2, 112, -342, 136, 3);   // …and on the tower
        box(c, OR, 0, -178, 360, 14);   // an orange band across the front with the departments
        say(c, "LUMBER · TOOLS", 52, -170.6, 9, "#ffffff", { weight: 900, max: 90 }); say(c, "PAINT · GARDEN", 308, -170.6, 9, "#ffffff", { weight: 900, max: 90 });
        box(c, OR, 0, -6, 360, 6);   // orange along the bottom
        // the square sign (v47 look, bigger): bright orange, rounded corners, a thin darker edge, HON over DIPO in heavy condensed white letters
        box(c, "rgba(0,0,0,.18)", 139, -337, 88, 88, 7); box(c, OR2, 136, -340, 88, 88, 7); box(c, lin(c, 0, -338, 0, -254, ["#ff7a1f", OR, "#ec5a00"]), 138, -338, 84, 84, 6);
        const HV = '"Avenir Next Condensed","Roboto Condensed","Arial Narrow","Helvetica Neue",Arial,sans-serif';
        for (const [txt, y] of [["HON", -316], ["DIPO", -278]]) { c.save(); c.translate(180, y); c.scale(0.84, 1); say(c, txt, 0, 0, 36, "#ffffff", { font: HV, weight: 900, max: 92 }); c.restore(); }
        line(c, "rgba(255,255,255,.85)", 2, [150, -297, 210, -297]);   // a little rule between the words
        box(c, "#8a939c", 224, -258, 38, 3, 1); box(c, "#6c757d", 222, -262, 4, 10, 1);   // a steel arm off the sign (the disco ball hangs from it)
        // a door at each end: an orange canopy, glass doors
        for (const x0 of [12, 266]) { box(c, lin(c, 0, -146, 0, -134, ["#ff8a1a", OR2]), x0 - 6, -146, 94, 12, 3); box(c, "#6c757d", x0, -134, 82, 128);
          glass(c, x0 + 4, -130, 36, 124, false); glass(c, x0 + 42, -130, 36, 124, false); box(c, "#6c757d", x0 + 40, -130, 2, 124);
          for (const hx of [x0 + 36, x0 + 46]) box(c, "#c9d0d8", hx - 1, -74, 2, 18, 1); }
    }
    return { rig: djRig, store, chest: djChest, speaker: djSpeaker, beam: djBeam, glow: djGlow, fan: djFan, note: djNote, COL: DJ_COL, rgba };
  })();

  // ---- the chase + the finish line (v49.16). Data first: a lap is a distance; the law joins in as you go (a friendly chase: no
  // guns, nobody gets hurt, running out of gas still ends it); at the end of the lap the Hon Dipo party on the Southside: the Juan
  // game's store + DJ (DJ above), lowriders hopping, monster trucks, dancers, lasers, and the cops give up and dance.
  const BANNER_Y = 150;   // event banners sit under the chase HUD (gas, the party distance, who's on your tail)
  const PARTY_COL = ["#FF1A7F", "#00C9CD", "#9b4dff", "#FF6A0B"];
  const CHASE = {
    laps: [
      { name: "San Antonio", miles: 1.25, boost: 0, gas: 1, feria: 40, pts: 3000 },
      { name: "Otra vuelta", miles: 1.5, boost: 0.3, gas: 1.25, feria: 75, pts: 6000 },   // harder: faster traffic sooner, gas cans farther apart
    ],
    pursuers: [[0.1, "cop"], [0.22, "trooper"], [0.34, "cop"], [0.46, "fbi"], [0.58, "trooper"], [0.68, "cop"], [0.78, "fbi"], [0.88, "cop"]],   // [progress, traffic id]
    helis: [{ at: 0.7, word: "POLICE", body: "#1d2a4a", belly: "#e9edf6", x: 0.72 }, { at: 0.84, word: "CHISME NEWS", body: "#FF1A7F", belly: "#ffffff", x: 0.3 }],
    beam: "#dff6ff",
    tail: {
      cop: ["Sir! SIR! …nice paint.", "Pull over! Por favor?", "Requesting backup. And snacks."],
      trooper: ["Howdy— I mean STOP.", "Sir, this is a 3-wheel zone."],
      fbi: ["We've been tracking that paint job.", "Suspect is… vibing."],
    },
    give: ["…is that a DJ on tool chests?", "Okay. One song.", "Backup has arrived. To dance.", "We're off duty in 3… 2…"],
    party: { secs: 6.5, near: 2600, cops: 4,
      rides: [{ car: "64", paint: "turq", x: 18, row: 0, ph: 0 }, { car: "jefe", paint: "purple", x: 520, row: 1, ph: 1.7 }, { car: "64", paint: "cherry", x: 640, row: 0, ph: 3.1 }],
      trucks: [{ x: 300, row: 1, body: "#7a32d4", hi: "#b27cff", trim: "#00C9CD", word: "LA CHANCLA", ph: 0.6 }, { x: 760, row: 1, body: "#00a3ab", hi: "#5fe0e4", trim: "#FF1A7F", word: "PAN DULCE", ph: 2.2 }],
      taq: { name: "Tacos La Tía Metiche", tag: "BARBACOA · CHISME GRATIS", wall: "#14b8b0", sign: "#FF1A7F" },
      dancers: 11 },
    finish: { title: "¡LLEGASTE!", sub: "You made it to the Hon Dipo party on the Southside. The cops stayed for the DJ.", again: "🔁 Otra vuelta (harder)" },
    lapLabel: "🔁 Otra vuelta (harder)",
  };
  const ell = (g, col, x, y, rx, ry) => { g.fillStyle = col; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, TAU); g.fill(); };
  let partyNear = false;   // lot(): the last stretch before the party is empty lots (the party scene draws there)
  const partyLot = () => ({ kind: "party", w: 400, crowd: 0, top: 40, draw() {} });

  function heli(g, x, y, h, t, rm) {   // a cartoon helicopter, nose right
    g.save(); g.translate(x, y); g.rotate(rm ? 0 : Math.sin(t * 1.3) * 0.04);
    g.strokeStyle = "#20232b"; g.lineWidth = 3; g.beginPath(); g.moveTo(-14, 18); g.lineTo(26, 18); g.moveTo(-8, 10); g.lineTo(-8, 18); g.moveTo(18, 10); g.lineTo(18, 18); g.stroke();
    box(g, h.body, -62, -6, 44, 7, 3);   // tail boom
    poly(g, h.body, [-66, -18, -58, -18, -54, -4, -64, -2]);
    g.fillStyle = h.body; g.beginPath(); g.ellipse(4, 0, 30, 14, 0, 0, TAU); g.fill();
    g.fillStyle = h.belly; g.beginPath(); g.ellipse(4, 6, 26, 6, 0, 0, Math.PI); g.fill();
    g.fillStyle = "#9fd8f0"; g.beginPath(); g.ellipse(20, -3, 12, 9, 0.2, -1.6, 1.4); g.fill();
    g.fillStyle = "rgba(255,255,255,.55)"; g.fillRect(17, -9, 3, 7);
    g.font = `900 7px ${H.SANS}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = "#ffffff"; g.fillText(h.word, -4, 0, 40);
    box(g, "#20232b", 0, -18, 6, 5, 1);
    const sp = rm ? 0.5 : (t * 9) % 1;   // the main rotor (a blur), the tail rotor
    g.fillStyle = "rgba(30,32,40,.75)"; g.fillRect(-46 + sp * 6, -20, 98 - sp * 12, 2.4);
    g.fillStyle = "rgba(30,32,40,.25)"; g.beginPath(); g.ellipse(3, -19, 50, 3, 0, 0, TAU); g.fill();
    g.strokeStyle = "rgba(30,32,40,.6)"; g.lineWidth = 2; g.beginPath(); g.arc(-62, -14, 8, 0, TAU); g.stroke();
    g.fillStyle = Math.floor(t * 3) % 2 ? "#ff2a3a" : "#2f6bff"; g.beginPath(); g.arc(-60, -6, 2, 0, TAU); g.fill();
    g.restore();
  }
  function mtruck(g, x, gy, s, T, t, rm) {   // a cartoon monster truck (big tires, lifted, its name on the bed)
    const b = rm ? 0 : Math.abs(Math.sin(t * 3.4 + T.ph)) * 9, sq = rm ? 0 : Math.max(0, Math.sin(t * 3.4 + T.ph + 1.2)) * 3;
    g.save(); g.translate(x, gy); g.scale(s, s);
    g.fillStyle = "rgba(0,0,0,.45)"; g.beginPath(); g.ellipse(70, 1, 82, 6, 0, 0, TAU); g.fill();
    for (const wx of [24, 116]) { g.save(); g.translate(wx, -26 + sq * 0.3);
      g.fillStyle = "#15131a"; g.beginPath(); g.arc(0, 0, 26, 0, TAU); g.fill();
      g.fillStyle = "#2b2733"; for (let k = 0; k < 12; k++) { const a = k / 12 * TAU + (rm ? 0 : t * 2); g.save(); g.rotate(a); g.fillRect(-3, -28, 6, 5); g.restore(); }
      g.fillStyle = "#cfd4dc"; g.beginPath(); g.arc(0, 0, 11, 0, TAU); g.fill(); g.fillStyle = T.trim; g.beginPath(); g.arc(0, 0, 5, 0, TAU); g.fill(); g.restore(); }
    g.translate(0, -b);
    g.strokeStyle = "#3a3f4a"; g.lineWidth = 4; g.beginPath(); g.moveTo(24, -30); g.lineTo(40, -50); g.moveTo(116, -30); g.lineTo(100, -50); g.stroke();   // the lift
    box(g, "#2b2733", 6, -56, 128, 8, 3);
    g.fillStyle = H.lg(g, 0, -96, 0, -50, [[0, T.hi], [0.5, T.body], [1, H.shade(T.body, -0.35)]]);
    g.beginPath(); g.moveTo(2, -52); g.lineTo(2, -74); g.lineTo(62, -76); g.lineTo(70, -100); g.lineTo(108, -100); g.lineTo(122, -76); g.lineTo(140, -72); g.lineTo(140, -52); g.closePath(); g.fill();
    poly(g, "#9fd8f0", [76, -96, 104, -96, 114, -77, 72, -77]);
    box(g, T.trim, 2, -64, 138, 4, 2);
    for (let k = 0; k < 4; k++) poly(g, T.trim, [8 + k * 14, -56, 16 + k * 14, -56, 24 + k * 14, -70, 16 + k * 14, -70]);   // flames-ish chevrons
    g.font = `900 13px ${H.FONT}`; g.textAlign = "center"; g.textBaseline = "middle"; g.lineWidth = 3; g.strokeStyle = "#1a1420"; g.strokeText(T.word, 36, -78, 66); g.fillStyle = "#ffffff"; g.fillText(T.word, 36, -78, 66);
    box(g, "#cfd4dc", 132, -60, 9, 5, 2); ell(g, "#e8f7ff", 138, -68, 3, 3);
    g.restore();
  }
  function taq(g, x, gy, s, T) {   // the taquería next door
    g.save(); g.translate(x, gy); g.scale(s, s);
    box(g, H.lg(g, 0, -150, 0, 0, [[0, T.wall], [1, H.shade(T.wall, -0.25)]]), 0, -150, 230, 150);
    box(g, "#0e5f5c", -4, -156, 238, 8, 2);
    box(g, "#111111", 30, -140, 170, 34, 4); g.font = `900 17px ${H.FONT}`; g.textAlign = "center"; g.textBaseline = "middle"; g.fillStyle = T.sign; g.fillText(T.name, 115, -122, 160);
    for (let i = 0; i < 16; i++) { const px = 4 + i * 14; poly(g, PARTY_COL[i % 4], [px, -100, px + 12, -100, px + 12, -94, px + 6, -90, px, -94]); }
    g.font = `800 8px ${H.SANS}`; g.fillStyle = "#ffffff"; g.fillText(T.tag, 115, -84, 200);
    for (let i = 0; i < 10; i++) box(g, i % 2 ? "#ffffff" : T.sign, 10 + i * 21, -76, 21, 12);
    box(g, "#2b2f38", 12, -62, 150, 50); g.fillStyle = H.lg(g, 12, -62, 162, -12, [[0, "#bfe6f7"], [0.5, "#7fb6d6"], [1, "#a9d4ea"]]); g.fillRect(14, -60, 146, 46);
    box(g, "#7a3b2a", 176, -62, 34, 62, 2);
    g.restore();
  }

  // the chase + the party, added onto the stage's systems (base: what install() built)
  function chaseKit(K, base, fxx) {
    const A = K.audio, rand = K.rand, Hk = K.H, clamp = Hk.clamp, lerp = Hk.lerp;
    const lapOf = (n) => CHASE.laps[Math.min(CHASE.laps.length, Math.max(1, n || 1)) - 1];
    const TT = (id) => TRAFFIC.find((q) => q.id === id) || TRAFFIC[0];
    const prog = () => { const r = K.run; return r && r.goal ? clamp(r.meters / r.goal, 0, 1) : 0; };
    const fake = (id, i) => ({ T: TT(id), dx: 0, wob: i * 1.9, hit: false, same: true, driver: driver(rand) });
    function lead() { const c = K.run && K.run.chase; return c && c.n ? c.cars[c.n - 1] : null; }
    function tailSay(text) {
      const c = K.run.chase, p = { get x() { return K.camX + 30; }, y: K.GY - 22, s: 1 };
      const B = K.bubbles; B.push({ p, text, t: 0, life: 1.8 }); if (B.length > 3) B.shift();
    }
    function party() {   // the finish: the car pulls in, the party, the cops give up and dance, then the ending card
      const car = K.car, run = K.run, x = car.x + 200 + Math.max(320, car.v * 2.2) + 120, keep = (c) => c.x < car.x + 200;
      K.obs = K.obs.filter((o) => o.x + o.w < car.x + 200); K.coins = K.coins.filter(keep); K.picks = K.picks.filter(keep);
      K.hold = 1e12; K.nextObs = 1e12; partyNear = true;
      const P = CHASE.party, nc = Math.min(P.cops, Math.max(1, run.chase.n));
      const cops = run.chase.cars.slice(-nc).map((o, i) => ({ o, i, at: 0.5 + i * 0.55, sx: -220, hop: 0, said: false }));
      const R = Hk.rng ? Hk.rng(7) : rand, dancers = [];
      for (let i = 0; i < P.dancers; i++) { const back = i % 3 !== 2; dancers.push({ rel: 120 + i * 58 + (R() - 0.5) * 20, back, p: Hk.makePerson(R, 0, 0, { dance: true, kid: false, s: back ? 0.72 : 0.9 }) }); }
      const ev = { type: "party", stop: true, x, X0: x - 260, phase: "arrive", t: 0, pt: 0, hops: 0, cops, dancers,
        update(dt) {
          if (ev.phase === "arrive" && (K.car.v < 25 || ev.t > 6)) { ev.phase = "party"; ev.pt = 0; K.run.chase.party = "party";
            fxx("cheer"); K.burst(ev.x - 120, K.GY - 220, 26, "confetti", { sp: 240, life: 1.4 });
            K.pop(CHASE.finish.title, { x: K.LW / 2, y: Math.max(150, K.GY - 330), col: Hk.COL.pink, size: 40, big: true, life: 2, rise: 8 }); K.sayLine("¡Llegaste!", "es-MX", { rate: 1, gap: 3000 }); }
          if (ev.phase !== "party") return; ev.pt += dt;
          for (const c of ev.cops) { const go = ev.pt - c.at; if (go <= 0) continue; c.sx = Math.min(c.i === 0 ? 228 : c.i === 1 ? 336 : c.i === 2 ? -40 : 440, -220 + go * 520);
            if (!c.said && go > 0.6) { c.said = true; const L = CHASE.give[c.i % CHASE.give.length], o = c, p = { get x() { return K.camX + o.sx + 60; }, y: K.GY - 4, s: 1 }; K.bubbles.push({ p, text: L, t: 0, life: 2 }); if (K.bubbles.length > 3) K.bubbles.shift(); fxx("chirp"); } }
          if (!partyLights && ev.pt > 3) { partyLights = true; fxx("cheer"); K.crowd(1, 0.8, "¡Ándale!"); }
          if (ev.pt > P.secs && ev.phase === "party") { ev.phase = "done"; done(ev); }
        },
        press() { if (ev.phase !== "party" || ev.hops >= 8) return; ev.hops++; const pts = 150 * K.TIERS[K.run.tier].x; K.run.score += pts;
          K.pop("+PARTY HOP " + K.num(pts), { x: K.LW / 2, y: Math.max(170, K.GY - 270) + (ev.hops % 2) * 26, col: Hk.COL.turq, size: 20, big: true, life: 1, rise: 14 }); fxx("oooh", 0.5); },
        auto(inRun) { const car = K.car; if (ev.phase === "party" && !car.charging && ev.hops < 3 && (ev.pt % 1.3) < 0.02) K.startCharge(); if (car.charging && car.charge > 0.45) inRun ? K.release() : K.launch(); return true; },
        draw(g, t, front) { if (!front) return; const rm = K.reduced(), GY = K.GY;   // the cops who came to arrest you and stayed to dance
          for (const c of ev.cops) { if (c.sx < -200) continue; const hop = partyLights && !rm ? Math.abs(Math.sin(t * 6 + c.i * 1.3)) * 12 : 0;
            g.save(); g.translate(c.sx, GY + 34 - hop); g.scale(0.85, 0.85); drawTraffic(g, c.o, 0, 0, t, rm, Hk); g.restore(); } },
        banner(g, t, txt) { if (ev.phase === "done") return; const LW = K.LW, bw = 262, bx = (LW - bw) / 2, by = BANNER_Y, C = Hk.COL;
          g.fillStyle = "rgba(0,0,0,.82)"; Hk.rr(g, bx, by, bw, 50, 12); g.fill(); g.strokeStyle = C.pink; g.lineWidth = 3; Hk.rr(g, bx, by, bw, 50, 12); g.stroke();
          txt("🎉 HON DIPO PARTY!", LW / 2, by + 18, 16, C.pink, "center", null);
          txt(ev.phase === "arrive" ? "Pull in… the whole Southside is here" : "HOP for the crowd · the cops are staying", LW / 2, by + 37, 11, "#ffffff", "center", null, Hk.SANS, "800"); },
      };
      run.chase.party = "arrive"; A.tempo && A.tempo(1.1); return ev;
    }
    let lastFin = null;
    function done(ev) {
      const run = K.run, st = K.st, L = lapOf(run.lap); run.chase.party = "done";
      run.score += L.pts; run.feria += L.feria; st.laps = st.laps || {}; st.laps.sa = Math.min(9, Math.max(st.laps.sa || 0, run.lap)); K.save();
      lastFin = { title: CHASE.finish.title, sub: CHASE.finish.sub, bonus: `+${L.feria} Feria party bonus · +${K.num(L.pts)} points`, again: CHASE.finish.again };
      K.endRun("finish");
    }
    function scene(g, t) {   // the Hon Dipo party (over the empty lots): taquería, store + DJ, the parking lot
      const ev = K.ev; if (!ev || ev.type !== "party") return; H = Hk; const sx0 = ev.X0 - K.camX, LW = K.LW, GY = K.GY, rm = K.reduced(), P = CHASE.party;
      if (sx0 > LW + 40 || sx0 + 900 < -40) return;
      const top = GY - 108, s = clamp((top - 150) / 352, 0.5, 0.9), sw = 360 * s;
      // the parking lot (asphalt + stripes) in front, over the far sidewalk
      g.fillStyle = Hk.lg(g, 0, top, 0, GY - 46, [[0, "#2c2638"], [1, "#3b3349"]]); g.fillRect(sx0 - 160, top, 1100, GY - 46 - top);
      g.fillStyle = "rgba(255,255,255,.55)"; for (let k = 0; k < 18; k++) { const xx = sx0 - 150 + k * 60; g.beginPath(); g.moveTo(xx, top + 4); g.lineTo(xx + 3, top + 4); g.lineTo(xx - 10, GY - 50); g.lineTo(xx - 13, GY - 50); g.fill(); }
      taq(g, sx0 - 150, top, s * 0.9, P.taq);
      g.save(); g.translate(sx0 + 120, top); g.scale(s, s); DJ.store(g); DJ.rig(g, t, rm); g.restore();
      // a neighbor wall past the store (plain, the city behind)
      box(g, Hk.lg(g, 0, top - 140, 0, top, [[0, "#5a4a72"], [1, "#3e3354"]]), sx0 + 120 + sw + 8, top - 140, 520, 140);
      for (let k = 0; k < 7; k++) box(g, k % 2 ? "#6a5a84" : "#4b3e63", sx0 + 140 + sw + k * 72, top - 112, 52, 60, 3);
      // lasers from the DJ (party colors), thin, additive
      if (ev.phase !== "arrive" || ev.t > 0.4) { g.save(); g.globalCompositeOperation = "lighter"; const ox = sx0 + 120 + 180 * s, oy = top - 200 * s;
        for (let k = 0; k < 8; k++) { const a = -Math.PI / 2 + (k - 3.5) * 0.28 + (rm ? 0 : Math.sin(t * 1.4 + k) * 0.35); g.strokeStyle = PARTY_COL[k % 4]; g.globalAlpha = 0.55; g.lineWidth = 1.6;
          g.beginPath(); g.moveTo(ox, oy); g.lineTo(ox + Math.cos(a) * 700, oy + Math.sin(a) * 700); g.stroke(); }
        g.restore(); }
      // the lot: lowriders hopping, monster trucks bouncing, dancers
      const rows = [top + 22, GY - 50], put = [];
      for (const r of P.rides) put.push({ rel: r.x, row: r.row, f: () => { const car = LIB.carById ? LIB.carById(r.car) : null, Pn = LIB.PAINTS.find((q) => q.id === r.paint) || LIB.PAINTS[0];
        const u = rm ? 0 : Math.max(0, Math.sin(t * 2.6 + r.ph)), hop = u * 70, ang = rm ? 0 : -Math.sin(t * 2.6 + r.ph) * 0.16 * u;
        g.save(); g.translate(sx0 + r.x, rows[r.row]); g.scale(0.46, 0.46); Hk.drawCar(g, { x: 0, gy: 0, y: hop, sR: 0, sF: 0, ang, rot: rm ? 0 : t * 4, t, P: Pn, car, lights: false, blur: false, brake: false, bob: 0 }); g.restore(); } });
      for (const T of P.trucks) put.push({ rel: T.x, row: T.row, f: () => mtruck(g, sx0 + T.x, rows[T.row], 0.62, T, t, rm) });
      for (const d of ev.dancers) put.push({ rel: d.rel, row: d.back ? 0 : 1, f: () => { d.p.y = d.back ? rows[0] + 2 : rows[1] + 2; Hk.drawPerson(g, d.p, sx0 + d.rel, rm ? 0 : t); } });
      put.sort((a, b) => a.row - b.row); for (const q of put) { const xx = sx0 + q.rel; if (xx > -160 && xx < LW + 60) q.f(); }
      // party glow on the lot
      if (!rm) { const k = Math.floor(t * 2) % 4; Hk.drawGlow(g, sx0 + 120 + 180 * s, top + 10, 180, PARTY_COL[k], 0.18); }
    }
    function chaseFront(g, t) {   // behind you (near lane), the strobe, the helicopters and their searchlights
      const run = K.run, c = run && run.chase; if (!c) return; H = Hk; const LW = K.LW, GY = K.GY, rm = K.reduced(), ev = K.ev, atParty = ev && ev.type === "party" && ev.phase !== "arrive";
      if (!atParty && c.n) {
        const amp = Math.min(1, 0.35 + c.n * 0.09), on = rm ? 0 : Math.floor(t * 6) % 2;
        Hk.drawGlow(g, 0, GY - 10, 90 + c.n * 14, on ? "#ff2a3a" : "#2f6bff", 0.32 * amp);
        const o = lead(); if (o) { const k = clamp((run.t - c.joinT) / 0.9, 0, 1), sx = lerp(-200, -64, k) + (rm ? 0 : Math.sin(t * 1.1) * 6);
          g.save(); g.translate(sx, GY + 34); g.scale(0.85, 0.85); drawTraffic(g, o, 0, 0, t, rm, Hk); g.restore(); }
      }
      CHASE.helis.forEach((h, i) => { const st = c.heli[i]; if (st == null) return; const k = clamp((run.t - st) / 2.5, 0, 1);
        const hx = lerp(LW + 90, LW * h.x, k) + (rm ? 0 : Math.sin(t * 0.5 + i * 2) * 26), hy = Math.max(130, GY - 420) + i * 46 + (rm ? 0 : Math.sin(t * 1.3 + i) * 5);
        const tx = 118 + (rm ? 0 : Math.sin(t * 0.8 + i * 2.1) * 150), col = atParty && partyLights ? PARTY_COL[(i * 2 + Math.floor(t * 2)) % 4] : CHASE.beam;
        g.save(); g.globalCompositeOperation = "lighter"; g.globalAlpha = atParty ? 0.22 : 0.16; g.fillStyle = Hk.lg(g, 0, hy, 0, GY + 20, [[0, col], [1, "rgba(0,0,0,0)"]]);
        g.beginPath(); g.moveTo(hx + 10, hy + 10); g.lineTo(tx - 46, GY + 22); g.lineTo(tx + 46, GY + 22); g.closePath(); g.fill();
        g.globalAlpha = atParty ? 0.2 : 0.14; g.fillStyle = col; g.beginPath(); g.ellipse(tx, GY + 6, 52, 12, 0, 0, TAU); g.fill(); g.restore();
        heli(g, hx, hy, h, t, rm); });
    }
    return Object.assign({}, base, {
      lapLabel: CHASE.lapLabel, bannerY: BANNER_Y,
      runStart(run) {
        const L = lapOf(run.lap); run.goal = L.miles * K.MILE; run.boost = L.boost; run.gasK = L.gas;
        run.chase = { n: 0, cars: [], joinT: 0, sayT: 5, heli: [], party: null }; partyNear = false; partyLights = false; lastFin = null;
        base.runStart(run);
      },
      run(dt) {
        const run = K.run, c = run.chase, p = prog();
        base.run(dt); if (!c || run.over) return;
        while (c.n < CHASE.pursuers.length && p >= CHASE.pursuers[c.n][0] && !c.party) {
          const id = CHASE.pursuers[c.n][1]; c.cars.push(fake(id, c.n)); c.n++; c.joinT = run.t; fxx("chirp");
          if (c.n === 1 || rand() < 0.6) { c.sayT = 4 + rand() * 4; const L = CHASE.tail[id] || CHASE.tail.cop; tailSay(L[(rand() * L.length) | 0]); }
        }
        CHASE.helis.forEach((h, i) => { if (c.heli[i] == null && p >= h.at) { c.heli[i] = run.t; fxx("chirp"); } });
        c.sayT -= dt; if (c.n && c.sayT <= 0 && !c.party) { c.sayT = 7 + rand() * 5; const o = lead(), L = CHASE.tail[o.T.id] || CHASE.tail.cop; tailSay(L[(rand() * L.length) | 0]); }
        if ((run.goal - run.meters) * K.UPM < CHASE.party.near) partyNear = true;
        if (p > 0.9) { run.nextAbuela = Math.max(run.nextAbuela || 0, run.t + 99); run.nextChancla = Math.max(run.nextChancla || 0, run.t + 99); run.nextTrail = Math.max(run.nextTrail || 0, run.t + 99); }
        if (!c.party && p >= 1 && !K.ev && !run.out) K.startEvent("party");
      },
      event(type) { return type === "party" ? party() : base.event(type); },
      hud(g, t, txt) {
        base.hud(g, t, txt); const run = K.run, c = run && run.chase; if (!c) return; const C = Hk.COL, rr = Hk.rr, fx = 14, fy = 96, fw = 100;
        const left = Math.max(0, (run.goal - run.meters) / K.MILE), p = prog();
        txt(c.party ? "🎉 ¡LLEGASTE! Hon Dipo party" : `🎉 Hon Dipo party: ${left.toFixed(2)} mi`, fx, fy, 10, "#ffffff", "left", "#000", Hk.SANS, "900");
        g.fillStyle = "rgba(0,0,0,.6)"; rr(g, fx, fy + 8, fw, 6, 3); g.fill(); g.fillStyle = C.pink; rr(g, fx, fy + 8, Math.max(6, fw * p), 6, 3); g.fill();
        if (c.n && !c.party) { const on = K.reduced() || Math.floor(t * 3) % 2 === 0; g.fillStyle = "rgba(0,0,0,.7)"; rr(g, fx, fy + 20, 104, 18, 9); g.fill();
          g.strokeStyle = on ? "#ff2a3a" : "#2f6bff"; g.lineWidth = 1.5; rr(g, fx, fy + 20, 104, 18, 9); g.stroke();
          txt(`🚨 x${c.n} on your tail`, fx + 8, fy + 29, 10, "#ffffff", "left", null, Hk.SANS, "900"); }
      },
      draw(g, t, layer) { if (base.draw) base.draw(g, t, layer); if (layer === "lot") scene(g, t); else if (layer === "front") chaseFront(g, t); },
      finish() { return lastFin; },
      state() { const run = K.run, c = run && run.chase, ev = K.ev; if (!c) return null;
        return { lap: run.lap, goal: Math.round(run.goal), progress: +prog().toFixed(3), n: c.n, helis: c.heli.filter((x) => x != null).length, party: c.party, phase: ev && ev.type === "party" ? ev.phase : null,
          copsIn: ev && ev.type === "party" ? ev.cops.filter((q) => q.sx > -200).length : 0, partyLights, boost: run.boost, gasK: run.gasK }; },
    });
  }

  // ---- the stage's systems, plugged into the game through install(K): K is the game's kernel (getters/setters for its world:
  // run, car, camX, obs, picks, bubbles, ev, hold, nextObs …; its helpers: pop, burst, crowd, sayLine, audio, txt …). The game calls
  // back: obstacle(d) (traffic instead of a road obstacle), afterObstacle(o), ahead() (gas cans), runStart(run), run(dt) (pickups, the
  // tank, the Trail Ride's dice), tick(dt) (traffic rolls, wobbles, honks, talks), say / over (a hit / a hop), event(type), hud(g, t).
  // An event object can carry its own update / press / auto / drawRoad / draw / banner, and stop: true (the car waits before ev.x).
  function install(K) {
    const E = LIB.EVENTS.trail, rand = K.rand, A = K.audio, S = A.synth, H = K.H, clamp = H.clamp, lerp = H.lerp;
    if (S) Object.assign(A.fx, {   // short, quiet, all synthesized
      honk(k = 1) { if (!S.on) return; const t = S.ac.currentTime, f = k > 1 ? 330 : 415; for (const [dt, d] of [[0, 0.16], [0.21, 0.24]]) { S.osc("square", f, t + dt, d, 0.07, S.out, 0.004); S.osc("square", f * 1.26, t + dt, d, 0.05, S.out, 0.004); } },
      scream() { if (!S.on) return; const t = S.ac.currentTime, o = S.osc("sawtooth", 700, t, 0.55, 0.05, S.out, 0.02);
        try { o.frequency.cancelScheduledValues(t); o.frequency.setValueCurveAtTime(new Float32Array([700, 1250, 1400, 1300, 1380, 900]), t, 0.55); } catch (e) {} S.nz(t, 0.5, 0.05, S.out, "bandpass", 2400, 3, 0.02); },
      chirp() { if (!S.on) return; const t = S.ac.currentTime; S.osc("sine", 900, t, 0.22, 0.07, S.out, 0.004, 1500, 0.2); },   // a friendly "whoop" from a patrol car, not a siren
      clop(n = 4) { if (!S.on) return; const t = S.ac.currentTime; for (let i = 0; i < n; i++) { const tt = t + i * 0.19 + (i % 2) * 0.05; S.nz(tt, 0.035, 0.22, S.out, "bandpass", 1900 + (i % 2) * 500, 6, 0.001); S.osc("sine", 260, tt, 0.05, 0.08, S.out, 0.001, 140); } },
    });
    const fxx = (k, ...a) => { const f = A.fx[k]; if (f) f(...a); };
    // traffic is oncoming (the other lane, coming at you), and always hoppable: the hop box is the body, not the bumpers (T.box of the drawn
    // length), and a vehicle always comes at least fast enough that a solid (not even full) hop clears it. meet = where you'd meet it at
    // cruise speed; it spawns farther out.
    function addTraffic(T, meet, d) {
      const car = K.car, w = Math.round(T.w * (T.box || 0.74)), v = K.cruise(d), lo = Math.max(0, (w + 200) * 1.35 - v);
      const s = clamp(T.speed ? T.speed[0] + rand() * (T.speed[1] - T.speed[0]) : 80, lo, Math.max(lo, 260)), x = meet + s * Math.max(0, meet - car.x - 200) / v;
      const o = { kind: "traffic", T, x, w, dx: (T.w - w) / 2, h: T.h, vx: -s, pit: false, soft: false, hit: false, cleared: false, knock: null, noKnock: true,
        driver: driver(rand), wob: rand() * 6.28, seed: (rand() * 1e6) | 0, near: false, honked: false };
      K.obs.push(o); return o;
    }
    const addPick = (kind, x, h) => K.picks.push({ kind, x, h, got: false, t: rand() * 6 });
    function say(o, when) {   // a comic line from the driver (data: T.lines.near / over / hit)
      const L = o.T.lines && o.T.lines[when]; if (!L || !L.length) return;
      const off = (o.T.mouth != null ? o.T.mouth : o.T.w * 0.4) - (o.dx || 0), p = { get x() { return o.x + off; }, y: K.GY - (o.T.mouthY || o.h + 4) + 46, s: 1 };
      const B = K.bubbles; B.push({ p, text: L[(rand() * L.length) | 0], t: 0, life: 1.5 }); if (B.length > 3) B.shift();
    }
    // the Trail Ride: the riders cross at a crossing ahead; the car always stops before it (never near a horse); every hop while
    // they cross is a salute (+YEEHAW), and the trail boss hollers back
    const trailDur = () => (E.horses - 1) * 0.62 + 2.8;
    function trail() {
      const car = K.car, x = car.x + 200 + Math.max(300, car.v * 2.4) + 90, keep = (c) => c.x < car.x + 200 || c.x > x + 700;
      K.obs = K.obs.filter((o) => o.x + o.w < car.x + 200 || o.x > x + 700); K.coins = K.coins.filter(keep); K.picks = K.picks.filter(keep);
      K.hold = x + 720; if (K.nextObs < K.hold) K.nextObs = K.hold;
      const ev = { type: "trail", stop: true, x, phase: "warn", t: 0, d: 0, n: E.horses, riders: riders(E.horses, rand), salutes: 0, clop: 0,
        update(dt) {
          if (ev.say) ev.say.t += dt;
          if (ev.phase === "warn" && ev.t > 0.8) { ev.phase = "wait"; ev.t = 0; }
          if (ev.phase === "wait" && (K.car.v < 6 || ev.t > 6)) { ev.phase = "cross"; ev.t = 0; A.tempo(0.8); }
          if (ev.phase === "cross") { ev.d = ev.t; ev.clop -= dt; if (ev.clop <= 0) { fxx("clop", 4); ev.clop = 0.8; }
            if (!ev.hi && ev.t > 0.7) { ev.hi = true; ev.say = { text: "Yeehaw!", i: 0, t: 0 }; K.sayLine("Yeehaw!", "en-US", { pitch: 1.1, rate: 1, gap: 4000 }); }   // the trail boss says hi
            if (ev.t > trailDur()) { ev.phase = "done"; ev.t = 0; finish(); } }
          if (ev.phase === "done" && ev.t > 1.8) K.ev = null;
        },
        press() { if (ev.phase === "cross" && ev.salutes < E.max) salute(); },
        auto(inRun) { const car = K.car; if (ev.phase === "done") return false;
          if (ev.phase === "cross" && !car.charging && ev.salutes < 3 && (ev.t % 1.4) < 0.02) K.startCharge(); if (car.charging && car.charge > 0.4) inRun ? K.release() : K.launch(); return true; },
        drawRoad(g) { const sx = ev.x - K.camX; g.fillStyle = "rgba(255,255,255,.5)"; for (let i = 0; i < 6; i++) { g.save(); g.translate(sx, K.GY - 44 + i * 15.2); g.transform(1, 0, -0.35, 1, 0, 0); g.fillRect(0, 0, 70, 3); g.restore(); } },
        draw(g, t, front) {   // the far half of the line walks behind the car, the near half in front
          if (ev.phase !== "cross" && ev.phase !== "done") return; const GY = K.GY;
          ev.riders.forEach((r, i) => { const u = clamp((ev.d - i * 0.62) / 2.8, 0, 1); if (u <= 0 || u >= 1) return; const x = ev.x - K.camX - 10 + u * 70, y = GY - 50 + u * 100;
            if ((y >= GY + 4) !== front) return; horse(g, r, x, y, 0.95 + u * 0.15, t, K.reduced(), H);
            if (ev.say && ev.say.i === i && ev.say.t < 1.4) K.bubble(g, x + 10, y - 84, ev.say.text, ev.say.t, K.LW); });
        },
        banner(g, t, txt) { if (ev.phase === "done") return; const LW = K.LW, bw = 248, bx = (LW - bw) / 2, by = BANNER_Y, C = H.COL;
          g.fillStyle = "rgba(0,0,0,.82)"; H.rr(g, bx, by, bw, 50, 12); g.fill(); g.strokeStyle = C.orange; g.lineWidth = 3; H.rr(g, bx, by, bw, 50, 12); g.stroke();
          txt("TRAIL RIDE!", LW / 2, by + 18, 16, C.orange, "center", null);
          txt(ev.phase === "cross" ? "HOP to salute the riders · +YEEHAW" : "Let the horses cross · then hop to salute", LW / 2, by + 37, 11, "#ffffff", "center", null, H.SANS, "800"); },
      };
      fxx("clop", 6); return ev;
    }
    function salute() {
      const ev = K.ev, run = K.run; ev.salutes++; run.salutes++; const pts = E.bonus * K.TIERS[run.tier].x; run.score += pts; run.feria += 1;
      K.pop("+YEEHAW " + K.num(pts), { x: K.LW / 2, y: Math.max(150, K.GY - 250) + (ev.salutes % 2) * 30, col: H.COL.turq, size: 24, big: true, life: 1.1, rise: 12 });
      const vis = ev.riders.map((r, i) => i).filter((i) => { const u = (ev.d - i * 0.62) / 2.8; return u > 0.1 && u < 0.85; }), i = vis.length ? vis[(rand() * vis.length) | 0] : -1;   // a rider you can see answers
      if (i >= 0) ev.say = { text: ["Yeehaw!", "¡Ajúa!", "Yeehaw!", "Nice hop, partner!"][(rand() * 4) | 0], i, t: 0 };
      fxx("oooh", 0.5);
    }
    function finish() {
      const run = K.run, st = K.st; A.tempo(1); fxx("cheer");
      if (run) { run.trails++; run.score += 250; run.feria += E.feria; st.totals.trails = (st.totals.trails || 0) + 1; K.save(); }
      K.pop("TRAIL RIDE! +YEEHAW", { x: K.LW / 2, y: Math.max(140, K.GY - 256), col: H.COL.turq, size: 28, big: true, life: 1.6, rise: 10 });
      K.crowd(1, 0.8, "Yeehaw!"); K.sayLine("Yeehaw!", "en-US", { pitch: 1.1, rate: 1, gap: 4000 });
    }
    return chaseKit(K, {
      addTraffic, addPick,
      obstacle(d) {   // maybe a vehicle instead of a road obstacle (with a taco / soda over the spot where you meet it)
        const list = TRAFFIC.filter((T) => (T.min || 0) <= d + 0.001), run = K.run;
        if (!list.length || rand() >= trafficRate(d) || !(run || K.mode === "title")) return false;
        let tot = 0; for (const T of list) tot += T.weight || 1; let k = rand() * tot, T = list[0]; for (const q of list) { k -= q.weight || 1; if (k <= 0) { T = q; break; } }
        const n = K.nextObs, o = addTraffic(T, n, d);
        if (run && rand() < 0.5) addPick(rand() < 0.55 ? "taco" : "soda", n + o.w / 2, 150 + rand() * 40);
        K.nextObs = n + K.cruise(d) * (lerp(2.7, 1.8, d) + rand() * lerp(1.2, 0.7, d)) + o.w + (run ? 0 : 160);
        return true;
      },
      afterObstacle(o) { if (rand() >= 0.3) return false; addPick(rand() < 0.5 ? "soda" : "taco", o.x + o.w / 2, 110 + rand() * 60); return true; },
      ahead() { const run = K.run; if (run && !run.out) while (run.nextGas < K.camX + K.LW + 300) { addPick("gas", run.nextGas, rand() < 0.5 ? 26 : 120 + rand() * 50); run.nextGas += (FUEL.gasEvery[0] + rand() * (FUEL.gasEvery[1] - FUEL.gasEvery[0])) * (run.gasK || 1); } },
      runStart(run) { run.nextGas = K.car.x + 200 + FUEL.first; run.nextTrail = E.first + rand() * 10; },
      run(dt) {
        const run = K.run, car = K.car, GY = K.GY;
        // pickups: gas fills the tank, a glass-bottle soda = Feria, a taco = points + combo
        for (const c of K.picks) if (!c.got && c.x > car.x - 4 && c.x < car.x + 204 && c.h > car.y - 4 && c.h < car.y + 80) {
          const P = PICKS[c.kind] || {}; c.got = true; run.picks[c.kind] = (run.picks[c.kind] || 0) + 1;
          if (P.fuel) run.fuel = Math.min(1, run.fuel + P.fuel);
          if (P.feria) run.feria += P.feria;
          if (P.pts) run.score += P.pts * K.TIERS[run.tier].x;
          if (P.streak) { run.streak += P.streak; run.tier = K.tierOf(run.streak); run.bestTier = Math.max(run.bestTier, run.tier); run.maxStreak = Math.max(run.maxStreak, run.streak); }
          fxx("coin"); K.burst(c.x, GY - c.h, 8, "star", { sp: 110, life: 0.45 });
          K.pop(P.text || "+1", { x: c.x - K.camX, y: GY - c.h - 26, col: P.col || "#fff", size: 15, life: 0.9, rise: 26 });
        }
        // the tank drains with distance (faster at speed); empty = you coast to a stop and the run's over
        if (!run.out && !(run.chase && run.chase.party)) { run.fuel -= (car.v * dt) / (K.UPM * FUEL.range); if (run.fuel <= 0) { run.fuel = 0; run.out = true; car.charging = false; fxx("pumpStop"); K.pop("OUT OF GAS!", { x: K.LW / 2, y: Math.max(130, GY - 236), col: H.COL.orange, size: 30, big: true, life: 1.6, rise: 8 }); } }
        // the rare Trail Ride
        if (K.evOn && !K.ev && run.t > run.nextTrail) { run.nextTrail = run.t + E.every[0] + rand() * (E.every[1] - E.every[0]); if (rand() < E.chance && K.startEvent("trail")) { if (run.nextAbuela < run.t + 14) run.nextAbuela = run.t + 14; if (run.nextChancla < run.t + 12) run.nextChancla = run.t + 12; } }
      },
      tick(dt) {   // traffic rolls at you, wobbles, honks, talks when you get close
        const car = K.car, m = K.mode;
        for (const o of K.obs) if (o.T) {
          if (o.vx && !o.hit) o.x += o.vx * dt;
          const gap = o.x - (car.x + 200);
          if (!o.near && gap < 330 && gap > -40) { o.near = true; if (m === "run" || m === "title") { if (rand() < (o.T.talk == null ? 0.7 : o.T.talk)) say(o, "near"); if (!o.honked && rand() < (o.T.honk || 0)) { o.honked = true; fxx("honk", o.T.horn || 1); } if (o.T.scream && rand() < 0.8) fxx("scream"); if (o.T.cop && rand() < 0.5) fxx("chirp"); } }
        }
      },
      say, over(o) { const run = K.run; run.traffic++; if (o.T.cop) { run.cops++; K.st.totals.cops++; } say(o, "over"); },
      event(type) { return type === "trail" ? trail() : null; },
      hud(g, t, txt) {   // the gas gauge: a pump + a bar; it flashes when you're nearly out
        const run = K.run, C = H.COL, rr = H.rr, fx = 14, fy = 62, fw = 84, low = run.fuel < 0.25, on = !low || Math.floor(t * 4) % 2 === 0;
        g.fillStyle = "#fff"; rr(g, fx, fy - 1, 9, 12, 2); g.fill(); g.fillStyle = "#000"; g.fillRect(fx + 2, fy + 1, 5, 3); g.strokeStyle = "#fff"; g.lineWidth = 1.4; g.beginPath(); g.moveTo(fx + 9, fy + 2); g.lineTo(fx + 12, fy + 4); g.lineTo(fx + 12, fy + 9); g.stroke();
        g.fillStyle = "rgba(0,0,0,.6)"; rr(g, fx + 16, fy, fw, 10, 5); g.fill();
        if (run.fuel > 0) { g.fillStyle = low ? (on ? C.pink : "#7a0f3d") : run.fuel < 0.5 ? C.orange : C.turq; rr(g, fx + 16, fy, Math.max(8, fw * run.fuel), 10, 5); g.fill(); }
        g.strokeStyle = "#fff"; g.lineWidth = 1.2; rr(g, fx + 16, fy, fw, 10, 5); g.stroke();
        if (low && on) txt(run.out ? "OUT OF GAS" : "LOW GAS · GRAB A CAN", fx, fy + 22, 10, C.pink, "left", "#000", H.SANS, "900");
      },
    }, fxx);
  }

  LIB.stages.sa = { id: "sa", name: "San Antonio", back, lot, billboards, traffic: TRAFFIC, trafficRate, driver, drawTraffic, picks: PICKS, drawPick, fuel: FUEL, riders, horse, install, lapLabel: CHASE.lapLabel, CHASE,
    LANDMARKS, STORES, TAQS, COATS, DONATE };
})(window);
