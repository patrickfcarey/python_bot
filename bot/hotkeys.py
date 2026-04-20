"""Low-overhead runtime hotkey polling helpers for global pause/resume."""

from __future__ import annotations

import ctypes
import time
from typing import Callable, Optional

VK_CONTROL = 0x11
VK_SPACE = 0x20


class PauseHotkeyMonitor:
    """Polls Ctrl+Space and emits a single toggle event per keypress."""

    def __init__(
        self,
        enabled: bool = True,
        debounce_seconds: float = 0.30,
        key_reader: Optional[Callable[[int], bool]] = None,
    ):
        self._enabled = bool(enabled)
        self._debounce_seconds = max(0.0, float(debounce_seconds))
        self._key_reader = key_reader if key_reader is not None else self._default_key_reader
        self._combo_was_down = False
        self._last_toggle_monotonic = -1_000_000.0

    @property
    def enabled(self) -> bool:
        """Return whether the pause hotkey monitor is active."""
        return bool(self._enabled)

    def poll(self, now_monotonic: Optional[float] = None) -> bool:
        """Return True once when Ctrl+Space is newly pressed and debounce has elapsed."""
        if not self._enabled:
            return False

        now = time.monotonic() if now_monotonic is None else float(now_monotonic)

        combo_down = self._key_reader(VK_CONTROL) and self._key_reader(VK_SPACE)
        should_toggle = (
            combo_down
            and not self._combo_was_down
            and (now - self._last_toggle_monotonic) >= self._debounce_seconds
        )

        self._combo_was_down = combo_down

        if should_toggle:
            self._last_toggle_monotonic = now
            return True
        return False

    @staticmethod
    def _default_key_reader(virtual_key_code: int) -> bool:
        """Read global key-down state using Win32 `GetAsyncKeyState`."""
        try:
            state = ctypes.windll.user32.GetAsyncKeyState(int(virtual_key_code))
        except Exception:
            return False
        return bool(state & 0x8000)
