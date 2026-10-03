"""v49.15: close (×) buttons on the Weather tab's bubbles: the disclaimer under the alerts, each NWS alert card and the
all-clear bubble.
  - each × is a real <button>, at least 44x44 px, aria-label "Close", inside its bubble's corner, no yellow (light + dark,
    390 + 320 px), and focus lands on something sensible after a close
  - the disclaimer stays closed for good (localStorage chisme-wx-disclaimer-x), across reloads; Settings → Weather keeps
    the same text
  - an alert card stays closed per alert (localStorage chisme-wx-cards-hidden: NWS id, event + severity + end, headline)
    across reloads and NWS re-issues; closing a card also takes it off the top strip
  - a new alert shows; an upgrade (higher severity) shows; a new Severe/Extreme alert shows even with the headline of a
    closed one (severe alerts are never hidden by a look-alike headline); "Show N closed alerts" brings them back
  - the all-clear bubble stays closed until an alert arrives, then shows again the next time it's all clear
  - closing the strip's ✕ does not close the card (the Weather tab keeps the full alerts)
Alerts are injected into /api/weather (the real response, alerts replaced), like weather_alert_close_test.
Screenshots (SHOTS, default ./screenshots): weather-close.png (light 390), weather-close-dark.png, weather-close-320.png.
    CHISME_URL=http://127.0.0.1:8297 ./venv/bin/python weather_close_test.py"""
import asyncio, json, os, sys
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import pw_csp  # noqa: E401,F401
from popup_quiet import QUIET

BASE = os.environ.get("CHISME_URL", "http://localhost:8211").rstrip("/")
OUT = os.environ.get("SHOTS") or os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
SETUP = ("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-default-tab','weather');"
         "if (!localStorage.getItem('chisme-a2hs')) localStorage.setItem('chisme-a2hs', JSON.stringify({ done: true }));")
fails = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what); (None if ok else fails.append(what))

def iso(h): return (datetime.now(timezone.utc) + timedelta(hours=h)).replace(microsecond=0).isoformat()
def alert(i, event, sev, h, headline=None):
    return {"id": f"urn:oid:test.{i}", "event": event, "headline": headline or f"{event} issued for Bexar County", "severity": sev, "urgency": "Expected",
            "certainty": "Likely", "areaDesc": "Bexar", "description": f"* WHAT...{event}.", "instruction": "Turn around, don't drown.",
            "effective": iso(-1), "onset": iso(-1), "expires": iso(h), "ends": iso(h), "senderName": "NWS Austin/San Antonio TX"}
FW = alert(1, "Flood Watch", "Moderate", 6)
HEAT = alert(2, "Heat Advisory", "Minor", 8)
state = {"alerts": [FW, HEAT]}

YELLOW = r"""(sels) => { const bad = []; const rgb = (s) => [...String(s).matchAll(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/g)].map((m) => [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]]);
  const yellow = ([r, g, b, a]) => a > .2 && r > 180 && g > 150 && b < 110 && Math.abs(r - g) < 90;
  for (const s of sels) for (const e of document.querySelectorAll(s)) { const cs = getComputedStyle(e);
    for (const v of [cs.backgroundColor, cs.backgroundImage, cs.color, cs.boxShadow, cs.borderTopColor]) if (rgb(v).some(yellow)) { bad.push(s + ' ' + String(v).slice(0, 40)); break; } }
  return bad; }"""
STATE = """() => { const R = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
  const xs = (box) => { const x = box && box.querySelector(':scope > .wx-x'); if (!x) return null; const cs = getComputedStyle(x);
    return { tag: x.tagName, label: x.getAttribute('aria-label'), x: R(x), box: R(box), shown: !!x.getClientRects().length && cs.visibility !== 'hidden', bg: cs.backgroundColor, ring: cs.borderTopColor }; };
  const d = document.querySelector('#wx-disclaimer'), strip = document.querySelector('#alert-strip');
  return { disc: { shown: !d.hidden && !!d.getClientRects().length, x: xs(d) },
    cards: [...document.querySelectorAll('#alerts .alert')].map((a) => ({ ev: a.querySelector('h3').textContent.replace('⚠ ', ''), x: xs(a) })),
    clear: (() => { const c = document.querySelector('#alerts .no-alerts'); return c ? { text: c.textContent, x: xs(c) } : null; })(),
    unhide: document.querySelector('#alerts .wx-unhide')?.textContent || null,
    strip: strip.hidden ? null : strip.textContent, focus: document.activeElement ? (document.activeElement.className || document.activeElement.id) : null,
    ls: { disc: localStorage.getItem('chisme-wx-disclaimer-x'), clear: localStorage.getItem('chisme-wx-allclear-x'), cards: Object.keys(JSON.parse(localStorage.getItem('chisme-wx-cards-hidden') || '{}')).length },
    setCopy: (document.querySelector('#set-wx-disclaimer')?.textContent || '').includes("isn't an official warning service"), vw: innerWidth }; }"""

