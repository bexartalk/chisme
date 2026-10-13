"""v49.22 the sign-up nudge ("Join the Metiches"): signed-out phones get a sheet after NUDGE.first ms of active use, 'Not
now' lets them browse, a 2nd after NUDGE.again more, never a 3rd that visit, and later visits the same day get none.
It waits while a video / the feed / a game is up, doesn't count hidden time, never shows on the sign-in screens, to
signed-in people, on desktop, or when sign-ups are closed (SIGNUPS_PUBLIC unset). Timings shortened via window.__CHISME_NUDGE.
Starts its own servers on PORT (default 8481, sign-ups open) and PORT+1 (sign-ups closed).
Screenshot: SHOTS (default /workspace/chisme-navswap-shots)/nudge-390.png"""
import asyncio, json, os, re, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pw_csp  # noqa: F401
from playwright.async_api import async_playwright

PORT = int(os.environ.get("PORT", "8481"))
SHOTS = os.environ.get("SHOTS", "/workspace/chisme-navswap-shots"); os.makedirs(SHOTS, exist_ok=True)
fails = 0
def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what)
    if not ok: fails += 1


def start(port, public):
    tmp = tempfile.mkdtemp(prefix="chisme-nudge-")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_", "SIGNUPS_"))}
    env.update(SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=f"{tmp}/social", NEW_USER_REVIEW="0", PUSH_STORE_FILE=f"{tmp}/push.json", STATS_STORE_FILE=f"{tmp}/stats.json",
               AUTO_PUSH_WAKE_DELAY="9999", OWNER_POSTS_DIR=f"{tmp}/posts", PYTHONUNBUFFERED="1", **({"SIGNUPS_PUBLIC": "1"} if public else {}))
    log = f"{tmp}/server.log"
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=HERE, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/"
    for _ in range(120):
        try:
            if urllib.request.urlopen(url + "healthz", timeout=2).status == 200: return proc, url, log
        except Exception: pass
        time.sleep(0.5)
    proc.kill(); raise RuntimeError("server didn't start: " + log)


FAST = "window.__CHISME_NUDGE={first:3000,again:4000,tick:250};"
INIT = ("try{localStorage.setItem('chisme-location-setup','done');localStorage.setItem('chisme-default-tab','chisme');localStorage.setItem('chisme-season-pin','off');"
        "localStorage.setItem('chisme-notif',JSON.stringify({n:1,shows:1}));localStorage.setItem('chisme-a2hs',JSON.stringify({done:true}));localStorage.setItem('chisme-settings-tip','test:0')}catch(e){}")
SHOWN = "() => !document.querySelector('#sheet').hidden && document.querySelector('#sheet').classList.contains('is-nudge')"
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)


async def ctx_page(b, url, extra="", **kw):
    ctx = await b.new_context(**(kw or PHONE)); await ctx.add_init_script(FAST + INIT + extra)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    await pg.goto(url + "#chisme"); await pg.wait_for_function("window.__chisme && __chisme.ready && window.__chismeNudge", timeout=30000)
    return ctx, pg, errs


