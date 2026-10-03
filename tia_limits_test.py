"""v49.12: Tía's daily limits (limits.DailyCounter + app.tia_gate + mascot.chat(gate=…)).
  • the day is Chicago's: 11:59:59 PM and 12:00:01 AM CT are different days; counters expire ~1 h after midnight CT
  • Upstash: one pipeline (INCRBY + EXPIRE), keys hashed (no raw device ids); if Upstash fails, memory (never fails open)
  • per phone: 20 AI answers a day (device id from the phone, else the IP); the 21st doesn't call Gemini and says
    "Tía needs her cafecito — come back tomorrow, metiche ☕", plus an answer straight from the feeds
  • global: TIA_DAILY_GLOBAL_CAP (default 1500) across everyone → "Tía's taking a siesta 😴 …", no Gemini call
  • a new Chicago day starts fresh; the crisis reply (988) works past every cap (and past the hourly limit), never calls Gemini
  • replies that don't use the AI (no key) are never counted or capped
  • /stats (signed in) shows today's usage: AI answers / cap, phones, phones at their limit, turned-away counts
    ./venv/bin/python tia_limits_test.py"""
import asyncio, json, os, sys, threading, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
for k in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MASCOT_PROVIDER"):
    os.environ.pop(k, None)
import socket
with socket.socket() as _so:   # a free port for the mock Gemini
    _so.bind(("127.0.0.1", 0)); MOCK = _so.getsockname()[1]
os.environ.update(ADMIN_TOKEN="unit-test-admin-token", GEMINI_API_KEY="AQ.test-key-not-real", GEMINI_API_BASE=f"http://127.0.0.1:{MOCK}",
                  TIA_DEVICE_DAILY_CAP="20", TIA_DAILY_GLOBAL_CAP="30", MASCOT_PER_HOUR="1000")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
CT = ZoneInfo("America/Chicago")
ts = lambda *a: datetime(*a, tzinfo=CT).timestamp()

