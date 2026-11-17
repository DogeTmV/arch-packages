"""Offline tests for tapecut: command builders, ffprobe parsing and GUI smoke."""

import os
import subprocess
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core
import gui

LAUNCHER = ROOT / "tapecut"


class CommandTests(unittest.TestCase):
    def test_stream_copy_when_input_and_output_share_a_family(self):
        command = core.build_cut_command("song.mp3", 10, 5, "clip.mp3")
        self.assertEqual(command, [
            "ffmpeg", "-y", "-ss", "10", "-i", "song.mp3",
            "-t", "5", "-vn", "-c", "copy", "clip.mp3"])

    def test_reencode_when_families_differ(self):
        cases = [
            ("song.mp3", "clip.wav", "pcm_s16le"),
            ("song.wav", "clip.mp3", "libmp3lame"),
            ("song.mp3", "clip.ogg", "libvorbis"),
            ("song.wav", "clip.m4a", "aac"),
        ]
        for source, target, encoder in cases:
            with self.subTest(source=source, target=target):
                command = core.build_cut_command(source, 1.5, 3, target)
                self.assertEqual(command[-3:-1], ["-c:a", encoder])
                self.assertIn("-ss", command)
                self.assertEqual(command[command.index("-ss") + 1], "1.5")
                self.assertEqual(command[command.index("-t") + 1], "3")

    def test_explicit_codec_and_extension_aliases(self):
        command = core.build_cut_command("in.flac", 0, 2, "out.ogg", codec="libopus")
        self.assertEqual(command[-3:-1], ["-c:a", "libopus"])
        command = core.build_cut_command("in.flac", 0, 2, "out.ogg", codec="mp3")
        self.assertEqual(command[-3:-1], ["-c:a", "libmp3lame"])

    def test_describe_command_quotes_paths(self):
        command = core.build_cut_command("my song.wav", 0, 1, "clip.wav")
        text = core.describe_command(command)
        self.assertTrue(text.startswith("ffmpeg -y"))
        self.assertIn("'my song.wav'", text)

    def test_invalid_inputs_are_rejected(self):
        bad = [
            (("in.wav", -1, 2, "out.wav"), {}),
            (("in.wav", 0, 0, "out.wav"), {}),
            (("in.wav", 0, -2, "out.wav"), {}),
            (("in.wav", 0, 2, "out.flac"), {}),
            (("in.wav", "abc", 2, "out.wav"), {}),
            (("in.wav", 0, None, "out.wav"), {}),
            (("", 0, 2, "out.wav"), {}),
            (("in.wav", 0, 2, ""), {}),
        ]
        for args, kwargs in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    core.build_cut_command(*args, **kwargs)

    def test_play_command_uses_ffplay(self):
        command = core.build_play_command("song.mp3")
        self.assertEqual(command, [
            "ffplay", "-nodisp", "-autoexit", "-loglevel", "error", "song.mp3"])


class ProbeTests(unittest.TestCase):
    def test_probe_duration_parses_fake_ffprobe_json(self):
        def runner(command, **_kwargs):
            self.assertEqual(command[0], "ffprobe")
            self.assertEqual(command[-1], "/tmp/song.mp3")
            self.assertEqual(command[command.index("-of") + 1], "json")
            return types.SimpleNamespace(
                returncode=0, stdout='{"format": {"duration": "123.5"}}', stderr="")

        self.assertEqual(core.probe_duration("/tmp/song.mp3", runner=runner), 123.5)

    def test_simple_runner_without_kwargs_is_supported(self):
        def runner(command):
            return {"returncode": 0, "stdout": b'{"format": {"duration": 2.25}}'}

        self.assertEqual(core.probe_duration("song.mp3", runner=runner), 2.25)

    def test_probe_errors_are_clear(self):
        def bad_json(_command, **_kwargs):
            return types.SimpleNamespace(returncode=0, stdout="not json", stderr="")

        def failed(_command, **_kwargs):
            return types.SimpleNamespace(returncode=1, stdout="", stderr="No such file")

        with self.assertRaisesRegex(RuntimeError, "song.mp3"):
            core.probe_duration("song.mp3", runner=bad_json)
        with self.assertRaisesRegex(RuntimeError, "No such file"):
            core.probe_duration("song.mp3", runner=failed)


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_offscreen_window_smoke(self):
        window = gui.create_window()
        window.show()
        self.assertEqual(window.windowTitle(), "tapecut")
        self.assertEqual(window.status.text(), "No file loaded")
        window.play_button.click()  # no file selected: only updates status
        self.assertIn("Open an audio file", window.status.text())
        window.close()

    def test_help_and_version_work_without_display(self):
        env = dict(os.environ)
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM"):
            env.pop(key, None)
        for flag in ("--help", "--version"):
            result = subprocess.run([str(LAUNCHER), flag], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        version = subprocess.run([str(LAUNCHER), "--version"], env=env,
                                 capture_output=True, text=True)
        self.assertEqual(version.stdout.strip(), "tapecut 0.1.0")


if __name__ == "__main__":
    unittest.main()
