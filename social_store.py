"""Chisme social: storage adapters (kept apart from the rules in social.py so each backend stays small).

* Tables: one tiny interface (select / insert / update / delete / count with simple filters), two backends:
  - SupabaseDB: PostgREST with the server-only secret key (SUPABASE_URL + SUPABASE_SERVICE_KEY, like owner posts).
  - LocalDB: SQLite (SOCIAL_DIR, default /tmp/chisme-social) for tests and local runs. The same filters, the same rows.
  Filters are (column, op, value) with op in eq neq in nin gt gte lt lte isnull notnull prefix contains.
* Media: one interface (put / delete / url), three backends: R2Media (Cloudflare R2, S3 API, SigV4, no SDK),
  SupabaseMedia (Storage bucket "chisme-media"), LocalMedia (a folder served by /api/social/media/...). Plus a
  private quarantine store (never served) for uploads held for a CSAM scan or kept as evidence.
* CSAM hook: CSAM_SCAN_URL (+ CSAM_SCAN_TOKEN). See SOCIAL.md."""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import urllib.parse
from pathlib import Path
from typing import Any

import httpx

TABLES: dict[str, dict] = {   # columns, primary key, json columns, bool columns
    "social_profiles": {"pk": ["id"], "json": ["privacy"], "bool": ["verified", "flagged"],
                        "cols": ["id", "username", "display_name", "bio", "area", "photo", "banner", "accent", "pinned_id", "privacy", "status", "verified", "flagged",
                                 "report_count", "created_at", "updated_at"]},
    "social_private": {"pk": ["user_id"], "cols": ["user_id", "email_hash", "email_hint", "phone", "birthday", "tos_at", "privacy_at",
                                                   "signup_ip", "device", "created_at"], "unique": [["email_hash"]]},
    "social_sessions": {"pk": ["id_hash"], "cols": ["id_hash", "user_id", "created_at", "expires_at", "ua"]},
    "social_homies": {"pk": ["a", "b"], "cols": ["a", "b", "created_at"]},
    "social_homie_requests": {"pk": ["id"], "cols": ["id", "from_id", "to_id", "status", "created_at"], "unique": [["from_id", "to_id"]]},
    "social_nahs": {"pk": ["user_id", "target_id"], "cols": ["user_id", "target_id", "created_at"]},
    "social_blocks": {"pk": ["blocker_id", "blocked_id"], "cols": ["blocker_id", "blocked_id", "created_at"]},
    "social_media": {"pk": ["name"], "cols": ["name", "owner_id", "kind", "status", "w", "h", "bytes", "seconds", "poster", "created_at"]},
    "social_chismes": {"pk": ["id"], "json": ["photos", "videos", "clip", "hashtags", "mentions", "tags"], "bool": ["meme"],
                       "cols": ["id", "author_id", "text", "photos", "videos", "clip", "meme", "audience", "hashtags", "mentions", "tags", "status", "report_count",
                                "created_at", "updated_at"]},
    "social_reactions": {"pk": ["chisme_id", "user_id", "kind"], "cols": ["chisme_id", "user_id", "kind", "created_at"]},
    "social_saves": {"pk": ["user_id", "chisme_id"], "cols": ["user_id", "chisme_id", "created_at"]},
    "social_comments": {"pk": ["id"], "cols": ["id", "chisme_id", "author_id", "text", "status", "report_count", "created_at"]},
    "social_reports": {"pk": ["id"], "cols": ["id", "reporter_id", "target_kind", "target_id", "target_user", "reason", "details", "status",
                                              "created_at"], "unique": [["reporter_id", "target_kind", "target_id"]]},
    "social_notifications": {"pk": ["id"], "bool": ["read"], "cols": ["id", "user_id", "actor_id", "kind", "chisme_id", "read", "created_at"]},
    "social_bans": {"pk": ["email_hash"], "cols": ["email_hash", "reason", "created_at"]},
    "social_dmca": {"pk": ["id"], "cols": ["id", "claimant_name", "claimant_email", "claimant_address", "work", "urls", "statement",
                                           "signature", "status", "created_at"]},
    "social_csam_holds": {"pk": ["id"], "cols": ["id", "media_name", "owner_id", "sha256", "created_at", "reported_at"]},
}
OPS = {"eq", "neq", "in", "nin", "gt", "gte", "lt", "lte", "isnull", "notnull", "prefix", "contains"}
COL_RX = re.compile(r"^[a-z_]{1,30}$")


