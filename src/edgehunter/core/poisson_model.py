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
DEFAULT_HOME_ADVANTAGE = 1.0
DEFAULT_MAX_OPTIMIZATION_ITERATIONS = 250
DEFAULT_OPTIMIZATION_TOLERANCE = 1e-6
DEFAULT_REGULARIZATION_WEIGHT = 1e-4
MIN_STEP_SIZE = 1e-8
INITIAL_STEP_SIZE = 0.25
GRADIENT_EPSILON = 1e-5


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


def _center(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    mean_value = sum(values.values()) / len(values)
    return {key: value - mean_value for key, value in values.items()}


@dataclass(frozen=True)
class TeamStrength:
    attack: float
    defense: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "attack", _require_positive_finite(self.attack, "attack"))
        object.__setattr__(self, "defense", _require_positive_finite(self.defense, "defense"))


@dataclass(frozen=True)
class TrainingResult:
    success: bool
    method: str
    matches_received: int
    matches_used: int
    teams_trained: int
    negative_log_likelihood: float
    iterations: int
    home_advantage: float
    warning: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "method": self.method,
            "matches_received": self.matches_received,
            "matches_used": self.matches_used,
            "teams_trained": self.teams_trained,
            "negative_log_likelihood": self.negative_log_likelihood,
            "iterations": self.iterations,
            "home_advantage": self.home_advantage,
            "warning": self.warning,
            "error": self.error,
        }


