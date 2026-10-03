"""v49.12 review screenshots at 390×844 (iPhone WebKit, 3x), the Día de Muertos look on, light mode (plus a dark home):
/workspace/v49.12-review/NN-name.png.   ./venv/bin/python tools/review_shots.py   (local server: ./run.sh)"""
import asyncio, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
from playwright.async_api import async_playwright
import pw_csp  # noqa: F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211").rstrip("/")
OUT = os.environ.get("OUT", "/workspace/v49.12-review"); os.makedirs(OUT, exist_ok=True)
VP = {"width": 390, "height": 844}
DEV = dict(is_mobile=True, has_touch=True, device_scale_factor=3)
def seed(theme): return (f"try{{localStorage.setItem('chisme-theme','{theme}');localStorage.setItem('chisme-season-pin','muertos');localStorage.setItem('chisme-default-tab','chisme');"
                         "localStorage.setItem('chisme-juan-top10',JSON.stringify({at:1,rank:3,score:999}));localStorage.setItem('chisme-launch-last','weather');}catch(e){}")
async def ready(pg): await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
async def shot(pg, name): await pg.screenshot(path=f"{OUT}/{name}.png"); print("  ", name)
async def go(pg, h, wait=1500):
    await pg.evaluate(f"location.hash = '{h}'"); await pg.wait_for_timeout(wait); await pg.evaluate("scrollTo(0, 0)"); await pg.wait_for_timeout(300)
async def main():
    async with async_playwright() as pw:
        b = await pw.webkit.launch()
        # first launch: the location card, then the Terms bar once it's answered
        ctx = await b.new_context(viewport=VP, color_scheme="light", **DEV)
        await ctx.add_init_script(seed("light"))
        await ctx.add_init_script("try{localStorage.setItem('chisme-notif',JSON.stringify({n:1,shows:1}));localStorage.setItem('chisme-settings-tip','test:0');localStorage.removeItem('chisme-terms-ok')}catch(e){}")
        await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
        pg = await ctx.new_page(); await pg.goto(URL + "/"); await ready(pg); await pg.wait_for_timeout(2500)
        await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=20000)
        await shot(pg, "01-first-launch-location-card")
        await pg.click("#loc-close"); await pg.wait_for_selector("#terms-bar", state="visible"); await pg.evaluate("scrollTo(0, 0)"); await pg.wait_for_timeout(600)
        await shot(pg, "02-first-launch-terms-bar")
        await ctx.close()
        for theme in ("light", "dark"):
            ctx = await b.new_context(viewport=VP, color_scheme=theme, **DEV)
            await ctx.add_init_script(seed(theme)); await ctx.add_init_script(QUIET); await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
            await ctx.add_init_script("try{localStorage.setItem('chisme-location-setup','1');localStorage.setItem('chisme-swiped','1')}catch(e){}")
            pg = await ctx.new_page(); await pg.goto(URL + "/#chisme"); await ready(pg); await pg.wait_for_timeout(3000)
            await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=20000)
            if theme == "dark":
                await shot(pg, "03b-chisme-all-dark"); await ctx.close(); continue
            await shot(pg, "03-chisme-all-themed")
            await pg.evaluate("document.querySelector('#mix-list').scrollIntoView({block: 'start'}); scrollBy(0, -140)"); await pg.wait_for_timeout(600)
            await shot(pg, "04-chisme-all-feed-sticky-chips")
            await go(pg, "#weather"); await shot(pg, "05-weather")
            await go(pg, "#antojos", 2500); await shot(pg, "06-ofrendas-food")
            await go(pg, "#juegos"); await pg.evaluate("document.querySelector('.game-pick') && document.querySelector('#juegos').scrollIntoView({block: 'start'}); scrollBy(0, -90)"); await pg.wait_for_timeout(400)
            await shot(pg, "07-juegos")
            await go(pg, "#loteria"); await pg.locator("#view-juegos button", has_text="Start").first.click(); await pg.wait_for_timeout(5000)
            await shot(pg, "08-chismeria-orale")
            x = pg.locator(".gfs-x").first
            if await x.is_visible(): await x.click(); await pg.wait_for_timeout(600)
            await go(pg, "#juan"); await pg.locator(".juan-sk-btn").first.click(); await pg.wait_for_timeout(1200)
            await shot(pg, "09-juan-skin-picker")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
            await go(pg, "#chisme", 800)
            await pg.click("#tia-btn"); await pg.wait_for_timeout(700); await shot(pg, "10-tia-menu-hola-metiche")
            await pg.click("#tia-menu-chat"); await pg.wait_for_timeout(1200); await shot(pg, "11-tia-chat-hola-metiche")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
            await pg.click("#settings-btn"); await pg.wait_for_timeout(900); await shot(pg, "12-settings")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
            await pg.goto(URL + "/privacy"); await pg.wait_for_timeout(800); await shot(pg, "13-privacy")
            await pg.goto(URL + "/terms"); await pg.wait_for_timeout(800); await shot(pg, "14-terms")
            await ctx.close()
        await b.close()
asyncio.run(main())
