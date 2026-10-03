"""Chisme's private, anonymous usage counts (v42) and the owner's dashboard at /stats.

What's counted, and how it stays anonymous:
  • The app sends small batches of events with navigator.sendBeacon (POST /api/stats): opens (installed app vs the
    browser), tab views, story opens (the headline + link of the public news story), game plays, food video views,
    Tía chats (a count only, never the text), donate taps, the Add to Home Screen tutorial's outcome, and the city of
    the location setting (city level only, e.g. "San Antonio, TX").
  • Unique visitors: the app makes a random ID on the phone (localStorage "chisme-anon-id", not a cookie, not tied to
    anything). The server never keeps it: it's hashed with a secret salt and added to a Redis HyperLogLog per day
    (which can only be counted, not listed). 7- and 30-day visitors are the union of the days.
  • No names, no IPs (the per-phone rate limit keeps only a salted hash, in memory), no cookies for tracking, no third
    parties, nothing sent when the browser asks for Do Not Track / Global Privacy Control.
Storage: Upstash Redis over its REST API when UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN are set (days kept
40 days). Otherwise a JSON file (STATS_STORE_FILE, default /tmp/chisme-stats.json), which on Render is wiped on every
redeploy or sleep: the dashboard says so in a banner.
Dashboard: /stats, only with ADMIN_TOKEN: sign in with the token on the form (v49.5) or open /stats?key=<token> once; either
sets an HttpOnly cookie holding an HMAC of the token, never the token itself. Without ADMIN_TOKEN, /stats doesn't exist (404).
The page itself is rendered by admin.py."""
from __future__ import annotations

import asyncio, hashlib, hmac, html, json, os, re, secrets, time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

TZ = ZoneInfo("America/Chicago")
P = "chisme:st:"
KEEP_DAYS = 40
MAX_EVENTS, MAX_BODY = 60, 16384
TABS = ("chisme", "news", "sports", "events", "weather", "antojos", "juegos")   # v49.12: + the Chisme tab's All view
TAB_NAMES = {"chisme": "Chisme · All", "news": "Chisme · News", "sports": "Chisme · Sports", "events": "Chisme · Events", "weather": "Weather",
             "antojos": "¿Y la dieta?", "juegos": "Juegos"}
A2HS = ("shown", "shown_auto", "got_it", "later")
A2HS_NAMES = {"shown": "Opened from Settings", "shown_auto": "Shown by itself", "got_it": "“Got it”", "later": "“Maybe later”"}
KINDS = ("all", "app", "web")
ID_RX = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
WORD_RX = re.compile(r"^[a-z][a-z0-9_-]{0,23}$")
CITY_RX = re.compile(r"^[^\x00-\x1f<>{}\[\]\\/@#$%^*=+|~`\"]{2,60}$")


def day_of(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts if ts is not None else time.time(), TZ).strftime("%Y-%m-%d")


