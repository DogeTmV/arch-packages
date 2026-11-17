"""Offscreen GUI and launcher smoke tests for hashcheck."""

import os
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
EXE = os.path.join(ROOT, "hashcheck")

from PySide6.QtWidgets import QApplication

import gui


def new_window():
    return gui.create_window()

EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)


class HashcheckWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_can_be_created_and_closed(self):
        window = new_window()
        window.close()
        self.assertFalse(window.isVisible())

    def test_compute_then_verify_reports_match_and_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "empty.bin")
            with open(path, "wb"):
                pass
            window = new_window()
            window.set_path(path)
            window.algo_combo.setCurrentText("sha256")
            window.compute_button.click()
            self.assertEqual(window.result_label.text(), EMPTY_SHA256)

            window.expected_edit.setText("  " + EMPTY_SHA256.upper() + " ")
            window.verify_button.click()
            self.assertIn("match", window.result_label.text().lower())

            window.expected_edit.setText("00" * 32)
            window.verify_button.click()
            self.assertIn("mismatch", window.result_label.text().lower())
            window.close()


class LauncherTest(unittest.TestCase):
    def run_launcher(self, argument):
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        env.pop("QT_QPA_PLATFORM", None)
        return subprocess.run(
            [EXE, argument], capture_output=True, text=True, env=env, timeout=30
        )

    def test_help_works_without_a_display(self):
        proc = self.run_launcher("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage: hashcheck", proc.stdout.lower())
        self.assertNotIn("Traceback", proc.stderr)

    def test_version_works_without_a_display(self):
        proc = self.run_launcher("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "hashcheck 0.1.0")


if __name__ == "__main__":
    unittest.main()
