"""v49.15.x Juan: the owner's GOD MODE (for play-testing every stage and hunting bugs).
  • HTTP: GET /stats/juan/god.js (the panel's code) is 401 without the /stats sign-in (no cookie, a forged chisme_admin=1
    marker, a made-up session cookie), 404 on a server with no ADMIN_TOKEN, 200 + no-store only for the owner; the panel code is
    not in /static (juan.js only has the switches) and the service worker never caches it; POST /api/juan/scores with
    god: true is refused and the board doesn't change
  • not the owner: no ⚡ God button, no panel, god mode off, even with ?god=1 in the URL, god keys in localStorage and a forged
    chisme_admin=1 cookie (that one asks the server, gets 401, and nothing happens)
  • the owner (signed in on /stats): ⚡ God → Immortal (bumps cost no health, agents never catch him), Fly, Noclip, Speed,
    Jump to a level; the GOD MODE badge; a god-mode run never saves a best score, never opens the Top 10 sheet and never
    POSTs a score (leaving full screen, a level clear, the win); turned off + Start over = a real run again
  • the native app (window.ChismeNative, or a ChismeNative user agent): no request for the panel, no button, even for the
    signed-in owner; GET /stats/juan/god.js with a ChismeNative user agent is 404 even with the owner's key
Screenshots: screenshots/godmode-panel.png, screenshots/godmode-play.png.
CHISME_URL (default :8211) = a server with no ADMIN_TOKEN; OWNER_URL (default :8212) = a local server started with
ADMIN_TOKEN=$OWNER_TOKEN. JUAN_GOD_ENGINE=webkit|chromium (default webkit: the owner plays on an iPhone)."""
import asyncio, json, os, sys, urllib.error, urllib.request
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pw_csp  # noqa: F401  (CSP-safe wait_for_function + admin_sign_in)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211").rstrip("/")
OWNER_URL = os.environ.get("OWNER_URL", "http://localhost:8212").rstrip("/")
TOKEN = os.environ.get("OWNER_TOKEN", "")
ENGINE = os.environ.get("JUAN_GOD_ENGINE", "webkit")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
G = "__chisme.juegos.game"
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

def http(url, method="GET", headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=json.dumps(body).encode() if body is not None else None)
    if body is not None: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e: return e.code, dict(e.headers), e.read().decode("utf-8", "replace")

