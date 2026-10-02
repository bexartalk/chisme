"""Headless location tests (phone 390x844):
 (a) geolocation granted at South Side San Antonio, (b) granted at Austin,
 (c) permission denied + manual entry, plus a move (>3 km) test and a non-US point.
Usage: ./venv/bin/python location_test.py [url]"""
import asyncio, json, sys, tempfile
from pathlib import Path
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)

STATE_JS = """() => ({
  label: document.querySelector('#set-loc-now').textContent,   // location now lives in Settings
  homeLocUI: !!document.querySelector('#loc-btn, .loc-pill'),
  loc: window.__chisme.loc,
  panel: document.querySelector('#loc-panel').hidden ? null : document.querySelector('#loc-panel').dataset.mode,
  alerts: document.querySelector('#alerts').innerText.slice(0, 120),
  temp: document.querySelector('.now-temp')?.textContent || null,
  notice: document.querySelector('#current .notice')?.textContent?.slice(0, 120) || null,
  forecastDays: document.querySelectorAll('#forecast .day').length,
  station: document.querySelector('.station')?.textContent || null,
  near: document.querySelectorAll('#near-list .story').length,
  nearTop: [...document.querySelectorAll('#near-list .story')].slice(0, 4).map(s => s.querySelector('h3').textContent.slice(0, 70) + ' [' + [...s.querySelectorAll('.tag')].map(t => t.textContent).join(', ') + ']'),
  nearHint: document.querySelector('#near-hint').textContent,
  more: document.querySelectorAll('#city-list .story').length,
  cityTitle: document.querySelector('#city-title').textContent,
  saSection: !document.querySelector('#sa-sec').hidden,
  mapCenter: (c => [+c.lat.toFixed(3), +c.lng.toFixed(3)])(window.__chisme.map.getCenter()),
  radarTiles: [...document.querySelectorAll('.radar-tiles img.leaflet-tile')].filter(i => i.complete && i.naturalWidth > 0).length,
  tz: document.querySelector('#tz-name').textContent,
  errors: [...document.querySelectorAll('.error')].map(e => e.textContent),
})"""

async def ready(page, label_re, timeout=90000):
    await page.wait_for_function(f"() => /{label_re}/.test(document.querySelector('#set-loc-now').textContent)", timeout=timeout)
    # weather + news rendered for the *current* location
    await page.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=timeout)
    await page.wait_for_timeout(2500)

async def shots(page, name):
    await page.evaluate("document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0,0)")
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(OUT / f"{name}.png"))
    await page.evaluate("document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0, document.querySelector('#near').getBoundingClientRect().top + window.scrollY - 8)")
    await page.wait_for_timeout(600)
    await page.screenshot(path=str(OUT / f"{name}-news.png"))

async def main():
    report = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        logs = []

        async def ctx_for(**kw):
            c = await b.new_context(**PHONE, **kw)
            pg = await c.new_page()
            pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
            pg.on("console", lambda m: logs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            return c, pg

        # (a) South Side San Antonio, permission granted
        c, pg = await ctx_for(geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"],
                              timezone_id="America/Chicago")
        await pg.goto(URL, wait_until="domcontentloaded")
        await ready(pg, "(?:Using your location|Showing): .*San Antonio")
        report["a_san_antonio"] = await pg.evaluate(STATE_JS)
        await shots(pg, "location-sa")
        # move > 3 km: emulate driving to Austin while the app is open (watchPosition)
        await c.set_geolocation({"latitude": 30.27, "longitude": -97.74})
        await ready(pg, "(?:Using your location|Showing): .*Austin")
        report["a_moved_to_austin"] = {k: v for k, v in (await pg.evaluate(STATE_JS)).items() if k in ("label", "loc", "mapCenter", "temp", "station")}
        await c.close()

        # (b) Austin, permission granted
        c, pg = await ctx_for(geolocation={"latitude": 30.27, "longitude": -97.74}, permissions=["geolocation"],
                              timezone_id="America/Chicago")
        await pg.goto(URL, wait_until="domcontentloaded")
        await ready(pg, "(?:Using your location|Showing): .*Austin")
        report["b_austin"] = await pg.evaluate(STATE_JS)
        await shots(pg, "location-austin")
        await c.close()

        # (c) permission denied -> manual entry
        c, pg = await ctx_for(timezone_id="America/Chicago")
        cdp = await c.new_cdp_session(pg)
        ctx_id = (await cdp.send("Target.getTargetInfo"))["targetInfo"]["browserContextId"]
        bcdp = await b.new_browser_cdp_session()
        await bcdp.send("Browser.setPermission", {"permission": {"name": "geolocation"}, "setting": "denied",
                                                  "origin": URL.rstrip("/"), "browserContextId": ctx_id})
        await pg.goto(URL, wait_until="domcontentloaded")
        report["c_permission_state"] = await pg.evaluate("navigator.permissions.query({name:'geolocation'}).then(r => r.state)")
        await pg.wait_for_selector("#loc-panel:not([hidden])[data-mode=denied]", timeout=30000)
        await ready(pg, "San Antonio")
        await pg.fill("#loc-q", "Houston, TX")
        report["c_denied_default"] = await pg.evaluate(STATE_JS)
        await pg.evaluate("document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0,0)")
        await pg.screenshot(path=str(OUT / "location-denied.png"))
        await pg.click("#loc-form button[type=submit]")
        await pg.wait_for_selector("#loc-results .loc-result", timeout=30000)   # "Houston, TX" vs "Houston County"
        report["c_search_choices"] = await pg.locator("#loc-results .loc-result b").all_text_contents()
        await pg.screenshot(path=str(OUT / "location-denied-search.png"))
        await pg.locator("#loc-results .loc-result").first.click()
        await ready(pg, "(?:Using your location|Showing): .*Houston")
        report["c_manual_houston"] = await pg.evaluate(STATE_JS)
        await shots(pg, "location-denied-manual")
        # after a place is set, the home screen has no location UI; reload keeps it that way
        await pg.reload(wait_until="domcontentloaded")
        await ready(pg, "(?:Using your location|Showing): .*Houston")
        report["c_after_setup_reload"] = await pg.evaluate("() => ({ panelHidden: document.querySelector('#loc-panel').hidden, pill: !!document.querySelector('#loc-btn, .loc-pill') })")
        # ZIP entry via Settings (the only place to change location now)
        await pg.click("#settings-btn")
        await pg.fill("#set-loc-q", "78211")
        await pg.click("#set-loc-form button[type=submit]")
        await ready(pg, "(?:Using your location|Showing): .*San Antonio")
        await pg.click("#settings-close")
        report["c_manual_zip"] = {k: v for k, v in (await pg.evaluate(STATE_JS)).items() if k in ("label", "loc", "near", "temp")}
        await c.close()

        # non-US point (NWS doesn't cover it)
        c, pg = await ctx_for(geolocation={"latitude": 48.8566, "longitude": 2.3522}, permissions=["geolocation"],
                              timezone_id="Europe/Paris")
        await pg.goto(URL, wait_until="domcontentloaded")
        await ready(pg, "(?:Using your location|Showing): .*(Paris|France)")
        report["d_non_us"] = await pg.evaluate(STATE_JS)
        await pg.evaluate("document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0,0)")
        await pg.screenshot(path=str(OUT / "location-nonus.png"))
        await c.close()
        await b.close()
    report["page_errors"] = logs[:20]
    print(json.dumps(report, indent=1, ensure_ascii=False))

asyncio.run(main())
