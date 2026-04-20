"""Controller abstractions for input actions."""

from dataclasses import dataclass
from typing import Optional, Tuple

from bot.config import RuntimeConfig

try:
    import pyautogui
except Exception:  # pragma: no cover - import guard for limited envs
    pyautogui = None


@dataclass
class Action:
    click_target: Optional[Tuple[int, int]] = None
    cast_spell: Optional[str] = None
    hold_move: Optional[bool] = None
    stop: bool = False
    reason: str = ""


class Controller:
    def __init__(self, config: RuntimeConfig):
        """Initialize a new `Controller` instance.

        Parameters:
            config: Parameter containing configuration values that guide behavior.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.config = config
        self._backend = pyautogui

        if self._backend is not None:
            self._backend.FAILSAFE = True
            self._backend.PAUSE = 0.01

    def _ensure_backend(self):
        """Internal helper to ensure backend.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if self.config.dry_run:
            return
        if self._backend is None:
            raise RuntimeError(
                "pyautogui is required for live input. Install dependencies or use --dry-run."
            )

    def move_forward(self, on: bool = True):
        """Move forward.

        Parameters:
            on: Parameter for on used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        self._ensure_backend()
        if self.config.dry_run:
            return

        if on:
            self._backend.keyDown(self.config.move_key)
        else:
            self._backend.keyUp(self.config.move_key)

    def stop_all(self):
        """Stop all.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        self._ensure_backend()
        if self.config.dry_run:
            return

        self._backend.keyUp(self.config.move_key)
        self._backend.keyUp(self.config.stop_key)

    def click(self, x: int, y: int):
        """Click.

        Parameters:
            x: Parameter for x used in this routine.
            y: Parameter for y used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        self._ensure_backend()
        if self.config.dry_run:
            return
        self._backend.click(x, y)

    def cast_spell(self, slot: str):
        """Cast spell.

        Parameters:
            slot: Parameter for slot used in this routine.

        Local Variables:
            key: Local variable for key used in this routine.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        self._ensure_backend()
        key = self.config.effective_spell_keys.get(slot)
        if not key:
            return
        if self.config.dry_run:
            return
        self._backend.press(key)

    def execute_action(self, action: Action):
        """Execute action.

        Parameters:
            action: Parameter for action used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        if action.stop:
            self.stop_all()
            return

        if action.hold_move is not None:
            self.move_forward(action.hold_move)

        if action.cast_spell:
            self.cast_spell(action.cast_spell)

        if action.click_target:
            self.click(*action.click_target)
