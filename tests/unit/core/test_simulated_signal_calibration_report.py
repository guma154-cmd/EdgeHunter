import pytest

from src.edgehunter.core.simulated_signal_calibration_report import (
    generate_simulated_signal_calibration_report,
)


def _classification(label="GREEN_SIM", **overrides):
    payload = {
        "classification_id": "class-1",
        "signal_id": "sig-1",
        "opportunity_id": "opp-1",
        "simulation_label": label,
        "calibrated_assertiveness": 0.8,
        "confidence": 0.7,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return payload


def _outcome(status="POSITIVE_OBSERVED", **overrides):
    payload = {
        "outcome_id": "out-1",
        "signal_id": "sig-1",
        "classification_id": "class-1",
        "opportunity_id": "opp-1",
        "outcome_status": status,
        "observed_at": "2026-01-01T00:00:00Z",
        "source": "manual_review",
        "notes": "technical review only",
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return payload


def test_empty_report_returns_safe_zero_metrics():
    report = generate_simulated_signal_calibration_report([], [])

    assert report["total_classifications"] == 0
    assert report["total_outcomes"] == 0
    assert report["matched_total"] == 0
    assert report["unmatched_classifications"] == 0
    assert report["green_confirmation_rate"] == 0.0
    assert report["average_calibrated_assertiveness"] == 0.0
    assert report["actionable"] is False


def test_green_positive_counts_green_confirmed():
    report = generate_simulated_signal_calibration_report(
        [_classification("GREEN_SIM")],
        [_outcome("POSITIVE_OBSERVED")],
    )

    assert report["green_confirmed"] == 1
    assert report["green_confirmation_rate"] == 1.0


def test_green_negative_counts_green_not_confirmed():
    report = generate_simulated_signal_calibration_report(
        [_classification("GREEN_SIM")],
        [_outcome("NEGATIVE_OBSERVED")],
    )

    assert report["green_not_confirmed"] == 1
    assert report["green_not_confirmed_rate"] == 1.0


def test_red_negative_counts_red_confirmed_as_rejection():
    report = generate_simulated_signal_calibration_report(
        [_classification("RED_SIM")],
        [_outcome("NEGATIVE_OBSERVED")],
    )

    assert report["red_confirmed_as_rejection"] == 1
    assert report["red_rejection_confirmation_rate"] == 1.0


def test_red_positive_counts_red_missed_positive_scenario():
    report = generate_simulated_signal_calibration_report(
        [_classification("RED_SIM")],
        [_outcome("POSITIVE_OBSERVED")],
    )

    assert report["red_missed_positive_scenario"] == 1
    assert report["red_missed_positive_rate"] == 1.0


def test_unresolved_counts_unresolved():
    report = generate_simulated_signal_calibration_report(
        [_classification("GREEN_SIM")],
        [_outcome("UNRESOLVED")],
    )

    assert report["unresolved_total"] == 1


def test_invalidated_counts_invalidated():
    report = generate_simulated_signal_calibration_report(
        [_classification("GREEN_SIM")],
        [_outcome("INVALIDATED")],
    )

    assert report["invalidated_total"] == 1


def test_classification_without_outcome_counts_unmatched():
    report = generate_simulated_signal_calibration_report([_classification()], [])

    assert report["unmatched_classifications"] == 1
    assert report["matched_total"] == 0


def test_matched_total_uses_best_available_key():
    report = generate_simulated_signal_calibration_report(
        [_classification(signal_id="sig-x", classification_id="class-1", opportunity_id="opp-x")],
        [_outcome(signal_id="sig-y", classification_id="class-1", opportunity_id="opp-y")],
    )

    assert report["matched_total"] == 1
    assert report["join_decision"]["matched_by"]["classification_id"] == 1


def test_average_calibrated_assertiveness_is_calculated():
    report = generate_simulated_signal_calibration_report(
        [
            _classification(signal_id="sig-1", classification_id="class-1", calibrated_assertiveness=0.6),
            _classification(signal_id="sig-2", classification_id="class-2", calibrated_assertiveness=0.8),
        ],
        [],
    )

    assert report["average_calibrated_assertiveness"] == 0.7


def test_average_confidence_is_calculated():
    report = generate_simulated_signal_calibration_report(
        [
            _classification(signal_id="sig-1", classification_id="class-1", confidence=0.5),
            _classification(signal_id="sig-2", classification_id="class-2", confidence=0.9),
        ],
        [],
    )

    assert report["average_confidence"] == 0.7


def test_minimum_viable_sample_met_uses_matched_total():
    report = generate_simulated_signal_calibration_report(
        [_classification(signal_id="sig-1")],
        [_outcome(signal_id="sig-1")],
        minimum_viable_sample_size=1,
    )

    assert report["sample_size"] == 1
    assert report["minimum_viable_sample_met"] is True


def test_global_flags_are_preserved():
    report = generate_simulated_signal_calibration_report([_classification()], [])

    assert report["is_simulated"] is True
    assert report["paper_trading"] is True
    assert report["learning_mode"] is True
    assert report["actionable"] is False
    assert report["bet_placed"] is False
    assert report["alerted"] is False
    assert report["not_operational_advice"] is True


def test_actionable_true_fails():
    with pytest.raises(ValueError):
        generate_simulated_signal_calibration_report([_classification(actionable=True)], [])


def test_bet_placed_true_fails():
    with pytest.raises(ValueError):
        generate_simulated_signal_calibration_report([_classification(bet_placed=True)], [])


def test_alerted_true_fails():
    with pytest.raises(ValueError):
        generate_simulated_signal_calibration_report([_classification(alerted=True)], [])


def test_operational_language_fails():
    with pytest.raises(ValueError):
        generate_simulated_signal_calibration_report(
            [_classification(rationale="ajustar stake")],
            [],
        )


def test_pure_function_does_not_call_sqlite_directly():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "sqlite" not in content


def test_no_network_calls():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_calls():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "gemini" not in content
    assert "google" not in content


def test_no_notification_or_timer_runtime():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "auto_evolution" not in content


def test_no_financial_action_runtime():
    with open("src/edgehunter/core/simulated_signal_calibration_report.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
