"""Unit tests for the SimulatedSignalClassifier contracts."""

import pytest

from src.edgehunter.core.simulated_signal_classifier import (
    SimulationLabel,
    SimulatedSignalClassificationInput,
    SimulatedSignalClassificationResult,
    classify_simulated_signal,
)

def _valid_input_payload() -> dict:
    return {
        "signal_id": "sig-123",
        "opportunity_id": "opp-456",
        "match_id": "match-789",
        "market": "1x2",
        "selection": "home",
        "source": "model-v1",
        "detection_method": "poisson",
        "calibrated_assertiveness": 0.75,
        "confidence": 0.80,
        "expected_value": 0.05,
        "edge_percentage": 5.0,
        "recent_hit_rate": 0.55,
        "recent_false_positive_rate": 0.10,
        "sample_size": 1500,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
    }

def _valid_result_payload() -> dict:
    return {
        "classification_id": "class-123",
        "signal_id": "sig-123",
        "opportunity_id": "opp-456",
        "simulation_label": "GREEN_SIM",
        "calibrated_assertiveness": 0.75,
        "confidence": 0.80,
        "threshold_green": 0.70,
        "learning_mode": True,
        "display": True,
        "rationale": "Valid rationale without operational terms.",
        "risk_factors": ["risk 1", "risk 2"],
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }

def test_creates_valid_input():
    payload = _valid_input_payload()
    result = SimulatedSignalClassificationInput.from_dict(payload)
    assert result.signal_id == "sig-123"
    assert result.calibrated_assertiveness == 0.75

def test_creates_valid_result():
    payload = _valid_result_payload()
    result = SimulatedSignalClassificationResult.from_dict(payload)
    assert result.simulation_label == SimulationLabel.GREEN_SIM
    assert result.calibrated_assertiveness == 0.75

def test_classifies_green_sim_when_assertiveness_equals_threshold():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = 0.70
    classification_input = SimulatedSignalClassificationInput.from_dict(payload)
    
    result = classify_simulated_signal(classification_input, threshold_green=0.70)
    assert result.simulation_label == SimulationLabel.GREEN_SIM
    assert result.calibrated_assertiveness == 0.70

def test_classifies_green_sim_when_assertiveness_greater_than_threshold():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = 0.71
    classification_input = SimulatedSignalClassificationInput.from_dict(payload)
    
    result = classify_simulated_signal(classification_input, threshold_green=0.70)
    assert result.simulation_label == SimulationLabel.GREEN_SIM

def test_classifies_red_sim_when_assertiveness_less_than_threshold():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = 0.69
    classification_input = SimulatedSignalClassificationInput.from_dict(payload)
    
    result = classify_simulated_signal(classification_input, threshold_green=0.70)
    assert result.simulation_label == SimulationLabel.RED_SIM

def test_custom_threshold_works():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = 0.85
    classification_input = SimulatedSignalClassificationInput.from_dict(payload)
    
    # Under custom 0.90 threshold, 0.85 is RED
    result = classify_simulated_signal(classification_input, threshold_green=0.90)
    assert result.simulation_label == SimulationLabel.RED_SIM

def test_calibrated_assertiveness_less_than_0_fails():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = -0.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_calibrated_assertiveness_greater_than_1_fails():
    payload = _valid_input_payload()
    payload["calibrated_assertiveness"] = 1.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_confidence_less_than_0_fails():
    payload = _valid_input_payload()
    payload["confidence"] = -0.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_confidence_greater_than_1_fails():
    payload = _valid_input_payload()
    payload["confidence"] = 1.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_invalid_threshold_fails():
    classification_input = SimulatedSignalClassificationInput.from_dict(_valid_input_payload())
    with pytest.raises(ValueError, match="between 0 and 1"):
        classify_simulated_signal(classification_input, threshold_green=-0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        classify_simulated_signal(classification_input, threshold_green=1.1)

def test_sample_size_negative_fails():
    payload = _valid_input_payload()
    payload["sample_size"] = -1
    with pytest.raises(ValueError, match="must be >= 0"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_empty_mandatory_string_fails():
    payload = _valid_input_payload()
    payload["signal_id"] = "   "
    with pytest.raises(ValueError, match="is required"):
        SimulatedSignalClassificationInput.from_dict(payload)

def test_actionable_true_fails():
    payload = _valid_input_payload()
    payload["actionable"] = True
    with pytest.raises(ValueError, match="must be False"):
        SimulatedSignalClassificationInput.from_dict(payload)
        
    payload2 = _valid_result_payload()
    payload2["actionable"] = True
    with pytest.raises(ValueError, match="must be False"):
        SimulatedSignalClassificationResult.from_dict(payload2)

def test_bet_placed_true_fails():
    payload = _valid_result_payload()
    payload["bet_placed"] = True
    with pytest.raises(ValueError, match="must be False"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_alerted_true_fails():
    payload = _valid_result_payload()
    payload["alerted"] = True
    with pytest.raises(ValueError, match="must be False"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_operational_rationale_fails():
    payload = _valid_result_payload()
    payload["rationale"] = "Eu recomendo que voce coloque aposta neste jogo"
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_operational_risk_factors_fails():
    payload = _valid_result_payload()
    payload["risk_factors"] = ["Alto risco, reduza a stake"]
    with pytest.raises(ValueError, match="forbidden content"):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_to_dict_is_deterministic():
    payload1 = _valid_input_payload()
    obj1 = SimulatedSignalClassificationInput.from_dict(payload1)
    
    payload2 = _valid_input_payload()
    obj2 = SimulatedSignalClassificationInput.from_dict(payload2)
    
    assert obj1.to_dict() == obj2.to_dict()
    
    res1 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    res2 = SimulatedSignalClassificationResult.from_dict(_valid_result_payload())
    
    assert res1.to_dict() == res2.to_dict()

def test_security_flags_are_preserved():
    classification_input = SimulatedSignalClassificationInput.from_dict(_valid_input_payload())
    result = classify_simulated_signal(classification_input)
    assert result.is_simulated is True
    assert result.paper_trading is True
    assert result.actionable is False
    assert result.bet_placed is False
    assert result.alerted is False
    assert result.not_operational_advice is True
    assert result.learning_mode is True

def test_output_does_not_contain_prohibited_terms():
    # As the output values are purely code-driven, they cannot contain prohibited terms
    # We will test that a raw string containing those will fail validation just to be sure.
    
    # 21. stake
    payload = _valid_result_payload()
    payload["rationale"] = "ajustar stake"
    with pytest.raises(ValueError):
        SimulatedSignalClassificationResult.from_dict(payload)
        
    # 22. Kelly
    payload["rationale"] = "usar kelly criterion"
    with pytest.raises(ValueError):
        SimulatedSignalClassificationResult.from_dict(payload)
        
    # 23. bankroll
    payload["rationale"] = "proteger o bankroll"
    with pytest.raises(ValueError):
        SimulatedSignalClassificationResult.from_dict(payload)
        
    # 24. recomendacao operacional
    payload["rationale"] = "minha recomendacao"
    with pytest.raises(ValueError):
        SimulatedSignalClassificationResult.from_dict(payload)

def test_no_external_imports():
    # 25, 26, 27, 28, 29, 30: Confirms there are no bad imports or behaviors
    import src.edgehunter.core.simulated_signal_classifier as mod
    
    import_names = dir(mod)
    assert "requests" not in import_names
    assert "google" not in import_names
    assert "gemini" not in import_names
    assert "telegram" not in import_names
    assert "schedule" not in import_names
    assert "execute_bet" not in import_names
    
    # Also parse the file to ensure no such imports
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
