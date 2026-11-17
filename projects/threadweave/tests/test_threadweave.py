"""Offline tests for the threadweave mbox browser."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "threadweave"
MBOX = Path(__file__).resolve().parent / "fixtures" / "sample.mbox"


def run(*args, env=None):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, env=env)


class ThreadweaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "store.json")
        self.assertEqual(run("import", str(MBOX), "--db", self.db).returncode, 0)

    def thread_ids(self):
        return [line.split()[0] for line in run("list", "--db", self.db).stdout.splitlines()]

    def test_import_then_stats_counts_messages_and_threads(self):
        stats = run("stats", "--db", self.db)
        self.assertEqual(stats.returncode, 0, stats.stderr)
        self.assertIn("messages: 4", stats.stdout)
        self.assertIn("threads: 3", stats.stdout)

    def test_reimport_replaces_store_without_duplicating(self):
        self.assertEqual(run("import", str(MBOX), "--db", self.db).returncode, 0)
        self.assertIn("messages: 4", run("stats", "--db", self.db).stdout)

    def test_list_respects_limit_and_includes_thread_ids(self):
        listing = run("list", "--db", self.db, "--limit", "2")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(len(listing.stdout.splitlines()), 2)
        self.assertEqual(len(self.thread_ids()), 3)

    def test_show_text_groups_reply_with_original_subject(self):
        garden = next(
            tid for tid in self.thread_ids()
            if "Garden plan" in run("show", tid, "--db", self.db).stdout
        )
        shown = run("show", garden, "--db", self.db)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Let's plant beans", shown.stdout)
        self.assertIn("Beans need a trellis", shown.stdout)
        self.assertIn("Alice", shown.stdout)
        self.assertIn("Bob", shown.stdout)

    def test_show_html_escapes_message_bodies(self):
        garden = next(
            tid for tid in self.thread_ids()
            if "trellis" in run("show", tid, "--db", self.db).stdout
        )
        shown = run("show", garden, "--db", self.db, "--format", "html")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("<!DOCTYPE html>", shown.stdout)
        self.assertIn("&lt;b&gt;soon&lt;/b&gt;", shown.stdout)
        self.assertNotIn("<b>soon</b>", shown.stdout)

    def test_search_finds_body_terms_and_rejects_empty_results(self):
        found = run("search", "trellis", "--db", self.db)
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(len(found.stdout.splitlines()), 1)
        self.assertIn("Garden plan", found.stdout)
        self.assertEqual(run("search", "no-such-word", "--db", self.db).stdout.strip(), "")

    def test_export_writes_one_html_file_per_thread(self):
        outdir = Path(self.tmp.name) / "export"
        result = run("export", str(outdir), "--db", self.db)
        self.assertEqual(result.returncode, 0, result.stderr)
        files = list(outdir.glob("*.html"))
        self.assertEqual(len(files), 3)
        self.assertTrue(all("<h1>" in path.read_text(encoding="utf-8") for path in files))

    def test_default_store_lives_under_home(self):
        home = Path(self.tmp.name) / "home"
        env = dict(os.environ, HOME=str(home))
        result = run("import", str(MBOX), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home / ".local/share/threadweave/store.json").is_file())
        self.assertIn("messages: 4", run("stats", env=env).stdout)

    def test_missing_store_and_unknown_thread_fail_cleanly(self):
        result = run("stats", "--db", str(Path(self.tmp.name) / "missing.json"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no store", result.stderr)
        self.assertNotEqual(run("show", "does-not-exist", "--db", self.db).returncode, 0)

    def test_help_and_version_exit_zero(self):
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run("show", "--help").returncode, 0)
        version = run("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)


if __name__ == "__main__":
    unittest.main()
