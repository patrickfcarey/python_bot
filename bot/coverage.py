"""Scenario coverage tracking utilities for observer data collection."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple


REQUIRED_SCENARIO_TAG_KEYS: Tuple[str, ...] = (
    "profile",
    "class_name",
    "level_number",
    "party_size_band",
    "threat_band",
    "combat_mode",
)


@dataclass(frozen=True)
class CoverageSummary:
    """Serializable snapshot of scenario coverage statistics."""

    total_events: int
    unique_buckets: int
    target_per_bucket: int
    min_bucket_count: int
    max_bucket_count: int
    avg_bucket_count: float
    under_target_buckets: int
    top_underfilled_buckets: Tuple[Dict[str, object], ...]

    def to_dict(self) -> Dict[str, object]:
        """Convert summary data into a JSON-serializable dictionary."""
        return {
            "total_events": int(self.total_events),
            "unique_buckets": int(self.unique_buckets),
            "target_per_bucket": int(self.target_per_bucket),
            "min_bucket_count": int(self.min_bucket_count),
            "max_bucket_count": int(self.max_bucket_count),
            "avg_bucket_count": float(self.avg_bucket_count),
            "under_target_buckets": int(self.under_target_buckets),
            "top_underfilled_buckets": [dict(row) for row in self.top_underfilled_buckets],
        }


class ScenarioCoverageTracker:
    """Track scenario bucket counts and report data-collection gaps."""

    def __init__(
        self,
        target_per_bucket: int = 300,
        required_keys: Iterable[str] = REQUIRED_SCENARIO_TAG_KEYS,
    ):
        """Initialize coverage tracker state.

        Parameters:
            target_per_bucket: Desired minimum count for each scenario bucket.
            required_keys: Ordered tag keys that define the bucket identity.

        Returns:
            None.

        Side Effects:
            - Initializes internal counters used for coverage analysis.
        """
        self._target_per_bucket = max(1, int(target_per_bucket))
        self._required_keys = tuple(str(key) for key in required_keys)
        self._bucket_counts: Counter[Tuple[str, ...]] = Counter()
        self._total_events = 0

    def update(self, scenario_tags: Mapping[str, object]):
        """Record one event into a normalized scenario bucket."""
        bucket_key = self._normalize_bucket_key(scenario_tags)
        self._bucket_counts[bucket_key] += 1
        self._total_events += 1

    def merge(self, other: "ScenarioCoverageTracker"):
        """Merge counters from another tracker instance."""
        self._bucket_counts.update(other._bucket_counts)
        self._total_events += int(other._total_events)

    def summary(self, top_n: int = 20) -> CoverageSummary:
        """Build a coverage summary with the most underfilled scenario buckets."""
        requested_top_n = max(1, int(top_n))

        if not self._bucket_counts:
            return CoverageSummary(
                total_events=0,
                unique_buckets=0,
                target_per_bucket=self._target_per_bucket,
                min_bucket_count=0,
                max_bucket_count=0,
                avg_bucket_count=0.0,
                under_target_buckets=0,
                top_underfilled_buckets=(),
            )

        count_values = list(self._bucket_counts.values())
        underfilled_rows = []
        for bucket_key, bucket_count in self._bucket_counts.items():
            deficit = max(0, self._target_per_bucket - int(bucket_count))
            if deficit <= 0:
                continue
            row = {
                "bucket": self._bucket_to_dict(bucket_key),
                "count": int(bucket_count),
                "deficit": int(deficit),
            }
            underfilled_rows.append(row)

        underfilled_rows.sort(key=lambda row: (-int(row["deficit"]), int(row["count"])))
        top_rows = tuple(underfilled_rows[:requested_top_n])

        return CoverageSummary(
            total_events=int(self._total_events),
            unique_buckets=len(self._bucket_counts),
            target_per_bucket=self._target_per_bucket,
            min_bucket_count=min(count_values),
            max_bucket_count=max(count_values),
            avg_bucket_count=float(sum(count_values) / max(1, len(count_values))),
            under_target_buckets=len(underfilled_rows),
            top_underfilled_buckets=top_rows,
        )

    def _normalize_bucket_key(self, scenario_tags: Mapping[str, object]) -> Tuple[str, ...]:
        """Map scenario tags into a deterministic bucket key tuple."""
        normalized_values = []
        for key_name in self._required_keys:
            raw_value = scenario_tags.get(key_name, "unknown")
            string_value = str(raw_value).strip()
            normalized_values.append(string_value if string_value else "unknown")
        return tuple(normalized_values)

    def _bucket_to_dict(self, bucket_key: Tuple[str, ...]) -> Dict[str, str]:
        """Convert bucket tuple back into labeled key/value mapping."""
        return {key_name: bucket_key[index] for index, key_name in enumerate(self._required_keys)}

    @property
    def total_events(self) -> int:
        """Return total number of events observed by this tracker."""
        return int(self._total_events)

    @property
    def unique_buckets(self) -> int:
        """Return number of unique scenario buckets observed."""
        return len(self._bucket_counts)
