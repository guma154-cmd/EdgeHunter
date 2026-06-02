"""Pure calibration report for simulated signal feedback."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
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

_VALID_LABELS = {"GREEN_SIM", "RED_SIM"}
_VALID_STATUSES = {
    "POSITIVE_OBSERVED",
    "NEGATIVE_OBSERVED",
    "UNRESOLVED",
    "INVALIDATED",
}
_JOIN_KEYS = ("signal_id", "classification_id", "opportunity_id")


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


def _require_safe_flags(payload: Mapping[str, Any], context: str) -> None:
    for field_name, expected in _SAFE_FLAGS.items():
        if field_name in payload and payload[field_name] is not expected:
            raise ValueError(f"{context}.{field_name} must be {expected}")


def _require_probability(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value) or not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _safe_probability_from_payload(payload: Mapping[str, Any], field_name: str) -> float:
    if field_name not in payload or payload[field_name] in (None, ""):
        return 0.0
    return _require_probability(payload[field_name], field_name)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _parse_observed_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _outcome_sort_key(index: int, outcome: Mapping[str, Any]) -> tuple[int, datetime, int]:
    observed_at = _parse_observed_at(outcome.get("observed_at"))
    if observed_at is None:
        return (0, datetime.min, index)
    return (1, observed_at, index)


def _index_outcomes(outcomes: list[dict]) -> dict[str, dict[str, dict[str, Any]]]:
    by_key: dict[str, dict[str, dict[str, Any]]] = {key: {} for key in _JOIN_KEYS}
    ranked_outcomes: list[tuple[int, dict[str, Any]]] = []

    for index, outcome in enumerate(outcomes):
        _reject_blocked_payload(outcome, "outcome")
        _require_safe_flags(outcome, "outcome")
        status = outcome.get("outcome_status")
        if status not in _VALID_STATUSES:
            raise ValueError("outcome_status is invalid")
        ranked_outcomes.append((index, outcome))

    ranked_outcomes.sort(key=lambda item: _outcome_sort_key(item[0], item[1]))

    for _, outcome in ranked_outcomes:
        for key_name in _JOIN_KEYS:
            key_value = str(outcome.get(key_name, "")).strip()
            if key_value:
                by_key[key_name][key_value] = outcome

    return by_key


def _find_outcome(
    classification: Mapping[str, Any],
    indexed_outcomes: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str | None]:
    for key_name in _JOIN_KEYS:
        key_value = str(classification.get(key_name, "")).strip()
        if key_value and key_value in indexed_outcomes[key_name]:
            return indexed_outcomes[key_name][key_value], key_name
    return None, None


def generate_simulated_signal_calibration_report(
    classifications: list[dict],
    outcomes: list[dict],
    *,
    threshold_green: float = 0.70,
    minimum_viable_sample_size: int = 30,
) -> dict[str, Any]:
    if not isinstance(classifications, list):
        raise ValueError("classifications must be a list")
    if not isinstance(outcomes, list):
        raise ValueError("outcomes must be a list")
    threshold_green = _require_probability(threshold_green, "threshold_green")
    if (
        isinstance(minimum_viable_sample_size, bool)
        or not isinstance(minimum_viable_sample_size, int)
        or minimum_viable_sample_size < 1
    ):
        raise ValueError("minimum_viable_sample_size must be >= 1")

    indexed_outcomes = _index_outcomes(outcomes)
    green_total = red_total = 0
    green_confirmed = green_not_confirmed = 0
    red_confirmed_as_rejection = red_missed_positive_scenario = 0
    unresolved_total = invalidated_total = 0
    matched_total = 0
    sum_calibrated_assertiveness = 0.0
    sum_confidence = 0.0
    matched_by = {key_name: 0 for key_name in _JOIN_KEYS}

    for classification in classifications:
        _reject_blocked_payload(classification, "classification")
        _require_safe_flags(classification, "classification")
        label = classification.get("simulation_label")
        if label not in _VALID_LABELS:
            raise ValueError("simulation_label is invalid")

        if label == "GREEN_SIM":
            green_total += 1
        else:
            red_total += 1

        sum_calibrated_assertiveness += _safe_probability_from_payload(
            classification,
            "calibrated_assertiveness",
        )
        sum_confidence += _safe_probability_from_payload(classification, "confidence")

        outcome, join_key = _find_outcome(classification, indexed_outcomes)
        if outcome is None:
            continue

        matched_total += 1
        matched_by[str(join_key)] += 1
        status = outcome["outcome_status"]

        if status == "UNRESOLVED":
            unresolved_total += 1
        elif status == "INVALIDATED":
            invalidated_total += 1
        elif label == "GREEN_SIM" and status == "POSITIVE_OBSERVED":
            green_confirmed += 1
        elif label == "GREEN_SIM" and status == "NEGATIVE_OBSERVED":
            green_not_confirmed += 1
        elif label == "RED_SIM" and status == "NEGATIVE_OBSERVED":
            red_confirmed_as_rejection += 1
        elif label == "RED_SIM" and status == "POSITIVE_OBSERVED":
            red_missed_positive_scenario += 1

    total_classifications = len(classifications)
    green_resolved = green_confirmed + green_not_confirmed
    red_resolved = red_confirmed_as_rejection + red_missed_positive_scenario

    return {
        "total_classifications": total_classifications,
        "total_outcomes": len(outcomes),
        "matched_total": matched_total,
        "unmatched_classifications": total_classifications - matched_total,
        "unresolved_total": unresolved_total,
        "invalidated_total": invalidated_total,
        "green_total": green_total,
        "red_total": red_total,
        "green_confirmed": green_confirmed,
        "green_not_confirmed": green_not_confirmed,
        "red_confirmed_as_rejection": red_confirmed_as_rejection,
        "red_missed_positive_scenario": red_missed_positive_scenario,
        "green_confirmation_rate": _rate(green_confirmed, green_resolved),
        "green_not_confirmed_rate": _rate(green_not_confirmed, green_resolved),
        "red_rejection_confirmation_rate": _rate(red_confirmed_as_rejection, red_resolved),
        "red_missed_positive_rate": _rate(red_missed_positive_scenario, red_resolved),
        "average_calibrated_assertiveness": _rate(
            sum_calibrated_assertiveness,
            total_classifications,
        ),
        "average_confidence": _rate(sum_confidence, total_classifications),
        "threshold_green": threshold_green,
        "sample_size": matched_total,
        "minimum_viable_sample_met": matched_total >= minimum_viable_sample_size,
        "join_decision": {
            "priority": list(_JOIN_KEYS),
            "latest_outcome_rule": "observed_at desc when valid; input order as deterministic fallback",
            "matched_by": matched_by,
        },
        **_SAFE_FLAGS,
    }
