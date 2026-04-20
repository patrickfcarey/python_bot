"""Enemy tracking stub for future combat logic."""

from math import inf
from typing import List

from bot.game_state import EnemyDetection, EnemyTrack


class EnemyTracker:
    def __init__(self, match_distance_px: float = 40.0, max_lost_frames: int = 6):
        """Initialize a new `EnemyTracker` instance.

        Parameters:
            match_distance_px: Parameter for match distance px used in this routine.
            max_lost_frames: Parameter representing image frame data for vision processing.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._match_distance_sq = match_distance_px * match_distance_px
        self._max_lost_frames = max_lost_frames
        self._next_track_id = 1
        self._active_tracks: List[EnemyTrack] = []

    def reset(self):
        """Reset.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._next_track_id = 1
        self._active_tracks = []

    def update(self, detections: List[EnemyDetection]) -> List[EnemyTrack]:
        """Update.

        Parameters:
            detections: Parameter for detections used in this routine.

        Local Variables:
            best_dist_sq: Local variable for best dist sq used in this routine.
            best_index: Local variable used as a position index while iterating.
            detection: Local variable for detection used in this routine.
            dist_sq: Local variable for dist sq used in this routine.
            dx: Local variable for dx used in this routine.
            dy: Local variable for dy used in this routine.
            idx: Local variable for idx used in this routine.
            lost_frames: Local variable representing image frame data for vision processing.
            old_track: Local variable for old track used in this routine.
            track: Local variable for track used in this routine.
            updated_tracks: Local variable for updated tracks used in this routine.
            used_track_indices: Local variable for used track indices used in this routine.
            vx: Local variable for vx used in this routine.
            vy: Local variable for vy used in this routine.

        Returns:
            A value matching the annotated return type `List[EnemyTrack]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        used_track_indices = set()
        updated_tracks: List[EnemyTrack] = []

        for detection in detections:
            best_index = None
            best_dist_sq = inf

            for idx, track in enumerate(self._active_tracks):
                if idx in used_track_indices:
                    continue

                dx = detection.position[0] - track.position[0]
                dy = detection.position[1] - track.position[1]
                dist_sq = (dx * dx) + (dy * dy)

                if dist_sq <= self._match_distance_sq and dist_sq < best_dist_sq:
                    best_dist_sq = dist_sq
                    best_index = idx

            if best_index is None:
                updated_tracks.append(
                    EnemyTrack(
                        track_id=self._next_track_id,
                        position=detection.position,
                        velocity=(0.0, 0.0),
                        frames_seen=1,
                        lost_frames=0,
                        enemy_type=detection.enemy_type,
                        is_elite=detection.is_elite,
                        combat_relevant=detection.combat_relevant,
                        danger_priority=detection.danger_priority,
                        danger_label=detection.danger_label,
                        danger_tags=detection.danger_tags,
                        threat_vector_primary=detection.threat_vector_primary,
                        threat_vector_secondary=detection.threat_vector_secondary,
                        engagement_profile=detection.engagement_profile,
                        mobility_class=detection.mobility_class,
                        burst_pressure_rating=detection.burst_pressure_rating,
                        control_pressure_rating=detection.control_pressure_rating,
                        attrition_pressure_rating=detection.attrition_pressure_rating,
                        spawn_pressure_rating=detection.spawn_pressure_rating,
                        threat_rollup_rating=detection.threat_rollup_rating,
                        threat_intensity_rating=detection.threat_intensity_rating,
                        human_consensus_score=detection.human_consensus_score,
                        human_consensus_band=detection.human_consensus_band,
                        target_priority_score=detection.target_priority_score,
                        avoidance_priority=detection.avoidance_priority,
                        needs_line_of_sight_break=detection.needs_line_of_sight_break,
                        needs_corpse_control=detection.needs_corpse_control,
                        needs_debuff_response=detection.needs_debuff_response,
                    )
                )
                self._next_track_id += 1
                continue

            used_track_indices.add(best_index)
            old_track = self._active_tracks[best_index]
            vx = float(detection.position[0] - old_track.position[0])
            vy = float(detection.position[1] - old_track.position[1])

            updated_tracks.append(
                EnemyTrack(
                    track_id=old_track.track_id,
                    position=detection.position,
                    velocity=(vx, vy),
                    frames_seen=old_track.frames_seen + 1,
                    lost_frames=0,
                    enemy_type=detection.enemy_type,
                    is_elite=detection.is_elite,
                    combat_relevant=detection.combat_relevant,
                    danger_priority=detection.danger_priority,
                    danger_label=detection.danger_label,
                    danger_tags=detection.danger_tags,
                    threat_vector_primary=detection.threat_vector_primary,
                    threat_vector_secondary=detection.threat_vector_secondary,
                    engagement_profile=detection.engagement_profile,
                    mobility_class=detection.mobility_class,
                    burst_pressure_rating=detection.burst_pressure_rating,
                    control_pressure_rating=detection.control_pressure_rating,
                    attrition_pressure_rating=detection.attrition_pressure_rating,
                    spawn_pressure_rating=detection.spawn_pressure_rating,
                    threat_rollup_rating=detection.threat_rollup_rating,
                    threat_intensity_rating=detection.threat_intensity_rating,
                    human_consensus_score=detection.human_consensus_score,
                    human_consensus_band=detection.human_consensus_band,
                    target_priority_score=detection.target_priority_score,
                    avoidance_priority=detection.avoidance_priority,
                    needs_line_of_sight_break=detection.needs_line_of_sight_break,
                    needs_corpse_control=detection.needs_corpse_control,
                    needs_debuff_response=detection.needs_debuff_response,
                )
            )

        for idx, old_track in enumerate(self._active_tracks):
            if idx in used_track_indices:
                continue

            lost_frames = old_track.lost_frames + 1
            if lost_frames <= self._max_lost_frames:
                updated_tracks.append(
                    EnemyTrack(
                        track_id=old_track.track_id,
                        position=old_track.position,
                        velocity=(0.0, 0.0),
                        frames_seen=old_track.frames_seen,
                        lost_frames=lost_frames,
                        enemy_type=old_track.enemy_type,
                        is_elite=old_track.is_elite,
                        combat_relevant=old_track.combat_relevant,
                        danger_priority=old_track.danger_priority,
                        danger_label=old_track.danger_label,
                        danger_tags=old_track.danger_tags,
                        threat_vector_primary=old_track.threat_vector_primary,
                        threat_vector_secondary=old_track.threat_vector_secondary,
                        engagement_profile=old_track.engagement_profile,
                        mobility_class=old_track.mobility_class,
                        burst_pressure_rating=old_track.burst_pressure_rating,
                        control_pressure_rating=old_track.control_pressure_rating,
                        attrition_pressure_rating=old_track.attrition_pressure_rating,
                        spawn_pressure_rating=old_track.spawn_pressure_rating,
                        threat_rollup_rating=old_track.threat_rollup_rating,
                        threat_intensity_rating=old_track.threat_intensity_rating,
                        human_consensus_score=old_track.human_consensus_score,
                        human_consensus_band=old_track.human_consensus_band,
                        target_priority_score=old_track.target_priority_score,
                        avoidance_priority=old_track.avoidance_priority,
                        needs_line_of_sight_break=old_track.needs_line_of_sight_break,
                        needs_corpse_control=old_track.needs_corpse_control,
                        needs_debuff_response=old_track.needs_debuff_response,
                    )
                )

        self._active_tracks = sorted(updated_tracks, key=lambda t: t.track_id)
        return list(self._active_tracks)