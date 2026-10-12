"""Chisme social, part 1 (social.py, social_api.py, social_store.py, social_auth.py): no browser, no network. FastAPI's
TestClient, the local backend (SQLite + files in a temp folder) and the in-memory fake Supabase Auth.
  • accounts: the bot check ("Prove you ain't a bot, cuh 🤖": signed math challenge + honeypot; Turnstile mocked), 18+
    (under-18 refused and remembered), the 6-digit email code, sign-in, forgot / reset, rate limits, no email ever answered
  • profiles: avatar, banner, display name, @username, bio, part of town, theme accent (Fiesta palette only), pinned Chisme;
    no LIVE anywhere
  • uploads: photos re-encoded to WebP with EXIF/GPS gone; videos re-encoded to <= 720p, <= 60 s, metadata gone, a poster;
    too long / not a video / too big refused; the CSAM hook (match → held privately, account closed; error → refused);
    R2 is picked when its keys are set (SigV4 PUT mocked), local fallback otherwise
  • Chismes: audiences (Everyone / Homies Only / Only Me), mutual Homies + private NAH, feeds (Homies, San Anto, Trending,
    Memes), reactions incl. 🌶️ + 😂, comments, saves, share pages, ChismeTV clip reposts
  • safety: report → auto-hide at 3, moderation queue (owner only) + restore / remove / ban, block, delete account, the
    DMCA page + form + "Report copyright", CSRF (cross-site refused), RLS on every table in the migration, no yellow"""
import asyncio, html, io, json, os, re, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
for k in [k for k in os.environ if k.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_", "UPLOADS_"))]:
    os.environ.pop(k)
TOKEN = "social-test-admin-token-77"
os.environ.update(ADMIN_TOKEN=TOKEN, SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=f"{tmp}/social", PUSH_STORE_FILE=f"{tmp}/push.json",
                  STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999", OWNER_POSTS_DIR=f"{tmp}/posts", OWNER_POSTS_STATIC_MAP="0", SIGNUPS_PUBLIC="1", NEW_USER_REVIEW="0", SOCIAL_OWNER_EMAIL="boss.goonie@example.com")
fails = 0


def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        fails += 1


import httpx
from fastapi.testclient import TestClient
from PIL import Image
import app as A
import social as X
import social_api as API
import social_auth as SA
import social_store as S

OFF = [0.0]
_real_now = X.now
X.now = lambda: _real_now() + OFF[0]
H = {"origin": "http://testserver"}
_ip = [10]


def client():
    _ip[0] += 1
    c = TestClient(A.app)
    c.headers.update({"x-forwarded-for": f"10.0.0.{_ip[0]}"})
    return c


def bot(c):
    cfg = c.get("/api/social/config").json()
    a, b = map(int, re.findall(r"\d+", cfg["challenge"]["question"]))
    OFF[0] += 3   # a person takes more than 2 s to fill the form
    return {"challenge": {"id": cfg["challenge"]["id"], "answer": str(a + b)}}


def join(username, name=None, bday="1990-05-05", fresh=False, **extra):
    c = client()
    email = extra.pop("email", None) or f"{username}@example.com"
    body = {"email": email, "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": name or username.title(),
            "username": username, "birthday": bday, "tos": True, **bot(c), **extra}
    r = c.post("/api/social/signup", json=body, headers=H)
    if r.status_code != 200:
        return c, r
    code = SA.FAKE.last_code(email)
    r2 = c.post("/api/social/verify", json={"email": email, "code": code}, headers=H)
    if r2.status_code == 200 and not fresh:   # past the new-account limits (tested on their own below)
        asyncio.run(S.db().update("social_profiles", [("username", "eq", username)], {"created_at": S.now_iso(time.time() - 10 * 86400)}))
    return c, r2


def jpeg_with_gps(w=900, h=700, color=(0, 201, 205)):
    im = Image.new("RGB", (w, h), color)
    ex = Image.Exif()
    ex[0x010F] = "SpyCam"            # Make
    ex[0x8825] = {1: "N", 2: (29.0, 25.0, 0.0), 3: "W", 4: (98.0, 29.0, 0.0)}   # GPS
    buf = io.BytesIO(); im.save(buf, "JPEG", exif=ex, quality=90)
    return buf.getvalue()


def make_video(seconds=3, size="1280x720", meta=True):
    out = f"{tmp}/v{seconds}_{size}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30", "-f", "lavfi", "-i", "sine=frequency=440",
           "-t", str(seconds), "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest"]
    if meta:
        cmd += ["-metadata", "location=+29.4241-098.4936/", "-metadata", "title=secret", "-metadata", "creation_time=2020-01-01T00:00:00Z"]
    subprocess.run(cmd + [out], check=True, capture_output=True)
    return open(out, "rb").read()


def probe(data):
    p = f"{tmp}/probe.mp4"; open(p, "wb").write(data)
    return json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", p],
                                     capture_output=True).stdout)


# ---------------------------------------------------------------- accounts
c0 = client()
cfg = c0.get("/api/social/config").json()
check(cfg["bot_copy"] == "Prove you ain't a bot, cuh 🤖", "bot-check copy")
check(cfg["providers"] == [], "Apple / Google sign-in off unless flagged (and Supabase is set up)")
check(not any(k for k in cfg if "live" in k.lower()) and "go live" not in json.dumps(cfg).lower(), "no LIVE in the config")
r = c0.get("/social", follow_redirects=False)
check(r.status_code == 302 and r.headers["location"] == "/#s/feed/sananto", "/social now lands in the main app's Chisme feed")
page = c0.get("/").text
check("➕ CHISME" in page and 'id="sx-chips"' in page and 'id="fb-menu"' in page and "/static/social.js" in page,
      "the main app's Chisme feed carries the social chips, the ➕ CHISME bar and the ☰ menu")
check(page.count('<header id="fbtop"') == 1 and page.count('data-view="chisme"') >= 1 and "LIVE" not in page and "Go Live" not in page,
      "one header (the app's own), no second Chisme section, no LIVE / Go Live")
css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "social.css")).read()
import re as _re
_rules = [x.strip() for x in _re.findall(r"(?:^|})\s*([^{}@]+?)\s*\{", _re.sub(r"/\*.*?\*/", "", css, flags=_re.S))]
_loose = [x for x in _rules for sel in x.split(",") if not _re.match(r"^\s*(\.sx|html|body\.sx|#view-chisme|\.mix-people|\[data-(?:theme|season)=\"\w+\"\] \.(sx|mix-people)|\.fb-menu|from|to|\d+%)", sel)]
check(not _loose, "social.css only styles its own .sx bits (the app's look stays the app's) " + repr(_loose[:3]))
js = open(f"{HERE}/static/social.js").read()
check("LIVE" not in js and "Go Live" not in js and "WHO CAN SEE THIS?" in js and "WHAT'S THE CHISME? 👀" in js and "POST CHISME 🌶️" in js,
      "composer copy (no LIVE tab / Go Live in part 1)")
check(".innerHTML" not in js, "the app never writes user text with innerHTML")

r = c0.post("/api/social/signup", json={"email": "x@example.com", "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": "X",
                                        "username": "xbot", "birthday": "1990-01-01", "tos": True, "challenge": {"id": "nope.1.2", "answer": "4"}}, headers=H)
check(r.status_code == 400 and "Prove you ain't a bot, cuh 🤖" in r.json()["error"], "a failed bot check is refused with the copy")
b = bot(c0); b["website"] = "http://spam"
r = c0.post("/api/social/signup", json={"email": "y@example.com", "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": "Y",
                                        "username": "ybot", "birthday": "1990-01-01", "tos": True, **b}, headers=H)
