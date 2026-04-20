"""Tests for asynchronous observer worker behavior."""

import json
import logging
from pathlib import Path
import time
from uuid import uuid4

from dataclasses import replace

from bot.config import default_config
from bot.observer import ObserverWorker
from bot.observer_schema import ObservationEvent


def _build_event(frame_id: int, profile_name: str = "balanced") -> ObservationEvent:
    return ObservationEvent(
        schema_version=1,
        frame_id=int(frame_id),
        monotonic_timestamp=float(time.monotonic()),
        wall_timestamp=float(time.time()),
        lifecycle_state="playing",
        profile_name=profile_name,
        class_name="generic",
        level_number=1,
        vision_mode="async",
        used_fallback_state=False,
        player_position=(400, 300),
        teammate_count=1,
        enemy_detection_count=2,
        enemy_track_count=2,
        ground_item_count=0,
        gold_item_count=0,
        pickit_match_count=0,
        health_ratio=0.95,
        mana_ratio=0.80,
        max_danger_priority=3,
        max_target_priority_score=18,
        threat_band="medium",
        party_size_band="duo",
        action_source="rule_policy",
        action_reason="follow_teammate",
        action_click_target=(420, 310),
        action_cast_spell=None,
        action_hold_move=None,
        action_stop=False,
        combat_mode="idle",
        combat_target_track_id=None,
        combat_target_priority_score=0,
        scenario_tags={
            "profile": profile_name,
            "class_name": "generic",
            "level_number": "1",
            "party_size_band": "duo",
            "threat_band": "medium",
            "combat_mode": "idle",
        },
        stage_timings_ms={"capture": 1.0, "vision": 3.0, "total": 16.0},
        flags=("test",),
    )


def test_observer_worker_writes_jsonl_and_coverage_snapshot():
    test_stamp = uuid4().hex
    observer_dir = Path("logs") / f"observer_test_{test_stamp}"
    image_dir = observer_dir / "images"

    cfg = replace(
        default_config(),
        observer_output_dir=observer_dir,
        observer_image_output_dir=image_dir,
        observer_enabled=True,
        observer_capture_full_frames=False,
        observer_event_queue_size=8,
        observer_event_batch_size=8,
        observer_flush_interval_ms=50,
        observer_drop_policy="drop_oldest",
    )

    worker = ObserverWorker(cfg, logger=logging.getLogger("python_bot.observer.test"))

    # Slow down flush path so a small queue can saturate and exercise drop counters.
    original_write_event_batch = worker._write_event_batch

    def slow_write_event_batch(batch_items):
        time.sleep(0.03)
        original_write_event_batch(batch_items)

    worker._write_event_batch = slow_write_event_batch

    worker.start()
    try:
        for frame_id in range(120):
            worker.publish_event(_build_event(frame_id=frame_id))

        time.sleep(0.30)
    finally:
        stats = worker.close()

    assert stats.submitted_events == 120
    assert stats.written_events > 0
    assert stats.dropped_events > 0
    assert stats.event_log_path is not None
    assert stats.coverage_path is not None

    event_log_path = Path(stats.event_log_path)
    coverage_path = Path(stats.coverage_path)

    assert event_log_path.exists()
    assert coverage_path.exists()

    with event_log_path.open("r", encoding="utf-8") as handle:
        line_count = sum(1 for line_text in handle if line_text.strip())
    assert line_count == stats.written_events

    coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert int(coverage_payload["total_events"]) == stats.written_events
    assert int(coverage_payload["unique_buckets"]) >= 1

    assert stats.shadow_enabled is True
    assert stats.shadow_metrics_path is not None
    shadow_metrics_path = Path(stats.shadow_metrics_path)
    assert shadow_metrics_path.exists()

    shadow_payload = json.loads(shadow_metrics_path.read_text(encoding="utf-8"))
    assert int(shadow_payload["seen_events"]) == stats.written_events
    assert int(shadow_payload["evaluated_events"]) == stats.shadow_evaluated_events
    assert float(shadow_payload["agreement_rate"]) >= 0.0

    shadow_rows = 0
    with event_log_path.open("r", encoding="utf-8") as handle:
        for line_text in handle:
            line_text = line_text.strip()
            if not line_text:
                continue
            row = json.loads(line_text)
            if "shadow" in row:
                shadow_rows += 1
    assert shadow_rows > 0

