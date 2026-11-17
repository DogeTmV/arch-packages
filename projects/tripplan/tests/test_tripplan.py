"""Offline unittest suite for the tripplan command line tool."""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tripplan"


def run(*args):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )


class TripPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = os.path.join(self.tmp.name, "trips")
        self.other = os.path.join(self.tmp.name, "other-trips")

    def invoke(self, *args, directory=None):
        return run(args[0], *args[1:], "--dir", directory or self.dir)

    def trip(self, name="Kyoto", directory=None):
        path = Path(directory or self.dir) / (name.lower().replace(" ", "-") + ".json")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_help_version_and_invalid_command(self):
        for flag in ("--help", "--version"):
            proc = run(flag)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("tripplan", run("--version").stdout)
        bad = self.invoke("bogus")
        self.assertNotEqual(bad.returncode, 0)
        self.assertTrue(bad.stderr.strip())

    def test_new_creates_trip_and_list_shows_date_range(self):
        proc = self.invoke("new", "Kyoto Trip", "--start", "2026-04-01",
                           "--end", "2026-04-05")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.trip("Kyoto Trip")
        self.assertEqual(data["start"], "2026-04-01")
        self.assertEqual(data["items"], [])
        listing = self.invoke("list")
        self.assertIn("Kyoto Trip", listing.stdout)
        self.assertIn("2026-04-01", listing.stdout)
        self.assertIn("2026-04-05", listing.stdout)
        self.assertNotEqual(
            self.invoke("new", "Kyoto Trip", "--start", "2026-04-01").returncode,
            0)

    def test_add_show_filter_and_remove_items(self):
        self.invoke("new", "Trip", "--start", "2026-04-01", "--end", "2026-04-03")
        self.invoke("add", "Trip", "Zoo", "--date", "2026-04-03",
                    "--time", "10:00", "--location", "City Zoo",
                    "--notes", "bring map", "--type", "sight")
        self.invoke("add", "Trip", "Breakfast", "--date", "2026-04-02",
                    "--time", "08:30", "--type", "food")
        shown = self.invoke("show", "Trip")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertLess(shown.stdout.index("Breakfast"), shown.stdout.index("Zoo"))
        self.assertIn("City Zoo", shown.stdout)
        filtered = self.invoke("show", "Trip", "--date", "2026-04-03")
        self.assertIn("Zoo", filtered.stdout)
        self.assertNotIn("Breakfast", filtered.stdout)
        item_id = next(i["id"] for i in self.trip("Trip")["items"]
                       if i["title"] == "Breakfast")
        removed = self.invoke("rm", "Trip", item_id)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertEqual(len(self.trip("Trip")["items"]), 1)
        self.assertNotEqual(self.invoke("rm", "Trip", item_id).returncode, 0)

    def test_ics_export_is_crlf_escaped_folded_and_stable(self):
        self.invoke("new", "Expo", "--start", "2026-05-01", "--end", "2026-05-02")
        self.invoke("add", "Expo", "Meet, greet; plan\\draft\nsecond line",
                    "--date", "2026-05-01", "--time", "09:15",
                    "--location", "Hall A;B", "--notes", "line one\nline two")
        self.invoke("add", "Expo", "All day", "--date", "2026-05-02")
        first = os.path.join(self.tmp.name, "first.ics")
        second = os.path.join(self.tmp.name, "second.ics")
        self.assertEqual(self.invoke("export", "Expo", first,
                                     "--format", "ics").returncode, 0)
        self.assertEqual(self.invoke("export", "Expo", second,
                                     "--format", "ics").returncode, 0)
        raw = Path(first).read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))
        text = raw.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR\r\nVERSION:2.0", text)
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        unfolded = text.replace("\r\n ", "")
        self.assertIn("DTSTART:20260501T091500", unfolded)
        self.assertIn("DTEND:20260501T101500", unfolded)
        self.assertIn("DTSTART;VALUE=DATE:20260502", unfolded)
        self.assertIn("DTEND;VALUE=DATE:20260503", unfolded)
        self.assertIn("SUMMARY:Meet\\, greet\\; plan\\\\draft\\nsecond line",
                      unfolded)
        self.assertIn("LOCATION:Hall A\\;B", unfolded)
        self.assertIn("DESCRIPTION:line one\\nline two", unfolded)
        uids = lambda path: re.findall(r"^UID:(.+)$", Path(path).read_text(),
                                       flags=re.MULTILINE)
        self.assertEqual(len(uids(first)), 2)
        self.assertEqual(uids(first), uids(second))
        self.assertTrue(all(uid.endswith("@tripplan") for uid in uids(first)))
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_markdown_export_and_json_round_trip(self):
        self.invoke("new", "Berlin", "--start", "2026-06-01", "--end", "2026-06-02")
        added = self.invoke("add", "Berlin", "Museum", "--date", "2026-06-01",
                            "--time", "11:00", "--notes", "tickets")
        self.assertEqual(added.returncode, 0, added.stderr)
        md = os.path.join(self.tmp.name, "trip.md")
        exported = self.invoke("export", "Berlin", md, "--format", "md")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertIn("# Berlin", Path(md).read_text(encoding="utf-8"))
        self.assertIn("Museum", Path(md).read_text(encoding="utf-8"))
        js = os.path.join(self.tmp.name, "trip.json")
        self.assertEqual(self.invoke("export", "Berlin", js,
                                     "--format", "json").returncode, 0)
        imported = self.invoke("import", "Copied", js, directory=self.other)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertIn("Museum", self.invoke("show", "Copied",
                                            directory=self.other).stdout)
        self.assertEqual(self.trip("Berlin")["items"],
                         self.trip("Copied", self.other)["items"])

    def test_invalid_dates_times_formats_and_missing_trips(self):
        bad_date = self.invoke("new", "Bad", "--start", "2026-13-99")
        self.assertNotEqual(bad_date.returncode, 0)
        self.assertTrue(bad_date.stderr.strip())
        self.invoke("new", "Trip", "--start", "2026-04-01")
        bad_time = self.invoke("add", "Trip", "Dinner", "--time", "25:99")
        self.assertNotEqual(bad_time.returncode, 0)
        self.assertNotEqual(self.invoke("show", "Missing").returncode, 0)
        self.assertNotEqual(self.invoke("add", "Missing", "Thing").returncode, 0)
        bad_format = self.invoke("export", "Trip",
                                 os.path.join(self.tmp.name, "x.txt"),
                                 "--format", "txt")
        self.assertNotEqual(bad_format.returncode, 0)

    def test_stats_counts_trips_and_items(self):
        self.assertIn("Trips: 0", self.invoke("stats").stdout)
        self.invoke("new", "One")
        self.invoke("new", "Two")
        self.invoke("add", "One", "A")
        self.invoke("add", "One", "B")
        self.invoke("add", "Two", "C")
        stats = self.invoke("stats")
        self.assertIn("Trips: 2", stats.stdout)
        self.assertIn("Items: 3", stats.stdout)

    def test_empty_list_is_friendly(self):
        self.assertIn("No trips", self.invoke("list").stdout)


if __name__ == "__main__":
    unittest.main()
