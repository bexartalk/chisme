"""Simple-feed (html.simple) click-through: Chromium Pixel 7 + WebKit iPhone 13. Every bottom tab, every ☰ menu item,
the ChismeTV row (strip + See all + a clip opens the reels player), a post opens in the reader, events in the feed, Sign in
/ Join, the photo galleries; no pills on show, From Chisme at most once; no page errors; feed links all resolve.
Usage: URL=http://localhost:8484/ ./venv/bin/python simple_feed_test.py"""
import asyncio, os, sys, urllib.request
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
URL = os.environ.get("URL", "http://localhost:8211/"); fails = []
def check(ok, what): print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "localStorage.removeItem('chisme-default-tab'); localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-terms-ok', String(Date.now())); localStorage.setItem('chisme-notif', JSON.stringify({n:2,shows:1}))"
CLOSE = "document.querySelectorAll('dialog[open]').forEach(d => d.close())"
async def run(bt, dev, name):
    b = await bt.launch(**({"executable_path": "/usr/bin/google-chrome", "args": ["--no-sandbox"]} if bt.name == "chromium" else {}))
    ctx = await b.new_context(**dev, timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
    await ctx.add_init_script(INIT); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: None if "tiktokcdn" in (getattr(e, "stack", "") or "") else errs.append((str(e) + " @ " + (getattr(e, "stack", "") or "").replace("\n", " | "))[:300]))   # (not the TikTok player's own)
    pg.on("console", lambda m: errs.append("console: " + m.text[:200]) if m.type == "error" and "Failed to load resource" not in m.text
          and (m.location or {}).get("url", "").startswith(URL) and "report-only" not in m.text else None)   # Chisme's own errors (not the TikTok / YouTube players')
    print("—", name)
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=120000)
    await pg.wait_for_timeout(1500)
    st0 = await pg.evaluate("[document.documentElement.classList.contains('simple'), window.__chisme.view, window.__chismeLaunch || null]")
    check(st0[0] and st0[1] == "chisme", f"opens on the simple feed {st0}")
    await pg.wait_for_function("() => document.querySelectorAll('#mix-list > .mix-item').length > 10", timeout=180000)
    try: await pg.wait_for_function("() => document.querySelector('.tv-row:not([hidden]) .tv-clip')", timeout=90000)
    except Exception: pass
    await pg.evaluate(CLOSE)
    st = await pg.evaluate("""() => ({ pills: [...document.querySelectorAll('.mq-chips')].some(n => n.offsetParent), fc: document.querySelectorAll('#view-chisme .from-chisme').length,
      tv: document.querySelectorAll('#view-chisme .tv-row:not([hidden])').length, clips: document.querySelectorAll('#view-chisme .tv-clip').length,
      ev: document.querySelectorAll('#mix-list > .mix-events').length, banners: [...document.querySelectorAll('#muertos-banner, .greet, #donate-chisme, #donate-mid, .donate-every')].filter(n => n.offsetParent).length,
      links: [...document.querySelectorAll('#mix-list a[href]')].map(a => a.href).filter(h => h.startsWith('http')).slice(0, 40) })""")
    check(not st["pills"] and st["banners"] == 0, f"no pills, no extra banners ({st['pills']}, {st['banners']})")
    check(st["fc"] <= 1 and st["tv"] >= 1 and st["clips"] > 0, f"From Chisme ≤ 1 ({st['fc']}), ChismeTV rows {st['tv']} with {st['clips']} clips")
    check(st["ev"] > 0, f"events in the feed ({st['ev']})")
    # links in the feed: well-formed http(s), no javascript:, not this server's 404s
    bad = [h for h in st["links"] if not h.startswith(("http://", "https://"))]
    loc = [h for h in st["links"] if h.startswith(URL)]
    for h in loc:
        try: urllib.request.urlopen(h, timeout=20)
        except Exception as ex: bad.append(f"{h} {ex}")
    check(not bad, f"feed links ok ({len(st['links'])} checked, local {len(loc)}) {bad[:3]}")
    # ChismeTV: a clip opens the reels player; See all too
    await pg.evaluate("window.__chisme.goView('chisme', { instant: true })"); await pg.wait_for_timeout(800)
    clip = pg.locator("#view-chisme .tv-row:not([hidden]) .tv-clip").first
    if await clip.count():
        await clip.scroll_into_view_if_needed(); await clip.click(); await pg.wait_for_timeout(2500)
        check(await pg.evaluate("document.getElementById('feed').open"), "a ChismeTV clip opens the reels player")
        await pg.click("#feed-close"); await pg.wait_for_timeout(800)
        await pg.locator("#view-chisme .tv-row:not([hidden]) .tv-row-all").first.click(); await pg.wait_for_timeout(2000)
        check(await pg.evaluate("document.getElementById('feed').open"), "See all opens the reels player"); await pg.click("#feed-close"); await pg.wait_for_timeout(800)
        sl = await pg.evaluate("(() => { const s = document.querySelector('#view-chisme .tv-strip'); s.scrollLeft = 300; return [s.scrollLeft > 0, window.__chisme.view]; })()")
        check(sl[0] and sl[1] == "chisme", f"the clip strip scrolls sideways, the view stays ({sl})")
    # a post opens in the reader
    a = pg.locator("#mix-list > .mix-news a.primary, #mix-list > .mix-news h3 a").first
    if await a.count():
        await a.scroll_into_view_if_needed(); await a.click(); await pg.wait_for_timeout(2500)
        check(await pg.evaluate("document.getElementById('player').open || !!document.querySelector('dialog[open]')"), "a news post opens in the in-app reader")
        await pg.evaluate(CLOSE); await pg.wait_for_timeout(500)
    # bottom tabs
    for v in ("antojos", "juegos", "chisme"):
        await pg.evaluate(CLOSE); await pg.locator(f'#tabs .tab[data-view="{v}"]').click(); await pg.wait_for_timeout(1500)
        check(await pg.evaluate("window.__chisme.view") == v, f"tab {v}")
    await pg.locator("#tab-homies").click(); await pg.wait_for_timeout(2000)
    check(await pg.evaluate("!document.getElementById('sx-view').hidden || /#s\\//.test(location.hash)"), "tab Homies opens the social view"); await pg.evaluate("location.hash=''"); await pg.wait_for_timeout(800)
    await pg.evaluate(CLOSE); await pg.locator("#tab-tia").click(); await pg.wait_for_timeout(1500)
    check(await pg.evaluate("document.getElementById('tia').open"), "tab Tía opens her chat"); await pg.evaluate(CLOSE)
    # ☰ menu items
    await pg.evaluate("window.__chismeMenu.open()"); await pg.wait_for_timeout(600)
    rows = await pg.evaluate("[...document.querySelectorAll('#menu .menu-row, #menu #menu-settings')].map(r => r.dataset.menuItem || r.id)")
    check(len(rows) >= 7, f"☰ menu rows: {rows}"); await pg.evaluate(CLOSE)
    for r in rows:
        await pg.evaluate("location.hash=''"); await pg.evaluate(CLOSE); await pg.wait_for_timeout(300)
        await pg.evaluate("window.__chismeMenu.open()"); await pg.wait_for_timeout(500)
        sel = f'#menu [data-menu-item="{r}"]' if r != "menu-settings" else "#menu-settings"
        href = await pg.evaluate(f"(document.querySelector('{sel}') || {{}}).getAttribute ? document.querySelector('{sel}').getAttribute('href') : null")
        if href and href.startswith("/") and not href.startswith("/#"):   # a real page (e.g. /dmca): check it loads, don't leave
            try: urllib.request.urlopen(URL.rstrip("/") + href, timeout=20); check(True, f"☰ {r} → {href} loads")
            except Exception as ex: check(False, f"☰ {r} → {href}: {ex}")
            await pg.evaluate(CLOSE); continue
        await pg.click(sel); await pg.wait_for_timeout(1800)
        s2 = await pg.evaluate("({ view: window.__chisme.view, hash: location.hash, dlg: [...document.querySelectorAll('dialog[open]')].map(d => d.id), feed: document.getElementById('feed').open })")
        moved = s2["view"] != "chisme" or s2["hash"] or s2["dlg"] or s2["feed"] or r.endswith(":5")
        check(bool(moved), f"☰ {r} does something {s2}")
        if s2["feed"]: await pg.click("#feed-close")
        await pg.evaluate(CLOSE)
        if s2["view"] != "chisme": await pg.evaluate("window.__chisme.goView('chisme')")
    # sign in / join pages
    for h, sel in (("#s/signin", "form button[type=submit]"), ("#s/signup", "form button[type=submit]")):
        await pg.evaluate(f"location.hash='{h}'"); await pg.wait_for_timeout(2000)
        n = await pg.locator(f"#sx-view {sel}").count(); soon = await pg.evaluate("/Opening soon/.test(document.getElementById('sx-view').innerText)")
        check(n > 0 or (h == "#s/signup" and soon), f"{h} shows its form" + (" (signups closed here: 'Opening soon')" if soon else ""))
    await pg.evaluate("location.hash=''"); await pg.wait_for_timeout(1000)
    # galleries below the feed: a photo opens the viewer
    await pg.evaluate("window.__chisme.goView('chisme')"); await pg.wait_for_timeout(800)
    g = pg.locator("#pl-gal-strip button, #pl-gal-strip [role=listitem], #mq-gal-strip button").first
    if await g.count():
        await g.scroll_into_view_if_needed(); await g.click(); await pg.wait_for_timeout(1500)
        check(await pg.evaluate("!!document.querySelector('dialog[open]') || !!document.querySelector('.mq-viewer:not([hidden]), [class*=viewer]:not([hidden])')"), "a gallery photo opens big")
        await pg.keyboard.press("Escape"); await pg.evaluate(CLOSE)
    check(not errs, f"no page errors {errs[:4]}")
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p.chromium, p.devices["Pixel 7"], "Chromium Pixel 7"); await run(p.webkit, p.devices["iPhone 13"], "WebKit iPhone 13")
    print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"); sys.exit(1 if fails else 0)
asyncio.run(main())
