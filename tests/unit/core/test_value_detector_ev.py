"""Tests for STORY-03-001 pure EV calculation."""

from __future__ import annotations

import inspect
import math

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import calculate_ev


def test_calculate_ev_matches_prd_formula() -> None:
    assert calculate_ev(0.6, 2.0) == pytest.approx(0.2)


def test_calculate_ev_can_return_positive_value() -> None:
    assert calculate_ev(0.55, 2.1) > 0


def test_calculate_ev_can_return_zero_value() -> None:
    assert calculate_ev(0.5, 2.0) == pytest.approx(0.0)


def test_calculate_ev_can_return_negative_value() -> None:
    assert calculate_ev(0.4, 2.0) < 0


def test_calculate_ev_accepts_zero_probability() -> None:
    assert calculate_ev(0.0, 2.0) == pytest.approx(-1.0)


def test_calculate_ev_accepts_one_probability() -> None:
    assert calculate_ev(1.0, 1.25) == pytest.approx(0.25)


@pytest.mark.parametrize("true_prob", (-0.01, -1.0))
def test_calculate_ev_rejects_probability_below_zero(true_prob: float) -> None:
    with pytest.raises(ValueError, match="true_prob must be between 0 and 1"):
        calculate_ev(true_prob, 2.0)


@pytest.mark.parametrize("true_prob", (1.01, 2.0))
def test_calculate_ev_rejects_probability_above_one(true_prob: float) -> None:
    with pytest.raises(ValueError, match="true_prob must be between 0 and 1"):
        calculate_ev(true_prob, 2.0)


@pytest.mark.parametrize("offered_odds", (0.0, -2.0, 1.0, 1.009))
def test_calculate_ev_rejects_odds_below_minimum(offered_odds: float) -> None:
    with pytest.raises(ValueError, match="offered_odds must be >= 1.01"):
        calculate_ev(0.5, offered_odds)


@pytest.mark.parametrize(
    ("true_prob", "offered_odds"),
    (
        (float("nan"), 2.0),
        (0.5, float("nan")),
        (float("inf"), 2.0),
        (0.5, float("inf")),
        (float("-inf"), 2.0),
        (0.5, float("-inf")),
    ),
)
def test_calculate_ev_rejects_nan_or_infinite_inputs(
    true_prob: float,
    offered_odds: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        calculate_ev(true_prob, offered_odds)


@pytest.mark.parametrize(
    ("true_prob", "offered_odds"),
    (
        (0.0, 1.01),
        (0.25, 4.0),
        (0.5, 2.0),
        (0.6, 2.0),
        (1.0, 100.0),
    ),
)
def test_calculate_ev_returns_finite_float_for_valid_inputs(
    true_prob: float,
    offered_odds: float,
) -> None:
    result = calculate_ev(true_prob, offered_odds)

    assert isinstance(result, float)
    assert math.isfinite(result)


def test_value_detector_ev_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(value_detector_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scheduler" not in source.lower()


def test_value_detector_ev_module_does_not_implement_operational_or_financial_flows() -> None:
    source = inspect.getsource(value_detector_module)

    assert "PoissonModel" not in source
    assert "OddsHistorian" not in source
    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source
    assert "value_detections" not in source
    assert "stake" not in source.lower()
    assert "kelly" not in source.lower()
    assert "bankroll" not in source.lower()
    assert "place_bet" not in source.lower()
    assert "real_money" not in source.lower()
