"""Donate (v32–v33): the Cash App card ($Slurmkaos) at the bottom of every tab, plus an inline card on every 5th app
open (5, 10, 15 …) in the middle of the tab Chisme opened on (about the 5th item), each time with a different line
from static/donatelines.js (never one of the last 5). Not a pop-up, never added on tab switches, stays put when that
list re-renders, ✕ hides it for the session. Node (the line picker) + WebKit, iPhone 13.
v34: never next to a serious story (crime, death, crashes, fires, missing, urgent, NWS): the nearest slot with two light
neighbors, else the end of the tab just above the bottom donate card.
Screenshots: donate-every-tab.png (the bottom of all 6 tabs), donate-midfeed.png (News, mid-list card),
donate-lines.png (4 opens, 4 different lines)."""
import asyncio, io, json, os, re, subprocess
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
require(process.argv[1].replace("donatelines.js", "newsorder.js"));
const heavy = ["Man dies after crash on Loop 410", "Shooting leaves one dead on the East Side", "Stabbing near the plaza", "Police: murder suspect arrested",
  "Missing teen found safe", "Abuse case goes to trial", "House fire displaces family", "Victim identified", "Fatal wreck on I-35",
  "Man charged in theft", "Death of a local legend", "Two killed in collision", "BREAKING: road closed downtown", "Tornado Warning issued for Bexar County",
  "Flash flood warning until 6 PM", "Muere motociclista en la 281"];
const light = ["New conchas at the panadería", "Fiesta medals drop Friday", "Spurs win at home", "Enjoy free fall events downtown",
  "Former chef opens new omakase", "Cafecito spot opens on Broadway", "Library adds Sunday hours", "Weather: sunny and warm this weekend"];
out.heavy = heavy.filter((t) => !D.serious(t)); out.light = light.filter((t) => D.serious(t));
out.nws = D.serious("Heat advisory in effect", "") && D.serious("Hot weekend ahead", "National Weather Service");
const f = (s) => [...s].map((c) => c === "x");
out.slots = [D.slot(f("........")), D.slot(f("....x...")), D.slot(f("...xx...")), D.slot(f("x.x.x.x.x.x")), D.slot(f("xxxxxx")), D.slot(f(".")), D.slot(f("..x"))];
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
    check(not o["heavy"], f"serious(): dies, crash, shooting, stabbing, murder, missing, abuse, fire, victim, fatal, arrested, charged, death, killed, BREAKING, NWS warnings… ({o['heavy']})")
    check(not o["light"], f"serious(): light stories stay light ({o['light']})")
    check(o["nws"], "serious(): NWS advisories and National Weather Service items")
    # slot k = between item k and k+1; default ~5th (middle of a short list); nearest light-light slot; 0 = no slot → the end
    check(o["slots"] == [4, 3, 6, 0, 0, 0, 1], f"slot(): nearest slot with two light neighbors, else the end ({o['slots']})")
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

# the card's neighbors: the nearest story before and after it in its list, and what follows it
NEIGH = """() => { const c = document.getElementById('donate-mid'); if (!c) return null; const k = [...c.parentElement.children];
  const i = k.indexOf(c), st = (n) => n && n.matches('.story, .ev') ? n : null;
  const before = k.slice(0, i).reverse().find(st), after = k.slice(i + 1).find(st), t = (n) => n ? n.querySelector('h3').textContent : null;
  return { before: t(before), after: t(after), next: c.nextElementSibling && c.nextElementSibling.id, list: c.parentElement.id,
    serious: [before, after].map((n) => !!n && ChismeDonate.serious(n.querySelector('h3').textContent + ' ' + ((n.querySelector('.sum') || {}).textContent || ''), (n.querySelector('.src') || {}).textContent)) }; }"""
LIGHT = ["New mural brightens a Southtown alley", "Panadería on Nogalitos adds pumpkin conchas", "Library adds Sunday hours downtown",
         "Fiesta medal makers show off this year's designs", "Cafecito spot opens on Broadway", "Spurs host fan night at the plaza",
         "Community garden harvest party this weekend", "Mariachi students win state competition", "Food truck park adds live music",
         "River Walk lights get a fall refresh"]
def near_titles(heavy_at=(), all_heavy=False):
    def fn(j):
        for i, it in enumerate(j.get("near") or []):
            it["title"] = ("Man arrested after downtown shooting" if (all_heavy or i in heavy_at) else LIGHT[i % len(LIGHT)] + f" ({i + 1})")
            it["summary"] = ""
    return fn
