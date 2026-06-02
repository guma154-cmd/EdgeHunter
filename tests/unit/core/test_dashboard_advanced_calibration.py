import pytest
from src.edgehunter.core.dashboard_advanced_calibration import generate_advanced_calibration_dashboard
from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel

def test_generate_advanced_calibration_dashboard_full_flow():
    curr_metrics = [
        {"signal_id": "1", "source": "S1", "detection_method": "M1", "simulation_label": "GREEN_SIM", "market": "MKT", "selection": "SEL", "calibrated_assertiveness": 0.8, "confidence": 0.9}
    ] * 20
    curr_outcomes = [
        {"signal_id": "1", "result_status": "POSITIVE_OBSERVED"}
    ] * 20
    
    prev_metrics = [
        {"signal_id": "2", "source": "S1", "detection_method": "M1", "simulation_label": "GREEN_SIM", "market": "MKT", "selection": "SEL", "calibrated_assertiveness": 0.7, "confidence": 0.8}
    ] * 20
    prev_outcomes = [
        {"signal_id": "2", "result_status": "NEGATIVE_OBSERVED"}
    ] * 20

    res = generate_advanced_calibration_dashboard(
        curr_metrics, curr_outcomes, prev_metrics, prev_outcomes, min_sample_size=10
    )
    
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert len(res["scores"]) == 1
    assert res["scores"][0]["reliability_level"] == ReliabilityLevel.RELIABILITY_HIGH
    
    # prev had 100% false pos, curr has 0% false pos (100% positive) -> should be IMPROVING
    # threshold suggestion should be LOWER_THRESHOLD or KEEP_THRESHOLD
    assert res["threshold_suggestion"]["suggested_action"] in ["KEEP_THRESHOLD", "LOWER_THRESHOLD"]
    assert res["threshold_suggestion"]["auto_apply"] is False

def test_generate_dashboard_no_previous_data():
    curr_metrics = [
        {"signal_id": "1", "source": "S1", "detection_method": "M1", "simulation_label": "GREEN_SIM", "market": "MKT", "selection": "SEL", "calibrated_assertiveness": 0.8, "confidence": 0.9}
    ] * 15
    curr_outcomes = [
        {"signal_id": "1", "result_status": "POSITIVE_OBSERVED"}
    ] * 15

    res = generate_advanced_calibration_dashboard(curr_metrics, curr_outcomes, min_sample_size=10)
    assert len(res["scores"]) == 1
    assert res["scores"][0]["reliability_level"] == ReliabilityLevel.RELIABILITY_HIGH
    assert "threshold_suggestion" in res

def test_generate_dashboard_insufficient_sample():
    curr_metrics = [{"signal_id": "1", "source": "S1", "detection_method": "M1", "simulation_label": "GREEN_SIM", "market": "MKT", "selection": "SEL", "calibrated_assertiveness": 0.8, "confidence": 0.9}]
    curr_outcomes = [{"signal_id": "1", "result_status": "POSITIVE_OBSERVED"}]
    
    res = generate_advanced_calibration_dashboard(curr_metrics, curr_outcomes, min_sample_size=10)
    assert res["scores"][0]["reliability_level"] == ReliabilityLevel.RELIABILITY_INSUFFICIENT_SAMPLE
    assert res["threshold_suggestion"]["suggested_action"] == "REQUIRE_MORE_SAMPLE"

def test_operational_language_fails():
    curr_metrics = [{"signal_id": "1", "notes": "lucro máximo"}]
    with pytest.raises(ValueError, match="Operational language detected"):
        generate_advanced_calibration_dashboard(curr_metrics, [], min_sample_size=10)
