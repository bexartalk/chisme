"""WebKit (iPhone 13) upgrade test: install an OLD build's service worker first, then the same origin
starts serving the current code (what happened on Render when v21 replaced v15). Checks that after
reopening, the page runs the NEW app.js with the NEW HTML: Sports and Weather tabs work, no JS errors.

    ./venv/bin/python upgrade_test.py [old_commit ...]      (default: v15, v17, v19, v21, v22, v23, v24 and v25)
Also checks the next deploy (current build -> build+1 with the app open): the page reloads itself once.
"""
import asyncio, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp; from popup_quiet import QUIET  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "venv", "bin", "python")
PORT = 8230
URL = f"http://localhost:{PORT}/"
OUT = os.path.join(HERE, "screenshots")
OLD = sys.argv[1:] or ["f0f68c2", "a3c1b3c", "4ca7393", "777a9f9", "fb94c22", "2170477", "2e3b9bd", "fa28328"]   # v15, v17, v19, v21, v22, v23, v24, v25
fails = []

def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok: fails.append(what)

def serve(cwd):
    p = subprocess.Popen([PY, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(PORT)], cwd=cwd,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(URL + "healthz", timeout=1); return p
        except Exception: time.sleep(0.2)
    raise SystemExit("server did not start in " + cwd)

def stop(p):
    p.terminate()
    try: p.wait(5)
    except Exception: p.kill()

async def tab_check(pg, errs, label, shots=False):
    # An old page may reload itself onto the new build in the middle of the check (the expected
    # auto-update). That destroys the JS context; wait for the new page and check it instead.
    for attempt in range(3):
        try:
            return await _tab_check(pg, errs, label, shots)
        except Exception as e:
            if "Execution context was destroyed" not in str(e) or attempt == 2: raise
            print(f"  ({label}: page reloaded itself mid-check; re-checking the reloaded page)")
            await pg.wait_for_load_state("load")

async def _tab_check(pg, errs, label, shots=False):
    try: await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
    except Exception: print("  (page never reported ready)")
    await pg.wait_for_timeout(1500)
    ver = await pg.evaluate("() => document.querySelector('#set-version') ? document.querySelector('#set-version').textContent : '(old page)'")
    js_views = await pg.evaluate("() => window.__chisme && typeof window.__chisme.goView === 'function' ? 'new app.js' : 'OLD app.js'")
    print(f"  {label}: page build '{ver}', app.js views {js_views}")
    res = {}
    for v in ["sports", "weather"]:
        if v == "sports":   # v49.12: Sports is a chip inside the Chisme tab
            await pg.click('#tabs [data-view="chisme"]'); await pg.wait_for_timeout(600)
            await pg.click('.view.active .mq-chip[data-go="sports"]')
        else: await pg.click(f'#tabs [data-view="{v}"]')
        await pg.wait_for_timeout(900)
        vis = await pg.evaluate(f"""() => {{ const el = document.querySelector('#view-{v}'); const r = el.getBoundingClientRect();
            const cur = document.querySelector('#tabs [aria-current="page"]');
            return {{ onScreen: r.left > -5 && r.left < 20, text: el.innerText.trim().length, current: cur && cur.dataset.view }}; }}""")
        if v == "sports":
            try: await pg.wait_for_selector("#sports-body .sp-photo", timeout=30000)
            except Exception: pass
        if v == "weather":
            try: await pg.wait_for_selector("#view-weather .now-temp", timeout=30000)
            except Exception: pass
        vis["text"] = await pg.evaluate(f"() => document.querySelector('#view-{v}').innerText.trim().length")
        res[v] = vis
        check(vis["onScreen"] and vis["current"] == ("chisme" if v == "sports" else v) and vis["text"] > 200, f"{label}: {v} tab shows the {v} view ({json.dumps(vis)})")
    return res

async def one(p, old):
    wt = tempfile.mkdtemp(prefix="chisme-old-")
    subprocess.run(["git", "worktree", "add", "-f", wt, old], cwd=HERE, check=True, capture_output=True)
    old_ver = [l for l in open(os.path.join(wt, "static", "sw.js")) if "const VERSION" in l][0].strip()
    print(f"\n== upgrade from {old} ({old_ver})")
    prof = tempfile.mkdtemp(prefix="wk-prof-")
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await p.webkit.launch_persistent_context(prof, **dev, permissions=["geolocation"],
                                                    geolocation={"latitude": 29.4241, "longitude": -98.4936})
    # the Home Screen tutorial (2nd open) has its own tests (a2hs_test, a2hs_v47_test); keep it out of the way here
    await ctx.add_init_script("if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({done: true}));")
    await ctx.add_init_script(QUIET)   # v49.11: pw_csp's auto-quiet doesn't cover persistent contexts; the notifications card covered the tabs
    errs = []
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
    net = []   # resource-load failures (e.g. an API request cut off by the test's own reopen) are network noise, not JS errors
    pg.on("console", lambda m: (net if "Failed to load resource" in m.text else errs).append(f"console: {m.text}") if m.type == "error" else None)
    srv = serve(wt)
    try:
        await pg.goto(URL)
        await pg.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=30000)
        await pg.wait_for_timeout(4000)                      # let the old SW cache the shell + some data
        cached = await pg.evaluate("async () => (await caches.keys())")
        print("  old caches:", cached)
        await pg.goto("about:blank")                          # the app is closed before the deploy (no requests in flight)
    finally:
        stop(srv)
    srv = serve(HERE)                                         # "deploy": same origin now serves the current code
    try:
        await pg.wait_for_timeout(300)                        # serve() blocks the loop: flush events from the down-time first
        errs.clear(); net.clear()
        await pg.goto(URL)                                    # reopen the app
        await pg.wait_for_timeout(6000)                       # new SW installs/activates; page may reload once
        ver = await pg.evaluate("() => window.CHISME_APP_BUILD || null")
        if ver is None:
            # v19-v21 serve their own cached (consistent) shell first; the new worker installs in the
            # background and the old page offers "Chisme was updated · Reload"
            cur = [l for l in open(os.path.join(HERE, "static", "sw.js")) if "const VERSION" in l][0].split('"')[1]
            installed = False
            for _ in range(60):                               # (wait_for_function can't await caches.keys())
                if any(k.startswith(cur + "-shell") for k in await pg.evaluate("async () => await caches.keys()")):
                    installed = True; break
                await pg.wait_for_timeout(1000)
            await pg.wait_for_function("() => !document.querySelector('#update-toast') || !document.querySelector('#update-toast').hidden", timeout=30000)
            check(installed, f"first open after deploy: old version's cached shell (consistent), {cur} installed, update toast shown")
        else:
            await tab_check(pg, errs, "first open after deploy")
        await pg.goto(URL)                                    # reopen again
        await tab_check(pg, errs, "second open")
        keys = await pg.evaluate("async () => (await caches.keys())")
        check(all(not k.startswith(("chisme-v1", "chisme-v20")) for k in keys), f"old caches removed ({keys})")
        check(not errs, f"no JS errors ({errs[:5]})")
        if net: print(f"  note: {len(net)} resource load failure(s) during the reopen: {net[:2]}")
        build = await pg.evaluate("() => [window.CHISME_BUILD, window.CHISME_APP_BUILD, !!window.__chismeBooted]")
        sw_ver = [l for l in open(os.path.join(HERE, "static", "sw.js")) if "const VERSION" in l][0].split('"')[1]
        check(build[0] == build[1] == sw_ver.replace("chisme-v", "") and build[2], f"HTML build, app.js build and sw.js VERSION agree ({build}, {sw_ver})")
        check(await pg.is_hidden("#boot-fail"), "no 'didn't start' banner")
    finally:
        stop(srv)
        await ctx.close()
        subprocess.run(["git", "worktree", "remove", "--force", wt], cwd=HERE, capture_output=True)
        shutil.rmtree(prof, ignore_errors=True)

