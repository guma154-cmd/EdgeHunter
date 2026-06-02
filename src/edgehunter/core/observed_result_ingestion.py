from typing import Literal

from src.edgehunter.core.observed_result_parser import parse_observed_results_csv, parse_observed_results_json
from src.edgehunter.core.observed_result_matcher import match_observed_results_to_classifications
from src.edgehunter.core.observed_result_outcome_builder import build_simulated_outcomes_from_matches
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome


def ingest_observed_results_payload(
    payload: str,
    payload_format: Literal["csv", "json"],
    classifications: list[dict],
    source_ref: str = "ingestion"
) -> dict:
    """
    Ingests a raw payload (CSV or JSON), parses it, matches against classifications,
    and returns a list of SimulatedSignalOutcomes ready for persistence.
    """
    if payload_format not in ("csv", "json"):
        raise ValueError(f"Unsupported payload format: {payload_format}")

    # 1. Parse payload
    if payload_format == "csv":
        results = parse_observed_results_csv(payload, source_ref=source_ref)
    else:
        results = parse_observed_results_json(payload, source_ref=source_ref)

    # 2. Match
    match_data = match_observed_results_to_classifications(results, classifications)
    matched_pairs = match_data.get("matched", [])

    # 3. Build Outcomes
    outcomes: list[SimulatedSignalOutcome] = build_simulated_outcomes_from_matches(matched_pairs)

    return {
        "outcomes": outcomes,
        "summary": match_data.get("summary", {}),
        "unmatched_results": match_data.get("unmatched_results", []),
        "unmatched_classifications": match_data.get("unmatched_classifications", []),
        "duplicates": match_data.get("duplicates", []),
        "invalid": match_data.get("invalid", [])
    }
