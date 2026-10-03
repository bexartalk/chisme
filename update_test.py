"""Phone (390x844) checks for the views/swipe/sticky-nav/story-links/events update.
Usage: ./venv/bin/python update_test.py [url]"""
import asyncio, json, sys, tempfile, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
GEO = {"latitude": 29.35, "longitude": -98.56}   # South Side San Antonio
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
             timezone_id="America/Chicago", geolocation=GEO, permissions=["geolocation"])


async def swipe(cdp, x0, x1, y, steps=12, ms=14):
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / steps, "y": y + k * 0.6}]})
        await asyncio.sleep(ms / 1000)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


async def vdrag(cdp, x, y0, dy, dx=0, steps=20):
    """Real finger drag (dispatchTouchEvent); synthesizeScrollGesture is a no-op in headless Chrome here."""
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + dx * k / steps, "y": y0 + dy * k / steps}]})
        await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def api(path):
    with urllib.request.urlopen(URL.rstrip("/") + path, timeout=120) as r:
        return json.loads(r.read())


async def main():
    rep, logs = {}, []
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="chisme-upd-"),
            executable_path="/usr/bin/google-chrome", args=["--no-sandbox"], **PHONE)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        page.on("console", lambda m: logs.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_function("() => window.__chisme && window.__chisme.ready && /^(Using your location|Showing): /.test(document.querySelector('#set-loc-now').textContent)", timeout=120000)
        await page.wait_for_timeout(1500)
        cdp = await ctx.new_cdp_session(page)

        # 1. news first on open
        rep["1_open"] = await page.evaluate("""() => ({ view: window.__chisme.view, label: document.querySelector('#set-loc-now').textContent,
            greeting: document.querySelector('#greet-hi').textContent, greetSub: document.querySelector('#greet-sub').textContent,
            newsVisible: document.querySelector('#view-news').getBoundingClientRect().height > 100,
            weatherHidden: document.querySelector('#view-weather').getBoundingClientRect().height === 0,
            near: document.querySelectorAll('#near-list .story').length, more: document.querySelectorAll('#city-list .story').length,
            firstCardTop: Math.round(document.querySelector('#near').getBoundingClientRect().top) })""")
        await page.screenshot(path=str(OUT / "update-news.png"))

        # 2. sticky nav after scrolling (touch scroll gesture)
        for _ in range(4):
            await vdrag(cdp, 195, 780, -500)
            await page.wait_for_timeout(250)
        await page.wait_for_timeout(600)
        rep["2_sticky"] = await page.evaluate("""() => { const r = document.querySelector('#tabs').getBoundingClientRect();
            const t0 = document.querySelector('#tabs .tab').getBoundingClientRect(), hit = document.elementFromPoint(t0.left + t0.width / 2, t0.top + t0.height / 2);   // v40: 2 rows of tabs on phones
            return { scrollY: Math.round(scrollY), tabsTop: Math.round(r.top), tabsH: Math.round(r.height), tabHit: !!(hit && hit.closest('.tab')),
                     headerOnScreen: document.querySelector('.topbar').getBoundingClientRect().bottom > 0, view: window.__chisme.view }; }""")
        await page.screenshot(path=str(OUT / "update-sticky-nav.png"))

        # 3. story links are real (every href is in the /api/news payload)
        news = api("/api/news?lat=29.350&lon=-98.560")
        real = set()
        for sec in ("near", "more", "metro_other"):
            for it in news.get(sec, []):
                real.add(it["link"]); real.add(it["search_url"]); real.update(r["link"] for r in it.get("related", []))
        links = await page.evaluate("""() => [...document.querySelectorAll('.story')].map(s => ({
            head: s.querySelector('h3 a').href, read: s.querySelector('.dig a.btnlink.primary')?.href,
            search: [...s.querySelectorAll('.dig a.btnlink')].map(a => a.href).find(h => h.includes('news.google.com/search')),
            related: [...s.querySelectorAll('.related a')].map(a => a.href) }))""")
        allh = [h for l in links for h in [l["read"], l["search"], *l["related"]] if h]
        rep["3_links"] = {"stories": len(links), "with_read": sum(1 for l in links if l["read"] and l["read"] == l["head"]),
                          "with_search": sum(1 for l in links if l["search"]), "with_related": sum(1 for l in links if l["related"]),
                          "hrefs_checked": len(allh), "hrefs_not_from_feeds": [h for h in allh if h not in real][:5]}
        # screenshot a story that has related coverage
        idx = await page.evaluate("() => [...document.querySelectorAll('#view-news .story')].findIndex(s => s.querySelector('.related'))")
        st = page.locator("#view-news .story").nth(max(0, idx))
        await st.scroll_into_view_if_needed()
        await page.evaluate("window.scrollBy(0, -80)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(OUT / "update-story-links.png"))

        # 4. swipe news -> sports (finger on a story); then the Weather tab
        y_before = await page.evaluate("scrollY")
        await swipe(cdp, 330, 60, 500)
        await page.wait_for_timeout(700)
        rep["4_swipe_to_sports"] = await page.evaluate("""() => ({ view: window.__chisme.view,
            ariaCurrent: document.querySelector('.tab[aria-current=page]').textContent.trim() })""")
        await page.click(".tab[data-view=weather]")
        await page.wait_for_timeout(700)
        rep["4b_weather_tab"] = await page.evaluate("""() => ({ view: window.__chisme.view, scrollY: Math.round(scrollY),
            weatherTop: Math.round(document.querySelector('#view-weather').getBoundingClientRect().top),
            tabsTop: Math.round(document.querySelector('#tabs').getBoundingClientRect().top),
            current: document.querySelector('.now-temp')?.textContent, blurb: document.querySelector('#wx-blurb').textContent,
            ariaCurrent: document.querySelector('.tab[aria-current=page]').textContent.trim() })""")
        await page.screenshot(path=str(OUT / "update-weather.png"))
        # vertical scrolling inside weather still scrolls (no view change)
        y0 = await page.evaluate("scrollY")
        await vdrag(cdp, 195, 760, -450, dx=40)   # slightly diagonal, mostly vertical
        await page.wait_for_timeout(700)
        rep["5_vertical_scroll"] = {"moved_px": round(await page.evaluate("scrollY") - y0), "view": await page.evaluate("window.__chisme.view")}
        # radar map: a horizontal drag pans the map and does NOT change the view
        await page.evaluate("document.querySelector('#map').scrollIntoView({block: 'center'})")
        await page.wait_for_timeout(500)
        box = await page.locator("#map").bounding_box()
        c0 = await page.evaluate("(() => { const c = window.__chisme.map.getCenter(); return [c.lat, c.lng]; })()")
        await swipe(cdp, box["x"] + box["width"] - 40, box["x"] + 40, box["y"] + box["height"] / 2)
        await page.wait_for_timeout(700)
        c1 = await page.evaluate("(() => { const c = window.__chisme.map.getCenter(); return [c.lat, c.lng]; })()")
        rep["6_map_pan"] = {"view": await page.evaluate("window.__chisme.view"), "map_center_moved_deg": round(abs(c1[1] - c0[1]), 4)}
        await page.evaluate("window.__chisme.map.setView([window.__chisme.loc.lat, window.__chisme.loc.lon], 8)")
        # swipe back (weather -> Sports, the tab before Weather)
        await page.evaluate("window.scrollTo({top: document.querySelector('#weather').getBoundingClientRect().top + scrollY - 90, behavior: 'instant'})")
        await swipe(cdp, 60, 330, 420)
        await page.wait_for_timeout(700)
        rep["7_swipe_back"] = {"view": await page.evaluate("window.__chisme.view"), "scrollY": round(await page.evaluate("scrollY")),
                               "news_scroll_before_swipe": round(y_before)}
        # a short/slow sideways wiggle snaps back (no switch)
        await swipe(cdp, 200, 160, 500, steps=10, ms=40)
        await page.wait_for_timeout(600)
        rep["8_small_wiggle"] = await page.evaluate("window.__chisme.view")

        # 9. events via tab
        await page.click("#tabs [data-view='chisme']"); await page.click(".view.active .mq-chip[data-go='events']")
        await page.wait_for_function("() => window.__chisme.eventsReady && document.querySelectorAll('#events-list .ev').length > 0", timeout=120000)
        # wait for background price/venue lookups to land (the page re-polls)
        for _ in range(8):
            ev = api("/api/events?lat=29.350&lon=-98.560")
            if not ev.get("pending"):
                break
            await page.wait_for_timeout(15000)
        await page.evaluate("() => {}")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        await page.click("#tabs [data-view='chisme']"); await page.click(".view.active .mq-chip[data-go='events']")  # tab on same view = no-op
        await page.evaluate("() => new Promise(r => setTimeout(r, 200))")
        # reload the list so the screenshot shows enriched data
        await page.evaluate("() => { window.__chisme.goView('events'); }")
        await page.wait_for_timeout(500)
        real_ev = set()
        for e in ev["events"] + ev["ongoing"]:
            real_ev.add(e["url"]); real_ev.update(a["url"] for a in e.get("also", []))
            if e.get("website"): real_ev.add(e["website"])
        for k in range(12):  # scroll through the first cards so lazy photos load
            await page.evaluate(f"document.querySelectorAll('#events-list .ev')[{k}]?.scrollIntoView({{block: 'center'}})")
            await page.wait_for_timeout(300)
        await page.wait_for_timeout(2500)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        rep["9_events"] = await page.evaluate("""(real) => { const cards = [...document.querySelectorAll('#events-list .ev')];
            const ev = cards.map(c => ({ title: c.querySelector('h3').textContent, when: c.querySelector('.ev-line span:nth-child(2)').textContent,
              photo: !!c.querySelector('.ev-media > img'), photoLoaded: !!c.querySelector('.ev-media > img') && c.querySelector('.ev-media > img').naturalWidth > 0,
              placeholder: !!c.querySelector('.ev-ph'), venue: c.querySelector('.ev-venue .txt').textContent.slice(0, 60),
              minimap: !!c.querySelector('.minimap'), price: c.querySelector('.price').textContent, wx: c.querySelector('.ev-wx').textContent.slice(0, 90),
              href: c.querySelector('h3 a').href }));
            return { view: window.__chisme.view, cards: cards.length, dayHeaders: document.querySelectorAll('.ev-day').length,
              intro: document.querySelector('#events-intro').textContent, withPhoto: ev.filter(e => e.photo).length,
              photosLoadedFirst12: ev.slice(0, 12).filter(e => e.photoLoaded).length, placeholders: ev.filter(e => e.placeholder).length,
              withMinimap: ev.filter(e => e.minimap).length,
              free: ev.filter(e => /FREE/.test(e.price)).length, priced: ev.filter(e => /\\$|Admission/.test(e.price)).length,
              checkPrice: ev.filter(e => /Check price/.test(e.price)).length,
              wxForecast: ev.filter(e => !/not available|unavailable/.test(e.wx)).length, wxNotYet: ev.filter(e => /not available yet/.test(e.wx)).length,
              ongoing: document.querySelectorAll('#ongoing-list .ev').length,
              hrefsNotFromApi: ev.map(e => e.href).filter(h => !real.includes(h) && !real.includes(decodeURI(h))).slice(0, 5), sample: ev.slice(0, 6) }; }""", list(real_ev))
        await page.screenshot(path=str(OUT / "update-events.png"))
        await page.evaluate("""() => { const c = document.querySelectorAll('#events-list .ev')[1];
            window.scrollTo({ top: c.getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 8, behavior: 'instant' }); }""")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(OUT / "update-event-card.png"))
        # swipe events -> Juegitos, the tab before Events (right swipe)
        await swipe(cdp, 60, 330, 500)
        await page.wait_for_timeout(700)
        rep["10_swipe_events_to_juegos"] = await page.evaluate("window.__chisme.view")

        # 11. offline: reload with the network off (service worker + saved API copies)
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=30000)
        await page.wait_for_function("() => window.__chisme.ready && window.__chisme.eventsReady", timeout=120000)
        await page.wait_for_timeout(1500)
        await ctx.set_offline(True)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_selector("#near-list .story", timeout=30000)
        await page.wait_for_timeout(3000)
        rep["11_offline"] = await page.evaluate("""() => ({ view: window.__chisme.view, near: document.querySelectorAll('#near-list .story').length,
            forecastDays: document.querySelectorAll('#forecast .day').length, events: document.querySelectorAll('#events-list .ev').length,
            banner: document.querySelector('#offline-banner').hidden ? null : document.querySelector('#offline-banner').textContent,
            eventsStamp: document.querySelector('#events-updated').textContent })""")
        await page.screenshot(path=str(OUT / "update-offline.png"))
        await page.click("#tabs [data-view='chisme']"); await page.click(".view.active .mq-chip[data-go='events']")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT / "update-offline-events.png"))
        await ctx.set_offline(False)
        await ctx.close()
    # offline image/tile failures are expected; report everything else
    rep["console"] = [l for l in logs if "ERR_INTERNET_DISCONNECTED" not in l and "Failed to load resource" not in l][:20]
    rep["console_offline_resource_errors"] = sum(1 for l in logs if "ERR_INTERNET_DISCONNECTED" in l or "Failed to load resource" in l)
    print(json.dumps(rep, indent=1, ensure_ascii=False))

asyncio.run(main())
