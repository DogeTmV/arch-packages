"""LanBridge PC-side HTTP server and command/media helpers.

The server is designed for trusted LAN use. All mutating endpoints require a
Bearer token. The Android client connects as an HTTP client (POST events,
SSE event stream for PC->phone messages, uploads/downloads).
"""

from __future__ import annotations

import json
import mimetypes
import os
import queue
import shutil
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import core


class BridgeState:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lock = threading.RLock()
        self.bus = core.EventBus()
        self.phone: Optional[Dict[str, Any]] = None
        self.phone_last_seen = 0.0
        self.clipboard_text = ""
        self.messages: list[Dict[str, Any]] = []
        self.calls: list[Dict[str, Any]] = []
        self.media: Dict[str, Any] = {}
        self.last_screen_jpeg: Optional[bytes] = None
        self.last_screen_ts = 0.0
        self.saved_commands = core.load_commands()

    def token(self) -> str:
        return str(self.config.get("token") or "")

    def publish(self, event: Dict[str, Any]) -> None:
        self.bus.publish(event)

    def set_phone(self, info: Dict[str, Any]) -> None:
        with self.lock:
            self.phone = info
            self.phone_last_seen = time.time()
        self.publish(core.Event("phone_status", {"connected": True, "info": info}, source="pc").to_dict())

    def touch_phone(self) -> None:
        with self.lock:
            self.phone_last_seen = time.time()

    def disconnect_phone(self) -> None:
        with self.lock:
            info = self.phone
            self.phone = None
        self.publish(core.Event("phone_status", {"connected": False, "info": info}, source="pc").to_dict())


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return b""
    return handler.rfile.read(length)


class BridgeHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr: Tuple[str, int], state: BridgeState):
        super().__init__(addr, BridgeHandler)
        self.state = state


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = f"LanBridge/{core.VERSION}"

    @property
    def state(self) -> BridgeState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter; UI shows logs
        return

    def _send(self, status: int, body: bytes = b"", content_type: str = "application/json; charset=utf-8", extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, status: int, data: Any) -> None:
        self._send(status, core.json_dumps(data))

    def _unauthorized(self) -> None:
        self._json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})

    def _bad_request(self, msg: str) -> None:
        self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": msg})

    def _authed(self) -> bool:
        token = core.auth_token_from_headers(self.headers)
        if not token:
            # allow token query for streams if needed
            qs = parse_qs(urlparse(self.path).query)
            token = (qs.get("token") or [None])[0]
        return core.check_token(token, self.state.token())

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/ping":
            return self._get_ping()
        if path == "/api/events":
            return self._get_events()
        if path == "/api/clipboard":
            return self._get_clipboard()
        if path == "/api/commands":
            return self._get_commands()
        if path == "/api/files":
            return self._get_files()
        if path.startswith("/api/files/"):
            return self._get_file_download(unquote(path[len("/api/files/"):]))
        if path == "/api/pc-files":
            return self._get_pc_files()
        if path.startswith("/api/pc-files/"):
            return self._get_pc_file_download(unquote(path[len("/api/pc-files/"):]))
        if path == "/api/screen/latest.jpg":
            return self._get_screen()
        if path == "/api/status":
            return self._get_status()
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/pair":
            return self._post_pair()
        if path == "/api/events":
            return self._post_phone_event()
        if path == "/api/clipboard":
            return self._post_clipboard()
        if path == "/api/commands":
            return self._post_commands()
        if path == "/api/commands/run":
            return self._post_commands_run()
        if path == "/api/files":
            return self._post_file_upload()
        if path == "/api/screen/push":
            return self._post_screen()
        if path == "/api/pc/media":
            return self._post_pc_media()
        if path == "/api/pc/media-status":
            return self._post_pc_media_status()
        if path == "/api/pc/command-result":
            return self._post_command_result()
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    # --- GET handlers ---

    def _get_ping(self) -> None:
        if not self._authed():
            return self._unauthorized()
        self._json(200, {
            "ok": True,
            "app": core.APP_NAME,
            "version": core.VERSION,
            "protocol": core.PROTOCOL,
            "device_name": self.state.config.get("device_name"),
            "platform": "linux",
        })

    def _get_status(self) -> None:
        if not self._authed():
            return self._unauthorized()
        with self.state.lock:
            data = {
                "ok": True,
                "phone": self.state.phone,
                "phone_last_seen": self.state.phone_last_seen,
                "media": self.state.media,
                "clipboard_len": len(self.state.clipboard_text or ""),
            }
        self._json(200, data)

    def _get_events(self) -> None:
        if not self._authed():
            return self._unauthorized()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q: queue.Queue = queue.Queue(maxsize=200)
        self.state.bus.subscribe(q)
        try:
            # hello
            self.wfile.write(b"event: hello\ndata: {\"ok\":true}\n\n")
            self.wfile.flush()
            last_ping = time.time()
            while True:
                try:
                    event = q.get(timeout=15)
                    payload = json.dumps(event, separators=(",", ":"))
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # keepalive
                    if time.time() - last_ping > 15:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        last_ping = time.time()
        except Exception:
            pass
        finally:
            self.state.bus.unsubscribe(q)

    def _get_clipboard(self) -> None:
        if not self._authed():
            return self._unauthorized()
        with self.state.lock:
            text = self.state.clipboard_text
        self._json(200, {"ok": True, "text": text})

    def _get_commands(self) -> None:
        if not self._authed():
            return self._unauthorized()
        with self.state.lock:
            cmds = list(self.state.saved_commands)
        self._json(200, {"ok": True, "commands": cmds})

    def _get_files(self) -> None:
        if not self._authed():
            return self._unauthorized()
        ddir = Path(self.state.config.get("download_dir") or core.DOWNLOAD_DIR)
        ddir.mkdir(parents=True, exist_ok=True)
        files = []
        for p in sorted(ddir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:200]:
            if p.is_file():
                st = p.stat()
                files.append({"name": p.name, "size": st.st_size, "mtime": int(st.st_mtime)})
        self._json(200, {"ok": True, "files": files, "download_dir": str(ddir)})

    def _get_file_download(self, name: str) -> None:
        if not self._authed():
            return self._unauthorized()
        safe = core.safe_filename(name)
        ddir = Path(self.state.config.get("download_dir") or core.DOWNLOAD_DIR)
        path = (ddir / safe).resolve()
        if ddir.resolve() not in path.parents and path != ddir.resolve():
            return self._bad_request("invalid_path")
        if not path.exists() or not path.is_file():
            return self._json(404, {"ok": False, "error": "not_found"})
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self._send(200, data, ctype)

    def _get_pc_files(self) -> None:
        if not self._authed():
            return self._unauthorized()
        files = list_pc_outgoing(self.state)
        self._json(200, {"ok": True, "files": files})

    def _get_pc_file_download(self, name: str) -> None:
        if not self._authed():
            return self._unauthorized()
        safe = core.safe_filename(name)
        ddir = Path(self.state.config.get("outgoing_dir") or (core.DATA_DIR / "outgoing"))
        path = (ddir / safe).resolve()
        if ddir.resolve() not in path.parents and path != ddir.resolve():
            return self._bad_request("invalid_path")
        if not path.exists() or not path.is_file():
            return self._json(404, {"ok": False, "error": "not_found"})
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self._send(200, data, ctype)

    def _get_screen(self) -> None:
        if not self._authed():
            return self._unauthorized()
        with self.state.lock:
            data = self.state.last_screen_jpeg
            ts = self.state.last_screen_ts
        if not data:
            return self._json(404, {"ok": False, "error": "no_frame"})
        self._send(200, data, "image/jpeg", {"X-Frame-Timestamp": str(ts)})

    # --- POST handlers ---

    def _json_body(self) -> Optional[Dict[str, Any]]:
        try:
            raw = _read_body(self)
            if not raw:
                return {}
            data = core.json_loads_bytes(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _post_pair(self) -> None:
        data = self._json_body()
        if data is None:
            return self._bad_request("invalid_json")
        if not core.check_token(str(data.get("token") or ""), self.state.token()):
            return self._unauthorized()
        info = data.get("device") if isinstance(data.get("device"), dict) else {}
        info = {
            "name": str(info.get("name") or "phone"),
            "platform": str(info.get("platform") or "android"),
            "model": str(info.get("model") or ""),
            "version": str(info.get("version") or ""),
        }
        self.state.set_phone(info)
        self._json(200, {
            "ok": True,
            "pc": {
                "name": self.state.config.get("device_name"),
                "version": core.VERSION,
                "protocol": core.PROTOCOL,
            },
        })

    def _post_phone_event(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body()
        if data is None:
            return self._bad_request("invalid_json")
        self.state.touch_phone()
        etype = str(data.get("type") or "")
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        # normalize/store some event types for UI
        if etype == "clipboard":
            text = str(payload.get("text") or "")
            with self.state.lock:
                self.state.clipboard_text = text
            self.state.publish(core.Event("clipboard", {"text": text, "source": "phone"}, source="phone").to_dict())
        elif etype == "media":
            with self.state.lock:
                self.state.media = payload
            self.state.publish(core.Event("media", payload, source="phone").to_dict())
        elif etype == "notification":
            with self.state.lock:
                self.state.messages.append({"ts": core.now_ms(), **payload})
                self.state.messages = self.state.messages[-200:]
            self.state.publish(core.Event("notification", payload, source="phone").to_dict())
        elif etype == "call":
            with self.state.lock:
                self.state.calls.append({"ts": core.now_ms(), **payload})
                self.state.calls = self.state.calls[-100:]
            self.state.publish(core.Event("call", payload, source="phone").to_dict())
        elif etype == "command_result":
            self.state.publish(core.Event("command_result", payload, source="phone").to_dict())
        elif etype == "log":
            self.state.publish(core.Event("phone_log", payload, source="phone").to_dict())
        elif etype == "disconnect":
            self.state.disconnect_phone()
        else:
            self.state.publish(core.Event(etype or "event", payload, source="phone").to_dict())
        self._json(200, {"ok": True})

    def _post_clipboard(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body()
        if data is None:
            return self._bad_request("invalid_json")
        text = str(data.get("text") or "")
        source = str(data.get("source") or "phone")
        with self.state.lock:
            self.state.clipboard_text = text
        if source == "pc":
            # explicit PC-originated update: notify phone clients
            self.state.publish(core.Event("pc_clipboard", {"text": text}, source="pc").to_dict())
        self.state.publish(core.Event("clipboard", {"text": text, "source": source}, source=source).to_dict())
        self._json(200, {"ok": True})

    def _post_commands(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body()
        if data is None:
            return self._bad_request("invalid_json")
        cmds = data.get("commands")
        if not isinstance(cmds, list):
            return self._bad_request("commands_must_be_list")
        cleaned = []
        for item in cmds[:200]:
            if isinstance(item, dict) and item.get("name") and item.get("action"):
                cleaned.append({
                    "id": str(item.get("id") or core.make_id("cmd")),
                    "name": str(item.get("name")),
                    "action": str(item.get("action")),
                    "payload": item.get("payload") if isinstance(item.get("payload"), dict) else {},
                    "target": str(item.get("target") or "pc"),
                })
        with self.state.lock:
            self.state.saved_commands = cleaned
            core.save_commands(cleaned)
        self._json(200, {"ok": True, "commands": cleaned})

    def _post_commands_run(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body()
        if data is None:
            return self._bad_request("invalid_json")
        target = str(data.get("target") or "phone")
        command = data.get("command") if isinstance(data.get("command"), dict) else {}
        if target == "phone":
            self.state.publish(core.Event("run_command", {"command": command}, source="pc").to_dict())
            return self._json(200, {"ok": True, "queued": True})
        # target == pc
        if not self.state.config.get("allow_pc_command_exec", False):
            return self._json(403, {"ok": False, "error": "pc_command_exec_disabled"})
        result = run_pc_command(command)
        self.state.publish(core.Event("command_result", {"target": "pc", **result}, source="pc").to_dict())
        self._json(200, {"ok": True, "result": result})

    def _post_file_upload(self) -> None:
        if not self._authed():
            return self._unauthorized()
        # Support raw body upload with X-Filename header or JSON {name,data_b64}
        ctype = (self.headers.get("Content-Type") or "").lower()
        ddir = Path(self.state.config.get("download_dir") or core.DOWNLOAD_DIR)
        try:
            if "application/json" in ctype:
                data = self._json_body()
                if data is None:
                    return self._bad_request("invalid_json")
                name = core.safe_filename(str(data.get("name") or "upload.bin"))
                blob = core.decode_bytes(str(data.get("data_b64") or ""))
            else:
                name = core.safe_filename(self.headers.get("X-Filename") or "upload.bin")
                blob = _read_body(self)
            path = core.unique_path(ddir, name)
            path.write_bytes(blob)
            meta = {"name": path.name, "size": len(blob), "path": str(path)}
            self.state.publish(core.Event("file_received", meta, source="pc").to_dict())
            self._json(200, {"ok": True, "file": meta})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def _post_screen(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = _read_body(self)
        if not data:
            return self._bad_request("empty")
        # accept raw jpeg or json {jpeg_b64}
        ctype = (self.headers.get("Content-Type") or "").lower()
        if "application/json" in ctype:
            try:
                obj = core.json_loads_bytes(data)
                jpeg = core.decode_bytes(str(obj.get("jpeg_b64") or ""))
            except Exception:
                return self._bad_request("invalid_json")
        else:
            jpeg = data
        with self.state.lock:
            self.state.last_screen_jpeg = jpeg
            self.state.last_screen_ts = time.time()
        self._json(200, {"ok": True})

    def _post_pc_media(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body() or {}
        cmd = str(data.get("cmd") or "")
        result = pc_media_command(cmd)
        self.state.publish(core.Event("pc_media_command", {"cmd": cmd, "result": result}, source="pc").to_dict())
        self._json(200, {"ok": True, "result": result})

    def _post_pc_media_status(self) -> None:
        if not self._authed():
            return self._unauthorized()
        self._json(200, {"ok": True, "media": pc_media_status()})

    def _post_command_result(self) -> None:
        if not self._authed():
            return self._unauthorized()
        data = self._json_body() or {}
        self.state.publish(core.Event("command_result", data, source="pc").to_dict())
        self._json(200, {"ok": True})


def run_pc_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Run a saved PC command locally (explicitly enabled in config).

    Supported actions: shell (argv list) and open_url. Shell commands are run
    without a shell to avoid injection; callers must provide argv arrays.
    """
    action = str(command.get("action") or "")
    payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
    try:
        if action == "open_url":
            url = str(payload.get("url") or "")
            if not (url.startswith("http://") or url.startswith("https://")):
                return {"ok": False, "error": "invalid_url"}
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "action": action}
        if action == "shell":
            argv = payload.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                return {"ok": False, "error": "argv_required"}
            # run with timeout, capture limited output
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            out = (proc.stdout or "")[-4000:]
            err = (proc.stderr or "")[-4000:]
            return {"ok": proc.returncode == 0, "code": proc.returncode, "stdout": out, "stderr": err}
        return {"ok": False, "error": "unsupported_action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pc_media_command(cmd: str) -> Dict[str, Any]:
    """Best-effort MPRIS control via playerctl if available."""
    allowed = {"play": ["play"], "pause": ["pause"], "play-pause": ["play-pause"], "next": ["next"], "previous": ["previous"], "stop": ["stop"]}
    if cmd not in allowed:
        return {"ok": False, "error": "unsupported"}
    exe = shutil.which("playerctl")
    if not exe:
        return {"ok": False, "error": "playerctl_not_found"}
    try:
        proc = subprocess.run([exe] + allowed[cmd], capture_output=True, text=True, timeout=5)
        return {"ok": proc.returncode == 0, "stderr": (proc.stderr or "").strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pc_media_status() -> Dict[str, Any]:
    exe = shutil.which("playerctl")
    if not exe:
        return {"available": False}
    try:
        fmt = "{{playerName}}\t{{status}}\t{{title}}\t{{artist}}"
        proc = subprocess.run([exe, "metadata", "--format", fmt], capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return {"available": True, "status": "stopped"}
        parts = (proc.stdout or "").strip("\n").split("\t")
        while len(parts) < 4:
            parts.append("")
        return {"available": True, "player": parts[0], "status": parts[1], "title": parts[2], "artist": parts[3]}
    except Exception:
        return {"available": True, "status": "unknown"}


class ServerThread(threading.Thread):
    def __init__(self, state: BridgeState):
        super().__init__(daemon=True)
        self.state = state
        self.httpd: Optional[BridgeHTTPServer] = None
        self.error: Optional[str] = None

    def run(self) -> None:
        host = str(self.state.config.get("listen_host") or "0.0.0.0")
        port = int(self.state.config.get("port") or core.DEFAULT_PORT)
        try:
            self.httpd = BridgeHTTPServer((host, port), self.state)
            self.httpd.serve_forever(poll_interval=0.5)
        except Exception as e:
            self.error = str(e)

    def stop(self) -> None:
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None


# --- extra helpers for PC GUI / extended protocol ---

def list_pc_outgoing(state: BridgeState) -> list:
    outdir = Path(state.config.get("outgoing_dir") or (core.DATA_DIR / "outgoing"))
    outdir.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted(outdir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:200]:
        if p.is_file():
            st = p.stat()
            files.append({"name": p.name, "size": st.st_size, "mtime": int(st.st_mtime)})
    return files


def add_pc_outgoing(state: BridgeState, src_path: str) -> Dict[str, Any]:
    src = Path(src_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(src_path)
    outdir = Path(state.config.get("outgoing_dir") or (core.DATA_DIR / "outgoing"))
    dst = core.unique_path(outdir, src.name)
    shutil.copy2(src, dst)
    return {"name": dst.name, "size": dst.stat().st_size, "path": str(dst)}
