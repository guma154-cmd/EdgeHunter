from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from typing import Any

FORBIDDEN_OPERATIONAL_TERMS = {
    "aposta", "apostar", "entrada", "sinal de aposta", "recomendado",
    "recomendação operacional", "lucro", "gain", "stake", "kelly", "bankroll",
    "bet_amount", "wager", "execute", "execution", "place_bet", "telegram",
    "scheduler", "autoevolution", "recomendacao"
}


def _check_operational_language(text: str) -> None:
    if not isinstance(text, str):
        return
    text_lower = text.lower()
    # Check whole words to avoid false positives on substrings
    words = re.findall(r'\b\w+\b', text_lower)
    for word in words:
        if word in FORBIDDEN_OPERATIONAL_TERMS:
            raise ValueError(f"Operational language detected: {word}")
    
    # Also check full string matches for multi-word terms
    for term in FORBIDDEN_OPERATIONAL_TERMS:
        if term in text_lower:
            raise ValueError(f"Operational language detected: {term}")


class ReliabilityLevel(str, Enum):
    RELIABILITY_HIGH = "RELIABILITY_HIGH"
    RELIABILITY_MEDIUM = "RELIABILITY_MEDIUM"
    RELIABILITY_LOW = "RELIABILITY_LOW"
    RELIABILITY_INSUFFICIENT_SAMPLE = "RELIABILITY_INSUFFICIENT_SAMPLE"


class TrendStatus(str, Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    VOLATILE = "VOLATILE"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"


def _check_string(val: Any, name: str) -> None:
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"{name} cannot be empty.")


@dataclass(frozen=True)
class CalibrationSegmentKey:
    source: str
    detection_method: str
    simulation_label: str
    market: str
    selection: str
    assertiveness_bucket: str

    def __post_init__(self):
        _check_string(self.source, "source")
        _check_string(self.detection_method, "detection_method")
        _check_string(self.simulation_label, "simulation_label")
        _check_string(self.market, "market")
        _check_string(self.selection, "selection")
        _check_string(self.assertiveness_bucket, "assertiveness_bucket")

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "detection_method": self.detection_method,
            "simulation_label": self.simulation_label,
            "market": self.market,
            "selection": self.selection,
            "assertiveness_bucket": self.assertiveness_bucket
        }


def _check_bounds(val: Any, name: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
    if not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be numeric.")
    if not (min_val <= val <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}.")


@dataclass(frozen=True)
class CalibrationSegmentMetrics:
    segment_key: CalibrationSegmentKey
    sample_size: int
    resolved_total: int
    confirmed_total: int
    not_confirmed_total: int
    unresolved_total: int
    invalidated_total: int
    confirmation_rate: float
    not_confirmed_rate: float
    average_calibrated_assertiveness: float
    average_confidence: float
    false_positive_rate: float
    false_negative_rate: float
    trend_status: TrendStatus
    reliability_level: ReliabilityLevel

    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False, init=False)
    bet_placed: bool = field(default=False, init=False)
    alerted: bool = field(default=False, init=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        if not isinstance(self.segment_key, CalibrationSegmentKey):
            raise ValueError("segment_key must be CalibrationSegmentKey.")
        if not isinstance(self.sample_size, int) or self.sample_size < 0:
            raise ValueError("sample_size must be >= 0.")

        for num in [self.resolved_total, self.confirmed_total, self.not_confirmed_total, self.unresolved_total, self.invalidated_total]:
            if not isinstance(num, int) or num < 0:
                raise ValueError("Count fields must be integers >= 0.")

        _check_bounds(self.confirmation_rate, "confirmation_rate")
        _check_bounds(self.not_confirmed_rate, "not_confirmed_rate")
        _check_bounds(self.average_calibrated_assertiveness, "average_calibrated_assertiveness")
        _check_bounds(self.average_confidence, "average_confidence")
        _check_bounds(self.false_positive_rate, "false_positive_rate")
        _check_bounds(self.false_negative_rate, "false_negative_rate")

        if not isinstance(self.trend_status, TrendStatus):
            raise ValueError("Invalid trend_status.")
        if not isinstance(self.reliability_level, ReliabilityLevel):
            raise ValueError("Invalid reliability_level.")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["segment_key"] = self.segment_key.to_dict()
        d["trend_status"] = self.trend_status.value
        d["reliability_level"] = self.reliability_level.value
        return d


@dataclass(frozen=True)
class ReliabilityScore:
    score_id: str
    segment_key: CalibrationSegmentKey
    score: float
    reliability_level: ReliabilityLevel
    confidence: float
    sample_size: int
    reason: str

    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False, init=False)
    bet_placed: bool = field(default=False, init=False)
    alerted: bool = field(default=False, init=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        _check_string(self.score_id, "score_id")
        if not isinstance(self.segment_key, CalibrationSegmentKey):
            raise ValueError("segment_key must be CalibrationSegmentKey.")
        
        _check_bounds(self.score, "score")
        _check_bounds(self.confidence, "confidence")
        if not isinstance(self.sample_size, int) or self.sample_size < 0:
            raise ValueError("sample_size must be >= 0.")
        
        if not isinstance(self.reliability_level, ReliabilityLevel):
            raise ValueError("Invalid reliability_level.")
            
        _check_string(self.reason, "reason")
        _check_operational_language(self.reason)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["segment_key"] = self.segment_key.to_dict()
        d["reliability_level"] = self.reliability_level.value
        return d


@dataclass(frozen=True)
class AdvancedCalibrationReport:
    report_id: str
    scores: list[ReliabilityScore]
    segments_metrics: list[CalibrationSegmentMetrics]
    
    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False, init=False)
    bet_placed: bool = field(default=False, init=False)
    alerted: bool = field(default=False, init=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        _check_string(self.report_id, "report_id")
        if not isinstance(self.scores, list) or any(not isinstance(s, ReliabilityScore) for s in self.scores):
            raise ValueError("scores must be a list of ReliabilityScore.")
        if not isinstance(self.segments_metrics, list) or any(not isinstance(m, CalibrationSegmentMetrics) for m in self.segments_metrics):
            raise ValueError("segments_metrics must be a list of CalibrationSegmentMetrics.")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scores"] = [s.to_dict() for s in self.scores]
        d["segments_metrics"] = [m.to_dict() for m in self.segments_metrics]
        return d
