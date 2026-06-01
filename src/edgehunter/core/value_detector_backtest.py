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
REPORT_FORMAT_DICT = "dict"
REPORT_FORMAT_MARKDOWN = "markdown"
SUPPORTED_REPORT_FORMATS = frozenset({REPORT_FORMAT_DICT, REPORT_FORMAT_MARKDOWN})
DEFAULT_REPORT_SELECTION_SAMPLE_LIMIT = 5


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
            if metric_name.endswith("_rate") and metric_value > 1:
                raise ValueError(
                    f"{field_name}.{key}.{metric_name} must be between 0 and 1",
                )
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
        if self.total_opportunities > self.total_analyzed:
            raise ValueError("total_opportunities must be <= total_analyzed")
        if self.total_hits > self.total_opportunities:
            raise ValueError("total_hits must be <= total_opportunities")
        if self.total_false_positives > self.total_opportunities:
            raise ValueError(
                "total_false_positives must be <= total_opportunities",
            )
        if self.total_hits + self.total_false_positives > self.total_opportunities:
            raise ValueError(
                "total_hits and total_false_positives must not exceed total_opportunities",
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
    return calculate_backtest_metrics([], total_analyzed=total_analyzed)


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


def _validate_selection_for_metrics(selection: BacktestSelectionResult) -> None:
    if selection.is_hit and selection.is_false_positive:
        raise ValueError("selection cannot be both hit and false positive")
    _require_finite_float(selection.expected_value, "expected_value")
    _require_finite_float(selection.edge_percentage, "edge_percentage")


def _selection_summary(
    selections: tuple[BacktestSelectionResult, ...],
) -> dict[str, int | float]:
    total_opportunities = len(selections)
    if total_opportunities == 0:
        return {
            "total_opportunities": 0,
            "total_hits": 0,
            "total_false_positives": 0,
            "hit_rate": 0.0,
            "false_positive_rate": 0.0,
            "average_expected_value": 0.0,
            "average_edge_percentage": 0.0,
            "opportunities": 0,
            "hits": 0,
            "false_positives": 0,
        }

    total_hits = sum(int(selection.is_hit) for selection in selections)
    total_false_positives = sum(
        int(selection.is_false_positive)
        for selection in selections
    )
    average_expected_value = (
        sum(selection.expected_value for selection in selections)
        / total_opportunities
    )
    average_edge_percentage = (
        sum(selection.edge_percentage for selection in selections)
        / total_opportunities
    )

    return {
        "total_opportunities": total_opportunities,
        "total_hits": total_hits,
        "total_false_positives": total_false_positives,
        "hit_rate": total_hits / total_opportunities,
        "false_positive_rate": total_false_positives / total_opportunities,
        "average_expected_value": average_expected_value,
        "average_edge_percentage": average_edge_percentage,
        "opportunities": total_opportunities,
        "hits": total_hits,
        "false_positives": total_false_positives,
    }


def _group_selection_metrics(
    selections: tuple[BacktestSelectionResult, ...],
    field_name: str,
) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, list[BacktestSelectionResult]] = {}
    for selection in selections:
        key = getattr(selection, field_name)
        grouped.setdefault(key, []).append(selection)
    return {
        key: _selection_summary(tuple(values))
        for key, values in sorted(grouped.items())
    }


def calculate_backtest_metrics(
    selections: list[BacktestSelectionResult] | tuple[BacktestSelectionResult, ...],
    total_analyzed: int,
) -> BacktestMetrics:
    total_analyzed_clean = _require_non_negative_int(total_analyzed, "total_analyzed")
    selection_tuple = tuple(selections)
    if not all(isinstance(selection, BacktestSelectionResult) for selection in selection_tuple):
        raise ValueError("selections must contain BacktestSelectionResult values")

    for selection in selection_tuple:
        _validate_selection_for_metrics(selection)

    total_opportunities = len(selection_tuple)
    if total_opportunities > total_analyzed_clean:
        raise ValueError("total_opportunities must be <= total_analyzed")

    summary = _selection_summary(selection_tuple)

    return BacktestMetrics(
        total_analyzed=total_analyzed_clean,
        total_opportunities=int(summary["total_opportunities"]),
        total_hits=int(summary["total_hits"]),
        total_false_positives=int(summary["total_false_positives"]),
        hit_rate=float(summary["hit_rate"]),
        false_positive_rate=float(summary["false_positive_rate"]),
        coverage_rate=(
            total_opportunities / total_analyzed_clean
            if total_analyzed_clean
            else 0.0
        ),
        average_expected_value=float(summary["average_expected_value"]),
        average_edge_percentage=float(summary["average_edge_percentage"]),
        by_source=_group_selection_metrics(selection_tuple, "source"),
        by_detection_method=_group_selection_metrics(
            selection_tuple,
            "detection_method",
        ),
    )


def _report_safety_payload() -> dict[str, str]:
    return {
        "paper_trading": "paper trading local",
        "simulation": "simulacao tecnica",
        "not_operational_recommendation": "nao e recomendacao operacional",
        "no_real_operation": "nao autoriza operacao real",
        "no_financial_sizing": "nao contem dimensionamento financeiro",
        "no_capital_formula": "nao contem formula de fracao de capital",
        "no_balance_management": "nao contem gestao de saldo",
        "no_execution": "nao executa operacao",
        "no_alerting": "nao envia alerta",
        "no_public_interface": "nao expoe interface publica",
    }


