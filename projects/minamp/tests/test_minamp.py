"""Offline unittest suite for the minamp playlist front-end."""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "minamp"


def run(*args):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), capture_output=True, text=True, timeout=30,
    )


def load_module():
    loader = importlib.machinery.SourceFileLoader("minamp_impl", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MinampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.music = self.root / "music"
        self.music.mkdir()
        self.db = str(self.root / "state.json")

    def track(self, name, data=b"fake audio"):
        path = self.music / name
        path.write_bytes(data)
        return str(path)

    def invoke(self, *args):
        return run("--db", self.db, *args)

    def state(self, db=None):
        with open(db or self.db, encoding="utf-8") as handle:
            return json.load(handle)

    def add_tracks(self, count=3):
        return [self.track("song%d.mp3" % i, b"audio%d" % i) for i in range(1, count + 1)]

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            proc = run(flag)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("minamp", run("--version").stdout)

    def test_add_recognizes_audio_extensions_and_ignores_other_files(self):
        audio = [self.track("a.mp3"), self.track("b.flac"),
                 self.track("c.ogg"), self.track("d.wav")]
        self.track("notes.txt")
        proc = self.invoke("add", *audio)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Added 4", proc.stdout)
        listing = self.invoke("list").stdout
        for path in audio:
            self.assertIn(path, listing)
        self.assertNotIn("notes.txt", listing)

    def test_add_directory_with_and_without_recursive(self):
        self.track("top.mp3")
        nested = self.music / "nested"
        nested.mkdir()
        inside = nested / "deep.ogg"
        inside.write_bytes(b"deep")
        flat = self.invoke("add", str(self.music))
        self.assertIn("Added 1", flat.stdout)
        recursive = self.invoke("add", str(self.music), "--recursive")
        self.assertIn("Added 1", recursive.stdout)
        self.assertIn("deep.ogg", self.invoke("list").stdout)

    def test_add_deduplicates_paths_and_preserves_ids(self):
        path = self.track("same.mp3")
        self.invoke("add", path, path)
        self.assertEqual(len(self.state()["tracks"]), 1)
        second = self.track("next.mp3")
        self.invoke("add", second)
        self.assertEqual([t["id"] for t in self.state()["tracks"]], [1, 2])

    def test_list_rm_and_clear(self):
        paths = self.add_tracks()
        self.invoke("add", *paths)
        listing = self.invoke("list").stdout
        self.assertIn("1  song1  ", listing)
        removed = self.invoke("rm", "2")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn("song2.mp3", self.invoke("list").stdout)
        self.invoke("clear")
        self.assertIn("Playlist is empty", self.invoke("list").stdout)

    def test_rm_unknown_id_is_an_error(self):
        proc = self.invoke("rm", "99")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_repeat_validates_mode(self):
        proc = self.invoke("repeat", "all")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.state()["repeat"], "all")
        bad = self.invoke("repeat", "sometimes")
        self.assertNotEqual(bad.returncode, 0)

    def test_shuffle_toggles(self):
        on = self.invoke("shuffle")
        self.assertEqual(on.returncode, 0, on.stderr)
        self.assertTrue(self.state()["shuffle"])
        self.assertIn("Shuffle: on", on.stdout)
        off = self.invoke("shuffle")
        self.assertFalse(self.state()["shuffle"])
        self.assertIn("Shuffle: off", off.stdout)

    def test_config_sets_and_reports_player(self):
        proc = self.invoke("config", "--player", "mpv --no-config")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["player"], "mpv --no-config")
        self.assertEqual(self.state()["player"], "mpv --no-config")

    def test_play_dry_run_never_launches_a_player(self):
        paths = self.add_tracks()
        self.invoke("add", *paths)
        proc = self.invoke("play", "1", "--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.startswith("DRY-RUN:"))
        self.assertIn("mpv", proc.stdout)
        for path in paths:
            self.assertIn(path, proc.stdout)
        self.assertEqual(self.state()["current"], 1)

    def test_repeat_off_plays_from_chosen_track_to_end(self):
        paths = self.add_tracks()
        self.invoke("add", *paths)
        proc = self.invoke("play", "2", "--dry-run")
        self.assertIn(paths[1], proc.stdout)
        self.assertIn(paths[2], proc.stdout)
        self.assertNotIn(paths[0], proc.stdout)

    def test_repeat_all_wraps_around_the_playlist(self):
        paths = self.add_tracks()
        self.invoke("add", *paths)
        self.invoke("repeat", "all")
        proc = self.invoke("play", "2", "--dry-run")
        self.assertLess(proc.stdout.index(paths[1]), proc.stdout.index(paths[2]))
        self.assertLess(proc.stdout.index(paths[2]), proc.stdout.index(paths[0]))

    def test_repeat_one_plays_a_single_track(self):
        paths = self.add_tracks()
        self.invoke("add", *paths)
        self.invoke("repeat", "one")
        proc = self.invoke("play", "2", "--dry-run")
        self.assertIn(paths[1], proc.stdout)
        self.assertNotIn(paths[0], proc.stdout)
        self.assertNotIn(paths[2], proc.stdout)

    def test_player_template_substitutes_file_placeholder(self):
        path = self.track("solo.mp3")
        self.invoke("add", path)
        self.invoke("repeat", "one")
        proc = self.invoke("play", "1", "--dry-run", "--player", "ffplay -nodisp {file}")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ffplay -nodisp", proc.stdout)
        self.assertIn(path, proc.stdout)

    def test_now_reports_current_track(self):
        paths = self.add_tracks(1)
        self.invoke("add", paths[0])
        self.assertIn("Nothing playing", self.invoke("now").stdout)
        self.invoke("play", "1", "--dry-run")
        self.assertIn("song1.mp3", self.invoke("now").stdout)

    def test_m3u_export_import_round_trip(self):
        paths = self.add_tracks(2)
        self.invoke("add", *paths)
        playlist = str(self.root / "list.m3u")
        exported = self.invoke("export", playlist)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        text = Path(playlist).read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#EXTM3U"))
        self.assertIn("#EXTINF:", text)
        other_db = str(self.root / "other.json")
        imported = run("--db", other_db, "import", playlist)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        before = [(t["path"], t["title"], t["duration"]) for t in
                  self.state()["tracks"]]
        after = [(t["path"], t["title"], t["duration"]) for t in
                 self.state(other_db)["tracks"]]
        self.assertEqual(before, after)

    def test_build_queue_respects_shuffle_and_repeat(self):
        module = load_module()
        state = {"tracks": [{"id": i} for i in range(1, 5)],
                 "shuffle": False, "repeat": "off"}
        self.assertEqual(module.build_queue(state, 3), [3, 4])
        state["repeat"] = "all"
        self.assertEqual(module.build_queue(state, 3), [3, 4, 1, 2])
        state["shuffle"] = True
        queue = module.build_queue(state, 1, seed=0)
        self.assertEqual(sorted(queue), [1, 2, 3, 4])
        self.assertNotEqual(queue, [1, 2, 3, 4])

    def test_play_empty_playlist_is_an_error(self):
        proc = self.invoke("play", "--dry-run")
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())


if __name__ == "__main__":
    unittest.main()
