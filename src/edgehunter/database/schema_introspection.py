"""Read-only SQLite schema introspection helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.edgehunter.database.schema import EXPECTED_COLUMNS


_DASHBOARD_TABLES = (
    "value_detections",
    "gemini_validation_reports",
    "simulated_signal_classifications",
    "simulated_signal_outcomes",
)


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def get_existing_tables(db_path: str) -> set[str]:
    connection = _connect(db_path)
    try:
        cursor = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {str(row["name"]) for row in cursor.fetchall()}
    finally:
        connection.close()


def get_table_columns(db_path: str, table_name: str) -> set[str]:
    if table_name not in EXPECTED_COLUMNS:
        raise ValueError("table_name is not tracked")
    connection = _connect(db_path)
    try:
        cursor = connection.execute(f"PRAGMA table_info({table_name})")
        return {str(row["name"]) for row in cursor.fetchall()}
    finally:
        connection.close()


def validate_expected_schema(db_path: str) -> dict[str, Any]:
    existing_tables = get_existing_tables(db_path)
    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    warnings: list[str] = []

    for table_name in _DASHBOARD_TABLES:
        if table_name not in existing_tables:
            missing_tables.append(table_name)
            continue

        existing_columns = get_table_columns(db_path, table_name)
        expected_columns = set(EXPECTED_COLUMNS[table_name])
        absent_columns = sorted(expected_columns - existing_columns)
        if absent_columns:
            missing_columns[table_name] = absent_columns

    passed = not missing_tables and not missing_columns
    if missing_tables:
        warnings.append("tracked table missing")
    if missing_columns:
        warnings.append("tracked column missing")

    return {
        "passed": passed,
        "missing_tables": sorted(missing_tables),
        "missing_columns": missing_columns,
        "warnings": warnings,
        "is_simulated": True,
        "actionable": False,
    }
