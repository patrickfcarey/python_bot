"""Tests for async vision scheduling helpers."""

import threading
import time

import numpy as np

from bot.game_state import GameState
from bot.vision_async import AsyncVisionRunner


def _state_for(level_number: int) -> GameState:
    return GameState(
        automap_matrix=None,
        teammate_detections=[],
        player_position=(0, 0),
        relative_vectors=[],
        enemy_detections=[],
        enemy_tracks=[],
        combat_state="idle",
        level_number=level_number,
        loading=False,
    )


def _wait_until(predicate, timeout_s: float = 1.0, step_s: float = 0.005) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(step_s)
    return False


def test_async_runner_multi_worker_keeps_latest_frame():
    def processor(_frame: np.ndarray, level_number: int) -> GameState:
        if level_number == 1:
            time.sleep(0.05)
        else:
            time.sleep(0.005)
        return _state_for(level_number)

    runner = AsyncVisionRunner(processor=processor, max_result_age_ms=200.0, max_workers=2, max_pending_jobs=4)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    try:
        assert runner.submit(frame, 1) is True
        assert runner.submit(frame, 2) is True
        assert _wait_until(lambda: runner.stats().completed >= 2, timeout_s=1.0)

        snapshot = runner.latest()
        assert snapshot is not None
        assert snapshot.state.level_number == 2

        stats = runner.stats()
        assert stats.submitted == 2
        assert stats.completed == 2
        assert stats.dropped == 0
        assert stats.max_workers == 2
        assert stats.max_pending_jobs == 4
    finally:
        runner.close()


def test_async_runner_drops_oldest_queued_when_backlogged():
    def processor(_frame: np.ndarray, level_number: int) -> GameState:
        time.sleep(0.20)
        return _state_for(level_number)

    runner = AsyncVisionRunner(processor=processor, max_result_age_ms=300.0, max_workers=1, max_pending_jobs=2)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    try:
        assert runner.submit(frame, 1) is True
        assert runner.submit(frame, 2) is True
        assert runner.submit(frame, 3) is True

        assert _wait_until(lambda: runner.stats().completed >= 2, timeout_s=1.5)

        snapshot = runner.latest()
        assert snapshot is not None
        assert snapshot.state.level_number == 3

        stats = runner.stats()
        assert stats.submitted == 3
        assert stats.completed == 2
        assert stats.dropped_stale >= 1
        assert stats.dropped_backpressure == 0
    finally:
        runner.close()


def test_async_runner_drops_new_when_all_workers_busy():
    release_event = threading.Event()
    started = {"count": 0}
    lock = threading.Lock()

    def processor(_frame: np.ndarray, level_number: int) -> GameState:
        with lock:
            started["count"] += 1
        release_event.wait(0.4)
        return _state_for(level_number)

    runner = AsyncVisionRunner(processor=processor, max_result_age_ms=300.0, max_workers=2, max_pending_jobs=2)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    try:
        assert runner.submit(frame, 1) is True
        assert runner.submit(frame, 2) is True
        assert _wait_until(lambda: started["count"] >= 2, timeout_s=0.5)

        assert runner.submit(frame, 3) is False

        release_event.set()
        assert _wait_until(lambda: runner.stats().completed >= 2, timeout_s=1.0)

        stats = runner.stats()
        assert stats.submitted == 2
        assert stats.dropped_backpressure >= 1
    finally:
        release_event.set()
        runner.close()


def test_async_runner_enforces_max_result_age():
    runner = AsyncVisionRunner(processor=lambda _f, lvl: _state_for(lvl), max_result_age_ms=5.0)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    try:
        assert runner.submit(frame, 3) is True

        snapshot = None
        for _ in range(20):
            snapshot = runner.latest()
            if snapshot is not None:
                break
            time.sleep(0.005)

        assert snapshot is not None

        time.sleep(0.02)
        assert runner.latest() is None
    finally:
        runner.close()


def test_async_runner_surfaces_worker_errors():
    def processor(_frame: np.ndarray, _level_number: int) -> GameState:
        raise RuntimeError("boom")

    runner = AsyncVisionRunner(processor=processor, max_result_age_ms=200.0)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)

    try:
        assert runner.submit(frame, 1) is True

        err = None
        for _ in range(200):
            err = runner.pop_error()
            if err is not None:
                break
            time.sleep(0.005)

        assert isinstance(err, RuntimeError)
        assert "boom" in str(err)
    finally:
        runner.close()

