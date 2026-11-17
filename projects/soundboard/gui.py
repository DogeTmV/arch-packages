"""Dark, minimal PySide6 GUI for soundboard: eight click-to-play slots."""

import argparse
import os
import sys

import core
import theme

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
    from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QGridLayout,
                                   QHBoxLayout, QVBoxLayout, QWidget)

    chosen_player = core.resolve_player(player)

    class SoundboardWindow(QWidget):
        def __init__(self, player_command):
            super().__init__()
            theme.polish(self, NAME)
            self.setWindowTitle(NAME)
            self.setMinimumWidth(480)
            self.player = player_command
            self.slots = [None] * core.SLOT_COUNT
            self.buttons = []
            self._process = None
            self._output = ""
            self._build()

        def _build(self):
            outer = QVBoxLayout(self)
            outer.setContentsMargins(22, 20, 22, 18)
            outer.setSpacing(16)
            outer.addWidget(theme.header(NAME, "Eight sounds, one click each"))

            board = theme.card("SLOTS  ·  RIGHT-CLICK TO ASSIGN")
            grid = QGridLayout()
            grid.setSpacing(10)
            self.slot_group = QButtonGroup(self)
            self.slot_group.setExclusive(False)
            for index in range(core.SLOT_COUNT):
                button = theme.button(str(index + 1), "play")
                button.setObjectName("slot")
                button.setToolTip("Slot %d: empty (right-click to assign)" % (index + 1))
                button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.slot_group.addButton(button, index)
                button.customContextMenuRequested.connect(self.assign_slot_from_menu)
                self.buttons.append(button)
                grid.addWidget(button, index // 4, index % 4)
            self.slot_group.idClicked.connect(self.play_slot)
            board.layout().addLayout(grid)
            outer.addWidget(board)

            footer = QHBoxLayout()
            self.status = theme.label("Click a slot to play; right-click to assign", "status")
            self.stop_button = theme.button("Stop", "stop")
            footer.addWidget(self.status, 1)
            footer.addWidget(self.stop_button)
            outer.addLayout(footer)
            outer.addStretch(1)

            self.stop_button.clicked.connect(self.stop)

        def set_status(self, text):
            self.status.setText(text)

        def assign_slot_from_menu(self, _position):
            button = self.sender()
            if button in self.buttons:
                self.assign_slot(self.buttons.index(button))

        def assign_slot(self, index):
            path, _selected = QFileDialog.getOpenFileName(
                self, "Assign slot %d" % (index + 1), "",
                "Audio files (*.wav *.mp3 *.ogg *.m4a *.flac *.aac);;All files (*)")
            if not path:
                return
            self.slots[index] = path
            self.buttons[index].setToolTip("Slot %d: %s" % (index + 1, path))
            self.buttons[index].setProperty("assigned", True)
            self.buttons[index].style().polish(self.buttons[index])
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
    theme.install(app)
    window = create_window(player=args.player)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
