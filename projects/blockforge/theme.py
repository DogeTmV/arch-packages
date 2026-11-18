"""Dark visual theme and vector icons for blockforge.

Qt is imported only inside helpers so that the compiler and tests can import
this module on a headless machine.  Every color lives here; widgets themselves
only refer to semantic names from :data:`DARK`.
"""

from core import CATEGORIES, CATEGORY_BY_KEY  # re-exported for the editor

DARK = {
    "window": "#0f1420",
    "panel": "#151b2b",
    "panel_alt": "#1b2336",
    "surface": "#222c42",
    "surface_hi": "#2a3651",
    "border": "#2b3750",
    "border_soft": "#222d43",
    "text": "#e8edf7",
    "muted": "#98a4bd",
    "accent": "#7c6cff",
    "accent_hover": "#9b8cff",
    "good": "#34d399",
    "warn": "#fbbf24",
    "bad": "#fb7185",
    "stage": "#101827",
    "shadow": "#070b12",
}

_GLYPHS = {
    "new": "M12 5v14M5 12h14",
    "open": "M4 7h6l2 2h8v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z",
    "save": "M5 3h11l3 3v15H5V3Zm3 0v6h8V3M8 21v-7h8v7",
    "examples": "M4 5h7v7H4V5Zm9 0h7v4h-7V5ZM4 14h7v5H4v-5Zm9 0h7v5h-7v-5Z",
    "build": "M7 4h10v5H7V4ZM5 11h14v3H5v-3Zm3 5h8v4H8v-4Z",
    "run": "M8 5v14l11-7L8 5Z",
    "stop": "M7 7h10v10H7V7Z",
    "preview": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    "plus": "M12 5v14M5 12h14",
    "trash": "M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14",
    "flag": "M5 21V4m0 0h11l-2 4 2 4H5",
    "sprite": "M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm-8 18a8 8 0 0 1 16 0H4Z",
    "variable": "M4 6h16v12H4V6Zm4 0v12m8-12v12",
    "procedure": "M6 4h7l4 4v12H6V4Zm7 0v5h4M9 13h6M9 17h6",
    "stage": "M3 5h18v14H3V5Zm6 4v6m-3-3h6m6-3v6m-3-3h6",
    "console": "M4 4h16v16H4V4Zm3 4 4 4-4 4m6 0h4",
    "search": "M11 4a7 7 0 1 1-4.9 12l-3.6 3.6-1.4-1.4 3.6-3.6A7 7 0 0 1 11 4Z",
}


