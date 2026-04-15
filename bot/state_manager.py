"""Track high-level bot lifecycle state."""

import time

from bot.config import LEVEL_STABILIZE_TIME
from bot.game_state import GameState


class StateManager:
    def __init__(self):
        self.state = "loading"
        self.last_level = 0
        self.level_timer = time.time()

    def update_state(self, game_state: GameState):
        if game_state.loading:
            self.state = "loading"
            return self.state

        if game_state.level_number != self.last_level:
            self.state = "new_level"
            self.last_level = game_state.level_number
            self.level_timer = time.time()
            return self.state

        if self.state == "new_level":
            if time.time() - self.level_timer >= LEVEL_STABILIZE_TIME:
                self.state = "playing"

        return self.state