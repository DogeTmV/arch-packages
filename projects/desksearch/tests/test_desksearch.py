"""Behavioral tests for the desksearch CLI."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "desksearch"


class DesksearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = str(self.base / "index.json")
        self.docs = self.base / "docs"
        self.docs.mkdir()
        self.other = self.base / "other"
        self.other.mkdir()

    def write(self, folder, name, text):
        path = folder / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def run_cli(self, *args):
        return subprocess.run(
            [str(SCRIPT), *map(str, args)],
            capture_output=True, text=True,
        )

    def index(self, *args):
        result = self.run_cli("index", "--db", self.db, *(args or (str(self.docs),)))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def search(self, query, *args):
        result = self.run_cli("search", query, "--db", self.db, *map(str, args))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_index_search_finds_all_terms_and_highlights_snippet(self):
        first = self.write(self.docs, "a.txt", "alpha beta are here together")
        self.write(self.docs, "b.txt", "alpha alone in this file")
        self.index()
        found = self.search("alpha beta")
        self.assertIn(first, found)
        self.assertNotIn("b.txt", found)
        self.assertIn("<mark>alpha</mark>", found)
        self.assertIn("<mark>beta</mark>", found)

    def test_search_limit_and_path_prefix(self):
        self.write(self.docs, "a.txt", "needle here")
        outside = self.write(self.other, "b.txt", "needle there")
        self.index(str(self.docs), str(self.other))
        limited = self.search("needle", "--limit", "1")
        self.assertEqual(len([line for line in limited.splitlines() if line]), 1)
        filtered = self.search("needle", "--path", str(self.other))
        self.assertIn(outside, filtered)
        self.assertNotIn("a.txt", filtered)

    def test_ranking_prefers_higher_term_frequency(self):
        quiet = self.write(self.docs, "quiet.txt", "zebra")
        loud = self.write(self.docs, "loud.txt", "zebra zebra zebra")
        self.index()
        lines = [line for line in self.search("zebra").splitlines() if line]
        self.assertIn(loud, lines[0])
        self.assertLess(lines.index(next(l for l in lines if loud in l)),
                        lines.index(next(l for l in lines if quiet in l)))

    def test_ranking_uses_recency_when_frequency_ties(self):
        old = self.write(self.docs, "old.txt", "sunrise")
        new = self.write(self.docs, "new.txt", "sunrise")
        os.utime(old, (1000000000, 1000000000))
        os.utime(new, (1600000000, 1600000000))
        self.index()
        lines = [line for line in self.search("sunrise").splitlines() if line]
        self.assertIn(new, lines[0])

    def test_index_skips_binary_and_files_over_max_bytes(self):
        self.write(self.docs, "small.txt", "findme")
        (self.docs / "binary.txt").write_bytes(b"findme\x00binary")
        self.write(self.docs, "huge.txt", "findme " * 100)
        self.index(str(self.docs), "--max-bytes", "40")
        found = self.search("findme")
        self.assertIn("small.txt", found)
        self.assertNotIn("binary.txt", found)
        self.assertNotIn("huge.txt", found)

    def test_ignore_globs_keep_matching_files_out_of_index(self):
        self.write(self.docs, "keep.txt", "secretword")
        self.write(self.docs, "skip.log", "secretword")
        added = self.run_cli("ignore", "*.log", "--db", self.db)
        self.assertEqual(added.returncode, 0, added.stderr)
        self.index()
        found = self.search("secretword")
        self.assertIn("keep.txt", found)
        self.assertNotIn("skip.log", found)
        listed = self.run_cli("list-ignores", "--db", self.db)
        self.assertIn("*.log", listed.stdout)

    def test_reindex_drops_files_deleted_from_disk(self):
        gone = self.write(self.docs, "gone.txt", "vanishing")
        self.index()
        self.assertIn("vanishing", self.search("vanishing"))
        os.remove(gone)
        self.index()
        status = self.run_cli("status", "--db", self.db)
        self.assertIn("files: 0", status.stdout)

    def test_clear_empties_index_and_ignore_list(self):
        self.write(self.docs, "a.txt", "clearword")
        self.run_cli("ignore", "*.tmp", "--db", self.db)
        self.index()
        cleared = self.run_cli("clear", "--db", self.db)
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        status = self.run_cli("status", "--db", self.db)
        self.assertIn("files: 0", status.stdout)
        self.assertIn("roots: 0", status.stdout)
        self.assertIn("(none)", self.run_cli("list-ignores", "--db", self.db).stdout)

    def test_search_without_usable_terms_exits_nonzero(self):
        self.index()
        result = self.run_cli("search", "!!!", "--db", self.db)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())

    def test_db_option_also_works_after_subcommand(self):
        other_db = str(self.base / "after.json")
        result = self.run_cli("ignore", "*.bak", "--db", other_db)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(other_db))

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            result = subprocess.run([str(SCRIPT), flag], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
