"""Fill a local stats FILE store with 30 days of made-up sample numbers, marked as TEST DATA (the /stats page shows a
pink "🧪 TEST DATA" banner for it). For screenshots and trying the dashboard. Refuses to touch Upstash.
Usage: STATS_STORE_FILE=/tmp/chisme-stats-sample.json ./venv/bin/python tools/stats_seed.py"""
import json, os, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stats

if os.environ.get("UPSTASH_REDIS_REST_URL"):
    sys.exit("stats_seed: UPSTASH_REDIS_REST_URL is set; sample data only ever goes to a local file")
path = os.environ.get("STATS_STORE_FILE") or "/tmp/chisme-stats-sample.json"
rnd = random.Random(42)
pool = [f"sample{i:04d}" for i in range(600)]   # made-up visitors (not hashes of anyone)
STORIES = [("Spurs rally late to beat the Suns in overtime", "Express-News"), ("New taquería opens on the West Side", "KSAT"),
           ("City council approves Fiesta route changes", "Texas Public Radio"), ("Cold front brings storms Thursday night", "KENS 5"),
           ("Missions clinch a playoff spot", "MySA"), ("H-E-B announces a new store downtown", "San Antonio Current")]
CITIES = [("San Antonio, TX", 60), ("San Antonio, TX (default)", 14), ("New Braunfels, TX", 9), ("Austin, TX", 7), ("Laredo, TX", 5), ("Houston, TX", 4)]
d = {"days": {}, "stories": {}, "meta": {"sample": True}}
days = stats.last_days(30)
for i, day in enumerate(days):
    n = int(22 + i * 1.9 + rnd.randint(-6, 9) + (14 if i % 7 in (5, 6) else 0))
    vis = rnd.sample(pool[: 160 + i * 12], n)
    app = vis[: int(n * (0.28 + i * 0.006))]
    web = vis[len(app):]
    c = {"open": 0, "open:app": 0, "open:web": 0}
    for v in vis:
        k = rnd.randint(1, 3); c["open"] += k; c["open:app" if v in app else "open:web"] += k
    for tab, w in (("news", 1.0), ("weather", 0.62), ("antojos", 0.48), ("sports", 0.4), ("juegos", 0.3), ("events", 0.22)):
        c["tab:" + tab] = int(c["open"] * w * rnd.uniform(0.8, 1.2))
    for j, (t, s) in enumerate(STORIES):
        k = stats.story_key(f"https://example.com/sample-story-{j}")
        d["stories"][k] = {"t": t, "s": s, "u": f"https://example.com/sample-story-{j}"}
        c["story:" + k] = max(0, int(n * (0.5 - j * 0.07) * rnd.uniform(0.6, 1.3)))
    c["game:loteria"] = int(n * 0.22 * rnd.uniform(0.6, 1.4)); c["game:juan"] = int(n * 0.12 * rnd.uniform(0.5, 1.5))
    c["game"] = c["game:loteria"] + c["game:juan"]
    c["food:yt"] = int(n * 1.6 * rnd.uniform(0.6, 1.4)); c["food:tt"] = int(c["food:yt"] * 0.12); c["food"] = c["food:yt"] + c["food:tt"]
    c["tia"] = int(n * 0.35 * rnd.uniform(0.5, 1.5))
    c["donate:cashapp"] = rnd.randint(0, 3); c["donate:bmc"] = rnd.randint(0, 2); c["donate"] = c["donate:cashapp"] + c["donate:bmc"]
    c["a2hs:shown_auto"] = rnd.randint(1, 5); c["a2hs:got_it"] = rnd.randint(0, c["a2hs:shown_auto"]); c["a2hs:later"] = c["a2hs:shown_auto"] - c["a2hs:got_it"]
    c["a2hs:shown"] = rnd.randint(0, 2)
    for city, w in CITIES:
        c["city:" + city] = int(n * w / 100 * rnd.uniform(0.7, 1.3))
    d["days"][day] = {"c": c, "u": {"all": vis, "app": app, "web": web}}
Path(path).write_text(json.dumps(d))
print(f"stats_seed: 30 days of TEST DATA → {path}")
