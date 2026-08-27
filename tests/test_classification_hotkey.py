import unittest

from clipboard_plus.classification import classify_content
from clipboard_plus.hotkey import MOD_ALT, MOD_CONTROL, MOD_NOREPEAT, parse_hotkey


class ClassificationTests(unittest.TestCase):
    def test_all_categories(self):
        cases = {
            "ordinary text": "文本",
            "https://example.com/a": "URL",
            '{"answer": 42}': "JSON",
            r"C:\\Temp\\notes.txt": "路径",
            "def answer():\n    return 42": "代码",
            "请帮我总结下面的文章内容并给出重点": "Prompt",
        }
        for content, expected in cases.items():
            self.assertEqual(classify_content(content), expected)


class HotkeyTests(unittest.TestCase):
    def test_parse_supported_hotkeys(self):
        modifiers, key = parse_hotkey("Ctrl+Alt+K")
        self.assertTrue(modifiers & MOD_CONTROL)
        self.assertTrue(modifiers & MOD_ALT)
        self.assertTrue(modifiers & MOD_NOREPEAT)
        self.assertEqual(key, ord("K"))

    def test_rejects_unmodified_key(self):
        with self.assertRaises(ValueError):
            parse_hotkey("V")


if __name__ == "__main__":
    unittest.main()
