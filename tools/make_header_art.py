"""Generates the header art for static/index.html (original drawing, flat silhouettes):
  * two skylines on a 1600 x 140 canvas, centered on x = 800 (the phone shows x 605..995 at 1:1):
      - San Antonio: low downtown blocks, the Tower of the Americas (slim shaft, flared pod, spire),
        a stepped tower with a pyramid roof, a slant-topped tower and the Alamo's curved parapet
      - Houston: Williams Tower (left), Pennzoil Place's twin slant-topped towers, the stepped gables of the
        Bank of America Center and the tall JPMorgan Chase Tower
      - Austin: the Texas Capitol dome (left), the Frost Bank Tower's notched crown, the UT Tower, The Independent
      - Dallas–Fort Worth: Reunion Tower's ball (left), Fountain Place's faceted prism, Bank of America Plaza
      - Miami: palms + the Freedom Tower's cupola (left), Brickell slabs, a palm
      - generic city: blocks + a few tall towers (anywhere else)
  * the app icon's own speech bubble (smooth hand-drawn oval, one curved tail at the bottom-left), its
    'Chisme' lettering and the confetti inside it, vector-traced from the icon by tools/trace_icon_bubble.py
    (tools/icon_bubble.json), plus Fiesta confetti in the icon's colours around it
Writes it into static/index.html between the HEADER-ART markers.
    ./venv/bin/python tools/make_header_art.py
"""
import json, math, pathlib, random

GROUND = 134          # y of the street line; the canvas is 140 tall
CX = 800              # canvas centre (= screen centre)

def f(v): return f"{v:.1f}".rstrip("0").rstrip(".")

def blocks(seed, lo, hi, x0=0, x1=1600, keep_out=(), rects=None):
    """Background buildings: flat roofs, some setbacks and antennas. keep_out = [(a, b, max_h)]
    rects (v46): collects each building's box (x, top, w), for its little windows"""
    rnd = random.Random(seed); x = x0; parts = []
    while x < x1:
        w = rnd.randint(14, 34); h = rnd.randint(lo, hi)
        for a, b, mh in keep_out:
            if x < b and x + w > a: h = min(h, mh)
        top = GROUND - h
        d = f"M{x} {GROUND}V{top}"
        r = rnd.random()
        if r < 0.22 and w > 20 and h > 22:                       # setback
            s = rnd.randint(4, 7); d += f"H{x + s}V{top - 7}H{x + w - s}V{top}H{x + w}"
        elif r < 0.34 and h > 18:                                 # antenna
            m = x + w // 2; d += f"H{m - 1}V{top - 9}H{m + 1}V{top}H{x + w}"
        else:
            d += f"H{x + w}"
        d += f"V{GROUND}Z"; parts.append(d)
        if rects is not None: rects.append((x, top, w))
        x += w + rnd.choice((0, 0, 1, 2))
    return parts

def tower_of_americas(x):
    """Slim tapering shaft; the pod flares out from it (curved underside), two decks, a roof cap and a thin spire."""
    return (f"M{x - 4.5} {GROUND}L{x - 3.5} 100Q{x - 5} 93 {x - 15} 92V86H{x - 13}V83H{x - 9}V80H{x - 1}V64H{x + 1}V80"
            f"H{x + 9}V83H{x + 13}V86H{x + 15}V92Q{x + 5} 93 {x + 3.5} 100L{x + 4.5} {GROUND}Z")

def stepped_pyramid(x, w=26, h=60):
    t = GROUND - h
    return (f"M{x} {GROUND}V{t + 14}H{x + 3}V{t + 8}H{x + 6}V{t + 4}L{x + w / 2} {t - 8}L{x + w - 6} {t + 4}"
            f"V{t + 8}H{x + w - 3}V{t + 14}H{x + w}V{GROUND}Z")

def slant_top(x, w=24, h=54):
    return f"M{x} {GROUND}V{GROUND - h + 12}L{x + w} {GROUND - h}V{GROUND}Z"

