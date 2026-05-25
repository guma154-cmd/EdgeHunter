"""Tests for STORY-02-002 PoissonModel historical training."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import math

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import PoissonModel


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


def _build_training_matches() -> list[SyntheticMatch]:
    return [
        SyntheticMatch(
            match_id="m1",
            home_team="Team A",
            away_team="Team B",
            league="Brasileirao",
            home_goals=2,
            away_goals=1,
            result="home_win",
        ),
        SyntheticMatch(
            match_id="m2",
            home_team="Team B",
            away_team="Team A",
            league="Brasileirao",
            home_goals=1,
            away_goals=1,
            result="draw",
        ),
        SyntheticMatch(
            match_id="m3",
            home_team="Team A",
            away_team="Team C",
            league="Brasileirao",
            home_goals=3,
            away_goals=0,
            result="home_win",
        ),
        SyntheticMatch(
            match_id="m4",
            home_team="Team C",
            away_team="Team A",
            league="Brasileirao",
            home_goals=0,
            away_goals=2,
            result="away_win",
        ),
    ]


def test_fit_trains_model_with_valid_synthetic_dataset() -> None:
    model = PoissonModel()

    summary = model.fit(_build_training_matches())

    assert model.trained is True
    assert summary["success"] is True
    assert summary["method"] == "MLE-STDlib"
    assert summary["league"] == "Brasileirao"
    assert summary["matches_used"] == 4
    assert summary["teams_trained"] == 3
    assert summary["negative_log_likelihood"] >= 0
    assert math.isfinite(summary["negative_log_likelihood"])


def test_predict_match_works_after_fit() -> None:
    model = PoissonModel()
    model.fit(_build_training_matches())

    prediction = model.predict_match(home_team="Team A", away_team="Team B")

    assert prediction["used_fallback"] is False
    assert prediction["home_win"] + prediction["draw"] + prediction["away_win"] == pytest.approx(
        1.0,
        abs=1e-9,
    )


def test_fit_calculates_league_goal_averages_correctly() -> None:
    model = PoissonModel()

    model.fit(_build_training_matches())

    assert model.league_avg_home_goals == pytest.approx(1.5)
    assert model.league_avg_away_goals == pytest.approx(1.0)


def test_fit_updates_attack_and_defense_strengths() -> None:
    model = PoissonModel()
    model.fit(_build_training_matches())

    home_favored = model.calculate_expected_goals(home_team="Team A", away_team="Team B")
    away_favored = model.calculate_expected_goals(home_team="Team B", away_team="Team A")

    assert home_favored["expected_home_goals"] > away_favored["expected_home_goals"]
    assert home_favored["expected_away_goals"] < away_favored["expected_away_goals"]


def test_fit_estimates_explicit_home_advantage() -> None:
    model = PoissonModel()

    summary = model.fit(_build_training_matches())

    assert summary["home_advantage"] > 0
    assert math.isfinite(summary["home_advantage"])


def test_home_advantage_directly_affects_expected_home_goals() -> None:
    model = PoissonModel()
    model.fit(_build_training_matches())

    baseline = model.calculate_expected_goals(home_team="Team A", away_team="Team B")
    model.home_advantage = model.home_advantage * 1.25
    boosted = model.calculate_expected_goals(home_team="Team A", away_team="Team B")

    assert boosted["expected_home_goals"] > baseline["expected_home_goals"]
    assert boosted["expected_away_goals"] == pytest.approx(baseline["expected_away_goals"])


def test_team_with_too_few_matches_uses_neutral_strength() -> None:
    model = PoissonModel()

    model.fit(_build_training_matches(), min_matches_per_team=3)

    team_b = model.get_team_strength("Team B")
    team_c = model.get_team_strength("Team C")

    assert team_b.attack == pytest.approx(1.0)
    assert team_b.defense == pytest.approx(1.0)
    assert team_c.attack == pytest.approx(1.0)
    assert team_c.defense == pytest.approx(1.0)


def test_fit_rejects_empty_match_list() -> None:
    model = PoissonModel()

    with pytest.raises(ValueError, match="matches cannot be empty"):
        model.fit([])


def test_fit_rejects_negative_goals() -> None:
    model = PoissonModel()
    matches = _build_training_matches()
    invalid_match = matches[0].__dict__ | {"home_goals": -1}

    with pytest.raises(ValueError, match="home_goals must be >= 0"):
        model.fit([invalid_match])


def test_fit_rejects_non_integer_goals() -> None:
    model = PoissonModel()
    matches = _build_training_matches()
    invalid_match = matches[0].__dict__ | {"away_goals": 1.5}

    with pytest.raises(ValueError, match="away_goals must be an integer"):
        model.fit([invalid_match])


def test_fit_rejects_same_home_and_away_team() -> None:
    model = PoissonModel()
    invalid_match = {
        "match_id": "bad",
        "home_team": "Same FC",
        "away_team": "Same FC",
        "league": "Brasileirao",
        "home_goals": 1,
        "away_goals": 0,
        "result": "home_win",
        "valid_for_analysis": True,
        "status": "finished",
    }

    with pytest.raises(ValueError, match="home_team and away_team must be different"):
        model.fit([invalid_match])


def test_valid_only_true_ignores_invalid_records_and_warns_when_ratio_is_high() -> None:
    model = PoissonModel()
    valid_match = _build_training_matches()[0].__dict__
    invalid_match = _build_training_matches()[1].__dict__ | {"valid_for_analysis": False}

    with pytest.warns(UserWarning, match="more than 20% of matches were excluded"):
        summary = model.fit([valid_match, invalid_match], valid_only=True)

    assert summary["matches_used"] == 1
    assert summary["matches_filtered_invalid"] == 1
    assert summary["success"] is True


def test_fit_fails_when_all_records_are_invalid_after_filter() -> None:
    model = PoissonModel()
    matches = [
        match.__dict__ | {"valid_for_analysis": False}
        for match in _build_training_matches()
    ]

    with pytest.warns(UserWarning, match="more than 20% of matches were excluded"):
        with pytest.raises(
            ValueError,
            match="no valid matches remain after applying valid_only filter",
        ):
            model.fit(matches, valid_only=True)


def test_fit_does_not_produce_nan_or_infinite_strengths() -> None:
    model = PoissonModel()
    summary = model.fit(_build_training_matches())

    for team in ("Team A", "Team B", "Team C"):
        strength = model.get_team_strength(team)
        assert math.isfinite(strength.attack)
        assert math.isfinite(strength.defense)
        assert strength.attack > 0
        assert strength.defense > 0
    assert math.isfinite(summary["negative_log_likelihood"])


def test_fit_handles_small_dataset_without_breaking() -> None:
    model = PoissonModel()
    tiny_dataset = [
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

    summary = model.fit(tiny_dataset)
    prediction = model.predict_match(home_team="Alpha", away_team="Beta")

    assert summary["matches_used"] == 1
    assert summary["success"] is True
    assert prediction["home_win"] + prediction["draw"] + prediction["away_win"] == pytest.approx(
        1.0,
        abs=1e-9,
    )


def test_fit_rejects_non_finished_status_when_present() -> None:
    model = PoissonModel()
    invalid_match = _build_training_matches()[0].__dict__ | {"status": "pending"}

    with pytest.raises(ValueError, match="status must be finished"):
        model.fit([invalid_match])


def test_fit_rejects_mixed_leagues() -> None:
    model = PoissonModel()
    matches = [
        _build_training_matches()[0].__dict__,
        _build_training_matches()[1].__dict__ | {"league": "Premier League"},
    ]

    with pytest.raises(ValueError, match="matches must belong to a single league"):
        model.fit(matches)


def test_fit_handles_zero_zero_dataset_without_breaking() -> None:
    model = PoissonModel()
    matches = [
        {
            "match_id": "z1",
            "home_team": "Zero A",
            "away_team": "Zero B",
            "league": "Brasileirao",
            "home_goals": 0,
            "away_goals": 0,
            "result": "draw",
            "valid_for_analysis": True,
            "status": "finished",
        },
        {
            "match_id": "z2",
            "home_team": "Zero B",
            "away_team": "Zero A",
            "league": "Brasileirao",
            "home_goals": 0,
            "away_goals": 0,
            "result": "draw",
            "valid_for_analysis": True,
            "status": "finished",
        },
    ]

    summary = model.fit(matches)
    prediction = model.predict_match(home_team="Zero A", away_team="Zero B")

    assert summary["success"] is True
    assert math.isfinite(summary["negative_log_likelihood"])
    assert prediction["expected_home_goals"] > 0
    assert prediction["expected_away_goals"] > 0


def test_fit_handles_extreme_score_dataset_without_nan_or_infinite_values() -> None:
    model = PoissonModel()
    matches = [
        {
            "match_id": "e1",
            "home_team": "Strong FC",
            "away_team": "Weak FC",
            "league": "Brasileirao",
            "home_goals": 10,
            "away_goals": 0,
            "result": "home_win",
            "valid_for_analysis": True,
            "status": "finished",
        },
        {
            "match_id": "e2",
            "home_team": "Weak FC",
            "away_team": "Strong FC",
            "league": "Brasileirao",
            "home_goals": 0,
            "away_goals": 6,
            "result": "away_win",
            "valid_for_analysis": True,
            "status": "finished",
        },
    ]

    summary = model.fit(matches)
    prediction = model.predict_match(home_team="Strong FC", away_team="Weak FC")

    assert summary["success"] is True
    assert math.isfinite(summary["negative_log_likelihood"])
    for value in prediction.values():
        if isinstance(value, bool):
            continue
        assert math.isfinite(value)


def test_negative_log_likelihood_is_finite_for_trained_params() -> None:
    model = PoissonModel()
    summary = model.fit(_build_training_matches())
    assert model.last_training_result is not None

    params = [math.log(model.home_advantage)]
    trained_teams = sorted(
        team for team in ("Team A", "Team B", "Team C")
        if model.get_team_strength(team) != model.neutral_strength
    )
    params.extend(math.log(model.get_team_strength(team).attack) for team in trained_teams)
    params.extend(math.log(model.get_team_strength(team).defense) for team in trained_teams)

    nll = model.negative_log_likelihood(
        params,
        [match.__dict__ for match in _build_training_matches()],
        trained_teams,
    )

    assert summary["negative_log_likelihood"] == pytest.approx(nll, rel=1e-3, abs=1e-3)
    assert math.isfinite(nll)


def test_training_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "telegram" not in source.lower()
    assert "scraper" not in source.lower()
