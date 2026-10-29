"""v49.29: every Puro Pinche Lowrider ride (the 3 cars + lifted pickup, lowrider pickup, monster truck, tank, fighter jet, cowboy on a horse)
at 390px: a v1/v2 save with no new fields still loads; each ride shows locked with its Feria price in the Garage, unlocks with Feria
(saved), equips, and plays 10 s (autopilot hops, hitboxes clear obstacles) with no console errors. Screenshots (VEHICLE_SHOTS) at scale 3:
select-<id>.png (Garage) and play-<id>.png (mid-run)."""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: F401

BASE = os.environ.get("CHISME_URL", "http://localhost:8486")
OUT = os.environ.get("VEHICLE_SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")); os.makedirs(OUT, exist_ok=True)
NEW = {"lifted": 1600, "lowtruck": 1800, "horse": 2000, "monster": 3200, "tank": 4500, "jet": 6000,
       "paleta": 1200, "c10": 2200, "raspa": 2600, "bruja": 2800, "chariot": 3600, "ofrenda": 3900, "fiesta": 4200, "barge": 5200}   # v49.29.1: 8 more
INIT = ("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');"
        " localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1'); localStorage.setItem('chisme-settings-tip','dismissed');")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

async def open_game(pg):
    await pg.goto(BASE + "/#juegos"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await pg.wait_for_timeout(300)
    await pg.click('.game-pick[data-game="lowrider"]'); await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current && ChismeLowrider.current.state", timeout=30000)
    await pg.wait_for_timeout(1200)

async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        ctx = await br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True, is_mobile=True)
        # an old v2 save from before v49.28/v49.29 (no music / flame / new rides): it must still load, with its Feria and '64
        old = {"v": 2, "feria": 60000, "best": 1200, "owned": {"car": ["primer", "64"], "paint": ["candy"]}, "equip": {"car": "64", "paint": "candy"},
               "carPaint": {}, "stage": "blvd", "ach": {}, "runs": [], "totals": {}, "laps": {}, "howto": True, "muted": True}
        await ctx.add_init_script(INIT + f" if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded','1'); localStorage.setItem('lowrider_v1', {json.dumps(json.dumps(old))}); }}")
        pg = await ctx.new_page(); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
        await open_game(pg)
        s = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
        check(s and s.get("feria") == 60000 and "64" in s["owned"]["car"] and s["equip"]["car"] == "64", "an old v2 save loads (Feria, the candy '64 equipped)")
        cars = await pg.evaluate("ChismeLowrider.CARS ? ChismeLowrider.CARS.map(c => [c.id, c.price]) : null")
        check(cars and {c[0] for c in cars} >= set(NEW) | {"primer", "64", "jefe"}, f"all rides are in CARS {cars}")
        check(cars and all(dict(cars).get(k) == v for k, v in NEW.items()), "new ride prices")
        for cid in ["primer", "64", "jefe"] + list(NEW):
            errs.clear()
            await pg.click('.lr-ov [data-act="garage"]'); await pg.wait_for_timeout(400)
            await pg.click(f'.lr-car[data-id="{cid}"]'); await pg.wait_for_timeout(500)
            if cid in NEW or cid == "jefe":   # the old save owns the Primer + the candy '64; El Jefe (2400) unlocks here too
                txt = await pg.evaluate("document.querySelector('.lr-ov').textContent")
                price = NEW.get(cid, 2400); check(f"{price:,}" in txt or str(price) in txt, f"{cid}: locked with its price ({price} Feria)")
                await pg.click('.lr-ov [data-act="buycar"]'); await pg.wait_for_timeout(400)
                check(cid in (await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))"))["owned"]["car"], f"{cid}: unlocked with Feria (saved)")
                await pg.click(f'.lr-car[data-id="{cid}"]'); await pg.wait_for_timeout(300)
            eq = await pg.query_selector('.lr-ov [data-act="equip"]')
            if eq: await eq.click(); await pg.wait_for_timeout(300)
            check((await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))"))["equip"]["car"] == cid, f"{cid}: equipped")
            await pg.wait_for_timeout(900); await pg.screenshot(path=os.path.join(OUT, f"select-{cid}.png"))
            await pg.click('.lr-ov [data-act="title"]'); await pg.wait_for_timeout(300)
            await pg.keyboard.press("Enter"); await pg.wait_for_timeout(300)
            if await pg.evaluate("ChismeLowrider.current.state.mode") != "run": await pg.keyboard.press("Enter"); await pg.wait_for_timeout(300)
            await pg.evaluate("ChismeLowrider.current.debug.auto(true)")
            await pg.wait_for_timeout(9000)
            st = await pg.evaluate("(() => { const s = ChismeLowrider.current.state; return { mode: s.mode, lives: s.lives }; })()")
            await pg.screenshot(path=os.path.join(OUT, f"play-{cid}.png"))
            check(st["mode"] == "run", f"{cid}: still cruising after 10 s on autopilot ({st})")
            check(not errs, f"{cid}: no console errors {errs[:3]}")
            await pg.evaluate("ChismeLowrider.current.debug.auto(false); ChismeLowrider.current.debug.end()"); await pg.wait_for_timeout(1200)
            await pg.evaluate("(() => { const b = document.querySelector('.lr-ov [data-act=\"title\"]'); if (b) b.click(); })()"); await pg.wait_for_timeout(500)
        await br.close()
    print("FAILS:", fails); sys.exit(1 if fails else 0)
asyncio.run(main())
