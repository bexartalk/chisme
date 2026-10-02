"""v45 alerts in real browsers, against the local server (CHISME_URL, default http://localhost:8211) started with an env
that has the VAPID keys + ADMIN_TOKEN + PUSH_TICK_SECRET + PUSH_TEST=1 (CHISME_ENV, see push_test.py):
    xvfb-run -a ./venv/bin/python push_v45_ui_test.py
Chromium runs headed (under Xvfb) with Chrome's push service enabled, so the subscription is a REAL one
(fcm.googleapis.com) and the sends really go out through FCM to the browser's service worker:
  • the soft prompt: never on the first visit, not before a few stories were opened, then once (Tía's voice) → Sí, avísame
  • Settings: the on/off switch; Turn off → gone from the server and from the browser
  • /stats: the owner's send box (subscriber count, confirm dialog, sent/failed after) → a real push arrives and shows
  • the auto-send switch + a big-news auto push (fake feed + clock via /api/push/tick, PUSH_TEST=1) → arrives, logged on /stats
  • a subscription the browser dropped: the push service answers 404/410 → pruned on the next send
  • a notification's link opens the story in the in-app reader (app open: SW message; app closed: ?story=…)
  • no yellow in the prompt, the iOS tip, the Settings group and the /stats panels
WebKit (iPhone 13, Safari, not installed): the "Add to Home Screen first" tip instead of the prompt; "Show me how" opens
the Add to Home Screen tutorial; the Settings switch explains why it's off.
Node: the service worker's notificationclick focuses an open Chisme window (never /stats) and posts the link, or opens
/?story=… when the app isn't open; outside links become in-app reader links.
Screenshots → CHISME_SHOTS (default /workspace/chisme-push-shots)."""
import asyncio, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211"); URL = BASE + "/"
ENV = os.environ.get("CHISME_ENV", "/workspace/secrets/chisme-local.env")
env = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l and not l.startswith("#"))
STORE = env.get("PUSH_STORE_FILE", "/tmp/chisme-push.json")
SHOTS = os.environ.get("CHISME_SHOTS", "/workspace/chisme-push-shots"); os.makedirs(SHOTS, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); %s }"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
subs = lambda: json.load(open(STORE)) if os.path.exists(STORE) else {}
CT = ZoneInfo("America/Chicago")

YELLOW = r"""(sel) => { const yellow = ([r, g, b, a]) => { if (a != null && a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.05) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= 0.85 || l <= 0.2)); };
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const els = [...document.querySelectorAll(sel)].flatMap((r) => [r, ...r.querySelectorAll('*')]).filter((e) => e.getClientRects().length && !['IMG'].includes(e.tagName));
  const bad = [];
  for (const e of els) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor, cs.borderLeftColor, cs.borderBottomColor, cs.outlineColor])
      if (rgb(v).some(yellow)) bad.push((e.id || e.className || e.tagName) + ' ' + String(v).slice(0, 50)); }
  return { n: els.length, bad: [...new Set(bad)].slice(0, 6) }; }"""

async def notes(pg, title, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        n = await pg.evaluate("(async () => (await (await navigator.serviceWorker.ready).getNotifications()).map(n => ({ t: n.title, b: n.body, u: n.data && n.data.url, tag: n.tag })))()")
        hit = [x for x in n if x["t"] == title]
        if hit:
            return hit[0], round(time.time() - t0, 1)
        await asyncio.sleep(1)
    return None, timeout

REAL = {"delivered": 0, "cdp": 0}
async def shown(ctx, pg, payload, real_wait=20):
    """Wait for the REAL push (FCM → Chrome) to show; if Chrome's push connection can't reach FCM from this sandbox
    (mtalk.google.com:5228 is blocked here), deliver the same payload to the service worker with CDP instead."""
    n, secs = await notes(pg, payload["title"], real_wait)
    if n:
        REAL["delivered"] += 1; return n, f"delivered by FCM in {secs} s"
    cdp = await ctx.new_cdp_session(pg); regs = []
    cdp.on("ServiceWorker.workerRegistrationUpdated", lambda e: regs.extend(e["registrations"]))
    await cdp.send("ServiceWorker.enable"); await asyncio.sleep(1)
    reg = next((r for r in regs if r["scopeURL"].startswith(URL)), None)
    if not reg:
        return None, "no SW registration"
    await cdp.send("ServiceWorker.deliverPushMessage", {"origin": BASE, "registrationId": reg["registrationId"], "data": json.dumps(payload)})
    n, secs = await notes(pg, payload["title"], 10)
    REAL["cdp"] += 1
    return n, "FCM accepted it, but this sandbox blocks Chrome's FCM connection: same payload delivered to the SW via CDP"

async def ready(pg):
    await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story h3 a')", timeout=120000)

async def open_story(pg, i):
    a = pg.locator("#near-list .story h3 a").nth(i)
    await a.scroll_into_view_if_needed(); await a.click()
    await pg.wait_for_function("document.querySelector('#player').open", timeout=8000)
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)

