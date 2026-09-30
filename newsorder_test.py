"""News order (v29): if you check often and nothing is new, News looks different each visit, all on the phone.

1. static/newsorder.js in Node: a first open keeps the server's order; later visits with nothing new reorder
   (lead rotates among the top 3, unseen stories rise, opened ones sink, light shuffle that keeps roughly the
   server's order, outlets don't clump); new + breaking/urgent stories stay pinned at the top in server order;
   the order is stable within a visit (even as stories get marked seen); a new visit needs 10+ minutes away.
2. WebKit iPhone 13: two visits to News. An immediate reload keeps the order; 10+ minutes away reorders it; the
   NWS alert strip stays on top; a story never shown before is pinned first; a news check mid-visit doesn't move
   anything; opening a story is remembered; Settings → Reset my feed and Forget me clear it.
Screenshots: news-reshuffle-before.png (visit 1), news-reshuffle-after.png (visit 2, after 10+ min away)."""
import asyncio, json, os, subprocess
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

UNIT = r"""
const N = require(process.argv[1]);
const srcs = ["KSAT 12", "KSAT 12", "News 4", "KENS 5", "KSAT 12", "Express-News", "News 4", "KENS 5", "KSAT 12", "News 4", "Report", "KENS 5", "KSAT 12", "News 4", "Current", "KSAT 12", "KENS 5", "News 4", "Express-News", "KSAT 12"];
const now = Date.now(), items = srcs.map((s, i) => ({ title: "Story " + i + " about the city council budget", link: "https://x.example/s" + i, source: s, published: now / 1000 - i * 3600 }));
let seed = 1; const rand = () => { seed = (seed * 48271) % 2147483647; return seed / 2147483647; };
const st = { s: {}, visit: null, active: 0 };
const out = {};
N.beginVisit(st, now, rand);
out.first = N.order(items, st, { now }).map((i) => i.link);
N.markRendered(st, items, now);
for (const it of items.slice(0, 8)) N.markSeen(st, N.idOf(it.link), now);    // visit 1: scrolled past the first 8
out.visits = [];
for (let v = 0; v < 4; v++) {
  N.beginVisit(st, now + (v + 1) * 11 * 60000, rand);
  const a = N.order(items, st, { now }).map((i) => i.link);
  for (const it of items) N.markSeen(st, N.idOf(it.link), now);   // seeing everything must not move this visit's order
  const b = N.order(items, st, { now }).map((i) => i.link);
  out.visits.push({ a, stable: JSON.stringify(a) === JSON.stringify(b) });
}
// new + urgent pinned
N.beginVisit(st, now + 99 * 60000, rand);
const fresh = [{ title: "Brand new story", link: "https://x.example/new1", source: "KSAT 12", published: now / 1000 }, { title: "Another new one", link: "https://x.example/new2", source: "KSAT 12", published: now / 1000 }];
const urgent = { title: "BREAKING: Boil water notice issued for the North Side", link: "https://x.example/s15", source: "KSAT 12", published: now / 1000 - 15 * 3600 };
const mixed = items.slice(0, 15).concat([urgent], items.slice(16)).concat(fresh);
mixed.splice(3, 0, ...mixed.splice(mixed.length - 2, 2));   // the server put the new ones at 3 and 4
out.pinned = N.order(mixed, st, { now }).slice(0, 3).map((i) => i.link);
// opened sinks
N.markOpened(st, N.idOf(items[1].link), now);
N.beginVisit(st, now + 120 * 60000, rand);
out.opened = N.order(items, st, { now }).map((i) => i.link).indexOf(items[1].link);
out.srcs = Object.fromEntries(items.map((i) => [i.link, i.source]));
out.away = [N.isNewVisit({ visit: {}, active: now - 9 * 60000 }, now), N.isNewVisit({ visit: {}, active: now - 11 * 60000 }, now), N.isNewVisit({ s: {}, visit: null }, now)];
console.log(JSON.stringify(out));
"""

