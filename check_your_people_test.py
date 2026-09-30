"""v42: News' first section is "Check Your People" (was "Near You"). WebKit, iPhone 13 at 390×844, against the local server.
- the heading says Check Your People, the section is labelled by it (aria-labelledby), no "Near You" anywhere on the page,
  in Settings, or in the home-screen shortcuts; the id and the #near link still work
- the location line ("Closest first: …") is at the BOTTOM of the section: after its last story, above the next section,
  smaller and quieter than the stories; the "Updated … CDT" stamp stays by the heading
Screenshots: check-your-people.png (the heading), check-your-people-bottom.png (the location line at the section's bottom)."""
import asyncio, json, os, sys, urllib.request
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "screenshots"); BASE = os.environ.get("BASE", "http://localhost:8211")
FAILS = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: FAILS.append(what)

# Lavaca / Downtown San Antonio; setup done so the one-time location card and tutorial stay out of the way
LAT, LON = 29.4155, -98.4905
INIT = ("if (!localStorage.getItem('chisme-location-setup')) { localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-ios-hint-dismissed','1');"
        " localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true })); }"
        " try { window.speechSynthesis && (speechSynthesis.speak = () => {}); } catch (e) {}")

LAYOUT = """() => { const s = document.querySelector('#near'), h = s.querySelector('h2'), hint = document.querySelector('#near-hint');
  const stories = [...s.querySelectorAll('#near-list .story')], last = stories[stories.length - 1], next = document.querySelector('#city');
  const cs = getComputedStyle(hint), story = stories[0] && getComputedStyle(stories[0].querySelector('h3'));
  const r = (e) => e.getBoundingClientRect(), y = window.scrollY;
  return { title: h.textContent.trim(), labelledby: s.getAttribute('aria-labelledby'), labelIsH2: document.getElementById(s.getAttribute('aria-labelledby')) === h,
    stampInHead: !!s.querySelector('.sec-head #news-updated'), stamp: document.querySelector('#news-updated').textContent,
    hint: hint.textContent, hintLast: s.lastElementChild === hint, hintInSection: s.contains(hint), stories: stories.length,
    belowLast: last ? r(hint).top >= r(last).bottom - 1 : false, aboveNext: r(hint).bottom <= r(next).top + 1, belowHead: r(hint).top > r(h).bottom,
    hintPx: parseFloat(cs.fontSize), storyPx: story ? parseFloat(story.fontSize) : 0, opacity: +cs.opacity, color: cs.color,
    hintTop: r(hint).top + y, hintBottom: r(hint).bottom + y, headTop: r(s).top + y,
    nearYou: /near you/i.test(document.querySelector('#view-news').innerText) }; }"""

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}; dev["screen"] = {"width": 390, "height": 844}
        ctx = await b.new_context(**dev, permissions=["geolocation"], geolocation={"latitude": LAT, "longitude": LON})
        await ctx.add_init_script(INIT); pg = await ctx.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await pg.goto(BASE + "/")
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=120000)
        await pg.wait_for_function("() => document.querySelectorAll('#near-list .story').length > 0 && /Closest first/.test(document.querySelector('#near-hint').textContent)", timeout=120000)
        try: await pg.wait_for_function("() => window.__chisme.sync.busy.length === 0 && document.querySelector('#sync').dataset.state !== 'busy'", timeout=60000)
        except Exception: pass
        await pg.wait_for_timeout(3500)   # the "Updated" pill fades away
        L = await pg.evaluate(LAYOUT)
        print("== the heading")
        check(L["title"] == "Check Your People", f"News' first section is called 'Check Your People' ({L['title']!r})")
        check(L["labelIsH2"], f"…and the section is labelled by that heading (aria-labelledby={L['labelledby']})")
        check(L["stampInHead"] and L["stamp"].startswith(("Updated", "Saved")), f"the '{L['stamp']}' stamp stays by the heading")
        check(not L["nearYou"], "no 'Near You' left anywhere in News")
        print("== the location line at the bottom of the section")
        check(L["hint"].startswith("Closest first:") and "→" in L["hint"], f"the location line: {L['hint']!r}")
        check(L["hintInSection"] and L["hintLast"], "it's the last thing in the section")
        check(L["belowLast"] and L["belowHead"], f"…below the section's last story ({L['stories']} stories), not under the heading")
        check(L["aboveNext"], "…and above the next section (More local news)")
        check(L["hintPx"] < L["storyPx"] and L["hintPx"] <= 15 and L["opacity"] < 1, f"small and subtle ({L['hintPx']:.1f} px vs {L['storyPx']:.1f} px headlines, opacity {L['opacity']}, {L['color']})")
        await pg.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)"); await pg.wait_for_timeout(300)
        await pg.evaluate("(y) => window.scrollTo(0, y)", max(0, L["headTop"] - 120)); await pg.wait_for_timeout(700)
        await pg.screenshot(path=os.path.join(OUT, "check-your-people.png"))
        await pg.evaluate("(y) => window.scrollTo(0, y)", max(0, L["hintBottom"] - 844 + 260)); await pg.wait_for_timeout(700)
        vis = await pg.evaluate("() => { const r = document.querySelector('#near-hint').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }")
        check(vis, "bottom screenshot shows the location line")
        await pg.screenshot(path=os.path.join(OUT, "check-your-people-bottom.png"))
        print("== Settings, shortcuts, #near")
        await pg.click("#settings-btn"); await pg.wait_for_timeout(500)
        st = await pg.evaluate("() => { const s = document.querySelector('#settings, #settings-sheet, dialog[open]'); return s ? s.innerText : document.body.innerText; }")
        check("near you" not in st.lower() or "check your people" in st.lower(), "Settings doesn't call it 'Near You'")
        await pg.click("#settings-close")
        html = await (await pg.request.get(BASE + "/")).text()
        check(">Near You<" not in html and "Check Your People" in html, "the page HTML says Check Your People")
        man = json.loads(await (await pg.request.get(BASE + "/manifest.webmanifest")).text())
        sc = [s for s in man.get("shortcuts", []) if s.get("url", "").endswith("#near")]
        check(sc and sc[0]["name"] == "Check Your People", f"the home-screen shortcut to #near is called 'Check Your People' ({[s['name'] for s in sc]})")
        await pg.goto(BASE + "/#near"); await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=120000); await pg.wait_for_timeout(1500)
        a = await pg.evaluate("() => ({ view: window.__chisme.view, top: document.querySelector('#near').getBoundingClientRect().top })")
        check(a["view"] == "news" and -5 < a["top"] < 400, f"#near still opens News at Check Your People ({a})")
        check(not errs, f"no page errors ({errs[:3]})")
        await b.close()
    print("\nALL PASS" if not FAILS else f"\n{len(FAILS)} FAIL(S)"); sys.exit(1 if FAILS else 0)

asyncio.run(main())
