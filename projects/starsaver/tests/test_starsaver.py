"""Offline tests for the starsaver terminal screensaver."""

import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "starsaver"


def run(*args):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True)


class StarsaverTests(unittest.TestCase):
    def test_render_is_repeatable_for_the_same_seed(self):
        for mode in ("stars", "rain", "pipes"):
            with self.subTest(mode=mode):
                args = ("render", mode, "--frames", "3", "--seed", "42")
                first, second = run(*args), run(*args)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertEqual(first.stdout, second.stdout)
                self.assertTrue(first.stdout.strip())

    def test_different_seeds_produce_different_frames(self):
        for mode in ("stars", "rain", "pipes"):
            with self.subTest(mode=mode):
                one = run("render", mode, "--frames", "1", "--seed", "1")
                two = run("render", mode, "--frames", "1", "--seed", "2")
                self.assertEqual(one.returncode, 0, one.stderr)
                self.assertEqual(two.returncode, 0, two.stderr)
                self.assertNotEqual(one.stdout, two.stdout)

    def test_render_frames_are_separated_by_blank_lines_and_respect_size(self):
        result = run("render", "stars", "--frames", "3", "--seed", "7",
                     "--width", "20", "--height", "8")
        self.assertEqual(result.returncode, 0, result.stderr)
        frames = result.stdout.rstrip("\n").split("\n\n")
        self.assertEqual(len(frames), 3)
        for frame in frames:
            rows = frame.splitlines()
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(len(row) == 20 for row in rows))

    def test_run_without_ansi_emits_plain_frames(self):
        result = run("run", "stars", "--duration", "0", "--fps", "1", "--seed", "5",
                     "--no-ansi", "--width", "20", "--height", "6")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b", result.stdout)
        self.assertTrue(any(char in result.stdout for char in ".+*"))

    def test_run_with_ansi_emits_escape_sequences(self):
        result = run("run", "rain", "--duration", "0", "--fps", "1", "--seed", "5",
                     "--width", "20", "--height", "6")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\x1b[", result.stdout)

    def test_modes_lists_all_three_modes(self):
        result = run("modes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["stars", "rain", "pipes"])

    def test_invalid_render_arguments_fail_cleanly(self):
        for args in (("render", "stars", "--frames", "0", "--seed", "1"),
                     ("render", "stars", "--frames", "1", "--seed", "1", "--width", "2"),
                     ("render", "unknown", "--frames", "1", "--seed", "1")):
            with self.subTest(args=args):
                result = run(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())

    def test_help_and_version_exit_zero(self):
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run("render", "--help").returncode, 0)
        version = run("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)


if __name__ == "__main__":
    unittest.main()
