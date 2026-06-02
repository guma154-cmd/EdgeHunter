import pytest
from src.edgehunter.core.advanced_calibration_models import (
    ReliabilityLevel, TrendStatus, CalibrationSegmentKey, 
    CalibrationSegmentMetrics, ReliabilityScore, AdvancedCalibrationReport
)

def test_create_reliability_level_valid():
    assert ReliabilityLevel("RELIABILITY_HIGH") == ReliabilityLevel.RELIABILITY_HIGH
    assert ReliabilityLevel("RELIABILITY_INSUFFICIENT_SAMPLE") == ReliabilityLevel.RELIABILITY_INSUFFICIENT_SAMPLE

def test_create_trend_status_valid():
    assert TrendStatus("IMPROVING") == TrendStatus.IMPROVING
    assert TrendStatus("VOLATILE") == TrendStatus.VOLATILE

def test_create_calibration_segment_key_valid():
    key = CalibrationSegmentKey(
        source="LOCAL_CSV",
        detection_method="poisson",
        simulation_label="GREEN_SIM",
        market="MATCH_ODDS",
        selection="HOME",
        assertiveness_bucket="0.70-0.79"
    )
    assert key.source == "LOCAL_CSV"
    
def test_create_calibration_segment_metrics_valid():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    metrics = CalibrationSegmentMetrics(
        segment_key=key,
        sample_size=100,
        resolved_total=90,
        confirmed_total=60,
        not_confirmed_total=30,
        unresolved_total=10,
        invalidated_total=0,
        confirmation_rate=0.66,
        not_confirmed_rate=0.33,
        average_calibrated_assertiveness=0.75,
        average_confidence=0.80,
        false_positive_rate=0.10,
        false_negative_rate=0.05,
        trend_status=TrendStatus.IMPROVING,
        reliability_level=ReliabilityLevel.RELIABILITY_HIGH
    )
    assert metrics.sample_size == 100
    assert metrics.is_simulated is True
    assert metrics.actionable is False

def test_create_reliability_score_valid():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    score = ReliabilityScore(
        score_id="SC-1",
        segment_key=key,
        score=0.85,
        reliability_level=ReliabilityLevel.RELIABILITY_HIGH,
        confidence=0.90,
        sample_size=150,
        reason="Consistent performance"
    )
    assert score.score == 0.85

def test_create_advanced_calibration_report_valid():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    score = ReliabilityScore("SC-1", key, 0.85, ReliabilityLevel.RELIABILITY_HIGH, 0.90, 150, "ok")
    metrics = CalibrationSegmentMetrics(key, 100, 90, 60, 30, 10, 0, 0.66, 0.33, 0.75, 0.80, 0.1, 0.05, TrendStatus.IMPROVING, ReliabilityLevel.RELIABILITY_HIGH)
    report = AdvancedCalibrationReport("REP-1", [score], [metrics])
    assert len(report.scores) == 1

def test_score_less_than_0_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="score must be between 0.0 and 1.0"):
        ReliabilityScore("SC-1", key, -0.1, ReliabilityLevel.RELIABILITY_HIGH, 0.90, 150, "ok")

def test_score_greater_than_1_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="score must be between 0.0 and 1.0"):
        ReliabilityScore("SC-1", key, 1.1, ReliabilityLevel.RELIABILITY_HIGH, 0.90, 150, "ok")

def test_confidence_less_than_0_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, -0.1, 150, "ok")

def test_confidence_greater_than_1_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 1.1, 150, "ok")

def test_sample_size_negative_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="sample_size must be >= 0"):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, -1, "ok")

def test_string_mandatory_empty_fails():
    with pytest.raises(ValueError, match="source cannot be empty"):
        CalibrationSegmentKey("", "METH", "LAB", "MKT", "SEL", "BKT")

def test_actionable_true_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(Exception):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, 10, "ok", actionable=True)

def test_bet_placed_true_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(Exception):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, 10, "ok", bet_placed=True)

def test_alerted_true_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(Exception):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, 10, "ok", alerted=True)

def test_operational_language_fails():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(ValueError, match="Operational language detected"):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, 10, "Isso é uma ótima aposta")

def test_forbidden_fields_fail():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    with pytest.raises(Exception):
        ReliabilityScore("SC-1", key, 0.8, ReliabilityLevel.RELIABILITY_HIGH, 0.9, 10, "ok", stake=100)

def test_to_dict_deterministic():
    key = CalibrationSegmentKey("SRC", "METH", "LAB", "MKT", "SEL", "BKT")
    score = ReliabilityScore("SC-1", key, 0.85, ReliabilityLevel.RELIABILITY_HIGH, 0.90, 150, "ok")
    d1 = score.to_dict()
    d2 = score.to_dict()
    assert d1 == d2
    assert d1["reliability_level"] == "RELIABILITY_HIGH"
    assert "is_simulated" in d1

# Verify constraints: sem SQLite, sem rede, sem Gemini, sem Telegram/scheduler, sem AutoEvolution, sem execução financeira.
