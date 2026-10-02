"""v42: private, anonymous usage counts + the owner's /stats dashboard (stats.py).
Starts its own servers (no Upstash, a temp file store, a test ADMIN_TOKEN): 8213 for the real flow, 8214 with
made-up sample data (tools/stats_seed.py, marked TEST DATA) for the screenshot screenshots/stats-dashboard.png.
Checks: batches are validated (junk and unknown events dropped, city level only, no chat text); the Upstash path's
Redis commands (a fake Redis); the app's events (open app/web, tabs, a story, a game, a food video, Tía, donate, the
Add to Home Screen tutorial, the city) arrive by sendBeacon from Chromium and WebKit iPhone (installed = standalone);
nothing is sent with Global Privacy Control / DNT; what's stored has no device ID, IP or text; /stats is 404 without
ADMIN_TOKEN, 401 without the key, ?key= once → HttpOnly cookie (not the token) and the key leaves the address bar;
the service worker doesn't answer /stats with the app; the temporary-storage banner; no yellow; Settings → Privacy."""
import asyncio, colorsys, json, os, re, secrets, subprocess, sys, tempfile, time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stats

OUT = HERE / "screenshots"; OUT.mkdir(exist_ok=True)
TOKEN = "test-admin-" + secrets.token_urlsafe(18)
TMP = Path(tempfile.mkdtemp(prefix="chisme-stats-"))
STORE, SAMPLE = TMP / "stats.json", TMP / "sample.json"
fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


