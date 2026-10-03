"""v49.12 legal quick fixes. NO_AUTO_QUIET (this test is about the one-time Terms bar). Chromium Android-size + WebKit iPhone, 320 + 390 px:
  • /privacy and /terms are real pages (200, their own title, contact email, no '[PLACEHOLDER]' left; open TODOs are marked),
    even with the service worker in control (it never serves the app shell for them)
  • first launch: the location card AND a non-modal Terms bar at the bottom; the bar covers neither the card's buttons nor Tía;
    OK hides it for good (also after a reload)
  • Settings → Privacy and the footer link both pages; the footer says who Chisme isn't affiliated with
  • the weather disclaimer sits under the alerts and in Settings → Notifications; tip buttons say tips aren't charity
  • the food feed plays with sound by default (v49.13, the owner's call; v49.12 had it muted); the API calls carry 2-decimal coordinates (/api/place keeps 3)"""
import asyncio, os, re, sys, urllib.request
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401
URL = os.environ.get("URL", "http://localhost:8211/").rstrip("/") + "/"
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))
INIT = "try { localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 })); localStorage.setItem('chisme-settings-tip', 'test:0'); localStorage.setItem('chisme-default-tab', 'news'); } catch (e) {}"
COVER = """(sel) => { const e = document.querySelector(sel); if (!e || !e.getClientRects().length) return 'missing'; const r = e.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2; if (y > innerHeight || y < 0) return 'offscreen';
  const at = document.elementFromPoint(x, y); return at && (e === at || e.contains(at)) ? 'free' : 'covered by ' + (at && (at.id || at.className)); }"""
