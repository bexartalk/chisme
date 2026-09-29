"""Phone (390x844): Events category chips filter the list; swiping the chip row doesn't switch views;
Food chip shows real food reviews (local creators + food desks) with thumbnails and outbound links; works offline.
Usage: ./venv/bin/python events_food_test.py [url]"""
import asyncio, json, sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
STATE_JS = """() => { const vis = [...document.querySelectorAll('#events-list .ev')];
  return { view: window.__chisme.view, cat: window.__chisme.evCat,
    pressed: [...document.querySelectorAll('#ev-chips .chip')].map(b => b.dataset.cat + '=' + b.getAttribute('aria-pressed') + ' ' + b.innerText.replace(/\\s+/g,' ').trim()),
    shown: vis.length, titles: vis.slice(0, 6).map(a => a.querySelector('h3').innerText),
    intro: document.querySelector('#events-intro').textContent, foodHidden: document.querySelector('#food-block').hidden,
    empty: document.querySelector('#events-list > p')?.textContent || null }; }"""


async def drag(cdp, x0, x1, y, steps=14):
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / steps, "y": y}]})
        await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


async def main():
    rep, logs = {}, []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                  timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        page = await ctx.new_page()
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        page.on("console", lambda m: logs.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        await page.goto(URL + "#events", wait_until="domcontentloaded")
        await page.evaluate("localStorage.removeItem('chisme-events-cat')")
        await page.wait_for_function("() => window.__chisme && window.__chisme.eventsReady && document.querySelectorAll('#events-list .ev').length", timeout=120000)
        await page.wait_for_timeout(1500)
        cdp = await ctx.new_cdp_session(page)
        rep["all"] = await page.evaluate(STATE_JS)
        data = await page.evaluate("fetch('/api/events?lat=29.35&lon=-98.56').then(r => r.json())")
        ev = data["events"]
        # chip row: horizontal swipe on it must not switch views
        await page.evaluate("document.querySelector('#ev-chips').scrollIntoView({block: 'center', behavior: 'instant'})")
        await page.wait_for_timeout(300)
        cb = await page.locator("#ev-chips").bounding_box()
        await drag(cdp, 360, 60, cb["y"] + cb["height"] / 2)
        await page.wait_for_timeout(700)
        rep["chip_swipe"] = await page.evaluate("() => ({ view: window.__chisme.view, chipScrollLeft: document.querySelector('#ev-chips').scrollLeft })")
        await page.evaluate("document.querySelector('#ev-chips').scrollLeft = 0")
        for cat in ("concerts", "festivals", "free-classes"):
            await page.tap(f"#ev-chips .chip[data-cat='{cat}']")
            await page.wait_for_timeout(500)
            st = await page.evaluate(STATE_JS)
            want = [e for e in ev if (cat == "free-classes" and "classes" in e["tags"] and e["free"]) or (cat != "free-classes" and cat in e["tags"])]
            st["expected"] = len(want)
            rep[cat] = st
            if cat == "concerts":
                await page.evaluate("document.querySelector('#events').scrollIntoView({block: 'start', behavior: 'instant'})")
                await page.evaluate("window.scrollBy(0, -8)")
                await page.wait_for_timeout(1500)
                await page.screenshot(path=str(OUT / "events-categories.png"))
        # Food
        await page.tap("#ev-chips .chip[data-cat='food']")
        await page.wait_for_function("() => window.__chisme.foodReady && document.querySelectorAll('#food-creators .fr').length", timeout=60000)
        await page.wait_for_timeout(500)
        rep["food_state"] = await page.evaluate(STATE_JS)
        await page.evaluate("document.querySelector('#food-block').scrollIntoView({block: 'start', behavior: 'instant'})")
        await page.evaluate("window.scrollBy(0, -130)")
        await page.wait_for_timeout(2500)
        rep["food"] = await page.evaluate("""() => { const items = [...document.querySelectorAll('#food-block .fr')];
            const imgs = [...document.querySelectorAll('#food-block .fr-thumb img')];
            return { creators: document.querySelectorAll('#food-creators .fr').length, outlets: document.querySelectorAll('#food-outlets .fr').length,
                     imgs: imgs.length, imgsLoaded: imgs.filter(i => i.complete && i.naturalWidth > 0).length,
                     placeholders: document.querySelectorAll('#food-block .fr-thumb .ev-ph').length,
                     hosts: [...new Set([...document.querySelectorAll('#food-block .fr h4 a')].map(a => new URL(a.href).host))],
                     sample: items.slice(0, 4).map(i => i.querySelector('h4').innerText + ' — ' + i.querySelector('.fr-by').innerText),
                     sources: [...document.querySelectorAll('#food-sources li')].map(l => l.innerText) }; }""")
        await page.screenshot(path=str(OUT / "food-reviews.png"))
        sb = await page.locator("#food-creators").bounding_box()
        await drag(cdp, 360, 40, sb["y"] + sb["height"] / 2)
        await page.wait_for_timeout(800)
        rep["food_strip_swipe"] = await page.evaluate("() => ({ view: window.__chisme.view, stripScrollLeft: Math.round(document.querySelector('#food-creators').scrollLeft) })")
        # food links must come from the API (never invented)
        food = await page.evaluate("fetch('/api/food').then(r => r.json())")
        api_urls = {i["url"] for i in food["items"]}
        dom_urls = await page.evaluate("[...document.querySelectorAll('#food-block .fr h4 a')].map(a => a.href)")
        rep["food_links_not_from_api"] = [u for u in dom_urls if u not in api_urls]
        # persistence + offline
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("() => window.__chisme && window.__chisme.eventsReady && window.__chisme.foodReady", timeout=120000)
        rep["persisted_cat"] = await page.evaluate("localStorage.getItem('chisme-events-cat')")
        await page.wait_for_timeout(1500)
        await b.close()
    rep["console"] = logs
    # offline: fresh persistent profile (no CDP session attached, so navigator.onLine follows the emulation)
    import tempfile
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path="/usr/bin/google-chrome", args=["--no-sandbox"],
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, timezone_id="America/Chicago",
            geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        pg = ctx.pages[0]
        await pg.goto(URL + "#food", wait_until="networkidle")
        await pg.reload(wait_until="networkidle")  # now controlled by the service worker, which saves the API responses
        await pg.wait_for_function("() => window.__chisme.eventsReady && window.__chisme.foodReady", timeout=120000)
        await pg.wait_for_timeout(1500)
        await ctx.set_offline(True)
        failed, errs = [], []
        pg.on("requestfailed", lambda r: failed.append(r.url[:100]))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.reload(wait_until="domcontentloaded")
        await pg.wait_for_function("() => window.__chisme && window.__chisme.eventsReady && window.__chisme.foodReady", timeout=60000)
        await pg.wait_for_timeout(3000)
        rep["offline"] = await pg.evaluate("""() => ({ onLine: navigator.onLine, cat: window.__chisme.evCat,
            creators: document.querySelectorAll('#food-creators .fr').length, outlets: document.querySelectorAll('#food-outlets .fr').length,
            events: document.querySelectorAll('#events-list .ev').length, thumbPlaceholders: document.querySelectorAll('#food-block .fr-thumb .ev-ph').length,
            imgs: document.querySelectorAll('#food-block img').length, banner: !document.querySelector('#offline-banner').hidden,
            stamp: document.querySelector('#events-updated').textContent })""")
        await pg.screenshot(path=str(OUT / "food-reviews-offline.png"))
        rep["offline_failed"], rep["offline_console"] = failed, errs
        await ctx.close()
    print(json.dumps(rep, indent=1, ensure_ascii=False))

asyncio.run(main())
