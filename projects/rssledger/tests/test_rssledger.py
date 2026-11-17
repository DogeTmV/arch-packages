"""Offline unittest suite for the rssledger command line tool."""

import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "rssledger"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def file_url(path):
    return "file://" + str(path)


def run(*args, env=None):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30,
    )


def load_module():
    loader = importlib.machinery.SourceFileLoader("rssledger_impl", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class RSSLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "state.json")
        self.env = os.environ.copy()
        self.env.pop("RSSLEDGER_DB", None)

    def invoke(self, *args, db=None, env=None):
        return run("--db", db or self.db, *args, env=env or self.env)

    def state(self, db=None):
        with open(db or self.db, encoding="utf-8") as handle:
            return json.load(handle)

    def add_feed(self, fixture="rss.xml", db=None):
        return self.invoke("add", file_url(FIXTURES / fixture), db=db)

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            proc = run(flag, env=self.env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        version = run("--version", env=self.env)
        self.assertIn("rssledger", version.stdout)

    def test_add_file_feed_and_list(self):
        proc = self.add_feed()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Added feed", proc.stdout)
        listing = self.invoke("list")
        self.assertIn("Example RSS Feed", listing.stdout)
        self.assertEqual(len(self.state()["feeds"]), 1)

    def test_fetch_populates_items_from_rss(self):
        self.add_feed()
        fetched = self.invoke("fetch")
        self.assertEqual(fetched.returncode, 0, fetched.stderr)
        self.assertIn("Fetched", fetched.stdout)
        listing = self.invoke("unread")
        self.assertIn("First Story", listing.stdout)
        self.assertIn("Second Story", listing.stdout)
        self.assertEqual(len(self.state()["items"]), 2)

    def test_fetch_atom_feed(self):
        self.add_feed("atom.xml")
        self.invoke("fetch")
        listing = self.invoke("unread")
        self.assertIn("Atom Alpha", listing.stdout)
        self.assertIn("Atom Beta", listing.stdout)

    def test_item_ids_are_stable_across_runs(self):
        other_db = os.path.join(self.tmp.name, "other.json")
        self.add_feed(db=self.db)
        self.invoke("fetch", db=self.db)
        self.add_feed(db=other_db)
        self.invoke("fetch", db=other_db)
        ids_a = [item["id"] for item in self.state(self.db)["items"]]
        ids_b = [item["id"] for item in self.state(other_db)["items"]]
        self.assertEqual(ids_a, ids_b)
        for item_id in ids_a:
            self.assertRegex(item_id, r"^[0-9a-f]{16}$")

    def test_malformed_feed_is_handled_gracefully(self):
        proc = self.add_feed("malformed.xml")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("warning", proc.stderr.lower())
        self.assertEqual(len(self.state()["items"]), 0)
        self.assertEqual(len(self.state()["feeds"]), 1)

    def test_read_and_unread_item(self):
        self.add_feed()
        self.invoke("fetch")
        item_id = self.state()["items"][0]["id"]
        marked = self.invoke("read", item_id)
        self.assertEqual(marked.returncode, 0, marked.stderr)
        self.assertTrue(self.state()["items"][0]["read"])
        self.assertNotIn("First Story", self.invoke("unread").stdout)
        self.invoke("unread", item_id)
        self.assertFalse(self.state()["items"][0]["read"])
        self.assertIn("First Story", self.invoke("unread").stdout)

    def test_search_matches_title_and_description_case_insensitively(self):
        self.add_feed()
        self.invoke("fetch")
        result = self.invoke("search", "python")
        self.assertIn("Second Story", result.stdout)
        self.assertNotIn("First Story", result.stdout)
        self.assertIn("No matches", self.invoke("search", "zzzznotfound").stdout)

    def test_remove_feed_also_removes_its_items(self):
        self.add_feed()
        self.invoke("fetch")
        feed_id = self.state()["feeds"][0]["id"]
        removed = self.invoke("remove", feed_id)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertEqual(self.state()["feeds"], [])
        self.assertEqual(self.state()["items"], [])
        again = self.invoke("remove", feed_id)
        self.assertNotEqual(again.returncode, 0)

    def test_opml_export_import_round_trip(self):
        self.invoke("import-opml", FIXTURES / "subscriptions.opml")
        exported = os.path.join(self.tmp.name, "export.opml")
        proc = self.invoke("export-opml", exported)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(exported, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("xmlUrl=", text)
        other_db = os.path.join(self.tmp.name, "imported.json")
        self.invoke("import-opml", exported, db=other_db)
        pair = lambda feeds: sorted((f["url"], f["title"]) for f in feeds)
        self.assertEqual(pair(self.state()["feeds"]), pair(self.state(other_db)["feeds"]))

    def test_stats_counts_feeds_items_and_unread(self):
        self.add_feed()
        self.invoke("fetch")
        stats = self.invoke("stats")
        for line in ("Feeds: 1", "Items: 2", "Unread: 2", "Read: 0"):
            self.assertIn(line, stats.stdout)
        self.invoke("read", self.state()["items"][0]["id"])
        self.assertIn("Unread: 1", self.invoke("stats").stdout)

    def test_environment_database_override_and_cli_precedence(self):
        env_db = os.path.join(self.tmp.name, "env.json")
        env = self.env.copy()
        env["RSSLEDGER_DB"] = env_db
        proc = run("add", file_url(FIXTURES / "rss.xml"), env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(env_db))
        self.assertFalse(os.path.exists(self.db))
        run("--db", self.db, "add", file_url(FIXTURES / "rss.xml"), env=env)
        self.assertTrue(os.path.exists(self.db))

    def test_parse_feed_unit_for_rss_atom_and_bad_xml(self):
        module = load_module()
        meta, items = module.parse_feed((FIXTURES / "rss.xml").read_bytes())
        self.assertEqual(meta["title"], "Example RSS Feed")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["link"], "https://example.org/1")
        meta, items = module.parse_feed((FIXTURES / "atom.xml").read_bytes())
        self.assertEqual(meta["title"], "Example Atom Feed")
        self.assertEqual(items[0]["title"], "Atom Alpha")
        self.assertIsNone(module.parse_feed((FIXTURES / "malformed.xml").read_bytes()))

    def test_second_fetch_of_unchanged_feed_is_skipped(self):
        self.add_feed()
        self.invoke("fetch")
        second = self.invoke("fetch")
        self.assertIn("Unchanged", second.stdout)
        self.assertEqual(len(self.state()["items"]), 2)

    def test_fetch_single_feed_by_id(self):
        self.add_feed()
        self.add_feed("atom.xml")
        feed_id = self.state()["feeds"][0]["id"]
        proc = self.invoke("fetch", feed_id)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.state()["items"]), 2)
        self.assertEqual(self.state()["items"][0]["title"], "First Story")

    def test_invalid_command_returns_nonzero(self):
        proc = self.invoke("bogus-command")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())


if __name__ == "__main__":
    unittest.main()
