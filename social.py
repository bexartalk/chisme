"""Chisme social, part 1: accounts, Homies and Chismes. Kept out of app.py (app.py only calls social.install(app, ...)).

Accounts: Supabase Auth checks every password and sends the 6-digit email codes (social_auth.py); Chisme keeps only its
own random session ids (hashed). Data: Supabase Postgres (RLS on every table) or SQLite for dev/tests (social_store.py).
Photos: resized to WebP with EXIF/GPS stripped (ownerposts.process_photo), stored on R2 / Supabase Storage / local,
held in a private quarantine until a CSAM scan says clean when CSAM_SCAN_URL is set. Everything is documented in
SOCIAL.md. Words: a "Chisme" (never a post), "Homies" (never followers / following)."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import html
import io
import json
import math
import os
import re
import secrets
import time
import unicodedata
import urllib.parse
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

import namefilter
import ownerposts as OP
import social_auth as SA
import social_store as S
from limits import SharedLimit, client_ip

CT = ZoneInfo("America/Chicago")
MIN_AGE = 18
MAX_PHOTOS = 4
MAX_TEXT, MAX_COMMENT, MAX_BIO, MAX_NAME = 2000, 500, 160, 40
SESSION_DAYS = 30
NEW_ACCOUNT_H = 72          # stricter limits, no links
FRESH_DAYS = 14             # trending boost
AUTO_HIDE = int(os.environ.get("SOCIAL_AUTO_HIDE_REPORTS", "3") or 3)
COOKIE, DEVICE, U18 = "chisme_s", "chisme_d", "chisme_u18"
REACTIONS = {"like": "❤️", "laugh": "😂", "wow": "😮", "chile": "🌶️"}
ACCENTS = {"turquoise": "#00C9CD", "pink": "#FF1A7F", "orange": "#FF6A0B", "purple": "#8A3FFC", "silver": "#A7A9AC", "black": "#111111"}
MAX_VIDEO_S, MAX_VIDEO_EDGE = 60, 720
AUDIENCES = ("everyone", "homies", "me")
REASONS = {"copyright": "Copyright (it's my work)", "spam": "Spam", "harassment": "Harassment or bullying", "hate": "Hate", "nudity": "Nudity or sexual content",
           "violence": "Violence or threats", "minor": "Someone under 18", "scam": "Scam or fake account", "other": "Something else"}
AREAS = ["Downtown", "Southside", "Westside", "Eastside", "Northside", "Northwest Side", "Northeast Side", "Medical Center",
         "Alamo Heights", "Stone Oak", "Pearl / Tobin Hill", "Southtown / King William", "Leon Valley", "Helotes", "Converse",
         "Live Oak", "Universal City", "Schertz", "Boerne", "New Braunfels", "Somewhere else in SA"]
PRIVACY_DEFAULT = {"area": "homies", "homies_list": "homies", "requests": "everyone", "suggest": True, "default_audience": "everyone"}
PRIVACY_CHOICES = {"area": ("everyone", "homies", "nobody"), "homies_list": ("everyone", "homies", "me"),
                   "requests": ("everyone", "mutuals"), "default_audience": AUDIENCES}
RESERVED = {"chisme", "chismeapp", "admin", "administrator", "support", "help", "moderator", "mod", "mods", "staff", "official",
            "tia", "tiachismosa", "root", "system", "null", "undefined", "api", "stats", "settings", "me", "homies", "everyone",
            "goonie", "security", "privacy", "terms", "news", "about"}
COMMON_PW = {"password", "password1", "12345678", "123456789", "1234567890", "qwertyui", "qwerty123", "iloveyou", "chisme123",
             "11111111", "00000000", "abcdefgh", "abc12345", "sanantonio", "spurs123", "letmein1", "welcome1"}
USER_RX = re.compile(r"^[a-z0-9_]{3,20}$")
UUID_RX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
EMAIL_RX = re.compile(r"^[^@\s<>\"'(),;:\\]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
TAG_RX = re.compile(r"(?<![\w#])#([^\W_][\w]{0,39})", re.U)
MENTION_RX = re.compile(r"(?<![\w@])@([A-Za-z0-9_]{3,20})\b")
LINK_RX = re.compile(r"(?i)\b(?:https?://|www\.)\S+|\b[a-z0-9-]{2,}\.(?:com|net|org|io|co|ly|gg|me|xyz|app|link|info|biz|ru|tk|top|shop|site|online)(?:/\S*)?\b")
HDR = {"Cache-Control": "no-store", "Referrer-Policy": "same-origin"}
BOT_COPY = "Prove you ain't a bot, cuh 🤖"


# ---------------------------------------------------------------- config + small helpers
def _env(n: str) -> str:
    return S._env(n)


def _secret() -> bytes:
    s = _env("SOCIAL_SECRET") or _env("ADMIN_TOKEN") or _env("STATS_SALT") or "chisme-dev-only-secret"
    return hashlib.sha256(("chisme-social:" + s).encode()).digest()


def hm(kind: str, v: str) -> str:
    return hmac.new(_secret(), f"{kind}:{v}".encode(), hashlib.sha256).hexdigest()[:40]


def turnstile() -> tuple[str, str]:
    site, sec = _env("TURNSTILE_SITE_KEY"), _env("TURNSTILE_SECRET_KEY")
    return (site, sec) if site and sec else ("", "")


def providers() -> list[str]:
    url, key = S.supabase_conf()
    if not (url and key):
        return []
    return [p for p, flag in (("apple", "SOCIAL_APPLE"), ("google", "SOCIAL_GOOGLE")) if _env(flag) == "1"]


def csp_script_extra() -> str:
    """Added to the page's script-src only when Turnstile is configured (its widget script)."""
    return " https://challenges.cloudflare.com" if turnstile()[0] else ""


