import csv
import io
import json
from datetime import datetime
from dateutil import parser as date_parser

from src.edgehunter.core.observed_result import ObservedResult, ObservedResultStatus, ObservedResultSource

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def _check_payload_size(content: str) -> None:
    if len(content.encode("utf-8")) > MAX_PAYLOAD_SIZE:
        raise ValueError("Payload size exceeds 5MB limit.")


def _check_source_ref(source_ref: str) -> None:
    if source_ref.startswith("http://") or source_ref.startswith("https://"):
        raise ValueError("URLs are not allowed in source_ref.")


def _parse_row_dict(row: dict, source_ref: str) -> ObservedResult:
    # Safely extract and convert string fields
    def get_str(k):
        return str(row.get(k, "")).strip()

    result_id = get_str("result_id")
    signal_id = get_str("signal_id")
    classification_id = get_str("classification_id")
    opportunity_id = get_str("opportunity_id")
    match_id = get_str("match_id")
    notes = get_str("notes")
    
    # Parse status
    status_str = get_str("result_status")
    try:
        status = ObservedResultStatus(status_str)
    except ValueError:
        raise ValueError(f"Invalid result_status: {status_str}")

    # Parse source
    source_str = get_str("source")
    try:
        source = ObservedResultSource(source_str)
    except ValueError:
        raise ValueError(f"Invalid source: {source_str}")

    # Parse observed_at
    observed_at_str = get_str("observed_at")
    if not observed_at_str:
        raise ValueError("observed_at cannot be empty.")
    try:
        observed_at = date_parser.isoparse(observed_at_str)
    except ValueError:
        raise ValueError(f"Invalid date format for observed_at: {observed_at_str}")
        
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware.")

    return ObservedResult(
        result_id=result_id,
        signal_id=signal_id,
        classification_id=classification_id,
        opportunity_id=opportunity_id,
        match_id=match_id,
        result_status=status,
        observed_at=observed_at,
        source=source,
        source_ref=source_ref,
        notes=notes
    )


def _validate_and_sort_results(results: list[ObservedResult]) -> list[ObservedResult]:
    seen_ids = set()
    for res in results:
        if res.result_id in seen_ids:
            raise ValueError(f"Duplicate result_id detected in payload: {res.result_id}")
        seen_ids.add(res.result_id)
        
    return sorted(results, key=lambda r: r.result_id)


def parse_observed_results_csv(content: str, *, source_ref: str = "local_csv") -> list[ObservedResult]:
    if not content.strip():
        return []
        
    _check_payload_size(content)
    _check_source_ref(source_ref)
    
    results = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            results.append(_parse_row_dict(row, source_ref))
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid CSV format: {str(e)}")
        
    return _validate_and_sort_results(results)


def parse_observed_results_json(content: str, *, source_ref: str = "local_json") -> list[ObservedResult]:
    if not content.strip():
        return []
        
    _check_payload_size(content)
    _check_source_ref(source_ref)
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")
        
    if not isinstance(data, list):
        raise ValueError("JSON content must be a list of objects.")
        
    results = []
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("Each item in JSON list must be an object.")
        results.append(_parse_row_dict(row, source_ref))
        
    return _validate_and_sort_results(results)
