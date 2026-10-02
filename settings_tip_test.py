"""v49 → v49.2: the one-time Settings tip + the ⚙️ Settings button in the header's top-right corner (WebKit iPhone 13, 390 px).
  - v49.2: the ⚙️ is its own 44 px round button (black, silver ring, white gear) at the top right of the header, clear of the
    skyline and the helicopter (checked shape by shape), at 390 and 320 px, light + dark; it opens Settings. The Chisme
    bubble still opens Settings too, and has no badge any more. Screenshot: header-settings-button.png.
  - A normal open: Tía's tip "👆 Settings are up here ⚙️ / Alerts, location & more." right under the ⚙️, its tail
    pointing up at it, big bold text, a ✕ (≥ 44 px), Fiesta colours (no yellow), light + dark. Screenshots cropped to the
    header: settings-tip-light.png, settings-tip-dark.png.
  - ✕, the ⚙️, the bubble, or tapping the tip (opens Settings) ends it for good (localStorage chisme-settings-tip).
  - Tapping the bubble before the tip appears: it never shows.
  - One popup per open: never on the first launch (location card), nor on an open the notifications card or the Home
    Screen tutorial took; it shows on the next open.
  - Dark mode: the tutorial's "Got it" is pink again (was near-black).
Against the local server (CHISME_URL, default http://localhost:8211)."""
import ast, asyncio, os
from playwright.async_api import async_playwright

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
GEOM = """() => { const t = document.querySelector('#settings-tip'), b = document.querySelector('#settings-btn'), g = document.querySelector('#settings-gear'), x = document.querySelector('#settings-tip-x');
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const shown = !t.hidden && getComputedStyle(t).display !== 'none', tail = getComputedStyle(t, '::before'), gc = getComputedStyle(g);
  // does the ⚙️ (plus 3 px around it) touch the skyline or the helicopter? sample its box against each visible shape
  const gr = g.getBoundingClientRect(), hits = [];
  const shapes = [...document.querySelectorAll('.skyline g[class^="sky-"] path, .skyline .heli')].filter((p) => p.getBoundingClientRect().width > 0);
  for (const p of shapes) { const m = p.getScreenCTM().inverse();
    for (let X = gr.left - 3; X <= gr.right + 3; X += 2) for (let Y = gr.top - 3; Y <= gr.bottom + 3; Y += 2) {
      const q = new DOMPoint(X, Y).matrixTransform(m); if (p.isPointInFill(q)) { hits.push(p.getAttribute('class') || p.parentNode.getAttribute('class')); X = 1e9; break; } } }
  const heli = document.querySelector('.skyline .heli').getBoundingClientRect();
  return { shown, tip: R(t), btn: R(b), gear: R(g), gearBg: gc.backgroundColor, gearRing: gc.borderTopColor, gearRadius: gc.borderTopLeftRadius,
    gearFill: getComputedStyle(g.querySelector('.gear-body')).fill, hits, heli: { l: heli.left, t: heli.top, r: heli.right, b: heli.bottom },
    badge: !!document.querySelector('#settings-btn .gear-badge, .gear-badge'), x: R(x),
    big: parseFloat(getComputedStyle(t.querySelector('.stip-big')).fontSize), weight: +getComputedStyle(t.querySelector('.stip-big')).fontWeight,
    text: t.innerText.replace(/\\s+/g, ' ').trim(), tailTop: parseFloat(tail.top), tailRight: parseFloat(tail.right), tailW: parseFloat(tail.borderLeftWidth), tailOn: tail.content !== 'none', st: __chisme.settingsTip }; }"""

def check_gear(s, w, scheme):
    g = s["gear"]
    check(round(g["w"]) == 44 and round(g["h"]) == 44 and s["gearRadius"] in ("50%", "22px") and g["r"] <= w - 8 and g["t"] >= 6 and g["r"] > w - 20,
          f"{w} px {scheme}: ⚙️ 44 px round button in the top-right corner ({g['l']:.0f},{g['t']:.0f} → {g['r']:.0f},{g['b']:.0f}, radius {s['gearRadius']})")
    check(s["gearBg"] == "rgb(0, 0, 0)" and s["gearFill"] in ("rgb(255, 255, 255)", "#fff", "#ffffff") and s["gearRing"] == "rgb(201, 208, 216)",
          f"{w} px {scheme}: black, silver ring, white gear ({s['gearBg']}, {s['gearRing']}, {s['gearFill']})")
    h = s["heli"]; clear_heli = h["r"] + 10 < g["l"] or h["l"] - 10 > g["r"] or h["b"] < g["t"] or h["t"] > g["b"] + 3   # ±10 px: the helicopter drifts
    check(not s["hits"] and clear_heli, f"{w} px {scheme}: clear of the skyline and the helicopter (shapes touched: {s['hits']}; heli {h['l']:.0f},{h['t']:.0f}–{h['r']:.0f},{h['b']:.0f})")
    check(not s["badge"], f"{w} px {scheme}: no badge on the Chisme bubble any more")

