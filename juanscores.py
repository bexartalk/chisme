"""v49.5: The Juan That Got Away high scores (server side) + the owner's manager.

Public:  GET  /api/juan/scores           → the top 10 {id, name, score, level, t}
         POST /api/juan/scores {name, score, level} → saves one (name: trimmed, at most 12 characters, nothing else
                                                      filtered, per the owner; empty → "Juan")
Owner (the same sign-in as /stats: the /stats cookie, or Authorization: Bearer ADMIN_TOKEN):
         GET    /stats/juan/scores                     → every score
         DELETE /api/juan/scores/{id}                  → delete one     (also /stats/juan/scores/{id}, which gets the cookie)
         PATCH  /api/juan/scores/{id} {name}           → rename one     (same)
         POST   /api/juan/scores/clear {confirm:"CLEAR"} → clear the board (also /stats/juan/scores/clear)
Storage: one Upstash hash (chisme:juan:scores, id → JSON) when Upstash is set up, else a JSON file
(JUAN_SCORES_FILE, default /tmp/chisme-juan-scores.json; temporary on Render's free plan, like the stats)."""
from __future__ import annotations

import json
import os
import secrets
import time

import stats

KEY = "chisme:juan:scores"
NAME_MAX = 12
SCORE_MAX = 10_000_000
KEEP = 500          # the board keeps the best 500; lower ones are dropped
TOP = 10


def clean_name(v) -> str:
    """Trim + at most 12 characters. No word filter (the owner moderates from /stats)."""
    s = " ".join(str(v or "").split())
    return s[:NAME_MAX].strip()


def clean_entry(body: dict) -> dict | None:
    try:
        score = int(body.get("score"))
        level = int(body.get("level") or 1)
    except (TypeError, ValueError):
        return None
    if not (0 < score <= SCORE_MAX) or not (1 <= level <= 6):
        return None
    return {"name": clean_name(body.get("name")) or "Juan", "score": score, "level": level, "t": int(time.time())}


def _sorted(d: dict) -> list[dict]:
    rows = [{"id": k, **v} for k, v in d.items() if isinstance(v, dict)]
    return sorted(rows, key=lambda r: (-int(r.get("score") or 0), int(r.get("t") or 0)))


class _File:
    name = "file"

    def __init__(self, path: str):
        self.path = path

    def _load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _save(self, d: dict):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    async def all(self) -> dict:
        return self._load()

    async def put(self, id_: str, row: dict):
        d = self._load(); d[id_] = row; self._save(d)

    async def delete(self, ids: list[str]) -> int:
        d = self._load(); n = sum(1 for i in ids if d.pop(i, None) is not None); self._save(d); return n

    async def clear(self) -> int:
        d = self._load(); self._save({}); return len(d)


class _Upstash:
    name = "upstash"

    def __init__(self, st):
        self.st = st

    async def all(self) -> dict:
        res = (await self.st.pipe([["HGETALL", KEY]]))[0] or []
        out = {}
        for i in range(0, len(res) - 1, 2):
            try:
                out[res[i]] = json.loads(res[i + 1])
            except Exception:
                pass
        return out

    async def put(self, id_: str, row: dict):
        await self.st.pipe([["HSET", KEY, id_, json.dumps(row, ensure_ascii=False, separators=(",", ":"))]])

    async def delete(self, ids: list[str]) -> int:
        return int((await self.st.pipe([["HDEL", KEY, *ids]]))[0] or 0) if ids else 0

    async def clear(self) -> int:
        n = int((await self.st.pipe([["HLEN", KEY]]))[0] or 0)
        await self.st.pipe([["DEL", KEY]])
        return n


def store():
    st = stats.store()
    if getattr(st, "name", "") == "upstash":
        return _Upstash(st)
    return _File(os.environ.get("JUAN_SCORES_FILE", "/tmp/chisme-juan-scores.json"))


async def board(n: int = TOP) -> list[dict]:
    return [{k: r.get(k) for k in ("id", "name", "score", "level", "t")} for r in _sorted(await store().all())[:n]]


async def everything() -> list[dict]:
    return _sorted(await store().all())


async def add(body: dict) -> dict:
    e = clean_entry(body)
    if not e:
        return {"ok": False, "error": "bad score"}
    s = store(); id_ = secrets.token_hex(6)
    await s.put(id_, e)
    rows = _sorted(await s.all())
    if len(rows) > KEEP:
        await s.delete([r["id"] for r in rows[KEEP:]])
    rank = next((i + 1 for i, r in enumerate(rows) if r["id"] == id_), None)
    return {"ok": True, "id": id_, "rank": rank, "entry": e}


async def remove(id_: str) -> bool:
    return bool(await store().delete([id_]))


async def rename(id_: str, name) -> dict | None:
    s = store(); d = await s.all()
    if id_ not in d:
        return None
    row = {**d[id_], "name": clean_name(name) or "Juan"}
    await s.put(id_, row)
    return {"id": id_, **row}


async def clear() -> int:
    return await store().clear()
