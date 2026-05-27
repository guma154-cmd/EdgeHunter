"""Adversarial tests for STORY-02-007 PoissonModel robustness."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import math
from pathlib import Path
from typing import Any

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import PoissonModel, SanityCheckResult


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
    valid_for_analysis: bool = True,
    status: str = "finished",
    league: str = "Adversarial League",
) -> SyntheticMatch:
    return SyntheticMatch(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        home_goals=home_goals,
        away_goals=away_goals,
        result=_result(home_goals, away_goals),
        valid_for_analysis=valid_for_analysis,
        status=status,
    )


def _assert_valid_prediction(prediction: dict[str, Any]) -> None:
    probability_sum = 0.0
    for field_name in ("home_win", "draw", "away_win"):
        probability = prediction[field_name]
        assert math.isfinite(probability)
        assert 0.0 <= probability <= 1.0
        probability_sum += probability

    assert probability_sum == pytest.approx(1.0, abs=1e-9)
    assert math.isfinite(prediction["expected_home_goals"])
    assert math.isfinite(prediction["expected_away_goals"])
    assert prediction["expected_home_goals"] > 0
    assert prediction["expected_away_goals"] > 0


def _build_known_training_matches() -> list[SyntheticMatch]:
    return [
        _match("k1", "Alpha FC", "Beta FC", 2, 1),
        _match("k2", "Beta FC", "Alpha FC", 1, 1),
        _match("k3", "Alpha FC", "Gamma FC", 3, 0),
        _match("k4", "Gamma FC", "Alpha FC", 0, 2),
        _match("k5", "Beta FC", "Gamma FC", 1, 0),
        _match("k6", "Gamma FC", "Beta FC", 2, 2),
    ]


def _build_zero_zero_matches() -> list[SyntheticMatch]:
    return [
        _match("z1", "Zero A", "Zero B", 0, 0),
        _match("z2", "Zero B", "Zero A", 0, 0),
        _match("z3", "Zero A", "Zero C", 0, 0),
        _match("z4", "Zero C", "Zero A", 0, 0),
        _match("z5", "Zero B", "Zero C", 0, 0),
        _match("z6", "Zero C", "Zero B", 0, 0),
    ]


def _build_extreme_score_matches() -> list[SyntheticMatch]:
    return [
        _match("e1", "Power FC", "Fragile FC", 10, 0),
        _match("e2", "Fragile FC", "Power FC", 0, 10),
        _match("e3", "Chaos FC", "Power FC", 12, 8),
        _match("e4", "Power FC", "Chaos FC", 9, 7),
    ]


def _build_moderate_synthetic_matches() -> list[SyntheticMatch]:
    teams = ["North FC", "South FC", "East FC", "West FC"]
    matches: list[SyntheticMatch] = []
    match_index = 0
    for cycle in range(3):
        for home_index, home_team in enumerate(teams):
            for away_index, away_team in enumerate(teams):
                if home_team == away_team:
                    continue
                match_index += 1
                home_goals = (home_index + cycle + 2) % 4
                away_goals = (away_index + cycle) % 3
                matches.append(
                    _match(
                        f"perf-{match_index}",
                        home_team,
                        away_team,
                        home_goals,
                        away_goals,
                    )
                )
    return matches


def test_team_not_seen_in_training_uses_safe_neutral_fallback() -> None:
    model = PoissonModel()
    model.fit(_build_known_training_matches())

    prediction = model.predict_match(home_team="Alpha FC", away_team="Newcomer FC")

    assert prediction["used_fallback"] is True
    assert model.get_team_strength("Newcomer FC") == model.neutral_strength
    _assert_valid_prediction(prediction)


def test_extreme_team_strength_disparity_keeps_probabilities_valid() -> None:
    model = PoissonModel(max_goals=20)
    model.set_team_strength(team="Titan FC", attack=3.0, defense=0.25)
    model.set_team_strength(team="Tiny FC", attack=0.25, defense=2.5)

    prediction = model.predict_match(home_team="Titan FC", away_team="Tiny FC")

    _assert_valid_prediction(prediction)
    assert prediction["home_win"] > 0.70


def test_dataset_minimo_aceito_returns_structured_sanity_with_visible_warnings() -> None:
    model = PoissonModel()
    summary = model.fit([_match("min-1", "Minimal A", "Minimal B", 0, 0)])

    sanity = model.sanity_check()

    assert summary["matches_used"] == 1
    assert isinstance(sanity, SanityCheckResult)
    assert isinstance(sanity.passed, bool)
    assert sanity.warnings
    assert "dataset is very small; sanity check used a fallback canary path" in sanity.warnings
    assert "canary_probability_sum" in sanity.metrics


def test_many_zero_zero_matches_keep_lambdas_positive_and_finite() -> None:
    model = PoissonModel()

    summary = model.fit(_build_zero_zero_matches())
    prediction = model.predict_match(home_team="Zero A", away_team="Zero B")

    assert summary["success"] is True
    assert math.isfinite(summary["negative_log_likelihood"])
    assert model.league_avg_home_goals > 0
    assert model.league_avg_away_goals > 0
    _assert_valid_prediction(prediction)


def test_extreme_score_dataset_keeps_finite_nll_and_prediction_or_fails_clearly() -> None:
    model = PoissonModel(max_goals=18)

    try:
        summary = model.fit(_build_extreme_score_matches())
    except ValueError as exc:
        assert "finite" in str(exc) or "positive" in str(exc)
        return

    prediction = model.predict_match(home_team="Power FC", away_team="Fragile FC")

    assert summary["success"] is True
    assert math.isfinite(summary["negative_log_likelihood"])
    _assert_valid_prediction(prediction)


def test_mixed_structurally_invalid_records_are_rejected_with_clear_error() -> None:
    valid_match = _match("valid-1", "Clean A", "Clean B", 2, 1)
    invalid_match = _match("bad-1", "Bad A", "Bad B", 1, 0)
    invalid_payload = invalid_match.__dict__ | {"home_goals": -1}

    with pytest.raises(ValueError, match="home_goals must be >= 0"):
        PoissonModel().fit([valid_match, invalid_payload])


def test_valid_only_filters_marked_invalid_records_and_errors_when_none_remain() -> None:
    valid_match = _match("valid-1", "Filter A", "Filter B", 2, 1)
    invalid_match = _match(
        "invalid-1",
        "Filter B",
        "Filter A",
        1,
        1,
        valid_for_analysis=False,
    )

    with pytest.warns(UserWarning, match="more than 20% of matches were excluded"):
        summary = PoissonModel().fit([valid_match, invalid_match], valid_only=True)

    assert summary["matches_used"] == 1
    assert summary["matches_filtered_invalid"] == 1

    with pytest.warns(UserWarning, match="more than 20% of matches were excluded"):
        with pytest.raises(ValueError, match="no valid matches remain"):
            PoissonModel().fit([invalid_match], valid_only=True)


def test_valid_only_warns_when_invalid_ratio_is_above_threshold() -> None:
    matches = [
        _match("v1", "Warn A", "Warn B", 1, 0),
        _match("i1", "Warn B", "Warn A", 0, 0, valid_for_analysis=False),
        _match("i2", "Warn A", "Warn C", 0, 0, valid_for_analysis=False),
    ]

    with pytest.warns(UserWarning, match="more than 20% of matches were excluded"):
        summary = PoissonModel().fit(matches, valid_only=True)

    assert summary["matches_received"] == 3
    assert summary["matches_used"] == 1
    assert summary["matches_filtered_invalid"] == 2


def test_round_trip_adversarial_dataset_preserves_prediction_and_sanity_after_load(
    tmp_path: Path,
) -> None:
    model = PoissonModel(max_goals=18)
    model.fit(_build_extreme_score_matches())
    assert model.last_training_result is not None
    assert model.last_training_result.warning
    before = model.predict_match(home_team="Power FC", away_team="Fragile FC")

    path = tmp_path / "extreme-poisson.json"
    model.save(path)
    loaded = PoissonModel.load(path)
    after = loaded.predict_match(home_team="Power FC", away_team="Fragile FC")
    sanity = loaded.sanity_check()

    for field_name in (
        "home_win",
        "draw",
        "away_win",
        "expected_home_goals",
        "expected_away_goals",
    ):
        assert after[field_name] == pytest.approx(before[field_name], abs=1e-12)
    assert isinstance(sanity, SanityCheckResult)
    assert sanity.passed is False
    assert "optimizer warning is treated as a critical sanity failure" in sanity.reasons


def test_weak_optimizer_convergence_warning_is_visible_and_blocks_sanity() -> None:
    model = PoissonModel(max_goals=18)

    summary = model.fit(_build_extreme_score_matches())
    sanity = model.sanity_check()

    assert summary["warning"] == "optimizer reached max iterations before hitting tolerance"
    assert model.last_training_result is not None
    assert model.last_training_result.warning == summary["warning"]
    assert sanity.passed is False
    assert summary["warning"] in sanity.warnings


def test_moderate_synthetic_training_is_bounded_and_keeps_predictions_finite() -> None:
    matches = _build_moderate_synthetic_matches()
    model = PoissonModel(max_goals=12)

    summary = model.fit(matches)
    prediction = model.predict_match(home_team="North FC", away_team="South FC")

    assert len(matches) == 36
    assert summary["matches_used"] == 36
    assert summary["teams_trained"] == 4
    assert summary["iterations"] <= 250
    assert math.isfinite(summary["negative_log_likelihood"])
    _assert_valid_prediction(prediction)


def test_prediction_underflow_path_fails_with_controlled_error() -> None:
    model = PoissonModel(max_goals=3)
    model.set_team_strength(team="Overflow Home", attack=100.0, defense=1.0)
    model.set_team_strength(team="Overflow Away", attack=1.0, defense=100.0)

    with pytest.raises(ValueError, match="score probability matrix produced invalid total mass"):
        model.predict_match(home_team="Overflow Home", away_team="Overflow Away")


def test_adversarial_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scraper" not in source.lower()
    assert "OddsHistorian" not in source
