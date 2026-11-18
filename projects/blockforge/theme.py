"""Scratch 3.0 visual theme for blockforge.

The colors and geometry here mirror Scratch 3.0's default theme: the purple
menu bar, pale blue page, white toolbox, light gray workspace, and the exact
category colors used by scratch-blocks.  Qt is imported only inside helpers so
the compiler and headless tests can import this module safely.
"""

from core import CATEGORIES, CATEGORY_BY_KEY  # re-exported for the editor

# Scratch's default theme (src/lib/themes/default/index.js) and GUI colors
# (src/css/colors.css).  The shorter names are kept for existing callers.
SCRATCH = {
    "menu": "#855CD6",
    "menu_text": "#FFFFFF",
    "page": "#E5F0FF",
    "secondary": "#E9F1FC",
    "tertiary": "#D9E3F2",
    "workspace": "#F9F9F9",
    "stage_header": "#E8EDF1",
    "drop_highlight": "#99C8FF",
    "scrollbar": "#CECDCE",
    "panel": "#FFFFFF",
    "panel_alt": "#E9F1FC",
    "surface": "#FFFFFF",
    "surface_hi": "#F2F6FC",
    "toolbox": "#FFFFFF",
    "toolbox_hover": "#4C97FF",
    "toolbox_selected": "#E9EEF2",
    "flyout": "#F9F9F9",
    "border": "#D9E3F2",
    "border_soft": "#E5EAF3",
    "text": "#575E75",
    "muted": "#7D879E",
    "accent": "#4C97FF",
    "accent_hover": "#3373CC",
    "selection": "#4C97FF",
    "good": "#0FBD8C",
    "warn": "#FFAB19",
    "bad": "#FF6680",
    "stage": "#FFFFFF",
    "stage_border": "rgba(0, 0, 0, 0.15)",
    "shadow": "rgba(0, 0, 0, 0.15)",
    "window": "#E5F0FF",
}

# Backwards-compatible alias for modules that still refer to the old name.
DARK = SCRATCH

# Scratch 3.0 block category colors: primary, secondary and tertiary.
BLOCK_COLORS = {
    "motion": ("#4C97FF", "#4280D7", "#3373CC"),
    "looks": ("#9966FF", "#855CD6", "#774DCB"),
    "sound": ("#CF63CF", "#C94FC9", "#BD42BD"),
    "events": ("#FFBF00", "#E6AC00", "#CC9900"),
    "control": ("#FFAB19", "#EC9C13", "#CF8B17"),
    "sensing": ("#5CB1D6", "#47A8D1", "#2E8EB8"),
    "operators": ("#59C059", "#46B946", "#389438"),
    "variables": ("#FF8C1A", "#FF8000", "#DB6E00"),
    "pen": ("#0FBD8C", "#0DA57A", "#0B8E69"),
    "custom": ("#FF6680", "#FF4D6A", "#FF3355"),
}

