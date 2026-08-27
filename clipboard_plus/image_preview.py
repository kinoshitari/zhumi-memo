from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout,
)


class ZoomGraphicsView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(Qt.black))
        self._pixmap_item = None

    def set_image(self, image: QImage) -> None:
        scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem(QPixmap.fromImage(image))
        scene.addItem(self._pixmap_item)
        self.setScene(scene)
        self.fit_image()

    def wheelEvent(self, event) -> None:
        if not self._pixmap_item:
            return super().wheelEvent(event)
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        prospective = self.transform().m11() * factor
        if 0.02 <= prospective <= 50:
            self.scale(factor, factor)
        event.accept()

    def actual_size(self) -> None:
        self.resetTransform()

    def fit_image(self) -> None:
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)


class ImagePreviewDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setSizeGripEnabled(True)
        self.resize(960, 700)
        self.setMinimumSize(480, 320)
        self.status = QLabel("正在加载大图…", self)
        self.status.setAlignment(Qt.AlignCenter)
        self.view = ZoomGraphicsView(self)
        self.view.hide()
        actual = QPushButton("恢复原始大小", self)
        fit = QPushButton("适应窗口", self)
        close = QPushButton("关闭", self)
        actual.clicked.connect(self.view.actual_size)
        fit.clicked.connect(self.view.fit_image)
        close.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addWidget(actual)
        buttons.addWidget(fit)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status, 1)
        layout.addWidget(self.view, 1)
        layout.addLayout(buttons)

    def set_image(self, image: QImage) -> None:
        self.status.hide()
        self.view.show()
        self.view.set_image(image)

    def set_error(self, message: str) -> None:
        self.status.setText("图片加载失败：%s" % message)