async def chromium_part(p):
    for f in (STORE, STORE.rsplit(".", 1)[0] + ".state.json"):
        if os.path.exists(f): os.remove(f)
    prof = tempfile.mkdtemp(prefix="chisme-push-chrome-")
    ctx = await p.chromium.launch_persistent_context(prof, headless=False, executable_path="/usr/bin/google-chrome", args=["--no-sandbox"],
        ignore_default_args=["--disable-background-networking", "--disable-component-update", "--disable-sync"],   # Chrome's push service (GCM/FCM) needs these on
        viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    await ctx.grant_permissions(["notifications"], origin=BASE)
    await ctx.add_init_script(INIT % "")
    await ctx.add_init_script("if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');")   # v49 tip: settings_tip_test
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    # 1-2. v49: the notifications card (a popup) on the 1st open (then every 5th open until alerts are on: notif_prompt_test)
    await pg.goto(URL); await ready(pg)
    await pg.wait_for_function("!document.querySelector('#push-ask').hidden", timeout=15000); await pg.wait_for_timeout(500)
    ask = await pg.evaluate("({ t: document.querySelector('#push-ask-t').textContent, s: document.querySelector('#push-ask-s').textContent, yes: document.querySelector('#push-ask-yes').textContent, no: document.querySelector('#push-ask-no').textContent, dialogs: [...document.querySelectorAll('dialog')].filter(d => d.open).length, kind: document.querySelector('#push-ask').dataset.kind })")
    check(ask["kind"] == "ask" and ask["t"] == "Allow notifications 🔔 for the latest chisme 👀" and ask["yes"] == "Turn on" and ask["no"] == "Not now", f"1st open: the notifications card '{ask['t']}' [{ask['yes']}] [{ask['no']}]")
    y = await pg.evaluate(YELLOW, "#push-ask"); check(not y["bad"], f"prompt: no yellow ({y['n']} elements) {y['bad']}")
    await pg.screenshot(path=os.path.join(SHOTS, "1-optin-prompt-phone.png"))
    # 3. Turn on → a REAL push subscription, stored on the server
    await pg.tap("#push-ask-yes")
    await pg.wait_for_function("__chisme.pushPrefs.on", timeout=60000); await pg.wait_for_timeout(800)
    recs = list(subs().values()); ep = recs[0]["sub"]["endpoint"] if recs else ""
    host = urllib.parse.urlsplit(ep).hostname or ""
    check(len(recs) == 1 and host.endswith(("googleapis.com", "push.services.mozilla.com")) and recs[0]["news"], f"subscribed for real: the server stored a {host} endpoint (news on)")
    done = await pg.evaluate("document.querySelector('#push-ask').textContent")
    check("¡Listo!" in done, f"the prompt says thanks: '{done[:60]}'")
    await pg.wait_for_function("document.querySelector('#push-ask').hidden", timeout=8000)   # …and closes by itself
    # 4. Settings: the switch is on
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    st = await pg.evaluate("({ on: document.querySelector('#set-push').checked, role: document.querySelector('#set-push').getAttribute('role'), l: document.querySelector('#set-push-l').textContent, status: document.querySelector('#set-push-status').textContent, news: document.querySelector('#set-push-news').checked && !document.querySelector('#set-push-news').disabled })")
    check(st["on"] and st["role"] == "switch" and st["news"] and st["status"].startswith("Alerts are on"), f"Settings: the switch is on ('{st['l']}'; {st['status'][:40]})")
    y = await pg.evaluate(YELLOW, "#set-alerts"); check(not y["bad"], f"Settings alerts group: no yellow ({y['n']} elements) {y['bad']}")
    await pg.evaluate("""(() => { const g = document.querySelector('#set-alerts'); g.scrollIntoView({ block: 'start' });
      let sc = g.parentElement; while (sc && sc.scrollHeight <= sc.clientHeight + 1) sc = sc.parentElement; if (sc) sc.scrollTop -= 70; })()"""); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(SHOTS, "3-settings-toggle.png"))
    await pg.tap("#settings-close"); await pg.wait_for_timeout(300)
    # 5. the owner's send box on /stats → a real push through FCM
    adm = await ctx.new_page(); adm.on("pageerror", lambda e: errs.append("stats: " + str(e)[:160]))
    await adm.set_viewport_size({"width": 430, "height": 932})
    await adm.goto(BASE + "/stats?key=" + urllib.parse.quote(env["ADMIN_TOKEN"]))
    info = await adm.evaluate("({ count: document.querySelector('#push-count b').textContent, msg: document.querySelector('#pf-msg').value, url: location.href })")
    check(info["count"] == "1" and info["msg"] == "¡Órale, new chisme! 👀" and "key=" not in info["url"], f"/stats: {info['count']} subscriber, default message '{info['msg']}', key dropped from the address")
    await adm.fill("#pf-title", "Chisme"); await adm.fill("#pf-link", "https://www.ksat.com/news/local/")
    await adm.click("#pf-send"); await adm.wait_for_function("document.querySelector('#pf-confirm').open", timeout=5000)
    cf = await adm.evaluate("({ h: document.querySelector('#pf-confirm-h').textContent, t: document.querySelector('#pf-pt').textContent, m: document.querySelector('#pf-pm').textContent })")
    check(cf["h"] == "Send this to 1 phone?" and cf["m"] == "¡Órale, new chisme! 👀", f"confirm dialog first: '{cf['h']}'")
    await adm.screenshot(path=os.path.join(SHOTS, "4b-stats-confirm-dialog.png"))
    await adm.click("#pf-yes")
    await adm.wait_for_function("/^(Sent|Not sent)/.test(document.querySelector('#pf-res').textContent)", timeout=60000)
    res = await adm.evaluate("document.querySelector('#pf-res').textContent")
    check(res.startswith("Sent: 1 · Failed: 0"), f"after sending: '{res}'")
    check(res.startswith("Sent: 1"), "the REAL push service (FCM) accepted the owner's push (HTTP 201; VAPID + encryption checked by Google)")
    n, how = await shown(ctx, pg, {"title": "Chisme", "body": "¡Órale, new chisme! 👀", "url": "/?story=https%3A%2F%2Fwww.ksat.com%2Fnews%2Flocal%2F&t=Chisme&s=&p=0#news", "tag": "chisme-owner"})
    check(bool(n) and n["b"] == "¡Órale, new chisme! 👀" and "story=https%3A%2F%2Fwww.ksat.com" in (n["u"] or ""), f"the service worker shows '{n and n['t']}: {n and n['b']}' (link: in-app reader) [{how}]")
    # 6. auto-send switch + a big-news auto push (fake feed + fake clock: PUSH_TEST=1)
    await adm.click("label.sw"); await adm.wait_for_function("document.querySelector('#auto-on-l').textContent === 'Auto-send is on'", timeout=10000)
    now = datetime.now(CT).replace(hour=12, minute=0, second=0, microsecond=0).timestamp()
    big = {"title": "BREAKING: SAPD says active shooter at North Star Mall, shoppers told to shelter in place", "link": "https://example.com/v45-ui/big-1",
           "source": "KSAT", "published": now - 300, "summary": "", "related": [{"source": "KENS 5"}, {"source": "Express-News"}], "tier": "city"}
    routine = {"title": "Fifth suspect arrested, charged in fatal Bexar County abduction", "link": "https://example.com/v45-ui/r1", "source": "KENS 5", "published": now - 200, "related": []}
    j = httpx.post(BASE + "/api/push/tick", headers={"Authorization": "Bearer " + env["PUSH_TICK_SECRET"]}, json={"now": now, "fake": {"news": [routine, big], "alerts": []}}, timeout=90).json()
    check(j["auto"]["result"].startswith("sent") and j["auto"]["sent"] == 1, f"auto-send on + a major story: {j['auto']['result'][:70]}")
    q = urllib.parse.urlencode({"story": big["link"], "t": big["title"], "s": big["source"], "p": int(big["published"])})
    n, how = await shown(ctx, pg, {"title": "Breaking news", "body": big["title"] + " — KSAT", "url": f"/?{q}#news", "tag": "chisme-news-x", "urgent": True})
    check(bool(n) and n["b"].startswith("BREAKING: SAPD says active shooter") and n["u"].startswith("/?story=https%3A%2F%2Fexample.com%2Fv45-ui%2Fbig-1"), f"auto push (FCM accepted it) shows '{n and n['b'][:40]}…' [{how}]")
    j2 = httpx.post(BASE + "/api/push/tick", headers={"Authorization": "Bearer " + env["PUSH_TICK_SECRET"]}, json={"now": now + 900, "fake": {"news": [routine, big], "alerts": []}}, timeout=90).json()
    check(j2["auto"]["result"] == "nothing major", f"15 min later, same feed: nothing (dedupe) ({j2['auto']['result']})")
    await adm.reload(); await adm.wait_for_timeout(500)
    pan = await adm.evaluate("({ on: document.querySelector('#auto-on').checked, log: [...document.querySelectorAll('.push.auto .plog li')].map(li => li.textContent).join(' | '), today: document.querySelector('.push.auto .pill').textContent, sends: document.querySelectorAll('.push:not(.auto) .plog li').length })")
    check(pan["on"] and "active shooter" in pan["log"] and "sent 1" in pan["log"] and pan["today"].startswith("Today:") and pan["sends"] == 1, f"/stats: switch on, log '{pan['log'][:70]}…', {pan['today']}, 1 recent owner send")
    y = await adm.evaluate(YELLOW, ".push"); check(not y["bad"], f"/stats push panels: no yellow ({y['n']} elements) {y['bad']}")
    await adm.screenshot(path=os.path.join(SHOTS, "4-stats-admin-send-and-auto.png"), full_page=True)
    await adm.evaluate("document.querySelector('#push-h').scrollIntoView()"); await adm.wait_for_timeout(200)
    await adm.screenshot(path=os.path.join(SHOTS, "4a-stats-admin-panels-viewport.png"))
    # 7. the notification's link opens the story in the in-app reader
    await pg.bring_to_front()
    await pg.evaluate("navigator.serviceWorker.dispatchEvent(new MessageEvent('message', { data: { chismeOpen: %r } }))" % n["u"])
    await pg.wait_for_function("document.querySelector('#player').open", timeout=8000)
    r = await pg.evaluate("({ t: document.querySelector('#player-title').textContent, orig: document.querySelector('#player-orig .orig-link')?.href, view: __chisme.view, pages: 0 })")
    check(r["t"].startswith("BREAKING: SAPD") and r["orig"] == "https://example.com/v45-ui/big-1" and r["view"] == "news" and len(ctx.pages) == 2, f"tap with the app open → '{r['t'][:40]}…' in Chisme's reader (no new tab)")
    await pg.keyboard.press("Escape")
    await pg.goto(URL + n["u"][1:]); await ready(pg)
    await pg.wait_for_function("document.querySelector('#player').open", timeout=10000)
    r = await pg.evaluate("({ t: document.querySelector('#player-title').textContent, q: location.search })")
    check(r["t"].startswith("BREAKING: SAPD") and r["q"] == "", "tap with the app closed → Chisme opens on the story in the reader; the address is cleaned up")
    await pg.keyboard.press("Escape")
    # 8. turn off in Settings → gone from the server and the browser
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    await pg.locator("label:has(#set-push)").scroll_into_view_if_needed(); await pg.tap("label:has(#set-push)")
    await pg.wait_for_function("!__chisme.pushPrefs.on", timeout=15000); await pg.wait_for_timeout(600)
    bsub = await pg.evaluate("(async () => !!(await (await navigator.serviceWorker.ready).pushManager.getSubscription()))()")
    check(subs() == {} and not bsub and not await pg.evaluate("document.querySelector('#set-push').checked"), "switch off: unsubscribed on the server and in the browser")
    # 9. back on, then the browser drops it without telling the server: the next send prunes it (404/410 from FCM)
    await pg.tap("label:has(#set-push)"); await pg.wait_for_function("__chisme.pushPrefs.on", timeout=60000); await pg.wait_for_timeout(500)
    on_again = len(subs()) == 1
    await pg.evaluate("(async () => { const s = await (await navigator.serviceWorker.ready).pushManager.getSubscription(); await s.unsubscribe(); })()")
    await pg.wait_for_timeout(3000)
    pr = {}
    for _ in range(4):   # FCM can take a moment to forget a token
        await adm.goto(BASE + "/stats"); await adm.click("#pf-send"); await adm.wait_for_function("document.querySelector('#pf-confirm').open"); await adm.click("#pf-yes")
        await adm.wait_for_function("/^(Sent|Not sent)/.test(document.querySelector('#pf-res').textContent)", timeout=60000)
        pr = {"res": await adm.evaluate("document.querySelector('#pf-res').textContent"), "left": len(subs())}
        if pr["left"] == 0: break
        await asyncio.sleep(5)
    check(on_again and pr["left"] == 0 and "removed" in pr["res"], f"a subscription the browser dropped: FCM says it's gone → pruned ('{pr.get('res')}')")
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close(); shutil.rmtree(prof, ignore_errors=True)

