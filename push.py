"""Web Push for Chisme: "New chisme, grab the tea! ☕" news alerts and NWS weather warnings/watches.

How it runs on a free host that sleeps (Render free) with no disk:
  • Subscriptions live in Upstash Redis (free tier) through its REST API when UPSTASH_REDIS_REST_URL and
    UPSTASH_REDIS_REST_TOKEN are set. Without them they go to a JSON file (PUSH_STORE_FILE, default
    /tmp/chisme-push.json): fine locally, but on Render that file is wiped whenever the server sleeps, so the
    app re-registers its subscription every time it's opened (that heals it, but a phone that isn't opened
    gets nothing until then).
  • Nothing runs on a timer inside the server (it sleeps). A scheduled GitHub Actions workflow calls
    POST /api/push/tick every ~10 minutes with the PUSH_TICK_SECRET; that wakes the server, which checks the
    news and NWS alerts for each subscriber's area and sends what's new.
  • Keys: VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY (base64url, raw P-256) and VAPID_SUBJECT (mailto: or https:)
    come from the environment only. Nothing secret is in the repo.

Rules per subscriber: at most 1 news push per PUSH_NEWS_GAP_MIN (default 45) minutes, only stories from the last
3 hours that this phone hasn't been told about; quiet hours 10 PM – 7 AM in the phone's time zone (news and
watches wait; warnings still go out); each NWS alert is sent once; the first check after subscribing only
records what's already out there (no burst of old news). Locations are stored rounded to ~1 km."""
import asyncio, hashlib, hmac, json, os, re, time, urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

TITLE_NEWS = "New chisme, grab the tea! ☕"
QUIET_FROM, QUIET_TO = 22, 7            # local hours
NEWS_MAX_AGE = 3 * 3600                 # only fresh stories become a push
MAX_SEEN, MAX_ALERTS, MAX_SUBS = 400, 120, 20000
WX_RX = re.compile(r"\b(warning|watch)\b", re.I)
KEY = "chisme:push:subs"


def news_gap() -> int:
    try:
        return max(30, min(120, int(os.environ.get("PUSH_NEWS_GAP_MIN", "45")))) * 60
    except ValueError:
        return 45 * 60


def conf() -> dict:
    e = os.environ.get
    return {"public": (e("VAPID_PUBLIC_KEY") or "").strip(), "private": (e("VAPID_PRIVATE_KEY") or "").strip(),
            "subject": (e("VAPID_SUBJECT") or "").strip(), "secret": (e("PUSH_TICK_SECRET") or "").strip(),
            "test": e("PUSH_TEST") == "1"}


def enabled() -> bool:
    c = conf()
    return bool(c["public"] and c["private"] and c["subject"])


# ---------------------------------------------------------------- storage
class FileStore:
    name = "file"

    def __init__(self, path: str):
        self.path, self.lock = Path(path), asyncio.Lock()

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return {}

    def _write(self, d: dict):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(d))
        tmp.replace(self.path)

    async def all(self) -> dict:
        async with self.lock:
            return self._read()

    async def get(self, sid: str):
        return (await self.all()).get(sid)

    async def put(self, rec: dict):
        async with self.lock:
            d = self._read(); d[rec["id"]] = rec; self._write(d)

    async def delete(self, sid: str):
        async with self.lock:
            d = self._read(); d.pop(sid, None); self._write(d)

    async def count(self) -> int:
        return len(await self.all())


class UpstashStore:
    """Upstash Redis over its REST API (one hash: id → JSON). Free tier, no driver needed."""
    name = "upstash"

    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    async def _cmd(self, *args):
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self.url, json=[str(a) for a in args], headers={"Authorization": f"Bearer {self.token}"})
            r.raise_for_status()
            return r.json().get("result")

    async def all(self) -> dict:
        flat = await self._cmd("HGETALL", KEY) or []
        out = {}
        for k, v in zip(flat[::2], flat[1::2]):
            try:
                out[k] = json.loads(v)
            except Exception:
                pass
        return out

    async def get(self, sid: str):
        v = await self._cmd("HGET", KEY, sid)
        return json.loads(v) if v else None

    async def put(self, rec: dict):
        await self._cmd("HSET", KEY, rec["id"], json.dumps(rec, separators=(",", ":")))

    async def delete(self, sid: str):
        await self._cmd("HDEL", KEY, sid)

    async def count(self) -> int:
        return int(await self._cmd("HLEN", KEY) or 0)


_store = None


def store():
    global _store
    url, tok = os.environ.get("UPSTASH_REDIS_REST_URL"), os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    want = ("upstash", url, tok) if url and tok else ("file", os.environ.get("PUSH_STORE_FILE") or "/tmp/chisme-push.json")
    if _store is None or getattr(_store, "_want", None) != want:
        _store = UpstashStore(url, tok) if want[0] == "upstash" else FileStore(want[1])
        _store._want = want
    return _store


# ---------------------------------------------------------------- subscriptions
sid_of = lambda endpoint: hashlib.sha256(endpoint.encode()).hexdigest()[:32]
story_id = lambda link: hashlib.sha1((link or "").encode()).hexdigest()[:14]


