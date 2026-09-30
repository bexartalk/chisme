"""Donate (v32–v33): the Cash App card ($Slurmkaos) at the bottom of every tab, plus an inline card on every 5th app
open (5, 10, 15 …) in the middle of the tab Chisme opened on (about the 5th item), each time with a different line
from static/donatelines.js (never one of the last 5). Not a pop-up, never added on tab switches, stays put when that
list re-renders, ✕ hides it for the session. Node (the line picker) + WebKit, iPhone 13.
Screenshots: donate-every-tab.png (the bottom of all 6 tabs), donate-midfeed.png (News, mid-list card),
donate-lines.png (4 opens, 4 different lines)."""
import asyncio, io, json, os, subprocess
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
TEXT = "The tea ain’t free! Help a chismoso out — donate now!"
# test hook: /?t_opens=N sets the open counter (in the new document, before app.js) so the next open is N + 1
OPENS_INIT = """(() => { const m = /[?&]t_opens=(\\d+)/.exec(location.search); if (!m) return;
  localStorage.setItem('chisme-opens', m[1]); history.replaceState(null, '', location.pathname + location.hash); })()"""
UNIT = r"""
const D = require(process.argv[1]);
const out = { n: D.LINES.length, uniq: new Set(D.LINES).size, show: [...Array(21).keys()].filter(D.shouldShow) };
let recent = [], hist = [];
for (let k = 0; k < 600; k++) { const [i, r] = D.pick(recent); hist.push(i); recent = r; }
out.repeat = hist.some((i, k) => hist.slice(Math.max(0, k - 5), k).includes(i));
out.used = new Set(hist).size; out.recentLen = recent.length;
const mem = {}, store = { getItem: (k) => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = String(v); } };
out.launches = [...Array(20)].map(() => D.launch(store)).map((x) => [x.opens, x.line]);
console.log(JSON.stringify(out));
"""
def unit():
    print("== static/donatelines.js (Node)")
    r = subprocess.run(["node", "-e", UNIT, os.path.join(HERE, "static", "donatelines.js")], capture_output=True, text=True, timeout=60)
    if r.returncode: check(False, "node harness: " + r.stderr[-300:]); return []
    o = json.loads(r.stdout)
    check(o["n"] >= 20 and o["uniq"] == o["n"], f"{o['n']} different lines")
    check(o["show"] == [5, 10, 15, 20], f"shows on opens {o['show']} (every 5th)")
    check(not o["repeat"] and o["used"] == o["n"] and o["recentLen"] == 5, f"600 picks: never one of the last 5 lines, all {o['used']} lines get used")
    shown = [l for n, l in o["launches"] if l]
    check([n for n, l in o["launches"] if l] == [5, 10, 15, 20] and len(set(shown)) == 4, "launch(): counts opens, a line on 5/10/15/20, all different")
    return json.loads(subprocess.run(["node", "-e", "console.log(JSON.stringify(require(process.argv[1]).LINES))", os.path.join(HERE, "static", "donatelines.js")], capture_output=True, text=True).stdout)
