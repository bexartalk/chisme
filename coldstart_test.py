"""Cold-start / flaky-server test for the "buffering, not updating" fix.

Runs a small proxy in front of the local server that can (a) hold every request for ~50 s, like a
sleeping free Render instance waking up, and (b) answer /api/news with 502 a few times. Checks:
saved news shows instantly; pending fetches stay silent and slow fetches complete directly to done;
a fast server never shows the waking pill, only a quick "Up to date ✓" (~1.5 s, then it fades; screenshots/uptodate-toast.png);
retry with backoff after 502s, pull-to-refresh, and that a hanging iOS geolocation call times out.
COLDSTART_PORT (default 8213) = the proxy's port.
Usage: ./venv/bin/python coldstart_test.py [upstream=http://localhost:8211]
"""
import asyncio, os, sys, tempfile, threading, time
import httpx, uvicorn
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from playwright.sync_api import sync_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

UP = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211"
PORT = int(os.environ.get("COLDSTART_PORT", "8213"))
COLD_S = float(os.environ.get("COLD_S", "50"))
state = {"cold_until": 0.0, "fail_news": 0, "hits": []}
client = httpx.AsyncClient(timeout=120)

async def proxy(request):
    path = request.url.path + ("?" + request.url.query if request.url.query else "")
    if time.time() < state["cold_until"]:
        await asyncio.sleep(max(0, state["cold_until"] - time.time()))
    if request.url.path == "/api/news" and state["fail_news"] > 0:
        state["fail_news"] -= 1
        state["hits"].append(("502", time.time()))
        return Response('{"error":"HTTPStatusError: upstream 429"}', status_code=502, media_type="application/json")
    hh = {k: v for k, v in request.headers.items() if k.lower() in ("accept", "user-agent", "if-none-match", "content-type")}
    r = await (client.post(UP + path, content=await request.body(), headers=hh) if request.method == "POST" else client.get(UP + path, headers=hh))   # POST: the v42 stats beacon
    if request.url.path == "/api/news": state["hits"].append((str(r.status_code), time.time()))
    hdrs = {k: v for k, v in r.headers.items() if k.lower() not in ("content-encoding", "content-length", "transfer-encoding", "connection")}
    return Response(r.content, status_code=r.status_code, headers=hdrs)

