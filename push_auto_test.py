"""v45 unit tests (no server, no network: every outside call is mocked). Big-news auto alerts, the owner's send box,
pruning, the storage and the /stats endpoints:
    ./venv/bin/python push_auto_test.py
Checks: the keyword score (major vs routine/soft/sports/follow-ups/not local), the auto-send switch (default off), quiet
hours 10 PM – 7 AM Central (both edges), the 2-a-day cap (and the next day), dedupe (same link, and the same story from
another outlet), Gemini yes / no / HTTP error / timeout / garbage (fail safe: only the strongest keyword scores go out),
recipients (news on, near San Antonio), the payload (serious title, in-app reader link), real pywebpush with a mocked
push service answering 201 / 404 / 410 / 500 (404 + 410 pruned, the rest kept), the owner's send (defaults, link →
in-app reader, bad links refused, counts), kick() (throttled, never blocks), the Upstash REST store (SET NX, INCRBY,
LPUSH/LTRIM …) against a mock, and /stats/push/* (cookie + JSON required, the panel on /stats)."""
import asyncio, base64, json, os, sys, tempfile, threading, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
TMP = tempfile.mkdtemp(prefix="chisme-v45-")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
_k = ec.generate_private_key(ec.SECP256R1())   # throwaway VAPID keys for this run only
for k in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "GEMINI_API_KEY", "PUSH_TEST", "AUTO_PUSH_DAILY_MAX"):
    os.environ.pop(k, None)
os.environ.update({"VAPID_PUBLIC_KEY": b64e(_k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)),
                   "VAPID_PRIVATE_KEY": b64e(_k.private_numbers().private_value.to_bytes(32, "big")), "VAPID_SUBJECT": "mailto:test@example.com",
                   "PUSH_STORE_FILE": os.path.join(TMP, "subs.json"), "STATS_STORE_FILE": os.path.join(TMP, "stats.json"),
                   "ADMIN_TOKEN": "unit-test-admin-token", "AUTO_PUSH_WAKE_DELAY": "3600"})
import httpx, requests
import push, autopush

fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

CT = ZoneInfo("America/Chicago")
at = lambda h, m=0, d=1: datetime(2026, 10, d, h, m, tzinfo=CT).timestamp()
run = lambda c: asyncio.run(c) if not isinstance(c, (dict, list)) else c
MAJOR = lambda i, t, src="KSAT", rel=2: {"title": t, "link": f"https://example.com/{i}", "source": src, "published": t_pub, "summary": "",
                                         "related": [{"source": "x"}] * rel, "tier": "city"}

# ---- mocked sending: endpoint → behaviour
sent = []
def fake_send(rec, payload, urgent, ttl=None):
    ep = rec["sub"]["endpoint"]; sent.append((ep, payload, urgent, ttl))
    return "gone" if "/gone" in ep else "error 500 boom" if "/flaky" in ep else "ok"
push._send_sync = fake_send

def reset():
    for f in os.listdir(TMP):
        os.remove(os.path.join(TMP, f))
    sent.clear(); autopush._verdicts.clear()
def sub(name, lat=29.43, lon=-98.49, news=True):
    return {"subscription": {"endpoint": f"https://push.example.com/{name}", "keys": {"p256dh": "B" + "A" * 86, "auth": "a" * 22}},
            "lat": lat, "lon": lon, "tz": "America/Chicago", "news": news, "weather": True}
async def setup(*subs, on=True):
    for s in subs:
        assert (await push.subscribe(s))["ok"]
    if on:
        await autopush.set_auto(True)

# ---------------------------------------------------------------- 1. the score
t_pub = at(12)
now = t_pub + 600
S = lambda t, **kw: autopush.score({"title": t, "link": "https://e/x", "published": t_pub, **kw}, now)[0]
big = [("BREAKING: SAPD says active shooter at North Star Mall, shoppers told to shelter in place", {}),
       ("Boil water notice issued for much of San Antonio after SAWS main break", {"related": [1, 2]}),
       ("I-10 closed in both directions near downtown San Antonio after tanker explosion", {"related": [1]})]
small = [("Fifth suspect arrested, charged with aggravated kidnapping in fatal Bexar County abduction", {"related": [1, 2]}),
         ("Man killed in crash on I-35 on San Antonio's East Side", {"related": [1]}),
         ("10 best tacos in San Antonio, ranked", {}), ("Spurs beat Lakers as Wembanyama scores 40 in San Antonio", {"related": [1, 2]}),
         ("Opinion: San Antonio needs a better plan for flooding", {}), ("Active shooter reported at a mall in Ohio", {"related": [1, 2]}),
         ("SAWS made its case for a rate increase again to City Council", {"related": [1, 2]})]
