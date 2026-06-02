import pytest
from src.edgehunter.core.advanced_calibration_segments import segment_historical_calibration_data
from src.edgehunter.core.advanced_calibration_metrics import calculate_segment_calibration_metrics
from src.edgehunter.core.advanced_calibration_trends import detect_segment_trends
from src.edgehunter.core.advanced_reliability_score import calculate_reliability_scores
from src.edgehunter.core.advanced_threshold_suggestion import generate_advanced_threshold_suggestion
from src.edgehunter.core.dashboard_advanced_calibration import generate_advanced_calibration_dashboard
from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel

def test_adversarial_segmentation_forbidden_terms():
    metrics = [{"notes": "grande lucro", "source": "A"}]
    with pytest.raises(ValueError, match="Operational language detected"):
        segment_historical_calibration_data(metrics, [])

def test_adversarial_segmentation_forbidden_terms_outcomes():
    metrics = [{"source": "A"}]
    outcomes = [{"notes": "aposta maxima"}]
    with pytest.raises(ValueError, match="Operational language detected"):
        segment_historical_calibration_data(metrics, outcomes)

def test_adversarial_metrics_forbidden_terms():
    data = {"segments": [{"notes": "gain infinito"}]}
    with pytest.raises(ValueError, match="Operational language detected"):
        calculate_segment_calibration_metrics(data)

def test_adversarial_trends_forbidden_terms():
    curr = {"notes": "wager alto"}
    with pytest.raises(ValueError, match="Operational language detected"):
        detect_segment_trends(curr)

def test_adversarial_score_forbidden_terms():
    metrics = {"sample_size": 10, "notes": "kelly_criterion = 0.5"}
    with pytest.raises(ValueError, match="Operational language detected"):
        calculate_reliability_scores(metrics)

def test_adversarial_threshold_forbidden_terms():
    report = {"scores": [{"notes": "lucro maximo"}]}
    with pytest.raises(ValueError, match="Operational language detected"):
        generate_advanced_threshold_suggestion(report)

def test_adversarial_dashboard_forbidden_terms():
    with pytest.raises(ValueError, match="Operational language detected"):
        generate_advanced_calibration_dashboard([{"notes": "aposta ganha"}], [])

def test_adversarial_dashboard_auto_apply_leak():
    res = generate_advanced_calibration_dashboard([], [])
    # MUST never auto apply
    assert res["threshold_suggestion"]["auto_apply"] is False
    assert res["actionable"] is False
    assert res["is_simulated"] is True

def test_adversarial_threshold_bounds():
    report = {"scores": [], "segments_metrics": []}
    # It must clamp between 0.50 and 0.95
    # Let's force a raise threshold case by passing low scores
    report["scores"] = [{"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_LOW}] * 10
    report["scores"].extend([{"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH}])
    
    # Starting at 0.95
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.95, min_sample_size=1)
    
    # It would want to raise, but must clamp at 0.95
    assert res["suggested_threshold"] == 0.95
    assert res["suggested_action"] == "KEEP_THRESHOLD"

def test_adversarial_segmentation_missing_keys():
    # Should not crash on empty dictionaries
    res = segment_historical_calibration_data([{}], [{}])
    assert "UNKNOWN" in str(res)
    assert res["global_totals"]["sample_size"] == 1
    assert res["global_totals"]["unresolved_total"] == 1

def test_adversarial_metrics_division_by_zero():
    # Force empty classifications and outcomes
    data = {
        "segments": [{
            "segment_key": "empty",
            "sample_size": 0,
            "resolved_total": 0,
            "classifications": [],
            "outcomes": []
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    seg = res["metrics_by_segment"][0]
    assert seg["confirmation_rate"] == 0.0
    assert seg["false_positive_rate"] == 0.0
