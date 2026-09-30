"""🎲 Juegitos (v30; v39 all English; v40 renamed from Juegos + full-screen portrait play): a games tab, all on the phone and offline.

1. Node: Lotería Chismosa's deck (30–54 original cards in English; none of the traditional card names, Spanish or English), random 4×4 tablas, and
   wins (rows, columns, diagonals, 4 corners) that only count for cards Tía actually called. Ice Ice Bebé's 5 levels
   (Home Dehole → The Taco Shop → The Corner Store → The Plaza → Mom's House), same course every time, power-ups on each
   level, no hazards right after a checkpoint.
2. WebKit iPhone 13: the 🎲 Juegitos tab (between ¿Cuál dieta? and Events) fits; a list of games. Lotería: Tía (avatar) calls
   cards in English with an English voice, only "Lotería" in a Spanish voice (mutable), pause, speed, new board, tap to put a marker, ¡Lotería! checks the marks,
   confetti + a brag on a win, wins/streak/best in localStorage. Ice Ice Bebé: run, jump (tap / Space), caught → a
   random big pixel "¡Ay no!" / "¡Fuera!" / "¡Vámonos, amigo!" (kept in Spanish) and back to the checkpoint, coffee boost, flip-flop
   shield (the agent just gets dizzy), level clear, the win at Mom's, no Spanish UI text besides Lotería / the catch lines, best score, mute, pause. Reduce motion (no
   confetti, no parallax). No links and no outside requests in the games. Settings → default tab Juegitos.
3. Chromium: offline (service worker), Juegitos still opens and both games run.
Screenshots: juegos-tab.png, juegos-english.png, loteria-english.png, loteria-win.png, ice-ice-bebe-level1.png, ice-ice-bebe-win.png (+ ice-ice-bebe-home-dehole.png)."""
import asyncio, json, os, subprocess
from urllib.parse import urlparse
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
# a recording speechSynthesis (headless browsers have no voices)
SPEECH = """(() => { window.__spoken = [];
  const fake = { speak(u) { __spoken.push({ text: u.text, lang: u.lang }); }, cancel() {}, getVoices() { return [{ lang: 'es-MX', name: 'Test es-MX' }, { lang: 'en-US', name: 'Test en-US' }]; }, addEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {}
  window.SpeechSynthesisUtterance = function (t) { this.text = t; }; })()"""
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

TRADITIONAL = {"el gallo", "el diablito", "la dama", "el catrín", "el paraguas", "la sirena", "la escalera", "la botella", "el barril", "el árbol", "el melón",
  "el valiente", "el gorrito", "la muerte", "la pera", "la bandera", "el bandolón", "el violoncello", "la garza", "el pájaro", "la mano", "la bota", "la luna",
  "el cotorro", "el borracho", "el negrito", "el corazón", "la sandía", "el tambor", "el camarón", "las jaras", "el músico", "la araña", "el soldado", "la estrella",
  "el cazo", "el mundo", "el apache", "el nopal", "el alacrán", "la rosa", "la calavera", "la campana", "el cantarito", "el venado", "el sol", "la corona",
  "la chalupa", "el pino", "el pescado", "la palma", "la maceta", "el arpa", "la rana",
  # the traditional deck's usual English names
  "the rooster", "the little devil", "the lady", "the dandy", "the gentleman", "the umbrella", "the mermaid", "the ladder", "the bottle", "the barrel", "the tree",
  "the melon", "the brave one", "the little bonnet", "the death", "death", "the pear", "the flag", "the mandolin", "the cello", "the heron", "the bird", "the hand",
  "the boot", "the moon", "the parrot", "the drunk", "the heart", "the watermelon", "the drum", "the shrimp", "the arrows", "the musician", "the spider",
  "the soldier", "the star", "the saucepan", "the world", "the apache", "the cactus", "the scorpion", "the rose", "the skull", "the bell", "the water pitcher",
  "the deer", "the sun", "the crown", "the canoe", "the pine tree", "the fish", "the palm tree", "the flowerpot", "the harp", "the frog"}
