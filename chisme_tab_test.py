"""v49.12: the one "Chisme" tab (News + Sports + Events), permanent. Chromium Pixel 7 + WebKit iPhone 13, light + dark, 320 px.
  • the tab bar is Chisme · Weather · ¿Y la dieta? · Juegitos (no separate News / Sports / Events tabs), one row, fits at 320 px
  • Chisme opens on ✨ All: News, Sports and Events mixed, a 📰 / 🏀 / 🎉 tag on every card, never 3 of a kind in a row,
    at least two kinds on screen; each kind keeps its own order (sports newest first, events soonest first)
  • mixFeed itself (500 random lists): no 3 in a row, each list's order kept, stops when one kind would run 3
  • the chips All · News · Sports · Events: 44 px+, the picked one marked (aria-current), sticky under the tab bar while you scroll
  • the Chisme tab goes back to the chip picked last (this session); a new launch starts on All
  • deep links: #news #sports #events #chisme ?tab=sports ?tab=events land on their chip, the Chisme tab lit
  • Settings → Open Chisme to lists Chisme: All / News / Sports / Events
  • no page errors"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211/")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
NO_PIN = "try { localStorage.setItem('chisme-default-tab', 'chisme'); localStorage.setItem('chisme-location-setup', '1'); } catch (e) {}"   # Open Chisme to: Chisme (All)
STATE = """() => { const v = window.__chisme.view, t = document.querySelector('.tab[aria-current=page]'), c = document.querySelector('.view.active .mq-chip[aria-current=true]');
  return { view: v, tab: t ? t.dataset.view : null, chip: c ? c.dataset.go : null }; }"""
async def ready(pg, url=URL):
    await pg.goto(url); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
    await pg.wait_for_timeout(700)   # (a hash-only link, e.g. #news → #sports, slides over without a reload: let it land)
    return await pg.evaluate(STATE)
async def phone(b, name, dev, theme, w=None):
    print(f"— {name}")
    opts = dict(dev)
    if w: opts["viewport"] = {"width": w, "height": 740}
    ctx = await b.new_context(**opts)
    await ctx.add_init_script(QUIET); await ctx.add_init_script(NO_PIN + f"localStorage.setItem('chisme-theme', '{theme}');")
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: None if "access control checks" in str(e) else errs.append(str(e)[:160]))   # WebKit: a fetch cut off by the test navigating away
    s = await ready(pg)
    tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].filter(t => t.offsetParent).map(t => [t.dataset.view, t.textContent.trim(), Math.round(t.getBoundingClientRect().top)])")
    check([t[0] for t in tabs] == ["chisme", "weather", "antojos", "juegos"] and "Chisme" in tabs[0][1], f"4 tabs: Chisme · Weather · ¿Y la dieta? · Juegitos ({[t[1] for t in tabs]})")
    check(len({t[2] for t in tabs}) == 1, f"…in one row ({[t[2] for t in tabs]})")
    fit = await pg.evaluate("(() => { const i = document.querySelector('.tabs-inner'); return i.scrollWidth <= i.clientWidth + 1; })()")
    check(fit, "…and they fit (no sideways scrolling)")
    check(s == {"view": "chisme", "tab": "chisme", "chip": "chisme"}, f"opens on Chisme → ✨ All ({s})")
    await pg.wait_for_function("document.querySelectorAll('#mix-list .mix-item').length >= 8", timeout=60000)
    await pg.wait_for_timeout(2500)   # sports + events arrive
    mix = await pg.evaluate("""[...document.querySelectorAll('#mix-list .mix-item')].map(n => ({ cat: n.dataset.cat, tag: n.querySelector('.mix-tag').textContent.trim(),
      pub: (n.querySelector('.sn-meta, .meta') || {}).textContent || '', title: (n.querySelector('h3, h4') || {}).textContent || '' }))""")
    cats = [m["cat"] for m in mix]
    run3 = any(cats[i] == cats[i + 1] == cats[i + 2] for i in range(len(cats) - 2))
    check(len(mix) >= 12 and not run3, f"All: {len(mix)} cards, never 3 of a kind in a row ({''.join(c[0] for c in cats)})")
    check(len(set(cats[:10])) >= 2 and len(set(cats)) == 3, f"…News, Sports and Events all mixed in ({sorted(set(cats))})")
    check(all(m["tag"].lower().endswith(m["cat"]) for m in mix), "…every card has its category tag (📰 News / 🏀 Sports / 🎉 Events)")
    chips = await pg.evaluate("[...document.querySelectorAll('#view-chisme .mq-chip')].map(c => { const r = c.getBoundingClientRect(); return [c.dataset.go, c.textContent.trim(), Math.round(r.height), Math.round(r.width), r.right <= innerWidth + 1 && c.scrollWidth <= c.clientWidth + 1]; })")
    check([c[0] for c in chips] == ["chisme", "news", "sports", "events"] and all(c[2] >= 44 and c[3] >= 44 and c[4] for c in chips),
          f"chips All · News · Sports · Events, 44 px+, on screen, labels not cut off ({[(c[1], c[2], c[3]) for c in chips]})")
    await pg.evaluate("window.scrollTo(0, 2200)"); await pg.wait_for_timeout(500)
    st = await pg.evaluate("(() => { const r = document.querySelector('#view-chisme .mq-chips').getBoundingClientRect(), t = document.querySelector('#tabs').getBoundingClientRect(); return [Math.round(r.top), Math.round(t.bottom)]; })()")
    check(abs(st[0] - st[1]) <= 2, f"…sticky: still right under the tab bar after scrolling ({st})")
    await pg.evaluate("window.scrollTo(0, 0)")
    for cat in ("sports", "events", "news", "chisme"):
        await pg.click(f".view.active .mq-chip[data-go='{cat}']"); await pg.wait_for_timeout(700)
        s = await pg.evaluate(STATE)
        check(s == {"view": cat, "tab": "chisme", "chip": cat}, f"chip {cat}: its section, the chip marked, the Chisme tab lit ({s})")
    await pg.click(".view.active .mq-chip[data-go='sports']"); await pg.wait_for_timeout(700)
    await pg.click("#tabs [data-view='weather']"); await pg.wait_for_timeout(700)
    await pg.click("#tabs [data-view='chisme']"); await pg.wait_for_timeout(700)
    s = await pg.evaluate(STATE)
    check(s["view"] == "sports", f"the Chisme tab goes back to the chip picked last, this session (sports → {s['view']})")
    pg2 = await ctx.new_page(); s2 = await ready(pg2)   # a new launch (a new tab = a new session)
    check(s2["view"] == "chisme" and s2["chip"] == "chisme", f"…a new launch starts on All ({s2['view']})")
    await pg2.close()
    for url, want in (("#news", "news"), ("#sports", "sports"), ("#events", "events"), ("#chisme", "chisme"), ("?tab=sports", "sports"), ("?tab=events", "events"), ("#spurs", "sports")):
        s = await ready(pg, URL + url)
        check(s == {"view": want, "tab": "chisme", "chip": want}, f"deep link {url} → {want} chip ({s})")
    await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready")
    await pg.evaluate("document.querySelector('#settings-btn').click()"); await pg.wait_for_timeout(300)
    opts = await pg.evaluate("[...document.querySelectorAll('#settings input[name=deftab]')].map(i => i.value + ':' + i.parentElement.textContent.trim())")
    check([o.split(":")[0] for o in opts] == ["random", "chisme", "news", "sports", "events", "weather", "antojos", "juegos"] and "Chisme: All" in opts[1],
          f"Settings → Open Chisme to: Surprise me, Chisme: All / News / Sports / Events, Weather, ¿Y la dieta?, Juegitos")
    check(not errs, f"no page errors ({errs[:2]})")
    await ctx.close()

async def unit(b):
    print("— mixFeed")
    ctx = await b.new_context(); await ctx.add_init_script(QUIET); pg = await ctx.new_page(); await ready(pg)
    r = await pg.evaluate("""() => { const { mixFeed, mulberry } = window.__chisme, bad = []; let stops = 0;
      for (let t = 0; t < 500; t++) {
        const rnd = mulberry(t + 1), mk = (c) => Array.from({ length: Math.floor(rnd() * 30) }, (_, i) => c + i);
        const L = { news: mk('n'), sports: mk('s'), events: mk('e') }, out = mixFeed(L, mulberry(t * 7 + 3), 60);
        for (let i = 2; i < out.length; i++) if (out[i].cat === out[i - 1].cat && out[i].cat === out[i - 2].cat) bad.push(['run', t]);
        for (const c of ['news', 'sports', 'events']) { const got = out.filter(x => x.cat === c).map(x => x.item), want = L[c].slice(0, got.length); if (got.join() !== want.join()) bad.push(['order', t, c]); }
        const total = L.news.length + L.sports.length + L.events.length;
        if (out.length < Math.min(60, total)) { stops++; const left = Object.keys(L).filter(c => out.filter(x => x.cat === c).length < L[c].length); if (left.length !== 1) bad.push(['stop', t, left]); }
      }
      return { bad: bad.slice(0, 5), stops }; }""")
    check(not r["bad"], f"500 random mixes: never 3 in a row, each list's order kept, stops only when one kind is left ({r})")
    await ctx.close()

async def main():
    async with async_playwright() as p:
        c = await p.chromium.launch()
        await unit(c)
        await phone(c, "Chromium · Pixel 7 · light", p.devices["Pixel 7"], "light")
        await phone(c, "Chromium · 320 px · dark", p.devices["Pixel 7"], "dark", w=320)
        await c.close()
        wk = await p.webkit.launch()
        await phone(wk, "WebKit · iPhone 13 · dark", p.devices["iPhone 13"], "dark")
        await wk.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