def now() -> float:
    return time.time()


def new_id() -> str:
    return str(uuid.uuid4())


def clean_line(v, n: int) -> str:
    return OP.clean_line(v, n)


def clean_text(v, n: int) -> str:
    return OP.clean_text(v, n)


def normalize_email(e: str) -> str:
    e = unicodedata.normalize("NFKC", str(e or "")).strip().lower()
    if not EMAIL_RX.match(e):
        return ""
    local, dom = e.rsplit("@", 1)
    local = local.split("+", 1)[0]
    if dom in ("gmail.com", "googlemail.com"):
        local, dom = local.replace(".", ""), "gmail.com"
    return f"{local}@{dom}" if local else ""


def mask_email(e: str) -> str:
    local, _, dom = str(e or "").partition("@")
    return (local[:1] + "•••@" + dom) if local and dom else ""


def mask_phone(p: str | None) -> str:
    return ("•••-•••-" + p[-4:]) if p and len(p) >= 4 else ""


def clean_phone(v) -> str | None:
    s = re.sub(r"[\s().-]", "", str(v or ""))
    if not s:
        return None
    if not re.fullmatch(r"\+?\d{7,15}", s):
        raise ValueError("That phone number doesn't look right. Use digits, like 210-555-0123.")
    if re.fullmatch(r"\d{10}", s):
        s = "+1" + s
    elif re.fullmatch(r"1\d{10}", s):
        s = "+" + s
    return s


def age_on(bday: date, today: date) -> int:
    return today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))


# The Terms / Privacy Policy versions a new account agrees to (saved with the time in social_private + social_consents).
# Each version is the "Effective date" of that page's text in legal/*.md (social_test checks they match); bump it with
# the text. Env TERMS_VERSION / PRIVACY_VERSION / RULES_VERSION override.
TERMS_VERSION = os.environ.get("TERMS_VERSION", "").strip() or "2026-10-12"
PRIVACY_VERSION = os.environ.get("PRIVACY_VERSION", "").strip() or "2026-10-12"
RULES_VERSION = os.environ.get("RULES_VERSION", "").strip() or "2026-10-12"


