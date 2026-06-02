import pytest
from src.edgehunter.database.migration_models import (
    MigrationOperation,
    MigrationSafetyLevel,
    MigrationExecutionMode,
    MigrationResultStatus,
    MigrationDefinition,
    MigrationPlanItem,
    MigrationPlan,
    MigrationResult,
)

def test_create_valid_migration_definition():
    definition = MigrationDefinition(
        migration_id="0001_test",
        version=1,
        name="Test Migration",
        operation=MigrationOperation.CREATE_TABLE,
        safety_level=MigrationSafetyLevel.SAFE,
        checksum="abcd123"
    )
    assert definition.migration_id == "0001_test"
    assert definition.is_simulated is True
    assert definition.actionable is False
    assert definition.not_operational_advice is True

def test_migration_definition_missing_strings():
    with pytest.raises(ValueError, match="cannot be empty"):
        MigrationDefinition(
            migration_id="",
            version=1,
            name="Test",
            operation=MigrationOperation.CREATE_TABLE,
            safety_level=MigrationSafetyLevel.SAFE,
            checksum="abcd123"
        )

def test_migration_definition_forbidden_language():
    with pytest.raises(ValueError, match="Forbidden operational language"):
        MigrationDefinition(
            migration_id="0001_execute_bankroll",
            version=1,
            name="Execute Bankroll",
            operation=MigrationOperation.CREATE_TABLE,
            safety_level=MigrationSafetyLevel.SAFE,
            checksum="abcd123"
        )

def test_migration_definition_invalid_flags():
    with pytest.raises(ValueError, match="strictly simulated and not actionable"):
        MigrationDefinition(
            migration_id="0001_test",
            version=1,
            name="Test",
            operation=MigrationOperation.CREATE_TABLE,
            safety_level=MigrationSafetyLevel.SAFE,
            checksum="abcd123",
            actionable=True
        )

def test_create_valid_migration_plan():
    definition = MigrationDefinition(
        migration_id="0001_test",
        version=1,
        name="Test Migration",
        operation=MigrationOperation.CREATE_TABLE,
        safety_level=MigrationSafetyLevel.SAFE,
        checksum="abcd123"
    )
    item = MigrationPlanItem(definition=definition, status=MigrationResultStatus.PENDING)
    plan = MigrationPlan(
        execution_mode=MigrationExecutionMode.DRY_RUN,
        items=[item]
    )
    assert plan.execution_mode == MigrationExecutionMode.DRY_RUN
    assert len(plan.items) == 1

def test_create_valid_migration_result():
    result = MigrationResult(
        migration_id="0001_test",
        status=MigrationResultStatus.APPLIED,
        details={"info": "success"}
    )
    assert result.status == MigrationResultStatus.APPLIED
    assert result.is_simulated is True

def test_migration_result_destructive_operation_blocked():
    with pytest.raises(ValueError, match="Destructive operations are forbidden"):
        MigrationResult(
            migration_id="0001_test",
            status=MigrationResultStatus.APPLIED,
            details={"sql": "DROP TABLE users;"}
        )

def test_to_dict_deterministic():
    definition = MigrationDefinition(
        migration_id="0001_test",
        version=1,
        name="Test Migration",
        operation=MigrationOperation.CREATE_TABLE,
        safety_level=MigrationSafetyLevel.SAFE,
        checksum="abcd123"
    )
    d = definition.to_dict()
    assert d["migration_id"] == "0001_test"
    assert d["operation"] == "CREATE_TABLE"
    assert d["safety_level"] == "SAFE"
    assert d["is_simulated"] is True
    assert d["actionable"] is False