async def fake_weather(route):
    r = await route.fetch(); body = await r.json()
    if body.get("supported") is not False: body["alerts"] = state["alerts"]
    await route.fulfill(response=r, body=json.dumps(body), headers={**r.headers, "content-type": "application/json"})
async def newctx(b, p, scheme="light", width=390):
    dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None)
    dev["viewport"] = {"width": width, "height": 844 if width >= 390 else 640}; dev["device_scale_factor"] = 2
    ctx = await b.new_context(**dev, color_scheme=scheme, service_workers="block")
    for s in (SETUP, QUIET, f"try{{localStorage.setItem('chisme-theme','{scheme}')}}catch(e){{}}"): await ctx.add_init_script(s)
    await ctx.route("**/api/weather?*", fake_weather)
    await ctx.route("**/api/stats", lambda r: r.fulfill(status=204))
    pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    return ctx, pg, errs
async def load(pg):
    await pg.reload() if pg.url.startswith("http") else await pg.goto(BASE + "/")
    await pg.wait_for_function("window.__chisme && __chisme.ready", timeout=120000)
    n = len(state["alerts"])
    cond = ("(n) => n ? document.querySelectorAll('#alerts .alert').length + (document.querySelector('#alerts .wx-unhide') ? 1 : 0) > 0"
            " : !!document.querySelector('#alerts .no-alerts') || localStorage.getItem('chisme-wx-allclear-x') === '1'")
    try: await pg.wait_for_function(cond, arg=n, timeout=30000)
    except Exception: pass
    await pg.wait_for_timeout(400)
    return await pg.evaluate(STATE)

