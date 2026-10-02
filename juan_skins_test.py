"""v49.5 Juan skins + a 1.5× Juan (static/juan.js + style.css).
  • Juan is drawn 1.5× bigger; his hitbox grows to match (32×88, the body without the hat, a bit forgiving at the sides)
  • the title screen has a "👕 Skin" chip beside Start (🔒 while locked; aria-label "Skin: <name>") → a picker sheet: Classic Juan, El Jefe Presidente, Iron Juan,
    El Payaso, Juan UFO, Master Jefe, Armadura (original parodies, no real names or logos)
  • Classic Juan is the default; the other six show 🔒 + "Make the Top 10 to unlock" until a score of yours posts into the
    Top 10 (then they're unlocked on this phone for good, localStorage chisme-juan-top10); tapping a locked one just says so
  • picking one is saved on the phone and Juan wears it in the game; every skin draws in every pose without page errors
  • light + dark at 390×844 and 320×640: the sheet fits the screen, names aren't clipped, cards ≥ 44 px; the title still fits,
    even with "Keep going: level 6" (on ≤ 360 px the chip is just 👕 then)
Screenshots: screenshots/juan-skins.png (the picker, unlocked, light 390), juan-big.png (the bigger Juan in the game, light 390).
Seeds the local server's file store (JUAN_SCORES_FILE), so run it against a local server only (CHISME_URL, default :8211)."""
import asyncio, json, os, random, sys, time
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
FILE = os.environ.get("JUAN_SCORES_FILE", "/tmp/chisme-juan-scores.json")
SETUP = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); }"
G = "__chisme.juegos.game"
SEVEN = [("Goonie", 12340, 6), ("La Tía", 10125, 6), ("Juanito", 7450, 5), ("Ictunis", 5800, 4), ("Mija", 4800, 4), ("Compa", 3950, 3), ("Chuy", 2600, 2)]
NAMES = ["Classic Juan", "El Jefe Presidente", "Iron Juan", "El Payaso", "Juan UFO", "Master Jefe", "Armadura"]
IDS = ["classic", "jefe", "hierro", "payaso", "ufo", "master", "armadura"]
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
def seed(rows):
    now = int(time.time()); json.dump({f"s{i}": {"name": n, "score": sc, "level": lv, "t": now - 9000 + i} for i, (n, sc, lv) in enumerate(rows)}, open(FILE, "w"))
TITLE = """() => { const ov = document.querySelector('#juan-ov'), r = ov.getBoundingClientRect(), b = ov.querySelector('[data-act=skins]');
  return { mode: __chisme.juegos.game.state.mode, txt: b ? b.textContent.trim() : null, aria: b ? b.getAttribute('aria-label') : null, h: b ? b.getBoundingClientRect().height : 0, scroll: ov.scrollHeight - ov.clientHeight,
    inside: [...ov.children].every(k => { const q = k.getBoundingClientRect(); return q.top >= r.top - 1 && q.bottom <= r.bottom + 1 && q.left >= r.left - 1 && q.right <= r.right + 1; }) }; }"""
PICK = """() => { const d = document.querySelector('dialog.juan-skins[open]'); if (!d) return null; const R = e => e.getBoundingClientRect(), bs = [...d.querySelectorAll('.juan-sk')];
  return { sub: d.querySelector('.juan-sk-sub').textContent.trim(), names: bs.map(b => b.querySelector('.juan-sk-n').textContent.replace(/\u00ad/g, '').trim()), ids: bs.map(b => b.dataset.skin),
    locked: bs.filter(b => b.classList.contains('locked')).map(b => b.dataset.skin), lockTxt: bs.filter(b => b.classList.contains('locked')).map(b => b.textContent.includes('🔒') && b.textContent.includes('Make the Top 10 to unlock')),
    on: bs.filter(b => b.classList.contains('on')).map(b => b.dataset.skin), minH: Math.min(...bs.map(b => R(b).height)),
    clipped: bs.filter(b => { return [...b.querySelectorAll('.juan-sk-n, .juan-sk-why')].some(n => { const q = R(n), o = R(b); return q.left < o.left + 2 || q.right > o.right - 2 || n.scrollWidth > n.clientWidth + 1; }); }).map(b => b.dataset.skin),
    drawn: bs.filter(b => { const c = b.querySelector('canvas'), x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < x.length; i += 16) n += x[i] > 0; return n > 200; }).length,
    fits: R(d).top >= 0 && R(d).bottom <= innerHeight + 1 && R(d).left >= 0 && R(d).right <= innerWidth + 1, scroll: d.scrollHeight - d.clientHeight,
    doneIn: R(d.querySelector('.juan-sk-done')).bottom <= Math.min(R(d).bottom, innerHeight) + 1, bg: getComputedStyle(d).backgroundColor }; }"""

