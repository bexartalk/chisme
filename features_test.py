"""Phone (390x844) checks for radar-in-Weather + blue dot, the Sports tab, Settings and dark mode.
Writes screenshots/weather-radar.png, sports-spurs.png, sports-mlb-missions.png, settings.png, dark-mode.png.
Usage: ./venv/bin/python features_test.py [url]   (dark-mode contrast check uses axe-core if found)"""
import io, json, os, sys, tempfile, urllib.request
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"; OUT.mkdir(exist_ok=True)
AXE = Path(os.environ.get("AXE", "/workspace/lh/node_modules/axe-core/axe.min.js"))
PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, timezone_id="America/Chicago",
             geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
fails, errors = [], []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)
def png(page, **kw): return Image.open(io.BytesIO(page.screenshot(**kw)))
def side_by_side(ims, path, gap=24):
    h = max(i.height for i in ims); w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    sheet = Image.new("RGB", (w, h), (40, 40, 40)); x = 0
    for i in ims: sheet.paste(i, (x, 0)); x += i.width + gap
    sheet.save(path)
def region(page, sel, height=None):
    """Phone-screen shot with `sel` scrolled to just under the fixed nav (status pill faded)."""
    page.evaluate(f"window.scrollTo(0, document.querySelector('{sel}').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 8)")
    try: page.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=8000)
    except Exception: pass
    page.wait_for_timeout(700)
    return png(page)

