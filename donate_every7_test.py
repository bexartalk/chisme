"""v46: a donation reminder after every 7 posts in News and Events, and its own swipeable slide every 7 videos in the
full-screen For You food feed. Tia's voice, the Cash App ($Slurmkaos) + Buy Me a Coffee (Chismoso) buttons (they open
outside the app, never in the in-app reader), a Share Chisme button (navigator.share with the title Chisme, a line and
Chisme's address (v49.13: PUBLIC_BASE_URL, else the page's own); without it the link is copied and a "Link copied!" toast shows), the X hides them for the
session, never next to a serious story, no yellow. WebKit iPhone 13.
Screenshots: donate-news.png, donate-events.png, donate-food.png."""
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests
import asyncio, colorsys, os, re
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
# a recording share sheet + clipboard (headless browsers have neither)
FAKE = """(() => { window.__shared = []; window.__copied = [];
  try { Object.defineProperty(navigator, 'share', { configurable: true, value: (d) => { __shared.push(d); return Promise.resolve(); } }); } catch (e) {}
  try { Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (t) => { __copied.push(t); return Promise.resolve(); } } }); } catch (e) {} })()"""
URL = (os.environ.get("PUBLIC_BASE_URL") or BASE).rstrip("/") + "/"   # v49.13: the shared link is PUBLIC_BASE_URL, else the page's own address
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

def yellowish(css):
    m = re.findall(r"[\d.]+", css or "")
    if len(m) < 3 or (len(m) > 3 and float(m[3]) == 0): return False
    r, g, b = (float(x) / 255 for x in m[:3]); h, l, s = colorsys.rgb_to_hls(r, g, b)
    return s > 0.35 and 0.2 < l < 0.9 and 40 / 360 <= h <= 70 / 360

def spaced(at):   # about every 7 posts: 7 after the last one, sliding a few (or skipping a turn) to stay clear of serious stories
    return bool(at) and 5 <= at[0] <= 20 and all(5 <= b - a <= 16 for a, b in zip(at, at[1:])) and sum(b - a for a, b in zip(at, at[1:])) <= 10 * max(1, len(at) - 1)

CARD_JS = """(sel) => { const c = document.querySelector(sel); if (!c) return null; const r = c.getBoundingClientRect();
  const a = [...c.querySelectorAll('a.donate-btn')], sh = c.querySelector('.share-chisme'), x = c.querySelector('.donate-x');
  const cols = [c, ...c.querySelectorAll('*')].flatMap((n) => { const s = getComputedStyle(n); return [s.backgroundColor, s.color, s.borderTopColor]; });
  return { text: c.querySelector('.donate-text').textContent, links: a.map((l) => [l.getAttribute('href'), l.target, l.rel]), share: sh ? sh.textContent.trim() : null,
    shareH: sh ? sh.getBoundingClientRect().height : 0, x: x ? x.getAttribute('aria-label') : null, tag: !c.querySelector('.donate-tag') && (c.querySelector('a.donate-btn.cashapp .ca-tag') || {}).textContent,   /* v47: inside the button */ cols, w: r.width }; }"""
