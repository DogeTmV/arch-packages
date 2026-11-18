# LanBridge connection tutorial

This guide covers connecting the LanBridge Android app to the LanBridge PC app over the same Wi-Fi network, required permissions, and later use over Tailscale.

## 1. Same Wi-Fi setup (recommended first)

### On the PC

1. Install/run LanBridge on your Linux PC.
   - From source: `python3 lanbridge            # desktop app
# or run headless bridge server (for background/systemd):
# python3 lanbridge --server`
   - Ensure dependencies are installed (Python 3, PySide6; `playerctl` optional for media control).
2. Open **Settings** in LanBridge.
3. Note the **Listen address** and **Port** (default port is `8765`).
   - For same-Wi-Fi use, listen on `0.0.0.0` (all interfaces) or your LAN IP (e.g. `192.168.1.20`).
4. Set or copy the **Pairing token**. This is a shared secret required by the phone.
5. Click **Start server**. Status should show `Listening`.
6. Allow the port through your firewall if enabled:
   - `ufw`: `sudo ufw allow 8765/tcp` (and UDP if you enable discovery later)
   - `firewalld`: `sudo firewall-cmd --add-port=8765/tcp --temporary` (or permanent)

Find your PC LAN IP with `ip addr` (look for your Wi-Fi interface, usually `wlan0`, address like `192.168.x.x`).

### On the Android phone

1. Build/install the Android app from `projects/lanbridge/android/` using Android Studio, or install your built APK.
2. Connect the phone to the **same Wi-Fi network** as the PC.
3. Open LanBridge and go to **Connect**.
4. Enter:
   - **PC address**: your PC LAN IP (e.g. `192.168.1.20`)
   - **Port**: `8765` (or your chosen port)
   - **Token**: the exact pairing token from the PC
5. Tap **Connect**. Grant notification permission if prompted (used for the foreground connection service on newer Android).
6. When connected, the dashboard tabs/features become available.

### Verify

- PC shows the device as connected with its name/model.
- Use **Clipboard → Send test** or **Files → Send** to confirm data transfer.
- Start **Screen share** on Android when prompted to allow capture; the PC Screen tab should display frames.

## 2. Android permissions (grant as needed)

LanBridge requests permissions only for features you use. You can grant them later in Android Settings → Apps → LanBridge → Permissions.

| Permission / access | Needed for | How to enable |
|---|---|---|
| Notifications (Android 13+) | Foreground service / connection status | Prompt on first run or App info → Notifications |
| Screen capture (MediaProjection prompt) | Phone screen viewing on PC | Prompt when starting screen share (not a permanent toggle) |
| Accessibility Service | Controlling phone from PC (taps/swipes/navigation) | Settings → Accessibility → LanBridge → Enable. Review carefully; this allows remote input when connected |
| Notification Listener | Mirroring notifications/media info to PC | Settings → Notification access → LanBridge |
| SMS / Phone / Call log (if requested) | Mirroring messages/call events to PC | Runtime permission prompts; behavior varies by Android version/OEM |
| Media/Photos/Files access | Sending/receiving files | Runtime prompts (scoped storage on modern Android) |

**Limitations:** Stock Android does not allow third-party apps to answer/end calls as a remote PC peripheral without special dialer roles; LanBridge can notify you of incoming calls but cannot replace your phone app. Some OEMs restrict background services—disable battery optimization for LanBridge if the connection drops.

## 3. Using features

- **Screen:** Start capture on phone, view on PC. Enable Accessibility to send taps/swipes/Back/Home/Recents from PC controls.
- **Commands:** Create saved commands on each side. Android commands include safe actions (open URL, app intent shortcuts, copy text) and optional shell-in-sandbox execution for advanced users. PC local-command execution is off by default; enable it in Settings if you want the phone to trigger saved PC commands.
- **Clipboard:** Enable auto-sync or use Push/Pull buttons. Text only in this version.
- **Files:** Pick files to send; received files go to the configured download folder (PC: `~/Downloads/LanBridge` by default, Android: app downloads location shown in UI).
- **Messages/Calls:** Shows mirrored notifications/events received from the phone when permissions are granted.
- **Media:** Shows current playback info and transport controls. PC side uses MPRIS (`playerctl`) when available; Android side controls active media sessions when allowed.

## 4. Later: connect outside Wi-Fi with Tailscale

When you want to use LanBridge away from home, put both devices on the same private VPN instead of exposing ports publicly.

1. Install [Tailscale](https://tailscale.com/) on the PC and Android phone and sign in to the same tailnet.
2. Confirm both devices can reach each other (check Tailscale IPs like `100.x.y.z` or MagicDNS names).
3. In LanBridge PC Settings, you can keep listening on `0.0.0.0` or bind to the Tailscale interface/IP.
4. On Android, set the **PC address** to the PC's Tailscale IP or MagicDNS hostname.
5. Keep the same port and pairing token. Ensure your firewall allows traffic from the Tailscale interface (`tailscale0`).
6. Connect as usual. Performance depends on your VPN path; screen streaming may use more bandwidth/latency than local Wi-Fi.

**Do not** port-forward LanBridge from your router to the internet. A VPN overlay like Tailscale/WireGuard provides authenticated private connectivity.

## 5. Troubleshooting

- **Cannot connect:** verify same network/Tailscale reachability, correct IP, port, token, firewall rules, and that the PC server is started.
- **Screen share black/fails:** re-start capture and accept the MediaProjection prompt; some apps block capture (DRM/secure flags).
- **Remote control not working:** Accessibility Service must be enabled for LanBridge.
- **No messages/calls/media info:** grant Notification access/SMS/Phone permissions and disable battery optimizations.
- **Drops in background:** keep the Android foreground service active and exempt the app from aggressive battery management.
- **PC media controls missing:** install/configure `playerctl` and ensure an MPRIS-compatible player is running.

## 6. Desktop mirroring note (PC ↔ phone)

LanBridge currently focuses on **phone → PC** screen viewing/control and feature sync. Full, low-latency **PC screen control from phone** is a different problem (capture, encoding, input injection on the desktop session). For that use case today, pair LanBridge with a dedicated remote-desktop tool over the same LAN/Tailscale (e.g. WayVNC/VNC, RustDesk, Sunshine/Moonlight depending on your setup), and use LanBridge for commands, clipboard, files, notifications, and media.



## Background connection tips (Android)

- Keep LanBridge battery optimization disabled/unrestricted so the foreground connection service can reconnect reliably.
- Allow notifications (Android 13+) so the foreground service notification can be shown.
- After saving host/token in Settings, LanBridge starts a foreground service and will try to reconnect automatically in background and after reboot (if configured).
- For remote control, enable **Accessibility** for LanBridge (Installed apps/downloaded services → LanBridge). Status in the app updates when the service connects.
- For notification/call/message mirroring, enable **Notification access** for LanBridge.

