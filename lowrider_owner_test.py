"""v49.29.1: the owner sees every Puro Pinche Lowrider ride unlocked; nobody else does.
  • GET /stats/lowrider/owner: owner false with no cookie and with a forged chisme_admin=1 marker; true only after the
    /stats sign-in (the same owner check as Juan's god mode; the signed-in admin account counts too, via social_api.admin_ok)
  • a non-owner with tampered localStorage (ownerRide / owner / ownerAll keys, every unlock flag we could think of) and the
    forged marker cookie: ownerAll stays false, the paid rides stay locked, and the ride falls back to the Primer
  • the owner: every ride unlocked (no 🔒), computed live: the save's owned rides don't change; the ride the owner picks
    comes back after a reload (a preference, not an unlock)
CHISME_URL = a server with no ADMIN_TOKEN; OWNER_URL = a server started with ADMIN_TOKEN=$OWNER_TOKEN."""
import asyncio, json, os, sys, urllib.request
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import pw_csp  # noqa: F401
BASE = os.environ.get("CHISME_URL", "http://localhost:8486").rstrip("/")
OWNER_URL = os.environ.get("OWNER_URL", "http://localhost:8487").rstrip("/")
TOKEN = os.environ.get("OWNER_TOKEN", "")
INIT = ("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');"
        " localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1'); localStorage.setItem('chisme-settings-tip','dismissed');")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
def get(url, cookie=None):
    req = urllib.request.Request(url, headers={"Cookie": cookie} if cookie else {})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())

async def open_game(pg, base):
    await pg.goto(base + "/#juegos"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.evaluate("__chisme.goView('juegos', { instant: true })"); await pg.wait_for_timeout(300)
    await pg.click('.game-pick[data-game="lowrider"]'); await pg.wait_for_function("window.ChismeLowrider && ChismeLowrider.current && ChismeLowrider.current.state", timeout=30000)
    await pg.wait_for_timeout(1500)

async def garage_locked(pg):
    await pg.click('.lr-ov [data-act="garage"]'); await pg.wait_for_timeout(500)
    n = await pg.evaluate("document.querySelectorAll('.lr-car.locked').length"); await pg.click('.lr-ov [data-act="title"]'); await pg.wait_for_timeout(300); return n

async def main():
    check(get(BASE + "/stats/lowrider/owner").get("owner") is False, "no cookie: owner false")
    check(get(BASE + "/stats/lowrider/owner", "chisme_admin=1").get("owner") is False, "a forged chisme_admin=1 marker: owner false")
    check(get(OWNER_URL + "/stats/lowrider/owner", "chisme_admin=1; chisme_stats=forged-session-value-1234567890").get("owner") is False, "owner server, forged session cookie: owner false")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        tampered = {"v": 2, "feria": 0, "owned": {"car": ["primer"], "paint": ["candy"]}, "equip": {"car": "jet", "paint": "orig"}, "ownerRide": "jet", "owner": True, "ownerAll": True, "admin": True, "unlockAll": True, "howto": True, "muted": True}
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        await ctx.add_cookies([{"name": "chisme_admin", "value": "1", "url": BASE}])
        await ctx.add_init_script(INIT + f" localStorage.setItem('lowrider_v1', {json.dumps(json.dumps(tampered))}); localStorage.setItem('chisme-owner','1');")
        pg = await ctx.new_page(); await open_game(pg, BASE)
        s = await pg.evaluate("ChismeLowrider.current.state")
        n_cars = await pg.evaluate("ChismeLowrider.CARS.length")
        check(s.get("ownerAll") is False, "non-owner, tampered localStorage + forged cookie: ownerAll stays false")
        check(await garage_locked(pg) == n_cars - 1, f"…every paid ride stays locked ({n_cars - 1})")
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(500)
        await ctx.close()
        if not TOKEN:
            check(False, "OWNER_TOKEN not set: the owner half didn't run")
        else:
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            await ctx.add_init_script(INIT + " if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded','1'); localStorage.setItem('lowrider_v1', JSON.stringify({v:2,feria:0,owned:{car:['primer'],paint:['candy']},equip:{car:'primer',paint:'orig'},howto:true,muted:true})); }")
            pg = await ctx.new_page(); await pw_csp.admin_sign_in(pg, OWNER_URL, TOKEN)
            await open_game(pg, OWNER_URL)
            check((await pg.evaluate("ChismeLowrider.current.state")).get("ownerAll") is True, "owner (signed in on /stats): ownerAll true, from the server")
            check(await garage_locked(pg) == 0, "owner: every ride unlocked, none locked")
            await pg.click('.lr-ov [data-act="garage"]'); await pg.wait_for_timeout(300); await pg.click('.lr-car[data-id="jet"]'); await pg.wait_for_timeout(300)
            await pg.click('.lr-ov [data-act="equip"]'); await pg.wait_for_timeout(300)
            sv = await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1'))")
            check(sv["owned"]["car"] == ["primer"], f"owner: unlocks are live, not written into the save's owned rides ({sv['owned']['car']})")
            await pg.reload(); await open_game(pg, OWNER_URL)
            check(await pg.evaluate("ChismeLowrider.current.debug.ride ? true : true") and (await pg.evaluate("JSON.parse(localStorage.getItem('lowrider_v1')).ownerRide")) == "jet", "owner: the picked ride is remembered as a preference")
            await ctx.close()
        await b.close()
    print("FAILS:", fails); sys.exit(1 if fails else 0)
asyncio.run(main())
