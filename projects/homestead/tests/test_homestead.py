"""Tests for the homestead homepage generator (temporary directories only)."""

import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "homestead")

PAGE_SOURCE = """# Hello World

Welcome to my little corner of the web.

- First item
- Second item

Visit [the guestbook](guestbook.html) and see ![cat](cat.png).
"""


class HomesteadCLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = os.path.join(self.tmp.name, "site-source")

    def run_cli(self, *args, check=True):
        proc = subprocess.run(
            [EXE] + [str(a) for a in args],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if check and proc.returncode != 0:
            self.fail(
                "homestead %s failed (%d): %s"
                % (" ".join(str(a) for a in args), proc.returncode, proc.stderr)
            )
        return proc

    def make_site(self):
        page = os.path.join(self.tmp.name, "page.md")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(PAGE_SOURCE)
        self.run_cli("init", self.site, "--title", "My Place", "--author", "Ada")
        self.run_cli(
            "add", self.site, "Hello", "--file", page,
            "--slug", "hello", "--date", "2020-01-02",
        )

    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as fh:
            return fh.read()

    def test_build_creates_index_page_css_and_guestbook(self):
        self.make_site()
        out = os.path.join(self.tmp.name, "out")
        self.run_cli("build", self.site, "--out", out)
        for name in ("index.html", "hello.html", "styles.css", "guestbook.html"):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)

        page = self.read(out, "hello.html")
        self.assertIn("<h1>Hello World</h1>", page)
        self.assertIn("<ul>\n<li>First item</li>\n<li>Second item</li>\n</ul>", page)
        self.assertIn('<a href="guestbook.html">the guestbook</a>', page)
        self.assertIn('<img src="cat.png" alt="cat">', page)
        index = self.read(out, "index.html")
        self.assertIn('<a href="hello.html">Hello</a>', index)
        self.assertIn("2020-01-02", index)
        guestbook = self.read(out, "guestbook.html")
        self.assertIn("<form", guestbook)
        self.assertIn("styles.css", guestbook)

    def test_list_and_page_show_metadata_and_source(self):
        self.make_site()
        listing = self.run_cli("list", self.site).stdout
        self.assertIn("hello", listing)
        self.assertIn("Hello", listing)
        self.assertIn("2020-01-02", listing)
        page = self.run_cli("page", self.site, "hello").stdout
        self.assertIn("# Hello World", page)
        self.assertIn("- First item", page)

    def test_theme_changes_css_only(self):
        self.make_site()
        classic = os.path.join(self.tmp.name, "classic")
        brick = os.path.join(self.tmp.name, "brick")
        self.run_cli("build", self.site, "--out", classic)
        self.run_cli("theme", self.site, "brick")
        self.run_cli("build", self.site, "--out", brick)
        for name in ("index.html", "hello.html", "guestbook.html"):
            self.assertEqual(
                self.read(classic, name), self.read(brick, name),
                "theme changed %s" % name,
            )
        self.assertNotEqual(
            self.read(classic, "styles.css"), self.read(brick, "styles.css")
        )
        self.assertTrue(self.read(brick, "styles.css").strip())

    def test_invalid_theme_is_rejected(self):
        self.make_site()
        proc = self.run_cli("theme", self.site, "neon", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_markdown_special_characters_are_escaped(self):
        self.make_site()
        page = os.path.join(self.tmp.name, "unsafe.md")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write("# <script>alert(1)</script>\n\nA & B.\n")
        self.run_cli("add", self.site, "Unsafe", "--file", page, "--slug", "unsafe")
        out = os.path.join(self.tmp.name, "out2")
        self.run_cli("build", self.site, "--out", out)
        html = self.read(out, "unsafe.html")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A &amp; B.", html)

    def test_help_and_version_work_without_a_tty(self):
        help_proc = self.run_cli("--help")
        self.assertEqual(help_proc.returncode, 0)
        self.assertIn("usage", help_proc.stdout.lower())
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)


if __name__ == "__main__":
    unittest.main()
