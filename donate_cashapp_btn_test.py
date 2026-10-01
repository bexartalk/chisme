"""v47: the Cash App tag lives INSIDE the green button on every donate card: the bottom card on every tab, Settings,
the every-5th-open mid-list card, the every-7 cards in News and the For You food feed's donate slide.
It reads "💸 Donate on Cash App · $Slurmkaos" on one line when the button is wide enough, else $Slurmkaos sits on a
2nd line inside the button (no "·"), and the old separate "$Slurmkaos" line under the buttons is gone.
Checked at 390×844 and 320×640 (WebKit iPhone) and 1280×900 (Chromium desktop): the text never overflows the button,
the button stays 48+ px tall, black on Cash App green, and it still opens https://cash.app/$Slurmkaos outside the app.
Screenshot: donate-cashapp-btn.png (the News donate card at 390×844)."""
import asyncio, os, re
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = """if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }
localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); localStorage.setItem('chisme-opens', '4');"""   # (opens 4 → this load is the 5th: the mid-list card shows)
TABS = ["news", "sports", "weather", "antojos", "juegos", "events"]
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

# every visible Cash App button under `sel`: its label, where the tag sits, and whether everything fits inside the button
CA = """(sel) => [...document.querySelectorAll(sel)].flatMap((r) => [...r.querySelectorAll('a.donate-btn.cashapp')]).filter((a) => a.getClientRects().length && a.getBoundingClientRect().width > 0).map((a) => {
  const t = a.querySelector('.ca-tag'), m = a.querySelector('.ca-main'), d = a.querySelector('.ca-dot'), ra = a.getBoundingClientRect(), cs = getComputedStyle(a);
  const inside = (e) => { const r = e.getBoundingClientRect(); return r.left >= ra.left - 0.5 && r.right <= ra.right + 0.5 && r.top >= ra.top - 0.5 && r.bottom <= ra.bottom + 0.5; };
  const rt = t && t.getBoundingClientRect(), rm = m && m.getBoundingClientRect(), card = a.closest('.donate, #set-donate, .vf-donate, .card') || a.parentElement;
  return { card: card.id || card.className, label: a.textContent.replace(a.querySelector('.sr-only')?.textContent || '', '').replace(/\\s+/g, ' ').trim(),
    seen: a.innerText.replace(a.querySelector('.sr-only')?.textContent.trim() || '', '').replace(/\\s+/g, ' ').trim(),   /* what you see (innerText minus the screen-reader note) */ tag: t ? t.textContent : null, href: a.getAttribute('href'), target: a.target,
    inside: !!(t && m && inside(t) && inside(m) && inside(a.firstElementChild)), ov: a.scrollWidth > a.clientWidth + 1,
    line: rt && rm ? (Math.abs(rt.top - rm.top) < 4 ? 1 : 2) : 0, dot: !!d && getComputedStyle(d).display !== 'none',
    below: rt && rm ? rt.top >= rm.bottom - 2 : false, h: Math.round(ra.height), w: Math.round(ra.width), bg: cs.backgroundColor, fg: cs.color }; })"""

def good(b, w):
    want = "💸 Donate on Cash App · $Slurmkaos"
    if b["label"] != want or b["tag"] != "$Slurmkaos" or b["href"] != "https://cash.app/$Slurmkaos" or b["target"] != "_blank": return False
    if not b["inside"] or b["ov"] or b["h"] < 48 or b["bg"] not in ("rgb(0, 214, 50)", "rgb(0, 226, 54)"): return False   # (the 2nd: :hover, the mouse may be resting on it)
    if b["line"] == 1: return b["dot"] and b["seen"] == want   # one line: "… · $Slurmkaos"
    return b["line"] == 2 and b["below"] and not b["dot"] and b["seen"].replace(" ", "") == want.replace(" · ", "").replace(" ", "")   # 2nd line: no dot

