"""v49.16 (nav-rearrange): the phone nav, rearranged.
  • top bar: ☰ Menu (aria-label "Menu") on the left, the Chisme bubble dead centre (it's a badge that hangs ~12 px past the
    bar's bottom edge, with a shadow; the overhang never takes taps: a tap there reaches the chips under it), no ⚙️ and no
    Tía up top; in the Día de Muertos season the candle and calavera sit either side of the bubble, evenly, and the bubble
    never touches ☰ (320, 360, 390 px)
  • ☰ opens Settings (what ⚙️ opened), focus comes back to ☰; the #menu sheet is there with Settings as its first item (☰
    shows it once it has a 2nd item, e.g. account management)
  • the season's confetti: behind the bar's buttons, only transform animates, paused while the bar is tucked away, still
    under Reduce motion (the system's and Chisme's own), not shown off-season; its SVG tile has no yellow
  • Weather is the Chisme tab's 5th chip (All · News · Sports · Events · Weather) in every chip row; it shows the old Weather
    tab (alerts, current, radar, forecast) with the Chisme tab lit; #weather, #radar, #radar-sec, #forecast-sec, #alerts and
    ?tab=weather land there; the Chisme tab goes back to the Weather chip if that was the last one
  • the bottom tabs: Chisme · ¿Y la dieta? (Ofrendas in the season) · Juegos · Tía; Tía (her avatar) opens her chat and
    is lit while it's open; the bars still hide on scroll down / come back on scroll up
  • ¿Y la dieta? ↔ Ofrendas: with the clock mocked to Oct 10 2026 (no pin) the 2nd tab reads Ofrendas, with it mocked to
    Nov 5 2026 it reads ¿Y la dieta? (the season is over) in the same slot
  • the random launch tab only picks Chisme, the food tab or Juegos (Weather is inside Chisme)
  • no yellow on the bars (news_no_yellow's strict test), season light + dark
  • desktop 1280×800: the nav shows Chisme · ¿Y la dieta?/Ofrendas · Juegos + Settings, no Tía tab (the floating Tía stays)
  • the store app's ChismeNative user agent: the same phone nav, no page errors
Screenshots: SHOTS (default /workspace/chisme-navswap-shots/test/).
    URL=http://127.0.0.1:8480/ ./venv/bin/python nav_rearrange_test.py"""
import ast, asyncio, os, re, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
HERE = os.path.dirname(os.path.abspath(__file__))
_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = next(ast.literal_eval(n.value) if isinstance(n.value, ast.Constant) else None for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SCAN") or None
URL = os.environ.get("URL", "http://localhost:8211/").rstrip("/") + "/"
OUT = os.environ.get("SHOTS", "/workspace/chisme-navswap-shots/test"); os.makedirs(OUT, exist_ok=True)
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

def init(season="muertos", tab="chisme", now=None):
    js = ("try { const s = localStorage; s.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 })); s.setItem('chisme-settings-tip', 'test:0');"
          " s.setItem('chisme-terms-ok', 'test'); s.setItem('chisme-location-setup', '1'); s.setItem('chisme-ios-hint-dismissed', '1'); s.setItem('chisme-swiped', '1');"
          f" s.setItem('chisme-season-pin', '{season}');" + (f" s.setItem('chisme-default-tab', '{tab}');" if tab else " s.removeItem('chisme-default-tab');") + " } catch (e) {}")
    if now is not None:   # a mocked clock (the season test): Date.now() and new Date() start at `now` (ms, UTC)
        js += (f"(() => {{ const R = Date, off = {now} - R.now(); class D extends R {{ constructor(...a) {{ if (a.length) super(...a); else super(R.now() + off); }}"
               " static now() { return R.now() + off; } } window.Date = D; })();")
    return js
IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
async def open_page(b, w=390, h=844, ua=IPHONE_UA, rm=False, theme="light", hash_="", query="", **kw):
    ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=w < 1024, has_touch=w < 1024,
                              user_agent=ua if w < 1024 else None, reduced_motion="reduce" if rm else "no-preference", color_scheme=theme)
    await ctx.add_init_script(init(**kw))
    pg = await ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    await pg.goto(URL + query + hash_); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(1200)
    return ctx, pg

