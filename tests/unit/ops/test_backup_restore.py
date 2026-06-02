import os
import sqlite3
import pytest
from src.edgehunter.ops.backup_restore import (
    create_local_backup,
    list_local_backups,
    validate_backup_file,
    restore_local_backup,
    is_safe_path
)

def create_dummy_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER);")

def test_create_local_backup(tmp_path):
    db_path = os.path.join(tmp_path, "edge.db")
    create_dummy_db(db_path)
    
    backup_dir = os.path.join(tmp_path, "backups")
    res = create_local_backup(db_path, backup_dir, mock_timestamp="2026")
    assert res["status"] == "SUCCESS"
    assert "edge.db.2026.bak" in res["backup_path"]
    assert os.path.exists(res["backup_path"])

def test_create_local_backup_not_found(tmp_path):
    db_path = os.path.join(tmp_path, "missing.db")
    backup_dir = os.path.join(tmp_path, "backups")
    with pytest.raises(FileNotFoundError):
        create_local_backup(db_path, backup_dir)

def test_list_local_backups(tmp_path):
    db_path = os.path.join(tmp_path, "edge.db")
    create_dummy_db(db_path)
    backup_dir = os.path.join(tmp_path, "backups")
    create_local_backup(db_path, backup_dir, mock_timestamp="1")
    create_local_backup(db_path, backup_dir, mock_timestamp="2")
    
    res = list_local_backups(backup_dir)
    assert res["status"] == "SUCCESS"
    assert len(res["backups"]) == 2

def test_validate_backup_valid(tmp_path):
    db_path = os.path.join(tmp_path, "edge.db")
    create_dummy_db(db_path)
    res = validate_backup_file(db_path)
    assert res["status"] == "VALID"

def test_validate_backup_invalid(tmp_path):
    bad_path = os.path.join(tmp_path, "bad.db")
    with open(bad_path, "w") as f:
        f.write("not a sqlite db")
        
    res = validate_backup_file(bad_path)
    assert res["status"] == "INVALID"

def test_restore_local_backup_dry_run(tmp_path):
    db_path = os.path.join(tmp_path, "edge.db")
    create_dummy_db(db_path)
    target = os.path.join(tmp_path, "target.db")
    
    res = restore_local_backup(db_path, target, dry_run=True)
    assert res["status"] == "DRY_RUN_SUCCESS"
    assert not os.path.exists(target)

def test_restore_local_backup_real(tmp_path):
    db_path = os.path.join(tmp_path, "edge.db")
    create_dummy_db(db_path)
    target = os.path.join(tmp_path, "target.db")
    
    res = restore_local_backup(db_path, target, dry_run=False)
    assert res["status"] == "SUCCESS"
    assert os.path.exists(target)

def test_restore_local_backup_invalid_backup(tmp_path):
    bad_path = os.path.join(tmp_path, "bad.db")
    with open(bad_path, "w") as f:
        f.write("not a sqlite db")
    target = os.path.join(tmp_path, "target.db")
    
    with pytest.raises(ValueError, match="Backup validation failed"):
        restore_local_backup(bad_path, target, dry_run=False)

def test_is_safe_path():
    base = "/opt/data"
    assert is_safe_path(base, "/opt/data/backup.db") is True
    # Traversing out of base should return False
    # Example: /opt/data/../other
    assert is_safe_path(base, os.path.join(base, "..", "other")) is False
