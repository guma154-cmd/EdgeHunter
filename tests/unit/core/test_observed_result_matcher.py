import pytest
from src.edgehunter.core.observed_result_matcher import match_observed_results_to_classifications


def _result(rid="r1", sid="", cid="", oid="", mid="", notes=""):
    return {
        "result_id": rid,
        "signal_id": sid,
        "classification_id": cid,
        "opportunity_id": oid,
        "match_id": mid,
        "notes": notes
    }


def _class(cid="c1", sid="", oid="", mid="", extra=""):
    return {
        "classification_id": cid,
        "signal_id": sid,
        "opportunity_id": oid,
        "match_id": mid,
        "extra": extra
    }


def test_match_by_signal_id():
    results = [_result(rid="r1", sid="sig_1")]
    classifications = [_class(cid="c1", sid="sig_1")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1
    assert out["summary"]["unmatched_results_total"] == 0
    assert out["matched"][0]["result"]["result_id"] == "r1"
    assert out["matched"][0]["classification"]["classification_id"] == "c1"


def test_match_fallback_classification_id():
    results = [_result(rid="r1", cid="c1")]
    classifications = [_class(cid="c1")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1
    assert out["summary"]["unmatched_results_total"] == 0


def test_match_fallback_opportunity_id():
    results = [_result(rid="r1", oid="o1")]
    classifications = [_class(cid="c1", oid="o1")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1


def test_match_fallback_match_id():
    results = [_result(rid="r1", mid="m1")]
    classifications = [_class(cid="c1", mid="m1")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1


def test_unmatched_results_and_classifications():
    results = [_result(rid="r1", sid="sig_1"), _result(rid="r2", sid="sig_UNKNOWN")]
    classifications = [_class(cid="c1", sid="sig_1"), _class(cid="c2", sid="sig_OTHER")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1
    assert out["summary"]["unmatched_results_total"] == 1
    assert out["summary"]["unmatched_classifications_total"] == 1
    assert out["unmatched_results"][0]["result_id"] == "r2"
    assert out["unmatched_classifications"][0]["classification_id"] == "c2"


def test_duplicates_detected():
    # Two results pointing to same signal_id
    results = [_result(rid="r1", sid="sig_1"), _result(rid="r2", sid="sig_1")]
    classifications = [_class(cid="c1", sid="sig_1")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1
    assert out["summary"]["duplicates_total"] == 1
    assert out["duplicates"][0]["result"]["result_id"] == "r2"
    assert "already matched" in out["duplicates"][0]["error"]


def test_input_not_mutated():
    results = [_result(rid="r1", sid="sig_1")]
    classifications = [_class(cid="c1", sid="sig_1")]
    
    match_observed_results_to_classifications(results, classifications)
    assert len(results) == 1
    assert len(classifications) == 1
    assert results[0]["result_id"] == "r1"


def test_priority_respected():
    # Result has signal_id and match_id.
    # Class1 matches match_id, Class2 matches signal_id.
    # signal_id has higher priority, so it should match Class2.
    results = [_result(rid="r1", sid="sig_2", mid="mat_1")]
    classifications = [_class(cid="c1", mid="mat_1"), _class(cid="c2", sid="sig_2")]
    
    out = match_observed_results_to_classifications(results, classifications)
    assert out["summary"]["matched_total"] == 1
    assert out["matched"][0]["classification"]["classification_id"] == "c2"


def test_flags_safe():
    results = []
    classifications = []
    out = match_observed_results_to_classifications(results, classifications)
    assert out["is_simulated"] is True
    assert out["actionable"] is False


def test_operational_language_fails():
    results = [_result(rid="r1", notes="stake 100")]
    classifications = []
    
    with pytest.raises(ValueError, match="Operational language blocked"):
        match_observed_results_to_classifications(results, classifications)
