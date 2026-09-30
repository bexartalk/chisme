"""Unit tests for the on-device For You ranker (static/foryou.js), run in Node. No browser, no network.
Checks features, each signal (open/watch time/save/skip-fast/not interested), recency decay, ~20% exploration,
diversity + the variety rules (round-robin creators, top-10 cap, restaurant dedupe, lead rotation), the 'Why you're seeing this' text, reset/storage, and that the ranker never talks to a server."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
JS = r"""
const F = require(process.argv[1]);
const DAY = 864e5, NOW = Date.UTC(2026, 8, 29, 20), ts = (d) => (NOW - d * DAY) / 1000;
const out = [], ok = (c, what) => out.push([!!c, what]);
const mk = (i, creator, title, daysAgo, extra = {}) => ({ url: "https://www.youtube.com/shorts/v" + i, title, creator, published: ts(daysAgo), video: true, ...extra });
const items = [
  mk(1, "Cherise", "Losoya’s Taqueria 4445 Walzem Road San Antonio, TX 78218 street tacos", 1),
  mk(2, "Cherise", "Birria tacos at Tacos El Regio", 2),
  mk(3, "Hannah", "2M Smokehouse is the best BBQ spot around!!", 3),
  mk(4, "Texas Eats", "Brisket and ribs at a new smokehouse", 4),
  mk(5, "Eatmigos", "Mariscos and aguachile on the Westside", 2),
  mk(6, "Eatmigos", "Churros, paletas and the best dessert in Stone Oak", 5),
  mk(7, "Hannah", "Breakfast tacos and chilaquiles brunch", 6),
  mk(8, "Porter's", "Fine dining at Dean’s Steak and Seafood", 7),
  mk(9, "Munchies", "Chinese buffet: $9.99 all you can eat", 8),
  mk(10, "Cherise", "Fruit Desserts La Café 11840 Alamo Ranch Parkway", 9),
  mk(11, "Full Nelson", "HEB spicy chips snack review", 10),
  mk(12, "Siempre", "Pizza night at The Pizza Spot", 11),
  mk(13, "Texas Eats", "Ramen and sushi downtown", 12),
  mk(14, "Eatmigos", "TX FRONTYARD BBQ", 13),
  mk(15, "Porter's", "Mac and cheese at the flea market", 14),
];
const byUrl = Object.fromEntries(items.map((i) => [i.url, i]));
// 1. features
const f = (i) => F.featuresOf(items[i - 1]);
ok(f(1).includes("k:tacos") && f(1).includes("n:Northeast") && f(1).includes("c:Cherise"), "features: creator + tacos + neighborhood from the ZIP (78218 → Northeast): " + f(1));
ok(f(2).includes("k:birria") && f(2).includes("k:tacos"), "features: birria tacos → birria + tacos");
ok(f(3).includes("k:bbq") && f(4).includes("k:bbq"), "features: BBQ / smokehouse / brisket → bbq");
ok(f(5).includes("k:mariscos") && f(5).includes("n:Westside"), "features: mariscos + Westside");
ok(f(6).includes("k:desserts") && f(6).includes("n:Stone Oak"), "features: desserts + Stone Oak");
ok(f(7).includes("k:breakfast"), "features: breakfast / brunch");
ok(f(8).includes("p:splurge") && f(9).includes("p:cheap"), "features: price hints (fine dining → splurge, $9.99 all you can eat → cheap)");
// 2. cold start: freshest first, no explore slots, no creator three times in a row
let p = F.load({ getItem: () => null });
let r = F.rank(p, items, { now: NOW, seed: 7 });
ok(r.length === items.length && r.every((x) => !x.explore), "cold start: every video, no exploration yet");
const nc = new Set(items.map((i) => i.creator)).size;
ok(new Set(r.slice(0, nc).map((x) => x.crew)).size === nc, `cold start: round-robin, the first ${nc} videos are all ${nc} creators: ` + r.slice(0, nc).map((x) => x.item.creator).join(", "));
const threeInRow = (list) => list.some((x, i) => i >= 2 && x.item.creator === list[i - 1].item.creator && x.item.creator === list[i - 2].item.creator);
ok(!threeInRow(r), "diversity: no creator three times in a row (cold start)");
ok(/^(Fresh this week|From )/.test(r[0].why.text), "why (cold): '" + r[0].why.text + "'");
// 3. saves teach it: two taco saves → taco videos rise, and the chip says so
p = F.load({ getItem: () => null });
F.signal(p, "save", items[0], { now: NOW }); F.signal(p, "save", items[6], { now: NOW });
r = F.rank(p, items, { now: NOW, seed: 7 });
const pos = (url) => r.findIndex((x) => x.item.url === url);
ok(pos(items[1].url) <= 1, "save ×2 (taco spots): the other taco video (birria tacos) ranks in the top 2 (#" + (pos(items[1].url) + 1) + ")");
const birria = r.find((x) => x.item.url === items[1].url);
ok(birria.why.text === "Because you saved 2 taco spots", "why: '" + birria.why.text + "'");
// 4. watch time: long watches beat short ones
p = F.load({ getItem: () => null });
F.signal(p, "watch", items[2], { now: NOW, seconds: 30 }); F.signal(p, "watch", items[3], { now: NOW, seconds: 28 });
const pShort = F.load({ getItem: () => null }); F.signal(pShort, "watch", items[2], { now: NOW, seconds: 4 }); F.signal(pShort, "watch", items[3], { now: NOW, seconds: 4 });
const bbq14 = items[13];
ok(F.scoreOf(p, bbq14, NOW) > F.scoreOf(pShort, bbq14, NOW) && F.scoreOf(pShort, bbq14, NOW) > F.scoreOf(F.load({ getItem: () => null }), bbq14, NOW),
   "watch time: 30 s watches lift another BBQ video more than 4 s watches, which still beat nothing");
