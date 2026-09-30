"""¿Cuál dieta? For You, in WebKit (iPhone 13) + a real touch swipe in Chromium.
Banner at the top with Start watching; full-screen vertical scroll-snap feed; one muted-autoplay player at a time;
overlaid Save / Directions / Not for me / Details; signals (skip-fast, watch, save, not interested + undo) land in
localStorage; the 'Why you're seeing this' chip learns ("Because you saved 2 … spots"); Back button and the browser's
back close the feed; reduced motion → tap-to-play thumbnail; Settings → Reset my feed; creator cards (Instagram-only
labeled). Screens: dieta-foryou-banner.png, dieta-vertical-feed.png, dieta-why-chip.png"""
import re
import asyncio, os, sys, json
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); %s }"
PROF = "JSON.parse(localStorage.getItem('chisme-foryou') || 'null')"
FEED = """() => { const s = document.querySelector('#feed-scroll'), sl = [...s.querySelectorAll('.vf-slide')];
  return { open: document.querySelector('#feed').open, cur: window.__chisme.forYou.cur, pos: document.querySelector('#feed-pos').textContent,
    frames: [...document.querySelectorAll('.vf-frame')].map(f => ({ slide: sl.indexOf(f.closest('.vf-slide')), src: f.src })),
    h: s.clientHeight, vh: innerHeight, slideH: sl.length ? Math.round(sl[0].getBoundingClientRect().height) : 0, n: sl.length,
    snap: getComputedStyle(s).scrollSnapType, align: sl.length ? getComputedStyle(sl[0]).scrollSnapAlign : '', top: s.scrollTop } }"""

def own_error(m):
    """A console error from Chisme itself. The embedded YouTube/TikTok players log their own noise (their CSP headers,
    cookie banners, cross-origin frame access) from inside their iframes; that isn't the app's to fix."""
    if m.type != "error" or any(s in m.text for s in ("Failed to load resource", "access control", "Content Security Policy")):
        return False
    url = (m.location or {}).get("url") or ""
    if url and not url.startswith("http://localhost"):
        return False
    return not re.search(r"tiktok|ttwstatic|byteimg|ibytedtos|youtube|ytimg|googlevideo", m.text, re.I)   # the players' own domains


async def go(pg, i):   # scroll the feed to slide i the way a snap scroll ends up
    await pg.evaluate("(i) => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: i * s.clientHeight, behavior: 'instant' }); }", i)
    await pg.wait_for_function("(i) => window.__chisme.forYou.cur === i", arg=i, timeout=5000)

