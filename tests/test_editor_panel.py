import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from clipboard_plus.editor_panel import ScratchEditor


class ScratchEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.editor = ScratchEditor()

    def tearDown(self):
        self.editor.close()

    def test_text_image_copy_and_combined_signals(self):
        copied_text, copied_images, copied_all = [], [], []
        self.editor.copy_text_requested.connect(copied_text.append)
        self.editor.copy_image_requested.connect(copied_images.append)
        self.editor.copy_all_requested.connect(
            lambda text, image: copied_all.append((text, image))
        )
        self.editor.text_editor.setPlainText("柴郡测试文本")
        image = QImage(64, 48, QImage.Format_ARGB32)
        image.fill(QColor("cyan"))
        self.editor.set_image(image)

        self.editor.copy_text_button.click()
        self.editor.copy_image_button.click()
        self.editor.copy_all_button.click()

        self.assertEqual(copied_text, ["柴郡测试文本"])
        self.assertEqual(copied_images[0].size(), image.size())
        self.assertEqual(copied_all[0][0], "柴郡测试文本")
        self.assertEqual(copied_all[0][1].size(), image.size())

    def test_one_click_clear_resets_all_content_and_actions(self):
        self.editor.text_editor.setPlainText("temporary")
        image = QImage(20, 10, QImage.Format_ARGB32)
        image.fill(QColor("pink"))
        self.editor.set_image(image)
        self.assertTrue(self.editor.clear_button.isEnabled())

        self.editor.clear_button.click()

        self.assertEqual(self.editor.text(), "")
        self.assertFalse(self.editor.has_image())
        self.assertFalse(self.editor.copy_text_button.isEnabled())
        self.assertFalse(self.editor.copy_image_button.isEnabled())
        self.assertFalse(self.editor.copy_all_button.isEnabled())
        self.assertEqual(self.editor.image_info.text(), "尚未添加图片")

    def test_invalid_image_does_not_replace_current_image(self):
        image = QImage(12, 8, QImage.Format_ARGB32)
        image.fill(QColor("navy"))
        self.editor.set_image(image)
        self.editor.set_image(QImage())
        self.assertEqual(self.editor.image().size(), image.size())


if __name__ == "__main__":
    unittest.main()