# Scratch uses a bowler-hat shape for event hats and a curved stack shape for
# custom-block definitions.  These helpers are what the palette and workspace
# both paint, so the two views cannot drift apart.
_GLYPHS = {
    "new": "M12 5v14M5 12h14",
    "open": "M4 7h6l2 2h8v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z",
    "save": "M5 3h11l3 3v15H5V3Zm3 0v6h8V3M8 21v-7h8v7",
    "examples": "M4 5h7v7H4V5Zm9 0h7v4h-7V5ZM4 14h7v5H4v-5Zm9 0h7v5h-7v-5Z",
    "build": "M7 4h10v5H7V4ZM5 11h14v3H5v-3Zm3 5h8v4H8v-4Z",
    "run": "M8 5v14l11-7L8 5Z",
    "stop": "M7 7h10v10H7V7Z",
    "preview": "M8 5v14l11-7L8 5Z",
    "plus": "M12 5v14M5 12h14",
    "trash": "M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14",
    "flag": "M5 21V4m0 0h11l-2 4 2 4H5",
    "sprite": "M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm-8 18a8 8 0 0 1 16 0H4Z",
    "variable": "M4 6h16v12H4V6Zm4 0v12m8-12v12",
    "procedure": "M6 4h7l4 4v12H6V4Zm7 0v5h4M9 13h6M9 17h6",
    "stage": "M3 5h18v14H3V5Zm6 4v6m-3-3h6m6-3v6m-3-3h6",
    "console": "M4 4h16v16H4V4Zm3 4 4 4-4 4m6 0h4",
    "search": "M11 4a7 7 0 1 1-4.9 12l-3.6 3.6-1.4-1.4 3.6-3.6A7 7 0 0 1 11 4Z",
    "settings": "M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0-5 2 3h3l1 3-2 2 2 2-1 3h-3l-2 3-2-3H7l-1-3 2-2-2-2 1-3h3l2-3Z",
    "eye": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    "move": "M12 3v18M3 12h18M12 3l-3 3m3-3 3 3M12 21l-3-3m3 3 3-3M3 12l3-3m-3 3 3 3M21 12l-3-3m3 3-3 3",
    "wave": "M3 12h2l2-6 3 12 3-15 3 18 3-9h2",
    "radar": "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18Zm0 5a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0 4 6-6",
    "loop": "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3",
    "braces": "M9 4H7a3 3 0 0 0-3 3v3a3 3 0 0 1-2 2 3 3 0 0 1 2 2v3a3 3 0 0 0 3 3h2m6-16h2a3 3 0 0 1 3 3v3a3 3 0 0 0 2 2 3 3 0 0 0-2 2v3a3 3 0 0 1-3 3h-2",
    "pen": "M4 20l4-1 10-10-3-3L5 16l-1 4Zm11-14 3 3m-1-5 3 3",
    "puzzle": "M4 4h6v3a2 2 0 1 0 4 0V4h6v6h-3a2 2 0 1 0 0 4h3v6h-6v-3a2 2 0 1 0-4 0v3H4v-6h3a2 2 0 1 0 0-4H4V4Z",
    "book": "M4 5a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-2V5Zm2 0v14m3-10h6m-6 4h6",
}


