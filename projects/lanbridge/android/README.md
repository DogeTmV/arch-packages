# LanBridge Android app

This directory contains the Android client for LanBridge (Kotlin + Jetpack Compose, Material 3, dark theme).

## Build

1. Open this `android/` folder in a recent stable Android Studio.
2. Let Gradle sync (Android Studio can generate/use a wrapper as needed for your environment).
3. Connect an Android device (Android 8.0+ recommended) with USB debugging, or create an emulator.
4. Build and run the `app` configuration.

## Notes

- The app uses cleartext HTTP for local/Tailscale LAN connections (`usesCleartextTraffic="true"`). Use it on trusted networks or over Tailscale.
- Grant permissions only for features you need: notifications, screen capture prompt (per session), Accessibility (remote control), Notification access (mirroring), and media/file access for transfers.
- See `../TUTORIAL.md` for pairing and connection steps.

## Project highlights

- `service/BridgeConnectionService` maintains the connection and SSE event stream to the PC.
- `service/ScreenCaptureService` captures the screen via MediaProjection and pushes JPEG frames to the PC.
- `service/LanBridgeAccessibilityService` performs input gestures/navigation requested by the PC.
- `service/LanBridgeNotificationService` mirrors notifications to the PC when enabled.
- `ui/LanBridgeApp.kt` provides the Compose UI and feature screens.
- `net/BridgeApi.kt` implements the HTTP protocol client.