api = json.load(urllib.request.urlopen(URL + "api/sports", timeout=120))
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"], **PHONE)
    page = ctx.pages[0]
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.goto(URL)
    page.wait_for_function("window.__chisme && __chisme.fresh", timeout=120000)
    if page.is_visible("#loc-close"): page.click("#loc-close")

    # ---- nav: News, Sports, Weather, Events (no Radar tab); A−/A+ not on the home screen
    tabs = page.eval_on_selector_all(".tab", "ts => ts.map(t => t.textContent.trim())")
    check([t.split()[-1] for t in tabs] == ["News", "Sports", "Weather", "dieta?", "Juegitos", "Events"], f"nav tabs {tabs}")
    check(not page.is_visible("#font-up"), "A−/A+ are no longer on the home screen")
    check(page.eval_on_selector("#tabs", "e => getComputedStyle(e).position") == "fixed", "nav is position:fixed")

    # ---- B: radar inside Weather, blue dot, no "You are here"
    page.click(".tab[data-view=weather]")
    page.wait_for_timeout(600)
    page.evaluate("document.querySelector('#radar-sec').scrollIntoView({block: 'start'}); scrollBy(0, -80)")
    page.wait_for_function("__chisme.frames.length > 0", timeout=60000)
    page.wait_for_function("document.querySelectorAll('.basemap img.leaflet-tile-loaded').length >= 4", timeout=30000)
    page.wait_for_timeout(2500)
    r = page.evaluate("""() => { const m = document.querySelector('.me-marker'), dot = m && m.querySelector('.me-dot'), halo = m && m.querySelector('.me-halo');
      const cs = dot && getComputedStyle(dot), hs = halo && getComputedStyle(halo);
      return { inWeather: !!document.querySelector('#view-weather #radar-sec'), youAreHere: document.body.innerText.includes('You are here'),
        tooltips: document.querySelectorAll('.leaflet-tooltip').length, redMarkers: document.querySelectorAll('path.leaflet-interactive').length,
        dotBg: cs && cs.backgroundColor, dotBorder: cs && cs.borderTopColor + ' ' + cs.borderTopWidth, halo: hs && hs.animationName,
        legend: !!document.querySelector('.radar-legend .bar'), time: document.querySelector('#radar-time').textContent,
        basemapTiles: document.querySelectorAll('.basemap img.leaflet-tile-loaded').length,
        radarTiles: document.querySelectorAll('.radar-tiles .leaflet-tile').length }; }""")
    check(r["inWeather"], "radar lives in the Weather section")
    check(not r["youAreHere"] and r["tooltips"] == 0 and r["redMarkers"] == 0, "no 'You are here' label or red marker")
    check(r["dotBg"] == "rgb(10, 132, 255)" and r["dotBorder"].startswith("rgb(255, 255, 255) 3px"), f"blue dot with white ring ({r['dotBg']}, {r['dotBorder']})")
    check(r["halo"] == "me-pulse", "soft pulsing halo (animation me-pulse)")
    check(r["legend"] and r["basemapTiles"] >= 4 and r["radarTiles"] >= 4, f"legend + basemap ({r['basemapTiles']} tiles) + radar ({r['radarTiles']} tiles); badge '{r['time']}'")
    try: page.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=8000)
    except Exception: pass
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "weather-radar.png"))

    # ---- C: Sports
    page.click(".tab[data-view=sports]")
    page.wait_for_function("__chisme.sportsReady", timeout=90000)
    page.wait_for_timeout(800)
    page.click("#sp-chips [data-lg=nba]")
    page.evaluate("window.scrollTo(0, document.querySelector('#sports').getBoundingClientRect().top + scrollY - 80)")
    page.wait_for_timeout(300)
    sp = api["nba"]["spurs"]
    s = page.evaluate("""() => ({ hero: !!document.querySelector('.spurs-hero img'), lines: [...document.querySelectorAll('.spurs-line')].map(e => e.textContent),
      scores: document.querySelectorAll('#sports-body .game').length, sched: document.querySelectorAll('.sched li').length,
      standings: document.querySelectorAll('.standings tbody tr').length, us: document.querySelector('.standings tr.us th')?.textContent,
      news: document.querySelectorAll('#sports-body .sn').length, trend: document.querySelectorAll('.trend li').length,
      thumbs: [...document.querySelectorAll('#sports-body .sn-thumb img')].map(i => i.src),
      credits: [...document.querySelectorAll('.sp-photo figcaption')].map(f => f.textContent),
      links: [...document.querySelectorAll('#sports-body a')].map(a => a.href) })""")
    check(s["hero"] and len(s["lines"]) >= 2, f"Spurs hero + summary: {s['lines']}")
    check(s["scores"] >= len(sp["last"]) and s["sched"] == len(sp["upcoming"]), f"Spurs latest scores ({s['scores']} cards) and schedule ({s['sched']} games)")
    check(s["standings"] >= 8 and s["us"] == "San Antonio Spurs", f"standings table ({s['standings']} rows, Spurs highlighted)")
    check(s["news"] >= 8, f"Spurs news ({s['news']}) + trending links ({s['trend']})")
    check(all("espncdn.com" in u or "espn" in u for u in s["thumbs"]), f"only ESPN story thumbnails as news photos ({len(s['thumbs'])})")
    check(all("Wikimedia Commons" in c and "Photo:" in c for c in s["credits"]) and len(s["credits"]) == 2, "team photos credited (author, license, Commons)")
    check(all(l.startswith("https://") for l in s["links"]), f"{len(s['links'])} links, all https")
    side_by_side([region(page, "#sports"), region(page, "#sports-body .scores"), region(page, "#sports-body .table-wrap")], OUT / "sports-spurs-features.png")
    # the score strip scrolls sideways without switching views
    box = page.locator("#sports-body .scores").first.bounding_box()
    page.evaluate("document.querySelector('#sports-body .scores').scrollIntoView({block: 'center'})")
    box = page.locator("#sports-body .scores").first.bounding_box()
    cdp = ctx.new_cdp_session(page)
    def swipe(x0, x1, y):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
        for k in range(1, 13): cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / 12, "y": y}]}); page.wait_for_timeout(14)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    swipe(box["x"] + box["width"] - 30, box["x"] + 30, box["y"] + box["height"] / 2)
    page.wait_for_timeout(700)
    check(page.evaluate("__chisme.view") == "sports", "swiping the score strip stays on Sports")

    shots = []
    for lg, sel in (("mlb", "#sports"), ("missions", "#sports")):
        page.click(f"#sp-chips [data-lg={lg}]"); page.wait_for_timeout(700)
        page.evaluate("window.scrollTo(0, document.querySelector('#sports').getBoundingClientRect().top + scrollY - 80)")
        info = page.evaluate("""() => ({ games: document.querySelectorAll('#sports-body .game').length, tx: document.querySelectorAll('#sports-body .game.tx').length,
          news: document.querySelectorAll('#sports-body .sn').length, table: document.querySelectorAll('.standings tbody tr').length,
          intro: document.querySelector('#sports-intro').textContent, blurb: document.querySelector('#sports-body .blurb')?.textContent })""")
        print("   ", lg, info)
        if lg == "mlb":
            check(info["games"] == len(api["mlb"]["games"]) + len(api["mlb"].get("next") or []) and info["news"] > 5, f"MLB scores ({info['games']}, Texas teams {info['tx']}) + news ({info['news']})")
        else:
            check(info["table"] == 5 and info["games"] >= 1 and info["news"] >= 1, f"Missions standings, results ({info['games']}) and news ({info['news']}): {info['blurb']}")
        page.wait_for_timeout(1200)
        shots.append(region(page, "#sports-body"))
        if lg == "missions": shots.append(region(page, "#sports-body .scores"))
    side_by_side(shots, OUT / "sports-mlb-missions.png")
    page.click("#sp-chips [data-lg=nfl]"); page.wait_for_timeout(500)
    nfl = page.evaluate("() => ({ games: document.querySelectorAll('#sports-body .game').length, first: document.querySelector('#sports-body .game')?.getAttribute('aria-label') })")
    check(nfl["games"] == len(api["nfl"]["games"]), f"NFL scores ({nfl['games']}), Texas first: {nfl['first']}")

    # ---- D: Settings
    page.evaluate("window.scrollTo(0, 0)")
    page.click("#settings-btn")
    page.wait_for_timeout(400)
    check(page.evaluate("document.querySelector('#settings').open"), "tapping the Chisme icon opens Settings")
    fs0 = page.evaluate("getComputedStyle(document.documentElement).fontSize")
    page.click("#font-up"); page.wait_for_timeout(200)
    fs1 = page.evaluate("getComputedStyle(document.documentElement).fontSize")
    check(fs1 != fs0 and page.evaluate("localStorage.getItem('chisme-font-px')"), f"A+ in Settings: {fs0} → {fs1} (saved)")
    page.click("#font-down"); page.wait_for_timeout(200)
    check(not page.query_selector("#settings input[name=greet]") and not page.query_selector(".greet-switch"), "no chismoso/chismosa choice (Settings or home card)")
    check(page.eval_on_selector("#greet-hi", "e => e.textContent").endswith(", chismosos!"), "greeting is plural: " + page.eval_on_selector("#greet-hi", "e => e.textContent"))
    page.check("#settings input[name=deftab][value=sports]")
    page.fill("#set-loc-q", "78704"); page.click("#set-loc-form button[type=submit]")
    page.wait_for_function("/Austin/.test(document.querySelector('#set-loc-now').textContent)", timeout=60000)
    check(True, "Change location from Settings: " + page.eval_on_selector("#set-loc-now", "e => e.textContent"))
    page.wait_for_function("__chisme.fresh", timeout=120000)
    page.fill("#set-loc-q", "78211"); page.click("#set-loc-form button[type=submit]")
    page.wait_for_function("/San Antonio/.test(document.querySelector('#set-loc-now').textContent)", timeout=60000)
    page.wait_for_function("__chisme.fresh", timeout=120000)
    page.click("#set-refresh")
    page.wait_for_function("document.querySelector('#set-refresh-note').textContent.startsWith('Last updated') || __chisme.sync.busy.length > 0", timeout=10000)
    page.wait_for_function("document.querySelector('#set-refresh-note').textContent.startsWith('Last updated')", timeout=90000)
    check(True, "Refresh now: " + page.eval_on_selector("#set-refresh-note", "e => e.textContent"))
    page.evaluate("document.querySelector('.set-body').scrollTop = 0; document.querySelector('#settings').scrollTop = 0")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "settings.png"))
    page.check("#set-motion"); page.wait_for_timeout(100)
    check(page.evaluate("document.documentElement.classList.contains('reduce-motion')") and
          page.eval_on_selector(".me-halo", "e => getComputedStyle(e).animationName") == "none", "Reduce motion stops the pulsing dot (and swipe animation)")
    page.uncheck("#set-motion")
    page.check("#settings input[name=theme][value=dark]"); page.wait_for_timeout(300)
    check(page.evaluate("document.documentElement.dataset.theme") == "dark", "Dark mode applies immediately")
    dark_settings = png(page)
    page.click("#settings-close"); page.wait_for_timeout(300)
    check(not page.evaluate("document.querySelector('#settings').open"), "Done closes Settings")

    # persisted: reload opens on Sports, dark (greeting stays plural)
    page.reload()
    page.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    st = page.evaluate("() => ({ theme: document.documentElement.dataset.theme, view: __chisme.view, greet: document.querySelector('#greet-hi').textContent, ls: {...localStorage} })")
    check(st["theme"] == "dark" and st["view"] == "sports" and "chismosos" in st["greet"] and "chisme-greeting-word" not in st["ls"], f"settings persist across reload: theme {st['theme']}, opens on {st['view']}, '{st['greet']}'")
    keys = sorted(k for k in st["ls"] if k.startswith("chisme-"))
    print("    localStorage:", {k: st["ls"][k] for k in keys if k in ("chisme-theme", "chisme-default-tab", "chisme-greeting-word", "chisme-reduce-motion", "chisme-font-px", "chisme-sports-league")})

    # ---- dark mode: contrast (axe-core) on every view + settings, and a composite screenshot
    page.wait_for_function("__chisme.sportsReady", timeout=90000)
    dark_shots = []
    if AXE.exists(): page.add_script_tag(path=str(AXE))
    for v in ("news", "sports", "weather", "events"):
        page.evaluate(f"__chisme.goView('{v}', {{instant: true}})"); page.wait_for_timeout(900)
        if v == "events": page.wait_for_function("__chisme.eventsReady", timeout=120000)
        page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(400)
        if v in ("news", "sports"):
            dark_shots.append(png(page))
        if v == "weather":
            page.evaluate("document.querySelector('#radar-sec').scrollIntoView({block: 'start'}); scrollBy(0, -80)"); page.wait_for_timeout(2500)
            dark_shots.append(png(page)); page.evaluate("window.scrollTo(0, 0)")
        if AXE.exists():
            res = page.evaluate("""async (v) => { const r = await axe.run(document.querySelector('#view-' + v).closest('body'), { runOnly: ['color-contrast'] });
              return r.violations.flatMap(x => x.nodes.map(n => n.target.join(' ') + ' :: ' + (n.any[0]?.message || '').slice(0, 90))).filter(t => !t.includes('leaflet')); }""", v)
            check(not res, f"dark mode contrast on {v}: {len(res)} issues {res[:4]}")
    page.click("#settings-btn"); page.wait_for_timeout(400)
    if AXE.exists():
        res = page.evaluate("""async () => { const r = await axe.run(document.querySelector('#settings'), { runOnly: ['color-contrast'] });
          return r.violations.flatMap(x => x.nodes.map(n => n.target.join(' ') + ' :: ' + (n.any[0]?.message || '').slice(0, 90))); }""")
        check(not res, f"dark mode contrast in Settings: {res[:4]}")
    dark_shots.append(dark_settings)
    side_by_side(dark_shots, OUT / "dark-mode.png")
    page.click("#settings-close")
    # light mode contrast on the new Sports view too
    page.evaluate("localStorage.setItem('chisme-theme', 'light'); localStorage.setItem('chisme-default-tab', 'news')")
    page.reload(); page.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    check(page.evaluate("__chisme.view") == "news", "default tab back to News")
    if AXE.exists():
        page.add_script_tag(path=str(AXE))
        page.evaluate("__chisme.goView('sports', {instant: true})"); page.wait_for_function("__chisme.sportsReady", timeout=90000); page.wait_for_timeout(600)
        res = page.evaluate("""async () => { const r = await axe.run(document.querySelector('#view-sports'), { runOnly: ['color-contrast'] });
          return r.violations.flatMap(x => x.nodes.map(n => n.target.join(' ') + ' :: ' + (n.any[0]?.message || '').slice(0, 90))); }""")
        check(not res, f"light mode contrast on Sports: {res[:4]}")
    ctx.close()

check(not errors, f"no console errors {errors[:3]}")
print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
