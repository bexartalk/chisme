"""Photo upload regression: Supabase Storage URLs, size limits and JSON errors; no network."""
import asyncio, io, os, random, re, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
_tmp = tempfile.TemporaryDirectory()
tmp = _tmp.name
for k in [k for k in os.environ if k.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_", "UPLOADS_"))]:
    os.environ.pop(k)
TOKEN = "social-test-admin-token-77"
os.environ.update(ADMIN_TOKEN=TOKEN, SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=f"{tmp}/social", PUSH_STORE_FILE=f"{tmp}/push.json",
                  STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999", OWNER_POSTS_DIR=f"{tmp}/posts", OWNER_POSTS_STATIC_MAP="0", SIGNUPS_PUBLIC="1", NEW_USER_REVIEW="0", SOCIAL_OWNER_EMAIL="boss.goonie@example.com",
                  SOCIAL_UPLOAD_TESTERS="goonie")
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
import social_auth as SA
import social_store as S

OFF = [0.0]
_real_now = X.now
X.now = lambda: _real_now() + OFF[0]
H = {"origin": "http://testserver"}


def bot(c):
    cfg = c.get("/api/social/config").json()
    a, b = map(int, re.findall(r"\d+", cfg["challenge"]["question"]))
    OFF[0] += 3
    return {"challenge": {"id": cfg["challenge"]["id"], "answer": str(a + b)}}


def join():
    c = TestClient(A.app)
    c.headers.update({"x-forwarded-for": "10.0.0.11"})
    email = "boss.goonie@example.com"
    r = c.post("/api/social/signup", json={"email": email, "password": "Tamales&Tea42", "password2": "Tamales&Tea42",
               "display_name": "Goonie", "username": "goonie", "birthday": "1990-05-05", "tos": True, **bot(c)}, headers=H)
    check(r.status_code == 200, "owner signs up")
    r = c.post("/api/social/verify", json={"email": email, "code": SA.FAKE.last_code(email)}, headers=H)
    check(r.status_code == 200 and c.cookies.get(X.COOKIE), "owner verifies and signs in")
    asyncio.run(S.db().update("social_profiles", [("username", "eq", "goonie")], {"created_at": S.now_iso(time.time() - 10 * 86400)}))
    return c


def jpeg(im, quality=90):
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


objects = {}


def storage(request):
    if request.method == "POST":
        objects[request.url.path] = request.content
        return httpx.Response(200, json={"Key": request.url.path})
    return httpx.Response(404)


http = httpx.AsyncClient(transport=httpx.MockTransport(storage))
media = S.SupabaseMedia("https://abc.supabase.co", "k", "chisme-media", client=http)
name = "c/202610/x.webp"
check(media.url(name) == "https://abc.supabase.co/storage/v1/object/public/chisme-media/c/202610/x.webp", "Supabase url() stays callable and returns the public URL")
check(isinstance(S.R2Media("account", "access", "secret", "bucket", "https://media.example.com", client=http).url(name), str), "R2 url() returns a string")
check(isinstance(S.LocalMedia(f"{tmp}/media").url(name), str), "local url() returns a string")

# Patch only media: Supabase credentials in the environment would also switch the DB.
os.environ["SOCIAL_MEDIA_STORE"] = "supabase"
_real_media = S.media
S.media = lambda: media
try:
    goonie = join()
    me = goonie.get("/api/social/me").json()
    owner = asyncio.run(S.db().select("social_profiles", [("username", "eq", "goonie")]))[0]
    check(owner["role"] == "admin" and me["can_upload"], "signed-in owner is an admin and can upload")
    img = jpeg(Image.new("RGB", (1200, 900), (0, 201, 205)))

    def upload(data):
        return goonie.post("/api/social/upload?kind=chisme", content=data, headers={**H, "content-type": "image/jpeg"})

    r = upload(img)
    ph = r.json()
    check(r.status_code == 200 and ph.get("ok"), "JPEG upload returns JSON success with Supabase media")
    path = "/storage/v1/object/chisme-media/" + ph.get("name", "")
    check(ph.get("url") == media.url(ph.get("name", "")) and bool(objects.get(path)), "upload returns its Supabase public URL and sends the object to storage")
    r = goonie.post("/api/social/chismes", json={"text": "Photo upload regression", "photos": [ph.get("name")], "audience": "everyone"}, headers=H)
    check(r.status_code == 201 and r.json().get("ok") and r.json()["chisme"]["photos"][0]["url"] == ph.get("url"), "create a Chisme with the uploaded Supabase photo")

    # Seeded random pixels make a reproducible large, valid JPEG.
    large = jpeg(Image.frombytes("RGB", (3000, 2500), random.Random(42).randbytes(3000 * 2500 * 3)), quality=90)
    check(5 * 1024 * 1024 < len(large) < 8 * 1024 * 1024, "large JPEG is between 5 and 8 MB")
    r = upload(large)
    check(r.status_code == 200 and r.json().get("ok"), "large JPEG uploads successfully")
    r = upload(b"x" * (9 * 1024 * 1024))
    check(r.status_code == 413 and r.json().get("error") == "That photo is too big (8 MB max).", "9 MB body returns the JSON photo size error")

    async def boom(name, data):
        raise RuntimeError("boom")

    _real_put = media.put
    media.put = boom
    try:
        r = upload(img)
        check(r.status_code == 500 and r.json().get("error") == "Chisme hit a snag on our end. Try again in a minute.", "unexpected backend exception returns a friendly JSON 500")
    finally:
        media.put = _real_put
finally:
    S.media = _real_media
    X.now = _real_now
    asyncio.run(http.aclose())

js = open(f"{HERE}/static/social.js").read()
check("That's too big to send. Try a smaller photo or a shorter video." in js, "413 friendly fallback is present")
check('const VERSION = "chisme-v49.27.2";' in open(f"{HERE}/static/sw.js").read(), "service worker version is 49.27.2")
check('window.CHISME_APP_BUILD = "49.27.2";' in open(f"{HERE}/static/app.js").read(), "app build is 49.27.2")
print(f"\n{fails} failure(s)")
sys.exit(1 if fails else 0)
