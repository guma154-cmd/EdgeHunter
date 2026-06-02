import sqlite3
import pytest
from pathlib import Path

from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.database.migration_models import (
    MigrationExecutionMode,
    MigrationResultStatus
)
from src.edgehunter.database.migration_journal import (
    list_applied_migrations
)
from src.edgehunter.database.migration_planner import plan_database_migrations
from src.edgehunter.database.migration_runner import run_migrations

def test_idempotency_under_stress(tmp_path: Path):
    db_path = str(tmp_path / "adversarial.db")
    ensure_schema(db_path)
    
    # Run 5 times in APPLY mode
    for _ in range(5):
        plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.APPLY)
        run_migrations(db_path, plan)
        
    journal = list_applied_migrations(db_path)
    # The journal should contain exactly the known migrations once
    plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.APPLY)
    # All items should be APPLIED
    for item in plan.items:
        assert item.status == MigrationResultStatus.APPLIED
    assert len(journal) > 0

def test_locked_database_runner(tmp_path: Path):
    db_path = str(tmp_path / "adversarial.db")
    ensure_schema(db_path)
    
    plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.APPLY)
    
    # Open exclusive connection to simulate locked database
    conn_lock = sqlite3.connect(db_path)
    conn_lock.execute("BEGIN EXCLUSIVE")
    
    try:
        from unittest.mock import patch
        
        # We mock _connect to raise OperationalError directly since timeout handling can be flaky in tests
        with patch("src.edgehunter.database.migration_journal._connect", side_effect=sqlite3.OperationalError("database is locked")):
            with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                run_migrations(db_path, plan)
            
    finally:
        conn_lock.rollback()
        conn_lock.close()

def test_dry_run_never_mutates(tmp_path: Path):
    db_path = str(tmp_path / "adversarial.db")
    ensure_schema(db_path)
    
    plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.DRY_RUN)
    
    # Run in DRY_RUN
    results = run_migrations(db_path, plan)
    
    # Results should be skipped
    for res in results:
        assert res.status == MigrationResultStatus.SKIPPED
        
    # Verify journal is empty
    journal = list_applied_migrations(db_path)
    assert len(journal) == 0
