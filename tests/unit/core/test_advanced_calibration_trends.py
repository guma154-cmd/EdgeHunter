import pytest
from src.edgehunter.core.advanced_calibration_trends import detect_segment_trends
from src.edgehunter.core.advanced_calibration_models import TrendStatus

def test_detects_improving():
    # conf subiu >= 0.05 e erro não subiu
    curr = {"sample_size": 20, "confirmation_rate": 0.60, "false_positive_rate": 0.10}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.15}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.IMPROVING

def test_detects_declining_by_conf():
    # conf caiu >= 0.05
    curr = {"sample_size": 20, "confirmation_rate": 0.40, "false_positive_rate": 0.10}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.DECLINING

def test_detects_declining_by_err():
    # err subiu >= 0.05
    curr = {"sample_size": 20, "confirmation_rate": 0.50, "false_positive_rate": 0.20}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.DECLINING

def test_detects_volatile():
    # conf subiu e err subiu
    curr = {"sample_size": 20, "confirmation_rate": 0.52, "false_positive_rate": 0.12}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.VOLATILE

def test_detects_stable():
    # conf subiu pouco, err caiu
    curr = {"sample_size": 20, "confirmation_rate": 0.52, "false_positive_rate": 0.08}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.STABLE

def test_detects_insufficient_sample():
    curr = {"sample_size": 5, "confirmation_rate": 0.60, "false_positive_rate": 0.10}
    prev = {"confirmation_rate": 0.50, "false_positive_rate": 0.15}
    res = detect_segment_trends(curr, prev)
    assert res["trend_status"] == TrendStatus.INSUFFICIENT_SAMPLE

def test_no_previous_returns_stable():
    curr = {"sample_size": 20, "confirmation_rate": 0.60, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, None)
    assert res["trend_status"] == TrendStatus.STABLE
    assert "No previous period" in res["reason"]

def test_min_sample_size_invalid_fails():
    with pytest.raises(ValueError, match="min_sample_size must be >= 1"):
        detect_segment_trends({}, min_sample_size=0)

def test_deltas_invalid_fails():
    with pytest.raises(ValueError, match="deltas must be strictly positive"):
        detect_segment_trends({}, improvement_delta=0.0)
    with pytest.raises(ValueError, match="deltas must be strictly positive"):
        detect_segment_trends({}, degradation_delta=-0.1)

def test_deterministic_output_and_safe_flags():
    curr = {"sample_size": 20, "confirmation_rate": 0.60, "false_positive_rate": 0.10}
    res = detect_segment_trends(curr, None)
    assert res["is_simulated"] is True
    assert res["actionable"] is False

def test_operational_language_fails():
    curr = {"sample_size": 20, "notes": "lucro máximo"}
    with pytest.raises(ValueError, match="Operational language detected"):
        detect_segment_trends(curr, None)