check(r.status_code == 400, "the honeypot field refuses bots")

# SIGNUPS_PUBLIC=0 (the default): only SOCIAL_SIGNUP_TESTERS can make accounts; browsing stays open
os.environ.pop("SIGNUPS_PUBLIC")
os.environ["SOCIAL_SIGNUP_TESTERS"] = "Tester.One@Example.com, other@example.com"
_cfg = client().get("/api/social/config").json()
check(_cfg["signups_public"] is False and "Accounts are opening soon" in _cfg["signups_soon"], "sign-ups are closed by default (SIGNUPS_PUBLIC unset)")
_sc, r = join("stranger")
check(r.status_code == 403 and r.json().get("signups_soon") and "Keep browsing the chisme" in r.json()["error"], "not on the list → 'Accounts are opening soon'")
check(not asyncio.run(S.db().select("social_profiles", [("username", "eq", "stranger")])), "…and no account was made")
_tc, r = join("testerone", email="tester.one@example.com")
check(r.status_code == 200 and _tc.cookies.get(X.COOKIE), "an email on SOCIAL_SIGNUP_TESTERS can still sign up")
check(_sc.get("/api/social/feed?tab=sananto").status_code == 200 and _sc.get("/").status_code == 200, "browsing stays open while sign-ups are closed")
_js = open(f"{HERE}/static/social.js").read()
check("signups_public === false" in _js and "#s/signup/invite" in _js, "the sign-up screen shows 'opening soon' (testers use the invite link)")
os.environ["SIGNUPS_PUBLIC"] = "1"; os.environ.pop("SOCIAL_SIGNUP_TESTERS")

ck, r = join("kiddo", bday=f"{time.localtime().tm_year - 16}-01-01")
check(r.status_code == 403 and r.json().get("under_age") and ck.cookies.get(X.U18), "under 18 → refused and remembered on that phone")
r = ck.post("/api/social/signup", json={"email": "kiddo2@example.com", **bot(ck)}, headers=H)
check(r.status_code == 403, "…and a retry with an older birthday is refused too")

goonie, r = join("goonie_tx", "Goonie") if False else join("goonie210", "Goonie")
check(r.status_code == 200 and goonie.cookies.get(X.COOKIE), "sign-up → 6-digit email code → signed in")
me = goonie.get("/api/social/me").json()
_uid = asyncio.run(S.db().select("social_profiles", [("username", "eq", "goonie210")]))[0]["id"]
_priv = asyncio.run(S.db().select("social_private", [("user_id", "eq", _uid)]))[0]
check("birthday" not in _priv and _priv["adult"] in (True, 1) and _priv["age_checked_at"], "the birthdate is checked but never stored: only 18+ and when it was checked")
sys.path.insert(0, f"{HERE}/tools"); import make_legal_pages as LP
check(_priv["tos_version"] == X.TERMS_VERSION and X.TERMS_VERSION.startswith(LP.effective("terms.md")) and _priv["privacy_version"] == X.PRIVACY_VERSION
      and X.PRIVACY_VERSION.startswith(LP.effective("privacy.md")) and X.RULES_VERSION.startswith(LP.effective("rules-and-copyright.md")) and _priv["tos_at"],
      "the agreed time + versions are saved and start with the pages' effective dates (.2 = same-day revision)")
check(X.TERMS_VERSION == X.PRIVACY_VERSION == X.RULES_VERSION == "2026-10-12.2", "consent version bumped for Plato's merged docs")
_cons = asyncio.run(S.db().select("social_consents", [("user_id", "eq", _uid)]))
check(sorted(c["kind"] for c in _cons) == ["age_18", "community_rules", "privacy", "terms"] and all(c["agreed_at"] for c in _cons), "the consent record has terms, privacy, rules and 18+")
_c, r = join("notick", tos=False)
check(r.status_code == 400 and "Terms" in r.json()["error"], "no ticked Terms box → no account (server side)")
_js = open(f"{HERE}/static/social.js").read()
_tl = [l for l in _js.split("\n") if "sx-tos" in l][0]
check("checked" not in _tl and "I agree to the " in _js and 'href: "/terms"' in _js and 'href: "/privacy"' in _js, "the Terms box starts unticked and links /terms + /privacy")
check(me["me"]["username"] == "goonie210" and "goonie210@example.com" not in json.dumps(me, ensure_ascii=False) and me["me"]["email_hint"] == "g•••@example.com", "/me never shows the full email")
lupe, _ = join("lupe", "Lupe")
tia, _ = join("tia_rosa", "Tía Rosa")
nena, _ = join("nena", "Nena")
r = client().post("/api/social/signup", json={"email": "goonie210@example.com", "password": "Tamales&Tea42", "password2": "Tamales&Tea42",
                                              "display_name": "Dup", "username": "dupper", "birthday": "1990-01-01", "tos": True, **bot(client())}, headers=H)
check(r.status_code == 200 and r.json()["next"] == "verify", "an email that's already in gets the same answer (no account fishing)")

lc = client()
r = lc.post("/api/social/login", json={"email": "lupe@example.com", "password": "wrong-password"}, headers=H)
check(r.status_code == 400, "a wrong password is refused")
r = lc.post("/api/social/login", json={"email": "lupe@example.com", "password": "Tamales&Tea42"}, headers=H)
check(r.status_code == 200, "sign in with email + password (Supabase Auth checks it)")
fc = client()
r = fc.post("/api/social/forgot", json={"email": "nena@example.com", **bot(fc)}, headers=H)
code = SA.FAKE.last_code("nena@example.com", "recovery")
r = fc.post("/api/social/reset", json={"email": "nena@example.com", "code": code, "password": "Fresh&Tea2026", "password2": "Fresh&Tea2026"}, headers=H)
check(r.status_code == 200, "forgot password → 6-digit code → new password")
check(nena.get("/api/social/me").json()["me"] is None and fc.get("/api/social/me").json()["me"]["username"] == "nena",
      "…signs out every other session and signs this phone in")
nena = fc

rc = client()
rc.headers["x-forwarded-for"] = "10.9.9.9"
codes = [rc.post("/api/social/signup", json={"email": f"spam{i}@example.com", **bot(rc)}, headers=H).status_code for i in range(6)]
check(codes[-1] == 429, "sign-ups are rate limited per IP")
r = goonie.post("/api/social/chismes", json={"text": "hi"}, headers={"origin": "https://evil.example"})
check(r.status_code == 403, "cross-site writes are refused")

# ---------------------------------------------------------------- uploads behind UPLOADS_PUBLIC (off by default) + a tester allowlist
img = jpeg_with_gps()
r = lupe.post("/api/social/upload?kind=chisme", content=img, headers={**H, "content-type": "image/jpeg"})
check(r.status_code == 403 and r.json()["error"].startswith("Photo and video uploads are coming soon") and r.json().get("uploads_soon"),
      "UPLOADS_PUBLIC unset: photo uploads say 'coming soon'")
check(lupe.post("/api/social/upload?kind=video", content=b"x" * 100, headers={**H, "content-type": "video/mp4"}).status_code == 403, "…videos too")
check(lupe.get("/api/social/me").json()["can_upload"] is False, "/me says can_upload: false")
r = lupe.post("/api/social/chismes", json={"text": "text Chismes still work 🙌"}, headers=H)
check(r.status_code == 201, "text Chismes stay open")
os.environ["SOCIAL_UPLOAD_TESTERS"] = "goonie210, @Tia_Rosa"
check(goonie.post("/api/social/upload?kind=chisme", content=img, headers={**H, "content-type": "image/jpeg"}).status_code == 200
      and tia.post("/api/social/upload?kind=chisme", content=img, headers={**H, "content-type": "image/jpeg"}).status_code == 200
      and goonie.get("/api/social/me").json()["can_upload"], "the owner + allowlisted testers can upload")
