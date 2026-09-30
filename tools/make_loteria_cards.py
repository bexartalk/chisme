"""v43: renders the 54 Lotería Chismosa cards as vintage lithograph-style images (static/loteria/cards/01.webp … 54.webp).

Our OWN art (nothing copied or traced from a published deck): the original drawings from static/loteria_cards.js, re-inked
and re-colored in an old painted-print style: a painted scene behind each one (sky, water, desert, night, sunburst or a
room), brush texture, halftone dots and paper grain, soft painted shading on the figure, bold outlines, the number in the
corner and the Spanish name on a banner at the bottom. Warm vintage colors: turquoise, pink, orange, cream, blue, red and
green (never yellow). Rendered once with Chrome (Playwright) so the phone just shows pictures.
Usage: ./venv/bin/python tools/make_loteria_cards.py [--sheet screenshots/x.png]"""
import asyncio, colorsys, json, re, subprocess, sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "static" / "loteria" / "cards"
W, H = 200, 300          # card units (2:3)
PX = 300                 # output width in pixels (≈ 3× the card's size on an iPhone tabla)

# the drawings' bright Fiesta colors → warm, a little faded, like an old print (no yellow)
REMAP = {"#111": "#1d1612", "#fff": "#fbf3e6", "#00b8b0": "#239a93", "#3ee8eb": "#72c9c0", "#ff3d8b": "#d8506f", "#c2185b": "#9b2d4a",
         "#ff8a00": "#df7a2c", "#c95f00": "#a4531f", "#b9c0c7": "#b9b2a6", "#7c858f": "#6e695f", "#2f9e57": "#3d8a4c", "#6cc26a": "#79a95e",
         "#e0243a": "#c5392f", "#1d2a4d": "#23345b", "#f2efed": "#f0e4d3", "#8a5a3b": "#875a3a", "#5e3a22": "#5a3a24", "#c8643b": "#c0633b"}
# backgrounds: turquoise, pink, orange, cream, blue, red, green
BG = {"turq": ("#6fc3bd", "#2e8f8a"), "pink": ("#f0a3b4", "#c95a78"), "orange": ("#f2a766", "#c8652a"), "cream": ("#f4e6d4", "#d7b99a"),
      "blue": ("#8fb8d9", "#3c6f9e"), "red": ("#e0806f", "#a8392e"), "green": ("#9cc58e", "#4f8a4a"), "night": ("#3b5584", "#18233f")}
# per card: (scene, background)
SCENE = {1: ("rays", "orange"), 2: ("rays", "red"), 3: ("room", "pink"), 4: ("street", "blue"), 5: ("rain", "blue"), 6: ("water", "turq"),
         7: ("sky", "blue"), 8: ("room", "green"), 9: ("room", "orange"), 10: ("sky", "turq"), 11: ("room", "pink"), 12: ("desert", "orange"),
         13: ("room", "turq"), 14: ("night", "night"), 15: ("room", "blue"), 16: ("sky", "blue"), 17: ("room", "red"), 18: ("room", "cream"),
         19: ("water", "blue"), 20: ("sky", "pink"), 21: ("rays", "turq"), 22: ("room", "cream"), 23: ("night", "night"), 24: ("sky", "turq"),
         25: ("street", "pink"), 26: ("room", "orange"), 27: ("rays", "pink"), 28: ("room", "green"), 29: ("room", "blue"), 30: ("water", "turq"),
         31: ("rays", "cream"), 32: ("street", "green"), 33: ("night", "night"), 34: ("street", "cream"), 35: ("night", "night"), 36: ("room", "turq"),
         37: ("night", "night"), 38: ("desert", "orange"), 39: ("desert", "orange"), 40: ("desert", "cream"), 41: ("sky", "green"), 42: ("night", "night"),
         43: ("rays", "blue"), 44: ("room", "pink"), 45: ("sky", "green"), 46: ("rays", "blue"), 47: ("rays", "red"), 48: ("water", "blue"),
         49: ("sky", "blue"), 50: ("water", "turq"), 51: ("water", "orange"), 52: ("room", "red"), 53: ("room", "green"), 54: ("water", "green")}


def cards():
    js = "const C=require(%r);console.log(JSON.stringify(C.CARDS.map(c=>({id:c.id,name:c.name,svg:c.svg}))))" % str(HERE / "static" / "loteria_cards.js")
    return json.loads(subprocess.check_output(["node", "-e", js]))


def recolor(s: str) -> str:
    return re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", lambda m: REMAP.get(m.group(0).lower(), m.group(0)), s)


def yellowish(hx: str) -> bool:
    hx = hx.lstrip("#")
    if len(hx) == 3: hx = "".join(c * 2 for c in hx)
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 40 / 360 <= h <= 70 / 360 and s > 0.45 and 0.3 < l < 0.92


def scene(kind: str, bg: str, n: int) -> str:
    lite, dark = BG[bg]
    fx, fy, fw, fh = 11, 11, W - 22, 243   # the painted field (the banner is below it)
    out = [f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#bg{n})"/>']
    if kind == "rays":   # the old sunburst
        rays = "".join(f'<path d="M100 120L{100 + 260 * __import__("math").cos(a / 18 * 3.14159):.1f} {120 + 260 * __import__("math").sin(a / 18 * 3.14159):.1f}L{100 + 260 * __import__("math").cos((a + .5) / 18 * 3.14159):.1f} {120 + 260 * __import__("math").sin((a + .5) / 18 * 3.14159):.1f}z"/>' for a in range(0, 36))
        out.append(f'<g fill="{dark}" opacity=".28">{rays}</g>')
    elif kind in ("sky", "rain", "street"):
        out.append(f'<path d="M{fx} 196 C60 186 120 204 {fx + fw} 192 V{fy + fh} H{fx}z" fill="{"#7d9b57" if kind == "sky" else "#b7916a"}" opacity=".9"/>')
        out.append(f'<path d="M{fx} 206 C70 198 130 214 {fx + fw} 204" fill="none" stroke="#1d1612" stroke-opacity=".25" stroke-width="1.4"/>')
        out.append('<g fill="#fbf3e6" opacity=".55"><ellipse cx="46" cy="44" rx="22" ry="7"/><ellipse cx="62" cy="40" rx="14" ry="8"/><ellipse cx="152" cy="62" rx="20" ry="6"/><ellipse cx="140" cy="58" rx="11" ry="7"/></g>')
        if kind == "rain":
            out.append('<g stroke="#fbf3e6" stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round">' + "".join(f'<path d="M{20 + (i * 37) % 170} {30 + (i * 53) % 150}l-4 10"/>' for i in range(22)) + "</g>")
        if kind == "street":
            out.append('<g fill="#1d1612" opacity=".12">' + "".join(f'<rect x="{fx + i * 22}" y="212" width="20" height="6" rx="1"/>' for i in range(9)) + "</g>")
    elif kind == "water":
        out.append(f'<path d="M{fx} 176 Q40 168 70 176 T130 176 T{fx + fw + 10} 176 V{fy + fh} H{fx}z" fill="#2f7fa3" opacity=".85"/>')
        for k, y in enumerate((192, 210, 228)):
            out.append(f'<path d="M{fx} {y} Q30 {y - 6} 50 {y} T90 {y} T130 {y} T170 {y} T{fx + fw + 20} {y}" fill="none" stroke="#fbf3e6" stroke-opacity="{.5 - k * .12:.2f}" stroke-width="2"/>')
        out.append('<g fill="#fbf3e6" opacity=".5"><ellipse cx="150" cy="42" rx="20" ry="6"/><ellipse cx="40" cy="60" rx="16" ry="5"/></g>')
    elif kind == "desert":
        out.append('<circle cx="152" cy="52" r="20" fill="#f6d2b8" opacity=".75"/>')
        out.append(f'<path d="M{fx} 186 Q60 170 110 184 T{fx + fw} 178 V{fy + fh} H{fx}z" fill="#c98a55"/>')
        out.append(f'<path d="M{fx} 206 Q70 194 130 208 T{fx + fw} 200 V{fy + fh} H{fx}z" fill="#a8683a" opacity=".85"/>')
    elif kind == "night":
        out.append('<g fill="#fbf3e6">' + "".join(f'<circle cx="{18 + (i * 41) % 166}" cy="{20 + (i * 67) % 215}" r="{.8 + (i % 3) * .5}" opacity="{.45 + (i % 4) * .12:.2f}"/>' for i in range(34)) + "</g>")
        out.append(f'<path d="M{fx} 214 Q100 202 {fx + fw} 214 V{fy + fh} H{fx}z" fill="#101a30" opacity=".7"/>')
    elif kind == "room":   # a painted wall with a little pattern, and a tiled floor
        out.append(f'<g fill="{dark}" opacity=".16">' + "".join(f'<path d="M{24 + (i % 6) * 30} {26 + (i // 6) * 34}l5 6-5 6-5-6z"/>' for i in range(30)) + "</g>")
        out.append(f'<rect x="{fx}" y="196" width="{fw}" height="{fy + fh - 196}" fill="#b9714a"/>')
        out.append('<g stroke="#1d1612" stroke-opacity=".28" stroke-width="1.2">' + "".join(f'<path d="M{fx + i * 24} 196 L{fx - 20 + i * 30} {fy + fh}"/>' for i in range(9)) + f'<path d="M{fx} 214H{fx + fw}M{fx} 234H{fx + fw}"/></g>')
        out.append(f'<path d="M{fx} 196H{fx + fw}" stroke="#1d1612" stroke-width="2"/>')
    return "".join(out)


def card_svg(c: dict) -> str:
    n, (kind, bg) = c["id"], SCENE[c["id"]]
    lite, dark = BG[bg]
    inner = re.sub(r"^<svg[^>]*>|</svg>$", "", recolor(c["svg"]).strip())
    name = c["name"].upper()
    fs = 25 if len(name) <= 10 else 22 if len(name) <= 12 else 19
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <radialGradient id="bg{n}" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="{lite}"/><stop offset=".62" stop-color="{lite}"/><stop offset="1" stop-color="{dark}"/></radialGradient>
  <pattern id="dots{n}" width="3.2" height="3.2" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="1.6" cy="1.6" r=".62" fill="#1d1612"/></pattern>
  <filter id="brush{n}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".012 .09" numOctaves="3" seed="{n * 7}"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 .96  0 0 0 0 .9  0 0 0 .55 -.18"/></filter>
  <filter id="grain{n}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="{n}"/>
    <feColorMatrix values="0 0 0 0 .12  0 0 0 0 .08  0 0 0 0 .05  0 0 0 -.9 .62"/></filter>
  <filter id="paint{n}" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="3.2" result="b"/>
    <feDiffuseLighting in="b" surfaceScale="2.2" diffuseConstant="1.2" lighting-color="#fff" result="d"><feDistantLight azimuth="235" elevation="50"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="di"/>
    <feBlend in="SourceGraphic" in2="di" mode="multiply" result="sh"/>
    <feSpecularLighting in="b" surfaceScale="4" specularConstant=".22" specularExponent="10" lighting-color="#fff6ea" result="s"><feDistantLight azimuth="235" elevation="50"/></feSpecularLighting>
    <feComposite in="s" in2="SourceAlpha" operator="in" result="si"/>
    <feComposite in="sh" in2="si" operator="arithmetic" k2="1" k3=".4" result="lit"/>
    <feTurbulence type="fractalNoise" baseFrequency=".7" numOctaves="2" seed="{n + 3}" result="nz"/>
    <feColorMatrix in="nz" values="0 0 0 0 .1  0 0 0 0 .07  0 0 0 0 .05  0 0 0 -.8 .5" result="g"/>
    <feComposite in="g" in2="SourceAlpha" operator="in" result="gi"/>
    <feMerge><feMergeNode in="lit"/><feMergeNode in="gi"/></feMerge>
  </filter>
  <filter id="shadow{n}" x="-10%" y="-10%" width="130%" height="130%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="3" dy="4"/><feComponentTransfer><feFuncA type="linear" slope=".35"/></feComponentTransfer></filter>
  <clipPath id="field{n}"><rect x="11" y="11" width="{W - 22}" height="243" rx="3"/></clipPath>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="#f6ead8" stroke="#1d1612" stroke-width="2"/>
<g clip-path="url(#field{n})">
  {scene(kind, bg, n)}
  <rect x="11" y="11" width="{W - 22}" height="243" filter="url(#brush{n})" opacity=".5"/>
  <rect x="11" y="11" width="{W - 22}" height="243" fill="url(#dots{n})" opacity=".09"/>
  <g class="fig" transform="translate(14 40) scale(1.72)"><g filter="url(#shadow{n})">{inner}</g></g>
  <g class="fig" transform="translate(14 40) scale(1.72)"><g filter="url(#paint{n})"><g class="figin">{inner}</g></g></g>
</g>
<rect x="11" y="11" width="{W - 22}" height="243" rx="3" fill="none" stroke="#1d1612" stroke-width="3"/>
<rect x="15" y="15" width="34" height="27" rx="4" fill="#f6ead8" stroke="#1d1612" stroke-width="2"/>
<text x="32" y="35.5" text-anchor="middle" font-family="Alfa Slab One" font-size="17" fill="#1d1612">{n}</text>
<rect x="11" y="258" width="{W - 22}" height="31" rx="3" fill="#f6ead8" stroke="#1d1612" stroke-width="2.4"/>
<text x="100" y="{282 if fs >= 22 else 281}" text-anchor="middle" font-family="Oswald" font-weight="700" font-size="{fs}" letter-spacing=".6" fill="#1d1612" textLength="{min(172, 12 + len(name) * fs * .5):.0f}" lengthAdjust="spacingAndGlyphs">{name}</text>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" filter="url(#grain{n})" opacity=".55" style="mix-blend-mode:multiply"/>
</svg>"""


async def render(cs: list, sheet: str | None):
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=PX / W)
        for c in cs:
            svg = card_svg(c)
            bad = [h for h in re.findall(r"#[0-9a-fA-F]{6}\b", svg) if yellowish(h)]
            if bad:
                raise SystemExit(f"card {c['id']}: yellow colors {bad}")
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await pg.evaluate("document.fonts.ready")
            # fit the figure to the painted field (each drawing uses its 100×100 box differently)
            await pg.evaluate("""() => { const g = document.querySelector('.figin'), b = g.getBBox();
              const s = Math.min(160 / b.width, 196 / b.height, 2.35), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
              const tx = 100 - cx * s, ty = Math.min(146 - cy * s, 246 - (b.y + b.height) * s);
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
        S = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 10) + 10), (246, 234, 216))
        for i, im in enumerate(ims):
            S.paste(im, (10 + (i % cols) * (w + 10), 10 + (i // cols) * (h + 10)), im)
        S.save(sheet)


if __name__ == "__main__":
    only = [int(a) for a in sys.argv[1:] if a.isdigit()]
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    cs = [c for c in cards() if not only or c["id"] in only]
    asyncio.run(render(cs, sheet))
