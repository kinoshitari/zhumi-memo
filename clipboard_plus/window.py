import ctypes
from ctypes import wintypes
from datetime import date, datetime, time, timedelta, timezone
from typing import Tuple

from PySide6.QtCore import QDate, QEvent, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QScrollArea, QSplitter,
    QToolButton, QVBoxLayout, QWidget,
)

from .classification import CATEGORIES, classify_content
from .config import MAX_PANEL_TRANSPARENCY, MIN_PANEL_TRANSPARENCY
from .editor_panel import ScratchEditor
from .mode_transition import ModeTransitionController
from .window_chrome import CustomTitleBar, GlassDeck, screen_resize_hit_test, unpack_screen_point


ID_ROLE = Qt.UserRole
CATEGORY_ROLE = Qt.UserRole + 1
FAVORITE_ROLE = Qt.UserRole + 2
PINNED_ROLE = Qt.UserRole + 3
KIND_ROLE = Qt.UserRole + 4
BASE_TYPE_ROLE = Qt.UserRole + 5
NOTE_ROLE = Qt.UserRole + 6

def _summary(content: str, maximum: int = 220) -> str:
    sample = content[: maximum * 3].replace("\x00", "")
    one_line = " ".join(sample.split())
    if not one_line:
        one_line = "（空白文本）"
    return one_line if len(one_line) <= maximum else one_line[: maximum - 1] + "…"


def _local_time(iso_timestamp: str) -> str:
    try:
        value = datetime.fromisoformat(iso_timestamp)
        if value.tzinfo is not None:
            value = value.astimezone()
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_timestamp


