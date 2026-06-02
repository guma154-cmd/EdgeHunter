from typing import List, Dict, Any
import sqlite3

from src.edgehunter.database.migration_models import (
    MigrationPlan,
    MigrationPlanItem,
    MigrationDefinition,
    MigrationOperation,
    MigrationSafetyLevel,
    MigrationExecutionMode,
    MigrationResultStatus
)
from src.edgehunter.database.migration_journal import list_applied_migrations
from src.edgehunter.database.migrations import list_known_migrations
from src.edgehunter.database.schema_introspection import get_existing_tables

def get_definitions_from_registry() -> List[MigrationDefinition]:
    """Converts known migrations to proper definitions."""
    definitions = []
    for rec in list_known_migrations():
        definitions.append(MigrationDefinition(
            migration_id=f"{rec.version}_{rec.description}",
            version=int(rec.version),
            name=rec.description.replace("_", " ").title(),
            operation=MigrationOperation.NO_OP,
            safety_level=MigrationSafetyLevel.SAFE,
            checksum=f"chk_{rec.version}_{rec.description}"
        ))
    return definitions

def plan_database_migrations(db_path: str, *, execution_mode: MigrationExecutionMode = MigrationExecutionMode.DRY_RUN) -> MigrationPlan:
    """Plans migrations by diffing known definitions against the journal."""
    try:
        tables = get_existing_tables(db_path)
        if "schema_migrations" in tables:
            applied_records = list_applied_migrations(db_path)
            applied = {m["migration_id"]: m for m in applied_records}
        else:
            applied = {}
    except sqlite3.Error:
        applied = {}

    definitions = get_definitions_from_registry()
    items = []
    
    for defn in definitions:
        if defn.migration_id in applied:
            rec = applied[defn.migration_id]
            if rec["status"] in ["APPLIED", "SKIPPED"]:
                status = MigrationResultStatus.APPLIED
            else:
                status = MigrationResultStatus.BLOCKED
        else:
            status = MigrationResultStatus.PENDING
            
        items.append(MigrationPlanItem(definition=defn, status=status))

    return MigrationPlan(
        execution_mode=execution_mode,
        items=items
    )
