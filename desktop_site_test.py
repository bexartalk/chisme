"""v49.14 desktop website: on wide screens (1024 px and up) Chisme is a site, not a stretched phone column; phones keep the app.

Against BASE (the build under test, default http://localhost:8211), plus a second copy of the same build this test starts
itself on a free port with the domain-move flags ON and a fixture sponsors file (PUBLIC_BASE_URL=https://chisme.co,
DOMAIN_REDIRECT=1, MOVED_BANNER=1, SPONSORS_FILE=<tmp>), so the flags are tested both off (BASE) and on.

Covers:
  • HTTP: titles, meta descriptions, canonical, Open Graph + Twitter cards (absolute URLs from PUBLIC_BASE_URL, else the
    request origin), the favicon, robots.txt, sitemap.xml, /about, /support (+ /contact → /support), the footer on every page,
    Privacy/Terms decorated (not duplicated), ?embed=1 pages, /qr.svg, /api/site, /api/sponsors (21+ and date filtering).
  • The 301 from the old host: off by default; with DOMAIN_REDIRECT=1 only page navigations move, while the service worker,
    the manifest, /api, /static, fetch()es and the installed app's start URL (?source=pwa) keep working.
  • Chromium 1440×900 and 1024×768: the top nav (logo, 4 tabs, Settings, Get the app), the hero (title, pitch, QR code that
    loads, Add to Home Screen steps, "coming soon" note), the multi-column story grid, the sidebar (weather, sponsor, games,
    ¿Y la dieta?, the $99 App Store goal), the reader as a right side panel (stories and Chisme's own pages), the footer
    links, keyboard (skip link, focus), alt text, contrast, no horizontal scroll, no yellow (light, dark, Día de Muertos),
    no console errors, and going back to the phone layout when the window narrows.
  • Sponsors: the house card ("Your business here" → Support), a paid card with its "Sponsored" tag and rel=sponsored,
    the adult (beer / ice-house) sponsor hidden until the 21+ switch in Settings is on.
  • The "Chisme moved" banner: only for installed users (standalone) on the old origin, and "Later" dismisses it.
  • WebKit iPhone 13: the phone UI is unchanged (no desktop class, nothing injected showing, the app's own header and tabs).
Screenshots go to SHOTS (default /workspace/chisme-desktop-shots)."""
import asyncio, json, os, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import date, timedelta
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("BASE", "http://localhost:8211").rstrip("/")
SHOTS = os.environ.get("SHOTS", "/workspace/chisme-desktop-shots")
os.makedirs(SHOTS, exist_ok=True)
FAILS = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: FAILS.append(what)

# the house tab pick: open on the homepage (QUIET would pin News); Día de Muertos pinned off unless a check pins it on
INIT = ("try { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-default-tab','chisme');"
        " localStorage.setItem('chisme-terms-ok','test'); } catch (e) {}")
READY = "window.__chisme && __chisme.ready && document.querySelector('#mix-list .story')"

# ---------------------------------------------------------------- HTTP helpers
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
OPEN = urllib.request.build_opener(NoRedirect)
def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = OPEN.open(req, timeout=30); return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
NAV = {"Accept": "text/html,application/xhtml+xml", "Sec-Fetch-Mode": "navigate"}

def meta(html, attr, name):
    import re
    m = re.search(r'<meta\s+' + attr + r'="' + re.escape(name) + r'"\s+content="([^"]*)"', html)
    return m.group(1) if m else None

def free_port():
    for p in range(8301, 8399):
        if p in (8211, 8231, 8260, 8275): continue
        with socket.socket() as s:
            try: s.bind(("127.0.0.1", p)); return p
            except OSError: continue
    raise RuntimeError("no free port")

# ---------------------------------------------------------------- the flags server (same build, flags on, fixture sponsors)
TODAY = date.today()
FIXTURE = {"sponsors": [
    {"id": "southtown-tacos", "name": "Southtown Tacos", "url": "https://example.com/tacos", "tagline": "Breakfast tacos till 2.",
     "area": "Southtown", "cta": "See the menu", "alt": "Southtown Tacos", "adult": False, "weight": 5},
    {"id": "ice-house", "name": "La Ice House", "url": "https://example.com/icehouse", "tagline": "Cold ones and conjunto on the patio.",
     "area": "East Side", "cta": "Find the patio", "adult": True, "weight": 5},
    {"id": "old-promo", "name": "Expired Promo", "url": "https://example.com/old", "cta": "Old", "end": str(TODAY - timedelta(days=2))},
    {"id": "later-promo", "name": "Future Promo", "url": "https://example.com/later", "cta": "Later", "start": str(TODAY + timedelta(days=5))},
    {"id": "off-promo", "name": "Paused Promo", "url": "https://example.com/off", "cta": "Off", "active": False},
    {"id": "bad-url", "name": "Not https", "url": "http://example.com/x", "cta": "Nope"},
]}

