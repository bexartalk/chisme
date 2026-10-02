"""v49.10 "🔄 Refresh everyone now" (owner button on /stats → every open Chisme reloads to the newest version).
  • GET /api/refresh is tiny (≈10 bytes), no-cache + ETag (304 when unchanged); the service worker never caches it
  • only the owner can push: no cookie, a forged cookie, or a non-JSON post → 401; /stats shows the card, a confirm sheet
    (Cancel changes nothing), then "Last pushed: just now" and a new token
  • an open app (not in a game) sees the new token → "Tía has fresh chisme, refreshing…" → reloads, with the new token as its baseline
  • mid-Juan-run (running or paused) it only offers a "Refresh" pill and keeps the run; leaving the game → it reloads
Screenshots: screenshots/admin-refresh.png, screenshots/refresh-toast.png.
OWNER_URL (default :8212) = a local server started with ADMIN_TOKEN=$OWNER_TOKEN (its own PUSH_STORE_FILE)."""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
URL = os.environ.get("OWNER_URL", "http://localhost:8212")
TOKEN = os.environ.get("OWNER_TOKEN", "")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
G = "__chisme.juegos.game"
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

async def ctx_of(b, p):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}
    ctx = await b.new_context(**dev); await ctx.add_init_script(SETUP); await ctx.add_init_script(QUIET); return ctx

async def token(ctx):
    r = await ctx.request.get(URL + "/api/refresh"); return (await r.json())["t"]

async def app_page(ctx, hash_=""):
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: None if "access control" in str(e) else errs.append(str(e)[:200]))
    await pg.goto(URL + "/" + hash_); await pg.wait_for_function("window.__chisme && __chisme.ready && window.__chismeRefresh && __chismeRefresh.base !== null", timeout=120000)
    await pg.evaluate("window.__same = 1"); return pg, errs

