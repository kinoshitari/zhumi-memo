from pathlib import Path
import os
import sys


APP_ID = "ClipboardPlus"
APP_NAME = "猪咪备忘录"
MAX_HISTORY = 1000
DEFAULT_HOTKEY = "Alt+V"
DEFAULT_PANEL_TRANSPARENCY = 42
MIN_PANEL_TRANSPARENCY = 0
MAX_PANEL_TRANSPARENCY = 100
HOTKEY_ID = 0x4350
DATABASE_NAME = "clipboard.db"
STORAGE_POINTER_NAME = "storage_location.txt"


def default_data_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = str(Path.home() / "AppData" / "Local")
    return Path(local_app_data) / APP_ID


def storage_pointer_path() -> Path:
    return default_data_directory() / STORAGE_POINTER_NAME


def data_directory() -> Path:
    # The pointer stays in the original V1 directory so a custom data location
    # can be found before the database is opened.
    default = default_data_directory()
    pointer = storage_pointer_path()
    path = default
    if pointer.is_file():
        try:
            configured = Path(pointer.read_text(encoding="utf-8").strip()).expanduser()
            if configured.is_absolute():
                path = configured
        except OSError:
            path = default
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_storage_location(path: Path) -> None:
    target = Path(path).expanduser().resolve()
    default = default_data_directory().resolve()
    default.mkdir(parents=True, exist_ok=True)
    pointer = storage_pointer_path()
    if target == default:
        if pointer.exists():
            pointer.unlink()
        return
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(str(target), encoding="utf-8")
    os.replace(str(temporary), str(pointer))


def database_path() -> Path:
    return data_directory() / DATABASE_NAME


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative
