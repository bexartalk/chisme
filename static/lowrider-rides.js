/* Chisme Puro Pinche Lowrider · v49.29 rides. Original cartoon art, no insignia.
   Shared frame: x 0..205; axle centers (42,-14), (160,-14), collision radius 14.
   Larger silhouettes grow upward; art never changes gameplay geometry. */
(function (root) {
  "use strict";
  const poly = (g, color, pts) => { g.fillStyle = color; g.beginPath(); pts.forEach(([x,y],i) => i ? g.lineTo(x,y) : g.moveTo(x,y)); g.closePath(); g.fill(); };
  const box = (g, color, x,y,w,h) => { g.fillStyle=color; g.fillRect(x,y,w,h); };
  const oval = (g,color,x,y,rx,ry) => { g.fillStyle=color; g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2); g.fill(); };
  const line = (g,color,w,pts) => { g.strokeStyle=color; g.lineWidth=w; g.lineCap="round"; g.lineJoin="round"; g.beginPath(); pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y)); g.stroke(); };
  function pickup(g,P,o,lift,noWheels) {
    const y=lift==="monster"?-62:lift?-43:-12;   // the lowrider pickup sits laid out over its wheels
    if (lift) line(g,"#363b4a",5,[[42,-14],[64,y-5],[143,y-5],[160,-14]]);
    if (!noWheels) o.wheels();
    poly(g,P.deep,[[3,y-8],[7,y-34],[76,y-34],[87,y-69],[132,y-69],[151,y-34],[196,y-29],[202,y-6]]);
    poly(g,P.base,[[5,y-10],[9,y-31],[79,y-31],[90,y-66],[130,y-66],[149,y-31],[197,y-26],[200,y-10]]);
    box(g,P.mid,9,y-31,68,17); box(g,P.deep,15,y-35,58,4);
    poly(g,"#173647",[[86,y-33],[94,y-61],[126,y-61],[140,y-33]]);
    line(g,P.trim,2,[[111,y-60],[111,y-34]]);
    line(g,P.hi,2,[[8,y-12],[197,y-12]]); box(g,P.trim,116,y-27,11,2);
    box(g,P.trim,1,y-10,17,5); box(g,P.trim,185,y-10,18,5);
    box(g,"#eef7ff",186,y-26,12,7); box(g,"#ff3c64",5,y-28,5,9);
    line(g,P.deep,1,[[80,y-30],[80,y-12],[146,y-12],[146,y-30]]);
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
  const draw = {
    lifted(g,P,o) { pickup(g,P,o,true); },
    lowtruck(g,P,o) { pickup(g,P,o,false); },
    monster(g,P,o) {
      // Big knobby tires: their bottoms touch the road exactly where the regular wheels do (contact geometry unchanged).
      line(g,"#363b4a",6,[[42,-28],[70,-66],[140,-66],[160,-28]]);
      for (const x of [42,160]) {
        oval(g,"#12131c",x,-28,28,28); oval(g,"#2a2c38",x,-28,20,20); oval(g,"#9aa3b5",x,-28,9,9);
        for(let i=0;i<12;i++) { const a=i*Math.PI/6+(o.rot||0); line(g,"#3e4050",4,[[x+24*Math.cos(a),-28+24*Math.sin(a)],[x+29*Math.cos(a),-28+29*Math.sin(a)]]); }
      }
      pickup(g,P,o,"monster",true);
      line(g,P.trim,4,[[71,-98],[77,-123],[134,-123],[142,-98]]);
      box(g,"#e4f6ff",84,-128,13,5); box(g,"#e4f6ff",114,-128,13,5);
    },
    tank(g,P,o) {
      // Tread ends share the axle centers and retain the radius-14 contact envelope.
      oval(g,"#181c29",42,-14,14,14); oval(g,"#181c29",160,-14,14,14);
      box(g,"#181c29",42,-28,118,28);
      for(let x=32;x<173;x+=12) { const shift=((o.rot||0)*4)%12; box(g,"#7b8597",x+shift,-26,5,3); box(g,"#7b8597",x+shift,-5,5,3); }
      for(const x of [42,71,101,130,160]) { oval(g,P.deep,x,-14,10,10); oval(g,P.mid,x,-14,6,6); }
      poly(g,P.base,[[8,-30],[21,-51],[158,-51],[190,-31]]);
      line(g,P.hi,2,[[24,-48],[157,-48],[183,-33]]);
      poly(g,P.mid,[[60,-51],[71,-75],[125,-75],[147,-51]]);
      box(g,P.deep,126,-68,76,10); box(g,P.trim,195,-67,8,8);
      oval(g,P.deep,96,-76,22,4); box(g,"#b8c6da",43,-43,17,5);
    },
    jet(g,P,o) {
      afterburner(g,o);
      o.wheels();
      line(g,P.trim,4,[[42,-14],[42,-42],[160,-42],[160,-14]]);
      poly(g,P.deep,[[5,-40],[14,-93],[32,-93],[49,-49],[141,-49],[202,-35],[164,-26],[33,-28]]);
      poly(g,P.base,[[5,-40],[39,-50],[145,-48],[202,-35],[159,-29],[32,-31]]);
      poly(g,P.mid,[[72,-42],[104,-86],[124,-86],[114,-43],[153,-19],[119,-22]]);
      poly(g,"#163b59",[[108,-50],[120,-68],[143,-65],[162,-46]]);
      line(g,P.hi,2,[[121,-65],[141,-63],[155,-49]]);
      box(g,"#101624",5,-42,16,9); box(g,P.trim,3,-40,4,5);
      line(g,P.hi,2,[[37,-34],[97,-34]]);
    },
    horse(g,P,o) { drawHorse(g,o); }
  };
  const truck = ({nz,osc,t,out},p) => { nz(t,0.36,0.3,out,"lowpass",1500,0.8,0.004,350); osc("sine",100,t,0.24,0.55*p,out,0.003,40); };
  const sound = {
    lifted: truck, lowtruck: truck,
    monster({osc,nz,t,out},p) { osc("sine",85,t,0.42,0.9*p,out,0.003,30); nz(t,0.24,0.3,out,"lowpass",650); },
    tank({osc,nz,t,out},p) { for(const f of [390,713,1127]) osc("triangle",f,t,0.19,0.09,out,0.002); osc("sine",65,t,0.4,0.65*p,out,0.004,32); nz(t,0.28,0.2,out,"lowpass",280); },
    jet({nz,t,out},p) { nz(t,0.4,0.4*(0.5+p*0.5),out,"bandpass",3200,0.7,0.015,300); },
    horse({osc,nz,t,out}) { for(const d of [0,0.085]) { osc("triangle",540,t+d,0.045,0.15,out,0.002,170); nz(t+d,0.025,0.15,out,"bandpass",1700,2); } osc("triangle",740,t+0.12,0.19,0.045,out,0.015,1150,0.13); }
  };
  root.ChismeLowriderRides = { draw, sound };
})(typeof window !== "undefined" ? window : globalThis);
