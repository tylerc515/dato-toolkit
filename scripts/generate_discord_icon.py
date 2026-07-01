"""Generate assets/discord-icon.png from assets/tc_software_logo.png.

Crops the source wordmark down to its opaque content, isolates the
leading "TC" mark from the trailing "Software" text (split at the
widest transparent gap between them), and letterboxes it onto a
256x256 transparent square canvas -- Discord embed thumbnails require
a real square-ish hosted image, not a wide wordmark or an .ico/.svg.

NOTE: this duplicates the compact-mark cropping logic in
app/logo.py::get_icon() (see feature/visual-redesign, not yet merged
to main as of this script's creation). Once that branch merges, this
script should be simplified to just call app.logo.get_icon() and save
the result, removing the duplication.

Re-run this script whenever assets/tc_software_logo.png changes:
    python scripts/generate_discord_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT_DIR / "assets" / "tc_software_logo.png"
OUTPUT_PATH = ROOT_DIR / "assets" / "discord-icon.png"

ICON_SIZE = 256

# Alpha values at or below this are treated as "empty" when locating the
# opaque content bounding box / word-boundary gap (guards against faint
# antialiasing fringes registering as content).
ALPHA_CONTENT_THRESHOLD = 10

# Minimum run of fully-transparent columns, within the cropped wordmark,
# required to treat a gap as the word boundary between "TC" and "Software"
# rather than just natural letter spacing.
MIN_MARK_GAP_WIDTH = 10


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


def main() -> None:
    with Image.open(SOURCE_PATH) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.split()[3]
        thresholded = alpha.point(lambda p: 255 if p > ALPHA_CONTENT_THRESHOLD else 0)
        bbox = thresholded.getbbox()
        content = rgba.crop(bbox) if bbox else rgba

    split_x = _find_mark_split(content)
    mark = content.crop((0, 0, split_x, content.height)) if split_x else content

    scale = min(ICON_SIZE / mark.width, ICON_SIZE / mark.height)
    scaled = mark.resize((round(mark.width * scale), round(mark.height * scale)), Image.LANCZOS)

    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    offset = ((ICON_SIZE - scaled.width) // 2, (ICON_SIZE - scaled.height) // 2)
    canvas.paste(scaled, offset, scaled)
    canvas.save(OUTPUT_PATH, "PNG")
    print(f"Wrote {OUTPUT_PATH} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
