# Mouse to Mac

Use an Android phone as a Mac trackpad over the phone hotspot. No phone app.

## Setup

1. Join the Mac to your Android hotspot.
2. Grant Terminal Accessibility: System Settings > Privacy & Security > Accessibility.
3. Start the host:

```bash
cd host
bash start.sh
```

4. Scan the QR code in the terminal (or open the printed URL) on the phone.

## Gestures

| Gesture | Action |
|---------|--------|
| Drag | Move pointer |
| Tap | Click |
| Double-tap | Double-click |
| Long-press | Right-click |
| Two-finger drag | Scroll |
| Three-finger left / right | Switch desktop (Spaces) |
| Three-finger up | Mission Control |
| Three-finger down | App windows |

## Layout

```
host/server.py          WebSocket + HTTP host
host/mouse.py           CoreGraphics injection
host/static/trackpad.html
host/start.sh
```

Each run prints a new access key in the URL (`?k=`). Only that key can open the trackpad.
