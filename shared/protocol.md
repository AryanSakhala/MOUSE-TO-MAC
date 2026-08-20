# Protocol

WebSocket binary frames. Auth: `?k=<access-key>` on HTTP and WS.

| Op | Size | Body |
|----|------|------|
| 1 MOVE | 9 | float32 dx, float32 dy (LE) |
| 2 SCROLL | 5 | float32 dy |
| 3 CLICK | 2 | u8 0=left 1=right 2=double |
| 4 SPACE | 2 | u8 0=left 1=right 2=up 3=down |

Legacy MOVE/SCROLL int16×64 packets still accepted. Port: 8765.
