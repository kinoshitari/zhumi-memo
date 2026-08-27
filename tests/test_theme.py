import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QGraphicsView,
    QKeySequenceEdit, QLabel, QLineEdit, QListWidget, QMainWindow,
    QPlainTextEdit, QPushButton, QScrollArea, QScrollBar, QSpinBox,
    QSplitter, QTextEdit, QToolButton, QToolTip, QWidget,
)

from clipboard_plus.theme import (
    APP_STYLESHEET,
    COLOR_CYAN_ACCENT,
    COLOR_GOLD_ACCENT,
    COLOR_ROSE_ACCENT,
    COLOR_SKY_BASE,
    COLOR_SKY_BORDER,
    COLOR_TEXT_PRIMARY,
    apply_app_theme,
)


class ThemePublicInterfaceTests(unittest.TestCase):
    def test_public_interface_exposed(self):
        self.assertIsInstance(APP_STYLESHEET, str)
        self.assertGreater(len(APP_STYLESHEET), 0)
        self.assertTrue(callable(apply_app_theme))

    def test_light_palette_colors_present(self):
        core_palette = [
            COLOR_SKY_BASE,
            COLOR_SKY_BORDER,
            COLOR_CYAN_ACCENT,
            COLOR_ROSE_ACCENT,
            COLOR_GOLD_ACCENT,
            COLOR_TEXT_PRIMARY,
            "#FFFFFF",
            "#F3F8FE",
            "#42B0FF",
            "#4D6B94",
        ]
        stylesheet_upper = APP_STYLESHEET.upper()
        for color in core_palette:
            with self.subTest(color=color):
                self.assertIn(color.upper(), stylesheet_upper)

    def test_gradients_and_translucent_surfaces_present(self):
        stylesheet_lower = APP_STYLESHEET.lower()
        self.assertIn("qlineargradient", stylesheet_lower)
        self.assertIn("rgba(", stylesheet_lower)

    def test_required_orchestrator_selectors_present(self):
        required_orchestrator_selectors = [
            "#windowChrome",
            "#customTitleBar",
            "#titleBarTitle",
            "#titleBarSubtitle",
            "#titleBarButton",
            "#titleBarCloseButton",
            "#contentDeck",
            "#cheshireWatermark",
        ]
        for selector in required_orchestrator_selectors:
            with self.subTest(selector=selector):
                self.assertIn(selector, APP_STYLESHEET)

    def test_common_widget_selectors_present(self):
        required_selectors = [
            "QMainWindow",
            "QDialog",
            "QWidget",
            "QPushButton",
            "QPushButton:checked",
            "QToolButton",
            "QLineEdit",
            "QPlainTextEdit",
            "QTextEdit",
            "QKeySequenceEdit",
            "QDateEdit",
            "QListWidget",
            "QListWidget::item",
            "QListWidget#categories",
            "QComboBox",
            "QSpinBox",
            "QCheckBox",
            "QMenu",
            "QScrollBar",
            "QToolTip",
            "QLabel",
            "QSplitter",
            "QScrollArea",
            "QGraphicsView",
            "QCalendarWidget",
            "QLabel#brandMark",
            "QPushButton#modeButton",
            "QWidget#scratchEditor",
            "QLabel#editorHeading",
            "QLabel#editorDescription",
            "QLabel#editorImageInfo",
            "QPlainTextEdit#editorTextInput",
            "QLabel#editorImageDropArea",
            "QPushButton#editorPrimaryAction",
            "QPushButton#editorClearAction",
        ]
        for selector in required_selectors:
            with self.subTest(selector=selector):
                self.assertIn(selector, APP_STYLESHEET)

    def test_state_selectors_present(self):
        required_states = [
            ":hover",
            ":pressed",
            ":checked",
            ":selected",
            ":disabled",
            ":focus",
            ":read-only",
        ]
        for state in required_states:
            with self.subTest(state=state):
                self.assertIn(state, APP_STYLESHEET)

    def test_no_url_or_remote_resources(self):
        stylesheet_lower = APP_STYLESHEET.lower()
        self.assertNotIn("url(", stylesheet_lower)
        self.assertNotIn("http://", stylesheet_lower)
        self.assertNotIn("https://", stylesheet_lower)
        self.assertNotIn("data:image", stylesheet_lower)

    def test_balanced_braces(self):
        open_count = APP_STYLESHEET.count("{")
        close_count = APP_STYLESHEET.count("}")
        self.assertGreater(open_count, 0)
        self.assertEqual(open_count, close_count)

        depth = 0
        for char in APP_STYLESHEET:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            self.assertGreaterEqual(depth, 0, "Braces closed before opening")
        self.assertEqual(depth, 0)


class ThemeSafetyAndApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_apply_theme_to_mock_object(self):
        mock_widget = MagicMock()
        apply_app_theme(mock_widget)
        mock_widget.setStyleSheet.assert_called_once_with(APP_STYLESHEET)

    def test_apply_theme_safety_on_none_and_incompatible_objects(self):
        # Should not raise any exceptions
        apply_app_theme(None)
        apply_app_theme(object())
        apply_app_theme("not_a_widget")
        apply_app_theme(12345)
        apply_app_theme({"key": "value"})

    def test_apply_theme_on_real_widgets(self):
        widgets = [
            QWidget(),
            QDialog(),
            QMainWindow(),
            QPushButton("Test Button"),
            QToolButton(),
            QLineEdit("Test Input"),
            QPlainTextEdit("Test Content"),
            QTextEdit("Test Document"),
            QListWidget(),
            QComboBox(),
            QSpinBox(),
            QCheckBox("Test Option"),
            QScrollBar(),
            QSplitter(),
            QScrollArea(),
            QGraphicsView(),
            QKeySequenceEdit(),
            QDateEdit(),
        ]
        for widget in widgets:
            with self.subTest(widget_type=widget.__class__.__name__):
                apply_app_theme(widget)
                self.assertEqual(widget.styleSheet(), APP_STYLESHEET)

    def test_apply_theme_preserves_widget_state(self):
        button = QPushButton("Action")
        button.setEnabled(False)
        button.setCheckable(True)
        button.setChecked(True)

        apply_app_theme(button)

        self.assertEqual(button.text(), "Action")
        self.assertFalse(button.isEnabled())
        self.assertTrue(button.isCheckable())
        self.assertTrue(button.isChecked())
        self.assertEqual(button.styleSheet(), APP_STYLESHEET)

    def test_apply_theme_on_application(self):
        apply_app_theme(self.app)
        self.assertEqual(self.app.styleSheet(), APP_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
