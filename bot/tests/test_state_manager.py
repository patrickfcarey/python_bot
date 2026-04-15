"""Tests for state transitions."""

from bot.game_state import GameState
from bot.state_manager import StateManager


def test_loading_to_new_level():
    sm = StateManager()
    state = GameState(
        automap_matrix=None,
        teammate_positions=[],
        player_position=(0, 0),
        relative_vectors=[],
        level_number=1,
        loading=True,
    )

    assert sm.update_state(state) == "loading"

    state.loading = False
    sm.update_state(state)
    assert sm.state == "new_level"