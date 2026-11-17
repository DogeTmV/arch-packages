"""Behavioral tests for the bookmarkdeck CLI."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bookmarkdeck"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bookmarks.html"


class BookmarkdeckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "bookmarks.json")

    def run_cli(self, *args):
        return subprocess.run(
            [str(SCRIPT), "--db", self.db, *map(str, args)],
            capture_output=True, text=True,
        )

    def import_fixture(self):
        result = self.run_cli("import", str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)

    def id_for_url(self, url):
        result = self.run_cli("search", url)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()[0]

    def test_import_turns_nested_folders_into_tags(self):
        self.import_fixture()
        work = self.run_cli("list", "--tag", "Work")
        archived = self.run_cli("list", "--tag", "Archived")
        self.assertIn("Work Docs", work.stdout)
        self.assertIn("Old Site", work.stdout)
        self.assertIn("Old Site", archived.stdout)
        self.assertNotIn("Work Docs", archived.stdout)

    def test_import_preserves_titles_and_tags_attribute(self):
        self.import_fixture()
        listed = self.run_cli("list")
        self.assertIn("Work Docs", listed.stdout)
        self.assertIn("docs", listed.stdout)
        self.assertIn("reference", listed.stdout)
        self.assertIn("https://example.com/", listed.stdout)

    def test_export_html_round_trips_through_import(self):
        self.import_fixture()
        exported = os.path.join(self.tmp.name, "exported.html")
        result = self.run_cli("export", exported)
        self.assertEqual(result.returncode, 0, result.stderr)
        html_text = Path(exported).read_text()
        self.assertIn("NETSCAPE-Bookmark-file-1", html_text)
        self.assertIn('HREF="https://work.example.com/docs"', html_text)

        other_db = os.path.join(self.tmp.name, "other.json")
        imported = subprocess.run(
            [str(SCRIPT), "--db", other_db, "import", exported],
            capture_output=True, text=True,
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)
        before = self.run_cli("list").stdout
        after = subprocess.run(
            [str(SCRIPT), "--db", other_db, "list"], capture_output=True, text=True,
        ).stdout
        self.assertEqual(before, after)

    def test_add_records_url_title_and_comma_separated_tags(self):
        result = self.run_cli("add", "https://new.example.com/x",
                              "--title", "New Site", "--tags", "news,tech")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = self.run_cli("list", "--tag", "news")
        self.assertIn("New Site", listed.stdout)
        self.assertIn("https://new.example.com/x", listed.stdout)

    def test_rm_removes_the_bookmark(self):
        self.import_fixture()
        bookmark_id = self.id_for_url("https://example.com/")
        removed = self.run_cli("rm", bookmark_id)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn("Example", self.run_cli("list").stdout)

    def test_search_matches_url_case_insensitively(self):
        self.import_fixture()
        found = self.run_cli("search", "WORK.EXAMPLE.COM")
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertIn("Work Docs", found.stdout)

    def test_tag_adds_multiple_tags_to_one_bookmark(self):
        self.import_fixture()
        bookmark_id = self.id_for_url("https://example.com/")
        result = self.run_cli("tag", bookmark_id, "alpha", "beta")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Example", self.run_cli("list", "--tag", "alpha").stdout)
        self.assertIn("Example", self.run_cli("list", "--tag", "beta").stdout)

    def test_open_dry_run_prints_command_and_does_not_launch(self):
        self.import_fixture()
        bookmark_id = self.id_for_url("https://example.com/")
        result = self.run_cli("open", bookmark_id, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "xdg-open https://example.com/")

    def test_stats_counts_bookmarks_and_tags(self):
        self.import_fixture()
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bookmarks: 3", result.stdout)
        self.assertIn("tags:", result.stdout)

    def test_unknown_id_exits_nonzero_with_stderr_message(self):
        self.import_fixture()
        result = self.run_cli("rm", "missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())

    def test_db_option_also_works_after_subcommand(self):
        other_db = os.path.join(self.tmp.name, "after.json")
        result = subprocess.run(
            [str(SCRIPT), "import", str(FIXTURE), "--db", other_db],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(other_db))

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            result = subprocess.run([str(SCRIPT), flag], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
