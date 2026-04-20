"""Tests for rule-based policy behavior."""

import math
from dataclasses import replace

from bot.config import default_config
from bot.game_state import GameState, TeammateDetection
from bot.policy.rule_policy import RulePolicy


def test_follow_nearest_teammate_decision_respects_follow_radius():
    config = replace(default_config(), turn_sensitivity=0.2, follow_deadzone_px=5)
    policy = RulePolicy(config)

    state = GameState(
        automap_matrix=None,
        teammate_detections=[
            TeammateDetection(position=(500, 500), name="A", confidence=80),
            TeammateDetection(position=(430, 430), name="B", confidence=82),
        ],
        player_position=(400, 400),
        relative_vectors=[(100, 100), (30, 30)],
        level_number=1,
        loading=False,
    )

    action = policy.decide(state)

    dx, dy = 30.0, 30.0
    distance = math.sqrt(dx * dx + dy * dy)
    ratio = (distance - 5.0) / distance
    expected_x = 400 + int(round(dx * ratio * 0.2))
    expected_y = 400 + int(round(dy * ratio * 0.2))

    assert action.stop is False
    assert action.click_target == (expected_x, expected_y)
    assert action.reason == "follow_nearest_teammate"


def test_policy_holds_when_within_follow_radius():
    config = replace(default_config(), active_profile="necromancer")
    policy = RulePolicy(config)

    state = GameState(
        automap_matrix=None,
        teammate_detections=[TeammateDetection(position=(410, 404), name="Lead", confidence=88)],
        player_position=(400, 400),
        relative_vectors=[(10, 4)],
        level_number=1,
        loading=False,
    )

    action = policy.decide(state)

    assert action.hold_move is False
    assert action.click_target is None
    assert action.reason == "within_follow_radius"


def test_policy_stops_on_loading():
    policy = RulePolicy(default_config())
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(0, 0),
        relative_vectors=[],
        level_number=1,
        loading=True,
    )

    action = policy.decide(state)
    assert action.stop is True
    assert action.reason == "loading_screen"
