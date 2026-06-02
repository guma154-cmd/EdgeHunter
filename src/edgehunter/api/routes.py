import sqlite3
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from src.edgehunter.api.contracts import build_safe_api_response
from src.edgehunter.api.security import get_api_key
from src.edgehunter.core.dashboard_periodic_reports import generate_periodic_agent_evolution_report
from src.edgehunter.core.dashboard_summary import generate_dashboard_summary
from src.edgehunter.core.gemini_validator_persistence import list_ai_validation_reports
from src.edgehunter.core.simulated_signal_calibration_report import generate_simulated_signal_calibration_report
from src.edgehunter.core.simulated_signal_classifier_persistence import list_simulated_signal_classifications
from src.edgehunter.core.simulated_signal_outcome_persistence import list_simulated_signal_outcomes
from src.edgehunter.core.simulated_threshold_suggestion import generate_threshold_suggestion

router = APIRouter()

def get_db_path() -> str:
    return os.getenv("EDGEHUNTER_DB_PATH", "edge_hunter.db")

def list_value_detections(
    db_path: str,
    limit: int = 50,
    offset: int = 0,
    source: str | None = None,
    detection_method: str | None = None,
    match_id: str | None = None,
) -> dict:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > 100:
        limit = 100
    if offset < 0:
        raise ValueError("offset must be >= 0")

    query = "SELECT * FROM value_detections WHERE 1=1"
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)
    if detection_method:
        query += " AND detection_method = ?"
        params.append(detection_method)
    if match_id:
        query += " AND match_id = ?"
        params.append(match_id)

    query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    # For total count
    count_query = "SELECT COUNT(*) FROM value_detections WHERE 1=1"
    count_params = []
    if source:
        count_query += " AND source = ?"
        count_params.append(source)
    if detection_method:
        count_query += " AND detection_method = ?"
        count_params.append(detection_method)
    if match_id:
        count_query += " AND match_id = ?"
        count_params.append(match_id)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        cursor = conn.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]

    data = []
    for row in rows:
        row_dict = dict(row)

        if row_dict.get("actionable") == 1 or row_dict.get("bet_placed") == 1 or row_dict.get("alerted") == 1:
            raise RuntimeError("Database contains unsafe operational flags (actionable=1, bet_placed=1, alerted=1). Security corruption detected.")

        row_dict["is_simulated"] = bool(row_dict.get("is_simulated", True))
        row_dict["paper_trading"] = bool(row_dict.get("paper_trading", True))
        row_dict["actionable"] = bool(row_dict.get("actionable", False))
        row_dict["bet_placed"] = bool(row_dict.get("bet_placed", False))
        row_dict["alerted"] = bool(row_dict.get("alerted", False))

        for k in ["stake", "kelly", "kelly_criterion", "bankroll", "bet_amount", "wager", "suggested_bet", "recommended_bet"]:
            if k in row_dict:
                raise RuntimeError(f"Database contains forbidden financial field: {k}")

        data.append(row_dict)

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
            "source": source,
            "detection_method": detection_method,
            "match_id": match_id
        }
    }

@router.get("/api/value-detections", dependencies=[Depends(get_api_key)], tags=["value-detections"])
def get_value_detections(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    detection_method: Optional[str] = None,
    match_id: Optional[str] = None,
):
    try:
        db_path = get_db_path()
        result = list_value_detections(
            db_path=db_path,
            limit=limit,
            offset=offset,
            source=source,
            detection_method=detection_method,
            match_id=match_id
        )
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_value_detection_by_id(db_path: str, detection_id: int) -> dict | None:
    if detection_id <= 0:
        raise ValueError("id must be positive")

    query = "SELECT * FROM value_detections WHERE id = ?"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (detection_id,))
        row = cursor.fetchone()

    if not row:
        return None

    row_dict = dict(row)
    if row_dict.get("actionable") == 1 or row_dict.get("bet_placed") == 1 or row_dict.get("alerted") == 1:
        raise RuntimeError("Database contains unsafe operational flags (actionable=1, bet_placed=1, alerted=1). Security corruption detected.")

    row_dict["is_simulated"] = bool(row_dict.get("is_simulated", True))
    row_dict["paper_trading"] = bool(row_dict.get("paper_trading", True))
    row_dict["actionable"] = bool(row_dict.get("actionable", False))
    row_dict["bet_placed"] = bool(row_dict.get("bet_placed", False))
    row_dict["alerted"] = bool(row_dict.get("alerted", False))

    for k in ["stake", "kelly", "kelly_criterion", "bankroll", "bet_amount", "wager", "suggested_bet", "recommended_bet"]:
        if k in row_dict:
            raise RuntimeError(f"Database contains forbidden financial field: {k}")

    return row_dict

