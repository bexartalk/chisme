"""v49.12 last visual sweep: every tab (Chisme All / News / Sports / Events, Weather, the food tab, Juegos), Chismería,
The Juan That Got Away + the skin picker, Settings, Tía's menu + chat, the first launch (location card, then the Terms bar),
/privacy and /terms, at 375 and 320 px wide: iPhone WebKit (light + dark) and Android Chromium (light), the Día de Muertos
look on (it's the season). Flags: page wider than the screen, text that overlaps other text, text cut off by its box
(ellipsis on purpose is listed apart), and text contrast under WCAG AA (4.5, or 3 for large text).
Screens: /workspace/v49.12-review/sweep/<device>-<w>-<theme>-<screen>.png
    ./venv/bin/python visual_sweep_test.py   (local server: ./run.sh)"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET
URL = os.environ.get("URL", "http://localhost:8211").rstrip("/")
OUT = os.environ.get("SWEEP_OUT", "/workspace/v49.12-review/sweep"); os.makedirs(OUT, exist_ok=True)
ONLY = os.environ.get("ONLY", "")
fails = []; found = {}
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

AUDIT = r"""(rootSel) => {
  const root = rootSel ? document.querySelector(rootSel) : document.body;
  const out = { wide: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth, overlap: [], cut: [], ellipsis: [], low: [] };
  if (!root) return out;
  const cs = (e) => getComputedStyle(e);
  const shown = (e) => { const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
    for (let n = e; n && n !== document.documentElement; n = n.parentElement) { const s = cs(n); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < .05) return false;
      if (n.hidden || (n.hasAttribute('inert') && !n.classList.contains('view'))) return false; if (n.classList.contains('sr-only')) return false; if (n.tagName === 'DIALOG' && !n.open) return false;
      if (n.parentElement && n.parentElement.tagName === 'DETAILS' && !n.parentElement.open && n.tagName !== 'SUMMARY') return false; }   // inside a closed <details>
    if (r.right < 0 || r.left > innerWidth) return false; return true; };
  const name = (e) => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '')) + ' "' + e.textContent.trim().replace(/\s+/g, ' ').slice(0, 40) + '"';
  const texts = [...root.querySelectorAll('*')].filter((e) => !['SCRIPT', 'STYLE', 'svg', 'SVG', 'CANVAS', 'OPTION', 'TEMPLATE', 'NOSCRIPT'].includes(e.tagName)
    && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && shown(e));
  // a text box's own text extent (a Range: real glyph boxes, not the element's padding box)
  const clamped = (e) => { for (let n = e, k = 0; n && k < 3; n = n.parentElement, k++) { const s = cs(n); if (s.webkitLineClamp && s.webkitLineClamp !== 'none' || s.textOverflow === 'ellipsis') return n; } return null; };
  const textRects = (e) => { const out = []; for (const n of e.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const rg = document.createRange(); rg.selectNodeContents(n); for (const r of rg.getClientRects()) if (r.width > 1 && r.height > 1) out.push(r); }
    const c = clamped(e); if (c) { const b = c.getBoundingClientRect(); return out.filter((r) => r.top < b.bottom - 2 && r.bottom > b.top + 2).map((r) => ({ left: Math.max(r.left, b.left), right: Math.min(r.right, b.right), top: Math.max(r.top, b.top), bottom: Math.min(r.bottom, b.bottom), width: r.width, height: Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top) })); }   // a clamped line shows only inside its box
    return out; };
  const fixedish = (e) => { for (let n = e; n && n !== document.body; n = n.parentElement) { const p = cs(n).position; if (p === 'fixed' || p === 'sticky') return true; if (n.tagName === 'DIALOG') return false; } return false; };
  const scroller = (n) => { const s = cs(n); return /(auto|scroll)/.test(s.overflowX + s.overflowY); };
  // 1) text over other text (in-flow text only; the fixed bar / Tía / sticky chips float over the page by design)
  // (big display text, e.g. the 75°F on Weather: its line box has ~20% empty leading above/below the glyphs, so trim it)
  const glyphs = (e) => { const rs = textRects(e); if (parseFloat(cs(e).fontSize) < 40) return rs; return rs.map((r) => { const t = .2 * (r.bottom - r.top); return { left: r.left, right: r.right, top: r.top + t, bottom: r.bottom - t }; }); };
  const flow = texts.filter((e) => !fixedish(e)).slice(0, 900).map((e) => [e, glyphs(e)]);
  for (let i = 0; i < flow.length; i++) for (let j = i + 1; j < flow.length; j++) {
    const [a, ra] = flow[i], [b, rb] = flow[j]; if (a.contains(b) || b.contains(a)) continue;
    let hit = 0; for (const x of ra) for (const y of rb) { const w = Math.min(x.right, y.right) - Math.max(x.left, y.left), h = Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top); if (w > 3 && h > Math.max(4, .3 * Math.min(x.bottom - x.top, y.bottom - y.top))) hit = Math.max(hit, w * h); }   // (a big line box brushing the next line isn't an overlap)
    if (hit > 24) { out.overlap.push(name(a) + ' × ' + name(b) + ' (' + Math.round(hit) + ' px²)'); if (out.overlap.length > 12) break; }
  }
  // fixed / sticky things that overlap each other (tab bar, chips, Tía, Terms bar, sync)
  const fx = ['#tabs', '.view.active .mq-chips', '#tia-btn', '#terms-bar', '#sync:not([data-state=done])', '#muertos-banner'].map((s) => document.querySelector(s)).filter((e) => e && shown(e) && fixedish(e));
  for (let i = 0; i < fx.length; i++) for (let j = i + 1; j < fx.length; j++) { const a = fx[i].getBoundingClientRect(), b = fx[j].getBoundingClientRect();
    if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2 && !fx[i].contains(fx[j])) out.overlap.push('FIXED ' + name(fx[i]) + ' × ' + name(fx[j])); }
  // 2) cut-off text: glyphs outside a clipping ancestor (not a scroll strip), or an element's own clipped overflow
  for (const e of texts) {
    const s = cs(e);
    const navLabel = e.closest('#tabs .tab, .mq-chip, button, .lot-btn');
    const ellip = (n) => cs(n).textOverflow === 'ellipsis' && n.scrollWidth > n.clientWidth + 1;
    if (navLabel && (ellip(navLabel) || ellip(e))) { out.cut.push(name(navLabel) + ' (a button label cut with …)'); continue; }
    if (s.textOverflow === 'ellipsis' && e.scrollWidth > e.clientWidth + 1) { out.ellipsis.push(name(e)); continue; }
    if (s.webkitLineClamp && s.webkitLineClamp !== 'none' && e.scrollHeight > e.clientHeight + 2) { out.ellipsis.push(name(e) + ' (line clamp)'); continue; }
    const rs = textRects(e); if (!rs.length) continue;
    for (let n = e, k = 0; n && n !== document.body && k < 8; n = n.parentElement, k++) {
      const p = cs(n); if (scroller(n)) break; if (n.tagName === 'DIALOG') break; if (n !== e && p.position === 'fixed') break;   // a full-screen game is fixed: not clipped by the page
      if (/(hidden|clip)/.test(p.overflowX + p.overflowY) || n === e && /(hidden|clip)/.test(p.overflow)) {
        const c = n.getBoundingClientRect();
        if (rs.some((r) => r.right > c.right + 2 || r.left < c.left - 2 || r.bottom > c.bottom + 3 || r.top < c.top - 3)) { out.cut.push(name(e) + ' in ' + name(n).split(' "')[0]); break; }
      }
    }
    if (out.cut.length > 15) break;
  }
  // 3) contrast (text colour vs the first solid background behind it; skipped over pictures / gradients)
  const rgb = (c) => { if (/^color\(srgb/.test(c)) { const m = c.match(/[\d.]+/g).map(Number); return [m[0] * 255, m[1] * 255, m[2] * 255, m[3] == null ? 1 : m[3]]; }
    const m = (c.match(/[\d.]+/g) || [0, 0, 0]).map(Number); return [m[0], m[1], m[2], m[3] == null ? 1 : m[3]]; };
  const L = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
  const mix = (top, bot) => [0, 1, 2].map((i) => top[i] * top[3] + bot[i] * (1 - top[3])).concat(1);
  const bgOf = (e) => { const layers = []; for (let n = e; n; n = n.parentElement) { const s = cs(n);
      if (s.backgroundImage !== 'none' && !/^url\(.*\.svg/.test(s.backgroundImage) || n.tagName === 'IMG' || n.tagName === 'VIDEO') return null;
      const c = rgb(s.backgroundColor); if (c[3] > 0) { layers.push(c); if (c[3] >= .99) break; } }
    let base = [255, 255, 255, 1]; for (let i = layers.length - 1; i >= 0; i--) base = mix(layers[i], base); return base; };
  const seen = new Set();
  for (const e of texts) {
    if (e.closest('button[disabled], [aria-disabled=true], .locked, .sync[data-state=done]')) continue;   // (the sync toast fading out: its text and its own background fade together)
    if (/^[\p{Extended_Pictographic}\p{Emoji_Component}\uFE0F\u200D\s·•|]+$/u.test(e.textContent.trim())) continue;   // emoji are drawn in their own colours
    const s = cs(e); const bg = bgOf(e); if (!bg) continue;
    let op = 1; for (let n = e; n; n = n.parentElement) op *= +cs(n).opacity;
    const fg = rgb(s.color); const c = mix([fg[0], fg[1], fg[2], fg[3] * op], bg);
    const a = L(c), b = L(bg), ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const px = parseFloat(s.fontSize), bold = +s.fontWeight >= 700, large = px >= 24 || (bold && px >= 18.66);
    if (ratio < (large ? 3 : 4.5) - .02) { const k = name(e); if (!seen.has(k)) { seen.add(k); out.low.push(k + ' ' + ratio.toFixed(2) + (large ? ' (large)' : '')); } }
    if (out.low.length > 15) break;
  }
  return out;
}"""

async def ready(pg):
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)

async def audit(pg, tag, screen, root=None, shot=True, full=False):
    r = await pg.evaluate(AUDIT, root)
    probs = []
    if r["wide"] > 1: probs.append(f"page {r['wide']} px wider than the screen")
    probs += ["overlap: " + x for x in r["overlap"]] + ["cut: " + x for x in r["cut"]] + ["contrast: " + x for x in r["low"]]
    found.setdefault(screen, {})[tag] = {"probs": probs, "ellipsis": r["ellipsis"]}
    if shot: await pg.screenshot(path=f"{OUT}/{tag.replace(' ', '-')}-{screen}.png", full_page=full)
    check(not probs, f"{tag} {screen}: no overlap / cut-off text / low contrast" + (f" {probs[:6]}" if probs else "") + (f" (ellipsis on purpose: {len(r['ellipsis'])})" if r["ellipsis"] else ""))

async def go(pg, h, wait=1200):
    await pg.evaluate(f"location.hash = '{h}'"); await pg.wait_for_timeout(wait); await pg.evaluate("scrollTo(0, 0)"); await pg.wait_for_timeout(250)

async def run(b, bname, dev, w, theme):
    tag = f"{bname} {w} {theme}"
    hgt = 812 if w == 375 else 640
    seed = (f"try{{localStorage.setItem('chisme-theme','{theme}');localStorage.setItem('chisme-season-pin','muertos');localStorage.setItem('chisme-juan-top10',JSON.stringify({{at:1,rank:3,score:999}}));"
            "localStorage.setItem('chisme-default-tab','chisme');localStorage.setItem('chisme-muertos-banner-x','');}catch(e){}")
    # first launch: the location card, then (after Not now) the Terms bar
    ctx = await b.new_context(viewport={"width": w, "height": hgt}, color_scheme=theme, **dev)
    await ctx.add_init_script(seed); await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    await ctx.add_init_script("try{const k=['chisme-notif','chisme-settings-tip'];localStorage.setItem('chisme-notif',JSON.stringify({n:1,shows:1}));localStorage.setItem('chisme-settings-tip','test:0');localStorage.setItem('chisme-a2hs',JSON.stringify({n:9,never:true}))}catch(e){}")
    await ctx.add_init_script("try{localStorage.removeItem('chisme-terms-ok')}catch(e){}")   # (pw_csp's automatic QUIET accepts the Terms; this is the real first launch)
    pg = await ctx.new_page(); await pg.goto(URL + "/"); await ready(pg); await pg.wait_for_timeout(1500)
    if not ONLY or "first" in ONLY:
        await audit(pg, tag, "first-launch")
        if await pg.is_visible("#loc-close"): await pg.click("#loc-close"); await pg.wait_for_timeout(500)
        try: await pg.wait_for_selector("#terms-bar", state="visible", timeout=4000); ok = True
        except Exception: ok = False
        check(ok, f"{tag}: after the location card is answered the Terms bar shows " + str(await pg.evaluate("[document.querySelector('#terms-bar').hidden, document.querySelector('#loc-panel').hidden, document.documentElement.className, localStorage.getItem('chisme-terms-ok')]")))
        await audit(pg, tag, "terms-bar")
    await ctx.close()
    # set up
    ctx = await b.new_context(viewport={"width": w, "height": hgt}, color_scheme=theme, **dev)
    await ctx.add_init_script(seed); await ctx.add_init_script(QUIET); await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    await ctx.add_init_script("try{localStorage.setItem('chisme-location-setup','1');localStorage.setItem('chisme-swiped','1')}catch(e){}")
    pg = await ctx.new_page(); await pg.goto(URL + "/#chisme"); await ready(pg); await pg.wait_for_timeout(2500)
    await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=20000)
    for h, screen in (("#chisme", "chisme-all"), ("#news", "news"), ("#sports", "sports"), ("#events", "events"), ("#weather", "weather"), ("#antojos", "food")):
        if ONLY and screen not in ONLY: continue
        await go(pg, h, 1800 if screen == "chisme-all" else 1200)
        await audit(pg, tag, screen, ".view.active")
        await pg.evaluate("scrollTo(0, innerHeight * 1.5)"); await pg.wait_for_timeout(500)
        await audit(pg, tag, screen + "-scrolled", ".view.active", shot=screen in ("chisme-all", "weather", "food"))
    if not ONLY or "juegos" in ONLY:
        await go(pg, "#juegos", 1500)
        await audit(pg, tag, "juegos", ".view.active")
        await go(pg, "#loteria", 1500)
        await audit(pg, tag, "chismeria", ".view.active")
        start = pg.locator("#view-juegos button", has_text="Start").first
        if await start.count():
            await start.click(); await pg.wait_for_timeout(2500)
            await audit(pg, tag, "chismeria-playing", None)
            x = pg.locator(".gfs-x"); 
            if await x.count() and await x.first.is_visible(): await x.first.click(); await pg.wait_for_timeout(500)
        await go(pg, "#juan", 1500)
        await audit(pg, tag, "juan", ".view.active")
        sk = pg.locator(".juan-sk-btn").first
        if await sk.count():
            await sk.click(); await pg.wait_for_timeout(900)
            await audit(pg, tag, "juan-skins", "dialog.juan-skins")
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    if not ONLY or "settings" in ONLY:
        await go(pg, "#chisme", 800)
        await pg.click("#settings-btn"); await pg.wait_for_timeout(800)
        await audit(pg, tag, "settings", "#settings")
        n = await pg.evaluate("(() => { const d = document.querySelector('#settings'); const s = [...d.querySelectorAll('*')].find(e => e.scrollHeight > e.clientHeight + 20 && /(auto|scroll)/.test(getComputedStyle(e).overflowY)) || d; return Math.ceil(s.scrollHeight / s.clientHeight); })()")
        for i in range(1, min(n, 8)):
            await pg.evaluate(f"(() => {{ const d = document.querySelector('#settings'); const s = [...d.querySelectorAll('*')].find(e => e.scrollHeight > e.clientHeight + 20 && /(auto|scroll)/.test(getComputedStyle(e).overflowY)) || d; s.scrollTop = s.clientHeight * {i} * .9; }})()")
            await pg.wait_for_timeout(250)
            await audit(pg, tag, f"settings-{i}", "#settings", shot=i <= 3)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    if not ONLY or "tia" in ONLY:
        await pg.click("#tia-btn"); await pg.wait_for_timeout(600)
        await audit(pg, tag, "tia-menu", "#tia-menu")
        await pg.click("#tia-menu-chat"); await pg.wait_for_timeout(900)
        await audit(pg, tag, "tia-chat", "#tia")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    if not ONLY or "legal" in ONLY:
        for path in ("privacy", "terms"):
            await pg.goto(URL + "/" + path); await pg.wait_for_timeout(600)
            await audit(pg, tag, path)
            await pg.evaluate("scrollTo(0, document.body.scrollHeight / 2)"); await pg.wait_for_timeout(200)
            await audit(pg, tag, path + "-mid", shot=False)
    await ctx.close()

async def main():
    async with async_playwright() as pw:
        for bname, bt, dev, themes in (("iphone", pw.webkit, dict(is_mobile=True, has_touch=True, device_scale_factor=2), ("light", "dark")),
                                       ("android", pw.chromium, dict(is_mobile=True, has_touch=True, device_scale_factor=2), ("light",))):
            b = await bt.launch()
            for w in (375, 320):
                for theme in themes:
                    print(f"== {bname} {w} {theme}")
                    try: await run(b, bname, dev, w, theme)
                    except Exception as ex: check(False, f"{bname} {w} {theme}: the sweep stopped: {type(ex).__name__}: {str(ex)[:200]}")
            await b.close()
    json.dump(found, open(f"{OUT}/findings.json", "w"), indent=1, ensure_ascii=False)
asyncio.run(main())
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
