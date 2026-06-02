import pytest
from src.edgehunter.core.advanced_calibration_metrics import calculate_segment_calibration_metrics

def test_calculates_sample_size_and_minimum_met():
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 15,
            "resolved_total": 0,
            "classifications": [{"calibrated_assertiveness": 0.5}],
            "outcomes": []
        }]
    }
    res = calculate_segment_calibration_metrics(data, min_sample_size=10)
    metrics = res["metrics_by_segment"][0]
    assert metrics["sample_size"] == 15
    assert metrics["minimum_sample_met"] is True

def test_calculates_minimum_sample_not_met():
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 5,
            "resolved_total": 0,
            "classifications": [],
            "outcomes": []
        }]
    }
    res = calculate_segment_calibration_metrics(data, min_sample_size=10)
    assert res["metrics_by_segment"][0]["minimum_sample_met"] is False

def test_calculates_green_confirmation():
    # GREEN_SIM + POSITIVE_OBSERVED = confirmação green
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 1,
            "resolved_total": 1,
            "classifications": [
                {"signal_id": "1", "simulation_label": "GREEN_SIM", "calibrated_assertiveness": 0.8}
            ],
            "outcomes": [
                {"signal_id": "1", "result_status": "POSITIVE_OBSERVED"}
            ]
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["confirmed_total"] == 1
    assert metrics["not_confirmed_total"] == 0
    assert metrics["confirmation_rate"] == 1.0
    assert metrics["green_confirmation_rate"] == 1.0
    assert metrics["green_not_confirmed_rate"] == 0.0

def test_calculates_green_not_confirmed():
    # GREEN_SIM + NEGATIVE_OBSERVED = não confirmação green
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 1,
            "resolved_total": 1,
            "classifications": [
                {"signal_id": "1", "simulation_label": "GREEN_SIM", "calibrated_assertiveness": 0.8}
            ],
            "outcomes": [
                {"signal_id": "1", "result_status": "NEGATIVE_OBSERVED"}
            ]
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["confirmed_total"] == 0
    assert metrics["not_confirmed_total"] == 1
    assert metrics["confirmation_rate"] == 0.0
    assert metrics["green_not_confirmed_rate"] == 1.0
    assert metrics["false_positive_rate"] == 1.0

def test_calculates_red_rejection_confirmation():
    # RED_SIM + NEGATIVE_OBSERVED = rejeição técnica confirmada
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 1,
            "resolved_total": 1,
            "classifications": [
                {"signal_id": "1", "simulation_label": "RED_SIM", "calibrated_assertiveness": 0.8}
            ],
            "outcomes": [
                {"signal_id": "1", "result_status": "NEGATIVE_OBSERVED"}
            ]
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["confirmed_total"] == 1
    assert metrics["red_rejection_confirmation_rate"] == 1.0

def test_calculates_red_missed_positive():
    # RED_SIM + POSITIVE_OBSERVED = cenário positivo não capturado
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 1,
            "resolved_total": 1,
            "classifications": [
                {"signal_id": "1", "simulation_label": "RED_SIM", "calibrated_assertiveness": 0.8}
            ],
            "outcomes": [
                {"signal_id": "1", "result_status": "POSITIVE_OBSERVED"}
            ]
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["not_confirmed_total"] == 1
    assert metrics["red_missed_positive_rate"] == 1.0
    assert metrics["false_negative_rate"] == 1.0

def test_calculates_averages():
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 2,
            "resolved_total": 0,
            "classifications": [
                {"calibrated_assertiveness": 0.6, "confidence": 0.8},
                {"calibrated_assertiveness": 0.8, "confidence": 0.9}
            ],
            "outcomes": []
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["average_calibrated_assertiveness"] == pytest.approx(0.7)
    assert metrics["average_confidence"] == pytest.approx(0.85)

def test_division_by_zero_returns_zero():
    data = {
        "segments": [{
            "segment_key": "dummy",
            "sample_size": 0,
            "resolved_total": 0,
            "classifications": [],
            "outcomes": []
        }]
    }
    res = calculate_segment_calibration_metrics(data)
    metrics = res["metrics_by_segment"][0]
    assert metrics["confirmation_rate"] == 0.0
    assert metrics["green_confirmation_rate"] == 0.0
    assert metrics["average_calibrated_assertiveness"] == 0.0

def test_min_sample_size_invalid_fails():
    with pytest.raises(ValueError, match="min_sample_size must be >= 1"):
        calculate_segment_calibration_metrics({}, min_sample_size=0)

def test_operational_language_fails():
    with pytest.raises(ValueError, match="Operational language detected"):
        calculate_segment_calibration_metrics({"segments": [{"notes": "aposta ganha"}]})

def test_deterministic_output_and_safe_flags():
    data = {"segments": [{"segment_key": "A"}]}
    res = calculate_segment_calibration_metrics(data)
    assert res["is_simulated"] is True
    assert res["actionable"] is False
    assert res["metrics_by_segment"][0]["actionable"] is False
