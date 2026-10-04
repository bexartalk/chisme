"""v49.15.3: the square "From Chisme" card after every 5th post in the Chisme feed (All, News, Sports, Events).
  • a card right after posts 5, 10, 15 … in each list (posts only are counted: never the art cards, the day headings or
    the cards themselves), never right next to another promo card, a small "From Chisme" label, not a post itself
  • the App Store goal, worded "Help get Chisme on the App Store, $99", ☕ Buy Me a Coffee → https://buymeacoffee.com/Chismoso,
    and it opens inside Chisme (the in-app reader), not a new tab; 📣 Share Chisme → the phone's share sheet with the
    "Download Chisme" line and Chisme's link
  • the store app (window.ChismeNative set): no donate button, no goal, only Share
  • a refresh puts the cards back in the same slots (no doubles, none back to back); the "N new stories" pill counts
    new stories only, not the cards
  • square at phone size (390 and 320 px), no yellow (light, dark, Día de Muertos)
  • v49.15.3 first-donor shout-out on every card (store app too): a round La Jefa photo (static/site/la-jefa.webp, ≤ 30 KB,
    no EXIF/XMP, lazy, width/height set) + exactly "👑 First Donor: La Jefa, gracias for believing in Chisme", alt
    "La Jefa, Chisme's first donor", no real name. Screenshots (SHOTS): la-jefa-card.png, -dark, -muertos, -desktop
Screenshot: SHOTS/donate-card.png (390x844 phone), donate-card-native.png.
    URL=http://127.0.0.1:8321/ SHOTS=/workspace/chisme-smoothnav-shots ./venv/bin/python from_chisme_test.py"""
import ast, asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("URL", "http://localhost:8211/").rstrip("/") + "/"
OUT = os.environ.get("SHOTS", os.path.join(HERE, "screenshots")); os.makedirs(OUT, exist_ok=True)
_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
FAKE = """(() => { window.__shared = []; try { Object.defineProperty(navigator, 'share', { configurable: true, value: (d) => { __shared.push(d); return Promise.resolve(); } }); } catch (e) {} })()"""
POSTS = {"chisme": "#mix-list > .mix-item", "news": "#near-list > .story, #city-list > .story, #sa-list > .story",
         "sports": "#sports-body .sn-list > article.sn", "events": "#events-list > article.ev"}
# for one tab: the posts in page order, where each card sits (= how many posts come before it), its neighbours
WHERE = """([tab, sel]) => { const V = document.querySelector('#view-' + tab);
  const posts = [...V.querySelectorAll(sel)].filter((n) => !n.closest('[hidden]'));
  const cards = [...V.querySelectorAll('.from-chisme')];
  const before = (c) => posts.filter((p) => p.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING).length;
  const promo = (n) => !!n && n.matches('aside.donate, .donate-every, .from-chisme, #donate-mid');
  return { n: posts.length, at: cards.map(before), prevIsPost: cards.every((c) => posts.includes(c.previousElementSibling)),
    nextPromo: cards.some((c) => promo(c.nextElementSibling)), prevPromo: cards.some((c) => promo(c.previousElementSibling)),
    labels: cards.map((c) => (c.querySelector('.fc-label') || {}).textContent), notPost: cards.every((c) => !c.matches('.story, .mix-item, .sn, .ev, article')),
    aria: cards.every((c) => c.getAttribute('aria-label') === 'From Chisme'),
    bmc: cards.map((c) => { const a = c.querySelector('a.fc-bmc'); return a ? a.getAttribute('href') : null; }),
    titles: [...new Set(cards.map((c) => c.querySelector('.fc-t').textContent))], share: cards.every((c) => c.querySelector('button.fc-share')),
    e7: V.querySelectorAll('.donate-every').length }; }"""
SCAN = "(sel) => { " + YELLOW_JS + r""" const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const bad = []; let n = 0;
  for (const e of document.querySelectorAll(sel)) { if (!e.getClientRects().length) continue; n++; const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor, cs.fill]) if (rgb(v).some(yellow)) bad.push((e.className.baseVal ?? e.className) + ' ' + String(v).slice(0, 40)); }
  for (const e of document.querySelectorAll(sel.split(',')[0].trim())) { const cs = getComputedStyle(e, '::before'); if (rgb(cs.backgroundImage).some(yellow)) bad.push('::before ' + cs.backgroundImage.slice(0, 40)); }
  return { n, bad }; }"""

