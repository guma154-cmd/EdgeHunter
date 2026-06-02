import os
import pytest
from scripts.release_check import run_release_check

def test_run_release_check_valid(monkeypatch, tmp_path):
    # Mock everything to be green
    def mock_env_check(base_path, env=None):
        return {"status": "READY"}
    monkeypatch.setattr("scripts.release_check.run_environment_check", mock_env_check)
    
    def mock_smoke_test():
        return {"status": "PASSED"}
    monkeypatch.setattr("scripts.release_check.run_local_smoke_test", mock_smoke_test)
    
    def mock_val_reg():
        return {"passed": True}
    monkeypatch.setattr("scripts.release_check.validate_migration_registry", mock_val_reg)
    
    class MockPlan:
        def __init__(self):
            self.items = []
    def mock_plan(db, execution_mode):
        return MockPlan()
    monkeypatch.setattr("scripts.release_check.plan_database_migrations", mock_plan)
    
    # Mock config
    monkeypatch.setattr("scripts.release_check.load_local_config", lambda: {"db_path": "test.db"})
    monkeypatch.setattr("scripts.release_check.validate_local_config", lambda x: {"status": "VALID"})
    
    # Create fake files so it passes
    os.makedirs(os.path.join(tmp_path, "docs"), exist_ok=True)
    open(os.path.join(tmp_path, "docs", "OPERATIONS_MANUAL.md"), "w").close()
    open(os.path.join(tmp_path, "docs", "LOCAL_DEPLOYMENT.md"), "w").close()
    open(os.path.join(tmp_path, "docs", "BACKUP_RESTORE.md"), "w").close()
    open(os.path.join(tmp_path, ".env.example"), "w").close()
    
    # Run with tmp_path as base_path via monkeypatch
    monkeypatch.setattr("os.path.abspath", lambda path: str(tmp_path) if ".." in path else path)
    
    res = run_release_check()
    assert res["status"] == "READY"
    assert len(res["messages"]) == 0

def test_run_release_check_missing_docs(monkeypatch, tmp_path):
    def mock_env_check(base_path, env=None):
        return {"status": "READY"}
    monkeypatch.setattr("scripts.release_check.run_environment_check", mock_env_check)
    
    def mock_smoke_test():
        return {"status": "PASSED"}
    monkeypatch.setattr("scripts.release_check.run_local_smoke_test", mock_smoke_test)
    
    def mock_val_reg():
        return {"passed": True}
    monkeypatch.setattr("scripts.release_check.validate_migration_registry", mock_val_reg)
    
    class MockPlan:
        def __init__(self):
            self.items = []
    def mock_plan(db, execution_mode):
        return MockPlan()
    monkeypatch.setattr("scripts.release_check.plan_database_migrations", mock_plan)
    
    monkeypatch.setattr("scripts.release_check.load_local_config", lambda: {"db_path": "test.db"})
    monkeypatch.setattr("scripts.release_check.validate_local_config", lambda x: {"status": "VALID"})
    
    monkeypatch.setattr("os.path.abspath", lambda path: str(tmp_path) if ".." in path else path)
    
    res = run_release_check()
    assert res["status"] == "NOT_READY"
    # Should flag missing docs and missing .env.example
    assert any("Missing doc" in m for m in res["messages"])
    assert any("Missing .env.example" in m for m in res["messages"])

def test_run_release_check_smoke_fail(monkeypatch, tmp_path):
    def mock_env_check(base_path, env=None):
        return {"status": "READY"}
    monkeypatch.setattr("scripts.release_check.run_environment_check", mock_env_check)
    
    def mock_smoke_test():
        return {"status": "FAILED"}
    monkeypatch.setattr("scripts.release_check.run_local_smoke_test", mock_smoke_test)
    
    def mock_val_reg():
        return {"passed": True}
    monkeypatch.setattr("scripts.release_check.validate_migration_registry", mock_val_reg)
    
    class MockPlan:
        def __init__(self):
            self.items = []
    def mock_plan(db, execution_mode):
        return MockPlan()
    monkeypatch.setattr("scripts.release_check.plan_database_migrations", mock_plan)
    
    monkeypatch.setattr("scripts.release_check.load_local_config", lambda: {"db_path": "test.db"})
    monkeypatch.setattr("scripts.release_check.validate_local_config", lambda x: {"status": "VALID"})
    
    os.makedirs(os.path.join(tmp_path, "docs"), exist_ok=True)
    open(os.path.join(tmp_path, "docs", "OPERATIONS_MANUAL.md"), "w").close()
    open(os.path.join(tmp_path, "docs", "LOCAL_DEPLOYMENT.md"), "w").close()
    open(os.path.join(tmp_path, "docs", "BACKUP_RESTORE.md"), "w").close()
    open(os.path.join(tmp_path, ".env.example"), "w").close()
    
    monkeypatch.setattr("os.path.abspath", lambda path: str(tmp_path) if ".." in path else path)
    
    res = run_release_check()
    assert res["status"] == "NOT_READY"
    assert any("Smoke test failed" in m for m in res["messages"])
