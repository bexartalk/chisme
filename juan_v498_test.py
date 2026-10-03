"""v49.8 Juan: 🔄 Start over, the owner's skin unlock, and the "tiny game" re-fit (static/juan.js).
  • Paused + level clear have 🔄 Start over: level 1, score 0; the unlocked skins, the best score (HI) and the Top 10 unlock stay
  • the owner, signed in to /stats on this phone (the high score admin's sign-in), gets all 10 skins; a forged chisme_admin=1
    cookie alone unlocks nothing (the server says no), and signed out (cookies gone) the phone is back to locked
  • the canvas re-fits when its box changes even if the window "resize" event never arrives (or arrives too early): full screen,
    portrait → landscape → portrait with resize events swallowed, it ends up filling the screen again
Screenshot: screenshots/start-over.png (Paused: ▶ Resume, 🔄 Start over, 👕 Skins).
BASE (default :8211) for the game; OWNER_URL (default :8212) = a local server started with ADMIN_TOKEN=$OWNER_TOKEN."""
import asyncio, os, sys
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OWNER_URL = os.environ.get("OWNER_URL", "http://localhost:8212")
TOKEN = os.environ.get("OWNER_TOKEN", "")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
G = "__chisme.juegos.game"
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

async def page(b, p, base, init=""):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}
    ctx = await b.new_context(**dev); await ctx.add_init_script(SETUP + init); await ctx.add_init_script(QUIET)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: None if "access control" in str(e) else errs.append(str(e)[:200]))
    await pg.goto(base + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000)
    await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 60); }"); await pg.wait_for_timeout(300)
    return ctx, pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        print("== 🔄 Start over")
        ctx, pg, errs = await page(b, p, BASE, "if (!localStorage.getItem('chisme-juan-top10')) { localStorage.setItem('chisme-juan-top10', JSON.stringify({ at: 1, rank: 3 })); localStorage.setItem('chisme-juegos-juan', JSON.stringify({ best: 9100, levelMax: 4, wins: 0, skin: 'vice', v6: 1 })); }")
        await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
        await pg.evaluate(G + ".warp(3, 2300)"); await pg.wait_for_timeout(1500); await pg.click("#juan-pause"); await pg.wait_for_timeout(250)
        s0 = await pg.evaluate(G + ".state"); btns = await pg.evaluate("[...document.querySelectorAll('#juan-ov button')].map(b => b.textContent.trim())")
        check(s0["mode"] == "paused" and btns[:2] == ["▶ Resume", "🔄 Start over"] and "👕 Skins" in btns, f"Paused (level {s0['level']}, score {s0['score']}): {btns}")
        await pg.screenshot(path=os.path.join(OUT, "start-over.png"))
        await pg.click("#juan-ov [data-act=over]"); await pg.wait_for_timeout(600)
        s = await pg.evaluate(G + ".state"); keep = await pg.evaluate("[localStorage.getItem('chisme-juan-top10'), JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{}').best]")
        check(s["mode"] == "run" and s["level"] == 1 and s["score"] == 0 and s["x"] < 400, f"Start over → level 1 from the start, score 0 (level {s['level']}, score {s['score']}, x {s['x']:.0f})")
        check(keep[0] and keep[1] >= 9100 and s["best"] >= 9100 and await pg.evaluate(G + ".skins.unlocked") and s["skin"] == "mariachi", f"…the skins stay unlocked (still wearing the saved 'vice', now its v49.12 redesign Mariachi Neón), the best score stays ({s['best']})")
        await pg.evaluate(G + ".warp(1, 5700)"); await pg.wait_for_function(G + ".state.mode === 'clear'", timeout=20000); await pg.wait_for_timeout(200)
        check(await pg.locator("#juan-ov [data-act=over]").count() == 1 and await pg.locator("#juan-ov [data-act=next]").count() == 1, "level clear: ▶ next level + 🔄 Start over")
        sc = (await pg.evaluate(G + ".state"))["score"]; await pg.click("#juan-ov [data-act=over]"); await pg.wait_for_timeout(1500)
        sheet = await pg.locator("dialog.juan-hs-sheet[open]").count()
        if sheet:   # 500+ made the board: its "New high score!" sheet comes first, and the game waits for it
            w = await pg.evaluate(G + ".state.mode"); await pg.click("dialog.juan-hs-sheet .juan-hs-skip"); await pg.wait_for_timeout(600)
            check(w == "clear", f"a score that makes the Top 10 ({sc}) gets its sheet first; the game waits ({w})")
        s = await pg.evaluate(G + ".state")
        check(s["level"] == 1 and s["mode"] == "run" and s["score"] == 0 and not errs, f"…then level 1 again, score 0 (sheet {'shown' if sheet else 'not needed'}) {errs[:1]}")

        print("== the canvas re-fits (no lost resize events)")
        # swallow every window resize (as if it fired too early / never came): only the box watching can fix it
        await pg.evaluate("window.addEventListener('resize', (e) => e.stopImmediatePropagation(), true)")
        a = await pg.evaluate(f"({{ w: {G}.state.cssW, fs: {G}.state.fullscreen, box: document.querySelector('.juan-wrap').offsetWidth }})")
        await pg.set_viewport_size({"width": 844, "height": 390}); await pg.wait_for_timeout(900)
        l = await pg.evaluate(f"({{ w: {G}.state.cssW, box: document.querySelector('.juan-wrap').offsetHeight }})")
        await pg.set_viewport_size({"width": 390, "height": 844}); await pg.wait_for_timeout(1200)
        z = await pg.evaluate(f"({{ w: {G}.state.cssW, box: document.querySelector('.juan-wrap').offsetWidth, back: {G}.state.backing, dpr: {G}.state.dpr }})")
        check(a["fs"] and abs(a["w"] - a["box"]) <= 1, f"full screen, portrait: the game is as wide as its box ({a['w']} of {a['box']})")
        check(l["w"] < 300, f"landscape: pillar-boxed to the short side ({l['w']}px wide, box {l['box']}px tall)")
        check(abs(z["w"] - z["box"]) <= 1 and z["w"] >= 380 and abs(z["back"][0] - round(z["w"] * z["dpr"])) <= 1, f"back to portrait, with no resize event: it fills its box again ({z['w']} of {z['box']}, backing {z['back']})")
        await ctx.close()

        print("== the owner gets every skin (the /stats sign-in)")
        if not TOKEN:
            check(False, "OWNER_TOKEN is set (a local server on OWNER_URL started with ADMIN_TOKEN=$OWNER_TOKEN)")
        else:
            ctx, pg, errs = await page(b, p, OWNER_URL)
            await ctx.add_cookies([{"name": "chisme_admin", "value": "1", "url": OWNER_URL}]); await pg.reload()
            await pg.wait_for_function(G + " && " + G + ".skins", timeout=120000); await pg.wait_for_timeout(1500)
            check(not await pg.evaluate(G + ".skins.unlocked") and not await pg.evaluate(G + ".skins.owner"), "a forged chisme_admin=1 cookie alone: still locked (the server says no)")
            await pw_csp.admin_sign_in(pg, OWNER_URL, TOKEN)
            await pg.goto(OWNER_URL + "/#juan"); await pg.wait_for_function(G + " && " + G + ".skins && " + G + ".skins.owner", timeout=30000)
            await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 60); }"); await pg.wait_for_timeout(400)
            txt = await pg.text_content("#juan-ov [data-act=skins]")
            await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]")
            m = await pg.evaluate("() => { const d = document.querySelector('dialog.juan-skins[open]'); return { sub: d.querySelector('.juan-sk-sub').textContent, n: d.querySelectorAll('.juan-sk').length, locked: d.querySelectorAll('.juan-sk.locked').length }; }")
            check(await pg.evaluate(G + ".skins.unlocked") and "🔒" not in txt and m["n"] == 10 and m["locked"] == 0 and m["sub"].startswith("👑"), f"signed in to /stats: all {m['n']} skins open ({txt.strip()!r}, {m['sub']!r})")
            await pg.click("dialog.juan-skins .juan-sk[data-skin=largo]"); await pg.click("dialog.juan-skins .juan-sk-done")
            check(await pg.evaluate(G + ".skins.now") == "largo" and not await pg.evaluate("localStorage.getItem('chisme-juan-top10')"), "…the owner can wear any (Juan Largo), and nothing is written to the Top 10 unlock")
            await ctx.clear_cookies(); await pg.reload(); await pg.wait_for_function(G + " && " + G + ".skins", timeout=120000); await pg.wait_for_timeout(800)
            check(not await pg.evaluate(G + ".skins.unlocked") and await pg.evaluate(G + ".skins.now") == "classic" and not errs, f"signed out: back to locked, Classic Juan {errs[:1]}")
            await ctx.close()
        await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
