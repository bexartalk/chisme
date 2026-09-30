"""¿Cuál dieta? (food) tab + in-app food player/reader. WebKit (iPhone 13) for the UI/screens, Chromium for real touch
swipes (view swipe, swipe-down to close) and offline.
Screens: cual-dieta-tab.png, food-desk-bottom.png, food-video-player.png, food-video-saved.png, nav-320.png, nav-order.png"""
import asyncio, os, sys, tempfile
from playwright.async_api import async_playwright
URL = os.environ.get("URL", "http://localhost:8211/")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); %s }"
TOP = "(sel) => window.scrollTo(0, document.querySelector(sel).getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 10)"

async def settle(pg):
    try: await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=15000)
    except Exception: pass
    await pg.wait_for_timeout(600)

async def wk(p):
    b = await p.webkit.launch()
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev)
    await ctx.add_init_script(INIT % "")
    pg = await ctx.new_page(); errs = []; third = []; framed = {"on": False}
    # while a news site is framed in the reader, its own scripts' errors (ads, consent banners) surface on the page in WebKit
    sink = lambda msg: (third if framed["on"] else errs).append(msg)
    pg.on("pageerror", lambda e: sink(str(e)[:160]))
    pg.on("console", lambda m: sink(m.text[:160]) if m.type == "error" and "Failed to load resource" not in m.text else None)
    await pg.goto(URL)
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map(t => t.textContent.trim().replace(/^\\S+\\s/, ''))")
    check(tabs == ["News", "Sports", "¿Cuál dieta?", "Weather", "Events"], f"nav is News · Sports · ¿Cuál dieta? · Weather · Events ({tabs})")
    panes = await pg.evaluate("[...document.querySelectorAll('#track > .view')].map(v => v.dataset.view)")
    check(panes == ["news", "sports", "antojos", "weather", "events"], f"swipe panes in the same order ({panes})")
    opts = await pg.evaluate("[...document.querySelectorAll('#settings input[name=deftab]')].map(i => i.value)")
    check(opts == ["news", "sports", "antojos", "weather", "events"], f"Settings 'Open Chisme to' in the same order ({opts})")
    check(await pg.evaluate("document.querySelector('#antojos-title').textContent.trim()") == "🌮 ¿Cuál dieta?", "section title is 🌮 ¿Cuál dieta?")
    check(await pg.evaluate("document.querySelector('#settings input[name=deftab][value=antojos]').parentElement.textContent.trim()") == "🌮 ¿Cuál dieta?", "Settings option reads 🌮 ¿Cuál dieta?")
    check(await pg.evaluate("document.querySelector('#tabs [data-view=antojos] span').textContent") == "🌮", "¿Cuál dieta? keeps the 🌮 icon")
    check(await pg.evaluate("!document.querySelector('#ev-chips [data-cat=food]') && !document.querySelector('#view-events #food-block')"), "no Food chip / food block left in Events")
    fit = await pg.evaluate("(() => { const i = document.querySelector('.tabs-inner'); return i.scrollWidth <= i.clientWidth && [...i.children].every(t => t.getBoundingClientRect().right <= innerWidth); })()")
    check(fit, "5 tabs fit at 390 px")
    await pg.tap('#tabs [data-view="antojos"]')
    await pg.wait_for_function("() => window.__chisme.view === 'antojos' && window.__chisme.foodReady && document.querySelectorAll('#food-creators .fr').length > 2", timeout=60000)
    check("Diet? Not today." in (await pg.text_content("#antojos-intro")), "witty intro line")
    # (the Food sources list credits each creator's YouTube *channel*; that's attribution, not a video)
    yt_blank = await pg.evaluate("[...document.querySelectorAll('a[target=_blank]')].filter(a => /youtube\\.com\\/(watch|shorts|embed|live)|youtu\\.be\\//.test(a.href)).map(a => a.href)")
    check(not yt_blank, f"no target=_blank links to YouTube videos anywhere (Antojos, Saved spots, Sports) ({yt_blank[:2]})")
    desk = await pg.evaluate("""() => { const d = document.querySelector('#food-desk'), strip = document.querySelector('#food-creators'), card = document.querySelector('#antojos');
        return { n: d.querySelectorAll('.desk').length, below: d.getBoundingClientRect().top > strip.getBoundingClientRect().bottom,
                 last: card.lastElementChild === d, visible: !d.hidden, noPhotos: !d.querySelector('img, .fr-thumb'), more: !!document.querySelector('.more-food') }; }""")
    check(desk["visible"] and 0 < desk["n"] <= 5 and desk["below"] and desk["last"] and desk["noPhotos"] and not desk["more"], f"food desk: ≤5 text items at the bottom ({desk})")
    await settle(pg)
    await pg.evaluate(TOP, "#antojos"); await pg.wait_for_timeout(1500)
    await pg.screenshot(path=os.path.join(OUT, "cual-dieta-tab.png"))
    await pg.evaluate(TOP, "#food-latest"); await pg.evaluate("scrollBy(0, 150)"); await pg.wait_for_timeout(1200)
    await pg.screenshot(path=os.path.join(OUT, "food-desk-bottom.png"))
    # video: tap the thumbnail of a card with a known restaurant (Losoya's has an address), else the first card
    idx = await pg.evaluate("(() => { const c = [...document.querySelectorAll('#food-creators .fr')]; const i = c.findIndex(x => /Losoya/.test(x.textContent)); return i < 0 ? 0 : i; })()")
    thumb = pg.locator("#food-creators .fr .fr-thumb").nth(idx)
    await thumb.scroll_into_view_if_needed(); await thumb.tap()
    await pg.wait_for_function("document.querySelector('#player').open && document.querySelector('#player-media iframe')", timeout=10000)
    v = await pg.evaluate("""() => { const f = document.querySelector('#player-media iframe');
        return { src: f.src, allow: f.getAttribute('allow'), kind: document.querySelector('#player-kind').textContent, title: document.querySelector('#player-title').textContent,
                 place: document.querySelector('#player-place').hidden ? null : document.querySelector('#player-place').textContent,
                 dir: (document.querySelector('#player-actions .fs-dir') || {}).href || null, save: !!document.querySelector('#player-actions .fr-save'),
                 blank: [...document.querySelectorAll('#player a[target=_blank]')].map(a => a.href).filter(h => /youtu/.test(h)) }; }""")
    print("   player:", {k: (x[:90] if isinstance(x, str) else x) for k, x in v.items()})
    check(v["src"].startswith("https://www.youtube-nocookie.com/embed/") and "playsinline=1" in v["src"] and "rel=0" in v["src"] and "modestbranding=1" in v["src"], "thumbnail tap opens the in-app player (youtube-nocookie embed, playsinline, rel=0, modestbranding)")
    check(v["kind"].endswith("Video") and v["save"] and not v["blank"], "sheet: Video, Save button, no link out to YouTube")
    if "Losoya" in v["title"]: check(bool(v["place"]) and "Walzem" in v["place"] and v["dir"] and v["dir"].startswith("https://maps.apple.com/"), "sheet shows the restaurant + Directions")
    await pg.wait_for_timeout(5000)
    await pg.screenshot(path=os.path.join(OUT, "food-video-player.png"))
    await pg.tap("#player-actions .fr-save")
    s = await pg.evaluate("[document.querySelector('#player-actions .fr-save').getAttribute('aria-pressed'), document.querySelector('#n-saved').textContent, document.querySelectorAll('#food-creators .fr-save[aria-pressed=true]').length]")
    check(s == ["true", "(1)", 1], f"Save in the sheet saves it (card button + count follow) {s}")
    await pg.tap("#player-close")
    try:   # the dialog's close event (which empties the player) can land a frame after the tap
        await pg.wait_for_function("!document.querySelector('#player').open && !document.querySelector('#player-media').children.length", timeout=3000)
    except Exception:
        pass
    c = await pg.evaluate("[document.querySelector('#player').open, document.querySelector('#player-media').children.length]")
    check(c == [False, 0], f"Close button closes the sheet and stops the video {c}")
    # tapping the card body (not the thumbnail) opens it too
    await pg.locator("#food-creators .fr .fr-by").nth(idx).tap()
    check(await pg.evaluate("document.querySelector('#player').open"), "tapping the card opens the player")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    # articles: reader sheet
    kinds = await pg.evaluate("window.__chismeFoodDesk = [...document.querySelectorAll('#food-desk .desk h4 a')].map(a => a.href)")
    for i in range(len(kinds)):
        framed["on"] = True
        await pg.locator("#food-desk .desk h4 a").nth(i).tap()
        await pg.wait_for_function("document.querySelector('#player').open", timeout=5000)
        r = await pg.evaluate("""() => { const f = document.querySelector('#player-media iframe'), o = document.querySelector('#player-orig .orig-link');
            return { kind: document.querySelector('#player-kind').textContent, frame: f ? f.getAttribute('sandbox') : null, open: o && [o.textContent, o.target],
                     note: document.querySelector('#player-note').textContent }; }""")
        ok = r["kind"].endswith("Article") and r["open"] and r["open"][0].startswith("Open original") and r["open"][1] == "_blank" and (r["frame"] is None or "allow-top-navigation" not in r["frame"])
        check(ok, f"desk item {i + 1} opens the reader ({'framed, sandboxed' if r['frame'] else 'headline card + small Open original link'}: {r['note'][:70]})")
        if r["frame"]: await pg.wait_for_timeout(4000); await pg.screenshot(path="/tmp/wk/reader-framed.png")
        elif not os.path.exists("/tmp/wk/reader.png") or i == 0: await pg.wait_for_timeout(800); await pg.screenshot(path="/tmp/wk/reader.png")
        await pg.tap("#player-close"); await pg.wait_for_timeout(600)
        framed["on"] = False
    # saved spots → reopen in the sheet
    await pg.tap('#food-view [data-fv="saved"]')
    await pg.locator("#food-saved .fs .fr-thumb").first.tap()
    await pg.wait_for_function("document.querySelector('#player').open && document.querySelector('#player-media iframe')", timeout=10000)
    sv = await pg.evaluate("[document.querySelector('#player-actions .fr-save').getAttribute('aria-pressed'), !!document.querySelector('#player-actions .fs-dir'), document.querySelector('#player-place').hidden]")
    check(sv[0] == "true", f"Saved spot reopens in the in-app player, shown as Saved {sv}")
    await pg.wait_for_timeout(5000)
    await pg.screenshot(path=os.path.join(OUT, "food-video-saved.png"))
    await pg.tap("#player-close")
    # Sports YouTube clips play in the same sheet (no Save button there)
    await pg.tap('#tabs [data-view="sports"]')
    try:
        await pg.wait_for_function("[...document.querySelectorAll('#view-sports a[aria-haspopup=dialog]')].length > 0", timeout=30000)
        await pg.evaluate("document.querySelector('#view-sports a[aria-haspopup=dialog]').click()")
        sp = await pg.evaluate("[document.querySelector('#player').open, (document.querySelector('#player-media iframe') || {}).src || '', !!document.querySelector('#player-actions .fr-save')]")
        check(sp[0] and "youtube-nocookie.com/embed/" in sp[1] and not sp[2], f"Sports video plays in the in-app player, without Save ({sp[1][:60]})")
        await pg.tap("#player-close")
    except Exception as ex:
        print("   (no Spurs YouTube clips in the feed right now:", str(ex)[:60], ")")
    # curated TikTok (data/food_tiktok.json) plays in TikTok's official embed player
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.tap('#tabs [data-view="antojos"]'); await pg.wait_for_timeout(600)
    FIND_TT = "[...document.querySelectorAll('#food-creators .fr')].find(x => / · TikTok$/.test(x.querySelector('.fr-by b').textContent))"
    tt = await pg.evaluate(f"(() => {{ const c = {FIND_TT}; if (!c) return null; c.scrollIntoView({{block: 'center', inline: 'center'}}); return c.querySelector('h4 a').textContent; }})()")
    check(tt, f"a curated TikTok card is in the food strip ({tt!r})")
    tt_blank = await pg.evaluate("[...document.querySelectorAll('a[target=_blank]')].map(a => a.href).filter(h => /tiktok\\.com\\/@[^/]+\\/video\\//.test(h))")
    check(not tt_blank, f"no target=_blank links to TikTok videos ({tt_blank[:2]})")
    if tt:
        await pg.wait_for_timeout(500)
        framed["on"] = True   # TikTok's player page logs its own CSP / cross-frame warnings
        await pg.evaluate(f"{FIND_TT}.querySelector('.fr-thumb').click()")
        await pg.wait_for_function("() => document.querySelector('#player').open && document.querySelector('#player-media iframe')", timeout=10000)
        t = await pg.evaluate("[document.querySelector('#player-media iframe').src, document.querySelector('#player-media').className, document.querySelector('#player-kind').textContent, document.querySelector('#player-note').textContent, !!document.querySelector('#player-actions .fr-save, #player-actions .save')]")
        check(t[0].startswith("https://www.tiktok.com/player/v1/") and "tall" in t[1] and "official" in t[3], f"TikTok plays in TikTok's official embed player, tall ({t[0][:70]}, {t[1]})")
        await pg.wait_for_timeout(4000); await settle(pg)
        await pg.screenshot(path=os.path.join(OUT, "food-tiktok-player.png"))
        await pg.tap("#player-close")
        check(await pg.evaluate("!document.querySelector('#player').open && !document.querySelector('#player-media iframe')"), "closing stops the TikTok")
        await pg.wait_for_timeout(500); framed["on"] = False
    # Settings → Open Chisme to: ¿Cuál dieta?
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.tap("#settings-btn")
    await pg.check('#settings input[name=deftab][value=antojos]'); await pg.tap("#settings-close")
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
    check(await pg.evaluate("window.__chisme.view") == "antojos", "Settings: Open Chisme to → ¿Cuál dieta? works")
    check(not errs, f"no console/page errors ({errs[:3]})")
    if third: print(f"   note: {len(third)} error(s) from framed sites' own scripts (news site / TikTok player), e.g. {third[0][:90]!r}")
    await ctx.close()
    # 320 px, largest text: the 5 tabs still fit
    for w, font in ((320, 30), (320, None), (390, 30), (390, None)):
        dev2 = dict(dev); dev2["viewport"] = {"width": w, "height": 740}; dev2["screen"] = {"width": w, "height": 740}
        ctx = await b.new_context(**dev2)
        await ctx.add_init_script(INIT % (f"localStorage.setItem('chisme-font-px','{font}');" if font else ""))
        pg = await ctx.new_page(); await pg.goto(URL)
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
        if w == 390 and font is None:
            await settle(pg)
            await pg.screenshot(path=os.path.join(OUT, "nav-order.png"), clip={"x": 0, "y": 0, "width": 390, "height": 200})
        await pg.tap('#tabs [data-view="antojos"]'); await pg.wait_for_timeout(800)
        m = await pg.evaluate("""(() => { const i = document.querySelector('.tabs-inner'), t = [...i.children];
            return { fits: i.scrollWidth <= i.clientWidth + 1 && t.every(x => x.getBoundingClientRect().right <= innerWidth + 0.5 && x.scrollWidth <= x.clientWidth + 1),
                     font: getComputedStyle(t[0]).fontSize, lines: (() => { const l = i.querySelector('[data-view=antojos] .tl'); return Math.round(l.getBoundingClientRect().height / parseFloat(getComputedStyle(l).lineHeight)); })(), rootFont: getComputedStyle(document.documentElement).fontSize, widths: t.map(x => Math.round(x.getBoundingClientRect().width)) }; })()""")
        check(m["fits"] and m["lines"] <= 2, f"{w} px, text {font or 'default'}: 5 tabs fit, no clipping, label ≤ 2 lines ({m})")
        if w == 320 and font == 30:
            await settle(pg)
            await pg.screenshot(path=os.path.join(OUT, "nav-320.png"), clip={"x": 0, "y": 0, "width": 320, "height": 200})
        await ctx.close()
    await b.close()

