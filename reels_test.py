"""v49.13 video reels ("¿Cuál dieta?"'s Bigger the Pansa, Better the Chansa feed), in Node + WebKit (iPhone 13) + Chromium (Pixel 5):
  • the on-device ranker (static/foryou.js, unit tests in Node): like / share / complete / rewatch / skip signals per video and per
    category / creator / tag, short videos first, the seen list (no repeats), ~20% exploration, the crowd boost, next() batches
  • Settings → Video reels: "Autoplay videos" and "Play with sound", both ON by default, remembered; autoplay off / Reduce motion /
    Data Saver → "Tap to play"; sound held by the browser → muted + "Tap anywhere for sound", one tap unmutes
  • Like (♥ button + double-tap heart) and Share on every video; navigator.share on phones, else the sheet (Copy link, Text, WhatsApp,
    Facebook, X, Email) with the Chisme link + the invite; share targets leave Chisme (never the in-app reader); shares counted
  • the deep link /?reel=<id> opens the feed on that video (and link previews get its Open Graph title + picture)
  • the endless feed (a new batch before the end), the progress bar, and no yellow anywhere in the reels UI
Screenshots → /workspace/chisme-reels-shots/ (or $REELS_SHOTS): reels-feed.png, reels-share-sheet.png, reels-settings-toggles.png,
reels-tap-for-sound.png, reels-heart.png
Run: python reels_test.py [http://localhost:8211/]"""
import asyncio, json, os, re, subprocess, sys, urllib.request
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

URL = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHISME_URL", "http://localhost:8211/")).rstrip("/") + "/"
SHOTS = os.environ.get("REELS_SHOTS", "/workspace/chisme-reels-shots")
HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); %s }"
PROF = "JSON.parse(localStorage.getItem('chisme-foryou') || 'null')"

