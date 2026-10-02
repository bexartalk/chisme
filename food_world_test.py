"""v43 food feed: food reviewers from the US and around the world, and just the title at the top (no 'N / 105' counter).

1. data/world_food_videos.json: 40+ real YouTube Shorts from 15+ creators (Best Ever Food Review Show + its Shorts, More
   BEFRS (Sonny Side), Mark Wiens, Luke Martin, Davidsbeenhere, Joel Hansen, Strictly Dumpling (Mike Chen), Daym Drops, The Food
   Ranger, Eater …), unique ids, none shared with the recipes.
2. Live, every id: YouTube oEmbed 200 (public + embeddable) with the listed channel as its author.
3. /api/food serves them as "world" videos (all still embeddable), one crew per person.
4. For You (WebKit, 390×844): a San Antonio creator leads on every visit (the lead rotates), world reviewers mixed in (local and
   world take turns, every 3rd a recipe), never the same creator twice in a row; a world slide says "🌎 Food around the world · <where>".
   The top bar shows just "Bigger the Pansa, Better the Chansa". Screenshots: food-v43.png, food-v43-world.png."""
import asyncio, json, os, sys, urllib.request, urllib.error, urllib.parse, concurrent.futures as cf
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
URL = os.environ.get("URL", "http://127.0.0.1:8211/")
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-feed-sound','off'); }"
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

W = json.load(open(os.path.join(HERE, "data", "world_food_videos.json")))["videos"]
R = json.load(open(os.path.join(HERE, "data", "recipe_videos.json")))["videos"]
WANT = ["Best Ever Food Review Show", "More Best Ever Food Review Show", "Mark Wiens", "Luke Martin", "Davidsbeenhere", "Joel Hansen", "Strictly Dumpling"]

def data():
    print("== data/world_food_videos.json")
    ids = [v["id"] for v in W]; people = {v["person"] for v in W}; chans = {v["creator"] for v in W}
    check(len(W) >= 40 and len(people) >= 15, f"{len(W)} videos from {len(chans)} channels / {len(people)} creators")
    check(len(set(ids)) == len(ids) and not set(ids) & {r["id"] for r in R}, "every id once, none shared with the recipes")
    check(all(c in chans for c in WANT), f"the ones asked for are there: {', '.join(WANT)} (+ Mike Chen = Strictly Dumpling, Sonny Side = BEFRS / More BEFRS)")
    check(all(v["url"] == f"https://www.youtube.com/shorts/{v['id']}" and v.get("verified") and v.get("channel_id", "").startswith("UC") for v in W), "all YouTube Shorts, each with its channel and the day it was checked")
    per = {}
    for v in W: per[v["person"]] = per.get(v["person"], 0) + 1
    check(max(per.values()) <= 9, f"no creator dominates (most: {max(per, key=per.get)} {max(per.values())})")

def oembed(v):
    u = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={v['id']}", "format": "json"})
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
        return v["id"], r.status, json.loads(r.read()).get("author_name")
    except urllib.error.HTTPError as e:
        return v["id"], e.code, None
    except Exception as e:
        return v["id"], 0, str(e)[:40]

def live():
    print("\n== live: YouTube oEmbed for every id")
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(oembed, W))
    if all(c == 0 for _, c, _ in res): check(False, "YouTube unreachable from here"); return
    bad = [(i, c, a) for (i, c, a), v in zip(res, W) if c != 200 or a != v["creator"]]
    check(not bad, f"all {len(W)} answer 200 (public + embeddable) with the right channel as author ({bad[:4]})")

def api():
    print("\n== /api/food")
    d = json.load(urllib.request.urlopen(URL + "api/food?lat=29.4241&lon=-98.4936", timeout=120))
    w = d.get("world") or []
    check(len(w) == len(W) and all(x["kind"] == "world" and x["world"] and x["video"] and x["crew"].startswith("world:") for x in w), f"serves {len(w)} world videos (all still embeddable)")
    check(len({x["crew"] for x in w}) == len({v["person"] for v in W}), "one crew per person (BEFRS + More BEFRS are both Sonny Side)")
    check(len(d["items"]) >= 10, f"San Antonio's own creators still there ({len(d['items'])} videos)")

async def ui(p):
    print("\n== For You, WebKit 390×844")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 1
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); pg = await ctx.new_page()
    leads = []
    await pg.goto(URL + "#cual-dieta")
    for visit in range(4):
        await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=120000)
        await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000); await pg.wait_for_timeout(900)
        feed = (await pg.evaluate("window.__chisme.forYou"))["feed"]
        leads.append(feed[0]["crew"])
        if visit == 0:
            top = feed[:15]
            kinds = ["R" if f["recipe"] else "W" if f["world"] else "L" for f in top]
            check(kinds[0] == "L", f"a San Antonio creator leads ({feed[0]['creator']})")
            check(kinds[:9] == ["L", "W", "R"] * 3, f"then local and world take turns, every 3rd a recipe ({''.join(kinds)})")
            check(all(a["crew"] != b["crew"] for a, b in zip(top, top[1:])) and len({f["crew"] for f in feed[:9]}) == 9, "the first 9 are 9 different creators, never one twice in a row")
            check(sum(f["world"] for f in feed) == len(W), f"all {len(W)} world videos are in the feed ({len(feed)} videos in all)")
            bar = await pg.evaluate("(() => { const l = document.querySelector('.feed-label'); return { txt: l.textContent.trim(), pos: !!document.querySelector('#feed-pos'), digits: /\\d+\\s*\\/\\s*\\d+/.test(document.querySelector('.feed-top').textContent) }; })()")
            check(bar["txt"] == "Bigger the Pansa, Better the Chansa" and not bar["pos"] and not bar["digits"], f"the top shows just the title, no 'N / {len(feed)}' counter ({bar})")
            await pg.wait_for_timeout(1500); await pg.screenshot(path=os.path.join(OUT, "food-v43.png"))
            await pg.evaluate("() => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: s.clientHeight, behavior: 'instant' }); }")
            await pg.wait_for_function("window.__chisme.forYou.cur === 1", timeout=5000); await pg.wait_for_timeout(1500)
            slide = await pg.evaluate("(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][1], w = s.querySelector('.vf-world'); return { world: w ? w.textContent : null, by: s.querySelector('.vf-by').textContent }; })()")
            check(feed[1]["world"] and slide["world"] == (f"🌎 Food around the world · {feed[1]['where']}" if feed[1]["where"] else "🌎 Food around the world") and feed[1]["creator"] in slide["by"],
                  f"a world video's slide: '{slide['world']}' · {slide['by']}")
            await pg.screenshot(path=os.path.join(OUT, "food-v43-world.png"))
        await pg.tap("#feed-close"); await pg.wait_for_function("!document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(500)
    check(all(not l.startswith("world:") for l in leads) and all(a != b for a, b in zip(leads, leads[1:])), f"every visit a different San Antonio creator leads ({leads})")
    await b.close()

async def main():
    data(); live(); api()
    async with async_playwright() as p: await ui(p)
    print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED")); sys.exit(1 if fails else 0)
asyncio.run(main())