async def main():
    s1, url, log = start(PORT, True); s2, url2, _ = start(PORT + 1, False)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            # ---- the happy path: 1st nudge, Not now, 2nd nudge, then no more this visit
            ctx, pg, errs = await ctx_page(b, url)
            st = await pg.evaluate("[window.__chismeNudge.state().active, !document.querySelector('#sheet').hidden]")
            check(st[0] < 3000 and not st[1] or st[0] >= 3000, f"no nudge before the first wait is up {st}")
            await pg.wait_for_function(SHOWN, timeout=8000)
            s = await pg.evaluate("""() => { const sh = document.querySelector('#sheet'), r = sh.querySelector('.sheet-card').getBoundingClientRect();
              return { title: document.querySelector('#sheet-title').textContent, body: document.querySelector('#sheet-body').textContent,
                join: (document.querySelector('#nudge-join') || {}).textContent, later: (document.querySelector('#nudge-later') || {}).textContent,
                joinBg: getComputedStyle(document.querySelector('#nudge-join')).backgroundColor, fit: r.left >= 0 && r.right <= innerWidth + .5,
                big: [...sh.querySelectorAll('.nudge-btns .btn')].every((x) => x.getBoundingClientRect().height >= 44) }; }""")
            check("Join the Metiches" in s["title"] and all(w in s["body"] for w in ("Like", "Comment", "Save", "Homies")), f"the sheet: 'Join the Metiches' + like / comment / save / Homies ({s['title']!r})")
            check(s["join"] == "Join Chisme" and s["later"] == "Not now" and s["big"] and s["fit"], f"…'Join Chisme' and 'Not now', 44 px+ buttons, fits 390 px ({s['joinBg']})")
            yl = await pg.evaluate("""() => { const out = []; for (const n of document.querySelectorAll('#sheet, #sheet *')) { const cs = getComputedStyle(n);
              for (const k of ['color', 'backgroundColor', 'borderLeftColor']) { const m = (cs[k].match(/[\\d.]+/g) || []).map(Number); if (m.length < 3 || m[3] === 0) continue;
                let [r, g, bb] = m.map((x) => x / 255), mx = Math.max(r, g, bb), mn = Math.min(r, g, bb); if (mx - mn < .25 || mx < .5) continue;
                let h = mx === r ? 60 * (((g - bb) / (mx - mn)) % 6) : mx === g ? 60 * ((bb - r) / (mx - mn) + 2) : 60 * ((r - g) / (mx - mn) + 4); h = (h + 360) % 360;
                if (h > 42 && h < 70) out.push(n.className + ' ' + k); } } return out; }""")
            check(not yl, f"…no yellow {yl[:3]}")
            await pg.wait_for_timeout(400); await pg.screenshot(path=f"{SHOTS}/nudge-390.png")
            check(await pg.evaluate("JSON.parse(localStorage.getItem('chisme-nudge')).day === new Date().toLocaleDateString('en-CA')"), "today's nudge is remembered (localStorage chisme-nudge)")
            await pg.click("#nudge-later"); await pg.wait_for_timeout(300)
            check(not await pg.evaluate(SHOWN) and not await pg.evaluate("document.body.classList.contains('sx-locked')"), "'Not now' closes it and the page scrolls freely")
            await pg.wait_for_timeout(1500)
            check(not await pg.evaluate(SHOWN), "…and it doesn't come straight back")
            await pg.wait_for_function(SHOWN, timeout=8000); check(True, "the 2nd nudge comes after the longer wait")
            await pg.click("#nudge-later"); await pg.wait_for_timeout(9000)
            check(not await pg.evaluate(SHOWN), "never a 3rd nudge in the same visit")
            # ---- same phone, a new visit the same day: none
            pg2 = await ctx.new_page(); await pg2.goto(url + "#chisme"); await pg2.wait_for_function("window.__chismeNudge", timeout=30000); await pg2.wait_for_timeout(6000)
            check(not await pg2.evaluate(SHOWN), "a new visit the same day: no nudge (once a day after the first visit)")
            await pg2.evaluate("localStorage.setItem('chisme-nudge', JSON.stringify({ day: '2026-01-01' }))")
            await pg2.reload(); await pg2.wait_for_function(SHOWN, timeout=10000); check(True, "a new day: it may ask again")
            check(not errs, f"no page errors {errs[:2]}")
            await ctx.close()
            # ---- waits while the video feed / a playing video is up
            ctx, pg, _ = await ctx_page(b, url)
            await pg.evaluate("document.documentElement.classList.add('feed-open')"); await pg.wait_for_timeout(5000)
            check(not await pg.evaluate(SHOWN), "never over the open video feed / reels")
            await pg.evaluate("""() => { document.documentElement.classList.remove('feed-open'); const v = document.createElement('video'); v.id = 'tv';
              Object.defineProperty(v, 'paused', { get: () => !!window.__pausedV }); document.body.append(v); }""")
            await pg.wait_for_timeout(1500); check(not await pg.evaluate(SHOWN), "never while a video plays")
            await pg.evaluate("window.__pausedV = true"); await pg.wait_for_function(SHOWN, timeout=5000); check(True, "…it shows once the video is paused")
            await pg.click("#nudge-join"); await pg.wait_for_timeout(1200)
            j = await pg.evaluate("[location.hash, !!document.querySelector('#sx-view input[type=password]'), document.querySelector('#sheet').hidden]")
            check(j[0] == "#s/signup" and j[1] and j[2], f"'Join Chisme' opens the join form {j}")
            await ctx.close()
            # ---- hidden time doesn't count
            ctx, pg, _ = await ctx_page(b, url, "Object.defineProperty(document,'visibilityState',{get:()=>window.__vis||'hidden'});")
            await pg.wait_for_timeout(5000); check(not await pg.evaluate(SHOWN), "time with the app in the background doesn't count")
            a = await pg.evaluate("window.__chismeNudge.state().active"); check(a == 0, f"…(active time stays {a})")
            await pg.evaluate("window.__vis = 'visible'"); await pg.wait_for_function(SHOWN, timeout=6000); check(True, "…and counts once it's visible")
            await ctx.close()
            # ---- the sign-in screens
            ctx, pg, _ = await ctx_page(b, url); await pg.evaluate("location.hash = '#s/signin'"); await pg.wait_for_timeout(5000)
            check(not await pg.evaluate(SHOWN), "never on the sign-in / join screens"); await ctx.close()
            # ---- signed in
            ctx, pg, _ = await ctx_page(b, url)
            cfg = await (await pg.request.get(url + "api/social/config")).json(); x, y = map(int, re.findall(r"\d+", cfg["challenge"]["question"])); await asyncio.sleep(3)
            H = {"origin": url.rstrip("/"), "content-type": "application/json"}; em = "nudge_me@example.com"
            await pg.request.post(url + "api/social/signup", headers=H, data=json.dumps({"email": em, "password": "Tamales&Tea42", "password2": "Tamales&Tea42", "display_name": "Nudge",
                "username": "nudge_me", "birthday": "1990-05-05", "tos": True, "challenge": {"id": cfg["challenge"]["id"], "answer": str(x + y)}}))
            await asyncio.sleep(1); code = re.findall(r"code for " + re.escape(em) + r": (\S+)", open(log).read())[-1]
            await pg.request.post(url + "api/social/verify", headers=H, data=json.dumps({"email": em, "code": code}))
            await pg.goto(url + "?in=1#chisme"); await pg.wait_for_function("window.__chismeNudge", timeout=30000); await pg.wait_for_timeout(6000)
            check(not await pg.evaluate(SHOWN), "never to signed-in people"); await ctx.close()
            # ---- sign-ups closed for this visitor
            ctx, pg, _ = await ctx_page(b, url2); await pg.wait_for_timeout(6000)
            check(not await pg.evaluate(SHOWN), "sign-ups closed (SIGNUPS_PUBLIC unset): no nudge"); await ctx.close()
            # ---- desktop
            ctx, pg, _ = await ctx_page(b, url, viewport={"width": 1280, "height": 800}); await pg.wait_for_timeout(6000)
            check(not await pg.evaluate(SHOWN), "desktop: no nudge (phones / the app only)"); await ctx.close()
            await b.close()
    finally:
        s1.terminate(); s2.terminate()
    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL(S)'}"); sys.exit(1 if fails else 0)


asyncio.run(main())
