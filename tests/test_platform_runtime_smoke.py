"""Platform runtime smoke metric tests."""

from experiments.platform.runtime_smoke import percentile, summarize


def test_percentile_uses_nearest_rank():
    assert percentile([4.0, 1.0, 3.0, 2.0], 0.50) == 2.0
    assert percentile([4.0, 1.0, 3.0, 2.0], 0.95) == 4.0


def test_summarize_reports_failures_and_latency():
    rows = [
        {"ok": True, "latency_seconds": 0.4},
        {"ok": False, "latency_seconds": 0.2},
        {"ok": True, "latency_seconds": 0.8},
    ]

    summary = summarize(rows, wall_seconds=1.0)

    assert summary["requests"] == 3
    assert summary["successes"] == 2
    assert summary["failures"] == 1
    assert summary["success_rate"] == 2 / 3
    assert summary["throughput_requests_per_second"] == 2.0
    assert summary["latency_seconds"]["median"] == 0.4
    assert summary["latency_seconds"]["p95"] == 0.8