async def run(pg, label, w, shot=None):
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.newsReady", timeout=120000); await pg.wait_for_timeout(900)
    print(f"\n== {label}")
    check(await pg.evaluate("document.querySelectorAll('.donate-tag').length") == 0, f"{w}px: no separate '$Slurmkaos' line under the buttons anywhere")
    allb = []
    for v in TABS:
        await pg.evaluate(f"__chisme.goView('{v}', {{ instant: true }})"); await pg.wait_for_timeout(500)
        bs = await pg.evaluate(CA, f"#view-{v}")
        bottom = [b for b in bs if b["card"].startswith("donate-") and b["card"] != "donate-mid"]
        check(bottom and all(good(b, w) for b in bs), f"{w}px {v}: {len(bs)} donate button(s) (bottom card {bottom[0]['card'] if bottom else None}) read '💸 Donate on Cash App · $Slurmkaos', tag inside, nothing overflows ({[(b['card'][:14], b['line'], b['w'], b['h']) for b in bs]})")
        allb += bs
        if v == "news":
            kinds = {("mid" if b["card"] == "donate-mid" else "every7" if "donate-every" in b["card"] else "bottom") for b in bs}
            check({"mid", "every7", "bottom"} <= kinds, f"{w}px News: the bottom card, the mid-list card and the every-7 cards all checked ({sorted(kinds)})")
            if shot:
                await pg.evaluate("document.querySelector('#donate-news').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(600)
                await pg.screenshot(path=os.path.join(OUT, shot))
    await pg.evaluate("__chisme.goView('news', { instant: true })")
    await pg.click("#settings-btn"); await pg.wait_for_function("document.querySelector('#settings').open"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('#set-donate').scrollIntoView({ block: 'center' })"); await pg.wait_for_timeout(300)
    bs = await pg.evaluate(CA, "#set-donate")
    check(len(bs) == 1 and good(bs[0], w), f"{w}px Settings → Support Chisme: the same button ({[(b['line'], b['w']) for b in bs]})")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
    await pg.evaluate("__chisme.goView('antojos', { instant: true })")
    await pg.wait_for_function("__chisme.foodReady && document.querySelector('#fy-start')", timeout=90000); await pg.wait_for_timeout(500)
    await pg.click("#fy-start"); await pg.wait_for_function("document.querySelector('#feed').open", timeout=8000); await pg.wait_for_timeout(800)
    await pg.evaluate("(i) => { const s = document.querySelector('#feed-scroll'); s.scrollTo({ top: i * s.clientHeight, behavior: 'instant' }); }", 7); await pg.wait_for_timeout(1000)
    bs = await pg.evaluate(CA, "#feed-scroll .vf-donate")
    check(bs and all(good(b, w) for b in bs), f"{w}px the For You food feed's donate slide: the same button ({[(b['line'], b['w']) for b in bs]})")
    allb += bs
    check(not errs, f"no page errors ({errs[:2]})")
    return allb

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
        for vw, vh, shot in ((390, 844, "donate-cashapp-btn.png"), (320, 640, "donate-cashapp-btn-320.png")):
            d = dict(dev); d["viewport"] = {"width": vw, "height": vh}
            ctx = await b.new_context(**d, service_workers="block"); await ctx.add_init_script(INIT); pg = await ctx.new_page()
            bs = await run(pg, f"WebKit iPhone {vw}×{vh}", vw, shot)
            if vw == 320: check(all(x["line"] == 2 for x in bs), f"320px: it doesn't fit on one line there, so $Slurmkaos is on a 2nd line inside every button ({sorted({x['w'] for x in bs})} px wide)")
            await ctx.close()
        await b.close()
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 900}, service_workers="block"); await ctx.add_init_script(INIT); pg = await ctx.new_page()
        bs = await run(pg, "Chromium desktop 1280×900", 1280)
        await b.close()
    print("\nALL PASS" if not fails else f"\n{fails} FAILED"); raise SystemExit(1 if fails else 0)

asyncio.run(main())
