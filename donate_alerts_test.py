"""Donation card + 'New chisme ↑' pill + alerts (Web Push) UI. WebKit iPhone 13 for the page, Chromium for push.
Run against the local server started with the push test env (see push_test.py). Screenshots: donate-news.png
(light | dark), donate-settings.png, new-chisme-pill.png, alerts-settings.png.

Headless browsers can't reach a real push service, so in Chromium the PushManager is stubbed with a subscription
whose keys this test owns; everything after that is real: the permission check, the tap flow, the server storing it,
the server encrypting + signing a test push to a local mock push service (decrypted here), the service worker showing
a pushed notification (CDP ServiceWorker.deliverPushMessage), and a notification's link opening the story in-app."""
import asyncio, base64, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.async_api import async_playwright
from PIL import Image
import http_ece
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

URL = os.environ.get("CHISME_URL", "http://localhost:8211") + "/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs(OUT, exist_ok=True)
ENV = os.environ.get("CHISME_ENV", "/workspace/secrets/chisme-local.env")
env = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l and not l.startswith("#"))
STORE = env.get("PUSH_STORE_FILE", "/tmp/chisme-push.json")
MOCK = int(os.environ.get("PUSH_MOCK_PORT", "8378"))
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); %s }"
TEXT = "The tea ain’t free! Help a chismoso out — donate now!"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok
b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def lum(rgb):
    def ch(c):
        c = c / 255; return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb; return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)
def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + 0.05) / (lb + 0.05)
rgb = lambda s: tuple(int(float(x)) for x in s[s.index("(") + 1:s.index(")")].split(",")[:3])

DONATE = """(id) => { const box = document.getElementById(id), a = box.querySelector('.donate-btn'), tag = box.querySelector('.donate-tag'), t = box.querySelector('.donate-text');
  const ra = a.getBoundingClientRect(), rt = tag.getBoundingClientRect(), cs = getComputedStyle(a), card = getComputedStyle(box.closest('.card, .settings-body, dialog') || box);
  return { text: t.textContent, btn: a.textContent.replace(a.querySelector('.sr-only')?.textContent || '', '').trim(), href: a.getAttribute('href'), target: a.target, rel: a.rel,
    tag: tag.textContent, below: rt.top >= ra.bottom - 1, h: Math.round(ra.height), bg: cs.backgroundColor, fg: cs.color,
    textColor: getComputedStyle(t).color, cardBg: getComputedStyle(box).backgroundColor, inList: !!box.closest('.news-list, .food-list, #food-creators'),
    last: box.parentElement.lastElementChild === box, parent: box.parentElement.id }; }"""

