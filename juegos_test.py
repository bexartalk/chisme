"""🎲 Juegitos (v30; v39 English UI; v40 renamed from Juegos + full-screen portrait play; v41 traditional Spanish Lotería; v44 The Juan That Got Away): a games tab, all on the phone and offline.

1. Node: Lotería Chismosa's deck: the 54 traditional cards (El Gallo … La Rana; #26 is El Chocolate instead of El Negrito) with their folk
   verses, each with its own original SVG art; the call is the verse then "¡Name!"; one recorded mp3 per call; random 4×4 tablas, and
   wins (rows, columns, diagonals, 4 corners) that only count for cards Tía actually called. The Juan That Got Away's 6 levels
   (Hon Dipo → La Chamba → Don Pedroes → O'Reillees → Juan's Casa → Noche Caliente), same course every time, ☕ coffee + breakfast taco on each
   level, cold ones to jump for on the cantina level, hazards on every level but none right at a checkpoint.
2. WebKit iPhone 13: the 🎲 Juegitos tab (between ¿Y la dieta? and Events) fits; a list of games. Lotería: Tía (avatar) calls
   cards in Spanish from recorded clips (the phone's es-MX voice only if a clip fails), 🔇 Sound, pause, speed, new board; a bean drops only on a
   called card (an uncalled one shakes), tap again to take it off; ¡Lotería! checks the beans,
   confetti + a brag on a win, wins/streak/best in localStorage. The Juan That Got Away (v44, replaces Ice Ice Bebé): run, jump (tap / Space),
   a bump costs health, out of health → a random "¡Ay no!" / "¡Híjole!" / "¡Ándale, otra vez!" (kept in Spanish) and back to the checkpoint,
   v47: caught by ICE → a random "¡Ay no!" / "¡Ay cabrón!" / "¡Chingao!" / "¡Pinche ICE!" / "¡Ay, vengo mamá!", never the same twice in a row; the longest fits 320 px,
   coffee boost, taco health, beers (+health) at night, level clear, the win at Noche Caliente ("¡Salud, Juan!"), English UI, best score, mute, pause.
   Reduce motion (no confetti, no parallax). No links and no outside requests in the games. Settings → default tab Juegitos.
3. Chromium: offline (service worker), Juegitos still opens and both games run.
4. v41 full screen: the board fills the width and most of the height at 390×844 and 320×640 with no scrolling; the called card sits small above it.
   v43: the tabla-app layout (picker + bean count in the top bar, the called-card strip, big vintage cards, Limpiar / Nueva tabla): see loteria_v43_test.py.
   v44: The Juan That Got Away full screen at 390×844 (level 1 at Hon Dipo, level 2 at La Chamba, Don Pedroes, level 6 at the cantina) and 320×640 (canvas + controls fit, no scrolling).
Screenshots: juegos-tab.png, juegos-english.png, loteria-calls.png, loteria-win.png, loteria-tabla-big.png, loteria-cards.png, loteria-320.png,
juan-intro.png, juan-l1.png, la-chamba.png, juan-don-pedroes.png, juan-l5.png, juan-caught-cabron.png, juan-win.png, juan-320.png, juan-caught-320.png."""
import asyncio, json, os, re, subprocess
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
# a recording speechSynthesis (headless browsers have no voices)
SPEECH = """(() => { window.__spoken = [];
  const fake = { speak(u) { __spoken.push({ text: u.text, lang: u.lang }); setTimeout(() => u.onend && u.onend(), 60); }, cancel() {}, getVoices() { return [{ lang: 'es-MX', name: 'Test es-MX' }, { lang: 'en-US', name: 'Test en-US' }]; }, addEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {}
  window.SpeechSynthesisUtterance = function (t) { this.text = t; }; })()"""
# v49.5: Juan's 🏆 new-high-score sheet would pop up over these runs; the board they see is full of unbeatable scores
# (the sheet itself is juan_highscores_test's job)
FULL_BOARD = json.dumps({"ok": True, "max": 13800, "scores": [{"id": f"x{i}", "name": "Test", "score": 13800 - i * 5, "level": 6, "t": 1} for i in range(10)]})
async def quiet_board(ctx):   # in the page (requests the service worker makes don't go through Playwright's routes)
    await ctx.add_init_script("(() => { const F = window.fetch, B = %s; window.fetch = function (u, o) { return String(u).includes('/api/juan/scores') ? Promise.resolve(new Response(B, { status: 200, headers: { 'Content-Type': 'application/json' } })) : F.apply(this, arguments); }; })()" % json.dumps(FULL_BOARD))

fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

TRADITIONAL = ["El Gallo", "El Diablito", "La Dama", "El Catrín", "El Paraguas", "La Sirena", "La Escalera", "La Botella", "El Barril", "El Árbol", "El Melón",
  "El Valiente", "El Gorrito", "La Muerte", "La Pera", "La Bandera", "El Bandolón", "El Violoncello", "La Garza", "El Pájaro", "La Mano", "La Bota", "La Luna",
  "El Cotorro", "El Borracho", "El Chocolate", "El Corazón", "La Sandía", "El Tambor", "El Camarón", "Las Jaras", "El Músico", "La Araña", "El Soldado", "La Estrella",
  "El Cazo", "El Mundo", "El Apache", "El Nopal", "El Alacrán", "La Rosa", "La Calavera", "La Campana", "El Cantarito", "El Venado", "El Sol", "La Corona",
  "La Chalupa", "El Pino", "El Pescado", "La Palma", "La Maceta", "El Arpa", "La Rana"]   # #26: El Chocolate replaces the racist "El Negrito"
# v39: Spanish words that must not show up in the games' UI (v41: the Spanish is the card names and Tía's calls, not the buttons/rules)
# v43: the user asked for these (the big buttons, the picker and its preset tablas' names)
ALLOWED_ES = ["Limpiar", "Nueva tabla", "Pick your tabla", "your tabla", "tabla", "La Clásica", "Del Campo", "La Fiesta", "Cielo y Mar", "La Gente"]
SPANISH = ["Empezar", "Pausa", "Seguir", "Otra vez", "Nueva tabla", "Voz", "Lenta", "Rápida", "mija", "Siéntate", "carta", "baraja", "Primero", "Todavía",
  "Ganaste", "Bienvenido", "Llegaste", "Qué", "fiesta", "Mamá", "Cafecito", "Taquería", "Tiendita", "Casa de", "La Plaza", "tabla", "ficha", "esquinas", "fila", "columna"]
