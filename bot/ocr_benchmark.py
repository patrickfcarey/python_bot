"""OCR-specific latency benchmarking utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List
import time


@dataclass(frozen=True)
class OCRBenchmarkSample:
    capture_ms: float
    teammate_ocr_ms: float
    ground_ocr_ms: float
    total_ms: float
    teammate_count: int
    ground_count: int


@dataclass(frozen=True)
class OCRStageStats:
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float


@dataclass(frozen=True)
class OCRBenchmarkSummary:
    samples: int
    mode: str
    wall_time_seconds: float
    achieved_fps: float
    avg_total_ms: float
    median_total_ms: float
    p95_total_ms: float
    p99_total_ms: float
    max_total_ms: float
    avg_teammate_count: float
    avg_ground_count: float
    stage_stats: Dict[str, OCRStageStats]
    generated_at_utc: str
    annotations: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """To dict.

        Parameters:
            None.

        Local Variables:
            k: Local variable for k used in this routine.
            payload: Local variable for payload used in this routine.
            v: Local variable for v used in this routine.

        Returns:
            A value matching the annotated return type `Dict[str, Any]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        payload = asdict(self)
        payload["stage_stats"] = {k: asdict(v) for k, v in self.stage_stats.items()}
        return payload


class OCRLatencyMonitor:
    def __init__(self, mode: str):
        """Initialize a new `OCRLatencyMonitor` instance.

        Parameters:
            mode: Parameter for mode used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.mode = str(mode)
        self._samples: List[OCRBenchmarkSample] = []
        self._start_wall = time.monotonic()
        self._annotations: Dict[str, Any] = {}

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

    def record(self, sample: OCRBenchmarkSample):
        """Record.

        Parameters:
            sample: Parameter for sample used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        self._samples.append(sample)

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

    def _build_stage_stats(self, values: List[float]) -> OCRStageStats:
        """Internal helper to build stage stats.

        Parameters:
            values: Parameter for values used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `OCRStageStats`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        if not values:
            return OCRStageStats(0.0, 0.0, 0.0, 0.0, 0.0)

        return OCRStageStats(
            avg_ms=float(mean(values)),
            median_ms=float(median(values)),
            p95_ms=self._percentile(values, 95.0),
            p99_ms=self._percentile(values, 99.0),
            max_ms=float(max(values)),
        )

    def summarize(self) -> OCRBenchmarkSummary:
        """Summarize.

        Parameters:
            None.

        Local Variables:
            achieved_fps: Local variable for achieved fps used in this routine.
            capture_values: Local variable for capture values used in this routine.
            ground_values: Local variable for ground values used in this routine.
            sample: Local variable for sample used in this routine.
            teammate_values: Local variable for teammate values used in this routine.
            total_values: Local variable for total values used in this routine.
            wall_elapsed: Local variable for wall elapsed used in this routine.

        Returns:
            A value matching the annotated return type `OCRBenchmarkSummary`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        wall_elapsed = max(1e-9, time.monotonic() - self._start_wall)
        total_values = [sample.total_ms for sample in self._samples]
        capture_values = [sample.capture_ms for sample in self._samples]
        teammate_values = [sample.teammate_ocr_ms for sample in self._samples]
        ground_values = [sample.ground_ocr_ms for sample in self._samples]

        achieved_fps = float(len(self._samples) / wall_elapsed)

        return OCRBenchmarkSummary(
            samples=len(self._samples),
            mode=self.mode,
            wall_time_seconds=float(wall_elapsed),
            achieved_fps=achieved_fps,
            avg_total_ms=float(mean(total_values)) if total_values else 0.0,
            median_total_ms=float(median(total_values)) if total_values else 0.0,
            p95_total_ms=self._percentile(total_values, 95.0),
            p99_total_ms=self._percentile(total_values, 99.0),
            max_total_ms=float(max(total_values)) if total_values else 0.0,
            avg_teammate_count=float(mean([sample.teammate_count for sample in self._samples])) if self._samples else 0.0,
            avg_ground_count=float(mean([sample.ground_count for sample in self._samples])) if self._samples else 0.0,
            stage_stats={
                "capture": self._build_stage_stats(capture_values),
                "teammate_ocr": self._build_stage_stats(teammate_values),
                "ground_ocr": self._build_stage_stats(ground_values),
            },
            generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            annotations=dict(self._annotations),
        )


class JSONOCRBenchmarkReporter:
    def __init__(self, output_dir: Path):
        """Initialize a new `JSONOCRBenchmarkReporter` instance.

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

    def write(self, summary: OCRBenchmarkSummary, output_path: Path | None = None) -> Path:
        """Write.

        Parameters:
            summary: Parameter for summary used in this routine.
            output_path: Parameter containing a filesystem location.

        Local Variables:
            handle: Local variable for handle used in this routine.
            stamp: Local variable for stamp used in this routine.

        Returns:
            A value matching the annotated return type `Path`.

        Side Effects:
            - May perform I/O or logging through called dependencies.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"ocr_bench_report_{stamp}.json"

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(summary.to_dict(), handle, indent=2, sort_keys=True)

        return output_path