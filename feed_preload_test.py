"""v47: the Bigger the Pansa, Better the Chansa video feed preloads, so a swipe lands on a video that plays at once.

Chromium (390×844, phone): 4 YouTube players are made and ready before ▶ Start (one on screen, the next 2 videos loaded
muted and held on their first frame, the one behind kept paused for a swipe back); the thumbnails of the next 6 slides are
fetched and decoded; each swipe plays the next video within 400 ms (median) with sound on; the donate slide every 7 doesn't
break it (the 2 videos after it are warm while you look at it, and the swipe past it plays at once); 13 swipes in there are
still exactly 4 player iframes and none of them more than 2 videos from the one on screen; swipe back: the one behind plays.
Slow connection (effectiveType 3g): 3 players, only 1 video ahead, thumbnails 2 ahead. Data saver: no autoplay, no players.
WebKit (iPhone 13): 3 players (memory), all made before Start so that one tap unlocks sound in every one (v41 fix kept):
the next 2 videos warm, 5 swipes each playing with sound."""
from popup_quiet import QUIET   # v49: the notifications card + Settings tip have their own tests
import asyncio, json, os, statistics, sys, time
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
URL = os.environ.get("URL", "http://localhost:8211/")
INIT = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));"
NET = """(() => { const c = { effectiveType: '%s', saveData: %s, downlink: 1, rtt: 300, addEventListener() {}, removeEventListener() {} };
  try { Object.defineProperty(Navigator.prototype, 'connection', { configurable: true, get: () => c }); } catch (e) {} })()"""
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
ST = """() => { const f = window.__chisme.forYou, P = f.player, sl = [...document.querySelectorAll('#feed-scroll .vf-slide')];
  const vidIdx = sl.map((s, i) => s.dataset.url ? i : -1).filter(i => i >= 0), vpos = (i) => vidIdx.indexOf(i);
  return { cur: f.cur, pool: P.pool, ahead: P.ahead, slow: P.slow, ios: P.ios, n: P.players.length, frames: document.querySelectorAll('iframe.vf-yt').length,
    players: P.players.map(p => ({ slide: p.slide, warm: p.warm, st: p.st, ready: p.ready, unlocked: p.unlocked, muted: p.muted })),
    warmReady: sl.map((s, i) => s.dataset.warm === 'ready' ? i : -1).filter(i => i >= 0), warms: P.warms,
    far: P.players.filter(p => p.slide >= 0 && Math.abs(vpos(p.slide) - vpos(f.cur)) > 2).map(p => p.slide),
    tt: [...document.querySelectorAll('#feed-scroll .vf-slide iframe')].map(x => sl.indexOf(x.closest('.vf-slide'))),
    kinds: sl.map(s => s.classList.contains('vf-donate') ? 'D' : s.classList.contains('vf-end') ? 'E' : s.dataset.kind === 'tt' ? 't' : 'y').join(''),
    thumbs: sl.map((s, i) => { const t = s.querySelector('img.vf-thumb'); return t && t.loading === 'eager' && t.complete && t.naturalWidth > 0 ? i : -1; }).filter(i => i >= 0) }; }"""
PLAYING = """(i) => { const f = window.__chisme.forYou, sl = document.querySelectorAll('#feed-scroll .vf-slide'), s = sl[i]; if (f.cur !== i || !s) return false;
  if (s.dataset.kind === 'yt') { const p = f.player.players.find(p => p.slide === i && !p.warm); return !!p && p.st === 1 && !s.classList.contains('vf-loading'); }
  return s._st === 1; }"""
POSTER = """(i) => { const s = document.querySelectorAll('#feed-scroll .vf-slide')[i], t = s && s.querySelector('img.vf-thumb'); return !!t && t.complete && t.naturalWidth > 0; }"""
async def go(pg, i): await pg.evaluate("(i) => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: i * s.clientHeight, behavior: 'instant' }); }", i)
async def swipe_time(pg, i):
    t0 = time.time(); await go(pg, i)
    try: await pg.wait_for_function(PLAYING, arg=i, timeout=10000, polling=20); return round((time.time() - t0) * 1000)
    except Exception: return 10000
