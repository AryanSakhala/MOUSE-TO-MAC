#!/usr/bin/env python3
"""Mac host: binary WebSocket trackpad, token auth, terminal QR."""

from __future__ import annotations

import asyncio
import hmac
import os
import secrets
import signal
import socket
import struct
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from websockets.asyncio.server import ServerConnection, serve
    from websockets.exceptions import ConnectionClosed
    from websockets.http11 import Request, Response
except ImportError:
    print("Install deps: pip install -r host/requirements.txt", file=sys.stderr)
    raise

try:
    import qrcode
except ImportError:
    qrcode = None  # type: ignore

from mouse import MotionPump, Mouse

PORT = int(os.environ.get("MOUSE_TO_MAC_PORT", "8765"))
ROOT = Path(__file__).resolve().parent
TRACKPAD_PATH = ROOT / "static" / "trackpad.html"

# Protocol: float32 moves (v3). Legacy int16 still accepted.
OP_MOVE = 1
OP_SCROLL = 2
OP_CLICK = 3
OP_SPACE = 4
OP_DOWN = 5
OP_UP = 6
BTN_LEFT = 0
BTN_RIGHT = 1
BTN_DOUBLE = 2
SPACE_LEFT = 0
SPACE_RIGHT = 1
SPACE_UP = 2
SPACE_DOWN = 3
SCALE_LEGACY = 64.0

TOKEN = secrets.token_urlsafe(8)


def lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    for iface in ("en0", "en1", "en2", "bridge100"):
        try:
            out = subprocess.check_output(
                ["ipconfig", "getifaddr", iface],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if out and out not in ips:
                ips.insert(0, out)
        except subprocess.CalledProcessError:
            continue
    return ips


def token_from_path(path: str) -> str | None:
    q = parse_qs(urlparse(path).query)
    vals = q.get("k") or q.get("token")
    return vals[0] if vals else None


def is_private(ip: str) -> bool:
    try:
        parts = [int(x) for x in ip.split(".")]
    except ValueError:
        return False
    if parts[0] == 10:
        return True
    if parts[0] == 172 and 16 <= parts[1] <= 31:
        return True
    if parts[0] == 192 and parts[1] == 168:
        return True
    if parts[0] == 100:
        return True
    return False


def print_qr(url: str) -> None:
    if qrcode is None:
        print("(install qrcode for terminal QR: pip install qrcode)", flush=True)
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    print("Scan with phone camera / Chrome:", flush=True)
    qr.print_ascii(invert=True)
    print(flush=True)


def unlock_page() -> str:
    return """<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Mouse to Mac</title>
<style>
body{font-family:system-ui;background:#0b1220;color:#e2e8f0;display:flex;
min-height:100vh;align-items:center;justify-content:center;margin:0}
form{display:flex;flex-direction:column;gap:12px;width:min(360px,92vw)}
input,button{font-size:18px;padding:14px;border-radius:12px;border:0}
input{background:#111827;color:#fff}
button{background:#38bdf8;color:#0b1220;font-weight:700}
p{color:#94a3b8;line-height:1.4}
</style></head><body><form method=GET>
<h1>Mouse to Mac</h1>
<p>Enter the access key from the Mac terminal, or scan the QR shown there.</p>
<input name=k placeholder="Access key" autocomplete=off autocapitalize=off required>
<button type=submit>Open trackpad</button>
</form></body></html>"""


async def process_request(connection: ServerConnection, request: Request) -> Response | None:
    path = request.path
    upgrade = request.headers.get("Upgrade", "").lower() == "websocket"
    key = token_from_path(path)

    if upgrade:
        if not key or not hmac.compare_digest(key, TOKEN):
            return connection.respond(403, "Forbidden")
        peer = connection.remote_address
        if peer and isinstance(peer, tuple) and peer[0]:
            ip = str(peer[0])
            if ip not in ("127.0.0.1", "::1") and not is_private(ip):
                return connection.respond(403, "Forbidden")
        return None

    clean = urlparse(path).path
    if clean in ("/", "/index.html", "/trackpad"):
        if not key or not hmac.compare_digest(key, TOKEN):
            resp = connection.respond(200, unlock_page())
            resp.headers["Content-Type"] = "text/html; charset=utf-8"
            resp.headers["Cache-Control"] = "no-store"
            return resp
        html = TRACKPAD_PATH.read_text(encoding="utf-8")
        resp = connection.respond(200, html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    return connection.respond(404, "Not found")


def enable_nodelay(ws: ServerConnection) -> None:
    try:
        transport = getattr(ws, "transport", None)
        if transport is None:
            return
        sock = transport.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        pass


def decode_packet(data: bytes, pump: MotionPump, mouse: Mouse) -> None:
    if not data:
        return
    op = data[0]
    if op == OP_MOVE:
        if len(data) >= 9:
            dx, dy = struct.unpack_from("<ff", data, 1)
            pump.add_move(dx, dy)
        elif len(data) >= 5:
            dx_i, dy_i = struct.unpack_from("<hh", data, 1)
            pump.add_move(dx_i / SCALE_LEGACY, dy_i / SCALE_LEGACY)
    elif op == OP_SCROLL:
        if len(data) >= 5:
            (dy,) = struct.unpack_from("<f", data, 1)
            pump.add_scroll(dy)
        elif len(data) >= 3:
            (dy_i,) = struct.unpack_from("<h", data, 1)
            pump.add_scroll(dy_i / SCALE_LEGACY)
    elif op == OP_DOWN and len(data) >= 2:
        pump.flush_now()
        mouse.down("right" if data[1] == BTN_RIGHT else "left")
    elif op == OP_UP and len(data) >= 2:
        pump.flush_now()
        mouse.up("right" if data[1] == BTN_RIGHT else "left")
    elif op == OP_CLICK and len(data) >= 2:
        pump.flush_now()
        btn = data[1]
        if btn == BTN_DOUBLE:
            pump.run_blocking(mouse.double_click)
        elif btn == BTN_RIGHT:
            mouse.click("right")
        else:
            mouse.click("left")
    elif op == OP_SPACE and len(data) >= 2:
        pump.flush_now()
        d = data[1]
        if d == SPACE_LEFT:
            pump.run_blocking(mouse.space_left)
        elif d == SPACE_RIGHT:
            pump.run_blocking(mouse.space_right)
        elif d == SPACE_UP:
            pump.run_blocking(mouse.mission_control)
        elif d == SPACE_DOWN:
            pump.run_blocking(mouse.app_windows)


_active: ServerConnection | None = None


async def handler(ws: ServerConnection, mouse: Mouse, pump: MotionPump) -> None:
    global _active
    enable_nodelay(ws)

    if _active is not None and _active is not ws:
        try:
            await _active.close(4000, "replaced")
        except Exception:
            pass
    _active = ws
    mouse.resync()
    peer = ws.remote_address
    print(f"client connected: {peer}", flush=True)

    try:
        await ws.send(struct.pack("<B", 0x7F))
        async for raw in ws:
            if isinstance(raw, bytes):
                decode_packet(raw, pump, mouse)
    except ConnectionClosed:
        pass
    finally:
        if _active is ws:
            _active = None
        print(f"client disconnected: {peer}", flush=True)


async def main() -> None:
    mouse = Mouse()
    pump = MotionPump(mouse, hz=144.0)
    pump.start()
    ips = lan_ips() or ["127.0.0.1"]
    primary = ips[0]
    url = f"http://{primary}:{PORT}/?k={TOKEN}"

    print("=" * 56, flush=True)
    print("Mouse to Mac", flush=True)
    print("=" * 56, flush=True)
    print(f"Access key: {TOKEN}", flush=True)
    print(f"URL: {url}", flush=True)
    for ip in ips[1:]:
        print(f"  alt: http://{ip}:{PORT}/?k={TOKEN}", flush=True)
    print("=" * 56, flush=True)
    print_qr(url)
    print("Gestures: drag, tap, double-tap, long-press right,", flush=True)
    print("  two-finger scroll, three-finger swipe = Spaces / Mission Control", flush=True)
    print("Accessibility: System Settings > Privacy & Security > Accessibility", flush=True)

    stop = asyncio.get_running_loop().create_future()

    def _stop(*_a: object) -> None:
        if not stop.done():
            stop.set_result(True)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    async def on_connect(ws: ServerConnection) -> None:
        await handler(ws, mouse, pump)

    try:
        async with serve(
            on_connect,
            "0.0.0.0",
            PORT,
            process_request=process_request,
            max_size=64 * 1024,
            ping_interval=20,
            ping_timeout=20,
        ):
            print(f"listening on 0.0.0.0:{PORT}", flush=True)
            await stop
    finally:
        pump.stop()


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    asyncio.run(main())
