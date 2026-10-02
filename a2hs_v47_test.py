"""v47: the Home Screen tutorial, very easy: one screen, 3 big steps at most (a few huge bold words + a big icon each), on the
2nd open (the visit counter the push opt-in uses, chisme-visits), never in the installed app, never on a desktop.
- iPhone Safari: Share → Add to Home Screen → Add (the arrow points at Safari's toolbar). Also fits 320×568.
- iPhone in another browser (Chrome): "Open Chisme in Safari" with a 📋 Copy link button (copies the app's link, "Link copied!").
- Android Chrome: the one-tap 📲 Install when the browser offers it (beforeinstallprompt), else ⋮ → Install app → Install.
  The inline install card doesn't show on the same visit, and after the tutorial it's gone for good.
- It has the visit to itself: no push opt-in card (or the iPhone "Home Screen first" push tip) on the same visit.
- "Show me later" → the next open (once more at most); "Got it" → never again. Fiesta colors, no yellow.
Screenshots: a2hs-iphone.png, a2hs-android.png."""
import asyncio, os, re
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests

BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs(OUT, exist_ok=True)
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
VISIT1 = "localStorage.setItem('chisme-location-setup','1'); if (!localStorage.getItem('chisme-visits')) localStorage.setItem('chisme-visits','1');"   # this load = the 2nd open
FAKE_BIP = """window.__prompted = 0; window.__fakeBIP = (outcome) => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompted++; };
  e.userChoice = Promise.resolve({ outcome: outcome || 'accepted' }); window.dispatchEvent(e); };"""
CLIP = "window.__copied = []; try { Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (t) => { __copied.push(t); return Promise.resolve(); } } }); } catch (e) {}"
SHEET = """(() => { const a = document.querySelector('#a2hs'), sh = a.querySelector('.a2hs-sheet'), r = sh.getBoundingClientRect(), px = (e, k) => parseFloat(getComputedStyle(e)[k]);
  const yellow = (c) => { const m = (c || '').match(/[\\d.]+/g); if (!m) return false; let [R, G, B, A] = m.map(Number); if (A != null && A < .1) return false; R /= 255; G /= 255; B /= 255;
    const mx = Math.max(R, G, B), mn = Math.min(R, G, B), l = (mx + mn) / 2, d = mx - mn; if (!d) return false; const s = d / (1 - Math.abs(2 * l - 1)); if (s < .3 || d * 255 < 12) return false;
    let h = mx === R ? ((G - B) / d) % 6 : mx === G ? (B - R) / d + 2 : (R - G) / d + 4; h = (h * 60 + 360) % 360; return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= .85 || l <= .2)); };
  const lis = [...a.querySelectorAll('.a2hs-steps li')], act = a.querySelector('#a2hs-act');
  return { open: !a.hidden && getComputedStyle(a).display !== 'none', title: a.querySelector('#a2hs-title').textContent, sub: a.querySelector('#a2hs-sub').textContent,
    steps: lis.map((li) => { const t = li.querySelector('.a2hs-t'), sm = t.querySelector('small'); return (t.innerText.replace(sm ? sm.innerText : '', '')).replace(/\\s+/g, ' ').trim(); }),
    stepPx: lis.map((li) => px(li, 'fontSize')), weight: lis.map((li) => +getComputedStyle(li.querySelector('b') || li).fontWeight), icon: lis.map((li) => li.querySelector('.a2hs-badge').getBoundingClientRect().width),
    titlePx: px(a.querySelector('#a2hs-title'), 'fontSize'), act: act.hidden ? null : act.textContent.trim(), actH: act.hidden ? 0 : act.getBoundingClientRect().height,
    btns: [...a.querySelectorAll('.a2hs-btns button')].map((b) => b.textContent.trim()), btnH: Math.min(...[...a.querySelectorAll('.a2hs-btns button')].map((b) => b.getBoundingClientRect().height)),
    fits: r.top >= 0 && r.bottom <= innerHeight + 1 && r.left >= 0 && r.right <= innerWidth + 1 && sh.scrollHeight <= sh.clientHeight + 1, sheet: [r.left, r.top, r.right, r.bottom].map(Math.round),
    bad: [...a.querySelectorAll('*')].flatMap((e) => { const c = getComputedStyle(e); return ['color', 'backgroundColor', 'borderTopColor'].filter((k) => yellow(c[k])).map((k) => e.className + ' ' + k + ' ' + c[k]); }),
    arrow: getComputedStyle(a.querySelector('.a2hs-arrow')).display, push: !document.querySelector('#push-ask').hidden, card: !document.querySelector('#install-card').hidden, state: __chisme.a2hs }; })()"""
async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def go(pg, wait=2400):
    await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(wait); return await pg.evaluate(SHEET)
async def again(pg, wait=2200):
    await pg.reload(); await ready(pg); await pg.wait_for_timeout(wait); return await pg.evaluate(SHEET)
def simple(s, n):
    return len(s["steps"]) == n and all(len(t.split()) <= 5 for t in s["steps"]) and min(s["stepPx"]) >= 18 and min(s["weight"]) >= 800 and min(s["icon"]) >= 44 and s["titlePx"] >= 19