async def next_deploy(p):
    """v22 page open while a v23 is deployed: the page must reload itself once onto v23 (no manual reopen)."""
    print("\n== next deploy: current build -> build+1, with the app left open")
    cur = [l for l in open(os.path.join(HERE, "static", "sw.js")) if "const VERSION" in l][0].split('"')[1]
    cur_build = cur.replace("chisme-v", ""); n = int(re.match(r"\d+", cur_build).group(0)); nxt = str(n + 1)   # "49.2" -> 50
    tmp = tempfile.mkdtemp(prefix="chisme-next-")
    shutil.copytree(HERE, os.path.join(tmp, "c"), ignore=shutil.ignore_patterns("venv", ".git", "screenshots", "art-candidates", "logs", "__pycache__"))
    d = os.path.join(tmp, "c")
    for f, a_, b_ in [("static/sw.js", f'"{cur}"', f'"chisme-v{nxt}"'), ("static/app.js", f'window.CHISME_APP_BUILD = "{cur_build}"', f'window.CHISME_APP_BUILD = "{nxt}"')]:
        path = os.path.join(d, f); t = open(path).read(); assert a_ in t, (f, a_); open(path, "w").write(t.replace(a_, b_))
    prof = tempfile.mkdtemp(prefix="wk-prof-")
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    ctx = await p.webkit.launch_persistent_context(prof, **dev)
    await ctx.add_init_script(QUIET)
    pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
    srv = serve(HERE)
    try:
        await pg.goto(URL)
        await pg.wait_for_function("() => navigator.serviceWorker.controller", timeout=30000)
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
    finally: stop(srv)
    srv = serve(d)
    try:
        await pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r.update())")   # app comes back to the front
        await pg.wait_for_function(f"() => window.CHISME_APP_BUILD === '{nxt}'", timeout=90000)
        await pg.wait_for_function("() => window.__chisme && window.__chisme.ready", timeout=60000)
        b = await pg.evaluate("() => [window.CHISME_BUILD, window.CHISME_APP_BUILD]")
        check(b == [nxt, nxt], f"open page reloaded itself onto the new build ({b})")
        await pg.click('#tabs [data-view="chisme"]'); await pg.click('.view.active .mq-chip[data-go="sports"]'); await pg.wait_for_timeout(1000)
        check(await pg.evaluate("() => window.__chisme.view") == "sports", "Sports tab works after the self-reload")
        check(not errs, f"no page errors ({errs[:3]})")
    finally:
        stop(srv); await ctx.close()
        shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(prof, ignore_errors=True)

async def main():
    async with async_playwright() as p:
        for old in OLD: await one(p, old)
        await next_deploy(p)
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
    sys.exit(1 if fails else 0)

asyncio.run(main())