JUAN_LEVELS = ["Hon Dipo", "La Chamba", "Don Pedroes", "O'Reillees", "Juan's Casa", "Noche Caliente", "Dice City VI"]
OOPS = {"¡Ay no!", "¡Híjole!", "¡Ándale, otra vez!"}
CAUGHT = ["¡Ay no!", "¡Ay cabrón!", "¡Chingao!", "¡Pinche ICE!", "¡Ay, vengo mamá!"]   # v47: caught by ICE, the user's picks (+ the original)
UNIT = r"""
const J = require(process.argv[1]), I = require(process.argv[2]);
const t = J.newTabla(), called = new Set(t), out = { n: J.CARDS.length, names: J.CARDS.map((c) => c.name), tabla: t.length, uniq: new Set(t).size, calls: J.CARDS.every((c) => c.verse && c.verse.length <= 100) };
out.art = J.CARDS.filter((c) => /^<svg[^>]*viewBox="0 0 100 100"/.test(c.svg) && c.svg.length > 300).length; out.artUniq = new Set(J.CARDS.map((c) => c.svg)).size;
out.imgs = J.CARDS.map((c) => c.img); out.presets = (J.PRESETS || []).map((p) => [p.id, p.cards.length, new Set(p.cards).size]);
out.call1 = J.callText(J.CARDS[0]); out.lines_es = J.LINES_ES; out.ids = J.CARDS.map((c) => c.id);
const win = (cells, calledSet) => J.check(t, new Set(cells), calledSet || called);
out.row = win([4, 5, 6, 7]); out.col = win([1, 5, 9, 13]); out.diag = win([3, 6, 9, 12]); out.corners = win([0, 3, 12, 15]); out.none = win([0, 1, 2, 5]);
out.uncalled = win([0, 1, 2, 3], new Set([t[0], t[1], t[2]]));
out.lines = J.LINES.length;
const ALL = I.LEVELS.map((_, i) => i + 1);   // v49.5: every level, Dice City VI too
out.levels = I.LEVELS.map((l) => l.name); out.outfits = I.LEVELS.map((l) => l.outfit);
out.same = JSON.stringify(I.buildLevel(3)) === JSON.stringify(I.buildLevel(3));
out.power = ALL.map((n) => { const e = I.buildLevel(n); return [e.filter((x) => x.t === "coffee").length, e.filter((x) => x.t === "taco").length]; });
out.beers = ALL.map((n) => I.buildLevel(n).filter((x) => x.t === "beer").length);
out.lastBeers = I.buildLevel(6).filter((x) => x.t === "beer" && x.x > I.END - 200).length;
const HZ = Object.keys(I.HAZ), SOLID = ["pallet", "tires", "lowcar", "sportscar"];
out.haz = ALL.map((n) => I.buildLevel(n).filter((x) => HZ.includes(x.t)).length);
out.kinds = [...new Set(ALL.flatMap((n) => I.buildLevel(n).filter((x) => HZ.includes(x.t) || SOLID.includes(x.t)).map((x) => x.t)))].sort();
out.dmg = Object.fromEntries(Object.entries(I.HAZ).map(([k, v]) => [k, v[0]])); out.hp = I.HP;
out.afterCheck = ALL.every((n) => I.buildLevel(n).every((e) => !(HZ.includes(e.t) || SOLID.includes(e.t)) || I.CHECKS.every((c) => !c || e.x + e.w < c - 40 || e.x > c + 60)));
const fs = require("fs"), path = require("path"), src = fs.readFileSync(process.argv[1], "utf8") + fs.readFileSync(process.argv[2], "utf8") + fs.readFileSync(path.join(path.dirname(process.argv[1]), "loteria_cards.js"), "utf8");
const srcNet = src.split('fetch("/api/juan/scores"').join("").split('fetch("/stats/juan/scores"').join("");   // v49.5: the one allowed call, Juan's own Top 10 board (same site); v49.8: + the owner check (same site, only with the admin marker)
out.net = ["http:", "https:", "fetch(", "XMLHttpRequest", "import(", "sendBeacon", "WebSocket", "<a "].filter((w) => srcNet.includes(w));
out.callsText = J.CARDS.map((c) => c.verse);
out.hints = I.LEVELS.map((l) => l.hint); out.game = [I.game.id, I.game.name, I.KEY];
out.ice = ALL.map((n) => { const e = I.buildLevel(n); return [e.filter((x) => x.t === "agent").length, e.filter((x) => x.t === "suv").length, e.filter((x) => x.t === "flipflops").length]; });
out.city = I.LEVELS.map((l) => !!l.city); out.sameOld = I.LEVELS.filter((l) => l.seed && l.seed === l.d).length === 5;
out.iceLines = [I.CAUGHT, I.FUERA]; out.caughtSeq = Array.from({ length: 3000 }, () => I.pickCaught()); out.caughtEdge = [I.pickCaught("¡Ay no!", () => 0.9999), I.pickCaught("¡Chingao!", () => 0)]; out.iceSafe = ALL.every((n) => I.buildLevel(n).every((e) => !I.ICE.includes(e.t) || I.CHECKS.every((c) => !c || e.x + e.w < c - 40 || e.x > c + 60)));
out.keepLines = ["¡Fuera!", "¡Vámonos, amigo!", "¡Ay no!", "¡Híjole!", "¡Ándale, otra vez!", "Flip-flops! He's dizzy", "Caught! Juan tries again"].filter((l) => !fs.readFileSync(process.argv[2], "utf8").includes(l));
out.iceSrc = /weapon|gun|pistol|handcuff|taser|blood/i.test(fs.readFileSync(process.argv[2], "utf8").replace(/No weapons|no weapons/g, ""));
console.log(JSON.stringify(out));
"""
def unit():
    print("== Node: Lotería Chismosa + The Juan That Got Away logic")
    r = subprocess.run(["node", "-e", UNIT, os.path.join(HERE, "static", "juegos.js"), os.path.join(HERE, "static", "juan.js")], capture_output=True, text=True, timeout=60)
    if r.returncode: check(False, "node harness: " + r.stderr[-300:]); return
    o = json.loads(r.stdout)
    check(o["n"] == 54 and o["names"] == TRADITIONAL and o["ids"] == list(range(1, 55)), f"the 54 traditional cards in order, El Gallo … La Rana ({o['n']}; #26 {o['names'][25]!r})")
    check("El Negrito" not in o["names"] and o["names"][25] == "El Chocolate", "#26 is El Chocolate (the racist 'El Negrito' is left out)")
    check(o["art"] == 54 and o["artUniq"] == 54, f"every card has its own original SVG drawing ({o['art']} drawn, {o['artUniq']} different)")
    cards_dir = os.path.join(HERE, "static", "loteria", "cards")
    okimg = [u == f"/static/loteria/cards/{i:02d}.webp" and os.path.getsize(os.path.join(cards_dir, f"{i:02d}.webp")) > 3000 for i, u in enumerate(o["imgs"], 1) if u]
    check(len(okimg) == 54 and all(okimg), f"v43: every card has its finished vintage picture (static/loteria/cards/01–54.webp, made by tools/make_loteria_cards.py from our drawings) ({sum(okimg)})")
    check(len(o["presets"]) >= 4 and all(n == 16 and u == 16 for _, n, u in o["presets"]), f"v43: ready-made tablas of 16 different cards each ({o['presets']})")
    check(o["calls"] and o["call1"] == "El que le cantó a San Pedro no le volverá a cantar. ¡El Gallo!", f"each call is the traditional verse, then the name ({o['call1']!r})")
    check(o["lines_es"] == {"intro": "¡Se va y se corre con…!", "loteria": "¡Lotería!", "over": "¡Se acabaron las cartas!"}, f"the other calls are Spanish too ({o['lines_es']})")
    es = [w for w in SPANISH if any(w.lower() in t.lower().split() or (" " in w and w.lower() in t.lower()) for t in o["hints"])]
    check(not es, f"The Juan That Got Away's level hints are English ({es})")
    audio = os.path.join(HERE, "static", "loteria", "audio"); clips = [f"{i:02d}.mp3" for i in range(1, 55)] + ["intro.mp3", "loteria.mp3", "over.mp3"]
    sizes = [os.path.getsize(os.path.join(audio, f)) if os.path.exists(os.path.join(audio, f)) else 0 for f in clips]
    heads = [open(os.path.join(audio, f), "rb").read(3) for f in clips if os.path.exists(os.path.join(audio, f))]
    check(all(4000 < z < 80000 for z in sizes) and all(h[:3] == b"ID3" or h[0] == 0xFF for h in heads), f"57 recorded calls (54 cards + intro / ¡Lotería! / end), small mp3s ({sum(sizes) // 1024} KB total)")
    check(o["tabla"] == 16 and o["uniq"] == 16, "a tabla is 4×4 with 16 different cards")
    check(o["row"]["win"] and o["col"]["win"] and o["diag"]["win"] and o["corners"]["win"] and o["lines"] == 11, "wins: a row, a column, a diagonal, the 4 corners (11 lines)")
    check(not o["none"]["win"], "4 marks that aren't a line: no win")
    check(not o["uncalled"]["win"] and len(o["uncalled"]["early"]) == 1, "a line with a card Tía hasn't called doesn't count (caught as an early mark)")
    check(o["game"] == ["juan", "The Juan That Got Away", "chisme-juegos-juan"], f"v44: the second game is The Juan That Got Away ({o['game']})")
    check(o["levels"] == JUAN_LEVELS, f"The Juan That Got Away: 7 stops, Hon Dipo → La Chamba → Don Pedroes → O'Reillees → Juan's Casa → Noche Caliente → (v49.5) Dice City VI ({o['levels']})")
    check(o["outfits"] == ["work", "work", "work", "work", "work", "western", "western"], f"work clothes for the first 5 levels, cowboy clothes at night and in Dice City VI ({o['outfits']})")
    check(o["same"], "a level is the same course every time (so a checkpoint restarts it fairly)")
    check(all(c >= 1 and t >= 1 for c, t in o["power"]), f"every level has a ☕ coffee and a breakfast taco ({o['power']})")
    check(o["beers"][:5] == [0, 0, 0, 0, 0] and o["beers"][5] >= 20 and o["beers"][6] >= 5 and o["lastBeers"] == 4, f"cold ones to jump for only on the cantina level, with a last arc of 4 by the door; martinis on Dice City VI ({o['beers']}, last {o['lastBeers']})")
    check(all(h >= 6 for h in o["haz"]), f"neutral hazards on every level, mixed in with the agents ({o['haz']})")
    check(all(a >= 2 and v >= 1 and f == 1 for a, v, f in o["ice"]), f"v46: ICE agents back on every level: patrolling agents + a dark SUV with a chaser, and a 🩴 flip-flops shield ({o['ice']})")
    check(o["ice"][1][0] > max(a for i, (a, v, f) in enumerate(o["ice"]) if i != 1) and o["ice"][1][1] >= 2 and o["city"] == [False, True, False, False, False, False, False],
          f"v47: La Chamba (downtown) has the most ICE agents of any level, and 2+ SUVs ({[a for a, v, f in o['ice']]})")
    check(o["sameOld"], "v47: the other 5 levels keep their old courses (seeded by the level, not its place in the list)")
    check(o["iceLines"] == [CAUGHT, "¡Fuera!"] and o["iceSafe"], f"v47: caught = one of {CAUGHT}, '¡Fuera!' when he gets away; no agents right at a checkpoint ({o['iceLines']})")
    sq = o["caughtSeq"]; reps = sum(a == b for a, b in zip(sq, sq[1:])); cnt = {l: sq.count(l) for l in CAUGHT}
    check(reps == 0 and set(sq) == set(CAUGHT) and min(cnt.values()) > 0.15 * len(sq) and "¡Chingao!" not in o["caughtEdge"][1:] and o["caughtEdge"][0] != "¡Ay no!",
          f"v47: the caught line rotates at random, never the same twice in a row ({len(sq)} picks, {reps} repeats, {cnt}, edges {o['caughtEdge']})")
    check(not o["keepLines"], f"v47: every existing line is still in the game (¡Fuera!, ¡Vámonos, amigo!, ¡Ay no!, ¡Híjole!, ¡Ándale, otra vez!…); the new caught lines are added, nothing replaced (missing {o['keepLines']})")
    check(not o["iceSrc"], "v46: cartoon agents, no weapons, handcuffs or blood in the game's code (v49.5: Dice City VI's background rooftop standoff is just silhouettes + flashes, decorative)")
    check(o["kinds"] == ["cart", "chancla", "chihuahua", "cone", "lowcar", "pallet", "pothole", "sportscar", "sprinkler", "tires"], f"cones, potholes, carts, chanclas, chihuahuas, sprinklers + pallets / tires (and, v49.5, Dice City VI's lowriders / sports cars) to hop on ({o['kinds']})")
    check(o["hp"] == 100 and all(5 <= d <= 20 for d in o["dmg"].values()), f"a bump costs a little of the 100-point health bar ({o['dmg']})")
    check(o["afterCheck"], "no hazards right at a checkpoint")
    check(not o["net"], f"the games' code has no URLs, links or network calls, except Juan's own Top 10 board (same-site /api/juan/scores) and the owner check (same-site /stats/juan/scores) ({o['net']})")