TOP = """() => { const R = (e) => { if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height }; };
  const top = document.querySelector('#fbtop'), menu = document.querySelector('#fb-menu'), bub = document.querySelector('#fbtop #settings-btn'), art = bub && bub.querySelector('.bubble');
  const bar = R(top), a = R(art);
  const x = a ? (a.l + a.r) / 2 : 0, y = bar ? bar.b + 5 : 0, hit = document.elementFromPoint(x, y);
  return { vw: innerWidth, bar, menu: R(menu), btn: R(bub), art: a, vela: R(document.querySelector('#fbtop .mq-vela')), skull: R(document.querySelector('#fbtop .mq-skull')),
    menuLabel: menu && menu.getAttribute('aria-label'), menuPopup: menu && menu.getAttribute('aria-haspopup'),
    gear: !!document.querySelector('#fb-set') || [...top.querySelectorAll('button')].some((b) => /⚙/.test(b.textContent)), topTia: !!top.querySelector('#fb-tia, .fb-tia, img[src*="mascot"]'),
    hitInBar: !!(hit && hit.closest('#fbtop')), hit: hit ? (hit.id || hit.className || hit.tagName) : null,
    artEvents: art ? getComputedStyle(art).pointerEvents : '', shadow: art ? getComputedStyle(art).filter : '',
    bars: [...document.querySelectorAll('#fbtop .fb-burger i')].map((i) => getComputedStyle(i).backgroundColor), menuBg: menu ? getComputedStyle(menu).backgroundColor : '' }; }"""
TABS = """() => [...document.querySelectorAll('#tabs .tab')].filter((t) => t.getClientRects().length).map((t) => ({ v: t.dataset.view || t.id, l: t.textContent.trim(),
  cur: t.getAttribute('aria-current') === 'page', img: !!t.querySelector('img'), w: t.getBoundingClientRect().width, h: t.getBoundingClientRect().height, on: t.classList.contains('tia-on') }))"""
CHIPS = """() => [...document.querySelectorAll('.mq-chips')].map((n) => ({ view: n.closest('.view').dataset.view, chips: [...n.querySelectorAll('.mq-chip[data-go]')].map((c) => c.dataset.go), sx: [...n.querySelectorAll('.sx-chip')].map((c) => c.dataset.sx),
  cur: (n.querySelector('.mq-chip[aria-current="true"]') || {}).dataset?.go }))"""
STATE = "() => ({ view: __chisme.view, tab: (document.querySelector('#tabs .tab[aria-current=\"page\"]') || {}).dataset?.view || null, hide: document.documentElement.classList.contains('fb-hide') })"

