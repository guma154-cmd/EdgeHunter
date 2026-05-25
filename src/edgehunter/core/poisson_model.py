"""Mathematical core for STORY-02-001 Poisson 1X2 predictions."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


MIN_MAX_GOALS = 3
DEFAULT_MAX_GOALS = 10
DEFAULT_LEAGUE_AVG_HOME_GOALS = 1.40
DEFAULT_LEAGUE_AVG_AWAY_GOALS = 1.10
DEFAULT_NEUTRAL_STRENGTH = 1.0
PROBABILITY_TOLERANCE = 1e-9


def _require_non_empty_team(team: str) -> str:
    if not team or not team.strip():
        raise ValueError("team cannot be empty")
    return " ".join(team.split())


def _require_positive_finite(value: float, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    if number <= 0:
        raise ValueError(f"{field_name} must be > 0")
    return number


@dataclass(frozen=True)
class TeamStrength:
    attack: float
    defense: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "attack", _require_positive_finite(self.attack, "attack"))
        object.__setattr__(self, "defense", _require_positive_finite(self.defense, "defense"))


class PoissonModel:
    """In-memory Poisson model with explicit team strengths and 1X2 inference."""

    def __init__(
        self,
        *,
        league_avg_home_goals: float = DEFAULT_LEAGUE_AVG_HOME_GOALS,
        league_avg_away_goals: float = DEFAULT_LEAGUE_AVG_AWAY_GOALS,
        max_goals: int = DEFAULT_MAX_GOALS,
        neutral_attack: float = DEFAULT_NEUTRAL_STRENGTH,
        neutral_defense: float = DEFAULT_NEUTRAL_STRENGTH,
    ) -> None:
        self.league_avg_home_goals = _require_positive_finite(
            league_avg_home_goals,
            "league_avg_home_goals",
        )
        self.league_avg_away_goals = _require_positive_finite(
            league_avg_away_goals,
            "league_avg_away_goals",
        )
        if not isinstance(max_goals, int):
            raise ValueError("max_goals must be an integer")
        if max_goals < MIN_MAX_GOALS:
            raise ValueError(f"max_goals must be >= {MIN_MAX_GOALS}")
        self.max_goals = max_goals
        self.neutral_strength = TeamStrength(
            attack=neutral_attack,
            defense=neutral_defense,
        )
        self._team_strengths: dict[str, TeamStrength] = {}

    @staticmethod
    def poisson_pmf(k: int, lambda_value: float) -> float:
        """Return the Poisson PMF using a numerically stable log formulation."""
        if isinstance(k, bool) or not isinstance(k, int):
            raise ValueError("k must be a non-negative integer")
        if k < 0:
            raise ValueError("k must be a non-negative integer")

        lambda_clean = _require_positive_finite(lambda_value, "lambda_value")
        log_probability = (k * math.log(lambda_clean)) - lambda_clean - math.lgamma(k + 1)
        probability = math.exp(log_probability)
        if not math.isfinite(probability):
            raise ValueError("poisson pmf produced a non-finite result")
        if probability < 0 or probability > 1:
            raise ValueError("poisson pmf produced a probability outside 0..1")
        return probability

    def set_team_strength(self, *, team: str, attack: float, defense: float) -> None:
        team_name = _require_non_empty_team(team)
        self._team_strengths[team_name] = TeamStrength(attack=attack, defense=defense)

    def get_team_strength(self, team: str) -> TeamStrength:
        team_name = _require_non_empty_team(team)
        return self._team_strengths.get(team_name, self.neutral_strength)

    def calculate_expected_goals(self, *, home_team: str, away_team: str) -> dict[str, float]:
        home_strength = self.get_team_strength(home_team)
        away_strength = self.get_team_strength(away_team)

        expected_home_goals = (
            self.league_avg_home_goals * home_strength.attack * away_strength.defense
        )
        expected_away_goals = (
            self.league_avg_away_goals * away_strength.attack * home_strength.defense
        )

        expected_home_goals = _require_positive_finite(
            expected_home_goals,
            "expected_home_goals",
        )
        expected_away_goals = _require_positive_finite(
            expected_away_goals,
            "expected_away_goals",
        )
        return {
            "expected_home_goals": expected_home_goals,
            "expected_away_goals": expected_away_goals,
        }

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, Any]:
        home_team_name = _require_non_empty_team(home_team)
        away_team_name = _require_non_empty_team(away_team)
        expected = self.calculate_expected_goals(
            home_team=home_team_name,
            away_team=away_team_name,
        )
        home_lambda = expected["expected_home_goals"]
        away_lambda = expected["expected_away_goals"]

        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        total_mass = 0.0

        for home_goals in range(self.max_goals + 1):
            home_probability = self.poisson_pmf(home_goals, home_lambda)
            for away_goals in range(self.max_goals + 1):
                away_probability = self.poisson_pmf(away_goals, away_lambda)
                score_probability = home_probability * away_probability
                total_mass += score_probability

                if home_goals > away_goals:
                    home_win += score_probability
                elif home_goals == away_goals:
                    draw += score_probability
                else:
                    away_win += score_probability

        if not math.isfinite(total_mass) or total_mass <= 0:
            raise ValueError("score probability matrix produced invalid total mass")

        normalized = self._normalize_probabilities(
            home_win=home_win / total_mass,
            draw=draw / total_mass,
            away_win=away_win / total_mass,
        )

        return {
            **normalized,
            **expected,
            "used_fallback": (
                home_team_name not in self._team_strengths
                or away_team_name not in self._team_strengths
            ),
        }

    @staticmethod
    def _normalize_probabilities(
        *,
        home_win: float,
        draw: float,
        away_win: float,
    ) -> dict[str, float]:
        probabilities = {
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,
        }
        for field_name, value in probabilities.items():
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
            if value < 0 or value > 1:
                raise ValueError(f"{field_name} must be between 0 and 1")

        total = probabilities["home_win"] + probabilities["draw"] + probabilities["away_win"]
        if not math.isfinite(total) or total <= 0:
            raise ValueError("probability total must be finite and > 0")

        normalized = {key: value / total for key, value in probabilities.items()}
        normalized_total = sum(normalized.values())
        if abs(normalized_total - 1.0) > PROBABILITY_TOLERANCE:
            raise ValueError("normalized probabilities must sum to 1")
        return normalized
