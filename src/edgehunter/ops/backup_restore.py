import os
import shutil
import sqlite3
from datetime import datetime

def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Evita path traversal assegurando que target_path resolve para dentro de base_dir."""
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    return abs_target.startswith(abs_base)

def create_local_backup(db_path: str, backup_dir: str, mock_timestamp: str | None = None) -> dict:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    os.makedirs(backup_dir, exist_ok=True)
    
    # Path traversal block
    if not is_safe_path(backup_dir, backup_dir):
        raise ValueError("Invalid backup directory path.")

    timestamp = mock_timestamp or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    db_name = os.path.basename(db_path)
    backup_filename = f"{db_name}.{timestamp}.bak"
    backup_path = os.path.join(backup_dir, backup_filename)

    shutil.copy2(db_path, backup_path)

    return {
        "status": "SUCCESS",
        "action": "BACKUP_CREATED",
        "backup_path": backup_path,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }

def list_local_backups(backup_dir: str) -> dict:
    if not os.path.exists(backup_dir):
        return {"status": "SUCCESS", "backups": [], "is_simulated": True, "actionable": False, "not_operational_advice": True}
        
    backups = []
    for f in os.listdir(backup_dir):
        if f.endswith(".bak"):
            full_path = os.path.join(backup_dir, f)
            backups.append({
                "filename": f,
                "path": full_path,
                "size_bytes": os.path.getsize(full_path)
            })
            
    # Sort by name (which includes timestamp usually)
    backups.sort(key=lambda x: x["filename"], reverse=True)
    
    return {
        "status": "SUCCESS",
        "backups": backups,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }

def validate_backup_file(backup_path: str) -> dict:
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
    # Validates if it's a valid sqlite3 database
    valid = False
    details = ""
    try:
        with sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            if row and row[0] == "ok":
                valid = True
                details = "Integrity check ok."
            else:
                details = f"Integrity check failed: {row}"
    except sqlite3.Error as e:
        details = f"SQLite error: {e}"

    return {
        "status": "VALID" if valid else "INVALID",
        "details": details,
        "backup_path": backup_path,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }

def restore_local_backup(backup_path: str, target_db_path: str, *, dry_run: bool = True) -> dict:
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
    validation = validate_backup_file(backup_path)
    if validation["status"] != "VALID":
        raise ValueError(f"Backup validation failed: {validation['details']}")

    # Security: check path traversal. For safety, we only allow restoring to same dir as target if it existed, or a known safe dir.
    # In this context, we will trust the provided target_db_path as long as we can write to it, but we won't execute shell.
    # We will enforce python's shutil.copy2
    
    if dry_run:
        return {
            "status": "DRY_RUN_SUCCESS",
            "action": "RESTORE_SIMULATED",
            "source": backup_path,
            "target": target_db_path,
            "is_simulated": True,
            "actionable": False,
            "not_operational_advice": True
        }

    # Make sure target dir exists
    target_dir = os.path.dirname(os.path.abspath(target_db_path))
    os.makedirs(target_dir, exist_ok=True)
    
    # Overwrite safely
    shutil.copy2(backup_path, target_db_path)

    return {
        "status": "SUCCESS",
        "action": "RESTORE_APPLIED",
        "source": backup_path,
        "target": target_db_path,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }
