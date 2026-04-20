"""Tests for pickit matching."""

from bot.game_state import GroundItemDetection
from bot.pickit import PickitDatabase, PickitRule


def test_pickit_matches_gold_by_threshold():
    db = PickitDatabase(rules=(), pickup_gold=True, min_gold_amount=500, gold_priority=35)

    low_gold = GroundItemDetection(position=(100, 100), label="321 Gold", confidence=80.0, is_gold=True, gold_amount=321)
    high_gold = GroundItemDetection(position=(120, 100), label="1200 Gold", confidence=80.0, is_gold=True, gold_amount=1200)

    assert db.match_detection(low_gold) is None

    matched = db.match_detection(high_gold)
    assert matched is not None
    assert matched.rule_name == "gold"


def test_pickit_matches_item_rule_by_contains_token():
    db = PickitDatabase(
        rules=(
            PickitRule(name="runes", contains=("rune",), priority=90, enabled=True),
            PickitRule(name="gems", contains=("gem",), priority=60, enabled=True),
        ),
        pickup_gold=False,
        min_gold_amount=0,
    )

    det = GroundItemDetection(position=(320, 240), label="Tal Rune", confidence=85.0, is_gold=False, gold_amount=0)
    matched = db.match_detection(det)

    assert matched is not None
    assert matched.priority == 90
    assert matched.rule_name == "runes"


def test_pickit_pick_candidates_sorts_by_priority_then_confidence():
    db = PickitDatabase(
        rules=(
            PickitRule(name="charms", contains=("charm",), priority=80, enabled=True),
            PickitRule(name="gems", contains=("gem",), priority=70, enabled=True),
        ),
        pickup_gold=False,
        min_gold_amount=0,
    )

    detections = [
        GroundItemDetection(position=(200, 200), label="Small Charm", confidence=60.0),
        GroundItemDetection(position=(210, 205), label="Chipped Gem", confidence=95.0),
        GroundItemDetection(position=(220, 210), label="Large Charm", confidence=92.0),
    ]

    matches = db.pick_candidates(detections)

    assert len(matches) == 3
    assert matches[0].rule_name == "charms"
    assert matches[0].item.label == "Large Charm"