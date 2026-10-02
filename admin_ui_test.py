"""v49.5: the owner's admin page (/stats) on an iPhone-size screen (WebKit, iPhone 13 = 390 px), end to end:
  • sign-in form: wrong key → a friendly error (401); right key + "Keep me signed in" → a 400-day HttpOnly session
    cookie (not the token) and the app's harmless chisme_admin=1 marker; sign out clears both
  • layout: one column, no sideways scroll at 390 and 320 px, a sticky header, every button/field ≥ 44 px tall
  • the send card first: subscriber count, quick templates fill title + message + where it opens, the live lock-screen
    preview follows the typing, a story link is required for "A story or web page", the confirm sheet shows the
    preview, then a toast with plain words (sent / didn't go through / cleaned up), never raw JSON
  • auto-alerts: the switch saves (toast) and the status line reads "On · 0 of 2 sent today · quiet hours …";
    Run a check now answers in a sentence
  • stats as cards (Today, This week, Subscribers, Installed app) + the week's top stories; everything else folded
  • the app: Settings → Owner only on a signed-in phone; holding the Chisme bubble ~1.5 s opens /stats
  • no yellow on the sign-in page or the admin page; /stats/manifest.webmanifest for a "Chisme Admin" Home Screen icon
Screenshots → /workspace/chisme-admin-shots/.
Run (server with PUSH_TEST=1 so http://localhost push endpoints are allowed):
    CHISME_ENV=/path/local.env CHISME_URL=http://localhost:8275 ./venv/bin/python admin_ui_test.py"""
import asyncio, base64, json, os, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from playwright.async_api import async_playwright

BASE = os.environ.get("CHISME_URL", "http://localhost:8275")
env = dict(os.environ)
if os.environ.get("CHISME_ENV"):
    for line in open(os.environ["CHISME_ENV"]):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1); env[k] = v.strip().strip('"\'')
TOKEN = env["ADMIN_TOKEN"]
SHOTS = os.environ.get("ADMIN_SHOTS", "/workspace/chisme-admin-shots"); os.makedirs(SHOTS, exist_ok=True)
MOCK = int(os.environ.get("ADMIN_MOCK_PORT", "8479"))
fails = 0


def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok


b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
got = []


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0)); name = self.path.rsplit("/", 1)[-1]; got.append(name)
        self.send_response(410 if name.startswith("gone") else 201); self.end_headers()
    def log_message(self, *a): pass


srv = ThreadingHTTPServer(("127.0.0.1", MOCK), H); threading.Thread(target=srv.serve_forever, daemon=True).start()


def phone(name):
    k = ec.generate_private_key(ec.SECP256R1())
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"endpoint": f"http://localhost:{MOCK}/push/{name}", "keys": {"p256dh": b64e(pub), "auth": b64e(os.urandom(16))}}


YELLOW = r"""() => { const yellow = ([r, g, b, a]) => { if (a != null && a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.05) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= 0.85 || l <= 0.2)); };
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const bad = [];
  for (const e of document.querySelectorAll('body, body *')) { if (!e.getClientRects().length || e.tagName === 'IMG') continue; const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor, cs.borderLeftColor, cs.borderBottomColor, cs.outlineColor, cs.fill])
      if (rgb(v).some(yellow)) bad.push((e.id || e.className || e.tagName) + ' ' + String(v).slice(0, 50)); }
  return [...new Set(bad)].slice(0, 6); }"""
SMALL = r"""() => [...document.querySelectorAll('header button, header a, main button, main summary, main input, main select, main textarea, main .sw, .sheet button')]
  .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && !(e.type === 'checkbox' && e.closest('label')) && e.type !== 'hidden')
  .map(e => [e.id || e.className || e.tagName, Math.round(e.getBoundingClientRect().height), Math.round(e.getBoundingClientRect().width)]).filter(x => x[1] < 44 || x[2] < 44)"""
NO_SIDEWAYS = "document.documentElement.scrollWidth <= innerWidth + 1"


