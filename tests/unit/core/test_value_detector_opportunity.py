"""Tests for STORY-03-SUP-001 simulated value opportunity contract."""

from __future__ import annotations

from dataclasses import fields
import inspect
import math

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    build_simulated_opportunity_id,
    calculate_ev,
)


def _valid_opportunity(**overrides: object) -> SimulatedValueOpportunity:
    expected_value = calculate_ev(0.6, 2.0)
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.6,
        "offered_odds": 2.0,
        "expected_value": expected_value,
        "edge_percentage": expected_value * 100.0,
        "source": "unit-test",
        "detection_method": "pure-ev-contract",
        "created_at": "2026-05-27T12:00:00+00:00",
    }
    data.update(overrides)
    return SimulatedValueOpportunity(**data)


def test_creates_valid_simulated_opportunity() -> None:
    opportunity = _valid_opportunity()

    assert opportunity.opportunity_id.startswith("sim-")
    assert opportunity.match_id == "match-001"
    assert opportunity.market == "1x2"
    assert opportunity.selection == "home_win"
    assert opportunity.true_probability == pytest.approx(0.6)
    assert opportunity.offered_odds == pytest.approx(2.0)
    assert opportunity.expected_value == pytest.approx(0.2)
    assert opportunity.edge_percentage == pytest.approx(20.0)
    assert opportunity.source == "unit-test"
    assert opportunity.detection_method == "pure-ev-contract"
    assert opportunity.created_at == "2026-05-27T12:00:00+00:00"


def test_security_flags_are_safe_by_default() -> None:
    opportunity = _valid_opportunity()

    assert opportunity.is_simulated is True
    assert opportunity.paper_trading is True
    assert opportunity.actionable is False
    assert opportunity.bet_placed is False
    assert opportunity.alerted is False


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    (
        ("is_simulated", False, "is_simulated must be True"),
        ("paper_trading", False, "paper_trading must be True"),
        ("actionable", True, "actionable must be False"),
        ("bet_placed", True, "bet_placed must be False"),
        ("alerted", True, "alerted must be False"),
    ),
)
def test_security_flags_cannot_be_overridden(
    field_name: str,
    unsafe_value: bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _valid_opportunity(**{field_name: unsafe_value})


def test_to_dict_preserves_security_flags() -> None:
    opportunity_dict = _valid_opportunity().to_dict()

    assert opportunity_dict["is_simulated"] is True
    assert opportunity_dict["paper_trading"] is True
    assert opportunity_dict["actionable"] is False
    assert opportunity_dict["bet_placed"] is False
    assert opportunity_dict["alerted"] is False


def test_to_dict_returns_required_fields() -> None:
    opportunity_dict = _valid_opportunity().to_dict()

    assert opportunity_dict == {
        "opportunity_id": opportunity_dict["opportunity_id"],
        "match_id": "match-001",
        "snapshot_id": None,
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.6,
        "offered_odds": 2.0,
        "expected_value": pytest.approx(0.2),
        "edge_percentage": pytest.approx(20.0),
        "source": "unit-test",
        "detection_method": "pure-ev-contract",
        "created_at": "2026-05-27T12:00:00+00:00",
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
    }


def test_opportunity_id_is_deterministic_for_same_inputs() -> None:
    first = _valid_opportunity()
    second = _valid_opportunity(created_at="2026-05-27T12:01:00+00:00")

    assert first.opportunity_id == second.opportunity_id


def test_explicit_id_helper_matches_auto_generated_id() -> None:
    opportunity = _valid_opportunity()
    explicit_id = build_simulated_opportunity_id(
        match_id="match-001",
        market="1x2",
        selection="home_win",
        source="unit-test",
        detection_method="pure-ev-contract",
        offered_odds=2.0,
        true_probability=0.6,
    )

    assert opportunity.opportunity_id == explicit_id


def test_opportunity_id_changes_when_odds_change() -> None:
    first = _valid_opportunity(offered_odds=2.0, expected_value=0.2)
    second = _valid_opportunity(offered_odds=2.2, expected_value=0.32)

    assert first.opportunity_id != second.opportunity_id


def test_opportunity_id_changes_when_selection_changes() -> None:
    first = _valid_opportunity(selection="home_win")
    second = _valid_opportunity(selection="draw")

    assert first.opportunity_id != second.opportunity_id


@pytest.mark.parametrize("field_name", ("match_id", "market", "selection"))
def test_required_identity_fields_reject_empty_values(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} is required"):
        _valid_opportunity(**{field_name: " "})


@pytest.mark.parametrize("field_name", ("source", "detection_method"))
def test_required_source_fields_reject_empty_values(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} is required"):
        _valid_opportunity(**{field_name: ""})


@pytest.mark.parametrize("true_probability", (-0.01, 1.01))
def test_probability_outside_closed_unit_interval_fails(
    true_probability: float,
) -> None:
    with pytest.raises(ValueError, match="true_probability must be between 0 and 1"):
        _valid_opportunity(true_probability=true_probability)


@pytest.mark.parametrize("offered_odds", (0.0, -1.0, 1.0, 1.009))
def test_invalid_odds_fail(offered_odds: float) -> None:
    with pytest.raises(ValueError, match="offered_odds must be >= 1.01"):
        _valid_opportunity(offered_odds=offered_odds)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("true_probability", float("nan")),
        ("true_probability", float("inf")),
        ("true_probability", float("-inf")),
        ("offered_odds", float("nan")),
        ("offered_odds", float("inf")),
        ("offered_odds", float("-inf")),
        ("expected_value", float("nan")),
        ("expected_value", float("inf")),
        ("expected_value", float("-inf")),
        ("edge_percentage", float("nan")),
        ("edge_percentage", float("inf")),
        ("edge_percentage", float("-inf")),
    ),
)
def test_nan_and_infinite_numeric_values_fail(
    field_name: str,
    bad_value: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        _valid_opportunity(**{field_name: bad_value})


def test_valid_numeric_values_remain_finite() -> None:
    opportunity = _valid_opportunity()

    assert math.isfinite(opportunity.true_probability)
    assert math.isfinite(opportunity.offered_odds)
    assert math.isfinite(opportunity.expected_value)
    assert math.isfinite(opportunity.edge_percentage)


def test_contract_has_no_position_sizing_fields() -> None:
    field_names = {field.name.lower() for field in fields(SimulatedValueOpportunity)}

    assert not any("stake" in field_name for field_name in field_names)
    assert not any("kelly" in field_name for field_name in field_names)
    assert not any("bankroll" in field_name for field_name in field_names)


def test_value_detector_opportunity_module_does_not_access_database_network_or_services() -> None:
    source = inspect.getsource(value_detector_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scheduler" not in source.lower()


def test_value_detector_opportunity_module_keeps_integration_out_of_scope() -> None:
    source = inspect.getsource(value_detector_module)

    assert "PoissonModel" not in source
    assert "OddsHistorian" not in source
    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source
    assert "value_detections" not in source


def test_value_detector_opportunity_module_does_not_implement_financial_execution() -> None:
    source = inspect.getsource(value_detector_module)

    assert "stake" not in source.lower()
    assert "kelly" not in source.lower()
    assert "bankroll" not in source.lower()
    assert "place_bet" not in source.lower()
    assert "real_money" not in source.lower()
