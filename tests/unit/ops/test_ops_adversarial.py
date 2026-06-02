import pytest
import os
from src.edgehunter.ops.config import load_local_config, validate_local_config
from src.edgehunter.ops.backup_restore import restore_local_backup, create_local_backup

def test_config_read_only_false_fails():
    cfg = load_local_config({"EDGEHUNTER_READ_ONLY_MODE": "false"})
    with pytest.raises(ValueError, match="EDGEHUNTER_READ_ONLY_MODE"):
        validate_local_config(cfg)

def test_config_actionable_true_fails():
    cfg = load_local_config({"EDGEHUNTER_ACTIONABLE": "true"})
    with pytest.raises(ValueError, match="EDGEHUNTER_ACTIONABLE"):
        validate_local_config(cfg)

def test_config_api_key_empty_fails():
    cfg = load_local_config({"EDGEHUNTER_API_KEY": ""})
    res = validate_local_config(cfg)
    assert res["status"] == "DEGRADED"

def test_config_invalid_port_fails():
    cfg = load_local_config({"EDGEHUNTER_PORT": "abc"})
    # it falls back to 8000 safely, so it will pass validate.
    # To fail validation, we have to inject an invalid port.
    cfg["port"] = -1
    with pytest.raises(ValueError, match="EDGEHUNTER_PORT"):
        validate_local_config(cfg)

def test_backup_path_traversal_fails(tmp_path):
    # Try to backup to an illegal path via a crafted timestamp that escapes the base
    db_path = os.path.join(tmp_path, "edge.db")
    with open(db_path, "w") as f:
        f.write("dummy db")
    
    backup_dir = os.path.join(tmp_path, "backups")
    os.makedirs(backup_dir)
    
    with pytest.raises(ValueError, match="Invalid backup directory path."):
        create_local_backup(db_path, backup_dir, mock_timestamp="/../../../evil")

def test_restore_invalid_file_fails(tmp_path):
    bad_backup = os.path.join(tmp_path, "bad.bak")
    with open(bad_backup, "w") as f:
        f.write("not a database")
    
    target_db = os.path.join(tmp_path, "target.db")
    
    with pytest.raises(ValueError, match="Backup validation failed"):
        restore_local_backup(bad_backup, target_db, dry_run=False)

def test_restore_dry_run_never_writes(tmp_path):
    # Create valid db
    import sqlite3
    db_path = os.path.join(tmp_path, "edge.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER);")
        
    backup_dir = os.path.join(tmp_path, "backups")
    res = create_local_backup(db_path, backup_dir)
    
    target_db = os.path.join(tmp_path, "target.db")
    restore_local_backup(res["backup_path"], target_db, dry_run=True)
    
    assert not os.path.exists(target_db)