async def to_stage(pg):
    await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 70); }"); await pg.wait_for_timeout(300)
G = "__chisme.juegos.game"
# v40: full-screen play. Everything about the overlay in one evaluate.
FS_JS = """(() => { const st = document.querySelector('#game-stage'), r = st.getBoundingClientRect(), cs = getComputedStyle(st), vis = (s) => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0; };
  const x = document.querySelector('.gfs-x'), xr = x && x.getBoundingClientRect(), badge = document.querySelector('.gfs-badge'), br = badge && badge.getBoundingClientRect();
  return { on: document.documentElement.classList.contains('game-fs') && st.classList.contains('gfs'), fixed: cs.position === 'fixed', covers: Math.abs(r.left) < 1 && Math.abs(r.top) < 1 && Math.abs(r.width - innerWidth) < 1 && Math.abs(r.height - innerHeight) < 1,
    tabs: vis('#tabs'), foot: vis('.foot'), fab: vis('.tia-fab'), x: !!x && xr.right > innerWidth - 70 && xr.top < 70 && xr.width >= 44, xlabel: x ? x.getAttribute('aria-label') : '', xtext: x ? x.textContent.trim() : '',
    badge: badge ? badge.textContent.trim() : '', badgeMid: !!br && Math.abs((br.left + br.right) / 2 - innerWidth / 2) < 24 && br.top < 70, ih: innerHeight, iw: innerWidth }; })()"""
async def fs(pg): return await pg.evaluate(FS_JS)
# v41: the full-screen Lotería layout: top row, board, ¡Lotería!, controls stacked in order and all on screen; how big the board is
# (v43: bar → the called-card strip with ¡Lotería! in it → the board → Limpiar / Nueva tabla)
LAYOUT_JS = """(() => { const r = (s) => document.querySelector(s).getBoundingClientRect(); const t = r('#lot-tabla'), c = r('#lot-claim'), k = r('.lot-controls'), top = r('.lot-now'), bar = r('.gfs-bar'), st = document.querySelector('#game-stage');
  const cell = document.querySelector('#lot-tabla .lcard').getBoundingClientRect(), card = document.querySelector('#lot-card .lcard');
  const names = [...document.querySelectorAll('#lot-tabla .lc-img')].filter(e => !e.complete || !e.naturalWidth).map(e => e.getAttribute('src'));   // v43: the name is in the picture, so 'clipped' = a picture that didn't load
  return { h: t.height, w: t.width, cell: cell.width, card: card ? card.getBoundingClientRect().width : 0, clipped: names, scroll: st.scrollHeight > st.clientHeight + 1 || document.scrollingElement.scrollHeight > innerHeight + 1 && getComputedStyle(document.documentElement).overflow !== 'hidden',
    ok: bar.bottom <= top.top + 1 && top.bottom <= t.top + 1 && t.bottom <= k.top + 1 && k.bottom <= innerHeight + 1 && c.top >= top.top - 1 && c.bottom <= top.bottom + 1 && t.left >= 0 && t.right <= innerWidth + 0.5 }; })()"""
def fs_ok(f): return f["on"] and f["fixed"] and f["covers"] and not f["tabs"] and not f["foot"] and not f["fab"] and f["x"] and f["xtext"] == "✕" and "Juegitos" in f["xlabel"]
async def st(pg): return await pg.evaluate(G + ".state")
async def until(pg, js, secs):
    for _ in range(int(secs * 10)):
        if await pg.evaluate(js): return True
        await pg.wait_for_timeout(100)
    return False

