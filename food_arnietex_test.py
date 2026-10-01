"""v44: ArnieTex (Arnie Segovia, @ArnieTex, a Texas BBQ pitmaster) in the Bigger the Pansa, Better the Chansa For You feed.

1. data/recipe_videos.json: 6–10 of his real YouTube Shorts (brisket, red marinade, carne asada, fajitas, Tex-Mex BBQ …),
   unique ids, his channel (UCnxOJ_Un-QF_KYqbPRAfLNw).
2. Live, every one of his ids: YouTube oEmbed 200 with author ArnieTex, the watch page says his channelId,
   playableInEmbed true and status OK, and /shorts/ID is a Short.
3. /api/food serves them as recipe videos, all under one crew (so the variety rules treat him as one creator).
4. For You (WebKit, 390×844), 4 new-phone visits: the first 9 videos are 9 different creators, never the same creator twice in
   a row in the top 15, no restaurant twice in the top 15, at most 2 per creator in the top 10; ArnieTex is in the feed with all his videos,
   at most once in the top 20 and spread out evenly (never two of his within 8 slides; foryou.js spreads a cook's
   videos 1/n apart through the cooking slots, so they don't bunch up at the end). Then every one of his slides plays in the feed
   (YouTube player state 1). Screenshot: food-arnietex.png."""
import asyncio, json, os, re, sys, time, urllib.request, urllib.error, urllib.parse
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
URL = os.environ.get("URL", "http://127.0.0.1:8211/")
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-feed-sound','off'); }"
CH = "UCnxOJ_Un-QF_KYqbPRAfLNw"; CREW = "cook:" + CH.lower()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

R = json.load(open(os.path.join(HERE, "data", "recipe_videos.json")))["videos"]
A = [v for v in R if v["creator"] == "ArnieTex"]

def data():
    print("== data/recipe_videos.json")
    ids = [v["id"] for v in R]
    check(6 <= len(A) <= 10, f"{len(A)} ArnieTex Shorts")
    check(len(set(ids)) == len(ids), "every id once")
    check(all(v["channel_id"] == CH and v["channel_url"] == "https://www.youtube.com/@ArnieTex" and v["url"] == f"https://www.youtube.com/shorts/{v['id']}" and v.get("verified") and v.get("person") == "Arnie Segovia" for v in A),
          "each is a /shorts/ link on his channel, with the day it was checked")
    text = " ".join(v["title"] + " " + v["topic"] for v in A).lower()
    check(all(w in text for w in ("brisket", "marinade", "asada", "fajita", "tex-mex")), f"brisket, red marinade, carne asada, fajitas, Tex-Mex: {sorted({v['topic'] for v in A})}")

def get(url, redirect=True):
    class NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    op = urllib.request.build_opener() if redirect else urllib.request.build_opener(NoRedir)
    try:
        r = op.open(urllib.request.Request(url, headers=UA), timeout=25); return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e: return e.code, ""
    except Exception as e: return 0, str(e)

def live():
    print("\n== live: YouTube, every ArnieTex id")
    for v in A:
        c, body = get("https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={v['id']}", "format": "json"}))
        author = json.loads(body).get("author_name") if c == 200 else None
        for _ in range(8):   # the watch page sometimes comes back without the player data (a consent / bot page): try again
            c2, w = get(f"https://www.youtube.com/watch?v={v['id']}")
            if '"playableInEmbed"' in w: break
            time.sleep(3)
        pie = re.search(r'"playableInEmbed":(true|false)', w); st = re.search(r'"playabilityStatus":\{"status":"(\w+)"', w); ch = re.search(r'"channelId":"(UC[\w-]{22})"', w)
        c3, _ = get(f"https://www.youtube.com/shorts/{v['id']}", redirect=False)
        ok = c == 200 and author == "ArnieTex" and pie and pie.group(1) == "true" and st and st.group(1) == "OK" and ch and ch.group(1) == CH and c3 == 200
        check(ok, f"{v['id']} {v['title'][:60]!r}: oEmbed {c} by {author}, embeddable {pie and pie.group(1)}, status {st and st.group(1)}, channel {ch and ch.group(1)}, /shorts {c3}")

