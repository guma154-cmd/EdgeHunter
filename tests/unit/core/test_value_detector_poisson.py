"""Tests for STORY-03-004 simulated Poisson-model value detection."""

from __future__ import annotations

from dataclasses import dataclass
import inspect

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    detect_value_vs_poisson,
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
        used_fallback: bool = False,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        self.trained = trained
        self.sanity_passed = sanity_passed
        self.used_fallback = used_fallback
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.25,
            "away_win": 0.15,
        }
        self.sanity_calls = 0

    def sanity_check(self) -> FakeSanityResult:
        self.sanity_calls += 1
        return FakeSanityResult(passed=self.sanity_passed)

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.6,
            "expected_away_goals": 1.0,
            "used_fallback": self.used_fallback,
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
            "bet365": {
                "home": 2.20,
                "draw": 3.10,
                "away": 4.50,
            },
        },
    }
    data.update(overrides)
    return data


def test_detects_simulated_opportunity_when_model_probability_creates_positive_ev() -> None:
    opportunities = detect_value_vs_poisson(
        _snapshot(),
        FakeModel(),
        target_bookmaker="bet365",
        min_ev=0.0,
    )

    assert [item.selection for item in opportunities] == ["home_win"]
    assert opportunities[0].true_probability == pytest.approx(0.60)
    assert opportunities[0].offered_odds == pytest.approx(2.20)
    assert opportunities[0].expected_value == pytest.approx(0.32)


def test_does_not_detect_when_ev_is_below_minimum_threshold() -> None:
    opportunities = detect_value_vs_poisson(
        _snapshot(),
        FakeModel(),
        target_bookmaker="bet365",
        min_ev=0.33,
    )

    assert opportunities == []


def test_invalid_snapshot_does_not_generate_opportunity() -> None:
    opportunities = detect_value_vs_poisson(
        _snapshot(valid_for_analysis=False),
        FakeModel(),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_missing_target_bookmaker_returns_empty_list() -> None:
    snapshot = _snapshot(odds={})

    assert detect_value_vs_poisson(snapshot, FakeModel(), target_bookmaker="bet365") == []


def test_invalid_odds_fail() -> None:
    snapshot = _snapshot(odds={"bet365": {"home": float("nan"), "draw": 3.1, "away": 4.5}})

    with pytest.raises(ValueError, match="offered_odds must be finite"):
        detect_value_vs_poisson(snapshot, FakeModel(), target_bookmaker="bet365")


def test_untrained_model_does_not_generate_opportunity() -> None:
    opportunities = detect_value_vs_poisson(
        _snapshot(),
        FakeModel(trained=False),
        target_bookmaker="bet365",
    )

    assert opportunities == []


def test_failed_sanity_check_does_not_generate_opportunity_when_required() -> None:
    model = FakeModel(sanity_passed=False)

    opportunities = detect_value_vs_poisson(
        _snapshot(),
        model,
        target_bookmaker="bet365",
        require_sanity=True,
    )

    assert opportunities == []
    assert model.sanity_calls == 1


def test_require_sanity_false_uses_trained_model_without_calling_sanity() -> None:
    model = FakeModel(sanity_passed=False)

    opportunities = detect_value_vs_poisson(
        _snapshot(),
        model,
        target_bookmaker="bet365",
        require_sanity=False,
    )

    assert len(opportunities) == 1
    assert model.sanity_calls == 0


def test_fallback_prediction_does_not_generate_opportunity() -> None:
    opportunities = detect_value_vs_poisson(
        _snapshot(),
        FakeModel(used_fallback=True),
        target_bookmaker="bet365",
    )

    assert opportunities == []


@pytest.mark.parametrize(
    "probabilities",
    (
        {"home_win": float("nan"), "draw": 0.25, "away_win": 0.15},
        {"home_win": 1.2, "draw": 0.25, "away_win": 0.15},
        {"home_win": -0.1, "draw": 0.25, "away_win": 0.15},
    ),
)
def test_invalid_probabilities_fail(probabilities: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="true_probability must|must be finite"):
        detect_value_vs_poisson(
            _snapshot(),
            FakeModel(probabilities=probabilities),
            target_bookmaker="bet365",
        )


def test_missing_selection_is_not_comparable_and_is_skipped() -> None:
    snapshot = _snapshot(odds={"bet365": {"draw": 3.1, "away": 4.5}})

    opportunities = detect_value_vs_poisson(snapshot, FakeModel(), "bet365")

    assert opportunities == []


def test_min_ev_must_be_finite_and_non_negative() -> None:
    with pytest.raises(ValueError, match="min_ev must be finite"):
        detect_value_vs_poisson(
            _snapshot(),
            FakeModel(),
            target_bookmaker="bet365",
            min_ev=float("inf"),
        )

    with pytest.raises(ValueError, match="min_ev must be >= 0"):
        detect_value_vs_poisson(
            _snapshot(),
            FakeModel(),
            target_bookmaker="bet365",
            min_ev=-0.01,
        )


def test_generated_opportunity_uses_simulated_contract_and_safe_flags() -> None:
    opportunity = detect_value_vs_poisson(_snapshot(), FakeModel(), "bet365")[0]

    assert isinstance(opportunity, SimulatedValueOpportunity)
    assert opportunity.is_simulated is True
    assert opportunity.paper_trading is True
    assert opportunity.actionable is False
    assert opportunity.bet_placed is False
    assert opportunity.alerted is False


def test_source_and_detection_method_identify_simulated_model_detection() -> None:
    opportunity = detect_value_vs_poisson(_snapshot(), FakeModel(), "bet365")[0]

    assert opportunity.source == "poisson_model"
    assert opportunity.detection_method == "poisson_ev_v1"


def test_opportunity_id_is_deterministic() -> None:
    first = detect_value_vs_poisson(_snapshot(), FakeModel(), "bet365")[0]
    second = detect_value_vs_poisson(_snapshot(), FakeModel(), "bet365")[0]

    assert first.opportunity_id == second.opportunity_id


def test_model_detection_module_does_not_implement_disallowed_flows() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "consensus" not in source
    assert "dedup" not in source
    assert "stake" not in source
    assert "kelly" not in source
    assert "bankroll" not in source
    assert "place_bet" not in source
    assert "real_money" not in source


def test_model_detection_module_does_not_persist_or_call_external_services() -> None:
    source = inspect.getsource(value_detector_module).lower()

    assert "sqlite3" not in source
    assert "value_detections" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source
    assert "scheduler" not in source


def test_model_detection_module_keeps_future_integrations_out_of_scope() -> None:
    source = inspect.getsource(value_detector_module)

    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source
