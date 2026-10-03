"""v49.12 Día de Muertos season theme (index.html season script + style.css html[data-season="muertos"] + the gallery).
Chromium Pixel 7 + WebKit iPhone 13, dark + light, 320 px. Screenshots → $SHOTS (default /workspace/muertos-v49.12).
  • on by itself Oct 3 00:00 → Nov 3 23:59:59 Chicago time (page.clock), off before and after, nothing left behind
  • the owner's override: /api/theme {override: off} turns it off on an open page; {override: muertos} forces it on out of
    season; THEME_OVERRIDE=off on a real server (a second one started here) sends 'off' with the page and from /api/theme
  • in season: the food tab reads "Ofrendas" (and "¿Y la dieta?" again after), the Chisme tab and its chips are unchanged,
    the papel picado, the greeting banner (✕ remembered), Tía's marigolds
  • readable: WCAG contrast ≥ 4.5 for the banner, tabs, chips, card text, tags and credits, dark and light
  • the gallery: 15–25 photos, every one with "Photo: name / license / Wikimedia Commons (resized)", the license and Commons
    page linked, only PD / CC0 / CC BY / CC BY-SA (no NC/ND), every file there; the viewer opens, steps, closes
  • no page errors"""
import asyncio, json, os, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211/")
SHOTS = os.environ.get("SHOTS", "/workspace/muertos-v49.12")
os.makedirs(SHOTS, exist_ok=True)
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
UNPIN = "try { localStorage.removeItem('chisme-season-pin'); localStorage.setItem('chisme-location-setup', '1'); localStorage.setItem('chisme-default-tab', 'chisme'); } catch (e) {}"
def utc(*a): return datetime(*a, tzinfo=timezone.utc)
async def ready(pg, url=URL):
    await pg.goto(url); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(500)
SEASON = "() => [document.documentElement.dataset.season || '', document.querySelector('#tabs .tab[data-view=antojos]').textContent.trim()]"
CONTRAST = """(sel) => { const L = (c) => { const m = c.match(/[\\d.]+/g).map(Number); const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
    return [.2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]), m[3] == null ? 1 : m[3]]; };
  const bgOf = (n) => { for (; n; n = n.parentElement) { const b = getComputedStyle(n).backgroundColor, al = b.match(/rgba\\([^)]*,\\s*([\\d.]+)\\)/) || b.match(/\\/\\s*([\\d.]+)\\s*\\)/);
      if (!/transparent/.test(b) && !(al && +al[1] < .5)) return /^color\\(srgb/.test(b) ? 'rgb(' + b.match(/[\\d.]+/g).slice(0, 3).map(v => Math.round(v * 255)).join(',') + ')' : b; } return 'rgb(255,255,255)'; };   // (a faint tint, e.g. 10% orange, counts as the page under it; color-mix() comes back as color(srgb r g b / a), 0–1)
  return [...document.querySelectorAll(sel)].filter(n => n.offsetParent && n.textContent.trim()).slice(0, 6).map(n => {
    const [a] = L(getComputedStyle(n).color), [b] = L(bgOf(n)); return Math.round(((Math.max(a, b) + .05) / (Math.min(a, b) + .05)) * 100) / 100; }); }"""
READ = [("#muertos-banner .mb-t", "banner"), ("#tabs .tab", "tabs"), ("#tabs .tab[aria-current=page]", "open tab"), (".view.active .mq-chip", "chips"),
        (".view.active .mq-chip[aria-current=true]", "picked chip"), ("#mix-list .story h3 a", "story titles"), ("#mix-list .meta", "story meta"), ("#mix-list .sum", "summaries"),
        ("#mix-list .mix-tag", "tags"), (".mix-hi", "intro"), ("#mq-gallery .mq-gal-cap", "photo captions"), ("#mq-gallery .mq-credit", "credits"),
        ("#mq-gallery .mq-credit a", "credit links"), ("#mb-photos", "See the photos")]

