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
    horse(g,P,o) {
      const rot=o.rot||0;
      // Knees swing with wheel rotation; the hooves stay at the shared contact points.
      for(const [x,phase] of [[42,0],[160,Math.PI]]) {
        const k=Math.sin(rot+phase)*9;
        line(g,P.deep,7,[[x,-56],[x+k,-30],[x,-5]]);
        line(g,P.mid,5,[[x+8,-54],[x-k+7,-29],[x+3,-5]]);
        box(g,"#24202c",x-7,-7,14,7);
      }
      oval(g,P.base,97,-62,65,24); oval(g,P.mid,64,-65,22,19);
      poly(g,P.base,[[135,-61],[145,-106],[165,-119],[186,-106],[198,-87],[181,-81],[165,-89],[159,-50]]);
      poly(g,P.deep,[[145,-102],[153,-122],[157,-103],[166,-123],[171,-107]]);
      line(g,P.deep,9,[[38,-65],[21,-73],[12,-54],[9,-37]]);
      line(g,P.deep,6,[[148,-100],[143,-82],[141,-65]]);
      oval(g,"#ffffff",179,-103,3,3); oval(g,"#15131e",180,-103,1.5,2);
      line(g,"#2c1c2e",2,[[189,-92],[163,-81],[112,-90]]);
      box(g,"#3b2644",77,-87,39,10); oval(g,P.hi,95,-84,19,4);
      // Original cowboy: boots, denim, shirt, face and a broad hat.
      line(g,"#293858",9,[[94,-100],[110,-83],[101,-55]]); box(g,"#282231",96,-57,15,6);
      poly(g,"#258997",[[82,-124],[103,-125],[112,-99],[88,-96]]);
      line(g,"#258997",7,[[101,-119],[117,-103],[130,-98]]);
      oval(g,"#d9a07a",94,-137,9,12);
      box(g,"#473144",85,-157,18,12); oval(g,"#65475a",94,-145,24,4);
      oval(g,"#211a29",100,-138,1.4,1.4);
    }
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
