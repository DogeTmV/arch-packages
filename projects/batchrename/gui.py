"""Dark, minimal PySide6 window for batchrename.

Qt is imported only when the GUI is actually launched, so --help and
--version work on a machine with no display server.
"""

import os
import sys

from core import BatchrenameError, apply_plan, build_plan
import theme

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
            theme.polish(self, NAME)
            self.paths = []
            self.setWindowTitle(NAME)
            self.setMinimumWidth(540)
            self._build()

        def _build(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Rename a whole folder in one pass"))

            files_card = theme.card("FILES")
            file_row = QtWidgets.QHBoxLayout()
            self.add_button = theme.button("Add files", "add")
            self.file_label = theme.label("No files selected", "status")
            file_row.addWidget(self.add_button)
            file_row.addWidget(self.file_label, 1)
            files_card.layout().addLayout(file_row)
            outer.addWidget(files_card)

            pattern_card = theme.card("NAMING PATTERN")
            self.pattern_edit = QtWidgets.QLineEdit("{name}_{nn}")
            self.pattern_edit.setPlaceholderText(
                "Tokens: {name}, {n}, {nn}, {ext}"
            )
            self.start_spin = QtWidgets.QSpinBox()
            self.start_spin.setRange(1, 999999)
            self.start_spin.setValue(1)
            pattern_row = QtWidgets.QHBoxLayout()
            pattern_row.addWidget(theme.field("Pattern", self.pattern_edit), 1)
            pattern_row.addWidget(theme.field("Start at", self.start_spin))
            pattern_card.layout().addLayout(pattern_row)
            self.preview_button = theme.button("Preview", "eye")
            pattern_card.layout().addWidget(self.preview_button)
            outer.addWidget(pattern_card)

            preview_card = theme.card("PREVIEW")
            self.preview_list = QtWidgets.QListWidget()
            self.preview_list.setMinimumHeight(130)
            preview_card.layout().addWidget(self.preview_list)
            outer.addWidget(preview_card)

            actions = QtWidgets.QHBoxLayout()
            self.status_label = theme.label("No files selected", "status")
            self.rename_button = theme.button("Rename files", "pencil", accent=True)
            actions.addWidget(self.status_label, 1)
            actions.addWidget(self.rename_button)
            outer.addLayout(actions)

            self.add_button.clicked.connect(self.add_files)
            self.preview_button.clicked.connect(self.preview)
            self.rename_button.clicked.connect(self.rename)

        def set_paths(self, paths):
            self.paths = [os.fspath(path) for path in paths]
            self.file_label.setText("%d file(s) in the queue" % len(self.paths))
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
    theme.install(app)
    window = create_window()
    window.show()
    return app.exec()
