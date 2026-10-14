"""v49.23 profile photo: Goonie's upload went to Storage but never attached (the edit page only saved it on 'Save profile').
Now the photo saves the moment it uploads. A real photo (a Commons JPEG of Mission San Juan, from static/places) is
picked on Edit profile at 390 px; no Save tap; the profile shows it after a reload. Starts its own server on PORT (8487).
Screenshot: SHOTS (default /workspace/chisme-v49-23-shots)/profile-photo-390.png"""
import asyncio, io, json, os, re, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pw_csp  # noqa: F401
from PIL import Image
from playwright.async_api import async_playwright
PORT = int(os.environ.get("PORT", "8487")); SHOTS = os.environ.get("SHOTS", "/workspace/chisme-v49-23-shots"); os.makedirs(SHOTS, exist_ok=True)
fails = 0
def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what); fails += 0 if ok else 1
USER = "photo_goonie"


def start():
    tmp = tempfile.mkdtemp(prefix="chisme-avatar-")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_", "UPLOADS_"))}
    env.update(SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=f"{tmp}/social", SIGNUPS_PUBLIC="1", NEW_USER_REVIEW="0", PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json",
               AUTO_PUSH_WAKE_DELAY="9999", OWNER_POSTS_DIR=f"{tmp}/posts", PYTHONUNBUFFERED="1", SOCIAL_UPLOAD_TESTERS=USER)
    log = f"{tmp}/server.log"
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(PORT)], cwd=HERE, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{PORT}/"
    for _ in range(120):
        try:
            if urllib.request.urlopen(url + "healthz", timeout=2).status == 200: return proc, url, log
        except Exception: pass
        time.sleep(0.5)
    proc.kill(); raise RuntimeError(log)


INIT = ("try{localStorage.setItem('chisme-location-setup','done');localStorage.setItem('chisme-default-tab','chisme');localStorage.setItem('chisme-season-pin','off');"
        "localStorage.setItem('chisme-notif',JSON.stringify({n:1,shows:1}));localStorage.setItem('chisme-a2hs',JSON.stringify({done:true}));localStorage.setItem('chisme-settings-tip','test:0')}catch(e){}")


async def main():
    proc, url, log = start()
    jpg = os.path.join(tempfile.mkdtemp(), "mission.jpg")
    Image.open(os.path.join(HERE, "static/places/mission-san-juan.webp")).convert("RGB").save(jpg, "JPEG", quality=90)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            await ctx.add_init_script(INIT); pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
            await pg.goto(url)
            cfg = await (await pg.request.get(url + "api/social/config")).json(); a, c = map(int, re.findall(r"\d+", cfg["challenge"]["question"])); await asyncio.sleep(3)
            H = {"origin": url.rstrip("/"), "content-type": "application/json"}; em = USER + "@example.com"
            await pg.request.post(url + "api/social/signup", headers=H, data=json.dumps({"email": em, "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": "Goonie",
                "username": USER, "birthday": "1990-05-05", "tos": True, "challenge": {"id": cfg["challenge"]["id"], "answer": str(a + c)}}))
            await asyncio.sleep(1); code = re.findall(r"code for " + re.escape(em) + r": (\S+)", open(log).read())[-1]
            await pg.request.post(url + "api/social/verify", headers=H, data=json.dumps({"email": em, "code": code}))
            await pg.goto(url + "?in=1#s/edit"); await pg.wait_for_function("document.querySelector('.av-edit')", timeout=20000)
            accept = await pg.evaluate("document.querySelector('#pick-avatar').accept")
            check("image/heic" in accept and "image/jpeg" in accept, f"the picker takes iPhone HEIC + JPEG ({accept})")
            await pg.set_input_files("#pick-avatar", jpg); await pg.wait_for_function("(document.querySelector('#sx-toast')||{}).textContent==='Photo saved 😎'", timeout=15000)
            check(True, "a real photo uploads and says 'Photo saved 😎'")
            me = (await (await pg.request.get(url + "api/social/me")).json())["me"]
            check(bool(me.get("photo")), "…saved on the profile without tapping Save profile")
            r = await pg.request.get(url + me["photo"].lstrip("/")); im = Image.open(io.BytesIO(await r.body()))
            check(r.status == 200 and im.format == "WEBP" and max(im.size) <= 512, f"…served as a resized WebP {im.format} {im.size}")
            await pg.goto(url + "?in=1#s/me"); await pg.wait_for_timeout(3000)
            check(await pg.evaluate("[...document.querySelectorAll('.av img')].some(i => i.naturalWidth > 0)"), "…and shows on the profile after a reload")
            await pg.screenshot(path=f"{SHOTS}/profile-photo-390.png")
            check(not errs, f"no page errors {errs[:2]}")
            await b.close()
    finally:
        proc.terminate()
    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL(S)'}"); sys.exit(1 if fails else 0)


asyncio.run(main())
