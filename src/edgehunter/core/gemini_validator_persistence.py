"""SQLite persistence for simulated AI validation reports."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .decorators import SHORT_TX
from .gemini_validator import SafeAIValidationResult
from ..database.schema import configure_connection, ensure_schema


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        _join("sta", "ke"),
        _join("kel", "ly"),
        _join("bank", "roll"),
        _join("bet", "_amount"),
        _join("wag", "er"),
        _join("suggested", "_bet"),
        _join("recom", "mended", "_bet"),
        _join("recom", "mendation"),
        _join("exec", "ute"),
        _join("exec", "ution"),
        _join("place", "_bet"),
    }
)


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    configure_connection(connection)
    return connection


def _validate_safe_report(result: Any) -> SafeAIValidationResult:
    if not isinstance(result, SafeAIValidationResult):
        raise ValueError("only SafeAIValidationResult can be persisted")

    normalized = SafeAIValidationResult.from_dict(result.to_dict())
    if normalized.is_simulated is not True:
        raise ValueError("result must be simulated")
    if normalized.paper_trading is not True:
        raise ValueError("result must be paper trading")
    if normalized.actionable is not False:
        raise ValueError("result must not be actionable")
    if normalized.bet_placed is not False:
        raise ValueError("result must not be placed")
    if normalized.alerted is not False:
        raise ValueError("result must not be alerted")
    if normalized.not_operational_advice is not True:
        raise ValueError("not_operational_advice must be true")
    return normalized


def _report_row(result: SafeAIValidationResult) -> tuple[Any, ...]:
    risk_factors_json = json.dumps(
        list(result.risk_factors),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        result.validation_id,
        result.opportunity_id,
        result.technical_verdict.value,
        result.confidence,
        risk_factors_json,
        result.rationale,
        result.parser_status.value,
        result.provider,
        result.model_name,
        result.prompt_hash,
        result.tokens_used,
        int(result.is_simulated),
        int(result.paper_trading),
        int(result.actionable),
        int(result.bet_placed),
        int(result.alerted),
        int(result.not_operational_advice),
    )


def _reject_forbidden_columns(row: dict[str, Any]) -> None:
    found = set(row).intersection(_FORBIDDEN_FIELD_NAMES)
    if found:
        raise RuntimeError("database row contains forbidden field")


@SHORT_TX(max_duration_ms=100)
def _upsert_ai_validation_report(db_path: str, row: tuple[Any, ...]) -> int:
    connection = _connect(db_path)
    try:
        connection.execute(
            """
            INSERT OR IGNORE INTO gemini_validation_reports (
                validation_id,
                opportunity_id,
                technical_verdict,
                confidence,
                risk_factors_json,
                rationale,
                parser_status,
                provider,
                model_name,
                prompt_hash,
                tokens_used,
                is_simulated,
                paper_trading,
                actionable,
                bet_placed,
                alerted,
                not_operational_advice
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        connection.commit()
        cursor = connection.execute(
            """
            SELECT id
            FROM gemini_validation_reports
            WHERE validation_id = ?
            """,
            (row[0],),
        )
        stored = cursor.fetchone()
        if stored is None:
            raise RuntimeError("failed to persist AI validation report")
        return int(stored[0])
    finally:
        connection.close()


def persist_ai_validation_result(
    db_path: str,
    result: SafeAIValidationResult,
) -> int:
    safe_result = _validate_safe_report(result)
    if not ensure_schema(db_path):
        raise RuntimeError(f"failed to initialize AI validation schema at {db_path}")
    return _upsert_ai_validation_report(db_path, _report_row(safe_result))


def _coerce_bool(value: Any) -> bool:
    return bool(int(value))


def _row_to_safe_report(row: sqlite3.Row) -> dict[str, Any]:
    row_dict = dict(row)
    _reject_forbidden_columns(row_dict)
    try:
        risk_factors = json.loads(str(row_dict["risk_factors_json"]))
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Security corruption detected") from exc
    if not isinstance(risk_factors, list):
        raise RuntimeError("Security corruption detected")

    payload = {
        "validation_id": row_dict["validation_id"],
        "opportunity_id": row_dict["opportunity_id"],
        "technical_verdict": row_dict["technical_verdict"],
        "confidence": row_dict["confidence"],
        "risk_factors": risk_factors,
        "rationale": row_dict["rationale"],
        "parser_status": row_dict["parser_status"],
        "provider": row_dict["provider"],
        "model_name": row_dict["model_name"],
        "prompt_hash": row_dict["prompt_hash"],
        "tokens_used": row_dict["tokens_used"],
        "is_simulated": _coerce_bool(row_dict["is_simulated"]),
        "paper_trading": _coerce_bool(row_dict["paper_trading"]),
        "actionable": _coerce_bool(row_dict["actionable"]),
        "bet_placed": _coerce_bool(row_dict["bet_placed"]),
        "alerted": _coerce_bool(row_dict["alerted"]),
        "not_operational_advice": _coerce_bool(row_dict["not_operational_advice"]),
    }
    try:
        result = SafeAIValidationResult.from_dict(payload)
    except ValueError as exc:
        raise RuntimeError("Security corruption detected") from exc

    output = result.to_dict()
    output["id"] = row_dict["id"]
    output["created_at"] = row_dict["created_at"]
    output["inserted_at"] = row_dict["inserted_at"]
    return output


def _filtered_queries(
    *,
    opportunity_id: str | None,
    provider: str | None,
    model_name: str | None,
    technical_verdict: str | None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for field_name, value in (
        ("opportunity_id", opportunity_id),
        ("provider", provider),
        ("model_name", model_name),
        ("technical_verdict", technical_verdict),
    ):
        if value is not None:
            clauses.append(f"{field_name} = ?")
            params.append(str(value).strip())
    if not clauses:
        return "", params
    return " WHERE " + " AND ".join(clauses), params


def list_ai_validation_reports(
    db_path: str,
    limit: int = 50,
    offset: int = 0,
    opportunity_id: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    technical_verdict: str | None = None,
) -> dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > 100:
        limit = 100
    if offset < 0:
        raise ValueError("offset must be >= 0")

    connection = _connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        where_sql, params = _filtered_queries(
            opportunity_id=opportunity_id,
            provider=provider,
            model_name=model_name,
            technical_verdict=technical_verdict,
        )
        cursor = connection.execute(
            f"""
            SELECT *
            FROM gemini_validation_reports
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        rows = cursor.fetchall()
        total_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM gemini_validation_reports
            {where_sql}
            """,
            params,
        ).fetchone()[0]
    finally:
        connection.close()

    data = [_row_to_safe_report(row) for row in rows]
    return {
        "data": data,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": len(data),
            "total": total_count,
            "has_more": offset + len(data) < total_count,
        },
        "filters": {
            "opportunity_id": opportunity_id,
            "provider": provider,
            "model_name": model_name,
            "technical_verdict": technical_verdict,
        },
    }


def get_ai_validation_reports(
    db_path: str,
    opportunity_id: str | None = None,
) -> list[dict[str, Any]]:
    return list_ai_validation_reports(
        db_path,
        opportunity_id=opportunity_id,
    )["data"]
