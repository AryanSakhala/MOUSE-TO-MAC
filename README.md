# Mouse to Mac

Android phone as a Mac trackpad (and IMU air mouse) over the phone hotspot. No phone app — Chrome + HTTPS.

## Setup

1. Have Mac and  mobile connected to the same Wi-Fi, or have your Mac connected to the mobile hotspot.
2. Grant Terminal Accessibility: System Settings → Privacy & Security → Accessibility.
3. Start the host:

```bash
cd host
bash start.sh
```

4. Scan the **https://** QR in the terminal (or open the printed URL).
5. First visit: Chrome → Advanced → Proceed (self-signed cert). One-time per cert/IP.

The host serves **HTTPS + WSS** on port `8765` so the browser can read motion sensors for Air mode. Each run prints a new access key (`?k=`).

## Modes

### Pad (default)

| Gesture | Action |
|---------|--------|
| 1-finger glide | Move pointer (no select) |
| Tap | Click |
| Double-tap | Double-click |
| Double-tap then hold & drag | Select / drag |
| Long-press | Right-click |
| Top Left / Right | Press = down, release = up (hold to drag) |
| Two-finger drag | Scroll |
| Three-finger left / right | Switch desktop |
| Three-finger up | Mission Control |
| Three-finger down | App windows |

### Air

Hold the phone like a **TV remote** (upright). Joystick-style tilt from Recenter — not free 6DOF waving.

1. Switch to **Air** → **Enable sensors** (unlocks IMU + vibration on Android).
2. Hold still upright → auto-recenter (or tap **Recenter**).
3. **Tilt left/right** or **tip forward/back** only. Twist/yaw is ignored.
4. Return upright to stop. **Cardinal lock** (on by default) keeps motion on one axis at a time.
5. **Vibration**: pulse when you leave the deadzone, hit full lean, recenter, or press Left/Right.
6. Top **Left** / **Right** still work for click/drag.

Needs `https://` (self-signed OK). Android Chrome vibration requires haptics enabled in system settings (not silent/DND blocking vibration).

## Notes

- Speed controls sit under the pad / air panel.
- Pad gestures are unchanged when you switch back from Air.
- Certs live in `host/certs/` (gitignored); delete that folder to regenerate.
