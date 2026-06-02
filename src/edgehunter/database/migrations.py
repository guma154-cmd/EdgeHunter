from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class MigrationRecord:
    version: str
    description: str

_KNOWN_MIGRATIONS = [
    MigrationRecord(version="0001", description="foundation_schema"),
    MigrationRecord(version="0002", description="value_detections"),
    MigrationRecord(version="0003", description="gemini_validation_reports"),
    MigrationRecord(version="0004", description="simulated_signal_classifications"),
    MigrationRecord(version="0005", description="simulated_signal_outcomes"),
    MigrationRecord(version="0006", description="dashboard_read_models"),
]

def list_known_migrations() -> list[MigrationRecord]:
    return list(_KNOWN_MIGRATIONS)

def get_latest_migration_version() -> str:
    migrations = list_known_migrations()
    if not migrations:
        return ""
    return migrations[-1].version

def validate_migration_registry(migrations: list[MigrationRecord] | None = None) -> dict:
    if migrations is None:
        migrations = list_known_migrations()
        
    seen = set()
    last_version = ""
    
    for m in migrations:
        if not m.description.strip():
            return {"passed": False, "error": f"Empty description for version {m.version}"}
            
        if m.version in seen:
            return {"passed": False, "error": f"Duplicate version detected: {m.version}"}
        seen.add(m.version)
        
        if m.version < last_version:
            return {"passed": False, "error": f"Versions are not strictly ordered: {m.version} came after {last_version}"}
        last_version = m.version
        
    return {
        "passed": True,
        "count": len(migrations),
        "latest": get_latest_migration_version() if migrations == _KNOWN_MIGRATIONS else (migrations[-1].version if migrations else "")
    }
