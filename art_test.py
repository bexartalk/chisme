"""Phone (390x844): Texas art/landmark photos between news stories (one after every 4 stories, rotating),
captions + attribution from art.json, swipe still works on top of a photo, photos cached offline.
Usage: ./venv/bin/python art_test.py [url]"""
import asyncio, json, sys, tempfile
from pathlib import Path
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"
ART = {a["n"]: a for a in json.load(open(Path(__file__).parent / "static/art/art.json"))["items"]}
LAYOUT_JS = """() => { const res = {};
  for (const id of ['near-list', 'city-list', 'sa-list']) {
    const kids = [...document.getElementById(id).children].filter(k => k.id !== 'donate-mid');   // the once-per-launch donate card (v32) isn't part of the photo rhythm
    res[id] = kids.map(k => k.matches('figure.art') ? 'A' + k.dataset.art : k.matches('article.story') ? 's' : '?').join(' ');
  }
  return res; }"""
CARD_JS = """(n) => { const f = document.querySelector(`figure.art[data-art="${n}"]`); if (!f) return null;
  const img = f.querySelector('img'); const cs = getComputedStyle(f.querySelector('.art-cap'));
  return { alt: img.alt, cap: f.querySelector('.art-cap').textContent, artist: f.querySelector('.art-artist')?.textContent || null,
           credit: f.querySelector('.art-credit').innerText, links: [...f.querySelectorAll('.art-credit a')].map(a => a.href),
           capPx: cs.fontSize, capWeight: cs.fontWeight, loaded: img.complete && img.naturalWidth > 0, natural: [img.naturalWidth, img.naturalHeight],
           shown: [Math.round(img.getBoundingClientRect().width), Math.round(img.getBoundingClientRect().height)], draggable: img.getAttribute('draggable') }; }"""


async def touch(cdp, pts, steps=14):
    (x0, y0), (x1, y1) = pts
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / steps, "y": y0 + (y1 - y0) * k / steps}]})
        await asyncio.sleep(0.016)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