LINES = []
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
    LINES.extend(unit())
    for ex in ["Tía's cafecito budget is running low ☕, help a chismosa out!", "This chisme ain't gonna spill itself. Tip the tea! 🫖", "Even the vecina pays for her novelas. Donate?", "Your donation keeps the rollers rolling 💇‍♀️"]:
        check(ex in LINES, f"example line in the set: {ex!r}")
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

        await ctx.close()
        print("\n== the mid-list card: every 5th open, a different line each time")
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(OPENS_INIT)
        pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        seen = []
        for n in range(1, 5):
            await (pg.goto(BASE + "/") if n == 1 else pg.reload()); await ready(pg)
            seen.append(((await pg.evaluate("__chisme.donateMid"))["opens"], (await pg.evaluate(MIDINFO))["n"]))
        check(seen == [(1, 0), (2, 0), (3, 0), (4, 0)], f"opens 1–4: no card ({seen})")
        await pg.reload(); await ready(pg)
        dm = await pg.evaluate("__chisme.donateMid"); m = await pg.evaluate(MIDINFO)
        check(dm["opens"] == 5 and m["n"] == 1 and m["view"] == "news" and m["list"] == "near-list" and m["storiesBefore"] == 5, f"open 5: one card in Near You, after the 5th story ({m.get('storiesBefore')})")
        check(m["text"] == dm["line"] and dm["line"] in LINES and m["href"] == "https://cash.app/$Slurmkaos" and m["x"], f"a line from the set, the Cash App button and a ✕ ({m['text']!r})")
        check(not m["dialog"] and not m["fixed"] and not await pg.evaluate("[...document.querySelectorAll('dialog')].some(d => d.open)"), "inline in the list: not a pop-up or modal")
        lines = [dm["line"]]; tiles = [Image.open(io.BytesIO(await pg.locator("#donate-mid").screenshot()))]
        await pg.evaluate("() => { const c = document.getElementById('donate-mid'); window.scrollTo(0, c.getBoundingClientRect().top + scrollY - 330); }"); await pg.wait_for_timeout(600); await pg.wait_for_timeout(4500)
        await pg.screenshot(path=os.path.join(OUT, "donate-midfeed.png"))
        for v in TABS[1:] + ["news"]:
            await pg.evaluate(f"__chisme.goView('{v}', {{ instant: true }})"); await pg.wait_for_timeout(1500 if v in ("sports", "events") else 400)
        m2 = await pg.evaluate(MIDINFO)
        check(m2["n"] == 1 and m2["view"] == "news", "switching through every tab doesn't add another")
        await pg.evaluate("__chisme.refreshNow()"); await pg.wait_for_timeout(6000)
        m3 = await pg.evaluate(MIDINFO)
        check(m3["n"] == 1 and m3["storiesBefore"] == 5 and m3["text"] == lines[0], "the News list re-renders: still one card, same line, still after the 5th story")
        await pg.evaluate("document.getElementById('donate-mid').scrollIntoView({ block: 'center' })")
        await pg.click("#donate-mid .donate-x"); await pg.wait_for_timeout(300)
        check((await pg.evaluate(MIDINFO))["n"] == 0 and (await pg.evaluate("__chisme.donateMid"))["dismissed"], "✕ dismisses it")
        await pg.reload(); await ready(pg)
        check((await pg.evaluate(MIDINFO))["n"] == 0 and (await pg.evaluate("__chisme.donateMid"))["opens"] == 6, "open 6: no card")
        # later 5th opens (new sessions): 10, 15, 20 → a different line each time
        for n in (10, 15, 20):
            p2 = await ctx.new_page(); p2.on("pageerror", lambda e: errs.append(str(e)[:160]))
            await p2.goto(BASE + f"/?t_opens={n - 1}"); await ready(p2)
            dm = await p2.evaluate("__chisme.donateMid"); m = await p2.evaluate(MIDINFO)
            check(dm["opens"] == n and m["n"] == 1 and m["text"] == dm["line"] and dm["line"] not in lines, f"open {n}: the card again, with a new line ({dm['line']!r})")
            lines.append(dm["line"]); tiles.append(Image.open(io.BytesIO(await p2.locator("#donate-mid").screenshot())))
            await p2.close()
        recent = json.loads(await pg.evaluate("localStorage.getItem('chisme-donate-recent')"))
        check(len(recent) == 4 and len(set(recent)) == 4, f"the last lines shown are remembered on the phone ({recent})")
        # donate-lines.png: 2 × 2 grid of the 4 different lines
        w = max(t.size[0] for t in tiles); h = max(t.size[1] for t in tiles)
        grid = Image.new("RGB", (w * 2 + 30, h * 2 + 30), "#f3f1ec")
        for i, t in enumerate(tiles): grid.paste(t, (10 + (i % 2) * (w + 10), 10 + (i // 2) * (h + 10)))
        grid.save(os.path.join(OUT, "donate-lines.png"))
        await ctx.close()
        # a 5th open that starts on Events → the card goes in the Events list
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(OPENS_INIT); await ctx.add_init_script("localStorage.setItem('chisme-default-tab', 'events')")
        pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/?t_opens=4"); await ready(pg, "#events-list .ev")
        m = await pg.evaluate(MIDINFO)
        check(m["n"] == 1 and m["view"] == "events" and m["list"] == "events-list", f"a 5th open on Events: the card is in the Events list ({m.get('view')}, {m.get('before')} items before it)")
        await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(600)
        check(await pg.evaluate("!document.querySelector('#view-news #donate-mid')"), "…and not in News after switching")
        await ctx.close()
        # a 5th open on Weather (#weather) → between the radar and the forecast
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(OPENS_INIT); pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/?t_opens=4#weather"); await ready(pg)
        where = await pg.evaluate("(() => { const c = document.getElementById('donate-mid'); return c && [c.previousElementSibling.id, c.nextElementSibling.id]; })()")
        check(where == ["radar-sec", "forecast-sec"], f"a 5th open on Weather: between the radar and the 7-day forecast ({where})")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
