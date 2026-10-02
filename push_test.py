"""End-to-end Web Push test, no real push service: a local mock push service receives what Chisme sends, checks the
VAPID signature (ES256 JWT with Chisme's public key) and decrypts each message (aes128gcm, RFC 8291) with the
subscriber's own private key, like a phone would. Runs against the local server started with the test env:
    CHISME_ENV=/path/to/local.env PUSH_TEST=1 ./run.sh      (PUSH_TEST=1 allows the fake clock/feeds and http://localhost endpoints)
Checks: config + /api/push/key, subscription validation, tick auth, the quiet first look, v45 big-news auto push
(off until the owner switches it on in /stats; title "Breaking news", headline body, in-app reader link; routine
stories never; the same story never twice; 2 a day at most), NWS warnings/watches (title '⚠️ <event>', high
urgency), quiet hours 10 PM–7 AM (warnings only; big news waits too), the test notification + its 1/min limit,
the owner's send box (/stats/push/send) and expired subscriptions (410) removed, news off, unsubscribe, the Upstash
REST store, and that no private key is in the repo. Unit tests with mocks: push_auto_test.py."""
import base64, json, os, subprocess, sys, threading, time, urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo
import httpx, http_ece
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
ENV = os.environ.get("CHISME_ENV", "/workspace/secrets/chisme-local.env")   # needs ADMIN_TOKEN too (v45: the auto-send switch)
env = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l and not l.startswith("#"))
SECRET, PUB = env["PUSH_TICK_SECRET"], env["VAPID_PUBLIC_KEY"]
STORE = env.get("PUSH_STORE_FILE", "/tmp/chisme-push.json")
MOCK = int(os.environ.get("PUSH_MOCK_PORT", "8377"))
b64d = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

# ---- a phone: its own key pair + auth secret, and the mock push service it "lives" behind
class Phone:
    def __init__(self, name):
        self.priv = ec.generate_private_key(ec.SECP256R1()); self.auth = os.urandom(16); self.name = name
        pub = self.priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.sub = {"endpoint": f"http://localhost:{MOCK}/push/{name}", "keys": {"p256dh": b64e(pub), "auth": b64e(self.auth)}}
got = []   # (phone name, headers, body bytes)
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        name = self.path.rsplit("/", 1)[-1]
        got.append((name, {k.lower(): v for k, v in self.headers.items()}, body))
        self.send_response(410 if name.startswith("gone") else 201); self.end_headers()
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(("127.0.0.1", MOCK), H); threading.Thread(target=srv.serve_forever, daemon=True).start()

def open_msg(phone, body):
    return json.loads(http_ece.decrypt(body, private_key=phone.priv, auth_secret=phone.auth, version="aes128gcm"))
def vapid_ok(headers):
    a = headers.get("authorization") or ""
    if not a.startswith("vapid "):
        return False, "no vapid header"
    parts = dict(p.strip().split("=", 1) for p in a[6:].split(","))
    if parts.get("k") != PUB:
        return False, "wrong k"
    h, p, sig = parts["t"].split(".")
    claims = json.loads(b64d(p)); raw = b64d(sig)
    der = utils.encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64d(PUB))
    try:
        key.verify(der, f"{h}.{p}".encode(), ec.ECDSA(hashes.SHA256()))
    except Exception:
        return False, "bad signature"
    return claims.get("aud") == f"http://localhost:{MOCK}" and claims.get("sub") == env["VAPID_SUBJECT"] and claims["exp"] > time.time(), claims

c = httpx.Client(base_url=BASE, timeout=60)
tick = lambda body, auth=SECRET: c.post("/api/push/tick", json=body, headers={"Authorization": f"Bearer {auth}"} if auth else {})
CT = ZoneInfo("America/Chicago")
at = lambda h, m=0, day=30: datetime(2026, 9, day, h, m, tzinfo=CT).timestamp()
def story(i, t_pub): return {"title": f"Story {i}: something happened on the Westside", "link": f"https://example.com/news/{i}", "source": "KSAT", "published": t_pub}
def alert(i, event): return {"id": f"urn:oid:test.{i}", "event": event, "headline": f"{event} issued for Bexar County until 9:00 PM CDT", "areaDesc": "Bexar, TX", "severity": "Severe"}