def start_flags_server():
    port = free_port()
    tmp = tempfile.mkdtemp(prefix="chisme-dk-")
    sp = os.path.join(tmp, "sponsors.json")
    with open(sp, "w") as f: json.dump(FIXTURE, f)
    env = dict(os.environ, PUBLIC_BASE_URL="https://chisme.co", DOMAIN_REDIRECT="1", MOVED_BANNER="1", SPONSORS_FILE=sp,
               REDIRECT_FROM_HOSTS="chisme.onrender.com", APP_STORE_GOAL_RAISED="25")
    log = open(os.path.join(tmp, "server.log"), "w")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            if get(url + "/healthz")[0] == 200: return proc, url
        except Exception: pass
        time.sleep(0.5)
    proc.kill(); raise RuntimeError("flags server didn't start: see " + log.name)

# ---------------------------------------------------------------- page-side checks
YELLOW = r"""(sels) => { const yellow = ([r, g, b, a]) => { if (a != null && a < 0.1) return false; r /= 255; g /= 255; b /= 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < 0.05) return false;
    const s = d / (1 - Math.abs(2 * l - 1)); if (s < 0.3) return false;
    let h = mx === r ? 60 * (((g - b) / d) % 6) : mx === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4); if (h < 0) h += 360;
    return (h >= 38 && h <= 70) || (h >= 25 && h < 38 && (l >= 0.85 || l <= 0.2)); };
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const roots = sels.flatMap((s) => [...document.querySelectorAll(s)]);
  const els = roots.flatMap((r) => [r, ...r.querySelectorAll('*')]).filter((e) => e.getClientRects().length && !['IMG','CANVAS','VIDEO','IFRAME','PICTURE','SOURCE'].includes(e.tagName));
  const bad = [];
  for (const e of els) { const cs = getComputedStyle(e), what = (e.id ? '#' + e.id : '') + ([...e.classList].length ? '.' + [...e.classList].join('.') : '') + ' <' + e.tagName.toLowerCase() + '>';
    const props = { background: cs.backgroundColor, gradient: cs.backgroundImage, text: cs.color, glow: cs.boxShadow, 'text-shadow': cs.textShadow,
      border: [cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor, cs.borderLeftColor].filter((c, i) => parseFloat([cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth][i]) > 0).join(' '),
      outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 ? cs.outlineColor : '' };
    for (const [k, v] of Object.entries(props)) if (rgb(v).some(yellow)) bad.push(`${what} ${k} ${String(v).slice(0, 60)}`); }
  return { n: els.length, bad: [...new Set(bad)].slice(0, 8) }; }"""

# WCAG contrast of text against the first solid background behind it (gradients/images are skipped as unknown)
CONTRAST = r"""(sels) => { const lum = (c) => { const [r, g, b] = c.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const parse = (s) => { const m = String(s).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/); return m ? [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]] : null; };
  const bgOf = (e) => { for (let x = e; x; x = x.parentElement) { const cs = getComputedStyle(x); if (cs.backgroundImage !== 'none' && !/gradient/.test(cs.backgroundImage)) return null; const c = parse(cs.backgroundColor); if (c && c[3] >= 0.95) return c; if (/gradient/.test(cs.backgroundImage)) return null; } return [255, 255, 255, 1]; };
  const out = []; for (const s of sels) for (const e of document.querySelectorAll(s)) { if (!e.getClientRects().length || !e.textContent.trim()) continue;
    const cs = getComputedStyle(e), fg = parse(cs.color), bg = bgOf(e); if (!fg || !bg) continue;
    const a = lum(fg), b = lum(bg), r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const big = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.66 && +cs.fontWeight >= 700);
    if (r < (big ? 3 : 4.5)) out.push(`${s} "${e.textContent.trim().slice(0, 30)}" ${r.toFixed(2)}`); }
  return out.slice(0, 8); }"""

DESK_ROOTS = ["#tabs", "#dk-hero", "#dk-getapp", ".dk-side", ".dk-foot", "#mix-list", ".dk-main > .card", "#set-sponsors"]

async def new_page(browser, w, h, extra_init=None, **kw):
    ctx = await browser.new_context(viewport={"width": w, "height": h}, **kw)
    await ctx.add_init_script(INIT)
    if extra_init: await ctx.add_init_script(extra_init)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text) if m.type == "error" else None)
    return ctx, pg

async def ready(pg, url):
    await pg.goto(url)
    await pg.wait_for_function(READY, timeout=90000)
    await pg.wait_for_function("document.documentElement.classList.contains('dk') ? !!document.querySelector('#dk-sponsor .dk-sp-name') : true", timeout=20000)
    await pg.wait_for_timeout(800)

