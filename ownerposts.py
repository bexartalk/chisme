"""Owner posts: Goonie's own chisme (news, weather, events, sports, food, anything) in the Chisme feed.

Kept out of app.py so merges stay easy: app.py only calls ownerposts.install(app, ...) and passes its owner check.

* Storage that survives Render's free-plan redeploys: Supabase (Postgres table public.owner_posts + the public Storage
  bucket "owner-posts"), used when SUPABASE_URL and SUPABASE_SERVICE_KEY (the server-only secret / service_role key) are
  set. The key never leaves the server: phones only ever talk to Chisme, which reads and writes Supabase itself.
  Without those env vars: a local SQLite file + a folder (OWNER_POSTS_DIR, default /tmp/chisme-owner-posts), the same
  interface, for tests and local runs (on Render it's wiped on every deploy; /stats says so).
  The table's migration (RLS on: the public can read published posts only) is supabase/migrations/*_owner_posts.sql.
* Owner only (the same sign-in as /stats and Juan's god mode): the composer at /stats/posts, and every write under
  /stats/posts/... (the /stats cookie is HttpOnly, SameSite=Strict, path=/stats; writes must be JSON and same-origin,
  or carry `Authorization: Bearer <ADMIN_TOKEN>` from a script). Everyone else: 401 (404 with no ADMIN_TOKEN), and a
  cross-site request: 403.
* Photos: up to 3 per post. JPEG / PNG / WebP only, 8 MB max; the server re-encodes every photo as WebP (1600 px max),
  which drops EXIF (GPS, camera, time), XMP and ICC metadata. Each photo has its own credit line.
* Location: the text shown on the post + a Google Maps search link; with a map pin (lat, lon) the server also draws a
  small static map from OpenStreetMap tiles once, at save time (free, no API key; credited "© OpenStreetMap
  contributors"), stored with the photos. OWNER_POSTS_STATIC_MAP=0 turns that off.
* Public: GET /api/posts (the feed's list), GET /api/posts/{slug}, GET /p/{slug} (a real page with Open Graph tags; the
  first photo is og:image), GET /api/posts/media/... (local storage only).
* Push: optional, after a preview. Uses the app's existing Web Push (push.py; VAPID keys on Render). With no VAPID keys
  the composer shows "not set up yet" and the endpoint answers 503. The store app's native push (FCM) is not here.
* News posts stay straight: no emoji anywhere in a News post (refused, never silently changed), plain styling."""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import html
import io
import json
import math
import os
import re
import secrets
import sqlite3
import time
import unicodedata
import urllib.parse
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

BASE = Path(__file__).parent
CT = ZoneInfo("America/Chicago")

CATEGORIES = {   # id: (label, emoji for the non-news cards)
    "news": ("News", ""),
    "weather": ("Weather", "🌤️"),
    "events": ("Events", "🎉"),
    "sports": ("Sports", "🏀"),
    "food": ("Food", "🌮"),
    "other": ("Other", "👀"),
}
MAX_HEADLINE, MAX_BODY, MAX_CREDIT, MAX_ALT, MAX_LOCATION, MAX_SOURCE_NAME, MAX_URL = 140, 6000, 120, 200, 200, 160, 1800
MAX_PHOTOS = 3
MAX_UPLOAD = 8 * 1024 * 1024          # decoded photo bytes
MAX_UPLOAD_BODY = 12 * 1024 * 1024    # the JSON (base64) request
MAX_PIXELS = 50_000_000               # decompression bombs
PHOTO_EDGE = 1600
STORE_MAX = 1_900_000                 # the bucket allows 2 MB
PIN_MAX_HOURS = 24 * 30
FRESH_HOURS = int(os.environ.get("OWNER_POSTS_FRESH_HOURS", "72") or 72)   # unpinned posts stay at the top this long
PHOTO_RX = re.compile(r"^p/\d{6}/[A-Za-z0-9_-]{12}\.webp$")
MAP_RX = re.compile(r"^m/\d{6}/[A-Za-z0-9_-]{12}\.webp$")
SLUG_RX = re.compile(r"^[a-z0-9][a-z0-9-]{2,95}$")
URL_RX = re.compile(r"^https?://[^\s<>\"'`\\]{3,1800}$", re.I)
EMOJI_RX = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D\u20E3\U000E0020-\U000E007F]")
CTRL_RX = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F\u200B\u200E\u200F\u202A-\u202E\u2066-\u2069\uFEFF]")


# ---------------------------------------------------------------- config
def _env(*names: str) -> str:
    for n in names:
        v = (os.environ.get(n) or "").strip().strip("\"'")
        if v:
            return v
    return ""


def supabase_conf() -> tuple[str, str, str]:
    url = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    bucket = _env("OWNER_POSTS_BUCKET") or "owner-posts"
    if url and not re.match(r"^https://[a-z0-9-]+\.supabase\.(co|in)$|^https?://(localhost|127\.0\.0\.1)(:\d+)?$", url):
        print("SUPABASE_URL doesn't look like https://<project>.supabase.co; owner posts use local storage")
        return "", "", bucket
    return url, key, bucket


