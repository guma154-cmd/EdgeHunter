"""Local sanity checks for the simulated ValueDetector pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import inspect
import sqlite3
import tempfile
from typing import Any

from . import value_detector as detection_module
from . import value_detector_persistence as persistence_module
from .value_detector import (
    SimulatedValueOpportunity,
    calculate_ev,
    deduplicate_opportunities,
    detect_value_consensus,
    detect_value_vs_pinnacle,
    detect_value_vs_poisson,
)
from .value_detector_persistence import persist_simulated_opportunities


@dataclass(frozen=True)
class ValueDetectorSanityResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class _FakeSanityResult:
    passed: bool


class _FakeModel:
    def __init__(
        self,
        *,
        trained: bool = True,
        sanity_passed: bool = True,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        self.trained = trained
        self.sanity_passed = sanity_passed
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.25,
            "away_win": 0.15,
        }

    def sanity_check(self) -> _FakeSanityResult:
        return _FakeSanityResult(passed=self.sanity_passed)

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.6,
            "expected_away_goals": 1.0,
            "used_fallback": False,
        }

    def predict_probabilities(self, *, home_team: str, away_team: str) -> dict[str, float]:
        return self.probabilities


def _snapshot(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "snapshot_id": 1,
        "match_id": "match-001",
        "home_team": "Flamengo",
        "away_team": "Palmeiras",
        "league": "Brasileirao",
        "valid_for_analysis": True,
        "odds": {
            "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
            "bet365": {"home": 2.2, "draw": 3.1, "away": 3.0},
        },
    }
    data.update(overrides)
    return data


def _opportunity(**overrides: object) -> SimulatedValueOpportunity:
    # created_at must be within the deduplication window (now - 60min, now)
    # so that deduplicate_opportunities([opp, opp]) correctly removes the duplicate.
    # Using a fixed past timestamp would place the opportunity outside the window,
    # causing both copies to pass through (correct historical behaviour, wrong for sanity).
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home_win",
        "true_probability": 0.60,
        "offered_odds": 2.00,
        "expected_value": 0.20,
        "edge_percentage": 20.0,
        "source": "consensus",
        "detection_method": "consensus_pinnacle_poisson_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data.update(overrides)
    return SimulatedValueOpportunity(**data)


def _record_check(
    condition: bool,
    reason: str,
    reasons: list[str],
    metrics: dict[str, Any],
    metric_name: str,
) -> None:
    metrics[metric_name] = bool(condition)
    if not condition:
        reasons.append(reason)


def _persisted_safety_flags(db_path: str) -> dict[str, int]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT is_simulated, paper_trading, actionable, bet_placed, alerted
            FROM value_detections
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {}
        return {key: int(row[key]) for key in row.keys()}
    finally:
        connection.close()


def _check_persistence_flags(db_path: str) -> bool:
    opportunity = _opportunity()
    inserted = persist_simulated_opportunities(db_path, [opportunity])
    flags = _persisted_safety_flags(db_path)
    return inserted == 1 and flags == {
        "is_simulated": 1,
        "paper_trading": 1,
        "actionable": 0,
        "bet_placed": 0,
        "alerted": 0,
    }


def _guardrails_pass() -> bool:
    combined_source = "\n".join(
        (
            inspect.getsource(detection_module),
            inspect.getsource(persistence_module),
        )
    ).lower()
    forbidden_terms = (
        "sta" + "ke",
        "kel" + "ly",
        "bank" + "roll",
        "tele" + "gram",
        "sched" + "uler",
        "requ" + "ests",
        "ht" + "tpx",
        "url" + "lib",
        "sock" + "et",
        "place_" + "bet",
        "execute_" + "bet",
        "real_" + "money",
    )
    return not any(term in combined_source for term in forbidden_terms)


def sanity_check_value_detector(db_path: str | None = None) -> ValueDetectorSanityResult:
    reasons: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    _record_check(
        calculate_ev(0.6, 2.0) == 0.19999999999999996,
        "calculate_ev_known_case_failed",
        reasons,
        metrics,
        "ev_known_case",
    )

    opportunity = _opportunity()
    _record_check(
        opportunity.is_simulated is True
        and opportunity.paper_trading is True
        and opportunity.actionable is False
        and opportunity.bet_placed is False
        and opportunity.alerted is False,
        "simulated_opportunity_safety_flags_failed",
        reasons,
        metrics,
        "opportunity_safety_flags",
    )

    _record_check(
        detect_value_vs_pinnacle(_snapshot(valid_for_analysis=False), "bet365") == [],
        "invalid_snapshot_generated_pinnacle_opportunity",
        reasons,
        metrics,
        "pinnacle_invalid_snapshot_skip",
    )

    _record_check(
        detect_value_vs_poisson(_snapshot(), _FakeModel(trained=False), "bet365") == []
        and detect_value_vs_poisson(_snapshot(), _FakeModel(sanity_passed=False), "bet365") == [],
        "poisson_unready_model_generated_opportunity",
        reasons,
        metrics,
        "poisson_unready_model_skip",
    )

    divergent_consensus = detect_value_consensus(
        _snapshot(),
        _FakeModel(probabilities={"home_win": 0.40, "draw": 0.20, "away_win": 0.40}),
        "bet365",
    )
    _record_check(
        divergent_consensus == [],
        "divergent_consensus_generated_opportunity",
        reasons,
        metrics,
        "consensus_divergence_skip",
    )

    deduped = deduplicate_opportunities([opportunity, opportunity])
    _record_check(
        deduped == [opportunity],
        "logical_deduplication_failed",
        reasons,
        metrics,
        "deduplication_removes_duplicate",
    )

    if db_path is None:
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence_passed = _check_persistence_flags(
                str(Path(temp_dir) / "edgehunter-sanity.db")
            )
    else:
        persistence_passed = _check_persistence_flags(db_path)
    _record_check(
        persistence_passed,
        "persistence_safety_flags_failed",
        reasons,
        metrics,
        "persistence_safety_flags",
    )

    _record_check(
        _guardrails_pass(),
        "operational_guardrails_failed",
        reasons,
        metrics,
        "operational_guardrails",
    )

    if db_path is None:
        warnings.append("persistence_checked_with_temporary_sqlite")

    return ValueDetectorSanityResult(
        passed=not reasons,
        reasons=reasons,
        warnings=warnings,
        metrics=metrics,
    )
