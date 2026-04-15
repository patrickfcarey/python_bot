"""Tests for rule-based follow behavior."""

from bot.controller import Action
from bot.game_state import GameState
from bot.policy.rule_policy import RulePolicy


def test_follow_teammate_decision():
    state = GameState(
        automap_matrix=None,
        teammate_positions=[(500, 500)],
        player_position=(400, 400),
        relative_vectors=[(100, 100)],
        level_number=1,
        loading=False,
    )
    policy = RulePolicy()
    action = policy.decide(state)

    assert isinstance(action, Action)
    assert action.click_target == (400 + int(100 * 0.2), 400 + int(100 * 0.2))