def serve(port: int, store: Path, token: str | None = TOKEN):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UPSTASH_", "ADMIN_TOKEN", "STATS_", "RENDER"))}
    env.update(STATS_STORE_FILE=str(store), PYTHONUNBUFFERED="1")
    if token:
        env["ADMIN_TOKEN"] = token
    p = subprocess.Popen([str(HERE / "venv/bin/uvicorn"), "app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=HERE, env=env,
                         stdout=open(TMP / f"server{port}.log", "w"), stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(120):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=2).status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit(f"server {port} didn't start")


def yellowish(css: str) -> bool:
    m = re.findall(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)", css)
    for r, g, b, a in m:
        if a and float(a) < 0.05:
            continue
        h, l, s = colorsys.rgb_to_hls(float(r) / 255, float(g) / 255, float(b) / 255)
        if 40 / 360 <= h <= 70 / 360 and s > 0.45 and 0.3 < l < 0.92:
            return True
    return False


async def unit():
    print("\n== batches: validated, anonymous")
    did = "A" * 22
    t = stats.tally({"d": did, "e": [["open", "web"], ["tab", "news"], ["tab", "hacker"], ["story", {"u": "https://ex.com/a", "t": " Big   news ", "s": "KSAT"}],
                                      ["game", "loteria"], ["food", "yt"], ["tia", "my secret message"], ["donate", "cashapp"], ["a2hs", "got_it"],
                                      ["city", "San Antonio, TX"], ["city", "<script>"], ["bogus", 1], "junk", ["open", "evil"]]})
    c = t["counts"]
    check(c.get("open:web") == 1 and c.get("tab:news") == 1 and "tab:hacker" not in c and c.get("game:loteria") == 1 and c.get("food:yt") == 1
          and c.get("tia") == 1 and c.get("donate:cashapp") == 1 and c.get("a2hs:got_it") == 1 and c.get("city:San Antonio, TX") == 1 and not any("script" in k for k in c)
          and not any(k.startswith(("bogus", "open:evil")) for k in c), f"known events counted, unknown/junk dropped ({sorted(c)})")
    check("my secret message" not in json.dumps(t), "Tía: only a count (the text never gets into what's stored)")
    check(t["uniq"]["all"] != did and did not in json.dumps(t) and len(t["uniq"]["all"]) == 16, "the device ID is only kept as a salted hash")
    check(list(t["stories"].values())[0]["t"] == "Big news", "a story keeps its (public) headline, tidied")
    check(stats.tally({"d": "short", "e": [["open", "web"]]}) is None and stats.tally({"d": did, "e": [["nope"]]}) is None and stats.tally([1]) is None, "bad IDs / empty batches are ignored")

    # the Upstash path, against a tiny fake Redis
    class FakeRedis:
        def __init__(self): self.h, self.hll, self.ttl = {}, {}, {}
        def run(self, c):
            op, *a = c
            if op == "HINCRBY": d = self.h.setdefault(a[0], {}); d[a[1]] = str(int(d.get(a[1], 0)) + int(a[2])); return int(d[a[1]])
            if op == "HSET": self.h.setdefault(a[0], {})[a[1]] = a[2]; return 1
            if op == "HGETALL": return [x for kv in self.h.get(a[0], {}).items() for x in kv]
            if op == "EXPIRE": self.ttl[a[0]] = int(a[1]); return 1
            if op == "PFADD": self.hll.setdefault(a[0], set()).update(a[1:]); return 1
            if op == "PFCOUNT": return len(set().union(*[self.hll.get(k, set()) for k in a]))
            raise ValueError(op)
    fake = FakeRedis()
    up = stats.UpstashStore("https://example.upstash.io", "t")
    async def pipe(cmds): return [fake.run([str(x) for x in c]) for c in cmds]
    up.pipe = pipe
    days = stats.last_days(30)

    async def go():
        t1 = stats.tally({"d": "B" * 22, "e": [["open", "app"], ["tab", "news"], ["story", {"u": "https://ex.com/b", "t": "B"}]]})
        t2 = stats.tally({"d": "C" * 22, "e": [["open", "web"], ["open", "web"]]})
        await up.add(days[-1], t1); await up.add(days[-1], t2); await up.add(days[-3], t1)
        return await up.read(days)
    r = await go()
    check(r["ranges"][1]["all"] == 2 and r["ranges"][1]["app"] == 1 and r["ranges"][7]["all"] == 2 and r["per"][days[-3]]["u"]["all"] == 1
          and r["per"][days[-1]]["c"]["open"] == 3 and len(r["stories"]) == 1, f"Upstash: HINCRBY/PFADD per day, PFCOUNT unions for 7/30 days ({r['ranges']})")
    check(fake.ttl and all(v == 40 * 86400 for v in fake.ttl.values()), "Upstash: every key expires after 40 days")
    html_ = stats.page(r, "upstash")
    check("Temporary storage" not in html_ and "TEST DATA" not in html_, "with Upstash: no temporary-storage banner")


def access():
    print("\n== /stats access")
    from fastapi.testclient import TestClient
    import app as appmod
    old = os.environ.pop("ADMIN_TOKEN", None)
    try:
        c = TestClient(appmod.app)
        check(c.get("/stats").status_code == 404 and c.get("/stats?key=x").status_code == 404, "no ADMIN_TOKEN: /stats doesn't exist (404)")
    finally:
        if old is not None:
            os.environ["ADMIN_TOKEN"] = old
    B = "http://127.0.0.1:8213"
    r = httpx.get(B + "/stats")
    check(r.status_code == 401 and "Private page" in r.text and "Visitors" not in r.text and r.headers.get("cache-control") == "no-store"
          and "noindex" in r.headers.get("x-robots-tag", ""), "no cookie: 401, a private-page note, nothing else (no-store, noindex)")
    check(httpx.get(B + "/stats?key=wrong").status_code == 401 and httpx.get(B + "/stats", cookies={stats.COOKIE: TOKEN}).status_code == 401,
          "a wrong key, or the token itself as the cookie: 401")
    r = httpx.get(B + "/stats?key=" + TOKEN)
    sc = r.headers.get("set-cookie", "")
    check(r.status_code == 303 and r.headers.get("location") == "/stats" and "HttpOnly" in sc and "SameSite=strict" in sc.replace("Strict", "strict")
          and "Path=/stats" in sc and TOKEN not in sc, f"?key= once: 303 to /stats (key out of the address bar), HttpOnly SameSite=Strict cookie that isn't the token")
    r = httpx.post(B + "/api/stats", content=json.dumps({"d": "D" * 22, "e": [["open", "web"]]}), headers={"DNT": "1", "Content-Type": "text/plain"})
    check(r.status_code == 204, "DNT: 1 → 204 and nothing kept")
    check(httpx.post(B + "/api/stats", content=b"x" * 20000).status_code == 204 and httpx.post(B + "/api/stats", content=b"{nope").status_code == 204,
          "oversized / broken batches: 204, ignored")


async def e2e(p):
    print("\n== the app's events → sendBeacon → the store")
    U = "http://127.0.0.1:8213/"
    b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = await ctx.new_page(); beacons = []
    pg.on("request", lambda r: beacons.append(r) if r.url.endswith("/api/stats") else None)
    await pg.goto(U)
    await pg.wait_for_function("() => window.__chisme && window.__chisme.stats", timeout=60000)
    q0 = await pg.evaluate("window.__chisme.stats.queue")
    check(["open", "web"] in q0 and ["tab", "news"] in q0, f"an open in the browser + the News tab are queued ({q0[:4]})")
    anon = await pg.evaluate("localStorage.getItem('chisme-anon-id')")
    check(bool(re.match(r"^[A-Za-z0-9_-]{22}$", anon or "")) and not any(c.name for c in await ctx.cookies()), "a random ID in localStorage, and no cookies")
    await pg.tap(".tab[data-view=weather]"); await pg.wait_for_timeout(600)
    try:
        await pg.wait_for_selector(".story[data-sid] a[href^=http]", state="attached", timeout=60000)
        title = await pg.evaluate("(() => { const a = document.querySelector('.story[data-sid] a[href^=http]'); const t = a.closest('.story').querySelector('a').textContent.trim(); a.click(); return t; })()")
    except Exception:
        title = None
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
    await pg.evaluate("""() => { document.addEventListener('click', (e) => { if (e.target.closest('.donate-btn')) e.preventDefault(); });
      document.querySelector('#set-donate .donate-btn.cashapp').click(); }""")
    await pg.evaluate("() => { document.querySelector('#tia-in').value = 'hola tía, a secret question'; document.querySelector('#tia-form').requestSubmit(); }")
    await pg.evaluate("document.querySelector('#set-a2hs').click()"); await pg.wait_for_timeout(300)
    await pg.evaluate("document.querySelector('#a2hs-ok').click()")
    await pg.evaluate("document.querySelector('.tab[data-view=juegos]').click()")
    await pg.wait_for_selector('.game-pick[data-game="loteria"]', timeout=15000); await pg.evaluate("document.querySelector('.game-pick[data-game=\"loteria\"]').click()")   # v47: Juegitos opens on Juan
    await pg.wait_for_selector("#lot-play", timeout=15000); await pg.evaluate("document.querySelector('#lot-play').click()"); await pg.wait_for_timeout(500)
    await pg.evaluate("document.querySelector('#lot-play').click()")   # pause, then resume: still one play
    await pg.evaluate("document.querySelector('#lot-play').click()")
    await pg.evaluate("document.querySelector('.tab[data-view=antojos]').click()")
    await pg.wait_for_function("() => window.__chisme.foodReady", timeout=90000)
    await pg.evaluate("window.__chisme.openFeed(null, 0)")
    try: await pg.wait_for_function("() => window.__chisme.stats.queue.some(e => e[0] === 'food')", timeout=30000)
    except Exception: pass
    await pg.evaluate("window.__chisme.stats.send()"); await pg.wait_for_timeout(1500)
    check(await pg.evaluate("window.__chisme.stats.queue.length") == 0 and beacons and all(r.method == "POST" for r in beacons), f"sent in batches ({len(beacons)} beacons), the queue is empty after")
    # the installed app (iPhone, from the Home Screen)
    wk = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    c2 = await wk.new_context(**dev); await c2.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true });")
    p2 = await c2.new_page(); await p2.goto(U)
    await p2.wait_for_function("() => window.__chisme && window.__chisme.stats", timeout=60000)
    q2 = await p2.evaluate("window.__chisme.stats.queue")
    check(["open", "app"] in q2, "iPhone, opened from the Home Screen: counted as the installed app")
    await p2.evaluate("window.__chisme.stats.send()"); await p2.wait_for_timeout(1500)
    # Global Privacy Control: nothing leaves the phone
    c3 = await b.new_context(); await c3.add_init_script("Object.defineProperty(navigator, 'globalPrivacyControl', { get: () => true });")
    p3 = await c3.new_page(); sent3 = []
    p3.on("request", lambda r: sent3.append(r.url) if "/api/stats" in r.url else None)
    await p3.goto(U); await p3.wait_for_function("() => window.__chisme && window.__chisme.stats", timeout=60000)
    await p3.evaluate("window.__chisme.stats.send()"); await p3.wait_for_timeout(800)
    check(await p3.evaluate("window.__chisme.stats.off") and not sent3 and not await p3.evaluate("window.__chisme.stats.queue.length"), "Global Privacy Control on: nothing queued or sent")
    # Settings → Privacy
    note = await pg.evaluate("document.querySelector('#set-privacy-note').textContent.trim()")
    check(note == "Chisme counts anonymous visits to improve the app. No names, no ads." and await pg.evaluate("document.querySelector('#set-privacy legend').textContent") == "Privacy",
          "Settings → Privacy: 'Chisme counts anonymous visits to improve the app. No names, no ads.'")

    # what's stored
    raw = STORE.read_text(); d = json.loads(raw); day = stats.day_of(); T = d["days"][day]; c = T["c"]
    check(len(T["u"]["all"]) == 2 and len(T["u"]["app"]) == 1 and len(T["u"]["web"]) == 1, f"2 visitors today (1 in the app, 1 in the browser) ({ {k: len(v) for k, v in T['u'].items()} })")
    want = {"tab:news": 1, "tab:weather": 1, "tab:juegos": 1, "tab:antojos": 1, "game:loteria": 1, "donate:cashapp": 1, "tia": 1, "a2hs:shown": 1, "a2hs:got_it": 1, "city:San Antonio, TX (default)": 1}
    check(all(c.get(k, 0) >= v for k, v in want.items()) and c.get("game:loteria") == 1, f"tabs, a game (pause/resume isn't another play), donate, Tía, the tutorial, the city ({ {k: c.get(k) for k in want} })")
    check(c.get("food", 0) >= 1, f"a food video view ({c.get('food')})")
    st = [v for v in d["stories"].values()]
    check(title is not None and any(s["t"][:30] == title[:30] for s in st) and any(k.startswith("story:") for k in c), f"the story opened, with its headline ({title!r:.60})")
    check(anon not in raw and "127.0.0.1" not in raw and "secret question" not in raw and "29.42" not in raw, "stored: no device ID, no IP, no chat text, no coordinates")
    await b.close(); await wk.close()


