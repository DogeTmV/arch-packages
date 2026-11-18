# LanBridge

LanBridge is a local-network companion app for connecting a Linux PC and an Android phone over the same Wi-Fi. It includes:

- **PC app** (`lanbridge`) — a PySide6 desktop dashboard and local bridge server
- **Android app** (`android/`) — a Kotlin + Jetpack Compose client/service app

The focus is a clean dark UI, simple LAN pairing, and practical features with clear permission requirements.

## Features

| Feature | Status | Notes |
|---|---|---|
| View phone screen on PC | Implemented (MJPEG stream) | Requires Android screen-capture permission each session |
| Control phone screen from PC | Implemented (basic tap/swipe/back/home) | Requires enabling LanBridge Accessibility Service on Android |
| View/control PC screen from phone | Partial / roadmap | Not enabled by default; use VNC/RustDesk for full desktop mirroring today. Tutorial includes Tailscale + alternatives |
| Run custom commands | Implemented | Android executes app-level actions and optional shell commands in app sandbox; PC can run saved local commands when explicitly enabled |
| Saved command list | Implemented | Stored locally on both devices, one-tap run |
| Shared clipboard | Implemented | Text clipboard sync over LAN (manual/auto modes) |
| Send photos/files | Implemented | HTTP transfer with progress and receive folder |
| Messages on PC | Implemented (notification/SMS mirror where permitted) | Depends on Android permissions and OEM restrictions; not a full SMS replacement app |
| Receive phone calls on PC | Partial | Incoming-call notifications/state mirrored to PC; answering from PC is not supported on stock Android without dialer-role integration |
| Media control both ways | Implemented (best effort) | Android media sessions + PC MPRIS players where available |

> **Security note:** LanBridge is designed for trusted networks/devices. It uses a pairing token, binds to LAN interfaces you choose, and avoids shell injection by treating commands as explicit actions/argv where possible. Do not expose it directly to the public internet; for remote access use a VPN overlay such as Tailscale.

## Project layout

```
projects/lanbridge/
  README.md
  TUTORIAL.md
  core.py            # protocol, storage, helpers (no Qt deps)
  server.py          # PC bridge server/client logic
  gui.py             # PySide6 desktop UI
  theme.py           # dark theme
  lanbridge          # launcher
  lanbridge.desktop
  icons/
  tests/
  android/           # Android Studio / Gradle project (Kotlin, Compose)
  docs/
```

## PC app

### Requirements

- Python 3
- PySide6 (`pyside6`, `qt6-svg` on Arch)
- Optional for media control: `playerctl` (MPRIS)

### Run from source

```bash
cd projects/lanbridge
python3 lanbridge --help
python3 lanbridge
```

Run tests:

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

## Android app

The Android client lives in `android/`. Open it in Android Studio (recent stable), let Gradle sync, and build/run on a device (Android 8.0+ recommended; some features need newer APIs).

See [TUTORIAL.md](TUTORIAL.md) for permissions, pairing, firewall notes, and Tailscale usage.

## License

MIT — see [LICENSE](LICENSE). Original implementation.