async def page(b, p, base, init="", url="/#juan", cookies=None, ua=None):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}
    if ua: dev["user_agent"] = dev["user_agent"] + " " + ua
    if ENGINE != "webkit": dev.pop("is_mobile", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(SETUP + init); await ctx.add_init_script(QUIET)
    if cookies: await ctx.add_cookies(cookies)
    pg = await ctx.new_page(); errs, god_req, posts = [], [], []
    pg.on("pageerror", lambda e: None if "access control" in str(e) else errs.append(str(e)[:200]))
    pg.on("request", lambda r: god_req.append(r.url) if "/stats/juan/god.js" in r.url else (posts.append(r.post_data) if r.method == "POST" and "/api/juan/scores" in r.url else None))
    if url is not None:
        await pg.goto(base + url); await pg.wait_for_function(f"window.__chisme && __chisme.ready && {G} && {G}.skins", timeout=120000); await pg.wait_for_timeout(1500)
    return ctx, pg, errs, god_req, posts

async def no_god(pg, what):
    s = await pg.evaluate(f"({{ btn: !!document.querySelector('#juan-god'), panel: {G}.state.godPanel, god: {G}.state.god, mod: typeof window.ChismeJuanGod, css: !!document.getElementById('juan-god-css') }})")
    check(not s["btn"] and not s["panel"] and not s["god"] and s["mod"] == "undefined" and not s["css"], f"{what}: no ⚡ God button, no panel, god mode off {s}")

async def main():
    print("== HTTP: the panel's code is the owner's only")
    st, h, body = http(OWNER_URL + "/stats/juan/god.js")
    check(st == 401 and "ChismeJuanGod" not in body, f"no sign-in → {st}")
    st, h, body = http(OWNER_URL + "/stats/juan/god.js", headers={"Cookie": "chisme_admin=1"})
    check(st == 401 and "ChismeJuanGod" not in body, f"a forged chisme_admin=1 marker → {st}")
    st, h, body = http(OWNER_URL + "/stats/juan/god.js", headers={"Cookie": "chisme_admin=1; chisme_stats=made-up-session"})
    check(st == 401 and "ChismeJuanGod" not in body, f"a made-up session cookie → {st}")
    st, h, body = http(BASE + "/stats/juan/god.js")
    check(st == 404 and "ChismeJuanGod" not in body, f"a server with no ADMIN_TOKEN → {st}")
    if TOKEN:
        st, h, body = http(OWNER_URL + "/stats/juan/god.js", headers={"Authorization": "Bearer " + TOKEN})
        hl = {k.lower(): v for k, v in h.items()}
        check(st == 200 and "ChismeJuanGod" in body and "javascript" in hl.get("content-type", "") and "no-store" in hl.get("cache-control", ""), f"the owner's key (Bearer, like the other /api/juan admin calls) → {st} {hl.get('content-type')} {hl.get('cache-control')}")
        st, h, body = http(OWNER_URL + "/stats/juan/god.js", headers={"Authorization": "Bearer " + TOKEN, "User-Agent": "Mozilla/5.0 (iPhone) ChismeNative/1.0"})
        check(st == 404 and "ChismeJuanGod" not in body, f"the owner's key from the native app (ChismeNative user agent) → {st}")
    for u in ("/static/juan_god.js", "/static/../private/juan_god.js", "/private/juan_god.js"):
        st, h, body = http(BASE + u); check("ChismeJuanGod" not in body, f"{u} → {st}, no panel code")
    js = http(BASE + "/static/juan.js")[2]; sw = http(BASE + "/sw.js")[2]
    check("ChismeJuanGod" in js and "Jump to a level" not in js and "juan-god-card" not in js and "/stats/juan/god.js" in js, "juan.js has the switches and the loader, not the panel")
    check("god.js" not in sw and "url.pathname.startsWith(\"/stats/\")" in sw, "the service worker never caches /stats/ (the panel isn't precached)")
    before = http(OWNER_URL + "/api/juan/scores?n=50")[2]
    st, _, body = http(OWNER_URL + "/api/juan/scores", "POST", body={"name": "GodTest", "score": 500, "level": 1, "t": 1, "god": True})
    after = http(OWNER_URL + "/api/juan/scores?n=50")[2]
    check(st == 400 and "GodTest" not in after and json.loads(before)["scores"] == json.loads(after)["scores"], f"POST a score with god: true → {st}, the board is unchanged")

    async with async_playwright() as p:
        b = await getattr(p, ENGINE).launch()
        print(f"== not the owner ({ENGINE})")
        ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, url="/?god=1&godmode=1#juan")
        await no_god(pg, "?god=1 in the URL"); check(not god_req, f"…and no request for the panel ({len(god_req)})"); await ctx.close()
        ls = "localStorage.setItem('chisme-juan-god','1'); localStorage.setItem('god','1'); localStorage.setItem('godmode','true'); localStorage.setItem('chisme-juegos-juan', JSON.stringify({ best: 0, levelMax: 7, v6: 1, god: true }));"
        ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, init=ls, url="/?god=1#juan")
        await no_god(pg, "god keys in localStorage"); check(not god_req, f"…and no request for the panel ({len(god_req)})"); await ctx.close()
        ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, init=ls, url="/?god=1#juan", cookies=[{"name": "chisme_admin", "value": "1", "url": OWNER_URL}])
        await no_god(pg, "a forged chisme_admin=1 cookie (+ URL + localStorage)")
        check(len(god_req) >= 1, f"…which asks the server once and gets told no ({len(god_req)} request)")
        check(not errs, f"no page errors {errs[:2]}"); await ctx.close()

        if not TOKEN:
            check(False, "OWNER_TOKEN is set (a local server on OWNER_URL started with ADMIN_TOKEN=$OWNER_TOKEN)")
        else:
            print(f"== the owner ({ENGINE})")
            ctx, pg, errs, god_req, posts = await page(b, p, OWNER_URL, url=None)
            await pw_csp.admin_sign_in(pg, OWNER_URL, TOKEN)
            await pg.goto(OWNER_URL + "/#juan"); await pg.wait_for_function(f"window.__chisme && __chisme.ready && {G} && {G}.skins", timeout=120000)
            await pg.wait_for_function(f"{G}.state.godPanel", timeout=30000)
            best0 = await pg.evaluate(f"{G}.state.best")
            check(await pg.locator("#juan-god").count() == 1 and not await pg.evaluate(f"{G}.state.god"), "signed in: the ⚡ God button is there, god mode starts off")
            await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(400)
            await pg.click("#juan-god"); await pg.wait_for_selector("dialog.juan-god[open]")
            m = await pg.evaluate(f"{G}.state.mode")
            n_lv = await pg.locator("dialog.juan-god [data-lv]").count()
            check(m == "paused" and n_lv == 7, f"⚡ God opens the panel and pauses the game ({m}); 7 levels to jump to ({n_lv})")
            await pg.click("dialog.juan-god input[data-k=on]"); await pg.wait_for_timeout(200)
            await pg.screenshot(path=os.path.join(OUT, "godmode-panel.png"))
            await pg.click("dialog.juan-god .juan-god-done"); await pg.wait_for_timeout(300)
            s = await pg.evaluate(f"{G}.state")
            badge = await pg.evaluate("(() => { const b = document.querySelector('.juan-god-badge'); return b && getComputedStyle(b).display !== 'none' ? b.textContent : null; })()")
            check(s["god"] and s["godRun"] and s["mode"] == "run" and badge and "GOD MODE" in badge, f"Immortal on: god mode on, this run is marked, the badge shows ({badge!r})")
            # immortal: run level 2 (the most agents) with no jumps at all
            await pg.click("#juan-god"); await pg.click("dialog.juan-god [data-lv='2']"); await pg.wait_for_timeout(300)
            s = await pg.evaluate(f"{G}.state"); check(s["level"] == 2 and s["mode"] == "run" and s["god"], f"Jump to a level → level {s['level']} ({s['name']}), running, still god mode")
            await pg.evaluate(f"{G}.warp(2, 560)"); hp, caught = 100, 0
            for _ in range(28):
                await pg.wait_for_timeout(250); s = await pg.evaluate(f"{G}.state"); hp = min(hp, s["health"]); caught = max(caught, s["caught"])
            check(hp == 100 and caught == 0 and s["mode"] == "run", f"7 s through La Chamba without a single jump: health {hp}, caught {caught}, still running at x {s['x']:.0f}")
            await pg.screenshot(path=os.path.join(OUT, "godmode-play.png"))
            # fly + noclip + speed
            await pg.click("#juan-god"); await pg.click("dialog.juan-god input[data-k=fly]"); await pg.click("dialog.juan-god [data-speed='2']"); await pg.click("dialog.juan-god .juan-god-done")
            await pg.evaluate(f"{G}.jump()")
            try: await pg.wait_for_function(f"{G}.state.y < -300", timeout=6000)
            except Exception: pass
            y1 = await pg.evaluate(f"{G}.state.y")
            check(y1 < -300, f"Fly: holding Jump lifts him high ({y1:.0f}, the ground is −88)")
            await pg.click("#juan-god"); await pg.click("dialog.juan-god input[data-k=fly]"); await pg.click("dialog.juan-god input[data-k=noclip]"); await pg.click("dialog.juan-god .juan-god-done")
            suv = await pg.evaluate(f"{G}.ents().filter(e => e.t === 'suv' || e.t === 'pallet').map(e => e.x)")
            x0 = suv[0] - 120 if suv else 1000
            await pg.evaluate(f"{G}.warp({G}.state.level, {x0})"); await pg.wait_for_timeout(1800); x1 = await pg.evaluate(f"{G}.state.x")
            check(x1 > x0 + 300, f"Noclip at 2×: straight through the {('pallet/SUV at ' + str(round(suv[0]))) if suv else 'road'} without a jump ({x0:.0f} → {x1:.0f})")
            # no score from a god-mode run: offer(), leaving full screen, the win
            check(not await pg.evaluate(f"{G}.hs.offer(99000, 7)"), "the Top 10 offer says no in a god-mode run")
            await pg.evaluate(f"{G}.exitFullscreen()"); await pg.wait_for_timeout(1500)
            sheet = await pg.locator("dialog.juan-hs-sheet").count()
            await pg.evaluate(f"{G}.resume()"); await pg.click("#juan-god"); await pg.click("dialog.juan-god [data-lv='7']"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"{G}.warp(7, 5700)"); await pg.wait_for_function(f"{G}.state.mode === 'win'", timeout=30000); await pg.wait_for_timeout(2600)
            s = await pg.evaluate(f"{G}.state"); sheet += await pg.locator("dialog.juan-hs-sheet").count()
            saved = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{}')")
            check(s["mode"] == "win" and sheet == 0 and not posts, f"god-mode win ({s['score']} pts) + leaving full screen: no Top 10 sheet ({sheet}), no score POSTed ({len(posts)})")
            check(s["best"] == best0 and (saved.get("best") or 0) == best0 and (saved.get("levelMax") or 1) == 1, f"…and nothing saved on the phone: best {s['best']} (was {best0}), levelMax {saved.get('levelMax')}")
            # off + Start over = a real run again
            await pg.click("#juan-ov [data-act=again]"); await pg.wait_for_timeout(300)
            await pg.click("#juan-god"); await pg.click("dialog.juan-god .juan-god-off"); await pg.wait_for_timeout(300)
            mid = await pg.evaluate(f"[{G}.state.god, {G}.state.godRun]")
            await pg.click("#juan-pause"); await pg.click("#juan-ov [data-act=over]"); await pg.wait_for_timeout(600)
            s = await pg.evaluate(f"{G}.state"); badge = await pg.evaluate("getComputedStyle(document.querySelector('.juan-god-badge')).display")
            check(mid == [False, True] and not s["god"] and not s["godRun"] and s["level"] == 1 and badge == "none", f"turned off: the run stays marked until 🔄 Start over ({mid}), then a real run (god {s['god']}, marked {s['godRun']}, badge {badge})")
            check(not errs, f"no page errors {errs[:2]}")
            signed_in = await ctx.cookies()   # one sign-in per run (the /stats sign-in allows a few tries per 15 min)
            await ctx.close()

            print(f"== the native app ({ENGINE})")
            ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, init="window.ChismeNative = { platform: 'ios' };", url=None, cookies=signed_in)
            await pg.goto(OWNER_URL + "/#juan"); await pg.wait_for_function(f"window.__chisme && __chisme.ready && {G} && {G}.skins", timeout=120000); await pg.wait_for_timeout(2500)
            await no_god(pg, "window.ChismeNative, signed in as the owner"); check(not god_req, f"…and the panel is never even asked for ({len(god_req)})")
            await ctx.close()
            ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, url=None, cookies=signed_in, ua="ChismeNative/1.0")
            await pg.goto(OWNER_URL + "/#juan"); await pg.wait_for_function(f"window.__chisme && __chisme.ready && {G} && {G}.skins", timeout=120000); await pg.wait_for_timeout(2500)
            await no_god(pg, "a ChismeNative user agent (no window flag), signed in as the owner"); check(not god_req, f"…and the panel is never even asked for ({len(god_req)})")
            await ctx.close()
            print("== signed out")
            ctx, pg, errs, god_req, _ = await page(b, p, OWNER_URL, url=None, cookies=signed_in)
            await pg.goto(OWNER_URL + "/#juan"); await pg.wait_for_function(f"{G} && {G}.state.godPanel", timeout=120000)
            check(True, "(the saved sign-in still opens the panel)"); await ctx.clear_cookies()
            await pg.reload(); await pg.wait_for_function(f"window.__chisme && __chisme.ready && {G} && {G}.skins", timeout=120000); await pg.wait_for_timeout(1500)
            await no_god(pg, "signed out (cookies gone)"); await ctx.close()
        await b.close()
    print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)

asyncio.run(main())
