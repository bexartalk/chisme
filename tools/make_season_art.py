"""v49.12: the Día de los Muertos season art (original, drawn from code): static/season/*.svg
papel-picado.svg (a string of cut-paper flags, tiles sideways), marigold.svg (a cempasúchil), sugar-skull.svg (a smiling
calaverita with flower eyes), candle.svg (a little lit candle). (The header's confetti turns into marigold petals in CSS.)
Run: python3 tools/make_season_art.py"""
import math, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "season")
os.makedirs(OUT, exist_ok=True)
def f(x): return f"{x:.2f}".rstrip("0").rstrip(".")
def save(name, svg): open(os.path.join(OUT, name), "w").write(svg.strip() + "\n"); print(name, len(svg))

def marigold_g(cx=0, cy=0, s=1.0):
    out = []
    for n, r, rr, col in ((14, 8.2, 3.5, "#e86a00"), (14, 7.6, 3.2, "#ff8a00"), (11, 5.0, 2.9, "#ffa41b"), (8, 2.6, 2.3, "#ffc93c")):
        for i in range(n):
            a = 2 * math.pi * i / n + (0.2 if col == "#ff8a00" else 0)
            out.append(f'<circle cx="{f(cx + s * r * math.cos(a))}" cy="{f(cy + s * r * math.sin(a))}" r="{f(s * rr)}" fill="{col}"/>')
    out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(s * 1.7)}" fill="#c25200"/>')
    return "".join(out)

save("marigold.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 24 24">{marigold_g()}</svg>')

# papel picado: 5 flags on a string; each flag has a cut-out border of holes, a flower, little diamonds and a scalloped bottom
W, H, FW, FH = 300, 50, 50, 40
cols = ["#ff3d8b", "#ff8a00", "#1fb8bf", "#ffc21a", "#9b5de5"]
def flag_mask():
    m = [f'<rect x="0" y="0" width="{FW}" height="{FH + 6}" fill="#fff"/>']
    for i in range(7): m.append(f'<circle cx="{f(5 + i * 6.67)}" cy="5.5" r="1.4" fill="#000"/>')   # the punched row under the string
    cx, cy = FW / 2, 19
    for i in range(6):
        a = 2 * math.pi * i / 6 - math.pi / 2
        m.append(f'<ellipse cx="{f(cx + 5.6 * math.cos(a))}" cy="{f(cy + 5.6 * math.sin(a))}" rx="2.6" ry="3.9" transform="rotate({f(math.degrees(a) + 90)} {f(cx + 5.6 * math.cos(a))} {f(cy + 5.6 * math.sin(a))})" fill="#000"/>')
    m.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="2" fill="#000"/>')
    for x in (8, FW - 8):
        m.append(f'<path d="M{x} 13l3 4-3 4-3-4z" fill="#000"/><path d="M{x} 24l2.4 3.2-2.4 3.2-2.4-3.2z" fill="#000"/>')
    for i in range(5): m.append(f'<circle cx="{f(9 + i * 8)}" cy="33" r="1.6" fill="#000"/>')
    return "".join(m)
def flag_shape():
    d = f"M0 0H{FW}V{FH}"
    n = 5
    for i in range(n, 0, -1):   # scallops along the bottom, right to left
        x0 = FW * i / n; x1 = FW * (i - 1) / n
        d += f"Q{f((x0 + x1) / 2)} {FH + 7} {f(x1)} {FH}"
    return d + "Z"
flags = []
for i, col in enumerate(cols):
    x = 5 + i * 60; y = 4 + (2 if i % 2 else 0)
    flags.append(f'<g transform="translate({x} {y})"><path d="{flag_shape()}" fill="{col}" mask="url(#cut)"/></g>')
save("papel-picado.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + 6}" width="{W}" height="{H + 6}">
<defs><mask id="cut" maskUnits="userSpaceOnUse" x="0" y="0" width="{FW}" height="{FH + 8}">{flag_mask()}</mask></defs>
<path d="M0 4Q75 9 150 4T300 4" fill="none" stroke="#f6e7c8" stroke-width="1.6"/>
{"".join(flags)}</svg>''')

# sugar skull: a friendly calaverita (round, smiling), turquoise flower eyes with pink petals, a pink heart nose,
# a marigold on the forehead, orange cheek dots, a stitched smile
eyes = []
for ex in (13.2, 26.8):
    for i in range(8):
        a = 2 * math.pi * i / 8
        eyes.append(f'<circle cx="{f(ex + 6.3 * math.cos(a))}" cy="{f(21 + 6.3 * math.sin(a))}" r="1.5" fill="#ff3d8b"/>')
    eyes.append(f'<circle cx="{ex}" cy="21" r="5" fill="#1fb8bf"/><circle cx="{ex}" cy="21" r="2.7" fill="#24103f"/><circle cx="{f(ex - 1)}" cy="20" r=".9" fill="#fff"/>')
teeth = "".join(f'<path d="M{f(14.5 + i * 2.75)} 34.2v3.4" stroke="#24103f" stroke-width=".9"/>' for i in range(5))
save("sugar-skull.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 44">
<path d="M20 2C9.5 2 3 9.6 3 18.6c0 6.6 3.6 10.6 7.4 12v5.6c0 3.2 2.6 5.6 5.8 5.6h7.6c3.2 0 5.8-2.4 5.8-5.6v-5.6c3.8-1.4 7.4-5.4 7.4-12C37 9.6 30.5 2 20 2z" fill="#fff6e8" stroke="#24103f" stroke-width="1.6"/>
<g transform="translate(20 9.6) scale(.42)">{marigold_g()}</g>
{"".join(eyes)}
<path d="M20 31.6c-1.2-1-3.4-2.4-3.4-4.1 0-1.2 1-2 2-2 .6 0 1.1.3 1.4.8.3-.5.8-.8 1.4-.8 1 0 2 .8 2 2 0 1.7-2.2 3.1-3.4 4.1z" fill="#ff3d8b"/>
<circle cx="7.4" cy="27.4" r="1.3" fill="#ff8a00"/><circle cx="32.6" cy="27.4" r="1.3" fill="#ff8a00"/>
<path d="M13.4 34.2q6.6 3.6 13.2 0" fill="none" stroke="#24103f" stroke-width="1.2" stroke-linecap="round"/>{teeth}
</svg>''')


save("candle.svg", '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 44">
<defs><radialGradient id="g" cx="50%" cy="40%" r="50%"><stop offset="0" stop-color="#ffd27a" stop-opacity=".9"/><stop offset="1" stop-color="#ff8a00" stop-opacity="0"/></radialGradient></defs>
<circle cx="12" cy="11" r="11" fill="url(#g)"/>
<path d="M12 3c2.6 3.4 3.6 5.6 3.6 7.6a3.6 3.6 0 0 1-7.2 0C8.4 8.6 9.4 6.4 12 3z" fill="#ffb627"/><path d="M12 7c1.2 1.8 1.7 3 1.7 4a1.7 1.7 0 0 1-3.4 0c0-1 .5-2.2 1.7-4z" fill="#fff4c6"/>
<path d="M12 14v3" stroke="#3a2a1a" stroke-width="1"/>
<rect x="6" y="17" width="12" height="25" rx="2" fill="#fbeedd"/><path d="M6 21c2 1.6 4 0 6 1.4s4 0 6-1" fill="none" stroke="#f0d9bb" stroke-width="1.4"/>
</svg>''')
