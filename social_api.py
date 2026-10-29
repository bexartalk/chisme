"""Chisme social, part 1: the HTTP routes (social.install(app, ...) calls install() here). The rules and shapes live in
social.py, storage in social_store.py, Supabase Auth in social_auth.py.

Pages: /social (the app: feeds, ➕ CHISME, profiles, Homies, settings, the moderation queue for the owner), /c/<id> (a
public Chisme's share page), /dmca (the copyright takedown form). APIs: /api/social/*. Every write is same-origin + JSON
(uploads: the raw file body) and rate limited; nothing ever answers with an email or phone, and a birthday is checked (18+) but never stored."""
from __future__ import annotations

import asyncio
import hashlib
import html
import inspect
import json
import re
import secrets
import shutil
import subprocess
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

import ownerposts as OP
import social as X
import social_auth as SA
import social_store as S
from limits import client_ip

BASE = Path(__file__).parent
MAX_PHOTO_BODY = 8 * 1024 * 1024        # the phone already shrank it (<= 2048 px JPEG); this is the hard cap
MAX_VIDEO_BODY = 40 * 1024 * 1024       # ~60 s of 720p after the phone's own squeeze; the server re-encodes anyway
FEEDS = ("homies", "sananto", "trending", "memes")
SA_TAGS = {"sanantonio", "sanantone", "satx", "sananto", "210", "spurs", "fiesta", "alamo", "riverwalk", "southside", "westside",
           "eastside", "northside", "pearl"}


def media_name(prefix: str, ext: str = "webp") -> str:
    return f"{prefix}/{datetime.now(X.CT).strftime('%Y%m')}/{secrets.token_urlsafe(9)}.{ext}"


def ok(d: dict | None = None, status: int = 200) -> JSONResponse:
    return JSONResponse({"ok": True, **(d or {})}, status_code=status, headers=X.HDR)


def bad(msg: str, status: int = 400, **extra) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg, **extra}, status_code=status, headers=X.HDR)


async def body_of(request: Request, cap: int = 20000) -> dict:
    if "application/json" not in (request.headers.get("content-type") or ""):
        raise X.Bad("Send JSON.", 415)
    raw = await request.body()
    if len(raw) > cap:
        raise X.Bad("That's too much at once.", 413)
    try:
        d = json.loads(raw or b"{}")
    except Exception:
        raise X.Bad("That didn't come through right. Try again.")
    if not isinstance(d, dict):
        raise X.Bad("That didn't come through right. Try again.")
    return d


async def me_or_401(request: Request) -> X.Viewer:
    v = await X.viewer(request)
    if not v.id:
        raise X.Bad("Sign in first.", 401)
    return v


def guard(request: Request) -> None:
    if not OP.same_origin(request):
        raise X.Bad("cross-site request refused", 403)


# ---------------------------------------------------------------- video: probe, re-encode to <= 720p / 60 s, no metadata
class VideoError(ValueError):
    pass


def _probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, timeout=30)
    if r.returncode != 0:
        raise VideoError("That file isn't a video Chisme can read.")
    return json.loads(r.stdout or b"{}")


def sniff_video(raw: bytes) -> str | None:
    if len(raw) > 12 and raw[4:8] == b"ftyp":
        return "mp4"   # mp4 / mov / m4v
    if raw[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def process_video(raw: bytes) -> tuple[bytes, bytes, dict]:
    """-> (mp4, poster webp, {w, h, seconds}). Checks the container and the length (60 s max), then re-encodes to
    H.264/AAC <= 720p with every metadata tag, chapter and data track dropped (no GPS / camera / date survive)."""
    if not shutil.which("ffmpeg"):
        raise VideoError("Videos aren't turned on on this server yet.")
    if len(raw) > MAX_VIDEO_BODY:
        raise VideoError("That video is too big (40 MB max). Try a shorter one.")
    if not sniff_video(raw):
        raise VideoError("Videos must be MP4, MOV or WebM.")
    with tempfile.TemporaryDirectory() as d:
        src, out, poster = f"{d}/in", f"{d}/out.mp4", f"{d}/poster.png"
        Path(src).write_bytes(raw)
        info = _probe(src)
        vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        if not vs:
            raise VideoError("That file has no video in it.")
        try:
            dur = float((info.get("format") or {}).get("duration") or vs[0].get("duration") or 0)
        except ValueError:
            dur = 0
        if dur <= 0.3:
            raise VideoError("That video is too short.")
        if dur > X.MAX_VIDEO_S + 0.5:
            raise VideoError(f"Videos can be {X.MAX_VIDEO_S} seconds max. Trim it and try again.")
        e = X.MAX_VIDEO_EDGE
        vf = f"scale='if(gt(iw,ih),-2,min({e},iw))':'if(gt(iw,ih),min({e},ih),-2)',format=yuv420p"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1",
               "-map_chapters", "-1", "-dn", "-sn", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
               "-maxrate", "2M", "-bufsize", "4M", "-r", "30", "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-t", str(X.MAX_VIDEO_S),
               "-movflags", "+faststart", out]
        r = subprocess.run(cmd, capture_output=True, timeout=240)
        if r.returncode != 0 or not Path(out).is_file():
            raise VideoError("Chisme couldn't read that video. Try another one.")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(min(1.0, dur / 2)), "-i", out, "-frames:v", "1", poster],
                       capture_output=True, timeout=60)
        o = _probe(out)
        ov = [s for s in o.get("streams", []) if s.get("codec_type") == "video"][0]
        data = Path(out).read_bytes()
        if len(data) > 25 * 1024 * 1024:
            raise VideoError("That video is still too big after shrinking it. Try a shorter one.")
        pb = Path(poster).read_bytes() if Path(poster).is_file() else b""
        pw = OP.process_photo(pb, 960)[0] if pb else b""
        return data, pw, {"w": int(ov.get("width") or 0), "h": int(ov.get("height") or 0), "seconds": round(min(dur, X.MAX_VIDEO_S), 1)}


def video_frames(mp4: bytes, n: int = 3) -> list[bytes]:
    """A few frames (start, middle, end) as WebP, for the CSAM scan hook."""
    out = []
    with tempfile.TemporaryDirectory() as d:
        Path(f"{d}/v.mp4").write_bytes(mp4)
        try:
            dur = float((_probe(f"{d}/v.mp4").get("format") or {}).get("duration") or 1)
        except Exception:
            dur = 1
        for i in range(n):
            t = dur * (i + 0.5) / n
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", f"{d}/v.mp4", "-frames:v", "1", f"{d}/{i}.png"],
                           capture_output=True, timeout=60)
            p = Path(f"{d}/{i}.png")
            if p.is_file():
                try:
                    out.append(OP.process_photo(p.read_bytes(), 960)[0])
                except Exception:
                    pass
    return out


# ---------------------------------------------------------------- feeds
def heat(c: dict, reacts: list[dict], comments: list[dict], fresh_author: bool) -> float:
    w = {"chile": 2.0, "laugh": 1.5, "like": 1.0, "wow": 1.0}
    pts = sum(w.get(r["kind"], 1) for r in reacts if r["chisme_id"] == c["id"]) + 2 * sum(1 for x in comments if x["chisme_id"] == c["id"])
    age_h = max(0.0, (X.now() - S.ts_of(c["created_at"])) / 3600)
    boost = 1.6 if fresh_author else 1.0          # small + new accounts get a fair shot at Trending
    return (pts + 1) * boost / ((age_h + 2) ** 1.4)


async def feed_rows(v: X.Viewer, tab: str, before: str | None, n: int = 20) -> list[dict]:
    db = S.db()
    f = [("status", "eq", "visible")]
    if before:
        f.append(("created_at", "lt", before))
    if tab == "homies":
        if not v.id:
            return []
        ids = list(await v.homies()) + [v.id]
        return await db.select("social_chismes", f + [("author_id", "in", ids), ("audience", "in", ["everyone", "homies"])],
                               order=[("created_at", True)], limit=n * 2)
    if tab == "memes":
        return await db.select("social_chismes", f + [("meme", "eq", True), ("audience", "in", ["everyone", "homies"])],
                               order=[("created_at", True)], limit=n * 2)
    if tab == "sananto":
        rows = await db.select("social_chismes", f + [("audience", "eq", "everyone")], order=[("created_at", True)], limit=n * 3)
        authors = {p["id"]: p for p in await db.select("social_profiles", [("id", "in", list({c["author_id"] for c in rows}))])} if rows else {}

        def local(c):   # around SA: a SA hashtag, or the author volunteered a part of town
            return bool(set(c.get("hashtags") or []) & SA_TAGS) or bool((authors.get(c["author_id"]) or {}).get("area"))
        loc = [c for c in rows if local(c)]
        return (loc or rows)[: n * 2]
    since = S.now_iso(X.now() - 7 * 86400)    # trending: the last 7 days, scored
    rows = await db.select("social_chismes", [("status", "eq", "visible"), ("audience", "eq", "everyone"), ("created_at", "gt", since)],
                           order=[("created_at", True)], limit=400)
    if not rows:
        return []
    ids = [c["id"] for c in rows]
    reacts = await db.select("social_reactions", [("chisme_id", "in", ids)], cols=["chisme_id", "kind"], limit=50000)
    comments = await db.select("social_comments", [("chisme_id", "in", ids), ("status", "eq", "visible")], cols=["chisme_id"], limit=50000)
    authors = {p["id"]: p for p in await db.select("social_profiles", [("id", "in", list({c["author_id"] for c in rows}))])}
    fresh = lambda c: X.age_hours(authors.get(c["author_id"]) or {"created_at": c["created_at"]}) < X.FRESH_DAYS * 24
    rows.sort(key=lambda c: -heat(c, reacts, comments, fresh(c)))
    out, rest = [], list(rows)
    while rest and len(out) < 60:   # nobody takes over: never 3 in a row from the same person
        pick = next((c for c in rest if [x["author_id"] for x in out[-2:]] != [c["author_id"]] * 2), rest[0])
        rest.remove(pick)
        out.append(pick)
    return out


