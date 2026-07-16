"""Loads the app logo (assets/tc_software_logo.png) as a QPixmap/QIcon.

The source asset is a raster PNG: a wide "TC Software" wordmark (blue "TC"
mark followed by gray "Software" text) rendered on an oversized transparent
canvas. The bulk of that canvas is empty padding around the actual artwork,
so the first thing this module does is crop the image down to its opaque
content (using the alpha channel) before anything gets scaled - otherwise
every consumer would receive a mostly-blank pixmap with a tiny sliver of
logo in the middle.

Two cropped sources are cached from that content bounding box:

- The full "TC Software" wordmark (~6.7:1 aspect ratio).
- Just the leading "TC" mark, split off at the widest gap between "TC" and
  "Software" (~1.7:1 aspect ratio) - close to square, which is what most of
  this app's existing UI slots (28x28 sidebar icon, 48x28 update-dialog
  logo, etc.) were originally sized for.

`get_pixmap` picks between them per call based on the height the full
wordmark would end up at once scaled to fit the requested box: below a
legibility threshold it falls back to the compact mark so small/near-square
slots don't render an unreadable 4px-tall sliver of text. `get_icon` always
uses the compact mark, letterboxed onto a square canvas, since window/
taskbar/tray icons are inherently small squares.
"""

from __future__ import annotations

import io
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap

LOGO_FILENAME = "tc_software_logo.png"

# Window/taskbar/tray icons are always small squares, so get_icon() always
# uses the compact "TC" mark letterboxed onto a canvas of this size.
ICON_PIXMAP_SIZE = (256, 256)

# If scaling the full "TC Software" wordmark to fit a requested box would
# render the text shorter than this, it's no longer legible - fall back to
# the compact "TC" mark instead. Chosen so the app's tightest real slots
# (28x28 sidebar icon -> ~4px tall wordmark, 48x28 update-dialog logo ->
# ~7px tall wordmark) fall back, while its more spacious slots (180x105
# success card -> ~27px, 240x140 onboarding -> ~36px, 200x116 splash ->
# ~30px) keep the full wordmark.
MIN_LEGIBLE_WORDMARK_HEIGHT = 20

# Minimum run of fully-transparent columns, within the cropped wordmark,
# required to treat a gap as the word boundary between "TC" and "Software"
# rather than just natural letter spacing.
MIN_MARK_GAP_WIDTH = 10

# Alpha values at or below this are treated as "empty" when locating the
# opaque content bounding box / word-boundary gap (guards against faint
# antialiasing fringes registering as content).
ALPHA_CONTENT_THRESHOLD = 10


def _logo_path() -> Path:
    """Return the path to assets/tc_software_logo.png, whether running from source or frozen."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "assets" / LOGO_FILENAME


def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL RGBA image to a QPixmap without touching disk."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap


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


@lru_cache(maxsize=1)
def _content_image() -> Image.Image:
    """The source PNG cropped to its opaque content (alpha-based bounding box).

    The raw alpha channel has a faint glow/antialiasing fringe that extends
    far beyond the crisp text (visible pixel values as low as 1-3 across
    most of the canvas), so QPixmap.getbbox()`` on the untouched alpha band
    returns a bounding box covering nearly the entire image. Thresholding
    the alpha channel first keeps the bounding box tight around the actual
    legible text.
    """
    with Image.open(_logo_path()) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.split()[3]
        thresholded = alpha.point(lambda p: 255 if p > ALPHA_CONTENT_THRESHOLD else 0)
        bbox = thresholded.getbbox()
        return rgba.crop(bbox) if bbox else rgba


@lru_cache(maxsize=1)
def _wordmark_pixmap() -> QPixmap:
    """The full "TC Software" wordmark, cropped to its content."""
    return _pil_to_qpixmap(_content_image())


@lru_cache(maxsize=1)
def _mark_pixmap() -> QPixmap:
    """Just the leading "TC" mark, split off from the trailing "Software" text."""
    content = _content_image()
    split_x = _find_mark_split(content)
    mark = content.crop((0, 0, split_x, content.height)) if split_x else content
    return _pil_to_qpixmap(mark)


def get_pixmap(width: int, height: int) -> QPixmap:
    """Return the logo scaled to fit within (width, height), preserving aspect ratio.

    Uses the full "TC Software" wordmark when the requested box is spacious
    enough for it to stay legible, otherwise falls back to the compact "TC"
    mark alone (see MIN_LEGIBLE_WORDMARK_HEIGHT).
    """
    wordmark = _wordmark_pixmap()
    scale = min(width / wordmark.width(), height / wordmark.height())
    projected_height = wordmark.height() * scale

    source = wordmark if projected_height >= MIN_LEGIBLE_WORDMARK_HEIGHT else _mark_pixmap()

    return source.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def get_icon() -> QIcon:
    """Return a QIcon built from the logo, suitable for use as the window icon.

    Always uses the compact "TC" mark (not the full wordmark) letterboxed
    onto a transparent square canvas, since window/taskbar/tray icons are
    rendered at small square sizes where the full wordmark would be
    illegible.
    """
    size, _ = ICON_PIXMAP_SIZE
    mark = _mark_pixmap().scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    canvas = QPixmap(size, size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.drawPixmap((size - mark.width()) // 2, (size - mark.height()) // 2, mark)
    painter.end()

    return QIcon(canvas)