class ClipboardWindow(QWidget):
    search_changed = Signal(str)
    category_changed = Signal(str)
    mode_changed = Signal(str)
    record_activated = Signal(int, str)
    record_preview_requested = Signal(int, str)
    date_changed = Signal()
    action_requested = Signal(str, int, str)
    settings_requested = Signal()
    pin_toggled = Signal(bool)
    create_category_requested = Signal()
    rename_category_requested = Signal(str)
    delete_category_requested = Signal(str)
    editor_copy_text_requested = Signal(str)
    editor_copy_image_requested = Signal(object)
    editor_copy_all_requested = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._mode = "text"
        self._custom_categories = []
        self._date_start = None
        self._date_end = None
        self.setWindowTitle("猪咪备忘录")
        self.resize(860, 620)
        self.setMinimumSize(600, 400)
        # Keep the custom frameless chrome, but also expose the native window
        # capabilities Explorer uses for taskbar-button toggling.  Without a
        # native minimize box Windows may only reactivate this window when its
        # already-active taskbar button is clicked, so no SC_MINIMIZE ever
        # reaches nativeEvent().
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.text_mode = QPushButton("文本", self)
        self.image_mode = QPushButton("图片", self)
        self.file_mode = QPushButton("文件", self)
        self.editor_mode = QPushButton("编辑", self)
        for button in (self.text_mode, self.image_mode, self.file_mode, self.editor_mode):
            button.setCheckable(True)
            button.setObjectName("modeButton")
        self.text_mode.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.text_mode)
        mode_group.addButton(self.image_mode)
        mode_group.addButton(self.file_mode)
        mode_group.addButton(self.editor_mode)
        self.text_mode.clicked.connect(lambda: self.set_mode("text"))
        self.image_mode.clicked.connect(lambda: self.set_mode("image"))
        self.file_mode.clicked.connect(lambda: self.set_mode("file"))
        self.editor_mode.clicked.connect(lambda: self.set_mode("editor"))
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.addWidget(self.text_mode)
        mode_row.addWidget(self.image_mode)
        mode_row.addWidget(self.file_mode)
        mode_row.addWidget(self.editor_mode)
        mode_row.addStretch(1)
        brand = QLabel("CHESHIRE // CLIPBOARD DECK", self)
        brand.setObjectName("brandMark")
        mode_row.addWidget(brand)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("搜索内容、备注或来源程序…")
        self.search.setClearButtonEnabled(True)
        self.search.installEventFilter(self)
        self.date_filter = QComboBox(self)
        for label, value in (
            ("全部日期", "all"), ("今天", "today"), ("昨天", "yesterday"),
            ("最近7天", "7days"), ("最近30天", "30days"), ("自定义…", "custom"),
        ):
            self.date_filter.addItem(label, value)
        self.date_filter.currentIndexChanged.connect(self._date_filter_changed)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.date_filter)
        self.categories = QListWidget(self)
        self.categories.setObjectName("categories")
        self.categories.viewport().setObjectName("categoriesViewport")
        self.categories.setFixedWidth(115)
        self.categories.setContextMenuPolicy(Qt.CustomContextMenu)
        self.categories.customContextMenuRequested.connect(self._category_context_menu)
        self.add_category = QToolButton(self)
        self.add_category.setText("＋ 新建分类")
        self.add_category.clicked.connect(self.create_category_requested.emit)
        self.category_panel = QWidget(self)
        self.category_panel.setObjectName("categoryPanel")
        category_layout = QVBoxLayout(self.category_panel)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(5)
        category_layout.addWidget(self.categories, 1)
        category_layout.addWidget(self.add_category)
        self.category_panel.setFixedWidth(115)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("historyList")
        self.list_widget.viewport().setObjectName("historyViewport")
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.setIconSize(QSize(112, 78))
        self.list_widget.installEventFilter(self)
        self.history_splitter = QSplitter(Qt.Horizontal, self)
        self.history_splitter.setObjectName("historySplitter")
        self.history_splitter.addWidget(self.category_panel)
        self.history_splitter.addWidget(self.list_widget)
        self.history_splitter.setStretchFactor(1, 1)
        self.history_splitter.setCollapsible(0, False)

        self.history_panel = QWidget(self)
        self.history_panel.setObjectName("historyPanel")
        history_layout = QVBoxLayout(self.history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(7)
        history_layout.addLayout(search_row)
        history_layout.addWidget(self.history_splitter, 1)

        self.editor = ScratchEditor(self)
        self.editor.hide()
        self.editor.copy_text_requested.connect(self.editor_copy_text_requested.emit)
        self.editor.copy_image_requested.connect(self.editor_copy_image_requested.emit)
        self.editor.copy_all_requested.connect(self.editor_copy_all_requested.emit)

        self.hint = QLabel("↑/↓ 选择   Enter 复制   Esc 隐藏", self)
        self.hint.setObjectName("hint")
        self.scroll_top_button = QToolButton(self)
        self.scroll_top_button.setText("回到顶部")
        self.scroll_top_button.setObjectName("scrollTopButton")
        self.scroll_top_button.clicked.connect(self.scroll_to_top)
        self.scroll_top_button.setEnabled(False)
        self.pin_window = QToolButton(self)
        self.pin_window.setText("普通窗口")
        self.pin_window.setCheckable(True)
        self.pin_window.setChecked(False)
        self.pin_window.toggled.connect(self._toggle_window_pin)
        self.settings_link = QLabel(
            '<a href="settings" style="color:#52D7E8;text-decoration:none;">设置</a>', self
        )
        self.settings_link.setObjectName("settingsLink")
        self.settings_link.setOpenExternalLinks(False)
        self.window_chrome = QWidget(self)
        self.window_chrome.setObjectName("windowChrome")
        self.title_bar = CustomTitleBar(self, self.window_chrome)
        self.title_bar.maximize_requested.connect(self._toggle_maximized)
        self.content_deck = GlassDeck(self.window_chrome)
        layout = QVBoxLayout(self.content_deck)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(7)
        layout.addLayout(mode_row)
        layout.addWidget(self.history_panel, 1)
        layout.addWidget(self.editor, 1)
        footer = QHBoxLayout()
        footer.addWidget(self.hint)
        footer.addStretch(1)
        footer.addWidget(self.scroll_top_button)
        footer.addWidget(self.pin_window)
        footer.addWidget(self.settings_link)
        layout.addLayout(footer)

        chrome_layout = QVBoxLayout(self.window_chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)
        chrome_layout.addWidget(self.title_bar)
        chrome_layout.addWidget(self.content_deck, 1)
        self._root_layout = QVBoxLayout(self)
        # Keep the visible chrome flush with the native window edge.  The
        # frameless resize hit-test operates on that native edge, so an outer
        # transparent margin would make the border look draggable while the
        # pointer is actually outside the resize zone.
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.addWidget(self.window_chrome)
        self.search.textChanged.connect(self.search_changed.emit)
        self.search.returnPressed.connect(self.activate_current)
        self.categories.currentTextChanged.connect(self.category_changed.emit)
        self.list_widget.itemDoubleClicked.connect(self._preview_item)
        self.list_widget.customContextMenuRequested.connect(self._context_menu)
        self.settings_link.linkActivated.connect(lambda _link: self.settings_requested.emit())
        self._rebuild_categories()
        self._transition_manager = ModeTransitionController(self)
        self._panel_transparency = 0
        self._activation_token = 0
        self._activation_timers = []

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_chrome_state()

    def _sync_chrome_state(self) -> None:
        maximized = self.isMaximized()
        self.title_bar.update_window_state(maximized)
        self._root_layout.setContentsMargins(0, 0, 0, 0)

    def current_mode(self) -> str:
        return self._mode

    def set_panel_transparency(self, value: int) -> None:
        """Apply a readable, adjustable glass surface to the large content panels."""
        value = max(MIN_PANEL_TRANSPARENCY, min(MAX_PANEL_TRANSPARENCY, int(value)))
        self._panel_transparency = value
        opacity = (100 - value) / 100.0
        # Keep the slider mapping literal: 0% transparency is fully opaque,
        # while 100% makes every adjustable content surface fully transparent.
        list_opacity = opacity
        sidebar_opacity = opacity
        editor_opacity = opacity
        drop_opacity = opacity
        self.history_panel.setStyleSheet(
            "QWidget#historyPanel { background-color: transparent; }"
        )
        self.history_splitter.setStyleSheet(
            "QSplitter#historySplitter { background-color: transparent; }"
        )
        self.category_panel.setStyleSheet(
            "QWidget#categoryPanel { background-color: transparent; }"
        )
        self._set_list_surface(
            self.list_widget, "historyList", "historyViewport",
            (255, 255, 255), list_opacity,
        )
        self._set_list_surface(
            self.categories, "categories", "categoriesViewport",
            (240, 247, 255), sidebar_opacity,
        )
        self.editor.text_editor.setStyleSheet(
            "QPlainTextEdit#editorTextInput { background-color: rgba(255, 255, 255, %.2f); }"
            % editor_opacity
        )
        self.editor.image_area.setStyleSheet(
            "QLabel#editorImageDropArea { background-color: rgba(238, 246, 255, %.2f); }"
            % drop_opacity
        )
        self.editor.setStyleSheet(
            "QWidget#scratchEditor { background-color: rgba(245, 250, 255, %.2f); }"
            % opacity
        )
        editor_splitter = self.editor.findChild(QSplitter, "editorSplitter")
        editor_image_panel = self.editor.findChild(QWidget, "editorImagePanel")
        if editor_splitter is not None:
            editor_splitter.setStyleSheet(
                "QSplitter#editorSplitter { background-color: transparent; }"
            )
        if editor_image_panel is not None:
            editor_image_panel.setStyleSheet(
                "QWidget#editorImagePanel { background-color: transparent; }"
            )

    @staticmethod
    def _set_list_surface(
        widget: QListWidget,
        widget_name: str,
        viewport_name: str,
        rgb: Tuple[int, int, int],
        opacity: float,
    ) -> None:
        """Style both an item view and its real painting surface.

        QAbstractScrollArea paints its records on an internal viewport. Styling
        only QListWidget leaves that viewport on the opaque application base,
        which is why the illustration was visible through the sidebar border
        but not through the history rows.
        """
        red, green, blue = rgb
        surface = "rgba(%d, %d, %d, %.2f)" % (red, green, blue, opacity)
        widget.setStyleSheet(
            "QListWidget#%s { background-color: %s; }" % (widget_name, surface)
        )
        viewport = widget.viewport()
        viewport.setAttribute(Qt.WA_StyledBackground, True)
        viewport.setStyleSheet(
            "QWidget#%s { background-color: %s; }" % (viewport_name, surface)
        )

    def panel_transparency(self) -> int:
        return self._panel_transparency

    def set_mode(self, mode: str, animated: bool = True) -> None:
        self._transition_manager.set_mode(mode, animated)

    def _set_mode_buttons(self, mode: str) -> None:
        self.text_mode.setChecked(mode == "text")
        self.image_mode.setChecked(mode == "image")
        self.file_mode.setChecked(mode == "file")
        self.editor_mode.setChecked(mode == "editor")

    def _apply_mode_state(self, mode: str) -> None:
        if mode not in ("text", "image", "file", "editor"):
            return
        if mode == self._mode:
            return
        self._mode = mode
        self._set_mode_buttons(mode)
        self.content_deck.set_mode(mode)
        is_editor = mode == "editor"
        self.history_panel.setVisible(not is_editor)
        self.editor.setVisible(is_editor)
        if is_editor:
            self.hint.setText("Ctrl+V 粘贴   一键复制   Esc 隐藏")
            self.scroll_top_button.setEnabled(False)
            self.mode_changed.emit(mode)
            return
        self.hint.setText("↑/↓ 选择   Enter 复制   Esc 隐藏")
        self.scroll_top_button.setEnabled(self.list_widget.count() > 0)
        self.search.clear()
        placeholders = {
            "text": "搜索内容、备注或来源程序…",
            "image": "搜索图片备注或来源程序…",
            "file": "搜索文件名、路径、备注或来源程序…",
        }
        self.search.setPlaceholderText(placeholders.get(mode, placeholders["text"]))
        self._rebuild_categories()
        self.mode_changed.emit(mode)

    def _focus_current_mode(self) -> None:
        if not self.isVisible() or self.isMinimized():
            return
        if self._mode == "editor":
            self.editor.focus_editor()
        else:
            self.search.setFocus(Qt.ShortcutFocusReason)

    def set_custom_categories(self, categories) -> None:
        selected = self.current_category()
        self._custom_categories = list(categories)
        self._rebuild_categories(selected)

    def _rebuild_categories(self, selected: str = "") -> None:
        self.categories.blockSignals(True)
        self.categories.clear()
        if self._mode == "text":
            builtins = ("全部", "固定", "收藏") + CATEGORIES
        elif self._mode == "image":
            builtins = ("全部图片", "固定", "收藏", "图片")
        else:
            builtins = ("全部文件", "固定", "收藏", "文件")
        for label in builtins + tuple(self._custom_categories):
            self.categories.addItem(label)
        matches = self.categories.findItems(selected, Qt.MatchExactly) if selected else []
        self.categories.setCurrentItem(matches[0] if matches else self.categories.item(0))
        self.categories.blockSignals(False)

    def current_category(self) -> str:
        item = self.categories.currentItem()
        default = "全部图片" if self._mode == "image" else ("全部文件" if self._mode == "file" else "全部")
        return item.text() if item else default

    def set_records(self, records, mode: str) -> None:
        current = self.list_widget.currentItem()
        current_id = current.data(ID_ROLE) if current else None
        self.list_widget.clear()
        selected_row = 0
        for row, record in enumerate(records):
            markers = ("📌 " if record.is_pinned else "") + ("★ " if record.is_favorite else "")
            source = " · " + record.source_app if record.source_app else ""
            metadata = "%s%s · %s" % (record.category, source, _local_time(record.copied_at))
            note_line = "\n备注：" + _summary(record.note, 120) if record.note else ""
            if mode == "image":
                item = QListWidgetItem(markers + "图片" + note_line + "\n" + metadata)
                pixmap = QPixmap()
                if pixmap.loadFromData(record.thumbnail):
                    item.setIcon(QIcon(pixmap))
                base_type = "图片"
            elif mode == "file":
                size = self._format_size(record.byte_size)
                state = {
                    "pending": "正在缓存…", "ready": size, "too_large": "仅保留原始路径",
                    "error": "缓存失败",
                }.get(record.status, size)
                item = QListWidgetItem(markers + "📄 " + record.display_name + note_line + "\n" + metadata + " · " + state)
                tooltip = record.original_path
                if record.error:
                    tooltip += "\n" + record.error
                if record.note:
                    tooltip += "\n\n备注：" + record.note
                item.setToolTip(tooltip)
                base_type = "文件"
            else:
                item = QListWidgetItem(markers + _summary(record.content) + note_line + "\n" + metadata)
                tooltip = record.content[:1000] + ("…" if len(record.content) > 1000 else "")
                if record.note:
                    tooltip += "\n\n备注：" + record.note
                item.setToolTip(tooltip)
                base_type = classify_content(record.content)
            item.setData(ID_ROLE, record.id)
            item.setData(CATEGORY_ROLE, record.category)
            item.setData(FAVORITE_ROLE, record.is_favorite)
            item.setData(PINNED_ROLE, record.is_pinned)
            item.setData(KIND_ROLE, mode)
            item.setData(BASE_TYPE_ROLE, base_type)
            item.setData(NOTE_ROLE, record.note)
            self.list_widget.addItem(item)
            if record.id == current_id:
                selected_row = row
        if self.list_widget.count():
            self.list_widget.setCurrentRow(selected_row)
        self.scroll_top_button.setEnabled(self._mode != "editor" and self.list_widget.count() > 0)

    def scroll_to_top(self) -> None:
        """Reset the non-editor history list to its first record and scroll to the top."""
        if self._mode == "editor":
            return
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            item = self.list_widget.item(0)
            if item is not None:
                self.list_widget.scrollToItem(item, QAbstractItemView.PositionAtTop)
        v_bar = self.list_widget.verticalScrollBar()
        if v_bar is not None:
            v_bar.setValue(v_bar.minimum())

    def _cancel_pending_activations(self) -> None:
        self._activation_token += 1
        for timer in self._activation_timers:
            try:
                timer.stop()
                timer.deleteLater()
            except (RuntimeError, TypeError):
                pass
        self._activation_timers.clear()

    def show_and_activate(self) -> None:
        self.scroll_to_top()
        self._cancel_pending_activations()
        token = self._activation_token

        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        self._force_windows_foreground()
        self._focus_current_mode()
        if self._mode != "editor":
            self.search.selectAll()

        def _delayed_activate(token_val: int) -> None:
            if token_val != self._activation_token:
                return
            if not self.isVisible() or self.isMinimized():
                return
            self._force_windows_foreground()
            if not self.isActiveWindow():
                self.activateWindow()
            self._focus_current_mode()

        for delay in (60, 180):
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda t=token, tm=timer: self._on_activation_timer(t, tm, _delayed_activate)
            )
            self._activation_timers.append(timer)
            timer.start(delay)

    def _on_activation_timer(self, token_val: int, timer: QTimer, callback) -> None:
        if timer in self._activation_timers:
            self._activation_timers.remove(timer)
        timer.deleteLater()
        callback(token_val)

    def is_foreground(self) -> bool:
        """Return whether this exact native window is currently foreground."""
        if not self.isVisible() or self.isMinimized():
            return False
        try:
            user32 = ctypes.windll.user32
            user32.GetForegroundWindow.restype = wintypes.HWND
            return int(user32.GetForegroundWindow() or 0) == int(self.winId())
        except (AttributeError, OSError, TypeError, ValueError):
            return self.isActiveWindow()

    def _force_windows_foreground(self) -> None:
        """Use the Win32 foreground APIs after a registered-hotkey activation."""
        if not self.isVisible() or self.isMinimized():
            return
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetForegroundWindow.restype = wintypes.HWND
            user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            user32.GetWindowThreadProcessId.restype = wintypes.DWORD
            user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.BringWindowToTop.argtypes = [wintypes.HWND]
            user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            user32.SetActiveWindow.argtypes = [wintypes.HWND]
            user32.SetFocus.argtypes = [wintypes.HWND]
            user32.SwitchToThisWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
            user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
            hwnd = wintypes.HWND(int(self.winId()))
            user32.ShowWindowAsync(hwnd, 9)  # SW_RESTORE
            foreground = user32.GetForegroundWindow()
            foreground_process = wintypes.DWORD()
            foreground_thread = (
                user32.GetWindowThreadProcessId(foreground, ctypes.byref(foreground_process))
                if foreground else 0
            )
            current_thread = kernel32.GetCurrentThreadId()
            attached = False
            if foreground_thread and foreground_thread != current_thread:
                attached = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
            try:
                user32.AllowSetForegroundWindow(-1)
                # A synthetic Alt transition is the documented Windows-compatible
                # escape hatch used after RegisterHotKey notifications.
                user32.keybd_event(0x12, 0, 0, 0)
                user32.keybd_event(0x12, 0, 2, 0)
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
                user32.SwitchToThisWindow(hwnd, True)
                user32.SetActiveWindow(hwnd)
                user32.SetFocus(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(current_thread, foreground_thread, False)
        except (AttributeError, OSError, ValueError):
            pass

    def activate_current(self) -> None:
        if self._mode == "editor":
            return
        item = self.list_widget.currentItem()
        if item:
            self._activate_item(item)

    def _activate_item(self, item: QListWidgetItem) -> None:
        self.record_activated.emit(item.data(ID_ROLE), item.data(KIND_ROLE))

    def _preview_item(self, item: QListWidgetItem) -> None:
        self.record_preview_requested.emit(item.data(ID_ROLE), item.data(KIND_ROLE))

    def date_range(self):
        return self._date_start, self._date_end

    def _date_filter_changed(self) -> None:
        selection = self.date_filter.currentData()
        today = date.today()
        if selection == "custom":
            selected = self._ask_custom_dates(today)
            if selected is None:
                self.date_filter.blockSignals(True)
                self.date_filter.setCurrentIndex(0)
                self.date_filter.blockSignals(False)
                selection = "all"
            else:
                start_date, end_date = selected
                self.date_filter.setItemText(
                    self.date_filter.currentIndex(),
                    "%s 至 %s" % (start_date.isoformat(), end_date.isoformat()),
                )
        if selection == "all":
            self._date_start = self._date_end = None
        else:
            if selection == "today":
                start_date, end_date = today, today
            elif selection == "yesterday":
                start_date = end_date = today - timedelta(days=1)
            elif selection == "7days":
                start_date, end_date = today - timedelta(days=6), today
            elif selection == "30days":
                start_date, end_date = today - timedelta(days=29), today
            local_zone = datetime.now().astimezone().tzinfo
            start_local = datetime.combine(start_date, time.min, local_zone)
            end_local = datetime.combine(end_date + timedelta(days=1), time.min, local_zone)
            self._date_start = start_local.astimezone(timezone.utc).isoformat()
            self._date_end = end_local.astimezone(timezone.utc).isoformat()
        self.date_changed.emit()

    def _ask_custom_dates(self, today: date):
        dialog = QDialog(self)
        dialog.setWindowTitle("自定义日期范围")
        start = QDateEdit(QDate(today.year, today.month, today.day), dialog)
        end = QDateEdit(QDate(today.year, today.month, today.day), dialog)
        for editor in (start, end):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd")
        form = QFormLayout()
        form.addRow("开始日期：", start)
        form.addRow("结束日期：", end)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addLayout(form)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return None
        start_date = start.date().toPython()
        end_date = end.date().toPython()
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return start_date, end_date

    @staticmethod
    def _format_size(value: int) -> str:
        number = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if number < 1024 or unit == "GB":
                return "%.1f %s" % (number, unit)
            number /= 1024
        return "0 B"

    def _context_menu(self, position) -> None:
        item = self.list_widget.itemAt(position)
        if not item:
            return
        kind = item.data(KIND_ROLE)
        menu, actions = QMenu(self), {}
        copy_label = "复制文件并隐藏" if kind == "file" else "复制并隐藏"
        actions[menu.addAction(copy_label)] = "copy_hide"
        actions[menu.addAction("复制（保持窗口）")] = "copy"
        menu.addSeparator()
        actions[menu.addAction("取消收藏" if item.data(FAVORITE_ROLE) else "收藏")] = "favorite"
        actions[menu.addAction("取消固定" if item.data(PINNED_ROLE) else "固定到顶部")] = "pin"
        note = item.data(NOTE_ROLE) or ""
        actions[menu.addAction("编辑备注" if note else "添加备注")] = "note"
        if note:
            actions[menu.addAction("复制备注")] = "copy_note"
            if kind == "text":
                actions[menu.addAction("复制备注和文本")] = "copy_note_with_content"
            elif kind == "image":
                actions[menu.addAction("复制备注和图片")] = "copy_note_with_content"
            actions[menu.addAction("清除备注")] = "clear_note"
        move_menu = menu.addMenu("移动到分类")
        target_categories = list(CATEGORIES) if kind == "text" else (["图片"] if kind == "image" else ["文件"])
        target_categories.extend(self._custom_categories)
        for category in target_categories:
            actions[move_menu.addAction(category)] = "move:" + category
        base_type = item.data(BASE_TYPE_ROLE)
        if kind == "text" and base_type == "URL":
            menu.addSeparator()
            actions[menu.addAction("在浏览器中打开")] = "open_url"
            actions[menu.addAction("复制域名")] = "copy_domain"
        elif kind == "text" and base_type == "路径":
            menu.addSeparator()
            actions[menu.addAction("打开文件或文件夹")] = "open_path"
            actions[menu.addAction("打开所在文件夹")] = "open_parent"
        menu.addSeparator()
        if kind == "text":
            actions[menu.addAction("查看完整内容")] = "view"
        elif kind == "image":
            actions[menu.addAction("查看图片")] = "view_image"
        else:
            actions[menu.addAction("打开文件")] = "open_file"
            actions[menu.addAction("另存为…")] = "save_file_as"
        actions[menu.addAction("打开文件所在位置")] = "open_item_location"
        actions[menu.addAction("删除")] = "delete"
        chosen = menu.exec(self.list_widget.mapToGlobal(position))
        if chosen in actions:
            self.action_requested.emit(actions[chosen], item.data(ID_ROLE), kind)

    def _category_context_menu(self, position) -> None:
        item = self.categories.itemAt(position)
        if not item or item.text() not in self._custom_categories:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("重命名分类")
        delete_action = menu.addAction("删除分类")
        chosen = menu.exec(self.categories.mapToGlobal(position))
        if chosen == rename_action:
            self.rename_category_requested.emit(item.text())
        elif chosen == delete_action:
            self.delete_category_requested.emit(item.text())

    def show_full_content(self, content: str) -> None:
        self.create_full_content_dialog(content).exec()

    def create_full_content_dialog(self, content: str) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("完整内容")
        dialog.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        dialog.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        dialog.setSizeGripEnabled(True)
        dialog.resize(820, 600)
        dialog.setMinimumSize(420, 280)
        editor = QPlainTextEdit(dialog)
        editor.setReadOnly(True)
        editor.setPlainText(content)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(editor, 1)
        layout.addWidget(buttons)
        return dialog

    def show_full_image(self, image_data: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_data):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("图片预览")
        dialog.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        dialog.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        dialog.setSizeGripEnabled(True)
        dialog.resize(900, 650)
        dialog.setMinimumSize(420, 280)
        label = QLabel(dialog)
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(pixmap)
        scroll = QScrollArea(dialog)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(label)
        layout = QVBoxLayout(dialog)
        layout.addWidget(scroll)
        dialog.exec()

    def is_pinned(self) -> bool:
        return bool(self.windowFlags() & Qt.WindowStaysOnTopHint)

    def set_pinned(self, pinned: bool) -> None:
        pinned = bool(pinned)
        if self.pin_window.isChecked() != pinned:
            self.pin_window.blockSignals(True)
            self.pin_window.setChecked(pinned)
            self.pin_window.blockSignals(False)
        self._apply_pinned_flag(pinned)

    def _toggle_window_pin(self, pinned: bool) -> None:
        self._apply_pinned_flag(pinned)
        self.pin_toggled.emit(pinned)

    def _apply_pinned_flag(self, pinned: bool) -> None:
        current_flag = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        expected_text = "固定窗口" if pinned else "普通窗口"
        if current_flag == pinned and self.pin_window.text() == expected_text:
            return
        visible = self.isVisible()
        if current_flag != pinned:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, pinned)
        self.pin_window.setText(expected_text)
        if visible and current_flag != pinned:
            self.show()
            self.raise_()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() != QEvent.WindowStateChange:
            return
        # Minimize must remain a real Windows minimize operation so the
        # taskbar button stays present.  Explicit close/Esc/tray actions are
        # the only paths that hide the window to the notification area.
        if self.isMinimized():
            self._cancel_pending_activations()
            if hasattr(self, "_transition_manager"):
                self._transition_manager.finish_immediately()
        elif hasattr(self, "title_bar"):
            self._sync_chrome_state()

    def nativeEvent(self, event_type, message):
        """Restore native edge/corner resizing for the frameless Windows window."""
        try:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0084 and not self.isMaximized():  # WM_NCHITTEST
                user32 = ctypes.windll.user32
                rect = wintypes.RECT()
                hwnd = wintypes.HWND(int(self.winId()))
                if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return super().nativeEvent(event_type, message)
                get_dpi = getattr(user32, "GetDpiForWindow", None)
                dpi = int(get_dpi(hwnd)) if get_dpi is not None else 96
                screen_x, screen_y = unpack_screen_point(int(msg.lParam))
                hit = screen_resize_hit_test(
                    screen_x, screen_y, rect.left, rect.top, rect.right, rect.bottom, dpi
                )
                if hit is not None:
                    return True, hit
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        return super().nativeEvent(event_type, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        if self._mode != "editor" and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.activate_current()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.hide()
                return True
            if watched is self.search and key in (Qt.Key_Up, Qt.Key_Down):
                count = self.list_widget.count()
                if count:
                    row = self.list_widget.currentRow()
                    row = max(0, row - 1) if key == Qt.Key_Up else min(count - 1, row + 1)
                    self.list_widget.setCurrentRow(row)
                    self.list_widget.scrollToItem(self.list_widget.currentItem())
                return True
            if watched is self.list_widget and key in (Qt.Key_Return, Qt.Key_Enter):
                self.activate_current()
                return True
        return super().eventFilter(watched, event)

    def hideEvent(self, event) -> None:
        self._cancel_pending_activations()
        if hasattr(self, "_transition_manager"):
            self._transition_manager.finish_immediately()
        super().hideEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._cancel_pending_activations()
        if hasattr(self, "_transition_manager"):
            self._transition_manager.finish_immediately()
        self.hide()
        event.ignore()
