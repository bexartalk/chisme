"""v49.23 (audit): the notifications / "Add Chisme to your Home Screen first" card (#push-ask) never comes back on the same
open after "Not now". WebKit iPhone 13 (the Home Screen variant) + Chromium Pixel 7.
Usage: URL=http://localhost:8484/ ./venv/bin/python notif_notnow_test.py"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
URL = os.environ.get("URL", "http://localhost:8211/"); fails = []
INIT = "try { if (!sessionStorage.getItem('x')) { sessionStorage.setItem('x','1'); localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-terms-ok', String(Date.now())); localStorage.removeItem('chisme-notif'); } } catch (e) {}"
async def run(bt, dev, name):
    b = await bt.launch(**({"executable_path": "/usr/bin/google-chrome", "args": ["--no-sandbox"]} if bt.name == "chromium" else {}))
    ctx = await b.new_context(**dev, service_workers="block"); await ctx.add_init_script(INIT); pg = await ctx.new_page()
    # a local server has no VAPID keys (push off): pretend it's on, so the card is due like on the live site
    await pg.route("**/api/push/config", lambda r: r.fulfill(json={"enabled": True, "publicKey": "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U", "dailyMax": 2, "quiet": [22, 7]}))
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    try: await pg.wait_for_function("() => window.__chisme.notif.open", timeout=40000)
    except Exception:
        print(f"  skip {name}: the card wasn't due here ({await pg.evaluate('JSON.stringify(window.__chisme.notif)')})"); await b.close(); return
    kind = await pg.evaluate("window.__chisme.notif.kind")
    await pg.click("#push-ask-no"); seen = []
    for _ in range(20):
        await pg.wait_for_timeout(1000); seen.append(await pg.evaluate("window.__chisme.notif.open"))
    ok = not any(seen); print(("  ok   " if ok else "  FAIL ") + f"{name} ({kind}): stays closed for 20 s after Not now {seen}")
    if not ok: fails.append(name)
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p.webkit, p.devices["iPhone 13"], "WebKit iPhone 13"); await run(p.chromium, p.devices["Pixel 7"], "Chromium Pixel 7")
    print("PASS" if not fails else "FAIL"); sys.exit(1 if fails else 0)
asyncio.run(main())
