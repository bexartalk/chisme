"""News has no yellow (v36): no yellow/cream highlight or background on story cards, headlines, pills or marks
(no 'new', 'unread', 'lead' or <mark>-style highlight), in light and dark mode. The closest (Near You) stories keep a
subtle turquoise edge instead. WebKit, iPhone 13, against the local server. Screenshot: news-no-yellow.png
(light and dark side by side)."""
import asyncio, io, os, sys
from playwright.async_api import async_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "screenshots"); BASE = os.environ.get("BASE", "http://localhost:8211")
FAILS = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: FAILS.append(what)

# every element in News (+ the "New chisme" pill): background colors, gradient stops, <mark>s and headline text colors
SCAN = r"""() => {
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const yellow = ([r, g, b, a]) => { if (a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.04) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return h >= 25 && h <= 70 && s >= 0.3; };   // amber → yellow → cream (#fff0e0 counts)
  const els = [...document.querySelectorAll('#view-news, #view-news *, #news-pill')].filter((e) => e.getClientRects().length && !e.closest('.donate, .art-frame') && e.tagName !== 'IMG');
  const bad = [];
  for (const e of els) {
    const cs = getComputedStyle(e), what = (e.id ? '#' + e.id : '') + '.' + [...e.classList].join('.') + ' <' + e.tagName.toLowerCase() + '>';
    if (rgb(cs.backgroundColor).some(yellow)) bad.push(what + ' background ' + cs.backgroundColor);
    if (rgb(cs.backgroundImage).some(yellow)) bad.push(what + ' gradient ' + cs.backgroundImage.slice(0, 80));
    if (e.matches('.story, .story *') && rgb(cs.boxShadow).some(yellow)) bad.push(what + ' glow ' + cs.boxShadow.slice(0, 60));
    if (e.matches('.story h3, .story h3 *') && rgb(cs.color).some(yellow)) bad.push(what + ' headline color ' + cs.color);
  }
  const near = document.querySelector('#near-list .story.near'), ncs = near && getComputedStyle(near);
  return { n: els.length, stories: document.querySelectorAll('#view-news .story').length, marks: document.querySelectorAll('#view-news mark').length, bad: bad.slice(0, 12),
           near: near && { bg: ncs.backgroundColor, left: ncs.borderLeftColor, leftW: ncs.borderLeftWidth } };
}"""

async def main():
    shots = []
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        for theme in ("light", "dark"):
            print(f"== {theme} mode")
            ctx = await b.new_context(**dev, color_scheme=theme); await ctx.add_init_script(f"localStorage.setItem('chisme-theme', '{theme}')")
            pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)
            await pg.wait_for_timeout(1500)
            # also show the "New chisme" pill, so it's scanned too
            await pg.evaluate("document.getElementById('news-pill').hidden = false")
            r = await pg.evaluate(SCAN)
            check(await pg.evaluate("document.documentElement.dataset.theme") == theme, f"{theme} theme on")
            check(r["stories"] >= 5 and not r["bad"], f"no yellow/cream backgrounds, gradients, glows or headline colors on {r['stories']} stories ({r['n']} elements) {r['bad']}")
            check(r["marks"] == 0, "no <mark> highlights in News")
            nr = r["near"] or {}
            check(nr.get("left") == "rgb(0, 201, 205)", f"Near You stories: a turquoise edge instead ({nr})")
            await pg.evaluate("document.getElementById('news-pill').hidden = true")
            await pg.evaluate("() => { const s = document.querySelector('#near-list .story'); window.scrollTo(0, s.getBoundingClientRect().top + scrollY - 90); }")
            await pg.wait_for_timeout(4500)
            shots.append(Image.open(io.BytesIO(await pg.screenshot())))
            check(not errs, f"no page errors ({errs[:2]})")
            await ctx.close()
        await b.close()
    w, h = shots[0].size; out = Image.new("RGB", (w * 2 + 30, h + 20), "#888")
    for i, s in enumerate(shots): out.paste(s, (10 + i * (w + 10), 10))
    out.save(os.path.join(OUT, "news-no-yellow.png"))
    print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAILED")); sys.exit(1 if FAILS else 0)

asyncio.run(main())
