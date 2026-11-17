"""Behavioral tests for the chathoard CLI."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "chathoard"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ChathoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "store.json")

    def run_cli(self, *args):
        return subprocess.run(
            [str(SCRIPT), "--db", self.db, *map(str, args)],
            capture_output=True, text=True,
        )

    def import_fixture(self, name, service):
        result = self.run_cli("import", str(FIXTURES / name), "--service", service)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def first_id(self):
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()[0]

    def test_import_plain_log_preserves_timestamp_sender_and_text(self):
        self.import_fixture("aim.log", "aim")
        conv_id = self.first_id()
        shown = self.run_cli("show", conv_id)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("[2020-01-02 10:11] Alice: hello there", shown.stdout)
        self.assertIn("Bob", shown.stdout)

    def test_import_irc_log_splits_angle_bracket_sender(self):
        self.import_fixture("irc.log", "irc")
        conv_id = self.first_id()
        shown = self.run_cli("show", conv_id)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Alice", shown.stdout)
        self.assertIn("hi all", shown.stdout)
        self.assertNotIn("<Alice>", shown.stdout)

    def test_import_unstructured_log_keeps_every_nonempty_line(self):
        self.import_fixture("generic.log", "unknown")
        conv_id = self.first_id()
        shown = self.run_cli("show", conv_id)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("this line has no structure", shown.stdout)
        self.assertIn("a second unstructured line", shown.stdout)

    def test_importing_same_file_and_service_twice_does_not_duplicate(self):
        self.import_fixture("aim.log", "aim")
        self.import_fixture("aim.log", "aim")
        stats = self.run_cli("stats")
        self.assertEqual(stats.returncode, 0, stats.stderr)
        self.assertIn("conversations: 1", stats.stdout)
        self.assertIn("messages: 2", stats.stdout)

    def test_tag_then_tags_lists_the_tag(self):
        self.import_fixture("aim.log", "aim")
        conv_id = self.first_id()
        tagged = self.run_cli("tag", conv_id, "friends")
        self.assertEqual(tagged.returncode, 0, tagged.stderr)
        tags = self.run_cli("tags")
        self.assertIn("friends", tags.stdout)

    def test_search_is_case_insensitive_and_finds_message_body(self):
        self.import_fixture("aim.log", "aim")
        found = self.run_cli("search", "HELLO")
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertIn("hello there", found.stdout)
        self.assertIn("c-", found.stdout)

    def test_export_is_byte_identical_across_runs_and_self_contained(self):
        self.import_fixture("aim.log", "aim")
        out_a = os.path.join(self.tmp.name, "export-a")
        out_b = os.path.join(self.tmp.name, "export-b")
        first = self.run_cli("export", out_a, "--format", "html")
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_cli("export", out_b, "--format", "html")
        self.assertEqual(second.returncode, 0, second.stderr)
        names = sorted(os.listdir(out_a))
        self.assertEqual(names, sorted(os.listdir(out_b)))
        for name in names:
            a = Path(out_a, name).read_text()
            b = Path(out_b, name).read_text()
            self.assertEqual(a, b, name)
            self.assertNotIn("<link", a)
            self.assertNotIn("<script", a)
            self.assertNotIn("src=", a)

    def test_show_unknown_id_exits_nonzero_with_stderr_message(self):
        self.import_fixture("aim.log", "aim")
        shown = self.run_cli("show", "does-not-exist")
        self.assertNotEqual(shown.returncode, 0)
        self.assertTrue(shown.stderr.strip())

    def test_db_option_also_works_after_subcommand(self):
        db = os.path.join(self.tmp.name, "after.json")
        result = subprocess.run(
            [str(SCRIPT), "import", str(FIXTURES / "aim.log"), "--db", db],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(db))

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            result = subprocess.run([str(SCRIPT), flag], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
