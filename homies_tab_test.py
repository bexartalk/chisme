"""v49.22: the Homies tab. The bottom tab bar is Homies · ¿Y la dieta? (Ofrendas in the Día de Muertos season) · Chisme ·
Juegos · Tía, with Chisme in the middle.
  • Homies opens your own profile (the page with the 🤝 Your Homies section) and is the current tab while it shows (the same
    pink pill + bar as the other tabs); signed out it opens Sign in / Join. Its icon is its own art: two homies fist-bumping.
  • 5 tabs, one row, 44 px+ targets, nothing wraps (but '¿Y la dieta?', which may take 2 lines) or spills past the edge at
    320, 360, 390 and 430 px; Chisme's tab sits in the middle of the screen; no yellow on the bar.
  • the bar still slides away on scroll down and comes back on scroll up with your profile open; Chisme / other tabs leave it.
  • desktop (1280): no Homies tab (nor Tía's), Chisme stays first in the top nav.
Starts its own server (local social backend + the fake email codes) on PORT (default 8481).
Screenshots: SHOTS (default /workspace/chisme-navswap-shots) homies-chisme-390/320.png, homies-profile-390/320.png."""
import asyncio, os, re, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pw_csp  # noqa: F401
from playwright.async_api import async_playwright

PORT = int(os.environ.get("PORT", "8481"))
SHOTS = os.environ.get("SHOTS", "/workspace/chisme-navswap-shots")
os.makedirs(SHOTS, exist_ok=True)
fails = 0


def check(ok, what):
    global fails
    print(("PASS " if ok else "FAIL ") + what)
    if not ok: fails += 1


def start():
    tmp = tempfile.mkdtemp(prefix="chisme-homies-")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UPSTASH_", "RENDER", "SUPABASE_", "R2_", "TURNSTILE_", "CSAM_", "SOCIAL_"))}
    env.update(SOCIAL_FAKE_AUTH="1", SOCIAL_DIR=f"{tmp}/social", SIGNUPS_PUBLIC="1", NEW_USER_REVIEW="0", PUSH_STORE_FILE=f"{tmp}/push.json",
               STATS_STORE_FILE=f"{tmp}/stats.json", AUTO_PUSH_WAKE_DELAY="9999", OWNER_POSTS_DIR=f"{tmp}/posts", PYTHONUNBUFFERED="1")
    logp = f"{tmp}/server.log"
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(PORT)],
                            cwd=HERE, env=env, stdout=open(logp, "w"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{PORT}/"
    for _ in range(120):
        try:
            if urllib.request.urlopen(url + "healthz", timeout=2).status == 200: return proc, url, logp
        except Exception: pass
        time.sleep(0.5)
    proc.kill(); raise RuntimeError("server didn't start: " + logp)


INIT = ("try{localStorage.setItem('chisme-location-setup','done');localStorage.setItem('chisme-default-tab','chisme');"
        "localStorage.setItem('chisme-muertos-banner-x','1');localStorage.setItem('chisme-season-pin','%s')}catch(e){}")
TABS = """() => [...document.querySelectorAll('#tabs .tab')].filter((t) => t.getClientRects().length).map((t) => { const r = t.getBoundingClientRect();
  const lab = t.querySelector('.tab-l') || t, rg = document.createRange(); rg.selectNodeContents(lab);
  const lines = new Set([...rg.getClientRects()].filter((q) => q.width > 1).map((q) => Math.round(q.top))).size;
  return { id: t.dataset.view || t.id, l: t.textContent.trim(), w: r.width, h: r.height, x: r.left, right: r.right, top: Math.round(r.top),
    cur: t.getAttribute('aria-current'), lines, spill: t.scrollWidth > t.clientWidth + 1, vw: innerWidth }; })"""
YELLOW = """() => { const y = (s) => { const m = s.match(/[\\d.]+/g); if (!m) return false; let [r, g, b, a] = m.map(Number); if (a != null && a < .1) return false;
  r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); if (mx - mn < .25 || mx < .5) return false;
  let h = mx === r ? 60 * (((g - b) / (mx - mn)) % 6) : mx === g ? 60 * ((b - r) / (mx - mn) + 2) : 60 * ((r - g) / (mx - mn) + 4); if (h < 0) h += 360; return h > 42 && h < 70; };
  const out = []; for (const n of document.querySelectorAll('#tabs, #tabs *')) { const cs = getComputedStyle(n);
    for (const p of ['color', 'backgroundColor', 'borderTopColor']) if (y(cs[p])) out.push(n.className + ' ' + p + ' ' + cs[p]);
    for (const ps of ['::before', '::after']) { const c = getComputedStyle(n, ps); if (c.content !== 'none' && y(c.backgroundColor)) out.push(n.className + ps); } } return out; }"""


async def signup(pg, url, logp, user):
    import json
    cfg = await (await pg.request.get(url + "api/social/config")).json()
    a, b = map(int, re.findall(r"\d+", cfg["challenge"]["question"]))
    await asyncio.sleep(3)   # the bot check wants more than 2 s on the form
    email = f"{user}@example.com"
    H = {"origin": url.rstrip("/"), "content-type": "application/json"}
    r = await pg.request.post(url + "api/social/signup", headers=H, data=json.dumps({"email": email, "password": "Tamales&Tea42", "password2": "Tamales&Tea42",
        "display_name": "Goonie Test", "username": user, "birthday": "1990-05-05", "tos": True, "challenge": {"id": cfg["challenge"]["id"], "answer": str(a + b)}}))
    check(r.status == 200, f"signed up @{user} ({r.status})")
    code = None
    for _ in range(20):
        m = re.findall(r"code for " + re.escape(email) + r": (\S+)", open(logp).read())
        if m: code = m[-1]; break
        await asyncio.sleep(0.25)
    r = await pg.request.post(url + "api/social/verify", headers=H, data=json.dumps({"email": email, "code": code}))
    check(r.status == 200, f"verified the email code ({r.status})")


async def open_app(ctx, url, hash_="#chisme"):
    pg = await ctx.new_page()
    await pg.goto(url + hash_); await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=30000)
    await pg.wait_for_timeout(1500)
    return pg


