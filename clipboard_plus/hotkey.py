import ctypes
from ctypes import wintypes
import threading

from PySide6.QtCore import QObject, Signal


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


def parse_hotkey(shortcut: str):
    parts = [part.strip().upper() for part in shortcut.split("+") if part.strip()]
    modifiers, key = MOD_NOREPEAT, None
    for part in parts:
        if part in ("CTRL", "CONTROL"):
            modifiers |= MOD_CONTROL
        elif part == "ALT":
            modifiers |= MOD_ALT
        elif part == "SHIFT":
            modifiers |= MOD_SHIFT
        elif part in ("WIN", "META"):
            modifiers |= MOD_WIN
        elif len(part) == 1 and part.isalnum():
            key = ord(part)
        elif part.startswith("F") and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            key = 0x70 + int(part[1:]) - 1
        else:
            raise ValueError("不支持的快捷键：%s" % part)
    if key is None or modifiers == MOD_NOREPEAT:
        raise ValueError("快捷键必须包含修饰键和一个字母、数字或 F1-F24")
    return modifiers, key


class HotkeySignals(QObject):
    activated = Signal()


class GlobalHotkey:
    """RegisterHotKey worker with its own Win32 message loop.

    A dedicated message thread is more reliable than a Qt native event filter in
    frozen applications while still delivering activation through a queued Qt signal.
    """

    def __init__(self, application, hotkey_id: int, shortcut: str) -> None:
        self.application = application
        self.hotkey_id = hotkey_id
        self.shortcut = shortcut
        self.signals = HotkeySignals()
        self._thread = None
        self._thread_id = 0
        self._ready = None
        self._register_ok = False
        self._activation_pending = threading.Event()

    @property
    def activated(self):
        return self.signals.activated

    def register(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        modifiers, key = parse_hotkey(self.shortcut)
        self._ready = threading.Event()
        self._register_ok = False
        self._thread = threading.Thread(
            target=self._message_loop, args=(modifiers, key),
            name="ZhumiMemoHotkey", daemon=True,
        )
        self._thread.start()
        self._ready.wait(2.0)
        return self._register_ok

    def _message_loop(self, modifiers: int, key: int) -> None:
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._register_ok = bool(user32.RegisterHotKey(None, self.hotkey_id, modifiers, key))
        self._ready.set()
        if not self._register_ok:
            return
        message = MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and int(message.wParam) == self.hotkey_id:
                    self._activation_pending.set()
                    self.signals.activated.emit()
        finally:
            user32.UnregisterHotKey(None, self.hotkey_id)
            self._thread_id = 0

    def unregister(self) -> None:
        thread = self._thread
        if thread and thread.is_alive() and self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            thread.join(2.0)
        self._thread = None
        self._thread_id = 0
        self._register_ok = False

    def consume_activation(self) -> bool:
        if not self._activation_pending.is_set():
            return False
        self._activation_pending.clear()
        return True

    def update(self, shortcut: str) -> bool:
        parse_hotkey(shortcut)
        old = self.shortcut
        self.unregister()
        self.shortcut = shortcut
        if self.register():
            return True
        self.shortcut = old
        self.register()
        return False
