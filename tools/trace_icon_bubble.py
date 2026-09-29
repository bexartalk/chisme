"""Vector-traces the speech bubble, the 'Chisme' lettering and the confetti inside the bubble from the
app icon artwork (assets/chisme-icon-original.png), so the header bubble is the icon's own shape.
Writes tools/icon_bubble.json (used by make_header_art.py). Dev-only deps: numpy, scipy, pillow, potracer.
    ./venv/bin/python tools/trace_icon_bubble.py
"""
import json, pathlib
import numpy as np
import potrace
from PIL import Image
from scipy import ndimage as ndi

ROOT = pathlib.Path(__file__).resolve().parent.parent
PALETTE = {"cp": (230, 29, 120), "co": (226, 102, 11), "ct": (8, 193, 196)}


def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def trace(mask, turdsize=8, alphamax=1.0, opttolerance=0.2):
    """Boolean mask -> SVG path data (potrace curves, even-odd holes)."""
    bm = potrace.Bitmap(~mask)  # potracer traces the "dark" (False) pixels
    d = []
    for curve in bm.trace(turdsize=turdsize, alphamax=alphamax, opticurve=True, opttolerance=opttolerance):
        p = curve.start_point; d.append(f"M{fmt(p.x)} {fmt(p.y)}")
        for s in curve.segments:
            if s.is_corner:
                d.append(f"L{fmt(s.c.x)} {fmt(s.c.y)}L{fmt(s.end_point.x)} {fmt(s.end_point.y)}")
            else:
                d.append(f"C{fmt(s.c1.x)} {fmt(s.c1.y)} {fmt(s.c2.x)} {fmt(s.c2.y)} {fmt(s.end_point.x)} {fmt(s.end_point.y)}")
        d.append("Z")
    return "".join(d)


def main():
    im = np.asarray(Image.open(ROOT / "assets" / "chisme-icon-original.png").convert("RGB")).astype(int)
    mx, mn = im.max(-1), im.min(-1)
    black = mx < 80
    lab, n = ndi.label(black)
    big = lab == (np.argmax(ndi.sum(black, lab, range(1, n + 1))) + 1)
    sil = ndi.binary_fill_holes(big)                        # bubble + tail, with the lettering/confetti holes filled
    sil = ndi.binary_opening(sil, iterations=1)
    ys, xs = np.nonzero(sil)
    box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    white = (mn > 150) & ndi.binary_erosion(sil, iterations=2)
    lab, n = ndi.label(white)
    sizes = ndi.sum(white, lab, range(1, n + 1))
    letters = np.isin(lab, [i + 1 for i in np.nonzero(sizes > 500)[0]])
    wy, wx = np.nonzero(letters)
    colour = ndi.binary_erosion(sil, iterations=2) & ~black & ~(mn > 150)
    lab, n = ndi.label(colour)
    conf = {k: np.zeros_like(sil) for k in PALETTE}
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() < 300:
            continue
        c = im[m].mean(0)
        k = min(PALETTE, key=lambda k: sum((a - b) ** 2 for a, b in zip(c, PALETTE[k])))
        conf[k] |= ndi.binary_closing(m, iterations=2)
    out = {"source": "assets/chisme-icon-original.png", "size": list(im.shape[1::-1]), "bubble_box": box,
           "text_box": [int(wx.min()), int(wy.min()), int(wx.max()) + 1, int(wy.max()) + 1],
           "bubble": trace(sil, turdsize=50, alphamax=1.2, opttolerance=0.4),
           "letters": trace(letters, turdsize=20, alphamax=1.0, opttolerance=0.2),
           "confetti": {k: trace(v, turdsize=40, alphamax=0.6) for k, v in conf.items() if v.any()}}
    (ROOT / "tools" / "icon_bubble.json").write_text(json.dumps(out, indent=1))
    print("bubble box", box, "text box", out["text_box"], {k: len(v) for k, v in out.items() if isinstance(v, str)})


if __name__ == "__main__":
    main()
