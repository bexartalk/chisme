"""v43 (v49.5: classic-deck style, see CLASSIC below): renders the 54 Lotería Chismosa cards as vintage lithograph-style images (static/loteria/cards/01.webp … 54.webp).

Our OWN art (nothing copied or traced from a published deck): the original drawings from static/loteria_cards.js, re-inked
and re-colored in an old painted-print style: a painted scene behind each one (sky, water, desert, night, sunburst or a
room), a light halftone + paper grain, soft shading on the figure, bold outlines, a crisp white card border, the number in
the corner and the Spanish name on a clean white banner at the bottom. Bright, flat vintage-print colors like the classic
decks: sky-blue, royal-blue, grass-green, brick-red, orange and pink, and golden yellow only inside the art of the cards
that traditionally have it (El Diablito, La Estrella, El Alacrán, El Sol, La Corona: GOLD). The app's UI stays yellow-free.
Rendered once with Chrome (Playwright) so the phone just shows pictures.
Usage: ./venv/bin/python tools/make_loteria_cards.py [--sheet screenshots/x.png]"""
import asyncio, colorsys, json, re, subprocess, sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "static" / "loteria" / "cards"
W, H = 200, 300          # card units (2:3)
PX = 300                 # output width in pixels (≈ 3× the card's size on an iPhone tabla; flat art stays crisp)

# the drawings' Fiesta colors → bright, flat vintage-print inks
REMAP = {"#111": "#161616", "#fff": "#ffffff", "#00b8b0": "#159f8c", "#3ee8eb": "#6fd3e0", "#ff3d8b": "#ec4f7c", "#c2185b": "#b3244f",
         "#ff8a00": "#f57f17", "#c95f00": "#b85312", "#b9c0c7": "#c6cbd0", "#7c858f": "#6f7983", "#2f9e57": "#2e9a45", "#6cc26a": "#7cc860",
         "#e0243a": "#d7261e", "#1d2a4d": "#1c2f6b", "#f2efed": "#f8f6f2", "#8a5a3b": "#8e5a33", "#5e3a22": "#5e3a1e", "#c8643b": "#c9642f"}
# golden yellow, only in these cards' art (where the classic decks use it); their oranges turn gold
GOLD = {2, 35, 40, 46, 47}
GOLD_REMAP = {"#ff8a00": "#ffc114", "#c95f00": "#d99100"}
# backgrounds (light, deep): a sky gradient / sunburst in flat print colors
BG = {"sky": ("#bfe4fa", "#3a95dc"), "royal": ("#7fa8ec", "#1f4ea8"), "green": ("#c3eba4", "#3c9b43"), "red": ("#f6977a", "#c0392b"),
      "orange": ("#ffc58a", "#f0761e"), "pink": ("#fdd3df", "#ec7ea0"), "gold": ("#ffe680", "#f5b800"), "night": ("#4a6fc4", "#142a6b")}
# per card: (scene, background)
SCENE = {1: ("rays", "orange"), 2: ("rays", "gold"), 3: ("room", "pink"), 4: ("street", "sky"), 5: ("rain", "royal"), 6: ("water", "sky"),
         7: ("sky", "pink"), 8: ("room", "royal"), 9: ("room", "orange"), 10: ("sky", "sky"), 11: ("room", "royal"), 12: ("desert", "orange"),
         13: ("room", "pink"), 14: ("rays", "pink"), 15: ("room", "sky"), 16: ("sky", "royal"), 17: ("room", "red"), 18: ("room", "orange"),
         19: ("water", "sky"), 20: ("sky", "pink"), 21: ("rays", "sky"), 22: ("room", "green"), 23: ("night", "night"), 24: ("sky", "sky"),
         25: ("street", "pink"), 26: ("room", "orange"), 27: ("rays", "green"), 28: ("room", "green"), 29: ("room", "royal"), 30: ("water", "sky"),
         31: ("rays", "royal"), 32: ("street", "green"), 33: ("rays", "sky"), 34: ("street", "red"), 35: ("night", "night"), 36: ("room", "sky"),
         37: ("night", "royal"), 38: ("desert", "orange"), 39: ("desert", "sky"), 40: ("rays", "gold"), 41: ("sky", "royal"), 42: ("rays", "royal"),
         43: ("rays", "red"), 44: ("room", "pink"), 45: ("sky", "green"), 46: ("rays", "sky"), 47: ("rays", "royal"), 48: ("water", "sky"),
         49: ("sky", "royal"), 50: ("water", "royal"), 51: ("water", "sky"), 52: ("room", "red"), 53: ("room", "sky"), 54: ("water", "green")}