def stylesheet():
    """Return the complete Scratch 3.0 application stylesheet."""
    s = SCRATCH
    return f"""
    QWidget {{
        background: {s['page']};
        color: {s['text']};
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 12px;
    }}
    QMainWindow, QDialog {{ background: {s['page']}; }}
    QToolBar#toolbar {{
        background: {s['menu']};
        border: none;
        color: {s['menu_text']};
        spacing: 2px;
        padding: 0 8px;
    }}
    QToolBar#toolbar QLabel, QToolBar#toolbar QToolButton,
    QToolBar#toolbar QComboBox {{
        color: {s['menu_text']};
        background: transparent;
        border: none;
    }}
    QLabel#brandLogo {{
        color: {s['menu_text']};
        font-size: 15px;
        font-weight: 700;
        padding: 0 12px 0 4px;
    }}
    QToolButton#fileMenuButton, QToolButton#editMenuButton,
    QToolButton#helpMenuButton {{
        color: {s['menu_text']};
        background: transparent;
        border: none;
        padding: 0 10px;
        font-weight: 700;
        min-height: 46px;
    }}
    QToolButton#fileMenuButton:hover, QToolButton#editMenuButton:hover,
    QToolButton#helpMenuButton:hover {{ background: rgba(0, 0, 0, 0.15); }}
    QLineEdit#projectTitle {{
        background: rgba(255, 255, 255, 0.25);
        color: {s['menu_text']};
        border: 1px dashed rgba(255, 255, 255, 0.65);
        border-radius: 4px;
        padding: 5px 8px;
        font-weight: 700;
        font-size: 12px;
        min-width: 180px;
        max-width: 240px;
    }}
    QLineEdit#projectTitle:hover {{ background: rgba(255, 255, 255, 0.5); }}
    QLineEdit#projectTitle:focus {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['panel']};
    }}
    QComboBox#languageCombo {{
        color: {s['menu_text']};
        background: rgba(255, 255, 255, 0.2);
        border: 1px dashed rgba(255, 255, 255, 0.65);
        border-radius: 4px;
        padding: 4px 8px;
        min-width: 72px;
    }}
    QLabel#hint, QLabel#sectionTitle, QLabel#statusLabel {{
        color: {s['text']};
        font-size: 11px;
        padding: 2px 4px;
        background: transparent;
    }}
    QFrame#toolboxPanel {{
        background: {s['toolbox']};
        border: none;
        border-right: 1px solid {s['border']};
    }}
    QToolButton#category_motion, QToolButton#category_looks,
    QToolButton#category_sound, QToolButton#category_events,
    QToolButton#category_control, QToolButton#category_sensing,
    QToolButton#category_operators, QToolButton#category_variables,
    QToolButton#category_pen, QToolButton#category_custom {{
        background: {s['toolbox']};
        color: {s['text']};
        border: none;
        border-left: 4px solid transparent;
        border-radius: 0;
        padding: 7px 4px;
        font-size: 10px;
        font-weight: 700;
        text-align: left;
        min-height: 38px;
    }}
    QToolButton#category_motion:hover, QToolButton#category_looks:hover,
    QToolButton#category_sound:hover, QToolButton#category_events:hover,
    QToolButton#category_control:hover, QToolButton#category_sensing:hover,
    QToolButton#category_operators:hover, QToolButton#category_variables:hover,
    QToolButton#category_pen:hover, QToolButton#category_custom:hover {{
        border-left-color: {s['toolbox_hover']};
    }}
    QToolButton#category_motion:checked {{ border-left-color: #4C97FF; background: {s['toolbox_selected']}; }}
    QToolButton#category_looks:checked {{ border-left-color: #9966FF; background: {s['toolbox_selected']}; }}
    QToolButton#category_sound:checked {{ border-left-color: #CF63CF; background: {s['toolbox_selected']}; }}
    QToolButton#category_events:checked {{ border-left-color: #FFBF00; background: {s['toolbox_selected']}; }}
    QToolButton#category_control:checked {{ border-left-color: #FFAB19; background: {s['toolbox_selected']}; }}
    QToolButton#category_sensing:checked {{ border-left-color: #5CB1D6; background: {s['toolbox_selected']}; }}
    QToolButton#category_operators:checked {{ border-left-color: #59C059; background: {s['toolbox_selected']}; }}
    QToolButton#category_variables:checked {{ border-left-color: #FF8C1A; background: {s['toolbox_selected']}; }}
    QToolButton#category_pen:checked {{ border-left-color: #0FBD8C; background: {s['toolbox_selected']}; }}
    QToolButton#category_custom:checked {{ border-left-color: #FF6680; background: {s['toolbox_selected']}; }}
    QFrame#flyoutPanel {{
        background: {s['flyout']};
        border: none;
        border-right: 1px solid {s['border']};
    }}
    QScrollArea#workspacePanel {{
        background: {s['workspace']};
        border: none;
    }}
    QWidget#workspaceContent {{ background: {s['workspace']}; }}
    QFrame#editorPane, QFrame#editorTabs {{
        background: {s['page']};
        border: none;
    }}
    QToolButton#tabBlocks, QToolButton#tabCostumes, QToolButton#tabSounds {{
        background: {s['tertiary']};
        color: {s['text']};
        border: 1px solid {s['stage_border']};
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 14px;
        min-width: 78px;
        min-height: 30px;
    }}
    QToolButton#tabBlocks:checked, QToolButton#tabCostumes:checked,
    QToolButton#tabSounds:checked {{
        background: {s['panel']};
        color: {s['menu']};
        min-height: 34px;
    }}
    QFrame#stagePane {{
        background: {s['page']};
        border: none;
    }}
    QFrame#stageFrame {{
        background: {s['stage']};
        border: 1px solid {s['stage_border']};
        border-radius: 8px;
    }}
    QFrame#stageHeader {{
        background: {s['stage_header']};
        border: none;
    }}
    QLabel#stageHeading {{
        color: {s['text']};
        font-size: 12px;
        font-weight: 700;
        background: transparent;
    }}
    QToolButton#previewButton {{
        background: {s['panel']};
        border: 1px solid {s['stage_border']};
        border-radius: 4px;
        color: {s['good']};
        padding: 3px;
        min-width: 34px;
        min-height: 34px;
        font-size: 17px;
    }}
    QToolButton#stopButton {{
        background: {s['panel']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        color: #FF661A;
        padding: 3px;
        min-width: 34px;
        min-height: 34px;
        font-size: 14px;
    }}
    QToolButton#backdropButton, QToolButton#stageLookButton,
    QToolButton#libraryButton, QToolButton#addSpriteButton {{
        background: {s['panel']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        color: {s['text']};
        padding: 4px;
    }}
    QFrame#targetPane {{
        background: {s['secondary']};
        border: none;
    }}
    QToolButton#stageSelector {{
        background: {s['panel']};
        color: {s['text']};
        border: 2px solid {s['stage_border']};
        border-radius: 8px 8px 0 0;
        font-size: 10px;
        font-weight: 700;
        min-width: 72px;
        min-height: 104px;
    }}
    QToolButton#stageSelector:checked {{
        background: {s['menu']};
        color: {s['menu_text']};
        border-color: {s['menu']};
    }}
    QFrame#spritePane {{
        background: {s['secondary']};
        border: none;
    }}
    QFrame#spriteInfo {{
        background: {s['panel']};
        border: 1px solid {s['stage_border']};
        border-bottom: none;
        border-radius: 8px 8px 0 0;
    }}
    QListWidget#spriteList {{
        background: {s['secondary']};
        border: none;
        padding: 2px;
    }}
    QListWidget#spriteList::item {{
        background: {s['panel']};
        border: 2px solid {s['stage_border']};
        border-radius: 8px;
        margin: 2px;
        padding: 3px;
    }}
    QListWidget#spriteList::item:selected {{
        background: {s['panel']};
        border: 2px solid {s['menu']};
    }}
    QFrame#costumePane, QFrame#soundPane {{
        background: {s['workspace']};
        border: 1px solid {s['border']};
        border-radius: 0 0 8px 8px;
    }}
    QPushButton, QToolButton {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 6px 10px;
        min-height: 20px;
    }}
    QToolButton {{ padding: 5px 8px; min-width: 28px; }}
    QPushButton:hover, QToolButton:hover {{ background: {s['surface_hi']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {s['toolbox_selected']}; }}
    QPushButton:checked, QToolButton:checked {{ background: {s['toolbox_selected']}; }}
    QPushButton#primaryButton {{
        background: {s['good']};
        color: {s['menu_text']};
        border-color: {s['good']};
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{ background: #0DA57A; }}
    QPushButton#dangerButton {{ border-color: {s['bad']}; color: {s['bad']}; }}
    QPushButton#dangerButton:hover {{ background: {s['bad']}; color: {s['menu_text']}; }}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 5px 8px;
        selection-background-color: {s['selection']};
    }}
    QComboBox:hover, QLineEdit:hover {{ border-color: {s['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        selection-background-color: {s['toolbox_selected']};
        selection-color: {s['text']};
    }}
    QListWidget, QTreeWidget, QPlainTextEdit {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 4px;
        selection-background-color: {s['toolbox_selected']};
        selection-color: {s['text']};
    }}
    QListWidget::item, QTreeWidget::item {{ border-radius: 4px; padding: 3px; }}
    QPlainTextEdit#buildView, QPlainTextEdit#outputView {{
        font-family: "JetBrains Mono", "Fira Code", monospace;
        font-size: 11px;
    }}
    QTabWidget::pane {{
        background: {s['panel']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: {s['secondary']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 6px 12px;
        margin: 2px;
    }}
    QTabBar::tab:selected {{ background: {s['panel']}; border-bottom-color: {s['panel']}; }}
    QMenu {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 4px;
    }}
    QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {s['toolbox_selected']}; }}
    QScrollBar:vertical {{ background: transparent; width: 11px; margin: 3px; }}
    QScrollBar::handle:vertical {{
        background: {s['tertiary']}; border-radius: 5px; min-height: 26px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {s['border']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 3px; }}
    QScrollBar::handle:horizontal {{
        background: {s['tertiary']}; border-radius: 5px; min-width: 26px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QStatusBar {{ color: {s['text']}; background: {s['page']}; }}
    QDockWidget {{ background: {s['page']}; border: none; }}
    QDockWidget::title {{
        background: {s['page']};
        color: {s['text']};
        padding: 4px 8px;
    }}
    QSplitter::handle {{ background: {s['border']}; }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical {{ height: 1px; }}
    QToolTip {{
        background: {s['panel']};
        color: {s['text']};
        border: 1px solid {s['border']};
        border-radius: 4px;
        padding: 5px;
    }}
    """


