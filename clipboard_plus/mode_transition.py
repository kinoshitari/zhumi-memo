"""Short, interruptible opacity transitions for clipboard modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

if TYPE_CHECKING:
    from .window import ClipboardWindow


class ModeTransitionController(QObject):
    """Fade the active panel out, apply the mode, then fade it back in."""

    FADE_OUT_DURATION_MS = 80
    FADE_IN_DURATION_MS = 90

    def __init__(self, window: "ClipboardWindow") -> None:
        super().__init__(window)
        self.window = window
        self._target_mode: Optional[str] = None
        self._phase: Optional[str] = None
        self._active_widget: Optional[QWidget] = None
        self._active_effect: Optional[QGraphicsOpacityEffect] = None
        self._animation: Optional[QPropertyAnimation] = None

    def is_animating(self) -> bool:
        return self._phase is not None

    def target_mode(self) -> Optional[str]:
        return self._target_mode

    def phase(self) -> Optional[str]:
        return self._phase

    def _panel_for_mode(self, mode: str) -> QWidget:
        return self.window.editor if mode == "editor" else self.window.history_panel

    def _ensure_effect(self, widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if isinstance(effect, QGraphicsOpacityEffect):
            return effect
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        return effect

    def _stop_animation(self) -> None:
        animation = self._animation
        self._animation = None
        if animation is None:
            return
        try:
            animation.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        animation.stop()
        animation.deleteLater()

    @staticmethod
    def _remove_effect(widget: Optional[QWidget]) -> None:
        if widget is not None and widget.graphicsEffect() is not None:
            widget.setGraphicsEffect(None)

    def set_mode(self, mode: str, animated: bool = True) -> None:
        if mode not in ("text", "image", "file", "editor"):
            return
        if mode == self.window._mode and self._phase is None:
            return
        if mode == self._target_mode and self._phase is not None:
            return

        if not animated or not self.window.isVisible():
            self.finish_immediately()
            self.window._apply_mode_state(mode)
            self.window._focus_current_mode()
            return

        self.window._set_mode_buttons(mode)
        if self._phase == "fade_out":
            self._target_mode = mode
            return

        start_opacity = 1.0
        if self._phase == "fade_in":
            start_opacity = self._active_effect.opacity() if self._active_effect else 1.0
            self._stop_animation()

        self._target_mode = mode
        outgoing = self._active_widget or self._panel_for_mode(self.window._mode)
        duration = max(25, round(self.FADE_OUT_DURATION_MS * start_opacity))
        self._start_fade_out(outgoing, start_opacity, duration)

    def _start_fade_out(self, widget: QWidget, opacity: float, duration: int) -> None:
        self._phase = "fade_out"
        self._active_widget = widget
        self._active_effect = self._ensure_effect(widget)
        self._active_effect.setOpacity(opacity)
        animation = QPropertyAnimation(self._active_effect, b"opacity", self)
        animation.setDuration(duration)
        animation.setStartValue(opacity)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InQuad)
        animation.finished.connect(self._fade_out_finished)
        self._animation = animation
        animation.start()

    def _fade_out_finished(self) -> None:
        if self._phase != "fade_out" or self._target_mode is None:
            return
        self._stop_animation()
        if self._active_widget is not None:
            self._remove_effect(self._active_widget)
        target = self._target_mode
        self.window._apply_mode_state(target)
        incoming = self._panel_for_mode(target)
        self._phase = "fade_in"
        self._active_widget = incoming
        self._active_effect = self._ensure_effect(incoming)
        self._active_effect.setOpacity(0.0)
        animation = QPropertyAnimation(self._active_effect, b"opacity", self)
        animation.setDuration(self.FADE_IN_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutQuad)
        animation.finished.connect(self._fade_in_finished)
        self._animation = animation
        animation.start()

    def _fade_in_finished(self) -> None:
        if self._phase != "fade_in":
            return
        self._cleanup()
        self.window._focus_current_mode()

    def _cleanup(self) -> None:
        self._stop_animation()
        self._remove_effect(self.window.history_panel)
        self._remove_effect(self.window.editor)
        self._active_widget = None
        self._active_effect = None
        self._phase = None
        self._target_mode = None

    def finish_immediately(self) -> None:
        target = self._target_mode
        self._cleanup()
        if target is not None and target != self.window._mode:
            self.window._apply_mode_state(target)
