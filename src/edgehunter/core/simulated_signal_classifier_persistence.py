"""SQLite persistence for the SimulatedSignalClassifier."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.edgehunter.core.simulated_signal_classifier import SimulatedSignalClassificationResult
from src.edgehunter.database.schema import configure_connection

def _get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    configure_connection(connection)
    connection.row_factory = sqlite3.Row
    return connection

def persist_simulated_signal_classification(
    db_path: str,
    result: SimulatedSignalClassificationResult,
) -> int:
    """
    Persist a simulated signal classification result idempotently.
    Returns the auto-increment ID of the inserted or existing row.
    """
    if not isinstance(result, SimulatedSignalClassificationResult):
        raise ValueError("result must be a SimulatedSignalClassificationResult")

    # Security rules
    if result.actionable is True:
        raise ValueError("actionable must be False")
    if result.bet_placed is True:
        raise ValueError("bet_placed must be False")
    if result.alerted is True:
        raise ValueError("alerted must be False")
    if result.is_simulated is False:
        raise ValueError("is_simulated must be True")
    if result.paper_trading is False:
        raise ValueError("paper_trading must be True")
    if result.not_operational_advice is False:
        raise ValueError("not_operational_advice must be True")
    if result.learning_mode is False:
        raise ValueError("learning_mode must be True")
    if result.display is False:
        raise ValueError("display must be True")

    # The result object itself already validates against prohibited fields,
    # operational rationale, and risk factors at instantiation time.
    # Therefore, if it is a valid SimulatedSignalClassificationResult, it is safe.

    risk_factors_json = json.dumps(list(result.risk_factors), ensure_ascii=False)

    sql = """
        INSERT INTO simulated_signal_classifications (
            classification_id, signal_id, opportunity_id, simulation_label,
            calibrated_assertiveness, confidence, threshold_green,
            learning_mode, display, rationale, risk_factors_json,
            is_simulated, paper_trading, actionable, bet_placed, alerted,
            not_operational_advice, created_at, inserted_at
        )
        VALUES (
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT(classification_id) DO UPDATE SET
            inserted_at = CURRENT_TIMESTAMP
    """

    parameters = (
        result.classification_id,
        result.signal_id,
        result.opportunity_id,
        result.simulation_label.value,
        result.calibrated_assertiveness,
        result.confidence,
        result.threshold_green,
        1 if result.learning_mode else 0,
        1 if result.display else 0,
        result.rationale,
        risk_factors_json,
        1 if result.is_simulated else 0,
        1 if result.paper_trading else 0,
        1 if result.actionable else 0,
        1 if result.bet_placed else 0,
        1 if result.alerted else 0,
        1 if result.not_operational_advice else 0,
    )

    connection = _get_connection(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(sql, parameters)
        
        # Get the ID (either inserted or updated)
        cursor.execute(
            "SELECT id FROM simulated_signal_classifications WHERE classification_id = ?",
            (result.classification_id,),
        )
        row = cursor.fetchone()
        row_id = row[0]
        
        connection.commit()
        return row_id
    finally:
        connection.close()

def list_simulated_signal_classifications(
    db_path: str,
    limit: int = 50,
    offset: int = 0,
    simulation_label: str | None = None,
    opportunity_id: str | None = None,
    signal_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve simulated classifications with filtering and pagination."""
    if not isinstance(limit, int) or limit < 1:
        limit = 50
    if not isinstance(offset, int) or offset < 0:
        offset = 0

    sql = "SELECT * FROM simulated_signal_classifications WHERE 1=1"
    params: list[Any] = []

    if simulation_label is not None:
        sql += " AND simulation_label = ?"
        params.append(simulation_label)
        
    if opportunity_id is not None:
        sql += " AND opportunity_id = ?"
        params.append(opportunity_id)
        
    if signal_id is not None:
        sql += " AND signal_id = ?"
        params.append(signal_id)

    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    connection = _get_connection(db_path)
    try:
        cursor = connection.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            d = dict(row)
            d["is_simulated"] = bool(d["is_simulated"])
            d["paper_trading"] = bool(d["paper_trading"])
            d["actionable"] = bool(d["actionable"])
            d["bet_placed"] = bool(d["bet_placed"])
            d["alerted"] = bool(d["alerted"])
            d["not_operational_advice"] = bool(d["not_operational_advice"])
            d["learning_mode"] = bool(d["learning_mode"])
            d["display"] = bool(d["display"])
            try:
                d["risk_factors"] = json.loads(d["risk_factors_json"])
            except Exception:
                d["risk_factors"] = []
            results.append(d)
        return results
    finally:
        connection.close()
