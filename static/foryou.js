/* Chisme "For You": an on-device food-video ranker. Everything lives in this phone's localStorage
   (key "chisme-foryou"); nothing is sent to the server. Pure functions, no DOM, so it's unit-tested
   in Node (foryou_rank_test.py) and used by app.js as window.ChismeForYou.

   Features of a video: creator, dish/cuisine keywords from the title, neighborhood (known names or
   the ZIP), and price hints. Signals change the weight of each of the video's features:
     open/watch +1, watch time up to +1.5 more (30 s), save +3, unsave −2, skip-fast −0.6,
     "Not interested" −4 (and that video is hidden).
   Weights fade with a 14-day half-life. Score = interest + freshness (10-day half-life) − repeats − already saved,
   then a light diversity pass (no creator three times in a row) and ~20% exploration slots
   (every 5th card is something new or different), picked with a seeded shuffle so the order
   is stable while you scroll. */
(function (root) {
  "use strict";
  const KEY = "chisme-foryou", VERSION = 1, DAY = 864e5;
  const HALF_LIFE = 14 * DAY, FRESH_HALF = 10 * DAY;
  const DELTA = { open: 1, save: 3, unsave: -2, skip: -0.6, not_interested: -4 };
  const IMPORTANCE = { c: 1.0, k: 1.2, n: 0.7, p: 0.6 };
  const EXPLORE_EVERY = 5;   // 1 in 5 cards (~20%) is exploration

  // dish / cuisine keywords (label, how to count saves: "2 taco spots", matches)
  const DISHES = [
    ["tacos", "taco", /\btacos?\b|taquer[ií]a|barbacoa|al pastor|trompo|puffy taco/i],
    ["birria", "birria", /\bbirria|quesabirria|consom[eé]/i],
    ["bbq", "BBQ", /\bbbq\b|barbe?cue|smokehouse|brisket|\bribs\b|burnt ends|smoked meat/i],
    ["mariscos", "mariscos", /mariscos|seafood|shrimp|camar[oó]n|ceviche|crawfish|oysters?|\bcrab\b|lobster|aguachile|fish\b|poke\b/i],
    ["desserts", "dessert", /desserts?|\bcakes?\b|cheesecake|ice cream|gelato|paletas?|churros?|donuts?|doughnuts?|cookies?|chocolate|pastr(y|ies)|pan dulce|conchas?|raspas?|fruit cups?|crepes?|sweets?|bakery|boba|milkshake|pie\b/i],
    ["breakfast", "breakfast", /breakfast|brunch|pancakes?|waffles?|chilaquiles|migas|biscuits?|\beggs?\b|french toast/i],
    ["burgers", "burger", /burgers?\b/i],
    ["pizza", "pizza", /pizza|pizzeria/i],
    ["italian", "Italian", /italian|pasta|lasagna|ristorante|trattoria/i],
    ["mexican", "Mexican", /mexican|tex-?mex|enchiladas?|tamales?|tortas?|gorditas?|elotes?|antojitos?|pozole|menudo|mole\b|cantina|quesadillas?|nachos/i],
    ["caribbean", "Caribbean", /boricua|puerto ric|cuban|caribbean|jamaican|mofongo|dominican/i],
    ["asian", "Asian", /ramen|sushi|\bpho\b|korean|kbbq|thai|chinese|dim sum|japanese|vietnamese|dumplings?|banh mi|hot pot|teriyaki|filipino|indian|curry/i],
    ["steak", "steak", /steak|steakhouse|fine dining|prime rib|wagyu/i],
    ["soup", "soup", /\bsoups?\b|caldo|stew|chili\b|gumbo/i],
    ["coffee", "coffee", /coffee|caf[eé]\b|roaster|roastery|latte|espresso|matcha/i],
    ["snacks", "snack", /snacks?|chips|ruffles|takis|chamoy|candy|hot cheetos|spicy/i],
    ["drinks", "drink", /\bbar\b|cocktails?|margaritas?|beer|brewery|wine|aguas? frescas|micheladas?|drinks?/i],
    ["wings", "wings", /\bwings?\b|fried chicken|chicken tenders/i],
    ["festival", "food event", /festival|\bfest\b|food truck park|market days?|pop-?up|raffle/i],
  ];
  // San Antonio-area neighborhoods: names first, then a coarse ZIP → area table (approximate, for grouping only)
  const HOODS = [
    ["Downtown", /downtown|river ?walk|market square/i], ["Pearl", /\bpearl\b/i], ["Southtown", /southtown|king william|blue star/i],
    ["Stone Oak", /stone oak/i], ["Alamo Ranch", /alamo ranch/i], ["Alamo Heights", /alamo heights/i], ["Medical Center", /medical center|med center/i],
    ["The Rim", /\bthe rim\b|la cantera/i], ["Westside", /west ?side/i], ["Eastside", /east ?side/i], ["Southside", /south ?side/i],
    ["Northside", /north ?side/i], ["Airport", /airport/i], ["Helotes", /helotes/i], ["Boerne", /boerne/i], ["New Braunfels", /new braunfels/i],
    ["Leon Valley", /leon valley/i], ["Castroville", /castroville/i], ["Schertz", /schertz|cibolo/i], ["Converse", /converse/i],
  ];
  const ZIPS = { 78205: "Downtown", 78215: "Downtown", 78204: "Southtown", 78210: "Southtown", 78209: "Alamo Heights", 78212: "Alamo Heights",
    78258: "Stone Oak", 78259: "Stone Oak", 78260: "Stone Oak", 78253: "Alamo Ranch", 78254: "Alamo Ranch", 78245: "Westover Hills",
    78240: "Medical Center", 78229: "Medical Center", 78249: "UTSA", 78256: "The Rim", 78257: "The Rim", 78207: "Westside", 78237: "Westside",
    78202: "Eastside", 78203: "Eastside", 78220: "Eastside", 78211: "Southside", 78214: "Southside", 78221: "Southside", 78224: "Southside",
    78216: "Airport", 78217: "Northeast", 78218: "Northeast", 78219: "Northeast", 78247: "Northeast", 78230: "Northwest", 78231: "Northwest",
    78232: "North Central", 78248: "North Central", 78213: "North Central", 78201: "Deco District", 78228: "Northwest", 78023: "Helotes",
    78006: "Boerne", 78130: "New Braunfels", 78132: "New Braunfels", 78154: "Schertz", 78108: "Schertz" };
  const CHEAP = /\bcheap\b|budget|\bdeals?\b|under \$\d+|\$\d(\.\d\d)?\b|\$1\d(\.\d\d)?\b|free\b|all you can eat|specials?\b|happy hour|dollar|bogo|affordable/i;
  const SPLURGE = /fine dining|steakhouse|omakase|tasting menu|luxury|upscale|fancy|wagyu|\$\d{3,}|\$[5-9]\d\b|expensive|splurge/i;

  const norm = (s) => String(s || "").trim();
  const labelOf = (id) => { const d = DISHES.find((x) => x[0] === id); return d ? d[1] : id; };

  function featuresOf(it) {
    const text = [it.title, it.summary, it.place && it.place.name, it.place && it.place.address].filter(Boolean).join(" ");
    const f = [];
    const creator = norm(it.creator || it.source);
    if (creator) f.push("c:" + creator);
    for (const [id, , re] of DISHES) if (re.test(text)) f.push("k:" + id);
    let hood = null;
    for (const [name, re] of HOODS) if (re.test(text)) { hood = name; break; }
    if (!hood) { const z = /\b(7[89]\d{3})\b/.exec(text); if (z && ZIPS[z[1]]) hood = ZIPS[z[1]]; }
    if (hood) f.push("n:" + hood);
    if (SPLURGE.test(text)) f.push("p:splurge"); else if (CHEAP.test(text)) f.push("p:cheap");
    return f;
  }

  // ---------- profile (what this phone has learned)
  const empty = () => ({ v: VERSION, f: {}, s: {}, n: 0 });
  function load(store) {
    try { const p = JSON.parse((store || root.localStorage).getItem(KEY) || "null"); if (p && p.v === VERSION && p.f && p.s) return p; } catch (e) {}
    return empty();
  }
  function save(p, store) {
    // keep it small: the 300 strongest features and the 400 most recent videos
    const f = Object.entries(p.f).sort((a, b) => Math.abs(b[1].w) - Math.abs(a[1].w)).slice(0, 300);
    const s = Object.entries(p.s).sort((a, b) => b[1].t - a[1].t).slice(0, 400);
    p.f = Object.fromEntries(f); p.s = Object.fromEntries(s);
    try { (store || root.localStorage).setItem(KEY, JSON.stringify(p)); return true; } catch (e) { return false; }
  }
  function reset(store) { try { (store || root.localStorage).removeItem(KEY); } catch (e) {} return empty(); }
  const decayed = (x, now) => (x ? x.w * Math.pow(0.5, Math.max(0, now - x.t) / HALF_LIFE) : 0);

  // kind: open | watch (with seconds) | save | unsave | skip | not_interested | undo_not_interested
  function signal(p, kind, it, opts) {
    opts = opts || {};
    const now = opts.now || Date.now(), url = it.url;
    let d = DELTA[kind] || 0;
    if (kind === "watch") d = 0.5 + 1.5 * Math.min(1, Math.max(0, (opts.seconds || 0) - 3) / 27);   // 3 s … 30 s → +0.5 … +2
    if (kind === "undo_not_interested") d = -DELTA.not_interested;
    const feats = featuresOf(it), scale = 1 / Math.sqrt(Math.max(1, feats.length));   // a video with many tags doesn't swamp the profile
    for (const k of feats) {
      const x = p.f[k] || { w: 0, t: now, sv: 0, wt: 0 };
      x.w = decayed(x, now) + d * scale; x.t = now;
      if (kind === "save") x.sv = (x.sv || 0) + 1;
      if (kind === "unsave") x.sv = Math.max(0, (x.sv || 0) - 1);
      if (kind === "watch" || kind === "open") x.wt = (x.wt || 0) + 1;
      p.f[k] = x;
    }
    const s = p.s[url] || { v: 0, t: now };
    s.t = now;
    if (kind === "watch" || kind === "open") s.v = (s.v || 0) + 1;
    if (kind === "skip") s.sk = (s.sk || 0) + 1;
    if (kind === "not_interested") s.ni = 1;
    if (kind === "save") s.sv = 1;
    if (kind === "unsave") delete s.sv;
    if (kind === "undo_not_interested") delete s.ni;
    p.s[url] = s; p.n = (p.n || 0) + 1;
    return p;
  }

  function contributions(p, it, now) {
    return featuresOf(it).map((k) => ({ k, v: decayed(p.f[k], now) * (IMPORTANCE[k[0]] || 1), x: p.f[k] })).filter((c) => c.v !== 0);
  }
  function scoreOf(p, it, now) {
    const interest = contributions(p, it, now).reduce((a, c) => a + c.v, 0);
    const age = it.published ? Math.max(0, now - it.published * 1000) : 30 * DAY;
    const fresh = Math.pow(0.5, age / FRESH_HALF);
    const s = p.s[it.url] || {};
    return interest + 1.5 * fresh - 0.8 * (s.v || 0) - 0.5 * (s.sk || 0) - (s.sv ? 1.5 : 0);   // already saved: make room for new finds
  }
  const familiarity = (p, it, now) => featuresOf(it).reduce((a, k) => a + Math.abs(decayed(p.f[k], now)), 0) + 2 * ((p.s[it.url] || {}).v || 0);

  function rng(seed) {   // mulberry32
    let a = seed >>> 0;
    return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;

  function why(p, it, now, explore) {
    if (explore) {
      const k = featuresOf(it).find((f) => f[0] === "k");
      return { text: k ? `Something different: ${labelOf(k.slice(2))}` : `Something new from ${norm(it.creator) || "a local creator"}`, kind: "explore" };
    }
    const top = contributions(p, it, now).filter((c) => c.v > 0.05).sort((a, b) => b.v - a.v)[0];
    if (top) {
      const t = top.k[0], name = top.k.slice(2), x = top.x || {};
      if (t === "k") {
        const lab = labelOf(name);
        if (x.sv) return { text: `Because you saved ${plural(x.sv, lab + " spot")}`, kind: "save" };
        return { text: `Because you watched ${plural(x.wt || 1, lab + " video")}`, kind: "watch" };
      }
      if (t === "c") return x.sv ? { text: `Because you saved ${plural(x.sv, "pick")} from ${name}`, kind: "save" } : { text: `Because you watch ${name}`, kind: "watch" };
      if (t === "n") return { text: x.sv ? `Near spots you saved in ${name}` : `Because you like ${name} spots`, kind: x.sv ? "save" : "watch" };
      if (t === "p") return { text: name === "cheap" ? "Because you like cheap eats" : "Because you like a splurge", kind: "watch" };
    }
    const age = it.published ? now - it.published * 1000 : Infinity;
    return { text: age < 7 * DAY ? "Fresh this week" : `From ${norm(it.creator) || "a local creator"}`, kind: "fresh" };
  }

  // The feed: ranked by score with a diversity pass; every 5th slot is exploration (a video whose features
  // this phone knows least, picked at random among the least familiar third). Not-interested videos are hidden.
  function rank(p, items, opts) {
    opts = opts || {};
    const now = opts.now || Date.now(), rand = rng(opts.seed == null ? Math.floor(now / DAY) : opts.seed);
    const pool = items.filter((it) => it && it.url && !((p.s[it.url] || {}).ni));
    const scored = pool.map((it) => ({ it, score: scoreOf(p, it, now), fam: familiarity(p, it, now) }));
    const learned = Object.keys(p.f).length > 0;
    const out = [], left = scored.slice();
    while (left.length) {
      const slot = out.length;
      let pickI = -1, explore = false;
      if (learned && slot % EXPLORE_EVERY === EXPLORE_EVERY - 1) {
        const byFam = left.map((x, i) => ({ i, fam: x.fam })).sort((a, b) => a.fam - b.fam);
        const cand = byFam.slice(0, Math.max(1, Math.ceil(byFam.length / 3)));
        pickI = cand[Math.floor(rand() * cand.length)].i; explore = true;
      } else {
        const recent = out.slice(-2).map((o) => norm(o.item.creator));
        let best = -Infinity;
        left.forEach((x, i) => {
          const same = recent.filter((c) => c && c === norm(x.it.creator)).length;
          const s = x.score - (same === 2 ? 1.2 : same * 0.25) + rand() * 1e-6;   // tiny jitter breaks ties
          if (s > best) { best = s; pickI = i; }
        });
      }
      const x = left.splice(pickI, 1)[0];
      out.push({ item: x.it, score: x.score, explore, why: why(p, x.it, now, explore) });
    }
    return out;
  }
  // top interests, for the banner ("Tuned to you: tacos, BBQ …")
  function interests(p, n, now) {
    now = now || Date.now();
    return Object.entries(p.f).map(([k, x]) => ({ k, v: decayed(x, now) })).filter((e) => e.v > 0.2 && e.k[0] !== "p")
      .sort((a, b) => b.v - a.v).slice(0, n || 3).map((e) => (e.k[0] === "k" ? labelOf(e.k.slice(2)) : e.k.slice(2)));
  }
  const api = { KEY, featuresOf, load, save, reset, signal, scoreOf, rank, why, interests, labelOf, EXPLORE_EVERY };
  root.ChismeForYou = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
