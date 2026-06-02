import pytest

from src.edgehunter.core.simulated_threshold_suggestion import (
    SimulatedThresholdSuggestion,
    generate_threshold_suggestion,
)


def _report(**overrides):
    payload = {
        "sample_size": 50,
        "green_confirmation_rate": 0.75,
        "green_not_confirmed_rate": 0.2,
        "red_missed_positive_rate": 0.2,
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


def test_creates_valid_suggestion():
    suggestion = generate_threshold_suggestion(_report(), current_threshold=0.7)

    assert isinstance(suggestion, SimulatedThresholdSuggestion)
    assert suggestion.current_threshold == 0.7
    assert suggestion.auto_apply is False
    assert suggestion.actionable is False


def test_low_sample_requires_more_sample():
    suggestion = generate_threshold_suggestion(_report(sample_size=5), minimum_sample_size=30)

    assert suggestion.action == "REQUIRE_MORE_SAMPLE"
    assert suggestion.suggested_threshold == suggestion.current_threshold


def test_high_green_not_confirmed_raises_threshold():
    suggestion = generate_threshold_suggestion(
        _report(green_not_confirmed_rate=0.5),
        current_threshold=0.7,
    )

    assert suggestion.action == "RAISE_THRESHOLD"
    assert suggestion.suggested_threshold == 0.72


def test_high_red_missed_positive_with_acceptable_green_rate_lowers_threshold():
    suggestion = generate_threshold_suggestion(
        _report(red_missed_positive_rate=0.5, green_confirmation_rate=0.75),
        current_threshold=0.7,
    )

    assert suggestion.action == "LOWER_THRESHOLD"
    assert suggestion.suggested_threshold == 0.68


def test_balanced_scenario_keeps_threshold():
    suggestion = generate_threshold_suggestion(_report(), current_threshold=0.7)

    assert suggestion.action == "KEEP_THRESHOLD"
    assert suggestion.suggested_threshold == 0.7


def test_suggested_threshold_never_exceeds_upper_bound():
    suggestion = generate_threshold_suggestion(
        _report(green_not_confirmed_rate=0.5),
        current_threshold=0.94,
    )

    assert suggestion.suggested_threshold == 0.95


def test_suggested_threshold_never_goes_below_lower_bound():
    suggestion = generate_threshold_suggestion(
        _report(red_missed_positive_rate=0.5, green_confirmation_rate=0.75),
        current_threshold=0.51,
    )

    assert suggestion.suggested_threshold == 0.5


def test_invalid_current_threshold_fails():
    with pytest.raises(ValueError):
        generate_threshold_suggestion(_report(), current_threshold=1.2)


def test_invalid_minimum_sample_size_fails():
    with pytest.raises(ValueError):
        generate_threshold_suggestion(_report(), minimum_sample_size=0)


def test_confidence_outside_range_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="technical hold",
            confidence=1.2,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
        )


def test_auto_apply_true_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="technical hold",
            confidence=0.5,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
            auto_apply=True,
        )


def test_actionable_true_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="technical hold",
            confidence=0.5,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
            actionable=True,
        )


def test_bet_placed_true_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="technical hold",
            confidence=0.5,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
            bet_placed=True,
        )


def test_alerted_true_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="technical hold",
            confidence=0.5,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
            alerted=True,
        )


def test_reason_operational_language_fails():
    with pytest.raises(ValueError):
        SimulatedThresholdSuggestion(
            suggestion_id="sug-1",
            current_threshold=0.7,
            suggested_threshold=0.7,
            action="KEEP_THRESHOLD",
            reason="ajustar stake",
            confidence=0.5,
            sample_size=30,
            green_confirmation_rate=0.7,
            green_not_confirmed_rate=0.2,
            red_missed_positive_rate=0.2,
        )


def test_payload_does_not_contain_stake():
    suggestion = generate_threshold_suggestion(_report())
    payload_text = str(suggestion.to_dict()).lower()

    assert "stake" not in payload_text


def test_payload_does_not_contain_kelly():
    suggestion = generate_threshold_suggestion(_report())
    payload_text = str(suggestion.to_dict()).lower()

    assert "kelly" not in payload_text


def test_payload_does_not_contain_bankroll():
    suggestion = generate_threshold_suggestion(_report())
    payload_text = str(suggestion.to_dict()).lower()

    assert "bankroll" not in payload_text


def test_no_network_calls():
    with open("src/edgehunter/core/simulated_threshold_suggestion.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "requests" not in content
    assert "httpx" not in content
    assert "urllib" not in content


def test_no_external_ai_provider_calls():
    with open("src/edgehunter/core/simulated_threshold_suggestion.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "gemini" not in content
    assert "google" not in content


def test_no_notification_or_timer_runtime():
    with open("src/edgehunter/core/simulated_threshold_suggestion.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "telegram" not in content
    assert "scheduler" not in content


def test_no_auto_evolution_runtime():
    with open("src/edgehunter/core/simulated_threshold_suggestion.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "auto_evolution" not in content


def test_no_financial_action_runtime():
    with open("src/edgehunter/core/simulated_threshold_suggestion.py", encoding="utf-8") as f:
        content = f.read().lower()
    assert "execute_bet" not in content
    assert "place_bet" not in content
