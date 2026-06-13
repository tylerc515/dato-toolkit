"""Generate assets/icon.ico from assets/logo.svg.

Renders the logo at several square sizes using PyQt6's QSvgRenderer,
letterboxing it (centered on a transparent canvas) to preserve its aspect
ratio, then combines the renders into a single multi-resolution .ico file
using Pillow.

Re-run this script whenever assets/logo.svg changes:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT_DIR / "assets" / "logo.svg"
ICO_PATH = ROOT_DIR / "assets" / "icon.ico"

SVG_WIDTH = 720
SVG_HEIGHT = 420

ICON_SIZES = [256, 64, 32, 16]


def _render_letterboxed(renderer: QSvgRenderer, size: int) -> Image.Image:
    """Render the logo scaled to fit within `size`x`size`, centered on a transparent canvas."""
    scale = size / max(SVG_WIDTH, SVG_HEIGHT)
    render_width = round(SVG_WIDTH * scale)
    render_height = round(SVG_HEIGHT * scale)
    offset_x = (size - render_width) // 2
    offset_y = (size - render_height) // 2

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter, QRectF(offset_x, offset_y, render_width, render_height))
    painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
    image.save(buffer, "PNG")
    png_bytes = bytes(buffer.data())
    buffer.close()

    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def main() -> None:
    app = QApplication(sys.argv)

    renderer = QSvgRenderer(str(SVG_PATH))

    images = [_render_letterboxed(renderer, size) for size in ICON_SIZES]
    largest, *rest = images
    largest.save(
        ICO_PATH,
        format="ICO",
        append_images=rest,
        sizes=[(img.width, img.height) for img in images],
    )
    print(f"Wrote {ICO_PATH}")

    app.quit()


if __name__ == "__main__":
    main()
    sys.exit(0)
