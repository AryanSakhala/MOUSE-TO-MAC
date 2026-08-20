"""macOS pointer + keyboard injection via CoreGraphics."""

from __future__ import annotations

import ctypes
import ctypes.util
from ctypes import c_bool, c_double, c_int64, c_uint32, c_void_p


class CGPoint(ctypes.Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


# Virtual key codes (HIToolbox)
KEY_LEFT = 0x7B
KEY_RIGHT = 0x7C
KEY_DOWN = 0x7D
KEY_UP = 0x7E
FLAG_CONTROL = 0x40000  # kCGEventFlagMaskControl


class Mouse:
    def __init__(self) -> None:
        cg_path = ctypes.util.find_library("CoreGraphics")
        cf_path = ctypes.util.find_library("CoreFoundation")
        if not cg_path or not cf_path:
            raise RuntimeError("CoreGraphics not available")

        self._cg = ctypes.CDLL(cg_path)
        self._cf = ctypes.CDLL(cf_path)

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
            ctypes.c_int32,
        ]
        self._cg.CGEventCreateKeyboardEvent.restype = c_void_p
        self._cg.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint32, c_bool]
        self._cg.CGEventSetFlags.argtypes = [c_void_p, c_uint32]
        self._cg.CGEventSetIntegerValueField.argtypes = [c_void_p, c_uint32, c_int64]
        self._cg.CGEventPost.argtypes = [c_uint32, c_void_p]
        self._cf.CFRelease.argtypes = [c_void_p]

        self._MOVED = 5
        self._LEFT_DOWN = 1
        self._LEFT_UP = 2
        self._RIGHT_DOWN = 3
        self._RIGHT_UP = 4
        self._HID_TAP = 0
        self._PIXEL_UNITS = 0
        self._DELTA_X = 75
        self._DELTA_Y = 76

        self._x, self._y = self._read_location()
        self._warn_accessibility()

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

    def _post_mouse(
        self, etype: int, x: float, y: float, button: int, dx: int, dy: int
    ) -> None:
        pt = CGPoint(x, y)
        ev = self._cg.CGEventCreateMouseEvent(
            None, c_uint32(etype), pt, c_uint32(button)
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
        self._x += dx
        self._y += dy
        self._post_mouse(
            self._MOVED, self._x, self._y, 0, int(round(dx)), int(round(dy))
        )

    def click(self, button: str = "left") -> None:
        if button == "right":
            down, up, btn = self._RIGHT_DOWN, self._RIGHT_UP, 1
        else:
            down, up, btn = self._LEFT_DOWN, self._LEFT_UP, 0
        self._post_mouse(down, self._x, self._y, btn, 0, 0)
        self._post_mouse(up, self._x, self._y, btn, 0, 0)

    def double_click(self) -> None:
        self.click("left")
        self.click("left")

    def scroll(self, dy: float) -> None:
        wheel = int(round(dy))
        if wheel == 0:
            return
        ev = self._cg.CGEventCreateScrollWheelEvent(
            None, c_uint32(self._PIXEL_UNITS), c_uint32(1), ctypes.c_int32(wheel)
        )
        if not ev:
            return
        self._cg.CGEventPost(c_uint32(self._HID_TAP), ev)
        self._cf.CFRelease(ev)

    def _key(self, keycode: int, down: bool, flags: int = 0) -> None:
        ev = self._cg.CGEventCreateKeyboardEvent(None, c_uint32(keycode), c_bool(down))
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
        """Slide to previous desktop / Space."""
        self.hotkey(KEY_LEFT, FLAG_CONTROL)

    def space_right(self) -> None:
        """Slide to next desktop / Space."""
        self.hotkey(KEY_RIGHT, FLAG_CONTROL)

    def mission_control(self) -> None:
        self.hotkey(KEY_UP, FLAG_CONTROL)

    def app_windows(self) -> None:
        self.hotkey(KEY_DOWN, FLAG_CONTROL)

    def resync(self) -> None:
        self._x, self._y = self._read_location()
