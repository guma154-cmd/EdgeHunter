import json
import pytest
from src.edgehunter.core.observed_result import ObservedResultStatus, ObservedResultSource
from src.edgehunter.core.observed_result_parser import (
    parse_observed_results_csv,
    parse_observed_results_json,
    MAX_PAYLOAD_SIZE,
)

def _valid_dict(result_id="res_1"):
    return {
        "result_id": result_id,
        "signal_id": "sig_1",
        "classification_id": "cls_1",
        "opportunity_id": "opp_1",
        "match_id": "mat_1",
        "result_status": "POSITIVE_OBSERVED",
        "observed_at": "2026-06-02T10:00:00Z",
        "source": "LOCAL_CSV",
        "notes": "Valid note"
    }

def _to_csv(data_list):
    if not data_list:
        return ""
    keys = list(data_list[0].keys())
    lines = [",".join(keys)]
    for d in data_list:
        lines.append(",".join(str(d.get(k, "")) for k in keys))
    return "\n".join(lines)

def test_parse_csv_valid_single():
    csv_str = _to_csv([_valid_dict()])
    res = parse_observed_results_csv(csv_str)
    assert len(res) == 1
    assert res[0].result_id == "res_1"
    assert res[0].result_status == ObservedResultStatus.POSITIVE_OBSERVED

def test_parse_csv_valid_multiple():
    csv_str = _to_csv([_valid_dict("res_2"), _valid_dict("res_1")])
    res = parse_observed_results_csv(csv_str)
    assert len(res) == 2
    # Should be deterministically sorted by result_id
    assert res[0].result_id == "res_1"
    assert res[1].result_id == "res_2"

def test_parse_json_valid_single():
    d = _valid_dict()
    d["source"] = "LOCAL_JSON"
    json_str = json.dumps([d])
    res = parse_observed_results_json(json_str)
    assert len(res) == 1
    assert res[0].result_id == "res_1"
    assert res[0].source == ObservedResultSource.LOCAL_JSON

def test_parse_json_valid_multiple():
    json_str = json.dumps([_valid_dict("res_2"), _valid_dict("res_1")])
    res = parse_observed_results_json(json_str)
    assert len(res) == 2
    assert res[0].result_id == "res_1"
    assert res[1].result_id == "res_2"

def test_csv_missing_mandatory_field_fails():
    d = _valid_dict()
    del d["result_id"]
    csv_str = _to_csv([d])
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_observed_results_csv(csv_str)

def test_json_missing_mandatory_field_fails():
    d = _valid_dict()
    del d["signal_id"]
    json_str = json.dumps([d])
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_observed_results_json(json_str)

def test_invalid_status_fails():
    d = _valid_dict()
    d["result_status"] = "INVALID"
    with pytest.raises(ValueError, match="Invalid result_status"):
        parse_observed_results_json(json.dumps([d]))

def test_invalid_source_fails():
    d = _valid_dict()
    d["source"] = "INVALID"
    with pytest.raises(ValueError, match="Invalid source"):
        parse_observed_results_csv(_to_csv([d]))

def test_duplicate_result_id_fails():
    json_str = json.dumps([_valid_dict("res_1"), _valid_dict("res_1")])
    with pytest.raises(ValueError, match="Duplicate result_id"):
        parse_observed_results_json(json_str)

def test_empty_content_returns_empty_list():
    assert parse_observed_results_csv("   ") == []
    assert parse_observed_results_json("   ") == []

def test_huge_payload_fails():
    huge_csv = "result_id\n" + ("x" * (MAX_PAYLOAD_SIZE + 10))
    with pytest.raises(ValueError, match="Payload size exceeds"):
        parse_observed_results_csv(huge_csv)

def test_operational_language_fails():
    d = _valid_dict()
    d["notes"] = "This is a gain."
    with pytest.raises(ValueError, match="Operational language blocked"):
        parse_observed_results_json(json.dumps([d]))

def test_url_source_ref_fails():
    with pytest.raises(ValueError, match="URLs are not allowed"):
        parse_observed_results_csv(_to_csv([_valid_dict()]), source_ref="https://example.com/data.csv")