# v39: Spanish words that must not show up in the games' UI anymore ("Lotería" and Ice Ice Bebé's 3 catch lines are the only Spanish)
SPANISH = ["Empezar", "Pausa", "Seguir", "Otra vez", "Nueva tabla", "Voz", "Lenta", "Rápida", "mija", "Siéntate", "carta", "baraja", "Primero", "Todavía",
  "Ganaste", "Bienvenido", "Llegaste", "Qué", "fiesta", "Mamá", "Cafecito", "chancla", "Taquería", "Tiendita", "Casa de", "La Plaza", "tabla", "ficha", "esquinas", "fila", "columna"]
UNIT = r"""
const J = require(process.argv[1]), I = require(process.argv[2]);
const t = J.newTabla(), called = new Set(t), out = { n: J.CARDS.length, names: J.CARDS.map((c) => c.name), tabla: t.length, uniq: new Set(t).size, calls: J.CARDS.every((c) => c.call && c.call.length < 70) };
const win = (cells, calledSet) => J.check(t, new Set(cells), calledSet || called);
out.row = win([4, 5, 6, 7]); out.col = win([1, 5, 9, 13]); out.diag = win([3, 6, 9, 12]); out.corners = win([0, 3, 12, 15]); out.none = win([0, 1, 2, 5]);
out.uncalled = win([0, 1, 2, 3], new Set([t[0], t[1], t[2]]));
out.lines = J.LINES.length;
out.levels = I.LEVELS.map((l) => l.name);
out.same = JSON.stringify(I.buildLevel(3)) === JSON.stringify(I.buildLevel(3));
out.power = [1, 2, 3, 4, 5].map((n) => { const e = I.buildLevel(n); return [e.filter((x) => x.t === "cup").length, e.filter((x) => x.t === "chancla").length]; });
out.afterCheck = [1, 2, 3, 4, 5].every((n) => I.buildLevel(n).every((e) => !["agent", "cone", "suv", "crate"].includes(e.t) || I.CHECKS.every((c) => !c || e.x < c - 40 || e.x > c + 60)));
const fs = require("fs"), src = fs.readFileSync(process.argv[1], "utf8") + fs.readFileSync(process.argv[2], "utf8");
out.net = ["http:", "https:", "fetch(", "XMLHttpRequest", "import(", "sendBeacon", "WebSocket", "<a "].filter((w) => src.includes(w));
out.agents = [1, 2, 3, 4, 5].map((n) => I.buildLevel(n).filter((x) => x.t === "agent").length);
out.callsText = J.CARDS.map((c) => c.call);
out.signs = I.LEVELS.map((l) => l.sign); out.hints = I.LEVELS.map((l) => l.hint);
out.parts = J.voicePartsOf("¡Lotería! I told you today was your day, honey.");
out.parts2 = J.voicePartsOf("The Coffee. To get you through the morning chisme.");
console.log(JSON.stringify(out));
"""
def unit():
    print("== Node: Lotería Chismosa + Ice Ice Bebé logic")
    r = subprocess.run(["node", "-e", UNIT, os.path.join(HERE, "static", "juegos.js"), os.path.join(HERE, "static", "icebebe.js")], capture_output=True, text=True, timeout=60)
    if r.returncode: check(False, "node harness: " + r.stderr[-300:]); return
    o = json.loads(r.stdout)
    check(30 <= o["n"] <= 54 and len(set(o["names"])) == o["n"], f"{o['n']} original cards, all different")
    copied = [n for n in o["names"] if n.lower() in TRADITIONAL]
    check(not copied, f"no traditional lotería card names ({copied})")
    check(all(x in o["names"] for x in ["The Coffee", "The Best Friend", "The Rollers", "The Phone", "The Neighbor", "The Gossip", "The Flip-Flop", "The Sweet Bread", "The Soap Opera", "The Snow Cone", "The Mariachi", "The Party", "The Taco", "The Grandma", "The Tamale", "The Piñata", "The Gossip Queen"]), "the chisme cards are in the deck, in English (The Coffee … The Gossip Queen)")
    check(all(n.startswith("The ") for n in o["names"]), "every card name is English (\"The …\")")
    es = [w for w in SPANISH if any(w.lower() in t.lower().split() or (" " in w and w.lower() in t.lower()) for t in o["callsText"] + o["hints"] + o["names"])]
    check(not es and not any(ch in t for t in o["callsText"] for ch in "¡¿áéíóúñ"), f"Tía's call lines and the level hints are English ({es})")
    check(o["parts"] == [["Lotería", "es"], ["I told you today was your day, honey.", "en"]] and o["parts2"] == [["The Coffee. To get you through the morning chisme.", "en"]], f"speech: English, only \"Lotería\" in Spanish ({o['parts']})")
    check(o["calls"], "every card has a short call line")
    check(o["tabla"] == 16 and o["uniq"] == 16, "a tabla is 4×4 with 16 different cards")
    check(o["row"]["win"] and o["col"]["win"] and o["diag"]["win"] and o["corners"]["win"] and o["lines"] == 11, "wins: a row, a column, a diagonal, the 4 corners (11 lines)")
    check(not o["none"]["win"], "4 marks that aren't a line: no win")
    check(not o["uncalled"]["win"] and len(o["uncalled"]["early"]) == 1, "a line with a card Tía hasn't called doesn't count (caught as an early mark)")
    check(o["levels"] == ["Home Dehole", "The Taco Shop", "The Corner Store", "The Plaza", "Mom's House"] and o["signs"] == ["HOME DEHOLE", "TACO SHOP", "CORNER STORE", "THE PLAZA", "MOM'S HOUSE"], f"Ice Ice Bebé: 5 levels in English, ending at {o['levels']}")
    check(o["same"], "a level is the same course every time (so a checkpoint restarts it fairly)")
    check(all(c >= 1 and s >= 1 for c, s in o["power"]), f"every level has a ☕ coffee and a 🩴 flip-flop ({o['power']})")
    check(o["afterCheck"], "no hazards right at a checkpoint")
    check(not o["net"], f"the games' code has no URLs, links or network calls ({o['net']})")
    check(all(a >= 3 for a in o["agents"]), f"agents on every level ({o['agents']})")

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
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs, outside = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    watch = {"on": False}
    pg.on("request", lambda r: outside.append(r.url[:90]) if watch["on"] and r.resource_type != "image" and urlparse(r.url).hostname not in ("localhost", "127.0.0.1") else None)   # images = other tabs' map tiles/photos
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_timeout(1500)
    tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t => t.textContent.trim())")
    fit = await pg.evaluate("(() => { const t = document.querySelector('.tabs-inner'), j = document.querySelector('.tab[data-view=juegos]').getBoundingClientRect(); return t.scrollWidth <= t.clientWidth + 1 && j.right <= innerWidth; })()")
    check([t.split()[-1] for t in tabs] == ["News", "Sports", "Weather", "dieta?", "Juegitos", "Events"] and tabs[4] == "🎲 Juegitos", f"tab bar: News · Sports · Weather · ¿Cuál dieta? · 🎲 Juegitos · Events ({tabs})")
    check(fit, "all 6 tabs fit on an iPhone 13 (no sideways scroll)")
    check(await pg.evaluate("__chisme.view") == "juegos" and await pg.evaluate("__chisme.juegos.id") == "loteria", "#loteria opens Juegitos → Lotería Chismosa")
    games = await pg.evaluate("[...document.querySelectorAll('.game-pick b')].map(b => b.textContent)")
    check(games == ["Lotería Chismosa", "Ice Ice Bebé"], f"a list of games ({games})")
    watch["on"] = True
    check(await pg.evaluate("document.querySelector('.lot-tia').naturalWidth > 0"), "Tía Chismosa's avatar is there")
    check(await pg.evaluate("document.querySelectorAll('#lot-tabla .lot-cell').length") == 16, "a 4×4 tabla")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('#juegos').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, "juegos-tab.png"))
    # v39: everything in English (besides "Lotería")
    txt = await pg.evaluate("(() => { const j = document.querySelector('#view-juegos'); return [...j.querySelectorAll('#juegos, #game-stage')].map(e => e.innerText).join(' ') + ' ' + [...j.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' '); })()")
    es = [w for w in SPANISH if w.lower() in txt.lower().replace("lotería", "")]
    check(not es and "Start" in txt and "New board" in txt and "Voice" in txt and "Pull up a chair" in txt, f"Lotería's UI is English: ▶ Start · 🔀 New board · 🔊 Voice ({es})")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('#juegos').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(200)
    await until(pg, "(document.querySelector('#sync') || {}).dataset?.state !== 'ok'", 6); await pg.wait_for_timeout(400)   # the "Updated" pill gone
    await pg.screenshot(path=os.path.join(OUT, "juegos-english.png"))
    # --- Lotería
    await pg.click("#lot-claim"); check("play first" in await pg.text_content("#lot-line"), "¡Lotería! before starting: Tía says to start first (in English)")
    await pg.click("#lot-play"); await pg.wait_for_timeout(600)
    s = await st(pg)
    check(s["running"] and len(s["called"]) == 1 and await pg.evaluate("!!document.querySelector('#lot-card .lcard')"), "▶ Start: Tía calls a card (shown big in her bubble)")
    line = await pg.text_content("#lot-line"); called = await pg.evaluate("document.querySelector('#lot-card').innerText")
    check(await pg.text_content("#lot-play") == "⏸ Pause" and not any(ch in line for ch in "¡¿áéíóúñ"), f"the call line and buttons are English ({line!r}, {called.strip()!r})")
    f = await fs(pg)
    check(fs_ok(f) and "Lotería Chismosa" in f["badge"] and f["badgeMid"], f"v40 ▶ Start: Lotería goes full screen (fixed overlay {f['iw']}×{f['ih']}, tab bar + footer hidden, ✕ top right, 'Lotería Chismosa' badge top center) {f}")
    lay = await pg.evaluate("""(() => { const r = (s) => document.querySelector(s).getBoundingClientRect(); const t = r('#lot-tabla'), c = r('#lot-claim'), k = r('.lot-controls'), top = r('.lot-top');
      return { h: t.height, w: t.width, ok: top.bottom <= t.top + 1 && t.bottom <= c.top + 1 && c.bottom <= k.top + 1 && k.bottom <= innerHeight + 1 && t.left >= 0 && t.right <= innerWidth, fill: (k.bottom - top.top) / innerHeight }; })()""")
    check(lay["ok"] and lay["h"] >= 0.45 * f["ih"] and lay["fill"] > 0.85, f"…Tía + the called card, the board, ¡Lotería! and the controls fill the tall screen, nothing cut off (board {lay['w']:.0f}×{lay['h']:.0f}, {lay['fill']:.0%} of the height)")
    check(await pg.evaluate("__chisme.view") == "juegos" and (await st(pg))["fullscreen"], "…and the game says it's full screen")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('.lot-top').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(300)
    await until(pg, "(document.querySelector('#sync') || {}).dataset?.state !== 'ok'", 6); await pg.wait_for_timeout(400)   # the "Updated" pill gone
    await pg.screenshot(path=os.path.join(OUT, "loteria-english.png"))
    sp = await pg.evaluate("__spoken")
    check(len(sp) == 1 and sp[0]["lang"].startswith("en") and sp[0]["text"].startswith("The "), f"she says it out loud in English ({sp[:1]})")
    await pg.click("#lot-play"); n0 = len((await st(pg))["called"]); await pg.wait_for_timeout(5200)
    check(not (await st(pg))["running"] and len((await st(pg))["called"]) == n0, "⏸ Pause stops the calling")
    await pg.click("#lot-speed"); s = await st(pg)
    check(s["speed"] == "fast" and json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))["speed"] == "fast", "speed: Normal → Fast (remembered)")
    check(await pg.text_content("#lot-speed") == "🐇 Fast", "the speed button says 🐇 Fast")
    await pg.click("#lot-voice"); await pg.evaluate(G + ".callNext()")
    check(len(await pg.evaluate("__spoken")) == 1 and (await st(pg))["muted"], "🔇 Voice mutes her (no speech after)")
    s = await st(pg)
    un = next(i for i, c in enumerate(s["tabla"]) if c not in s["called"])
    await pg.click(f'.lot-cell[data-i="{un}"]')
    check(await pg.get_attribute(f'.lot-cell[data-i="{un}"]', "aria-pressed") == "true", "tap a card: a marker goes on it")
    await pg.click("#lot-claim"); check("hasn't been called" in await pg.text_content("#lot-line"), "¡Lotería! with a card that wasn't called: Tía catches it (in English)")
    await pg.click(f'.lot-cell[data-i="{un}"]')
    # call until row 1 (cells 0–3) is all called, then mark it and claim
    for _ in range(45):
        s = await st(pg)
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(250)
    s = await st(pg); stored = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))
    check(s["over"] and await pg.evaluate("document.querySelector('#view-juegos .game-stage').classList.contains('won') || !!document.querySelector('.won')"), "a full row + ¡Lotería!: a win")
    brag = await pg.text_content("#lot-line")
    check(await pg.evaluate("!!document.querySelector('.lot-confetti')") and brag.startswith("¡Lotería! I told you") and "(a row)" in brag, f"confetti + Tía brags in English ({brag[:60]!r})")
    check(await pg.text_content("#lot-play") == "▶ Play again", "after a win: ▶ Play again")
    check(stored["wins"] == 1 and stored["streak"] == 1 and stored["best"] == 1, f"wins / streak / best streak saved on the phone ({ {k: stored[k] for k in ('wins', 'streak', 'best')} })")
    check(await pg.evaluate("document.querySelectorAll('.lot-cell.win').length") == 4, "the winning line is highlighted")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('.lot-top').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(350)
    await pg.screenshot(path=os.path.join(OUT, "loteria-win.png"))
    await pg.click("#lot-new"); await pg.click("#lot-play"); await pg.wait_for_timeout(300); await pg.click("#lot-play"); await pg.click("#lot-new")
    stored = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))
    check(stored["streak"] == 0 and stored["best"] == 1, "🔀 New board mid-game ends the streak; the best streak stays")
    await pg.click("#lot-play"); await pg.wait_for_timeout(300)
    check((await st(pg))["running"] and (await fs(pg))["on"], "▶ Start again: calling, full screen")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(400)
    s = await st(pg); f = await fs(pg); n0 = len(s["called"])
    back = await pg.evaluate("(() => { const b = document.querySelector('.game-pick').getBoundingClientRect(); return b.top >= 0 && b.bottom <= innerHeight; })()")
    await pg.wait_for_timeout(3200)
    check(not s["running"] and not s["fullscreen"] and not f["on"] and f["tabs"] and f["foot"] and back and len((await st(pg))["called"]) == n0,
          f"✕: the calling stops, back to the Juegitos list, tab bar + footer back (running {s['running']}, fs {f['on']}, tabs {f['tabs']}, list in view {back})")
    # --- Ice Ice Bebé
    await pg.click('.game-pick[data-game="icebebe"]'); await to_stage(pg)
    s = await st(pg)
    check(s["mode"] == "title" and "Ice Ice Bebé" in s["overlay"], "Ice Ice Bebé: title screen")
    await pg.click('#ice-ov [data-act="start"]'); await pg.wait_for_timeout(700)
    s1 = await st(pg); await pg.wait_for_timeout(500); s2 = await st(pg)
    check(s2["mode"] == "run" and s2["x"] > s1["x"] + 20, f"he runs ({s1['x']:.0f} → {s2['x']:.0f})")
    f = await fs(pg)
    check(fs_ok(f) and f["badgeMid"] and "Ice Ice Bebé" in f["badge"] and await pg.evaluate("!!document.querySelector('.gfs-badge canvas.gfs-ice-cv')"), f"v40 ▶ Start: Ice Ice Bebé goes full screen (fixed overlay {f['iw']}×{f['ih']}, tab bar + footer hidden, ✕ top right, pixel 'ICE ICE BEBÉ' badge top center) {f}")
    cvr = await pg.evaluate("(() => { const r = document.querySelector('#ice-cv').getBoundingClientRect(), c = document.querySelector('#ice-cv'); return { w: r.width, h: r.height, cw: c.width, ch: c.height, top: r.top, bot: r.bottom }; })()")
    check(cvr["ch"] > cvr["cw"] * 1.4 and cvr["h"] >= 0.7 * f["ih"] and cvr["w"] >= 0.9 * f["iw"], f"…a tall portrait screen that fills the phone ({cvr['cw']}×{cvr['ch']} px shown at {cvr['w']:.0f}×{cvr['h']:.0f})")
    hud = await pg.evaluate("(() => { const g = document.querySelector('#ice-cv').getContext('2d'), px = (x, y) => [...g.getImageData(x, y, 1, 1).data].slice(0, 3).join(','); return [px(70, 1), px(40, 23), px(3, 3)]; })()")
    check(hud[0] == "20,23,38" and hud[1] == "255,61,139" and hud[2] == "255,61,139", f"…a HUD across the top of the canvas, right under the ✕ bar (level chip, score, progress, power-up slots) {hud}")
    await pg.locator("#ice-cv").dispatch_event("pointerdown"); await pg.wait_for_timeout(150)
    check(not (await st(pg))["ground"], "tap the game: he jumps")
    await pg.wait_for_timeout(900)
    await pg.keyboard.press("Space"); await pg.wait_for_timeout(120)
    check(not (await st(pg))["ground"], "Space: he jumps")
    s = await st(pg)
    check(s["fxMade"] > 5, f"particles: dust behind his boots and on landing, sparkles on the double jump / pickups ({s['fxMade']} so far)")
    await pg.wait_for_timeout(700)
    await pg.screenshot(path=os.path.join(OUT, "ice-ice-bebe-level1.png"))
    caught = await until(pg, G + ".state.mode === 'caught'", 20)
    s = await st(pg)
    check(caught and s["caughtMsg"] in ("¡Ay no!", "¡Fuera!", "¡Vámonos, amigo!") and "Try again" in s["overlay"], f"caught: big pixel {s['caughtMsg']!r} + Try again")
    await until(pg, G + ".state.mode === 'run'", 3)
    check((await st(pg))["x"] < 40, "…and back to the start")
    msgs = {s["caughtMsg"]}
    await pg.evaluate(G + ".warp(1, 820)"); await pg.wait_for_timeout(200)
    check((await st(pg))["ck"] == 1, "passing the 🚩 flag sets a checkpoint")
    await until(pg, G + ".state.mode === 'caught'", 25); msgs.add((await st(pg))["caughtMsg"]); await until(pg, G + ".state.mode === 'run'", 3)
    x = (await st(pg))["x"]
    check(795 < x < 830, f"caught after the checkpoint → back to the checkpoint (x {x:.0f})")
    ents = await pg.evaluate(G + ".ents()")
    for kind, key in (("cup", "boost"), ("chancla", "shield")):
        got = False
        await until(pg, G + ".state.boost === 0 && " + G + ".state.mode === 'run'", 8)
        for off in (12, 9, 15, 6, 18):
            await until(pg, G + ".state.mode === 'run'", 3)
            ex = next(e["x"] for e in await pg.evaluate(G + ".ents()") if e["t"] == kind) if any(e["t"] == kind for e in await pg.evaluate(G + ".ents()")) else None
            if ex is None: await pg.evaluate(G + ".warp(1, 10)"); await pg.evaluate("__chisme.juegos.game"); continue
            await pg.evaluate(f"{G}.warp(1, {ex - off})"); await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(450)
            if (await st(pg))[key] > 0: got = True; break
        check(got, f"{'☕ coffee → speed boost' if kind == 'cup' else '🩴 flip-flop → shield'} ({(await st(pg))['msg']!r})")
        if got: check((await st(pg))["msg"] == ("Coffee! Speed boost" if kind == "cup" else "Flip-flop! Shield on"), "…with an English pop-up")
        if kind == "chancla" and got:
            dizzy = await until(pg, "__chisme.juegos.game.ents().some(e => e.st === 'dizzy') || __chisme.juegos.game.state.mode === 'caught'", 25)
            s = await st(pg)
            check(dizzy and s["mode"] != "caught" and any(e["st"] == "dizzy" for e in await pg.evaluate(G + ".ents()")), "with the flip-flop, the next agent just gets dizzy (he isn't caught)")
    await pg.evaluate(f"{G}.warp(1, 2340)")
    await until(pg, G + ".state.mode === 'clear'", 6)
    await pg.wait_for_timeout(300); await pg.locator("#ice-cv").screenshot(path=os.path.join(OUT, "ice-ice-bebe-home-dehole.png"))
    s = await st(pg)
    check(s["mode"] == "clear" and "You made it to Home Dehole!" in s["overlay"] and s["levelMax"] == 2, f"level 1 cleared at Home Dehole ({s['overlay'][:40]!r})")
    await pg.click('#ice-ov [data-act="next"]'); await pg.wait_for_timeout(200)
    check((await st(pg))["level"] == 2 and (await st(pg))["mode"] == "run", "▶ on to level 2: The Taco Shop")
    await pg.click("#ice-pause"); s = await st(pg); await pg.wait_for_timeout(600)
    check(s["mode"] == "paused" and (await st(pg))["x"] == s["x"], "⏸ Pause freezes the game")
    await pg.click("#ice-pause")
    check((await st(pg))["mode"] == "run" and (await fs(pg))["on"], "▶ Resume: still full screen")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    s = await st(pg); f = await fs(pg)
    check(s["mode"] == "paused" and not f["on"] and f["tabs"] and f["foot"] and "Paused" in s["overlay"], f"✕: Ice Ice Bebé pauses and it's back to Juegitos (tab bar + footer back) ({s['mode']}, fs {f['on']})")
    await pg.click('#ice-ov [data-act="resume"]'); await pg.wait_for_timeout(200)
    check((await st(pg))["mode"] == "run" and (await fs(pg))["on"], "▶ Resume from the list: full screen again")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
    check((await st(pg))["mode"] == "paused" and not (await fs(pg))["on"], "Escape works like ✕ (paused, out of full screen)")
    await pg.click('#ice-ov [data-act="resume"]'); await pg.wait_for_timeout(150)
    await pg.click("#ice-sound")
    check((await st(pg))["muted"] and json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos-ice')"))["muted"], "🔇 Sound mutes the beeps (remembered)")
    await pg.evaluate(f"{G}.warp(5, 2330)")
    won = await until(pg, G + ".state.mode === 'win'", 6)
    await pg.wait_for_timeout(1300)
    s = await st(pg); ice = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos-ice')"))
    note = await pg.text_content("#ice-note")
    check(won and "Welcome home" in s["overlay"] and "Mom's house" in note and "What a party" in note, "level 5: home to Mom's House, the family party (in English)")
    txt = await pg.evaluate("(() => { const j = document.querySelector('#view-juegos'); return [...j.querySelectorAll('#juegos, #game-stage')].map(e => e.textContent).join(' ') + ' ' + [...j.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' '); })()")   # textContent: the rules are hidden while full screen
    es = [w for w in SPANISH if w.lower() in txt.lower().replace("lotería", "")]
    check(not es and "Coffee = speed boost" in txt and "Flip-flop = shield" in txt, f"Ice Ice Bebé's UI is English ({es})")
    check(ice["best"] >= s["score"] > 0 and ice["wins"] == 1 and ice["levelMax"] == 5, f"best score saved on the phone ({ice['best']})")
    check("Play again" in s["overlay"], "…with ▶ Play again right on the full-screen win screen")
    await pg.screenshot(path=os.path.join(OUT, "ice-ice-bebe-win.png"))
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    msgs_seen = set(msgs)
    check(msgs_seen <= {"¡Ay no!", "¡Fuera!", "¡Vámonos, amigo!"}, f"caught lines seen (kept in Spanish): {sorted(msgs_seen)}")
    check(await pg.evaluate("document.querySelectorAll('#game-stage a').length") == 0, "no links in the games")
    check(not outside, f"no outside requests while playing (besides other tabs' images) ({outside[:3]})")
    # a fresh Ice Ice Bebé (title screen), then News: Space there must not start the game
    await pg.click('.game-pick[data-game="loteria"]'); await pg.click('.game-pick[data-game="icebebe"]'); await pg.wait_for_timeout(200)
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
    ctx = await b.new_context(**dev, reduced_motion="reduce"); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page()
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    await pg.click("#lot-play"); await pg.click("#lot-play")
    for _ in range(45):
        s = await st(pg)
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(200)
    s = await st(pg)
    check(s["over"] and not await pg.evaluate("!!document.querySelector('.lot-confetti')"), f"reduce motion: a win without confetti (over {s['over']}, marks {s['marks']}, line {await pg.text_content('#lot-line')!r})")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="icebebe"]'); await pg.click('#ice-ov [data-act="start"]'); await pg.wait_for_timeout(300)
    await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(1200)
    s = await st(pg)
    check(not s["parallax"] and s["fxMade"] == 0 and s["fullscreen"], f"reduce motion: Ice Ice Bebé's background stays still (no parallax, shake, particles or confetti), still full screen (fx {s['fxMade']})")
    await b.close()

