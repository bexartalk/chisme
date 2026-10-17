"""Offline creator avatar regression checks; all upstream HTTP uses MockTransport."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

_tmp = tempfile.TemporaryDirectory(prefix="chisme-avatars-")
for key in list(os.environ):
    if key.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_")):
        os.environ.pop(key)
os.environ.update(SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=_tmp.name + "/social",
                  PUSH_STORE_FILE=_tmp.name + "/push.json", STATS_STORE_FILE=_tmp.name + "/stats.json",
                  OWNER_POSTS_DIR=_tmp.name + "/posts", AUTO_PUSH_WAKE_DELAY="9999")
import httpx
from fastapi.testclient import TestClient
import app as A

fails = 0

def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what)
    fails += not ok

URL = "https://www.youtube.com/@eatmigos"
IMAGE = "https://yt3.googleusercontent.com/paBYSV=s176-c-k-c0x00ffffff-no-rj"
HTML = '<meta property="og:image" content="https://yt3.googleusercontent.com/paBYSV=s900-c-k-c0x00ffffff-no-rj">'

async def parsing():
    calls = []
    body = [HTML]
    def upstream(req):
        calls.append(req)
        return httpx.Response(200, text=body[0])
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as mock:
        with patch.object(A, "client", return_value=mock):
            check(await A._yt_avatar_url(URL) == IMAGE, "channel og:image is resized to s176")
            check(calls[-1].headers['accept-language'] == 'en-US', "browser headers")
            for bad in ('https://evil.test/', 'https://www.youtube.com.evil.test/@eatmigos', 'http://www.youtube.com/@eatmigos'):
                before = len(calls)
                check(await A._yt_avatar_url(bad) is None and len(calls) == before, "reject channel " + bad)
            body[0] = '<meta content="https://evil.test/photo.jpg" property="og:image">'
            check(await A._yt_avatar_url(URL) is None, "reject non-yt3 image")
            body[0] = '<html>No avatar</html>'
            check(await A._yt_avatar_url(URL) is None, "missing metadata")
            body[0] = '<link href="https://yt3.ggpht.com/a=s88-c" itemprop="thumbnailUrl">'
            check(await A._yt_avatar_url(URL) == 'https://yt3.ggpht.com/a=s176-c-k-c0x00ffffff-no-rj', "thumbnail fallback")

asyncio.run(parsing())
counts = {"page": 0, "image": 0}
mode = ["ok"]
def upstream(req):
    if req.url.host == "www.youtube.com":
        counts["page"] += 1
        return httpx.Response(200, text=HTML)
    if req.url.host == "yt3.googleusercontent.com":
        counts["image"] += 1
        return httpx.Response(200, content=b"jpeg-avatar" if mode[0] != "large" else b'x' * (300 * 1024 + 1),
                              headers={"content-type": "text/html" if mode[0] == "type" else "image/jpeg"})
    raise AssertionError("Unexpected network request: " + str(req.url))

mock = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
with patch.object(A, "client", return_value=mock), patch.object(A.autopush, "kick"):
    A._cache.clear(); A._locks.clear()
    # uvloop also works in restricted sandboxes where asyncio thread wakeups stall.
    tc = TestClient(A.app, backend_options={"use_uvloop": importlib.util.find_spec("uvloop") is not None})
    r = tc.get('/api/creator-avatar/eatmigos')
    check(r.status_code == 200 and r.content == b'jpeg-avatar' and r.headers.get('content-type') == 'image/jpeg', "avatar endpoint returns JPEG bytes")
    check(r.headers.get('cache-control') == 'public, max-age=604800', "seven-day browser cache")
    r = tc.get('/api/creator-avatar/eatmigos')
    check(r.status_code == 200 and counts == {"page": 1, "image": 1}, "second call uses cached URL and bytes")
    for slug in ('unknown', 'sanantoniomunchies'):
        check(tc.get('/api/creator-avatar/' + slug).status_code == 404, slug + ' returns 404')
    for bad in ('large', 'type'):
        mode[0] = bad
        A._cache.pop('ytavatarimg:eatmigos', None)
        check(tc.get('/api/creator-avatar/eatmigos').status_code == 404, 'reject image ' + bad)
asyncio.run(mock.aclose())

async def metadata():
    A._cache.clear(); A._locks.clear()
    calls = []
    async def resolve(url):
        calls.append(url)
        return IMAGE
    with patch.object(A, '_yt_avatar_url', side_effect=resolve):
        creators = await A.creators_with_avatars()
    check(all(c['slug'] and c['initial'] for c in creators), 'every creator has slug and initial')
    check(all(c['avatar'] == ('/api/creator-avatar/' + c['slug'] if c['youtube'] else None) for c in creators), 'only YouTube creators have avatar paths')
    A._cache.clear()
    async def failure(url):
        calls.append(url)
        return None
    with patch.object(A, '_yt_avatar_url', side_effect=failure):
        before = len(calls)
        check(await A._cached_yt_avatar(URL) is None and await A._cached_yt_avatar(URL) is None and len(calls) == before + 1, 'failed resolution cached')
        A._cache['ytavatar:' + URL] = (A.time.time() - 6 * 3600 - 1, None)
        await A._cached_yt_avatar(URL)
        check(len(calls) == before + 2, 'failure retried after six hours')
asyncio.run(metadata())
js = Path('static/app.js').read_text().split('function renderCrew(', 1)[1].split('function renderFood(', 1)[0]
css = Path('static/style.css').read_text()
check('class: "crew-av"' in js and 'crew-initial' in js and 'photo.onerror' in js and 'replaceChildren(fallback())' in js, 'crew avatar and initial error fallback')
check('.crew-av{' in css and 'width:56px;height:56px' in css and 'html[data-season="muertos"] .crew-av' in css, '56px avatar and Muertos ring CSS')
sys.exit(1 if fails else 0)
