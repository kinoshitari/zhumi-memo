"""Zhumi Memo Cheshire-inspired light sky-glass desktop theme module for PySide6.

Visual direction:
- Sky blue, ice blue, and blue-white luminous gradients (#EAF3FD -> #F3F8FE -> #E4F0FC)
- Translucent glass-like surfaces and panels (rgba(255, 255, 255, 0.85))
- Sparkling ice & sky blue accents (#2B98E8 / #42B0FF)
- Playful Cheshire rose-pink highlights (#F07AA6 / #F89EC1 / #D85888)
- Warm Royal Navy gold accents (#E8A838 / #F5C358 / #D48D1B)
- Crisp deep navy text for high contrast and Chinese readability (#182A4A / #4D6B94)
- Compact information density and clear state styling.
"""

from typing import Any

# Core Palette Constants - Cheshire Light Sky-Glass Theme
COLOR_SKY_BASE = "#EAF3FD"
COLOR_SKY_SURFACE = "#F3F8FE"
COLOR_SKY_PANEL = "#F5FAFF"
COLOR_SKY_CARD = "#FFFFFF"
COLOR_SKY_BORDER = "#B8D4F0"
COLOR_SKY_BORDER_MUTED = "#D0E1F4"
COLOR_SKY_HOVER = "#DEF0FD"
COLOR_SKY_SELECTED = "#D5EBFF"

COLOR_CYAN_ACCENT = "#2B98E8"
COLOR_CYAN_HOVER = "#42B0FF"
COLOR_CYAN_ACTIVE = "#1876BD"
COLOR_CYAN_MUTED = "#D5EBFF"

COLOR_ROSE_ACCENT = "#F07AA6"
COLOR_ROSE_HOVER = "#F89EC1"
COLOR_ROSE_ACTIVE = "#D85888"
COLOR_ROSE_MUTED = "#FDE8F1"

COLOR_GOLD_ACCENT = "#E8A838"
COLOR_GOLD_HOVER = "#F7CA6E"
COLOR_GOLD_DEEP = "#D48D1B"

COLOR_TEXT_PRIMARY = "#182A4A"
COLOR_TEXT_MUTED = "#4D6B94"
COLOR_TEXT_HINT = "#6A86AA"
COLOR_TEXT_DISABLED = "#A0B4CC"

COLOR_BG_DISABLED = "#EDF3FA"
COLOR_BORDER_DISABLED = "#D8E4F2"

