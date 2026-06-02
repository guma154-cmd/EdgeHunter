import json

import pytest

from src.edgehunter.core.dashboard_read_models import (
    DashboardCalibrationSnapshot,
    DashboardHealthStatus,
    DashboardLabelMetrics,
    DashboardOutcomeMetrics,
    DashboardSummary,
    DashboardThresholdSuggestionSnapshot,
)


def _summary(**overrides):
    payload = {
        "total_classifications": 10,
        "green_total": 6,
        "red_total": 4,
        "total_outcomes": 8,
        "positive_observed_total": 5,
        "negative_observed_total": 3,
        "unresolved_total": 1,
        "invalidated_total": 1,
        "green_confirmation_rate": 0.75,
        "green_not_confirmed_rate": 0.25,
        "red_rejection_confirmation_rate": 0.8,
        "red_missed_positive_rate": 0.2,
        "average_calibrated_assertiveness": 0.7,
        "average_confidence": 0.8,
        "current_threshold": 0.7,
        "latest_suggested_threshold": 0.72,
        "latest_threshold_action": "RAISE_THRESHOLD",
        "minimum_viable_sample_met": True,
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return DashboardSummary.from_dict(payload)


def test_creates_valid_dashboard_summary():
    summary = _summary()

    assert summary.total_classifications == 10
    assert summary.green_total == 6
    assert summary.latest_threshold_action == "RAISE_THRESHOLD"


def test_creates_label_metrics():
    metrics = DashboardLabelMetrics(
        label="GREEN_SIM",
        total=6,
        confirmed=4,
        not_confirmed=2,
        confirmation_rate=0.67,
        not_confirmed_rate=0.33,
    )

    assert metrics.to_dict()["label"] == "GREEN_SIM"
    assert metrics.to_dict()["total"] == 6


def test_creates_calibration_snapshot():
    snapshot = DashboardCalibrationSnapshot(
        threshold_green=0.7,
        sample_size=30,
        minimum_viable_sample_met=True,
        average_calibrated_assertiveness=0.71,
        average_confidence=0.82,
    )

    assert snapshot.to_dict()["sample_size"] == 30
    assert snapshot.to_dict()["minimum_viable_sample_met"] is True


def test_creates_threshold_suggestion_snapshot():
    snapshot = DashboardThresholdSuggestionSnapshot(
        current_threshold=0.7,
        suggested_threshold=0.72,
        action="RAISE_THRESHOLD",
        confidence=0.65,
        auto_apply=False,
    )

    assert snapshot.to_dict()["auto_apply"] is False
    assert snapshot.to_dict()["action"] == "RAISE_THRESHOLD"


def test_flags_are_preserved():
    payload = _summary().to_dict()

    assert payload["is_simulated"] is True
    assert payload["paper_trading"] is True
    assert payload["learning_mode"] is True
    assert payload["actionable"] is False
    assert payload["bet_placed"] is False
    assert payload["alerted"] is False
    assert payload["not_operational_advice"] is True


def test_actionable_true_fails():
    with pytest.raises(ValueError):
        _summary(actionable=True)


def test_bet_placed_true_fails():
    with pytest.raises(ValueError):
        _summary(bet_placed=True)


def test_alerted_true_fails():
    with pytest.raises(ValueError):
        _summary(alerted=True)


def test_forbidden_field_fails():
    payload = _summary().to_dict()
    payload["stake"] = 1

    with pytest.raises(ValueError):
        DashboardSummary.from_dict(payload)


def test_operational_language_fails():
    with pytest.raises(ValueError):
        DashboardHealthStatus(status="ajustar stake")


def test_to_dict_is_deterministic():
    summary = _summary()

    assert json.dumps(summary.to_dict(), sort_keys=True) == json.dumps(
        summary.to_dict(),
        sort_keys=True,
    )


def test_no_network_imports():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_imports():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "gemini" not in content
    assert "google" not in content


def test_no_notification_or_timer_runtime():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "autoevolution" not in content
    assert "auto_evolution" not in content


def test_no_financial_terms_in_runtime_source():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "stake" not in content
    assert "kelly" not in content
    assert "bankroll" not in content


def test_no_financial_execution_runtime():
    with open("src/edgehunter/core/dashboard_read_models.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
