"""No yellow anywhere in the app (v36 News → v37 app-wide), in light AND dark mode. No yellow, gold, amber or cream
highlights or backgrounds, text, borders, glows, focus rings, pills or toasts. The Fiesta palette (turquoise, pink,
orange on neutral backgrounds) replaces them. Weather severity can be orange or red, not yellow; the radar legend and
the RainViewer tiles (recolored on a canvas) go blue → orange → red → pink.

Covers every tab (News, Sports, Weather, ¿Cuál dieta?, Juegos, Events), Settings, the Tía chat sheet (her picture
itself is excluded), the "Updated" status pill in every state, the "New chisme" pill, the offline banner, the focus
ring, the radar legend and tiles, Lotería (a win, with its winning-row highlight) and Ice Ice Bebé (DOM overlays + canvas
pixels on the title, level 1, caught, level clear, levels 2–4 and the win). WebKit, iPhone 13, against the local server.
Screenshots, light | dark side by side: no-yellow-news.png, no-yellow-loteria.png, no-yellow-icebebe.png."""
import asyncio, io, os, sys
from playwright.async_api import async_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "screenshots"); BASE = os.environ.get("BASE", "http://localhost:8211")
FAILS = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: FAILS.append(what)

# yellow = hue 38–70° (yellow/gold/amber), or 25–38° when very light (cream) or very dark (amber-brown); orange (~30°,
# mid lightness) is Fiesta and fine. Shared by the DOM scan and the canvas scan.
YELLOW_JS = r"""const yellow = ([r, g, b, a]) => { if (a != null && a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.05) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= 0.85 || l <= 0.2)); };"""

