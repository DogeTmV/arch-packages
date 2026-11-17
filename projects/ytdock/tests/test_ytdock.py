import os
import subprocess
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import core
from gui import build_window, early_exit


class ModeAndCommandTests(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(set(core.MODES), {"best", "video", "audio", "small"})

    def test_best_command(self):
        self.assertEqual(
            core.build_command("https://example.com/watch?v=1", "best", "/tmp/out"),
            ["yt-dlp", "-f", "bestvideo+bestaudio/best", "-o",
             os.path.join("/tmp/out", "%(title)s.%(ext)s"),
             "https://example.com/watch?v=1"])

    def test_small_command(self):
        command = core.build_command("https://example.com/v", "small", "/tmp/out")
        self.assertEqual(command[2], "worstvideo+bestaudio/worst")

    def test_audio_command_adds_extraction(self):
        command = core.build_command("https://example.com/v", "audio", "/tmp/out")
        self.assertEqual(command[:7], ["yt-dlp", "-f", "bestaudio/best",
                                       "-x", "--audio-format", "mp3", "-o"])

    def test_custom_template(self):
        command = core.build_command("https://example.com/v", "video", "/tmp/out",
                                     template="%(id)s.%(ext)s")
        self.assertIn(os.path.join("/tmp/out", "%(id)s.%(ext)s"), command)

    def test_validation(self):
        with self.assertRaises(core.DownloadError):
            core.build_command("ftp://example.com/v", "best", "/tmp/out")
        with self.assertRaises(core.DownloadError):
            core.build_command("example.com/v", "best", "/tmp/out")
        with self.assertRaises(core.DownloadError):
            core.build_command("https://example.com/v", "turbo", "/tmp/out")


class ProgressTests(unittest.TestCase):
    def test_extracts_percentage(self):
        self.assertEqual(core.parse_progress(
            "[download]  45.2% of ~10.00MiB at 1.20MiB/s ETA 00:05"), 45.2)
        self.assertEqual(core.parse_progress("[download] 100% of 5MiB in 00:02"),
                         100.0)

    def test_returns_none(self):
        self.assertIsNone(core.parse_progress("[download] Destination: x.mp4"))
        self.assertIsNone(core.parse_progress(""))


class RunnerTests(unittest.TestCase):
    def test_injectable_runner_receives_command_and_output_flags(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append((command, kwargs))
            return "stub-output"

        self.assertEqual(core.run_download(fake_runner, ["yt-dlp", "--version"]),
                         "stub-output")
        self.assertEqual(calls[0][0], ["yt-dlp", "--version"])
        self.assertTrue(calls[0][1]["text"])
        self.assertTrue(calls[0][1]["stdout"] is subprocess.PIPE)

    def test_fake_ytdlp_script_full_command_and_log(self):
        with tempfile.TemporaryDirectory() as directory:
            script = os.path.join(directory, "yt-dlp")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("""#!/bin/sh
printf '%s\\n' "$@"
printf '%s\\n' '[download]  42.0% of 1.00MiB'
""")
            os.chmod(script, 0o755)

            command = core.build_command(
                "https://example.com/watch?v=abc", "best", directory,
                template="%(id)s.%(ext)s")
            command[0] = script
            result = core.run_download(subprocess.run, command)

            self.assertEqual(result.returncode, 0)
            lines = result.stdout.splitlines()
            self.assertIn("-f", lines)
            self.assertIn("bestvideo+bestaudio/best", lines)
            self.assertIn(os.path.join(directory, "%(id)s.%(ext)s"), lines)
            self.assertIn("https://example.com/watch?v=abc", lines)
            self.assertEqual(core.parse_progress(result.stdout), 42.0)


class GuiTests(unittest.TestCase):
    def test_early_args(self):
        self.assertEqual(early_exit(["--help"]),
                         ("usage: ytdock [--help | --version]", 0))
        self.assertEqual(early_exit(["--version"]), ("ytdock 0.1.0", 0))
        self.assertIsNone(early_exit([]))

    def test_offscreen_smoke(self):
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        window = build_window()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "ytdock")
        self.assertEqual(window.mode_combo.count(), 4)
        self.assertTrue(window.log_pane.isReadOnly())
        window.close()
        self.assertIs(app, QtWidgets.QApplication.instance())


if __name__ == "__main__":
    unittest.main()
