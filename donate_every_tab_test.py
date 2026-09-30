"""Donate (v32): the Cash App card ($Slurmkaos) at the bottom of every tab, plus one inline "Enjoying the chisme?"
card per launch in the middle of the tab Chisme opened on (about the 5th item). It's not a pop-up, never added on
tab switches, stays put when that list re-renders, and ✕ hides it for the session. WebKit, iPhone 13.
Screenshots: donate-every-tab.png (the bottom of all 6 tabs), donate-midfeed.png (News, mid-list card)."""
import asyncio, io, os
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
TEXT = "The tea ain’t free! Help a chismoso out — donate now!"
MID = "Enjoying the chisme? ☕ Donate for more (and better) chisme!"
TABS = ["news", "sports", "weather", "antojos", "juegos", "events"]
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

LAST = """(v) => { const view = document.getElementById('view-' + v), kids = [...view.children].filter(n => n.id !== 'donate-mid'), last = kids[kids.length - 1], a = last && last.querySelector('.donate-btn');
  return { isDonate: !!(last && last.matches('.card.donate')), text: last && last.querySelector('.donate-text').textContent, href: a && a.href, target: a && a.target, tag: last && last.querySelector('.donate-tag').textContent }; }"""
MIDINFO = """() => { const c = document.getElementById('donate-mid'); if (!c) return { n: 0 };
  const list = c.parentElement, prev = [...list.children].slice(0, [...list.children].indexOf(c));
  const a = c.querySelector('.donate-btn'), x = c.querySelector('.donate-x');
  return { n: document.querySelectorAll('#donate-mid, .donate-mid').length, view: c.closest('.view').dataset.view, list: list.id, before: prev.filter(n => n.matches('.story, .ev, :not(.ev-day)')).length,
    storiesBefore: prev.filter(n => n.matches('.story')).length, text: c.querySelector('.donate-text').textContent, href: a.href, x: x && x.getAttribute('aria-label'),
    dialog: !!c.closest('dialog'), fixed: getComputedStyle(c).position === 'fixed' }; }"""

async def ready(pg, sel="#near-list .story"):
    await pg.wait_for_function(f"window.__chisme && __chisme.ready && document.querySelector('{sel}')", timeout=120000); await pg.wait_for_timeout(1500)

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/"); await ready(pg)
        print("== the donate card at the bottom of every tab")
        tiles = []
        for v in TABS:
            await pg.evaluate(f"__chisme.goView('{v}', {{ instant: true }})"); await pg.wait_for_timeout(2500 if v in ("sports", "antojos", "events") else 900)
            d = await pg.evaluate(LAST, v)
            check(d["isDonate"] and d["text"] == TEXT and d["href"] == "https://cash.app/$Slurmkaos" and d["target"] == "_blank" and d["tag"] == "$Slurmkaos", f"{v}: the last thing is the Cash App donate card")
            await pg.evaluate(f"document.querySelector('#view-{v} > .donate:last-child').scrollIntoView({{ block: 'end' }}); window.scrollBy(0, 40)"); await pg.wait_for_timeout(500)
            tiles.append(Image.open(io.BytesIO(await pg.screenshot())))
        cards = await pg.evaluate("[...document.querySelectorAll('.donate:not(.donate-mid)')].map(d => d.closest('.view') ? d.closest('.view').dataset.view : '?')")
        sett = await pg.evaluate("document.querySelectorAll('dialog .donate-btn').length")
        check(sorted(cards) == sorted(TABS) and sett == 1, f"exactly one per tab ({cards}); Settings still has just its own one ({sett})")
        # stitch: 3 × 2 grid, labeled
        W, H = tiles[0].size; s = 0.34; tw, th = int(W * s), int(H * s)
        try: FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except OSError: FONT = ImageFont.load_default()
        grid = Image.new("RGB", (tw * 3 + 40, (th + 60) * 2 + 20), "white"); dr = ImageDraw.Draw(grid)
        for i, (v, im) in enumerate(zip(TABS, tiles)):
            x, y = 10 + (i % 3) * (tw + 10), 10 + (i // 3) * (th + 60)
            grid.paste(im.resize((tw, th)), (x, y + 44)); dr.rectangle([x - 1, y + 43, x + tw, y + 44 + th], outline="black", width=2)
            dr.text((x + 6, y + 8), ["News", "Sports", "Weather", "¿Cuál dieta?", "Juegos", "Events"][i], fill="black", font=FONT)
        grid.save(os.path.join(OUT, "donate-every-tab.png"))

        print("\n== once per launch, mid-list")
        await pg.goto(BASE + "/"); await ready(pg)
        m = await pg.evaluate(MIDINFO)
        check(m["n"] == 1 and m["view"] == "news" and m["list"] == "near-list" and m["storiesBefore"] == 5, f"launch on News: one card in Near You, after the 5th story ({m.get('storiesBefore')})")
        check(m["text"] == MID and m["href"] == "https://cash.app/$Slurmkaos" and m["x"], f"text, Cash App button and a ✕ ({m['text']!r})")
        check(not m["dialog"] and not m["fixed"] and not await pg.evaluate("[...document.querySelectorAll('dialog')].some(d => d.open)"), "inline in the list: not a pop-up or modal")
        await pg.evaluate("() => { const c = document.getElementById('donate-mid'); window.scrollTo(0, c.getBoundingClientRect().top + scrollY - 330); }"); await pg.wait_for_timeout(600)
        await pg.screenshot(path=os.path.join(OUT, "donate-midfeed.png"))
        for v in TABS[1:] + ["news"]:
            await pg.evaluate(f"__chisme.goView('{v}', {{ instant: true }})"); await pg.wait_for_timeout(1500 if v in ("sports", "events") else 400)
        m2 = await pg.evaluate(MIDINFO)
        check(m2["n"] == 1 and m2["view"] == "news", "switching through every tab doesn't add another")
        await pg.evaluate("__chisme.refreshNow()"); await pg.wait_for_timeout(6000)
        m3 = await pg.evaluate(MIDINFO)
        check(m3["n"] == 1 and m3["storiesBefore"] == 5, "the News list re-renders: still one card, still after the 5th story")
        await pg.evaluate("document.getElementById('donate-mid').scrollIntoView({ block: 'center' })")
        await pg.click("#donate-mid .donate-x"); await pg.wait_for_timeout(300)
        check((await pg.evaluate(MIDINFO))["n"] == 0 and (await pg.evaluate("__chisme.donateMid"))["dismissed"], "✕ dismisses it")
        await pg.reload(); await ready(pg)
        check((await pg.evaluate(MIDINFO))["n"] == 0, "…for the rest of the session (a reload doesn't bring it back)")
        await ctx.close()
        # a new launch (new session) that opens on Events → the card goes in the Events list
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script("localStorage.setItem('chisme-default-tab', 'events')")
        pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/"); await ready(pg, "#events-list .ev")
        m = await pg.evaluate(MIDINFO)
        check(m["n"] == 1 and m["view"] == "events" and m["list"] == "events-list", f"a new launch that opens on Events: the card is in the Events list ({m.get('view')}, {m.get('before')} items before it)")
        await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(600)
        check(await pg.evaluate("!document.querySelector('#view-news #donate-mid')"), "…and not in News after switching")
        await ctx.close()
        # a launch on Weather (#weather) → between the radar and the forecast
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/#weather"); await ready(pg)
        where = await pg.evaluate("(() => { const c = document.getElementById('donate-mid'); return c && [c.previousElementSibling.id, c.nextElementSibling.id]; })()")
        check(where == ["radar-sec", "forecast-sec"], f"a launch on Weather: between the radar and the 7-day forecast ({where})")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
