"""Tests for OCR latency benchmark monitor."""

from bot.ocr_benchmark import OCRBenchmarkSample, OCRLatencyMonitor


def test_ocr_latency_monitor_summarizes_basic_stats():
    monitor = OCRLatencyMonitor(mode="both")
    monitor.record(
        OCRBenchmarkSample(
            capture_ms=2.0,
            teammate_ocr_ms=10.0,
            ground_ocr_ms=6.0,
            total_ms=18.5,
            teammate_count=1,
            ground_count=2,
        )
    )
    monitor.record(
        OCRBenchmarkSample(
            capture_ms=3.0,
            teammate_ocr_ms=12.0,
            ground_ocr_ms=7.0,
            total_ms=22.0,
            teammate_count=2,
            ground_count=1,
        )
    )

    summary = monitor.summarize()

    assert summary.samples == 2
    assert summary.mode == "both"
    assert summary.avg_total_ms > 0.0
    assert summary.p95_total_ms >= summary.median_total_ms
    assert "capture" in summary.stage_stats
    assert "teammate_ocr" in summary.stage_stats
    assert "ground_ocr" in summary.stage_stats
    assert summary.avg_teammate_count == 1.5
    assert summary.avg_ground_count == 1.5


def test_ocr_latency_monitor_handles_empty_samples():
    summary = OCRLatencyMonitor(mode="teammate").summarize()

    assert summary.samples == 0
    assert summary.mode == "teammate"
    assert summary.avg_total_ms == 0.0
    assert summary.stage_stats["capture"].avg_ms == 0.0