async def webkit_part(p):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    b = await p.webkit.launch()
    # ---- light
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "")
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)
    d = await pg.evaluate(DONATE, "donate-news")
    check(d["text"] == TEXT, f"News donate card, exact text: '{d['text']}'")
    check(d["btn"] == "💸 Donate on Cash App" and d["href"] == "https://cash.app/$Slurmkaos" and d["target"] == "_blank" and "noopener" in d["rel"], f"button '{d['btn']}' → {d['href']} (new tab, {d['rel']})")
    check(d["tag"] == "$Slurmkaos" and d["below"], "$Slurmkaos shows under the button")
    check(d["last"] and d["parent"] == "view-news" and not d["inList"], "it's the last thing in News, not between stories")
    check(d["bg"] == "rgb(0, 214, 50)" and contrast(rgb(d["bg"]), rgb(d["fg"])) >= 7 and d["h"] >= 48, f"Cash App green button, black text (contrast {contrast(rgb(d['bg']), rgb(d['fg'])):.1f}:1), {d['h']} px tall")
    between = await pg.evaluate("[...document.querySelectorAll('#near-list > *, #city-list > *, #sa-list > *')].some(n => n.querySelector && (n.matches('.donate') || n.querySelector('.donate')))")
    check(not between, "no donate card between stories")
    await pg.wait_for_timeout(3000)
    pop = await pg.evaluate("({ dialogs: [...document.querySelectorAll('dialog')].filter(d => d.open).map(d => d.id), ask: !document.querySelector('#push-ask').hidden })")
    check(not pop["dialogs"] and not pop["ask"], f"no popups on the first visit (open dialogs {pop['dialogs']}, alerts prompt shown: {pop['ask']})")
    await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(600)
    await pg.locator("#donate-news").scroll_into_view_if_needed(); await pg.evaluate("window.scrollBy(0, -120)"); await pg.wait_for_timeout(400)
    await pg.screenshot(path="/tmp/dn-light.png")
    # the one link that leaves the app
    await ctx.route("https://cash.app/**", lambda r: r.fulfill(status=200, content_type="text/html", body="<title>Cash App</title>cash app"))
    async with ctx.expect_page() as newp:
        await pg.tap("#donate-news .donate-btn")
    np_ = await newp.value
    check(np_.url == "https://cash.app/$Slurmkaos" and pg.url.startswith(URL), f"tapping it opens {np_.url} outside Chisme; Chisme stays put")
    await np_.close()
    # ¿Cuál dieta?
    await pg.evaluate("__chisme.goView('antojos', { instant: true })"); await pg.wait_for_timeout(800)
    d = await pg.evaluate(DONATE, "donate-dieta")
    check(d["text"] == TEXT and d["href"] == "https://cash.app/$Slurmkaos" and d["last"] and d["parent"] == "view-antojos" and d["tag"] == "$Slurmkaos", "¿Cuál dieta?: the same card, last thing on the tab")
    # Settings row
    await pg.evaluate("__chisme.goView('news', { instant: true })")
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    d = await pg.evaluate(DONATE, "set-donate")
    check(d["text"] == TEXT and d["btn"] == "💸 Donate on Cash App" and d["tag"] == "$Slurmkaos" and d["below"], "Settings: a 'Support Chisme' row with the same text, button and $Slurmkaos")
    st = await pg.evaluate("({ btn: document.querySelector('#set-push').disabled, status: document.querySelector('#set-push-status').textContent, pm: 'PushManager' in window })")
    if not st["pm"]:
        check(st["btn"] and "Add to Home Screen" in st["status"] and "16.4" in st["status"], f"iPhone in Safari (not the Home Screen app): alerts explain how: '{st['status'][:90]}…'")
    else:
        print("   note: this WebKit build exposes PushManager outside a Home Screen app; status:", st["status"][:80])
    await pg.locator("#set-donate").scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, "donate-settings.png"))
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close()
    # ---- dark
    ctx = await b.new_context(**dev, color_scheme="dark"); await ctx.add_init_script(INIT % "localStorage.setItem('chisme-theme','dark');")
    pg = await ctx.new_page()
    await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)
    d = await pg.evaluate(DONATE, "donate-news")
    theme = await pg.evaluate("document.documentElement.dataset.theme")
    c_txt = contrast(rgb(d["textColor"]), rgb(d["cardBg"]))
    check(theme == "dark" and lum(rgb(d["cardBg"])) < 0.05 and c_txt >= 7 and d["bg"] == "rgb(0, 214, 50)" and contrast(rgb(d["bg"]), rgb(d["fg"])) >= 7,
          f"dark mode: dark card, text {c_txt:.1f}:1, green button with black text")
    await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(500)
    await pg.locator("#donate-news").scroll_into_view_if_needed(); await pg.evaluate("window.scrollBy(0, -120)"); await pg.wait_for_timeout(400)
    await pg.screenshot(path="/tmp/dn-dark.png")
    await ctx.close()
    a, c = Image.open("/tmp/dn-light.png"), Image.open("/tmp/dn-dark.png")
    img = Image.new("RGB", (a.width + c.width + 36, max(a.height, c.height) + 24), (255, 244, 214)); img.paste(a, (12, 12)); img.paste(c, (a.width + 24, 12))
    img.save(os.path.join(OUT, "donate-news.png"))

    # ---- New chisme ↑ (the list doesn't jump; new stories wait behind the pill). Service workers off here so the
    # test can stand in for the news server (WebKit doesn't route a service worker's own requests).
    ctx = await b.new_context(**dev, service_workers="block"); await ctx.add_init_script(INIT % "")
    mode = {"add": 0}; calls = {"n": 0}
    async def news_route(route):
        calls["n"] += 1
        r = await route.fetch(); j = await r.json()
        for k in reversed(range(mode["add"])):   # #1 on top
            j["near"].insert(0, {**j["near"][0], "title": f"Breaking: new chisme #{k + 1} — crews respond on the Westside", "link": f"https://example.com/breaking/{k + 1}",
                                 "published": time.time() - 60 * k, "related": [], "summary": ""})
        await route.fulfill(response=r, json=j)
    await ctx.route("**/api/news?*", news_route)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story') && __chisme.fresh", timeout=120000)
    await pg.wait_for_timeout(1500)
    await pg.evaluate("window.scrollTo(0, 700)"); await pg.wait_for_timeout(300)
    first = lambda: pg.evaluate("document.querySelector('#near-list .story h3 a').textContent")
    f0, y0 = await first(), await pg.evaluate("scrollY")
    n0 = calls["n"]; await pg.evaluate("__chisme.checkNews()")
    await pg.wait_for_function(f"!__chisme.sync.busy.length", timeout=60000); await pg.wait_for_timeout(500)
    st = await pg.evaluate("__chisme.newsPill")
    check(calls["n"] > n0 and not st["shown"] and await first() == f0, "a check with nothing new: no pill, the list stays as it is")
    mode["add"] = 2
    await pg.evaluate("__chisme.checkNews()")
    await pg.wait_for_function("__chisme.newsPill.shown", timeout=60000)
    st = await pg.evaluate("({ pill: __chisme.newsPill, text: document.querySelector('#news-pill').textContent, vis: document.querySelector('#news-pill').getBoundingClientRect().top })")
    check(st["text"].startswith("New chisme ↑") and "2 new stories" in st["text"] and st["pill"]["n"] == 2 and 0 < st["vis"] < 240, f"2 new stories → the '{st['text'][:12]}' pill at the top ({st['text']}; top {st['vis']:.0f} px)")
    check(await first() == f0 and abs(await pg.evaluate("scrollY") - y0) < 2, "…and the list didn't jump (same first story, same scroll position)")
    ov = await pg.evaluate("""(() => { const a = document.querySelector('#news-pill').getBoundingClientRect(), s = document.querySelector('#sync');
      if (!s || s.hidden) return false; const b = s.getBoundingClientRect(); return b.height > 0 && a.top < b.bottom && b.top < a.bottom && a.left < b.right && b.left < a.right; })()""")
    check(not ov, "the pill doesn't cover the 'Updated' status pill")
    await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, "new-chisme-pill.png"))
    await pg.evaluate("__chisme.goView('weather', { instant: true })"); await pg.wait_for_timeout(300)
    hid = await pg.evaluate("document.querySelector('#news-pill').hidden")
    await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(300)
    back = await pg.evaluate("!document.querySelector('#news-pill').hidden")
    check(hid and back, "the pill only shows on the News tab (it waits while you're on Weather)")
    await pg.tap("#news-pill"); await pg.wait_for_timeout(1200)
    f1 = await first()
    st = await pg.evaluate("({ shown: __chisme.newsPill.shown, top: document.querySelector('#near').getBoundingClientRect().top, focus: document.activeElement && document.activeElement.textContent })")
    check(f1.startswith("Breaking: new chisme #1") and not st["shown"] and st["top"] < 250, f"tap it: the new stories show at the top and it scrolls there ('{f1[:40]}')")
    # a manual refresh shows new stories right away
    mode["add"] = 3
    await pg.evaluate("__chisme.refreshNow()"); await pg.wait_for_timeout(300)
    await pg.wait_for_function("[...document.querySelectorAll('#near-list .story h3 a')].slice(0, 3).some(a => a.textContent.includes('#3')) || __chisme.newsPill.shown", timeout=60000)
    check((await first()).startswith("Breaking: new chisme #1") and "#3" in await pg.evaluate("[...document.querySelectorAll('#near-list .story h3 a')].slice(0,3).map(a=>a.textContent).join('|')") and not (await pg.evaluate("__chisme.newsPill.shown")),
          "pull to refresh / Refresh now: new stories show right away, no pill")
    # the app polls every 4 min while it's on screen, and checks when you come back to it
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "app.js")).read()
    check("const NEWS_MS = 4 * 60 * 1000" in src and 'addEventListener("focus", newsOnReturn)' in src and "NEWS_FOCUS_MS = 60 * 1000" in src, "polls for news every 4 min while open, and on focus / coming back (if > 1 min)")
    n0 = calls["n"]
    await pg.evaluate("Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })")
    await pg.clock.install(); await pg.clock.fast_forward("01:10")
    await pg.evaluate("window.dispatchEvent(new Event('focus'))"); await pg.wait_for_timeout(1500)
    check(calls["n"] > n0, f"coming back after a minute+ checks for news right away ({calls['n'] - n0} request)")
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close(); await b.close()

