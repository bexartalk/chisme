"""v49: the "Allow notifications 🔔 for the latest chisme 👀" card (a popup with Turn on / Not now).
  Chromium Pixel 7 (Android):
  - 1st launch: not on top of the location card; it shows right after it closes. Big bold text, Fiesta colours, no
    yellow, fits the screen. Screenshot: notif-prompt.png. Not now → gone for this open.
  - Then every 5th open: opens 2-5 nothing, open 6 the card, open 7 nothing.
  - Turn on = the existing subscribe flow (permission prompt → pushManager.subscribe → POST /api/push/subscribe; the push
    service is faked here, push_test / push_v45_ui_test cover the real one) → "¡Listo!" → gone, and never again (open 11).
  - Blocked in the browser: never shows. Denied at the prompt: the card closes.
  - One popup per open: on an open where both are due, the card wins and the Home Screen tutorial waits for the next open.
  WebKit iPhone 13 (Safari, not the Home Screen app), dark: "Add Chisme to your Home Screen first 📲" → Show me how opens
  the tutorial.
Against the local server (CHISME_URL, default http://localhost:8211), which must have push configured."""
import ast, asyncio, json, os
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1');"
NO_A2 = "if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));"
NO_TIP = "if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
FAKE_PUSH_ONLY = """(() => { if (!window.PushManager) return;
  const mk = () => ({ endpoint: 'https://push.example.test/sub/1', options: {}, toJSON() { return { endpoint: this.endpoint, keys: { p256dh: 'BTEST', auth: 'ATEST' } }; },
    unsubscribe: async () => { localStorage.removeItem('__fakeSub'); return true; } });
  PushManager.prototype.getSubscription = async function () { return localStorage.getItem('__fakeSub') ? mk() : null; };
  PushManager.prototype.subscribe = async function () { localStorage.setItem('__fakeSub', '1'); window.__subscribed = (window.__subscribed || 0) + 1; return mk(); }; })();"""
# headless Chromium reports notifications as "denied" up front; a phone starts at "default". So the permission is faked too:
# localStorage __perm (the state), __permAnswer (what the user taps in the browser's prompt).
FAKE_PERM = """try { Object.defineProperty(Notification, 'permission', { configurable: true, get: () => localStorage.getItem('__perm') || 'default' });
  Notification.requestPermission = async () => { const a = localStorage.getItem('__permAnswer') || 'denied'; localStorage.setItem('__perm', a); return a; }; } catch (e) {}"""
