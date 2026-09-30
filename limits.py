"""Tiny in-memory per-IP rate limiter (one process on Render's free plan, so memory is enough)."""
import os
import time
from collections import deque

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
