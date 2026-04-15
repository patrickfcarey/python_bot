"""Default rule-based policy."""

from bot.config import TURN_SENSITIVITY
from bot.controller import Action
from bot.game_state import GameState


class RulePolicy:
    def decide(self, state: GameState) -> Action:
        action = Action()
        if state.relative_vectors:
            dx, dy = state.relative_vectors[0]  # follow first teammate
            px, py = state.player_position
            move_x = int(dx * TURN_SENSITIVITY)
            move_y = int(dy * TURN_SENSITIVITY)
            action.click_target = (px + move_x, py + move_y)
        return action