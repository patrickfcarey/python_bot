"""Thread-safe command queue plus runtime override state."""

from __future__ import annotations

from queue import Empty, Queue
from threading import Lock
from typing import Optional

from bot.controller import Action


class CommandModule:
    """Stores one-shot action commands and persistent runtime overrides."""

    def __init__(self):
        self._queue: Queue[Action] = Queue()
        self._lock = Lock()

        self._paused = False
        self._combat_enabled_override: Optional[bool] = None
        self._pickup_enabled_override: Optional[bool] = None
        self._potion_enabled_override: Optional[bool] = None

    def add_command(self, cmd: Action):
        """Queue a one-shot action command."""
        self._queue.put(cmd)

    def get_next(self) -> Optional[Action]:
        """Pop the next queued action command, if any."""
        if self._queue.empty():
            return None
        return self._queue.get_nowait()

    def size(self) -> int:
        """Return number of queued one-shot commands."""
        return self._queue.qsize()

    def clear_pending_commands(self) -> int:
        """Drop all queued commands and return how many were removed."""
        removed = 0
        while True:
            try:
                self._queue.get_nowait()
                removed += 1
            except Empty:
                break
        return removed

    def set_paused(self, paused: bool):
        """Enable or disable manual pause mode."""
        with self._lock:
            self._paused = bool(paused)

    def is_paused(self) -> bool:
        """Read current manual pause mode."""
        with self._lock:
            return bool(self._paused)

    def set_combat_enabled_override(self, enabled: Optional[bool]):
        """Set combat behavior override (`None` means default behavior)."""
        with self._lock:
            self._combat_enabled_override = None if enabled is None else bool(enabled)

    def is_combat_enabled(self, default_enabled: bool) -> bool:
        """Resolve current combat-enabled value against default."""
        with self._lock:
            if self._combat_enabled_override is None:
                return bool(default_enabled)
            return bool(self._combat_enabled_override)

    def set_pickup_enabled_override(self, enabled: Optional[bool]):
        """Set pickup behavior override (`None` means default behavior)."""
        with self._lock:
            self._pickup_enabled_override = None if enabled is None else bool(enabled)

    def is_pickup_enabled(self, default_enabled: bool) -> bool:
        """Resolve current pickup-enabled value against default."""
        with self._lock:
            if self._pickup_enabled_override is None:
                return bool(default_enabled)
            return bool(self._pickup_enabled_override)

    def set_potion_enabled_override(self, enabled: Optional[bool]):
        """Set potion behavior override (`None` means default behavior)."""
        with self._lock:
            self._potion_enabled_override = None if enabled is None else bool(enabled)

    def is_potion_enabled(self, default_enabled: bool) -> bool:
        """Resolve current potion-enabled value against default."""
        with self._lock:
            if self._potion_enabled_override is None:
                return bool(default_enabled)
            return bool(self._potion_enabled_override)

    def reset_overrides(self):
        """Reset pause/combat/pickup/potion overrides back to defaults."""
        with self._lock:
            self._paused = False
            self._combat_enabled_override = None
            self._pickup_enabled_override = None
            self._potion_enabled_override = None
