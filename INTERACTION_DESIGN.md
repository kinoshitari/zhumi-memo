# ZhumiMemo 4.3.7 Interaction System Design

This document details the interaction system implemented for ZhumiMemo 4.3.6, covering module transitions, window activation and foregrounding, hide-to-tray semantics, and rapid input interruption policies.

---

## 1. Module Transition Architecture

### 1.1 State Machine

Module switching is managed by `ModeTransitionController` (`clipboard_plus/mode_transition.py`). It coordinates opacity transitions between the active content container (`history_panel` for text, image, file modes; `editor` for editor mode) and updates the Cheshire watercolor background deck (`content_deck`).

```
                    ┌─────────────────────────┐
                    │          Idle           │
                    └───────────┬─────────────┘
                                │ set_mode(target)
                                ▼
                    ┌─────────────────────────┐
       Interrupted  │         FadeOut         │
    ┌───────────────┤ (duration: 80ms InQuad) │
    │ update target └───────────┬─────────────┘
    └──────────────►            │ on_finished: _apply_mode_state(target)
                                ▼
                    ┌─────────────────────────┐
       Interrupted  │         FadeIn          │
    ┌───────────────┤ (duration: 90ms OutQuad)│
    │ reverse to 0  └───────────┬─────────────┘
    └──────────────►            │ on_finished: _cleanup(), focus
                                ▼
                    ┌─────────────────────────┐
                    │          Idle           │
                    └─────────────────────────┘
```

1. **Idle State**:
   - No animations active (`is_animating() == False`).
   - Graphics opacity effects are removed from both `history_panel` and `editor` to ensure crisp raster rendering.
   - Mode buttons reflect the active mode.

2. **FadeOut Phase**:
   - Duration: 80 ms nominal, easing: `QEasingCurve.InQuad`.
   - The outgoing panel's opacity animates from initial opacity (1.0) to 0.0.
   - Mode selection button acknowledges immediately on click (`_set_mode_buttons(mode)`).

3. **State Handoff (`_fade_out_finished`)**:
   - Outgoing panel effect is removed.
   - `_apply_mode_state(target)` is called synchronously:
     - Updates window `_mode` and deck mode `content_deck.set_mode(target)`.
     - Sets visibility (`history_panel.setVisible(not is_editor)`, `editor.setVisible(is_editor)`).
     - Configures search bar placeholder / category tree.
     - Emits `mode_changed(target)` to refresh data from SQLite.
   - Incoming panel is initialized at opacity 0.0.

4. **FadeIn Phase**:
   - Duration: 90 ms nominal, easing: `QEasingCurve.OutQuad`.
   - Incoming panel's opacity animates from 0.0 to 1.0.

5. **Completion (`_fade_in_finished`)**:
   - `_cleanup()` is called: stops animation objects, deletes them via `deleteLater()`, removes `QGraphicsOpacityEffect` from both containers, and resets state variables.
   - Focus is asserted on the appropriate control (`search` or scratch editor).

---

## 2. Interruption & Coalescing Policy

To ensure high responsiveness and zero visual glitches under rapid user input:

- **Interruption during `FadeOut`**:
  - The controller simply updates `_target_mode = new_mode`.
  - The in-flight fade-out continues smoothly to 0.0 without restarting or jumping.
  - Intermediate modes are bypassed entirely: no redundant layout swapping, category rebuilds, or database queries occur for superseded modes.
  - When fade-out finishes, the latest target mode is applied.

- **Interruption during `FadeIn`**:
  - The controller captures current opacity: `start_opacity = active_effect.opacity()`.
  - The fade-in animation is stopped and disconnected.
  - A proportional fade-out begins immediately from `start_opacity` down to 0.0 with scaled duration: `max(25, round(80 * start_opacity))`.
  - Once 0.0 is reached, the latest target mode is applied and fades in.

- **Same-Target Reselection**:
  - Reselecting the current active mode while idle or reselecting the target mode currently being transitioned to is an immediate no-op.

- **Immediate Settle (`finish_immediately`)**:
  - Stops animations, disconnects finished signals, deletes animation objects, clears graphics effects, and synchronously applies the target mode.
  - Invoked automatically when the window is hidden (`hideEvent`), closed (`closeEvent`), minimized (`changeEvent`), or when `animated=False` is passed.

---

## 3. Timing & Easing Choices

| Phase | Nominal Duration | Easing Curve | Rationale |
|---|---|---|---|
| **Fade Out** | 80 ms | `QEasingCurve.InQuad` | Accelerates out quickly so content vanishes cleanly before swapping state. |
| **Fade In** | 90 ms | `QEasingCurve.OutQuad` | Decelerates smoothly into 1.0 for a soft, polished visual landing. |
| **Total** | 170 ms | Composite | Sits squarely in the target 120–220 ms perceived responsiveness range. |

---

## 4. Window Lifecycle & Windows OS Integration

### 4.1 Activation Token & Coalesced Retries

Activating a frameless window on Windows across hotkeys and tray triggers requires coordinating Win32 APIs (`SetForegroundWindow`, `AttachThreadInput`, `keybd_event` Alt-escape).

To eliminate focus races where delayed activation timers fire after a newer hide/minimize action:

1. **Generation Token (`_activation_token`)**:
   - An integer token increments on every `show_and_activate()`, `hide()`, `hideEvent()`, `closeEvent()`, and minimization in `changeEvent()`.
   - Pending timer instances (`_activation_timers`) are stopped and deleted.
2. **Guarded Timers**:
   - Retries scheduled at 60 ms and 180 ms check `token_val == self._activation_token` and `self.isVisible() and not self.isMinimized()`.
   - If the window was hidden or minimized during those intervals, the timer aborts cleanly without touching OS focus or un-minimizing the window.
3. **Guarded Win32 Calls (`_force_windows_foreground`)**:
   - Immediate guard `if not self.isVisible() or self.isMinimized(): return` prevents Win32 `ShowWindowAsync(hwnd, SW_RESTORE)` from resurrecting minimized or hidden windows.

### 4.2 Taskbar Minimization vs. Hide to Tray

- **Taskbar Minimize**:
  - Clicking the taskbar button or the titlebar minimize button performs native minimization (`showMinimized()`).
  - The window maintains `isVisible() == True` and `isMinimized() == True`, keeping the taskbar button visible on Windows.
  - Normal minimize does NOT trigger hide-to-tray.
- **Explicit Hide-to-Tray**:
  - `Esc` key, titlebar close button (`×`), `copy_and_hide()`, and tray icon click (when foreground) explicitly call `hide()`.
  - Hiding cancels all pending activation timers and finishes mode transitions immediately.
- **Alt+V Hotkey**:
  - Calls `ClipboardController.show_window()` -> `refresh()` + `show_and_activate()`.
  - Always restores/foregrounds the window; never toggles to hidden.
- **Tray Icon Activation**:
  - When `is_foreground()` is True: hides the window to tray.
  - When `is_foreground()` is False (hidden, minimized, or obscured): restores and foregrounds via `show_window()`.
