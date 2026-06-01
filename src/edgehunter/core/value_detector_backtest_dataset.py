"""Historical dataset records for local simulated backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import sqlite3
from typing import Any, Mapping


SUPPORTED_BOOKMAKERS: tuple[str, ...] = (
    "pinnacle",
    "bet365",
    "betano",
    "oddsportal_avg",
)
REQUIRED_TABLES: tuple[str, ...] = ("matches", "odds_snapshots")
RESULT_VALUES: frozenset[str] = frozenset({"home_win", "draw", "away_win"})


def _require_text(value: str, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    return clean_value


def _require_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _require_safe_flags(
    *,
    is_simulated: bool,
    paper_trading: bool,
    actionable: bool,
) -> None:
    if is_simulated is not True:
        raise ValueError("is_simulated must be True")
    if paper_trading is not True:
        raise ValueError("paper_trading must be True")
    if actionable is not False:
        raise ValueError("actionable must be False")


def _compute_actual_result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home_win"
    if home_goals < away_goals:
        return "away_win"
    return "draw"


def _normalize_actual_result(
    *,
    stored_result: str | None,
    home_goals: int,
    away_goals: int,
    match_id: str,
) -> str:
    computed_result = _compute_actual_result(home_goals, away_goals)
    if stored_result is None:
        return computed_result

    clean_result = _require_text(stored_result, "result")
    if clean_result not in RESULT_VALUES:
        raise ValueError(f"stored result is invalid for match_id={match_id}")
    if clean_result != computed_result:
        raise ValueError(f"stored result does not match scoreline for match_id={match_id}")
    return clean_result


def _normalize_odds(
    odds: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {}
    for bookmaker in SUPPORTED_BOOKMAKERS:
        bookmaker_odds = odds.get(bookmaker)
        if bookmaker_odds is None:
            continue
        normalized[bookmaker] = {
            "home": float(bookmaker_odds["home"]),
            "draw": float(bookmaker_odds["draw"]),
            "away": float(bookmaker_odds["away"]),
        }
    return normalized


def _parse_bookmakers_synced(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("bookmakers_synced must be a JSON array")
    return tuple(_require_text(str(item), "bookmakers_synced item") for item in parsed)


@dataclass(frozen=True)
class BacktestHistoricalMatch:
    match_id: str
    home_team: str
    away_team: str
    league: str
    scheduled_time: datetime
    home_goals: int
    away_goals: int
    actual_result: str
    snapshot_id: int
    snapshot_timestamp: datetime
    valid_for_analysis: bool
    odds: Mapping[str, Mapping[str, float]]
    bookmakers_synced: tuple[str, ...] = ()
    max_latency_seconds: int | None = None
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False

    def __post_init__(self) -> None:
        _require_safe_flags(
            is_simulated=self.is_simulated,
            paper_trading=self.paper_trading,
            actionable=self.actionable,
        )
        object.__setattr__(self, "match_id", _require_text(self.match_id, "match_id"))
        object.__setattr__(self, "home_team", _require_text(self.home_team, "home_team"))
        object.__setattr__(self, "away_team", _require_text(self.away_team, "away_team"))
        object.__setattr__(self, "league", _require_text(self.league, "league"))
        object.__setattr__(
            self,
            "scheduled_time",
            _require_aware_datetime(self.scheduled_time, "scheduled_time"),
        )
        object.__setattr__(
            self,
            "home_goals",
            _require_non_negative_int(self.home_goals, "home_goals"),
        )
        object.__setattr__(
            self,
            "away_goals",
            _require_non_negative_int(self.away_goals, "away_goals"),
        )
        if self.actual_result not in RESULT_VALUES:
            raise ValueError("actual_result must be one of home_win, draw, away_win")
        object.__setattr__(
            self,
            "snapshot_id",
            _require_non_negative_int(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "snapshot_timestamp",
            _require_aware_datetime(self.snapshot_timestamp, "snapshot_timestamp"),
        )
        object.__setattr__(
            self,
            "valid_for_analysis",
            _require_bool(self.valid_for_analysis, "valid_for_analysis"),
        )
        normalized_odds = _normalize_odds(self.odds)
        if not normalized_odds:
            raise ValueError("odds must include at least one bookmaker")
        object.__setattr__(self, "odds", normalized_odds)
        object.__setattr__(
            self,
            "bookmakers_synced",
            tuple(_require_text(item, "bookmakers_synced item") for item in self.bookmakers_synced),
        )
        if self.max_latency_seconds is not None:
            object.__setattr__(
                self,
                "max_latency_seconds",
                _require_non_negative_int(
                    self.max_latency_seconds,
                    "max_latency_seconds",
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league": self.league,
            "scheduled_time": self.scheduled_time.isoformat(),
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "actual_result": self.actual_result,
            "snapshot_id": self.snapshot_id,
            "snapshot_timestamp": self.snapshot_timestamp.isoformat(),
            "valid_for_analysis": self.valid_for_analysis,
            "odds": {
                bookmaker: dict(values)
                for bookmaker, values in self.odds.items()
            },
            "bookmakers_synced": list(self.bookmakers_synced),
            "max_latency_seconds": self.max_latency_seconds,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
        }


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _has_required_tables(connection: sqlite3.Connection) -> bool:
    placeholders = ",".join("?" for _ in REQUIRED_TABLES)
    rows = connection.execute(
        f"""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
            AND name IN ({placeholders})
        """,
        REQUIRED_TABLES,
    ).fetchall()
    return {row["name"] for row in rows} == set(REQUIRED_TABLES)


def _build_snapshot_odds_payload(row: sqlite3.Row) -> dict[str, dict[str, float]]:
    odds: dict[str, dict[str, float]] = {}
    for bookmaker in SUPPORTED_BOOKMAKERS:
        home = row[f"{bookmaker}_home"]
        draw = row[f"{bookmaker}_draw"]
        away = row[f"{bookmaker}_away"]
        if home is None or draw is None or away is None:
            continue
        odds[bookmaker] = {
            "home": float(home),
            "draw": float(draw),
            "away": float(away),
        }
    return odds


def _dataset_row_to_match(row: sqlite3.Row) -> BacktestHistoricalMatch | None:
    odds = _build_snapshot_odds_payload(row)
    if not odds:
        return None

    match_id = _require_text(row["match_id"], "match_id")
    home_goals = _require_non_negative_int(int(row["home_goals"]), "home_goals")
    away_goals = _require_non_negative_int(int(row["away_goals"]), "away_goals")
    actual_result = _normalize_actual_result(
        stored_result=row["result"],
        home_goals=home_goals,
        away_goals=away_goals,
        match_id=match_id,
    )

    return BacktestHistoricalMatch(
        match_id=match_id,
        home_team=row["home_team"],
        away_team=row["away_team"],
        league=row["league"],
        scheduled_time=datetime.fromisoformat(row["match_date"]),
        home_goals=home_goals,
        away_goals=away_goals,
        actual_result=actual_result,
        snapshot_id=int(row["snapshot_id"]),
        snapshot_timestamp=datetime.fromisoformat(row["snapshot_timestamp"]),
        valid_for_analysis=bool(row["valid_for_analysis"]),
        odds=odds,
        bookmakers_synced=_parse_bookmakers_synced(row["bookmakers_synced"]),
        max_latency_seconds=row["max_latency_seconds"],
    )


def get_backtest_dataset(
    db_path: str,
    league: str | None = None,
    valid_only: bool = True,
    limit: int | None = None,
) -> list[BacktestHistoricalMatch]:
    if not isinstance(valid_only, bool):
        raise ValueError("valid_only must be a boolean")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be > 0")
    league_filter = None if league is None else _require_text(league, "league")

    if not Path(db_path).exists():
        return []

    valid_clause = "AND s.valid_for_analysis = 1" if valid_only else ""
    league_clause = "AND m.league = ?" if league_filter is not None else ""
    limit_clause = "LIMIT ?" if limit is not None else ""
    params: list[Any] = []
    if league_filter is not None:
        params.append(league_filter)
    if limit is not None:
        params.append(limit)

    connection = _connect(db_path)
    try:
        if not _has_required_tables(connection):
            return []
        rows = connection.execute(
            f"""
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.league,
                m.match_date,
                m.home_goals,
                m.away_goals,
                m.result,
                s.id AS snapshot_id,
                s.pinnacle_home,
                s.pinnacle_draw,
                s.pinnacle_away,
                s.bet365_home,
                s.bet365_draw,
                s.bet365_away,
                s.betano_home,
                s.betano_draw,
                s.betano_away,
                s.oddsportal_avg_home,
                s.oddsportal_avg_draw,
                s.oddsportal_avg_away,
                s.bookmakers_synced,
                s.valid_for_analysis,
                s.snapshot_timestamp,
                s.max_latency_seconds
            FROM matches AS m
            JOIN odds_snapshots AS s
                ON s.match_id = m.match_id
            WHERE
                m.status = 'finished'
                AND m.home_goals IS NOT NULL
                AND m.away_goals IS NOT NULL
                {valid_clause}
                {league_clause}
            ORDER BY
                m.match_date ASC,
                m.match_id ASC,
                s.snapshot_timestamp ASC,
                s.id ASC
            {limit_clause}
            """,
            tuple(params),
        ).fetchall()
    finally:
        connection.close()

    dataset: list[BacktestHistoricalMatch] = []
    for row in rows:
        item = _dataset_row_to_match(row)
        if item is not None:
            dataset.append(item)
    return dataset