check(lupe.post("/api/social/upload?kind=chisme", content=img, headers={**H, "content-type": "image/jpeg"}).status_code == 403, "…nobody else")
os.environ.pop("SOCIAL_UPLOAD_TESTERS")
os.environ["UPLOADS_PUBLIC"] = "1"
check(lupe.get("/api/social/me").json()["can_upload"] is True, "UPLOADS_PUBLIC=1 opens uploads to everybody")
check("Photo and video uploads are coming soon" in js, "the app shows the 'coming soon' copy")

# ---------------------------------------------------------------- profile customization
up = goonie.post("/api/social/upload?kind=avatar", content=jpeg_with_gps(), headers={**H, "content-type": "image/jpeg"}).json()
ban = goonie.post("/api/social/upload?kind=banner", content=jpeg_with_gps(2000, 700, (255, 26, 127)), headers={**H, "content-type": "image/jpeg"}).json()
check(up["ok"] and up["name"].startswith("a/") and ban["ok"] and ban["name"].startswith("b/"), "avatar + banner upload")
raw = goonie.get(up["url"]).content
im = Image.open(io.BytesIO(raw))
check(im.format == "WEBP" and not im.getexif() and b"SpyCam" not in raw and max(im.size) <= 512, "avatar: WebP, EXIF + GPS gone, resized")
r = goonie.patch("/api/social/profile", json={"display_name": "Goonie El Tejano 🤠", "username": "goonie", "bio": "Spilling the tea since day one #satx",
                                              "accent": "pink", "area": "Southside", "photo": up["name"], "banner": ban["name"]}, headers=H)
p = r.json().get("profile", {})
check(r.status_code == 400, "reserved @username refused in the same save")
r = goonie.patch("/api/social/profile", json={"display_name": "Goonie El Tejano 🤠", "bio": "Spilling the tea since day one #satx",
                                              "accent": "pink", "area": "Southside", "photo": up["name"], "banner": ban["name"]}, headers=H)
p = r.json().get("profile", {})
check(r.status_code == 200 and p["accent_hex"] == "#FF1A7F" and p["banner"] and p["photo"] and p["name"] == "Goonie El Tejano 🤠"
      and p["area"] == "Southside" and p["bio"].startswith("Spilling"), "profile saved: name, bio, area, accent, avatar, banner")
r = goonie.patch("/api/social/profile", json={"username": "goonie"}, headers=H)
check(r.status_code == 400, "reserved @usernames can't be taken")
r = goonie.patch("/api/social/profile", json={"username": "goonie_tx"}, headers=H)
check(r.status_code == 200 and r.json()["profile"]["username"] == "goonie_tx", "change @username")
check(goonie.patch("/api/social/profile", json={"accent": "yellow"}, headers=H).status_code == 400, "accent must come from the Fiesta palette (no yellow)")
check("yellow" not in X.ACCENTS and all(not re.match(r"#(F{2}[CDEF]|F[CDEF]{1}[CDEF])", h, re.I) for h in X.ACCENTS.values()), "no yellow accent")
check(lupe.patch("/api/social/profile", json={"photo": up["name"]}, headers=H).status_code == 400, "you can't use someone else's upload")

# ---------------------------------------------------------------- photos + videos
ph = goonie.post("/api/social/upload?kind=chisme", content=jpeg_with_gps(3000, 2000), headers={**H, "content-type": "image/jpeg"}).json()
raw = goonie.get(ph["url"]).content
im = Image.open(io.BytesIO(raw))
check(ph["ok"] and im.format == "WEBP" and not im.getexif() and max(im.size) <= 1600 and b"SpyCam" not in raw, "chisme photo: resized WebP, no EXIF / GPS")
r = goonie.post("/api/social/upload?kind=chisme", content=b"GIF89a" + b"0" * 500, headers={**H, "content-type": "image/gif"})
check(r.status_code == 400, "non-photo files refused")
r = goonie.post("/api/social/upload?kind=chisme", content=b"0" * (9 * 1024 * 1024), headers={**H, "content-type": "image/jpeg"})
check(r.status_code == 413, "photos over 8 MB refused")
vid = goonie.post("/api/social/upload?kind=video", content=make_video(3, "1920x1080"), headers={**H, "content-type": "video/mp4"}).json()
check(vid.get("ok") and vid["name"].endswith(".mp4") and vid["h"] <= 720 and vid["seconds"] <= 60 and vid["poster"], "video: re-encoded to 720p, with a poster")
vraw = goonie.get(vid["url"]).content
pr = probe(vraw)
tags = json.dumps(pr["format"].get("tags", {})) + json.dumps([s.get("tags", {}) for s in pr["streams"]])
check("29.4241" not in tags and "secret" not in tags and "2020-01-01" not in tags and b"+29.4241" not in vraw, "video: location / title / date metadata gone")
r = goonie.post("/api/social/upload?kind=video", content=make_video(62, "320x240", meta=False), headers={**H, "content-type": "video/mp4"})
check(r.status_code == 400 and "60 seconds" in r.json()["error"], "videos over 60 s refused")
r = goonie.post("/api/social/upload?kind=video", content=b"not a video at all" * 100, headers={**H, "content-type": "video/mp4"})
check(r.status_code == 400, "non-videos refused")
r = goonie.post("/api/social/upload?kind=video", content=b"0" * (41 * 1024 * 1024), headers={**H, "content-type": "video/mp4"})
check(r.status_code == 413, "videos over 40 MB refused")

# CSAM hook: a match is held privately and closes the account; a scanner error refuses the upload
bad_c, _ = join("sketchy")
real_scan = S.csam_scan
async def match(data, client=None, kind="image/webp"): return "match"
async def broken(data, client=None, kind="image/webp"): return "error"
S.csam_scan = broken
r = bad_c.post("/api/social/upload?kind=chisme", content=jpeg_with_gps(), headers={**H, "content-type": "image/jpeg"})
check(r.status_code == 503, "CSAM scanner down → the upload waits (refused, nothing stored)")
S.csam_scan = match
r = bad_c.post("/api/social/upload?kind=chisme", content=jpeg_with_gps(), headers={**H, "content-type": "image/jpeg"})
holds = asyncio.run(S.db().select("social_csam_holds"))
check(r.status_code == 403 and len(holds) == 1 and bad_c.get("/api/social/me").json()["me"] is None, "CSAM match → held privately, account closed")
q = os.listdir(f"{tmp}/social/quarantine/c") if os.path.isdir(f"{tmp}/social/quarantine/c") else []
check(bool(q) and goonie.get("/api/social/media/" + holds[0]["media_name"]).status_code == 404, "…the file is in quarantine, never served")
S.csam_scan = real_scan

_anon_h = client()
# ---------------------------------------------------------------- v49.19 profile header photo (the same upload path: testers only, scanned, EXIF gone)
os.environ["UPLOADS_PUBLIC"] = "0"; os.environ["SOCIAL_UPLOAD_TESTERS"] = "goonie_tx"
r = lupe.post("/api/social/upload?kind=banner", content=jpeg_with_gps(1800, 600), headers={**H, "content-type": "image/jpeg"})
check(r.status_code == 403 and r.json().get("uploads_soon"), "header photo: UPLOADS_PUBLIC=0 → non-testers can't upload one")
hb = goonie.post("/api/social/upload?kind=banner", content=jpeg_with_gps(2400, 800, (0, 201, 205)), headers={**H, "content-type": "image/jpeg"}).json()
_raw = goonie.get(hb["url"]).content; _im = Image.open(io.BytesIO(_raw))
check(hb["ok"] and hb["name"].startswith("b/") and _im.format == "WEBP" and not _im.getexif() and b"SpyCam" not in _raw and max(_im.size) <= 1600,
      "header photo: a tester's upload is re-encoded, EXIF + GPS gone, capped at 1600 px")