GO = "(i) => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: i * s.clientHeight, behavior: 'instant' }); }"

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev, service_workers="block"); await ctx.add_init_script(QUIET + INIT); await ctx.add_init_script(FAKE)
        await ctx.route(re.compile(r"https://(cash\.app|buymeacoffee\.com)/.*"), lambda r: r.fulfill(status=200, content_type="text/html", body="<p>donate page</p>"))
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.newsReady", timeout=120000); await pg.wait_for_timeout(800)
        print("== News")
        ev = await pg.evaluate("__chisme.every"); n_st = await pg.evaluate("document.querySelectorAll('#near-list .story, #city-list .story, #sa-list .story').length")
        cards = await pg.evaluate("document.querySelectorAll('#view-news .donate-every').length")
        check(n_st >= 14 and cards >= 2 and cards == len(ev["news"]) and spaced(ev["news"]), f"a donate card after about every 7th story ({n_st} stories, cards after {ev['news']})")
        gaps = await pg.evaluate("""() => { const all = [...document.querySelectorAll('#near-list > *, #city-list > *, #sa-list > *')], out = []; let k = 0;
          for (const n of all) { if (n.matches('.story')) k++; else if (n.matches('.donate-every')) out.push(k); } return out; }""")
        check(gaps == ev["news"], f"...counted across the News lists in order ({gaps})")
        heavy = await pg.evaluate("""() => [...document.querySelectorAll('#view-news .donate-every')].filter((c) => [c.previousElementSibling, c.nextElementSibling]
          .filter((n) => n && n.matches('.story')).some((n) => window.ChismeDonate.serious((n.querySelector('h3') || n).textContent + ' ' + ((n.querySelector('.sum') || {}).textContent || ''), (n.querySelector('.src') || {}).textContent || ''))).length""")
        check(heavy == 0, "never right next to a serious story")
        c = await pg.evaluate(CARD_JS, "#view-news .donate-every")
        check(c["links"] == [["https://cash.app/$Slurmkaos", "_blank", "noopener noreferrer"], ["https://buymeacoffee.com/Chismoso", "_blank", "noopener noreferrer"]] and c["tag"] == "$Slurmkaos",
              f"the same buttons as the other donate cards: Cash App $Slurmkaos + Buy Me a Coffee, opening outside ({c['links']})")
        check(c["share"] == "📣 Share Chisme" and c["shareH"] >= 44 and c["x"] == "Dismiss these for now", f"...a Share Chisme button next to them and an X ({c['share']!r}, {c['shareH']:.0f} px)")
        lines = await pg.evaluate("[...document.querySelectorAll('.donate-every .donate-text')].map(p => p.textContent)")
        check(all(len(t) <= 110 for t in lines) and all(a != b for a, b in zip(lines, lines[1:])) and len(set(lines)) == min(5, len(lines)), f"short, a different line on each card in turn ({lines[:2]})")
        bad = [x for x in c["cols"] if yellowish(x)]
        check(not bad, f"no yellow in the card ({bad[:3]})")
        await pg.evaluate("document.querySelector('#view-news .donate-every').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(500)
        await pg.screenshot(path=os.path.join(OUT, "donate-news.png"))
        await pg.click("#view-news .donate-every .share-chisme"); await pg.wait_for_timeout(300)
        sh = await pg.evaluate("__shared")
        check(len(sh) == 1 and sh[0]["title"] == "Chisme" and sh[0]["url"] == URL and 10 < len(sh[0]["text"]) <= 90, f"Share Chisme -> navigator.share: title Chisme, a witty line, {URL} ({sh})")
        await pg.evaluate("Object.defineProperty(navigator, 'share', { configurable: true, value: undefined })")
        await pg.click("#view-news .donate-every .share-chisme"); await pg.wait_for_timeout(300)
        cp = await pg.evaluate("__copied"); toast = await pg.evaluate("(() => { const t = document.querySelector('#share-toast'); return { shown: !t.hidden, text: t.textContent, bg: getComputedStyle(t).backgroundColor }; })()")
        check(cp == [URL] and toast["shown"] and toast["text"] == "Link copied!" and not yellowish(toast["bg"]), f"no share sheet: the link is copied and a 'Link copied!' toast shows ({cp}, {toast})")
        async with ctx.expect_page() as newp:
            await pg.click("#view-news .donate-every a.donate-btn.cashapp")
        np = await newp.value; await np.wait_for_load_state()
        rd = await pg.evaluate("[...document.querySelectorAll('dialog')].filter(d => d.open).map(d => d.id)")
        check(np.url.startswith("https://cash.app/$Slurmkaos") and not rd, f"Donate on Cash App opens outside the app, not in the reader ({np.url}, open dialogs {rd})")
        await np.close()
        print("== Events")
        await pg.evaluate("__chisme.goView('events', { instant: true })")
        await pg.wait_for_function("__chisme.eventsReady", timeout=90000); await pg.wait_for_timeout(1500)
        ev = await pg.evaluate("__chisme.every"); n_ev = await pg.evaluate("document.querySelectorAll('#events-list article.ev').length")
        evc = await pg.evaluate("document.querySelectorAll('#view-events .donate-every').length")
        check(n_ev > 7 and evc >= 1 and evc == len(ev["events"]) and spaced(ev["events"]), f"Events: a donate card after about every 7th event ({n_ev} events, cards after {ev['events']})")
        if evc:
            ce = await pg.evaluate(CARD_JS, "#view-events .donate-every")
            check(ce["share"] == "📣 Share Chisme" and len(ce["links"]) == 2 and not [x for x in ce["cols"] if yellowish(x)], "...same card: donate buttons + Share Chisme, no yellow")
            await pg.evaluate("document.querySelector('#view-events .donate-every').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(500)
            await pg.screenshot(path=os.path.join(OUT, "donate-events.png"))
        print("== For You food feed")
        await pg.evaluate("__chisme.goView('antojos', { instant: true })")
        await pg.wait_for_function("__chisme.foodReady && document.querySelector('#fy-start')", timeout=90000); await pg.wait_for_timeout(800)
        await pg.click("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000); await pg.wait_for_timeout(800)
        k = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')].map((s) => s.classList.contains('vf-donate') ? 'D' : s.dataset.url ? 'v' : 'o').join('')")
        vids = k.count("v"); body = k.rstrip("o")
        want = "".join("v" * 7 + "D" for _ in range((vids - 1) // 7)) + "v" * (vids - 7 * ((vids - 1) // 7))
        check(vids >= 8 and body == want, f"a donate slide of its own after every 7 videos ({vids} videos: {k[:26]}...)")
        await pg.evaluate(GO, 7); await pg.wait_for_timeout(1000)
        fd = await pg.evaluate("""() => { const sl = [...document.querySelectorAll('#feed-scroll .vf-slide')], s = sl[7], r = s.getBoundingClientRect(), f = window.__chisme.forYou;
          return { cur: f.cur, donate: s.classList.contains('vf-donate'), full: Math.abs(r.top) < 2 && r.height > innerHeight * 0.6, share: !!s.querySelector('.share-chisme'), links: s.querySelectorAll('a.donate-btn').length }; }""")
        check(fd["donate"] and fd["cur"] == 7 and fd["full"] and fd["share"] and fd["links"] == 2, f"swipe to it: the donate slide fills the screen, with the donate + Share Chisme buttons {fd}")
        cf = await pg.evaluate(CARD_JS, "#feed-scroll .vf-donate .donate-every")
        check(cf and not [x for x in cf["cols"] if yellowish(x)], "...no yellow")
        await pg.screenshot(path=os.path.join(OUT, "donate-food.png"))
        await pg.evaluate(GO, 8); await pg.wait_for_timeout(1000)
        nx = await pg.evaluate("(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][8]; return { url: !!s.dataset.url, cur: window.__chisme.forYou.cur }; })()")
        check(nx["url"] and nx["cur"] == 8, f"...and the next swipe is the 8th video {nx}")
        await pg.evaluate(GO, 7); await pg.wait_for_timeout(800)
        await pg.click("#feed-scroll .vf-donate .donate-x"); await pg.wait_for_timeout(800)
        gone = await pg.evaluate("({ slides: document.querySelectorAll('.vf-donate').length, cards: document.querySelectorAll('.donate-every').length, ss: sessionStorage.getItem('chisme-donate-every-x'), open: document.querySelector('#feed').open, cur: __chisme.forYou.cur })")
        check(gone["slides"] == 0 and gone["cards"] == 0 and gone["ss"] == "1" and gone["open"] and gone["cur"] >= 0, f"X hides them all for the session (the feed stays open on a video) {gone}")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.newsReady", timeout=120000); await pg.wait_for_timeout(800)
        check(await pg.evaluate("document.querySelectorAll('.donate-every').length") == 0, "...still hidden after a reload in the same session")
        c2 = await b.new_context(**dev, service_workers="block"); await c2.add_init_script(QUIET + INIT); pg2 = await c2.new_page()
        await pg2.goto(BASE + "/"); await pg2.wait_for_function("window.__chisme && __chisme.ready && __chisme.newsReady", timeout=120000); await pg2.wait_for_timeout(800)
        check(await pg2.evaluate("document.querySelectorAll('#view-news .donate-every').length") >= 1, "...and back in a new session")
        check(not errs, f"no page errors ({errs[:2]})")
        await b.close()
    print("\nALL PASS" if not fails else f"\n{fails} FAILED")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