def api():
    print("\n== /api/food")
    d = json.load(urllib.request.urlopen(URL + "api/food?lat=29.4241&lon=-98.4936", timeout=120))
    mine = [x for x in d.get("recipes") or [] if x["creator"] == "ArnieTex"]
    check(len(mine) == len(A) and {x["crew"] for x in mine} == {CREW} and all(x["kind"] == "recipe" and x["video"] for x in mine), f"serves his {len(mine)} as recipe videos, one crew ({CREW})")

async def ui(p):
    print("\n== For You, WebKit 390×844")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 1
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); pg = await ctx.new_page()
    await pg.goto(URL + "#cual-dieta")
    seen = []
    for visit in range(4):
        await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=120000)
        await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000); await pg.wait_for_timeout(700)
        feed = (await pg.evaluate("window.__chisme.forYou"))["feed"]
        at = [i for i, f in enumerate(feed) if f["creator"] == "ArnieTex"]; seen.append(at)
        top = feed[:15]; places = [f["place"] for f in top if f["place"]]
        check(len({f["crew"] for f in feed[:9]}) == 9 and all(a["crew"] != b["crew"] for a, b in zip(top, top[1:])) and len(places) == len(set(places))
              and max(sum(f["crew"] == c for f in feed[:10]) for c in {f["crew"] for f in feed[:10]}) <= 2,
              f"visit {visit + 1}: the first 9 are 9 different creators, never one twice in a row (top 15), no restaurant twice in the top 15, ≤ 2 per creator in the top 10")
        check(len(at) == len(A) and sum(i < 20 for i in at) <= 1 and all(b - a >= 8 for a, b in zip(at, at[1:])),
              f"visit {visit + 1}: all {len(A)} ArnieTex videos are in the {len(feed)}-video feed, spread out, not taking over (slides {[i + 1 for i in at]})")
        await pg.tap("#feed-close"); await pg.wait_for_function("!document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(400)
    await ctx.close()
    # a fresh phone: open the feed, let the first video start, then go to his first slide: it plays
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); pg = await ctx.new_page()
    await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=120000)
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000)
    try: await pg.wait_for_function("window.__chisme.forYou.player.st === 1", timeout=15000)
    except Exception: pass
    mine = [k for k, f in enumerate((await pg.evaluate("window.__chisme.forYou"))["feed"]) if f["creator"] == "ArnieTex"]
    played = {}
    async def go(i):
        await pg.evaluate(f"() => {{ const s = document.querySelector('#feed-scroll'); s.scrollTo({{ top: s.clientHeight * {i}, behavior: 'instant' }}); }}")
        await pg.wait_for_function(f"window.__chisme.forYou.cur === {i}", timeout=8000)
        try: await pg.wait_for_function(f"() => {{ const f = window.__chisme.forYou; return f.player.slide === {i} && f.player.st === 1; }}", timeout=15000)
        except Exception: pass
        return await pg.evaluate("(() => { const f = window.__chisme.forYou, s = [...document.querySelectorAll('#feed-scroll .vf-slide')][f.cur]; return { cur: f.cur, st: f.player.st, vid: f.player.vid, by: s.querySelector('.vf-by') ? s.querySelector('.vf-by').textContent : '', title: f.feed[f.cur].title }; })()")
    for i in mine:   # every one of his videos, in feed order
        st = await go(i); want = next(v for v in A if v["title"] == st["title"])
        played[want["id"]] = st["st"] == 1 and st["vid"] == want["id"] and "ArnieTex" in st["by"]
        check(played[want["id"]], f"slide {i + 1}: ArnieTex's {st['title'][:55]!r} plays in the feed (YouTube state {st['st']}, video {st['vid']}, '{st['by']}')")
    check(len(played) == len(A) and all(played.values()), f"all {len(A)} of his videos play in the For You feed")
    # the picture: his first slide, paused so the info + buttons show
    await go(mine[0]); await pg.wait_for_timeout(2500)
    await pg.tap(f"#feed-scroll .vf-slide:nth-child({mine[0] + 1}) .vf-shield"); await pg.wait_for_timeout(900)
    await pg.screenshot(path=os.path.join(OUT, "food-arnietex.png"))
    await b.close()

async def main():
    data(); live(); api()
    async with async_playwright() as p: await ui(p)
    print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED")); sys.exit(1 if fails else 0)
asyncio.run(main())
