# tests/test_state_manager.py
from state_manager import StateManager
from game_state import GameState

def test_loading_to_new_level():
    sm = StateManager()
    state = GameState(None, [], (0,0), 1, loading=True)
    assert sm.update_state(state) == "loading"
    state.loading = False
    sm.update_state(state)
    assert sm.state == "new_level"