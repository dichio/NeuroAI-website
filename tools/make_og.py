"""Generate assets/og-image.png, the 1200x630 social-preview image.

What it does
  1. Takes assets/brand/banner/banner-2400x900.jpg, scales it to the image
     height and positions it so the brain illustration (centred at about 65% of
     the banner's width) lands at about 71% of the preview's width, leaving the
     dark left side free for the logo.
  2. Darkens the left side with a horizontal gradient so the logo reads well.
  3. Places the stacked reversed logo (assets/brand/logo-stacked-reversed.svg)
     on the left, vertically centred.

How to run (from the repository root)
  python3 tools/make_og.py

Requirements
  - Python 3 with Pillow (pip install Pillow)
  - ImageMagick 7 ("magick" on the PATH), used only to rasterise the SVG logo,
    because Pillow cannot read SVG.

Notes
  - The logo SVG has a solid navy background <rect>. It is removed from an
    in-memory copy before rasterising so the logo sits on the banner without a
    visible box. ImageMagick also skips stroked horizontal <line> elements (the
    rule under "NeuroAI"), so in that same copy each one is redrawn as a filled
    <rect> with identical position, length, thickness and colour. The SVG file
    itself is never modified.
  - The page title is not baked into the banner on the website (it is live
    HTML there); this preview image is the only place where the logo is
    composited onto the banner.
"""

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BANNER = ROOT / "assets/brand/banner/banner-2400x900.jpg"
LOGO_SVG = ROOT / "assets/brand/logo-stacked-reversed.svg"
OUT = ROOT / "assets/og-image.png"

W, H = 1200, 630
LOGO_WIDTH = 440          # px, on the 1200x630 canvas
LOGO_LEFT = 80            # px from the left edge
DARKEN_TO = (4, 15, 34)   # colour of the banner's empty left area (#040F22)
BRAIN_X = 0.65            # horizontal centre of the brain in the banner (fraction of width)
BRAIN_TARGET = 0.71       # where that centre should land in the preview (fraction of width)


def place_banner(img, w, h):
    """Scale the banner to height h and shift it so its brain sits at BRAIN_TARGET of the width.
    Any uncovered area is filled with the banner's own dark background colour."""
    scale = h / img.height
    img = img.resize((round(img.width * scale), h), Image.LANCZOS)
    offset = round(w * BRAIN_TARGET - img.width * BRAIN_X)
    canvas = Image.new("RGB", (w, h), DARKEN_TO)
    canvas.paste(img, (offset, 0))
    return canvas


def left_gradient(w, h, colour, strength=0.85, reach=0.6):
    """RGBA overlay: `colour` at `strength` alpha on the left, fading out by `reach` of the width."""
    overlay = Image.new("RGBA", (w, h), colour + (0,))
    alpha = Image.new("L", (w, 1))
    for x in range(w):
        t = max(0.0, 1 - x / (w * reach))
        alpha.putpixel((x, 0), round(255 * strength * t))
    overlay.putalpha(alpha.resize((w, h)))
    return overlay


def line_as_rect(m):
    """Equivalent filled <rect> for a horizontal stroked <line> (ImageMagick ignores the stroke)."""
    x1, y, x2, colour, sw = float(m[1]), float(m[2]), float(m[3]), m[4], float(m[5])
    return f'<rect x="{x1}" y="{y - sw / 2}" width="{x2 - x1}" height="{sw}" fill="{colour}"/>'


def rasterise_logo(svg_path, width):
    """Render the SVG to a transparent PNG of the given width with ImageMagick."""
    svg = svg_path.read_text(encoding="utf-8")
    svg = re.sub(r'<rect width="100%" height="100%"[^>]*/>', "", svg, count=1)  # drop background box
    svg = re.sub(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="\2" stroke="(#[0-9a-fA-F]+)" stroke-width="([\d.]+)"/>',
                 line_as_rect, svg)
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "logo.svg", Path(tmp) / "logo.png"
        src.write_text(svg, encoding="utf-8")
        subprocess.run(["magick", "-background", "none", "-density", "600", str(src),
                        "-resize", f"{width}x", str(dst)], check=True)
        return Image.open(dst).convert("RGBA")


def main():
    canvas = place_banner(Image.open(BANNER).convert("RGB"), W, H).convert("RGBA")
    canvas = Image.alpha_composite(canvas, left_gradient(W, H, DARKEN_TO))
    logo = rasterise_logo(LOGO_SVG, LOGO_WIDTH)
    canvas.alpha_composite(logo, (LOGO_LEFT, (H - logo.height) // 2))
    canvas.convert("RGB").save(OUT, optimize=True)
    print(f"Wrote {OUT.relative_to(ROOT)} ({W}x{H})")


if __name__ == "__main__":
    main()