# ---------------------------------------------------------------- storage backends (same interface)
class LocalStore:
    """SQLite + a folder. For tests and local runs (on Render's free plan it's wiped on every deploy)."""
    name = "local"
    durable = False

    def __init__(self, folder: str):
        self.dir = Path(folder)
        (self.dir / "media").mkdir(parents=True, exist_ok=True)
        self.db = str(self.dir / "posts.db")
        with sqlite3.connect(self.db) as c:
            c.execute("create table if not exists owner_posts (id text primary key, slug text unique not null, data text not null, "
                      "status text not null, created_at text not null)")

    def _rows(self, where: str = "", args: tuple = ()) -> list[dict]:
        with sqlite3.connect(self.db) as c:
            return [json.loads(r[0]) for r in c.execute(f"select data from owner_posts {where} order by created_at desc", args)]

    async def list(self, drafts: bool = False, limit: int = 60) -> list[dict]:
        return (self._rows() if drafts else self._rows("where status = 'published'"))[:limit]

    async def get(self, *, id: str | None = None, slug: str | None = None, drafts: bool = False) -> dict | None:
        rows = self._rows("where id = ?", (id,)) if id else self._rows("where slug = ?", (slug,))
        r = rows[0] if rows else None
        return r if r and (drafts or r.get("status") == "published") else None

    async def insert(self, rec: dict) -> dict:
        now = _iso(time.time())
        rec = {**rec, "id": secrets.token_hex(16), "created_at": now, "updated_at": now}
        with sqlite3.connect(self.db) as c:
            c.execute("insert into owner_posts values (?, ?, ?, ?, ?)", (rec["id"], rec["slug"], json.dumps(rec), rec["status"], rec["created_at"]))
        return rec

    async def update(self, id: str, fields: dict) -> dict | None:
        cur = await self.get(id=id, drafts=True)
        if not cur:
            return None
        rec = {**cur, **fields, "updated_at": _iso(time.time())}
        with sqlite3.connect(self.db) as c:
            c.execute("update owner_posts set data = ?, status = ? where id = ?", (json.dumps(rec), rec["status"], id))
        return rec

    async def delete(self, id: str) -> bool:
        with sqlite3.connect(self.db) as c:
            return c.execute("delete from owner_posts where id = ?", (id,)).rowcount > 0

    async def put_file(self, name: str, data: bytes) -> None:
        p = self.dir / "media" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    async def delete_files(self, names: list[str]) -> None:
        for n in names:
            try:
                (self.dir / "media" / n).unlink()
            except FileNotFoundError:
                pass

    def file_url(self, name: str) -> str:
        return "/api/posts/media/" + name

    def local_path(self, name: str) -> Path | None:
        p = (self.dir / "media" / name).resolve()
        return p if p.is_file() and str(p).startswith(str((self.dir / "media").resolve()) + os.sep) else None


class SupabaseStore:
    """Postgres via PostgREST + Supabase Storage, with the server-only secret key (bypasses RLS; never sent to phones)."""
    name = "supabase"
    durable = True
    COLS = ("slug", "status", "category", "headline", "body", "photos", "location", "map_query", "lat", "lon", "map_image",
            "source_url", "source_name", "pinned_until", "push_sent_at", "sponsored")

    def __init__(self, url: str, key: str, bucket: str, client: httpx.AsyncClient | None = None):
        self.url, self.key, self.bucket = url, key, bucket
        self.http = client or httpx.AsyncClient(timeout=20)

    def _h(self, extra: dict | None = None) -> dict:
        h = {"apikey": self.key}
        if self.key.startswith("eyJ"):   # a legacy service_role JWT also goes in Authorization (sb_secret_ keys don't need it)
            h["Authorization"] = "Bearer " + self.key
        return {**h, **(extra or {})}

    def _t(self) -> str:
        return f"{self.url}/rest/v1/owner_posts"

    @staticmethod
    def _ok(r: httpx.Response) -> httpx.Response:
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase {r.status_code}")   # never the body (it can echo the request)
        return r

    async def list(self, drafts: bool = False, limit: int = 60) -> list[dict]:
        q = {"select": "*", "order": "created_at.desc", "limit": str(limit)}
        if not drafts:
            q["status"] = "eq.published"
        return self._ok(await self.http.get(self._t(), params=q, headers=self._h())).json()

    async def get(self, *, id: str | None = None, slug: str | None = None, drafts: bool = False) -> dict | None:
        q = {"select": "*", "limit": "1"}
        if id:
            if not re.fullmatch(r"[0-9a-f-]{32,36}", id):
                return None
            q["id"] = "eq." + id
        else:
            q["slug"] = "eq." + str(slug)
        if not drafts:
            q["status"] = "eq.published"
        rows = self._ok(await self.http.get(self._t(), params=q, headers=self._h())).json()
        return rows[0] if rows else None

    async def insert(self, rec: dict) -> dict:
        body = {k: rec.get(k) for k in self.COLS}
        r = self._ok(await self.http.post(self._t(), json=body, headers=self._h({"Prefer": "return=representation"})))
        return r.json()[0]

    async def update(self, id: str, fields: dict) -> dict | None:
        body = {k: v for k, v in fields.items() if k in self.COLS}
        r = self._ok(await self.http.patch(self._t(), params={"id": "eq." + id}, json=body, headers=self._h({"Prefer": "return=representation"})))
        rows = r.json()
        return rows[0] if rows else None

    async def delete(self, id: str) -> bool:
        r = self._ok(await self.http.delete(self._t(), params={"id": "eq." + id}, headers=self._h({"Prefer": "return=representation"})))
        return bool(r.json())

    async def put_file(self, name: str, data: bytes) -> None:
        self._ok(await self.http.post(f"{self.url}/storage/v1/object/{self.bucket}/{name}", content=data,
                                      headers=self._h({"Content-Type": "image/webp", "Cache-Control": "max-age=31536000", "x-upsert": "false"})))

    async def delete_files(self, names: list[str]) -> None:
        if names:
            self._ok(await self.http.request("DELETE", f"{self.url}/storage/v1/object/{self.bucket}", json={"prefixes": names}, headers=self._h()))

    def file_url(self, name: str) -> str:
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"

    def local_path(self, name: str) -> Path | None:
        return None


_store: Any = None


def store():
    global _store
    url, key, bucket = supabase_conf()
    want = ("supabase", url, key, bucket) if url and key else ("local", os.environ.get("OWNER_POSTS_DIR") or "/tmp/chisme-owner-posts")
    if _store is None or getattr(_store, "_want", None) != want:
        _store = SupabaseStore(url, key, bucket) if want[0] == "supabase" else LocalStore(want[1])
        _store._want = want
    return _store


def storage_status() -> dict:
    url, key, _ = supabase_conf()
    st = store()
    return {"backend": st.name, "durable": st.durable, "supabase_url": bool(url), "supabase_key": bool(key)}


# ---------------------------------------------------------------- text
def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _ts(v) -> float | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def clean_line(v, n: int) -> str:
    """One line: no control / invisible / bidi characters, spaces squeezed, trimmed to n."""
    s = unicodedata.normalize("NFC", CTRL_RX.sub("", str(v or "")))
    return re.sub(r"\s+", " ", s).strip()[:n]


