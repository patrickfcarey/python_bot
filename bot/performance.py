"""Performance measurement utilities for frame-loop benchmarking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List
import time


@dataclass(frozen=True)
class FrameTiming:
    capture_ms: float
    vision_ms: float
    state_ms: float
    decision_ms: float
    control_ms: float
    sleep_ms: float
    total_ms: float


@dataclass(frozen=True)
class StageStats:
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float


@dataclass(frozen=True)
class PerformanceSummary:
    target_fps: float
    warmup_frames: int
    sampled_frames: int
    wall_time_seconds: float
    achieved_fps: float
    avg_frame_ms: float
    median_frame_ms: float
    p95_frame_ms: float
    p99_frame_ms: float
    max_frame_ms: float
    stage_stats: Dict[str, StageStats]
    meets_target: bool
    generated_at_utc: str
    annotations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """To dict.

        Parameters:
            None.

        Local Variables:
            k: Local variable for k used in this routine.
            payload: Local variable for payload used in this routine.
            v: Local variable for v used in this routine.

        Returns:
            A value matching the annotated return type `Dict[str, object]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        payload = asdict(self)
        payload["stage_stats"] = {k: asdict(v) for k, v in self.stage_stats.items()}
        return payload


class PerformanceMonitor:
    def __init__(self, target_fps: float, warmup_frames: int = 120):
        """Initialize a new `PerformanceMonitor` instance.

        Parameters:
            target_fps: Parameter for target fps used in this routine.
            warmup_frames: Parameter representing image frame data for vision processing.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.target_fps = float(target_fps)
        self.warmup_frames = max(0, int(warmup_frames))
        self._frames_total = 0
        self._samples: List[FrameTiming] = []
        self._start_wall = time.monotonic()
        self._sample_start_wall: float | None = None
        self._last_sample_wall: float | None = None
        self._annotations: Dict[str, Any] = {}

    @property
    def frames_total(self) -> int:
        """Frames total.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `int`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return self._frames_total

    def record(self, timing: FrameTiming):
        """Record.

        Parameters:
            timing: Parameter for timing used in this routine.

        Local Variables:
            now: Local variable for now used in this routine.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._frames_total += 1
        if self._frames_total <= self.warmup_frames:
            return

        now = time.monotonic()
        if self._sample_start_wall is None:
            self._sample_start_wall = now
        self._last_sample_wall = now
        self._samples.append(timing)

    def annotate(self, key: str, value: Any):
        """Annotate.

        Parameters:
            key: Parameter for key used in this routine.
            value: Parameter for value used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        self._annotations[str(key)] = value

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Internal helper to percentile.

        Parameters:
            values: Parameter for values used in this routine.
            percentile: Parameter for percentile used in this routine.

        Local Variables:
            high: Local variable for high used in this routine.
            low: Local variable for low used in this routine.
            rank: Local variable for rank used in this routine.
            sorted_values: Local variable for sorted values used in this routine.
            weight: Local variable for weight used in this routine.

        Returns:
            A value matching the annotated return type `float`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return float(sorted_values[0])

        rank = (percentile / 100.0) * (len(sorted_values) - 1)
        low = int(rank)
        high = min(low + 1, len(sorted_values) - 1)
        weight = rank - low
        return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)

    def _build_stage_stats(self, values: List[float]) -> StageStats:
        """Internal helper to build stage stats.

        Parameters:
            values: Parameter for values used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `StageStats`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        if not values:
            return StageStats(0.0, 0.0, 0.0, 0.0, 0.0)

        return StageStats(
            avg_ms=float(mean(values)),
            median_ms=float(median(values)),
            p95_ms=self._percentile(values, 95.0),
            p99_ms=self._percentile(values, 99.0),
            max_ms=float(max(values)),
        )

    def summarize(self) -> PerformanceSummary:
        """Summarize.

        Parameters:
            None.

        Local Variables:
            achieved_fps: Local variable for achieved fps used in this routine.
            avg_frame_ms: Local variable storing a duration value in milliseconds.
            capture_values: Local variable for capture values used in this routine.
            control_values: Local variable for control values used in this routine.
            decision_values: Local variable for decision values used in this routine.
            frame_values: Local variable representing image frame data for vision processing.
            meets_target: Local variable for meets target used in this routine.
            p95_frame_ms: Local variable storing a duration value in milliseconds.
            sample: Local variable for sample used in this routine.
            sleep_values: Local variable for sleep values used in this routine.
            stage_stats: Local variable for stage stats used in this routine.
            state_values: Local variable carrying runtime state information.
            target_frame_ms: Local variable storing a duration value in milliseconds.
            vision_values: Local variable for vision values used in this routine.
            wall_elapsed: Local variable for wall elapsed used in this routine.

        Returns:
            A value matching the annotated return type `PerformanceSummary`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        frame_values = [sample.total_ms for sample in self._samples]

        capture_values = [sample.capture_ms for sample in self._samples]
        vision_values = [sample.vision_ms for sample in self._samples]
        state_values = [sample.state_ms for sample in self._samples]
        decision_values = [sample.decision_ms for sample in self._samples]
        control_values = [sample.control_ms for sample in self._samples]
        sleep_values = [sample.sleep_ms for sample in self._samples]

        if (
            self._sample_start_wall is not None
            and self._last_sample_wall is not None
            and self._last_sample_wall > self._sample_start_wall
        ):
            wall_elapsed = self._last_sample_wall - self._sample_start_wall
        else:
            wall_elapsed = max(1e-9, time.monotonic() - self._start_wall)

        achieved_fps = float(len(self._samples) / max(1e-9, wall_elapsed))

        avg_frame_ms = float(mean(frame_values)) if frame_values else 0.0
        target_frame_ms = 1000.0 / self.target_fps if self.target_fps > 0 else 0.0

        # We require both average and p95 frame-time to satisfy the target.
        p95_frame_ms = self._percentile(frame_values, 95.0)
        meets_target = bool(
            frame_values
            and self.target_fps > 0
            and avg_frame_ms <= target_frame_ms
            and p95_frame_ms <= target_frame_ms
        )

        stage_stats = {
            "capture": self._build_stage_stats(capture_values),
            "vision": self._build_stage_stats(vision_values),
            "state": self._build_stage_stats(state_values),
            "decision": self._build_stage_stats(decision_values),
            "control": self._build_stage_stats(control_values),
            "sleep": self._build_stage_stats(sleep_values),
        }

        return PerformanceSummary(
            target_fps=self.target_fps,
            warmup_frames=self.warmup_frames,
            sampled_frames=len(self._samples),
            wall_time_seconds=float(wall_elapsed),
            achieved_fps=achieved_fps,
            avg_frame_ms=avg_frame_ms,
            median_frame_ms=float(median(frame_values)) if frame_values else 0.0,
            p95_frame_ms=p95_frame_ms,
            p99_frame_ms=self._percentile(frame_values, 99.0),
            max_frame_ms=float(max(frame_values)) if frame_values else 0.0,
            stage_stats=stage_stats,
            meets_target=meets_target,
            generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            annotations=dict(self._annotations),
        )


class JSONPerfReporter:
    def __init__(self, output_dir: Path):
        """Initialize a new `JSONPerfReporter` instance.

        Parameters:
            output_dir: Parameter containing a filesystem location.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.output_dir = output_dir

    def write(self, summary: PerformanceSummary, output_path: Path | None = None) -> Path:
        """Write.

        Parameters:
            summary: Parameter for summary used in this routine.
            output_path: Parameter containing a filesystem location.

        Local Variables:
            handle: Local variable for handle used in this routine.
            payload: Local variable for payload used in this routine.
            stamp: Local variable for stamp used in this routine.

        Returns:
            A value matching the annotated return type `Path`.

        Side Effects:
            - May perform I/O or logging through called dependencies.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"perf_report_{stamp}.json"

        payload = summary.to_dict()
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

        return output_path


def timing_from_stages(
    capture_ms: float,
    vision_ms: float,
    state_ms: float,
    decision_ms: float,
    control_ms: float,
    sleep_ms: float,
    total_ms: float,
) -> FrameTiming:
    """Timing from stages.

    Parameters:
        capture_ms: Parameter storing a duration value in milliseconds.
        vision_ms: Parameter storing a duration value in milliseconds.
        state_ms: Parameter storing a duration value in milliseconds.
        decision_ms: Parameter storing a duration value in milliseconds.
        control_ms: Parameter storing a duration value in milliseconds.
        sleep_ms: Parameter storing a duration value in milliseconds.
        total_ms: Parameter storing a duration value in milliseconds.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `FrameTiming`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return FrameTiming(
        capture_ms=float(capture_ms),
        vision_ms=float(vision_ms),
        state_ms=float(state_ms),
        decision_ms=float(decision_ms),
        control_ms=float(control_ms),
        sleep_ms=float(sleep_ms),
        total_ms=float(total_ms),
    )