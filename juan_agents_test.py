"""v49.7 every agent can be cleared (The Juan That Got Away, static/juan.js).
Bug (v49.6): on a phone every tap is short, and letting go cut Juan's rising speed ×0.55, so a tap topped out ~35–70 units, about
the height of an agent's hitbox (64): agents were often impossible to clear, and partners stood only 130 apart.
  • simulation with the game's own physics (ChismeJuan.fall / trim / JUMP): for every agent placement on every level (Playa Neón too),
    a quick tap AND a held jump clear the agent's hitbox (the game's 5-unit forgiveness), at normal / Reduce motion / coffee speed,
    with the agent walking at Juan; there's a takeoff window of ≥ 6 frames (0.1 s) and the tap clears the hitbox by ≥ 20 units
  • agents are never back to back (≥ 380 apart), and every pair of neighbours can be cleared one after the other (land, jump again)
  • in the browser: the drawn agent (taller in v49.7) covers its hitbox (the hitbox isn't bigger than the picture), and in the real game
    a tap at the right moment clears every agent placement without getting caught
Screenshot: screenshots/agent-jump-fix.png (Juan clearing a taller agent, 390). Run against a local server (CHISME_URL, default :8211)."""
import asyncio, json, os, subprocess, sys
from playwright.async_api import async_playwright
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import pw_csp  # noqa: E401,F401  (v49.11: CSP-safe wait_for_function)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from popup_quiet import QUIET
BASE = os.environ.get("CHISME_URL", "http://localhost:8211")
OUT = os.path.join(HERE, "screenshots"); os.makedirs(OUT, exist_ok=True)
G = "__chisme.juegos.game"
fails = 0
def check(ok, what):
    global fails
    print(("  ok   " if ok else "  FAIL ") + what); fails += not ok

SIM = r"""
const J = require(process.argv[1]), DT = 1 / 60, HW = 32, HH = 88, PAD = 5, [AW, AH] = J.DIM.agent, out = { levels: [] };
// one run: Juan at speed v, agents walking at him at u (positions = their left edge at t=0, relative to Juan's left edge), jumps at the given frames
function run(ag, v, u, style, jumpsAt) {
  let x = 0, y = -HH, vy = 0, ground = true, peak = 0, a = ag.slice(), f = 0, k = 0;
  for (; f < 900; f++) {
    if (k < jumpsAt.length && f === jumpsAt[k] && ground) { vy = J.JUMP; ground = false; k++; if (style === "tap") vy = J.trim(vy); }
    x += v * DT; a = a.map((p) => p - u * DT);
    if (!ground) { vy = J.fall(vy, DT); y += vy * DT; if (y + HH >= 0) { y = -HH; vy = 0; ground = true; } }
    peak = Math.max(peak, -(y + HH));
    for (const p of a) if (x + PAD < p + AW && x + HW - PAD > p && y + PAD < 0 && y + HH - PAD > -AH) return { ok: false, f, peak };
    if (a.every((p) => x > p + AW)) return { ok: true, f, peak };
  }
  return { ok: false, f, peak };
}
const window1 = (gap, v, u, style) => { const ok = []; let peak = 0; for (let f = 0; f < 300; f++) { const r = run([gap], v, u, style, [f]); if (r.ok) { ok.push(f); peak = Math.max(peak, r.peak); } } return { n: ok.length, peak }; };
J.LEVELS.forEach((L, i) => {
  const n = i + 1, es = J.buildLevel(n).filter((e) => e.t === "agent").sort((a, b) => a.x - b.x), lv = { n, name: L.name, agents: es.length, worst: 999, peak: 999, gaps: [], pairs: 0, pairsOk: 0 };
  for (const e of es) {
    const u = Math.abs(e.vx);
    for (const v of [L.speed, L.speed * 0.88, L.speed * 1.4]) for (const uu of [u, -u * J.AWAY]) for (const style of ["tap", "hold"]) {   // he patrols: toward Juan, then back the same way at ¼ pace
      const w = window1(400, v, uu, style); lv.worst = Math.min(lv.worst, w.n); if (style === "tap" && v === L.speed && uu === u) lv.peak = Math.min(lv.peak, w.peak - (AH - PAD));
    }
  }
  for (let j = 1; j < es.length; j++) {   // neighbours: the patrol can bring them up to 100 closer; can Juan clear one, land, and clear the next?
    const gap = es[j].x - es[j - 1].x; lv.gaps.push(gap); if (gap > 900) continue;
    lv.pairs++; const u = Math.abs(es[j].vx), v = L.speed; let ok = false;
    for (let f1 = 0; f1 < 120 && !ok; f1++) { if (!run([400], v, u, "tap", [f1]).ok) continue; for (let f2 = f1 + 20; f2 < f1 + 200 && !ok; f2++) ok = run([400, 400 + gap - 100], v, u, "tap", [f1, f2]).ok; }
    lv.pairsOk += ok;
  }
  out.levels.push(lv);
});
console.log(JSON.stringify(out));
"""

