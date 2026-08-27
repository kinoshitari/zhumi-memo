"""Zhumi Memo Cheshire-inspired desktop theme module for PySide6.

Visual direction:
- Dark naval blue structure (#0B1734 / #13264A)
- Luminous cyan/teal controls (#52D7E8)
- Restrained rose-pink accents (#F3A6C8)
- Warm gold highlights (#F5D58A)
- Soft off-white content surfaces and text (#F7FAFF)
- Compact density, high contrast, readable Chinese text.
"""

from typing import Any

# Core Palette Constants
COLOR_NAVAL_DARK = "#0B1734"
COLOR_NAVAL_SURFACE = "#13264A"
COLOR_NAVAL_PANEL = "#0F2040"
COLOR_NAVAL_CARD = "#0C1938"
COLOR_NAVAL_BORDER = "#254885"
COLOR_NAVAL_BORDER_MUTED = "#1E3A68"
COLOR_NAVAL_HOVER = "#18335E"
COLOR_NAVAL_SELECTED = "#19436E"

COLOR_CYAN_ACCENT = "#52D7E8"
COLOR_CYAN_HOVER = "#7DE5F2"
COLOR_CYAN_ACTIVE = "#36B8C9"
COLOR_CYAN_MUTED = "#163B60"

COLOR_ROSE_ACCENT = "#F3A6C8"
COLOR_ROSE_HOVER = "#F7BFD6"
COLOR_ROSE_ACTIVE = "#D882A8"
COLOR_ROSE_MUTED = "#3D2034"

COLOR_GOLD_ACCENT = "#F5D58A"
COLOR_GOLD_HOVER = "#FCE2A6"

COLOR_TEXT_PRIMARY = "#F7FAFF"
COLOR_TEXT_MUTED = "#B2C4DF"
COLOR_TEXT_HINT = "#7E95BA"
COLOR_TEXT_DISABLED = "#4B5F7D"

COLOR_BG_DISABLED = "#09132B"
COLOR_BORDER_DISABLED = "#1A2E50"

