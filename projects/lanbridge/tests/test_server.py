import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core
import server


def req(method, url, token=None, data=None, headers=None, ctype=None):
    hdrs = dict(headers or {})
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        if isinstance(data, (bytes, bytearray)):
            body = bytes(data)
        else:
            body = json.dumps(data).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
    if ctype:
        hdrs["Content-Type"] = ctype
    r = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                return resp.status, json.loads(raw.decode("utf-8"))
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8"))
        except Exception:
            return e.code, raw


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = core.default_config()
        self.cfg.update({
            "listen_host": "127.0.0.1",
            "port": 0,
            "token": "test-token",
            "device_name": "pc-test",
            "download_dir": os.path.join(self.tmp.name, "downloads"),
            "allow_pc_command_exec": False,
        })
        self.state = server.BridgeState(self.cfg)
        self.httpd = server.BridgeHTTPServer(("127.0.0.1", 0), self.state)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.t = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.t.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.t.join(timeout=2)
        self.tmp.cleanup()

    def test_ping_requires_auth(self):
        code, _ = req("GET", self.base + "/api/ping")
        self.assertEqual(code, 401)
        code, data = req("GET", self.base + "/api/ping", token="wrong")
        self.assertEqual(code, 401)
        code, data = req("GET", self.base + "/api/ping", token="test-token")
        self.assertEqual(code, 200)
        self.assertTrue(data["ok"])

    def test_pair_and_clipboard(self):
        code, data = req("POST", self.base + "/api/pair", data={"token": "test-token", "device": {"name": "Pixel"}})
        self.assertEqual(code, 200)
        self.assertTrue(data["ok"])
        self.assertIsNotNone(self.state.phone)
        code, _ = req("POST", self.base + "/api/clipboard", token="test-token", data={"text": "hello", "source": "phone"})
        self.assertEqual(code, 200)
        code, data = req("GET", self.base + "/api/clipboard", token="test-token")
        self.assertEqual(code, 200)
        self.assertEqual(data["text"], "hello")

    def test_commands_save_and_files(self):
        cmds = [{"id": "1", "name": "Hi", "action": "notify", "payload": {}, "target": "phone"}]
        code, data = req("POST", self.base + "/api/commands", token="test-token", data={"commands": cmds})
        self.assertEqual(code, 200)
        self.assertEqual(len(data["commands"]), 1)
        code, data = req("GET", self.base + "/api/commands", token="test-token")
        self.assertEqual(code, 200)
        self.assertEqual(data["commands"][0]["name"], "Hi")

        # upload file
        code, data = req("POST", self.base + "/api/files", token="test-token", data=b"hello file", headers={"X-Filename": "note.txt"}, ctype="application/octet-stream")
        self.assertEqual(code, 200)
        self.assertTrue(data["ok"])
        code, data = req("GET", self.base + "/api/files", token="test-token")
        self.assertEqual(code, 200)
        self.assertTrue(any(f["name"].startswith("note") for f in data["files"]))
        name = data["files"][0]["name"]
        code, blob = req("GET", self.base + f"/api/files/{name}", token="test-token")
        self.assertEqual(code, 200)
        self.assertEqual(blob, b"hello file")

    def test_phone_event_stores_state(self):
        code, _ = req("POST", self.base + "/api/events", token="test-token", data={"type": "notification", "payload": {"title": "Msg"}})
        self.assertEqual(code, 200)
        self.assertEqual(len(self.state.messages), 1)
        code, _ = req("POST", self.base + "/api/events", token="test-token", data={"type": "call", "payload": {"state": "ringing"}})
        self.assertEqual(code, 200)
        self.assertEqual(len(self.state.calls), 1)

    def test_pc_command_exec_disabled(self):
        code, data = req("POST", self.base + "/api/commands/run", token="test-token", data={"target": "pc", "command": {"action": "shell", "payload": {"argv": ["echo", "hi"]}}})
        self.assertEqual(code, 403)
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main()
