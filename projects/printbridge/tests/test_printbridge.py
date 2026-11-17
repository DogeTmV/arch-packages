"""Offline unittest suite for the printbridge command line tool."""

import http.client
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "printbridge"
TOKEN = "test-secret-token"
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def run(*args, env=None):
    return subprocess.run(
        [str(SCRIPT), *[str(a) for a in args]],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30,
    )


def load_module():
    loader = importlib.machinery.SourceFileLoader("printbridge_impl", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class PrintBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spool = os.path.join(self.tmp.name, "spool")
        self.config = os.path.join(self.tmp.name, "config.json")
        self.env = os.environ.copy()
        self.env["PRINTBRIDGE_CONFIG"] = self.config
        self.module = load_module()

    def start_server(self, token=TOKEN, printer="Lab", host=None):
        kwargs = {
            "port": 0, "token": token, "printer": printer,
            "spool": self.spool, "dry_run": True,
        }
        if host is not None:
            kwargs["host"] = host
        server = self.module.create_server(**kwargs)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.stop_server, server, thread)
        port = server.server_address[1]
        return server, "http://127.0.0.1:%d" % port

    @staticmethod
    def stop_server(server, thread):
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    def post(self, url, data=PDF, content_type="application/pdf",
             headers=None, token=TOKEN):
        base = {"Content-Type": content_type}
        if token is not None:
            base["X-Auth-Token"] = token
        request = urllib.request.Request(
            url + "/print", data=data, method="POST",
            headers={**base, **(headers or {})},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            exc.close()
            try:
                return exc.code, json.loads(body)
            except ValueError:
                return exc.code, body

    def jobs(self):
        return sorted((Path(self.spool) / "jobs").glob("*.json"))

    def test_help_and_version_exit_zero(self):
        for flag in ("--help", "--version"):
            proc = run(flag, env=self.env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.strip())
        self.assertIn("printbridge", run("--version", env=self.env).stdout)

    def test_invalid_command_exits_nonzero_with_stderr(self):
        proc = run("bogus", env=self.env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    def test_config_persists_token_and_printer(self):
        proc = run("config", "--token", "abc123", "--printer", "Office", env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(self.config, encoding="utf-8") as handle:
            saved = json.load(handle)
        self.assertEqual(saved["token"], "abc123")
        self.assertEqual(saved["printer"], "Office")
        shown = run("config", env=self.env)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Office", shown.stdout)

    def test_default_bind_host_is_loopback(self):
        server, _ = self.start_server()
        self.assertEqual(server.server_address[0], "127.0.0.1")

    def test_print_rejects_missing_and_wrong_tokens(self):
        _, url = self.start_server()
        for headers in ({}, {"X-Auth-Token": "wrong"},
                        {"Authorization": "Bearer wrong"}):
            status, body = self.post(url, headers=headers, token=None)
            self.assertEqual(status, 401, body)

    def test_print_accepts_bearer_token(self):
        _, url = self.start_server()
        status, body = self.post(
            url, headers={"Authorization": "Bearer " + TOKEN}, token=None)
        self.assertEqual(status, 202, body)
        self.assertEqual(body["status"], "queued")
        self.assertEqual(len(self.jobs()), 1)

    def test_send_round_trip_records_command_without_printing(self):
        _, url = self.start_server(printer="Lab")
        source = os.path.join(self.tmp.name, "report.txt")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("hello print bridge\n")
        proc = run("send", source, "--url", url + "/print",
                   "--token", TOKEN, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        jobs = self.jobs()
        self.assertEqual(len(jobs), 1)
        job = json.loads(jobs[0].read_text(encoding="utf-8"))
        self.assertEqual(job["kind"], "text")
        self.assertEqual(job["printer"], "Lab")
        self.assertEqual(job["status"], "queued")
        self.assertTrue(job["dry_run"])
        self.assertEqual(job["command"][:2], ["lp", "-d"])
        payload = Path(self.spool) / "data" / (job["id"] + "-report.txt")
        self.assertEqual(payload.read_text(encoding="utf-8"),
                         "hello print bridge\n")

    def test_queue_status_and_cancel(self):
        _, url = self.start_server()
        status, body = self.post(url)
        self.assertEqual(status, 202, body)
        job_id = body["id"]
        queue = run("queue", "--spool", self.spool, env=self.env)
        self.assertEqual(queue.returncode, 0, queue.stderr)
        self.assertIn(job_id, queue.stdout)
        self.assertIn("queued", queue.stdout)
        info = run("status", "--spool", self.spool, env=self.env)
        self.assertEqual(info.returncode, 0, info.stderr)
        self.assertIn("queued: 1", info.stdout)
        cancelled = run("cancel", job_id, "--spool", self.spool, env=self.env)
        self.assertEqual(cancelled.returncode, 0, cancelled.stderr)
        self.assertIn("cancelled: 1",
                      run("status", "--spool", self.spool, env=self.env).stdout)
        self.assertNotEqual(
            run("cancel", job_id, "--spool", self.spool, env=self.env).returncode,
            0,
        )

    def test_accepts_png_and_plaintext(self):
        _, url = self.start_server()
        status, body = self.post(url, data=b"\x89PNG\r\n\x1a\nfake",
                                 content_type="image/png")
        self.assertEqual(status, 202, body)
        status, body = self.post(url, data=b"plain words\n",
                                 content_type="text/plain; charset=utf-8")
        self.assertEqual(status, 202, body)
        kinds = []
        for path in self.jobs():
            with path.open(encoding="utf-8") as handle:
                kinds.append(json.load(handle)["kind"])
        kinds.sort()
        self.assertEqual(kinds, ["png", "text"])

    def test_rejects_unsupported_and_mislabeled_content(self):
        _, url = self.start_server()
        status, _ = self.post(url, data=b"bytes",
                              content_type="application/octet-stream")
        self.assertEqual(status, 415)
        status, _ = self.post(url, data=b"not a pdf")
        self.assertEqual(status, 415)
        self.assertEqual(self.jobs(), [])

    def test_rejects_oversized_payload_before_reading(self):
        _, url = self.start_server()
        from urllib.parse import urlparse
        parsed = urlparse(url)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        conn.putrequest("POST", "/print")
        conn.putheader("Content-Type", "application/pdf")
        conn.putheader("X-Auth-Token", TOKEN)
        conn.putheader("Content-Length", str(5 * 1024 * 1024 + 1))
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        conn.close()
        self.assertEqual(self.jobs(), [])


if __name__ == "__main__":
    unittest.main()