APP_STYLESHEET: str = """
/* ==========================================================================
   Zhumi Memo - Cheshire-Inspired Desktop Theme
   Core Palette:
     - Naval Base: #0B1734
     - Naval Surface: #13264A
     - Luminous Cyan: #52D7E8
     - Rose-Pink Accent: #F3A6C8
     - Warm Gold Highlight: #F5D58A
     - Off-White Text/Surface: #F7FAFF
   ========================================================================== */

/* --- Base & Window Structure --- */
QWidget {
    background-color: #0B1734;
    color: #F7FAFF;
    font-size: 13px;
    selection-background-color: #52D7E8;
    selection-color: #0B1734;
}

QMainWindow {
    background-color: #0B1734;
    color: #F7FAFF;
}

QDialog {
    background-color: #0B1734;
    color: #F7FAFF;
}

/* --- Labels & Links --- */
QLabel {
    color: #F7FAFF;
    background-color: transparent;
}

QLabel:disabled {
    color: #4B5F7D;
}

QLabel#hint {
    color: #7E95BA;
    font-size: 11px;
}

/* --- Text Input Fields --- */
QLineEdit {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 6px 9px;
}

QLineEdit:hover {
    border: 1px solid #3B6BB0;
}

QLineEdit:focus {
    border: 1px solid #52D7E8;
    background-color: #162E58;
}

QLineEdit:read-only {
    background-color: #0F1F3E;
    color: #B2C4DF;
    border: 1px solid #1E3A68;
}

QLineEdit:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border: 1px solid #1A2E50;
}

QPlainTextEdit, QTextEdit {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 6px 8px;
}

QPlainTextEdit:hover, QTextEdit:hover {
    border: 1px solid #3B6BB0;
}

QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #52D7E8;
    background-color: #162E58;
}

QPlainTextEdit:read-only, QTextEdit:read-only {
    background-color: #0F1F3E;
    color: #B2C4DF;
    border: 1px solid #1E3A68;
}

QPlainTextEdit:disabled, QTextEdit:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border: 1px solid #1A2E50;
}

/* --- Key Sequence & Date Editors --- */
QKeySequenceEdit {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 6px 9px;
}

QKeySequenceEdit:focus {
    border: 1px solid #52D7E8;
}

QDateEdit {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 5px 8px;
}

QDateEdit:hover {
    border: 1px solid #3B6BB0;
}

QDateEdit:focus {
    border: 1px solid #52D7E8;
}

QDateEdit:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border: 1px solid #1A2E50;
}

QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #254885;
    background-color: #13264A;
}

QDateEdit::drop-down:hover {
    background-color: #18335E;
}

/* --- PushButtons & ToolButtons --- */
QPushButton {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 5px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #18335E;
    border-color: #52D7E8;
    color: #7DE5F2;
}

QPushButton:pressed {
    background-color: #0B1734;
    border-color: #36B8C9;
    color: #52D7E8;
}

QPushButton:focus {
    border-color: #52D7E8;
}

QPushButton:checked {
    background-color: #163B60;
    border: 1px solid #52D7E8;
    color: #52D7E8;
    font-weight: bold;
}

QPushButton:checked:hover {
    background-color: #1D4C7C;
    border-color: #7DE5F2;
    color: #7DE5F2;
}

QPushButton:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border-color: #1A2E50;
}

QToolButton {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 4px 10px;
}

QToolButton:hover {
    background-color: #18335E;
    border-color: #52D7E8;
    color: #7DE5F2;
}

QToolButton:pressed {
    background-color: #0B1734;
    border-color: #36B8C9;
    color: #52D7E8;
}

QToolButton:focus {
    border-color: #52D7E8;
}

QToolButton:checked {
    background-color: #163B60;
    border: 1px solid #52D7E8;
    color: #52D7E8;
    font-weight: bold;
}

QToolButton:checked:hover {
    background-color: #1D4C7C;
    border-color: #7DE5F2;
    color: #7DE5F2;
}

QToolButton:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border-color: #1A2E50;
}

/* --- List Widgets & Items --- */
QListWidget {
    background-color: #0F2040;
    color: #F7FAFF;
    border: 1px solid #1E3A68;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    border-bottom: 1px solid #182F56;
    padding: 7px 8px;
    color: #F7FAFF;
}

QListWidget::item:hover {
    background-color: #18335E;
    color: #F7FAFF;
}

QListWidget::item:selected {
    background-color: #19436E;
    color: #F7FAFF;
    border-left: 3px solid #52D7E8;
}

QListWidget::item:selected:hover {
    background-color: #1F5082;
    color: #F7FAFF;
}

QListWidget::item:disabled {
    color: #4B5F7D;
    background-color: transparent;
}

/* Categories Sidebar Panel */
QListWidget#categories {
    background-color: #0C1938;
    border: 1px solid #1E3A68;
}

QListWidget#categories::item {
    border-bottom: none;
    padding: 6px 8px;
    margin: 1px 2px;
    border-radius: 3px;
    color: #B2C4DF;
}

QListWidget#categories::item:hover {
    background-color: #172F58;
    color: #F3A6C8;
}

QListWidget#categories::item:selected {
    background-color: #1D3A6A;
    color: #52D7E8;
    font-weight: bold;
    border-left: 3px solid #F3A6C8;
}

/* --- Combo Box --- */
QComboBox {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 5px 24px 5px 8px;
    min-height: 18px;
}

QComboBox:hover {
    border-color: #52D7E8;
}

QComboBox:focus {
    border-color: #52D7E8;
}

QComboBox:on {
    border-color: #52D7E8;
}

QComboBox:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border-color: #1A2E50;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #254885;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #13264A;
}

QComboBox::drop-down:hover {
    background-color: #18335E;
}

QComboBox QAbstractItemView {
    background-color: #0E1C3A;
    color: #F7FAFF;
    border: 1px solid #254885;
    selection-background-color: #19436E;
    selection-color: #52D7E8;
    outline: none;
    padding: 2px;
}

/* --- Spin Box --- */
QSpinBox {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 4px;
    padding: 5px 8px;
}

QSpinBox:hover {
    border-color: #3B6BB0;
}

QSpinBox:focus {
    border-color: #52D7E8;
}

QSpinBox:disabled {
    background-color: #09132B;
    color: #4B5F7D;
    border-color: #1A2E50;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #254885;
    border-bottom: 1px solid #254885;
    border-top-right-radius: 4px;
    background-color: #13264A;
}

QSpinBox::up-button:hover {
    background-color: #18335E;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #254885;
    border-bottom-right-radius: 4px;
    background-color: #13264A;
}

QSpinBox::down-button:hover {
    background-color: #18335E;
}

/* --- Check Box --- */
QCheckBox {
    color: #F7FAFF;
    spacing: 7px;
}

QCheckBox:hover {
    color: #7DE5F2;
}

QCheckBox:disabled {
    color: #4B5F7D;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #254885;
    border-radius: 3px;
    background-color: #0B1734;
}

QCheckBox::indicator:hover {
    border-color: #52D7E8;
    background-color: #13264A;
}

QCheckBox::indicator:checked {
    background-color: #52D7E8;
    border-color: #52D7E8;
}

QCheckBox::indicator:checked:hover {
    background-color: #7DE5F2;
    border-color: #7DE5F2;
}

QCheckBox::indicator:disabled {
    border-color: #1A2E50;
    background-color: #09132B;
}

/* --- Context Menu --- */
QMenu {
    background-color: #0E1C3A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
    color: #F7FAFF;
    background-color: transparent;
}

QMenu::item:selected {
    background-color: #19436E;
    color: #52D7E8;
}

QMenu::item:disabled {
    color: #4B5F7D;
    background-color: transparent;
}

QMenu::separator {
    height: 1px;
    background-color: #1E3A68;
    margin: 4px 6px;
}

/* --- ScrollBar --- */
QScrollBar:vertical {
    background-color: #0B1734;
    width: 10px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #1E3A68;
    min-height: 24px;
    border-radius: 4px;
    margin: 1px;
}

QScrollBar::handle:vertical:hover {
    background-color: #52D7E8;
}

QScrollBar::handle:vertical:pressed {
    background-color: #F3A6C8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: #0B1734;
    height: 10px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #1E3A68;
    min-width: 24px;
    border-radius: 4px;
    margin: 1px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #52D7E8;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #F3A6C8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* --- ToolTip --- */
QToolTip {
    background-color: #0B1734;
    color: #F7FAFF;
    border: 1px solid #F5D58A;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
}

/* --- Splitter & Separators --- */
QSplitter {
    background-color: transparent;
}

QSplitter::handle {
    background-color: #182F56;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #52D7E8;
}

QFrame[frameShape="4"], QFrame[frameShape="5"],
QFrame[frameShape="HLine"], QFrame[frameShape="VLine"] {
    border: none;
    background-color: #182F56;
    height: 1px;
    width: 1px;
}

/* --- ScrollArea & GraphicsView --- */
QScrollArea, QGraphicsView {
    background-color: #0B1734;
    border: 1px solid #1E3A68;
    border-radius: 4px;
}

/* --- Calendar Widget --- */
QCalendarWidget QWidget {
    background-color: #0E1C3A;
    color: #F7FAFF;
}

QCalendarWidget QTableView {
    background-color: #0E1C3A;
    selection-background-color: #19436E;
    selection-color: #52D7E8;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #F7FAFF;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #4B5F7D;
}

QCalendarWidget QToolButton {
    background-color: #13264A;
    color: #F7FAFF;
    border: 1px solid #254885;
    border-radius: 3px;
    padding: 3px 6px;
}

QCalendarWidget QToolButton:hover {
    background-color: #18335E;
    border-color: #52D7E8;
    color: #7DE5F2;
}

QCalendarWidget QSpinBox {
    background-color: #13264A;
    color: #F7FAFF;
}

/* --- Zhumi Memo identity & editor deck --- */
QLabel#brandMark {
    color: #F5D58A;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 2px 5px;
}

QPushButton#modeButton {
    min-width: 58px;
    border-radius: 0px;
    padding: 7px 14px;
}

QWidget#scratchEditor {
    background-color: #0F2040;
    border: 1px solid #254885;
    border-radius: 7px;
}

QLabel#editorHeading {
    color: #52D7E8;
    font-size: 18px;
    font-weight: 700;
    padding: 2px 4px 0px 4px;
}

QLabel#editorDescription, QLabel#editorImageInfo {
    color: #B2C4DF;
    padding: 0px 4px;
}

QPlainTextEdit#editorTextInput {
    background-color: #F7FAFF;
    color: #13264A;
    selection-background-color: #F3A6C8;
    selection-color: #0B1734;
    border: 2px solid #254885;
    border-radius: 6px;
    padding: 10px;
    font-size: 14px;
}

QPlainTextEdit#editorTextInput:focus {
    border-color: #52D7E8;
}

QLabel#editorImageDropArea {
    background-color: #0B1734;
    color: #7E95BA;
    border: 2px dashed #3B6BB0;
    border-radius: 7px;
    padding: 9px;
}

QLabel#editorImageDropArea:hover {
    color: #52D7E8;
    border-color: #52D7E8;
    background-color: #102A4E;
}

QPushButton#editorPrimaryAction {
    background-color: #52D7E8;
    color: #0B1734;
    border-color: #7DE5F2;
    font-weight: 700;
}

QPushButton#editorPrimaryAction:hover {
    background-color: #7DE5F2;
    border-color: #F5D58A;
}

QPushButton#editorClearAction {
    color: #F3A6C8;
    border-color: #D882A8;
}

QPushButton#editorClearAction:hover {
    background-color: #3D2034;
    color: #F7BFD6;
}
""".strip()


def apply_app_theme(widget: Any) -> None:
    """Apply the Zhumi Cheshire-inspired stylesheet to a widget or application.

    This function safely applies `APP_STYLESHEET` to any QWidget, QDialog,
    QMainWindow, QApplication, or widget-like object exposing `setStyleSheet`.
    If the target object is None or does not implement `setStyleSheet`, this
    function returns safely without raising exceptions or mutating other state.

    Args:
        widget: A QWidget, QApplication, or compatible object with a setStyleSheet method.
    """
    if widget is not None and hasattr(widget, "setStyleSheet"):
        widget.setStyleSheet(APP_STYLESHEET)
