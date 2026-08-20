# Protocol

HTTPS page + WSS binary frames (same port). Auth: `?k=<access-key>` on the URL.

Air mode uses the same opcodes as Pad — the phone maps IMU → relative `MOVE` packets.

| Op | Size | Body |
|----|------|------|
| 1 MOVE | 9 | float32 dx, float32 dy |
| 2 SCROLL | 5 | float32 dy |
| 3 CLICK | 2 | u8 0=left 1=right 2=double |
| 4 SPACE | 2 | u8 0=left 1=right 2=up 3=down |
| 5 DOWN | 2 | u8 button 0=left 1=right |
| 6 UP | 2 | u8 button 0=left 1=right |

Legacy MOVE/SCROLL int16×64 packets still accepted. Default port: **8765** (TLS).

## Transport

- Page: `https://<mac-ip>:8765/?k=<token>`
- Socket: `wss://<mac-ip>:8765/?k=<token>`
- Self-signed cert in `host/certs/` — phone must accept the warning once

## Client modes (UI only)

| Mode | Source of MOVE | Notes |
|------|----------------|-------|
| Pad | Touch glide | Gestures unchanged |
| Air | `DeviceMotion` `rotationRate` (fallback: orientation vs Recenter) | Deadzone + EMA + idle bias recal on client |

No extra host opcodes for v1 Air motion.
