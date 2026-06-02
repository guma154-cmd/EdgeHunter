"""Pure dashboard summary aggregation."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any
import unicodedata

from src.edgehunter.core.dashboard_read_models import DashboardSummary
from src.edgehunter.core.simulated_signal_calibration_report import (
    generate_simulated_signal_calibration_report,
)


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


def _reject_blocked_payload(payload: Mapping[str, Any], context: str) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{context} must be a mapping")
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError(f"{context} keys must be strings")
        if _has_blocked_term(key):
            raise ValueError(f"{context} contains forbidden field")
        _reject_blocked_value(value, context)


def _reject_blocked_value(value: Any, context: str) -> None:
    if isinstance(value, str) and _has_blocked_term(value):
        raise ValueError(f"{context} contains forbidden content")
    if isinstance(value, Mapping):
        _reject_blocked_payload(value, context)
    if isinstance(value, list | tuple):
        for item in value:
            _reject_blocked_value(item, context)


def _require_probability(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value) or not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _count_outcomes(outcomes: list[dict]) -> dict[str, int]:
    totals = {
        "positive_observed_total": 0,
        "negative_observed_total": 0,
        "unresolved_total": 0,
        "invalidated_total": 0,
    }
    for outcome in outcomes:
        _reject_blocked_payload(outcome, "outcome")
        status = outcome.get("outcome_status")
        if status == "POSITIVE_OBSERVED":
            totals["positive_observed_total"] += 1
        elif status == "NEGATIVE_OBSERVED":
            totals["negative_observed_total"] += 1
        elif status == "UNRESOLVED":
            totals["unresolved_total"] += 1
        elif status == "INVALIDATED":
            totals["invalidated_total"] += 1
        else:
            raise ValueError("outcome_status is invalid")
    return totals


def _safe_threshold_suggestion(
    threshold_suggestion: dict | None,
    current_threshold: float,
) -> tuple[float, str]:
    if threshold_suggestion is None:
        return current_threshold, "KEEP_THRESHOLD"

    _reject_blocked_payload(threshold_suggestion, "threshold_suggestion")
    if threshold_suggestion.get("auto_apply", False) is not False:
        raise ValueError("threshold_suggestion.auto_apply must be False")

    suggested_threshold = _require_probability(
        threshold_suggestion.get("suggested_threshold", current_threshold),
        "suggested_threshold",
    )
    action = str(threshold_suggestion.get("action", "KEEP_THRESHOLD")).strip()
    if action not in _THRESHOLD_ACTIONS:
        raise ValueError("threshold action is invalid")
    return suggested_threshold, action


def _calibration(
    classifications: list[dict],
    outcomes: list[dict],
    calibration_report: dict | None,
    current_threshold: float,
) -> dict[str, Any]:
    if calibration_report is None:
        return generate_simulated_signal_calibration_report(
            classifications,
            outcomes,
            threshold_green=current_threshold,
        )
    _reject_blocked_payload(calibration_report, "calibration_report")
    return calibration_report


def generate_dashboard_summary(
    classifications: list[dict],
    outcomes: list[dict],
    calibration_report: dict | None = None,
    threshold_suggestion: dict | None = None,
    *,
    current_threshold: float = 0.70,
) -> dict[str, Any]:
    if not isinstance(classifications, list):
        raise ValueError("classifications must be a list")
    if not isinstance(outcomes, list):
        raise ValueError("outcomes must be a list")
    current_threshold = _require_probability(current_threshold, "current_threshold")

    for classification in classifications:
        _reject_blocked_payload(classification, "classification")
    outcome_totals = _count_outcomes(outcomes)
    calibration = _calibration(
        classifications,
        outcomes,
        calibration_report,
        current_threshold,
    )
    latest_suggested_threshold, latest_threshold_action = _safe_threshold_suggestion(
        threshold_suggestion,
        current_threshold,
    )

    summary = DashboardSummary(
        total_classifications=len(classifications),
        green_total=int(calibration.get("green_total", 0)),
        red_total=int(calibration.get("red_total", 0)),
        total_outcomes=len(outcomes),
        positive_observed_total=outcome_totals["positive_observed_total"],
        negative_observed_total=outcome_totals["negative_observed_total"],
        unresolved_total=outcome_totals["unresolved_total"],
        invalidated_total=outcome_totals["invalidated_total"],
        green_confirmation_rate=float(calibration.get("green_confirmation_rate", 0.0)),
        green_not_confirmed_rate=float(calibration.get("green_not_confirmed_rate", 0.0)),
        red_rejection_confirmation_rate=float(
            calibration.get("red_rejection_confirmation_rate", 0.0)
        ),
        red_missed_positive_rate=float(calibration.get("red_missed_positive_rate", 0.0)),
        average_calibrated_assertiveness=float(
            calibration.get("average_calibrated_assertiveness", 0.0)
        ),
        average_confidence=float(calibration.get("average_confidence", 0.0)),
        current_threshold=current_threshold,
        latest_suggested_threshold=latest_suggested_threshold,
        latest_threshold_action=latest_threshold_action,
        minimum_viable_sample_met=bool(calibration.get("minimum_viable_sample_met", False)),
    )
    return summary.to_dict()
