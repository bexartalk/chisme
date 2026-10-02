"""v49.3: Settings live in Tía's menu. Tapping the floating Tía opens a small menu right above her (tail pointing at her):
the Chisme bubble as branding, a big "⚙️ Settings" and "💬 Chat with Tía" (what tapping Tía did before), a ✕.
  - WebKit iPhone 13, light + dark, 390 + 320 px: big bold text, big buttons, Fiesta colours (no yellow), fits the screen.
    Screenshots: tia-menu-light.png, tia-menu-dark.png (390 px).
  - ⚙️ Settings opens Settings; 💬 Chat opens her chat (and focus comes back to Tía); ✕ / Escape / a tap outside close it.
  - The header's Chisme bubble still opens Settings; the v49.2 corner ⚙️ is gone.
  - No collisions: while the notifications card is up Tía is hidden (no menu on top of it); while the menu is open the
    card waits and comes after it closes (never both); over a donation card the menu is a modal on top (nothing under it
    gets tapped) and the card's buttons work again once it closes.
  - v49.3 refinements: a ⚙️ badge on Tía's circle (tia-circle-badge.png); her chat header reads just "Tía Chismosa" in the
    logo-style display face (white, black outline, no pill, no subtitle), "Tía is an AI" moves to the footer line, and a
    ⚙️ Settings button next to Close (same style, 44px+) opens Settings (tia-chat-header.png).
Against the local server (CHISME_URL, default http://localhost:8211)."""
import ast, asyncio, os
from playwright.async_api import async_playwright
from popup_quiet import QUIET

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1');"
NO_A2 = "if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));"
NO_TIP = "if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const r = document.querySelector(root), bad = [];
  for (const e of [r, ...r.querySelectorAll('*')]) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push((e.id || (e.className && e.className.baseVal != null ? e.className.baseVal : e.className) || e.tagName) + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
MENU = """() => { const m = document.querySelector('#tia-menu'), f = document.querySelector('#tia-btn'), R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const btn = (id) => { const b = document.querySelector(id); return { text: b.innerText.replace(/\\s+/g, ' ').trim(), h: b.getBoundingClientRect().height, px: parseFloat(getComputedStyle(b.querySelector('.tm-big')).fontSize),
    w: +getComputedStyle(b.querySelector('.tm-big')).fontWeight, bg: getComputedStyle(b).backgroundColor, fg: getComputedStyle(b).color }; };
  const tail = getComputedStyle(m, '::before'), emb = m.querySelector('.tia-menu-emblem svg');
  return { open: m.open, modal: m.matches(':modal'), box: R(m), fab: R(f), vw: innerWidth, vh: innerHeight, settings: btn('#tia-menu-settings'), chat: btn('#tia-menu-chat'),
    hi: m.querySelector('#tia-menu-title').textContent, x: R(m.querySelector('#tia-menu-x')), emblem: emb ? R(emb) : null, emblemWord: !!m.querySelector('.tia-menu-emblem .bubble-word'),
    tailBottom: parseFloat(tail.bottom), tailRight: parseFloat(tail.right), tailW: parseFloat(tail.borderLeftWidth), gear: !!document.querySelector('#settings-gear') }; }"""

async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def newctx(b, p, scheme="light", width=390, init=(SETUP, NO_A2, QUIET)):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    dev["viewport"] = {"width": width, "height": 844 if width >= 390 else 640}; dev["device_scale_factor"] = 2
    ctx = await b.new_context(**dev, color_scheme=scheme)
    for s in init: await ctx.add_init_script(s)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); allerrs = []
        for scheme in ["light", "dark"]:
            for width in [390, 320]:
                print(f"== Tía's menu ({scheme}, {width} px)")
                ctx, pg, errs = await newctx(b, p, scheme, width)
                await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(1200)
                await pg.click("#tia-btn"); await pg.wait_for_timeout(450)
                m = await pg.evaluate(MENU)
                check(m["open"] and m["modal"] and not m["gear"], f"tapping Tía opens her menu (a modal; no corner ⚙️ in the header)")
                check(m["settings"]["text"] == "⚙️ Settings Alerts, location & more" and m["chat"]["text"] == "💬 Chat with Tía Ask about today's chisme" and "Tía" in m["hi"],
                      f"⚙️ Settings first, then 💬 Chat with Tía ({m['settings']['text']!r} · {m['chat']['text']!r})")
                check(m["emblem"] and m["emblem"]["w"] >= 55 and m["emblemWord"], f"the Chisme bubble is in it as branding ({m['emblem'] and round(m['emblem']['w'])} px)")
                big = min(m["settings"]["px"], m["chat"]["px"])
                check(big >= (20 if width >= 390 else 19) and m["settings"]["w"] >= 800 and min(m["settings"]["h"], m["chat"]["h"]) >= 60 and m["x"]["w"] >= 44,
                      f"big bold ({big} px / {m['settings']['w']}), big buttons ({m['settings']['h']:.0f} / {m['chat']['h']:.0f} px), ✕ {m['x']['w']:.0f} px")
                bx, fb = m["box"], m["fab"]
                tail_x = bx["r"] - 3 - m["tailRight"] - m["tailW"]; fx = (fb["l"] + fb["r"]) / 2; tail_y = bx["b"] - 3 - m["tailBottom"]
                check(bx["l"] >= 0 and bx["r"] <= width and bx["t"] >= 0 and bx["b"] < fb["t"] and abs(tail_x - fx) < 3 and fb["t"] - 8 <= tail_y <= fb["t"] + 4,
                      f"fits the screen, right above Tía, tail at her ({bx['l']:.0f}–{bx['r']:.0f}, {bx['t']:.0f}–{bx['b']:.0f}; tail {tail_x:.0f},{tail_y:.0f} vs Tía {fx:.0f},{fb['t']:.0f})")
                bad = await pg.evaluate(SCAN, "#tia-menu")
                check(not bad, f"Fiesta colours, no yellow {bad[:3]} (Settings {m['settings']['bg']}, Chat {m['chat']['bg']})")
                top = max(0, int(bx["t"]) - 30)
                shot = os.path.join(OUT, f"tia-menu-{scheme}.png") if width == 390 else f"/tmp/tia-menu-{scheme}-{width}.png"
                await pg.screenshot(path=shot, clip={"x": 0, "y": top, "width": width, "height": m["vh"] - top})
                await pg.click("#tia-menu-settings"); await pg.wait_for_timeout(450)
                st = await pg.evaluate("({ s: document.querySelector('#settings').open, m: document.querySelector('#tia-menu').open })")
                check(st["s"] and not st["m"], "⚙️ Settings → Settings opens (the menu closes)")
                await pg.evaluate("document.querySelector('#settings').close()"); await pg.wait_for_timeout(300)
                if width == 390:
                    await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.click("#tia-menu-chat"); await pg.wait_for_timeout(600)
                    ch = await pg.evaluate("({ t: document.querySelector('#tia').open, m: document.querySelector('#tia-menu').open, log: document.querySelectorAll('#tia-log li').length })")
                    check(ch["t"] and not ch["m"] and ch["log"] >= 1, f"💬 Chat with Tía → her chat, as before ({ch['log']} message(s))")
                    await pg.click("#tia-close"); await pg.wait_for_timeout(400)
                    check(await pg.evaluate("document.activeElement && document.activeElement.id") == "tia-btn", "closing the chat puts focus back on Tía")
                    await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.click("#tia-menu-x"); await pg.wait_for_timeout(300)
                    x = await pg.evaluate("document.querySelector('#tia-menu').open")
                    await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
                    esc = await pg.evaluate("document.querySelector('#tia-menu').open")
                    await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.mouse.click(30, 120); await pg.wait_for_timeout(300)
                    out = await pg.evaluate("({ m: document.querySelector('#tia-menu').open, s: document.querySelector('#settings').open })")
                    check(not x and not esc and not out["m"] and not out["s"], "✕, Escape and a tap outside each close it (the tap outside doesn't reach the page)")
                    await pg.click("#settings-btn"); await pg.wait_for_timeout(400)
                    check(await pg.evaluate("document.querySelector('#settings').open"), "the header's Chisme bubble still opens Settings")
                    await pg.evaluate("document.querySelector('#settings').close()")
                allerrs += errs; await ctx.close()

        print("== the notifications card and Tía's menu never share the screen")
        ctx, pg, errs = await newctx(b, p, init=(SETUP, NO_A2, NO_TIP))   # the card is due (1st open)
        await pg.goto(BASE + "/"); await ready(pg)
        await pg.wait_for_function("__chisme.notif.open", timeout=10000)
        vis = await pg.evaluate("getComputedStyle(document.querySelector('#tia-btn')).visibility")
        check(vis == "hidden", f"card up: Tía is hidden, so no menu on top of it ({vis})")
        await pg.click("#push-ask-no"); await pg.wait_for_timeout(400)
        await pg.click("#tia-btn"); await pg.wait_for_timeout(400)
        check(await pg.evaluate("document.querySelector('#tia-menu').open"), "card closed: Tía and her menu work")
        await pg.evaluate("document.querySelector('#tia-menu').close()"); allerrs += errs; await ctx.close()
        ctx, pg, errs = await newctx(b, p, init=(SETUP, NO_A2, NO_TIP))
        await pg.goto(BASE + "/"); await ready(pg)
        await pg.evaluate("document.querySelector('#tia-btn').click()")   # Tía's menu first, before the card's turn
        both = False
        for _ in range(10):
            await pg.wait_for_timeout(500)
            st = await pg.evaluate("({ m: document.querySelector('#tia-menu').open, c: __chisme.notif.open })"); both |= st["m"] and st["c"]
        check(st["m"] and not st["c"], "menu open: the card waits")
        await pg.click("#tia-menu-x")
        try: await pg.wait_for_function("__chisme.notif.open", timeout=8000); came = True
        except Exception: came = False
        check(came and not both, "menu closed: then the card (never both at once)")
        allerrs += errs; await ctx.close()

        print("== over a donation card")
        ctx, pg, errs = await newctx(b, p)
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(1500)
        await pg.evaluate("document.querySelector('#donate-news').scrollIntoView({ block: 'end' })"); await pg.wait_for_timeout(600)
        HIT = """() => { const b = document.querySelector('#donate-news .donate-btn.cashapp'), r = b.getBoundingClientRect(), x = r.left + 12, y = r.top + r.height / 2;
          const e = document.elementFromPoint(x, y); return { onScreen: r.top >= 0 && r.bottom <= innerHeight, hitsBtn: !!(e && b.contains(e)), menu: document.querySelector('#tia-menu').open }; }"""
        h0 = await pg.evaluate(HIT)
        await pg.click("#tia-btn"); await pg.wait_for_timeout(400)
        h1 = await pg.evaluate(HIT)
        await pg.click("#tia-menu-x"); await pg.wait_for_timeout(300)
        h2 = await pg.evaluate(HIT)
        check(h0["onScreen"] and h0["hitsBtn"] and h1["menu"] and not h1["hitsBtn"] and h2["hitsBtn"],
              f"menu open: the donation buttons can't be hit by mistake (modal); closed: they work again ({h0['hitsBtn']} → {h1['hitsBtn']} → {h2['hitsBtn']})")
        allerrs += errs; await ctx.close()

        HEAD = """() => { const t = document.querySelector('#tia-title'), cs = getComputedStyle(t), st = document.querySelector('#tia-settings'), cl = document.querySelector('#tia-close');
          const S = (b) => { const c = getComputedStyle(b), r = b.getBoundingClientRect(); return { w: r.width, h: r.height, t: r.top, l: r.left, r: r.right, bg: c.backgroundColor, fg: c.color, bd: c.borderTopColor, fs: c.fontSize, fw: c.fontWeight }; };
          const tr = t.getBoundingClientRect(), hr = document.querySelector('.tia-head').getBoundingClientRect();
          return { text: t.textContent, font: cs.fontFamily, loaded: document.fonts.check('40px "Chisme Display"', 'Tía Chismosa'), px: parseFloat(cs.fontSize), color: cs.color,
            stroke: cs.webkitTextStrokeWidth, strokeColor: cs.webkitTextStrokeColor, bg: cs.backgroundColor, sub: !!document.querySelector('.tia-head p'), inHead: tr.bottom <= hr.bottom + 1 && tr.right <= hr.right,
            settings: S(st), close: S(cl), foot: document.querySelector('.tia-foot').textContent, vw: innerWidth }; }"""
        BADGE = """() => { const f = document.querySelector('#tia-btn'), g = f.querySelector('.tia-fab-badge'), r = g.getBoundingClientRect(), fr = f.getBoundingClientRect(), c = getComputedStyle(g);
          return { text: g.textContent, hidden: g.getAttribute('aria-hidden'), w: r.width, l: r.left, t: r.top, r: r.right, fl: fr.left, ft: fr.top, vw: innerWidth, bg: c.backgroundColor, ring: c.boxShadow, pe: c.pointerEvents,
            hit: document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)?.closest('#tia-btn') === f }; }"""
        for scheme, width in [("light", 390), ("dark", 320)]:
            print(f"== Tía's circle badge + her chat header ({scheme}, {width} px)")
            ctx, pg, errs = await newctx(b, p, scheme, width)
            await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(1000)
            g = await pg.evaluate(BADGE)
            check(g["text"] == "⚙️" and g["hidden"] == "true", f"{scheme} {width}: a ⚙️ badge on Tía's circle (decorative, aria-hidden)")
            check(26 <= g["w"] <= 34 and g["l"] < g["fl"] and g["t"] < g["ft"] and g["r"] <= g["vw"], f"{scheme} {width}: badge sits on the circle's top-left edge ({g['w']:.0f} px)")
            check(g["bg"] == "rgb(255, 255, 255)" and "0, 201, 205" in g["ring"], f"{scheme} {width}: white badge, turquoise ring ({g['bg']}, {g['ring'][:30]})")
            check(g["pe"] == "none" and g["hit"], f"{scheme} {width}: tapping the badge is tapping Tía")
            if scheme == "light":
                bx = await pg.evaluate("(() => { const f = document.querySelector('#tia-btn').getBoundingClientRect(); return { x: f.left - 18, y: f.top - 18, width: f.width + 30, height: f.height + 30 }; })()")
                await pg.screenshot(path=os.path.join(OUT, "tia-circle-badge.png"), clip=bx, scale="device")
            bad = await pg.evaluate(SCAN, "#tia-btn"); check(not bad, f"{scheme} {width}: no yellow on Tía's circle ({bad[:3]})")
            await pg.click("#tia-btn"); await pg.click("#tia-menu-chat"); await pg.wait_for_timeout(900)
            await pg.evaluate("document.fonts.ready")
            h = await pg.evaluate(HEAD)
            check(h["text"] == "Tía Chismosa" and not h["sub"], f"{scheme} {width}: the title is just 'Tía Chismosa', no subtitle")
            check("Chisme Display" in h["font"] and h["loaded"], f"{scheme} {width}: in the logo-style display face ({h['font'][:30]}, loaded {h['loaded']})")
            check(h["px"] >= 30 and h["color"] == "rgb(255, 255, 255)" and float(h["stroke"].rstrip("px") or 0) >= 5 and h["strokeColor"] == "rgb(0, 0, 0)", f"{scheme} {width}: big white with a black outline ({h['px']:.0f}px, stroke {h['stroke']})")
            check(h["bg"] in ("rgba(0, 0, 0, 0)", "transparent") and h["inHead"], f"{scheme} {width}: no pill behind it, inside the header ({h['bg']})")
            st, cl = h["settings"], h["close"]
            check(st["h"] >= 44 and st["w"] >= 44 and abs(st["t"] - cl["t"]) < 1 and st["r"] < cl["l"] and cl["r"] <= h["vw"], f"{scheme} {width}: ⚙️ Settings next to Close, 44px+ ({st['w']:.0f}x{st['h']:.0f})")
            check((st["bg"], st["fg"], st["bd"], st["fs"], st["fw"]) == (cl["bg"], cl["fg"], cl["bd"], cl["fs"], cl["fw"]), f"{scheme} {width}: same style as Close ({st['bg']}, {st['fg']})")
            check(h["foot"].startswith("Tía is an AI and only talks about what's in Chisme right now.") and "Forget me" in h["foot"], f"{scheme} {width}: 'Tía is an AI' in the footer line")
            check(await pg.evaluate("document.activeElement && document.activeElement.id") == "tia-title", f"{scheme} {width}: opens with focus on her name (no ring on Settings after a tap)")
            bad = await pg.evaluate(SCAN, ".tia-head"); check(not bad, f"{scheme} {width}: no yellow in the header chrome ({bad[:3]})")
            if scheme == "light": await pg.screenshot(path=os.path.join(OUT, "tia-chat-header.png"), clip={"x": 0, "y": 0, "width": width, "height": 340})
            else: await pg.screenshot(path="/tmp/tia-chat-header-dark-320.png")
            await pg.click("#tia-settings"); await pg.wait_for_timeout(500)
            check(await pg.evaluate("document.querySelector('#settings').open && !document.querySelector('#tia').open"), f"{scheme} {width}: ⚙️ Settings in her chat opens Settings (chat closes)")
            allerrs += errs; await ctx.close()

        check(not allerrs, f"no page errors {allerrs[:3]}")
        await b.close()
    print("\nALL PASS" if not fails else f"\n{fails} FAILED")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