async def page(b, p, w, scheme="light", ctx=None):
    if ctx is None:
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": w, "height": 844 if w == 390 else 640}; dev["device_scale_factor"] = 2
        ctx = await b.new_context(**dev, color_scheme=scheme, extra_http_headers={"X-Forwarded-For": f"10.{random.randint(1, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"})
        await ctx.add_init_script(SETUP); await ctx.add_init_script(QUIET)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: None if "access control checks" in str(e) or "Context is stopped" in str(e) else errs.append(str(e)[:200]))   # WebKit noise when a reload cancels a fetch / audio
    await pg.goto(BASE + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000)
    await pg.wait_for_timeout(600)
    return ctx, pg, errs

async def to_stage(pg):
    await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 60); }"); await pg.wait_for_timeout(400)

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        print("== a new phone: Classic Juan, the rest locked")
        seed(SEVEN); ctx, pg, errs = await page(b, p, 390); await to_stage(pg)
        t = await pg.evaluate(TITLE)
        check(t["mode"] == "title" and t["txt"] == "👕 Skin 🔒" and t["aria"] == "Skin: Classic Juan. Make the Top 10 to unlock more" and t["h"] >= 44 and t["inside"] and t["scroll"] <= 1, f"the title screen has {t['txt']!r} beside Start ({t['aria']!r}, {t['h']:.0f}px) and still fits")
        check(await pg.evaluate(G + ".skins.now") == "classic" and not await pg.evaluate(G + ".skins.unlocked"), "Classic Juan is the default; skins start locked")
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
        check(m["names"] == NAMES and m["ids"] == IDS, f"the picker lists the seven ({', '.join(m['names'])})")
        check(m["locked"] == IDS[1:] and all(m["lockTxt"]) and m["on"] == ["classic"] and m["sub"].startswith("🔒"), f"six are locked, each with 🔒 + 'Make the Top 10 to unlock'; Classic is on ({m['sub']!r})")
        check(m["drawn"] == 7 and m["fits"] and m["doneIn"] and not m["clipped"] and m["minH"] >= 44, f"light 390: every card has its picture, the sheet fits, names not clipped ({m['clipped']}), cards ≥ {m['minH']:.0f}px")
        await pg.screenshot(path="/tmp/juan-skins-locked.png")
        await pg.click("dialog.juan-skins .juan-sk[data-skin=jefe]"); await pg.wait_for_timeout(200); m = await pg.evaluate(PICK)
        check(m["sub"] == "🔒 Make the Top 10 to unlock El Jefe Presidente." and m["on"] == ["classic"] and await pg.evaluate(G + ".skins.now") == "classic", f"tapping a locked one just says so ({m['sub']!r})")
        await pg.click("dialog.juan-skins .juan-sk-done"); await pg.wait_for_timeout(200)
        check(not await pg.evaluate("!!document.querySelector('dialog.juan-skins')"), "Done closes the sheet")
        # a stored skin doesn't sneak past the lock
        await pg.evaluate("(() => { const s = JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{}'); s.skin = 'armadura'; localStorage.setItem('chisme-juegos-juan', JSON.stringify(s)); })()")
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000)
        check(await pg.evaluate(G + ".skins.now") == "classic", "a skin saved while still locked falls back to Classic Juan")

        print("== the bigger Juan")
        await to_stage(pg); await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(400)
        s = await pg.evaluate(G + ".state")
        check(s["hw"] == 32 and s["hh"] == 88 and s["skin"] == "classic", f"the hitbox matches the 1.5× Juan ({s['hw']}×{s['hh']})")
        await pg.evaluate(G + ".warp(1, 900)"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=os.path.join(OUT, "juan-big.png"))

        print("== a real run makes the Top 10 → the skins unlock")
        END = await pg.evaluate("ChismeJuan.END")
        await pg.evaluate(f"{G}.warp(6, {END} - 40)"); await pg.wait_for_function(G + ".state.mode === 'win'", timeout=10000)
        await pg.wait_for_selector("dialog.juan-hs-sheet[open]", timeout=8000)
        await pg.fill("dialog.juan-hs-sheet input", "Skinny"); await pg.click("dialog.juan-hs-sheet .juan-hs-save")
        await pg.wait_for_function("document.querySelector('dialog.juan-hs-sheet .in-sheet')", timeout=10000)
        un = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-juan-top10') || 'null')")
        check(un and await pg.evaluate(G + ".skins.unlocked"), f"the score posts into the Top 10 → skins unlocked on this phone ({un})")
        await pg.click("dialog.juan-hs-sheet .juan-hs-save"); await pg.wait_for_timeout(300); await pg.click(".gfs-x"); await pg.wait_for_timeout(600)
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(600)
        await to_stage(pg); t = await pg.evaluate(TITLE)
        check(t["txt"] == "👕 Skin" and t["aria"] == "Skin: Armadura" and t["inside"] and t["scroll"] <= 1, f"after a reload: still unlocked, no lock, and the skin saved earlier (Armadura) now applies ({t})")
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
        check(not m["locked"] and m["sub"] == "🏆 You made the Top 10: every skin is yours." and m["drawn"] == 7, f"the picker: nothing locked ({m['sub']!r})")
        foc = await pg.evaluate("document.activeElement && document.activeElement.dataset.skin")
        check(foc == "armadura", f"the sheet opens with the skin you're wearing focused ({foc})")
        try: await pg.wait_for_function("(document.querySelector('#sync') || {}).dataset?.state === 'done'", timeout=20000)
        except Exception: pass
        await pg.wait_for_timeout(3500); await pg.screenshot(path=os.path.join(OUT, "juan-skins.png"))
        for sid, name in zip(IDS[1:], NAMES[1:]):
            await pg.click(f"dialog.juan-skins .juan-sk[data-skin={sid}]"); await pg.wait_for_timeout(120)
            on = (await pg.evaluate(PICK))["on"]; lbl = await pg.get_attribute("#juan-ov [data-act=skins]", "aria-label")
            check(on == [sid] and await pg.evaluate(G + ".skins.now") == sid and name in lbl, f"pick {name} → it's on, the title says {lbl.strip()!r}")
        await pg.click("dialog.juan-skins .juan-sk-done"); await pg.wait_for_timeout(200)
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000)
        check(await pg.evaluate(G + ".skins.now") == "armadura", "the pick is saved on the phone (Armadura after a reload)")

        print("== every skin in the game: run, jump, cheer")
        for sid in IDS:
            await pg.evaluate(f"(() => {{ const s = JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{{}}'); s.skin = '{sid}'; localStorage.setItem('chisme-juegos-juan', JSON.stringify(s)); }})()")
            await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(300)
            await to_stage(pg); await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
            await pg.evaluate(G + ".warp(2, 700)"); await pg.wait_for_timeout(500); await pg.evaluate(G + ".air(-160)"); await pg.wait_for_timeout(400)
            await pg.screenshot(path=f"/tmp/juan-skin-{sid}.png")
            s = await pg.evaluate(G + ".state")
            check(s["skin"] == sid and s["hw"] == 32 and s["hh"] == 88 and not errs, f"{sid}: Juan wears it in the game, same hitbox, no page errors {errs[:1]}")
            await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
            if await pg.evaluate("!!document.querySelector('dialog.juan-hs-sheet[open]')"):
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
        await ctx.close()

        print("== light + dark, 390 + 320")
        for scheme, w in [("dark", 390), ("light", 320), ("dark", 320)]:
            for unlocked in (False, True):
                ctx, pg, errs = await page(b, p, w, scheme)
                if unlocked:
                    # unlocked + a best score + "Keep going: level 6" (the fullest title there is)
                    await pg.evaluate("localStorage.setItem('chisme-juan-top10', JSON.stringify({ at: Date.now(), rank: 4 })); localStorage.setItem('chisme-juegos-juan', JSON.stringify({ best: 13250, levelMax: 6, wins: 2, skin: 'jefe' }))"); await pg.reload()
                    await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(400)
                await to_stage(pg); t = await pg.evaluate(TITLE)
                await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
                ok = (t["inside"] and t["scroll"] <= 1 and m["fits"] and m["doneIn"] and not m["clipped"] and m["minH"] >= 44 and m["drawn"] == 7 and len(m["locked"]) == (0 if unlocked else 6)
                      and (m["bg"] == "rgb(255, 255, 255)") == (scheme == "light") and not errs)
                check(ok, f"{scheme} {w} {'unlocked, Keep going + best score' if unlocked else 'locked'}: title fits ({t['scroll']}), the sheet fits with Done showing, names not clipped {m['clipped']}, cards ≥ {m['minH']:.0f}px ({m['bg']}) {errs[:1]}")
                await pg.screenshot(path=f"/tmp/juan-skins-{scheme}-{w}-{'open' if unlocked else 'locked'}.png")
                await ctx.close()
        await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
