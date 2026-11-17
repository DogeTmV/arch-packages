"""Behavioral tests for the notebox CLI."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "notebox"


class NoteboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "notes.json")

    def run_cli(self, *args):
        return subprocess.run(
            [str(SCRIPT), "--db", self.db, *map(str, args)],
            capture_output=True, text=True,
        )

    def add_note(self, *text, title=None, tags=None):
        args = ["add", *text]
        if title:
            args += ["--title", title]
        if tags:
            args += ["--tags", tags]
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.split()[-1]

    def test_added_note_has_title_body_tags_and_timestamps(self):
        note_id = self.add_note("first", "note", title="Hello", tags="work,ideas")
        shown = self.run_cli("show", note_id)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Hello", shown.stdout)
        self.assertIn("first note", shown.stdout)
        self.assertIn("work", shown.stdout)
        self.assertIn("created:", shown.stdout)
        self.assertIn("updated:", shown.stdout)

    def test_edit_replaces_body_of_existing_note(self):
        note_id = self.add_note("old", "body", title="Draft")
        edited = self.run_cli("edit", note_id, "new", "body")
        self.assertEqual(edited.returncode, 0, edited.stderr)
        shown = self.run_cli("show", note_id)
        self.assertIn("new body", shown.stdout)
        self.assertNotIn("old body", shown.stdout)

    def test_rm_removes_the_note(self):
        note_id = self.add_note("temporary", title="Temp")
        removed = self.run_cli("rm", note_id)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn("temporary", self.run_cli("list").stdout)

    def test_list_tag_filter_and_limit(self):
        self.add_note("one", title="One", tags="alpha")
        self.add_note("two", title="Two", tags="beta")
        self.add_note("three", title="Three", tags="alpha")
        alpha = self.run_cli("list", "--tag", "alpha")
        self.assertIn("One", alpha.stdout)
        self.assertIn("Three", alpha.stdout)
        self.assertNotIn("Two", alpha.stdout)
        limited = self.run_cli("list", "--limit", "1")
        self.assertEqual(len([line for line in limited.stdout.splitlines() if line]), 1)

    def test_search_is_case_insensitive_over_title_and_body(self):
        self.add_note("secret", "payload", title="Hidden")
        found = self.run_cli("search", "SECRET")
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertIn("secret payload", found.stdout)

    def test_tag_adds_multiple_tags_to_one_note(self):
        note_id = self.add_note("tagged", title="Tagged")
        result = self.run_cli("tag", note_id, "red", "blue")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Tagged", self.run_cli("list", "--tag", "red").stdout)
        self.assertIn("Tagged", self.run_cli("list", "--tag", "blue").stdout)

    def test_export_writes_safe_deterministic_files_per_note(self):
        self.add_note("body text", title="Hello/World?")
        self.add_note("another body", title="Second")
        out_a = os.path.join(self.tmp.name, "a")
        out_b = os.path.join(self.tmp.name, "b")
        first = self.run_cli("export", out_a, "--format", "md")
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_cli("export", out_b, "--format", "md")
        self.assertEqual(second.returncode, 0, second.stderr)
        names = sorted(os.listdir(out_a))
        self.assertEqual(len(names), 3)
        self.assertEqual(names, sorted(os.listdir(out_b)))
        for name in names:
            self.assertNotIn("/", name)
            self.assertNotIn("?", name)
            self.assertEqual(Path(out_a, name).read_text(), Path(out_b, name).read_text())

    def test_html_export_is_self_contained(self):
        self.add_note("html body", title="Page")
        out = os.path.join(self.tmp.name, "html")
        result = self.run_cli("export", out, "--format", "html")
        self.assertEqual(result.returncode, 0, result.stderr)
        combined = "".join(p.read_text() for p in Path(out).glob("*.html"))
        self.assertIn("html body", combined)
        self.assertNotIn("<link", combined)
        self.assertNotIn("<script", combined)
        self.assertNotIn("src=", combined)

    def test_import_single_markdown_file_uses_heading_and_tags(self):
        source = Path(self.tmp.name, "in.md")
        source.write_text("# Imported Title\n\nTags: one, two\n\nImported body line.\n")
        result = self.run_cli("import", str(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Imported Title", self.run_cli("list").stdout)
        self.assertIn("Imported Title", self.run_cli("list", "--tag", "one").stdout)

    def test_import_directory_reads_all_text_files(self):
        folder = Path(self.tmp.name, "notes-dir")
        folder.mkdir()
        (folder / "a.txt").write_text("plain text note")
        (folder / "b.md").write_text("# Markdown note\n\nmarkdown body")
        (folder / "skip.bin").write_bytes(b"\x00\x01")
        result = self.run_cli("import", str(folder))
        self.assertEqual(result.returncode, 0, result.stderr)
        listing = self.run_cli("list").stdout
        self.assertIn("plain text note", listing)
        self.assertIn("Markdown note", listing)
        self.assertNotIn("skip.bin", listing)

    def test_stats_counts_notes_and_tags(self):
        self.add_note("a", title="A", tags="x")
        self.add_note("b", title="B", tags="y")
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notes: 2", result.stdout)
        self.assertIn("tags: 2", result.stdout)

    def test_show_unknown_id_exits_nonzero_with_stderr_message(self):
        result = self.run_cli("show", "n-9999")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())

    def test_db_option_also_works_after_subcommand(self):
        other_db = os.path.join(self.tmp.name, "after.json")
        result = subprocess.run(
            [str(SCRIPT), "add", "hello", "--db", other_db],
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