def last_days(n: int, today: str | None = None) -> list[str]:
    t = datetime.strptime(today or day_of(), "%Y-%m-%d")
    return [(t - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]


def _salt() -> str:
    s = os.environ.get("STATS_SALT") or ""
    if not s and os.environ.get("ADMIN_TOKEN"):
        s = hashlib.sha256(("chisme-stats-salt:" + os.environ["ADMIN_TOKEN"]).encode()).hexdigest()
    return s or _PROCESS_SALT


_PROCESS_SALT = secrets.token_hex(16)   # no secret configured: uniques are only counted per server run
anon = lambda device_id: hashlib.sha256(f"{_salt()}:{device_id}".encode()).hexdigest()[:16]
story_key = lambda url: hashlib.sha1((url or "").encode()).hexdigest()[:12]


# ---------------------------------------------------------------- turning a batch into counts
def clean_text(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def tally(body: dict) -> dict | None:
    """A batch from the app → {"counts": {...}, "uniq": {kind: hash}, "stories": {key: meta}}, or None if it's junk."""
    if not isinstance(body, dict):
        return None
    did, evs = body.get("d"), body.get("e")
    if not isinstance(did, str) or not ID_RX.match(did) or not isinstance(evs, list):
        return None
    h = anon(did)
    counts: dict[str, int] = {}
    uniq: dict[str, str] = {}
    stories: dict[str, dict] = {}
    add = lambda k, n=1: counts.__setitem__(k, counts.get(k, 0) + n)
    for ev in evs[:MAX_EVENTS]:
        if not isinstance(ev, list) or not ev or not isinstance(ev[0], str):
            continue
        t, v = ev[0], (ev[1] if len(ev) > 1 else None)
        if t == "open" and v in ("app", "web"):
            add("open"); add("open:" + v); uniq["all"] = h; uniq[v] = h
        elif t == "tab" and v in TABS:
            add("tab:" + v)
        elif t == "story" and isinstance(v, dict) and isinstance(v.get("u"), str) and re.match(r"^https?://", v["u"]):
            k = story_key(v["u"]); add("story:" + k)
            stories[k] = {"t": clean_text(v.get("t"), 140) or clean_text(v["u"], 80), "s": clean_text(v.get("s"), 40), "u": v["u"][:400]}
        elif t == "game" and isinstance(v, str) and WORD_RX.match(v):
            add("game"); add("game:" + v)
        elif t == "food" and v in ("yt", "tt"):
            add("food"); add("food:" + v)
        elif t == "tia":
            add("tia")
        elif t == "donate" and isinstance(v, str) and WORD_RX.match(v):
            add("donate"); add("donate:" + v)
        elif t == "a2hs" and v in A2HS:
            add("a2hs:" + v)
        elif t == "city" and isinstance(v, str) and CITY_RX.match(v.strip()):
            add("city:" + clean_text(v, 60))
    if not counts and not uniq:
        return None
    return {"counts": counts, "uniq": uniq, "stories": stories}


# ---------------------------------------------------------------- storage
class FileStore:
    """A JSON file (or memory only, with path ""): fine locally; on Render it's gone after a redeploy or a sleep."""
    name = "file"

    def __init__(self, path: str):
        self.path = Path(path) if path else None
        self.lock = asyncio.Lock()
        self.d = self._load()

    def _load(self) -> dict:
        try:
            d = json.loads(self.path.read_text()) if self.path and self.path.exists() else {}
        except Exception:
            d = {}
        d.setdefault("days", {}); d.setdefault("stories", {}); d.setdefault("meta", {})
        return d

    def _save(self):
        if not self.path:
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, separators=(",", ":")))
        tmp.replace(self.path)

    async def add(self, day: str, t: dict):
        async with self.lock:
            dd = self.d["days"].setdefault(day, {"c": {}, "u": {}})
            for k, n in t["counts"].items():
                dd["c"][k] = dd["c"].get(k, 0) + n
            for kind, h in t["uniq"].items():
                lst = dd["u"].setdefault(kind, [])
                if h not in lst and len(lst) < 100000:
                    lst.append(h)
            self.d["stories"].update(t["stories"])
            keep = set(last_days(KEEP_DAYS, day))
            for old in [k for k in self.d["days"] if k not in keep and k < day]:
                self.d["days"].pop(old, None)
            self._save()

    async def read(self, days: list[str]) -> dict:
        async with self.lock:
            D = self.d["days"]
            per = {d: {"c": dict(D.get(d, {}).get("c", {})), "u": {k: len(D.get(d, {}).get("u", {}).get(k, [])) for k in KINDS}} for d in days}
            def union(kind, ds):
                s = set()
                for d in ds:
                    s.update(D.get(d, {}).get("u", {}).get(kind, []))
                return len(s)
            ranges = {n: {k: union(k, days[-n:]) for k in KINDS} for n in (1, 7, 30)}
            return {"per": per, "ranges": ranges, "stories": dict(self.d["stories"]), "sample": bool(self.d["meta"].get("sample"))}


