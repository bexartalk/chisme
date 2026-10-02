"""Change location anywhere in the U.S. (WebKit, iPhone 13), with GPS allowed at a San Antonio position:
the typed place must stick (the v22/v23 bug: the GPS watch switched straight back to San Antonio), and the
whole app must follow: header skyline, News outlets, Weather (NWS point), Events sources, ¿Cuál dieta?, Sports.
Screens: location-houston.png, location-miami.png, location-austin.png (+ extras in /tmp/wk)
Usage: ./venv/bin/python location_city_test.py [url]"""
import asyncio, json, os, re, sys
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs("/tmp/wk", exist_ok=True)
fails = []
def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: fails.append(msg)

SA_OUTLETS = re.compile(r"KSAT|KENS|News 4 San Antonio|San Antonio Report|Texas Public Radio|San Antonio Current|Express-News|MySA", re.I)
FULL = {  # query -> (city, skyline, NBA chip, MiLB chip or None, food city, screenshot)
    "Houston TX": ("Houston", "houston", "Rockets", "Space Cowboys", "location-houston.png"),
    "Miami FL": ("Miami", "miami", "Heat", None, "location-miami.png"),
    "Austin": ("Austin", "austin", "Spurs", "Express", "location-austin.png"),
}
QUICK = {"Houston, TX": "Houston", "Houston": "Houston", "77002": "Houston", "33101": "Miami"}

