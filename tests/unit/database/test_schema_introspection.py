import sqlite3

from src.edgehunter.database.schema import ensure_schema
from src.edgehunter.database.schema_introspection import (
    get_existing_tables,
    get_table_columns,
    validate_expected_schema,
)


def test_lists_existing_tables(tmp_path):
    db_path = str(tmp_path / "complete.db")
    ensure_schema(db_path)

    tables = get_existing_tables(db_path)

    assert "simulated_signal_outcomes" in tables


def test_lists_table_columns(tmp_path):
    db_path = str(tmp_path / "complete.db")
    ensure_schema(db_path)

    columns = get_table_columns(db_path, "simulated_signal_outcomes")

    assert "outcome_id" in columns
    assert "outcome_status" in columns


def test_detects_missing_table(tmp_path):
    db_path = str(tmp_path / "incomplete.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE value_detections (id INTEGER PRIMARY KEY)")

    result = validate_expected_schema(db_path)

    assert result["passed"] is False
    assert "simulated_signal_outcomes" in result["missing_tables"]


def test_detects_missing_column(tmp_path):
    db_path = str(tmp_path / "incomplete.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE simulated_signal_outcomes (id INTEGER PRIMARY KEY)")

    result = validate_expected_schema(db_path)

    assert result["passed"] is False
    assert "simulated_signal_outcomes" in result["missing_columns"]
    assert "outcome_id" in result["missing_columns"]["simulated_signal_outcomes"]


def test_returns_passed_true_for_complete_schema(tmp_path):
    db_path = str(tmp_path / "complete.db")
    ensure_schema(db_path)

    result = validate_expected_schema(db_path)

    assert result["passed"] is True
    assert result["missing_tables"] == []
    assert result["missing_columns"] == {}


def test_returns_passed_false_for_incomplete_schema(tmp_path):
    db_path = str(tmp_path / "incomplete.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE value_detections (id INTEGER PRIMARY KEY)")

    result = validate_expected_schema(db_path)

    assert result["passed"] is False


def test_validation_does_not_write_to_database(tmp_path):
    db_path = str(tmp_path / "complete.db")
    ensure_schema(db_path)
    before = get_existing_tables(db_path)

    validate_expected_schema(db_path)

    assert get_existing_tables(db_path) == before


def test_does_not_call_ensure_schema():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read()
    assert "ensure_schema" not in content


def test_no_network_calls():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_calls():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "google" not in content
    assert "genai" not in content


def test_does_not_implement_api():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "fastapi" not in content
    assert "apirouter" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "autoevolution" not in content
    assert "auto_evolution" not in content


def test_no_financial_terms_in_runtime_source():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "stake" not in content
    assert "kelly" not in content
    assert "bankroll" not in content


def test_no_financial_execution_runtime():
    with open("src/edgehunter/database/schema_introspection.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
