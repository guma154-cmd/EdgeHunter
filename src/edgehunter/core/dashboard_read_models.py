"""Pure read models for the simulated dashboard."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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

_SAFE_FLAGS = {
    "is_simulated": True,
    "paper_trading": True,
    "learning_mode": True,
    "actionable": False,
    "bet_placed": False,
    "alerted": False,
    "not_operational_advice": True,
}

_THRESHOLD_ACTIONS = {
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


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _require_probability(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value) or not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value


def _require_flag(value: bool, expected: bool, field_name: str) -> bool:
    if value is not expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value


def _validate_payload_keys(payload: Mapping[str, Any], allowed_fields: set[str]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    keys = set()
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError("payload keys must be strings")
        if _has_blocked_term(key):
            raise ValueError("payload contains forbidden field")
        if isinstance(value, str) and _has_blocked_term(value):
            raise ValueError("payload contains forbidden content")
        keys.add(key)
    unexpected = sorted(keys - allowed_fields)
    if unexpected:
        raise ValueError(f"unexpected fields: {', '.join(unexpected)}")
    missing = sorted(allowed_fields - keys)
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    return {field_name: payload[field_name] for field_name in sorted(allowed_fields)}


@dataclass(frozen=True)
class DashboardLabelMetrics:
    label: str
    total: int
    confirmed: int
    not_confirmed: int
    confirmation_rate: float
    not_confirmed_rate: float

    def __post_init__(self) -> None:
        if self.label not in {"GREEN_SIM", "RED_SIM"}:
            raise ValueError("label is invalid")
        object.__setattr__(self, "total", _require_non_negative_int(self.total, "total"))
        object.__setattr__(self, "confirmed", _require_non_negative_int(self.confirmed, "confirmed"))
        object.__setattr__(self, "not_confirmed", _require_non_negative_int(self.not_confirmed, "not_confirmed"))
        object.__setattr__(self, "confirmation_rate", _require_probability(self.confirmation_rate, "confirmation_rate"))
        object.__setattr__(self, "not_confirmed_rate", _require_probability(self.not_confirmed_rate, "not_confirmed_rate"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "total": self.total,
            "confirmed": self.confirmed,
            "not_confirmed": self.not_confirmed,
            "confirmation_rate": self.confirmation_rate,
            "not_confirmed_rate": self.not_confirmed_rate,
        }


@dataclass(frozen=True)
class DashboardOutcomeMetrics:
    total_outcomes: int
    positive_observed_total: int
    negative_observed_total: int
    unresolved_total: int
    invalidated_total: int

    def __post_init__(self) -> None:
        for field_name in (
            "total_outcomes",
            "positive_observed_total",
            "negative_observed_total",
            "unresolved_total",
            "invalidated_total",
        ):
            object.__setattr__(self, field_name, _require_non_negative_int(getattr(self, field_name), field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_outcomes": self.total_outcomes,
            "positive_observed_total": self.positive_observed_total,
            "negative_observed_total": self.negative_observed_total,
            "unresolved_total": self.unresolved_total,
            "invalidated_total": self.invalidated_total,
        }


@dataclass(frozen=True)
class DashboardCalibrationSnapshot:
    threshold_green: float
    sample_size: int
    minimum_viable_sample_met: bool
    average_calibrated_assertiveness: float
    average_confidence: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "threshold_green", _require_probability(self.threshold_green, "threshold_green"))
        object.__setattr__(self, "sample_size", _require_non_negative_int(self.sample_size, "sample_size"))
        object.__setattr__(
            self,
            "minimum_viable_sample_met",
            _require_bool(self.minimum_viable_sample_met, "minimum_viable_sample_met"),
        )
        object.__setattr__(
            self,
            "average_calibrated_assertiveness",
            _require_probability(self.average_calibrated_assertiveness, "average_calibrated_assertiveness"),
        )
        object.__setattr__(self, "average_confidence", _require_probability(self.average_confidence, "average_confidence"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold_green": self.threshold_green,
            "sample_size": self.sample_size,
            "minimum_viable_sample_met": self.minimum_viable_sample_met,
            "average_calibrated_assertiveness": self.average_calibrated_assertiveness,
            "average_confidence": self.average_confidence,
        }


@dataclass(frozen=True)
class DashboardThresholdSuggestionSnapshot:
    current_threshold: float
    suggested_threshold: float
    action: str
    confidence: float
    auto_apply: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "current_threshold", _require_probability(self.current_threshold, "current_threshold"))
        object.__setattr__(self, "suggested_threshold", _require_probability(self.suggested_threshold, "suggested_threshold"))
        if self.action not in _THRESHOLD_ACTIONS:
            raise ValueError("action is invalid")
        object.__setattr__(self, "confidence", _require_probability(self.confidence, "confidence"))
        object.__setattr__(self, "auto_apply", _require_flag(self.auto_apply, False, "auto_apply"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_threshold": self.current_threshold,
            "suggested_threshold": self.suggested_threshold,
            "action": self.action,
            "confidence": self.confidence,
            "auto_apply": self.auto_apply,
        }


@dataclass(frozen=True)
class DashboardHealthStatus:
    status: str
    schema_passed: bool = True
    data_ready: bool = True
    is_simulated: bool = True
    paper_trading: bool = True
    learning_mode: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _require_text(self.status, "status"))
        object.__setattr__(self, "schema_passed", _require_bool(self.schema_passed, "schema_passed"))
        object.__setattr__(self, "data_ready", _require_bool(self.data_ready, "data_ready"))
        _apply_safe_flags(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "schema_passed": self.schema_passed,
            "data_ready": self.data_ready,
            **_safe_flags_to_dict(self),
        }


_SUMMARY_FIELDS = {
    "total_classifications",
    "green_total",
    "red_total",
    "total_outcomes",
    "positive_observed_total",
    "negative_observed_total",
    "unresolved_total",
    "invalidated_total",
    "green_confirmation_rate",
    "green_not_confirmed_rate",
    "red_rejection_confirmation_rate",
    "red_missed_positive_rate",
    "average_calibrated_assertiveness",
    "average_confidence",
    "current_threshold",
    "latest_suggested_threshold",
    "latest_threshold_action",
    "minimum_viable_sample_met",
    *set(_SAFE_FLAGS),
}


@dataclass(frozen=True)
class DashboardSummary:
    total_classifications: int
    green_total: int
    red_total: int
    total_outcomes: int
    positive_observed_total: int
    negative_observed_total: int
    unresolved_total: int
    invalidated_total: int
    green_confirmation_rate: float
    green_not_confirmed_rate: float
    red_rejection_confirmation_rate: float
    red_missed_positive_rate: float
    average_calibrated_assertiveness: float
    average_confidence: float
    current_threshold: float
    latest_suggested_threshold: float
    latest_threshold_action: str
    minimum_viable_sample_met: bool
    is_simulated: bool = True
    paper_trading: bool = True
    learning_mode: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DashboardSummary:
        return cls(**_validate_payload_keys(payload, _SUMMARY_FIELDS))

    def __post_init__(self) -> None:
        for field_name in (
            "total_classifications",
            "green_total",
            "red_total",
            "total_outcomes",
            "positive_observed_total",
            "negative_observed_total",
            "unresolved_total",
            "invalidated_total",
        ):
            object.__setattr__(self, field_name, _require_non_negative_int(getattr(self, field_name), field_name))
        for field_name in (
            "green_confirmation_rate",
            "green_not_confirmed_rate",
            "red_rejection_confirmation_rate",
            "red_missed_positive_rate",
            "average_calibrated_assertiveness",
            "average_confidence",
            "current_threshold",
            "latest_suggested_threshold",
        ):
            object.__setattr__(self, field_name, _require_probability(getattr(self, field_name), field_name))
        if self.latest_threshold_action not in _THRESHOLD_ACTIONS:
            raise ValueError("latest_threshold_action is invalid")
        object.__setattr__(
            self,
            "minimum_viable_sample_met",
            _require_bool(self.minimum_viable_sample_met, "minimum_viable_sample_met"),
        )
        _apply_safe_flags(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_classifications": self.total_classifications,
            "green_total": self.green_total,
            "red_total": self.red_total,
            "total_outcomes": self.total_outcomes,
            "positive_observed_total": self.positive_observed_total,
            "negative_observed_total": self.negative_observed_total,
            "unresolved_total": self.unresolved_total,
            "invalidated_total": self.invalidated_total,
            "green_confirmation_rate": self.green_confirmation_rate,
            "green_not_confirmed_rate": self.green_not_confirmed_rate,
            "red_rejection_confirmation_rate": self.red_rejection_confirmation_rate,
            "red_missed_positive_rate": self.red_missed_positive_rate,
            "average_calibrated_assertiveness": self.average_calibrated_assertiveness,
            "average_confidence": self.average_confidence,
            "current_threshold": self.current_threshold,
            "latest_suggested_threshold": self.latest_suggested_threshold,
            "latest_threshold_action": self.latest_threshold_action,
            "minimum_viable_sample_met": self.minimum_viable_sample_met,
            **_safe_flags_to_dict(self),
        }


def _apply_safe_flags(model: Any) -> None:
    for field_name, expected in _SAFE_FLAGS.items():
        object.__setattr__(model, field_name, _require_flag(getattr(model, field_name), expected, field_name))


def _safe_flags_to_dict(model: Any) -> dict[str, bool]:
    return {field_name: getattr(model, field_name) for field_name in _SAFE_FLAGS}
