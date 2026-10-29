"""🚘 Puro Pinche Lowrider (v49.16, was "Lowrider Hop"): Juegos game 3, an original one-thumb arcade game (static/lowrider.js, loaded the
first time it's opened; its San Antonio stage, static/lowrider-sa.js, the first time that stage is picked; art in static/lowrider/).

1. Static: the game files never name a real car make/model, store or soda (or their slogans); Feria is earned only by playing (no money,
   no outside links; the only $ is Chisme's own App Store goal, which comes from app.js); 3 rides (The '64 (Primer) free, the candy '64
   900 Feria, El Jefe '76 2400), 5 paints (no gold), the Primer's bronze wheels; Abuela Crossing + La Chancla + the Trail Ride; 12 made-up
   businesses (sponsor: false) + Chisme's "YOUR BUSINESS HERE / Ask Chisme" house ad; San Antonio's landmarks, parody stores, taquerías,
   7 traffic types, gas / soda / tacos, 10 horse coats; no yellow in any color. Node: grades, combo tiers, the versioned save (a v1 save
   keeps its '64 + paint; garbage in → a fresh save).
2. WebKit iPhone 13: Juegos lists it third (with its own art), it loads lazily, the canvas draws at devicePixelRatio, no errors.
   TAP hops at once (v49.29.1; holding while rising goes higher), TAP right before landing = PERFECT HOP!; no tap = YOU SCRAPED IT!; the combo goes x2 at a 3 streak;
   an obstacle costs a wheel; Abuela Crossing stops the car before the crosswalk (+500 RESPETO, "Gracias, mijo."); La Chancla;
   game over saves Feria / best / runs in localStorage "lowrider_v1"; the Garage shows locked rides + prices, unlocks one with Feria
   (saved, survives a reload) and buys + equips paint; Share with a #puro-pinche-lowrider link; trophies; the house billboard every
   3rd–4th billboard; sound follows the app setting; it pauses when hidden; Muertos marigolds; no yellow in the DOM or the canvas.
   San Antonio: loads lazily, traffic you can hop (a hit costs a wheel) with comic lines, pickups, gas 0 ends the run, the Trail Ride
   (the car stops before the riders, a hop is a salute: +YEEHAW, no horse is ever hit), the App Store goal hidden in the native app.
3. Chromium 1280×800 (desktop site): opens and plays.
Screenshots (LOWRIDER_SHOTS, default screenshots/): title, gameplay-hop, perfect-landing, abuela-crossing, la-chancla, garage-locked,
garage-unlocked, game-over, juegos-list, desktop (1280×800), car-primer, car-64, billboards, sa-stage, sa-trail-ride."""
import asyncio, json, os, re, subprocess
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8485")
OUT = os.environ.get("LOWRIDER_SHOTS", os.path.join(HERE, "screenshots")); os.makedirs(OUT, exist_ok=True)
INIT = ("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');"
        " localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1');")
SPEECH = """(() => { window.__spoken = [];
  const fake = { speak(u) { __spoken.push({ text: u.text, lang: u.lang }); }, cancel() {}, getVoices() { return [{ lang: 'es-MX', name: 'Test es-MX' }, { lang: 'en-US', name: 'Test en-US' }]; }, addEventListener() {}, removeEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {}
  window.SpeechSynthesisUtterance = function (t) { this.text = t; };
  try { Object.defineProperty(navigator, 'share', { value: (d) => { window.__shared = d; return Promise.resolve(); }, configurable: true }); } catch (e) {} })()"""
SEASON = "if (!localStorage.getItem('chisme-season-pin')) localStorage.setItem('chisme-season-pin', 'muertos');"   # screenshots: the Día de Muertos look (in season now)
L = "ChismeLowrider.current"; D = L + ".debug"; S = L + ".state"

fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

