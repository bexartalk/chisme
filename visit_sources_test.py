"""v49.15.2 where visits come from ("src", stats.py) + GET /stats/api/summary:
  • server (TestClient, a temp file store): a src batch counts src:/camp:/land:/ref:, junk is refused, /api/stats says
    X-Stats: counted / skipped, Do Not Track / GPC → nothing; /stats/api/summary is owner only (Bearer ADMIN_TOKEN) and
    returns visitors, opens, sources, campaigns, landing spots, sending sites, per-day rows; the /stats page shows the fold
  • the app (Chromium against CHISME_URL, default http://localhost:8211): ?utm_source=&utm_campaign=, ?fbclid=,
    ?ttclid=, a Facebook in-app browser, a /?reel= link, plain → the queued "src" event (category only: no full URL, no
    user agent); Do Not Track → nothing queued
Run: CHISME_URL=http://localhost:8341 ./venv/bin/python visit_sources_test.py"""
import asyncio, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
for k in [k for k in os.environ if k.startswith(("UPSTASH_", "RENDER", "PUSH_TEST"))]: os.environ.pop(k)
os.environ.update(ADMIN_TOKEN="src-test-token-123", PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

import stats  # noqa: E402
print("== tally")
D = "A" * 22
t = stats.tally({"d": D, "e": [["open", "web"], ["src", {"s": "facebook", "c": "dj-post", "l": "reel:dQw4w9WgXcQ", "r": "l.facebook.com"}]]})
c = t["counts"] if t else {}
check(c.get("src:facebook") == 1 and c.get("camp:facebook/dj-post") == 1 and c.get("land:reel:dQw4w9WgXcQ") == 1 and c.get("ref:l.facebook.com") == 1, f"a src event counts source, campaign, landing and sending site ({c})")
bad = stats.tally({"d": D, "e": [["src", {"s": "Face Book!", "c": "<x>", "l": "javascript:x", "r": "http://evil.com/path?q=1"}], ["src", "facebook"], ["src", {"s": "x" * 40}]]})
check(bad is None, f"junk src events (bad words, a full URL, not a dict, too long) are dropped ({bad})")
t2 = stats.tally({"d": D, "e": [["src", {"s": "tiktok", "l": "story", "r": "bad host"}]]})
check(t2 and t2["counts"] == {"src:tiktok": 1, "land:story": 1}, f"a bad host is dropped, the rest kept ({t2 and t2['counts']})")

print("== /api/stats + /stats/api/summary")
from fastapi.testclient import TestClient  # noqa: E402
import app as appmod  # noqa: E402
cl = TestClient(appmod.app)
body = json.dumps({"d": "B" * 22, "e": [["open", "web"], ["src", {"s": "tiktok", "c": "juan-dj", "l": "juegos"}], ["src", {"s": "facebook"}]]})
r = cl.post("/api/stats", content=body, headers={"content-type": "text/plain"})
check(r.status_code == 204 and r.headers.get("x-stats") == "counted", f"a real batch → 204, X-Stats: counted ({r.status_code} {r.headers.get('x-stats')})")
r = cl.post("/api/stats", content=b"nope", headers={"content-type": "text/plain"})
check(r.status_code == 204 and r.headers.get("x-stats") == "skipped", f"junk → 204, X-Stats: skipped ({r.headers.get('x-stats')})")
r = cl.post("/api/stats", content=body, headers={"content-type": "text/plain", "sec-gpc": "1"})
check(r.status_code == 204 and r.headers.get("x-stats") != "counted", "Global Privacy Control → not counted")
r = cl.get("/stats/api/summary")
check(r.status_code == 401 and "visitors" not in r.text, f"/stats/api/summary without the key → 401 ({r.status_code})")
r = cl.get("/stats/api/summary", headers={"authorization": "Bearer wrong"})
check(r.status_code == 401, f"…a wrong key → 401 ({r.status_code})")
r = cl.get("/stats/api/summary", headers={"authorization": "Bearer src-test-token-123"})
j = r.json() if r.status_code == 200 else {}
td = (j.get("periods") or {}).get("today") or {}
check(r.status_code == 200 and td.get("visitors") == 1 and td.get("opens") == 1 and td.get("sources") == {"tiktok": 1, "facebook": 1}
      and td.get("campaigns") == {"tiktok/juan-dj": 1} and td.get("landing") == {"juegos": 1} and len(j.get("per_day") or []) == 30
      and r.headers.get("cache-control") == "no-store", f"…the owner's key → today's visitors, opens, sources, campaigns, landing, 30 day rows ({td})")
check(set(j["periods"]) == {"today", "7d", "30d"} and j["periods"]["30d"]["sources"].get("tiktok") == 1, "…today / 7 days / 30 days")
sess, _ = asyncio.run(stats.new_session(True)); cl.cookies.set(stats.COOKIE, sess, path="/stats")
r = cl.get("/stats")
check(r.status_code == 200 and "Where visitors come from" in r.text and "TikTok · juan-dj" in r.text and "#juegos" in r.text, "the /stats page has the '🔗 Where visitors come from' fold (sources, campaigns, landing)")
check("#ff0" not in r.text.lower() and "yellow" not in r.text.lower(), "no yellow on the new fold")

print("== the app (" + os.environ.get("CHISME_URL", "http://localhost:8211") + ")")
BASE = os.environ.get("CHISME_URL", "http://localhost:8211").rstrip("/")
from playwright.async_api import async_playwright  # noqa: E402
import pw_csp  # noqa: E402,F401
INIT = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1');"
Q = "(() => JSON.parse(localStorage.getItem('chisme-stats-q') || '[]').filter((e) => e[0] === 'src').map((e) => e[1]))()"
async def src_of(b, path, ua=None, extra=None, dnt=False):
    kw = {"viewport": {"width": 390, "height": 844}}
    if ua: kw["user_agent"] = ua
    ctx = await b.new_context(**kw); await ctx.add_init_script(INIT)
    if dnt: await ctx.add_init_script("Object.defineProperty(navigator, 'globalPrivacyControl', { get: () => true });")
    pg = await ctx.new_page(); await pg.goto(BASE + path, referer=extra) if extra else await pg.goto(BASE + path)
    await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=90000); await pg.wait_for_timeout(300)
    v = await pg.evaluate(Q); await ctx.close(); return v
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        v = await src_of(b, "/?utm_source=facebook&utm_campaign=Hon%20Dipo%20DJ")
        check(v == [{"s": "facebook", "c": "hon-dipo-dj"}], f"?utm_source=facebook&utm_campaign=… → facebook / hon-dipo-dj ({v})")
        v = await src_of(b, "/?fbclid=IwAR0abc")
        check(v == [{"s": "facebook"}], f"?fbclid= → facebook ({v})")
        v = await src_of(b, "/?ttclid=E.abc#juegos")
        check(v == [{"s": "tiktok", "l": "juegos"}], f"?ttclid= + #juegos → tiktok, landed on juegos ({v})")
        v = await src_of(b, "/", ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/450.0]")
        check(v == [{"s": "facebook"}], f"Facebook's in-app browser (no referrer) → facebook ({v})")
        v = await src_of(b, "/?reel=dQw4w9WgXcQ", extra="https://www.tiktok.com/@someone/video/1")
        check(v == [{"s": "tiktok", "l": "reel:dQw4w9WgXcQ", "r": "tiktok.com"}], f"a ChismeTV link from tiktok.com → tiktok, landed on the reel, site name only ({v})")
        v = await src_of(b, "/", extra="https://news.example.org/some/article?id=5")
        check(v == [{"s": "other", "r": "news.example.org"}] and "article" not in json.dumps(v), f"another site → other + its host name, never the path ({v})")
        v = await src_of(b, "/")
        check(v == [{"s": "direct"}], f"typed / bookmark → direct ({v})")
        v = await src_of(b, "/?utm_source=facebook", dnt=True)
        check(v == [], f"Global Privacy Control → nothing queued ({v})")
        await b.close()
asyncio.run(main())
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
