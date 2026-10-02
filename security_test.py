"""v49.11 security fixes (no browser; FastAPI's TestClient + a tiny fake Upstash):
  • headers: CSP with a fresh nonce on every HTML page (the page's own inline scripts carry it, nothing else), nosniff,
    Referrer-Policy, Permissions-Policy, X-Frame-Options / frame-ancestors, HSTS over https
  • _err / feed status lines never echo exception text (URLs, keys) to the phone
  • reader: a name that resolves to a private address is refused, and the connection goes to the address that was
    checked (no second lookup: no DNS rebinding)
  • rate limits in Upstash (SharedLimit): counted across "restarts", per IP, fall back to memory when storage is down;
    Tía 32 KB cap; push sign-ups per IP + only real push services; high scores: the real client IP, per-minute + per-day,
    a double post isn't a second row, names lose invisible/bidi characters
  • innerHTML lint: in app.js / juan.js / juegos.js every ${…} that goes into innerHTML is escaped, a number, or our own text
  • /api/refresh: a weak ETag (W/"r…", what Render's proxy sends back) still gets 304
  • the Dockerfile copies every module app.py imports"""
import asyncio, json, os, re, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
for k in [k for k in os.environ if k.startswith(("UPSTASH_", "RENDER", "PUSH_TEST"))]: os.environ.pop(k)
os.environ.update(ADMIN_TOKEN="sec-test-token-123", PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

# ---- a fake Upstash REST (only what SharedLimit uses: /pipeline SET NX EX, INCR, TTL; and EXPIRE)
DB, DOWN = {}, {"on": False}
class U(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        if DOWN["on"]: self.send_response(500); self.end_headers(); return
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        def run(c):
            now = time.time(); k = c[1]
            if k in DB and DB[k][1] and DB[k][1] < now: DB.pop(k)
            if c[0] == "SET":
                if "NX" in c and k in DB: return None
                DB[k] = [c[2], now + int(c[c.index("EX") + 1]) if "EX" in c else None]; return "OK"
            if c[0] == "INCR": v = int(DB.get(k, ["0", None])[0]) + 1; DB[k] = [str(v), DB.get(k, [0, None])[1]]; return v
            if c[0] == "TTL": return int(DB[k][1] - now) if k in DB and DB[k][1] else -1
            if c[0] == "EXPIRE": DB[k][1] = now + int(c[2]); return 1
        out = [{"result": run(c)} for c in body] if self.path.endswith("/pipeline") else {"result": run(body)}
        b = json.dumps(out).encode(); self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(b)
srv = HTTPServer(("127.0.0.1", 0), U); threading.Thread(target=srv.serve_forever, daemon=True).start()
UP = f"http://127.0.0.1:{srv.server_port}"

from fastapi.testclient import TestClient
import app as A, limits, reader, juanscores, push
c = TestClient(A.app)

print("== security headers + CSP nonce")
r1, r2 = c.get("/"), c.get("/")
h = r1.headers; cs = h.get("content-security-policy", "")
n1 = re.search(r"'nonce-([^']+)'", cs); n2 = re.search(r"'nonce-([^']+)'", r2.headers.get("content-security-policy", ""))
check(n1 and n2 and n1.group(1) != n2.group(1), "a fresh nonce on every load of /")
tags = re.findall(r"<script([^>]*)>", r1.text)
inline = [t for t in tags if "src=" not in t]
check(len(inline) == 2 and all(f'nonce="{n1.group(1)}"' in t for t in inline), f"index.html's 2 inline scripts carry this response's nonce ({len(inline)})")
for d in ("default-src 'self'", "object-src 'none'", "base-uri 'self'", "frame-ancestors 'self'", "connect-src 'self'", "form-action 'self'"):
    check(d in cs, f"CSP: {d}")
check("'unsafe-eval'" not in cs and "'unsafe-inline'" not in cs.split("script-src")[1].split(";")[0], "CSP: no unsafe-eval / unsafe-inline for scripts")
check(h.get("x-content-type-options") == "nosniff" and h.get("referrer-policy") == "strict-origin-when-cross-origin" and "camera=()" in h.get("permissions-policy", "")
      and h.get("x-frame-options") == "SAMEORIGIN", "nosniff, Referrer-Policy, Permissions-Policy, X-Frame-Options")
check("strict-transport-security" not in h and "max-age=31536000" in c.get("/healthz", headers={"x-forwarded-proto": "https"}).headers.get("strict-transport-security", ""),
      "HSTS only over https (Render sends x-forwarded-proto: https)")
sj = c.get("/static/app.js").headers
check("content-security-policy" not in sj and sj.get("x-content-type-options") == "nosniff", "scripts/JSON: nosniff (the CSP is for pages)")
g = c.get("/stats"); gn = re.search(r"'nonce-([^']+)'", g.headers.get("content-security-policy", ""))
check(gn and f'<script nonce="{gn.group(1)}">' in g.text, "the admin sign-in page's script has its nonce")
check(g.headers.get("referrer-policy") == "no-referrer", "/stats keeps its stricter no-referrer")

print("== errors never echo internals")
import httpx
req = httpx.Request("GET", "https://api.example.com/x?api_key=SECRET123")
ex = httpx.HTTPStatusError("Client error '403' for url 'https://api.example.com/x?api_key=SECRET123'", request=req, response=httpx.Response(403, request=req))
j = json.loads(A._err(ex).body); p = A._plain(ex)
check("SECRET" not in json.dumps(j) and "example.com" not in json.dumps(j) and j["error"].startswith("Couldn't load"), f"_err: a plain message ({j})")
check(p == "HTTPStatusError 403" and "SECRET" not in p, f"feed status line: kind + status only ({p})")
src = open(os.path.join(HERE, "app.py")).read()
check(not re.search(r'"error": f"\{type\(ex\)\.__name__\}: \{ex\}"', src), "no feed status line in app.py puts {ex} on the phone anymore")

print("== reader: public addresses only, pinned")
async def rd():
    out = {}
    for u in ("http://localtest.me/", "http://127.0.0.1/", "http://[::1]/", "http://169.254.169.254/latest/", "http://10.0.0.1/"):
        try: await reader.inspect(reader.safe_client(), u); out[u] = "fetched"
        except reader.Blocked as e: out[u] = str(e)
        except Exception as e: out[u] = type(e).__name__
    calls, got = [], []
    real, real_connect = reader._public, reader.httpcore.AnyIOBackend.connect_tcp
    async def fake_public(host):   # the check says public; a second lookup would say loopback
        calls.append(host); return "93.184.215.14" if len(calls) == 1 else "127.0.0.1"
    async def spy(self, host, port, **kw):
        got.append(host); raise OSError("stop here")
    reader._public = fake_public; reader.httpcore.AnyIOBackend.connect_tcp = spy
    try:
        try: await reader.safe_client().get("http://rebind.example/")
        except Exception: pass
    finally:
        reader._public = real; reader.httpcore.AnyIOBackend.connect_tcp = real_connect
    return out, calls, got
out, calls, got = asyncio.run(rd())
check(all(v != "fetched" for v in out.values()), f"private/loopback/metadata addresses refused: {out}")
check(got == ["93.184.215.14"] and len(calls) == 1, f"the socket opens to the checked address, one lookup per connection ({got}, lookups {len(calls)})")

print("== rate limits in Upstash")
os.environ["UPSTASH_REDIS_REST_URL"], os.environ["UPSTASH_REDIS_REST_TOKEN"] = UP, "fake-token"
async def lim():
    L1 = limits.SharedLimit("t", 3, 60)
    a = [await L1.hit("1.2.3.4") for _ in range(4)]
    L2 = limits.SharedLimit("t", 3, 60)   # "after a redeploy": a fresh limiter, same Upstash
    b = await L2.hit("1.2.3.4"); other = await L2.hit("5.6.7.8")
    DOWN["on"] = True; L3 = limits.SharedLimit("t2", 2, 60); d = [await L3.hit("9.9.9.9") for _ in range(3)]; DOWN["on"] = False
    return a, b, other, d
a, b, other, d = asyncio.run(lim())
check([x[0] for x in a] == [True, True, True, False] and a[3][1] > 0, f"3 allowed, the 4th waits ({a[3]})")
check(not b[0] and other[0], "a new process (a redeploy) still remembers the count; another IP is separate")
check(not any("1.2.3.4" in k for k in DB) and all(k.startswith("chisme:rl:") for k in DB), "keys are hashed (no raw IPs in Upstash)")
check([x[0] for x in d] == [True, True, False], "Upstash down: falls back to the in-memory count (still limited, never wide open)")
check(all(isinstance(x, limits.SharedLimit) for x in (A.MASCOT_LIMIT, A.LOGIN_LIMIT, A.SUB_LIMIT, A.HS_LIMIT, A.HS_DAY)), "Tía, admin sign-in, push sign-ups and high scores use it")
for k in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"): os.environ.pop(k)
r = c.post("/api/mascot/chat", content=b'{"messages":[{"role":"user","text":"' + b"x" * 33000 + b'"}]}', headers={"content-type": "application/json"})
check(r.status_code == 413 and A.TIA_MAX_BODY == 32000, f"Tía: more than 32 KB → 413 ({r.status_code})")

print("== push sign-ups")
ok = lambda ep: bool(push.clean_sub({"endpoint": ep, "keys": {"p256dh": "B" * 87, "auth": "a" * 22}}))
check(all(ok(e) for e in ("https://fcm.googleapis.com/fcm/send/x", "https://web.push.apple.com/Qx", "https://updates.push.services.mozilla.com/wpush/v2/x", "https://wns2-bl2p.notify.windows.com/w/?token=x")),
      "Google, Apple, Mozilla, Microsoft push services accepted")
check(not any(ok(e) for e in ("https://evil.example/x", "https://fcm.googleapis.com.evil.example/x", "https://127.0.0.1/x", "https://169.254.169.254/x")),
      "any other address refused (the server POSTs to it, so never anywhere else)")
A.SUB_LIMIT.limit = 2; A.SUB_LIMIT.hits.clear()
real_enabled = push.enabled; push.enabled = lambda: True
codes = [c.post("/api/push/subscribe", json={}, headers={"x-forwarded-for": "7.7.7.7"}).status_code for _ in range(3)]
push.enabled = real_enabled
check(codes == [400, 400, 429], f"per-IP sign-up cap: the 3rd from one IP in a day → 429 ({codes})")

print("== high scores")
os.environ["RENDER"] = "1"; A.HS_LIMIT.hits.clear(); A.HS_DAY.hits.clear(); A._juan_posts.clear()
post = lambda ip, body: c.post("/api/juan/scores", json=body, headers={"cf-connecting-ip": ip, "x-forwarded-for": "1.1.1.1, 10.0.0.9"})
e = {"name": "Ju\u202ean\u200b", "score": 500, "level": 1}
q1 = post("8.8.8.8", e); q2 = post("8.8.8.8", e)
check(q1.json().get("ok") and q1.json()["entry"]["name"] == "Juan", f"name cleaned of bidi/zero-width characters ({q1.json().get('entry')})")
check(q2.json().get("id") == q1.json().get("id"), "the same score posted twice (a double tap / retry) is one row")
codes = [post("8.8.8.8", {"name": "x", "score": 10 * (i + 1), "level": 1}).status_code for i in range(6)]
check(429 in codes and post("9.9.9.9", {"name": "y", "score": 15, "level": 1}).status_code == 200,
      f"6 a minute per real client IP (CF-Connecting-IP, not the last X-Forwarded-For hop everyone shares): {codes}")
check(post("4.4.4.4", {"name": "z", "score": 999999, "level": 1}).status_code == 400 and post("4.4.4.4", {"name": "z", "score": 501, "level": 1}).status_code == 400,
      "impossible scores still refused (over the level's max, not a multiple of 5)")
os.environ.pop("RENDER")

print("== innerHTML lint")
SAFE = re.compile(r"^(esc|escH|num|fmt|cardHTML|listHTML|howList|skinBtn|skinHint)\(|^\+[\w.]+ \|\| 0$|"
                  r"^(BEAN_DEFS|OVER|VW|cont|line|name|id|L\(\)\.done|LEVELS\[level\]\.name|oopsMsg|level \+ 1)$|"
                  r"^[^`]*\?\s*(\"[^\"]*\"|'[^']*'|`[^`]*`)\s*:\s*(\"[^\"]*\"|'[^']*'|`[^`]*`)\s*$|^(id === cur|lock)")
bad = []
for f in ("static/app.js", "static/juan.js", "static/juegos.js"):
    s = open(os.path.join(HERE, f)).read()
    for m in re.finditer(r"(innerHTML\s*=|overlay\()\s*`", s):
        i, depth, j = m.end(), 0, m.end()
        while j < len(s):
            ch = s[j]
            if ch == "\\": j += 2; continue
            if s.startswith("${", j): depth += 1; j += 2; continue
            if ch == "}" and depth: depth -= 1
            if ch == "`" and depth == 0: break
            j += 1
        for ex in re.findall(r"\$\{((?:[^{}]|\{[^{}]*\})*)\}", s[i:j]):
            if not SAFE.search(ex.strip()): bad.append(f"{f}:{s[:m.start()].count(chr(10)) + 1} ${{{ex.strip()[:60]}}}")
check(not bad, f"every interpolation into innerHTML is escaped / a number / our own text {bad[:8]}")
js = open(os.path.join(HERE, "static/juan.js")).read()
check("escH(r.name)" in js and "escH(lsGet(HS_NAME" in js, "high score names go in through escH()")

print("== /api/refresh weak ETag, Dockerfile")
et = c.get("/api/refresh").headers["etag"]
check(c.get("/api/refresh", headers={"if-none-match": "W/" + et}).status_code == 304 and c.get("/api/refresh", headers={"if-none-match": et}).status_code == 304,
      f"W/{et} and {et} both → 304")
df = open(os.path.join(HERE, "Dockerfile")).read()
local = {m for m in re.findall(r"^(?:import|from) (\w+)", src, re.M) if os.path.exists(os.path.join(HERE, m + ".py"))}
for m in list(local):
    local |= {x for x in re.findall(r"^(?:import|from) (\w+)", open(os.path.join(HERE, m + ".py")).read(), re.M) if os.path.exists(os.path.join(HERE, x + ".py"))}
check(all(f"{m}.py" in df for m in local | {"app"}), f"the Dockerfile copies every module: {sorted(local | {'app'})}")
print("PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