async def desktop_checks(browser, w, h, tag):
    print(f"\n== Chromium {w}×{h}")
    ctx, pg = await new_page(browser, w, h)
    await ready(pg, BASE + "/")
    check(await pg.evaluate("document.documentElement.classList.contains('dk')"), f"{tag}: html.dk (desktop layout on)")
    check(await pg.evaluate("document.querySelector('#view-chisme').classList.contains('active')"), f"{tag}: opens on the homepage (Chisme tab)")
    check(await pg.title() == "Chisme · San Antonio news, food & games for los metiches", f"{tag}: page title")
    # nav
    nav = await pg.evaluate("""() => { const t = document.querySelector('#tabs'), r = t.getBoundingClientRect();
      return { top: r.top, h: r.height, logo: !!t.querySelector('.dk-logo img[alt]'), tabs: [...t.querySelectorAll('.tab')].filter((b) => b.getClientRects().length).map((b) => b.textContent.trim()),
        set: !!t.querySelector('#settings-btn'), get: (t.querySelector('#dk-get') || {}).textContent || '', over: t.scrollWidth > t.clientWidth + 1,
        topbar: getComputedStyle(document.querySelector('#topbar')).display }; }""")
    check(nav["top"] <= 1 and nav["h"] < 110, f"{tag}: nav at the top ({nav['top']:.0f}px, {nav['h']:.0f}px tall)")
    check(nav["logo"] and nav["set"] and "Get the app" in nav["get"], f"{tag}: nav has the logo, Settings and Get the app")
    check(len(nav["tabs"]) == 4 and any("Chisme" in t for t in nav["tabs"]) and any("Weather" in t for t in nav["tabs"])
          and any(("dieta" in t) or ("Ofrendas" in t) for t in nav["tabs"]) and any("Juegitos" in t for t in nav["tabs"]), f"{tag}: the 4 tabs {nav['tabs']}")
    check(not nav["over"] and nav["topbar"] == "none", f"{tag}: nav fits, the phone header is hidden")
    # hero
    hero = await pg.evaluate("""() => { const q = (s) => document.querySelector(s); const qr = q('#dk-getapp img');
      return { h1: (q('#dk-hero h1') || {}).textContent || '', hola: (q('#dk-hero') || {}).textContent || '', qr: qr ? [qr.naturalWidth, qr.alt, qr.getAttribute('src')] : null,
        a2hs: (q('#dk-getapp') || {}).textContent || '', h1s: [...document.querySelectorAll('h1')].filter((e) => e.getClientRects().length).length }; }""")
    check(hero["h1"].strip() == "Chisme, the community for los metiches", f"{tag}: hero title")
    check("¡Hola, metiche!" in hero["hola"] and "waiting room" in hero["hola"], f"{tag}: Tía's greeting and the pitch")
    check(bool(hero["qr"]) and hero["qr"][0] > 0 and hero["qr"][1] and hero["qr"][2].startswith("/qr.svg"), f"{tag}: QR code loads, with alt text")
    check("Add to Home Screen" in hero["a2hs"] and "Coming soon to the App Store and Google Play" in hero["a2hs"], f"{tag}: Add to Home Screen steps + coming soon")
    check(hero["h1s"] == 1, f"{tag}: one visible h1 on the page ({hero['h1s']})")
    # grid + sidebar
    g = await pg.evaluate("""() => { const l = document.querySelector('#mix-list'), cs = getComputedStyle(l);
      const cards = [...l.children].filter((c) => c.getClientRects().length).slice(0, 6).map((c) => c.getBoundingClientRect());
      const side = document.querySelector('.dk-side'), sr = side && side.getBoundingClientRect();
      return { display: cs.display, cols: cs.gridTemplateColumns.split(' ').length, tops: cards.map((r) => Math.round(r.top)), lefts: cards.map((r) => Math.round(r.left)),
        side: sr ? [sr.left, sr.width] : null, main: document.querySelector('.dk-main').getBoundingClientRect().right,
        widgets: ['#dk-wx', '#dk-sponsor', '#dk-games', '#dk-dieta', '#dk-goal'].filter((s) => { const e = document.querySelector(s); return e && e.getClientRects().length; }),
        hscroll: document.documentElement.scrollWidth > innerWidth + 1,
        lazy: [...l.querySelectorAll('img')].filter((i) => i.getAttribute('loading') !== 'lazy').length,
        noalt: [...document.querySelectorAll('.dk-side img, #dk-hero img, #dk-getapp img, #tabs img, .dk-foot img')].filter((i) => !i.hasAttribute('alt')).length }; }""")
    want = 3 if w >= 1400 else 2
    check(g["display"] == "grid" and g["cols"] >= want and len(set(g["lefts"])) >= want, f"{tag}: story grid, {g['cols']} columns (want ≥ {want})")
    check(bool(g["side"]) and g["side"][0] >= g["main"] - 1, f"{tag}: sidebar to the right of the grid")
    check(len(g["widgets"]) == 5, f"{tag}: sidebar widgets weather, sponsor, games, ¿Y la dieta?, goal {g['widgets']}")
    check(not g["hscroll"], f"{tag}: no horizontal scroll")
    check(g["lazy"] == 0, f"{tag}: story images lazy-load")
    check(g["noalt"] == 0, f"{tag}: every desktop image has alt text")
    goal = await pg.evaluate("() => { const e = document.querySelector('#dk-goal'); const a = e.querySelector('a[href*=\"buymeacoffee.com/Chismoso\"]'); return [e.textContent, !!a]; }")
    check("Help get Chisme on the App Store, $99" in goal[0] and goal[1], f"{tag}: the $99 App Store goal → buymeacoffee.com/Chismoso")
    house = await pg.evaluate("() => { const e = document.querySelector('#dk-sponsor'); const a = e.querySelector('a'); return [e.textContent, a && a.getAttribute('href'), !!e.querySelector('.dk-sp-tag')]; }")
    check("This chisme brought to you by" in house[0] and "Your business here" in house[0] and house[1] == "/support#advertise" and not house[2],
          f"{tag}: no sponsors → 'Your business here' house card → Support (no Sponsored tag on it)")
    wx = await pg.evaluate("() => document.querySelector('#dk-wx').textContent")
    check("°" in wx, f"{tag}: weather widget shows a temperature")
    games = await pg.evaluate("() => [...document.querySelectorAll('#dk-games .dk-game b')].map((b) => b.textContent)")
    check("Chismería" in games and any("Juan" in x for x in games), f"{tag}: games widget {games}")
    # contrast + no yellow (light)
    bad = await pg.evaluate(CONTRAST, ["#tabs .tab", ".dk-logo", "#dk-get", "#dk-hero h1", "#dk-hero p", "#dk-getapp li", "#dk-getapp p",
                                       ".dk-side h2", ".dk-side p", ".dk-side a", ".dk-sp-tag", ".dk-foot a", ".dk-foot p", "#mix-list h3 a"])
    check(not bad, f"{tag}: text contrast ≥ WCAG AA {bad}")
    y = await pg.evaluate(YELLOW, DESK_ROOTS)
    check(not y["bad"], f"{tag}: no yellow in the desktop UI, light ({y['n']} elements) {y['bad']}")
    await pg.screenshot(path=os.path.join(SHOTS, f"home-{w}.png"))
    await pg.screenshot(path=os.path.join(SHOTS, f"home-{w}-full.png"), full_page=True)
    # keyboard: the first Tab is the skip link, and it lands on the latest chisme
    await pg.evaluate("window.scrollTo(0, 0); document.activeElement && document.activeElement.blur()")
    await pg.keyboard.press("Tab")
    first = await pg.evaluate("document.activeElement && document.activeElement.className")
    check("dk-skip" in (first or ""), f"{tag}: first Tab = 'Skip to the latest chisme' ({first})")
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(700)
    landed = await pg.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.tagName)")
    check(landed == "mix-title", f"{tag}: the skip link moves focus to the stories ({landed})")
    ring = await pg.evaluate("() => { const t = document.querySelector('#tabs .tab'); t.focus(); const cs = getComputedStyle(t); return cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 || cs.boxShadow !== 'none'; }")
    check(ring, f"{tag}: visible focus ring on the nav tabs")
    # the reader as a side panel
    a = pg.locator("#mix-list .story h3 a").first
    await a.click(); await pg.wait_for_timeout(1500)
    p = await pg.evaluate("() => { const d = document.querySelector('#player'); const r = d.getBoundingClientRect(); return { open: d.open, l: r.left, r: r.right, h: r.height, kind: document.querySelector('#player-kind').textContent }; }")
    check(p["open"] and p["l"] > w * 0.3 and abs(p["r"] - w) < 2 and p["h"] >= h - 2, f"{tag}: a story opens in the reader side panel (x {p['l']:.0f}–{p['r']:.0f}, {p['h']:.0f}px tall)")
    if w == 1440: await pg.screenshot(path=os.path.join(SHOTS, "reader-panel.png"))
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    check(not await pg.evaluate("document.querySelector('#player').open"), f"{tag}: Escape closes the reader")
    # footer links (on every desktop page: here, and the server-side pages below)
    foot = await pg.evaluate("() => [...document.querySelectorAll('.dk-foot a')].map((a) => [a.textContent.trim(), a.getAttribute('href')])")
    hrefs = {h for _, h in foot}
    check({"/about", "/support", "/privacy", "/terms"} <= hrefs, f"{tag}: footer links About, Support, Privacy, Terms {sorted(hrefs)}")
    for path, shot in (("/about", "about"), ("/support", "support"), ("/privacy", "privacy")):
        await pg.evaluate("document.querySelector('.dk-foot').scrollIntoView({block:'end'})")
        await pg.click(f".dk-foot a[href='{path}']"); await pg.wait_for_timeout(1500)
        fr = await pg.evaluate("() => { const f = document.querySelector('#player iframe'); return f ? f.getAttribute('src') : null; }")
        check(bool(fr) and fr.endswith(path + "?embed=1") and await pg.evaluate("document.querySelector('#player').classList.contains('dk-page')"),
              f"{tag}: footer {path} opens in the reader panel ({fr})")
        if w == 1440:
            fh = await pg.frame_locator("#player iframe").locator("h1").first.text_content(timeout=10000)
            check(bool(fh), f"{tag}: {path} loads in the panel ('{(fh or '').strip()[:30]}')")
            await pg.screenshot(path=os.path.join(SHOTS, f"panel-{shot}.png"))
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    # dark + Día de Muertos: still no yellow
    await pg.evaluate("document.documentElement.dataset.theme = 'dark'"); await pg.wait_for_timeout(300)
    y = await pg.evaluate(YELLOW, DESK_ROOTS)
    check(not y["bad"], f"{tag}: no yellow, dark {y['bad']}")
    await pg.evaluate("localStorage.setItem('chisme-season-pin', 'muertos'); document.documentElement.removeAttribute('data-theme')")
    await ready(pg, BASE + "/")
    season = await pg.evaluate("[document.documentElement.dataset.season, [...document.querySelectorAll('#tabs .tab')].map((b) => b.textContent).join(' ')]")
    check(season[0] == "muertos" and "Ofrendas" in season[1], f"{tag}: Día de Muertos theme pinned, the food tab reads Ofrendas {season}")
    y = await pg.evaluate(YELLOW, DESK_ROOTS)
    check(not y["bad"], f"{tag}: no yellow, Día de Muertos {y['bad']}")
    if w == 1440: await pg.screenshot(path=os.path.join(SHOTS, "home-1440-muertos.png"))
    await pg.evaluate("localStorage.setItem('chisme-season-pin', 'off')")
    # narrowing the window goes back to the phone app
    await pg.set_viewport_size({"width": 800, "height": 900}); await pg.wait_for_timeout(600)
    back = await pg.evaluate("""() => ({ dk: document.documentElement.classList.contains('dk'), main: !!document.querySelector('.dk-main'),
      shown: [...document.querySelectorAll('#dk-hero, #dk-getapp, .dk-side, .dk-foot, .dk-navend, .dk-logo')].filter((e) => e.getClientRects().length).length,
      set: !!document.querySelector('#topbar #settings-btn'), topbar: getComputedStyle(document.querySelector('#topbar')).display !== 'none' })""")
    check(not back["dk"] and not back["main"] and back["shown"] == 0 and back["set"] and back["topbar"], f"{tag}: narrowed to 800px → the phone layout {back}")
    await pg.set_viewport_size({"width": w, "height": h}); await pg.wait_for_timeout(600)
    check(await pg.evaluate("document.documentElement.classList.contains('dk') && !!document.querySelector('#view-chisme > .dk-main #mix-list') && !document.querySelector('#dk-hero').hidden"), f"{tag}: widened again → desktop")
    errs = [e for e in pg.errs if "favicon" not in e]
    check(not errs, f"{tag}: no console errors {errs[:4]}")
    await ctx.close()

