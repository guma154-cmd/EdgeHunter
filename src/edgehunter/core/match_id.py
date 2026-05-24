"""Deterministic match identity helpers for OddsHistorian."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import unicodedata


TEAM_SUFFIXES: tuple[str, ...] = (
    " esporte clube",
    " futebol clube",
    " football club",
    " soccer club",
    " clube",
    " fc",
    " ec",
    " sc",
    " ac",
    " cf",
    " cd",
)

TEAM_ALIASES: dict[str, str] = {
    "s paulo": "sao paulo",
}


def _strip_accents(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _collapse_text(value: str) -> str:
    collapsed = _strip_accents(value).lower()
    collapsed = re.sub(r"[^a-z0-9]+", " ", collapsed)
    return re.sub(r"\s+", " ", collapsed).strip()


def _require_non_empty(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _require_aware_datetime(scheduled_time: datetime) -> datetime:
    if scheduled_time.tzinfo is None or scheduled_time.utcoffset() is None:
        raise ValueError("scheduled_time must be timezone-aware")
    return scheduled_time.astimezone(timezone.utc).replace(microsecond=0)


def normalize_team(team_name: str) -> str:
    """Normalize a team name without collapsing distinctive club terms."""
    canonical = _collapse_text(_require_non_empty(team_name, "team_name"))
    canonical = TEAM_ALIASES.get(canonical, canonical)

    for suffix in TEAM_SUFFIXES:
        if canonical.endswith(suffix):
            canonical = canonical[: -len(suffix)].strip()
            break

    if not canonical:
        raise ValueError("team_name cannot be empty after normalization")
    return canonical.replace(" ", "_")


def normalize_league(league: str) -> str:
    canonical = _collapse_text(_require_non_empty(league, "league"))
    if not canonical:
        raise ValueError("league cannot be empty after normalization")
    return canonical.replace(" ", "_")


def canonical_match_key(
    home_team: str,
    away_team: str,
    league: str,
    scheduled_time: datetime,
) -> str:
    """Return the normalized canonical key used for deterministic IDs."""
    normalized_time = _require_aware_datetime(scheduled_time)
    return "|".join(
        (
            normalize_league(league),
            normalize_team(home_team),
            normalize_team(away_team),
            normalized_time.isoformat(timespec="seconds"),
        )
    )


def generate_match_id(
    home_team: str,
    away_team: str,
    league: str,
    scheduled_time: datetime,
) -> str:
    """Generate a stable 16-character match identifier."""
    canonical_key = canonical_match_key(
        home_team=home_team,
        away_team=away_team,
        league=league,
        scheduled_time=scheduled_time,
    )
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]