async def top_bar(b, w, h):
    tag = f"{w}×{h}"
    ctx, pg = await open_page(b, w, h)
    t = await pg.evaluate(TOP)
    cr = await pg.evaluate("() => { const b = [...document.querySelectorAll('#sx-chips .mq-chip')]; const r = b.map((c) => c.getBoundingClientRect()); return [b.map((c) => c.dataset.go || c.dataset.sx), new Set(r.map((x) => Math.round(x.top))).size, Math.min(...r.map((x) => x.width)), Math.min(...r.map((x) => x.height)), b.filter((c) => c.scrollWidth > c.clientWidth + 0.5).length, Math.max(...r.map((x) => x.right)) <= innerWidth]; }")
    check(cr[0] == ["chisme", "news", "sports", "events", "weather"] and cr[1] == 1 and cr[2] >= 44 and cr[3] >= 44 and not cr[4] and cr[5],
          f"{tag}: Chisme chips are ONE row (All · News · Sports · Events · Weather), 44 px+, untruncated, on screen {cr}")
    c = (t["art"]["l"] + t["art"]["r"]) / 2
    check(t["menu"] and t["menuLabel"].startswith("Menu") and t["menuPopup"] == "dialog" and t["menu"]["w"] >= 42 and t["menu"]["h"] >= 42 and t["menu"]["l"] < 20,
          f"{tag}: ☰ Menu on the left, a 42 px+ button labelled 'Menu' {t['menu']}")
    check(len(t["bars"]) == 3 and t["menuBg"].startswith("rgba"), f"{tag}: ☰ is three bars on a see-through disc ({t['menuBg']})")
    check(not t["gear"] and not t["topTia"], f"{tag}: no ⚙️ and no Tía in the top bar")
    check(abs(c - t["vw"] / 2) <= 1, f"{tag}: the Chisme bubble is centred ({c:.1f} of {t['vw']})")
    check(t["art"]["l"] - t["menu"]["r"] >= 8 and (not t["vela"] or t["vela"]["l"] - t["menu"]["r"] >= 8), f"{tag}: the bubble (and the candle) stay clear of ☰ ({t['menu']['r']:.0f} → {t['vela']['l'] if t['vela'] else t['art']['l']:.0f})")
    if t["vela"] and t["skull"]:
        gl, gr = t["art"]["l"] - t["vela"]["r"], t["skull"]["l"] - t["art"]["r"]
        check(abs(gl - gr) <= 1.5 and 0 <= gl <= 12, f"{tag}: candle and calavera evenly either side of the bubble ({gl:.1f} / {gr:.1f} px)")
        check(t["skull"]["r"] <= t["vw"] - 40, f"{tag}: the calavera leaves the right side clear")
    over = t["art"]["b"] - t["bar"]["b"]
    check(8 <= over <= 18, f"{tag}: the bubble hangs {over:.1f} px past the bar's bottom edge (a badge)")
    check(t["btn"]["b"] <= t["bar"]["b"] and t["artEvents"] == "none" and not t["hitInBar"], f"{tag}: the overhang takes no taps (a tap 5 px under the bar reaches {t['hit']})")
    check("drop-shadow" in t["shadow"], f"{tag}: the bubble has a soft shadow")
    chip_top = await pg.evaluate("Math.min(...[...document.querySelectorAll('.view.active .mq-chip')].map((c) => c.getBoundingClientRect().top))")
    check(chip_top >= t["art"]["b"] + 1, f"{tag}: the chips start below the overhang ({chip_top:.0f} ≥ {t['art']['b']:.0f})")
    await pg.screenshot(path=os.path.join(OUT, f"top-{w}.png"), clip={"x": 0, "y": 0, "width": w, "height": 150})
    await ctx.close()