def install(app):
    """Apply the Scratch palette, stylesheet, and typography to *app*."""
    from PySide6.QtGui import QColor, QPalette

    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(SCRATCH["page"]))
    palette.setColor(QPalette.WindowText, QColor(SCRATCH["text"]))
    palette.setColor(QPalette.Base, QColor(SCRATCH["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor(SCRATCH["secondary"]))
    palette.setColor(QPalette.Text, QColor(SCRATCH["text"]))
    palette.setColor(QPalette.Button, QColor(SCRATCH["panel"]))
    palette.setColor(QPalette.ButtonText, QColor(SCRATCH["text"]))
    palette.setColor(QPalette.Highlight, QColor(SCRATCH["selection"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(SCRATCH["muted"]))
    app.setPalette(palette)
    if hasattr(app, "setApplicationName"):
        app.setApplicationName("blockforge")


def category_color(key, default=None):
    """Return the primary palette color for a block category."""
    category = CATEGORY_BY_KEY.get(key)
    return category.color if category else (default or SCRATCH["accent"])


def block_colors(key):
    """Return ``(primary, secondary, tertiary)`` for a Scratch category."""
    return BLOCK_COLORS.get(key, BLOCK_COLORS["custom"])


def _stack_path(rect, hat=False, top=True, bottom=True):
    """Build Scratch's stack-block puzzle silhouette."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPainterPath

    x, y, width, height = rect.left(), rect.top(), rect.width(), rect.height()
    center = x + width / 2.0
    path = QPainterPath()
    if hat:
        path.moveTo(x + 16, y + height)
        path.lineTo(x + 16, y + 18)
        path.cubicTo(x + 16, y - 2, x + width - 16, y - 2,
                     x + width - 16, y + 18)
        path.lineTo(x + width - 16, y + height)
    elif top:
        path.moveTo(x, y + 7)
        path.quadTo(x, y, x + 7, y)
        path.lineTo(center - 9, y)
        path.cubicTo(center - 6, y + 9, center + 6, y + 9, center + 9, y)
        path.lineTo(x + width - 7, y)
        path.quadTo(x + width, y, x + width, y + 7)
    else:
        path.moveTo(x, y + 7)
        path.quadTo(x, y, x + 7, y)
        path.lineTo(x + width - 7, y)
        path.quadTo(x + width, y, x + width, y + 7)
    path.lineTo(x + width, y + height - 7)
    path.quadTo(x + width, y + height, x + width - 7, y + height)
    if bottom:
        path.lineTo(center + 9, y + height)
        path.cubicTo(center + 6, y + height + 9,
                     center - 6, y + height + 9, center - 9, y + height)
    path.lineTo(x + 7, y + height)
    path.quadTo(x, y + height, x, y + height - 7)
    path.closeSubpath()
    return path


def paint_block(painter, rect, key, hat=False, reporter=None,
                top=True, bottom=True):
    """Paint one Scratch block body with its exact category colors."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    primary, secondary, tertiary = block_colors(key)
    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    pen = QPen(QColor(tertiary), 1)
    body = QColor(primary)
    if reporter in ("boolean", "hexagon"):
        points = [
            rect.left() + 8, rect.center().y(),
            rect.left() + 16, rect.top() + 2,
            rect.right() - 16, rect.top() + 2,
            rect.right() - 8, rect.center().y(),
            rect.right() - 16, rect.bottom() - 2,
            rect.left() + 16, rect.bottom() - 2,
        ]
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        polygon = QPolygonF([QPointF(points[i], points[i + 1])
                             for i in range(0, len(points), 2)])
        painter.setBrush(body)
        painter.setPen(pen)
        painter.drawPolygon(polygon)
    elif reporter:
        painter.setBrush(body)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)
    else:
        path = _stack_path(rect, hat=hat, top=top, bottom=bottom)
        painter.setPen(pen)
        painter.setBrush(body)
        painter.drawPath(path)
        # Scratch uses a subtle lighter top edge on stack blocks.
        painter.setPen(QPen(QColor(secondary), 1))
        painter.drawLine(rect.left() + 10, rect.top() + 2,
                         rect.right() - 10, rect.top() + 2)
    painter.restore()


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
        % (SCRATCH["text"], path)
    )


def icon(name, color=None):
    """Build a QIcon from an inline SVG glyph."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    markup = glyph(name)
    if color:
        markup = markup.replace(SCRATCH["text"], color)
    renderer = QSvgRenderer(markup.encode("utf-8"))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    renderer.render(QPainter(pixmap))
    return QIcon(pixmap)
