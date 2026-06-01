import pytest
from src.edgehunter.core.simulated_signal_learning_report import generate_simulated_signal_learning_report

def _get_base_classification(label="GREEN_SIM", signal_id="sig-1", ca=0.8, conf=0.8):
    return {
        "classification_id": "c1",
        "signal_id": signal_id,
        "opportunity_id": "opp1",
        "simulation_label": label,
        "calibrated_assertiveness": ca,
        "confidence": conf,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True
    }

def test_empty_report():
    report = generate_simulated_signal_learning_report([])
    assert report["total_classifications"] == 0
    assert report["green_total"] == 0
    assert report["red_total"] == 0
    assert report["resolved_total"] == 0
    assert report["unresolved_total"] == 0
    assert report["green_success_rate"] == 0.0
    assert report["red_success_rate"] == 0.0
    assert report["average_calibrated_assertiveness"] == 0.0
    assert report["is_simulated"] is True
    assert report["actionable"] is False

def test_green_sim_outcome_true_counts_success():
    classifications = [_get_base_classification(label="GREEN_SIM", signal_id="sig-1")]
    outcomes = {"sig-1": True}
    report = generate_simulated_signal_learning_report(classifications, outcomes)
    
    assert report["green_total"] == 1
    assert report["resolved_total"] == 1
    assert report["by_label"]["GREEN_SIM"]["success"] == 1
    assert report["green_success_rate"] == 1.0
    assert report["green_false_positive_rate"] == 0.0

def test_green_sim_outcome_false_counts_false_positive():
    classifications = [_get_base_classification(label="GREEN_SIM", signal_id="sig-1")]
    outcomes = {"sig-1": False}
    report = generate_simulated_signal_learning_report(classifications, outcomes)
    
    assert report["by_label"]["GREEN_SIM"]["false_positive"] == 1
    assert report["green_success_rate"] == 0.0
    assert report["green_false_positive_rate"] == 1.0

def test_red_sim_outcome_false_counts_success():
    classifications = [_get_base_classification(label="RED_SIM", signal_id="sig-1")]
    outcomes = {"sig-1": False}
    report = generate_simulated_signal_learning_report(classifications, outcomes)
    
    assert report["by_label"]["RED_SIM"]["success"] == 1
    assert report["red_success_rate"] == 1.0
    assert report["red_false_negative_rate"] == 0.0

def test_red_sim_outcome_true_counts_false_negative():
    classifications = [_get_base_classification(label="RED_SIM", signal_id="sig-1")]
    outcomes = {"sig-1": True}
    report = generate_simulated_signal_learning_report(classifications, outcomes)
    
    assert report["by_label"]["RED_SIM"]["false_negative"] == 1
    assert report["red_success_rate"] == 0.0
    assert report["red_false_negative_rate"] == 1.0

def test_unresolved_is_counted_when_no_outcome():
    classifications = [_get_base_classification(label="GREEN_SIM", signal_id="sig-1")]
    report = generate_simulated_signal_learning_report(classifications, {})
    
    assert report["unresolved_total"] == 1
    assert report["resolved_total"] == 0
    assert report["by_label"]["GREEN_SIM"]["unresolved"] == 1

def test_averages_are_calculated():
    c1 = _get_base_classification(label="GREEN_SIM", signal_id="sig-1", ca=0.6, conf=0.7)
    c2 = _get_base_classification(label="RED_SIM", signal_id="sig-2", ca=0.8, conf=0.9)
    report = generate_simulated_signal_learning_report([c1, c2])
    
    assert report["average_calibrated_assertiveness"] == 0.7
    assert report["average_confidence"] == 0.8
    assert report["by_label"]["GREEN_SIM"]["average_calibrated_assertiveness"] == 0.6
    assert report["by_label"]["RED_SIM"]["average_confidence"] == 0.9

def test_global_safe_flags_preserved():
    report = generate_simulated_signal_learning_report([_get_base_classification()])
    assert report["is_simulated"] is True
    assert report["paper_trading"] is True
    assert report["actionable"] is False
    assert report["not_operational_advice"] is True

def test_actionable_true_fails():
    c = _get_base_classification()
    c["actionable"] = True
    with pytest.raises(ValueError, match="Operational flags.*must be False"):
        generate_simulated_signal_learning_report([c])

def test_bet_placed_true_fails():
    c = _get_base_classification()
    c["bet_placed"] = True
    with pytest.raises(ValueError, match="Operational flags.*must be False"):
        generate_simulated_signal_learning_report([c])

def test_alerted_true_fails():
    c = _get_base_classification()
    c["alerted"] = True
    with pytest.raises(ValueError, match="Operational flags.*must be False"):
        generate_simulated_signal_learning_report([c])

def test_stake_field_fails():
    c = _get_base_classification()
    c["stake"] = 100
    with pytest.raises(ValueError, match="Forbidden financial field"):
        generate_simulated_signal_learning_report([c])

def test_kelly_field_fails():
    c = _get_base_classification()
    c["kelly"] = 0.05
    with pytest.raises(ValueError, match="Forbidden financial field"):
        generate_simulated_signal_learning_report([c])

def test_bankroll_field_fails():
    c = _get_base_classification()
    c["bankroll"] = 1000
    with pytest.raises(ValueError, match="Forbidden financial field"):
        generate_simulated_signal_learning_report([c])

def test_operational_language_fails():
    c = _get_base_classification()
    c["execute"] = "now"
    with pytest.raises(ValueError, match="Forbidden financial field"):
        generate_simulated_signal_learning_report([c])
