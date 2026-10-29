"""v49.28: every Juegos game (The Juan That Got Away, Chismería, Puro Pinche Lowrider) at 390px: a pick opens it full screen
(the stage covers the viewport, a ✕ sits in the top-right corner), it plays for 10 s (taps + keys) with no console errors,
and the ✕ exits back to the Juegos list. Screenshots (GAMES_SHOTS, default screenshots/) at device scale 3."""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: F401

BASE = os.environ.get("CHISME_URL", "http://localhost:8486")
OUT = os.environ.get("GAMES_SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")); os.makedirs(OUT, exist_ok=True)
INIT = ("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');"
        " localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1');")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

FS = """(() => { const s = document.querySelector('#view-juegos .game-stage.gfs, .gfs'); const x = document.querySelector('.gfs-x');
  if (!s || !x) return { ok: false }; const r = s.getBoundingClientRect(), xr = x.getBoundingClientRect();
  return { ok: true, cover: r.left <= 1 && r.top <= 1 && r.right >= innerWidth - 1 && r.bottom >= innerHeight - 1,
    xTopRight: xr.right >= innerWidth - 70 && xr.top <= 80 && xr.width >= 24, xVisible: getComputedStyle(x).visibility !== 'hidden' }; })()"""

async def play(pg, gid):
    box = await pg.evaluate("(() => { const r = document.querySelector('.gfs').getBoundingClientRect(); return [r.width, r.height]; })()")
    for i in range(20):   # 10 s of play
        if gid == "loteria":
            cells = await pg.query_selector_all(".lot-cell")
            if i == 0:
                b = await pg.query_selector("#lot-go, .lot-go, [data-act=start]")
                if b and await b.is_visible(): await b.click()
            if cells: await cells[i % len(cells)].click(force=True)
        elif gid == "lowrider":
            if i < 3 and await pg.evaluate("ChismeLowrider.current.state.mode") != "run":   # Enter starts (v49.28); a first run shows How to play
                await pg.keyboard.press("Enter"); await pg.wait_for_timeout(400); continue
            await pg.mouse.move(box[0] / 2, box[1] * 0.6); await pg.mouse.down(); await pg.wait_for_timeout(180); await pg.mouse.up()
            await pg.keyboard.press("Space")
        else:
            await pg.mouse.click(box[0] / 2, box[1] * 0.55); await pg.keyboard.press("ArrowUp")
        await pg.wait_for_timeout(500)

async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        for gid in ["juan", "loteria", "lowrider"]:
            ctx = await br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True, is_mobile=True)
            await ctx.add_init_script(INIT)
            pg = await ctx.new_page(); errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(BASE + "/#juegos"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
            await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await pg.wait_for_timeout(400)
            await pg.click(f'.game-pick[data-game="{gid}"]'); await pg.wait_for_timeout(2500)
            fs = await pg.evaluate(FS)
            check(fs.get("ok") and fs["cover"], f"{gid}: opens full screen at 390px")
            check(fs.get("ok") and fs["xTopRight"] and fs["xVisible"], f"{gid}: ✕ in the top-right corner")
            if gid == "lowrider": await pg.screenshot(path=os.path.join(OUT, "lowrider-title.png"))
            await play(pg, gid)
            if gid == "lowrider": check(await pg.evaluate("ChismeLowrider.current.state.mode") in ("run", "over", "crash"), "lowrider: Enter starts a run and it plays")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=os.path.join(OUT, f"{'lowrider-gameplay' if gid == 'lowrider' else gid}.png"))
            check(await pg.evaluate("!!document.querySelector('.gfs')"), f"{gid}: still full screen after 10 s of play")
            await pg.click(".gfs-x"); await pg.wait_for_timeout(500)
            check(await pg.evaluate("!document.querySelector('.gfs') && !!document.querySelector('.game-pick')"), f"{gid}: ✕ exits to the Juegos list")
            bad = [e for e in errs if "favicon" not in e and "net::ERR" not in e and "Failed to load resource" not in e]
            check(not bad, f"{gid}: no console errors {bad[:3]}")
            await ctx.close()
        await br.close()
    print("FAILS:", fails); sys.exit(1 if fails else 0)
asyncio.run(main())
