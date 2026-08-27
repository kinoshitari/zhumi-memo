from pathlib import Path
import hashlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from clipboard_plus.database import HistoryDatabase


class HistoryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = HistoryDatabase(Path(self.temp.name) / "test.db", limit=3)

    def tearDown(self):
        self.database.close()
        self.temp.cleanup()

    def test_add_deduplicate_and_move_to_top(self):
        self.database.add_or_touch("first", "2026-01-01T00:00:00+00:00")
        self.database.add_or_touch("second", "2026-01-02T00:00:00+00:00")
        first_id = self.database.add_or_touch("first", "2026-01-03T00:00:00+00:00")
        rows = self.database.list_history()
        self.assertEqual([row.content for row in rows], ["first", "second"])
        self.assertEqual(rows[0].id, first_id)
        self.assertEqual(self.database.count(), 2)

    def test_limit_search_delete_and_clear(self):
        for index in range(5):
            self.database.add_or_touch("item %d" % index, "2026-01-0%dT00:00:00+00:00" % (index + 1))
        self.assertEqual(self.database.count(), 3)
        rows = self.database.list_history("item 3")
        self.assertEqual(len(rows), 1)
        self.database.delete(rows[0].id)
        self.assertEqual(self.database.list_history("item 3"), [])
        self.database.clear()
        self.assertEqual(self.database.count(), 0)

    def test_search_treats_wildcards_as_literal(self):
        self.database.add_or_touch("100% ready")
        self.database.add_or_touch("other")
        self.assertEqual([row.content for row in self.database.list_history("%")], ["100% ready"])

    def test_long_text_uses_preview_but_full_content_remains_available(self):
        content = "x" * 100000
        record_id = self.database.add_or_touch(content)
        preview = self.database.list_history()[0].content
        self.assertEqual(len(preview), 1000)
        self.assertEqual(self.database.get_content(record_id), content)

    def test_favorite_and_pinned_survive_limit_cleanup(self):
        favorite_id = self.database.add_or_touch("keep favorite", "2026-01-01T00:00:00+00:00")
        pinned_id = self.database.add_or_touch("keep pinned", "2026-01-02T00:00:00+00:00")
        self.database.toggle_favorite(favorite_id)
        self.database.toggle_pinned(pinned_id)
        for index in range(5):
            self.database.add_or_touch("ordinary %d" % index)
        contents = [row.content for row in self.database.list_history()]
        self.assertIn("keep favorite", contents)
        self.assertIn("keep pinned", contents)
        self.assertEqual(len(contents), 3)
        self.assertEqual(self.database.list_history(category_filter="收藏")[0].id, favorite_id)
        self.assertEqual(self.database.list_history(category_filter="固定")[0].id, pinned_id)

    def test_manual_category_survives_recopy_and_custom_category_lifecycle(self):
        record_id = self.database.add_or_touch("https://example.com")
        self.database.add_custom_category("工作")
        self.database.move_to_category(record_id, "工作")
        self.database.add_or_touch("https://example.com")
        self.assertEqual(self.database.list_history()[0].category, "工作")
        self.database.rename_custom_category("工作", "项目")
        self.assertEqual(self.database.list_history()[0].category, "项目")
        self.database.delete_custom_category("项目")
        self.assertEqual(self.database.list_history()[0].category, "URL")

    def test_images_have_independent_limit_dedup_and_protection(self):
        self.database.set_image_limit(5)
        first_id = self.database.add_or_touch_image(b"image-one", b"thumb-one")
        self.database.toggle_favorite(first_id, "image")
        for index in range(2, 8):
            self.database.add_or_touch_image(
                ("image-%d" % index).encode(), ("thumb-%d" % index).encode()
            )
        rows = self.database.list_images()
        self.assertEqual(len(rows), 6)
        self.assertIn(first_id, [row.id for row in rows])
        self.assertEqual(sum(not row.is_favorite and not row.is_pinned for row in rows), 5)
        same_id = self.database.add_or_touch_image(b"image-one", b"thumb-new")
        self.assertEqual(same_id, first_id)
        self.assertEqual(self.database.get_image(first_id), b"image-one")
        self.database.add_custom_category("截图")
        self.database.move_to_category(first_id, "截图", "image")
        self.database.add_or_touch_image(b"image-one", b"thumb-newer")
        self.assertEqual(self.database.list_images(category_filter="截图")[0].id, first_id)

    def test_image_delete_removes_external_cache(self):
        record_id = self.database.add_or_touch_image(b"cached-image", b"thumbnail")
        cache_path = self.database.get_image_cache_path(record_id)
        self.assertIsNotNone(cache_path)
        self.assertTrue(cache_path.exists())
        self.database.delete(record_id, "image")
        self.assertFalse(cache_path.exists())

    def test_failed_image_insert_and_startup_cleanup_leave_no_orphan_cache(self):
        image_data = b"image-that-will-roll-back"
        cache_path = self.database.image_cache_dir / (
            hashlib.sha256(image_data).hexdigest() + ".png"
        )
        with patch.object(self.database, "_trim_table", side_effect=RuntimeError("forced")):
            with self.assertRaises(RuntimeError):
                self.database.add_or_touch_image(image_data, b"thumbnail")
        self.assertFalse(cache_path.exists())
        self.assertEqual(self.database.count("image"), 0)

        orphan = self.database.image_cache_dir / "orphan.png"
        orphan.write_bytes(b"orphan")
        self.database.close()
        self.database = HistoryDatabase(Path(self.temp.name) / "test.db", limit=3)
        self.assertFalse(orphan.exists())

    def test_file_cache_capacity_cleans_oldest_unprotected_record(self):
        self.database.set_file_cache_limit_mb(128)
        paths = []
        for index in range(3):
            source = Path(self.temp.name) / ("source-%d.bin" % index)
            source.write_bytes(("data-%d" % index).encode())
            record_id, destination, should_copy = self.database.prepare_file_cache(
                source, copied_at="2026-01-0%dT00:00:00+00:00" % (index + 1)
            )
            self.assertTrue(should_copy)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            self.database.complete_file_cache(record_id, destination, 70 * 1024 * 1024)
            paths.append((record_id, destination))
            if index == 0:
                self.database.toggle_favorite(record_id, "file")
        rows = self.database.list_files()
        self.assertEqual(len(rows), 2)
        self.assertIn(paths[0][0], [row.id for row in rows])
        self.assertIn(paths[2][0], [row.id for row in rows])
        self.assertNotIn(paths[1][0], [row.id for row in rows])
        self.assertFalse(paths[1][1].exists())

    def test_single_file_larger_than_limit_is_recorded_without_copying(self):
        self.database.set_file_cache_limit_mb(128)
        source = Path(self.temp.name) / "oversized.bin"
        with source.open("wb") as handle:
            handle.truncate(129 * 1024 * 1024)
        started = __import__("time").perf_counter()
        record_id, destination, should_copy = self.database.prepare_file_cache(source)
        elapsed = __import__("time").perf_counter() - started
        self.assertFalse(should_copy)
        self.assertIsNone(destination)
        self.assertLess(elapsed, 0.5)
        row = self.database.list_files()[0]
        self.assertEqual(row.id, record_id)
        self.assertEqual(row.status, "too_large")
        self.assertEqual(self.database.get_file_path(record_id), source)

    def test_date_range_combines_with_keyword_search(self):
        self.database.add_or_touch("alpha old", "2026-07-01T00:00:00+00:00")
        self.database.add_or_touch("alpha new", "2026-08-20T00:00:00+00:00")
        self.database.add_or_touch("beta new", "2026-08-21T00:00:00+00:00")
        rows = self.database.list_history(
            "alpha", date_start="2026-08-01T00:00:00+00:00",
            date_end="2026-09-01T00:00:00+00:00",
        )
        self.assertEqual([row.content for row in rows], ["alpha new"])

    def test_notes_are_searchable_and_automatically_favorite_text_and_images(self):
        text_id = self.database.add_or_touch("plain clipboard text")
        image_id = self.database.add_or_touch_image(b"noted-image", b"noted-thumb")
        self.assertTrue(self.database.set_note(text_id, "项目登录信息"))
        self.assertTrue(self.database.set_note(image_id, "设计稿截图", "image"))
        text = self.database.list_history("登录信息")[0]
        image = self.database.list_images("设计稿")[0]
        self.assertEqual(text.note, "项目登录信息")
        self.assertEqual(image.note, "设计稿截图")
        self.assertTrue(text.is_favorite)
        self.assertTrue(image.is_favorite)
        self.database.set_note(text_id, "")
        self.assertEqual(self.database.get_note(text_id), "")
        self.assertTrue(self.database.list_history(category_filter="收藏")[0].is_favorite)