check(all(S(t, **kw) >= autopush.STRICT_MIN for t, kw in big), f"major local stories score ≥ {autopush.STRICT_MIN}: {[S(t, **kw) for t, kw in big]}")
check(all(S(t, **kw) < autopush.CANDIDATE_MIN for t, kw in small), f"routine crime, a single crash, lists, sports, opinion, out-of-town, council business stay < {autopush.CANDIDATE_MIN}: {[S(t, **kw) for t, kw in small]}")

# ---------------------------------------------------------------- 2. switch, quiet hours, cap, dedupe
async def scenario():
    reset(); await setup(sub("a"), sub("b"), on=False)
    news = [MAJOR(1, big[0][0])]
    r = await autopush.check(None, now=now, fake_news=news)
    check(r["result"] == "auto-send is off" and not sent, f"auto-send is off by default: nothing sent ({r['result']})")
    await autopush.set_auto(True)
    for h, m in ((22, 0), (23, 59), (3, 0), (6, 59)):
        r = await autopush.check(None, now=at(h, m), fake_news=[{**news[0], "published": at(h, m) - 60}])
        check(r["result"].startswith("quiet hours") and not sent, f"{h:02d}:{m:02d} CT: quiet hours, nothing sent")
    r = await autopush.check(None, now=at(7, 0), fake_news=[{**news[0], "published": at(7, 0) - 60}])
    check(r["result"].startswith("sent") and len(sent) == 2, f"7:00 AM CT: the major story goes to both subscribers ({r['result'][:60]})")
    p = sent[0][1]
    check(p["title"] == "Breaking news" and p["body"].startswith(big[0][0]) and p["body"].endswith("— KSAT"), f"serious wording: '{p['title']}' / '{p['body'][:50]}…'")
    check(p["url"].startswith("/?story=https%3A%2F%2Fexample.com%2F1") and p["url"].endswith("#news") and sent[0][2] is True, f"tap → Chisme's in-app reader link ({p['url'][:48]}…), high urgency")
    n0 = len(sent)
    r = await autopush.check(None, now=at(7, 30), fake_news=[{**news[0], "published": at(7, 25)}])
    check(len(sent) == n0 and r["result"] == "nothing major", f"the same link is never pushed twice ({r['result']})")
    other = {**MAJOR(99, "SAPD: active shooter at North Star Mall, shoppers told to shelter in place — what we know", src="KENS 5"), "published": at(7, 40)}
    r = await autopush.check(None, now=at(7, 45), fake_news=[other])
    check(len(sent) == n0, f"…nor the same story from another outlet (headline fingerprint) ({r['result']})")
    r = await autopush.check(None, now=at(9), fake_news=[{**MAJOR(2, big[1][0]), "published": at(8, 50)}])
    check(r["result"].startswith("sent") and len(sent) == n0 + 2, "a second major story the same day: sent (2 of 2)")
    n0 = len(sent)
    r = await autopush.check(None, now=at(11), fake_news=[{**MAJOR(3, big[2][0]), "published": at(10, 50)}])
    check(r["result"].startswith("daily cap") and len(sent) == n0, f"a third one the same day: held by the hard cap ({r['result']})")
    os.environ["AUTO_PUSH_DAILY_MAX"] = "9"
    check(autopush.daily_max() == 2, "AUTO_PUSH_DAILY_MAX can't raise the cap above 2")
    os.environ.pop("AUTO_PUSH_DAILY_MAX")
    r = await autopush.check(None, now=at(8, d=2), fake_news=[{**MAJOR(3, big[2][0]), "published": at(7, 55, d=2)}])
    check(r["result"].startswith("sent") and len(sent) == n0 + 2, "next day (Central time): it goes out")
    stale = {**MAJOR(4, "BREAKING: Explosion and evacuations at San Antonio plant, shelter in place ordered"), "published": at(8, d=2) - 4 * 3600}
    r = await autopush.check(None, now=at(9, d=2), fake_news=[stale])
    check(r["considered"] == 0 and len(sent) == n0 + 2, "a story older than 3 hours is never pushed")
    log = await autopush.recent("log", 10)
    check(len(log) == 3 and log[0]["title"].startswith("I-10 closed") and log[0]["sent"] == 2 and "urgent" in " ".join(log[0]["why"]), f"the /stats log keeps each auto push (newest first, {len(log)} entries, sent/failed, why)")
asyncio.run(scenario())