class UpstashStore:
    """Upstash Redis over its REST API: per day a hash of counts (chisme:st:c:<day>) and HyperLogLogs of anonymous
    visitors (chisme:st:u:<kind>:<day>), plus one hash of story headlines. Every key expires after 40 days."""
    name = "upstash"

    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    async def pipe(self, cmds: list[list]) -> list:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(self.url + "/pipeline", json=[[str(a) for a in cmd] for cmd in cmds],
                             headers={"Authorization": f"Bearer {self.token}"})
            r.raise_for_status()
            return [x.get("result") for x in r.json()]

    async def add(self, day: str, t: dict):
        ttl = KEEP_DAYS * 86400
        ck, cmds = f"{P}c:{day}", []
        for k, n in t["counts"].items():
            cmds.append(["HINCRBY", ck, k, n])
        if t["counts"]:
            cmds.append(["EXPIRE", ck, ttl])
        for kind, h in t["uniq"].items():
            uk = f"{P}u:{kind}:{day}"
            cmds += [["PFADD", uk, h], ["EXPIRE", uk, ttl]]
        for k, meta in t["stories"].items():
            cmds.append(["HSET", P + "stories", k, json.dumps(meta, separators=(",", ":"))])
        if t["stories"]:
            cmds.append(["EXPIRE", P + "stories", ttl])
        if cmds:
            await self.pipe(cmds)

    async def read(self, days: list[str]) -> dict:
        cmds = [["HGETALL", f"{P}c:{d}"] for d in days]
        cmds += [["PFCOUNT", f"{P}u:{k}:{d}"] for d in days for k in KINDS]
        rng = [(n, k) for n in (1, 7, 30) for k in KINDS]
        cmds += [["PFCOUNT", *[f"{P}u:{k}:{d}" for d in days[-n:]]] for n, k in rng]
        cmds.append(["HGETALL", P + "stories"])
        res = await self.pipe(cmds)
        per, i = {}, 0
        for d in days:
            flat = res[i] or []; i += 1
            per[d] = {"c": {a: int(b) for a, b in zip(flat[::2], flat[1::2])}, "u": {}}
        for d in days:
            for k in KINDS:
                per[d]["u"][k] = int(res[i] or 0); i += 1
        ranges = {}
        for n, k in rng:
            ranges.setdefault(n, {})[k] = int(res[i] or 0); i += 1
        flat, stories = res[i] or [], {}
        for a, b in zip(flat[::2], flat[1::2]):
            try:
                stories[a] = json.loads(b)
            except Exception:
                pass
        return {"per": per, "ranges": ranges, "stories": stories, "sample": False}


def _upstash_host(v: str) -> str:
    """Pull an Upstash host out of anything pasted: https://h, h, redis://default:pw@h:6379, rediss://..."""
    m = re.search(r"([a-z0-9-]+(?:\.[a-z0-9-]+)*\.upstash\.io)", v or "", re.I)
    return m.group(1).lower() if m else ""


def upstash_conf() -> tuple[str, str]:
    """(rest_url, token), forgiving: values swapped, quotes, NAME=, redis:// URLs, or a password-in-URL."""
    a, b = _clean_env("UPSTASH_REDIS_REST_URL"), _clean_env("UPSTASH_REDIS_REST_TOKEN")
    if not a and not b:
        return "", ""
    if _upstash_host(b) and not _upstash_host(a):
        a, b = b, a   # pasted into the wrong rows
    host = _upstash_host(a)
    tok = b
    if not tok:   # a redis://default:<password>@host URL also carries a usable token
        m = re.search(r"//[^:/@]*:([^@/]+)@", a)
        tok = m.group(1) if m else ""
    return (f"https://{host}" if host else a), tok


def upstash_diag() -> str:
    """Masked hint for the owner: never prints the token."""
    a, b = _clean_env("UPSTASH_REDIS_REST_URL"), _clean_env("UPSTASH_REDIS_REST_TOKEN")
    url, tok = upstash_conf()
    host = _upstash_host(url)
    bits = [f"URL value: {'missing' if not a else (host if host else 'not an Upstash address (' + str(len(a)) + ' characters)')}",
            f"token: {'missing' if not tok else str(len(tok)) + ' characters'}"]
    if host and host != _upstash_host(a):
        bits.append("(the two values looked swapped; fixed automatically)")
    return " · ".join(bits)


def _clean_env(name: str) -> str:
    """Forgiving read of a pasted env value: strips spaces, quotes, a leading NAME= / export NAME=, and stray ':'."""
    v = (os.environ.get(name) or "").strip()
    v = re.sub(r"^(export\s+)?" + re.escape(name) + r"\s*[=:]\s*", "", v, flags=re.I).strip()
    v = v.strip("\"'`“”‘’ ").strip()
    return "".join(v.split())


_store = None


def store():
    global _store
    url, tok = upstash_conf()
    want = ("upstash", url, tok) if url and tok else ("file", os.environ.get("STATS_STORE_FILE", "/tmp/chisme-stats.json"))
    if _store is None or getattr(_store, "_want", None) != want:
        _store = UpstashStore(url, tok) if want[0] == "upstash" else FileStore(want[1])
        _store._want = want
    return _store


async def collect(raw: bytes) -> bool:
    if not raw or len(raw) > MAX_BODY:
        return False
    try:
        t = tally(json.loads(raw))
    except Exception:
        return False
    if not t:
        return False
    await store().add(day_of(), t)
    return True


# ---------------------------------------------------------------- the dashboard's access
COOKIE = "chisme_stats"


def admin_token() -> str:
    return os.environ.get("ADMIN_TOKEN", "")


def session_value() -> str:
    return hmac.new(admin_token().encode(), b"chisme-stats-session-v1", hashlib.sha256).hexdigest()