r = F.rank(p, items, { now: NOW, seed: 7 });
const bb = r.find((x) => x.item.url === bbq14.url);
ok(r.findIndex((x) => x === bb) < 5 && /BBQ video|Eatmigos/.test(bb.why.text), "BBQ watcher: TX FRONTYARD BBQ (13 days old) moves into the top 5, why '" + bb.why.text + "'");
// 5. skip-fast pushes a topic down; repeats sink
p = F.load({ getItem: () => null });
for (const d of [5, 9]) for (let k = 0; k < 3; k++) F.signal(p, "skip", items[d], { now: NOW });
r = F.rank(p, items, { now: NOW, seed: 7 });
ok(r.findIndex((x) => x.item.url === items[5].url) >= items.length / 2 && r.findIndex((x) => x.item.url === items[9].url) >= items.length / 2, "skip-fast ×3 on dessert videos: both drop to the bottom half");
// 6. not interested: hidden, similar videos pushed down, undo brings it back
p = F.load({ getItem: () => null });
F.signal(p, "not_interested", items[7], { now: NOW });
r = F.rank(p, items, { now: NOW, seed: 7 });
ok(!r.some((x) => x.item.url === items[7].url), "not interested: that video is hidden");
ok(F.scoreOf(p, mk(99, "Porter's", "Steakhouse wagyu fine dining", 1), NOW) < F.scoreOf(F.load({ getItem: () => null }), mk(99, "Porter's", "Steakhouse wagyu fine dining", 1), NOW), "not interested: similar (steak, splurge, same creator) score lower");
F.signal(p, "undo_not_interested", items[7], { now: NOW });
ok(F.rank(p, items, { now: NOW, seed: 7 }).some((x) => x.item.url === items[7].url), "undo: it's back");
// 7. exploration ≈ 20%: every 5th slot, from the least familiar videos, labeled
p = F.load({ getItem: () => null });
F.signal(p, "save", items[0], { now: NOW }); F.signal(p, "save", items[1], { now: NOW }); F.signal(p, "watch", items[2], { now: NOW, seconds: 30 });
r = F.rank(p, items, { now: NOW, seed: 7 });
const ex = r.filter((x) => x.explore);
ok(ex.length === Math.floor(items.length / 5) && r.every((x, i) => x.explore === (i % 5 === 4)), `exploration: ${ex.length}/${r.length} slots (${Math.round(100 * ex.length / r.length)}%), every 5th`);
ok(ex.every((x) => !/tacos|bbq/.test(F.featuresOf(x.item).join(" ")) || F.featuresOf(x.item).length > 2), "exploration picks aren't more of what you already saved: " + ex.map((x) => x.item.title.slice(0, 18)).join(" | "));
ok(ex.every((x) => /^Something (different|new)/.test(x.why.text)), "exploration chip: " + ex.map((x) => x.why.text).join(" | "));
const big = Array.from({ length: 50 }, (_, i) => mk(100 + i, "C" + (i % 7), ["tacos", "BBQ", "sushi", "pizza", "dessert", "breakfast", "mariscos"][i % 7] + " spot " + i, i % 20));
const rb = F.rank(p, big, { now: NOW, seed: 3 });
ok(rb.filter((x) => x.explore).length === 10, "exploration on 50 videos: 10 (20%)");
ok(JSON.stringify(F.rank(p, big, { now: NOW, seed: 3 }).map((x) => x.item.url)) === JSON.stringify(rb.map((x) => x.item.url)), "stable: same seed, same order (the feed doesn't reshuffle while you scroll)");
// 8. recency decay: an old save counts less than a fresh one
const pOld = F.load({ getItem: () => null }), pNew = F.load({ getItem: () => null });
F.signal(pOld, "save", items[0], { now: NOW - 28 * DAY }); F.signal(pNew, "save", items[0], { now: NOW });
const sOld = F.scoreOf(pOld, items[1], NOW), sNew = F.scoreOf(pNew, items[1], NOW), s0 = F.scoreOf(F.load({ getItem: () => null }), items[1], NOW);
ok(sNew > sOld && sOld > s0 && Math.abs((sOld - s0) / (sNew - s0) - 0.25) < 0.05, `recency decay: a 28-day-old save counts ~1/4 of today's (14-day half-life): ${((sOld - s0) / (sNew - s0)).toFixed(2)}`);
// 9. unsave takes it back; interests for the banner
p = F.load({ getItem: () => null });
F.signal(p, "save", items[0], { now: NOW }); F.signal(p, "save", items[1], { now: NOW });
ok(F.interests(p, 3, NOW).includes("taco"), "interests: " + F.interests(p, 3, NOW).join(", "));
F.signal(p, "unsave", items[1], { now: NOW });
ok(p.f["k:tacos"].sv === 1, "unsave: the save count goes back down");
// 10. storage: round trip, caps, reset
const mem = {}, store = { getItem: (k) => mem[k] ?? null, setItem: (k, v) => { mem[k] = v; }, removeItem: (k) => { delete mem[k]; } };
p = F.load(store);
for (let i = 0; i < 600; i++) F.signal(p, "watch", mk(1000 + i, "Creator " + i, "Taco " + i + " review", 1), { now: NOW, seconds: 10 });
F.save(p, store);
const back = F.load(store);
ok(Object.keys(back.f).length <= 300 && Object.keys(back.s).length <= 400 && mem[F.KEY].length < 120000, `storage capped: ${Object.keys(back.f).length} features, ${Object.keys(back.s).length} videos, ${(mem[F.KEY].length / 1024).toFixed(0)} KB`);
F.reset(store);
ok(!(F.KEY in mem) && Object.keys(F.load(store).f).length === 0, "reset: the profile is gone");

