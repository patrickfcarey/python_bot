"""Observer event schemas and helper functions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Mapping, Optional, Tuple


DEFAULT_EVENT_SCHEMA_VERSION = 1


def classify_threat_band(max_danger_priority: int) -> str:
    """Map danger-priority integer to a coarse threat band label."""
    danger_value = int(max_danger_priority)
    if danger_value <= 0:
        return "none"
    if danger_value == 1:
        return "trivial"
    if danger_value == 2:
        return "low"
    if danger_value == 3:
        return "medium"
    if danger_value == 4:
        return "high"
    return "critical"


def classify_party_size_band(teammate_count: int) -> str:
    """Map teammate count to coarse party-size label."""
    teammate_value = max(0, int(teammate_count))
    if teammate_value <= 0:
        return "solo"
    if teammate_value == 1:
        return "duo"
    if teammate_value == 2:
        return "trio"
    return "party_4_plus"


def sanitize_scenario_tags(raw_tags: Mapping[str, object]) -> Dict[str, str]:
    """Normalize scenario tag values into non-empty strings."""
    normalized: Dict[str, str] = {}
    for key_name, raw_value in raw_tags.items():
        normalized_key = str(key_name).strip()
        if not normalized_key:
            continue
        value_string = str(raw_value).strip()
        normalized[normalized_key] = value_string if value_string else "unknown"
    return normalized


@dataclass(frozen=True)
class ObservationEvent:
    """Structured per-frame observation record for offline learning/analysis."""

    schema_version: int
    frame_id: int
    monotonic_timestamp: float
    wall_timestamp: float

    lifecycle_state: str
    profile_name: str
    class_name: str
    level_number: int

    vision_mode: str
    used_fallback_state: bool

    player_position: Tuple[int, int]
    teammate_count: int
    enemy_detection_count: int
    enemy_track_count: int
    ground_item_count: int
    gold_item_count: int
    pickit_match_count: int

    health_ratio: float
    mana_ratio: float

    max_danger_priority: int
    max_target_priority_score: int
    threat_band: str
    party_size_band: str

    action_source: str
    action_reason: str
    action_click_target: Optional[Tuple[int, int]]
    action_cast_spell: Optional[str]
    action_hold_move: Optional[bool]
    action_stop: bool

    combat_mode: str
    combat_target_track_id: Optional[int]
    combat_target_priority_score: int

    scenario_tags: Dict[str, str] = field(default_factory=dict)
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    flags: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, object]:
        """Convert event into JSON-serializable dictionary payload."""
        payload = asdict(self)
        payload["scenario_tags"] = sanitize_scenario_tags(payload.get("scenario_tags", {}))

        stage_timings = payload.get("stage_timings_ms", {})
        payload["stage_timings_ms"] = {
            str(stage_name): float(stage_value)
            for stage_name, stage_value in stage_timings.items()
        }

        payload["flags"] = tuple(str(flag_name) for flag_name in payload.get("flags", ()))

        if self.action_click_target is not None:
            payload["action_click_target"] = [
                int(self.action_click_target[0]),
                int(self.action_click_target[1]),
            ]

        payload["player_position"] = [int(self.player_position[0]), int(self.player_position[1])]
        return payload