# ---------------------------------------------------------------- pages
def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#00C9CD"><title>{html.escape(title)}</title>
<link rel="icon" href="/static/icons/icon-192.png"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/social.css">
</head><body class="sx sx-plain"><header class="topbar sx-modbar"><div class="wrap"><a href="/" class="sx-modlink">‹ Chisme</a></div><div class="picado" aria-hidden="true"></div></header>{body}</body></html>"""


# Chisme's designated DMCA agent (U.S. Copyright Office registration DMCA-1082743). DMCA_AGENT_INFO overrides it.
import legal_contact as LC   # the one place the agent's name / address / phone / email live
DMCA_EMAIL = LC.EMAIL
DMCA_REG = LC.DMCA_REG
DMCA_NAME = LC.AGENT_NAME
DMCA_ADDRESS = LC.ADDRESS
DMCA_PHONE = LC.PHONE
DMCA_AGENT_DEFAULT = (f"Chisme's designated agent for copyright complaints is registered with the U.S. Copyright Office "
                      f"(registration {DMCA_REG}). Email copyright complaints to {DMCA_EMAIL}, or send a notice with this form.")


def dmca_page(done: str = "", err: str = "", f: dict | None = None) -> str:
    f = f or {}
    e = lambda k: html.escape(str(f.get(k) or ""), quote=True)
    agent = html.escape(X._env("DMCA_AGENT_INFO") or DMCA_AGENT_DEFAULT)
    agent = agent.replace(html.escape(DMCA_EMAIL), f'<a href="mailto:{DMCA_EMAIL}">{DMCA_EMAIL}</a>')
    # the agent's full contact, as on the Copyright Office registration; the registration's name / address / phone are the defaults; DMCA_AGENT_NAME / _ADDRESS / _PHONE override
    soon = '<i class="dmca-unset">Not listed here yet. Email the address below for now.</i>'
    row = lambda label, v: f"<dt>{label}</dt><dd>{html.escape(v).replace(chr(10), '<br>') if v else soon}</dd>"
    agent_card = (f'<section class="card dmca-agent" aria-labelledby="dmca-agent-h"><h2 id="dmca-agent-h">Designated copyright agent</h2><dl>'
                  + row("Name", (X._env("DMCA_AGENT_NAME").strip() or DMCA_NAME)) + row("Mailing address", (X._env("DMCA_AGENT_ADDRESS").strip() or DMCA_ADDRESS))
                  + row("Phone", (X._env("DMCA_AGENT_PHONE").strip() or DMCA_PHONE))
                  + f'<dt>Email</dt><dd><a href="mailto:{DMCA_EMAIL}">{DMCA_EMAIL}</a></dd>'
                  + f'<dt>Registration</dt><dd>{DMCA_REG} (U.S. Copyright Office)</dd></dl></section>')
    if done:
        inner = f'<div class="card ok-card"><h2>Got it ✅</h2><p>{html.escape(done)}</p><p><a href="/">Back to Chisme</a></p></div>'
    else:
        inner = f"""
