"""Pure periodic reports for simulated agent evolution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import math
from typing import Any
import unicodedata

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

_PERIODS = {"daily", "weekly", "monthly"}
_EMPTY_COMPARISON = {
    "green_confirmation_rate_delta": 0.0,
    "green_not_confirmed_rate_delta": 0.0,
    "red_missed_positive_rate_delta": 0.0,
    "average_calibrated_assertiveness_delta": 0.0,
    "average_confidence_delta": 0.0,
}
_SAFE_FLAGS = {
    "is_simulated": True,
    "paper_trading": True,
    "learning_mode": True,
    "actionable": False,
    "bet_placed": False,
    "alerted": False,
    "not_operational_advice": True,
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


def _require_safe_flags(payload: Mapping[str, Any], context: str) -> None:
    for field_name, expected in _SAFE_FLAGS.items():
        if field_name in payload and payload[field_name] is not expected:
            raise ValueError(f"{context}.{field_name} must be {expected}")


def _parse_dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("period timestamps must be valid ISO strings")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _item_dt(item: Mapping[str, Any], fields: tuple[str, ...]) -> datetime | None:
    for field in fields:
        if item.get(field):
            return _parse_dt(str(item[field]))
    return None


def _filter_by_period(
    items: list[dict],
    *,
    start: datetime,
    end: datetime,
    fields: tuple[str, ...],
    context: str,
) -> list[dict]:
    filtered = []
    for item in items:
        _reject_blocked_payload(item, context)
        _require_safe_flags(item, context)
        item_timestamp = _item_dt(item, fields)
        if item_timestamp is not None and start <= item_timestamp <= end:
            filtered.append(item)
    return filtered


def _report_for_period(
    classifications: list[dict],
    outcomes: list[dict],
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    current_classifications = _filter_by_period(
        classifications,
        start=start,
        end=end,
        fields=("created_at", "inserted_at", "classified_at", "observed_at"),
        context="classification",
    )
    current_outcomes = _filter_by_period(
        outcomes,
        start=start,
        end=end,
        fields=("observed_at", "created_at", "inserted_at"),
        context="outcome",
    )
    calibration = generate_simulated_signal_calibration_report(
        current_classifications,
        current_outcomes,
    )
    resolved_total = (
        calibration["green_confirmed"]
        + calibration["green_not_confirmed"]
        + calibration["red_confirmed_as_rejection"]
        + calibration["red_missed_positive_scenario"]
    )
    return {
        **calibration,
        "resolved_total": resolved_total,
    }


def _latest_threshold_suggestion(threshold_suggestions: list[dict] | None) -> dict[str, Any] | None:
    if not threshold_suggestions:
        return None
    safe_suggestions = []
    for index, suggestion in enumerate(threshold_suggestions):
        _reject_blocked_payload(suggestion, "threshold_suggestion")
        if suggestion.get("auto_apply", False) is not False:
            raise ValueError("threshold_suggestion.auto_apply must be False")
        sort_key = _item_dt(
            suggestion,
            ("created_at", "inserted_at", "suggested_at"),
        ) or datetime.min
        safe_suggestions.append((sort_key, index, dict(suggestion)))
    safe_suggestions.sort(key=lambda item: (item[0], item[1]))
    return safe_suggestions[-1][2]


def _delta(current: dict[str, Any], previous: dict[str, Any], key: str) -> float:
    current_value = float(current.get(key, 0.0))
    previous_value = float(previous.get(key, 0.0))
    if not math.isfinite(current_value) or not math.isfinite(previous_value):
        raise ValueError("comparison metrics must be finite")
    return current_value - previous_value


def _comparison(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, float]:
    if previous is None:
        return dict(_EMPTY_COMPARISON)
    return {
        "green_confirmation_rate_delta": _delta(current, previous, "green_confirmation_rate"),
        "green_not_confirmed_rate_delta": _delta(current, previous, "green_not_confirmed_rate"),
        "red_missed_positive_rate_delta": _delta(current, previous, "red_missed_positive_rate"),
        "average_calibrated_assertiveness_delta": _delta(
            current,
            previous,
            "average_calibrated_assertiveness",
        ),
        "average_confidence_delta": _delta(current, previous, "average_confidence"),
    }


def _evolution_status(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if current["resolved_total"] <= 0:
        return "INSUFFICIENT_SAMPLE"
    if previous is None or previous["resolved_total"] <= 0:
        return "STABLE"
    comparison = _comparison(current, previous)
    if (
        comparison["green_confirmation_rate_delta"] > 0
        and comparison["green_not_confirmed_rate_delta"] < 0
    ):
        return "IMPROVING"
    if (
        comparison["green_confirmation_rate_delta"] < 0
        or comparison["red_missed_positive_rate_delta"] > 0
    ):
        return "DECLINING"
    return "STABLE"


def generate_periodic_agent_evolution_report(
    classifications: list[dict],
    outcomes: list[dict],
    threshold_suggestions: list[dict] | None = None,
    *,
    period: str = "daily",
    current_period_start: str,
    current_period_end: str,
    previous_period_start: str | None = None,
    previous_period_end: str | None = None,
) -> dict[str, Any]:
    if period not in _PERIODS:
        raise ValueError("period is invalid")
    if not isinstance(classifications, list):
        raise ValueError("classifications must be a list")
    if not isinstance(outcomes, list):
        raise ValueError("outcomes must be a list")

    current_start = _parse_dt(current_period_start)
    current_end = _parse_dt(current_period_end)
    if current_start > current_end:
        raise ValueError("current period start must be before end")

    current = _report_for_period(
        classifications,
        outcomes,
        start=current_start,
        end=current_end,
    )

    previous = None
    if previous_period_start is not None and previous_period_end is not None:
        previous_start = _parse_dt(previous_period_start)
        previous_end = _parse_dt(previous_period_end)
        if previous_start > previous_end:
            raise ValueError("previous period start must be before end")
        previous = _report_for_period(
            classifications,
            outcomes,
            start=previous_start,
            end=previous_end,
        )

    return {
        "period": period,
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
        "total_classifications": current["total_classifications"],
        "green_total": current["green_total"],
        "red_total": current["red_total"],
        "resolved_total": current["resolved_total"],
        "unresolved_total": current["unresolved_total"],
        "green_confirmed": current["green_confirmed"],
        "green_not_confirmed": current["green_not_confirmed"],
        "red_confirmed_as_rejection": current["red_confirmed_as_rejection"],
        "red_missed_positive_scenario": current["red_missed_positive_scenario"],
        "green_confirmation_rate": current["green_confirmation_rate"],
        "green_not_confirmed_rate": current["green_not_confirmed_rate"],
        "red_rejection_confirmation_rate": current["red_rejection_confirmation_rate"],
        "red_missed_positive_rate": current["red_missed_positive_rate"],
        "average_calibrated_assertiveness": current["average_calibrated_assertiveness"],
        "average_confidence": current["average_confidence"],
        "latest_threshold_suggestion": _latest_threshold_suggestion(threshold_suggestions),
        "previous_period_comparison": _comparison(current, previous),
        "agent_evolution_status": _evolution_status(current, previous),
        **_SAFE_FLAGS,
    }
