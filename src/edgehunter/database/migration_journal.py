import sqlite3
import json
from typing import Dict, Any, List

from src.edgehunter.database.schema import ensure_schema, _connect
from src.edgehunter.database.migration_models import (
    MigrationResult,
    MigrationResultStatus,
    MigrationExecutionMode
)

def ensure_migration_journal(db_path: str) -> None:
    """Ensures that the schema_migrations table exists by invoking ensure_schema."""
    ensure_schema(db_path)

def record_migration_result(db_path: str, result: MigrationResult, version: int, name: str, checksum: str, execution_mode: str) -> int:
    """Records a migration execution in the journal."""
    ensure_schema(db_path)
    connection = _connect(db_path)
    try:
        cursor = connection.cursor()
        
        # Check if already exists with success to ensure idempotency
        cursor.execute("SELECT status FROM schema_migrations WHERE migration_id = ?", (result.migration_id,))
        row = cursor.fetchone()
        if row and row[0] in [MigrationResultStatus.APPLIED.value, MigrationResultStatus.SKIPPED.value]:
            # Already applied or skipped successfully
            return cursor.lastrowid or 0

        details_str = json.dumps(result.details)
        
        cursor.execute("""
            INSERT OR REPLACE INTO schema_migrations (
                migration_id, version, name, checksum, status, execution_mode,
                details_json, is_simulated, actionable, not_operational_advice
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.migration_id,
            version,
            name,
            checksum,
            result.status.value,
            execution_mode,
            details_str,
            int(result.is_simulated),
            int(result.actionable),
            int(result.not_operational_advice)
        ))
        
        connection.commit()
        return cursor.lastrowid or 0
    finally:
        connection.close()

def list_applied_migrations(db_path: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Returns a list of all migrations executed."""
    ensure_schema(db_path)
    connection = _connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                migration_id, version, name, checksum, status, applied_at,
                execution_mode, details_json, is_simulated, actionable, not_operational_advice
            FROM schema_migrations
            ORDER BY version ASC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "migration_id": row[0],
                "version": row[1],
                "name": row[2],
                "checksum": row[3],
                "status": row[4],
                "applied_at": row[5],
                "execution_mode": row[6],
                "details": json.loads(row[7]),
                "is_simulated": bool(row[8]),
                "actionable": bool(row[9]),
                "not_operational_advice": bool(row[10])
            })
            
        return results
    finally:
        connection.close()
