"""v49.12: the food tab is '¿Y la dieta?' (was '¿Cuál dieta?') everywhere you see it, and it fits the tab bar.
Chromium (Android-size) + WebKit (iPhone-size), 320 / 360 / 390 / 412 px wide, light and the biggest Text size:
  • the tab, the section header, the Settings choice, the feed's Back button and the swipe pane's label read '¿Y la dieta?'
  • no visible text, aria-label or manifest entry still says 'Cuál dieta'
  • every tab label fits inside its button (no overflow, at most 2 lines, inside the screen); the 4 tabs stay in at most 2 rows (one row on phones)
  • the old links #cual-dieta / #antojos still open the food tab, and #y-la-dieta does too"""
import asyncio, json, os, sys, urllib.request
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
URL = os.environ.get("URL", "http://localhost:8211/")
NEW, OLD = "¿Y la dieta?", "Cuál dieta"
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
FIT = """() => [...document.querySelectorAll('#tabs .tab')].map(t => { const r = t.getBoundingClientRect(), l = t.querySelector('.tl'), rg = document.createRange();
  if (l) rg.selectNodeContents(l); else rg.selectNode(t.lastChild); const lr = rg.getBoundingClientRect(), fsz = parseFloat(getComputedStyle(l || t).fontSize);
  return { v: t.dataset.view, text: (l ? l.textContent : t.lastChild.textContent).trim(), lines: Math.round(lr.height / (fsz * 1.08)) || 1,
           over: t.scrollWidth > t.clientWidth + 1 || lr.left < r.left - 0.5 || lr.right > r.right + 0.5 || lr.bottom > r.bottom + 0.5,
           out: r.left < -1 || r.right > innerWidth + 1, top: Math.round(r.top) }; })"""
async def main():
    m = json.load(urllib.request.urlopen(URL.rstrip("/") + "/static/manifest.webmanifest"))
    check(OLD not in json.dumps(m, ensure_ascii=False), "manifest: no 'Cuál dieta'")
    async with async_playwright() as p:
        for name, bt, mob in (("chromium", p.chromium, dict(device_scale_factor=2.625, is_mobile=True, has_touch=True)), ("webkit", p.webkit, dict(device_scale_factor=3, is_mobile=True, has_touch=True))):
            b = await bt.launch()
            for w in (320, 360, 390, 412):
                for fs in (0, 22):
                    ctx = await b.new_context(viewport={"width": w, "height": 740}, **mob)
                    await ctx.add_init_script("try { localStorage.setItem('chisme-location-setup', '1'); localStorage.setItem('chisme-default-tab', 'antojos');"
                                              + (f" localStorage.setItem('chisme-font-px', '{fs}');" if fs else "") + " } catch (e) {}")
                    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
                    pg = await ctx.new_page()
                    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(500)
                    tabs = await pg.evaluate(FIT)
                    food = next(t for t in tabs if t["v"] == "antojos")
                    bad = [t for t in tabs if t["over"] or t["out"] or t["lines"] > 2]
                    rows = len({t["top"] for t in tabs})
                    check(food["text"] == NEW and not bad and rows <= 2, f"{name} {w}px{' text ' + str(fs) + 'px' if fs else ''}: '{food['text']}' fits ({food['lines']} line(s)), all 4 tabs fit in {rows} row(s) {bad[:2]}")
                    if w == 320 and not fs:
                        await pg.screenshot(path=f"/tmp/food-label-{name}-320.png", clip={"x": 0, "y": 0, "width": 320, "height": 200})
                        seen = await pg.evaluate("""() => ({ head: document.querySelector('#antojos-title').textContent.trim(), pane: document.querySelector('#view-antojos').getAttribute('aria-label'),
                          set: document.querySelector('#settings input[name=deftab][value=antojos]').parentElement.textContent.trim(), back: document.querySelector('#feed-close').getAttribute('aria-label'),
                          old: [document.body.innerText, ...[...document.querySelectorAll('[aria-label],[title],[alt],[placeholder]')].map(e => [e.getAttribute('aria-label'), e.title, e.alt, e.placeholder].join(' '))].join(' ').includes('Cuál dieta') || document.documentElement.innerHTML.includes('Cuál dieta') })""")
                        check(seen["head"] == "🌮 " + NEW and seen["pane"] == NEW and seen["set"] == "🌮 " + NEW and seen["back"] == "Back to " + NEW and not seen["old"],
                              f"{name}: header, swipe pane, Settings and Back read {NEW}; no 'Cuál dieta' left on the page ({seen})")
                        for h in ("#cual-dieta", "#antojos", "#y-la-dieta"):
                            await pg.goto(URL + h); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(300)
                            await pg.evaluate("localStorage.setItem('chisme-default-tab', 'news')")
                            await pg.goto(URL + h); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(300)
                            v = await pg.evaluate("__chisme.view")
                            check(v == "antojos", f"{name}: link {h} opens the food tab ({v})")
                    await ctx.close()
            await b.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