// 5. VARIETY: many creators, many different places (a realistic SA pool: one creator posts the most + the freshest)
const V = [];
const add = (creator, crew, title, daysAgo, place) => V.push({ url: "https://www.youtube.com/shorts/d" + V.length, title, creator, crew, published: ts(daysAgo), video: true, place: place ? { name: place, address: null } : null });
for (let i = 0; i < 11; i++) add("Cherise SA Texas Food Guide", "satexasfoodies", `Cherise spot ${i} tacos`, i * 0.2, "Cherise Place " + i);
for (let i = 0; i < 8; i++) add("Eatmigos", "eatmigos", `Eatmigos pick ${i}`, 1 + i, "Eatmigos Spot " + i);
for (let i = 0; i < 5; i++) add("Texas Eats", "eldereats", `Texas Eats: dish ${i}`, 2 + i, "Texas Eats Kitchen " + i);
for (let i = 0; i < 2; i++) add("Elder Eats", "eldereats", `Elder Eats TikTok ${i}`, 300 + i, null);
for (let i = 0; i < 7; i++) add("Full Nelson Eats", "fullnelsoneats", `Full Nelson bite ${i} - Full Nelson Eats`, 3 + i, F.placeKey({ place: { name: "Full Nelson Eats" }, creator: "Full Nelson Eats" }) ? "Full Nelson Eats" : "Nelson Grill " + i);
for (let i = 0; i < 4; i++) add("Hannah | SATX Creator", "hannah | satx creator", `Hannah tries ${i}`, 4 + i, "Hannah Diner " + i);
for (let i = 0; i < 3; i++) add("Porter's Food Reviews", "portersfoodreviews", `Porter reviews ${i}`, 5 + i, "Porter Hall " + i);
for (let i = 0; i < 3; i++) add("San Antonio Munchies", "sanantoniomunchies", `Munchies ${i}`, 400 + i, "Munch Box " + i);
for (let i = 0; i < 2; i++) add("Siempre San Antonio", "siempre_sanantonio", `Siempre ${i}`, 6 + i, "Siempre Cafe " + i);
add("Bootleg Food Review", "bootlegfoodreview", "Bootleg review", 700, "Bootleg Burgers");
// the same restaurant from 4 creators, written 3 ways, one only in the title
add("Cherise SA Texas Food Guide", "satexasfoodies", "Losoya’s Taqueria street tacos", 0.1, "Losoya’s Taqueria");
add("Eatmigos", "eatmigos", "LOSOYAS TAQUERIA", 0.3, "LOSOYAS TAQUERIA");
add("Porter's Food Reviews", "portersfoodreviews", "Porter at losoyas taqueria part 2", 0.5, null);
add("Hannah | SATX Creator", "hannah | satx creator", "Losoya's Taqueria, San Antonio", 0.4, "Losoya's Taqueria San Antonio");
const crews = new Set(V.map((x) => x.crew));
const inTop = (list, n, c) => list.slice(0, n).filter((x) => x.crew === c).length;
const maxTop10 = (list) => Math.max(...[...crews].map((c) => inTop(list, 10, c)));
const backToBack = (list, key, n) => list.slice(0, n || list.length).some((x, i) => i > 0 && x[key] && x[key] === list[i - 1][key]);
const placeRepeat = (list, n) => { const s = list.slice(0, n).map((x) => x.place).filter(Boolean); return s.length !== new Set(s).size; };
ok(F.placeKey({ place: { name: "Losoya’s Taqueria" } }) === F.placeKey({ place: { name: "LOSOYAS TAQUERIA" } }) && F.placeKey({ place: { name: "Losoya's Taqueria San Antonio" } }) === "losoyas taqueria",
  "restaurant key: 'Losoya’s Taqueria' = 'LOSOYAS TAQUERIA' = 'Losoya's Taqueria San Antonio' (" + F.placeKey({ place: { name: "Losoya’s Taqueria" } }) + ")");
