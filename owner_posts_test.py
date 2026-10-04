"""Owner posts ("post your own chisme", ownerposts.py): no browser, no network. FastAPI's TestClient, the local backend
(sqlite + files in a temp folder), a mocked Supabase (httpx.MockTransport) and mocked OpenStreetMap tiles.
  • who can write: visitors, a forged / made-up session cookie, a wrong Bearer key and form posts get 401 on create, edit,
    delete, photo upload, push preview / send, the list and the map preview (404 on a server with no ADMIN_TOKEN); the
    composer page sends visitors to the /stats sign-in
  • CSRF: a cross-site Origin, Origin: null, Sec-Fetch-Site cross-site / same-site → 403, even with the owner's cookie
  • escaping: XSS payloads in the headline, text, photo credit + alt, location, map address and source name are inert on
    /p/<slug> (no injected tags / handlers / scripts), in its og / twitter tags, the JSON-LD, the composer and /stats;
    source links are http(s) only (javascript:, data:, ftp:, //host, user:pass@, quotes refused)
  • uploads: JPEG / PNG / WebP only (GIF, SVG, HTML, HEIC refused), 8 MB / 12 MB request caps (413), 50 MP bomb (413),
    tiny images refused; EXIF (GPS, camera), XMP, comments and PNG text chunks are gone from the stored WebP; upright
  • the rules: News posts refuse emoji; lengths; map pins; drafts are invisible to the public (API, page); pins expire and
    pinned posts come first; edit keeps unsent fields and deletes dropped photos; delete needs {"confirm": "DELETE"} and
    removes the row, its photos and its map
  • Paid / Sponsored: a "Sponsored" label on the API shape, the page, og / twitter / meta descriptions and the notification;
    independent of pin-to-top (a 1-week pinned spotlight; unpin keeps the label); never on News
  • push: "not set up yet" (503) without VAPID keys, the preview, a mocked send, once per post, drafts refused
  • Supabase backend (mocked PostgREST + Storage): published-only reads, the secret key only in the apikey header (Bearer
    only for a legacy JWT), public photo URLs, and the key never reaches a response
  • the static map: mocked OSM tiles → pin + credit, yellow turned silver (no_yellow), off switch, tile errors → no map"""
import asyncio, base64, html, io, json, os, re, sys, tempfile, time, urllib.parse
from html.parser import HTMLParser
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
for k in [k for k in os.environ if k.startswith(("UPSTASH_", "RENDER", "PUSH_TEST", "SUPABASE_", "VAPID_", "OWNER_POSTS", "OSM_"))]: os.environ.pop(k)
TOKEN = "owner-posts-test-token-42"
os.environ.update(ADMIN_TOKEN=TOKEN, PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999",
                  OWNER_POSTS_DIR=f"{tmp}/posts", OWNER_POSTS_STATIC_MAP="0")
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

import httpx
from PIL import Image
from fastapi.testclient import TestClient
import app as A, ownerposts as OP, push, stats