async def webkit(p):
    print("\n== WebKit iPhone 13: the 🎲 Juegitos tab")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await quiet_board(ctx); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs, outside = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    watch = {"on": False}
    pg.on("request", lambda r: outside.append(r.url[:90]) if watch["on"] and r.resource_type != "image" and urlparse(r.url).hostname not in ("localhost", "127.0.0.1") else None)   # images = other tabs' map tiles/photos
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_timeout(1500)
    tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t => t.textContent.trim())")
    fit = await pg.evaluate("(() => { const t = document.querySelector('.tabs-inner'), j = document.querySelector('.tab[data-view=juegos]').getBoundingClientRect(); return t.scrollWidth <= t.clientWidth + 1 && j.right <= innerWidth; })()")
    check([t.split()[-1] for t in tabs] == ["News", "Sports", "Weather", "dieta?", "Juegitos", "Events"] and tabs[4] == "🎲 Juegitos", f"tab bar: News · Sports · Weather · ¿Y la dieta? · 🎲 Juegitos · Events ({tabs})")
    check(fit, "all 6 tabs fit on an iPhone 13 (no sideways scroll)")
    check(await pg.evaluate("__chisme.view") == "juegos" and await pg.evaluate("__chisme.juegos.id") == "loteria", "#loteria opens Juegitos → Lotería Chismosa")
    games = await pg.evaluate("[...document.querySelectorAll('.game-pick b')].map(b => b.textContent)")
    check(games == ["The Juan That Got Away", "Lotería Chismosa"], f"a list of games, The Juan That Got Away first (v47) ({games})")
    watch["on"] = True
    check(await pg.evaluate("document.querySelectorAll('#lot-tabla .lot-cell').length") == 16, "a 4×4 tabla")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('#juegos').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, "juegos-tab.png"))
    # v39: the UI is English (v41: the card names and Tía's calls are the Spanish part)
    UI_TXT = "(() => { const j = document.querySelector('#view-juegos'); return [...j.querySelectorAll('#juegos, .lot-controls, .lot-rules, .lot-stats, #lot-count, .lot-hist-h, #lot-claim, .gfs-bar')].map(e => e.textContent).join(' ') + ' ' + [...j.querySelectorAll('[aria-label]:not(.lot-cell)')].map(e => e.getAttribute('aria-label')).join(' '); })()"
    txt = await pg.evaluate(UI_TXT) + " " + await pg.text_content("#lot-line")
    has_es = "Limpiar" in txt and "Nueva tabla" in txt   # v43: the two big buttons are Spanish on purpose (like a real tabla app)
    low = txt.lower().replace("lotería", "")
    for w in ALLOWED_ES: low = low.replace(w.lower(), "")
    es = [w for w in SPANISH if w.lower() in low]
    check(not es and has_es and "Start" in txt and "Sound is on" in txt and "Pull up a chair" in txt and "drop a bean" in txt, f"Lotería's UI is English (▶ Start · 🔊 Sound · the bean rules) besides the Limpiar / Nueva tabla buttons, the preset names and 'tabla' ({es})")
    names = await pg.evaluate("[...document.querySelectorAll('#lot-tabla .lc-name')].map(e => e.textContent)")
    check(len(names) == 16 and all(n in TRADITIONAL for n in names) and await pg.evaluate("[...document.querySelectorAll('#lot-tabla .lcard .lc-img')].filter(i => /\\/static\\/loteria\\/cards\\/\\d\\d\\.webp$/.test(i.src) && i.naturalWidth >= 200).length") == 16,
          f"the tabla shows the traditional Spanish names with our own vintage pictures ({names[:4]})")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('#juegos').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(200)
    await until(pg, "(document.querySelector('#sync') || {}).dataset?.state !== 'ok'", 6); await pg.wait_for_timeout(400)   # the "Updated" pill gone
    await pg.screenshot(path=os.path.join(OUT, "juegos-english.png"))
    # --- Lotería
    clips = []
    pg.on("requestfinished", lambda r: clips.append(r.url.split("/")[-1]) if "/static/loteria/audio/" in r.url else None)
    await pg.click("#lot-claim"); check("play first" in await pg.text_content("#lot-line"), "¡Lotería! before starting: Tía says to start first (in English)")
    await pg.click("#lot-play"); await pg.wait_for_timeout(700)
    s = await st(pg)
    check(s["running"] and len(s["called"]) == 1 and await pg.evaluate("!!document.querySelector('#lot-card .lcard')"), "▶ Start: Tía calls a card (shown in her bubble)")
    line = await pg.text_content("#lot-line"); first = s["called"][0]
    verse = await pg.evaluate(f"ChismeLoteriaCards.CARDS[{first - 1}].verse")
    check(line == verse and await pg.get_attribute("#lot-line", "lang") == "es" and await pg.text_content("#lot-play") == "⏸ Pause", f"the call on screen is the card's Spanish verse ({line!r}); the buttons stay English")
    ok_voice = await until(pg, f"(() => {{ const v = {G}.state.voice; return v.last === '{first:02d}' && v.clips === 2; }})()", 6)
    v = (await st(pg))["voice"]
    check(ok_voice and v["fallbacks"] == 0 and v["src"].endswith(f"/static/loteria/audio/{first:02d}.mp3") and "intro.mp3" in clips,
          f"she says it out loud from the recorded clips: '¡Se va y se corre con…!' then the card's verse + name ({v}, fetched {clips[:3]})")
    check(await pg.evaluate("__spoken.length") == 0, "…not the phone's robot voice (speechSynthesis only as a fallback)")
    f = await fs(pg)
    bar = await pg.evaluate("(() => { const b = document.querySelector('.gfs-badge').getBoundingClientRect(), p = document.querySelector('.gfs-bar #lot-pick'), m = document.querySelector('.gfs-bar #lot-marked'); return { left: b.left < 30 && b.top < 60, pick: !!p, marked: !!m && /^\\d+ \\/ 16$/.test(m.textContent) }; })()")
    check(fs_ok(f) and "Lotería Chismosa" in f["badge"] and bar["left"] and bar["pick"] and bar["marked"], f"v40 ▶ Start: Lotería goes full screen (fixed overlay {f['iw']}×{f['ih']}, tab bar + footer hidden, ✕ top right); v43 the bar holds the badge (left), the tabla picker and the 'x / 16' bean count {bar}")
    lay = await pg.evaluate(LAYOUT_JS)
    check(lay["ok"] and (lay["w"] >= 0.85 * f["iw"] or lay["h"] >= 0.62 * f["ih"]) and lay["h"] >= 0.6 * f["ih"] and not lay["scroll"], f"v41 the board fills (nearly) the width or (on this short {f['ih']} px screen) the height, nothing cut off, no scrolling (board {lay['w']:.0f}×{lay['h']:.0f} on {f['iw']}×{f['ih']})")
    check(lay["card"] < lay["cell"] * 0.75, f"…the called card sits small above the board ({lay['card']:.0f} px wide vs {lay['cell']:.0f} px board cards)")
    check(await pg.evaluate("__chisme.view") == "juegos" and (await st(pg))["fullscreen"], "…and the game says it's full screen")
    await pg.screenshot(path=os.path.join(OUT, "loteria-calls.png"))
    await pg.click("#lot-play"); n0 = len((await st(pg))["called"]); await pg.wait_for_timeout(5200)
    check(not (await st(pg))["running"] and len((await st(pg))["called"]) == n0 and not (await st(pg))["voice"]["talking"], "⏸ Pause stops the calling (and her voice)")
    await pg.click("#lot-pick"); await pg.wait_for_timeout(250)   # v43: the speed lives in the "Pick your tabla" sheet
    await pg.click("#lot-speed"); s = await st(pg)
    check(s["speed"] == "fast" and json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))["speed"] == "fast", "speed: Normal → Fast (remembered)")
    check(await pg.text_content("#lot-speed") == "🐇 Fast", "the speed button says 🐇 Fast")
    await pg.click("#lot-sheet-x"); await pg.wait_for_timeout(200)
    # beans: only on a called card; an uncalled card shakes; tap again takes the bean off
    s = await st(pg)
    un = next(i for i, c in enumerate(s["tabla"]) if c not in s["called"])
    await pg.click(f'.lot-cell[data-i="{un}"]')
    shook = await pg.evaluate(f"document.querySelector('.lot-cell[data-i=\"{un}\"]').classList.contains('nope')")
    check(await pg.get_attribute(f'.lot-cell[data-i="{un}"]', "aria-pressed") == "false" and shook and not (await st(pg))["marks"], "tap a card that hasn't been called: no bean, just a little shake")
    for _ in range(54):
        s = await st(pg)
        if any(c in s["called"] for c in s["tabla"]): break
        await pg.evaluate(G + ".callNext()")
    ci = next(i for i, c in enumerate(s["tabla"]) if c in s["called"]); p0 = (await st(pg))["plinks"]
    await pg.click(f'.lot-cell[data-i="{ci}"]'); await pg.wait_for_timeout(600)
    bean = await pg.evaluate(f"(() => {{ const c = document.querySelector('.lot-cell[data-i=\"{ci}\"]'), b = c.querySelector('.frijol'), r = b.getBoundingClientRect(), cr = c.getBoundingClientRect(); return {{ op: getComputedStyle(b).opacity, anim: getComputedStyle(b).animationName, w: r.width / cr.width, use: !!b.querySelector('use'), sym: !!document.querySelector('symbol#bean') }}; }})()")
    check(await pg.get_attribute(f'.lot-cell[data-i="{ci}"]', "aria-pressed") == "true" and bean["op"] == "1" and bean["anim"] == "bean-drop" and bean["sym"] and 0.7 < bean["w"] < 1.15,
          f"tap a called card: a big pinto bean drops onto it and covers it ({bean})")
    check((await st(pg))["plinks"] == p0 + 1, "…with a little 'tock' sound")
    await pg.click(f'.lot-cell[data-i="{ci}"]'); await pg.wait_for_timeout(300)
    check(await pg.get_attribute(f'.lot-cell[data-i="{ci}"]', "aria-pressed") == "false" and not (await st(pg))["marks"] and await pg.evaluate(f"getComputedStyle(document.querySelector('.lot-cell[data-i=\"{ci}\"] .frijol')).opacity") == "0", "tap it again: the bean comes off")
    await pg.click(f'.lot-cell[data-i="{ci}"]')
    await pg.click("#lot-claim"); check("Not yet" in await pg.text_content("#lot-line"), "¡Lotería! without a full line: 'Not yet, sweetheart' (in English)")
    await pg.click(f'.lot-cell[data-i="{ci}"]')
    await pg.click("#lot-voice"); c0 = (await st(pg))["voice"]["clips"]; await pg.evaluate(G + ".callNext()")
    s = await st(pg)
    check(s["muted"] and s["voice"]["clips"] == c0 and await pg.evaluate("__spoken.length") == 0 and "🔇" in await pg.text_content("#lot-voice"), "🔇 Sound mutes her (no clip, no fallback voice)")
    await pg.click("#lot-voice")
    # call until row 1 (cells 0–3) is all called, then bean it and claim
    for _ in range(54):
        s = await st(pg)
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(250)
    s = await st(pg); stored = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))
    check(s["over"] and await pg.evaluate("document.querySelector('#view-juegos .game-stage').classList.contains('won') || !!document.querySelector('.won')"), "a full row of beans + ¡Lotería!: a win")
    brag = await pg.text_content("#lot-line")
    check(await pg.evaluate("!!document.querySelector('.lot-confetti')") and brag.startswith("¡Lotería! I told you") and "(a row)" in brag, f"confetti + Tía brags in English ({brag[:60]!r})")
    check(s["voice"]["last"] == "loteria", f"…and shouts '¡Lotería!' (recorded clip {s['voice']['last']!r})")
    check(await pg.text_content("#lot-play") == "▶ Play again", "after a win: ▶ Play again")
    check(stored["wins"] == 1 and stored["streak"] == 1 and stored["best"] == 1, f"wins / streak / best streak saved on the phone ({ {k: stored[k] for k in ('wins', 'streak', 'best')} })")
    check(await pg.evaluate("document.querySelectorAll('.lot-cell.win').length") == 4, "the winning line is highlighted")
    await pg.screenshot(path=os.path.join(OUT, "loteria-win.png"))
    await pg.click("#lot-new"); await pg.click("#lot-play"); await pg.wait_for_timeout(300); await pg.click("#lot-play"); await pg.click("#lot-new")
    stored = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))
    check(stored["streak"] == 0 and stored["best"] == 1, "Nueva tabla mid-game ends the streak; the best streak stays")
    await pg.click("#lot-play"); await pg.wait_for_timeout(300)
    check((await st(pg))["running"] and (await fs(pg))["on"], "▶ Start again: calling, full screen")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(400)
    s = await st(pg); f = await fs(pg); n0 = len(s["called"])
    back = await pg.evaluate("(() => { const b = document.querySelector('.game-pick').getBoundingClientRect(); return b.top >= 0 && b.bottom <= innerHeight; })()")
    await pg.wait_for_timeout(3200)
    check(not s["running"] and not s["fullscreen"] and not f["on"] and f["tabs"] and f["foot"] and back and len((await st(pg))["called"]) == n0,
          f"✕: the calling stops, back to the Juegitos list, tab bar + footer back (running {s['running']}, fs {f['on']}, tabs {f['tabs']}, list in view {back})")
    # --- The Juan That Got Away (v44; replaces Ice Ice Bebé)
    await pg.click('.game-pick[data-game="juan"]'); await to_stage(pg)
    s = await st(pg)
    how = await pg.evaluate("[...document.querySelectorAll('#juan-ov .juan-how li')].map(l => l.textContent.trim())")
    check(s["mode"] == "title" and "The Juan That Got Away" in s["overlay"] and "¡Ya es viernes! One last shift, then cold ones." in s["overlay"]
          and how == ["👆Tap to jump (or twice!)", "🚧Hop cones, carts & ICE", "☕Grab coffee & tacos", "🍻Reach Noche Caliente"], f"v49.4: title screen = a one-line hook + 4 short how-to-play lines ({how})")
    check(await pg.evaluate("document.querySelectorAll('.juan-rules .juan-how li').length") == 4 and "Nobody gets hurt" not in await pg.evaluate("document.querySelector('.juan-rules').textContent"), "v49.4: the same 4 lines under the game (the long rules paragraph is gone)")
    await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(700)
    s1 = await st(pg); await pg.wait_for_timeout(500); s2 = await st(pg)
    check(s2["mode"] == "run" and s2["x"] > s1["x"] + 20 and s2["outfit"] == "work" and s2["health"] == 100, f"Juan runs, in his work clothes, full health ({s1['x']:.0f} → {s2['x']:.0f}, {s2['outfit']}, {s2['health']})")
    f = await fs(pg)
    check(fs_ok(f) and f["badgeMid"] and "The Juan That Got Away" in f["badge"] and await pg.text_content(".gfs-juan-t b") == "That Got Away" and await pg.evaluate("!!document.querySelector('.gfs-badge.gfs-juan svg.gfs-juan-hat')"), f"▶ Start: The Juan That Got Away goes full screen (fixed overlay {f['iw']}×{f['ih']}, tab bar + footer hidden, ✕ top right, hard-hat 'The Juan' + pink 'That Got Away' badge top center) {f}")
    cvr = await pg.evaluate("(() => { const r = document.querySelector('#juan-cv').getBoundingClientRect(), c = document.querySelector('#juan-cv'); return { w: r.width, h: r.height, cw: c.width, ch: c.height, top: r.top, bot: r.bottom }; })()")
    check(cvr["ch"] > cvr["cw"] * 1.4 and cvr["h"] >= 0.7 * f["ih"] and cvr["w"] >= 0.9 * f["iw"], f"…a tall portrait screen that fills the phone ({cvr['cw']}×{cvr['ch']} px shown at {cvr['w']:.0f}×{cvr['h']:.0f})")
    s = await st(pg)
    check(s["dpr"] >= 2 and abs(s["backing"][0] - s["cssW"] * s["dpr"]) <= 2, f"…drawn at the phone's pixel density, so it's crisp (dpr {s['dpr']}, {s['backing']} px for {s['cssW']:.0f} css px)")
    hud = await pg.evaluate("""(() => { const c = document.querySelector('#juan-cv'), g = c.getContext('2d'), S = c.width / 360, px = (x, y) => [...g.getImageData(Math.round(x * S), Math.round(y * S), 1, 1).data].slice(0, 3);
      return { chip: px(17, 21), heart: px(143, 46), panel: px(200, 28), track: px(110, 44), health: px(240, 44.5) }; })()""")
    dark = lambda c: max(c) < 70
    check(hud["chip"] == [255, 61, 139] and hud["heart"] == [255, 61, 139] and dark(hud["panel"]) and hud["track"] == [58, 64, 88] and hud["health"][0] == 255 and hud["health"][2] > 139, f"…a HUD across the top of the canvas, right under the ✕ bar (pink LV chip + heart on a dark panel, progress track, full pink health bar) {hud}")
    await pg.locator("#juan-cv").dispatch_event("pointerdown"); await pg.wait_for_timeout(150)
    check(not (await st(pg))["ground"], "tap the game: he jumps")
    await pg.wait_for_timeout(900)
    await pg.keyboard.press("Space"); await pg.wait_for_timeout(120)
    check(not (await st(pg))["ground"], "Space: he jumps")
    s = await st(pg)
    check(s["fxMade"] > 5, f"particles: dust behind his boots and on landing, sparkles on the double jump / pickups ({s['fxMade']} so far)")
    # a bump costs a little health (no game over)
    await until(pg, G + ".state.ground", 2)
    hz = next(e for e in await pg.evaluate(G + ".ents()") if e["t"] == "cone" and e["x"] > 700)
    await pg.evaluate(f"{G}.warp(1, {hz['x'] - 150}); {G}.setHealth(100)")
    bumped = await until(pg, G + ".state.health < 100", 4); s = await st(pg)
    check(bumped and s["mode"] == "run" and s["health"] >= 80 and re.search(r"−\d+$", s["msg"]), f"bump a hazard: a little health gone, a pop-up, keep running ({s['health']}, {s['msg']!r})")
    hz = next(e for e in await pg.evaluate(G + ".ents()") if e["t"] in ("cone", "pothole", "cart") and e["st"] != "hit" and 700 < e["x"] < 1750)
    await pg.wait_for_timeout(1100)   # the blink after the last bump is over
    await pg.evaluate(f"{G}.warp(1, {hz['x'] - 150}); {G}.setHealth(1)")
    oops = await until(pg, G + ".state.mode === 'oops'", 20)
    s = await st(pg)
    check(oops and s["oopsMsg"] in OOPS and "worn out" in s["overlay"] and "Try again" in s["overlay"], f"out of health: big {s['oopsMsg']!r} + 'Juan's worn out. Try again'")
    await until(pg, G + ".state.mode === 'run'", 3)
    s = await st(pg)
    check(s["x"] < 200 and s["health"] == 100, f"…and back to the start with full health (x {s['x']:.0f})")
    msgs = {s["oopsMsg"]}
    await pg.evaluate(G + ".warp(1, 1880)")
    check(await until(pg, G + ".state.ck === 1", 3), "running past the 🚩 flag sets a checkpoint")
    x = (await st(pg))["x"]; hz = next(e for e in await pg.evaluate(G + ".ents()") if e["t"] in ("cone", "pothole", "cart") and e["x"] > x + 160)
    await pg.evaluate(f"{G}.warp(1, {hz['x'] - 150}); {G}.setHealth(1)")
    await until(pg, G + ".state.mode === 'oops'", 25); msgs.add((await st(pg))["oopsMsg"]); await until(pg, G + ".state.mode === 'run'", 3)
    x = (await st(pg))["x"]
    check(2000 <= x < 2120, f"worn out after the checkpoint → back to the checkpoint (x {x:.0f})")
    async def grab(n, kind, ok_js):
        for off in (40, 60, 25, 85, 110):
            es = [e for e in await pg.evaluate(G + ".ents()") if e["t"] == kind and e["x"] > 300]
            if not es: await pg.evaluate(f"{G}.warp({n}, 10)"); continue
            await until(pg, G + ".state.mode === 'run'", 3)
            await pg.evaluate(f"{G}.warp({n}, {es[0]['x'] - off}); {G}.setHealth(50)"); await pg.wait_for_timeout(30); await pg.evaluate(G + ".jump()")
            if await until(pg, ok_js, 0.9): return True
        return False
    for kind, ok_js, want in (("coffee", G + ".state.boost > 0", "Coffee! Speed boost"), ("taco", G + ".state.health >= 75", "Breakfast taco! +30 health"), ("flipflops", G + ".state.shield > 0", "Flip-flops! Shield on")):
        got = await grab(1, kind, ok_js); s = await st(pg)
        check(got and s["msg"] == want, f"{ {'coffee': '☕ coffee → speed boost', 'taco': 'breakfast taco → +30 health', 'flipflops': 'v46: 🩴 flip-flops → shield'}[kind] }, with an English pop-up ({s['msg']!r}, boost {s['boost']:.1f}, health {s['health']}, shield {s['shield']})")
    # v46: the ICE agents (shield on from the flip-flops: the next agent who reaches him just gets dizzy)
    async def to_agent(n, gap=330):   # stand Juan `gap` in front of an agent with no cone by him (he'd trip on it), the road between clear
        await until(pg, G + ".state.mode === 'run'", 3); await pg.evaluate(f"{G}.warp({n}, 100)")
        es = await pg.evaluate(G + ".ents()")
        ag = next(e for e in es if e["t"] == "agent" and e["x"] > 900 and not any(k["t"] == "cone" and e["x"] - 160 < k["x"] < e["x"] + 30 for k in es))
        await pg.evaluate(f"{G}.warp({n}, {ag['x'] - gap}); {G}.clearAhead({gap - 40})"); return ag
    await to_agent(1); await pg.evaluate(f"{G}.setHealth(100)")
    if (await st(pg))["shield"] <= 0: await grab(1, "flipflops", G + ".state.shield > 0"); await to_agent(1)
    dz = await until(pg, f"{G}.ents().some(e => e.t === 'agent' && e.st === 'dizzy')", 4); s = await st(pg)
    check(dz and s["mode"] == "run" and s["shield"] == 0 and s["msg"] == "Flip-flops! He's dizzy", f"v46: shield on, an agent reaches Juan → he just gets dizzy, Juan keeps running ({s['msg']!r}, {s['mode']})")
    await pg.wait_for_timeout(2700)   # he shakes it off
    await to_agent(1)
    caught = await until(pg, G + ".state.mode === 'oops'", 5); s = await st(pg)
    check(caught and s["oopsMsg"] in CAUGHT and s["caughtBy"] == "agent" and "Caught!" in s["overlay"] and "tries again" in s["overlay"] and s["oopsMsg"] in s["overlay"], f"v46/v47: run into an agent → caught: a big {s['oopsMsg']!r} + 'Caught! Juan tries again…' ({s['overlay'][-50:]!r})")
    await until(pg, G + ".state.mode === 'run'", 3); s = await st(pg)
    check(s["mode"] == "run" and s["health"] == 100, "…then back to the last checkpoint, nobody hurt")
    seen = [(await st(pg))["oopsMsg"]]   # v47: get caught a few more times: a different line each time
    for _ in range(4):
        await to_agent(1); await pg.evaluate(f"{G}.setHealth(100)")
        if await until(pg, G + ".state.mode === 'oops'", 5): seen.append((await st(pg))["oopsMsg"])
        await until(pg, G + ".state.mode === 'run'", 3)
    check(len(seen) == 5 and all(m in CAUGHT for m in seen) and all(a != b for a, b in zip(seen, seen[1:])), f"v47: caught 5 times in a row: the line changes every time, never the same twice ({seen})")
    last_caught = seen[-1]
    await to_agent(1); f0 = (await st(pg))["fueras"]
    for _ in range(160):   # hop over him: jump when he's close
        es = [e for e in await pg.evaluate(G + ".ents()") if e["t"] == "agent"]; x = (await st(pg))["x"]
        if min([e["x"] - x for e in es if e["x"] > x - 40] or [999]) < 95: await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(170); await pg.evaluate(G + ".jump()"); break
        await pg.wait_for_timeout(15)
    hop = await until(pg, G + ".state.fuera", 2); s = await st(pg)
    check(hop and s["fueras"] > f0 and s["mode"] == "run", f"v46: hop over an agent → a big '¡Fuera!' and bonus points ({s['fueras']} escapes)")
    await until(pg, "!" + G + ".state.fuera", 3)
    # v46: black ICE SUVs now and then in the far lane (driving by, or parked at the far curb): scenery only
    await pg.evaluate(f"{G}.warp(1, 1500); {G}.clearAhead(700); {G}.setHealth(100); {G}.bgSpawn('drive', 30); {G}.bgSpawn('parked', 240)")
    b0, sx0 = await pg.evaluate(f"[{G}.bgIce(), {G}.state.x]"); s0 = await st(pg); await pg.wait_for_timeout(900)
    b1, sx1 = await pg.evaluate(f"[{G}.bgIce(), {G}.state.x]"); s = await st(pg); es = await pg.evaluate(G + ".ents()")   # (the cars + where Juan is in the same frame)
    pk0 = next(c for c in b0["cars"] if c["kind"] == "parked"); pk1 = next((c for c in b1["cars"] if c["kind"] == "parked"), None)
    dv0 = next(c for c in b0["cars"] if c["kind"] == "drive")
    check(len(b0["cars"]) >= 2 and all(c["y"] >= 30 for c in b0["cars"]) and dv0["vx"] != 0 and pk0["vx"] == 0 and not [e for e in es if e["x"] - 60 < s["x"] < e["x"] + 60 and e["t"] == "suv"]
          and s["mode"] == "run" and s["health"] == 100 and s["caught"] == s0["caught"], f"v46: dark ICE SUVs drive by / sit parked in the far lane, just scenery: Juan runs right past them ({s['mode']}, health {s['health']})")
    mv = pk1["sx"] - pk0["sx"] if pk1 else 0
    check(pk1 is not None and abs((pk1["sx"] - pk0["sx"]) + (sx1 - sx0)) < 1 and 0 < b1["next"] <= 17, f"…the parked one scrolls with the street, and another comes along now and then (moved {mv:.0f} as Juan ran {sx1 - sx0:.0f}; next in {b1['next']:.1f} s)")
    suv = next(e for e in await pg.evaluate(G + ".ents()") if e["t"] == "suv")
    await pg.evaluate(f"{G}.warp(1, {suv['x'] + suv['w'] + 62}); {G}.clearAhead(1400)")
    ch = await until(pg, G + ".state.chase", 2); s = await st(pg)
    check(ch and s["msg"] == "¡Vámonos, amigo!", f"v46: run past a dark SUV → an agent hops out and chases Juan ('¡Vámonos, amigo!') ({s['msg']!r})")
    f0 = s["fueras"]; away = await until(pg, G + ".state.fuera", 5); s = await st(pg)
    check(away and not s["chase"] and s["fueras"] > f0 and s["mode"] == "run", f"…he runs out of breath: '¡Fuera!', Juan got away ({s['fueras']})")
    suv = next((e for e in await pg.evaluate(G + ".ents()") if e["t"] == "suv" and e["x"] > s["x"] + 300), None)
    if suv:
        await pg.evaluate(f"{G}.warp(1, {suv['x'] + suv['w'] + 62}); {G}.clearAhead(1400)"); await until(pg, G + ".state.chase", 2); await pg.evaluate(G + ".stumble(3)")
        got = await until(pg, G + ".state.mode === 'oops'", 4); s = await st(pg)
        check(got and s["caughtBy"] == "chaser" and s["oopsMsg"] in CAUGHT and s["oopsMsg"] != last_caught, f"v46: slowed down while chased → the agent catches up: {s['oopsMsg']!r}, not {last_caught!r} again ({s['caughtBy']})")
        await until(pg, G + ".state.mode === 'run'", 3)
    await pg.evaluate(f"{G}.warp(1, 5900)")
    await until(pg, G + ".state.mode === 'clear'", 6)
    s = await st(pg)
    check(s["mode"] == "clear" and "You made it to Hon Dipo!" in s["overlay"] and "Supplies loaded. ¡Órale!" in s["overlay"] and s["levelMax"] == 2, f"level 1 cleared at Hon Dipo ({s['overlay'][:40]!r})")
    await pg.click('#juan-ov [data-act="next"]'); await pg.wait_for_timeout(200)
    check((await st(pg))["level"] == 2 and (await st(pg))["mode"] == "run" and (await st(pg))["name"] == "La Chamba", "▶ on to level 2: La Chamba")
    await pg.click("#juan-pause"); s = await st(pg); await pg.wait_for_timeout(600)
    check(s["mode"] == "paused" and (await st(pg))["x"] == s["x"], "⏸ Pause freezes the game")
    await pg.click("#juan-pause")
    check((await st(pg))["mode"] == "run" and (await fs(pg))["on"], "▶ Resume: still full screen")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    s = await st(pg); f = await fs(pg)
    check(s["mode"] == "paused" and not f["on"] and f["tabs"] and f["foot"] and "Paused" in s["overlay"], f"✕: The Juan That Got Away pauses and it's back to Juegitos (tab bar + footer back) ({s['mode']}, fs {f['on']})")
    await pg.click('#juan-ov [data-act="resume"]'); await pg.wait_for_timeout(200)
    check((await st(pg))["mode"] == "run" and (await fs(pg))["on"], "▶ Resume from the list: full screen again")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
    check((await st(pg))["mode"] == "paused" and not (await fs(pg))["on"], "Escape works like ✕ (paused, out of full screen)")
    await pg.click('#juan-ov [data-act="resume"]'); await pg.wait_for_timeout(150)
    await pg.click("#juan-sound")
    check((await st(pg))["muted"] and json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos-juan')"))["muted"], "🔇 Sound mutes the beeps (remembered)")
    # level 6 (Noche Caliente): cowboy clothes, cold ones (+health)
    got = await grab(6, "beer", G + ".state.beers > 0"); s = await st(pg)
    check(got and s["outfit"] == "western" and s["health"] > 50 and s["msg"] == "¡Salud! +8 health", f"level 6: boots + cowboy hat on; jump for a cold one → a little health ({s['msg']!r}, health {s['health']}, beers {s['beers']})")
    await pg.evaluate(f"{G}.warp(6, 5900)")
    cl6 = await until(pg, G + ".state.mode === 'clear'", 6); s = await st(pg)
    check(cl6 and "You made it to Noche Caliente!" in s["overlay"] and "Level 7: Dice City VI" in s["overlay"], f"v49.5: Noche Caliente → on to the celebration level, Dice City VI ({s['overlay'][:90]!r})")
    await pg.evaluate(f"{G}.warp(7, 5900)")
    won = await until(pg, G + ".state.mode === 'win'", 6)
    await pg.wait_for_timeout(1300)
    s = await st(pg); juan = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos-juan')"))
    note = await pg.text_content("#juan-note")
    check(won and "¡Salud, Juan!" in s["overlay"] and "From Noche Caliente to the beach at Dice City VI" in s["overlay"] and "Friday shift done" in note and "Noche Caliente" in note and "Dice City VI" in note, f"level 7: the win after Dice City VI, '¡Salud, Juan!' ({note[:70]!r})")
    txt = await pg.evaluate("(() => { const j = document.querySelector('#view-juegos'); return [...j.querySelectorAll('#juegos, #game-stage')].map(e => e.textContent).join(' ') + ' ' + [...j.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' '); })()")   # textContent: the rules are hidden while full screen
    es = [w for w in SPANISH if w.lower() in txt.lower().replace("lotería", "")]
    check(not es and "Tap to jump (or twice!)" in txt and "Hop cones, carts & ICE" in txt and "Grab coffee & tacos" in txt and "Reach Noche Caliente" in txt, f"The Juan That Got Away's UI is English (v49.4: the 4 short how-to-play lines) ({es})")
    check(juan["best"] >= s["score"] > 0 and juan["wins"] == 1 and juan["levelMax"] == len(JUAN_LEVELS), f"best score saved on the phone ({juan['best']})")
    check("Play again" in s["overlay"], "…with ▶ Play again right on the full-screen win screen")
    await pg.screenshot(path=os.path.join(OUT, "juan-win.png"))
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    check(msgs <= OOPS, f"worn-out lines seen (kept in Spanish): {sorted(msgs)}")
    check(await pg.evaluate("document.querySelectorAll('#game-stage a').length") == 0, "no links in the games")
    check(not outside, f"no outside requests while playing (besides other tabs' images) ({outside[:3]})")
    # a fresh The Juan That Got Away (title screen), then News: Space there must not start the game
    await pg.click('.game-pick[data-game="loteria"]'); await pg.click('.game-pick[data-game="juan"]'); await pg.wait_for_timeout(200)
    await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(200)
    await pg.keyboard.press("Space"); await pg.wait_for_timeout(300)
    check((await st(pg))["mode"] == "title", "Space on another tab doesn't touch the game (and switching games drops the old one)")
    await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await pg.wait_for_timeout(200)
    await pg.keyboard.press("Space"); await pg.wait_for_timeout(300)
    check((await st(pg))["mode"] == "run" and (await fs(pg))["on"], "…and on Juegitos, Space starts it (full screen)")
    await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(250)
    f = await fs(pg)
    check(not f["on"] and f["tabs"] and (await st(pg))["mode"] == "paused", f"leaving the tab drops full screen and pauses the game (fs {f['on']}, {(await st(pg))['mode']})")
    await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await pg.wait_for_timeout(200)
    # Settings → default tab Juegitos
    await pg.click("#settings-btn"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('input[name=deftab][value=juegos]').scrollIntoView()")
    await pg.click("label:has(input[name=deftab][value=juegos]) span")
    check(await pg.evaluate("localStorage.getItem('chisme-default-tab')") == "juegos", "Settings → Default opening tab has 🎲 Juegitos")
    await pg.keyboard.press("Escape")
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(500)
    check(await pg.evaluate("__chisme.view") == "juegos" and await pg.evaluate("document.querySelectorAll('.game-pick').length") == 2, "Settings → default tab: Juegitos opens first")
    check(not errs, f"no page errors ({errs[:3]})")
    await ctx.close()
    # reduce motion
    ctx = await b.new_context(**dev, reduced_motion="reduce", service_workers="block"); await quiet_board(ctx); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page()
    await pg.route("**/static/loteria/audio/**", lambda r: r.abort())   # v41: the recorded clips can't load → the phone's own Spanish voice
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    await pg.click("#lot-play"); await pg.wait_for_timeout(700); await pg.click("#lot-play")
    sp = await pg.evaluate("__spoken"); s = await st(pg)
    want = await pg.evaluate(f"ChismeLoteriaCards.callText(ChismeLoteriaCards.CARDS[{s['called'][0] - 1}])")
    check(len(sp) >= 1 and sp[0]["lang"] == "es-MX" and sp[0]["text"] == "¡Se va y se corre con…!" and s["voice"]["fallbacks"] >= 1,
          f"a clip that fails to load falls back to the phone's es-MX voice ({sp[:2]}, {s['voice']})")
    check(await until(pg, f"__spoken.some(u => u.text === {json.dumps(want)} && u.lang === 'es-MX')", 3), f"…for the card's verse + name too ({want!r})")
    for _ in range(60):
        s = await st(pg)
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(200)
    s = await st(pg)
    check(s["over"] and not await pg.evaluate("!!document.querySelector('.lot-confetti')"), f"reduce motion: a win without confetti (over {s['over']}, marks {s['marks']}, line {await pg.text_content('#lot-line')!r})")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="juan"]'); await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(300)
    await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(1200)
    s = await st(pg)
    check(not s["parallax"] and s["fxMade"] == 0 and s["fullscreen"], f"reduce motion: The Juan That Got Away's background stays still (no parallax, shake, particles or confetti), still full screen (fx {s['fxMade']})")
    nx = (await pg.evaluate(G + ".bgIce()"))["next"]
    for _ in range(8): await pg.evaluate(G + ".bgSpawn()")
    bg = await pg.evaluate(G + ".bgIce()")
    check(nx > 9 and bg["cars"] and all(c["kind"] == "parked" and c["vx"] == 0 for c in bg["cars"]), f"reduce motion: the background ICE SUVs only sit parked, and come along rarely (next in {nx:.0f} s)")
    await b.close()

async def fullscreen_shots(p):
    print("\n== WebKit 390×844: full-screen screenshots")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 1   # screenshots exactly 390×844
    ctx = await b.new_context(**dev); await quiet_board(ctx); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    for alias in ("#juan-that-got-away", "#juans-long-day"):   # the new title's link + the old one (#juan below)
        await pg.goto(BASE + "/" + alias); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
        check(await pg.evaluate("__chisme.view") == "juegos" and await pg.evaluate("__chisme.juegos.id") == "juan", f"{alias} opens Juegitos → The Juan That Got Away")
    await pg.goto(BASE + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    await until(pg, "(document.querySelector('#sync') || {}).dataset?.state === 'done'", 15)   # the "Updating… / ✓ Updated" pill gone, so it doesn't cover the title
    await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 60); }"); await pg.wait_for_timeout(700)
    s = await st(pg)
    check(await pg.evaluate("__chisme.juegos.id") == "juan" and s["mode"] == "title", "#juan opens Juegitos → The Juan That Got Away (title screen)")
    await pg.screenshot(path=os.path.join(OUT, "juan-intro.png"))
    await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(300)
    await pg.evaluate(G + ".warp(1, 5740)"); await pg.wait_for_timeout(350); await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(200)
    f = await fs(pg); s = await st(pg)
    cvh = await pg.evaluate("document.querySelector('#juan-cv').getBoundingClientRect().height")
    check(fs_ok(f) and s["mode"] == "run" and s["level"] == 1 and s["H"] > 1.7 * s["W"] and cvh > 0.8 * f["ih"], f"390×844: The Juan That Got Away level 1, running up to Hon Dipo, full screen (canvas {s['W']}×{s['H']:.0f}, {cvh:.0f} px tall on an {f['ih']} px screen)")
    await pg.screenshot(path=os.path.join(OUT, "juan-l1.png"))
    await pg.evaluate(G + ".warp(2, 5780)"); await pg.wait_for_timeout(450)
    s = await st(pg)
    check(s["level"] == 2 and s["name"] == "La Chamba" and (await fs(pg))["on"], f"v47 390×844: level 2, La Chamba: the construction site with the COMING SOON Gualmart sign ({s['mode']})")
    await pg.screenshot(path=os.path.join(OUT, "la-chamba.png"))
    await pg.evaluate(G + ".warp(3, 5780)"); await pg.wait_for_timeout(450)
    s = await st(pg)
    check(s["level"] == 3 and s["name"] == "Don Pedroes" and (await fs(pg))["on"], f"390×844: level 3, Don Pedroes ({s['mode']})")
    await pg.screenshot(path=os.path.join(OUT, "juan-don-pedroes.png"))
    await pg.evaluate(G + ".warp(6, 5790)"); await pg.wait_for_timeout(120); await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(260)
    s = await st(pg); beers = [e for e in await pg.evaluate(G + ".ents()") if e["t"] == "beer"]
    check(s["level"] == 6 and s["outfit"] == "western" and not s["ground"] and len(beers) >= 3, f"390×844: level 6, cowboy Juan jumping for the cold ones by Noche Caliente ({len(beers)} beers left, {s['mode']})")
    await pg.screenshot(path=os.path.join(OUT, "juan-l5.png"))
    # v47: caught by ICE, one of the new lines: "¡Ay cabrón!" (same big caption as "¡Ay no!")
    async def caught_by(line, n=1):
        await pg.evaluate(f"{G}.warp({n}, 100)"); await until(pg, G + ".state.mode === 'run'", 3); es = await pg.evaluate(G + ".ents()")
        ag = next(e for e in es if e["t"] == "agent" and e["x"] > 900 and not any(k["t"] == "cone" and e["x"] - 160 < k["x"] < e["x"] + 30 for k in es))
        await pg.evaluate(f"{G}.warp({n}, {ag['x'] - 330}); {G}.clearAhead(290); {G}.setHealth(100); {G}.caughtNext({json.dumps(line)})")
        ok = await until(pg, G + ".state.mode === 'oops'", 5); await pg.wait_for_timeout(120)
        return ok, await st(pg), await pg.evaluate(G + ".captionBox()")
    ok, s, cap = await caught_by("¡Ay cabrón!")
    check(ok and s["oopsMsg"] == "¡Ay cabrón!" and "Caught!" in s["overlay"] and cap["size"] == 42, f"v47 390×844: caught → a big '¡Ay cabrón!' in the '¡Ay no!' caption style ({cap})")
    await pg.screenshot(path=os.path.join(OUT, "juan-caught-cabron.png"))
    await until(pg, G + ".state.mode === 'run'", 3)
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="loteria"]'); await pg.wait_for_timeout(300)
    await pg.click("#lot-play"); await pg.wait_for_timeout(300); await pg.click("#lot-play")   # paused, so the called card stays put for the picture
    for _ in range(40):
        s = await st(pg)
        if sum(c in s["called"] for c in s["tabla"]) >= 5: break
        await pg.evaluate(G + ".callNext()")
    marked = [i for i, c in enumerate(s["tabla"]) if c in s["called"]][:5]
    for i in marked: await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.wait_for_timeout(700)
    f = await fs(pg); lay = await pg.evaluate(LAYOUT_JS); beans = await pg.evaluate("[...document.querySelectorAll('.lot-cell.marked .frijol')].filter(b => getComputedStyle(b).opacity === '1').length")
    check(fs_ok(f) and beans == len(marked) >= 4, f"390×844: Lotería full screen mid-game, beans on {beans} called cards")
    check(lay["ok"] and not lay["scroll"] and lay["w"] >= 0.94 * 390 and lay["h"] >= 0.65 * 844 and lay["card"] < lay["cell"] * 0.75 and not lay["clipped"],
          f"390×844: the board is {lay['w']:.0f}×{lay['h']:.0f} (full width, {lay['h'] / 844:.0%} of the height), the called card small above it ({lay['card']:.0f} px), no scrolling, no clipped names {lay['clipped']}")
    await pg.screenshot(path=os.path.join(OUT, "loteria-tabla-big.png"))
    # a sample of the original art: 24 of the 54 cards in a grid
    await pg.evaluate("""() => { const L = ChismeLoteriaCards, d = document.createElement('div'); d.id = 'art-sheet';
      d.style.cssText = 'position:fixed;inset:0;z-index:9000;background:#0d0f1a;padding:8px;box-sizing:border-box;display:grid;grid-template-columns:repeat(4,1fr);gap:6px;align-content:start;overflow:hidden';
      d.innerHTML = '<p style="grid-column:1/-1;margin:2px 0 4px;color:#fff;font-weight:900;text-align:center">Our own vintage Lotería art · 16 of 54 cards</p>' + L.CARDS.filter((c, i) => i % 3 === 0 || i === 25 || i === 37).slice(0, 16).map(c => `<span class="lcard"><img class="lc-img" src="${c.img}" alt="${c.name}"></span>`).join('');
      document.body.appendChild(d); }""")
    await until(pg, "[...document.querySelectorAll('#art-sheet img')].every(i => i.complete && i.naturalWidth)", 8); await pg.wait_for_timeout(200)
    sheet = await pg.evaluate("(() => { const d = document.querySelector('#art-sheet'), l = [...d.querySelectorAll('.lcard')]; return { n: l.length, fits: l[l.length - 1].getBoundingClientRect().bottom <= innerHeight + 1, alts: l.map(e => e.querySelector('img').alt).filter(a => a === 'El Chocolate' || a === 'El Apache') }; })()")
    check(sheet["n"] == 16 and sheet["fits"] and len(sheet["alts"]) == 2, f"a grid of 16 cards' original vintage art fits one 390×844 screen, incl. #26 El Chocolate and #38 El Apache ({sheet})")
    await pg.screenshot(path=os.path.join(OUT, "loteria-cards.png"))
    await pg.evaluate("document.querySelector('#art-sheet').remove()")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    await pg.evaluate("() => window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
    tab = await pg.evaluate("(() => { const t = document.querySelector('.tab[data-view=juegos]'), r = t.getBoundingClientRect(), i = document.querySelector('.tabs-inner'); return { txt: t.textContent.trim(), fits: t.scrollWidth <= t.clientWidth + 1 && r.right <= innerWidth && i.scrollWidth <= i.clientWidth + 1 }; })()")
    check(tab["txt"] == "🎲 Juegitos" and tab["fits"], f"the tab says 🎲 Juegitos and fits the tab bar at 390 px ({tab})")
    check(not errs, f"no page errors ({errs[:3]})")
    await ctx.close()
    # v41: the small phone, 320×640
    dev["viewport"] = {"width": 320, "height": 640}
    ctx = await b.new_context(**dev); await quiet_board(ctx); await ctx.add_init_script(QUIET); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH); pg = await ctx.new_page()
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    await pg.click("#lot-play"); await pg.wait_for_timeout(300); await pg.click("#lot-play")
    for _ in range(6): await pg.evaluate(G + ".callNext()")
    s = await st(pg)
    for i in [i for i, c in enumerate(s["tabla"]) if c in s["called"]][:3]: await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.wait_for_timeout(600)
    # every card's verse in the bubble (the long ones wrap the most), ending on the longest, so the check is the worst case
    vs = await pg.evaluate("""(() => { const C = ChismeLoteriaCards, l = document.querySelector('#lot-line'), all = C.CARDS.map(c => C.callText(c)).sort((a, b) => a.length - b.length); let min = 1e9;
      for (const t of all) { l.textContent = t; min = Math.min(min, document.querySelector('#lot-tabla').getBoundingClientRect().height); } return { min, longest: all[all.length - 1] }; })()""")
    check(vs["min"] >= 0.58 * 640, f"320×640: with any card's verse (even the longest) the board stays {vs['min']:.0f}+ px tall")
    lay = await pg.evaluate(LAYOUT_JS); ctl = await pg.evaluate("[...document.querySelectorAll('.lot-controls .lot-btn')].every(b => b.scrollWidth <= b.clientWidth + 1 && b.getBoundingClientRect().height >= 44)")
    check(lay["ok"] and not lay["scroll"] and lay["w"] >= 0.85 * 320 and lay["h"] >= 0.58 * 640 and ctl and not lay["clipped"],
          f"320×640: everything fits with no scrolling, board {lay['w']:.0f}×{lay['h']:.0f}, controls one row of 44 px buttons ({ctl}), no clipped names {lay['clipped']}")
    await pg.screenshot(path=os.path.join(OUT, "loteria-320.png"))
    # v44: The Juan That Got Away on the small phone
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="juan"]'); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('#game-stage').scrollIntoView()"); await pg.wait_for_timeout(200)
    intro = await pg.evaluate("(() => { const o = document.querySelector('#juan-ov').getBoundingClientRect(), b = document.querySelector('#juan-ov [data-act=start]').getBoundingClientRect(), t = document.querySelector('#juan-ov .juan-big').getBoundingClientRect(); return { btn: b.bottom <= o.bottom + 1 && b.top >= o.top, title: t.left >= o.left && t.right <= o.right }; })()")
    check(intro["btn"] and intro["title"], f"320×640: the intro's title 'The Juan That Got Away', the 6 stops and ▶ Start all fit on the game screen {intro}")
    await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(400)
    badge = await pg.evaluate("(() => { const b = document.querySelector('.gfs-badge.gfs-juan'), t = b.querySelector('.gfs-juan-t'), br = b.getBoundingClientRect(), x = document.querySelector('.gfs-x').getBoundingClientRect(); return { fits: t.scrollWidth <= t.clientWidth + 1 && b.scrollWidth <= b.clientWidth + 1, clear: br.left >= 4 && br.right <= x.left - 4, w: Math.round(br.width), text: t.textContent }; })()")
    check(badge["fits"] and badge["clear"] and badge["text"] == "The Juan That Got Away", f"320×640: the full-screen badge 'The Juan That Got Away' fits whole, clear of the ✕ {badge}")
    await pg.evaluate(G + ".warp(2, 5700)"); await pg.wait_for_timeout(400)
    sm = await pg.evaluate("""(() => { const c = document.querySelector('#juan-cv').getBoundingClientRect(), k = document.querySelector('.juan-controls').getBoundingClientRect(), st = document.querySelector('#game-stage');
      const btns = [...document.querySelectorAll('.juan-controls .lot-btn')];
      return { cw: c.width, ch: c.height, ctop: c.top, cbot: c.bottom, ktop: k.top, kbot: k.bottom, btn: btns.every(b => b.getBoundingClientRect().height >= 40 && b.scrollWidth <= b.clientWidth + 1),
        scroll: st.scrollHeight > st.clientHeight + 1 }; })()""")
    f = await fs(pg); s = await st(pg)
    check(fs_ok(f) and sm["cw"] >= 0.95 * 320 and sm["ch"] >= 0.6 * 640 and sm["cbot"] <= sm["ktop"] + 1 and sm["kbot"] <= 641 and sm["btn"] and not sm["scroll"] and s["mode"] == "run",
          f"320×640: The Juan That Got Away fits: canvas {sm['cw']:.0f}×{sm['ch']:.0f}, the controls below it on screen, no scrolling {sm}")
    await pg.screenshot(path=os.path.join(OUT, "juan-320.png"))
    longest = max(CAUGHT, key=len); ok, s, cap = await caught_by(longest)
    check(ok and s["oopsMsg"] == longest and cap["w"] <= cap["max"] and cap["size"] >= 30 and cap["cssW"] <= 320, f"v47 320×640: the longest caught line {longest!r} fits the screen, still big ({cap})")
    await pg.screenshot(path=os.path.join(OUT, "juan-caught-320.png"))
    await b.close()

