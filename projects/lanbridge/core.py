"""LanBridge core: protocol constants, storage, and pure helpers.

This module has no Qt or Android dependencies so it can be unit-tested and
reused by the GUI, server, and CLI entry points.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import socket
import string
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "0.1.0"
DEFAULT_PORT = 8765
APP_NAME = "LanBridge"
PROTOCOL = 1

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "lanbridge"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "lanbridge"
DOWNLOAD_DIR = Path.home() / "Downloads" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
COMMANDS_FILE = CONFIG_DIR / "commands.json"


def ensure_dirs() -> None:
    for path in (CONFIG_DIR, DATA_DIR, DOWNLOAD_DIR):
        path.mkdir(parents=True, exist_ok=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def make_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_token(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def default_config() -> Dict[str, Any]:
    return {
        "listen_host": "0.0.0.0",
        "port": DEFAULT_PORT,
        "token": generate_token(),
        "device_name": socket.gethostname() or "pc",
        "allow_pc_command_exec": False,
        "clipboard_auto_push": False,
        "download_dir": str(DOWNLOAD_DIR),
        "known_devices": {},
    }


def load_config() -> Dict[str, Any]:
    ensure_dirs()
    cfg = default_config()
    stored = _read_json(CONFIG_FILE, {})
    if isinstance(stored, dict):
        cfg.update({k: v for k, v in stored.items() if k in cfg or k == "known_devices"})
        # keep generated token stable only if missing
        if not stored.get("token"):
            cfg["token"] = stored.get("token") or cfg["token"]
    # always ensure token exists
    if not cfg.get("token"):
        cfg["token"] = generate_token()
    _write_json(CONFIG_FILE, cfg)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    ensure_dirs()
    _write_json(CONFIG_FILE, cfg)


def load_commands() -> List[Dict[str, Any]]:
    ensure_dirs()
    data = _read_json(COMMANDS_FILE, [])
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if isinstance(item, dict) and item.get("name") and item.get("action"):
            out.append({
                "id": item.get("id") or make_id("cmd"),
                "name": str(item["name"]),
                "action": str(item["action"]),
                "payload": item.get("payload") or {},
                "target": item.get("target") or "pc",
            })
    return out


def save_commands(commands: Iterable[Dict[str, Any]]) -> None:
    ensure_dirs()
    _write_json(COMMANDS_FILE, list(commands))


def check_token(provided: Optional[str], expected: str) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(str(provided), str(expected))


def auth_token_from_headers(headers: Any) -> Optional[str]:
    auth = headers.get("Authorization", "") if headers else ""
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth.split(None, 1)[1].strip()
    if headers and headers.get("X-LanBridge-Token"):
        return str(headers.get("X-LanBridge-Token"))
    return None


def json_dumps(data: Any) -> bytes:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def json_loads_bytes(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def safe_filename(name: str) -> str:
    name = os.path.basename((name or "file").replace("\\", "/"))
    cleaned = "".join(ch if ch.isalnum() or ch in "._- ()" else "_" for ch in name).strip("._ ")
    return cleaned or "file"


def unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base = safe_filename(filename)
    path = directory / base
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for i in range(1, 10000):
        cand = directory / f"{stem} ({i}){suffix}"
        if not cand.exists():
            return cand
    return directory / f"{stem}-{uuid.uuid4().hex[:6]}{suffix}"


def encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_bytes(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: make_id("evt"))
    ts: int = field(default_factory=now_ms)
    source: str = "pc"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventBus:
    """Simple in-process subscriber bus for server/UI coordination."""

    def __init__(self) -> None:
        import threading

        self._lock = threading.Lock()
        self._subs: List[Any] = []

    def subscribe(self, queue_obj: Any) -> None:
        with self._lock:
            self._subs.append(queue_obj)

    def unsubscribe(self, queue_obj: Any) -> None:
        with self._lock:
            self._subs = [s for s in self._subs if s is not queue_obj]

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(event)
            except Exception:
                try:
                    q.put(event, timeout=0.1)
                except Exception:
                    pass


def lan_addresses() -> List[str]:
    addrs = []
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None):
            ip = info[4][0]
            if ":" in ip or ip.startswith("127."):
                continue
            if ip not in addrs:
                addrs.append(ip)
    except Exception:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and ip not in addrs and not ip.startswith("127."):
                addrs.insert(0, ip)
    except Exception:
        pass
    return addrs
