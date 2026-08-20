# Mouse to Mac

Android phone as a Mac trackpad over the phone hotspot. No phone app.

## Setup

1. Join the Mac to your Android hotspot.
2. Grant Terminal Accessibility: System Settings > Privacy & Security > Accessibility.
3. Start the host:

```bash
cd host
bash start.sh
```

4. Scan the QR in the terminal (or open the printed URL).

## Gestures

| Gesture | Action |
|---------|--------|
| Drag | Move pointer |
| Tap | Click |
| Double-tap | Double-click |
| Long-press | Right-click |
| Top Left / Right | Mouse buttons |
| Two-finger drag | Scroll |
| Three-finger left / right | Switch desktop |
| Three-finger up | Mission Control |
| Three-finger down | App windows |

Speed controls sit under the trackpad.

Each run prints a new access key (`?k=`). Only that key opens the trackpad.
