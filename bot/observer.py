"""Asynchronous observer worker for non-blocking runtime data capture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import queue
import threading
import time
from typing import Dict, Optional

import numpy as np

from bot.config import RuntimeConfig
from bot.coverage import ScenarioCoverageTracker
from bot.observer_schema import ObservationEvent
from bot.shadow_policy import ShadowPolicyScorer

try:
    import cv2
except Exception:  # pragma: no cover - import guard for limited envs
    cv2 = None


SUPPORTED_DROP_POLICIES = {"drop_oldest", "drop_new"}


@dataclass(frozen=True)
class ObserverStats:
    """Snapshot counters and file outputs for observer runtime behavior."""

    submitted_events: int
    written_events: int
    dropped_events: int
    event_queue_depth: int
    event_queue_max_depth: int

    submitted_images: int
    written_images: int
    dropped_images: int
    image_queue_depth: int
    image_queue_max_depth: int

    flush_count: int
    write_errors: int

    coverage_total_events: int
    coverage_unique_buckets: int

    shadow_enabled: bool
    shadow_seen_events: int
    shadow_evaluated_events: int
    shadow_agreement_count: int
    shadow_disagreement_count: int
    shadow_agreement_rate: float
    shadow_skipped_loading: int
    shadow_skipped_low_confidence: int

    event_log_path: Optional[str]
    coverage_path: Optional[str]
    shadow_metrics_path: Optional[str]
    image_index_path: Optional[str]
    image_output_dir: Optional[str]

    last_error: str


class ObserverWorker:
    """Background writer that captures structured observation events and sampled frames."""

    def __init__(self, config: RuntimeConfig, logger: Optional[logging.Logger] = None):
        """Initialize observer queues, counters, and writer settings."""
        self._config = config
        self._logger = logger if logger is not None else logging.getLogger("python_bot.observer")

        self._drop_policy = str(config.observer_drop_policy).strip().lower() or "drop_oldest"
        if self._drop_policy not in SUPPORTED_DROP_POLICIES:
            self._drop_policy = "drop_oldest"

        self._event_queue = queue.Queue(maxsize=max(1, int(config.observer_event_queue_size)))
        self._image_queue = queue.Queue(maxsize=max(1, int(config.observer_image_queue_size)))

        self._event_batch_size = max(1, int(config.observer_event_batch_size))
        self._flush_interval_s = max(0.01, float(config.observer_flush_interval_ms) / 1000.0)

        self._capture_full_frames = bool(config.observer_capture_full_frames)
        self._full_frame_sample_fps = max(0.0, float(config.observer_full_frame_sample_fps))
        self._full_frame_sample_interval_s = 0.0
        if self._full_frame_sample_fps > 0.0:
            self._full_frame_sample_interval_s = 1.0 / self._full_frame_sample_fps

        self._capture_high_threat_frames = bool(config.observer_high_threat_frame_capture)
        self._high_threat_min_danger = int(config.observer_high_threat_min_danger)
        self._high_threat_cooldown_s = max(0.0, float(config.observer_high_threat_cooldown_s))

        self._image_jpeg_quality = max(30, min(100, int(config.observer_image_jpeg_quality)))

        self._output_dir = Path(config.observer_output_dir)
        self._image_output_dir = Path(config.observer_image_output_dir)

        self._event_log_path: Optional[Path] = None
        self._coverage_path: Optional[Path] = None
        self._shadow_metrics_path: Optional[Path] = None
        self._stats_path: Optional[Path] = None
        self._image_index_path: Optional[Path] = None

        self._event_writer_thread: Optional[threading.Thread] = None
        self._image_writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        self._coverage_tracker = ScenarioCoverageTracker(target_per_bucket=config.observer_coverage_target_samples)
        self._shadow_enabled = bool(config.observer_shadow_enabled)
        self._shadow_policy: Optional[ShadowPolicyScorer] = None
        if self._shadow_enabled:
            self._shadow_policy = ShadowPolicyScorer(
                enabled=True,
                include_loading=bool(config.observer_shadow_include_loading),
                min_confidence=float(config.observer_shadow_min_confidence),
                max_disagreement_examples=20,
            )

        self._stats_lock = threading.Lock()
        self._submitted_events = 0
        self._written_events = 0
        self._dropped_events = 0
        self._event_queue_max_depth = 0

        self._submitted_images = 0
        self._written_images = 0
        self._dropped_images = 0
        self._image_queue_max_depth = 0

        self._flush_count = 0
        self._write_errors = 0
        self._last_error = ""

        self._next_periodic_frame_sample_monotonic = 0.0
        self._next_high_threat_sample_monotonic = 0.0

    def start(self):
        """Start observer worker threads and initialize output files."""
        if self._running:
            return

        timestamp_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._event_log_path = self._output_dir / f"observer_events_{timestamp_stamp}.jsonl"
        self._coverage_path = self._output_dir / "coverage_latest.json"
        self._stats_path = self._output_dir / "observer_stats_latest.json"
        if self._shadow_enabled:
            self._shadow_metrics_path = self._output_dir / "shadow_metrics_latest.json"

        if self._capture_full_frames:
            self._image_output_dir.mkdir(parents=True, exist_ok=True)
            self._image_index_path = self._output_dir / "observer_images_index.jsonl"

        self._stop_event.clear()
        self._running = True

        self._event_writer_thread = threading.Thread(
            target=self._event_writer_loop,
            name="observer_event_writer",
            daemon=True,
        )
        self._event_writer_thread.start()

        if self._capture_full_frames and cv2 is not None:
            self._image_writer_thread = threading.Thread(
                target=self._image_writer_loop,
                name="observer_image_writer",
                daemon=True,
            )
            self._image_writer_thread.start()
        elif self._capture_full_frames and cv2 is None:
            self._logger.warning("Observer image capture disabled: cv2 import unavailable.")

    def publish_event(self, event: ObservationEvent) -> bool:
        """Publish an observation event without blocking the caller."""
        if not self._running:
            return False

        event_payload = event.to_dict()
        with self._stats_lock:
            self._submitted_events += 1

        return self._enqueue_non_blocking(self._event_queue, event_payload, is_image=False)

    def publish_frame_sample(
        self,
        frame: np.ndarray,
        frame_id: int,
        reason: str,
        scenario_tags: Dict[str, str],
        wall_timestamp: Optional[float] = None,
    ) -> bool:
        """Publish a frame sample write request without blocking the caller."""
        if not self._running:
            return False
        if not self._capture_full_frames:
            return False
        if cv2 is None:
            return False
        if frame is None:
            return False

        with self._stats_lock:
            self._submitted_images += 1

        image_item = {
            "frame": frame.copy(),
            "frame_id": int(frame_id),
            "reason": str(reason),
            "scenario_tags": dict(scenario_tags),
            "wall_timestamp": float(time.time() if wall_timestamp is None else wall_timestamp),
        }
        return self._enqueue_non_blocking(self._image_queue, image_item, is_image=True)

    def maybe_publish_periodic_frame_sample(
        self,
        frame: np.ndarray,
        frame_id: int,
        scenario_tags: Dict[str, str],
        wall_timestamp: Optional[float] = None,
    ) -> bool:
        """Capture periodic frame samples at configured low-frequency cadence."""
        if not self._capture_full_frames:
            return False
        if self._full_frame_sample_interval_s <= 0.0:
            return False

        now_monotonic = time.monotonic()
        if now_monotonic < self._next_periodic_frame_sample_monotonic:
            return False

        self._next_periodic_frame_sample_monotonic = now_monotonic + self._full_frame_sample_interval_s
        return self.publish_frame_sample(
            frame=frame,
            frame_id=frame_id,
            reason="periodic",
            scenario_tags=scenario_tags,
            wall_timestamp=wall_timestamp,
        )

    def maybe_publish_high_threat_frame_sample(
        self,
        frame: np.ndarray,
        frame_id: int,
        scenario_tags: Dict[str, str],
        max_danger_priority: int,
        wall_timestamp: Optional[float] = None,
    ) -> bool:
        """Capture frame samples for high-threat scenarios with cooldown throttling."""
        if not self._capture_high_threat_frames:
            return False
        if int(max_danger_priority) < self._high_threat_min_danger:
            return False

        now_monotonic = time.monotonic()
        if now_monotonic < self._next_high_threat_sample_monotonic:
            return False

        self._next_high_threat_sample_monotonic = now_monotonic + self._high_threat_cooldown_s
        return self.publish_frame_sample(
            frame=frame,
            frame_id=frame_id,
            reason=f"high_threat_d{int(max_danger_priority)}",
            scenario_tags=scenario_tags,
            wall_timestamp=wall_timestamp,
        )

    def _enqueue_non_blocking(self, target_queue: queue.Queue, payload: object, is_image: bool) -> bool:
        """Push payload into bounded queue using configured drop policy."""
        accepted = False

        try:
            target_queue.put_nowait(payload)
            accepted = True
        except queue.Full:
            if self._drop_policy == "drop_oldest":
                dropped_one = self._discard_oldest(target_queue, is_image=is_image)
                if dropped_one:
                    try:
                        target_queue.put_nowait(payload)
                        accepted = True
                    except queue.Full:
                        accepted = False
                else:
                    accepted = False
            else:
                accepted = False

            if not accepted:
                if is_image:
                    with self._stats_lock:
                        self._dropped_images += 1
                else:
                    with self._stats_lock:
                        self._dropped_events += 1

        self._record_queue_depth(target_queue, is_image=is_image)
        return accepted

    def _discard_oldest(self, target_queue: queue.Queue, is_image: bool) -> bool:
        """Drop oldest queued payload and account for discard counters."""
        try:
            target_queue.get_nowait()
        except queue.Empty:
            return False

        if is_image:
            with self._stats_lock:
                self._dropped_images += 1
        else:
            with self._stats_lock:
                self._dropped_events += 1
        return True

    def _record_queue_depth(self, target_queue: queue.Queue, is_image: bool):
        """Track current and peak queue depths for diagnostics."""
        queue_depth = int(target_queue.qsize())
        with self._stats_lock:
            if is_image:
                self._image_queue_max_depth = max(self._image_queue_max_depth, queue_depth)
            else:
                self._event_queue_max_depth = max(self._event_queue_max_depth, queue_depth)

    def _event_writer_loop(self):
        """Drain event queue and persist JSONL batches until shutdown."""
        pending_batch = []
        last_flush_monotonic = time.monotonic()
        last_coverage_write_monotonic = last_flush_monotonic
        last_shadow_write_monotonic = last_flush_monotonic

        while not self._stop_event.is_set() or not self._event_queue.empty() or pending_batch:
            timeout_s = max(0.01, self._flush_interval_s / 2.0)
            try:
                queued_item = self._event_queue.get(timeout=timeout_s)
                pending_batch.append(queued_item)
            except queue.Empty:
                pass

            now_monotonic = time.monotonic()
            should_flush = (
                len(pending_batch) >= self._event_batch_size
                or (
                    pending_batch
                    and (now_monotonic - last_flush_monotonic) >= self._flush_interval_s
                )
                or (
                    self._stop_event.is_set()
                    and pending_batch
                    and self._event_queue.empty()
                )
            )

            if should_flush:
                self._write_event_batch(pending_batch)
                pending_batch.clear()
                last_flush_monotonic = now_monotonic

            if (now_monotonic - last_coverage_write_monotonic) >= 2.0:
                self._write_coverage_snapshot()
                last_coverage_write_monotonic = now_monotonic

            if (now_monotonic - last_shadow_write_monotonic) >= 2.0:
                self._write_shadow_snapshot()
                last_shadow_write_monotonic = now_monotonic

        self._write_coverage_snapshot()
        self._write_shadow_snapshot()

    def _image_writer_loop(self):
        """Drain image queue and persist JPEG samples plus metadata index."""
        while not self._stop_event.is_set() or not self._image_queue.empty():
            try:
                image_item = self._image_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                self._write_image_item(image_item)
            except Exception as exc:  # pragma: no cover - defensive logging path
                self._record_write_error(f"image_write_error: {exc}")

    def _write_event_batch(self, batch_items):
        """Write one event batch to JSONL and update coverage + shadow counters."""
        if not batch_items or self._event_log_path is None:
            return

        try:
            self._event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._event_log_path.open("a", encoding="utf-8") as handle:
                for event_payload in batch_items:
                    write_payload = dict(event_payload)

                    if self._shadow_policy is not None:
                        shadow_metadata = self._shadow_policy.score_event(write_payload)
                        if shadow_metadata is not None:
                            write_payload["shadow"] = shadow_metadata

                    handle.write(json.dumps(write_payload, separators=(",", ":")) + "\n")
                    self._coverage_tracker.update(write_payload.get("scenario_tags", {}))

            with self._stats_lock:
                self._written_events += len(batch_items)
                self._flush_count += 1
        except Exception as exc:  # pragma: no cover - defensive logging path
            self._record_write_error(f"event_write_error: {exc}")
            with self._stats_lock:
                self._dropped_events += len(batch_items)

    def _write_image_item(self, image_item: Dict[str, object]):
        """Encode and write one queued frame sample plus metadata index row."""
        if cv2 is None:
            with self._stats_lock:
                self._dropped_images += 1
            return

        frame = image_item.get("frame")
        if frame is None:
            with self._stats_lock:
                self._dropped_images += 1
            return

        frame_id = int(image_item.get("frame_id", 0))
        reason = str(image_item.get("reason", "sample"))
        wall_timestamp = float(image_item.get("wall_timestamp", time.time()))
        scenario_tags = dict(image_item.get("scenario_tags", {}))

        reason_sanitized = self._sanitize_filename_component(reason)
        timestamp_component = datetime.fromtimestamp(wall_timestamp, tz=timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        output_name = f"frame_{frame_id:08d}_{timestamp_component}_{reason_sanitized}.jpg"
        output_path = self._image_output_dir / output_name

        self._image_output_dir.mkdir(parents=True, exist_ok=True)

        encode_ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(self._image_jpeg_quality)],
        )
        if not encode_ok:
            with self._stats_lock:
                self._dropped_images += 1
            return

        with output_path.open("wb") as handle:
            handle.write(encoded.tobytes())

        if self._image_index_path is not None:
            index_row = {
                "frame_id": frame_id,
                "wall_timestamp": wall_timestamp,
                "reason": reason,
                "path": str(output_path),
                "scenario_tags": scenario_tags,
            }
            with self._image_index_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(index_row, separators=(",", ":")) + "\n")

        with self._stats_lock:
            self._written_images += 1

    def _write_coverage_snapshot(self):
        """Persist latest coverage summary to JSON for external reporting."""
        if self._coverage_path is None:
            return

        summary_payload = self._coverage_tracker.summary(top_n=25).to_dict()
        summary_payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            self._coverage_path.parent.mkdir(parents=True, exist_ok=True)
            with self._coverage_path.open("w", encoding="utf-8") as handle:
                json.dump(summary_payload, handle, indent=2, sort_keys=True)
        except Exception as exc:  # pragma: no cover - defensive logging path
            self._record_write_error(f"coverage_write_error: {exc}")

    def _write_shadow_snapshot(self):
        """Persist latest shadow-policy summary to JSON for external reporting."""
        if self._shadow_policy is None or self._shadow_metrics_path is None:
            return

        summary_payload = self._shadow_policy.summary().to_dict()
        summary_payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            self._shadow_metrics_path.parent.mkdir(parents=True, exist_ok=True)
            with self._shadow_metrics_path.open("w", encoding="utf-8") as handle:
                json.dump(summary_payload, handle, indent=2, sort_keys=True)
        except Exception as exc:  # pragma: no cover - defensive logging path
            self._record_write_error(f"shadow_write_error: {exc}")

    def _write_stats_snapshot(self):
        """Persist latest observer counters to JSON."""
        if self._stats_path is None:
            return

        stats_payload = self.stats().__dict__
        stats_payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        try:
            self._stats_path.parent.mkdir(parents=True, exist_ok=True)
            with self._stats_path.open("w", encoding="utf-8") as handle:
                json.dump(stats_payload, handle, indent=2, sort_keys=True)
        except Exception as exc:  # pragma: no cover - defensive logging path
            self._record_write_error(f"stats_write_error: {exc}")

    def _record_write_error(self, error_message: str):
        """Track write failures and emit a warning log line."""
        with self._stats_lock:
            self._write_errors += 1
            self._last_error = str(error_message)
        self._logger.warning("Observer write issue: %s", error_message)

    def stats(self) -> ObserverStats:
        """Return current observer counters and output paths."""
        if self._shadow_policy is not None:
            shadow_summary = self._shadow_policy.summary()
            shadow_seen_events = int(shadow_summary.seen_events)
            shadow_evaluated_events = int(shadow_summary.evaluated_events)
            shadow_agreement_count = int(shadow_summary.agreement_count)
            shadow_disagreement_count = int(shadow_summary.disagreement_count)
            shadow_agreement_rate = float(shadow_summary.agreement_rate)
            shadow_skipped_loading = int(shadow_summary.skipped_loading)
            shadow_skipped_low_confidence = int(shadow_summary.skipped_low_confidence)
        else:
            shadow_seen_events = 0
            shadow_evaluated_events = 0
            shadow_agreement_count = 0
            shadow_disagreement_count = 0
            shadow_agreement_rate = 0.0
            shadow_skipped_loading = 0
            shadow_skipped_low_confidence = 0

        with self._stats_lock:
            return ObserverStats(
                submitted_events=int(self._submitted_events),
                written_events=int(self._written_events),
                dropped_events=int(self._dropped_events),
                event_queue_depth=int(self._event_queue.qsize()),
                event_queue_max_depth=int(self._event_queue_max_depth),
                submitted_images=int(self._submitted_images),
                written_images=int(self._written_images),
                dropped_images=int(self._dropped_images),
                image_queue_depth=int(self._image_queue.qsize()),
                image_queue_max_depth=int(self._image_queue_max_depth),
                flush_count=int(self._flush_count),
                write_errors=int(self._write_errors),
                coverage_total_events=int(self._coverage_tracker.total_events),
                coverage_unique_buckets=int(self._coverage_tracker.unique_buckets),
                shadow_enabled=bool(self._shadow_enabled),
                shadow_seen_events=shadow_seen_events,
                shadow_evaluated_events=shadow_evaluated_events,
                shadow_agreement_count=shadow_agreement_count,
                shadow_disagreement_count=shadow_disagreement_count,
                shadow_agreement_rate=shadow_agreement_rate,
                shadow_skipped_loading=shadow_skipped_loading,
                shadow_skipped_low_confidence=shadow_skipped_low_confidence,
                event_log_path=None if self._event_log_path is None else str(self._event_log_path),
                coverage_path=None if self._coverage_path is None else str(self._coverage_path),
                shadow_metrics_path=None if self._shadow_metrics_path is None else str(self._shadow_metrics_path),
                image_index_path=None if self._image_index_path is None else str(self._image_index_path),
                image_output_dir=None if self._image_output_dir is None else str(self._image_output_dir),
                last_error=str(self._last_error),
            )

    def close(self, join_timeout_s: float = 5.0) -> ObserverStats:
        """Stop worker threads, flush outputs, and return final stats."""
        if self._running:
            self._stop_event.set()

            if self._event_writer_thread is not None:
                self._event_writer_thread.join(timeout=max(0.1, float(join_timeout_s)))
            if self._image_writer_thread is not None:
                self._image_writer_thread.join(timeout=max(0.1, float(join_timeout_s)))

            self._running = False

        self._write_coverage_snapshot()
        self._write_shadow_snapshot()
        self._write_stats_snapshot()
        return self.stats()

    @staticmethod
    def _sanitize_filename_component(raw_component: str) -> str:
        """Sanitize filename fragment for cross-platform safe output names."""
        safe_chars = []
        for char in str(raw_component):
            if char.isalnum() or char in {"-", "_"}:
                safe_chars.append(char)
            else:
                safe_chars.append("_")
        sanitized = "".join(safe_chars).strip("_")
        return sanitized or "sample"
