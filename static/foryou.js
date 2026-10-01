/* Chisme "For You": an on-device food-video ranker. Everything lives in this phone's localStorage
   (key "chisme-foryou"); nothing is sent to the server. Pure functions, no DOM, so it's unit-tested
   in Node (foryou_rank_test.py) and used by app.js as window.ChismeForYou.

   Features of a video: creator, dish/cuisine keywords from the title, neighborhood (known names or
   the ZIP), and price hints. Signals change the weight of each of the video's features:
     open/watch +1, watch time up to +1.5 more (30 s), save +3, unsave −2, skip-fast −0.6,
     "Not interested" −4 (and that video is hidden).
   Weights fade with a 14-day half-life. Score = interest + freshness (10-day half-life) − repeats − already saved,
   then hard variety rules (many creators, many different places: see rank()) and ~20% exploration
   slots (every 5th card is something new or different), with a seeded shuffle so the order is
   stable while you scroll. */
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
      return { text: k ? `Something different: ${labelOf(k.slice(2))}` : `Something new from ${norm(it.creator) || (isRecipe(it) ? "a home cook" : isWorld(it) ? "a food reviewer" : "a local creator")}`, kind: "explore" };
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
    if (isRecipe(it)) return { text: `Cook it at home: ${norm(it.creator) || "a home cook"}`, kind: "fresh" };
    if (isWorld(it)) return { text: `Around the world with ${norm(it.creator) || "a food reviewer"}`, kind: "fresh" };
    const age = it.published ? now - it.published * 1000 : Infinity;
    return { text: age < 7 * DAY ? "Fresh this week" : `From ${norm(it.creator) || "a local creator"}`, kind: "fresh" };
  }

  // ---------- variety: many creators, many different places
  // crew = the person behind the videos (one key for a creator's YouTube + TikTok; the server sends it as it.crew)
  const crewOf = (it) => norm(it.crew || it.creator || it.source).toLowerCase();
  const keyText = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[’'`´]/g, "")
    .replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
  const PLACE_STOP = /^(the|a|an|new|best|hey|wow|food|eats|san antonio|satx|texas|tx|restaurant|here|this|part \d+)$/;
  // the restaurant a video is about, as a comparable key ("Losoya’s Taqueria" and "losoyas taqueria" match); null if unknown
  function placeKey(it) {
    const n = it && it.place && it.place.name;
    if (!n) return null;
    const k = keyText(n).replace(/^the /, "").replace(/ (restaurant|san antonio|satx|tx|texas)$/g, "").trim();
    if (k.replace(/ /g, "").length < 4 || PLACE_STOP.test(k)) return null;
    if (k === keyText(it.creator) || k === keyText(it.crew) || k === keyText(it.source)) return null;   // "- Full Nelson Eats" is the channel, not a spot
    return k;
  }
  const CAP_TOP10 = 2, PLACE_WINDOW = 15, ROUND_NEW = 9, ROUND_LEARNED = 5;
  // cooking & recipe videos (it.recipe) are mixed in: every MIX_EVERY-th video is one, as long as both kinds are left
  const MIX_EVERY = 3;
  const isRecipe = (it) => !!(it && (it.recipe || it.kind === "recipe"));
  // v43: food reviewers from the US and around the world (it.world): never first (a San Antonio creator leads), then
  // local and world take turns in the non-recipe slots while both are left
  const isWorld = (it) => !!(it && (it.world || it.kind === "world"));

  // The feed. Hard variety rules first, then taste:
  //  • one video per restaurant (videos about the same spot are deduped; the best one stays)
  //  • never the same creator or the same restaurant twice in a row; no restaurant twice in the top 15
  //  • at most 2 videos per creator in the top 10
  //  • new phone: round-robin across creators (the first ~9 are 9 different people), in a daily order that
  //    rotates with opts.rot so the lead creator changes; a phone that has learned: first 5 are 5 different creators
  //  • opts.lastLead: the creator who led last time doesn't lead again
  //  • after that it's score order (taste + freshness), and every 5th slot is exploration (least familiar third)
  //  • the mix: every 3rd video is a cooking / recipe video (slots 3, 6, 9 …) while there are both kinds left; v44: a cook
  //    with many videos (ArnieTex) is spread evenly through those slots, not bunched at the end
  //  • v43: a local creator leads (slot 1 is never a world reviewer or a recipe while a local video is left); after that
  //    the other slots take turns local → world → local … while both are left
  // If the rules can't all be met (a tiny feed), they relax in order: round-robin → caps → the mix / back-to-back creator.
  function rank(p, items, opts) {
    opts = opts || {};
    const now = opts.now || Date.now(), rand = rng(opts.seed == null ? Math.floor(now / DAY) : opts.seed);
    const urls = new Set();
    const pool = items.filter((it) => it && it.url && !((p.s[it.url] || {}).ni) && !urls.has(it.url) && urls.add(it.url));
    let scored = pool.map((it) => ({ it, score: scoreOf(p, it, now), fam: familiarity(p, it, now), crew: crewOf(it), place: placeKey(it), j: rand() }));
    // a video with no place of its own but whose title names a known spot is about that spot
    const known = [...new Set(scored.map((x) => x.place).filter((k) => k && k.length >= 6))];
    for (const x of scored) if (!x.place) { const t = " " + keyText(x.it.title) + " "; const k = known.find((k) => t.includes(" " + k + " ")); if (k) x.place = k; }
    const best = new Map();
    for (const x of scored) if (x.place) {
      const b = best.get(x.place);
      if (!b || x.score > b.score || (x.score === b.score && (x.it.published || 0) > (b.it.published || 0))) best.set(x.place, x);
    }
    scored = scored.filter((x) => !x.place || best.get(x.place) === x);

    const learned = Object.keys(p.f).length > 0;
    const crews = [...new Set(scored.map((x) => x.crew))].sort();
    for (let i = crews.length - 1; i > 0; i--) { const k = Math.floor(rand() * (i + 1)); [crews[i], crews[k]] = [crews[k], crews[i]]; }   // today's order
    // local creators and cooks each rotate in their own order (so every visit a different local creator leads)
    const cooks = new Set(scored.filter((x) => isRecipe(x.it)).map((x) => x.crew)), pos = new Map(), frac = new Map();
    const globe = new Set(scored.filter((x) => isWorld(x.it)).map((x) => x.crew));
    const isLocal = (x) => !isRecipe(x.it) && !isWorld(x.it);
    for (const group of [crews.filter((c) => !cooks.has(c) && !globe.has(c)), crews.filter((c) => cooks.has(c)), crews.filter((c) => globe.has(c) && !cooks.has(c))]) {
      if (!group.length) continue;
      let off = ((opts.rot || 0) % group.length + group.length) % group.length;
      if (group.length > 1 && group[off] === opts.lastLead) off = (off + 1) % group.length;
      group.forEach((c, i) => { pos.set(c, (i - off + group.length) % group.length); frac.set(c, pos.get(c) / group.length); });
    }
    // v44: a cook with many videos (ArnieTex has 8) is spread evenly through the cooking slots instead of all of them landing
    // at the end once everyone else's single video is used up. A cook's k-th video is due at (k + phase) / its count, so n videos
    // sit evenly 1/n apart; the phase comes from today's order (a cook with one video: just its place in today's order), so
    // where the first one lands rotates from visit to visit
    const total = new Map(); for (const x of scored) total.set(x.crew, (total.get(x.crew) || 0) + 1);
    const due = (c) => { const n = total.get(c); return (cnt(c) + ((frac.get(c) * n) % 1)) / n; };
    const firstRound = Math.min(learned ? ROUND_LEARNED : ROUND_NEW, crews.length);
    const used = new Map(), out = [];
    const cnt = (c) => used.get(c) || 0;
    const ok = (x, slot, level, mix, turns) => {
      const prev = out[out.length - 1];
      if (level <= 3 && slot === 0 && !isLocal(x) && left.some(isLocal)) return false;   // a local creator leads
      if (level <= 2 && mix && isRecipe(x.it) !== (slot % MIX_EVERY === MIX_EVERY - 1)) return false;
      if (level <= 2 && turns && !isRecipe(x.it) && isWorld(x.it) !== (out.filter((o) => !isRecipe(o.item)).length % 2 === 1)) return false;
      if (level <= 3) {
        if (prev && x.place && prev.place === x.place) return false;
        if (slot === 0 && opts.lastLead && crews.length > 1 && x.crew === opts.lastLead) return false;
      }
      if (level <= 2 && prev && prev.crew === x.crew) return false;
      if (level <= 1) {
        if (slot < 10 && out.filter((o) => o.crew === x.crew).length >= CAP_TOP10) return false;
        if (slot < PLACE_WINDOW && x.place && out.some((o) => o.place === x.place)) return false;
      }
      if (level === 0 && slot < firstRound && cnt(x.crew) > 0) return false;
      return true;
    };
    let left = scored.slice();
    while (left.length) {
      const slot = out.length, explore = learned && slot % EXPLORE_EVERY === EXPLORE_EVERY - 1;
      let cands;
      if (!learned) {   // round-robin: fewest shown first, then today's creator order, then that creator's best (cooks: the one most due)
        const key = (x) => (isRecipe(x.it) ? due(x.crew) : cnt(x.crew) + frac.get(x.crew));
        cands = left.slice().sort((a, b) => key(a) - key(b) || b.score - a.score || a.j - b.j);
      } else if (explore) {
        const byFam = left.slice().sort((a, b) => a.fam - b.fam || a.j - b.j);
        const third = byFam.slice(0, Math.max(1, Math.ceil(byFam.length / 3))).sort((a, b) => a.j - b.j);
        cands = third.concat(byFam.slice(third.length).sort((a, b) => b.score - a.score));
      } else {
        cands = left.slice().sort((a, b) => (b.score - 0.3 * cnt(b.crew)) - (a.score - 0.3 * cnt(a.crew)) || a.j - b.j);
      }
      const mix = left.some((c) => isRecipe(c.it)) && left.some((c) => !isRecipe(c.it));
      const turns = left.some(isLocal) && left.some((c) => isWorld(c.it));
      let x = null;
      for (let level = 0; level <= 4 && !x; level++) x = cands.find((c) => ok(c, slot, level, mix, turns)) || null;
      left = left.filter((c) => c !== x);
      used.set(x.crew, cnt(x.crew) + 1);
      out.push({ item: x.it, score: x.score, explore, crew: x.crew, place: x.place, why: why(p, x.it, now, explore) });
    }
    return out;
  }
  // top interests, for the banner ("Tuned to you: tacos, BBQ …")
  function interests(p, n, now) {
    now = now || Date.now();
    return Object.entries(p.f).map(([k, x]) => ({ k, v: decayed(x, now) })).filter((e) => e.v > 0.2 && e.k[0] !== "p")
      .sort((a, b) => b.v - a.v).slice(0, n || 3).map((e) => (e.k[0] === "k" ? labelOf(e.k.slice(2)) : e.k.slice(2)));
  }
  const api = { KEY, isRecipe, isWorld, MIX_EVERY, crewOf, placeKey, featuresOf, load, save, reset, signal, scoreOf, rank, why, interests, labelOf, EXPLORE_EVERY };
  root.ChismeForYou = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
