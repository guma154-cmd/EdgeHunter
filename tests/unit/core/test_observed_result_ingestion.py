import pytest
import json
from src.edgehunter.core.observed_result_ingestion import ingest_observed_results_payload


def _valid_dict():
    return {
        "result_id": "res1",
        "signal_id": "sig1",
        "classification_id": "cls1",
        "opportunity_id": "opp1",
        "match_id": "mat1",
        "result_status": "POSITIVE_OBSERVED",
        "observed_at": "2026-06-02T10:00:00Z",
        "source": "LOCAL_JSON",
        "notes": "won"
    }


def _class():
    return {
        "classification_id": "cls1",
        "signal_id": "sig1",
        "opportunity_id": "opp1"
    }


def test_ingest_json_payload():
    payload = json.dumps([_valid_dict()])
    classifications = [_class()]
    
    out = ingest_observed_results_payload(payload, "json", classifications)
    
    assert len(out["outcomes"]) == 1
    assert out["summary"]["matched_total"] == 1
    assert out["outcomes"][0].signal_id == "sig1"


def test_ingest_csv_payload():
    csv_str = "result_id,signal_id,classification_id,opportunity_id,match_id,result_status,observed_at,source,notes\nres1,sig1,cls1,opp1,mat1,POSITIVE_OBSERVED,2026-06-02T10:00:00Z,LOCAL_CSV,won"
    classifications = [_class()]
    
    out = ingest_observed_results_payload(csv_str, "csv", classifications, source_ref="file.csv")
    
    assert len(out["outcomes"]) == 1
    assert out["summary"]["matched_total"] == 1
    assert out["outcomes"][0].source == "LOCAL_CSV:file.csv"


def test_ingest_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported payload format"):
        ingest_observed_results_payload("data", "xml", [])


def test_ingest_operational_language_blocked():
    d = _valid_dict()
    d["notes"] = "this is a gain"
    payload = json.dumps([d])
    
    with pytest.raises(ValueError, match="Operational language blocked"):
        ingest_observed_results_payload(payload, "json", [_class()])
