"""
Minimal SQLite observability helpers for contention analysis.

These utilities are intentionally dependency-light so they can be reused by
benchmarks, scripts, and future runtime instrumentation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from threading import Lock
from typing import DefaultDict
import math
import sqlite3
import time


@dataclass(frozen=True)
class WriteSample:
    """Single measured write transaction."""

    writer_name: str
    wait_ms: float
    tx_ms: float
    locked_error: bool


def percentile(values: list[float], pct: float) -> float:
    """Return a simple interpolated percentile."""
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])

    ordered = sorted(float(v) for v in values)
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]

    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


class SQLiteWriteObserver:
    """Thread-safe collector for write lock and transaction metrics."""

    def __init__(self) -> None:
        self._samples: list[WriteSample] = []
        self._lock = Lock()

    def record(self, writer_name: str, wait_ms: float, tx_ms: float, locked_error: bool = False) -> None:
        sample = WriteSample(
            writer_name=writer_name,
            wait_ms=wait_ms,
            tx_ms=tx_ms,
            locked_error=locked_error,
        )
        with self._lock:
            self._samples.append(sample)

    @property
    def samples(self) -> list[WriteSample]:
        with self._lock:
            return list(self._samples)

    def summary(self, elapsed_seconds: float) -> dict:
        samples = self.samples
        total_writes = len(samples)
        total_locked_errors = sum(1 for sample in samples if sample.locked_error)
        waits = [sample.wait_ms for sample in samples if not sample.locked_error]
        txs = [sample.tx_ms for sample in samples if not sample.locked_error]

        by_writer: DefaultDict[str, list[WriteSample]] = defaultdict(list)
        for sample in samples:
            by_writer[sample.writer_name].append(sample)

        per_writer = {}
        for writer_name, writer_samples in sorted(by_writer.items()):
            successful = [sample for sample in writer_samples if not sample.locked_error]
            writer_waits = [sample.wait_ms for sample in successful]
            writer_txs = [sample.tx_ms for sample in successful]
            per_writer[writer_name] = {
                "writes": len(writer_samples),
                "locked_errors": sum(1 for sample in writer_samples if sample.locked_error),
                "writes_per_min": round(len(writer_samples) / max(elapsed_seconds / 60.0, 1e-9), 2),
                "p95_wait_ms": round(percentile(writer_waits, 0.95), 2),
                "p95_tx_ms": round(percentile(writer_txs, 0.95), 2),
                "max_wait_ms": round(max(writer_waits, default=0.0), 2),
                "max_tx_ms": round(max(writer_txs, default=0.0), 2),
            }

        return {
            "total_writes": total_writes,
            "locked_errors": total_locked_errors,
            "writes_per_second": round(total_writes / max(elapsed_seconds, 1e-9), 2),
            "writes_per_min": round(total_writes / max(elapsed_seconds / 60.0, 1e-9), 2),
            "p95_wait_ms": round(percentile(waits, 0.95), 2),
            "p95_tx_ms": round(percentile(txs, 0.95), 2),
            "avg_wait_ms": round(mean(waits), 2) if waits else 0.0,
            "avg_tx_ms": round(mean(txs), 2) if txs else 0.0,
            "max_wait_ms": round(max(waits, default=0.0), 2),
            "max_tx_ms": round(max(txs, default=0.0), 2),
            "per_writer": per_writer,
        }


def connect_sqlite(db_path: str, busy_timeout_ms: int = 5000) -> sqlite3.Connection:
    """
    Open a SQLite connection with the same concurrency profile used by EdgeHunter.
    """
    connection = sqlite3.connect(
        db_path,
        timeout=busy_timeout_ms / 1000.0,
        check_same_thread=False,
    )
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def measured_write_transaction(
    connection: sqlite3.Connection,
    observer: SQLiteWriteObserver,
    writer_name: str,
    operation,
) -> bool:
    """
    Execute one measured write transaction.

    Returns True on success, False on lock timeout.
    """
    tx_start = time.perf_counter()
    wait_start = tx_start
    try:
        connection.execute("BEGIN IMMEDIATE")
        wait_ms = (time.perf_counter() - wait_start) * 1000.0
        operation(connection)
        connection.commit()
        tx_ms = (time.perf_counter() - tx_start) * 1000.0
        observer.record(writer_name=writer_name, wait_ms=wait_ms, tx_ms=tx_ms)
        return True
    except sqlite3.OperationalError as exc:
        connection.rollback()
        locked = "locked" in str(exc).lower()
        tx_ms = (time.perf_counter() - tx_start) * 1000.0
        observer.record(
            writer_name=writer_name,
            wait_ms=(time.perf_counter() - wait_start) * 1000.0,
            tx_ms=tx_ms,
            locked_error=locked,
        )
        if locked:
            return False
        raise