def unit():
    print("== static/newsorder.js (Node)")
    r = subprocess.run(["node", "-e", UNIT, os.path.join(HERE, "static", "newsorder.js")], capture_output=True, text=True, timeout=60)
    if r.returncode:
        check(False, "node harness ran: " + r.stderr[-300:]); return
    o = json.loads(r.stdout)
    server = [f"https://x.example/s{i}" for i in range(20)]
    check(o["first"] == server, "first open (nothing seen before): the server's order, untouched")
    orders = [v["a"] for v in o["visits"]]
    check(all(a != server for a in orders), "later visits with nothing new: a different order each time")
    check(orders[0][0] != server[0], "visit 2: a different lead than visit 1")
    check(len({a[0] for a in orders[:3]}) == 3 and all(a[0] in server[:6] for a in orders), f"the lead rotates among the top few ({[a[0][-3:] for a in orders]})")
    check(all(v["stable"] for v in o["visits"]), "stable within a visit, even as stories get marked seen")
    disp = [abs(a.index(u) - i) for a in orders for i, u in enumerate(server)]
    check(sum(disp) / len(disp) <= 4 and max(disp) <= 12, f"light shuffle: roughly the server's recency/importance order (avg move {sum(disp) / len(disp):.1f}, max {max(disp)})")
    v1 = orders[0]
    unseen_rank = sum(v1.index(u) for u in server[8:14]) / 6
    check(unseen_rank < 11, f"stories you haven't scrolled past move up (avg place {unseen_rank:.1f}, server avg 10.5)")
    runs = [sum(o["srcs"][a[k]] == o["srcs"][a[k + 1]] for k in range(len(a) - 1)) for a in orders]
    base = sum(o["srcs"][server[k]] == o["srcs"][server[k + 1]] for k in range(19))
    check(max(runs) <= 1, f"outlets mixed: back-to-back same outlet {runs} per visit (server order had {base})")
    check(o["pinned"] == ["https://x.example/new1", "https://x.example/new2", "https://x.example/s15"], f"new stories + breaking/urgent pinned on top, in the server's order ({o['pinned']})")
    check(o["opened"] >= 5, f"a story you already opened makes room at the top (now #{o['opened'] + 1})")
    check(o["away"] == [False, True, True], "a new visit needs 10+ minutes away (or a first open)")

ORDER = "() => [...document.querySelectorAll('#near-list .story h3 a')].map(a => a.textContent)"
async def wait_news(pg):
    await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelectorAll('#near-list .story').length >= 5", timeout=120000)
    await pg.wait_for_timeout(2500)   # the live load after the saved copy
async def shot(pg, name):
    await pg.evaluate("() => { const n = document.querySelector('#near'); window.scrollTo(0, n.getBoundingClientRect().top + scrollY - 70); }")
    await pg.wait_for_timeout(700); await pg.screenshot(path=os.path.join(OUT, name))
# "11 minutes away": applied by an init script in the NEW document before app.js runs (editing storage from the old
# page races WebKit's process swap on navigation, and the app's own hide handler re-saves "last on screen").
AWAY_INIT = """(() => { const m = /[?&]t_away=([^&]*)/.exec(location.search); if (!m) return;
  const k = 'chisme-news-seen', s = JSON.parse(localStorage.getItem(k)); s.active -= 11 * 60000;
  if (m[1]) delete s.s[decodeURIComponent(m[1])];
  localStorage.setItem(k, JSON.stringify(s)); history.replaceState(null, '', '/'); })()"""
async def away(pg, drop=""):
    """Leave the app for 11+ minutes (optionally forgetting one story), then open it again."""
    await pg.goto(BASE + "/healthz"); await pg.goto(BASE + "/?t_away=" + drop); await wait_news(pg)