def parse_birthday(v) -> date:
    try:
        d = date.fromisoformat(str(v or "").strip())
    except ValueError:
        raise ValueError("Add your birthday.")
    today = datetime.now(CT).date()
    if d > today or age_on(d, today) > 120:
        raise ValueError("That birthday doesn't look right.")
    return d


def clean_username(v) -> str:
    return str(v or "").strip().lstrip("@").lower()


def username_problem(u: str) -> str:
    if not USER_RX.match(u):
        return "Your @username needs 3–20 letters, numbers or underscores."
    if u in RESERVED or namefilter.blocked(u):
        return "That @username isn't available. Try another one."
    return ""


def password_problem(pw: str, pw2: str, email: str = "", username: str = "") -> str:
    if len(pw) < 8:
        return "Your password needs at least 8 characters."
    if len(pw.encode()) > 72:
        return "That password is too long (72 characters max)."
    if pw != pw2:
        return "The passwords don't match."
    low = pw.lower()
    if low in COMMON_PW or len(set(low)) < 4:
        return "That password is too easy to guess. Mix it up, cuh."
    local = email.split("@")[0].lower()
    if (len(local) >= 4 and local in low) or (username and len(username) >= 4 and username in low):
        return "Don't use your email or @username in your password."
    return ""


def spam_problem(text: str, age_h: float, recent: list[str]) -> str:
    links = LINK_RX.findall(text or "")
    if links and age_h < NEW_ACCOUNT_H:
        return "New accounts can't share links yet. Give it a few days. 🙏"
    if len(links) > 2:
        return "That's too many links for one Chisme."
    if re.search(r"(.)\1{14,}", text or ""):
        return "That's a whole lot of the same letter, cuh."
    words = re.findall(r"\w+", (text or "").lower())
    if len(words) >= 10 and len(set(words)) / len(words) < 0.3:
        return "That reads like spam. Try saying it a different way."
    if len(MENTION_RX.findall(text or "")) > 10:
        return "That's a lot of @mentions. Ten max."
    norm = re.sub(r"\W+", " ", (text or "").lower()).strip()
    if norm and len(norm) > 3 and norm in {re.sub(r"\W+", " ", t.lower()).strip() for t in recent}:
        return "You already said that one. 👀"
    return ""


def hashtags_of(text: str) -> list[str]:
    out: list[str] = []
    for t in TAG_RX.findall(text or ""):
        t = t.lower()
        if t not in out:
            out.append(t)
    return out[:10]


class Bad(Exception):
    def __init__(self, msg: str, status: int = 400, **extra):
        super().__init__(msg)
        self.msg, self.status, self.extra = msg, status, extra


# ---------------------------------------------------------------- rate limits (Upstash when set, else memory)
L = {
    "signup_ip": SharedLimit("soc-signup-ip", 5, 3600), "signup_day": SharedLimit("soc-signup-day", 3, 86400),
    "signup_dev": SharedLimit("soc-signup-dev", 2, 86400),
    "login_ip": SharedLimit("soc-login-ip", 10, 900), "login_email": SharedLimit("soc-login-email", 6, 900),
    "verify": SharedLimit("soc-verify", 8, 900), "forgot": SharedLimit("soc-forgot", 4, 3600),
    "chisme": SharedLimit("soc-chisme", 10, 3600), "chisme_new": SharedLimit("soc-chisme-new", 3, 3600),
    "chisme_day": SharedLimit("soc-chisme-day", 30, 86400), "chisme_day_new": SharedLimit("soc-chisme-day-new", 8, 86400),
    "comment": SharedLimit("soc-comment", 30, 3600), "comment_new": SharedLimit("soc-comment-new", 10, 3600),
    "homie": SharedLimit("soc-homie", 30, 86400), "homie_new": SharedLimit("soc-homie-new", 10, 86400),
    "upload": SharedLimit("soc-upload", 40, 3600), "report": SharedLimit("soc-report", 20, 86400),
    "react": SharedLimit("soc-react", 300, 3600), "account": SharedLimit("soc-account", 10, 3600),
}
_login_fails: dict[str, list[float]] = {}


