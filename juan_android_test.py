"""v49.9 Juan on a tall Android phone (Chromium, Pixel-like 412×915 @2.625, touch): no more dark screen + blank teal bar.
  • Bug (live v49.8): in full screen the tab track loses its transform (so position:fixed works), and the hidden screen-reader
    labels (position:absolute) in the other tabs' strips were placed against the whole page, out to x≈15,800. Android Chrome
    widened the page, and the full-screen game with it: the game, its HUD and the Jump label sat off to the right.
  • Now: in full screen the page is exactly as wide as the screen; the game fills it, draws, the HUD + Jump label are on screen
  • The safety net: ~2 s after it starts, a game that's wider than the screen (the old CSS, simulated), has a 0-size canvas or a
    crashing frame shows "🔄 Tap to reload" on screen (100vw × 100vh), and tapping it reloads
Screenshot: screenshots/android-juan-fix.png. Run against a local server (CHISME_URL, default :8211)."""
import asyncio, os, sys
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
G = "__chisme.juegos.game"
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip','test:0');"
UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"
M = """() => { const R = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height }; };
  const cv = document.querySelector('#juan-cv'), c = cv.getContext('2d'), px = c.getImageData(0, 0, cv.width, Math.min(cv.height, 400)).data; let n = 0, s = new Set();
  for (let i = 0; i < px.length; i += 4 * 97) { s.add(px[i] >> 4 << 8 | px[i + 1] >> 4 << 4 | px[i + 2] >> 4); n++; }
  return { iw: innerWidth, ih: innerHeight, sw: document.documentElement.scrollWidth, fs: __chisme.juegos.game.state.fullscreen, mode: __chisme.juegos.game.state.mode, stage: R('#game-stage'), cv: R('#juan-cv'), jump: R('#juan-jump'), badge: R('.gfs-badge'), x: R('.gfs-x'),
    jumpTxt: document.querySelector('#juan-jump').textContent.trim(), colors: s.size, broken: !!document.querySelector('.game-broken') }; }"""
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
inside = lambda r, m: r and r["l"] >= -1 and r["r"] <= m["iw"] + 1 and r["t"] >= -1 and r["b"] <= m["ih"] + 1

async def page(b, init=""):
    ctx = await b.new_context(viewport={"width": 412, "height": 915}, device_scale_factor=2.625, is_mobile=True, has_touch=True, user_agent=UA)
    await ctx.add_init_script(SETUP + init); await ctx.add_init_script(QUIET)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:200])); pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
    await pg.goto(BASE + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game", timeout=120000); await pg.wait_for_timeout(600)
    return ctx, pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        print("== a tall Android phone: the game fills the screen")
        ctx, pg, errs = await page(b)
        await pg.tap("#juan-ov [data-act=start]"); await pg.wait_for_timeout(2600); m = await pg.evaluate(M)
        check(m["fs"] and m["mode"] == "run" and m["sw"] <= m["iw"] + 1, f"full screen: the page is as wide as the screen ({m['sw']} vs {m['iw']}; v49.8 was 15,837)")
        check(inside(m["stage"], m) and inside(m["cv"], m) and m["cv"]["w"] >= m["iw"] - 1 and m["cv"]["h"] > 600, f"the game and its canvas fill the screen ({m['cv']})")
        check(inside(m["jump"], m) and "Jump" in m["jumpTxt"] and inside(m["badge"], m) and inside(m["x"], m), f"the Jump button + label ({m['jumpTxt']!r}), the title badge and ✕ are on screen")
        check(m["colors"] > 20 and not m["broken"] and not errs, f"the canvas is drawn ({m['colors']} colours), no safety-net card, no errors {errs[:2]}")
        await pg.screenshot(path=os.path.join(OUT, "android-juan-fix.png")); await ctx.close()

        print("== the safety net")
        # the v49.8 layout bug, brought back on purpose: the full-screen page is wider than the screen
        ctx, pg, errs = await page(b, "document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = 'html.game-fs .views{position:static!important}'; document.head.appendChild(s); });")
        await pg.tap("#juan-ov [data-act=start]"); await pg.wait_for_timeout(2700); m = await pg.evaluate(M)
        r = await pg.evaluate("(() => { const e = document.querySelector('.game-broken'); if (!e) return null; const q = e.getBoundingClientRect(); return { l: q.left, r: q.right, t: q.top, b: q.bottom, txt: e.textContent.trim() }; })()")
        check(m["sw"] > m["iw"] + 100 and r and "Tap to reload" in r["txt"] and r["l"] >= -1 and r["r"] <= m["iw"] + 1, f"the old wide-page bug (simulated, {m['sw']}px) → '{r and r['txt']}' on screen ({r})")
        await pg.tap(".game-broken"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && !document.querySelector('.game-broken')", timeout=120000)
        check(True, "tapping it reloads the app")
        await ctx.close()
        # a 0-size canvas (it never shows)
        ctx, pg, errs = await page(b, "document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = '#juan-cv{display:none!important}'; document.head.appendChild(s); });")
        await pg.wait_for_timeout(2700)
        check(await pg.locator(".game-broken").count() == 1, "a canvas with no size → 'Tap to reload' ~2 s after the game opens (even before Start)")
        await ctx.close()
        # a frame that throws
        ctx, pg, errs = await page(b)
        await pg.tap("#juan-ov [data-act=start]"); await pg.wait_for_timeout(500)
        await pg.evaluate("(() => { const c = document.querySelector('#juan-cv').getContext('2d'), f = c.fillRect; c.fillRect = function () { throw new Error('boom (test)'); }; })()"); await pg.wait_for_timeout(600)
        check(await pg.locator(".game-broken").count() == 1, "a frame that crashes → 'Tap to reload' right away (not a frozen game)")
        await ctx.close()
        await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