APP_STYLESHEET: str = """
/* ==========================================================================
   Zhumi Memo - Cheshire Sky-Glass Theme (Light Edition)
   Inspired by Azur Lane Cheshire (柴郡 - 冰雪公主 / Maid)
   Core Palette:
     - Sky Blue Gradient Base: #EAF3FD -> #F3F8FE -> #E4F0FC
     - Translucent Glass Surfaces: rgba(255, 255, 255, 0.85) / rgba(240, 247, 255, 0.9)
     - Ice & Sky Blue Accents: #2B98E8 / #42B0FF / #1876BD
     - Cheshire Rose-Pink Highlights: #F07AA6 / #F89EC1 / #D85888
     - Royal Navy Warm Gold Accents: #E8A838 / #F5C358 / #D48D1B
     - Crisp Contrast Deep Navy Text: #182A4A / #4D6B94 / #6A86AA
   ========================================================================== */

/* --- Orchestrator Frameless Window & Custom Title Bar --- */
#windowChrome {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EAF3FD, stop:0.5 #F3F8FE, stop:1 #E4F0FC);
    border: 1px solid rgba(160, 205, 250, 0.85);
    border-radius: 8px;
}

#customTitleBar {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(232, 244, 255, 0.85));
    border-bottom: 1px solid #CFE2F5;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 2px 6px;
}

#titleBarTitle {
    color: #182A4A;
    font-size: 13px;
    font-weight: 700;
    padding-left: 4px;
}

#titleBarSubtitle {
    color: #4D6B94;
    font-size: 11px;
    font-weight: 500;
    padding-left: 6px;
}

#titleBarButton {
    background-color: transparent;
    color: #2E4870;
    border: none;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 12px;
}

#titleBarButton:hover {
    background-color: rgba(215, 235, 255, 0.85);
    color: #1E7CC8;
}

#titleBarButton:pressed {
    background-color: rgba(185, 215, 250, 0.95);
    color: #15629F;
}

#titleBarCloseButton {
    background-color: transparent;
    color: #2E4870;
    border: none;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 12px;
}

#titleBarCloseButton:hover {
    background-color: #FA5252;
    color: #FFFFFF;
}

#titleBarCloseButton:pressed {
    background-color: #E03131;
    color: #FFFFFF;
}

#contentDeck {
    background-color: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(184, 212, 240, 0.8);
    border-radius: 6px;
}

#cheshireWatermark {
    background-color: transparent;
    color: rgba(43, 152, 232, 0.12);
}

/* --- Base & Window Structure --- */
QWidget {
    background-color: #F0F6FC;
    color: #182A4A;
    font-size: 13px;
    selection-background-color: #42B0FF;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EAF3FD, stop:0.5 #F3F8FE, stop:1 #E4F0FC);
    color: #182A4A;
}

QDialog {
    background-color: #F0F6FC;
    color: #182A4A;
}

/* --- Labels & Links --- */
QLabel {
    color: #182A4A;
    background-color: transparent;
}

QLabel:disabled {
    color: #A0B4CC;
}

QLabel#hint {
    color: #6A86AA;
    font-size: 11px;
}

QLabel#settingsLink {
    color: #2B98E8;
}

/* --- Text Input Fields --- */
QLineEdit {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 6px 9px;
    selection-background-color: #42B0FF;
    selection-color: #FFFFFF;
}

QLineEdit:hover {
    border: 1px solid #7BB8EB;
    background-color: #FFFFFF;
}

QLineEdit:focus {
    border: 1px solid #2B98E8;
    background-color: #FFFFFF;
}

QLineEdit:read-only {
    background-color: rgba(238, 245, 253, 0.85);
    color: #4D6B94;
    border: 1px solid #D0E1F4;
}

QLineEdit:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border: 1px solid #D8E4F2;
}

QPlainTextEdit, QTextEdit {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #42B0FF;
    selection-color: #FFFFFF;
}

QPlainTextEdit:hover, QTextEdit:hover {
    border: 1px solid #7BB8EB;
}

QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #2B98E8;
    background-color: #FFFFFF;
}

QPlainTextEdit:read-only, QTextEdit:read-only {
    background-color: rgba(238, 245, 253, 0.85);
    color: #4D6B94;
    border: 1px solid #D0E1F4;
}

QPlainTextEdit:disabled, QTextEdit:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border: 1px solid #D8E4F2;
}

/* --- Key Sequence & Date Editors --- */
QKeySequenceEdit {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 6px 9px;
}

QKeySequenceEdit:focus {
    border: 1px solid #2B98E8;
}

QDateEdit {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 5px 8px;
}

QDateEdit:hover {
    border: 1px solid #7BB8EB;
}

QDateEdit:focus {
    border: 1px solid #2B98E8;
}

QDateEdit:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border: 1px solid #D8E4F2;
}

QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #B8D4F0;
    background-color: #F0F6FD;
}

QDateEdit::drop-down:hover {
    background-color: #E0EFFD;
}

/* --- PushButtons & ToolButtons --- */
QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #EAF2FB);
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 5px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #DEF0FD);
    border-color: #42B0FF;
    color: #1E7CC8;
}

QPushButton:pressed {
    background-color: #D2E7FB;
    border-color: #2B98E8;
    color: #15629F;
}

QPushButton:focus {
    border-color: #2B98E8;
}

QPushButton:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38A8F5, stop:1 #208FE0);
    border: 1px solid #1E82D0;
    color: #FFFFFF;
    font-weight: bold;
}

QPushButton:checked:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4EB4F8, stop:1 #2B96E8);
    border-color: #248DE0;
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border-color: #D8E4F2;
}

QToolButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #EAF2FB);
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 4px 10px;
}

QToolButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #DEF0FD);
    border-color: #42B0FF;
    color: #1E7CC8;
}

QToolButton:pressed {
    background-color: #D2E7FB;
    border-color: #2B98E8;
    color: #15629F;
}

QToolButton:focus {
    border-color: #2B98E8;
}

QToolButton:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38A8F5, stop:1 #208FE0);
    border: 1px solid #1E82D0;
    color: #FFFFFF;
    font-weight: bold;
}

QToolButton:checked:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4EB4F8, stop:1 #2B96E8);
    border-color: #248DE0;
    color: #FFFFFF;
}

QToolButton:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border-color: #D8E4F2;
}

/* --- List Widgets & Items --- */
QListWidget {
    background-color: rgba(255, 255, 255, 0.76);
    color: #182A4A;
    border: 1px solid #C4DCF4;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    border-bottom: 1px solid #E6F0FA;
    padding: 7px 8px;
    color: #182A4A;
}

QListWidget::item:hover {
    background-color: rgba(225, 240, 255, 0.75);
    color: #15325B;
}

QListWidget::item:selected {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D5EBFF, stop:1 #EAF4FF);
    color: #0C2852;
    border-left: 3px solid #2B98E8;
    font-weight: 500;
}

QListWidget::item:selected:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #C8E4FE, stop:1 #E2EFFF);
    color: #0C2852;
}

QListWidget::item:disabled {
    color: #A0B4CC;
    background-color: transparent;
}

/* Categories Sidebar Panel */
QListWidget#categories {
    background-color: rgba(240, 247, 255, 0.76);
    border: 1px solid #C4DCF4;
}

QListWidget#categories::item {
    border-bottom: none;
    padding: 6px 8px;
    margin: 1px 2px;
    border-radius: 3px;
    color: #4D6B94;
}

QListWidget#categories::item:hover {
    background-color: #E2F0FD;
    color: #F07AA6;
}

QListWidget#categories::item:selected {
    background-color: #D7ECFF;
    color: #1E78C2;
    font-weight: bold;
    border-left: 3px solid #F07AA6;
}

/* --- Combo Box --- */
QComboBox {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 5px 24px 5px 8px;
    min-height: 18px;
}

QComboBox:hover {
    border-color: #42B0FF;
}

QComboBox:focus {
    border-color: #2B98E8;
}

QComboBox:on {
    border-color: #2B98E8;
}

QComboBox:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border-color: #D8E4F2;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #B8D4F0;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #F0F6FD;
}

QComboBox::drop-down:hover {
    background-color: #E0EFFD;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    selection-background-color: #D7ECFF;
    selection-color: #0C2852;
    outline: none;
    padding: 2px;
}

/* --- Spin Box --- */
QSpinBox {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 4px;
    padding: 5px 8px;
}

QSpinBox:hover {
    border-color: #7BB8EB;
}

QSpinBox:focus {
    border-color: #2B98E8;
}

QSpinBox:disabled {
    background-color: #EDF3FA;
    color: #A0B4CC;
    border-color: #D8E4F2;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #B8D4F0;
    border-bottom: 1px solid #B8D4F0;
    border-top-right-radius: 4px;
    background-color: #F0F6FD;
}

QSpinBox::up-button:hover {
    background-color: #E0EFFD;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #B8D4F0;
    border-bottom-right-radius: 4px;
    background-color: #F0F6FD;
}

QSpinBox::down-button:hover {
    background-color: #E0EFFD;
}

/* --- Check Box --- */
QCheckBox {
    color: #182A4A;
    spacing: 7px;
}

QCheckBox:hover {
    color: #208FD8;
}

QCheckBox:disabled {
    color: #A0B4CC;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #A8CAEC;
    border-radius: 3px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #2B98E8;
    background-color: #F0F7FF;
}

QCheckBox::indicator:checked {
    background-color: #2B98E8;
    border-color: #2B98E8;
}

QCheckBox::indicator:checked:hover {
    background-color: #42B0FF;
    border-color: #42B0FF;
}

QCheckBox::indicator:disabled {
    border-color: #D8E4F2;
    background-color: #EDF3FA;
}

/* --- Context Menu --- */
QMenu {
    background-color: rgba(255, 255, 255, 0.96);
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
    color: #182A4A;
    background-color: transparent;
}

QMenu::item:selected {
    background-color: #D7ECFF;
    color: #1E78C2;
}

QMenu::item:disabled {
    color: #A0B4CC;
    background-color: transparent;
}

QMenu::separator {
    height: 1px;
    background-color: #E0EDF8;
    margin: 4px 6px;
}

/* --- ScrollBar --- */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #C0D6EC;
    min-height: 24px;
    border-radius: 4px;
    margin: 1px;
}

QScrollBar::handle:vertical:hover {
    background-color: #74B5EB;
}

QScrollBar::handle:vertical:pressed {
    background-color: #F07AA6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #C0D6EC;
    min-width: 24px;
    border-radius: 4px;
    margin: 1px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #74B5EB;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #F07AA6;
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
    background-color: rgba(240, 248, 255, 0.96);
    color: #182A4A;
    border: 1px solid #E8A838;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
}

/* --- Splitter & Separators --- */
QSplitter {
    background-color: transparent;
}

QSplitter::handle {
    background-color: #D4E4F5;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #42B0FF;
}

QFrame[frameShape="4"], QFrame[frameShape="5"],
QFrame[frameShape="HLine"], QFrame[frameShape="VLine"] {
    border: none;
    background-color: #DCE8F5;
    height: 1px;
    width: 1px;
}

/* --- ScrollArea & GraphicsView --- */
QScrollArea, QGraphicsView {
    background-color: rgba(248, 252, 255, 0.85);
    border: 1px solid #C4DCF4;
    border-radius: 4px;
}

/* --- Calendar Widget --- */
QCalendarWidget QWidget {
    background-color: #F5FAFF;
    color: #182A4A;
}

QCalendarWidget QTableView {
    background-color: #FFFFFF;
    selection-background-color: #D7ECFF;
    selection-color: #0C2852;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #182A4A;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #A0B4CC;
}

QCalendarWidget QToolButton {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
    border-radius: 3px;
    padding: 3px 6px;
}

QCalendarWidget QToolButton:hover {
    background-color: #DEF0FD;
    border-color: #42B0FF;
    color: #1E7CC8;
}

QCalendarWidget QSpinBox {
    background-color: #FFFFFF;
    color: #182A4A;
    border: 1px solid #B8D4F0;
}

/* --- Zhumi Memo identity & editor deck --- */
QLabel#brandMark {
    color: #D48D1B;
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
    background-color: rgba(245, 250, 255, 0.9);
    border: 1px solid #B8D4F0;
    border-radius: 7px;
}

QLabel#editorHeading {
    color: #1E82D0;
    font-size: 18px;
    font-weight: 700;
    padding: 2px 4px 0px 4px;
}

QLabel#editorDescription, QLabel#editorImageInfo {
    color: #4D6B94;
    padding: 0px 4px;
}

QPlainTextEdit#editorTextInput {
    background-color: #FFFFFF;
    color: #182A4A;
    selection-background-color: #F8C0D5;
    selection-color: #182A4A;
    border: 2px solid #B8D4F0;
    border-radius: 6px;
    padding: 10px;
    font-size: 14px;
}

QPlainTextEdit#editorTextInput:focus {
    border-color: #2B98E8;
}

QLabel#editorImageDropArea {
    background-color: rgba(238, 246, 255, 0.75);
    color: #6A86AA;
    border: 2px dashed #9AC2E8;
    border-radius: 7px;
    padding: 9px;
}

QLabel#editorImageDropArea:hover {
    color: #1E82D0;
    border-color: #2B98E8;
    background-color: #E2F0FE;
}

QPushButton#editorPrimaryAction {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38A8F5, stop:1 #208FE0);
    color: #FFFFFF;
    border: 1px solid #1E82D0;
    font-weight: 700;
}

QPushButton#editorPrimaryAction:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4EB4F8, stop:1 #2B96E8);
    border-color: #E8A838;
}

QPushButton#editorClearAction {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FFF2F6);
    color: #D85888;
    border: 1px solid #F5A8C4;
}

QPushButton#editorClearAction:hover {
    background-color: #FFE6EE;
    color: #C2386E;
    border-color: #E8659B;
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