async def phone(b):
    print("\n== phone 390×844, Día de Muertos")
    ctx, pg = await open_page(b)
    tabs = await pg.evaluate(TABS)
    check([t["v"] for t in tabs] == ["chisme", "antojos", "juegos", "tab-tia"] and tabs[1]["l"].endswith("Ofrendas") and tabs[3]["l"].endswith("Tía") and tabs[3]["img"],
          f"bottom tabs: Chisme · Ofrendas · Juegos · Tía (her avatar) {[t['l'] for t in tabs]}")
    check(all(t["w"] >= 44 and t["h"] >= 44 for t in tabs), "every tab is a 44 px+ target")
    chips = await pg.evaluate(CHIPS)
    check(len(chips) == 5 and all(c["chips"] == ["chisme", "news", "sports", "events", "weather"] and c["cur"] == c["view"] for c in chips)
          and [c["sx"] for c in chips if c["view"] == "chisme"] == [[]] and all(not c["sx"] for c in chips if c["view"] != "chisme"),
          f"every Chisme view has All · News · Sports · Events · Weather, its own lit {[(c['view'], c['cur']) for c in chips]}")
    # v49.20: Chisme's chip row is ONE row, the same five (no Homies / San Anto / Trending / Memes chips)
    rows = await pg.evaluate("() => { const b = [...document.querySelectorAll('#sx-chips .mq-chip')].map((c) => c.getBoundingClientRect()); return [b.length, new Set(b.map((r) => Math.round(r.top))).size, Math.min(...b.map((r) => r.width)), Math.min(...b.map((r) => r.height))]; }")
    check(rows[0] == 5 and rows[1] == 1 and rows[2] >= 44 and rows[3] >= 44, f"Chisme chips: one row of 5, every chip 44 px+ {rows}")
    trunc = await pg.evaluate("[...document.querySelectorAll('.view.active .mq-chip')].filter((c) => c.scrollWidth > c.clientWidth + 0.5).map((c) => c.textContent.trim())")
    check(not trunc, f"the 5 chips fit untruncated {trunc}")
    hi = await pg.evaluate("document.querySelector('#mix-hi').textContent")
    check("Weather" in hi, f"the line under the chips mentions Weather ({hi!r})")
    # Weather chip
    await pg.click('.view.active .mq-chip[data-go="weather"]'); await pg.wait_for_timeout(900)
    st = await pg.evaluate(STATE)
    wx = await pg.evaluate("() => ['#alerts', '#weather', '#radar-sec', '#map'].map((s) => !!document.querySelector('#view-weather.active ' + s))")
    check(st["view"] == "weather" and st["tab"] == "chisme" and all(wx), f"the Weather chip shows the weather (alerts, now, radar) with the Chisme tab lit {st} {wx}")
    await pg.click('#tabs .tab[data-view="juegos"]'); await pg.wait_for_timeout(700)
    await pg.click('#tabs .tab[data-view="chisme"]'); await pg.wait_for_timeout(900)
    check((await pg.evaluate(STATE))["view"] == "weather", "the Chisme tab goes back to the Weather chip (the last one picked)")
    await pg.click('.view.active .mq-chip[data-go="chisme"]'); await pg.wait_for_timeout(900)
    # nav-on-social: ☰ opens one Menu sheet with social's rows (signed out: Join, Sign in, Memes, DMCA) above Settings
    await pg.click("#fb-menu"); await pg.wait_for_timeout(900)
    rm = await pg.evaluate("() => ({ open: document.querySelector('#menu').open, own: !!document.querySelector('#sheet:not([hidden])'), settings: document.querySelector('#settings').open, rows: [...document.querySelectorAll('#menu [data-menu-item]')].map(n => n.dataset.menuItem) })")
    check(rm["open"] and not rm["own"] and not rm["settings"] and rm["rows"][0] == "social:0" and rm["rows"][-1] == "settings" and len(rm["rows"]) == 5,
          f"☰ opens exactly one menu: social's rows (Join, Sign in, Memes, DMCA) then Settings {rm}")
    await pg.screenshot(path=os.path.join(OUT, "menu-social-real.png"))
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    # with only Settings in it, ☰ goes straight to Settings (what ⚙️ opened)
    await pg.evaluate("() => __chismeMenu.setSection('social', null)")
    await pg.evaluate("() => { const M = __chismeMenu; M.__open = M.open; }")
    await pg.evaluate("() => document.querySelector('#fb-menu').onclick = () => { if (!__chismeMenu.sheet) document.querySelector('#settings-btn').click(); }")   # (social's hook would put its rows back on open)
    await pg.click("#fb-menu"); await pg.wait_for_timeout(500)
    check(await pg.evaluate("document.querySelector('#settings').open"), "☰ opens Settings (what ⚙️ opened) when Settings is its only item")
    await pg.screenshot(path=os.path.join(OUT, "menu-open.png"))
    await pg.click("#settings-close"); await pg.wait_for_timeout(400)
    sheet = await pg.evaluate("() => ({ first: document.querySelector('#menu [data-menu-item]')?.dataset.menuItem, label: document.querySelector('#menu-title')?.textContent, n: document.querySelectorAll('#menu [data-menu-item]').length, sheet: __chismeMenu.sheet })")
    check(sheet["first"] == "settings" and sheet["label"] == "Menu" and sheet["n"] == 1 and not sheet["sheet"], f"the Menu sheet has Settings first (one item, so ☰ goes straight to Settings) {sheet}")
    # other features plug rows in (Chisme social's items from social-p1, via __chismeMenu.setSection)
    await pg.evaluate("() => { document.querySelector('#fb-menu').onclick = __chismeMenu.__open; }")
    await pg.evaluate("""() => { window.__picked = null; __chismeMenu.setSection('test', [
      { emoji: '🙋', label: 'My profile', href: '#s/me' }, { emoji: '✏️', label: 'Customize my profile', href: '#s/edit' },
      { emoji: '🤝', label: 'Homies', href: '#s/homies', badge: 2 }, { emoji: '🔔', label: 'Alerts', href: '#s/alerts', badge: 5 },
      { emoji: '😂', label: 'Memes', onSelect: () => { window.__picked = 'memes'; } }, { emoji: '⚙️', label: 'Account and privacy', href: '#s/settings' },
      { emoji: '©️', label: 'Report copyright (DMCA)', href: '/dmca' }]); __chismeMenu.setDot(true); }""")
    await pg.click("#fb-menu"); await pg.wait_for_timeout(500)
    m = await pg.evaluate("() => ({ open: document.querySelector('#menu').open, keys: [...document.querySelectorAll('#menu [data-menu-item]')].map(n => n.dataset.menuItem), dot: !document.querySelector('#fb-menu #sx-dot').hidden, ctl: document.querySelector('#fb-menu').getAttribute('aria-controls') })")
    check(m["open"] and len([k for k in m["keys"] if k.startswith("test:")]) == 7 and m["keys"][0] == "test:0" and m["keys"][-1] == "settings" and m["dot"] and m["ctl"] == "menu", f"with the social rows, ☰ shows the Menu sheet: social first, Settings last, the dot on ☰ {m}")
    await pg.screenshot(path=os.path.join(OUT, "menu-social.png"))
    await pg.click("#menu [data-menu-item='test:4']"); await pg.wait_for_timeout(300)
    check(await pg.evaluate("window.__picked === 'memes' && !document.querySelector('#menu').open"), "a row's onSelect runs and the sheet closes")
    await pg.click("#fb-menu"); await pg.wait_for_timeout(400)
    await pg.click("#menu-settings"); await pg.wait_for_timeout(400)
    check(await pg.evaluate("document.querySelector('#settings').open && !document.querySelector('#menu').open"), "the sheet's Settings opens Settings")
    await pg.click("#settings-close"); await pg.wait_for_timeout(400)
    await pg.evaluate("() => { __chismeMenu.setSection('test', null); __chismeMenu.setSection('social', null); __chismeMenu.setDot(false); }")
    check(await pg.evaluate("!__chismeMenu.sheet && document.querySelector('#fb-menu').getAttribute('aria-controls') === 'settings'"), "removing the section puts ☰ back to one-tap Settings")
    # the bubble still opens Settings too
    await pg.click("#settings-btn"); await pg.wait_for_timeout(400)
    check(await pg.evaluate("document.querySelector('#settings').open"), "the Chisme bubble still opens Settings")
    await pg.click("#settings-close"); await pg.wait_for_timeout(400)
    # Tía tab
    await pg.click("#tab-tia"); await pg.wait_for_timeout(700)
    t = await pg.evaluate("() => [document.querySelector('#tia').open, document.querySelector('#tab-tia').classList.contains('tia-on'), !document.querySelector('#tia-menu').open]")
    check(all(t), f"the Tía tab opens her chat (lit while it's open) {t}")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
    t = await pg.evaluate("() => [document.querySelector('#tia').open, document.querySelector('#tab-tia').classList.contains('tia-on'), document.activeElement && document.activeElement.id]")
    check(t[:2] == [False, False] and t[2] == "tab-tia", f"closing her chat: not lit, focus back on the Tía tab {t}")
    # confetti + hide on scroll
    cf = await pg.evaluate("() => { const c = document.querySelector('.fb-confetti'), a = getComputedStyle(c, '::before'), z = getComputedStyle(c).zIndex; return { shown: getComputedStyle(c).display !== 'none', anim: a.animationName, state: a.animationPlayState, under: +z < +getComputedStyle(document.querySelector('.fbtop-in')).zIndex }; }")
    check(cf["shown"] and cf["anim"] == "fb-confetti" and cf["state"] == "running" and cf["under"], f"the season's confetti drifts behind the bar's buttons {cf}")
    for y in (400, 900, 1400): await pg.mouse.wheel(0, 500); await pg.wait_for_timeout(250)
    await pg.wait_for_timeout(600)
    hid = await pg.evaluate("() => ({ hide: document.documentElement.classList.contains('fb-hide'), top: document.querySelector('#fbtop').getBoundingClientRect().bottom, art: document.querySelector('#fbtop .bubble').getBoundingClientRect().bottom, tabs: document.querySelector('#tabs').getBoundingClientRect().top, vh: innerHeight, cf: getComputedStyle(document.querySelector('.fb-confetti'), '::before').animationPlayState })")
    check(hid["hide"] and hid["art"] <= 1 and hid["tabs"] >= hid["vh"] - 1 and hid["cf"] == "paused", f"scrolling down hides both bars (the badge too) and pauses the confetti {hid}")
    await pg.screenshot(path=os.path.join(OUT, "scrolled.png"))
    await pg.mouse.wheel(0, -60); await pg.wait_for_timeout(700)
    check(not (await pg.evaluate(STATE))["hide"], "a scroll up brings them back")
    check(not pg.errs, f"no page errors {pg.errs[:2]}")
    await ctx.close()

