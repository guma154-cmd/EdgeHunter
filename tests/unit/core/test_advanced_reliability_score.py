import pytest
from src.edgehunter.core.advanced_reliability_score import calculate_reliability_scores
from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel, TrendStatus, CalibrationSegmentKey

def get_dummy_key():
    return CalibrationSegmentKey("S", "M", "L", "MKT", "SEL", "0.70-0.79")

def test_calculates_high_score():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.90,
        "average_calibrated_assertiveness": 0.85,
        "average_confidence": 0.90,
        "not_confirmed_rate": 0.05,
        "false_positive_rate": 0.05
    }
    trend = {"trend_status": TrendStatus.IMPROVING}
    res = calculate_reliability_scores(metrics, trend)
    assert res["reliability_level"] == ReliabilityLevel.RELIABILITY_HIGH
    assert res["score"] >= 0.75

def test_calculates_medium_score():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.60,
        "average_calibrated_assertiveness": 0.70,
        "average_confidence": 0.70,
        "not_confirmed_rate": 0.20,
        "false_positive_rate": 0.10
    }
    trend = {"trend_status": TrendStatus.STABLE}
    res = calculate_reliability_scores(metrics, trend)
    assert res["reliability_level"] == ReliabilityLevel.RELIABILITY_MEDIUM
    assert 0.55 <= res["score"] < 0.75

def test_calculates_low_score():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.30,
        "average_calibrated_assertiveness": 0.50,
        "average_confidence": 0.50,
        "not_confirmed_rate": 0.50,
        "false_positive_rate": 0.30
    }
    trend = {"trend_status": TrendStatus.DECLINING}
    res = calculate_reliability_scores(metrics, trend)
    assert res["reliability_level"] == ReliabilityLevel.RELIABILITY_LOW
    assert res["score"] < 0.55

def test_insufficient_sample_returns_specific_level():
    metrics = {"sample_size": 5, "segment_key": get_dummy_key()}
    res = calculate_reliability_scores(metrics)
    assert res["reliability_level"] == ReliabilityLevel.RELIABILITY_INSUFFICIENT_SAMPLE
    assert res["score"] == 0.0

def test_declining_penalizes():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.60,
        "average_calibrated_assertiveness": 0.70,
        "average_confidence": 0.70,
        "not_confirmed_rate": 0.10,
        "false_positive_rate": 0.05
    }
    res_stable = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.STABLE})
    res_declining = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.DECLINING})
    assert res_declining["score"] < res_stable["score"]

def test_volatile_penalizes():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.60,
        "average_calibrated_assertiveness": 0.70,
        "average_confidence": 0.70,
        "not_confirmed_rate": 0.10,
        "false_positive_rate": 0.05
    }
    res_stable = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.STABLE})
    res_volatile = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.VOLATILE})
    assert res_volatile["score"] < res_stable["score"]

def test_not_confirmed_rate_penalizes():
    metrics1 = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.60,
        "average_calibrated_assertiveness": 0.70,
        "average_confidence": 0.70,
        "not_confirmed_rate": 0.10,
        "false_positive_rate": 0.05
    }
    metrics2 = dict(metrics1)
    metrics2["not_confirmed_rate"] = 0.35
    res1 = calculate_reliability_scores(metrics1)
    res2 = calculate_reliability_scores(metrics2)
    assert res2["score"] < res1["score"]

def test_false_positive_rate_penalizes():
    metrics1 = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.60,
        "average_calibrated_assertiveness": 0.70,
        "average_confidence": 0.70,
        "not_confirmed_rate": 0.10,
        "false_positive_rate": 0.05
    }
    metrics2 = dict(metrics1)
    metrics2["false_positive_rate"] = 0.25
    res1 = calculate_reliability_scores(metrics1)
    res2 = calculate_reliability_scores(metrics2)
    assert res2["score"] < res1["score"]

def test_score_never_below_zero():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 0.0,
        "average_calibrated_assertiveness": 0.0,
        "average_confidence": 0.0,
        "not_confirmed_rate": 1.0,
        "false_positive_rate": 1.0
    }
    res = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.DECLINING})
    assert res["score"] == 0.0

def test_score_never_above_one():
    metrics = {
        "segment_key": get_dummy_key(),
        "sample_size": 50,
        "confirmation_rate": 1.0,
        "average_calibrated_assertiveness": 1.0,
        "average_confidence": 1.0,
        "not_confirmed_rate": 0.0,
        "false_positive_rate": 0.0
    }
    res = calculate_reliability_scores(metrics, {"trend_status": TrendStatus.IMPROVING})
    assert res["score"] == 1.0

def test_min_sample_size_fails():
    with pytest.raises(ValueError):
        calculate_reliability_scores({}, min_sample_size=0)

def test_operational_language_fails():
    with pytest.raises(ValueError, match="Operational language detected"):
        calculate_reliability_scores({"notes": "grande aposta", "sample_size": 10})

def test_deterministic_and_safe_flags():
    metrics = {"sample_size": 50, "segment_key": get_dummy_key()}
    res = calculate_reliability_scores(metrics)
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert "bet" not in res["reason"].lower()
