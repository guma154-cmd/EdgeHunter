"""Tests for STORY-02-001 PoissonModel mathematical core."""

from __future__ import annotations

import inspect
import math

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import MIN_MAX_GOALS, PoissonModel


def test_poisson_pmf_returns_valid_value_for_positive_lambda() -> None:
    probability = PoissonModel.poisson_pmf(2, 1.75)

    assert 0 < probability < 1
    assert math.isfinite(probability)


@pytest.mark.parametrize("lambda_value", (0, -0.5, float("nan"), float("inf")))
def test_poisson_pmf_rejects_non_positive_or_invalid_lambda(lambda_value: float) -> None:
    with pytest.raises(ValueError):
        PoissonModel.poisson_pmf(1, lambda_value)


def test_poisson_pmf_rejects_negative_k() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        PoissonModel.poisson_pmf(-1, 1.2)


def test_predict_match_returns_1x2_probabilities_and_expected_goals() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Flamengo", attack=1.25, defense=0.90)
    model.set_team_strength(team="Corinthians", attack=0.95, defense=1.05)

    prediction = model.predict_match(home_team="Flamengo", away_team="Corinthians")

    assert set(prediction) == {
        "home_win",
        "draw",
        "away_win",
        "expected_home_goals",
        "expected_away_goals",
        "used_fallback",
    }
    assert prediction["expected_home_goals"] > 0
    assert prediction["expected_away_goals"] > 0


def test_predict_match_probabilities_sum_to_one() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Flamengo", attack=1.25, defense=0.90)
    model.set_team_strength(team="Corinthians", attack=0.95, defense=1.05)

    prediction = model.predict_match(home_team="Flamengo", away_team="Corinthians")

    total = prediction["home_win"] + prediction["draw"] + prediction["away_win"]
    assert total == pytest.approx(1.0, abs=1e-9)


def test_home_favorite_has_higher_home_win_probability() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Strong Home", attack=1.45, defense=0.80)
    model.set_team_strength(team="Weak Away", attack=0.80, defense=1.20)

    prediction = model.predict_match(home_team="Strong Home", away_team="Weak Away")

    assert prediction["home_win"] > prediction["draw"]
    assert prediction["home_win"] > prediction["away_win"]


def test_balanced_teams_generate_plausible_distribution() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Team A", attack=1.0, defense=1.0)
    model.set_team_strength(team="Team B", attack=1.0, defense=1.0)

    prediction = model.predict_match(home_team="Team A", away_team="Team B")

    assert prediction["draw"] > 0
    assert prediction["home_win"] > prediction["away_win"]
    assert abs(prediction["home_win"] - prediction["away_win"]) < 0.20


def test_unknown_team_uses_neutral_strength_fallback() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Known FC", attack=1.10, defense=0.95)

    prediction = model.predict_match(home_team="Known FC", away_team="Unknown FC")

    assert prediction["used_fallback"] is True
    assert prediction["expected_away_goals"] == pytest.approx(
        model.league_avg_away_goals * model.neutral_strength.attack * 0.95
    )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    (
        ({"team": "", "attack": 1.0, "defense": 1.0}, "team cannot be empty"),
        ({"team": "A", "attack": 0, "defense": 1.0}, "attack must be > 0"),
        ({"team": "A", "attack": 1.0, "defense": 0}, "defense must be > 0"),
    ),
)
def test_set_team_strength_rejects_invalid_inputs(
    kwargs: dict[str, object],
    match: str,
) -> None:
    model = PoissonModel()

    with pytest.raises(ValueError, match=match):
        model.set_team_strength(**kwargs)


def test_constructor_rejects_invalid_league_averages_and_max_goals() -> None:
    with pytest.raises(ValueError, match="league_avg_home_goals must be > 0"):
        PoissonModel(league_avg_home_goals=0)

    with pytest.raises(ValueError, match="league_avg_away_goals must be > 0"):
        PoissonModel(league_avg_away_goals=-1)

    with pytest.raises(ValueError, match=f"max_goals must be >= {MIN_MAX_GOALS}"):
        PoissonModel(max_goals=MIN_MAX_GOALS - 1)


def test_prediction_contains_no_nan_or_infinite_values() -> None:
    model = PoissonModel()
    model.set_team_strength(team="Flamengo", attack=1.25, defense=0.90)
    model.set_team_strength(team="Corinthians", attack=0.95, defense=1.05)

    prediction = model.predict_match(home_team="Flamengo", away_team="Corinthians")

    for value in prediction.values():
        if isinstance(value, bool):
            continue
        assert math.isfinite(value)


def test_changing_max_goals_keeps_distribution_stable() -> None:
    compact_model = PoissonModel(max_goals=10)
    extended_model = PoissonModel(max_goals=14)

    for model in (compact_model, extended_model):
        model.set_team_strength(team="Flamengo", attack=1.25, defense=0.90)
        model.set_team_strength(team="Corinthians", attack=0.95, defense=1.05)

    compact_prediction = compact_model.predict_match(
        home_team="Flamengo",
        away_team="Corinthians",
    )
    extended_prediction = extended_model.predict_match(
        home_team="Flamengo",
        away_team="Corinthians",
    )

    assert compact_prediction["home_win"] == pytest.approx(
        extended_prediction["home_win"],
        abs=0.02,
    )
    assert compact_prediction["draw"] == pytest.approx(
        extended_prediction["draw"],
        abs=0.02,
    )
    assert compact_prediction["away_win"] == pytest.approx(
        extended_prediction["away_win"],
        abs=0.02,
    )


def test_module_does_not_import_database_network_or_telegram_dependencies() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "telegram" not in source
    assert "scraper" not in source.lower()
