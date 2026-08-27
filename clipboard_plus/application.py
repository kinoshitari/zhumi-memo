import os
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QMimeData, QObject, QThreadPool, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from .classification import CATEGORIES
from .config import (
    APP_ID, APP_NAME, DEFAULT_HOTKEY, MAX_HISTORY, resource_path,
    set_storage_location,
)
from .database import HistoryDatabase
from .file_types import (
    DEFAULT_FILE_CACHE_EXTENSIONS, file_matches_cache_extensions,
    is_common_image_file,
)
from .image_preview import ImagePreviewDialog
from .settings_dialog import SettingsDialog
from .source_app import clipboard_source_app
from .system_integration import is_autostart_enabled, set_autostart
from .window import ClipboardWindow
from .workers import FileCopyTask, FileExportTask, ImageLoadTask


DEFAULT_IMAGE_LIMIT = 200
DEFAULT_FILE_CACHE_LIMIT_MB = 512
RESERVED_CATEGORIES = set(("全部", "全部图片", "全部文件", "固定", "收藏", "图片", "文件") + CATEGORIES)


def _image_png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


class ClipboardController(QObject):
    def __init__(self, app: QApplication, database: HistoryDatabase, pythonw_path: Path = None, main_script: Path = None) -> None:
        super().__init__()
        self.app = app
        self.database = database
        self.pythonw_path = Path(pythonw_path) if pythonw_path else None
        self.main_script = Path(main_script) if main_script else None
        self.hotkey_update_callback = None
        self.clipboard = app.clipboard()
        self.window = ClipboardWindow()
        self.thread_pool = QThreadPool.globalInstance()
        self._background_tasks = set()
        self._preview_dialogs = set()
        self.paused = False
        self._ignore_clipboard_events = 0
        self._build_tray()
        self._connect_signals()
        self.refresh_categories()
        self.refresh()

    def _build_tray(self) -> None:
        icon = QIcon(str(resource_path("assets/app_icon.png")))
        if icon.isNull():
            icon = self.app.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        self.app.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self.app)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        open_action = QAction("打开", menu)
        self.pause_action = QAction("暂停剪贴板记录", menu)
        self.pause_action.setCheckable(True)
        settings_action = QAction("设置", menu)
        clear_action = QAction("清空全部历史", menu)
        exit_action = QAction("退出", menu)
        open_action.triggered.connect(self.show_window)
        self.pause_action.toggled.connect(self.set_paused)
        settings_action.triggered.connect(self.show_settings)
        clear_action.triggered.connect(self.clear_history)
        exit_action.triggered.connect(self.quit)
        for action in (open_action, self.pause_action, settings_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(clear_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _connect_signals(self) -> None:
        self.clipboard.dataChanged.connect(self._clipboard_changed)
        self.window.search_changed.connect(self.refresh)
        self.window.category_changed.connect(self.refresh)
        self.window.mode_changed.connect(self.refresh)
        self.window.record_activated.connect(self.copy_and_hide)
        self.window.record_preview_requested.connect(self.preview_record)
        self.window.date_changed.connect(self.refresh)
        self.window.action_requested.connect(self.handle_action)
        self.window.settings_requested.connect(self.show_settings)
        self.window.create_category_requested.connect(self.create_category)
        self.window.rename_category_requested.connect(self.rename_category)
        self.window.delete_category_requested.connect(self.delete_category)
        self.window.editor_copy_text_requested.connect(self._set_text_clipboard)
        self.window.editor_copy_image_requested.connect(self._set_editor_image_clipboard)
        self.window.editor_copy_all_requested.connect(self._set_editor_clipboard)

    def _clipboard_changed(self) -> None:
        if self._ignore_clipboard_events:
            self._ignore_clipboard_events -= 1
            return
        if self.paused:
            return
        mime = self.clipboard.mimeData()
        if not mime:
            return
        source = clipboard_source_app()
        if source.lower() in ("python", "pythonw"):
            source = ""
        local_files = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()] if mime.hasUrls() else []
        local_files = [path for path in local_files if path.is_file()]
        if local_files:
            self._record_local_files(local_files, source)
        elif mime.hasImage():
            image = QImage(mime.imageData())
            if image.isNull():
                return
            image_data = _image_png(image)
            thumbnail_image = image.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.database.add_or_touch_image(image_data, _image_png(thumbnail_image), source)
        elif mime.hasText():
            content = mime.text()
            if not content or "\x00" in content:
                return
            self.database.add_or_touch(content, source_app=source)
        else:
            return
        self.refresh()

    def _record_local_files(self, paths, source_app: str) -> None:
        cache_extensions = self.database.get_setting(
            "file_cache_extensions", DEFAULT_FILE_CACHE_EXTENSIONS
        )
        files_to_cache = []
        for path in paths:
            if is_common_image_file(path):
                if not self._record_image_file(path, source_app):
                    self.tray.showMessage(
                        APP_NAME, "图片无法读取，未加入历史：%s" % path.name,
                        QSystemTrayIcon.Warning, 4000,
                    )
                continue
            if file_matches_cache_extensions(path, cache_extensions):
                files_to_cache.append(path)
        if files_to_cache:
            self._queue_file_cache(files_to_cache, source_app)

    def _record_image_file(self, path: Path, source_app: str) -> bool:
        image = QImage(str(path))
        if image.isNull():
            return False
        image_data = _image_png(image)
        if not image_data:
            return False
        thumbnail_image = image.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.database.add_or_touch_image(image_data, _image_png(thumbnail_image), source_app)
        return True

    def _queue_file_cache(self, paths, source_app: str) -> None:
        for path in paths:
            try:
                record_id, destination, should_copy = self.database.prepare_file_cache(path, source_app)
            except (OSError, ValueError) as exc:
                self.tray.showMessage(APP_NAME, "文件记录失败：%s" % exc, QSystemTrayIcon.Warning, 4000)
                continue
            if not should_copy or destination is None:
                continue
            task = FileCopyTask(record_id, path, destination)
            self._background_tasks.add(task)
            task.signals.completed.connect(self._file_cache_completed)
            task.signals.failed.connect(self._file_cache_failed)
            task.signals.completed.connect(lambda *_, task=task: self._background_tasks.discard(task))
            task.signals.failed.connect(lambda *_, task=task: self._background_tasks.discard(task))
            self.thread_pool.start(task)

    def _file_cache_completed(self, record_id: int, destination: str, byte_size: int) -> None:
        try:
            retained = self.database.complete_file_cache(record_id, Path(destination), byte_size)
            if not retained:
                Path(destination).unlink()
        except (OSError, sqlite3.Error):
            try:
                Path(destination).unlink()
            except OSError:
                pass
        self.refresh()

    def _file_cache_failed(self, record_id: int, destination: str, error: str) -> None:
        self.database.fail_file_cache(record_id, error)
        try:
            Path(destination).unlink()
        except OSError:
            pass
        self.refresh()

    def refresh_categories(self) -> None:
        self.window.set_custom_categories(self.database.list_custom_categories())

    def refresh(self, *_args) -> None:
        mode = self.window.current_mode()
        if mode == "editor":
            return
        date_start, date_end = self.window.date_range()
        if mode == "image":
            records = self.database.list_images(
                self.window.search.text(), self.window.current_category(), date_start, date_end
            )
        elif mode == "file":
            records = self.database.list_files(
                self.window.search.text(), self.window.current_category(), date_start, date_end
            )
        else:
            records = self.database.list_history(
                self.window.search.text(), self.window.current_category(), date_start, date_end
            )
        self.window.set_records(records, mode)

    def show_window(self) -> None:
        self.refresh()
        self.window.show_and_activate()

    def _ignore_next_clipboard_change(self) -> None:
        self._ignore_clipboard_events += 1
        QTimer.singleShot(100, self._clear_stale_ignore)

    def _set_text_clipboard(self, content: str) -> None:
        self._ignore_next_clipboard_change()
        self.clipboard.setText(content)

    def _set_image_clipboard(self, image_data: bytes) -> None:
        image = QImage()
        if image.loadFromData(image_data):
            self._ignore_next_clipboard_change()
            self.clipboard.setImage(image)

    def _set_image_with_note_clipboard(self, image_data: bytes, note: str) -> bool:
        image = QImage()
        if not note or not image.loadFromData(image_data):
            return False
        mime = QMimeData()
        mime.setText(note)
        mime.setImageData(image)
        self._ignore_next_clipboard_change()
        self.clipboard.setMimeData(mime)
        return True

    def _set_editor_image_clipboard(self, image: QImage) -> None:
        if image is None or image.isNull():
            return
        self._ignore_next_clipboard_change()
        self.clipboard.setImage(QImage(image))

    def _set_editor_clipboard(self, text: str, image: QImage) -> None:
        has_image = image is not None and not image.isNull()
        if not text and not has_image:
            return
        mime = QMimeData()
        if text:
            mime.setText(text)
        if has_image:
            mime.setImageData(QImage(image))
        self._ignore_next_clipboard_change()
        self.clipboard.setMimeData(mime)

    def _set_file_clipboard(self, path: Path) -> None:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        self._ignore_next_clipboard_change()
        self.clipboard.setMimeData(mime)

    def copy_and_hide(self, record_id: int, kind: str) -> None:
        if kind == "file":
            path = self.database.get_file_path(record_id)
            if path is None:
                QMessageBox.warning(self.window, APP_NAME, "文件缓存和原始文件均不存在。")
                return
            self._set_file_clipboard(path)
            self.database.touch_file(record_id)
        elif kind == "image":
            data = self.database.get_image(record_id)
            if data is None:
                return
            self._set_image_clipboard(data)
            self.database.add_or_touch_image(data, self._thumbnail_from_data(data))
        else:
            content = self.database.get_content(record_id)
            if content is None:
                return
            self._set_text_clipboard(content)
            self.database.add_or_touch(content)
        self.window.hide()
        self.refresh()

    def preview_record(self, record_id: int, kind: str) -> None:
        if kind == "text":
            content = self.database.get_content(record_id)
            if content is not None:
                self.window.show_full_content(content)
        elif kind == "image":
            self._show_image_preview(record_id)
        else:
            self._open_cached_file(record_id, False)

    def _show_image_preview(self, record_id: int) -> None:
        dialog = ImagePreviewDialog(self.window)
        self._preview_dialogs.add(dialog)
        dialog.destroyed.connect(lambda *_: self._preview_dialogs.discard(dialog))
        task = ImageLoadTask(
            self.database.path, record_id, self.database.get_image_cache_path(record_id)
        )
        self._background_tasks.add(task)
        task.signals.loaded.connect(dialog.set_image)
        task.signals.failed.connect(dialog.set_error)
        task.signals.loaded.connect(lambda *_: self._background_tasks.discard(task))
        task.signals.failed.connect(lambda *_: self._background_tasks.discard(task))
        dialog.show()
        dialog.raise_()
        self.thread_pool.start(task)

    @staticmethod
    def _thumbnail_from_data(data: bytes) -> bytes:
        image = QImage()
        if not image.loadFromData(data):
            return b""
        return _image_png(image.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _clear_stale_ignore(self) -> None:
        self._ignore_clipboard_events = 0

    def handle_action(self, action: str, record_id: int, kind: str) -> None:
        if action == "copy_hide":
            self.copy_and_hide(record_id, kind)
            return
        content = self.database.get_content(record_id) if kind == "text" else None
        image_data = self.database.get_image(record_id) if kind == "image" else None
        file_path = self.database.get_file_path(record_id) if kind == "file" else None
        if (kind == "text" and content is None) or (kind == "image" and image_data is None):
            return
        if action == "copy":
            if kind == "file":
                if file_path is None:
                    QMessageBox.warning(self.window, APP_NAME, "文件缓存和原始文件均不存在。")
                    return
                self._set_file_clipboard(file_path)
                self.database.touch_file(record_id)
            elif kind == "image":
                self._set_image_clipboard(image_data)
                self.database.add_or_touch_image(image_data, self._thumbnail_from_data(image_data))
            else:
                self._set_text_clipboard(content)
                self.database.add_or_touch(content)
            self.refresh()
        elif action == "copy_note":
            note = self.database.get_note(record_id, kind) or ""
            if note:
                self._set_text_clipboard(note)
        elif action == "copy_note_with_content":
            note = self.database.get_note(record_id, kind) or ""
            if not note:
                return
            if kind == "text":
                self._set_text_clipboard(f"{content}\n\n备注：{note}")
            elif kind == "image":
                self._set_image_with_note_clipboard(image_data, note)
        elif action == "delete":
            self.database.delete(record_id, kind)
            self.refresh()
        elif action == "favorite":
            self.database.toggle_favorite(record_id, kind)
            self.refresh()
        elif action == "pin":
            self.database.toggle_pinned(record_id, kind)
            self.refresh()
        elif action == "note":
            self._edit_note(record_id, kind)
        elif action == "clear_note":
            self.database.set_note(record_id, "", kind)
            self.refresh()
        elif action.startswith("move:"):
            self.database.move_to_category(record_id, action.split(":", 1)[1], kind)
            self.refresh()
        elif action == "view":
            self.window.show_full_content(content)
        elif action == "view_image":
            self._show_image_preview(record_id)
        elif action == "open_file":
            self._open_cached_file(record_id, False)
        elif action == "save_file_as":
            self._save_file_as(record_id)
        elif action == "open_item_location":
            self._open_item_location(record_id, kind)
        elif action == "open_url":
            QDesktopServices.openUrl(QUrl(content.strip()))
        elif action == "copy_domain":
            domain = urlparse(content.strip()).netloc
            if domain:
                self._set_text_clipboard(domain)
        elif action in ("open_path", "open_parent"):
            self._open_path(content, action == "open_parent")

    def _edit_note(self, record_id: int, kind: str) -> None:
        current = self.database.get_note(record_id, kind)
        if current is None:
            return
        note, ok = QInputDialog.getMultiLineText(
            self.window,
            "编辑备注",
            "备注内容（保存非空备注后自动收藏）：",
            current,
        )
        if not ok:
            return
        self.database.set_note(record_id, note, kind)
        self.refresh()

    def _open_path(self, content: str, parent: bool) -> None:
        path = Path(os.path.expandvars(content.strip().strip('"\'')))
        target = (path if path.is_dir() else path.parent) if parent else path
        if not target.exists():
            QMessageBox.warning(self.window, APP_NAME, "路径不存在：\n%s" % target)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _open_cached_file(self, record_id: int, parent: bool) -> None:
        path = self.database.get_file_path(record_id)
        if path is None:
            QMessageBox.warning(self.window, APP_NAME, "文件缓存和原始文件均不存在。")
            return
        target = path.parent if parent else path
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            QMessageBox.warning(self.window, APP_NAME, "无法打开：\n%s" % target)

    def _open_item_location(self, record_id: int, kind: str) -> None:
        if kind == "file":
            path = self.database.get_file_path(record_id)
            if path is None:
                QMessageBox.warning(self.window, APP_NAME, "文件缓存和原始文件均不存在。")
                return
            target = path.parent
        elif kind == "image":
            cache_path = self.database.get_image_cache_path(record_id)
            target = cache_path.parent if cache_path else self.database.image_cache_dir
        else:
            target = self.database.path.parent
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            QMessageBox.warning(self.window, APP_NAME, "无法打开：\n%s" % target)

    def _save_file_as(self, record_id: int) -> None:
        source = self.database.get_file_path(record_id)
        if source is None:
            QMessageBox.warning(self.window, APP_NAME, "文件缓存和原始文件均不存在。")
            return
        selected, _filter = QFileDialog.getSaveFileName(
            self.window, "另存文件", source.name
        )
        if not selected:
            return
        destination = Path(selected)
        if destination.resolve() == source.resolve():
            return
        task = FileExportTask(source, destination)
        self._background_tasks.add(task)
        task.signals.completed.connect(
            lambda path: self.tray.showMessage(APP_NAME, "文件已保存：%s" % path, QSystemTrayIcon.Information, 4000)
        )
        task.signals.failed.connect(
            lambda error: QMessageBox.warning(self.window, "文件保存失败", error)
        )
        task.signals.completed.connect(lambda *_, task=task: self._background_tasks.discard(task))
        task.signals.failed.connect(lambda *_, task=task: self._background_tasks.discard(task))
        self.thread_pool.start(task)

    def create_category(self) -> None:
        name, ok = QInputDialog.getText(self.window, "新建分类", "分类名称：")
        if not ok:
            return
        self._save_new_category(name)

    def _save_new_category(self, name: str) -> bool:
        if name.strip() in RESERVED_CATEGORIES:
            QMessageBox.warning(self.window, APP_NAME, "该名称属于系统分类，不能重复使用。")
            return False
        try:
            self.database.add_custom_category(name)
        except (ValueError, sqlite3.IntegrityError) as exc:
            QMessageBox.warning(self.window, APP_NAME, "无法创建分类：%s" % exc)
            return False
        self.refresh_categories()
        self.refresh()
        return True

    def rename_category(self, old: str) -> None:
        name, ok = QInputDialog.getText(self.window, "重命名分类", "新名称：", text=old)
        if not ok or name.strip() == old:
            return
        if name.strip() in RESERVED_CATEGORIES:
            QMessageBox.warning(self.window, APP_NAME, "该名称属于系统分类，不能重复使用。")
            return
        try:
            self.database.rename_custom_category(old, name)
        except (ValueError, sqlite3.IntegrityError) as exc:
            QMessageBox.warning(self.window, APP_NAME, "无法重命名分类：%s" % exc)
            return
        self.refresh_categories()
        self.refresh()

    def delete_category(self, name: str) -> None:
        answer = QMessageBox.question(
            self.window, APP_NAME, "删除分类“%s”？其中内容会移回系统分类。" % name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.database.delete_custom_category(name)
            self.refresh_categories()
            self.refresh()

    def set_paused(self, paused: bool) -> None:
        self.paused = bool(paused)
        self.pause_action.setText("恢复剪贴板记录" if paused else "暂停剪贴板记录")
        self.tray.setToolTip(APP_NAME + ("（已暂停）" if paused else ""))
        if paused:
            self.tray.showMessage(APP_NAME, "文本、图片和文件记录均已暂停。", QSystemTrayIcon.Information, 2500)

    def show_settings(self) -> None:
        hotkey = self.database.get_setting("hotkey", DEFAULT_HOTKEY)
        history_limit = int(self.database.get_setting("history_limit", str(MAX_HISTORY)))
        image_limit = int(self.database.get_setting("image_limit", str(DEFAULT_IMAGE_LIMIT)))
        file_cache_limit = int(self.database.get_setting(
            "file_cache_limit_mb", str(DEFAULT_FILE_CACHE_LIMIT_MB)
        ))
        file_cache_extensions = self.database.get_setting(
            "file_cache_extensions", DEFAULT_FILE_CACHE_EXTENSIONS
        )
        autostart = bool(self.pythonw_path and is_autostart_enabled(APP_ID, self.pythonw_path, self.main_script))
        dialog = SettingsDialog(
            hotkey, history_limit, image_limit, file_cache_limit, file_cache_extensions,
            str(self.database.path.parent), self.database.storage_usage(),
            autostart, self.window,
        )
        dialog.apply_requested.connect(lambda values: self._apply_settings(dialog, values))
        dialog.exec()

    def _apply_settings(self, dialog: SettingsDialog, values: dict) -> None:
        shortcut = values["hotkey"]
        old_shortcut = self.database.get_setting("hotkey", DEFAULT_HOTKEY)
        if shortcut != old_shortcut and self.hotkey_update_callback and not self.hotkey_update_callback(shortcut):
            QMessageBox.warning(dialog, "快捷键不可用", "%s 已被其他程序占用，请换一个快捷键。" % shortcut)
            return
        try:
            if self.pythonw_path:
                set_autostart(values["autostart"], APP_ID, self.pythonw_path, self.main_script)
        except OSError as exc:
            if shortcut != old_shortcut and self.hotkey_update_callback:
                self.hotkey_update_callback(old_shortcut)
            QMessageBox.warning(dialog, "开机启动设置失败", str(exc))
            return
        requested_storage = Path(values["storage_path"]).expanduser()
        if requested_storage.resolve() != self.database.path.parent.resolve():
            if self.thread_pool.activeThreadCount():
                QMessageBox.warning(dialog, "暂时无法迁移", "仍有文件或图片正在后台处理，请稍后再修改存储位置。")
                return
            try:
                old_root = self.database.relocate(requested_storage)
                set_storage_location(self.database.path.parent)
            except (OSError, ValueError, sqlite3.Error) as exc:
                QMessageBox.warning(dialog, "数据迁移失败", str(exc))
                return
            QMessageBox.information(
                dialog, APP_NAME,
                "数据已安全迁移。为防止意外，旧目录仍作为备份保留：\n%s" % old_root,
            )
        for key in (
            "hotkey", "history_limit", "image_limit", "file_cache_limit_mb",
            "file_cache_extensions",
        ):
            self.database.set_setting(key, str(values[key]))
        self.database.set_limit(values["history_limit"])
        self.database.set_image_limit(values["image_limit"])
        self.database.set_file_cache_limit_mb(values["file_cache_limit_mb"])
        self.refresh()
        dialog.accept()

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self.window, APP_NAME, "确定要清空全部文本、图片和文件历史（包括收藏和固定）吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.database.clear()
            self.refresh()

    def _tray_activated(self, reason) -> None:
        if reason != QSystemTrayIcon.Trigger:
            return
        if self.window.is_foreground():
            self.window.hide()
            return
        self.show_window()

    def quit(self) -> None:
        self.tray.hide()
        try:
            self.clipboard.dataChanged.disconnect(self._clipboard_changed)
        except RuntimeError:
            pass
        self.database.close()
        self.app.quit()