def clean_sub(s) -> dict | None:
    """A browser PushSubscription.toJSON(), checked: https endpoint, the two keys, sane sizes."""
    if not isinstance(s, dict):
        return None
    ep, keys = s.get("endpoint"), s.get("keys") or {}
    local_ok = conf()["test"] and isinstance(ep, str) and ep.startswith("http://localhost")
    if not isinstance(ep, str) or len(ep) > 1200 or not (ep.startswith("https://") or local_ok):
        return None
    p, a = keys.get("p256dh"), keys.get("auth")
    if not (isinstance(p, str) and isinstance(a, str) and 40 <= len(p) <= 200 and 10 <= len(a) <= 64):
        return None
    return {"endpoint": ep, "keys": {"p256dh": p, "auth": a}}


def clean_tz(tz) -> str:
    try:
        ZoneInfo(str(tz)); return str(tz)
    except Exception:
        return "America/Chicago"


async def subscribe(body: dict) -> dict:
    sub = clean_sub(body.get("subscription"))
    if not sub:
        return {"ok": False, "error": "bad subscription"}
    try:
        lat, lon = round(float(body.get("lat")), 2), round(float(body.get("lon")), 2)
        assert -90 <= lat <= 90 and -180 <= lon <= 180
    except Exception:
        return {"ok": False, "error": "bad location"}
    st, sid = store(), sid_of(sub["endpoint"])
    rec = await st.get(sid)
    if not rec:
        if await st.count() >= MAX_SUBS:
            return {"ok": False, "error": "full"}
        rec = {"id": sid, "created": time.time(), "seen": [], "alerts": [], "last_news": 0, "primed": 0}
    moved = (rec.get("lat"), rec.get("lon")) != (lat, lon)
    rec.update({"sub": sub, "lat": lat, "lon": lon, "tz": clean_tz(body.get("tz")), "news": bool(body.get("news", True)),
                "weather": bool(body.get("weather", True)), "updated": time.time()})
    if moved and rec.get("primed"):
        rec["primed"] = 0   # new area: record what's already out there first, don't push its backlog
    await st.put(rec)
    return {"ok": True, "id": sid, "store": st.name}


async def unsubscribe(body: dict) -> dict:
    ep = (body.get("endpoint") or (body.get("subscription") or {}).get("endpoint") or "")
    if ep:
        await store().delete(sid_of(ep))
    return {"ok": True}


# ---------------------------------------------------------------- sending
def _send_sync(rec: dict, payload: dict, urgent: bool) -> str:
    from pywebpush import webpush, WebPushException
    c = conf()
    try:
        webpush(subscription_info=rec["sub"], data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=c["private"], vapid_claims={"sub": c["subject"]},
                ttl=3 * 3600 if not urgent else 6 * 3600, headers={"Urgency": "high" if urgent else "normal"}, timeout=15)
        return "ok"
    except WebPushException as ex:
        code = getattr(ex.response, "status_code", None)
        return "gone" if code in (404, 410) else f"error {code or ''} {str(ex)[:120]}".strip()
    except Exception as ex:
        return f"error {type(ex).__name__}: {str(ex)[:120]}"


async def send(rec: dict, payload: dict, urgent: bool = False) -> str:
    return await asyncio.to_thread(_send_sync, rec, payload, urgent)


def news_payload(s: dict, more: int) -> dict:
    q = urllib.parse.urlencode({"story": s.get("link") or "", "t": (s.get("title") or "")[:220], "s": (s.get("source") or "")[:80],
                                "p": int(s.get("published") or 0)})
    body = (s.get("title") or "").strip()
    if s.get("source"):
        body += f" — {s['source']}"
    if more > 0:
        body += f" (+{more} more)"
    return {"title": TITLE_NEWS, "body": body[:240], "url": f"/?{q}#news", "tag": "chisme-news"}


def wx_payload(a: dict) -> dict:
    event = (a.get("event") or "Weather alert").strip()
    body = (a.get("headline") or a.get("areaDesc") or "").strip()
    return {"title": f"⚠️ {event}", "body": body[:240], "url": "/#alerts", "tag": "wx-" + story_id(a.get("id") or event),
            "urgent": bool(re.search(r"warning", event, re.I))}


def quiet(rec: dict, now: float) -> bool:
    h = datetime.fromtimestamp(now, ZoneInfo(clean_tz(rec.get("tz")))).hour
    return h >= QUIET_FROM or h < QUIET_TO


