from pathlib import Path
import unittest

from clipboard_plus.file_types import (
    file_matches_cache_extensions, is_common_image_file,
    normalize_file_cache_extensions,
)


class FileTypeTests(unittest.TestCase):
    def test_common_image_extensions_are_detected_case_insensitively(self):
        for name in ("photo.JPG", "graphic.webp", "scan.TIFF", "icon.ico", "image.avif"):
            self.assertTrue(is_common_image_file(Path(name)))
        self.assertFalse(is_common_image_file(Path("document.pdf")))

    def test_file_cache_extensions_are_normalized_and_matched(self):
        extensions = normalize_file_cache_extensions("pdf; DOCX, .tar.gz")
        self.assertEqual(extensions, ".pdf, .docx, .tar.gz")
        self.assertTrue(file_matches_cache_extensions(Path("report.PDF"), extensions))
        self.assertTrue(file_matches_cache_extensions(Path("archive.tar.gz"), extensions))
        self.assertFalse(file_matches_cache_extensions(Path("photo.png"), extensions))

    def test_asterisk_and_empty_extension_settings(self):
        self.assertTrue(file_matches_cache_extensions(Path("anything.bin"), "*"))
        self.assertFalse(file_matches_cache_extensions(Path("anything.bin"), ""))
        with self.assertRaises(ValueError):
            normalize_file_cache_extensions("*, .pdf")


if __name__ == "__main__":
    unittest.main()
