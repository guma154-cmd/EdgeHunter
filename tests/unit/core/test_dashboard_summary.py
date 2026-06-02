import pytest

from src.edgehunter.core.dashboard_summary import generate_dashboard_summary


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


def test_empty_report_returns_safe_zeros():
    summary = generate_dashboard_summary([], [])

    assert summary["total_classifications"] == 0
    assert summary["total_outcomes"] == 0
    assert summary["green_confirmation_rate"] == 0.0
    assert summary["actionable"] is False


def test_green_sim_counts_correctly():
    summary = generate_dashboard_summary([_classification("GREEN_SIM")], [])

    assert summary["green_total"] == 1
    assert summary["red_total"] == 0


def test_red_sim_counts_correctly():
    summary = generate_dashboard_summary([_classification("RED_SIM")], [])

    assert summary["green_total"] == 0
    assert summary["red_total"] == 1


def test_outcomes_count_correctly():
    summary = generate_dashboard_summary(
        [],
        [
            _outcome("POSITIVE_OBSERVED", outcome_id="out-1"),
            _outcome("NEGATIVE_OBSERVED", outcome_id="out-2"),
        ],
    )

    assert summary["total_outcomes"] == 2
    assert summary["positive_observed_total"] == 1
    assert summary["negative_observed_total"] == 1


def test_rates_are_calculated():
    summary = generate_dashboard_summary(
        [
            _classification("GREEN_SIM", signal_id="sig-1", classification_id="class-1"),
            _classification("RED_SIM", signal_id="sig-2", classification_id="class-2"),
        ],
        [
            _outcome("POSITIVE_OBSERVED", signal_id="sig-1", classification_id="class-1"),
            _outcome("NEGATIVE_OBSERVED", signal_id="sig-2", classification_id="class-2"),
        ],
    )

    assert summary["green_confirmation_rate"] == 1.0
    assert summary["red_rejection_confirmation_rate"] == 1.0


def test_unresolved_and_invalidated_are_counted():
    summary = generate_dashboard_summary(
        [],
        [
            _outcome("UNRESOLVED", outcome_id="out-1"),
            _outcome("INVALIDATED", outcome_id="out-2"),
        ],
    )

    assert summary["unresolved_total"] == 1
    assert summary["invalidated_total"] == 1


def test_average_calibrated_assertiveness_is_calculated():
    summary = generate_dashboard_summary(
        [
            _classification(signal_id="sig-1", classification_id="class-1", calibrated_assertiveness=0.6),
            _classification(signal_id="sig-2", classification_id="class-2", calibrated_assertiveness=0.8),
        ],
        [],
    )

    assert summary["average_calibrated_assertiveness"] == 0.7


def test_average_confidence_is_calculated():
    summary = generate_dashboard_summary(
        [
            _classification(signal_id="sig-1", classification_id="class-1", confidence=0.5),
            _classification(signal_id="sig-2", classification_id="class-2", confidence=0.9),
        ],
        [],
    )

    assert summary["average_confidence"] == 0.7


def test_current_threshold_is_preserved():
    summary = generate_dashboard_summary([], [], current_threshold=0.73)

    assert summary["current_threshold"] == 0.73
    assert summary["latest_suggested_threshold"] == 0.73


def test_threshold_suggestion_is_reflected_without_auto_apply():
    summary = generate_dashboard_summary(
        [],
        [],
        threshold_suggestion={
            "suggested_threshold": 0.72,
            "action": "RAISE_THRESHOLD",
            "auto_apply": False,
        },
        current_threshold=0.7,
    )

    assert summary["current_threshold"] == 0.7
    assert summary["latest_suggested_threshold"] == 0.72
    assert summary["latest_threshold_action"] == "RAISE_THRESHOLD"


def test_unsafe_payload_fails():
    with pytest.raises(ValueError):
        generate_dashboard_summary([_classification(actionable=True)], [])


def test_operational_language_fails():
    with pytest.raises(ValueError):
        generate_dashboard_summary([_classification(rationale="ajustar stake")], [])


def test_no_sqlite_access():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "sqlite" not in content


def test_no_network_calls():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_calls():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "gemini" not in content
    assert "google" not in content


def test_no_notification_or_timer_runtime():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "autoevolution" not in content
    assert "auto_evolution" not in content


def test_no_financial_terms_in_runtime_source():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "stake" not in content
    assert "kelly" not in content
    assert "bankroll" not in content


def test_no_financial_execution_runtime():
    with open("src/edgehunter/core/dashboard_summary.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
