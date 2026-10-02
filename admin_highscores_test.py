"""v49.5: the owner's 🏆 Juan High Scores manager on /stats + the score endpoints.
  • public: POST /api/juan/scores trims the name and keeps 12 characters (no word filter); GET returns the top 10
  • v49.5 sanity check: scores the game can't give are refused (over levels 1..L's maximum, re-counted here from juan.js's
    seeded levels; not a multiple of 5; a level that doesn't exist)
  • owner only (the /stats sign-in): GET /stats/juan/scores, DELETE + PATCH /api/juan/scores/{id} (+ /stats/juan/...
    aliases that get the cookie), POST .../clear {confirm:"CLEAR"}; without the cookie or the Bearer ADMIN_TOKEN → 401
  • the page (WebKit iPhone 13, 390 + 320 px): a folded "🏆 Juan High Scores" section listing every score best first,
    rename + Save, Delete (tap twice), Clear the board (confirm sheet) → empty; 44 px+ buttons, no sideways scroll
Screenshot: screenshots/admin-highscores.png. Seeds the local server's file store (JUAN_SCORES_FILE, default
/tmp/chisme-juan-scores.json), so run it against a local server only (CHISME_URL, default http://localhost:8211)."""
import asyncio, json, os, time
import httpx
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
FILE = os.environ.get("JUAN_SCORES_FILE", "/tmp/chisme-juan-scores.json")
env = dict(os.environ)
if os.environ.get("CHISME_ENV"):
    for line in open(os.environ["CHISME_ENV"]):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1); env[k] = v.strip().strip('"\'')
TOKEN = env["ADMIN_TOKEN"]
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

SEED = [("Goonie", 12340, 6), ("La Tía", 10125, 6), ("Juanito", 7450, 5), ("Ictunis", 5800, 4), ("Mija", 3950, 3), ("Compa", 1650, 1)]   # v49.5: real, possible scores
def seed():
    now = int(time.time())
    json.dump({f"seed{i}": {"name": n, "score": sc, "level": lv, "t": now - i * 3600} for i, (n, sc, lv) in enumerate(SEED)}, open(FILE, "w"))

