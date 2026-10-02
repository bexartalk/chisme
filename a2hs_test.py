"""v41 → v47: the "Add to Home Screen" tutorial (iPhone / iPad Safari; v47: also iPhone in other browsers and Android, see a2hs_v47_test.py).

WebKit (iPhone 13 at 390×844, Safari): not on the first open; v47: on the 2nd open (the shared visit counter chisme-visits), once
the one-time location card is answered: a bottom sheet with 3 big steps (Share ⬆️ → Add to Home Screen → Add), big icons, an arrow pointing down toward Safari's
toolbar (bottom center), Got it / Show me later, Fiesta colors (no yellow). "Show me later" → back on the next open, and it shows
by itself at most twice. "Got it" → never again. Never in the installed app (navigator.standalone) or on a desktop; Chrome/Firefox
on iOS get "Open Chisme in Safari" instead, Android its own steps. iPad: the arrow points to the top right. Settings → "How to add Chisme to your Home Screen" reopens it.
Screenshot: a2hs-tutorial.png (+ a2hs-ipad.png)."""
import asyncio, json, os, re
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests

BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs(OUT, exist_ok=True)
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
SHEET = """(() => { const a = document.querySelector('#a2hs'), sh = a.querySelector('.a2hs-sheet'), ar = a.querySelector('.a2hs-arrow'), r = sh.getBoundingClientRect(), q = ar.getBoundingClientRect();
  const yellow = (c) => { const m = (c || '').match(/[\\d.]+/g); if (!m) return false; let [R, G, B, A] = m.map(Number); if (A != null && A < .1) return false; R /= 255; G /= 255; B /= 255;
    const mx = Math.max(R, G, B), mn = Math.min(R, G, B), l = (mx + mn) / 2, d = mx - mn; if (!d) return false; const s = d / (1 - Math.abs(2 * l - 1)); if (s < .3 || d * 255 < 12) return false;
    let h = mx === R ? ((G - B) / d) % 6 : mx === G ? (B - R) / d + 2 : (R - G) / d + 4; h = (h * 60 + 360) % 360; return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= .85 || l <= .2)); };
  const bad = [...a.querySelectorAll('*')].flatMap(e => { const c = getComputedStyle(e); return ['color', 'backgroundColor', 'borderTopColor'].filter(k => yellow(c[k])).map(k => e.className + ' ' + k + ' ' + c[k]); });
  return { open: !a.hidden && getComputedStyle(a).display !== 'none', steps: [...a.querySelectorAll('.a2hs-steps li')].map(li => li.innerText.replace(/\\s+/g, ' ').trim()), icons: a.querySelectorAll('.a2hs-steps .a2hs-badge').length,
    title: a.querySelector('#a2hs-title').textContent, sub: a.querySelector('#a2hs-sub').textContent, btns: [...a.querySelectorAll('.a2hs-btns button')].map(b => b.textContent.trim()),
    sheet: [r.left, r.top, r.right, r.bottom].map(Math.round), arrow: [q.left, q.top, q.right, q.bottom].map(Math.round), arrowRot: getComputedStyle(ar).transform, iw: innerWidth, ih: innerHeight,
    fits: r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth, bad, role: a.getAttribute('role'), label: a.getAttribute('aria-labelledby'), focus: document.activeElement && document.activeElement.id,
    state: window.__chisme && __chisme.a2hs }; })()"""
async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def is_open(pg): return await pg.evaluate("!document.querySelector('#a2hs').hidden")
async def reopen(pg, wait=2300):
    await pg.reload(); await ready(pg); await pg.wait_for_timeout(wait)
    return await is_open(pg)

