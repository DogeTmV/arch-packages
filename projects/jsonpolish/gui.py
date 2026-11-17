"""Dark, minimal PySide6 window for jsonpolish.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import sys

from core import JsonpolishError, format_json, minify_json, validate_json
import theme

NAME = "jsonpolish"
VERSION = "0.1.0"
USAGE = "usage: jsonpolish [--help | --version]"


def early_exit(argv):
    """Return an exit code for informational flags, otherwise None."""
    if "--help" in argv or "-h" in argv:
        print(USAGE)
        return 0
    if "--version" in argv:
        print("%s %s" % (NAME, VERSION))
        return 0
    return None


def create_window():
    """Build and return the jsonpolish window (Qt imported here only)."""
    from PySide6 import QtWidgets

    class JsonpolishWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            theme.polish(self, NAME)
            self.setWindowTitle(NAME)
            self.setMinimumSize(600, 440)
            self._build()

        def _build(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Tidy JSON without leaving the desktop"))

            editor_card = theme.card("JSON")
            self.text_edit = QtWidgets.QPlainTextEdit()
            self.text_edit.setPlaceholderText("Paste JSON here…")
            font = self.text_edit.font()
            font.setFamily("Adwaita Mono, DejaVu Sans Mono, monospace")
            font.setPointSize(11)
            self.text_edit.setFont(font)
            editor_card.layout().addWidget(self.text_edit)
            outer.addWidget(editor_card)

            actions = QtWidgets.QHBoxLayout()
            self.format_button = theme.button("Format", "format", accent=True)
            self.minify_button = theme.button("Minify", "minify")
            self.copy_button = theme.button("Copy", "copy")
            self.clear_button = theme.button("Clear", "trash", flat=True)
            for control in (self.format_button, self.minify_button,
                            self.copy_button, self.clear_button):
                actions.addWidget(control)
            actions.addStretch(1)
            outer.addLayout(actions)

            self.status_label = theme.label("Ready", "status")
            outer.addWidget(self.status_label)

            self.format_button.clicked.connect(self.format_text)
            self.minify_button.clicked.connect(self.minify_text)
            self.copy_button.clicked.connect(self.copy_text)
            self.clear_button.clicked.connect(self.clear_text)

        def show_error(self, message):
            self.status_label.setText(message)
            QtWidgets.QMessageBox.warning(self, NAME, message)

        def format_text(self):
            text = self.text_edit.toPlainText()
            try:
                result = format_json(text)
            except JsonpolishError as exc:
                self.show_error(str(exc))
                return
            self.text_edit.setPlainText(result)
            self.status_label.setText("Valid JSON (formatted)")

        def minify_text(self):
            text = self.text_edit.toPlainText()
            try:
                result = minify_json(text)
            except JsonpolishError as exc:
                self.show_error(str(exc))
                return
            self.text_edit.setPlainText(result)
            self.status_label.setText("Valid JSON (minified)")

        def copy_text(self):
            text = self.text_edit.toPlainText()
            if not text:
                self.status_label.setText("Nothing to copy")
                return
            QtWidgets.QApplication.clipboard().setText(text)
            self.status_label.setText("Copied to clipboard")

        def clear_text(self):
            self.text_edit.clear()
            self.status_label.setText("Cleared")

    return JsonpolishWindow()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    status = early_exit(argv)
    if status is not None:
        return status
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(argv)
    theme.install(app)
    window = create_window()
    window.show()
    return app.exec()