def cards():
    js = "const C=require(%r);console.log(JSON.stringify(C.CARDS.map(c=>({id:c.id,name:c.name,svg:c.svg}))))" % str(HERE / "static" / "loteria_cards.js")
    return json.loads(subprocess.check_output(["node", "-e", js]))


def recolor(s: str, n: int = 0) -> str:
    m = dict(REMAP, **(GOLD_REMAP if n in GOLD else {}))
    return re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", lambda x: m.get(x.group(0).lower(), x.group(0)), s)


def yellowish(hx: str) -> bool:
    hx = hx.lstrip("#")
    if len(hx) == 3: hx = "".join(c * 2 for c in hx)
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 40 / 360 <= h <= 70 / 360 and s > 0.45 and 0.3 < l < 0.92


def scene(kind: str, bg: str, n: int) -> str:
    lite, dark = BG[bg]
    fx, fy, fw, fh = 11, 11, W - 22, 243   # the painted field (the banner is below it)
    out = [f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#{"rg" if kind == "rays" else "bg"}{n})"/>']
    if kind == "rays":   # the old sunburst
        rays = "".join(f'<path d="M100 120L{100 + 260 * __import__("math").cos(a / 18 * 3.14159):.1f} {120 + 260 * __import__("math").sin(a / 18 * 3.14159):.1f}L{100 + 260 * __import__("math").cos((a + .5) / 18 * 3.14159):.1f} {120 + 260 * __import__("math").sin((a + .5) / 18 * 3.14159):.1f}z"/>' for a in range(0, 36))
        out.append(f'<g fill="{dark}" opacity=".32">{rays}</g>')
    elif kind in ("sky", "rain", "street"):
        out.append(f'<path d="M{fx} 196 C60 186 120 204 {fx + fw} 192 V{fy + fh} H{fx}z" fill="{"#4caf45" if kind == "sky" else "#e0ad78"}"/>')
        out.append(f'<path d="M{fx} 206 C70 198 130 214 {fx + fw} 204" fill="none" stroke="#161616" stroke-opacity=".3" stroke-width="1.4"/>')
        out.append('<g fill="#ffffff" opacity=".8"><ellipse cx="46" cy="44" rx="22" ry="7"/><ellipse cx="62" cy="40" rx="14" ry="8"/><ellipse cx="152" cy="62" rx="20" ry="6"/><ellipse cx="140" cy="58" rx="11" ry="7"/></g>')
        if kind == "rain":
            out.append('<g stroke="#ffffff" stroke-opacity=".75" stroke-width="1.6" stroke-linecap="round">' + "".join(f'<path d="M{20 + (i * 37) % 170} {30 + (i * 53) % 150}l-4 10"/>' for i in range(22)) + "</g>")
        if kind == "street":
            out.append('<g fill="#161616" opacity=".14">' + "".join(f'<rect x="{fx + i * 22}" y="212" width="20" height="6" rx="1"/>' for i in range(9)) + "</g>")
    elif kind == "water":
        out.append(f'<path d="M{fx} 176 Q40 168 70 176 T130 176 T{fx + fw + 10} 176 V{fy + fh} H{fx}z" fill="#1f73c9"/>')
        for k, y in enumerate((192, 210, 228)):
            out.append(f'<path d="M{fx} {y} Q30 {y - 6} 50 {y} T90 {y} T130 {y} T170 {y} T{fx + fw + 20} {y}" fill="none" stroke="#ffffff" stroke-opacity="{.8 - k * .15:.2f}" stroke-width="2"/>')
        out.append('<g fill="#ffffff" opacity=".8"><ellipse cx="150" cy="42" rx="20" ry="6"/><ellipse cx="40" cy="60" rx="16" ry="5"/></g>')
    elif kind == "desert":
        out.append('<circle cx="152" cy="52" r="20" fill="#ffffff" opacity=".7"/>')
        out.append(f'<path d="M{fx} 186 Q60 170 110 184 T{fx + fw} 178 V{fy + fh} H{fx}z" fill="#e89a52"/>')
        out.append(f'<path d="M{fx} 206 Q70 194 130 208 T{fx + fw} 200 V{fy + fh} H{fx}z" fill="#b8642c"/>')
    elif kind == "night":
        out.append('<g fill="#ffffff">' + "".join(f'<circle cx="{18 + (i * 41) % 166}" cy="{20 + (i * 67) % 215}" r="{.8 + (i % 3) * .5}" opacity="{.45 + (i % 4) * .12:.2f}"/>' for i in range(34)) + "</g>")
        out.append(f'<path d="M{fx} 214 Q100 202 {fx + fw} 214 V{fy + fh} H{fx}z" fill="#0e1d4d" opacity=".75"/>')
    elif kind == "room":   # a painted wall with a little pattern, and a tiled floor
        out.append(f'<g fill="{dark}" opacity=".16">' + "".join(f'<path d="M{24 + (i % 6) * 30} {26 + (i // 6) * 34}l5 6-5 6-5-6z"/>' for i in range(30)) + "</g>")
        out.append(f'<rect x="{fx}" y="196" width="{fw}" height="{fy + fh - 196}" fill="#c4552f"/>')
        out.append('<g stroke="#161616" stroke-opacity=".3" stroke-width="1.2">' + "".join(f'<path d="M{fx + i * 24} 196 L{fx - 20 + i * 30} {fy + fh}"/>' for i in range(9)) + f'<path d="M{fx} 214H{fx + fw}M{fx} 234H{fx + fw}"/></g>')
        out.append(f'<path d="M{fx} 196H{fx + fw}" stroke="#161616" stroke-width="2"/>')
    return "".join(out)


# v49.5: the classic-deck look: flat solid backgrounds in the old lotería print colors (card art, not app UI), a cream
# border, a small number top-left, the NAME in caps at the bottom, bold black outlines, no gradients / halftone / grain.
CLASSIC = {"sky": "#8fcbee", "pink": "#f6c3d0", "cream": "#f6ead2", "mint": "#bfe7cf", "yellow": "#f8e7a4", "tan": "#e3c99c"}
CREAM = "#f7f0de"


def classic_bg(n: int) -> str:
    kind, bg = SCENE[n]
    if bg in ("sky", "royal", "night"): return "sky"
    if bg in ("pink", "red"): return "pink"
    if bg == "green": return "mint"
    if bg == "gold": return "yellow"
    return "cream" if kind == "room" else "tan"   # orange


def card_svg(c: dict) -> str:
    n = c["id"]
    inner = re.sub(r"^<svg[^>]*>|</svg>$", "", recolor(c["svg"], n).strip())
    if n == 2:   # El Diablito's trident in gold (the classic decks' gold), outlined in black like the rest of the print
        inner = re.sub(r'<path d="([^"]+)" fill="none" stroke="#6f7983"/>',
                       r'<path d="\1" fill="none" stroke="#161616" stroke-width="8"/><path d="\1" fill="none" stroke="#f2b705" stroke-width="4.6"/>', inner)
    name = c["name"].upper()
    fs = 22 if len(name) <= 10 else 19 if len(name) <= 13 else 17
    bg = CLASSIC[classic_bg(n)]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{CREAM}" stroke="#b9ae93" stroke-width="1"/>
<clipPath id="field{n}"><rect x="9" y="9" width="{W - 18}" height="{H - 18}" rx="3"/></clipPath>
<g clip-path="url(#field{n})">
  <rect x="9" y="9" width="{W - 18}" height="{H - 18}" fill="{bg}"/>
  <g class="fig" transform="translate(14 40) scale(1.72)"><g class="figin" stroke-linejoin="round">{inner}</g></g>
</g>
<rect x="9" y="9" width="{W - 18}" height="{H - 18}" rx="3" fill="none" stroke="#161616" stroke-width="2"/>
<text x="17" y="29" font-family="Oswald" font-weight="600" font-size="15" fill="#161616">{n}</text>
<text x="100" y="281" text-anchor="middle" font-family="Oswald" font-weight="700" font-size="{fs}" letter-spacing="1" fill="#161616" textLength="{min(170, 10 + len(name) * fs * .52):.0f}" lengthAdjust="spacingAndGlyphs">{name}</text>
</svg>"""


def card_svg_v43(c: dict) -> str:
    n, (kind, bg) = c["id"], SCENE[c["id"]]
    lite, dark = BG[bg]
    inner = re.sub(r"^<svg[^>]*>|</svg>$", "", recolor(c["svg"], n).strip())
    name = c["name"].upper()
    fs = 25 if len(name) <= 10 else 22 if len(name) <= 12 else 19
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <linearGradient id="bg{n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{dark}"/><stop offset=".78" stop-color="{lite}"/></linearGradient>
  <radialGradient id="rg{n}" cx="50%" cy="42%" r="72%"><stop offset="0" stop-color="{lite}"/><stop offset=".45" stop-color="{lite}"/><stop offset="1" stop-color="{dark}"/></radialGradient>
  <pattern id="dots{n}" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="1.5" cy="1.5" r=".55" fill="#161616"/></pattern>
  <filter id="brush{n}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".012 .09" numOctaves="3" seed="{n * 7}"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 .96  0 0 0 0 .9  0 0 0 .55 -.18"/></filter>
  <filter id="grain{n}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="{n}"/>
    <feColorMatrix values="0 0 0 0 .12  0 0 0 0 .08  0 0 0 0 .05  0 0 0 -.9 .62"/></filter>
  <filter id="paint{n}" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="3.2" result="b"/>
    <feDiffuseLighting in="b" surfaceScale="2" diffuseConstant="1.6" lighting-color="#fff" result="d"><feDistantLight azimuth="235" elevation="50"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="di"/>
    <feBlend in="SourceGraphic" in2="di" mode="multiply" result="sh"/>
    <feSpecularLighting in="b" surfaceScale="4" specularConstant=".22" specularExponent="10" lighting-color="#fff6ea" result="s"><feDistantLight azimuth="235" elevation="50"/></feSpecularLighting>
    <feComposite in="s" in2="SourceAlpha" operator="in" result="si"/>
    <feComposite in="sh" in2="si" operator="arithmetic" k2="1" k3=".25" result="lit"/>
    <feTurbulence type="fractalNoise" baseFrequency=".7" numOctaves="2" seed="{n + 3}" result="nz"/>
    <feColorMatrix in="nz" values="0 0 0 0 .1  0 0 0 0 .07  0 0 0 0 .05  0 0 0 -.5 .28" result="g"/>
    <feComposite in="g" in2="SourceAlpha" operator="in" result="gi"/>
    <feMerge><feMergeNode in="lit"/><feMergeNode in="gi"/></feMerge>
  </filter>
  <filter id="shadow{n}" x="-10%" y="-10%" width="130%" height="130%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="3" dy="4"/><feComponentTransfer><feFuncA type="linear" slope=".3"/></feComponentTransfer></filter>
  <clipPath id="field{n}"><rect x="11" y="11" width="{W - 22}" height="245" rx="4"/></clipPath>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="11" fill="#ffffff" stroke="#c9c9c9" stroke-width="1"/>
<g clip-path="url(#field{n})">
  {scene(kind, bg, n)}
  <rect x="11" y="11" width="{W - 22}" height="245" filter="url(#brush{n})" opacity=".12"/>
  <rect x="11" y="11" width="{W - 22}" height="245" fill="url(#dots{n})" opacity=".05"/>
  <g class="fig" transform="translate(14 40) scale(1.72)"><g filter="url(#shadow{n})">{inner}</g></g>
  <g class="fig" transform="translate(14 40) scale(1.72)"><g filter="url(#paint{n})"><g class="figin">{inner}</g></g></g>
</g>
<rect x="11" y="11" width="{W - 22}" height="245" rx="4" fill="none" stroke="#161616" stroke-width="1.6"/>
<text x="18" y="33" font-family="Alfa Slab One" font-size="18" fill="#161616" stroke="#ffffff" stroke-width="4" stroke-linejoin="round" paint-order="stroke">{n}</text>
<text x="100" y="{283 if fs >= 22 else 282}" text-anchor="middle" font-family="Oswald" font-weight="700" font-size="{fs}" letter-spacing=".6" fill="#161616" textLength="{min(172, 12 + len(name) * fs * .5):.0f}" lengthAdjust="spacingAndGlyphs">{name}</text>
<rect x="11" y="11" width="{W - 22}" height="245" rx="4" filter="url(#grain{n})" opacity=".2" style="mix-blend-mode:multiply"/>
</svg>"""


async def render(cs: list, sheet: str | None):
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=PX / W)
        for c in cs:
            svg = card_svg(c)
            bad = [h for h in re.findall(r"#[0-9a-fA-F]{6}\b", svg) if yellowish(h) and h.lower() not in {v.lower() for v in (*CLASSIC.values(), CREAM)}]
            if bad and c["id"] not in GOLD:   # golden yellow only where the classic decks have it
                raise SystemExit(f"card {c['id']}: yellow colors {bad}")
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await pg.evaluate("document.fonts.ready")
            # fit the figure to the painted field (each drawing uses its 100×100 box differently)
            await pg.evaluate("""() => { const g = document.querySelector('.figin'), b = g.getBBox();
              const s = Math.min(164 / b.width, 214 / b.height, 2.45), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
              const tx = 100 - cx * s, ty = Math.min(148 - cy * s, 258 - (b.y + b.height) * s);
              document.querySelectorAll('.fig').forEach(f => f.setAttribute('transform', `translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${s.toFixed(3)})`)); }""")
            png = OUT / f"{c['id']:02d}.png"
            await pg.locator("svg").first.screenshot(path=str(png), omit_background=True)
            im = Image.open(png).convert("RGBA")
            im.save(OUT / f"{c['id']:02d}.webp", "WEBP", quality=80, method=6)
            png.unlink()
        await b.close()
    total = sum((OUT / f"{c['id']:02d}.webp").stat().st_size for c in cs)
    print(f"{len(cs)} cards → {OUT} ({total // 1024} KB)")
    if sheet:
        ims = [Image.open(OUT / f"{c['id']:02d}.webp") for c in cs]
        w, h = ims[0].size; cols = 6; rows = (len(ims) + cols - 1) // cols
        S = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 10) + 10), (247, 232, 223))
        for i, im in enumerate(ims):
            S.paste(im, (10 + (i % cols) * (w + 10), 10 + (i // cols) * (h + 10)), im)
        S.save(sheet)


if __name__ == "__main__":
    only = [int(a) for a in sys.argv[1:] if a.isdigit()]
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    cs = [c for c in cards() if not only or c["id"] in only]
    asyncio.run(render(cs, sheet))
