"""v49.14: the share image (Open Graph / Twitter card) for the website: static/site/og-image.png, 1200×630.
Fiesta palette (turquoise ground, black type, pink + orange accents), the app icon and Tía. No yellow.
Run: ./venv/bin/python tools/make_site_art.py   (needs Pillow and the DejaVu fonts; the PNG is committed)"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "site" / "og-image.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TURQ, PINK, ORANGE, BLACK = (0, 201, 205), (255, 26, 127), (255, 106, 11), (0, 0, 0)   # the app icon's colours
W, H = 1200, 630


def main():
    im = Image.new("RGB", (W, H), TURQ)
    d = ImageDraw.Draw(im)
    # papel picado strip at the bottom: pink / orange / black flags with zig-zag edges
    y0 = H - 46
    for i, x in enumerate(range(0, W, 60)):
        col = (PINK, ORANGE, BLACK)[i % 3]
        d.rectangle([x, y0, x + 60, H], fill=col)
        for k in range(0, 60, 20):
            d.polygon([(x + k, y0), (x + k + 10, y0 + 12), (x + k + 20, y0)], fill=TURQ)
    # the app icon with Tía over its corner
    icon = Image.open(ROOT / "static" / "icons" / "icon-512.png").convert("RGBA").resize((330, 330), Image.LANCZOS)
    mask = Image.new("L", icon.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 329, 329], radius=70, fill=255)
    d.rounded_rectangle([62, 102, 62 + 342, 102 + 342], radius=76, fill=BLACK)
    im.paste(icon, (68, 108), mask)
    tia = Image.open(ROOT / "static" / "mascot" / "avatar-192.webp").convert("RGBA").resize((150, 150), Image.LANCZOS)
    tm = Image.new("L", tia.size, 0)
    ImageDraw.Draw(tm).ellipse([0, 0, 149, 149], fill=255)
    d.ellipse([300, 352, 300 + 162, 352 + 162], fill=PINK)
    im.paste(tia, (306, 358), tm)
    # the words
    big, mid, small = ImageFont.truetype(FONT, 120), ImageFont.truetype(FONT, 66), ImageFont.truetype(FONT, 32)
    x = 500
    d.text((x, 92), "Chisme", font=big, fill=BLACK)
    d.text((x, 262), "Did you hear?", font=mid, fill=BLACK)
    d.rounded_rectangle([x, 392, x + 640, 392 + 6], radius=3, fill=PINK)
    d.text((x, 420), "San Antonio news, sports, events,", font=small, fill=BLACK)
    d.text((x, 462), "weather, food and games. Free.", font=small, fill=BLACK)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, optimize=True)
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
