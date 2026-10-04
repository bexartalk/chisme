"""v49.15: the Facebook-style phone nav. Under 1024 px: a slim top bar (v49.16: ☰ Menu = Settings, the Chisme bubble =
Settings too; Tía moved to the bottom tab bar) and the section tabs as a bottom tab bar; both slide away while you scroll down and come back on any
scroll up (8 px or more), and always show near the top. The Chisme tab's sticky chip row (All · News · Sports · Events)
slides away with the top bar and comes back with it; no other tab leaves a sticky row stuck at the top.
Desktop (1024 px and up) must be exactly as before.
  • phone 390x844 (Android Chromium + iPhone WebKit): bars at the top, hidden after scrolling down, a 4 px nudge up keeps them
    hidden, a 20 px scroll up brings them back, back near the top always shows; content is padded (no overlap at the top,
    the last thing on the page clears the tab bar); the bars sit inside the safe areas; tabs switch (ids, aria-current,
    the bars come back on a switch); the Tía tab opens her chat, ☰ and the Chisme bubble open Settings; the floating
    Tía is gone on phones (one Tía); reduced motion = no transition; dark + Día de Muertos colours have no yellow on the bars
  • ChismeTV (full-screen reels): nothing covers the Like / Share column or the video's controls; the bars are tucked away
  • desktop 1440x900: html.dk, no phone top bar, the nav at the top, the floating Tía, Settings in the nav, no hiding on
    scroll; with REF_URL (the base build) the nav, Settings, Tía and the page column are in the same place, same size
  • no yellow anywhere in the Día de Muertos season (news_no_yellow's stricter yellow/gold/cream test): the greeting
    banner (white headline, marigold-orange border), the whole Chisme page, light + dark, and every season SVG
  • Día de Muertos logo art (v49.15): a candle + a calavera beside the Chisme bubble in the phone top bar (390 + 320 px) and
    the desktop hero; only in the season; small; clear of the bubble, the tagline and Tía; no yellow in the SVGs or the CSS
    flame; the flame flickers, and stops under Reduce motion (system or Chisme's own); the desktop hero doesn't re-flow
  • v49.15.3 smooth bars: the top bar, the chip row and the tab bar slide AND fade (transform + opacity, 250–300 ms, an
    ease-out curve); at the start of the slide-in they're still out of sight (no snap), half-way they're part-way in with
    the chip row glued under the top bar, at the end they're fully in; turning around mid-slide never jumps or flickers;
    the new-stories pill, the sync pill and the Terms bar ride on `translate` with the same timing; the status-bar strip
    (.fb-safe) stays put in the bar's colour; Reduce motion = no sliding, only a short fade
  • v49.15.3 the phone top bar has the city skyline (the old header's art) behind its buttons, no ¿Oyistes?, the same height;
    the tab bar is Chisme · ¿Y la dieta? (Ofrendas in the Día de Muertos season) · Juegos · Tía (v49.16; Weather is a Chisme chip)
  • v49.15.3 (temporary) the Muertos top bar keeps the skyline's drifting helicopter and lit (marigold-orange) window squares,
    the papel picado strip, and no ¿Oyistes? in or over it, light + dark
Screenshots: SHOTS (default /workspace/chisme-navbar-shots/): top, scrolled, scroll-up, tia-open, dark, chismetv, muertos, weather,
desktop-1440, muertos-logo (phone), muertos-logo-desktop, top-skyline, top-skyline-dark, top-muertos, top-muertos-dark, tabbar-offseason, tabbar-season,
slide-in-1-start, slide-in-2-mid, slide-in-3-end.
    URL=http://127.0.0.1:8297/ REF_URL=http://127.0.0.1:8298/ ./venv/bin/python fb_nav_test.py"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
import ast
_src = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_no_yellow_test.py")).read())
STRICT_YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
URL = os.environ.get("URL", "http://localhost:8211/").rstrip("/") + "/"
REF = (os.environ.get("REF_URL") or "").rstrip("/")
OUT = os.environ.get("SHOTS", "/workspace/chisme-navbar-shots"); os.makedirs(OUT, exist_ok=True)
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

BARS = """() => { const R = (e) => { const r = e.getBoundingClientRect(); return { t: r.top, b: r.bottom, l: r.left, r: r.right, h: r.height }; };
  const top = document.querySelector('#fbtop'), tabs = document.querySelector('#tabs');
  return { top: R(top), tabs: R(tabs), vh: innerHeight, vw: innerWidth, y: scrollY, hide: document.documentElement.classList.contains('fb-hide'),
    topShown: R(top).t > -1 && R(top).b > 40, tabsShown: R(tabs).b <= innerHeight + 1 && R(tabs).t < innerHeight - 40,
    topGone: R(top).b <= 1, tabsGone: R(tabs).t >= innerHeight - 1 }; }"""
SETTLE = 480   # v49.15.3: the slide is 280 ms

async def scroll_to(pg, y, step=None):
    """scrolls like a finger would: in steps, one frame apart (the nav reads the scroll once per animation frame)"""
    cur = await pg.evaluate("scrollY")
    step = step or max(1, abs(y - cur))
    while abs(y - cur) > 0:
        cur = cur + max(-step, min(step, y - cur))
        await pg.evaluate("(y) => new Promise((ok) => { window.scrollTo({ top: y, behavior: 'instant' }); requestAnimationFrame(() => requestAnimationFrame(ok)); })", cur)
    await pg.wait_for_timeout(SETTLE)
    return await pg.evaluate(BARS)

async def new_page(b, w, h, theme="light", season="off", tab="chisme", dev=None, reduced=None):
    ctx = await b.new_context(viewport={"width": w, "height": h}, color_scheme=theme, reduced_motion=reduced or "no-preference", **(dev or {}))
    await ctx.add_init_script(f"try{{localStorage.setItem('chisme-season-pin','{season}');localStorage.setItem('chisme-theme','{theme}');"
                              f"localStorage.setItem('chisme-default-tab','{tab}');localStorage.setItem('chisme-location-setup','1')}}catch(e){{}}")
    await ctx.add_init_script(QUIET)
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page()
    return ctx, pg

async def ready(pg, url=URL):
    await pg.goto(url); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    await pg.wait_for_function("() => document.querySelectorAll('#mix-list .mix-item, #near-list .story').length >= 6", timeout=90000)
    await pg.evaluate("() => { const s = document.querySelector('#sync'); if (s) s.dataset.state = 'done'; }")   # the 'Updated' toast, out of the pictures
    await pg.wait_for_timeout(900)

YELLOWISH = """(sels) => { const out = []; const yellow = (c) => { const m = c.match(/rgba?\\(([\\d.]+), ([\\d.]+), ([\\d.]+)(?:, ([\\d.]+))?/); if (!m) return false;
    const [r, g, b, a] = [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]; return a > .2 && r > 180 && g > 150 && b < 110 && Math.abs(r - g) < 90; };
  for (const s of sels) for (const e of document.querySelectorAll(s)) { const cs = getComputedStyle(e);
    for (const p of ['color', 'backgroundColor', 'borderTopColor', 'outlineColor']) if (yellow(cs[p]) && (p !== 'borderTopColor' || parseFloat(cs.borderTopWidth) > 0)) out.push(s + ' ' + p + ' ' + cs[p]);
    for (const g of [cs.backgroundImage, cs.boxShadow]) if (g && g !== 'none' && (g.match(/rgba?\\([^)]*\\)/g) || []).some(yellow)) out.push(s + ' gradient/shadow ' + g.slice(0, 60)); }
  return out; }"""

SKY = """() => { const top = document.querySelector('#fbtop'), sky = top.querySelector('svg.fb-sky'), tb = top.getBoundingClientRect();
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const shapes = sky ? [...sky.querySelectorAll('g[class^="sky-"]')].filter((g) => getComputedStyle(g).display !== 'none') : [];
  const s = sky && R(sky), cs = sky && getComputedStyle(sky), win = shapes[0] && shapes[0].querySelector('.sky-win');
  const btns = ['#settings-btn', '#fb-menu'].map((q) => top.querySelector(q)).filter(Boolean);   // v49.16: the bubble + ☰
  const hits = btns.map((x) => { const r = R(x), at = document.elementFromPoint((r.l + r.r) / 2, (r.t + r.b) / 2); return !!at && (at === x || x.contains(at)); });
  const rgb = (c) => (String(c).match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
  const mix = (a, b, o) => a.map((v, i) => v * o + b[i] * (1 - o));
  const bg = rgb(getComputedStyle(top).backgroundColor), bgGrad = getComputedStyle(top).backgroundImage;
  const base = bgGrad && bgGrad !== 'none' ? rgb((bgGrad.match(/rgba?\\([^)]*\\)/g) || []).pop() || '') : bg;
  const fill = cs ? rgb(cs.fill) : [0, 0, 0], op = cs ? +cs.opacity : 0, seen = mix(fill, base, op);
  return { sky: !!sky, which: top.dataset.skyline, shown: shapes.reduce((n, g) => n + g.querySelectorAll('path').length, 0),
    inBar: !!s && s.t >= tb.top - 0.5 && s.b <= tb.bottom + 0.5 && s.w >= tb.width - 1, barH: Math.round(tb.height),
    oyistes: /Oyistes/i.test(top.textContent), tag: !!top.querySelector('.fb-tag'), under: hits.length === 2 && hits.every(Boolean), hits,
    fills: [cs && cs.fill, win && getComputedStyle(win).fill].filter(Boolean), fillDiff: Math.round(Math.max(...seen.map((v, i) => Math.abs(v - base[i])))) }; }"""
def sky_yellow(fills):
    import re
    for f in fills:
        m = re.findall(r"[\d.]+", f)
        if len(m) >= 3:
            r, g, b_ = map(float, m[:3])
            if r > 180 and g > 150 and b_ < 110 and abs(r - g) < 90: return True
    return False
# the bars' transitions: [property, seconds, timing function] per element
TRANS = """() => { const out = {}; const sec = (x) => x.trim().endsWith('ms') ? parseFloat(x) / 1000 : parseFloat(x);
  for (const [k, q] of [['top', '#fbtop'], ['tabs', '#tabs'], ['chips', '#view-chisme .mq-chips'], ['pill', '#news-pill'], ['sync', '#sync'], ['terms', '.terms-bar']]) {
    const e = document.querySelector(q); if (!e) continue; const cs = getComputedStyle(e);
    const p = cs.transitionProperty.split(','), d = cs.transitionDuration.split(','), f = cs.transitionTimingFunction.split(/,(?![^(]*\\))/);
    out[k] = { list: p.map((x, i) => [x.trim(), sec(d[i % d.length]), (f[i % f.length] || '').trim()]) }; }
  return out; }"""
FRAME = """() => { const R = (q) => { const e = document.querySelector(q); if (!e) return null; const r = e.getBoundingClientRect(); return { t: +r.top.toFixed(1), b: +r.bottom.toFixed(1), o: +(+getComputedStyle(e).opacity).toFixed(3) }; };
  return { top: R('#fbtop'), tabs: R('#tabs'), chips: R('#view-chisme .mq-chips'), vh: innerHeight }; }"""
# shows the bars and freezes their CSS transitions at the very start (so the test can step through the slide-in)
SHOW_PAUSED = """() => { window.__chismeNav.show(); const els = ['#fbtop', '#tabs', '#view-chisme .mq-chips'].map((q) => document.querySelector(q));
  getComputedStyle(els[0]).transform;
  const an = document.getAnimations().filter((a) => a.effect && els.includes(a.effect.target) && a.transitionProperty);
  an.forEach((a) => { a.pause(); a.currentTime = 0; }); window.__fbAn = an;
  return an.map((a) => a.effect.target.id || a.effect.target.className.split(' ')[0]).map((t, i) => t + ':' + an[i].transitionProperty + ':' + Math.round(an[i].effect.getComputedTiming().duration)); }"""
SEEK = "(ms) => { for (const a of window.__fbAn) a.currentTime = Math.min(ms, a.effect.getComputedTiming().duration); }"

async def motion(b, bname, dev, shots):
    print(f"\n== smooth bars ({bname})")
    ctx, pg = await new_page(b, 390, 844, dev=dev); await ready(pg)
    tr = await pg.evaluate(TRANS)
    def has(k, prop):
        return [x for x in tr.get(k, {"list": []})["list"] if x[0] == prop]
    for k, name in (("top", "top bar"), ("tabs", "tab bar"), ("chips", "chip row")):
        t, o = has(k, "transform"), has(k, "opacity")
        ok = t and o and all(0.25 <= x[1] <= 0.30 for x in t + o) and all(x[2] not in ("linear", "ease-in") and ("ease-out" in x[2] or "cubic-bezier" in x[2]) for x in t + o)
        check(bool(ok), f"{bname}: the {name} slides and fades: transform + opacity transitions, 250–300 ms, ease-out {t + o}")
    same = {x[1] for k in ("top", "tabs", "chips") for x in has(k, "transform") + has(k, "opacity")} | {x[1] for k in ("pill", "sync", "terms") for x in has(k, "translate")}
    check(len(same) == 1 and all(has(k, "translate") for k in ("pill", "sync", "terms")),
          f"{bname}: the new-stories pill, the sync pill and the Terms bar move on `translate` with the bars' exact timing (one duration for all: {sorted(same)})")
    safe = await pg.evaluate("""() => { const s = document.querySelector('.fb-safe'), t = document.querySelector('#fbtop'); if (!s) return null; const cs = getComputedStyle(s);
      return { pos: cs.position, top: s.getBoundingClientRect().top, z: +cs.zIndex, tz: +getComputedStyle(t).zIndex, bg: cs.backgroundColor, bar: getComputedStyle(t).backgroundColor, tr: cs.transitionDuration, h: cs.height }; }""")
    check(safe and safe["pos"] == "fixed" and safe["top"] == 0 and safe["z"] > safe["tz"] and safe["bg"] == safe["bar"] and safe["tr"] == "0s",
          f"{bname}: the status-bar strip (.fb-safe, safe-area-inset-top tall) is fixed at the top, over the bar, in the bar's colour, and doesn't move (the bar slides under it) {safe}")
    # hide them, then step through the slide-in
    await scroll_to(pg, 1200, 60)
    hid = await pg.evaluate(FRAME)
    check(hid["top"]["b"] <= 0.5 and hid["top"]["o"] == 0 and hid["tabs"]["t"] >= hid["vh"] - 0.5 and hid["tabs"]["o"] == 0 and hid["chips"]["b"] <= 0.5 and hid["chips"]["o"] == 0,
          f"{bname}: hidden: the top bar, the chip row and the tab bar are off screen and faded out {hid}")
    an = await pg.evaluate(SHOW_PAUSED)
    check(len(an) >= 6, f"{bname}: showing them starts CSS transitions on all three (transform + opacity each) {an}")
    f0 = await pg.evaluate(FRAME)
    check(f0["top"]["b"] <= 0.5 and f0["top"]["o"] <= 0.02 and f0["tabs"]["t"] >= f0["vh"] - 0.5 and f0["tabs"]["o"] <= 0.02 and f0["chips"]["b"] <= 0.5,
          f"{bname}: at the start of the slide-in the bars are still out of sight (not already half-way in: no snap) {f0}")
    if shots: await pg.screenshot(path=f"{OUT}/slide-in-1-start.png")
    durs = [int(x.rsplit(":", 1)[1]) for x in an]; D = max(durs) if durs else 280
    await pg.evaluate(SEEK, D * 0.3)
    fm = await pg.evaluate(FRAME)
    check(-hid["top"]["t"] > -fm["top"]["t"] > 0 and 0.05 < fm["top"]["o"] < 0.99 and hid["tabs"]["t"] > fm["tabs"]["t"] > fm["vh"] - 70 and 0.05 < fm["tabs"]["o"] < 0.99,
          f"{bname}: mid-slide the bars are part-way in and part-faded (top bar at {fm['top']['t']}, opacity {fm['top']['o']}; tab bar at {fm['tabs']['t']})")
    check(abs(fm["chips"]["t"] - fm["top"]["b"]) <= 1.5 and abs(fm["chips"]["o"] - fm["top"]["o"]) < 0.02,
          f"{bname}: mid-slide the chip row is glued right under the top bar (no gap, no overlap: {fm['chips']['t']} vs {fm['top']['b']}), same fade")
    if shots: await pg.screenshot(path=f"{OUT}/slide-in-2-mid.png")
    await pg.evaluate("() => { for (const a of window.__fbAn) a.finish(); }")
    fe = await pg.evaluate(FRAME)
    check(fe["top"]["t"] == 0 and fe["top"]["o"] == 1 and abs(fe["tabs"]["b"] - fe["vh"]) < 0.5 and fe["tabs"]["o"] == 1 and abs(fe["chips"]["t"] - fe["top"]["b"]) <= 1,
          f"{bname}: at the end the bars are fully in and opaque, the chip row right under the top bar {fe}")
    if shots: await pg.screenshot(path=f"{OUT}/slide-in-3-end.png")
    # turning around mid-slide: no jump, no flicker
    SAMPLE = """(n) => new Promise((ok) => { const out = []; const f = () => { const R = (q) => { const e = document.querySelector(q), r = e.getBoundingClientRect(); return [r.top, r.bottom, +getComputedStyle(e).opacity]; };
      out.push({ top: R('#fbtop'), tabs: R('#tabs'), chips: R('#view-chisme .mq-chips') }); if (out.length < n) requestAnimationFrame(f); else ok(out); }; requestAnimationFrame(f); })"""
    for flip in (60, 120, 200):
        await pg.evaluate("window.__chismeNav.show()"); await pg.wait_for_timeout(SETTLE)
        await pg.evaluate("window.__chismeNav.hide()"); await pg.wait_for_timeout(flip)
        await pg.evaluate("window.__chismeNav.show()")
        fr = await pg.evaluate(SAMPLE, 26)
        tops = [x["top"][0] for x in fr]; ops = [x["top"][2] for x in fr]; tb = [x["tabs"][0] for x in fr]
        mono = all(b2 >= a2 - 0.5 for a2, b2 in zip(tops, tops[1:])) and all(b2 >= a2 - 0.01 for a2, b2 in zip(ops, ops[1:])) and all(b2 <= a2 + 0.5 for a2, b2 in zip(tb, tb[1:]))
        jump = max(abs(b2 - a2) for a2, b2 in zip(tops, tops[1:]))
        glued = all(abs(x["chips"][0] - x["top"][1]) <= 1.5 for x in fr)
        check(mono and jump < 45 and glued and tops[-1] == 0 and ops[-1] == 1,
              f"{bname}: hide then show again after {flip} ms: they turn around smoothly (only towards shown, biggest step {jump:.0f} px, the chip row stays glued, ends fully in)")
    # fast flicking: down/up/down/up a few px at a time must not leave them half-way or blinking
    await pg.evaluate("window.__chismeNav.show()"); await pg.wait_for_timeout(SETTLE)
    y0 = await pg.evaluate("scrollY")
    for k in range(6):
        await pg.evaluate("(y) => new Promise((ok) => { scrollTo({ top: y, behavior: 'instant' }); requestAnimationFrame(() => ok()); })", y0 + (40 if k % 2 == 0 else 0))
        await pg.wait_for_timeout(35)
    r = await scroll_to(pg, y0 + 60, 20)
    end = await pg.evaluate(FRAME)
    check(r["hide"] and end["top"]["b"] <= 0.5 and end["top"]["o"] == 0, f"{bname}: after flicking up and down fast, they settle cleanly (hidden after the last scroll down, nothing left half-way) {end['top']}")
    # the new-stories pill rides along
    await pg.evaluate("window.__chismeNav.show()"); await pg.wait_for_timeout(SETTLE)
    pill = await pg.evaluate("""async () => { const p = document.querySelector('#news-pill'), h = document.documentElement; p.hidden = false; p.style.transition = 'none';   // (the end values, not mid-slide)
      const shown = getComputedStyle(p).translate; h.classList.add('fb-hide'); const hid = getComputedStyle(p).translate, tr = getComputedStyle(p, null).getPropertyValue('top');
      h.classList.remove('fb-hide'); p.style.transition = ''; p.hidden = true; return { shown, hid }; }""")
    check(pill["shown"] in ("none", "0px", "0px 0px") and pill["hid"] not in ("none", "0px", "0px 0px"), f"{bname}: the 'N new stories' pill moves up with the top bar on `translate` {pill}")
    await ctx.close()

async def phone(b, bname, dev, shots):
    print(f"\n== phone 390x844 ({bname})")
    ctx, pg = await new_page(b, 390, 844, dev=dev)
    await ready(pg)
    r = await pg.evaluate(BARS)
    check(r["topShown"] and r["tabsShown"] and not r["hide"] and r["top"]["t"] == 0 and abs(r["tabs"]["b"] - r["vh"]) < 1,
          f"{bname}: at the top both bars show (top bar at 0, tab bar on the bottom edge) {r['top']} {r['tabs']}")
    lay = await pg.evaluate("""() => { const v = document.querySelector('#views').getBoundingClientRect(), t = document.querySelector('#fbtop').getBoundingClientRect(),
        cs = getComputedStyle(document.body), tabs = document.querySelector('#tabs');
      return { viewsTop: v.top, topB: t.bottom, padT: parseFloat(cs.paddingTop), padB: parseFloat(cs.paddingBottom), tabsH: tabs.offsetHeight,
        varTop: getComputedStyle(document.documentElement).getPropertyValue('--tabs-h').trim(), fbtopH: document.querySelector('#fbtop').offsetHeight,
        header: getComputedStyle(document.querySelector('header.topbar')).display, fab: getComputedStyle(document.querySelector('#tia-btn')).display,
        set: document.querySelector('#settings-btn').closest('#fbtop') ? 'top bar' : 'elsewhere', ids: ['settings-btn', 'sync', 'tabs', 'tia-btn', 'tia', 'settings'].every((i) => document.getElementById(i)) }; }""")
    check(lay["viewsTop"] >= lay["topB"] - 0.5 and lay["padT"] == lay["fbtopH"] and lay["varTop"] == f"{lay['fbtopH']}px",
          f"{bname}: the page starts under the top bar (body padding = --tabs-h = the bar's {lay['fbtopH']} px; content top {lay['viewsTop']:.0f})")
    check(lay["padB"] >= lay["tabsH"], f"{bname}: the page has room for the tab bar at the bottom (padding {lay['padB']:.0f} ≥ bar {lay['tabsH']})")
    check(lay["header"] == "none" and lay["fab"] == "none" and lay["set"] == "top bar" and lay["ids"],
          f"{bname}: the skyline header and the floating Tía are off on phones; #settings-btn sits in the top bar; every id is still there {lay}")
    tabs = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map((t) => { const r = t.getBoundingClientRect(); return { v: t.dataset.view || t.id, w: r.width, h: r.height, b: r.bottom, l: t.textContent.trim() }; })")
    check(len(tabs) == 4 and all(t["w"] >= 44 and t["h"] >= 44 for t in tabs), f"{bname}: 4 tabs on the bottom bar, each a 44 px+ target {[(t['v'], round(t['w']), round(t['h'])) for t in tabs]}")
    check([t["v"] for t in tabs] == ["chisme", "antojos", "juegos", "tab-tia"] and "¿Y la dieta?" in tabs[1]["l"] and "Tía" in tabs[3]["l"] and len({round(t["b"]) for t in tabs}) == 1,
          f"{bname}: the tab bar reads Chisme · ¿Y la dieta? · Juegos · Tía (v49.16) {[t['l'] for t in tabs]}")
    sky = await pg.evaluate(SKY)
    check(sky["sky"] and sky["shown"] > 0 and sky["inBar"] and not sky["oyistes"] and not sky["tag"] and sky["barH"] <= 60,
          f"{bname}: the top bar has the city skyline behind its buttons ({sky['which']} skyline, {sky['shown']} shapes, inside the {sky['barH']} px bar), no ¿Oyistes? {sky}")
    check(sky["under"], f"{bname}: the skyline sits behind the bubble and ☰ (they're still what you tap) {sky['hits']}")
    if shots: await pg.screenshot(path=f"{OUT}/top.png"); await pg.screenshot(path=f"{OUT}/top-skyline.png", clip={"x": 0, "y": 0, "width": 390, "height": 140})
    if shots: await pg.screenshot(path=f"{OUT}/tabbar-offseason.png", clip={"x": 0, "y": 844 - 110, "width": 390, "height": 110})
    CHIPS = "(() => { const c = document.querySelector('#view-chisme .mq-chips'), r = c.getBoundingClientRect(), t = document.querySelector('#fbtop').getBoundingClientRect(); return { t: r.top, b: r.bottom, vis: getComputedStyle(c).visibility, under: t.bottom, hit: document.elementFromPoint(innerWidth / 2, (r.top + r.bottom) / 2)?.closest('.mq-chips') === c }; })()"
    c = await pg.evaluate(CHIPS)
    check(c["vis"] == "visible" and c["t"] >= c["under"] - 1 and c["hit"], f"{bname}: at the very top the chip row shows, under the top bar {c}")
    # down 40 px: still inside the 60 px zone → bars stay
    r = await scroll_to(pg, 40, 10)
    check(r["topShown"] and r["tabsShown"], f"{bname}: 40 px down (under 60 px) the bars stay")
    r = await scroll_to(pg, 1200, 60)
    check(r["hide"] and r["topGone"] and r["tabsGone"], f"{bname}: after scrolling down (1200 px) both bars are off screen {r['top']} {r['tabs']}")
    if shots: await pg.screenshot(path=f"{OUT}/scrolled.png")
    c = await pg.evaluate(CHIPS)
    check(c["b"] <= 1 and c["vis"] == "hidden", f"{bname}: Chisme's All · News · Sports · Events chip row slides away with the top bar on scroll down (bottom {c['b']:.1f}, {c['vis']})")
    r = await scroll_to(pg, 1196)
    check(r["hide"], f"{bname}: a 4 px nudge up doesn't bring them back (needs 8 px)")
    r = await scroll_to(pg, 1176, 5)
    check(not r["hide"] and r["topShown"] and r["tabsShown"], f"{bname}: a 20 px scroll up brings both bars back")
    if shots: await pg.screenshot(path=f"{OUT}/scroll-up.png")
    c = await pg.evaluate(CHIPS)
    check(abs(c["t"] - lay["fbtopH"]) < 1.5 and c["vis"] == "visible" and c["hit"], f"{bname}: the chip row comes back with the top bar, right under it ({c['t']:.1f}) and tappable")
    r = await scroll_to(pg, 2000, 80); r2 = await scroll_to(pg, 30)
    check(r["hide"] and not r2["hide"] and r2["topShown"], f"{bname}: hidden mid-page, then back at the top they show")
    # the very bottom: nothing hides under the tab bar (bars shown at the end of the page)
    await scroll_to(pg, await pg.evaluate("document.documentElement.scrollHeight - innerHeight"), 400)
    await pg.evaluate("window.__chismeNav.show()"); await pg.wait_for_timeout(SETTLE)
    end = await pg.evaluate("""() => { const t = document.querySelector('#tabs').getBoundingClientRect();
      const low = Math.max(...[...document.body.children].filter((e) => e.getClientRects().length && !['fixed', 'absolute'].includes(getComputedStyle(e).position) && e.tagName !== 'DIALOG' && e.tagName !== 'SCRIPT').map((e) => e.getBoundingClientRect().bottom));
      return { vb: low, tt: t.top }; }""")
    check(end["vb"] <= end["tt"] + 1, f"{bname}: at the end of the page the last of the content clears the tab bar ({end['vb']:.0f} ≤ {end['tt']:.0f})")
    # tabs switch
    back = []
    for v in ("weather", "antojos", "juegos", "chisme"):   # v49.16: Weather is the Chisme tab's Weather chip (the Chisme tab stays lit)
        y0 = min(900, await pg.evaluate("document.documentElement.scrollHeight - innerHeight"))
        await scroll_to(pg, y0, 100); await scroll_to(pg, max(0, y0 - 30), 6)   # a little scroll up shows the bar, then tap
        await pg.click('.view.active .mq-chip[data-go="weather"]' if v == "weather" else f'#tabs .tab[data-view="{v}"]')
        await pg.wait_for_timeout(700)
        st = await pg.evaluate(f"""() => ({{ cur: document.querySelector('#tabs .tab[aria-current="page"]')?.dataset.view, active: document.querySelector('#view-{v}').classList.contains('active'),
            hide: document.documentElement.classList.contains('fb-hide') }})""")
        lit = "chisme" if v == "weather" else v
        check(st["cur"] == lit and st["active"], f"{bname}: the {v} {'chip' if v == 'weather' else 'tab'} opens #view-{v} and the {lit} tab lights up {st}")
        back.append(not st["hide"])
        if v == "weather" and shots: await pg.evaluate("scrollTo(0,0)"); await pg.wait_for_timeout(500); await pg.screenshot(path=f"{OUT}/weather.png")
        # any sticky sub-filter row on this tab must go away with the bars too (nothing stays stuck at the top)
        ymax = await pg.evaluate("document.documentElement.scrollHeight - innerHeight")
        if ymax > 400:
            await scroll_to(pg, 0); r = await scroll_to(pg, min(ymax, 1400), 80)
            stuck = await pg.evaluate(f"""() => [...document.querySelectorAll('#view-{v} *')].filter((e) => {{ const cs = getComputedStyle(e); if (!['sticky', 'fixed'].includes(cs.position) || cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return false;
                const r = e.getBoundingClientRect(); return r.height > 0 && r.bottom > 1 && r.top < 90; }}).map((e) => (e.className || e.tagName) + '@' + Math.round(e.getBoundingClientRect().top))""")
            check(r["hide"] and not stuck, f"{bname}: {v}: scrolled down with the bars away, no sticky row is left stuck at the top {stuck[:3]}")
    check(all(back), f"{bname}: switching tabs brings the bars back {back}")
    # v49.16: the Tía tab → chat; ☰ and the Chisme bubble → Settings
    await scroll_to(pg, 0)
    await pg.click("#tab-tia"); await pg.wait_for_timeout(600)
    t = await pg.evaluate("({ tia: document.querySelector('#tia').open, menu: document.querySelector('#tia-menu').open })")
    check(t["tia"] and not t["menu"], f"{bname}: the Tía tab opens Tía's chat {t}")
    if shots: await pg.screenshot(path=f"{OUT}/tia-open.png")
    await pg.click("#tia-close"); await pg.wait_for_timeout(400)
    foc = await pg.evaluate("document.activeElement && document.activeElement.id")
    check(foc == "tab-tia", f"{bname}: closing her chat puts focus back on her tab ({foc})")
    for sel in ("#fb-menu", "#settings-btn"):
        await pg.click(sel); await pg.wait_for_timeout(500)
        o = await pg.evaluate("document.querySelector('#settings').open")
        check(o, f"{bname}: {sel} opens Settings")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    # what the bars are made of: no yellow
    y = await pg.evaluate(YELLOWISH, ["#fbtop", "#fbtop *", "#tabs", "#tabs *"])
    check(not y, f"{bname}: no yellow on the bars (light) {y[:3]}")
    await ctx.close()

    # reduced motion: no slide, just a short fade (v49.15.3)
    ctx, pg = await new_page(b, 390, 844, dev=dev, reduced="reduce"); await ready(pg)
    tr = await pg.evaluate(TRANS)
    r = await scroll_to(pg, 1000, 100)
    ok = all(not any(p in ("transform", "all") and d > 0 for p, d, _ in t["list"]) and all(d <= 0.15 for p, d, _ in t["list"] if p == "opacity") for t in tr.values())
    check(ok and r["hide"] and r["topGone"], f"{bname}: reduced motion: the bars don't slide (no transform transition), only a short fade of 0.15 s or less {tr}")
    r = await scroll_to(pg, 970, 5)
    check(not r["hide"] and r["top"]["t"] == 0, f"{bname}: reduced motion: scrolling up puts the top bar straight back in place (no slide) {r['top']}")
    await ctx.close()

    for theme, season, name in (("dark", "off", "dark"), ("light", "muertos", "muertos"), ("dark", "muertos", None)):
        ctx, pg = await new_page(b, 390, 844, theme=theme, season=season, dev=dev); await ready(pg)
        y = await pg.evaluate(YELLOWISH, ["#fbtop", "#fbtop *", "#tabs", "#tabs *"])
        bg = await pg.evaluate("[getComputedStyle(document.querySelector('#fbtop')).backgroundColor, getComputedStyle(document.querySelector('#fbtop')).backgroundImage.slice(0, 30), getComputedStyle(document.querySelector('#tabs')).backgroundColor]")
        check(not y, f"{bname}: {theme}{' + Día de Muertos' if season == 'muertos' else ''}: no yellow on the bars {y[:3]} {bg}")
        sky = await pg.evaluate(SKY)
        tag = f"{theme}{' + Día de Muertos' if season == 'muertos' else ''}"
        check(sky["sky"] and sky["shown"] > 0 and not sky["oyistes"] and not sky_yellow(sky["fills"]) and sky["fillDiff"] >= 40,
              f"{bname}: {tag}: the skyline shows in the top bar, stands out from it (colour difference {sky['fillDiff']}) and isn't yellow {sky['fills']}")
        tl = await pg.evaluate("[...document.querySelectorAll('#tabs .tab')].map((t) => (t.dataset.view || t.id) + ':' + t.textContent.trim())")
        want2 = "Ofrendas" if season == "muertos" else "¿Y la dieta?"
        check([x.split(":")[0] for x in tl] == ["chisme", "antojos", "juegos", "tab-tia"] and want2 in tl[1], f"{bname}: {tag}: tab order Chisme · {want2} · Juegos · Tía {tl}")
        if shots and name: await pg.screenshot(path=f"{OUT}/{name}.png")
        if shots and name == "dark": await pg.screenshot(path=f"{OUT}/top-skyline-dark.png", clip={"x": 0, "y": 0, "width": 390, "height": 140})
        if shots and name == "muertos": await pg.screenshot(path=f"{OUT}/tabbar-season.png", clip={"x": 0, "y": 844 - 110, "width": 390, "height": 110})
        await ctx.close()

async def reels(b, bname, dev, shots):
    print(f"\n== ChismeTV ({bname})")
    ctx, pg = await new_page(b, 390, 844, tab="antojos", dev=dev); await ready(pg)
    await pg.wait_for_function("() => { const b = document.querySelector('#fy-start'); return b && !b.disabled; }", timeout=60000)
    await pg.tap("#fy-start"); await pg.wait_for_function("() => document.querySelector('#feed').open", timeout=10000)
    await pg.wait_for_function("() => document.querySelector('#feed-scroll .vf-slide .vf-share')", timeout=60000)
    try: await pg.wait_for_function("() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur]; return s && s.classList.contains('vf-playing'); }", timeout=15000)
    except Exception: pass
    await pg.wait_for_timeout(1200)
    r = await pg.evaluate("""() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur || 0];
      const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
      const hit = (a, b) => a.l < b.r - .5 && b.l < a.r - .5 && a.t < b.b - .5 && b.t < a.b - .5;
      const btns = [...s.querySelectorAll('.vf-act button, .vf-rail button, .vf-rail a, .vf-play, #feed-close, #feed-sound')].filter((x) => { const r = x.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(x).visibility !== 'hidden'; });
      const bars = [document.querySelector('#fbtop'), document.querySelector('#tabs')].map(R);
      const out = btns.map((x) => { const r = R(x), cx = (r.l + r.r) / 2, cy = (r.t + r.b) / 2, at = document.elementFromPoint(cx, cy);
        return { c: x.className || x.id, b: Math.round(innerHeight - r.b), own: !!at && (at === x || x.contains(at)), bar: bars.some((q) => hit(q, r) && q.b > 0 && q.t < innerHeight) }; });
      const act = s.querySelector(s.classList.contains('vf-playing') ? '.vf-act' : '.vf-rail');
      return { out, playing: s.classList.contains('vf-playing'), feedOpen: document.documentElement.classList.contains('feed-open'),
        tabsTop: R(document.querySelector('#tabs')).t, topB: R(document.querySelector('#fbtop')).b, vh: innerHeight, colB: act ? Math.round(innerHeight - R(act).b) : null }; }""")
    bad = [o for o in r["out"] if not o["own"] or o["bar"]]
    check(r["out"] and not bad, f"{bname}: ChismeTV: every Like / Share / control button is on top where you tap it, nothing of the nav over it ({len(r['out'])} buttons, column {r['colB']} px from the bottom, playing={r['playing']}) {bad[:3]}")
    check(r["feedOpen"] and r["tabsTop"] >= r["vh"] - 1 and r["topB"] <= 1, f"{bname}: ChismeTV: the top bar and the tab bar are tucked away under the full-screen video")
    if shots: await pg.screenshot(path=f"{OUT}/chismetv.png")
    await pg.tap("#feed-close"); await pg.wait_for_function("() => !document.querySelector('#feed').open", timeout=5000); await pg.wait_for_timeout(500)
    r = await pg.evaluate(BARS)
    check(r["topShown"] and r["tabsShown"], f"{bname}: back from ChismeTV, both bars are back")
    await ctx.close()

DESK = """() => { const R = (s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  return { dk: document.documentElement.classList.contains('dk'), fbtop: getComputedStyle(document.querySelector('#fbtop') || document.body).display, hide: document.documentElement.classList.contains('fb-hide'),
    rects: { tabs: R('#tabs'), inner: R('#tabs .tabs-inner'), logo: R('.dk-logo'), tab1: R('#tabs .tab[data-view="chisme"]'), tab4: R('#tabs .tab[data-view="juegos"]'), set: R('#settings-btn'), get: R('#dk-get'),
      fab: R('#tia-btn'), views: R('#views'), hero: R('.dk-hero'), side: R('.dk-side') },
    setIn: !!document.querySelector('.dk-set-slot #settings-btn'), syncIn: !!document.querySelector('.dk-sync-slot #sync'), varTop: getComputedStyle(document.documentElement).getPropertyValue('--tabs-h').trim(),
    bodyPad: [getComputedStyle(document.body).paddingTop, getComputedStyle(document.body).paddingBottom], tabsBg: getComputedStyle(document.querySelector('#tabs')).backgroundColor }; }"""

async def desktop(b, shots):
    print("\n== desktop 1440x900 (must be unchanged)")
    async def grab(url):
        ctx, pg = await new_page(b, 1440, 900); await ready(pg, url + "/" if not url.endswith("/") else url); await pg.wait_for_timeout(800)
        d = await pg.evaluate(DESK)
        await pg.evaluate("scrollTo(0, 1500)"); await pg.wait_for_timeout(500)
        d2 = await pg.evaluate(DESK)
        await pg.evaluate("scrollTo(0, 1400)"); await pg.wait_for_timeout(400)
        return ctx, pg, d, d2
    ctx, pg, d, d2 = await grab(URL)
    check(d["dk"] and d["fbtop"] == "none" and d["setIn"] and d["syncIn"] and d["rects"]["tabs"][1] == 0 and d["rects"]["fab"],
          f"{bname_d}: desktop mode, no phone top bar, the nav on top with Settings + the sync chip in it, the floating Tía {d['rects']['tabs']} fab={d['rects']['fab']}")
    check(not d2["hide"] and d2["rects"]["tabs"][1] == 0, f"{bname_d}: scrolling on desktop doesn't hide the nav")
    if shots: await pg.evaluate("scrollTo(0,0)"); await pg.wait_for_timeout(400); await pg.screenshot(path=f"{OUT}/desktop-1440.png")
    await ctx.close()
    if REF:
        ctx, pg, r, r2 = await grab(REF)
        cut = lambda k, v: v[:3] if v and k in ("views", "side") else v   # (the page column's height is the news of the moment)
        same = {k: (d["rects"][k], r["rects"][k]) for k in d["rects"] if cut(k, d["rects"][k]) != cut(k, r["rects"][k])}
        check(not same, f"{bname_d}: same nav / logo / tabs / Settings / Get the app / Tía / page column / hero / sidebar as the base build {same}")
        for k in ("varTop", "bodyPad", "tabsBg", "setIn", "syncIn"):
            check(d[k] == r[k], f"{bname_d}: {k} as on the base build ({d[k]} vs {r[k]})")
        await ctx.close()
bname_d = "chromium"

DECO = """() => { const R = (e) => { if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const one = (root) => { const v = root.querySelector('.mq-vela'), k = root.querySelector('.mq-skull'), f = v && v.querySelector('.mq-flame');
    const imgs = [...root.querySelectorAll('.mq-deco img')];
    return { vela: R(v), skull: R(k), flame: R(f), anim: f ? getComputedStyle(f).animationName : null, dur: f ? getComputedStyle(f).animationDuration : null,
      hidden: [v, k].every((e) => e && e.getAttribute('aria-hidden') === 'true'), loaded: imgs.length === 2 && imgs.every((i) => i.complete && i.naturalWidth > 0) }; };
  const top = document.querySelector('#fbtop'), hero = document.querySelector('#dk-hero-t');
  return { season: document.documentElement.dataset.season || '', phone: one(top), bar: R(top), bubble: R(top.querySelector('#settings-btn')), tag: R(top.querySelector('.fb-tag')),
    right: R(top.querySelector('.fb-right')), tia: R(top.querySelector('#fb-menu')),   // v49.16: ☰ (Tía left the top bar)
    hero: hero ? one(hero) : null, heroBox: R(hero), heroQ: R(hero && hero.querySelector('.dk-hero-q')), heroLogo: R(hero && hero.querySelector('.dk-hero-logo')) }; }"""
SVG_YELLOW = """async () => { const out = {}; const yellow = (r, g, b) => r > 180 && g > 150 && b < 110 && Math.abs(r - g) < 90;
  for (const n of ['vela', 'calavera']) { const t = await (await fetch('/static/season/' + n + '.svg')).text();
    out[n] = [...t.matchAll(/#([0-9a-f]{6}|[0-9a-f]{3})\\b/gi)].map((m) => m[1]).filter((h) => { const x = h.length === 3 ? h.replace(/./g, '$&$&') : h;
      return yellow(parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16)); }); }
  return out; }"""
def hit(a, b, pad=0):
    return bool(a and b and a["l"] < b["r"] - pad and b["l"] < a["r"] - pad and a["t"] < b["b"] - pad and b["t"] < a["b"] - pad)

STRICT_SCAN = "(sel) => { " + STRICT_YELLOW_JS + r""" const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const bad = []; let n = 0;
  for (const e of document.querySelectorAll(sel)) { if (!e.getClientRects().length || ['IMG', 'CANVAS', 'VIDEO', 'IFRAME', 'PICTURE', 'SOURCE'].includes(e.tagName) || e.closest('.leaflet-tile-pane')) continue; n++;
    const cs = getComputedStyle(e);
    const props = { bg: cs.backgroundColor, gradient: cs.backgroundImage, text: cs.color, glow: cs.boxShadow, shadow: cs.textShadow, outline: parseFloat(cs.outlineWidth) > 0 ? cs.outlineColor : '',
      border: [cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor, cs.borderLeftColor].filter((c, i) => parseFloat([cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth][i]) > 0).join(' ') };
    for (const [k, v] of Object.entries(props)) if (rgb(v).some(yellow)) bad.push(((e.id ? '#' + e.id : '') + '.' + [...e.classList].join('.') + ' <' + e.tagName.toLowerCase() + '>').slice(0, 50) + ' ' + k + ' ' + String(v).slice(0, 50)); }
  return { n, bad }; }"""
SVG_STRICT = "async (names) => { " + STRICT_YELLOW_JS + r""" const out = {};
  for (const n of names) { const t = await (await fetch('/static/season/' + n + '.svg')).text();
    out[n] = [...new Set([...t.matchAll(/#([0-9a-f]{6}|[0-9a-f]{3})\b/gi)].map((m) => m[1]))].filter((h) => { const x = h.length === 3 ? h.replace(/./g, '$&$&') : h;
      return yellow([parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16), 1]); }); }
  return out; }"""

MQ_TOP = """() => { const d = document.documentElement, top = document.querySelector('#fbtop'), sky = top && top.querySelector('svg.fb-sky');
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const shown = (e) => { if (!e || !e.getClientRects().length) return false; for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const cs = getComputedStyle(n);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; } return true; };
  const tb = R(top), inBar = (r) => r.w > 0 && r.h > 0 && r.t >= tb.t - 0.5 && r.b <= tb.b + 0.5 && r.l < tb.r && r.r > tb.l;
  const over = (r) => r.w > 0 && r.h > 0 && r.t < tb.b && r.b > tb.t && r.l < tb.r && r.r > tb.l;
  const oy = []; const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) if (/Oyistes/i.test(n.nodeValue) && shown(n.parentElement)) { const r = R(n.parentElement); if (over(r)) oy.push(n.parentElement.className || n.parentElement.tagName); }
  const g = sky ? [...sky.querySelectorAll('g[class^="sky-"]')].find((x) => getComputedStyle(x).display !== 'none') : null;
  const win = g && g.querySelector('.sky-win'), heli = sky && sky.querySelector('.heli-drift'), hp = heli && heli.querySelector('.heli');
  const pic = top && top.querySelector('.fb-picado');
  return { season: d.dataset.season || '', theme: d.dataset.theme, topText: top ? top.textContent.replace(/\\s+/g, ' ').trim() : '', oy,
    tagline: getComputedStyle(document.querySelector('body > .tagline')).display, header: getComputedStyle(document.querySelector('header.topbar')).display,
    heli: heli ? { shown: shown(heli) && shown(hp), box: R(hp), inBar: inBar(R(hp)), fill: getComputedStyle(hp).fill, anim: getComputedStyle(heli).animationName } : null,
    win: win ? { shown: shown(win), box: R(win), inBar: inBar(R(win)), fill: getComputedStyle(win).fill, op: +getComputedStyle(win).opacity, n: (win.getAttribute('d') || '').split('M').length - 1 } : null,
    sky: sky ? { fill: getComputedStyle(sky).fill, op: +getComputedStyle(sky).opacity } : null,
    picado: pic && shown(pic) ? getComputedStyle(pic).backgroundImage : '' }; }"""

async def muertos_top_bar(b, bname, dev, shots):
    """v49.15.3 (Goonie, temporary): in the Muertos season the phone top bar is the city skyline WITH the drifting helicopter and
    the lit window squares, papel picado + marigold orange (no yellow), and no ¿Oyistes? anywhere in it, light + dark."""
    print(f"\n== Día de Muertos phone top bar: skyline, helicopter, windows, no ¿Oyistes? ({bname})")
    import re
    rgb = lambda c: [float(x) for x in re.findall(r"[\d.]+", str(c))[:3]]
    yellowish = lambda c: (lambda r, g, b_: r > 180 and g > 150 and b_ < 110 and abs(r - g) < 90)(*rgb(c)) if len(rgb(c)) == 3 else False
    for theme in ("light", "dark"):
        ctx, pg = await new_page(b, 390, 844, theme=theme, season="muertos", dev=dev); await ready(pg); await pg.wait_for_timeout(400)
        m = await pg.evaluate(MQ_TOP)
        check(m["season"] == "muertos", f"{bname} {theme}: the Muertos season is on ({m['season']!r})")
        check("Oyistes" not in m["topText"] and not m["oy"] and m["tagline"] == "none" and m["header"] == "none",
              f"{bname} {theme}: no ¿Oyistes? in or over the phone top bar (bar text {m['topText']!r}, over it: {m['oy']}, tagline {m['tagline']}, old header {m['header']})")
        h = m["heli"]
        check(bool(h) and h["shown"] and h["inBar"] and h["box"]["w"] >= 6 and not yellowish(h["fill"]) and rgb(h["fill"]) != rgb(m["sky"]["fill"]),
              f"{bname} {theme}: the helicopter flies over the skyline in Muertos, in the bar, pale against the night sky, not yellow {h}")
        check(bool(h) and h["anim"] == "heli-drift", f"{bname} {theme}: …and it drifts ({h and h['anim']})")
        w = m["win"]
        check(bool(w) and w["shown"] and w["inBar"] and w["n"] >= 10 and w["op"] >= 0.5 and rgb(w["fill"]) == [255, 138, 0] and not yellowish(w["fill"]),
              f"{bname} {theme}: the lit window squares show, marigold orange #FF8A00 (no yellow) {w}")
        check("linear-gradient" in m["picado"] and m["picado"].count("rgb") >= 3 and not any(yellowish(c) for c in re.findall(r"rgba?\([^)]*\)", m["picado"])),
              f"{bname} {theme}: the papel picado strip is still there ({m['picado'][:90]})")
        if shots:
            await pg.screenshot(path=f"{OUT}/top-muertos{'' if theme == 'light' else '-dark'}.png", clip={"x": 0, "y": 0, "width": 390, "height": 140})
        await ctx.close()

async def muertos_no_yellow(b, bname, dev, shots):
    print(f"\n== Día de Muertos: no yellow anywhere ({bname})")
    for theme in ("light", "dark"):
        ctx, pg = await new_page(b, 390, 844, theme=theme, season="muertos", dev=dev); await ready(pg)
        bn = await pg.evaluate("""() => { const t = document.querySelector('.mb-t'), i = document.querySelector('.mb-inner'); if (!t || !t.getClientRects().length) return null;
          const cs = getComputedStyle(t); return { color: cs.color, border: getComputedStyle(i).borderTopColor, shadow: cs.textShadow }; }""")
        check(bn and bn["color"] == "rgb(255, 255, 255)" and bn["border"] == "rgb(255, 138, 0)", f"{bname} {theme}: the Muertos greeting reads in white with a marigold-orange (#FF8A00) border {bn}")
        y = await pg.evaluate(STRICT_SCAN, ".muertos-banner, .muertos-banner *")
        check(y["n"] > 3 and not y["bad"], f"{bname} {theme}: no yellow in the Muertos greeting banner ({y['n']} elements) {y['bad'][:3]}")
        y = await pg.evaluate(STRICT_SCAN, "body, body *")
        check(y["n"] > 100 and not y["bad"], f"{bname} {theme}: Día de Muertos: no yellow / gold / cream anywhere on the page ({y['n']} elements) {y['bad'][:4]}")
        if theme == "light":
            sv = await pg.evaluate(SVG_STRICT, ["papel-picado", "marigold", "sugar-skull", "candle", "calavera", "vela"])
            check(not any(sv.values()), f"{bname}: no yellow in any season SVG {sv}")
        await ctx.close()

async def muertos_logo(b, bname, dev, shots):
    print(f"\n== Día de Muertos logo art ({bname})")
    ctx, pg = await new_page(b, 390, 844, dev=dev); await ready(pg)
    d = await pg.evaluate(DECO)
    check(d["season"] != "muertos" and not d["phone"]["vela"] and not d["phone"]["skull"], f"{bname}: out of season: no candle or calavera in the top bar")
    await ctx.close()
    for w in (390, 320):
        ctx, pg = await new_page(b, w, 844 if w > 320 else 640, season="muertos", dev=dev); await ready(pg)
        d = await pg.evaluate(DECO); p = d["phone"]
        check(d["season"] == "muertos" and p["vela"] and p["skull"] and p["flame"] and p["loaded"] and p["hidden"],
              f"{bname} {w}: Muertos: a candle (with its flame) and a calavera by the Chisme bubble, images loaded, aria-hidden {p['vela']} {p['skull']}")
        if p["vela"] and p["skull"]:
            check(p["vela"]["w"] <= 14 and p["vela"]["h"] <= 30 and p["skull"]["w"] <= 24 and p["skull"]["h"] <= 26,
                  f"{bname} {w}: small: candle {p['vela']['w']:.0f}x{p['vela']['h']:.0f}, calavera {p['skull']['w']:.0f}x{p['skull']['h']:.0f} (bubble {d['bubble']['w']:.0f}x{d['bubble']['h']:.0f})")
            check(p["vela"]["r"] <= d["bubble"]["l"] + 3 and p["skull"]["l"] >= d["bubble"]["r"] - 3 and not d["tag"],
                  f"{bname} {w}: one on each side of the bubble, not over it (v49.15.3: no ¿Oyistes? tag in the bar)")
            check(p["skull"]["r"] < d["right"]["l"] - 8 and not hit(p["flame"], d["tia"]) and not hit(p["vela"], d["tia"]),
                  f"{bname} {w}: clear of ☰ and the bar's right side ({d['right']['l'] - p['skull']['r']:.0f} px to spare)")
            check(all(x["t"] >= d["bar"]["t"] - 0.5 and x["b"] <= d["bar"]["b"] for x in (p["vela"], p["skull"], p["flame"])), f"{bname} {w}: inside the top bar (flame top {p['flame']['t']:.0f})")
        check(p["anim"] == "mq-flame-flicker", f"{bname} {w}: the flame flickers ({p['anim']} {p['dur']})")
        y = await pg.evaluate(YELLOWISH, [".mq-deco", ".mq-deco *"])
        sy = await pg.evaluate(SVG_YELLOW)
        check(not y and not any(sy.values()), f"{bname} {w}: no yellow in the candle, flame or calavera {y[:3]} {sy}")
        await pg.evaluate("document.documentElement.classList.add('reduce-motion')")
        rm = await pg.evaluate("getComputedStyle(document.querySelector('#fbtop .mq-flame')).animationName")
        check(rm == "none", f"{bname} {w}: Chisme's own Reduce motion stops the flicker ({rm})")
        if shots and w == 390: await pg.screenshot(path=f"{OUT}/muertos-logo.png", clip={"x": 0, "y": 0, "width": 390, "height": 140})
        await ctx.close()
    ctx, pg = await new_page(b, 390, 844, season="muertos", dev=dev, reduced="reduce"); await ready(pg)
    rm = await pg.evaluate("getComputedStyle(document.querySelector('#fbtop .mq-flame')).animationName")
    check(rm == "none", f"{bname}: the system's Reduce motion stops the flicker ({rm})")
    await ctx.close()

async def muertos_desktop(b, shots):
    print("\n== Día de Muertos logo art (desktop hero)")
    for w in (1440, 1100):
        seen = {}
        for season in ("off", "muertos"):
            ctx, pg = await new_page(b, w, 900, season=season); await ready(pg); await pg.wait_for_timeout(600)
            seen[season] = d = await pg.evaluate(DECO)
            if season == "muertos":
                h = d["hero"]
                check(h and h["vela"] and h["skull"] and h["flame"] and h["loaded"] and h["hidden"] and not d["phone"]["vela"],
                      f"desktop {w}: Muertos: the hero has a candle and a calavera by the bubble logo (the phone ones are off) {h and h['vela']} {h and h['skull']}")
                if h and h["vela"]:
                    lg, q = d["heroLogo"], d["heroQ"]
                    check(h["vela"]["w"] <= 26 and h["skull"]["w"] <= 50 and h["skull"]["h"] <= 56, f"desktop {w}: small next to the {lg['w']:.0f} px logo (candle {h['vela']['w']:.0f} px, calavera {h['skull']['w']:.0f} px)")
                    check(h["vela"]["l"] < lg["l"] + lg["w"] * .2 and h["skull"]["l"] > lg["l"] + lg["w"] * .75 and not hit(h["skull"], q) and not hit(h["vela"], q),
                          f"desktop {w}: the candle by the bubble's tail (left), the calavera on its right shoulder, clear of ¿Oyistes?")
                    check(h["anim"] == "mq-flame-flicker", f"desktop {w}: the flame flickers ({h['anim']})")
                y = await pg.evaluate(YELLOWISH, [".dk-hero-t-logo .mq-deco", ".dk-hero-t-logo .mq-deco *"])
                check(not y, f"desktop {w}: no yellow in the hero's candle / calavera {y[:3]}")
                if shots and w == 1440 and d["heroBox"]:
                    hb = d["heroBox"]
                    await pg.screenshot(path=f"{OUT}/muertos-logo-desktop.png", clip={"x": max(0, hb["l"] - 40), "y": max(0, hb["t"] - 60), "width": min(900, w - hb["l"] + 40), "height": hb["h"] + 110})
            else:
                check(d["hero"] and not d["hero"]["vela"] and not d["hero"]["skull"], f"desktop {w}: out of season the hero has no candle or calavera (unchanged)")
            await ctx.close()
        a, m = seen["off"], seen["muertos"]
        check(a["heroBox"] and m["heroBox"] and round(a["heroBox"]["h"]) == round(m["heroBox"]["h"]) and round(a["heroQ"]["l"]) == round(m["heroQ"]["l"]) and round(a["heroLogo"]["l"]) == round(m["heroLogo"]["l"]),
              f"desktop {w}: the art doesn't move the logo or ¿Oyistes? or re-wrap the hero (h1 {a['heroBox'] and round(a['heroBox']['h'])} vs {m['heroBox'] and round(m['heroBox']['h'])})")

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        cdev = dict(is_mobile=True, has_touch=True, device_scale_factor=3)
        await phone(b, "android-chromium", cdev, True)
        await motion(b, "android-chromium", cdev, True)
        await reels(b, "android-chromium", cdev, True)
        await desktop(b, True)
        await muertos_logo(b, "android-chromium", cdev, True)
        await muertos_top_bar(b, "android-chromium", cdev, True)
        await muertos_no_yellow(b, "android-chromium", cdev, True)
        await muertos_desktop(b, True)
        await b.close()
        if os.environ.get("NO_WEBKIT") != "1":
            w = await pw.webkit.launch()
            wdev = dict(is_mobile=True, has_touch=True, device_scale_factor=3)
            await phone(w, "iphone-webkit", wdev, False)
            await motion(w, "iphone-webkit", wdev, False)
            await reels(w, "iphone-webkit", wdev, False)
            await muertos_logo(w, "iphone-webkit", wdev, False)
            await muertos_top_bar(w, "iphone-webkit", wdev, False)
            await muertos_no_yellow(w, "iphone-webkit", wdev, False)
            await w.close()
    print("\n" + ("ALL OK" if not fails else f"{len(fails)} FAILED:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
