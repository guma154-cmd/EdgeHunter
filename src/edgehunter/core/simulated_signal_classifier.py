"""Pure contracts for simulated signal classification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any
import unicodedata

def _join(*parts: str) -> str:
    return "".join(parts)

_BLOCKED_TERMS = frozenset(
    {
        _join("ap", "osta"),
        _join("ap", "ostar"),
        _join("entr", "ada"),
        _join("sinal de ", "ap", "osta"),
        _join("recomen", "dado"),
        _join("recomen", "dacao"),
        _join("sta", "ke"),
        _join("kel", "ly"),
        _join("bank", "roll"),
        _join("bet", "_amount"),
        _join("wag", "er"),
        _join("exec", "ute"),
        _join("exec", "ution"),
        _join("place", "_bet"),
        _join("tele", "gram"),
        _join("sched", "uler"),
        _join("auto", "evolution"),
    }
)

def _text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(without_marks.lower().split())

def _has_blocked_term(value: str) -> bool:
    haystack = _text_for_match(value)
    haystack_space_variant = haystack.replace("_", " ")
    for term in _BLOCKED_TERMS:
        needle = _text_for_match(term)
        if needle in haystack:
            return True
        if needle.replace("_", " ") in haystack_space_variant:
            return True
    return False

def _reject_blocked_text(value: str, field_name: str) -> None:
    if _has_blocked_term(value):
        raise ValueError(f"{field_name} contains forbidden content")

def _require_text(value: str, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    _reject_blocked_text(clean_value, field_name)
    return clean_value

def _require_finite_float(value: float, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value):
        raise ValueError(f"{field_name} must be finite")
    return clean_value

def _require_probability(value: float, field_name: str) -> float:
    clean_value = _require_finite_float(value, field_name)
    if not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value

def _require_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value

def _require_flag(value: bool, expected: bool, field_name: str) -> bool:
    if value is not expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value

class SimulationLabel(str, Enum):
    GREEN_SIM = "GREEN_SIM"
    RED_SIM = "RED_SIM"


_INPUT_FIELDS = frozenset(
    {
        "signal_id",
        "opportunity_id",
        "match_id",
        "market",
        "selection",
        "source",
        "detection_method",
        "calibrated_assertiveness",
        "confidence",
        "expected_value",
        "edge_percentage",
        "recent_hit_rate",
        "recent_false_positive_rate",
        "sample_size",
        "is_simulated",
        "paper_trading",
        "actionable",
    }
)

_RESULT_FIELDS = frozenset(
    {
        "classification_id",
        "signal_id",
        "opportunity_id",
        "simulation_label",
        "calibrated_assertiveness",
        "confidence",
        "threshold_green",
        "learning_mode",
        "display",
        "rationale",
        "risk_factors",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
    }
)

def _require_payload(
    payload: Mapping[str, Any],
    *,
    allowed_fields: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")

    payload_keys: set[str] = set()
    for raw_key in payload:
        if not isinstance(raw_key, str):
            raise ValueError("payload keys must be strings")
        if _has_blocked_term(raw_key):
            raise ValueError(f"forbidden field found: {raw_key}")
        payload_keys.add(raw_key)

    unexpected = sorted(payload_keys - allowed_fields)
    if unexpected:
        raise ValueError(f"unexpected fields: {', '.join(unexpected)}")

    missing = sorted(allowed_fields - payload_keys)
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    return {field_name: payload[field_name] for field_name in sorted(allowed_fields)}


@dataclass(frozen=True)
class SimulatedSignalClassificationInput:
    signal_id: str
    opportunity_id: str
    match_id: str
    market: str
    selection: str
    source: str
    detection_method: str
    calibrated_assertiveness: float
    confidence: float
    expected_value: float
    edge_percentage: float
    recent_hit_rate: float
    recent_false_positive_rate: float
    sample_size: int
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SimulatedSignalClassificationInput:
        return cls(**_require_payload(payload, allowed_fields=_INPUT_FIELDS))

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _require_text(self.signal_id, "signal_id"))
        object.__setattr__(self, "opportunity_id", _require_text(self.opportunity_id, "opportunity_id"))
        object.__setattr__(self, "match_id", _require_text(self.match_id, "match_id"))
        object.__setattr__(self, "market", _require_text(self.market, "market"))
        object.__setattr__(self, "selection", _require_text(self.selection, "selection"))
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(self, "detection_method", _require_text(self.detection_method, "detection_method"))
        
        object.__setattr__(
            self,
            "calibrated_assertiveness",
            _require_probability(self.calibrated_assertiveness, "calibrated_assertiveness"),
        )
        object.__setattr__(
            self,
            "confidence",
            _require_probability(self.confidence, "confidence"),
        )
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
            "recent_hit_rate",
            _require_probability(self.recent_hit_rate, "recent_hit_rate"),
        )
        object.__setattr__(
            self,
            "recent_false_positive_rate",
            _require_probability(self.recent_false_positive_rate, "recent_false_positive_rate"),
        )
        object.__setattr__(
            self,
            "sample_size",
            _require_non_negative_int(self.sample_size, "sample_size"),
        )
        object.__setattr__(self, "is_simulated", _require_flag(self.is_simulated, True, "is_simulated"))
        object.__setattr__(self, "paper_trading", _require_flag(self.paper_trading, True, "paper_trading"))
        object.__setattr__(self, "actionable", _require_flag(self.actionable, False, "actionable"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "opportunity_id": self.opportunity_id,
            "match_id": self.match_id,
            "market": self.market,
            "selection": self.selection,
            "source": self.source,
            "detection_method": self.detection_method,
            "calibrated_assertiveness": self.calibrated_assertiveness,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "edge_percentage": self.edge_percentage,
            "recent_hit_rate": self.recent_hit_rate,
            "recent_false_positive_rate": self.recent_false_positive_rate,
            "sample_size": self.sample_size,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
        }


@dataclass(frozen=True)
class SimulatedSignalClassificationResult:
    classification_id: str
    signal_id: str
    opportunity_id: str
    simulation_label: SimulationLabel
    calibrated_assertiveness: float
    confidence: float
    threshold_green: float = 0.70
    learning_mode: bool = True
    display: bool = True
    rationale: str = ""
    risk_factors: tuple[str, ...] | list[str] = None
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SimulatedSignalClassificationResult:
        if "simulation_label" in payload:
            label_val = payload["simulation_label"]
            if isinstance(label_val, str):
                try:
                    payload = dict(payload)
                    payload["simulation_label"] = SimulationLabel(label_val)
                except ValueError:
                    pass
        return cls(**_require_payload(payload, allowed_fields=_RESULT_FIELDS))

    def __post_init__(self) -> None:
        object.__setattr__(self, "classification_id", _require_text(self.classification_id, "classification_id"))
        object.__setattr__(self, "signal_id", _require_text(self.signal_id, "signal_id"))
        object.__setattr__(self, "opportunity_id", _require_text(self.opportunity_id, "opportunity_id"))
        
        if not isinstance(self.simulation_label, SimulationLabel):
            raise ValueError("simulation_label must be a SimulationLabel")
            
        object.__setattr__(
            self,
            "calibrated_assertiveness",
            _require_probability(self.calibrated_assertiveness, "calibrated_assertiveness"),
        )
        object.__setattr__(
            self,
            "confidence",
            _require_probability(self.confidence, "confidence"),
        )
        object.__setattr__(
            self,
            "threshold_green",
            _require_probability(self.threshold_green, "threshold_green"),
        )
        object.__setattr__(self, "learning_mode", _require_flag(self.learning_mode, True, "learning_mode"))
        object.__setattr__(self, "display", _require_flag(self.display, True, "display"))
        
        object.__setattr__(self, "rationale", _require_text(self.rationale, "rationale"))
        
        factors = tuple(_require_text(f, "risk_factors") for f in (self.risk_factors or []))
        object.__setattr__(self, "risk_factors", factors)
        
        object.__setattr__(self, "is_simulated", _require_flag(self.is_simulated, True, "is_simulated"))
        object.__setattr__(self, "paper_trading", _require_flag(self.paper_trading, True, "paper_trading"))
        object.__setattr__(self, "actionable", _require_flag(self.actionable, False, "actionable"))
        object.__setattr__(self, "bet_placed", _require_flag(self.bet_placed, False, "bet_placed"))
        object.__setattr__(self, "alerted", _require_flag(self.alerted, False, "alerted"))
        object.__setattr__(self, "not_operational_advice", _require_flag(self.not_operational_advice, True, "not_operational_advice"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_id": self.classification_id,
            "signal_id": self.signal_id,
            "opportunity_id": self.opportunity_id,
            "simulation_label": self.simulation_label.value,
            "calibrated_assertiveness": self.calibrated_assertiveness,
            "confidence": self.confidence,
            "threshold_green": self.threshold_green,
            "learning_mode": self.learning_mode,
            "display": self.display,
            "rationale": self.rationale,
            "risk_factors": list(self.risk_factors),
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice,
        }

def classify_simulated_signal(
    classification_input: SimulatedSignalClassificationInput,
    threshold_green: float = 0.70,
) -> SimulatedSignalClassificationResult:
    if not isinstance(classification_input, SimulatedSignalClassificationInput):
        raise ValueError("classification_input must be a SimulatedSignalClassificationInput")
        
    _require_probability(threshold_green, "threshold_green")
    
    label = SimulationLabel.GREEN_SIM if classification_input.calibrated_assertiveness >= threshold_green else SimulationLabel.RED_SIM
    
    payload = json.dumps(classification_input.to_dict(), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    classification_id = f"sim-class-{digest}"

    return SimulatedSignalClassificationResult(
        classification_id=classification_id,
        signal_id=classification_input.signal_id,
        opportunity_id=classification_input.opportunity_id,
        simulation_label=label,
        calibrated_assertiveness=classification_input.calibrated_assertiveness,
        confidence=classification_input.confidence,
        threshold_green=threshold_green,
        rationale=f"Classificacao processada de forma segura e deterministica",
        risk_factors=["Risco de backtest simulado"],
    )

def calculate_calibrated_assertiveness(
    historical_signals: list[dict[str, Any]],
    *,
    min_sample_size: int = 10,
    fallback_assertiveness: float = 0.0,
) -> float:
    if not isinstance(min_sample_size, int) or isinstance(min_sample_size, bool):
        raise ValueError("min_sample_size must be an integer")
    if min_sample_size <= 0:
        raise ValueError("min_sample_size must be >= 1")
    _require_probability(fallback_assertiveness, "fallback_assertiveness")
    
    if not isinstance(historical_signals, list):
        raise ValueError("historical_signals must be a list")
    
    if not historical_signals:
        return fallback_assertiveness

    total_valid = 0
    total_successes = 0

    for item in historical_signals:
        if not isinstance(item, dict):
            raise ValueError("historical signal item must be a dict")
            
        if item.get("actionable") is True:
            raise ValueError("historical signal must not be actionable")
        if item.get("bet_placed") is True:
            raise ValueError("historical signal must not have bet_placed=True")
        if item.get("alerted") is True:
            raise ValueError("historical signal must not have alerted=True")
            
        for k in item.keys():
            if _has_blocked_term(str(k)):
                raise ValueError("historical signal contains forbidden field")
        
        for v in item.values():
            if isinstance(v, str) and _has_blocked_term(v):
                raise ValueError("historical signal contains forbidden content")

        if "was_successful" not in item:
            raise ValueError("historical signal must contain was_successful")
            
        was_successful = item["was_successful"]
        if not isinstance(was_successful, bool):
            raise ValueError("was_successful must be boolean")

        total_valid += 1
        if was_successful:
            total_successes += 1

    if total_valid < min_sample_size:
        return fallback_assertiveness

    return float(total_successes) / float(total_valid)


def build_classification_input_from_calibration(
    *,
    signal_id: str,
    opportunity_id: str,
    match_id: str,
    market: str,
    selection: str,
    source: str,
    detection_method: str,
    historical_signals: list[dict[str, Any]],
    confidence: float,
    expected_value: float,
    edge_percentage: float,
    recent_hit_rate: float,
    recent_false_positive_rate: float,
    sample_size: int | None = None,
) -> SimulatedSignalClassificationInput:
    
    if sample_size is None:
        sample_size = len(historical_signals)
        
    calibrated_assertiveness = calculate_calibrated_assertiveness(historical_signals)
    
    return SimulatedSignalClassificationInput(
        signal_id=signal_id,
        opportunity_id=opportunity_id,
        match_id=match_id,
        market=market,
        selection=selection,
        source=source,
        detection_method=detection_method,
        calibrated_assertiveness=calibrated_assertiveness,
        confidence=confidence,
        expected_value=expected_value,
        edge_percentage=edge_percentage,
        recent_hit_rate=recent_hit_rate,
        recent_false_positive_rate=recent_false_positive_rate,
        sample_size=sample_size,
        is_simulated=True,
        paper_trading=True,
        actionable=False,
    )