async def deep_links(b):
    print("\n== deep links")
    for h, sec in (("#weather", None), ("#radar", "radar-sec"), ("#radar-sec", "radar-sec"), ("#forecast-sec", "forecast-sec"), ("#alerts", "alerts")):
        ctx, pg = await open_page(b, hash_=h, tab="juegos")
        st = await pg.evaluate(STATE)
        near = True
        if sec: near = await pg.evaluate(f"(() => {{ const r = document.getElementById('{sec}').getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; }})()")
        check(st["view"] == "weather" and st["tab"] == "chisme" and near, f"{h} → the Weather chip in the Chisme tab{' at #' + sec if sec else ''} {st}")
        await ctx.close()
    ctx, pg = await open_page(b, query="?tab=weather", tab=None)
    st = await pg.evaluate(STATE)
    check(st["view"] == "weather" and st["tab"] == "chisme", f"?tab=weather → the Weather chip {st}")
    await ctx.close()
    for h, v in (("#news", "news"), ("#sports", "sports"), ("#events", "events"), ("#food", "antojos"), ("#y-la-dieta", "antojos"), ("#juegos", "juegos"), ("#loteria", "juegos")):
        ctx, pg = await open_page(b, hash_=h, tab="chisme")
        st = await pg.evaluate(STATE)
        check(st["view"] == v, f"{h} → {v} {st}")
        await ctx.close()
    # random launch: never Weather on its own
    ctx, pg = await open_page(b, tab=None)
    picks = set()
    for _ in range(14):
        await pg.evaluate("localStorage.removeItem('chisme-default-tab')"); await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=60000)
        picks.add(await pg.evaluate("__chisme.view"))
    check(picks <= {"chisme", "antojos", "juegos"} and len(picks) >= 2, f"Surprise me picks only Chisme, the food tab or Juegos {sorted(picks)}")
    await ctx.close()

