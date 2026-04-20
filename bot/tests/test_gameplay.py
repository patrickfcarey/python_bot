"""Tests for timed gameplay scanner/planner routines."""

from dataclasses import replace

import numpy as np

from bot.config import default_config
from bot.game_state import (
    BeltStatus,
    EnemyDetection,
    EnemyTrack,
    GameState,
    GroundItemDetection,
    PickitMatch,
    ResourceStatus,
)
from bot.gameplay import GameplayActionPlanner, GameplayScanner
from bot.pickit import PickitDatabase, PickitRule


class FakeVision:
    def __init__(self):
        self.resource_calls = 0
        self.belt_calls = 0
        self.ground_calls = 0

    def scan_resource_status(self, _frame):
        self.resource_calls += 1
        return ResourceStatus(health_ratio=0.9, mana_ratio=0.9, confidence=0.7)

    def scan_belt_status(self, _frame):
        self.belt_calls += 1
        return BeltStatus(health_slots_filled=6, mana_slots_filled=6, rejuvenation_slots_filled=2, total_slots=16, confidence=0.6)

    def scan_ground_item_labels(self, _frame, max_labels=12):
        self.ground_calls += 1
        return [
            GroundItemDetection(position=(350, 260), label="Tal Rune", confidence=88.0),
            GroundItemDetection(position=(360, 262), label="1200 Gold", confidence=92.0, is_gold=True, gold_amount=1200),
        ][:max_labels]


def _state() -> GameState:
    return GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 300),
        relative_vectors=[],
        loading=False,
    )


def test_gameplay_scanner_runs_tasks_on_independent_timers():
    cfg = replace(
        default_config(),
        resource_scan_interval_s=0.10,
        belt_scan_interval_s=0.40,
        ground_item_scan_interval_s=0.55,
        enable_pickit=True,
    )
    db = PickitDatabase(rules=(PickitRule(name="runes", contains=("rune",), priority=90, enabled=True),))
    scanner = GameplayScanner(config=cfg, pickit_db=db)
    vision = FakeVision()
    frame = np.zeros((600, 800, 3), dtype=np.uint8)

    state = scanner.enrich_state(vision, frame, _state(), now_monotonic=0.0)
    assert vision.resource_calls == 1
    assert vision.belt_calls == 1
    assert vision.ground_calls == 1
    assert len(state.pickit_matches) == 2

    scanner.enrich_state(vision, frame, _state(), now_monotonic=0.05)
    assert vision.resource_calls == 1
    assert vision.belt_calls == 1
    assert vision.ground_calls == 1

    scanner.enrich_state(vision, frame, _state(), now_monotonic=0.12)
    assert vision.resource_calls == 2
    assert vision.belt_calls == 1
    assert vision.ground_calls == 1


def test_gameplay_planner_uses_potion_with_cooldown():
    cfg = replace(
        default_config(),
        enable_belt_management=True,
        health_potion_trigger_ratio=0.50,
        mana_potion_trigger_ratio=0.20,
        potion_action_cooldown_s=0.75,
        health_potion_action_slot="belt_health",
    )
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.resource_status = ResourceStatus(health_ratio=0.40, mana_ratio=0.90, confidence=0.8)

    first = planner.decide(state, now_monotonic=10.0)
    second = planner.decide(state, now_monotonic=10.2)
    third = planner.decide(state, now_monotonic=10.9)

    assert first is not None and first.cast_spell == "belt_health"
    assert second is None
    assert third is not None and third.cast_spell == "belt_health"


def test_gameplay_planner_picks_highest_priority_pickit_match():
    cfg = replace(
        default_config(),
        enable_pickit=True,
        enable_item_pickup=True,
        enable_gold_pickup=False,
        pickup_disable_when_enemies=True,
        pickup_click_cooldown_s=0.20,
    )
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.pickit_matches = [
        PickitMatch(
            item=GroundItemDetection(position=(450, 300), label="Chipped Gem", confidence=90.0),
            priority=65,
            rule_name="gems",
        ),
        PickitMatch(
            item=GroundItemDetection(position=(430, 310), label="Tal Rune", confidence=80.0),
            priority=95,
            rule_name="runes",
        ),
    ]

    action = planner.decide(state, now_monotonic=2.0)

    assert action is not None
    assert action.click_target == (430, 310)
    assert action.reason == "pickit_pickup_runes"

def test_gameplay_planner_exposes_active_threat_snapshot_from_tracks():
    cfg = default_config()
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.enemy_tracks = [
        EnemyTrack(
            track_id=4,
            position=(420, 305),
            lost_frames=0,
            danger_priority=4,
            danger_label="high",
            danger_tags=("archer",),
            combat_relevant=True,
        )
    ]

    snapshot = planner.active_threat_snapshot(state)

    assert len(snapshot) == 1
    assert snapshot[0]["source"] == "track"
    assert snapshot[0]["danger_priority"] == 4
    assert snapshot[0]["danger_label"] == "high"
    assert snapshot[0]["danger_tags"] == ("archer",)


def test_gameplay_planner_exposes_active_threat_snapshot_from_detections_when_no_tracks():
    cfg = default_config()
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.enemy_detections = [
        EnemyDetection(
            position=(410, 290),
            danger_priority=3,
            danger_label="medium",
            danger_tags=("unclassified_enemy",),
            combat_relevant=True,
        )
    ]

    snapshot = planner.active_threat_snapshot(state)

    assert len(snapshot) == 1
    assert snapshot[0]["source"] == "detection"
    assert snapshot[0]["id"] is None
    assert snapshot[0]["danger_priority"] == 3
    assert snapshot[0]["danger_tags"] == ("unclassified_enemy",)

def test_gameplay_planner_respects_allow_potions_override():
    cfg = replace(
        default_config(),
        enable_belt_management=True,
        health_potion_trigger_ratio=0.50,
        potion_action_cooldown_s=0.10,
    )
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.resource_status = ResourceStatus(health_ratio=0.30, mana_ratio=0.90, confidence=0.8)

    action = planner.decide(state, now_monotonic=1.0, allow_potions=False)

    assert action is None


def test_gameplay_planner_respects_allow_pickups_override():
    cfg = replace(
        default_config(),
        enable_pickit=True,
        enable_item_pickup=True,
        enable_gold_pickup=False,
        pickup_disable_when_enemies=False,
        pickup_click_cooldown_s=0.10,
    )
    planner = GameplayActionPlanner(cfg)
    state = _state()
    state.resource_status = ResourceStatus(health_ratio=0.90, mana_ratio=0.90, confidence=0.9)
    state.pickit_matches = [
        PickitMatch(
            item=GroundItemDetection(position=(410, 302), label="Tal Rune", confidence=90.0),
            priority=95,
            rule_name="runes",
        )
    ]

    blocked = planner.decide(state, now_monotonic=2.0, allow_pickups=False)
    allowed = planner.decide(state, now_monotonic=2.2, allow_pickups=True)

    assert blocked is None
    assert allowed is not None
    assert allowed.click_target == (410, 302)
    assert allowed.reason == "pickit_pickup_runes"