app = Starlette(routes=[Route("/{p:path}", proxy, methods=["GET", "HEAD", "POST"])])
srv = uvicorn.Server(uvicorn.Config(app, port=PORT, log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
time.sleep(1.5)

BASE = f"http://localhost:{PORT}/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT, exist_ok=True)
fails, errors = [], []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

def msg(page): return page.eval_on_selector("#sync-msg", "e => e.textContent")
def sync_state(page): return page.eval_on_selector("#sync", "e => e.dataset.state")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path="/usr/bin/google-chrome", headless=True,
        viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True,
        args=["--no-sandbox"])
    # the Home Screen tutorial (2nd open) has its own tests (a2hs_test, a2hs_v47_test); keep it out of the way here
    ctx.add_init_script("if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done: true}));")
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    expected_net = [False]
    def on_console(m):
        if m.type != "error": return
        if expected_net[0] and "Failed to load resource" in m.text: return
        errors.append(m.text)
    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.goto(BASE)
    page.wait_for_function("window.__chisme && __chisme.ready", timeout=90000)
    page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=30000)
    page.reload()
    page.wait_for_function("window.__chisme && __chisme.ready", timeout=90000)
    page.wait_for_function("caches.match(location.origin + '/api/news').then(r => !!r)", timeout=30000)
    page.wait_for_timeout(1500)
    if page.is_visible("#loc-close"): page.click("#loc-close")   # "Not now" on the location pre-prompt

    # --- 1. cold start: server holds requests for COLD_S seconds
    state["cold_until"] = time.time() + COLD_S
    t0 = time.time()
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#near-list .story", timeout=10000)
    if page.is_visible("#loc-close"): page.click("#loc-close")
    t_news = time.time() - t0
    check(t_news < 4, f"saved news on screen {t_news:.1f}s after opening on a sleeping server")
    check(page.eval_on_selector("#news-updated", "e => e.textContent").startswith("Saved copy from"), "news stamp says 'Saved copy from …' while waking")
    st0, t_st0 = sync_state(page), time.time() - t0
    check(st0 == "wait" and not msg(page) and t_st0 < 3 and page.eval_on_selector("#sync", "e => +getComputedStyle(e).opacity") < 0.05,
          f"pending under 3 s: no pill on screen yet (state {st0!r} at {t_st0:.1f}s)")
    page.wait_for_timeout(3100)
    check(sync_state(page) == "wait" and not msg(page) and page.eval_on_selector("#sync", "e => +getComputedStyle(e).opacity") < 0.05,
          "still pending after 3 s: silent hidden wait state")
    page.evaluate("""() => { window.__slowSyncSeen = []; const s = document.querySelector('#sync');
      new MutationObserver(() => window.__slowSyncSeen.push(s.dataset.state)).observe(s, { attributes: true, attributeFilter: ['data-state'] }); }""")
    check(page.eval_on_selector("#offline-banner", "e => e.hidden"), "no misleading 'You're offline' banner while the server wakes")
    page.screenshot(path=os.path.join(OUT, "fix-news-loading.png"))
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=(COLD_S + 40) * 1000)
    check(not msg(page) and "ok" not in page.evaluate("window.__slowSyncSeen"), "slow fetch completes silently straight to done")
    check(page.evaluate("__chisme.fresh"), "fresh news + weather rendered after wake-up")
    check(page.eval_on_selector("#news-updated", "e => e.textContent").startswith("Updated"), "news stamp now 'Updated …'")
    page.screenshot(path=os.path.join(OUT, "fix-news-updated.png"))
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=5000)

    # --- 1b. a fast server (v49.15.3): no waking pill at all, just a quick "Up to date ✓" that fades
    t1 = time.time()
    page.reload(wait_until="domcontentloaded")
    page.evaluate("""() => { window.__syncSeen = []; const s = document.querySelector('#sync'); const rec = () => window.__syncSeen.push([s.dataset.state, document.querySelector('#sync-msg').textContent, Math.round(performance.now())]);
      rec(); new MutationObserver(rec).observe(s, { attributes: true, attributeFilter: ['data-state'] }); }""")
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'ok'", timeout=15000)
    t_fast = time.time() - t1
    check(msg(page) == "Up to date ✓" and t_fast < 3, f"fast server: 'Up to date ✓' after {t_fast:.1f}s")
    page.wait_for_timeout(250); page.screenshot(path=os.path.join(OUT, "uptodate-toast.png"))
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'done'", timeout=4000)
    seen = page.evaluate("window.__syncSeen")
    ok_at = [t for st, _, t in seen if st == "ok"]; done_at = [t for st, _, t in seen if st == "done" and ok_at and t > ok_at[0]]
    check(not any(st == "busy" or "Waking" in m for st, m, _ in seen), f"fast server: never the waking pill {[s[:2] for s in seen]}")
    check(ok_at and done_at and 1200 <= done_at[0] - ok_at[0] <= 2500, f"'Up to date ✓' stays ~1.5 s, then fades ({(done_at[0] - ok_at[0]) if ok_at and done_at else None} ms)")

    # --- 2. server errors (e.g. the 502 Render returned): retry with backoff, keep the stories
    expected_net[0] = True
    state["fail_news"] = 2; state["hits"].clear()
    page.evaluate("window.scrollTo(0, 0)")
    cdp = ctx.new_cdp_session(page)
    def touch(kind, x, y):
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
    # pull to refresh
    touch("touchStart", 195, 330)
    for y in range(340, 560, 20): touch("touchMove", 195, y); page.wait_for_timeout(16)
    ptr_visible = page.eval_on_selector("#ptr", "e => !e.hidden")
    touch("touchEnd", 195, 560)
    check(ptr_visible, "pull-to-refresh indicator shows while pulling down at the top")
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'fail'", timeout=15000)
    check(True, f"502 → {msg(page)!r}")
    check(page.locator("#near-list .story").count() > 3, "stories stay on screen during errors")
    check(page.is_visible("#sync-retry"), "'Retry now' button visible")
    page.wait_for_function("document.querySelector('#sync').dataset.state === 'ok'", timeout=60000)
    codes = [c for c, _ in state["hits"]]
    gaps = [round(b[1] - a[1], 1) for a, b in zip(state["hits"], state["hits"][1:])]
    check(codes[:3] == ["502", "502", "200"], f"news retried with backoff: {codes} gaps {gaps}s")
    expected_net[0] = False

    # --- 3. iOS standalone: geolocation that never answers
    page2 = ctx.new_page()
    page2.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page2.add_init_script("navigator.geolocation.getCurrentPosition = () => {}; navigator.geolocation.watchPosition = () => 1;")
    page2.goto(BASE)
    page2.wait_for_selector("#near-list .story", timeout=10000)
    check(page2.locator("#near-list .story").count() > 3, "news shows without waiting for location")
    page2.click("#settings-btn")                     # location lives in Settings now
    t1 = time.time()
    page2.click("#set-gps")
    page2.wait_for_function("/Couldn't get a location fix/.test(document.querySelector('#set-loc-status').textContent)", timeout=16000)
    check(True, f"hanging geolocation gives up after {time.time() - t1:.0f}s: " + page2.eval_on_selector("#set-loc-status", "e => e.textContent"))
    ctx.close()

check(not errors, f"no console errors ({errors[:3]})")
srv.should_exit = True
print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