# ---- 1. config + subscribe
for f in (STORE, STORE.rsplit(".", 1)[0] + ".state.json"):
    if os.path.exists(f): os.remove(f)
cfg = c.get("/api/push/config").json()
check(cfg["enabled"] and cfg["publicKey"] == PUB and cfg["store"] == "file" and cfg["dailyMax"] == 2, f"config: enabled, public key served, store '{cfg['store']}', 2 news alerts a day max")
check(c.get("/api/push/key").json() == {"publicKey": PUB}, "/api/push/key: the applicationServerKey")
check(c.post("/api/push/subscribe", json={"subscription": {"endpoint": "ftp://x", "keys": {}}, "lat": 29.4, "lon": -98.5}).status_code == 400, "a bad subscription is refused")
A = Phone("phoneA")
r = c.post("/api/push/subscribe", json={"subscription": A.sub, "lat": 29.42412, "lon": -98.49363, "tz": "America/Chicago", "news": True, "weather": True}).json()
check(r["ok"], "subscribe: ok")
rec = list(json.load(open(STORE)).values())[0]
check(rec["lat"] == 29.42 and rec["lon"] == -98.49, f"the stored area is rounded to ~1 km ({rec['lat']}, {rec['lon']})")
# ---- 2. tick auth
check(tick({}, auth=None).status_code == 401 and tick({}, auth="nope").status_code == 401, "tick without / with a wrong secret: 401")
# ---- 3. first look: nothing sent; big news: off until the owner switches it on
t0 = at(15)
def major(i, t_pub, title=None):
    return {"title": title or f"BREAKING: SAPD says active shooter at North Star Mall #{i}, shoppers told to shelter in place", "link": f"https://example.com/big/{i}",
            "source": "KSAT", "published": t_pub, "summary": "", "related": [{"source": "KENS 5"}, {"source": "Express-News"}], "tier": "city"}
news = [story(1, t0 - 1800), story(2, t0 - 3600), major(1, t0 - 600)]; alerts = [alert(1, "Heat Advisory")]
j = tick({"now": t0, "fake": {"news": news, "alerts": alerts}}).json()
check(j["primed"] == 1 and j["auto"]["result"] == "auto-send is off" and not got, f"first check: alerts only recorded; auto-send is off by default, nothing sent ({j['auto']['result']})")
c.post("/stats/login", data={"key": env["ADMIN_TOKEN"], "remember": "1"}, follow_redirects=False)   # v49.11: the sign-in form (?key= no longer signs in)
check(c.post("/stats/push/auto", json={"on": True}).json() == {"ok": True, "on": True}, "the owner switches auto-send on (/stats, admin cookie)")
# ---- 4. a major story → one push, routine ones never
j = tick({"now": t0 + 600, "fake": {"news": news, "alerts": alerts}}).json()
time.sleep(0.3)
check(j["auto"]["result"].startswith("sent") and len(got) == 1, f"major breaking local story → 1 push ({j['auto']['result'][:60]})")
if got:
    name, hd, body = got[-1]; msg = open_msg(A, body); ok, claims = vapid_ok(hd)
    check(msg["title"] == "Breaking news", f"title: '{msg['title']}' (serious wording)")
    check(msg["body"].startswith("BREAKING: SAPD says active shooter at North Star Mall #1") and msg["body"].endswith("— KSAT"), f"body is the headline: '{msg['body'][:60]}…'")
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(msg["url"]).query)
    check(msg["url"].startswith("/?") and q["story"] == ["https://example.com/big/1"] and msg["url"].endswith("#news"), f"tap opens it in Chisme's reader: {msg['url'][:70]}")
    check(ok is True, f"VAPID: ES256 JWT signed with Chisme's key, aud = the push service, sub = VAPID_SUBJECT ({claims if ok is not True else 'verified'})")
    check(hd.get("content-encoding") == "aes128gcm" and int(hd.get("ttl", 0)) > 0 and hd.get("urgency") == "high", f"encrypted aes128gcm, TTL {hd.get('ttl')} s, Urgency {hd.get('urgency')}")