class MigrationTests(unittest.TestCase):
    def test_v1_database_is_migrated_without_losing_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "v1.db"
            connection = sqlite3.connect(str(path))
            connection.execute(
                "CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL UNIQUE, copied_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO history(id, content, copied_at) VALUES (7, ?, ?)",
                ("https://example.com/old", "2026-01-01T00:00:00+00:00"),
            )
            connection.commit()
            connection.close()
            database = HistoryDatabase(path)
            try:
                rows = database.list_history()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].id, 7)
                self.assertEqual(rows[0].content, "https://example.com/old")
                self.assertEqual(rows[0].category, "URL")
                self.assertEqual(database._connection.execute("PRAGMA user_version").fetchone()[0], 5)
                self.assertEqual(database.count("image"), 0)
                self.assertEqual(rows[0].note, "")
                self.assertEqual(database.get_setting("image_limit", ""), "200")
            finally:
                database.close()

    def test_storage_relocation_preserves_database_and_caches(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / "original"
            target = Path(folder) / "target"
            database = HistoryDatabase(original / "clipboard.db")
            text_id = database.add_or_touch("migrate me")
            image_id = database.add_or_touch_image(b"migrated-image", b"thumb")
            source = original / "migration-file.txt"
            source.write_text("file payload", encoding="utf-8")
            file_id, file_destination, _should_copy = database.prepare_file_cache(source)
            file_destination.parent.mkdir(parents=True, exist_ok=True)
            file_destination.write_bytes(source.read_bytes())
            database.complete_file_cache(file_id, file_destination, source.stat().st_size)
            old_root = database.relocate(target)
            try:
                self.assertEqual(old_root, original.resolve())
                self.assertEqual(database.path.parent, target.resolve())
                self.assertEqual(database.get_content(text_id), "migrate me")
                self.assertEqual(database.get_image(image_id), b"migrated-image")
                self.assertEqual(database.get_file_path(file_id).read_text(encoding="utf-8"), "file payload")
                self.assertTrue((original / "clipboard.db").exists())
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
