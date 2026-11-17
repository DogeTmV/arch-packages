"""Offscreen GUI and launcher smoke tests for batchrename."""

import os
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
EXE = os.path.join(ROOT, "batchrename")

from PySide6.QtWidgets import QApplication

import gui


def new_window():
    return gui.create_window()


class BatchrenameWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_can_be_created_and_closed(self):
        window = new_window()
        window.close()
        self.assertFalse(window.isVisible())

    def test_preview_then_rename_uses_the_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            first = os.path.join(directory, "one.txt")
            second = os.path.join(directory, "two.txt")
            for path in (first, second):
                with open(path, "wb"):
                    pass
            target = os.path.join(directory, "one_01.txt")

            window = new_window()
            window.set_paths([first, second])
            window.pattern_edit.setText("{name}_{nn}")
            window.start_spin.setValue(1)
            window.preview_button.click()
            lines = [
                window.preview_list.item(i).text()
                for i in range(window.preview_list.count())
            ]
            self.assertEqual(
                lines,
                ["one.txt -> one_01.txt", "two.txt -> two_02.txt"],
            )

            window.rename_button.click()
            self.assertTrue(os.path.exists(target))
            self.assertFalse(os.path.exists(first))
            self.assertIn("2", window.status_label.text())
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
        self.assertIn("usage: batchrename", proc.stdout.lower())
        self.assertNotIn("Traceback", proc.stderr)

    def test_version_works_without_a_display(self):
        proc = self.run_launcher("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "batchrename 0.1.0")


if __name__ == "__main__":
    unittest.main()