# ---------------------------------------------------------------- 1. the ranker (Node)
RANK_JS = r"""
const F = require(process.argv[1]);
const out = []; const ok = (c, m) => out.push([!!c, m]);
const NOW = Date.UTC(2026, 9, 2, 18), DAY = 864e5, mem = () => ({ getItem: () => null });
const mk = (i, o) => Object.assign({ url: "https://www.youtube.com/shorts/vid" + String(i).padStart(8, "0"), title: "Tacos number " + i, creator: "Creator " + (i % 7),
  crew: "crew" + (i % 7), video: true, published: (NOW - (i % 9) * DAY) / 1000 }, o || {});
// ids
ok(F.reelId("https://www.youtube.com/shorts/abcDEF_-123") === "abcDEF_-123" && F.reelId("https://youtu.be/abcDEF_-123") === "abcDEF_-123"
   && F.reelId("https://www.tiktok.com/@satexasfoodies/video/7655381342229712142") === "7655381342229712142" && F.reelId("https://example.com/x") === null,
   "reelId: YouTube (shorts / youtu.be) → 11 chars, TikTok → its number, anything else → null");
// signals per video
let p = F.load(mem()); const A = mk(1);
p = F.signal(p, "like", A, { now: NOW }); ok(p.s[A.url].lk === 1 && F.liked(p, A.url), "like: remembered on the video (s.lk)");
const wLike = p.f["c:" + A.creator].w;
p = F.signal(p, "unlike", A, { now: NOW }); ok(!p.s[A.url].lk && Math.abs(p.f["c:" + A.creator].w) < 1e-9, "unlike: takes the like (and its weight) back");
p = F.signal(p, "share", A, { now: NOW }); p = F.signal(p, "complete", A, { now: NOW, duration: 41 }); p = F.signal(p, "rewatch", A, { now: NOW });
p = F.signal(p, "watch", A, { now: NOW, seconds: 12.5 }); p = F.signal(p, "watch", A, { now: NOW, seconds: 7 });
const sA = p.s[A.url];
ok(sA.sh === 1 && sA.c === 1 && sA.rw === 1 && sA.wt === 19.5 && sA.d === 41 && sA.v === 2, "per video: shares, completions, rewatches, watch time (s), duration, views: " + JSON.stringify(sA));
ok(F.DELTA.share > F.DELTA.like && F.DELTA.like > F.DELTA.complete && F.DELTA.rewatch > 0 && F.DELTA.skip < 0, "signal strength: share > like > watched to the end; rewatch +; skip −");
// per category / creator / tag
const feats = F.featuresOf(A);
ok(feats.includes("c:" + A.creator) && feats.includes("k:tacos") && feats.includes("t:local"), "features: creator + tag (tacos) + category (local): " + feats.join(", "));
ok(F.featuresOf(mk(2, { recipe: true })).includes("t:recipe") && F.featuresOf(mk(3, { world: true })).includes("t:world"), "category: recipe / world");
const sib = mk(8);   // same creator (8 % 7 = 1) and tag as A, never seen
const base = F.scoreOf(F.load(mem()), sib, NOW);
let pl = F.load(mem()); pl = F.signal(pl, "like", A, { now: NOW });
let ps = F.load(mem()); ps = F.signal(ps, "share", A, { now: NOW });
let pk = F.load(mem()); pk = F.signal(pk, "skip", A, { now: NOW }); pk = F.signal(pk, "skip", A, { now: NOW });
ok(F.scoreOf(ps, sib, NOW) > F.scoreOf(pl, sib, NOW) && F.scoreOf(pl, sib, NOW) > base && F.scoreOf(pk, sib, NOW) < base,
   "a like / share lifts the same creator's other videos (share most); skips sink them");
const cookA = mk(20, { recipe: true, creator: "Cook A", crew: "cooka", title: "Easy soup at home" }), cookB = mk(21, { recipe: true, creator: "Cook B", crew: "cookb", title: "Fried rice" });
let pr = F.load(mem()); for (let k = 0; k < 3; k++) pr = F.signal(pr, "like", cookA, { now: NOW });
ok(F.scoreOf(pr, cookB, NOW) > F.scoreOf(F.load(mem()), cookB, NOW), "category: liking recipes lifts another cook's recipe (t:recipe)");
ok(F.interests(pr, 5, NOW).every((x) => !/^(recipe|local|world)$/.test(x)), "the banner's interests don't show the category feature: " + F.interests(pr, 5, NOW).join(", "));
// short videos first
const e = F.load(mem()), shortV = mk(30), longV = mk(30, { url: "https://www.youtube.com/watch?v=vid00000030" });
ok(F.shortness(shortV) === 1 && F.shortness(longV) === -1 && F.shortness(mk(31, { url: "https://www.tiktok.com/@x/video/7655381342229712199" })) === 1, "shortness: Shorts / TikTok short, watch?v= long");
ok(F.scoreOf(e, shortV, NOW) > F.scoreOf(e, longV, NOW), "Shorts rank above a long YouTube video, all else equal");
ok(F.scoreOf(e, mk(32, { dur: 45 }), NOW) > F.scoreOf(e, mk(32, { dur: 300 }), NOW), "a known 45 s video ranks above a known 5-minute one");
// the seen list: no repeats
let pv = F.load(mem()); pv = F.signal(pv, "watch", mk(40), { now: NOW - 3600e3, seconds: 20 });
let pvOld = F.load(mem()); pvOld = F.signal(pvOld, "watch", mk(40), { now: NOW - 3 * DAY, seconds: 20 });
const twin = mk(47, { published: mk(40).published });   // same creator + tags, never seen
const gapNew = F.scoreOf(pv, twin, NOW) - F.scoreOf(pv, mk(40), NOW), gapOld = F.scoreOf(pvOld, twin, NOW) - F.scoreOf(pvOld, mk(40), NOW);
ok(gapOld > 0.5 && gapNew > gapOld + 1, `seen list: a seen video ranks below its unseen twin (−${gapOld.toFixed(2)}), much further if seen in the last 6 h (−${gapNew.toFixed(2)})`);
const items = Array.from({ length: 30 }, (_, i) => mk(100 + i, { title: ["Tacos", "BBQ brisket", "Ramen", "Pizza", "Birria", "Pan dulce"][i % 6] + " " + i }));
const shown = new Set(items.slice(0, 20).map((x) => x.url)), recent = new Set(items.slice(14, 20).map((x) => x.url));
let b1 = F.next(F.load(mem()), items, { n: 8, shown, recent, now: NOW, seed: 5 });
ok(b1.length === 8 && b1.every((r) => !recent.has(r.item.url)) && b1.every((r) => !shown.has(r.item.url)), "next(): 8 new videos, none of the last few, unseen ones first");
const shownAll = new Set(items.map((x) => x.url));
let b2 = F.next(F.load(mem()), items, { n: 10, shown: shownAll, recent, now: NOW, seed: 6 });
ok(b2.length === 10 && b2.every((r) => !recent.has(r.item.url)) && new Set(b2.map((r) => r.item.url)).size === 10, "next(): everything seen → the best seen ones come back (endless), still none of the last few, no duplicates");
let pni = F.load(mem()); pni = F.signal(pni, "not_interested", items[25], { now: NOW });
ok(F.next(pni, items, { n: 30, now: NOW }).every((r) => r.item.url !== items[25].url), "next(): never a 'Not for me' video");
ok(F.next(F.load(mem()), items.slice(0, 3), { n: 5, recent: new Set(items.slice(0, 3).map((x) => x.url)) }).length === 0, "next(): nothing left that isn't recent → empty (the feed ends)");
// ~20% exploration once it has learned
let pe = F.load(mem()); pe = F.signal(pe, "like", items[0], { now: NOW });
const many = Array.from({ length: 60 }, (_, i) => mk(300 + i, { title: ["Tacos", "BBQ brisket", "Ramen", "Pizza", "Birria", "Pan dulce", "Wings", "Coffee"][i % 8] + " " + i }));
const r60 = F.rank(pe, many, { now: NOW, seed: 9 }), ex = r60.filter((r) => r.explore).length;
ok(ex === 12, `exploration: ${ex} of 60 (${Math.round(ex / 60 * 100)}%) are something different`);
ok(F.next(pe, many, { n: 10, now: NOW, seed: 3 }).filter((r) => r.explore).length === 2, "next(): 2 of every 10 are exploration");
// the crowd's favorites (server, anonymous): a small, capped boost
const fav = mk(50), id = F.reelId(fav.url);
const s0 = F.scoreOf(e, fav, NOW), s1 = F.scoreOf(e, fav, NOW, { [id]: 40 }), s2 = F.scoreOf(e, fav, NOW, { [id]: 1e9 });
ok(s1 > s0 && s2 - s0 <= 1.2001 && s2 >= s1, `popularity: boosts (+${(s1 - s0).toFixed(2)}), capped at +1.2 (+${(s2 - s0).toFixed(2)})`);
const popRank = F.rank(F.load(mem()), many, { now: NOW, seed: 9, pop: { [F.reelId(many[59].url)]: 500 } }).findIndex((r) => r.item.url === many[59].url);
const noPop = F.rank(F.load(mem()), many, { now: NOW, seed: 9 }).findIndex((r) => r.item.url === many[59].url);
ok(popRank <= noPop, `rank(): a crowd favorite moves up (${noPop + 1} → ${popRank + 1})`);
// back-compat
ok(["KEY", "featuresOf", "load", "save", "reset", "signal", "scoreOf", "rank", "why", "interests", "EXPLORE_EVERY", "MIX_EVERY", "crewOf", "placeKey"].every((k) => k in F), "the old API is all still there");
const pSave = F.signal(F.load(mem()), "save", A, { now: NOW }); const store = { v: null, setItem(k, v) { this.v = v; }, getItem() { return this.v; } };
F.save(pSave, store); ok(F.load(store).s[A.url].sv === 1, "profiles still save / load (same localStorage key and version)");
console.log(JSON.stringify(out));
"""

