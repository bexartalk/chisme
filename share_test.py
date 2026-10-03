"""Share Chisme (v28), WebKit iPhone 13: a small pill in the footer. With the Web Share API it hands the phone's share
sheet the title, text and link; without it the link is copied and a 'Link copied!' toast shows. Nothing opens outside
the app. Screenshot: share-button.png (the pill in the footer | the toast after copying)."""
import asyncio, io, os
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from PIL import Image

BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"); os.makedirs(OUT, exist_ok=True)
INIT = "if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-swiped','1'); }"
WANT = {"title": "Chisme", "text": "Chisme. Did you hear? 👀 Local news, weather, food & events:", "url": "https://chisme.onrender.com/"}
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

async def page(p, stub):
    b = await p.webkit.launch()
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); await ctx.add_init_script(INIT); await ctx.add_init_script(stub)
    pg = await ctx.new_page(); errs, pops = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160])); ctx.on("page", lambda n: pops.append(n.url))
    await pg.goto(BASE + "/"); await pg.wait_for_function("window.__chisme && __chisme.ready && document.querySelector('#near-list .story')", timeout=120000)
    await pg.evaluate("document.querySelector('#share-btn').scrollIntoView({block: 'center'})"); await pg.wait_for_timeout(500)
    return b, pg, errs, pops

async def main():
    async with async_playwright() as p:
        print("== with the Web Share API (iPhone)")
        b, pg, errs, pops = await page(p, "window.__shared = []; navigator.share = (d) => { window.__shared.push(d); return Promise.resolve(); };")
        box = await pg.evaluate("""() => { const b = document.querySelector('#share-btn'), r = b.getBoundingClientRect(), cs = getComputedStyle(b);
            return { text: b.textContent.trim(), h: r.height, w: r.width, inFoot: !!b.closest('footer'), fs: parseFloat(cs.fontSize), vw: innerWidth }; }""")
        check(box["inFoot"] and "Share Chisme" in box["text"], f"a 'Share Chisme' pill in the footer ({box['text']})")
        check(44 <= box["h"] <= 52 and box["w"] < box["vw"] * 0.6 and box["fs"] < 19, f"small and subtle, still a 44px tap target ({box})")
        top = await pg.screenshot()
        await pg.tap("#share-btn"); await pg.wait_for_timeout(300)
        shared = await pg.evaluate("window.__shared")
        check(shared == [WANT], f"the phone's share sheet gets the title, text and link ({shared})")
        check(await pg.is_hidden("#share-toast"), "no toast when the share sheet handled it")
        check(not pops and not errs, f"nothing opened, no errors ({pops[:1]}, {errs[:2]})")
        await b.close()
        print("\n== without it: copy the link")
        b, pg, errs, pops = await page(p, "delete Navigator.prototype.share; Object.defineProperty(navigator, 'share', { value: undefined }); window.__copied = []; Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__copied.push(t); return Promise.resolve(); } } });")
        await pg.tap("#share-btn"); await pg.wait_for_selector("#share-toast:not([hidden])", timeout=5000)
        toast = await pg.text_content("#share-toast"); copied = await pg.evaluate("window.__copied")
        check(copied == [WANT["url"]] and toast == "Link copied!", f"link copied + toast ({copied}, {toast!r})")
        after = await pg.screenshot()
        await pg.wait_for_timeout(3000)
        check(await pg.is_hidden("#share-toast"), "the toast goes away by itself")
        check(not pops and not errs, f"nothing opened, no errors ({pops[:1]}, {errs[:2]})")
        await b.close()
        a, c = Image.open(io.BytesIO(top)), Image.open(io.BytesIO(after))
        both = Image.new("RGB", (a.width * 2 + 24, a.height), "white"); both.paste(a, (0, 0)); both.paste(c, (a.width + 24, 0))
        both.save(os.path.join(OUT, "share-button.png"))
    print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