async def season(b):
    print("\n== ¿Y la dieta? ↔ Ofrendas (clock mocked, no pin)")
    for when, ms, want, on in (("Oct 10 2026", 1791633600000, "Ofrendas", True), ("Nov 5 2026", 1793880000000, "¿Y la dieta?", False)):
        ctx, pg = await open_page(b, season="auto", now=ms)
        r = await pg.evaluate("() => [new Date().toISOString(), document.documentElement.dataset.season || '', [...document.querySelectorAll('#tabs .tab')].filter((t) => t.getClientRects().length).map((t) => t.textContent.trim()), getComputedStyle(document.querySelector('.fb-confetti')).display, document.querySelector('#view-antojos').getAttribute('aria-label')]")
        check(r[2][1].endswith(want) and (r[1] == "muertos") == on and len(r[2]) == 4 and r[2][2].endswith("Juegos") and r[2][3].endswith("Tía"),
              f"{when}: the 2nd tab reads {want} (season {'on' if on else 'off'}) {r[:3]}")
        check((r[3] != "none") == on and r[4] == want, f"{when}: confetti {'on' if on else 'off'}, the food view is named {want} ({r[3]}, {r[4]!r})")
        await pg.screenshot(path=os.path.join(OUT, f"season-{'on' if on else 'over'}.png"))
        await ctx.close()

