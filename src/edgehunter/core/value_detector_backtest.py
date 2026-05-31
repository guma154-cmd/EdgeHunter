"""Pure result contracts for local ValueDetector backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any, Mapping


MIN_OFFERED_ODDS = 1.01


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