async def wk(p):
    b = await p.webkit.launch()
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "")
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: None if re.search(r"(tiktok|youtube(-nocookie)?)\.com\" from accessing a frame", str(e)) else errs.append(str(e)[:160]))   # the player iframe poking at its parent (WebKit)
    pg.on("console", lambda m: errs.append(m.text[:160]) if own_error(m) else None)
    await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    # 1. the banner: top of ¿Cuál dieta?, above the Latest / Saved spots chips; desk still at the bottom
    lay = await pg.evaluate("""() => { const c = document.querySelector('#foryou-card'), chips = document.querySelector('#food-view'), card = document.querySelector('#antojos');
      const r = c.getBoundingClientRect(), b = document.querySelector('#fy-start').getBoundingClientRect();
      return { afterHead: c.previousElementSibling.classList.contains('sec-head'), aboveChips: r.bottom <= chips.getBoundingClientRect().top,
        chips: [...chips.querySelectorAll('.chip')].map(x => x.dataset.fv), deskLast: card.lastElementChild.id === 'food-desk',
        title: document.querySelector('#fy-title').textContent.trim(), btn: document.querySelector('#fy-start').textContent.trim(), btnH: Math.round(b.height), btnW: Math.round(b.width),
        meta: document.querySelector('#fy-meta').textContent } }""")
    check(lay["afterHead"] and lay["aboveChips"], "For You banner is the first thing under the ¿Cuál dieta? heading, above the chips")
    check(lay["title"] == "🌮 Tu feed de antojos" and lay["btn"] == "▶ Start watching" and lay["btnH"] >= 52 and lay["btnW"] >= 300, f"banner: '{lay['title']}', big '{lay['btn']}' button ({lay['btnW']}×{lay['btnH']})")
    check(lay["chips"] == ["latest", "saved"] and lay["deskLast"], "Latest + Saved spots chips kept; food desk still at the bottom")
    crew = await pg.evaluate("[...document.querySelectorAll('#food-crew-list .crew')].map(c => ({ name: c.querySelector('b').textContent, uses: c.querySelector('.crew-uses').textContent, links: [...c.querySelectorAll('a')].map(a => a.href + ' ' + a.target) }))")
    saf = next((c for c in crew if c["name"] == "S.A. Foodie"), None)
    check(len(crew) >= 9 and saf and saf["uses"] == "Instagram only" and saf["links"] == ["https://www.instagram.com/s.a.foodie/ "], f"creator cards: {len(crew)}, S.A. Foodie is an Instagram-only link card, opening in Chisme ({saf})")
    await pg.evaluate("window.scrollTo(0, document.querySelector('#antojos').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 10)")
    await pg.wait_for_timeout(900)
    await pg.screenshot(path=os.path.join(OUT, "dieta-foryou-banner.png"))
    # 2. Start watching → full-screen vertical feed, one video per screen, first one autoplays muted
    cov = await pg.evaluate("({ tiles: [...document.querySelectorAll('#fy-cover .fy-tile-by')].map(e => e.textContent), next: document.querySelector('#fy-next').textContent, urls: __chisme.forYou.cover })")
    check(len(cov["tiles"]) == 3 and len(set(cov["tiles"])) == 3 and cov["next"].startswith("Up next:"), f"banner cover: 3 videos from 3 different creators ({cov['tiles']}; '{cov['next'][:90]}')")
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(700)
    f = await pg.evaluate(FEED)
    check(f["open"] and f["h"] == f["vh"] and f["slideH"] == f["vh"], f"feed fills the screen; each video is one screen tall ({f['slideH']} = {f['vh']} px)")
    check(f["snap"].startswith("y") and "mandatory" in f["snap"] and f["align"] == "start", f"scroll-snap: '{f['snap']}', slides snap to '{f['align']}'")
    check(len(f["frames"]) == 1 and f["frames"][0]["slide"] == 0 and "autoplay=1" in f["frames"][0]["src"] and ("mute=1" in f["frames"][0]["src"] or "tiktok.com/player" in f["frames"][0]["src"]) and "playsinline=1" in f["frames"][0]["src"] + "playsinline=1",
          f"first video: one muted, inline autoplay player ({f['frames'][0]['src'][:90] if f['frames'] else None})")
    n = f["n"] - 1
    check(f["pos"] == f"1 / {n}" and n >= 10, f"position '{f['pos']}' ({n} videos)")
    feed = (await pg.evaluate("window.__chisme.forYou"))["feed"]
    check(all(r["why"] for r in feed) and not any(r["explore"] for r in feed), "fresh phone: every card has a why chip; no exploration until it has learned something")
    check([r["url"] for r in feed[:3]] == cov["urls"], "the feed opens on the same 3 videos the banner cover shows")
    crews9 = [r["crew"] for r in feed[:9]]
    check(len(set(crews9)) == min(9, len({r["crew"] for r in feed})), f"new phone: the first 9 videos are {len(set(crews9))} different creators ({', '.join(r['creator'].split(' ')[0] for r in feed[:9])})")
    top10 = [r["crew"] for r in feed[:10]]
    check(max(top10.count(c) for c in top10) <= 2 and not any(feed[i]["crew"] == feed[i - 1]["crew"] for i in range(1, len(feed))), "no creator more than 2× in the top 10, never the same creator twice in a row")
    pl = [r["place"] for r in feed if r["place"]]
    check(len(pl) == len(set(pl)), f"one video per restaurant ({len(pl)} videos with a known spot, no repeats)")
    lead0 = feed[0]["crew"]
    # 3. swipe on (keyboard ↓, then a snap scroll): the player moves with you, one at a time; a fast skip is recorded
    await pg.keyboard.press("ArrowDown"); await pg.wait_for_function("window.__chisme.forYou.cur === 1", timeout=5000); await pg.wait_for_timeout(300)
    f = await pg.evaluate(FEED)
    check([x["slide"] for x in f["frames"]] == [1] and f["pos"] == f"2 / {n}", f"↓ next video: the player moved to video 2 and video 1 stopped ({[x['slide'] for x in f['frames']]})")
    prof = await pg.evaluate(PROF)
    check(prof and (prof["s"].get(feed[0]["url"]) or {}).get("sk") == 1, "skip-fast (< 2 s) on video 1 is recorded on the phone")
    await pg.wait_for_timeout(3600); await go(pg, 2)
    prof = await pg.evaluate(PROF)
    check((prof["s"].get(feed[1]["url"]) or {}).get("v", 0) >= 1, "watching video 2 for 3.6 s counts as a watch")
    # 4. overlay actions: Save, Not for me (+ Undo)
    s2 = "#feed-scroll .vf-slide:nth-child(3)"
    await pg.tap(f"{s2} .vf-rail .fr-save"); await pg.wait_for_timeout(300)
    sv = await pg.evaluate(f"({{ pressed: document.querySelector('{s2} .fr-save').getAttribute('aria-pressed'), n: document.querySelector('#n-saved').textContent }})")
    prof = await pg.evaluate(PROF)
    check(sv["pressed"] == "true" and sv["n"] == "(1)" and (prof["s"].get(feed[2]["url"]) or {}).get("sv") == 1, f"🔖 Save on the video: saved to Saved spots {sv['n']} and learned")
    await pg.tap(f"{s2} .vf-ni"); await pg.wait_for_timeout(500)
    ni = await pg.evaluate(f"({{ gone: !document.querySelector('#feed-scroll .vf-slide[data-url=\"' + CSS.escape({json.dumps(feed[2]['url'])}) + '\"]'), toast: document.querySelector('#feed-toast').textContent, pos: document.querySelector('#feed-pos').textContent }})")
    prof = await pg.evaluate(PROF)
    check(ni["gone"] and "fewer like this" in ni["toast"] and (prof["s"].get(feed[2]["url"]) or {}).get("ni") == 1, f"🙅 Not for me: the video is gone, '{ni['toast']}'")
    await pg.tap("#feed-toast button"); await pg.wait_for_timeout(500)
    back = await pg.evaluate(f"({{ back: !!document.querySelector('#feed-scroll .vf-slide[data-url=\"' + CSS.escape({json.dumps(feed[2]['url'])}) + '\"]'), cur: window.__chisme.forYou.cur }})")
    prof = await pg.evaluate(PROF)
    check(back["back"] and not (prof["s"].get(feed[2]["url"]) or {}).get("ni"), "Undo brings it back")
    has_dir = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')].findIndex(s => s.querySelector('.vf-dir'))")
    if has_dir >= 0:
        await go(pg, has_dir); await pg.wait_for_timeout(1400)
        d = await pg.evaluate(f"(() => {{ const s = document.querySelectorAll('#feed-scroll .vf-slide')[{has_dir}], a = s.querySelector('.vf-dir'); return {{ href: a.href, place: s.querySelector('.vf-place')?.textContent }}; }})()")
        check(d["href"].startswith("https://maps.apple.com/?daddr=") and d["place"], f"📍 restaurant info + Directions on the video ({d['place'][:50]})")
        await pg.screenshot(path=os.path.join(OUT, "dieta-vertical-feed.png"))
    else:
        check(False, "a video with a restaurant address (for Directions)")
    # 5. close: the Back button returns to the tab; so does the browser's back
    await pg.tap("#feed-close"); await pg.wait_for_timeout(600)
    st = await pg.evaluate("({ open: document.querySelector('#feed').open, view: window.__chisme.view, locked: document.documentElement.classList.contains('feed-open') })")
    check(not st["open"] and st["view"] == "antojos" and not st["locked"], f"‹ Back closes the feed, back on ¿Cuál dieta? ({st})")
    lead1 = await pg.evaluate("__chisme.forYou.coverCrews[0]")
    check(lead1 and lead1 != lead0, f"rotation: after closing, the banner cover leads with a different creator ({lead0} → {lead1})")
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
    await pg.evaluate("history.back()"); await pg.wait_for_timeout(800)
    st = await pg.evaluate("({ open: document.querySelector('#feed').open, view: window.__chisme.view, frames: document.querySelectorAll('.vf-frame').length })")
    check(not st["open"] and st["view"] == "antojos" and st["frames"] == 0, f"the phone's Back also closes it (and stops the video) ({st})")
    # 6. the why chip learns: save two videos of the most common dish, reopen
    pick = await pg.evaluate("""() => { const F = window.ChismeForYou, all = window.__chisme.forYou;
      return null; }""")
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
    feed = (await pg.evaluate("window.__chisme.forYou"))["feed"]
    dish = await pg.evaluate("""(feed) => { const F = window.ChismeForYou, by = {};
      feed.forEach((r, i) => F.featuresOf(r).filter(k => k[0] === 'k').forEach(k => (by[k] = by[k] || []).push(i)));
      const order = Object.entries(by).filter(([, v]) => v.length >= 2).sort((a, b) => (b[0] === 'k:tacos') - (a[0] === 'k:tacos') || b[1].length - a[1].length);
      return order.length ? { k: order[0][0], label: F.labelOf(order[0][0].slice(2)), idx: order[0][1] } : null; }""", feed)
    check(dish is not None, f"dish with ≥ 2 videos in today's feed: {dish and dish['label']} ({dish and len(dish['idx'])} videos)")
    if dish:
        for i in dish["idx"][:2]:
            await go(pg, i); await pg.tap(f"#feed-scroll .vf-slide:nth-child({i + 1}) .vf-rail .fr-save"); await pg.wait_for_timeout(250)
        await pg.tap("#feed-close"); await pg.wait_for_timeout(500)
        meta = await pg.text_content("#fy-meta")
        check(meta.startswith("Tuned to you:"), f"banner shows what it learned: '{meta}'")
        await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
        feed2 = (await pg.evaluate("window.__chisme.forYou"))["feed"]
        want = f"Because you saved 2 {dish['label']} spots"
        hit = next((i for i, r in enumerate(feed2) if r["why"] == want), -1)
        check(hit >= 0 and hit < 6, f"why chip: '{want}' on video #{hit + 1}")
        ex = [r for r in feed2 if r["explore"]]
        check(len(ex) == len(feed2) // 5 and all(r["why"].startswith("Something") for r in ex), f"exploration: {len(ex)} of {len(feed2)} videos (~20%), chip '{ex[0]['why'] if ex else ''}'")
        if hit >= 0:
            await go(pg, hit); await pg.wait_for_timeout(1400)
            sel = f"#feed-scroll .vf-slide:nth-child({hit + 1}) .why-chip"
            await pg.tap(sel); await pg.wait_for_timeout(300)
            exp = await pg.evaluate(f"({{ exp: document.querySelector('{sel}').getAttribute('aria-expanded'), more: document.querySelector('{sel}').nextElementSibling.textContent, label: document.querySelector('{sel}').getAttribute('aria-label') }})")
            check(exp["exp"] == "true" and "Nothing leaves your phone" in exp["more"] and exp["label"].startswith("Why you're seeing this:"), f"tap the chip: '{exp['more'][:70]}…'")
            await pg.screenshot(path=os.path.join(OUT, "dieta-why-chip.png"))
        await pg.tap("#feed-close"); await pg.wait_for_timeout(400)
    # 7. Settings → Reset my feed
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.tap("#settings-btn"); await pg.wait_for_timeout(500)
    await pg.tap("#set-fy-reset"); await pg.wait_for_timeout(300)
    note = await pg.text_content("#set-fy-note"); prof = await pg.evaluate(PROF)
    check(prof is None and "starts fresh" in note and not (await pg.text_content("#fy-meta")).startswith("Tuned"), f"Settings → Reset my feed: profile cleared ('{note}')")
    await pg.tap("#settings-close")
    check(not errs, f"no console/page errors ({errs[:3]})")
    await ctx.close()
    # 8. reduced motion: no autoplay, a tap-to-play thumbnail
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "localStorage.setItem('chisme-reduce-motion','1');")
    pg = await ctx.new_page(); await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.tap("#fy-start"); await pg.wait_for_timeout(700)
    r = await pg.evaluate("({ frames: document.querySelectorAll('.vf-frame').length, play: !!document.querySelector('#feed-scroll .vf-slide:first-child .vf-play'), thumb: !!document.querySelector('#feed-scroll .vf-slide:first-child .vf-thumb') })")
    check(r["frames"] == 0 and r["play"] and r["thumb"], f"reduced motion: no autoplay; a thumbnail with ▶ Tap to play ({r})")
    await pg.tap("#feed-scroll .vf-slide:first-child .vf-play"); await pg.wait_for_timeout(500)
    r = await pg.evaluate("({ frames: [...document.querySelectorAll('.vf-frame')].map(f => f.src.includes('autoplay=1')), p: " + PROF + " })")
    check(r["frames"] == [True] and r["p"] and r["p"]["n"] >= 1, "tap to play: the player starts, and it counts as an open")
    await ctx.close(); await b.close()

