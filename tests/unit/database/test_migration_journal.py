import pytest
import sqlite3

from src.edgehunter.database.migration_journal import (
    ensure_migration_journal,
    record_migration_result,
    list_applied_migrations
)
from src.edgehunter.database.migration_models import (
    MigrationResult,
    MigrationResultStatus,
    MigrationExecutionMode
)

@pytest.fixture
def empty_db(tmp_path):
    return str(tmp_path / "test_journal.db")

def test_ensure_migration_journal(empty_db):
    ensure_migration_journal(empty_db)
    
    # Verify table exists
    conn = sqlite3.connect(empty_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    assert cursor.fetchone() is not None
    conn.close()

def test_record_and_list_applied_migrations(empty_db):
    result = MigrationResult(
        migration_id="0001_initial",
        status=MigrationResultStatus.APPLIED,
        details={"info": "OK"}
    )
    
    record_migration_result(
        empty_db, 
        result, 
        version=1, 
        name="Initial", 
        checksum="abcd", 
        execution_mode=MigrationExecutionMode.APPLY.value
    )
    
    migrations = list_applied_migrations(empty_db)
    assert len(migrations) == 1
    
    m = migrations[0]
    assert m["migration_id"] == "0001_initial"
    assert m["version"] == 1
    assert m["status"] == "APPLIED"
    assert m["details"]["info"] == "OK"
    assert m["is_simulated"] is True
    assert m["actionable"] is False

def test_record_idempotency(empty_db):
    result = MigrationResult(
        migration_id="0001_initial",
        status=MigrationResultStatus.APPLIED,
        details={"info": "OK"}
    )
    
    record_migration_result(
        empty_db, result, 1, "Initial", "abcd", MigrationExecutionMode.APPLY.value
    )
    
    # Try recording again
    record_migration_result(
        empty_db, result, 1, "Initial", "abcd", MigrationExecutionMode.APPLY.value
    )
    
    migrations = list_applied_migrations(empty_db)
    assert len(migrations) == 1  # Should still be 1

def test_record_blocked(empty_db):
    result = MigrationResult(
        migration_id="0002_blocked",
        status=MigrationResultStatus.BLOCKED,
        details={"info": "Blocked"}
    )
    
    record_migration_result(
        empty_db, result, 2, "Blocked", "dcba", MigrationExecutionMode.APPLY.value
    )
    
    migrations = list_applied_migrations(empty_db)
    assert len(migrations) == 1
    assert migrations[0]["status"] == "BLOCKED"

def test_pagination(empty_db):
    for i in range(5):
        result = MigrationResult(
            migration_id=f"000{i}_test",
            status=MigrationResultStatus.APPLIED,
            details={"i": i}
        )
        record_migration_result(
            empty_db, result, i, f"Test {i}", "chk", MigrationExecutionMode.APPLY.value
        )
        
    page1 = list_applied_migrations(empty_db, limit=2, offset=0)
    page2 = list_applied_migrations(empty_db, limit=2, offset=2)
    
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["version"] == 0
    assert page1[1]["version"] == 1
    assert page2[0]["version"] == 2
    assert page2[1]["version"] == 3
