"""v49.3: the weather alert banner (the red strip under the header, e.g. "⚠ Flood Watch for your area") has a ✕.
  - The ✕ is a round 44 px target with an accessible name, Fiesta colours, no yellow, light + dark, 390 + 320 px.
  - ✕ hides that one alert (the next one, if any, takes the banner); it stays hidden across reloads (localStorage
    chisme-wx-hidden), and an NWS re-issue of the same alert (new id, same event / severity / end) stays hidden.
  - It comes back when it's new or upgraded (Watch → Warning, higher severity), extended (later end) or once the hide
    expires (at the alert's end time). The Weather tab always keeps the full alerts.
Alerts are injected into /api/weather (the real response, alerts replaced). Screenshots: weather-alert-close.png
(light 390 px), weather-alert-close-dark.png. Against the local server (CHISME_URL, default http://localhost:8211)."""
import ast, asyncio, json, os, time
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
from popup_quiet import QUIET

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
SETUP = "localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1');"
NO_A2 = "if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

_src = ast.parse(open(os.path.join(HERE, "news_no_yellow_test.py")).read())
YELLOW_JS = next(ast.literal_eval(n.value) for n in _src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "YELLOW_JS")
SCAN = "(root) => { " + YELLOW_JS + r"""
  const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const r = document.querySelector(root), bad = [];
  for (const e of [r, ...r.querySelectorAll('*')]) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push((e.className || e.tagName) + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
STRIP = """() => { const s = document.querySelector('#alert-strip'), x = s.querySelector('.as-x'), g = s.querySelector('.as-go');
  const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  if (s.hidden || !x) return { shown: false, vw: innerWidth };
  const cx = getComputedStyle(x);
  return { shown: true, vw: innerWidth, text: g.textContent, label: x.getAttribute('aria-label'), x: R(x), go: R(g), bg: cx.backgroundColor, fg: cx.color,
    ring: cx.borderTopColor, weight: +cx.fontWeight, radius: cx.borderTopLeftRadius }; }"""

def iso(h): return (datetime.now(timezone.utc) + timedelta(hours=h)).replace(microsecond=0).isoformat()
def alert(i, event, sev, h):
    return {"id": f"urn:oid:test.{i}", "event": event, "headline": f"{event} issued for Bexar County", "severity": sev, "urgency": "Expected",
            "certainty": "Likely", "areaDesc": "Bexar", "description": f"* WHAT...{event}.", "instruction": "Turn around, don't drown.",
            "effective": iso(-1), "onset": iso(-1), "expires": iso(h), "ends": iso(h), "senderName": "NWS Austin/San Antonio TX"}
FW = alert(1, "Flood Watch", "Moderate", 6)
HEAT = alert(2, "Heat Advisory", "Minor", 8)
state = {"alerts": [FW, HEAT]}

async def ready(pg): await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
async def fake_weather(route):
    r = await route.fetch(); body = await r.json()
    if body.get("supported") is not False: body["alerts"] = state["alerts"]
    await route.fulfill(response=r, body=json.dumps(body), headers={**r.headers, "content-type": "application/json"})
async def newctx(b, p, scheme="light", width=390):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    dev["viewport"] = {"width": width, "height": 844 if width >= 390 else 640}; dev["device_scale_factor"] = 2
    ctx = await b.new_context(**dev, color_scheme=scheme, service_workers="block")
    for s in (SETUP, NO_A2, QUIET): await ctx.add_init_script(s)
    await ctx.route("**/api/weather?*", fake_weather)
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs
async def load(pg, want):
    """(re)load and wait until the banner shows `want` (an event name) or is hidden (want=None)."""
    await pg.reload() if pg.url.startswith("http") else await pg.goto(BASE + "/")
    await ready(pg)
    cond = ("(w) => { const s = document.querySelector('#alert-strip'); return w ? !s.hidden && s.textContent.includes(w) : "
            "document.querySelectorAll('#alerts .alert').length > 0 && s.hidden; }")
    try: await pg.wait_for_function(cond, arg=want, timeout=30000)
    except Exception: pass
    await pg.wait_for_timeout(300)
    return await pg.evaluate(STRIP)

def look(s, scheme, width):
    check(s["shown"] and "Flood Watch" in s["text"] and "(+1 more)" in s["text"], f"{scheme} {width}: banner shows the Flood Watch (+1 more) ({s.get('text', '')[:60]!r})")
    check(s["x"]["w"] >= 44 and s["x"]["h"] >= 44, f"{scheme} {width}: ✕ is a 44 px target ({s['x']['w']:.0f}x{s['x']['h']:.0f})")
    check(s["label"] == "Hide this alert: Flood Watch", f"{scheme} {width}: ✕ has an accessible name ({s['label']!r})")
    check(s["x"]["r"] <= s["vw"] - 4 and s["go"]["r"] < s["x"]["l"] and s["go"]["w"] >= 180, f"{scheme} {width}: fits beside the banner text ({s['go']['w']:.0f} px text, ✕ right {s['x']['r']:.0f}/{s['vw']})")
    check(s["weight"] >= 800 and s["radius"] != "0px", f"{scheme} {width}: bold, round ({s['weight']}, {s['radius']})")
    if scheme == "light": check(s["bg"] == "rgb(255, 255, 255)" and s["ring"] == "rgb(239, 66, 111)" and s["fg"] == "rgb(0, 0, 0)", f"light: white ✕ with a Fiesta pink ring ({s['bg']}, {s['ring']}, {s['fg']})")
    else: check(s["bg"] == "rgb(17, 17, 17)" and s["ring"] == "rgb(0, 201, 205)" and s["fg"] == "rgb(255, 255, 255)", f"dark: near-black ✕ with a turquoise ring ({s['bg']}, {s['ring']}, {s['fg']})")

async def main():
    async with async_playwright() as p:
        b = await p.webkit.launch(); allerrs = []
        for scheme, width in [("light", 390), ("dark", 390), ("light", 320), ("dark", 320)]:
            print(f"== the banner's ✕ ({scheme}, {width} px)")
            state["alerts"] = [FW, HEAT]
            ctx, pg, errs = await newctx(b, p, scheme, width)
            s = await load(pg, "Flood Watch"); look(s, scheme, width)
            bad = await pg.evaluate(SCAN, "#alert-strip"); check(not bad, f"{scheme} {width}: no yellow in the banner ({bad[:3]})")
            if width == 390:
                await pg.screenshot(path=os.path.join(OUT, "weather-alert-close.png" if scheme == "light" else "weather-alert-close-dark.png"), clip={"x": 0, "y": 0, "width": 390, "height": 420})
            if scheme == "light" and width == 390:
                print("== hiding, staying hidden, coming back")
                await pg.click("#alert-strip .as-x"); await pg.wait_for_timeout(250)
                s = await pg.evaluate(STRIP)
                check(s["shown"] and "Heat Advisory" in s["text"] and "more" not in s["text"], f"✕ hides just the Flood Watch; the next alert takes the banner ({s.get('text', '')[:50]!r})")
                check(await pg.evaluate("document.activeElement && document.activeElement.classList.contains('as-go')"), "focus moves to the next banner (not lost)")
                hid = await pg.evaluate("JSON.parse(localStorage.getItem('chisme-wx-hidden'))")
                end = datetime.fromisoformat(FW["ends"]).timestamp() * 1000
                check(hid.get(f"id:{FW['id']}|Flood Watch|Moderate") == end and hid.get(f"Flood Watch|Moderate|{FW['ends']}") == end, f"saved in localStorage until the alert ends ({len(hid)} keys)")
                await pg.click("#alert-strip .as-x"); await pg.wait_for_timeout(250)
                s = await pg.evaluate(STRIP); check(not s["shown"], "✕ on the last one: the banner goes away")
                check(await pg.evaluate("document.querySelectorAll('#alerts .alert').length") == 2, "the Weather tab still has both full alerts")
                s = await load(pg, None); check(not s["shown"], "still hidden after a reload")
                state["alerts"] = [dict(FW, id="urn:oid:test.1b"), HEAT]
                s = await load(pg, None); check(not s["shown"], "an NWS re-issue of the same Flood Watch (new id) stays hidden")
                state["alerts"] = [alert(3, "Flood Warning", "Severe", 6), FW, HEAT]
                s = await load(pg, "Flood Warning"); check(s["shown"] and s["text"].startswith("⚠ Flood Warning") and "more" not in s["text"], f"upgrade: Watch → Warning shows again ({s.get('text', '')[:40]!r})")
                state["alerts"] = [dict(FW, severity="Severe")]
                s = await load(pg, "Flood Watch"); check(s["shown"], "a higher severity shows again")
                state["alerts"] = [dict(FW, id="urn:oid:test.1c", ends=iso(12), expires=iso(12))]
                s = await load(pg, "Flood Watch"); check(s["shown"], "extended (a later end) shows again")
                state["alerts"] = [FW]
                s = await load(pg, None); check(not s["shown"], "the original Flood Watch is still hidden")
                await pg.evaluate("() => { const m = JSON.parse(localStorage.getItem('chisme-wx-hidden')); for (const k in m) m[k] = Date.now() - 1000; localStorage.setItem('chisme-wx-hidden', JSON.stringify(m)); }")
                s = await load(pg, "Flood Watch"); check(s["shown"], "once the hide expires it shows again")
                check(await pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('chisme-wx-hidden') || '{}')).length") == 0, "expired hides are cleaned out of localStorage")
                await pg.click("#alert-strip .as-go"); await pg.wait_for_timeout(800)
                check(await pg.evaluate("__chisme.view") == "weather", "the banner text still opens the Weather tab")
            allerrs += errs; await ctx.close()
        check(not allerrs, f"no page errors ({allerrs[:2]})")
        await b.close()
    print("ALL PASS" if not fails else f"{fails} FAIL(S)")
    raise SystemExit(1 if fails else 0)

asyncio.run(main())