class Conflict(Exception):
    """A duplicate key (unique / primary key)."""


class StorageError(RuntimeError):
    pass


def now_iso(ts: float | None = None) -> str:
    d = _dt.datetime.now(_dt.timezone.utc) if ts is None else _dt.datetime.fromtimestamp(ts, _dt.timezone.utc)
    return d.isoformat(timespec="microseconds")


def ts_of(v) -> float:
    if not v:
        return 0.0
    try:
        return _dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _check(table: str, filters: list) -> None:
    if table not in TABLES:
        raise StorageError("unknown table")
    for f in filters:
        if len(f) != 3 or not COL_RX.match(f[0]) or f[1] not in OPS:
            raise StorageError("bad filter")


# ---------------------------------------------------------------- SQLite
class LocalDB:
    name = "local"
    durable = False

    def __init__(self, folder: str):
        Path(folder).mkdir(parents=True, exist_ok=True)
        self.path = str(Path(folder) / "social.db")
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.execute("pragma journal_mode=wal")
        for t, meta in TABLES.items():
            cols = ", ".join(f'"{c}"' for c in meta["cols"])
            uniq = "".join(f", unique ({', '.join(u)})" for u in meta.get("unique", []))
            self.conn.execute(f"create table if not exists {t} ({cols}, primary key ({', '.join(meta['pk'])}){uniq})")
        self.conn.execute("create unique index if not exists sp_user on social_profiles (username)")

    @staticmethod
    def _enc(table: str, row: dict) -> dict:
        meta = TABLES[table]
        out = {}
        for k, v in row.items():
            if k not in meta["cols"]:
                continue
            if k in meta.get("json", []):
                v = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                v = int(v)
            out[k] = v
        return out

    @staticmethod
    def _dec(table: str, row: dict) -> dict:
        meta = TABLES[table]
        for k in meta.get("json", []):
            if k in row and isinstance(row[k], str):
                row[k] = json.loads(row[k])
        for k in meta.get("bool", []):
            if k in row and row[k] is not None:
                row[k] = bool(row[k])
        return row

    def _where(self, filters: list) -> tuple[str, list]:
        parts, args = [], []
        for col, op, val in filters:
            c = f'"{col}"'
            if op in ("in", "nin"):
                vals = list(val)
                if not vals:
                    parts.append("0" if op == "in" else "1")
                    continue
                parts.append(f"{c} {'not ' if op == 'nin' else ''}in ({','.join('?' * len(vals))})")
                args += vals
            elif op == "isnull":
                parts.append(f"{c} is null")
            elif op == "notnull":
                parts.append(f"{c} is not null")
            elif op == "prefix":
                parts.append(f"{c} like ? escape '\\'")
                args.append(re.sub(r"([%_\\])", r"\\\1", str(val)) + "%")
            elif op == "contains":   # a JSON array column holds this string
                parts.append(f"{c} like ?")
                args.append("%" + json.dumps(str(val), ensure_ascii=False) + "%")
            else:
                sym = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[op]
                parts.append(f"{c} {sym} ?")
                args.append(int(val) if isinstance(val, bool) else val)
        return (" where " + " and ".join(parts)) if parts else "", args

    async def select(self, table: str, filters: list | None = None, order: list | None = None, limit: int | None = None,
                     cols: list | None = None) -> list[dict]:
        filters = filters or []
        _check(table, filters)
        w, args = self._where(filters)
        sel = ", ".join(f'"{c}"' for c in cols) if cols else "*"
        o = ""
        if order:
            o = " order by " + ", ".join(f'"{c}" {"desc" if d else "asc"}' for c, d in order)
        lim = f" limit {int(limit)}" if limit else ""
        with self.lock:
            cur = self.conn.execute(f"select {sel} from {table}{w}{o}{lim}", args)
            names = [d[0] for d in cur.description]
            return [self._dec(table, dict(zip(names, r))) for r in cur.fetchall()]

    async def count(self, table: str, filters: list | None = None) -> int:
        filters = filters or []
        _check(table, filters)
        w, args = self._where(filters)
        with self.lock:
            return int(self.conn.execute(f"select count(*) from {table}{w}", args).fetchone()[0])

    async def insert(self, table: str, row: dict, ignore_dup: bool = False) -> dict:
        _check(table, [])
        r = self._enc(table, row)
        cols = ", ".join(f'"{c}"' for c in r)
        try:
            with self.lock:
                self.conn.execute(f"insert {'or ignore ' if ignore_dup else ''}into {table} ({cols}) values ({','.join('?' * len(r))})", list(r.values()))
        except sqlite3.IntegrityError:
            raise Conflict(table)
        return dict(row)

    async def update(self, table: str, filters: list, fields: dict) -> int:
        _check(table, filters)
        if not filters:
            raise StorageError("update needs a filter")
        r = self._enc(table, fields)
        w, args = self._where(filters)
        with self.lock:
            try:
                return self.conn.execute(f"update {table} set {', '.join(f'{chr(34)}{k}{chr(34)} = ?' for k in r)}{w}", list(r.values()) + args).rowcount
            except sqlite3.IntegrityError:
                raise Conflict(table)

    async def delete(self, table: str, filters: list) -> int:
        _check(table, filters)
        if not filters:
            raise StorageError("delete needs a filter")
        w, args = self._where(filters)
        with self.lock:
            return self.conn.execute(f"delete from {table}{w}", args).rowcount