# ---------------------------------------------------------------- 3. recipients
async def recipients():
    reset(); await setup(sub("sa"), sub("nb", 29.70, -98.12), sub("austin", 30.27, -97.74), sub("houston", 29.76, -95.37), sub("off", news=False))
    r = await autopush.check(None, now=at(12), fake_news=[{**MAJOR(5, big[0][0]), "published": at(11, 55)}])
    eps = sorted(e.rsplit("/", 1)[1] for e, *_ in sent)
    check(eps == ["nb", "sa"], f"auto push goes to news subscribers within {autopush.radius_km()} km of San Antonio only: {eps}")
    reset(); await setup(sub("houston", 29.76, -95.37))
    r = await autopush.check(None, now=at(12), fake_news=[{**MAJOR(5, big[0][0]), "published": at(11, 55)}])
    check(not sent and "nobody" in r["result"] and await autopush.today_count(at(12)) == 0, "nobody nearby: nothing sent and the daily cap isn't spent")
asyncio.run(recipients())

# ---------------------------------------------------------------- 4. Gemini (mocked) and fail safe
real_client = httpx.AsyncClient
def gemini_mock(handler):
    autopush.httpx.AsyncClient = lambda *a, **kw: real_client(transport=httpx.MockTransport(handler))
def gem_answer(arr):
    return lambda req: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(arr)}]}}]})
async def gemini():
    os.environ["GEMINI_API_KEY"] = "test-key-not-real"
    mid = {**MAJOR(6, "Tornado damage reported in Leon Valley neighborhood, crews responding"), "published": at(11, 55), "related": []}
    sc = autopush.score(mid, at(12))[0]
    check(autopush.CANDIDATE_MIN <= sc < autopush.STRICT_MIN, f"a mid-score story ({sc}) needs Gemini's yes")
    seen = {}
    def yes(req):
        seen["key"] = req.headers.get("x-goog-api-key"); seen["body"] = json.loads(req.content)
        return gem_answer([{"i": 0, "major": True, "why": "tornado damage in the city"}])(req)
    for name, handler, want in (("says yes", yes, True), ("says no", gem_answer([{"i": 0, "major": False, "why": "minor"}]), False),
                                ("HTTP 429", lambda r: httpx.Response(429, json={}), False), ("HTTP 500", lambda r: httpx.Response(500), False),
                                ("garbage", lambda r: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "lol not json"}]}}]}), False),
                                ("timeout", lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow")), False)):
        reset(); await setup(sub("a")); gemini_mock(handler)
        r = await autopush.check(None, now=at(12), fake_news=[mid])
        check(bool(sent) == want, f"Gemini {name}: {'sent' if sent else 'not sent'} ({r['result'][:70]})")
    check(seen.get("key") == "test-key-not-real" and "San Antonio" in seen["body"]["contents"][0]["parts"][0]["text"], "Gemini gets the key in x-goog-api-key and a strict San Antonio prompt")
    reset(); await setup(sub("a")); gemini_mock(lambda r: httpx.Response(503))
    r = await autopush.check(None, now=at(12), fake_news=[{**MAJOR(7, big[0][0]), "published": at(11, 55)}])
    check(len(sent) == 1 and "keywords only" in json.dumps(await autopush.recent("log", 1)), "Gemini down + a very strong story: it still goes out (keywords only)")
    reset(); await setup(sub("a")); gemini_mock(gem_answer([{"i": 0, "major": False, "why": "not urgent"}]))
    r = await autopush.check(None, now=at(12), fake_news=[{**MAJOR(7, big[0][0]), "published": at(11, 55)}])
    check(not sent, "Gemini says no: even a high keyword score isn't sent")
    os.environ.pop("GEMINI_API_KEY"); autopush.httpx.AsyncClient = real_client
asyncio.run(gemini())

# ---------------------------------------------------------------- 5. real pywebpush, mocked push service: 404 / 410 pruned
push._send_sync = push.__dict__["_send_sync"] = None or __import__("importlib").reload(push)._send_sync   # the real one
import autopush as _ap; autopush = __import__("importlib").reload(_ap)
codes = {"ok": 201, "gone410": 410, "gone404": 404, "flaky": 500}
calls = []
class FakeResp:
    def __init__(self, code): self.status_code, self.text, self.content, self.headers, self.reason = code, "", b"", {}, "mock"
def fake_post(url, data=None, headers=None, timeout=None, **kw):
    calls.append((url, headers)); return FakeResp(codes[url.rsplit("/", 1)[1]])
requests.post = fake_post
async def prune():
    reset()
    for n in codes:
        ph = ec.generate_private_key(ec.SECP256R1())
        s = {"subscription": {"endpoint": f"https://fcm.googleapis.com/fcm/send/{n}", "keys": {"p256dh": b64e(ph.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)), "auth": b64e(os.urandom(16))}},
             "lat": 29.43, "lon": -98.49}
        assert (await push.subscribe(s))["ok"]
    r = await autopush.admin_send({"title": "Chisme", "message": "Test", "link": ""})
    left = sorted(x["sub"]["endpoint"].rsplit("/", 1)[1] for x in (await push.store().all()).values())
    auth = calls[0][1].get("Authorization", "") if calls else ""
    check(r["ok"] and (r["sent"], r["failed"], r["removed"], r["total"]) == (1, 3, 2, 4), f"owner send through real pywebpush: sent {r['sent']}, failed {r['failed']}, pruned {r['removed']} of {r['total']}")
    check(left == ["flaky", "ok"], f"404 and 410 subscriptions deleted, a 500 is kept for next time ({left})")
    check(auth.startswith("vapid t=") and calls[0][1].get("Content-Encoding") == "aes128gcm", "real VAPID header + aes128gcm body")
