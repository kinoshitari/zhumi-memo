from pathlib import Path
import subprocess
import winreg


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command(executable: Path, main_script: Path = None) -> str:
    parts = [str(executable)]
    if main_script is not None:
        parts.append(str(main_script))
    return subprocess.list2cmdline(parts)


def is_autostart_enabled(value_name: str, executable: Path, main_script: Path = None) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
        return value == _command(executable, main_script)
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool, value_name: str, executable: Path, main_script: Path = None) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, _command(executable, main_script))
        else:
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass
