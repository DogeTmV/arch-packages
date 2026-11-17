"""Offline tests for soundboard: play commands, player selection and GUI smoke."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core
import gui

LAUNCHER = ROOT / "soundboard"


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sound = os.path.join(self.tmp.name, "click.wav")
        Path(self.sound).write_bytes(b"fake audio")

    def test_default_player_command(self):
        self.assertEqual(core.build_play_command("ffplay", self.sound), [
            "ffplay", "-nodisp", "-autoexit", "-loglevel", "error", self.sound])
        self.assertEqual(core.build_play_command(None, self.sound),
                         core.build_play_command("ffplay", self.sound))
        self.assertEqual(core.build_play_command(self.sound),
                         core.build_play_command("ffplay", self.sound))

    def test_custom_player_command(self):
        self.assertEqual(core.build_play_command("mpv", self.sound),
                         ["mpv", self.sound])
        self.assertEqual(core.build_play_command("mpv --no-config", self.sound),
                         ["mpv", "--no-config", self.sound])
        self.assertEqual(core.build_play_command(["paplay", "--device=test"], self.sound),
                         ["paplay", "--device=test", self.sound])

    def test_missing_file_and_empty_player_are_rejected(self):
        missing = os.path.join(self.tmp.name, "nope.wav")
        with self.assertRaisesRegex(FileNotFoundError, "nope.wav"):
            core.build_play_command("ffplay", missing)
        with self.assertRaises(ValueError):
            core.build_play_command("   ", self.sound)
        with self.assertRaises(ValueError):
            core.build_play_command("ffplay", "")

    def test_resolve_player_precedence(self):
        self.assertEqual(core.resolve_player(None, {}), "ffplay")
        self.assertEqual(core.resolve_player(None, {"SOUNDBOARD_PLAYER": "mpv"}), "mpv")
        self.assertEqual(core.resolve_player("paplay", {"SOUNDBOARD_PLAYER": "mpv"}),
                         "paplay")
        self.assertEqual(core.resolve_player("", {"SOUNDBOARD_PLAYER": "  "}), "ffplay")

    def test_slot_count_and_description(self):
        self.assertEqual(core.SLOT_COUNT, 8)
        command = core.build_play_command("ffplay", self.sound)
        self.assertIn("ffplay", core.describe_command(command))


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QPushButton
        cls.app = QApplication.instance() or QApplication([])
        cls.button_type = QPushButton

    def test_offscreen_window_smoke(self):
        window = gui.create_window(player="ffplay")
        window.show()
        self.assertEqual(window.windowTitle(), "soundboard")
        labels = [button.text() for button in window.findChildren(self.button_type)]
        self.assertEqual(labels[:8], [str(i) for i in range(1, 9)])
        window.buttons[0].click()  # empty slot: status only, no player launched
        self.assertIn("empty", window.status.text())
        window.stop_button.click()
        self.assertEqual(window.status.text(), "Stopped")
        window.close()

    def test_help_and_version_work_without_display(self):
        env = dict(os.environ)
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM"):
            env.pop(key, None)
        for flag in (["--help"], ["--version"], ["--player", "mpv", "--help"]):
            result = subprocess.run([str(LAUNCHER), *flag], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        version = subprocess.run([str(LAUNCHER), "--version"], env=env,
                                 capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "soundboard 0.1.0")


if __name__ == "__main__":
    unittest.main()
