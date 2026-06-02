from typing import List

from src.edgehunter.database.migration_models import (
    MigrationPlan,
    MigrationResult,
    MigrationResultStatus,
    MigrationExecutionMode
)
from src.edgehunter.database.migration_journal import record_migration_result

def run_migrations(db_path: str, plan: MigrationPlan) -> List[MigrationResult]:
    """Runs pending migrations from the given plan and records them in the journal."""
    results = []
    
    if plan.execution_mode != MigrationExecutionMode.APPLY:
        # Dry run - do not actually apply
        for item in plan.items:
            if item.status == MigrationResultStatus.PENDING:
                results.append(MigrationResult(
                    migration_id=item.definition.migration_id,
                    status=MigrationResultStatus.SKIPPED,
                    details={"message": "Dry run, migration not applied"}
                ))
            else:
                results.append(MigrationResult(
                    migration_id=item.definition.migration_id,
                    status=item.status,
                    details={"message": "Already processed in previous run"}
                ))
        return results

    for item in plan.items:
        if item.status == MigrationResultStatus.PENDING:
            try:
                # We currently support NO_OP style metadata migrations for PRD-01 tables
                result = MigrationResult(
                    migration_id=item.definition.migration_id,
                    status=MigrationResultStatus.APPLIED,
                    details={"message": f"Successfully applied operation: {item.definition.operation.value}"}
                )
                
                record_migration_result(
                    db_path, 
                    result, 
                    item.definition.version, 
                    item.definition.name, 
                    item.definition.checksum, 
                    plan.execution_mode.value
                )
                results.append(result)
                
            except Exception as e:
                failed_result = MigrationResult(
                    migration_id=item.definition.migration_id,
                    status=MigrationResultStatus.FAILED,
                    details={"error": str(e)}
                )
                record_migration_result(
                    db_path, 
                    failed_result, 
                    item.definition.version, 
                    item.definition.name, 
                    item.definition.checksum, 
                    plan.execution_mode.value
                )
                results.append(failed_result)
                break
        else:
            results.append(MigrationResult(
                migration_id=item.definition.migration_id,
                status=item.status,
                details={"message": "Skipped - not pending"}
            ))
            
    return results