S.csam_scan = match
_sk, _ = join("sketchy2"); os.environ["SOCIAL_UPLOAD_TESTERS"] = "goonie_tx,sketchy2"
r = _sk.post("/api/social/upload?kind=banner", content=jpeg_with_gps(), headers={**H, "content-type": "image/jpeg"})
check(r.status_code == 403 and _sk.get("/api/social/me").json()["me"] is None, "header photo: goes through the CSAM hook (match → held, account closed)")
S.csam_scan = real_scan
r = lupe.patch("/api/social/profile", json={"banner": hb["name"]}, headers=H)
check(r.status_code == 400, "header photo: you can't use someone else's upload")
r = goonie.patch("/api/social/profile", json={"banner": hb["name"]}, headers=H)
check(r.status_code == 200 and r.json()["profile"]["banner"].endswith(hb["name"]) and _anon_h.get("/api/social/u/goonie_tx").json()["profile"]["banner"], "header photo: saved + shown on the profile")
r = goonie.patch("/api/social/profile", json={"banner": None}, headers=H)
check(r.status_code == 200 and r.json()["profile"]["banner"] is None and _anon_h.get("/api/social/u/goonie_tx").json()["profile"]["banner"] is None,
      "header photo: Remove → back to the default Chisme header")
os.environ.pop("SOCIAL_UPLOAD_TESTERS"); os.environ["UPLOADS_PUBLIC"] = "1"
_js = open(f"{HERE}/static/social.js").read(); _css = open(f"{HERE}/static/social.css").read()
_hdr = _css[_css.index("/* v49.19 the profile header"):]
_sky = open(f"{HERE}/static/site/sa-skyline.svg").read()
check("📷 Change header" in _js and "✖ Remove" in _js and "/static/site/chisme-bubble-logo.svg" in _js and "/static/site/sa-skyline.svg" in _js
      and 'relation === "me"' in _js, "the owner gets Change header + Remove; the default is the Chisme bubble + the SA skyline")
_app_css = open(f"{HERE}/static/style.css").read()
check(set(re.findall(r'fill="([^"]+)"', _sky)) == {"#000", "#00C9CD"} and "sky-win" not in _sky and ".skyline{position:absolute;left:0;bottom:14px;width:100%;height:140px;display:block;fill:#000;" in _app_css
      and ".sky-win{fill:var(--turq);opacity:.5}" in _app_css, "the skyline SVG: a black silhouette (the app's own light-theme skyline art, colors as-is)")
_cols = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{3,6}\b", re.sub(r"/\*.*?\*/", "", _hdr, flags=re.S))}
check(_cols <= {"#00C9CD", "#FF1A7F", "#FF6A0B", "#000", "#FFF", "#C0C0C0"} and not re.search(r"yellow|gold\b", re.sub(r"/\*.*?\*/", "", _hdr, flags=re.S), re.I),
      f"the header uses only the icon's Fiesta colors (no yellow): {_cols}")
_skh = int(re.search(r"\.sx \.p-hdr-sky \{[^}]*height: (\d+)px", _hdr).group(1)); _hh = int(re.search(r"\.sx \.p-hdr \{ height: (\d+)px", _hdr).group(1))
check(_skh >= 88 and _hh >= 200 and _hh - _skh >= 100, f"the skyline is big (≈2× v49.19's 46 px: {_skh} px) and the header grew to keep room ({_hh} px)")
_bgc = re.search(r"\.sx \.p-hdr \{[^}]*background: (#[0-9A-Fa-f]+) ", _hdr).group(1)
check(_bgc == "#00C9CD", f"the header sky is the app icon's turquoise #00C9CD ({_bgc})")
_air = open(f"{HERE}/static/site/profile-sky.svg").read()
_airc = {c.upper() for c in re.findall(r'fill="(#[0-9A-Fa-f]+)"', _air)}
check(_airc and _airc <= {"#000", "#FFF", "#FF1A7F", "#FF6A0B"} and _air.count("<g class=\"air-") >= 3 and "p-hdr-air" in _js,
      f"a few small planes + helicopters in the sky, black, white, pink, orange only (no yellow): {_airc}")
check(re.search(r"prefers-reduced-motion: reduce\) \{ \.sx \.p-hdr-air \{ animation: none", _hdr) and "html.reduce-motion .sx .p-hdr-air { animation: none; }" in _hdr,
      "the sky's gentle drift stops for reduced motion (system setting + the app's own switch)")
check("drop-shadow(0 4px 0 #FF1A7F)" in _hdr and "confetti.svg" in _hdr and "#00C9CD" not in _air, "the black bubble + pink/orange confetti on the turquoise sky (like the icon); nothing turquoise-on-turquoise")
_ff = re.search(r'@font-face \{ font-family: "Chisme Profile Display"; src: url\("([^"]+)"\)', _hdr)
check(_ff and _ff.group(1) == "/static/fonts/chewy-site.woff" and os.path.exists(f"{HERE}{_ff.group(1)}") and "http" not in _ff.group(0)
      and '.sx .p-name { font-family: "Chisme Profile Display"' in _hdr, "the profile name uses the self-hosted Chewy display font (no CDN)")

