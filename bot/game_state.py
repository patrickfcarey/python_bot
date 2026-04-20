"""Game state models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time


@dataclass(frozen=True)
class TeammateDetection:
    position: Tuple[int, int]
    name: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class EnemyDetection:
    position: Tuple[int, int]
    enemy_type: str = "unknown"
    confidence: float = 0.0
    is_elite: bool = False
    combat_relevant: bool = True
    danger_priority: int = 2
    danger_label: str = "low"
    danger_tags: Tuple[str, ...] = field(default_factory=tuple)
    threat_vector_primary: str = "general_pressure"
    threat_vector_secondary: str = "none"
    engagement_profile: str = "mixed"
    mobility_class: str = "standard"
    burst_pressure_rating: int = 0
    control_pressure_rating: int = 0
    attrition_pressure_rating: int = 0
    spawn_pressure_rating: int = 0
    threat_rollup_rating: int = 0
    threat_intensity_rating: int = 0
    human_consensus_score: int = 0
    human_consensus_band: str = "routine"
    target_priority_score: int = 0
    avoidance_priority: bool = False
    needs_line_of_sight_break: bool = False
    needs_corpse_control: bool = False
    needs_debuff_response: bool = False


@dataclass(frozen=True)
class EnemyTrack:
    track_id: int
    position: Tuple[int, int]
    velocity: Tuple[float, float] = (0.0, 0.0)
    frames_seen: int = 1
    lost_frames: int = 0
    enemy_type: str = "unknown"
    is_elite: bool = False
    combat_relevant: bool = True
    danger_priority: int = 2
    danger_label: str = "low"
    danger_tags: Tuple[str, ...] = field(default_factory=tuple)
    threat_vector_primary: str = "general_pressure"
    threat_vector_secondary: str = "none"
    engagement_profile: str = "mixed"
    mobility_class: str = "standard"
    burst_pressure_rating: int = 0
    control_pressure_rating: int = 0
    attrition_pressure_rating: int = 0
    spawn_pressure_rating: int = 0
    threat_rollup_rating: int = 0
    threat_intensity_rating: int = 0
    human_consensus_score: int = 0
    human_consensus_band: str = "routine"
    target_priority_score: int = 0
    avoidance_priority: bool = False
    needs_line_of_sight_break: bool = False
    needs_corpse_control: bool = False
    needs_debuff_response: bool = False


@dataclass(frozen=True)
class ResourceStatus:
    health_ratio: float = 1.0
    mana_ratio: float = 1.0
    confidence: float = 0.0


@dataclass(frozen=True)
class BeltStatus:
    health_slots_filled: int = 0
    mana_slots_filled: int = 0
    rejuvenation_slots_filled: int = 0
    total_slots: int = 16
    confidence: float = 0.0


@dataclass(frozen=True)
class GroundItemDetection:
    position: Tuple[int, int]
    label: str
    confidence: float = 0.0
    is_gold: bool = False
    gold_amount: int = 0


@dataclass(frozen=True)
class PickitMatch:
    item: GroundItemDetection
    priority: int
    rule_name: str


@dataclass
class GameState:
    automap_matrix: Optional[Any]
    teammate_detections: List[TeammateDetection]
    player_position: Tuple[int, int]
    relative_vectors: List[Tuple[float, float]] = field(default_factory=list)
    enemy_detections: List[EnemyDetection] = field(default_factory=list)
    enemy_tracks: List[EnemyTrack] = field(default_factory=list)
    combat_state: str = "idle"
    level_number: int = 0
    loading: bool = False
    last_action: Optional[str] = None
    resource_status: Optional[ResourceStatus] = None
    belt_status: Optional[BeltStatus] = None
    ground_items: List[GroundItemDetection] = field(default_factory=list)
    gold_items: List[GroundItemDetection] = field(default_factory=list)
    pickit_matches: List[PickitMatch] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def teammate_positions(self) -> List[Tuple[int, int]]:
        """Teammate positions.

        Parameters:
            None.

        Local Variables:
            d: Local variable for d used in this routine.

        Returns:
            A value matching the annotated return type `List[Tuple[int, int]]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return [d.position for d in self.teammate_detections]

    @property
    def active_enemy_tracks(self) -> List[EnemyTrack]:
        """Active enemy tracks.

        Parameters:
            None.

        Local Variables:
            track: Local variable for track used in this routine.

        Returns:
            A value matching the annotated return type `List[EnemyTrack]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return [track for track in self.enemy_tracks if track.lost_frames == 0]

    @property
    def active_enemy_detections(self) -> List[EnemyDetection]:
        """Active enemy detections.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `List[EnemyDetection]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return list(self.enemy_detections)

    def enemy_threat_snapshot(self) -> List[Dict[str, object]]:
        """Expose enemy threat metadata for targeting/avoidance consumers.

        Uses active tracks when present; falls back to raw detections.
        """
        if self.active_enemy_tracks:
            return [
                {
                    "source": "track",
                    "id": track.track_id,
                    "position": track.position,
                    "combat_relevant": track.combat_relevant,
                    "danger_priority": track.danger_priority,
                    "danger_label": track.danger_label,
                    "danger_tags": track.danger_tags,
                    "threat_vector_primary": track.threat_vector_primary,
                    "threat_vector_secondary": track.threat_vector_secondary,
                    "engagement_profile": track.engagement_profile,
                    "mobility_class": track.mobility_class,
                    "burst_pressure_rating": track.burst_pressure_rating,
                    "control_pressure_rating": track.control_pressure_rating,
                    "attrition_pressure_rating": track.attrition_pressure_rating,
                    "spawn_pressure_rating": track.spawn_pressure_rating,
                    "threat_rollup_rating": track.threat_rollup_rating,
                    "threat_intensity_rating": track.threat_intensity_rating,
                    "human_consensus_score": track.human_consensus_score,
                    "human_consensus_band": track.human_consensus_band,
                    "target_priority_score": track.target_priority_score,
                    "avoidance_priority": track.avoidance_priority,
                    "needs_line_of_sight_break": track.needs_line_of_sight_break,
                    "needs_corpse_control": track.needs_corpse_control,
                    "needs_debuff_response": track.needs_debuff_response,
                }
                for track in self.active_enemy_tracks
            ]

        return [
            {
                "source": "detection",
                "id": None,
                "position": detection.position,
                "combat_relevant": detection.combat_relevant,
                "danger_priority": detection.danger_priority,
                "danger_label": detection.danger_label,
                "danger_tags": detection.danger_tags,
                "threat_vector_primary": detection.threat_vector_primary,
                "threat_vector_secondary": detection.threat_vector_secondary,
                "engagement_profile": detection.engagement_profile,
                "mobility_class": detection.mobility_class,
                "burst_pressure_rating": detection.burst_pressure_rating,
                "control_pressure_rating": detection.control_pressure_rating,
                "attrition_pressure_rating": detection.attrition_pressure_rating,
                "spawn_pressure_rating": detection.spawn_pressure_rating,
                "threat_rollup_rating": detection.threat_rollup_rating,
                "threat_intensity_rating": detection.threat_intensity_rating,
                "human_consensus_score": detection.human_consensus_score,
                "human_consensus_band": detection.human_consensus_band,
                "target_priority_score": detection.target_priority_score,
                "avoidance_priority": detection.avoidance_priority,
                "needs_line_of_sight_break": detection.needs_line_of_sight_break,
                "needs_corpse_control": detection.needs_corpse_control,
                "needs_debuff_response": detection.needs_debuff_response,
            }
            for detection in self.enemy_detections
        ]