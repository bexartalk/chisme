/* Chisme · Puro Pinche Lowrider · San Antonio chase + Hon Dipo party. // v49.26 */
(function (root) {
  "use strict";
  const LIB = root.ChismeLowrider; if (!LIB) return;
  LIB.saChase = function ({ TAU, box, poly, TRAFFIC, driver, drawTraffic, CHASE, PARTY_COL, BANNER_Y, partyState }) {
  let H = null;
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

  const ell = (g, col, x, y, rx, ry) => { g.fillStyle = col; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, TAU); g.fill(); };


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
      const B = K.bubbles; B.push({ p, text, t: 0, life: 1.8 }); if (B.length > 8) B.pop();
    }
    function party() {   // the finish: the car pulls in, the party, the cops give up and dance, then the ending card
      const car = K.car, run = K.run, x = car.x + 200 + Math.max(320, car.v * 2.2) + 120, keep = (c) => c.x < car.x + 200;
      K.obs = K.obs.filter((o) => o.x + o.w < car.x + 200); K.coins = K.coins.filter(keep); K.picks = K.picks.filter(keep);
      K.hold = 1e12; K.nextObs = 1e12; partyState.near = true;
      const P = CHASE.party, nc = Math.min(P.cops, Math.max(1, run.chase.n));
      const cops = run.chase.cars.slice(-nc).map((o, i) => ({ o, i, at: 0.5 + i * 0.55, sx: -220, hop: 0, said: false }));
      const R = Hk.rng ? Hk.rng(7) : rand, dancers = [];
      for (let i = 0; i < P.dancers; i++) { const back = i % 3 !== 2; dancers.push({ rel: 120 + i * 58 + (R() - 0.5) * 20, back, p: Hk.makePerson(R, 0, 0, { dance: true, kid: false, s: back ? 0.72 : 0.9 }) }); }
      const ev = { type: "party", stop: true, x, X0: x - 260, phase: "arrive", t: 0, pt: 0, hops: 0, cops, dancers,
        update(dt) {
          if (ev.phase === "arrive" && (K.car.v < 25 || ev.t > 6)) { ev.phase = "party"; ev.pt = 0; K.run.chase.party = "party";
            fxx("cheer"); K.burst(ev.x - 120, K.GY - 220, 26, "confetti", { sp: 240, life: 1.4 });
            // v49.26: the core HUD keeps the finish title visible throughout the party.
            K.sayLine("¡Llegaste!", "es-MX", { rate: 1, gap: 3000 }); }
          if (ev.phase !== "party") return; ev.pt += dt;
          for (const c of ev.cops) { const go = ev.pt - c.at; if (go <= 0) continue; c.sx = Math.min(c.i === 0 ? 228 : c.i === 1 ? 336 : c.i === 2 ? -40 : 440, -220 + go * 520);
            if (!c.said && go > 0.6) { c.said = true; const L = CHASE.give[c.i % CHASE.give.length], o = c, p = { get x() { return K.camX + o.sx + 60; }, y: K.GY - 4, s: 1 }; K.bubbles.push({ p, text: L, t: 0, life: 2 }); if (K.bubbles.length > 8) K.bubbles.pop(); fxx("chirp"); } }
          if (!partyState.lights && ev.pt > 3) { partyState.lights = true; fxx("cheer"); K.crowd(1, 0.8, "¡Ándale!"); }
          if (ev.pt > P.secs && ev.phase === "party") { ev.phase = "done"; done(ev); }
        },
        press() { if (ev.phase !== "party" || ev.hops >= 8) return; ev.hops++; const pts = 150 * K.TIERS[K.run.tier].x; K.run.score += pts;
          K.pop("+PARTY HOP " + K.num(pts), { x: K.LW / 2, y: Math.max(170, K.GY - 270) + (ev.hops % 2) * 26, col: Hk.COL.turq, size: 20, big: true, life: 1, rise: 14 }); fxx("oooh", 0.5); },
        auto(inRun) { const car = K.car; if (ev.phase === "party" && !car.charging && ev.hops < 3 && (ev.pt % 1.3) < 0.02) K.startCharge(); if (car.charging && car.charge > 0.45) inRun ? K.release() : K.launch(); return true; },
        draw(g, t, front) { if (!front) return; const rm = K.reduced(), GY = K.GY;   // the cops who came to arrest you and stayed to dance
          for (const c of ev.cops) { if (c.sx < -200) continue; const hop = partyState.lights && !rm ? Math.abs(Math.sin(t * 6 + c.i * 1.3)) * 12 : 0;
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
        const tx = 118 + (rm ? 0 : Math.sin(t * 0.8 + i * 2.1) * 150), col = atParty && partyState.lights ? PARTY_COL[(i * 2 + Math.floor(t * 2)) % 4] : CHASE.beam;
        g.save(); g.globalCompositeOperation = "lighter"; g.globalAlpha = atParty ? 0.22 : 0.16; g.fillStyle = Hk.lg(g, 0, hy, 0, GY + 20, [[0, col], [1, "rgba(0,0,0,0)"]]);
        g.beginPath(); g.moveTo(hx + 10, hy + 10); g.lineTo(tx - 46, GY + 22); g.lineTo(tx + 46, GY + 22); g.closePath(); g.fill();
        g.globalAlpha = atParty ? 0.2 : 0.14; g.fillStyle = col; g.beginPath(); g.ellipse(tx, GY + 6, 52, 12, 0, 0, TAU); g.fill(); g.restore();
        heli(g, hx, hy, h, t, rm); });
    }
    return Object.assign({}, base, {
      lapLabel: CHASE.lapLabel, bannerY: BANNER_Y,
      runStart(run) {
        const L = lapOf(run.lap); run.goal = L.miles * K.MILE; run.boost = L.boost; run.gasK = L.gas;
        run.chase = { n: 0, cars: [], joinT: 0, sayT: 5, heli: [], party: null }; partyState.near = false; partyState.lights = false; lastFin = null;
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
        if ((run.goal - run.meters) * K.UPM < CHASE.party.near) partyState.near = true;
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
          copsIn: ev && ev.type === "party" ? ev.cops.filter((q) => q.sx > -200).length : 0, partyLights: partyState.lights, boost: run.boost, gasK: run.gasK }; },
    });
  }

  return chaseKit;
  };
})(window);