async def fullscreen_shots(p):
    print("\n== WebKit 390×844: full-screen screenshots")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 1   # screenshots exactly 390×844
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/#ice"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    await pg.click('#ice-ov [data-act="start"]'); await pg.wait_for_timeout(300)
    await pg.evaluate(G + ".warp(1, 470)"); await pg.wait_for_timeout(700); await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(260)
    f = await fs(pg); s = await st(pg)
    cvh = await pg.evaluate("document.querySelector('#ice-cv').getBoundingClientRect().height")
    check(fs_ok(f) and s["mode"] == "run" and s["H"] > 1.7 * s["W"] and cvh > 0.8 * f["ih"], f"390×844: Ice Ice Bebé mid-game, full screen (canvas {s['W']}×{s['H']}, {cvh:.0f} px tall on an {f['ih']} px screen)")
    await pg.screenshot(path=os.path.join(OUT, "icebebe-fullscreen.png"))
    await pg.evaluate(G + ".warp(2, 1100)"); await pg.wait_for_timeout(100)
    ax = next((e["x"] for e in await pg.evaluate(G + ".ents()") if e["t"] == "agent" and e["x"] > 1200), 1360)
    await pg.evaluate(f"{G}.warp(2, {ax - 110})"); await pg.wait_for_timeout(450); await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(180)   # an agent on screen
    s = await st(pg)
    check(s["level"] == 2 and (await fs(pg))["on"], f"390×844: level 2, The Taco Shop street ({s['mode']})")
    await pg.screenshot(path=os.path.join(OUT, "icebebe-level2.png"))
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="loteria"]'); await pg.wait_for_timeout(300)
    await pg.click("#lot-play"); await pg.wait_for_timeout(300)
    for _ in range(5): await pg.evaluate(G + ".callNext()")
    s = await st(pg)
    for i, c in enumerate(s["tabla"]):
        if c in s["called"]: await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.wait_for_timeout(400)
    check(fs_ok(await fs(pg)) and len(s["called"]) == 6, "390×844: Lotería Chismosa full screen, a few cards called and marked")
    await pg.screenshot(path=os.path.join(OUT, "loteria-fullscreen.png"))
    await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
    await pg.evaluate("() => window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
    tab = await pg.evaluate("(() => { const t = document.querySelector('.tab[data-view=juegos]'), r = t.getBoundingClientRect(), i = document.querySelector('.tabs-inner'); return { txt: t.textContent.trim(), fits: t.scrollWidth <= t.clientWidth + 1 && r.right <= innerWidth && i.scrollWidth <= i.clientWidth + 1 }; })()")
    check(tab["txt"] == "🎲 Juegitos" and tab["fits"], f"the tab says 🎲 Juegitos and fits the tab bar at 390 px ({tab})")
    check(not errs, f"no page errors ({errs[:3]})")
    await b.close()

async def offline(p):
    print("\n== Chromium: offline")
    b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    await ctx.add_init_script(INIT); pg = await ctx.new_page()
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=60000)
    await pg.wait_for_timeout(2500)
    await ctx.set_offline(True)
    await pg.evaluate("location.hash = '#ice'"); await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.view === 'juegos'", timeout=30000); await pg.wait_for_timeout(500)
    ok = await pg.evaluate("__chisme.juegos.id") == "icebebe"
    await pg.click('#ice-ov [data-act="start"]'); await pg.wait_for_timeout(800)
    s = await pg.evaluate(G + ".state")
    await pg.click(".gfs-x"); await pg.wait_for_timeout(200)
    await pg.click('.game-pick[data-game="loteria"]'); await pg.wait_for_timeout(200)
    check(ok and s["mode"] == "run" and await pg.evaluate("document.querySelectorAll('#lot-tabla .lot-cell').length") == 16, "offline: Juegitos opens (#ice), Ice Ice Bebé runs, Lotería deals a tabla")
    await b.close()

async def main():
    unit()
    async with async_playwright() as p:
        await webkit(p); await fullscreen_shots(p); await offline(p)
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