async def iphone(p):
    print("== WebKit iPhone Safari, 390×844")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 1
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2500)
    loc = await pg.evaluate("!document.querySelector('#loc-panel').hidden")
    check(loc and not await is_open(pg), f"first open: the one-time location card is up, no tutorial (location card {loc})")
    await pg.click("#loc-close"); await pg.wait_for_timeout(2500)
    check(not await is_open(pg) and (await pg.evaluate("__chisme.a2hs"))["opens"] == 1, "first open, location answered: still no tutorial (not on the first visit)")
    await pg.reload(); await ready(pg); await pg.wait_for_timeout(150)
    check(not await is_open(pg), "second open: not in the first instant…")
    await pg.wait_for_timeout(2350)
    s = await pg.evaluate(SHEET)
    check(s["open"] and s["state"]["opens"] == 2 and s["state"]["shows"] == 1 and s["state"]["safari"] and not s["state"]["standalone"], f"v47: …then on the 2nd open the tutorial slides up ({s['state']})")
    check(len(s["steps"]) == 3 and "Share" in s["steps"][0] and "bottom of Safari" in s["steps"][0] and "Add to Home Screen" in s["steps"][1] and "Add" in s["steps"][2] and s["icons"] == 3,
          f"3 short steps with big icons: {s['steps']}")
    check(s["btns"] == ["Show me later", "Got it"] and s["title"] == "Put Chisme on your Home Screen" and len(s["sub"]) < 110, f"'Got it' + 'Show me later', a short witty line ({s['sub']!r})")
    ax = (s["arrow"][0] + s["arrow"][2]) / 2
    check(abs(ax - 195) < 6 and s["arrow"][3] >= 844 - 60 and s["arrow"][1] >= s["sheet"][3] - 2 and s["fits"], f"an arrow under the sheet points down at Safari's toolbar, bottom center (arrow {s['arrow']}, sheet {s['sheet']})")
    check(not s["bad"], f"Fiesta colors, no yellow ({s['bad'][:3]})")
    check(s["role"] == "dialog" and s["label"] == "a2hs-title" and s["focus"] == "a2hs-title", "accessible: a labelled dialog, focus moves to its title")
    await pg.wait_for_timeout(500); await pg.screenshot(path=os.path.join(OUT, "a2hs-tutorial.png"))
    await pg.click("#a2hs-later"); await pg.wait_for_timeout(300)
    st = await pg.evaluate("__chisme.a2hs")
    check(not await is_open(pg) and not st["done"] and st["next"] == st["opens"] + 1, f"Show me later: it goes away, back on the next open ({st})")
    seen = [await reopen(pg)]
    check(seen == [True], f"…the next open: it's back ({seen})")
    await pg.click("#a2hs-later"); await pg.wait_for_timeout(200)
    st = await pg.evaluate("__chisme.a2hs")
    seen = [await reopen(pg, 1800) for _ in range(4)]
    check(st["done"] and st["shows"] == 2 and seen == [False] * 4, f"it shows by itself at most twice: after the 2nd 'Show me later', never again ({st}, then {seen})")
    # Settings reopens it anytime
    await pg.click("#settings-btn"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('#set-a2hs').scrollIntoView()")
    txt = await pg.text_content("#set-a2hs")
    await pg.click("#set-a2hs"); await pg.wait_for_timeout(400)
    s = await pg.evaluate(SHEET)
    check("How to add Chisme to your Home Screen" in txt and s["open"] and not await pg.evaluate("document.querySelector('#settings').open") and s["state"]["shows"] == 2,
          f"Settings → '{txt.strip()}' reopens it (Settings closes; doesn't count as an automatic show)")
    await pg.click("#a2hs-ok"); await pg.wait_for_timeout(200)
    check(not await is_open(pg), "Got it closes it")
    check(not errs, f"no page errors ({errs[:3]})")
    await ctx.close()
    # Got it on the first show → never again; the old one-line hint dismissed = already seen
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1')"); pg = await ctx.new_page()
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
    first = [await is_open(pg), await reopen(pg)]
    await pg.click("#a2hs-ok")
    seen = [await reopen(pg, 1800) for _ in range(4)]
    check(first == [False, True] and seen == [False] * 4, f"location already set: open 1 nothing, the 2nd shows it; 'Got it' → never again ({first}, then {seen})")
    await ctx.close()
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits', '1')"); pg = await ctx.new_page()
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
    check(not await is_open(pg), "someone who dismissed the old one-line install hint doesn't get it again")
    await ctx.close()
    # the installed Home Screen app: never
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits', '1'); Object.defineProperty(navigator, 'standalone', { get: () => true });"); pg = await ctx.new_page()
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
    st = await pg.evaluate("__chisme.a2hs")
    await pg.click("#settings-btn"); await pg.wait_for_timeout(300)
    note = await pg.evaluate("({ btn: document.querySelector('#set-a2hs').hidden, note: document.querySelector('#set-a2hs-note').textContent })")
    check(not await is_open(pg) and st["standalone"] and st["opens"] == 2 and note["btn"] and "already" in note["note"], f"in the installed Home Screen app: never (and Settings says it's already installed) ({note})")
    await ctx.close()
    # Chrome / Firefox on iPhone: not Safari → never
    for name, ua in (("Chrome on iPhone", re.sub(r"Version/[\d.]+", "CriOS/129.0.6668.46", dev["user_agent"])), ("Firefox on iPhone", re.sub(r"Version/[\d.]+", "FxiOS/131.0", dev["user_agent"])), ("Instagram's in-app browser", dev["user_agent"] + " Instagram 350.0.0")):
        d2 = dict(dev); d2["user_agent"] = ua
        ctx = await b.new_context(**d2); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits', '1')"); pg = await ctx.new_page()   # (its 2nd open)
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
        s = await pg.evaluate(SHEET)
        check(("CriOS" in ua or "FxiOS" in ua or "Instagram" in ua) and s["open"] and not s["state"]["safari"] and s["state"]["kind"] == "ios-other" and s["title"] == "Open Chisme in Safari",
              f"v47 {name}: not the Safari steps but 'Open Chisme in Safari' ({s['title']!r}, {s['state']['kind']})")
        await ctx.close()
    # iPad Safari: the Share button is at the top right
    dev = dict(p.devices["iPad Pro 11"]); dev.pop("default_browser_type", None); dev["device_scale_factor"] = 1
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits', '1')"); pg = await ctx.new_page()   # its 2nd open
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
    s = await pg.evaluate(SHEET)
    check(s["open"] and s["state"]["ipad"] and "top right of Safari" in s["steps"][0] and s["arrow"][1] < 70 and s["arrow"][2] > s["iw"] - 80 and s["arrowRot"] != "none",
          f"iPad: the arrow points up to the top right, and step 1 says so (arrow {s['arrow']} on {s['iw']}×{s['ih']})")
    await pg.screenshot(path=os.path.join(OUT, "a2hs-ipad.png"))
    await b.close()

async def others(p):
    print("\n== Android Chrome: its own steps (v47) / desktop: never")
    b = await p.chromium.launch()
    for name, kw in (("Android Chrome (Pixel 7)", {k: v for k, v in p.devices["Pixel 7"].items() if k != "default_browser_type"}), ("desktop Chrome", {"viewport": {"width": 1280, "height": 800}})):
        ctx = await b.new_context(**kw); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits', '1')"); pg = await ctx.new_page()
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(2300)
        st = await pg.evaluate("__chisme.a2hs")
        if "Android" in name: check(await is_open(pg) and not st["safari"] and st["kind"] in ("android", "android-install"), f"v47 {name}: the Android version (⋮ → Install app, or one-tap Install) ({st['kind']})")
        else: check(not await is_open(pg) and not st["safari"] and st["kind"] == "desktop", f"{name}: never on a desktop")
        await ctx.close()
    await b.close()

async def main():
    async with async_playwright() as p:
        await iphone(p); await others(p)
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)
asyncio.run(main())
