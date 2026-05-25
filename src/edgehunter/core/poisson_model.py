"""Mathematical core for STORY-02-001 and STORY-02-002 Poisson predictions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Any, Mapping
import warnings


MIN_MAX_GOALS = 3
DEFAULT_MAX_GOALS = 10
DEFAULT_LEAGUE_AVG_HOME_GOALS = 1.40
DEFAULT_LEAGUE_AVG_AWAY_GOALS = 1.10
DEFAULT_NEUTRAL_STRENGTH = 1.0
PROBABILITY_TOLERANCE = 1e-9
MIN_POSITIVE_STRENGTH = 1e-6
INVALID_DATA_WARNING_THRESHOLD = 0.20


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


def _require_non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _mean(values: list[float]) -> float:
    if not values:
        return DEFAULT_NEUTRAL_STRENGTH
    return sum(values) / len(values)


def _safe_relative_strength(value: float, baseline: float) -> float:
    if baseline <= 0:
        return DEFAULT_NEUTRAL_STRENGTH
    if value == 0:
        return MIN_POSITIVE_STRENGTH
    return max(value / baseline, MIN_POSITIVE_STRENGTH)


def _read_record_field(record: Any, field_name: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(field_name)
    return getattr(record, field_name, None)


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
        self.trained = False
        self.trained_league: str | None = None
        self.last_fit_summary: dict[str, Any] | None = None

    @staticmethod
    def _normalize_training_match(record: Any) -> dict[str, Any]:
        home_team = _require_non_empty_team(_read_record_field(record, "home_team"))
        away_team = _require_non_empty_team(_read_record_field(record, "away_team"))
        if home_team == away_team:
            raise ValueError("home_team and away_team must be different")

        league = _require_non_empty_team(_read_record_field(record, "league"))
        home_goals = _require_non_negative_integer(
            _read_record_field(record, "home_goals"),
            "home_goals",
        )
        away_goals = _require_non_negative_integer(
            _read_record_field(record, "away_goals"),
            "away_goals",
        )

        status = _read_record_field(record, "status")
        if status is not None and str(status).strip().lower() != "finished":
            raise ValueError("status must be finished")

        computed_result = (
            "home_win"
            if home_goals > away_goals
            else "away_win"
            if away_goals > home_goals
            else "draw"
        )
        result = _read_record_field(record, "result")
        if result is not None and str(result).strip() != computed_result:
            raise ValueError("result does not match scoreline")

        valid_for_analysis = _read_record_field(record, "valid_for_analysis")
        if valid_for_analysis is None:
            valid_for_analysis = True
        elif not isinstance(valid_for_analysis, bool):
            raise ValueError("valid_for_analysis must be a boolean when provided")

        return {
            "match_id": _read_record_field(record, "match_id"),
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "result": computed_result,
            "valid_for_analysis": valid_for_analysis,
        }

    def fit(
        self,
        matches: list[Any],
        *,
        min_matches_per_team: int = 1,
        valid_only: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(min_matches_per_team, int) or min_matches_per_team < 1:
            raise ValueError("min_matches_per_team must be an integer >= 1")
        if not matches:
            raise ValueError("matches cannot be empty")

        normalized_matches = [self._normalize_training_match(match) for match in matches]
        invalid_matches = [match for match in normalized_matches if not match["valid_for_analysis"]]

        if valid_only:
            training_matches = [match for match in normalized_matches if match["valid_for_analysis"]]
            invalid_ratio = len(invalid_matches) / len(normalized_matches)
            if invalid_ratio > INVALID_DATA_WARNING_THRESHOLD:
                warnings.warn(
                    "more than 20% of matches were excluded by valid_only=True",
                    stacklevel=2,
                )
        else:
            training_matches = normalized_matches

        if not training_matches:
            raise ValueError("no valid matches remain after applying valid_only filter")

        leagues = {match["league"] for match in training_matches}
        if len(leagues) != 1:
            raise ValueError("matches must belong to a single league")
        trained_league = next(iter(leagues))

        total_matches = len(training_matches)
        total_home_goals = sum(match["home_goals"] for match in training_matches)
        total_away_goals = sum(match["away_goals"] for match in training_matches)

        self.league_avg_home_goals = max(total_home_goals / total_matches, MIN_POSITIVE_STRENGTH)
        self.league_avg_away_goals = max(total_away_goals / total_matches, MIN_POSITIVE_STRENGTH)

        appearances: dict[str, int] = defaultdict(int)
        home_scored: dict[str, int] = defaultdict(int)
        home_scored_count: dict[str, int] = defaultdict(int)
        away_scored: dict[str, int] = defaultdict(int)
        away_scored_count: dict[str, int] = defaultdict(int)
        home_conceded: dict[str, int] = defaultdict(int)
        home_conceded_count: dict[str, int] = defaultdict(int)
        away_conceded: dict[str, int] = defaultdict(int)
        away_conceded_count: dict[str, int] = defaultdict(int)

        for match in training_matches:
            home_team = match["home_team"]
            away_team = match["away_team"]
            home_goals = match["home_goals"]
            away_goals = match["away_goals"]

            appearances[home_team] += 1
            appearances[away_team] += 1

            home_scored[home_team] += home_goals
            home_scored_count[home_team] += 1
            away_scored[away_team] += away_goals
            away_scored_count[away_team] += 1

            home_conceded[home_team] += away_goals
            home_conceded_count[home_team] += 1
            away_conceded[away_team] += home_goals
            away_conceded_count[away_team] += 1

        team_strengths: dict[str, TeamStrength] = {}
        for team, match_count in appearances.items():
            if match_count < min_matches_per_team:
                team_strengths[team] = self.neutral_strength
                continue

            attack_components: list[float] = []
            defense_components: list[float] = []

            if home_scored_count[team] > 0:
                attack_components.append(
                    _safe_relative_strength(
                        home_scored[team] / home_scored_count[team],
                        self.league_avg_home_goals,
                    )
                )
            if away_scored_count[team] > 0:
                attack_components.append(
                    _safe_relative_strength(
                        away_scored[team] / away_scored_count[team],
                        self.league_avg_away_goals,
                    )
                )

            if home_conceded_count[team] > 0:
                defense_components.append(
                    _safe_relative_strength(
                        home_conceded[team] / home_conceded_count[team],
                        self.league_avg_away_goals,
                    )
                )
            if away_conceded_count[team] > 0:
                defense_components.append(
                    _safe_relative_strength(
                        away_conceded[team] / away_conceded_count[team],
                        self.league_avg_home_goals,
                    )
                )

            team_strengths[team] = TeamStrength(
                attack=_mean(attack_components),
                defense=_mean(defense_components),
            )

        self._team_strengths = team_strengths
        self.trained = True
        self.trained_league = trained_league
        self.last_fit_summary = {
            "league": trained_league,
            "matches_received": len(normalized_matches),
            "matches_used": total_matches,
            "matches_filtered_invalid": len(normalized_matches) - total_matches,
            "league_avg_home_goals": self.league_avg_home_goals,
            "league_avg_away_goals": self.league_avg_away_goals,
            "teams_trained": len(team_strengths),
            "min_matches_per_team": min_matches_per_team,
            "valid_only": valid_only,
        }
        return dict(self.last_fit_summary)

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

    def predict_probabilities(self, *, home_team: str, away_team: str) -> dict[str, float]:
        prediction = self.predict_match(home_team=home_team, away_team=away_team)
        return {
            "home_win": prediction["home_win"],
            "draw": prediction["draw"],
            "away_win": prediction["away_win"],
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
