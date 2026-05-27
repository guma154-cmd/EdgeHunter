"""Pure value calculation primitives for PRD-03."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


MIN_OFFERED_ODDS = 1.01


def calculate_ev(true_prob: float, offered_odds: float) -> float:
    true_prob_clean = float(true_prob)
    offered_odds_clean = float(offered_odds)

    if not math.isfinite(true_prob_clean):
        raise ValueError("true_prob must be finite")
    if not 0.0 <= true_prob_clean <= 1.0:
        raise ValueError("true_prob must be between 0 and 1")
    if not math.isfinite(offered_odds_clean):
        raise ValueError("offered_odds must be finite")
    if offered_odds_clean < MIN_OFFERED_ODDS:
        raise ValueError("offered_odds must be >= 1.01")

    ev = (true_prob_clean * offered_odds_clean) - 1.0
    if not math.isfinite(ev):
        raise ValueError("expected value must be finite")
    return ev


def _require_text(value: str, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    return clean_value


def _require_finite_float(value: float, field_name: str) -> float:
    clean_value = float(value)
    if not math.isfinite(clean_value):
        raise ValueError(f"{field_name} must be finite")
    return clean_value


def _normalize_probability(true_probability: float) -> float:
    clean_probability = _require_finite_float(true_probability, "true_probability")
    if not 0.0 <= clean_probability <= 1.0:
        raise ValueError("true_probability must be between 0 and 1")
    return clean_probability


def _normalize_offered_odds(offered_odds: float) -> float:
    clean_odds = _require_finite_float(offered_odds, "offered_odds")
    if clean_odds < MIN_OFFERED_ODDS:
        raise ValueError("offered_odds must be >= 1.01")
    return clean_odds


def _stable_number(value: float) -> str:
    return format(value, ".15g")


def build_simulated_opportunity_id(
    *,
    match_id: str,
    market: str,
    selection: str,
    source: str,
    detection_method: str,
    offered_odds: float,
    true_probability: float,
) -> str:
    payload = {
        "detection_method": _require_text(detection_method, "detection_method"),
        "market": _require_text(market, "market"),
        "match_id": _require_text(match_id, "match_id"),
        "offered_odds": _stable_number(_normalize_offered_odds(offered_odds)),
        "selection": _require_text(selection, "selection"),
        "source": _require_text(source, "source"),
        "true_probability": _stable_number(_normalize_probability(true_probability)),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sim-{hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SimulatedValueOpportunity:
    match_id: str
    market: str
    selection: str
    true_probability: float
    offered_odds: float
    expected_value: float
    edge_percentage: float
    source: str
    detection_method: str
    opportunity_id: str | None = None
    created_at: str | None = None
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False

    def __post_init__(self) -> None:
        match_id = _require_text(self.match_id, "match_id")
        market = _require_text(self.market, "market")
        selection = _require_text(self.selection, "selection")
        source = _require_text(self.source, "source")
        detection_method = _require_text(self.detection_method, "detection_method")
        true_probability = _normalize_probability(self.true_probability)
        offered_odds = _normalize_offered_odds(self.offered_odds)
        expected_value = _require_finite_float(self.expected_value, "expected_value")
        edge_percentage = _require_finite_float(self.edge_percentage, "edge_percentage")

        if self.is_simulated is not True:
            raise ValueError("is_simulated must be True")
        if self.paper_trading is not True:
            raise ValueError("paper_trading must be True")
        if self.actionable is not False:
            raise ValueError("actionable must be False")
        if self.bet_placed is not False:
            raise ValueError("bet_placed must be False")
        if self.alerted is not False:
            raise ValueError("alerted must be False")

        opportunity_id = (
            _require_text(self.opportunity_id, "opportunity_id")
            if self.opportunity_id is not None
            else build_simulated_opportunity_id(
                match_id=match_id,
                market=market,
                selection=selection,
                source=source,
                detection_method=detection_method,
                offered_odds=offered_odds,
                true_probability=true_probability,
            )
        )
        created_at = (
            _require_text(self.created_at, "created_at")
            if self.created_at is not None
            else _utc_now_iso()
        )

        object.__setattr__(self, "match_id", match_id)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "selection", selection)
        object.__setattr__(self, "true_probability", true_probability)
        object.__setattr__(self, "offered_odds", offered_odds)
        object.__setattr__(self, "expected_value", expected_value)
        object.__setattr__(self, "edge_percentage", edge_percentage)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "detection_method", detection_method)
        object.__setattr__(self, "opportunity_id", opportunity_id)
        object.__setattr__(self, "created_at", created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "match_id": self.match_id,
            "market": self.market,
            "selection": self.selection,
            "true_probability": self.true_probability,
            "offered_odds": self.offered_odds,
            "expected_value": self.expected_value,
            "edge_percentage": self.edge_percentage,
            "source": self.source,
            "detection_method": self.detection_method,
            "created_at": self.created_at,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
        }
