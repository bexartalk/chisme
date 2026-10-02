"""Greeting card: '¡Buenos días / Buenas tardes / Buenas noches, chismosos!' by the place's time of day, the fixed
line under it, no chismoso/chismosa toggle (home card or Settings), the old saved choice ignored and cleared,
and the short swipe hint fitting in ≤ 2 lines at 390 and 320 px. WebKit, iPhone 13.
Screen: greeting-chismosos.png"""
import asyncio, os, sys
from datetime import datetime, timezone
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
URL = os.environ.get("URL", "http://localhost:8211/")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
SUB = "Pull up a chair, grab the tea, here’s the latest chisme."
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
# a returning v23 user who had picked "chismosa"
INIT = ("if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1');"
        " localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-greeting-word','chismosa'); }")
STATE = """() => { const h = document.querySelector('#swipe-hint'), cs = getComputedStyle(h);
  return { hi: document.querySelector('#greet-hi').textContent, sub: document.querySelector('#greet-sub').textContent,
    toggle: !!document.querySelector('.greet-switch, [data-word], input[name=greet]'), saved: localStorage.getItem('chisme-greeting-word'),
    hint: h.hidden ? null : { text: h.textContent, lines: Math.round(h.getBoundingClientRect().height / parseFloat(cs.lineHeight)) },
    overflow: document.documentElement.scrollWidth > innerWidth } }"""

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        # San Antonio (Central time): 9 AM, 3 PM, 9 PM, 2 AM
        for utc, want in ((datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc), "¡Buenos días, chismosos!"),
                          (datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc), "¡Buenas tardes, chismosos!"),
                          (datetime(2026, 9, 30, 2, 0, tzinfo=timezone.utc), "¡Buenas noches, chismosos!"),
                          (datetime(2026, 9, 30, 7, 0, tzinfo=timezone.utc), "¡Buenas noches, chismosos!")):
            ctx = await b.new_context(**dev); await ctx.add_init_script(INIT)
            pg = await ctx.new_page(); await pg.clock.set_system_time(utc)
            await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
            r = await pg.evaluate(STATE)
            check(r["hi"] == want, f"{utc:%H:%M} UTC ({(utc.hour - 5) % 24}:00 CT): '{r['hi']}'")
            check(r["sub"] == SUB, f"line under it is exactly '{SUB}' ({r['sub']!r})")
            await ctx.close()
        for w in (390, 320):
            d = dict(dev); d["viewport"] = {"width": w, "height": 844}; d["screen"] = {"width": w, "height": 844}
            ctx = await b.new_context(**d); await ctx.add_init_script(INIT); pg = await ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
            r = await pg.evaluate(STATE)
            check(not r["toggle"], f"{w} px: no chismoso/chismosa toggle on the home card")
            check(r["saved"] is None and "chismosos" in r["hi"], f"{w} px: saved 'chismosa' choice ignored and cleared ({r['saved']!r}, '{r['hi']}')")
            check(r["hint"] and r["hint"]["lines"] <= 2 and not r["overflow"], f"{w} px: swipe hint fits in ≤ 2 lines ({r['hint']})")
            await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
            st = await pg.evaluate("() => ({ open: document.querySelector('#settings').open, greet: !!document.querySelector('#settings input[name=greet]'), legends: [...document.querySelectorAll('#settings legend')].map(l => l.textContent) })")
            check(st["open"] and not st["greet"] and "Greet me as" not in st["legends"], f"{w} px: Settings has no 'Greet me as' ({st['legends']})")
            await pg.click("#settings-close"); await pg.wait_for_timeout(400)
            if w == 390:
                try: await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=15000)
                except Exception: pass
                await pg.wait_for_timeout(1200)
                await pg.screenshot(path=os.path.join(OUT, "greeting-chismosos.png"), clip={"x": 0, "y": 0, "width": 390, "height": 560})
            check(not errs, f"{w} px: no page errors ({errs[:2]})")
            await ctx.close()
        await b.close()
    print("ALL PASS" if not fails else f"{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
