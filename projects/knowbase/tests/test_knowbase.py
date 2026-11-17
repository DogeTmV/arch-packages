"""Offline tests for the knowbase encyclopedia tool."""

import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "knowbase"


def run(*args, stdin=None):
    return subprocess.run([str(SCRIPT), *args], input=stdin, capture_output=True, text=True)


class KnowbaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "kb"
        self.assertEqual(run("init", str(self.dir)).returncode, 0)

    def add(self, title, body="Some text.", tags="", see=()):
        args = ["add", str(self.dir), title, "--body", "-"]
        if tags:
            args += ["--tags", tags]
        for target in see:
            args += ["--see", target]
        result = run(*args, stdin=body)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_add_then_show_round_trip(self):
        self.add("Day and Night", "Earth turns once a day.", "astronomy,earth", ("Tides",))
        shown = run("show", str(self.dir), "Day and Night")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Earth turns once a day.", shown.stdout)
        self.assertIn("astronomy", shown.stdout)
        self.assertIn("Tides", shown.stdout)

    def test_list_filters_by_tag_and_all_titles_are_sorted(self):
        self.add("Zinc", tags="element,metal")
        self.add("Amber", tags="mineral")
        self.assertEqual(run("list", str(self.dir)).stdout.splitlines(), ["Amber", "Zinc"])
        self.assertEqual(run("list", str(self.dir), "--tag", "metal").stdout.splitlines(), ["Zinc"])
        self.assertEqual(run("list", str(self.dir), "--tag", "missing").stdout.strip(), "")

    def test_rm_removes_only_named_article(self):
        self.add("One")
        self.add("Two")
        removed = run("rm", str(self.dir), "One")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertEqual(run("list", str(self.dir)).stdout.splitlines(), ["Two"])
        self.assertNotEqual(run("show", str(self.dir), "One").returncode, 0)

    def test_search_matches_body_and_tags_case_insensitively(self):
        self.add("The Ocean", "Salt water covers much of the planet.", "water,earth")
        self.add("Deserts", "Dry places receive little rain.", "climate")
        self.assertEqual(run("search", str(self.dir), "SALT WATER").stdout.splitlines(), ["The Ocean"])
        self.assertEqual(run("search", str(self.dir), "climate").stdout.splitlines(), ["Deserts"])

    def test_random_prints_one_of_the_stored_titles(self):
        self.add("Alpha")
        self.add("Beta")
        result = run("random", str(self.dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        title = result.stdout.splitlines()[0].removeprefix("Title: ")
        self.assertIn(title, ("Alpha", "Beta"))

    def test_export_writes_html_with_escaped_body(self):
        self.add("Markup", "<b>bold</b> & more", "test")
        outdir = self.dir.parent / "html-out"
        result = run("export", str(self.dir), str(outdir), "--format", "html")
        self.assertEqual(result.returncode, 0, result.stderr)
        exported = outdir / "markup.html"
        self.assertTrue(exported.is_file())
        content = exported.read_text(encoding="utf-8")
        self.assertIn("<h1>Markup</h1>", content)
        self.assertIn("&lt;b&gt;bold&lt;/b&gt; &amp; more", content)
        self.assertNotIn("<b>bold</b>", content)

    def test_export_markdown_uses_heading(self):
        self.add("Notes", "Plain words")
        outdir = self.dir.parent / "md-out"
        result = run("export", str(self.dir), str(outdir), "--format", "markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (outdir / "notes.md").read_text(encoding="utf-8")
        self.assertIn("# Notes", content)
        self.assertIn("Plain words", content)

    def test_stats_counts_articles_and_unique_tags(self):
        self.add("One", tags="alpha,beta")
        self.add("Two", tags="beta,gamma")
        result = run("stats", str(self.dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("articles: 2", result.stdout)
        self.assertIn("tags: 3", result.stdout)

    def test_init_sample_installs_between_six_and_ten_original_articles(self):
        second = self.dir.parent / "sample-kb"
        result = run("init", str(second), "--sample")
        self.assertEqual(result.returncode, 0, result.stderr)
        titles = run("list", str(second)).stdout.splitlines()
        self.assertGreaterEqual(len(titles), 6)
        self.assertLessEqual(len(titles), 10)

    def test_duplicate_add_and_missing_article_fail(self):
        self.add("Unique")
        self.assertNotEqual(run("add", str(self.dir), "Unique", "--body", "-", stdin="x").returncode, 0)
        self.assertNotEqual(run("show", str(self.dir), "Ghost").returncode, 0)

    def test_uninitialized_directory_reports_error(self):
        result = run("list", str(self.dir.parent / "nowhere"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not an initialized knowbase", result.stderr)

    def test_help_and_version_exit_zero(self):
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run("export", "--help").returncode, 0)
        version = run("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)


if __name__ == "__main__":
    unittest.main()