async def dashboard(p):
    print("\n== the dashboard")
    b = await p.webkit.launch(); dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await b.new_context(**dev); pg = await ctx.new_page()
    await pg.goto("http://127.0.0.1:8213/")   # the app first, so its service worker is in charge
    await pg.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=30000)
    await pg.goto("http://127.0.0.1:8213/stats")
    check("Private page" in await pg.content() and not await pg.evaluate("!!window.__chisme"), "with the app's service worker running, /stats is the server's page (not the app)")
    await pg.goto("http://127.0.0.1:8213/stats?key=" + TOKEN)
    ck = [c for c in await ctx.cookies() if c["name"] == stats.COOKIE]
    check(pg.url.endswith("/stats") and "key=" not in pg.url and ck and ck[0]["httpOnly"] and ck[0]["value"] != TOKEN, f"?key= once → /stats, cookie set ({pg.url})")
    txt = await pg.inner_text("body")
    n = await pg.evaluate("[...document.querySelectorAll('#p1 .stat')].map(s => [s.querySelector('.l').textContent, s.querySelector('.n').textContent])")
    nd = dict(n)
    check(nd.get("Visitors") == "3" and nd.get("Installed app") == "1" and nd.get("In Safari / browser") == "2" and int(nd.get("Tía chats", 0)) >= 1 and int(nd.get("Donate taps", 0)) >= 1 and int(nd.get("Game plays", 0)) >= 1,
          f"Today: 3 visitors (the 2 phones + this browser, which opened the app above), 1 installed, the chats, donate taps, game plays ({nd})")
    check("reset on every redeploy" in txt and "TEST DATA" not in txt, "no Upstash: the 'resets on every redeploy' banner (real data: no TEST DATA label)")
    for lab in ("Top tabs", "Top stories", "Games", "Cities", "Add to Home Screen tutorial", "Visitors per day"):
        check(lab in txt, f"section: {lab}")
    check(not await pg.evaluate("document.querySelector('#f-all').open"), "v49.5: the detailed numbers are folded away at first (the phone-first admin page)")
    await pg.tap("#f-all summary"); await pg.wait_for_timeout(150)
    vis = await pg.evaluate("[...document.querySelectorAll('[role=tabpanel]')].filter(x => x.offsetHeight > 0).map(x => x.id)")
    check(vis == ["p1"], f"only Today's numbers show at first ({vis})")
    await pg.tap("#t7"); await pg.wait_for_timeout(200)
    vis = await pg.evaluate("[...document.querySelectorAll('[role=tabpanel]')].filter(x => x.offsetHeight > 0).map(x => x.id)")
    check(vis == ["p7"], f"7 days / 30 days switch: only that period's numbers show ({vis})")
    await pg.goto("http://127.0.0.1:8214/stats?key=" + TOKEN)   # the sample-data server
    await pg.wait_for_timeout(300)
    txt = await pg.inner_text("body")
    check("TEST DATA" in txt and "made-up sample numbers" in txt, "sample data: labeled 🧪 TEST DATA")
    ov = await pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    check(ov, "fits the phone's width (no sideways scroll)")
    cols = await pg.evaluate("""() => [...document.querySelectorAll('*')].flatMap(e => { const s = getComputedStyle(e); return [s.color, s.backgroundColor, s.borderTopColor, s.borderLeftColor, s.fill, s.backgroundImage]; })""")
    yl = sorted({x for x in cols if yellowish(x)})
    check(not yl, f"no yellow anywhere ({yl[:3]})")
    await pg.screenshot(path=str(OUT / "stats-dashboard.png"), full_page=True)
    print("  shot screenshots/stats-dashboard.png")
    await b.close()


async def main():
    await unit()
    s1 = serve(8213, STORE)
    subprocess.run([str(HERE / "venv/bin/python"), str(HERE / "tools/stats_seed.py")], env={**{k: v for k, v in os.environ.items() if not k.startswith("UPSTASH_")}, "STATS_STORE_FILE": str(SAMPLE)}, check=True)
    s2 = serve(8214, SAMPLE)
    try:
        access()
        async with async_playwright() as p:
            await e2e(p)
            await dashboard(p)
    finally:
        for s in (s1, s2):
            s.terminate()
            try: s.wait(10)
            except Exception: s.kill()
    print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAIL(S)"))
    sys.exit(1 if fails else 0)


asyncio.run(main())
