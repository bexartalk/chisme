"""Offline headline spam regression checks; no HTTP or application startup."""
import asyncio
import html
import os
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json",
                      SOCIAL_DIR=f"{tmp}/social", OWNER_POSTS_DIR=f"{tmp}/posts", AUTO_PUSH_WAKE_DELAY="9999")
    import app

    fails = 0

    def check(ok, what):
        global fails
        print(("PASS " if ok else "FAIL ") + what)
        fails += not ok

    live = "[NFHS Network]TV!] South San Antonio vs Southside Ｌｉｖｅ Ｓｔｒｅａｍｉｎｇ Ｆｒｅｅ ＯＮ Ｔｖ Ｃｈａｎｎｅｌ 16 October 2026"
    spaced = "South San vs Southside L i v e S t r e a m i n g F r e e"
    for t in [live, spaced, "Watch Free: Brandeis vs Clark HD", "[NFHS Network] Reagan vs Johnson Live Stream"]:
        check(app.is_spam_item(t, "Universidad de Córdoba (UCO)" if t == live else "KSAT 12"), f"spam: {t}")
    legit = ["WATCH LIVE: San Antonio City Council meeting", "UTSA vs. Rice live updates",
             "NFHS Network to stream UIL state playoffs", "Live: Spurs vs Lakers score",
             "Southside ISD football beats South San 28-14"]
    for i, t in enumerate(legit):
        check(not app.is_spam_item(t, ["KSAT 12", "San Antonio Express-News", "KENS 5"][i % 3]), f"legit: {t}")
    institutions = ["UTSA", "UT San Antonio", "Trinity University", "St. Mary's University",
                    "University of the Incarnate Word", "UIW", "Texas A&M University-San Antonio",
                    "Our Lady of the Lake University", "UT Health San Antonio", "Alamo Colleges",
                    "San Antonio College", "Palo Alto College", "St. Philip's College",
                    "Northwest Vista College", "Northeast Lakeview College"]
    for src in institutions:
        check(not app.is_spam_item("Campus opens new building", src, "https://school.edu"), f"local institution: {src}")
    check(app.is_spam_item("Campus news", "University of Oxford"), "foreign university blocked")
    # real newsrooms' how-to-watch explainers stay; the same words from an unknown Google News source don't
    for t in ("Spurs vs. Lakers: Time, TV channel, how to watch online", "Watch: Free flu shots at Southside clinics Saturday",
              "UTSA vs. Rice: streaming info, odds and prediction"):
        check(not app.is_spam_item(t, "KSAT 12"), f"trusted newsroom kept: {t}")
        check(not app.is_spam_item(t, None), f"curated feed kept: {t}")
    check(app.is_spam_item("Reagan vs Johnson TV Channel and streaming tonight", "Random Blog Hub"), "weak signals from an unknown source dropped")
    for t in ("Who shot the Southside store clerk?", "Spurs win again!", "Wait... the Alamodome is booked"):
        check(app.clean_title(t) == t, f"ending punctuation / ellipsis kept: {t}")
    check(app.is_spam_item("Campus news", "Publisher", "https://www.uco.es"), "foreign domain blocked")
    check(not app.is_spam_item("Border news", "Publisher", "https://news.mx"), "Mexican outlet kept")
    check(app.clean_title("Ｌｉｖｅ") == "Live", "fullwidth normalized")
    check(app.clean_title("L i v e S t r e a m") == "Live Stream", "letter spacing collapsed")
    check(app.clean_title("[NFHS Network]TV!] Foo").count("[") == app.clean_title("[NFHS Network]TV!] Foo").count("]") == 0, "stray brackets removed")
    long = app.clean_title("A headline about local news " * 20)
    check(len(long) <= 160 and long.endswith("…"), "title clipped")
    for t in ["Spurs beat Lakers 112-104", "U.S. 281 closed", "Q & A with the mayor", "A new day"]:
        check(app.clean_title(t) == t, f"unchanged: {t}")
    check(app.clean_title("A\u200b new\ufeff day") == "A new day", "zero-width characters removed")
    feed = {"id": "hood1", "name": "x", "kind": "gnews_strict", "url": "https://news.google.com/rss/search?q=x"}
    real = "WATCH LIVE: San Antonio City Council meeting"
    rows = [(live, "Universidad de Córdoba (UCO)", "https://www.uco.es"),
            (spaced, "Spam", "https://example.com"), (real, "KSAT 12", "https://ksat.com")]
    xml = '<rss version="2.0"><channel><title>News</title>' + ''.join(
        f'<item><title>{html.escape(t)}</title><link>https://example.com/{i}</link><source url="{url}">{html.escape(src)}</source></item>'
        for i, (t, src, url) in enumerate(rows)) + '</channel></rss>'
    def no_network(*args, **kwargs):
        raise AssertionError("Network forbidden in this test")

    with patch.object(app, "client", no_network):
        items = asyncio.run(app._fetch_feed(feed, SimpleNamespace(content=xml.encode())))
        check(len(items) == 1 and items[0]["title"] == real and items[0]["source_url"] == "https://ksat.com", "XML ingest keeps KSAT and captures source URL")
        old = [{"title": t, "source": src, "source_url": url, "link": f"https://example.com/{i}"} for i, (t, src, url) in enumerate(rows)]
        app._cache["feed:" + feed["url"]] = (time.time(), old)
        result = asyncio.run(app.fetch_feed(feed))
        check(len(result["items"]) == 1 and result["status"].get("spam_dropped", 0) > 0, "post-cache spam removal and status")
        count = app.SPAM_DROPPED[feed["id"]]
        asyncio.run(app.fetch_feed(feed))
        check(app.SPAM_DROPPED[feed["id"]] == count, "cache cleanup is idempotent")
        check(len(asyncio.run(app.feed_items(feed))) == 1, "feed_items cleans cached feed")
        curated = dict(feed, id="curated", kind="rss")
        check(len(app._clean_feed_items(curated, [{"title": "Campus news", "source": "University of Oxford"}])) == 1, "curated university source kept")
        app._cache["feed:" + feed["url"]] = (time.time(), [dict(title=live, source="Spam", link="https://example.com/spam")])
        check(asyncio.run(app.feed_items(feed)) == [], "feed_items independently removes cached spam")
    sys.exit(1 if fails else 0)
