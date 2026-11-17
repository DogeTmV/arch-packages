"""Thin PySide6 GUI for cutframe.

Qt is imported lazily inside :func:`main` / :func:`build_window` so that
``--help`` and ``--version`` work on a machine with no display server.
"""

import os
import sys

import core

VERSION = core.VERSION
USAGE = "usage: cutframe [--help | --version]"


def early_exit(argv=None):
    """Return (message, code) for help/version, otherwise None."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        return USAGE, 0
    if "--version" in args:
        return "cutframe " + VERSION, 0
    return None


def build_window():
    """Create and return the main window (PySide6 imported on demand)."""
    from PySide6 import QtCore, QtWidgets

    class CutframeWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.source = ""
            self.process = None
            self.setWindowTitle("cutframe")
            self.setMinimumWidth(420)
            self._build()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)

            buttons = QtWidgets.QHBoxLayout()
            self.open_button = QtWidgets.QPushButton("Open")
            self.cut_button = QtWidgets.QPushButton("Cut")
            self.crop_button = QtWidgets.QPushButton("Crop")
            self.export_button = QtWidgets.QPushButton("Export")
            for button in (self.open_button, self.cut_button,
                           self.crop_button, self.export_button):
                buttons.addWidget(button)
            layout.addLayout(buttons)

            self.cut_panel = QtWidgets.QWidget()
            cut_layout = QtWidgets.QHBoxLayout(self.cut_panel)
            cut_layout.setContentsMargins(0, 0, 0, 0)
            self.start_spin = QtWidgets.QDoubleSpinBox()
            self.start_spin.setRange(0.0, 100000.0)
            self.start_spin.setDecimals(2)
            self.start_spin.setSuffix(" s")
            self.length_spin = QtWidgets.QDoubleSpinBox()
            self.length_spin.setRange(0.1, 100000.0)
            self.length_spin.setDecimals(2)
            self.length_spin.setValue(5.0)
            self.length_spin.setSuffix(" s")
            self.start_label = QtWidgets.QLabel("Start")
            self.length_label = QtWidgets.QLabel("Length")
            cut_layout.addWidget(self.start_label)
            cut_layout.addWidget(self.start_spin)
            cut_layout.addWidget(self.length_label)
            cut_layout.addWidget(self.length_spin)
            self.cut_panel.setVisible(False)
            layout.addWidget(self.cut_panel)

            self.crop_panel = QtWidgets.QWidget()
            crop_layout = QtWidgets.QHBoxLayout(self.crop_panel)
            crop_layout.setContentsMargins(0, 0, 0, 0)
            self.x_spin = QtWidgets.QSpinBox()
            self.y_spin = QtWidgets.QSpinBox()
            self.w_spin = QtWidgets.QSpinBox()
            self.h_spin = QtWidgets.QSpinBox()
            for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
                spin.setRange(0, 100000)
            self.w_spin.setMinimum(1)
            self.h_spin.setMinimum(1)
            self.w_spin.setValue(640)
            self.h_spin.setValue(480)
            for label, spin in (("X", self.x_spin), ("Y", self.y_spin),
                                ("W", self.w_spin), ("H", self.h_spin)):
                crop_layout.addWidget(QtWidgets.QLabel(label))
                crop_layout.addWidget(spin)
            self.crop_panel.setVisible(False)
            layout.addWidget(self.crop_panel)

            self.status_label = QtWidgets.QLabel("Open a video to begin")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

            self.open_button.clicked.connect(self.open_file)
            self.cut_button.clicked.connect(
                lambda: self.cut_panel.setVisible(not self.cut_panel.isVisible()))
            self.crop_button.clicked.connect(
                lambda: self.crop_panel.setVisible(not self.crop_panel.isVisible()))
            self.export_button.clicked.connect(self.export)

        def open_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open video", filter="Video files (*.mp4 *.mkv *.mov *.avi *.webm)")
            if not path:
                return
            self.source = path
            self.status_label.setText("Probing %s…" % os.path.basename(path))
            command = core.build_probe_command(path)
            process = QtCore.QProcess(self)
            process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            process.finished.connect(
                lambda _code, _status, proc=process, src=path: self._probe_finished(proc, src))
            self.process = process
            process.start()

        def _probe_finished(self, process, source):
            raw = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
            try:
                width, height, duration = core.parse_probe_output(raw)
            except core.MediaError as exc:
                self.status_label.setText(str(exc))
                return
            self.w_spin.setValue(width)
            self.h_spin.setValue(height)
            self.status_label.setText("%s — %dx%d, %.1f s"
                                      % (os.path.basename(source), width, height, duration))

        def export(self):
            if not self.source:
                QtWidgets.QMessageBox.warning(self, "cutframe", "Open a video first.")
                return
            destination, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export video", filter="Video (*.mp4 *.mkv *.mov)")
            if not destination:
                return
            if os.path.splitext(destination)[1].lower() not in core.OUTPUT_EXTS:
                destination += ".mp4"
            crop = None
            if self.crop_panel.isVisible():
                crop = {"x": self.x_spin.value(), "y": self.y_spin.value(),
                        "w": self.w_spin.value(), "h": self.h_spin.value()}
            try:
                command = core.build_command(
                    self.source, self.start_spin.value(), self.length_spin.value(),
                    crop, destination)
            except core.MediaError as exc:
                QtWidgets.QMessageBox.critical(self, "cutframe", str(exc))
                return

            process = QtCore.QProcess(self)
            process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            process.finished.connect(
                lambda code, _status, dest=destination: self._export_finished(code, dest))
            self.process = process
            self.status_label.setText("Exporting…")
            process.start()

        def _export_finished(self, code, destination):
            if code == 0:
                self.status_label.setText("Saved %s" % destination)
            else:
                self.status_label.setText("ffmpeg failed (exit %s)" % code)

    return CutframeWindow()


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
