"""v47: the game-day banner at the top of the Sports tab ("It's game day!", v49.12: was ¡Hoy hay juego!). /api/sports is mocked (the real payload,
with games moved onto today) so it doesn't depend on the schedule. WebKit, iPhone 13, Central time:
  A) Spurs at home tonight 7:30 PM + Cowboys live (away): both rows, opponent, local start time, Home/Away, LIVE + score;
     tapping the Cowboys row opens the Cowboys chip, tapping the Spurs row the Spurs chip
  B) the Spurs game is final: FINAL + the final score
  C) no game today: no banner
Light and dark: no yellow in the banner (the same check as news_no_yellow_test), no images (no logos), no page errors.
Screenshot: gameday-banner.png (scenario A, light, cropped to the top of the Sports tab)."""
import ast, asyncio, copy, json, os
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
CT = ZoneInfo("America/Chicago")
INIT = """localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1');
localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '1'); localStorage.removeItem('chisme-sports-league');"""
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const r = document.querySelector(root), bad = [];
  for (const e of [r, ...r.querySelectorAll('*')].filter((e) => e.getClientRects().length)) {
    const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.textShadow, cs.borderTopColor, cs.borderLeftColor, cs.outlineColor])
      if (rgb(v).some(yellow)) { bad.push((e.className || e.tagName) + ' ' + String(v).slice(0, 40)); break; }
  }
  return bad; }"""

today = datetime.now(CT).date()
iso = lambda h, m: datetime.combine(today, dtime(h, m), CT).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
side = lambda name, short, abbr, score=None, winner=None: {"name": name, "short": short, "abbr": abbr, "id": "", "score": score, "winner": winner, "record": None}
def game(gid, lg, date, state, home, away, detail, tv=None):
    return {"id": gid, "league": lg, "date": date, "state": state, "detail": detail, "home": home, "away": away, "note": None, "tv": tv, "link": None, "texas": True}

def strip_today(d):   # C: nothing today (whatever the real schedule says)
    is_today = lambda g: g["state"] == "in" or datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(CT).date() == today
    for blk in (d["nba"]["spurs"], d["nfl"].get("cowboys") or {}):
        for k in ("live", "last", "upcoming"):
            if k in blk: blk[k] = [g for g in blk[k] if not is_today(g)]
    for lg in ("nba", "nfl"): d[lg]["games"] = [g for g in d[lg]["games"] if not is_today(g)]
    return d

def scenario(real, which):
    d = strip_today(copy.deepcopy(real))
    sp, cb = d["nba"]["spurs"], d["nfl"]["cowboys"]
    if which == "A":
        sp["upcoming"].insert(0, game("m-spurs", "nba", iso(19, 30), "pre", side("San Antonio Spurs", "Spurs", "SA"), side("Atlanta Hawks", "Hawks", "ATL"), "7:30 PM CDT", "FanDuel SN SW"))
        cb["live"].insert(0, game("m-boys", "nfl", iso(12, 0), "in", side("New York Giants", "Giants", "NYG", "14"), side("Dallas Cowboys", "Cowboys", "DAL", "17"), "3rd 5:12", "FOX"))
    elif which == "B":
        sp["last"].insert(0, game("m-spurs", "nba", iso(12, 0), "post", side("San Antonio Spurs", "Spurs", "SA", "112", True), side("Atlanta Hawks", "Hawks", "ATL", "104", False), "Final"))
    return d

BANNER = """() => { const b = document.querySelector('#gameday'); return { shown: !b.hidden && b.getBoundingClientRect().height > 0, kick: b.querySelector('.gd-kick')?.textContent,
  imgs: b.querySelectorAll('img, svg, picture').length, top: b.getBoundingClientRect().top <= document.querySelector('#sports .sec-head').getBoundingClientRect().top,
  rows: [...b.querySelectorAll('.gd-game')].map((r) => ({ lg: r.dataset.lg, text: r.innerText.replace(/\\s+/g, ' ').trim(), live: !!r.querySelector('.gd-live'), fin: !!r.querySelector('.gd-final'), h: r.getBoundingClientRect().height })) }; }"""

async def page_for(b, dev, theme, payload):
    ctx = await b.new_context(**dev, color_scheme=theme, timezone_id="America/Chicago", service_workers="block"); await ctx.add_init_script(QUIET)
    await ctx.add_init_script(INIT + f"localStorage.setItem('chisme-theme', '{theme}');")
    async def fake(route): await route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
    await ctx.route("**/api/sports*", fake)
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/#sports"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.sportsReady", timeout=120000)
    await pg.wait_for_timeout(700)
    return ctx, pg, errs

async def main():
    import urllib.request
    with urllib.request.urlopen(BASE + "/api/sports", timeout=120) as r: real = json.load(r)
    check(real["nfl"].get("cowboys") and real["nba"]["spurs"].get("team"), "the real /api/sports has the Spurs and Cowboys blocks the banner reads")
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        for theme in ("light", "dark"):
            print(f"\n== A: Spurs tonight + Cowboys live ({theme})")
            ctx, pg, errs = await page_for(b, dev, theme, scenario(real, "A"))
            s = await pg.evaluate(BANNER); print("   ", s["rows"])
            check(s["shown"] and s["top"] and s["kick"] and "It's game day!" in s["kick"], f"banner at the top of Sports: {s['kick']}")
            rows = {r["lg"]: r for r in s["rows"]}
            check(len(s["rows"]) == 2 and s["rows"][0]["lg"] == "cowboys", "both teams shown, the live game first")
            sp, cb = rows.get("nba", {}), rows.get("cowboys", {})
            check("Spurs vs Hawks" in sp.get("text", "") and "7:30 PM CDT" in sp["text"] and "Home" in sp["text"] and not sp["live"], f"Spurs: opponent, local start time, home ({sp.get('text')})")
            check("Cowboys @ Giants" in cb.get("text", "") and cb["live"] and "LIVE" in cb["text"] and "Cowboys 17, Giants 14" in cb["text"] and "3rd 5:12" in cb["text"], f"Cowboys: away, LIVE + score ({cb.get('text')})")
            check(s["imgs"] == 0, "no logos or images in the banner")
            check(all(r["h"] >= 44 for r in s["rows"]), "rows are 44+ px tap targets")
            bad = await pg.evaluate(SCAN, "#gameday")
            check(not bad, f"no yellow in the banner ({theme}) {bad[:3]}")
            if theme == "light":
                await pg.evaluate("window.scrollTo(0, document.querySelector('#sports').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 12)")
                try: await pg.wait_for_function("document.querySelector('#sync').hidden", timeout=12000)   # the "Updated" pill fades first
                except Exception: pass
                await pg.wait_for_timeout(400)
                top = await pg.evaluate("(() => { const s = document.querySelector('#sports').getBoundingClientRect(), c = document.querySelector('#sp-chips').getBoundingClientRect(); return { y: Math.max(0, document.querySelector('#tabs').getBoundingClientRect().bottom), b: c.bottom + 8, w: innerWidth }; })()")
                await pg.screenshot(path=os.path.join(OUT, "gameday-banner.png"), clip={"x": 0, "y": top["y"], "width": top["w"], "height": top["b"] - top["y"]})
            await pg.click("#gameday .gd-game[data-lg=cowboys]"); await pg.wait_for_timeout(400)
            st = await pg.evaluate("({ lg: __chisme.spLg, body: document.querySelector('#sports-body').dataset.lg, pressed: document.querySelector('#sp-chips .chip[aria-pressed=true]').dataset.lg })")
            check(st == {"lg": "cowboys", "body": "cowboys", "pressed": "cowboys"}, f"tapping the Cowboys row opens the Cowboys chip ({st})")
            await pg.click("#gameday .gd-game[data-lg=nba]"); await pg.wait_for_timeout(400)
            check(await pg.evaluate("__chisme.spLg") == "nba", "tapping the Spurs row opens the Spurs chip")
            check(await pg.evaluate("!document.querySelector('#gameday').hidden"), "the banner stays while you switch chips")
            check(not errs, f"no page errors ({errs[:2]})"); await ctx.close()
        print("\n== B: the Spurs game is final")
        ctx, pg, errs = await page_for(b, dev, "light", scenario(real, "B"))
        s = await pg.evaluate(BANNER); print("   ", s["rows"])
        r = s["rows"][0] if s["rows"] else {}
        check(s["shown"] and len(s["rows"]) == 1 and r.get("fin") and "FINAL" in r["text"] and "Spurs 112, Hawks 104" in r["text"] and not r["live"], f"final score ({r.get('text')})")
        check(not await pg.evaluate(SCAN, "#gameday"), "no yellow (final)")
        check(not errs, f"no page errors ({errs[:2]})"); await ctx.close()
        print("\n== C: no game today")
        ctx, pg, errs = await page_for(b, dev, "light", scenario(real, "C"))
        s = await pg.evaluate(BANNER)
        check(not s["shown"] and not s["rows"], "no banner on a day without a game")
        check(await pg.evaluate("!!document.querySelector('#sports-body .spurs-hero')"), "the Spurs page still renders under it")
        check(not errs, f"no page errors ({errs[:2]})"); await ctx.close()
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)

asyncio.run(main())
