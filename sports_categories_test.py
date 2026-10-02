"""v47: the Sports tab's team + league categories, chips in this order: 🏀 Spurs · 🏀 NBA · 🏈 Cowboys · 🏈 NFL (then MLB and
the Missions, unchanged). Spurs = the existing Spurs page (record, scores, schedule, West table, news, fan chisme);
NBA = today's ESPN scoreboard + ESPN league news; Cowboys = Dallas Cowboys (ESPN NFL team 6) record, latest scores, schedule,
NFC East table, news + Blogging The Boys; NFL = today's scoreboard + league news.
Checks /api/sports (shape + cached on the server: a 2nd call returns the same build), then in WebKit (iPhone 13), light and
dark: the chip order and that the new chips look exactly like the old ones, each category's content matches the API, a
story from each opens in the in-app reader (#player, nothing leaves the app), no yellow in the chrome, MLB and Missions
still render, the pick is remembered across reloads, #cowboys / #nba deep links, and no page errors.
Screenshots (light, iPhone 13 width, 390×1700 so each shows the chips and the top of the page): sports-spurs.png, sports-nba.png, sports-cowboys.png, sports-nfl.png."""
import ast, asyncio, json, os, time, urllib.request
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = """localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');
localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1');"""
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

# the same yellow test news_no_yellow_test uses (read from that file, not copied)
_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const r = document.querySelector(root), bad = [];
  for (const e of [r, ...r.querySelectorAll('*')].filter((e) => e.getClientRects().length && !['IMG', 'CANVAS', 'VIDEO', 'IFRAME'].includes(e.tagName))) {
    const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.textShadow, cs.borderTopColor, cs.borderLeftColor, cs.outlineColor])
      if (rgb(v).some(yellow)) { bad.push((e.className || e.tagName) + ' ' + String(v).slice(0, 40)); break; }
  }
  return bad; }"""

def api(path):
    t0 = time.time()
    with urllib.request.urlopen(BASE + path, timeout=120) as r: d = json.load(r)
    return d, time.time() - t0

def check_api():
    print("== /api/sports")
    d, t1 = api("/api/sports")
    d2, t2 = api("/api/sports")
    check(d2["generated"] == d["generated"] and t2 < 1.0, f"cached on the server: the 2nd call is the same build ({t1:.2f}s → {t2:.2f}s)")
    nba, nfl, sp, c = d["nba"], d["nfl"], d["nba"]["spurs"], d["nfl"].get("cowboys")
    check(isinstance(nba["games"], list) and len(nba["news"]) >= 5 and all(n["link"].startswith("https://") for n in nba["news"]), f"NBA: {len(nba['games'])} games today, {len(nba['news'])} ESPN league stories")
    check(isinstance(nfl["games"], list) and len(nfl["news"]) >= 5, f"NFL: {len(nfl['games'])} games on the board, {len(nfl['news'])} stories")
    check(sp["team"]["abbr"] == "SA" and len(sp["news"]) >= 5, f"Spurs page: {sp['record']}, {len(sp['last'])} latest, {len(sp['upcoming'])} upcoming, {len(sp['news'])} stories")
    check(bool(c) and c["team"]["id"] == "6" and c["team"]["name"] == "Dallas Cowboys", "Cowboys page = ESPN NFL team 6, the Dallas Cowboys")
    if c:
        st = c["standings"] or {}
        us = [r for r in st.get("rows", []) if r["us"]]
        check(st.get("division") == "NFC East" and len(st["rows"]) == 4 and len(us) == 1 and us[0]["abbr"] == "DAL", f"Cowboys: NFC East table, Dallas highlighted ({st.get('division')})")
        check(len(c["last"]) + len(c["upcoming"]) + len(c["live"]) >= 1, f"Cowboys: record {c['record']}, {len(c['last'])} latest scores, {len(c['upcoming'])} upcoming, {len(c['live'])} live")
        check(all("DAL" in (g["home"]["abbr"], g["away"]["abbr"]) for g in c["last"] + c["upcoming"] + c["live"]), "every Cowboys game has Dallas in it")
        check(len(c["news"]) >= 5 and all(n["link"].startswith("https://") for n in c["news"]), f"Cowboys news: {len(c['news'])} stories (ESPN + Google News), {len(c['blog'])} from Blogging The Boys")
    names = {s["name"] for s in d["sources"]}
    check({"ESPN: Cowboys news", "ESPN: Cowboys schedule", "ESPN: NFL scoreboard", "ESPN: NBA scoreboard", "ESPN: NBA news", "ESPN: NFL news"} <= names, "new sources listed under Sources")
    return d

CONTENT = """() => { const b = document.querySelector('#sports-body'), q = (s) => b.querySelectorAll(s).length;
  return { lg: b.dataset.lg, games: q('.game'), sched: q('.sched li'), news: q('.sn'), table: q('.standings tbody tr'), hero: !!b.querySelector('.spurs-hero'),
    photo: !!b.querySelector('.spurs-hero img'), kicker: b.querySelector('.spurs-card .kicker')?.textContent || null,
    us: b.querySelector('.standings tr.us th')?.textContent || null, h: [...b.querySelectorAll('h3.sp-h')].map((e) => e.textContent),
    intro: document.querySelector('#sports-intro').textContent, pressed: [...document.querySelectorAll('#sp-chips .chip[aria-pressed=true]')].map((c) => c.dataset.lg) }; }"""

async def open_story(pg, label):
    href = await pg.evaluate("() => { const a = document.querySelector('#sports-body .sn h4 a'); if (!a) return null; a.scrollIntoView({block: 'center'}); a.click(); return a.href; }")
    if not href: check(False, f"{label}: a story to tap"); return
    try:
        await pg.wait_for_function("document.querySelector('#player').open", timeout=20000); ok = True
    except Exception: ok = False
    check(ok and pg.url.startswith(BASE), f"{label}: a story opens in the in-app reader ({href[:70]})")
    await pg.evaluate("document.querySelector('#player').open && document.querySelector('#player').close()"); await pg.wait_for_timeout(300)

async def run(b, dev, theme, d):
    print(f"\n== WebKit iPhone 13, {theme}")
    ctx = await b.new_context(**dev, color_scheme=theme); await ctx.add_init_script(QUIET)
    await ctx.add_init_script(INIT + f"localStorage.setItem('chisme-theme', '{theme}');")
    pg = await ctx.new_page(); errs, popups = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160])); ctx.on("page", lambda p: popups.append(p.url))
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    await pg.evaluate("localStorage.removeItem('chisme-sports-league')")
    await pg.evaluate("__chisme.goView('sports', { instant: true })")
    await pg.wait_for_function("__chisme.sportsReady && document.querySelector('#sports-body .spurs-hero')", timeout=120000); await pg.wait_for_timeout(800)
    chips = await pg.evaluate("""() => [...document.querySelectorAll('#sp-chips .chip')].filter((c) => !c.hidden).map((c) => { const s = getComputedStyle(c);
      return { lg: c.dataset.lg, text: c.textContent.trim(), cls: c.className, pressed: c.getAttribute('aria-pressed'), look: [s.fontSize, s.fontWeight, s.borderRadius, s.height, s.paddingLeft] }; })""")
    check([c["lg"] for c in chips][:4] == ["nba", "nba-all", "cowboys", "nfl"] and [c["text"] for c in chips][:4] == ["🏀 Spurs", "🏀 NBA", "🏈 Cowboys", "🏈 NFL"],
          f"chips in order: {[c['text'] for c in chips]}")
    check({"mlb", "missions"} <= {c["lg"] for c in chips}, "MLB and Missions chips still there")
    check(len({json.dumps(c["look"]) for c in chips}) == 1 and all(c["cls"] == "chip" for c in chips), f"the new chips match the existing chip style ({chips[0]['look']})")
    sp, c = d["nba"]["spurs"], d["nfl"]["cowboys"]
    for lg, name, shot in (("nba", "Spurs", "sports-spurs.png"), ("nba-all", "NBA", "sports-nba.png"), ("cowboys", "Cowboys", "sports-cowboys.png"), ("nfl", "NFL", "sports-nfl.png")):
        await pg.click(f"#sp-chips [data-lg={lg}]"); await pg.wait_for_timeout(700)
        s = await pg.evaluate(CONTENT)
        print("   ", name, {k: s[k] for k in ("games", "sched", "news", "table", "us", "h")})
        check(s["lg"] == lg and s["pressed"] == [lg] and s["intro"], f"{name}: chip pressed, its own intro ({s['intro'][:60]})")
        if lg == "nba":
            check(s["photo"] and s["us"] == "San Antonio Spurs" and s["games"] >= len(sp["last"]) and s["sched"] == len(sp["upcoming"]) and s["news"] >= 5,
                  f"Spurs: hero, {s['games']} scores, {s['sched']} on the schedule, West table (Spurs highlighted), {s['news']} stories")
            check("Around the NBA" not in s["h"], "league-wide scores moved to the NBA chip (no duplicate on the Spurs page)")
        elif lg == "cowboys":
            check(s["hero"] and not s["photo"] and s["kicker"] == "Dallas Cowboys" and s["us"] == "Dallas Cowboys" and s["table"] == 4,
                  f"Cowboys: summary card, NFC East table with Dallas highlighted ({s['h']})")
            check(s["games"] == len(c["last"]) + len(c["live"]) and s["sched"] == len(c["upcoming"]) and s["news"] == len(c["news"]),
                  f"Cowboys: {s['games']} scores, {s['sched']} on the schedule, {s['news']} stories (= the API)")
        else:
            L = d["nba" if lg == "nba-all" else "nfl"]
            check(s["games"] == len(L["games"]) and s["news"] == len(L["news"]) and (s["h"][0].startswith("Today's scores") or s["h"][0].startswith("Next on the board") or s["h"][0].startswith("This week's scoreboard")) and s["h"][1] == f"{name} news",
                  f"{name}: today's scoreboard ({s['games']} games) + league news ({s['news']} stories)")
        bad = await pg.evaluate(SCAN, "#view-sports")
        check(not bad, f"{name} ({theme}): no yellow in the Sports chrome {bad[:3]}")
        if theme == "light":
            vp = pg.viewport_size; await pg.set_viewport_size({"width": vp["width"], "height": 1700}); await pg.wait_for_timeout(400)   # a tall phone shot: chips + the top of the page
            await pg.evaluate("window.scrollTo(0, document.querySelector('#sports').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 12)")
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=os.path.join(OUT, shot))
            await pg.set_viewport_size(vp); await pg.wait_for_timeout(300)
        await open_story(pg, name)
    for lg in ("mlb", "missions"):
        if await pg.evaluate(f"!document.querySelector('#sp-chips [data-lg={lg}]').hidden"):
            await pg.click(f"#sp-chips [data-lg={lg}]"); await pg.wait_for_timeout(600)
            s = await pg.evaluate(CONTENT)
            check(s["lg"] == lg and s["games"] + s["news"] > 0, f"{lg.upper() if lg == 'mlb' else 'Missions'} still renders ({s['games']} games, {s['news']} stories)")
    if theme == "light":
        await pg.click("#sp-chips [data-lg=cowboys]"); await pg.wait_for_timeout(300)
        await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
        await pg.evaluate("__chisme.goView('sports', { instant: true })"); await pg.wait_for_function("__chisme.sportsReady", timeout=120000); await pg.wait_for_timeout(500)
        check(await pg.evaluate("__chisme.spLg") == "cowboys" and await pg.evaluate("document.querySelector('#sports-body').dataset.lg") == "cowboys", "the pick (Cowboys) is remembered after a reload")
        for h, want in (("#nba", "nba-all"), ("#spurs", "nba"), ("#nfl", "nfl")):
            await pg.goto(BASE + "/" + h); await pg.reload(); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.sportsReady", timeout=120000); await pg.wait_for_timeout(400)
            check(await pg.evaluate("__chisme.view") == "sports" and await pg.evaluate("__chisme.spLg") == want, f"{h} opens Sports on the {want} page")
    check(not popups, f"nothing opened a new tab ({popups[:2]})")
    check(not errs, f"no page errors ({errs[:3]})")
    await ctx.close()

async def main():
    d = check_api()
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        for theme in ("light", "dark"): await run(b, dev, theme, d)
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)

asyncio.run(main())