async def main():
    global fails
    print("== the endpoints")
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        open(FILE, "w").write("{}")
        r = (await c.post("/api/juan/scores", json={"name": "   pinche   cabrón chingón ", "score": 775, "level": 2}, headers={"X-Forwarded-For": "10.9.9.1"})).json()
        check(r["ok"] and r["entry"]["name"] == "pinche cabró", f"name trimmed + cut to 12 characters, no word filter ({r['entry']['name']!r})")
        r2 = (await c.post("/api/juan/scores", json={"name": "", "score": 5, "level": 1}, headers={"X-Forwarded-For": "10.9.9.1"})).json()
        check(r2["ok"] and r2["entry"]["name"] == "Juan", "an empty name → Juan")
        bad = await c.post("/api/juan/scores", json={"name": "x", "score": -3}, headers={"X-Forwarded-For": "10.9.9.1"})
        check(bad.status_code == 400, "a bad score is refused (400)")
        top = (await c.get("/api/juan/scores")).json()["scores"]
        check([t["score"] for t in top] == [775, 5] and set(top[0]) == {"id", "name", "score", "level", "t"}, "GET /api/juan/scores: best first")
        sid = r["id"]
        for m, path, body in [("DELETE", f"/api/juan/scores/{sid}", None), ("PATCH", f"/api/juan/scores/{sid}", {"name": "x"}), ("POST", "/api/juan/scores/clear", {"confirm": "CLEAR"}),
                              ("GET", "/stats/juan/scores", None), ("DELETE", f"/stats/juan/scores/{sid}", None)]:
            rr = await c.request(m, path, json=body)
            check(rr.status_code == 401, f"{m} {path} without the owner sign-in → 401")
        rr = await c.request("DELETE", f"/api/juan/scores/{sid}", headers={"Authorization": "Bearer wrong-token"})
        check(rr.status_code == 401, "a wrong Bearer token → 401")
        H = {"Authorization": f"Bearer {TOKEN}"}
        rr = await c.patch(f"/api/juan/scores/{sid}", json={"name": "  Pinche   Juan  12345678 "}, headers=H)
        check(rr.status_code == 200 and rr.json()["score"]["name"] == "Pinche Juan", f"PATCH with the owner token renames (trim + 12) ({rr.json().get('score', {}).get('name')!r})")
        rr = await c.delete(f"/api/juan/scores/{sid}", headers=H); check(rr.status_code == 200 and rr.json()["ok"], "DELETE with the owner token deletes")
        rr = await c.delete(f"/api/juan/scores/{sid}", headers=H); check(rr.status_code == 404, "deleting it again → 404")
        rr = await c.post("/api/juan/scores/clear", json={}, headers=H); check(rr.status_code == 400, "clear without confirm → 400")
        rr = await c.post("/api/juan/scores/clear", json={"confirm": "CLEAR"}, headers=H); check(rr.status_code == 200 and rr.json()["cleared"] == 1, "clear with confirm CLEAR empties the board")
        # v49.5 sanity check: impossible scores for the game are refused
        import juanscores, subprocess
        js = "const J=require(%r);const o=[];for(let n=1;n<=J.LEVELS.length;n++){let s=500;for(const e of J.buildLevel(n)){const t=e.t;s+=t==='concha'?10:t==='beer'?15:['coffee','taco','flipflops'].includes(t)?50:t==='agent'?150:t==='suv'?300:J.HAZ[t]?25:0;}o.push(s);}console.log(JSON.stringify(o))" % os.path.join(HERE, "static", "juan.js")
        game = json.loads(subprocess.check_output(["node", "-e", js]))
        check(len(game) == juanscores.LEVELS and all(g <= t for g, t in zip(game, juanscores.LEVEL_PTS)), f"the server's per-level maximum covers everything the game's levels can give ({game} ≤ {list(juanscores.LEVEL_PTS)})")
        mx = (await c.get("/api/juan/scores")).json().get("max")
        check(mx == juanscores.SCORE_MAX == juanscores.MAX_BY_LEVEL[-1] and 12000 < mx < 20000, f"GET says the highest possible score ({mx})")
        cases = [({"score": juanscores.MAX_BY_LEVEL[0] + 5, "level": 1}, 400, "more than level 1 can give"), ({"score": mx + 5, "level": 6}, 400, "more than the whole game can give"),
                 ({"score": 1003, "level": 3}, 400, "not a multiple of 5"), ({"score": 500, "level": 7}, 400, "a level that doesn't exist"), ({"score": 10_000_000, "level": 6}, 400, "a silly big number"),
                 ({"score": mx, "level": 6}, 200, "the very best possible run (all 6 levels)"), ({"score": juanscores.MAX_BY_LEVEL[0], "level": 1}, 200, "the best possible level-1 run")]
        for i, (body, want, what) in enumerate(cases):
            rr = await c.post("/api/juan/scores", json={"name": "Test", **body}, headers={"X-Forwarded-For": f"10.9.8.{i}"})
            check(rr.status_code == want, f"sanity check: {what} ({body['score']} on level {body['level']}) → {rr.status_code}")
        await c.post("/api/juan/scores/clear", json={"confirm": "CLEAR"}, headers=H)
    seed()
    async with async_playwright() as p:
        b = await p.webkit.launch(); errs = []
        for width in (390, 320):
            print(f"== the admin page ({width} px)")
            dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": width, "height": 844 if width == 390 else 640}; dev["device_scale_factor"] = 2
            ctx = await b.new_context(**dev); pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            await pg.goto(f"{BASE}/stats?key={TOKEN}"); await pg.wait_for_selector("#f-scores")
            summ = await pg.text_content("#f-scores summary")
            check("🏆 Juan High Scores" in summ and "6 scores" in summ and not await pg.evaluate("document.querySelector('#f-scores').open"), f"a folded '🏆 Juan High Scores' section ({summ.strip()!r})")
            await pg.click("#f-scores summary"); await pg.wait_for_timeout(300)
            rows = await pg.evaluate("[...document.querySelectorAll('#hs-list .hs-row')].map(li => [li.querySelector('.hs-name').value, li.querySelector('.hs-meta b').textContent])")
            check([r[0] for r in rows] == [n for n, _, _ in SEED] and rows[0][1] == "12,340", f"every score, best first ({rows[:3]})")
            sz = await pg.evaluate("""() => ({ small: [...document.querySelectorAll('#f-scores button, #f-scores input')].filter(e => e.offsetParent && e.getBoundingClientRect().height < 44).map(e => e.className),
                wide: document.documentElement.scrollWidth - innerWidth, max: document.querySelector('.hs-name').maxLength })""")
            check(not sz["small"] and sz["wide"] <= 0 and sz["max"] == 12, f"{width}: 44 px+ buttons, no sideways scroll, names max 12 ({sz})")
            if width == 390:
                await pg.evaluate("document.querySelector('#f-scores').scrollIntoView({block: 'start'}); scrollBy(0, -70)"); await pg.wait_for_timeout(300)
                await pg.screenshot(path=os.path.join(OUT, "admin-highscores.png"))
                # rename #2
                await pg.fill("#hs-list .hs-row:nth-child(2) .hs-name", "Tía Chismosa and more")   # the field stops at 12
                await pg.click("#hs-list .hs-row:nth-child(2) .hs-save"); await pg.wait_for_timeout(700)
                v = await pg.input_value("#hs-list .hs-row:nth-child(2) .hs-name"); t = await pg.text_content("#toast")
                async with httpx.AsyncClient(base_url=BASE) as c:
                    allr = (await c.get("/stats/juan/scores", headers={"Authorization": f"Bearer {TOKEN}"})).json()["scores"]
                check(v == "Tía Chismosa" and "Saved" in t and allr[1]["name"] == "Tía Chismosa", f"rename + Save: saved on the server, trimmed to 12 ({v!r}, toast {t!r})")
                # delete #4 (two taps)
                await pg.click("#hs-list .hs-row:nth-child(4) .hs-del"); await pg.wait_for_timeout(200)
                armed = await pg.text_content("#hs-list .hs-row:nth-child(4) .hs-del")
                n_before = await pg.evaluate("document.querySelectorAll('#hs-list .hs-row').length")
                check(armed == "Tap again" and n_before == 6, "Delete asks for a second tap (nothing deleted yet)")
                await pg.click("#hs-list .hs-row:nth-child(4) .hs-del"); await pg.wait_for_timeout(700)
                names = await pg.evaluate("[...document.querySelectorAll('#hs-list .hs-name')].map(i => i.value)")
                async with httpx.AsyncClient(base_url=BASE) as c:
                    left = [r["name"] for r in (await c.get("/api/juan/scores")).json()["scores"]]
                check("Ictunis" not in names and "Ictunis" not in left and len(left) == 5 and "5 scores" in await pg.text_content("#f-scores summary"), f"second tap deletes it (page + server: {left})")
                # clear the board
                await pg.click("#hs-clear"); await pg.wait_for_timeout(300)
                check(await pg.evaluate("document.querySelector('#hs-confirm').open") and "5 scores" in await pg.text_content("#hs-confirm-n"), "Clear the board → a confirm sheet (5 scores)")
                await pg.click("#hs-no"); await pg.wait_for_timeout(200)
                async with httpx.AsyncClient(base_url=BASE) as c:
                    still = len((await c.get("/api/juan/scores")).json()["scores"])
                check(still == 5, "Cancel keeps the board")
                await pg.click("#hs-clear"); await pg.wait_for_timeout(200); await pg.click("#hs-yes"); await pg.wait_for_timeout(800)
                async with httpx.AsyncClient(base_url=BASE) as c:
                    gone = len((await c.get("/api/juan/scores")).json()["scores"])
                vis = await pg.evaluate("({ rows: document.querySelectorAll('#hs-list .hs-row').length, empty: !document.querySelector('#hs-empty').hidden, clr: document.querySelector('#hs-clear').hidden })")
                check(gone == 0 and vis == {"rows": 0, "empty": True, "clr": True} and "cleared" in await pg.text_content("#toast"), f"Yes, clear it → the board is empty (server {gone}, page {vis})")
                seed()
            await ctx.close()
        check(not errs, f"no page errors ({errs[:2]})")
        await b.close()
    open(FILE, "w").write("{}")
    print("ALL PASS" if not fails else f"{fails} FAIL(S)")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
