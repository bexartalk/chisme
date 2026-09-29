"""WebKit (iPhone 13): food Save toggles, Saved spots list, persistence across reload + offline, Directions, remove/undo, add place."""
import asyncio, os, sys
from playwright.async_api import async_playwright
URL = os.environ.get("URL", "http://localhost:8211/")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

SAVE = """(needle) => { const a = [...document.querySelectorAll('#food-latest .fr')].find(x => x.querySelector('h4').textContent.includes(needle));
  if (!a) return null; const b = a.querySelector('.fr-save'); b.scrollIntoView({block:'center'}); b.click();
  return { pressed: b.getAttribute('aria-pressed'), name: b.textContent }; }"""

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev, color_scheme="light")
        await ctx.add_init_script("if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); }")
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
        await pg.goto(URL)
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
        await pg.click('#tabs [data-view="events"]')
        await pg.click('#ev-chips [data-cat="food"]')
        await pg.wait_for_function("() => window.__chisme.foodReady && document.querySelectorAll('#food-latest .fr-save').length > 3", timeout=60000)
        check(await pg.evaluate("document.querySelector('#n-saved').textContent") == "(0)", "Saved spots count starts at (0)")
        first = await pg.evaluate("document.querySelector('#food-latest .fr-save').textContent")
        check(first.startswith("Save: ") and len(first) > 10, f"Save button has an accessible name with the title ({first[:40]!r})")
        titles = await pg.evaluate("[...document.querySelectorAll('#food-latest .fr h4')].map(h => h.textContent)")
        picks = [t for t in titles if "Losoya" in t][:1] + [t for t in titles if "Alzer" in t][:1]
        outlet = await pg.evaluate("document.querySelector('#food-outlets .fr h4').textContent")
        picks = [outlet] + list(reversed(picks or titles[:2]))  # newest first in the list: Losoya's (has an address) on top
        for i, t in enumerate(picks):
            r = await pg.evaluate(SAVE, t[:25])
            check(bool(r) and r["pressed"] == "true" and r["name"].startswith("Saved"), f"Save toggles on: {t[:40]}")
            if i == 0:
                r = await pg.evaluate(SAVE, t[:25]); check(r["pressed"] == "false", "Save toggles off")
                r = await pg.evaluate(SAVE, t[:25]); check(r["pressed"] == "true", "Save toggles back on")
        check(await pg.evaluate("document.querySelector('#n-saved').textContent") == f"({len(picks)})", f"count shows ({len(picks)})")
        stored = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-food-saved'))")
        keys = set(stored[0].keys())
        check({"url", "title", "image", "source", "published", "place", "savedAt"} <= keys, f"stored fields {sorted(keys)}")
        # survives a reload + fresh feed fetch (offline is checked in Chromium below; WebKit's offline emulation can't reload SW pages)
        await pg.reload()
        await pg.wait_for_function("() => window.__chisme && document.querySelector('#n-saved')", timeout=30000)
        await pg.click('#tabs [data-view="events"]')
        if await pg.get_attribute('#ev-chips [data-cat="food"]', "aria-pressed") != "true": await pg.click('#ev-chips [data-cat="food"]')
        await pg.click('#food-view [data-fv="saved"]')
        n = await pg.evaluate("document.querySelectorAll('#food-saved .fs').length")
        check(n == len(picks), f"after reload: {n} saved spots listed")
        check(await pg.evaluate("document.querySelector('#food-latest').hidden && document.querySelector('#events-list').hidden"), "Saved view hides the live feeds + events")
        dirs = await pg.evaluate("[...document.querySelectorAll('#food-saved .fs-dir')].map(a => [a.getAttribute('aria-label'), a.href])")
        print("   directions:", dirs)
        check(any("Losoya" in l and "4445%20Walzem" in h and h.startswith("https://maps.apple.com/?daddr=") for l, h in dirs) or "Losoya" not in " ".join(picks), "Directions → Apple Maps with the street address")
        # remove + undo
        await pg.evaluate("document.querySelector('#food-saved .fs:last-child .fs-rm').click()")
        check(await pg.evaluate("document.querySelector('#n-saved').textContent") == f"({len(picks)-1})", "Remove drops the count")
        check(await pg.evaluate("document.activeElement.classList.contains('fs-undo')"), "focus moves to Undo")
        await pg.click(".fs-undo")
        check(await pg.evaluate("document.querySelectorAll('#food-saved .fs').length") == len(picks), "Undo restores it")
        # add a place to the outlet story
        row = f"#food-saved .fs:has(h4 a:text-is({outlet!r}))"
        await pg.evaluate("(t) => [...document.querySelectorAll('#food-saved .fs')].find(a => a.querySelector('h4').textContent === t).querySelector('.fs-edit').click()", outlet)
        await pg.fill("#food-saved .fs-form input[autocomplete=off]", "The Esquire Tavern")
        await pg.fill("#food-saved .fs-form input[autocomplete=street-address]", "155 E Commerce St, San Antonio, TX 78205")
        await pg.click("#food-saved .fs-form button[type=submit]")
        h = await pg.evaluate("(t) => { const a = [...document.querySelectorAll('#food-saved .fs')].find(a => a.querySelector('h4').textContent === t).querySelector('.fs-dir'); return a && a.href }", outlet)
        check(bool(h) and "155%20E%20Commerce" in h, "Add place → Directions button appears")
        await pg.evaluate("(t) => [...document.querySelectorAll('#food-saved .fs')].find(a => a.querySelector('h4').textContent === t).querySelector('.fs-edit').click()", outlet)
        await pg.fill("#food-saved .fs-form input[autocomplete=off]", ""); await pg.fill("#food-saved .fs-form input[autocomplete=street-address]", "")
        await pg.click("#food-saved .fs-form button[type=submit]")
        # screenshot: chips + list under the fixed nav
        await pg.evaluate("window.scrollTo(0, document.querySelector('#food-view').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 10)")
        try: await pg.wait_for_function("document.querySelector('#sync').hidden || document.querySelector('#sync').dataset.state === 'done'", timeout=15000)
        except Exception: pass
        await pg.wait_for_timeout(4000)
        chips = await pg.evaluate("[...document.querySelectorAll('#food-view .chip')].every(e => e.getBoundingClientRect().right <= innerWidth - 16 && e.getBoundingClientRect().left >= 16)")
        check(chips, "Latest / Saved spots chips both fully visible at 390px")
        fit = await pg.evaluate("[...document.querySelectorAll('#food-saved .fs-act > *')].every(e => e.getBoundingClientRect().right <= innerWidth - 8)")
        check(fit, "saved-spot buttons fit at 390px")
        await pg.screenshot(path=os.path.join(OUT, "food-saved.png"))
        await pg.emulate_media(color_scheme="dark"); await pg.evaluate("document.documentElement.dataset.theme='dark'")
        await pg.wait_for_timeout(400); os.makedirs("/tmp/wk", exist_ok=True)
        await pg.screenshot(path="/tmp/wk/food-saved-dark.png")
        await pg.evaluate("document.documentElement.dataset.theme='light'")
        await pg.click('#food-view [data-fv="latest"]')
        check(await pg.evaluate("!document.querySelector('#food-latest').hidden && !document.querySelector('#events-list').hidden"), "Latest reviews brings the feeds back")
        await pg.evaluate("window.scrollTo(0, document.querySelector('#food-view').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 10)")
        await pg.wait_for_timeout(1200)
        await pg.screenshot(path="/tmp/wk/food-latest.png")
        await pg.evaluate("document.querySelector('#food-outlets').scrollIntoView({block:'start'}); scrollBy(0, -110)")
        await pg.wait_for_timeout(600); await pg.screenshot(path="/tmp/wk/food-outlets.png")
        check(not errs, f"no console/page errors ({errs[:3]})")
        await b.close()
    # offline (Chromium, fresh profile): saved spots still render with the network gone
    import tempfile
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path="/usr/bin/google-chrome", args=["--no-sandbox"],
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, timezone_id="America/Chicago",
            geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        pg = ctx.pages[0]
        await pg.goto(URL + "#food", wait_until="networkidle")
        await pg.reload(wait_until="networkidle")
        await pg.wait_for_function("() => window.__chisme.foodReady && document.querySelectorAll('#food-latest .fr-save').length > 1", timeout=120000)
        await pg.evaluate("document.querySelectorAll('#food-latest .fr-save')[0].click(); document.querySelectorAll('#food-latest .fr-save')[1].click()")
        await ctx.set_offline(True)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.reload(wait_until="domcontentloaded")
        await pg.wait_for_function("() => window.__chisme && document.querySelector('#food-block') && !document.querySelector('#food-block').hidden", timeout=60000)
        await pg.click('#food-view [data-fv="saved"]')
        r = await pg.evaluate("({ on: navigator.onLine, n: document.querySelectorAll('#food-saved .fs').length, count: document.querySelector('#n-saved').textContent, links: [...document.querySelectorAll('#food-saved .fs h4 a')].every(a => a.href.startsWith('http')) })")
        check(not r["on"] and r["n"] == 2 and r["count"] == "(2)" and r["links"], f"offline: saved spots render from the phone ({r})")
        check(not errs, f"offline: no page errors ({errs[:2]})")
        await ctx.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