async def motion(b):
    print("\n== Reduce motion")
    ctx, pg = await open_page(b, rm=True)
    a = await pg.evaluate("getComputedStyle(document.querySelector('.fb-confetti'), '::before').animationName + '|' + getComputedStyle(document.querySelector('.fb-confetti'), '::after').animationName + '|' + getComputedStyle(document.querySelector('.fb-confetti')).display")
    check(a.startswith("none|none|") and not a.endswith("none"), f"system Reduce motion: the confetti stays, still ({a})")
    await pg.screenshot(path=os.path.join(OUT, "reduced-motion.png"), clip={"x": 0, "y": 0, "width": 390, "height": 150})
    await ctx.close()
    ctx, pg = await open_page(b)
    await pg.evaluate("document.documentElement.classList.add('reduce-motion')"); await pg.wait_for_timeout(100)
    a = await pg.evaluate("getComputedStyle(document.querySelector('.fb-confetti'), '::before').animationName")
    check(a == "none", f"Chisme's own Reduce motion: still too ({a})")
    await ctx.close()
    ctx, pg = await open_page(b, season="off")
    check(await pg.evaluate("getComputedStyle(document.querySelector('.fb-confetti')).display") == "none", "off-season: no confetti")
    await pg.screenshot(path=os.path.join(OUT, "offseason-top.png"), clip={"x": 0, "y": 0, "width": 390, "height": 150})
    await ctx.close()
    svg = open(os.path.join(HERE, "static/season/fb-confetti.svg")).read()
    cols = sorted(set(c.upper() for c in re.findall(r"#[0-9a-fA-F]{6}\b", svg)))
    def yellow(hx):
        r, g, bl = (int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)); mx, mn = max(r, g, bl), min(r, g, bl); l = (mx + mn) / 2; d = mx - mn
        if d < .05: return False
        s = d / (1 - abs(2 * l - 1))
        if s < .3: return False
        h = 60 * (((g - bl) / d) % 6) if mx == r else 60 * ((bl - r) / d + 2) if mx == g else 60 * ((r - g) / d + 4)
        return 38 <= h <= 70 or (25 <= h < 38 and (l >= .85 or l <= .2))
    check(cols and not [c for c in cols if yellow(c)] and len(svg) < 6000, f"the confetti tile: no yellow ({cols}), {len(svg)} bytes")

async def no_yellow(b):
    print("\n== no yellow on the bars")
    for theme in ("light", "dark"):
        ctx, pg = await open_page(b, theme=theme)
        r = await pg.evaluate("(root) => { " + YELLOW_JS + """
          const rgb = (s) => [...String(s).matchAll(/rgba?\\(([\\d.]+),\\s*([\\d.]+),\\s*([\\d.]+)(?:,\\s*([\\d.]+))?\\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
          const els = [...document.querySelectorAll(root)].flatMap((r) => [r, ...r.querySelectorAll('*')]).filter((e) => e.getClientRects().length && e.tagName !== 'IMG');
          const bad = [];
          for (const e of els) { const cs = getComputedStyle(e);
            for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor, cs.filter, cs.fill]) if (rgb(v).some(yellow)) bad.push((e.id || e.className.baseVal || e.className) + ' ' + String(v).slice(0, 60)); }
          return { n: els.length, bad: [...new Set(bad)].slice(0, 6) }; }""", "#fbtop, #tabs, .view.active .mq-chips")
        check(r["n"] > 20 and not r["bad"], f"Día de Muertos {theme}: no yellow on the top bar, the chips or the tab bar ({r['n']} elements) {r['bad']}")
        await pg.screenshot(path=os.path.join(OUT, f"muertos-{theme}.png"), clip={"x": 0, "y": 0, "width": 390, "height": 150})
        await ctx.close()

