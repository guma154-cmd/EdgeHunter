import pytest
import sqlite3

from src.edgehunter.database.migration_planner import plan_database_migrations
from src.edgehunter.database.migration_runner import run_migrations
from src.edgehunter.database.migration_models import (
    MigrationExecutionMode,
    MigrationResultStatus
)
from src.edgehunter.database.migration_journal import list_applied_migrations

@pytest.fixture
def empty_db(tmp_path):
    return str(tmp_path / "test_runner.db")

def test_runner_dry_run(empty_db):
    plan = plan_database_migrations(empty_db, execution_mode=MigrationExecutionMode.DRY_RUN)
    results = run_migrations(empty_db, plan)
    
    # In dry run, pending ones should be skipped
    pending_count = sum(1 for item in plan.items if item.status == MigrationResultStatus.PENDING)
    assert len(results) == len(plan.items)
    
    skipped = [r for r in results if r.status == MigrationResultStatus.SKIPPED]
    assert len(skipped) == pending_count
    
    # Ensure nothing was actually written to the journal
    try:
        applied = list_applied_migrations(empty_db)
        assert len(applied) == 0
    except sqlite3.Error:
        pass # Table doesn't exist, which is fine

def test_runner_apply(empty_db):
    plan = plan_database_migrations(empty_db, execution_mode=MigrationExecutionMode.APPLY)
    assert len(plan.items) > 0
    
    results = run_migrations(empty_db, plan)
    
    assert len(results) == len(plan.items)
    assert all(r.status == MigrationResultStatus.APPLIED for r in results)
    
    # Check journal
    applied = list_applied_migrations(empty_db)
    assert len(applied) == len(plan.items)
    assert applied[0]["status"] == "APPLIED"

def test_runner_idempotency(empty_db):
    # Apply first time
    plan1 = plan_database_migrations(empty_db, execution_mode=MigrationExecutionMode.APPLY)
    run_migrations(empty_db, plan1)
    
    # Try again
    plan2 = plan_database_migrations(empty_db, execution_mode=MigrationExecutionMode.APPLY)
    results2 = run_migrations(empty_db, plan2)
    
    assert all(r.status == MigrationResultStatus.APPLIED for r in results2)
    # Check that it didn't duplicate in journal
    applied = list_applied_migrations(empty_db)
    assert len(applied) == len(plan1.items)