def ranker_tests():
    print("\n== the ranker (Node, static/foryou.js)")
    r = subprocess.run(["node", "-e", RANK_JS, os.path.join(HERE, "static", "foryou.js")], capture_output=True, text=True, timeout=60)
    if r.returncode:
        check(False, "node ran the ranker tests: " + r.stderr[-400:]); return
    for good, msg in json.loads(r.stdout.strip().splitlines()[-1]):
        check(good, msg)

# ---------------------------------------------------------------- helpers (browser)
def food():
    with urllib.request.urlopen(URL + "api/food?lat=29.4241&lon=-98.4936", timeout=90) as r:
        return json.load(r)

def reel_id(u):
    m = re.search(r"(?:youtube\.com/shorts/|youtu\.be/|[?&]v=)([\w-]{11})", u or "") or re.search(r"tiktok\.com/@[\w.]+/video/(\d{15,20})", u or "")
    return m.group(1) if m else None

async def open_food(pg, extra=""):
    await pg.goto(URL + "#cual-dieta", wait_until="domcontentloaded")
    await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)

async def start_feed(pg):
    await pg.tap("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000)
    await pg.wait_for_function("window.__chisme.forYou.cur === 0", timeout=8000)

async def open_settings(pg):
    await pg.evaluate("window.scrollTo(0, 0)"); await pg.tap("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open", timeout=5000); await pg.wait_for_timeout(300)

async def close_settings(pg):
    await pg.evaluate("document.querySelector('#settings').close()"); await pg.wait_for_timeout(200)

CUR = "(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur]; return s; })()"
async def cur_visible_btn(pg, cls):
    """the Like / Share button of the video on screen that's visible right now (floating .vf-act while playing, else the rail)"""
    return await pg.evaluate("""(cls) => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur];
      const b = [...s.querySelectorAll('.' + cls)].find((x) => { const r = x.getBoundingClientRect(), cs = getComputedStyle(x.closest('.vf-act, .vf-rail'));
        return r.width > 0 && cs.visibility === 'visible' && cs.display !== 'none' && +cs.opacity > 0.5; });
      if (!b) return null; b.dataset.t = 'pick-' + cls; return '[data-t="pick-' + cls + '"]'; }""", cls)

YELLOW = r"""(roots) => {
  const bad = [], seen = new Set();
  const yellow = (c) => { const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(c); if (!m) return false;
    const [r, g, b, a] = [+m[1] / 255, +m[2] / 255, +m[3] / 255, m[4] == null ? 1 : +m[4]]; if (a < .2) return false;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (d < .2) return false;
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h = (h * 60 + 360) % 360;
    return h >= 44 && h <= 70 && l > .3; };
  const colorsIn = (v) => (String(v).match(/rgba?\([^)]*\)/g) || []);
  const EMOJI = /[\u26A1\u26A0\u{1F525}\u{1F514}\u{1F510}\u{1F496}\u{1F5C2}\u{1F3C6}\u{1F446}\u{1F44D}\u{1F44F}\u{1F64C}\u{1F600}-\u{1F606}\u{1F60A}\u{1F31F}\u2B50\u{1F4A1}\u{1F7E8}\u{1F49B}]/u;
  for (const sel of roots) for (const root of document.querySelectorAll(sel)) for (const n of [root, ...root.querySelectorAll('*')]) {
    for (const pse of [null, '::before', '::after']) {
      const cs = getComputedStyle(n, pse);
      if (pse && (cs.content === 'none' || cs.content === 'normal')) continue;
      for (const prop of ['color', 'backgroundColor', 'borderTopColor', 'borderLeftColor', 'fill', 'stroke', 'outlineColor', 'backgroundImage', 'boxShadow'])
        for (const c of colorsIn(cs[prop])) if (yellow(c)) { const k = (n.className && n.className.baseVal != null ? n.className.baseVal : n.className) + (pse || '') + ' ' + prop + ' ' + c; if (!seen.has(k)) { seen.add(k); bad.push(k); } }
      if (pse && EMOJI.test(cs.content)) bad.push((n.className || n.tagName) + pse + ' emoji ' + cs.content);
    }
    // (text: Chisme's own words only. Creators' video titles and the donate slide's copy (v46, not part of the reels UI) are skipped)
    const titles = (window.__chisme.forYou.feed || []).map((r) => (r.title || '').slice(0, 24)).filter(Boolean);
    if (n.childNodes && !n.closest('.vf-info h3, .vf-donate, .rs-msg, .sr-only')) for (const t of n.childNodes) if (t.nodeType === 3 && EMOJI.test(t.textContent) && !titles.some((x) => t.textContent.includes(x))) bad.push('text emoji: ' + t.textContent.trim().slice(0, 40));
  }
  return bad.slice(0, 12);
}"""

# ---------------------------------------------------------------- 2. WebKit iPhone
async def webkit_tests(p, data):
    print("\n== WebKit iPhone 13: Settings defaults + persistence")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % ""); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: None if "no supported source" in str(e) else errs.append(str(e)[:200]))   # (Playwright's Chromium has no H.264: a YouTube media error, not Chisme's)
    await open_food(pg)
    st = await pg.evaluate("""() => ({ auto: document.querySelector('#set-feed-autoplay').checked, snd: document.querySelector('#set-feed-sound').checked,
      autoL: document.querySelector('#set-feed-autoplay').closest('label').textContent.trim(), sndL: document.querySelector('#set-feed-sound').closest('label').textContent.trim(),
      legend: document.querySelector('#set-feed-sound-group legend').textContent.trim(), ls: [localStorage.getItem('chisme-feed-autoplay'), localStorage.getItem('chisme-feed-sound')],
      r: window.__chisme.forYou.reels, wanted: window.__chisme.forYou.sound.wanted })""")
    check(st["auto"] and st["snd"] and st["ls"] == [None, None] and st["r"]["autoplay"] and st["r"]["canAutoplay"] and st["wanted"],
          f"fresh phone: Autoplay videos ON and Play with sound ON by default (nothing stored yet) ({st['ls']}, canAutoplay {st['r']['canAutoplay']})")
    check(st["autoL"] == "Autoplay videos" and st["sndL"] == "Play with sound" and st["legend"] == "Video reels", f"Settings → '{st['legend']}': '{st['autoL']}', '{st['sndL']}'")
    await open_settings(pg); await pg.evaluate("document.querySelector('#set-feed-sound-group').scrollIntoView({ block: 'center' })")
    await pg.wait_for_timeout(400); os.makedirs(SHOTS, exist_ok=True)
    await pg.screenshot(path=os.path.join(SHOTS, "reels-settings-toggles.png"))
    await pg.tap("#set-feed-autoplay + span"); await pg.tap("#set-feed-sound + span"); await pg.wait_for_timeout(200); await close_settings(pg)
    ls = await pg.evaluate("[localStorage.getItem('chisme-feed-autoplay'), localStorage.getItem('chisme-feed-sound')]")
    check(ls == ["off", "off"], f"turning both off is saved ({ls})")
    await pg.reload(wait_until="domcontentloaded"); await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
    st = await pg.evaluate("({ auto: document.querySelector('#set-feed-autoplay').checked, snd: document.querySelector('#set-feed-sound').checked, r: window.__chisme.forYou.reels, wanted: window.__chisme.forYou.sound.wanted })")
    await open_settings(pg)
    st2 = await pg.evaluate("({ auto: document.querySelector('#set-feed-autoplay').checked, snd: document.querySelector('#set-feed-sound').checked })")
    await close_settings(pg)
    check(not st2["auto"] and not st2["snd"] and not st["r"]["canAutoplay"] and not st["wanted"], f"after a reload both stay off ({st2}, canAutoplay {st['r']['canAutoplay']})")
    await start_feed(pg); await pg.wait_for_timeout(1200)
    f = await pg.evaluate("(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][0]; return { play: !!s.querySelector('.vf-play'), playing: s.classList.contains('vf-playing'), btn: document.querySelector('#feed-sound').textContent.trim() }; })()")
    check(f["play"] and not f["playing"] and f["btn"] == "🔇 Muted", f"autoplay off: the video waits for a tap ('Tap to play'), sound button says Muted ({f})")
    await pg.tap("#feed-close"); await pg.wait_for_function("!document.querySelector('#feed').open", timeout=5000)
    await open_settings(pg); await pg.tap("#set-feed-autoplay + span"); await pg.tap("#set-feed-sound + span"); await close_settings(pg)
    ls = await pg.evaluate("[localStorage.getItem('chisme-feed-autoplay'), localStorage.getItem('chisme-feed-sound')]")
    check(ls == ["on", "on"], f"turned back on: saved ({ls})")

    print("\n== WebKit iPhone 13: the feed, like + double-tap heart, progress")
    await start_feed(pg)
    try: await pg.wait_for_function("(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur]; return s && s.classList.contains('vf-playing') && window.__chisme.forYou.player.st === 1; })()", timeout=20000)
    except Exception: pass
    sl = await pg.evaluate("""() => { const all = [...document.querySelectorAll('#feed-scroll .vf-slide[data-url]')], v = all.slice(0, 6);
      return { n: v.length, lazy: !all[all.length - 1].querySelector('.vf-act'), act: v.every((s) => s.querySelector('.vf-act .vf-like') && s.querySelector('.vf-act .vf-share') && s.querySelector('.vf-rail .vf-like') && s.querySelector('.vf-rail .vf-share') && s.querySelector('.vf-prog i')),
        playing: v[0].classList.contains('vf-playing'), actShown: getComputedStyle(v[0].querySelector('.vf-act')).display, railVis: getComputedStyle(v[0].querySelector('.vf-rail')).visibility }; }""")
    check(sl["n"] == 6 and sl["act"] and sl["lazy"], "the video on screen and the next ones have Like + Share (floating and in the rail) and a progress bar (far-off slides get them when they come near: a light feed)")
    check(not sl["playing"] or (sl["actShown"] == "flex" and sl["railVis"] == "hidden"), f"while it plays: Like + Share stay on the video, the rest of the rail hides ({sl})")
    await pg.wait_for_timeout(2500)
    pr = await pg.evaluate("(() => { const s = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur]; return { t: s.querySelector('.vf-prog i').style.transform, playing: s.classList.contains('vf-playing') }; })()")
    m = re.search(r"scaleX\(([\d.]+)\)", pr["t"] or "")
    check(not pr["playing"] or (m and float(m.group(1)) > 0), f"progress bar moves while the video plays ({pr['t']})")
    await pg.screenshot(path=os.path.join(SHOTS, "reels-feed.png"))
    url0 = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].dataset.url")
    box = await pg.evaluate("(() => { const r = [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].querySelector('.vf-shield').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height * 0.4 }; })()")
    was = await pg.evaluate("window.__chisme.forYou.sound ? [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].classList.contains('vf-playing') : null")
    await pg.touchscreen.tap(box["x"], box["y"]); await pg.wait_for_timeout(120); await pg.touchscreen.tap(box["x"], box["y"]); await pg.wait_for_timeout(250)
    h = await pg.evaluate(f"({{ heart: document.querySelectorAll('#feed-scroll .vf-heart').length, liked: !!({PROF}).s[{json.dumps(url0)}]?.lk, pressed: [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].querySelector('.vf-act .vf-like').getAttribute('aria-pressed'), q: window.__chisme.stats.queue.filter(e => e[0] === 'reel') }})")
    await pg.screenshot(path=os.path.join(SHOTS, "reels-heart.png"))
    check(h["heart"] >= 1 and h["liked"] and h["pressed"] == "true", f"double-tap the video: a ♥ pops where you tapped and it's liked ({h['heart']} heart, pressed {h['pressed']})")
    check(any(e[1].get("a") == "like" and e[1].get("id") == reel_id(url0) for e in h["q"]), f"the like is counted (anonymous, by video id) ({h['q'][-2:]})")
    await pg.wait_for_timeout(1200)
    now = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].classList.contains('vf-playing')")
    check(now == was, f"a double-tap doesn't leave the video paused (playing before {was}, after {now})")
    sel = await cur_visible_btn(pg, "vf-like")
    if sel: await pg.tap(sel); await pg.wait_for_timeout(200)
    un = await pg.evaluate(f"({{ liked: !!({PROF}).s[{json.dumps(url0)}]?.lk, pressed: [...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].querySelector('.vf-like').getAttribute('aria-pressed') }})")
    check(sel and not un["liked"] and un["pressed"] == "false", f"the ♥ button toggles it back off ({un})")
    check(not errs, "no page errors" + (f": {errs[:2]}" if errs else ""))
    await ctx.close()

    print("\n== WebKit iPhone 13: deep link /?reel=<id>, 'Tap anywhere for sound', share sheet (no navigator.share)")
    vids = [i for k in ("items", "recipes", "world") for i in data.get(k) or [] if i.get("video") and "/shorts/" in i.get("url", "")]
    target = vids[min(len(vids) - 1, 17)]; rid = reel_id(target["url"])
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "")
    await ctx.add_init_script("try { delete Navigator.prototype.share; delete Navigator.prototype.canShare; } catch (e) {}")
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: None if "no supported source" in str(e) else errs.append(str(e)[:200]))   # (Playwright's Chromium has no H.264: a YouTube media error, not Chisme's)
    await pg.goto(URL + "?reel=" + rid, wait_until="domcontentloaded")
    try: await pg.wait_for_function("document.querySelector('#feed').open && window.__chisme.forYou.cur === 0", timeout=90000)
    except Exception: pass
    d = await pg.evaluate("""() => { const s = document.querySelector('#feed-scroll .vf-slide'); return { open: document.querySelector('#feed').open, url: s && s.dataset.url,
      why: s && s.querySelector('.why-chip').textContent, search: location.search, hash: location.hash, view: window.__chisme.view, lead: window.__chisme.forYou.reels.lead }; }""")
    check(d["open"] and reel_id(d["url"] or "") == rid, f"/?reel={rid} opens the reels feed straight on that video ({(d['url'] or '')[-30:]})")
    check("Shared with you" in (d["why"] or "") and d["search"] == "" and d["hash"] == "#y-la-dieta" and d["lead"] is None,
          f"…marked 'Shared with you', and the ?reel= is dropped from the address (a reload doesn't reopen it) ({d['why']!r}, {d['search']!r}{d['hash']})")
    try: await pg.wait_for_function("window.__chisme.forYou.sound.held", timeout=15000)
    except Exception: pass
    hs = await pg.evaluate("({ held: window.__chisme.forYou.sound.held, btn: document.querySelector('#feed-sound').textContent.trim(), hint: getComputedStyle(document.querySelector('#feed .feed-top'), '::after').content })")
    check(hs["held"] and "Tap anywhere for sound" in hs["hint"] and hs["btn"] == "🔇 Muted", f"opened by a link (no tap yet): plays muted with the 'Tap anywhere for sound' hint ({hs})")
    await pg.screenshot(path=os.path.join(SHOTS, "reels-tap-for-sound.png"))
    await pg.tap("#feed-scroll .vf-slide:nth-child(1) .vf-shield"); await pg.wait_for_timeout(1500)
    hs2 = await pg.evaluate("({ held: window.__chisme.forYou.sound.held, wanted: window.__chisme.forYou.sound.wanted, unlocks: window.__chisme.forYou.sound.unlocks })")
    check(not hs2["held"] and hs2["wanted"] and hs2["unlocks"] >= 1, f"one tap: the sound comes on (the hint goes) ({hs2})")
    sel = await cur_visible_btn(pg, "vf-share")
    if not sel:   # (paused: the rail's Share)
        await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].querySelector('.vf-rail .vf-share').dataset.t = 'pick-vf-share'"); sel = '[data-t="pick-vf-share"]'
    await pg.tap(sel); await pg.wait_for_timeout(500)
    sh = await pg.evaluate("""() => ({ open: document.querySelector('#reel-share').open, msg: document.querySelector('#rs-msg').textContent,
      btns: [...document.querySelectorAll('#rs-grid .rs-btn')].map((a) => ({ t: a.textContent.trim(), href: a.getAttribute('href') || '', target: a.getAttribute('target') || '', way: a.dataset.way })) })""")
    check(sh["open"], "Share (no system share sheet in this browser): Chisme's share sheet opens")
    link = URL + "?reel=" + rid
    check(sh["msg"].startswith("Mira este video en Chisme 👀 " + link) and "Get the Chisme app for San Antonio's news, food & chisme: " + URL.rstrip('/') in sh["msg"],
          f"the message: the video's Chisme link + the invite to get the app ({sh['msg'][:150]})")
    names = [x["t"] for x in sh["btns"]]
    check(names[:6] == ["Copy link", "Text message", "WhatsApp", "Facebook", "X", "Email"], f"targets: {names}")
    hb = {x["way"]: x for x in sh["btns"]}
    from urllib.parse import quote
    check(hb["sms"]["href"].startswith("sms:?&body=") and quote("Get the Chisme app", safe="") in hb["sms"]["href"].replace("%20", "%20") and quote(link, safe="") in hb["sms"]["href"],
          "Text message: sms: with the message + link as the body")
    check(hb["whatsapp"]["href"].startswith("https://wa.me/?text=") and hb["whatsapp"]["target"] == "_blank", "WhatsApp: wa.me with the message, in a new window (leaves Chisme)")
    check(hb["facebook"]["href"].startswith("https://www.facebook.com/sharer/sharer.php?u=" + quote(link, safe="")), "Facebook: the sharer with the video's Chisme link")
    check(hb["x"]["href"].startswith("https://twitter.com/intent/tweet?text=") and ("url=" + quote(link, safe="")) in hb["x"]["href"], "X: a tweet with the invite + the link")
    check(hb["email"]["href"].startswith("mailto:?subject=") and quote(link, safe="") in hb["email"]["href"], "Email: mailto: with the message + link")
    await pg.screenshot(path=os.path.join(SHOTS, "reels-share-sheet.png"))
    yl = await pg.evaluate(YELLOW, ["#feed", "#reel-share"])
    check(not yl, "no yellow in the reels feed or the share sheet (colors, gradients, emoji, ::before/::after)" + (f": {yl}" if yl else ""))
    await pg.tap("#rs-grid .rs-copy"); await pg.wait_for_timeout(400)
    note = await pg.evaluate("document.querySelector('#rs-note').textContent")
    check(note.startswith("Copied") or note.startswith("Couldn't copy"), f"Copy link answers ({note!r})")
    await pg.tap("#rs-close"); await pg.wait_for_timeout(200)
    check(not await pg.evaluate("document.querySelector('#reel-share').open") and await pg.evaluate("document.querySelector('#feed').open"), "✕ closes the sheet, back on the video")
    check(not errs, "no page errors" + (f": {errs[:2]}" if errs else ""))
    await ctx.close(); await b.close()

