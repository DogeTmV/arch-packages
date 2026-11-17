"""Tests for the headless snake core and the snakecell CLI."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "snakecell")
sys.path.insert(0, ROOT)

from snake_core import Grid  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [EXE] + [str(a) for a in args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )


class SnakeCoreTest(unittest.TestCase):
    def test_direction_change_turns_and_rejects_immediate_reversal(self):
        grid = Grid(width=9, height=9, seed=1)
        grid.food = (0, 0)
        start = grid.snake[0]
        self.assertTrue(grid.change_direction("up"))
        self.assertFalse(grid.change_direction("down"))
        self.assertTrue(grid.step())
        self.assertEqual(grid.snake[0], (start[0], start[1] - 1))

    def test_wall_collision_ends_the_game(self):
        grid = Grid(width=5, height=5, seed=7)
        grid.food = (0, 0)
        self.assertTrue(grid.step())  # head x=3
        self.assertTrue(grid.step())  # head x=4
        self.assertFalse(grid.step())  # head x=5 is outside
        self.assertTrue(grid.game_over)
        self.assertEqual(grid.score, 0)

    def test_self_collision_ends_the_game(self):
        grid = Grid(width=5, height=5, seed=3)
        grid.food = (0, 0)
        grid.snake = [(2, 2), (1, 2), (1, 3), (2, 3), (3, 3)]
        grid.direction = (0, 1)
        self.assertFalse(grid.step())
        self.assertTrue(grid.game_over)

    def test_food_consumption_increases_score_and_grows_snake(self):
        grid = Grid(width=7, height=7, seed=11)
        grid.food = (grid.snake[0][0] + 1, grid.snake[0][1])
        before = len(grid.snake)
        self.assertTrue(grid.step())
        self.assertEqual(grid.score, 1)
        self.assertEqual(len(grid.snake), before + 1)
        self.assertNotEqual(grid.food, (grid.snake[0][0], grid.snake[0][1]))

    def test_serialize_board_has_border_head_and_food(self):
        grid = Grid(width=7, height=7, seed=5)
        board = grid.serialize_board()
        lines = board.splitlines()
        self.assertEqual(len(lines), 9)
        self.assertTrue(all(len(line) == 9 for line in lines))
        self.assertIn("O", board)
        self.assertIn("*", board)
        self.assertEqual(str(grid), board)

    def test_same_seed_places_food_identically(self):
        a = Grid(width=12, height=10, seed=123)
        b = Grid(width=12, height=10, seed=123)
        self.assertEqual(a.food, b.food)
        self.assertEqual(a.serialize_board(), b.serialize_board())


class SnakeCLITest(unittest.TestCase):
    def test_demo_is_deterministic_for_the_same_seed(self):
        first = run_cli("--demo", "--steps", "20", "--seed", "42")
        second = run_cli("--demo", "--steps", "20", "--seed", "42")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn("Score:", first.stdout)
        self.assertIn("#", first.stdout)

    def test_help_and_version_never_need_a_tty(self):
        help_proc = run_cli("--help")
        self.assertEqual(help_proc.returncode, 0)
        self.assertIn("usage", help_proc.stdout.lower())
        version = run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)

    def test_invalid_dimension_is_rejected(self):
        proc = run_cli("--demo", "--steps", "1", "--width", "2")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_installed_layout_can_run_demo_from_bin(self):
        # Simulate /usr/bin/snakecell + /usr/lib/snakecell/snake_core.py
        # without touching either location.
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            lib_dir = os.path.join(tmp, "lib", "snakecell")
            os.makedirs(bin_dir)
            os.makedirs(lib_dir)
            shutil.copy(EXE, os.path.join(bin_dir, "snakecell"))
            shutil.copy(os.path.join(ROOT, "snake_core.py"), os.path.join(lib_dir, "snake_core.py"))
            installed = os.path.join(bin_dir, "snakecell")
            proc = subprocess.run(
                [installed, "--demo", "--steps", "3", "--seed", "5"],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Score:", proc.stdout)
            self.assertIn("*", proc.stdout)


if __name__ == "__main__":
    unittest.main()
