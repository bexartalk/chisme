"""v49.12: the sync status pill ("Updating…", "Waking up the server…", "Couldn't update … Retry now", "✓ Updated 8:45 AM")
is a toast at the bottom, left of Tía. It must never cover the header (tab bar, Chisme bubble, tagline), Tía, or the one-time
Terms bar (that steps aside while the pill is up), and never clip its text. Android Chromium + iPhone WebKit; 320, 375, 390 and
430 px wide; light + dark; the Día de Muertos look on and off. Screenshots: /workspace/v49.12-review/sync/ (one per browser).
    ./venv/bin/python sync_pill_test.py   (needs the local server: ./run.sh)"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211/")
OUT = "/workspace/v49.12-review/sync"; os.makedirs(OUT, exist_ok=True)
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
STATES = [("busy", "Updating…", False), ("busy", "Waking up the server — this can take up to a minute. Your saved chisme is below.", False),
          ("fail", "Couldn't update (couldn't reach Chisme). Showing the saved copy; trying again in 30 s.", True), ("ok", "Updated 8:45 AM", False)]
MEASURE = """([state, text, retry]) => {
  const s = document.querySelector('#sync'); s.hidden = false; s.dataset.state = state; document.querySelector('#sync-msg').textContent = text;
  document.querySelector('#sync-retry').hidden = !retry; s.style.transition = 'none';
  const R = (e) => { if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
  const hit = (a, b) => !!(a && b) && a.l < b.r - 0.5 && b.l < a.r - 0.5 && a.t < b.b - 0.5 && b.t < a.b - 0.5;
  const p = R(s), m = document.querySelector('#sync-msg');
  const parts = { tabs: R(document.querySelector('#tabs')), header: R(document.querySelector('header')), bubble: R(document.querySelector('.brand-bubble')),
    tagline: R(document.querySelector('.tagline')), tia: R(document.querySelector('#tia-btn')), terms: getComputedStyle(document.querySelector('#terms-bar')).visibility === 'visible' ? R(document.querySelector('#terms-bar')) : null };
  const tb = document.querySelector('#terms-bar');
  return { p, over: Object.entries(parts).filter(([k, v]) => hit(p, v)).map(([k]) => k), on: p.l >= 0 && p.r <= innerWidth && p.t >= 0 && p.b <= innerHeight,
    clip: m.scrollWidth > m.clientWidth + 1 || s.scrollWidth > s.clientWidth + 1, h: Math.round(p.b - p.t), w: Math.round(p.r - p.l), vw: innerWidth,
    termsUp: !tb.hidden && getComputedStyle(tb).visibility === 'visible' };
}"""
async def main():
    async with async_playwright() as pw:
        for bname, bt, dev in (("android-chromium", pw.chromium, dict(is_mobile=True, has_touch=True, device_scale_factor=2.625)),
                               ("iphone-webkit", pw.webkit, dict(is_mobile=True, has_touch=True, device_scale_factor=3))):
            b = await bt.launch()
            for w, hgt in ((320, 640), (375, 667), (390, 844), (430, 932)):
                for theme in ("light", "dark"):
                    season = "muertos" if (w + (theme == "dark")) % 2 else "off"
                    for terms in (False, True):
                        ctx = await b.new_context(viewport={"width": w, "height": hgt}, color_scheme=theme, **dev)
                        await ctx.add_init_script(f"try{{localStorage.setItem('chisme-season-pin','{season}');localStorage.setItem('chisme-theme','{theme}');localStorage.setItem('chisme-default-tab','chisme');"
                                                  + ("" if terms else "localStorage.setItem('chisme-location-setup','1');") + "}catch(e){}")
                        await ctx.add_init_script(QUIET)
                        if terms: await ctx.add_init_script("try{localStorage.removeItem('chisme-terms-ok')}catch(e){}")
                        await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
                        pg = await ctx.new_page()
                        await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(700)
                        if terms:
                            if await pg.is_visible("#loc-close"): await pg.click("#loc-close"); await pg.wait_for_timeout(300)
                            if not await pg.evaluate("!document.querySelector('#terms-bar').hidden"): check(False, f"{bname} {w}: the Terms bar is up for this run"); await ctx.close(); continue
                        await pg.evaluate("scrollTo(0, 0)")
                        bad = []
                        for st in STATES:
                            r = await pg.evaluate(MEASURE, list(st))
                            if r["over"] or not r["on"] or r["clip"]: bad.append((st[0], st[1][:16], r["over"], r["on"], r["clip"], r["w"], r["h"]))
                            if terms and r["termsUp"]: bad.append((st[0], "the Terms bar stayed up under the pill"))
                        if terms:
                            await pg.evaluate("document.querySelector('#sync').dataset.state = 'done'"); await pg.wait_for_timeout(100)
                            back = await pg.evaluate("getComputedStyle(document.querySelector('#terms-bar')).visibility")
                            if back != "visible": bad.append(("done", "the Terms bar didn't come back", back))
                        tag = f"{bname} {w}px {theme}{' muertos' if season == 'muertos' else ''}{' + Terms bar' if terms else ''}"
                        check(not bad, f"{tag}: every sync state clear of the tab bar, header, Chisme bubble, tagline, Tía{' (the Terms bar steps aside while the pill is up, then comes back)' if terms else ''}; on screen, no clipped text {bad}")
                        if w == 390 and theme == "dark" and not terms:
                            await pg.evaluate(MEASURE, list(STATES[1])); await pg.screenshot(path=f"{OUT}/{bname}-390-dark-waking.png")
                        if w == 320 and theme == "light" and terms:
                            await pg.evaluate(MEASURE, list(STATES[2])); await pg.screenshot(path=f"{OUT}/{bname}-320-light-fail-terms-aside.png")
                        await ctx.close()
            await b.close()
asyncio.run(main())
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