asyncio.run(prune())

# ---------------------------------------------------------------- 6. the owner's payload
P = autopush.admin_payload
p, _ = P({})
check(p and p["title"] == "Chisme" and p["body"] == "¡Órale, new chisme! 👀" and p["url"] == "/#news", f"defaults: '{p['title']}' / '{p['body']}' → {p['url']}")
p, _ = P({"title": "Heads up", "message": "Big story", "link": "https://www.ksat.com/news/local/2026/10/01/x/"})
check(p["url"].startswith("/?story=https%3A%2F%2Fwww.ksat.com") and p["url"].endswith("#news"), "a story link opens in the in-app reader, not a browser tab")
check(P({"message": "x", "link": "/#weather"})[0]["url"] == "/#weather", "an app path (/#weather) is kept")
check(all(P({"message": "x", "link": l})[0] is None for l in ("javascript:alert(1)", "//evil.example", "ftp://x/y", "data:text/html,hi")), "javascript:, //host, ftp:, data: links are refused")
check(P({"message": "   "})[0] is None and len(P({"message": "y" * 999})[0]["body"]) == 240, "an empty message is refused; long ones are cut to 240")

# ---------------------------------------------------------------- 7. kick(): throttled + non-blocking
async def kicks():
    reset(); autopush._last_kick = 0
    started = asyncio.Event()
    async def slow_stories():
        started.set(); await asyncio.sleep(0.5); return []
    await autopush.set_auto(True)
    t0 = time.perf_counter(); k1 = autopush.kick(slow_stories, now=at(12)); dt = time.perf_counter() - t0
    k2 = autopush.kick(slow_stories, now=at(12) + 60)
    await asyncio.wait_for(started.wait(), 2); await asyncio.sleep(0.7)
    k3 = autopush.kick(slow_stories, now=at(12) + autopush.check_every() + 1)
    check(k1 and dt < 0.02 and not k2 and k3, f"kick(): starts a background check without waiting ({dt * 1000:.1f} ms), then not again for {autopush.check_every() // 60} min")
    await asyncio.sleep(0.7)
asyncio.run(kicks())

# ---------------------------------------------------------------- 8. Upstash REST store (mock)
R, ucalls = {}, []
class U(BaseHTTPRequestHandler):
    def do_POST(self):
        cmd = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0))); ucalls.append((self.headers.get("Authorization"), cmd))
        op, key, *a = cmd
        def SET():
            if "NX" in a and key in R: return None
            R[key] = a[0]; return "OK"
        def INCRBY():
            R[key] = str(int(R.get(key, 0)) + int(a[0])); return int(R[key])
        def LPUSH():
            R.setdefault(key, []).insert(0, a[0]); return len(R[key])
        def LTRIM():
            R[key] = R.get(key, [])[int(a[0]):int(a[1]) + 1]; return "OK"
        h = lambda: R.setdefault(key, {})
        res = {"SET": SET, "GET": lambda: R.get(key), "INCRBY": INCRBY, "EXPIRE": lambda: 1, "LPUSH": LPUSH, "LTRIM": LTRIM,
               "LRANGE": lambda: R.get(key, [])[int(a[0]):int(a[1]) + 1], "HSET": lambda: (h().__setitem__(a[0], a[1]), 1)[1],
               "HGET": lambda: h().get(a[0]), "HDEL": lambda: int(h().pop(a[0], None) is not None), "HLEN": lambda: len(h()),
               "HGETALL": lambda: [x for kv in h().items() for x in kv]}[op]()
        out = json.dumps({"result": res}).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass
us = ThreadingHTTPServer(("127.0.0.1", 0), U); threading.Thread(target=us.serve_forever, daemon=True).start()
os.environ.update({"UPSTASH_REDIS_REST_URL": f'"http://127.0.0.1:{us.server_port}"', "UPSTASH_REDIS_REST_TOKEN": "UPSTASH_REDIS_REST_TOKEN=tok-xyz"})
async def upstash():
    st = push.store()
    a = await st.kv_setnx("k1", 1, ex=60); b = await st.kv_setnx("k1", 2, ex=60)
    n1 = await st.kv_incr("c", 1, ex=60); n2 = await st.kv_incr("c", 1, ex=60); n3 = await st.kv_incr("c", -1)
    for i in range(35):
        await st.list_push("L", json.dumps({"i": i}), 30)
    L = await st.list_get("L", 50)
    await autopush.set_auto(True); on = await autopush.auto_on()
    return st.name, a, b, (n1, n2, n3), len(L), json.loads(L[0])["i"], on
name, a, b, ns, nL, first, on = asyncio.run(upstash())
check(name == "upstash" and a is True and b is False, "Upstash: SET NX claims a story once (the dedupe)")
check(ns == (1, 2, 1) and nL == 30 and first == 34 and on is True, f"Upstash: INCRBY counter {ns}, LPUSH+LTRIM log keeps 30 (newest first), the switch round-trips")
check(all(h == "Bearer tok-xyz" for h, _ in ucalls), "forgiving env values (quotes, NAME=) via stats.upstash_conf; token sent as Bearer")
us.shutdown()
for k in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"):
    os.environ.pop(k)

# ---------------------------------------------------------------- 9. /stats/push/* endpoints (FastAPI, no startup → no network)
import app as A
from fastapi.testclient import TestClient
autopush._last_kick = time.time() + 10 ** 6   # no background checks from these requests
A.autopush._last_kick = autopush._last_kick
reset()
_ph = ec.generate_private_key(ec.SECP256R1())
asyncio.run(push.subscribe({**sub("x"), "subscription": {"endpoint": "https://push.example.com/x", "keys": {"p256dh": b64e(_ph.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)), "auth": b64e(os.urandom(16))}}}))
requests.post = lambda url, **kw: FakeResp(201)
c = TestClient(A.app)
r0 = c.post("/stats/push/send", json={"message": "hi"})
r1 = c.post("/stats/push/auto", json={"on": True})
check(r0.status_code == 401 and r1.status_code == 401, "send / switch without the admin cookie: 401")
c.get("/stats?key=wrong"); r = c.get("/stats", follow_redirects=False)
check(r.status_code == 401 and "Send a notification" not in r.text, "/stats with a wrong key: the gate page, no send box")
c.get("/stats?key=unit-test-admin-token", follow_redirects=False)
c.cookies.set(A.stats.COOKIE, A.stats.session_value(), path="/stats")
r = c.get("/stats")
check(r.status_code == 200 and "Send a notification" in r.text and "Auto-send is off" in r.text and "¡Órale, new chisme! 👀" in r.text and "<b>1</b> subscriber will get it" in r.text,
      "/stats (admin): send box with the default message, the subscriber count, the auto-send switch (off)")
r = c.post("/stats/push/send", content="message=hi", headers={"Content-Type": "application/x-www-form-urlencoded"})
check(r.status_code == 401, "a form post (cross-site style) is refused even with the cookie: JSON only")
r = c.post("/stats/push/send", json={"title": "Chisme", "message": "¡Órale, new chisme! 👀", "link": "https://example.com/s"})
check(r.status_code == 200 and r.json()["sent"] == 1 and r.json()["failed"] == 0, f"owner send: {r.json()}")
r = c.post("/stats/push/send", json={"message": "x", "link": "javascript:alert(1)"})
check(r.status_code == 400 and "https" in r.json()["error"], "a bad link: 400 with a reason")
r = c.post("/stats/push/auto", json={"on": True}); r2 = c.get("/stats")
check(r.json() == {"ok": True, "on": True} and "Auto-send is on" in r2.text, "the auto-send switch saves (and /stats shows it on)")
r = c.post("/stats/push/auto", json={"on": "yes"})
check(r.status_code == 400, "the switch only takes true/false")
check(c.get("/api/push/key").json()["publicKey"] == os.environ["VAPID_PUBLIC_KEY"], "/api/push/key serves the VAPID public key (applicationServerKey)")

print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)