class Gemini(BaseHTTPRequestHandler):
    hits = 0
    def log_message(self, *a): pass
    def do_POST(self):
        Gemini.hits += 1; self.rfile.read(int(self.headers["Content-Length"]))
        out = json.dumps({"candidates": [{"content": {"parts": [{"text": "Here's the tea: the council approved a new park [S1]."}]}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)
srv = ThreadingHTTPServer(("127.0.0.1", MOCK), Gemini); threading.Thread(target=srv.serve_forever, daemon=True).start()

import limits, mascot
print("== the Chicago day")
a, b = ts(2026, 10, 3, 23, 59, 59), ts(2026, 10, 4, 0, 0, 1)
check(limits.ct_day(a) == "2026-10-03" and limits.ct_day(b) == "2026-10-04", f"11:59:59 PM and 12:00:01 AM CT are different days ({limits.ct_day(a)}, {limits.ct_day(b)})")
check(limits.secs_to_ct_midnight(ts(2026, 10, 3, 23, 0)) == 3600 and limits.secs_to_ct_midnight(ts(2026, 11, 1, 0, 30)) == 23.5 * 3600 + 3600,
      "seconds to midnight CT (incl. the Nov 1 DST day, 25 h long)")

print("== DailyCounter")
async def counters():
    c = limits.DailyCounter("t")
    n = [await c.incr("x", now=a) for _ in range(3)] + [await c.incr("x", now=b)]
    sent = []
    async def fake(cmds):   # an Upstash stand-in: the same pipeline shapes
        sent.append(cmds); out = []
        for cmd in cmds:
            if cmd[0] == "INCRBY": fake.db[cmd[1]] = fake.db.get(cmd[1], 0) + int(cmd[2]); out.append(fake.db[cmd[1]])
            elif cmd[0] == "GET": out.append(fake.db.get(cmd[1]))
            else: out.append(1)
        return out
    fake.db = {}
    u = limits.DailyCounter("t"); u._send = fake
    m = [await u.incr("d:secret-device-id-123", now=a) for _ in range(2)]
    got = await u.get_many(["d:secret-device-id-123", "nope"], now=a)
    async def boom(cmds): raise RuntimeError("down")
    f = limits.DailyCounter("t"); f._send = boom
    fb = [await f.incr("y") for _ in range(2)]
    return n, m, got, sent, fb
n, m, got, sent, fb = asyncio.run(counters())
check(n == [1, 2, 3, 1], f"memory: counts up, a new Chicago day starts at 1 ({n})")
k = sent[0][0][1]
check(m == [1, 2] and got == {"d:secret-device-id-123": 2, "nope": 0} and sent[0][0][0] == "INCRBY" and sent[0][1][0] == "EXPIRE", f"Upstash: INCRBY + EXPIRE in one pipeline, GET for /stats ({m}, {got})")
check("secret-device-id" not in k and k.startswith("chisme:day:t:2026-10-03:") and int(sent[0][1][2]) == limits.secs_to_ct_midnight(a) + 3600,
      f"keys are hashed (no raw device id) and expire an hour after midnight CT ({k}, ttl {sent[0][1][2]})")
check(fb == [1, 2], "Upstash down → counts in memory instead (never fails open)")

print("== the endpoint (in-process, mock Gemini)")
import app as A
from fastapi.testclient import TestClient
async def no_kb(body): return {}
A.tia_knowledge = no_kb   # no network: the phone's context is enough here
CTX = {"stories": [{"title": "City council approves a new park on the East Side", "source": "KSAT 12", "url": "https://k.example/1", "summary": "A new park."}]}
c = TestClient(A.app)
def say(text, device="dev-aaaaaaaaaaaaaaaa", ip="203.0.113.10"):
    body = {"messages": [{"role": "user", "text": text}], "context": CTX, "hour": 10}
    if device: body["device"] = device
    r = c.post("/api/mascot/chat", json=body, headers={"X-Forwarded-For": ip})
    return r.status_code, r.json()
h0 = Gemini.hits
res = [say("What's the chisme?") for _ in range(20)]
check(all(s == 200 and j["mode"] == "ai" for s, j in res) and Gemini.hits == h0 + 20, f"20 AI answers for one phone ({Gemini.hits - h0} Gemini calls)")
s, j = say("What's the chisme?")
check(s == 200 and j["mode"] == "capped" and j.get("cap") == "device" and j["reply"].startswith("Tía needs her cafecito — come back tomorrow, metiche ☕") and Gemini.hits == h0 + 20,
      f"the 21st: no Gemini call, '{j['reply'][:60]}'")
check(j["cites"] and "\n" in j["reply"], f"…and she still answers from the feeds ({j['reply'].splitlines()[-1][:60]!r}, {j['cites']})")
s, j = say("I want to kill myself")
check(j["mode"] == "safety" and "988" in j["reply"] and Gemini.hits == h0 + 20, "past the cap, the crisis reply (988) still works, no Gemini call")
s, j = say("What's the chisme?", device="dev-bbbbbbbbbbbbbbbb")
check(j["mode"] == "ai", "another phone (its own device id) still gets the AI")
s, j = say("What's the chisme?", device=None, ip="198.51.100.7")
check(j["mode"] == "ai" and A.tia_who(type("R", (), {"headers": {"x-forwarded-for": "198.51.100.7"}, "client": None})(), {}) == "ip:198.51.100.7", "no device id → the IP is the key")
s, j = say("What's the chisme?", device="bad id!")
check(j["mode"] == "ai", "a malformed device id falls back to the IP")
# global cap: 30 in total; 20 + 3 used so far
res = [say("What's the chisme?", device=f"dev-global-{i:06d}xx") for i in range(7)]
check(all(j["mode"] == "ai" for _, j in res), "…up to the global cap (30 today)")
h1 = Gemini.hits
s, j = say("What's the chisme?", device="dev-cccccccccccccccc")
check(j["mode"] == "capped" and j.get("cap") == "global" and j["reply"].startswith("Tía's taking a siesta 😴 — too much chisme today! Back tomorrow, metiche.") and Gemini.hits == h1,
      f"global cap reached: no Gemini call, '{j['reply'][:70]}'")
s, j = say("I want to end my life", device="dev-cccccccccccccccc")
check(j["mode"] == "safety" and "988" in j["reply"], "…and the crisis reply still works past the global cap")
# hourly limit: crisis bypasses it too
A.MASCOT_LIMIT.limit = 1
say("hey", device="dev-dddddddddddddddd", ip="192.0.2.50"); s, j = say("hey", device="dev-dddddddddddddddd", ip="192.0.2.50")
s2, j2 = say("I want to kill myself", device="dev-dddddddddddddddd", ip="192.0.2.50")
check(s == 429 and s2 == 200 and j2["mode"] == "safety" and "988" in j2["reply"], f"the hourly limit (429) never blocks the crisis reply ({s}, {s2})")
A.MASCOT_LIMIT.limit = 1000
# no AI key: replies aren't counted or capped
os.environ.pop("GEMINI_API_KEY"); before = dict(A.TIA_DAY.mem)
s, j = say("What's the chisme?", device="dev-aaaaaaaaaaaaaaaa")
check(j["mode"] == "scripted" and "cafecito" not in j["reply"] and A.TIA_DAY.mem == before, "without the AI (scripted answers) nothing is counted and no cap applies")
os.environ["GEMINI_API_KEY"] = "AQ.test-key-not-real"
print("== /stats")
u = asyncio.run(A.tia_usage())
check(u["ai"] == 30 and u["devices"] == 11 and u["capped-devices"] == 1 and u["blocked-device"] == 1 and u["blocked-global"] == 2 and u["device_cap"] == 20 and u["global_cap"] == 30,
      f"today's usage ({u})")
c.post("/stats/login", data={"key": "unit-test-admin-token", "remember": "1"}, follow_redirects=False)
r = c.get("/stats")
t = r.text
check(r.status_code == 200 and "💬 Tía today" in t and 'id="tia-ai">30<' in t and "of 30" in t and 'id="tia-capped">1<' in t and "TIA_DAILY_GLOBAL_CAP" in t and "cap reached" in t,
      "/stats (signed in) shows Tía today: AI answers / cap, phones at their limit, the env names")
r = TestClient(A.app).get("/stats", follow_redirects=False)
check("Tía today" not in r.text, "…and not before signing in")
# a new Chicago day
tomorrow = time.time() + 86400
orig = limits.ct_day
A.ct_day = limits.ct_day = lambda now=None: orig(tomorrow if now is None else now)
s, j = say("What's the chisme?", device="dev-aaaaaaaaaaaaaaaa")
check(j["mode"] == "ai", "the next Chicago day: the same phone gets the AI again")
A.ct_day = limits.ct_day = orig

print("== the phone + defaults")
js = open(os.path.join(HERE, "static/app.js"), encoding="utf-8").read(); src = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
check('lsGet("chisme-tia-device")' in js and "device: tiaDevice()" in js and "crypto.getRandomValues" in js, "the phone keeps a random device id (localStorage chisme-tia-device) and sends it with each chat")
check("function tiaDaily()" in js and "no AI call needed" in js, "the daily top-chisme opener is built on the phone (no AI call, so no cap)")
os.environ["TIA_X"] = "lots"; os.environ["TIA_Y"] = '"250"'
check('_env_int("TIA_DAILY_GLOBAL_CAP", "1500")' in src and '_env_int("TIA_DEVICE_DAILY_CAP", "20")' in src and A._env_int("TIA_X", "1500") == 1500 and A._env_int("TIA_Y", "1") == 250, "defaults: 20 per phone, 1500 overall (TIA_DAILY_GLOBAL_CAP); a junk env value falls back to the default")
check(mascot.CAP_LINES == {"device": "Tía needs her cafecito — come back tomorrow, metiche ☕", "global": "Tía's taking a siesta 😴 — too much chisme today! Back tomorrow, metiche."}, "the exact cap lines")
srv.shutdown()
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