def stylesheet():
    """Return the complete application stylesheet."""
    d = DARK
    return f"""
    QWidget {{
        background: {d['window']};
        color: {d['text']};
        font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background: {d['window']}; }}
    QToolBar#toolbar {{
        background: {d['panel']};
        border: none;
        border-bottom: 1px solid {d['border']};
        spacing: 8px;
        padding: 10px 14px;
    }}
    QLabel#projectTitle {{
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 0.2px;
        padding: 0 10px;
    }}
    QLabel#hint, QLabel#sectionTitle, QLabel#statusLabel {{
        color: {d['muted']};
        font-size: 11px;
        padding: 2px 4px;
    }}
    QLabel#sectionTitle {{
        color: {d['text']};
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    QFrame#panel, QFrame#card {{
        background: {d['panel']};
        border: 1px solid {d['border']};
        border-radius: 14px;
    }}
    QFrame#stageFrame {{
        background: {d['stage']};
        border: 1px solid {d['border']};
        border-radius: 12px;
    }}
    QPushButton, QToolButton {{
        background: {d['surface']};
        color: {d['text']};
        border: 1px solid {d['border']};
        border-radius: 9px;
        padding: 7px 13px;
        min-height: 20px;
    }}
    QToolButton {{
        padding: 6px 9px;
        min-width: 34px;
    }}
    QPushButton:hover, QToolButton:hover {{
        background: {d['surface_hi']};
        border-color: {d['accent']};
    }}
    QPushButton:pressed, QToolButton:pressed {{ background: {d['accent']}; }}
    QPushButton:checked, QToolButton:checked {{
        background: {d['accent']};
        color: #ffffff;
        border-color: {d['accent_hover']};
    }}
    QPushButton#primaryButton {{
        background: {d['accent']};
        color: #ffffff;
        border-color: {d['accent_hover']};
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{ background: {d['accent_hover']}; }}
    QPushButton#dangerButton {{ border-color: {d['bad']}; color: {d['bad']}; }}
    QPushButton#dangerButton:hover {{ background: {d['bad']}; color: #ffffff; }}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {d['panel_alt']};
        color: {d['text']};
        border: 1px solid {d['border']};
        border-radius: 8px;
        padding: 6px 9px;
        selection-background-color: {d['accent']};
    }}
    QComboBox:hover, QLineEdit:hover {{ border-color: {d['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {d['panel_alt']};
        color: {d['text']};
        border: 1px solid {d['border']};
        border-radius: 8px;
        selection-background-color: {d['accent']};
    }}
    QListWidget, QTreeWidget, QPlainTextEdit {{
        background: {d['panel_alt']};
        color: {d['text']};
        border: 1px solid {d['border']};
        border-radius: 10px;
        padding: 6px;
        selection-background-color: {d['accent']};
        selection-color: #ffffff;
    }}
    QListWidget::item, QTreeWidget::item {{
        border-radius: 7px;
        padding: 4px;
    }}
    QPlainTextEdit#sourceView {{
        font-family: "JetBrains Mono", "Fira Code", monospace;
        font-size: 11px;
        line-height: 18px;
    }}
    QPlainTextEdit#buildView {{
        font-family: "JetBrains Mono", "Fira Code", monospace;
        font-size: 11px;
    }}
    QTabWidget::pane {{
        background: {d['panel']};
        border: 1px solid {d['border']};
        border-radius: 10px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {d['muted']};
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 7px 15px;
        margin: 3px;
    }}
    QTabBar::tab:selected {{
        background: {d['surface']};
        color: {d['text']};
        border-color: {d['border']};
    }}
    QScrollBar:vertical {{
        background: transparent; width: 11px; margin: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {d['border']}; border-radius: 5px; min-height: 26px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {d['muted']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent; height: 11px; margin: 3px;
    }}
    QScrollBar::handle:horizontal {{
        background: {d['border']}; border-radius: 5px; min-width: 26px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QStatusBar {{ color: {d['muted']}; background: {d['window']}; }}
    QSplitter::handle {{ background: {d['border']}; }}
    QSplitter::handle:horizontal {{ width: 2px; }}
    QSplitter::handle:vertical {{ height: 2px; }}
    QToolTip {{
        background: {d['panel_alt']};
        color: {d['text']};
        border: 1px solid {d['border']};
        border-radius: 6px;
        padding: 5px;
    }}
    """


def install(app):
    """Apply the palette, stylesheet, and typography to *app*."""
    from PySide6.QtGui import QColor, QPalette

    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(DARK["window"]))
    palette.setColor(QPalette.WindowText, QColor(DARK["text"]))
    palette.setColor(QPalette.Base, QColor(DARK["panel_alt"]))
    palette.setColor(QPalette.AlternateBase, QColor(DARK["panel"]))
    palette.setColor(QPalette.Text, QColor(DARK["text"]))
    palette.setColor(QPalette.Button, QColor(DARK["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(DARK["text"]))
    palette.setColor(QPalette.Highlight, QColor(DARK["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DARK["muted"]))
    app.setPalette(palette)
    if hasattr(app, "setApplicationName"):
        app.setApplicationName("blockforge")


def category_color(key, default=None):
    """Return the palette color for a block category."""
    category = CATEGORY_BY_KEY.get(key)
    return category.color if category else (default or DARK["accent"])


def shade(color, factor):
    """Blend a hex color toward white (factor > 0) or black (factor < 0)."""
    from PySide6.QtGui import QColor

    value = QColor(color)
    target = QColor("#ffffff") if factor >= 0 else QColor("#000000")
    amount = abs(factor)
    return QColor(
        int(value.red() * (1 - amount) + target.red() * amount),
        int(value.green() * (1 - amount) + target.green() * amount),
        int(value.blue() * (1 - amount) + target.blue() * amount),
    )


def glyph(name):
    """Return inline SVG markup for a toolbar glyph."""
    path = _GLYPHS.get(name, _GLYPHS["new"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'width="24" height="24" fill="none" stroke="%s" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="%s"/></svg>'
        % (DARK["text"], path)
    )


def icon(name, color=None):
    """Build a QIcon from an inline SVG glyph."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    markup = glyph(name)
    if color:
        markup = markup.replace(DARK["text"], color)
    renderer = QSvgRenderer(markup.encode("utf-8"))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    renderer.render(QPainter(pixmap))
    return QIcon(pixmap)