async def news_route(ctx, fn):
    async def h(route):
        r = await route.fetch(); j = await r.json(); fn(j); await route.fulfill(response=r, json=j)
    await ctx.route(re.compile(r"/api/news\\?"), h)

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
        sett = await pg.evaluate("document.querySelectorAll('dialog .donate-btns').length")
        check(sorted(cards) == sorted(TABS) and sett == 1, f"exactly one per tab ({cards}); Settings still has just its own one ({sett})")
        print("\n== ☕ Buy Me a Coffee next to Cash App in every donate card")
        BTNS = """() => [...document.querySelectorAll('.donate:not(#donate-mid), #set-donate')].map((c) => { const bs = [...c.querySelectorAll('.donate-btns > a.donate-btn')];
          return { id: c.id, btns: bs.map((a) => [a.className.replace('donate-btn', '').trim(), a.getAttribute('href'), a.target, a.rel, a.textContent.replace(a.querySelector('.sr-only')?.textContent || '', '').trim()]),
            bg: bs[1] && getComputedStyle(bs[1]).backgroundColor, fg: bs[1] && getComputedStyle(bs[1]).color, h: bs[1] && Math.round(bs[1].getBoundingClientRect().height || 0) }; })"""
        cards = await pg.evaluate(BTNS)
        ids = sorted(c["id"] for c in cards)
        want = [["cashapp", "https://cash.app/$Slurmkaos", "_blank", "noopener noreferrer", "💸 Donate on Cash App"], ["bmc", "https://buymeacoffee.com/Chismoso", "_blank", "noopener noreferrer", "☕ Buy Me a Coffee"]]
        check(len(cards) == 7 and all(c["btns"] == want for c in cards), f"every donate card (6 tabs + Settings: {ids}) has 💸 Cash App then ☕ Buy Me a Coffee → buymeacoffee.com/Chismoso")
        check(all(c["bg"] == "rgb(255, 130, 0)" and c["fg"] == "rgb(0, 0, 0)" for c in cards), f"BMC button: Fiesta orange with black text, not BMC yellow ({cards[0]['bg']} / {cards[0]['fg']})")
        # the in-app reader leaves both alone (they open outside Chisme); a story link is still caught
        res = await pg.evaluate("""() => { const out = {}; const rec = (e) => { out[e.target.closest('a').getAttribute('href')] = e.defaultPrevented; e.preventDefault(); };
          document.addEventListener('click', rec); for (const h of ['https://cash.app/$Slurmkaos', 'https://buymeacoffee.com/Chismoso', 'https://www.buymeacoffee.com/Chismoso']) {
            const a = document.createElement('a'); a.href = h; a.textContent = 'x'; document.body.append(a); a.click(); a.remove(); }
          document.querySelector('#donate-news .donate-btn.bmc').click(); document.querySelector('#near-list .story h3 a').click();
          document.removeEventListener('click', rec); return out; }""")
        story = [k for k in res if k not in ("https://cash.app/$Slurmkaos", "https://buymeacoffee.com/Chismoso", "https://www.buymeacoffee.com/Chismoso")]
        check(res.get("https://buymeacoffee.com/Chismoso") is False and res.get("https://www.buymeacoffee.com/Chismoso") is False and res.get("https://cash.app/$Slurmkaos") is False,
              f"in-app reader exceptions: Cash App and Buy Me a Coffee links open outside Chisme ({ {k: v for k, v in res.items() if k not in story} })")
        check(story and res[story[0]] is True, "…while a story link still opens in the in-app reader")
        await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())"); await pg.wait_for_timeout(300)
        # donate-bmc.png: the News donate card, light | dark, + the Settings one
        await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(500)
        tl = Image.open(io.BytesIO(await pg.locator("#donate-news").screenshot()))
        await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelector('#set-donate').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(300)
        ts = Image.open(io.BytesIO(await pg.locator("#set-donate").screenshot()))
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        await pg.evaluate("localStorage.setItem('chisme-theme', 'dark'); document.documentElement.dataset.theme = 'dark'"); await pg.wait_for_timeout(300)
        td = Image.open(io.BytesIO(await pg.locator("#donate-news").screenshot()))
        dk = await pg.evaluate("(() => { const b = getComputedStyle(document.querySelector('#donate-news .donate-btn.bmc')); return [b.backgroundColor, b.borderTopColor]; })()")
        check(dk == ["rgb(255, 130, 0)", "rgb(255, 130, 0)"], f"dark mode: the BMC button keeps its orange ({dk})")
        await pg.evaluate("localStorage.setItem('chisme-theme', 'light'); document.documentElement.dataset.theme = 'light'")
        w = max(tl.size[0] + td.size[0] + 30, ts.size[0] + 20); h = max(tl.size[1], td.size[1]) + ts.size[1] + 30
        grid = Image.new("RGB", (w, h), "#888"); grid.paste(tl, (10, 10)); grid.paste(td, (tl.size[0] + 20, 10)); grid.paste(ts, (10, max(tl.size[1], td.size[1]) + 20))
        grid.save(os.path.join(OUT, "donate-bmc.png"))
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
        w = dm["where"] or {}; nb = await pg.evaluate(NEIGH)
        check(dm["opens"] == 5 and m["n"] == 1 and m["view"] == "news", f"open 5: one card in News (today's real stories: {w.get('serious')} of {w.get('n')} in Near You look serious)")
        if w.get("k"):
            check(m["list"] == "near-list" and m["storiesBefore"] == w["k"] and nb["serious"] == [False, False], f"…after story {w['k']}, both neighbors light: {nb['before']!r} / {nb['after']!r}")
        else:
            check(nb["next"] == "donate-news", f"…no light-light slot today, so it's at the end, just above the bottom donate card ({nb['next']})")
        spot0 = (m["list"], m["storiesBefore"], nb["next"])
        check(m["text"] == dm["line"] and dm["line"] in LINES and m["href"] == "https://cash.app/$Slurmkaos" and m["x"], f"a line from the set, the Cash App button and a ✕ ({m['text']!r})")
        check(await pg.evaluate("[...document.querySelectorAll('#donate-mid .donate-btns > a')].map(a => a.getAttribute('href')).join(' ')") == "https://cash.app/$Slurmkaos https://buymeacoffee.com/Chismoso", "…and ☕ Buy Me a Coffee next to it")
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
        nb3 = await pg.evaluate(NEIGH)
        w3 = (await pg.evaluate("__chisme.donateMid"))["where"] or {}
        light3 = (m3["list"] == "near-list" and m3["storiesBefore"] == w3.get("k") and nb3["serious"] == [False, False]) or (not w3.get("k") and nb3["next"] == "donate-news")
        check(m3["n"] == 1 and m3["text"] == lines[0] and light3, f"pull-to-refresh re-orders News: still one card, same line, and it re-checks its neighbors (now after story {w3.get('k')}: {nb3['before']!r} / {nb3['after']!r})")
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
        print("\n== never next to a serious story (controlled Near You titles)")
        for heavy_at, all_heavy, want, what in [((), False, 5, "all light → after the 5th story"),
                                                ((4,), False, 6, "5th story serious → moves to after the 6th (6th & 7th light)"),
                                                ((4, 5), False, 7, "5th & 6th serious → the nearest light pair: after the 7th"),
                                                ((3, 4, 5, 6), False, 8, "4th–7th serious → after the 2nd and after the 8th are equally near; the tie goes later: the 8th"),
                                                ((), True, 0, "every story serious → the end, just above the bottom donate card")]:
            c2 = await b.new_context(**dev, service_workers="block"); await c2.add_init_script(INIT); await c2.add_init_script(OPENS_INIT)
            await news_route(c2, near_titles(heavy_at, all_heavy))
            p2 = await c2.new_page(); p2.on("pageerror", lambda e: errs.append(str(e)[:160]))
            await p2.goto(BASE + "/?t_opens=4"); await ready(p2)
            m = await p2.evaluate(MIDINFO); nb = await p2.evaluate(NEIGH); dm = await p2.evaluate("__chisme.donateMid")
            if want:
                ok = m["n"] == 1 and m["list"] == "near-list" and m["storiesBefore"] == want and nb["serious"] == [False, False]
            else:
                ok = m["n"] == 1 and nb["next"] == "donate-news" and dm["where"]["k"] == 0 and nb["list"] == "view-news"
            check(ok, f"{what} ({m.get('storiesBefore')} stories before; {nb['before']!r} / {nb['after']!r}; next: {nb['next']})")
            if heavy_at == (4,):
                await p2.evaluate("() => { const c = document.getElementById('donate-mid'); window.scrollTo(0, c.getBoundingClientRect().top + scrollY - 330); }")
            if all_heavy:
                await p2.evaluate("__chisme.refreshNow()"); await p2.wait_for_timeout(5000)
                check((await p2.evaluate(NEIGH))["next"] == "donate-news" and (await p2.evaluate(MIDINFO))["n"] == 1, "…and stays there when News re-renders")
            await c2.close()

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