async def webkit_part(p):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    b = await p.webkit.launch()
    ctx = await b.new_context(**dev); await ctx.add_init_script("if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');")
    await ctx.add_init_script(INIT % "localStorage.setItem('chisme-visits','1'); localStorage.setItem('chisme-push-engage', JSON.stringify({stories: 2}));")
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await ready(pg)
    await pg.wait_for_function("!document.querySelector('#push-ask').hidden", timeout=15000)
    tip = await pg.evaluate("({ kind: document.querySelector('#push-ask').dataset.kind, t: document.querySelector('#push-ask-t').textContent, s: document.querySelector('#push-ask-s').textContent, yes: document.querySelector('#push-ask-yes').textContent, no: document.querySelector('#push-ask-no').textContent })")
    check(tip["kind"] == "ios" and "Home Screen" in tip["t"] and "Home Screen" in tip["s"] and tip["yes"] == "Show me how" and tip["no"] == "Not now", f"iPhone Safari (not installed): '{tip['t']}' instead of the prompt (and it wins over the tutorial due this visit)")
    y = await pg.evaluate(YELLOW, "#push-ask"); check(not y["bad"], f"iOS tip: no yellow {y['bad']}")
    await pg.wait_for_timeout(600)
    await pg.screenshot(path=os.path.join(SHOTS, "2-ios-add-to-home-screen-tip.png"))
    await pg.tap("#push-ask-yes"); await pg.wait_for_timeout(600)
    a2 = await pg.evaluate("({ a2: !document.querySelector('#a2hs').hidden, ask: !document.querySelector('#push-ask').hidden })")
    check(a2["a2"] and not a2["ask"], "'Show me how' opens the Add to Home Screen tutorial")
    await pg.tap("#a2hs-ok"); await pg.reload(); await ready(pg); await pg.wait_for_timeout(2500)
    check(await pg.evaluate("document.querySelector('#push-ask').hidden"), "it doesn't come back on the next open (every 5th open)")
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    st = await pg.evaluate("({ dis: document.querySelector('#set-push').disabled, s: document.querySelector('#set-push-status').textContent })")
    check(st["dis"] and "Home Screen" in st["s"], f"Settings on iPhone Safari: switch disabled, '{st['s'][:70]}…'")
    check(not errs, f"no page errors ({errs[:2]})")
    await b.close()

SW_HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const code = fs.readFileSync(process.argv[2], 'utf8');
function run(wins) {
  const L = {}, log = [];
  const self = { location: new URL('https://chisme.test/sw.js'), addEventListener: (t, f) => (L[t] = f), registration: {},
    clients: { matchAll: async () => wins, openWindow: async (u) => { log.push(['open', u]); return null; }, claim: async () => {} }, skipWaiting: async () => {} };
  vm.runInNewContext(code, { self, caches: {}, fetch: () => {}, URL, Response: function () {}, Headers: function () {}, Request: function () {}, console, atob: (s) => Buffer.from(s, 'base64').toString('binary') });
  return { L, log };
}
const win = (url, extra = {}) => ({ url, focused: false, visibilityState: 'hidden', ...extra, msgs: [], focus() { this.f = true; return Promise.resolve(this); }, postMessage(m) { this.msgs.push(m); } });
async function click(wins, url) {
  const { L, log } = run(wins); let p; const ev = { notification: { data: { url }, close() { this.closed = true; } }, waitUntil: (x) => (p = x) };
  L.notificationclick(ev); await p; return { log, closed: ev.notification.closed };
}
(async () => {
  const out = {};
  const stats = win('https://chisme.test/stats', { focused: true }), app = win('https://chisme.test/#weather');
  let r = await click([stats, app], '/?story=https%3A%2F%2Fexample.com%2Fs&t=T#news');
  out.focusApp = { appFocused: !!app.f, statsFocused: !!stats.f, msg: app.msgs[0], opened: r.log.length, closed: r.closed };
  r = await click([stats], '/?story=https%3A%2F%2Fexample.com%2Fs#news');
  out.openWhenOnlyStats = r.log;
  r = await click([], 'https://evil.example/x?y=1');
  out.outside = r.log;
  r = await click([], '/stats');
  out.stats = r.log;
  r = await click([], 'javascript:alert(1)');
  out.js = r.log;
  console.log(JSON.stringify(out));
})();
"""

def sw_part():
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(SW_HARNESS)
    o = json.loads(subprocess.run(["node", f.name, os.path.join(HERE, "static", "sw.js")], capture_output=True, text=True, timeout=30).stdout)
    fa = o["focusApp"]
    check(fa["appFocused"] and not fa["statsFocused"] and fa["msg"] == {"chismeOpen": "/?story=https%3A%2F%2Fexample.com%2Fs&t=T#news"} and fa["opened"] == 0 and fa["closed"],
          "SW notificationclick: focuses the open Chisme window (not the /stats tab) and hands it the story link")
    check(o["openWhenOnlyStats"] == [["open", "https://chisme.test/?story=https%3A%2F%2Fexample.com%2Fs#news"]], f"no Chisme window open: opens the app on the story ({o['openWhenOnlyStats']})")
    check(o["outside"] == [["open", "https://chisme.test/?story=https%3A%2F%2Fevil.example%2Fx%3Fy%3D1#news"]], "an outside URL becomes an in-app reader link, never a browser tab")
    check(o["stats"] == [["open", "https://chisme.test/"]] and o["js"] == [["open", "https://chisme.test/"]], "/stats or javascript: in a payload → just the app")
    sw = open(os.path.join(HERE, "static", "sw.js")).read()
    m = re.search(r'const VERSION = "chisme-v(\d+)(?:\.\d+)?";', sw); n = int(m.group(1)) if m else 0   # v46: v45 or any later build
    check(n >= 45 and f'window.CHISME_APP_BUILD = "{n}";' in open(os.path.join(HERE, "static", "app.js")).read(), f"service worker cache chisme-v{n} (app build {n}, v45 or later)")

async def main():
    sw_part()
    async with async_playwright() as p:
        await webkit_part(p)
        await chromium_part(p)
    print(f"   note: notifications delivered by FCM end to end: {REAL['delivered']}; via CDP after FCM accepted them: {REAL['cdp']}")
    print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
