"""v49.5 Lotería Chismosa in the classic-deck look: the tabla is a clean white printed grid (1 px dark lines, white cells, no
rounded corners or shadows), in light AND dark mode (the full-screen page stays cream, the strip buttons keep their colours),
at 390×844 and 320×640: 16 cards loaded, nothing scrolls, no page errors. Also checks the stylesheet has no stray `}` (one
swallowed the cream full-screen page rule, so the verse was dark-on-dark). Screenshots: loteria-tabla-new.png (tabla, light 390)
and loteria-cards-new.png (20 of the 54 new cards, light 390)."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
import asyncio, sys, json
from playwright.async_api import async_playwright
from popup_quiet import QUIET
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true})); localStorage.setItem('chisme-notif', JSON.stringify({n:1}));"
SPEECH = """(() => { const fake = { speak(u) { setTimeout(() => u.onend && u.onend(), 60); }, cancel() {}, getVoices() { return [{ lang: 'es-MX', name: 'T' }]; }, addEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {} window.SpeechSynthesisUtterance = function (t) { this.text = t; }; })()"""
G = "__chisme.juegos.game"
M = """() => { const t = document.querySelector('#lot-tabla'), R = e => e.getBoundingClientRect(), cs = getComputedStyle(t), cells = [...t.querySelectorAll('.lot-cell')];
  const act = R(document.querySelector('.lot-actions')), st = document.querySelector('#game-stage'), cr = cells.map(R);
  return { n: cells.length, tbg: cs.backgroundColor, gap: cs.columnGap + '/' + cs.rowGap, border: cs.borderTopWidth + ' ' + cs.borderTopColor,
    cellBg: [...new Set(cells.filter(c => !c.classList.contains('win')).map(c => getComputedStyle(c).backgroundColor))], radius: getComputedStyle(cells[0]).borderRadius, shadow: getComputedStyle(cells[0]).boxShadow,
    t: [R(t).left, R(t).top, R(t).right, R(t).bottom].map(Math.round), vw: innerWidth, vh: innerHeight, actBottom: Math.round(act.bottom),
    scroll: st.scrollHeight > st.clientHeight + 1 || st.scrollWidth > st.clientWidth + 1, card: [Math.round(cr[0].width), Math.round(cr[0].height)],
    loaded: [...t.querySelectorAll('.lc-img')].every(i => i.complete && i.naturalWidth >= 200), dark: matchMedia('(prefers-color-scheme: dark)').matches,
    page: getComputedStyle(st).backgroundColor }; }"""
SHEET = """() => { const L = ChismeLoteriaCards, d = document.createElement('div'); d.id = 'art-sheet';
  d.style.cssText = 'position:fixed;inset:0;z-index:9000;background:#ffffff;padding:10px 8px;box-sizing:border-box;display:grid;grid-template-columns:repeat(4,1fr);gap:7px;align-content:start;overflow:hidden';
  const pick = [1, 2, 3, 4, 6, 8, 14, 17, 20, 23, 26, 28, 35, 38, 42, 46, 47, 48, 51, 54];
  d.innerHTML = '<p style="grid-column:1/-1;margin:0 0 2px;color:#0f6d73;font:900 15px system-ui;text-align:center">Lotería Chismosa · our own classic-deck art (20 of 54)</p>' + pick.map(n => { const c = L.CARDS[n - 1]; return `<img src="${c.img}" alt="${c.name}" style="width:100%;aspect-ratio:2/3;display:block;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.25)">`; }).join('');
  document.body.appendChild(d); }"""
async def main():
    async with async_playwright() as p:
        css = re.sub(r"/\*.*?\*/", "", open(os.path.join(HERE, "static", "style.css")).read(), flags=re.S); d = neg = 0
        for ch in css:
            d += (ch == "{") - (ch == "}")
            if d < 0: neg += 1; d = 0
        print("stylesheet braces balanced, no stray }:", "OK" if not neg and not d else "BAD"); bad = int(bool(neg or d))
        b = await p.webkit.launch()
        for scheme, w in [("light",390),("dark",390),("light",320),("dark",320)]:
            h = 844 if w == 390 else 640
            dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"]={"width":w,"height":h}; dev["device_scale_factor"]=2
            ctx = await b.new_context(**dev, color_scheme=scheme); await ctx.add_init_script(SETUP); await ctx.add_init_script(QUIET); await ctx.add_init_script(SPEECH)
            pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            await pg.goto(BASE + "/#loteria"); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000); await pg.wait_for_timeout(1500)
            await pg.click("#lot-play"); await pg.wait_for_timeout(500); await pg.click("#lot-play")
            for _ in range(14): await pg.evaluate(G + ".callNext()")
            s = await pg.evaluate(G + ".state")
            for i in [i for i, c in enumerate(s["tabla"]) if c in s["called"]][:4]: await pg.click(f'.lot-cell[data-i="{i}"]')
            await pg.wait_for_function("[...document.querySelectorAll('#lot-tabla .lc-img')].every(i => i.complete && i.naturalWidth)", timeout=15000); await pg.wait_for_timeout(900)
            m = await pg.evaluate(M); btn = await pg.evaluate("[getComputedStyle(document.querySelector('#lot-play')).backgroundColor, getComputedStyle(document.querySelector('#lot-claim')).backgroundColor]")
            m["btns"] = btn
            ok = (m["n"] == 16 and m["cellBg"] == ["rgb(255, 255, 255)"] and m["gap"] == "1px/1px" and m["border"].startswith("1px") and m["radius"] == "0px" and m["shadow"] == "none"
                  and m["t"][0] >= 0 and m["t"][2] <= w and m["actBottom"] <= h + 1 and not m["scroll"] and m["loaded"] and m["dark"] == (scheme == "dark") and not errs
                  and m["page"] == "rgb(247, 232, 223)" and btn == ["rgb(0, 201, 205)", "rgb(239, 66, 111)"])
            bad += not ok; print(scheme, w, "OK" if ok else "BAD", m, errs[:2])
            await pg.screenshot(path=f"/tmp/lot-tabla-{scheme}-{w}.png")
            if scheme == "light" and w == 390: await pg.screenshot(path=os.path.join(HERE, "screenshots", "loteria-tabla-new.png"))
            await pg.evaluate(SHEET); await pg.wait_for_function("[...document.querySelectorAll('#art-sheet img')].every(i => i.complete && i.naturalWidth)", timeout=15000); await pg.wait_for_timeout(300)
            fit = await pg.evaluate("[...document.querySelectorAll('#art-sheet img')].map(i => i.getBoundingClientRect().bottom).pop() <= innerHeight + 1")
            bad += not fit; print("   20 cards fit one screen:", fit)
            await pg.screenshot(path=f"/tmp/lot-cards-{scheme}-{w}.png")
            if scheme == "light" and w == 390: await pg.screenshot(path=os.path.join(HERE, "screenshots", "loteria-cards-new.png"))
            await ctx.close()
        await b.close(); print(f"{bad} FAILED" if bad else "ALL PASS"); sys.exit(1 if bad else 0)
asyncio.run(main())
