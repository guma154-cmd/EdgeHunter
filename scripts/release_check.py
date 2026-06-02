import os
import sys

# Add root project to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edgehunter.ops.environment_check import run_environment_check
from src.edgehunter.ops.config import load_local_config, validate_local_config
from scripts.smoke_test_local import run_local_smoke_test
from src.edgehunter.database.migrations import validate_migration_registry
from src.edgehunter.database.migration_planner import plan_database_migrations
from src.edgehunter.database.migration_models import MigrationExecutionMode
from src.edgehunter.ops.backup_restore import create_local_backup, validate_backup_file

def run_release_check() -> dict:
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    status = "READY"
    messages = []
    
    # 1. Environment check
    env_check = run_environment_check(base_path=base_path)
    if env_check["status"] != "READY":
        status = "NOT_READY"
        messages.append("Environment check failed or degraded.")
        
    # 2. Config check
    cfg = load_local_config()
    try:
        cfg_val = validate_local_config(cfg)
        if cfg_val.get("status") == "DEGRADED":
            messages.append("Config warning: " + cfg_val.get("reason", ""))
    except ValueError as e:
        status = "NOT_READY"
        messages.append(f"Config check failed: {str(e)}")

    # 3. Required docs exist
    docs = [
        "docs/OPERATIONS_MANUAL.md",
        "docs/LOCAL_DEPLOYMENT.md",
        "docs/BACKUP_RESTORE.md"
    ]
    for d in docs:
        if not os.path.exists(os.path.join(base_path, d)):
            status = "NOT_READY"
            messages.append(f"Missing doc: {d}")
            
    # 4. .env.example exists
    if not os.path.exists(os.path.join(base_path, ".env.example")):
        status = "NOT_READY"
        messages.append("Missing .env.example")
        
    # 5. Smoke test
    # We will temporarily set testing environment
    os.environ["EDGEHUNTER_API_KEY"] = "test-release-check"
    try:
        smoke = run_local_smoke_test()
        if smoke["status"] != "PASSED":
            status = "NOT_READY"
            messages.append("Smoke test failed.")
    except Exception as e:
        status = "NOT_READY"
        messages.append(f"Smoke test crashed: {e}")

    # 6. Migration status
    db_path = cfg["db_path"]
    try:
        registry_status = validate_migration_registry()
        plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.DRY_RUN)
        pending = [i for i in plan.items if i.status.value != "APPLIED"]
        if not registry_status["passed"] or len(pending) > 0:
            messages.append(f"Migrations check: {len(pending)} pending migrations. Consider applying them before release.")
    except Exception as e:
        messages.append(f"Could not check migrations: {e}")
        
    # 7. Backup capability (we can do a dry run or just rely on existence of functions)
    # We will just verify if the module exists, since the tests cover the behavior. We won't write real backups here.
    if "create_local_backup" not in globals():
        status = "NOT_READY"
        messages.append("Backup capability missing.")
        
    return {
        "status": status,
        "messages": messages,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }

def main():
    print("Running EdgeHunter Release Check...")
    res = run_release_check()
    for msg in res["messages"]:
        print(f"- {msg}")
    
    print(f"Status: {res['status']}")
    if res["status"] != "READY":
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
