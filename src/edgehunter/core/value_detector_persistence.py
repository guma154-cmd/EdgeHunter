"""SQLite persistence for simulated paper-trading value detections."""

from __future__ import annotations

import sqlite3
from typing import Any

from .decorators import SHORT_TX
from .value_detector import SimulatedValueOpportunity
from ..database.schema import configure_connection, ensure_schema


def _require_text(value: str | None, field_name: str) -> str:
    clean_value = "" if value is None else str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    return clean_value


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    configure_connection(connection)
    return connection


def _validate_safe_paper_opportunity(opportunity: Any) -> SimulatedValueOpportunity:
    if not isinstance(opportunity, SimulatedValueOpportunity):
        raise ValueError("only SimulatedValueOpportunity can be persisted")
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
    return opportunity


def _opportunity_row(opportunity: SimulatedValueOpportunity) -> tuple[Any, ...]:
    return (
        _require_text(opportunity.opportunity_id, "opportunity_id"),
        _require_text(opportunity.match_id, "match_id"),
        _require_text(opportunity.market, "market"),
        _require_text(opportunity.selection, "selection"),
        opportunity.true_probability,
        opportunity.offered_odds,
        opportunity.expected_value,
        opportunity.edge_percentage,
        _require_text(opportunity.source, "source"),
        _require_text(opportunity.detection_method, "detection_method"),
        _require_text(opportunity.created_at, "created_at"),
        int(opportunity.is_simulated),
        int(opportunity.paper_trading),
        int(opportunity.actionable),
        int(opportunity.bet_placed),
        int(opportunity.alerted),
    )


@SHORT_TX(max_duration_ms=100)
def _insert_simulated_opportunity_rows(
    db_path: str,
    rows: list[tuple[Any, ...]],
) -> int:
    inserted = 0
    connection = _connect(db_path)
    try:
        for row in rows:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO value_detections (
                    opportunity_id,
                    match_id,
                    market,
                    selection,
                    true_probability,
                    offered_odds,
                    expected_value,
                    edge_percentage,
                    source,
                    detection_method,
                    created_at,
                    is_simulated,
                    paper_trading,
                    actionable,
                    bet_placed,
                    alerted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            inserted += int(cursor.rowcount == 1)
        connection.commit()
        return inserted
    finally:
        connection.close()


def persist_simulated_opportunities(
    db_path: str,
    opportunities: list[SimulatedValueOpportunity],
) -> int:
    """Persist safe simulated opportunities as an idempotent local audit log."""
    rows = [
        _opportunity_row(_validate_safe_paper_opportunity(opportunity))
        for opportunity in opportunities
    ]
    if not ensure_schema(db_path):
        raise RuntimeError(f"failed to initialize value_detections schema at {db_path}")
    return _insert_simulated_opportunity_rows(db_path, rows)