async def offline(p):
    print("\n== Chromium: offline")
    b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True); await quiet_board(ctx); await ctx.add_init_script(QUIET)
    await ctx.add_init_script(INIT); pg = await ctx.new_page()
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=60000)
    await pg.wait_for_timeout(2500)
    await ctx.set_offline(True)
    await pg.evaluate("location.hash = '#juan'"); await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.view === 'juegos'", timeout=30000); await pg.wait_for_timeout(500)
    ok = await pg.evaluate("__chisme.juegos.id") == "juan"
    await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(800)
    s = await pg.evaluate(G + ".state")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="loteria"]'); await pg.wait_for_timeout(200)
    check(ok and s["mode"] == "run" and await pg.evaluate("document.querySelectorAll('#lot-tabla .lot-cell').length") == 16, "offline: Juegitos opens (#juan), The Juan That Got Away runs, Lotería deals a tabla")
    shell = re.search(r'VERSION\s*=\s*"(chisme-v\d+(?:\.\d+)?)"', open(os.path.join(HERE, "static", "sw.js")).read()).group(1) + "-shell"   # (this build's cache)
    cached = await pg.evaluate("(async () => { const c = await caches.open('" + shell + "'), k = (await c.keys()).map(r => new URL(r.url).pathname); const r = await fetch('/static/loteria/audio/01.mp3', { headers: { Range: 'bytes=0-99' } }); return { n: k.filter(p => p.startsWith('/static/loteria/audio/')).length, cards: k.includes('/static/loteria_cards.js'), status: r.status, len: (await r.arrayBuffer()).byteLength, cr: r.headers.get('Content-Range') }; })()")
    check(cached["n"] == 57 and cached["cards"] and cached["status"] == 206 and cached["len"] == 100, f"offline: the service worker has all 57 recorded calls + the card art, and answers a Range request with 206 (for Safari) ({cached})")
    await b.close()

async def main():
    unit()
    async with async_playwright() as p:
        await webkit(p); await fullscreen_shots(p); await offline(p)
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
