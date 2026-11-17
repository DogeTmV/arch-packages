import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import core
from gui import build_window, early_exit


class CommandTests(unittest.TestCase):
    def test_build_command_without_crop(self):
        self.assertEqual(
            core.build_command("in.mp4", 5, 2.5, None, "out.mp4"),
            ["ffmpeg", "-y", "-ss", "5", "-t", "2.5", "-i", "in.mp4",
             "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
             "out.mp4"])

    def test_build_command_with_crop(self):
        command = core.build_command(
            "in.mkv", 1.5, 3, {"x": 10, "y": 20, "w": 640, "h": 480},
            "out.mov")
        self.assertEqual(command, [
            "ffmpeg", "-y", "-ss", "1.5", "-t", "3", "-i", "in.mkv",
            "-vf", "crop=640:480:10:20",
            "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
            "out.mov"])

    def test_build_preview_command(self):
        self.assertEqual(core.build_preview_command("in.mp4", 2.5),
                         ["ffplay", "-ss", "2.5", "-i", "in.mp4"])

    def test_invalid_start_length_output(self):
        with self.assertRaises(core.MediaError):
            core.build_command("in.mp4", -1, 2, None, "out.mp4")
        with self.assertRaises(core.MediaError):
            core.build_command("in.mp4", 0, 0, None, "out.mp4")
        with self.assertRaises(core.MediaError):
            core.build_command("in.mp4", 0, -2, None, "out.mp4")
        with self.assertRaises(core.MediaError):
            core.build_command("in.mp4", 0, 2, None, "out.avi")

    def test_invalid_crop(self):
        for crop in ({"x": 0, "y": 0, "w": 640},
                     {"x": -1, "y": 0, "w": 640, "h": 480},
                     {"x": 0, "y": 0, "w": 0, "h": 480},
                     {"x": 0.5, "y": 0, "w": 640, "h": 480},
                     "not-a-dict"):
            with self.assertRaises(core.MediaError):
                core.build_command("in.mp4", 0, 2, crop, "out.mp4")


class ProbeTests(unittest.TestCase):
    def test_probe_video_with_fake_runner(self):
        calls = []

        class Result:
            stdout = json.dumps({
                "streams": [{"width": 1280, "height": 720}],
                "format": {"duration": "12.5"},
            })

        def fake_runner(command, **kwargs):
            calls.append(command)
            return Result()

        self.assertEqual(core.probe_video("in.mp4", runner=fake_runner),
                         (1280, 720, 12.5))
        self.assertEqual(calls[0], core.build_probe_command("in.mp4"))

    def test_parse_probe_output_errors(self):
        with self.assertRaises(core.MediaError):
            core.parse_probe_output("not json")
        with self.assertRaises(core.MediaError):
            core.parse_probe_output('{"streams": []}')
        with self.assertRaises(core.MediaError):
            core.parse_probe_output('{"streams": [{"width": 4}]}')


class GuiTests(unittest.TestCase):
    def test_early_args(self):
        self.assertEqual(early_exit(["--help"]),
                         ("usage: cutframe [--help | --version]", 0))
        self.assertEqual(early_exit(["--version"]), ("cutframe 0.1.0", 0))
        self.assertIsNone(early_exit([]))

    def test_offscreen_smoke(self):
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        window = build_window()
        try:
            self.assertIsNotNone(window)
            self.assertEqual(window.windowTitle(), "cutframe")
            self.assertTrue(window.cut_panel.isHidden())
            self.assertTrue(window.crop_panel.isHidden())
            window.cut_button.click()
            window.crop_button.click()
            self.assertFalse(window.cut_panel.isHidden())
            self.assertFalse(window.crop_panel.isHidden())
        finally:
            window.close()
        self.assertIs(app, QtWidgets.QApplication.instance())


if __name__ == "__main__":
    unittest.main()
