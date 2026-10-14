#!/usr/bin/env python3
"""v49.23 one-step app icon switch (temporary Día de los Muertos icon → back to the Fiesta original on Nov 3).

    python3 tools/icon_theme.py muertos   # the Día de los Muertos icon (static/icons/muertos/) + night-purple manifest colors
    python3 tools/icon_theme.py fiesta    # REVERT: the original Fiesta icon (static/icons/fiesta-original/) + its manifest

Copies the set over static/icons/*.png|ico (same file names, so no HTML / manifest / sw.js paths change) and swaps
static/manifest.webmanifest. Then commit, bump the build (app.js BUILD + sw.js cache) and deploy so phones refetch.
The Día de los Muertos colors need no step: they live under html[data-season="muertos"] and turn off by themselves after
Nov 3 23:59 Chicago time (or right away with THEME_OVERRIDE=off)."""
import json, shutil, sys
from pathlib import Path

ICONS = Path(__file__).resolve().parent.parent / "static" / "icons"
FILES = ["apple-touch-icon.png", "favicon-32.png", "favicon.ico", "icon-192.png", "icon-512.png", "maskable-192.png", "maskable-512.png"]
MANIFEST = ICONS.parent / "manifest.webmanifest"


def main(theme: str) -> None:
    src = {"fiesta": ICONS / "fiesta-original", "muertos": ICONS / "muertos"}.get(theme)
    if not src:
        sys.exit(__doc__)
    for f in FILES:
        shutil.copyfile(src / f, ICONS / f)
    orig = ICONS / "fiesta-original" / "manifest.webmanifest"
    if theme == "fiesta":
        shutil.copyfile(orig, MANIFEST)
    else:
        m = json.loads(orig.read_text())
        m["background_color"] = m["theme_color"] = "#3E1160"
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    print(f"icons + manifest → {theme}. Now bump the build and commit.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