ALLOW = "localStorage.setItem('__permAnswer', 'granted');"
BLOCKED = "localStorage.setItem('__perm', 'denied');"
FAKE_PUSH = FAKE_PUSH_ONLY + "\n" + FAKE_PERM
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
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push((e.id || e.className || e.tagName) + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
CARD = """() => { const a = document.querySelector('#push-ask'), c = a.querySelector('.notif-card'), r = c.getBoundingClientRect(), t = a.querySelector('#push-ask-t');
  const y = a.querySelector('#push-ask-yes'), n = a.querySelector('#push-ask-no'), cs = (e) => getComputedStyle(e);
  return { open: !a.hidden && cs(a).display !== 'none', kind: a.dataset.kind || null, t: t.textContent, s: a.querySelector('#push-ask-s').textContent,
    yes: y.hidden ? null : y.textContent, no: n.hidden ? null : n.textContent, tPx: parseFloat(cs(t).fontSize), tW: +cs(t).fontWeight,
    yesH: y.getBoundingClientRect().height, noH: n.getBoundingClientRect().height, yesPx: parseFloat(cs(y).fontSize), yesBg: cs(y).backgroundColor,
    fits: r.top >= 0 && r.bottom <= innerHeight + 1 && r.left >= 0 && r.right <= innerWidth + 1,
    a2: __chisme.a2hs.open, a2next: __chisme.a2hs.next, visits: __chisme.a2hs.visits, tip: __chisme.settingsTip.shown, loc: !document.querySelector('#loc-panel').hidden, st: __chisme.notif }; }"""

async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def card(pg): return await pg.evaluate(CARD)
async def wait_card(pg, timeout=10000):
    try: await pg.wait_for_function("__chisme.notif.open", timeout=timeout); return True
    except Exception: return False
async def chromium_ctx(b, p, init, perms=None, scheme="light"):
    dev = dict(p.devices["Pixel 7"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev, color_scheme=scheme, permissions=perms or [])
    for s in init: await ctx.add_init_script(s)
    subs = []
    async def sub_route(route):
        if route.request.method == "POST": subs.append(json.loads(route.request.post_data or "{}"))
        await route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
    await ctx.route("**/api/push/subscribe", sub_route)
    await ctx.route("**/api/push/unsubscribe", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok": true}'))
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs, subs

async def main():
    async with async_playwright() as p:
        allerrs = []
        b = await p.chromium.launch()
        print("== Android (Chromium Pixel 7): first launch, then every 5th open")
        ctx, pg, errs, subs = await chromium_ctx(b, p, [NO_A2, NO_TIP, FAKE_PUSH])
        await pg.goto(BASE + "/"); await ready(pg); await pg.wait_for_timeout(4000)
        c = await card(pg)
        check(c["loc"] and not c["open"], "1st launch: the location card is up, the notifications card waits")
        await pg.click("#loc-close")
        ok = await wait_card(pg); await pg.wait_for_timeout(600); c = await card(pg)
        check(ok and c["open"] and c["kind"] == "ask" and not c["loc"], "…and it shows right after the location card closes")
        check(c["t"] == "Allow notifications 🔔 for the latest chisme 👀" and c["yes"] == "Turn on" and c["no"] == "Not now", f"the words: {c['t']!r} · {c['yes']} / {c['no']}")
        check(c["tPx"] >= 22 and c["tW"] >= 800 and c["yesH"] >= 54 and c["noH"] >= 48 and c["yesPx"] >= 20, f"big bold text ({c['tPx']} px / {c['tW']}, Turn on {c['yesPx']} px), big buttons ({c['yesH']:.0f} / {c['noH']:.0f} px)")
        bad = await pg.evaluate(SCAN, "#push-ask")
        check(not bad and c["fits"] and c["yesBg"] in ("rgb(239, 66, 111)", "rgb(255, 61, 139)"), f"Fiesta colours (Turn on {c['yesBg']}), no yellow {bad[:3]}, fits the screen")
        check(not c["a2"] and not c["tip"], "nothing else on top (no tutorial, no Settings tip)")
        await pg.screenshot(path=os.path.join(OUT, "notif-prompt.png"))
        await pg.click("#push-ask-no"); await pg.wait_for_timeout(300); c = await card(pg)
        check(not c["open"] and c["st"]["how"] == "later", f"Not now: gone for this open ({c['st']['how']})")
        seen = []
        for n in range(2, 8):
            await pg.reload(); await ready(pg)
            shown = await wait_card(pg, 4500 if n != 6 else 10000); seen.append((n, shown))
            if shown: await pg.click("#push-ask-no"); await pg.wait_for_timeout(200)
        check(seen == [(2, False), (3, False), (4, False), (5, False), (6, True), (7, False)], f"every 5th open: {seen}")
        allerrs += errs; await ctx.close()

        print("== Turn on (the existing subscribe flow), then never again")
        ctx, pg, errs, subs = await chromium_ctx(b, p, [SETUP, NO_A2, NO_TIP, ALLOW, FAKE_PUSH])
        await pg.goto(BASE + "/"); await ready(pg)
        check(await wait_card(pg), "open 1 (setup already done): the card")
        await pg.click("#push-ask-yes")
        await pg.wait_for_function("document.querySelector('#push-ask-t').textContent.includes('Listo')", timeout=10000)
        st = await pg.evaluate("({ prefs: JSON.parse(localStorage.getItem('chisme-push') || '{}'), subscribed: window.__subscribed || 0, sw: document.querySelector('#set-push').checked })")
        check(st["prefs"].get("on") and st["subscribed"] == 1 and len(subs) == 1 and subs[0].get("subscription", {}).get("endpoint") and st["sw"],
              f"Turn on → permission → subscribe → POST /api/push/subscribe ({len(subs)} posts), Settings switch on")
        await pg.wait_for_timeout(4800)
        check(not (await card(pg))["open"], "\"¡Listo!\" then the card goes away by itself")
        await pg.evaluate("localStorage.setItem('chisme-notif', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('chisme-notif')), { n: 10 })))")
        await pg.reload(); await ready(pg)
        due = await pg.evaluate("__chisme.notif.due")
        check(due and not await wait_card(pg, 6000), "subscribed: never again (not even on a scheduled open, open 11)")
        allerrs += errs; await ctx.close()

        print("== blocked in the browser")
        ctx, pg, errs, subs = await chromium_ctx(b, p, [SETUP, NO_A2, NO_TIP, BLOCKED, FAKE_PUSH])
        await pg.goto(BASE + "/"); await ready(pg)
        check(not await wait_card(pg, 6000) and await pg.evaluate("__chisme.notif.phase") == "none", "notifications blocked: the card never shows")
        allerrs += errs; await ctx.close()

        print("== denied at the browser's prompt")
        ctx, pg, errs, subs = await chromium_ctx(b, p, [SETUP, NO_A2, NO_TIP, FAKE_PUSH])
        await pg.goto(BASE + "/"); await ready(pg); await wait_card(pg)
        await pg.click("#push-ask-yes"); await pg.wait_for_timeout(1500)
        c = await card(pg); perm = await pg.evaluate("Notification.permission")
        check(not c["open"] and c["st"]["how"] in ("blocked", "no") and not subs, f"prompt answered {perm}: the card closes ({c['st']['how']}), nothing subscribed")
        await pg.evaluate("localStorage.setItem('chisme-notif', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('chisme-notif')), { n: 5 })))")
        await pg.reload(); await ready(pg)
        check(not await wait_card(pg, 6000), "…and now that it's blocked, not even on the next scheduled open")
        allerrs += errs; await ctx.close()

        print("== one popup per open: the card wins over the Home Screen tutorial")
        ctx, pg, errs, subs = await chromium_ctx(b, p, [SETUP, NO_TIP, FAKE_PUSH,
            "if (!localStorage.getItem('chisme-visits')) { localStorage.setItem('chisme-visits','1'); localStorage.setItem('chisme-notif', JSON.stringify({ n: 5, shows: 1 })); }"])
        await pg.goto(BASE + "/"); await ready(pg)
        ok = await wait_card(pg); c = await card(pg)
        check(ok and not c["a2"] and c["visits"] == 2 and c["st"]["n"] == 6, f"visit 2 (tutorial due) + open 6 (card due): the card, no tutorial")
        await pg.click("#push-ask-no"); await pg.wait_for_timeout(5000); c = await card(pg)
        check(not c["a2"] and c["a2next"] == 3, f"after Not now: still no tutorial on this open (it moved to the next open: {c['a2next']})")
        await pg.reload(); await ready(pg)
        try: await pg.wait_for_function("__chisme.a2hs.open", timeout=10000); a2 = True
        except Exception: a2 = False
        check(a2 and not (await card(pg))["open"], "the next open: the tutorial, no card")
        allerrs += errs; await ctx.close()
        await b.close()

        print("== iPhone Safari (WebKit iPhone 13, dark): Home Screen first")
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev, color_scheme="dark")
        for s in (SETUP, NO_A2, NO_TIP): await ctx.add_init_script(s)
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        await pg.goto(BASE + "/"); await ready(pg)
        ok = await wait_card(pg); await pg.wait_for_timeout(500); c = await card(pg)
        check(ok and c["kind"] == "ios" and c["t"] == "Add Chisme to your Home Screen first 📲" and "Home Screen" in c["s"] and c["yes"] == "Show me how" and c["no"] == "Not now",
              f"not the Home Screen app: explains first ({c['t']!r} · {c['yes']} / {c['no']})")
        bad = await pg.evaluate(SCAN, "#push-ask")
        check(not bad and c["fits"], f"dark: Fiesta colours, no yellow {bad[:3]}")
        await pg.screenshot(path="/tmp/notif-prompt-ios-dark.png")
        await pg.click("#push-ask-yes"); await pg.wait_for_timeout(600); c = await card(pg)
        check(not c["open"] and c["a2"], "Show me how → the Home Screen tutorial")
        allerrs += errs; await ctx.close(); await b.close()
        check(not allerrs, f"no page errors {allerrs[:3]}")
    print("\nALL PASS" if not fails else f"\n{fails} FAILED")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
