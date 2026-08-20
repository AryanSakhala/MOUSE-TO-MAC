# Protocol

WebSocket binary frames. Auth: `?k=<access-key>` on HTTP and WS.

| Op | Size | Body |
|----|------|------|
| 1 MOVE | 9 | float32 dx, float32 dy |
| 2 SCROLL | 5 | float32 dy |
| 3 CLICK | 2 | u8 0=left 1=right 2=double |
| 4 SPACE | 2 | u8 0=left 1=right 2=up 3=down |
| 5 DOWN | 2 | u8 button 0=left 1=right |
| 6 UP | 2 | u8 button 0=left 1=right |

Legacy MOVE/SCROLL int16×64 packets still accepted. Port: 8765.
