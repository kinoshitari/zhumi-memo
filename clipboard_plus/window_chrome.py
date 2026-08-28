"""Custom frameless window chrome and Cheshire backdrop."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QIcon, QImage, QLinearGradient, QMouseEvent, QPainter,
    QPainterPath, QPen, QPixmap, QRadialGradient,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QGraphicsOpacityEffect,
    QLabel,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .config import resource_path


HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

MODE_BACKGROUND_PATHS = {
    "text": "assets/backgrounds/text.png",
    "image": "assets/backgrounds/image.png",
    "file": "assets/backgrounds/file.png",
    "editor": "assets/backgrounds/editor.png",
}


def resize_hit_test(x: int, y: int, width: int, height: int, margin: int = 7) -> int | None:
    """Return a Win32 resize hit-test code for an edge or corner."""

    if width <= 0 or height <= 0 or x < 0 or y < 0 or x >= width or y >= height:
        return None
    left = x < margin
    right = x >= width - margin
    top = y < margin
    bottom = y >= height - margin
    if top and left:
        return HTTOPLEFT
    if top and right:
        return HTTOPRIGHT
    if bottom and left:
        return HTBOTTOMLEFT
    if bottom and right:
        return HTBOTTOMRIGHT
    if left:
        return HTLEFT
    if right:
        return HTRIGHT
    if top:
        return HTTOP
    if bottom:
        return HTBOTTOM
    return None


def screen_resize_hit_test(
    screen_x: int,
    screen_y: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    dpi: int = 96,
) -> int | None:
    """Hit-test using one native physical-pixel coordinate system.

    Win32 cursor positions and ``GetWindowRect`` values are physical pixels.
    Keeping them together avoids the large false resize zones caused by mixing
    those values with Qt's DPI-scaled logical geometry.
    """

    width = right - left
    height = bottom - top
    margin = max(6, round(7 * max(96, dpi) / 96))
    return resize_hit_test(screen_x - left, screen_y - top, width, height, margin)


def unpack_screen_point(lparam: int) -> tuple[int, int]:
    """Decode the signed physical screen point carried by WM_NCHITTEST."""

    x = (lparam & 0xFFFF)
    y = ((lparam >> 16) & 0xFFFF)
    if x & 0x8000:
        x -= 0x10000
    if y & 0x8000:
        y -= 0x10000
    return x, y


class GlassDeck(QWidget):
    """Cached watercolor sky-glass surface with a mode-specific background."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("contentDeck")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._mode = "text"
        self._backgrounds = {
            mode: self._load_background(mode, relative_path)
            for mode, relative_path in MODE_BACKGROUND_PATHS.items()
        }
        self._character = self._backgrounds[self._mode]
        self._watercolor_cache = QPixmap()
        self._watercolor_cache_size = QSize()
        self.watermark = QLabel(self)
        self.watermark.setObjectName("cheshireWatermark")
        self.watermark.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._watermark_opacity = QGraphicsOpacityEffect(self.watermark)
        self._watermark_opacity.setOpacity(0.16)
        self.watermark.setGraphicsEffect(self._watermark_opacity)

    @staticmethod
    def _load_background(mode: str, relative_path: str) -> QPixmap:
        image = QImage(str(resource_path(relative_path)))
        if image.isNull():
            return QPixmap()
        if mode == "text":
            # The original text-mode artwork has a pure-black backdrop.
            alpha_mask = image.createMaskFromColor(QColor(0, 0, 0).rgb(), Qt.MaskOutColor)
            image = image.convertToFormat(QImage.Format_ARGB32)
            image.setAlphaChannel(alpha_mask)
        return QPixmap.fromImage(image)

    def set_mode(self, mode: str) -> None:
        if mode not in self._backgrounds or mode == self._mode:
            return
        self._mode = mode
        self._character = self._backgrounds[mode]
        self._watermark_opacity.setOpacity(0.16 if mode == "text" else 0.12)
        self._update_watermark()

    def _render_watercolor_cache(self) -> None:
        size = self.size()
        if size.isEmpty() or (
            not self._watercolor_cache.isNull() and self._watercolor_cache_size == size
        ):
            return

        cache = QPixmap(size)
        cache.fill(Qt.transparent)
        painter = QPainter(cache)
        painter.setRenderHint(QPainter.Antialiasing, True)
        width, height = float(size.width()), float(size.height())

        # AGY-designed diagonal sky -> pale-blue -> blue-white base.
        diagonal = QLinearGradient(0.0, height, width, 0.0)
        diagonal.setColorAt(0.0, QColor(190, 225, 252, 185))
        diagonal.setColorAt(0.42, QColor(222, 240, 255, 165))
        diagonal.setColorAt(0.72, QColor(240, 248, 255, 175))
        diagonal.setColorAt(1.0, QColor(255, 255, 255, 205))
        painter.fillRect(cache.rect(), diagonal)

        painter.setPen(Qt.NoPen)
        blooms = (
            (0.12, 0.84, 0.48, QColor(104, 189, 245, 48)),
            (0.38, 0.20, 0.38, QColor(165, 214, 250, 38)),
            (0.78, 0.52, 0.46, QColor(205, 235, 255, 35)),
            (0.87, 0.85, 0.30, QColor(244, 184, 215, 25)),
        )
        longest = max(width, height)
        for x_ratio, y_ratio, radius_ratio, color in blooms:
            radius = longest * radius_ratio
            bloom = QRadialGradient(width * x_ratio, height * y_ratio, radius)
            bloom.setColorAt(0.0, color)
            edge = QColor(color)
            edge.setAlpha(0)
            bloom.setColorAt(1.0, edge)
            painter.setBrush(bloom)
            painter.drawEllipse(
                QPointF(width * x_ratio, height * y_ratio), radius, radius * 0.72
            )

        # A fixed number of translucent brush paths keeps the wash organic
        # without area-dependent work or animation timers.
        strokes = (
            ((0.28, 0.28), (0.47, 0.17), (0.69, 0.18), (0.93, 0.08),
             QColor(255, 255, 255, 62), 5.0),
            ((0.58, 0.92), (0.72, 0.85), (0.84, 0.83), (0.98, 0.72),
             QColor(238, 137, 187, 23), 4.0),
        )
        for start, control1, control2, end, color, pen_width in strokes:
            path = QPainterPath(QPointF(width * start[0], height * start[1]))
            path.cubicTo(
                QPointF(width * control1[0], height * control1[1]),
                QPointF(width * control2[0], height * control2[1]),
                QPointF(width * end[0], height * end[1]),
            )
            painter.strokePath(
                path, QPen(color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            )

        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.1, Qt.SolidLine, Qt.RoundCap))
        for x_ratio, y_ratio, radius in (
            (0.08, 0.10, 2.0), (0.21, 0.72, 2.5), (0.43, 0.17, 2.0),
            (0.64, 0.09, 2.5), (0.82, 0.67, 2.0), (0.93, 0.22, 2.5),
        ):
            x, y = width * x_ratio, height * y_ratio
            painter.drawLine(QPointF(x - radius * 2, y), QPointF(x + radius * 2, y))
            painter.drawLine(QPointF(x, y - radius * 2), QPointF(x, y + radius * 2))
        painter.end()
        self._watercolor_cache = cache
        self._watercolor_cache_size = QSize(size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        option = QStyleOption()
        option.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)

        self._render_watercolor_cache()
        if not self._watercolor_cache.isNull():
            painter.drawPixmap(0, 0, self._watercolor_cache)
        painter.end()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._watercolor_cache = QPixmap()
        self._watercolor_cache_size = QSize()
        self._update_watermark()

    def _update_watermark(self) -> None:
        if self._character.isNull():
            self.watermark.clear()
            self.watermark.hide()
            return
        available_height = max(1, int(self.height() * 0.88))
        scaled = self._character.scaledToHeight(available_height, Qt.SmoothTransformation)
        self.watermark.setPixmap(scaled)
        self.watermark.resize(scaled.size())
        self.watermark.move(
            self.width() - scaled.width() + int(scaled.width() * 0.07),
            self.height() - scaled.height() + 4,
        )
        self.watermark.show()
        self.watermark.lower()


