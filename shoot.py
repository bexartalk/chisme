"""Headless check + screenshots. Usage: ./venv/bin/python shoot.py [url]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
CHROME = "/usr/bin/google-chrome"

CHECK_JS = """() => {
  const tiles = [...document.querySelectorAll('.radar-tiles img.leaflet-tile')];
  const visibleRadar = [...document.querySelectorAll('.radar-tiles')].filter(l => getComputedStyle(l).opacity > 0);
  const vis = visibleRadar.flatMap(l => [...l.querySelectorAll('img.leaflet-tile')]);
  const base = [...document.querySelectorAll('.leaflet-tile-pane > .leaflet-layer:first-child img.leaflet-tile')];
  return {
    radarFrames: window.__chisme.frames.length,
    radarTilesLoaded: tiles.filter(i => i.complete && i.naturalWidth > 0).length,
    radarTilesVisibleLoaded: vis.filter(i => i.complete && i.naturalWidth > 0).length,
    radarTileSample: vis[0] && vis[0].src,
    baseTilesLoaded: base.filter(i => i.complete && i.naturalWidth > 0).length,
    near: document.querySelectorAll('#near-list .story').length,
    city: document.querySelectorAll('#city-list .story').length,
    thumbs: [...document.querySelectorAll('.story img')].filter(i => i.complete && i.naturalWidth > 0).length,
    forecastDays: document.querySelectorAll('#forecast .day').length,
    currentTemp: document.querySelector('.now-temp')?.textContent,
    alerts: document.querySelectorAll('.alert').length,
    noAlertsMsg: !!document.querySelector('.no-alerts'),
    errors: [...document.querySelectorAll('.error')].map(e => e.textContent),
    bodyFont: getComputedStyle(document.body).fontSize,
    headlineFont: getComputedStyle(document.querySelector('.story h3') || document.body).fontSize,
  };
}"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        results = {}
        for name, vp, mobile in [("desktop", {"width": 1280, "height": 900}, False),
                                 ("phone", {"width": 390, "height": 844}, True)]:
            ctx = await b.new_context(viewport=vp, device_scale_factor=2 if mobile else 1,
                                      is_mobile=mobile, has_touch=mobile, timezone_id="America/Chicago")
            page = await ctx.new_page()
            logs = []
            page.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            page.on("requestfailed", lambda r: logs.append(f"requestfailed: {r.url[:120]} {r.failure}"))
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector("#city-list .story", timeout=60000)
            await page.wait_for_selector("#forecast .day", timeout=60000)
            # pause radar on latest frame so the screenshot is deterministic
            await page.click("#r-play") if await page.text_content("#r-play") != "► Play" else None
            await page.evaluate("document.querySelector('#r-slider').value = document.querySelector('#r-slider').max; document.querySelector('#r-slider').dispatchEvent(new Event('input'))")
            await page.wait_for_timeout(4000)
            res = await page.evaluate(CHECK_JS)
            res["console"] = logs[:15]
            results[name] = res
            await page.evaluate("window.scrollTo(0,0)")
            await page.evaluate("""() => Promise.all([...document.images].map(i => { i.loading = 'eager'; return i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 8000); }); }))""")
            await page.wait_for_timeout(800)
            res["thumbsAfterEager"] = await page.evaluate("[...document.querySelectorAll('.story img')].filter(i => i.complete && i.naturalWidth > 0).length")
            await page.screenshot(path=str(OUT / f"{name}-top.png"))
            await page.screenshot(path=str(OUT / f"{name}-full.png"), full_page=True)
            await page.locator("#radar-sec").scroll_into_view_if_needed()
            await page.wait_for_timeout(1500)
            await page.locator("#radar-sec").screenshot(path=str(OUT / f"{name}-radar.png"))
            await page.locator("#near").screenshot(path=str(OUT / f"{name}-near.png"))
            await ctx.close()
        await b.close()
        print(json.dumps(results, indent=2))

asyncio.run(main())
