"""Tests for STORY-02-008 sanity checks on trained PoissonModel instances."""

from __future__ import annotations

from dataclasses import dataclass, replace
import inspect
import math

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import PoissonModel, TrainingResult


@dataclass(frozen=True)
class SyntheticMatch:
    match_id: str
    home_team: str
    away_team: str
    league: str
    home_goals: int
    away_goals: int
    result: str
    valid_for_analysis: bool = True
    status: str = "finished"


def _build_healthy_matches() -> list[SyntheticMatch]:
    return [
        SyntheticMatch("m1", "Strong FC", "Weak FC", "Brasileirao", 3, 0, "home_win"),
        SyntheticMatch("m2", "Strong FC", "Mid FC", "Brasileirao", 2, 0, "home_win"),
        SyntheticMatch("m3", "Mid FC", "Weak FC", "Brasileirao", 2, 1, "home_win"),
        SyntheticMatch("m4", "Weak FC", "Strong FC", "Brasileirao", 0, 2, "away_win"),
        SyntheticMatch("m5", "Mid FC", "Strong FC", "Brasileirao", 0, 1, "away_win"),
        SyntheticMatch("m6", "Weak FC", "Mid FC", "Brasileirao", 0, 1, "away_win"),
    ]


def _build_tiny_matches() -> list[dict[str, object]]:
    return [
        {
            "match_id": "tiny-1",
            "home_team": "Alpha",
            "away_team": "Beta",
            "league": "Brasileirao",
            "home_goals": 0,
            "away_goals": 0,
            "result": "draw",
            "valid_for_analysis": True,
            "status": "finished",
        }
    ]


def _train_healthy_model() -> PoissonModel:
    model = PoissonModel()
    model.fit(_build_healthy_matches())
    assert model.last_training_result is not None
    model.last_training_result = replace(model.last_training_result, warning=None)
    return model


def _build_failed_training_result() -> TrainingResult:
    return TrainingResult(
        success=False,
        method="MLE-STDlib",
        matches_received=1,
        matches_used=1,
        teams_trained=2,
        negative_log_likelihood=1.0,
        iterations=1,
        home_advantage=1.0,
        warning=None,
        error="fit failed",
    )


def test_sanity_check_fails_when_model_was_not_trained() -> None:
    model = PoissonModel()

    result = model.sanity_check()

    assert result.passed is False
    assert "model must be trained before sanity_check" in result.reasons
    assert "last_training_result is required before sanity_check" in result.reasons


def test_sanity_check_fails_when_last_training_result_success_is_false() -> None:
    model = PoissonModel()
    model.trained = True
    model.last_training_result = _build_failed_training_result()

    result = model.sanity_check()

    assert result.passed is False
    assert "last_training_result.success must be True" in result.reasons


def test_sanity_check_fails_when_optimizer_warning_is_present() -> None:
    model = _train_healthy_model()
    assert model.last_training_result is not None
    model.last_training_result = replace(
        model.last_training_result,
        warning="optimizer reached max iterations before hitting tolerance",
    )

    result = model.sanity_check()

    assert result.passed is False
    assert "optimizer warning is treated as a critical sanity failure" in result.reasons
    assert "optimizer reached max iterations before hitting tolerance" in result.warnings


def test_sanity_check_passes_for_healthy_trained_model() -> None:
    model = _train_healthy_model()

    result = model.sanity_check()

    assert result.passed is True
    assert result.reasons == []
    assert result.metrics["canary_plausible_strength_signal"] is True


def test_sanity_check_returns_useful_metrics() -> None:
    model = _train_healthy_model()

    result = model.sanity_check()

    assert math.isfinite(result.metrics["negative_log_likelihood"])
    assert result.metrics["home_advantage"] > 0
    assert result.metrics["canary_probability_sum"] == pytest.approx(1.0, abs=1e-6)
    assert result.metrics["canary_home_team"] == "Strong FC"
    assert result.metrics["canary_away_team"] == "Weak FC"


def test_sanity_check_fails_when_nll_is_not_finite() -> None:
    model = _train_healthy_model()
    assert model.last_training_result is not None
    model.last_training_result = replace(
        model.last_training_result,
        negative_log_likelihood=float("nan"),
    )

    result = model.sanity_check()

    assert result.passed is False
    assert "negative_log_likelihood must be finite" in result.reasons


def test_sanity_check_fails_when_home_advantage_is_non_positive() -> None:
    model = _train_healthy_model()
    model.home_advantage = 0.0

    result = model.sanity_check()

    assert result.passed is False
    assert "home_advantage must be finite and > 0" in result.reasons


def test_sanity_check_fails_when_canary_probabilities_do_not_sum_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _train_healthy_model()

    def fake_predict_match(*, home_team: str, away_team: str) -> dict[str, object]:
        return {
            "home_win": 0.80,
            "draw": 0.30,
            "away_win": 0.10,
            "expected_home_goals": 1.5,
            "expected_away_goals": 0.5,
            "used_fallback": False,
        }

    monkeypatch.setattr(model, "predict_match", fake_predict_match)

    result = model.sanity_check()

    assert result.passed is False
    assert "canary probabilities must sum to approximately 1" in result.reasons


def test_sanity_check_fails_when_canary_probability_is_not_finite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _train_healthy_model()

    def fake_predict_match(*, home_team: str, away_team: str) -> dict[str, object]:
        return {
            "home_win": float("nan"),
            "draw": 0.40,
            "away_win": 0.60,
            "expected_home_goals": 1.5,
            "expected_away_goals": 0.5,
            "used_fallback": False,
        }

    monkeypatch.setattr(model, "predict_match", fake_predict_match)

    result = model.sanity_check()

    assert result.passed is False
    assert "canary probability home_win must be finite" in result.reasons


def test_sanity_check_validates_plausible_strong_vs_weak_signal() -> None:
    model = _train_healthy_model()

    result = model.sanity_check()

    assert result.metrics["canary_home_team"] == "Strong FC"
    assert result.metrics["canary_away_team"] == "Weak FC"
    assert result.metrics["canary_home_win"] > result.metrics["canary_away_win"]
    assert result.metrics["canary_home_lambda"] > result.metrics["canary_away_lambda"]


def test_sanity_check_handles_tiny_dataset_without_breaking() -> None:
    model = PoissonModel()
    model.fit(_build_tiny_matches())

    result = model.sanity_check()

    assert isinstance(result.passed, bool)
    assert result.metrics["matches_used"] == 1
    assert result.metrics["canary_probability_sum"] == pytest.approx(1.0, abs=1e-6)
    assert result.warnings


def test_sanity_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "telegram" not in source.lower()
    assert "scraper" not in source.lower()
