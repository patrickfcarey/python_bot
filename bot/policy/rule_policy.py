# policy/rule_policy.py

from game_state import GameState
from controller import Action
from config import TURN_SENSITIVITY

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