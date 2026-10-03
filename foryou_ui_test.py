"""¿Y la dieta? For You (v40: "Bigger the Pansa, Better the Chansa"), in WebKit (iPhone 13) + a real touch swipe in Chromium.
Banner at the top with Start watching; full-screen vertical scroll-snap feed; one muted-autoplay player at a time;
overlaid Save / Directions / Not for me / Details; signals (skip-fast, watch, save, not interested + undo) land in
localStorage; the 'Why you're seeing this' chip learns ("Because you saved 2 … spots"); Back button and the browser's
back close the feed; reduced motion → tap-to-play thumbnail; Settings → Reset my feed; creator cards (Instagram-only
labeled). v40: the feed is named "Bigger the Pansa, Better the Chansa" (banner, feed top bar, aria, Settings).
v41: sound is ON by default (remembered; 🔇 Muted turns it off). v49.12 started it MUTED; v49.13 (the owner's call) is back to sound ON by default
(Settings → Video reels → Play with sound); the sound runs below turn it on explicitly too. The video on screen tries sound first; when the browser refuses
(Chrome without a tap, iPhone Safari), it plays muted with a "Tap anywhere for sound" hint, and the first tap in the feed unmutes it.
v42: persistent YouTube players for the whole feed (loadVideoById), one on screen and others warming the next videos (muted,
held on its first frame, waiting under the slide on screen), swapping as you swipe; never an iframe per video.
v47: preloading: 3 players on iPhone (on screen + the next 2 videos), 4 elsewhere (+ the one behind, paused). On iPhone the
Start tap (or the first tap in the feed) unlocks sound for every video after it: WebKit iPhone, 5 videos in a row, each playing
within 3 s, with sound after one tap (also with YouTube held back until 3 s after Start). Settings → Food videos: sound on/off
(default on). TikToks go after YouTube on iPhone; elsewhere the next TikTok warms muted in its slide.
Screens: dieta-foryou-banner.png, dieta-vertical-feed.png, dieta-why-chip.png, food-panza.png, food-sound.png, food-sound-held.png,
settings-food-sound.png"""
import re
import asyncio, time, os, sys, json
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); %s }"
PROF = "JSON.parse(localStorage.getItem('chisme-foryou') || 'null')"
FEED = """() => { const s = document.querySelector('#feed-scroll'), sl = [...s.querySelectorAll('.vf-slide')];
  return { open: document.querySelector('#feed').open, cur: window.__chisme.forYou.cur, pos: document.querySelector('#feed-pos') ? document.querySelector('#feed-pos').textContent : null, label: (document.querySelector('.feed-label') || {}).textContent,
    // v42: players = the YouTube players' layers on a slide (not the one warming the next video) + TikTok iframes in their slides
    frames: [...window.__chisme.forYou.player.players.filter(p => p.slide >= 0 && !p.warm).map(p => ({ slide: p.slide, src: 'yt:' + p.vid })),
      ...[...s.querySelectorAll('.vf-slide:not([data-warm]) iframe')].map(f => ({ slide: sl.indexOf(f.closest('.vf-slide')), src: f.src }))].sort((a, b) => a.slide - b.slide),
    yt: document.querySelectorAll('iframe.vf-yt').length, ytInSlides: s.querySelectorAll('.vf-slide iframe[data-kind=yt]').length,
    playingUi: sl.map((x, i) => x.classList.contains('vf-playing') ? i : -1).filter(i => i >= 0), warm: sl.map((x, i) => x.dataset.warm === 'ready' ? i : -1).filter(i => i >= 0),
    info: sl.length && window.__chisme.forYou.cur >= 0 ? (() => { const x = sl[window.__chisme.forYou.cur], a = x.querySelector('.vf-info'), r = x.querySelector('.vf-rail');
      return a ? { info: getComputedStyle(a).visibility + ' ' + getComputedStyle(a).opacity, rail: getComputedStyle(r).visibility, paused: x.classList.contains('vf-paused') } : null; })() : null,
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


async def wait_warm(pg, ms=8000):   # v42/v47: the video on screen plays and the next 2 videos (donate slides skipped) are loaded in players of their own (first frame, held)
    try: await pg.wait_for_function("""() => { const f = window.__chisme.forYou, P = f.player, sl = [...document.querySelectorAll('#feed-scroll .vf-slide')], c = sl[f.cur];
      if (!(c.dataset.kind === 'yt' ? P.st === 1 : c._st === 1)) return false;
      return sl.slice(f.cur + 1).filter(s => s.dataset.url).slice(0, P.ahead).every(s => s.dataset.warm === 'ready' || (P.ios && s.dataset.kind === 'tt')); }""", timeout=ms)
    except Exception: pass

async def show_info(pg, i):   # while a video plays its info + buttons are hidden; a tap on the video pauses it and brings them back
    sel = f"#feed-scroll .vf-slide:nth-child({i + 1})"
    for _ in range(2):
        if not await pg.evaluate(f"document.querySelector('{sel}').classList.contains('vf-playing')"): break
        await pg.tap(f"{sel} .vf-shield")
        try: await pg.wait_for_function(f"getComputedStyle(document.querySelector('{sel} .vf-rail')).visibility === 'visible'", timeout=2000)
        except Exception: pass
    await pg.wait_for_timeout(300)

SLIDE_OF = "(u) => [...document.querySelectorAll('#feed-scroll .vf-slide')].findIndex(s => s.dataset.url === u)"   # a video's slide (v46: a donate slide after every 7)
async def go(pg, i):   # scroll the feed to slide i the way a snap scroll ends up
    await pg.evaluate("(i) => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: i * s.clientHeight, behavior: 'instant' }); }", i)
    await pg.wait_for_function("(i) => window.__chisme.forYou.cur === i", arg=i, timeout=5000)

async def wk(p):
    b = await p.webkit.launch()
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "localStorage.setItem('chisme-feed-sound','off');")   # v41: this run is muted (sound() tests the default)
    pg = await ctx.new_page(); errs = []
    # WebKit: an embedded player torn down mid-call (far-behind players are unloaded) can throw "Context is stopped" from inside
    # its own frame; it's only the app's if the stack points into Chisme's code
    pg.on("pageerror", lambda e: print("    (player noise, not Chisme:", str(e)[:60] + ")") if str(e) == "Context is stopped" and "localhost" not in (e.stack or "") else None)
    pg.on("pageerror", lambda e: None if (str(e) == "Context is stopped" and "localhost" not in (e.stack or "")) or re.search(r"(tiktok|youtube(-nocookie)?)\.com\" from accessing a frame|tiktokw?\.|ttwstatic|byteimg|ibytedtos|googlevideo|ytimg", str(e)) else errs.append(str(e)[:160]))   # the player iframe poking at its parent (WebKit)
    pg.on("console", lambda m: errs.append(m.text[:160]) if own_error(m) else None)
    await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    # 1. the banner: top of ¿Y la dieta?, above the Latest / Saved spots chips; desk still at the bottom
    lay = await pg.evaluate("""() => { const c = document.querySelector('#foryou-card'), chips = document.querySelector('#food-view'), card = document.querySelector('#antojos');
      const r = c.getBoundingClientRect(), b = document.querySelector('#fy-start').getBoundingClientRect();
      return { afterHead: c.previousElementSibling.classList.contains('sec-head'), aboveChips: r.bottom <= chips.getBoundingClientRect().top,
        chips: [...chips.querySelectorAll('.chip')].map(x => x.dataset.fv), deskLast: card.lastElementChild.id === 'food-desk',
        title: document.querySelector('#fy-title').textContent.trim(), btn: document.querySelector('#fy-start').textContent.trim(), btnH: Math.round(b.height), btnW: Math.round(b.width),
        meta: document.querySelector('#fy-meta').textContent } }""")
    check(lay["afterHead"] and lay["aboveChips"], "For You banner is the first thing under the ¿Y la dieta? heading, above the chips")
    check(lay["title"] == "📺 ChismeTV" and lay["btn"] == "▶ Watch ChismeTV" and lay["btnH"] >= 52 and lay["btnW"] >= 300, f"banner: '{lay['title']}', big '{lay['btn']}' button ({lay['btnW']}×{lay['btnH']})")
    check(lay["chips"] == ["latest", "saved"] and lay["deskLast"], "Latest + Saved spots chips kept; food desk still at the bottom")
    # v40: the feed is called "Bigger the Pansa, Better the Chansa" everywhere (banner title, feed top bar, aria, tip note, Settings); no "For You" / "Tu feed de antojos" left
    NAME = "ChismeTV"   # v49.13: the feed is ChismeTV (its old name stays as a small subtitle)
    nm = await pg.evaluate("""() => { const k = document.querySelector('#fy-title'), card = document.querySelector('#foryou-card'), r = k.getBoundingClientRect(), c = card.getBoundingClientRect();
      const txt = document.body.innerText + ' ' + [...document.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' ') + ' ' + document.querySelector('#settings').textContent;
      return { title: k.textContent.trim(), dup: !!document.querySelector('#fy-kicker'), fits: k.scrollWidth <= k.clientWidth + 1 && r.left >= c.left && r.right <= c.right + 1, lines: Math.round(r.height / parseFloat(getComputedStyle(k).lineHeight)),
        region: card.getAttribute('aria-labelledby'), dialog: document.querySelector('#feed').getAttribute('aria-label'), legend: [...document.querySelectorAll('#settings legend')].map(l => l.textContent).find(t => /feed/i.test(t)) || '',
        forYou: /for you\\b|feed de antojos/i.test(txt.replace(/for your/gi, '')) }; }""")
    check(nm["title"] == "📺 " + NAME and not nm["dup"] and nm["fits"] and nm["lines"] <= 3 and nm["region"] == "fy-title", f"banner title: '{nm['title']}' fits the card on a phone ({nm['lines']} line(s), no overflow, not repeated)")
    check(nm["dialog"].startswith(NAME) and nm["legend"] == NAME + " feed" and not nm["forYou"], f"the feed's aria label and Settings say '{NAME}', and 'For You' is gone ({nm['dialog'][:40]!r}, {nm['legend']!r})")
    crew = await pg.evaluate("[...document.querySelectorAll('#food-crew-list .crew')].map(c => ({ name: c.querySelector('b').textContent, uses: c.querySelector('.crew-uses').textContent, links: [...c.querySelectorAll('a')].map(a => a.href + ' ' + a.target) }))")
    saf = next((c for c in crew if c["name"] == "S.A. Foodie"), None)
    check(len(crew) >= 9 and saf and saf["uses"] == "Instagram only" and saf["links"] == ["https://www.instagram.com/s.a.foodie/ "], f"creator cards: {len(crew)}, S.A. Foodie is an Instagram-only link card, opening in Chisme ({saf})")
    await pg.evaluate("window.scrollTo(0, document.querySelector('#antojos').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 10)")
    await pg.wait_for_timeout(900)
    await pg.screenshot(path=os.path.join(OUT, "dieta-foryou-banner.png"))
    # 2. Start watching → full-screen vertical feed, one video per screen, first one autoplays muted
    cov = await pg.evaluate("({ tiles: [...document.querySelectorAll('#fy-cover .fy-tile-by')].map(e => e.textContent), next: document.querySelector('#fy-next').textContent, urls: __chisme.forYou.cover })")
    check(len(cov["tiles"]) == 3 and len(set(cov["tiles"])) == 3 and cov["next"].startswith("Up next:"), f"banner cover: 3 videos from 3 different creators ({cov['tiles']}; '{cov['next'][:90]}')")
    await pg.tap("#fy-start"); t_open = time.time(); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(700)
    f = await pg.evaluate(FEED)
    check(f["open"] and f["h"] == f["vh"] and f["slideH"] == f["vh"], f"feed fills the screen; each video is one screen tall ({f['slideH']} = {f['vh']} px)")
    check(f["snap"].startswith("y") and "mandatory" in f["snap"] and f["align"] == "start", f"scroll-snap: '{f['snap']}', slides snap to '{f['align']}'")
    n = f["n"] - 1
    check(f["pos"] is None and (f["label"] or "").strip().startswith("ChismeTV") and f["cur"] == 0 and n >= 10, f"v43: just the title at the top, no 'N / {n}' counter ({f['label']!r}, {n} videos)")
    feed = (await pg.evaluate("window.__chisme.forYou"))["feed"]
    check(all(r["why"] for r in feed) and not any(r["explore"] for r in feed), "fresh phone: every card has a why chip; no exploration until it has learned something")
    check([r["url"] for r in feed[:3]] == cov["urls"], "the feed opens on the same 3 videos the banner cover shows")
    crews9 = [r["crew"] for r in feed[:9]]
    check(len(set(crews9)) == min(9, len({r["crew"] for r in feed})), f"new phone: the first 9 videos are {len(set(crews9))} different creators ({', '.join(r['creator'].split(' ')[0] for r in feed[:9])})")
    top10 = [r["crew"] for r in feed[:10]]
    check(max(top10.count(c) for c in top10) <= 2 and not any(feed[i]["crew"] == feed[i - 1]["crew"] for i in range(1, len(feed))), "no creator more than 2× in the top 10, never the same creator twice in a row")
    pl = [r["place"] for r in feed if r["place"]]
    check(len(pl) == len(set(pl)), f"one video per restaurant ({len(pl)} videos with a known spot, no repeats)")
    rec = [i for i, r in enumerate(feed) if r["recipe"]]
    check(len(rec) >= 40 and len({feed[i]["crew"] for i in rec}) >= 35 and all(feed[i]["recipe"] == (i % 3 == 2) for i in range(30)),
          f"cooking / recipe videos mixed in: {len(rec)} from {len({feed[i]['crew'] for i in rec})} cooks, every 3rd video ({''.join('R' if r['recipe'] else '·' for r in feed[:15])}; {', '.join(feed[i]['title'][:22] for i in rec[:3])})")
    lead0 = feed[0]["crew"]
    # 3. swipe on (keyboard ↓, then a snap scroll): the player moves with you, one at a time; a fast skip is recorded
    await pg.keyboard.press("ArrowDown"); await pg.wait_for_function("window.__chisme.forYou.cur === 1", timeout=5000); await wait_warm(pg)
    f = await pg.evaluate(FEED)
    check([x["slide"] for x in f["frames"]] == [1] and f["playingUi"] == [1] and f["warm"] == [2, 3] and f["cur"] == 1,
          f"↓ next video: video 2 plays in the player that had it warming, and videos 3 + 4 are now warm (v47: 2 ahead) (on screen {[x['slide'] for x in f['frames']]}, warm {f['warm']})")
    check(f["yt"] == 3 and f["ytInSlides"] == 0, f"v47 iPhone: 3 YouTube players for the whole feed, reused from video to video (no iframe per video: {f['yt']} players, {f['ytInSlides']} in slides)")
    prof = await pg.evaluate(PROF)
    check(prof and (prof["s"].get(feed[0]["url"]) or {}).get("sk") == 1, f"[{time.time() - t_open:.1f} s on video 1; {prof and prof['s'].get(feed[0]['url'])}] skip-fast (< 2 s) on video 1 is recorded on the phone")
    await pg.tap("#feed-scroll .vf-slide:nth-child(2) .vf-shield"); await pg.wait_for_timeout(400)
    f = await pg.evaluate(FEED)
    check(f["info"]["paused"] and f["info"]["info"] == "visible 1" and f["info"]["rail"] == "visible" and f["playingUi"] == [], f"tap the video: it pauses and the info + buttons come back ({f['info']})")
    await pg.tap("#feed-scroll .vf-slide:nth-child(2) .vf-shield"); await pg.wait_for_timeout(700)
    f = await pg.evaluate(FEED)
    check(not f["info"]["paused"] and f["info"]["info"].startswith("hidden") and f["playingUi"] == [1], f"tap again: it plays and the info hides ({f['info']}, {f['playingUi']})")
    await pg.wait_for_timeout(3600); await go(pg, 2); await wait_warm(pg)
    f = await pg.evaluate(FEED)
    check([x["slide"] for x in f["frames"]] == [2] and f["warm"] == [3, 4] and f["yt"] == 3, f"3 videos in: still the same 3 players (on screen {[x['slide'] for x in f['frames']]}, warm {f['warm']}, {f['yt']} YouTube players)")
    rs = await pg.evaluate("""(u) => { const s = document.querySelectorAll('#feed-scroll .vf-slide')[2], P = window.__chisme.forYou.player, id = (u.match(/shorts\\/([\\w-]{11})/) || [])[1];
      const fr = [...document.querySelectorAll('iframe.vf-yt')].find(f => !f.parentNode.classList.contains('warm') && !f.parentNode.classList.contains('off'));
      return { tag: s.querySelector('.vf-recipe')?.textContent, dir: !!s.querySelector('.vf-dir'), inApp: P.slide === 2 && P.vid === id && !!fr && fr.src.startsWith('https://www.youtube-nocookie.com/embed/'), tall: s.classList.contains('tall'), why: s.querySelector('.why-chip').textContent }; }""", feed[2]["url"])
    check(feed[2]["recipe"] and rs["tag"] == "🍳 Recipe · cook it at home" and not rs["dir"] and rs["inApp"] and rs["tall"] and rs["why"].startswith("✨Cook it at home: "),
          f"video 3 is a recipe: plays in the app (YouTube embed, full height), '{rs['tag']}', chip '{rs['why']}', no Directions")
    prof = await pg.evaluate(PROF)
    check((prof["s"].get(feed[1]["url"]) or {}).get("v", 0) >= 1, "watching video 2 for 3.6 s counts as a watch")
    # 4. overlay actions: Save, Not for me (+ Undo)
    s2 = "#feed-scroll .vf-slide:nth-child(3)"
    await show_info(pg, 2)
    await pg.tap(f"{s2} .vf-rail .fr-save"); await pg.wait_for_timeout(300)
    sv = await pg.evaluate(f"({{ pressed: document.querySelector('{s2} .fr-save').getAttribute('aria-pressed'), n: document.querySelector('#n-saved').textContent }})")
    prof = await pg.evaluate(PROF)
    check(sv["pressed"] == "true" and sv["n"] == "(1)" and (prof["s"].get(feed[2]["url"]) or {}).get("sv") == 1, f"🔖 Save on the video: saved to Saved spots {sv['n']} and learned")
    await pg.tap(f"{s2} .vf-ni"); await pg.wait_for_timeout(500)
    ni = await pg.evaluate(f"({{ gone: !document.querySelector('#feed-scroll .vf-slide[data-url=\"' + CSS.escape({json.dumps(feed[2]['url'])}) + '\"]'), toast: document.querySelector('#feed-toast').textContent }})")
    prof = await pg.evaluate(PROF)
    check(ni["gone"] and "fewer like this" in ni["toast"] and (prof["s"].get(feed[2]["url"]) or {}).get("ni") == 1, f"🙅 Not for me: the video is gone, '{ni['toast']}'")
    await pg.tap("#feed-toast button"); await pg.wait_for_timeout(500)
    await show_info(pg, 2)
    back = await pg.evaluate(f"({{ back: !!document.querySelector('#feed-scroll .vf-slide[data-url=\"' + CSS.escape({json.dumps(feed[2]['url'])}) + '\"]'), cur: window.__chisme.forYou.cur }})")
    prof = await pg.evaluate(PROF)
    check(back["back"] and not (prof["s"].get(feed[2]["url"]) or {}).get("ni"), "Undo brings it back")
    has_dir = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')].findIndex(s => s.querySelector('.vf-dir'))")
    if has_dir >= 0:
        await go(pg, has_dir); await pg.wait_for_timeout(1400); await show_info(pg, has_dir)
        d = await pg.evaluate(f"(() => {{ const s = document.querySelectorAll('#feed-scroll .vf-slide')[{has_dir}], a = s.querySelector('.vf-dir'); return {{ href: a.href, place: s.querySelector('.vf-place')?.textContent }}; }})()")
        check(d["href"].startswith("https://maps.apple.com/?daddr=") and d["place"], f"📍 restaurant info + Directions on the video ({d['place'][:50]})")
        await pg.screenshot(path=os.path.join(OUT, "dieta-vertical-feed.png"))
    else:
        check(False, "a video with a restaurant address (for Directions)")
    # 5. close: the Back button returns to the tab; so does the browser's back
    await pg.tap("#feed-close"); await pg.wait_for_timeout(600)
    st = await pg.evaluate("({ open: document.querySelector('#feed').open, view: window.__chisme.view, locked: document.documentElement.classList.contains('feed-open') })")
    check(not st["open"] and st["view"] == "antojos" and not st["locked"], f"‹ Back closes the feed, back on ¿Y la dieta? ({st})")
    lead1 = await pg.evaluate("__chisme.forYou.coverCrews[0]")
    check(lead1 and lead1 != lead0, f"rotation: after closing, the banner cover leads with a different creator ({lead0} → {lead1})")
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(700)
    await wait_warm(pg); f = await pg.evaluate(FEED)
    pl = await pg.evaluate("({ P: window.__chisme.forYou.player, src: [...document.querySelectorAll('iframe.vf-yt')].map(f => f.src) })")
    check([x["slide"] for x in f["frames"]] == [0] and pl["P"]["st"] == 1 and pl["P"]["ytMuted"] is True and all("playsinline=1" in u and "enablejsapi=1" in u for u in pl["src"]),
          f"(🔇 Muted chosen) the first video autoplays muted + inline (player state {pl['P']['st']}, YouTube muted={pl['P']['ytMuted']})")
    check(f["playingUi"] == [0] and f["warm"] == [1, 2], f"only the video on screen plays; the next 2 wait, loaded, in the other players (playing {f['playingUi']}, warm {f['warm']})")
    check(f["info"] and f["info"]["info"].startswith("hidden") and f["info"]["rail"] == "hidden", f"while it plays, the title / creator / spot / buttons are hidden ({f['info']})")
    tb = await pg.evaluate("[...document.querySelectorAll('#feed-close, #feed-sound')].map(b => { const r = b.getBoundingClientRect(), st = getComputedStyle(b); return st.visibility === 'visible' && +st.opacity > .9 && r.top >= 0 && r.height >= 44; })")
    check(tb == [True, True], "‹ Back and 🔇 Muted stay on screen while it plays")
    bar = await pg.evaluate("""() => { const t = document.querySelector('.feed-top'), r = t.getBoundingClientRect(), a = getComputedStyle(t).backgroundColor.match(/[\\d.]+/g).map(Number);
      const tall = [...document.querySelectorAll('#feed-scroll .vf-player.tall:not(.warm):not(.off) .vf-frame, #feed-scroll .vf-slide.tall .vf-frame')].map(f => Math.round(f.getBoundingClientRect().top - f.parentNode.getBoundingClientRect().top));
      return { h: Math.round(r.bottom), alpha: a.length > 3 ? a[3] : 1, lum: Math.max(a[0], a[1], a[2]), tall }; }""")
    check(bar["alpha"] >= 0.9 and bar["lum"] <= 30 and bar["tall"] and all(t >= bar["h"] - 1 for t in bar["tall"]),
          f"top bar is a solid dark strip ({bar['h']} px) and full-height players start below it, so their own creator row never sits under the title (frame tops {bar['tall'][:4]})")
    fl = await pg.evaluate("""() => { const l = document.querySelector('.feed-label'), b = l.querySelector('b'), r = l.getBoundingClientRect(), back = document.querySelector('#feed-close').getBoundingClientRect(), snd = document.querySelector('#feed-sound').getBoundingClientRect();
      return { name: b.textContent, clear: r.left >= back.right - 1 && r.right <= snd.left + 1, fits: l.scrollWidth <= l.clientWidth + 1, h: Math.round(r.height) }; }""")
    check(fl["name"] == NAME and fl["clear"] and fl["fits"] and fl["h"] <= 60, f"feed top bar: '{fl['name']}' wraps/shrinks between ‹ Back and 🔇 Muted without overlapping ({fl['h']} px tall)")
    try:   # food-panza.png: the banner and the feed's top bar, side by side
        from PIL import Image
        import io
        feed_top = Image.open(io.BytesIO(await pg.screenshot())); banner = Image.open(os.path.join(OUT, "dieta-foryou-banner.png"))
        out = Image.new("RGB", (banner.width + feed_top.width + 30, max(banner.height, feed_top.height)), "white"); out.paste(banner, (0, 0)); out.paste(feed_top, (banner.width + 30, 0))
        out.save(os.path.join(OUT, "food-panza.png"))
    except Exception as e: check(False, f"food-panza.png ({e})")
    await pg.evaluate("history.back()"); await pg.wait_for_timeout(800)
    st = await pg.evaluate("({ open: document.querySelector('#feed').open, view: window.__chisme.view, frames: document.querySelectorAll('.vf-slide iframe, .vf-player:not(.off)').length, playing: window.__chisme.forYou.player.players.some(p => p.st === 1) })")
    check(not st["open"] and st["view"] == "antojos" and st["frames"] == 0 and not st["playing"], f"the phone's Back also closes it (and stops the video) ({st})")
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
        for fi in dish["idx"][:2]:
            i = await pg.evaluate(SLIDE_OF, feed[fi]["url"])   # (v46+: donate slides in between, so find the video's slide by its url)
            await go(pg, i); await show_info(pg, i); await pg.tap(f"#feed-scroll .vf-slide:nth-child({i + 1}) .vf-rail .fr-save"); await pg.wait_for_timeout(250)
        await pg.tap("#feed-close"); await pg.wait_for_timeout(500)
        meta = await pg.text_content("#fy-meta")
        check(meta.startswith("Tuned to you:"), f"banner shows what it learned: '{meta}'")
        await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
        feed2 = (await pg.evaluate("window.__chisme.forYou"))["feed"]
        nsv = ((await pg.evaluate(PROF))["f"].get(dish["k"]) or {}).get("sv", 0)   # (a video saved earlier can be this dish too)
        want = f"Because you saved {nsv} {dish['label']} spot{'s' if nsv != 1 else ''}"
        hit = next((i for i, r in enumerate(feed2) if r["why"] == want), -1)
        check(hit >= 0 and hit < 6, f"why chip: '{want}' on video #{hit + 1}")
        ex = [r for r in feed2 if r["explore"]]
        check(len(ex) == len(feed2) // 5 and all(r["why"].startswith("Something") for r in ex), f"exploration: {len(ex)} of {len(feed2)} videos (~20%), chip '{ex[0]['why'] if ex else ''}'")
        if hit >= 0:
            hit = await pg.evaluate(SLIDE_OF, feed2[hit]["url"])
            await go(pg, hit); await pg.wait_for_timeout(1400); await show_info(pg, hit)
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
    r = await pg.evaluate("({ frames: document.querySelectorAll('.vf-slide iframe, .vf-player:not(.off)').length, play: !!document.querySelector('#feed-scroll .vf-slide:first-child .vf-play'), thumb: !!document.querySelector('#feed-scroll .vf-slide:first-child .vf-thumb') })")
    check(r["frames"] == 0 and r["play"] and r["thumb"], f"Reduce motion switched on in Chisme's Settings: no autoplay; a thumbnail with ▶ Tap to play ({r})")
    await pg.tap("#feed-scroll .vf-slide:first-child .vf-play")
    try: await pg.wait_for_function("window.__chisme.forYou.player.slide === 0 && window.__chisme.forYou.player.st === 1", timeout=15000)
    except Exception: pass
    r = await pg.evaluate("({ P: window.__chisme.forYou.player, p: " + PROF + " })")
    check(r["P"]["slide"] == 0 and r["P"]["st"] == 1 and r["p"] and r["p"]["n"] >= 1, f"tap to play: the player starts, and it counts as an open (state {r['P']['st']})")
    await ctx.close()
    # v42: the phone's own Reduce Motion alone doesn't stop the feed (you opened it to watch; a tap pauses)
    ctx = await b.new_context(**dev, reduced_motion="reduce"); await ctx.add_init_script(INIT % "")
    pg = await ctx.new_page(); await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.wait_for_timeout(1500); await pg.tap("#fy-start")
    try: await pg.wait_for_function("window.__chisme.forYou.player.slide === 0 && window.__chisme.forYou.player.st === 1", timeout=15000)
    except Exception: pass
    r = await pg.evaluate("({ rm: matchMedia('(prefers-reduced-motion: reduce)').matches, P: window.__chisme.forYou.player, play: !!document.querySelector('#feed-scroll .vf-slide:first-child .vf-play') })")
    check(r["rm"] and r["P"]["st"] == 1 and not r["play"], f"the phone's system Reduce Motion alone: the feed still autoplays (state {r['P']['st']})")
    await ctx.close(); await b.close()

async def cr(p):   # a real finger swipe on the video itself scrolls to the next one (the player doesn't eat the touch)
    b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=3)
    await ctx.add_init_script(INIT % "localStorage.setItem('chisme-feed-sound','on');")   # v49.12: sound turned on (the default is muted)
    pg = await ctx.new_page(); await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(1200)
    cdp = await ctx.new_cdp_session(pg)
    async def swipe(y0, dy):   # a finger drag (Input.synthesizeScrollGesture doesn't scroll anything in headless Chrome)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 195, "y": y0}]})
        for i in range(1, 16):
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 195, "y": y0 + dy * i / 15}]}); await pg.wait_for_timeout(16)
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await wait_warm(pg, 15000)
    w = await pg.evaluate("({ sl: [...document.querySelectorAll('#feed-scroll .vf-slide')].slice(0, 3).map(s => s.dataset.warm || ''), kind: document.querySelectorAll('#feed-scroll .vf-slide')[1].dataset.kind, tt: !!document.querySelector('#feed-scroll .vf-slide:nth-child(2) iframe.vf-frame'), P: window.__chisme.forYou.player.players })")
    wp = next((x for x in w["P"] if x["warm"] and x["slide"] == 1), None)
    if w["kind"] == "yt":
        check(w["sl"][1] == "ready" and wp and wp["slide"] == 1 and wp["st"] == 2 and wp["muted"] is True, f"Chromium: video 2 (YouTube) is loaded in the second player, muted and held on its first frame ({w['sl']}, {wp})")
    else:
        check(w["sl"][1] == "ready" and w["tt"], f"Chromium: video 2 (TikTok) is loaded in its own player, muted and held on its first frame ({w['sl']})")
    check(await pg.evaluate("document.querySelector('#feed-sound').textContent.trim()") == "🔊 Sound on", "Chromium (autoplay allowed): with sound turned on, it plays with sound")
    for want in (1, 2):
        under = await pg.evaluate("document.elementFromPoint(195, 380).className")
        await swipe(380, -450)
        try: await pg.wait_for_function("(w) => window.__chisme.forYou.cur === w", arg=want, timeout=5000)
        except Exception: pass
        await pg.wait_for_timeout(400)
        f = await pg.evaluate(FEED)
        pl = await pg.evaluate("(w) => { const s = document.querySelectorAll('#feed-scroll .vf-slide')[w]; return { st: s._st, loading: s.classList.contains('vf-loading'), snd: document.querySelector('#feed-sound').textContent.trim() }; }", want)
        check(pl["st"] == 1 and not pl["loading"] and pl["snd"] == "🔊 Sound on", f"Chromium: video {want + 1} is already playing 0.4 s after the swipe (it was warming), no spinner, sound stays on ({pl})")
        await wait_warm(pg); f = await pg.evaluate(FEED)
        on = sorted({x["slide"] for x in f["frames"]})   # the one on screen (+ the one just behind it, kept paused for a swipe back)
        check(f["cur"] == want and f["top"] % f["h"] == 0 and want in on and set(on) <= {want - 1, want} and f["warm"] == [want + 1, want + 2] and f["playingUi"] == [want] and f["yt"] == 4,
              f"Chromium: finger swipe up on the video ({under}) → video {want + 1}, snapped exactly (scrollTop {f['top']}), only it plays; videos {want + 2} + {want + 3} are warm, 4 players ({[(x['slide'], x['src'][:40]) for x in f['frames']]}, warm {f['warm']})")
    await swipe(300, 450)
    try: await pg.wait_for_function("window.__chisme.forYou.cur === 1", timeout=5000)
    except Exception: pass
    check((await pg.evaluate(FEED))["cur"] == 1, "swipe down goes back a video")
    # a tap on the video pauses / plays (it doesn't open anything or scroll)
    await pg.wait_for_timeout(5200)
    await pg.tap("#feed-scroll .vf-slide:nth-child(2) .vf-shield"); await pg.wait_for_timeout(600)
    f = await pg.evaluate(FEED); st = await pg.evaluate("document.querySelectorAll('#feed-scroll .vf-slide')[1]._st")
    check(f["cur"] == 1 and await pg.evaluate("document.querySelector('#feed').open") and f["info"]["paused"] and f["info"]["info"] == "visible 1" and st == 2,
          f"a tap on the video pauses it (player state {st}), shows the info, and stays put")
    await pg.tap("#feed-scroll .vf-slide:nth-child(2) .vf-shield"); await pg.wait_for_timeout(1200)
    f = await pg.evaluate(FEED); st = await pg.evaluate("document.querySelectorAll('#feed-scroll .vf-slide')[1]._st")
    check(st == 1 and f["info"]["info"].startswith("hidden"), f"tap again: playing (state {st}), info hidden")
    await b.close()

SND = """() => { const f = window.__chisme.forYou, s = document.querySelectorAll('#feed-scroll .vf-slide')[f.cur], P = f.player, b = document.querySelector('#feed-sound'), h = getComputedStyle(document.querySelector('#feed .feed-top'), '::after');
  const yt = !!s && s.dataset.kind === 'yt';
  return { ...f.sound, btn: b.textContent.trim(), pressed: b.getAttribute('aria-pressed'), label: b.getAttribute('aria-label'), yt, st: yt ? (P.slide === f.cur ? P.st : -1) : s && s._st, ytMuted: yt ? P.ytMuted : null,
    unlocked: P.unlocked, vid: P.vid, cur: f.cur, loading: !!s && s.classList.contains('vf-loading'), players: P.frames, setting: document.querySelector('#set-feed-sound').checked,
    playing: !!s && s.classList.contains('vf-playing'), hint: h.content, pref: localStorage.getItem('chisme-feed-sound') }; }"""
async def sound(p):
    print("\n== v41: sound (v49.12: muted by default, then turned on)")
    # Chrome with its normal autoplay rule (sound needs a tap on the page); the feed opened without a tap, like a browser that says no
    b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--autoplay-policy=document-user-activation-required"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    c0 = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=1)   # v49.12: nothing chosen yet = muted
    await c0.add_init_script(INIT % ""); p0 = await c0.new_page(); await p0.goto(URL + "#cual-dieta")
    await p0.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await p0.wait_for_timeout(1000); await p0.evaluate("window.__chisme.openFeed(null, 0)"); await p0.wait_for_timeout(1500)
    d0 = await p0.evaluate(SND)
    # v49.13: the owner wants the reels to autoplay WITH sound by default again (reverses v49.12 legal M4/L20; the browser may still
    # hold the sound until a tap: then it plays muted with the hint)
    check(d0["wanted"] and d0["pref"] is None and d0["setting"], f"v49.13: nothing chosen yet: sound is wanted (Settings → Video reels → Play with sound checked) ({d0['btn']!r})")
    await c0.close()
    await ctx.add_init_script(INIT % "localStorage.setItem('chisme-feed-sound','on');"); pg = await ctx.new_page(); errs = []
    pg.on("console", lambda m: errs.append(m.text[:160]) if own_error(m) else None)
    await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.wait_for_timeout(1500); await pg.evaluate("window.__chisme.openFeed(null, 0)")
    s0 = await pg.evaluate(SND)
    check(s0["wanted"] and s0["pref"] == "on" and s0["setting"], f"sound turned on: sound is wanted (Settings → Food videos: sound on is checked), and the video on screen tries to start WITH sound")
    try: await pg.wait_for_function("window.__chisme.forYou.sound.held", timeout=12000)
    except Exception: pass
    try: await pg.wait_for_function("() => { const f = window.__chisme.forYou, s = document.querySelectorAll('#feed-scroll .vf-slide')[f.cur]; return s && (s.dataset.kind === 'yt' ? f.player.st === 1 : s._st === 1); }", timeout=10000)   # (past any buffering)
    except Exception: pass
    await pg.wait_for_timeout(1500)
    s1 = await pg.evaluate(SND)
    if s1["held"]:
        check(s1["btn"] == "🔇 Muted" and "Tap anywhere for sound" in s1["hint"] and s1["st"] == 1, f"Chrome refused sound without a tap: it plays muted, the button says 🔇 Muted, and a 'Tap anywhere for sound' hint shows ({ {k: s1[k] for k in ('held', 'btn', 'st', 'ytMuted')} })")
        await pg.screenshot(path=os.path.join(OUT, "food-sound-held.png"))
        await pg.tap(f"#feed-scroll .vf-slide:nth-child({await pg.evaluate('window.__chisme.forYou.cur') + 1}) .vf-shield"); await pg.wait_for_timeout(2500)
        s2 = await pg.evaluate(SND)
        check(s2["unlocks"] == 1 and not s2["held"] and s2["btn"] == "🔊 Sound on" and s2["playing"] and s2["st"] == 1, f"the first tap in the feed turns the sound on (and doesn't pause the video) ({ {k: s2[k] for k in ('unlocks', 'btn', 'st', 'playing')} })")
    else:   # this Chrome let it start with sound right away
        s2 = s1
        check(s1["btn"] == "🔊 Sound on" and s1["st"] == 1 and s1["playing"] and not s1["hint"].startswith('"'), f"Chrome allowed sound without a tap: it plays with sound, 🔊 Sound on, no hint ({ {k: s1[k] for k in ('btn', 'st', 'ytMuted')} })")
    check(not s2["yt"] or s2["ytMuted"] is False, f"…YouTube itself reports it isn't muted (muted={s2['ytMuted']})")
    await pg.wait_for_timeout(1000); await pg.screenshot(path=os.path.join(OUT, "food-sound.png"))
    await pg.tap("#feed-sound"); await pg.wait_for_timeout(400)
    s3 = await pg.evaluate(SND)
    check(s3["btn"] == "🔇 Muted" and s3["pref"] == "off" and not s3["held"], "🔇 Muted turns it off and remembers it")
    await pg.tap("#feed-close"); await pg.wait_for_timeout(500); await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(800)
    s4 = await pg.evaluate(SND)
    check(s4["btn"] == "🔇 Muted" and not s4["wanted"] and not s4["setting"], f"reopened: still muted (and Settings → Food videos: sound is unchecked) ({s4['btn']})")
    await pg.tap("#feed-sound"); await pg.wait_for_timeout(1500)
    s5 = await pg.evaluate(SND)
    check(s5["btn"] == "🔊 Sound on" and s5["pref"] == "on", "tap it again: 🔊 Sound on (remembered)")
    check(not errs, f"no errors from Chisme ({errs[:2]})")
    await b.close()
    # v42, iPhone (WebKit): 5 videos in a row, each playing within 3 s, with sound after one tap
    await ios_five(p, slow=False)   # the players were ready when Start was tapped: that tap already brings the sound
    await ios_five(p, slow=True)    # YouTube slow to load: the first video plays muted with the hint; one tap, then sound from there on
    await settings_toggle(p)

async def ios_five(p, slow):
    label = "players slow to load" if slow else "players ready"
    print(f"\n== v42 WebKit iPhone: scroll through 5 videos ({label})")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "localStorage.setItem('chisme-feed-sound','on');"); pg = await ctx.new_page(); errs = []   # v49.12: sound turned on
    pg.on("console", lambda m: errs.append(m.text[:160]) if own_error(m) else None)
    gate = asyncio.Event()
    if slow:   # YouTube's player page arrives only 3 s after Start is tapped (so the players can't be ready for that tap)
        async def late(route): await gate.wait(); await asyncio.sleep(3); await route.continue_()
        await pg.route("**/www.youtube-nocookie.com/embed/**", late)
    await pg.goto(URL + "#cual-dieta", wait_until="domcontentloaded")   # (not "load": the players' iframes are made on this screen, and here they're held until Start)
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    if not slow:
        try: await pg.wait_for_function("window.__chisme.forYou.player.players.length === 3 && window.__chisme.forYou.player.players.every(p => p.ready)", timeout=20000)
        except Exception: pass
    await pg.tap("#fy-start"); gate.set(); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
    kinds = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide[data-url]')].map(s => s.dataset.kind || '')")   # (the videos: not the donate / end slides)
    tt = [i for i, k in enumerate(kinds) if k == "tt"]
    check(kinds[:5] == ["yt"] * 5 and (not tt or all(k == "tt" for k in kinds[tt[0]:-1])), f"iPhone: the YouTube videos come first, the TikToks after them ({len(tt)} TikToks from #{tt[0] + 1 if tt else '-'})")
    times, tapped = [], 0
    for k in range(5):
        await pg.wait_for_function("(k) => window.__chisme.forYou.cur === k", arg=k, timeout=5000)
        t0 = time.time(); ok = False
        for _ in range(int((10 if slow and k == 0 else 3) / 0.1)):
            w = await pg.evaluate(SND)
            if w["st"] == 1 and w["playing"] and not w["loading"]: ok = True; break
            await pg.wait_for_timeout(100)
        dt = time.time() - t0; times.append(round(dt, 1))
        await pg.wait_for_timeout(900); w = await pg.evaluate(SND)
        if k == 0 and w["held"]:   # the browser holds the sound until a tap: the hint, then one tap
            check(slow and w["btn"] == "🔇 Muted" and "Tap anywhere for sound" in w["hint"] and w["st"] == 1, f"video 1 plays muted with the 'Tap anywhere for sound' hint while sound isn't allowed yet (state {w['st']})")
            await pg.screenshot(path=os.path.join(OUT, "food-sound-held.png"))
            await pg.tap(f"#feed-scroll .vf-slide:nth-child({k + 1}) .vf-shield"); tapped += 1; await pg.wait_for_timeout(1500)
            w = await pg.evaluate(SND)
            check(w["unlocks"] == 1 and not w["held"] and w["ytMuted"] is False and w["st"] == 1 and w["playing"], f"one tap: sound on, and it keeps playing (YouTube muted={w['ytMuted']}, state {w['st']})")
        limit = 10 if slow and k == 0 else 3   # (slow: YouTube's player page is held back on purpose)
        check(ok and dt <= limit, f"video {k + 1} ({w['vid']}): playing {dt:.1f} s after it came on screen (≤ {limit} s)")
        check(w["ytMuted"] is False and not w["held"] and w["btn"] == "🔊 Sound on", f"video {k + 1}: with sound (YouTube muted={w['ytMuted']}, button '{w['btn']}')")
        if k == 1 and not slow: await pg.wait_for_timeout(2500); await pg.screenshot(path=os.path.join(OUT, "food-sound.png"))
        if k < 4:   # watch it a moment (like a person), then swipe up
            await pg.wait_for_timeout(1500)
            await pg.evaluate("() => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: s.scrollTop + s.clientHeight, behavior: 'instant' }); }")
    w = await pg.evaluate(SND)
    check(tapped == (1 if slow else 0) and w["players"] == 3, f"{'one tap' if slow else 'no tap besides Start'}, 5 videos with sound, all in the same 3 players (v47: made before Start, so that one tap unlocks them all) ({w['players']} YouTube iframes; times {times})")
    check(not errs, f"no errors from Chisme ({errs[:2]})")
    await b.close()

async def settings_toggle(p):
    print("\n== v42 Settings → Food videos: sound")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % ""); pg = await ctx.new_page()
    await pg.goto(URL + "#cual-dieta")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    await pg.tap("#settings-btn"); await pg.wait_for_timeout(500)
    st = await pg.evaluate("({ on: document.querySelector('#set-feed-sound').checked, label: document.querySelector('#set-feed-sound').closest('label').textContent.trim(), legend: document.querySelector('#set-feed-sound-group legend').textContent })")
    check(st["on"] and st["label"] == "Play with sound" and st["legend"] == "ChismeTV", f"Settings → Video reels has 'Play with sound', checked by default (v49.13 wording; was 'Food videos: sound on') ({st})")
    await pg.evaluate("document.querySelector('#set-feed-sound').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(300)
    await pg.screenshot(path=os.path.join(OUT, "settings-food-sound.png"))
    # v49.13: on by default, so the first tap turns it off
    await pg.tap("#set-feed-sound"); await pg.wait_for_timeout(200)
    check(await pg.evaluate("localStorage.getItem('chisme-feed-sound')") == "off", "unchecking it turns the videos' sound off (remembered)")
    await pg.tap("#set-feed-sound"); await pg.wait_for_timeout(200)
    check(await pg.evaluate("localStorage.getItem('chisme-feed-sound')") == "on", "checking it turns the videos' sound back on (remembered)")
    await pg.tap("#set-feed-sound"); await pg.wait_for_timeout(200)
    check(await pg.evaluate("localStorage.getItem('chisme-feed-sound')") == "off", "unchecking it again: off (remembered)")
    await pg.tap("#settings-close"); await pg.wait_for_timeout(300)
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=5000)
    try: await pg.wait_for_function("window.__chisme.forYou.player.st === 1", timeout=15000)
    except Exception: pass
    w = await pg.evaluate(SND)
    check(w["btn"] == "🔇 Muted" and not w["held"] and w["st"] == 1 and w["ytMuted"] is True, f"…so the feed plays muted, the button says 🔇 Muted, no hint (state {w['st']}, YouTube muted={w['ytMuted']})")
    await pg.tap("#feed-sound"); await pg.wait_for_timeout(1500)
    w = await pg.evaluate(SND)
    check(w["btn"] == "🔊 Sound on" and w["setting"] and w["ytMuted"] is False, f"the feed's 🔊 button turns it back on, and Settings follows (YouTube muted={w['ytMuted']})")
    await b.close()

async def main():
    async with async_playwright() as p:
        only = os.environ.get("FY_ONLY")   # e.g. FY_ONLY=sound
        for name, fn in (("wk", wk), ("cr", cr), ("sound", sound)):
            if not only or only == name: await fn(p)
    print("ALL PASS" if not fails else f"{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
