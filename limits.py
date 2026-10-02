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
