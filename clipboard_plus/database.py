from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Dict, List, Optional, Tuple
import uuid

from .classification import classify_content


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    content: str
    copied_at: str
    category: str
    source_app: str
    is_favorite: bool
    is_pinned: bool
    note: str


@dataclass(frozen=True)
class ImageRecord:
    id: int
    thumbnail: bytes
    copied_at: str
    category: str
    source_app: str
    is_favorite: bool
    is_pinned: bool
    note: str


@dataclass(frozen=True)
class FileRecord:
    id: int
    display_name: str
    original_path: str
    copied_at: str
    category: str
    source_app: str
    is_favorite: bool
    is_pinned: bool
    note: str
    byte_size: int
    status: str
    error: str


class HistoryDatabase:
    def __init__(
        self, path: Path, limit: int = 1000, image_limit: int = 200,
        file_cache_limit_mb: int = 512,
    ) -> None:
        self.path = Path(path)
        self.limit = int(limit)
        self.image_limit = min(200, max(5, int(image_limit)))
        self.file_cache_limit_mb = min(2048, max(128, int(file_cache_limit_mb)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.image_cache_dir = self.path.parent / "images"
        self.file_cache_dir = self.path.parent / "files"
        self.image_cache_dir.mkdir(parents=True, exist_ok=True)
        self.file_cache_dir.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._create_schema()
        self._remove_orphan_image_cache_files()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL UNIQUE,
                    copied_at TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in self._connection.execute("PRAGMA table_info(history)")}
            additions = (
                ("category", "TEXT NOT NULL DEFAULT '文本'"),
                ("source_app", "TEXT NOT NULL DEFAULT ''"),
                ("is_favorite", "INTEGER NOT NULL DEFAULT 0"),
                ("is_pinned", "INTEGER NOT NULL DEFAULT 0"),
                ("category_manual", "INTEGER NOT NULL DEFAULT 0"),
                ("note", "TEXT NOT NULL DEFAULT ''"),
            )
            for name, definition in additions:
                if name not in columns:
                    self._connection.execute("ALTER TABLE history ADD COLUMN %s %s" % (name, definition))
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_order "
                "ON history(is_pinned DESC, copied_at DESC, id DESC)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL UNIQUE,
                    image_data BLOB NOT NULL,
                    thumbnail BLOB NOT NULL,
                    copied_at TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '图片',
                    source_app TEXT NOT NULL DEFAULT '',
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    category_manual INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_images_order "
                "ON images(is_pinned DESC, copied_at DESC, id DESC)"
            )
            image_columns = {row[1] for row in self._connection.execute("PRAGMA table_info(images)")}
            image_additions = (
                ("note", "TEXT NOT NULL DEFAULT ''"),
                ("cache_name", "TEXT NOT NULL DEFAULT ''"),
                ("byte_size", "INTEGER NOT NULL DEFAULT 0"),
            )
            for name, definition in image_additions:
                if name not in image_columns:
                    self._connection.execute("ALTER TABLE images ADD COLUMN %s %s" % (name, definition))
            self._connection.execute(
                """CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_key TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    cache_name TEXT NOT NULL DEFAULT '',
                    byte_size INTEGER NOT NULL DEFAULT 0,
                    modified_ns INTEGER NOT NULL DEFAULT 0,
                    copied_at TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '文件',
                    source_app TEXT NOT NULL DEFAULT '',
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    category_manual INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    error TEXT NOT NULL DEFAULT ''
                )"""
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_order ON files(is_pinned DESC,copied_at DESC,id DESC)"
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_categories (
                    name TEXT PRIMARY KEY COLLATE NOCASE,
                    created_at TEXT NOT NULL
                )
                """
            )
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            if version < 2:
                rows = self._connection.execute("SELECT id, content FROM history").fetchall()
                self._connection.executemany(
                    "UPDATE history SET category = ? WHERE id = ?",
                    [(classify_content(str(content)), int(record_id)) for record_id, content in rows],
                )
            if version < 5:
                # V5 raises the product image-history ceiling from the previous
                # 100 maximum to 200 ordinary images.
                self._connection.execute(
                    "INSERT INTO settings(key,value) VALUES('image_limit','200') "
                    "ON CONFLICT(key) DO UPDATE SET value='200'"
                )
                self._connection.execute(
                    "INSERT OR IGNORE INTO settings(key,value) VALUES('file_cache_limit_mb','512')"
                )
            self._connection.execute("PRAGMA user_version = 5")

    def _next_timestamp(self, table: str = "history") -> str:
        if table not in ("history", "images", "files"):
            raise ValueError("invalid table")
        now = datetime.now(timezone.utc)
        row = self._connection.execute("SELECT MAX(copied_at) FROM " + table).fetchone()
        if row and row[0]:
            try:
                latest = datetime.fromisoformat(str(row[0]))
                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)
                latest = latest.astimezone(timezone.utc)
                if latest >= now:
                    now = latest + timedelta(microseconds=1)
            except ValueError:
                pass
        return now.isoformat(timespec="microseconds")

    def add_or_touch(
        self, content: str, copied_at: Optional[str] = None,
        category: Optional[str] = None, source_app: str = "",
    ) -> int:
        timestamp = copied_at or self._next_timestamp("history")
        detected = category or classify_content(content)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO history(content, copied_at, category, source_app)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(content) DO UPDATE SET
                    copied_at=excluded.copied_at,
                    category=CASE WHEN history.category_manual=1 THEN history.category ELSE excluded.category END,
                    source_app=CASE WHEN excluded.source_app<>'' THEN excluded.source_app ELSE history.source_app END
                """,
                (content, timestamp, detected, source_app),
            )
            row = self._connection.execute("SELECT id FROM history WHERE content=?", (content,)).fetchone()
            self._trim_table("history", self.limit)
        return int(row[0])

    def add_or_touch_image(
        self, image_data: bytes, thumbnail: bytes, source_app: str = "",
        copied_at: Optional[str] = None,
    ) -> int:
        image_hash = hashlib.sha256(image_data).hexdigest()
        timestamp = copied_at or self._next_timestamp("images")
        cache_name = image_hash + ".png"
        cache_path = self.image_cache_dir / cache_name
        cache_created = False
        if not cache_path.exists():
            temporary = cache_path.with_suffix(".tmp")
            try:
                temporary.write_bytes(image_data)
                os.replace(str(temporary), str(cache_path))
                cache_created = True
            except OSError:
                try:
                    temporary.unlink()
                except OSError:
                    pass
                cache_name = ""
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO images(image_hash,image_data,thumbnail,copied_at,source_app,cache_name,byte_size)
                    VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(image_hash) DO UPDATE SET
                        copied_at=excluded.copied_at,
                        thumbnail=excluded.thumbnail,
                        cache_name=CASE WHEN excluded.cache_name<>'' THEN excluded.cache_name ELSE images.cache_name END,
                        byte_size=CASE WHEN excluded.byte_size>0 THEN excluded.byte_size ELSE images.byte_size END,
                        source_app=CASE WHEN excluded.source_app<>'' THEN excluded.source_app ELSE images.source_app END
                    """,
                    (
                        image_hash, sqlite3.Binary(b"" if cache_name else image_data),
                        sqlite3.Binary(thumbnail), timestamp, source_app, cache_name, len(image_data),
                    ),
                )
                row = self._connection.execute(
                    "SELECT id FROM images WHERE image_hash=?", (image_hash,)
                ).fetchone()
                self._trim_table("images", self.image_limit)
        except Exception:
            if cache_created:
                referenced = self._connection.execute(
                    "SELECT 1 FROM images WHERE cache_name=? LIMIT 1", (cache_name,)
                ).fetchone()
                if referenced is None:
                    self._remove_cache_file(self.image_cache_dir, cache_name)
            raise
        return int(row[0])

    def _trim_table(self, table: str, limit: int) -> None:
        if table not in ("history", "images"):
            raise ValueError("invalid table")
        protected = self._connection.execute(
            "SELECT COUNT(*) FROM %s WHERE is_favorite=1 OR is_pinned=1" % table
        ).fetchone()[0]
        # Image limits count ordinary records only; protected pictures are kept
        # in addition to the configured maximum.
        allowed = int(limit) if table == "images" else max(0, int(limit) - int(protected))
        doomed = []
        if table == "images":
            doomed = self._connection.execute(
                """SELECT id,cache_name FROM images
                   WHERE is_favorite=0 AND is_pinned=0
                   ORDER BY copied_at DESC,id DESC LIMIT -1 OFFSET ?""",
                (allowed,),
            ).fetchall()
        self._connection.execute(
            """
            DELETE FROM {table}
            WHERE is_favorite=0 AND is_pinned=0
              AND id NOT IN (
                SELECT id FROM {table} WHERE is_favorite=0 AND is_pinned=0
                ORDER BY copied_at DESC,id DESC LIMIT ?
              )
            """.format(table=table),
            (allowed,),
        )
        for _record_id, cache_name in doomed:
            self._remove_cache_file(self.image_cache_dir, str(cache_name or ""))

    @staticmethod
    def _filter_clause(
        query: str, category_filter: str, image: bool = False, file: bool = False,
        date_start: Optional[str] = None, date_end: Optional[str] = None,
    ):
        clauses, parameters = [], []
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = "%" + escaped + "%"
            if image:
                clauses.append("(source_app LIKE ? ESCAPE '\\' OR note LIKE ? ESCAPE '\\')")
                parameters.extend((pattern, pattern))
            elif file:
                clauses.append(
                    "(display_name LIKE ? ESCAPE '\\' OR original_path LIKE ? ESCAPE '\\' "
                    "OR source_app LIKE ? ESCAPE '\\' OR note LIKE ? ESCAPE '\\')"
                )
                parameters.extend((pattern, pattern, pattern, pattern))
            else:
                clauses.append("(content LIKE ? ESCAPE '\\' OR source_app LIKE ? ESCAPE '\\' OR note LIKE ? ESCAPE '\\')")
                parameters.extend((pattern, pattern, pattern))
        if category_filter == "收藏":
            clauses.append("is_favorite=1")
        elif category_filter == "固定":
            clauses.append("is_pinned=1")
        elif category_filter not in ("全部", "全部图片", "全部文件"):
            clauses.append("category=?")
            parameters.append(category_filter)
        if date_start:
            clauses.append("copied_at>=?")
            parameters.append(date_start)
        if date_end:
            clauses.append("copied_at<?")
            parameters.append(date_end)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters

    def list_history(
        self, query: str = "", category_filter: str = "全部",
        date_start: Optional[str] = None, date_end: Optional[str] = None,
    ) -> List[HistoryRecord]:
        where, parameters = self._filter_clause(
            query, category_filter, date_start=date_start, date_end=date_end
        )
        cursor = self._connection.execute(
            """SELECT id,substr(content,1,1000),copied_at,category,source_app,is_favorite,is_pinned,note
               FROM history""" + where + " ORDER BY is_pinned DESC,copied_at DESC,id DESC",
            tuple(parameters),
        )
        return [HistoryRecord(int(r[0]),str(r[1]),str(r[2]),str(r[3]),str(r[4]),bool(r[5]),bool(r[6]),str(r[7])) for r in cursor.fetchall()]

    def list_images(
        self, query: str = "", category_filter: str = "全部图片",
        date_start: Optional[str] = None, date_end: Optional[str] = None,
    ) -> List[ImageRecord]:
        where, parameters = self._filter_clause(
            query, category_filter, image=True, date_start=date_start, date_end=date_end
        )
        cursor = self._connection.execute(
            """SELECT id,thumbnail,copied_at,category,source_app,is_favorite,is_pinned,note
               FROM images""" + where + " ORDER BY is_pinned DESC,copied_at DESC,id DESC",
            tuple(parameters),
        )
        return [ImageRecord(int(r[0]),bytes(r[1]),str(r[2]),str(r[3]),str(r[4]),bool(r[5]),bool(r[6]),str(r[7])) for r in cursor.fetchall()]

    def list_files(
        self, query: str = "", category_filter: str = "全部文件",
        date_start: Optional[str] = None, date_end: Optional[str] = None,
    ) -> List[FileRecord]:
        where, parameters = self._filter_clause(
            query, category_filter, file=True, date_start=date_start, date_end=date_end
        )
        cursor = self._connection.execute(
            """SELECT id,display_name,original_path,copied_at,category,source_app,
                      is_favorite,is_pinned,note,byte_size,status,error
               FROM files""" + where + " ORDER BY is_pinned DESC,copied_at DESC,id DESC",
            tuple(parameters),
        )
        return [
            FileRecord(
                int(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]),
                bool(r[6]), bool(r[7]), str(r[8]), int(r[9]), str(r[10]), str(r[11]),
            )
            for r in cursor.fetchall()
        ]

    def get_content(self, record_id: int) -> Optional[str]:
        row = self._connection.execute("SELECT content FROM history WHERE id=?", (record_id,)).fetchone()
        return str(row[0]) if row else None

    def get_image(self, record_id: int) -> Optional[bytes]:
        row = self._connection.execute(
            "SELECT image_data,cache_name FROM images WHERE id=?", (record_id,)
        ).fetchone()
        if not row:
            return None
        if row[1]:
            try:
                return (self.image_cache_dir / str(row[1])).read_bytes()
            except OSError:
                pass
        return bytes(row[0]) if row[0] else None

    def get_image_cache_path(self, record_id: int) -> Optional[Path]:
        row = self._connection.execute("SELECT cache_name FROM images WHERE id=?", (record_id,)).fetchone()
        if not row or not row[0]:
            return None
        path = self.image_cache_dir / str(row[0])
        return path if path.is_file() else None

    def get_file_path(self, record_id: int) -> Optional[Path]:
        row = self._connection.execute(
            "SELECT original_path,cache_name,status FROM files WHERE id=?", (record_id,)
        ).fetchone()
        if not row:
            return None
        if row[1] and row[2] == "ready":
            cached = self.file_cache_dir / str(row[1])
            if cached.exists():
                return cached
        original = Path(str(row[0]))
        return original if original.exists() else None

    def touch_file(self, record_id: int) -> None:
        with self._connection:
            self._connection.execute(
                "UPDATE files SET copied_at=? WHERE id=?",
                (self._next_timestamp("files"), record_id),
            )

    def get_note(self, record_id: int, kind: str = "text") -> Optional[str]:
        table = self._table_for_kind(kind)
        row = self._connection.execute("SELECT note FROM %s WHERE id=?" % table, (record_id,)).fetchone()
        return str(row[0]) if row else None

    def set_note(self, record_id: int, note: str, kind: str = "text") -> bool:
        """Save a note and automatically favorite records with a non-empty note."""
        table = self._table_for_kind(kind)
        cleaned = note.strip()
        with self._connection:
            self._connection.execute(
                "UPDATE %s SET note=?,is_favorite=CASE WHEN ?<>'' THEN 1 ELSE is_favorite END WHERE id=?" % table,
                (cleaned, cleaned, record_id),
            )
            row = self._connection.execute("SELECT is_favorite FROM %s WHERE id=?" % table, (record_id,)).fetchone()
        return bool(row[0]) if row else False

    def toggle_favorite(self, record_id: int, kind: str = "text") -> bool:
        return self._toggle_flag(record_id, "is_favorite", kind)

    def toggle_pinned(self, record_id: int, kind: str = "text") -> bool:
        return self._toggle_flag(record_id, "is_pinned", kind)

    def _toggle_flag(self, record_id: int, column: str, kind: str) -> bool:
        table = self._table_for_kind(kind)
        with self._connection:
            self._connection.execute(
                "UPDATE %s SET %s=CASE %s WHEN 0 THEN 1 ELSE 0 END WHERE id=?" % (table,column,column),
                (record_id,),
            )
            row = self._connection.execute("SELECT %s FROM %s WHERE id=?" % (column,table), (record_id,)).fetchone()
        return bool(row[0]) if row else False

    def move_to_category(self, record_id: int, category: str, kind: str = "text") -> None:
        table = self._table_for_kind(kind)
        with self._connection:
            self._connection.execute(
                "UPDATE %s SET category=?,category_manual=1 WHERE id=?" % table,
                (category, record_id),
            )

    def list_custom_categories(self) -> List[str]:
        return [str(row[0]) for row in self._connection.execute(
            "SELECT name FROM custom_categories ORDER BY name COLLATE NOCASE"
        ).fetchall()]

    def add_custom_category(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        with self._connection:
            self._connection.execute(
                "INSERT INTO custom_categories(name,created_at) VALUES (?,?)",
                (cleaned, self._next_timestamp("history")),
            )

    def rename_custom_category(self, old: str, new: str) -> None:
        cleaned = new.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        with self._connection:
            self._connection.execute("UPDATE custom_categories SET name=? WHERE name=?", (cleaned, old))
            self._connection.execute("UPDATE history SET category=? WHERE category=?", (cleaned, old))
            self._connection.execute("UPDATE images SET category=? WHERE category=?", (cleaned, old))
            self._connection.execute("UPDATE files SET category=? WHERE category=?", (cleaned, old))

    def delete_custom_category(self, name: str) -> None:
        with self._connection:
            rows = self._connection.execute("SELECT id,content FROM history WHERE category=?", (name,)).fetchall()
            self._connection.executemany(
                "UPDATE history SET category=?,category_manual=0 WHERE id=?",
                [(classify_content(str(content)), int(record_id)) for record_id,content in rows],
            )
            self._connection.execute("UPDATE images SET category='图片',category_manual=0 WHERE category=?", (name,))
            self._connection.execute("UPDATE files SET category='文件',category_manual=0 WHERE category=?", (name,))
            self._connection.execute("DELETE FROM custom_categories WHERE name=?", (name,))

    def set_limit(self, limit: int) -> None:
        self.limit = int(limit)
        with self._connection:
            self._trim_table("history", self.limit)

    def set_image_limit(self, limit: int) -> None:
        self.image_limit = min(200, max(5, int(limit)))
        with self._connection:
            self._trim_table("images", self.image_limit)

    def set_file_cache_limit_mb(self, limit_mb: int) -> None:
        self.file_cache_limit_mb = min(2048, max(128, int(limit_mb)))
        with self._connection:
            removed_names = self._trim_file_cache()
        for name in removed_names:
            self._remove_cache_file(self.file_cache_dir, name)

    def prepare_file_cache(
        self, source_path: Path, source_app: str = "", copied_at: Optional[str] = None,
    ) -> Tuple[int, Optional[Path], bool]:
        """Register a file quickly and return a destination for background copying."""
        source = Path(source_path)
        stat = source.stat()
        if not source.is_file():
            raise ValueError("仅支持缓存普通文件")
        size = int(stat.st_size)
        modified_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)))
        identity = "%s|%d|%d" % (str(source.resolve()).lower(), size, modified_ns)
        file_key = hashlib.sha256(identity.encode("utf-8", errors="surrogatepass")).hexdigest()
        timestamp = copied_at or self._next_timestamp("files")
        cache_name = str(Path(file_key) / source.name)
        limit_bytes = self.file_cache_limit_mb * 1024 * 1024
        too_large = size > limit_bytes
        removed_names = self._make_file_cache_room(0 if too_large else size)
        with self._connection:
            self._connection.execute(
                """INSERT INTO files(
                       file_key,display_name,original_path,cache_name,byte_size,modified_ns,
                       copied_at,source_app,status,error
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(file_key) DO UPDATE SET
                       copied_at=excluded.copied_at,
                       original_path=excluded.original_path,
                       source_app=CASE WHEN excluded.source_app<>'' THEN excluded.source_app ELSE files.source_app END,
                       error=CASE WHEN files.status='ready' THEN files.error ELSE excluded.error END,
                       status=CASE WHEN files.status='ready' THEN files.status ELSE excluded.status END""",
                (
                    file_key, source.name, str(source), "" if too_large else cache_name,
                    size, modified_ns, timestamp, source_app,
                    "too_large" if too_large else "pending",
                    "文件超过缓存容量上限，仅保留原始路径" if too_large else "",
                ),
            )
            row = self._connection.execute(
                "SELECT id,cache_name,status FROM files WHERE file_key=?", (file_key,)
            ).fetchone()
        for name in removed_names:
            self._remove_cache_file(self.file_cache_dir, name)
        record_id = int(row[0])
        if row[2] == "ready" and row[1] and (self.file_cache_dir / str(row[1])).is_file():
            return record_id, self.file_cache_dir / str(row[1]), False
        if too_large:
            return record_id, None, False
        return record_id, self.file_cache_dir / cache_name, True

    def complete_file_cache(self, record_id: int, cache_path: Path, byte_size: int) -> bool:
        cache_name = str(Path(cache_path).resolve().relative_to(self.file_cache_dir.resolve()))
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE files SET cache_name=?,byte_size=?,status='ready',error='' WHERE id=?",
                (cache_name, int(byte_size), record_id),
            )
            if cursor.rowcount == 0:
                return False
            removed_names = self._trim_file_cache()
        for name in removed_names:
            self._remove_cache_file(self.file_cache_dir, name)
        return True

    def fail_file_cache(self, record_id: int, error: str) -> None:
        with self._connection:
            self._connection.execute(
                "UPDATE files SET status='error',error=?,cache_name='' WHERE id=?",
                (str(error)[:500], record_id),
            )

    def _make_file_cache_room(self, incoming_size: int) -> List[str]:
        limit_bytes = self.file_cache_limit_mb * 1024 * 1024
        current = int(self._connection.execute(
            "SELECT COALESCE(SUM(byte_size),0) FROM files "
            "WHERE status='ready' AND is_favorite=0 AND is_pinned=0"
        ).fetchone()[0])
        if current + int(incoming_size) <= limit_bytes:
            return []
        removed = []
        rows = self._connection.execute(
            """SELECT id,cache_name,byte_size FROM files
               WHERE status='ready' AND is_favorite=0 AND is_pinned=0
               ORDER BY copied_at ASC,id ASC"""
        ).fetchall()
        with self._connection:
            for record_id, cache_name, byte_size in rows:
                if current + int(incoming_size) <= limit_bytes:
                    break
                self._connection.execute("DELETE FROM files WHERE id=?", (int(record_id),))
                removed.append(str(cache_name or ""))
                current -= int(byte_size or 0)
        return removed

    def _trim_file_cache(self) -> List[str]:
        return self._make_file_cache_room(0)

    def storage_usage(self) -> Dict[str, int]:
        def directory_size(path: Path) -> int:
            total = 0
            try:
                for entry in path.rglob("*"):
                    if entry.is_file():
                        total += entry.stat().st_size
            except OSError:
                pass
            return total

        database_bytes = 0
        for suffix in ("", "-wal", "-shm"):
            try:
                database_bytes += Path(str(self.path) + suffix).stat().st_size
            except OSError:
                pass
        text_bytes = int(self._connection.execute(
            "SELECT COALESCE(SUM(length(CAST(content AS BLOB))+length(CAST(note AS BLOB))),0) FROM history"
        ).fetchone()[0])
        legacy_image_bytes = int(self._connection.execute(
            "SELECT COALESCE(SUM(length(image_data)+length(thumbnail)),0) FROM images"
        ).fetchone()[0])
        image_cache_bytes = directory_size(self.image_cache_dir)
        file_cache_bytes = directory_size(self.file_cache_dir)
        return {
            "text": text_bytes,
            "image": image_cache_bytes + legacy_image_bytes,
            "file": file_cache_bytes,
            "database": database_bytes,
            "total": database_bytes + image_cache_bytes + file_cache_bytes,
        }

    def relocate(self, new_root: Path) -> Path:
        """Copy the active database and caches to an empty directory and switch live."""
        target_root = Path(new_root).expanduser().resolve()
        old_root = self.path.parent.resolve()
        if target_root == old_root:
            return old_root
        if old_root in target_root.parents or target_root in old_root.parents:
            raise ValueError("新旧存储目录不能互相嵌套")
        target_root.mkdir(parents=True, exist_ok=True)
        target_db = target_root / self.path.name
        target_images = target_root / "images"
        target_files = target_root / "files"
        existing_paths = [path for path in (target_db, target_images, target_files) if path.exists()]
        if existing_paths:
            if not target_db.is_file():
                raise FileExistsError("目标目录已存在同名缓存文件夹，请选择其他目录")
            try:
                existing = sqlite3.connect(str(target_db))
                try:
                    tables = {str(row[0]) for row in existing.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()}
                finally:
                    existing.close()
            except sqlite3.Error as exc:
                raise FileExistsError("目标目录中的 clipboard.db 不是可识别的历史数据库") from exc
            if "history" not in tables:
                raise FileExistsError("目标目录中的 clipboard.db 不属于猪咪备忘录")

        token = uuid.uuid4().hex
        temp_db = target_root / (".%s.%s.migrating" % (self.path.name, token))
        temp_images = target_root / (".images.%s.migrating" % token)
        temp_files = target_root / (".files.%s.migrating" % token)
        try:
            destination = sqlite3.connect(str(temp_db))
            try:
                self._connection.backup(destination)
                destination.commit()
                if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError("迁移后的数据库完整性检查失败")
            finally:
                destination.close()
            shutil.copytree(str(self.image_cache_dir), str(temp_images))
            shutil.copytree(str(self.file_cache_dir), str(temp_files))
            if existing_paths:
                backup_root = target_root / ("previous-data-backup-" + token[:8])
                backup_root.mkdir()
                for path in existing_paths:
                    os.replace(str(path), str(backup_root / path.name))
            os.replace(str(temp_db), str(target_db))
            os.replace(str(temp_images), str(target_images))
            os.replace(str(temp_files), str(target_files))
        except Exception:
            for path in (
                temp_db, temp_images, temp_files, target_db,
                target_images, target_files,
            ):
                try:
                    if path.is_dir():
                        shutil.rmtree(str(path))
                    elif path.exists():
                        path.unlink()
                except OSError:
                    pass
            raise

        self._connection.close()
        self.path = target_db
        self.image_cache_dir = target_root / "images"
        self.file_cache_dir = target_root / "files"
        self._connection = sqlite3.connect(str(self.path))
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        return old_root

    def get_setting(self, key: str, default: str) -> str:
        row = self._connection.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )

    def delete(self, record_id: int, kind: str = "text") -> None:
        table = self._table_for_kind(kind)
        with self._connection:
            cache_name = ""
            if table in ("images", "files"):
                row = self._connection.execute(
                    "SELECT cache_name FROM %s WHERE id=?" % table, (record_id,)
                ).fetchone()
                cache_name = str(row[0] or "") if row else ""
            self._connection.execute("DELETE FROM %s WHERE id=?" % table, (record_id,))
        if table == "images":
            self._remove_cache_file(self.image_cache_dir, cache_name)
        elif table == "files":
            self._remove_cache_file(self.file_cache_dir, cache_name)

    def clear(self, kind: Optional[str] = None) -> None:
        with self._connection:
            if kind in (None, "text"):
                self._connection.execute("DELETE FROM history")
            if kind in (None, "image"):
                image_names = [str(row[0] or "") for row in self._connection.execute(
                    "SELECT cache_name FROM images"
                ).fetchall()]
                self._connection.execute("DELETE FROM images")
            else:
                image_names = []
            if kind in (None, "file"):
                file_names = [str(row[0] or "") for row in self._connection.execute(
                    "SELECT cache_name FROM files"
                ).fetchall()]
                self._connection.execute("DELETE FROM files")
            else:
                file_names = []
        for name in image_names:
            self._remove_cache_file(self.image_cache_dir, name)
        for name in file_names:
            self._remove_cache_file(self.file_cache_dir, name)

    def count(self, kind: str = "text") -> int:
        table = self._table_for_kind(kind)
        return int(self._connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])

    @staticmethod
    def _table_for_kind(kind: str) -> str:
        if kind == "image":
            return "images"
        if kind == "file":
            return "files"
        return "history"

    @staticmethod
    def _remove_cache_file(directory: Path, cache_name: str) -> None:
        if not cache_name:
            return
        root = directory.resolve()
        target = (directory / cache_name).resolve()
        if target != root and root not in target.parents:
            return
        try:
            target.unlink()
            if target.parent != root:
                try:
                    target.parent.rmdir()
                except OSError:
                    pass
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def _remove_orphan_image_cache_files(self) -> None:
        referenced = {
            str(row[0]) for row in self._connection.execute(
                "SELECT cache_name FROM images WHERE cache_name<>''"
            ).fetchall()
        }
        for path in self.image_cache_dir.iterdir():
            if path.is_file() and path.name not in referenced:
                self._remove_cache_file(self.image_cache_dir, path.name)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
