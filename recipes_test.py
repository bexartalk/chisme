"""v40: the cooking / recipe videos in data/recipe_videos.json are real, public and embeddable, from many cooks, and the
food API serves them for the Bigger the Pansa, Better the Chansa feed. Needs the network (YouTube oEmbed) and the app on
CHISME_URL (default http://localhost:8211)."""
import collections, json, os, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); URL = os.environ.get("CHISME_URL", "http://localhost:8211").rstrip("/")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
doc = json.load(open(os.path.join(HERE, "data", "recipe_videos.json")))
V = doc["videos"]; ids = [v["id"] for v in V]
check(len(V) >= 40 and len(set(ids)) == len(ids) and all(re.fullmatch(r"[\w-]{11}", i) for i in ids), f"{len(V)} recipe videos, unique YouTube ids")
by = collections.Counter(v["creator"] for v in V)
check(len(by) >= 35 and max(by.values()) <= 2, f"{len(by)} different cooks, at most {max(by.values())} videos each")
topics = collections.Counter(v["topic"] for v in V)
need = {"spaghetti", "tacos", "enchiladas", "dinner", "dessert", "hack"}
check(need <= set(topics), f"topics: {dict(topics)}")
check(all(v.get("verified") and v.get("channel_url", "").startswith("https://www.youtube.com/") for v in V), "each has its channel link and the date it was checked")
def oembed(i):
    try:
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={i}&format=json", timeout=20) as r:
            return i, r.status, json.load(r).get("author_name")
    except urllib.error.HTTPError as e:
        return i, e.code, None
    except Exception as e:
        return i, 0, str(e)[:60]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(oembed, ids))
bad = [r for r in res if r[1] != 200]
check(not bad, f"YouTube oEmbed: {len(res) - len(bad)}/{len(res)} are public + embeddable right now (200){' — bad: ' + str(bad) if bad else ''}")
names = {v["id"]: v["creator"] for v in V}
check(all(r[2] is None or r[2].strip() == names[r[0]] for r in res), "the creator in the file matches YouTube's channel name for every video")
try:
    with urllib.request.urlopen(URL + "/api/food?lat=29.4241&lon=-98.4936", timeout=120) as r:
        d = json.load(r)
    rec = d.get("recipes") or []
    check(len(rec) >= 40 and all(x["kind"] == "recipe" and x["video"] and x["url"].startswith("https://www.youtube.com/shorts/") and x["crew"].startswith("cook:") for x in rec),
          f"/api/food serves {len(rec)} recipe videos (kind recipe, Shorts URLs, one crew key per cook)")
    check(not any(x.get("recipe") for x in d.get("items", [])), "recipes aren't mixed into the Latest list of San Antonio food news")
except Exception as e:
    check(False, f"/api/food ({e})")
print("ALL PASS" if not fails else f"{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
