"""Tests for deterministic match identity generation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.edgehunter.core.match_id import generate_match_id


def test_same_input_generates_same_match_id() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = generate_match_id("Flamengo FC", "Palmeiras", "Brasileirao", scheduled_time)
    second = generate_match_id("Flamengo FC", "Palmeiras", "Brasileirao", scheduled_time)

    assert first == second
    assert len(first) == 16


def test_home_team_change_generates_different_match_id() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = generate_match_id("Flamengo", "Palmeiras", "Brasileirao", scheduled_time)
    second = generate_match_id("Fluminense", "Palmeiras", "Brasileirao", scheduled_time)

    assert first != second


def test_league_change_generates_different_match_id() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = generate_match_id("Flamengo", "Palmeiras", "Brasileirao", scheduled_time)
    second = generate_match_id("Flamengo", "Palmeiras", "Copa do Brasil", scheduled_time)

    assert first != second


def test_relevant_datetime_change_generates_different_match_id() -> None:
    base_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = generate_match_id("Flamengo", "Palmeiras", "Brasileirao", base_time)
    second = generate_match_id(
        "Flamengo",
        "Palmeiras",
        "Brasileirao",
        base_time + timedelta(hours=2),
    )

    assert first != second


def test_naive_datetime_is_rejected() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        generate_match_id("Flamengo", "Palmeiras", "Brasileirao", scheduled_time)


def test_accents_case_and_spacing_do_not_break_determinism() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    first = generate_match_id("São Paulo FC", "PALMEIRAS", "Brasileirão", scheduled_time)
    second = generate_match_id("s. paulo", "palmeiras", "brasileirao", scheduled_time)

    assert first == second


def test_distinct_teams_do_not_collapse_to_same_name() -> None:
    scheduled_time = datetime(2026, 5, 24, 18, 0, tzinfo=UTC)

    united = generate_match_id(
        "Manchester United",
        "Liverpool",
        "Premier League",
        scheduled_time,
    )
    city = generate_match_id(
        "Manchester City",
        "Liverpool",
        "Premier League",
        scheduled_time,
    )

    assert united != city
