"""Build the mascot's WebP images from ONE source picture, so swapping her art is a one-command job.

    ./venv/bin/python tools/make_mascot_assets.py path/to/new-art.png [--face CX,CY,SIZE]

- avatar-64/128/192.webp: a round crop on her face for the floating button (64px at 1x, 2x and 3x)
- header-480/960.webp: a wide banner for the top of the chat sheet
--face is the face box in source pixels (center x, center y, square size). By default the values in
static/mascot/mascot.json are used, else a centered upper-third guess. The chosen box is saved back there.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "mascot"
CFG = OUT / "mascot.json"


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    cfg = json.loads(CFG.read_text()) if CFG.exists() else {}
    im = Image.open(src).convert("RGB")
    W, H = im.size
    face = cfg.get("face")
    if "--face" in args:
        face = [int(v) for v in args[args.index("--face") + 1].split(",")]
    if not face:
        face = [W // 2, int(H * 0.35), int(min(W, H) * 0.55)]
    cx, cy, s = face
    s = min(s, W, H)
    x0 = max(0, min(W - s, cx - s // 2)); y0 = max(0, min(H - s, cy - s // 2))
    sq = im.crop((x0, y0, x0 + s, y0 + s))
    OUT.mkdir(parents=True, exist_ok=True)
    for px in (64, 128, 192):
        a = sq.resize((px, px), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", (px * 4, px * 4), 0)
        ImageDraw.Draw(m).ellipse((0, 0, px * 4 - 1, px * 4 - 1), fill=255)
        a.putalpha(m.resize((px, px), Image.LANCZOS))
        a.save(OUT / f"avatar-{px}.webp", "WEBP", quality=82, method=6)
    # header: 2:1 banner centered on the face column, keeping as much of the scene as fits
    hh = min(H, W // 2); hw = hh * 2
    hx = max(0, min(W - hw, cx - hw // 2)); hy = max(0, min(H - hh, cy - int(hh * 0.4)))
    ban = im.crop((hx, hy, hx + hw, hy + hh))
    for w in (480, 960):
        ban.resize((w, w // 2), Image.LANCZOS).save(OUT / f"header-{w}.webp", "WEBP", quality=78, method=6)
    cfg.update({"source": src.name, "face": [cx, cy, s]})
    cfg.setdefault("name", "Tía Chismosa")
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    for f in sorted(OUT.glob("*.webp")):
        print(f"{f.name}: {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