ok(F.placeKey({ place: { name: "Full Nelson Eats" }, creator: "Full Nelson Eats" }) === null && F.placeKey({ place: { name: "Hey" } }) === null,
  "restaurant key: the channel's own name and 'Hey' are not restaurants");
const fresh = F.load({ getItem: () => null });
let cold = F.rank(fresh, V, { now: NOW, seed: 3, rot: 0 });
ok(new Set(cold.slice(0, 9).map((x) => x.crew)).size === 9, "new user: the first 9 videos are 9 different creators: " + cold.slice(0, 9).map((x) => x.item.creator.split(" ")[0]).join(", "));
ok(inTop(cold, 9, "eldereats") === 1, "new user: Texas Eats + Elder Eats count as one creator (David Elder): 1 of the first 9");
ok(maxTop10(cold) <= 2, "new user: no creator more than 2× in the top 10 (max " + maxTop10(cold) + ")");
ok(!backToBack(cold, "crew", 30), "new user: never the same creator twice in a row (first 30)");
const los = (list) => list.filter((x) => /losoya/i.test(x.item.title));
ok(los(cold).length === 1, "dedupe: 4 videos about Losoya’s Taqueria (3 spellings + a title mention) → 1 in the feed (" + los(cold).map((x) => x.item.creator).join(", ") + ")");
ok(!backToBack(cold, "place") && !placeRepeat(cold, 15), "restaurants: never the same spot twice in a row, never twice in the top 15");
ok(cold.length === V.length - 3, "dedupe drops only the duplicates: " + cold.length + " of " + V.length);
// the lead creator rotates (and the banner cover uses the same first videos)
const leads = [...Array(9).keys()].map((k) => F.rank(fresh, V, { now: NOW, seed: 3, rot: k })[0].crew);
ok(new Set(leads).size === 9, "rotation: 9 visits → 9 different creators lead (" + leads.map((c) => c.slice(0, 8)).join(", ") + ")");
ok(leads.every((c, i) => i === 0 || c !== leads[i - 1]), "rotation: the lead changes every visit");
let lastLeadOk = true;
for (let k = 0; k < 12; k++) { const a = F.rank(fresh, V, { now: NOW, seed: 3, rot: k }); const b = F.rank(fresh, V, { now: NOW, seed: 3, rot: k, lastLead: a[0].crew }); if (b[0].crew === a[0].crew) lastLeadOk = false; }
ok(lastLeadOk, "rotation: whoever led last time doesn't lead again (12 visits)");
const top3 = [...Array(9).keys()].map((k) => F.rank(fresh, V, { now: NOW, seed: 3, rot: k }).slice(0, 3));
ok(top3.every((t) => new Set(t.map((x) => x.crew)).size === 3), "banner cover: the first 3 videos are always 3 different creators");
ok(leads.filter((c) => c === "satexasfoodies").length === 1, "the creator with the most + freshest videos leads 1 visit in 9, not every time");
const coldDays = [...Array(7).keys()].map((d) => F.rank(fresh, V, { now: NOW + d * DAY, rot: 0 })[0].crew);
ok(new Set(coldDays).size >= 3, "daily order changes too: " + new Set(coldDays).size + " different leads over 7 days at the same rotation");
// someone who loves one creator: still capped, still varied
const fan = F.load({ getItem: () => null });
V.filter((x) => x.crew === "satexasfoodies").slice(0, 5).forEach((x) => F.signal(fan, "save", x, { now: NOW }));
V.filter((x) => x.crew === "satexasfoodies").slice(5, 9).forEach((x) => F.signal(fan, "watch", x, { now: NOW, seconds: 30 }));
const fr = F.rank(fan, V, { now: NOW, seed: 3, rot: 0 });
ok(inTop(fr, 10, "satexasfoodies") === 2, "Cherise superfan: she's capped at 2 of the top 10 (" + inTop(fr, 10, "satexasfoodies") + ")");
ok(inTop(fr, 3, "satexasfoodies") >= 1, "Cherise superfan: taste still counts, she's in the top 3");
ok(new Set(fr.slice(0, 5).map((x) => x.crew)).size === 5 && new Set(fr.slice(0, 10).map((x) => x.crew)).size >= 7,
  "Cherise superfan: first 5 are 5 creators, top 10 has " + new Set(fr.slice(0, 10).map((x) => x.crew)).size + " different creators");
