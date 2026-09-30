/* Chisme news order (v29): if you check often and nothing is new, the News lists look different each visit.
   Everything runs on the phone. localStorage "chisme-news-seen" = { s: { id: { f: first rendered, l: last seen on
   screen, n: visits it was seen in, o: opened at } }, visit: { n, seed, at, snap, prev, leads }, active: last time the app was on screen }.
   - New stories (never shown on this phone before this visit) and breaking/urgent ones stay pinned at the top, in
     the server's order. A brand-new place or a first open (everything new) keeps the server's order untouched.
   - The rest: stories you haven't opened / have seen less move up; the lead rotates among the top 3; a light,
     seeded shuffle (a few places at most) keeps roughly the server's recency + importance order; the same outlet
     doesn't run back to back when another one can go there.
   - The order only changes on a new visit (opened after 10+ minutes away, back after 10+ minutes, or a manual
     refresh). Within a visit it's stable: same seed + a snapshot of what you'd seen when the visit started.
   Used by app.js as window.ChismeNewsOrder; pure functions, also loaded in Node by newsorder_test.py. */
(function (root) {
  const KEY = "chisme-news-seen", AWAY_MS = 10 * 60 * 1000, KEEP_MS = 21 * 864e5, MAX = 800;
  const URGENT = /^\s*(breaking|urgent|developing|live)\b|breaking news|\b(amber|silver|blue) alert\b|evacuat|shelter[- ]in[- ]place|boil[- ]water (notice|advisory)|\blockdown\b|active shooter|tornado warning|flash flood (warning|emergency)|\b(missing|endangered) (child|person|teen)\b/i;
  function idOf(link) {   // short, stable id for a story link (djb2 on the URL without tracking bits)
    const u = String(link || "").replace(/[?#].*$/, "").replace(/\/$/, "");
    let h = 5381;
    for (let i = 0; i < u.length; i++) h = ((h << 5) + h + u.charCodeAt(i)) >>> 0;
    return h.toString(36) + u.length.toString(36);
  }
  const urgent = (it) => URGENT.test(it.title || "");
  function empty() { return { s: {}, visit: null, active: 0 }; }
  function load(store) {
    try { const j = JSON.parse((store || root.localStorage).getItem(KEY)); if (j && j.s) return j; } catch (e) {}
    return empty();
  }
  function save(st, store) {
    const now = Date.now(), ids = Object.keys(st.s);
    for (const id of ids) { const x = st.s[id]; if (now - Math.max(x.f || 0, x.l || 0, x.o || 0) > KEEP_MS) delete st.s[id]; }
    const left = Object.entries(st.s);
    if (left.length > MAX) st.s = Object.fromEntries(left.sort((a, b) => Math.max(b[1].f || 0, b[1].l || 0) - Math.max(a[1].f || 0, a[1].l || 0)).slice(0, MAX));
    try { (store || root.localStorage).setItem(KEY, JSON.stringify(st)); } catch (e) {}
  }
  function reset(store) { try { (store || root.localStorage).removeItem(KEY); } catch (e) {} return empty(); }
  // A new visit: fresh seed, visit count + 1, and a snapshot of what was known when it started (so the order can't
  // shift while you scroll, even as stories get marked seen).
  function beginVisit(st, now, rand) {
    now = now || Date.now();
    const snap = {};
    for (const [id, x] of Object.entries(st.s)) snap[id] = [x.n || 0, x.o ? 1 : 0];
    const pv = st.visit || {}, prev = (pv.prev || []).concat(pv.leads || []).slice(-9);   // who led recent visits
    st.visit = { n: (pv.n || 0) + 1, seed: Math.floor((rand || Math.random)() * 2 ** 31), at: now, snap, prev, leads: [] };
    st.active = now;
    return st;
  }
  // Should this open / return start a new visit?
  const isNewVisit = (st, now) => !st.visit || (now || Date.now()) - (st.active || 0) >= AWAY_MS;
  function rnd(seed, id) {   // deterministic 0..1 per (visit, story)
    let h = (seed ^ 0x9e3779b9) >>> 0;
    for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995) >>> 0; h ^= h >>> 15;
    return (h >>> 0) / 4294967296;
  }
  // Order one list. items: the server's order (already recency + importance ranked). Returns a new array.
  function order(items, st, opts) {
    opts = opts || {};
    const v = st.visit;
    if (!v || items.length < 3) return items.slice();
    const snap = v.snap || {};
    const tagged = items.map((it, i) => ({ it, i, id: idOf(it.link), src: (it.source || "").toLowerCase() }));
    const isNew = (t) => !(t.id in snap);
    if (tagged.every(isNew)) {   // first open here / new place: the server's order as is
      if (v.leads && !v.leads.includes(tagged[0].id)) v.leads.push(tagged[0].id);
      return items.slice();
    }
    const pinned = tagged.filter((t) => isNew(t) || urgent(t.it));
    const rest = tagged.filter((t) => !pinned.includes(t));
    const nowS = (opts.now || Date.now()) / 1000;
    for (const t of rest) {
      const [seen, opened] = snap[t.id] || [0, 0];
      const age = t.it.published ? Math.max(0, nowS - t.it.published) / 3600 : 48;
      t.score = -t.i                        // the server's rank (recency + how local/important)
        + (seen ? 0 : 3.5)                  // never scrolled past it: move it up
        - 1.2 * Math.min(seen, 4)           // seen on several visits: sink a little each time
        - (opened ? 6 : 0)                  // already opened it: let others have the top
        + (age < 3 ? 1 : 0)                 // still fresh
        + (rnd(v.seed, t.id) - 0.5) * 5;    // light shuffle: a few places either way
    }
    rest.sort((a, b) => b.score - a.score || a.i - b.i);
    // rotate the lead among the top 3: one that didn't lead a recent visit (depends only on what was known when this
    // visit began, so it's the same every time this visit renders)
    if (rest.length > 1) {
      const top = rest.slice(0, Math.min(3, rest.length)), prev = v.prev || [];
      const fresh = top.filter((t) => !prev.includes(t.id)), pickFrom = fresh.length ? fresh : top;
      const lead = pickFrom[(v.n - 1) % pickFrom.length];
      rest.splice(rest.indexOf(lead), 1); rest.unshift(lead);
      if (v.leads && !v.leads.includes(lead.id)) v.leads.push(lead.id);
    }
    // mix outlets: don't put the same one twice in a row when something within the next few can go there instead
    const out = [], pool = rest.slice(), prevSrc = pinned.length ? pinned[pinned.length - 1].src : null;
    let last = prevSrc;
    while (pool.length) {
      let k = pool.findIndex((t, j) => j < 5 && t.src !== last);
      if (k < 0 || (out.length === 0 && !pinned.length)) k = 0;   // keep the chosen lead
      const [t] = pool.splice(k, 1); out.push(t); last = t.src;
    }
    return pinned.concat(out).map((t) => t.it);
  }
  function markRendered(st, items, now) {
    now = now || Date.now();
    for (const it of items) { const id = idOf(it.link); if (!st.s[id]) st.s[id] = { f: now }; }
  }
  function markSeen(st, id, now) {   // on screen: counts once per visit
    const x = st.s[id] || (st.s[id] = { f: now || Date.now() });
    const vn = st.visit ? st.visit.n : 0;
    if (x.v !== vn) { x.n = (x.n || 0) + 1; x.v = vn; }
    x.l = now || Date.now();
  }
  function markOpened(st, id, now) { const x = st.s[id] || (st.s[id] = { f: now || Date.now() }); x.o = now || Date.now(); }
  const api = { KEY, AWAY_MS, idOf, urgent, load, save, reset, beginVisit, isNewVisit, order, markRendered, markSeen, markOpened };
  root.ChismeNewsOrder = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