async def sponsor_checks(browser, FLAGS):
    print("\n== Sponsors (flags server, fixture sponsors) + the moved banner")
    ctx, pg = await new_page(browser, 1440, 900, service_workers="block")   # (so page.route sees /api/sponsors below)
    await ready(pg, FLAGS + "/")
    s = await pg.evaluate("""() => { const e = document.querySelector('#dk-sponsor'), a = e.querySelector('a.dk-btn');
      return { id: e.dataset.sponsor, text: e.textContent, tag: (e.querySelector('.dk-sp-tag') || {}).textContent, rel: a && a.rel, href: a && a.href }; }""")
    check(s["id"] == "southtown-tacos" and "Southtown Tacos" in s["text"] and "This chisme brought to you by" in s["text"], f"{tag_(s)}: paid sponsor card shows")
    check(s["tag"] == "Sponsored" and "sponsored" in (s["rel"] or ""), f"the card has a 'Sponsored' tag and rel=sponsored ({s['tag']}, {s['rel']})")
    check("Ice House" not in s["text"], "the adult (ice-house) sponsor stays hidden without 21+")
    await pg.locator("#dk-sponsor").scroll_into_view_if_needed()
    await pg.locator("#dk-sponsor").screenshot(path=os.path.join(SHOTS, "sponsor-card.png"))
    await pg.click("#dk-sponsor a.dk-btn"); await pg.wait_for_timeout(1200)
    check(await pg.evaluate("document.querySelector('#player').open"), "the sponsor link opens in the in-app reader")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    # the 21+ switch (Settings) → the adult sponsor can show; the client also gates it (route returns only the adult one)
    only_adult = {"sponsors": [dict(FIXTURE["sponsors"][1], start=None, end=None, image=None)]}
    async def route(r):
        await r.fulfill(status=200, content_type="application/json", body=json.dumps(only_adult))
    await pg.route("**/api/sponsors*", route)
    await pg.evaluate("__chismeDesk.reloadSponsors()"); await pg.wait_for_timeout(500)
    t = await pg.evaluate("document.querySelector('#dk-sponsor').textContent")
    check("Your business here" in t and "Ice House" not in t, "client-side: an adult sponsor isn't shown without 21+ (house card instead)")
    await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
    sw = pg.locator("#set-21")
    check(await sw.count() == 1 and not await sw.is_checked(), "Settings has the 21+ switch, off by default")
    await sw.scroll_into_view_if_needed(); await sw.check(); await pg.wait_for_timeout(600)
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    s = await pg.evaluate("() => { const e = document.querySelector('#dk-sponsor'); return { id: e.dataset.sponsor, text: e.textContent, adult: e.classList.contains('dk-adult'), tag: (e.querySelector('.dk-sp-tag') || {}).textContent }; }")
    check(s["id"] == "ice-house" and s["adult"] and "21+" in s["text"] and s["tag"] == "Sponsored", "21+ on → the ice-house sponsor shows, tagged Sponsored and 21+")
    await pg.unroute("**/api/sponsors*")
    await pg.locator("#dk-sponsor").screenshot(path=os.path.join(SHOTS, "sponsor-card-21plus.png"))
    check(await pg.evaluate("localStorage.getItem('chisme-21plus')") == "1", "the 21+ setting is saved on the device")
    errs = list(pg.errs); check(not errs, f"sponsors: no console errors {errs[:4]}")
    # meta on the flags server: absolute URLs from PUBLIC_BASE_URL
    og = await pg.evaluate("() => [document.querySelector('meta[property=\"og:url\"]').content, document.querySelector('link[rel=canonical]').href, (document.querySelector('meta[name=\"chisme-share-url\"]') || {}).content]")
    check(og == ["https://chisme.co/", "https://chisme.co/", "https://chisme.co/"], f"PUBLIC_BASE_URL drives og:url, canonical and the share link {og}")
    await ctx.close()
    # the moved banner: installed (standalone) on the old origin only
    ctx, pg = await new_page(browser, 1440, 900, "Object.defineProperty(Navigator.prototype, 'standalone', { get: () => true, configurable: true });")
    await ready(pg, FLAGS + "/")
    await pg.wait_for_selector("#moved-banner", timeout=8000)
    b = await pg.evaluate("() => { const e = document.querySelector('#moved-banner'); return [e.textContent, document.querySelector('#moved-go').getAttribute('href')]; }")
    check("Chisme moved to chisme.co" in b[0] and "Home Screen" in b[0] and b[1] == "https://chisme.co/", f"installed + old origin → the 'Chisme moved to chisme.co' banner ({b[1]})")
    y = await pg.evaluate(YELLOW, ["#moved-banner"]); check(not y["bad"], f"the moved banner has no yellow {y['bad']}")
    await pg.locator("#moved-banner").screenshot(path=os.path.join(SHOTS, "moved-banner.png"))
    await pg.click("#moved-x"); await pg.wait_for_timeout(300)
    check(await pg.locator("#moved-banner").count() == 0, "'Later' dismisses it")
    await pg.reload(); await pg.wait_for_function(READY, timeout=90000); await pg.wait_for_timeout(1500)
    check(await pg.locator("#moved-banner").count() == 0, "…and it stays dismissed for a few days")
    await ctx.close()
    ctx, pg = await new_page(browser, 1440, 900)
    await ready(pg, FLAGS + "/"); await pg.wait_for_timeout(1000)
    check(await pg.locator("#moved-banner").count() == 0, "a browser tab (not installed) gets no moved banner")
    await ctx.close()
    ctx, pg = await new_page(browser, 1440, 900, "Object.defineProperty(Navigator.prototype, 'standalone', { get: () => true, configurable: true });")
    await ready(pg, BASE + "/"); await pg.wait_for_timeout(1000)
    check(await pg.locator("#moved-banner").count() == 0, "MOVED_BANNER off (default) → no banner, even installed")
    await ctx.close()