async def main():
    for name in ("privacy", "terms"):
        with urllib.request.urlopen(URL + name, timeout=30) as r:
            body = r.read().decode(); st = r.status
        title = re.search(r"<title>(.*?)</title>", body).group(1)
        left = re.findall(r"\[[A-Z][A-Z /$]{3,}\]", body)
        check(st == 200 and ("Privacy" if name == "privacy" else "Terms") in title and "bexartalkradio@gmail.com" in body and not left and 'id="track"' not in body,
              f"/{name}: a real page ({st}, '{title}', contact email, no placeholders left {left[:3]}, {body.count('class=\"todo\"')} TODO marks)")
    async with async_playwright() as p:
        for bname, bt, dev in (("chromium", p.chromium, dict(is_mobile=True, has_touch=True, device_scale_factor=2.625)), ("webkit", p.webkit, dict(is_mobile=True, has_touch=True, device_scale_factor=3))):
            b = await bt.launch()
            for w in (320, 390):
                ctx = await b.new_context(viewport={"width": w, "height": 700}, **dev); await ctx.add_init_script(INIT)
                await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
                pg = await ctx.new_page(); calls = []
                pg.on("request", lambda rq: calls.append(rq.url) if "/api/" in rq.url and "lat=" in rq.url else None)
                await pg.goto(URL); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(800)
                VIS = "[!document.querySelector('#terms-bar').hidden, !document.querySelector('#loc-panel').hidden, document.querySelector('#terms-bar').textContent.replace(/\\s+/g, ' ').trim()]"
                vis = await pg.evaluate(VIS)
                check(not vis[0] and vis[1], f"{bname} {w}: first launch shows the location card, and the Terms bar waits (v49.12: they never share the screen) ({vis[:2]})")
                await pg.click("#loc-close"); await pg.wait_for_timeout(300)   # "Not now"
                vis = await pg.evaluate(VIS)
                check(vis[0] and not vis[1] and "By using Chisme you agree to our Terms and Privacy Policy" in vis[2], f"{bname} {w}: once the card is answered (Not now), the Terms bar shows ({vis})")
                # v49.12: while the sync toast is up the Terms bar steps aside (CSS); it's back once the toast is done
                await pg.wait_for_function("() => { const s = document.querySelector('#sync'); return s.hidden || s.dataset.state === 'done'; }", timeout=45000); await pg.wait_for_timeout(400)
                tia = "#tia-btn" if await pg.is_visible("#tia-btn") else "#fb-tia"   # v49.15 phones: Tía is in the top bar
                cov = {s: await pg.evaluate(COVER, s) for s in (tia, "#terms-ok")}
                tb = await pg.evaluate("(sel) => { const b = document.querySelector('#terms-bar').getBoundingClientRect(), t = document.querySelector(sel).getBoundingClientRect(), n = document.querySelector('#tabs').getBoundingClientRect(), nav = getComputedStyle(document.querySelector('#tabs')).bottom === '0px'; return [b.right <= t.left || b.bottom <= t.top || b.top >= t.bottom, b.left >= 0 && b.right <= innerWidth && b.bottom <= innerHeight, !nav || b.bottom <= n.top + 0.5] }", tia)
                check(cov["#terms-ok"] == "free" and cov[tia] == "free" and all(tb), f"{bname} {w}: the bar is on screen and clear of Tía and the tab bar ({cov}, {tb})")
                links = await pg.evaluate("[...document.querySelectorAll('#terms-bar a')].map(a => a.getAttribute('href'))")
                check(links == ["/terms", "/privacy"], f"{bname} {w}: the bar links /terms and /privacy ({links})")
                await pg.click("#terms-ok"); await pg.wait_for_timeout(200)
                gone = await pg.evaluate("[document.querySelector('#terms-bar').hidden, !!localStorage.getItem('chisme-terms-ok')]")
                await pg.reload(); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000); await pg.wait_for_timeout(300)
                again = await pg.evaluate("document.querySelector('#terms-bar').hidden")
                check(gone == [True, True] and again, f"{bname} {w}: OK hides it and it stays gone after a reload ({gone}, {again})")
                if w == 390:
                    t = await pg.evaluate("""() => ({ set: [...document.querySelectorAll('#set-privacy a')].map(a => a.getAttribute('href')), foot: [...document.querySelectorAll('.foot-legal a')].map(a => a.getAttribute('href')),
                      affil: (document.querySelector('.foot-affil') || {}).textContent || '', wx: (document.querySelector('#wx-disclaimer') || {}).textContent || '', wxs: (document.querySelector('#set-wx-disclaimer') || {}).textContent || '',
                      tips: document.querySelectorAll('.donate-fine').length, tipsTxt: (document.querySelector('.donate-fine') || {}).textContent, sound: document.querySelector('#set-feed-sound').checked,
                      tia: document.querySelector('.tia-foot').textContent, priv: document.querySelector('#set-privacy-note').textContent,
                      after: document.querySelector('#alerts').nextElementSibling && document.querySelector('#alerts').nextElementSibling.id })""")
                    check(t["set"][:2] == ["/privacy", "/terms"] and t["foot"][:2] == ["/privacy", "/terms"], f"{bname}: Settings → Privacy and the footer link both pages ({t['set']}, {t['foot']})")
                    check(all(k in t["affil"] for k in ("Spurs", "NBA", "Lotería publisher", "National Weather Service", "Immigration and Customs Enforcement")), "footer: not affiliated with the Spurs/NBA, Lotería publishers, NWS/ICE")
                    check("isn't an official warning service" in t["wx"] and t["after"] == "wx-disclaimer" and "weather.gov" in t["wxs"], "weather disclaimer under the alerts and in Settings → Notifications")
                    check(t["tips"] >= 7 and t["tipsTxt"] == "Tips go to the Chisme creator; not a charity, not tax-deductible, unlocks nothing.", f"tip note under every set of tip buttons ({t['tips']})")
                    check(t["sound"] and await pg.evaluate("localStorage.getItem('chisme-feed-sound')") is None, "food videos: sound ON by default (v49.13: the owner's call, reverses v49.12 legal M4/L20 — review)")
                    check("Google" in t["tia"] and "Chats stay on this phone" not in t["tia"] and "No names" not in t["priv"] and "public" in t["priv"], f"accurate privacy wording (Tía: {t['tia'][:60]}…)")
                    qs = [re.search(r"lat=([-\d.]+)&lon=([-\d.]+)", u) for u in calls]
                    dec = {(u.split("/api/")[1].split("?")[0], len(m.group(1).split(".")[1]) if "." in m.group(1) else 0) for u, m in zip(calls, qs) if m}
                    check(dec and all(d <= 2 for a, d in dec if a != "place") and all(d <= 3 for a, d in dec), f"{bname}: API calls carry ≤2-decimal coordinates (place ≤3) {sorted(dec)}")
                    # the service worker never answers /privacy with the app shell
                    await pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=30000)
                    await pg.goto(URL + "privacy"); await pg.wait_for_load_state("domcontentloaded")
                    check("Privacy Policy" in await pg.title() and not await pg.evaluate("!!document.querySelector('#track')"), f"{bname}: with the service worker in control, /privacy is the real page ({await pg.title()})")
                await ctx.close()
            await b.close()
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL(S)"); sys.exit(1 if fails else 0)
asyncio.run(main())
