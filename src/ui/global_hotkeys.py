import sys
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QCoreApplication


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey):
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, eventType, message):
        if eventType not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False, 0

        try:
            addr = int(message)
            msg = wintypes.MSG.from_address(addr)
        except Exception:
            return False, 0

        if msg.message != WM_HOTKEY:
            return False, 0

        try:
            hotkey_id = int(msg.wParam)
        except Exception:
            hotkey_id = 0

        try:
            self._on_hotkey(hotkey_id)
        except Exception:
            # Never crash the app from the event filter
            pass

        return True, 0


class GlobalHotkeyManager(QObject):
    """Registers global (system-wide) hotkeys on Windows.

    Works even if the overlay window is click-through / unfocused.
    """

    activated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered: set[int] = set()
        self._filter = _HotkeyFilter(self._emit)

        if sys.platform.startswith("win"):
            app = QCoreApplication.instance()
            if app is not None:
                app.installNativeEventFilter(self._filter)

    def _emit(self, hotkey_id: int):
        self.activated.emit(int(hotkey_id))

    def register(self, hotkey_id: int, *, modifiers: int, vk: int) -> bool:
        if not sys.platform.startswith("win"):
            return False

        user32 = ctypes.windll.user32
        ok = bool(user32.RegisterHotKey(None, int(hotkey_id), int(modifiers), int(vk)))
        if ok:
            self._registered.add(int(hotkey_id))
        return ok

    def unregister_all(self) -> None:
        if not sys.platform.startswith("win"):
            return

        user32 = ctypes.windll.user32
        for hotkey_id in list(self._registered):
            try:
                user32.UnregisterHotKey(None, int(hotkey_id))
            except Exception:
                pass
        self._registered.clear()

    def __del__(self):
        try:
            self.unregister_all()
        except Exception:
            pass
