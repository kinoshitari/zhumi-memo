from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QKeySequenceEdit, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from .hotkey import parse_hotkey
from .file_types import normalize_file_cache_extensions


class SettingsDialog(QDialog):
    apply_requested = Signal(dict)

    def __init__(
        self, hotkey: str, history_limit: int, image_limit: int,
        file_cache_limit_mb: int, file_cache_extensions: str, storage_path: str, usage: dict,
        autostart: bool, parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("猪咪备忘录 - 设置")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.hotkey = QKeySequenceEdit(QKeySequence(hotkey), self)
        self.history_limit = QSpinBox(self)
        self.history_limit.setRange(100, 10000)
        self.history_limit.setSingleStep(100)
        self.history_limit.setValue(history_limit)
        self.image_limit = QSpinBox(self)
        self.image_limit.setRange(5, 200)
        self.image_limit.setValue(image_limit)
        self.file_cache_limit = QSpinBox(self)
        self.file_cache_limit.setRange(128, 2048)
        self.file_cache_limit.setSingleStep(128)
        self.file_cache_limit.setSuffix(" MB")
        self.file_cache_limit.setValue(file_cache_limit_mb)
        self.file_cache_extensions = QLineEdit(file_cache_extensions, self)
        self.file_cache_extensions.setPlaceholderText("* 或 .pdf, .docx, .xlsx")
        self.storage_path = QLineEdit(storage_path, self)
        self.storage_path.setReadOnly(True)
        browse = QPushButton("更改…", self)
        browse.clicked.connect(self._browse_storage)
        storage_row = QWidget(self)
        storage_layout = QHBoxLayout(storage_row)
        storage_layout.setContentsMargins(0, 0, 0, 0)
        storage_layout.addWidget(self.storage_path, 1)
        storage_layout.addWidget(browse)
        self.autostart = QCheckBox("登录 Windows 后自动启动", self)
        self.autostart.setChecked(autostart)
        form = QFormLayout()
        form.addRow("全局快捷键：", self.hotkey)
        form.addRow("最大文本数量：", self.history_limit)
        form.addRow("最大图片数量：", self.image_limit)
        form.addRow("文件缓存容量：", self.file_cache_limit)
        form.addRow("文件缓存格式：", self.file_cache_extensions)
        form.addRow("数据存放位置：", storage_row)
        form.addRow("缓存占用：", QLabel(self._format_usage(usage), self))
        hint = QLabel(
            "图片始终归入图片分类；“*”表示缓存全部非图片格式，留空则不缓存文件。"
            "收藏或固定的内容不会被自动清理。", self,
        )
        hint.setStyleSheet("color: #666;")
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.autostart)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        shortcut = self.hotkey.keySequence().toString(QKeySequence.PortableText)
        try:
            parse_hotkey(shortcut)
        except ValueError as exc:
            QMessageBox.warning(self, "快捷键无效", str(exc))
            return
        try:
            file_cache_extensions = normalize_file_cache_extensions(self.file_cache_extensions.text())
        except ValueError as exc:
            QMessageBox.warning(self, "文件格式无效", str(exc))
            return
        self.apply_requested.emit({
            "hotkey": shortcut,
            "history_limit": self.history_limit.value(),
            "image_limit": self.image_limit.value(),
            "file_cache_limit_mb": self.file_cache_limit.value(),
            "file_cache_extensions": file_cache_extensions,
            "storage_path": self.storage_path.text(),
            "autostart": self.autostart.isChecked(),
        })

    def _browse_storage(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "选择猪咪备忘录数据存放目录", self.storage_path.text()
        )
        if selected:
            self.storage_path.setText(selected)

    @staticmethod
    def _format_bytes(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if number < 1024 or unit == "GB":
                return "%.1f %s" % (number, unit)
            number /= 1024
        return "0 B"

    @classmethod
    def _format_usage(cls, usage: dict) -> str:
        return "总计 %s（文本 %s / 图片 %s / 文件 %s）" % (
            cls._format_bytes(usage.get("total", 0)),
            cls._format_bytes(usage.get("text", 0)),
            cls._format_bytes(usage.get("image", 0)),
            cls._format_bytes(usage.get("file", 0)),
        )