async def all_warm(pg, ms=15000):
    try: await pg.wait_for_function("""() => { const f = window.__chisme.forYou, P = f.player, sl = [...document.querySelectorAll('#feed-scroll .vf-slide')];
        return sl.slice(f.cur + 1).filter(s => s.dataset.url).slice(0, P.ahead).every(s => s.dataset.warm === 'ready' || (P.ios && s.dataset.kind === 'tt')); }""", timeout=ms)
    except Exception: pass
async def open_feed(p, eng, init=""):
    if eng == "webkit":
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); ctx = await b.new_context(**dev)
    else:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"]); ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    await ctx.add_init_script(QUIET + INIT); 
    if init: await ctx.add_init_script(init)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:140]) if "localhost" in (e.stack or "") else None)
    await pg.goto(URL + "#cual-dieta"); await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    return b, pg, errs

async def chromium(p):
    print("== Chromium phone (390×844), a good connection")
    b, pg, errs = await open_feed(p, "chromium")
    try: await pg.wait_for_function("window.__chisme.forYou.player.players.length === window.__chisme.forYou.player.pool && window.__chisme.forYou.player.players.every(p => p.ready)", timeout=30000)
    except Exception: pass
    s = await pg.evaluate(ST)
    check(s["pool"] == 4 and s["n"] == 4 and all(x["ready"] and x["slide"] == -1 for x in s["players"]), f"4 YouTube players made and ready on ¿Y la dieta?, before ▶ Start ({s['n']} players, pool {s['pool']})")
    await pg.click("#fy-start"); await pg.wait_for_function(PLAYING, arg=0, timeout=20000); await all_warm(pg)
    s = await pg.evaluate(ST); vids = [i for i, k in enumerate(s["kinds"]) if k in "ty"]
    check(s["warmReady"] == vids[1:3] and s["ahead"] == 2, f"video 1 plays; the next 2 videos are loaded, muted, held on their first frame (warm {s['warmReady']})")
    await pg.wait_for_timeout(1500); s = await pg.evaluate(ST)
    check(set(range(0, 7)) - {k for k in range(7) if s["kinds"][k] == "D"} <= set(s["thumbs"]), f"the next 6 slides' thumbnails are already fetched and decoded ({s['thumbs'][:10]})")
    times, posters, i = [], [], 0
    for k in range(13):
        await all_warm(pg); await pg.wait_for_timeout(600)
        i += 1
        if s["kinds"][i] == "D":   # the donate slide: the 2 videos after it are warm while you look at it
            await go(pg, i); await pg.wait_for_timeout(1200); d = await pg.evaluate(ST)
            nxt = [j for j in vids if j > i][:2]
            check(d["cur"] == i and d["warmReady"] == nxt and not [x for x in d["players"] if x["slide"] == i], f"on the donate slide ({i}): no player on it, and the 2 videos after it are warm ({d['warmReady']} = {nxt})")
            i += 1; donate_next = len(times)
        posters.append(await pg.evaluate(POSTER, i))
        times.append(await swipe_time(pg, i))
        snd = await pg.evaluate("document.querySelector('#feed-sound').textContent.trim()")
        if snd != "🔊 Sound on": check(False, f"sound stays on after swipe {k + 1} ({snd})")
    s = await pg.evaluate(ST)
    med = statistics.median(times)
    check(med <= 400 and max(times) <= 1500, f"each swipe → playing: median {med:.0f} ms (≤ 400), slowest {max(times)} ms ({times})")
    check(times[donate_next] <= 600, f"the swipe past the donate slide plays at once too ({times[donate_next]} ms)")
    check(all(posters), f"every slide swiped to already has its picture (never a black screen while a player readies) ({posters.count(True)}/{len(posters)})")
    check(s["frames"] == 4 and s["n"] == 4 and not s["far"] and all(abs(t - s["cur"]) <= 3 for t in s["tt"]), f"{len(times)} swipes in: still exactly 4 player iframes, none on a video more than 2 away (slide {s['cur']}: players on {[x['slide'] for x in s['players']]}, TikToks {s['tt']})")
    behind = max(j for j in vids if j < s["cur"]); pb = next((x for x in s["players"] if x["slide"] == behind), None)
    check(pb is not None and not pb["warm"] and pb["st"] == 2, f"the one behind is kept, paused, for a swipe back ({pb})")
    t = await swipe_time(pg, behind)
    check(t <= 600, f"swipe back: it plays right away ({t} ms)")
    check(not errs, f"no errors from Chisme ({errs[:2]})")
    await b.close()
    return times