def key_ok(key: str | None) -> bool:
    tok = admin_token()
    return bool(tok) and bool(key) and hmac.compare_digest(key.encode(), tok.encode())


def cookie_ok(val: str | None) -> bool:
    """(v49.5 fixed cookie: no longer accepted since v49.11; kept for the tests that check it's refused.)"""
    return False


# ---------------------------------------------------------------- v49.11: revocable admin sessions
# Signing in makes a random session id (the cookie); the store (Upstash via push.store(), so it survives redeploys)
# keeps only its SHA-256, with an expiry (30 days with "keep me signed in", else 12 hours). Each session also carries
# the current "epoch" (Sign out everywhere bumps it, so every session ends at once) and a tag of ADMIN_TOKEN (changing
# the token on Render still signs out every device). A copied cookie can be revoked without touching the token.
SESSION_DAYS = 30
SESSION_SHORT = 12 * 3600
EPOCH_KEY = "chisme:adm:epoch"
_sess_ok: dict[str, float] = {}   # verified session hash → until when (a 60 s memo; cleared on any sign-out)


def _sess_key(sid: str) -> str:
    return "chisme:adm:sess:" + hashlib.sha256(sid.encode()).hexdigest()[:40]


def _tok_tag() -> str:
    return hmac.new(admin_token().encode(), b"chisme-stats-session-v2", hashlib.sha256).hexdigest()[:24]


def _kv():
    import push   # (late: push imports stats)
    return push.store()


async def _epoch() -> int:
    return int(await _kv().kv_get(EPOCH_KEY) or 0)


async def new_session(remember: bool = True) -> tuple[str, int]:
    sid, ttl = secrets.token_urlsafe(32), SESSION_DAYS * 86400 if remember else SESSION_SHORT
    await _kv().kv_set(_sess_key(sid), {"e": await _epoch(), "k": _tok_tag(), "t": int(time.time())}, ex=ttl)
    return sid, ttl


async def session_ok(sid: str | None) -> bool:
    if not admin_token() or not sid or len(sid) > 128:
        return False
    k, now = _sess_key(sid), time.time()
    if _sess_ok.get(k, 0) > now:
        return True
    try:
        rec, ep = await _kv().kv_get(k), await _epoch()
    except Exception as ex:
        print("admin session storage:", type(ex).__name__)
        return False
    ok = isinstance(rec, dict) and hmac.compare_digest(str(rec.get("k") or ""), _tok_tag()) and int(rec.get("e", -1)) == ep
    if ok:
        if len(_sess_ok) > 200:
            _sess_ok.clear()
        _sess_ok[k] = now + 60
    return ok


async def end_session(sid: str | None) -> None:
    if sid and len(sid) <= 128:
        _sess_ok.pop(_sess_key(sid), None)
        try:
            await _kv().kv_set(_sess_key(sid), None, ex=1)
        except Exception:
            pass


async def end_all_sessions() -> int:
    """Sign out everywhere: every session made before now stops working (this one too)."""
    _sess_ok.clear()
    return int(await _kv().kv_incr(EPOCH_KEY))


# ---------------------------------------------------------------- the dashboard
def summarize(r: dict, days: list[str]) -> dict:
    per = r["per"]

    def tot(n: int) -> dict:
        c: dict[str, int] = {}
        for d in days[-n:]:
            for k, v in per[d]["c"].items():
                c[k] = c.get(k, 0) + v
        return c
    return {n: {"c": tot(n), "u": r["ranges"][n]} for n in (1, 7, 30)}


def _top(c: dict, prefix: str, n: int = 8) -> list[tuple[str, int]]:
    return sorted(((k[len(prefix):], v) for k, v in c.items() if k.startswith(prefix)), key=lambda x: (-x[1], x[0]))[:n]


def page(r: dict, store_name: str, now: float | None = None, extra: str = "", info: dict | None = None, info_error: str = "", scores: list | None = None, refresh: dict | None = None, nonce: str = "", tia: dict | None = None) -> str:
    """The dashboard (v49.5: rendered by admin.py, phone-first). `info`: autopush.admin_info() for the push cards; `tia`: v49.12 app.tia_usage()."""
    import admin
    return admin.page(r, store_name, info=info, now=now, info_error=info_error, extra=extra, scores=scores, refresh=refresh, nonce=nonce, tia=tia)


def gate_page(error: str = "", nonce: str = "") -> str:
    """v49.5: a simple sign-in form (admin.login_page) instead of 'open the link with ?key='."""
    import admin
    return admin.login_page(error, nonce=nonce)
