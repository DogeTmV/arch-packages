"""Dark, minimal PySide6 GUI for cutframe.

Qt is imported lazily inside :func:`main` / :func:`build_window` so that
``--help`` and ``--version`` work on a machine with no display server.
"""

import os
import sys

import core
import theme

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
            theme.polish(self, "cutframe")
            self.source = ""
            self.process = None
            self.setWindowTitle("cutframe")
            self.setMinimumWidth(470)
            self._build()

        def _build(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header("cutframe", "Cut, crop and export video clips"))

            source_card = theme.card("SOURCE VIDEO")
            source_row = QtWidgets.QHBoxLayout()
            self.open_button = theme.button("Open video", "folder")
            self.file_label = theme.label("No video selected", "status")
            source_row.addWidget(self.open_button)
            source_row.addWidget(self.file_label, 1)
            source_card.layout().addLayout(source_row)
            outer.addWidget(source_card)

            edit_card = theme.card("EDIT")
            toolbar = QtWidgets.QHBoxLayout()
            self.cut_button = theme.button("Cut", "scissors")
            self.crop_button = theme.button("Crop", "crop")
            self.export_button = theme.button("Export", "export", accent=True)
            toolbar.addWidget(self.cut_button)
            toolbar.addWidget(self.crop_button)
            toolbar.addStretch(1)
            toolbar.addWidget(self.export_button)
            edit_card.layout().addLayout(toolbar)

            self.cut_panel = QtWidgets.QFrame()
            self.cut_panel.setObjectName("panel")
            cut_layout = QtWidgets.QHBoxLayout(self.cut_panel)
            cut_layout.setContentsMargins(14, 12, 14, 12)
            cut_layout.setSpacing(12)
            self.start_spin = QtWidgets.QDoubleSpinBox()
            self.start_spin.setRange(0.0, 100000.0)
            self.start_spin.setDecimals(2)
            self.start_spin.setSuffix(" s")
            self.length_spin = QtWidgets.QDoubleSpinBox()
            self.length_spin.setRange(0.1, 100000.0)
            self.length_spin.setDecimals(2)
            self.length_spin.setValue(5.0)
            self.length_spin.setSuffix(" s")
            self.start_label = theme.label("Start", "field")
            self.length_label = theme.label("Length", "field")
            cut_layout.addWidget(theme.field("Start", self.start_spin))
            cut_layout.addWidget(theme.field("Length", self.length_spin))
            self.cut_panel.setVisible(False)
            edit_card.layout().addWidget(self.cut_panel)

            self.crop_panel = QtWidgets.QFrame()
            self.crop_panel.setObjectName("panel")
            crop_layout = QtWidgets.QHBoxLayout(self.crop_panel)
            crop_layout.setContentsMargins(14, 12, 14, 12)
            crop_layout.setSpacing(10)
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
                crop_layout.addWidget(theme.field(label, spin))
            self.crop_panel.setVisible(False)
            edit_card.layout().addWidget(self.crop_panel)
            outer.addWidget(edit_card)

            self.status_label = theme.label("Open a video to begin", "status")
            outer.addWidget(self.status_label)
            outer.addStretch(1)

            self.open_button.clicked.connect(self.open_file)
            self.cut_button.clicked.connect(self.toggle_cut)
            self.crop_button.clicked.connect(self.toggle_crop)
            self.export_button.clicked.connect(self.export)

        def toggle_cut(self):
            self.cut_panel.setVisible(not self.cut_panel.isVisible())

        def toggle_crop(self):
            self.crop_panel.setVisible(not self.crop_panel.isVisible())

        def open_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open video", filter="Video files (*.mp4 *.mkv *.mov *.avi *.webm)")
            if not path:
                return
            self.source = path
            self.file_label.setText(os.path.basename(path))
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
    theme.install(app)
    window = build_window()
    window.show()
    return app.exec()
