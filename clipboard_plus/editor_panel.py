from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)


class ImageDropArea(QLabel):
    image_dropped = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("editorImageDropArea")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(230, 180)
        self.setText("粘贴、选择或拖入图片")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasImage() or any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        image = QImage(mime.imageData()) if mime.hasImage() else QImage()
        if image.isNull():
            for url in mime.urls():
                if not url.isLocalFile():
                    continue
                image = QImage(str(Path(url.toLocalFile())))
                if not image.isNull():
                    break
        if image.isNull():
            event.ignore()
            return
        self.image_dropped.emit(image)
        event.acceptProposedAction()


class ScratchEditor(QWidget):
    copy_text_requested = Signal(str)
    copy_image_requested = Signal(object)
    copy_all_requested = Signal(str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("scratchEditor")
        self._image = QImage()

        heading = QLabel("即时编辑台", self)
        heading.setObjectName("editorHeading")
        description = QLabel(
            "自由输入文字，并可粘贴、选择或拖入图片。内容仅保留在当前窗口中。",
            self,
        )
        description.setObjectName("editorDescription")
        description.setWordWrap(True)

        self.text_editor = QPlainTextEdit(self)
        self.text_editor.setObjectName("editorTextInput")
        self.text_editor.setPlaceholderText("在这里输入要复制的文本…")
        self.text_editor.textChanged.connect(self._update_actions)

        self.image_area = ImageDropArea(self)
        self.image_area.image_dropped.connect(self.set_image)
        self.image_info = QLabel("尚未添加图片", self)
        self.image_info.setObjectName("editorImageInfo")
        self.image_info.setAlignment(Qt.AlignCenter)

        self.paste_image_button = QPushButton("粘贴图片", self)
        self.choose_image_button = QPushButton("选择图片…", self)
        self.clear_image_button = QPushButton("移除图片", self)
        self.paste_image_button.clicked.connect(self.paste_image)
        self.choose_image_button.clicked.connect(self.choose_image)
        self.clear_image_button.clicked.connect(self.clear_image)
        image_buttons = QHBoxLayout()
        image_buttons.addWidget(self.paste_image_button)
        image_buttons.addWidget(self.choose_image_button)
        image_buttons.addWidget(self.clear_image_button)

        image_panel = QWidget(self)
        image_panel.setObjectName("editorImagePanel")
        image_layout = QVBoxLayout(image_panel)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_area, 1)
        image_layout.addWidget(self.image_info)
        image_layout.addLayout(image_buttons)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setObjectName("editorSplitter")
        splitter.addWidget(self.text_editor)
        splitter.addWidget(image_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([430, 280])

        self.copy_text_button = QPushButton("复制文本", self)
        self.copy_image_button = QPushButton("复制图片", self)
        self.copy_all_button = QPushButton("复制文本＋图片", self)
        self.clear_button = QPushButton("一键清空", self)
        self.copy_all_button.setObjectName("editorPrimaryAction")
        self.clear_button.setObjectName("editorClearAction")
        self.copy_text_button.clicked.connect(self._copy_text)
        self.copy_image_button.clicked.connect(self._copy_image)
        self.copy_all_button.clicked.connect(self._copy_all)
        self.clear_button.clicked.connect(self.clear_all)
        actions = QHBoxLayout()
        actions.addWidget(self.copy_text_button)
        actions.addWidget(self.copy_image_button)
        actions.addWidget(self.copy_all_button)
        actions.addStretch(1)
        actions.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(splitter, 1)
        layout.addLayout(actions)
        self._update_actions()

    def text(self) -> str:
        return self.text_editor.toPlainText()

    def image(self) -> QImage:
        return self._image.copy()

    def has_image(self) -> bool:
        return not self._image.isNull()

    def set_image(self, image: QImage) -> None:
        candidate = QImage(image)
        if candidate.isNull():
            return
        self._image = candidate.copy()
        self.image_info.setText("%d × %d 像素" % (self._image.width(), self._image.height()))
        self._refresh_preview()
        self._update_actions()

    def paste_image(self) -> None:
        self.set_image(QApplication.clipboard().image())

    def choose_image(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)"
        )
        if selected:
            self.set_image(QImage(selected))

    def clear_image(self) -> None:
        self._image = QImage()
        self.image_area.clear()
        self.image_area.setText("粘贴、选择或拖入图片")
        self.image_info.setText("尚未添加图片")
        self._update_actions()

    def clear_all(self) -> None:
        self.text_editor.clear()
        self.clear_image()
        self.text_editor.setFocus(Qt.OtherFocusReason)

    def focus_editor(self) -> None:
        self.text_editor.setFocus(Qt.ShortcutFocusReason)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._image.isNull():
            return
        available = self.image_area.size()
        available.setWidth(max(1, available.width() - 18))
        available.setHeight(max(1, available.height() - 18))
        pixmap = QPixmap.fromImage(self._image).scaled(
            available, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_area.setPixmap(pixmap)

    def _copy_text(self) -> None:
        text = self.text()
        if text:
            self.copy_text_requested.emit(text)

    def _copy_image(self) -> None:
        if self.has_image():
            self.copy_image_requested.emit(self.image())

    def _copy_all(self) -> None:
        if self.text() or self.has_image():
            self.copy_all_requested.emit(self.text(), self.image())

    def _update_actions(self) -> None:
        has_text = bool(self.text())
        has_image = self.has_image()
        self.copy_text_button.setEnabled(has_text)
        self.copy_image_button.setEnabled(has_image)
        self.copy_all_button.setEnabled(has_text or has_image)
        self.clear_image_button.setEnabled(has_image)
        self.clear_button.setEnabled(has_text or has_image)
