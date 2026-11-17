"""Offline unittest suite for the pipeway pipeline tool."""

import json
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "pipeway"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(*args):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )


class PipewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def config(self, stages):
        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"stages": stages}, handle)
        return path

    def run_config(self, stages, *extra):
        return run("run", self.config(stages), *extra)

    def titles_from_json(self, proc):
        return [item["title"] for item in json.loads(proc.stdout)]

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            proc = run(flag)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("pipeway", run("--version").stdout)

    def test_validate_accepts_a_correct_config(self):
        proc = run("validate", self.config([
            {"stage": "fetch", "url": "file:///tmp/f.xml"},
            {"stage": "sort", "field": "title", "order": "desc"},
            {"stage": "format", "type": "json", "title": "Demo"},
        ]))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_validate_reports_unknown_stage_precisely(self):
        proc = run("validate", self.config([{"stage": "fetc", "url": "x"}]))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown stage", proc.stderr.lower())
        self.assertIn("fetc", proc.stderr)
        self.assertIn("stage 0", proc.stderr)

    def test_validate_reports_missing_required_keys(self):
        proc = run("validate", self.config([
            {"stage": "match", "pattern": "x"},
            {"stage": "fetch"},
        ]))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("stage 0 (match): missing required key 'field'", proc.stderr)
        self.assertIn("stage 1 (fetch): missing required key 'url'", proc.stderr)

    def test_validate_checks_enums_and_counts(self):
        bad_order = run("validate", self.config([
            {"stage": "sort", "field": "x", "order": "sideways"},
        ]))
        self.assertNotEqual(bad_order.returncode, 0)
        self.assertIn("order", bad_order.stderr)
        bad_limit = run("validate", self.config([{"stage": "limit", "count": 0}]))
        self.assertNotEqual(bad_limit.returncode, 0)
        self.assertIn("count", bad_limit.stderr)
        bad_format = run("validate", self.config([{"stage": "format", "type": "yaml"}]))
        self.assertNotEqual(bad_format.returncode, 0)
        self.assertIn("format", bad_format.stderr)

    def test_example_prints_a_working_config(self):
        proc = run("example")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        config = json.loads(proc.stdout)
        self.assertIn("stages", config)
        path = os.path.join(self.tmp.name, "example.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(proc.stdout)
        validated = run("validate", path)
        self.assertEqual(validated.returncode, 0, validated.stderr)

    def test_match_stage_keeps_only_matching_items(self):
        proc = self.run_config([
            {"stage": "match", "field": "title", "pattern": "Alpha"},
            {"stage": "format", "type": "json"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.titles_from_json(proc), ["Alpha", "Alpha Again"])

    def test_exclude_stage_drops_matching_items(self):
        proc = self.run_config([
            {"stage": "exclude", "field": "description", "pattern": "dog"},
            {"stage": "format", "type": "json"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.titles_from_json(proc), ["Zebra", "Alpha Again"])

    def test_dedupe_stage_keeps_first_occurrence(self):
        proc = self.run_config([
            {"stage": "dedupe", "field": "link"},
            {"stage": "format", "type": "json"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.titles_from_json(proc), ["Zebra", "Alpha"])

    def test_sort_stage_respects_order(self):
        base = [{"stage": "sort", "field": "title", "order": "asc"},
                {"stage": "format", "type": "json"}]
        asc = self.run_config(base, "--input", FIXTURES / "items.json")
        self.assertEqual(self.titles_from_json(asc), ["Alpha", "Alpha Again", "Zebra"])
        base[0]["order"] = "desc"
        desc = self.run_config(base, "--input", FIXTURES / "items.json")
        self.assertEqual(self.titles_from_json(desc), ["Zebra", "Alpha Again", "Alpha"])

    def test_limit_stage_caps_item_count(self):
        proc = self.run_config([
            {"stage": "limit", "count": 2},
            {"stage": "format", "type": "json"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.titles_from_json(proc), ["Zebra", "Alpha"])

    def test_format_rss_emits_valid_rss_with_title(self):
        proc = self.run_config([
            {"stage": "match", "field": "title", "pattern": "Alpha"},
            {"stage": "format", "type": "rss", "title": "My Pipeline"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        root = ET.fromstring(proc.stdout)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.get("version"), "2.0")
        channel = root.find("channel")
        self.assertEqual(channel.findtext("title"), "My Pipeline")
        self.assertEqual(len(channel.findall("item")), 2)

    def test_format_text_emits_readable_lines(self):
        proc = self.run_config([
            {"stage": "limit", "count": 1},
            {"stage": "format", "type": "text", "title": "Header"},
        ], "--input", FIXTURES / "items.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Header", proc.stdout)
        self.assertIn("Zebra", proc.stdout)

    def test_fetch_stage_reads_local_feed(self):
        url = "file://" + str(FIXTURES / "feed.xml")
        proc = self.run_config([
            {"stage": "fetch", "url": url},
            {"stage": "format", "type": "json"},
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.titles_from_json(proc),
                         ["Alpha Beta", "Gamma", "Alpha Delta"])

    def test_full_pipeline_offline(self):
        url = "file://" + str(FIXTURES / "feed.xml")
        proc = self.run_config([
            {"stage": "fetch", "url": url},
            {"stage": "match", "field": "description", "pattern": "cat"},
            {"stage": "dedupe", "field": "link"},
            {"stage": "sort", "field": "date", "order": "desc"},
            {"stage": "limit", "count": 2},
            {"stage": "format", "type": "rss", "title": "Curated"},
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        channel = ET.fromstring(proc.stdout).find("channel")
        self.assertEqual([i.findtext("title") for i in channel.findall("item")],
                         ["Alpha Delta", "Alpha Beta"])

    def test_output_file_option(self):
        output = os.path.join(self.tmp.name, "out.json")
        proc = self.run_config([
            {"stage": "limit", "count": 1},
            {"stage": "format", "type": "json"},
        ], "--input", FIXTURES / "items.json", "--output", output)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(output, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)[0]["title"], "Zebra")

    def test_malformed_feed_is_handled_gracefully(self):
        url = "file://" + str(FIXTURES / "broken.xml")
        proc = self.run_config([
            {"stage": "fetch", "url": url},
            {"stage": "format", "type": "json"},
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("warning", proc.stderr.lower())
        self.assertEqual(json.loads(proc.stdout), [])

    def test_run_rejects_invalid_config(self):
        proc = run("run", self.config([{"stage": "nope"}]))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown stage", proc.stderr.lower())


if __name__ == "__main__":
    unittest.main()
