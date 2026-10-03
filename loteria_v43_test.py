"""v43 Chismería redesign: laid out like a real tabla app, with our own vintage card art.

1. Files: 54 finished card pictures (static/loteria/cards/01–54.webp, drawn by tools/make_loteria_cards.py) in bright flat
   vintage-print colors with a white border (v49.5: the classic-deck look, solid pastel backgrounds, bold black outlines, a cream border); golden yellow only in the art of the 5 cards the classic decks have it in
   (El Diablito, La Estrella, El Alacrán, El Sol, La Corona; the user asked for it), none anywhere else; #26 is El Chocolate,
   #38 El Apache is a dignified Apache man with a bow (v49.5b; was the huaraches); the service worker precaches them. The app's UI stays yellow-free.
2. WebKit 390×844 full screen: the teal top bar holds the title badge, the "Pick your tabla" picker, the "x / 16" bean count and ✕;
   under it a strip with the called card (picture, Spanish verse, count) + ▶/⏸ and ¡Buenas!; a 4×4 tabla of big cards filling the
   width; big Limpiar + Nueva tabla buttons at the bottom; nothing scrolls. A called card tapped → a big pinto bean covers it (the
   card dimmed) and the count goes up; an uncalled card shakes; Limpiar takes every bean off; Nueva tabla deals a random new mix;
   the picker's presets deal their 16 cards and are remembered. No yellow in the game's colors. Win + ¡Buenas! still work.
3. WebKit 320×640: the same, shrunk (no scrolling, 44 px buttons, labels not clipped).
Screenshots (390×844): loteria-v43.png (mid-game, beans on called cards, the called card showing), loteria-v43-cards.png (the art),
loteria-v43-picker.png, loteria-v43-320.png."""
import asyncio, colorsys, glob, json, os, re
from PIL import Image
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://127.0.0.1:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-notif','{\"n\":1}'); }"
SPEECH = """(() => { window.__spoken = []; const fake = { speak(u) { __spoken.push({ text: u.text, lang: u.lang }); setTimeout(() => u.onend && u.onend(), 60); }, cancel() {}, getVoices() { return [{ lang: 'es-MX', name: 'T' }]; }, addEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {} window.SpeechSynthesisUtterance = function (t) { this.text = t; }; })()"""
G = "__chisme.juegos.game"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

