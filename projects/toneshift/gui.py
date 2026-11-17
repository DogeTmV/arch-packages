"""Dark, minimal PySide6 GUI for toneshift (speed/pitch slider)."""

import argparse
import os
import sys

import core
import theme

NAME = "toneshift"
VERSION = core.VERSION


def build_parser():
    parser = argparse.ArgumentParser(
        prog=NAME, description="Change playback speed with a small slider GUI.")
    parser.add_argument("--version", action="version",
                        version="%s %s" % (NAME, VERSION))
    return parser


def create_window():
    """Build the main window; Qt is imported lazily for display-free CLI flags."""
    from PySide6.QtCore import QProcess, Qt
    from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QSlider, QVBoxLayout, QWidget

    class ToneshiftWindow(QWidget):
        def __init__(self):
            super().__init__()
            theme.polish(self, NAME)
            self.setWindowTitle(NAME)
            self.setMinimumWidth(430)
            self.path = ""
            self._export_process = None
            self._player_process = None
            self._build()

        def _build(self):
            outer = QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Shift playback speed without losing the vibe"))

            source_card = theme.card("SOURCE")
            source_row = QHBoxLayout()
            self.open_button = theme.button("Open audio", "folder")
            self.file_label = theme.label("No file loaded", "status")
            source_row.addWidget(self.open_button)
            source_row.addWidget(self.file_label, 1)
            source_card.layout().addLayout(source_row)
            outer.addWidget(source_card)

            speed_card = theme.card("PLAYBACK SPEED")
            self.rate_label = theme.label("Speed: 1.00x", "value")
            self.rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.slider = QSlider(Qt.Orientation.Horizontal)
            self.slider.setMinimum(int(core.ATEMPO_MIN * 100))
            self.slider.setMaximum(int(core.ATEMPO_MAX * 100))
            self.slider.setSingleStep(5)
            self.slider.setValue(100)
            self.slider.setToolTip("Playback speed (0.5x - 2.0x)")
            speed_card.layout().addWidget(self.rate_label)
            speed_card.layout().addWidget(self.slider)
            hints = QHBoxLayout()
            hints.addWidget(theme.label("0.5×", "field"))
            hints.addStretch(1)
            hints.addWidget(theme.label("1.0×", "field"))
            hints.addStretch(1)
            hints.addWidget(theme.label("2.0×", "field"))
            speed_card.layout().addLayout(hints)
            outer.addWidget(speed_card)

            actions = QHBoxLayout()
            self.play_button = theme.button("Play / Stop", "play")
            self.export_button = theme.button("Export audio", "export", accent=True)
            actions.addWidget(self.play_button)
            actions.addStretch(1)
            actions.addWidget(self.export_button)
            outer.addLayout(actions)

            self.status = theme.label("Ready", "status")
            outer.addWidget(self.status)
            outer.addStretch(1)

            self.open_button.clicked.connect(self.choose_file)
            self.slider.valueChanged.connect(self._on_rate_changed)
            self.export_button.clicked.connect(self.export)
            self.play_button.clicked.connect(self.toggle_play)

        def set_status(self, text):
            self.status.setText(text)

        @property
        def rate(self):
            return self.slider.value() / 100.0

        def _on_rate_changed(self, _value=None):
            self.rate_label.setText("Speed: %.2fx" % self.rate)

        def choose_file(self):
            path, _selected = QFileDialog.getOpenFileName(
                self, "Open audio", "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.flac *.aac);;All files (*)")
            if not path:
                return
            self.path = path
            self.file_label.setText(os.path.basename(path))
            self.set_status("Loaded %s" % os.path.basename(path))

        def export(self):
            if not self.path:
                self.set_status("Open an audio file first")
                return
            path, selected = QFileDialog.getSaveFileName(
                self, "Export audio", "",
                "WAV (*.wav);;MP3 (*.mp3);;OGG (*.ogg)")
            if not path:
                return
            if not os.path.splitext(path)[1]:
                suffix = ".wav"
                if "mp3" in selected.lower():
                    suffix = ".mp3"
                elif "ogg" in selected.lower():
                    suffix = ".ogg"
                path += suffix
            try:
                command = core.build_speed_command(self.path, self.rate, path)
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
            for process in (self._player_process, self._export_process):
                if (process is not None and
                        process.state() != QProcess.ProcessState.NotRunning):
                    process.kill()
            super().closeEvent(event)

    return ToneshiftWindow()


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