async def limit(name: str, key: str, msg: str = "Slow down a little, cuh. Try again in a bit.") -> None:
    ok, wait = await L[name].hit(key)
    if not ok:
        mins = max(1, round(wait / 60))
        raise Bad(f"{msg} (about {mins} min)", 429)


def fails(key: str, add: bool = False) -> int:
    t = now()
    q = [x for x in _login_fails.get(key, []) if t - x < 900]
    if add:
        q.append(t)
    _login_fails[key] = q
    if len(_login_fails) > 20000:
        _login_fails.clear()
    return len(q)


# ---------------------------------------------------------------- bot check: Turnstile, or a signed challenge + honeypot
_used_nonces: dict[str, float] = {}


def make_challenge() -> dict:
    a, b = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
    nonce = secrets.token_urlsafe(12)
    t = int(now())
    sig = hm("chal", f"{nonce}|{t}|{a + b}")
    return {"id": f"{nonce}.{t}.{sig}", "question": f"What's {a} + {b}?"}


def challenge_ok(cid: str, answer) -> bool:
    try:
        nonce, t, sig = str(cid or "").split(".")
        t = int(t)
    except ValueError:
        return False
    age = now() - t
    if age < 2 or age > 900 or nonce in _used_nonces:   # under 2 s: no person fills a sign-up form that fast
        return False
    ans = re.sub(r"\D", "", str(answer or ""))[:3]
    if not ans or not hmac.compare_digest(sig, hm("chal", f"{nonce}|{t}|{int(ans)}")):
        return False
    _used_nonces[nonce] = now()
    if len(_used_nonces) > 50000:
        for k in [k for k, v in _used_nonces.items() if now() - v > 900]:
            _used_nonces.pop(k, None)
    return True


async def bot_check(request: Request, b: dict, client: httpx.AsyncClient | None = None) -> None:
    if str(b.get("website") or "").strip():          # the honeypot: a field people never see
        raise Bad("Something went wrong. Reload and try again.", 400, bot=True)
    site, sec = turnstile()
    if site:
        tok = str(b.get("turnstile") or "")
        if not tok or len(tok) > 4096:
            raise Bad(BOT_COPY + " Finish the check first.", 400, bot=True)
        own = client is None
        c = client or httpx.AsyncClient(timeout=10)
        try:
            r = await c.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                             data={"secret": sec, "response": tok, "remoteip": client_ip(request)})
            okk = bool(r.json().get("success"))
        except Exception:
            okk = False
        finally:
            if own:
                await c.aclose()
        if not okk:
            raise Bad(BOT_COPY + " That check didn't pass. Try it again.", 400, bot=True)
        return
    ch = b.get("challenge") if isinstance(b.get("challenge"), dict) else {}
    if not challenge_ok(ch.get("id"), ch.get("answer")):
        raise Bad(BOT_COPY + " That answer didn't check out. Try the new one.", 400, bot=True)


# ---------------------------------------------------------------- sessions
_sess_cache: dict[str, tuple[float, str]] = {}


def _https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").startswith("https")


async def start_session(resp: Response, request: Request, uid: str) -> None:
    sid = secrets.token_urlsafe(32)
    t = now()
    await S.db().insert("social_sessions", {"id_hash": hm("sess", sid), "user_id": uid, "created_at": S.now_iso(t),
                                            "expires_at": S.now_iso(t + SESSION_DAYS * 86400),
                                            "ua": clean_line(request.headers.get("user-agent"), 80) or None})
    resp.set_cookie(COOKIE, sid, max_age=SESSION_DAYS * 86400, path="/", httponly=True, secure=_https(request), samesite="lax")


async def end_sessions(uid: str, keep: str | None = None) -> None:
    f = [("user_id", "eq", uid)] + ([("id_hash", "neq", keep)] if keep else [])
    await S.db().delete("social_sessions", f)
    for k in [k for k, v in _sess_cache.items() if v[1] == uid and k != keep]:
        _sess_cache.pop(k, None)


def clear_cookie(resp: Response, request: Request) -> None:
    resp.delete_cookie(COOKIE, path="/", secure=_https(request), httponly=True, samesite="lax")


