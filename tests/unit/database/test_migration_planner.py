import pytest
import sqlite3

from src.edgehunter.database.migration_planner import (
    plan_database_migrations,
    get_definitions_from_registry
)
from src.edgehunter.database.migration_journal import record_migration_result
from src.edgehunter.database.migration_models import (
    MigrationResult,
    MigrationResultStatus,
    MigrationExecutionMode
)

@pytest.fixture
def empty_db(tmp_path):
    return str(tmp_path / "test_planner.db")

def test_planner_empty_db(empty_db):
    plan = plan_database_migrations(empty_db)
    
    assert plan.execution_mode == MigrationExecutionMode.DRY_RUN
    assert plan.is_simulated is True
    assert plan.actionable is False
    assert len(plan.items) > 0
    assert all(item.status == MigrationResultStatus.PENDING for item in plan.items)

def test_planner_some_applied(empty_db):
    definitions = get_definitions_from_registry()
    assert len(definitions) >= 2
    
    first = definitions[0]
    
    # Fake applying the first one
    result = MigrationResult(
        migration_id=first.migration_id,
        status=MigrationResultStatus.APPLIED,
        details={"info": "Done"}
    )
    
    record_migration_result(
        empty_db, result, first.version, first.name, first.checksum, MigrationExecutionMode.APPLY.value
    )
    
    plan = plan_database_migrations(empty_db)
    
    assert len(plan.items) == len(definitions)
    assert plan.items[0].status == MigrationResultStatus.APPLIED
    assert plan.items[1].status == MigrationResultStatus.PENDING
