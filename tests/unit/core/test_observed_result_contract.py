from datetime import datetime, timezone
import pytest
from src.edgehunter.core.observed_result import ObservedResult, ObservedResultStatus, ObservedResultSource

def _valid_kwargs():
    return {
        "result_id": "res_123",
        "signal_id": "sig_123",
        "classification_id": "cls_123",
        "opportunity_id": "opp_123",
        "match_id": "mat_123",
        "result_status": ObservedResultStatus.POSITIVE_OBSERVED,
        "observed_at": datetime(2026, 6, 2, tzinfo=timezone.utc),
        "source": ObservedResultSource.LOCAL_CSV,
        "source_ref": "data.csv",
        "notes": "Test result"
    }

def test_valid_positive_observed():
    res = ObservedResult(**_valid_kwargs())
    assert res.result_status == ObservedResultStatus.POSITIVE_OBSERVED

def test_valid_negative_observed():
    kwargs = _valid_kwargs()
    kwargs["result_status"] = ObservedResultStatus.NEGATIVE_OBSERVED
    res = ObservedResult(**kwargs)
    assert res.result_status == ObservedResultStatus.NEGATIVE_OBSERVED

def test_valid_unresolved():
    kwargs = _valid_kwargs()
    kwargs["result_status"] = ObservedResultStatus.UNRESOLVED
    res = ObservedResult(**kwargs)
    assert res.result_status == ObservedResultStatus.UNRESOLVED

def test_valid_invalidated():
    kwargs = _valid_kwargs()
    kwargs["result_status"] = ObservedResultStatus.INVALIDATED
    res = ObservedResult(**kwargs)
    assert res.result_status == ObservedResultStatus.INVALIDATED

def test_source_local_csv():
    kwargs = _valid_kwargs()
    kwargs["source"] = ObservedResultSource.LOCAL_CSV
    res = ObservedResult(**kwargs)
    assert res.source == ObservedResultSource.LOCAL_CSV

def test_source_local_json():
    kwargs = _valid_kwargs()
    kwargs["source"] = ObservedResultSource.LOCAL_JSON
    res = ObservedResult(**kwargs)
    assert res.source == ObservedResultSource.LOCAL_JSON

def test_source_internal_dataset():
    kwargs = _valid_kwargs()
    kwargs["source"] = ObservedResultSource.INTERNAL_DATASET
    res = ObservedResult(**kwargs)
    assert res.source == ObservedResultSource.INTERNAL_DATASET

def test_invalid_source_fails():
    kwargs = _valid_kwargs()
    kwargs["source"] = "INVALID"
    with pytest.raises(ValueError):
        ObservedResult(**kwargs)

def test_invalid_status_fails():
    kwargs = _valid_kwargs()
    kwargs["result_status"] = "INVALID"
    with pytest.raises(ValueError):
        ObservedResult(**kwargs)

def test_observed_at_without_timezone_fails():
    kwargs = _valid_kwargs()
    kwargs["observed_at"] = datetime(2026, 6, 2)
    with pytest.raises(ValueError, match="timezone-aware"):
        ObservedResult(**kwargs)

def test_empty_mandatory_string_fails():
    kwargs = _valid_kwargs()
    kwargs["result_id"] = "   "
    with pytest.raises(ValueError, match="cannot be empty"):
        ObservedResult(**kwargs)

def test_actionable_true_fails():
    kwargs = _valid_kwargs()
    with pytest.raises(dataclass_frozen_error()):
        res = ObservedResult(**kwargs)
        res.actionable = True
        
def dataclass_frozen_error():
    import dataclasses
    return dataclasses.FrozenInstanceError

def test_bet_placed_true_fails():
    kwargs = _valid_kwargs()
    with pytest.raises(dataclass_frozen_error()):
        res = ObservedResult(**kwargs)
        res.bet_placed = True

def test_alerted_true_fails():
    kwargs = _valid_kwargs()
    with pytest.raises(dataclass_frozen_error()):
        res = ObservedResult(**kwargs)
        res.alerted = True

def test_operational_language_fails():
    kwargs = _valid_kwargs()
    kwargs["notes"] = "This is a gain signal"
    with pytest.raises(ValueError, match="Operational language blocked"):
        ObservedResult(**kwargs)
        
    kwargs = _valid_kwargs()
    kwargs["source_ref"] = "stake_log.txt"
    with pytest.raises(ValueError, match="Operational language blocked"):
        ObservedResult(**kwargs)

def test_extra_fields_fail():
    kwargs = _valid_kwargs()
    kwargs["extra_field"] = "not allowed"
    with pytest.raises(TypeError):
        ObservedResult(**kwargs)

def test_to_dict_deterministic():
    kwargs = _valid_kwargs()
    res = ObservedResult(**kwargs)
    d = res.to_dict()
    assert d["result_id"] == "res_123"
    assert d["result_status"] == "POSITIVE_OBSERVED"
    assert d["source"] == "LOCAL_CSV"
    assert d["is_simulated"] is True
    assert d["actionable"] is False
