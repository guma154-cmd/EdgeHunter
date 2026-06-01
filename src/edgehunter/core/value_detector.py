"""Pure value calculation primitives for PRD-03."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from collections.abc import Iterable
from typing import Any


MIN_OFFERED_ODDS = 1.01
PROBABILITY_SUM_TOLERANCE = 1e-6
PINNACLE_SOURCE = "pinnacle_benchmark"
PINNACLE_DETECTION_METHOD = "pinnacle_ev_v2"
POISSON_SOURCE = "poisson_model"
POISSON_DETECTION_METHOD = "poisson_ev_v1"
CONSENSUS_SOURCE = "consensus"
CONSENSUS_DETECTION_METHOD = "consensus_pinnacle_poisson_v1"
SELECTION_BY_ODDS_KEY: dict[str, str] = {
    "home": "home_win",
    "draw": "draw",
    "away": "away_win",
}
ODDS_KEY_BY_SELECTION: dict[str, str] = {
    selection: odds_key for odds_key, selection in SELECTION_BY_ODDS_KEY.items()
}


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


def _normalize_min_ev(min_ev: float) -> float:
    clean_min_ev = _require_finite_float(min_ev, "min_ev")
    if clean_min_ev < 0.0:
        raise ValueError("min_ev must be >= 0")
    return clean_min_ev


def _stable_number(value: float) -> str:
    return format(value, ".15g")


def _snapshot_odds(snapshot: dict[str, Any], bookmaker: str) -> dict[str, Any] | None:
    odds = snapshot.get("odds")
    if not isinstance(odds, dict):
        return None
    bookmaker_odds = odds.get(bookmaker)
    if not isinstance(bookmaker_odds, dict):
        return None
    return bookmaker_odds


ODDS_KEYS_1X2 = ("home", "draw", "away")


def calculate_normalized_implied_probabilities(
    odds: dict[str, float],
) -> dict[str, float]:
    """Remove Pinnacle overround and return normalized implied probabilities for 1X2.

    Formula (proportional margin removal):
        raw_prob   = 1 / odd              for each of home, draw, away
        overround  = sum(raw_probs)
        norm_prob  = raw_prob / overround for each selection

    The returned probabilities sum to approximately 1.0.

    Args:
        odds: dict with keys 'home', 'draw', 'away' mapping to Pinnacle decimal odds.

    Returns:
        dict with keys 'home', 'draw', 'away' mapping to normalized probabilities.

    Raises:
        ValueError: if any key is missing, any odd is invalid (<1.01, NaN, inf),
                    or if the overround is not finite / <= 0.
    """
    raw: dict[str, float] = {}
    for key in ODDS_KEYS_1X2:
        if key not in odds:
            raise ValueError(f"odds missing required key: '{key}'")
        odd = _normalize_offered_odds(float(odds[key]))
        raw[key] = 1.0 / odd

    overround = sum(raw.values())
    if not math.isfinite(overround) or overround <= 0.0:
        raise ValueError(f"overround must be finite and positive, got {overround}")

    return {key: raw[key] / overround for key in ODDS_KEYS_1X2}


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


def _ensure_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        created_at = value
    else:
        created_at = datetime.fromisoformat(str(value))
    return _ensure_aware_datetime(created_at, "created_at")


def detect_value_vs_pinnacle(
    snapshot: dict[str, Any],
    target_bookmaker: str,
    market: str = "1x2",
    min_ev: float = 0.0,
) -> list[SimulatedValueOpportunity]:
    clean_min_ev = _normalize_min_ev(min_ev)
    match_id = _require_text(str(snapshot.get("match_id", "")), "match_id")
    target_bookmaker_clean = _require_text(target_bookmaker, "target_bookmaker")
    market_clean = _require_text(market, "market")

    if snapshot.get("valid_for_analysis") is not True:
        return []

    pinnacle_odds = _snapshot_odds(snapshot, "pinnacle")
    target_odds = _snapshot_odds(snapshot, target_bookmaker_clean)
    if pinnacle_odds is None or target_odds is None:
        return []

    # v2: remove Pinnacle overround before computing true probabilities.
    # Requires all three keys (home, draw, away) present and valid in pinnacle_odds;
    # raises ValueError for missing keys, invalid odds (< 1.01, NaN, inf).
    normalized_probs = calculate_normalized_implied_probabilities(
        {k: pinnacle_odds[k] for k in ODDS_KEYS_1X2 if k in pinnacle_odds}
    )

    opportunities: list[SimulatedValueOpportunity] = []
    for odds_key, selection in SELECTION_BY_ODDS_KEY.items():
        if odds_key not in normalized_probs or odds_key not in target_odds:
            continue

        true_probability = normalized_probs[odds_key]
        offered_odd = _normalize_offered_odds(target_odds[odds_key])
        expected_value = calculate_ev(true_probability, offered_odd)
        if expected_value < clean_min_ev:
            continue

        opportunities.append(
            SimulatedValueOpportunity(
                match_id=match_id,
                market=market_clean,
                selection=selection,
                true_probability=true_probability,
                offered_odds=offered_odd,
                expected_value=expected_value,
                edge_percentage=expected_value * 100.0,
                source=PINNACLE_SOURCE,
                detection_method=PINNACLE_DETECTION_METHOD,
            )
        )

    return opportunities


def _model_sanity_passed(model: Any) -> bool:
    sanity_check = getattr(model, "sanity_check", None)
    if not callable(sanity_check):
        return False
    sanity_result = sanity_check()
    return getattr(sanity_result, "passed", False) is True


def _prediction_used_fallback(
    model: Any,
    *,
    home_team: str,
    away_team: str,
) -> bool:
    predict_match = getattr(model, "predict_match", None)
    if not callable(predict_match):
        return True
    prediction = predict_match(home_team=home_team, away_team=away_team)
    if not isinstance(prediction, dict):
        return True
    return prediction.get("used_fallback") is True


def _model_probabilities(
    model: Any,
    *,
    home_team: str,
    away_team: str,
) -> dict[str, Any]:
    predict_probabilities = getattr(model, "predict_probabilities", None)
    if not callable(predict_probabilities):
        return {}
    probabilities = predict_probabilities(home_team=home_team, away_team=away_team)
    if not isinstance(probabilities, dict):
        return {}
    return probabilities


def _normalize_model_probability_vector(
    probabilities: dict[str, Any],
) -> dict[str, float]:
    required_selections = tuple(ODDS_KEY_BY_SELECTION)
    if not all(selection in probabilities for selection in required_selections):
        return {}

    normalized = {
        selection: _normalize_probability(probabilities[selection])
        for selection in required_selections
    }
    probability_sum = sum(normalized.values())
    if abs(probability_sum - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ValueError("model probabilities must sum to 1")
    return normalized


def detect_value_vs_poisson(
    snapshot: dict[str, Any],
    poisson_model: Any,
    target_bookmaker: str,
    market: str = "1x2",
    min_ev: float = 0.0,
    require_sanity: bool = True,
) -> list[SimulatedValueOpportunity]:
    clean_min_ev = _normalize_min_ev(min_ev)
    match_id = _require_text(str(snapshot.get("match_id", "")), "match_id")
    home_team = _require_text(str(snapshot.get("home_team", "")), "home_team")
    away_team = _require_text(str(snapshot.get("away_team", "")), "away_team")
    target_bookmaker_clean = _require_text(target_bookmaker, "target_bookmaker")
    market_clean = _require_text(market, "market")

    if snapshot.get("valid_for_analysis") is not True:
        return []
    if getattr(poisson_model, "trained", False) is not True:
        return []
    if require_sanity and not _model_sanity_passed(poisson_model):
        return []
    if _prediction_used_fallback(
        poisson_model,
        home_team=home_team,
        away_team=away_team,
    ):
        return []

    target_odds = _snapshot_odds(snapshot, target_bookmaker_clean)
    if target_odds is None:
        return []

    probabilities = _model_probabilities(
        poisson_model,
        home_team=home_team,
        away_team=away_team,
    )
    normalized_probabilities = _normalize_model_probability_vector(probabilities)
    if not normalized_probabilities:
        return []

    opportunities: list[SimulatedValueOpportunity] = []
    for selection, odds_key in ODDS_KEY_BY_SELECTION.items():
        if odds_key not in target_odds:
            continue

        true_probability = normalized_probabilities[selection]
        offered_odd = _normalize_offered_odds(target_odds[odds_key])
        expected_value = calculate_ev(true_probability, offered_odd)
        if expected_value < clean_min_ev:
            continue

        opportunities.append(
            SimulatedValueOpportunity(
                match_id=match_id,
                market=market_clean,
                selection=selection,
                true_probability=true_probability,
                offered_odds=offered_odd,
                expected_value=expected_value,
                edge_percentage=expected_value * 100.0,
                source=POISSON_SOURCE,
                detection_method=POISSON_DETECTION_METHOD,
            )
        )

    return opportunities


def _opportunity_key(opportunity: SimulatedValueOpportunity) -> tuple[str, str, str]:
    return (
        opportunity.match_id,
        opportunity.market,
        opportunity.selection,
    )


def detect_value_consensus(
    snapshot: dict[str, Any],
    poisson_model: Any,
    target_bookmaker: str,
    market: str = "1x2",
    min_ev: float = 0.0,
    require_sanity: bool = True,
) -> list[SimulatedValueOpportunity]:
    pinnacle_opportunities = detect_value_vs_pinnacle(
        snapshot=snapshot,
        target_bookmaker=target_bookmaker,
        market=market,
        min_ev=min_ev,
    )
    poisson_opportunities = detect_value_vs_poisson(
        snapshot=snapshot,
        poisson_model=poisson_model,
        target_bookmaker=target_bookmaker,
        market=market,
        min_ev=min_ev,
        require_sanity=require_sanity,
    )

    poisson_by_key = {
        _opportunity_key(opportunity): opportunity
        for opportunity in poisson_opportunities
    }

    consensus_opportunities: list[SimulatedValueOpportunity] = []
    for pinnacle_opportunity in pinnacle_opportunities:
        poisson_opportunity = poisson_by_key.get(_opportunity_key(pinnacle_opportunity))
        if poisson_opportunity is None:
            continue

        conservative_source = min(
            (pinnacle_opportunity, poisson_opportunity),
            key=lambda opportunity: opportunity.expected_value,
        )
        conservative_ev = min(
            pinnacle_opportunity.expected_value,
            poisson_opportunity.expected_value,
        )
        conservative_edge = min(
            pinnacle_opportunity.edge_percentage,
            poisson_opportunity.edge_percentage,
        )

        consensus_opportunities.append(
            SimulatedValueOpportunity(
                match_id=pinnacle_opportunity.match_id,
                market=pinnacle_opportunity.market,
                selection=pinnacle_opportunity.selection,
                true_probability=conservative_source.true_probability,
                offered_odds=conservative_source.offered_odds,
                expected_value=conservative_ev,
                edge_percentage=conservative_edge,
                source=CONSENSUS_SOURCE,
                detection_method=CONSENSUS_DETECTION_METHOD,
            )
        )

    return consensus_opportunities


def _deduplication_payload(
    opportunity: SimulatedValueOpportunity | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(opportunity, SimulatedValueOpportunity):
        return opportunity.to_dict()
    if isinstance(opportunity, dict):
        return opportunity
    raise ValueError("opportunity must be a SimulatedValueOpportunity or dict")


def _deduplication_key(
    opportunity: SimulatedValueOpportunity | dict[str, Any],
) -> tuple[str, str, str, str, str]:
    payload = _deduplication_payload(opportunity)
    return (
        _require_text(str(payload.get("match_id", "")), "match_id"),
        _require_text(str(payload.get("market", "")), "market"),
        _require_text(str(payload.get("selection", "")), "selection"),
        _require_text(str(payload.get("source", "")), "source"),
        _require_text(str(payload.get("detection_method", "")), "detection_method"),
    )


def _validate_safe_opportunity(opportunity: SimulatedValueOpportunity) -> None:
    if opportunity.is_simulated is not True:
        raise ValueError("opportunity must be simulated")
    if opportunity.paper_trading is not True:
        raise ValueError("opportunity must be paper trading")
    if opportunity.actionable is not False:
        raise ValueError("opportunity must not be actionable")
    if opportunity.bet_placed is not False:
        raise ValueError("opportunity must not be placed")
    if opportunity.alerted is not False:
        raise ValueError("opportunity must not be alerted")


def _created_at_for_deduplication(
    opportunity: SimulatedValueOpportunity | dict[str, Any],
) -> datetime:
    payload = _deduplication_payload(opportunity)
    return _parse_created_at(payload.get("created_at"))


def deduplicate_opportunities(
    opportunities: list[SimulatedValueOpportunity],
    seen: Iterable[SimulatedValueOpportunity | dict[str, Any]] | None = None,
    window_minutes: int = 60,
    now: datetime | None = None,
) -> list[SimulatedValueOpportunity]:
    if window_minutes <= 0:
        raise ValueError("window_minutes must be > 0")

    reference_time = (
        datetime.now(timezone.utc)
        if now is None
        else _ensure_aware_datetime(now, "now")
    )
    window_start = reference_time - timedelta(minutes=window_minutes)

    blocked_keys: set[tuple[str, str, str, str, str]] = set()
    if seen is not None:
        for seen_opportunity in seen:
            if _created_at_for_deduplication(seen_opportunity) >= window_start:
                blocked_keys.add(_deduplication_key(seen_opportunity))

    results: list[SimulatedValueOpportunity] = []
    current_window_keys: set[tuple[str, str, str, str, str]] = set()
    for opportunity in opportunities:
        _validate_safe_opportunity(opportunity)
        opportunity_created_at = _created_at_for_deduplication(opportunity)
        key = _deduplication_key(opportunity)
        if opportunity_created_at < window_start:
            results.append(opportunity)
            continue
        if key in blocked_keys or key in current_window_keys:
            continue
        current_window_keys.add(key)
        results.append(opportunity)

    return results


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
