"""Thin PySide6 window for hashcheck.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import sys

from core import ALGOS, HashcheckError, hash_file, verify as hashes_match

NAME = "hashcheck"
VERSION = "0.1.0"
USAGE = "usage: hashcheck [--help | --version]"


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
    """Build and return the hashcheck window (Qt imported here only)."""
    from PySide6 import QtWidgets

    class HashcheckWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.current_hash = ""
            self.setWindowTitle(NAME)
            self.setMinimumWidth(420)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            self.choose_button = QtWidgets.QPushButton("Choose File")
            self.choose_button.clicked.connect(self.choose_file)
            layout.addWidget(self.choose_button)

            self.path_label = QtWidgets.QLabel("No file chosen")
            self.path_label.setWordWrap(True)
            layout.addWidget(self.path_label)

            self.algo_combo = QtWidgets.QComboBox()
            self.algo_combo.addItems(ALGOS)
            layout.addWidget(self.algo_combo)

            self.compute_button = QtWidgets.QPushButton("Compute")
            self.compute_button.clicked.connect(self.compute)
            layout.addWidget(self.compute_button)

            self.expected_edit = QtWidgets.QLineEdit()
            self.expected_edit.setPlaceholderText("Expected hash")
            layout.addWidget(self.expected_edit)

            self.verify_button = QtWidgets.QPushButton("Verify")
            self.verify_button.clicked.connect(self.verify)
            layout.addWidget(self.verify_button)

            self.result_label = QtWidgets.QLabel("")
            self.result_label.setWordWrap(True)
            layout.addWidget(self.result_label)

        def set_path(self, path):
            self.path_label.setText(path)
            self.current_hash = ""
            self.result_label.setText("")

        def choose_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose File")
            if path:
                self.set_path(path)

        def compute(self):
            path = self.path_label.text()
            if not path or path == "No file chosen":
                self.result_label.setText("Choose a file first.")
                QtWidgets.QMessageBox.warning(self, NAME, "Choose a file first.")
                return
            try:
                self.current_hash = hash_file(
                    path, self.algo_combo.currentText()
                )
            except (HashcheckError, OSError) as exc:
                self.result_label.setText(str(exc))
                QtWidgets.QMessageBox.warning(self, NAME, str(exc))
                return
            self.result_label.setText(self.current_hash)

        def verify(self):
            if not self.current_hash:
                self.result_label.setText("Compute a hash first.")
                QtWidgets.QMessageBox.warning(self, NAME, "Compute a hash first.")
                return
            matches = hashes_match(self.expected_edit.text(), self.current_hash)
            self.result_label.setText("Match" if matches else "Mismatch")

    return HashcheckWindow()


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
