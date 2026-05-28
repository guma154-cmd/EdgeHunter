"""Adversarial tests for STORY-03-010 ValueDetector hardening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import inspect
import math
import sqlite3

import pytest

from src.edgehunter.core import value_detector as value_detector_module
from src.edgehunter.core import value_detector_persistence as persistence_module
from src.edgehunter.core.value_detector import (
    SimulatedValueOpportunity,
    calculate_ev,
    deduplicate_opportunities,
    detect_value_consensus,
    detect_value_vs_pinnacle,
    detect_value_vs_poisson,
)
from src.edgehunter.core.value_detector_persistence import persist_simulated_opportunities


NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class FakeSanityResult:
    passed: bool


class FakeModel:
    def __init__(
        self,
        *,
        trained: bool = True,
        sanity_passed: bool = True,
        used_fallback: bool = False,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        self.trained = trained
        self.sanity_passed = sanity_passed
        self.used_fallback = used_fallback
        self.probabilities = probabilities or {
            "home_win": 0.60,
            "draw": 0.25,
            "away_win": 0.15,
        }

    def sanity_check(self) -> FakeSanityResult:
        return FakeSanityResult(passed=self.sanity_passed)

    def predict_match(self, *, home_team: str, away_team: str) -> dict[str, object]:
        return {
            **self.probabilities,
            "expected_home_goals": 1.6,
            "expected_away_goals": 1.0,
            "used_fallback": self.used_fallback,
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
            "bet365": {"home": 2.2, "draw": 3.1, "away": 4.5},
        },
    }
    data.update(overrides)
    return data


def _opportunity(**overrides: object) -> SimulatedValueOpportunity:
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
        "created_at": (NOW - timedelta(minutes=5)).isoformat(),
    }
    data.update(overrides)
    return SimulatedValueOpportunity(**data)


def _unsafe_opportunity(**overrides: object) -> SimulatedValueOpportunity:
    opportunity = _opportunity()
    for field_name, value in overrides.items():
        object.__setattr__(opportunity, field_name, value)
    return opportunity


def _row_count(db_path: Path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM value_detections").fetchone()[0])
    finally:
        connection.close()


def test_extreme_ev_values_remain_finite_and_controlled() -> None:
    assert calculate_ev(0.01, 100.0) == pytest.approx(0.0)
    assert calculate_ev(0.99, 100.0) == pytest.approx(98.0)
    assert calculate_ev(0.01, 1.01) == pytest.approx(-0.9899)

    for true_probability, offered_odds in ((0.01, 100.0), (0.99, 100.0), (0.01, 1.01)):
        assert math.isfinite(calculate_ev(true_probability, offered_odds))


@pytest.mark.parametrize(
    ("true_probability", "offered_odds"),
    (
        (float("nan"), 2.0),
        (0.5, float("inf")),
        (float("inf"), float("inf")),
    ),
)
def test_ev_rejects_nan_and_infinite_values_in_bulk(
    true_probability: float,
    offered_odds: float,
) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        calculate_ev(true_probability, offered_odds)


@pytest.mark.parametrize(
    "overrides",
    (
        {"true_probability": float("nan")},
        {"offered_odds": float("inf")},
        {"expected_value": float("-inf")},
        {"edge_percentage": float("nan")},
    ),
)
def test_opportunity_rejects_invalid_numeric_payloads(overrides: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        _opportunity(**overrides)


@pytest.mark.parametrize(
    "snapshot",
    (
        _snapshot(odds=None),
        _snapshot(odds="not-a-dict"),
        _snapshot(odds={"pinnacle": "bad", "bet365": {"home": 2.2, "draw": 3.1, "away": 4.5}}),
        _snapshot(valid_for_analysis=False),
    ),
)
def test_malformed_snapshots_return_no_pinnacle_opportunity(snapshot: dict[str, object]) -> None:
    assert detect_value_vs_pinnacle(snapshot, "bet365") == []


def test_missing_snapshot_identity_fails_clearly() -> None:
    snapshot = _snapshot()
    del snapshot["match_id"]

    with pytest.raises(ValueError, match="match_id is required"):
        detect_value_vs_pinnacle(snapshot, "bet365")


def test_missing_target_selection_is_skipped_not_fabricated() -> None:
    snapshot = _snapshot(
        odds={
            "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
            "bet365": {"home": 2.2, "draw": 3.1},
        },
    )

    opportunities = detect_value_vs_pinnacle(snapshot, "bet365")

    assert [opportunity.selection for opportunity in opportunities] == ["home_win"]


def test_pinnacle_missing_or_malformed_inputs_are_safe() -> None:
    assert detect_value_vs_pinnacle(
        _snapshot(odds={"bet365": {"home": 2.2, "draw": 3.1, "away": 4.5}}),
        "bet365",
    ) == []

    with pytest.raises(ValueError, match="offered_odds must"):
        detect_value_vs_pinnacle(
            _snapshot(
                odds={
                    "pinnacle": {"home": 0.0, "draw": 3.2, "away": 4.0},
                    "bet365": {"home": 2.2, "draw": 3.1, "away": 4.5},
                },
            ),
            "bet365",
        )


def test_pinnacle_handles_missing_selection_and_absurd_target_odds() -> None:
    snapshot = _snapshot(
        odds={
            "pinnacle": {"home": 2.0, "draw": 3.2},
            "bet365": {"home": 100.0, "draw": 3.1, "away": 100.0},
        },
    )

    opportunities = detect_value_vs_pinnacle(snapshot, "bet365", min_ev=0.0)

    assert [opportunity.selection for opportunity in opportunities] == ["home_win"]
    assert opportunities[0].expected_value == pytest.approx(49.0)
    assert opportunities[0].actionable is False


def test_poisson_refuses_untrained_failed_sanity_and_fallback_models() -> None:
    assert detect_value_vs_poisson(_snapshot(), FakeModel(trained=False), "bet365") == []
    assert detect_value_vs_poisson(_snapshot(), FakeModel(sanity_passed=False), "bet365") == []
    assert detect_value_vs_poisson(_snapshot(), FakeModel(used_fallback=True), "bet365") == []


@pytest.mark.parametrize(
    "probabilities",
    (
        {"home_win": float("nan"), "draw": 0.25, "away_win": 0.15},
        {"home_win": float("inf"), "draw": 0.25, "away_win": 0.15},
        {"home_win": 1.20, "draw": 0.00, "away_win": -0.20},
    ),
)
def test_poisson_rejects_invalid_probability_values(
    probabilities: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="true_probability must|must be finite"):
        detect_value_vs_poisson(
            _snapshot(),
            FakeModel(probabilities=probabilities),
            "bet365",
        )


def test_poisson_rejects_probability_vector_that_does_not_sum_to_one() -> None:
    with pytest.raises(ValueError, match="model probabilities must sum to 1"):
        detect_value_vs_poisson(
            _snapshot(),
            FakeModel(probabilities={"home_win": 0.60, "draw": 0.25, "away_win": 0.05}),
            "bet365",
        )


def test_consensus_refuses_divergent_or_single_source_hits() -> None:
    divergent = detect_value_consensus(
        _snapshot(
            odds={
                "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
                "bet365": {"home": 2.2, "draw": 3.1, "away": 3.0},
            },
        ),
        FakeModel(probabilities={"home_win": 0.40, "draw": 0.20, "away_win": 0.40}),
        "bet365",
    )
    assert divergent == []

    only_pinnacle = detect_value_consensus(
        _snapshot(
            odds={
                "pinnacle": {"home": 2.0, "draw": 3.2, "away": 4.0},
                "bet365": {"home": 2.2, "draw": 2.5, "away": 3.0},
            },
        ),
        FakeModel(probabilities={"home_win": 0.40, "draw": 0.32, "away_win": 0.28}),
        "bet365",
    )
    assert only_pinnacle == []


def test_consensus_uses_lower_ev_when_sources_agree() -> None:
    opportunity = detect_value_consensus(
        _snapshot(),
        FakeModel(probabilities={"home_win": 0.60, "draw": 0.25, "away_win": 0.15}),
        "bet365",
    )[0]

    assert opportunity.selection == "home_win"
    assert opportunity.expected_value == pytest.approx(0.10)
    assert opportunity.edge_percentage == pytest.approx(10.0)
    assert opportunity.source == "consensus"
    assert opportunity.actionable is False


def test_deduplication_ignores_same_id_when_logical_keys_differ() -> None:
    first = _opportunity(opportunity_id="sim-same", match_id="match-001")
    second = _opportunity(opportunity_id="sim-same", match_id="match-002")

    assert deduplicate_opportunities([first, second], now=NOW) == [first, second]


def test_deduplication_uses_logical_key_even_when_ids_differ() -> None:
    first = _opportunity(offered_odds=2.0, expected_value=0.20)
    second = _opportunity(offered_odds=2.4, expected_value=0.44)

    assert first.opportunity_id != second.opportunity_id
    assert deduplicate_opportunities([first, second], now=NOW) == [first]


def test_deduplication_treats_window_boundary_as_inside_window() -> None:
    seen = [_opportunity(created_at=(NOW - timedelta(minutes=60)).isoformat())]
    current = _opportunity(created_at=NOW.isoformat())

    assert deduplicate_opportunities([current], seen=seen, window_minutes=60, now=NOW) == []


def test_deduplication_rejects_naive_time_and_incomplete_seen_dict() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        deduplicate_opportunities([_opportunity()], now=datetime(2026, 5, 28, 12, 0))

    with pytest.raises(ValueError, match="market is required"):
        deduplicate_opportunities(
            [_opportunity()],
            seen=[{"match_id": "match-001", "created_at": NOW.isoformat()}],
            now=NOW,
        )


def test_persistence_rejects_unsafe_duplicate_and_partial_invalid_batches(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    valid = _opportunity()
    unsafe = _unsafe_opportunity(actionable=True)

    with pytest.raises(ValueError, match="opportunity must not be actionable"):
        persist_simulated_opportunities(str(db_path), [valid, unsafe])

    assert persist_simulated_opportunities(str(db_path), [valid]) == 1
    assert persist_simulated_opportunities(str(db_path), [valid]) == 0
    assert _row_count(db_path) == 1


def test_persistence_accepts_extreme_but_valid_simulated_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "edgehunter.db"
    opportunity = _opportunity(
        true_probability=1.0,
        offered_odds=100.0,
        expected_value=99.0,
        edge_percentage=9900.0,
    )

    assert persist_simulated_opportunities(str(db_path), [opportunity]) == 1
    assert _row_count(db_path) == 1


@pytest.mark.parametrize(
    "field_name",
    ("is_simulated", "paper_trading", "actionable", "bet_placed", "alerted"),
)
def test_persistence_rejects_tampered_security_flags(
    tmp_path: Path,
    field_name: str,
) -> None:
    db_path = tmp_path / "edgehunter.db"
    bad_values = {
        "is_simulated": False,
        "paper_trading": False,
        "actionable": True,
        "bet_placed": True,
        "alerted": True,
    }

    with pytest.raises(ValueError):
        persist_simulated_opportunities(
            str(db_path),
            [_unsafe_opportunity(**{field_name: bad_values[field_name]})],
        )


def test_persistence_rejects_non_opportunity_payloads(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="only SimulatedValueOpportunity"):
        persist_simulated_opportunities(
            str(tmp_path / "edgehunter.db"),
            [{"match_id": "match-001", "stake": 10.0}],  # type: ignore[list-item]
        )


def test_operational_guardrails_remain_absent_from_runtime_modules() -> None:
    combined_source = "\n".join(
        (
            inspect.getsource(value_detector_module),
            inspect.getsource(persistence_module),
        )
    ).lower()

    for forbidden in (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "telegram",
        "scheduler",
        "kelly",
        "bankroll",
        "place_bet",
        "execute_bet",
        "real_money",
    ):
        assert forbidden not in combined_source

    assert "actionable=true" not in combined_source.replace(" ", "")
    assert "bet_placed=true" not in combined_source.replace(" ", "")
    assert "alerted=true" not in combined_source.replace(" ", "")