async def clock_checks(b, dev):
    print("— dates (page.clock, Chicago time)")
    for when, want, label in ((utc(2026, 10, 3, 4, 59), "", "Oct 2 11:59 PM CT: not yet"), (utc(2026, 10, 3, 5, 0, 30), "muertos", "Oct 3 12:00 AM CT: on"),
                              (utc(2026, 11, 2, 18), "muertos", "Nov 2: on"), (utc(2026, 11, 4, 5, 59), "muertos", "Nov 3 11:59 PM CT: still on"),
                              (utc(2026, 11, 4, 6, 0, 30), "", "Nov 4 12:00 AM CT: off by itself"), (utc(2027, 10, 20), "", "Oct 2027: off (2026 only)")):
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(UNPIN)
        pg = await ctx.new_page(); await pg.clock.install(time=when); await ready(pg)
        s = await pg.evaluate(SEASON)
        check(s[0] == want and s[1].endswith("Ofrendas" if want else "¿Y la dieta?"), f"{label} ({s})")
        if label.startswith("Nov 4"):
            vis = await pg.evaluate("[...document.querySelectorAll('.muertos-only')].filter(n => n.offsetParent).length")
            tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t => t.textContent.trim())")
            check(vis == 0 and "Chisme" in tabs[0] and len(tabs) == 4, f"…after: no banner / gallery / papel picado / marigolds left, the Chisme tab stays ({vis} shown, {tabs})")
            await pg.screenshot(path=f"{SHOTS}/after-nov3-home.png")
        await ctx.close()
    print("— a page left open across the end")
    ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(UNPIN)
    pg = await ctx.new_page(); await pg.clock.install(time=utc(2026, 11, 4, 5, 58)); await ready(pg)
    a = await pg.evaluate(SEASON); await pg.clock.fast_forward("06:00"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(2500)
    await pg.clock.fast_forward("05:00"); await pg.wait_for_timeout(500)
    z = await pg.evaluate(SEASON)
    check(a[0] == "muertos" and z[0] == "", f"open at 11:58 PM Nov 3, still open after midnight: the theme goes away by itself ({a} → {z})")
    await ctx.close()

async def override_checks(b, dev):
    print("— the owner's override (/api/theme)")
    for mode, when, want in (("off", utc(2026, 10, 20), ""), ("muertos", utc(2026, 12, 20), "muertos"), ("auto", utc(2026, 10, 20), "muertos")):
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(UNPIN)
        body = json.dumps({"override": mode, "at": int(time.time() * 1000) + 60000})
        await ctx.route("**/api/theme", (lambda b_: (lambda r: r.fulfill(status=200, content_type="application/json", body=b_)))(body))
        pg = await ctx.new_page(); await pg.clock.install(time=when); await ready(pg)
        await pg.wait_for_timeout(2500)   # app.js asks /api/theme 1.5 s in
        s = await pg.evaluate(SEASON)
        check(s[0] == want, f"override {mode} on {when:%b %d}: {'on' if want else 'off'} ({s})")
        await ctx.close()
    print("— THEME_OVERRIDE=off on a real server")
    port = 8293
    env = dict(os.environ, THEME_OVERRIDE="off")
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv/bin/uvicorn"), "app:app", "--host", "127.0.0.1", "--port", str(port)],
                           cwd=os.path.dirname(os.path.abspath(__file__)), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try: urllib.request.urlopen(f"http://127.0.0.1:{port}/api/theme", timeout=2); break
            except Exception: time.sleep(0.5)
        t = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/theme"))
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
        check(t.get("override") == "off" and 'v: "off"' in page and "__THEME_OVERRIDE__" not in page, f"/api/theme says off and the page carries it ({t})")
        ctx = await b.new_context(**dev); await ctx.add_init_script(QUIET); await ctx.add_init_script(UNPIN)
        pg = await ctx.new_page(); await pg.clock.install(time=utc(2026, 10, 20)); await ready(pg, f"http://127.0.0.1:{port}/")
        s = await pg.evaluate(SEASON)
        check(s[0] == "", f"…so Oct 20 shows no theme on that server ({s})")
        await ctx.close()
    finally:
        srv.terminate(); srv.wait(10)

async def phone(b, name, dev, theme, tag, w=None, tabs=False):
    print(f"— {name}")
    opts = dict(dev)
    if w: opts["viewport"] = {"width": w, "height": 740}
    ctx = await b.new_context(**opts); await ctx.add_init_script(QUIET); await ctx.add_init_script(UNPIN + f"localStorage.setItem('chisme-theme', '{theme}');")
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: None if "access control checks" in str(e) else errs.append(str(e)[:160]))   # WebKit: a fetch cut off by the test navigating away
    await pg.clock.install(time=utc(2026, 10, 25, 17)); await ready(pg)
    await pg.wait_for_function("document.querySelectorAll('#mix-list .mix-item').length >= 6 && document.querySelectorAll('#mq-gal-strip .mq-gal-item').length >= 15", timeout=60000)
    await pg.wait_for_timeout(1500)
    s = await pg.evaluate(SEASON)
    labels = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t => t.textContent.trim())")
    check(s[0] == "muertos" and labels[0].endswith("Chisme") and labels[2].endswith("Ofrendas") and len(labels) == 4, f"themed: tabs {labels}")
    shown = await pg.evaluate("Object.fromEntries(['.mq-picado', '#muertos-banner', '#mq-gallery', '.tia-flores'].map(s => [s, !!document.querySelector(s).offsetParent || getComputedStyle(document.querySelector(s)).display !== 'none']))")
    check(all(shown.values()), f"papel picado, greeting, gallery, Tía's marigolds on show ({shown})")
    await pg.screenshot(path=f"{SHOTS}/{tag}-home.png")
    low = []
    for sel, what in READ:
        cs = await pg.evaluate(CONTRAST, sel)
        if cs and min(cs) < 4.5: low.append((what, min(cs)))
    check(not low, f"contrast ≥ 4.5 everywhere checked ({low})")
    over = await pg.evaluate("(() => [...document.querySelectorAll('#muertos-banner *, #tabs .tab, .view.active .mq-chip')].filter(n => n.offsetParent && n.getBoundingClientRect().right > innerWidth + 1).length)()")
    check(over == 0, f"nothing runs off the right edge ({over})")
    await pg.click("#mb-photos"); await pg.wait_for_timeout(1500)
    sp = await pg.evaluate("[window.__chisme.view, Math.round(document.querySelector('#mq-gallery').getBoundingClientRect().top)]")
    check(sp[0] == "chisme" and -40 < sp[1] < 400, f"greeting 'See the photos' scrolls to the gallery on Chisme: All ({sp})")
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
    # gallery
    g = await pg.evaluate("""[...document.querySelectorAll('#mq-gal-strip .mq-gal-item')].map(f => { const c = f.querySelector('.mq-credit'), a = [...c.querySelectorAll('a')];
      return { text: c.textContent.trim(), links: a.map(x => x.href), img: f.querySelector('img').getAttribute('src') }; })""")
    ok_lic = ("Public domain", "CC0", "CC BY 2.0", "CC BY 3.0", "CC BY 4.0", "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0")
    bad = [x["text"] for x in g if not (x["text"].startswith("Photo: ") and x["text"].endswith("(resized)") and "/ Wikimedia Commons" in x["text"]
           and any(f"/ {l} /" in x["text"] for l in ok_lic) and any("commons.wikimedia.org/wiki/File:" in h for h in x["links"]))]
    check(15 <= len(g) <= 25 and not bad, f"gallery: {len(g)} photos, each 'Photo: name / license / Wikimedia Commons (resized)', linked ({bad[:2]})")
    check(not any(" NC" in x["text"] or " ND" in x["text"] for x in g), "…no NC / ND licenses")
    await pg.evaluate("document.querySelector('#mq-gallery').scrollIntoView()"); await pg.wait_for_timeout(1500)
    await pg.screenshot(path=f"{SHOTS}/{tag}-gallery.png")
    await pg.click("#mq-gal-strip .mq-gal-open >> nth=0"); await pg.wait_for_timeout(1200)
    v1 = await pg.evaluate("[document.querySelector('#mq-viewer').open, document.querySelector('#mq-v-n').textContent, document.querySelector('#mq-v-credit').textContent, document.querySelector('#mq-v-img').naturalWidth]")
    await pg.screenshot(path=f"{SHOTS}/{tag}-viewer.png")
    await pg.click("#mq-v-next"); await pg.wait_for_timeout(600)
    v2 = await pg.evaluate("document.querySelector('#mq-v-n').textContent")
    await pg.click("#mq-v-x"); await pg.wait_for_timeout(300)
    v3 = await pg.evaluate("document.querySelector('#mq-viewer').open")
    check(v1[0] and v1[1].startswith("1 of") and v1[2].startswith("Photo:") and v1[3] >= 800 and v2.startswith("2 of") and not v3, f"viewer: opens big with its credit, Next, ✕ ({v1[1]}, {v2})")
    if tabs:
        await pg.evaluate("window.scrollTo(0, 0)")
        for view in ("news", "sports", "events"):
            await pg.click(f".view.active .mq-chip[data-go='{view}']"); await pg.wait_for_timeout(2500)
            await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
            await pg.screenshot(path=f"{SHOTS}/{tag}-chisme-{view}.png")
        for view, nm in (("weather", "weather"), ("antojos", "ofrendas"), ("juegos", "juegos")):
            await pg.click(f"#tabs [data-view='{view}']"); await pg.wait_for_timeout(3000)
            await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
            await pg.screenshot(path=f"{SHOTS}/{tag}-{nm}.png")
            low = []
            for sel in (".view.active h2", ".view.active p:not(.hint)", "#tabs .tab"):
                cs = await pg.evaluate(CONTRAST, sel)
                if cs and min(cs) < 4.5: low.append((sel, min(cs)))
            check(not low, f"{nm}: contrast ≥ 4.5 ({low})")
        await pg.click("#tabs [data-view='chisme']"); await pg.wait_for_timeout(800)
    # banner ✕
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.click("#muertos-banner-x"); await pg.wait_for_timeout(300)
    gone = await pg.evaluate("getComputedStyle(document.querySelector('#muertos-banner')).display")
    await ready(pg)
    gone2 = await pg.evaluate("getComputedStyle(document.querySelector('#muertos-banner')).display")
    check(gone == "none" and gone2 == "none", f"greeting ✕: gone, and stays gone after a reload ({gone}, {gone2})")
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close()

async def main():
    async with async_playwright() as p:
        c = await p.chromium.launch()
        px = p.devices["Pixel 7"]
        await clock_checks(c, px)
        await override_checks(c, px)
        await phone(c, "Chromium · Pixel 7 · dark", px, "dark", "pixel7-dark", tabs=True)
        await phone(c, "Chromium · Pixel 7 · light", px, "light", "pixel7-light", tabs=True)
        await phone(c, "Chromium · 320 px · dark", px, "dark", "320-dark", w=320)
        await phone(c, "Chromium · 320 px · light", px, "light", "320-light", w=320)
        await c.close()
        wk = await p.webkit.launch()
        ip = p.devices["iPhone 13"]
        await phone(wk, "WebKit · iPhone 13 · dark", ip, "dark", "iphone13-dark")
        await phone(wk, "WebKit · iPhone 13 · light", ip, "light", "iphone13-light")
        await wk.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