def alamo(x, w=46):
    """Low facade with the curved 'hump' parapet."""
    b = GROUND - 12; m = x + w / 2
    return (f"M{x} {GROUND}V{b}H{x + 10}C{x + 12} {b - 3} {m - 8} {b - 4} {m - 5} {b - 9}"
            f"C{m - 3} {b - 12} {m + 3} {b - 12} {m + 5} {b - 9}C{m + 8} {b - 4} {x + w - 12} {b - 3} {x + w - 10} {b}"
            f"H{x + w}V{GROUND}Z")

def spire_tower(x, w=22, h=76):
    t = GROUND - h; m = x + w / 2
    return f"M{x} {GROUND}V{t + 10}H{x + 4}V{t}H{x + w - 4}V{t + 10}H{x + w}V{GROUND}Z M{m - 1} {t}V{t - 14}H{m + 1}V{t}Z"

def windows(seed, rects):
    """v46: small window squares in the buildings (2 x 2 units on a 5 x 6 grid, about half of them lit), drawn in the
    header's own background colour so they read as tiny cut-outs: subtle, crisp (whole units), no new colours."""
    rnd = random.Random(seed); d = []
    for x, top, w in rects:
        cols = int((w - 4) // 5)
        if cols < 1 or GROUND - top < 14: continue
        x0 = x + (w - (cols * 5 - 3)) // 2
        for y in range(int(top) + 4, GROUND - 6, 6):
            for k in range(cols):
                if rnd.random() < 0.5: d.append(f"M{x0 + k * 5} {y}h2v2h-2Z")
    return "".join(d)

def heli(x, y):
    """v46: a small helicopter silhouette (faces left): cabin, tail boom + fin, mast, main rotor, skids."""
    P = lambda dx, dy: f"{f(x + dx)} {f(y + dy)}"
    return (f"M{P(-7, 0)}C{P(-7, -4)} {P(-3, -5)} {P(1, -5)}H{f(x + 4)}C{P(7, -5)} {P(8, -2)} {P(8, 0)}C{P(8, 3)} {P(5, 4)} {P(1, 4)}H{f(x - 4)}C{P(-6, 4)} {P(-7, 2)} {P(-7, 0)}Z"
            f"M{P(6, -2.5)}L{P(19, -3)}V{f(y - 1.2)}L{P(6, 1)}Z M{P(17, -3)}L{P(18.6, -7.5)}H{f(x + 20)}L{P(19.8, -1.2)}Z"
            f"M{P(0, -5)}V{f(y - 7)}H{f(x + 1.5)}V{f(y - 5)}Z M{P(-12, -7.8)}H{f(x + 14)}V{f(y - 6.8)}H{f(x - 12)}Z"
            f"M{P(-3, 3.5)}h1v3h-1Z M{P(3, 3.5)}h1v3h-1Z M{P(-6.5, 6.3)}H{f(x + 7)}V{f(y + 7.3)}H{f(x - 5.5)}Q{P(-7, 7.3)} {P(-7.5, 5.8)}Z")

TOWER_X = CX - 152
ground = f"M0 {GROUND}H1600V140H0Z"

# San Antonio: keep the blocks low right around the tower and the Alamo so they read clearly
sa_rects = []; sa_blocks = blocks(7, 10, 32, rects=sa_rects, keep_out=[(TOWER_X - 24, TOWER_X + 24, 12), (CX + 40, CX + 94, 10)])
sa = sa_blocks + [tower_of_americas(TOWER_X), stepped_pyramid(CX + 116, 26, 50), slant_top(CX + 94, 20, 44), alamo(CX + 44),
                  f"M{CX + 150} {GROUND}V{GROUND - 46}H{CX + 172}V{GROUND}Z", ground]

sa_rects += [(CX + 116, GROUND - 50 + 14, 26), (CX + 94, GROUND - 44 + 12, 20), (CX + 150, GROUND - 46, 22)]
city_rects = []; city_blocks = blocks(11, 12, 40, rects=city_rects, keep_out=[(TOWER_X - 16, TOWER_X + 16, 14)])
city = city_blocks + [spire_tower(TOWER_X - 11, 22, 64), spire_tower(CX + 96, 26, 58), slant_top(CX + 60, 24, 48),
                      f"M{CX + 130} {GROUND}V{GROUND - 52}H{CX + 152}V{GROUND}Z", ground]

# --- other metros (simple flat silhouettes; landmark left of the bubble at TOWER_X, the rest right of it)
def williams_tower(x, w=18, h=84):
    t = GROUND - h
    return f"M{x} {GROUND}V{t + 8}L{x + 3} {t + 2}H{x + w - 3}L{x + w} {t + 8}V{GROUND}Z M{x + w / 2 - 1} {t + 2}V{t - 8}H{x + w / 2 + 1}V{t + 2}Z"

def pennzoil(x, w=16, h=58, gap=3):
    t = GROUND - h
    return (f"M{x} {GROUND}V{t + 10}L{x + w} {t}V{GROUND}Z "
            f"M{x + w + gap} {GROUND}V{t}L{x + 2 * w + gap} {t + 10}V{GROUND}Z")

def gables(x, w=30, h=60):
    t = GROUND - h
    return (f"M{x} {GROUND}V{t + 22}L{x + 4} {t + 14}L{x + 8} {t + 22}V{t + 12}L{x + 12} {t + 4}L{x + 15} {t - 4}"
            f"L{x + 18} {t + 4}L{x + 22} {t + 12}V{t + 22}L{x + 26} {t + 14}L{x + w} {t + 22}V{GROUND}Z")

def bevel_box(x, w=24, h=78, b=5):
    t = GROUND - h
    return f"M{x} {GROUND}V{t + b}L{x + b} {t}H{x + w}V{GROUND}Z"

def capitol(x, w=64):
    m = x + w / 2; b = GROUND - 14
    return (f"M{x} {GROUND}V{b}H{m - 12}V{b - 10}H{m - 9}V{b - 16}"
            f"C{m - 9} {b - 30} {m + 9} {b - 30} {m + 9} {b - 16}V{b - 10}H{m + 12}V{b}H{x + w}V{GROUND}Z "
            f"M{m - 2} {b - 27}V{b - 34}H{m - 1}V{b - 40}H{m + 1}V{b - 34}H{m + 2}V{b - 27}Z")

def frost_tower(x, w=22, h=70):
    t = GROUND - h
    return (f"M{x} {GROUND}V{t + 22}L{x + 3} {t + 16}V{t + 12}L{x + 6} {t + 8}V{t + 4}L{x + w / 2} {t - 8}"
            f"L{x + w - 6} {t + 4}V{t + 8}L{x + w - 3} {t + 12}V{t + 16}L{x + w} {t + 22}V{GROUND}Z")

def ut_tower(x, w=14, h=56):
    t = GROUND - h; m = x + w / 2
    return f"M{x} {GROUND}V{t + 8}H{x + 2}V{t + 2}H{x + w - 2}V{t + 8}H{x + w}V{GROUND}Z M{m - 3} {t + 2}V{t - 3}L{m} {t - 7}L{m + 3} {t - 3}V{t + 2}Z"

def independent(x, h=64):
    parts, y, off = [], GROUND, 0
    for k, (dw, dh) in enumerate(((22, 16), (20, 14), (22, 12), (18, 12), (16, 10))):
        off = (4, -3, 5, -2, 3)[k]
        parts.append(f"M{x + off} {y}V{y - dh}H{x + off + dw}V{y}Z"); y -= dh
    return " ".join(parts)

def reunion(x, r=10, h=72):
    t = GROUND - h
    return (f"M{x - 3} {GROUND}L{x - 1.5} {t + r}H{x + 1.5}L{x + 3} {GROUND}Z "
            f"M{x - r} {t}A{r} {r} 0 1 0 {x + r} {t}A{r} {r} 0 1 0 {x - r} {t}Z M{x - 1} {t - r}V{t - r - 8}H{x + 1}V{t - r}Z")

def fountain_place(x, w=26, h=72):
    t = GROUND - h
    return f"M{x} {GROUND}V{t + 18}L{x + 8} {t}L{x + w} {t + 26}V{GROUND}Z"

def freedom_tower(x, w=22, h=56):
    t = GROUND - h; m = x + w / 2
    return (f"M{x - 8} {GROUND}V{GROUND - 18}H{x}V{t + 16}H{x + 3}V{t + 8}H{x + w - 3}V{t + 16}H{x + w}V{GROUND - 18}H{x + w + 8}V{GROUND}Z "
            f"M{m - 4} {t + 8}V{t}C{m - 4} {t - 6} {m + 4} {t - 6} {m + 4} {t}V{t + 8}Z M{m - 0.8} {t - 5}V{t - 14}H{m + 0.8}V{t - 5}Z")

def palm(x, h=58, lean=6):
    t = GROUND - h; tx = x + lean
    trunk = f"M{x - 2} {GROUND}Q{x + lean * 0.2} {t + h / 2} {tx - 1} {t}H{tx + 1}Q{x + lean * 0.4} {t + h / 2} {x + 2} {GROUND}Z"
    fronds = "".join(f"M{tx} {t}Q{tx + dx * 0.5} {t - 10 + dy} {tx + dx} {t + dy}Q{tx + dx * 0.5} {t - 5 + dy} {tx} {t + 1}Z"
                     for dx, dy in ((-16, 6), (-12, 12), (16, 6), (12, 12), (-6, -1), (7, -1)))
    return trunk + " " + fronds

hou_rects = []; hou = blocks(21, 12, 38, rects=hou_rects, keep_out=[(TOWER_X - 20, TOWER_X + 20, 14)]) + [
    williams_tower(TOWER_X - 9), pennzoil(CX + 52), gables(CX + 96, 30, 58), bevel_box(CX + 134, 24, 80),
    f"M{CX + 164} {GROUND}V{GROUND - 50}H{CX + 184}V{GROUND}Z", ground]
atx_rects = []; atx = blocks(31, 10, 30, rects=atx_rects, keep_out=[(TOWER_X - 40, TOWER_X + 40, 10)]) + [
    capitol(TOWER_X - 32), frost_tower(CX + 60), ut_tower(CX + 100), independent(CX + 128),
    f"M{CX + 160} {GROUND}V{GROUND - 44}H{CX + 180}V{GROUND}Z", ground]
dal_rects = []; dal = blocks(41, 12, 36, rects=dal_rects, keep_out=[(TOWER_X - 16, TOWER_X + 16, 12)]) + [
    reunion(TOWER_X), fountain_place(CX + 60), bevel_box(CX + 98, 24, 84, 0), spire_tower(CX + 132, 20, 60),
    f"M{CX + 160} {GROUND}V{GROUND - 48}H{CX + 180}V{GROUND}Z", ground]
mia_rects = []; mia = blocks(51, 10, 28, rects=mia_rects, keep_out=[(TOWER_X - 46, TOWER_X + 40, 10)]) + [
    palm(TOWER_X - 36, 50, -5), freedom_tower(TOWER_X - 6), palm(TOWER_X + 30, 44, 6),
    bevel_box(CX + 58, 20, 70, 0), bevel_box(CX + 82, 18, 82, 6), f"M{CX + 104} {GROUND}V{GROUND - 60}H{CX + 124}V{GROUND}Z",
    palm(CX + 140, 52, 5), f"M{CX + 156} {GROUND}V{GROUND - 40}H{CX + 178}V{GROUND}Z", ground]

ICON = json.loads((pathlib.Path(__file__).resolve().parent / "icon_bubble.json").read_text())
bx0, by0, bx1, by1 = ICON["bubble_box"]; M = 6                 # icon pixels; margin for the dark-mode outline
BUBBLE_VB = f"{bx0 - M} {by0 - M} {bx1 - bx0 + 2 * M} {by1 - by0 + 2 * M}"
inner_conf = "".join(f'<path class="i{k[1]}" d="{d}"/>' for k, d in ICON["confetti"].items())

def confetti(items):
    return "".join(f'<rect class="{c}" x="{f(x)}" y="{f(y)}" width="{w}" height="{h}" rx="1" transform="rotate({r} {f(x + w / 2)} {f(y + h / 2)})"/>'
                   for x, y, w, h, r, c in items)
# Fiesta confetti in the sky around the bubble, icon-style (chunky pink / orange / pale-cyan chips).
# x in phone-screen px at 390 wide (skyline x = screen x + 605); y in skyline px (screen y = y + 12, the header is 166 tall).
SCREEN = [(20, 16, -30, "ip"), (56, 8, 25, "io"), (78, 34, -15, "il"), (12, 50, 40, "io"), (70, 60, 60, "ip"), (40, 30, 10, "ip"),
          (298, 12, 20, "ip"), (336, 28, -35, "io"), (372, 10, 15, "ip"), (362, 54, 50, "il"), (304, 50, -20, "io"), (382, 36, -60, "io"),
          # wider screens
          (-30, 20, 30, "io"), (-70, 44, -20, "ip"), (-110, 14, 50, "il"), (-150, 40, 15, "io"), (-190, 12, -35, "ip"),
          (420, 18, -25, "ip"), (460, 42, 35, "io"), (500, 12, -10, "il"), (540, 38, 55, "ip"), (580, 16, 20, "io")]
sky_conf = confetti([(x + 605, y, 11, 7, r, c) for x, y, r, c in SCREEN])

ART = f'''<!-- HEADER-ART (generated by tools/make_header_art.py): flat skyline + the app icon's speech bubble -->
    <svg class="skyline" viewBox="0 0 1600 140" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">
      <g class="confetti">{sky_conf}</g>
      <g class="sky-sa"><path d="{"".join(sa)}"/><path class="sky-win" d="{windows(70, sa_rects)}"/></g>
      <g class="sky-city"><path d="{"".join(city)}"/><path class="sky-win" d="{windows(110, city_rects)}"/></g>
      <g class="sky-houston"><path d="{"".join(hou)}"/><path class="sky-win" d="{windows(210, hou_rects)}"/></g>
      <g class="sky-austin"><path d="{"".join(atx)}"/><path class="sky-win" d="{windows(310, atx_rects)}"/></g>
      <g class="sky-dallas"><path d="{"".join(dal)}"/><path class="sky-win" d="{windows(410, dal_rects)}"/></g>
      <g class="sky-miami"><path d="{"".join(mia)}"/><path class="sky-win" d="{windows(510, mia_rects)}"/></g>
      <g class="heli-drift"><path class="heli" d="{heli(CX + 140, 63)}"/></g>
    </svg>
    <button type="button" id="settings-btn" class="brand-bubble" aria-label="Settings" aria-haspopup="dialog" aria-controls="settings">
      <svg class="bubble" viewBox="{BUBBLE_VB}" aria-hidden="true" focusable="false">
        <path class="bubble-edge" d="{ICON["bubble"]}"/><path class="bubble-fill" d="{ICON["bubble"]}"/>{inner_conf}
        <path class="bubble-word" fill-rule="evenodd" d="{ICON["letters"]}"/>
      </svg>
      <span class="gear-badge" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><circle class="gear-teeth" cx="12" cy="12" r="8.6" stroke-dasharray="3.38 3.38"/><circle class="gear-body" cx="12" cy="12" r="6.4"/><circle class="gear-hole" cx="12" cy="12" r="2.6"/></svg></span>
    </button>
    <!-- /HEADER-ART -->'''
if __name__ == "__main__":
    import re as _re
    page = pathlib.Path(__file__).resolve().parent.parent / "static" / "index.html"
    html = page.read_text()
    html, n = _re.subn(r"<!-- HEADER-ART.*?<!-- /HEADER-ART -->", lambda m: ART, html, count=1, flags=_re.S)
    assert n == 1, "HEADER-ART markers not found in index.html"
    page.write_text(html); print("updated", page)
