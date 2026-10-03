"""v49.15.3: the Día de los Muertos sugar skull (calavera de azúcar), our own art drawn from code, one reusable SVG symbol
(<symbol id="calavera" viewBox="0 0 40 44">). Hand-painted look: a shaded bone-white skull (radial gradient white → silver,
a soft highlight, silver shading under the cheekbones), ornate forehead filigree around a marigold with two little pink
roses, petal rings around the eye sockets, a heart nose, stitched teeth, dotted scrollwork on the cheeks and chin.
Palette: turquoise #00C9CD, pink #FF1A7F, orange #FF6A0B, black, white, silver (#C9CED6 / #A7A9AC). No yellow.
Writes static/season/calavera.svg (top bar + desktop hero), static/season/sugar-skull.svg (the greeting banner; same art)
and puts the same symbol on two flags of static/season/papel-picado.svg. Run: python3 tools/make_calavera.py"""
import math, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "static", "season")
T, P, O, K, W, S, S2 = "#00C9CD", "#FF1A7F", "#FF6A0B", "#000", "#fff", "#C9CED6", "#A7A9AC"
def f(x): return f"{x:.2f}".rstrip("0").rstrip(".")

def petals(cx, cy, r, n, rx, ry, cols, rot0=0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + rot0; x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" transform="rotate({f(math.degrees(a) + 90)} {f(x)} {f(y)})" fill="{cols[i % len(cols)]}"/>')
    return "".join(out)

def dots(pts, r, cols):
    return "".join(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{cols[i % len(cols)]}"/>' for i, (x, y) in enumerate(pts))

def mirror(d):   # mirror a path's absolute x coordinates around x = 20 (only M/C/Q/L/S with absolute pairs)
    nums = iter(re.findall(r"[A-Za-z]|-?[\d.]+", d)); out = []; cmd = None; k = 0
    for t in nums:
        if t.isalpha(): out.append(t); k = 0; continue
        out.append(f(40 - float(t)) if k % 2 == 0 else t); k += 1
    return " ".join(out)

SKULL = "M20 2C9.6 2 3 9.4 3 18.6c0 5.8 2.6 9.8 6.4 12.2v4.6c0 3.6 2.8 6.2 6.2 6.2h8.8c3.4 0 6.2-2.6 6.2-6.2v-4.6c3.8-2.4 6.4-6.4 6.4-12.2C37 9.4 30.4 2 20 2Z"
L_SCROLL = "M17.6 9.4C15.6 7.2 12 7.4 10.6 9.6C9.6 11.4 11 13.2 12.8 12.4"          # forehead filigree, left half
L_SCROLL2 = "M17.4 12.2C15.4 13.8 12.6 14.4 10.4 13.8"
L_CHEEK = "M9.6 25.4C7 25.4 6.4 28.4 8.4 29.2C9.8 29.6 10.6 28.2 9.6 27.4"        # cheek curl, left
def symbol():
    s = [f'<symbol id="calavera" viewBox="0 0 40 44">',
         f'<path d="{SKULL}" fill="url(#cv-bone)" stroke="{K}" stroke-width="1.4" stroke-linejoin="round"/>',
         # painted shading: silver under the cheekbones and around the jaw, a soft highlight on the crown
         f'<ellipse cx="9.6" cy="29" rx="3.4" ry="2.2" fill="{S2}" opacity=".35"/><ellipse cx="30.4" cy="29" rx="3.4" ry="2.2" fill="{S2}" opacity=".35"/>',
         f'<ellipse cx="13.4" cy="6.6" rx="5" ry="2.2" transform="rotate(-24 13.4 6.6)" fill="{W}" opacity=".85"/>',
         # forehead filigree: turquoise scrolls + pink/turquoise dot rows, a marigold in the middle, two little roses
         f'<g fill="none" stroke="{T}" stroke-width=".9" stroke-linecap="round"><path d="{L_SCROLL}"/><path d="{mirror(L_SCROLL)}"/><path d="{L_SCROLL2}"/><path d="{mirror(L_SCROLL2)}"/></g>',
         dots([(20 + 6.2 * math.cos(a), 10 + 6.2 * math.sin(a)) for a in [math.radians(d) for d in (200, 220, 240, 300, 320, 340)]], .55, [P, K]),
         dots([(14.5, 15.6), (17.2, 15.2), (22.8, 15.2), (25.5, 15.6)], .5, [P, T, T, P]),
         petals(20, 9.6, 2.5, 10, 1.15, 1.7, [O]), f'<circle cx="20" cy="9.6" r="1.5" fill="{P}" stroke="{K}" stroke-width=".4"/>',
         *[f'<circle cx="{x}" cy="5.6" r="1.25" fill="{P}"/><path d="M{f(x - .6)} 5.4a.7.7 0 1 1 .9.8" fill="none" stroke="{K}" stroke-width=".35"/>' for x in (14.2, 25.8)],
         # eyes: a ring of petals (pink / orange / turquoise), a turquoise rim, a black socket, a painted highlight
         *[petals(ex, 20.6, 5.5, 12, .95, 1.6, [P, T, O, T]) + f'<circle cx="{ex}" cy="20.6" r="4.3" fill="{T}"/><circle cx="{ex}" cy="20.6" r="3.4" fill="{K}"/>'
           f'<circle cx="{f(ex - 1.1)}" cy="19.4" r=".9" fill="{W}"/><circle cx="{f(ex + 1.2)}" cy="21.9" r=".4" fill="{W}" opacity=".7"/>' for ex in (13, 27)],
         # heart nose (point down), pink inside a black outline
         f'<path d="M20 29.6c-1.3-1-3.3-2.3-3.3-4 0-1.2.9-2 1.9-2 .6 0 1.1.3 1.4.8.3-.5.8-.8 1.4-.8 1 0 1.9.8 1.9 2 0 1.7-2 3-3.3 4Z" fill="{P}" stroke="{K}" stroke-width=".7" stroke-linejoin="round"/>',
         # cheeks: dotted scrollwork + a little rose / marigold
         f'<g fill="none" stroke="{T}" stroke-width=".8" stroke-linecap="round"><path d="{L_CHEEK}"/><path d="{mirror(L_CHEEK)}"/></g>',
         dots([(6.2, 24.2), (5.6, 26.4), (5.8, 28.8), (34.2, 24.2), (34.4, 26.4), (34.2, 28.8)], .5, [P, O, P]),
         f'<circle cx="11.6" cy="26" r=".9" fill="{O}"/><circle cx="28.4" cy="26" r=".9" fill="{O}"/>',
         # stitched teeth: a white mouth band, a black seam, stitches across
         f'<rect x="13.2" y="31.4" width="13.6" height="4.4" rx="2" fill="{W}" stroke="{K}" stroke-width=".8"/>',
         f'<path d="M13.6 33.6H26.4" stroke="{K}" stroke-width=".7"/>',
         "".join(f'<path d="M{f(15.1 + i * 1.95)} 31.9v3.4" stroke="{K}" stroke-width=".55"/>' for i in range(6)),
         # chin: dotted scroll arc + a tiny spade
         dots([(20 + 6.4 * math.cos(math.radians(a)), 35.4 + 3.2 * math.sin(math.radians(a))) for a in (25, 45, 65, 115, 135, 155)], .5, [T, P, T]),
         f'<path transform="translate(20 37.2) scale(.62) translate(-20 -37.2)" d="M20 37.3c-1 1.1-2 1.8-2 2.7 0 .6.5 1 1 1 .4 0 .7-.2.9-.5l-.4 1.1h1l-.4-1.1c.2.3.5.5.9.5.5 0 1-.4 1-1 0-.9-1-1.6-2-2.7Z" fill="{P}"/>',
         '</symbol>']
    return "".join(s)

DEFS = (f'<radialGradient id="cv-bone" cx="40%" cy="32%" r="70%"><stop offset="0" stop-color="{W}"/><stop offset=".62" stop-color="{W}"/>'
        f'<stop offset="1" stop-color="{S}"/></radialGradient>')

def standalone(w, h, note):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 40 44" width="{w}" height="{h}" aria-hidden="true">'
            f'<!-- {note} -->\n<defs>{DEFS}{symbol()}</defs><use href="#calavera" xlink:href="#calavera" width="40" height="44"/></svg>\n')

def picado(old):
    """put the calavera on flags 2 and 4 of papel-picado.svg (over the cut-out flower), same symbol"""
    old = re.sub(r'<defs data-cv="1">.*?</defs>|<use data-cv[^>]*/>', "", old, flags=re.S)
    old = old.replace("<defs>", f'<defs data-cv="1">{DEFS}{symbol()}</defs><defs>', 1)
    gs = list(re.finditer(r'<g transform="translate\(([\d.]+) ([\d.]+)\)">', old)); add = []
    for i in (1, 3):
        if i < len(gs):
            x, y = float(gs[i].group(1)), float(gs[i].group(2))
            add.append(f'<use data-cv="1" href="#calavera" xlink:href="#calavera" x="{f(x + 15)}" y="{f(y + 7)}" width="20" height="22"/>')
    if 'xmlns:xlink' not in old: old = old.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    return old.replace("</svg>", "".join(add) + "</svg>")

if __name__ == "__main__":
    for name, w, h, note in (("calavera.svg", 40, 44, "v49.15.3 Día de Muertos calavera de azúcar (tools/make_calavera.py): our own art, no yellow"),
                             ("sugar-skull.svg", 40, 44, "v49.15.3 the greeting banner's sugar skull: the same calavera symbol (tools/make_calavera.py)")):
        svg = standalone(w, h, note); open(os.path.join(OUT, name), "w").write(svg); print(name, len(svg.encode()))
    p = os.path.join(OUT, "papel-picado.svg"); s = picado(open(p).read()); open(p, "w").write(s); print("papel-picado.svg", len(s.encode()))
