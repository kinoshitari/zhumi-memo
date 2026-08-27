import tempfile
import unittest
from pathlib import Path

from zhumi_core.mobile_repository import MobileHistoryRepository


class MobileRepositoryTests(unittest.TestCase):
    def test_text_and_images_are_independent_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = MobileHistoryRepository(Path(folder) / "mobile.db", text_limit=2, image_limit=5)
            first = repo.add_text("https://example.com")
            self.assertEqual(first, repo.add_text("https://example.com"))
            self.assertEqual("URL", repo.list("text")[0]["category"])
            repo.add_image(b"fake-png-a")
            repo.add_image(b"fake-png-b")
            self.assertEqual(1, len(repo.list("text")))
            self.assertEqual(2, len(repo.list("image")))
            repo.close()


if __name__ == "__main__":
    unittest.main()