class CustomTitleBar(QWidget):
    """Compact title bar that keeps native move/snap behaviour."""

    maximize_requested = Signal()

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self.setObjectName("customTitleBar")
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        icon = QLabel(self)
        icon.setPixmap(QIcon(str(resource_path("assets/app_icon.png"))).pixmap(24, 24))
        icon.setFixedSize(28, 28)
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("猪咪备忘录", self)
        title.setObjectName("titleBarTitle")
        subtitle = QLabel("CHESHIRE · SKY GLASS DECK", self)
        subtitle.setObjectName("titleBarSubtitle")
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 3, 0, 3)
        title_column.setSpacing(0)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        self.minimize_button = self._button("—", "最小化", "titleBarButton")
        self.maximize_button = self._button("□", "最大化", "titleBarButton")
        self.close_button = self._button("×", "关闭到托盘", "titleBarCloseButton")
        self.minimize_button.clicked.connect(window.showMinimized)
        self.maximize_button.clicked.connect(self.maximize_requested.emit)
        self.close_button.clicked.connect(window.close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 5, 0)
        layout.setSpacing(4)
        layout.addWidget(icon)
        layout.addLayout(title_column)
        layout.addStretch(1)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def _button(self, text: str, accessible_name: str, object_name: str) -> QToolButton:
        button = QToolButton(self)
        button.setText(text)
        button.setObjectName(object_name)
        button.setAccessibleName(accessible_name)
        button.setFixedSize(40, 30)
        return button

    def update_window_state(self, maximized: bool) -> None:
        self.maximize_button.setText("❐" if maximized else "□")
        self.maximize_button.setAccessibleName("还原" if maximized else "最大化")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            handle = self._window.windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.maximize_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
