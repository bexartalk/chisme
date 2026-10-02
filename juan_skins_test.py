"""v49.5 Juan skins + a 1.5× Juan (static/juan.js + style.css).
  • Juan is drawn 1.5× bigger; his hitbox grows to match (32×88, the body without the hat, a bit forgiving at the sides)
  • v49.8: "👕 Skins" (aria "Skins: wearing <name>") on the title, Paused, level clear and the win; locked: 🔒 + "Make the Top 10 to unlock"; a pick applies at once (even paused)
  • the title screen has a "👕 Skin" chip beside Start (🔒 while locked; aria-label "Skin: <name>") → a picker sheet: Classic Juan, El Jefe Presidente, Iron Juan,
    El Joker, Juan UFO, Master Jefe, Armadura, Juanby, Juan Vice (original parodies, no real names, logos or numbers); 9 cards in 2 columns,
    the odd last one centered
  • Classic Juan is the default; the other eight show 🔒 + "Make the Top 10 to unlock" until a score of yours posts into the
    Top 10 (then they're unlocked on this phone for good, localStorage chisme-juan-top10); tapping a locked one just says so
  • picking one is saved on the phone and Juan wears it in the game; every skin draws in every pose without page errors
  • every skin has its own short jump animation (dust + hat bounce, tie + swoop, thrusters, confetti + card, UFO jet + beam, jetpack,
    steam + a landing dust ring, Juanby's alley-oop, Vice's neon trail + shades glint), visual only: the hitbox stays 32×88 mid-jump
  • Juanby (~2× tall) stays below the HUD on the ground and on screen at the top of a double jump (he tucks his knees), 390 + 320
  • level 7, Dice City VI, comes after Noche Caliente (the clear screen offers it) and the run's win is at the end of it
  • light + dark at 390×844 and 320×640: the sheet fits the screen, names aren't clipped, cards ≥ 44 px; the title still fits,
    even with "Keep going: level 7" (on ≤ 360 px the chip is just 👕 then)
Screenshots: screenshots/juan-skins.png (the picker, unlocked, light 390), juan-big.png (the bigger Juan in the game, light 390),
juan-juanby.png (Juanby dribbling in the game), dice-city-start.png + dice-city-beach.png (level 7: the arch, the beach finish), juan-vice.png (Juan Vice mid-jump), juan-jumps.png (every skin mid-jump).
Seeds the local server's file store (JUAN_SCORES_FILE), so run it against a local server only (CHISME_URL, default :8211)."""
import asyncio, base64, json, os, random, sys, time
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
FILE = os.environ.get("JUAN_SCORES_FILE", "/tmp/chisme-juan-scores.json")
SETUP = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); }"
G = "__chisme.juegos.game"
SEVEN = [("Goonie", 12340, 6), ("La Tía", 10125, 6), ("Juanito", 7450, 5), ("Ictunis", 5800, 4), ("Mija", 4800, 4), ("Compa", 3950, 3), ("Chuy", 2600, 2)]
NAMES = ["Classic Juan", "El Jefe Presidente", "Iron Juan", "El Joker", "Juan UFO", "Master Jefe", "Armadura", "Juanby", "Juan Vice", "Cocaine Cowboy"]
IDS = ["classic", "jefe", "hierro", "joker", "ufo", "master", "armadura", "juanby", "vice", "cowboy"]
N = len(IDS)
TIDY = lambda m: (m["last"]["alone"] and m["last"]["mid"] < 2) if N % 2 else not m["last"]["alone"]
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
    last: (() => { const g = R(d.querySelector('.juan-sk-grid')), l = R(bs[bs.length - 1]), o = R(bs[0]); return { mid: Math.abs((l.left + l.right) / 2 - (g.left + g.right) / 2), w: Math.abs(l.width - o.width), alone: bs.slice(0, -1).every(b => R(b).bottom <= l.top + 1) }; })(),
    doneIn: R(d.querySelector('.juan-sk-done')).bottom <= Math.min(R(d).bottom, innerHeight) + 1, bg: getComputedStyle(d).backgroundColor }; }"""

# every skin drawn standing still vs right after a jump (ja = 0.2 s), same frame otherwise → the jump animation adds pixels; plus a sheet of them all
FX = """(() => { const J = ChismeJuan, W = 150, H = 230, px = (c) => c.getContext('2d').getImageData(0, 0, c.width, c.height).data, diff = {};
  const draw = (id, ja) => { const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d'); g.translate(75, 205); g.scale(J.JS * 0.75, J.JS * 0.75); J.drawJuan(g, { skin: id, pose: 'up', outfit: 'western', t: 1.3, ph: 0, ja }); return c; };
  const sheet = document.createElement('canvas'); sheet.width = J.SKINS.length * W; sheet.height = H + 26; const s = sheet.getContext('2d'); s.fillStyle = '#d6f7f8'; s.fillRect(0, 0, sheet.width, sheet.height);
  J.SKINS.forEach(([id, name], i) => { const a = draw(id), b = draw(id, 0.2), x = px(a), y = px(b); let n = 0; for (let k = 3; k < x.length; k += 4) n += Math.abs(x[k] - y[k]) > 40 || Math.abs(x[k - 1] - y[k - 1]) + Math.abs(x[k - 2] - y[k - 2]) + Math.abs(x[k - 3] - y[k - 3]) > 90; diff[id] = n;
    s.drawImage(b, i * W, 0); s.fillStyle = '#000'; s.font = '900 15px Arial'; s.textAlign = 'center'; s.fillText(name, i * W + W / 2, H + 18); });
  const r = document.createElement('canvas'); r.width = W; r.height = 80; const rg = r.getContext('2d'); rg.translate(75, 60); rg.scale(J.JS, J.JS); J.groundFx(rg, 'armadura', 0.15); let ring = 0; const rd = px(r); for (let k = 3; k < rd.length; k += 4) ring += rd[k] > 20;
  return { diff, ring, png: sheet.toDataURL('image/png') }; })()"""
# Juanby's height in the game (offscreen, run + falling poses) against the view: head top on the ground and at the top of a double jump (game units, y = 0 is the top)
FIT = """(() => { const J = ChismeJuan, v = __chisme.juegos.game.state.view, top = (pose) => { const c = document.createElement('canvas'); c.width = 500; c.height = 600; const g = c.getContext('2d'); g.translate(250, 560); g.scale(J.JS, J.JS);
    J.drawJuan(g, { skin: 'juanby', pose, outfit: 'western', t: 1.3, ph: 1 }); const d = g.getImageData(0, 0, 500, 600).data; let t = 600, r = 0; for (let y = 0; y < 600; y++) for (let x = 0; x < 500; x++) if (d[(y * 500 + x) * 4 + 3] > 20) { if (t === 600) t = y; r = Math.max(r, x); } return [560 - t, r - 250]; };
  const [hr, wr] = top('run'), [hd] = top('down'), jump = 620 * 620 / 3500 + 540 * 540 / 3500;   // JUMP −620, JUMP2 −540, GRAV 1750 (juan.js)
  return { GS: Math.round(v.GS), run: hr, fall: hd, ground: v.GS - hr, apex: v.GS - jump - hd, right: 84 + 16 + wr }; })()"""

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
        check(t["mode"] == "title" and t["txt"] == "👕 Skins 🔒" and t["aria"] == "Skins: wearing Classic Juan. Make the Top 10 to unlock more" and t["h"] >= 44 and t["inside"] and t["scroll"] <= 1, f"the title screen has {t['txt']!r} beside Start ({t['aria']!r}, {t['h']:.0f}px) and still fits")
        check(await pg.evaluate(G + ".skins.now") == "classic" and not await pg.evaluate(G + ".skins.unlocked"), "Classic Juan is the default; skins start locked")
        OVB = "(() => { const ov = document.querySelector('#juan-ov'), b = ov.querySelector('[data-act=skins]'), h = ov.querySelector('.juan-sk-hint'); return { mode: " + G + ".state.mode, btn: b ? b.textContent.trim() : null, hint: h ? h.textContent.trim() : null, skin: " + G + ".state.skin, h: b ? b.getBoundingClientRect().height : 0 }; })()"
        o = await pg.evaluate(OVB); check(o["hint"] == "🔒 Make the Top 10 to unlock", f"v49.8 locked: the title shows the hint under the button ({o['hint']!r})")
        await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(500); await pg.click("#juan-pause"); await pg.wait_for_timeout(200); o = await pg.evaluate(OVB)
        check(o["mode"] == "paused" and o["btn"] == "👕 Skins 🔒" and o["hint"] == "🔒 Make the Top 10 to unlock" and o["h"] >= 44, f"v49.8 locked: Paused has a locked 👕 Skins with the Top 10 hint ({o})")
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await to_stage(pg)
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
        check(m["names"] == NAMES and m["ids"] == IDS, f"the picker lists all {N}: Classic + {N - 1} ({', '.join(m['names'])})")
        check(TIDY(m) and m["last"]["w"] < 2, f"{N} cards in 2 columns, tidy (an odd last card sits alone, centered; v49.6: 10 fill 5 full rows), all the same size ({m['last']})")
        check(m["locked"] == IDS[1:] and all(m["lockTxt"]) and m["on"] == ["classic"] and m["sub"].startswith("🔒"), f"{N - 1} are locked, each with 🔒 + 'Make the Top 10 to unlock'; Classic is on ({m['sub']!r})")
        check(m["drawn"] == N and m["fits"] and m["doneIn"] and not m["clipped"] and m["minH"] >= 44, f"light 390: every card has its picture, the sheet fits, names not clipped ({m['clipped']}), cards ≥ {m['minH']:.0f}px")
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
        await pg.evaluate(f"{G}.warp(6, {END} - 40)"); await pg.wait_for_function(G + ".state.mode === 'clear'", timeout=10000)
        nx = await pg.evaluate("(document.querySelector('#juan-ov [data-act=next]') || {}).textContent || ''")
        await pg.click("#juan-ov [data-act=next]"); await pg.wait_for_timeout(500); s = await pg.evaluate(G + ".state")
        check("Level 7: Dice City VI" in nx and s["level"] == 7 and s["name"] == "Dice City VI" and s["mode"] in ("run", "intro"), f"v49.5: after Noche Caliente the clear screen offers level 7, Dice City VI ({nx!r} → level {s['level']}, {s['mode']})")
        await pg.evaluate(f"{G}.warp(7, {END} - 40)"); await pg.wait_for_function(G + ".state.mode === 'win'", timeout=10000)
        await pg.wait_for_selector("dialog.juan-hs-sheet[open]", timeout=8000)
        await pg.fill("dialog.juan-hs-sheet input", "Skinny"); await pg.click("dialog.juan-hs-sheet .juan-hs-save")
        await pg.wait_for_function("document.querySelector('dialog.juan-hs-sheet .in-sheet')", timeout=10000)
        un = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-juan-top10') || 'null')")
        check(un and await pg.evaluate(G + ".skins.unlocked"), f"the score posts into the Top 10 → skins unlocked on this phone ({un})")
        await pg.click("dialog.juan-hs-sheet .juan-hs-save"); await pg.wait_for_timeout(300); await pg.click(".gfs-x"); await pg.wait_for_timeout(600)
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(600)
        await to_stage(pg); t = await pg.evaluate(TITLE)
        check(t["txt"] == "👕 Skins" and t["aria"] == "Skins: wearing Armadura" and t["inside"] and t["scroll"] <= 1, f"after a reload: still unlocked, no lock, and the skin saved earlier (Armadura) now applies ({t})")
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
        check(not m["locked"] and m["sub"] == "🏆 You made the Top 10: every skin is yours." and m["drawn"] == N and TIDY(m), f"the picker: nothing locked ({m['sub']!r})")
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
        check(await pg.evaluate(G + ".skins.now") == IDS[-1], f"the pick is saved on the phone (the last one picked, {NAMES[-1]}, after a reload)")

        print("== v49.8: 👕 Skins anytime: paused, level clear, the win")
        await to_stage(pg); await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(600); await pg.click("#juan-pause"); await pg.wait_for_timeout(200); o = await pg.evaluate(OVB)
        check(o["mode"] == "paused" and o["btn"] == "👕 Skins" and o["hint"] is None and o["h"] >= 44, f"Paused: ▶ Resume + 👕 Skins, no lock ({o})")
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); await pg.click("dialog.juan-skins .juan-sk[data-skin=jefe]"); await pg.wait_for_timeout(150)
        o = await pg.evaluate(OVB); await pg.screenshot(path=os.path.join(OUT, "skins-button-picker.png"))
        check(o["skin"] == "jefe" and o["mode"] == "paused", f"picking Master Jefe while paused puts him on right away (the paused game shows {o['skin']}), still paused")
        await pg.click("dialog.juan-skins .juan-sk-done"); await pg.wait_for_timeout(200); await pg.screenshot(path=os.path.join(OUT, "skins-button.png"))
        await pg.click("#juan-ov [data-act=resume]"); await pg.wait_for_timeout(300)
        check((await pg.evaluate(OVB))["mode"] == "run" and await pg.evaluate(G + ".state.skin") == "jefe", "▶ Resume: the run goes on in the new skin")
        await pg.evaluate(G + ".warp(1, 5700)"); await pg.wait_for_function(G + ".state.mode === 'clear'", timeout=20000); await pg.wait_for_timeout(300); o = await pg.evaluate(OVB)
        check(o["btn"] == "👕 Skins" and o["h"] >= 44 and await pg.locator("#juan-ov [data-act=next]").count() == 1, f"level clear: ▶ next level + 👕 Skins ({o})")
        await pg.evaluate(G + ".warp(7, 5700)"); await pg.wait_for_function(G + ".state.mode === 'win'", timeout=30000); await pg.wait_for_timeout(300); o = await pg.evaluate(OVB)
        check(o["btn"] == "👕 Skins" and await pg.locator("#juan-ov [data-act=again]").count() == 1, f"the win (end of Dice City VI): ▶ Play again + 👕 Skins ({o})")
        await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); await pg.click(f"dialog.juan-skins .juan-sk[data-skin={IDS[-1]}]"); await pg.click("dialog.juan-skins .juan-sk-done")
        check(await pg.evaluate(G + ".skins.now") == IDS[-1], f"…and it opens the picker there too (back to {NAMES[-1]})")

        print("== every skin's jump animation (offscreen, the game's own drawJuan)")
        fx = await pg.evaluate(FX)
        check(all(fx["diff"][k] > 100 for k in IDS) and fx["ring"] > 150, f"every skin draws something extra right after a jump (changed pixels {fx['diff']}), Armadura's landing dust ring draws ({fx['ring']})")
        open(os.path.join(OUT, "juan-jumps.png"), "wb").write(base64.b64decode(fx["png"].split(",", 1)[1]))

        print("== every skin in the game: run, jump, cheer")
        for sid in IDS:
            await pg.evaluate(f"(() => {{ const s = JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{{}}'); s.skin = '{sid}'; localStorage.setItem('chisme-juegos-juan', JSON.stringify(s)); }})()")
            await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(300)
            await to_stage(pg); await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
            lv, x0 = (7, 1180) if sid in ("vice", "juanby") else (2, 700)
            await pg.evaluate(f"{G}.warp({lv}, {x0})"); await pg.wait_for_timeout(500)
            if sid == "juanby":
                await pg.wait_for_function(G + ".state.ground", timeout=3000); await pg.wait_for_timeout(250)
                await pg.screenshot(path=os.path.join(OUT, "juan-juanby.png"))
            await pg.evaluate(G + ".jump()"); await pg.wait_for_timeout(130 if sid == "vice" else 200)
            j = await pg.evaluate(G + ".state")
            if sid == "vice": await pg.screenshot(path=os.path.join(OUT, "juan-vice.png"))
            check(j["ja"] is not None and 0 < j["ja"] < 0.6 and not j["ground"] and j["hw"] == 32 and j["hh"] == 88, f"{sid}: a real jump plays the jump animation ({j['ja'] and round(j['ja'], 2)}s in), the hitbox stays 32×88")
            await pg.evaluate(G + ".air(-160)"); await pg.wait_for_timeout(400)
            await pg.screenshot(path=f"/tmp/juan-skin-{sid}.png")
            s = await pg.evaluate(G + ".state")
            check(s["skin"] == sid and s["hw"] == 32 and s["hh"] == 88 and not errs, f"{sid}: Juan wears it in the game, same hitbox, no page errors {errs[:1]}")
            if sid == "vice":   # Dice City VI: the arch at the start + the beach at the end
                await pg.evaluate(f"{G}.warp(7, 140)"); await pg.wait_for_timeout(300)
                c = await pg.evaluate(G + ".state")
                check(c["name"] == "Dice City VI" and c["level"] == 7 and not errs, f"level 7 runs: {c['name']} {errs[:1]}")
                await pg.screenshot(path=os.path.join(OUT, "dice-city-start.png"))   # the DICE CITY VI neon arch at the start
                await pg.evaluate(f"{G}.warp(7, {END} - 260)"); await pg.wait_for_timeout(700)
                await pg.screenshot(path=os.path.join(OUT, "dice-city-beach.png"))   # the finish: the beach, the cheering crowd
            await pg.click(".gfs-x"); await pg.wait_for_timeout(300)
            if await pg.evaluate("!!document.querySelector('dialog.juan-hs-sheet[open]')"):
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
        await ctx.close()

        print("== light + dark, 390 + 320")
        for scheme, w in [("dark", 390), ("light", 320), ("dark", 320)]:
            for unlocked in (False, True):
                ctx, pg, errs = await page(b, p, w, scheme)
                if unlocked:
                    # unlocked + a best score + "Keep going: level 7" (the fullest title there is)
                    await pg.evaluate("localStorage.setItem('chisme-juan-top10', JSON.stringify({ at: Date.now(), rank: 4 })); localStorage.setItem('chisme-juegos-juan', JSON.stringify({ best: 13250, levelMax: 7, wins: 2, skin: 'jefe', v6: 1 }))"); await pg.reload()
                    await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(400)
                await to_stage(pg); t = await pg.evaluate(TITLE)
                await pg.click("#juan-ov [data-act=skins]"); await pg.wait_for_selector("dialog.juan-skins[open]"); m = await pg.evaluate(PICK)
                ok = (t["inside"] and t["scroll"] <= 1 and m["fits"] and m["doneIn"] and not m["clipped"] and m["minH"] >= 44 and m["drawn"] == N and len(m["locked"]) == (0 if unlocked else N - 1) and TIDY(m)
                      and (m["bg"] == "rgb(255, 255, 255)") == (scheme == "light") and not errs)
                check(ok, f"{scheme} {w} {'unlocked, Keep going + best score' if unlocked else 'locked'}: title fits ({t['scroll']}), the sheet fits with Done showing, names not clipped {m['clipped']}, cards ≥ {m['minH']:.0f}px ({m['bg']}) {errs[:1]}")
                await pg.screenshot(path=f"/tmp/juan-skins-{scheme}-{w}-{'open' if unlocked else 'locked'}.png")
                if unlocked and scheme == "dark":   # Juanby fits: below the HUD on the ground, on screen at the top of a double jump
                    await pg.click("dialog.juan-skins .juan-sk-done"); await pg.wait_for_timeout(200)
                    await pg.evaluate("(() => { const s = JSON.parse(localStorage.getItem('chisme-juegos-juan') || '{}'); s.skin = 'juanby'; localStorage.setItem('chisme-juegos-juan', JSON.stringify(s)); })()")
                    await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game && __chisme.juegos.game.skins", timeout=120000); await pg.wait_for_timeout(300)
                    await to_stage(pg); await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(400)
                    f = await pg.evaluate(FIT)
                    check(f["ground"] >= 62 and f["apex"] >= 0 and f["right"] <= 360 and not errs, f"{scheme} {w}: Juanby fits: head at y={f['ground']:.0f} on the ground (HUD ends at 60), y={f['apex']:.0f} at the top of a double jump (≥ 0, on screen), {f}")
                await ctx.close()
        await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
