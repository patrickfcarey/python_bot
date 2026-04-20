"""Lightweight shadow-policy scorer for observer events.

This module provides a deterministic baseline scorer that predicts a coarse
action category from frame state, then compares that prediction against the
observed runtime action category. It is designed for cheap, non-blocking
telemetry during live runs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import threading
from typing import Dict, Mapping, Optional, Tuple


ACTION_CATEGORIES: Tuple[str, ...] = ("stop", "recover", "combat", "loot", "follow", "idle")


def _safe_int(raw_value: object, default: int = 0) -> int:
    """Convert a value to int with defensive fallback."""
    try:
        return int(raw_value)
    except Exception:
        return int(default)


def _safe_float(raw_value: object, default: float = 0.0) -> float:
    """Convert a value to float with defensive fallback."""
    try:
        return float(raw_value)
    except Exception:
        return float(default)


def _normalized_text(raw_value: object) -> str:
    """Return lowercase stripped text for token matching."""
    return str(raw_value or "").strip().lower()


def _contains_any_token(raw_text: str, tokens: Tuple[str, ...]) -> bool:
    """Check if any token appears in normalized text."""
    normalized = _normalized_text(raw_text)
    return any(token in normalized for token in tokens)


def infer_observed_action_category(event_payload: Mapping[str, object]) -> str:
    """Infer coarse observed action category from event action fields."""
    lifecycle_state = _normalized_text(event_payload.get("lifecycle_state", ""))
    action_reason = _normalized_text(event_payload.get("action_reason", ""))
    action_source = _normalized_text(event_payload.get("action_source", ""))
    action_cast_spell = _normalized_text(event_payload.get("action_cast_spell", ""))
    action_stop = bool(event_payload.get("action_stop", False))

    teammate_count = max(0, _safe_int(event_payload.get("teammate_count", 0)))
    enemy_track_count = max(0, _safe_int(event_payload.get("enemy_track_count", 0)))
    enemy_detection_count = max(0, _safe_int(event_payload.get("enemy_detection_count", 0)))
    pickit_match_count = max(0, _safe_int(event_payload.get("pickit_match_count", 0)))
    ground_item_count = max(0, _safe_int(event_payload.get("ground_item_count", 0)))
    gold_item_count = max(0, _safe_int(event_payload.get("gold_item_count", 0)))

    combat_mode = _normalized_text(event_payload.get("combat_mode", ""))

    if action_stop or lifecycle_state != "playing" or "loading" in action_reason:
        return "stop"

    recover_tokens = ("potion", "rejuv", "health", "mana", "resource")
    if (
        _contains_any_token(action_reason, recover_tokens)
        or _contains_any_token(action_source, recover_tokens)
        or _contains_any_token(action_cast_spell, recover_tokens)
    ):
        return "recover"

    loot_tokens = ("pickup", "pickit", "gold", "loot", "item")
    if (
        _contains_any_token(action_reason, loot_tokens)
        or _contains_any_token(action_source, loot_tokens)
        or pickit_match_count > 0
        or gold_item_count > 0
        or ground_item_count > 0
    ):
        return "loot"

    combat_tokens = ("combat", "attack", "target", "curse", "summon", "kite", "engage", "danger")
    if (
        combat_mode not in {"", "idle"}
        or _contains_any_token(action_reason, combat_tokens)
        or _contains_any_token(action_source, combat_tokens)
        or _contains_any_token(action_cast_spell, combat_tokens)
        or enemy_track_count > 0
        or enemy_detection_count > 0
    ):
        return "combat"

    follow_tokens = ("follow", "teammate", "ally")
    if _contains_any_token(action_reason, follow_tokens) or teammate_count > 0:
        return "follow"

    return "idle"


def predict_shadow_action_category(event_payload: Mapping[str, object]) -> Tuple[str, float, str]:
    """Predict action category from state-only signals for shadow scoring."""
    lifecycle_state = _normalized_text(event_payload.get("lifecycle_state", ""))
    if lifecycle_state != "playing":
        return ("stop", 1.0, "lifecycle_not_playing")

    health_ratio = max(0.0, min(1.0, _safe_float(event_payload.get("health_ratio", 1.0), 1.0)))
    mana_ratio = max(0.0, min(1.0, _safe_float(event_payload.get("mana_ratio", 1.0), 1.0)))
    max_danger_priority = max(0, _safe_int(event_payload.get("max_danger_priority", 0)))
    enemy_track_count = max(0, _safe_int(event_payload.get("enemy_track_count", 0)))
    enemy_detection_count = max(0, _safe_int(event_payload.get("enemy_detection_count", 0)))
    pickit_match_count = max(0, _safe_int(event_payload.get("pickit_match_count", 0)))
    ground_item_count = max(0, _safe_int(event_payload.get("ground_item_count", 0)))
    gold_item_count = max(0, _safe_int(event_payload.get("gold_item_count", 0)))
    teammate_count = max(0, _safe_int(event_payload.get("teammate_count", 0)))

    if health_ratio <= 0.30:
        return ("recover", 0.97, "critical_health")
    if health_ratio <= 0.45 and (enemy_track_count > 0 or max_danger_priority >= 4):
        return ("recover", 0.90, "low_health_under_threat")
    if mana_ratio <= 0.15 and enemy_track_count > 0:
        return ("recover", 0.72, "low_mana_in_combat")

    if enemy_track_count > 0:
        combat_confidence = min(0.97, 0.72 + (max_danger_priority * 0.05) + min(0.10, enemy_track_count * 0.01))
        return ("combat", combat_confidence, "enemy_tracks_present")
    if enemy_detection_count > 0 and max_danger_priority >= 2:
        combat_confidence = min(
            0.90,
            0.60 + (max_danger_priority * 0.06) + min(0.12, enemy_detection_count * 0.01),
        )
        return ("combat", combat_confidence, "enemy_detections_present")

    if pickit_match_count > 0:
        return ("loot", 0.86, "pickit_matches_present")
    if (ground_item_count + gold_item_count) > 0:
        loot_confidence = 0.62 if (ground_item_count + gold_item_count) >= 3 else 0.55
        return ("loot", loot_confidence, "ground_loot_visible")

    if teammate_count > 0:
        follow_confidence = 0.75 if teammate_count >= 2 else 0.70
        return ("follow", follow_confidence, "teammates_visible")

    return ("idle", 0.58, "no_strong_signal")


@dataclass(frozen=True)
class ShadowPolicySummary:
    """JSON-serializable summary of shadow-policy scoring behavior."""

    enabled: bool
    include_loading: bool
    min_confidence: float

    seen_events: int
    evaluated_events: int
    agreement_count: int
    disagreement_count: int
    agreement_rate: float
    skipped_loading: int
    skipped_low_confidence: int

    confusion_pairs: Dict[str, int]
    disagreement_examples: Tuple[Dict[str, object], ...]

    def to_dict(self) -> Dict[str, object]:
        """Convert summary dataclass to a plain JSON-ready dictionary."""
        return {
            "enabled": bool(self.enabled),
            "include_loading": bool(self.include_loading),
            "min_confidence": float(self.min_confidence),
            "seen_events": int(self.seen_events),
            "evaluated_events": int(self.evaluated_events),
            "agreement_count": int(self.agreement_count),
            "disagreement_count": int(self.disagreement_count),
            "agreement_rate": float(self.agreement_rate),
            "skipped_loading": int(self.skipped_loading),
            "skipped_low_confidence": int(self.skipped_low_confidence),
            "confusion_pairs": dict(self.confusion_pairs),
            "disagreement_examples": [dict(row) for row in self.disagreement_examples],
        }


class ShadowPolicyScorer:
    """Thread-safe scorer for tracking baseline action-category agreement."""

    def __init__(
        self,
        enabled: bool = True,
        include_loading: bool = False,
        min_confidence: float = 0.55,
        max_disagreement_examples: int = 20,
    ):
        self._enabled = bool(enabled)
        self._include_loading = bool(include_loading)
        self._min_confidence = max(0.0, min(1.0, float(min_confidence)))
        self._max_disagreement_examples = max(0, int(max_disagreement_examples))

        self._lock = threading.Lock()
        self._seen_events = 0
        self._evaluated_events = 0
        self._agreement_count = 0
        self._disagreement_count = 0
        self._skipped_loading = 0
        self._skipped_low_confidence = 0
        self._confusion_counter: Counter[Tuple[str, str]] = Counter()
        self._disagreement_examples = []

    def score_event(self, event_payload: Mapping[str, object]) -> Optional[Dict[str, object]]:
        """Evaluate one event and return per-event shadow metadata when evaluated."""
        if not self._enabled:
            return None

        lifecycle_state = _normalized_text(event_payload.get("lifecycle_state", ""))
        predicted_category, predicted_confidence, predicted_reason = predict_shadow_action_category(event_payload)

        with self._lock:
            self._seen_events += 1

            if (not self._include_loading) and lifecycle_state != "playing":
                self._skipped_loading += 1
                return None

            if float(predicted_confidence) < self._min_confidence:
                self._skipped_low_confidence += 1
                return None

            observed_category = infer_observed_action_category(event_payload)
            agreement = predicted_category == observed_category

            self._evaluated_events += 1
            if agreement:
                self._agreement_count += 1
            else:
                self._disagreement_count += 1

            self._confusion_counter[(observed_category, predicted_category)] += 1

            if (not agreement) and (len(self._disagreement_examples) < self._max_disagreement_examples):
                self._disagreement_examples.append(
                    {
                        "frame_id": _safe_int(event_payload.get("frame_id", 0)),
                        "lifecycle_state": lifecycle_state,
                        "observed_category": observed_category,
                        "predicted_category": predicted_category,
                        "predicted_confidence": round(float(predicted_confidence), 4),
                        "predicted_reason": predicted_reason,
                        "action_reason": str(event_payload.get("action_reason", "")),
                        "combat_mode": str(event_payload.get("combat_mode", "")),
                        "enemy_track_count": _safe_int(event_payload.get("enemy_track_count", 0)),
                        "teammate_count": _safe_int(event_payload.get("teammate_count", 0)),
                        "max_danger_priority": _safe_int(event_payload.get("max_danger_priority", 0)),
                    }
                )

        return {
            "predicted_category": predicted_category,
            "predicted_confidence": round(float(predicted_confidence), 4),
            "predicted_reason": predicted_reason,
            "observed_category": observed_category,
            "agreement": bool(agreement),
        }

    def summary(self) -> ShadowPolicySummary:
        """Return immutable summary snapshot of scorer metrics."""
        with self._lock:
            evaluated_events = int(self._evaluated_events)
            agreement_count = int(self._agreement_count)
            disagreement_count = int(self._disagreement_count)
            agreement_rate = (agreement_count / evaluated_events) if evaluated_events > 0 else 0.0

            confusion_pairs: Dict[str, int] = {}
            for (observed_category, predicted_category), count in sorted(
                self._confusion_counter.items(),
                key=lambda row: (-row[1], row[0][0], row[0][1]),
            ):
                pair_key = f"{observed_category}->{predicted_category}"
                confusion_pairs[pair_key] = int(count)

            disagreement_examples = tuple(dict(row) for row in self._disagreement_examples)

            return ShadowPolicySummary(
                enabled=bool(self._enabled),
                include_loading=bool(self._include_loading),
                min_confidence=float(self._min_confidence),
                seen_events=int(self._seen_events),
                evaluated_events=evaluated_events,
                agreement_count=agreement_count,
                disagreement_count=disagreement_count,
                agreement_rate=float(agreement_rate),
                skipped_loading=int(self._skipped_loading),
                skipped_low_confidence=int(self._skipped_low_confidence),
                confusion_pairs=confusion_pairs,
                disagreement_examples=disagreement_examples,
            )
