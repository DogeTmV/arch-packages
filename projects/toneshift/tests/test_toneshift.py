"""Offline tests for toneshift: rate handling, ffmpeg args and GUI smoke."""

import math
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core
import gui

LAUNCHER = ROOT / "toneshift"


class RateTests(unittest.TestCase):
    def test_normalize_rate_clamps_and_reports_errors(self):
        self.assertEqual(core.normalize_rate(1.5), 1.5)
        self.assertEqual(core.normalize_rate(0.1), 0.5)
        self.assertEqual(core.normalize_rate(3.0), 2.0)
        for bad in (0, -1, -0.5, "fast", None, math.nan, math.inf, True):
            with self.subTest(rate=bad):
                with self.assertRaises(ValueError):
                    core.normalize_rate(bad)

    def test_single_atempo_filters(self):
        expected = [(0.5, "atempo=0.5"), (1.0, "atempo=1"),
                    (1.5, "atempo=1.5"), (2.0, "atempo=2")]
        for rate, chain in expected:
            with self.subTest(rate=rate):
                command = core.build_speed_command("song.mp3", rate, "out.mp3")
                self.assertEqual(command[command.index("-filter:a") + 1], chain)

    def test_decomposes_rates_outside_single_filter_range(self):
        self.assertEqual(core.atempo_factors(2.5), [1.25, 2.0])
        self.assertEqual(core.atempo_factors(0.25), [0.5, 0.5])
        command = core.build_speed_command("song.mp3", 2.5, "out.mp3")
        self.assertEqual(command[command.index("-filter:a") + 1],
                         "atempo=1.25,atempo=2")
        slow = core.build_speed_command("song.mp3", 0.25, "out.ogg")
        self.assertEqual(slow[slow.index("-filter:a") + 1],
                         "atempo=0.5,atempo=0.5")

    def test_products_of_factors_match_the_requested_rate(self):
        for rate in (0.125, 0.4, 0.75, 1.0, 1.7, 2.0, 2.5, 3.3, 10.0):
            with self.subTest(rate=rate):
                product = 1.0
                for factor in core.atempo_factors(rate):
                    self.assertGreaterEqual(factor, 0.5)
                    self.assertLessEqual(factor, 2.0)
                    product *= factor
                self.assertAlmostEqual(product, rate, places=9)

    def test_command_shape_and_encoders(self):
        command = core.build_speed_command("in.wav", 1.5, "out.mp3")
        self.assertEqual(command, [
            "ffmpeg", "-y", "-i", "in.wav", "-filter:a", "atempo=1.5",
            "-vn", "-c:a", "libmp3lame", "out.mp3"])
        self.assertEqual(core.build_speed_command("in.mp3", 1, "a.wav")[-3:-1],
                         ["-c:a", "pcm_s16le"])
        self.assertEqual(core.build_speed_command("in.mp3", 1, "a.ogg")[-3:-1],
                         ["-c:a", "libvorbis"])
        self.assertIn("in.wav", core.describe_command(command))

    def test_invalid_rates_and_outputs_are_rejected(self):
        for rate in (0, -1, "x", math.nan):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    core.build_speed_command("in.mp3", rate, "out.mp3")
        with self.assertRaises(ValueError):
            core.build_speed_command("in.mp3", 1, "out.flac")
        with self.assertRaises(ValueError):
            core.build_speed_command("", 1, "out.mp3")


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_offscreen_window_smoke(self):
        window = gui.create_window()
        window.show()
        self.assertEqual(window.windowTitle(), "toneshift")
        self.assertEqual((window.slider.minimum(), window.slider.maximum()), (50, 200))
        window.slider.setValue(150)
        self.assertEqual(window.rate_label.text(), "Speed: 1.50x")
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
        self.assertEqual(version.stdout.strip(), "toneshift 0.1.0")


if __name__ == "__main__":
    unittest.main()