async def slow(p):
    print("\n== Chromium, a slow connection (3g) / data saver")
    b, pg, errs = await open_feed(p, "chromium", NET % ("3g", "false"))
    try: await pg.wait_for_function("window.__chisme.forYou.player.players.length === 3 && window.__chisme.forYou.player.players.every(p => p.ready)", timeout=30000)
    except Exception: pass
    await pg.click("#fy-start"); await pg.wait_for_function(PLAYING, arg=0, timeout=20000); await all_warm(pg); await pg.wait_for_timeout(2500)
    s = await pg.evaluate(ST); vids = [i for i, k in enumerate(s["kinds"]) if k in "ty"]
    check(s["slow"] and s["ahead"] == 1 and s["pool"] == 3 and s["n"] == 3 and s["warmReady"] == vids[1:2], f"3g: only the next video is preloaded (warm {s['warmReady']}), 3 players")
    th = [k for k in s["thumbs"] if k > 2]
    check(not [k for k in th if k > 3], f"…and thumbnails only 2 ahead ({s['thumbs']})")
    t = await swipe_time(pg, vids[1])
    check(t <= 600, f"…the swipe to it still plays at once ({t} ms)")
    await b.close()
    b, pg, errs = await open_feed(p, "chromium", NET % ("4g", "true"))
    await pg.wait_for_timeout(2500); await pg.click("#fy-start"); await pg.wait_for_timeout(2500)
    s = await pg.evaluate(ST); play = await pg.evaluate("!!document.querySelector('#feed-scroll .vf-slide .vf-play')")
    check(s["n"] == 0 and s["frames"] == 0 and play, f"data saver: nothing preloads or autoplays (as before): no players, ▶ Tap to play ({s['n']} players)")
    await b.close()

async def webkit(p):
    print("\n== WebKit iPhone 13")
    b, pg, errs = await open_feed(p, "webkit")
    try: await pg.wait_for_function("window.__chisme.forYou.player.players.length === 3 && window.__chisme.forYou.player.players.every(p => p.ready)", timeout=30000)
    except Exception: pass
    s = await pg.evaluate(ST)
    check(s["ios"] and s["pool"] == 3 and s["n"] == 3, f"iPhone: 3 players (memory), all made before Start ({s['n']})")
    await pg.tap("#fy-start"); await pg.wait_for_function(PLAYING, arg=0, timeout=20000); await all_warm(pg)
    s = await pg.evaluate(ST)
    check(all(x["unlocked"] for x in s["players"]), f"the Start tap unlocked sound in all 3 (v41: never a player made after the tap) ({[x['unlocked'] for x in s['players']]})")
    check(s["warmReady"] == [1, 2], f"the next 2 videos are warm ({s['warmReady']})")
    times, loud = [], []
    for i in range(1, 6):
        await all_warm(pg); await pg.wait_for_timeout(800)
        times.append(await swipe_time(pg, i)); await pg.wait_for_timeout(700)
        loud.append(await pg.evaluate("(() => { const f = window.__chisme.forYou; return f.player.ytMuted === false && document.querySelector('#feed-sound').textContent.trim() === '🔊 Sound on'; })()"))
    s = await pg.evaluate(ST)
    check(all(loud) and statistics.median(times) <= 500, f"5 swipes: each plays with sound, median {statistics.median(times):.0f} ms ({times}, sound {loud})")
    check(s["frames"] == 3 and not s["far"], f"still 3 player iframes, none more than 2 videos away ({[x['slide'] for x in s['players']]})")
    check(not errs, f"no errors from Chisme ({errs[:2]})")
    await b.close()

async def main():
    async with async_playwright() as p:
        await chromium(p); await slow(p); await webkit(p)
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED"); sys.exit(1 if fails else 0)
asyncio.run(main())
