# state_manager.py

import time
from game_state import GameState

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
            if time.time() - self.level_timer >= 2.0:  # LEVEL_STABILIZE_TIME
                self.state = "playing"
        return self.state