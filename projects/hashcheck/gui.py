"""Dark, minimal PySide6 window for hashcheck.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import sys

from core import ALGOS, HashcheckError, hash_file, verify as hashes_match
import theme

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
            theme.polish(self, NAME)
            self.current_hash = ""
            self.setWindowTitle(NAME)
            self.setMinimumWidth(430)
            self._build()

        def _build(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Compute and verify file fingerprints"))

            source_card = theme.card("SOURCE FILE")
            source_row = QtWidgets.QHBoxLayout()
            self.choose_button = theme.button("Choose file", "folder")
            self.path_label = theme.label("No file chosen", "status")
            source_row.addWidget(self.choose_button)
            source_row.addWidget(self.path_label, 1)
            source_card.layout().addLayout(source_row)
            outer.addWidget(source_card)

            hash_card = theme.card("DIGEST")
            self.algo_combo = QtWidgets.QComboBox()
            self.algo_combo.addItems(ALGOS)
            compute_row = QtWidgets.QHBoxLayout()
            compute_row.addWidget(theme.field("Algorithm", self.algo_combo), 1)
            self.compute_button = theme.button("Compute", "calc", accent=True)
            compute_row.addWidget(self.compute_button)
            hash_card.layout().addLayout(compute_row)
            outer.addWidget(hash_card)

            verify_card = theme.card("COMPARE")
            self.expected_edit = QtWidgets.QLineEdit()
            self.expected_edit.setPlaceholderText("Paste the expected hash…")
            verify_row = QtWidgets.QHBoxLayout()
            verify_row.addWidget(theme.field("Expected value", self.expected_edit), 1)
            self.verify_button = theme.button("Verify", "check")
            verify_row.addWidget(self.verify_button)
            verify_card.layout().addLayout(verify_row)
            outer.addWidget(verify_card)

            self.result_label = theme.label("Awaiting a file", "value")
            from PySide6.QtCore import Qt
            self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer.addWidget(self.result_label)
            outer.addStretch(1)

            self.choose_button.clicked.connect(self.choose_file)
            self.compute_button.clicked.connect(self.compute)
            self.verify_button.clicked.connect(self.verify)

        def set_path(self, path):
            self.path_label.setText(path)
            self.current_hash = ""
            self.result_label.setText("Awaiting a file")

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
    theme.install(app)
    window = create_window()
    window.show()
    return app.exec()