async def main():
    rep, logs = {}, []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                  timezone_id="America/Chicago", geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        page = await ctx.new_page()
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        page.on("console", lambda m: logs.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.evaluate("localStorage.setItem('chisme-art-next', '0')")
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("() => window.__chisme && window.__chisme.ready && document.querySelectorAll('#near-list figure.art').length", timeout=120000)
        await page.wait_for_timeout(1500)
        rep["layout"] = await page.evaluate(LAYOUT_JS)
        # every art card sits after exactly 4 stories and never at the end of a list
        ok = True
        for lst in rep["layout"].values():
            toks = lst.split()
            for i, t in enumerate(toks):
                if t.startswith("A"):
                    ok &= toks[max(0, i - 4):i] == ["s"] * 4 and i < len(toks) - 1 and (i + 1 >= len(toks) or toks[i + 1] == "s")
        rep["spacing_ok"] = ok
        seq = [int(t[1:]) for l in rep["layout"].values() for t in l.split() if t.startswith("A")]
        rep["art_sequence"] = seq
        rep["all_13_shown"] = sorted(set(seq)) == list(range(1, 14))
        # captions/credits must match art.json
        cards, mism = {}, []
        for n in sorted(set(seq)):
            await page.evaluate(f"document.querySelector('figure.art[data-art=\"{n}\"]').scrollIntoView({{block: 'center', behavior: 'instant'}})")
            await page.wait_for_timeout(350)
            c = await page.evaluate(CARD_JS, n)
            a = ART[n]
            want_links = ([a["license_url"]] if a["license_url"] else []) + [a["source_url"]]
            norm = lambda u: u.rstrip("/")
            if c["alt"] != a["alt"] or f'{a["subject"]} · {a["city"]}' != c["cap"] or (a["artist"] or None) != c["artist"] \
                    or [norm(x) for x in c["links"]] != [norm(x) for x in want_links] or a["author"] not in c["credit"] or a["license"] not in c["credit"]:
                mism.append(n)
            cards[n] = c
        rep["cards_loaded"] = sum(c["loaded"] for c in cards.values())
        rep["card_mismatches"] = mism
        rep["card_samples"] = {n: cards[n] for n in (1, 8, 10, 11) if n in cards}
        # screenshot: story / art / story
        n0 = seq[0]
        await page.evaluate(f"""() => {{ const f = document.querySelector('figure.art[data-art="{n0}"]');
            window.scrollTo(0, f.getBoundingClientRect().top + scrollY - 260); }}""")
        await page.wait_for_timeout(900)
        await page.screenshot(path=str(OUT / "art-between-stories.png"))
        mural = next(n for n in seq if ART[n]["mural"])
        rep["mural_shot"] = mural
        await page.evaluate(f"""() => {{ const f = document.querySelector('figure.art[data-art="{mural}"]');
            window.scrollTo(0, f.getBoundingClientRect().top + scrollY - 110); }}""")
        await page.wait_for_timeout(900)
        await page.screenshot(path=str(OUT / "art-mural.png"))
        # gestures on top of a photo: vertical drag scrolls, horizontal swipe switches to Sports and back
        cdp = await ctx.new_cdp_session(page)
        bb = await page.locator(f'figure.art[data-art="{mural}"] img').first.bounding_box()
        cy = min(bb["y"] + bb["height"] / 2, 700)
        y0 = await page.evaluate("scrollY")
        await touch(cdp, [(200, cy), (200, cy - 300)])
        await page.wait_for_timeout(700)
        rep["vertical_on_photo"] = {"scrolled": await page.evaluate("scrollY") - y0, "view": await page.evaluate("window.__chisme.view")}
        bb = await page.locator(f'figure.art[data-art="{mural}"] img').first.bounding_box()
        cy = max(150, min(bb["y"] + bb["height"] / 2, 700))
        await touch(cdp, [(340, cy), (60, cy)])
        await page.wait_for_timeout(900)
        v1 = await page.evaluate("window.__chisme.view")
        await touch(cdp, [(60, 400), (340, 400)])
        await page.wait_for_timeout(900)
        rep["swipe_on_photo"] = {"after_left_swipe": v1, "after_right_swipe": await page.evaluate("window.__chisme.view")}
        # rotation: next load starts where this one stopped
        rep["cursor_saved"] = await page.evaluate("localStorage.getItem('chisme-art-next')")
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("() => window.__chisme && window.__chisme.ready && document.querySelectorAll('#near-list figure.art').length", timeout=120000)
        rep["first_art_after_reload"] = await page.evaluate("document.querySelector('#near-list figure.art').dataset.art")
        await b.close()
    rep["console"] = logs
    # offline, clean profile: photos (even ones not yet viewed) come from the service worker precache
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path="/usr/bin/google-chrome", args=["--no-sandbox"],
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, timezone_id="America/Chicago",
            geolocation={"latitude": 29.35, "longitude": -98.56}, permissions=["geolocation"])
        pg = ctx.pages[0]
        await pg.goto(URL, wait_until="domcontentloaded")
        await pg.wait_for_function("() => navigator.serviceWorker.controller || navigator.serviceWorker.ready", timeout=60000)
        await pg.evaluate("navigator.serviceWorker.ready")
        await pg.reload(wait_until="networkidle")
        await pg.wait_for_function("() => window.__chisme.ready && window.__chisme.eventsReady && window.__chisme.foodReady", timeout=120000)
        await pg.wait_for_timeout(1500)
        rep["precached"] = await pg.evaluate("""caches.keys().then(async ks => { let n = 0; for (const k of ks) { const c = await caches.open(k);
            n += (await c.keys()).filter(r => /\\/static\\/art\\//.test(r.url)).length; } return n; })""")
        await ctx.set_offline(True)
        failed, errs = [], []
        pg.on("requestfailed", lambda r: failed.append(r.url[:100]))
        pg.on("response", lambda r: failed.append(f"{r.status} {r.url[:100]}") if r.status >= 400 else None)
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        await pg.reload(wait_until="domcontentloaded")
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
        await pg.wait_for_timeout(1000)
        loaded = []
        for f in await pg.query_selector_all("figure.art"):
            await f.scroll_into_view_if_needed()
            await pg.wait_for_timeout(250)
            loaded.append(await f.evaluate("f => { const i = f.querySelector('img'); return i.complete && i.naturalWidth > 0; }"))
        rep["offline"] = {"onLine": await pg.evaluate("navigator.onLine"), "art_cards": len(loaded), "art_loaded": sum(loaded),
                          "failed_requests": failed, "console_errors": errs}
        await ctx.close()
    print(json.dumps(rep, indent=1, ensure_ascii=False))

asyncio.run(main())
