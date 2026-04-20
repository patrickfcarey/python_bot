"""Unit tests for shadow-policy scoring utilities."""

from bot.shadow_policy import (
    ShadowPolicyScorer,
    infer_observed_action_category,
    predict_shadow_action_category,
)


def _event_payload(**overrides):
    payload = {
        "frame_id": 1,
        "lifecycle_state": "playing",
        "action_stop": False,
        "action_reason": "within_follow_radius",
        "action_source": "rule_policy",
        "action_cast_spell": None,
        "combat_mode": "idle",
        "teammate_count": 1,
        "enemy_detection_count": 0,
        "enemy_track_count": 0,
        "ground_item_count": 0,
        "gold_item_count": 0,
        "pickit_match_count": 0,
        "health_ratio": 0.95,
        "mana_ratio": 0.80,
        "max_danger_priority": 0,
    }
    payload.update(overrides)
    return payload


def test_predict_shadow_action_category_handles_core_paths():
    assert predict_shadow_action_category(_event_payload(health_ratio=0.22))[0] == "recover"
    assert predict_shadow_action_category(_event_payload(enemy_track_count=3, max_danger_priority=4))[0] == "combat"
    assert predict_shadow_action_category(_event_payload(pickit_match_count=2))[0] == "loot"
    assert predict_shadow_action_category(_event_payload(teammate_count=2))[0] == "follow"
    assert predict_shadow_action_category(_event_payload(teammate_count=0))[0] == "idle"


def test_infer_observed_action_category_respects_action_context():
    assert infer_observed_action_category(_event_payload(action_stop=True)) == "stop"
    assert infer_observed_action_category(_event_payload(action_reason="use_health_potion_now")) == "recover"
    assert infer_observed_action_category(_event_payload(action_reason="pickup_gold_stack")) == "loot"
    assert infer_observed_action_category(_event_payload(combat_mode="combat_stub_necromancer")) == "combat"
    assert infer_observed_action_category(_event_payload(action_reason="follow_nearest_teammate")) == "follow"
    assert infer_observed_action_category(_event_payload(teammate_count=0, action_reason="idle_no_action")) == "idle"


def test_shadow_policy_scorer_tracks_agreement_disagreement_and_skips():
    scorer = ShadowPolicyScorer(enabled=True, include_loading=False, min_confidence=0.60, max_disagreement_examples=5)

    agree_meta = scorer.score_event(_event_payload(action_reason="follow_nearest_teammate"))
    assert agree_meta is not None
    assert agree_meta["agreement"] is True

    low_conf_meta = scorer.score_event(_event_payload(teammate_count=0, action_reason="idle_no_action"))
    assert low_conf_meta is None

    loading_meta = scorer.score_event(_event_payload(lifecycle_state="loading", action_stop=True, action_reason="loading_screen"))
    assert loading_meta is None

    disagree_meta = scorer.score_event(_event_payload(action_reason="attack_primary_target"))
    assert disagree_meta is not None
    assert disagree_meta["agreement"] is False

    summary = scorer.summary()
    assert summary.seen_events == 4
    assert summary.evaluated_events == 2
    assert summary.agreement_count == 1
    assert summary.disagreement_count == 1
    assert summary.skipped_loading == 1
    assert summary.skipped_low_confidence == 1
    assert "combat->follow" in summary.confusion_pairs
    assert len(summary.disagreement_examples) == 1


def test_shadow_policy_can_include_loading_when_enabled():
    scorer = ShadowPolicyScorer(enabled=True, include_loading=True, min_confidence=0.0)

    metadata = scorer.score_event(
        _event_payload(
            lifecycle_state="loading",
            action_stop=True,
            action_reason="loading_screen",
            teammate_count=0,
        )
    )

    assert metadata is not None
    assert metadata["predicted_category"] == "stop"
    assert metadata["observed_category"] == "stop"
    assert metadata["agreement"] is True

    summary = scorer.summary()
    assert summary.evaluated_events == 1
    assert summary.skipped_loading == 0