async def desktop(b):
    print("\n== desktop 1280×800")
    ctx, pg = await open_page(b, 1280, 800, ua=None)
    r = await pg.evaluate("""() => ({ dk: document.documentElement.classList.contains('dk'), tabs: [...document.querySelectorAll('#tabs .tab')].filter((t) => t.getClientRects().length).map((t) => t.textContent.trim()),
      set: !!document.querySelector('#tabs #settings-btn'), fab: getComputedStyle(document.querySelector('#tia-btn')).display !== 'none', top: getComputedStyle(document.querySelector('#fbtop')).display,
      chips: [...document.querySelectorAll('#view-chisme .mq-chip')].map((c) => c.dataset.go), over: document.querySelector('#tabs').scrollWidth > document.querySelector('#tabs').clientWidth + 1 })""")
    check(r["dk"] and len(r["tabs"]) == 3 and r["tabs"][0].endswith("Chisme") and r["tabs"][2].endswith("Juegos") and not any("Tía" in t or "Weather" in t for t in r["tabs"]),
          f"desktop nav: Chisme · {r['tabs'][1] if len(r['tabs']) > 1 else '?'} · Juegos (no Tía tab, Weather is a chip) {r['tabs']}")
    check(r["set"] and r["fab"] and r["top"] == "none" and not r["over"] and "weather" in r["chips"], f"desktop: Settings in the nav, the floating Tía, no phone top bar, the Weather chip {r}")
    await pg.click('#view-chisme .mq-chip[data-go="weather"]'); await pg.wait_for_timeout(900)
    st = await pg.evaluate(STATE)
    check(st["view"] == "weather" and st["tab"] == "chisme", f"desktop: the Weather chip works, Chisme lit {st}")
    await pg.screenshot(path=os.path.join(OUT, "desktop-1280.png"))
    await pg.set_viewport_size({"width": 390, "height": 844}); await pg.wait_for_timeout(700)
    back = await pg.evaluate("() => ({ dk: document.documentElement.classList.contains('dk'), inCenter: !!document.querySelector('#fbtop .fb-center > #settings-btn'), tia: getComputedStyle(document.querySelector('#tab-tia')).display !== 'none' })")
    check(not back["dk"] and back["inCenter"] and back["tia"], f"narrowed to 390 px: the bubble is back in the centre of the phone bar, the Tía tab shows {back}")
    check(not pg.errs, f"desktop: no page errors {pg.errs[:2]}")
    await ctx.close()

async def native(b):
    print("\n== ChismeNative user agent")
    ctx, pg = await open_page(b, ua=IPHONE_UA + " ChismeNative/1.0")
    tabs = await pg.evaluate(TABS); t = await pg.evaluate(TOP)
    await pg.click("#tab-tia"); await pg.wait_for_timeout(600)
    tia = await pg.evaluate("document.querySelector('#tia').open")
    check([x["v"] for x in tabs] == ["chisme", "antojos", "juegos", "tab-tia"] and t["menuLabel"].startswith("Menu") and tia and not pg.errs, f"the store app's user agent: same nav, Tía opens, no errors {pg.errs[:2]}")
    await ctx.close()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h in ((390, 844), (360, 740), (320, 640)):
            print(f"\n== top bar {w}×{h}"); await top_bar(b, w, h)
        await phone(b); await deep_links(b); await season(b); await motion(b); await no_yellow(b); await desktop(b); await native(b)
        await b.close()
        wk = await p.webkit.launch()
        print("\n== iPhone WebKit 390×844"); await top_bar(wk, 390, 844)
        await wk.close()
    print("\n" + ("ALL OK" if not fails else f"{len(fails)} FAILED:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)
asyncio.run(main())
