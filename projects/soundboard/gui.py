"""Thin PySide6 GUI for soundboard: eight click-to-play slots."""

import argparse
import os
import sys

import core

NAME = "soundboard"
VERSION = core.VERSION


def build_parser():
    parser = argparse.ArgumentParser(
        prog=NAME, description="Eight-slot click-to-play soundboard GUI.")
    parser.add_argument("--version", action="version",
                        version="%s %s" % (NAME, VERSION))
    parser.add_argument(
        "--player", metavar="CMD", default=None,
        help="player command (default: ffplay, or SOUNDBOARD_PLAYER)")
    return parser


def create_window(player=None):
    """Build the main window; Qt is imported lazily for display-free CLI flags."""
    from PySide6.QtCore import QProcess, Qt
    from PySide6.QtWidgets import (QFileDialog, QGridLayout, QLabel,
                                   QPushButton, QWidget)

    chosen_player = core.resolve_player(player)

    class SoundboardWindow(QWidget):
        def __init__(self, player_command):
            super().__init__()
            self.setWindowTitle(NAME)
            self.resize(520, 270)
            self.player = player_command
            self.slots = [None] * core.SLOT_COUNT
            self.buttons = []
            self._process = None
            self._output = ""

            self.stop_button = QPushButton("Stop")
            self.status = QLabel("Click a slot to play; right-click to assign")
            self.status.setWordWrap(True)

            layout = QGridLayout(self)
            for index in range(core.SLOT_COUNT):
                button = QPushButton(str(index + 1))
                button.setMinimumSize(105, 70)
                button.setToolTip("Slot %d: empty (right-click to assign)" % (index + 1))
                button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                button.clicked.connect(
                    lambda _checked, idx=index: self.play_slot(idx))
                button.customContextMenuRequested.connect(
                    lambda _pos, idx=index: self.assign_slot(idx))
                self.buttons.append(button)
                layout.addWidget(button, index // 4, index % 4)
            layout.addWidget(self.stop_button, 2, 0, 1, 2)
            layout.addWidget(self.status, 2, 2, 1, 2)
            self.stop_button.clicked.connect(self.stop)

        def set_status(self, text):
            self.status.setText(text)

        def assign_slot(self, index):
            path, _selected = QFileDialog.getOpenFileName(
                self, "Assign slot %d" % (index + 1), "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.flac *.aac);;All files (*)")
            if not path:
                return
            self.slots[index] = path
            self.buttons[index].setToolTip("Slot %d: %s" % (index + 1, path))
            self.set_status("Slot %d assigned: %s" % (index + 1, os.path.basename(path)))

        def play_slot(self, index):
            path = self.slots[index]
            if not path:
                self.set_status("Slot %d is empty — right-click to assign" % (index + 1))
                return
            try:
                command = core.build_play_command(self.player, path)
            except (FileNotFoundError, ValueError) as exc:
                self.set_status(str(exc))
                return
            self.stop()
            self._output = ""
            self._process = QProcess(self)
            self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self._process.readyRead.connect(self._on_ready_read)
            self._process.finished.connect(self._on_finished)
            self._process.start(command[0], command[1:])
            self.set_status("Playing slot %d (%s)" % (index + 1, core.describe_command(command)))

        def _on_ready_read(self):
            self._output += bytes(self._process.readAll()).decode("utf-8", "replace")

        def _on_finished(self, *_args):
            if self._process is not None and self._process.exitCode() != 0:
                detail = self._output.strip().splitlines()
                self.set_status("Playback failed: %s" % (
                    detail[-1] if detail else "player exited with an error"))
            else:
                self.set_status("Playback finished")

        def stop(self):
            if (self._process is not None and
                    self._process.state() != QProcess.ProcessState.NotRunning):
                self._process.kill()
            self._process = None
            self.set_status("Stopped")

        def closeEvent(self, event):
            if (self._process is not None and
                    self._process.state() != QProcess.ProcessState.NotRunning):
                self._process.kill()
            super().closeEvent(event)

    return SoundboardWindow(chosen_player)


def main(argv=None):
    args = build_parser().parse_args(argv)  # exits before Qt for --help/--version
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    window = create_window(player=args.player)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
