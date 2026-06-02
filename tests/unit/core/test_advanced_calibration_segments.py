import pytest
from src.edgehunter.core.advanced_calibration_segments import segment_historical_calibration_data, get_bucket_label

def test_bucket_size_invalid_fails():
    with pytest.raises(ValueError, match="bucket_size must be strictly between 0.0 and 1.0"):
        segment_historical_calibration_data([], [], bucket_size=1.0)
    with pytest.raises(ValueError, match="bucket_size must be strictly between 0.0 and 1.0"):
        segment_historical_calibration_data([], [], bucket_size=-0.1)

def test_assertiveness_out_of_bounds_fails():
    with pytest.raises(ValueError, match="assertiveness must be between 0.0 and 1.0"):
        get_bucket_label(1.1, 0.1)
    with pytest.raises(ValueError, match="assertiveness must be between 0.0 and 1.0"):
        get_bucket_label(-0.1, 0.1)

def test_segment_by_source():
    cls = [
        {"source": "SRC1", "calibrated_assertiveness": 0.5},
        {"source": "SRC2", "calibrated_assertiveness": 0.5}
    ]
    res = segment_historical_calibration_data(cls, [])
    assert res["total_segments"] == 2
    keys = [s["segment_key"].source for s in res["segments"]]
    assert "SRC1" in keys
    assert "SRC2" in keys

def test_segment_by_detection_method():
    cls = [
        {"detection_method": "M1", "calibrated_assertiveness": 0.5},
        {"detection_method": "M2", "calibrated_assertiveness": 0.5}
    ]
    res = segment_historical_calibration_data(cls, [])
    assert res["total_segments"] == 2
    keys = [s["segment_key"].detection_method for s in res["segments"]]
    assert "M1" in keys
    assert "M2" in keys

def test_segment_by_simulation_label():
    cls = [
        {"simulation_label": "GREEN_SIM", "calibrated_assertiveness": 0.5},
        {"simulation_label": "RED_SIM", "calibrated_assertiveness": 0.5}
    ]
    res = segment_historical_calibration_data(cls, [])
    keys = [s["segment_key"].simulation_label for s in res["segments"]]
    assert "GREEN_SIM" in keys
    assert "RED_SIM" in keys

def test_segment_by_market():
    cls = [
        {"market": "MATCH_ODDS", "calibrated_assertiveness": 0.5},
        {"market": "OVER_UNDER", "calibrated_assertiveness": 0.5}
    ]
    res = segment_historical_calibration_data(cls, [])
    keys = [s["segment_key"].market for s in res["segments"]]
    assert "MATCH_ODDS" in keys
    assert "OVER_UNDER" in keys

def test_segment_by_selection():
    cls = [
        {"selection": "HOME", "calibrated_assertiveness": 0.5},
        {"selection": "AWAY", "calibrated_assertiveness": 0.5}
    ]
    res = segment_historical_calibration_data(cls, [])
    keys = [s["segment_key"].selection for s in res["segments"]]
    assert "HOME" in keys
    assert "AWAY" in keys

def test_segment_by_assertiveness_bucket():
    cls = [
        {"calibrated_assertiveness": 0.15},
        {"calibrated_assertiveness": 0.85}
    ]
    res = segment_historical_calibration_data(cls, [], bucket_size=0.10)
    keys = [s["segment_key"].assertiveness_bucket for s in res["segments"]]
    assert "0.10-0.19" in keys
    assert "0.80-0.89" in keys

def test_classification_without_outcome_is_unresolved():
    cls = [{"signal_id": "SIG1", "calibrated_assertiveness": 0.5}]
    res = segment_historical_calibration_data(cls, [])
    assert res["global_totals"]["unresolved_total"] == 1
    assert res["global_totals"]["resolved_total"] == 0

def test_outcome_invalidated_is_counted():
    cls = [{"signal_id": "SIG1", "calibrated_assertiveness": 0.5}]
    out = [{"signal_id": "SIG1", "result_status": "INVALIDATED"}]
    res = segment_historical_calibration_data(cls, out)
    assert res["global_totals"]["invalidated_total"] == 1

def test_link_by_signal_id():
    cls = [{"signal_id": "SIG1", "calibrated_assertiveness": 0.5}]
    out = [{"signal_id": "SIG1", "result_status": "POSITIVE_OBSERVED"}]
    res = segment_historical_calibration_data(cls, out)
    assert res["global_totals"]["resolved_total"] == 1

def test_fallback_link_by_classification_id():
    cls = [{"classification_id": "CLS1", "calibrated_assertiveness": 0.5}]
    out = [{"classification_id": "CLS1", "result_status": "POSITIVE_OBSERVED"}]
    res = segment_historical_calibration_data(cls, out)
    assert res["global_totals"]["resolved_total"] == 1

def test_fallback_link_by_opportunity_id():
    cls = [{"opportunity_id": "OPP1", "calibrated_assertiveness": 0.5}]
    out = [{"opportunity_id": "OPP1", "result_status": "POSITIVE_OBSERVED"}]
    res = segment_historical_calibration_data(cls, out)
    assert res["global_totals"]["resolved_total"] == 1

def test_deterministic_output():
    cls = [
        {"source": "S2", "calibrated_assertiveness": 0.5},
        {"source": "S1", "calibrated_assertiveness": 0.5}
    ]
    res1 = segment_historical_calibration_data(cls, [])
    res2 = segment_historical_calibration_data(cls, [])
    assert [s["segment_key"].source for s in res1["segments"]] == [s["segment_key"].source for s in res2["segments"]]

def test_input_not_mutated():
    cls = [{"source": "S1", "calibrated_assertiveness": 0.5}]
    out = [{"signal_id": "S1", "result_status": "POSITIVE_OBSERVED"}]
    cls_copy = list(cls)
    out_copy = list(out)
    segment_historical_calibration_data(cls, out)
    assert cls == cls_copy
    assert out == out_copy

def test_safe_flags():
    res = segment_historical_calibration_data([], [])
    assert res["is_simulated"] is True
    assert res["actionable"] is False

def test_operational_language_fails():
    cls = [{"source": "betting_bot", "calibrated_assertiveness": 0.5, "notes": "lucro garantido aposta"}]
    with pytest.raises(ValueError, match="Operational language detected"):
        segment_historical_calibration_data(cls, [])
