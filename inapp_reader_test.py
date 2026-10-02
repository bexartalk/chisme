"""In-app reader (v27), WebKit iPhone 13: every outside link stays inside Chisme.

- Audit: across News, Sports, ¿Cuál dieta?, Weather and Events, no link opens a new tab/browser except the Cash App
  donate button (and the small "Open original" / "Open in Maps" links at the bottom of the sheets).
- News story → reader sheet: framed where the site allows it (checked server-side from X-Frame-Options /
  CSP frame-ancestors), else a headline card (headline, source, date, the feed's summary, image) with attribution
  and one small secondary "Open original" link, last in the sheet. No article text is copied.
- Also reported by / More coverage / Gamecast / creator profile (Instagram) / event page → reader; event map and
  food Directions (Apple Maps) → the in-app OpenStreetMap map sheet with "Open in Maps".
- /api/reader refuses private addresses, odd ports and non-web links.
Screenshots: inapp-reader-framed.png, inapp-reader-card.png (+ inapp-map-sheet.png)."""
import asyncio, io, json, os, urllib.parse, urllib.request
from PIL import Image
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
URL = BASE + "/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

def api(url):
    try:
        with urllib.request.urlopen(BASE + "/api/reader?url=" + urllib.parse.quote(url, safe=""), timeout=40) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

AUDIT = """() => [...document.querySelectorAll('a[href]')].filter(a => { try { return new URL(a.href).origin !== location.origin && /^https?:/.test(a.href); } catch { return false; } })
  .map(a => ({ href: a.href, target: a.target, cls: a.className, inSheet: !!a.closest('#player, #mapsheet') }))"""
SHEET = """() => { const p = document.querySelector('#player'), m = document.querySelector('#player-media'), o = document.querySelector('#player-orig a');
  const body = [...document.querySelectorAll('#player .player-body > *')].filter(n => !n.hidden && getComputedStyle(n).display !== 'none');
  return { open: p.open, kind: document.querySelector('#player-kind').textContent, title: document.querySelector('#player-title').textContent,
    by: document.querySelector('#player-by').textContent, sum: document.querySelector('#player-sum').hidden ? '' : document.querySelector('#player-sum').textContent,
    note: document.querySelector('#player-note').textContent, frame: m.querySelector('iframe') ? m.querySelector('iframe').getAttribute('sandbox') : null,
    frameSrc: m.querySelector('iframe') ? m.querySelector('iframe').src : null, img: !!m.querySelector('img'), checking: m.classList.contains('checking'),
    orig: o ? { text: o.textContent, href: o.href, target: o.target, size: parseFloat(getComputedStyle(o).fontSize) } : null,
    lastIsOrig: body.length ? body[body.length - 1].id === 'player-orig' : false,
    acts: [...document.querySelectorAll('#player-actions a')].map(a => [a.textContent, a.target]) }; }"""

async def tap_and_read(pg, selector_js, label):
    href = await pg.evaluate(f"() => {{ const a = {selector_js}; if (!a) return null; a.scrollIntoView({{block: 'center'}}); a.click(); return a.href; }}")
    if not href:
        check(False, f"{label}: found a link to tap"); return None, None
    await pg.wait_for_function("document.querySelector('#player').open && !document.querySelector('#player-media').classList.contains('checking')", timeout=45000)
    await pg.wait_for_timeout(600)
    return href, await pg.evaluate(SHEET)

async def close_sheet(pg):
    await pg.evaluate("document.querySelector('#player').close()"); await pg.wait_for_timeout(300)