@router.get("/api/value-detections/{id}", dependencies=[Depends(get_api_key)], tags=["value-detections"])
def get_value_detection(id: int):
    try:
        db_path = get_db_path()
        result = get_value_detection_by_id(db_path, id)
        if result is None:
            raise HTTPException(status_code=404, detail="Detection not found")
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

def list_backtests(limit: int = 50, offset: int = 0) -> dict:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > 100:
        limit = 100
    if offset < 0:
        raise ValueError("offset must be >= 0")

    return {
        "data": [],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": 0,
            "total": 0,
            "has_more": False
        },
        "filters": {}
    }

@router.get("/api/backtests", dependencies=[Depends(get_api_key)], tags=["backtests"])
def get_backtests(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
):
    try:
        result = list_backtests(limit=limit, offset=offset)
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

from src.edgehunter.core.reconciliation_report import generate_reconciliation_report

@router.get("/api/reconciliation/report", dependencies=[Depends(get_api_key)], tags=["reconciliation"])
def get_reconciliation_report():
    try:
        db_path = get_db_path()
        result = generate_reconciliation_report(db_path)
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/gemini-validations",
    dependencies=[Depends(get_api_key)],
    tags=["gemini-validations"],
)
def get_gemini_validations(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
    opportunity_id: Optional[str] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    technical_verdict: Optional[str] = None,
):
    try:
        result = list_ai_validation_reports(
            db_path=get_db_path(),
            limit=limit,
            offset=offset,
            opportunity_id=opportunity_id,
            provider=provider,
            model_name=model_name,
            technical_verdict=technical_verdict,
        )
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/simulated-signal-classifications",
    dependencies=[Depends(get_api_key)],
    tags=["simulated-signal-classifications"],
)
def get_simulated_signal_classifications(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
    simulation_label: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    signal_id: Optional[str] = None,
):
    try:
        db_path = get_db_path()
        result = list_simulated_signal_classifications(
            db_path=db_path,
            limit=limit,
            offset=offset,
            simulation_label=simulation_label,
            opportunity_id=opportunity_id,
            signal_id=signal_id,
        )
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/api/simulated-signal-outcomes",
    dependencies=[Depends(get_api_key)],
    tags=["simulated-signal-outcomes"],
)
def get_simulated_signal_outcomes(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
    outcome_status: Optional[str] = None,
    signal_id: Optional[str] = None,
    classification_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
):
    try:
        db_path = get_db_path()
        result = list_simulated_signal_outcomes(
            db_path=db_path,
            limit=limit,
            offset=offset,
            outcome_status=outcome_status,
            signal_id=signal_id,
            classification_id=classification_id,
            opportunity_id=opportunity_id,
        )
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


def _read_dashboard_inputs(
    db_path: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], list[dict]]:
    classifications = list_simulated_signal_classifications(
        db_path=db_path,
        limit=limit,
        offset=offset,
    )["data"]
    outcomes = list_simulated_signal_outcomes(
        db_path=db_path,
        limit=limit,
        offset=offset,
    )["data"]
    return classifications, outcomes


