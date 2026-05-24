"""Tests for SQLite observability helpers used by the contention benchmark."""

from src.edgehunter.database.sqlite_observability import SQLiteWriteObserver, percentile


def test_percentile_handles_empty_values() -> None:
    assert percentile([], 0.95) == 0.0


def test_percentile_interpolates_values() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 0.50) == 25.0


def test_observer_summary_aggregates_per_writer() -> None:
    observer = SQLiteWriteObserver()
    observer.record("writer_a", wait_ms=10.0, tx_ms=20.0)
    observer.record("writer_a", wait_ms=20.0, tx_ms=40.0)
    observer.record("writer_b", wait_ms=5.0, tx_ms=15.0, locked_error=True)

    summary = observer.summary(elapsed_seconds=30.0)

    assert summary["total_writes"] == 3
    assert summary["locked_errors"] == 1
    assert summary["per_writer"]["writer_a"]["writes"] == 2
    assert summary["per_writer"]["writer_b"]["locked_errors"] == 1