async def main():
    assert TOKEN, "set OWNER_TOKEN (the ADMIN_TOKEN of the server at OWNER_URL)"
    async with async_playwright() as p:
        b = await p.webkit.launch()
        print("== the token endpoint + who can push")
        anon = await ctx_of(b, p)
        r = await anon.request.get(URL + "/api/refresh"); t0 = (await r.json())["t"]; et = r.headers.get("etag")
        check(r.ok and len(await r.body()) < 40 and r.headers.get("cache-control") == "no-cache" and et, f"GET /api/refresh: {len(await r.body())} bytes, no-cache, ETag {et}")
        r304 = await anon.request.get(URL + "/api/refresh", headers={"If-None-Match": et}); check(r304.status == 304, f"same ETag → 304 ({r304.status})")
        for name, hdr in (("no cookie", {}), ("forged chisme_stats cookie", {"Cookie": "chisme_stats=forged"}), ("forged chisme_admin=1", {"Cookie": "chisme_admin=1"})):
            rr = await anon.request.post(URL + "/stats/refresh", headers={"Content-Type": "application/json", **hdr}, data="{}")
            check(rr.status == 401, f"a regular visitor ({name}) can't push: {rr.status}")
        check(await token(anon) == t0, "…and the token didn't move")

        print("== the owner's /stats card")
        own = await ctx_of(b, p); ap = await own.new_page()
        await ap.goto(f"{URL}/stats?key={TOKEN}"); await ap.wait_for_selector("#rf-go", timeout=30000)
        rr = await own.request.post(URL + "/stats/refresh", headers={"Content-Type": "text/plain"}, data="{}")
        check(rr.status == 401 and await token(anon) == t0, f"signed in but not a JSON post (a cross-site form) → {rr.status}")
        lp = (await ap.text_content("#rf-last")).strip()
        check(lp == "never" if t0 == "0" else bool(lp) and lp != "never", f"Last pushed: {lp}")
        await ap.click("#rf-go"); await ap.wait_for_timeout(300)
        check(await ap.evaluate("document.getElementById('rf-confirm').open"), "🔄 Refresh everyone now → a confirm sheet")
        await ap.click("#rf-no"); await ap.wait_for_timeout(300)
        check(not await ap.evaluate("document.getElementById('rf-confirm').open") and await token(anon) == t0, "Cancel → nothing pushed")

        # an app open on the home screen, and one mid-Juan-run, both loaded before the push
        cli = await ctx_of(b, p); home, e1 = await app_page(cli)
        cli2 = await ctx_of(b, p); game, e2 = await app_page(cli2, "#juan")
        await game.wait_for_function(G + " && " + G + ".skins", timeout=60000)
        await game.click("#juan-ov [data-act=start]"); await game.wait_for_timeout(500)
        check(await game.evaluate(G + ".state.mode") == "run" and await game.evaluate("__chismeRefresh.busy()"), "Juan run going → busy")
        await game.click("#juan-pause"); await game.wait_for_timeout(250)

        await ap.click("#rf-go"); await ap.wait_for_timeout(300); await ap.click("#rf-yes")
        await ap.wait_for_selector("#rf-res.ok", timeout=15000); t1 = await token(anon)
        check(t1 != t0 and (await ap.text_content("#rf-last")).strip() == "just now", f"Yes → pushed: new token ({t0} → {t1}), Last pushed: just now")
        await ap.evaluate("document.getElementById('rf').scrollIntoView({block:'center'})"); await ap.wait_for_timeout(300)
        await ap.screenshot(path=os.path.join(OUT, "admin-refresh.png")); print("  📸 screenshots/admin-refresh.png")
        await ap.goto(URL + "/stats"); await ap.wait_for_selector("#rf-last")
        check((await ap.text_content("#rf-last")).strip() == "just now", "…still shown after reloading /stats (saved in the store)")

        print("== an open app picks it up")
        await home.evaluate("__chismeRefresh.check()")
        await home.wait_for_function("(() => { const t = document.getElementById('update-toast'); return t && !t.hidden && /refreshing/.test(t.textContent); })()", timeout=5000)
        txt = (await home.text_content("#update-toast")).strip()
        await home.screenshot(path=os.path.join(OUT, "refresh-toast.png")); print("  📸 screenshots/refresh-toast.png")
        check(txt.startswith("✨ Tía has fresh chisme, refreshing…"), f"toast: {txt!r}")
        await home.wait_for_function("window.__same === undefined && window.__chismeRefresh && __chismeRefresh.base !== null", timeout=20000)
        b2 = await home.evaluate("__chismeRefresh.base")
        check(b2 == t1 and not await home.evaluate("__chismeRefresh.pending"), f"…reloaded; the new token is its baseline ({b2}), nothing pending (no reload loop)")
        cached = await home.evaluate("(async () => { for (const k of await caches.keys()) { const c = await caches.open(k); if ((await c.keys()).some(r => r.url.includes('/api/refresh'))) return k; } return ''; })()")
        check(not cached, f"the service worker never cached /api/refresh {cached}")

        print("== not mid-game")
        await game.evaluate("__chismeRefresh.check()"); await game.wait_for_timeout(4000)
        st = await game.evaluate("({ same: window.__same, mode: " + G + ".state.mode, t: document.getElementById('update-toast').textContent.trim(), hid: document.getElementById('update-toast').hidden, btn: getComputedStyle(document.getElementById('update-reload')).display })")
        check(st["same"] == 1 and st["mode"] == "paused" and not st["hid"] and "Refresh" in st["t"] and st["btn"] != "none", f"paused Juan run: no reload, a Refresh pill instead ({st})")
        await game.click("#juan-ov [data-act=resume]") if await game.locator("#juan-ov [data-act=resume]").count() else None
        await game.wait_for_timeout(1500)
        check(await game.evaluate("window.__same") == 1, f"…still running ({await game.evaluate(G + '.state.mode')}): still no reload")
        await game.evaluate("document.querySelector('.tab[data-view=news]').click()")   # (full screen hides the tabs; the app's own tab switch)
        await game.wait_for_function("window.__same === undefined && window.__chismeRefresh && __chismeRefresh.base !== null", timeout=20000)
        check(await game.evaluate("__chismeRefresh.base") == t1, "left the game (News tab) → it refreshed")
        check(not e1 and not e2, f"no page errors {e1[:1]} {e2[:1]}")
        await b.close()
    print("PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)

asyncio.run(main())