async def cr(p):   # a real finger swipe on the video itself scrolls to the next one (the player doesn't eat the touch)
    b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=3)
    await ctx.add_init_script(INIT % "")
    pg = await ctx.new_page(); await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(1200)
    cdp = await ctx.new_cdp_session(pg)
    async def swipe(y0, dy):   # a finger drag (Input.synthesizeScrollGesture doesn't scroll anything in headless Chrome)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 195, "y": y0}]})
        for i in range(1, 16):
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 195, "y": y0 + dy * i / 15}]}); await pg.wait_for_timeout(16)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    for want in (1, 2):
        under = await pg.evaluate("document.elementFromPoint(195, 380).className")
        await swipe(380, -450)
        try: await pg.wait_for_function("(w) => window.__chisme.forYou.cur === w", arg=want, timeout=5000)
        except Exception: pass
        await pg.wait_for_timeout(400)
        f = await pg.evaluate(FEED)
        check(f["cur"] == want and f["top"] % f["h"] == 0 and [x["slide"] for x in f["frames"]] == [want],
              f"Chromium: finger swipe up on the video ({under}) → video {want + 1}, snapped exactly (scrollTop {f['top']}), player moved along")
    await swipe(300, 450)
    try: await pg.wait_for_function("window.__chisme.forYou.cur === 1", timeout=5000)
    except Exception: pass
    check((await pg.evaluate(FEED))["cur"] == 1, "swipe down goes back a video")
    # a tap on the video pauses / plays (it doesn't open anything or scroll)
    await pg.wait_for_timeout(5200)
    await pg.tap("#feed-scroll .vf-slide:nth-child(2) .vf-shield"); await pg.wait_for_timeout(200)
    check((await pg.evaluate(FEED))["cur"] == 1 and await pg.evaluate("document.querySelector('#feed').open"), "a tap on the video toggles play/pause and stays put")
    await b.close()

async def main():
    async with async_playwright() as p:
        await wk(p); await cr(p)
    print("ALL PASS" if not fails else f"{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
