"""Async vision helpers to keep the control loop responsive."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import time
from typing import Callable, Optional

import numpy as np

from bot.game_state import GameState


VisionProcessor = Callable[[np.ndarray, int], GameState]


@dataclass(frozen=True)
class VisionResultSnapshot:
    state: GameState
    age_ms: float
    compute_ms: float
    frame_id: int


@dataclass(frozen=True)
class AsyncVisionStats:
    submitted: int
    dropped: int
    completed: int
    inflight: bool
    inflight_count: int = 0
    max_workers: int = 1
    max_pending_jobs: int = 1
    dropped_stale: int = 0
    dropped_backpressure: int = 0


@dataclass(frozen=True)
class _VisionResultRecord:
    state: GameState
    frame_id: int
    submitted_at: float
    completed_at: float
    compute_ms: float


class AsyncVisionRunner:
    """Run expensive vision processing in background workers.

    Design goals:
    - Keep control loop non-blocking.
    - Keep a bounded queue so vision load cannot grow unbounded.
    - Prefer newest frames by dropping stale queued jobs under pressure.
    - Expose only fresh-enough results to avoid stale decisions.
    """

    def __init__(
        self,
        processor: VisionProcessor,
        max_result_age_ms: float = 150.0,
        max_workers: int = 2,
        max_pending_jobs: int = 4,
        thread_name_prefix: str = "vision_worker",
    ):
        """Initialize a new `AsyncVisionRunner` instance.

        Parameters:
            processor: Parameter for processor used in this routine.
            max_result_age_ms: Parameter storing a duration value in milliseconds.
            max_workers: Parameter for max workers used in this routine.
            max_pending_jobs: Parameter for max pending jobs used in this routine.
            thread_name_prefix: Parameter for thread name prefix used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._processor = processor
        self._max_result_age_ms = float(max_result_age_ms)
        self._max_workers = max(1, int(max_workers))
        self._max_pending_jobs = max(self._max_workers, int(max_pending_jobs))
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix=thread_name_prefix)

        self._inflight_jobs: OrderedDict[Future[_VisionResultRecord], int] = OrderedDict()
        self._latest: Optional[_VisionResultRecord] = None
        self._last_error: Optional[BaseException] = None
        self._next_frame_id = 1

        self._submitted_count = 0
        self._dropped_count = 0
        self._dropped_stale_count = 0
        self._dropped_backpressure_count = 0
        self._completed_count = 0

        self._closed = False

    def _run_job(self, frame: np.ndarray, level_number: int, frame_id: int, submitted_at: float) -> _VisionResultRecord:
        """Internal helper to run job.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            level_number: Parameter for level number used in this routine.
            frame_id: Parameter representing image frame data for vision processing.
            submitted_at: Parameter for submitted at used in this routine.

        Local Variables:
            completed: Local variable for completed used in this routine.
            start: Local variable for start used in this routine.
            state: Local variable carrying runtime state information.

        Returns:
            A value matching the annotated return type `_VisionResultRecord`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        start = time.monotonic()
        state = self._processor(frame, level_number)
        completed = time.monotonic()
        return _VisionResultRecord(
            state=state,
            frame_id=frame_id,
            submitted_at=submitted_at,
            completed_at=completed,
            compute_ms=(completed - start) * 1000.0,
        )

    def _accept_completed(self, result: _VisionResultRecord):
        """Internal helper to accept completed.

        Parameters:
            result: Parameter holding a computed outcome from a prior step.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self._completed_count += 1
        if self._latest is None or result.frame_id > self._latest.frame_id:
            self._latest = result

    def _harvest_if_done(self):
        """Internal helper to harvest if done.

        Parameters:
            None.

        Local Variables:
            future: Local variable for future used in this routine.
            result: Local variable holding a computed outcome from a prior step.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        if not self._inflight_jobs:
            return

        for future in list(self._inflight_jobs.keys()):
            if not future.done():
                continue

            self._inflight_jobs.pop(future, None)

            if future.cancelled():
                continue

            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover - validated via pop_error behavior
                self._last_error = exc
                continue

            self._accept_completed(result)

    def _drop_oldest_cancellable(self) -> bool:
        """Drop oldest queued work so newest frame can enter the pipeline."""
        for future in list(self._inflight_jobs.keys()):
            if future.done():
                continue
            if future.cancel():
                self._inflight_jobs.pop(future, None)
                self._dropped_count += 1
                self._dropped_stale_count += 1
                return True
        return False

    def submit(self, frame: np.ndarray, level_number: int) -> bool:
        """Submit a vision job, dropping stale work under backpressure."""
        if self._closed:
            return False

        self._harvest_if_done()

        while len(self._inflight_jobs) >= self._max_pending_jobs:
            if self._drop_oldest_cancellable():
                continue
            self._dropped_count += 1
            self._dropped_backpressure_count += 1
            return False

        frame_id = self._next_frame_id
        self._next_frame_id += 1

        submitted_at = time.monotonic()
        frame_copy = frame.copy()

        future = self._executor.submit(self._run_job, frame_copy, int(level_number), frame_id, submitted_at)
        self._inflight_jobs[future] = frame_id
        self._submitted_count += 1
        return True

    def latest(self, now_monotonic: Optional[float] = None) -> Optional[VisionResultSnapshot]:
        """Return the latest fresh snapshot or None if no fresh result is available."""
        self._harvest_if_done()

        if self._latest is None:
            return None

        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        age_ms = (now - self._latest.completed_at) * 1000.0
        if age_ms > self._max_result_age_ms:
            return None

        return VisionResultSnapshot(
            state=self._latest.state,
            age_ms=age_ms,
            compute_ms=self._latest.compute_ms,
            frame_id=self._latest.frame_id,
        )

    def pop_error(self) -> Optional[BaseException]:
        """Pop the latest worker error, if any."""
        self._harvest_if_done()
        if self._last_error is None:
            return None

        err = self._last_error
        self._last_error = None
        return err

    def stats(self) -> AsyncVisionStats:
        """Stats.

        Parameters:
            None.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `AsyncVisionStats`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        self._harvest_if_done()
        return AsyncVisionStats(
            submitted=self._submitted_count,
            dropped=self._dropped_count,
            completed=self._completed_count,
            inflight=(len(self._inflight_jobs) > 0),
            inflight_count=len(self._inflight_jobs),
            max_workers=self._max_workers,
            max_pending_jobs=self._max_pending_jobs,
            dropped_stale=self._dropped_stale_count,
            dropped_backpressure=self._dropped_backpressure_count,
        )

    def close(self):
        """Close.

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
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._inflight_jobs.clear()
