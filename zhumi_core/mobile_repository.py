"""Small SQLite repository used by the Android client prototype."""

import hashlib
import sqlite3
from pathlib import Path
from typing import List, Optional

from .classification import classify_content


class MobileHistoryRepository:
    def __init__(self, path: Path, text_limit: int = 1000, image_limit: int = 10) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.text_limit = max(1, int(text_limit))
        self.image_limit = min(30, max(5, int(image_limit)))
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('text', 'image')),
                content TEXT,
                image_data BLOB,
                digest TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kind, digest)
            )"""
        )
        self.connection.commit()

    def add_text(self, content: str) -> Optional[int]:
        if not content:
            return None
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return self._upsert("text", digest, classify_content(content), content, None)

    def add_image(self, png_data: bytes) -> Optional[int]:
        if not png_data:
            return None
        digest = hashlib.sha256(png_data).hexdigest()
        return self._upsert("image", digest, "图片", None, png_data)

    def _upsert(self, kind: str, digest: str, category: str, content, image_data) -> int:
        row = self.connection.execute(
            "SELECT id FROM history WHERE kind = ? AND digest = ?", (kind, digest)
        ).fetchone()
        if row:
            record_id = int(row["id"])
            self.connection.execute(
                "UPDATE history SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (record_id,)
            )
        else:
            cursor = self.connection.execute(
                "INSERT INTO history(kind, content, image_data, digest, category) VALUES(?, ?, ?, ?, ?)",
                (kind, content, image_data, digest, category),
            )
            record_id = int(cursor.lastrowid)
        self._trim(kind, self.text_limit if kind == "text" else self.image_limit)
        self.connection.commit()
        return record_id

    def _trim(self, kind: str, limit: int) -> None:
        self.connection.execute(
            """DELETE FROM history WHERE id IN (
                SELECT id FROM history WHERE kind = ?
                ORDER BY updated_at DESC, id DESC LIMIT -1 OFFSET ?
            )""",
            (kind, limit),
        )

    def list(self, kind: str, query: str = "") -> List[sqlite3.Row]:
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        return list(
            self.connection.execute(
                """SELECT * FROM history WHERE kind = ?
                   AND (? = '' OR COALESCE(content, '') LIKE ? ESCAPE '\\')
                   ORDER BY updated_at DESC, id DESC""",
                (kind, query, pattern),
            )
        )

    def delete(self, record_id: int) -> None:
        self.connection.execute("DELETE FROM history WHERE id = ?", (record_id,))
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