async def main():
    proc, url, logp = start()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            # ---- sizes, order, fit (signed out), both seasons
            for w, h in ((320, 640), (360, 740), (390, 844), (430, 932)):
                for season in ("off", "muertos"):
                    ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
                    await ctx.add_init_script(INIT % season)
                    pg = await open_app(ctx, url)
                    t = await pg.evaluate(TABS)
                    tag = f"{w}px {season}"
                    check([x["id"] for x in t] == ["tab-homies", "antojos", "chisme", "juegos", "tab-tia"], f"{tag}: Homies · food · Chisme · Juegos · Tía {[x['l'] for x in t]}")
                    food = "Ofrendas" if season == "muertos" else "¿Y la dieta?"
                    check(len(t) == 5 and t[0]["l"].endswith("Homies") and food in t[1]["l"] and t[2]["l"].endswith("Chisme") and t[3]["l"].endswith("Juegos") and t[4]["l"].endswith("Tía"),
                          f"{tag}: plain labels {[x['l'] for x in t]}")
                    check(len({x["top"] for x in t}) == 1 and all(x["w"] >= 44 and x["h"] >= 44 for x in t), f"{tag}: one row of 44 px+ tabs {[(round(x['w']), round(x['h'])) for x in t]}")
                    check(all(x["x"] >= 0 and x["right"] <= w + 0.5 and not x["spill"] for x in t), f"{tag}: nothing spills past the edge or out of its tab")
                    check(all(x["lines"] == 1 for x in t if x["id"] != "antojos") and t[1]["lines"] <= 2, f"{tag}: labels on one line (food ≤ 2) {[x['lines'] for x in t]}")
                    c = t[2]; check(abs((c["x"] + c["right"]) / 2 - w / 2) <= 2, f"{tag}: Chisme is centred ({(c['x'] + c['right']) / 2:.1f} vs {w / 2})")
                    check(t[2]["cur"] == "page" and t[0]["cur"] is None, f"{tag}: Chisme is the current tab")
                    sw = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
                    check(sw[0] <= sw[1], f"{tag}: no sideways scroll {sw}")
                    yl = await pg.evaluate(YELLOW); check(not yl, f"{tag}: no yellow on the tab bar {yl[:3]}")
                    if w == 390 and season == "off":
                        ic = await pg.evaluate("""() => { const i = document.querySelector('#tab-homies .tab-homies-ico'), sv = i && i.querySelector('svg.homies-ico'), r = sv ? sv.getBoundingClientRect() : {};
                          return { svg: !!sv, img: !!i.querySelector('img'), html: sv ? sv.outerHTML : '', w: r.width, h: r.height }; }""")
                        import re as _re
                        cols = set(c.upper() for c in _re.findall(r"#[0-9A-Fa-f]{3,6}\b", ic["html"]))
                        check(ic["svg"] and not ic["img"] and len(ic["html"]) < 3000 and "script" not in ic["html"].lower() and " on" not in ic["html"].lower().replace(" one", "")
                              and {"#00C9CD", "#FF1A7F", "#FF6A0B"} <= cols and cols <= {"#00C9CD", "#FF1A7F", "#FF6A0B", "#000", "#FFF"} and 24 <= ic["w"] <= 32,
                              f"Homies has its own two-homies icon (small inline SVG, palette only {sorted(cols)}, no script, {ic['w']}px)")
                        await pg.click("#tab-homies"); await pg.wait_for_timeout(1200)
                        s = await pg.evaluate("""() => ({ hash: location.hash, cur: document.querySelector('#tab-homies').getAttribute('aria-current'),
                          ch: document.querySelector('#tabs .tab[data-view=chisme]').getAttribute('aria-current'), txt: (document.querySelector('#sx-view') || {}).textContent || '',
                          pw: !!document.querySelector('#sx-view input[type=password]') })""")
                        check(s["hash"] == "#s/me" and s["pw"] and "Sign in" in s["txt"], f"signed out: Homies opens Sign in / Join ({s['hash']}, {s['txt'][:60]!r})")
                        check(s["cur"] == "page" and s["ch"] is None, f"signed out: Homies is the current tab on Sign in ({s})")
                        await pg.click("#tabs .tab[data-view=chisme]"); await pg.wait_for_timeout(900)
                        s = await pg.evaluate("[location.hash, document.querySelector('#tab-homies').getAttribute('aria-current'), document.querySelector('#tabs .tab[data-view=chisme]').getAttribute('aria-current'), document.querySelector('#sx-view').hidden]")
                        check(not s[0].startswith("#s/") and s[1] is None and s[2] == "page" and s[3], f"Chisme takes you back to the feed {s}")
                    await ctx.close()
            # ---- signed in
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            await ctx.add_init_script(INIT % "muertos")
            pg = await ctx.new_page(); await pg.goto(url + "#chisme")
            await signup(pg, url, logp, "homie_tab")
            await pg.close()
            for w, h in ((390, 844), (320, 640)):
                c2 = ctx if w == 390 else await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True, storage_state=await ctx.storage_state())
                if w != 390: await c2.add_init_script(INIT % "muertos")
                pg = await open_app(c2, url)
                await pg.wait_for_function("document.querySelector('#fb-menu') && !!document.querySelector('#tab-homies .tab-homies-ico')", timeout=10000)
                await pg.wait_for_timeout(800)
                await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(500)
                await pg.screenshot(path=f"{SHOTS}/homies-chisme-{w}.png")
                t = await pg.evaluate(TABS)
                check(t[2]["cur"] == "page", f"{w}px signed in: Chisme is current on the feed")
                want = await pg.evaluate("() => { const c = document.querySelector('#tabs .tab[data-view=chisme]'); return [getComputedStyle(c.querySelector('span[aria-hidden]')).backgroundColor, getComputedStyle(c, '::before').backgroundColor, getComputedStyle(c).color]; }")
                await pg.click("#tab-homies"); await pg.wait_for_selector("#sx-view .p-homies", timeout=10000); await pg.wait_for_timeout(1200)
                s = await pg.evaluate("""() => { const h = document.querySelector('#tab-homies'), ico = h.querySelector('.tab-homies-ico');
                  return { hash: location.hash, cur: h.getAttribute('aria-current'), others: [...document.querySelectorAll('#tabs .tab[aria-current]')].length,
                    pill: getComputedStyle(ico).backgroundColor, bar: getComputedStyle(h, '::before').backgroundColor, col: getComputedStyle(h).color, name: document.querySelector('#sx-view').textContent.includes('@homie_tab') }; }""")
                check(s["hash"] == "#s/me" and s["name"], f"{w}px: Homies opens your own profile with the Homies section ({s['hash']})")
                check(s["cur"] == "page" and s["others"] == 1, f"{w}px: Homies is the only current tab")
                check([s["pill"], s["bar"], s["col"]] == want and s["pill"] == "rgb(255, 26, 127)", f"{w}px: Homies active looks like Chisme active (pink pill + its bar) ({s['pill']}, {s['bar']}, {s['col']} vs {want})")
                t = await pg.evaluate(TABS)
                check(len({x["top"] for x in t}) == 1 and all(x["right"] <= w + 0.5 and not x["spill"] for x in t), f"{w}px: the bar still fits with Homies current")
                await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(600)
                await pg.screenshot(path=f"{SHOTS}/homies-profile-{w}.png")
                if w == 390:
                    # hide on scroll, back on scroll up, Homies still current
                    await pg.evaluate("document.body.style.minHeight = '3000px'")
                    await pg.mouse.move(195, 400)
                    for _ in range(6): await pg.mouse.wheel(0, 120); await pg.wait_for_timeout(80)
                    await pg.wait_for_timeout(700)
                    hid = await pg.evaluate("[document.documentElement.classList.contains('fb-hide'), document.querySelector('#tabs').getBoundingClientRect().top >= innerHeight - 1]")
                    check(all(hid), f"profile: scrolling down hides the tab bar {hid}")
                    for _ in range(2): await pg.mouse.wheel(0, -120); await pg.wait_for_timeout(80)
                    await pg.wait_for_timeout(700)
                    back = await pg.evaluate("[!document.documentElement.classList.contains('fb-hide'), Math.abs(document.querySelector('#tabs').getBoundingClientRect().bottom - innerHeight) < 1, document.querySelector('#tab-homies').getAttribute('aria-current')]")
                    check(back[0] and back[1] and back[2] == "page", f"profile: scrolling up brings it back, Homies still current {back}")
                    await pg.evaluate("document.body.style.minHeight = ''")
                    await pg.click("#tabs .tab[data-view=juegos]"); await pg.wait_for_timeout(1200)
                    s = await pg.evaluate("[document.querySelector('#tab-homies').getAttribute('aria-current'), document.querySelector('#tabs .tab[data-view=juegos]').getAttribute('aria-current'), location.hash]")
                    check(s[0] is None and s[1] == "page" and not s[2].startswith("#s/"), f"Juegos from your profile: Juegos current, profile closed {s}")
                    # your photo becomes the icon
                    has = await pg.evaluate("[!!document.querySelector('#tab-homies .tab-homies-ico svg.homies-ico'), !!document.querySelector('#tab-homies img')]")
                    check(has == [True, False], "signed in: still the two-homies icon (never your photo)")
                await pg.close()
                if c2 is not ctx: await c2.close()
            await ctx.close()
            # ---- desktop
            ctx = await b.new_context(viewport={"width": 1280, "height": 800})
            await ctx.add_init_script(INIT % "off")
            pg = await open_app(ctx, url); await pg.wait_for_timeout(1200)
            d = await pg.evaluate("""() => ({ dk: document.documentElement.classList.contains('dk'), tabs: [...document.querySelectorAll('#tabs .tab')].filter((t) => t.getClientRects().length)
              .sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left).map((t) => t.dataset.view || t.id),
              logo: (document.querySelector('.dk-logo') || { getBoundingClientRect: () => ({ left: 0 }) }).getBoundingClientRect().left,
              first: (document.querySelector('#tabs .tab[data-view=chisme]')).getBoundingClientRect().left })""")
            check(d["dk"] and d["tabs"] == ["chisme", "antojos", "juegos"] and d["logo"] < d["first"], f"desktop: no Homies / Tía tab, Chisme first after the logo {d}")
            await ctx.close()
            await b.close()
    finally:
        proc.terminate()
    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAIL(S)'}")
    sys.exit(1 if fails else 0)


asyncio.run(main())
