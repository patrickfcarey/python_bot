"""Tests for scenario coverage tracking utilities."""

from bot.coverage import ScenarioCoverageTracker


def test_coverage_tracker_counts_and_underfilled_buckets():
    tracker = ScenarioCoverageTracker(target_per_bucket=3)

    tracker.update(
        {
            "profile": "necromancer",
            "class_name": "necromancer",
            "level_number": "1",
            "party_size_band": "duo",
            "threat_band": "high",
            "combat_mode": "combat_stub_necromancer",
        }
    )
    tracker.update(
        {
            "profile": "necromancer",
            "class_name": "necromancer",
            "level_number": "1",
            "party_size_band": "duo",
            "threat_band": "high",
            "combat_mode": "combat_stub_necromancer",
        }
    )

    tracker.update(
        {
            "profile": "balanced",
            "class_name": "generic",
            "level_number": "1",
            "party_size_band": "solo",
            "threat_band": "low",
            "combat_mode": "idle",
        }
    )

    summary = tracker.summary(top_n=5)

    assert summary.total_events == 3
    assert summary.unique_buckets == 2
    assert summary.under_target_buckets == 2
    assert len(summary.top_underfilled_buckets) == 2

    top_row = summary.top_underfilled_buckets[0]
    assert top_row["deficit"] >= 1
    assert "bucket" in top_row
    assert "profile" in top_row["bucket"]


def test_coverage_tracker_handles_empty_summary():
    tracker = ScenarioCoverageTracker(target_per_bucket=5)
    summary = tracker.summary(top_n=10)

    assert summary.total_events == 0
    assert summary.unique_buckets == 0
    assert summary.under_target_buckets == 0
    assert summary.top_underfilled_buckets == ()
