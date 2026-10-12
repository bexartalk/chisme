"""Reddit r/NBASpurs: 429 → Retry-After / exponential cooldown (no calls meanwhile), stale cache served, descriptive UA. Offline."""
import asyncio, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app

RSS = b'<?xml version="1.0"?><rss><channel><item><title>Wemby dunk</title><link>https://www.reddit.com/r/NBASpurs/1</link></item></channel></rss>'
fails = 0
def check(ok, what):
    global fails; print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

class R:
    def __init__(s, code, headers=None): s.status_code, s.headers, s.content = code, headers or {}, RSS
    def raise_for_status(s):
        if s.status_code >= 400: raise RuntimeError(f"HTTP {s.status_code}")

calls = []
class C:
    def __init__(s): s.next = R(200)
    async def get(s, url, headers=None, **k): calls.append(headers); return s.next
c = C(); app.client = lambda: c
FEED = next(f for f in app.SPURS_FEEDS if f["kind"] == "reddit")
KEY = "feed:" + FEED["url"]

async def main():
    items = await app.feed_items(FEED)
    check(len(items) == 1 and items[0]["source"] == "r/NBASpurs", "200 → items parsed")
    check("chisme" in (calls[-1] or {}).get("User-Agent", "").lower(), "descriptive User-Agent sent")
    check(app.REDDIT_TTL >= 15 * 60, "cached ≥ 15 min")
    # expire the cache so the next call goes upstream and hits a 429
    app._cache[KEY] = (time.time() - app.REDDIT_TTL - 1, app._cache[KEY][1]); app._bg.clear()
    c.next = R(429, {"Retry-After": "120"})
    n = len(calls)
    items = await app.feed_items(FEED); await asyncio.sleep(0.05)
    check(len(items) == 1, "429 → stale cache still served")
    left = app._reddit["until"] - time.time()
    check(100 < left <= 121, f"Retry-After respected ({int(left)}s)")
    n = len(calls); app._cache.pop(KEY); 
    try: await app.feed_items(FEED); check(False, "cooldown with no cache raises")
    except RuntimeError: check(len(calls) == n, "no Reddit call during cooldown")
    log = app.SportsLog(); v = await log.run("reddit", "", app.feed_items(FEED), [])
    check(v == [] and log.sources[-1]["ok"] is False, "failure → [] for the sports feed, not an exception")
    # exponential backoff without Retry-After
    app._reddit.update(until=0, strikes=0); c.next = R(429)
    for want in (5, 10, 20, 40, 60, 60):
        app._reddit["until"] = 0
        try: await app.feed_items(FEED)
        except RuntimeError: pass
        got = round((app._reddit["until"] - time.time()) / 60)
        check(got == want, f"backoff {got}m == {want}m")
    app._reddit["until"] = 0; c.next = R(200)
    check(len(await app.feed_items(FEED)) == 1 and app._reddit["strikes"] == 0, "success resets backoff")

asyncio.run(main())
print("FAILED" if fails else "ALL OK"); sys.exit(1 if fails else 0)