async def swipe(cdp, x0, x1, y, steps=12, ms=14):
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / steps, "y": y + k * 0.6}]})
        await asyncio.sleep(ms / 1000)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

async def vdrag(cdp, x, y0, dy, steps=16):
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 + dy * k / steps}]})
        await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

async def chrome(p):
    ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(prefix="chisme-fp-"), executable_path="/usr/bin/google-chrome", args=["--no-sandbox"],
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2, timezone_id="America/Chicago")
    await ctx.add_init_script(INIT % "")
    pg = ctx.pages[0]; errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(URL, wait_until="networkidle"); await pg.reload(wait_until="networkidle")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    cdp = await ctx.new_cdp_session(pg)
    await pg.evaluate("window.__chisme.goView('sports', { instant: true })"); await pg.wait_for_timeout(600)
    sy = await pg.evaluate("(() => { const r = document.querySelector('#sports h2').getBoundingClientRect(); return r.top + r.height / 2; })()")
    await swipe(cdp, 330, 50, sy); await pg.wait_for_timeout(900)
    check(await pg.evaluate("window.__chisme.view") == "antojos", "swipe left from Sports lands on ¿Cuál dieta?")
    await pg.wait_for_function("() => window.__chisme.foodReady && document.querySelectorAll('#food-creators .fr').length", timeout=60000)
    iy = await pg.evaluate("(() => { const r = document.querySelector('#antojos .sec-head').getBoundingClientRect(); return r.top + r.height / 2; })()")
    await swipe(cdp, 60, 340, iy); await pg.wait_for_timeout(900)
    check(await pg.evaluate("window.__chisme.view") == "sports", "swipe right from ¿Cuál dieta? goes back to Sports")
    await pg.evaluate("window.__chisme.goView('antojos', { instant: true })"); await pg.wait_for_timeout(600)
    iy = await pg.evaluate("(() => { const r = document.querySelector('#antojos .sec-head').getBoundingClientRect(); return r.top + r.height / 2; })()")
    await swipe(cdp, 330, 50, iy); await pg.wait_for_timeout(900)
    check(await pg.evaluate("window.__chisme.view") == "weather", "swipe left from ¿Cuál dieta? goes on to Weather")
    await pg.evaluate("window.__chisme.goView('antojos', { instant: true })"); await pg.wait_for_timeout(500)
    await pg.evaluate("document.querySelector('#food-creators .fr h4 a').click()")
    await pg.wait_for_function("document.querySelector('#player').open", timeout=5000)
    hb = await pg.evaluate("(() => { const r = document.querySelector('.player-head').getBoundingClientRect(); return [r.left + 40, r.top + r.height / 2]; })()")
    await vdrag(cdp, hb[0], hb[1], 40); await pg.wait_for_timeout(400)
    check(await pg.evaluate("document.querySelector('#player').open"), "a short drag on the sheet snaps back")
    await vdrag(cdp, hb[0], hb[1], 220); await pg.wait_for_timeout(500)
    check(not await pg.evaluate("document.querySelector('#player').open"), "swipe down on the sheet closes it")
    await ctx.set_offline(True); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('#food-creators .fr h4 a').click()")
    off = await pg.evaluate("[navigator.onLine, !!document.querySelector('#player-media .player-off'), (document.querySelector('#player-media') || {}).textContent]")
    check(off[0] is False and off[1] and "offline" in off[2], f"offline: friendly message instead of the player ({off[2][:80]})")
    await pg.screenshot(path="/tmp/wk/player-offline.png")
    await ctx.set_offline(False); await pg.wait_for_timeout(800)
    check(await pg.evaluate("!!document.querySelector('#player-media iframe')"), "back online: the video loads in the open sheet")
    check(not errs, f"chromium: no page errors ({errs[:2]})")
    await ctx.close()

async def main():
    os.makedirs("/tmp/wk", exist_ok=True)
    for f in ("/tmp/wk/reader.png", "/tmp/wk/reader-framed.png"):
        if os.path.exists(f): os.remove(f)
    async with async_playwright() as p:
        await wk(p)
        await chrome(p)
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
