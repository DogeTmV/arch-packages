"""Shared dark visual theme for the minimal GUI utilities.

This module deliberately does **not** import Qt at import time, so applications
can answer ``--help`` / ``--version`` on a machine with no display server.
Every helper imports the Qt classes it needs when it is called.

The design uses one flat dark palette, one rounded surface style, and small
stroke-based vector icons drawn from inline SVG.  No external icon theme or
asset file is required at runtime.
"""

BG = "#101217"
SURFACE = "#191c24"
RAISED = "#222632"
BORDER = "#303646"
BORDER_HOVER = "#444d63"
TEXT = "#e8ebf5"
MUTED = "#98a1b5"
ACCENT = "#7c6cff"
ACCENT_HOVER = "#9184ff"
ACCENT_PRESS = "#6857e8"
SUCCESS = "#4ade80"
DANGER = "#fb7185"

STYLE_SHEET = """
QWidget {
    background: %(bg)s;
    color: %(text)s;
    font-family: "Inter", "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 13px;
}
QFrame#card {
    background: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
}
QFrame#divider {
    background: %(border)s;
    max-height: 1px;
    min-height: 1px;
    border: none;
}
QFrame#panel {
    background: %(raised)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
}
QLabel#h1 { font-size: 17px; font-weight: 700; color: %(text)s; }
QLabel#h2 { font-size: 11px; font-weight: 600; color: %(muted)s; }
QLabel#field { font-size: 11px; font-weight: 600; color: %(muted)s; }
QLabel#status { font-size: 12px; color: %(muted)s; }
QLabel#value {
    font-size: 12px; font-weight: 600; color: %(accent)s;
    background: %(raised)s; border: 1px solid %(border)s;
    border-radius: 6px; padding: 4px 8px;
}
QPushButton {
    background: %(raised)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    padding: 7px 13px;
    min-height: 16px;
}
QPushButton:hover { background: %(hover)s; border-color: %(border_hover)s; }
QPushButton:pressed { background: %(border)s; }
QPushButton:disabled { color: %(muted)s; background: %(surface)s; border-color: %(border)s; }
QPushButton[accent="true"] {
    background: %(accent)s; border-color: %(accent)s; color: #ffffff; font-weight: 600;
}
QPushButton[accent="true"]:hover { background: %(accent_hover)s; border-color: %(accent_hover)s; }
QPushButton[accent="true"]:pressed { background: %(accent_press)s; }
QPushButton[flat="true"] { background: transparent; border: 1px solid transparent; color: %(muted)s; }
QPushButton[flat="true"]:hover { background: %(raised)s; color: %(text)s; }
QPushButton#slot {
    min-height: 72px; font-size: 17px; font-weight: 700;
    border-radius: 12px; color: %(muted)s;
}
QPushButton#slot[assigned="true"] {
    color: %(accent)s; border-color: %(accent)s;
    background: %(surface)s;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QListWidget {
    background: %(bg)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    padding: 6px 9px;
    selection-background-color: %(accent)s;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus, QListWidget:focus {
    border-color: %(accent)s;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    image: none; border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid %(muted)s; margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: %(raised)s; color: %(text)s;
    border: 1px solid %(border)s; border-radius: 8px;
    selection-background-color: %(accent)s; selection-color: #ffffff;
    padding: 4px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: transparent; border: none; width: 16px;
}
QListWidget::item { border-radius: 6px; padding: 5px 8px; }
QListWidget::item:selected { background: %(accent)s; color: #ffffff; }
QSlider::groove:horizontal {
    background: %(border)s; height: 5px; border-radius: 3px; margin: 7px 0;
}
QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #ffffff; border: 3px solid %(accent)s;
    width: 12px; height: 12px; border-radius: 10px; margin: -6px 0;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: %(border_hover)s; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip {
    background: %(raised)s; color: %(text)s;
    border: 1px solid %(border)s; border-radius: 6px; padding: 5px 8px;
}
""" % {
    "bg": BG, "surface": SURFACE, "raised": RAISED, "border": BORDER,
    "border_hover": BORDER_HOVER, "text": TEXT, "muted": MUTED,
    "accent": ACCENT, "accent_hover": ACCENT_HOVER, "accent_press": ACCENT_PRESS,
    "hover": "#2b3040",
}

