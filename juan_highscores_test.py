"""v49.5 player-facing 🏆 Juan Top 10 (static/juan.js + style.css; server: juanscores.py).
  • the board sits at the bottom of The Juan That Got Away's game screen: rank · name · score from GET /api/juan/scores,
    "Be the first on the board!" when empty, hidden while the game is full screen; the last board is kept on the phone and
    still shows offline (with an offline note)
  • a run ends when Juan makes it through Playa Neón (level 7), or when you leave the game (✕) with points: if the score makes the Top 10,
    a sheet says "🏆 New high score! Put your nickname on the board" with a 12-character name box and a big Save → POST → the
    board refreshes with the new row highlighted (in the sheet and on the page); a score that doesn't make it asks nothing
  • offline: Save keeps the name on the phone ("waiting") and posts it when the phone is back online
  • light + dark at 390×844 and 320×640: big bold text (rows ≥ 44 px, ≥ 16 px), nothing clipped or sideways-scrolling
Screenshots: screenshots/juan-highscores.png (the board, light 390), juan-new-highscore.png (the sheet, light 390).
Seeds the local server's file store (JUAN_SCORES_FILE), so run it against a local server only (CHISME_URL, default :8211)."""
import asyncio, json, os, random, sys, time
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
FILE = os.environ.get("JUAN_SCORES_FILE", "/tmp/chisme-juan-scores.json")
SETUP = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); }"
G = "__chisme.juegos.game"
TEN = [("Goonie", 12340, 6), ("La Tía", 10125, 6), ("Juanito", 7450, 5), ("Ictunis", 5800, 4), ("Mija", 4800, 4), ("Compa", 3950, 3), ("Chuy", 2600, 2), ("Lupe", 2105, 2), ("Beto", 1650, 1), ("Nena", 1200, 1)]
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
def seed(rows):
    now = int(time.time()); json.dump({f"s{i}": {"name": n, "score": sc, "level": lv, "t": now - 9000 + i} for i, (n, sc, lv) in enumerate(rows)}, open(FILE, "w"))
BOARD = """() => { const s = document.querySelector('#juan-hs'), R = e => e.getBoundingClientRect(), rows = [...s.querySelectorAll('.juan-hs-row')];
  return { title: s.querySelector('.juan-hs-t').textContent.trim(), rows: rows.map(r => [r.querySelector('.rk').textContent, r.querySelector('.nm').textContent, r.querySelector('.sc').textContent]),
    empty: (s.querySelector('.juan-hs-empty') || {}).textContent || '', me: rows.findIndex(r => r.classList.contains('me')), note: s.querySelector('#juan-hs-note').hidden ? '' : s.querySelector('#juan-hs-note').textContent,
    minH: Math.min(...rows.map(r => R(r).height), 99), px: rows.length ? parseFloat(getComputedStyle(rows[0]).fontSize) : 0, fw: rows.length ? getComputedStyle(rows[0]).fontWeight : '',
    clipped: rows.filter(r => r.querySelector('.sc').scrollWidth > r.querySelector('.sc').clientWidth + 1 || R(r).right > R(s).right + 1).length,
    wide: document.documentElement.scrollWidth - innerWidth, bg: getComputedStyle(s).backgroundColor, fg: getComputedStyle(s).color, below: R(s).top >= R(document.querySelector('#juan-stats')).bottom - 1 }; }"""
SHEET = """() => { const d = document.querySelector('dialog.juan-hs-sheet[open]'); if (!d) return null; const R = e => e.getBoundingClientRect(), i = d.querySelector('input'), b = d.querySelector('.juan-hs-save');
  return { big: d.querySelector('.juan-hs-big').textContent.trim(), sub: d.querySelector('.juan-hs-sub').textContent.trim(), max: i ? i.maxLength : 0, inH: i ? R(i).height : 0, saveH: R(b).height, saveTxt: b.textContent.trim(),
    savePx: parseFloat(getComputedStyle(b).fontSize), saveBg: getComputedStyle(b).backgroundColor, fits: R(d).top >= 0 && R(d).bottom <= innerHeight + 1 && R(d).left >= 0 && R(d).right <= innerWidth + 1,
    bg: getComputedStyle(d).backgroundColor, rows: [...d.querySelectorAll('.juan-hs-row')].map(r => r.querySelector('.nm').textContent), me: [...d.querySelectorAll('.juan-hs-row')].findIndex(r => r.classList.contains('me')) }; }"""

