"""Tests for lifecycle state transitions."""

from bot.game_state import GameState
from bot.state_manager import BotLifecycle, StateManager


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def test_loading_to_new_level_to_playing():
    clock = FakeClock(now=10.0)
    manager = StateManager(level_stabilize_time=2.0, now_fn=clock)

    loading_state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(0, 0),
        relative_vectors=[],
        level_number=1,
        loading=True,
    )

    assert manager.update_state(loading_state) == BotLifecycle.LOADING

    loading_state.loading = False
    assert manager.update_state(loading_state) == BotLifecycle.NEW_LEVEL

    clock.now = 13.0
    assert manager.update_state(loading_state) == BotLifecycle.PLAYING