# storage adapter: R2 when its keys are set (SigV4), local otherwise
check(S.media().name == "local", "no R2 / Supabase keys → local media fallback")
os.environ.update(R2_ACCOUNT_ID="acc123", R2_ACCESS_KEY_ID="AKIDTEST", R2_SECRET_ACCESS_KEY="secret", R2_BUCKET="chisme-media", R2_PUBLIC_BASE_URL="https://media.chisme.co")
m = S.media()
check(m.name == "r2" and m.url("c/202610/abcdefghijkl.webp") == "https://media.chisme.co/c/202610/abcdefghijkl.webp", "R2 picked when its 5 keys are set")
seen = []
m.http = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: (seen.append(req), httpx.Response(200))[1]))
asyncio.run(m.put("v/202610/abcdefghijkl.mp4", b"data"))
check(seen and seen[0].method == "PUT" and seen[0].url.host == "acc123.r2.cloudflarestorage.com" and seen[0].headers["content-type"] == "video/mp4"
      and seen[0].headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIDTEST/"), "R2 PUT is SigV4-signed with the right type")
for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_BASE_URL"):
    os.environ.pop(k)
check(S.media().name == "local", "…and back to local when the keys are gone")

# ---------------------------------------------------------------- Chismes, audiences, Homies
def post(c, **b):
    r = c.post("/api/social/chismes", json=b, headers=H)
    return r.json().get("chisme") or r.json()

c_pub = post(goonie, text="Who else is at the Pearl tonight? #satx #fiesta", photos=[ph["name"]], audience="everyone")
c_vid = post(goonie, text="Fiesta parade vibes", video=vid["name"], audience="everyone")
c_hom = post(goonie, text="Homies only: tamales at my tía's Sunday", audience="homies")
c_me = post(goonie, text="note to self: buy more Big Red", audience="me")
check(c_pub["photos"] and c_vid["videos"] and c_vid["videos"][0]["poster"], "Chismes with a photo and a video")
check(post(goonie, text="again", photos=[ph["name"]]).get("ok") is False, "an upload can't be reused in a second Chisme")
anon = client()
check(anon.get("/c/" + c_pub["id"]).status_code == 200 and anon.get("/c/" + c_hom["id"]).status_code == 404, "share page: public yes, Homies-only no")
lupe_feed = lupe.get("/api/social/u/goonie_tx").json()
ids = {c["id"] for c in lupe_feed["chismes"]}
check(c_pub["id"] in ids and c_hom["id"] not in ids and c_me["id"] not in ids, "strangers see only Everyone Chismes")
check(lupe_feed["profile"]["relation"] == "none" and "email" not in json.dumps(lupe_feed), "profile view: no email / phone / birthday")
r = lupe.post("/api/social/homies/goonie_tx", json={"action": "homie"}, headers=H).json()
check(r["relation"] == "requested", "🤝 HOMIE sends a request")
n = goonie.get("/api/social/notifications").json()["notifications"]
check(any(x["text"] == "Lupe says you're Homies. 🤝" for x in n), 'the notification reads "Lupe says you\'re Homies. 🤝"')
r = goonie.post("/api/social/homies/lupe", json={"action": "accept"}, headers=H).json()
check(r["relation"] == "homies", "YEAH, HOMIE → mutual Homies")
ids = {c["id"] for c in lupe.get("/api/social/u/goonie_tx").json()["chismes"]}
check(c_hom["id"] in ids and c_me["id"] not in ids, "Homies see Homies-only, never Only Me")
nena.post("/api/social/homies/goonie_tx", json={"action": "homie"}, headers=H)
r = goonie.post("/api/social/homies/nena", json={"action": "nah"}, headers=H).json()
check(nena.get("/api/social/u/goonie_tx").json()["profile"]["relation"] == "requested", "✋ NAH is private: their side still says requested")
check(not goonie.get("/api/social/requests").json()["requests"], "…and it leaves my request list")
tia.post("/api/social/homies/goonie_tx", json={"action": "homie"}, headers=H); goonie.post("/api/social/homies/tia_rosa", json={"action": "accept"}, headers=H)
prof = anon.get("/api/social/u/goonie_tx").json()["profile"]
check(prof["homies"] == 2 and "followers" not in json.dumps(prof).lower(), "HOMIES count, never followers")
check(lupe.get("/api/social/u/tia_rosa").json()["profile"]["mutual_homies"] == 1, "Mutual Homies count")

# pinned Chisme
r = goonie.patch("/api/social/profile", json={"pinned_id": c_vid["id"]}, headers=H)
d = anon.get("/api/social/u/goonie_tx").json()
check(d["pinned"] and d["pinned"]["id"] == c_vid["id"] and c_vid["id"] not in {c["id"] for c in d["chismes"]}, "pinned Chisme on top of the profile")
check(lupe.patch("/api/social/profile", json={"pinned_id": c_vid["id"]}, headers=H).status_code == 400, "you can only pin your own")
d = anon.get("/api/social/u/goonie_tx?tab=videos").json()
check([c["id"] for c in d["chismes"]] == [c_vid["id"]], "VIDEOS tab")
check([c["id"] for c in anon.get("/api/social/u/goonie_tx?tab=photos").json()["chismes"]] == [c_pub["id"]], "PHOTOS tab")

# new accounts: stricter posting limits, no links
newbie, _ = join("newbie", fresh=True)
check(post(newbie, text="check out spam.xyz/deal").get("ok") is False, "new accounts can't post links")
codes = [newbie.post("/api/social/chismes", json={"text": f"hola {i} {'x' * i}"}, headers=H).status_code for i in range(4)]
check(codes[:3] == [201] * 3 and codes[3] == 429, "new accounts: 3 Chismes an hour")

# memes + ChismeTV clip reposts
meme = post(lupe, text="When your tía asks why you're still single 😂 #memes", audience="everyone")
meme2 = post(tia, text="Me at the Spurs game pretending I know the rules", meme=True, audience="everyone")
clip = post(nena, text="Y'all need these tacos", clip={"url": "https://chisme.co/?reel=dQw4w9WgXcQ"}, audience="everyone")
tt = post(nena, text="this one too", clip={"url": "https://www.tiktok.com/@eatmigos/video/7301234567890123456"}, audience="everyone")
check(meme.get("meme") and meme2.get("meme") and "memes" in meme2["hashtags"], "#memes or the meme switch → a meme")
check(clip.get("clip") and clip["clip"]["id"] == "dQw4w9WgXcQ" and clip["clip"]["embed"].startswith("https://www.youtube-nocookie.com/embed/"), "repost a ChismeTV (YouTube) clip")
check(tt.get("clip") and tt["clip"]["embed"] == "https://www.tiktok.com/player/v1/7301234567890123456", "repost a ChismeTV (TikTok) clip")
check(post(nena, clip={"url": "javascript:alert(1)"}).get("ok") is False, "bad clip links refused")
mf = anon.get("/api/social/feed?tab=memes").json()["chismes"]
check({c["id"] for c in mf} == {meme["id"], meme2["id"]}, "Memes feed: only memes")

# reactions, comments, saves
for who, k in ((lupe, "chile"), (tia, "chile"), (nena, "laugh"), (lupe, "laugh")):
    who.post(f"/api/social/chismes/{meme['id']}/react", json={"kind": k}, headers=H)
cm = nena.get(f"/api/social/chismes/{meme['id']}").json()["chisme"]
check(cm["counts"]["chile"] == 2 and cm["counts"]["laugh"] == 2 and cm["mine"]["laugh"], "reactions incl. 🌶️ and 😂 (counts + mine)")
nena.post(f"/api/social/chismes/{meme['id']}/react", json={"kind": "laugh"}, headers=H)
check(nena.get(f"/api/social/chismes/{meme['id']}").json()["chisme"]["counts"]["laugh"] == 1, "tap again → reaction off")
check(set(X.REACTIONS.values()) >= {"🌶️", "😂"}, "🌶️ and 😂 are reactions")
r = tia.post(f"/api/social/chismes/{meme['id']}/comments", json={"text": "JAJAJA mija 💀"}, headers=H)
check(r.status_code == 201 and anon.get(f"/api/social/chismes/{meme['id']}/comments").json()["comments"][0]["text"] == "JAJAJA mija 💀", "comments")
r = lupe.post(f"/api/social/chismes/{c_hom['id']}/comments", json={"text": "ya llego"}, headers=H)
check(r.status_code == 201 and nena.post(f"/api/social/chismes/{c_hom['id']}/comments", json={"text": "me?"}, headers=H).status_code == 404,
      "can't comment on what you can't see")
lupe.post(f"/api/social/chismes/{c_pub['id']}/save", json={}, headers=H)
check(lupe.get(f"/api/social/chismes/{c_pub['id']}").json()["chisme"]["mine"]["saved"], "🔖 save")
check(lupe.get(f"/api/social/chismes/{c_pub['id']}").json()["chisme"]["share_url"] == "/c/" + c_pub["id"], "↗ share link for public Chismes")

# feeds
hf = lupe.get("/api/social/feed?tab=homies").json()["chismes"]
check({c_pub["id"], c_hom["id"]} <= {c["id"] for c in hf} and meme2["id"] not in {c["id"] for c in hf}, "Homies feed: confirmed Homies (+ me)")
sa = anon.get("/api/social/feed?tab=sananto").json()["chismes"]
check(c_pub["id"] in {c["id"] for c in sa} and c_hom["id"] not in {c["id"] for c in sa}, "San Anto feed: public Chismes around SA")
tr = anon.get("/api/social/feed?tab=trending").json()["chismes"]
check(tr and tr[0]["id"] == meme["id"], "Trending: the most-reacted Chisme first")
check(anon.get("/api/social/feed?tab=homies").json()["chismes"] == [], "signed out: no Homies feed")

# ---------------------------------------------------------------- reports, auto-hide, moderation
r = lupe.post("/api/social/report", json={"kind": "chisme", "id": tt["id"], "reason": "copyright"}, headers=H).json()
check(r["ok"] and r["dmca"] and "/dmca" in r["message"], "'Report copyright' points to the DMCA form")
r = goonie.post("/api/social/report", json={"kind": "chisme", "id": tt["id"], "reason": "spam"}, headers=H).json()
check(not r["hidden"], "2 reports: still up")
check(lupe.post("/api/social/report", json={"kind": "chisme", "id": tt["id"], "reason": "spam"}, headers=H).json()["message"].startswith("You already"),
      "one report per person")
r = tia.post("/api/social/report", json={"kind": "chisme", "id": tt["id"], "reason": "spam"}, headers=H).json()
check(r["hidden"] and tt["id"] not in {c["id"] for c in anon.get("/api/social/feed?tab=sananto").json()["chismes"]}, "3 reports → auto-hidden from feeds")
mine = nena.get(f"/api/social/chismes/{tt['id']}").json()
check(mine.get("chisme", {}).get("hidden") is True, "…the author still sees it, marked hidden")
check(nena.post("/api/social/report", json={"kind": "chisme", "id": clip["id"], "reason": "spam"}, headers=H).status_code == 404, "can't report your own")
check(anon.get("/stats/social/queue").status_code == 404 and lupe.get("/stats/social/queue").status_code == 404, "mod queue: owner only")
OWN = {"authorization": "Bearer " + TOKEN}
q = anon.get("/stats/social/queue", headers=OWN).json()
it = [g for g in q["items"] if g["id"] == tt["id"]]
check(it and it[0]["count"] == 3 and it[0]["status"] == "hidden" and q["csam_unreported"] == 2, "mod queue lists it (3 reports, auto-hidden) + the CSAM hold count")
r = anon.post("/stats/social/action", json={"kind": "chisme", "id": tt["id"], "action": "restore"}, headers={**OWN, **H})
check(r.status_code == 200 and anon.get(f"/api/social/chismes/{tt['id']}").status_code == 200
      and tt["id"] in {c["id"] for c in anon.get("/api/social/feed?tab=trending").json()["chismes"]}, "Keep it up → back up, in the feeds")
check(anon.post("/stats/social/action", json={"kind": "chisme", "id": tt["id"], "action": "restore"}, headers={**OWN, "origin": "https://evil.example"}).status_code == 403,
      "mod actions refuse cross-site")
anon.post("/stats/social/action", json={"kind": "chisme", "id": meme2["id"], "action": "remove"}, headers={**OWN, **H})
check(anon.get(f"/api/social/chismes/{meme2['id']}").status_code == 404, "Take it down → gone")
troll, _ = join("troll")
tc = post(troll, text="bad stuff", audience="everyone")
for w in (lupe, tia, nena):
    w.post("/api/social/report", json={"kind": "user", "id": "troll", "reason": "harassment"}, headers=H)
q = anon.get("/stats/social/queue", headers=OWN).json()
check(any(g["kind"] == "user" and g["status"] == "flagged" for g in q["items"]), "profiles reported 3× get flagged")
troll_id = [g for g in q["items"] if g["kind"] == "user"][0]["id"]
anon.post("/stats/social/action", json={"kind": "user", "id": troll_id, "action": "ban"}, headers={**OWN, **H})
check(troll.get("/api/social/me").json()["me"] is None and anon.get(f"/api/social/chismes/{tc['id']}").status_code == 404, "ban → signed out, Chismes gone")
r = client().post("/api/social/signup", json={"email": "troll@example.com", "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": "T",
                                              "username": "troll2", "birthday": "1990-01-01", "tos": True, **bot(client())}, headers=H)
check(r.status_code == 403, "a banned email can't sign up again")

# block
r = tia.post("/api/social/block/lupe", json={"on": True}, headers=H).json()
check(r["blocked"] and lupe.get("/api/social/u/tia_rosa").status_code == 404 and tia.get("/api/social/u/lupe").status_code == 404, "block hides both ways")
check(lupe.post("/api/social/homies/tia_rosa", json={"action": "homie"}, headers=H).status_code == 404, "…and stops Homie requests")
check(meme["id"] not in {c["id"] for c in tia.get("/api/social/feed?tab=memes").json()["chismes"]}, "…and their Chismes")
tia.post("/api/social/block/lupe", json={"on": False}, headers=H)

# DMCA
d = anon.get("/dmca").text
check("DMCA-1082743" in d and 'href="mailto:Arnulfoled@outlook.com"' in d, "/dmca shows the agent registration number and the copyright email by default")
os.environ["DMCA_AGENT_INFO"] = "Agent: Test Person <b>x</b>"
_o = anon.get("/dmca").text
check("Agent: Test Person &lt;b&gt;x&lt;/b&gt;" in _o and "Email copyright complaints to" not in _o, "DMCA_AGENT_INFO still overrides it (escaped)")
del os.environ["DMCA_AGENT_INFO"]
check("Arnulfo Ledezma (Chisme)" in d and "912 FM 2537 Lot #5, San Antonio, TX 78221" in d and "(210) 837-2281" in d
      and "Not listed here yet" not in d and "Designated copyright agent" in d, "/dmca: the registration's name, address and phone are the defaults")
os.environ.update(DMCA_AGENT_NAME="Test Agent", DMCA_AGENT_ADDRESS="1 Test St\nTestville, TX", DMCA_AGENT_PHONE="000-000-0000")
_o = anon.get("/dmca").text
check("Test Agent" in _o and "1 Test St<br>Testville, TX" in _o and "000-000-0000" in _o and "Arnulfo Ledezma" not in _o and "837-2281" not in _o, "/dmca: DMCA_AGENT_NAME / _ADDRESS / _PHONE override DMCA_AGENT_NAME / _ADDRESS / _PHONE")
for _k in ("DMCA_AGENT_NAME", "DMCA_AGENT_ADDRESS", "DMCA_AGENT_PHONE"): del os.environ[_k]
check("Report copyright (DMCA)" in d and "penalty of perjury" in d and "designated agent for copyright complaints" in d, "/dmca page")
r = anon.post("/dmca", data={"claimant_name": "Ana Photog", "claimant_email": "ana@example.com", "work": "My photo of the Pearl",
                             "urls": f"https://chisme.co/c/{c_pub['id']}", "signature": "Ana Photog", "good_faith": "1", "accurate": "1"}, headers=H)
check(r.status_code == 200 and "Your notice is in" in r.text and anon.get(f"/api/social/chismes/{c_pub['id']}").status_code == 404, "DMCA notice → listed Chisme hidden")
check(anon.post("/dmca", data={"claimant_name": "x"}, headers=H).status_code == 400, "DMCA form needs every part")
xss = anon.post("/dmca", data={"claimant_name": "<script>alert(1)</script>"}, headers=H).text
check("<script>alert(1)" not in xss, "DMCA form escapes what you typed")
q = anon.get("/stats/social/queue", headers=OWN).json()
check(q["dmca"] and "ana@example.com" not in json.dumps(q), "DMCA notice in the queue (claimant email not echoed)")
anon.post("/stats/social/action", json={"kind": "dmca", "id": q["dmca"][0]["id"], "action": "rejected"}, headers={**OWN, **H})
check(anon.get(f"/api/social/chismes/{c_pub['id']}").status_code == 200, "rejected notice → restored")

# delete account
r = nena.post("/api/social/account/delete", json={"confirm": "nah"}, headers=H)
check(r.status_code == 400, "delete needs DELETE typed")
_nid = asyncio.run(S.db().select("social_profiles", [("username", "eq", "nena")]))[0]["id"]
check(asyncio.run(S.db().select("social_consents", [("user_id", "eq", _nid)])), "nena has consent rows before deleting")
r = nena.post("/api/social/account/delete", json={"confirm": "DELETE"}, headers=H)
check(r.status_code == 200 and anon.get("/api/social/u/nena").status_code == 404 and anon.get(f"/api/social/chismes/{clip['id']}").status_code == 404,
      "delete account → profile + Chismes gone")
check(not any(asyncio.run(S.db().select(t, [(col, "eq", _nid)])) for t, col in (("social_private", "user_id"), ("social_consents", "user_id"),
      ("social_profiles", "id"), ("social_chismes", "author_id"), ("social_comments", "author_id"), ("social_reactions", "user_id"),
      ("social_homies", "a"), ("social_homies", "b"), ("social_sessions", "user_id"), ("social_media", "owner_id"))),
      "…private row, consents, Chismes, comments, reactions, Homies, sessions and media rows all gone (Privacy Policy §6/§7)")
check(nena.get("/api/social/me").json()["me"] is None, "…and the deleted account is signed out")

# ---------------------------------------------------------------- the admin account, badges, new-user review
boss, r = join("boss_goonie", "Goonie", email="boss.goonie@example.com")
bme = boss.get("/api/social/me").json()
check(r.status_code == 200 and bme["admin"] is True and bme["me"]["badge"] == "gold", "SOCIAL_OWNER_EMAIL's account is the admin, with the gold badge")
check(goonie.get("/api/social/me").json()["admin"] is False, "everyone else isn't")
JH = {**H, "content-type": "application/json"}
r = goonie.post("/api/social/admin/badge", json={"username": "lupe", "badge": "gold"}, headers=H)
check(r.status_code == 404 and X.badge_of(asyncio.run(X.profile_by(username="lupe"))) is None, "a non-admin can't give badges (server side)")
r = boss.post("/api/social/admin/badge", json={"username": "lupe", "badge": "blue"}, headers=H)
check(r.status_code == 200 and r.json()["profile"]["badge"] == "blue", "the admin gives a blue badge")
_feed = anon.get("/api/social/feed?tab=memes").json()["chismes"]
check(any(c["author"]["username"] == "lupe" and c["author"]["badge"] == "blue" for c in _feed), "badges show next to names in the feeds")
check(anon.get("/api/social/u/lupe").json()["profile"]["badge"] == "blue", "…and on the profile")
r = boss.post("/api/social/admin/badge", json={"username": "lupe", "badge": "gold"}, headers=H); check(r.json()["profile"]["badge"] == "gold", "…switches it to gold")
r = boss.post("/api/social/admin/badge", json={"username": "lupe", "badge": "none"}, headers=H)
check(r.json()["profile"]["badge"] is None, "…and removes it")
r = boss.post("/api/social/admin/badge", json={"username": "boss_goonie", "badge": "none"}, headers=H)
check(r.status_code == 400, "the admin's own gold badge can't be removed")
# the owner tools (/stats/*) take the admin account too: analytics, push, sponsor posts
check(boss.get("/stats/api/summary").status_code == 200 and goonie.get("/stats/api/summary").status_code in (401, 404), "analytics: admin yes, others no")
check(boss.get("/stats/posts/list").status_code == 200 and goonie.get("/stats/posts/list").status_code in (401, 404), "sponsor posts list: admin yes, others no")
check(goonie.post("/stats/push/send", json={"title": "x", "message": "y"}, headers=JH).status_code in (401, 404), "push to everyone: others can't")
r = boss.post("/stats/push/send", json={"title": "Chisme", "message": "Test"}, headers=JH)
check(r.status_code in (200, 400) and "not allowed" not in r.text, "push to everyone: the admin reaches the existing sender")
# new metiches: held for review
os.environ["NEW_USER_REVIEW"] = "1"
newb, r = join("fresh_face", "Fresh Face")
fc = post(newb, text="Hi San Anto! First Chisme 👋", audience="everyone")
check(fc.get("held") is True, "a new account's first Chisme is held")
check(anon.get(f"/api/social/chismes/{fc['id']}").status_code == 404, "…nobody else sees it yet")
check(fc["id"] in {c["id"] for c in newb.get("/api/social/u/fresh_face").json()["chismes"]}, "…but they see their own")
q = boss.get("/stats/social/queue").json()
check(any(u["username"] == "fresh_face" and any(h["id"] == fc["id"] for h in u["held"]) for u in q["new_users"]), "the 'New metiches' list has them + their held Chisme")
_al = boss.get("/api/social/notifications").json()["notifications"]
check({"new_user", "held"} <= {n["kind"] for n in _al}, "the admin's alerts include new sign-ups and held Chismes")
check(goonie.get("/stats/social/queue").status_code == 404, "the review list is admin only")
r = boss.post("/api/social/admin/review", json={"username": "fresh_face", "action": "approve"}, headers=H)
check(r.status_code == 200 and anon.get(f"/api/social/chismes/{fc['id']}").status_code == 200, "approve → their Chismes go live")
fc2 = post(newb, text="Second one, no wait")
check(not fc2.get("held"), "…and later ones aren't held")
newc, r = join("blue_soon", "Blue Soon")
h1 = post(newc, text="held till the badge")
boss.post("/api/social/admin/badge", json={"username": "blue_soon", "badge": "blue"}, headers=H)
check(h1.get("held") and anon.get(f"/api/social/chismes/{h1['id']}").status_code == 200 and not post(newc, text="free now").get("held"),
      "a blue badge ends the review (held Chismes go live)")
newd, r = join("held_out", "Held Out")
h2 = post(newd, text="spammy first post")
r = boss.post("/api/social/admin/review", json={"chisme": h2["id"], "action": "remove"}, headers=H)
check(r.status_code == 200 and newd.get(f"/api/social/chismes/{h2['id']}").status_code == 404, "the admin can remove a held Chisme")
r = goonie.post("/api/social/report", json={"kind": "chisme", "id": fc2["id"], "reason": "spam"}, headers=H)
check("report" in {n["kind"] for n in boss.get("/api/social/notifications").json()["notifications"]}, "the admin's alerts include reports")
# releasing held Chismes never un-hides one with AUTO_HIDE+ reports (approve person / approve post / badge)
def _rep(cid, n=3): asyncio.run(S.db().update("social_chismes", [("id", "eq", cid)], {"report_count": n}))
def _st(cid): return asyncio.run(S.db().select("social_chismes", [("id", "eq", cid)]))[0]["status"]
for _i, _how in enumerate(("person", "post", "badge")):
    _c, _ = join(f"reprel{_i}", "Rep Rel")
    _bad, _ok = post(_c, text="reported while held"), post(_c, text="fine while held")
    _rep(_bad["id"]); _rep(_ok["id"], 1)
    if _how == "person": boss.post("/api/social/admin/review", json={"username": f"reprel{_i}", "action": "approve"}, headers=H)
    elif _how == "post":
        for _x in (_bad, _ok): boss.post("/api/social/admin/review", json={"chisme": _x["id"], "action": "approve"}, headers=H)
    else: boss.post("/api/social/admin/badge", json={"username": f"reprel{_i}", "badge": "blue"}, headers=H)
    check(_st(_bad["id"]) == "hidden" and anon.get(f"/api/social/chismes/{_bad['id']}").status_code == 404 and _st(_ok["id"]) == "visible",
          f"release by {_how}: a held Chisme with {X.AUTO_HIDE}+ reports stays hidden, the rest go live")
# Tía chat is 18+: a signed-in account that confirmed 18+ at sign-up, nobody else (server side)
_tb = {"messages": [{"role": "user", "text": "What's the chisme today?"}], "hour": 12}
r = anon.post("/api/mascot/chat", json=_tb, headers=H)
check(r.status_code == 403 and r.json()["gate"] == "signin" and "18+" in r.json()["reply"], "Tía: signed out → the 18+ gate (sign in)")
r = lupe.post("/api/mascot/chat", json=_tb, headers=H)
check(r.status_code != 403 and r.json().get("gate") is None, "Tía: a signed-in 18+ account gets her")
check(lupe.get("/api/social/me").json()["me"]["adult"] is True, "/me says the account confirmed 18+")
_gid = asyncio.run(X.profile_by(username="lupe"))["id"]
asyncio.run(S.db().update("social_private", [("user_id", "eq", _gid)], {"adult": False}))
r = lupe.post("/api/mascot/chat", json=_tb, headers=H)
check(r.status_code == 403 and r.json()["gate"] == "adult", "Tía: an account without the 18+ flag is gated")
asyncio.run(S.db().update("social_private", [("user_id", "eq", _gid)], {"adult": True}))
r = anon.post("/api/mascot/chat", json={"messages": [{"role": "user", "text": "I want to kill myself"}]}, headers=H)
check(r.status_code != 403 and "988" in r.json().get("reply", ""), "Tía: crisis replies (988) still answer everyone, gate or not")
_aj = open(f"{HERE}/static/app.js").read(); _ix = open(f"{HERE}/static/index.html").read()
check('id="tia-gate"' in _ix and "tiaGate(" in _aj and "/api/social/me" in _aj, "the app shows the Tía 18+ gate screen before the chat")
os.environ["NEW_USER_REVIEW"] = "0"
check(X.new_user_review() is False and (os.environ.pop("NEW_USER_REVIEW") and X.new_user_review() is True), "NEW_USER_REVIEW is on unless set to 0")
_as = boss.get("/api/social/admin/stats").json()
check(_as["ok"] and _as["periods"]["30d"]["new_users"] >= 3 and any(u["username"] == "fresh_face" for u in _as["new_users"]) and isinstance(_as["top"], list),
      "☰ Admin → Analytics: social numbers (new users, Chismes, engagement, top Chismes) for the admin")
check(goonie.get("/api/social/admin/stats").status_code == 404 and anon.get("/api/social/admin/stats").status_code == 404, "…404 for everyone else")
_sj = open(f"{HERE}/static/social.js").read()
check(all(k in _sj for k in ('"#s/admin/analytics"', '"#s/admin/posts"', '"#s/admin/push"', '"#s/admin/mod"', "ME.admin ?", "/stats/push/send", 'src: "/stats/posts"')),
      "the ☰ menu has the Admin section (Analytics, Sponsor posts, Notifications, Moderation), shown only to the admin")
_sc2 = open(f"{HERE}/static/social.css").read()
import re as _re
_gold = _re.search(r"\.sx-bdg\.gold \{(.*?)\}\n", _sc2, _re.S).group(1)
check("#FF6A0B" in _gold and "#C0C0C0" in _gold and not _re.search(r"#FF(D|E|F)[0-9A-F]00|#FFFF00|gold\b|yellow", _gold, _re.I), "the gold badge is orange-gold + silver, no yellow")
# theme: social colors come from the app's variables, so switching seasons switches them
_rules = _re.sub(r"/\*.*?\*/", "", _sc2[:_sc2.index("/* v49.19 the profile header")], flags=_re.S)   # v49.19's header keeps the icon's fixed Fiesta colors
_bg = _re.findall(r"background(?:-color)?:\s*(#[0-9A-Fa-f]{3,6})\b", _rules)
check(set(_bg) <= {"#000", "#111", "#222", "#c4135f"}, f"no hard-coded light backgrounds in social.css (theme vars only): {set(_bg)}")
check("var(--card)" in _rules and 'html[data-season="muertos"] .sx {' in _rules and "--sx-banner" in _rules, "the Muertos season restyles the social screens through the theme variables")
_m3 = open(f"{HERE}/supabase/migrations/20261012200000_social_admin_badges.sql").read()
check("check (badge is null or badge in ('gold', 'blue'))" in _m3 and "social_badges_admin_only" in _m3 and "'held'" in _m3 and "force row level security" in _m3,
      "the badge migration: gold/blue only, server-only trigger, held status, RLS forced")

# ---------------------------------------------------------------- migration: RLS on every table, no yellow
sql = open(f"{HERE}/supabase/migrations/20261004150000_social_p1.sql").read()
sql2 = open(f"{HERE}/supabase/migrations/20261012190000_social_signup_consent.sql").read()
tables = set(re.findall(r"create table if not exists public\.(\w+)", sql))
tables2 = set(re.findall(r"create table if not exists public\.(\w+)", sql2))
rls = re.search(r"foreach t in array array\[(.*?)\] loop", sql, re.S).group(1)
check(tables | tables2 == set(S.TABLES) and all(f"'{t}'" in rls for t in tables)
      and all(f"alter table public.{t} force row level security" in sql2 and f"revoke all on table public.{t} from anon" in sql2 for t in tables2),
      "every table is in a migration with RLS on + forced (social_consents in the new one)")
check("drop column if exists birthday" in sql2 and "check (adult = true)" in sql2 and "tos_version" in sql2 and "Apply AFTER 20261004150000_social_p1.sql" in sql2,
      "the new migration drops stored birthdates, keeps 18+ and the consent versions, and runs after part 1")
_cols = set(S.TABLES["social_private"]["cols"])
check({"adult", "age_checked_at", "tos_version", "privacy_version"} <= _cols and "birthday" not in _cols, "the store matches the new migration")
# the legal pages: Plato's text word for word, in the app's look, cross-links working
for _path, _src in (("/terms", "terms.md"), ("/privacy", "privacy.md"), ("/community-rules", "rules-and-copyright.md")):
    _h = anon.get(_path); _md = open(f"{HERE}/legal/{_src}").read()
    _heads = re.findall(r"^#{1,3} (.+)$", _md, re.M)
    check(_h.status_code == 200 and "/static/style.css" in _h.text and 'class="topbar' in _h.text and all(html.escape(x, quote=False) in _h.text for x in _heads)
          and 'href="terms.md"' not in _h.text and 'href="privacy.md"' not in _h.text and "TODO" not in _h.text, f"{_path}: Plato's text in the app's look")
    check(_md == open(f"/workspace/chisme_legal/{_src}").read() if os.path.exists(f"/workspace/chisme_legal/{_src}") else True, f"{_src}: wording untouched")
_pp = anon.get("/privacy").text
check("strip GPS and other EXIF location metadata" in _pp and "in-app account deletion" in _pp, "the Privacy Policy's EXIF + in-app delete promises are on the page (and tested above)")
check("912 FM 2537 Lot #5" in anon.get("/community-rules").text, "the agent's mailing address is on the rules page (legal_contact.py can hide it)")
check("enable row level security" in sql and "force row level security" in sql and "revoke all on table public.%I from anon" in sql, "RLS on, anon revoked")
css = open(f"{HERE}/static/social.css").read().lower()
check(not re.search(r"yellow|gold|#ff(?:d|e|f)[0-9a-f]00\b|#ff[cdef]\d0[0-9a-f]\b", re.sub(r"/\*.*?\*/", "", css, flags=re.S).replace(".gold", "").replace("--marigold", "")), "no yellow in social.css (the .gold badge class and the app's orange --marigold aside)")

print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