# ---------------------------------------------------------------- alerts (Chromium)
phone = ec.generate_private_key(ec.SECP256R1()); auth = os.urandom(16)
P256 = b64e(phone.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)); AUTH = b64e(auth)
ENDPOINT = f"http://localhost:{MOCK}/push/ui-phone"
got = []
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        got.append(self.rfile.read(int(self.headers.get("Content-Length") or 0))); self.send_response(201); self.end_headers()
    def log_message(self, *a): pass
STUB = """(() => {   // headless browsers have no push service: a subscription whose keys the test owns
  const sub = { endpoint: %(ep)r, expirationTime: null, options: {}, toJSON() { return { endpoint: this.endpoint, expirationTime: null, keys: { p256dh: %(p)r, auth: %(a)r } }; },
    unsubscribe: async () => { window.__subbed = false; localStorage.removeItem('stub-subbed'); return true; } };
  PushManager.prototype.subscribe = async function (o) { window.__subOpts = { user: o.userVisibleOnly, keyLen: o.applicationServerKey && o.applicationServerKey.byteLength }; window.__subbed = true; localStorage.setItem('stub-subbed', '1'); return sub; };
  PushManager.prototype.getSubscription = async function () { return localStorage.getItem('stub-subbed') ? sub : null; };
})();""" % {"ep": ENDPOINT, "p": P256, "a": AUTH}

