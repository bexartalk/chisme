"""Per-IP rate limits. RateLimit: in memory (cheap, resets when the free server sleeps or redeploys).
SharedLimit (v49.11): kept in Upstash Redis, so a sleep or a deploy doesn't reset it (Tía, push sign-ups, high scores,
admin sign-in); without Upstash, or if it's down, it falls back to the in-memory count (never fails open)."""
import hashlib
import os
import time
from collections import deque

import httpx

from fastapi import Request


def client_ip(request: Request) -> str:
    """The phone's IP. Render sits behind Cloudflare, which sets CF-Connecting-IP / True-Client-IP (and overwrites any
    the client sends); X-Forwarded-For is only appended to there, so it's trusted only off Render (local runs, tests)."""
    if os.environ.get("RENDER"):
        v = request.headers.get("cf-connecting-ip") or request.headers.get("true-client-ip")
        if v:
            return v.strip()
    else:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


class RateLimit:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = {}

    def check(self, key: str) -> tuple[bool, int]:
        """(allowed, seconds until the next slot frees up). Counts the hit when allowed."""
        now = time.time()
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False, int(self.window - (now - q[0])) + 1
        q.append(now)
        if len(self.hits) > 20000:   # forget idle IPs
            for k in [k for k, v in self.hits.items() if not v or now - v[-1] > self.window][:10000]:
                self.hits.pop(k, None)
        return True, 0


class SharedLimit(RateLimit):
    """A fixed window per key in Upstash: one pipelined request (SET NX EX + INCR + TTL), keys hashed (no raw IPs)."""
    _http: httpx.AsyncClient | None = None

    def __init__(self, name: str, limit: int, window: float):
        super().__init__(limit, window)
        self.name = name

    @classmethod
    def _client(cls) -> httpx.AsyncClient:
        if cls._http is None:
            cls._http = httpx.AsyncClient(timeout=httpx.Timeout(3.0))
        return cls._http

    def _key(self, key: str) -> str:
        salt = os.environ.get("STATS_SALT") or os.environ.get("ADMIN_TOKEN") or "chisme"
        return "chisme:rl:" + self.name + ":" + hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()[:24]

    async def hit(self, key: str) -> tuple[bool, int]:
        """(allowed, seconds to wait). Counts the hit."""
        import stats   # the forgiving Upstash env reader (late import: stats doesn't need limits)
        url, tok = stats.upstash_conf()
        if not (url and tok):
            return self.check(key)
        k, w = self._key(key), max(1, int(self.window))
        try:
            r = await self._client().post(url.rstrip("/") + "/pipeline", headers={"Authorization": f"Bearer {tok}"},
                                          json=[["SET", k, "0", "EX", str(w), "NX"], ["INCR", k], ["TTL", k]])
            r.raise_for_status()
            res = [x.get("result") for x in r.json()]
            n, ttl = int(res[1]), int(res[2])
            if ttl < 0:   # (a key that lost its expiry somehow: never let it stick forever)
                await self._client().post(url.rstrip("/"), headers={"Authorization": f"Bearer {tok}"}, json=["EXPIRE", k, str(w)])
                ttl = w
        except Exception as ex:
            print("rate limit storage:", type(ex).__name__)
            return self.check(key)
        return (True, 0) if n <= self.limit else (False, max(1, ttl))


# ---------------------------------------------------------------- v49.12: per-day counters (Tía's daily limits)
def ct_day(now: float | None = None) -> str:
    """Today's date in Chicago (the app's day: counters reset at midnight Central)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(now or time.time(), ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")


def secs_to_ct_midnight(now: float | None = None) -> int:
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    t = datetime.fromtimestamp(now or time.time(), ZoneInfo("America/Chicago"))
    nxt = (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int(nxt.timestamp() - t.timestamp()))


class DailyCounter:
    """Counts per key per Chicago day: in Upstash (INCRBY + EXPIRE a little after midnight, keys hashed, so no raw
    device ids or IPs), else in memory. If Upstash fails it counts in memory instead (never fails open)."""
    _http: httpx.AsyncClient | None = None

    def __init__(self, name: str):
        self.name = name
        self.mem: dict[tuple[str, str], int] = {}

    def _key(self, day: str, key: str) -> str:
        salt = os.environ.get("STATS_SALT") or os.environ.get("ADMIN_TOKEN") or "chisme"
        return f"chisme:day:{self.name}:{day}:" + hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()[:24]

    def _mem(self, day: str, key: str, by: int) -> int:
        if len(self.mem) > 50000 or any(d != day for d, _ in list(self.mem)[:1]):   # a new day (or too many keys): start over
            self.mem = {k: v for k, v in self.mem.items() if k[0] == day} if len(self.mem) <= 50000 else {}
        n = self.mem.get((day, key), 0) + by
        self.mem[(day, key)] = n
        return n

    async def _send(self, cmds: list) -> list | None:
        import stats
        url, tok = stats.upstash_conf()
        if not (url and tok):
            return None
        if DailyCounter._http is None:
            DailyCounter._http = httpx.AsyncClient(timeout=httpx.Timeout(3.0))
        r = await DailyCounter._http.post(url.rstrip("/") + "/pipeline", headers={"Authorization": f"Bearer {tok}"}, json=cmds)
        r.raise_for_status()
        return [x.get("result") for x in r.json()]

    async def incr(self, key: str, by: int = 1, now: float | None = None) -> int:
        day = ct_day(now)
        k = self._key(day, key)
        try:
            res = await self._send([["INCRBY", k, str(by)], ["EXPIRE", k, str(secs_to_ct_midnight(now) + 3600)]])
            if res is not None:
                return int(res[0])
        except Exception as ex:
            print("daily counter storage:", type(ex).__name__)
        return self._mem(day, key, by)

    async def get_many(self, keys: list[str], now: float | None = None) -> dict[str, int]:
        day = ct_day(now)
        try:
            res = await self._send([["GET", self._key(day, k)] for k in keys])
            if res is not None:
                return {k: int(v or 0) for k, v in zip(keys, res)}
        except Exception as ex:
            print("daily counter storage:", type(ex).__name__)
        return {k: self.mem.get((day, k), 0) for k in keys}
