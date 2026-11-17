"""Offline unittest suite for the photoatlas indexer and gallery generator."""

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "photoatlas"


def run(*args):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )


def tiny_jpeg(width, height):
    """Return bytes containing a minimal JPEG SOF0 marker with dimensions."""
    segment = struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8\xff\xe0\x00\x04JFIF\xff\xc0" + segment + b"\xff\xd9"


class PhotoAtlasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.photos = self.root / "photos"
        self.photos.mkdir()
        self.db = str(self.root / "index.json")

    def write(self, name, data):
        path = self.photos / name
        path.write_bytes(data)
        return str(path)

    def invoke(self, *args):
        return run("--db", self.db, *args)

    def state(self):
        with open(self.db, encoding="utf-8") as handle:
            return json.load(handle)

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            proc = run(flag)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("photoatlas", run("--version").stdout)

    def test_index_discovers_files_and_stores_metadata(self):
        first = self.write("one.jpg", tiny_jpeg(30, 20))
        second = self.write("two.txt", b"plain text")
        proc = self.invoke("index", str(self.photos))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Indexed 2 photos", proc.stdout)
        entries = {e["path"]: e for e in self.state()["photos"]}
        self.assertEqual(set(entries), {first, second})
        entry = entries[first]
        self.assertEqual(entry["size"], os.path.getsize(first))
        self.assertEqual(entry["sha256"], hashlib.sha256(tiny_jpeg(30, 20)).hexdigest())
        self.assertIn("mtime", entry)
        self.assertIn("tags", entry)

    def test_jpeg_dimensions_are_parsed_from_sof_marker(self):
        self.write("sized.jpg", tiny_jpeg(640, 480))
        self.invoke("index", str(self.photos))
        entry = self.state()["photos"][0]
        self.assertEqual((entry["width"], entry["height"]), (640, 480))

    def test_identical_files_are_reported_as_duplicates(self):
        one = self.write("copy1.bin", b"identical bytes")
        two = self.write("copy2.bin", b"identical bytes")
        unique = self.write("unique.bin", b"something else")
        self.invoke("index", str(self.photos))
        proc = self.invoke("duplicates")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(one, proc.stdout)
        self.assertIn(two, proc.stdout)
        self.assertNotIn(unique, proc.stdout)

    def test_two_phase_hash_does_not_call_same_prefix_files_duplicates(self):
        prefix = b"A" * 65536
        first = self.write("prefix1.bin", prefix + b"tail-one")
        second = self.write("prefix2.bin", prefix + b"tail-two")
        self.invoke("index", str(self.photos))
        entries = {e["path"]: e for e in self.state()["photos"]}
        self.assertEqual(entries[first]["partial_sha256"],
                         entries[second]["partial_sha256"])
        self.assertNotEqual(entries[first]["sha256"], entries[second]["sha256"])
        proc = self.invoke("duplicates")
        self.assertIn("No duplicates", proc.stdout)

    def test_tag_and_find(self):
        path = self.write("holiday.jpg", tiny_jpeg(10, 10))
        self.invoke("index", str(self.photos))
        tagged = self.invoke("tag", path, "holiday")
        self.assertEqual(tagged.returncode, 0, tagged.stderr)
        found = self.invoke("find", "holiday")
        self.assertIn(path, found.stdout)
        self.assertIn("No matches", self.invoke("find", "missing").stdout)

    def test_tag_rejects_unindexed_path(self):
        proc = self.invoke("tag", str(self.photos / "absent.jpg"), "x")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_list_shows_paths_and_tags(self):
        path = self.write("indexed.jpg", tiny_jpeg(5, 5))
        self.invoke("index", str(self.photos))
        self.invoke("tag", path, "favorite")
        listing = self.invoke("list")
        self.assertIn(path, listing.stdout)
        self.assertIn("favorite", listing.stdout)
        self.assertIn("5x5", listing.stdout)

    def test_stats_counts_photos_bytes_and_duplicate_groups(self):
        self.write("a.bin", b"abc")
        self.write("b.bin", b"abc")
        self.invoke("index", str(self.photos))
        proc = self.invoke("stats")
        for line in ("Photos: 2", "Total bytes: 6", "Duplicate groups: 1"):
            self.assertIn(line, proc.stdout)

    def test_gallery_writes_relative_links_and_inline_css(self):
        path = self.write("photo.jpg", tiny_jpeg(12, 9))
        self.invoke("index", str(self.photos))
        before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        before_mtime = os.path.getmtime(path)
        out = self.root / "gallery"
        proc = self.invoke("gallery", str(out), "--title", "My Album")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        html = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("My Album", html)
        self.assertIn("<style>", html)
        self.assertIn("../photos/photo.jpg", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), before)
        self.assertEqual(os.path.getmtime(path), before_mtime)

    def test_reindex_updates_changed_files_and_prunes_deleted(self):
        keep = self.write("keep.bin", b"old")
        gone = self.write("gone.bin", b"delete me")
        self.invoke("index", str(self.photos))
        Path(keep).write_bytes(b"new and longer")
        Path(gone).unlink()
        proc = self.invoke("index", str(self.photos))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        paths = [e["path"] for e in self.state()["photos"]]
        self.assertEqual(paths, [keep])
        self.assertEqual(self.state()["photos"][0]["size"], len(b"new and longer"))

    def test_index_rejects_missing_directory(self):
        proc = self.invoke("index", str(self.root / "nope"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())


if __name__ == "__main__":
    unittest.main()
