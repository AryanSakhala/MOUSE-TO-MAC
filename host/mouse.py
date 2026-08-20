"""macOS pointer + keyboard injection via CoreGraphics."""

from __future__ import annotations

import ctypes
import ctypes.util
import threading
import time
from ctypes import c_bool, c_double, c_int32, c_int64, c_uint32, c_void_p


class CGPoint(ctypes.Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


KEY_LEFT = 0x7B
KEY_RIGHT = 0x7C
KEY_DOWN = 0x7D
KEY_UP = 0x7E
FLAG_CONTROL = 0x40000


class Mouse:
    def __init__(self) -> None:
        cg_path = ctypes.util.find_library("CoreGraphics")
        cf_path = ctypes.util.find_library("CoreFoundation")
        if not cg_path or not cf_path:
            raise RuntimeError("CoreGraphics not available")

        self._cg = ctypes.CDLL(cg_path)
        self._cf = ctypes.CDLL(cf_path)
        self._lock = threading.Lock()

        self._cg.CGEventSourceCreate.restype = c_void_p
        self._cg.CGEventSourceCreate.argtypes = [c_uint32]
        self._cg.CGEventCreate.restype = c_void_p
        self._cg.CGEventCreate.argtypes = [c_void_p]
        self._cg.CGEventGetLocation.restype = CGPoint
        self._cg.CGEventGetLocation.argtypes = [c_void_p]
        self._cg.CGEventCreateMouseEvent.restype = c_void_p
        self._cg.CGEventCreateMouseEvent.argtypes = [
            c_void_p,
            c_uint32,
            CGPoint,
            c_uint32,
        ]
        self._cg.CGEventCreateScrollWheelEvent.restype = c_void_p
        self._cg.CGEventCreateScrollWheelEvent.argtypes = [
            c_void_p,
            c_uint32,
            c_uint32,
            c_int32,
        ]
        self._cg.CGEventCreateKeyboardEvent.restype = c_void_p
        self._cg.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint32, c_bool]
        self._cg.CGEventSetFlags.argtypes = [c_void_p, c_uint32]
        self._cg.CGEventSetIntegerValueField.argtypes = [c_void_p, c_uint32, c_int64]
        self._cg.CGEventPost.argtypes = [c_uint32, c_void_p]
        self._cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]
        self._cg.CGAssociateMouseAndMouseCursorPosition.argtypes = [c_bool]
        self._cg.CGMainDisplayID.restype = c_uint32
        self._cg.CGDisplayBounds.restype = CGRect
        self._cg.CGDisplayBounds.argtypes = [c_uint32]
        self._cf.CFRelease.argtypes = [c_void_p]

        # HID system state source — smoother than NULL for synthetic moves
        self._src = self._cg.CGEventSourceCreate(1)
        self._MOVED = 5
        self._LEFT_DOWN = 1
        self._LEFT_UP = 2
        self._RIGHT_DOWN = 3
        self._RIGHT_UP = 4
        self._LEFT_DRAGGED = 6
        self._RIGHT_DRAGGED = 7
        self._HID_TAP = 0
        self._PIXEL_UNITS = 0
        self._DELTA_X = 75
        self._DELTA_Y = 76

        self._bounds = self._display_bounds()
        self._x, self._y = self._read_location()
        self._left_held = False
        self._right_held = False
        self._warn_accessibility()

    def _display_bounds(self) -> tuple[float, float, float, float]:
        try:
            did = self._cg.CGMainDisplayID()
            r = self._cg.CGDisplayBounds(did)
            return (
                float(r.origin.x),
                float(r.origin.y),
                float(r.origin.x + r.size.width),
                float(r.origin.y + r.size.height),
            )
        except Exception:
            return (0.0, 0.0, 3000.0, 2000.0)

    def _warn_accessibility(self) -> None:
        as_path = ctypes.util.find_library("ApplicationServices")
        if not as_path:
            return
        try:
            app = ctypes.CDLL(as_path)
            app.AXIsProcessTrusted.restype = ctypes.c_bool
            if not app.AXIsProcessTrusted():
                print(
                    "Grant Accessibility to Terminal: "
                    "System Settings > Privacy & Security > Accessibility",
                    flush=True,
                )
        except Exception:
            pass

    def _read_location(self) -> tuple[float, float]:
        ev = self._cg.CGEventCreate(None)
        if not ev:
            return 0.0, 0.0
        pt = self._cg.CGEventGetLocation(ev)
        self._cf.CFRelease(ev)
        return float(pt.x), float(pt.y)

    def _clamp(self, x: float, y: float) -> tuple[float, float]:
        min_x, min_y, max_x, max_y = self._bounds
        return (
            min(max(x, min_x), max_x - 1.0),
            min(max(y, min_y), max_y - 1.0),
        )

    def _post_mouse(
        self, etype: int, x: float, y: float, button: int, dx: int, dy: int
    ) -> None:
        pt = CGPoint(x, y)
        ev = self._cg.CGEventCreateMouseEvent(
            self._src, c_uint32(etype), pt, c_uint32(button)
        )
        if not ev:
            return
        if dx or dy:
            self._cg.CGEventSetIntegerValueField(
                ev, c_uint32(self._DELTA_X), c_int64(dx)
            )
            self._cg.CGEventSetIntegerValueField(
                ev, c_uint32(self._DELTA_Y), c_int64(dy)
            )
        self._cg.CGEventPost(c_uint32(self._HID_TAP), ev)
        self._cf.CFRelease(ev)

    def move(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        with self._lock:
            self._x, self._y = self._clamp(self._x + dx, self._y + dy)
            x, y = self._x, self._y
            left = self._left_held
            right = self._right_held
        if left:
            etype, btn = self._LEFT_DRAGGED, 0
        elif right:
            etype, btn = self._RIGHT_DRAGGED, 1
        else:
            etype, btn = self._MOVED, 0
        self._post_mouse(etype, x, y, btn, int(round(dx)), int(round(dy)))

    def down(self, button: str = "left") -> None:
        with self._lock:
            x, y = self._x, self._y
            if button == "right":
                self._right_held = True
                etype, btn = self._RIGHT_DOWN, 1
            else:
                self._left_held = True
                etype, btn = self._LEFT_DOWN, 0
        self._post_mouse(etype, x, y, btn, 0, 0)

    def up(self, button: str = "left") -> None:
        with self._lock:
            x, y = self._x, self._y
            if button == "right":
                self._right_held = False
                etype, btn = self._RIGHT_UP, 1
            else:
                self._left_held = False
                etype, btn = self._LEFT_UP, 0
        self._post_mouse(etype, x, y, btn, 0, 0)

    def click(self, button: str = "left") -> None:
        self.down(button)
        self.up(button)

    def double_click(self) -> None:
        self.click("left")
        time.sleep(0.04)
        self.click("left")

    def scroll(self, dy: float) -> None:
        wheel = int(round(dy))
        if wheel == 0:
            return
        ev = self._cg.CGEventCreateScrollWheelEvent(
            self._src, c_uint32(self._PIXEL_UNITS), c_uint32(1), c_int32(wheel)
        )
        if not ev:
            return
        self._cg.CGEventPost(c_uint32(self._HID_TAP), ev)
        self._cf.CFRelease(ev)

    def _key(self, keycode: int, down: bool, flags: int = 0) -> None:
        ev = self._cg.CGEventCreateKeyboardEvent(
            self._src, c_uint32(keycode), c_bool(down)
        )
        if not ev:
            return
        if flags:
            self._cg.CGEventSetFlags(ev, c_uint32(flags))
        self._cg.CGEventPost(c_uint32(self._HID_TAP), ev)
        self._cf.CFRelease(ev)

    def hotkey(self, keycode: int, flags: int = FLAG_CONTROL) -> None:
        self._key(keycode, True, flags)
        self._key(keycode, False, flags)

    def space_left(self) -> None:
        self.hotkey(KEY_LEFT, FLAG_CONTROL)

    def space_right(self) -> None:
        self.hotkey(KEY_RIGHT, FLAG_CONTROL)

    def mission_control(self) -> None:
        self.hotkey(KEY_UP, FLAG_CONTROL)

    def app_windows(self) -> None:
        self.hotkey(KEY_DOWN, FLAG_CONTROL)

    def resync(self) -> None:
        with self._lock:
            self._bounds = self._display_bounds()
            self._x, self._y = self._read_location()


class MotionPump:
    """Dedicated thread applies coalesced motion at a stable high rate."""

    def __init__(self, mouse: Mouse, hz: float = 144.0) -> None:
        self.mouse = mouse
        self._hz = hz
        self._dx = 0.0
        self._dy = 0.0
        self._scroll = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run, name="motion-pump", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=1.0)

    def add_move(self, dx: float, dy: float) -> None:
        with self._lock:
            self._dx += dx
            self._dy += dy
        self._wake.set()

    def add_scroll(self, dy: float) -> None:
        with self._lock:
            self._scroll += dy
        self._wake.set()

    def flush_now(self) -> None:
        with self._lock:
            dx, dy, sc = self._dx, self._dy, self._scroll
            self._dx = self._dy = self._scroll = 0.0
        if dx or dy:
            self.mouse.move(dx, dy)
        if sc:
            self.mouse.scroll(sc)

    def run_blocking(self, fn) -> None:
        """Run click/hotkey off the asyncio loop (avoids freezing input)."""
        threading.Thread(target=fn, daemon=True).start()

    def _run(self) -> None:
        interval = 1.0 / self._hz
        next_t = time.perf_counter()
        while not self._stop.is_set():
            self._wake.wait(timeout=0.05)
            self._wake.clear()
            while not self._stop.is_set():
                with self._lock:
                    dx, dy, sc = self._dx, self._dy, self._scroll
                    if dx == 0.0 and dy == 0.0 and sc == 0.0:
                        break
                    self._dx = self._dy = self._scroll = 0.0
                if dx or dy:
                    self.mouse.move(dx, dy)
                if sc:
                    self.mouse.scroll(sc)
                next_t += interval
                delay = next_t - time.perf_counter()
                if delay > 0.0004:
                    time.sleep(delay)
                elif delay < -interval:
                    next_t = time.perf_counter()