@dataclass(frozen=True)
class SanityCheckResult:
    passed: bool
    reasons: list[str]
    warnings: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "metrics": dict(self.metrics),
        }


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
        self.home_advantage = _require_positive_finite(DEFAULT_HOME_ADVANTAGE, "home_advantage")
        self._team_strengths: dict[str, TeamStrength] = {}
        self.trained = False
        self.trained_league: str | None = None
        self.last_fit_summary: dict[str, Any] | None = None
        self.last_training_result: TrainingResult | None = None

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

    @staticmethod
    def _build_team_counts(matches: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for match in matches:
            counts[match["home_team"]] += 1
            counts[match["away_team"]] += 1
        return counts

    def _build_initial_strengths(
        self,
        matches: list[dict[str, Any]],
        trainable_teams: list[str],
    ) -> tuple[dict[str, float], dict[str, float]]:
        home_scored: dict[str, int] = defaultdict(int)
        home_scored_count: dict[str, int] = defaultdict(int)
        away_scored: dict[str, int] = defaultdict(int)
        away_scored_count: dict[str, int] = defaultdict(int)
        home_conceded: dict[str, int] = defaultdict(int)
        home_conceded_count: dict[str, int] = defaultdict(int)
        away_conceded: dict[str, int] = defaultdict(int)
        away_conceded_count: dict[str, int] = defaultdict(int)

        for match in matches:
            home_team = match["home_team"]
            away_team = match["away_team"]
            home_goals = match["home_goals"]
            away_goals = match["away_goals"]

            home_scored[home_team] += home_goals
            home_scored_count[home_team] += 1
            away_scored[away_team] += away_goals
            away_scored_count[away_team] += 1
            home_conceded[home_team] += away_goals
            home_conceded_count[home_team] += 1
            away_conceded[away_team] += home_goals
            away_conceded_count[away_team] += 1

        attack_strengths: dict[str, float] = {}
        defense_strengths: dict[str, float] = {}
        for team in trainable_teams:
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

            attack_strengths[team] = math.log(max(_mean(attack_components), MIN_POSITIVE_STRENGTH))
            defense_strengths[team] = math.log(max(_mean(defense_components), MIN_POSITIVE_STRENGTH))

        return _center(attack_strengths), _center(defense_strengths)

    @staticmethod
    def _pack_params(
        home_advantage_log: float,
        attack_logs: dict[str, float],
        defense_logs: dict[str, float],
        teams: list[str],
    ) -> list[float]:
        params = [home_advantage_log]
        params.extend(attack_logs[team] for team in teams)
        params.extend(defense_logs[team] for team in teams)
        return params

    @staticmethod
    def _unpack_params(
        params: list[float],
        teams: list[str],
    ) -> tuple[float, dict[str, float], dict[str, float]]:
        team_count = len(teams)
        home_advantage_log = float(params[0])
        attack_logs = {
            team: float(params[index + 1])
            for index, team in enumerate(teams)
        }
        defense_logs = {
            team: float(params[index + 1 + team_count])
            for index, team in enumerate(teams)
        }
        return home_advantage_log, _center(attack_logs), _center(defense_logs)

    def _calculate_match_lambdas_from_logs(
        self,
        *,
        match: dict[str, Any],
        home_advantage_log: float,
        attack_logs: dict[str, float],
        defense_logs: dict[str, float],
    ) -> tuple[float, float]:
        home_attack_log = attack_logs.get(match["home_team"], 0.0)
        away_attack_log = attack_logs.get(match["away_team"], 0.0)
        home_defense_log = defense_logs.get(match["home_team"], 0.0)
        away_defense_log = defense_logs.get(match["away_team"], 0.0)

        home_lambda_log = (
            math.log(self.league_avg_home_goals)
            + home_advantage_log
            + home_attack_log
            + away_defense_log
        )
        away_lambda_log = (
            math.log(self.league_avg_away_goals)
            + away_attack_log
            + home_defense_log
        )
        home_lambda = math.exp(home_lambda_log)
        away_lambda = math.exp(away_lambda_log)
        return (
            _require_positive_finite(home_lambda, "home_lambda"),
            _require_positive_finite(away_lambda, "away_lambda"),
        )

    def negative_log_likelihood(
        self,
        params: list[float],
        matches: list[dict[str, Any]],
        teams: list[str],
    ) -> float:
        home_advantage_log, attack_logs, defense_logs = self._unpack_params(params, teams)
        total = 0.0
        for match in matches:
            home_lambda, away_lambda = self._calculate_match_lambdas_from_logs(
                match=match,
                home_advantage_log=home_advantage_log,
                attack_logs=attack_logs,
                defense_logs=defense_logs,
            )
            total += home_lambda - (match["home_goals"] * math.log(home_lambda)) + math.lgamma(
                match["home_goals"] + 1
            )
            total += away_lambda - (match["away_goals"] * math.log(away_lambda)) + math.lgamma(
                match["away_goals"] + 1
            )

        regularization = DEFAULT_REGULARIZATION_WEIGHT * sum(
            value * value for value in params[1:]
        )
        nll = total + regularization
        if not math.isfinite(nll):
            raise ValueError("negative_log_likelihood produced a non-finite result")
        return nll

    def _compute_gradient(
        self,
        params: list[float],
        matches: list[dict[str, Any]],
        teams: list[str],
    ) -> list[float]:
        gradient: list[float] = []
        for index in range(len(params)):
            plus_params = list(params)
            minus_params = list(params)
            plus_params[index] += GRADIENT_EPSILON
            minus_params[index] -= GRADIENT_EPSILON
            plus_value = self.negative_log_likelihood(plus_params, matches, teams)
            minus_value = self.negative_log_likelihood(minus_params, matches, teams)
            gradient.append((plus_value - minus_value) / (2 * GRADIENT_EPSILON))
        return gradient

    def _optimize_mle(
        self,
        params: list[float],
        matches: list[dict[str, Any]],
        teams: list[str],
    ) -> tuple[list[float], float, int, bool, str | None]:
        best_params = list(params)
        best_nll = self.negative_log_likelihood(best_params, matches, teams)

        for iteration in range(1, DEFAULT_MAX_OPTIMIZATION_ITERATIONS + 1):
            gradient = self._compute_gradient(best_params, matches, teams)
            gradient_norm = math.sqrt(sum(value * value for value in gradient))
            if gradient_norm <= DEFAULT_OPTIMIZATION_TOLERANCE:
                return best_params, best_nll, iteration, True, None

            normalized_gradient = [value / max(gradient_norm, MIN_POSITIVE_STRENGTH) for value in gradient]
            step_size = INITIAL_STEP_SIZE
            improved = False

            while step_size >= MIN_STEP_SIZE:
                candidate = [
                    param - (step_size * direction)
                    for param, direction in zip(best_params, normalized_gradient, strict=True)
                ]
                candidate_nll = self.negative_log_likelihood(candidate, matches, teams)
                if candidate_nll + DEFAULT_OPTIMIZATION_TOLERANCE < best_nll:
                    best_params = candidate
                    best_nll = candidate_nll
                    improved = True
                    break
                step_size /= 2.0

            if not improved:
                warning = "optimizer stopped after failing to improve the objective"
                return best_params, best_nll, iteration, True, warning

        return (
            best_params,
            best_nll,
            DEFAULT_MAX_OPTIMIZATION_ITERATIONS,
            True,
            "optimizer reached max iterations before hitting tolerance",
        )

    def _apply_trained_parameters(
        self,
        *,
        params: list[float],
        teams: list[str],
        all_teams: list[str],
        min_matches_per_team: int,
        team_counts: dict[str, int],
    ) -> None:
        home_advantage_log, attack_logs, defense_logs = self._unpack_params(params, teams)
        self.home_advantage = math.exp(home_advantage_log)
        self._team_strengths = {}
        for team in all_teams:
            if team_counts[team] < min_matches_per_team:
                self._team_strengths[team] = self.neutral_strength
                continue

            self._team_strengths[team] = TeamStrength(
                attack=math.exp(attack_logs.get(team, 0.0)),
                defense=math.exp(defense_logs.get(team, 0.0)),
            )

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

        team_counts = self._build_team_counts(training_matches)
        all_teams = sorted(team_counts)
        trainable_teams = sorted(
            team for team, count in team_counts.items() if count >= min_matches_per_team
        )
        if not trainable_teams:
            raise ValueError("no teams meet min_matches_per_team for MLE training")

        initial_attack_logs, initial_defense_logs = self._build_initial_strengths(
            training_matches,
            trainable_teams,
        )
        initial_params = self._pack_params(
            home_advantage_log=0.0,
            attack_logs=initial_attack_logs,
            defense_logs=initial_defense_logs,
            teams=trainable_teams,
        )
        params, negative_log_likelihood, iterations, success, warning = self._optimize_mle(
            initial_params,
            training_matches,
            trainable_teams,
        )
        self._apply_trained_parameters(
            params=params,
            teams=trainable_teams,
            all_teams=all_teams,
            min_matches_per_team=min_matches_per_team,
            team_counts=team_counts,
        )
        self.trained = True
        self.trained_league = trained_league
        self.last_training_result = TrainingResult(
            success=success,
            method="MLE-STDlib",
            matches_received=len(normalized_matches),
            matches_used=total_matches,
            teams_trained=len(trainable_teams),
            negative_log_likelihood=negative_log_likelihood,
            iterations=iterations,
            home_advantage=self.home_advantage,
            warning=warning,
            error=None,
        )
        self.last_fit_summary = {
            "league": trained_league,
            **self.last_training_result.to_dict(),
            "league_avg_home_goals": self.league_avg_home_goals,
            "league_avg_away_goals": self.league_avg_away_goals,
            "matches_filtered_invalid": len(normalized_matches) - total_matches,
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
            self.league_avg_home_goals
            * self.home_advantage
            * home_strength.attack
            * away_strength.defense
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

    def _build_sanity_metrics(self) -> dict[str, Any]:
        training_result = self.last_training_result
        metrics: dict[str, Any] = {
            "trained": self.trained,
            "home_advantage": self.home_advantage,
            "teams_with_explicit_strength": len(self._team_strengths),
        }
        if training_result is None:
            return metrics

        metrics.update(
            {
                "training_success": training_result.success,
                "negative_log_likelihood": training_result.negative_log_likelihood,
                "matches_received": training_result.matches_received,
                "matches_used": training_result.matches_used,
                "teams_trained": training_result.teams_trained,
                "training_iterations": training_result.iterations,
                "optimizer_warning": training_result.warning,
            }
        )
        return metrics

    def _append_strength_reasons(
        self,
        reasons: list[str],
        metrics: dict[str, Any],
    ) -> None:
        invalid_teams: list[str] = []
        for team, strength in sorted(self._team_strengths.items()):
            if not math.isfinite(strength.attack) or strength.attack <= 0:
                invalid_teams.append(team)
            if not math.isfinite(strength.defense) or strength.defense <= 0:
                invalid_teams.append(team)

        metrics["invalid_strength_teams"] = invalid_teams
        if invalid_teams:
            reasons.append("team strengths must be finite and > 0")

    def _select_canary_matchup(self) -> tuple[str, str, bool]:
        trained_teams = sorted(self._team_strengths.items())
        if len(trained_teams) < 2:
            return "__sanity_home__", "__sanity_away__", True

        strongest_team = max(
            trained_teams,
            key=lambda item: (item[1].attack, -item[1].defense, item[0]),
        )[0]
        weakest_team = min(
            trained_teams,
            key=lambda item: (item[1].attack, -item[1].defense, item[0]),
        )[0]
        if weakest_team == strongest_team:
            alternatives = [team for team, _ in trained_teams if team != strongest_team]
            weakest_team = alternatives[0] if alternatives else "__sanity_away__"

        return strongest_team, weakest_team, False

    @staticmethod
    def _validate_canary_probabilities(
        prediction: Mapping[str, Any],
        reasons: list[str],
        metrics: dict[str, Any],
    ) -> None:
        probability_values: dict[str, float] = {}
        for field_name in ("home_win", "draw", "away_win"):
            value = float(prediction[field_name])
            probability_values[field_name] = value
            metrics[f"canary_{field_name}"] = value
            if not math.isfinite(value):
                reasons.append(f"canary probability {field_name} must be finite")
                continue
            if value < 0 or value > 1:
                reasons.append(f"canary probability {field_name} must be between 0 and 1")

        probability_sum = sum(probability_values.values())
        metrics["canary_probability_sum"] = probability_sum
        if not math.isfinite(probability_sum) or abs(probability_sum - 1.0) > 1e-6:
            reasons.append("canary probabilities must sum to approximately 1")

    def sanity_check(self) -> SanityCheckResult:
        reasons: list[str] = []
        warnings_list: list[str] = []
        metrics = self._build_sanity_metrics()

        if not self.trained:
            reasons.append("model must be trained before sanity_check")
        if self.last_training_result is None:
            reasons.append("last_training_result is required before sanity_check")

        training_result = self.last_training_result
        if training_result is not None:
            if training_result.success is not True:
                reasons.append("last_training_result.success must be True")
            if training_result.warning:
                reasons.append("optimizer warning is treated as a critical sanity failure")
                warnings_list.append(training_result.warning)
            if not math.isfinite(training_result.negative_log_likelihood):
                reasons.append("negative_log_likelihood must be finite")
            if training_result.matches_used < 2:
                warnings_list.append(
                    "dataset is very small; sanity check used a fallback canary path",
                )

        if not math.isfinite(self.home_advantage) or self.home_advantage <= 0:
            reasons.append("home_advantage must be finite and > 0")

        self._append_strength_reasons(reasons, metrics)

        canary_home_team, canary_away_team, used_synthetic_canary = self._select_canary_matchup()
        metrics["canary_home_team"] = canary_home_team
        metrics["canary_away_team"] = canary_away_team
        metrics["used_synthetic_canary"] = used_synthetic_canary

        if used_synthetic_canary:
            warnings_list.append("trained team set too small; using synthetic neutral canary")

        try:
            expected = self.calculate_expected_goals(
                home_team=canary_home_team,
                away_team=canary_away_team,
            )
            prediction = self.predict_match(
                home_team=canary_home_team,
                away_team=canary_away_team,
            )
        except Exception as exc:
            reasons.append(f"canary prediction failed: {exc}")
        else:
            metrics["canary_home_lambda"] = expected["expected_home_goals"]
            metrics["canary_away_lambda"] = expected["expected_away_goals"]
            if not math.isfinite(expected["expected_home_goals"]) or expected["expected_home_goals"] <= 0:
                reasons.append("canary home lambda must be finite and > 0")
            if not math.isfinite(expected["expected_away_goals"]) or expected["expected_away_goals"] <= 0:
                reasons.append("canary away lambda must be finite and > 0")

            self._validate_canary_probabilities(prediction, reasons, metrics)

            plausible_signal = (
                prediction["home_win"] > prediction["away_win"]
                and expected["expected_home_goals"] > expected["expected_away_goals"]
            )
            metrics["canary_plausible_strength_signal"] = plausible_signal
            if not used_synthetic_canary and not plausible_signal:
                reasons.append("strong-vs-weak canary prediction is not plausible")

        return SanityCheckResult(
            passed=not reasons,
            reasons=reasons,
            warnings=warnings_list,
            metrics=metrics,
        )

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
