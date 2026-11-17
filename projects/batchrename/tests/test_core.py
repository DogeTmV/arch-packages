"""Core tests for batchrename (offline, temporary files only)."""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import BatchrenameError, apply_plan, build_plan, expand_pattern


class ExpandPatternTest(unittest.TestCase):
    def test_all_four_tokens_are_replaced(self):
        self.assertEqual(
            expand_pattern("{name}_{n}_{nn}.{ext}", "photo", 7, "jpg"),
            "photo_7_07.jpg",
        )

    def test_double_digit_token_zero_pads_small_indexes(self):
        self.assertEqual(expand_pattern("{nn}", "x", 3, "txt"), "03")
        self.assertEqual(expand_pattern("{nn}", "x", 42, "txt"), "42")

    def test_unknown_tokens_are_left_untouched(self):
        self.assertEqual(expand_pattern("{name}-{date}", "a", 1, "txt"), "a-{date}")


class BuildPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        self.first = os.path.join(self.dir, "photo1.jpg")
        self.second = os.path.join(self.dir, "photo2.jpg")
        self.readme = os.path.join(self.dir, "README")
        for path in (self.first, self.second, self.readme):
            with open(path, "wb"):
                pass

    def test_plan_preserves_input_order_and_original_extension(self):
        plan = build_plan([self.second, self.first], "{name}_{nn}")
        self.assertEqual(plan, [
            (self.second, os.path.join(self.dir, "photo2_01.jpg")),
            (self.first, os.path.join(self.dir, "photo1_02.jpg")),
        ])

    def test_start_index_shifts_numbering(self):
        plan = build_plan([self.first, self.second], "{name}_{n}", start=5)
        self.assertEqual(plan, [
            (self.first, os.path.join(self.dir, "photo1_5.jpg")),
            (self.second, os.path.join(self.dir, "photo2_6.jpg")),
        ])

    def test_ext_token_does_not_duplicate_the_extension(self):
        plan = build_plan([self.first], "{name}_{n}.{ext}")
        self.assertEqual(plan, [
            (self.first, os.path.join(self.dir, "photo1_1.jpg")),
        ])

    def test_file_without_extension_gets_no_appended_suffix(self):
        plan = build_plan([self.readme], "{name}_{n}")
        self.assertEqual(plan, [
            (self.readme, os.path.join(self.dir, "README_1")),
        ])

    def test_duplicate_destination_paths_raise_clear_error(self):
        with self.assertRaisesRegex(BatchrenameError, "duplicate destination"):
            build_plan([self.first, self.second], "same")


class ApplyPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = os.path.join(self.tmp.name, "clip.wav")
        with open(self.source, "wb"):
            pass
        self.destination = os.path.join(self.tmp.name, "clip_01.wav")
        self.plan = [(self.source, self.destination)]

    def test_dry_run_returns_planned_pairs_without_touching_files(self):
        result = apply_plan(self.plan, dry_run=True)
        self.assertEqual(result, self.plan)
        self.assertTrue(os.path.exists(self.source))
        self.assertFalse(os.path.exists(self.destination))

    def test_apply_performs_the_rename(self):
        apply_plan(self.plan)
        self.assertFalse(os.path.exists(self.source))
        self.assertTrue(os.path.exists(self.destination))


if __name__ == "__main__":
    unittest.main()
