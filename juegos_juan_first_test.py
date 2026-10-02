"""v47: The Juan That Got Away is the first game in Juegitos and the one it opens on (ahead of Lotería Chismosa; Ice Ice
Bebé was replaced by Juan in v44). WebKit, iPhone 13: tapping the 🎲 Juegitos tab opens Juan (title screen); the list reads
Juan, then Lotería; #juan-that-got-away (and #juan) still open Juan, #loteria still opens Lotería; tapping Lotería in the
list still works, and Juan → Lotería → Juan → ▶ Start shows one full-screen bar (the first Juan's click handler is removed). Screenshot: juegos-juan-first.png (Juegitos as it opens, 390×844)."""
import asyncio, os
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = """localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');
localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1');
try { window.speechSynthesis && (speechSynthesis.speak = () => {}); } catch (e) {}"""
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

async def ready(pg, url):
    await pg.goto(url); await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(600)

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev, service_workers="block"); await ctx.add_init_script(INIT)
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await ready(pg, BASE + "/")
        await pg.click("#tabs .tab[data-view=juegos]")
        await pg.wait_for_function("__chisme.view === 'juegos' && __chisme.juegos && __chisme.juegos.id", timeout=15000); await pg.wait_for_timeout(900)
        s = await pg.evaluate("""() => ({ id: __chisme.juegos.id, list: [...document.querySelectorAll('.game-pick b')].map((b) => b.textContent),
          pressed: [...document.querySelectorAll('.game-pick[aria-pressed=true]')].map((b) => b.dataset.game), juan: !!document.querySelector('#game-stage #juan-cv'),
          lot: !!document.querySelector('#game-stage #lot-tabla') })""")
        check(s["id"] == "juan" and s["juan"] and not s["lot"], f"tapping 🎲 Juegitos opens The Juan That Got Away ({s['id']})")
        check(s["list"][:2] == ["The Juan That Got Away", "Lotería Chismosa"] and s["pressed"] == ["juan"], f"Juan first in the list, selected ({s['list']})")
        check(not any("Ice Ice" in g for g in s["list"]), "no Ice Ice Bebé entry (replaced by Juan in v44)")
        await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
        try: await pg.wait_for_function("document.querySelector('#sync').hidden", timeout=12000)
        except Exception: pass
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "juegos-juan-first.png"))
        await pg.click('.game-pick[data-game="loteria"]'); await pg.wait_for_timeout(500)
        check(await pg.evaluate("__chisme.juegos.id") == "loteria" and await pg.evaluate("!!document.querySelector('#lot-tabla')"), "tapping Lotería Chismosa still opens it")
        await pg.click('.game-pick[data-game="juan"]'); await pg.wait_for_timeout(500)   # Juan → Lotería → Juan again: the old Juan is fully gone
        await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(1000)
        f = await pg.evaluate("(() => { const c = document.querySelector('#juan-cv').getBoundingClientRect(); return { bars: document.querySelectorAll('#game-stage .gfs-bar').length, w: c.width, iw: innerWidth }; })()")
        check(f["bars"] == 1 and f["w"] >= 0.9 * f["iw"], f"Juan → Lotería → Juan, ▶ Start: one full-screen bar, the game fills the width ({f})")
        await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
        for h, want in (("#juan-that-got-away", "juan"), ("#juan", "juan"), ("#loteria", "loteria"), ("#juegos", "juan")):
            await ready(pg, BASE + "/" + h)
            try: await pg.wait_for_function(f"__chisme.view === 'juegos' && __chisme.juegos && __chisme.juegos.id === '{want}'", timeout=10000); ok = True
            except Exception: ok = False
            check(ok, f"{h} opens Juegitos → {want} ({await pg.evaluate('__chisme.juegos && __chisme.juegos.id')})")
        check(not errs, f"no page errors ({errs[:2]})")
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)

asyncio.run(main())