<form class="card form" method="post" action="/dmca">
  {f'<p class="err" role="alert">{html.escape(err)}</p>' if err else ''}
  <label>Your full legal name<input name="claimant_name" required maxlength="120" value="{e('claimant_name')}" autocomplete="name"></label>
  <label>Your email (only Chisme's team sees it)<input name="claimant_email" type="email" required maxlength="254" value="{e('claimant_email')}" autocomplete="email"></label>
  <label>Your mailing address or phone<input name="claimant_address" maxlength="300" value="{e('claimant_address')}"></label>
  <label>The copyrighted work (what it is, and a link to the original if it's online)<textarea name="work" required maxlength="1000" rows="3">{e('work')}</textarea></label>
  <label>Where it is on Chisme (one link per line, like https://chisme.co/c/...)<textarea name="urls" required maxlength="2000" rows="3">{e('urls')}</textarea></label>
  <label>Anything else we should know<textarea name="statement" maxlength="2000" rows="2">{e('statement')}</textarea></label>
  <label class="chk"><input type="checkbox" name="good_faith" value="1" required> I believe in good faith that this use isn't allowed by the copyright owner, its agent, or the law.</label>
  <label class="chk"><input type="checkbox" name="accurate" value="1" required> This notice is accurate, and under penalty of perjury, I own the work or am allowed to act for the owner.</label>
  <label>Type your full name as your signature<input name="signature" required maxlength="120" value="{e('signature')}"></label>
  <input name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
  <button class="btn pink" type="submit">Send takedown notice</button>
</form>"""
    return page("Report copyright (DMCA) · Chisme", f"""
<main class="legal"><h1>Report copyright (DMCA)</h1>
<p>If someone shared your photo, video or other work on Chisme without permission, tell us here and we'll take it down.
We follow the Digital Millennium Copyright Act. Only send a notice for work you own or are allowed to act for; fake notices can get you in legal trouble.</p>
<p class="small">{agent}</p>
{agent_card}
<p class="small">Was something of yours taken down by mistake? Reply to the email we send you with a counter-notice: your name and address,
what was removed, a statement under penalty of perjury that it was removed by mistake, and your consent to your local federal court.
Accounts that get repeated valid notices are closed.</p>
{inner}</main>""")


def chisme_page(c: dict, base: str) -> str:
    who = c["author"]
    txt = c["text"] or ("A Chisme by @" + who["username"])
    img = (c["photos"][0]["url"] if c["photos"] else c["videos"][0]["poster"] if c["videos"] else (c["clip"] or {}).get("thumb")) or "/static/site/og-banner.png"
    img = img if img.startswith("http") else base + img
    e = lambda s: html.escape(str(s or ""), quote=True)
    media = "".join(f'<img src="{e(p["url"])}" alt="" width="{p["w"] or 600}" height="{p["h"] or 600}">' for p in c["photos"])
    media += "".join(f'<video src="{e(vd["url"])}" poster="{e(vd["poster"])}" controls playsinline preload="metadata"></video>' for vd in c["videos"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(who['name'])} on Chisme</title><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/social.css">
<meta property="og:title" content="{e(who['name'])} (@{e(who['username'])}) on Chisme"><meta property="og:description" content="{e(txt[:200])}">
<meta property="og:image" content="{e(img)}"><meta name="twitter:card" content="summary_large_image"></head>
<body class="sx sx-plain"><header class="topbar sx-modbar"><div class="wrap"><a href="/" class="sx-modlink">‹ Chisme</a></div><div class="picado" aria-hidden="true"></div></header><main class="share"><article class="chisme card"><header class="by"><b>{e(who['name'])}</b> <span>@{e(who['username'])}</span></header>
<p class="txt">{e(c['text'])}</p><div class="media">{media}</div></article>
<a class="btn pink" href="/#s/c/{e(c['id'])}">Open in Chisme 🌶️</a></main></body></html>"""


AUTH_MSG = {"rate_limited": "Too many tries. Give it a few minutes.", "bad_code": "That code didn't work. Check it or get a new one.",
            "weak_password": "That password is too weak. Make it longer.", "email_not_confirmed": "Confirm your email first.",
            "invalid": "That email or password doesn't match.", "unreachable": "Accounts are taking a nap. Try again in a minute."}


def wrap(fn):
    async def inner(*a, **k):
        try:
            return await fn(*a, **k)
        except X.Bad as ex:
            return bad(ex.msg, ex.status, **ex.extra)
        except SA.AuthError as ex:
            return bad(AUTH_MSG.get(ex.code, "Something went wrong with your account. Try again."), ex.status, code=ex.code)
        except (S.StorageError, OSError) as ex:
            print("social storage:", type(ex).__name__, str(ex)[:120])
            return bad("Chisme's storage is having a moment. Try again in a minute.", 503)
        except Exception:
            print("social error in", fn.__name__)
            traceback.print_exc()
            return bad("Chisme hit a snag on our end. Try again in a minute.", 500)
    inner.__name__ = fn.__name__
    inner.__signature__ = inspect.signature(fn)
    return inner


UPLOADS_SOON = "Photo and video uploads are coming soon 📸 Text Chismes work right now."


def can_upload(me: dict | None) -> bool:
    """UPLOADS_PUBLIC=1 opens photo + video uploads to everybody. Until a CSAM scanner is live it stays 0 (the default):
    only the usernames in SOCIAL_UPLOAD_TESTERS (comma list; put the owner's @username first) may upload."""
    if not me:
        return False
    if X._env("UPLOADS_PUBLIC") == "1":
        return True
    allow = {u.strip().lstrip("@").lower() for u in X._env("SOCIAL_UPLOAD_TESTERS").split(",") if u.strip()}
    return me.get("username", "").lower() in allow


def gotrue() -> SA.GoTrue:
    a = SA.auth()
    if not a:
        raise X.Bad("Accounts aren't turned on yet. Check back soon. 🙏", 503)
    return a


SIGNUPS_SOON = "Accounts are opening soon. Keep browsing the chisme! 👀"


def signups_public() -> bool:
    return X._env("SIGNUPS_PUBLIC") == "1"


def signup_allowed(email: str) -> bool:
    """SIGNUPS_PUBLIC=0 (the default, until chisme.co has a verified sending domain): only the emails in
    SOCIAL_SIGNUP_TESTERS (comma list, compared normalized) can make an account. Browsing and signing in stay open."""
    if signups_public():
        return True
    allow = {X.normalize_email(e.strip()) for e in X._env("SOCIAL_SIGNUP_TESTERS").split(",") if e.strip()}
    return bool(email) and email in allow


_IS_OWNER = None


async def release_held(filters: list) -> None:
    """Held Chismes go live, except ones that already have AUTO_HIDE+ reports: those stay hidden for the moderation queue."""
    db = S.db()
    await db.update("social_chismes", filters + [("status", "eq", "held"), ("report_count", "gte", X.AUTO_HIDE)], {"status": "hidden"})
    await db.update("social_chismes", filters + [("status", "eq", "held")], {"status": "visible"})


async def admin_ok(request: Request, write: bool = False) -> bool:
    """The owner's /stats sign-in, or the signed-in admin account (SOCIAL_OWNER_EMAIL). Checked on every admin call."""
    if _IS_OWNER and await _IS_OWNER(request, write):
        return True
    return (await X.viewer(request)).admin


def install(app: FastAPI, *, owner: Callable[..., Awaitable[bool]], public_base: Callable[[Request], str],
            reel_lookup: Callable[[str], dict | None] | None = None, reel_id: Callable[[str], str | None] | None = None) -> None:

    async def is_owner(request: Request, write: bool = False) -> bool:
        try:
            return bool(await owner(request, json_only=write))
        except Exception:
            return False

    global _IS_OWNER
    _IS_OWNER = is_owner

    # ------------------------------------------------ pages
    @app.get("/social", include_in_schema=False)
    async def social_page(request: Request):
        # the social app lives inside the main app now (index.html → Chisme feed); old links land there
        return RedirectResponse("/#s/feed/sananto", 302)

    @app.get("/stats/social", include_in_schema=False)
    async def mod_page(request: Request):
        if not await admin_ok(request):
            return RedirectResponse("/stats", 303)
        body = (BASE / "static" / "social.html").read_text().replace("{{TS_SCRIPT}}", "").replace('data-mode="app"', 'data-mode="mod"')
        return HTMLResponse(body, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})

    @app.get("/dmca", include_in_schema=False)
    async def dmca_get(request: Request):
        return HTMLResponse(dmca_page())

    @app.post("/dmca", include_in_schema=False)
    async def dmca_post(request: Request):
        if not OP.same_origin(request):
            return HTMLResponse(dmca_page(err="That came from another site. Use this page."), status_code=403)
        raw = await request.body()
        if len(raw) > 12000:
            return HTMLResponse(dmca_page(err="That's too long."), status_code=413)
        q = {k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}
        if q.get("website"):
            return HTMLResponse(dmca_page(err="Something went wrong. Reload and try again."), status_code=400)
        ok_, _w = await X.L["report"].hit("dmca:" + client_ip(request))
        if not ok_:
            return HTMLResponse(dmca_page(err="Too many notices from here today. Try again tomorrow.", f=q), status_code=429)
        row = {"id": X.new_id(), "claimant_name": X.clean_line(q.get("claimant_name"), 120), "claimant_email": X.clean_line(q.get("claimant_email"), 254),
               "claimant_address": X.clean_line(q.get("claimant_address"), 300), "work": X.clean_text(q.get("work"), 1000),
               "urls": X.clean_text(q.get("urls"), 2000), "statement": X.clean_text(q.get("statement"), 2000),
               "signature": X.clean_line(q.get("signature"), 120), "status": "open", "created_at": S.now_iso()}
        if len(row["claimant_name"]) < 2 or not X.EMAIL_RX.match(row["claimant_email"]) or len(row["work"]) < 3 or len(row["urls"]) < 3 \
                or len(row["signature"]) < 2 or q.get("good_faith") != "1" or q.get("accurate") != "1":
            return HTMLResponse(dmca_page(err="Fill in every required part, and check both statements.", f=q), status_code=400)
        await S.db().insert("social_dmca", row)
        for cid in list(set(re.findall(r"/c/([0-9a-f-]{36})", row["urls"])))[:20]:   # hidden right away until a person reviews it
            await S.db().update("social_chismes", [("id", "eq", cid), ("status", "eq", "visible")], {"status": "hidden"})
        return HTMLResponse(dmca_page(done="Your notice is in. The Chismes you listed are hidden while our team reviews it, and we'll email you."))

    @app.get("/c/{cid}", include_in_schema=False)
    @wrap
    async def share_page(request: Request, cid: str):
        v = X.Viewer(None)   # the public page shows only what anyone may see
        c = await X.chisme_for(v, cid)
        shaped = await X.shape_chismes(v, [c]) if c else []
        if not shaped:
            return HTMLResponse(page("Not here · Chisme", '<main class="share"><h1>That Chisme isn\'t here 👀</h1><a class="btn" href="/">Open Chisme</a></main>'), status_code=404)
        return HTMLResponse(chisme_page(shaped[0], public_base(request)))

    # ------------------------------------------------ config + accounts
    @app.get("/api/social/config")
    @wrap
    async def config(request: Request):
        site, _ = X.turnstile()
        return ok({"turnstile": site, "challenge": None if site else X.make_challenge(), "bot_copy": X.BOT_COPY,
                   "providers": X.providers(), "accounts": bool(SA.auth()), "reactions": X.REACTIONS, "accents": X.ACCENTS,
                   "reasons": X.REASONS, "areas": X.AREAS, "min_age": X.MIN_AGE, "max_video_s": X.MAX_VIDEO_S,
                   "max_photos": X.MAX_PHOTOS, "uploads": X._env("SOCIAL_UPLOADS") != "0", "media_store": S.media().name,
                   "dev_outbox": SA.fake_enabled(), "signups_public": signups_public(), "signups_soon": SIGNUPS_SOON})

    @app.get("/api/social/dev/outbox")
    async def dev_outbox(email: str = ""):
        if not SA.fake_enabled():
            return bad("Not here.", 404)
        return ok({"code": SA.FAKE.last_code(email.strip().lower())})

    @app.post("/api/social/signup")
    @wrap
    async def signup(request: Request):
        guard(request)
        adult = f"Chisme is for people {X.MIN_AGE} and up. Come back when you're older. 🤙"
        if request.cookies.get(X.U18):
            raise X.Bad(adult, 403, under_age=True)
        b = await body_of(request)
        ip = client_ip(request)
        await X.bot_check(request, b)
        await X.limit("signup_ip", ip, "Too many sign-ups from here.")
        email_raw = str(b.get("email") or "").strip()
        email = X.normalize_email(email_raw)
        if not email:
            raise X.Bad("That email doesn't look right.")
        if not signup_allowed(email):
            return bad(SIGNUPS_SOON, 403, signups_soon=True)
        try:
            bday = X.parse_birthday(b.get("birthday"))
        except ValueError as ex:
            raise X.Bad(str(ex))
        if X.age_on(bday, datetime.now(X.CT).date()) < X.MIN_AGE:
            r = bad(adult, 403, under_age=True)
            r.set_cookie(X.U18, "1", max_age=86400 * 30, path="/", httponly=True, samesite="lax")
            return r
        if b.get("tos") is not True:
            raise X.Bad("Agree to the Terms and Privacy Policy to join.")
        name = X.clean_line(b.get("display_name"), X.MAX_NAME)
        if not name:
            raise X.Bad("Add your display name.")
        u = X.clean_username(b.get("username"))
        if X.owner_email() and email == X.owner_email() and not await S.db().count("social_profiles", [("username", "eq", X.OWNER_HANDLE)]):
            u = X.OWNER_HANDLE   # v49.21: the owner's account gets @goonie, whatever they typed
        p = X.username_problem(u, email)
        if p:
            raise X.Bad(p)
        pw, pw2 = str(b.get("password") or ""), str(b.get("password2") or "")
        p = X.password_problem(pw, pw2, email, u)
        if p:
            raise X.Bad(p)
        try:
            phone = X.clean_phone(b.get("phone"))
        except ValueError as ex:
            raise X.Bad(str(ex))
        if await S.db().count("social_profiles", [("username", "eq", u)]):
            raise X.Bad("That @username is taken. Try another one.", 409)
        eh = X.hm("email", email)
        if await S.db().count("social_bans", [("email_hash", "eq", eh)]):
            raise X.Bad("That email can't be used on Chisme.", 403)
        dev = request.cookies.get(X.DEVICE) or secrets.token_urlsafe(16)
        await X.limit("signup_dev", dev, "This phone already made accounts today.")
        generic = {"next": "verify", "email": email_raw, "message": "We sent a 6-digit code to your email. Type it in to finish."}
        if await S.db().count("social_private", [("email_hash", "eq", eh)]):
            return ok(generic)   # never says the address already has an account
        res = await gotrue().signup(email_raw, pw)
        if res.get("existing") or not res.get("id"):
            return ok(generic)
        uid, t = res["id"], S.now_iso()
        await S.db().insert("social_profiles", {"id": uid, "username": u, "display_name": name, "bio": "", "area": None, "photo": None,
                                                "banner": None, "accent": "turquoise", "pinned_id": None, "privacy": {}, "status": "active",
                                                "verified": False, "flagged": False, "report_count": 0, "created_at": t, "updated_at": t,
                                                "role": None, "badge": None, "badge_at": None, "review": "pending" if X.new_user_review() else None,
                                                "golden_taco": False, "golden_taco_at": None})
        await S.db().insert("social_private", {"user_id": uid, "email_hash": eh, "email_hint": X.mask_email(email_raw), "phone": phone,
                                               # the birthday itself is never stored: only "18+, checked on this date"
                                               "adult": True, "age_checked_at": t, "tos_at": t, "tos_version": X.TERMS_VERSION,
                                               "privacy_at": t, "privacy_version": X.PRIVACY_VERSION, "signup_ip": X.hm("ip", ip),
                                               "device": X.hm("dev", dev), "created_at": t})
        await X.promote_owner(uid, email_raw)
        for kind, ver in (("terms", X.TERMS_VERSION), ("privacy", X.PRIVACY_VERSION), ("community_rules", X.RULES_VERSION), ("age_18", "birthdate-checked")):
            await S.db().insert("social_consents", {"id": X.new_id(), "user_id": uid, "kind": kind, "version": ver, "agreed_at": t})
        r = ok(generic)
        r.set_cookie(X.DEVICE, dev, max_age=86400 * 365, path="/", httponly=True, samesite="lax")
        return r

    @app.post("/api/social/verify")
    @wrap
    async def verify(request: Request):
        guard(request)
        b = await body_of(request)
        email = str(b.get("email") or "").strip()
        code = re.sub(r"\D", "", str(b.get("code") or ""))
        await X.limit("verify", X.hm("e", email.lower()) + client_ip(request), "Too many codes tried.")
        if len(code) != 6:
            raise X.Bad("The code has 6 digits.")
        d = await gotrue().verify(email, code, "email")
        prof = await X.profile_by(uid=d.get("id")) if d.get("id") else None
        if not prof:
            raise X.Bad("That code didn't work. Check it or get a new one.")
        if prof.get("status") == "banned":
            raise X.Bad("This account is closed.", 403)
        await S.db().update("social_profiles", [("id", "eq", prof["id"])], {"verified": True})
        await X.promote_owner(prof["id"], email)
        if not prof.get("verified") and prof.get("role") != "admin" and X.normalize_email(email) != X.owner_email():
            await X.notify_admins(prof["id"], "new_user")   # the admin's alerts: a new metiche to look at
        r = ok({"username": X.display_handle(prof["username"])})
        await X.start_session(r, request, prof["id"])
        return r

    @app.post("/api/social/resend")
    @wrap
    async def resend(request: Request):
        guard(request)
        b = await body_of(request)
        email = str(b.get("email") or "").strip()
        await X.limit("forgot", "resend:" + client_ip(request))
        if X.normalize_email(email):
            try:
                await gotrue().resend(email)
            except SA.AuthError:
                pass
        return ok({"message": "If that email is signing up, a new code is on the way."})

    @app.post("/api/social/login")
    @wrap
    async def login(request: Request):
        guard(request)
        b = await body_of(request)
        email = str(b.get("email") or "").strip()
        key = X.hm("e", X.normalize_email(email) or email.lower())
        await X.limit("login_ip", client_ip(request), "Too many tries from here.")
        await X.limit("login_email", key, "Too many tries for this email.")
        if X.fails(key) >= 2 or X.turnstile()[0]:
            await X.bot_check(request, b)
        try:
            d = await gotrue().password_login(email, str(b.get("password") or ""))
        except SA.AuthError as ex:
            if ex.code == "email_not_confirmed":
                return bad("Confirm your email first. We can send a new code.", 403, next="verify")
            X.fails(key, add=True)
            return bad("That email or password doesn't match.", 400, need_bot=X.fails(key) >= 2)
        prof = await X.profile_by(uid=d.get("id"))
        if not prof or prof.get("status") != "active":
            raise X.Bad("This account is closed.", 403)
        if not prof.get("verified"):
            await S.db().update("social_profiles", [("id", "eq", prof["id"])], {"verified": True})
        r = ok({"username": X.display_handle(prof["username"])})
        await X.promote_owner(prof["id"], email)
        await X.start_session(r, request, prof["id"])
        return r

    @app.post("/api/social/forgot")
    @wrap
    async def forgot(request: Request):
        guard(request)
        b = await body_of(request)
        await X.bot_check(request, b)
        await X.limit("forgot", client_ip(request))
        email = str(b.get("email") or "").strip()
        if X.normalize_email(email):
            try:
                await gotrue().recover(email)
            except SA.AuthError:
                pass
        return ok({"message": "If that email has a Chisme account, a 6-digit code is on the way."})

    @app.post("/api/social/reset")
    @wrap
    async def reset(request: Request):
        guard(request)
        b = await body_of(request)
        email = str(b.get("email") or "").strip()
        await X.limit("verify", "reset:" + X.hm("e", email.lower()))
        pw, pw2 = str(b.get("password") or ""), str(b.get("password2") or "")
        p = X.password_problem(pw, pw2, email)
        if p:
            raise X.Bad(p)
        d = await gotrue().verify(email, re.sub(r"\D", "", str(b.get("code") or "")), "recovery")
        if not d.get("access_token") or not await X.profile_by(uid=d.get("id")):
            raise X.Bad("That code didn't work.")
        await gotrue().update_user(d["access_token"], {"password": pw})
        await X.end_sessions(d["id"])
        r = ok({"message": "Password changed. You're signed in."})
        await X.start_session(r, request, d["id"])
        return r

    @app.post("/api/social/logout")
    @wrap
    async def logout(request: Request):
        guard(request)
        sid = request.cookies.get(X.COOKIE) or ""
        if sid:
            await S.db().delete("social_sessions", [("id_hash", "eq", X.hm("sess", sid))])
            X._sess_cache.pop(X.hm("sess", sid), None)
        r = ok()
        X.clear_cookie(r, request)
        return r

    @app.get("/api/social/oauth/{provider}")
    @wrap
    async def oauth_start(request: Request, provider: str):
        if provider not in X.providers():   # Apple / Google: off unless SOCIAL_APPLE=1 / SOCIAL_GOOGLE=1
            raise X.Bad("That sign-in isn't turned on.", 404)
        ver, chal = SA.pkce_pair()
        r = RedirectResponse(gotrue().authorize_url(provider, public_base(request) + "/api/social/oauth-done", chal), 302)
        r.set_cookie("chisme_pkce", ver, max_age=600, path="/api/social/", httponly=True, secure=X._https(request), samesite="lax")
        return r

    @app.get("/api/social/oauth-done")
    @wrap
    async def oauth_done(request: Request, code: str = ""):
        ver = request.cookies.get("chisme_pkce") or ""
        if not code or not ver or not X.providers():
            return RedirectResponse("/#s/signin", 302)
        d = await gotrue().pkce_exchange(code, ver)
        prof = await X.profile_by(uid=d.get("id"))
        if not prof or prof.get("status") != "active":   # a new Apple / Google account still needs the 18+ sign-up form
            return RedirectResponse("/#s/signup", 302)
        r = RedirectResponse("/#s/feed/sananto", 302)
        await X.start_session(r, request, prof["id"])
        return r

    @app.get("/api/social/me")
    @wrap
    async def me(request: Request):
        v = await X.viewer(request)
        if not v.id:
            return ok({"me": None, "owner": await is_owner(request)})
        unread = await S.db().count("social_notifications", [("user_id", "eq", v.id), ("read", "eq", False)])
        reqs = await S.db().count("social_homie_requests", [("to_id", "eq", v.id), ("status", "eq", "pending")])
        priv = (await S.db().select("social_private", [("user_id", "eq", v.id)], limit=1) or [{}])[0]
        prof = await X.profile_view(v, v.me)
        return ok({"me": {**prof, "email_hint": priv.get("email_hint", ""), "adult": priv.get("adult") is True, "area_choice": v.me.get("area")},
                   "unread": unread, "requests": reqs, "can_upload": can_upload(v.me), "owner": await is_owner(request), "admin": v.admin})

    @app.post("/api/social/account/delete")
    @wrap
    async def delete_account(request: Request):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        if b.get("confirm") != "DELETE":
            raise X.Bad("Type DELETE to confirm.")
        await X.limit("account", v.id)
        await wipe_user(v.id)
        try:
            await gotrue().admin_delete(v.id)
        except SA.AuthError:
            pass
        r = ok({"message": "Your account and everything you shared are gone. Take care. 🤙"})
        X.clear_cookie(r, request)
        return r

    async def wipe_user(uid: str) -> None:
        db = S.db()
        cids = [c["id"] for c in await db.select("social_chismes", [("author_id", "eq", uid)], cols=["id"], limit=100000)]
        media = [m["name"] for m in await db.select("social_media", [("owner_id", "eq", uid), ("status", "neq", "blocked")], cols=["name"], limit=100000)]
        if cids:
            for t in ("social_reactions", "social_saves", "social_comments", "social_notifications"):
                await db.delete(t, [("chisme_id", "in", cids)])
        for t, col in (("social_reactions", "user_id"), ("social_saves", "user_id"), ("social_comments", "author_id"), ("social_chismes", "author_id"),
                       ("social_notifications", "user_id"), ("social_notifications", "actor_id"), ("social_homies", "a"), ("social_homies", "b"),
                       ("social_homie_requests", "from_id"), ("social_homie_requests", "to_id"), ("social_nahs", "user_id"), ("social_nahs", "target_id"),
                       ("social_blocks", "blocker_id"), ("social_blocks", "blocked_id"), ("social_sessions", "user_id"), ("social_consents", "user_id"), ("social_private", "user_id")):
            await db.delete(t, [(col, "eq", uid)])
        await db.update("social_reports", [("reporter_id", "eq", uid)], {"reporter_id": None})
        await db.delete("social_media", [("owner_id", "eq", uid), ("status", "neq", "blocked")])
        await db.delete("social_profiles", [("id", "eq", uid)])
        try:
            await S.media().delete(media)
        except Exception as ex:
            print("social media delete:", type(ex).__name__)
        for k in [k for k, val in X._sess_cache.items() if val[1] == uid]:
            X._sess_cache.pop(k, None)

    install_profiles(app, is_owner)
    install_chismes(app, is_owner, reel_lookup, reel_id)


def install_profiles(app: FastAPI, is_owner) -> None:
    @app.patch("/api/social/profile")
    @wrap
    async def edit_profile(request: Request):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        await X.limit("account", "p:" + v.id)
        f: dict = {}
        if "display_name" in b:
            n = X.clean_line(b["display_name"], X.MAX_NAME)
            if not n:
                raise X.Bad("Add your display name.")
            if X.namefilter.blocked(n):
                raise X.Bad("Pick a different display name.")
            f["display_name"] = n
        if "username" in b:
            u = X.clean_username(b["username"])
            if u != v.me["username"]:
                p = X.username_problem(u, admin=v.me.get("role") == "admin")
                if p:
                    raise X.Bad(p)
                if await S.db().count("social_profiles", [("username", "eq", u)]):
                    raise X.Bad("That @username is taken. Try another one.", 409)
                f["username"] = u
        if "bio" in b:
            bio = X.clean_text(b["bio"], X.MAX_BIO)
            if X.LINK_RX.search(bio) and X.age_hours(v.me) < X.NEW_ACCOUNT_H:
                raise X.Bad("New accounts can't put links in their bio yet.")
            f["bio"] = bio
        if "area" in b:
            if b["area"] not in (None, "") and b["area"] not in X.AREAS:
                raise X.Bad("Pick a part of town from the list.")
            f["area"] = b["area"] or None
        if "accent" in b:
            if b["accent"] not in X.ACCENTS:
                raise X.Bad("Pick a color from the Fiesta palette.")
            f["accent"] = b["accent"]
        for k, pre in (("photo", "a/"), ("banner", "b/")):
            if k in b:
                nm = b[k]
                if nm in (None, ""):
                    f[k] = None
                    continue
                m = await S.db().select("social_media", [("name", "eq", str(nm)), ("owner_id", "eq", v.id)], limit=1)
                if not m or not str(nm).startswith(pre) or m[0]["status"] not in ("pending", "attached"):
                    raise X.Bad("Upload that picture again.")
                await S.db().update("social_media", [("name", "eq", nm)], {"status": "attached"})
                f[k] = nm
        if "pinned_id" in b:
            pid = b["pinned_id"]
            if pid and not (X.UUID_RX.match(str(pid)) and await S.db().count(
                    "social_chismes", [("id", "eq", str(pid)), ("author_id", "eq", v.id), ("status", "neq", "removed")])):
                raise X.Bad("You can only pin one of your own Chismes.")
            f["pinned_id"] = pid or None
        if isinstance(b.get("privacy"), dict):
            f["privacy"] = X.privacy_of({"privacy": {**X.privacy_of(v.me), **b["privacy"]}})
        if f:
            f["updated_at"] = S.now_iso()
            try:
                await S.db().update("social_profiles", [("id", "eq", v.id)], f)
            except S.Conflict:
                raise X.Bad("That @username is taken. Try another one.", 409)
        prof = await X.profile_by(uid=v.id)
        return ok({"profile": await X.profile_view(X.Viewer(prof), prof)})

    @app.get("/api/social/u/{username}")
    @wrap
    async def profile(request: Request, username: str, tab: str = "chismes"):
        v = await X.viewer(request)
        p = await X.profile_by(username=X.clean_username(username))
        if not p or not X.live(p) or p["id"] in await v.blocked():
            raise X.Bad("Nobody here by that @username. 👀", 404)
        view = await X.profile_view(v, p)
        rows = await S.db().select("social_chismes", [("author_id", "eq", p["id"]), ("status", "neq", "removed")], order=[("created_at", True)], limit=60)
        items = await X.shape_chismes(v, rows)
        if tab == "photos":
            items = [c for c in items if c["photos"]]
        elif tab == "videos":
            items = [c for c in items if c["videos"] or c["clip"]]
        pinned = next((c for c in items if c["id"] == p.get("pinned_id")), None) if tab == "chismes" else None
        if pinned:
            items = [c for c in items if c["id"] != pinned["id"]]
        return ok({"profile": view, "pinned": pinned, "chismes": items})

    @app.post("/api/social/homies/{username}")
    @wrap
    async def homie_action(request: Request, username: str):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        act = b.get("action")
        p = await X.profile_by(username=X.clean_username(username))
        if not p or not X.live(p) or p["id"] == v.id or p["id"] in await v.blocked():
            raise X.Bad("Nobody here by that @username.", 404)
        db = S.db()
        a, bb = X.pair(v.id, p["id"])
        rel = await X.relation(v, p)
        if act == "homie":
            if rel in ("homies", "requested"):
                return ok({"relation": rel})
            if rel != "incoming":
                await X.limit("homie_new" if X.age_hours(v.me) < X.NEW_ACCOUNT_H else "homie", v.id, "That's a lot of Homie requests today.")
                if X.privacy_of(p)["requests"] == "mutuals" and not (await X.homie_ids(p["id"]) & await v.homies()):
                    raise X.Bad("They only take Homie requests from people with mutual Homies.", 403)
                await db.insert("social_homie_requests", {"id": X.new_id(), "from_id": v.id, "to_id": p["id"], "status": "pending",
                                                          "created_at": S.now_iso()}, ignore_dup=True)
                await X.notify(p["id"], v.id, "homie_request", once=True)
                return ok({"relation": "requested"})
            act = "accept"
        if act == "accept":
            if rel != "incoming":
                raise X.Bad("There's no request from them.")
            await db.insert("social_homies", {"a": a, "b": bb, "created_at": S.now_iso()}, ignore_dup=True)
            await db.delete("social_homie_requests", [("from_id", "in", [v.id, p["id"]]), ("to_id", "in", [v.id, p["id"]])])
            await db.delete("social_nahs", [("user_id", "eq", v.id), ("target_id", "eq", p["id"])])
            await X.notify(p["id"], v.id, "homie_yes", once=True)
            return ok({"relation": "homies"})
        if act == "nah":   # private: nothing changes on their side; they're just shown less
            await db.insert("social_nahs", {"user_id": v.id, "target_id": p["id"], "created_at": S.now_iso()}, ignore_dup=True)
            if rel == "incoming":   # their request stays "requested" on their side; it just leaves my list
                await db.delete("social_notifications", [("user_id", "eq", v.id), ("actor_id", "eq", p["id"]), ("kind", "eq", "homie_request")])
            return ok({"relation": "none"})
        if act == "unhomie":
            await db.delete("social_homies", [("a", "eq", a), ("b", "eq", bb)])
            await db.delete("social_homie_requests", [("from_id", "eq", v.id), ("to_id", "eq", p["id"])])
            return ok({"relation": "none"})
        raise X.Bad("Pick HOMIE or NAH.")

    @app.get("/api/social/requests")
    @wrap
    async def requests_list(request: Request):
        v = await me_or_401(request)
        rows = await S.db().select("social_homie_requests", [("to_id", "eq", v.id), ("status", "eq", "pending")], order=[("created_at", True)], limit=100)
        skip = await v.blocked() | await v.nahs()
        profs = [await X.profile_by(uid=r["from_id"]) for r in rows if r["from_id"] not in skip]
        return ok({"requests": [await X.profile_view(v, p) for p in profs if X.live(p)]})

    @app.get("/api/social/suggestions")
    @wrap
    async def suggestions(request: Request):
        v = await me_or_401(request)
        mine, nah, blocked = await v.homies(), await v.nahs(), await v.blocked()
        rows = await S.db().select("social_profiles", [("verified", "eq", True), ("status", "eq", "active"), ("id", "neq", v.id)],
                                   order=[("created_at", True)], limit=300)
        pending = {r["to_id"] for r in await S.db().select("social_homie_requests", [("from_id", "eq", v.id)], cols=["to_id"], limit=5000)} | \
            {r["from_id"] for r in await S.db().select("social_homie_requests", [("to_id", "eq", v.id)], cols=["from_id"], limit=5000)}
        scored = []
        for p in rows:
            if p["id"] in mine or p["id"] in blocked or p["id"] in pending or not X.privacy_of(p)["suggest"]:
                continue
            mut = len(await X.homie_ids(p["id"]) & mine)
            s = mut * 3 + (1 if v.me.get("area") and p.get("area") == v.me.get("area") else 0) + (0.5 if X.age_hours(p) < X.FRESH_DAYS * 24 else 0)
            scored.append((s - (10 if p["id"] in nah else 0), p))
        scored.sort(key=lambda t: -t[0])
        return ok({"people": [await X.profile_view(v, p) for s, p in scored[:20] if s > -5]})

    @app.get("/api/social/notifications")
    @wrap
    async def notifications(request: Request):
        v = await me_or_401(request)
        rows = await S.db().select("social_notifications", [("user_id", "eq", v.id)], order=[("created_at", True)], limit=50)
        blocked, out = await v.blocked(), []
        for n in rows:
            a = await X.profile_by(uid=n["actor_id"]) if n["actor_id"] not in blocked else None
            if not X.live(a):
                continue
            nm = a["display_name"]
            text = {"homie_request": f"{nm} says you're Homies. 🤝", "homie_yes": f"You and {nm} are Homies now. 🤝",
                    "react": f"{nm} reacted to your Chisme.", "comment": f"{nm} commented on your Chisme. 💬",
                    "mention": f"{nm} mentioned you in a Chisme.",
                    "new_user": f"New metiche: {nm} just joined. Take a look. 👀", "report": f"Something from {nm} was reported. 🚩",
                    "held": f"{nm}'s first Chisme is waiting for your OK. ⏳"}.get(n["kind"], f"{nm} did something.")
            out.append({"id": n["id"], "kind": n["kind"], "text": text, "actor": X.mini(a), "chisme_id": n.get("chisme_id"),
                        "read": n["read"], "created_at": n["created_at"]})
        await S.db().update("social_notifications", [("user_id", "eq", v.id), ("read", "eq", False)], {"read": True})
        return ok({"notifications": out})

    @app.post("/api/social/block/{username}")
    @wrap
    async def block(request: Request, username: str):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        p = await X.profile_by(username=X.clean_username(username))
        if not p or p["id"] == v.id:
            raise X.Bad("Nobody here by that @username.", 404)
        db = S.db()
        if b.get("on", True):
            await db.insert("social_blocks", {"blocker_id": v.id, "blocked_id": p["id"], "created_at": S.now_iso()}, ignore_dup=True)
            a, bb = X.pair(v.id, p["id"])
            await db.delete("social_homies", [("a", "eq", a), ("b", "eq", bb)])
            await db.delete("social_homie_requests", [("from_id", "in", [v.id, p["id"]]), ("to_id", "in", [v.id, p["id"]])])
            return ok({"blocked": True, "message": f"Blocked. @{p['username']} can't see you or reach you, and they won't be told."})
        await db.delete("social_blocks", [("blocker_id", "eq", v.id), ("blocked_id", "eq", p["id"])])
        return ok({"blocked": False})

    @app.get("/api/social/blocked")
    @wrap
    async def blocked_list(request: Request):
        v = await me_or_401(request)
        rows = await S.db().select("social_blocks", [("blocker_id", "eq", v.id)], limit=1000)
        profs = [await X.profile_by(uid=r["blocked_id"]) for r in rows]
        return ok({"people": [X.mini(p) for p in profs if p]})

    # ------------------------------------------------ uploads (photos + short videos)
    async def scan_and_store(v: X.Viewer, name: str, data: bytes, scan: list[bytes]) -> None:
        verdicts = [await S.csam_scan(d) for d in scan]
        if "match" in verdicts:   # evidence kept privately for the legally required report; the account is closed
            await S.quarantine().put(name, data)
            await S.db().insert("social_media", {"name": name, "owner_id": v.id, "kind": "video" if name.endswith(".mp4") else "chisme",
                                                 "status": "blocked", "bytes": len(data), "created_at": S.now_iso()})
            await S.db().insert("social_csam_holds", {"id": X.new_id(), "media_name": name, "owner_id": v.id,
                                                      "sha256": hashlib.sha256(data).hexdigest(), "created_at": S.now_iso(), "reported_at": None})
            await S.db().update("social_profiles", [("id", "eq", v.id)], {"status": "banned"})
            await X.end_sessions(v.id)
            print("CSAM scan match: account closed, evidence held for the NCMEC report:", name)
            raise X.Bad("That upload can't go on Chisme.", 403)
        if "error" in verdicts:
            raise X.Bad("Chisme couldn't check that upload right now. Try again in a few minutes.", 503)
        await S.media().put(name, data)

    @app.post("/api/social/upload")
    @wrap
    async def upload(request: Request, kind: str = "chisme"):
        guard(request)
        v = await me_or_401(request)
        if X._env("SOCIAL_UPLOADS") == "0":
            raise X.Bad("Uploads are paused for a bit. Text Chismes still work.", 503)
        if not can_upload(v.me):
            raise X.Bad(UPLOADS_SOON, 403, uploads_soon=True)
        if kind not in ("chisme", "avatar", "banner", "video"):
            raise X.Bad("Unknown upload.")
        await X.limit("upload", v.id, "That's a lot of uploads. Take a breather.")
        cap = MAX_VIDEO_BODY if kind == "video" else MAX_PHOTO_BODY
        too_big = "That video is too big (40 MB max). Try a shorter one." if kind == "video" else "That photo is too big (8 MB max)."
        try:
            n = int(request.headers.get("content-length") or 0)
        except ValueError:
            n = 0
        if n > cap:
            raise X.Bad(too_big, 413)
        buf = bytearray()
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > cap:
                raise X.Bad(too_big, 413)
        raw = bytes(buf)
        if kind == "video":
            try:
                mp4, poster, meta = await asyncio.to_thread(process_video, raw)
                frames = await asyncio.to_thread(video_frames, mp4)
            except (VideoError, OP.PhotoError) as ex:
                raise X.Bad(str(ex), 413 if "big" in str(ex) else 400)
            name, pname = media_name("v", "mp4"), media_name("v")
            await scan_and_store(v, name, mp4, frames + ([poster] if poster else []))
            if poster:
                await S.media().put(pname, poster)
                await S.db().insert("social_media", {"name": pname, "owner_id": v.id, "kind": "poster", "status": "pending", "w": meta["w"],
                                                     "h": meta["h"], "bytes": len(poster), "created_at": S.now_iso()})
            await S.db().insert("social_media", {"name": name, "owner_id": v.id, "kind": "video", "status": "pending", "w": meta["w"], "h": meta["h"],
                                                 "bytes": len(mp4), "seconds": meta["seconds"], "poster": pname if poster else None,
                                                 "created_at": S.now_iso()})
            return ok({"name": name, "url": X.photo_url(name), "poster": X.photo_url(pname) if poster else None, **meta})
        edge = {"avatar": 512, "banner": 1600}.get(kind, OP.PHOTO_EDGE)
        try:
            data, w, h = await asyncio.to_thread(OP.process_photo, raw, edge)
        except OP.PhotoError as ex:
            raise X.Bad(str(ex), 413 if "big" in str(ex) or "large" in str(ex) else 400)
        name = media_name({"avatar": "a", "banner": "b"}.get(kind, "c"))
        await scan_and_store(v, name, data, [data])
        await S.db().insert("social_media", {"name": name, "owner_id": v.id, "kind": kind, "status": "pending", "w": w, "h": h, "bytes": len(data),
                                             "created_at": S.now_iso()})
        return ok({"name": name, "url": X.photo_url(name), "w": w, "h": h})

    @app.get("/api/social/media/{name:path}")
    async def media_file(request: Request, name: str):
        m = S.media()
        p = m.local_path(name)
        if not p:
            return Response(status_code=404)
        rows = await S.db().select("social_media", [("name", "eq", name)], limit=1)
        if not rows or rows[0]["status"] not in ("pending", "attached"):
            return Response(status_code=404)
        return FileResponse(p, media_type=S.ctype(name), headers={"Cache-Control": "public, max-age=86400"})


def clip_id_of(raw: str, reel_id: Callable[[str], str | None] | None) -> str | None:
    raw = str(raw or "").strip()[:500]
    m = re.search(r"[?&]reel=([\w-]{11}|\d{15,20})(?:&|#|$)", raw) or re.fullmatch(r"([\w-]{11}|\d{15,20})", raw)
    if m:
        return m.group(1)
    return reel_id(raw) if reel_id else None


async def delete_chisme(c: dict) -> None:
    db = S.db()
    names = [p.get("name") for p in c.get("photos") or []] + [x.get("name") for x in c.get("videos") or []] + \
        [x.get("poster") for x in c.get("videos") or []]
    names = [n for n in names if n]
    for t in ("social_reactions", "social_saves", "social_comments", "social_notifications"):
        await db.delete(t, [("chisme_id", "eq", c["id"])])
    await db.delete("social_chismes", [("id", "eq", c["id"])])
    await db.update("social_profiles", [("pinned_id", "eq", c["id"])], {"pinned_id": None})
    if names:
        await db.delete("social_media", [("name", "in", names)])
        try:
            await S.media().delete(names)
        except Exception as ex:
            print("social media delete:", type(ex).__name__)


def install_chismes(app: FastAPI, is_owner, reel_lookup, reel_id) -> None:
    @app.post("/api/social/chismes")
    @wrap
    async def create(request: Request):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        new = X.age_hours(v.me) < X.NEW_ACCOUNT_H
        text = X.clean_text(b.get("text"), X.MAX_TEXT)
        aud = b.get("audience") if b.get("audience") in X.AUDIENCES else X.privacy_of(v.me)["default_audience"]
        recent = [c["text"] for c in await S.db().select("social_chismes", [("author_id", "eq", v.id)], order=[("created_at", True)], limit=5, cols=["text"])]
        p = X.spam_problem(text, X.age_hours(v.me), recent)
        if p:
            raise X.Bad(p)
        names = [str(x) for x in (b.get("photos") or []) if isinstance(x, str)]
        if len(names) > X.MAX_PHOTOS:
            raise X.Bad(f"{X.MAX_PHOTOS} photos max per Chisme.")
        vname = b.get("video") if isinstance(b.get("video"), str) else None
        if vname and names:
            raise X.Bad("One video or up to 4 photos, not both in one Chisme.")
        db = S.db()
        photos, videos = [], []
        for nm in names + ([vname] if vname else []):
            m = await db.select("social_media", [("name", "eq", nm), ("owner_id", "eq", v.id), ("status", "eq", "pending")], limit=1)
            if not m or m[0]["kind"] not in ("chisme", "video") or (m[0]["kind"] == "video") != (nm == vname):
                raise X.Bad("Upload that again, it didn't stick.")
            m = m[0]
            if m["kind"] == "video":
                videos.append({"name": nm, "poster": m.get("poster"), "w": m["w"], "h": m["h"], "seconds": m.get("seconds")})
            else:
                photos.append({"name": nm, "w": m["w"], "h": m["h"]})
        clip = None
        if b.get("clip"):
            cin = b["clip"] if isinstance(b["clip"], dict) else {"url": b["clip"]}
            rid = clip_id_of(cin.get("id") or cin.get("url") or "", reel_id)
            if not rid:
                raise X.Bad("That isn't a ChismeTV, YouTube or TikTok clip link.")
            it = (reel_lookup(rid) if reel_lookup else None) or {}
            clip = {"id": rid, "title": X.clean_line(it.get("title") or cin.get("title"), 120),
                    "creator": X.clean_line(it.get("creator") or cin.get("creator"), 60)}
            if not X.clip_view(clip):
                raise X.Bad("That clip link didn't work.")
        if not (text or photos or videos or clip):
            raise X.Bad("What's the chisme? 👀 Write something or add a photo or video.")
        await X.limit("chisme_new" if new else "chisme", v.id, "You're on fire 🔥 but slow down a little.")
        await X.limit("chisme_day_new" if new else "chisme_day", v.id, "That's the most Chismes for today. Come back tomorrow.")
        tags = X.hashtags_of(text)
        meme = bool(b.get("meme")) or "memes" in tags or "meme" in tags
        if meme and "memes" not in tags:
            tags = (tags + ["memes"])[:11]
        mentions = []
        for u in dict.fromkeys(m.lower() for m in X.MENTION_RX.findall(text)):
            pr = await X.profile_by(username=u)
            if pr and X.live(pr) and pr["id"] != v.id:
                mentions.append(pr["id"])
        t = S.now_iso()
        row = {"id": X.new_id(), "author_id": v.id, "text": text, "photos": photos, "videos": videos, "clip": clip, "meme": meme,
               "audience": aud, "hashtags": tags, "mentions": mentions, "tags": [], "report_count": 0,
               "status": "held" if X.needs_review(v.me) and not v.admin else "visible",   # a new metiche's Chismes wait for the admin
               "created_at": t, "updated_at": t}
        await db.insert("social_chismes", row)
        if row["status"] == "held":
            await X.notify_admins(v.id, "held", row["id"])
        for nm in [x["name"] for x in photos + videos] + [x["poster"] for x in videos if x.get("poster")]:
            await db.update("social_media", [("name", "eq", nm)], {"status": "attached"})
        if aud != "me":
            homies = await v.homies()
            for uid in mentions:
                if aud == "everyone" or uid in homies:
                    await X.notify(uid, v.id, "mention", row["id"], once=True)
        return ok({"chisme": (await X.shape_chismes(v, [row]))[0]}, 201)

    @app.delete("/api/social/chismes/{cid}")
    @wrap
    async def remove(request: Request, cid: str):
        guard(request)
        v = await me_or_401(request)
        rows = await S.db().select("social_chismes", [("id", "eq", cid), ("author_id", "eq", v.id)], limit=1) if X.UUID_RX.match(cid) else []
        if not rows:
            raise X.Bad("That Chisme isn't yours or is gone.", 404)
        await delete_chisme(rows[0])
        return ok()

    @app.get("/api/social/feed")
    @wrap
    async def feed(request: Request, tab: str = "sananto", before: str = ""):
        if tab not in FEEDS:
            raise X.Bad("Unknown feed.")
        v = await X.viewer(request)
        rows = await feed_rows(v, tab, before[:40] or None)
        items = await X.shape_chismes(v, rows)
        if tab in ("sananto", "trending") and v.id:   # a private NAH just shows them less (pushed down, never hidden from them)
            nah = await v.nahs()
            if nah:
                ids = {p["id"]: X.display_handle(p["username"]) for p in await S.db().select("social_profiles", [("id", "in", list(nah))], cols=["id", "username"])}
                names = set(ids.values())
                items = [c for c in items if c["author"]["username"] not in names] + [c for c in items if c["author"]["username"] in names]
        return ok({"tab": tab, "chismes": items[:20], "signed_in": bool(v.id)})

    @app.get("/api/social/chismes/{cid}")
    @wrap
    async def one(request: Request, cid: str):
        v = await X.viewer(request)
        c = await X.chisme_for(v, cid)
        shaped = await X.shape_chismes(v, [c]) if c else []
        if not shaped:
            raise X.Bad("That Chisme isn't here. 👀", 404)
        return ok({"chisme": shaped[0]})

    @app.post("/api/social/chismes/{cid}/react")
    @wrap
    async def react(request: Request, cid: str):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        k = b.get("kind")
        if k not in X.REACTIONS:
            raise X.Bad("Pick a reaction.")
        c = await X.chisme_for(v, cid)
        if not c:
            raise X.Bad("That Chisme isn't here. 👀", 404)
        await X.limit("react", v.id)
        f = [("chisme_id", "eq", cid), ("user_id", "eq", v.id), ("kind", "eq", k)]
        if await S.db().count("social_reactions", f):
            await S.db().delete("social_reactions", f)
        else:
            await S.db().insert("social_reactions", {"chisme_id": cid, "user_id": v.id, "kind": k, "created_at": S.now_iso()}, ignore_dup=True)
            await X.notify(c["author_id"], v.id, "react", cid, once=True)
        return ok({"chisme": (await X.shape_chismes(v, [c]))[0]})

    @app.post("/api/social/chismes/{cid}/save")
    @wrap
    async def save(request: Request, cid: str):
        guard(request)
        v = await me_or_401(request)
        c = await X.chisme_for(v, cid)
        if not c:
            raise X.Bad("That Chisme isn't here.", 404)
        f = [("user_id", "eq", v.id), ("chisme_id", "eq", cid)]
        if await S.db().count("social_saves", f):
            await S.db().delete("social_saves", f)
        else:
            await S.db().insert("social_saves", {"user_id": v.id, "chisme_id": cid, "created_at": S.now_iso()}, ignore_dup=True)
        return ok({"chisme": (await X.shape_chismes(v, [c]))[0]})

    @app.get("/api/social/chismes/{cid}/comments")
    @wrap
    async def comments(request: Request, cid: str):
        v = await X.viewer(request)
        c = await X.chisme_for(v, cid)
        if not c:
            raise X.Bad("That Chisme isn't here.", 404)
        blocked, out = await v.blocked(), []
        rows = await S.db().select("social_comments", [("chisme_id", "eq", cid), ("status", "eq", "visible")], order=[("created_at", False)], limit=200)
        for r in rows:
            a = await X.profile_by(uid=r["author_id"]) if r["author_id"] not in blocked else None
            if X.live(a):
                out.append({"id": r["id"], "author": X.mini(a), "text": r["text"], "created_at": r["created_at"],
                            "own": r["author_id"] == v.id, "can_delete": r["author_id"] == v.id or c["author_id"] == v.id})
        return ok({"comments": out})

    @app.post("/api/social/chismes/{cid}/comments")
    @wrap
    async def comment(request: Request, cid: str):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        c = await X.chisme_for(v, cid)
        if not c:
            raise X.Bad("That Chisme isn't here.", 404)
        text = X.clean_text(b.get("text"), X.MAX_COMMENT)
        if not text:
            raise X.Bad("Say something first.")
        p = X.spam_problem(text, X.age_hours(v.me), [])
        if p:
            raise X.Bad(p)
        await X.limit("comment_new" if X.age_hours(v.me) < X.NEW_ACCOUNT_H else "comment", v.id)
        row = {"id": X.new_id(), "chisme_id": cid, "author_id": v.id, "text": text, "status": "visible", "report_count": 0, "created_at": S.now_iso()}
        await S.db().insert("social_comments", row)
        await X.notify(c["author_id"], v.id, "comment", cid)
        return ok({"comment": {"id": row["id"], "author": X.mini(v.me), "text": text, "created_at": row["created_at"], "own": True, "can_delete": True}}, 201)

    @app.delete("/api/social/comments/{mid}")
    @wrap
    async def uncomment(request: Request, mid: str):
        guard(request)
        v = await me_or_401(request)
        rows = await S.db().select("social_comments", [("id", "eq", mid)], limit=1) if X.UUID_RX.match(mid) else []
        if not rows:
            raise X.Bad("Gone already.", 404)
        r = rows[0]
        if r["author_id"] != v.id and not await S.db().count("social_chismes", [("id", "eq", r["chisme_id"]), ("author_id", "eq", v.id)]):
            raise X.Bad("That's not yours to delete.", 403)
        await S.db().delete("social_comments", [("id", "eq", mid)])
        return ok()

    # ------------------------------------------------ reports (auto-hide at 3) + the moderation queue
    @app.post("/api/social/report")
    @wrap
    async def report(request: Request):
        guard(request)
        v = await me_or_401(request)
        b = await body_of(request)
        kind, tid, reason = b.get("kind"), str(b.get("id") or "")[:60], b.get("reason")
        if kind not in ("chisme", "comment", "user") or reason not in X.REASONS:
            raise X.Bad("Pick what's wrong.")
        db = S.db()
        target_user, c = None, None
        if kind == "chisme":
            c = await X.chisme_for(v, tid)
            table = "social_chismes"
        elif kind == "comment":
            rows = await db.select("social_comments", [("id", "eq", tid), ("status", "eq", "visible")], limit=1) if X.UUID_RX.match(tid) else []
            c = rows[0] if rows and await X.chisme_for(v, rows[0]["chisme_id"]) else None
            table = "social_comments"
        else:
            p = await X.profile_by(username=X.clean_username(tid))
            c = p if X.live(p) else None
            table = "social_profiles"
            if c:
                tid = c["id"]
        if c:
            target_user = c["id"] if kind == "user" else c["author_id"]
        if not c or target_user == v.id:
            raise X.Bad("That's not something you can report.", 404)
        await X.limit("report", v.id, "You've sent a lot of reports today. Our team is on it.")
        try:
            await db.insert("social_reports", {"id": X.new_id(), "reporter_id": v.id, "target_kind": kind, "target_id": tid, "target_user": target_user,
                                               "reason": reason, "details": X.clean_text(b.get("details"), 500), "status": "open", "created_at": S.now_iso()})
        except S.Conflict:
            return ok({"message": "You already reported this. Our team will look at it.", "hidden": False})
        await X.notify_admins(target_user, "report", tid if kind == "chisme" else None)   # who reported stays private
        n = await db.count("social_reports", [("target_kind", "eq", kind), ("target_id", "eq", tid), ("status", "eq", "open")])
        fields: dict = {"report_count": n}
        hidden = n >= X.AUTO_HIDE or reason == "minor"
        if hidden:
            fields["flagged" if table == "social_profiles" else "status"] = True if table == "social_profiles" else "hidden"
        filt = [("id", "eq", tid)] + ([] if table == "social_profiles" else [("status", "neq", "removed")])
        await db.update(table, filt, fields)
        msg = "Thanks for telling us. Our team will look at it." + (" It's hidden while we check." if hidden and table != "social_profiles" else "")
        if reason == "copyright":
            msg += " If it's your work, send a takedown notice at /dmca so we can remove it for good."
        return ok({"message": msg, "hidden": hidden, "dmca": reason == "copyright"})

    @app.get("/stats/social/queue")
    @wrap
    async def mod_queue(request: Request):
        if not await admin_ok(request):
            raise X.Bad("Not here.", 404)
        db = S.db()
        reps = await db.select("social_reports", [("status", "eq", "open")], order=[("created_at", True)], limit=500)
        groups: dict = {}
        for r in reps:
            g = groups.setdefault((r["target_kind"], r["target_id"]), {"kind": r["target_kind"], "id": r["target_id"], "reasons": {}, "count": 0,
                                                                       "first": r["created_at"], "details": []})
            g["count"] += 1
            label = X.REASONS.get(r["reason"], r["reason"])
            g["reasons"][label] = g["reasons"].get(label, 0) + 1
            if r.get("details"):
                g["details"].append(r["details"][:200])
            g["first"] = min(g["first"], r["created_at"])
        out = []
        for g in groups.values():
            prev, who, status, media = "", None, "", []
            if g["kind"] == "chisme":
                rows = await db.select("social_chismes", [("id", "eq", g["id"])], limit=1)
                if rows:
                    c = rows[0]
                    prev, status = c["text"][:280], c["status"]
                    media = [X.photo_url(p.get("name")) for p in c.get("photos") or []] + [X.photo_url(x.get("poster")) for x in c.get("videos") or []]
                    who = await X.profile_by(uid=c["author_id"])
            elif g["kind"] == "comment":
                rows = await db.select("social_comments", [("id", "eq", g["id"])], limit=1)
                if rows:
                    prev, status = rows[0]["text"][:280], rows[0]["status"]
                    who = await X.profile_by(uid=rows[0]["author_id"])
            else:
                who = await X.profile_by(uid=g["id"])
                if who:
                    prev, status = who.get("bio") or "", "flagged" if who.get("flagged") else "visible"
            g.update(preview=prev, status=status, media=[m for m in media if m], author=X.mini(who) if who else None)
            out.append(g)
        out.sort(key=lambda g: (-g["count"], g["first"]))
        dmca = await db.select("social_dmca", [("status", "eq", "open")], order=[("created_at", True)], limit=100)
        holds = await db.count("social_csam_holds", [("reported_at", "isnull", None)])
        news = await db.select("social_profiles", [("review", "eq", "pending"), ("status", "eq", "active")], order=[("created_at", True)], limit=200)
        held = await db.select("social_chismes", [("status", "eq", "held")], order=[("created_at", False)], limit=300)
        v = await X.viewer(request)
        held_view = {c["id"]: c for c in await X.shape_chismes(X.Viewer(None), held, check=False)}
        new_users = []
        for p in news:
            if X.badge_of(p):
                continue
            mine = [held_view[c["id"]] for c in held if c["author_id"] == p["id"] and c["id"] in held_view]
            new_users.append({**X.mini(p), "bio": p.get("bio") or "", "joined": p["created_at"], "created_at": p["created_at"], "review": p.get("review") or "approved", "verified": bool(p.get("verified")),
                              "held": mine, "reports": p.get("report_count") or 0})
        return ok({"items": out, "dmca": [{k: d[k] for k in ("id", "claimant_name", "work", "urls", "created_at")} for d in dmca],
                   "csam_unreported": holds, "new_users": new_users, "held_count": len(held), "review_on": X.new_user_review(),
                   "badges": [{**X.mini(p), "role": p.get("role")} for p in await db.select("social_profiles", [("badge", "in", ["gold", "blue"]), ("status", "eq", "active")], limit=500)],
                   "tacos": [{**X.mini(p), "role": p.get("role")} for p in await db.select("social_profiles", [("status", "eq", "active")], limit=5000) if X.golden_taco_of(p)],
                   "taco_log": await db.select("social_admin_audit", [("action", "in", ["golden_taco_grant", "golden_taco_revoke"])], order=[("created_at", False)], limit=50)})

    @app.post("/api/social/admin/badge")
    @wrap
    async def admin_badge(request: Request):
        """Gold (people Goonie knows) or blue (active members), or none. Admin only; a blue badge also clears the review."""
        guard(request)
        if not await admin_ok(request, write=True):
            raise X.Bad("Not here.", 404)
        b = await body_of(request)
        badge = b.get("badge")
        if badge not in ("gold", "blue", None, "none"):
            raise X.Bad("Pick gold, blue or none.")
        p = await X.profile_by(username=X.clean_username(b.get("username")))
        if not p:
            raise X.Bad("No one by that @username.", 404)
        if p.get("role") == "admin":
            raise X.Bad("The admin's gold badge stays.")
        badge = None if badge in (None, "none") else badge
        fields = {"badge": badge, "badge_at": S.now_iso() if badge else None}
        if badge:
            fields["review"] = "approved"
            await release_held([("author_id", "eq", p["id"])])
        await S.db().update("social_profiles", [("id", "eq", p["id"])], fields)
        return ok({"profile": X.mini({**p, **fields})})

    @app.post("/api/social/admin/golden-taco")
    @wrap
    async def admin_golden_taco(request: Request):
        """v49.21 the 🌮 Golden Taco: admin only, grant or revoke, every change written to social_admin_audit."""
        guard(request)
        if not await admin_ok(request, write=True):
            raise X.Bad("Not here.", 404)
        b = await body_of(request)
        on = b.get("on")
        if not isinstance(on, bool):
            raise X.Bad("Say grant or revoke.")
        p = await X.profile_by(username=X.clean_username(b.get("username")))
        if not p:
            raise X.Bad("No one by that @username.", 404)
        if p.get("role") == "admin" and not on:
            raise X.Bad("The owner's Golden Taco stays.")
        fields = {"golden_taco": on, "golden_taco_at": S.now_iso() if on else None}
        await S.db().update("social_profiles", [("id", "eq", p["id"])], fields)
        v = await X.viewer(request)
        await S.db().insert("social_admin_audit", {"id": X.new_id(), "actor_id": v.me["id"] if v.me else None,
                                                   "actor": ("@" + X.display_handle(v.me["username"])) if v.me else "owner (stats sign-in)",
                                                   "target_id": p["id"], "target_username": X.display_handle(p["username"]),
                                                   "action": "golden_taco_grant" if on else "golden_taco_revoke", "created_at": S.now_iso()})
        return ok({"profile": X.mini({**p, **fields})})

    @app.post("/api/social/admin/review")
    @wrap
    async def admin_review(request: Request):
        """New metiches: approve (their held Chismes go live) or keep holding. A held Chisme: approve or remove."""
        guard(request)
        if not await admin_ok(request, write=True):
            raise X.Bad("Not here.", 404)
        b = await body_of(request)
        db, act = S.db(), b.get("action")
        if b.get("chisme"):
            cid = str(b["chisme"])[:60]
            if act not in ("approve", "remove"):
                raise X.Bad("Pick approve or remove.")
            if act == "approve":
                n = await db.count("social_chismes", [("id", "eq", cid), ("status", "eq", "held")])
                await release_held([("id", "eq", cid)])
            else:
                n = await db.update("social_chismes", [("id", "eq", cid), ("status", "eq", "held")], {"status": "removed"})
            return ok({"done": True})
        p = await X.profile_by(username=X.clean_username(b.get("username")))
        if not p:
            raise X.Bad("No one by that @username.", 404)
        if act != "approve":
            raise X.Bad("Pick approve.")
        await db.update("social_profiles", [("id", "eq", p["id"])], {"review": "approved"})
        await release_held([("author_id", "eq", p["id"])])
        return ok({"done": True})

    @app.get("/api/social/admin/stats")
    @wrap
    async def admin_stats(request: Request):
        """The social half of the ☰ Admin → Analytics page (the site half is the existing /stats/api/summary)."""
        if not await admin_ok(request):
            raise X.Bad("Not here.", 404)
        import datetime as _dt
        db = S.db()
        now = _dt.datetime.now(_dt.timezone.utc)
        out = {}
        for k, days in (("today", 1), ("7d", 7), ("30d", 30)):
            since = (now - _dt.timedelta(days=days)).isoformat()
            out[k] = {"new_users": await db.count("social_profiles", [("created_at", "gte", since)]),
                      "chismes": await db.count("social_chismes", [("created_at", "gte", since), ("status", "neq", "removed")]),
                      "reactions": await db.count("social_reactions", [("created_at", "gte", since)]),
                      "comments": await db.count("social_comments", [("created_at", "gte", since)])}
        since = (now - _dt.timedelta(days=7)).isoformat()
        rows = await db.select("social_chismes", [("created_at", "gte", since), ("status", "eq", "visible"), ("audience", "eq", "everyone")],
                               order=[("created_at", True)], limit=300)
        rx = {}
        for r in await db.select("social_reactions", [("created_at", "gte", since)], cols=["chisme_id"], limit=20000):
            rx[r["chisme_id"]] = rx.get(r["chisme_id"], 0) + 1
        top = sorted(rows, key=lambda r: -rx.get(r["id"], 0))[:5]
        authors = {p["id"]: p for p in await db.select("social_profiles", [("id", "in", list({r["author_id"] for r in top}) or ["-"])])}
        newest = await db.select("social_profiles", [], order=[("created_at", True)], limit=8)
        return ok({"periods": out, "users": await db.count("social_profiles", [("status", "eq", "active")]),
                   "top": [{"id": r["id"], "text": (r.get("text") or "")[:140], "reactions": rx.get(r["id"], 0),
                            "author": X.mini(authors[r["author_id"]]) if r["author_id"] in authors else None} for r in top],
                   "new_users": [{**X.mini(p), "created_at": p["created_at"], "review": p.get("review")} for p in newest]})

    @app.post("/stats/social/action")
    @wrap
    async def mod_action(request: Request):
        guard(request)
        if not await admin_ok(request, write=True):
            raise X.Bad("Not here.", 404)
        b = await body_of(request)
        kind, tid, act = b.get("kind"), str(b.get("id") or "")[:60], b.get("action")
        db = S.db()
        if kind == "dmca":
            if act not in ("removed", "rejected"):
                raise X.Bad("Pick remove or reject.")
            d = await db.select("social_dmca", [("id", "eq", tid)], limit=1)
            if not d:
                raise X.Bad("Gone.", 404)
            for cid in set(re.findall(r"/c/([0-9a-f-]{36})", d[0]["urls"])):
                await db.update("social_chismes", [("id", "eq", cid), ("status", "neq", "removed")], {"status": "removed" if act == "removed" else "visible"})
            await db.update("social_dmca", [("id", "eq", tid)], {"status": act})
            return ok()
        table = {"chisme": "social_chismes", "comment": "social_comments", "user": "social_profiles"}.get(kind)
        if not table or act not in ("restore", "remove", "ban"):
            raise X.Bad("Pick an action.")
        rows = await db.select(table, [("id", "eq", tid)], limit=1)
        if not rows:
            raise X.Bad("Gone.", 404)
        author = rows[0]["id"] if kind == "user" else rows[0]["author_id"]
        if act == "restore":
            await db.update(table, [("id", "eq", tid)], {"flagged": False, "report_count": 0} if kind == "user" else {"status": "visible", "report_count": 0})
        elif act == "remove":
            await db.update(table, [("id", "eq", tid)], {"flagged": True} if kind == "user" else {"status": "removed"})
        else:   # ban: the account closes, its Chismes go dark, the email can't sign up again
            await db.update("social_profiles", [("id", "eq", author)], {"status": "banned"})
            await db.update("social_chismes", [("author_id", "eq", author)], {"status": "removed"})
            priv = await db.select("social_private", [("user_id", "eq", author)], limit=1)
            if priv:
                await db.insert("social_bans", {"email_hash": priv[0]["email_hash"], "reason": "moderation", "created_at": S.now_iso()}, ignore_dup=True)
            await X.end_sessions(author)
        await db.update("social_reports", [("target_kind", "eq", kind), ("target_id", "eq", tid), ("status", "eq", "open")],
                        {"status": "dismissed" if act == "restore" else "actioned"})
        return ok()
