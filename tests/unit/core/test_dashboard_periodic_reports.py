import pytest

from src.edgehunter.core.dashboard_periodic_reports import (
    generate_periodic_agent_evolution_report,
)


def _classification(label="GREEN_SIM", when="2026-06-01T10:00:00Z", **overrides):
    payload = {
        "classification_id": "class-1",
        "signal_id": "sig-1",
        "opportunity_id": "opp-1",
        "simulation_label": label,
        "calibrated_assertiveness": 0.8,
        "confidence": 0.7,
        "created_at": when,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
    }
    payload.update(overrides)
    return payload


def _outcome(status="POSITIVE_OBSERVED", when="2026-06-01T12:00:00Z", **overrides):
    payload = {
        "outcome_id": "out-1",
        "signal_id": "sig-1",
        "classification_id": "class-1",
        "opportunity_id": "opp-1",
        "outcome_status": status,
        "observed_at": when,
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


def _report(classifications=None, outcomes=None, **kwargs):
    return generate_periodic_agent_evolution_report(
        classifications or [],
        outcomes or [],
        period=kwargs.pop("period", "daily"),
        current_period_start=kwargs.pop("current_period_start", "2026-06-01T00:00:00Z"),
        current_period_end=kwargs.pop("current_period_end", "2026-06-01T23:59:59Z"),
        **kwargs,
    )


def test_daily_report_valid():
    report = _report(period="daily")
    assert report["period"] == "daily"


def test_weekly_report_valid():
    report = _report(period="weekly")
    assert report["period"] == "weekly"


def test_monthly_report_valid():
    report = _report(period="monthly")
    assert report["period"] == "monthly"


def test_invalid_period_fails():
    with pytest.raises(ValueError):
        _report(period="yearly")


def test_calculates_simulated_hits():
    report = _report([_classification()], [_outcome()])
    assert report["green_confirmed"] == 1


def test_calculates_simulated_errors():
    report = _report([_classification()], [_outcome("NEGATIVE_OBSERVED")])
    assert report["green_not_confirmed"] == 1


def test_calculates_green_confirmed():
    report = _report([_classification("GREEN_SIM")], [_outcome("POSITIVE_OBSERVED")])
    assert report["green_confirmed"] == 1


def test_calculates_green_not_confirmed():
    report = _report([_classification("GREEN_SIM")], [_outcome("NEGATIVE_OBSERVED")])
    assert report["green_not_confirmed"] == 1


def test_calculates_red_confirmed_as_rejection():
    report = _report([_classification("RED_SIM")], [_outcome("NEGATIVE_OBSERVED")])
    assert report["red_confirmed_as_rejection"] == 1


def test_calculates_red_missed_positive_scenario():
    report = _report([_classification("RED_SIM")], [_outcome("POSITIVE_OBSERVED")])
    assert report["red_missed_positive_scenario"] == 1


def test_calculates_rates_correctly():
    report = _report([_classification()], [_outcome()])
    assert report["green_confirmation_rate"] == 1.0
    assert report["green_not_confirmed_rate"] == 0.0


def test_compares_with_previous_period():
    report = _report(
        [_classification()],
        [_outcome()],
        previous_period_start="2026-05-31T00:00:00Z",
        previous_period_end="2026-05-31T23:59:59Z",
    )
    assert "green_confirmation_rate_delta" in report["previous_period_comparison"]


def test_status_improving_works():
    report = _report(
        [
            _classification(when="2026-06-01T10:00:00Z"),
            _classification(when="2026-05-31T10:00:00Z"),
        ],
        [
            _outcome("POSITIVE_OBSERVED", when="2026-06-01T11:00:00Z"),
            _outcome("NEGATIVE_OBSERVED", when="2026-05-31T11:00:00Z"),
        ],
        previous_period_start="2026-05-31T00:00:00Z",
        previous_period_end="2026-05-31T23:59:59Z",
    )
    assert report["agent_evolution_status"] == "IMPROVING"


def test_status_stable_works():
    report = _report([_classification()], [_outcome()])
    assert report["agent_evolution_status"] == "STABLE"


def test_status_declining_works():
    report = _report(
        [
            _classification(when="2026-06-01T10:00:00Z"),
            _classification(when="2026-05-31T10:00:00Z"),
        ],
        [
            _outcome("NEGATIVE_OBSERVED", when="2026-06-01T11:00:00Z"),
            _outcome("POSITIVE_OBSERVED", when="2026-05-31T11:00:00Z"),
        ],
        previous_period_start="2026-05-31T00:00:00Z",
        previous_period_end="2026-05-31T23:59:59Z",
    )
    assert report["agent_evolution_status"] == "DECLINING"


def test_status_insufficient_sample_works():
    report = _report()
    assert report["agent_evolution_status"] == "INSUFFICIENT_SAMPLE"


def test_preserves_safe_flags():
    report = _report()
    assert report["is_simulated"] is True
    assert report["paper_trading"] is True
    assert report["learning_mode"] is True
    assert report["actionable"] is False
    assert report["bet_placed"] is False
    assert report["alerted"] is False
    assert report["not_operational_advice"] is True


def test_does_not_alter_threshold():
    suggestion = {"suggested_threshold": 0.72, "action": "RAISE_THRESHOLD", "auto_apply": False}
    report = _report(threshold_suggestions=[suggestion])
    assert report["latest_threshold_suggestion"]["suggested_threshold"] == 0.72


def test_does_not_apply_suggestion_automatically():
    with pytest.raises(ValueError):
        _report(threshold_suggestions=[{"suggested_threshold": 0.72, "auto_apply": True}])


def test_no_network_calls():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_calls():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "google" not in content
    assert "genai" not in content


def test_no_notification_or_timer_runtime():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "autoevolution" not in content
    assert "auto_evolution" not in content


def test_no_financial_terms_in_runtime_source():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "stake" not in content
    assert "kelly" not in content
    assert "bankroll" not in content


def test_no_financial_execution_runtime():
    with open("src/edgehunter/core/dashboard_periodic_reports.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