J = {"Content-Type": "application/json"}
SAME = {**J, "Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}
visitor = TestClient(A.app)
owner = TestClient(A.app)
r = owner.post("/stats/login", content="key=" + TOKEN + "&remember=1", headers={"content-type": "application/x-www-form-urlencoded", "origin": "http://testserver"}, follow_redirects=False)
sc = r.headers.get("set-cookie", "")
check(r.status_code == 303 and stats.COOKIE in owner.cookies, f"the owner signs in on /stats ({r.status_code})")
check("httponly" in sc.lower() and "samesite=strict" in sc.lower() and "path=/stats" in sc.lower(), "the session cookie: HttpOnly, SameSite=Strict, Path=/stats")

def ow(method, url, body=None, headers=None, **kw):
    return owner.request(method, url, content=json.dumps(body) if body is not None else None, headers={**SAME, **(headers or {})}, **kw)

def jpeg(w=400, h=300, color=(0, 201, 205), **save):
    b = io.BytesIO(); Image.new("RGB", (w, h), color).save(b, "JPEG", quality=90, **save); return b.getvalue()

def data_url(raw, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(raw).decode()

def upload(raw, mime="image/jpeg", client=None, headers=None):
    if client is None:
        return ow("POST", "/stats/posts/photo", {"data": data_url(raw, mime)}, headers=headers)
    return client.post("/stats/posts/photo", content=json.dumps({"data": data_url(raw, mime)}), headers={**J, **(headers or {})})

def media(url):
    return visitor.get(url)

# ------------------------------------------------------------------ who can write
print("== visitors and non-owners can't write (401), the server without ADMIN_TOKEN hides it (404)")
good = {"category": "other", "headline": "A test post", "body": "Hello"}
ENDS = [("POST", "/stats/posts", good), ("PATCH", "/stats/posts/0123456789abcdef0123456789abcdef", {"headline": "x"}),
        ("DELETE", "/stats/posts/0123456789abcdef0123456789abcdef", {"confirm": "DELETE"}), ("POST", "/stats/posts/photo", {"data": data_url(jpeg())}),
        ("POST", "/stats/posts/push-preview", good), ("POST", "/stats/posts/0123456789abcdef0123456789abcdef/push", {"confirm": True}),
        ("GET", "/stats/posts/list", None), ("GET", "/stats/posts/map-preview?lat=29.5&lon=-98.4", None)]
def codes(client, headers=None, cookies=None):
    out = []
    for m, u, b in ENDS:
        cl = client
        if cookies is not None:
            cl = TestClient(A.app); [cl.cookies.set(k, v, path="/stats") for k, v in cookies.items()]
        out.append(cl.request(m, u, content=json.dumps(b) if b is not None else None, headers={**J, **(headers or {})}).status_code)
    return out
check(codes(visitor) == [401] * len(ENDS), f"no sign-in: {codes(visitor)}")
check(codes(visitor, cookies={stats.COOKIE: "made-up-session-id", "chisme_admin": "1"}) == [401] * len(ENDS), "a made-up session cookie + the chisme_admin=1 marker: all 401")
check(codes(visitor, headers={"Authorization": "Bearer not-the-key"}) == [401] * len(ENDS), "a wrong Bearer key: all 401")
form = [owner.request(m, u, content=urllib.parse.urlencode(b or {}), headers={"content-type": "application/x-www-form-urlencoded", "origin": "http://testserver"}).status_code
        for m, u, b in ENDS[:6]]
check(form == [401] * 6, f"the owner's own cookie on a form post (not JSON) → 401, so no cross-site form can use it {form}")
tp = owner.post("/stats/posts", content=json.dumps(good), headers={"content-type": "text/plain", "origin": "http://testserver"}).status_code
check(tp == 401, f"…and text/plain (a 'simple' cross-site request) → 401 ({tp})")
os.environ.pop("ADMIN_TOKEN")
nt = codes(visitor)
os.environ["ADMIN_TOKEN"] = TOKEN
check(nt == [404] * len(ENDS), f"a server with no ADMIN_TOKEN: 404 (the feature doesn't exist there) {nt}")
g = visitor.get("/stats/posts", follow_redirects=False)
check(g.status_code == 303 and g.headers["location"] == "/stats", f"a visitor opening the composer goes to the sign-in ({g.status_code} → {g.headers.get('location')})")
g = owner.get("/stats/posts")
gn = re.search(r"'nonce-([^']+)'", g.headers.get("content-security-policy", ""))
check(g.status_code == 200 and "no-store" in g.headers.get("cache-control", "") and gn and f'nonce="{gn.group(1)}"' in g.text and 'id="op-form"' in g.text,
      "the owner gets the composer: no-store, the CSP nonce on its script")
check(TOKEN not in g.text, "the admin key isn't in the composer page")

print("== CSRF: only this site can call the owner endpoints")
for label, hdr in (("a cross-site Origin", {"Origin": "https://evil.example"}), ("Origin: null", {"Origin": "null"}),
                   ("Sec-Fetch-Site: cross-site", {"Sec-Fetch-Site": "cross-site", "Origin": ""}), ("Sec-Fetch-Site: same-site", {"Sec-Fetch-Site": "same-site"}),
                   ("a look-alike Origin", {"Origin": "http://testserver.evil.example"})):
    h2 = {**SAME, **hdr}
    if h2.get("Origin") == "": h2.pop("Origin")
    cs = [owner.request(m, u, content=json.dumps(b), headers=h2).status_code for m, u, b in ENDS[:6]]
    check(cs == [403] * 6, f"{label} with the owner's cookie → 403 {cs}")
cs = owner.post("/stats/posts/push-preview", content=json.dumps(good), headers=J).status_code
check(cs == 200, f"no Origin / Sec-Fetch-Site (a same-origin fetch from an older browser) still works ({cs})")
b2 = visitor.post("/stats/posts/push-preview", content=json.dumps(good), headers={**J, "Authorization": "Bearer " + TOKEN}).status_code
check(b2 == 200, f"Bearer ADMIN_TOKEN (a script, no cookie, no Origin) works ({b2})")

# ------------------------------------------------------------------ validation + escaping
print("== source links: http(s) only")
for u in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", " javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "ftp://example.com/x", "//evil.example/x",
          "https://user:pw@example.com/", 'https://example.com/"onmouseover="alert(1)', "https://example.com/<script>", "http://localhost", "vbscript:msgbox(1)",
          "https://exa mple.com/"):
    r = ow("POST", "/stats/posts", {**good, "source_url": u})
    check(r.status_code == 400 and "http" in r.json().get("error", ""), f"source {u!r} refused ({r.status_code})")
r = ow("POST", "/stats/posts", {**good, "source_url": "https://news4sanantonio.com/news/local/x?a=1&b=2"})
check(r.status_code == 200 and r.json()["post"]["source_url"] == "https://news4sanantonio.com/news/local/x?a=1&b=2", "a real https link is kept as is")
ow("DELETE", "/stats/posts/" + r.json()["post"]["id"], {"confirm": "DELETE"})

print("== XSS payloads are inert everywhere")
ph = upload(jpeg()).json()["photo"]
X = {"headline": '"><img src=x onerror=alert(1)><script>alert(2)</script>',
     "body": "<b onmouseover=alert(3)>**bold <i>x</i>**</b>\n\n- <svg onload=alert(4)>\n- </p><script>alert(44)</script>",
     "credit": "</figcaption><script>alert(5)</script>", "alt": '" onerror="alert(6)', "location": "<iframe src=javascript:alert(7)></iframe>",
     "map_query": '"><script>alert(8)</script>', "source_name": "<a href=javascript:alert(9)>x</a>"}
r = ow("POST", "/stats/posts", {"category": "other", "headline": X["headline"], "body": X["body"], "photos": [{**ph, "credit": X["credit"], "alt": X["alt"]}],
                                 "location": X["location"], "map_query": X["map_query"], "source_url": "https://example.com/a?q=%22%3E%3Cscript%3E", "source_name": X["source_name"]})
check(r.status_code == 200, f"the post saves (text is stored as typed, escaped on the way out) ({r.status_code})")
xp = r.json()["post"]
check(xp["headline"] == X["headline"] and xp["photos"][0]["credit"] == X["credit"], "the API returns the raw text (the app puts it in with textContent)")

class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.tags, self.scripts, self.meta, self._s = [], [], {}, None
    def handle_starttag(self, t, a):
        a = dict(a); self.tags.append((t, a))
        if t == "script": self._s = [a, ""]
        if t == "meta" and (a.get("property") or a.get("name")): self.meta[a.get("property") or a.get("name")] = a.get("content")
    def handle_data(self, d):
        if self._s is not None: self._s[1] += d
    def handle_endtag(self, t):
        if t == "script" and self._s is not None: self.scripts.append(self._s); self._s = None
def scan(text):
    s = Scan(); s.feed(text); return s
def inert(text, where):
    s = scan(text)
    handlers = [(t, k) for t, a in s.tags for k in a if k.startswith("on")]
    bad_tags = [t for t, a in s.tags if t in ("iframe", "svg", "object", "embed")]
    imgs = [a.get("src") for t, a in s.tags if t == "img" and a.get("src") == "x"]
    js_links = [a.get("href") for t, a in s.tags if t == "a" and (a.get("href") or "").strip().lower().startswith(("javascript", "data", "vbscript"))]
    evil_js = [sc[1][:60] for sc in s.scripts if "alert(" in sc[1] and sc[0].get("type") not in ("application/ld+json", "application/json")]
    check(not handlers and not bad_tags and not imgs and not js_links and not evil_js, f"{where}: no injected tags, handlers, javascript: links or scripts {handlers[:3]} {bad_tags[:3]} {imgs[:2]} {js_links[:2]} {evil_js[:2]}")
    return s
pg = visitor.get("/p/" + xp["slug"])
s = inert(pg.text, "/p/<slug>")
ld = [sc for sc in s.scripts if sc[0].get("type") == "application/ld+json"]
check(len(ld) == 1 and "</" not in ld[0][1] and "<" not in ld[0][1] and json.loads(ld[0][1])["headline"] == X["headline"], "the JSON-LD can't be closed early (< and > are \\u-escaped) and still says the real headline")
check(s.meta.get("og:title") == X["headline"] and s.meta.get("twitter:title") == X["headline"], "og:title / twitter:title: the exact headline, attribute-escaped")
check("<img src=x" not in pg.text and "<script>alert" not in pg.text and "<iframe" not in pg.text and 'onerror="alert' not in pg.text, "none of the raw payloads are anywhere in the page source")
for k in ("headline", "credit", "location", "source_name"):
    check(html.escape(X[k], quote=False).replace('"', "&quot;") in pg.text or html.escape(X[k]) in pg.text, f"{k}: shown as text (escaped) on the page")
check("<strong>bold &lt;i&gt;x&lt;/i&gt;</strong>" in pg.text and "&lt;svg onload=alert(4)&gt;" in pg.text, "the text's **bold** and bullets work, with the HTML inside escaped")
src_a = [a for t, a in s.tags if t == "a" and "example.com" in (a.get("href") or "")]
check(src_a and src_a[0]["href"].startswith("https://example.com/") and "nofollow" in src_a[0].get("rel", ""), "the source link is the https URL (rel nofollow noopener)")
gm = [a for t, a in s.tags if t == "a" and "google.com/maps" in (a.get("href") or "")]
check(gm and gm[0]["href"].startswith("https://www.google.com/maps/search/?api=1&query=") and "<" not in gm[0]["href"] and '"' not in gm[0]["href"], "the Google Maps link is URL-encoded")
inert(owner.get("/stats/posts").text, "the composer (the owner's page)")
sp_html = owner.get("/stats").text
card = sp_html[sp_html.index('id="op-entry"'):][:4000]
check("<img src=x" not in sp_html and "<script>alert" not in sp_html and html.escape(X["headline"]) in card, "/stats: the Post your own chisme card shows the headline as text")
cp = scan(owner.get("/stats/posts").text)
dat = [sc for sc in cp.scripts if sc[0].get("id") == "op-data"]
check(dat and dat[0][0].get("type") == "application/json" and "<" not in dat[0][1] and json.loads(dat[0][1])["posts"][0]["headline"] == X["headline"],
      "the composer's data is an inert application/json block with < escaped")
check("<script>alert(2)" not in owner.get("/stats/posts").text, "the composer's embedded data is \\u003c-escaped")
api = visitor.get("/api/posts")
check(api.headers["content-type"].startswith("application/json") and xp["slug"] in api.text, "/api/posts is JSON (nosniff), never HTML")
js = open(os.path.join(HERE, "static/ownerposts.js")).read()
code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))
check(not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function", code), "static/ownerposts.js never builds HTML from strings (textContent / attributes only)")
check("httpUrl(" in js and re.search(r"httpUrl = function[^\n]*https\?", js), "…and it only links http(s) URLs (httpUrl)")
adm = open(os.path.join(HERE, "ownerposts_admin.py")).read()
check(not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", adm), "the composer's script never builds HTML from strings")
ow("DELETE", "/stats/posts/" + xp["id"], {"confirm": "DELETE"})

print("== the rules: News stays straight, lengths, pins")
for b, what in (({"category": "news", "headline": "Breaking 🔥 news"}, "an emoji in a News headline"),
                ({"category": "news", "headline": "Plain", "body": "Text 👀"}, "an emoji in News text"),
                ({"category": "news", "headline": "Plain", "photos": [{**ph, "credit": "Photo 📸"}]}, "an emoji in a News photo credit"),
                ({"category": "news", "headline": "Plain", "location": "Here ⭐"}, "an emoji in a News location")):
    r = ow("POST", "/stats/posts", b)
    check(r.status_code == 400 and "emoji" in r.json()["error"], f"{what} → 400 ({r.json().get('error')})")
r = ow("POST", "/stats/posts", {"category": "events", "headline": "Fiesta 🎉 tonight", "body": "Come 💃"})
check(r.status_code == 200, "emoji are fine outside News"); ow("DELETE", "/stats/posts/" + r.json()["post"]["id"], {"confirm": "DELETE"})
for b, what in (({**good, "category": "gossip"}, "an unknown category"), ({**good, "headline": "   "}, "no headline"), ({**good, "headline": "x" * 141}, "a 141-character headline"),
                ({**good, "body": "x" * 6001}, "6,001 characters of text"), ({**good, "photos": [ph] * 4}, "4 photos"),
                ({**good, "photos": [{"name": "../../app.py"}]}, "a photo name that's a path"), ({**good, "photos": [{"name": "p/202610/aaaaaaaaaaaa.png"}]}, "a photo that isn't ours (.png)"),
                ({**good, "lat": 95, "lon": 0, "location": "x"}, "a pin off the planet"), ({**good, "lat": 29.5, "lon": -98.4}, "a pin with no location text"),
                ({**good, "pin_hours": 1000}, "a 1,000-hour pin"), ({**good, "pin_hours": -1}, "a negative pin"), ({**good, "status": "deleted"}, "a made-up status"),
                ({**good, "sponsored": "yes"}, "sponsored that isn't true/false")):
    r = ow("POST", "/stats/posts", b)
    check(r.status_code == 400, f"{what} → 400 ({r.status_code} {r.json().get('error', '')[:60]})")
r = ow("POST", "/stats/posts", {**good, "headline": "Ri\u202eght\u200b to left\u0007"})
check(r.status_code == 200 and r.json()["post"]["headline"] == "Right to left", f"bidi / zero-width / control characters are stripped ({r.json()['post']['headline']!r})")
ow("DELETE", "/stats/posts/" + r.json()["post"]["id"], {"confirm": "DELETE"})
big = ow("POST", "/stats/posts", {**good, "body": "x" * 70000})
check(big.status_code == 413, f"a 70 KB post body → 413 ({big.status_code})")
sl = OP.slugify("Man stabbed outside DeeWillie's BBQ on O'Connor Road; suspect still at large")
check(OP.SLUG_RX.match(sl) and sl.startswith("man-stabbed-outside-deewillies-bbq-on-oconnor-road") and len(sl) <= 65, f"slugs: readable, cut at a word ({sl})")

# ------------------------------------------------------------------ uploads + EXIF
print("== uploads: type and size limits")
for raw, mime, what in ((b"GIF89a" + b"\x00" * 200, "image/gif", "a GIF"), (b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>", "image/svg+xml", "an SVG"),
                        (b"<html><script>alert(1)</script></html>", "image/jpeg", "HTML labeled image/jpeg"), (b"\x00\x00\x00\x18ftypheic" + b"\x00" * 400, "image/jpeg", "HEIC"),
                        (b"\xff\xd8\xff\xe0" + b"garbage" * 50, "image/jpeg", "a broken JPEG"), (jpeg(32, 32), "image/jpeg", "a 32 px image")):
    r = upload(raw, mime)
    check(r.status_code == 415, f"{what} → 415 ({r.status_code} {r.json().get('error', '')[:50]})")
check("HEIC" in upload(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 400).json()["error"], "HEIC gets a plain-English hint")
r = ow("POST", "/stats/posts/photo", {"data": "data:image/jpeg;base64," + "A" * (9 * 1024 * 1024 * 4 // 3)})
check(r.status_code == 413, f"a 9 MB photo → 413 ({r.status_code})")
r = owner.post("/stats/posts/photo", content=b'{"data":"' + b"A" * (13 * 1024 * 1024) + b'"}', headers=SAME)
check(r.status_code == 413, f"a 13 MB request → 413 before it's parsed ({r.status_code})")
bomb = io.BytesIO(); Image.new("1", (10000, 6000)).save(bomb, "PNG"); bomb = bomb.getvalue()
r = upload(bomb, "image/png")
check(r.status_code == 413 and len(bomb) < 200000, f"a 60-megapixel PNG bomb ({len(bomb) // 1024} KB file) → 413 ({r.status_code})")
files_before = sum(len(f) for _, _, f in os.walk(f"{tmp}/posts/media"))

print("== EXIF / GPS / XMP are stripped")
src = Image.new("RGB", (2400, 1600), (255, 26, 127))
ex = Image.Exif(); ex[0x010F] = "SecretCam"; ex[0x0110] = "SecretModel"; ex[0x0132] = "2026:10:02 20:04:00"
ex[0x8825] = {1: "N", 2: (29.0, 32.0, 58.56), 3: "W", 4: (98.0, 22.0, 32.88)}
xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><exif:GPSLatitude>29,32.976N SECRETXMP</exif:GPSLatitude></rdf:RDF></x:xmpmeta>'
b = io.BytesIO(); src.save(b, "JPEG", quality=90, exif=ex, comment=b"SECRETCOMMENT", xmp=xmp); raw = b.getvalue()
pre = Image.open(io.BytesIO(raw)).getexif()
check(pre.get_ifd(0x8825).get(2) and b"SECRETXMP" in raw and b"SECRETCOMMENT" in raw and b"SecretCam" in raw, "the test photo really has GPS EXIF, a camera, XMP and a comment")
r = upload(raw)
check(r.status_code == 200, f"…uploads ({r.status_code})")
p1 = r.json()["photo"]; out = media(p1["url"]).content
im = Image.open(io.BytesIO(out))
check(im.format == "WEBP" and max(im.size) == 1600 and (p1["w"], p1["h"]) == im.size, f"stored as WebP, 1600 px on the long edge ({im.format} {im.size})")
check(len(im.getexif()) == 0 and not im.getexif().get_ifd(0x8825) and not any(k in im.info for k in ("exif", "xmp", "icc_profile", "comment")),
      f"no EXIF / GPS IFD / XMP / ICC / comment in the WebP ({sorted(im.info)})")
check(not any(t in out for t in (b"Exif", b"EXIF", b"GPS", b"XMP ", b"xmpmeta", b"SECRET", b"SecretCam", b"ICCP")), "…and none of their bytes are anywhere in the file")
ex2 = Image.Exif(); ex2[0x0112] = 6
r = upload(jpeg(300, 200, exif=ex2))
check(r.status_code == 200 and (r.json()["photo"]["w"], r.json()["photo"]["h"]) == (200, 300), f"a sideways phone photo (Orientation 6) is turned upright ({r.json()['photo']['w']}×{r.json()['photo']['h']})")
from PIL.PngImagePlugin import PngInfo
pi = PngInfo(); pi.add_text("GPSLatitude", "29.5496 SECRETPNG"); pi.add_text("Comment", "SECRETPNG")
b = io.BytesIO(); Image.new("RGBA", (300, 300), (0, 201, 205, 128)).save(b, "PNG", pnginfo=pi)
r = upload(b.getvalue(), "image/png"); out = media(r.json()["photo"]["url"]).content
check(r.status_code == 200 and b"SECRETPNG" not in out and Image.open(io.BytesIO(out)).mode == "RGB", "PNG text chunks are gone; transparency goes on white")
w = io.BytesIO(); Image.new("RGB", (500, 500), (0, 0, 0)).save(w, "WEBP", exif=ex); r = upload(w.getvalue(), "image/webp")
check(r.status_code == 200 and b"SecretCam" not in media(r.json()["photo"]["url"]).content, "a WebP with EXIF: re-encoded clean")
check(media("/api/posts/media/p/202610/..%2F..%2Fposts.db").status_code == 404 and media("/api/posts/media/../posts.db").status_code in (404, 400)
      and media("/api/posts/media/p/202610/aaaaaaaaaaaa.webp").status_code == 404, "the media route only serves our own file names (no paths)")
mh = media(p1["url"]).headers
check(mh["content-type"] == "image/webp" and mh.get("x-content-type-options") == "nosniff", "photos are served as image/webp, nosniff")

# ------------------------------------------------------------------ visibility, pins, edit, delete
print("== drafts are the owner's only; pins; edit; delete")
OP.bust()
d = ow("POST", "/stats/posts", {**good, "headline": "A secret draft", "status": "draft", "photos": [p1]}).json()["post"]
check(d["slug"] not in visitor.get("/api/posts").text, "a draft isn't in /api/posts")
check(visitor.get("/api/posts/" + d["slug"]).status_code == 404 and visitor.get("/p/" + d["slug"]).status_code == 404, "…nor at /api/posts/<slug> or /p/<slug> (404)")
check(any(x["id"] == d["id"] for x in ow("GET", "/stats/posts/list").json()["posts"]), "the owner sees it in the list")
r = ow("PATCH", "/stats/posts/" + d["id"], {"status": "published"})
check(r.status_code == 200 and visitor.get("/p/" + d["slug"]).status_code == 200 and d["slug"] in visitor.get("/api/posts").text, "published → it shows up right away (the feed cache is busted)")
check(r.json()["post"]["body"] == "Hello" and r.json()["post"]["photos"][0]["url"] == p1["url"], "an edit that only sends the status keeps the text and photos")
pa = ow("POST", "/stats/posts", {**good, "headline": "Pinned one", "pin_hours": 24}).json()["post"]
time.sleep(1.1)
pb = ow("POST", "/stats/posts", {**good, "headline": "Newer, not pinned"}).json()["post"]
feed = visitor.get("/api/posts").json()["posts"]
check(feed[0]["id"] == pa["id"] and pa["pinned"] and not pb["pinned"], f"a pinned post comes first even when it's older ({[x['headline'] for x in feed[:3]]})")
pu = OP._ts(pa["pinned_until"]) - time.time()
check(23.9 * 3600 < pu <= 24 * 3600 + 5, f"pinned for 24 hours ({pu / 3600:.2f} h)")
later = time.time() + 25 * 3600
st = OP.store(); rows = asyncio.run(st.list())
order = OP.feed_order([OP.public(x, st, later) for x in rows], later)
check(order[0]["id"] == pb["id"] and not any(x["pinned"] for x in order), "25 hours later the pin has expired: newest first again")
r = ow("PATCH", "/stats/posts/" + pa["id"], {"pin_hours": 0})
check(r.status_code == 200 and not r.json()["post"]["pinned"], "unpin (pin_hours 0)")
ph2 = upload(jpeg(500, 400, (255, 106, 11))).json()["photo"]; ph3 = upload(jpeg(500, 400, (75, 31, 158))).json()["photo"]
e = ow("POST", "/stats/posts", {**good, "headline": "Two photos", "photos": [ph2, ph3]}).json()["post"]
r = ow("PATCH", "/stats/posts/" + e["id"], {"photos": [ph3]})
check(r.status_code == 200 and len(r.json()["post"]["photos"]) == 1 and media(ph2["url"]).status_code == 404 and media(ph3["url"]).status_code == 200,
      "editing out a photo deletes its file; the kept one stays")
check(ow("PATCH", "/stats/posts/ffffffffffffffffffffffffffffffff", {"headline": "x"}).status_code == 404, "editing a post that isn't there → 404")
r = ow("DELETE", "/stats/posts/" + e["id"], {})
check(r.status_code == 400, f"delete without {{\"confirm\": \"DELETE\"}} → 400 ({r.status_code})")
real_map = OP.render_map
async def fake_map(lat, lon, ua, **kw):
    b = io.BytesIO(); Image.new("RGB", (640, 320), (200, 200, 200)).save(b, "WEBP"); return b.getvalue()
OP.render_map = fake_map
m = ow("POST", "/stats/posts", {**good, "headline": "With a map", "location": "12100 block of O'Connor Road", "lat": 29.5496, "lon": -98.3758, "photos": [ph3]}).json()["post"]
OP.render_map = real_map
check(m["map_image"] and media(m["map_image"]["url"]).status_code == 200, "a pin draws + stores a static map with the post")
r = ow("DELETE", "/stats/posts/" + m["id"], {"confirm": "DELETE"})
check(r.status_code == 200 and visitor.get("/p/" + m["slug"]).status_code == 404 and media(ph3["url"]).status_code == 404 and media(m["map_image"]["url"]).status_code == 404,
      "delete: the page is gone (404), and so are its photos and map")
check(ow("DELETE", "/stats/posts/" + m["id"], {"confirm": "DELETE"}).status_code == 404, "deleting it again → 404")

# ------------------------------------------------------------------ Paid / Sponsored
print("== Paid / Sponsored: labeled everywhere, independent of the pin, never News")
spp = upload(jpeg(600, 400, (0, 201, 205))).json()["photo"]
r = ow("POST", "/stats/posts", {"category": "events", "headline": "Spotlight: a paid event", "body": "Come out Saturday.", "sponsored": True, "pin_hours": 168, "photos": [spp]})
sp = r.json()["post"]
check(r.status_code == 200 and sp["sponsored"] is True and sp["pinned"], "a paid event spotlight: sponsored + pinned")
pu = OP._ts(sp["pinned_until"]) - time.time()
check(167.9 * 3600 < pu <= 168 * 3600 + 5, f"pinned for a week ({pu / 86400:.2f} days)")
pub = next(x for x in visitor.get("/api/posts").json()["posts"] if x["id"] == sp["id"])
check(pub["sponsored"] is True, "the public API says sponsored (the app shows the label)")
s = scan(visitor.get("/p/" + sp["slug"]).text)
pg_txt = visitor.get("/p/" + sp["slug"]).text
check('<span class="op-spon">Sponsored</span>' in pg_txt, "the post's page shows a Sponsored label")
check(all((s.meta.get(k) or "").startswith("Sponsored · ") for k in ("og:description", "twitter:description", "description")),
      f"og:description, twitter:description and the meta description start with \"Sponsored · \" ({s.meta.get('og:description')!r})")
check(OP.push_payload(pub)["body"].startswith("Sponsored · "), "the notification text says Sponsored too")
check('"op-spon", text: "Sponsored"' in js and "p.sponsored" in js, "the feed card and the in-app sheet draw the Sponsored label (badges())")
r = ow("PATCH", "/stats/posts/" + sp["id"], {"pin_hours": 0})
check(r.status_code == 200 and r.json()["post"]["sponsored"] and not r.json()["post"]["pinned"], "unpinned, it's still labeled Sponsored (independent of the pin)")
r = ow("POST", "/stats/posts", {**good, "headline": "Sponsored, never pinned", "sponsored": True})
check(r.status_code == 200 and r.json()["post"]["sponsored"] and not r.json()["post"]["pinned"], "sponsored without a pin works too")
ow("DELETE", "/stats/posts/" + r.json()["post"]["id"], {"confirm": "DELETE"})
r = ow("PATCH", "/stats/posts/" + sp["id"], {"sponsored": False})
s2 = scan(visitor.get("/p/" + sp["slug"]).text)
check(r.status_code == 200 and not r.json()["post"]["sponsored"] and not (s2.meta.get("og:description") or "").startswith("Sponsored")
      and "op-spon" not in visitor.get("/p/" + sp["slug"]).text, "turned off: the label and the og prefix are gone")
r = ow("POST", "/stats/posts", {"category": "news", "headline": "Paid news", "sponsored": True})
check(r.status_code == 400 and "News" in r.json()["error"], f"a paid post in News → 400 ({r.json().get('error')})")
r = ow("PATCH", "/stats/posts/" + sp["id"], {"category": "news", "sponsored": True})
check(r.status_code == 400, "…and editing a sponsored post into News is refused too")
nonsp = scan(visitor.get("/p/" + pb["slug"]).text)
check(not (nonsp.meta.get("og:description") or "").startswith("Sponsored") and "op-spon" not in visitor.get("/p/" + pb["slug"]).text, "a normal post has no Sponsored label")
check("sponsored" in OP.SupabaseStore.COLS, "the Supabase backend saves the flag")
mig = open(os.path.join(HERE, "supabase/migrations/20261004133000_owner_posts_sponsored.sql")).read()
check("add column if not exists sponsored boolean not null default false" in mig and "not (sponsored and category = 'news')" in mig, "the migration adds the column + the not-in-News check")

# ------------------------------------------------------------------ push
print("== push: not set up → 503; preview; send once")
pv = ow("POST", "/stats/posts/push-preview", {"category": "news", "headline": "Road closed on O'Connor", "body": "Police closed the road.\n\nMore later."}).json()
check(pv["ok"] and pv["enabled"] is False and "VAPID" in pv["why"] and pv["payload"]["title"] == "Road closed on O'Connor", f"preview without VAPID keys: the text + why it can't send ({pv['why'][:50]})")
r = ow("POST", f"/stats/posts/{pb['id']}/push", {"confirm": True})
check(r.status_code == 503 and "set up" in r.json()["error"], f"send without VAPID keys → 503 \"not set up yet\" ({r.status_code})")
sent = []
async def fake_broadcast(payload, **kw):
    sent.append((payload, kw)); return {"total": 3, "sent": 3, "failed": 0, "removed": 0}
real_en, real_bc = push.enabled, push.broadcast
push.enabled, push.broadcast = (lambda: True), fake_broadcast
try:
    check(ow("POST", f"/stats/posts/{pb['id']}/push", {}).status_code == 400, "send without {\"confirm\": true} (no preview) → 400")
    dr = ow("POST", "/stats/posts", {**good, "headline": "Draft push", "status": "draft"}).json()["post"]
    check(ow("POST", f"/stats/posts/{dr['id']}/push", {"confirm": True}).status_code == 409 and not sent, "a draft can't be sent")
    check(visitor.post(f"/stats/posts/{pb['id']}/push", content=json.dumps({"confirm": True}), headers=J).status_code == 401 and not sent, "a visitor can't send")
    r = ow("POST", f"/stats/posts/{pb['id']}/push", {"confirm": True})
    check(r.status_code == 200 and r.json()["sent"] == 3 and len(sent) == 1, f"the owner sends it: {r.json()}")
    pl = sent[0][0]
    check(pl["title"] == pb["headline"] and pl["url"] == f"/?post={pb['slug']}#chisme" and pl["tag"] == "chisme-post-" + pb["slug"], f"payload: headline, opens the post in Chisme ({pl['url']})")
    check(ow("POST", f"/stats/posts/{pb['id']}/push", {"confirm": True}).status_code == 409 and len(sent) == 1, "a second send → 409 (once per post)")
    check(ow("POST", f"/stats/posts/{pb['id']}/push", {"confirm": True, "again": True}).status_code == 200 and len(sent) == 2, "…unless it says {\"again\": true}")
    lst = next(x for x in ow("GET", "/stats/posts/list").json()["posts"] if x["id"] == pb["id"])
    check(bool(lst["push_sent_at"]), "the post remembers it was sent")
    pv = ow("POST", "/stats/posts/push-preview", {**good, "headline": "Preview"}).json()
    check(pv["enabled"] is True and pv["why"] == "" and len(sent) == 2, "with push set up, the preview says how many phones and sends nothing")
finally:
    push.enabled, push.broadcast = real_en, real_bc

# ------------------------------------------------------------------ Supabase backend (mocked)
print("== Supabase backend (mocked PostgREST + Storage)")
URL, KEY = "https://abcdefghijklmnopqrst.supabase.co", "sb_" + "secret_FAKE-test-key-never-leaks"   # a made-up key (split so secret scanners don't flag it)
os.environ.update(SUPABASE_URL=URL, SUPABASE_SERVICE_KEY=KEY)
ROWS, FILES, SEEN = [], {}, []
import uuid
def handler(req: httpx.Request):
    SEEN.append(req)
    u = req.url
    if u.path == "/rest/v1/owner_posts":
        q = dict(u.params)
        def match(r):
            return all(str(r.get(k)) == v[3:] for k, v in q.items() if k in ("id", "slug", "status") and v.startswith("eq."))
        if req.method == "GET":
            rows = sorted([r for r in ROWS if match(r)], key=lambda r: r["created_at"], reverse=True)[: int(q.get("limit", 60))]
            return httpx.Response(200, json=rows)
        if req.method == "POST":
            b = json.loads(req.content); now = OP._iso(time.time())
            row = {**b, "id": str(uuid.uuid4()), "created_at": now, "updated_at": now}; ROWS.append(row); return httpx.Response(201, json=[row])
        if req.method == "PATCH":
            b = json.loads(req.content); out = []
            for r in ROWS:
                if match(r): r.update(b); out.append(r)
            return httpx.Response(200, json=out)
        if req.method == "DELETE":
            gone = [r for r in ROWS if match(r)]; [ROWS.remove(r) for r in gone]; return httpx.Response(200, json=gone)
    if u.path.startswith("/storage/v1/object/owner-posts/") and req.method == "POST":
        FILES[u.path.split("/owner-posts/", 1)[1]] = req.content; return httpx.Response(200, json={"Key": "x"})
    if u.path == "/storage/v1/object/owner-posts" and req.method == "DELETE":
        for n in json.loads(req.content)["prefixes"]: FILES.pop(n, None)
        return httpx.Response(200, json=[])
    return httpx.Response(404, json={"message": "no"})
mock = OP.SupabaseStore(URL, KEY, "owner-posts", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
mock._want = ("supabase", URL, KEY, "owner-posts")
OP._store = mock; OP.bust()
check(OP.store() is mock and OP.storage_status() == {"backend": "supabase", "durable": True, "supabase_url": True, "supabase_key": True}, "SUPABASE_URL + SUPABASE_SERVICE_KEY → the Supabase backend (durable)")
up = upload(jpeg(800, 600)); sph = up.json()["photo"]
check(up.status_code == 200 and sph["url"].startswith(URL + "/storage/v1/object/public/owner-posts/p/") and sph["name"] in FILES, "photos go to the owner-posts bucket; the page links the public URL")
put = [q for q in SEEN if q.method == "POST" and "/storage/" in q.url.path][-1]
check(put.headers["content-type"] == "image/webp" and put.headers["apikey"] == KEY and "authorization" not in put.headers, "upload: image/webp, the sb_secret key in apikey only (not a JWT, so no Bearer)")
r1 = ow("POST", "/stats/posts", {"category": "weather", "headline": "Storms tonight", "body": "Heavy rain after 9 p.m.", "photos": [sph], "sponsored": False})
r2 = ow("POST", "/stats/posts", {**good, "headline": "A Supabase draft", "status": "draft"})
check(r1.status_code == 200 and r2.status_code == 200 and len(ROWS) == 2, "create → an insert into owner_posts")
pubs = visitor.get("/api/posts").json()["posts"]
check([x["headline"] for x in pubs] == ["Storms tonight"], "the public feed asks for status=eq.published only")
gets = [q for q in SEEN if q.method == "GET" and q.url.path == "/rest/v1/owner_posts"]
check(any(q.url.params.get("status") == "eq.published" for q in gets), "…in the PostgREST query (RLS also enforces it for the anon key)")
check(visitor.get("/p/" + r2.json()["post"]["slug"]).status_code == 404 and visitor.get("/p/" + r1.json()["post"]["slug"]).status_code == 200, "the draft's page is 404, the published one renders")
e1 = ow("PATCH", "/stats/posts/" + r1.json()["post"]["id"], {"headline": "Storms tonight, then sun"})
check(e1.status_code == 200 and ROWS[0]["headline"] == "Storms tonight, then sun", "edit → a PATCH id=eq.<uuid>")
d1 = ow("DELETE", "/stats/posts/" + r1.json()["post"]["id"], {"confirm": "DELETE"})
check(d1.status_code == 200 and len(ROWS) == 1 and sph["name"] not in FILES, "delete → the row and its photo in the bucket")
everything = "".join([visitor.get("/api/posts").text, owner.get("/stats/posts").text, owner.get("/stats").text, ow("GET", "/stats/posts/list").text,
                      visitor.get("/").text, visitor.get("/static/ownerposts.js").text, visitor.get("/static/sw.js").text])
check(KEY not in everything and "sb_secret" not in everything and "service_role" not in everything, "the secret key never reaches a page, the API or the app's files")
leg = OP.SupabaseStore(URL, "eyJhbGciOiJIUzI1NiJ9.x.y", "owner-posts")
check(leg._h().get("Authorization") == "Bearer eyJhbGciOiJIUzI1NiJ9.x.y" and leg._h()["apikey"].startswith("eyJ"), "a legacy service_role JWT also goes in Authorization")
def boom(req): return httpx.Response(500, json={"message": "secret detail " + KEY})
OP._store = OP.SupabaseStore(URL, KEY, "owner-posts", client=httpx.AsyncClient(transport=httpx.MockTransport(boom))); OP._store._want = mock._want; OP.bust()
f5 = visitor.get("/api/posts"); c5 = ow("POST", "/stats/posts", good)
check(f5.status_code == 503 and c5.status_code == 503 and KEY not in f5.text + c5.text and "secret detail" not in f5.text + c5.text, "Supabase down: 503 with a plain message (no key, no echo)")
for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"): os.environ.pop(k)
os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"] = "https://evil.example.com", KEY
check(OP.supabase_conf()[0] == "", "a SUPABASE_URL that isn't https://<project>.supabase.co is ignored (local storage)")
for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"): os.environ.pop(k)
OP._store = None; OP.bust()
check(OP.store().name == "local", "no Supabase env → back to local storage")

# ------------------------------------------------------------------ the static map
print("== the static map (OpenStreetMap tiles, mocked)")
reqs = []
def tile(color):
    b = io.BytesIO(); Image.new("RGB", (256, 256), color).save(b, "PNG"); return b.getvalue()
def tile4(cols):
    im = Image.new("RGB", (256, 256))
    for i, c in enumerate(cols): im.paste(c, ((i % 2) * 128, (i // 2) * 128, (i % 2) * 128 + 128, (i // 2) * 128 + 128))
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
OSM = [(247, 250, 191), (252, 214, 164), (242, 239, 233), (255, 222, 23)]   # OSM carto: secondary road, primary road, land, a pure yellow
def tiles(req):
    reqs.append(req); return httpx.Response(200, content=tile4(OSM))
os.environ["OWNER_POSTS_STATIC_MAP"] = "1"
async def mp(handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "Chisme test"}) as c:
        return await OP.render_map(29.5496, -98.3758, "Chisme test", client=c)
img = asyncio.run(mp(tiles))
mi = Image.open(io.BytesIO(img)).convert("RGB")
def yellowish(px):
    r, g, b = [v / 255 for v in px]; mx, mn = max(r, g, b), min(r, g, b); l = (mx + mn) / 2; dd = mx - mn
    if dd < 0.05: return False
    s = dd / (1 - abs(2 * l - 1)) if l not in (0, 1) else 0
    if s < 0.3: return False
    h = (60 * (((g - b) / dd) % 6) if mx == r else 60 * ((b - r) / dd + 2) if mx == g else 60 * ((r - g) / dd + 4)) % 360
    return 38 <= h <= 70 or (25 <= h < 38 and (l >= 0.85 or l <= 0.2))
data = list(mi.get_flattened_data()) if hasattr(mi, "get_flattened_data") else list(mi.getdata())
yl = sum(1 for p in data[::7] if yellowish(p))
check(mi.size == (640, 320) and yl == 0, f"a 640×320 map; OSM's yellow roads come out silver: {yl} yellow pixels (news_no_yellow_test's rule)")
check(any(abs(p[0] - 255) < 8 and abs(p[1] - 26) < 8 and abs(p[2] - 127) < 8 for p in [mi.getpixel((320 + dx, 320 // 2 + dy)) for dx in range(-8, 9) for dy in range(-8, 9)]), "a pink pin in the middle")
check(reqs and all(q.url.host == "tile.openstreetmap.org" and re.match(r"^/16/\d+/\d+\.png$", q.url.path) for q in reqs) and len(reqs) <= 9, f"{len(reqs)} OSM tiles at zoom 16 (light use, drawn once per post)")
tq = OP.no_yellow(Image.new("RGB", (4, 4), (0, 201, 205))).getpixel((0, 0))
check(abs(tq[0] - 0) < 6 and abs(tq[1] - 201) < 6 and abs(tq[2] - 205) < 6, f"turquoise stays turquoise ({tq})")
check(asyncio.run(mp(lambda q: httpx.Response(500))) is None, "a tile error → no map (the post still saves)")
os.environ["OWNER_POSTS_STATIC_MAP"] = "0"
check(asyncio.run(mp(tiles)) is None, "OWNER_POSTS_STATIC_MAP=0 turns it off")
check("© OpenStreetMap contributors" in open(os.path.join(HERE, "ownerposts.py")).read(), "the OSM credit is drawn on the map (and under it on the page)")

# ------------------------------------------------------------------ shipping bits
print("== shipping: Dockerfile, requirements, service worker, render.yaml")
df = open(os.path.join(HERE, "Dockerfile")).read(); rq = open(os.path.join(HERE, "requirements.txt")).read()
sw = open(os.path.join(HERE, "static/sw.js")).read(); ry = open(os.path.join(HERE, "render.yaml")).read()
check("ownerposts.py" in df and "ownerposts_admin.py" in df and re.search(r"(?im)^pillow", rq), "the Dockerfile copies both modules; Pillow is in requirements.txt")
check("/static/ownerposts.js" in sw and "/static/ownerposts.css" in sw and 'startsWith("/p/")' in sw, "the service worker caches the new files and leaves /p/ pages to the network")
check(re.search(r"SUPABASE_SERVICE_KEY\s*\n\s*sync: false", ry) and "sb_secret_" not in ry.replace("sb_secret_…", "") and KEY not in ry, "render.yaml names SUPABASE_URL / SUPABASE_SERVICE_KEY (sync: false), no secret in the repo")
print("PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
