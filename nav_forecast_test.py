"""Phone (390x844): fixed nav visible after scrolling far down in News, Weather and Events;
7-day forecast strip scrolls sideways without switching views; tapping a day shows details.
Usage: ./venv/bin/python nav_forecast_test.py [url]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
NAV_JS = """() => { const r = document.querySelector('#tabs').getBoundingClientRect();
  const hits = [60, 150, 240, 330].map(x => document.elementFromPoint(x, r.top + r.height / 2)?.closest('.tab')?.textContent.trim() || null);
  const hdr = document.querySelector('.topbar').getBoundingClientRect();
  return { view: window.__chisme.view, scrollY: Math.round(scrollY), maxScroll: document.documentElement.scrollHeight - innerHeight,
           navTop: Math.round(r.top), navBottom: Math.round(r.bottom), position: getComputedStyle(document.querySelector('#tabs')).position,
           tabsHit: hits, headerTop: Math.round(hdr.top) }; }"""


async def drag(cdp, x0, x1, y, steps=14):
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / steps, "y": y}]})
        await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


async def vscroll(cdp, times):
    for _ in range(times):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 200, "y": 780}]})
        for k in range(1, 21):
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 200, "y": 780 - k * 30}]})
            await asyncio.sleep(0.012)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        await asyncio.sleep(0.15)


async def main():
    rep, logs = {}, []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                  timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        page = await ctx.new_page()
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        page.on("console", lambda m: logs.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_function("() => window.__chisme && window.__chisme.ready && /^(Using your location|Showing): /.test(document.querySelector('#set-loc-now').textContent)", timeout=120000)
        await page.wait_for_timeout(1200)
        cdp = await ctx.new_cdp_session(page)
        rep["top_of_page"] = await page.evaluate(NAV_JS)   # header starts below the nav, nothing hidden
        # News: scroll far down with real finger drags
        await vscroll(cdp, 14)
        await page.wait_for_timeout(800)
        rep["news_far_down"] = await page.evaluate(NAV_JS)
        await page.screenshot(path=str(OUT / "fixed-nav-news.png"))
        # Weather: tap the nav while deep in News, then scroll to the bottom of Weather
        await page.tap(".tab[data-view=weather]:not([data-scroll])")
        await page.wait_for_timeout(700)
        await vscroll(cdp, 8)
        await page.wait_for_timeout(800)
        rep["weather_far_down"] = await page.evaluate(NAV_JS)
        await page.screenshot(path=str(OUT / "fixed-nav-weather.png"))
        # Events
        await page.tap(".tab[data-view=events]")
        await page.wait_for_function("() => window.__chisme.eventsReady && document.querySelectorAll('#events-list .ev').length", timeout=120000)
        await page.wait_for_timeout(800)
        await vscroll(cdp, 25)
        await page.wait_for_timeout(800)
        rep["events_far_down"] = await page.evaluate(NAV_JS)
        await page.screenshot(path=str(OUT / "fixed-nav-events.png"))

        # Forecast strip
        await page.tap(".tab[data-view=weather]:not([data-scroll])")
        await page.wait_for_timeout(700)
        await page.evaluate("document.querySelector('#forecast-sec').scrollIntoView({block: 'center', behavior: 'instant'})")
        await page.wait_for_timeout(400)
        fb = await page.locator("#forecast").bounding_box()
        rep["strip"] = await page.evaluate("""() => { const f = document.querySelector('#forecast'); const cards = [...f.querySelectorAll('.day')];
            return { cards: cards.length, display: getComputedStyle(f).display, snap: getComputedStyle(f).scrollSnapType,
                     overflowX: getComputedStyle(f).overflowX, scrollWidth: f.scrollWidth, clientWidth: f.clientWidth, cardH: Math.round(cards[0].getBoundingClientRect().height),
                     sample: cards.slice(0, 3).map(c => c.innerText.replace(/\\n/g, ' | ')) }; }""")
        await page.screenshot(path=str(OUT / "forecast-strip.png"))
        before = await page.evaluate("document.querySelector('#forecast').scrollLeft")
        await drag(cdp, fb["x"] + fb["width"] - 20, fb["x"] + 30, fb["y"] + fb["height"] / 2)
        await page.wait_for_timeout(900)
        rep["strip_swipe"] = {"scrollLeft_before": before, "scrollLeft_after": await page.evaluate("document.querySelector('#forecast').scrollLeft"),
                              "view_after": await page.evaluate("window.__chisme.view")}
        await page.evaluate("document.querySelector('#forecast').scrollLeft = 0")
        await page.wait_for_timeout(300)
        await page.tap("#forecast .day:nth-child(2)")
        await page.wait_for_timeout(400)
        rep["tap_day"] = await page.evaluate("""() => ({ expanded: [...document.querySelectorAll('#forecast .day')].map(c => c.getAttribute('aria-expanded')),
            detailShown: !document.querySelector('#fc-detail').hidden, detail: document.querySelector('#fc-detail').innerText.slice(0, 160),
            view: window.__chisme.view })""")
        await page.evaluate("document.querySelector('#forecast-sec').scrollIntoView({block: 'center', behavior: 'instant'})")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(OUT / "forecast-strip-expanded.png"))
        await page.tap("#forecast .day:nth-child(2)")
        await page.wait_for_timeout(300)
        rep["tap_again_collapses"] = await page.evaluate("document.querySelector('#fc-detail').hidden")
        # a swipe on the Weather page outside the strip still switches views
        await page.evaluate("window.scrollTo({top: document.querySelector('#weather').getBoundingClientRect().top + scrollY - 80, behavior: 'instant'})")
        await drag(cdp, 330, 60, 500)
        await page.wait_for_timeout(700)
        rep["swipe_outside_strip"] = await page.evaluate("window.__chisme.view")
        await b.close()
    rep["console"] = logs
    print(json.dumps(rep, indent=1, ensure_ascii=False))

asyncio.run(main())
