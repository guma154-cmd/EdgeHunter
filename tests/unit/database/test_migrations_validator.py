import sqlite3
import pytest
from src.edgehunter.database.migrations import get_latest_migration_version
from src.edgehunter.database.migrations_validator import validate_database_migrations

def test_validate_migrations_no_table(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE mock (id INTEGER)")
        
    result = validate_database_migrations(db_path)
    assert result["is_valid"] is False
    assert result["current"] == "none"
    assert result["expected"] == get_latest_migration_version()
    assert "not found" in result["reason"]

def test_validate_migrations_empty_table(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, description TEXT, applied_at DATETIME)")
        
    result = validate_database_migrations(db_path)
    assert result["is_valid"] is False
    assert result["current"] == "none"
    assert "empty" in result["reason"]

def test_validate_migrations_mismatch(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, description TEXT, applied_at DATETIME)")
        conn.execute("INSERT INTO schema_migrations (version, description) VALUES ('0001', 'test')")
        
    result = validate_database_migrations(db_path)
    assert result["is_valid"] is False
    assert result["current"] == "0001"
    assert "mismatch" in result["reason"].lower()

def test_validate_migrations_valid(tmp_path):
    db_path = str(tmp_path / "test.db")
    expected = get_latest_migration_version()
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, description TEXT, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.execute(f"INSERT INTO schema_migrations (version, description) VALUES ('{expected}', 'test')")
        
    result = validate_database_migrations(db_path)
    assert result["is_valid"] is True
    assert result["current"] == expected
    assert result["expected"] == expected
    assert "Valid" in result["reason"]

def test_validate_migrations_db_error():
    result = validate_database_migrations("/invalid/path/to/nonexistent/dir/db.sqlite")
    assert result["is_valid"] is False
    assert result["current"] == "error"
    assert "Database error" in result["reason"]
