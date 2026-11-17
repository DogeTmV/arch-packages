"""Offscreen GUI and launcher smoke tests for jsonpolish."""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
EXE = os.path.join(ROOT, "jsonpolish")

from PySide6.QtWidgets import QApplication

import gui


def new_window():
    return gui.create_window()


class JsonpolishWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_can_be_created_and_closed(self):
        window = new_window()
        window.close()
        self.assertFalse(window.isVisible())

    def test_format_minify_copy_and_clear_buttons(self):
        window = new_window()
        window.text_edit.setPlainText('{"b":2,"a":1}')

        window.format_button.click()
        self.assertEqual(
            window.text_edit.toPlainText(),
            '{\n  "b": 2,\n  "a": 1\n}',
        )
        self.assertIn("Valid", window.status_label.text())

        window.minify_button.click()
        self.assertEqual(window.text_edit.toPlainText(), '{"b":2,"a":1}')

        window.copy_button.click()
        self.assertEqual(self.app.clipboard().text(), '{"b":2,"a":1}')
        self.assertIn("Copied", window.status_label.text())

        window.clear_button.click()
        self.assertEqual(window.text_edit.toPlainText(), "")
        window.close()

    def test_invalid_input_reports_error_and_keeps_text(self):
        window = new_window()
        window.text_edit.setPlainText("{oops")
        with patch("PySide6.QtWidgets.QMessageBox.warning"):
            window.format_button.click()
        self.assertEqual(window.text_edit.toPlainText(), "{oops")
        self.assertTrue(window.status_label.text().startswith("Invalid JSON:"))
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
        self.assertIn("usage: jsonpolish", proc.stdout.lower())
        self.assertNotIn("Traceback", proc.stderr)

    def test_version_works_without_a_display(self):
        proc = self.run_launcher("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "jsonpolish 0.1.0")


if __name__ == "__main__":
    unittest.main()
