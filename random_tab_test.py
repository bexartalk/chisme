"""v49.12 random launch tab (static/app.js launchTab). NO_AUTO_QUIET: this test is about the launch tab, so the test shim's
News pin (popup_quiet.QUIET) is left out. Chromium, Android-size phone.
  • the very first launch opens News with the location card, exactly as before (and counts as the last pick)
  • every later launch opens a random main tab, never the same one twice in a row; the tab bar marks it and it's on screen
  • deep links win: #weather, #juan, ?tab=events, ?story=… (News + the reader)
  • Settings → Open Chisme to: 🔀 Surprise me is the default; a fixed pick (Sports) opens Sports every time
  • a reload Chisme does itself (update, 'Refresh everyone') stays on the tab you were on
  • no flash of the old News default: every frame painted before app.js moves shows either nothing in the track or the launch tab"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
URL = os.environ.get("URL", "http://localhost:8211/")
VIEWS = ["news", "sports", "weather", "antojos", "juegos", "events"]
QUIET_NOTIF = "try { localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 })); localStorage.setItem('chisme-settings-tip', 'test:0'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); localStorage.setItem('chisme-ios-hint-dismissed','1'); } catch (e) {}"
FRAMES = """window.__frames = []; (function f() { const a = document.querySelector('.view.active'), t = document.querySelector('.track'), c = null;
  if (a && t) { const tabLit = [...document.querySelectorAll('.tab')].filter(x => !x.dataset.scroll && getComputedStyle(x).backgroundColor !== 'rgb(0, 0, 0)').map(x => x.dataset.view);
    window.__frames.push({ shown: getComputedStyle(t).opacity !== '0' ? a.dataset.view : null, lit: tabLit }); }
  if (!window.__chisme || !window.__chisme.ready) requestAnimationFrame(f); })();"""
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
STATE = """() => { const v = window.__chisme.view, t = document.querySelector('.tab[aria-current=page]'), el = document.querySelector('#view-' + v), r = el.getBoundingClientRect();
  return { view: v, tab: t ? t.dataset.view : null, onscreen: Math.abs(r.left) < 30 && el.classList.contains('active'), last: localStorage.getItem('chisme-launch-last') }; }"""
async def launch(pg, url=URL):
    await pg.goto(url); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(400)
    return await pg.evaluate(STATE)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 412, "height": 915}, device_scale_factor=2.625, is_mobile=True, has_touch=True)
        await ctx.add_init_script(QUIET_NOTIF); await ctx.add_init_script(FRAMES); await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        s = await launch(pg)
        loc = await pg.evaluate("!document.querySelector('#loc-panel').hidden")
        check(s["view"] == "news" and s["tab"] == "news" and loc and s["last"] == "news", f"first launch: News + the location card, as before ({s}, card {loc})")
        await pg.evaluate("localStorage.setItem('chisme-location-setup', '1')")   # (what finishing the location card does)
        seen, prev, bad, flash = [], "news", [], []
        for i in range(14):
            s = await launch(pg)
            seen.append(s["view"])
            fr = await pg.evaluate("window.__frames")
            flash += [(s["view"], f) for f in fr if (f["shown"] not in (None, s["view"])) or (f["lit"] and f["lit"] != [s["view"]])][:1]
            if s["view"] not in VIEWS or s["view"] == prev or s["tab"] != s["view"] or not s["onscreen"] or s["last"] != s["view"]: bad.append((prev, s))
            prev = s["view"]
        check(not bad, f"14 launches: a main tab each time, never the same twice in a row, tab bar + content match {seen} {bad[:2]}")
        check(not flash, f"…with no flash of another tab before it (track hidden or the launch tab, the tab bar lit on it) {flash[:2]}")
        check(len(set(seen)) >= 4, f"…and they really vary ({len(set(seen))} different tabs)")
        for url, want in ((URL + "#weather", "weather"), (URL + "#juan", "juegos"), (URL + "?tab=events", "events"), (URL + "?tab=sports#juegos", "juegos")):
            for _ in range(2):   # twice: a deep link wins even when it repeats the last tab
                s = await launch(pg, url)
                if s["view"] != want: break
            check(s["view"] == want and s["tab"] == want, f"deep link {url[len(URL) - 1:]} → {want} ({s['view']})")
        s = await launch(pg, URL + "?story=" + "https%3A%2F%2Fwww.ksat.com%2Fnews%2Ftest-story")
        await pg.wait_for_timeout(600)
        check(s["view"] == "news" and await pg.evaluate("document.querySelector('#player').open"), f"notification / shared story link → News + the reader ({s['view']})")
        await pg.evaluate("document.querySelector('#player').close()")
        await pg.evaluate("document.querySelector('#settings-btn').click()"); await pg.wait_for_timeout(300)
        sm = await pg.evaluate("(() => { const r = document.querySelector('#settings input[name=deftab][value=random]'); return r && [r.checked, r.parentElement.textContent.trim()]; })()")
        check(bool(sm) and sm[0] and "Surprise me" in sm[1], f"Settings → Open Chisme to: 🔀 Surprise me is on by default ({sm})")
        await pg.evaluate("document.querySelector('input[name=deftab][value=sports]').scrollIntoView({block: 'center'})"); await pg.click("#settings input[name=deftab][value=sports]"); await pg.click("#settings-close")
        v = [(await launch(pg))["view"] for _ in range(3)]
        check(v == ["sports"] * 3, f"a fixed pick in Settings (Sports) opens Sports every time ({v})")
        await pg.evaluate("document.querySelector('#settings-btn').click()"); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('input[name=deftab][value=random]').scrollIntoView({block: 'center'})"); await pg.click("#settings input[name=deftab][value=random]"); await pg.click("#settings-close")
        check(await pg.evaluate("localStorage.getItem('chisme-default-tab')") == "random", "…and back to Surprise me")
        s = await launch(pg)
        target = next(t for t in VIEWS if t != s["view"])
        await pg.evaluate(f"window.__chisme.goView('{target}', {{ instant: true }})"); await pg.wait_for_timeout(300)
        await pg.evaluate("window.__chisme.reloadHere()")   # the same path as the update / 'Refresh everyone' reloads
        await pg.wait_for_load_state("load"); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(400)
        s2 = await pg.evaluate(STATE)
        check(s2["view"] == target and s2["tab"] == target, f"Chisme's own reload stays on the tab you were on ({target} → {s2['view']})")
        s3 = await launch(pg)
        check(s3["view"] != target, f"…and the next real launch is random again, not that tab ({s3['view']})")
        check(not errs, f"no page errors ({errs[:2]})")
        await ctx.close(); await b.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
