"""LanBridge dark theme (PySide6 imported lazily)."""

BG = "#0b0f14"
SURFACE = "#121923"
SURFACE_ALT = "#172232"
BORDER = "#243244"
TEXT = "#e6edf6"
MUTED = "#9fb0c3"
ACCENT = "#4da3ff"
ACCENT_2 = "#22c55e"
DANGER = "#ef4444"
WARN = "#f59e0b"


def apply(app):
    from PySide6 import QtGui, QtWidgets

    app.setStyle("Fusion")
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.Window, QtGui.QColor(BG))
    pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Base, QtGui.QColor(SURFACE))
    pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(SURFACE_ALT))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Button, QtGui.QColor(SURFACE_ALT))
    pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(SURFACE_ALT))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(ACCENT))
    pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#081018"))
    pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(MUTED))
    app.setPalette(pal)
    app.setStyleSheet(f"""
        QWidget {{ color: {TEXT}; background: {BG}; font-size: 13px; }}
        QMainWindow, QDialog {{ background: {BG}; }}
        QFrame#card, QGroupBox {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
        }}
        QGroupBox {{ margin-top: 10px; padding: 12px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {MUTED}; }}
        QLabel#muted {{ color: {MUTED}; }}
        QLabel#title {{ font-size: 20px; font-weight: 700; }}
        QLabel#pill {{
            background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 10px; padding: 4px 10px; color: {MUTED};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QListWidget, QTableWidget {{
            background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px; selection-background-color: {ACCENT};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QPushButton {{
            background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 12px; font-weight: 600;
        }}
        QPushButton:hover {{ border-color: {ACCENT}; background: #1b2a3d; }}
        QPushButton:pressed {{ background: #22354d; }}
        QPushButton[variant="primary"] {{ background: {ACCENT}; color: #081018; border-color: {ACCENT}; }}
        QPushButton[variant="primary"]:hover {{ background: #6bb6ff; }}
        QPushButton[variant="danger"] {{ background: #3a1820; border-color: #5b2230; color: #ffd7dd; }}
        QPushButton[variant="success"] {{ background: #143222; border-color: #1f5136; color: #d9ffe9; }}
        QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 12px; background: {SURFACE}; top: -1px; }}
        QTabBar::tab {{
            background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-bottom: none; padding: 8px 14px; margin-right: 4px;
            border-top-left-radius: 10px; border-top-right-radius: 10px; color: {MUTED};
        }}
        QTabBar::tab:selected {{ background: {SURFACE}; color: {TEXT}; }}
        QStatusBar {{ background: {SURFACE}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
        QScrollArea {{ border: none; background: transparent; }}
        QSplitter::handle {{ background: {BORDER}; }}
        QHeaderView::section {{ background: {SURFACE_ALT}; color: {MUTED}; border: 1px solid {BORDER}; padding: 6px; }}
    """)


def make_button(text: str, variant: Optional[str] = None):
    from PySide6 import QtWidgets
    b = QtWidgets.QPushButton(text)
    if variant:
        b.setProperty("variant", variant)
    return b