async def session_uid(request: Request) -> str | None:
    sid = request.cookies.get(COOKIE) or ""
    if not (20 <= len(sid) <= 100):
        return None
    h = hm("sess", sid)
    c = _sess_cache.get(h)
    if c and c[0] > now():
        return c[1]
    rows = await S.db().select("social_sessions", [("id_hash", "eq", h)], limit=1)
    if not rows or S.ts_of(rows[0]["expires_at"]) < now():
        if rows:
            await S.db().delete("social_sessions", [("id_hash", "eq", h)])
        return None
    _sess_cache[h] = (now() + 60, rows[0]["user_id"])
    if len(_sess_cache) > 5000:
        _sess_cache.clear()
    return rows[0]["user_id"]


# ---------------------------------------------------------------- the viewer + relationships
async def profile_by(uid: str | None = None, username: str | None = None) -> dict | None:
    if uid:
        rows = await S.db().select("social_profiles", [("id", "eq", uid)], limit=1)
    elif username and USER_RX.match(username):
        rows = await S.db().select("social_profiles", [("username", "eq", username)], limit=1)
    else:
        return None
    return rows[0] if rows else None


def live(p: dict | None) -> bool:
    return bool(p and p.get("verified") and p.get("status") == "active")


def privacy_of(p: dict) -> dict:
    out = dict(PRIVACY_DEFAULT)
    for k, v in (p.get("privacy") or {}).items():
        if k in PRIVACY_CHOICES and v in PRIVACY_CHOICES[k]:
            out[k] = v
        elif k == "suggest" and isinstance(v, bool):
            out[k] = v
    return out


def age_hours(p: dict) -> float:
    return (now() - S.ts_of(p.get("created_at"))) / 3600


class Viewer:
    """Who's looking (None = signed out), with their Homies / blocks / NAHs loaded once per request."""

    def __init__(self, me: dict | None):
        self.me = me
        self.id = me["id"] if me else None
        self._homies: set | None = None
        self._blocked: set | None = None
        self._nah: set | None = None

    async def homies(self) -> set:
        if self._homies is None:
            self._homies = await homie_ids(self.id) if self.id else set()
        return self._homies

    async def blocked(self) -> set:
        """Both ways: people I blocked and people who blocked me."""
        if self._blocked is None:
            if not self.id:
                self._blocked = set()
            else:
                a = await S.db().select("social_blocks", [("blocker_id", "eq", self.id)], cols=["blocked_id"], limit=5000)
                b = await S.db().select("social_blocks", [("blocked_id", "eq", self.id)], cols=["blocker_id"], limit=5000)
                self._blocked = {r["blocked_id"] for r in a} | {r["blocker_id"] for r in b}
        return self._blocked

    async def nahs(self) -> set:
        if self._nah is None:
            rows = await S.db().select("social_nahs", [("user_id", "eq", self.id)], cols=["target_id"], limit=5000) if self.id else []
            self._nah = {r["target_id"] for r in rows}
        return self._nah


async def viewer(request: Request) -> Viewer:
    uid = await session_uid(request)
    me = await profile_by(uid=uid) if uid else None
    return Viewer(me if live(me) else None)


async def homie_ids(uid: str) -> set:
    a = await S.db().select("social_homies", [("a", "eq", uid)], cols=["b"], limit=5000)
    b = await S.db().select("social_homies", [("b", "eq", uid)], cols=["a"], limit=5000)
    return {r["b"] for r in a} | {r["a"] for r in b}


def pair(x: str, y: str) -> tuple[str, str]:
    return (x, y) if x < y else (y, x)


async def is_blocked_between(x: str, y: str) -> bool:
    a = await S.db().count("social_blocks", [("blocker_id", "eq", x), ("blocked_id", "eq", y)])
    b = await S.db().count("social_blocks", [("blocker_id", "eq", y), ("blocked_id", "eq", x)])
    return bool(a or b)


