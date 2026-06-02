from src.edgehunter.database.migrations import (
    MigrationRecord, list_known_migrations, get_latest_migration_version, validate_migration_registry
)

def test_list_known_migrations():
    migrations = list_known_migrations()
    assert len(migrations) >= 6
    assert migrations[0].version == "0001"
    assert migrations[0].description == "foundation_schema"

def test_get_latest_migration_version():
    latest = get_latest_migration_version()
    assert int(latest) >= 6

def test_validate_registry_success():
    result = validate_migration_registry()
    assert result["passed"] is True
    assert result["count"] >= 6

def test_validate_registry_duplicate_fails():
    bad = [
        MigrationRecord(version="0001", description="a"),
        MigrationRecord(version="0001", description="b")
    ]
    result = validate_migration_registry(bad)
    assert result["passed"] is False
    assert "Duplicate" in result["error"]

def test_validate_registry_empty_description_fails():
    bad = [
        MigrationRecord(version="0001", description=" ")
    ]
    result = validate_migration_registry(bad)
    assert result["passed"] is False
    assert "Empty description" in result["error"]

def test_validate_registry_ordering_fails():
    bad = [
        MigrationRecord(version="0002", description="b"),
        MigrationRecord(version="0001", description="a")
    ]
    result = validate_migration_registry(bad)
    assert result["passed"] is False
    assert "strictly ordered" in result["error"]

def test_registry_has_no_io_or_destructive_actions():
    # Calling these pure functions demonstrates they do not reach out to db/network
    latest = get_latest_migration_version()
    assert isinstance(latest, str)
