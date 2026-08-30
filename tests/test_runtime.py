from pathlib import Path
import os
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QKeyEvent
from PySide6.QtWidgets import QApplication, QGraphicsView, QSystemTrayIcon

from clipboard_plus.application import ClipboardController
from clipboard_plus.database import HistoryDatabase
from clipboard_plus.image_preview import ImagePreviewDialog
from clipboard_plus.settings_dialog import SettingsDialog


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = HistoryDatabase(Path(self.temp.name) / "runtime.db")
        self.controller = ClipboardController(self.app, self.database)

    def tearDown(self):
        try:
            self.controller.clipboard.dataChanged.disconnect(self.controller._clipboard_changed)
        except RuntimeError:
            pass
        self.controller.tray.hide()
        self.controller.window.close()
        self.database.close()
        self.temp.cleanup()

    def test_clipboard_event_search_and_self_copy_suppression(self):
        self.controller.clipboard.setText("alpha clipboard test")
        self.app.processEvents()
        self.assertEqual(self.database.count(), 1)

        self.controller.clipboard.setText("beta clipboard test")
        self.app.processEvents()
        self.assertEqual(self.database.count(), 2)

        self.controller.window.search.setText("alpha")
        self.controller.refresh()
        self.assertEqual(self.controller.window.list_widget.count(), 1)
        item = self.controller.window.list_widget.item(0)
        self.controller.copy_and_hide(item.data(Qt.UserRole), "text")
        self.app.processEvents()
        self.assertEqual(self.database.count(), 2)
        self.assertEqual(self.database.list_history()[0].content, "alpha clipboard test")

    def test_editor_mode_copies_text_and_image_without_recording_itself(self):
        self.controller.window.set_mode("editor")
        editor = self.controller.window.editor
        editor.text_editor.setPlainText("编辑台混合内容")
        image = QImage(36, 24, QImage.Format_ARGB32)
        image.fill(QColor("cyan"))
        editor.set_image(image)

        editor.copy_all_button.click()
        self.app.processEvents()

        mime = self.controller.clipboard.mimeData()
        self.assertTrue(mime.hasText())
        self.assertEqual(mime.text(), "编辑台混合内容")
        self.assertTrue(mime.hasImage())
        self.assertEqual(self.database.count("text"), 0)
        self.assertEqual(self.database.count("image"), 0)

    def test_editor_mode_hides_history_controls_and_clear_is_one_click(self):
        self.controller.window.set_mode("editor")
        editor = self.controller.window.editor
        self.assertFalse(self.controller.window.history_panel.isVisible())
        editor.text_editor.setPlainText("temporary")
        image = QImage(18, 12, QImage.Format_ARGB32)
        image.fill(QColor("pink"))
        editor.set_image(image)
        editor.clear_button.click()
        self.assertEqual(editor.text(), "")
        self.assertFalse(editor.has_image())

        self.controller.window.set_mode("text")
        self.assertFalse(editor.isVisible())

    def test_pause_blocks_new_clipboard_records(self):
        self.controller.set_paused(True)
        before = self.database.count()
        self.controller.clipboard.setText("must not be recorded while paused")
        self.app.processEvents()
        self.assertEqual(self.database.count(), before)

    def test_url_domain_context_action(self):
        record_id = self.database.add_or_touch("https://sub.example.com/path")
        self.controller.handle_action("copy_domain", record_id, "text")
        self.app.processEvents()
        self.assertEqual(self.controller.clipboard.text(), "sub.example.com")

    def test_image_clipboard_is_recorded_and_copied_independently(self):
        image = QImage(40, 30, QImage.Format_ARGB32)
        image.fill(QColor("red"))
        self.controller.clipboard.setImage(image)
        self.app.processEvents()
        self.assertEqual(self.database.count("image"), 1)
        self.assertEqual(self.database.count("text"), 0)
        self.controller.window.set_mode("image")
        self.controller.refresh()
        self.assertEqual(self.controller.window.current_mode(), "image")
        self.assertEqual(self.controller.window.list_widget.count(), 1)
        image_id = self.database.list_images()[0].id
        self.controller.copy_and_hide(image_id, "image")
        self.app.processEvents()
        self.assertFalse(self.controller.clipboard.image().isNull())

    def test_file_clipboard_is_cached_asynchronously_and_keeps_filename(self):
        source = Path(self.temp.name) / "large-document.txt"
        source.write_bytes(b"x" * (2 * 1024 * 1024))
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        started = time.perf_counter()
        self.controller.clipboard.setMimeData(mime)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.5)
        deadline = time.time() + 8
        while time.time() < deadline:
            self.app.processEvents()
            rows = self.database.list_files()
            if rows and rows[0].status == "ready":
                break
            time.sleep(0.02)
        rows = self.database.list_files()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "ready")
        cached = self.database.get_file_path(rows[0].id)
        self.assertEqual(cached.name, source.name)
        self.assertEqual(cached.read_bytes(), source.read_bytes())

    def test_image_file_clipboard_is_stored_as_an_image(self):
        source = Path(self.temp.name) / "cached-photo.JPG"
        image = QImage(40, 30, QImage.Format_ARGB32)
        image.fill(QColor("green"))
        self.assertTrue(image.save(str(source), "JPG"))
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        self.controller.clipboard.setMimeData(mime)
        self.app.processEvents()
        self.assertEqual(self.database.count("image"), 1)
        self.assertEqual(self.database.count("file"), 0)

    def test_open_item_location_uses_the_correct_folder_for_each_record_type(self):
        text_id = self.database.add_or_touch("stored text")
        image_id = self.database.add_or_touch_image(b"stored-image", b"thumbnail")
        source = Path(self.temp.name) / "stored-file.txt"
        source.write_text("payload", encoding="utf-8")
        file_id, destination, _should_copy = self.database.prepare_file_cache(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        self.database.complete_file_cache(file_id, destination, source.stat().st_size)

        with patch("clipboard_plus.application.QDesktopServices.openUrl", return_value=True) as open_url:
            self.controller.handle_action("open_item_location", text_id, "text")
            self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()), self.database.path.parent)
            self.controller.handle_action("open_item_location", image_id, "image")
            self.assertEqual(
                Path(open_url.call_args.args[0].toLocalFile()),
                self.database.get_image_cache_path(image_id).parent,
            )
            self.controller.handle_action("open_item_location", file_id, "file")
            self.assertEqual(Path(open_url.call_args.args[0].toLocalFile()), destination.parent)

    def test_double_click_requests_preview_instead_of_copy_hide(self):
        record_id = self.database.add_or_touch("preview text")
        self.controller.refresh()
        received = []
        self.controller.window.record_preview_requested.disconnect(self.controller.preview_record)
        self.controller.window.record_preview_requested.connect(
            lambda item_id, kind: received.append((item_id, kind))
        )
        self.controller.window._preview_item(self.controller.window.list_widget.item(0))
        self.assertEqual(received, [(record_id, "text")])

    def test_image_preview_supports_zoom_pan_fit_and_actual_size(self):
        dialog = ImagePreviewDialog(self.controller.window)
        image = QImage(1200, 800, QImage.Format_ARGB32)
        image.fill(QColor("blue"))
        dialog.set_image(image)
        self.assertEqual(dialog.view.dragMode(), QGraphicsView.DragMode.ScrollHandDrag)
        dialog.view.actual_size()
        self.assertAlmostEqual(dialog.view.transform().m11(), 1.0)
        dialog.view.scale(2.0, 2.0)
        self.assertGreater(dialog.view.transform().m11(), 1.0)
        dialog.view.fit_image()
        dialog.close()

    def test_full_image_load_is_dispatched_to_background_worker(self):
        image = QImage(1800, 1200, QImage.Format_ARGB32)
        image.fill(QColor("green"))
        from clipboard_plus.application import _image_png
        image_data = _image_png(image)
        record_id = self.database.add_or_touch_image(image_data, _image_png(image.scaled(120, 80)))
        started = time.perf_counter()
        self.controller._show_image_preview(record_id)
        self.assertLess(time.perf_counter() - started, 0.5)
        dialog = next(iter(self.controller._preview_dialogs))
        deadline = time.time() + 8
        while time.time() < deadline and dialog.view.scene() is None:
            self.app.processEvents()
            time.sleep(0.02)
        self.assertIsNotNone(dialog.view.scene())
        dialog.close()

    def test_window_pin_can_be_toggled(self):
        self.assertFalse(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
        self.assertEqual(self.controller.window.pin_window.text(), "普通窗口")
        self.assertFalse(self.controller.window.pin_window.isChecked())
        self.controller.window.pin_window.setChecked(True)
        self.assertTrue(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
        self.assertEqual(self.controller.window.pin_window.text(), "固定窗口")
        self.assertEqual(self.database.get_setting("always_on_top", ""), "true")
        self.controller.window.pin_window.setChecked(False)
        self.assertFalse(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
        self.assertEqual(self.controller.window.pin_window.text(), "普通窗口")
        self.assertEqual(self.database.get_setting("always_on_top", ""), "false")

    def test_tray_click_hides_only_when_window_is_foreground(self):
        self.controller.window.show()
        with patch.object(self.controller.window, "is_foreground", return_value=True), \
                patch.object(self.controller.window, "hide") as hide, \
                patch.object(self.controller, "show_window") as show_window:
            self.controller._tray_activated(QSystemTrayIcon.Trigger)
            hide.assert_called_once_with()
            show_window.assert_not_called()

    def test_tray_click_restores_when_hidden_minimized_or_obscured(self):
        with patch.object(self.controller.window, "is_foreground", return_value=False), \
                patch.object(self.controller, "show_window") as show_window:
            self.controller._tray_activated(QSystemTrayIcon.Trigger)
            show_window.assert_called_once_with()

    def test_alt_v_show_path_never_toggles_window(self):
        with patch.object(self.controller, "refresh") as refresh, \
                patch.object(self.controller.window, "show_and_activate") as activate, \
                patch.object(self.controller.window, "hide") as hide:
            self.controller.show_window()
            refresh.assert_called_once_with()
            activate.assert_called_once_with()
            hide.assert_not_called()

    def test_minimize_state_remains_visible_in_taskbar(self):
        window = self.controller.window
        window.show()
        self.app.processEvents()
        self.assertTrue(window.isVisible())
        window.showMinimized()
        self.app.processEvents()
        self.app.processEvents()
        self.assertTrue(window.isVisible())
        self.assertTrue(window.isMinimized())

        with patch.object(window, "show_and_activate") as activate:
            self.controller.show_window()
            activate.assert_called_once_with()

    def test_escape_hides_window(self):
        self.controller.window.show()
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        QApplication.sendEvent(self.controller.window.search, event)
        self.assertFalse(self.controller.window.isVisible())

    def test_full_content_dialog_is_resizable_and_maximizable(self):
        dialog = self.controller.window.create_full_content_dialog("complete\nclipboard\ncontent")
        try:
            self.assertTrue(dialog.isSizeGripEnabled())
            self.assertTrue(dialog.windowFlags() & Qt.WindowMaximizeButtonHint)
            self.assertGreaterEqual(dialog.width(), 820)
        finally:
            dialog.close()

    def test_settings_ranges_cover_file_capacity_and_200_images(self):
        dialog = SettingsDialog(
            "Alt+V", 1000, 200, 2048, "*", str(Path(self.temp.name)),
            {"total": 0, "text": 0, "image": 0, "file": 0}, 42, False,
            always_on_top=True,
        )
        try:
            self.assertEqual(dialog.image_limit.maximum(), 200)
            self.assertEqual(dialog.file_cache_limit.minimum(), 128)
            self.assertEqual(dialog.file_cache_limit.maximum(), 2048)
            self.assertEqual(dialog.file_cache_extensions.text(), "*")
            self.assertTrue(dialog.always_on_top.isChecked())
            self.assertEqual(dialog.panel_transparency.minimum(), 0)
            self.assertEqual(dialog.panel_transparency.maximum(), 100)
            previews = []
            dialog.transparency_preview.connect(previews.append)
            dialog.panel_transparency.setValue(55)
            self.assertEqual(previews, [55])
            self.assertEqual(dialog.panel_transparency_value.text(), "55%")
            received = []
            dialog.apply_requested.connect(received.append)
            dialog.file_cache_extensions.setText("pdf; DOCX")
            dialog.always_on_top.setChecked(False)
            dialog._apply()
            self.assertEqual(received[0]["file_cache_extensions"], ".pdf, .docx")
            self.assertEqual(received[0]["panel_transparency"], 55)
            self.assertFalse(received[0]["always_on_top"])
        finally:
            dialog.close()

    def test_panel_transparency_is_clamped_and_applied_to_large_panels(self):
        window = self.controller.window
        window.set_panel_transparency(55)
        self.assertEqual(window.panel_transparency(), 55)
        self.assertIn("0.45", window.list_widget.styleSheet())
        self.assertIn("0.45", window.list_widget.viewport().styleSheet())
        self.assertIn("historyViewport", window.list_widget.viewport().styleSheet())
        self.assertIn("transparent", window.history_panel.styleSheet())
        self.assertIn("transparent", window.history_splitter.styleSheet())
        self.assertIn("0.45", window.editor.text_editor.styleSheet())
        window.set_panel_transparency(999)
        self.assertEqual(window.panel_transparency(), 100)
        self.assertIn("0.00", window.list_widget.viewport().styleSheet())
        self.assertIn("0.00", window.categories.viewport().styleSheet())
        self.assertIn("0.00", window.editor.text_editor.styleSheet())
        self.assertIn("0.00", window.editor.image_area.styleSheet())
        self.assertIn("0.00", window.editor.styleSheet())
        self.assertIn("transparent", window.category_panel.styleSheet())
        window.set_panel_transparency(-1)
        self.assertEqual(window.panel_transparency(), 0)
        self.assertIn("1.00", window.list_widget.viewport().styleSheet())
        self.assertIn("1.00", window.categories.viewport().styleSheet())
        self.assertIn("1.00", window.editor.text_editor.styleSheet())
        self.assertIn("1.00", window.editor.image_area.styleSheet())
        self.assertIn("1.00", window.editor.styleSheet())

    def test_clear_note_action_keeps_automatic_favorite(self):
        record_id = self.database.add_or_touch("annotated")
        self.database.set_note(record_id, "important")
        self.controller.handle_action("clear_note", record_id, "text")
        row = self.database.list_history()[0]
        self.assertEqual(row.note, "")
        self.assertTrue(row.is_favorite)

    def test_note_and_text_can_be_copied_without_creating_history(self):
        record_id = self.database.add_or_touch("正文内容")
        self.database.set_note(record_id, "重要备注")

        self.controller.handle_action("copy_note", record_id, "text")
        self.app.processEvents()
        self.assertEqual(self.controller.clipboard.text(), "重要备注")
        self.assertEqual(self.database.count("text"), 1)

        self.controller.handle_action("copy_note_with_content", record_id, "text")
        self.app.processEvents()
        self.assertEqual(self.controller.clipboard.text(), "正文内容\n\n备注：重要备注")
        self.assertEqual(self.database.count("text"), 1)

    def test_note_and_image_can_be_copied_as_one_mime_payload(self):
        from clipboard_plus.application import _image_png

        image = QImage(40, 30, QImage.Format_ARGB32)
        image.fill(QColor("magenta"))
        image_data = _image_png(image)
        record_id = self.database.add_or_touch_image(image_data, image_data)
        self.database.set_note(record_id, "图片备注", "image")

        self.controller.handle_action("copy_note_with_content", record_id, "image")
        self.app.processEvents()
        mime = self.controller.clipboard.mimeData()
        self.assertTrue(mime.hasText())
        self.assertEqual(mime.text(), "图片备注")
        self.assertTrue(mime.hasImage())
        self.assertEqual(self.database.count("image"), 1)

    def test_delayed_activation_timers_cancelled_on_hide(self):
        window = self.controller.window
        window.show_and_activate()
        first_token = window._activation_token
        self.assertGreater(first_token, 0)
        window.hide()
        self.assertGreater(window._activation_token, first_token)
        self.assertEqual(len(window._activation_timers), 0)
        self.app.processEvents()
        time.sleep(0.22)
        self.app.processEvents()
        self.assertFalse(window.isVisible())

    def test_delayed_activation_timers_cancelled_on_minimize(self):
        window = self.controller.window
        window.show_and_activate()
        first_token = window._activation_token
        window.showMinimized()
        self.app.processEvents()
        self.assertGreater(window._activation_token, first_token)
        self.assertEqual(len(window._activation_timers), 0)
        time.sleep(0.22)
        self.app.processEvents()
        self.assertTrue(window.isVisible())
        self.assertTrue(window.isMinimized())

    def test_rapid_show_and_activate_coalesces_timers(self):
        window = self.controller.window
        for _ in range(3):
            window.show_and_activate()
        token_after_rapid = window._activation_token
        self.assertGreaterEqual(token_after_rapid, 3)
        self.assertEqual(len(window._activation_timers), 2)
        time.sleep(0.22)
        self.app.processEvents()
        self.assertTrue(window.isVisible())
        self.assertFalse(window.isMinimized())

    def test_alt_v_repeated_calls_never_toggle_hidden(self):
        window = self.controller.window
        for _ in range(3):
            self.controller.show_window()
            self.app.processEvents()
            self.assertTrue(window.isVisible())
            self.assertFalse(window.isMinimized())

    def test_always_on_top_restored_on_controller_init(self):
        self.assertFalse(self.controller.window.is_pinned())
        self.assertFalse(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
        self.database.set_setting("always_on_top", "true")
        restored_controller = ClipboardController(self.app, self.database)
        try:
            self.assertTrue(restored_controller.window.is_pinned())
            self.assertTrue(restored_controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertTrue(restored_controller.window.pin_window.isChecked())
            self.assertEqual(restored_controller.window.pin_window.text(), "固定窗口")
        finally:
            try:
                restored_controller.clipboard.dataChanged.disconnect(restored_controller._clipboard_changed)
            except RuntimeError:
                pass
            restored_controller.tray.hide()
            restored_controller.window.close()

    def test_apply_settings_updates_live_window_pin_and_persists_setting(self):
        dialog = SettingsDialog(
            "Alt+V", 1000, 200, 2048, "*", str(Path(self.temp.name)),
            {"total": 0, "text": 0, "image": 0, "file": 0}, 42, False,
            parent=self.controller.window, always_on_top=False,
        )
        try:
            values = {
                "hotkey": "Alt+V",
                "history_limit": 1000,
                "image_limit": 200,
                "file_cache_limit_mb": 512,
                "file_cache_extensions": "*",
                "panel_transparency": 42,
                "storage_path": str(self.database.path.parent),
                "autostart": False,
                "always_on_top": True,
            }
            self.controller._apply_settings(dialog, values)
            self.assertTrue(self.controller.window.is_pinned())
            self.assertTrue(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertTrue(self.controller.window.pin_window.isChecked())
            self.assertEqual(self.controller.window.pin_window.text(), "固定窗口")
            self.assertEqual(self.database.get_setting("always_on_top", ""), "true")

            values["always_on_top"] = False
            self.controller._apply_settings(dialog, values)
            self.assertFalse(self.controller.window.is_pinned())
            self.assertFalse(self.controller.window.windowFlags() & Qt.WindowStaysOnTopHint)
            self.assertFalse(self.controller.window.pin_window.isChecked())
            self.assertEqual(self.controller.window.pin_window.text(), "普通窗口")
            self.assertEqual(self.database.get_setting("always_on_top", ""), "false")
        finally:
            dialog.close()

    def test_show_window_and_scroll_top_button_resets_history_list_and_scroll(self):
        for i in range(40):
            self.database.add_or_touch(f"history record {i}")
        self.controller.refresh()
        self.assertEqual(self.controller.window.list_widget.count(), 40)
        self.assertTrue(self.controller.window.scroll_top_button.isEnabled())

        self.controller.window.list_widget.setCurrentRow(35)
        v_bar = self.controller.window.list_widget.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())
        self.assertEqual(self.controller.window.list_widget.currentRow(), 35)

        self.controller.window.scroll_top_button.click()
        self.assertEqual(self.controller.window.list_widget.currentRow(), 0)
        self.assertEqual(v_bar.value(), v_bar.minimum())

        self.controller.window.list_widget.setCurrentRow(30)
        v_bar.setValue(v_bar.maximum())
        self.assertEqual(self.controller.window.list_widget.currentRow(), 30)

        self.controller.show_window()
        self.assertEqual(self.controller.window.list_widget.currentRow(), 0)
        self.assertEqual(v_bar.value(), v_bar.minimum())

    def test_scroll_top_button_disabled_in_editor_mode_and_empty_list(self):
        self.assertEqual(self.controller.window.list_widget.count(), 0)
        self.assertFalse(self.controller.window.scroll_top_button.isEnabled())
        self.controller.window.scroll_to_top()

        self.database.add_or_touch("test record")
        self.controller.refresh()
        self.assertTrue(self.controller.window.scroll_top_button.isEnabled())

        self.controller.window.set_mode("editor")
        self.assertFalse(self.controller.window.scroll_top_button.isEnabled())
        self.controller.window.scroll_to_top()


if __name__ == "__main__":
    unittest.main()