async def chromium_part(p):
    srv = ThreadingHTTPServer(("127.0.0.1", MOCK), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    if os.path.exists(STORE): os.remove(STORE)
    b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    await ctx.grant_permissions(["notifications"], origin=URL.rstrip("/"))
    await ctx.add_init_script(INIT % "")
    # 1. a real subscribe attempt (expected to fail headless: no push service) — just a note
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    real = await pg.evaluate("""(async () => { try { const r = await navigator.serviceWorker.ready; const c = await (await fetch('/api/push/config')).json();
        const s = await r.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(atob(c.publicKey.replace(/-/g,'+').replace(/_/g,'/') + '='), ch => ch.charCodeAt(0)) });
        const j = s.toJSON(); await s.unsubscribe(); return 'real subscription ok: ' + new URL(j.endpoint).host; } catch (e) { return 'real subscribe: ' + e.name + ': ' + e.message; } })()""")
    print("   note:", real[:140])
    ask1 = await pg.evaluate("!document.querySelector('#push-ask').hidden")
    await pg.close()
    await ctx.add_init_script(STUB)
    # 2. second visit: the one-time soft prompt (inline, not a popup)
    pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_function("!document.querySelector('#push-ask').hidden", timeout=15000)
    ask = await pg.evaluate("({ t: document.querySelector('#push-ask-t').textContent, yes: document.querySelector('#push-ask-yes').textContent, no: document.querySelector('#push-ask-no').textContent, dialogs: [...document.querySelectorAll('dialog')].filter(d => d.open).length })")
    check(not ask1 and ask["yes"] == "Turn on alerts 🔔" and ask["no"] == "Not now" and ask["dialogs"] == 0, f"soft prompt: not on the first visit, once on the second, inline ('{ask['t'][:50]}…', no dialog)")
    await pg.tap("#push-ask-no"); hidden = await pg.evaluate("document.querySelector('#push-ask').hidden")
    await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(2500)
    again = await pg.evaluate("!document.querySelector('#push-ask').hidden")
    check(hidden and not again, "'Not now' hides it, and it never comes back")
    # 3. Settings → Turn on alerts 🔔 (a tap)
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    before = await pg.evaluate("({ btn: document.querySelector('#set-push').textContent, dis: document.querySelector('#set-push-news').disabled })")
    await pg.locator("#set-push").scroll_into_view_if_needed(); await pg.tap("#set-push")
    await pg.wait_for_function("__chisme.pushPrefs.on && document.querySelector('#set-push-note').textContent.startsWith('Done')", timeout=20000)
    st = await pg.evaluate("({ btn: document.querySelector('#set-push').textContent, status: document.querySelector('#set-push-status').textContent, note: document.querySelector('#set-push-note').textContent, news: !document.querySelector('#set-push-news').disabled && document.querySelector('#set-push-news').checked, wx: !document.querySelector('#set-push-wx').disabled && document.querySelector('#set-push-wx').checked, test: !document.querySelector('#set-push-test').hidden, opts: window.__subOpts, loc: __chisme.loc })")
    recs = list(json.load(open(STORE)).values())
    check(before["btn"] == "Turn on alerts 🔔" and before["dis"] and st["btn"] == "Turn off alerts" and st["status"].startswith("Alerts are on for"), f"tap 'Turn on alerts 🔔' → '{st['note']}'")
    check(st["opts"] == {"user": True, "keyLen": 65}, f"subscribed with userVisibleOnly + Chisme's 65-byte VAPID key ({st['opts']})")
    check(st["news"] and st["wx"] and st["test"], "toggles on: Breaking & new local news, NWS warnings & watches; 'Send a test' appears")
    check(len(recs) == 1 and recs[0]["sub"]["endpoint"] == ENDPOINT and recs[0]["lat"] == round(st["loc"]["lat"], 2) and recs[0]["news"] and recs[0]["weather"],
          f"the server stored it with the area rounded ({recs[0]['lat'] if recs else '?'}, {recs[0]['lon'] if recs else '?'}) and both kinds on")
    await pg.evaluate("""(() => { const g = document.querySelector('#set-alerts'); g.scrollIntoView({ block: 'start' });
      let sc = g.parentElement; while (sc && sc.scrollHeight <= sc.clientHeight + 1) sc = sc.parentElement;
      if (sc) sc.scrollTop -= 96; })()"""); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, "alerts-settings.png"))
    # 4. Send a test → the server encrypts + signs → our mock push service → decrypted with the phone's key
    n0 = len(got); await pg.tap("#set-push-test")
    await pg.wait_for_function("document.querySelector('#set-push-note').textContent.startsWith('Test sent')", timeout=20000); await asyncio.sleep(0.3)
    msg = json.loads(http_ece.decrypt(got[-1], private_key=phone, auth_secret=auth, version="aes128gcm")) if len(got) > n0 else {}
    check(msg.get("title") == "Chisme alerts are on 🔔", f"Send a test: the phone gets '{msg.get('title')}'")
    # 5. toggle news off → the server follows
    await pg.tap("label:has(#set-push-news)"); await pg.wait_for_timeout(1200)
    recs = list(json.load(open(STORE)).values())
    check(recs and recs[0]["news"] is False and recs[0]["weather"] is True, "switching off news alerts updates the server (weather stays on)")
    await pg.tap("label:has(#set-push-news)"); await pg.wait_for_timeout(800)
    await pg.tap("#settings-close"); await pg.wait_for_timeout(300)
    # 6. the service worker shows a pushed notification
    cdp = await ctx.new_cdp_session(pg); regs = []
    cdp.on("ServiceWorker.workerRegistrationUpdated", lambda e: regs.extend(e["registrations"]))
    await cdp.send("ServiceWorker.enable"); await asyncio.sleep(1)
    reg = next((r for r in regs if r["scopeURL"].startswith(URL)), None)
    data = {"title": "New chisme, grab the tea! ☕", "body": "Test headline — KSAT", "url": "/?story=https%3A%2F%2Fexample.com%2Fs1&t=Test+headline&s=KSAT#news", "tag": "chisme-news"}
    if reg:
        await cdp.send("ServiceWorker.deliverPushMessage", {"origin": URL.rstrip("/"), "registrationId": reg["registrationId"], "data": json.dumps(data)})
        await pg.wait_for_timeout(1500)
        notes = await pg.evaluate("(async () => (await (await navigator.serviceWorker.ready).getNotifications()).map(n => ({ t: n.title, b: n.body, u: n.data && n.data.url, tag: n.tag })))()")
        check(any(n["t"] == data["title"] and n["b"] == data["body"] and n["u"] == data["url"] for n in notes), f"service worker: a push shows '{notes[0]['t'] if notes else '—'}' with the headline")
    else:
        check(False, "service worker registration found for CDP push delivery")
    # 7. tapping it: the SW posts the link to the open app → the story opens in the in-app reader
    await pg.evaluate("navigator.serviceWorker.dispatchEvent(new MessageEvent('message', { data: { chismeOpen: %r } }))" % data["url"])
    await pg.wait_for_function("document.querySelector('#player').open", timeout=5000)
    r = await pg.evaluate("({ t: document.querySelector('#player-title').textContent, kind: document.querySelector('#player-kind').textContent, open: document.querySelector('#player-orig .orig-link')?.href, view: __chisme.view })")
    check(r["t"] == "Test headline" and r["view"] == "news" and r["open"] == "https://example.com/s1", f"notification tap (app open): '{r['t']}' opens in Chisme's reader on News")
    await pg.keyboard.press("Escape")
    # ...and with the app closed: the link it opens
    await pg.goto(URL + data["url"][1:]); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.wait_for_function("document.querySelector('#player').open", timeout=8000)
    r = await pg.evaluate("({ t: document.querySelector('#player-title').textContent, url: location.search })")
    check(r["t"] == "Test headline" and r["url"] == "", "notification tap (app closed): Chisme opens on the story, and the address is cleaned up")
    await pg.keyboard.press("Escape")
    # 8. turn off → deleted from the server
    await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open")
    await pg.locator("#set-push").scroll_into_view_if_needed(); await pg.tap("#set-push")
    await pg.wait_for_function("!__chisme.pushPrefs.on", timeout=10000); await pg.wait_for_timeout(500)
    check(json.load(open(STORE)) == {} and (await pg.evaluate("document.querySelector('#set-push').textContent")) == "Turn on alerts 🔔", "Turn off alerts: gone from the server")
    check(not errs, f"no page errors ({errs[:2]})")
    await b.close(); srv.shutdown()

async def main():
    async with async_playwright() as p:
        await webkit_part(p)
        await chromium_part(p)
    print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
