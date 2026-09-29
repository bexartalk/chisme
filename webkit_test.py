"""WebKit / iPhone 13 checks (what the home-screen app runs on):
  * first launch: one-time location card on the home screen -> pick a ZIP -> card gone for good,
    no location UI on the home screen after reloads (location lives in Settings)
  * Sports and Weather tabs render (fresh install), incl. geolocation denied and a hanging geolocation
  * narrow phone (320 px), default-tab setting (opens on Weather / Sports)
  * no console errors or page errors
Writes screenshots/location-first-run.png, home-no-location.png, sports-fixed.png, weather-fixed.png, header-logo.png

    ./venv/bin/python webkit_test.py [url]      (default http://localhost:8211/)
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: fails.append(what)

async def new(p, b, width=None, grant=None, init=None):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    if width: dev["viewport"] = {"width": width, "height": 700}; dev["screen"] = {"width": width, "height": 700}
    kw = {}
    if grant: kw = dict(permissions=["geolocation"], geolocation={"latitude": grant[0], "longitude": grant[1]})
    ctx = await b.new_context(**dev, **kw)
    if init: await ctx.add_init_script(init)
    pg = await ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errs.append(f"console: {m.text}") if m.type == "error" else None)
    return ctx, pg, errs

async def ready(pg):
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    await pg.wait_for_timeout(800)

async def idle(pg):
    """Wait for in-flight API requests to finish (a reload mid-fetch makes WebKit log cancelled loads)."""
    try: await pg.wait_for_function("() => window.__chisme && window.__chisme.sync.busy.length === 0", timeout=60000)
    except Exception: pass
    await pg.wait_for_timeout(300)

async def settle(pg):
    try: await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=10000)
    except Exception: pass
    await pg.wait_for_timeout(400)

async def view_ok(pg, v):
    await pg.click(f'#tabs [data-view="{v}"]')
    sel = {"sports": "#sports-body .sp-photo, #sports-body .error", "weather": "#view-weather .now-temp, #view-weather .notice, #view-weather .error"}[v]
    await pg.wait_for_selector(sel, timeout=60000)
    await pg.wait_for_timeout(700)
    return await pg.evaluate(f"""() => {{ const el = document.querySelector('#view-{v}'), r = el.getBoundingClientRect();
        return {{ view: window.__chisme.view, onScreen: r.left > -5 && r.left < 20, chars: el.innerText.trim().length,
                 error: !!el.querySelector('.error') }}; }}""")

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()

        print("== first launch (location permission not granted yet)")
        ctx, pg, errs = await new(p, b)
        await pg.goto(URL); await ready(pg)
        card = await pg.evaluate("() => ({ shown: !document.querySelector('#loc-panel').hidden, mode: document.querySelector('#loc-panel').dataset.mode, pill: !!document.querySelector('#loc-btn, .loc-pill') })")
        check(card["shown"] and card["mode"] == "ask" and not card["pill"], f"one-time location card on the home screen, no location pill ({card})")
        await pg.evaluate("window.scrollTo(0, 0)"); await settle(pg)
        await pg.screenshot(path=os.path.join(OUT, "location-first-run.png"))
        await pg.fill("#loc-q", "78211"); await pg.click("#loc-form button[type=submit]")
        await pg.wait_for_function("() => document.querySelector('#loc-panel').hidden && /78211|San Antonio/.test(document.querySelector('#set-loc-now').textContent) && window.__chisme.loc.source === 'manual'", timeout=60000)
        check(True, "picking a ZIP on the card sets the location and hides the card")
        for i in range(2):
            await idle(pg); await pg.reload(); await ready(pg)
            st = await pg.evaluate("() => ({ card: !document.querySelector('#loc-panel').hidden, pill: !!document.querySelector('#loc-btn, .loc-pill'), now: document.querySelector('#set-loc-now').textContent })")
            check(not st["card"] and not st["pill"], f"reload {i + 1}: no location UI on the home screen ({st})")
        await pg.evaluate("window.scrollTo(0, 0)"); await settle(pg)
        await pg.screenshot(path=os.path.join(OUT, "home-no-location.png"))
        await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
        st = await pg.evaluate("() => ({ now: document.querySelector('#set-loc-now').textContent, gps: !!document.querySelector('#set-gps'), form: !!document.querySelector('#set-loc-form') })")
        check("San Antonio" in st["now"] and st["gps"] and st["form"], f"Settings shows the current location + Use my location + city/ZIP ({st})")
        await pg.click("#settings-close")
        check(not errs, f"no console/page errors ({errs[:3]})")
        await ctx.close()

        print("== returning user who says 'Not now'")
        ctx, pg, errs = await new(p, b)
        await pg.goto(URL); await ready(pg)
        await pg.click("#loc-close"); await idle(pg); await pg.reload(); await ready(pg)
        check(await pg.is_hidden("#loc-panel"), "'Not now' hides the card for good (still San Antonio)")
        await ctx.close()

        print("== location granted (South Side SA): Sports + Weather, screenshots")
        ctx, pg, errs = await new(p, b, grant=(29.36, -98.52))
        await pg.goto(URL); await ready(pg)
        await pg.wait_for_function("() => window.__chisme.loc.source === 'gps'", timeout=30000)
        check(await pg.is_hidden("#loc-panel"), "granted permission: no card, location set automatically")
        if await pg.is_visible("#ios-hint-close"): await pg.click("#ios-hint-close")   # Safari tab, not standalone
        await pg.evaluate("document.activeElement && document.activeElement.blur()")
        for v in ("sports", "weather"):
            r = await view_ok(pg, v)
            check(r["view"] == v and r["onScreen"] and r["chars"] > 300 and not r["error"], f"{v} tab shows {v} ({r})")
            await pg.evaluate("document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0)"); await settle(pg)
            await pg.screenshot(path=os.path.join(OUT, f"{v}-fixed.png"))
        await pg.click('#tabs [data-view="news"]'); await pg.evaluate("document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0)"); await settle(pg)
        await pg.screenshot(path=os.path.join(OUT, "header-logo.png"), clip={"x": 0, "y": 0, "width": 390, "height": 170})
        logo = await pg.evaluate("""() => { const b = document.querySelector('#settings-btn'), s = getComputedStyle(b);
            return { bg: s.backgroundColor, border: s.borderTopWidth, pad: s.paddingTop, appearance: s.appearance || s.webkitAppearance }; }""")
        check(logo["bg"] in ("rgba(0, 0, 0, 0)", "transparent") and logo["border"] == "0px" and logo["pad"] == "0px" and logo["appearance"] == "none", f"logo button has no background/border/padding ({logo})")
        await pg.click("#settings-btn"); await pg.wait_for_timeout(400)
        check(await pg.evaluate("document.querySelector('#settings').open"), "tapping the logo still opens Settings")
        await pg.click("#settings-close")
        check(not errs, f"no console/page errors ({errs[:3]})")
        await ctx.close()

        print("== geolocation denied / hanging: Weather is never blank")
        for name, init in [("denied", "navigator.geolocation.getCurrentPosition = (ok, err) => setTimeout(() => err({ code: 1, message: 'denied' }), 50); navigator.geolocation.watchPosition = (ok, err) => { setTimeout(() => err({ code: 1 }), 50); return 1; };"),
                           ("hanging", "navigator.geolocation.getCurrentPosition = () => {}; navigator.geolocation.watchPosition = () => 1;")]:
            ctx, pg, errs = await new(p, b, init=init)
            await pg.goto(URL); await ready(pg)
            if name == "denied":
                await pg.click("#loc-gps")
                await pg.wait_for_selector("#loc-panel[data-mode=denied]", timeout=15000)
            r = await view_ok(pg, "weather")
            check(r["view"] == "weather" and r["onScreen"] and r["chars"] > 300, f"{name}: Weather shows the default location's weather ({r})")
            check(not errs, f"{name}: no console/page errors ({errs[:3]})")
            await ctx.close()

        print("== narrow phone (320 px) + default tab")
        ctx, pg, errs = await new(p, b, width=320, init="if (!localStorage.getItem('chisme-default-tab')) { localStorage.setItem('chisme-location-setup', '1'); localStorage.setItem('chisme-default-tab', 'weather'); }")
        await pg.goto(URL); await ready(pg); await pg.wait_for_timeout(800)
        check(await pg.evaluate("() => window.__chisme.view") == "weather", "default tab 'Weather' opens on Weather")
        wide = await pg.evaluate("() => ({ doc: document.documentElement.scrollWidth, tabs: [...document.querySelectorAll('#tabs .tab')].map(t => Math.round(t.getBoundingClientRect().right)) })")
        check(wide["doc"] <= 320 and max(wide["tabs"]) <= 320, f"320 px: no sideways overflow, all 4 tabs fit ({wide})")
        for v in ("sports", "weather"):
            r = await view_ok(pg, v)
            check(r["view"] == v and r["onScreen"] and r["chars"] > 300, f"320 px: {v} renders ({r})")
        await pg.evaluate("localStorage.setItem('chisme-default-tab', 'sports')"); await idle(pg); await pg.reload(); await ready(pg); await pg.wait_for_timeout(800)
        check(await pg.evaluate("() => window.__chisme.view") == "sports", "default tab 'Sports' opens on Sports")
        check(not errs, f"no console/page errors ({errs[:3]})")
        await ctx.close()
        await b.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
    sys.exit(1 if fails else 0)

asyncio.run(main())