async def relation(v: Viewer, p: dict) -> str:
    """me | homies | requested (I asked; stays this way even after a private NAH) | incoming | none"""
    if not v.id:
        return "none"
    if p["id"] == v.id:
        return "me"
    if p["id"] in await v.homies():
        return "homies"
    if await S.db().count("social_homie_requests", [("from_id", "eq", v.id), ("to_id", "eq", p["id"])]):
        return "requested"
    if await S.db().count("social_homie_requests", [("from_id", "eq", p["id"]), ("to_id", "eq", v.id)]):
        return "incoming"
    return "none"


# ---------------------------------------------------------------- shapes (what the API shows: never email / phone / birthday)
def photo_url(name: str | None) -> str | None:
    return S.media().url(name) if name and S.NAME_RX.match(name) else None


def mini(p: dict) -> dict:
    return {"username": p["username"], "name": p["display_name"], "photo": photo_url(p.get("photo")),
            "accent": p.get("accent") if p.get("accent") in ACCENTS else "turquoise", "fresh": age_hours(p) < FRESH_DAYS * 24}


def allowed(level: str, rel: str) -> bool:
    return rel == "me" or level == "everyone" or (level == "homies" and rel == "homies")


async def profile_view(v: Viewer, p: dict) -> dict:
    rel = await relation(v, p)
    pv = privacy_of(p)
    their = await homie_ids(p["id"])
    mutual = len(their & (await v.homies())) if v.id and rel != "me" else 0
    out = {**mini(p), "bio": p.get("bio") or "", "relation": rel, "homies": len(their), "mutual_homies": mutual,
           "area": p.get("area") if p.get("area") and allowed({"nobody": "me"}.get(pv["area"], pv["area"]), rel) else None,
           "homies_list_visible": allowed(pv["homies_list"], rel), "joined": (p.get("created_at") or "")[:7],
           "under_review": bool(p.get("flagged")) and rel == "me", "banner": photo_url(p.get("banner")),
           "accent_hex": ACCENTS.get(p.get("accent") or "", ACCENTS["turquoise"]), "pinned_id": p.get("pinned_id")}
    if rel == "me":
        out["privacy"] = pv
    return out


def can_see(v: Viewer, c: dict, homies: set, blocked: set) -> bool:
    if c["author_id"] == v.id:
        return c["status"] != "removed"
    if c["status"] != "visible" or c["author_id"] in blocked:
        return False
    if c["audience"] == "everyone":
        return True
    if c["audience"] == "homies":
        return bool(v.id) and c["author_id"] in homies
    return False


