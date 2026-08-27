import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from clipboard_plus.window import ClipboardWindow
from clipboard_plus.window_chrome import (
    HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT, HTLEFT, HTRIGHT,
    HTTOP, HTTOPLEFT, HTTOPRIGHT, MODE_BACKGROUND_PATHS,
    resize_hit_test, screen_resize_hit_test,
    unpack_screen_point,
)


class WindowChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_all_resize_edges_and_corners(self):
        expected = {
            (0, 0): HTTOPLEFT, (99, 0): HTTOPRIGHT,
            (0, 99): HTBOTTOMLEFT, (99, 99): HTBOTTOMRIGHT,
            (0, 50): HTLEFT, (99, 50): HTRIGHT,
            (50, 0): HTTOP, (50, 99): HTBOTTOM,
            (50, 50): None,
        }
        for point, hit in expected.items():
            with self.subTest(point=point):
                self.assertEqual(resize_hit_test(*point, 100, 100), hit)

    def test_points_outside_window_never_become_resize_handles(self):
        for point in ((-1, 50), (100, 50), (50, -1), (50, 100), (500, 500)):
            with self.subTest(point=point):
                self.assertIsNone(resize_hit_test(*point, 100, 100))

    def test_native_screen_coordinates_remain_correct_at_high_dpi(self):
        rect = (1000, 400, 2500, 1300)
        self.assertIsNone(screen_resize_hit_test(1750, 850, *rect, dpi=144))
        self.assertEqual(screen_resize_hit_test(1003, 850, *rect, dpi=144), HTLEFT)
        self.assertEqual(screen_resize_hit_test(2497, 403, *rect, dpi=144), HTTOPRIGHT)

    def test_nchittest_lparam_supports_negative_monitor_coordinates(self):
        x, y = -1200, 350
        packed = ((y & 0xFFFF) << 16) | (x & 0xFFFF)
        self.assertEqual(unpack_screen_point(packed), (x, y))

    def test_window_uses_translucent_frameless_chrome(self):
        window = ClipboardWindow()
        try:
            self.assertTrue(window.windowFlags() & Qt.FramelessWindowHint)
            self.assertTrue(window.testAttribute(Qt.WA_TranslucentBackground))
            self.assertEqual(window.window_chrome.objectName(), "windowChrome")
            self.assertEqual(window.title_bar.objectName(), "customTitleBar")
            self.assertEqual(window.content_deck.objectName(), "contentDeck")
            self.assertFalse(window.content_deck._character.isNull())
            self.assertTrue(window.content_deck._character.hasAlphaChannel())
            self.assertTrue(window.content_deck.watermark.testAttribute(Qt.WA_TransparentForMouseEvents))
            self.assertEqual(window.title_bar.close_button.accessibleName(), "关闭到托盘")
            self.assertEqual(
                set(window.content_deck._backgrounds),
                set(MODE_BACKGROUND_PATHS),
            )
            margins = window._root_layout.contentsMargins()
            self.assertEqual(
                (margins.left(), margins.top(), margins.right(), margins.bottom()),
                (0, 0, 0, 0),
            )
        finally:
            window.close()

    def test_watercolor_layer_is_cached_for_stable_size(self):
        window = ClipboardWindow()
        try:
            deck = window.content_deck
            deck.resize(720, 480)
            deck._render_watercolor_cache()
            first_key = deck._watercolor_cache.cacheKey()
            self.assertFalse(deck._watercolor_cache.isNull())
            deck._render_watercolor_cache()
            self.assertEqual(deck._watercolor_cache.cacheKey(), first_key)
        finally:
            window.close()

    def test_maximize_toggle_updates_titlebar(self):
        window = ClipboardWindow()
        try:
            window.showMaximized()
            window._sync_chrome_state()
            self.assertEqual(window.title_bar.maximize_button.accessibleName(), "还原")
            margins = window._root_layout.contentsMargins()
            self.assertEqual(
                (margins.left(), margins.top(), margins.right(), margins.bottom()),
                (0, 0, 0, 0),
            )
            window._toggle_maximized()
            self.assertFalse(window.isMaximized())
            self.assertEqual(window.title_bar.maximize_button.accessibleName(), "最大化")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
