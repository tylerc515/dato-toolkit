"""Entry point for TRACE Tracker Builder."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.logging_config import setup_logging
from app.logo import get_icon
from app.styles import STYLESHEET
from app.window import MainWindow


def main() -> int:
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(get_icon())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
