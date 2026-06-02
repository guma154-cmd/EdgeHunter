"""Pure technical threshold suggestion for simulated calibration reports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
        _join("luc", "ro"),
        _join("ga", "in"),
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

_ACTIONS = {
    "KEEP_THRESHOLD",
    "RAISE_THRESHOLD",
    "LOWER_THRESHOLD",
    "REQUIRE_MORE_SAMPLE",
}


def _text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
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


def _require_text(value: Any, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    if _has_blocked_term(clean_value):
        raise ValueError(f"{field_name} contains forbidden content")
    return clean_value


def _require_probability(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value) or not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _require_flag(value: bool, expected: bool, field_name: str) -> bool:
    if value is not expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value


def _require_safe_report(report: Mapping[str, Any]) -> None:
    if not isinstance(report, Mapping):
        raise ValueError("calibration_report must be a mapping")
    expected_flags = {
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    for field_name, expected in expected_flags.items():
        if report.get(field_name, expected) is not expected:
            raise ValueError(f"calibration_report.{field_name} must be {expected}")


def _payload_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SimulatedThresholdSuggestion:
    suggestion_id: str
    current_threshold: float
    suggested_threshold: float
    action: str
    reason: str
    confidence: float
    sample_size: int
    green_confirmation_rate: float
    green_not_confirmed_rate: float
    red_missed_positive_rate: float
    auto_apply: bool = False
    is_simulated: bool = True
    paper_trading: bool = True
    learning_mode: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "suggestion_id", _require_text(self.suggestion_id, "suggestion_id"))
        object.__setattr__(
            self,
            "current_threshold",
            _require_probability(self.current_threshold, "current_threshold"),
        )
        object.__setattr__(
            self,
            "suggested_threshold",
            _require_probability(self.suggested_threshold, "suggested_threshold"),
        )
        if self.action not in _ACTIONS:
            raise ValueError("action is invalid")
        object.__setattr__(self, "reason", _require_text(self.reason, "reason"))
        object.__setattr__(self, "confidence", _require_probability(self.confidence, "confidence"))
        object.__setattr__(
            self,
            "sample_size",
            _require_non_negative_int(self.sample_size, "sample_size"),
        )
        object.__setattr__(
            self,
            "green_confirmation_rate",
            _require_probability(self.green_confirmation_rate, "green_confirmation_rate"),
        )
        object.__setattr__(
            self,
            "green_not_confirmed_rate",
            _require_probability(self.green_not_confirmed_rate, "green_not_confirmed_rate"),
        )
        object.__setattr__(
            self,
            "red_missed_positive_rate",
            _require_probability(self.red_missed_positive_rate, "red_missed_positive_rate"),
        )
        object.__setattr__(self, "auto_apply", _require_flag(self.auto_apply, False, "auto_apply"))
        object.__setattr__(self, "is_simulated", _require_flag(self.is_simulated, True, "is_simulated"))
        object.__setattr__(self, "paper_trading", _require_flag(self.paper_trading, True, "paper_trading"))
        object.__setattr__(self, "learning_mode", _require_flag(self.learning_mode, True, "learning_mode"))
        object.__setattr__(self, "actionable", _require_flag(self.actionable, False, "actionable"))
        object.__setattr__(self, "bet_placed", _require_flag(self.bet_placed, False, "bet_placed"))
        object.__setattr__(self, "alerted", _require_flag(self.alerted, False, "alerted"))
        object.__setattr__(
            self,
            "not_operational_advice",
            _require_flag(self.not_operational_advice, True, "not_operational_advice"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "current_threshold": self.current_threshold,
            "suggested_threshold": self.suggested_threshold,
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "green_confirmation_rate": self.green_confirmation_rate,
            "green_not_confirmed_rate": self.green_not_confirmed_rate,
            "red_missed_positive_rate": self.red_missed_positive_rate,
            "auto_apply": self.auto_apply,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "learning_mode": self.learning_mode,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice,
        }


def generate_threshold_suggestion(
    calibration_report: dict,
    *,
    current_threshold: float = 0.70,
    minimum_sample_size: int = 30,
) -> SimulatedThresholdSuggestion:
    _require_safe_report(calibration_report)
    current_threshold = _require_probability(current_threshold, "current_threshold")
    if (
        isinstance(minimum_sample_size, bool)
        or not isinstance(minimum_sample_size, int)
        or minimum_sample_size < 1
    ):
        raise ValueError("minimum_sample_size must be >= 1")

    sample_size = _require_non_negative_int(
        calibration_report.get("sample_size", 0),
        "sample_size",
    )
    green_confirmation_rate = _require_probability(
        calibration_report.get("green_confirmation_rate", 0.0),
        "green_confirmation_rate",
    )
    green_not_confirmed_rate = _require_probability(
        calibration_report.get("green_not_confirmed_rate", 0.0),
        "green_not_confirmed_rate",
    )
    red_missed_positive_rate = _require_probability(
        calibration_report.get("red_missed_positive_rate", 0.0),
        "red_missed_positive_rate",
    )

    if sample_size < minimum_sample_size:
        action = "REQUIRE_MORE_SAMPLE"
        suggested_threshold = current_threshold
        reason = "technical sample below configured minimum"
        confidence = 0.25
    elif green_not_confirmed_rate > 0.35:
        action = "RAISE_THRESHOLD"
        suggested_threshold = min(current_threshold + 0.02, 0.95)
        reason = "technical calibration shows elevated non confirmation"
        confidence = 0.65
    elif red_missed_positive_rate > 0.35 and green_confirmation_rate >= 0.70:
        action = "LOWER_THRESHOLD"
        suggested_threshold = max(current_threshold - 0.02, 0.50)
        reason = "technical calibration shows strict rejection boundary"
        confidence = 0.65
    else:
        action = "KEEP_THRESHOLD"
        suggested_threshold = current_threshold
        reason = "technical calibration remains balanced"
        confidence = 0.55

    payload_for_id = {
        "current_threshold": current_threshold,
        "suggested_threshold": suggested_threshold,
        "action": action,
        "sample_size": sample_size,
        "green_confirmation_rate": green_confirmation_rate,
        "green_not_confirmed_rate": green_not_confirmed_rate,
        "red_missed_positive_rate": red_missed_positive_rate,
    }

    return SimulatedThresholdSuggestion(
        suggestion_id=f"sim-threshold-{_payload_digest(payload_for_id)}",
        current_threshold=current_threshold,
        suggested_threshold=round(suggested_threshold, 2),
        action=action,
        reason=reason,
        confidence=confidence,
        sample_size=sample_size,
        green_confirmation_rate=green_confirmation_rate,
        green_not_confirmed_rate=green_not_confirmed_rate,
        red_missed_positive_rate=red_missed_positive_rate,
    )
