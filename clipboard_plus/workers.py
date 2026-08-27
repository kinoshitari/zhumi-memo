import shutil
import sqlite3
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage


class FileCopySignals(QObject):
    completed = Signal(int, str, int)
    failed = Signal(int, str, str)


class FileCopyTask(QRunnable):
    """Copy a potentially large file without blocking the Qt event loop."""

    def __init__(self, record_id: int, source: Path, destination: Path) -> None:
        super().__init__()
        self.record_id = int(record_id)
        self.source = Path(source)
        self.destination = Path(destination)
        self.signals = FileCopySignals()

    def run(self) -> None:
        temporary = self.destination.with_suffix(self.destination.suffix + ".part")
        try:
            size = self.source.stat().st_size
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            free = shutil.disk_usage(str(self.destination.parent)).free
            if free < size + 32 * 1024 * 1024:
                raise OSError("磁盘剩余空间不足，文件未缓存")
            with self.source.open("rb") as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
            shutil.copystat(str(self.source), str(temporary))
            temporary.replace(self.destination)
            self.signals.completed.emit(
                self.record_id, str(self.destination), int(self.destination.stat().st_size)
            )
        except Exception as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            self.signals.failed.emit(self.record_id, str(self.destination), str(exc))


class FileExportSignals(QObject):
    completed = Signal(str)
    failed = Signal(str)


class FileExportTask(QRunnable):
    def __init__(self, source: Path, destination: Path) -> None:
        super().__init__()
        self.source = Path(source)
        self.destination = Path(destination)
        self.signals = FileExportSignals()

    def run(self) -> None:
        temporary = self.destination.with_suffix(self.destination.suffix + ".part")
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            size = self.source.stat().st_size
            if shutil.disk_usage(str(self.destination.parent)).free < size + 32 * 1024 * 1024:
                raise OSError("目标磁盘剩余空间不足")
            with self.source.open("rb") as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
            shutil.copystat(str(self.source), str(temporary))
            temporary.replace(self.destination)
            self.signals.completed.emit(str(self.destination))
        except Exception as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            self.signals.failed.emit(str(exc))


class ImageLoadSignals(QObject):
    loaded = Signal(QImage)
    failed = Signal(str)


class ImageLoadTask(QRunnable):
    """Read and decode a full-size image on a worker thread."""

    def __init__(self, database_path: Path, record_id: int, cache_path: Path = None) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.record_id = int(record_id)
        self.cache_path = Path(cache_path) if cache_path else None
        self.signals = ImageLoadSignals()

    def run(self) -> None:
        try:
            data = None
            if self.cache_path and self.cache_path.is_file():
                data = self.cache_path.read_bytes()
            if not data:
                connection = sqlite3.connect(str(self.database_path))
                try:
                    row = connection.execute(
                        "SELECT image_data FROM images WHERE id=?", (self.record_id,)
                    ).fetchone()
                finally:
                    connection.close()
                data = bytes(row[0]) if row and row[0] else b""
            image = QImage.fromData(data)
            if image.isNull():
                raise ValueError("图片数据无法读取")
            self.signals.loaded.emit(image)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