# Stroke glyphs drawn on a 24x24 grid.  Paths use the supplied stroke colour;
# filled shapes override fill/stroke inline.
_GLYPHS = {
    "wave": '<path d="M3 12h2M7 8v8M11 4v16M15 7v10M19 10v4"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "open": '<path d="M3 8a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v1"/><path d="M3 10h17l-2 7a2 2 0 0 1-2 1.5H5A2 2 0 0 1 3 17z"/>',
    "export": '<path d="M12 17V5"/><path d="m7 10 5-5 5 5"/><path d="M4 19h16"/>',
    "download": '<path d="M12 5v12"/><path d="m7 12 5 5 5-5"/><path d="M4 19h16"/>',
    "play": '<path d="M8 5.5v13L19 12z" fill="{color}" stroke="none"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2" fill="{color}" stroke="none"/>',
    "scissors": '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M20 4 8.5 15.5M14 14l6 6M8.5 8.5 12 12"/>',
    "crop": '<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M2 6h14a2 2 0 0 1 2 2v14"/>',
    "convert": '<path d="M3 7h14l-3-3"/><path d="M21 17H7l3 3"/><path d="M19 7a4 4 0 0 0-4-4M5 17a4 4 0 0 0 4 4"/>',
    "cancel": '<path d="M6 6l12 12M18 6 6 18"/>',
    "hash": '<path d="M5 9h14M4 15h14M10 3 8 21M16 3l-2 18"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "add": '<path d="M12 5v14M5 12h14"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    "pencil": '<path d="m4 20 4.5-1 10-10-3.5-3.5-10 10z"/><path d="m13.5 6.5 3.5 3.5"/>',
    "format": '<path d="m4 20 11-11"/><path d="m14 3 1.2 2.4L18 6.5l-2.8 1.1L14 10l-1.2-2.4L10 6.5l2.8-1.1z"/><path d="M19 13v6M16 16h6"/>',
    "minify": '<path d="M8 3v6H2M16 21v-6h6"/><path d="M3 3l5 5M21 21l-5-5"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 10v6M14 10v6"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2"/>',
    "sliders": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2.2"/><circle cx="15" cy="17" r="2.2"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "film": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M7 4v16M17 4v16M2 9h5M2 15h5M17 9h5M17 15h5"/>',
    "file": '<path d="M5 2h9l5 5v15H5z"/><path d="M14 2v5h5"/>',
    "braces": '<path d="M8 3H7a2 2 0 0 0-2 2v4a2 2 0 0 1-2 2 2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h1"/><path d="M16 3h1a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2 2 2 0 0 0-2 2v4a2 2 0 0 1-2 2h-1"/>',
    "calc": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h2M14 11h2M8 15h2M14 15h2M8 19h8"/>',
}

ACCENTS = {
    "tapecut": "#f472b6", "toneshift": "#38bdf8", "soundboard": "#fbbf24",
    "fileforge": "#a78bfa", "ytdock": "#fb7185", "cutframe": "#34d399",
    "hashcheck": "#60a5fa", "batchrename": "#fb923c", "jsonpolish": "#2dd4bf",
}


def install(app):
    """Apply the dark palette and stylesheet to a QApplication."""
    from PySide6 import QtGui

    palette = QtGui.QPalette()
    for role, color in (
        (QtGui.QPalette.ColorRole.Window, BG),
        (QtGui.QPalette.ColorRole.Base, BG),
        (QtGui.QPalette.ColorRole.AlternateBase, SURFACE),
        (QtGui.QPalette.ColorRole.ToolTipBase, RAISED),
        (QtGui.QPalette.ColorRole.Text, TEXT),
        (QtGui.QPalette.ColorRole.ToolTipText, TEXT),
        (QtGui.QPalette.ColorRole.Button, RAISED),
        (QtGui.QPalette.ColorRole.ButtonText, TEXT),
        (QtGui.QPalette.ColorRole.Highlight, ACCENT),
        (QtGui.QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QtGui.QColor(color))
    palette.setColor(QtGui.QPalette.ColorGroup.Disabled,
                     QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(MUTED))
    app.setPalette(palette)
    app.setStyleSheet(STYLE_SHEET)
    return app


def _render_svg(svg, size):
    from PySide6.QtCore import QByteArray, QSize, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return pixmap


def _svg_for(glyph, color, size):
    body = _GLYPHS[glyph].format(color=color)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">%s</svg>'
        % (size, size, color, body)
    )