def check_tail(s):
    tip, g = s["tip"], s["gear"]
    tail_x = tip["r"] - 3 - s["tailRight"] - s["tailW"]; gx = (g["l"] + g["r"]) / 2; tail_y = tip["t"] + 3 + s["tailTop"]
    check(s["tailOn"] and abs(tail_x - gx) < 3 and g["b"] - 4 <= tail_y <= g["b"] + 8, f"the tail points up at the ⚙️ (tail x {tail_x:.0f} vs ⚙️ x {gx:.0f}; tail tip y {tail_y:.0f}, ⚙️ bottom {g['b']:.0f})")

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
            check(s["shown"] and s["text"].startswith("👆 Settings are up here ⚙️ Alerts, location & more.") and "mija" not in s["text"], f"the tip shows: {s['text']!r}")
            check_gear(s, 390, scheme)
            check_tail(s)
            check(s["big"] >= 19 and s["weight"] >= 800 and s["x"]["w"] >= 44 and s["x"]["h"] >= 44, f"big bold text ({s['big']} px, {s['weight']}), ✕ {s['x']['w']:.0f}×{s['x']['h']:.0f}")
            check(s["tip"]["l"] >= 0 and s["tip"]["r"] <= 390, f"fits the screen ({s['tip']['l']:.0f}–{s['tip']['r']:.0f})")
            bad = await pg.evaluate(SCAN, "#settings-tip, #settings-gear")
            check(not bad, f"Fiesta colours, no yellow {bad[:3]}")
            try: await pg.wait_for_function("document.querySelector('#sync').hidden", timeout=8000)   # the "Updated" pill fades away
            except Exception: pass
            await pg.wait_for_timeout(400)
            clip_h = s["tip"]["b"] + 14
            await pg.screenshot(path=os.path.join(OUT, f"settings-tip-{scheme}.png"), clip={"x": 0, "y": 0, "width": 390, "height": clip_h})
            if scheme == "light":
                await pg.click("#settings-tip-x", force=True); await pg.wait_for_timeout(300)
                s = await state(pg)
                check(not s["shown"] and (s["st"]["saved"] or "").startswith("dismissed:"), f"✕ hides it and saves it ({s['st']['saved']})")
                await pg.wait_for_timeout(300)
                await pg.screenshot(path=os.path.join(OUT, "header-settings-button.png"), clip={"x": 0, "y": 0, "width": 390, "height": s["btn"]["b"] + 30})
                await pg.click("#settings-gear"); await pg.wait_for_timeout(400)
                check(await pg.evaluate("document.querySelector('#settings').open"), "the ⚙️ opens Settings")
                await pg.evaluate("document.querySelector('#settings').close()"); await pg.wait_for_timeout(200)
                await pg.click("#settings-btn"); await pg.wait_for_timeout(400)
                check(await pg.evaluate("document.querySelector('#settings').open"), "…and so does the Chisme bubble")
                await pg.evaluate("document.querySelector('#settings').close()")
                await pg.reload(); await ready(pg); await pg.wait_for_timeout(4500)
                check(not (await state(pg))["shown"], "…and it never shows again")
            else:
                await pg.click("#settings-gear", force=True); await pg.wait_for_timeout(500)
                s = await state(pg); dlg = await pg.evaluate("document.querySelector('#settings').open")
                check(not s["shown"] and dlg and (s["st"]["saved"] or "").startswith("gear:"), f"tapping the ⚙️ hides it, Settings opens ({s['st']['saved']})")
                await pg.evaluate("document.querySelector('#settings').close()")
                await pg.reload(); await ready(pg); await pg.wait_for_timeout(4500)
                check(not (await state(pg))["shown"], "…and it never shows again")
            allerrs += errs; await ctx.close()

        print("== tapping the tip opens Settings")
        ctx, pg, errs = await newctx(b, p)
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); await pg.wait_for_timeout(500)
        await pg.click("#settings-tip-go", force=True); await pg.wait_for_timeout(500)
        s = await state(pg); dlg = await pg.evaluate("document.querySelector('#settings').open")
        check(not s["shown"] and dlg and (s["st"]["saved"] or "").startswith("tip:"), f"tip → Settings opens, tip gone for good ({s['st']['saved']})")
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

        print("== 320 px")
        ctx, pg, errs = await newctx(b, p, width=320)
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_function("__chisme.settingsTip.shown", timeout=8000); await pg.wait_for_timeout(600)
        s = await state(pg)
        check_gear(s, 320, "light"); check_tail(s)
        check(s["tip"]["l"] >= 0 and s["tip"]["r"] <= 320 and s["x"]["w"] >= 44, f"the tip fits ({s['tip']['l']:.0f}–{s['tip']['r']:.0f})")
        await pg.screenshot(path="/tmp/settings-tip-320.png", clip={"x": 0, "y": 0, "width": 320, "height": s["tip"]["b"] + 14})
        allerrs += errs; await ctx.close()
        print("== 320 px, dark (no tip)")
        ctx, pg, errs = await newctx(b, p, "dark", width=320, init=(SETUP, NO_A2, NO_NOTIF, "localStorage.setItem('chisme-settings-tip', 'test:0');"))
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(1500)
        s = await state(pg); check_gear(s, 320, "dark")
        await pg.click("#settings-gear"); await pg.wait_for_timeout(400)
        check(await pg.evaluate("document.querySelector('#settings').open"), "320 px dark: the ⚙️ opens Settings")
        await pg.evaluate("document.querySelector('#settings').close()"); await pg.wait_for_timeout(300)
        await pg.screenshot(path="/tmp/header-gear-320-dark.png", clip={"x": 0, "y": 0, "width": 320, "height": s["btn"]["b"] + 30})
        allerrs += errs; await ctx.close()

        check(not allerrs, f"no page errors {allerrs[:3]}")
        await b.close()
    print("\nALL PASS" if not fails else f"\n{fails} FAILED")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
