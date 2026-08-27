import ctypes
from ctypes import wintypes
from pathlib import Path


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _process_name_from_window(hwnd: int) -> str:
    if not hwnd:
        return ""
    process_id = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    if not process_id.value:
        return ""
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value
    )
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return Path(buffer.value).stem
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
    return ""


def clipboard_source_app() -> str:
    """Return the best available source process name; Windows may expose none."""
    owner = ctypes.windll.user32.GetClipboardOwner()
    name = _process_name_from_window(owner)
    if name:
        return name
    return _process_name_from_window(ctypes.windll.user32.GetForegroundWindow())