def icon(name, color=TEXT, size=18):
    """Return a crisp QIcon for one of the named stroke glyphs."""
    from PySide6.QtGui import QIcon
    return QIcon(_render_svg(_svg_for(name, color, size * 2), size * 2))


def app_icon(name, size=32):
    """Return the branded app icon (glyph on a rounded accent tile)."""
    from PySide6.QtGui import QIcon
    color = ACCENTS.get(name, ACCENT)
    body = _GLYPHS[_APP_GLYPH.get(name, "file")].format(color="#ffffff")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 24 24"><rect x="1" y="1" width="22" height="22" rx="6" '
        'fill="%s"/><g fill="none" stroke="#ffffff" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">%s</g></svg>'
        % (size * 2, size * 2, color, body)
    )
    return QIcon(_render_svg(svg, size * 2))


_APP_GLYPH = {
    "tapecut": "wave", "toneshift": "sliders", "soundboard": "grid",
    "fileforge": "convert", "ytdock": "download", "cutframe": "film",
    "hashcheck": "hash", "batchrename": "pencil", "jsonpolish": "braces",
}


def badge(name, size=36):
    """Return a QLabel containing the branded app badge."""
    from PySide6.QtWidgets import QLabel
    label = QLabel()
    label.setPixmap(app_icon(name, size).pixmap(size, size))
    label.setFixedSize(size, size)
    return label


def label(text, kind=None):
    """Return a QLabel with an optional semantic style name."""
    from PySide6.QtWidgets import QLabel
    item = QLabel(text)
    if kind:
        item.setObjectName(kind)
    if kind in ("status", "h2", "field"):
        item.setWordWrap(True)
    return item


def button(text, glyph=None, accent=False, flat=False):
    """Return a QPushButton, optionally with a vector icon."""
    from PySide6.QtWidgets import QPushButton
    item = QPushButton(text)
    if glyph:
        from PySide6.QtCore import QSize
        item.setIcon(icon(glyph, "#ffffff" if accent else TEXT))
        item.setIconSize(QSize(16, 16))
    if accent:
        item.setProperty("accent", True)
    if flat:
        item.setProperty("flat", True)
    return item


def card(title=None, subtitle=None):
    """Return a styled QFrame with a prepared vertical layout."""
    from PySide6.QtWidgets import QFrame, QVBoxLayout
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "h2"))
    if subtitle:
        layout.addWidget(label(subtitle, "status"))
    return frame


def header(name, description):
    """Return a branded header widget with ``title``/``subtitle`` labels."""
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(12)
    row.addWidget(badge(name, 40))
    column = QVBoxLayout()
    column.setSpacing(2)
    title = label(name, "h1")
    subtitle = label(description, "status")
    column.addWidget(title)
    column.addWidget(subtitle)
    row.addLayout(column)
    row.addStretch(1)
    widget.title = title
    widget.subtitle = subtitle
    return widget


def field(text, control):
    """Return a labelled control (small muted label above the widget)."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(label(text, "field"))
    layout.addWidget(control)
    widget.control = control
    return widget


def divider():
    from PySide6.QtWidgets import QFrame
    line = QFrame()
    line.setObjectName("divider")
    return line


def polish(window, name):
    """Final touches shared by every window: icon, minimum size, theme."""
    window.setWindowIcon(app_icon(name))
    window.setContentsMargins(0, 0, 0, 0)
    return window
