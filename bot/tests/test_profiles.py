"""Tests for character behavior profile support."""

from argparse import Namespace
from dataclasses import replace

import pytest

from bot.config import default_config
from bot.game_state import GameState, TeammateDetection
from bot.main import make_config
from bot.policy.rule_policy import RulePolicy


def test_profiles_available_and_default_legacy():
    cfg = default_config()
    names = cfg.available_profiles()

    assert "legacy" in names
    assert "sorc_tele" in names
    assert "necromancer" in names
    assert cfg.active_profile == "legacy"


def test_make_config_applies_profile_override():
    args = Namespace(profile="necromancer")

    cfg = make_config(args)

    assert cfg.active_profile == "necromancer"
    assert cfg.effective_class_name == "necromancer"
    assert cfg.effective_prefer_combat is True
    assert cfg.effective_necromancer_config is not None
    assert cfg.effective_follow_radius_px == cfg.effective_necromancer_config.follow_radius


def test_make_config_rejects_unknown_profile():
    args = Namespace(profile="does_not_exist")

    with pytest.raises(ValueError):
        make_config(args)


def test_rule_policy_uses_profile_sensitivity_when_selected():
    legacy_cfg = replace(default_config(), active_profile="legacy", turn_sensitivity=0.2, follow_deadzone_px=5)
    sorc_cfg = replace(default_config(), active_profile="sorc_tele")

    state = GameState(
        automap_matrix=None,
        teammate_detections=[TeammateDetection(position=(500, 400), name="Leader", confidence=90)],
        player_position=(400, 400),
        relative_vectors=[(100, 0)],
        level_number=1,
        loading=False,
    )

    legacy_action = RulePolicy(legacy_cfg).decide(state)
    sorc_action = RulePolicy(sorc_cfg).decide(state)

    assert legacy_action.click_target == (419, 400)
    assert sorc_action.click_target == (427, 400)


def test_make_config_applies_async_vision_overrides():
    args = Namespace(sync_vision=True, vision_max_age_ms=95.0)

    cfg = make_config(args)

    assert cfg.vision_async_enabled is False
    assert cfg.vision_async_max_result_age_ms == 95.0


def test_make_config_applies_async_worker_overrides_and_clamps_pending():
    args = Namespace(vision_workers=3, vision_max_pending=1)

    cfg = make_config(args)

    assert cfg.vision_async_workers == 3
    assert cfg.vision_async_max_pending_jobs == 3


def test_make_config_applies_observer_overrides():
    args = Namespace(
        observer_off=True,
        observer_event_queue=2048,
        observer_image_queue=48,
        observer_batch_size=96,
        observer_flush_ms=120,
        observer_sample_fps=2.5,
        observer_high_threat_min_danger=5,
        observer_shadow_off=True,
        observer_shadow_min_confidence=0.77,
        observer_shadow_include_loading=True,
    )

    cfg = make_config(args)

    assert cfg.observer_enabled is False
    assert cfg.observer_event_queue_size == 2048
    assert cfg.observer_image_queue_size == 48
    assert cfg.observer_event_batch_size == 96
    assert cfg.observer_flush_interval_ms == 120
    assert cfg.observer_full_frame_sample_fps == 2.5
    assert cfg.observer_high_threat_min_danger == 5
    assert cfg.observer_shadow_enabled is False
    assert cfg.observer_shadow_min_confidence == 0.77
    assert cfg.observer_shadow_include_loading is True


def test_make_config_applies_chat_command_overrides():
    args = Namespace(
        chat_commands_off=True,
        chat_command_prefix="/",
        chat_command_senders="Leader, Support ",
        chat_command_require_sender=True,
        chat_command_allow_no_prefix=True,
    )

    cfg = make_config(args)

    assert cfg.chat_commands_enabled is False
    assert cfg.chat_command_prefix == "/"
    assert cfg.chat_command_allowed_senders == ("Leader", "Support")
    assert cfg.chat_command_require_sender is True
    assert cfg.chat_command_allow_no_prefix is True

def test_make_config_applies_pause_hotkey_overrides():
    args = Namespace(
        pause_hotkey_off=True,
        pause_hotkey_debounce_ms=175.0,
    )

    cfg = make_config(args)

    assert cfg.pause_hotkey_enabled is False
    assert cfg.pause_hotkey_debounce_s == 0.175