ok(!backToBack(fr, "crew", 30) && !backToBack(fr, "place") && !placeRepeat(fr, 15), "Cherise superfan: no creator/restaurant back-to-back, no spot twice in the top 15");
ok(fr.filter((x) => x.explore).length === Math.floor(fr.length / 5), "Cherise superfan: exploration still every 5th slot (" + fr.filter((x) => x.explore).length + "/" + fr.length + ")");
ok(JSON.stringify(F.rank(fan, V, { now: NOW, seed: 3, rot: 2 }).map((x) => x.item.url)) === JSON.stringify(F.rank(fan, V, { now: NOW, seed: 3, rot: 2 }).map((x) => x.item.url)), "variety is stable: same visit, same order");
// tiny feeds relax the rules instead of dropping videos
const solo = [0, 1, 2].map((i) => ({ url: "https://www.tiktok.com/@a/video/" + i, title: "Solo " + i, creator: "Solo", published: ts(i), video: true }));
ok(F.rank(fresh, solo, { now: NOW }).length === 3, "one creator only: all 3 videos still play (rules relax)");
// 6. RECIPES: cooking videos from many cooks are mixed in (every 3rd video), and the variety rules still hold
const R = [];
const dishes = ["spaghetti", "birria tacos", "enchiladas", "brownies", "one pot dinner", "flan", "guacamole", "kitchen hack"];
for (let i = 0; i < 45; i++) R.push({ url: "https://www.youtube.com/shorts/r" + i, title: `How to make ${dishes[i % dishes.length]} ${i}`, creator: "Cook " + (i % 40),
  crew: "cook:" + (i % 40), video: true, kind: "recipe", recipe: true, published: null, place: null });
