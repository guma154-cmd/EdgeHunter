"""Tests for STORY-01-002 SQLite schema bootstrap."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile

import pytest

from src.edgehunter.core.odds_historian import OddsHistorian
from src.edgehunter.database.schema import (
    DEFAULT_BUSY_TIMEOUT_MS,
    EXPECTED_COLUMNS,
    EXPECTED_INDEXES,
    EXPECTED_TABLES,
    SCHEMA_VERSION,
    configure_connection,
    ensure_schema,
    get_indexes,
    get_pragma_profile,
    get_schema_version,
    get_table_columns,
    verify_schema,
)


@pytest.fixture
def temp_db():
    """Create one isolated SQLite file per test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        db_path = handle.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)
    Path(f"{db_path}-wal").unlink(missing_ok=True)
    Path(f"{db_path}-shm").unlink(missing_ok=True)


class TestSchemaIdempotence:
    def test_first_execution_creates_all_expected_tables(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        assert verify_schema(temp_db) == {table: True for table in EXPECTED_TABLES}

    def test_second_execution_preserves_schema_version(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        version_before = get_schema_version(temp_db)

        assert ensure_schema(temp_db) is True
        version_after = get_schema_version(temp_db)

        assert version_before == SCHEMA_VERSION
        assert version_after == SCHEMA_VERSION

    def test_multiple_executions_do_not_drift_columns(self, temp_db: str) -> None:
        for _ in range(5):
            assert ensure_schema(temp_db) is True

        for table_name, expected_columns in EXPECTED_COLUMNS.items():
            assert get_table_columns(temp_db, table_name) == expected_columns

    def test_bootstrapping_odds_historian_initializes_schema(self, temp_db: str) -> None:
        historian = OddsHistorian(db_path=temp_db)

        assert historian.db_path == temp_db
        assert verify_schema(temp_db) == {table: True for table in EXPECTED_TABLES}


class TestSchemaShape:
    def test_matches_columns_match_prd_contract(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        assert get_table_columns(temp_db, "matches") == EXPECTED_COLUMNS["matches"]

    def test_odds_snapshots_columns_match_prd_contract(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        assert get_table_columns(temp_db, "odds_snapshots") == EXPECTED_COLUMNS["odds_snapshots"]

    def test_scraper_health_columns_match_prd_contract(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        assert get_table_columns(temp_db, "scraper_health") == EXPECTED_COLUMNS["scraper_health"]

    def test_required_indexes_exist(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True
        assert set(EXPECTED_INDEXES).issubset(get_indexes(temp_db))


class TestPragmaProfile:
    def test_required_pragmas_are_active(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True

        pragmas = get_pragma_profile(temp_db)
        assert pragmas["journal_mode"].lower() == "wal"
        assert pragmas["busy_timeout"] == DEFAULT_BUSY_TIMEOUT_MS
        assert pragmas["foreign_keys"] == 1
        # SQLite returns numeric code 1 for NORMAL.
        assert pragmas["synchronous"] == 1

    def test_wal_sidecar_files_are_created_after_write(self, temp_db: str) -> None:
        assert ensure_schema(temp_db) is True

        connection = sqlite3.connect(temp_db)
        configure_connection(connection)
        connection.execute("INSERT INTO matches (match_id, home_team, away_team, league, match_date) VALUES (?, ?, ?, ?, ?)", (
            "match-1",
            "Home",
            "Away",
            "League",
            "2026-05-24T00:00:00+00:00",
        ))
        connection.commit()

        assert Path(f"{temp_db}-wal").exists()
        assert Path(f"{temp_db}-shm").exists()

        connection.close()


class TestFailureScenarios:
    def test_invalid_path_returns_false_without_crashing(self, tmp_path: Path) -> None:
        invalid_path = tmp_path / ("A" * 500) / "edgehunter.db"
        assert ensure_schema(str(invalid_path)) is False

    def test_unwritable_directory_returns_false(self, tmp_path: Path) -> None:
        locked_dir = tmp_path / "locked"
        locked_dir.mkdir()
        locked_dir.chmod(0o444)

        db_path = locked_dir / "edgehunter.db"
        result = ensure_schema(str(db_path))

        assert isinstance(result, bool)
