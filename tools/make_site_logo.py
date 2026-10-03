"""v49.14 desktop site: the 'Chisme' bubble logo, cut from the app icon itself.

Uses the icon's own vector trace (tools/icon_bubble.json, made from assets/chisme-icon-original.png by
tools/trace_icon_bubble.py): the black speech bubble with its tail, the white hand-drawn 'Chisme' lettering and the
pink / orange / turquoise confetti inside it, on a transparent background. Vector, so it's sharp at any width.
    ./venv/bin/python tools/make_site_logo.py      → static/site/chisme-bubble-logo.svg
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICON = json.loads((ROOT / "tools" / "icon_bubble.json").read_text())
COLOURS = {"cp": "#FF1A7F", "co": "#FF6A0B", "ct": "#00C9CD"}   # sampled from static/icons/icon-512.png
OUT = ROOT / "static" / "site" / "chisme-bubble-logo.svg"


def main():
    x0, y0, x1, y1 = ICON["bubble_box"]
    m = 2
    conf = "".join(f'<path fill="{COLOURS[k]}" d="{d}"/>' for k, d in ICON["confetti"].items() if k in COLOURS)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0 - m} {y0 - m} {x1 - x0 + 2 * m} {y1 - y0 + 2 * m}" '
           f'width="{x1 - x0 + 2 * m}" height="{y1 - y0 + 2 * m}" role="img" aria-label="Chisme">'
           f'<title>Chisme</title><path fill="#000" d="{ICON["bubble"]}"/>{conf}'
           f'<path fill="#fff" fill-rule="evenodd" d="{ICON["letters"]}"/></svg>\n')
    OUT.write_text(svg)
    print("wrote", OUT, len(svg), "bytes", (x1 - x0 + 2 * m, y1 - y0 + 2 * m))


if __name__ == "__main__":
    main()
