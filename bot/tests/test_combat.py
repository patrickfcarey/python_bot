"""Tests for combat routine stubs."""

from bot.combat import CombatRoutine
from bot.config import NecromancerConfig
from bot.game_state import EnemyTrack, GameState


def test_combat_returns_none_without_tracks():
    routine = CombatRoutine(engage_range_px=200, close_range_px=30)
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 400),
    )

    decision = routine.decide(state)
    assert decision is None


def test_combat_returns_action_with_target_in_range():
    routine = CombatRoutine(engage_range_px=300, close_range_px=20)
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 400),
        enemy_tracks=[EnemyTrack(track_id=7, position=(430, 420), lost_frames=0)],
    )

    decision = routine.decide(state)

    assert decision is not None
    assert decision.target_track_id == 7
    assert decision.action.cast_spell == "primary"


def test_necromancer_spell_stub_uses_curse_then_primary_then_summon():
    routine = CombatRoutine(
        engage_range_px=300,
        close_range_px=40,
        class_name="necromancer",
        necromancer_config=NecromancerConfig(
            follow_radius=18,
            curse_spell_slot="curse",
            primary_attack_slot="primary",
            summon_spell_slot="summon",
            curse_recast_frames=10,
            summon_recast_frames=2,
        ),
    )
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 400),
        enemy_tracks=[EnemyTrack(track_id=2, position=(410, 410), lost_frames=0)],
    )

    first = routine.decide(state)
    second = routine.decide(state)
    third = routine.decide(state)

    assert first is not None and first.action.cast_spell == "curse"
    assert second is not None and second.action.cast_spell == "primary"
    assert third is not None and third.action.cast_spell == "summon"

def test_combat_decision_exposes_target_danger_metadata():
    routine = CombatRoutine(engage_range_px=300, close_range_px=25)
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 400),
        enemy_tracks=[
            EnemyTrack(
                track_id=9,
                position=(410, 410),
                lost_frames=0,
                danger_priority=5,
                danger_label="critical",
                danger_tags=("explode", "light_mover"),
                combat_relevant=True,
            )
        ],
    )

    decision = routine.decide(state)

    assert decision is not None
    assert decision.target_track_id == 9
    assert decision.target_danger_priority == 5
    assert decision.target_danger_label == "critical"
    assert decision.target_danger_tags == ("explode", "light_mover")
    assert decision.target_combat_relevant is True


def test_combat_prefers_weighted_high_threat_target_over_nearest():
    routine = CombatRoutine(engage_range_px=320, close_range_px=30)
    state = GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(400, 400),
        enemy_tracks=[
            EnemyTrack(
                track_id=1,
                position=(412, 404),
                lost_frames=0,
                danger_priority=2,
                danger_label="low",
                danger_tags=("melee_attacker",),
                target_priority_score=10,
                human_consensus_score=12,
                human_consensus_band="routine",
            ),
            EnemyTrack(
                track_id=2,
                position=(505, 405),
                lost_frames=0,
                danger_priority=6,
                danger_label="super_critical",
                danger_tags=("super_critical_threat", "lightning_sniper"),
                target_priority_score=95,
                human_consensus_score=92,
                human_consensus_band="run_ending",
                burst_pressure_rating=5,
                control_pressure_rating=3,
                attrition_pressure_rating=2,
                spawn_pressure_rating=0,
                avoidance_priority=True,
            ),
        ],
    )

    decision = routine.decide(state)

    assert decision is not None
    assert decision.target_track_id == 2
    assert decision.target_priority_score == 95
    assert decision.target_human_consensus_band == "run_ending"