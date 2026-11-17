"""Thin PySide6 window for jsonpolish.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import sys

from core import JsonpolishError, format_json, minify_json, validate_json

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
            self.setWindowTitle(NAME)
            self.resize(620, 460)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            self.text_edit = QtWidgets.QPlainTextEdit()
            self.text_edit.setPlaceholderText("Paste JSON here")
            layout.addWidget(self.text_edit)

            self.format_button = QtWidgets.QPushButton("Format")
            self.format_button.clicked.connect(self.format_text)
            layout.addWidget(self.format_button)

            self.minify_button = QtWidgets.QPushButton("Minify")
            self.minify_button.clicked.connect(self.minify_text)
            layout.addWidget(self.minify_button)

            self.copy_button = QtWidgets.QPushButton("Copy")
            self.copy_button.clicked.connect(self.copy_text)
            layout.addWidget(self.copy_button)

            self.clear_button = QtWidgets.QPushButton("Clear")
            self.clear_button.clicked.connect(self.clear_text)
            layout.addWidget(self.clear_button)

            self.status_label = QtWidgets.QLabel("Ready")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

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
    window = create_window()
    window.show()
    return app.exec()
