"""Build Chisme's icon set from the chosen artwork (assets/chisme-icon-original.png, 720x720:
turquoise rounded square, black 'Chisme' speech bubble, pink/orange confetti).
The source has white outside the rounded corners. We flood-fill that white (plus the
anti-aliased edge band) from the image border with the icon's own turquoise, sampled
from the artwork, so exported icons are turquoise edge-to-edge with no white rim.
Usage: ./venv/bin/python tools/make_icons.py"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "chisme-icon-original.png"
OUT = ROOT / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

a = np.asarray(Image.open(SRC).convert("RGB")).astype(np.int16)
H, W, _ = a.shape
R, G, B = a[..., 0], a[..., 1], a[..., 2]

# 1) sample the turquoise: pixels with ~no red and high green/blue
tq_px = a[(R < 20) & (G > 170) & (B > 170)]
TURQ = np.median(tq_px, axis=0).astype(np.int16)
print("sampled turquoise:", "#%02X%02X%02X" % tuple(int(v) for v in TURQ))

# 2) white / light-cyan region connected to the image border = outside the rounded square
light = (R > 20) & (G > 150) & (B > 150)
lab, _ = ndimage.label(light)
border_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
outside = np.isin(lab, list(border_labels))
# 3) grow a few px into the turquoise to swallow the darker anti-aliased rim,
#    but only over turquoise-ish pixels so confetti/bubble are never touched
turq_like = (R < 90) & (G > 150) & (B > 150)
grown = outside | (ndimage.binary_dilation(outside, iterations=4) & turq_like)
a[grown] = TURQ
flat = Image.fromarray(a.astype(np.uint8), "RGB")
C = W // 2

def crop(size_px):
    h = size_px // 2
    return flat.crop((C - h, C - h, C + h, C + h))

def save(img, px, name):
    img.resize((px, px), Image.LANCZOS).save(OUT / name, optimize=True)
    print("wrote", OUT / name)

# "any" icons, apple-touch-icon, favicons: full artwork, turquoise edge-to-edge
full = crop(W)
save(full, 192, "icon-192.png")
save(full, 512, "icon-512.png")
save(full, 180, "apple-touch-icon.png")
save(full, 96, "header-icon.png")
save(full, 32, "favicon-32.png")
full.resize((48, 48), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

# maskable: pad with turquoise so the whole speech bubble sits inside the
# 80%-diameter safe circle. Bubble reaches ~300px from center in the 720 source,
# so place it on a 720/0.78 ~ 925px canvas.
pad = int(W / 0.78)
canvas = Image.new("RGB", (pad, pad), tuple(int(v) for v in TURQ))
canvas.paste(flat, ((pad - W) // 2, (pad - W) // 2))
save(canvas, 512, "maskable-512.png")
save(canvas, 192, "maskable-192.png")
