"""Tests for STORY-01-010 SQLite backup automation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import gzip
from pathlib import Path
import socket
import sqlite3
import tempfile

import pytest

from src.edgehunter.database.backup import (
    BACKUP_SCHEDULE_HOUR_UTC,
    BACKUP_SCHEDULE_MINUTE_UTC,
    DEFAULT_KEEP_LAST,
    create_sqlite_backup,
    get_backup_schedule_utc,
)
from src.edgehunter.database.schema import configure_connection, ensure_schema


@pytest.fixture
def temp_db() -> str:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        db_path = handle.name
    ensure_schema(db_path)
    _seed_database(db_path)
    yield db_path
    Path(db_path).unlink(missing_ok=True)
    Path(f"{db_path}-wal").unlink(missing_ok=True)
    Path(f"{db_path}-shm").unlink(missing_ok=True)


def _seed_database(db_path: str) -> None:
    connection = sqlite3.connect(db_path)
    configure_connection(connection)
    try:
        connection.execute(
            """
            INSERT INTO matches (
                match_id,
                home_team,
                away_team,
                league,
                match_date
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "backup-match-1",
                "Flamengo",
                "Palmeiras",
                "Brasileirao",
                "2026-05-24T18:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO odds_snapshots (
                match_id,
                pinnacle_home,
                pinnacle_draw,
                pinnacle_away,
                pinnacle_timestamp,
                max_latency_seconds,
                bookmakers_synced,
                valid_for_analysis,
                snapshot_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "backup-match-1",
                2.10,
                3.40,
                3.20,
                "2026-05-24T17:55:00+00:00",
                0,
                '["pinnacle"]',
                1,
                "2026-05-24T17:55:00+00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_backup_is_created_successfully(temp_db: str, tmp_path: Path) -> None:
    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path / "backups",
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is True
    assert result.error is None
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.backup_path.suffix == ".gz"
    assert result.integrity_check == "ok"
    assert result.backups_after_rotation == 1


def test_backup_directory_is_created_automatically(temp_db: str, tmp_path: Path) -> None:
    backup_dir = tmp_path / "nested" / "sqlite" / "backups"

    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=backup_dir,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is True
    assert backup_dir.exists()


def test_backup_file_is_gzipped_and_contains_sqlite_data(temp_db: str, tmp_path: Path) -> None:
    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.backup_path is not None
    with gzip.open(result.backup_path, "rb") as handle:
        header = handle.read(16)

    assert header.startswith(b"SQLite format 3")


def test_integrity_check_passes_for_generated_backup(temp_db: str, tmp_path: Path) -> None:
    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.integrity_check == "ok"


def test_rotation_keeps_only_last_seven_backups(temp_db: str, tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    for minute_offset in range(9):
        result = create_sqlite_backup(
            db_path=Path(temp_db),
            backup_dir=backup_dir,
            keep_last=DEFAULT_KEEP_LAST,
            now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC) + timedelta(minutes=minute_offset),
        )
        assert result.success is True

    backups = sorted(backup_dir.glob("*.db.gz"))
    assert len(backups) == DEFAULT_KEEP_LAST
    assert backups[0].name.endswith("20260524T030200Z.db.gz")
    assert backups[-1].name.endswith("20260524T030800Z.db.gz")


def test_missing_database_fails_in_controlled_way(tmp_path: Path) -> None:
    result = create_sqlite_backup(
        db_path=tmp_path / "missing.db",
        backup_dir=tmp_path / "backups",
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is False
    assert result.backup_path is None
    assert result.error is not None
    assert "not found" in result.error


def test_now_must_be_timezone_aware(temp_db: str, tmp_path: Path) -> None:
    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0),
    )

    assert result.success is False
    assert result.error == "now must be timezone-aware"


def test_wal_checkpoint_happens_before_backup_copy(
    temp_db: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.edgehunter.database.backup as backup_module

    call_order: list[str] = []
    original_checkpoint = backup_module._run_wal_checkpoint
    original_copy = backup_module._copy_database_via_backup
    original_integrity = backup_module._validate_backup_integrity

    def record_checkpoint(db_path: Path) -> tuple[int, int, int]:
        call_order.append("checkpoint")
        return original_checkpoint(db_path)

    def record_copy(source_db: Path, plain_backup: Path) -> None:
        call_order.append("copy")
        original_copy(source_db, plain_backup)

    def record_integrity(plain_backup: Path) -> str:
        call_order.append("integrity")
        return original_integrity(plain_backup)

    monkeypatch.setattr(backup_module, "_run_wal_checkpoint", record_checkpoint)
    monkeypatch.setattr(backup_module, "_copy_database_via_backup", record_copy)
    monkeypatch.setattr(backup_module, "_validate_backup_integrity", record_integrity)

    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is True
    assert call_order[:3] == ["checkpoint", "copy", "integrity"]


def test_backup_does_not_depend_on_network(temp_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("network access should not be attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is True


def test_failure_path_does_not_create_backup_artifact(temp_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import src.edgehunter.database.backup as backup_module

    def explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise sqlite3.OperationalError("simulated checkpoint failure")

    monkeypatch.setattr(backup_module, "_run_wal_checkpoint", explode)

    result = create_sqlite_backup(
        db_path=Path(temp_db),
        backup_dir=tmp_path,
        now=datetime(2026, 5, 24, 3, 0, tzinfo=UTC),
    )

    assert result.success is False
    assert result.error == "simulated checkpoint failure"
    assert list(tmp_path.glob("*.db.gz")) == []


def test_backup_schedule_metadata_is_03_00_utc() -> None:
    schedule = get_backup_schedule_utc()

    assert schedule == {
        "hour": BACKUP_SCHEDULE_HOUR_UTC,
        "minute": BACKUP_SCHEDULE_MINUTE_UTC,
        "timezone": "UTC",
    }
