"""SQLite backup utilities for STORY-01-010."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import gzip
from pathlib import Path
import shutil
import sqlite3

from .schema import configure_connection


DEFAULT_KEEP_LAST = 7
BACKUP_SCHEDULE_HOUR_UTC = 3
BACKUP_SCHEDULE_MINUTE_UTC = 0


@dataclass(frozen=True)
class BackupResult:
    success: bool
    backup_path: Path | None
    backup_timestamp: datetime
    backups_after_rotation: int
    error: str | None = None
    integrity_check: str | None = None


def get_backup_schedule_utc() -> dict[str, int | str]:
    """Return the canonical schedule metadata for the daily backup job."""
    return {
        "hour": BACKUP_SCHEDULE_HOUR_UTC,
        "minute": BACKUP_SCHEDULE_MINUTE_UTC,
        "timezone": "UTC",
    }


def create_sqlite_backup(
    db_path: Path,
    backup_dir: Path,
    keep_last: int = DEFAULT_KEEP_LAST,
    now: datetime | None = None,
) -> BackupResult:
    """Create a compressed SQLite backup with WAL checkpoint and rotation."""
    source_db = Path(db_path)
    target_dir = Path(backup_dir)

    try:
        timestamp = _normalize_backup_timestamp(now)
        if keep_last < 1:
            raise ValueError("keep_last must be >= 1")
        if not source_db.exists():
            raise FileNotFoundError(f"database file not found: {source_db}")

        target_dir.mkdir(parents=True, exist_ok=True)

        plain_backup = target_dir / f"{source_db.stem}_{_format_timestamp(timestamp)}.db"
        gzip_backup = plain_backup.with_suffix(".db.gz")

        _run_wal_checkpoint(source_db)
        _copy_database_via_backup(source_db, plain_backup)
        integrity_check = _validate_backup_integrity(plain_backup)
        _gzip_file(plain_backup, gzip_backup)
        backups_after_rotation = _rotate_backups(target_dir, source_db.stem, keep_last)

        return BackupResult(
            success=True,
            backup_path=gzip_backup,
            backup_timestamp=timestamp,
            backups_after_rotation=backups_after_rotation,
            integrity_check=integrity_check,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        fallback_timestamp = (
            datetime.now(UTC).replace(microsecond=0)
            if now is None
            else now.replace(tzinfo=UTC, microsecond=0)
        )
        return BackupResult(
            success=False,
            backup_path=None,
            backup_timestamp=fallback_timestamp,
            backups_after_rotation=_count_existing_backups(target_dir, source_db.stem),
            error=str(exc),
        )


def _normalize_backup_timestamp(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC).replace(microsecond=0)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(UTC).replace(microsecond=0)


def _format_timestamp(timestamp: datetime) -> str:
    return timestamp.strftime("%Y%m%dT%H%M%SZ")


def _open_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    configure_connection(connection)
    return connection


def _run_wal_checkpoint(db_path: Path) -> tuple[int, int, int]:
    connection = _open_connection(db_path)
    try:
        row = connection.execute("PRAGMA wal_checkpoint(FULL);").fetchone()
        if row is None:
            raise sqlite3.DatabaseError("wal_checkpoint(FULL) returned no result")
        return int(row[0]), int(row[1]), int(row[2])
    finally:
        connection.close()


def _copy_database_via_backup(source_db: Path, plain_backup: Path) -> None:
    source_connection = _open_connection(source_db)
    destination_connection = sqlite3.connect(str(plain_backup))
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _validate_backup_integrity(plain_backup: Path) -> str:
    connection = sqlite3.connect(str(plain_backup))
    try:
        result = connection.execute("PRAGMA integrity_check;").fetchone()
    finally:
        connection.close()

    if result is None:
        raise sqlite3.DatabaseError("integrity_check returned no result")

    integrity = str(result[0])
    if integrity != "ok":
        raise sqlite3.DatabaseError(f"integrity_check failed: {integrity}")
    return integrity


def _gzip_file(plain_backup: Path, gzip_backup: Path) -> None:
    with plain_backup.open("rb") as source_handle, gzip.open(gzip_backup, "wb") as target_handle:
        shutil.copyfileobj(source_handle, target_handle)
    plain_backup.unlink(missing_ok=True)


def _rotate_backups(backup_dir: Path, db_stem: str, keep_last: int) -> int:
    backups = sorted(
        backup_dir.glob(f"{db_stem}_*.db.gz"),
        key=lambda item: item.name,
        reverse=True,
    )
    for stale_backup in backups[keep_last:]:
        stale_backup.unlink(missing_ok=True)
    return min(len(backups), keep_last)


def _count_existing_backups(backup_dir: Path, db_stem: str) -> int:
    if not backup_dir.exists():
        return 0
    return len(list(backup_dir.glob(f"{db_stem}_*.db.gz")))
