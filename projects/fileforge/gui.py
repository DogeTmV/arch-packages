"""Thin PySide6 GUI for fileforge.

Qt is imported lazily inside :func:`main` / :func:`build_window` so that
``--help`` and ``--version`` work on a machine with no display server.
"""

import os
import sys

import core

VERSION = core.VERSION
USAGE = "usage: fileforge [--help | --version]"


def early_exit(argv=None):
    """Return (message, code) for help/version, otherwise None."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        return USAGE, 0
    if "--version" in args:
        return "fileforge " + VERSION, 0
    return None


def build_window():
    """Create and return the main window (PySide6 imported on demand)."""
    from PySide6 import QtCore, QtWidgets

    class FileforgeWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.source = ""
            self.process = None
            self.setWindowTitle("fileforge")
            self.setMinimumWidth(420)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            top = QtWidgets.QHBoxLayout()
            self.open_button = QtWidgets.QPushButton("Open…")
            self.path_label = QtWidgets.QLabel("No file selected")
            self.path_label.setWordWrap(True)
            top.addWidget(self.open_button)
            top.addWidget(self.path_label, 1)
            layout.addLayout(top)

            self.format_combo = QtWidgets.QComboBox()
            layout.addWidget(self.format_combo)

            self.convert_button = QtWidgets.QPushButton("Convert")
            layout.addWidget(self.convert_button)

            self.status_label = QtWidgets.QLabel("Ready")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

            self.open_button.clicked.connect(self.choose_file)
            self.convert_button.clicked.connect(self.convert)

        def choose_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open file")
            if not path:
                return
            self.source = path
            self.path_label.setText(path)
            targets = core.supported_targets(path)
            self.format_combo.clear()
            self.format_combo.addItems(targets)
            if targets:
                self.status_label.setText("Ready to convert to %s" % targets[0])
            else:
                self.status_label.setText("No conversions available for this file")

        def convert(self):
            if not self.source:
                QtWidgets.QMessageBox.warning(self, "fileforge", "Choose a file first.")
                return
            target = self.format_combo.currentText()
            if not target:
                QtWidgets.QMessageBox.warning(self, "fileforge", "Choose a target format.")
                return
            destination, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save converted file", filter="%s file (*%s)" % (target, target))
            if not destination:
                return
            if not destination.lower().endswith(target):
                destination += target

            if target in core.TEXT_EXTS:
                try:
                    core.convert_file(self.source, destination)
                    self.status_label.setText("Saved %s" % destination)
                except core.ConversionError as exc:
                    QtWidgets.QMessageBox.critical(self, "fileforge", str(exc))
                    self.status_label.setText("Conversion failed")
                return

            command = core.build_media_command(self.source, destination)
            process = QtCore.QProcess(self)
            process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            process.finished.connect(
                lambda code, _status, dest=destination: self._on_finished(code, dest))
            self.process = process
            self.status_label.setText("Converting…")
            process.start()

        def _on_finished(self, code, destination):
            if code == 0:
                self.status_label.setText("Saved %s" % destination)
            else:
                self.status_label.setText("ffmpeg failed (exit %s)" % code)

    return FileforgeWindow()


def main(argv=None):
    early = early_exit(argv)
    if early is not None:
        message, code = early
        print(message)
        return code

    from PySide6 import QtWidgets

    args = list(sys.argv if argv is None else argv)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    window = build_window()
    window.show()
    return app.exec()