@router.get(
    "/api/dashboard/summary",
    dependencies=[Depends(get_api_key)],
    tags=["dashboard"],
)
def get_dashboard_summary(
    limit: int = Query(50, gt=0),
    offset: int = Query(0, ge=0),
):
    try:
        classifications, outcomes = _read_dashboard_inputs(
            db_path=get_db_path(),
            limit=limit,
            offset=offset,
        )
        result = generate_dashboard_summary(
            classifications=classifications,
            outcomes=outcomes,
            current_threshold=0.70,
        )
        return build_safe_api_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/calibration/summary",
    dependencies=[Depends(get_api_key)],
    tags=["dashboard"],
)
def get_calibration_summary(
    threshold_green: float = Query(0.70, ge=0.0, le=1.0),
    minimum_sample_size: int = Query(30, gt=0),
):
    try:
        classifications, outcomes = _read_dashboard_inputs(db_path=get_db_path())
        calibration_report = generate_simulated_signal_calibration_report(
            classifications,
            outcomes,
            threshold_green=threshold_green,
            minimum_viable_sample_size=minimum_sample_size,
        )
        threshold_suggestion = generate_threshold_suggestion(
            calibration_report,
            current_threshold=threshold_green,
            minimum_sample_size=minimum_sample_size,
        )
        return build_safe_api_response(
            {
                "calibration_report": calibration_report,
                "threshold_suggestion": threshold_suggestion.to_dict(),
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/dashboard/evolution-report",
    dependencies=[Depends(get_api_key)],
    tags=["dashboard"],
)
def get_dashboard_evolution_report(
    period: str = Query("daily"),
    current_period_start: str = Query(...),
    current_period_end: str = Query(...),
    previous_period_start: Optional[str] = None,
    previous_period_end: Optional[str] = None,
):
    try:
        classifications, outcomes = _read_dashboard_inputs(db_path=get_db_path(), limit=100)
        report = generate_periodic_agent_evolution_report(
            classifications,
            outcomes,
            period=period,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            previous_period_start=previous_period_start,
            previous_period_end=previous_period_end,
        )
        return build_safe_api_response(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

from src.edgehunter.core.dashboard_renderer import render_dashboard_visual_page, render_dashboard_html
from src.edgehunter.database.migrations_validator import validate_database_migrations

@router.get(
    "/api/dashboard/visual",
    dependencies=[Depends(get_api_key)],
    tags=["dashboard"],
)
def get_dashboard_visual():
    try:
        classifications, outcomes = _read_dashboard_inputs(
            db_path=get_db_path(),
            limit=50,
            offset=0,
        )
        summary = generate_dashboard_summary(
            classifications=classifications,
            outcomes=outcomes,
            current_threshold=0.70,
        )
        calibration_report = generate_simulated_signal_calibration_report(
            classifications,
            outcomes,
            threshold_green=0.70,
            minimum_viable_sample_size=30,
        )
        schema_val = validate_database_migrations(get_db_path())
        page = render_dashboard_visual_page(
            summary=summary,
            calibration_summary=calibration_report,
            evolution_report=None,
            schema_status=schema_val
        )
        return build_safe_api_response(page.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/dashboard",
    dependencies=[Depends(get_api_key)],
    tags=["dashboard"],
    response_class=HTMLResponse
)
def get_dashboard_html():
    try:
        classifications, outcomes = _read_dashboard_inputs(
            db_path=get_db_path(),
            limit=50,
            offset=0,
        )
        summary = generate_dashboard_summary(
            classifications=classifications,
            outcomes=outcomes,
            current_threshold=0.70,
        )
        calibration_report = generate_simulated_signal_calibration_report(
            classifications,
            outcomes,
            threshold_green=0.70,
            minimum_viable_sample_size=30,
        )
        schema_val = validate_database_migrations(get_db_path())
        page = render_dashboard_visual_page(
            summary=summary,
            calibration_summary=calibration_report,
            evolution_report=None,
            schema_status=schema_val
        )
        html_content = render_dashboard_html(page)
        return HTMLResponse(content=html_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

from src.edgehunter.database.migration_planner import plan_database_migrations
from src.edgehunter.database.migration_journal import list_applied_migrations
from src.edgehunter.database.migrations import validate_migration_registry
from src.edgehunter.database.migration_models import MigrationExecutionMode

@router.get("/api/migrations/status", dependencies=[Depends(get_api_key)], tags=["migrations"])
def get_migrations_status():
    try:
        db_path = get_db_path()
        registry_status = validate_migration_registry()
        plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.DRY_RUN)

        pending = [i for i in plan.items if i.status.value != "APPLIED"]

        result = {
            "registry_valid": registry_status["passed"],
            "latest_version": registry_status.get("latest", ""),
            "total_defined": registry_status.get("count", 0),
            "up_to_date": len(pending) == 0,
            "pending_count": len(pending),
            "is_simulated": True,
            "actionable": False,
            "not_operational_advice": True
        }
        return build_safe_api_response(result)
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/migrations/plan", dependencies=[Depends(get_api_key)], tags=["migrations"])
def get_migrations_plan():
    try:
        db_path = get_db_path()
        plan = plan_database_migrations(db_path, execution_mode=MigrationExecutionMode.DRY_RUN)

        result = {
            "execution_mode": plan.execution_mode.value,
            "is_simulated": plan.is_simulated,
            "actionable": plan.actionable,
            "not_operational_advice": plan.not_operational_advice,
            "items": [item.to_dict() for item in plan.items]
        }
        return build_safe_api_response(result)
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/migrations/journal", dependencies=[Depends(get_api_key)], tags=["migrations"])
def get_migrations_journal(limit: int = Query(50, gt=0), offset: int = Query(0, ge=0)):
    try:
        db_path = get_db_path()
        try:
            journal = list_applied_migrations(db_path, limit=limit, offset=offset)
        except sqlite3.Error:
            journal = []

        result = {
            "data": journal,
            "is_simulated": True,
            "actionable": False,
            "not_operational_advice": True
        }
        return build_safe_api_response(result)
    except (RuntimeError, sqlite3.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))
