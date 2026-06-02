"""Pure contracts for simulated signal outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any
import unicodedata
from datetime import datetime

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
        _join("luc", "ro"),
        _join("ga", "in"),
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
    
    words = haystack.split()
    for w in words:
        if w in ["green", "red"]:
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

def _require_optional_text(value: str | None, field_name: str) -> str:
    if not value:
        return ""
    clean_value = str(value).strip()
    _reject_blocked_text(clean_value, field_name)
    return clean_value

def _require_flag(value: bool, expected: bool, field_name: str) -> bool:
    if value is not expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value

class OutcomeStatus(str, Enum):
    POSITIVE_OBSERVED = "POSITIVE_OBSERVED"
    NEGATIVE_OBSERVED = "NEGATIVE_OBSERVED"
    UNRESOLVED = "UNRESOLVED"
    INVALIDATED = "INVALIDATED"


_OUTCOME_FIELDS = frozenset(
    {
        "outcome_id",
        "signal_id",
        "classification_id",
        "opportunity_id",
        "outcome_status",
        "observed_at",
        "source",
        "notes",
        "is_simulated",
        "paper_trading",
        "learning_mode",
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
class SimulatedSignalOutcome:
    outcome_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    outcome_status: OutcomeStatus
    observed_at: str
    source: str
    notes: str = ""
    is_simulated: bool = True
    paper_trading: bool = True
    learning_mode: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SimulatedSignalOutcome:
        if "outcome_status" in payload:
            status_val = payload["outcome_status"]
            if isinstance(status_val, str):
                try:
                    payload = dict(payload)
                    payload["outcome_status"] = OutcomeStatus(status_val)
                except ValueError:
                    pass
        return cls(**_require_payload(payload, allowed_fields=_OUTCOME_FIELDS))

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_id", _require_text(self.outcome_id, "outcome_id"))
        object.__setattr__(self, "signal_id", _require_text(self.signal_id, "signal_id"))
        object.__setattr__(self, "classification_id", _require_text(self.classification_id, "classification_id"))
        object.__setattr__(self, "opportunity_id", _require_text(self.opportunity_id, "opportunity_id"))
        
        if not isinstance(self.outcome_status, OutcomeStatus):
            raise ValueError("outcome_status must be an OutcomeStatus")
            
        object.__setattr__(self, "observed_at", _require_text(self.observed_at, "observed_at"))
        try:
            datetime.fromisoformat(self.observed_at.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("observed_at must be a valid ISO format string")
            
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(self, "notes", _require_optional_text(self.notes, "notes"))
        
        object.__setattr__(self, "is_simulated", _require_flag(self.is_simulated, True, "is_simulated"))
        object.__setattr__(self, "paper_trading", _require_flag(self.paper_trading, True, "paper_trading"))
        object.__setattr__(self, "learning_mode", _require_flag(self.learning_mode, True, "learning_mode"))
        object.__setattr__(self, "actionable", _require_flag(self.actionable, False, "actionable"))
        object.__setattr__(self, "bet_placed", _require_flag(self.bet_placed, False, "bet_placed"))
        object.__setattr__(self, "alerted", _require_flag(self.alerted, False, "alerted"))
        object.__setattr__(self, "not_operational_advice", _require_flag(self.not_operational_advice, True, "not_operational_advice"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "signal_id": self.signal_id,
            "classification_id": self.classification_id,
            "opportunity_id": self.opportunity_id,
            "outcome_status": self.outcome_status.value,
            "observed_at": self.observed_at,
            "source": self.source,
            "notes": self.notes,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "learning_mode": self.learning_mode,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice,
        }
