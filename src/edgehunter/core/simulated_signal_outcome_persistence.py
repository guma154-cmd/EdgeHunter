"""Simulated Signal Outcome Persistence"""
import sqlite3
import json
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome

def _get_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection

def persist_simulated_signal_outcome(db_path: str, outcome: SimulatedSignalOutcome) -> int:
    """Persist a simulated signal outcome idempotently."""
    
    connection = _get_connection(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            INSERT OR IGNORE INTO simulated_signal_outcomes (
                outcome_id, signal_id, classification_id, opportunity_id,
                outcome_status, observed_at, source, notes,
                is_simulated, paper_trading, learning_mode,
                actionable, bet_placed, alerted, not_operational_advice
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                outcome.outcome_id,
                outcome.signal_id,
                outcome.classification_id,
                outcome.opportunity_id,
                outcome.outcome_status.value,
                outcome.observed_at,
                outcome.source,
                outcome.notes,
                int(outcome.is_simulated),
                int(outcome.paper_trading),
                int(outcome.learning_mode),
                int(outcome.actionable),
                int(outcome.bet_placed),
                int(outcome.alerted),
                int(outcome.not_operational_advice),
            )
        )
        
        # Determine the id to return (either new or existing)
        if cursor.rowcount > 0:
            result_id = cursor.lastrowid
        else:
            cursor.execute(
                "SELECT id FROM simulated_signal_outcomes WHERE outcome_id = ?",
                (outcome.outcome_id,)
            )
            result_id = cursor.fetchone()[0]
            
        connection.commit()
        return result_id
    finally:
        connection.close()


def list_simulated_signal_outcomes(
    db_path: str,
    limit: int = 50,
    offset: int = 0,
    outcome_status: str | None = None,
    signal_id: str | None = None,
    classification_id: str | None = None,
    opportunity_id: str | None = None,
) -> dict:
    """List simulated signal outcomes with optional filtering and pagination."""
    
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > 100:
        limit = 100
        
    if offset < 0:
        raise ValueError("offset must be >= 0")
        
    query = "SELECT * FROM simulated_signal_outcomes"
    count_query = "SELECT COUNT(*) FROM simulated_signal_outcomes"
    
    conditions = []
    params = []
    
    if outcome_status:
        conditions.append("outcome_status = ?")
        params.append(outcome_status)
        
    if signal_id:
        conditions.append("signal_id = ?")
        params.append(signal_id)
        
    if classification_id:
        conditions.append("classification_id = ?")
        params.append(classification_id)
        
    if opportunity_id:
        conditions.append("opportunity_id = ?")
        params.append(opportunity_id)
        
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        query += where_clause
        count_query += where_clause
        
    query += " ORDER BY observed_at DESC, id DESC LIMIT ? OFFSET ?"
    params_with_pagination = params + [limit, offset]
    
    connection = _get_connection(db_path)
    try:
        cursor = connection.cursor()
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        cursor.execute(query, params_with_pagination)
        rows = cursor.fetchall()
    finally:
        connection.close()
        
    data = []
    for row in rows:
        item = dict(row)
        
        if item.get("actionable") == 1 or item.get("bet_placed") == 1 or item.get("alerted") == 1:
            raise RuntimeError("Database contains unsafe operational flags (actionable=1, bet_placed=1, alerted=1). Security corruption detected.")
            
        for k in ["stake", "kelly", "kelly_criterion", "bankroll", "bet_amount", "wager", "suggested_bet", "recommended_bet"]:
            if k in item:
                raise RuntimeError(f"Database contains forbidden financial field: {k}")
                
        item['is_simulated'] = bool(item['is_simulated'])
        item['paper_trading'] = bool(item['paper_trading'])
        item['learning_mode'] = bool(item['learning_mode'])
        item['actionable'] = bool(item.get('actionable', False))
        item['bet_placed'] = bool(item.get('bet_placed', False))
        item['alerted'] = bool(item.get('alerted', False))
        item['not_operational_advice'] = bool(item['not_operational_advice'])
        data.append(item)
        
    return {
        "data": data,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": len(data),
            "total": total_count,
            "has_more": offset + len(data) < total_count
        },
        "filters": {
            "outcome_status": outcome_status,
            "signal_id": signal_id,
            "classification_id": classification_id,
            "opportunity_id": opportunity_id
        }
    }
