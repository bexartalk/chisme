"""v49.11 CSP + bug sweep: every tab, both games (Juan: start, pause, Skins, Start over, every level warp; Lotería: a few
calls), Tía menu + chat, Settings, a story in the player, the donate buttons, on Android Chrome (Pixel 7, Galaxy S-class
tall 3.75x) and iPhone WebKit. Collects: CSP violations, console errors / page errors, page wider than the screen,
broken images, loading spinners still up after 25 s, tiny tap targets, cut-off button text. Visits only (the anonymous
stats beacon is blocked so the owner's numbers aren't touched).
BASE=http://localhost:8212 (default) or the live site. SLOW=1: Android pass on "slow 3G" (Chromium network throttle).
Screens: /tmp/sweep/<device>-<what>.png"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("BASE", "http://localhost:8212").rstrip("/")
SLOW = os.environ.get("SLOW") == "1"
OUT = os.environ.get("SWEEP_OUT", "/tmp/sweep"); os.makedirs(OUT, exist_ok=True)
ONLY = os.environ.get("ONLY", "")
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
CSPV = "window.__csp=[];document.addEventListener('securitypolicyviolation',function(e){window.__csp.push(e.violatedDirective+' '+(e.blockedURI||'inline')+' '+(e.sourceFile||'')+':'+(e.lineNumber||'')+' '+(e.sample||'').slice(0,60))});"
TABS = ["chisme", "news", "sports", "events", "weather", "antojos", "juegos"]   # v49.12: Chisme (All · News · Sports · Events) · Weather · ¿Y la dieta? · Juegitos
G = "__chisme.juegos.game"
issues = {}
def note(dev, what):
    issues.setdefault(dev, []).append(what); print(f"  ⚠ [{dev}] {what}")

AUDIT = r"""(view) => {
  const out = { overflow: 0, broken: [], tiny: [], cut: [], loading: 0 };
  const W = innerWidth; out.overflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - W;
  const root = view ? document.querySelector('#view-' + view) : document;
  const vis = (e) => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden],[inert]:not(.view)'); };
  for (const im of root.querySelectorAll('img')) if (im.complete && im.naturalWidth === 0 && im.getAttribute('src') && vis(im)) out.broken.push(im.src.slice(0, 120));
  for (const b of root.querySelectorAll('button, [role=button], a.btn, .donate-btn, .tab, .pill')) {
    if (!vis(b) || b.closest('.sr-only')) continue; const r = b.getBoundingClientRect();
    if ((r.width < 32 || r.height < 32) && r.top < innerHeight * 3) out.tiny.push((b.id || b.className || b.tagName).toString().slice(0, 40) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    const s = getComputedStyle(b);
    if (b.scrollWidth > b.clientWidth + 2 && /hidden|clip/.test(s.overflow + s.overflowX) && s.textOverflow !== 'ellipsis') out.cut.push(((b.id || b.className) + ': ' + b.textContent.trim()).slice(0, 60));
  }
  for (const l of root.querySelectorAll('.loading')) if (vis(l)) out.loading++;
  return out;
}"""

SEEN = {}
async def audit(pg, dev, what, view=None, shot=True):
    a = await pg.evaluate(AUDIT, view)
    c = await pg.evaluate("window.__csp || []")
    if len(c) > SEEN.get(dev, 0): print(f"  (CSP before/at '{what}': {c[SEEN.get(dev, 0):][:3]})"); SEEN[dev] = len(c)
    if a["overflow"] > 1: note(dev, f"{what}: page {a['overflow']}px wider than the screen")
    if a["broken"]: note(dev, f"{what}: broken images {a['broken'][:3]}")
    if a["tiny"]: note(dev, f"{what}: small tap targets {sorted(set(a['tiny']))[:6]}")
    if a["cut"]: note(dev, f"{what}: cut-off text {a['cut'][:4]}")
    if shot: await pg.screenshot(path=f"{OUT}/{dev}-{what}.png")
    return a

async def run(p, b, dev, opts):
    print(f"== {dev}")
    ctx = await b.new_context(**opts, service_workers="allow")
    await ctx.add_init_script(SETUP); await ctx.add_init_script(QUIET); await ctx.add_init_script(CSPV)
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page(); errs, bad = [], []
    pg.on("console", lambda m: errs.append(m.text[:220]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:220]))
    pg.on("response", lambda r: bad.append(f"{r.status} {r.url[:110]}") if r.status >= 400 and r.url.startswith(BASE) and "/api/reader" not in r.url else None)
    if SLOW and "android" in dev:
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 400, "downloadThroughput": 400 * 1024 / 8, "uploadThroughput": 400 * 1024 / 8})
    t0 = asyncio.get_event_loop().time()
    await pg.goto(BASE + "/", timeout=180000)
    try:
        await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=180000)
    except Exception:
        note(dev, "app never became ready (blank/stuck loading?)"); await pg.screenshot(path=f"{OUT}/{dev}-stuck.png")
    print(f"  ready in {asyncio.get_event_loop().time() - t0:.1f}s")
    boot = await pg.evaluate("!document.getElementById('boot-fail').hidden")
    if boot: note(dev, "boot-fail card is showing")
    for t in TABS:
        await pg.evaluate(f"__chisme.goView('{t}')")   # v49.12: News / Sports / Events are chips inside the Chisme tab
        for _ in range(50):
            n = await pg.evaluate(f"[...document.querySelectorAll('#view-{t} .loading')].filter(e => e.getBoundingClientRect().height > 0).length")
            if not n: break
            await pg.wait_for_timeout(500)
        else:
            note(dev, f"{t}: still loading after 25 s")
        await pg.wait_for_timeout(1200)
        await audit(pg, dev, t, t)
        await pg.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)"); await pg.wait_for_timeout(600)
        await audit(pg, dev, t + "-lower", t, shot=False)
        await pg.evaluate("window.scrollTo(0, 0)")
    # donate buttons go out to the real pages
    hrefs = await pg.evaluate("[...document.querySelectorAll('a.donate-btn')].map(a => a.href)")
    if not hrefs or any(not (h.startswith("https://cash.app/") or h.startswith("https://buymeacoffee.com/")) for h in hrefs): note(dev, f"donate links look wrong: {hrefs[:4]}")
    # a story in the player (the in-app reader)
    await pg.evaluate("__chisme.goView('news', { instant: true })"); await pg.wait_for_timeout(800)   # Chisme → News
    card = pg.locator("#view-news a.story, #view-news .story a, #view-news article a").first
    if await card.count():
        try:
            await card.click(timeout=5000); await pg.wait_for_timeout(3500)
            if await pg.evaluate("document.getElementById('player').open"):
                await audit(pg, dev, "story-player", None); await pg.click("#player-close"); await pg.wait_for_timeout(500)
        except Exception as ex: note(dev, f"story tap: {type(ex).__name__}")
    # Tía: menu → chat → a message; menu → Settings
    await pg.click("#tia-btn"); await pg.wait_for_timeout(500)
    await audit(pg, dev, "tia-menu")
    await pg.click("#tia-menu-chat"); await pg.wait_for_timeout(600)
    await pg.fill("#tia-in", "¿Qué hay de nuevo?"); await pg.click("#tia-send")
    try: await pg.wait_for_function("document.querySelectorAll('#tia-log .from-tia:not(.typing)').length > 0 && !document.querySelector('#tia-log .typing')", timeout=40000)
    except Exception: note(dev, "Tía never answered")
    await audit(pg, dev, "tia-chat")
    await pg.click("#tia-close"); await pg.wait_for_timeout(400)
    await pg.click("#tia-btn"); await pg.wait_for_timeout(400); await pg.click("#tia-menu-settings"); await pg.wait_for_timeout(800)
    await audit(pg, dev, "settings")
    await pg.evaluate("document.querySelector('#settings .set-alerts, #settings [class*=alert]') && document.querySelector('#settings .set-alerts, #settings [class*=alert]').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
    await audit(pg, dev, "settings-notifications")
    await pg.click("#settings-close"); await pg.wait_for_timeout(400)
    # Juan
    await pg.evaluate("document.querySelector('.tab[data-view=juegos]').click()"); await pg.wait_for_timeout(600)
    await pg.evaluate("document.querySelector('.game-pick[data-game=juan]').click()")
    await pg.wait_for_function(G + " && " + G + ".skins", timeout=30000)
    await audit(pg, dev, "juan-title", "juegos")
    await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(2500)
    st = await pg.evaluate(G + ".state")
    cv = await pg.evaluate("(() => { const c = document.querySelector('.juan-wrap canvas'); const r = c.getBoundingClientRect(); return { w: r.width, h: r.height, iw: innerWidth, ih: innerHeight, sw: document.documentElement.scrollWidth }; })()")
    if cv["w"] < cv["iw"] * 0.9 or cv["h"] < 150 or cv["sw"] > cv["iw"] + 1: note(dev, f"juan canvas looks wrong while running {cv}")
    if await pg.locator(".game-broken").count(): note(dev, "Juan showed 'Tap to reload'")
    await pg.screenshot(path=f"{OUT}/{dev}-juan-run.png")
    await pg.click("#juan-pause"); await pg.wait_for_timeout(300)
    await audit(pg, dev, "juan-paused")
    sk = pg.locator("#juan-ov [data-act=skins]")
    if await sk.count():
        await sk.click(); await pg.wait_for_timeout(500); await audit(pg, dev, "juan-skins")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    if await pg.locator("#juan-ov [data-act=over]").count():
        await pg.click("#juan-ov [data-act=over]"); await pg.wait_for_timeout(800)
        if (await pg.evaluate(G + ".state"))["level"] != 1: note(dev, "Start over didn't go back to level 1")
    nlev = await pg.evaluate("ChismeJuan.LEVELS ? ChismeJuan.LEVELS.length : 7")
    for lv in range(1, nlev + 1):
        try:
            await pg.evaluate(f"{G}.warp({lv}, 600)"); await pg.wait_for_timeout(900)
            s2 = await pg.evaluate(G + ".state")
            if s2["level"] != lv: note(dev, f"warp to level {lv} landed on {s2['level']}")
            if await pg.locator(".game-broken").count(): note(dev, f"level {lv}: 'Tap to reload'"); break
            await pg.screenshot(path=f"{OUT}/{dev}-juan-l{lv}.png")
        except Exception as ex: note(dev, f"level {lv}: {type(ex).__name__} {str(ex)[:80]}")
    await pg.evaluate("document.querySelector('#juan-pause') && document.querySelector('#juan-pause').click()"); await pg.wait_for_timeout(300)
    if await pg.evaluate(f"{G}.state.fullscreen"): await pg.evaluate(f"{G}.exitFullscreen && {G}.exitFullscreen()")
    # Lotería
    await pg.evaluate("document.querySelector('.game-pick[data-game=loteria]').click()"); await pg.wait_for_timeout(1200)
    await audit(pg, dev, "loteria", "juegos")
    start = pg.locator("#game-stage button:has-text('Start'), #game-stage button:has-text('Play'), #game-stage .lot-main").first
    if await start.count():
        try: await start.click(timeout=4000); await pg.wait_for_timeout(5000); await audit(pg, dev, "loteria-play")
        except Exception as ex: note(dev, f"Lotería start: {type(ex).__name__}")
    if await pg.evaluate(f"{G} && {G}.state && {G}.state.fullscreen"): await pg.evaluate(f"{G}.exitFullscreen && {G}.exitFullscreen()")
    csp = await pg.evaluate("window.__csp")
    if csp: note(dev, f"CSP violations: {sorted(set(csp))[:8]}")
    real = [e for e in errs if "access control" not in e and "net::ERR" not in e]
    if real: note(dev, f"console errors: {sorted(set(real))[:8]}")
    if bad: note(dev, f"same-site HTTP errors: {sorted(set(bad))[:8]}")
    await ctx.close()

async def main():
    async with async_playwright() as p:
        ch = await p.chromium.launch(); wk = await p.webkit.launch()
        pixel = dict(p.devices["Pixel 7"]); pixel.pop("default_browser_type", None)
        galaxy = dict(pixel, viewport={"width": 384, "height": 854}, screen={"width": 384, "height": 854}, device_scale_factor=3.75,
                      user_agent="Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36")
        iphone = dict(p.devices["iPhone 13"]); iphone.pop("default_browser_type", None)
        for dev, br, o in (("android-pixel7", ch, pixel), ("android-galaxy", ch, galaxy), ("iphone13", wk, iphone)):
            if ONLY and ONLY not in dev: continue
            try: await run(p, br, dev, o)
            except Exception as ex: note(dev, f"sweep crashed: {type(ex).__name__} {str(ex)[:300]}")
        await ch.close(); await wk.close()
    print("\n== summary"); print(json.dumps(issues, indent=1, ensure_ascii=False)[:6000])
    n = sum(len(v) for v in issues.values()); print("PASS" if not n else f"{n} ISSUES"); sys.exit(1 if n else 0)

asyncio.run(main())
