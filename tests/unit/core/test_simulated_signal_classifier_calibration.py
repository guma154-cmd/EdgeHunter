"""Unit tests for the simulated signal classifier calibration."""

import pytest

from src.edgehunter.core.simulated_signal_classifier import (
    SimulationLabel,
    calculate_calibrated_assertiveness,
    build_classification_input_from_calibration,
    classify_simulated_signal,
)

def _build_history(successes: int, total: int) -> list[dict]:
    history = []
    for _ in range(successes):
        history.append({"was_successful": True, "is_simulated": True})
    for _ in range(total - successes):
        history.append({"was_successful": False, "is_simulated": True})
    return history

def test_calculates_0_70_for_7_successes_in_10():
    history = _build_history(7, 10)
    assert calculate_calibrated_assertiveness(history, min_sample_size=10) == 0.70

def test_calculates_0_60_for_6_successes_in_10():
    history = _build_history(6, 10)
    assert calculate_calibrated_assertiveness(history, min_sample_size=10) == 0.60

def test_calculates_1_0_for_all_successes():
    history = _build_history(10, 10)
    assert calculate_calibrated_assertiveness(history, min_sample_size=10) == 1.0

def test_calculates_0_0_for_no_successes():
    history = _build_history(0, 10)
    assert calculate_calibrated_assertiveness(history, min_sample_size=10) == 0.0

def test_returns_fallback_if_empty_list():
    assert calculate_calibrated_assertiveness([], fallback_assertiveness=0.42) == 0.42

def test_returns_fallback_if_sample_less_than_min_size():
    history = _build_history(5, 5) # 100% success rate but only 5 samples
    assert calculate_calibrated_assertiveness(history, min_sample_size=10, fallback_assertiveness=0.33) == 0.33

def test_fallback_less_than_zero_fails():
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_calibrated_assertiveness([], fallback_assertiveness=-0.1)

def test_fallback_greater_than_one_fails():
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_calibrated_assertiveness([], fallback_assertiveness=1.1)

def test_min_sample_size_less_than_or_equal_to_zero_fails():
    with pytest.raises(ValueError):
        calculate_calibrated_assertiveness([], min_sample_size=0)
    with pytest.raises(ValueError):
        calculate_calibrated_assertiveness([], min_sample_size=-1)

def test_item_without_was_successful_fails():
    history = [{"is_simulated": True}]
    with pytest.raises(ValueError, match="must contain was_successful"):
        calculate_calibrated_assertiveness(history)

def test_was_successful_not_boolean_fails():
    history = [{"was_successful": "yes"}]
    with pytest.raises(ValueError, match="must be boolean"):
        calculate_calibrated_assertiveness(history)

def test_actionable_true_fails():
    history = [{"was_successful": True, "actionable": True}]
    with pytest.raises(ValueError, match="must not be actionable"):
        calculate_calibrated_assertiveness(history)

def test_bet_placed_true_fails():
    history = [{"was_successful": True, "bet_placed": True}]
    with pytest.raises(ValueError, match="must not have bet_placed=True"):
        calculate_calibrated_assertiveness(history)

def test_alerted_true_fails():
    history = [{"was_successful": True, "alerted": True}]
    with pytest.raises(ValueError, match="must not have alerted=True"):
        calculate_calibrated_assertiveness(history)

def test_field_stake_fails():
    history = [{"was_successful": True, "stake": 10}]
    with pytest.raises(ValueError, match="forbidden field"):
        calculate_calibrated_assertiveness(history)

def test_field_kelly_fails():
    history = [{"was_successful": True, "kelly": 0.05}]
    with pytest.raises(ValueError, match="forbidden field"):
        calculate_calibrated_assertiveness(history)

def test_field_bankroll_fails():
    history = [{"was_successful": True, "bankroll": 1000}]
    with pytest.raises(ValueError, match="forbidden field"):
        calculate_calibrated_assertiveness(history)

def test_operational_language_in_text_fails():
    history = [{"was_successful": True, "note": "Eu recomendo apostar."}]
    with pytest.raises(ValueError, match="forbidden content"):
        calculate_calibrated_assertiveness(history)

def test_result_is_deterministic():
    history = _build_history(7, 10)
    assert calculate_calibrated_assertiveness(history) == calculate_calibrated_assertiveness(history)

def test_result_is_always_between_0_and_1():
    for successes in range(11):
        history = _build_history(successes, 10)
        result = calculate_calibrated_assertiveness(history, min_sample_size=10)
        assert 0.0 <= result <= 1.0

def test_helper_creates_valid_input():
    history = _build_history(7, 10)
    obj = build_classification_input_from_calibration(
        signal_id="sig1",
        opportunity_id="opp1",
        match_id="match1",
        market="1x2",
        selection="home",
        source="v1",
        detection_method="poisson",
        historical_signals=history,
        confidence=0.8,
        expected_value=0.1,
        edge_percentage=10.0,
        recent_hit_rate=0.6,
        recent_false_positive_rate=0.1,
    )
    assert obj.calibrated_assertiveness == 0.70
    assert obj.sample_size == 10
    assert obj.actionable is False

def test_integration_generates_green_sim_on_0_70():
    history = _build_history(7, 10)
    obj = build_classification_input_from_calibration(
        signal_id="sig1",
        opportunity_id="opp1",
        match_id="match1",
        market="1x2",
        selection="home",
        source="v1",
        detection_method="poisson",
        historical_signals=history,
        confidence=0.8,
        expected_value=0.1,
        edge_percentage=10.0,
        recent_hit_rate=0.6,
        recent_false_positive_rate=0.1,
    )
    res = classify_simulated_signal(obj, threshold_green=0.70)
    assert res.simulation_label == SimulationLabel.GREEN_SIM

def test_integration_generates_red_sim_on_0_69():
    history = _build_history(69, 100)
    obj = build_classification_input_from_calibration(
        signal_id="sig1",
        opportunity_id="opp1",
        match_id="match1",
        market="1x2",
        selection="home",
        source="v1",
        detection_method="poisson",
        historical_signals=history,
        confidence=0.8,
        expected_value=0.1,
        edge_percentage=10.0,
        recent_hit_rate=0.6,
        recent_false_positive_rate=0.1,
    )
    res = classify_simulated_signal(obj, threshold_green=0.70)
    assert res.simulation_label == SimulationLabel.RED_SIM

def test_no_external_imports_in_classifier():
    import src.edgehunter.core.simulated_signal_classifier as mod
    import_names = dir(mod)
    assert "requests" not in import_names
    assert "google" not in import_names
    assert "gemini" not in import_names
    assert "telegram" not in import_names
    assert "schedule" not in import_names
    assert "sqlite3" not in import_names
    
    import ast
    with open(mod.__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert "google" not in name.name
                assert "requests" not in name.name
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            assert "google" not in node.module
            assert "requests" not in node.module