def tag_(s): return "sponsor"

async def phone_checks(p):
    print("\n== WebKit iPhone 13 (the phone app, unchanged)")
    b = await p.webkit.launch()
    ctx = await b.new_context(**p.devices["iPhone 13"])
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(BASE + "/"); await pg.wait_for_function(READY, timeout=90000); await pg.wait_for_timeout(1500)
    r = await pg.evaluate("""() => { const tb = document.querySelector('#topbar'), tabs = document.querySelector('#tabs');
      return { dk: document.documentElement.classList.contains('dk'), inj: [...document.querySelectorAll('#dk-hero, #dk-getapp, .dk-side, .dk-main, .dk-foot, .dk-logo, .dk-navend, #set-sponsors, #moved-banner')].length,
        topbar: getComputedStyle(tb).display !== 'none' && tb.getBoundingClientRect().height > 0, set: !!tb.querySelector('#settings-btn'),
        tabs: [...tabs.querySelectorAll('.tab')].filter((b) => b.getClientRects().length).length, w: document.documentElement.scrollWidth, iw: innerWidth,
        css: [...document.styleSheets].some((s) => (s.href || '').includes('desktop.css') && s.media && s.media.mediaText.includes('1024')),
        list: getComputedStyle(document.querySelector('#mix-list')).display, title: document.title }; }""")
    check(not r["dk"] and r["inj"] == 0, f"phone: no desktop class, nothing injected ({r['inj']})")
    check(r["topbar"] and r["set"] and r["tabs"] == 4, "phone: the app's own header (with the Chisme bubble / Settings) and its 4 tabs")
    check(r["list"] != "grid" and r["w"] <= r["iw"], f"phone: single-column feed, no sideways scroll ({r['list']})")
    check(r["css"], "phone: desktop.css only applies at min-width 1024px")
    await pg.screenshot(path=os.path.join(SHOTS, "phone-unchanged.png"))
    check(not errs, f"phone: no page errors {errs[:3]}")
    await b.close()

