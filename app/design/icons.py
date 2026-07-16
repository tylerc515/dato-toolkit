"""Icon helper wrapping qtawesome's Phosphor ("ph.") icon set.

Verified against qtawesome 1.4.2: the `ph.` prefix resolves for every
name used in this app EXCEPT `mail` and `file-spreadsheet`, which don't
exist in this version's Phosphor font map. Use `envelope-simple` and
`table` instead - see docs/superpowers/plans/2026-07-01-visual-redesign.md
Global Constraints for the full list of confirmed names.
"""

import qtawesome as qta
from PyQt6.QtGui import QIcon

from app.design.tokens import Color


def icon(name: str, color: str = Color.TEXT_MUTED, size: int | None = None) -> QIcon:
    """Return a QIcon for the given Phosphor icon name (without the
    'ph.' prefix - pass just 'house', 'gear', etc).
    Use color=Color.ACCENT_TEXT for active/selected states.
    """
    return qta.icon(f"ph.{name}", color=color)