def _report_selection_sample(
    result: BacktestRunResult,
) -> list[dict[str, Any]]:
    return [
        selection.to_dict()
        for selection in result.selections[:DEFAULT_REPORT_SELECTION_SAMPLE_LIMIT]
    ]


def _build_report_payload(result: BacktestRunResult) -> dict[str, Any]:
    metrics = result.metrics.to_dict()
    return {
        "run_id": result.run_id,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "status": {
            "is_simulated": result.is_simulated,
            "paper_trading": result.paper_trading,
            "actionable": result.actionable,
        },
        "safety": _report_safety_payload(),
        "metrics": metrics,
        "by_source": metrics["by_source"],
        "by_detection_method": metrics["by_detection_method"],
        "warnings": list(result.warnings),
        "reasons": list(result.reasons),
        "selection_sample": _report_selection_sample(result),
        "selection_sample_limit": DEFAULT_REPORT_SELECTION_SAMPLE_LIMIT,
        "total_selections": len(result.selections),
        "is_simulated": result.is_simulated,
        "paper_trading": result.paper_trading,
        "actionable": result.actionable,
    }


def _format_grouped_metrics(
    grouped: Mapping[str, Mapping[str, int | float]],
) -> list[str]:
    if not grouped:
        return ["- nenhum agrupamento"]
    return [
        (
            f"- {key}: total_opportunities={values['total_opportunities']}; "
            f"total_hits={values['total_hits']}; "
            f"total_false_positives={values['total_false_positives']}; "
            f"hit_rate={values['hit_rate']}; "
            f"false_positive_rate={values['false_positive_rate']}; "
            f"average_expected_value={values['average_expected_value']}; "
            f"average_edge_percentage={values['average_edge_percentage']}"
        )
        for key, values in sorted(grouped.items())
    ]


def _format_selection_sample(selection_sample: list[dict[str, Any]]) -> list[str]:
    if not selection_sample:
        return ["- nenhuma selecao"]
    return [
        (
            f"- {selection['match_id']} {selection['market']} "
            f"{selection['selection']}: hit={selection['is_hit']}; "
            f"false_positive={selection['is_false_positive']}; "
            f"expected_value={selection['expected_value']}; "
            f"edge_percentage={selection['edge_percentage']}"
        )
        for selection in selection_sample
    ]


def _format_markdown_report(payload: Mapping[str, Any]) -> str:
    metrics = payload["metrics"]
    status = payload["status"]
    safety = payload["safety"]
    lines = [
        "# Relatorio local de paper trading",
        "",
        f"- Run ID: {payload['run_id']}",
        f"- Inicio: {payload['started_at']}",
        f"- Fim: {payload['finished_at']}",
        "",
        "## Status",
        f"- Simulacao: {str(status['is_simulated']).lower()}",
        f"- Paper trading: {str(status['paper_trading']).lower()}",
        f"- Acionavel: {str(status['actionable']).lower()}",
        "",
        "## Avisos de seguranca",
    ]
    lines.extend(f"- {value}" for value in safety.values())
    lines.extend(
        [
            "",
            "## Metricas",
            f"- Total analisado: {metrics['total_analyzed']}",
            f"- Total de oportunidades: {metrics['total_opportunities']}",
            f"- Total de acertos: {metrics['total_hits']}",
            f"- Total de falsos positivos: {metrics['total_false_positives']}",
            f"- Taxa de acerto: {metrics['hit_rate']}",
            f"- Taxa de falso positivo: {metrics['false_positive_rate']}",
            f"- Cobertura: {metrics['coverage_rate']}",
            f"- EV medio: {metrics['average_expected_value']}",
            f"- Edge medio: {metrics['average_edge_percentage']}",
            "",
            "## Por fonte",
        ],
    )
    lines.extend(_format_grouped_metrics(payload["by_source"]))
    lines.extend(["", "## Por metodo de deteccao"])
    lines.extend(_format_grouped_metrics(payload["by_detection_method"]))
    lines.extend(
        [
            "",
            "## Avisos",
            *(f"- {warning}" for warning in payload["warnings"]),
            "",
            "## Razoes",
            *(f"- {reason}" for reason in payload["reasons"]),
            "",
            "## Amostra limitada de selecoes",
            f"- Limite: {payload['selection_sample_limit']}",
            f"- Total de selecoes: {payload['total_selections']}",
        ],
    )
    lines.extend(_format_selection_sample(payload["selection_sample"]))
    return "\n".join(lines)


def generate_paper_trading_report(
    result: BacktestRunResult,
    format: str = REPORT_FORMAT_DICT,
) -> dict[str, Any] | str:
    if not isinstance(result, BacktestRunResult):
        raise ValueError("result must be a BacktestRunResult")

    format_clean = _require_text(format, "format").lower()
    if format_clean not in SUPPORTED_REPORT_FORMATS:
        raise ValueError(f"unsupported report format: {format_clean}")

    payload = _build_report_payload(result)
    if format_clean == REPORT_FORMAT_DICT:
        return payload
    return _format_markdown_report(payload)


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
        metrics=calculate_backtest_metrics(
            selection_tuple,
            total_analyzed=len(historical_matches),
        ),
        selections=selection_tuple,
        warnings=(),
        reasons=reasons,
    )
