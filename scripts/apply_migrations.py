"""Apply all pending migrations to the EdgeHunter database."""
import os
import sys
from pathlib import Path

# Add root to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.database.migration_planner import plan_database_migrations
from src.edgehunter.database.migration_runner import run_migrations
from src.edgehunter.database.migration_models import MigrationExecutionMode

def main():
    db_path = os.getenv("DATABASE_PATH", "./data/edgehunter.db")
    print(f"Applying migrations to {db_path}...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    ensure_schema(db_path)
    plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.APPLY)
    results = run_migrations(db_path, plan)
    
    print("Migrations applied:")
    for result in results:
        print(f"  {result.migration_id}: {result.status.value}")

if __name__ == "__main__":
    main()
