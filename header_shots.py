"""WebKit iPhone 13 (390x844) shots of the header mockup:
screenshots/header-mockup-light.png, header-mockup-dark.png, header-mockup-crop.png (+ extra review shots in /tmp/wk)."""
import asyncio, os, sys
from playwright.async_api import async_playwright
URL = "http://localhost:8211/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
EXTRA = "/tmp/wk"

async def shot(p, b, name, theme="light", loc=None, font=None, width=390, clip=None, out=OUT):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    if width != 390: dev["viewport"] = {"width": width, "height": 844}; dev["screen"] = {"width": width, "height": 844}
    ctx = await b.new_context(**dev)
    init = f"localStorage.setItem('chisme-theme', '{theme}'); localStorage.setItem('chisme-location-setup', '1'); localStorage.setItem('chisme-ios-hint-dismissed', '1');"
    if loc: init += f"localStorage.setItem('chisme-location', JSON.stringify({loc}));"
    if font: init += f"localStorage.setItem('chisme-font-px', '{font}');"
    await ctx.add_init_script("if (!sessionStorage.getItem('x')) { sessionStorage.setItem('x', 1); " + init + " }")
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    await pg.goto(URL)
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    for sel in ("#ios-hint-close",):
        if await pg.is_visible(sel): await pg.click(sel)
    try: await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=12000)
    except Exception: pass
    await pg.wait_for_timeout(500)
    info = await pg.evaluate("""() => {
        const pt = (svg, x, y) => {   // viewBox point -> screen px (xMidYMid meet / xMidYMax slice), from the element's box
            const r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, slice = svg.classList.contains('skyline');
            const k = (slice ? Math.max : Math.min)(r.width / vb.width, r.height / vb.height);
            const ox = (r.width - vb.width * k) / 2, oy = slice ? r.height - vb.height * k : (r.height - vb.height * k) / 2;
            return [Math.round(r.left + ox + (x - vb.x) * k), Math.round(r.top + oy + (y - vb.y) * k)]; };
        const bub = document.querySelector('.bubble'), sky = document.querySelector('.skyline'), tb = document.querySelector('#topbar');
        const tail = pt(bub, 172, 601), pod = pt(sky, 663, 92), spire = pt(sky, 649, 64);
        const picado = document.querySelector('.topbar .picado').getBoundingClientRect().top;
        return { skyline: tb.dataset.skyline, label: document.querySelector('#settings-btn').getAttribute('aria-label'), h1: document.querySelector('h1').textContent,
                 traced: !!document.querySelector('.bubble .bubble-word[d]'), topbarH: tb.offsetHeight, tailTip: tail, towerPodRight: pod, spireTop: spire,
                 tailClearOfTower: tail[0] - pod[0], tailAbovePicado: Math.round(picado - tail[1]) }; }""")
    await pg.screenshot(path=os.path.join(out, name), **({"clip": clip} if clip else {}))
    await pg.tap("#settings-btn"); await pg.wait_for_timeout(500)
    info["opensSettings"] = await pg.evaluate("document.querySelector('#settings').open")
    if name == "header-mockup-light.png": await pg.screenshot(path=os.path.join(EXTRA, "bubble-tapped-settings.png"))
    print(name, info, "errors:", errs[:3])
    await ctx.close()

async def radar_shot(p, b):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev)
    await ctx.add_init_script("if (!sessionStorage.getItem('x')) { sessionStorage.setItem('x', 1); localStorage.setItem('chisme-location-setup', '1'); localStorage.setItem('chisme-ios-hint-dismissed', '1'); }")
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    await pg.goto(URL)
    await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=90000)
    if await pg.is_visible("#ios-hint-close"): await pg.click("#ios-hint-close")
    await pg.click('#tabs [data-view="weather"]'); await pg.wait_for_timeout(800)
    await pg.evaluate("window.scrollTo(0, document.querySelector('#radar-sec').getBoundingClientRect().top + scrollY - document.querySelector('#tabs').offsetHeight - 8)")
    await pg.wait_for_function("() => document.querySelectorAll('.radar-tiles img.leaflet-tile').length >= 4 && document.querySelector('.me-marker')", timeout=30000)
    try: await pg.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=12000)
    except Exception: pass
    await pg.wait_for_timeout(1500)
    info = await pg.evaluate("""() => ({ meButton: !!document.querySelector('#r-center'), meText: [...document.querySelectorAll('.radar-controls button')].map(b => b.textContent.trim()),
        blueDot: !!document.querySelector('.me-marker .me-dot'), dot: getComputedStyle(document.querySelector('.me-dot')).backgroundColor,
        controlsFit: [...document.querySelectorAll('.radar-controls > *')].every(e => e.getBoundingClientRect().right <= innerWidth) })""")
    await pg.screenshot(path=os.path.join(OUT, "weather-radar-no-me.png"))
    print("weather-radar-no-me.png", info, "errors:", errs[:3])
    await ctx.close()

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        if os.environ.get('RADAR'): await radar_shot(p, b)
        await shot(p, b, "header-mockup-light.png")
        await shot(p, b, "header-mockup-dark.png", theme="dark")
        await shot(p, b, "header-mockup-crop.png", clip={"x": 0, "y": 0, "width": 390, "height": 236})
        await shot(p, b, "crop-dark.png", theme="dark", clip={"x": 0, "y": 0, "width": 390, "height": 236}, out=EXTRA)
        await shot(p, b, "crop-bigtext.png", font=30, clip={"x": 0, "y": 0, "width": 390, "height": 330}, out=EXTRA)
        austin = '{"lat":30.2672,"lon":-97.7431,"source":"manual","label":"Austin, TX","place":{"city":"Austin","county":"Travis County","state":"TX"}}'
        await shot(p, b, "crop-austin.png", loc=austin, clip={"x": 0, "y": 0, "width": 390, "height": 236}, out=EXTRA)
        await shot(p, b, "crop-320.png", width=320, clip={"x": 0, "y": 0, "width": 320, "height": 236}, out=EXTRA)
        await shot(p, b, "crop-desktop.png", width=1280, clip={"x": 0, "y": 0, "width": 1280, "height": 236}, out=EXTRA)
        await b.close()
asyncio.run(main())
