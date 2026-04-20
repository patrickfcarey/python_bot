"""Tests for performance monitoring framework."""

from pathlib import Path

from bot.performance import JSONPerfReporter, PerformanceMonitor, timing_from_stages


def _timing(total_ms: float):
    return timing_from_stages(
        capture_ms=2.0,
        vision_ms=4.0,
        state_ms=1.0,
        decision_ms=2.0,
        control_ms=1.0,
        sleep_ms=max(0.0, total_ms - 10.0),
        total_ms=total_ms,
    )


def test_performance_monitor_meets_target():
    monitor = PerformanceMonitor(target_fps=50.0, warmup_frames=2)

    monitor.record(_timing(30.0))
    monitor.record(_timing(30.0))

    for _ in range(12):
        monitor.record(_timing(18.0))

    summary = monitor.summarize()

    assert summary.sampled_frames == 12
    assert summary.meets_target is True
    assert summary.avg_frame_ms <= 20.0
    assert summary.p95_frame_ms <= 20.0


def test_performance_monitor_fails_target_on_p95():
    monitor = PerformanceMonitor(target_fps=50.0, warmup_frames=0)

    for _ in range(8):
        monitor.record(_timing(18.0))
    for _ in range(2):
        monitor.record(_timing(28.0))

    summary = monitor.summarize()

    assert summary.sampled_frames == 10
    assert summary.meets_target is False
    assert summary.p95_frame_ms > 20.0


def test_json_perf_reporter_writes_file(tmp_path: Path):
    monitor = PerformanceMonitor(target_fps=50.0, warmup_frames=0)
    for _ in range(3):
        monitor.record(_timing(18.0))

    summary = monitor.summarize()
    reporter = JSONPerfReporter(tmp_path)
    out_path = reporter.write(summary)

    assert out_path.exists()
    assert out_path.suffix == ".json"

def test_performance_monitor_annotations_are_in_summary():
    monitor = PerformanceMonitor(target_fps=50.0, warmup_frames=0)
    monitor.record(_timing(18.0))
    monitor.annotate("vision_mode", "async")
    monitor.annotate("vision_async_dropped", 3)

    summary = monitor.summarize()
    payload = summary.to_dict()

    assert summary.annotations["vision_mode"] == "async"
    assert summary.annotations["vision_async_dropped"] == 3
    assert payload["annotations"]["vision_mode"] == "async"