async def set_place(pg, q):
    await pg.evaluate("window.scrollTo(0, 0)")
    await pg.tap("#settings-btn"); await pg.wait_for_timeout(300)
    await pg.fill("#set-loc-q", q); await pg.press("#set-loc-q", "Enter")
    await pg.wait_for_function("() => /Now showing|Pick one|No places|failed/.test(document.querySelector('#set-loc-status').textContent)", timeout=45000)
    if "Pick one" in await pg.text_content("#set-loc-status"):
        await pg.click("#set-loc-results button >> nth=0")
    await pg.wait_for_function("() => /Now showing/.test(document.querySelector('#set-loc-status').textContent)", timeout=20000)
    await pg.wait_for_function("() => { const l = JSON.parse(localStorage.getItem('chisme-location') || '{}'); return l.place && l.place.metro !== undefined; }", timeout=45000)
    await pg.tap("#settings-close"); await pg.wait_for_timeout(300)

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev, timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        await ctx.add_init_script("localStorage.setItem('chisme-install-card-dismissed', '1'); localStorage.setItem('chisme-ios-hint-dismissed', '1')")
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
        await pg.wait_for_timeout(4000)
        start = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-location') || '{}')")
        check(start.get("source") == "gps", f"starts on the phone's GPS in San Antonio ({start.get('label')})")
        check(await pg.get_attribute("#topbar", "data-skyline") == "sa", "San Antonio skyline at home")
        for q, city in QUICK.items():
            await set_place(pg, q)
            l = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-location'))")
            await ctx.set_geolocation({"latitude": 29.3501, "longitude": -98.5601}); await pg.wait_for_timeout(2500)   # GPS keeps reporting SA
            l2 = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-location'))")
            check(l["source"] == "manual" and (l["place"] or {}).get("city") == city and l2["lat"] == l["lat"] and l2["source"] == "manual",
                  f"'{q}' → {l['label']} ({l['place'].get('city')}), still there after a GPS update ({l2['label']})")
        for q, (city, sky, nba, milb, shot) in FULL.items():
            print(f"-- {q}")
            await set_place(pg, q)
            await ctx.set_geolocation({"latitude": 29.3502, "longitude": -98.5602}); await pg.wait_for_timeout(1500)
            await pg.wait_for_function("() => window.__chisme.newsReady && !document.querySelector('#near-list .loading')", timeout=120000)
            await pg.wait_for_timeout(2500)
            r = await pg.evaluate("""() => ({ loc: JSON.parse(localStorage.getItem('chisme-location')), sky: document.querySelector('#topbar').dataset.skyline,
                cityTitle: document.querySelector('#city-title').textContent, saHidden: document.querySelector('#sa-sec').hidden,
                sources: [...document.querySelectorAll('#near-list .story, #near-list article, #city-list article')].map(a => (a.querySelector('.src, .source, .meta b') || {}).textContent || '').slice(0, 60),
                greet: document.querySelector('#greet-sub').textContent, feeds: [...document.querySelectorAll('#feeds li')].map(l => l.textContent.split(':')[0]) })""")
            check(r["loc"]["source"] == "manual" and r["loc"]["place"]["city"] == city, f"location is {city} and stays (GPS says SA): {r['loc']['label']}")
            check(r["sky"] == sky, f"header skyline: {r['sky']}")
            stamp = await pg.text_content("#news-updated")
            want_tz = {"Houston": "CDT", "Austin": "CDT", "Miami": "EDT"}[city]
            check(want_tz in stamp, f"times use {city}'s zone: '{stamp}'")
            check(r["cityTitle"] == f"More {city} news" and r["saHidden"], f"News: '{r['cityTitle']}', no 'San Antonio headlines' section")
            check(not any(SA_OUTLETS.search(f) for f in r["feeds"]), f"no San Antonio outlets fetched ({', '.join(r['feeds'][:6])} …)")
            # screenshot: header skyline + greeting + the first Check Your People stories (from that city's outlets)
            await pg.wait_for_function("() => document.querySelector('#sync').hidden || document.querySelector('#sync').dataset.state === 'done'", timeout=60000)
            await pg.wait_for_timeout(2500)
            await pg.set_viewport_size({"width": 390, "height": 1500}); await pg.wait_for_timeout(600)
            await pg.screenshot(path=os.path.join(OUT, shot))
            await pg.set_viewport_size({"width": 390, "height": 664}); await pg.wait_for_timeout(300)
            # Weather: NWS for the point
            wx = await pg.evaluate(f"fetch('/api/weather?' + 'lat=' + JSON.parse(localStorage.getItem('chisme-location')).lat + '&lon=' + JSON.parse(localStorage.getItem('chisme-location')).lon).then(r => r.json())")
            st = ((wx.get("current") or {}).get("station_name") or "") + " " + json.dumps(wx.get("location") or wx.get("point") or "")[:80]
            check(city.split()[0] in st or (wx.get("periods") or wx.get("forecast")), f"Weather: NWS for {city} ({st.strip()[:70]})")
            # Events
            await pg.tap('#tabs [data-view="events"]')
            await pg.wait_for_function("() => window.__chisme.eventsReady", timeout=150000); await pg.wait_for_timeout(1500)
            ev = await pg.evaluate("({ intro: document.querySelector('#events-intro').textContent, n: document.querySelectorAll('#events-list .ev').length, src: [...document.querySelectorAll('#event-sources li, #ev-sources li')].map(l => l.textContent.slice(0, 40)) })")
            check(ev["n"] > 0 and not any("Visit San Antonio" in s for s in ev["src"]), f"Events: {ev['n']} near {city}, no Visit San Antonio ({ev['intro'][:70]})")
            # Food
            await pg.tap('#tabs [data-view="antojos"]')
            await pg.wait_for_function(f"() => window.__chisme.foodReady && /{city}/.test(document.querySelector('#antojos-intro').textContent)", timeout=120000)
            await pg.wait_for_timeout(1500)
            fd = await pg.evaluate("""() => ({ intro: document.querySelector('#antojos-intro').textContent, desk: document.querySelector('#food-desk-h').textContent,
                deskN: document.querySelectorAll('#food-outlets .desk').length, road: document.querySelector('#food-latest-h').textContent,
                deskFirst: !!(document.querySelector('#food-desk').compareDocumentPosition(document.querySelector('#food-latest')) & Node.DOCUMENT_POSITION_FOLLOWING),
                outlets: [...document.querySelectorAll('#food-outlets .desk .fr-by b')].map(b => b.textContent) })""")
            check(city in fd["intro"] and fd["desk"] == f"{city} food news" and 0 < fd["deskN"] <= 5, f"¿Cuál dieta?: '{fd['desk']}' ({fd['deskN']}: {', '.join(fd['outlets'][:3])})")
            check("San Antonio" in fd["road"] and fd["deskFirst"], f"SA creators kept but labeled + below the city's food news ('{fd['road']}')")
            await pg.evaluate("window.scrollTo(0, document.querySelector('#antojos').getBoundingClientRect().top + scrollY - 110)"); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f"/tmp/wk/food-{city.lower()}.png")
            # Sports
            await pg.tap('#tabs [data-view="sports"]')
            await pg.wait_for_function(f"() => /{nba}/.test(document.querySelector('#sp-chips [data-lg=nba]').textContent)", timeout=150000)
            spt = await pg.evaluate("""() => ({ nba: document.querySelector('#sp-chips [data-lg=nba]').textContent.trim(), milb: document.querySelector('#sp-chips [data-lg=missions]').hidden ? null : document.querySelector('#sp-chips [data-lg=missions]').textContent.trim(),
                intro: document.querySelector('#sports-intro').textContent, kicker: (document.querySelector('.spurs-card .kicker') || {}).textContent })""")
            check(nba in spt["nba"] and ((milb is None and spt["milb"] is None) or (milb and spt["milb"] and milb in spt["milb"])), f"Sports: {spt['nba']} · MiLB {spt['milb']} · {spt['kicker']}")
            await pg.wait_for_function("() => window.__chisme.view === 'sports' && window.__chisme.sportsReady", timeout=60000); await pg.wait_for_timeout(1200)
            await pg.evaluate("window.scrollTo(0, document.querySelector('#sports').getBoundingClientRect().top + scrollY - 110)"); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f"/tmp/wk/sports-{city.lower()}.png")
            await pg.tap('#tabs [data-view="news"]'); await pg.wait_for_timeout(600)
        # back home: "Use my location" returns to GPS in San Antonio
        await pg.evaluate("window.scrollTo(0, 0)"); await pg.tap("#settings-btn"); await pg.tap("#set-gps")
        await pg.wait_for_function("() => JSON.parse(localStorage.getItem('chisme-location')).source === 'gps'", timeout=30000)
        await pg.tap("#settings-close"); await pg.wait_for_timeout(4000)
        check(await pg.get_attribute("#topbar", "data-skyline") == "sa", "“Use my location” → back to GPS (San Antonio skyline)")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)")
    sys.exit(1 if fails else 0)

asyncio.run(main())
