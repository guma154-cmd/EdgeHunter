import pytest
from src.edgehunter.core.advanced_threshold_suggestion import generate_advanced_threshold_suggestion
from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel, TrendStatus

def get_dummy_report(scores=None, metrics=None):
    if scores is None:
        scores = []
    if metrics is None:
        metrics = []
    return {
        "scores": scores,
        "segments_metrics": metrics
    }

def test_require_more_sample():
    report = get_dummy_report(scores=[{"sample_size": 10}])
    res = generate_advanced_threshold_suggestion(report, min_sample_size=30)
    assert res["suggested_action"] == "REQUIRE_MORE_SAMPLE"

def test_keep_threshold_in_balanced_scenario():
    scores = [
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH},
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_MEDIUM}
    ]
    metrics = [{"false_positive_rate": 0.05, "trend_status": TrendStatus.STABLE, "segment_key": {"simulation_label": "GREEN_SIM"}}]
    report = get_dummy_report(scores, metrics)
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.70)
    assert res["suggested_action"] == "KEEP_THRESHOLD"
    assert res["suggested_threshold"] == 0.70

def test_raise_threshold_with_many_weak_segments():
    scores = [
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_LOW},
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_LOW}
    ]
    report = get_dummy_report(scores)
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.70)
    assert res["suggested_action"] == "RAISE_THRESHOLD"
    assert res["suggested_threshold"] > 0.70

def test_lower_threshold_with_missed_positive_and_green_reliable():
    scores = [
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH},
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH}
    ]
    metrics = [
        {"false_positive_rate": 0.0, "segment_key": {"simulation_label": "GREEN_SIM"}, "trend_status": TrendStatus.STABLE},
        {"false_negative_rate": 0.20, "segment_key": {"simulation_label": "RED_SIM"}, "trend_status": TrendStatus.STABLE}
    ]
    report = get_dummy_report(scores, metrics)
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.70)
    assert res["suggested_action"] == "LOWER_THRESHOLD"
    assert res["suggested_threshold"] < 0.70

def test_upper_bound_095_respected():
    scores = [
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_LOW},
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_LOW}
    ]
    report = get_dummy_report(scores)
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.95)
    assert res["suggested_action"] == "KEEP_THRESHOLD"
    assert res["suggested_threshold"] == 0.95

def test_lower_bound_050_respected():
    scores = [
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH},
        {"sample_size": 20, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH}
    ]
    metrics = [
        {"false_positive_rate": 0.0, "segment_key": {"simulation_label": "GREEN_SIM"}, "trend_status": TrendStatus.STABLE},
        {"false_negative_rate": 0.20, "segment_key": {"simulation_label": "RED_SIM"}, "trend_status": TrendStatus.STABLE}
    ]
    report = get_dummy_report(scores, metrics)
    res = generate_advanced_threshold_suggestion(report, current_threshold=0.50)
    assert res["suggested_action"] == "KEEP_THRESHOLD"
    assert res["suggested_threshold"] == 0.50

def test_invalid_current_threshold_fails():
    with pytest.raises(ValueError, match="current_threshold must be between 0.50 and 0.95"):
        generate_advanced_threshold_suggestion(get_dummy_report(), current_threshold=0.99)
    with pytest.raises(ValueError, match="current_threshold must be between 0.50 and 0.95"):
        generate_advanced_threshold_suggestion(get_dummy_report(), current_threshold=0.40)

def test_invalid_min_sample_size_fails():
    with pytest.raises(ValueError, match="min_sample_size must be >= 1"):
        generate_advanced_threshold_suggestion(get_dummy_report(), min_sample_size=0)

def test_auto_apply_always_false():
    report = get_dummy_report([{"sample_size": 40, "reliability_level": ReliabilityLevel.RELIABILITY_HIGH}])
    res = generate_advanced_threshold_suggestion(report)
    assert res["auto_apply"] is False
    assert res["is_simulated"] is True
    assert res["actionable"] is False

def test_operational_language_fails():
    report = get_dummy_report([{"sample_size": 40, "notes": "lucro incrivel"}])
    with pytest.raises(ValueError, match="Operational language detected"):
        generate_advanced_threshold_suggestion(report)
