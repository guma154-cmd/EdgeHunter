"""Tests for STORY-03-005 simulated consensus value detection."""

from __future__ import annotations

from dataclasses import dataclass
import inspect

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    detect_value_consensus,
)


@dataclass(frozen=True)
class FakeSanityResult:
    passed: bool


class FakeModel:
    def __init__(
        self,
        *,
        trained: bool = True,
        sanity_passed: bool = True,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        self.trained = trained
        self.sanity_passed = sanity_passed
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.20,
            "away_win": 0.10,
        }

    def sanity_check(self) -> FakeSanityResult:
        return FakeSanityResult(passed=self.sanity_passed)

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.5,
            "expected_away_goals": 0.9,
            "used_fallback": False,
        }

    def predict_probabilities(self, *, home_team: str, away_team: str) -> dict[str, float]:
        return self.probabilities


def _snapshot(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "snapshot_id": 1,
        "match_id": "match-001",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "league": "Brasileirao",
        "valid_for_analysis": True,
        "odds": {
            "pinnacle": {
                "home": 2.00,
                "draw": 3.20,
                "away": 4.00,
            },
            "bet365": {
                "home": 2.20,
                "draw": 3.00,
                "away": 3.50,
            },
        },
    }
    data.update(overrides)
    return data


def test_returns_simulated_opportunity_when_pinnacle_and_poisson_agree() -> None:
    opportunities = detect_value_consensus(
        _snapshot(),
        FakeModel(),
        target_bookmaker="bet365",
    )

    assert [item.selection for item in opportunities] == ["home_win"]
    assert opportunities[0].source == "consensus"
    assert opportunities[0].detection_method == "consensus_pinnacle_poisson_v1"


def test_does_not_return_when_only_pinnacle_detects() -> None:
    opportunities = detect_value_consensus(
        _snapshot(),
        FakeModel(probabilities={"home_win": 0.40, "draw": 0.20, "away_win": 0.10}),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_does_not_return_when_only_poisson_detects() -> None:
    snapshot = _snapshot(
        odds={
            "pinnacle": {"home": 1.80, "draw": 3.20, "away": 4.00},
            "bet365": {"home": 1.70, "draw": 3.00, "away": 3.50},
        },
    )

    opportunities = detect_value_consensus(
        snapshot,
        FakeModel(probabilities={"home_win": 0.70, "draw": 0.20, "away_win": 0.10}),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_does_not_return_when_sources_detect_different_selections() -> None:
    opportunities = detect_value_consensus(
        _snapshot(),
        FakeModel(probabilities={"home_win": 0.40, "draw": 0.20, "away_win": 0.40}),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_preserves_security_flags() -> None:
    opportunity = detect_value_consensus(_snapshot(), FakeModel(), "bet365")[0]

    assert isinstance(opportunity, SimulatedValueOpportunity)
    assert opportunity.is_simulated is True
    assert opportunity.paper_trading is True
    assert opportunity.actionable is False
    assert opportunity.bet_placed is False
    assert opportunity.alerted is False


def test_uses_conservative_minimum_ev_and_edge() -> None:
    opportunity = detect_value_consensus(_snapshot(), FakeModel(), "bet365")[0]

    assert opportunity.expected_value == pytest.approx(0.10)
    assert opportunity.edge_percentage == pytest.approx(10.0)


def test_opportunity_id_is_deterministic() -> None:
    first = detect_value_consensus(_snapshot(), FakeModel(), "bet365")[0]
    second = detect_value_consensus(_snapshot(), FakeModel(), "bet365")[0]

    assert first.opportunity_id == second.opportunity_id


def test_invalid_snapshot_does_not_generate_opportunity() -> None:
    assert detect_value_consensus(
        _snapshot(valid_for_analysis=False),
        FakeModel(),
        "bet365",
    ) == []


def test_untrained_model_does_not_generate_opportunity() -> None:
    assert detect_value_consensus(_snapshot(), FakeModel(trained=False), "bet365") == []


def test_failed_sanity_does_not_generate_opportunity() -> None:
    assert detect_value_consensus(
        _snapshot(),
        FakeModel(sanity_passed=False),
        "bet365",
    ) == []


def test_invalid_odds_fail_in_controlled_way() -> None:
    snapshot = _snapshot(
        odds={
            "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
            "bet365": {"home": float("nan"), "draw": 3.0, "away": 3.5},
        },
    )

    with pytest.raises(ValueError, match="offered_odds must be finite"):
        detect_value_consensus(snapshot, FakeModel(), "bet365")


def test_min_ev_validation_is_reused() -> None:
    with pytest.raises(ValueError, match="min_ev must be >= 0"):
        detect_value_consensus(_snapshot(), FakeModel(), "bet365", min_ev=-0.01)


def test_consensus_module_does_not_implement_disallowed_flows() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source
    assert "place_bet" not in source
    assert "real_money" not in source


def test_consensus_module_does_not_persist_or_call_external_services() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "sqlite3" not in source
    assert "value_detections" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source
    assert "scheduler" not in source


def test_consensus_module_keeps_future_integrations_out_of_scope() -> None:
    source = inspect.getsource(value_detector_module)

    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source
