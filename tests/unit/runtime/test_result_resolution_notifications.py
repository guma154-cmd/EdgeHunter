import pytest
from unittest.mock import MagicMock
from src.edgehunter.runtime.result_resolution_notifications import (
    resolve_signal_result,
    process_and_notify_signals,
)


@pytest.mark.parametrize("selection, home_score, away_score, expected", [
    ("mandante", 2, 1, "GREEN"),
    ("mandante vence", 1, 2, "RED"),
    ("mandante", 1, 1, "RED"),
    ("home", 3, 0, "GREEN"),
    ("empate", 1, 1, "GREEN"),
    ("empate", 2, 1, "RED"),
    ("draw", 0, 0, "GREEN"),
    ("visitante", 1, 2, "GREEN"),
    ("visitante vence", 2, 1, "RED"),
    ("visitante", 2, 2, "RED"),
    ("away", 0, 1, "GREEN"),
])
def test_resolve_signal_result(selection, home_score, away_score, expected):
    assert resolve_signal_result(selection, home_score, away_score) == expected


def test_resolve_signal_result_incomplete():
    assert resolve_signal_result("mandante", None, 1) is None
    assert resolve_signal_result("mandante", 1, None) is None
    assert resolve_signal_result("mandante", None, None) is None


def test_process_and_notify_signals_pending():
    notified = set()
    pending = [{"signal_id": "sig-1", "home": "A", "away": "B", "selection": "mandante"}]
    mock_send = MagicMock(return_value={"sent": True})
    
    env = {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}
    process_and_notify_signals(pending, [], notified, env, _mock_send=mock_send)
    
    assert "sig-1_PENDING" in notified
    assert mock_send.call_count == 1
    args, _ = mock_send.call_args
    assert "PENDENTE" in args[2]


def test_process_and_notify_signals_resolved_green():
    notified = set()
    outcomes = [{
        "signal_id": "sig-2", 
        "selection": "mandante", 
        "home_score": 2, 
        "away_score": 1
    }]
    mock_send = MagicMock(return_value={"sent": True})
    
    env = {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}
    process_and_notify_signals([], outcomes, notified, env, _mock_send=mock_send)
    
    assert "sig-2_RESOLVED" in notified
    assert mock_send.call_count == 1
    args, _ = mock_send.call_args
    assert "GREEN" in args[2]


def test_process_and_notify_signals_resolved_red():
    notified = set()
    outcomes = [{
        "signal_id": "sig-3", 
        "selection": "empate", 
        "home_score": 2, 
        "away_score": 1
    }]
    mock_send = MagicMock(return_value={"sent": True})
    
    env = {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}
    process_and_notify_signals([], outcomes, notified, env, _mock_send=mock_send)
    
    assert "sig-3_RESOLVED" in notified
    assert mock_send.call_count == 1
    args, _ = mock_send.call_args
    assert "RED" in args[2]


def test_process_and_notify_signals_does_not_resend():
    notified = {"sig-4_PENDING", "sig-4_RESOLVED"}
    pending = [{"signal_id": "sig-4"}]
    outcomes = [{"signal_id": "sig-4", "selection": "mandante", "home_score": 2, "away_score": 0}]
    
    mock_send = MagicMock()
    
    process_and_notify_signals(pending, outcomes, notified, {}, _mock_send=mock_send)
    
    assert mock_send.call_count == 0


def test_process_and_notify_signals_incomplete_score():
    notified = set()
    outcomes = [{"signal_id": "sig-5", "selection": "mandante", "home_score": None, "away_score": 1}]
    
    mock_send = MagicMock()
    
    process_and_notify_signals([], outcomes, notified, {}, _mock_send=mock_send)
    
    assert mock_send.call_count == 0
    assert "sig-5_RESOLVED" not in notified
