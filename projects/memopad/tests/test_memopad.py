"""CLI-level tests for memopad (offline, temporary JSON database)."""

import csv
import json
import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "memopad")


class MemopadCLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "memopad.json")

    def run_cli(self, *args, check=True):
        proc = subprocess.run(
            [EXE] + [str(a) for a in args],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if check and proc.returncode != 0:
            self.fail(
                "memopad %s failed (%d): %s"
                % (" ".join(str(a) for a in args), proc.returncode, proc.stderr)
            )
        return proc

    def add(self, text, category=None):
        args = ["add", text, "--db", self.db]
        if category:
            args += ["--category", category]
        return self.run_cli(*args)

    def test_deterministic_ids_are_not_reused_after_removal(self):
        first = self.add("first memo").stdout
        second = self.add("second memo").stdout
        self.assertRegex(first, r"\b1\b")
        self.assertRegex(second, r"\b2\b")
        self.run_cli("rm", "1", "--db", self.db)
        listing = self.run_cli("list", "--db", self.db).stdout
        self.assertIn("second memo", listing)
        self.assertNotIn("first memo", listing)
        third = self.add("third memo").stdout
        self.assertRegex(third, r"\b3\b")

    def test_edit_and_category_update_existing_memo(self):
        self.add("original text", "Ideas")
        self.run_cli("edit", "1", "updated text", "--db", self.db)
        self.run_cli("category", "1", "Work", "--db", self.db)
        shown = self.run_cli("show", "1", "--db", self.db).stdout
        self.assertIn("updated text", shown)
        self.assertNotIn("original text", shown)
        self.assertIn("Work", shown)
        self.assertIn("Work", self.run_cli("categories", "--db", self.db).stdout)

    def test_search_is_case_insensitive_over_text_and_category(self):
        self.add("A TURTLE story", "Nature")
        self.add("grocery list", "Home")
        self.assertIn("TURTLE", self.run_cli("search", "turtle", "--db", self.db).stdout)
        self.assertIn("A TURTLE story", self.run_cli("search", "nature", "--db", self.db).stdout)
        self.assertNotIn("grocery", self.run_cli("search", "turtle", "--db", self.db).stdout)

    def test_list_honours_category_and_limit(self):
        self.add("alpha", "Work")
        self.add("beta", "Home")
        self.add("gamma", "Work")
        work = self.run_cli("list", "--category", "Work", "--db", self.db).stdout
        self.assertIn("alpha", work)
        self.assertIn("gamma", work)
        self.assertNotIn("beta", work)
        limited = self.run_cli("list", "--limit", "1", "--db", self.db).stdout
        self.assertEqual(len([line for line in limited.splitlines() if line.strip()]), 1)

    def test_json_export_can_be_imported_into_a_fresh_database(self):
        self.add("keep me", "Travels")
        self.add("and me", "Travels")
        exported = os.path.join(self.tmp.name, "memos.json")
        self.run_cli("export", exported, "--format", "json", "--db", self.db)
        with open(exported, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["memos"]), 2)

        other = os.path.join(self.tmp.name, "other.json")
        self.run_cli("import", exported, "--db", other)
        listing = self.run_cli("list", "--db", other).stdout
        self.assertIn("keep me", listing)
        self.assertIn("and me", listing)
        self.assertIn("Travels", listing)

    def test_csv_export_can_be_imported_into_a_fresh_database(self):
        self.add("comma, quote \" and more", "Quotes")
        self.add("second line\nwith newline", "Notes")
        exported = os.path.join(self.tmp.name, "memos.csv")
        self.run_cli("export", exported, "--format", "csv", "--db", self.db)
        with open(exported, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["text"], "comma, quote \" and more")

        other = os.path.join(self.tmp.name, "other.json")
        self.run_cli("import", exported, "--db", other)
        listing = self.run_cli("list", "--db", other).stdout
        self.assertIn("comma, quote", listing)
        self.assertIn("second line", listing)
        self.assertIn("Quotes", listing)

    def test_stats_reports_counts(self):
        self.add("one", "A")
        self.add("two", "B")
        stats = self.run_cli("stats", "--db", self.db).stdout
        self.assertIn("2", stats)
        self.assertIn("categories", stats.lower())

    def test_show_unknown_id_fails_with_useful_stderr(self):
        proc = self.run_cli("show", "404", "--db", self.db, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_help_and_version_work_without_a_tty(self):
        help_proc = self.run_cli("--help")
        self.assertEqual(help_proc.returncode, 0)
        self.assertIn("usage", help_proc.stdout.lower())
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)

    def test_state_is_json_at_selected_path(self):
        self.add("persisted", "General")
        with open(self.db, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["memos"][0]["text"], "persisted")
        self.assertEqual(data["memos"][0]["category"], "General")
        self.assertTrue(data["memos"][0]["created"])
        self.assertTrue(data["memos"][0]["updated"])


if __name__ == "__main__":
    unittest.main()
