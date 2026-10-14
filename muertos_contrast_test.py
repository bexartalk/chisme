"""v49.23 Día de Muertos contrast sweep: every visible text element on every feed screen (Chisme, News, Sports, Events,
Weather, ¿Y la dieta?/Ofrendas, Juegos), light + dark, Chromium Pixel 7 + WebKit iPhone 13, must reach WCAG AA (4.5:1,
3:1 for large text) against the nearest solid background. The From Chisme donation card is checked by name.
Usage: URL=http://localhost:8484/ ./venv/bin/python muertos_contrast_test.py   (SHOT=path saves the From Chisme card)"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211/")
SHOT = os.environ.get("SHOT")
SWEEP = """(root) => { const lum = (c) => { const m = c.match(/[\\d.]+/g).map(Number); const s = /^color\\(srgb/.test(c);
    const f = (v) => { v = s ? v : v / 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
    return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]); };
  const alpha = (c) => { const a = c.match(/rgba\\([^)]*,\\s*([\\d.]+)\\)/) || c.match(/\\/\\s*([\\d.]+)\\s*\\)/); return a ? +a[1] : (/transparent/.test(c) ? 0 : 1); };
  const bgOf = (n) => { for (; n; n = n.parentElement) { const cs = getComputedStyle(n);
      if (cs.backgroundImage !== 'none' && /(url|gradient)\\(/.test(cs.backgroundImage) && n !== document.documentElement && n !== document.body) return null;   // photo: skip
      if (alpha(cs.backgroundColor) >= .5) return cs.backgroundColor; } return null; };
  const out = [];
  for (const n of root.querySelectorAll('*')) {
    if (!n.offsetParent || n.closest('[hidden],[inert],svg,.mq-gallery figure,.vf-slide,iframe')) continue;
    const own = [...n.childNodes].some(t => t.nodeType === 3 && t.textContent.trim()); if (!own) continue;
    const r = n.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(n); if (+cs.opacity < .3 || cs.visibility === 'hidden') continue;
    const bg = bgOf(n); if (!bg) continue;
    const a = lum(cs.color), b = lum(bg), ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const big = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.66 && +cs.fontWeight >= 700);
    if (ratio < (big ? 3 : 4.5)) out.push({ el: n.tagName.toLowerCase() + (n.className && typeof n.className === 'string' ? '.' + n.className.trim().split(/\\s+/).join('.') : '') + (n.id ? '#' + n.id : ''),
      text: n.textContent.trim().slice(0, 40), color: cs.color, bg, ratio: Math.round(ratio * 100) / 100 });
  }
  const seen = new Set(); return out.filter(o => { const k = o.el + o.color + o.bg; if (seen.has(k)) return false; seen.add(k); return true; }); }"""
VIEWS = [("chisme", None), ("news", "news"), ("sports", "sports"), ("events", "events"), ("weather", "weather"), ("antojos", None), ("juegos", None)]
fails = []

async def run(bt, dev, name, theme):
    b = await bt.launch(**({"executable_path": "/usr/bin/google-chrome", "args": ["--no-sandbox"]} if bt.name == "chromium" else {}))
    ctx = await b.new_context(**dev, timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
    await ctx.add_init_script(QUIET)
    await ctx.add_init_script(f"try {{ localStorage.removeItem('chisme-season-pin'); localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-default-tab','chisme'); localStorage.setItem('chisme-theme','{theme}'); }} catch (e) {{}}")
    pg = await ctx.new_page()
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    season = await pg.evaluate("document.documentElement.dataset.season || ''")
    if season != "muertos":
        await pg.evaluate("localStorage.setItem('chisme-season-pin','muertos')"); await pg.reload()
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    print(f"— {name} · {theme} · season={await pg.evaluate('document.documentElement.dataset.season')}")
    for v, chip in VIEWS:
        if chip:
            await pg.tap('#tabs .tab[data-view="chisme"]'); await pg.tap(f'.view.active .mq-chip[data-go="{chip}"]')
        else:
            await pg.locator(f'#tabs .tab[data-view="{v}"]').scroll_into_view_if_needed(); await pg.tap(f'#tabs .tab[data-view="{v}"]')
        await pg.wait_for_timeout(9000 if v in ("chisme", "events") else 4000)
        bad = await pg.evaluate(f"() => ({SWEEP})(document.querySelector('#view-{v}'))")
        for o in bad:
            fails.append(f"{name} {theme} {v}: {o}")
        print(("  ok   " if not bad else "  FAIL ") + f"{v}: {len(bad)} low-contrast text" + "".join(f"\n         {o}" for o in bad[:12]))
    # the From Chisme card by name
    await pg.tap('#tabs .tab[data-view="chisme"]'); await pg.tap('.view.active .mq-chip[data-go="chisme"]')
    await pg.wait_for_selector("#view-chisme .from-chisme", timeout=60000)
    fc = pg.locator("#view-chisme .from-chisme").first
    await fc.scroll_into_view_if_needed()
    bad = await pg.evaluate(f"() => ({SWEEP})(document.querySelector('#view-chisme .from-chisme'))")
    print(("  ok   " if not bad else "  FAIL ") + f"From Chisme card: {bad or 'all text AA'}")
    if bad: fails.append(f"{name} {theme} from-chisme {bad}")
    # audit v49.23: the Homies sign-in view ("‹ Back to the chisme", the pink Sign in button)
    await pg.evaluate("location.hash = '#s/signin'"); await pg.wait_for_selector(".sx-back", timeout=30000); await pg.wait_for_timeout(800)
    bad = await pg.evaluate(f"() => ({SWEEP})(document.querySelector('#sx-view') || document.body).filter(o => /sx-back|btn/.test(o.el))")
    print(("  ok   " if not bad else "  FAIL ") + f"Homies sign-in: back link + pink button {bad or 'AA'}")
    if bad: fails.append(f"{name} {theme} signin {bad}")
    await pg.evaluate("location.hash = ''"); await pg.wait_for_timeout(800)
    if SHOT and theme == "light" and bt.name == "webkit":
        await pg.wait_for_timeout(800); await fc.screenshot(path=SHOT)
    await b.close()

async def main():
    async with async_playwright() as p:
        for bt, dev, nm in ((p.chromium, p.devices["Pixel 7"], "Chromium Pixel 7"), (p.webkit, p.devices["iPhone 13"], "WebKit iPhone 13")):
            for th in ("light", "dark"):
                await run(bt, dev, nm, th)
    print("PASS" if not fails else f"FAIL ({len(fails)})"); sys.exit(1 if fails else 0)
asyncio.run(main())
