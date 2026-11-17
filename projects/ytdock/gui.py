"""Dark, minimal PySide6 GUI for ytdock.

Qt is imported lazily inside :func:`main` / :func:`build_window` so that
``--help`` and ``--version`` work on a machine with no display server.
"""

import os
import shlex
import sys

import core
import theme

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
            theme.polish(self, "ytdock")
            self.outdir = os.path.expanduser("~")
            self.process = None
            self.setWindowTitle("ytdock")
            self.setMinimumWidth(520)
            self._build()

        def _build(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header("ytdock", "A quiet dock for yt-dlp downloads"))

            download_card = theme.card("DOWNLOAD")
            self.url_edit = QtWidgets.QLineEdit()
            self.url_edit.setPlaceholderText("https://…")
            self.mode_combo = QtWidgets.QComboBox()
            self.mode_combo.addItems(core.MODES)
            download_card.layout().addWidget(theme.field("Video URL", self.url_edit))
            download_card.layout().addWidget(theme.field("Preset", self.mode_combo))

            folder_row = QtWidgets.QHBoxLayout()
            self.folder_button = theme.button("Choose folder", "folder")
            self.folder_label = theme.label(self.outdir, "status")
            folder_row.addWidget(self.folder_button)
            folder_row.addWidget(self.folder_label, 1)
            download_card.layout().addLayout(folder_row)
            outer.addWidget(download_card)

            actions = QtWidgets.QHBoxLayout()
            self.cancel_button = theme.button("Cancel", "cancel")
            self.download_button = theme.button("Download", "download", accent=True)
            actions.addWidget(self.cancel_button)
            actions.addStretch(1)
            actions.addWidget(self.download_button)
            outer.addLayout(actions)

            log_card = theme.card("ACTIVITY")
            self.log_pane = QtWidgets.QTextEdit()
            self.log_pane.setReadOnly(True)
            self.log_pane.setMinimumHeight(170)
            font = self.log_pane.font()
            font.setFamily("Adwaita Mono, DejaVu Sans Mono, monospace")
            font.setPointSize(10)
            self.log_pane.setFont(font)
            log_card.layout().addWidget(self.log_pane)
            outer.addWidget(log_card)

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
                self.folder_label.setText(folder)
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
    theme.install(app)
    window = build_window()
    window.show()
    return app.exec()