async def main():
    js = os.path.join(HERE, "static", "juan.js")
    o = json.loads(subprocess.check_output(["node", "-e", SIM, js]))
    print("== simulation (the game's physics), every agent on every level")
    for lv in o["levels"]:
        check(lv["agents"] >= 2 and lv["worst"] >= 6 and lv["peak"] >= 20,
              f"level {lv['n']} {lv['name']}: all {lv['agents']} agents clear with a tap or a held jump at every speed (narrowest takeoff window {lv['worst']} frames, a tap clears the hitbox by {lv['peak']:.0f})")
        check(all(g >= 380 for g in lv["gaps"]) and lv["pairsOk"] == lv["pairs"], f"level {lv['n']}: never back to back (gaps {[round(g) for g in lv['gaps']]}), {lv['pairsOk']}/{lv['pairs']} neighbour pairs clear one after the other")

    async with async_playwright() as p:
        b = await p.webkit.launch()
        dev = dict(p.devices["iPhone 13"]); dev.pop("default_browser_type", None); dev["viewport"] = {"width": 390, "height": 844}
        ctx = await b.new_context(**dev); await ctx.add_init_script("localStorage.setItem('chisme-location-setup','1'); localStorage.setItem('chisme-swiped','1'); localStorage.setItem('chisme-ios-hint-dismissed','1'); localStorage.setItem('chisme-a2hs', JSON.stringify({done:true}));"); await ctx.add_init_script(QUIET)
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        await pg.goto(BASE + "/#juan"); await pg.wait_for_function("window.__chisme && __chisme.ready && __chisme.juegos.game", timeout=120000)
        print("== the drawn agent vs his hitbox")
        bb = await pg.evaluate("""(() => { const J = ChismeJuan, c = document.createElement('canvas'); c.width = 300; c.height = 300; const g = c.getContext('2d'); g.translate(150, 250); g.scale(1.06, J.AG_TALL);
          J.drawAgent(g, { pose: 'walk', ph: 1, t: 1, sk: 0 }); const d = g.getImageData(0, 0, 300, 300).data; let l = 300, r = 0, t = 300, bt = 0;
          for (let y = 0; y < 300; y++) for (let x = 0; x < 300; x++) if (d[(y * 300 + x) * 4 + 3] > 40) { l = Math.min(l, x); r = Math.max(r, x); t = Math.min(t, y); bt = Math.max(bt, y); }
          return { l: l - 150, r: r - 150, top: 250 - t, bot: 250 - bt, w: J.DIM.agent[0], h: J.DIM.agent[1] }; })()""")
        # the hitbox: 30×64 from the drawing's center line (x+15), feet at 0; the game forgives 5 on each side
        check(bb["l"] <= -(bb["w"] / 2 - 5) and bb["r"] >= bb["w"] / 2 - 5 and bb["top"] >= bb["h"] - 5 and bb["bot"] <= 5 and bb["top"] > 64 * 1.1,
              f"the agent is drawn {bb['top']} tall (taller than before) and {bb['r'] - bb['l']} wide; his {bb['w']}×{bb['h']} hitbox (5 forgiven) sits inside the drawing {bb}")
        print("== the real game: a tap clears every agent")
        await pg.evaluate("() => { const t = document.querySelector('#game-stage'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 60); }")
        await pg.click("#juan-ov [data-act=start]"); await pg.wait_for_timeout(300)
        shot = False
        for lv in o["levels"]:
            n = lv["n"]; cleared = tried = 0
            await pg.evaluate(f"{G}.warp({n}, 10)"); await pg.wait_for_timeout(200)
            xs = sorted(e["x"] for e in await pg.evaluate(G + ".ents()") if e["t"] == "agent")
            for ax in xs:
                tried += 1
                # warp well before him (the warp hook clears agents within 320), run up, and when he's ~45 ahead (inside the window whichever way he walks; the middle of the
                # takeoff window) jump + let go at once (a phone tap), all inside the page on animation frames
                for back in (480, 420):   # (a second, closer try if a run-up hazard or chaser got him first)
                  before = (await pg.evaluate(G + ".state"))["caught"]
                  ok = await pg.evaluate(f"""(async () => {{ const g = {G}, near = () => g.ents().filter((e) => e.t === 'agent').sort((p, q) => Math.abs(p.x - {ax}) - Math.abs(q.x - {ax}))[0];
                  g.warp({n}, {ax} - 32 - {back}); g.setHealth(100); const raf = () => new Promise((r) => requestAnimationFrame(r));
                  for (let k = 0; k < 240; k++) {{ await raf(); const a = near(), s = g.state; if (!a || s.mode !== 'run') return false; if (a.x - (s.x + 32) <= 45 && s.ground) break; }}
                  const d = near().x - (g.state.x + 32), gr = g.state.ground; g.jump(); document.dispatchEvent(new KeyboardEvent('keyup', {{ code: 'Space', bubbles: true }})); return [!!near() && Math.abs(near().x - {ax}) < 150, Math.round(d), gr, Math.round(g.state.y)]; }})()""")
                  if ok and ok[0]: break
                  await pg.wait_for_timeout(1600)
                info = ok; ok = ok and ok[0]
                if not ok: print("     (couldn't line up agent at", ax, ")")
                if not shot and not any(e["t"] == "cone" and -100 < e["x"] - ax < 0 for e in await pg.evaluate(G + ".ents()")):   # the screenshot (an agent with no cone to trip on, so he's standing tall): as Juan's front reaches him, mid-air
                    for _ in range(60):
                        q = await pg.evaluate(f"(() => {{ const s = {G}.state, a = {G}.ents().filter((e) => e.t === 'agent').sort((p, q) => Math.abs(p.x - {ax}) - Math.abs(q.x - {ax}))[0]; return [s.x + 32 - a.x, s.ground]; }})()")
                        if q[0] > -25 and not q[1]: break
                    await pg.screenshot(path=os.path.join(OUT, "agent-jump-fix.png")); shot = True
                await pg.wait_for_timeout(1100)
                s = await pg.evaluate(G + ".state")
                passed = any(e["t"] == "agent" and abs(e["x"] - ax) < 200 and e["st"] in ("huh", "walk", "trip", "dizzy") for e in await pg.evaluate(G + ".ents()")) and s["x"] > ax
                cleared += ok and passed and s["caught"] == before and s["mode"] == "run"
                if s["mode"] != "run": await pg.evaluate(f"{G}.warp({n}, 10)"); await pg.wait_for_timeout(300)
            check(cleared == tried and not errs, f"level {n} {lv['name']}: a tap cleared {cleared}/{tried} agents in the real game {errs[:1]}")
        await b.close()
    print(f"{fails} FAILED" if fails else "ALL PASS"); sys.exit(1 if fails else 0)
asyncio.run(main())
