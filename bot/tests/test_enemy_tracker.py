"""Tests for enemy tracker stub behavior."""

from bot.enemy_tracker import EnemyTracker
from bot.game_state import EnemyDetection


def test_enemy_tracker_reuses_track_id_for_nearby_detection():
    tracker = EnemyTracker(match_distance_px=50.0, max_lost_frames=2)

    tracks_1 = tracker.update([EnemyDetection(position=(100, 100))])
    first_id = tracks_1[0].track_id

    tracks_2 = tracker.update([EnemyDetection(position=(112, 104))])
    assert len(tracks_2) == 1
    assert tracks_2[0].track_id == first_id
    assert tracks_2[0].frames_seen == 2


def test_enemy_tracker_drops_tracks_after_lost_threshold():
    tracker = EnemyTracker(match_distance_px=20.0, max_lost_frames=1)
    tracker.update([EnemyDetection(position=(50, 50))])

    tracks_lost_once = tracker.update([])
    assert len(tracks_lost_once) == 1
    assert tracks_lost_once[0].lost_frames == 1

    tracks_lost_twice = tracker.update([])
    assert tracks_lost_twice == []
def test_enemy_tracker_propagates_threat_metadata_from_detection():
    tracker = EnemyTracker(match_distance_px=35.0, max_lost_frames=2)

    tracks = tracker.update(
        [
            EnemyDetection(
                position=(120, 80),
                enemy_type="fetish",
                combat_relevant=True,
                danger_priority=5,
                danger_label="critical",
                danger_tags=("explode", "light_mover"),
            )
        ]
    )

    assert len(tracks) == 1
    track = tracks[0]
    assert track.enemy_type == "fetish"
    assert track.combat_relevant is True
    assert track.danger_priority == 5
    assert track.danger_label == "critical"
    assert track.danger_tags == ("explode", "light_mover")