# ---- 5. never twice; 2 a day
n0 = len(got); news = [story(3, t0 + 900)] + news
j = tick({"now": t0 + 1200, "fake": {"news": news, "alerts": alerts}}).json()
check(len(got) == n0 and j["auto"]["result"] == "nothing major", f"the same story isn't sent twice, and a routine new story never is ({j['auto']['result']})")
news = [major(2, t0 + 1500, "Boil water notice issued for much of San Antonio after SAWS main break")] + news
j = tick({"now": t0 + 1800, "fake": {"news": news, "alerts": alerts}}).json(); time.sleep(0.3)
check(len(got) == n0 + 1 and open_msg(A, got[-1][2])["body"].startswith("Boil water notice"), "a second major story: sent (2 of 2 today)")
news = [major(3, t0 + 2000, "I-10 closed in both directions near downtown San Antonio after tanker explosion")] + news
n0 = len(got); j = tick({"now": t0 + 2400, "fake": {"news": news, "alerts": alerts}}).json()
check(len(got) == n0 and j["auto"]["result"].startswith("daily cap"), f"a third: held by the daily cap ({j['auto']['result']})")
# ---- 6. weather: advisories never, warnings/watches once, with high urgency for warnings
t1 = t0 + 2 * 3600
alerts = [alert(1, "Heat Advisory"), alert(2, "Tornado Warning")]
n0 = len(got); j = tick({"now": t1, "fake": {"news": news, "alerts": alerts}}).json(); time.sleep(0.3)
m = open_msg(A, got[-1][2]) if len(got) > n0 else {}
check(j["weather"] == 1 and m.get("title") == "⚠️ Tornado Warning" and m.get("url") == "/#alerts", f"NWS Tornado Warning → '{m.get('title')}' ({m.get('body', '')[:60]})")
check(got[-1][1].get("urgency") == "high", f"warnings go out with Urgency: {got[-1][1].get('urgency')}")
j = tick({"now": t1 + 600, "fake": {"news": news, "alerts": alerts}}).json()
check(j["weather"] == 0, "the same warning isn't sent twice; the Heat Advisory is never pushed")
# ---- 7. quiet hours (11:30 PM, the next day): big news + watches wait, warnings still come through
tq = at(23, 30, day=1) if False else datetime(2026, 10, 1, 23, 30, tzinfo=CT).timestamp()
news = [major(4, tq - 300, "BREAKING: Explosion at Port San Antonio plant, nearby homes evacuated")] + news
alerts += [alert(3, "Flood Watch"), alert(4, "Severe Thunderstorm Warning")]
n0 = len(got); j = tick({"now": tq, "fake": {"news": news, "alerts": alerts}}).json(); time.sleep(0.3)
titles = [open_msg(A, b)["title"] for _, _, b in got[n0:]]
check(titles == ["⚠️ Severe Thunderstorm Warning"] and j["quiet"] >= 1 and j["auto"]["result"].startswith("quiet hours"), f"11:30 PM: only the warning comes through {titles} (big news: {j['auto']['result']})")
# ---- 8. morning: the watch (still active) goes out; last night's big story is too old to push
tm = datetime(2026, 10, 2, 7, 30, tzinfo=CT).timestamp()
n0 = len(got); j = tick({"now": tm, "fake": {"news": news, "alerts": alerts}}).json(); time.sleep(0.3)
titles = [open_msg(A, b)["title"] for _, _, b in got[n0:]]
check(titles == ["⚠️ Flood Watch"] and j["auto"]["considered"] == 0, f"7:30 AM: the Flood Watch goes out, last night's story doesn't (only stories < 3 h old) {titles}")
# ---- 9. test notification
r1 = c.post("/api/push/test", json={"endpoint": A.sub["endpoint"]}); time.sleep(0.3)
r2 = c.post("/api/push/test", json={"endpoint": A.sub["endpoint"]})
check(r1.status_code == 200 and open_msg(A, got[-1][2])["title"] == "Chisme alerts are on 🔔" and r2.status_code == 400, "Send a test: one sample notification, then 'wait a minute'")
# ---- 10. the owner's send box; an expired subscription (410 Gone) is removed
G = Phone("gone1")
c.post("/api/push/subscribe", json={"subscription": G.sub, "lat": 29.42, "lon": -98.49, "tz": "America/Chicago"})
n0 = len(got); j = c.post("/stats/push/send", json={"title": "Chisme", "message": "¡Órale, new chisme! 👀", "link": "https://example.com/owner/1"}).json(); time.sleep(0.3)
mine = [open_msg(A, b) for n, _, b in got[n0:] if n == "phoneA"]
ids = list(json.load(open(STORE)).keys())
check(j["ok"] and (j["sent"], j["failed"], j["removed"]) == (1, 1, 1) and len(ids) == 1, f"owner send: sent {j['sent']}, failed {j['failed']} (410 Gone → removed {j['removed']}, {len(ids)} left)")
check(mine and mine[0]["title"] == "Chisme" and mine[0]["body"] == "¡Órale, new chisme! 👀" and "story=https%3A%2F%2Fexample.com%2Fowner%2F1" in mine[0]["url"], "the owner's note arrives, its link opens in the in-app reader")
check(httpx.post(BASE + "/stats/push/send", json={"message": "x"}).status_code == 401, "the send box needs the admin cookie (a client without it: 401)")
# ---- 11. news off / unsubscribe
c.post("/api/push/subscribe", json={"subscription": A.sub, "lat": 29.42, "lon": -98.49, "tz": "America/Chicago", "news": False, "weather": True})
n0 = len(got); news3 = [major(5, tm + 3 * 3600, "BREAKING: SAPD manhunt after officers shot on the West Side, residents told to shelter in place")] + news
j = tick({"now": tm + 3 * 3600 + 60, "fake": {"news": news3, "alerts": alerts}}).json()
check(len(got) == n0 and "nobody" in j["auto"]["result"], f"news alerts off: no news push ({j['auto']['result'][:60]})")
c.post("/api/push/unsubscribe", json={"endpoint": A.sub["endpoint"]})
check(json.load(open(STORE)) == {}, "Turn off alerts: the subscription and its area are deleted from the server")
c.post("/stats/push/auto", json={"on": False})
# ---- 12. the Upstash Redis store (what Render uses) against a mock of Upstash's REST API
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import push as P
R, calls = {}, []
class U(BaseHTTPRequestHandler):
    def do_POST(self):
        cmd = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0))); calls.append((self.headers.get("Authorization"), cmd))
        op, key, *a = cmd; hsh = R.setdefault(key, {})
        res = {"HSET": lambda: (hsh.__setitem__(a[0], a[1]), 1)[1], "HGET": lambda: hsh.get(a[0]), "HDEL": lambda: int(hsh.pop(a[0], None) is not None),
               "HLEN": lambda: len(hsh), "HGETALL": lambda: [x for kv in hsh.items() for x in kv]}[op]()
        out = json.dumps({"result": res}).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass
us = ThreadingHTTPServer(("127.0.0.1", MOCK + 1), U); threading.Thread(target=us.serve_forever, daemon=True).start()
os.environ.update({"UPSTASH_REDIS_REST_URL": f"http://127.0.0.1:{MOCK + 1}", "UPSTASH_REDIS_REST_TOKEN": "tok-123"})
async def upstash_roundtrip():
    st = P.store(); await st.put({"id": "abc", "lat": 29.42}); await st.put({"id": "def", "lat": 30.27})
    a = await st.all(); g = await st.get("abc"); n = await st.count(); await st.delete("abc")
    return st.name, sorted(a), g, n, await st.count()
name, keys, g, n, n2 = asyncio.run(upstash_roundtrip())
check(name == "upstash" and keys == ["abc", "def"] and g == {"id": "abc", "lat": 29.42} and (n, n2) == (2, 1) and all(h == "Bearer tok-123" for h, _ in calls),
      f"Upstash store: put/get/all/count/delete over the REST API with the token ({[c[1][0] for c in calls]})")
us.shutdown()
# ---- 13. no secrets in git
tracked = subprocess.run(["git", "grep", "-l", "-e", env["VAPID_PRIVATE_KEY"]], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
check(not tracked and env["PUSH_TICK_SECRET"] not in open(__file__).read(), "the VAPID private key and tick secret are nowhere in the repo")
srv.shutdown()
print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)
