# tests/test_rule_policy.py

import pytest
from game_state import GameState
from policy.rule_policy import RulePolicy
from controller import Action

def test_follow_teammate_decision():
    state = GameState(
        automap_matrix=None,
        teammate_positions=[(500, 500)],
        player_position=(400, 400),
        relative_vectors=[(100, 100)],
        level_number=1,
        loading=False
    )
    policy = RulePolicy()
    action = policy.decide(state)
    assert isinstance(action, Action)
    assert action.click_target == (400 + int(100*0.2), 400 + int(100*0.2))