# ---------------------------------------------------------------- 3. Chromium (Pixel 5)
async def chromium_tests(p, data):
    print("\n== Chromium Pixel 5: navigator.share, share targets leave Chisme, endless feed, Data Saver / Reduce motion, Open Graph")
    b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"]); dev = dict(p.devices["Pixel 5"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % "")
    await ctx.add_init_script("""window.__shares = []; window.__shareMode = 'ok';
      Object.defineProperty(Navigator.prototype, 'share', { configurable: true, value: function (d) { window.__shares.push(d);
        if (window.__shareMode === 'abort') return Promise.reject(new DOMException('cancel', 'AbortError'));
        if (window.__shareMode === 'fail') return Promise.reject(new DOMException('no', 'NotAllowedError'));
        return Promise.resolve(); } });
      Object.defineProperty(Navigator.prototype, 'canShare', { configurable: true, value: () => true });""")
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: None if "no supported source" in str(e) else errs.append(str(e)[:200]))   # (Playwright's Chromium has no H.264: a YouTube media error, not Chisme's)
    await ctx.route(re.compile(r"^https://(wa\.me|api\.whatsapp\.com)/"), lambda r: r.fulfill(status=200, content_type="text/html", body="<p>wa</p>"))   # (context-wide: the popup is a new page)
    await open_food(pg); await start_feed(pg); await pg.wait_for_timeout(800)
    url0 = await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][0].dataset.url")
    await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][0].querySelector('.vf-rail .vf-share').click()"); await pg.wait_for_timeout(400)
    s = await pg.evaluate(f"({{ shares: window.__shares, sheet: document.querySelector('#reel-share').open, prof: ({PROF}).s[{json.dumps(url0)}], q: window.__chisme.stats.queue.filter(e => e[0] === 'reel') }})")
    d0 = (s["shares"] or [{}])[0]
    check(len(s["shares"]) == 1 and not s["sheet"] and d0.get("url") == URL + "?reel=" + reel_id(url0) and "Get the Chisme app for San Antonio's news, food & chisme: " + URL.rstrip('/') in d0.get("text", "")
          and d0.get("text", "").startswith("Mira este video en Chisme 👀"), f"phone with a share sheet: navigator.share gets the Chisme link + the invite ({d0})")
    check((s["prof"] or {}).get("sh") == 1 and any(e[1] == {"a": "share", "id": reel_id(url0), "m": "native"} for e in s["q"]), "the share teaches the ranker (s.sh) and is counted (reel share, native)")
    await pg.evaluate("window.__shareMode = 'abort'; window.__shares = []; [...document.querySelectorAll('#feed-scroll .vf-slide')][0].querySelector('.vf-rail .vf-share').click()"); await pg.wait_for_timeout(300)
    s = await pg.evaluate(f"({{ n: window.__shares.length, sheet: document.querySelector('#reel-share').open, sh: ({PROF}).s[{json.dumps(url0)}].sh }})")
    check(s["n"] == 1 and not s["sheet"] and s["sh"] == 1, f"cancelled in the system sheet: nothing counted, no second sheet ({s})")
    await pg.evaluate("window.__shareMode = 'fail'; [...document.querySelectorAll('#feed-scroll .vf-slide')][0].querySelector('.vf-rail .vf-share').click()"); await pg.wait_for_timeout(400)
    check(await pg.evaluate("document.querySelector('#reel-share').open"), "system share failed: falls back to Chisme's sheet")
    names = await pg.evaluate("[...document.querySelectorAll('#rs-grid .rs-btn')].map(a => a.textContent.trim())")
    check(names[-1] == "More apps…", f"…with 'More apps…' (the system sheet) when the phone has one ({names})")
    async with ctx.expect_page(timeout=8000) as pop:
        await pg.click("#rs-grid .rs-wa")
    wp = await pop.value; await wp.wait_for_load_state("domcontentloaded")
    st = await pg.evaluate("({ reader: document.querySelector('#player').open, q: window.__chisme.stats.queue.filter(e => e[0] === 'reel' && e[1].m === 'whatsapp') })")
    check(re.match(r"^https://(wa\.me/|api\.whatsapp\.com/send/)\?text=", wp.url) is not None and not st["reader"] and st["q"], f"WhatsApp leaves Chisme in a new window (not the in-app reader) and is counted ({wp.url[:60]}…)")
    await wp.close(); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)

    # endless: jump near the end, a new batch is added before the end card
    n0 = await pg.evaluate("document.querySelectorAll('#feed-scroll .vf-slide').length")
    await pg.evaluate("(() => { const s = document.querySelector('#feed-scroll'), all = [...s.querySelectorAll('.vf-slide')]; s.scrollTop = all[all.length - 3].offsetTop; })()")
    try: await pg.wait_for_function("window.__chisme.forYou.reels.batches >= 1", timeout=8000)
    except Exception: pass
    e = await pg.evaluate("""() => { const all = [...document.querySelectorAll('#feed-scroll .vf-slide')], r = window.__chisme.forYou.reels;
      return { n: all.length, batches: r.batches, endLast: all[all.length - 1].classList.contains('vf-end'), urls: all.filter((s) => s.dataset.url).map((s) => s.dataset.url) }; }""")
    check(e["batches"] >= 1 and e["n"] > n0 and e["endLast"], f"endless: 4 videos before the end, the next batch is already there ({n0} → {e['n']} slides, the end card stays last)")
    old, new = e["urls"][:-10], e["urls"][-10:]
    check(not (set(new) & set(old[-12:])) and len(set(new)) == len(new), "…none of the new batch repeats the last 12 videos, no duplicates inside it")
    check(not errs, "no page errors" + (f": {errs[:2]}" if errs else ""))
    await ctx.close()

    for name, init in (("Data Saver", "Object.defineProperty(Navigator.prototype, 'connection', { configurable: true, get: () => ({ saveData: true, effectiveType: '4g', addEventListener() {} }) });"),
                       ("Reduce motion (Chisme's Settings)", "localStorage.setItem('chisme-reduce-motion', '1');")):
        ctx = await b.new_context(**dev); await ctx.add_init_script(INIT % ""); await ctx.add_init_script(init); pg = await ctx.new_page()
        await open_food(pg); await start_feed(pg); await pg.wait_for_timeout(800)
        f = await pg.evaluate("({ can: window.__chisme.forYou.reels.canAutoplay, auto: window.__chisme.forYou.reels.autoplay, play: !!document.querySelector('#feed-scroll .vf-slide .vf-play') })")
        check(not f["can"] and f["auto"] and f["play"], f"{name}: no autoplay (the setting itself stays on); 'Tap to play' instead ({f})")
        await ctx.close()

    # Open Graph for a shared link (the food list is in the server's memory now)
    vids = [i for k in ("items", "recipes", "world") for i in data.get(k) or [] if i.get("video") and "/shorts/" in i.get("url", "")]
    it = vids[3]; rid = reel_id(it["url"])
    html = urllib.request.urlopen(URL + "?reel=" + rid, timeout=30).read().decode()
    og = dict(re.findall(r'<meta (?:property|name)="((?:og|twitter):[\w:]+)" content="([^"]*)"', html))
    import html as H
    check(og.get("og:image") == f"https://i.ytimg.com/vi/{rid}/hqdefault.jpg" and og.get("og:url", "").endswith("/?reel=" + rid) and og.get("og:type") == "video.other",
          f"/?reel=<id>: Open Graph picture = the video's thumbnail, url = the Chisme link ({og.get('og:image')})")
    want = re.sub(r"\s+", " ", it["title"]).strip()
    check(H.unescape(og.get("og:title", "")).rstrip("…")[:40] == want[:40] and "Get the Chisme app" in H.unescape(og.get("og:description", "")),
          f"…title = the video's, description invites to get Chisme ({H.unescape(og.get('og:title', ''))[:60]!r})")
    html2 = urllib.request.urlopen(URL + "?reel=%3Cscript%3E", timeout=30).read().decode()
    check('property="og:title" content="Chisme — San Antonio' in html2 and "<script>" not in html2.split("<body")[0].replace("<script>", "") , "a bad ?reel= value: the normal Open Graph tags, nothing injected")
    check('property="og:title" content="Chisme — San Antonio' in urllib.request.urlopen(URL, timeout=30).read().decode(), "the home page has Open Graph tags too")
    pop = json.load(urllib.request.urlopen(URL + "api/reels/popular", timeout=30))
    check(isinstance(pop.get("pop"), dict), f"/api/reels/popular answers ({len(pop.get('pop') or {})} videos)")
    await b.close()

