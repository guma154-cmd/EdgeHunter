"""Tests for STORY-03-007 paper-trading persistence of simulated opportunities."""

from __future__ import annotations

from pathlib import Path
import inspect
import sqlite3

import pytest

from src.edgehunter.core.value_detector import SimulatedValueOpportunity
from src.edgehunter.core import value_detector_persistence as persistence_module
from src.edgehunter.database.schema import ensure_schema, get_table_columns
from src.edgehunter.core.value_detector_persistence import persist_simulated_opportunities


def _opportunity(**overrides: object) -> SimulatedValueOpportunity:
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.60,
        "offered_odds": 2.00,
        "expected_value": 0.20,
        "edge_percentage": 20.0,
        "source": "consensus",
        "detection_method": "consensus_pinnacle_poisson_v1",
        "created_at": "2026-05-28T12:00:00+00:00",
    }
    data.update(overrides)
    return SimulatedValueOpportunity(**data)


def _unsafe_opportunity(**overrides: object) -> SimulatedValueOpportunity:
    opportunity = _opportunity()
    for field_name, value in overrides.items():
        object.__setattr__(opportunity, field_name, value)
    return opportunity


def _rows(db_path: Path) -> list[sqlite3.Row]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute("SELECT * FROM value_detections ORDER BY id").fetchall()
    finally:
        connection.close()


def test_schema_creates_value_detections_table(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    assert ensure_schema(str(db_path)) is True

    assert get_table_columns(str(db_path), "value_detections") == (
        "id",
        "opportunity_id",
        "match_id",
        "market",
        "selection",
        "true_probability",
        "offered_odds",
        "expected_value",
        "edge_percentage",
        "source",
        "detection_method",
        "created_at",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "inserted_at",
    )


def test_persists_valid_simulated_opportunity(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    opportunity = _opportunity()

    inserted = persist_simulated_opportunities(str(db_path), [opportunity])

    assert inserted == 1
    row = _rows(db_path)[0]
    assert row["opportunity_id"] == opportunity.opportunity_id
    assert row["match_id"] == "match-001"
    assert row["market"] == "1x2"
    assert row["selection"] == "home_win"
    assert row["true_probability"] == pytest.approx(0.60)
    assert row["offered_odds"] == pytest.approx(2.00)
    assert row["expected_value"] == pytest.approx(0.20)
    assert row["edge_percentage"] == pytest.approx(20.0)
    assert row["source"] == "consensus"
    assert row["detection_method"] == "consensus_pinnacle_poisson_v1"
    assert row["created_at"] == "2026-05-28T12:00:00+00:00"


def test_preserves_paper_trading_safety_flags(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    assert persist_simulated_opportunities(str(db_path), [_opportunity()]) == 1

    row = _rows(db_path)[0]
    assert row["is_simulated"] == 1
    assert row["paper_trading"] == 1
    assert row["actionable"] == 0
    assert row["bet_placed"] == 0
    assert row["alerted"] == 0


def test_rejects_non_simulated_or_insecure_opportunities(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    unsafe = _unsafe_opportunity(is_simulated=False)

    with pytest.raises(ValueError, match="opportunity must be simulated"):
        persist_simulated_opportunities(str(db_path), [unsafe])


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    (
        ("actionable", True, "opportunity must not be actionable"),
        ("bet_placed", True, "opportunity must not be placed"),
        ("alerted", True, "opportunity must not be alerted"),
        ("paper_trading", False, "opportunity must be paper trading"),
    ),
)
def test_rejects_unsafe_flags(
    tmp_path: Path,
    field_name: str,
    unsafe_value: bool,
    message: str,
) -> None:
    db_path = tmp_path / "edgehunter.db"
    unsafe = _unsafe_opportunity(**{field_name: unsafe_value})

    with pytest.raises(ValueError, match=message):
        persist_simulated_opportunities(str(db_path), [unsafe])


def test_idempotent_by_opportunity_id(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    opportunity = _opportunity()

    assert persist_simulated_opportunities(str(db_path), [opportunity]) == 1
    assert persist_simulated_opportunities(str(db_path), [opportunity]) == 0

    assert len(_rows(db_path)) == 1


def test_does_not_duplicate_same_opportunity_inside_batch(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    opportunity = _opportunity()

    inserted = persist_simulated_opportunities(str(db_path), [opportunity, opportunity])

    assert inserted == 1
    assert len(_rows(db_path)) == 1


def test_returns_count_of_new_insertions_and_persists_multiple(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    first = _opportunity(match_id="match-001")
    second = _opportunity(match_id="match-002")

    inserted = persist_simulated_opportunities(str(db_path), [first, second])

    assert inserted == 2
    assert [row["match_id"] for row in _rows(db_path)] == ["match-001", "match-002"]


def test_rejects_non_opportunity_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"

    with pytest.raises(ValueError, match="only SimulatedValueOpportunity"):
        persist_simulated_opportunities(str(db_path), [object()])  # type: ignore[list-item]


def test_persistence_does_not_calculate_financial_sizing() -> None:
    source = inspect.getsource(persistence_module).lower()

    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source


def test_persistence_does_not_call_external_services_or_runtime_jobs() -> None:
    source = inspect.getsource(persistence_module).lower()

    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source
    assert "scheduler" not in source


def test_persistence_does_not_implement_real_bet_or_financial_execution() -> None:
    source = inspect.getsource(persistence_module).lower()

    assert "place_bet" not in source
    assert "real_money" not in source
    assert "execute_bet" not in source


def test_persistence_does_not_call_poisson_or_detection_functions() -> None:
    source = inspect.getsource(persistence_module)

    assert "PoissonModel" not in source
    assert "detect_value_vs_pinnacle" not in source
    assert "detect_value_vs_poisson" not in source
    assert "detect_value_consensus" not in source
