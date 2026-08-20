# Protocol

WebSocket binary frames. Auth: `?k=<access-key>` on HTTP and WS.

| Op | Size | Body |
|----|------|------|
| 1 MOVE | 5 | i16 dx*64, i16 dy*64 |
| 2 SCROLL | 3 | i16 dy*64 |
| 3 CLICK | 2 | u8 0=left 1=right 2=double |
| 4 SPACE | 2 | u8 0=left 1=right 2=up 3=down |

Port default: 8765.