async def page(b, p, w, scheme="light"):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": w, "height": 844 if w == 390 else 640}; dev["device_scale_factor"] = 2
    ctx = await b.new_context(**dev, color_scheme=scheme, extra_http_headers={"X-Forwarded-For": f"10.{random.randint(1, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"})
    await ctx.add_init_script(SETUP); await ctx.add_init_script(QUIET)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    await pg.goto(BASE + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.hs", timeout=120000)
    await pg.wait_for_function(G + ".hs.live", timeout=15000); await pg.wait_for_timeout(500)
    return ctx, pg, errs

async def to_board(pg):
    await pg.evaluate("document.querySelector('#juan-hs').scrollIntoView({ block: 'end' })"); await pg.wait_for_timeout(400)

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        print("== an empty board")
        seed([]); ctx, pg, errs = await page(b, p, 390)
        m = await pg.evaluate(BOARD)
        check(m["title"].endswith("Top 10") and m["empty"] == "Be the first on the board!" and not m["rows"] and m["below"], f"the board at the bottom of the game screen says 'Be the first on the board!' ({m['title']!r}, {m['empty']!r})")
        await ctx.close()

        print("== a full board, light + dark, 390 + 320")
        seed(TEN)
        for scheme, w in [("light", 390), ("dark", 390), ("light", 320), ("dark", 320)]:
            ctx, pg, errs = await page(b, p, w, scheme); await to_board(pg); m = await pg.evaluate(BOARD)
            ok = (len(m["rows"]) == 10 and m["rows"][0] == ["1", "Goonie", "12,340"] and m["rows"][9] == ["10", "Nena", "1,200"] and m["minH"] >= 44 and m["px"] >= 16 and int(m["fw"]) >= 800
                  and not m["clipped"] and m["wide"] <= 0 and not errs and (m["bg"] == "rgb(255, 255, 255)") == (scheme == "light"))
            check(ok, f"{scheme} {w}: 10 rows rank · name · score, best first, big bold ({m['px']:.0f}px/{m['fw']}, rows ≥ {m['minH']:.0f}px), not clipped, no sideways scroll ({m['bg']} / {m['fg']}) {errs[:1]}")
            if scheme == "light" and w == 390:   # the screenshot: after the "Updated" pill is gone, the whole board under the tab bar
                try: await pg.wait_for_function("(document.querySelector('#sync') || {}).dataset?.state === 'done'", timeout=20000)
                except Exception: pass
                await pg.wait_for_timeout(3500)
                await pg.evaluate("(() => { const s = document.querySelector('#juan-hs'), top = (document.querySelector('.tabs, nav') || { getBoundingClientRect: () => ({ bottom: 0 }) }).getBoundingClientRect().bottom; scrollTo(0, s.getBoundingClientRect().top + scrollY - top - 50); })()")
                await pg.wait_for_timeout(600); await pg.screenshot(path=os.path.join(OUT, "juan-highscores.png"))
            if w == 390 and scheme == "light":
                # a score that doesn't make it → nothing asked
                asked = await pg.evaluate(G + ".hs.offer(1000, 1)")
                check(asked is False and not await pg.evaluate(SHEET), "a score below #10 (1,000 < 1,200) asks nothing")
                # offline: the last board still shows, with a note
                await ctx.set_offline(True); await pg.evaluate(G + ".hs.loadBoard()"); m2 = await pg.evaluate(BOARD)
                check(len(m2["rows"]) == 10 and "Offline" in m2["note"], f"offline: the last board this phone saw still shows ({len(m2['rows'])} rows, {m2['note']!r})")
                await ctx.set_offline(False)
            if w == 320 and scheme == "dark":
                await pg.evaluate(G + ".hs.offer(9000, 5)"); await pg.wait_for_selector("dialog.juan-hs-sheet[open]"); sh = await pg.evaluate(SHEET)
                check(sh and sh["fits"] and sh["inH"] >= 44 and sh["saveH"] >= 56 and sh["max"] == 12 and sh["bg"] != "rgb(255, 255, 255)", f"dark 320: the sheet fits the screen, dark, 12-char box, big Save ({sh})")
            await ctx.close()

        print("== a real run: Juan makes it through Playa Neón → the sheet → Save → the board")
        seed(TEN[:7]); ctx, pg, errs = await page(b, p, 390)
        await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
        hidden = await pg.evaluate("getComputedStyle(document.querySelector('#juan-hs')).display === 'none'")
        check(hidden, "the board is hidden while the game is full screen")
        END = await pg.evaluate("ChismeJuan.END")
        await pg.evaluate(f"{G}.warp(7, {END} - 40)")
        await pg.wait_for_function(G + ".state.mode === 'win'", timeout=10000)
        await pg.wait_for_selector("dialog.juan-hs-sheet[open]", timeout=8000)
        sc = await pg.evaluate(G + ".state.score"); sh = await pg.evaluate(SHEET)
        check(sh["big"] == "🏆 New high score!" and sh["sub"] == "Put your nickname on the board" and sh["max"] == 12 and sh["saveTxt"].lower() == "save" and sh["saveH"] >= 56 and sh["savePx"] >= 20 and sh["fits"],
              f"the run's over ({sc} points) and it makes the Top 10 → '{sh['big']} {sh['sub']}', a 12-char name box, a big Save ({sh['saveH']:.0f}px, {sh['savePx']:.0f}px text, {sh['saveBg']})")
        await pg.fill("dialog.juan-hs-sheet input", "Goonie El Tejano")
        val = await pg.input_value("dialog.juan-hs-sheet input")
        check(val == "Goonie El Te", f"the name box stops at 12 characters ({val!r})")
        await pg.wait_for_timeout(200); await pg.screenshot(path=os.path.join(OUT, "juan-new-highscore.png"))
        await pg.click("dialog.juan-hs-sheet .juan-hs-save")
        await pg.wait_for_function("document.querySelector('dialog.juan-hs-sheet .in-sheet')", timeout=10000)
        sh = await pg.evaluate(SHEET); srv = await pg.evaluate("fetch('/api/juan/scores').then(r => r.json())")
        mine = [r for r in srv["scores"] if r["name"] == "Goonie El Te"]
        check(mine and mine[0]["score"] == sc and mine[0]["level"] == 7, f"Save POSTs it: the server has 'Goonie El Te' · {sc} · level 7 (v49.5: Playa Neón ends the run)")
        check(sh["me"] >= 0 and sh["rows"][sh["me"]] == "Goonie El Te", f"the sheet shows the refreshed board with the new row highlighted (#{sh['me'] + 1})")
        await pg.click("dialog.juan-hs-sheet .juan-hs-save"); await pg.wait_for_timeout(300)
        await pg.click(".gfs-x"); await pg.wait_for_timeout(500); await to_board(pg); m = await pg.evaluate(BOARD)
        check(m["me"] >= 0 and m["rows"][m["me"]][1] == "Goonie El Te" and len(m["rows"]) == 8, f"the page's board refreshed too, the new row highlighted ({m['rows'][m['me']] if m['me'] >= 0 else None})")
        again = await pg.evaluate(G + ".hs.offer(99999, 6)")
        check(again is False, "one name per run (no second sheet for the same run)")
        check(not errs, f"no page errors {errs[:2]}")
        await ctx.close()

        print("== leaving the game (✕) with points ends the run; offline Save waits on the phone")
        ctx, pg, errs = await page(b, p, 320, "dark")
        await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
        await pg.evaluate(f"{G}.warp(2, {END} - 40)"); await pg.wait_for_function(G + ".state.mode === 'clear'", timeout=10000)
        await ctx.set_offline(True)
        await pg.click(".gfs-x"); await pg.wait_for_selector("dialog.juan-hs-sheet[open]", timeout=8000)
        check(True, "✕ mid-run with 500 points → the sheet (the board has room)")
        await pg.fill("dialog.juan-hs-sheet input", "Mija"); await pg.click("dialog.juan-hs-sheet .juan-hs-save")
        await pg.wait_for_function("document.querySelector('dialog.juan-hs-sheet .in-sheet')", timeout=8000)
        txt = await pg.text_content("dialog.juan-hs-sheet .juan-hs-sub")
        pend = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-juan-pending') || '[]')")
        check("Saved on this phone" in txt and len(pend) == 1 and pend[0]["name"] == "Mija", f"offline: Save keeps it on the phone ({txt!r})")
        await pg.click("dialog.juan-hs-sheet .juan-hs-save"); await to_board(pg); m = await pg.evaluate(BOARD)
        check(any("Mija" in r[1] and "waiting" in r[1] for r in m["rows"]), "the board shows it as waiting")
        await ctx.set_offline(False); await pg.evaluate("dispatchEvent(new Event('online'))")
        await pg.wait_for_function("JSON.parse(localStorage.getItem('chisme-juan-pending') || '[]').length === 0", timeout=10000); await pg.wait_for_timeout(500)
        srv = await pg.evaluate("fetch('/api/juan/scores').then(r => r.json())"); m = await pg.evaluate(BOARD)
        check(any(r["name"] == "Mija" and r["score"] == 500 for r in srv["scores"]) and m["me"] >= 0 and "waiting" not in m["rows"][m["me"]][1], "back online: it goes up to the server and the board highlights it")
        check(not errs, f"no page errors {errs[:2]}")
        await ctx.close(); await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
