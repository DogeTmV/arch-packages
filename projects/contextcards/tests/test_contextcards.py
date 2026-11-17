"""Offline unittest suite for the contextcards command line tool."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "contextcards"
DATE = "2026-04-02"  # a Thursday


def run(*args):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )


class ContextCardsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = os.path.join(self.tmp.name, "state")
        self.other = os.path.join(self.tmp.name, "other-state")

    def invoke(self, *args, directory=None):
        return run(args[0], *args[1:], "--dir", directory or self.dir)

    def state(self, directory=None):
        with open(os.path.join(directory or self.dir, "state.json"),
                  encoding="utf-8") as handle:
            return json.load(handle)

    def feed_file(self, events, name="events.json"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"events": events}, handle)
        return path

    def test_help_version_and_invalid_command(self):
        for flag in ("--help", "--version"):
            proc = run(flag)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("contextcards", run("--version").stdout)
        bad = self.invoke("bogus")
        self.assertNotEqual(bad.returncode, 0)
        self.assertTrue(bad.stderr.strip())

    def test_rule_list_and_remove(self):
        added = self.invoke("rule", "deadline", "--title", "Taxes",
                            "--body", "file by Friday", "--date", "2026-04-03",
                            "--tag", "admin")
        self.assertEqual(added.returncode, 0, added.stderr)
        listing = self.invoke("list")
        for text in ("deadline", "Taxes", "2026-04-03", "admin"):
            self.assertIn(text, listing.stdout)
        removed = self.invoke("rm", "deadline")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn("Taxes", self.invoke("list").stdout)
        self.assertNotEqual(self.invoke("rm", "deadline").returncode, 0)

    def test_show_selects_date_weekday_tag_and_always_rules(self):
        self.invoke("rule", "dated", "--title", "Dated card", "--body", "today",
                    "--date", DATE)
        self.invoke("rule", "weekly", "--title", "Weekly card", "--body", "thu",
                    "--weekday", "thu")
        self.invoke("rule", "traffic", "--title", "Traffic watch",
                    "--body", "leave early", "--tag", "commute")
        self.invoke("rule", "monday", "--title", "Monday card",
                    "--body", "wrong day", "--weekday", "MON")
        self.invoke("rule", "always", "--title", "Always card", "--body", "hello")
        events = [
            {"kind": "commute", "title": "Bridge closure", "body": "delays",
             "date": DATE, "tag": "commute", "time": "08:00"},
            {"kind": "weather", "title": "Rain", "body": "bring a coat",
             "weekday": "THU"},
            {"kind": "calendar", "title": "Meeting", "body": "10:00",
             "date": "2026-04-03"},
        ]
        fed = self.invoke("feed", self.feed_file(events))
        self.assertEqual(fed.returncode, 0, fed.stderr)
        shown = self.invoke("show", "--date", DATE)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        for text in ("2026-04-02 (THU)", "Dated card", "Weekly card",
                     "Traffic watch", "Always card", "Bridge closure", "Rain"):
            self.assertIn(text, shown.stdout)
        self.assertNotIn("Monday card", shown.stdout)
        self.assertNotIn("Meeting", shown.stdout)
        cleared = self.invoke("feed", self.feed_file([]))
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertNotIn("Traffic watch", self.invoke("show", "--date", DATE).stdout)
        self.assertEqual(self.state()["events"], [])

    def test_show_ordering_is_deterministic(self):
        self.invoke("rule", "z", "--title", "Zebra", "--body", "last")
        self.invoke("rule", "a", "--title", "Alpha", "--body", "first")
        self.invoke("rule", "m", "--title", "Middle", "--body", "middle")
        self.invoke("feed", self.feed_file([
            {"kind": "calendar", "title": "Early", "body": "timed",
             "date": DATE, "time": "07:30"},
        ]))
        first = self.invoke("show", "--date", DATE)
        second = self.invoke("show", "--date", DATE)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        positions = [first.stdout.index(name) for name in
                     ("Early", "Alpha", "Middle", "Zebra")]
        self.assertEqual(positions, sorted(positions))

    def test_html_output_escapes_user_text(self):
        self.invoke("rule", "xss", "--title", "<script>alert(1)</script>",
                    "--body", 'a & b "q" <b>x</b>')
        page = self.invoke("show", "--date", DATE, "--format", "html")
        self.assertEqual(page.returncode, 0, page.stderr)
        for text in ("&lt;script&gt;alert(1)&lt;/script&gt;", "&amp;",
                     "&quot;", "&lt;b&gt;x&lt;/b&gt;", "<!DOCTYPE html>"):
            self.assertIn(text, page.stdout)
        self.assertNotIn("<script>", page.stdout)
        self.assertNotIn("<b>x</b>", page.stdout)

    def test_export_import_round_trip(self):
        self.invoke("rule", "one", "--title", "Card", "--body", "details",
                    "--date", DATE, "--tag", "home")
        self.invoke("feed", self.feed_file([
            {"kind": "calendar", "title": "Local event", "body": "at home",
             "date": DATE, "tag": "home"},
        ]))
        out = os.path.join(self.tmp.name, "backup.json")
        exported = self.invoke("export", out)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        imported = self.invoke("import", out, directory=self.other)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(self.state(), self.state(self.other))
        self.assertEqual(self.invoke("show", "--date", DATE).stdout,
                         self.invoke("show", "--date", DATE,
                                     directory=self.other).stdout)
        self.assertEqual(Path(out).read_text(encoding="utf-8").count("Card"), 1)

    def test_invalid_weekday_date_feed_and_format(self):
        bad_weekday = self.invoke("rule", "bad", "--title", "x", "--body", "y",
                                  "--weekday", "FUNDAY")
        self.assertNotEqual(bad_weekday.returncode, 0)
        self.assertTrue(bad_weekday.stderr.strip())
        bad_date = self.invoke("rule", "bad2", "--title", "x", "--body", "y",
                               "--date", "2026-99-99")
        self.assertNotEqual(bad_date.returncode, 0)
        broken = os.path.join(self.tmp.name, "broken.json")
        Path(broken).write_text("{not json", encoding="utf-8")
        self.assertNotEqual(self.invoke("feed", broken).returncode, 0)
        self.assertNotEqual(
            self.invoke("show", "--date", DATE, "--format", "xml").returncode, 0)


if __name__ == "__main__":
    unittest.main()
