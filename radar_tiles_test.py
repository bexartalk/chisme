"""v49.12: RainViewer radar tiles keep the console clean on Weather.

Cause of the console errors seen on big screens: every radar frame stayed on the map at opacity 0, so each pan/zoom
re-requested tiles for all ~13 frames at once (150+ tiles per move on a desktop-size map). RainViewer's free tiles are
rate limited per IP (300 burst / 500 a minute in its headers), and its "Too Many Requests" replies carry no
Access-Control-Allow-Origin, so Chrome logged "blocked by CORS policy: No 'Access-Control-Allow-Origin' header" per tile
(the tiles are crossOrigin=anonymous because they're redrawn on a canvas). Now only the frame on show + the next one stay
on the map. Tiles are served locally here (with ACAO, like RainViewer's 200s) so the test never touches their limit.

Checks, at 1440x1000 (desktop) and 390x844 (phone), Chromium:
  * after a full play cycle at most 2 radar layers are on the map
  * zooming out asks for tiles of at most 2 frames
  * no console errors / failed requests on Weather; tiles still drawn (canvas recolour works with CORS)
"""
import asyncio, base64, re, sys
sys.path.insert(0, "/workspace/chisme")
from playwright.async_api import async_playwright
from popup_quiet import QUIET

BASE = "http://localhost:8211"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
FRAME = re.compile(r"/v2/radar/([^/]+)/")
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

async def run(p, w, h):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={"width": w, "height": h})
    await ctx.add_init_script("try{localStorage.setItem('chisme-location-setup','1')}catch(e){}")
    await ctx.add_init_script(QUIET)
    reqs, errs = [], []
    async def tile(route):
        reqs.append(route.request.url)
        await route.fulfill(status=200, body=PNG, headers={"content-type": "image/png", "access-control-allow-origin": "*", "cache-control": "no-store"})
    await ctx.route(re.compile(r"https://tilecache\.rainviewer\.com/.*"), tile)
    pg = await ctx.new_page()
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
    pg.on("requestfailed", lambda r: errs.append("failed " + r.url[-70:]) if "rainviewer" in r.url or "/api/radar" in r.url else None)
    await pg.goto(BASE + "/#weather")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
    await pg.wait_for_selector("#map .radar-tiles", state="attached", timeout=30000)
    await pg.evaluate("document.querySelector('#map').scrollIntoView()")
    n = await pg.evaluate("() => +document.querySelector('#r-slider').max + 1")
    for _ in range(n):  # step through every frame (what Play does)
        await pg.click("#r-next"); await pg.wait_for_timeout(250)
    await pg.wait_for_timeout(1500)
    on = await pg.evaluate("() => document.querySelectorAll('#map .radar-tiles').length")
    check(on <= 2, f"{w}px: {on} radar layers on the map after stepping through {n} frames (≤2)")
    before = len(reqs)
    await pg.click("#map .leaflet-control-zoom-out"); await pg.wait_for_timeout(1200)
    await pg.click("#map .leaflet-control-zoom-out"); await pg.wait_for_timeout(2500)
    zf = {FRAME.search(u).group(1) for u in reqs[before:] if FRAME.search(u)}
    check(0 < len(zf) <= 2, f"{w}px: zooming out twice requested {len(reqs) - before} tiles from {len(zf)} frame(s) (≤2)")
    drawn = await pg.evaluate("() => [...document.querySelectorAll('#map .radar-tiles canvas, #map .radar-tiles img')].length")
    check(drawn > 0, f"{w}px: radar tiles drawn ({drawn})")
    check(not errs, f"{w}px: console clean on Weather" + (f" — {errs[:3]}" if errs else ""))
    await b.close()

async def main():
    async with async_playwright() as p:
        await run(p, 1440, 1000)
        await run(p, 390, 844)
    print("ALL PASS" if not fails else f"{len(fails)} FAIL")
    sys.exit(1 if fails else 0)
asyncio.run(main())
