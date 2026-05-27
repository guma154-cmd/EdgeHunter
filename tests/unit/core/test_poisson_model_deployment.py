"""Tests for STORY-02-008 in-memory PoissonModel deployment decisions."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import math

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import (
    DEPLOYMENT_DECISION_KEEP_PREVIOUS,
    DEPLOYMENT_DECISION_PROMOTE_NEW,
    DEPLOYMENT_DECISION_REJECT_CANDIDATE,
    DeploymentDecision,
    PoissonModel,
    TrainingResult,
    evaluate_deployment_candidate,
)


@dataclass(frozen=True)
class SyntheticMatch:
    match_id: str
    home_team: str
    away_team: str
    league: str
    home_goals: int
    away_goals: int
    result: str | None = None
    valid_for_analysis: bool = True
    status: str = "finished"


def _result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home_win"
    if away_goals > home_goals:
        return "away_win"
    return "draw"


def _match(
    match_id: str,
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    *,
    result: str | None = None,
) -> SyntheticMatch:
    return SyntheticMatch(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        league="Deployment League",
        home_goals=home_goals,
        away_goals=away_goals,
        result=result,
    )


def _validation_home_wins(*, include_result: bool = True) -> list[SyntheticMatch]:
    matches: list[SyntheticMatch] = []
    for index in range(6):
        home_goals = 2 + (index % 2)
        away_goals = index % 2
        matches.append(
            _match(
                f"hw-{index}",
                "Alpha FC",
                "Beta FC",
                home_goals,
                away_goals,
                result=_result(home_goals, away_goals) if include_result else None,
            )
        )
    return matches


def _deployment_ready_model(*, alpha_stronger: bool = True) -> PoissonModel:
    model = PoissonModel(max_goals=12)
    if alpha_stronger:
        model.set_team_strength(team="Alpha FC", attack=2.5, defense=0.55)
        model.set_team_strength(team="Beta FC", attack=0.55, defense=1.8)
    else:
        model.set_team_strength(team="Alpha FC", attack=0.55, defense=1.8)
        model.set_team_strength(team="Beta FC", attack=2.5, defense=0.55)
    model.trained = True
    model.trained_league = "Deployment League"
    model.last_training_result = TrainingResult(
        success=True,
        method="MLE-STDlib",
        matches_received=24,
        matches_used=24,
        teams_trained=2,
        negative_log_likelihood=12.5,
        iterations=18,
        home_advantage=model.home_advantage,
        warning=None,
        error=None,
    )
    model.last_fit_summary = model.last_training_result.to_dict()
    return model


def test_healthy_candidate_without_previous_model_promotes_new() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins(),
    )

    assert isinstance(decision, DeploymentDecision)
    assert decision.approved is True
    assert decision.decision == DEPLOYMENT_DECISION_PROMOTE_NEW
    assert decision.reasons == []
    assert decision.metrics["validation_matches"] == 6


def test_candidate_with_failed_sanity_rejects_candidate() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)
    assert candidate.last_training_result is not None
    candidate.last_training_result = TrainingResult(
        **(candidate.last_training_result.to_dict() | {"warning": "optimizer warning"})
    )

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins(),
    )

    assert decision.approved is False
    assert decision.decision == DEPLOYMENT_DECISION_REJECT_CANDIDATE
    assert "candidate sanity failed: optimizer warning is treated as a critical sanity failure" in (
        decision.reasons
    )
    assert "optimizer warning" in decision.warnings


def test_candidate_worse_than_previous_model_keeps_previous() -> None:
    candidate = _deployment_ready_model(alpha_stronger=False)
    previous = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        previous_model=previous,
        validation_matches=_validation_home_wins(),
    )

    assert decision.approved is False
    assert decision.decision == DEPLOYMENT_DECISION_KEEP_PREVIOUS
    assert "candidate_log_loss regressed against previous_model" in decision.reasons
    assert "candidate_brier_score regressed against previous_model" in decision.reasons
    assert decision.metrics["candidate_log_loss"] > decision.metrics["previous_log_loss"]
    assert decision.metrics["candidate_brier_score"] > decision.metrics["previous_brier_score"]


def test_candidate_equivalent_to_previous_model_promotes_new() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)
    previous = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        previous_model=previous,
        validation_matches=_validation_home_wins(),
    )

    assert decision.approved is True
    assert decision.decision == DEPLOYMENT_DECISION_PROMOTE_NEW
    assert decision.metrics["candidate_log_loss"] == pytest.approx(
        decision.metrics["previous_log_loss"],
    )
    assert decision.metrics["candidate_brier_score"] == pytest.approx(
        decision.metrics["previous_brier_score"],
    )


def test_deployment_metrics_include_accuracy_log_loss_and_brier_score() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins(),
    )

    assert decision.metrics["candidate_accuracy"] == pytest.approx(1.0)
    assert math.isfinite(decision.metrics["candidate_log_loss"])
    assert math.isfinite(decision.metrics["candidate_brier_score"])
    assert decision.metrics["candidate_log_loss"] >= 0
    assert decision.metrics["candidate_brier_score"] >= 0


def test_validation_with_fewer_matches_than_minimum_rejects_candidate() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins()[:4],
        min_validation_matches=5,
    )

    assert decision.approved is False
    assert decision.decision == DEPLOYMENT_DECISION_REJECT_CANDIDATE
    assert "validation_matches must be >= 5" in decision.reasons


def test_actual_result_can_come_from_result_field() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)
    matches = [
        _match("r1", "Alpha FC", "Beta FC", 1, 0, result="home_win"),
        _match("r2", "Alpha FC", "Beta FC", 2, 0, result="home_win"),
        _match("r3", "Alpha FC", "Beta FC", 3, 1, result="home_win"),
        _match("r4", "Alpha FC", "Beta FC", 2, 1, result="home_win"),
        _match("r5", "Alpha FC", "Beta FC", 4, 0, result="home_win"),
    ]

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=matches,
    )

    assert decision.approved is True
    assert decision.metrics["candidate_accuracy"] == pytest.approx(1.0)


def test_actual_result_can_be_calculated_from_goals() -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins(include_result=False),
    )

    assert decision.approved is True
    assert decision.metrics["candidate_accuracy"] == pytest.approx(1.0)


def test_invalid_probabilities_reject_candidate_with_controlled_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)

    def invalid_probabilities(*, home_team: str, away_team: str) -> dict[str, float]:
        return {"home_win": 0.9, "draw": 0.9, "away_win": 0.1}

    monkeypatch.setattr(candidate, "predict_probabilities", invalid_probabilities)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        validation_matches=_validation_home_wins(),
    )

    assert decision.approved is False
    assert decision.decision == DEPLOYMENT_DECISION_REJECT_CANDIDATE
    assert "candidate probabilities must sum to approximately 1" in decision.reasons


def test_deployment_decision_does_not_save_load_or_promote_by_side_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    candidate = _deployment_ready_model(alpha_stronger=True)
    previous = _deployment_ready_model(alpha_stronger=True)

    def fail_save(*args, **kwargs) -> None:
        raise AssertionError("save must not be called")

    def fail_load(*args, **kwargs) -> PoissonModel:
        raise AssertionError("load must not be called")

    monkeypatch.setattr(candidate, "save", fail_save)
    monkeypatch.setattr(previous, "save", fail_save)
    monkeypatch.setattr(PoissonModel, "load", fail_load)

    decision = evaluate_deployment_candidate(
        candidate_model=candidate,
        previous_model=previous,
        validation_matches=_validation_home_wins(),
    )

    assert decision.approved is True
    assert list(tmp_path.iterdir()) == []


def test_deployment_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scraper" not in source.lower()
    assert "OddsHistorian" not in source


def test_deployment_module_does_not_implement_downstream_systems() -> None:
    source = inspect.getsource(poisson_module)

    assert "ValueDetector" not in source
    assert "GeminiValidator" not in source
    assert "AutoEvolution" not in source
    assert "stake" not in source.lower()
    assert "place_bet" not in source.lower()
    assert "real_money" not in source.lower()
