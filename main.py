import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from clipboard_plus.application import ClipboardController
from clipboard_plus.config import APP_NAME, DEFAULT_HOTKEY, HOTKEY_ID, MAX_HISTORY, database_path, resource_path
from clipboard_plus.database import HistoryDatabase
from clipboard_plus.hotkey import GlobalHotkey
from clipboard_plus.single_instance import SingleInstance
from clipboard_plus.theme import apply_app_theme


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(resource_path("assets/app_icon.png"))))
    apply_app_theme(app)

    instance = SingleInstance("Local\\ClipboardPlus.SingleInstance")
    if instance.already_running:
        QMessageBox.information(None, APP_NAME, "%s 已经在运行。" % APP_NAME)
        instance.close()
        return 0

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "当前 Windows 会话无法使用系统托盘。")
        instance.close()
        return 1

    database = HistoryDatabase(database_path(), MAX_HISTORY)
    history_limit = int(database.get_setting("history_limit", str(MAX_HISTORY)))
    image_limit = int(database.get_setting("image_limit", "200"))
    file_cache_limit = int(database.get_setting("file_cache_limit_mb", "512"))
    database.set_limit(history_limit)
    database.set_image_limit(image_limit)
    database.set_file_cache_limit_mb(file_cache_limit)
    main_script = None if getattr(sys, "frozen", False) else Path(__file__).resolve()
    controller = ClipboardController(app, database, Path(sys.executable), main_script)
    shortcut = database.get_setting("hotkey", DEFAULT_HOTKEY)
    hotkey = GlobalHotkey(app, HOTKEY_ID, shortcut)
    controller.hotkey_update_callback = hotkey.update
    if not hotkey.register():
        controller.tray.showMessage(
            APP_NAME,
            "无法注册 %s，可能已被其他程序占用。仍可通过托盘打开。" % shortcut,
            QSystemTrayIcon.Warning,
            6000,
        )
    else:
        hotkey_timer = QTimer(app)
        hotkey_timer.setInterval(40)
        hotkey_timer.timeout.connect(
            lambda: controller.show_window() if hotkey.consume_activation() else None
        )
        hotkey_timer.start()

    app.aboutToQuit.connect(hotkey.unregister)
    app.aboutToQuit.connect(instance.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