def clean_text(v, n: int) -> str:
    """Multi-line text (the body): the same, keeping line breaks (at most 2 blank lines in a row)."""
    s = unicodedata.normalize("NFC", str(v or "").replace("\r\n", "\n").replace("\r", "\n"))
    s = CTRL_RX.sub("", s).replace("\t", " ")
    s = "\n".join(re.sub(r"[ \u00a0]+", " ", ln).rstrip() for ln in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()[:n]


def clean_url(v) -> str | None:
    s = clean_line(v, MAX_URL)
    if not s:
        return None
    if not URL_RX.match(s):
        raise ValueError("The source link must start with http:// or https://")
    p = urllib.parse.urlsplit(s)
    if p.scheme.lower() not in ("http", "https") or not p.hostname or "." not in p.hostname or p.username or p.password:
        raise ValueError("The source link must start with http:// or https://")
    return s


def has_emoji(*texts: str) -> bool:
    return any(EMOJI_RX.search(t or "") for t in texts)


def slugify(headline: str) -> str:
    s = unicodedata.normalize("NFKD", headline).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"['’`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 60:
        s = s[:61].rsplit("-", 1)[0] if "-" in s[:61] else s[:60]
    s = s.strip("-") or "post"
    return f"{s}-{secrets.token_hex(2)}"


def body_blocks(text: str) -> list[dict]:
    """The body's light formatting, parsed once (the page, the app and the tests share the shape):
    blank line = new paragraph; lines starting with "- " or "• " = a bullet list; **bold**. Nothing else (no HTML)."""
    blocks: list[dict] = []
    para: list[str] = []
    items: list[str] = []

    def flush():
        nonlocal para, items
        if para:
            blocks.append({"t": "p", "lines": para}); para = []
        if items:
            blocks.append({"t": "ul", "items": items}); items = []
    for ln in (text or "").split("\n"):
        s = ln.strip()
        if not s:
            flush(); continue
        m = re.match(r"^[-•*]\s+(.*)$", s)
        if m and not s.startswith("**"):
            if para:
                blocks.append({"t": "p", "lines": para}); para = []
            items.append(m.group(1)); continue
        if items:
            blocks.append({"t": "ul", "items": items}); items = []
        para.append(s)
    flush()
    return blocks


def inline_html(s: str) -> str:
    """Escape first, then **bold** → <strong>. The only markup a post's text can make."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s, quote=True))


def body_html(text: str) -> str:
    out = []
    for b in body_blocks(text):
        if b["t"] == "p":
            out.append("<p>" + "<br>".join(inline_html(x) for x in b["lines"]) + "</p>")
        else:
            out.append("<ul>" + "".join(f"<li>{inline_html(x)}</li>" for x in b["items"]) + "</ul>")
    return "\n".join(out)


def plain(text: str, n: int = 200) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", text or "")
    s = re.sub(r"(?m)^[-•*]\s+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def gmaps_url(q: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(q)


# ---------------------------------------------------------------- photos
class PhotoError(ValueError):
    pass


def sniff(raw: bytes) -> str | None:
    if raw[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    if raw[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftyphevc", b"ftypavif"):
        return "heic"
    return None


def decode_data_url(data: str) -> bytes:
    m = re.match(r"^data:(image/(?:jpeg|jpg|png|webp));base64,([A-Za-z0-9+/=\s]+)$", data or "", re.S)
    if not m:
        raise PhotoError("Photos must be JPEG, PNG or WebP.")
    if len(m.group(2)) > MAX_UPLOAD * 4 // 3 + 16:
        raise PhotoError("That photo is too big (8 MB max).")
    try:
        return base64.b64decode(re.sub(r"\s+", "", m.group(2)), validate=True)
    except (binascii.Error, ValueError):
        raise PhotoError("That photo didn't upload properly. Try again.")


def process_photo(raw: bytes, edge: int = PHOTO_EDGE) -> tuple[bytes, int, int]:
    """Any JPEG / PNG / WebP → a clean WebP: turned upright (EXIF orientation), resized, re-encoded from the pixels only,
    so no EXIF (GPS, camera, time), XMP, ICC or comments survive."""
    from PIL import Image, ImageOps
    if len(raw) > MAX_UPLOAD:
        raise PhotoError("That photo is too big (8 MB max).")
    kind = sniff(raw)
    if kind == "heic":
        raise PhotoError("HEIC photos can't be read here. On iPhone, pick the photo again from the composer (it converts it).")
    if kind not in ("jpeg", "png", "webp"):
        raise PhotoError("Photos must be JPEG, PNG or WebP.")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(raw))
            if (im.format or "").lower() not in ("jpeg", "png", "webp") or (im.format or "").lower() != kind:
                raise PhotoError("Photos must be JPEG, PNG or WebP.")
            if im.width * im.height > MAX_PIXELS:
                raise PhotoError("That photo is too large (50 megapixels max).")
            im.seek(0)
            im.load()
            im = ImageOps.exif_transpose(im)
    except PhotoError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise PhotoError("That photo is too large (50 megapixels max).")
    except Exception:
        raise PhotoError("That file isn't a photo Chisme can read.")
    if min(im.size) < 64:
        raise PhotoError("That photo is too small (64 px minimum).")
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((edge, edge), Image.LANCZOS)
    clean = Image.new("RGB", im.size)
    clean.paste(im)   # pixels only: nothing from the original file's info rides along
    for q, e2 in ((80, None), (70, None), (68, 1280), (60, 1024)):
        img = clean
        if e2 and max(img.size) > e2:
            img = clean.copy(); img.thumbnail((e2, e2), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=q, method=4)
        if buf.tell() <= STORE_MAX:
            return buf.getvalue(), img.width, img.height
    raise PhotoError("That photo is too big even after shrinking it.")


def media_name(kind: str) -> str:
    return f"{kind}/{datetime.now(CT).strftime('%Y%m')}/{secrets.token_urlsafe(9)}.webp"


# ---------------------------------------------------------------- the static map (OpenStreetMap tiles, drawn once)
TILE = 256


def _tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x * TILE, y * TILE


def no_yellow(im):
    """Chisme has no yellow anywhere: OpenStreetMap's yellow / cream / beige roads and areas (hue 25–70°) turn silver
    (their saturation goes to 0), the rest of the map keeps its colours. Same rule as news_no_yellow_test."""
    from PIL import Image, ImageChops
    h, s, v = im.convert("HSV").split()
    band = h.point(lambda x: 255 if 17 <= x <= 50 else 0)        # Pillow hue 0–255: 25°–70°
    sat = s.point(lambda x: 255 if x >= 8 else 0)
    mask = ImageChops.multiply(band, sat)
    s2 = Image.composite(s.point(lambda x: 0), s, mask)          # pure silver / grey (a pale tint still reads as cream)
    return Image.merge("HSV", (h, s2, v)).convert("RGB")


async def render_map(lat: float, lon: float, ua: str, z: int = 16, w: int = 640, h: int = 320,
                     client: httpx.AsyncClient | None = None) -> bytes | None:
    """A small map with a pin, from ~6 OpenStreetMap tiles (their usage policy: an identifying User-Agent, light use, the
    credit on the image). Drawn once when the post is saved and stored with it, never per visitor. None if it fails."""
    if os.environ.get("OWNER_POSTS_STATIC_MAP", "1") == "0":
        return None
    from PIL import Image, ImageDraw, ImageFont
    tpl = os.environ.get("OSM_TILE_URL") or "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    cx, cy = _tile_xy(lat, lon, z)
    x0, y0 = cx - w / 2, cy - h / 2
    tx0, ty0, tx1, ty1 = int(x0 // TILE), int(y0 // TILE), int((x0 + w) // TILE), int((y0 + h) // TILE)
    canvas = Image.new("RGB", (w, h), (230, 236, 238))
    own = client is None
    c = client or httpx.AsyncClient(timeout=10, headers={"User-Agent": ua, "Referer": "https://chisme.co/"})
    try:
        async def one(tx: int, ty: int):
            r = await c.get(tpl.format(z=z, x=tx % (2 ** z), y=ty))
            r.raise_for_status()
            return tx, ty, Image.open(io.BytesIO(r.content)).convert("RGB")
        tiles = await asyncio.gather(*(one(tx, ty) for tx in range(tx0, tx1 + 1) for ty in range(ty0, ty1 + 1)))
    except Exception as ex:
        print("owner posts map:", type(ex).__name__)
        return None
    finally:
        if own:
            await c.aclose()
    for tx, ty, im in tiles:
        canvas.paste(im, (int(tx * TILE - x0), int(ty * TILE - y0)))
    canvas = no_yellow(canvas)
    d = ImageDraw.Draw(canvas)
    px, py = w // 2, h // 2
    d.ellipse((px - 15, py - 15, px + 15, py + 15), fill=(0, 0, 0))
    d.ellipse((px - 11, py - 11, px + 11, py + 11), fill=(255, 26, 127))
    d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(255, 255, 255))
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    txt = "© OpenStreetMap contributors"
    tw = d.textlength(txt, font=font)
    d.rectangle((w - tw - 12, h - 21, w, h), fill=(255, 255, 255))
    d.text((w - tw - 6, h - 18), txt, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    canvas.save(buf, "WEBP", quality=78, method=4)
    return buf.getvalue()


# ---------------------------------------------------------------- validation
def clean_post(body: dict, cur: dict | None = None, now: float | None = None) -> tuple[dict | None, str]:
    """The owner's fields → a stored record (or a plain-English error). `cur`: the post being edited."""
    now = now or time.time()
    cur = cur or {}
    try:
        cat = str(body.get("category", cur.get("category") or "")).strip().lower()
        if cat not in CATEGORIES:
            return None, "Pick a category."
        headline = clean_line(body.get("headline", cur.get("headline")), MAX_HEADLINE + 1)
        if not headline:
            return None, "Write a headline."
        if len(headline) > MAX_HEADLINE:
            return None, f"The headline is too long ({MAX_HEADLINE} characters max)."
        text = clean_text(body.get("body", cur.get("body")), MAX_BODY + 1)
        if len(text) > MAX_BODY:
            return None, f"The text is too long ({MAX_BODY:,} characters max)."
        photos_in = body.get("photos", cur.get("photos") or [])
        if not isinstance(photos_in, list):
            return None, "Photos didn't come through. Try again."
        if len(photos_in) > MAX_PHOTOS:
            return None, f"Up to {MAX_PHOTOS} photos."
        photos = []
        for p in photos_in:
            if not isinstance(p, dict) or not PHOTO_RX.match(str(p.get("name") or "")):
                return None, "A photo didn't upload properly. Remove it and add it again."
            photos.append({"name": p["name"], "w": int(p.get("w") or 0) or None, "h": int(p.get("h") or 0) or None,
                           "credit": clean_line(p.get("credit"), MAX_CREDIT), "alt": clean_line(p.get("alt"), MAX_ALT)})
        location = clean_line(body.get("location", cur.get("location")), MAX_LOCATION) or None
        map_query = clean_line(body.get("map_query", cur.get("map_query")), MAX_LOCATION) or None
        lat, lon = body.get("lat", cur.get("lat")), body.get("lon", cur.get("lon"))
        if lat in ("", None) or lon in ("", None):
            lat = lon = None
        else:
            lat, lon = float(lat), float(lon)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
                return None, "That map pin isn't a real place."
            lat, lon = round(lat, 5), round(lon, 5)
        if (lat is not None) and not (location or map_query):
            return None, "Add the location text for the map pin."
        source_url = clean_url(body.get("source_url", cur.get("source_url")))
        source_name = clean_line(body.get("source_name", cur.get("source_name")), MAX_SOURCE_NAME) or None
        status = str(body.get("status", cur.get("status") or "published"))
        if status not in ("published", "draft"):
            return None, "Status must be published or draft."
        sp = body.get("sponsored", cur.get("sponsored", False))
        if sp not in (True, False, None, 0, 1):
            return None, "Something in the form isn't right. Check the numbers."
        sponsored = bool(sp)
        pin = body.get("pin_hours", None)
        pinned_until = cur.get("pinned_until")
        if pin is not None and pin != "":
            hours = float(pin)
            if hours < 0 or hours > PIN_MAX_HOURS:
                return None, "Pins last up to 30 days."
            pinned_until = _iso(now + hours * 3600) if hours > 0 else None
    except (TypeError, ValueError) as ex:
        msg = str(ex)
        return None, msg if msg.startswith("The source link") else "Something in the form isn't right. Check the numbers."
    if sponsored and cat == "news":
        return None, "Paid posts can't go in News (news stays independent). Pick Events or Other for a sponsor post."
    if cat == "news":
        texts = [headline, text, location or "", map_query or "", source_name or ""] + [p["credit"] + p["alt"] for p in photos]
        if has_emoji(*texts):
            return None, "News posts stay straight: take out the emoji first."
    rec = {"category": cat, "headline": headline, "body": text, "photos": photos, "location": location, "map_query": map_query,
           "lat": lat, "lon": lon, "source_url": source_url, "source_name": source_name, "status": status, "pinned_until": pinned_until,
           "sponsored": sponsored}
    return rec, ""


# ---------------------------------------------------------------- public shape
def public(rec: dict, st=None, now: float | None = None) -> dict:
    st = st or store()
    now = now or time.time()
    pu = _ts(rec.get("pinned_until"))
    cat = rec.get("category") or "other"
    q = rec.get("map_query") or rec.get("location") or ""
    mi = rec.get("map_image") if isinstance(rec.get("map_image"), dict) else None
    return {
        "id": rec.get("id"), "slug": rec.get("slug"), "url": "/p/" + str(rec.get("slug")), "app_url": "/?post=" + str(rec.get("slug")),
        "category": cat, "category_label": CATEGORIES.get(cat, ("Other", ""))[0],
        "headline": rec.get("headline") or "", "body": rec.get("body") or "", "summary": plain(rec.get("body") or "", 220),
        "photos": [{"url": st.file_url(p["name"]), "w": p.get("w"), "h": p.get("h"), "credit": p.get("credit") or "", "alt": p.get("alt") or ""}
                   for p in rec.get("photos") or [] if isinstance(p, dict) and PHOTO_RX.match(str(p.get("name") or ""))],
        "location": rec.get("location") or "", "maps_url": gmaps_url(q) if q else "",
        "lat": rec.get("lat"), "lon": rec.get("lon"),
        "map_image": ({"url": st.file_url(mi["name"]), "w": mi.get("w"), "h": mi.get("h")} if mi and MAP_RX.match(str(mi.get("name") or "")) else None),
        "source_url": rec.get("source_url") or "", "source_name": rec.get("source_name") or "",
        "sponsored": bool(rec.get("sponsored")),   # paid / sponsor post: a "Sponsored" label everywhere it shows (FTC)
        "pinned": bool(pu and pu > now), "pinned_until": rec.get("pinned_until") if pu and pu > now else None,
        "status": rec.get("status") or "published",
        "created_at": rec.get("created_at"), "updated_at": rec.get("updated_at"), "push_sent_at": rec.get("push_sent_at"),
    }


def feed_order(posts: list[dict], now: float | None = None) -> list[dict]:
    """Pinned (unexpired) first, newest first within each group."""
    now = now or time.time()
    return sorted(posts, key=lambda p: (not p["pinned"], -(_ts(p.get("created_at")) or 0)))


_feed_mem: dict = {"at": 0.0, "v": None}


def bust() -> None:
    _feed_mem.update(at=0.0, v=None)


async def feed(now: float | None = None) -> dict:
    t = time.time()
    if _feed_mem["v"] is not None and t - _feed_mem["at"] < 30:
        return _feed_mem["v"]
    st = store()
    rows = await st.list(drafts=False, limit=40)
    out = {"posts": feed_order([public(r, st, now) for r in rows], now), "fresh_hours": FRESH_HOURS}
    _feed_mem.update(at=t, v=out)
    return out


# ---------------------------------------------------------------- push (the app's Web Push: push.py)
def push_payload(p: dict) -> dict:
    """What the notification says: the headline as the title, the first lines of the text, opening the post in Chisme."""
    title = p["headline"] if len(p["headline"]) <= 80 else p["headline"][:79].rsplit(" ", 1)[0] + "…"
    body = plain(p["body"], 160) or (p["location"] or "New from Chisme")
    if p.get("sponsored"):
        body = "Sponsored · " + body
    return {"title": title, "body": body, "url": "/?post=" + p["slug"] + "#chisme", "tag": "chisme-post-" + p["slug"]}


async def push_state() -> dict:
    import push
    if not push.enabled():
        return {"enabled": False, "phones": 0, "why": "Push isn't set up on this server yet (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY and VAPID_SUBJECT are missing)."}
    try:
        recs = list((await push.store().all()).values())
    except Exception as ex:
        return {"enabled": False, "phones": 0, "why": f"The push storage didn't answer ({type(ex).__name__})."}
    n = sum(1 for r in recs if r.get("sub") and push.wants_news(r))
    return {"enabled": True, "phones": n, "why": ""}


# ---------------------------------------------------------------- the /p/<slug> page
def _when(iso: str | None) -> str:
    t = _ts(iso)
    if not t:
        return ""
    d = datetime.fromtimestamp(t, CT)
    return d.strftime("%a, %b %-d, %Y, %-I:%M %p CT")   # the same shape the app's sheet shows


def post_page(p: dict, base: str, nonce: str = "") -> str:
    import website
    e = lambda v: html.escape(str(v or ""), quote=True)
    news = p["category"] == "news"
    url = base + p["url"]
    desc = p["summary"] or p["location"] or "From Chisme"
    if p.get("sponsored"):
        desc = "Sponsored · " + desc   # the FTC disclosure, in every link preview too
    first = p["photos"][0] if p["photos"] else None
    img = first["url"] if first else (p["map_image"]["url"] if p["map_image"] else website.OG_IMAGE)
    img = img if img.startswith("http") else base + img
    iw, ih = (first.get("w"), first.get("h")) if first else ((p["map_image"] or {}).get("w"), (p["map_image"] or {}).get("h")) if p["map_image"] else (1200, 630)
    alt = (first.get("alt") or p["headline"]) if first else p["headline"]
    label, emo = CATEGORIES.get(p["category"], ("Other", ""))
    og_title = p["headline"]
    meta = [
        f'<meta name="description" content="{e(desc)}">', f'<link rel="canonical" href="{e(url)}">',
        '<meta property="og:site_name" content="Chisme">', '<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{e(og_title)}">', f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(url)}">', f'<meta property="og:image" content="{e(img)}">',
        *([f'<meta property="og:image:width" content="{int(iw)}">', f'<meta property="og:image:height" content="{int(ih)}">'] if iw and ih else []),
        f'<meta property="og:image:alt" content="{e(alt)}">', '<meta property="og:locale" content="en_US">',
        f'<meta property="article:published_time" content="{e(p["created_at"])}">',
        *([f'<meta property="article:modified_time" content="{e(p["updated_at"])}">'] if p.get("updated_at") and p["updated_at"] != p["created_at"] else []),
        f'<meta property="article:section" content="{e(label)}">',
        '<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:title" content="{e(og_title)}">',
        f'<meta name="twitter:description" content="{e(desc)}">', f'<meta name="twitter:image" content="{e(img)}">',
        f'<meta name="twitter:image:alt" content="{e(alt)}">',
    ]
    ld = {"@context": "https://schema.org", "@type": "NewsArticle" if news else "Article", "headline": p["headline"],
          "datePublished": p["created_at"], "dateModified": p.get("updated_at") or p["created_at"], "image": [img],
          "publisher": {"@type": "Organization", "name": "Chisme"}, "mainEntityOfPage": url}
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    figs = []
    for i, ph in enumerate(p["photos"]):
        size = f' width="{int(ph["w"])}" height="{int(ph["h"])}"' if ph.get("w") and ph.get("h") else ""
        load = ' fetchpriority="high"' if i == 0 else ' loading="lazy"'
        cap = f'<figcaption>{e(ph["credit"])}</figcaption>' if ph.get("credit") else ""
        figs.append(f'<figure class="op-fig{" op-lead" if i == 0 else ""}"><img src="{e(ph["url"])}" alt="{e(ph["alt"] or "Photo " + str(i + 1))}"'
                    f'{size}{load} decoding="async">{cap}</figure>')
    photos = "".join(figs)
    where = ""
    if p["location"] or p["maps_url"]:
        mp = ""
        if p["map_image"]:
            mi = p["map_image"]
            mp = (f'<a class="op-map" href="{e(p["maps_url"])}" target="_blank" rel="noopener noreferrer"><img src="{e(mi["url"])}" alt="Map of {e(p["location"] or "the location")}"'
                  f' width="{int(mi.get("w") or 640)}" height="{int(mi.get("h") or 320)}" loading="lazy" decoding="async"></a>'
                  '<p class="op-mapc">Map © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors</p>')
        where = (f'<div class="op-where"><p><strong>Where:</strong> {e(p["location"])}</p>'
                 + (f'<p><a class="op-gmaps" href="{e(p["maps_url"])}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a></p>' if p["maps_url"] else "")
                 + mp + "</div>")
    src = ""
    if p["source_url"] or p["source_name"]:
        name = e(p["source_name"] or urllib.parse.urlsplit(p["source_url"]).hostname or "the source")
        src = (f'<p class="op-src"><strong>Source:</strong> '
               + (f'<a href="{e(p["source_url"])}" target="_blank" rel="noopener noreferrer nofollow">{name}</a>' if p["source_url"] else name) + "</p>")
    upd = (f' · Updated {e(_when(p["updated_at"]))}' if p.get("updated_at") and (_ts(p["updated_at"]) or 0) - (_ts(p["created_at"]) or 0) > 120 else "")
    cat_html = e(label) if news else f'<span aria-hidden="true">{emo}</span> {e(label)}'
    b = website.app_build()
    body = f"""<article class="op-article op-{e(p["category"])}">
<p class="op-badges"><span class="op-badge">From Chisme</span><span class="op-cat">{cat_html}</span>{'<span class="op-spon">Sponsored</span>' if p.get("sponsored") else ''}{'<span class="op-pin">Pinned</span>' if p["pinned"] else ''}</p>
<h1 class="op-h1">{e(p["headline"])}</h1>
<p class="op-time">Posted {e(_when(p["created_at"]))}{upd}</p>
{photos}
<div class="op-body">{body_html(p["body"])}</div>
{where}
{src}
<p class="op-open"><a class="btn" href="{e(p["app_url"])}">Open in Chisme</a></p>
</article>"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(p["headline"])} · Chisme</title>
{chr(10).join(meta)}
<script type="application/ld+json" nonce="{e(nonce)}">{ld_json}</script>
<meta name="theme-color" content="#00C9CD">
<link rel="icon" href="/static/icons/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png" sizes="180x180">
<link rel="stylesheet" href="/static/site.css?v={b}">
<link rel="stylesheet" href="/static/ownerposts.css?v={b}">
</head>
<body class="site op-page{' op-page-news' if news else ''}">
<a class="skip" href="#main">Skip to the content</a>
{website.site_nav()}
<main id="main" class="site-main">
{body}
</main>
{website.site_footer()}
</body>
</html>"""


def missing_page() -> str:
    import website
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Post not found · Chisme</title><meta name="robots" content="noindex"><link rel="stylesheet" href="/static/site.css?v={website.app_build()}"></head>
<body class="site">{website.site_nav()}<main id="main" class="site-main"><article class="prose"><h1>That post isn't here</h1>
<p>It may have been taken down. <a href="/">Open Chisme</a> for the latest.</p></article></main>{website.site_footer()}</body></html>"""


# ---------------------------------------------------------------- routes
def same_origin(request: Request) -> bool:
    """CSRF, on top of the SameSite=Strict cookie and the JSON-only rule: a browser request must come from this site."""
    sfs = (request.headers.get("sec-fetch-site") or "").lower()
    if sfs and sfs not in ("same-origin", "none"):
        return False
    origin = request.headers.get("origin")
    if origin is None:
        return True
    host = request.headers.get("host") or request.url.netloc
    try:
        return origin != "null" and urllib.parse.urlsplit(origin).netloc == host
    except Exception:
        return False


HDR = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "no-referrer"}


def install(app: FastAPI, *, owner: Callable[..., Awaitable[bool]], nope: Callable[[], Response], public_base: Callable[[Request], str],
            nonce: Callable[[Request], str], ua: str, signed_in: Callable[[Request], Awaitable[bool]]) -> None:
    """owner(request, json_only=True): app.py's _juan_admin (the /stats sign-in + a JSON body, or Bearer ADMIN_TOKEN)."""

    def forbidden() -> JSONResponse:
        return JSONResponse({"ok": False, "error": "cross-site request refused"}, status_code=403, headers=HDR)

    async def guard(request: Request, write: bool = True) -> Response | None:
        if not await owner(request, json_only=write):
            return nope()
        if write and not same_origin(request):
            return forbidden()
        return None

    def bad(msg: str, code: int = 400) -> JSONResponse:
        return JSONResponse({"ok": False, "error": msg}, status_code=code, headers=HDR)

    async def body_of(request: Request, limit: int) -> dict | None:
        raw = await request.body()
        if len(raw) > limit:
            return None
        try:
            d = json.loads(raw or b"{}")
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def storage_err(ex: Exception) -> JSONResponse:
        print("owner posts storage:", type(ex).__name__, str(ex)[:80])
        return bad(f"Couldn't reach the post storage ({type(ex).__name__}). Try again in a minute.", 503)

    # ---- public
    @app.get("/api/posts")
    async def api_posts():
        try:
            return JSONResponse(await feed(), headers={"Cache-Control": "no-cache"})
        except Exception as ex:
            print("owner posts feed:", type(ex).__name__)
            return JSONResponse({"posts": [], "error": "Couldn't load Chisme's own posts right now."}, status_code=503)

    @app.get("/api/posts/media/{name:path}", include_in_schema=False)
    async def api_post_media(name: str):
        st = store()
        if not (PHOTO_RX.match(name) or MAP_RX.match(name)):
            return Response("Not Found", status_code=404)
        p = st.local_path(name)
        if not p:
            return Response("Not Found", status_code=404)
        return FileResponse(p, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})

    @app.get("/api/posts/{slug}")
    async def api_post(slug: str):
        if not SLUG_RX.match(slug):
            return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
        try:
            r = await store().get(slug=slug)
        except Exception:
            return JSONResponse({"ok": False, "error": "Couldn't load that post right now."}, status_code=503)
        if not r:
            return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
        return JSONResponse({"ok": True, "post": public(r)}, headers={"Cache-Control": "no-cache"})

    @app.get("/p/{slug}", include_in_schema=False)
    async def post_html(slug: str, request: Request):
        r = None
        if SLUG_RX.match(slug):
            try:
                r = await store().get(slug=slug)
            except Exception:
                return HTMLResponse(missing_page(), status_code=503, headers={"Retry-After": "30"})
        if not r:
            return HTMLResponse(missing_page(), status_code=404)
        return HTMLResponse(post_page(public(r), public_base(request), nonce(request)), headers={"Cache-Control": "no-cache"})

    # ---- owner
    @app.get("/stats/posts", include_in_schema=False)
    async def composer(request: Request):
        import ownerposts_admin
        if not await owner(request, json_only=False):
            if not await signed_in(request):
                return RedirectResponse("/stats", status_code=303, headers=HDR)
            return nope()
        try:
            posts = [public(r) for r in await store().list(drafts=True, limit=60)]
        except Exception as ex:
            posts, err = None, f"Couldn't load your posts ({type(ex).__name__})."
        else:
            err = ""
        return HTMLResponse(ownerposts_admin.page(posts, storage_status(), await push_state(), nonce=nonce(request), error=err,
                                                  edit=request.query_params.get("edit") or ""), headers=HDR)

    @app.get("/stats/posts/list", include_in_schema=False)
    async def owner_list(request: Request):
        if (g := await guard(request, write=False)):
            return g
        try:
            return JSONResponse({"ok": True, "posts": [public(r) for r in await store().list(drafts=True, limit=60)], "storage": storage_status()}, headers=HDR)
        except Exception as ex:
            return storage_err(ex)

    @app.post("/stats/posts/photo", include_in_schema=False)
    async def owner_photo(request: Request):
        if (g := await guard(request)):
            return g
        if int(request.headers.get("content-length") or 0) > MAX_UPLOAD_BODY:
            return bad("That photo is too big (8 MB max).", 413)
        b = await body_of(request, MAX_UPLOAD_BODY)
        if b is None:
            return bad("That photo is too big (8 MB max).", 413)
        try:
            raw = decode_data_url(str(b.get("data") or ""))
            out, w, h = await asyncio.to_thread(process_photo, raw)
        except PhotoError as ex:
            return bad(str(ex), 413 if "too big" in str(ex) or "too large" in str(ex) else 415)
        name = media_name("p")
        try:
            await store().put_file(name, out)
        except Exception as ex:
            return storage_err(ex)
        return JSONResponse({"ok": True, "photo": {"name": name, "url": store().file_url(name), "w": w, "h": h, "bytes": len(out)}}, headers=HDR)

    @app.get("/stats/posts/map-preview", include_in_schema=False)
    async def owner_map_preview(request: Request, lat: float, lon: float):
        if (g := await guard(request, write=False)):
            return g
        if not (-85 <= lat <= 85 and -180 <= lon <= 180):
            return bad("That map pin isn't a real place.")
        img = await render_map(lat, lon, ua)
        if not img:
            return bad("Couldn't draw the map right now (OpenStreetMap didn't answer).", 502)
        return Response(img, media_type="image/webp", headers=HDR)

    async def save_map(rec: dict, cur: dict | None) -> None:
        """Draw + store the static map when the pin is new or moved; drop the old one."""
        old = (cur or {}).get("map_image") if isinstance((cur or {}).get("map_image"), dict) else None
        moved = not cur or (cur.get("lat"), cur.get("lon")) != (rec["lat"], rec["lon"]) or not old
        if rec["lat"] is None:
            rec["map_image"] = None
        elif moved:
            img = await render_map(rec["lat"], rec["lon"], ua)
            if img:
                name = media_name("m")
                await store().put_file(name, img)
                rec["map_image"] = {"name": name, "w": 640, "h": 320}
            else:
                rec["map_image"] = None
        else:
            rec["map_image"] = old
        if old and old != rec.get("map_image"):
            try:
                await store().delete_files([old["name"]])
            except Exception:
                pass

    @app.post("/stats/posts", include_in_schema=False)
    async def owner_create(request: Request):
        if (g := await guard(request)):
            return g
        b = await body_of(request, 64000)
        if b is None:
            return bad("That post is too long.", 413)
        rec, err = clean_post(b)
        if not rec:
            return bad(err)
        try:
            await save_map(rec, None)
            rec["slug"] = slugify(rec["headline"])
            saved = await store().insert(rec)
        except Exception as ex:
            return storage_err(ex)
        bust()
        return JSONResponse({"ok": True, "post": public(saved)}, headers=HDR)

    @app.patch("/stats/posts/{pid}", include_in_schema=False)
    async def owner_update(pid: str, request: Request):
        if (g := await guard(request)):
            return g
        b = await body_of(request, 64000)
        if b is None:
            return bad("That post is too long.", 413)
        try:
            cur = await store().get(id=pid, drafts=True)
        except Exception as ex:
            return storage_err(ex)
        if not cur:
            return bad("That post isn't there anymore.", 404)
        rec, err = clean_post(b, cur)
        if not rec:
            return bad(err)
        try:
            await save_map(rec, cur)
            gone = {p["name"] for p in cur.get("photos") or []} - {p["name"] for p in rec["photos"]}
            saved = await store().update(pid, rec)
            if gone:
                await store().delete_files(sorted(gone))
        except Exception as ex:
            return storage_err(ex)
        bust()
        return JSONResponse({"ok": True, "post": public(saved)}, headers=HDR)

    @app.delete("/stats/posts/{pid}", include_in_schema=False)
    async def owner_delete(pid: str, request: Request):
        if (g := await guard(request)):
            return g
        b = await body_of(request, 2000) or {}
        if b.get("confirm") != "DELETE":
            return bad('Send {"confirm": "DELETE"} to delete a post.')
        try:
            cur = await store().get(id=pid, drafts=True)
            if not cur:
                return bad("That post isn't there anymore.", 404)
            await store().delete(pid)
            names = [p["name"] for p in cur.get("photos") or []] + ([cur["map_image"]["name"]] if isinstance(cur.get("map_image"), dict) else [])
            try:
                await store().delete_files(names)
            except Exception:
                pass
        except Exception as ex:
            return storage_err(ex)
        bust()
        return JSONResponse({"ok": True, "deleted": pid}, headers=HDR)

    @app.post("/stats/posts/push-preview", include_in_schema=False)
    async def owner_push_preview(request: Request):
        """What the notification would say for these fields (nothing saved, nothing sent) + who would get it."""
        if (g := await guard(request)):
            return g
        b = await body_of(request, 64000) or {}
        rec, err = clean_post(b)
        if not rec:
            return bad(err)
        p = {"headline": rec["headline"], "body": rec["body"], "location": rec["location"] or "", "slug": "<new-post>"}
        return JSONResponse({"ok": True, "payload": push_payload(p), **(await push_state())}, headers=HDR)

    @app.post("/stats/posts/{pid}/push", include_in_schema=False)
    async def owner_push(pid: str, request: Request):
        """Send the post as a notification (after the owner saw the preview): {"confirm": true}. Once per post unless
        {"again": true}. Uses the app's Web Push (push.py); 503 when it isn't set up."""
        import push
        if (g := await guard(request)):
            return g
        b = await body_of(request, 2000) or {}
        if b.get("confirm") is not True:
            return bad('Preview it first, then send {"confirm": true}.')
        try:
            cur = await store().get(id=pid, drafts=True)
        except Exception as ex:
            return storage_err(ex)
        if not cur:
            return bad("That post isn't there anymore.", 404)
        if cur.get("status") != "published":
            return bad("Publish the post before sending it as a notification.", 409)
        if cur.get("push_sent_at") and b.get("again") is not True:
            return bad("This post was already sent as a notification.", 409)
        stt = await push_state()
        if not stt["enabled"]:
            return bad(stt["why"], 503)
        payload = push_payload(public(cur))
        r = await push.broadcast(payload, urgent=False, ttl=6 * 3600)
        try:
            await store().update(pid, {"push_sent_at": _iso(time.time())})
            import autopush
            await push.store().list_push(autopush.K + "manual", json.dumps({"ts": time.time(), "title": payload["title"], "body": payload["body"],
                                                                           "url": payload["url"], **{k: r[k] for k in ("total", "sent", "failed", "removed")}}, ensure_ascii=False), autopush.LOG_KEEP)
        except Exception:
            pass
        bust()
        return JSONResponse({"ok": True, "payload": payload, **{k: r[k] for k in ("total", "sent", "failed", "removed")}}, headers=HDR)


