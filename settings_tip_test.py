"""v49 → v49.3: the one-time Settings tip (WebKit iPhone 13, 390 + 320 px, light + dark).
  - v49.3: Settings live in Tía's menu (tap the floating Tía; tia_menu_test covers the menu). The tip floats right above
    Tía: "👆 Tap Tía for Settings ⚙️ / Notifications, location & more.", its tail pointing down at her, big bold text, a ✕ (≥ 44 px),
    Fiesta colours (no yellow), fits at 390 and 320 px. The v49.2 corner ⚙️ and the v49 badge are gone; the header's Chisme
    bubble still opens Settings. Screenshots: tia-tip.png (light), settings-tip-light.png, settings-tip-dark.png.
  - ✕, tapping Tía, the bubble, or tapping the tip (opens Tía's menu) ends it for good (localStorage chisme-settings-tip).
  - Tapping the bubble before the tip appears: it never shows.
  - One popup per open: never on the first launch (location card), nor on an open the notifications card or the Home
    Screen tutorial took; it shows on the next open.
  - Dark mode: the tutorial's "Got it" is pink again (was near-black).
Against the local server (CHISME_URL, default http://localhost:8211)."""
import ast, asyncio, os
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1');"
NO_A2 = "if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));"
NO_NOTIF = "localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 }));"   # each load = open 2: the card isn't due
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const bad = [];
  for (const r of document.querySelectorAll(root)) for (const e of [r, ...r.querySelectorAll('*')]) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push((e.id || e.className.baseVal || e.className || e.tagName) + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
GEOM = """() => { const t = document.querySelector('#settings-tip'), f = document.querySelector('#tia-btn'), b = document.querySelector('#settings-btn'), x = document.querySelector('#settings-tip-x');
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const shown = !t.hidden && getComputedStyle(t).display !== 'none', tail = getComputedStyle(t, '::before');
  return { shown, tip: R(t), fab: R(f), btn: R(b), x: R(x), vw: innerWidth, vh: innerHeight,
    gone: !!document.querySelector('#settings-gear, .gear-badge'),
    big: parseFloat(getComputedStyle(t.querySelector('.stip-big')).fontSize), weight: +getComputedStyle(t.querySelector('.stip-big')).fontWeight,
    text: t.innerText.replace(/\\s+/g, ' ').trim(), tailBottom: parseFloat(tail.bottom), tailRight: parseFloat(tail.right), tailW: parseFloat(tail.borderLeftWidth),
    tailOn: tail.content !== 'none', menu: __chisme.tiaMenu.open, st: __chisme.settingsTip }; }"""

def check_tip(s, w):
    tip, f = s["tip"], s["fab"]
    tail_x = tip["r"] - 3 - s["tailRight"] - s["tailW"]; fx = (f["l"] + f["r"]) / 2; tail_y = tip["b"] - 3 - s["tailBottom"]
    check(s["tailOn"] and abs(tail_x - fx) < 3 and f["t"] - 8 <= tail_y <= f["t"] + 4, f"{w} px: the tail points down at Tía (tail x {tail_x:.0f} vs Tía x {fx:.0f}; tail tip y {tail_y:.0f}, Tía top {f['t']:.0f})")
    check(tip["l"] >= 0 and tip["r"] <= w and tip["t"] >= 0 and tip["b"] < f["t"], f"{w} px: fits the screen, right above Tía ({tip['l']:.0f}–{tip['r']:.0f}, {tip['t']:.0f}–{tip['b']:.0f})")
    check(not s["gone"], f"{w} px: no corner ⚙️ and no badge on the bubble")

async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def state(pg): return await pg.evaluate(GEOM)
async def newctx(b, p, scheme="light", width=390, init=(SETUP, NO_A2, NO_NOTIF)):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    dev["viewport"] = {"width": width, "height": 844 if width >= 390 else 640}; dev["device_scale_factor"] = 2
    ctx = await b.new_context(**dev, color_scheme=scheme)
    for s in init: await ctx.add_init_script(s)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        allerrs = []
        for scheme in ["light", "dark"]:
            print(f"== a normal open ({scheme})")
            ctx, pg, errs = await newctx(b, p, scheme)
            await pg.goto(BASE + "/"); await ready(pg)
            await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000)
            await pg.wait_for_timeout(700)   # past the slide-in
            s = await state(pg)
            check(s["shown"] and s["text"].startswith("👆 Tap Tía for Settings ⚙️ Notifications, location & more.") and "mija" not in s["text"], f"the tip shows: {s['text']!r}")
            check_tip(s, 390)
            check(s["big"] >= 19 and s["weight"] >= 800 and s["x"]["w"] >= 44 and s["x"]["h"] >= 44, f"big bold text ({s['big']} px, {s['weight']}), ✕ {s['x']['w']:.0f}×{s['x']['h']:.0f}")
            bad = await pg.evaluate(SCAN, "#settings-tip")
            check(not bad, f"Fiesta colours, no yellow {bad[:3]}")
            try: await pg.wait_for_function("document.querySelector('#sync').hidden", timeout=8000)   # the "Updated" pill fades away
            except Exception: pass
            await pg.wait_for_timeout(400)
            top = max(0, s["tip"]["t"] - 24); clip = {"x": 0, "y": top, "width": 390, "height": s["vh"] - top}   # the bottom of the screen: the tip + Tía
            await pg.screenshot(path=os.path.join(OUT, f"settings-tip-{scheme}.png"), clip=clip)
            if scheme == "light": await pg.screenshot(path=os.path.join(OUT, "tia-tip.png"), clip=clip)
            if scheme == "light":
                await pg.click("#settings-tip-x", force=True); await pg.wait_for_timeout(300)
                s = await state(pg)
                check(not s["shown"] and (s["st"]["saved"] or "").startswith("dismissed:"), f"✕ hides it and saves it ({s['st']['saved']})")
                await pg.wait_for_timeout(300)
                await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.click("#tia-menu-settings"); await pg.wait_for_timeout(400)
                check(await pg.evaluate("document.querySelector('#settings').open"), "Tía → ⚙️ Settings opens Settings")
                await pg.evaluate("document.querySelector('#settings').close()"); await pg.wait_for_timeout(200)
                await pg.click("#settings-btn"); await pg.wait_for_timeout(400)
                check(await pg.evaluate("document.querySelector('#settings').open"), "…and so does the Chisme bubble")
                await pg.evaluate("document.querySelector('#settings').close()")
                await pg.reload(); await ready(pg); await pg.wait_for_timeout(4500)
                check(not (await state(pg))["shown"], "…and it never shows again")
            else:
                await pg.click("#tia-btn", force=True); await pg.wait_for_timeout(500)
                s = await state(pg)
                check(not s["shown"] and s["menu"] and (s["st"]["saved"] or "").startswith("tia:"), f"tapping Tía hides it, her menu opens ({s['st']['saved']})")
                await pg.evaluate("document.querySelector('#tia-menu').close()")
                await pg.reload(); await ready(pg); await pg.wait_for_timeout(4500)
                check(not (await state(pg))["shown"], "…and it never shows again")
            allerrs += errs; await ctx.close()

        print("== tapping the tip opens Tía's menu")
        ctx, pg, errs = await newctx(b, p)
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); await pg.wait_for_timeout(500)
        await pg.click("#settings-tip-go", force=True); await pg.wait_for_timeout(500)
        s = await state(pg)
        check(not s["shown"] and s["menu"] and (s["st"]["saved"] or "").startswith("tip:"), f"tip → Tía's menu (Settings first), tip gone for good ({s['st']['saved']})")
        allerrs += errs; await ctx.close()

        print("== the bubble tapped before the tip appears")
        ctx, pg, errs = await newctx(b, p)
        await pg.goto(BASE + "/"); await ready(pg)
        await pg.evaluate("document.querySelector('#settings-btn').click(); document.querySelector('#settings').close()")
        await pg.wait_for_timeout(4500)
        s = await state(pg)
        check(not s["shown"] and s["st"]["done"], "they found Settings on their own: no tip, ever")
        allerrs += errs; await ctx.close()

        print("== first launch: the location card has this open")
        ctx, pg, errs = await newctx(b, p, init=(NO_A2, NO_NOTIF))
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(3500)
        loc = await pg.evaluate("!document.querySelector('#loc-panel').hidden")
        check(loc and not (await state(pg))["shown"], "location card up, no tip")
        await pg.click("#loc-close"); await pg.wait_for_timeout(5000)
        check(not (await state(pg))["shown"], "after the location card closes: still no tip on this open (one popup per open)")
        await pg.reload(); await ready(pg)
        try: await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); ok = True
        except Exception: ok = False
        check(ok, "the next open: the tip")
        allerrs += errs; await ctx.close()

        print("== the Home Screen tutorial has this open (dark)")
        ctx, pg, errs = await newctx(b, p, "dark", init=(SETUP, NO_NOTIF, "if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits','1');"))
        await pg.goto(BASE + "/"); await ready(pg)
        await pg.wait_for_function("__chisme.a2hs.open", timeout=10000); await pg.wait_for_timeout(600)
        ok_bg = await pg.evaluate("getComputedStyle(document.querySelector('#a2hs-ok')).backgroundColor")
        check(not (await state(pg))["shown"], "tutorial up, no tip")
        check(ok_bg == "rgb(255, 61, 139)", f"dark mode: the tutorial's Got it is pink ({ok_bg}), not near-black")
        await pg.click("#a2hs-ok"); await pg.wait_for_timeout(5000)
        check(not (await state(pg))["shown"], "after Got it: no tip on this open")
        await pg.reload(); await ready(pg)
        try: await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); ok = True
        except Exception: ok = False
        check(ok and not await pg.evaluate("__chisme.a2hs.open"), "the next open: the tip (and no tutorial)")
        allerrs += errs; await ctx.close()

        print("== the notifications card has this open")
        ctx, pg, errs = await newctx(b, p, init=(SETUP, NO_A2))
        await pg.goto(BASE + "/"); await ready(pg)
        await pg.wait_for_function("__chisme.notif.open", timeout=10000)
        check(not (await state(pg))["shown"], "notifications card up, no tip")
        await pg.click("#push-ask-no"); await pg.wait_for_timeout(5000)
        check(not (await state(pg))["shown"], "after Not now: no tip on this open")
        await pg.reload(); await ready(pg)
        try: await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); ok = True
        except Exception: ok = False
        check(ok and not await pg.evaluate("__chisme.notif.open"), "the next open: the tip (no card)")
        allerrs += errs; await ctx.close()

        for scheme in ["light", "dark"]:
            print(f"== 320 px ({scheme})")
            ctx, pg, errs = await newctx(b, p, scheme, width=320)
            await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); await pg.wait_for_timeout(700)
            s = await state(pg); check_tip(s, 320)
            check(s["x"]["w"] >= 44 and s["big"] >= 18, f"320 px: ✕ {s['x']['w']:.0f} px, text {s['big']} px")
            top = max(0, s["tip"]["t"] - 24)
            await pg.screenshot(path=f"/tmp/tia-tip-320-{scheme}.png", clip={"x": 0, "y": top, "width": 320, "height": s["vh"] - top})
            allerrs += errs; await ctx.close()

        check(not allerrs, f"no page errors {allerrs[:3]}")
        await b.close()
    print("\nALL PASS" if not fails else f"\n{fails} FAILED")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