JEFA_TEXT = "👑 First Donor: La Jefa, gracias for believing in Chisme"; JEFA_ALT = "La Jefa, Chisme's first donor"
JEFA_JS = """() => [...document.querySelectorAll('.from-chisme')].map((c) => { const j = c.querySelector('.fc-jefa'), i = j && j.querySelector('img.fc-jefa-img'), t = j && j.querySelector('.fc-jefa-t');
  const r = i && i.getBoundingClientRect(), cs = i && getComputedStyle(i);
  return { ok: !!(j && i && t), text: t ? t.textContent : '', alt: i ? i.getAttribute('alt') : '', lazy: i ? i.getAttribute('loading') : '', w: i ? i.getAttribute('width') : '', h: i ? i.getAttribute('height') : '',
    src: i ? i.getAttribute('src') : '', round: cs ? cs.borderRadius : '', size: r ? Math.round(r.width) : 0, nextIsBtns: !!(j && j.nextElementSibling && j.nextElementSibling.matches('.fc-btns')) }; })"""
def jefa_ok(cards, where):
    good = [c for c in cards if c["ok"] and c["text"] == JEFA_TEXT and c["alt"] == JEFA_ALT and c["lazy"] == "lazy" and c["w"] and c["h"]
            and "/static/site/la-jefa.webp" in c["src"] and c["round"] == "50%" and c["nextIsBtns"]]
    check(cards and len(good) == len(cards), f"{where}: every From Chisme card has the La Jefa shout-out by the buttons (exact text + alt, lazy, sized) ({len(good)}/{len(cards)}) {cards[:1]}")
    seen = [c for c in cards if c["size"]]
    check(all(40 <= c["size"] <= 58 for c in seen), f"{where}: the photo is a small round one (44-56 px) {[c['size'] for c in seen][:3]}")

async def new_page(b, w=390, h=844, theme="light", season="off", native=False, tab="chisme", sw="allow"):
    ctx = await b.new_context(viewport={"width": w, "height": h}, color_scheme=theme, is_mobile=True, has_touch=True, device_scale_factor=3, service_workers=sw)
    await ctx.add_init_script(f"try{{localStorage.setItem('chisme-season-pin','{season}');localStorage.setItem('chisme-theme','{theme}');"
                              f"localStorage.setItem('chisme-default-tab','{tab}');localStorage.setItem('chisme-location-setup','1')}}catch(e){{}}"
                              + ("window.ChismeNative = { platform: 'ios' };" if native else ""))
    await ctx.add_init_script(QUIET); await ctx.add_init_script(FAKE)
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    await pg.wait_for_function("() => document.querySelectorAll('#mix-list .mix-item').length >= 10 && document.querySelectorAll('#near-list .story').length >= 5", timeout=90000)
    await pg.wait_for_function("() => document.querySelectorAll('#events-list article.ev').length >= 5 && document.querySelectorAll('#sports-body .sn-list > article.sn').length >= 5", timeout=90000)
    await pg.wait_for_timeout(900)
    return ctx, pg, errs

def want_at(n): return list(range(5, n + 1, 5))

