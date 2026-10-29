/* Chisme Puro Pinche Lowrider · v49.29 rides. Original cartoon art, no insignia.
   Shared frame: x 0..205; axle centers (42,-14), (160,-14), collision radius 14.
   Larger silhouettes grow upward; art never changes gameplay geometry. */
(function (root) {
  "use strict";
  const poly = (g, color, pts) => { g.fillStyle = color; g.beginPath(); pts.forEach(([x,y],i) => i ? g.lineTo(x,y) : g.moveTo(x,y)); g.closePath(); g.fill(); };
  const box = (g, color, x,y,w,h) => { g.fillStyle=color; g.fillRect(x,y,w,h); };
  const oval = (g,color,x,y,rx,ry) => { g.fillStyle=color; g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2); g.fill(); };
  const line = (g,color,w,pts) => { g.strokeStyle=color; g.lineWidth=w; g.lineCap="round"; g.lineJoin="round"; g.beginPath(); pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y)); g.stroke(); };

  // ---- v49.29.2 art kit: outlines, gradients, chrome, a tiny bitmap cache for heavy static parts
  const OL = "#1b1024";
  const lg = (g, x0, y0, x1, y1, st) => { const q = g.createLinearGradient(x0, y0, x1, y1); st.forEach(([a, c]) => q.addColorStop(a, c)); return q; };
  const rg = (g, x, y, r0, r1, st, fx, fy) => { const q = g.createRadialGradient(fx == null ? x : fx, fy == null ? y : fy, r0, x, y, r1); st.forEach(([a, c]) => q.addColorStop(a, c)); return q; };
  const trace = (g, pts) => { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); };
  const fo = (g, fill, lw = 1.3, stroke = OL) => { g.fillStyle = fill; g.fill(); if (lw) { g.strokeStyle = stroke; g.lineWidth = lw; g.lineJoin = "round"; g.lineCap = "round"; g.stroke(); } };
  const rrp = (g, x, y, w, h, r) => { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); };
  const circ = (g, x, y, r) => { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); };
  const chromeG = (g, y0, y1) => lg(g, 0, y0, 0, y1, [[0, "#ffffff"], [0.3, "#cfd8e2"], [0.52, "#66707c"], [0.75, "#e9eff5"], [1, "#8d97a3"]]);
  const goldG = (g, y0, y1) => lg(g, 0, y0, 0, y1, [[0, "#fff4c2"], [0.3, "#f2c04a"], [0.55, "#a8701a"], [0.8, "#ffd970"], [1, "#b47c22"]]);
  const glassG = (g, y0, y1) => lg(g, 0, y0, 0, y1, [[0, "#9fd6ff"], [0.45, "#2e5f8f"], [1, "#16253f"]]);
  const paintG = (g, P, y0, y1) => lg(g, 0, y0, 0, y1, [[0, P.hi], [0.18, P.mid], [0.55, P.base], [1, P.deep]]);
  const rand = (seed) => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const bitmaps = new Map();
  function cached(g, key, x, y, w, h, fn) {   // static art rendered once at 3x, then blitted every frame
    let c = bitmaps.get(key);
    if (!c) {
      const k = 3; c = typeof document !== "undefined" ? document.createElement("canvas") : new OffscreenCanvas(1, 1);
      c.width = Math.ceil(w * k); c.height = Math.ceil(h * k);
      const cg = c.getContext("2d"); cg.scale(k, k); cg.translate(-x, -y); fn(cg);
      if (bitmaps.size > 40) bitmaps.clear(); bitmaps.set(key, c);
    }
    g.drawImage(c, x, y, w, h);
  }
  const pkey = (id, P) => id + P.deep + P.base + P.mid + P.hi;
  function bell(g, x, y, s, swing) {   // a little brass bell hanging from (x, y)
    g.save(); g.translate(x, y); g.rotate(swing);
    g.strokeStyle = "#6b5a3a"; g.lineWidth = 0.8; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, 2 * s); g.stroke();
    g.beginPath(); g.moveTo(-1.2 * s, 2.6 * s); g.quadraticCurveTo(-1.6 * s, 5.5 * s, -3.4 * s, 7 * s); g.lineTo(3.4 * s, 7 * s); g.quadraticCurveTo(1.6 * s, 5.5 * s, 1.2 * s, 2.6 * s); g.quadraticCurveTo(0, 1.6 * s, -1.2 * s, 2.6 * s);
    fo(g, lg(g, -3.4 * s, 0, 3.4 * s, 0, [[0, "#a8701a"], [0.35, "#fff1b0"], [0.6, "#e7b23c"], [1, "#7a4c10"]]), 0.7);
    g.fillStyle = "#4a3210"; circ(g, Math.sin(swing * 3) * s, 7.6 * s, 0.9 * s); g.fill();
    g.restore();
  }
  function pickup(g,P,o,lift,noWheels) {
    const dy=lift==="monster"?-50:lift?-31:0;   // the lowrider pickup sits laid out over its wheels
    const ay=lift==="monster"?-28:-14;
    if (lift) {   // lift kit: chrome struts with pink coil springs, a crossmember
      line(g,"#363b4a",5,[[42,ay],[70,dy-16],[132,dy-16],[160,ay]]);
      for (const x of [42,160]) { line(g,OL,4.4,[[x,ay],[x,dy-14]]); line(g,"#d7dee6",2.6,[[x,ay],[x,dy-14]]);
        g.strokeStyle="#ff1a7f"; g.lineWidth=1.8; g.beginPath(); const n=7, y0=dy-14, y1=ay-6; for(let i=0;i<=n;i++){ g.lineTo(x+(i%2?4.5:-4.5),y0+(y1-y0)*i/n); } g.stroke(); }
    } else { g.fillStyle="#07060a"; g.beginPath(); g.arc(42,-14,16,Math.PI,0); g.arc(160,-14,16,Math.PI,0); g.fill(); }
    if (!noWheels) o.wheels();
    cached(g,pkey("pickup"+lift,P),-4,dy-100,214,96,(c)=>{
      c.translate(0,dy);
      const body=()=>{ c.beginPath(); c.moveTo(3,-15); c.lineTo(3,-44); c.lineTo(84,-44); c.lineTo(87,-46); c.lineTo(92,-74); c.quadraticCurveTo(93,-77,97,-77); c.lineTo(126,-77);
        c.quadraticCurveTo(131,-77,134,-73); c.lineTo(150,-50); c.lineTo(194,-46); c.quadraticCurveTo(203,-45,203,-37); c.lineTo(203,-15); c.lineTo(178,-15);
        c.arc(160,-14-dy*0,lift?18:17.5,0,Math.PI,true); c.lineTo(60,-15); c.arc(42,-14,lift?18:17.5,0,Math.PI,true); c.lineTo(3,-15); c.closePath(); };
      body(); fo(c,lg(c,0,-77,0,-15,[[0,P.hi],[0.12,P.mid],[0.42,P.base],[0.52,P.mid],[0.7,P.base],[1,P.deep]]),1.7);
      c.save(); body(); c.clip(); c.fillStyle="rgba(255,255,255,.35)"; c.beginPath(); c.ellipse(110,-41,96,1.6,0,0,TAU); c.fill();
      c.fillStyle="rgba(0,0,0,.18)"; c.fillRect(0,-24,210,10); c.restore();
      // pinstripe + body seams
      line(c,P.trim,0.9,[[6,-33],[200,-31]]); line(c,"#ff1a7f",0.6,[[6,-35],[200,-33]]);
      line(c,OL,1.1,[[86,-45],[86,-16]]); c.strokeStyle=OL; c.lineWidth=0.9; c.beginPath(); c.moveTo(92,-47); c.lineTo(92,-18); c.lineTo(144,-18); c.lineTo(147,-48); c.stroke();
      rrp(c,132,-41,9,2.2,1); fo(c,chromeG(c,-41,-38.8),0.5);
      // glass: rear cab window + door glass
      trace(c,[[95,-72],[125,-72],[143,-50],[95,-50]]); fo(c,glassG(c,-72,-50),1.2);
      c.save(); trace(c,[[95,-72],[125,-72],[143,-50],[95,-50]]); c.clip();
      c.fillStyle="#1d1420"; circ(c,112,-59,4.6); c.fill(); c.fillRect(106,-55,12,6); c.fillStyle="#151515"; c.fillRect(106,-64.5,11,2.4);
      c.fillStyle="rgba(255,255,255,.3)"; trace(c,[[102,-72],[110,-72],[97,-50],[95,-50],[95,-60]]); c.fill(); c.restore();
      line(c,"#20202a",1.6,[[126,-72],[124,-50]]);
      trace(c,[[145,-54],[151,-56],[151,-49],[145,-49]]); fo(c,chromeG(c,-56,-49),0.7);
      // bed rail, tailgate, taillight
      c.fillStyle=chromeG(c,-46,-42.5); c.fillRect(3,-46,82,3.4); c.strokeStyle=OL; c.lineWidth=0.7; c.strokeRect(3,-46,82,3.4);
      line(c,"rgba(27,16,36,.55)",0.9,[[8,-43],[8,-16]]);
      rrp(c,2.5,-42,4.5,13,1.2); fo(c,lg(c,0,-42,0,-29,[[0,"#ff6a6a"],[1,"#a50f1e"]]),0.7);
      // nose: billet grille, headlight, amber marker
      rrp(c,196,-44,8,20,2); fo(c,"#1e1e24",0.9); for(let y=-42;y<-25;y+=2.6) { c.fillStyle=chromeG(c,y,y+1.3); c.fillRect(197,y,6.5,1.2); }
      rrp(c,193,-44,10,6,2); fo(c,rg(c,198,-41,0.5,6,[[0,"#ffffff"],[0.6,"#dff3ff"],[1,"#8fb7d0"]]),0.8);
      rrp(c,186,-37,5,2.6,1); fo(c,"#ff9b2a",0.6);
      rrp(c,185,-21,23,7,2.5); fo(c,chromeG(c,-21,-14),1); rrp(c,-2,-20,14,6,2.5); fo(c,chromeG(c,-20,-14),1);
      c.strokeStyle=OL; c.lineWidth=1.8; for(const x of [42,160]) { c.beginPath(); c.arc(x,-14,lift?18:17.5,Math.PI,0); c.stroke(); }
      if (lift) { // mud flaps, roof light bar
        for (const x of [64,180]) { rrp(c,x-2,-22,4,12,1); fo(c,"#1d1d24",0.8); }
        rrp(c,96,-82,30,4,1.5); fo(c,"#2a2433",0.9); for(let i=0;i<5;i++){ c.fillStyle=rg(c,99+i*6,-80,0.3,2.6,[[0,"#ffffff"],[1,"#bfe6ff"]]); circ(c,99+i*6,-80,1.8); c.fill(); }
      }
    });
  }

  // ---- v49.29 the horse: original art, real proportions (withers ≈ body length ≈ 105, legs ≈ half the height,
  // head ≈ 0.4 of the height). Hooves land on the shared contact points (≈42 and ≈160, ground y = 0).
  const H = { coat: "#7a4a2e", dark: "#5a3420", hi: "#9a6240", mane: "#22140f", hoof: "#2b2622", sock: "#d9cfc6" };
  const TAU = Math.PI * 2;
  // one leg: from the top joint, segments with angles from straight-down (+ = toward the head)
  function leg(g, x, y, segs, w, col, sock) {
    const pts = [[x, y]];
    for (const [L, a] of segs) { x += L * Math.sin(a); y += L * Math.cos(a); pts.push([x, y]); }
    g.lineCap = "round"; g.lineJoin = "round"; g.strokeStyle = col;
    for (let i = 0; i < pts.length - 1; i++) { g.lineWidth = w[i]; g.beginPath(); g.moveTo(pts[i][0], pts[i][1]); g.lineTo(pts[i + 1][0], pts[i + 1][1]); g.stroke(); }
    const [jx, jy] = pts[pts.length - 2]; oval(g, col, jx, jy, w[w.length - 2] * 0.62, w[w.length - 2] * 0.62);   // fetlock
    if (sock) line(g, sock, w[w.length - 1] + 0.5, [pts[pts.length - 2], pts[pts.length - 1]]);
    const [hx, hy] = pts[pts.length - 1], ha = segs[segs.length - 1][1];
    g.save(); g.translate(hx, hy); g.rotate(-ha); g.fillStyle = H.hoof; g.beginPath(); g.moveTo(-3.6, -1); g.lineTo(4.2, -1); g.lineTo(5.6, 4); g.lineTo(-3.8, 4); g.closePath(); g.fill(); g.restore();
  }
  // gallop poses per leg (p = 0..1 through the stride). Front: forearm, cannon, pastern. Hind: gaskin, cannon, pastern.
  const STAND_F = [[27, 0.04], [24, 0], [8, 0.35]], STAND_H = [[28, -0.32], [27, 0.12], [8, 0.5]];
  function fore(p, air, idle) {
    if (idle) return STAND_F;
    if (air) return [[27, 1.05], [24, -0.55], [8, -0.2]];                     // tucked: knee up and forward, cannon folded back
    const sw = Math.sin(p * TAU), lift = Math.max(0, Math.sin(p * TAU + 1.2));
    const a1 = 0.55 * sw; return [[27, a1], [24, a1 - 1.5 * lift], [8, a1 - 1.5 * lift + 0.35 + 0.25 * lift]];
  }
  function hind(p, air, idle) {
    if (idle) return STAND_H;
    if (air) return [[28, -0.15], [27, 0.95], [8, 0.6]];                      // hocks flexed, hind legs tucked under
    const sw = Math.sin(p * TAU), lift = Math.max(0, Math.sin(p * TAU + 1.2));
    const a1 = -0.38 + 0.5 * sw; return [[28, a1], [27, a1 + 0.42 + 0.9 * lift], [8, a1 + 0.75 + 0.6 * lift]];
  }
  function drawHorse(g, o) {
    const air = !!o.air, idle = !!o.garage, t = o.t || 0;
    const p = idle ? 0.12 + Math.sin(t * 1.2) * 0.02 : ((o.rot || 0) * 0.16) % 1;   // the stride follows the rolling distance
    const rise = air || idle ? 0 : Math.abs(Math.sin(p * TAU)) * 2.4;            // the back rises and falls with the gallop
    g.save(); g.translate(0, -rise);
    const tw = Math.sin(t * 3.1) * 0.12 + (air ? -0.25 : 0);
    // tail: flowing back from the croup
    g.fillStyle = H.mane; g.beginPath(); g.moveTo(34, -98); g.bezierCurveTo(14, -96 + tw * 20, 4, -78, 10 + tw * 30, -50);
    g.bezierCurveTo(16, -66, 22, -80, 40, -88); g.closePath(); g.fill();
    line(g, "#3a241a", 1.4, [[30, -94], [14, -80 + tw * 10], [14 + tw * 26, -58]]);
    // far legs (darker), then the body, then the near legs
    const legs = (near) => {
      const c = near ? H.coat : H.dark, ps = near ? [p, p + 0.62] : [p + 0.1, p + 0.72];
      leg(g, 56, -72, hind(ps[0] % 1, air, idle), [10, 6, 4.6], c, near ? H.sock : null);
      leg(g, 148, -66, fore(ps[1] % 1, air, idle), [9, 5.4, 4.4], c, null);
    };
    legs(false);
    // body: hindquarters, barrel, deep chest; then neck + head
    g.fillStyle = H.coat; g.beginPath();
    g.moveTo(40, -96); g.bezierCurveTo(42, -112, 66, -112, 84, -104);              // croup to the back
    g.bezierCurveTo(104, -100, 118, -104, 130, -110);                               // back to the withers
    g.lineTo(166, -142); g.bezierCurveTo(172, -150, 182, -152, 188, -146);          // crest of the neck to the poll
    g.lineTo(202, -125); g.bezierCurveTo(209, -120, 207, -110, 198, -110);          // face to a rounded muzzle
    g.bezierCurveTo(192, -110, 186, -114, 180, -117); g.bezierCurveTo(170, -110, 162, -94, 160, -80);   // chin, jaw, a thick throat
    g.bezierCurveTo(158, -68, 150, -60, 140, -60);                                  // deep chest
    g.bezierCurveTo(116, -60, 92, -58, 70, -64);                                    // belly
    g.bezierCurveTo(56, -64, 44, -74, 40, -86); g.closePath(); g.fill();
    // shading: shoulder, hip, jowl
    const shade = (x, y, r, a) => { const gr = g.createRadialGradient(x - r * 0.3, y - r * 0.4, 1, x, y, r); gr.addColorStop(0, `rgba(176,118,80,${a})`); gr.addColorStop(1, "rgba(176,118,80,0)"); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); };
    shade(142, -88, 20, 0.55); shade(60, -92, 22, 0.55); shade(100, -96, 26, 0.25);
    oval(g, H.dark, 182, -126, 8, 6);
    line(g, H.dark, 1.3, [[70, -66], [100, -62], [128, -63]]);
    // head detail: nostril, eye, blaze
    oval(g, "#3a2219", 200, -117, 1.8, 1.4); oval(g, "#140c0a", 184, -138, 2.4, 2); oval(g, "#f3ece6", 184.6, -138.6, 0.7, 0.7);
    line(g, "#d9cfc6", 2, [[192, -141], [201, -124]]);
    // ears
    poly(g, H.dark, [[180, -147], [178, -160], [185, -149]]); poly(g, H.coat, [[184, -148], [186, -161], [189, -147]]);
    // mane: along the crest, flicking with the gallop
    g.fillStyle = H.mane; g.beginPath(); g.moveTo(182, -150); g.lineTo(178, -152);
    for (let i = 0; i <= 6; i++) { const u = i / 6, x = 178 - u * 48, y = -152 + u * 42; g.lineTo(x - 7 - Math.sin(t * 7 + i) * 2, y + 4 + (i % 2) * 3); g.lineTo(x - 2, y + 1); }
    g.lineTo(134, -106); g.lineTo(164, -138); g.closePath(); g.fill();
    oval(g, H.mane, 178, -149, 5, 3);   // forelock
    legs(true);
    // tack: reins + bridle
    line(g, "#2c1c22", 1.4, [[196, -118], [186, -134], [180, -144]]); line(g, "#2c1c22", 1.4, [[190, -128], [178, -122]]);
    // saddle + blanket
    poly(g, "#00a3a8", [[86, -104], [120, -106], [122, -88], [88, -86]]); line(g, "#ff1a7f", 2, [[88, -89], [121, -91]]);
    g.fillStyle = "#4a2a22"; g.beginPath(); g.moveTo(88, -104); g.bezierCurveTo(92, -112, 112, -112, 118, -108); g.lineTo(122, -118); g.lineTo(125, -116); g.lineTo(122, -104); g.closePath(); g.fill();
    line(g, "#3a1f18", 2, [[106, -104], [106, -82]]);   // the stirrup leather
    // the cowboy: upright torso, a leg down the horse's side, foot in the stirrup, hands on the reins
    const bounce = air ? -3 : idle ? 0 : Math.sin(p * TAU * 2) * 1.2;
    g.save(); g.translate(0, bounce);
    line(g, "#293858", 8, [[100, -112], [114, -100], [108, -82]]);   // thigh forward, shin down
    g.fillStyle = "#3a2620"; g.beginPath(); g.moveTo(104, -86); g.lineTo(114, -86); g.lineTo(119, -79); g.lineTo(104, -78); g.closePath(); g.fill();   // boot
    line(g, "#9aa3b5", 1.6, [[103, -78], [117, -78]]);   // stirrup
    poly(g, "#258997", [[94, -112], [108, -112], [110, -140], [96, -141]]);   // shirt
    line(g, "#1d6f7a", 6, [[106, -136], [118, -122], [128, -120]]);   // arm to the reins
    oval(g, "#c98f6a", 129, -120, 3, 2.6); line(g, "#2c1c22", 1.2, [[129, -120], [180, -144]]);
    line(g, "#d9cfc6", 2, [[96, -113], [109, -113]]);   // belt
    oval(g, "#c98f6a", 103, -148, 6.5, 7.5); line(g, "#c98f6a", 4, [[102, -141], [103, -144]]);
    oval(g, "#140c0a", 107, -149, 0.9, 0.9);
    g.fillStyle = "#473144"; g.beginPath(); g.moveTo(96, -153); g.bezierCurveTo(97, -165, 110, -165, 111, -153); g.closePath(); g.fill();   // crown
    g.beginPath(); g.ellipse(103, -153, 15, 3, 0, 0, TAU); g.fill();   // brim
    line(g, "#ff1a7f", 1.6, [[97, -155], [110, -155]]);   // hat band
    g.restore();
    g.restore();
  }

  // ---- v49.29 the jet's afterburner: layered flickering cone + an additive glow behind the nozzle (x≈4, y≈-37)
  function afterburner(g, o) {
    const t = o.t || 0, k = o.air ? 1 : o.garage ? 0.28 : 0.55;
    const f = 1 + Math.sin(t * 47) * 0.08 + Math.sin(t * 83 + 1) * 0.06, L = (22 + 46 * k) * f, nx = 4, ny = -37.5;
    g.save(); g.globalCompositeOperation = "lighter";
    const gl = g.createRadialGradient(nx - L * 0.35, ny, 2, nx - L * 0.35, ny, L * 0.9);
    gl.addColorStop(0, `rgba(255,106,11,${0.35 * k})`); gl.addColorStop(0.5, `rgba(79,140,255,${0.14 * k})`); gl.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gl; g.beginPath(); g.ellipse(nx - L * 0.35, ny, L * 0.9, 16 + 10 * k, 0, 0, TAU); g.fill();
    const cone = (len, half, col, a) => { g.globalAlpha = a; g.fillStyle = col; g.beginPath(); g.moveTo(nx, ny - half); g.quadraticCurveTo(nx - len * 0.55, ny - half * 0.9, nx - len, ny); g.quadraticCurveTo(nx - len * 0.55, ny + half * 0.9, nx, ny + half); g.closePath(); g.fill(); };
    cone(L, 5.2, "#ff4a1a", 0.75); cone(L * 0.72, 4.2, "#ff6a0b", 0.8); cone(L * 0.5, 3.3, "#4f8cff", 0.85); cone(L * 0.26, 2.2, "#ffffff", 0.95);
    for (let i = 1; i <= 3; i++) { g.globalAlpha = 0.5 * k; oval(g, "#7fb2ff", nx - L * (0.18 + i * 0.14), ny, 1.6, 2.6); }   // shock diamonds
    g.restore();
  }
  function marigold(g, x, y, r) {   // cempasúchil: ruffled orange petals, gold heart
    g.fillStyle = "#b8430a"; circ(g, x, y + r * 0.15, r); g.fill();
    for (let i = 0; i < 7; i++) { const a = i / 7 * TAU; g.fillStyle = i % 2 ? "#ff7a00" : "#ff9a1f"; circ(g, x + Math.cos(a) * r * 0.55, y + Math.sin(a) * r * 0.5, r * 0.55); g.fill(); }
    g.fillStyle = "#ffc23a"; circ(g, x - r * 0.1, y - r * 0.15, r * 0.45); g.fill(); g.fillStyle = "#c25500"; circ(g, x, y, r * 0.16); g.fill();
  }
  function paperFlower(g, x, y, r, col) {
    for (let i = 0; i < 6; i++) { const a = i / 6 * TAU; g.fillStyle = col; circ(g, x + Math.cos(a) * r * 0.6, y + Math.sin(a) * r * 0.6, r * 0.55); g.fill(); }
    g.strokeStyle = "rgba(27,16,36,.35)"; g.lineWidth = 0.5; circ(g, x, y, r * 1.1); g.stroke(); g.fillStyle = "#ffe36e"; circ(g, x, y, r * 0.35); g.fill();
  }
  // papel picado: flags on a sagging string, each with cut-outs (even-odd holes show what's behind)
  function papel(g, x0, x1, y, sag, n, cols, t) {
    const yAt = (x) => { const u = (x - x0) / (x1 - x0); return y + sag * 4 * u * (1 - u); };
    const fw = (x1 - x0) / n;
    for (let i = 0; i < n; i++) {
      const cx = x0 + fw * (i + 0.5), top = yAt(cx), w = fw * 0.84, h = fw * 0.95, sw = t == null ? 0 : Math.sin(t * 5 + i) * 0.08;
      g.save(); g.translate(cx, top); g.rotate(sw); g.beginPath();
      g.moveTo(-w / 2, 0); g.lineTo(w / 2, 0); g.lineTo(w / 2, h); for (let k = 0; k < 5; k++) { const xa = w / 2 - (k + 0.5) * w / 5, xb = w / 2 - (k + 1) * w / 5; g.lineTo(xa, h - w * 0.09); g.lineTo(xb, h); } g.closePath();
      const d = w * 0.13;   // a flower of four diamonds + a row of little triangles
      for (const [dx, dy] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) { const px = dx * d * 1.3, py = h * 0.5 + dy * d * 1.3; g.moveTo(px, py - d); g.lineTo(px + d * 0.7, py); g.lineTo(px, py + d); g.lineTo(px - d * 0.7, py); g.closePath(); }
      for (let k = 0; k < 3; k++) { const px = -w * 0.3 + k * w * 0.3; g.moveTo(px - d * 0.6, h * 0.16); g.lineTo(px + d * 0.6, h * 0.16); g.lineTo(px, h * 0.16 + d); g.closePath(); }
      g.fillStyle = cols[i % cols.length]; g.fill("evenodd"); g.strokeStyle = "rgba(27,16,36,.5)"; g.lineWidth = 0.5; g.stroke();
      g.restore();
    }
    g.strokeStyle = "#f4ecff"; g.lineWidth = 0.7; g.beginPath(); for (let x = x0; x <= x1; x += 4) g.lineTo(x, yAt(x)); g.stroke();
  }
  function candle(g, x, y, h, t, k) {   // a white candle with a flickering flame and glow
    rrp(g, x - 2.2, y - h, 4.4, h, 1); fo(g, lg(g, x - 2.2, 0, x + 2.2, 0, [[0, "#d8c9b8"], [0.4, "#fffaf0"], [1, "#cbb8a6"]]), 0.7);
    const f = Math.sin(t * 13 + k) * 0.6, fy = y - h - 1;
    g.save(); g.globalCompositeOperation = "lighter"; g.fillStyle = rg(g, x, fy - 3, 0, 9, [[0, "rgba(255,170,60,.45)"], [1, "rgba(255,120,20,0)"]]); circ(g, x, fy - 3, 9); g.fill(); g.restore();
    g.beginPath(); g.moveTo(x, fy - 7 - f); g.quadraticCurveTo(x + 2.6, fy - 2, x, fy); g.quadraticCurveTo(x - 2.6, fy - 2, x, fy - 7 - f); g.fillStyle = "#ff8a1f"; g.fill();
    g.fillStyle = "#fff6c8"; g.beginPath(); g.ellipse(x, fy - 2, 0.9, 2, 0, 0, TAU); g.fill();
  }
  function sugarSkull(g, x, y, s, accent) {   // an original calavera de azúcar, cheerful
    g.save(); g.translate(x, y); g.scale(s, s);
    g.beginPath(); g.moveTo(-9, -2); g.bezierCurveTo(-10, -15, 10, -15, 9, -2); g.quadraticCurveTo(9, 3, 5, 4); g.lineTo(5, 8); g.lineTo(-5, 8); g.lineTo(-5, 4); g.quadraticCurveTo(-9, 3, -9, -2); g.closePath();
    fo(g, rg(g, -2, -6, 1, 13, [[0, "#ffffff"], [1, "#e6dcef"]]), 1.1 / s);
    for (const ex of [-4, 4]) { g.fillStyle = accent; circ(g, ex, -2.5, 3.2); g.fill(); g.fillStyle = "#1b1024"; circ(g, ex, -2.5, 1.9); g.fill(); g.fillStyle = "#fff"; circ(g, ex + 0.6, -3.1, 0.6); g.fill(); }
    g.fillStyle = "#1b1024"; g.beginPath(); g.moveTo(0, 0.5); g.lineTo(1.2, 2.6); g.lineTo(-1.2, 2.6); g.closePath(); g.fill();
    g.strokeStyle = "#1b1024"; g.lineWidth = 0.5; for (let i = -4; i <= 4; i += 2) { g.beginPath(); g.moveTo(i, 4.5); g.lineTo(i, 7.5); g.stroke(); } g.beginPath(); g.moveTo(-5, 6); g.lineTo(5, 6); g.stroke();
    for (const [px, c] of [[-3, "#ff1a7f"], [0, "#00c9cd"], [3, "#ffb020"]]) { g.fillStyle = c; circ(g, px, -9.5, 1.2); g.fill(); }
    g.restore();
  }
  // Independent hop edges for Garage preview and gameplay.
  const fiestaPop = { garage: { air: false, start: -10, last: -1 }, game: { air: false, start: -10, last: -1 } };
  const draw = {
    paleta(g,P,o) {
      const t=o.t||0;
      o.wheels();
      line(g,"#2a2433",3.2,[[42,-14],[52,-30],[150,-30],[160,-14]]); line(g,P.trim,1.4,[[42,-14],[52,-30],[150,-30],[160,-14]]);
      cached(g,pkey("paleta",P),14,-160,196,136,(c)=>{
        // umbrella pole (behind the box)
        c.fillStyle=chromeG(c,-150,-70); c.fillRect(98.6,-150,2.8,80); c.strokeStyle=OL; c.lineWidth=0.6; c.strokeRect(98.6,-150,2.8,80);
        // freezer box: rounded, glossy, chrome bands
        rrp(c,22,-76,156,50,6); fo(c,paintG(c,P,-76,-26),1.6);
        rrp(c,34,-66,132,30,4); fo(c,lg(c,0,-66,0,-36,[[0,"#ffffff"],[0.6,"#eef3f8"],[1,"#c9d3de"]]),1.1);
        c.fillStyle=chromeG(c,-78,-72); rrp(c,18,-80,164,7,3); c.fill(); c.strokeStyle=OL; c.lineWidth=1.1; c.stroke();   // the lid lip
        rrp(c,30,-86,140,7,3); fo(c,lg(c,0,-86,0,-79,[[0,"#ffffff"],[1,"#cbd5df"]]),1.1);   // the freezer lid
        for(const x of [56,144]) { rrp(c,x-7,-89,14,3.5,1.5); fo(c,chromeG(c,-89,-85),0.8); }   // lid handles
        c.fillStyle=chromeG(c,-30,-25); c.fillRect(20,-30,160,4.5); c.strokeStyle=OL; c.lineWidth=0.9; c.strokeRect(20,-30,160,4.5);
        // painted paletas on the panel
        const fl=[["#ff3b6b","#ffd2de"],["#29c7a8","#c9fff1"],["#8a4bd8","#e8d6ff"],["#ff8a1f","#ffe0bf"],["#3aa0ff","#d4ecff"]];
        fl.forEach(([a,b],i)=>{ const x=46+i*24;
          c.fillStyle="#d8b27a"; c.fillRect(x+3,-50,3,7); c.strokeStyle="#8c6a3a"; c.lineWidth=0.5; c.strokeRect(x+3,-50,3,7);
          rrp(c,x-1,-64,11,16,4.5); fo(c,lg(c,x-1,0,x+10,0,[[0,a],[0.35,b],[1,a]]),0.9);
          c.fillStyle="rgba(255,255,255,.7)"; c.fillRect(x+1.5,-61,1.6,9); });
        c.fillStyle=P.deep; c.font="bold 7px sans-serif"; c.textAlign="center"; c.fillText("PALETAS",100,-37.5);
        for(const x of [26,174]) for(const y of [-71,-34]) { c.fillStyle=chromeG(c,y-1.5,y+1.5); circ(c,x,y,1.5); c.fill(); }   // rivets
        // push handle
        c.lineCap="round"; c.strokeStyle=OL; c.lineWidth=4.6; c.beginPath(); c.moveTo(178,-62); c.lineTo(194,-66); c.lineTo(200,-80); c.stroke();
        c.strokeStyle=chromeG(c,-82,-60); c.lineWidth=2.8; c.stroke();
        c.strokeStyle="#231a28"; c.lineWidth=5; c.beginPath(); c.moveTo(199,-77); c.lineTo(202,-85); c.stroke();
        // umbrella canopy: six striped panels with scalloped edges
        const cols=["#ff4b99","#ffffff","#00c9cd","#ffffff","#ffb020","#ffffff","#8a4bd8","#ffffff"], n=8, x0=26, x1=174, ay=-152, ry=-120;
        for(let i=0;i<n;i++) { const a=x0+(x1-x0)*i/n, b=x0+(x1-x0)*(i+1)/n;
          c.beginPath(); c.moveTo(100,ay); c.quadraticCurveTo(a+(100-a)*0.25,ay+8,a,ry); c.quadraticCurveTo((a+b)/2,ry+7,b,ry); c.quadraticCurveTo(b+(100-b)*0.25,ay+8,100,ay); c.closePath();
          c.fillStyle=cols[i]; c.fill(); }
        c.beginPath(); c.moveTo(100,ay); c.quadraticCurveTo(x0+18,ay+8,x0,ry); for(let i=0;i<n;i++){const a=x0+(x1-x0)*i/n,b=x0+(x1-x0)*(i+1)/n; c.quadraticCurveTo((a+b)/2,ry+7,b,ry);} c.quadraticCurveTo(x1-18,ay+8,100,ay); c.closePath();
        c.fillStyle=lg(c,0,ay,0,ry+6,[[0,"rgba(255,255,255,.35)"],[0.5,"rgba(255,255,255,0)"],[1,"rgba(40,0,40,.25)"]]); c.fill(); c.strokeStyle=OL; c.lineWidth=1.4; c.stroke();
        c.strokeStyle="rgba(27,16,36,.45)"; c.lineWidth=0.7; for(let i=1;i<n;i++){ const a=x0+(x1-x0)*i/n; c.beginPath(); c.moveTo(100,ay); c.quadraticCurveTo(a+(100-a)*0.25,ay+8,a,ry); c.stroke(); }
        c.fillStyle=goldG(c,-158,-151); circ(c,100,-155,3.2); c.fill(); c.strokeStyle=OL; c.lineWidth=0.8; c.stroke();
      });
      // bells on the handle, swinging with the ride
      const sw=Math.sin(t*9)*(o.air?0.5:0.22);
      line(g,"#6b5a3a",1,[[184,-66],[196,-69]]);
      bell(g,185,-66,1.7,sw); bell(g,194,-68,1.45,-sw*0.8);
      // umbrella fringe tassels
      for(let i=0;i<9;i++) { const x=27+i*18.4, s2=Math.sin(t*6+i)*1.2; line(g,"#ffe08a",0.8,[[x,-120],[x+s2,-115]]); oval(g,"#ffb020",x+s2,-114.5,1.1,1.4); }
      // a cold shine on the lid
      g.save(); g.globalAlpha=0.5+0.2*Math.sin(t*2); line(g,"#ffffff",1.2,[[40,-84],[90,-84]]); g.restore();
    },
    c10(g,P,o) {
      // Only the body leans: the standard contact centers stay fixed.
      g.fillStyle="#07060a"; g.beginPath(); g.arc(42,-14,16.5,Math.PI,0); g.arc(160,-14,16.5,Math.PI,0); g.fill();
      o.wheels();
      const lift=o.air?13:Math.max(0,Math.sin((o.rot||0)*0.7))*9;
      line(g,"#2a2433",3,[[42,-14],[48,-28],[151,-28-lift],[160,-14]]);
      g.save(); g.translate(42,-14); g.rotate(-lift/250); g.translate(-42,14);
      cached(g,pkey("c10",P),-4,-92,214,86,(c)=>{
        const body=()=>{ c.beginPath(); c.moveTo(3,-13); c.lineTo(3,-47); c.lineTo(93,-47); c.lineTo(96,-49); c.lineTo(98,-80); c.quadraticCurveTo(99,-83,103,-83); c.lineTo(130,-83);
          c.quadraticCurveTo(134,-83,136,-80); c.lineTo(147,-52); c.lineTo(196,-49); c.quadraticCurveTo(203,-48,203,-42); c.lineTo(203,-14); c.lineTo(178,-14);
          c.arc(160,-14,18,0,Math.PI,true); c.lineTo(60,-14); c.arc(42,-14,18,0,Math.PI,true); c.lineTo(3,-14); c.closePath(); };
        body(); fo(c,lg(c,0,-83,0,-13,[[0,P.mid],[0.38,P.base],[0.5,P.mid],[0.62,P.base],[1,P.deep]]),1.7);
        c.save(); body(); c.clip();
        // rough primer patches (flat, jagged edges) + rust freckles
        const R=rand(1067), patch=(col,cx,cy,rx,ry)=>{ c.beginPath(); for(let i=0;i<18;i++){ const a=i/18*Math.PI*2, k=0.78+R()*0.32; c.lineTo(cx+Math.cos(a)*rx*k,cy+Math.sin(a)*ry*k); } c.closePath(); c.fillStyle=col; c.fill(); };
        patch("#8e4a3c",168,-34,17,11); patch("#7a3a30",172,-30,8,5);
        patch("#3c4048",114,-24,15,7); patch("#5d636d",36,-34,19,8); patch("#9aa1ab",118,-76,10,4); patch("#4e535c",76,-22,10,6);
        for(let i=0;i<40;i++){ const x=6+R()*196, y=-46+R()*32; c.fillStyle=R()<0.5?"rgba(122,52,26,.7)":"rgba(70,40,30,.55)"; c.beginPath(); c.ellipse(x,y,0.5+R()*1.4,0.4+R()*0.9,0,0,6.3); c.fill(); }
        c.fillStyle="rgba(255,255,255,.18)"; c.fillRect(0,-47,210,3);   // the shoulder line highlight
        c.restore();
        // the beltline crease + bed/cab seam + door
        line(c,"rgba(27,16,36,.55)",1,[[4,-33],[202,-33]]); line(c,"rgba(255,255,255,.35)",0.8,[[4,-34.2],[202,-34.2]]);
        line(c,OL,1.2,[[95,-47],[95,-14]]);
        c.strokeStyle=OL; c.lineWidth=1; c.beginPath(); c.moveTo(100,-50); c.lineTo(100,-17); c.lineTo(141,-17); c.lineTo(143,-50); c.stroke();
        rrp(c,128,-44,9,2.2,1); fo(c,chromeG(c,-44,-41.8),0.5);   // door handle
        // the side glass + vent window, a driver in a ball cap
        trace(c,[[102,-78],[131,-78],[141,-53],[102,-53]]); fo(c,glassG(c,-78,-53),1.2);
        c.save(); trace(c,[[102,-78],[131,-78],[141,-53],[102,-53]]); c.clip();
        c.fillStyle="#2b1a14"; c.beginPath(); c.arc(116,-62,5,0,6.3); c.fill(); c.fillRect(110,-58,12,6); c.fillStyle="#151515"; c.beginPath(); c.ellipse(116,-66,5.4,2.4,0,3.1,6.3); c.fill(); c.fillRect(116,-67,7,1.4);
        c.fillStyle="rgba(255,255,255,.28)"; trace(c,[[108,-78],[116,-78],[104,-53],[102,-53],[102,-62]]); c.fill(); c.restore();
        line(c,"#2a2a30",1.6,[[132,-78],[127,-53]]);
        trace(c,[[143,-56],[149,-58],[149,-52],[143,-52]]); fo(c,chromeG(c,-58,-52),0.7);   // mirror
        // the bed: chrome rail, stake pockets, tailgate seam, fuel door
        c.fillStyle=chromeG(c,-49,-45.5); c.fillRect(3,-49,91,3.4); c.strokeStyle=OL; c.lineWidth=0.7; c.strokeRect(3,-49,91,3.4);
        for(const x of [20,50,80]) { c.fillStyle="#26242c"; c.fillRect(x,-45,3,3); }
        line(c,"rgba(27,16,36,.6)",0.9,[[8,-46],[8,-15]]); circ(c,70,-40,3.4); fo(c,"rgba(0,0,0,.12)",0.6);
        // nose: grille bars (no badge), headlight, marker, hood seam
        rrp(c,197,-46,7,22,2); fo(c,"#1e1e24",0.9); for(let y=-44;y<-25;y+=3) { c.fillStyle=chromeG(c,y,y+1.6); c.fillRect(198,y,5.5,1.5); }
        circ(c,202,-36,3.6); fo(c,rg(c,202,-36,0.5,3.6,[[0,"#ffffff"],[0.6,"#dff3ff"],[1,"#8fb7d0"]]),0.8);
        rrp(c,188,-43,6,3,1); fo(c,"#ff9b2a",0.6); line(c,"rgba(27,16,36,.5)",0.8,[[150,-50],[195,-47.5]]);
        rrp(c,3,-44,4,12,1); fo(c,lg(c,0,-44,0,-32,[[0,"#ff6a6a"],[1,"#a50f1e"]]),0.7);   // taillight
        // bumpers + exhaust
        rrp(c,186,-21,22,7,2.5); fo(c,chromeG(c,-21,-14),1); rrp(c,-2,-20,14,6,2.5); fo(c,chromeG(c,-20,-14),1);
        rrp(c,6,-13,16,3,1.4); fo(c,chromeG(c,-13,-10),0.6);
        // wheel-arch lips
        c.strokeStyle=OL; c.lineWidth=1.8; for(const x of [42,160]) { c.beginPath(); c.arc(x,-14,18,Math.PI,0); c.stroke(); }
      });
      g.restore();
    },
    raspa(g,P,o) {
      const t=o.t||0, colors=["#ff2948","#ff8a1f","#ffd23a","#20bd80","#00c9cd","#397bff","#993ede"], power=o.air?1:o.garage?0.35:0.6;
      // the rainbow trail: seven syrup ribbons rippling out of the nozzle
      g.save(); const L=50+60*power;
      for(let i=0;i<7;i++) {
        const y0=-55.5+i*3.2; g.beginPath(); g.moveTo(30,y0);
        for(let s=0;s<=10;s++){ const x=30-L*s/10, w=Math.sin(t*10-s*0.9+i*0.15)*(1.5+s*0.45)*power; g.lineTo(x,y0+w-s*0.18*(3-i)); }
        for(let s=10;s>=0;s--){ const x=30-L*s/10, w=Math.sin(t*10-s*0.9+i*0.15)*(1.5+s*0.45)*power; g.lineTo(x,y0+3.4+w-s*0.18*(3-i)); }
        g.closePath(); g.fillStyle=lg(g,30,0,30-L,0,[[0,colors[i]],[0.7,colors[i]],[1,"rgba(255,255,255,0)"]]); g.globalAlpha=0.92; g.fill();
      }
      g.globalAlpha=0.6*power; for(let i=0;i<6;i++){ const x=30-((t*90+i*19)%L), y=-50+Math.sin(i*2.1+t*4)*10; g.fillStyle="#ffffff"; circ(g,x,y,1+((i*7)%3)*0.4); g.fill(); }
      g.restore();
      o.wheels();
      line(g,"#2a2433",3.2,[[42,-14],[56,-32],[148,-32],[160,-14]]); line(g,P.trim,1.4,[[42,-14],[56,-32],[148,-32],[160,-14]]);
      cached(g,pkey("raspa",P),14,-112,192,86,(c)=>{
        // fins (behind) — top + belly
        trace(c,[[44,-62],[24,-90],[34,-91],[70,-62]]); fo(c,lg(c,0,-91,0,-62,[[0,"#ff4a6a"],[1,"#a3102c"]]),1.4);
        trace(c,[[46,-34],[26,-22],[36,-20],[68,-34]]); fo(c,lg(c,0,-34,0,-20,[[0,"#ff4a6a"],[1,"#a3102c"]]),1.2);
        // nozzle bell
        c.beginPath(); c.moveTo(38,-58); c.lineTo(26,-62); c.lineTo(26,-32); c.lineTo(38,-36); c.closePath(); fo(c,chromeG(c,-62,-32),1.3);
        line(c,"rgba(0,0,0,.35)",1,[[30,-60],[30,-34]]);
        // the syrup bottle strapped to the back (behind the fuselage top)
        rrp(c,58,-104,15,40,4); fo(c,lg(c,58,0,73,0,[[0,"#8c0a22"],[0.35,"#ff4d6a"],[0.6,"#e0193e"],[1,"#7a0a1e"]]),1.3);
        rrp(c,59,-92,13,15,2); fo(c,"#fffaf2",0.8); c.fillStyle="#ff2948"; c.beginPath(); c.moveTo(65.5,-89); c.quadraticCurveTo(69,-84,65.5,-81.5); c.quadraticCurveTo(62,-84,65.5,-89); c.fill();
        c.fillStyle="#3a2a30"; c.font="bold 2.9px sans-serif"; c.textAlign="center"; c.fillText("JARABE",65.5,-78.5);
        rrp(c,62,-110,7,7,1.5); fo(c,chromeG(c,-110,-103),0.8); trace(c,[[64,-110],[67,-110],[72,-116],[70,-117]]); fo(c,"#ffffff",0.7);   // pour spout
        c.fillStyle="rgba(255,255,255,.55)"; c.fillRect(60.5,-101,2,8);
        // the fuselage
        const fus=()=>{ c.beginPath(); c.moveTo(36,-64); c.lineTo(158,-64); c.bezierCurveTo(182,-64,198,-54,203,-47); c.bezierCurveTo(198,-40,182,-30,158,-30); c.lineTo(36,-30); c.quadraticCurveTo(31,-47,36,-64); c.closePath(); };
        fus(); fo(c,lg(c,0,-64,0,-30,[[0,P.hi],[0.2,P.mid],[0.55,P.base],[1,P.deep]]),1.7);
        c.save(); fus(); c.clip();
        c.fillStyle=lg(c,0,-64,0,-30,[[0,"#ffb0bd"],[0.3,"#ff3a5c"],[1,"#8a0b22"]]); c.fillRect(168,-70,40,46);   // candy-red nose cone
        c.fillStyle=chromeG(c,-64,-30); c.fillRect(163,-66,5,40); c.fillRect(48,-66,4,40);
        c.fillStyle="rgba(255,255,255,.45)"; c.beginPath(); c.ellipse(110,-58,60,2.4,0,0,6.3); c.fill();
        c.restore(); fus(); c.strokeStyle=OL; c.lineWidth=1.7; c.stroke();
        for(let x=58;x<160;x+=8) { c.fillStyle="rgba(27,16,36,.45)"; circ(c,x,-34,0.8); c.fill(); }
        // portholes
        for(const [x,r] of [[146,8],[124,5]]) { circ(c,x,-48,r+2); fo(c,chromeG(c,-48-r-2,-46+r),1.1); circ(c,x,-48,r); fo(c,glassG(c,-48-r,-48+r),0.8);
          c.fillStyle="rgba(255,255,255,.6)"; c.beginPath(); c.ellipse(x-r*0.35,-48-r*0.35,r*0.35,r*0.18,-0.6,0,6.3); c.fill(); }
        c.fillStyle="#f2c6a8"; circ(c,147,-47,3.6); c.fill(); c.fillStyle="#2a1a20"; circ(c,148.5,-48,0.7); c.fill(); c.strokeStyle="#2a1a20"; c.lineWidth=0.6; c.beginPath(); c.arc(148,-46.4,1.5,0.2,1.6); c.stroke();
        c.fillStyle="#2b1a14"; c.beginPath(); c.arc(146.6,-49,3.8,3.3,6.1); c.fill();
        // the raspa on top: a striped paper cup and a dome of shaved ice in three syrups
        trace(c,[[86,-88],[114,-88],[110,-63],[90,-63]]); fo(c,"#ffffff",1.3);
        c.save(); trace(c,[[86,-88],[114,-88],[110,-63],[90,-63]]); c.clip(); for(let x=80;x<120;x+=7){ c.fillStyle="#3aa0ff"; trace(c,[[x,-90],[x+3,-90],[x+1,-60],[x-2,-60]]); c.fill(); } c.restore();
        trace(c,[[86,-88],[114,-88],[110,-63],[90,-63]]); c.strokeStyle=OL; c.lineWidth=1.3; c.stroke();
        c.beginPath(); c.moveTo(84,-88); c.bezierCurveTo(82,-112,118,-112,116,-88); c.closePath(); fo(c,"#eaf6ff",1.3);
        c.save(); c.beginPath(); c.moveTo(84,-88); c.bezierCurveTo(82,-112,118,-112,116,-88); c.closePath(); c.clip();
        c.fillStyle="#ff2948"; c.fillRect(80,-112,14,26); c.fillStyle="#00c9cd"; c.fillRect(94,-112,12,26); c.fillStyle="#20bd80"; c.fillRect(106,-112,14,26);
        c.fillStyle=lg(c,0,-108,0,-88,[[0,"rgba(255,255,255,.65)"],[1,"rgba(255,255,255,0)"]]); c.fillRect(80,-112,40,26);
        const R=rand(77); for(let i=0;i<40;i++){ c.fillStyle="rgba(255,255,255,.85)"; circ(c,84+R()*32,-108+R()*20,0.5+R()*0.7); c.fill(); }
        c.restore(); c.beginPath(); c.moveTo(84,-88); c.bezierCurveTo(82,-112,118,-112,116,-88); c.strokeStyle=OL; c.lineWidth=1.3; c.stroke();
        line(c,OL,2.6,[[108,-102],[118,-111]]); line(c,"#ffb020",1.6,[[108,-102],[118,-111]]);   // a little spoon-straw
      });
      // a drip of syrup from the spout
      const d=(t*1.6)%1; oval(g,"#ff2948",71+d*1.5,-114+d*10,1.1,1.5);
    },
    bruja(g,P,o) {
      const t=o.t||0;
      for(const x of [42,160]) oval(g,"rgba(198,147,239,.55)",x,-1.5,10+Math.sin(t*5)*2,1.6);
      g.save(); g.translate(0,-4-Math.sin(t*3)*3);
      // flowing cape, behind everything
      const w=(k)=>Math.sin(t*6+k)*3*(o.air?1.5:1);
      g.beginPath(); g.moveTo(108,-84); g.bezierCurveTo(90,-86,70,-82+w(0),52,-76+w(1)); g.quadraticCurveTo(46,-70+w(2),50,-62+w(2));
      g.quadraticCurveTo(58,-66+w(3),64,-60+w(3)); g.quadraticCurveTo(72,-62+w(4),78,-56+w(4)); g.quadraticCurveTo(90,-58,100,-52); g.lineTo(110,-60); g.closePath();
      fo(g,lg(g,50,-80,110,-56,[[0,P.base],[0.6,P.deep],[1,P.deep]]),1.4);
      line(g,P.mid,1,[[100,-80],[70,-76+w(0.5)],[56,-70+w(1.5)]]);
      cached(g,"bruja-broom",0,-70,196,50,(c)=>{
        // the broom: a twisty wooden handle, bound bristles that fan out
        c.lineCap="round"; c.strokeStyle=OL; c.lineWidth=6; c.beginPath(); c.moveTo(44,-40); c.lineTo(192,-48); c.stroke();
        c.strokeStyle=lg(c,0,-47,0,-40,[[0,"#c48a5a"],[0.5,"#8a5232"],[1,"#5c3420"]]); c.lineWidth=4; c.stroke();
        for(let x=60;x<190;x+=12){ const y=-40-(x-44)*8/148; line(c,"rgba(60,30,15,.5)",0.7,[[x,y-1.8],[x+3,y+1.8]]); }
        circ(c,192,-48,3); fo(c,"#8a5232",1);
        c.beginPath(); c.moveTo(48,-46); c.quadraticCurveTo(20,-64,2,-62); c.lineTo(0,-22); c.quadraticCurveTo(22,-22,48,-35); c.closePath();
        fo(c,lg(c,0,-62,0,-22,[[0,"#f4cf7a"],[0.5,"#d9a24a"],[1,"#9c6a28"]]),1.4);
        const R=rand(9); for(let i=0;i<26;i++){ const a=i/25, y1=-62+a*40+(R()-0.5)*3; c.strokeStyle=i%3?"#a8742e":"#f8dc96"; c.lineWidth=0.8; c.beginPath(); c.moveTo(46,-45+a*10); c.quadraticCurveTo(24,-48+a*16,1+R()*3,y1); c.stroke(); }
        rrp(c,40,-48,9,15,2); fo(c,"#7b2cbf",1.1); line(c,"#ffd23a",1,[[42,-47],[42,-34]]); line(c,"#ffd23a",1,[[46.5,-47],[46.5,-34]]);
      });
      // body: dress + striped stockings + boots
      g.beginPath(); g.moveTo(104,-48); g.quadraticCurveTo(100,-70,108,-84); g.lineTo(122,-84); g.quadraticCurveTo(128,-66,132,-46); g.closePath(); fo(g,lg(g,100,0,132,0,[[0,P.deep],[0.5,P.base],[1,P.deep]]),1.4);
      line(g,OL,6.4,[[114,-47],[134,-44],[138,-30]]); line(g,"#f8f2ff",4.6,[[114,-47],[134,-44],[138,-30]]);
      for(let i=1;i<6;i++){ const u=i/6; const x=u<0.55?114+20*u/0.55:134+4*(u-0.55)/0.45, y=u<0.55?-47+3*u/0.55:-44+14*(u-0.55)/0.45; line(g,"#7b2cbf",1.6,[[x-1.5,y-1.5],[x+1.5,y+1.5]]); }
      g.beginPath(); g.moveTo(134,-31); g.lineTo(141,-31); g.quadraticCurveTo(149,-30,150,-24); g.lineTo(133,-24); g.closePath(); fo(g,"#3a2230",1.1);
      trace(g,[[102,-50],[134,-50],[134,-46],[102,-46]]); fo(g,P.mid,1);   // the skirt hem over the broom
      // arms to the broom
      line(g,OL,6,[[116,-80],[130,-62],[146,-50]]); line(g,P.base,4.4,[[116,-80],[130,-62],[146,-50]]);
      oval(g,"#f2c6a8",147,-49.5,3.2,3); g.strokeStyle=OL; g.lineWidth=0.8; g.stroke();
      // head: hair, friendly face
      g.beginPath(); g.moveTo(106,-100); g.bezierCurveTo(98,-92,100,-80,92,-72+w(2)*0.5); g.quadraticCurveTo(104,-76,110,-86); g.closePath(); fo(g,"#3a1d52",1.2);
      circ(g,118,-94,10.5); fo(g,rg(g,118,-94,2,11,[[0,"#ffe0cc"],[1,"#eab08e"]],115,-97),1.3);
      for(const x of [114,122.5]) { oval(g,"#ffffff",x,-95,2.6,3.1); oval(g,"#2a1a3a",x+0.5,-94.6,1.7,2.2); oval(g,"#ffffff",x+1.1,-95.6,0.7,0.7); }
      line(g,OL,0.9,[[111.5,-99.5],[115,-100.3]]); line(g,OL,0.9,[[121,-100.3],[124.5,-99.5]]);
      oval(g,"rgba(255,110,140,.45)",111.5,-90.5,2.2,1.4); oval(g,"rgba(255,110,140,.45)",125,-90.5,2.2,1.4);
      g.strokeStyle="#8a2a3a"; g.lineWidth=1.1; g.beginPath(); g.arc(119,-90,3.3,0.25,Math.PI-0.25); g.stroke();
      oval(g,"#e2a080",120.5,-92.4,1.1,0.9);
      // the pointed hat: wide brim, a bent tip, a band with a star buckle
      g.beginPath(); g.ellipse(118,-103,21,4.6,-0.06,0,TAU); fo(g,lg(g,0,-108,0,-98,[[0,P.mid],[1,P.deep]]),1.3);
      g.beginPath(); g.moveTo(106,-104); g.quadraticCurveTo(112,-124,112,-136); g.quadraticCurveTo(104,-142,96,-136); g.quadraticCurveTo(108,-130,110,-128); g.quadraticCurveTo(122,-118,130,-104); g.closePath();
      fo(g,lg(g,104,0,130,0,[[0,P.deep],[0.45,P.base],[1,P.deep]]),1.3);
      g.beginPath(); g.moveTo(107,-106); g.quadraticCurveTo(118,-104,129,-106.5); g.lineTo(128,-110); g.quadraticCurveTo(118,-108,108,-110); g.closePath(); fo(g,"#ff1a7f",0.8);
      poly(g,"#ffd23a",[[118,-111.5],[119,-109],[121.6,-108.8],[119.6,-107.2],[120.3,-104.6],[118,-106],[115.7,-104.6],[116.4,-107.2],[114.4,-108.8],[117,-109]]);
      oval(g,"#ffd23a",96,-136,1.8,1.8);
      // sparkles
      for(let i=0;i<6;i++) { const x=10+i*34,y=-60-((t*14+i*17)%44), a=0.5+0.5*Math.sin(t*8+i); g.globalAlpha=a; line(g,"#fff2a8",1.2,[[x-2.5,y],[x+2.5,y]]); line(g,"#fff2a8",1.2,[[x,y-2.5],[x,y+2.5]]); g.globalAlpha=1; }
      g.restore();
    },
    chariot(g,P,o) {
      const t=o.t||0;
      line(g,"#3a2a20",4.5,[[42,-14],[61,-36],[145,-36],[160,-14]]); line(g,"#e7b23c",2,[[42,-14],[61,-36],[145,-36],[160,-14]]);
      cached(g,pkey("chariot",P),14,-120,184,94,(c)=>{
        const shell=()=>{ c.beginPath(); c.moveTo(24,-30); c.lineTo(22,-66); c.quadraticCurveTo(24,-72,32,-70); c.quadraticCurveTo(70,-56,118,-58); c.bezierCurveTo(150,-60,160,-80,168,-96);
          c.quadraticCurveTo(178,-108,188,-96); c.quadraticCurveTo(190,-60,180,-30); c.closePath(); };
        shell(); fo(c,lg(c,0,-104,0,-30,[[0,P.hi],[0.2,P.mid],[0.55,P.base],[1,P.deep]]),1.8);
        c.save(); shell(); c.clip();
        // greek-key band in gold on a dark stripe
        c.fillStyle=P.deep; c.fillRect(20,-46,172,11); c.strokeStyle=goldG(c,-46,-35); c.lineWidth=1.2; c.lineJoin="miter";
        c.beginPath(); for(let x=22;x<190;x+=10){ c.moveTo(x,-37); c.lineTo(x,-44); c.lineTo(x+7,-44); c.lineTo(x+7,-39.5); c.lineTo(x+3,-39.5); c.lineTo(x+3,-41.5); c.moveTo(x+7,-37); c.lineTo(x+10,-37); } c.stroke();
        c.fillStyle=goldG(c,-48,-45); c.fillRect(20,-48,172,2); c.fillRect(20,-35,172,2);
        c.fillStyle="rgba(255,255,255,.25)"; c.beginPath(); c.ellipse(170,-86,4,12,-0.4,0,TAU); c.fill();
        c.restore();
        // gold rim along the top edge + the bottom
        c.beginPath(); c.moveTo(22,-66); c.quadraticCurveTo(24,-72,32,-70); c.quadraticCurveTo(70,-56,118,-58); c.bezierCurveTo(150,-60,160,-80,168,-96); c.quadraticCurveTo(178,-108,188,-96);
        c.strokeStyle=OL; c.lineWidth=5; c.lineCap="round"; c.stroke(); c.strokeStyle=goldG(c,-106,-56); c.lineWidth=3; c.stroke();
        c.fillStyle=goldG(c,-32,-27); c.fillRect(22,-32,160,4); c.strokeStyle=OL; c.lineWidth=0.8; c.strokeRect(22,-32,160,4);
        // a laurel sprig along the side
        c.strokeStyle="#2f6b2a"; c.lineWidth=1; c.beginPath(); c.moveTo(40,-52); c.quadraticCurveTo(90,-46,150,-54); c.stroke();
        for(let i=0;i<14;i++){ const u=i/13, x=40+u*110, y=-52+Math.sin(u*Math.PI)*(-3)+u*-2+6*u*(1-u)*1; for(const sd of [-1,1]){ c.save(); c.translate(x,y); c.rotate(sd*0.7-0.2); c.fillStyle=sd>0?"#4f9a3c":"#3b7f2e"; c.beginPath(); c.ellipse(3,0,3.6,1.3,0,0,TAU); c.fill(); c.restore(); } }
        // a gold medallion on the front guard
        circ(c,176,-68,9); fo(c,goldG(c,-77,-59),1.2); circ(c,176,-68,6); fo(c,P.deep,0.8);
        c.fillStyle=goldG(c,-73,-63); for(let i=0;i<8;i++){ const a=i/8*TAU; c.beginPath(); c.ellipse(176+Math.cos(a)*3,-68+Math.sin(a)*3,1.6,0.8,a,0,TAU); c.fill(); } circ(c,176,-68,1.4); c.fill();
      });
      // the charioteer: tunic, cape, a crested helmet, reins forward
      const b=o.air?-2:Math.sin(t*8)*0.8; g.save(); g.translate(0,b);
      g.beginPath(); g.moveTo(98,-62); g.quadraticCurveTo(80,-70+Math.sin(t*6)*3,70,-62+Math.sin(t*6+1)*3); g.lineTo(96,-58); g.closePath(); fo(g,"#c2185b",1.1);
      g.beginPath(); g.moveTo(96,-60); g.lineTo(98,-88); g.lineTo(118,-88); g.lineTo(122,-60); g.closePath(); fo(g,lg(g,96,0,122,0,[[0,"#e9e2f2"],[0.5,"#ffffff"],[1,"#c9bfd6"]]),1.2);
      line(g,goldG(g,-77,-73),2.2,[[97,-75],[121,-75]]);
      line(g,OL,5.6,[[116,-84],[134,-72],[154,-74]]); line(g,"#d79a78",4,[[116,-84],[134,-72],[154,-74]]);
      line(g,"#4a2a1a",1,[[156,-74],[196,-58]]);
      circ(g,110,-97,8.5); fo(g,rg(g,110,-97,1,9,[[0,"#f0bf98"],[1,"#c98a66"]],112,-99),1.2);
      oval(g,"#2a1a20",114,-98,1.1,1.3); g.strokeStyle="#7a3a2a"; g.lineWidth=0.9; g.beginPath(); g.arc(113,-93.5,2.2,0.3,1.8); g.stroke();
      g.beginPath(); g.moveTo(101,-96); g.quadraticCurveTo(100,-110,111,-110); g.quadraticCurveTo(121,-110,120,-99); g.lineTo(116,-100); g.lineTo(115,-94); g.lineTo(105,-92); g.closePath(); fo(g,goldG(g,-110,-92),1.2);
      g.beginPath(); g.moveTo(102,-108); g.quadraticCurveTo(108,-124,120,-112); g.quadraticCurveTo(112,-116,104,-104); g.closePath(); fo(g,"#d81b40",1);   // crest
      for(let i=0;i<5;i++) line(g,"#ff6a7f",0.6,[[104+i*3,-108-i*0.8],[107+i*3,-116+i*0.6]]);
      g.restore();
      // gold spoked wheels on the shared radius-14 envelope
      for(const x of [42,160]) {
        circ(g,x,-14,14); fo(g,rg(g,x,-14,8,14,[[0,"#3a2a20"],[1,"#120c0a"]]),1.2);
        g.strokeStyle=goldG(g,-26,-2); g.lineWidth=2.6; circ(g,x,-14,10.8); g.stroke(); g.strokeStyle=OL; g.lineWidth=0.6; circ(g,x,-14,12.2); g.stroke(); circ(g,x,-14,9.4); g.stroke();
        for(let i=0;i<8;i++) { const a=i*TAU/8+(o.rot||0); line(g,OL,2.4,[[x+2.5*Math.cos(a),-14+2.5*Math.sin(a)],[x+9.6*Math.cos(a),-14+9.6*Math.sin(a)]]); line(g,"#f2c04a",1.3,[[x+2.5*Math.cos(a),-14+2.5*Math.sin(a)],[x+9.6*Math.cos(a),-14+9.6*Math.sin(a)]]); }
        circ(g,x,-14,3.6); fo(g,goldG(g,-17.6,-10.4),0.8); g.fillStyle=OL; circ(g,x,-14,1.1); g.fill();
      }
    },
    ofrenda(g,P,o) {
      const t=o.t||0;
      o.wheels();
      cached(g,pkey("ofrenda",P),4,-160,200,140,(c)=>{
        // poles + papel picado across the top
        for(const x of [16,190]) { c.fillStyle=chromeG(c,-150,-40); c.fillRect(x-1.3,-150,2.6,112); c.strokeStyle=OL; c.lineWidth=0.6; c.strokeRect(x-1.3,-150,2.6,112); }
        papel(c,16,190,-148,10,9,["#ff1a7f","#00c9cd","#ffb020","#8a4bd8","#20bd80"]);
        // the trailer deck + skirt with fringe
        rrp(c,10,-40,186,10,2); fo(c,chromeG(c,-40,-30),1.3);
        c.beginPath(); c.moveTo(12,-31); c.lineTo(194,-31); c.lineTo(194,-22); for(let x=194;x>12;x-=7){ c.quadraticCurveTo(x-3.5,-17,x-7,-22); } c.closePath(); fo(c,lg(c,0,-31,0,-18,[[0,P.base],[1,P.deep]]),1.3);
        // three tiers dressed in cloth with lace edges
        const tier=(x0,x1,y0,y1)=>{ rrp(c,x0,y0,x1-x0,y1-y0,2); fo(c,lg(c,0,y0,0,y1,[[0,P.mid],[0.35,P.base],[1,P.deep]]),1.3);
          c.fillStyle="#fff6fb"; c.beginPath(); c.moveTo(x0,y0); for(let x=x0;x<x1-0.1;x+=5){ c.lineTo(x,y0+2); c.arc(x+2.5,y0+2,2.5,Math.PI,0,true); } c.lineTo(x1,y0); c.closePath(); c.fill(); c.strokeStyle="rgba(27,16,36,.35)"; c.lineWidth=0.5; c.stroke(); };
        tier(20,186,-62,-40); tier(44,162,-86,-62); tier(72,134,-108,-86);
        // marigold arch over the top tier
        c.lineWidth=2; c.strokeStyle="#2f6b2a"; c.beginPath(); c.moveTo(66,-86); c.bezierCurveTo(66,-140,140,-140,140,-86); c.stroke();
        for(let i=0;i<=16;i++){ const u=i/16, mt=1-u, x=mt*mt*mt*66+3*mt*mt*u*66+3*mt*u*u*140+u*u*u*140, y=mt*mt*mt*-86+3*mt*mt*u*-140+3*mt*u*u*-140+u*u*u*-86; marigold(c,x,y,4.2); }
        // photo frames with generic portraits, sugar skulls, pan de muerto
        for(const [x,col] of [[88,"#e7b23c"],[112,"#c0c8d4"]]) { rrp(c,x-9,-122,18,22,1.5); fo(c,goldG(c,-122,-100),1.1); c.fillStyle="#2a2440"; c.fillRect(x-6,-119,12,16);
          c.fillStyle=col==="#e7b23c"?"#8a6a8f":"#6a7a9a"; circ(c,x,-114,3); c.fill(); c.beginPath(); c.ellipse(x,-104.5,5,4,0,Math.PI,0); c.fill(); }
        sugarSkull(c,60,-72,1.05,"#ff1a7f"); sugarSkull(c,146,-72,1.05,"#00c9cd"); sugarSkull(c,103,-72,0.85,"#ffb020");
        c.beginPath(); c.ellipse(40,-66,9,5,0,Math.PI,0); fo(c,lg(c,0,-71,0,-66,[[0,"#e8a35a"],[1,"#a8622a"]]),1); line(c,"#c47a3a",1.6,[[33,-68],[47,-68]]); c.fillStyle="#fff5e0"; for(let i=0;i<6;i++){ circ(c,34+i*2.6,-70+((i%2)*1.2),0.5); c.fill(); }
        c.beginPath(); c.ellipse(166,-66,9,5,0,Math.PI,0); fo(c,lg(c,0,-71,0,-66,[[0,"#e8a35a"],[1,"#a8622a"]]),1); line(c,"#c47a3a",1.6,[[159,-68],[173,-68]]);
        // marigold garlands along each tier
        for(const [x0,x1,y] of [[22,184,-41],[46,160,-63],[74,132,-87]]) for(let x=x0+3;x<=x1-3;x+=6.5) marigold(c,x,y+Math.sin(x)*0.6,3.3);
        for(let x=14;x<=194;x+=7) marigold(c,x,-31,3);
      });
      // candles: flicker each frame
      for(const [x,y,h] of [[30,-62,9],[176,-62,9],[54,-86,8],[152,-86,8],[124,-108,7],[80,-108,7],[84,-62,6],[122,-62,6]]) candle(g,x,y,h,t,x);
      // petals drifting off on a hop
      if(o.air) for(let i=0;i<6;i++){ const x=30+i*28+Math.sin(t*3+i)*6, y=-130+((t*40+i*20)%90); g.fillStyle="#ff8a1f"; g.beginPath(); g.ellipse(x,y,1.8,1,t*4+i,0,TAU); g.fill(); }
    },
    fiesta(g,P,o) {
      const key=o.garage?"garage":"game", t=o.t||0, state=fiestaPop[key];
      if(t<state.last) { state.air=false; state.start=-10; }
      if(o.air&&!state.air) state.start=t;
      state.air=!!o.air; state.last=t;
      o.wheels();
      cached(g,pkey("fiesta",P),4,-160,200,140,(c)=>{
        // center mast + two strings of papel picado to the corner poles
        for(const x of [18,186]) { c.fillStyle=chromeG(c,-118,-40); c.fillRect(x-1.3,-118,2.6,78); c.strokeStyle=OL; c.lineWidth=0.6; c.strokeRect(x-1.3,-118,2.6,78); }
        c.fillStyle=chromeG(c,-150,-60); c.fillRect(100.7,-150,2.6,90); c.strokeStyle=OL; c.lineWidth=0.6; c.strokeRect(100.7,-150,2.6,90);
        papel(c,18,102,-118,-0,6,["#ff1a7f","#ffb020","#00c9cd","#8a4bd8"]); papel(c,102,186,-118,0,6,["#20bd80","#ff1a7f","#ffb020","#00c9cd"]);
        // balloons
        for(const [x,y,col] of [[34,-136,"#ff1a7f"],[46,-142,"#00c9cd"],[160,-140,"#ffb020"],[172,-134,"#8a4bd8"]]) {
          line(c,"#f4ecff",0.6,[[x,y+8],[x+(x<100?-10:10)*0+(x<100?-12:12),-118]]);
          c.beginPath(); c.ellipse(x,y,6,7.5,0,0,TAU); fo(c,rg(c,x,y,1,8,[[0,"#ffffff"],[0.25,col],[1,col]],x-2,y-3),1);
          poly(c,col,[[x-1.5,y+7.5],[x+1.5,y+7.5],[x,y+5.5]]);
        }
        // deck + rainbow fringe skirt
        rrp(c,10,-42,186,10,2); fo(c,chromeG(c,-42,-32),1.3);
        const fr=["#ff1a7f","#ffb020","#20bd80","#00c9cd","#8a4bd8"];
        for(let i=0;i<31;i++){ const x=12+i*6; c.fillStyle=fr[i%5]; c.fillRect(x,-33,6,12); c.fillStyle="rgba(27,16,36,.25)"; for(let k=1;k<6;k+=2) c.fillRect(x+k,-28,0.5,7); }
        c.strokeStyle=OL; c.lineWidth=1; c.strokeRect(12,-33,186,12);
        // the float body: painted panel + scallop trim
        rrp(c,16,-66,174,25,3); fo(c,lg(c,0,-66,0,-41,[[0,P.mid],[0.3,P.base],[1,P.deep]]),1.4);
        c.fillStyle="#fff6fb"; c.font="bold 11px sans-serif"; c.textAlign="center"; c.fillText("\u00a1FIESTA!",103,-49.5);
        c.strokeStyle=OL; c.lineWidth=0.6; c.strokeText("\u00a1FIESTA!",103,-49.5);
        // big paper flowers along the front
        const fc=["#ff1a7f","#ffb020","#00c9cd","#8a4bd8","#ff6a0b","#20bd80"];
        for(let i=0;i<6;i++) paperFlower(c,24+i*10,-66+(i%2)*2,4.6,fc[i]); for(let i=0;i<6;i++) paperFlower(c,132+i*10,-66+(i%2)*2,4.6,fc[5-i]);
        // the star piñata on the mast
        const sx=102, sy=-88; c.save(); c.translate(sx,sy);
        for(let i=0;i<7;i++){ const a=i/7*TAU-Math.PI/2; c.beginPath(); c.moveTo(Math.cos(a-0.32)*11,Math.sin(a-0.32)*11); c.lineTo(Math.cos(a)*27,Math.sin(a)*27); c.lineTo(Math.cos(a+0.32)*11,Math.sin(a+0.32)*11); c.closePath();
          fo(c,lg(c,Math.cos(a)*11,Math.sin(a)*11,Math.cos(a)*27,Math.sin(a)*27,[[0,fc[i%6]],[1,"#fff6fb"]]),1.1);
          line(c,fc[(i+2)%6],1.6,[[Math.cos(a)*27,Math.sin(a)*27],[Math.cos(a)*29,Math.sin(a)*29+8]]); }
        circ(c,0,0,13); fo(c,rg(c,0,0,2,13,[[0,"#fff2a8"],[1,"#ffb020"]],-3,-3),1.3);
        for(let i=0;i<10;i++){ const a=i/10*TAU; c.fillStyle=i%2?"#ff1a7f":"#00c9cd"; circ(c,Math.cos(a)*9,Math.sin(a)*9,1.4); c.fill(); }
        c.restore();
      });
      // confetti cannons (aim outward)
      for(const x of [40,164]) { const d=x<100?-1:1;
        g.save(); g.translate(x,-62); g.rotate(d*0.35); rrp(g,-5,-26,10,26,3); fo(g,lg(g,-5,0,5,0,[[0,"#2a2433"],[0.5,"#6b6478"],[1,"#2a2433"]]),1.2);
        rrp(g,-6,-28,12,4,1.5); fo(g,goldG(g,-28,-24),0.8); for(let k=0;k<3;k++){ g.fillStyle=["#ff1a7f","#00c9cd","#ffb020"][k]; g.fillRect(-5,-20+k*6,10,1.6);} g.restore(); }
      const age=t-state.start;
      if(age>=0&&age<0.6) {
        g.save(); g.globalAlpha=1-age/0.6;
        for(let i=0;i<32;i++) {
          const side=i%2, vx=Math.sin(i*2.4)*65, vy=55+(i%7)*10;
          const x=(side?173:31)+vx*age, y=-87-vy*age+100*age*age;
          g.save(); g.translate(x,y); g.rotate(i+age*9); box(g,["#ff1a7f","#00c9cd","#7b2cbf","#ff6a0b"][i%4],-2,-1,4,2); g.restore();
        }
        g.restore();
      }
      // the piñata sways a little
    },
    barge(g,P,o) {
      const t=o.t||0;
      cached(g,pkey("barge",P),0,-136,208,124,(c)=>{
        // canopy posts + arched roof with a painted name board
        for(const x of [34,158]) { rrp(c,x-2,-104,4,52,1); fo(c,lg(c,x-2,0,x+2,0,[[0,"#5a2a4a"],[0.5,"#b4769b"],[1,"#5a2a4a"]]),0.9); }
        c.beginPath(); c.moveTo(20,-102); c.quadraticCurveTo(96,-132,176,-102); c.lineTo(172,-96); c.quadraticCurveTo(96,-122,24,-96); c.closePath(); fo(c,lg(c,0,-124,0,-96,[[0,P.mid],[1,P.deep]]),1.4);
        rrp(c,52,-116,88,15,3); fo(c,"#fff3e6",1.2);
        c.fillStyle="#d81b60"; c.font="bold 10px sans-serif"; c.textAlign="center"; c.fillText("CALAVERA",96,-105);
        for(const x of [46,146]) paperFlower(c,x,-109,4.2,"#ff1a7f");
        for(let i=0;i<=12;i++){ const u=i/12, x=24+u*148, y=-96-26*4*u*(1-u)*0.95; marigold(c,x,y,2.8); }
        // the hull: painted planks, a gunwale, sweeping up to the prow
        const hull=()=>{ c.beginPath(); c.moveTo(4,-56); c.lineTo(10,-52); c.lineTo(176,-52); c.quadraticCurveTo(190,-54,202,-66); c.quadraticCurveTo(196,-30,170,-14); c.lineTo(34,-14); c.quadraticCurveTo(12,-28,4,-56); c.closePath(); };
        hull(); fo(c,P.base,1.8); c.save(); hull(); c.clip();
        const bands=["#ff1a7f","#ffb020","#00c9cd","#20bd80",P.deep]; bands.forEach((col,i)=>{ c.fillStyle=col; c.fillRect(0,-52+i*8,210,8); });
        c.fillStyle=lg(c,0,-56,0,-14,[[0,"rgba(255,255,255,.25)"],[0.4,"rgba(255,255,255,0)"],[1,"rgba(0,0,0,.35)"]]); c.fillRect(0,-70,210,60);
        for(let i=0;i<5;i++) line(c,"rgba(27,16,36,.4)",0.6,[[0,-44+i*8],[210,-44+i*8]]);
        for(let x=24;x<170;x+=24) paperFlower(c,x+8,-40,2.8,"#fff6fb");
        c.restore(); hull(); c.strokeStyle=OL; c.lineWidth=1.8; c.stroke();
        rrp(c,6,-58,172,6,2); fo(c,goldG(c,-58,-52),1.1);
        // the sugar-skull prow
        sugarSkull(c,188,-74,1.55,"#ff1a7f");
        for(let i=0;i<5;i++) marigold(c,176+i*5,-58-i*1.5,2.6);
      });
      // water: a deep band with moving ripples + sparkles (wheels are under the water line)
      g.save();
      g.fillStyle=lg(g,0,-14,0,2,[[0,"rgba(40,140,190,.85)"],[1,"rgba(20,60,110,.9)"]]); g.beginPath(); g.moveTo(-6,-12);
      for(let x=-6;x<=212;x+=6) g.lineTo(x,-12+Math.sin(x*0.15+t*4)*1.6); g.lineTo(212,1); g.lineTo(-6,1); g.closePath(); g.fill();
      g.strokeStyle="rgba(190,240,255,.85)"; g.lineWidth=1; g.beginPath(); for(let x=-6;x<=212;x+=6) g.lineTo(x,-12+Math.sin(x*0.15+t*4)*1.6); g.stroke();
      for(let r=0;r<3;r++){ g.strokeStyle=`rgba(160,230,255,${0.55-r*0.15})`; g.lineWidth=0.8; g.beginPath(); for(let x=0;x<206;x+=12){ const ox=(x+t*30*(r+1))%206; g.moveTo(ox,-8+r*3.2); g.quadraticCurveTo(ox+3,-9.6+r*3.2,ox+6,-8+r*3.2); } g.stroke(); }
      for(const x of [42,160]) for(let i=0;i<3;i++) oval(g,"#9fe9ff",x-8+i*8,-14-Math.abs(Math.sin(t*7+i+x))*5,1.4,1.8);
      g.restore();
      // candles along the gunwale
      for(const x of [24,58,96,134,166]) candle(g,x,-58,8,t,x);
    },
    lifted(g,P,o) { pickup(g,P,o,true); },
    lowtruck(g,P,o) { pickup(g,P,o,false); },
    monster(g,P,o) {
      // Big knobby tires: their bottoms touch the road exactly where the regular wheels do (contact geometry unchanged).
      pickup(g,P,o,"monster",true);
      for (const x of [42,160]) {
        circ(g,x,-28,28); fo(g,rg(g,x,-28,14,28,[[0,"#3a3c48"],[0.7,"#1c1d26"],[1,"#0b0c12"]]),1.6);
        g.save(); g.translate(x,-28); g.rotate(o.rot||0);
        for(let i=0;i<16;i++) { const a=i*TAU/16; g.save(); g.rotate(a); rrp(g,22.5,-3.4,6.5,6.8,1.6); fo(g,"#2a2c38",0.9); g.restore(); }   // tread lugs
        circ(g,0,0,15); fo(g,rg(g,-3,-4,1,15,[[0,"#ffffff"],[0.4,"#b8c2ce"],[0.8,"#5d6672"],[1,"#c9d2dc"]]),1.2);
        for(let i=0;i<6;i++){ g.save(); g.rotate(i*TAU/6); rrp(g,4,-1.8,9,3.6,1.6); fo(g,"#3a414c",0.5); g.restore(); }
        circ(g,0,0,4.2); fo(g,chromeG(g,-4,4),0.8); for(let i=0;i<6;i++){ g.fillStyle="#2a2f38"; circ(g,Math.cos(i*TAU/6)*2.6,Math.sin(i*TAU/6)*2.6,0.6); g.fill(); }
        g.restore();
        g.strokeStyle="rgba(255,255,255,.12)"; g.lineWidth=1.2; g.beginPath(); g.arc(x,-28,25,3.5,5.2); g.stroke();
      }
    },
    tank(g,P,o) {
      // Tread ends share the axle centers and retain the radius-14 contact envelope.
      const rot=o.rot||0;
      g.beginPath(); g.arc(42,-14,14,Math.PI/2,Math.PI*1.5); g.lineTo(160,-28); g.arc(160,-14,14,-Math.PI/2,Math.PI/2); g.closePath();
      fo(g,lg(g,0,-28,0,0,[[0,"#3a3f4c"],[0.5,"#1a1d27"],[1,"#0e1016"]]),1.6);
      const shift=(rot*4)%8;
      g.fillStyle="#6b7385"; for(let x=34+shift;x<168;x+=8) { g.fillRect(x,-28,4,2.6); g.fillRect(x,-2.6,4,2.6); }
      for(const x of [42,71,101,130,160]) { circ(g,x,-14,10.5); fo(g,rg(g,x-2,-16,1,10.5,[[0,P.hi],[0.4,P.mid],[1,P.deep]]),1.1); circ(g,x,-14,4.2); fo(g,"#2a2f3a",0.8);
        g.save(); g.translate(x,-14); g.rotate(rot); for(let i=0;i<5;i++){ g.fillStyle="#c9d2dc"; circ(g,Math.cos(i*TAU/5)*7,Math.sin(i*TAU/5)*7,0.9); g.fill(); } g.restore(); }
      cached(g,pkey("tank",P),2,-100,206,74,(c)=>{
        // hull with fenders, sloped glacis, tool box, rivets
        trace(c,[[6,-30],[18,-52],[160,-52],[194,-32],[190,-28],[10,-28]]); fo(c,lg(c,0,-52,0,-28,[[0,P.hi],[0.2,P.mid],[0.6,P.base],[1,P.deep]]),1.6);
        line(c,"rgba(255,255,255,.4)",1,[[20,-50],[158,-50],[190,-32]]);
        c.fillStyle="rgba(0,0,0,.2)"; c.fillRect(10,-34,180,4);
        for(let x=22;x<186;x+=10){ c.fillStyle="rgba(27,16,36,.5)"; circ(c,x,-32,0.9); c.fill(); }
        rrp(c,30,-48,26,10,1.5); fo(c,lg(c,0,-48,0,-38,[[0,P.mid],[1,P.deep]]),1); line(c,"#c9d2dc",1,[[34,-43],[52,-43]]);
        rrp(c,166,-46,10,5,1.5); fo(c,rg(c,171,-43.5,0.5,6,[[0,"#ffffff"],[1,"#9fd6ff"]]),0.8);   // headlight
        // turret, hatch, periscope, antenna
        c.beginPath(); c.moveTo(58,-52); c.lineTo(68,-74); c.quadraticCurveTo(98,-82,126,-74); c.lineTo(146,-52); c.closePath(); fo(c,lg(c,0,-80,0,-52,[[0,P.hi],[0.25,P.mid],[0.7,P.base],[1,P.deep]]),1.6);
        line(c,"rgba(255,255,255,.4)",1,[[72,-72],[124,-72]]);
        c.beginPath(); c.ellipse(92,-78,14,3.4,0,0,TAU); fo(c,lg(c,0,-81,0,-75,[[0,P.mid],[1,P.deep]]),1.1);
        rrp(c,86,-86,12,6,2); fo(c,P.base,1); rrp(c,108,-84,6,6,1); fo(c,"#2a2f3a",0.9); c.fillStyle="#9fd6ff"; c.fillRect(109,-82,4,2);
        line(c,OL,1.6,[[70,-74],[64,-98]]); line(c,"#c9d2dc",0.9,[[70,-74],[64,-98]]); c.fillStyle="#ff1a7f"; circ(c,64,-98,1.6); c.fill();
        // the barrel + muzzle brake
        rrp(c,140,-68,56,8,3); fo(c,lg(c,0,-68,0,-60,[[0,P.hi],[0.35,P.mid],[1,P.deep]]),1.3);
        rrp(c,138,-70,10,12,2); fo(c,P.base,1.1); rrp(c,192,-70,12,12,2); fo(c,chromeG(c,-70,-58),1.2); c.fillStyle="#1b1024"; c.fillRect(196,-66,3,4);
      });
    },
    jet(g,P,o) {
      afterburner(g,o);
      // landing gear struts to the shared wheels
      for(const x of [42,160]) { line(g,OL,5,[[x,-14],[x+(x<100?6:-6),-34]]); line(g,"#c9d2dc",3,[[x,-14],[x+(x<100?6:-6),-34]]); }
      o.wheels();
      cached(g,pkey("jet",P),0,-100,208,82,(c)=>{
        // tail fin + far wing (behind the fuselage)
        trace(c,[[8,-44],[16,-94],[30,-94],[50,-48]]); fo(c,lg(c,0,-94,0,-44,[[0,P.hi],[0.3,P.mid],[1,P.deep]]),1.5);
        line(c,"rgba(255,255,255,.45)",1,[[18,-90],[28,-90]]); trace(c,[[19,-80],[27,-80],[34,-64],[24,-64]]); fo(c,"#ff1a7f",0);
        trace(c,[[86,-46],[118,-70],[132,-70],[126,-46]]); fo(c,P.deep,1.2);
        // fuselage
        const fus=()=>{ c.beginPath(); c.moveTo(6,-44); c.lineTo(40,-50); c.lineTo(140,-50); c.bezierCurveTo(170,-49,192,-42,206,-36); c.bezierCurveTo(192,-31,170,-28,140,-28); c.lineTo(30,-29); c.lineTo(6,-32); c.closePath(); };
        fus(); fo(c,lg(c,0,-50,0,-28,[[0,P.hi],[0.18,P.mid],[0.55,P.base],[1,P.deep]]),1.7);
        c.save(); fus(); c.clip();
        c.fillStyle="#2a2f3a"; c.fillRect(176,-50,40,30); c.fillStyle="rgba(255,255,255,.35)"; c.beginPath(); c.ellipse(186,-41,10,1.2,-0.1,0,TAU); c.fill();   // dark radome
        line(c,"rgba(27,16,36,.4)",0.6,[[60,-50],[60,-28]]); line(c,"rgba(27,16,36,.4)",0.6,[[100,-50],[100,-28]]); line(c,"rgba(27,16,36,.4)",0.6,[[140,-50],[140,-28]]);
        c.fillStyle="#ff1a7f"; c.fillRect(30,-40,150,2); c.fillStyle="#00c9cd"; c.fillRect(30,-38,150,1.2);
        c.restore(); fus(); c.strokeStyle=OL; c.lineWidth=1.7; c.stroke();
        // intake
        trace(c,[[96,-40],[124,-40],[128,-32],[100,-32]]); fo(c,lg(c,0,-40,0,-32,[[0,"#1b1024"],[1,"#3a3f4c"]]),1);
        // near wing + missiles-free wingtip lights
        trace(c,[[70,-36],[116,-36],[154,-20],[132,-18]]); fo(c,lg(c,0,-36,0,-18,[[0,P.mid],[1,P.deep]]),1.4);
        circ(c,150,-20,1.6); fo(c,"#20bd80",0.4);
        // canopy: glass bubble with a frame + pilot helmet
        c.beginPath(); c.moveTo(118,-50); c.bezierCurveTo(124,-68,150,-68,166,-48); c.closePath(); fo(c,glassG(c,-66,-48),1.4);
        c.save(); c.beginPath(); c.moveTo(118,-50); c.bezierCurveTo(124,-68,150,-68,166,-48); c.closePath(); c.clip();
        c.fillStyle="#f2f2f6"; circ(c,138,-55,5.2); c.fill(); c.fillStyle="#1b1024"; rrp(c,139,-58,6,3.2,1.4); c.fill(); c.fillStyle="#ff1a7f"; c.fillRect(132,-61,12,1.6);
        c.fillStyle="rgba(255,255,255,.45)"; c.beginPath(); c.ellipse(134,-62,10,2,-0.3,0,TAU); c.fill(); c.restore();
        line(c,"#2a2f3a",1.6,[[146,-63],[148,-49]]);
        // nozzle
        rrp(c,1,-44,10,12,2); fo(c,chromeG(c,-44,-32),1.1); c.fillStyle="#101624"; c.fillRect(1,-41,3,6);
      });
    },
    horse(g,P,o) { drawHorse(g,o); }
  };
  const truck = ({nz,osc,t,out},p) => { nz(t,0.36,0.3,out,"lowpass",1500,0.8,0.004,350); osc("sine",100,t,0.24,0.55*p,out,0.003,40); };
  const sound = {
    paleta({osc,t,out},p) {
      for(let i=0;i<4;i++) { const f=[1318.51,1567.98,1975.53,1567.98][i], at=t+i*0.075; osc("sine",f,at,0.42,0.12*(0.6+p*0.4),out,0.002); osc("sine",f*2.76,at,0.16,0.035,out,0.001); }
    },
    c10({osc,nz,t,out},p) {
      osc("sine",110,t,0.32,0.55*p,out,0.003,38);
      for(const d of [0,0.07,0.15]) { nz(t+d,0.06,0.12,out,"bandpass",1100,1.8); osc("triangle",170,t+d,0.055,0.08,out,0.002,70); }
    },
    raspa({osc,nz,t,out},p) {
      nz(t,0.5,0.32*(0.5+p*0.5),out,"highpass",1300,0.7,0.035,5800);
      nz(t+0.02,0.36,0.15,out,"bandpass",2600,2,0.015,550);
      osc("sine",240,t,0.3,0.1,out,0.025,680);
    },
    bruja({osc,nz,t,out},p) {
      for(let i=0;i<5;i++) { const f=[523.25,659.25,783.99,1046.5,1318.51][i]; osc("sine",f,t+i*0.055,0.26,0.1*(0.65+p*0.35),out,0.008); osc("triangle",f*2,t+i*0.055,0.13,0.018,out,0.006); }
      nz(t,0.4,0.14,out,"bandpass",700,0.8,0.04,3200);
    },
    chariot({osc,nz,t,out},p) {
      for(const [f,v] of [[330,0.18],[557,0.1],[901,0.065],[1423,0.04]]) osc("sine",f,t,0.42,v,out,0.002);
      osc("sine",85,t,0.3,0.55*p,out,0.003,35); nz(t,0.055,0.12,out,"highpass",1800);
    },
    ofrenda({osc,t,out},p) {
      for(let i=0;i<3;i++) { const f=[523.25,659.25,783.99][i], at=t+i*0.105; osc("sine",f,at,0.25,0.16*(0.6+p*0.4),out,0.003); osc("sine",f*4,at,0.065,0.035,out,0.001); }
    },
    fiesta({osc,nz,t,out},p) {
      for(const d of [0,0.085]) { nz(t+d,0.055,0.24,out,"bandpass",2200,0.7,0.001,650); osc("sine",200,t+d,0.065,0.28*p,out,0.001,55); }
      nz(t+0.08,0.34,0.17,out,"highpass",1900,0.8,0.015,4500);
    },
    barge({osc,nz,t,out},p) {
      osc("sine",185,t,0.17,0.28*p,out,0.002,95); osc("triangle",370,t,0.085,0.1,out,0.001,210);
      nz(t+0.025,0.36,0.22,out,"lowpass",2100,0.8,0.012,450);
      for(let i=0;i<3;i++) osc("sine",700+i*190,t+0.07+i*0.05,0.075,0.035,out,0.005,350+i*90);
    },
    lifted: truck, lowtruck: truck,
    monster({osc,nz,t,out},p) { osc("sine",85,t,0.42,0.9*p,out,0.003,30); nz(t,0.24,0.3,out,"lowpass",650); },
    tank({osc,nz,t,out},p) { for(const f of [390,713,1127]) osc("triangle",f,t,0.19,0.09,out,0.002); osc("sine",65,t,0.4,0.65*p,out,0.004,32); nz(t,0.28,0.2,out,"lowpass",280); },
    jet({nz,t,out},p) { nz(t,0.4,0.4*(0.5+p*0.5),out,"bandpass",3200,0.7,0.015,300); },
    horse({osc,nz,t,out}) { for(const d of [0,0.085]) { osc("triangle",540,t+d,0.045,0.15,out,0.002,170); nz(t+d,0.025,0.15,out,"bandpass",1700,2); } osc("triangle",740,t+0.12,0.19,0.045,out,0.015,1150,0.13); }
  };
  root.ChismeLowriderRides = { draw, sound };
})(typeof window !== "undefined" ? window : globalThis);