async def ui():
    print("\n== WebKit iPhone 13: two visits to News")
    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(AWAY_INIT)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: None if "access control checks" in str(e) else errs.append(str(e)[:160]))   # WebKit: a fetch cut off by the test navigating away
        await pg.goto(BASE + "/"); await wait_news(pg)
        v1 = await pg.evaluate(ORDER)
        for y in range(0, 5000, 600):   # read down the list: marks what was on screen as seen
            await pg.evaluate(f"window.scrollTo(0, {y})"); await pg.wait_for_timeout(250)
        await shot(pg, "news-reshuffle-before.png")
        await pg.wait_for_timeout(1200)
        st = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-news-seen'))")
        seen = sum(1 for x in st["s"].values() if x.get("n"))
        check(len(st["s"]) >= len(v1) and seen >= 3, f"the phone tracks shown ({len(st['s'])}) and seen ({seen}) stories, with a visit ({st['visit']['n']})")
        await pg.reload(); await wait_news(pg)
        v1b = await pg.evaluate(ORDER)
        check(v1b == v1, "an immediate reload (same visit) keeps the order")
        await away(pg)
        v2 = await pg.evaluate(ORDER)
        common = [t for t in v2 if t in v1]
        new_top = [t for t in v2 if t not in v1]
        check(common != [t for t in v1 if t in v2] and len(common) >= 5, f"10+ minutes away → a different order ({len(common)} stories, {len(new_top)} new pinned on top)")
        check(common[0] != v1[0], f"a different lead story ({v1[0][:40]!r} → {common[0][:40]!r})")
        check(v2[:len(new_top)] == new_top, "any story that's actually new is on top")
        check(sorted(v1b) == sorted(v1) and set(common) <= set(v1), "same stories, same headlines (nothing rewritten)")
        await shot(pg, "news-reshuffle-after.png")
        pos = await pg.evaluate("() => { const a = document.querySelector('#alert-strip'), n = document.querySelector('#near'); return a && !a.hidden ? !!(a.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING) : null; }")
        check(pos in (True, None), f"NWS alert strip stays above the news ({'shown' if pos else 'no active alert'})")
        await pg.evaluate("__chisme.checkNews()"); await pg.wait_for_timeout(4000)
        check(await pg.evaluate(ORDER) == v2, "a news check mid-visit doesn't move anything")
        # a story never shown before is pinned first
        target = v2[6]
        sid = await pg.evaluate("(t) => [...document.querySelectorAll('#near-list .story')].find(x => x.querySelector('h3 a').textContent === t).dataset.sid", target)
        await away(pg, sid)
        v3 = await pg.evaluate(ORDER)
        check(target in v3[:3], f"a story this phone never showed before is pinned on top (#{v3.index(target) + 1 if target in v3 else '?'})")
        # opening a story is remembered
        await pg.evaluate("() => { const a = document.querySelector('#near-list .story h3 a'); a.scrollIntoView({block:'center'}); a.click(); }")
        await pg.wait_for_function("document.querySelector('#player').open", timeout=15000)
        await pg.evaluate("document.querySelector('#player').close()"); await pg.wait_for_timeout(1200)
        opened = await pg.evaluate("Object.values(JSON.parse(localStorage.getItem('chisme-news-seen')).s).filter(x => x.o).length")
        check(opened >= 1, "opening a story is remembered on the phone")
        # Settings → Reset my feed / Forget me clear it
        for btn, twice in (("#set-fy-reset", False), ("#set-forget", True)):
            await pg.click("#settings-btn"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"document.querySelector('{btn}').scrollIntoView()")
            await pg.click(btn)
            if twice: await pg.click(btn)
            st = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-news-seen'))")
            check(st and not st["s"] and not st["visit"]["snap"], f"Settings → {'Forget me' if twice else 'Reset my feed'} clears what News remembered")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
            await pg.evaluate("() => { const s = JSON.parse(localStorage.getItem('chisme-news-seen')); s.s = {'x': {f: 1}}; localStorage.setItem('chisme-news-seen', JSON.stringify(s)); }")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()

async def main():
    unit(); await ui()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