async def main():
    async with async_playwright() as p:
        print("== iPhone Safari (WebKit, iPhone 13)")
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["device_scale_factor"] = 2
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-push-engage', JSON.stringify({ stories: 6 }));"); pg = await ctx.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        s = await go(pg)
        check(not s["open"] and s["state"]["visits"] == 1, f"1st open: nothing (visit {s['state']['visits']})")
        s = await again(pg)
        check(s["open"] and s["state"]["visits"] == 2 and s["state"]["kind"] == "ios" and s["state"]["shows"] == 1, f"2nd open: the tutorial ({s['state']['kind']}, visit {s['state']['visits']})")
        check(simple(s, 3) and s["steps"] == ["Tap Share", "Tap Add to Home Screen", "Tap Add"], f"one screen, 3 steps of a few huge bold words, big icons ({s['steps']}, {s['stepPx']} px, icons {s['icon']})")
        check(s["fits"] and not s["bad"] and s["btns"] == ["Show me later", "Got it"] and s["btnH"] >= 48 and s["arrow"] != "none", f"fits, Fiesta colors (no yellow {s['bad'][:2]}), Show me later / Got it, the arrow at Safari's toolbar")
        check(not s["push"] and s["state"]["claim"], "no push card (or 'Home Screen first' tip) on the same visit, even with lots of stories read")
        await pg.screenshot(path=os.path.join(OUT, "a2hs-iphone.png"))
        await pg.click("#a2hs-ok"); await pg.wait_for_timeout(300)
        await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(300)
        check(not await pg.evaluate("!document.querySelector('#push-ask').hidden"), "…and not after it's closed, either (the push card waits for another visit)")
        s = await again(pg); s2 = await again(pg)
        check(not s["open"] and not s2["open"] and s["state"]["done"], "Got it → never again")
        # (v49: the notifications card has its own schedule, 1st open + every 5th, and wins its opens: notif_prompt_test)
        await ctx.close()
        # standalone, 320×568
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1 + "Object.defineProperty(navigator, 'standalone', { get: () => true });"); pg = await ctx.new_page()
        s = await go(pg); check(not s["open"] and s["state"]["standalone"], "installed Home Screen app (navigator.standalone): never")
        await ctx.close()
        d2 = dict(dev); d2["viewport"] = {"width": 320, "height": 568}
        ctx = await b.new_context(**d2); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1); pg = await ctx.new_page()
        s = await go(pg); check(s["open"] and s["fits"] and simple(s, 3), f"320×568: the whole thing fits, still big ({s['sheet']}, {s['stepPx']} px)")
        await ctx.close()
        # Show me later → the next open, once
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1); pg = await ctx.new_page()
        s = await go(pg); await pg.click("#a2hs-later"); await pg.wait_for_timeout(200)
        seen = [(await again(pg))["open"]]; await pg.click("#a2hs-later"); seen += [(await again(pg))["open"] for _ in range(2)]
        check(seen == [True, False, False], f"Show me later → back on the next open, at most once more ({seen})")
        await ctx.close()
        # Chrome on iPhone: open in Safari + Copy link
        d3 = dict(dev); d3["user_agent"] = re.sub(r"Version/[\d.]+", "CriOS/129.0.6668.46", dev["user_agent"])
        ctx = await b.new_context(**d3); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1); await ctx.add_init_script(CLIP); pg = await ctx.new_page()
        s = await go(pg)
        check(s["open"] and s["state"]["kind"] == "ios-other" and s["title"] == "Open Chisme in Safari" and simple(s, 3) and s["act"] == "📋 Copy link" and s["actH"] >= 50 and s["arrow"] == "none",
              f"iPhone, Chrome: 'Open Chisme in Safari' + a big 📋 Copy link ({s['steps']})")
        await pg.click("#a2hs-act"); await pg.wait_for_timeout(300)
        cp = await pg.evaluate("__copied"); toast = await pg.evaluate("document.querySelector('#share-toast').textContent")
        check(cp == [BASE + "/"] and "Link copied" in toast, f"…Copy link copies the app's link ({cp}, {toast!r})")
        await ctx.close(); await b.close()

        print("\n== Android Chrome (Chromium, Pixel 7) / desktop")
        b = await p.chromium.launch(); pdev = {k: v for k, v in p.devices["Pixel 7"].items() if k != "default_browser_type"}
        ctx = await b.new_context(**pdev); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1); await ctx.add_init_script(FAKE_BIP); pg = await ctx.new_page()
        s = await go(pg)
        check(s["open"] and s["state"]["kind"] == "android" and simple(s, 3) and s["steps"] == ["Tap ⋮", "Tap Install app", "Tap Install"] and s["arrow"] != "none" and not s["bad"],
              f"no install prompt from the browser: ⋮ → Install app → Install, arrow up at the menu ({s['steps']})")
        await pg.evaluate("__fakeBIP()"); await pg.wait_for_timeout(400); s = await pg.evaluate(SHEET)
        check(s["state"]["kind"] == "android-install" and s["act"] == "📲 Install" and s["actH"] >= 50 and simple(s, 1) and not s["card"] and s["fits"] and not s["bad"],
              f"the browser offers install → one big 📲 Install button (one tap), no inline install card on top ({s['steps']}, card {s['card']})")
        await pg.screenshot(path=os.path.join(OUT, "a2hs-android.png"))
        await pg.click("#a2hs-act"); await pg.wait_for_timeout(400)
        st = await pg.evaluate("({ p: __prompted, open: !document.querySelector('#a2hs').hidden, done: __chisme.a2hs.done, key: localStorage.getItem('chisme-install-card-dismissed') })")
        check(st == {"p": 1, "open": False, "done": True, "key": "1"}, f"Install → the browser's install prompt, then the tutorial's done for good (no inline card later) {st}")
        await ctx.close()
        ctx = await b.new_context(viewport={"width": 1280, "height": 800}); await ctx.add_init_script(QUIET); await ctx.add_init_script(VISIT1); pg = await ctx.new_page()
        s = await go(pg); check(not s["open"] and s["state"]["kind"] == "desktop", "desktop: skipped")
        await ctx.close(); await b.close()
        check(not errs, f"no page errors ({errs[:2]})")
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)
asyncio.run(main())