async def main():
    # fresh push state: no subscribers, auto-alerts off
    for f in (env["PUSH_STORE_FILE"], env["PUSH_STORE_FILE"].rsplit(".", 1)[0] + ".state.json"):
        if os.path.exists(f): os.remove(f)
    for n in ("phoneA", "gone1"):
        r = httpx.post(BASE + "/api/push/subscribe", json={"subscription": phone(n), "lat": 29.42, "lon": -98.49, "tz": "America/Chicago", "news": True, "weather": True})
        check(r.status_code == 200 and r.json().get("ok"), f"a test phone subscribes ({n})")
    m = httpx.get(BASE + "/stats/manifest.webmanifest")
    mj = m.json()
    check(m.headers["content-type"].startswith("application/manifest+json") and mj["start_url"] == "/stats" and mj["name"] == "Chisme Admin" and mj["display"] == "standalone",
          "/stats/manifest.webmanifest: a 'Chisme Admin' Home Screen app that opens /stats")
    check(httpx.post(BASE + "/stats/login", data={"key": TOKEN}, headers={"Origin": "https://evil.example"}).status_code == 403, "sign-in from another site's page: refused (403)")

    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev); pg = await ctx.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        # ---- sign in
        r = await pg.goto(BASE + "/stats")
        check(r.status == 401 and await pg.is_visible("#key") and "Private page" in await pg.content(), "/stats signed out: the sign-in form (401, 'Private page')")
        check(await pg.evaluate("document.querySelector('#key').type") == "password" and await pg.evaluate("document.querySelector('[name=remember]').checked"),
              "the key field is a password field; 'Keep me signed in' is on by default")
        await pg.screenshot(path=os.path.join(SHOTS, "0-sign-in.png"))
        await pg.fill("#key", "nope-wrong"); await pg.click("#login-go"); await pg.wait_for_load_state()
        check("didn't match" in await pg.inner_text("main") and not [c for c in await ctx.cookies() if c["name"] == "chisme_stats"], "a wrong key: 'That key didn't match', no cookie")
        await pg.tap("#show"); check(await pg.evaluate("document.querySelector('#key').type") == "text", "Show reveals what was typed")
        check(not await pg.evaluate(YELLOW) and await pg.evaluate(NO_SIDEWAYS), "sign-in page: no yellow, no sideways scroll")
        await pg.fill("#key", TOKEN); await pg.click("#login-go"); await pg.wait_for_selector("#push-h")
        ck = {c["name"]: c for c in await ctx.cookies()}
        sess, mark = ck.get("chisme_stats"), ck.get("chisme_admin")
        import time as _t
        check(bool(sess) and sess["httpOnly"] and sess["value"] != TOKEN and sess["path"] == "/stats" and sess["expires"] > _t.time() + 360 * 86400,
              f"signed in: HttpOnly session cookie (path /stats, not the token) kept a year or more (400 days asked; the browser may cap it) ({round((sess['expires'] - _t.time()) / 86400) if sess else '-'} d)")
        check(bool(mark) and mark["value"] == "1" and mark["path"] == "/" and not mark["httpOnly"], "…plus the chisme_admin=1 marker the app can see (nothing secret)")
        check(pg.url.rstrip("/").endswith("/stats") and "key" not in pg.url, f"back on /stats, no key in the address ({pg.url})")
        # reset the switch to off through the page's own API
        await pg.evaluate("fetch('/stats/push/auto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:false})})"); await pg.reload()
        # ---- layout
        check(await pg.evaluate(NO_SIDEWAYS), "390 px: no sideways scroll")
        small = await pg.evaluate(SMALL); check(not small, f"every button, field and fold is at least 44×44 px {small[:4]}")
        order = await pg.evaluate("[...document.querySelectorAll('main > section, main > h2')].map(e => e.id || e.textContent.trim().slice(0, 14))")
        check(order[:2] == ["send", "auto"] and "📊 At a glance" in order, f"most-used first: Send, then Auto-alerts, then the stats ({order[:4]})")
        cnt = await pg.inner_text("#push-count"); check(cnt.startswith("2 phones will get it"), f"subscriber count: '{cnt.splitlines()[0]}'")
        check(await pg.inner_text("#pf-send") == "Send to 2 phones…", "the send button says how many phones")
        st = await pg.inner_text("#auto-status-t"); check(st == "Off · nothing is sent automatically", f"auto-alerts status in plain English: '{st}'")
        gl = await pg.evaluate("[...document.querySelectorAll('.gl')].map(g => g.querySelector('.l').textContent + '=' + g.querySelector('.n').textContent)")
        check([x.split("=")[0] for x in gl] == ["Today", "This week", "Subscribers", "Installed app"] and "Subscribers=2" in gl, f"stat cards: {gl}")
        folds = await pg.evaluate("[...document.querySelectorAll('details.fold')].map(d => [d.querySelector('summary span').textContent, d.open])")
        check(len(folds) >= 8 and not any(o for _, o in folds), f"the rest is folded away ({len(folds)} sections, all closed)")
        check(not await pg.evaluate(YELLOW), "admin page: no yellow")
        # (v49.5: the one exception is the owner-requested "🏆 Juan High Scores" section title)
        emo = await pg.evaluate("[...document.body.innerText.replace('🏆 Juan High Scores', 'Juan High Scores').matchAll(/[\\u26A1\\u26A0\\u{1F525}\\u{1F514}\\u{1F512}-\\u{1F513}\\u{1F510}\\u{1F496}\\u{1F5C2}\\u{1F3C6}]/gu)].map(m => m[0])")
        check(not emo, f"no yellow emoji in the page's own copy (⚡ ⚠ 🔥 🔔 🔐 💖 🗂 🏆; 🏆 only in the requested 'Juan High Scores' title) {emo}")
        await pg.screenshot(path=os.path.join(SHOTS, "1-top.png"))
        await pg.evaluate("scrollTo(0, 1400)"); await pg.wait_for_timeout(200)
        check(await pg.evaluate("Math.round(document.querySelector('header.top').getBoundingClientRect().top)") == 0, "the header stays on top while scrolling (sticky)")
        # ---- templates + live preview
        await pg.evaluate("scrollTo(0, 0)")
        await pg.tap("[data-tpl=weather]")
        v = await pg.evaluate("({t: pf_title.value, m: document.querySelector('#pf-msg').value, w: document.querySelector('#pf-where').value, pt: document.querySelector('#pv-t').textContent, pm: document.querySelector('#pv-m').textContent, pl: document.querySelector('#pv-l').textContent, pressed: document.querySelector('[data-tpl=weather]').getAttribute('aria-pressed')})".replace("pf_title", "document.querySelector('#pf-title')"))
        check(v["t"] == "Weather alert" and v["w"] == "weather" and v["pt"] == v["t"] and v["pm"] == v["m"] and "Weather" in v["pl"] and v["pressed"] == "true",
              f"'Weather alert' template: title, message and 'opens Weather' filled in; the preview matches ({v['pl']})")
        await pg.fill("#pf-msg", "Tornado warning for Bexar County until 9 PM. Take shelter now.")
        check(await pg.inner_text("#pv-m") == "Tornado warning for Bexar County until 9 PM. Take shelter now." and await pg.inner_text("#pf-mc") == "62 / 240",
              "the preview follows the typing, with a character count")
        await pg.evaluate("document.querySelector('#pv').scrollIntoView({block: 'center'})"); await pg.wait_for_timeout(200)
        await pg.evaluate("document.querySelector('.tpl').scrollIntoView({block: 'start'}); scrollBy(0, -70)"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(SHOTS, "2-send-preview-weather-template.png"))
        await pg.tap("[data-tpl=breaking]")
        check(await pg.is_visible("#pf-link") and await pg.evaluate("document.querySelector('#pf-where').value") == "link", "'Breaking news' template: asks for the story link")
        await pg.tap("#pf-send"); await pg.wait_for_timeout(300)
        check(await pg.is_visible("#pf-err") and "link" in await pg.inner_text("#pf-err") and not await pg.evaluate("document.querySelector('#pf-confirm').open"),
              f"no link yet: a clear message, no confirm ('{await pg.inner_text('#pf-err')}')")
        await pg.fill("#pf-link", "ksat.com/news"); await pg.tap("#pf-send"); await pg.wait_for_timeout(200)
        check("https://" in await pg.inner_text("#pf-err"), "a link without https://: explained")
        await pg.fill("#pf-link", "https://www.ksat.com/news/local/2026/10/02/test-story/")
        check("ksat.com" in await pg.inner_text("#pv-l"), f"preview: where the tap goes ({await pg.inner_text('#pv-l')})")
        await pg.tap("#pf-send"); await pg.wait_for_function("document.querySelector('#pf-confirm').open", timeout=5000)
        cf = await pg.evaluate("({h: document.querySelector('#pf-confirm-h').textContent, t: document.querySelector('#pf-pt').textContent, m: document.querySelector('#pf-pm').textContent})")
        check(cf["h"] == "Send this to 2 phones?" and cf["t"] == "Breaking news" and cf["m"].startswith("Big news in San Antonio"), f"confirm sheet first, with the preview ('{cf['h']}')")
        await pg.wait_for_timeout(300); await pg.screenshot(path=os.path.join(SHOTS, "3-confirm-dialog.png"))
        small = await pg.evaluate(SMALL); check(not small, f"confirm buttons are big enough {small[:3]}")
        await pg.tap("#pf-no"); check(not await pg.evaluate("document.querySelector('#pf-confirm').open") and not got, "Cancel: nothing sent")
        # ---- a real send (mock push service: one phone fine, one gone)
        await pg.tap("[data-tpl=news]"); await pg.tap("#pf-send"); await pg.wait_for_function("document.querySelector('#pf-confirm').open")
        await pg.tap("#pf-yes")
        await pg.wait_for_function("/^(Sent|Not sent|Nobody)/.test(document.querySelector('#pf-res').textContent)", timeout=30000)
        t = await pg.text_content("#toast"); res = await pg.inner_text("#pf-res")
        check(res == "Sent to 1 phone · 1 didn't go through · 1 old subscription cleaned up" and t.startswith("✅") and "{" not in t,
              f"after sending: a toast in plain words ('{t}')")
        check(sorted(got) == ["gone1", "phoneA"], f"the mock push service got both pushes ({got})")
        await pg.wait_for_function("document.querySelector('#pf-send').textContent === 'Send to 1 phone…'", timeout=5000)
        check(await pg.inner_text("#push-count b") == "1" and await pg.inner_text("#gl-subs") == "1", "counts refresh by themselves (the dead subscription is gone)")
        # ---- auto-alerts switch + check
        await pg.tap("label.sw"); await pg.wait_for_function("document.querySelector('#auto-status-t').textContent.startsWith('On')", timeout=10000)
        st = await pg.inner_text("#auto-status-t"); t = await pg.text_content("#toast")
        check(re.match(r"^On · 0 of 2 sent today · (quiet hours 10pm–7am|quiet hours now, back at 7am)$", st) and "on" in t, f"switch on: toast '{t}', status '{st}'")
        await pg.tap("#auto-check"); await pg.wait_for_function("!/^Checking/.test(document.querySelector('#auto-res').textContent) && document.querySelector('#auto-res').textContent", timeout=90000)
        ar = await pg.inner_text("#auto-res")
        check(ar and "{" not in ar and not ar.startswith(("nothing major", "quiet hours (", "error:")) and ar[0].isupper(), f"Run a check now: one plain sentence ('{ar}')")
        check(await pg.inner_text("#auto-last") != "No check yet.", f"last check line updated ('{await pg.inner_text('#auto-last')}')")
        await pg.evaluate("scrollTo(0, 0)"); await pg.wait_for_timeout(4800)
        await pg.evaluate("document.querySelector('#auto').scrollIntoView({block: 'start'}); scrollBy(0, -64)"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(SHOTS, "4-auto-alerts.png"))
        await pg.tap("label.sw"); await pg.wait_for_function("document.querySelector('#auto-status-t').textContent.startsWith('Off')", timeout=10000)
        await pg.wait_for_function("!document.querySelector('#toast').classList.contains('show')", timeout=10000); await pg.wait_for_timeout(300)
        # ---- folded sections
        await pg.evaluate("document.querySelector('h2.sec:last-of-type').scrollIntoView({block: 'start'}); scrollBy(0, -64)"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(SHOTS, "5-collapsed-sections.png"))
        await pg.tap("#f-sent summary"); await pg.wait_for_timeout(200)
        sent_log = await pg.inner_text("#f-sent .fold-b")
        check("¡Órale, new chisme! 👀" in sent_log and "Sent to 1 phone" in sent_log, f"open 'Notifications you sent': your send is listed in plain words")
        await pg.tap("#f-all summary"); await pg.tap("#t7"); await pg.wait_for_timeout(150)
        vis = await pg.evaluate("[...document.querySelectorAll('[role=tabpanel]')].filter(x => x.offsetHeight > 0).map(x => x.id)")
        check(vis == ["p7"], f"'All the numbers': Today / 7 days / 30 days ({vis})")
        await pg.screenshot(path=os.path.join(SHOTS, "6-full-page.png"), full_page=True)
        await pg.set_viewport_size({"width": 320, "height": 640}); await pg.wait_for_timeout(200)
        check(await pg.evaluate(NO_SIDEWAYS), "320 px: still no sideways scroll")
        await pg.set_viewport_size({"width": 390, "height": 844})
        # ---- the app: Settings → Owner, and the long-press
        app = await ctx.new_page(); app.on("pageerror", lambda e: errs.append("app: " + str(e)[:160]))
        await app.goto(BASE + "/"); await app.wait_for_function("() => window.__chisme", timeout=60000)
        await app.evaluate("localStorage.setItem('chisme-loc', localStorage.getItem('chisme-loc') || '')")
        await app.wait_for_timeout(800)
        await app.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
        await app.tap("#settings-btn"); await app.wait_for_timeout(400)
        check(await app.is_visible("#set-admin"), "the app, signed-in phone: Settings shows 'Owner → Open the Admin page'")
        await app.evaluate("document.querySelector('#set-admin').scrollIntoView({block: 'center'})"); await app.wait_for_timeout(300)
        await app.screenshot(path=os.path.join(SHOTS, "7-app-settings-owner-button.png"))
        await app.tap("#set-admin-open"); await app.wait_for_url("**/stats", timeout=10000)
        check("Chisme Admin" in await app.title(), "…which opens the admin page")
        await app.goto(BASE + "/"); await app.wait_for_function("() => window.__chisme", timeout=60000); await app.wait_for_timeout(600)
        await app.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
        bx = await app.locator("#settings-btn").bounding_box()
        await app.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2); await app.mouse.down()
        try:
            await app.wait_for_url("**/stats", timeout=4000); lp = True
        except Exception:
            lp = False
        await app.mouse.up()
        check(lp, "holding the Chisme bubble ~1.5 s opens /stats (the hidden way in)")
        # ---- sign out
        await pg.bring_to_front(); await pg.evaluate("scrollTo(0, 0)"); await pg.tap("#logout"); await pg.wait_for_selector("#key")
        names = [c["name"] for c in await ctx.cookies()]
        check("chisme_stats" not in names and "chisme_admin" not in names, f"Sign out: back to the sign-in form, both cookies gone ({names})")
        check(httpx.post(BASE + "/stats/push/send", json={"message": "x"}).status_code == 401, "the send endpoint still needs the session (401 without it)")
        await app.goto(BASE + "/"); await app.wait_for_function("() => window.__chisme", timeout=60000); await app.wait_for_timeout(600)
        await app.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
        await app.tap("#settings-btn"); await app.wait_for_timeout(300)
        check(not await app.is_visible("#set-admin"), "signed out: no Owner section in Settings")
        e2 = [x for x in errs if "ResizeObserver" not in x]
        check(not e2, f"no page errors {e2[:3]}")
        await b.close()
    print("ALL PASS" if not fails else f"{fails} FAIL(S)"); sys.exit(1 if fails else 0)


asyncio.run(main())