YELLOW_JS = r"""const yellow = ([r, g, b, a]) => { if (a != null && a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.05) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= 0.85 || l <= 0.2)); };"""
DOM_SCAN = r"""(sel) => { """ + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const els = [...document.querySelectorAll(sel)].flatMap((r) => [r, ...r.querySelectorAll('*')]).filter((e) => e.getClientRects().length && e.tagName !== 'CANVAS');
  const bad = [];
  for (const e of els) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.textShadow, cs.borderTopColor, cs.fill, cs.stroke]) if (rgb(v).some(yellow)) bad.push(e.className + ' ' + String(v).slice(0, 50)); }
  return { n: els.length, bad: [...new Set(bad)].slice(0, 6) }; }"""
CANVAS_SCAN = r"""() => { """ + YELLOW_JS + r"""
  const c = document.querySelector('.lr-cv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0, all = 0; const ex = new Set();
  for (let i = 0; i < d.length; i += 16) { all++; if (yellow([d[i], d[i + 1], d[i + 2]])) { n++; if (ex.size < 5) ex.add('#' + [d[i], d[i + 1], d[i + 2]].map((v) => v.toString(16).padStart(2, '0')).join('')); } }
  return { n, all, ex: [...ex] }; }"""

GAME_FILES = ["static/lowrider.js", "static/lowrider-sa.js", "static/lowrider-sa-chase.js"]
BANNED = ["impala", "chevy", "chevrolet", "bowtie", "altima", "nissan", "walmart", "wal-mart", "coca-cola", "coca cola", "home depot", "hotbox", "dave's not here", "daves not here",
          "here everything's better", "here everything’s better", "save money. live better", "more saving. more doing"]
def static():
    print("== static")
    js = open(os.path.join(HERE, "static/lowrider.js"), encoding="utf-8").read()
    sa = open(os.path.join(HERE, "static/lowrider-sa.js"), encoding="utf-8").read()
    chase = open(os.path.join(HERE, "static/lowrider-sa-chase.js"), encoding="utf-8").read()
    jg = open(os.path.join(HERE, "static/juegos.js"), encoding="utf-8").read()
    app = open(os.path.join(HERE, "static/app.js"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "static/style.css"), encoding="utf-8").read(); lcss = css[css.index("Juegos game 3: Puro Pinche Lowrider"):]
    stub = jg[jg.index("game 3: Puro Pinche Lowrider"):jg.index("GAMES.push({ id: \"lowrider\"")]
    for word in BANNED:
        check(not any(word in t.lower() for t in (js, sa, chase, stub, lcss)), f"no '{word}' in the game files")
    check(not any(re.search(r"\bH-E-B\b|\bHEB\b|\bGM\b|\bCoke\b", t) for t in (js, sa, chase)), "no H-E-B / HEB / GM / Coke (H-E-Bae, Gualmart, Hon Dipo are our own parodies)")
    kb = len(js.encode()) // 1024, len(sa.encode()) // 1024
    check(len(js.encode()) < 210_000 and len(sa.encode()) < 80_000 and len(chase.encode()) < 80_000, f"lowrider.js {kb[0]} KB, the San Antonio stage its own file ({kb[1]} KB), the art in static/lowrider/")
    for f in ("title.webp", "thumb.webp"): check(os.path.getsize(os.path.join(HERE, "static/lowrider", f)) < 200_000, f"static/lowrider/{f} ({os.path.getsize(os.path.join(HERE, 'static/lowrider', f)) // 1024} KB)")
    check(os.path.getsize(os.path.join(HERE, "static/fonts/ppl-display.woff2")) < 20_000 and os.path.exists(os.path.join(HERE, "static/fonts/LICENSE-UnifrakturCook-OFL.txt")), "the title font is a subset with its OFL license")
    for name, t in (("lowrider.js", js), ("lowrider-sa.js", sa), ("lowrider-sa-chase.js", chase)):
        check(not re.search(r"\$\s?\d|USD|in-app purchase|checkout|\bstripe\b|cash ?app|paypal|venmo", t, re.I), f"{name}: no money (Feria is earned only by playing; the only $ is Chisme's own goal, from app.js)")
        check(not re.search(r"https?://", t), f"{name}: no outside links or requests")
    check("window.__chismeGoal" in app and "FC_GOAL.url" in app[app.index("window.__chismeGoal"):app.index("window.__chismeGoal") + 900], "the App Store goal (amount + link) comes from app.js's From Chisme card")
    check("Feria is earned only by playing" in js and "Nothing here costs real money" in js and "More rides coming." not in js, "the Garage: unlock rides with Feria only, nothing costs real money")
    check(not re.search(r"coming soon", js + sa + chase, re.I), "no 'coming soon' clutter")
    sw = open(os.path.join(HERE, "static/sw.js")).read()
    check(all(x in sw for x in ("/static/lowrider.js?v=${BUILD}", "/static/lowrider-sa.js?v=${BUILD}", "/static/lowrider-sa-chase.js?v=${BUILD}", "/static/lowrider/title.webp?v=${BUILD}", "/static/fonts/ppl-display.woff2")), "the service worker caches the game, the SA stage, the art + font (offline)")
    dk = open(os.path.join(HERE, "static/desktop.js")).read()
    check('"#lowrider"' in app and '"#puro-pinche-lowrider"' in app and 'lowrider: "#puro-pinche-lowrider"' in dk, "#puro-pinche-lowrider deep link (app + desktop site); #lowrider still works")
    check("Puro Pinche Lowrider" in open(os.path.join(HERE, "website.py"), encoding="utf-8").read(), "the website names it Puro Pinche Lowrider")
    node = r"""
      global.window = { addEventListener() {}, removeEventListener() {} }; global.localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = String(v); }, removeItem(k) { delete this._d[k]; } };
      require(process.argv[1]); require(process.argv[2]); require(process.argv[3]); const L = window.ChismeLowrider, SA = L.stages.sa;
      const hue = (h) => { const n = parseInt(h.slice(1), 16), r = (n >> 16) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, l = (mx + mn) / 2;
        if (d < 0.05) return false; const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false; let H = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (H < 0) H += 360;
        return (H >= 38 && H <= 70) || (H >= 25 && H < 38 && (l >= 0.85 || l <= 0.2)); };
      const hexes = (o) => JSON.stringify(o).match(/#[0-9a-fA-F]{6}\b/g) || [];
      const fs = require("fs"), saHex = ((fs.readFileSync(process.argv[2], "utf8") + fs.readFileSync(process.argv[3], "utf8")).match(/#[0-9a-fA-F]{6}\b/g) || []).filter(hue);
      const t = L.migrate({ v: 1, feria: 50, owned: { paint: ["turq", "gold", "x"] }, equip: { paint: "turq" }, runs: [{ score: 9, at: 1 }] }), f = L.fresh();
      const runs = { runs: [] }; L.BOARD.submit(runs, { score: 5, at: 2 }); L.BOARD.submit(runs, { score: 50, at: 3 }); const rank = L.BOARD.submit(runs, { score: 20, at: 4 });
      const slot = {id:"test",name:"Test",line:"Hello barrio",colors:["#000000","#FFFFFF","#FF1A7F"],art:"text",sponsor:true};
      if (!L.SPONSOR_SLOTS.every(s=>s.id && s.line && !s.sponsor) || !L.setSponsors([slot]) || L.setSponsors([{...slot,name:"<script>"}]) || L.setSponsors([{...slot,line:"https://example.com"}]) || L.setSponsors([slot,slot]) || !L.setSponsors([])) throw Error("sponsor validation");
      const bb = (n) => SA.billboards(n).map((s) => s && s.name);
      console.log(JSON.stringify({ cars: L.CARS.map((c) => [c.id, c.name, c.price]), paints: L.PAINTS.map((p) => [p.name, p.price]), events: Object.keys(L.EVENTS), trail: L.EVENTS.trail, signs: L.SIGNS,
        stages: L.STAGES.map((s) => s.id), paintYellow: L.PAINTS.flatMap((p) => Object.values(p).filter((v) => typeof v === "string" && v[0] === "#" && v.length === 7 && hue(v))),
        carYellow: [...hexes(L.CARS), ...hexes(L.WHEELS), ...hexes(L.PATCH)].filter(hue), bronze: L.WHEELS.bronze.dish.map((x) => x[1]),
        signYellow: L.SIGNS.flatMap((s) => s.colors.filter(hue)), saHex, ach: L.ACH.map((a) => a.name), tiers: [0, 2, 3, 6, 10, 16, 40].map((s) => L.TIERS[L.tierOf(s)].x),
        grades: [0.05, 0.1, 0.2, 0.3, 0.5].map((d) => L.gradeFor(d, false)), late: [0.02, 0.08].map((d) => L.gradeFor(d, true)),
        garbage: JSON.stringify(L.migrate("nope")) === JSON.stringify(f), fresh: { cars: f.owned.car, car: f.equip.car },
        mig: { feria: t.feria, owned: t.owned.paint, cars: t.owned.car, car: t.equip.car, equip: t.equip.paint, runs: t.runs.length }, rank, key: L.SAVE_KEY, week: L.isoWeek(Date.UTC(2026, 9, 3, 12)),
        sa: { landmarks: SA.LANDMARKS.map((l) => l.name || l.tag || l.id), stores: SA.STORES.map((s) => s.name || s.id), taqs: SA.TAQS.map((s) => s.name || s.id), traffic: SA.traffic.map((x) => [x.id, x.lines.near.length, x.lines.over.length, x.lines.hit.length]),
          picks: Object.keys(SA.picks), coats: SA.COATS.map((c) => c.id), coatHex: SA.COATS.flatMap((c) => hexes(c)), fuel: SA.fuel, bbWeb: bb(false).slice(0, 8), bbNative: bb(true).slice(0, 8) } })); """
    r = json.loads(subprocess.run(["node", "-e", node, os.path.join(HERE, "static/lowrider.js"), os.path.join(HERE, "static/lowrider-sa.js"), os.path.join(HERE, "static/lowrider-sa-chase.js")], capture_output=True, text=True, check=True).stdout)
    check(r["cars"] == [["primer", "The '64 (Primer)", 0], ["64", "The '64 (Candy)", 900], ["jefe", "El Jefe '76", 2400],
                         ["lifted", "Lifted Pickup", 1600], ["lowtruck", "Lowrider Pickup", 1800], ["monster", "Monster Truck", 3200],
                         ["tank", "Tank", 4500], ["jet", "Fighter Jet", 6000], ["horse", "Cowboy on a Horse", 2000],
                         ["paleta", "Paleta Cart", 1200], ["c10", "Chafa C10 Hopper", 2200], ["raspa", "Raspa Rocket", 2600], ["bruja", "Witch on a Broom", 2800],
                         ["chariot", "Chariot Lowrider", 3600], ["ofrenda", "Ofrenda Float", 3900], ["fiesta", "Fiesta Float", 4200], ["barge", "Calavera River Barge", 5200]], f"17 rides: the Primer is free, the rest unlock with Feria {r['cars']}")
    check(r["fresh"] == {"cars": ["primer"], "car": "primer"}, "a new player starts in The '64 (Primer)")
    check(r["bronze"][1] == "#c47a4e" and not r["carYellow"], f"the Primer's bronze wheels (no gold / yellow in any ride, wheel or patch) {r['carYellow']}")
    check([p[0] for p in r["paints"]] == ["Candy red", "Turquoise", "Purple", "Black cherry", "Pearl white"] and r["paints"][0][1] == 0, f"paint: 5 colors, no gold {r['paints']}")
    check(r["events"] == ["abuela", "chancla", "trail"] and r["trail"]["horses"] == 10, "3 events: Abuela Crossing, La Chancla, the (San Antonio) Trail Ride with 10 horses")
    check(r["stages"] == ["blvd", "sa"], "2 stages: the Boulevard and San Antonio")
    check(not r["paintYellow"] and not r["signYellow"] and not r["saHex"], f"no yellow in paint, sign or San Antonio colors {r['paintYellow']} {r['signYellow']} {r['saHex'][:6]}")
    signs = r["signs"]; house = [s for s in signs if s.get("house")]
    check(len(signs) == 13 and all(s["sponsor"] is False and s["name"] and s["tagline"] and len(s["colors"]) == 3 and s["slot"] in ("store", "billboard") for s in signs),
          "13 data-driven signs {name, tagline, colors, slot, sponsor:false}")
    check(len(house) == 1 and house[0]["name"] == "YOUR BUSINESS HERE" and house[0]["tagline"] == "Ask Chisme" and house[0]["slot"] == "billboard", "Chisme's house ad: YOUR BUSINESS HERE / Ask Chisme (house: true)")
    check(not re.search(r"sponsored", json.dumps(signs), re.I), "no 'Sponsored' label")
    check(r["ach"] == ["First Hop", "Puro Pinche Style", "Not a Scratch", "Ay Güey", "Hydraulic Addiction", "Respect Your Elders"], "the 6 trophies")
    check(r["tiers"] == [1, 1, 2, 5, 10, 25, 25], f"combo x2 / x5 / x10 / x25 {r['tiers']}")
    check(r["grades"] == ["perfect", "perfect", "puro", "ay", "scraped"] and r["late"] == ["puro", "ay"], f"landing grades by how early (or a hair late) the tap came {r['grades']} {r['late']}")
    check(r["garbage"] and r["mig"] == {"feria": 50, "owned": ["candy", "turq"], "cars": ["primer", "64"], "car": "64", "equip": "turq", "runs": 1} and r["key"] == "lowrider_v1",
          f"versioned save: a v1 save keeps its Feria + paint, owns the Primer + its '64 (still riding it); bad data is dropped {r['mig']}")
    check(r["rank"] == 1 and r["week"] == "2026-W40", "best runs sorted; ISO week for a later weekly board")
    s_ = r["sa"]
    check(len(s_["landmarks"]) >= 30 and all(n in s_["landmarks"] for n in ("The Alamo", "Tower of the Americas", "San Fernando Cathedral", "Mission San José", "Market Square · El Mercado", "Hays Street Bridge")), f"San Antonio: {len(s_['landmarks'])} landmarks with name tags")
    check(s_["stores"] == ["Hon Dipo", "Gualmart", "H-E-Bae"] and len(s_["taqs"]) == 3, f"parody stores {s_['stores']} + made-up taquerías {s_['taqs']}")
    check([x[0] for x in s_["traffic"]] == ["cop", "trooper", "fbi", "construction", "beater", "cuh", "troca"] and all(all(n and n >= 1 for n in x[1:]) for x in s_["traffic"]),
          "7 data-driven traffic types, each with near / hopped / hit lines")
    check(s_["picks"] == ["gas", "soda", "taco"] and s_["fuel"]["range"] > 0, "pickups: gas, soda, tacos; the tank runs down")
    check(s_["coats"] == ["bay", "black", "white", "palomino", "paint", "appaloosa", "chestnut", "grey", "buckskin", "roan"] and len(set(s_["coatHex"])) >= 20, "Trail Ride: 10 horse coats (palomino is tan + cream, never yellow)")
    check(s_["bbWeb"][0] == "Help get Chisme on the App Store" and "Help get Chisme on the App Store" not in s_["bbNative"] and "YOUR BUSINESS HERE" in s_["bbNative"],
          f"San Antonio billboards: Chisme's App Store goal on the web, the house ad in the app {s_['bbWeb'][:3]} {s_['bbNative'][:3]}")

async def phone(p, b, hash_="#puro-pinche-lowrider", extra="", reduced=None, ua=None):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    if ua: dev["user_agent"] = dev["user_agent"] + " " + ua
    ctx = await b.new_context(**dev, service_workers="block", **({"reduced_motion": reduced} if reduced else {}))
    await ctx.add_init_script(SEASON); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT + extra); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append("pageerror " + str(e)[:200])); pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" else None)
    await pg.goto(BASE + "/" + hash_, wait_until="domcontentloaded")
    if hash_ in ("#lowrider", "#puro-pinche-lowrider"): await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current && __chisme.juegos && __chisme.juegos.id === 'lowrider'", timeout=90000)
    else: await pg.wait_for_function("window.__chisme && __chisme.juegos && __chisme.juegos.id", timeout=90000)
    await pg.wait_for_timeout(800)
    return ctx, pg

async def start(pg):
    await pg.click('.lr-ov [data-act="start"]'); await pg.wait_for_timeout(150)
    if await pg.evaluate(S + ".overlay") == "howto": await pg.click('.lr-ov [data-act="gotit"]')
    await pg.evaluate(D + ".freeze(true); " + D + ".clear(); " + D + ".auto(false); " + D + ".events(false)")

async def land_with_tap(pg, before=0.06):
    await pg.evaluate("(() => { const d = %s; let n = 0; while (%s.tLand > %f && n++ < 400) d.step(1 / 120); d.press(); d.step(%f); })()" % (D, S, before, before + 0.15))

async def hop(pg, c=0.6, before=0.06):
    hold = max(0.0, (c - 0.35) / 0.65 * 0.28)   # v49.29.1: the hop fires on press; holding while rising adds height
    await pg.evaluate(D + ".press(); " + D + f".step({max(hold, 0.01):.3f}); " + D + ".release(); " + D + ".step(0.05)"); await land_with_tap(pg, before)

async def webkit(p):
    b = await p.webkit.launch()
    print("\n== WebKit iPhone 13: Juegos list, lazy load")
    ctx, pg = await phone(p, b, "#juegos")
    picks = await pg.evaluate("[...document.querySelectorAll('.game-pick')].map((b) => [b.dataset.game, b.querySelector('b').textContent, !!b.querySelector('.gp-thumb img[src*=lowrider]')])")
    check([x[1] for x in picks] == ["The Juan That Got Away", "Chismería", "Puro Pinche Lowrider"] and picks[2][2], f"Juegos lists Puro Pinche Lowrider third, with its key-art thumbnail {picks}")
    check(await pg.evaluate("!window.ChismeLowrider && !document.querySelector('script[src*=\"lowrider.js\"]')"), "lowrider.js isn't loaded until it's opened")
    await pg.evaluate("document.querySelector('.game-pick[data-game=lowrider]').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(300)
    await pg.screenshot(path=os.path.join(OUT, "juegos-list.png"))
    await pg.click('.game-pick[data-game="lowrider"]')
    await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current", timeout=30000); await pg.wait_for_timeout(600)
    s = await pg.evaluate(S)
    check(s["mode"] == "title" and s["overlay"] == "title" and "Puro Pinche Lowrider" in s["overlayText"] and "Cruise" in s["overlayText"] and "Garage" in s["overlayText"] and "San Antonio" in s["overlayText"],
          "opens on its title: Puro Pinche Lowrider, the stage pick, ▶ Cruise, Garage, Best runs, Trophies")
    check(await pg.evaluate("document.querySelector('.lr-hero-img').complete && document.querySelector('.lr-hero-img').naturalWidth > 0"), "the key art loads")
    check(s["backing"] == [round(s["css"][0] * s["dpr"]), round(s["css"][1] * s["dpr"])] and s["dpr"] == 3, f"the canvas draws at devicePixelRatio {s['backing']} css {s['css']}")
    check(await pg.evaluate("(() => { const c = document.querySelector('.lr-cv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = new Set(); for (let i = 0; i < d.length; i += 4000) n.add(d[i] + ',' + d[i + 1]); return n.size; })()") > 40, "the boulevard is drawn")
    check(s["muted"] is False, "sound is on by default (the app's sound setting is on)")
    check(not pg.errs, f"no console errors {pg.errs[:3]}"); await ctx.close()

    print("\n== hop, land, combo, wheels")
    ctx, pg = await phone(p, b)
    await pg.evaluate(D + ".fs(); " + D + ".freeze(true); " + D + ".step(1.6)"); await pg.wait_for_timeout(400); await pg.screenshot(path=os.path.join(OUT, "title.png"))
    check(await pg.evaluate(S + ".fullscreen"), "the title can go full screen (the attract-mode '64 cruises under the logo)")
    await start(pg); s = await pg.evaluate(S)
    check(s["mode"] == "run" and s["fullscreen"], "▶ Cruise plays full screen (after the how-to the first time)")
    await pg.evaluate(D + ".step(0.4); " + D + ".press()"); s = await pg.evaluate(S)
    check(s["air"] and not s["charging"], "v49.29.1: a press hops at once (no wind-up)")
    await pg.evaluate(D + ".step(0.3); " + D + ".release()"); s = await pg.evaluate(S)
    check(s["air"] and s["y"] > 80, f"…and holding while rising goes higher ({s['y']:.0f} units up)")
    await pg.screenshot(path=os.path.join(OUT, "gameplay-hop.png"))
    await land_with_tap(pg); s = await pg.evaluate(S)
    check(s["lastGrade"] == "perfect" and s["score"] > 0 and s["runFeria"] > 0 and "first" in s["ach"], f"TAP right before landing: PERFECT HOP! (+{s['score']}, +{s['runFeria']} Feria, First Hop)")
    await pg.screenshot(path=os.path.join(OUT, "perfect-landing.png"))
    await pg.evaluate(D + ".step(0.6)"); await hop(pg, 0.5, 0.18); s = await pg.evaluate(S)
    check(s["lastGrade"] == "puro", f"a slightly early tap: PURO STYLE ({s['lastGrade']})")
    await pg.evaluate(D + ".step(0.6)"); await hop(pg, 0.5, 0.33); s = await pg.evaluate(S)
    check(s["lastGrade"] == "ay" and s["streak"] == 0, f"too early: AY GÜEY! and the streak drops ({s['lastGrade']}, {s['streak']})")
    await pg.evaluate(D + ".step(0.6); " + D + ".press(); " + D + ".step(0.4); " + D + ".release(); " + D + ".step(2)"); s = await pg.evaluate(S)
    check(s["lastGrade"] == "scraped" and s["streak"] == 0, "no tap: YOU SCRAPED IT!")
    for _ in range(3): await pg.evaluate(D + ".step(0.5)"); await hop(pg, 0.45)
    s = await pg.evaluate(S); check(s["streak"] == 3 and s["mult"] == 2, f"3 clean hops in a row: x2 combo ({s['streak']}, x{s['mult']})")
    await pg.evaluate(D + ".set({ streak: 15 })"); await pg.evaluate(D + ".step(0.5)"); await hop(pg, 0.45); s = await pg.evaluate(S)
    check(s["mult"] == 25, f"16 in a row: x25 ({s['mult']})")
    lives = s["lives"]; await pg.evaluate(D + ".step(0.6); " + D + ".spawn('cone', 60); " + D + ".step(1.2)"); s = await pg.evaluate(S)
    check(s["lives"] == lives - 1 and s["mult"] == 1, f"hitting a cone costs a wheel and the combo ({lives} → {s['lives']})")
    await pg.evaluate(D + ".step(1.5); " + D + ".spawn('couch', 230)")
    await pg.evaluate("(() => { const d = %s; d.auto(true); d.step(2.5); d.auto(false); })()" % D); s = await pg.evaluate(S)
    check(s["lives"] == lives - 1 and any(o["kind"] == "couch" and o["cleared"] for o in s["obstacles"]), "a well-timed hop clears a couch")
    check(not pg.errs, f"no console errors {pg.errs[:3]}")

    print("\n== events")
    sc = (await pg.evaluate(S))["score"]
    await pg.evaluate(D + ".step(0.5); " + D + ".event('abuela'); " + D + ".step(3.9)"); s = await pg.evaluate(S)
    check(s["event"] and s["event"]["type"] == "abuela" and s["carPos"]["front"] <= s["crosswalk"] - 20, f"Abuela Crossing: the '64 stops before the crosswalk ({s['carPos']['front']:.0f} < {s['crosswalk']:.0f})")
    await pg.screenshot(path=os.path.join(OUT, "abuela-crossing.png"))
    await pg.evaluate(D + ".step(3)"); s = await pg.evaluate(S); spoken = [x["text"] for x in await pg.evaluate("__spoken")]
    check(s["score"] >= sc + 500 and "Gracias, mijo." in spoken, f"+500 RESPETO and 'Gracias, mijo.' ({sc} → {s['score']}) {spoken[-3:]}")
    await pg.evaluate(D + ".step(2.5); " + D + ".clear()")
    lives, sc = s["lives"], s["score"]
    await pg.evaluate(D + ".event('chancla', { high: false }); " + D + ".step(1.0)"); s = await pg.evaluate(S)
    check(s["event"]["type"] == "chancla" and "LA CHANCLA" not in s["overlayText"], "La Chancla: a warning first (on the canvas)")
    await pg.evaluate("(() => { const d = %s; d.auto(true); d.step(0.8); })()" % D); await pg.screenshot(path=os.path.join(OUT, "la-chancla.png"))
    await pg.evaluate(D + ".step(1.4); " + D + ".auto(false)"); s = await pg.evaluate(S)
    check(s["lives"] == lives and s["score"] >= sc + 300, f"hop the low chancla: +300 ({sc} → {s['score']})")
    sc = s["score"]; await pg.evaluate(D + ".event('chancla', { high: true }); " + D + ".step(3.5)"); s = await pg.evaluate(S)
    check(s["lives"] == lives and s["score"] >= sc + 300, "stay low for the high one: +300")
    await pg.evaluate(D + ".event('chancla', { high: false }); " + D + ".step(3.5)"); s = await pg.evaluate(S)
    check(s["lives"] == lives - 1, f"don't hop the low one: THWAP, −1 wheel ({lives} → {s['lives']})")
    check(not pg.errs, f"no console errors {pg.errs[:3]}")

    print("\n== no yellow (canvas + DOM)")
    await pg.evaluate(D + ".step(1)"); c = await pg.evaluate(CANVAS_SCAN)
    check(c["n"] / c["all"] < 0.0005, f"no yellow on the canvas ({c['n']} of {c['all']} sampled px) {c['ex']}")
    r = await pg.evaluate(DOM_SCAN, ".gfs-bar, .lr-wrap"); check(r["n"] > 3 and not r["bad"], f"no yellow in the bar / HUD DOM {r['bad']}")

    print("\n== game over, save")
    await pg.evaluate(D + ".end()"); await pg.wait_for_timeout(300); s = await pg.evaluate(S)
    save = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
    check(s["mode"] == "over" and "Play again" in s["overlayText"] and "Share" in s["overlayText"], "game over: score, Play again, Garage, Share, Back")
    check(save["feria"] > 0 and save["best"] == s["best"] > 0 and len(save["runs"]) == 1 and save["totals"]["hops"] >= 8, f"Feria, best and the run are saved in lowrider_v1 ({save['feria']} Feria, best {save['best']})")
    r = await pg.evaluate(DOM_SCAN, ".lr-ov"); check(not r["bad"], f"no yellow on the game-over card {r['bad']}")
    await pg.screenshot(path=os.path.join(OUT, "game-over.png"))
    await pg.click('.lr-ov [data-act="share"]'); await pg.wait_for_timeout(300); sh = await pg.evaluate("window.__shared || null")
    check(sh and sh["url"].endswith("/#puro-pinche-lowrider") and "Puro Pinche Lowrider" in sh["text"] and "Download Chisme" in sh["text"], f"Share: Chisme's share sheet with a #puro-pinche-lowrider link {sh and sh['url']}")
    check(not pg.errs, f"no console errors {pg.errs[:3]}"); await ctx.close()

    print("\n== garage: rides you unlock with Feria, paint")
    ctx, pg = await phone(p, b); await pg.evaluate(D + ".feria(300)")
    await pg.click('.lr-ov [data-act="garage"]'); await pg.wait_for_timeout(200)
    txt = await pg.evaluate(S + ".overlayText")
    check(all(n in txt for n in ["The '64 (Primer)", "The '64 (Candy)", "El Jefe '76", "900", "2,400", "Candy red", "Turquoise", "Purple", "Black cherry", "Pearl white", "earned only by playing"]) and "Gold" not in txt,
          "Garage: the 3 rides with their Feria prices, 5 paints, Feria only by playing")
    check(await pg.evaluate("[...document.querySelectorAll('.lr-car.locked')].length") == 16, "the candy '64, El Jefe and the 14 newer rides show locked")
    await pg.click('[data-id="turq"]'); await pg.click('.lr-ov [data-act="buy"]'); await pg.wait_for_timeout(200); s = await pg.evaluate(S)
    save = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
    check("turq" in s["owned"] and save["feria"] == 180 and "turq" in save["owned"]["paint"], f"buy Turquoise with 120 Feria (saved) {s['owned']} {save['feria']}")
    await pg.click('[data-id="purple"]'); await pg.wait_for_timeout(100)
    check(await pg.evaluate("document.querySelector('.lr-ov [data-act=\"buy\"]').disabled"), "not enough Feria: Purple can't be bought")
    await pg.click('.lr-car[data-id="64"]'); await pg.wait_for_timeout(3500)   # (after the toast)
    check(await pg.evaluate("document.querySelector('.lr-ov [data-act=\"buycar\"]').disabled") and "720 more" in await pg.evaluate(S + ".overlayText"), "a locked ride: its price and how much more Feria to earn")
    r = await pg.evaluate(DOM_SCAN, ".lr-ov"); check(not r["bad"], f"no yellow in the Garage {r['bad']}")
    await pg.screenshot(path=os.path.join(OUT, "garage-locked.png"))
    await pg.evaluate(D + ".feria(1000)"); await pg.click('.lr-car[data-id="primer"]'); await pg.click('.lr-car[data-id="64"]'); await pg.wait_for_timeout(100)
    await pg.click('.lr-ov [data-act="buycar"]'); await pg.wait_for_timeout(200); save = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
    check("64" in save["owned"]["car"] and save["feria"] == 100, f"unlock the candy '64 for 900 Feria (saved: {save['owned']['car']}, {save['feria']} Feria)")
    if await pg.evaluate("!!document.querySelector('.lr-ov [data-act=\"equip\"]')"): await pg.click('.lr-ov [data-act="equip"]'); await pg.wait_for_timeout(200)
    check(await pg.evaluate(S + ".car") == "64", "ride it")
    await pg.wait_for_timeout(3500); await pg.screenshot(path=os.path.join(OUT, "garage-unlocked.png"))
    await pg.reload(); await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current", timeout=90000); await pg.wait_for_timeout(500); s = await pg.evaluate(S)
    check(s["car"] == "64" and "64" in s["cars"] and s["feria"] == 100, f"the unlock survives a reload (saved on the phone) {s['cars']}")
    await pg.click('.lr-ov [data-act="trophies"]'); txt = await pg.evaluate(S + ".overlayText")
    check("Respect Your Elders" in txt and "Hydraulic Addiction" in txt and "0 / 25" in txt, "Trophies list, with progress")
    check(not pg.errs, f"no console errors {pg.errs[:3]}"); await ctx.close()

    print("\n== billboards, close-up")
    ctx, pg = await phone(p, b); await pg.evaluate(D + ".freeze(true); " + D + ".auto(true)")
    for _ in range(8): await pg.evaluate(D + ".step(15)")
    log = (await pg.evaluate(S))["signs"]["log"]; idx = [i for i, n in enumerate(log) if n == "YOUR BUSINESS HERE"]; gaps = [b_ - a for a, b_ in zip(idx, idx[1:])]
    check(len(idx) >= 3 and all(g in (3, 4) for g in gaps), f"the house ad comes up every 3rd–4th billboard (gaps {gaps}, {len(log)} billboards)")
    check(len(set(log) - {"YOUR BUSINESS HERE"}) >= 8, "the other billboards rotate through the made-up ads")
    await start(pg); await pg.evaluate(D + ".step(0.4); " + D + ".lots(['taco', 'icehouse', 'pinata'], -40); " + D + ".zoom(1.9)")
    await pg.screenshot(path=os.path.join(OUT, "car-primer.png"))
    await pg.evaluate(D + ".ride('64', 'candy'); " + D + ".zoom(1.9)"); await pg.screenshot(path=os.path.join(OUT, "car-64.png")); await pg.evaluate(D + ".zoom(1)")
    check(not pg.errs, f"no console errors {pg.errs[:3]}"); await ctx.close()

    print("\n== San Antonio: lazy stage, traffic, pickups, gas, Trail Ride")
    ctx, pg = await phone(p, b)
    check(await pg.evaluate("!document.querySelector('script[src*=\"lowrider-sa.js\"]')") and not await pg.evaluate(S + ".stageLoaded"), "lowrider-sa.js isn't loaded until San Antonio is picked")
    await pg.click('.lr-ov [data-act="stage"][data-id="sa"]'); await pg.wait_for_function(S + ".stageLoaded", timeout=30000); await pg.wait_for_timeout(300)
    check(await pg.evaluate(S + ".stage") == "sa" and "San Antonio" in await pg.evaluate(S + ".overlayText"), "San Antonio picked")
    await start(pg); await pg.evaluate(D + ".step(0.5)"); s = await pg.evaluate(S)
    check(s["mode"] == "run" and s["stage"] == "sa" and s["fuel"] > 0.95 and len(s["tags"]) >= 1, f"a San Antonio run: full tank, landmarks with name tags {s['tags'][:3]}")
    await pg.screenshot(path=os.path.join(OUT, "sa-stage.png"))
    lives = s["lives"]; await pg.evaluate(D + ".clear(); " + D + ".traffic('cop', 420)")
    await pg.evaluate("(() => { const d = %s; d.auto(true); d.step(3.5); d.auto(false); })()" % D); s = await pg.evaluate(S)
    check(s["trafficCleared"] >= 1 and s["lives"] == lives and s["cops"] >= 1, f"hop the oncoming cop: cleared, no damage ({s['trafficCleared']} cleared)")
    await pg.evaluate(D + ".step(0.6); " + D + ".clear(); " + D + ".traffic('beater', 360); " + D + ".step(3)"); s = await pg.evaluate(S)
    check(s["lives"] == lives - 1, f"don't hop the beater: −1 wheel ({lives} → {s['lives']})")
    said = set(); await pg.evaluate(D + ".step(1.5); " + D + ".auto(true)")
    for kind in ["fbi", "beater", "cuh", "trooper", "troca", "construction"] * 2:
        await pg.evaluate(D + ".clear(); " + D + ".traffic('%s', 420)" % kind)
        for _ in range(16): await pg.evaluate(D + ".step(0.2)"); said |= set(await pg.evaluate(S + ".bubbles"))
    await pg.evaluate(D + ".auto(false)")
    check(len(said) >= 3, f"drivers talk back in comic bubbles {sorted(said)[:6]}")
    await pg.evaluate(D + ".step(2); " + D + ".clear(); " + D + ".set({ lives: 3 })")
    f0 = (await pg.evaluate(S))["runFeria"]
    await pg.evaluate(D + ".pick('soda', 40, 30); " + D + ".step(1); " + D + ".pick('taco', 40, 30); " + D + ".step(1); " + D + ".fuel(0.2); " + D + ".pick('gas', 40, 30); " + D + ".step(1)"); s = await pg.evaluate(S)
    check(s["picks"]["gas"] >= 1 and s["picks"]["soda"] == 1 and s["picks"]["taco"] == 1 and s["runFeria"] >= f0 + 3 and s["fuel"] > 0.5, f"soda +3 Feria, a taco, gas fills the tank {s['picks']} fuel {s['fuel']:.2f}")
    check(not pg.errs, f"no console errors {pg.errs[:3]}")
    await pg.evaluate(D + ".clear(); " + D + ".event('trail')"); n = 0
    while (await pg.evaluate(S + ".event.phase")) != "cross" and n < 60: await pg.evaluate(D + ".step(0.1)"); n += 1
    s = await pg.evaluate(S)
    check(s["event"]["type"] == "trail" and s["carPos"]["front"] <= s["crosswalk"] - 20 and s["carPos"]["v"] < 6, f"Trail Ride: the car stops before the riders ({s['carPos']['front']:.0f} < {s['crosswalk']:.0f})")
    for _ in range(3): await pg.evaluate(D + ".step(0.6); " + D + ".press(); " + D + ".step(0.3); " + D + ".release(); " + D + ".step(0.3)")
    await pg.evaluate(D + ".step(0.4)"); c = await pg.evaluate(CANVAS_SCAN)
    check(c["n"] / c["all"] < 0.0005, f"no yellow in the horses, riders or San Antonio ({c['n']} of {c['all']} px) {c['ex']}")
    await pg.screenshot(path=os.path.join(OUT, "sa-trail-ride.png"))
    s = await pg.evaluate(S); spoken = [x["text"] for x in await pg.evaluate("__spoken")]
    check(s["salutes"] >= 1 and s["lives"] == 3 and "Yeehaw!" in spoken, f"hop for the riders: +YEEHAW ({s['salutes']} salutes), 'Yeehaw!', nobody hurt (lives {s['lives']}, said {spoken[-3:]})")
    await pg.evaluate(D + ".step(8)"); s = await pg.evaluate(S)
    check(s["trails"] == 1 and s["lives"] == 3 and s["event"] is None, "the riders clear the road, the run goes on")
    await pg.evaluate(D + ".clear(); " + D + ".picksClear(true); " + D + ".fuel(0); " + D + ".step(5)"); await pg.wait_for_timeout(1200); s = await pg.evaluate(S)
    check(s["mode"] == "over" and "Out of gas" in s["overlayText"], f"an empty tank ends the run: Out of gas ({s['mode']})")
    g = await pg.evaluate("(() => { const a = document.querySelector('.lr-ov .lr-donate'); return a && [a.href, a.textContent, window.__chismeGoal.url, window.__chismeGoal.amount]; })()")
    check(g and g[0] == g[2] and ("$" + format(g[3], ",")) in g[1], f"on the web, game over offers Chisme's App Store goal (from app.js) {g and g[1]}")
    check(not pg.errs, f"no console errors {pg.errs[:3]}"); await ctx.close()
    ctx, pg = await phone(p, b, ua="ChismeNative/1.0")
    await pg.click('.lr-ov [data-act="stage"][data-id="sa"]'); await pg.wait_for_function(S + ".stageLoaded", timeout=30000); await pg.wait_for_timeout(300)
    check(not await pg.evaluate("!!document.querySelector('.lr-donate')"), "the native app: no App Store goal button")
    await start(pg); await pg.evaluate(D + ".auto(true)")
    for _ in range(6): await pg.evaluate(D + ".step(10)")
    log = (await pg.evaluate(S))["signs"]["log"]
    check(len(log) >= 6 and "Help get Chisme on the App Store" not in log and "YOUR BUSINESS HERE" in log, f"the native app: the house ad takes the donation billboard's slot ({len(log)} billboards)")
    await ctx.close()

    print("\n== sound setting, pause when hidden, Muertos")
    ctx, pg = await phone(p, b, extra="localStorage.setItem('chisme-feed-sound', 'off');")
    check(await pg.evaluate(S + ".muted") is True, "the app's sound is off → the game starts muted")
    await pg.click('.lr-controls [data-act="sound"]'); s = await pg.evaluate(S); save = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
    check(s["muted"] is False and save["muted"] is False, "🔊 in the game turns it on (and remembers)")
    await start(pg); await pg.evaluate(D + ".freeze(false)"); await pg.wait_for_timeout(300)
    await pg.evaluate("Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange'))")
    check(await pg.evaluate(S + ".mode") == "paused", "pauses when the page is hidden")
    await ctx.close()
    ctx, pg = await phone(p, b, extra="localStorage.setItem('chisme-season-pin', 'muertos');")
    check(await pg.evaluate(S + ".season") is True, "Día de Muertos: papel picado + marigolds when the season is on")
    await ctx.close()
    ctx, pg = await phone(p, b, extra="localStorage.setItem('chisme-season-pin', 'off');", reduced="reduce")
    await start(pg); await hop(pg, 0.5)
    check(await pg.evaluate(S + ".lastGrade") == "perfect" and not pg.errs, "Reduce Motion: still plays (less shake + confetti, the Garage car holds still)")
    await ctx.close(); await b.close()

async def chromium(p):
    print("\n== Chromium 1280×800 (desktop site), billboards for sponsor pitches")
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={"width": 1280, "height": 800}, service_workers="block"); await ctx.add_init_script(SEASON); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    await pg.goto(BASE + "/#puro-pinche-lowrider", wait_until="domcontentloaded"); await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current", timeout=90000); await pg.wait_for_timeout(1200)
    await pg.evaluate("document.querySelector('.lr-wrap').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(300)
    await pg.screenshot(path=os.path.join(OUT, "desktop.png"))
    await start(pg); await hop(pg, 0.5); s = await pg.evaluate(S)
    check(s["lastGrade"] == "perfect" and s["fullscreen"] and not errs, f"desktop: opens, plays full screen ({s['css']})")
    await ctx.close()
    ctx = await b.new_context(viewport={"width": 1200, "height": 640}, device_scale_factor=2, service_workers="block"); await ctx.add_init_script(SEASON); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT)
    pg = await ctx.new_page(); await pg.goto(BASE + "/#lowrider", wait_until="domcontentloaded"); await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current", timeout=90000); await pg.wait_for_timeout(1200)
    await start(pg)
    await pg.evaluate(D + ".step(0.3); " + D + ".billboards(['Raspas Tía Chismosa', 'Paletería Ay Mija', 'YOUR BUSINESS HERE', 'Panadería La Abuela Sabe', 'Tortillería Doña Metiche']); " + D + ".lots(['taco', 'icehouse', 'tires', 'pinata', 'barber', 'shop'])")
    s = await pg.evaluate(S); check("YOUR BUSINESS HERE" in s["signs"]["billboards"] and len(s["signs"]["billboards"]) == 5, "billboards shot: 4 made-up ads + the house ad")
    await pg.screenshot(path=os.path.join(OUT, "billboards.png")); await b.close()

# v49.27: real DOM input and real HTTP owner gate (never inject a god hook/script).
async def revision_4927(p):
    b = await p.chromium.launch()
    ctx, pg = await phone(p, b)
    await start(pg)
    instant = await pg.evaluate("""() => { const cv = document.querySelector('.lr-cv');
      cv.dispatchEvent(new PointerEvent('pointerdown', { bubbles:true, cancelable:true, pointerId:7, pointerType:'touch' }));
      const s = ChismeLowrider.current.state; cv.dispatchEvent(new PointerEvent('pointerup', { bubbles:true, pointerId:7 }));
      return { air:s.air, lag:s.inputLagMs, action:getComputedStyle(cv.parentElement).touchAction, select:getComputedStyle(cv.parentElement).userSelect }; }""")
    check(instant['air'] and instant['lag'] < 17 and instant['action'] == 'none' and instant['select'] == 'none', f"pointerdown hops synchronously without click {instant}")
    await pg.evaluate(D + ".step(2); " + D + ".launch(.6)")
    await land_with_tap(pg, .12)
    s0 = await pg.evaluate(S)
    check(s0['lastGrade'] in ('perfect', 'puro') and not s0['pend'], 'a tap 120ms before landing is consumed as the landing tap')
    coyote = await pg.evaluate("""() => { const g = ChismeLowrider.current, d = g.debug; d.step(1); d.launch(.3);
      let n=0; while(g.state.air && n++<400) d.sim(1/120); d.sim(.05); d.press(); const hopped=g.state.air; d.release(); return hopped; }""")
    check(coyote, 'a press 50ms after touchdown can grade the landing and start another hop')
    for stage in ('blvd', 'sa'):
        await pg.evaluate(D + ".title()")
        await pg.evaluate(D + f".stage('{stage}')")
        await start(pg)
        for kind in ('pothole', 'bump', 'pallet', 'copcar'):
            result = await pg.evaluate("""kind => { const g = ChismeLowrider.current, d = g.debug;
              d.clear(); d.auto(false); d.step(2); d.set({lives:3}); d.spawn(kind,0); d.step(.5);
              const hit = g.state.lives === 2 && d.obs.some(o => o.kind === kind && o.hit);
              d.clear(); d.step(2); d.set({lives:3}); const before = g.state.cleared[kind] || 0;
              d.spawn(kind,500); d.auto(true); let n=0; while ((g.state.cleared[kind] || 0) === before && n++ < 720 && g.state.lives === 3) d.sim(1/120);
              d.auto(false); d.draw(); const s = g.state;
              return {hit, cleared:(s.cleared[kind] || 0) > before, lives:s.lives, bonus:s.pops.some(p => p.text.includes(kind === 'copcar' ? '+COP HOP ' : '+CLEAN '))}; }""", kind)
            check(all((result['hit'], result['cleared'], result['lives'] == 3, result['bonus'])), f"{stage} {kind}: penalty, jump, counter and bonus {result}")
    patrol = await pg.evaluate("""() => { const g=ChismeLowrider.current,d=g.debug; d.clear(); d.step(2); d.set({lives:3}); const before=g.state.cleared.copcar||0;
      d.traffic('cop',600,-80); d.auto(true); let n=0; while((g.state.cleared.copcar||0)===before && n++<720 && g.state.lives===3) d.sim(1/120);
      d.auto(false); return g.state.lives===3 && (g.state.cleared.copcar||0)>before; }""")
    check(patrol, 'San Antonio oncoming cop traffic has a fair jump window')
    sponsors = await pg.evaluate("""() => { const L = ChismeLowrider, slot = {id:'test',name:'Barrio Test',line:'See you on the boulevard',colors:['#000000','#FFFFFF','#FF1A7F'],art:'text',sponsor:true};
      const good = L.setSponsors([slot]), names = L.current.state.sponsorSlots.map(s=>s.name);
      const bad = [null, [{...slot,name:'<img>'}], [{...slot,line:'https://example.com'}], [{...slot,art:'image'}], [{...slot,colors:['yellow']}], [slot,slot]].every(x=>L.setSponsors(x)===false);
      const unchanged = L.current.state.sponsorSlots[0].name === slot.name; L.setSponsors([]);
      return {good,bad,unchanged,names,defaults:L.SPONSOR_SLOTS.every(s=>s.id && s.line && s.sponsor===false),house:L.SPONSOR_SLOTS.some(s=>s.name==='YOUR BUSINESS HERE' && s.line==='Ask Chisme')}; }""")
    check(all(sponsors[k] for k in ('good','bad','unchanged','defaults','house')), f"sponsor inventory and atomic validation {sponsors}")
    await ctx.close()
    ctx = await b.new_context(service_workers='block')
    response = await ctx.request.get(BASE + '/stats/lowrider/god.js')
    check(response.status in (401,404), f"private Lowrider script rejects unsigned requests ({response.status})")
    response = await ctx.request.get(BASE + '/stats/lowrider/god.js', headers={'User-Agent':'ChismeNative'})
    check(response.status == 404, 'private Lowrider script is unavailable in native app')
    await ctx.add_init_script(INIT + SEASON + QUIET)
    pg = await ctx.new_page(); requests = []
    pg.on('request', lambda r: requests.append(r.url) if '/stats/lowrider/god.js' in r.url else None)
    await pg.goto(BASE + '/?god=1#puro-pinche-lowrider', wait_until="domcontentloaded")
    await pg.wait_for_function('window.ChismeLowrider && ChismeLowrider.current')
    check(not requests and not await pg.evaluate(S + '.god') and not await pg.locator('.lr-god-badge').count(), '?god=1 alone: no script request, badge or god mode')
    await ctx.add_cookies([{'name':'chisme_admin','value':'1','url':BASE}])
    await pg.reload(); await pg.wait_for_function('window.ChismeLowrider && ChismeLowrider.current'); await pg.wait_for_timeout(300)
    check(bool(requests) and not await pg.evaluate(S + '.god') and not await pg.locator('.lr-god-badge').count(), 'forged marker requests real endpoint but cannot activate god mode')
    await ctx.clear_cookies()
    token = os.environ.get('OWNER_TOKEN')
    if token:
        await pw_csp.admin_sign_in(pg, BASE, token)
        await pg.goto(BASE + '/?god=1#puro-pinche-lowrider', wait_until="domcontentloaded")
        await pg.wait_for_function('window.ChismeLowrider && ChismeLowrider.current && ChismeLowrider.current.state.god')
        check(await pg.locator('.lr-god-badge[data-on="1"]').count() == 1, 'owner loads god mode through the authenticated endpoint')
        await start(pg)
        before = await pg.evaluate("localStorage.getItem('lowrider_v1')")
        await pg.evaluate(D + ".spawn('copcar',0); " + D + ".step(1); " + D + ".set({score:999999}); " + D + ".end()")
        after = await pg.evaluate("localStorage.getItem('lowrider_v1')")
        keep = lambda raw: (lambda o: (o.get('feria', 0), o.get('best', 0), len(o.get('runs', [])), (o.get('totals') or {}).get('runs', 0)))(json.loads(raw) if raw else {})   # v49.27: a fresh save written after the run counts as unchanged
        check(await pg.evaluate(S + '.lives') == 3 and keep(before) == keep(after), f'owner invincible run leaves scores and Feria storage unchanged {keep(before)} → {keep(after)}')
    await ctx.close(); await b.close()

# v49.27: real audio must stay silent after every route out of a game.
async def audio_exit_regression(p):
    for bt, devn in ((p.chromium, "Pixel 7"), (p.webkit, "iPhone 13")):   # v49.27: both engines, phone sizes
      b = await bt.launch(); dev = dict(p.devices[devn]); dev.pop("default_browser_type", None)
      for game in ['lowrider']:
          for way in ("x", "tab", "hash", "escape", "hidden", "pagehide", "swap"):
              ctx = await b.new_context(**dev, service_workers="block")
              await ctx.add_init_script(INIT + QUIET + ";localStorage.setItem('chisme-feed-sound','1');")
              pg = await ctx.new_page()
              await pg.goto(BASE + "/#" + game, wait_until="domcontentloaded")
              await pg.wait_for_function("window.__chisme && window.ChismeJuegos && __chisme.juegos.id === '" + game + "'")
              if game == "lowrider":
                  if await pg.get_attribute('[data-act="sound"]', 'aria-pressed') == 'false':
                      await pg.click('[data-act="sound"]')
                  await start(pg)
              elif game == "juan":
                  await pg.click('#juan-ov [data-act="start"]')
                  if await pg.get_attribute('#juan-sound', 'aria-pressed') == 'false':
                      await pg.click('#juan-sound')
                  await pg.keyboard.press('Space')
              else:
                  if await pg.get_attribute('#lot-voice', 'aria-pressed') == 'false':
                      await pg.click('#lot-voice')
                  await pg.click('#lot-play')
              await pg.wait_for_function("(() => { const s = __chismeAudioActive(); return s.contexts.includes('running') || s.playingMedia > 0 || s.speaking; })()")
              if way == "x": await pg.click('.gfs-x')
              elif way == "tab": await pg.locator('.tab[data-view="chisme"]').first.dispatch_event('click')
              elif way == "hash": await pg.evaluate("location.hash = '#chisme'")
              elif way == "escape": await pg.keyboard.press('Escape')
              elif way == "hidden": await pg.evaluate("Object.defineProperty(document, 'hidden', {value:true, configurable:true}); Object.defineProperty(document, 'visibilityState', {value:'hidden', configurable:true}); document.dispatchEvent(new Event('visibilitychange'))")
              elif way == "pagehide": await pg.evaluate("window.dispatchEvent(new Event('pagehide'))")
              else: await pg.locator('.game-pick[data-game="' + ('loteria' if game != 'loteria' else 'juan') + '"]').dispatch_event('click')
              for delay in (500, 2500):
                  await pg.wait_for_timeout(delay)
                  state = await pg.evaluate('__chismeAudioActive()')
                  check('running' not in state['contexts'] and state['playingMedia'] == 0 and not state['speaking'] and state['pendingSounds'] == 0,
                        f"{devn} {game} {way}: silent after {delay} ms ({state})")
              await ctx.close()
      await b.close()

async def main():
    static()
    async with async_playwright() as p:
        await audio_exit_regression(p)
        await webkit(p); await chromium(p); await revision_4927(p)
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
