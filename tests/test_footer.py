import sys
from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_link_label_stores_url():
    from app.widgets.footer import _LinkLabel
    label = _LinkLabel("Click me", "https://example.com", "#eaeaea")
    assert label._url == "https://example.com"
    assert label.text() == "Click me"


def test_footer_bar_fixed_height():
    from app.widgets.footer import FooterBar
    footer = FooterBar()
    assert footer.minimumHeight() == 28
    assert footer.maximumHeight() == 28
