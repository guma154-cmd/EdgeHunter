import pytest
from src.edgehunter.core.observed_result_outcome_builder import build_simulated_outcomes_from_matches
from src.edgehunter.core.simulated_signal_outcome import OutcomeStatus
from src.edgehunter.core.observed_result import ObservedResultStatus, ObservedResultSource


def test_build_simulated_outcomes_positive():
    matches = [
        {
            "result": {
                "result_status": ObservedResultStatus.POSITIVE_OBSERVED,
                "observed_at": "2026-06-02T10:00:00Z",
                "source": ObservedResultSource.LOCAL_CSV,
                "source_ref": "file.csv",
                "notes": "won"
            },
            "classification": {
                "signal_id": "sig1",
                "classification_id": "cls1",
                "opportunity_id": "opp1"
            }
        }
    ]
    
    outcomes = build_simulated_outcomes_from_matches(matches)
    assert len(outcomes) == 1
    
    outcome = outcomes[0]
    assert outcome.signal_id == "sig1"
    assert outcome.classification_id == "cls1"
    assert outcome.opportunity_id == "opp1"
    assert outcome.outcome_status == OutcomeStatus.POSITIVE_OBSERVED
    assert outcome.is_simulated is True
    assert outcome.actionable is False
    assert outcome.source == "LOCAL_CSV:file.csv"


def test_build_simulated_outcomes_negative():
    matches = [
        {
            "result": {
                "result_status": "NEGATIVE_OBSERVED",
                "observed_at": "2026-06-02T10:00:00Z",
                "source": "LOCAL_JSON"
            },
            "classification": {
                "signal_id": "sig2",
                "classification_id": "cls2",
                "opportunity_id": "opp2"
            }
        }
    ]
    
    outcomes = build_simulated_outcomes_from_matches(matches)
    assert len(outcomes) == 1
    assert outcomes[0].outcome_status == OutcomeStatus.NEGATIVE_OBSERVED


def test_build_simulated_outcomes_pending():
    matches = [
        {
            "result": {
                "result_status": "UNRESOLVED",
                "observed_at": "2026-06-02T10:00:00Z",
                "source": "LOCAL_JSON"
            },
            "classification": {
                "signal_id": "sig3",
                "classification_id": "cls3",
                "opportunity_id": "opp3"
            }
        }
    ]
    
    outcomes = build_simulated_outcomes_from_matches(matches)
    assert outcomes[0].outcome_status == OutcomeStatus.UNRESOLVED


def test_build_simulated_outcomes_canceled_and_refunded():
    matches = [
        {
            "result": {
                "result_status": "INVALIDATED",
                "observed_at": "2026-06-02T10:00:00Z",
                "source": "LOCAL_JSON"
            },
            "classification": {
                "signal_id": "sig4",
                "classification_id": "cls4",
                "opportunity_id": "opp4"
            }
        },
        {
            "result": {
                "result_status": "INVALIDATED",
                "observed_at": "2026-06-02T10:00:00Z",
                "source": "LOCAL_JSON"
            },
            "classification": {
                "signal_id": "sig5",
                "classification_id": "cls5",
                "opportunity_id": "opp5"
            }
        }
    ]
    
    outcomes = build_simulated_outcomes_from_matches(matches)
    assert len(outcomes) == 2
    assert outcomes[0].outcome_status == OutcomeStatus.INVALIDATED
    assert outcomes[1].outcome_status == OutcomeStatus.INVALIDATED
