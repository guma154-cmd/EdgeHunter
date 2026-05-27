"""Pure value calculation primitives for PRD-03."""

from __future__ import annotations

import math


MIN_OFFERED_ODDS = 1.01


def calculate_ev(true_prob: float, offered_odds: float) -> float:
    true_prob_clean = float(true_prob)
    offered_odds_clean = float(offered_odds)

    if not math.isfinite(true_prob_clean):
        raise ValueError("true_prob must be finite")
    if not 0.0 <= true_prob_clean <= 1.0:
        raise ValueError("true_prob must be between 0 and 1")
    if not math.isfinite(offered_odds_clean):
        raise ValueError("offered_odds must be finite")
    if offered_odds_clean < MIN_OFFERED_ODDS:
        raise ValueError("offered_odds must be >= 1.01")

    ev = (true_prob_clean * offered_odds_clean) - 1.0
    if not math.isfinite(ev):
        raise ValueError("expected value must be finite")
    return ev
