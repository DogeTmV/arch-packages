"""Thin PySide6 GUI for ytdock.

Qt is imported lazily inside :func:`main` / :func:`build_window` so that
``--help`` and ``--version`` work on a machine with no display server.
"""

import os
import shlex
import sys

import core

VERSION = core.VERSION
USAGE = "usage: ytdock [--help | --version]"


def early_exit(argv=None):
    """Return (message, code) for help/version, otherwise None."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        return USAGE, 0
    if "--version" in args:
        return "ytdock " + VERSION, 0
    return None


def build_window():
    """Create and return the main window (PySide6 imported on demand)."""
    from PySide6 import QtCore, QtWidgets

    class YtdockWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.outdir = os.path.expanduser("~")
            self.process = None
            self.setWindowTitle("ytdock")
            self.setMinimumWidth(520)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            self.url_edit = QtWidgets.QLineEdit()
            self.url_edit.setPlaceholderText("https://…")
            layout.addWidget(self.url_edit)

            self.mode_combo = QtWidgets.QComboBox()
            self.mode_combo.addItems(core.MODES)
            layout.addWidget(self.mode_combo)

            self.folder_button = QtWidgets.QPushButton("Choose Folder…")
            layout.addWidget(self.folder_button)

            buttons = QtWidgets.QHBoxLayout()
            self.download_button = QtWidgets.QPushButton("Download")
            self.cancel_button = QtWidgets.QPushButton("Cancel")
            buttons.addWidget(self.download_button)
            buttons.addWidget(self.cancel_button)
            layout.addLayout(buttons)

            self.log_pane = QtWidgets.QTextEdit()
            self.log_pane.setReadOnly(True)
            self.log_pane.setMinimumHeight(180)
            layout.addWidget(self.log_pane)

            self.folder_button.clicked.connect(self.choose_folder)
            self.download_button.clicked.connect(self.download)
            self.cancel_button.clicked.connect(self.cancel)

        def _log(self, text):
            self.log_pane.append(str(text))

        def choose_folder(self):
            folder = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Choose output folder", self.outdir)
            if folder:
                self.outdir = folder
                self._log("Output folder: %s" % folder)

        def download(self):
            url = self.url_edit.text().strip()
            mode = self.mode_combo.currentText()
            try:
                command = core.build_command(url, mode, self.outdir)
            except core.DownloadError as exc:
                QtWidgets.QMessageBox.critical(self, "ytdock", str(exc))
                return

            self._log("$ %s" % shlex.join(command))
            process = QtCore.QProcess(self)
            process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            process.readyRead.connect(
                lambda proc=process: self._read_output(proc))
            process.finished.connect(
                lambda code, _status, proc=process: self._on_finished(proc, code))
            self.process = process
            process.start()

        def _read_output(self, process):
            raw = bytes(process.readAll()).decode("utf-8", "replace")
            for line in raw.splitlines():
                if not line.strip():
                    continue
                self._log(line)
                progress = core.parse_progress(line)
                if progress is not None:
                    self._log("  → %.1f%% complete" % progress)

        def _on_finished(self, process, code):
            self._log("Finished with exit code %s" % code)

        def cancel(self):
            if (self.process is not None
                    and self.process.state() != QtCore.QProcess.NotRunning):
                self.process.kill()
                self._log("Cancelled")

    return YtdockWindow()


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