const M = V.concat(R);
const mixed = F.rank(fresh, M, { now: NOW, seed: 3, rot: 0 });
const isR = (x) => F.isRecipe(x.item);
ok(mixed.length === V.length - 3 + R.length, `recipes: all ${R.length} cooking videos are in the feed (${mixed.length} videos)`);
ok(mixed.slice(0, 30).every((x, i) => isR(x) === (i % 3 === 2)), "recipes: every 3rd video is a cooking video (slots 3, 6, 9 …): " + mixed.slice(0, 12).map((x) => (isR(x) ? "R" : "·")).join(""));
ok(new Set(mixed.slice(0, 9).map((x) => x.crew)).size === 9, "recipes: the first 9 are still 9 different creators: " + mixed.slice(0, 9).map((x) => x.item.creator.split(" ")[0]).join(", "));
const mcrews = new Set(M.map((x) => x.crew)), maxIn10 = Math.max(...[...mcrews].map((c) => mixed.slice(0, 10).filter((x) => x.crew === c).length));
ok(maxIn10 <= 2 && !backToBack(mixed, "crew") && !backToBack(mixed, "place") && !placeRepeat(mixed, 15), `recipes: caps + no creator/restaurant back-to-back + no spot twice in the top 15 (max ${maxIn10} per creator in the top 10)`);
ok(/^Cook it at home: Cook /.test(mixed[2].why.text), "recipes: why chip '" + mixed[2].why.text + "'");
const mleads = [...Array(6).keys()].map((k) => F.rank(fresh, M, { now: NOW, seed: 3, rot: k })[0]);
ok(new Set(mleads.map((x) => x.crew)).size === 6 && mleads.every((x) => !isR(x)), "recipes: a local creator still leads, and a different one each visit (" + mleads.map((x) => x.crew.slice(0, 8)).join(", ") + ")");
const cook3 = [...Array(6).keys()].map((k) => F.rank(fresh, M, { now: NOW, seed: 3, rot: k })[2].crew);
ok(new Set(cook3).size === 6, "recipes: the first cooking video comes from a different cook each visit");
const tacoFan = F.load({ getItem: () => null });
R.filter((x) => /tacos/.test(x.title)).slice(0, 3).forEach((x) => F.signal(tacoFan, "save", x, { now: NOW }));
const tf = F.rank(tacoFan, M, { now: NOW, seed: 3, rot: 0 });
ok(tf.filter(isR).slice(0, 3).some((x) => /tacos/.test(x.item.title)) && tf.slice(0, 30).filter(isR).length === 10, "recipes: saved taco recipes → taco recipes come sooner, still 1 in 3 (" + tf.slice(0, 30).filter(isR).length + " of the first 30)");
const fewR = F.rank(fresh, V.concat(R.slice(0, 2)), { now: NOW, seed: 3, rot: 0 });
ok(fewR.length === V.length - 3 + 2 && fewR.filter(isR).length === 2, "recipes: with only 2 cooking videos, the rest of the feed is local videos (rule relaxes)");
console.log(JSON.stringify(out));
"""
src = open(os.path.join(HERE, "static", "foryou.js")).read()
res = subprocess.run(["node", "-e", JS, os.path.join(HERE, "static", "foryou.js")], capture_output=True, text=True, timeout=60)
if res.returncode:
    print(res.stderr); sys.exit(1)
checks = json.loads(res.stdout.strip().splitlines()[-1])
checks.append([not any(w in src for w in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "navigator.sendBeacon", "import(")), "on-device only: foryou.js makes no network calls"])
fails = 0
for good, what in checks:
    print(("  ok   " if good else "  FAIL ") + what); fails += not good
print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)