def http_checks(FLAGS):
    print("\n== HTTP: meta, pages, robots, sitemap, sponsors, the redirect flag")
    st, hd, html = get(BASE + "/")
    check(st == 200, "/ 200")
    base = BASE
    check("<title>Chisme · San Antonio news, food &amp; games for los metiches</title>" in html and html.count("<title>") == 1, "/ title (one)")
    d = meta(html, "name", "description")
    check(bool(d) and "metiches" in d and html.count('name="description"') == 1, f"/ meta description (one): {d}")
    for k in ("og:title", "og:description", "og:image", "og:url", "og:type", "og:site_name"):
        check(bool(meta(html, "property", k)), f"/ {k}")
    check((meta(html, "property", "og:image") or "").startswith(base + "/static/site/og-image.png"), "og:image is absolute (request origin)")
    check(meta(html, "name", "twitter:card") == "summary_large_image" and meta(html, "name", "twitter:image"), "Twitter card")
    check(f'<link rel="canonical" href="{base}/">' in html, "canonical = request origin + /")
    check('rel="icon"' in html and get(BASE + "/static/icons/favicon.ico")[0] == 200, "favicon")
    check(get(BASE + "/static/site/og-image.png")[0] == 200, "og image served")
    check(st == 200 and "chisme-share-url" not in html, "no share-url override without PUBLIC_BASE_URL")
    for path, h1 in (("/about", "About Chisme"), ("/support", "Support")):
        st, _, page = get(BASE + path)
        check(st == 200 and h1 in page and meta(page, "property", "og:title") and meta(page, "name", "description"), f"{path} 200 with title/OG/description")
        check(all(f'href="{x}"' in page for x in ("/about", "/support", "/privacy", "/terms")), f"{path} footer links")
        _, _, emb = get(BASE + path + "?embed=1")
        check('class="site-foot' not in emb and "sn-tabs" not in emb and '/privacy?embed=1' in emb, f"{path}?embed=1: no chrome, links stay in the panel")
    st, _, sup = get(BASE + "/support")
    check("mailto:bexartalkradio@gmail.com" in sup and 'id="advertise"' in sup, "Support uses the repo's contact email, has the advertise section")
    import re
    emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", sup))
    check(emails == {"bexartalkradio@gmail.com"}, f"no invented email addresses {emails}")
    for path in ("/privacy", "/terms"):
        st, _, page = get(BASE + path)
        check(st == 200 and meta(page, "property", "og:title") and 'href="/about"' in page and 'href="/support"' in page and page.count("<h1") == 1,
              f"{path}: the v49.12 page + OG + the site footer")
    st, hd, _ = get(BASE + "/contact")
    check(st == 308 and hd.get("location") in ("/support", hd.get("Location")) or hd.get("Location") == "/support", "/contact → /support")
    st, hd, rb = get(BASE + "/robots.txt")
    check(st == 200 and "Disallow: /api/" in rb and "Disallow: /stats" in rb and f"Sitemap: {base}/sitemap.xml" in rb, "robots.txt")
    st, hd, sm = get(BASE + "/sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    check(st == 200 and "xml" in hd.get("content-type", "") and locs == [base + p for p in ("/", "/about", "/support", "/privacy", "/terms")], f"sitemap.xml {locs}")
    st, hd, qr = get(BASE + "/qr.svg")
    check(st == 200 and "image/svg+xml" in hd.get("content-type", "") and "<path" in qr, "/qr.svg")
    st, _, site = get(BASE + "/api/site"); j = json.loads(site)
    check(j["goal"]["amount"] == 99 and "buymeacoffee.com/Chismoso" in j["goal"]["url"] and not j["moved"]["on"] and j["build"] == "49.14", "/api/site (goal $99, moved off, build 49.14)")
    st, _, sw = get(BASE + "/sw.js")
    check('"chisme-v49.14"' in sw or "'chisme-v49.14'" in sw, "service worker cache chisme-v49.14")
    # redirect flag OFF (default): the old host is served as is
    st, hd, _ = get(BASE + "/", dict(NAV, Host="chisme.onrender.com"))
    check(st == 200, f"DOMAIN_REDIRECT off → no redirect from chisme.onrender.com ({st})")
    # ---- the flags server
    st, _, html = get(FLAGS + "/")
    check(meta(html, "property", "og:url") == "https://chisme.co/" and '<link rel="canonical" href="https://chisme.co/">' in html
          and (meta(html, "property", "og:image") or "").startswith("https://chisme.co/"), "PUBLIC_BASE_URL → canonical / og:url / og:image on chisme.co")
    check(f"Sitemap: https://chisme.co/sitemap.xml" in get(FLAGS + "/robots.txt")[2], "robots.txt sitemap on chisme.co")
    check("<loc>https://chisme.co/about</loc>" in get(FLAGS + "/sitemap.xml")[2], "sitemap URLs on chisme.co")
    check('href="https://chisme.co"' in get(FLAGS + "/privacy")[2], "the Privacy Policy names the new address")
    old = dict(NAV, Host="chisme.onrender.com")
    st, hd, _ = get(FLAGS + "/about?x=1", old)
    check(st == 301 and hd.get("location", hd.get("Location")) == "https://chisme.co/about?x=1", f"DOMAIN_REDIRECT=1: page on the old host → 301 chisme.co ({st} {hd.get('location')})")
    st, hd, _ = get(FLAGS + "/", old)
    check(st == 301 and hd.get("location") == "https://chisme.co/", "…/ too")
    for path, h in (("/sw.js", old), ("/manifest.webmanifest", old), ("/api/site", old), ("/static/app.js", old), ("/healthz", old),
                    ("/?source=pwa", old), ("/", {"Host": "chisme.onrender.com", "Accept": "*/*", "Sec-Fetch-Mode": "cors"}),
                    ("/", {"Host": "chisme.onrender.com", "Accept": "application/json"}), ("/", NAV)):
        st, _, _ = get(FLAGS + path, h)
        check(st == 200, f"not redirected: {path} ({h.get('Host', 'new host')}, {h.get('Sec-Fetch-Mode') or h.get('Accept')}) → {st}")
    st, _, site = get(FLAGS + "/api/site"); j = json.loads(site)
    check(j["moved"] == {"on": True, "to": "https://chisme.co/", "host": "chisme.co"} and j["goal"]["raised"] == 25, f"/api/site moved on + goal raised {j['moved']}")
    ids0 = [s["id"] for s in json.loads(get(FLAGS + "/api/sponsors?adult=0")[2])["sponsors"]]
    ids1 = [s["id"] for s in json.loads(get(FLAGS + "/api/sponsors?adult=1")[2])["sponsors"]]
    check(ids0 == ["southtown-tacos"], f"/api/sponsors?adult=0 → no adult, no expired / future / paused / non-https {ids0}")
    check(sorted(ids1) == ["ice-house", "southtown-tacos"], f"/api/sponsors?adult=1 → + the ice house {ids1}")
    check(json.loads(get(BASE + "/api/sponsors")[2])["sponsors"] == [], "the repo's sponsors.json ships empty (house card)")

async def main():
    proc, FLAGS = start_flags_server()
    try:
        http_checks(FLAGS)
        async with async_playwright() as p:
            chromium = await p.chromium.launch()
            await desktop_checks(chromium, 1440, 900, "1440")
            await desktop_checks(chromium, 1024, 768, "1024")
            await sponsor_checks(chromium, FLAGS)
            await chromium.close()
            await phone_checks(p)
    finally:
        proc.terminate()
        try: proc.wait(10)
        except Exception: proc.kill()
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: desktop_site_test ({len(FAILS)} failing)")
    for f in FAILS: print("   -", f)
    sys.exit(1 if FAILS else 0)

asyncio.run(main())
