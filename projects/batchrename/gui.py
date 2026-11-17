"""Thin PySide6 window for batchrename.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import os
import sys

from core import BatchrenameError, apply_plan, build_plan

NAME = "batchrename"
VERSION = "0.1.0"
USAGE = "usage: batchrename [--help | --version]"


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
    """Build and return the batchrename window (Qt imported here only)."""
    from PySide6 import QtWidgets

    class BatchrenameWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.paths = []
            self.setWindowTitle(NAME)
            self.setMinimumWidth(520)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            self.add_button = QtWidgets.QPushButton("Add Files")
            self.add_button.clicked.connect(self.add_files)
            layout.addWidget(self.add_button)

            self.pattern_edit = QtWidgets.QLineEdit("{name}_{nn}")
            self.pattern_edit.setPlaceholderText(
                "Pattern: {name}, {n}, {nn}, {ext}"
            )
            layout.addWidget(self.pattern_edit)

            self.start_spin = QtWidgets.QSpinBox()
            self.start_spin.setRange(1, 999999)
            self.start_spin.setValue(1)
            layout.addWidget(self.start_spin)

            self.preview_button = QtWidgets.QPushButton("Preview")
            self.preview_button.clicked.connect(self.preview)
            layout.addWidget(self.preview_button)

            self.preview_list = QtWidgets.QListWidget()
            layout.addWidget(self.preview_list)

            self.rename_button = QtWidgets.QPushButton("Rename")
            self.rename_button.clicked.connect(self.rename)
            layout.addWidget(self.rename_button)

            self.status_label = QtWidgets.QLabel("No files selected")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

        def set_paths(self, paths):
            self.paths = [os.fspath(path) for path in paths]
            self.preview_list.clear()
            self.status_label.setText("%d file(s) selected" % len(self.paths))

        def add_files(self):
            paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Add Files")
            if paths:
                self.set_paths(self.paths + list(paths))

        def current_plan(self):
            return build_plan(
                self.paths, self.pattern_edit.text(), self.start_spin.value()
            )

        def show_error(self, message):
            self.status_label.setText(message)
            QtWidgets.QMessageBox.warning(self, NAME, message)

        def preview(self):
            self.preview_list.clear()
            if not self.paths:
                self.status_label.setText("Add files first.")
                return
            try:
                plan = self.current_plan()
            except BatchrenameError as exc:
                self.show_error(str(exc))
                return
            for source, destination in plan:
                self.preview_list.addItem(
                    "%s -> %s"
                    % (os.path.basename(source), os.path.basename(destination))
                )
            self.status_label.setText("Preview: %d rename(s)" % len(plan))

        def rename(self):
            if not self.paths:
                self.status_label.setText("Add files first.")
                return
            try:
                applied = apply_plan(self.current_plan())
            except (BatchrenameError, OSError) as exc:
                self.show_error(str(exc))
                return
            self.set_paths([])
            self.status_label.setText("Renamed %d file(s)" % len(applied))

    return BatchrenameWindow()


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
