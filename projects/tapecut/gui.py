"""Dark, minimal PySide6 GUI for tapecut (one-button tape deck styling)."""

import argparse
import os
import sys

import core
import theme

NAME = "tapecut"
VERSION = core.VERSION


def build_parser():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Trim a piece of an audio file with a one-button tape deck GUI.")
    parser.add_argument("--version", action="version",
                        version="%s %s" % (NAME, VERSION))
    return parser


def create_window():
    """Build the main window.

    Qt is imported here rather than at module scope so that ``--help`` and
    ``--version`` work without a display.
    """
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import (QDoubleSpinBox, QFileDialog, QHBoxLayout,
                                   QVBoxLayout, QWidget)

    class TapecutWindow(QWidget):
        def __init__(self):
            super().__init__()
            theme.polish(self, NAME)
            self.setWindowTitle(NAME)
            self.setMinimumWidth(430)
            self.path = ""
            self._probe_process = None
            self._export_process = None
            self._player_process = None
            self._build()

        def _build(self):
            outer = QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Trim a clean clip from any audio file"))

            source_card = theme.card("SOURCE")
            source_row = QHBoxLayout()
            self.open_button = theme.button("Open audio", "folder")
            self.file_label = theme.label("No file loaded", "status")
            source_row.addWidget(self.open_button)
            source_row.addWidget(self.file_label, 1)
            source_card.layout().addLayout(source_row)
            outer.addWidget(source_card)

            trim_card = theme.card("SELECTION")
            self.start_spin = QDoubleSpinBox()
            self.start_spin.setPrefix("Start ")
            self.start_spin.setSuffix(" s")
            self.start_spin.setDecimals(2)
            self.start_spin.setMaximum(100000.0)
            self.start_spin.setToolTip("Start time in seconds")
            self.length_spin = QDoubleSpinBox()
            self.length_spin.setPrefix("Length ")
            self.length_spin.setSuffix(" s")
            self.length_spin.setDecimals(2)
            self.length_spin.setMinimum(0.01)
            self.length_spin.setMaximum(100000.0)
            self.length_spin.setValue(10.0)
            self.length_spin.setToolTip("Length of the exported clip in seconds")
            spins = QHBoxLayout()
            spins.addWidget(theme.field("Start time", self.start_spin))
            spins.addWidget(theme.field("Length", self.length_spin))
            trim_card.layout().addLayout(spins)
            outer.addWidget(trim_card)

            actions = QHBoxLayout()
            self.play_button = theme.button("Play / Stop", "play")
            self.export_button = theme.button("Export clip", "export", accent=True)
            actions.addWidget(self.play_button)
            actions.addStretch(1)
            actions.addWidget(self.export_button)
            outer.addLayout(actions)

            self.status = theme.label("No file loaded", "status")
            outer.addWidget(self.status)
            outer.addStretch(1)

            self.open_button.clicked.connect(self.choose_file)
            self.export_button.clicked.connect(self.export)
            self.play_button.clicked.connect(self.toggle_play)

        def set_status(self, text):
            self.status.setText(text)

        def choose_file(self):
            path, _selected = QFileDialog.getOpenFileName(
                self, "Open audio", "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.flac *.aac);;All files (*)")
            if not path:
                return
            self.path = path
            self.file_label.setText(os.path.basename(path))
            self.set_status("Reading %s…" % os.path.basename(path))
            command = core.build_probe_command(path)
            self._probe_process = QProcess(self)
            self._probe_process.setProcessChannelMode(
                QProcess.ProcessChannelMode.MergedChannels)
            self._probe_process.finished.connect(self._on_probe_finished)
            self._probe_process.start(command[0], command[1:])

        def _on_probe_finished(self, *_args):
            output = bytes(self._probe_process.readAll()).decode("utf-8", "replace")
            try:
                seconds = core.parse_duration_json(output)
            except ValueError as exc:
                self.set_status("Cannot read duration: %s" % exc)
                return
            self.length_spin.setMaximum(max(0.01, seconds))
            if self.length_spin.value() > seconds:
                self.length_spin.setValue(seconds)
            self.set_status("%s — %.2f s" % (os.path.basename(self.path), seconds))

        def export(self):
            if not self.path:
                self.set_status("Open an audio file first")
                return
            path, selected = QFileDialog.getSaveFileName(
                self, "Export clip", "",
                "WAV (*.wav);;MP3 (*.mp3);;OGG (*.ogg);;M4A (*.m4a)")
            if not path:
                return
            if not os.path.splitext(path)[1]:
                suffix = ".wav"
                if "mp3" in selected.lower():
                    suffix = ".mp3"
                elif "ogg" in selected.lower():
                    suffix = ".ogg"
                elif "m4a" in selected.lower():
                    suffix = ".m4a"
                path += suffix
            try:
                command = core.build_cut_command(
                    self.path, self.start_spin.value(), self.length_spin.value(), path)
            except ValueError as exc:
                self.set_status(str(exc))
                return
            self.set_status("Exporting %s…" % os.path.basename(path))
            self._export_process = QProcess(self)
            self._export_process.setProcessChannelMode(
                QProcess.ProcessChannelMode.MergedChannels)
            self._export_process.finished.connect(self._on_export_finished)
            self._export_process.start(command[0], command[1:])

        def _on_export_finished(self, *_args):
            output = bytes(self._export_process.readAll()).decode("utf-8", "replace").strip()
            if self._export_process.exitCode() == 0:
                self.set_status("Export finished")
            else:
                tail = output.splitlines()[-1] if output else "ffmpeg failed"
                self.set_status("Export failed: %s" % tail)

        def toggle_play(self):
            if (self._player_process is not None and
                    self._player_process.state() != QProcess.ProcessState.NotRunning):
                self._player_process.kill()
                self._player_process = None
                self.set_status("Playback stopped")
                return
            if not self.path:
                self.set_status("Open an audio file first")
                return
            command = core.build_play_command(self.path)
            self._player_process = QProcess(self)
            self._player_process.setProcessChannelMode(
                QProcess.ProcessChannelMode.MergedChannels)
            self._player_process.finished.connect(self._on_play_finished)
            self._player_process.start(command[0], command[1:])
            self.set_status("Playing %s" % os.path.basename(self.path))

        def _on_play_finished(self, *_args):
            self.set_status("Playback finished")

        def closeEvent(self, event):
            for process in (self._player_process, self._export_process,
                            self._probe_process):
                if (process is not None and
                        process.state() != QProcess.ProcessState.NotRunning):
                    process.kill()
            super().closeEvent(event)

    return TapecutWindow()


def main(argv=None):
    build_parser().parse_args(argv)  # exits before Qt for --help/--version
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    theme.install(app)
    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