# ---------------------------------------------------------------- PostgREST (Supabase)
def _pg_val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _pg_list(vals) -> str:
    return "(" + ",".join('"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"' for v in vals) + ")"


def pg_params(filters: list) -> list[tuple[str, str]]:
    """Our filters → PostgREST query parameters (shared with the test's fake PostgREST, which parses them back)."""
    out = []
    for col, op, val in filters:
        if op == "in":
            out.append((col, "in." + _pg_list(val)))
        elif op == "nin":
            out.append((col, "not.in." + _pg_list(val)))
        elif op == "isnull":
            out.append((col, "is.null"))
        elif op == "notnull":
            out.append((col, "not.is.null"))
        elif op == "prefix":
            out.append((col, "like." + re.sub(r"[*%_\\]", "", str(val)) + "*"))
        elif op == "contains":
            out.append((col, "cs." + json.dumps([str(val)], ensure_ascii=False)))
        else:
            out.append((col, f"{op}.{_pg_val(val)}"))
    return out


class SupabaseDB:
    name = "supabase"
    durable = True

    def __init__(self, url: str, key: str, client: httpx.AsyncClient | None = None):
        self.url, self.key = url, key
        self.http = client or httpx.AsyncClient(timeout=15)

    def _h(self, extra: dict | None = None) -> dict:
        h = {"apikey": self.key}
        if self.key.startswith("eyJ"):
            h["Authorization"] = "Bearer " + self.key
        return {**h, **(extra or {})}

    def _t(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    @staticmethod
    def _ok(r: httpx.Response, table: str) -> httpx.Response:
        if r.status_code == 409:
            raise Conflict(table)
        if r.status_code >= 400:
            raise StorageError(f"Supabase {r.status_code}")   # never the body (it can echo the request)
        return r

    async def select(self, table, filters=None, order=None, limit=None, cols=None):
        filters = filters or []
        _check(table, filters)
        q = [("select", ",".join(cols) if cols else "*")] + pg_params(filters)
        if order:
            q.append(("order", ",".join(f"{c}.{'desc' if d else 'asc'}" for c, d in order)))
        if limit:
            q.append(("limit", str(int(limit))))
        return self._ok(await self.http.get(self._t(table), params=q, headers=self._h()), table).json()

    async def count(self, table, filters=None):
        filters = filters or []
        _check(table, filters)
        q = [("select", TABLES[table]["pk"][0])] + pg_params(filters)
        r = self._ok(await self.http.get(self._t(table), params=q + [("limit", "1")], headers=self._h({"Prefer": "count=exact"})), table)
        m = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
        return int(m.group(1)) if m else len(r.json())

    async def insert(self, table, row, ignore_dup=False):
        _check(table, [])
        body = {k: v for k, v in row.items() if k in TABLES[table]["cols"]}
        pref = "return=minimal" + (",resolution=ignore-duplicates" if ignore_dup else "")
        self._ok(await self.http.post(self._t(table), json=body, headers=self._h({"Prefer": pref})), table)
        return dict(row)

    async def update(self, table, filters, fields):
        _check(table, filters)
        if not filters:
            raise StorageError("update needs a filter")
        body = {k: v for k, v in fields.items() if k in TABLES[table]["cols"]}
        r = self._ok(await self.http.patch(self._t(table), params=pg_params(filters), json=body,
                                           headers=self._h({"Prefer": "return=minimal,count=exact"})), table)
        m = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
        return int(m.group(1)) if m else 1

    async def delete(self, table, filters):
        _check(table, filters)
        if not filters:
            raise StorageError("delete needs a filter")
        r = self._ok(await self.http.delete(self._t(table), params=pg_params(filters), headers=self._h({"Prefer": "return=minimal,count=exact"})), table)
        m = re.search(r"/(\d+)$", r.headers.get("content-range", ""))
        return int(m.group(1)) if m else 1


# ---------------------------------------------------------------- media
NAME_RX = re.compile(r"^(?:[acb]/\d{6}/[A-Za-z0-9_-]{12}\.webp|v/\d{6}/[A-Za-z0-9_-]{12}\.(?:mp4|webp))$")


def ctype(name: str) -> str:
    return "video/mp4" if name.endswith(".mp4") else "image/webp"


class LocalMedia:
    name = "local"

    def __init__(self, folder: str):
        self.dir = Path(folder)
        self.dir.mkdir(parents=True, exist_ok=True)

    async def put(self, name: str, data: bytes) -> None:
        p = self.dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    async def get(self, name: str) -> bytes | None:
        p = self.local_path(name)
        return p.read_bytes() if p else None

    async def delete(self, names: list[str]) -> None:
        for n in names:
            try:
                (self.dir / n).unlink()
            except (FileNotFoundError, OSError):
                pass

    def url(self, name: str) -> str:
        return "/api/social/media/" + name

    def local_path(self, name: str) -> Path | None:
        if not NAME_RX.match(name or ""):
            return None
        p = (self.dir / name).resolve()
        return p if p.is_file() and str(p).startswith(str(self.dir.resolve()) + os.sep) else None


class SupabaseMedia:
    name = "supabase"

    def __init__(self, url: str, key: str, bucket: str, public: bool = True, client: httpx.AsyncClient | None = None):
        self.url, self.key, self.bucket, self.public = url, key, bucket, public
        self.http = client or httpx.AsyncClient(timeout=20)

    def _h(self, extra=None):
        h = {"apikey": self.key}
        if self.key.startswith("eyJ"):
            h["Authorization"] = "Bearer " + self.key
        return {**h, **(extra or {})}

    async def put(self, name, data):
        r = await self.http.post(f"{self.url}/storage/v1/object/{self.bucket}/{name}", content=data,
                                 headers=self._h({"Content-Type": ctype(name), "Cache-Control": "max-age=31536000", "x-upsert": "false"}))
        if r.status_code >= 400:
            raise StorageError(f"Supabase Storage {r.status_code}")

    async def get(self, name):
        r = await self.http.get(f"{self.url}/storage/v1/object/{self.bucket}/{name}", headers=self._h())
        return r.content if r.status_code == 200 else None

    async def delete(self, names):
        if names:
            r = await self.http.request("DELETE", f"{self.url}/storage/v1/object/{self.bucket}", json={"prefixes": names}, headers=self._h())
            if r.status_code >= 400:
                raise StorageError(f"Supabase Storage {r.status_code}")

    def url(self, name):
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"

    def local_path(self, name):
        return None


def _sigv4(method: str, url: str, headers: dict, body: bytes, access: str, secret: str, region: str = "auto", service: str = "s3") -> dict:
    """AWS Signature V4 (what R2's S3 API wants), standard library only."""
    u = urllib.parse.urlsplit(url)
    t = _dt.datetime.now(_dt.timezone.utc)
    amz, day = t.strftime("%Y%m%dT%H%M%SZ"), t.strftime("%Y%m%d")
    ph = hashlib.sha256(body).hexdigest()
    h = {**{k.lower(): v for k, v in headers.items()}, "host": u.netloc, "x-amz-date": amz, "x-amz-content-sha256": ph}
    signed = ";".join(sorted(h))
    canon_q = "&".join(sorted(u.query.split("&"))) if u.query else ""
    creq = "\n".join([method, urllib.parse.quote(u.path or "/", safe="/-_.~"), canon_q,
                      "".join(f"{k}:{str(h[k]).strip()}\n" for k in sorted(h)), signed, ph])
    scope = f"{day}/{region}/{service}/aws4_request"
    sts = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(creq.encode()).hexdigest()])
    k = ("AWS4" + secret).encode()
    for part in (day, region, service, "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    h["authorization"] = f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={signed}, Signature={sig}"
    return h


class R2Media:
    """Cloudflare R2 through its S3 API. The bucket's public address (an r2.dev URL or a custom domain on Cloudflare,
    which is also where Cloudflare's CSAM Scanning Tool can watch) is R2_PUBLIC_BASE_URL."""
    name = "r2"

    def __init__(self, account: str, access: str, secret: str, bucket: str, public_base: str, client: httpx.AsyncClient | None = None):
        self.endpoint = f"https://{account}.r2.cloudflarestorage.com"
        self.access, self.secret, self.bucket, self.public_base = access, secret, bucket, public_base.rstrip("/")
        self.http = client or httpx.AsyncClient(timeout=20)

    def _u(self, name: str) -> str:
        return f"{self.endpoint}/{self.bucket}/{name}"

    async def put(self, name, data):
        url = self._u(name)
        h = _sigv4("PUT", url, {"content-type": ctype(name), "cache-control": "public, max-age=31536000, immutable"}, data, self.access, self.secret)
        r = await self.http.put(url, content=data, headers=h)
        if r.status_code >= 400:
            raise StorageError(f"R2 {r.status_code}")

    async def get(self, name):
        url = self._u(name)
        r = await self.http.get(url, headers=_sigv4("GET", url, {}, b"", self.access, self.secret))
        return r.content if r.status_code == 200 else None

    async def delete(self, names):
        for n in names:
            url = self._u(n)
            r = await self.http.delete(url, headers=_sigv4("DELETE", url, {}, b"", self.access, self.secret))
            if r.status_code >= 400 and r.status_code != 404:
                raise StorageError(f"R2 {r.status_code}")

    def url(self, name):
        return f"{self.public_base}/{name}"

    def local_path(self, name):
        return None


# ---------------------------------------------------------------- picking the backends
def _env(*names: str) -> str:
    for n in names:
        v = (os.environ.get(n) or "").strip().strip("\"'")
        if v:
            return v
    return ""


def supabase_conf() -> tuple[str, str]:
    url = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    if url and not re.match(r"^https://[a-z0-9-]+\.supabase\.(co|in)$|^https?://(localhost|127\.0\.0\.1)(:\d+)?$", url):
        return "", ""
    return url, key


def r2_conf() -> dict | None:
    c = {k: _env("R2_" + k.upper()) for k in ("account_id", "access_key_id", "secret_access_key", "bucket", "public_base_url")}
    return c if all(c.values()) and re.match(r"^https://[^\s/]+", c["public_base_url"]) else None


_cache: dict[str, Any] = {}


def db():
    url, key = supabase_conf()
    want = ("supabase", url, key) if url and key else ("local", _env("SOCIAL_DIR") or "/tmp/chisme-social")
    cur = _cache.get("db")
    if cur is None or cur._want != want:
        cur = SupabaseDB(url, key) if want[0] == "supabase" else LocalDB(want[1])
        cur._want = want
        _cache["db"] = cur
    return cur


def media():
    """SOCIAL_MEDIA_STORE = r2 | supabase | local (default: r2 when its 5 vars are set, else Supabase, else local)."""
    pick = _env("SOCIAL_MEDIA_STORE").lower()
    url, key = supabase_conf()
    r2 = r2_conf()
    if pick not in ("r2", "supabase", "local"):
        pick = "r2" if r2 else "supabase" if (url and key) else "local"
    if pick == "r2" and not r2:
        pick = "supabase" if (url and key) else "local"
    if pick == "supabase" and not (url and key):
        pick = "local"
    want = (pick, url, key, json.dumps(r2, sort_keys=True), _env("SOCIAL_DIR"))
    cur = _cache.get("media")
    if cur is None or cur._want != want:
        if pick == "r2":
            cur = R2Media(r2["account_id"], r2["access_key_id"], r2["secret_access_key"], r2["bucket"], r2["public_base_url"])
        elif pick == "supabase":
            cur = SupabaseMedia(url, key, _env("SOCIAL_MEDIA_BUCKET") or "chisme-media")
        else:
            cur = LocalMedia(str(Path(_env("SOCIAL_DIR") or "/tmp/chisme-social") / "media"))
        cur._want = want
        _cache["media"] = cur
    return cur


def quarantine():
    """Private, never served: Supabase's private bucket "chisme-quarantine" (or R2_QUARANTINE_BUCKET), else a local folder."""
    url, key = supabase_conf()
    r2 = r2_conf()
    qb = _env("R2_QUARANTINE_BUCKET")
    want = ("q", url, key, qb, json.dumps(r2, sort_keys=True), _env("SOCIAL_DIR"))
    cur = _cache.get("q")
    if cur is None or cur._want != want:
        if r2 and qb:
            cur = R2Media(r2["account_id"], r2["access_key_id"], r2["secret_access_key"], qb, "https://invalid.local")
        elif url and key:
            cur = SupabaseMedia(url, key, "chisme-quarantine", public=False)
        else:
            cur = LocalMedia(str(Path(_env("SOCIAL_DIR") or "/tmp/chisme-social") / "quarantine"))
        cur._want = want
        _cache["q"] = cur
    return cur


# ---------------------------------------------------------------- CSAM scanning hook
def csam_conf() -> tuple[str, str]:
    url = _env("CSAM_SCAN_URL")
    return (url, _env("CSAM_SCAN_TOKEN")) if url.startswith("https://") or url.startswith("http://127.0.0.1") or url.startswith("http://localhost") else ("", "")


async def csam_scan(data: bytes, client: httpx.AsyncClient | None = None, kind: str = "image/webp") -> str:
    """'clean' | 'match' | 'error'. POSTs the WebP to CSAM_SCAN_URL (Bearer CSAM_SCAN_TOKEN), expects {"match": bool}.
    The adapter for whichever service Goonie gets (e.g. Microsoft PhotoDNA Cloud, Thorn Safer) answers in that shape.
    Not configured → 'clean' (nothing to wait for; Cloudflare's CSAM Scanning Tool, if on, watches the served files)."""
    url, tok = csam_conf()
    if not url:
        return "clean"
    own = client is None
    c = client or httpx.AsyncClient(timeout=20)
    try:
        r = await c.post(url, content=data, headers={"Content-Type": kind, **({"Authorization": "Bearer " + tok} if tok else {})})
        if r.status_code >= 400:
            return "error"
        m = r.json().get("match")
        return "match" if m is True else "clean" if m is False else "error"
    except Exception:
        return "error"
    finally:
        if own:
            await c.aclose()
