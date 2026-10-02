"""v48: Android (Chromium, Pixel 7, dark mode) — never a blank dark screen.
  1) A normal open boots (no "waking up" card, header + tab bar showing, no console errors). Screenshot: android-fix.png.
  2) Safety net: when app.js never arrives (the request hangs), a "Chisme is waking up… Tap to reload" card shows after
     ~8 s (inline styles, no yellow); tapping it clears the caches and reloads, and the app starts; the card goes away.
  3) The v47 bug: leaving the app during a full-screen game (Juan) left the game full screen with the header and tab bar
     hidden, and Android hands the canvas back blank after a long background, so the app reopened to an empty dark navy
     screen. Now leaving the app leaves full screen (paused, ▶ Resume, header + tabs back), and a restored canvas is redrawn.
  4) A full-screen class that outlived its game is cleared (header + tabs come back).
Against the local server (CHISME_URL, default http://localhost:8211)."""
import ast, asyncio, os
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = """localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');
localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1');
localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 }));   // v49: notif card + Settings tip have their own tests
if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"""
import re as _re
VER = _re.search(r'const VERSION = "chisme-v(\d+(?:\.\d+)?)"', open(os.path.join(HERE, "static", "sw.js")).read()).group(1)   # the current build
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const r = document.querySelector(root), bad = [];
  for (const e of [r, ...r.querySelectorAll('*')]) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push((e.id || e.tagName) + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
CHROME = """() => { const t = document.querySelector('#tabs'), r = t.getBoundingClientRect(); return { tabs: getComputedStyle(t).display !== 'none' && r.height > 20 && r.bottom > 0,
  fs: document.documentElement.classList.contains('game-fs'), gfs: !!document.querySelector('.game-stage.gfs'), booted: !!window.__chismeBooted, wake: !!document.querySelector('#wake'),
  build: window.CHISME_APP_BUILD }; }"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); dev = dict(p.devices["Pixel 7"]); dev.pop("default_browser_type", None)

        print("== 1) a normal open (Pixel 7, dark)")
        ctx = await b.new_context(**dev, color_scheme="dark"); await ctx.add_init_script(INIT)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160])); pg.on("console", lambda m: errs.append(m.text[:160]) if m.type == "error" else None)
        await pg.goto(BASE + "/?source=pwa"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
        await pg.wait_for_timeout(9000)
        s = await pg.evaluate(CHROME)
        check(s["booted"] and s["tabs"] and not s["wake"] and not s["fs"] and s["build"] == VER, f"boots: header + tab bar, no waking-up card, build {s['build']}")
        check(await pg.evaluate("document.querySelectorAll('#view-news .story').length") > 5, "News stories render")
        try: await pg.wait_for_function("document.querySelector('#sync').hidden", timeout=12000)
        except Exception: pass
        await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(500)
        await pg.screenshot(path=os.path.join(OUT, "android-fix.png"))

        print("\n== 3) leaving the app during a full-screen game")
        await pg.click(".tab[data-view=juegos]"); await pg.wait_for_function("__chisme.juegos && __chisme.juegos.id === 'juan'", timeout=15000); await pg.wait_for_timeout(600)
        await pg.click('#juan-ov [data-act="start"]'); await pg.wait_for_timeout(1200)
        s = await pg.evaluate(CHROME)
        check(s["fs"] and s["gfs"] and not s["tabs"], "▶ Start: full screen (header + tabs hidden, as before)")
        await pg.evaluate("Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' }); document.dispatchEvent(new Event('visibilitychange'))")
        await pg.wait_for_timeout(400)
        await pg.evaluate("Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' }); document.dispatchEvent(new Event('visibilitychange'))")
        await pg.wait_for_timeout(2500)
        s = await pg.evaluate(CHROME); st = await pg.evaluate("__chisme.juegos.game.state")
        ov = await pg.evaluate("document.querySelector('#juan-ov').innerText")
        check(not s["fs"] and not s["gfs"] and s["tabs"], f"back in the app: out of full screen, header + tab bar showing ({s})")
        check(st["mode"] == "paused" and "Resume" in ov, f"the game is paused with ▶ Resume ({st['mode']}, {ov!r})")
        # Android hands the canvas back blank: it must be redrawn
        px = "(() => { const c = document.querySelector('#juan-cv'), g = c.getContext('2d'), d = g.getImageData(0, 0, c.width, c.height).data; const s = new Set(); for (let i = 0; i < d.length; i += 4 * 997) s.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]); return s.size; })()"
        await pg.evaluate("(() => { const c = document.querySelector('#juan-cv'); c.width = c.width; })()")   # what a lost canvas looks like: blank
        blank = await pg.evaluate(px)
        await pg.evaluate("document.querySelector('#juan-cv').dispatchEvent(new Event('contextrestored'))"); await pg.wait_for_timeout(300)
        drawn = await pg.evaluate(px)
        check(blank <= 2 and drawn > 10, f"a canvas handed back blank is redrawn on contextrestored ({blank} → {drawn} colors)")
        await pg.evaluate("(() => { const c = document.querySelector('#juan-cv'); c.width = c.width; })()")
        await pg.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))"); await pg.wait_for_timeout(300)
        check(await pg.evaluate(px) > 10, "…and when the page is shown again (pageshow)")
        await pg.click('#juan-ov [data-act="resume"]'); await pg.wait_for_timeout(600)
        s = await pg.evaluate(CHROME)
        check(s["fs"] and s["gfs"], "▶ Resume goes back to full screen")
        await pg.click(".gfs-x"); await pg.wait_for_timeout(400)

        print("\n== 4) a full-screen class that outlived its game")
        await pg.evaluate("document.documentElement.classList.add('game-fs')")
        hidden = not (await pg.evaluate(CHROME))["tabs"]
        await pg.evaluate("__chismeWake.check()"); s = await pg.evaluate(CHROME)
        check(hidden and not s["fs"] and s["tabs"] and not s["wake"], "stale game-fs class removed: header + tabs back, no card (the app is running)")
        check(not errs, f"no console/page errors ({errs[:3]})")
        await ctx.close()

        print("\n== 2) app.js never arrives → 'Chisme is waking up…' after ~8 s")
        ctx = await b.new_context(**dev, color_scheme="dark", service_workers="block"); await ctx.add_init_script(INIT)
        hold = asyncio.Event()
        async def slow(route):
            if not hold.is_set():
                try: await asyncio.wait_for(hold.wait(), 60)
                except Exception: pass
            try: await route.continue_()
            except Exception: pass
        await ctx.route("**/static/app.js*", slow)
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/?source=pwa", wait_until="commit")
        await pg.wait_for_timeout(5000)
        early = await pg.evaluate("!!document.querySelector('#wake')")
        try: await pg.wait_for_selector("#wake", timeout=8000); shown = True
        except Exception: shown = False
        check(not early and shown, f"no card at 5 s, the card at ~8 s (early {early}, shown {shown})")
        w = await pg.evaluate("(() => { const c = document.querySelector('#wake'), b = document.querySelector('#wake-reload'), r = c.getBoundingClientRect(), br = b.getBoundingClientRect(); return { text: c.innerText.replace(/\\s+/g, ' '), full: r.width >= innerWidth - 1 && r.height >= innerHeight - 1, bh: br.height }; })()")
        check("Chisme is waking up…" in w["text"] and "Tap to reload" in w["text"] and w["full"] and w["bh"] >= 48, f"friendly full-screen card with a big button ({w['text'][:80]})")
        check(not await pg.evaluate(SCAN, "#wake"), "no yellow on the card")
        await pg.screenshot(path=os.path.join(OUT, "android-wake-card.png"))
        await pg.evaluate("caches.open('chisme-v%s-shell')" % VER + ".then((c) => c.put('/x-test', new Response('x')))")
        hold.set()
        await pg.click("#wake-reload")
        await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(1500)
        s = await pg.evaluate(CHROME)
        keys = await pg.evaluate("caches.keys()")
        check(s["booted"] and s["tabs"] and not s["wake"], "Tap to reload: the app starts and the card is gone")
        check(f"chisme-v{VER}-shell" not in keys, f"…and the saved app files were cleared first ({keys})")
        await ctx.close(); await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)

asyncio.run(main())
