import sys
from unittest.mock import patch

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
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


def test_link_label_opens_url_on_click():
    from app.widgets.footer import _LinkLabel
    label = _LinkLabel("Click me", "https://example.com", "#eaeaea")
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with patch("app.widgets.footer.webbrowser.open") as mock_open:
        label.mousePressEvent(event)
    mock_open.assert_called_once_with("https://example.com")


def test_footer_bar_shows_bsi_website_link():
    from app.widgets.footer import BSI_WEBSITE_URL, FooterBar, _LinkLabel
    footer = FooterBar()
    links = footer.findChildren(_LinkLabel)
    bsi_links = [link for link in links if link._url == BSI_WEBSITE_URL]
    assert len(bsi_links) == 1
    assert bsi_links[0].text() == "Boiler Services and Inspection"
    assert BSI_WEBSITE_URL == "https://www.boilerservicesandinspection.com"


def test_footer_bar_link_order():
    from app.widgets.footer import FooterBar, _LinkLabel
    footer = FooterBar()
    labels = [link.text() for link in footer.findChildren(_LinkLabel)]
    assert labels == [
        "Developed by Tyler Chambers",
        "Boiler Services and Inspection",
        "Documentation",
    ]


def test_link_label_ignores_right_click():
    from app.widgets.footer import _LinkLabel
    label = _LinkLabel("Click me", "https://example.com", "#eaeaea")
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with patch("app.widgets.footer.webbrowser.open") as mock_open:
        label.mousePressEvent(event)
    mock_open.assert_not_called()
