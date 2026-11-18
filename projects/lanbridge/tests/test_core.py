import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core


class CoreTests(unittest.TestCase):
    def test_generate_and_check_token(self):
        t = core.generate_token()
        self.assertGreaterEqual(len(t), 16)
        self.assertTrue(core.check_token(t, t))
        self.assertFalse(core.check_token(t, "wrong"))
        self.assertFalse(core.check_token("", t))
        self.assertFalse(core.check_token(None, t))

    def test_safe_filename_and_unique_path(self):
        self.assertEqual(core.safe_filename("../evil.txt"), "evil.txt")
        self.assertEqual(core.safe_filename("..\\..\\a b.png"), "a b.png")
        self.assertEqual(core.safe_filename(""), "file")
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            p1 = core.unique_path(d, "photo.jpg")
            p1.write_text("x")
            p2 = core.unique_path(d, "photo.jpg")
            self.assertNotEqual(p1, p2)
            self.assertTrue(str(p2.name).startswith("photo"))

    def test_json_helpers(self):
        data = {"a": 1, "b": "x"}
        raw = core.json_dumps(data)
        self.assertEqual(core.json_loads_bytes(raw), data)

    def test_commands_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            old = core.COMMANDS_FILE
            try:
                core.COMMANDS_FILE = Path(td) / "commands.json"
                cmds = [{"id": "c1", "name": "Open", "action": "open_url", "payload": {"url": "https://example.com"}, "target": "phone"}]
                core.save_commands(cmds)
                loaded = core.load_commands()
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["name"], "Open")
                self.assertEqual(loaded[0]["payload"]["url"], "https://example.com")
            finally:
                core.COMMANDS_FILE = old

    def test_event_and_auth_header(self):
        e = core.Event("ping", {"x": 1}, source="pc")
        d = e.to_dict()
        self.assertEqual(d["type"], "ping")
        self.assertEqual(d["source"], "pc")
        self.assertIn("id", d)

        class H(dict):
            def get(self, k, d=None):
                return super().get(k, d)
        self.assertEqual(core.auth_token_from_headers({"Authorization": "Bearer abc"}), "abc")
        self.assertEqual(core.auth_token_from_headers({"X-LanBridge-Token": "xyz"}), "xyz")


if __name__ == "__main__":
    unittest.main()