async def for_one(rec: dict, stories: list | None, alerts: list | None, now: float, tally: dict) -> str | None:
    """Decide and send this subscriber's pushes. Returns "gone" if the subscription is dead."""
    if not rec.get("primed"):   # first look: remember what's already out there, send nothing
        rec["seen"] = [story_id(s.get("link")) for s in (stories or [])][:MAX_SEEN]
        rec["alerts"] = [a.get("id") for a in (alerts or []) if a.get("id")][:MAX_ALERTS]
        rec["primed"] = now; tally["primed"] += 1
        return None
    hush = quiet(rec, now)
    if rec.get("weather") and alerts:
        sent = 0
        for a in sorted(alerts, key=lambda a: 0 if re.search(r"warning", a.get("event") or "", re.I) else 1):
            aid = a.get("id")
            if not aid or aid in rec["alerts"] or not WX_RX.search(a.get("event") or "") or sent >= 2:
                continue
            p = wx_payload(a)
            if hush and not p["urgent"]:
                tally["quiet"] += 1; continue   # a watch at 2 AM waits for the morning (if it's still active)
            r = await send(rec, p, urgent=p["urgent"])
            if r == "gone":
                return "gone"
            if r == "ok":
                rec["alerts"] = (rec["alerts"] + [aid])[-MAX_ALERTS:]; sent += 1; tally["weather"] += 1
            else:
                tally["errors"].append(r)
    if rec.get("news") and stories:
        seen = set(rec.get("seen") or [])
        new = [s for s in stories if story_id(s.get("link")) not in seen and now - (s.get("published") or 0) <= NEWS_MAX_AGE]
        if new:
            if hush:
                tally["quiet"] += 1
            elif now - (rec.get("last_news") or 0) < news_gap():
                tally["rate_limited"] += 1
            else:
                r = await send(rec, news_payload(new[0], len(new) - 1))
                if r == "gone":
                    return "gone"
                if r == "ok":
                    ids = [story_id(s.get("link")) for s in stories]
                    rec["seen"] = (ids + [i for i in rec.get("seen") or [] if i not in set(ids)])[:MAX_SEEN]
                    rec["last_news"] = now; tally["news"] += 1
                else:
                    tally["errors"].append(r)
    return None


_tick_lock = asyncio.Lock()


async def tick(get_stories, get_alerts, now: float | None = None, fake: dict | None = None) -> dict:
    """One pass over every subscriber (called by the scheduled GitHub Action). Grouped by ~1 km area so each
    area's news and alerts are fetched once."""
    if _tick_lock.locked():
        return {"ok": True, "skipped": "a tick is already running"}
    async with _tick_lock:
        t0, now = time.time(), now or time.time()
        st = store(); recs = await st.all()
        tally = {"subs": len(recs), "areas": 0, "news": 0, "weather": 0, "primed": 0, "quiet": 0, "rate_limited": 0, "removed": 0, "errors": []}
        groups: dict = {}
        for r in recs.values():
            groups.setdefault((r.get("lat"), r.get("lon")), []).append(r)
        for (lat, lon), rs in groups.items():
            tally["areas"] += 1
            stories = alerts = None
            try:
                if any(r.get("news") for r in rs):
                    stories = fake["news"] if fake and "news" in fake else await get_stories(lat, lon)
                if any(r.get("weather") for r in rs):
                    alerts = fake["alerts"] if fake and "alerts" in fake else await get_alerts(lat, lon)
            except Exception as ex:
                tally["errors"].append(f"area {lat},{lon}: {type(ex).__name__}: {str(ex)[:100]}")
            for r in rs:
                r.setdefault("seen", []); r.setdefault("alerts", [])
                before = json.dumps(r, sort_keys=True)
                if await for_one(r, stories, alerts, now, tally) == "gone":
                    await st.delete(r["id"]); tally["removed"] += 1
                elif json.dumps(r, sort_keys=True) != before:
                    await st.put(r)
        tally["errors"] = tally["errors"][:10]
        tally["store"], tally["ms"] = st.name, int((time.time() - t0) * 1000)
        return {"ok": True, **tally}


def authorized(header: str | None) -> bool:
    secret = conf()["secret"]
    got = (header or "").removeprefix("Bearer ").strip()
    return bool(secret) and hmac.compare_digest(got.encode(), secret.encode())


async def renew(body: dict) -> dict:
    """pushsubscriptionchange from the service worker: move the old record's settings to the new endpoint."""
    sub = clean_sub(body.get("subscription"))
    if not sub:
        return {"ok": False, "error": "bad subscription"}
    st, old = store(), body.get("old")
    rec = await st.get(sid_of(old)) if isinstance(old, str) and old else None
    if not rec:
        return {"ok": False, "error": "unknown"}   # the page re-registers with its location next time it opens
    await st.delete(rec["id"])
    rec.update({"id": sid_of(sub["endpoint"]), "sub": sub, "updated": time.time()})
    await st.put(rec)
    return {"ok": True}


async def send_test(body: dict) -> dict:
    """"Send a test" in Settings: one sample notification to this phone (at most one a minute)."""
    ep = body.get("endpoint") or ""
    st = store(); rec = await st.get(sid_of(ep)) if ep else None
    if not rec:
        return {"ok": False, "error": "not subscribed"}
    if time.time() - (rec.get("last_test") or 0) < 60:
        return {"ok": False, "error": "wait a minute"}
    rec["last_test"] = time.time()
    r = await send(rec, {"title": "Chisme alerts are on 🔔", "body": "This is how a heads-up looks. New chisme and weather warnings for your area will land here.",
                         "url": "/#news", "tag": "chisme-test"})
    if r == "gone":
        await st.delete(rec["id"]); return {"ok": False, "error": "subscription expired"}
    await st.put(rec)
    return {"ok": r == "ok", "result": r}