def looks(s, tag):
    xs = ([("disclaimer", s["disc"]["x"])] if s["disc"]["shown"] else []) + [(c["ev"], c["x"]) for c in s["cards"]] + ([("all-clear", s["clear"]["x"])] if s["clear"] else [])
    for name, x in xs:
        ok = x and x["tag"] == "BUTTON" and x["label"] == "Close" and x["shown"] and x["x"]["w"] >= 44 and x["x"]["h"] >= 44
        inside = x and x["x"]["l"] >= x["box"]["l"] and x["x"]["r"] <= x["box"]["r"] + 0.5 and x["x"]["t"] >= x["box"]["t"] - 0.5 and x["x"]["b"] <= x["box"]["b"] + 0.5 and x["x"]["r"] <= s["vw"]
        check(bool(ok and inside), f"{tag}: {name}: a visible × button, aria-label 'Close', {x and round(x['x']['w'])}x{x and round(x['x']['h'])} px, inside the bubble's corner")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # ---- light 390: the looks, then the behaviour
        ctx, pg, errs = await newctx(b, p)
        s = await load(pg)
        check(s["disc"]["shown"] and [c["ev"] for c in s["cards"]] == ["Flood Watch", "Heat Advisory"] and s["unhide"] is None,
              f"fresh: the disclaimer and both alert cards show {[c['ev'] for c in s['cards']]}")
        looks(s, "light 390")
        check(s["disc"]["x"]["bg"] == "rgb(255, 255, 255)" and s["disc"]["x"]["ring"] == "rgb(239, 66, 111)", f"light: white × with the Fiesta pink ring (like the strip's ✕) {s['disc']['x']['bg']} {s['disc']['x']['ring']}")
        y = await pg.evaluate(YELLOW, ["#alerts", "#alerts *", "#wx-disclaimer", "#wx-disclaimer *"])
        check(not y, f"light: no yellow on the bubbles or their × {y[:3]}")
        await pg.evaluate("document.querySelector('#alerts').scrollIntoView({ block: 'start' }); scrollBy(0, -130); const t = document.querySelector('#sync'); if (t) t.dataset.state = 'done'"); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f"{OUT}/weather-close.png")
        # disclaimer: closes, stays closed
        await pg.click("#wx-disclaimer .wx-x"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check(not s["disc"]["shown"] and s["ls"]["disc"] == "1" and s["focus"] == "wx-x", f"the disclaimer's × closes it, remembers it, focus moves to the next × ({s['focus']})")
        s = await load(pg)
        check(not s["disc"]["shown"] and len(s["cards"]) == 2, "after a reload the disclaimer stays closed (the alerts still show)")
        check(s["setCopy"], "Settings → Weather still has the disclaimer text")
        # an alert card: closes, off the strip too, stays closed, survives an NWS re-issue
        check(s["strip"] and "Flood Watch" in s["strip"], f"the strip shows the Flood Watch ({(s['strip'] or '')[:40]!r})")
        await pg.click("#alerts .alert:nth-child(1) .wx-x"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check([c["ev"] for c in s["cards"]] == ["Heat Advisory"] and s["unhide"] == "Show 1 closed alert" and s["ls"]["cards"] >= 2,
              f"the Flood Watch card's × closes just that card ('{s['unhide']}' offered)")
        check(s["strip"] and "Heat Advisory" in s["strip"] and "Flood Watch" not in s["strip"], f"…and the strip moves on to the Heat Advisory ({(s['strip'] or '')[:40]!r})")
        check(s["focus"] == "wx-x", f"focus moves to the next ×, not lost ({s['focus']})")
        s = await load(pg)
        check([c["ev"] for c in s["cards"]] == ["Heat Advisory"], "after a reload the Flood Watch card stays closed")
        state["alerts"] = [dict(FW, id="urn:oid:test.1b"), HEAT]
        s = await load(pg)
        check([c["ev"] for c in s["cards"]] == ["Heat Advisory"], "an NWS re-issue of the same Flood Watch (new id) stays closed")
        state["alerts"] = [dict(FW, id="urn:oid:test.1c", ends=iso(9), expires=iso(9)), HEAT]
        s = await load(pg)
        check([c["ev"] for c in s["cards"]] == ["Heat Advisory"], "same headline, new id + later end (moderate): still closed (by headline)")
        # new and upgraded alerts show
        FFW = alert(3, "Flash Flood Warning", "Severe", 3)
        state["alerts"] = [FFW, FW, HEAT]
        s = await load(pg)
        check([c["ev"] for c in s["cards"]] == ["Flash Flood Warning", "Heat Advisory"], f"a new Severe alert arrives: it shows {[c['ev'] for c in s['cards']]}")
        state["alerts"] = [dict(FW, severity="Severe"), HEAT]
        s = await load(pg)
        check("Flood Watch" in [c["ev"] for c in s["cards"]], "the closed Flood Watch upgraded to Severe (same id) shows again")
        # severe alerts aren't hidden by a look-alike headline
        state["alerts"] = [FFW, HEAT]; await load(pg)
        await pg.click("#alerts .alert.sev-Severe .wx-x"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check("Flash Flood Warning" not in [c["ev"] for c in s["cards"]], "a Severe card can be closed too")
        state["alerts"] = [dict(FFW, id="urn:oid:test.3b", ends=iso(4), expires=iso(4)), HEAT]
        s = await load(pg)
        check("Flash Flood Warning" in [c["ev"] for c in s["cards"]], "a NEW Severe alert with the same headline (new id, new end) still shows")
        state["alerts"] = [FFW, HEAT]
        s = await load(pg)
        check("Flash Flood Warning" not in [c["ev"] for c in s["cards"]] and s["unhide"], "the closed one itself stays closed")
        await pg.click("#alerts .wx-unhide"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check([c["ev"] for c in s["cards"]] == ["Flash Flood Warning", "Heat Advisory"] and not s["unhide"], "'Show 1 closed alert' brings it back")
        # the strip's ✕ doesn't close the card
        await pg.click("#alert-strip .as-x"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check(len(s["cards"]) == 2, "the strip's ✕ hides the strip alert only; the Weather tab keeps both cards")
        # all clear: closes until an alert arrives
        state["alerts"] = []
        s = await load(pg)
        check(s["clear"] and "No active" in s["clear"]["text"], "all clear: the all-clear bubble shows")
        looks(s, "light 390 all-clear")
        await pg.click("#alerts .no-alerts .wx-x"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(STATE)
        check(not s["clear"] and s["ls"]["clear"] == "1", "its × closes it")
        s = await load(pg)
        check(not s["clear"], "after a reload it stays closed")
        state["alerts"] = [alert(4, "Wind Advisory", "Minor", 5)]
        s = await load(pg)
        check([c["ev"] for c in s["cards"]] == ["Wind Advisory"] and s["ls"]["clear"] is None, "an alert arrives: it shows, and the all-clear flag resets")
        state["alerts"] = []
        s = await load(pg)
        check(bool(s["clear"]), "the next all-clear shows again")
        check(not errs, f"no page errors {errs[:2]}")
        await ctx.close()
        # ---- dark 390 + light 320: looks
        for scheme, width, shot in (("dark", 390, "weather-close-dark.png"), ("light", 320, "weather-close-320.png")):
            state["alerts"] = [FFW, FW]
            ctx, pg, errs = await newctx(b, p, scheme, width)
            s = await load(pg)
            looks(s, f"{scheme} {width}")
            y = await pg.evaluate(YELLOW, ["#alerts", "#alerts *", "#wx-disclaimer", "#wx-disclaimer *"])
            check(not y, f"{scheme} {width}: no yellow {y[:3]}")
            if scheme == "dark": check(s["disc"]["x"]["bg"] != "rgb(255, 255, 255)", f"dark: the × is dark, not a white blob ({s['disc']['x']['bg']})")
            await pg.evaluate("document.querySelector('#alerts').scrollIntoView({ block: 'start' }); scrollBy(0, -130); const t = document.querySelector('#sync'); if (t) t.dataset.state = 'done'"); await pg.wait_for_timeout(2500)
            await pg.screenshot(path=f"{OUT}/{shot}")
            check(not errs, f"{scheme} {width}: no page errors {errs[:2]}")
            await ctx.close()
        await b.close()
    print("\n" + ("ALL OK" if not fails else f"{len(fails)} FAILED:\n  - " + "\n  - ".join(fails)))
    sys.exit(1 if fails else 0)

asyncio.run(main())