async def main():
    global fails
    print("== /api/reader safety + verdicts")
    for bad in ["http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "https://localhost/", "http://10.0.0.1/", "file:///etc/passwd",
                "http://[::1]/", "https://example.com:8443/", "ftp://example.com/"]:
        st, j = api(bad)
        check(st == 400, f"refuses {bad} ({st} {j.get('error')})")
    st, j = api("https://www.ksat.com/")
    check(st == 200 and j.get("frame") is False and j.get("why") in ("x-frame-options", "frame-ancestors"), f"KSAT: not framed ({j.get('why')})")
    check(bool(j.get("title")) and len(j.get("description") or "") <= 300, "card data: title + short site description (≤300 chars)")
    st, j = api("https://en.wikipedia.org/wiki/San_Antonio")
    check(st == 200 and j.get("frame") is True, f"Wikipedia: framed ({j.get('why')})")
    st, j = api("https://www.instagram.com/s.a.foodie/")
    check(j.get("frame") is False, "Instagram: never framed")

    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT)
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        popups = []; ctx.on("page", lambda n: popups.append(n.url))
        await pg.goto(URL); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)

        print("\n== audit: outside links on every tab")
        links = []
        for v in ["news", "sports", "weather", "antojos", "juegos", "events"]:
            await pg.click(f"#tabs .tab[data-view={v}]"); await pg.wait_for_timeout(4000 if v in ("sports", "antojos", "events") else 1500)
            links += await pg.evaluate(AUDIT)
        uniq = {l["href"]: l for l in links}
        blank = [l for l in uniq.values() if l["target"] == "_blank" and "donate-btn" not in l["cls"] and not l["inSheet"]]
        donate = [l for l in uniq.values() if "donate-btn" in l["cls"]]
        print(f"  {len(uniq)} distinct outside links on the page")
        check(not blank, f"no outside link opens a new tab/browser except the donate button ({[b['href'][:60] for b in blank[:3]]})")
        check(donate and all(d["target"] == "_blank" and d["href"].startswith(("https://cash.app/", "https://buymeacoffee.com/")) for d in donate)
              and {d["href"] for d in donate} >= {"https://cash.app/$Slurmkaos", "https://buymeacoffee.com/Chismoso"}, "the donate buttons (Cash App, Buy Me a Coffee) still open their sites")

        # the global handler: only the donate button (and the sheets' "Open original") are left alone
        res = await pg.evaluate("""() => { const out = {}; const rec = (e) => { const a = e.target.closest('a'); if (a) { out[a.className || a.href] = e.defaultPrevented; e.preventDefault(); } };
            window.addEventListener('click', rec); const d = document.querySelector('.donate-btn'); d.click(); window.removeEventListener('click', rec); return out; }""")
        check(list(res.values()) == [False], f"donate tap isn't intercepted ({res})")

        print("\n== news → reader")
        await pg.click("#tabs .tab[data-view=news]"); await pg.wait_for_timeout(800)
        hosts = await pg.evaluate("() => [...document.querySelectorAll('.story .dig-row .btnlink.primary')].map(a => a.href)")
        verdict = {}
        for h in hosts[:40]:
            host = urllib.parse.urlsplit(h).netloc
            if host not in verdict and host != "news.google.com": verdict[host] = api(h)[1].get("frame")
        framed_host = next((h for h, f in verdict.items() if f), None)
        card_host = next((h for h, f in verdict.items() if f is False), None)
        print(f"  frame verdicts: {verdict}")
        if card_host:
            href, s = await tap_and_read(pg, f"[...document.querySelectorAll('.story .dig-row .btnlink.primary')].find(a => new URL(a.href).host === '{card_host}')", "card story")
            check(s["open"] and not s["frame"] and s["kind"].endswith("Article"), f"{card_host}: headline card, not framed ({s['kind']})")
            check(bool(s["title"]) and bool(s["by"]) and s["by"].split(" · ")[0].strip() != "", f"card: headline + source/date ({s['by'][:50]})")
            check(s["note"].startswith("From ") and "never the article itself" in s["note"], f"attribution + no copied article text ({s['note'][:80]})")
            check(s["orig"] and s["orig"]["text"].startswith("Open original on") and s["orig"]["target"] == "_blank" and s["lastIsOrig"] and s["orig"]["size"] < 19,
                  f"one small secondary 'Open original' link, last in the sheet ({s['orig']})")
            check(not any(t == "_blank" for _, t in s["acts"]), f"no primary outbound buttons in the sheet ({s['acts']})")
            check(len(s["sum"]) <= 600, f"summary is the feed's short summary ({len(s['sum'])} chars)")
            top = await pg.screenshot()
            await pg.evaluate("() => { const d = document.querySelector('#player'); d.scrollTop = d.scrollHeight; }"); await pg.wait_for_timeout(300)
            bottom = await pg.screenshot()
            a, c = Image.open(io.BytesIO(top)), Image.open(io.BytesIO(bottom))   # top of the card | bottom (attribution + Open original)
            both = Image.new("RGB", (a.width * 2 + 24, a.height), "white"); both.paste(a, (0, 0)); both.paste(c, (a.width + 24, 0))
            both.save(os.path.join(OUT, "inapp-reader-card.png"))
            await close_sheet(pg)
        else:
            check(False, "a news story from a site that refuses framing (for the card)")
        # framed: a story from a site that allows it, else an injected link to one (the global handler is what's tested)
        if framed_host:
            sel = f"[...document.querySelectorAll('.story .dig-row .btnlink.primary')].find(a => new URL(a.href).host === '{framed_host}')"
        else:
            await pg.evaluate("() => { const a = document.createElement('a'); a.href = 'https://www.sanantonioreport.org/'; a.id = 'probe'; a.textContent = 'San Antonio Report'; document.querySelector('#near-list').prepend(a); }")
            sel = "document.querySelector('#probe')"
        n_err = len(errs)
        href, s = await tap_and_read(pg, sel, "framed story")
        framed_netloc = urllib.parse.urlsplit(href).netloc.removeprefix("www.")
        check(s["frame"] is not None and "allow-top-navigation" not in s["frame"], f"{urllib.parse.urlsplit(href).netloc}: framed inside Chisme, sandboxed ({s['frame']})")
        check("inside Chisme" in s["note"] and s["orig"] and s["lastIsOrig"], f"framed: credited + small 'Open original' last ({s['note'][:70]})")
        await pg.wait_for_timeout(4000)
        await pg.screenshot(path=os.path.join(OUT, "inapp-reader-framed.png"))
        await close_sheet(pg)
        # the framed site's own scripts (consent managers, analytics, cross-frame probes) throw inside its sandboxed iframe
        # and WebKit reports those as page errors too; while it's open, only errors from Chisme's own scripts count.
        errs[n_err:] = [e for e in errs[n_err:] if "/static/" in e and "localhost" in e]   # only Chisme's own scripts count here
        rel = await pg.evaluate("!!document.querySelector('.story .related a')")
        if rel:
            _, s = await tap_and_read(pg, "document.querySelector('.story .related a')", "also reported by")
            check(s["open"] and s["orig"], f"'Also reported by' → reader ({s['by'][:40]})"); await close_sheet(pg)
        _, s = await tap_and_read(pg, "document.querySelector('.story .dig-row .btnlink:not(.primary)')", "more coverage")
        check(s["open"] and s["title"].startswith("More coverage"), f"'More coverage' → reader ({s['title'][:50]})"); await close_sheet(pg)

        print("\n== sports, creators, events, food")
        await pg.click("#tabs .tab[data-view=sports]"); await pg.wait_for_timeout(3000)
        if await pg.evaluate("!!document.querySelector('.game .glink')"):
            _, s = await tap_and_read(pg, "document.querySelector('.game .glink')", "gamecast")
            check(s["open"] and "Game" in s["kind"] and " at " in s["title"], f"Gamecast → in-app game card ({s['title']})"); await close_sheet(pg)
        else: print("  note: no games with a Gamecast link today")
        await pg.click("#tabs .tab[data-view=antojos]"); await pg.wait_for_timeout(4000)
        if await pg.evaluate("!!document.querySelector('#food-crew-list a[href*=instagram]')"):
            _, s = await tap_and_read(pg, "document.querySelector('#food-crew-list a[href*=instagram]')", "instagram")
            check(s["open"] and "Profile" in s["kind"] and "Instagram" in s["title"] and s["orig"] and "instagram.com" in s["orig"]["href"],
                  f"creator Instagram → in-app profile card ({s['title']})"); await close_sheet(pg)
        await pg.click("#tabs .tab[data-view=events]"); await pg.wait_for_timeout(4000)
        if await pg.evaluate("!!document.querySelector('.ev h3 a')"):
            _, s = await tap_and_read(pg, "document.querySelector('.ev h3 a')", "event")
            check(s["open"] and s["orig"], f"event page → reader ({s['kind']}, {s['by'][:50]})"); await close_sheet(pg)
        mm = await pg.evaluate("() => { const a = document.querySelector('.ev .minimap') || [...document.querySelectorAll('.ev-links a')].find(a => /Map/.test(a.textContent)); if (!a) return null; a.scrollIntoView({block:'center'}); a.click(); return a.href; }")
        if mm:
            await pg.wait_for_function("document.querySelector('#mapsheet').open", timeout=15000)
            await pg.wait_for_function("document.querySelector('#mapsheet .ms-pin') || document.querySelector('#ms-status').textContent.length > 0", timeout=30000)
            m = await pg.evaluate("() => ({ pin: !!document.querySelector('#mapsheet .ms-pin'), title: document.querySelector('#ms-title').textContent, orig: (a => a && [a.textContent, a.href, a.target])(document.querySelector('#ms-orig a')), tiles: document.querySelectorAll('#ms-map .leaflet-tile').length })")
            check(m["pin"] and m["tiles"] > 0 and m["orig"] and m["orig"][0].startswith("Open in Maps") and m["orig"][1].startswith("https://maps.apple.com/"),
                  f"event map → in-app OSM map sheet with a pin + small 'Open in Maps' ({m['title']})")
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=os.path.join(OUT, "inapp-map-sheet.png"))
            await pg.evaluate("document.querySelector('#mapsheet').close()")
        check(not popups, f"nothing opened a new tab or browser ({popups[:2]})")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
