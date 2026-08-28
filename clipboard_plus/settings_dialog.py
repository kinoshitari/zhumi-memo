from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QKeySequenceEdit, QLineEdit, QMessageBox, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

from .hotkey import parse_hotkey
from .file_types import normalize_file_cache_extensions
from .config import MAX_PANEL_TRANSPARENCY, MIN_PANEL_TRANSPARENCY


class SettingsDialog(QDialog):
    apply_requested = Signal(dict)
    transparency_preview = Signal(int)

    def __init__(
        self, hotkey: str, history_limit: int, image_limit: int,
        file_cache_limit_mb: int, file_cache_extensions: str, storage_path: str, usage: dict,
        panel_transparency: int, autostart: bool, parent=None,
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
        self.panel_transparency = QSlider(Qt.Horizontal, self)
        self.panel_transparency.setRange(MIN_PANEL_TRANSPARENCY, MAX_PANEL_TRANSPARENCY)
        self.panel_transparency.setSingleStep(1)
        self.panel_transparency.setPageStep(5)
        self.panel_transparency.setValue(panel_transparency)
        self.panel_transparency.setToolTip("数值越高，内容面板越透明，立绘越清晰")
        self.panel_transparency_value = QLabel("%d%%" % self.panel_transparency.value(), self)
        self.panel_transparency_value.setMinimumWidth(38)
        transparency_row = QWidget(self)
        transparency_layout = QHBoxLayout(transparency_row)
        transparency_layout.setContentsMargins(0, 0, 0, 0)
        transparency_layout.addWidget(self.panel_transparency, 1)
        transparency_layout.addWidget(self.panel_transparency_value)
        self.panel_transparency.valueChanged.connect(self._transparency_changed)
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
        form.addRow("内容面板透明度：", transparency_row)
        form.addRow("数据存放位置：", storage_row)
        form.addRow("缓存占用：", QLabel(self._format_usage(usage), self))
        hint = QLabel(
            "图片始终归入图片分类；“*”表示缓存全部非图片格式，留空则不缓存文件。"
            "收藏或固定的内容不会被自动清理。", self,
        )
        hint.setObjectName("hint")
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
            "panel_transparency": self.panel_transparency.value(),
            "storage_path": self.storage_path.text(),
            "autostart": self.autostart.isChecked(),
        })

    def _transparency_changed(self, value: int) -> None:
        self.panel_transparency_value.setText("%d%%" % value)
        self.transparency_preview.emit(value)

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
