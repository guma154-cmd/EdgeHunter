"""Pure result contracts for local ValueDetector backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Mapping

from .value_detector import (
    SimulatedValueOpportunity,
    detect_value_consensus,
    detect_value_vs_pinnacle,
    detect_value_vs_poisson,
)


MIN_OFFERED_ODDS = 1.01
BACKTEST_MODE_PINNACLE = "pinnacle"
BACKTEST_MODE_POISSON = "poisson"
BACKTEST_MODE_CONSENSUS = "consensus"
SUPPORTED_BACKTEST_MODES = frozenset(
    {
        BACKTEST_MODE_PINNACLE,
        BACKTEST_MODE_POISSON,
        BACKTEST_MODE_CONSENSUS,
    }
)
RESULT_BY_SELECTION = {
    "home": "home_win",
    "home_win": "home_win",
    "draw": "draw",
    "away": "away_win",
    "away_win": "away_win",
}


def _require_text(value: str, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    return clean_value


def _require_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _require_finite_float(value: float, field_name: str) -> float:
    clean_value = float(value)
    if not math.isfinite(clean_value):
        raise ValueError(f"{field_name} must be finite")
    return clean_value


def _require_probability(value: float, field_name: str) -> float:
    clean_value = _require_finite_float(value, field_name)
    if not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _require_offered_odds(value: float) -> float:
    clean_value = _require_finite_float(value, "offered_odds")
    if clean_value < MIN_OFFERED_ODDS:
        raise ValueError("offered_odds must be >= 1.01")
    return clean_value


def _require_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _require_safe_flags(
    *,
    is_simulated: bool,
    paper_trading: bool,
    actionable: bool,
    bet_placed: bool | None = None,
    alerted: bool | None = None,
) -> None:
    if is_simulated is not True:
        raise ValueError("is_simulated must be True")
    if paper_trading is not True:
        raise ValueError("paper_trading must be True")
    if actionable is not False:
        raise ValueError("actionable must be False")
    if bet_placed is not None and bet_placed is not False:
        raise ValueError("bet_placed must be False")
    if alerted is not None and alerted is not False:
        raise ValueError("alerted must be False")


def _normalize_summary_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, dict[str, int | float]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")

    normalized: dict[str, dict[str, int | float]] = {}
    for raw_key, raw_metrics in value.items():
        key = _require_text(str(raw_key), f"{field_name} key")
        if not isinstance(raw_metrics, Mapping):
            raise ValueError(f"{field_name}.{key} must be a mapping")

        metric_payload: dict[str, int | float] = {}
        for raw_metric_name, raw_metric_value in raw_metrics.items():
            metric_name = _require_text(str(raw_metric_name), f"{field_name}.{key} key")
            if isinstance(raw_metric_value, bool) or not isinstance(
                raw_metric_value,
                (int, float),
            ):
                raise ValueError(f"{field_name}.{key}.{metric_name} must be numeric")
            metric_value = _require_finite_float(
                raw_metric_value,
                f"{field_name}.{key}.{metric_name}",
            )
            if metric_value < 0:
                raise ValueError(f"{field_name}.{key}.{metric_name} must be >= 0")
            metric_payload[metric_name] = (
                int(raw_metric_value)
                if isinstance(raw_metric_value, int)
                else metric_value
            )
        normalized[key] = dict(sorted(metric_payload.items()))
    return dict(sorted(normalized.items()))


@dataclass(frozen=True)
class BacktestSelectionResult:
    match_id: str
    market: str
    selection: str
    source: str
    detection_method: str
    predicted_probability: float
    offered_odds: float
    expected_value: float
    edge_percentage: float
    actual_result: str
    is_hit: bool
    is_false_positive: bool
    evaluated_at: datetime
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False

    def __post_init__(self) -> None:
        _require_safe_flags(
            is_simulated=self.is_simulated,
            paper_trading=self.paper_trading,
            actionable=self.actionable,
            bet_placed=self.bet_placed,
            alerted=self.alerted,
        )
        object.__setattr__(self, "match_id", _require_text(self.match_id, "match_id"))
        object.__setattr__(self, "market", _require_text(self.market, "market"))
        object.__setattr__(self, "selection", _require_text(self.selection, "selection"))
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(
            self,
            "detection_method",
            _require_text(self.detection_method, "detection_method"),
        )
        object.__setattr__(
            self,
            "predicted_probability",
            _require_probability(
                self.predicted_probability,
                "predicted_probability",
            ),
        )
        object.__setattr__(self, "offered_odds", _require_offered_odds(self.offered_odds))
        object.__setattr__(
            self,
            "expected_value",
            _require_finite_float(self.expected_value, "expected_value"),
        )
        object.__setattr__(
            self,
            "edge_percentage",
            _require_finite_float(self.edge_percentage, "edge_percentage"),
        )
        object.__setattr__(
            self,
            "actual_result",
            _require_text(self.actual_result, "actual_result"),
        )
        object.__setattr__(self, "is_hit", _require_bool(self.is_hit, "is_hit"))
        object.__setattr__(
            self,
            "is_false_positive",
            _require_bool(self.is_false_positive, "is_false_positive"),
        )
        object.__setattr__(
            self,
            "evaluated_at",
            _require_aware_datetime(self.evaluated_at, "evaluated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "market": self.market,
            "selection": self.selection,
            "source": self.source,
            "detection_method": self.detection_method,
            "predicted_probability": self.predicted_probability,
            "offered_odds": self.offered_odds,
            "expected_value": self.expected_value,
            "edge_percentage": self.edge_percentage,
            "actual_result": self.actual_result,
            "is_hit": self.is_hit,
            "is_false_positive": self.is_false_positive,
            "evaluated_at": self.evaluated_at.isoformat(),
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
        }


@dataclass(frozen=True)
class BacktestMetrics:
    total_analyzed: int
    total_opportunities: int
    total_hits: int
    total_false_positives: int
    hit_rate: float
    false_positive_rate: float
    coverage_rate: float
    average_expected_value: float
    average_edge_percentage: float
    by_source: Mapping[str, Mapping[str, int | float]] = field(default_factory=dict)
    by_detection_method: Mapping[str, Mapping[str, int | float]] = field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "total_analyzed",
            _require_non_negative_int(self.total_analyzed, "total_analyzed"),
        )
        object.__setattr__(
            self,
            "total_opportunities",
            _require_non_negative_int(self.total_opportunities, "total_opportunities"),
        )
        object.__setattr__(
            self,
            "total_hits",
            _require_non_negative_int(self.total_hits, "total_hits"),
        )
        object.__setattr__(
            self,
            "total_false_positives",
            _require_non_negative_int(
                self.total_false_positives,
                "total_false_positives",
            ),
        )
        object.__setattr__(self, "hit_rate", _require_probability(self.hit_rate, "hit_rate"))
        object.__setattr__(
            self,
            "false_positive_rate",
            _require_probability(self.false_positive_rate, "false_positive_rate"),
        )
        object.__setattr__(
            self,
            "coverage_rate",
            _require_probability(self.coverage_rate, "coverage_rate"),
        )
        object.__setattr__(
            self,
            "average_expected_value",
            _require_finite_float(
                self.average_expected_value,
                "average_expected_value",
            ),
        )
        object.__setattr__(
            self,
            "average_edge_percentage",
            _require_finite_float(
                self.average_edge_percentage,
                "average_edge_percentage",
            ),
        )
        object.__setattr__(
            self,
            "by_source",
            _normalize_summary_mapping(self.by_source, "by_source"),
        )
        object.__setattr__(
            self,
            "by_detection_method",
            _normalize_summary_mapping(
                self.by_detection_method,
                "by_detection_method",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_analyzed": self.total_analyzed,
            "total_opportunities": self.total_opportunities,
            "total_hits": self.total_hits,
            "total_false_positives": self.total_false_positives,
            "hit_rate": self.hit_rate,
            "false_positive_rate": self.false_positive_rate,
            "coverage_rate": self.coverage_rate,
            "average_expected_value": self.average_expected_value,
            "average_edge_percentage": self.average_edge_percentage,
            "by_source": {
                key: dict(value)
                for key, value in self.by_source.items()
            },
            "by_detection_method": {
                key: dict(value)
                for key, value in self.by_detection_method.items()
            },
        }


@dataclass(frozen=True)
class BacktestRunResult:
    run_id: str
    started_at: datetime
    finished_at: datetime
    metrics: BacktestMetrics
    selections: tuple[BacktestSelectionResult, ...] | list[BacktestSelectionResult]
    warnings: tuple[str, ...] | list[str] = field(default_factory=tuple)
    reasons: tuple[str, ...] | list[str] = field(default_factory=tuple)
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False

    def __post_init__(self) -> None:
        _require_safe_flags(
            is_simulated=self.is_simulated,
            paper_trading=self.paper_trading,
            actionable=self.actionable,
        )
        if not isinstance(self.metrics, BacktestMetrics):
            raise ValueError("metrics must be a BacktestMetrics")

        selections = tuple(self.selections)
        if not all(isinstance(selection, BacktestSelectionResult) for selection in selections):
            raise ValueError("selections must contain BacktestSelectionResult values")

        started_at = _require_aware_datetime(self.started_at, "started_at")
        finished_at = _require_aware_datetime(self.finished_at, "finished_at")
        if finished_at < started_at:
            raise ValueError("finished_at must be >= started_at")

        object.__setattr__(self, "run_id", _require_text(self.run_id, "run_id"))
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "finished_at", finished_at)
        object.__setattr__(self, "selections", selections)
        object.__setattr__(
            self,
            "warnings",
            tuple(_require_text(warning, "warning") for warning in self.warnings),
        )
        object.__setattr__(
            self,
            "reasons",
            tuple(_require_text(reason, "reason") for reason in self.reasons),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "metrics": self.metrics.to_dict(),
            "selections": [
                selection.to_dict()
                for selection in self.selections
            ],
            "warnings": list(self.warnings),
            "reasons": list(self.reasons),
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_run_id(mode: str, started_at: datetime) -> str:
    return f"bt-{mode}-{started_at.strftime('%Y%m%d%H%M%S%f')}"


def _empty_metrics(total_analyzed: int = 0) -> BacktestMetrics:
    return BacktestMetrics(
        total_analyzed=total_analyzed,
        total_opportunities=0,
        total_hits=0,
        total_false_positives=0,
        hit_rate=0.0,
        false_positive_rate=0.0,
        coverage_rate=0.0,
        average_expected_value=0.0,
        average_edge_percentage=0.0,
    )


def _historical_match_to_snapshot(historical_match: Any) -> dict[str, Any]:
    return {
        "snapshot_id": historical_match.snapshot_id,
        "match_id": historical_match.match_id,
        "home_team": historical_match.home_team,
        "away_team": historical_match.away_team,
        "league": historical_match.league,
        "valid_for_analysis": historical_match.valid_for_analysis,
        "odds": {
            bookmaker: dict(values)
            for bookmaker, values in historical_match.odds.items()
        },
    }


def _detect_opportunities(
    *,
    mode: str,
    snapshot: dict[str, Any],
    poisson_model: Any,
    target_bookmaker: str,
    min_ev: float,
    require_sanity: bool,
) -> list[SimulatedValueOpportunity]:
    if mode == BACKTEST_MODE_PINNACLE:
        return detect_value_vs_pinnacle(
            snapshot,
            target_bookmaker=target_bookmaker,
            min_ev=min_ev,
        )
    if mode == BACKTEST_MODE_POISSON:
        return detect_value_vs_poisson(
            snapshot,
            poisson_model=poisson_model,
            target_bookmaker=target_bookmaker,
            min_ev=min_ev,
            require_sanity=require_sanity,
        )
    if mode == BACKTEST_MODE_CONSENSUS:
        return detect_value_consensus(
            snapshot,
            poisson_model=poisson_model,
            target_bookmaker=target_bookmaker,
            min_ev=min_ev,
            require_sanity=require_sanity,
        )
    raise ValueError(f"unsupported backtest mode: {mode}")


def _selection_to_actual_result(selection: str) -> str:
    selection_clean = _require_text(selection, "selection")
    try:
        return RESULT_BY_SELECTION[selection_clean]
    except KeyError as exc:
        raise ValueError(f"selection cannot be mapped to a result: {selection_clean}") from exc


def _opportunity_to_selection_result(
    opportunity: SimulatedValueOpportunity,
    historical_match: Any,
) -> BacktestSelectionResult:
    mapped_result = _selection_to_actual_result(opportunity.selection)
    actual_result = _require_text(historical_match.actual_result, "actual_result")
    is_hit = mapped_result == actual_result

    return BacktestSelectionResult(
        match_id=opportunity.match_id,
        market=opportunity.market,
        selection=opportunity.selection,
        source=opportunity.source,
        detection_method=opportunity.detection_method,
        predicted_probability=opportunity.true_probability,
        offered_odds=opportunity.offered_odds,
        expected_value=opportunity.expected_value,
        edge_percentage=opportunity.edge_percentage,
        actual_result=actual_result,
        is_hit=is_hit,
        is_false_positive=not is_hit,
        evaluated_at=historical_match.snapshot_timestamp,
    )


def _group_selection_results(
    selections: tuple[BacktestSelectionResult, ...],
    field_name: str,
) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for selection in selections:
        key = getattr(selection, field_name)
        metrics = grouped.setdefault(
            key,
            {
                "opportunities": 0,
                "hits": 0,
                "false_positives": 0,
            },
        )
        metrics["opportunities"] += 1
        metrics["hits"] += int(selection.is_hit)
        metrics["false_positives"] += int(selection.is_false_positive)
    return dict(sorted(grouped.items()))


def _build_metrics(
    *,
    total_analyzed: int,
    selections: tuple[BacktestSelectionResult, ...],
) -> BacktestMetrics:
    total_opportunities = len(selections)
    if total_opportunities == 0:
        return _empty_metrics(total_analyzed=total_analyzed)

    total_hits = sum(int(selection.is_hit) for selection in selections)
    total_false_positives = sum(
        int(selection.is_false_positive)
        for selection in selections
    )
    expected_value_total = sum(selection.expected_value for selection in selections)
    edge_total = sum(selection.edge_percentage for selection in selections)

    return BacktestMetrics(
        total_analyzed=total_analyzed,
        total_opportunities=total_opportunities,
        total_hits=total_hits,
        total_false_positives=total_false_positives,
        hit_rate=total_hits / total_opportunities,
        false_positive_rate=total_false_positives / total_opportunities,
        coverage_rate=total_opportunities / total_analyzed if total_analyzed else 0.0,
        average_expected_value=expected_value_total / total_opportunities,
        average_edge_percentage=edge_total / total_opportunities,
        by_source=_group_selection_results(selections, "source"),
        by_detection_method=_group_selection_results(selections, "detection_method"),
    )


def run_value_detector_backtest(
    dataset: list[Any],
    poisson_model: Any = None,
    mode: str = BACKTEST_MODE_CONSENSUS,
    target_bookmaker: str = "bet365",
    min_ev: float = 0.0,
    require_sanity: bool = True,
) -> BacktestRunResult:
    started_at = _utc_now()
    mode_clean = _require_text(mode, "mode").lower()
    if mode_clean not in SUPPORTED_BACKTEST_MODES:
        raise ValueError(f"unsupported backtest mode: {mode_clean}")
    target_bookmaker_clean = _require_text(target_bookmaker, "target_bookmaker")

    historical_matches = tuple(dataset)
    if not historical_matches:
        finished_at = _utc_now()
        return BacktestRunResult(
            run_id=_build_run_id(mode_clean, started_at),
            started_at=started_at,
            finished_at=finished_at,
            metrics=_empty_metrics(),
            selections=(),
            warnings=("empty_dataset",),
            reasons=("no_historical_matches_to_analyze",),
        )

    selections: list[BacktestSelectionResult] = []
    for historical_match in historical_matches:
        snapshot = _historical_match_to_snapshot(historical_match)
        opportunities = _detect_opportunities(
            mode=mode_clean,
            snapshot=snapshot,
            poisson_model=poisson_model,
            target_bookmaker=target_bookmaker_clean,
            min_ev=min_ev,
            require_sanity=require_sanity,
        )
        selections.extend(
            _opportunity_to_selection_result(opportunity, historical_match)
            for opportunity in opportunities
        )

    selection_tuple = tuple(selections)
    reasons = () if selection_tuple else ("no_opportunities_detected",)
    finished_at = _utc_now()
    return BacktestRunResult(
        run_id=_build_run_id(mode_clean, started_at),
        started_at=started_at,
        finished_at=finished_at,
        metrics=_build_metrics(
            total_analyzed=len(historical_matches),
            selections=selection_tuple,
        ),
        selections=selection_tuple,
        warnings=(),
        reasons=reasons,
    )