async def admin_card() -> str:
    """The entry card on /stats (admin.page's `extra` slot): a big New post button + the last few posts."""
    e = lambda v: html.escape(str(v or ""), quote=True)
    try:
        rows = await store().list(drafts=True, limit=3)
        posts = [public(r) for r in rows]
        lst = "".join(f'<li style="margin:6px 0"><a href="/stats/posts?edit={e(p["id"])}">{e(p["headline"])}</a> <small style="display:block;color:#555">{e(p["category_label"])}'
                      f'{" · draft" if p["status"] == "draft" else ""}{" · sponsored" if p.get("sponsored") else ""}{" · pinned" if p["pinned"] else ""}</small></li>' for p in posts)
    except Exception:
        lst = ""
    warn = "" if store().durable else '<p class="sub"><b>Heads up:</b> posts are in temporary storage until SUPABASE_URL and SUPABASE_SERVICE_KEY are set on Render.</p>'
    return (f'<section class="card" id="op-entry" aria-labelledby="op-entry-h" style="border-top-color:#00C9CD"><h2 id="op-entry-h">✍️ Post your own chisme</h2>'
            '<p class="sub" style="margin:0 0 4px">News, weather, events, anything. It shows in the Chisme feed with a “From Chisme” badge.</p>'
            f'{warn}<a class="big go" href="/stats/posts" style="text-decoration:none">✍️ New post</a>'
            + (f'<ul class="op-recent" style="list-style:none;margin:10px 0 0;padding:0">{lst}</ul><p class="sub"><a href="/stats/posts#op-mine">All your posts</a></p>' if lst else "")
            + "</section>")
