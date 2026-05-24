"""Unit tests for core decorators."""

from __future__ import annotations

import logging
import time

from src.edgehunter.core.decorators import SHORT_TX


def test_short_tx_returns_wrapped_value_without_warning(caplog) -> None:
    @SHORT_TX(max_duration_ms=50)
    def fast_add(a: int, b: int) -> int:
        return a + b

    with caplog.at_level(logging.WARNING):
        result = fast_add(2, 3)

    assert result == 5
    assert "possible transaction lock risk" not in caplog.text


def test_short_tx_logs_warning_when_budget_exceeded(caplog) -> None:
    @SHORT_TX(max_duration_ms=1)
    def slow_call() -> str:
        time.sleep(0.01)
        return "done"

    with caplog.at_level(logging.WARNING):
        result = slow_call()

    assert result == "done"
    assert "possible transaction lock risk" in caplog.text
