"""Entry point for TRACE Tracker Builder."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QPropertyAnimation, QTimer
from PyQt6.QtWidgets import QApplication

from app.logging_config import setup_logging
from app.logo import get_icon
from app.splash import SPLASH_MIN_DURATION_MS, SplashScreen
from app.styles import STYLESHEET
from app.window import MainWindow

SPLASH_FADE_DURATION_MS = 200


def main() -> int:
    setup_logging()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(get_icon())

    splash = SplashScreen()
    splash.show()
    splash.start()

    # Keep references alive for the duration of the startup sequence.
    startup: dict[str, object] = {}

    def _finish_startup() -> None:
        window = MainWindow()
        startup["window"] = window

        animation = QPropertyAnimation(splash, b"windowOpacity")
        animation.setDuration(SPLASH_FADE_DURATION_MS)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)

        def _on_fade_finished() -> None:
            window.show()
            splash.close()

        animation.finished.connect(_on_fade_finished)
        startup["animation"] = animation
        animation.start()

    QTimer.singleShot(SPLASH_MIN_DURATION_MS, _finish_startup)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
