import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clipboard_plus.window import ClipboardWindow
from clipboard_plus.window_chrome import MODE_BACKGROUND_PATHS


class ModeTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = ClipboardWindow()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_hidden_window_switches_immediately_and_updates_background(self):
        self.window.set_mode("image")
        self.assertEqual(self.window.current_mode(), "image")
        self.assertEqual(self.window.content_deck._mode, "image")
        self.assertFalse(self.window.content_deck._character.isNull())

    def test_visible_transition_finishes_and_releases_effects(self):
        self.window.show()
        self.app.processEvents()
        self.window.set_mode("editor")
        self.assertTrue(self.window._transition_manager.is_animating())
        QTest.qWait(230)
        self.assertEqual(self.window.current_mode(), "editor")
        self.assertTrue(self.window.editor.isVisibleTo(self.window))
        self.assertFalse(self.window.history_panel.isVisibleTo(self.window))
        self.assertIsNone(self.window.editor.graphicsEffect())
        self.assertIsNone(self.window.history_panel.graphicsEffect())

    def test_rapid_switching_settles_on_latest_mode(self):
        self.window.show()
        self.app.processEvents()
        for mode in ("image", "file", "editor", "image", "text"):
            self.window.set_mode(mode)
            QTest.qWait(18)
        QTest.qWait(240)
        self.assertEqual(self.window.current_mode(), "text")
        self.assertEqual(self.window.content_deck._mode, "text")
        self.assertTrue(self.window.history_panel.isVisibleTo(self.window))
        self.assertFalse(self.window.editor.isVisibleTo(self.window))
        self.assertFalse(self.window._transition_manager.is_animating())

    def test_all_mode_background_assets_load(self):
        self.assertEqual(set(MODE_BACKGROUND_PATHS), {"text", "image", "file", "editor"})
        for mode in MODE_BACKGROUND_PATHS:
            with self.subTest(mode=mode):
                self.window.set_mode(mode, animated=False)
                self.assertEqual(self.window.content_deck._mode, mode)
                self.assertFalse(self.window.content_deck._character.isNull())


if __name__ == "__main__":
    unittest.main()
