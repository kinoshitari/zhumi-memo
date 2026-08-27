"""Touch-friendly Android prototype for 猪咪备忘录.

Android 10+ limits clipboard reads to focused apps (or the default IME), so this
client records clipboard changes only while it is in the foreground and also
offers an explicit import button.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, QStandardPaths, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from zhumi_core.mobile_repository import MobileHistoryRepository


class MobileWindow(QMainWindow):
    def __init__(self, repository: MobileHistoryRepository) -> None:
        super().__init__()
        self.repository = repository
        self.clipboard = QApplication.clipboard()
        self.setWindowTitle("猪咪备忘录")
        self.resize(440, 760)

        root = QWidget()
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索文本历史")
        import_button = QPushButton("读取当前剪贴板")
        import_button.clicked.connect(self.capture_clipboard)
        header.addWidget(self.search, 1)
        header.addWidget(import_button)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.text_list = QListWidget()
        self.image_list = QListWidget()
        self.tabs.addTab(self.text_list, "文本")
        self.tabs.addTab(self.image_list, "图片")
        layout.addWidget(self.tabs, 1)

        footer = QLabel("Android 版仅在应用位于前台时读取剪贴板")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        self.setCentralWidget(root)

        self.search.textChanged.connect(self.refresh_text)
        self.text_list.itemDoubleClicked.connect(self.copy_selected_text)
        self.image_list.itemDoubleClicked.connect(self.copy_selected_image)
        self.clipboard.dataChanged.connect(self.capture_clipboard)
        self.refresh_all()

    def capture_clipboard(self) -> None:
        mime = self.clipboard.mimeData()
        if mime.hasImage():
            image = self.clipboard.image()
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            self.repository.add_image(bytes(data))
        elif mime.hasText() and mime.text():
            self.repository.add_text(mime.text())
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_text()
        self.refresh_images()

    def refresh_text(self) -> None:
        self.text_list.clear()
        for row in self.repository.list("text", self.search.text()):
            preview = (row["content"] or "").replace("\r", " ").replace("\n", " ")
            if len(preview) > 180:
                preview = preview[:180] + "…"
            item = QListWidgetItem("[%s] %s\n%s" % (row["category"], preview, row["updated_at"]))
            item.setData(Qt.ItemDataRole.UserRole, dict(row))
            item.setSizeHint(QSize(0, 72))
            self.text_list.addItem(item)

    def refresh_images(self) -> None:
        self.image_list.clear()
        for row in self.repository.list("image"):
            image = QImage.fromData(row["image_data"], "PNG")
            item = QListWidgetItem("图片 · %s" % row["updated_at"])
            item.setIcon(QIcon(QPixmap.fromImage(image).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )))
            item.setData(Qt.ItemDataRole.UserRole, dict(row))
            item.setSizeHint(QSize(0, 112))
            self.image_list.addItem(item)

    def copy_selected_text(self, item: QListWidgetItem) -> None:
        self.clipboard.setText(item.data(Qt.ItemDataRole.UserRole)["content"])
        QMessageBox.information(self, "猪咪备忘录", "文本已复制。")

    def copy_selected_image(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)["image_data"]
        self.clipboard.setImage(QImage.fromData(data, "PNG"))
        QMessageBox.information(self, "猪咪备忘录", "图片已复制。")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("猪咪备忘录")
    icon_path = PROJECT_ROOT / "assets" / "android_icon_192.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    repository = MobileHistoryRepository(data_dir / "zhumi_mobile.db")
    window = MobileWindow(repository)
    app.aboutToQuit.connect(repository.close)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
