"""Generates the header art for static/index.html (original drawing, flat silhouettes):
  * two skylines on a 1600 x 140 canvas, centered on x = 800 (the phone shows x 605..995 at 1:1):
      - San Antonio: low downtown blocks, the Tower of the Americas (slim shaft, flared pod, spire),
        a stepped tower with a pyramid roof, a slant-topped tower and the Alamo's curved parapet
      - generic city: blocks + a few tall towers (used outside San Antonio / Bexar County)
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

def blocks(seed, lo, hi, x0=0, x1=1600, keep_out=()):
    """Background buildings: flat roofs, some setbacks and antennas. keep_out = [(a, b, max_h)]"""
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

TOWER_X = CX - 152
ground = f"M0 {GROUND}H1600V140H0Z"

# San Antonio: keep the blocks low right around the tower and the Alamo so they read clearly
sa_blocks = blocks(7, 10, 32, keep_out=[(TOWER_X - 24, TOWER_X + 24, 12), (CX + 40, CX + 94, 10)])
sa = sa_blocks + [tower_of_americas(TOWER_X), stepped_pyramid(CX + 116, 26, 50), slant_top(CX + 94, 20, 44), alamo(CX + 44),
                  f"M{CX + 150} {GROUND}V{GROUND - 46}H{CX + 172}V{GROUND}Z", ground]

city_blocks = blocks(11, 12, 40, keep_out=[(TOWER_X - 16, TOWER_X + 16, 14)])
city = city_blocks + [spire_tower(TOWER_X - 11, 22, 64), spire_tower(CX + 96, 26, 58), slant_top(CX + 60, 24, 48),
                      f"M{CX + 130} {GROUND}V{GROUND - 52}H{CX + 152}V{GROUND}Z", ground]

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
      <g class="sky-sa"><path d="{"".join(sa)}"/></g>
      <g class="sky-city"><path d="{"".join(city)}"/></g>
    </svg>
    <button type="button" id="settings-btn" class="brand-bubble" aria-label="Settings" aria-haspopup="dialog" aria-controls="settings">
      <svg class="bubble" viewBox="{BUBBLE_VB}" aria-hidden="true" focusable="false">
        <path class="bubble-edge" d="{ICON["bubble"]}"/><path class="bubble-fill" d="{ICON["bubble"]}"/>{inner_conf}
        <path class="bubble-word" fill-rule="evenodd" d="{ICON["letters"]}"/>
      </svg>
    </button>
    <!-- /HEADER-ART -->'''
if __name__ == "__main__":
    import re as _re
    page = pathlib.Path(__file__).resolve().parent.parent / "static" / "index.html"
    html = page.read_text()
    html, n = _re.subn(r"<!-- HEADER-ART.*?<!-- /HEADER-ART -->", lambda m: ART, html, count=1, flags=_re.S)
    assert n == 1, "HEADER-ART markers not found in index.html"
    page.write_text(html); print("updated", page)
