"""Generate assets/icon.ico from assets/tc_software_logo.png.

The source PNG is a wide "TC Software" wordmark on an oversized transparent
canvas. For a small square icon, the full wordmark would be squeezed into an
illegible sliver, so this script isolates just the leading "TC" mark (split
off from the trailing "Software" text at the transparent gap between them),
then renders it at several square sizes, letterboxed (centered on a
transparent canvas) to preserve its aspect ratio, and combines the renders
into a single multi-resolution .ico file using Pillow.

Re-run this script whenever assets/tc_software_logo.png changes:
    python scripts/generate_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT_DIR / "assets" / "tc_software_logo.png"
ICO_PATH = ROOT_DIR / "assets" / "icon.ico"

ICON_SIZES = [256, 64, 32, 16]

# Minimum run of fully-transparent columns, within the cropped wordmark,
# required to treat a gap as the word boundary between "TC" and "Software"
# rather than just natural letter spacing. Mirrors app/logo.py.
MIN_MARK_GAP_WIDTH = 10
ALPHA_CONTENT_THRESHOLD = 10


def _find_mark_split(content_image: Image.Image) -> int | None:
    """Find the x-offset of the widest interior transparent gap in a
    left-to-right wordmark, used to isolate a leading mark ("TC") from
    trailing text ("Software"). Returns None if no clear gap is found.
    """
    alpha = content_image.split()[3]
    width, height = alpha.size
    pixels = alpha.load()

    col_has_content = [
        any(pixels[x, y] > ALPHA_CONTENT_THRESHOLD for y in range(height)) for x in range(width)
    ]

    gaps: list[tuple[int, int]] = []
    x = 0
    while x < width:
        if not col_has_content[x]:
            start = x
            while x < width and not col_has_content[x]:
                x += 1
            if start > 0 and x < width:  # interior gap only, not leading/trailing padding
                gaps.append((start, x))
        else:
            x += 1

    if not gaps:
        return None

    widest = max(gaps, key=lambda gap: gap[1] - gap[0])
    if widest[1] - widest[0] < MIN_MARK_GAP_WIDTH:
        return None
    return widest[0]


def _load_mark() -> Image.Image:
    """Load the source PNG and isolate the compact "TC" mark.

    The raw alpha channel has a faint glow/antialiasing fringe extending far
    beyond the crisp text, so the alpha channel is thresholded before
    computing the bounding box (mirrors app/logo.py) - otherwise the crop
    covers nearly the entire oversized canvas instead of just the wordmark.
    """
    with Image.open(LOGO_PATH) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.split()[3]
        thresholded = alpha.point(lambda p: 255 if p > ALPHA_CONTENT_THRESHOLD else 0)
        bbox = thresholded.getbbox()
        content = rgba.crop(bbox) if bbox else rgba

    split_x = _find_mark_split(content)
    return content.crop((0, 0, split_x, content.height)) if split_x else content


def _render_letterboxed(mark: Image.Image, size: int) -> Image.Image:
    """Scale `mark` to fit within `size`x`size`, centered on a transparent canvas."""
    scale = size / max(mark.width, mark.height)
    render_width = round(mark.width * scale)
    render_height = round(mark.height * scale)
    resized = mark.resize((render_width, render_height), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset_x = (size - render_width) // 2
    offset_y = (size - render_height) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    return canvas


def main() -> None:
    mark = _load_mark()

    images = [_render_letterboxed(mark, size) for size in ICON_SIZES]
    largest, *rest = images
    largest.save(
        ICO_PATH,
        format="ICO",
        append_images=rest,
        sizes=[(img.width, img.height) for img in images],
    )
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
