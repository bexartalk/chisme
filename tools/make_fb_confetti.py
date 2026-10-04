# v49.16 the phone top bar's Día de Muertos confetti tile (static/season/fb-confetti.svg): papel picado bits (little
# rectangles with a cut-out), marigold petals (small teardrops) and tiny sugar-skull sprinkles, in the Muertos colours
# (pink, orange, purple, turquoise; white only on the tiny skulls). No yellow. The tile repeats both ways, so the CSS can
# drift it down by exactly one tile height and loop with no seam.
import random, math
random.seed(1102)
W, H = 240, 64
PINK, ORANGE, MARI, PURPLE, TURQ = "#FF1A7F", "#FF6A0B", "#FF7A1A", "#A45CFF", "#00C9CD"
parts = []
def wrap(x, y, r, emit):   # draw at (x, y) and its wrapped copies so the tile is seamless
    for dx in (-W, 0, W):
        for dy in (-H, 0, H):
            X, Y = x + dx, y + dy
            if -r <= X <= W + r and -r <= Y <= H + r: emit(X, Y)
def picado(x, y, c, a):
    wrap(x, y, 6, lambda X, Y: parts.append(
        f'<g transform="translate({X:.1f} {Y:.1f}) rotate({a})"><path fill="{c}" fill-rule="evenodd" d="M-3.5-2.4h7v4.8h-7zM-1-.8h2v1.6h-2z"/></g>'))
def petal(x, y, c, a):
    wrap(x, y, 5, lambda X, Y: parts.append(
        f'<path fill="{c}" transform="translate({X:.1f} {Y:.1f}) rotate({a})" d="M0-3.6C1.9-1.8 2-0.2 0 2.6-2-0.2-1.9-1.8 0-3.6z"/>'))
def skull(x, y, a):
    wrap(x, y, 4, lambda X, Y: parts.append(
        f'<g transform="translate({X:.1f} {Y:.1f}) rotate({a})"><path fill="#fff" d="M0-2.6C1.7-2.6 2.7-1.5 2.7-.2 2.7.8 2.1 1.4 1.4 1.6V2.4H-1.4V1.6C-2.1 1.4-2.7.8-2.7-.2-2.7-1.5-1.7-2.6 0-2.6z"/>'
        f'<circle cx="-1" cy="-.3" r=".62" fill="#2a1250"/><circle cx="1" cy="-.3" r=".62" fill="#2a1250"/></g>'))
def dot(x, y, c, r):
    wrap(x, y, 2, lambda X, Y: parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r}" fill="{c}"/>'))
# spread on a jittered grid so nothing clumps
cells = [(i, j) for i in range(8) for j in range(2)]
kinds = (["picado"] * 6 + ["petal"] * 6 + ["skull"] * 2 + ["dot"] * 2)
random.shuffle(kinds)
for (i, j), k in zip(cells, kinds):
    x = i * W / 8 + random.uniform(4, W / 8 - 4); y = j * H / 2 + random.uniform(4, H / 2 - 4); a = random.randint(-60, 60)
    if k == "picado": picado(x, y, random.choice([PINK, ORANGE, PURPLE, TURQ]), a)
    elif k == "petal": petal(x, y, random.choice([ORANGE, MARI, ORANGE]), a)
    elif k == "skull": skull(x, y, random.randint(-20, 20))
    else: dot(x, y, random.choice([PINK, TURQ, PURPLE]), 1.3)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       '<!-- Chisme v49.16: Dia de Muertos top-bar confetti tile (tools/make_fb_confetti.py). No yellow. -->' + "".join(parts) + '</svg>\n')
import os, sys; out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "season", "fb-confetti.svg"); open(out, "w").write(svg); print(len(svg), "bytes")
