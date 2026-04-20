"""Default rule-based policy."""

import math

from bot.config import RuntimeConfig
from bot.controller import Action
from bot.game_state import GameState


class RulePolicy:
    def __init__(self, config: RuntimeConfig):
        """Initialize a new `RulePolicy` instance.

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

    def decide(self, state: GameState) -> Action:
        """Decide.

        Parameters:
            state: Parameter carrying runtime state information.

        Local Variables:
            adjusted_dx: Local variable for adjusted dx used in this routine.
            adjusted_dy: Local variable for adjusted dy used in this routine.
            click_target: Local variable for click target used in this routine.
            distance: Local variable for distance used in this routine.
            distance_sq: Local variable for distance sq used in this routine.
            dx: Local variable for dx used in this routine.
            dy: Local variable for dy used in this routine.
            follow_radius: Local variable for follow radius used in this routine.
            move_x: Local variable for move x used in this routine.
            move_y: Local variable for move y used in this routine.
            px: Local variable for px used in this routine.
            py: Local variable for py used in this routine.
            ratio: Local variable for ratio used in this routine.

        Returns:
            A value matching the annotated return type `Action`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if state.loading:
            return Action(stop=True, reason="loading_screen")

        if not state.relative_vectors:
            return Action(hold_move=False, reason="no_teammates")

        dx, dy = min(state.relative_vectors, key=lambda v: (v[0] ** 2) + (v[1] ** 2))
        distance_sq = (dx * dx) + (dy * dy)
        follow_radius = max(0, int(self.config.effective_follow_radius_px))

        if distance_sq <= follow_radius * follow_radius:
            return Action(hold_move=False, reason="within_follow_radius")

        distance = math.sqrt(distance_sq)
        ratio = max(0.0, (distance - follow_radius) / distance)

        adjusted_dx = dx * ratio
        adjusted_dy = dy * ratio

        px, py = state.player_position
        move_x = int(round(adjusted_dx * self.config.effective_turn_sensitivity))
        move_y = int(round(adjusted_dy * self.config.effective_turn_sensitivity))

        if move_x == 0 and move_y == 0:
            return Action(hold_move=False, reason="follow_radius_stable")

        click_target = (px + move_x, py + move_y)
        return Action(click_target=click_target, reason="follow_nearest_teammate")
