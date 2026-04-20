"""Track high-level bot lifecycle state."""

import enum
import time

from bot.game_state import GameState


class BotLifecycle(str, enum.Enum):
    LOADING = "loading"
    NEW_LEVEL = "new_level"
    PLAYING = "playing"


class StateManager:
    def __init__(self, level_stabilize_time: float, now_fn=time.monotonic):
        """Initialize a new `StateManager` instance.

        Parameters:
            level_stabilize_time: Parameter for level stabilize time used in this routine.
            now_fn: Parameter for now fn used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._stabilize_time = level_stabilize_time
        self._now_fn = now_fn
        self.state: BotLifecycle = BotLifecycle.LOADING
        self.last_level = 0
        self.level_timer = self._now_fn()

    def update_state(self, game_state: GameState) -> BotLifecycle:
        """Update state.

        Parameters:
            game_state: Parameter carrying runtime state information.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `BotLifecycle`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        if game_state.loading:
            self.state = BotLifecycle.LOADING
            return self.state

        if game_state.level_number != self.last_level:
            self.state = BotLifecycle.NEW_LEVEL
            self.last_level = game_state.level_number
            self.level_timer = self._now_fn()
            return self.state

        if self.state == BotLifecycle.NEW_LEVEL:
            if self._now_fn() - self.level_timer >= self._stabilize_time:
                self.state = BotLifecycle.PLAYING

        return self.state