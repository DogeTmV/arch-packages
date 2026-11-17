"""CLI-level tests for cardstack (offline, temporary state directory)."""

import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "cardstack")


class CardstackCLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = os.path.join(self.tmp.name, "stacks")

    def run_cli(self, *args, check=True):
        proc = subprocess.run(
            [EXE] + [str(a) for a in args],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if check and proc.returncode != 0:
            self.fail(
                "cardstack %s failed (%d): %s"
                % (" ".join(str(a) for a in args), proc.returncode, proc.stderr)
            )
        return proc

    def make_demo_stack(self):
        self.run_cli("new", "demo", "--title", "Demo", "--dir", self.dir)
        self.run_cli(
            "add", "demo", "--title", "Alpha", "--text", "Hello [[Beta]]",
            "--dir", self.dir,
        )
        self.run_cli(
            "add", "demo", "--title", "Beta", "--text", "Second card about turtles.",
            "--dir", self.dir,
        )

    def test_card_ids_are_numeric_stable_and_not_reused_after_removal(self):
        self.run_cli("new", "demo", "--title", "Demo", "--dir", self.dir)
        first = self.run_cli(
            "add", "demo", "--title", "Alpha", "--text", "text", "--dir", self.dir
        ).stdout
        second = self.run_cli(
            "add", "demo", "--title", "Beta", "--text", "text", "--dir", self.dir
        ).stdout
        self.assertIn("1", first)
        self.assertIn("2", second)
        self.run_cli("rm", "demo", "1", "--dir", self.dir)
        listing = self.run_cli("list", "demo", "--dir", self.dir).stdout
        self.assertIn("2", listing)
        self.assertNotIn("Alpha", listing)
        third = self.run_cli(
            "add", "demo", "--title", "Gamma", "--text", "text", "--dir", self.dir
        ).stdout
        self.assertIn("3", third)

    def test_show_edit_and_list_roundtrip(self):
        self.make_demo_stack()
        shown = self.run_cli("show", "demo", "1", "--dir", self.dir).stdout
        self.assertIn("Alpha", shown)
        self.assertIn("Hello [[Beta]]", shown)
        self.run_cli(
            "edit", "demo", "1", "--title", "Renamed", "--text", "New body",
            "--dir", self.dir,
        )
        listing = self.run_cli("list", "demo", "--dir", self.dir).stdout
        self.assertIn("Renamed", listing)
        self.assertNotIn("Alpha", listing)
        self.assertIn("New body", self.run_cli("show", "demo", "1", "--dir", self.dir).stdout)

    def test_card_reference_by_title_and_labelled_links(self):
        self.make_demo_stack()
        self.run_cli("link", "demo", "1", "Beta", "--label", "goes to", "--dir", self.dir)
        links = self.run_cli("links", "demo", "1", "--dir", self.dir).stdout
        self.assertIn("2", links)
        self.assertIn("goes to", links)
        self.assertIn("Beta", links)

    def test_find_is_case_insensitive_and_can_be_scoped_to_a_stack(self):
        self.make_demo_stack()
        self.run_cli("new", "other", "--title", "Other", "--dir", self.dir)
        self.run_cli(
            "add", "other", "--title", "Extra", "--text", "TURTLES everywhere",
            "--dir", self.dir,
        )
        found = self.run_cli("find", "turtle", "--dir", self.dir).stdout
        self.assertIn("demo", found)
        self.assertIn("other", found)
        scoped = self.run_cli("find", "turtle", "--stack", "demo", "--dir", self.dir).stdout
        self.assertIn("demo", scoped)
        self.assertNotIn("other", scoped)

    def test_export_resolves_wiki_links_in_html_and_markdown(self):
        self.make_demo_stack()
        out = os.path.join(self.tmp.name, "export")
        self.run_cli("export", "demo", out, "--format", "html", "--dir", self.dir)
        with open(os.path.join(out, "card-1.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('<a href="card-2.html">Beta</a>', html)
        self.assertTrue(os.path.isfile(os.path.join(out, "card-2.html")))
        self.assertTrue(os.path.isfile(os.path.join(out, "index.html")))

        mdout = os.path.join(self.tmp.name, "md")
        self.run_cli("export", "demo", mdout, "--format", "markdown", "--dir", self.dir)
        with open(os.path.join(mdout, "card-1.md"), encoding="utf-8") as fh:
            markdown = fh.read()
        self.assertIn("[Beta](card-2.md)", markdown)
        self.assertTrue(os.path.isfile(os.path.join(mdout, "index.md")))

    def test_stacks_lists_created_stacks(self):
        self.make_demo_stack()
        self.run_cli("new", "other", "--dir", self.dir)
        output = self.run_cli("stacks", "--dir", self.dir).stdout
        self.assertIn("demo", output)
        self.assertIn("other", output)

    def test_unknown_card_reports_error_and_exits_nonzero(self):
        self.make_demo_stack()
        proc = self.run_cli("show", "demo", "99", "--dir", self.dir, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_help_and_version_work_without_a_tty(self):
        help_proc = self.run_cli("--help")
        self.assertEqual(help_proc.returncode, 0)
        self.assertIn("usage", help_proc.stdout.lower())
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)

    def test_state_is_json_under_the_selected_directory(self):
        self.make_demo_stack()
        path = os.path.join(self.dir, "demo.json")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as fh:
            data = __import__("json").load(fh)
        self.assertEqual(data["name"], "demo")
        self.assertEqual(len(data["cards"]), 2)
        self.assertEqual([c["id"] for c in data["cards"]], [1, 2])


if __name__ == "__main__":
    unittest.main()