async def slots(pg, label):
    res = {}
    for tab, sel in POSTS.items():
        w = await pg.evaluate(WHERE, [tab, sel]); res[tab] = w
        check(w["n"] >= 5 and w["at"] == want_at(w["n"]) and w["prevIsPost"], f"{label}: {tab}: a From Chisme card right after posts {want_at(w['n'])[:6]}… of {w['n']} (found after {w['at'][:6]}…)")
        check(not w["nextPromo"] and not w["prevPromo"] and w["e7"] == 0, f"{label}: {tab}: no card right next to another promo card (and no every-7 donate cards in the Chisme lists)")
    return res

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        print("== phone 390x844 (android-chromium)")
        ctx, pg, errs = await new_page(b)
        res = await slots(pg, "first render")
        w = res["chisme"]
        check(all(l == "From Chisme" for l in w["labels"]) and w["notPost"] and w["aria"], f"each card has a small 'From Chisme' label, is an <aside> labelled 'From Chisme', and isn't a post {w['labels'][:2]}")
        check(all(r["titles"] == ["Help get Chisme on the App Store, $99"] for r in res.values()), f"the goal reads exactly 'Help get Chisme on the App Store, $99' {w['titles']}")
        check(all(r["bmc"] and all(h == "https://buymeacoffee.com/Chismoso" for h in r["bmc"]) and r["share"] for r in res.values()),
              f"every card has ☕ Buy Me a Coffee → https://buymeacoffee.com/Chismoso and 📣 Share Chisme {w['bmc'][:1]}")
        box = await pg.evaluate("""() => { const c = document.querySelector('#view-chisme .from-chisme'), r = c.getBoundingClientRect(), l = c.querySelector('.fc-label').getBoundingClientRect(),
            logo = c.querySelector('.fc-logo svg'), btns = [...c.querySelectorAll('.fc-bmc, .fc-share')].map((x) => x.getBoundingClientRect());
          return { w: r.width, h: r.height, labelH: l.height, logo: !!logo && logo.getBoundingClientRect().width > 30, btn: Math.min(...btns.map((x) => x.height)), inside: btns.every((x) => x.bottom <= r.bottom && x.top >= r.top) }; }""")
        check(abs(box["w"] - box["h"]) <= 2 and box["labelH"] <= 24 and box["logo"] and box["btn"] >= 44 and box["inside"],
              f"390 px: the card is square ({box['w']:.0f}x{box['h']:.0f}), the label is small ({box['labelH']:.0f} px), the bubble logo shows, buttons are 44 px+ and inside the card")
        y = await pg.evaluate(SCAN, ".from-chisme, .from-chisme *")
        check(y["n"] > 8 and not y["bad"], f"light: no yellow in the card ({y['n']} elements) {y['bad'][:3]}")
        jefa_ok(await pg.evaluate(JEFA_JS), "390 px light")
        with open(os.path.join(HERE, "static", "site", "la-jefa.webp"), "rb") as f: wb = f.read()
        check(wb[:4] == b"RIFF" and wb[8:12] == b"WEBP" and len(wb) <= 30 * 1024 and b"EXIF" not in wb and b"XMP " not in wb,
              f"la-jefa.webp: a webp of {len(wb) // 1024} KB (≤ 30 KB), no EXIF / XMP metadata")
        body = await pg.evaluate("() => [...document.querySelectorAll('.from-chisme .fc-jefa')].map((j) => j.textContent + ' ' + j.querySelector('img').alt).join(' | ')")
        names = {w for part in body.split(" | ") for w in part.replace(",", " ").replace(":", " ").replace("'s", " ").split() if w[:1].isupper()}
        check(names <= {"First", "Donor", "La", "Jefa", "Chisme", "👑"}, f"no real name in the shout-out or its alt, only 'La Jefa' {sorted(names)}")
        c = pg.locator("#view-chisme .from-chisme").first; await c.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        await c.screenshot(path=f"{OUT}/la-jefa-card.png")
        # screenshot: the card in the feed, at phone size
        await pg.evaluate("() => { const c = document.querySelector('#view-chisme .from-chisme'); scrollTo({ top: c.getBoundingClientRect().top + scrollY - (innerHeight - c.offsetHeight) / 2, behavior: 'instant' }); }")
        await pg.wait_for_timeout(200); await pg.evaluate("window.__chismeNav.show()"); await pg.wait_for_timeout(500)
        await pg.screenshot(path=f"{OUT}/donate-card.png")
        # Share → the share sheet with the Download Chisme line and the link
        await pg.locator("#view-chisme .from-chisme .fc-share").first.click(); await pg.wait_for_timeout(400)
        sh = await pg.evaluate("[window.__shared, window.__chisme.fromChisme.share, window.__chisme.fromChisme.lastShare]")
        base = await pg.evaluate("(document.querySelector('meta[name=chisme-base]') || {}).content || location.origin")
        check(len(sh[0]) == 1 and sh[0][0]["text"].startswith("Download Chisme") and sh[0][0]["url"] == base.rstrip("/") + "/" and sh[0][0]["title"] == "Chisme" and sh[2] == "shared",
              f"📣 Share Chisme opens the phone's share sheet with the Download Chisme line and Chisme's link {sh[0]}")
        # Buy Me a Coffee → the in-app reader, not a new tab / leaving the app
        await ctx.route("**/api/reader*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps({"frame": False, "title": "Buy Me a Coffee"})))
        pages = len(ctx.pages); here = pg.url
        await pg.locator("#view-chisme .from-chisme .fc-bmc").first.click(); await pg.wait_for_timeout(700)
        rd = await pg.evaluate("() => ({ open: document.querySelector('#player').open, text: document.querySelector('#player').textContent.replace(/\\s+/g, ' ').slice(0, 300) })")
        check(rd["open"] and "Help get Chisme on the App Store" in rd["text"] and len(ctx.pages) == pages and pg.url == here,
              f"☕ Buy Me a Coffee opens inside Chisme (the in-app reader), no new tab, the page stays {rd['text'][:90]!r}")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        # a refresh: same slots, no doubles, none back to back
        for k in range(2):
            await pg.evaluate("() => { for (const t of ['chisme', 'news', 'sports', 'events']) window.__chisme.placeFrom(t); }")
        await pg.evaluate("document.querySelector('#set-refresh') && document.querySelector('#set-refresh').click()")
        await pg.wait_for_timeout(5000)
        await slots(pg, "after a refresh")
        check(not errs, f"no page errors {errs[:2]}")
        await ctx.close()

        # the "N new stories" pill counts stories, not cards
        print("\n== the new-stories pill")
        state = {"n": 0, "on": False}
        async def news_route(route):
            r = await route.fetch(); j = await r.json(); state["n"] += 1
            if state["on"] and j.get("near"):
                extra = []
                for i in range(2):
                    it = dict(j["near"][0]); it.update(title=f"Test new story {i + 1}", link=f"https://example.com/new-{i + 1}", published=(it.get("published") or 0) + 60 + i); extra.append(it)
                j["near"] = extra + j["near"]
            await route.fulfill(response=r, body=json.dumps(j), content_type="application/json")
        ctx, pg, errs = await new_page(b, tab="news", sw="block")   # (so the page's own fetches reach the route)
        await ctx.route("**/api/news*", news_route); state["on"] = True
        cards = await pg.evaluate("document.querySelectorAll('#view-news .from-chisme').length")
        await pg.evaluate("window.__chisme.checkNews()")
        await pg.wait_for_function("() => window.__chisme.newsPill.held", timeout=30000)
        p = await pg.evaluate("[window.__chisme.newsPill, document.querySelector('#news-pill').textContent]")
        check(cards >= 2 and p[0]["n"] == 2 and "2 new stories" in p[1], f"with {cards} From Chisme cards on the page, 2 new stories → the pill says 2 ({p[1]!r})")
        await ctx.close()

        print("\n== the store app (window.ChismeNative)")
        ctx, pg, errs = await new_page(b, native=True)
        nat = await pg.evaluate("""() => { const c = [...document.querySelectorAll('.from-chisme')]; return { n: c.length, bmc: document.querySelectorAll('.from-chisme a.fc-bmc, .from-chisme a[href*="buymeacoffee"]').length,
            money: c.filter((x) => /\\$\\d|coffee|donat/i.test(x.textContent)).length, share: c.every((x) => x.querySelector('button.fc-share')), native: window.__chisme.fromChisme.native }; }""")
        check(nat["native"] and nat["n"] >= 4 and nat["bmc"] == 0 and nat["money"] == 0 and nat["share"], f"ChismeNative set: the cards keep only 📣 Share Chisme (no Buy Me a Coffee, no $99 goal) {nat}")
        await slots(pg, "store app")
        jefa_ok(await pg.evaluate(JEFA_JS), "store app (no donate button, the shout-out stays)")
        c = pg.locator("#view-chisme .from-chisme").first
        await c.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        await c.screenshot(path=f"{OUT}/donate-card-native.png")
        await ctx.close()

        print("\n== 320 px, dark, Día de Muertos")
        for theme, season, w in (("light", "off", 320), ("dark", "off", 390), ("light", "muertos", 390), ("dark", "muertos", 390)):
            ctx, pg, errs = await new_page(b, w=w, h=740 if w == 320 else 844, theme=theme, season=season)
            box = await pg.evaluate("""() => { const c = document.querySelector('#view-chisme .from-chisme'), r = c.getBoundingClientRect(); return { w: r.width, h: r.height, over: c.scrollWidth > c.clientWidth + 1 }; }""")
            y = await pg.evaluate(SCAN, ".from-chisme, .from-chisme *")
            tag = f"{w} px {theme}{' + Día de Muertos' if season == 'muertos' else ''}"
            check(box["h"] <= box["w"] * 1.2 and not box["over"] and box["w"] <= w - 20, f"{tag}: the card stays (about) square and nothing spills sideways ({box['w']:.0f}x{box['h']:.0f})")
            check(y["n"] > 8 and not y["bad"], f"{tag}: no yellow in the card {y['bad'][:3]}")
            jefa_ok(await pg.evaluate(JEFA_JS), tag)
            shot = {("dark", "off"): "dark", ("light", "muertos"): "muertos"}.get((theme, season)) if w == 390 else None
            if shot:
                c = pg.locator("#view-chisme .from-chisme").first; await c.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
                await c.screenshot(path=f"{OUT}/la-jefa-card-{shot}.png")
            if theme == "dark" and season == "off":
                c = pg.locator("#view-chisme .from-chisme").first; await c.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
                await c.screenshot(path=f"{OUT}/donate-card-dark.png")
            await ctx.close()
        print("\n== desktop 1280 px")
        ctx, pg, errs = await new_page(b, w=1280, h=900)
        jefa_ok(await pg.evaluate(JEFA_JS), "desktop 1280 px")
        y = await pg.evaluate(SCAN, ".from-chisme, .from-chisme *")
        check(not y["bad"], f"desktop: no yellow in the card {y['bad'][:3]}")
        c = pg.locator("#view-chisme .from-chisme").first; await c.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        await c.screenshot(path=f"{OUT}/la-jefa-card-desktop.png")
        await ctx.close()
        await b.close()
    print("\n" + ("ALL OK" if not fails else f"{len(fails)} FAILED:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
