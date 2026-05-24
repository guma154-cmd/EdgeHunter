"""Core decorators shared across EdgeHunter runtime code."""

from __future__ import annotations

from functools import wraps
import logging
import time
from typing import Any, Callable, TypeVar, cast


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def SHORT_TX(max_duration_ms: float = 100.0) -> Callable[[F], F]:
    """
    Warn when a transaction-focused function exceeds the expected duration budget.

    This decorator is meant for functions whose body should stay limited to local
    SQL work. It is not intended for orchestration functions that perform network
    I/O or other slow operations before/after the transaction.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if elapsed_ms > max_duration_ms:
                logger.warning(
                    "%s took %.2fms (max %.2fms) - possible transaction lock risk",
                    func.__name__,
                    elapsed_ms,
                    max_duration_ms,
                )
            return result

        return cast(F, wrapper)

    return decorator