def yellowish(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 45 / 360 <= h <= 68 / 360 and s >= 0.45 and v >= 0.55

def goldish(r, g, b):   # golden yellow / amber-gold (the classic decks' gold)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 38 / 360 <= h <= 68 / 360 and s >= 0.6 and v >= 0.7

def files():
    print("== the card pictures")
    d = os.path.join(HERE, "static", "loteria", "cards"); fs = sorted(glob.glob(os.path.join(d, "*.webp")))
    names = [os.path.basename(f) for f in fs]
    check(names == [f"{i:02d}.webp" for i in range(1, 55)], f"54 card pictures, 01–54.webp ({len(fs)})")
    sizes = [os.path.getsize(f) for f in fs]
    check(all(3000 < z < 80000 for z in sizes), f"small files ({sum(sizes) // 1024} KB total, biggest {max(sizes) // 1024} KB)")
    GOLD = {2, 35, 40, 46, 47}
    worst = 0; gold = {}; dims = set(); sat = []; border = []; ink = []
    for i, f in enumerate(fs, 1):
        im = Image.open(f).convert("RGB"); dims.add(im.size); sm = im.resize((100, 150))
        px = list(sm.get_flattened_data() if hasattr(sm, "get_flattened_data") else sm.getdata())
        if i in GOLD: gold[i] = sum(goldish(*p) for p in px) / 15000
        else: worst = max(worst, sum(yellowish(*p) for p in px) / 15000)
        field = [p for k, p in enumerate(px) if 8 <= k % 100 <= 92 and 8 <= k // 100 <= 120]
        sat.append(sum(colorsys.rgb_to_hsv(*(c / 255 for c in p))[1] for p in field) / len(field))
        ink.append(sum(max(p) < 60 for p in field) / len(field))
        border.append(min(im.getpixel((im.width // 2, 6)) + im.getpixel((6, im.height // 2))))   # the white border, top and side
    check(len(dims) == 1 and abs(list(dims)[0][1] / list(dims)[0][0] - 1.5) < 0.01, f"all the same 2:3 portrait size ({dims})")
    check(worst < 0.002, f"no yellow in the other 49 cards' art (worst {worst:.3%} yellow-ish pixels, anti-aliasing)")
    check(all(v > 0.03 for v in gold.values()), f"golden yellow in El Diablito, La Estrella, El Alacrán, El Sol, La Corona ({ {k: f'{v:.0%}' for k, v in gold.items()} })")
    check(sum(sat) / len(sat) > 0.22 and min(sat) > 0.12, f"v49.5 classic-deck colors: solid pastel backgrounds + flat print art, not grey or muddy (mean saturation {sum(sat) / len(sat):.2f}, lowest {min(sat):.2f})")
    check(min(ink) > 0.02, f"v49.5 bold black outlines on every card (least ink {min(ink):.1%} of the picture)")
    check(min(border) >= 215, f"a clean cream/white card border on every card (darkest border pixel {min(border)})")
    sw = open(os.path.join(HERE, "static", "sw.js")).read()
    check("/static/loteria/cards/" in sw and re.search(r'VERSION = "chisme-v\d+(?:\.\d+)?"', sw), "the service worker precaches the pictures (offline tabla)")
    gen = open(os.path.join(HERE, "tools", "make_loteria_cards.py")).read()
    check("loteria_cards.js" in gen and "webp" in gen, "tools/make_loteria_cards.py re-renders them from our own drawings in loteria_cards.js")

COLORS_JS = """(() => { const out = []; const scan = (root) => root.querySelectorAll('*').forEach((e) => { const cs = getComputedStyle(e);
    for (const k of ['color', 'backgroundColor', 'borderTopColor', 'borderBottomColor', 'outlineColor']) { const m = cs[k].match(/rgba?\\(([\\d.]+), ([\\d.]+), ([\\d.]+)(?:, ([\\d.]+))?/); if (m && (m[4] === undefined || +m[4] > 0.05)) out.push([+m[1], +m[2], +m[3], e.id || e.className.toString().slice(0, 30), k]); } });
  scan(document.querySelector('#game-stage')); return out; })()"""
LAY_JS = """(() => { const r = (s) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null; }, st = document.querySelector('#game-stage');
  const bar = r('.gfs-bar'), now = r('.lot-now'), t = r('#lot-tabla'), act = r('.lot-actions'), card = r('#lot-card .lcard'), cell = r('#lot-tabla .lcard');
  const over = [...document.querySelectorAll('.gfs-bar button, .gfs-bar .lot-marked, .lot-now-btns button, .lot-actions button, #lot-pick-t')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.id || e.className);
  const small = [...document.querySelectorAll('.gfs-bar button, .lot-now-btns button, .lot-actions button')].filter(e => e.getBoundingClientRect().height < 40).map(e => e.id || e.className);
  return { bar: [bar.top, bar.bottom], now: [now.top, now.bottom], t: [t.left, t.top, t.width, t.height], act: [act.top, act.bottom], card: card ? card.width : 0, cell: cell.width, cellH: cell.height,
    inBar: ['.gfs-badge', '#lot-pick', '#lot-marked', '.gfs-x'].every(s => { const e = r(s); return e && e.top >= bar.top - 1 && e.bottom <= bar.bottom + 1; }),
    order: bar.bottom <= now.top + 1 && now.bottom <= t.top + 1 && t.bottom <= act.top + 1 && act.bottom <= innerHeight + 1 && t.left >= 0 && t.right <= innerWidth + 0.5,
    scroll: st.scrollHeight > st.clientHeight + 1 || st.scrollWidth > st.clientWidth + 1, over, small, vh: innerHeight, vw: innerWidth,
    loaded: [...document.querySelectorAll('#lot-tabla .lc-img')].every(i => i.complete && i.naturalWidth >= 200) }; })()"""

async def page(b, p, w, h):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": w, "height": h}; dev["device_scale_factor"] = 1
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(SPEECH)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(800)
    return ctx, pg, errs

async def st(pg): return await pg.evaluate(G + ".state")
async def beans(pg): return await pg.evaluate("[...document.querySelectorAll('.lot-cell.marked .frijol')].filter(b => getComputedStyle(b).opacity === '1').length")

async def big(p):
    print("\n== WebKit 390×844 full screen")
    b = await p.webkit.launch(); ctx, pg, errs = await page(b, p, 390, 844)
    await pg.click("#lot-play"); await pg.wait_for_timeout(500); await pg.click("#lot-play")   # paused: the called card stays for the checks
    lay = await pg.evaluate(LAY_JS)
    check(await pg.evaluate("(await_ => document.documentElement.classList.contains('game-fs'))()") and lay["inBar"], "▶ Start goes full screen; the teal bar holds the title badge, the tabla picker, the bean count and ✕")
    bg = await pg.evaluate("[getComputedStyle(document.querySelector('.gfs-bar')).backgroundColor, getComputedStyle(document.querySelector('#game-stage')).backgroundColor]")
    check(bg[0] != bg[1], f"teal bar over a warm cream page ({bg})")
    check(lay["order"] and not lay["scroll"] and lay["loaded"], f"bar → called-card strip → tabla → Limpiar / Nueva tabla, all on screen, no scrolling ({lay['bar']} {lay['now']} {lay['t']} {lay['act']})")
    check(lay["t"][2] >= 0.94 * 390 and lay["t"][3] >= 0.6 * 844 and lay["cellH"] >= 130, f"big cards: the tabla is {lay['t'][2]:.0f}×{lay['t'][3]:.0f} (full width, {lay['t'][3] / 844:.0%} of the height), each card {lay['cell']:.0f}×{lay['cellH']:.0f}")
    check(0 < lay["card"] < lay["cell"] and not lay["over"] and not lay["small"], f"the called card sits in the strip ({lay['card']:.0f} px), nothing clipped {lay['over']}, buttons ≥ 40 px {lay['small']}")
    s = await st(pg); first = s["called"][0]
    strip = await pg.evaluate("[document.querySelector('#lot-card .lc-img').getAttribute('src'), document.querySelector('#lot-line').textContent, document.querySelector('#lot-count').textContent, document.querySelector('#lot-play').textContent]")
    verse = await pg.evaluate(f"ChismeLoteriaCards.CARDS[{first - 1}].verse")
    check(strip[0].endswith(f"/{first:02d}.webp") and strip[1] == verse and "called" in strip[2] and "Resume" in strip[3], f"the strip: the called card's picture, its Spanish verse, the count, ▶ Resume ({strip})")
    # the tabla picker
    await pg.click("#lot-pick"); await pg.wait_for_timeout(300)
    opts = await pg.evaluate("[...document.querySelectorAll('#lot-picks [data-pick]')].map(b => [b.dataset.pick, b.textContent.trim().slice(0, 24)])")
    check(not await pg.evaluate("document.querySelector('#lot-sheet').hidden") and len(opts) >= 5 and opts[0][0] == "random", f"'Pick your tabla' opens: 🔀 Random mix + the ready-made tablas ({[o[0] for o in opts]})")
    await pg.screenshot(path=os.path.join(OUT, "loteria-v43-picker.png"))
    await pg.click('#lot-picks [data-pick="fiesta"]'); await pg.wait_for_timeout(300)
    s = await st(pg); want = await pg.evaluate("__chisme.juegos.game && ChismeLoteriaCards.PRESETS.find(p => p.id === 'fiesta').cards")
    saved = json.loads(await pg.evaluate("localStorage.getItem('chisme-juegos')"))
    check(await pg.evaluate("document.querySelector('#lot-sheet').hidden") and s["tabla"] == want and s["pick"] == "fiesta" and saved.get("pick") == "fiesta" and await pg.text_content("#lot-pick-t") == "La Fiesta",
          f"picking La Fiesta closes the sheet and deals its 16 cards (remembered; the bar says La Fiesta)")
    await pg.click("#lot-new"); await pg.wait_for_timeout(300); s2 = await st(pg)
    await pg.click("#lot-new"); await pg.wait_for_timeout(300); s3 = await st(pg)
    check(s2["pick"] == "random" and len(set(s2["tabla"])) == 16 and s2["tabla"] != want and s3["tabla"] != s2["tabla"] and "Random" in await pg.text_content("#lot-pick-t"),
          "Nueva tabla: a random new mix of 16 every tap (the picker says 🔀 Random)")
    # play: beans cover called cards, uncalled cards shake, the count goes up
    await pg.click("#lot-play"); await pg.wait_for_timeout(400); await pg.click("#lot-play")
    for _ in range(40):
        s = await st(pg)
        if sum(c in s["called"] for c in s["tabla"]) >= 5: break
        await pg.evaluate(G + ".callNext()")
    hits = [i for i, c in enumerate(s["tabla"]) if c in s["called"]]; un = next(i for i, c in enumerate(s["tabla"]) if c not in s["called"])
    await pg.click(f'.lot-cell[data-i="{un}"]')
    check(await pg.evaluate(f"document.querySelector('.lot-cell[data-i=\"{un}\"]').classList.contains('nope')") and not (await st(pg))["marks"], "an uncalled card shakes, no bean")
    for i in hits[:5]: await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.wait_for_timeout(750)
    cov = await pg.evaluate(f"""(() => {{ const c = document.querySelector('.lot-cell[data-i="{hits[0]}"]'), b = c.querySelector('.frijol'), img = c.querySelector('.lc-img'), br = b.getBoundingClientRect(), cr = c.getBoundingClientRect();
      return {{ w: br.width / cr.width, dx: Math.abs((br.left + br.right) / 2 - (cr.left + cr.right) / 2) / cr.width, dy: Math.abs((br.top + br.bottom) / 2 - (cr.top + cr.bottom) / 2) / cr.height, filt: getComputedStyle(img).filter }}; }})()""")
    n = min(5, len(hits))
    check(await beans(pg) == n and await pg.text_content("#lot-marked") == f"{n} / 16", f"tapping {n} called cards drops {n} beans; the bar says {await pg.text_content('#lot-marked')}")
    check(cov["w"] >= 0.7 and cov["dx"] < 0.12 and cov["dy"] < 0.12 and "brightness" in cov["filt"], f"a big bean covers the card, centered, the card dimmed ({cov})")
    await pg.wait_for_timeout(300)
    await pg.screenshot(path=os.path.join(OUT, "loteria-v43.png"))
    lay = await pg.evaluate(LAY_JS); check(not lay["scroll"] and lay["order"], "mid-game: still no scrolling")
    # colors: no yellow anywhere in the game
    ys = [c for c in await pg.evaluate(COLORS_JS) if yellowish(*c[:3])]
    check(not ys, f"no yellow in the game's colors ({ys[:4]})")
    # Limpiar
    await pg.click("#lot-clear"); await pg.wait_for_timeout(300)
    check(await beans(pg) == 0 and not (await st(pg))["marks"] and await pg.text_content("#lot-marked") == "0 / 16" and (await st(pg))["called"], "Limpiar takes every bean off (the calls stay); 0 / 16")
    # a win still works
    for _ in range(60):
        s = await st(pg)
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(300); s = await st(pg)
    check(s["over"] and s["voice"]["last"] == "loteria" and (await pg.text_content("#lot-line")).startswith("¡Buenas!"), "a full row + ¡Buenas!: a win, and she shouts '¡Buenas!' (recorded clip)")
    check(await pg.evaluate("document.querySelectorAll('.lot-cell.win').length") == 4, "the winning line is highlighted")
    # the art sample
    await pg.evaluate("""() => { const L = ChismeLoteriaCards, d = document.createElement('div'); d.id = 'art-sheet';
      d.style.cssText = 'position:fixed;inset:0;z-index:9000;background:#f7e8df;padding:8px;box-sizing:border-box;display:grid;grid-template-columns:repeat(4,1fr);gap:6px;align-content:start;overflow:hidden';
      const pick = [1, 2, 3, 4, 6, 11, 14, 17, 23, 26, 29, 35, 38, 42, 46, 51];
      d.innerHTML = '<p style="grid-column:1/-1;margin:2px 0 2px;color:#0f6d73;font-weight:900;text-align:center;font-size:15px">Our own vintage Lotería art · 16 of 54 cards</p>' + pick.map(n => { const c = L.CARDS[n - 1]; return `<img src="${c.img}" alt="${c.name}" style="width:100%;aspect-ratio:2/3;display:block;border-radius:6px;box-shadow:0 2px 0 #1d1612">`; }).join('');
      document.body.appendChild(d); }""")
    await pg.wait_for_function("[...document.querySelectorAll('#art-sheet img')].every(i => i.complete && i.naturalWidth)", timeout=10000); await pg.wait_for_timeout(200)
    fit = await pg.evaluate("(() => { const l = [...document.querySelectorAll('#art-sheet img')]; return l.length === 16 && l[15].getBoundingClientRect().bottom <= innerHeight + 1; })()")
    check(fit, "16 of the new cards (incl. #26 El Chocolate, #38 El Apache) fit one 390×844 screen")
    await pg.screenshot(path=os.path.join(OUT, "loteria-v43-cards.png"))
    await pg.evaluate("document.querySelector('#art-sheet').remove()")
    names = await pg.evaluate("[ChismeLoteriaCards.CARDS[25].name, ChismeLoteriaCards.CARDS[37].name, ChismeLoteriaCards.CARDS[37].svg.length > 300]")
    check(names[0] == "El Chocolate" and names[2], f"#26 is {names[0]}; #38 ({names[1]}) has its own drawing (v49.5b: a dignified Apache man with a bow)")
    check(not errs, f"no page errors ({errs[:3]})")
    await b.close()

async def small(p):
    print("\n== WebKit 320×640 full screen")
    b = await p.webkit.launch(); ctx, pg, errs = await page(b, p, 320, 640)
    await pg.click("#lot-play"); await pg.wait_for_timeout(400); await pg.click("#lot-play")
    for _ in range(8): await pg.evaluate(G + ".callNext()")
    s = await st(pg)
    for i in [i for i, c in enumerate(s["tabla"]) if c in s["called"]][:3]: await pg.click(f'.lot-cell[data-i="{i}"]')
    worst = await pg.evaluate("""(() => { const C = ChismeLoteriaCards, l = document.querySelector('#lot-line'); let min = 1e9;
      for (const c of C.CARDS) { l.textContent = c.verse; min = Math.min(min, document.querySelector('#lot-tabla').getBoundingClientRect().height); } return min; })()""")
    await pg.evaluate(f"document.querySelector('#lot-line').textContent = ChismeLoteriaCards.CARDS[{s['called'][-1] - 1}].verse")
    await pg.wait_for_timeout(600); lay = await pg.evaluate(LAY_JS)
    check(lay["inBar"] and lay["order"] and not lay["scroll"] and lay["loaded"], f"everything fits, no scrolling ({lay['bar']} {lay['now']} {lay['t']} {lay['act']})")
    check(lay["t"][2] >= 0.85 * 320 and worst >= 0.6 * 640, f"the tabla shrinks gracefully: {lay['t'][2]:.0f}×{lay['t'][3]:.0f}, ≥ {worst:.0f} px tall with any verse")
    check(not lay["over"] and not lay["small"], f"labels not clipped {lay['over']}, buttons ≥ 40 px {lay['small']}")
    await pg.screenshot(path=os.path.join(OUT, "loteria-v43-320.png"))
    check(not errs, f"no page errors ({errs[:3]})")
    await b.close()

async def main():
    files()
    async with async_playwright() as p:
        await big(p); await small(p)
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)

asyncio.run(main())
