import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from clipboard_plus.config import resource_path
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

    def test_new_module_illustrations_have_real_alpha_channels(self):
        for mode in ("image", "file", "editor"):
            with self.subTest(mode=mode):
                image = QImage(str(resource_path(MODE_BACKGROUND_PATHS[mode])))
                self.assertFalse(image.isNull())
                self.assertTrue(image.hasAlphaChannel())

    def test_interruption_during_fade_in_reverses_cleanly_and_settles_on_latest(self):
        self.window.show()
        self.app.processEvents()
        self.window.set_mode("editor")
        QTest.qWait(100)
        self.assertEqual(self.window._transition_manager.phase(), "fade_in")
        self.window.set_mode("text")
        self.assertEqual(self.window._transition_manager.target_mode(), "text")
        QTest.qWait(240)
        self.assertEqual(self.window.current_mode(), "text")
        self.assertEqual(self.window.content_deck._mode, "text")
        self.assertTrue(self.window.history_panel.isVisibleTo(self.window))
        self.assertFalse(self.window.editor.isVisibleTo(self.window))
        self.assertFalse(self.window._transition_manager.is_animating())
        self.assertIsNone(self.window.editor.graphicsEffect())
        self.assertIsNone(self.window.history_panel.graphicsEffect())

    def test_same_mode_reselect_is_noop_and_does_not_restart_animation(self):
        self.window.show()
        self.app.processEvents()
        self.window.set_mode("text")
        self.assertFalse(self.window._transition_manager.is_animating())
        self.window.set_mode("image")
        self.assertTrue(self.window._transition_manager.is_animating())
        self.window.set_mode("image")
        QTest.qWait(240)
        self.assertEqual(self.window.current_mode(), "image")
        self.assertFalse(self.window._transition_manager.is_animating())

    def test_rapid_interruption_avoids_redundant_mode_changed_emissions(self):
        self.window.show()
        self.app.processEvents()
        emitted_modes = []
        self.window.mode_changed.connect(emitted_modes.append)
        for mode in ("image", "file", "editor", "image", "text"):
            self.window.set_mode(mode)
            QTest.qWait(5)
        QTest.qWait(240)
        self.assertEqual(self.window.current_mode(), "text")
        self.assertEqual(emitted_modes, [])

    def test_finish_immediately_cleans_up_all_graphics_effects_and_animations(self):
        self.window.show()
        self.app.processEvents()
        self.window.set_mode("editor")
        self.assertTrue(self.window._transition_manager.is_animating())
        self.window._transition_manager.finish_immediately()
        self.assertEqual(self.window.current_mode(), "editor")
        self.assertFalse(self.window._transition_manager.is_animating())
        self.assertIsNone(self.window.editor.graphicsEffect())
        self.assertIsNone(self.window.history_panel.graphicsEffect())

    def test_hide_event_cancels_in_flight_transition_and_applies_target(self):
        self.window.show()
        self.app.processEvents()
        self.window.set_mode("editor")
        self.assertTrue(self.window._transition_manager.is_animating())
        self.window.hide()
        self.assertEqual(self.window.current_mode(), "editor")
        self.assertFalse(self.window._transition_manager.is_animating())
        self.assertIsNone(self.window.editor.graphicsEffect())
        self.assertIsNone(self.window.history_panel.graphicsEffect())


if __name__ == "__main__":
    unittest.main()
