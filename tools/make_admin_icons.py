"""v49.5: the "Chisme Admin" Home Screen icons (static/icons/admin-*.png): the app icon with a black ADMIN band.
Usage: ./venv/bin/python tools/make_admin_icons.py   (needs Pillow; the font is DejaVu Sans Bold, or any bold TTF via ADMIN_ICON_FONT)"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent / "static" / "icons"
FONT = os.environ.get("ADMIN_ICON_FONT") or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
src = Image.open(ROOT / "icon-512.png").convert("RGBA")
for size, name in ((512, "admin-512.png"), (192, "admin-192.png"), (180, "admin-180.png")):
    im = src.resize((size, size), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    h = round(size * 0.24)
    d.rectangle([0, size - h, size, size], fill=(10, 10, 10, 255))                       # black band
    d.rectangle([0, size - h, size, size - h + max(2, size // 64)], fill=(239, 66, 111, 255))   # pink edge (Fiesta)
    f = ImageFont.truetype(FONT, round(h * 0.6))
    w = d.textlength("ADMIN", font=f)
    d.text(((size - w) / 2, size - h / 2), "ADMIN", font=f, fill=(0, 201, 205, 255), anchor="lm")   # turquoise
    im.convert("RGB").save(ROOT / name, optimize=True)
    print("wrote", ROOT / name)