async def shape_chismes(v: Viewer, rows: list[dict], check: bool = True) -> list[dict]:
    """Rows → what phones get. Drops anything this viewer may not see (audience, blocks, banned / unverified authors)."""
    homies, blocked = await v.homies(), await v.blocked()
    if check:
        rows = [c for c in rows if can_see(v, c, homies, blocked)]
    if not rows:
        return []
    db = S.db()
    ids = [c["id"] for c in rows]
    authors = {p["id"]: p for p in await db.select("social_profiles", [("id", "in", list({c["author_id"] for c in rows}))])}
    rows = [c for c in rows if live(authors.get(c["author_id"])) or c["author_id"] == v.id]
    reacts = await db.select("social_reactions", [("chisme_id", "in", ids)], cols=["chisme_id", "user_id", "kind"], limit=20000)
    comments = await db.select("social_comments", [("chisme_id", "in", ids), ("status", "eq", "visible")], cols=["chisme_id", "author_id"], limit=20000)
    saved = {r["chisme_id"] for r in await db.select("social_saves", [("user_id", "eq", v.id), ("chisme_id", "in", ids)], cols=["chisme_id"])} if v.id else set()
    tag_ids = list({t for c in rows for t in (c.get("tags") or []) if isinstance(t, str) and UUID_RX.match(t)})
    tagged = {p["id"]: p for p in await db.select("social_profiles", [("id", "in", tag_ids)])} if tag_ids else {}
    out = []
    for c in rows:
        a = authors.get(c["author_id"])
        if not a:
            continue
        counts = {k: 0 for k in REACTIONS}
        mine = {k: False for k in REACTIONS}
        for r in reacts:
            if r["chisme_id"] == c["id"] and r["user_id"] not in blocked and r["kind"] in counts:
                counts[r["kind"]] += 1
                if r["user_id"] == v.id:
                    mine[r["kind"]] = True
        ncom = sum(1 for x in comments if x["chisme_id"] == c["id"] and x["author_id"] not in blocked)
        out.append({
            "id": c["id"], "author": mini(a), "text": c.get("text") or "",
            "photos": [{"url": photo_url(ph.get("name")), "w": ph.get("w"), "h": ph.get("h")} for ph in c.get("photos") or []
                       if isinstance(ph, dict) and photo_url(ph.get("name"))],
            "videos": [{"url": photo_url(vd.get("name")), "poster": photo_url(vd.get("poster")), "w": vd.get("w"), "h": vd.get("h"),
                        "seconds": vd.get("seconds")} for vd in c.get("videos") or [] if isinstance(vd, dict) and photo_url(vd.get("name"))],
            "clip": clip_view(c.get("clip")), "meme": bool(c.get("meme")),
            "audience": c["audience"], "hashtags": c.get("hashtags") or [], "created_at": c["created_at"],
            "tags": [mini(tagged[t]) for t in c.get("tags") or [] if t in tagged and live(tagged[t]) and t not in blocked],
            "counts": {**counts, "comments": ncom}, "mine": {**mine, "saved": c["id"] in saved},
            "own": c["author_id"] == v.id, "hidden": c["status"] != "visible",
            "share_url": "/c/" + c["id"] if c["audience"] == "everyone" and c["status"] == "visible" else None,
        })
    return out


def clip_view(clip) -> dict | None:
    """A reposted ChismeTV clip: only YouTube (11-char id) or TikTok (numeric id); the player URL is built here, never stored."""
    if not isinstance(clip, dict):
        return None
    cid = str(clip.get("id") or "")
    if re.fullmatch(r"[\w-]{11}", cid) and not cid.isdigit():
        thumb, embed = f"https://i.ytimg.com/vi/{cid}/hqdefault.jpg", f"https://www.youtube-nocookie.com/embed/{cid}?playsinline=1"
    elif re.fullmatch(r"\d{15,20}", cid):
        thumb, embed = None, f"https://www.tiktok.com/player/v1/{cid}"
    else:
        return None
    return {"id": cid, "title": clean_line(clip.get("title"), 120), "creator": clean_line(clip.get("creator"), 60),
            "thumb": thumb, "embed": embed, "link": "/?reel=" + cid}


async def chisme_for(v: Viewer, cid: str) -> dict | None:
    """The raw row, only if this viewer may see it."""
    if not UUID_RX.match(cid or ""):
        return None
    rows = await S.db().select("social_chismes", [("id", "eq", cid)], limit=1)
    if not rows:
        return None
    c = rows[0]
    if not can_see(v, c, await v.homies(), await v.blocked()):
        return None
    a = await profile_by(uid=c["author_id"])
    if not (live(a) or c["author_id"] == v.id):
        return None
    return c


async def notify(user_id: str, actor_id: str, kind: str, chisme_id: str | None = None, once: bool = False) -> None:
    if user_id == actor_id or await is_blocked_between(user_id, actor_id):
        return
    if once:
        f = [("user_id", "eq", user_id), ("actor_id", "eq", actor_id), ("kind", "eq", kind)]
        f += [("chisme_id", "eq", chisme_id)] if chisme_id else [("chisme_id", "isnull", None)]
        if await S.db().count("social_notifications", f):
            return
    await S.db().insert("social_notifications", {"id": new_id(), "user_id": user_id, "actor_id": actor_id, "kind": kind,
                                                 "chisme_id": chisme_id, "read": False, "created_at": S.now_iso()})


def install(app: FastAPI, **kw) -> None:
    """app.py: social.install(app, owner=..., public_base=..., reel_lookup=..., reel_id=...). Routes: social_api.py."""
    import social_api
    social_api.install(app, **kw)
