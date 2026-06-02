import sqlite3
from src.edgehunter.database.migrations import get_latest_migration_version

def validate_database_migrations(db_path: str) -> dict:
    expected = get_latest_migration_version()
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Check if schema_migrations table exists
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                return {
                    "is_valid": False,
                    "current": "none",
                    "expected": expected,
                    "reason": "schema_migrations table not found"
                }
            
            # Read the latest migration
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                return {
                    "is_valid": False,
                    "current": "none",
                    "expected": expected,
                    "reason": "schema_migrations table is empty"
                }
                
            current = row[0]
            is_valid = (current == expected)
            return {
                "is_valid": is_valid,
                "current": current,
                "expected": expected,
                "reason": "Migration mismatch" if not is_valid else "Valid"
            }
            
    except sqlite3.Error as e:
        return {
            "is_valid": False,
            "current": "error",
            "expected": expected,
            "reason": f"Database error: {str(e)}"
        }
