import pytest
from src.edgehunter.api.contracts import build_safe_api_response, FORBIDDEN_FIELDS

def test_build_safe_api_response_injects_flags():
    resp = build_safe_api_response({"a": 1})
    assert resp["is_simulated"] is True
    assert resp["paper_trading"] is True
    assert resp["actionable"] is False
    assert resp["bet_placed"] is False
    assert resp["alerted"] is False
    assert resp["not_operational_advice"] is True
    assert "Data is simulated/paper trading only and is not betting advice." in resp["disclaimer"]
    assert resp["data"] == {"a": 1}

@pytest.mark.parametrize("field", FORBIDDEN_FIELDS)
def test_rejects_forbidden_fields(field):
    with pytest.raises(ValueError, match="Forbidden field found"):
        build_safe_api_response({field: 10})
        
    with pytest.raises(ValueError, match="Forbidden field found"):
        build_safe_api_response({"nested": {field: 10}})

@pytest.mark.parametrize("field", ["actionable", "bet_placed", "alerted"])
def test_rejects_true_flags(field):
    with pytest.raises(ValueError, match=f"{field} cannot be true"):
        build_safe_api_response({field: True})
        
    with pytest.raises(ValueError, match=f"{field} cannot be true"):
        build_safe_api_response({"nested": {field: True}})

def test_allows_false_flags():
    resp = build_safe_api_response({"actionable": False})
    assert resp["data"]["actionable"] is False