async def public_base_tests(p, data):
    """v49.13: share links, the promo line and Open Graph come from PUBLIC_BASE_URL (the move to chisme.co), else the page's address."""
    print("\n== PUBLIC_BASE_URL: share links + Open Graph follow one setting")
    port = 8291; base = f"http://127.0.0.1:{port}"
    env = dict(os.environ, PUBLIC_BASE_URL="https://chisme.co/", STATS_STORE_FILE="/tmp/reels-pb-stats.json", PUSH_STORE_FILE="/tmp/reels-pb-push.json")
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=os.path.dirname(os.path.abspath(__file__)),
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        page = ""
        for _ in range(60):
            try: page = urllib.request.urlopen(base + "/", timeout=5).read().decode(); break
            except Exception: await asyncio.sleep(1)
        rid = reel_id(next(it["url"] for k in ("items", "recipes", "world") for it in (data.get(k) or []) if it.get("video") and reel_id(it.get("url"))))
        rp = urllib.request.urlopen(base + "/?reel=" + rid, timeout=20).read().decode()
        check('<meta name="chisme-base" content="https://chisme.co">' in page and 'og:url" content="https://chisme.co/"' in page
              and 'og:image" content="https://chisme.co/static/icons/icon-512.png"' in page and "onrender" not in page and "__PUBLIC_BASE__" not in page,
              "PUBLIC_BASE_URL=https://chisme.co/ → the page's base meta + Open Graph url/image use it (trailing / trimmed; no onrender anywhere)")
        check(f'og:url" content="https://chisme.co/?reel={rid}"' in rp and "onrender" not in rp, f"…and a shared reel's preview links to https://chisme.co/?reel={rid}")
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await ctx.add_init_script(INIT % ""); await ctx.add_init_script("try { delete Navigator.prototype.share; delete Navigator.prototype.canShare; } catch (e) {}")
        pg = await ctx.new_page(); await pg.goto(base + "/#y-la-dieta", wait_until="domcontentloaded")
        await pg.wait_for_function("() => window.__chisme && window.__chisme.foodReady && !document.querySelector('#foryou-card').hidden", timeout=90000)
        pb = await pg.evaluate("window.__chisme.publicBase")
        await start_feed(pg)
        await pg.evaluate("[...document.querySelectorAll('#feed-scroll .vf-slide')][window.__chisme.forYou.cur].querySelector('.vf-rail .vf-share').click()"); await pg.wait_for_timeout(400)
        msg = await pg.evaluate("(document.querySelector('.reel-share .rs-msg') || {}).textContent || ''")
        check(pb == "https://chisme.co" and re.search(r"Mira este video en Chisme 👀 https://chisme\.co/\?reel=[\w-]+", msg) and msg.rstrip().endswith("food & chisme: https://chisme.co"),
              f"the share sheet's link + promo line use https://chisme.co (served from {base}) ({msg[:140]!r})")
        await b.close()
    finally:
        srv.terminate()
        try: srv.wait(10)
        except Exception: srv.kill()

async def main():
    ranker_tests()
    data = food()
    async with async_playwright() as p:
        await webkit_tests(p, data)
        await chromium_tests(p, data)
        await public_base_tests(p, data)
    print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