SCAN = r"""(root) => { """ + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const roots = [...document.querySelectorAll(root)];
  const els = roots.flatMap((r) => [r, ...r.querySelectorAll('*')]).filter((e) => e.getClientRects().length && !['IMG', 'CANVAS', 'VIDEO', 'IFRAME', 'PICTURE', 'SOURCE'].includes(e.tagName) && !e.closest('.leaflet-tile-pane'));
  const bad = [];
  for (const e of els) {
    const cs = getComputedStyle(e), what = (e.id ? '#' + e.id : '') + ([...e.classList].length ? '.' + [...e.classList].join('.') : '') + ' <' + e.tagName.toLowerCase() + '>';
    const props = { background: cs.backgroundColor, gradient: cs.backgroundImage, text: cs.color, glow: cs.boxShadow, 'text-shadow': cs.textShadow,
      border: [cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor, cs.borderLeftColor].filter((c, i) => parseFloat([cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth][i]) > 0).join(' '),
      outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 ? cs.outlineColor : '' };
    for (const [k, v] of Object.entries(props)) if (rgb(v).some(yellow)) bad.push(`${what} ${k} ${String(v).slice(0, 70)}`);
  }
  return { n: els.length, bad: [...new Set(bad)].slice(0, 10) };
}"""

# canvas pixels (Ice Ice Bebé): how many yellow pixels, and a few examples
CANVAS = r"""(sel) => { """ + YELLOW_JS + r"""
  const c = document.querySelector(sel); if (!c) return null; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let n = 0; const ex = new Set();
  for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 200 && yellow([d[i], d[i + 1], d[i + 2]])) { n++; if (ex.size < 4) ex.add('#' + [d[i], d[i + 1], d[i + 2]].map((v) => v.toString(16).padStart(2, '0')).join('')); }
  return { n, ex: [...ex], px: d.length / 4 };
}"""

G = "__chisme.juegos.game"
async def until(pg, js, secs):
    for _ in range(int(secs * 10)):
        if await pg.evaluate(js): return True
        await pg.wait_for_timeout(100)
    return False

async def scan(pg, root, label):
    r = await pg.evaluate(SCAN, root)
    check(r["n"] > 0 and not r["bad"], f"{label}: no yellow ({r['n']} elements) {r['bad']}")

async def shot(pg): return Image.open(io.BytesIO(await pg.screenshot()))

async def run_theme(b, dev, theme, shots):
    print(f"\n== {theme} mode")
    ctx = await b.new_context(**dev, color_scheme=theme)
    await ctx.add_init_script(f"localStorage.setItem('chisme-theme', '{theme}'); try {{ window.speechSynthesis && (speechSynthesis.speak = () => {{}}); }} catch (e) {{}}")
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)
    await pg.wait_for_timeout(1500)
    check(await pg.evaluate("document.documentElement.dataset.theme") == theme, f"{theme} theme on")
    # --- News (+ the New chisme pill, the offline banner, the "Updated" pill in every state)
    await pg.evaluate("document.getElementById('news-pill').hidden = false")
    await scan(pg, "#view-news, #news-pill, .topbar, #tabs", "News, header, tabs, New chisme pill")
    near = await pg.evaluate("(() => { const s = getComputedStyle(document.querySelector('#near-list .story.near')); return [s.backgroundColor, s.borderLeftColor]; })()")
    check(near[1] == "rgb(0, 201, 205)", f"Near You stories: a subtle turquoise edge ({near})")
    await pg.evaluate("document.getElementById('news-pill').hidden = true")
    await pg.evaluate("(() => { const o = document.getElementById('offline-banner'); o.textContent = \"You're offline. Showing the chisme saved on this phone.\"; o.hidden = false; })()")
    await scan(pg, "#offline-banner", "offline banner")
    await pg.evaluate("document.getElementById('offline-banner').hidden = true")
    for state in ("busy", "slow", "failed", "done"):
        await pg.evaluate(f"(() => {{ const s = document.getElementById('sync'); s.hidden = false; s.dataset.state = '{state}'; document.getElementById('sync-msg').textContent = 'Updated 3:01 AM'; document.getElementById('sync-retry').hidden = '{state}' !== 'failed'; }})()")
        await scan(pg, "#sync", f"status pill ({state})")
    await pg.evaluate("document.getElementById('sync').hidden = true")
    # focus ring (keyboard)
    await pg.keyboard.press("Tab"); await pg.keyboard.press("Tab")
    ring = await pg.evaluate("(() => { const e = document.activeElement, s = getComputedStyle(e); return [e.id || e.className, s.outlineStyle, s.outlineColor]; })()")
    check(ring[1] != "none" and ring[2] in ("rgb(239, 66, 111)", "rgb(255, 111, 147)"), f"keyboard focus ring is pink ({ring})")
    await pg.evaluate("document.activeElement && document.activeElement.blur()")
    await pg.evaluate("() => { const s = document.querySelector('#near-list .story'); window.scrollTo(0, s.getBoundingClientRect().top + scrollY - 90); }"); await pg.wait_for_timeout(4500)
    shots["news"].append(await shot(pg))
    # --- the other tabs
    for v, root in [("sports", "#view-sports"), ("weather", "#view-weather"), ("antojos", "#view-antojos"), ("events", "#view-events"), ("juegos", "#view-juegos")]:
        await pg.evaluate(f"__chisme.goView('{v}', {{ instant: true }})"); await pg.wait_for_timeout(2500 if v in ("sports", "weather", "events") else 1200)
        await scan(pg, root, f"{v} tab")
        if v == "weather":
            leg = await pg.evaluate("getComputedStyle(document.querySelector('.radar-legend .bar')).backgroundImage")
            check("255, 238, 0" not in leg and "255, 128, 0" in leg, "radar legend: blue → orange → red → pink (no yellow)")
            m = await pg.evaluate("[__chisme.radarColor(255, 238, 0), __chisme.radarColor(255, 170, 0), __chisme.radarColor(0, 163, 224)]")
            check(m[0] == [255, 129, 0] and m[1] == [255, 101, 0] and m[2] is None, f"radar tiles: yellow → orange, amber → deep orange, blues untouched ({m})")
            await until(pg, "document.querySelectorAll('.radar-tiles canvas.leaflet-tile-loaded').length > 0", 15)
            t = await pg.evaluate("""(() => { const cs = [...document.querySelectorAll('.radar-tiles canvas.leaflet-tile-loaded')]; let y = 0, rain = 0;
              for (const c of cs) { try { const d = c.getContext('2d').getImageData(0, 0, 256, 256).data; for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 0) { rain++; const r = d[i], g = d[i + 1], b = d[i + 2];
                if (r > 200 && g > 180 && b < 90) y++; } } catch (e) { return { tainted: true }; } } return { tiles: cs.length, rain, y }; })()""")
            check(t.get("tiles", 0) > 0 and not t.get("tainted") and t["y"] == 0, f"radar tiles are recolored canvases, no yellow pixels ({t})")
    # --- Settings
    await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(400)
    await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
    await scan(pg, "#settings", "Settings")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    # --- the Tía chat sheet (her picture is left as is)
    await pg.click("#tia-btn"); await pg.wait_for_timeout(1200)
    await scan(pg, "#tia", "Tía chat sheet (UI; her art excluded)")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    # --- Lotería: a win
    await pg.evaluate("location.hash = '#loteria'"); await pg.wait_for_timeout(300)
    await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await until(pg, "__chisme.juegos && __chisme.juegos.id === 'loteria'", 10)
    if await pg.evaluate("__chisme.juegos.id") != "loteria": await pg.click('.game-pick[data-game="loteria"]')
    await pg.click("#lot-play"); await pg.wait_for_timeout(200); await pg.click("#lot-play")
    for _ in range(45):
        s = await pg.evaluate(G + ".state")
        if all(c in s["called"] for c in s["tabla"][:4]): break
        await pg.evaluate(G + ".callNext()")
    for i in range(4): await pg.click(f'.lot-cell[data-i="{i}"]')
    await pg.click("#lot-claim"); await pg.wait_for_timeout(300)
    check(await pg.evaluate("document.querySelectorAll('.lot-cell.win').length") == 4, "Lotería: a win, the winning row highlighted")
    win = await pg.evaluate("(() => { const s = getComputedStyle(document.querySelector('.lot-cell.win .lcard')); return [s.borderTopColor, s.boxShadow]; })()")
    check(win[0] == "rgb(0, 201, 205)", f"…in turquoise (+ pink ring), not gold ({win[0]})")
    await scan(pg, "#view-juegos", "Lotería win (cards, ¡Lotería! button, bubble)")
    await pg.evaluate("() => window.scrollTo(0, document.querySelector('.lot-top').getBoundingClientRect().top + scrollY - 70)"); await pg.wait_for_timeout(2600)
    shots["loteria"].append(await shot(pg))
    # --- Ice Ice Bebé: overlays (DOM) + canvas pixels in every state
    await pg.click('.game-pick[data-game="icebebe"]'); await pg.wait_for_timeout(600)
    await pg.evaluate("document.querySelector('#game-stage').scrollIntoView({ block: 'start' })"); await pg.wait_for_timeout(300)
    async def ice(label):
        c = await pg.evaluate(CANVAS, "#ice-cv")
        check(c and c["n"] == 0, f"Ice Ice Bebé {label}: no yellow pixels ({c['n'] if c else None} {c['ex'] if c else ''})")
        await scan(pg, "#game-stage", f"Ice Ice Bebé {label}: overlay/UI")
    await ice("title")
    await pg.click('#ice-ov [data-act="start"]'); await pg.wait_for_timeout(900)
    await pg.evaluate(G + ".warp(1, 300)"); await pg.wait_for_timeout(300); await ice("level 1 (HUD, road, agents)")
    await until(pg, G + ".state.mode === 'caught'", 20); await pg.wait_for_timeout(150); await ice("caught (big pixel text)")
    shots["icebebe"].append(await shot(pg))
    await until(pg, G + ".state.mode === 'run'", 3)
    await pg.evaluate(G + ".warp(1, 2340)"); await until(pg, G + ".state.mode === 'clear'", 6); await pg.wait_for_timeout(300); await ice("level 1 clear: Home Dehole + level title")
    for lv in (2, 3, 4):
        await pg.evaluate(f"{G}.warp({lv}, 400)"); await pg.wait_for_timeout(400)
        if await pg.evaluate(G + ".state.mode") in ("run", "caught", "clear"): await ice(f"level {lv}")
        await pg.evaluate(f"{G}.warp({lv}, 2340)"); await until(pg, G + ".state.mode === 'clear'", 6); await pg.wait_for_timeout(300); await ice(f"level {lv} clear")
    await pg.evaluate(G + ".warp(5, 2330)"); await until(pg, G + ".state.mode === 'win'", 6); await pg.wait_for_timeout(1200); await ice("win (family party, confetti)")
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close()

async def main():
    shots = {"news": [], "loteria": [], "icebebe": []}
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        for theme in ("light", "dark"): await run_theme(b, dev, theme, shots)
        await b.close()
    for k, (a, d) in shots.items():
        w, h = a.size; out = Image.new("RGB", (w * 2 + 30, h + 20), "#888")
        out.paste(a, (10, 10)); out.paste(d, (w + 20, 10)); out.save(os.path.join(OUT, f"no-yellow-{k}.png"))
    print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED")); sys.exit(1 if FAILS else 0)

asyncio.run(main())
