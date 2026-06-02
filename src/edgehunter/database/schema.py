"""SQLite schema management for STORY-01-002."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging
import sqlite3

try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - fallback for lean test environments
    logger = logging.getLogger(__name__)


DEFAULT_BUSY_TIMEOUT_MS = 5000
DEFAULT_CACHE_SIZE_PAGES = -10000
SCHEMA_VERSION = 1

EXPECTED_TABLES: tuple[str, ...] = (
    "matches",
    "odds_snapshots",
    "scraper_health",
    "value_detections",
    "gemini_validation_reports",
    "simulated_signal_classifications",
    "simulated_signal_outcomes",
    "schema_version",
)

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "matches": (
        "match_id",
        "home_team",
        "away_team",
        "league",
        "match_date",
        "home_goals",
        "away_goals",
        "result",
        "status",
        "created_at",
        "updated_at",
    ),
    "odds_snapshots": (
        "id",
        "match_id",
        "pinnacle_home",
        "pinnacle_draw",
        "pinnacle_away",
        "pinnacle_timestamp",
        "bet365_home",
        "bet365_draw",
        "bet365_away",
        "bet365_timestamp",
        "betano_home",
        "betano_draw",
        "betano_away",
        "betano_timestamp",
        "oddsportal_avg_home",
        "oddsportal_avg_draw",
        "oddsportal_avg_away",
        "oddsportal_timestamp",
        "max_latency_seconds",
        "bookmakers_synced",
        "valid_for_analysis",
        "snapshot_timestamp",
    ),
    "scraper_health": (
        "id",
        "scraper_name",
        "last_successful_run",
        "last_data_collected",
        "consecutive_failures",
        "odds_stale",
        "divergence_detected",
        "status",
        "last_alert_sent",
        "checked_at",
    ),
    "value_detections": (
        "id",
        "opportunity_id",
        "match_id",
        "snapshot_id",
        "market",
        "selection",
        "true_probability",
        "offered_odds",
        "expected_value",
        "edge_percentage",
        "source",
        "detection_method",
        "created_at",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "inserted_at",
    ),
    "gemini_validation_reports": (
        "id",
        "validation_id",
        "opportunity_id",
        "technical_verdict",
        "confidence",
        "risk_factors_json",
        "rationale",
        "parser_status",
        "provider",
        "model_name",
        "prompt_hash",
        "tokens_used",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
        "created_at",
        "inserted_at",
    ),
    "simulated_signal_classifications": (
        "id",
        "classification_id",
        "signal_id",
        "opportunity_id",
        "simulation_label",
        "calibrated_assertiveness",
        "confidence",
        "threshold_green",
        "learning_mode",
        "display",
        "rationale",
        "risk_factors_json",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
        "created_at",
        "inserted_at",
    ),
    "simulated_signal_outcomes": (
        "id",
        "outcome_id",
        "signal_id",
        "classification_id",
        "opportunity_id",
        "outcome_status",
        "observed_at",
        "source",
        "notes",
        "is_simulated",
        "paper_trading",
        "learning_mode",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
        "inserted_at",
    ),
    "schema_version": (
        "version",
        "applied_at",
        "description",
    ),
}

EXPECTED_INDEXES: tuple[str, ...] = (
    "idx_matches_status",
    "idx_matches_league_date",
    "idx_snapshots_match_time",
    "idx_snapshots_valid",
    "idx_scraper_health_status",
    "idx_value_detections_match_created",
    "idx_value_detections_safety_flags",
    "idx_gemini_validation_reports_opportunity",
    "idx_gemini_validation_reports_model_prompt",
    "idx_gemini_validation_reports_created",
    "idx_simulated_signal_classifications_opportunity",
    "idx_simulated_signal_classifications_signal",
    "idx_simulated_signal_outcomes_opportunity",
    "idx_simulated_signal_outcomes_signal",
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    league TEXT NOT NULL,
    match_date TIMESTAMP NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    result TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_league_date ON matches(league, match_date);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    pinnacle_home REAL,
    pinnacle_draw REAL,
    pinnacle_away REAL,
    pinnacle_timestamp TIMESTAMP,
    bet365_home REAL,
    bet365_draw REAL,
    bet365_away REAL,
    bet365_timestamp TIMESTAMP,
    betano_home REAL,
    betano_draw REAL,
    betano_away REAL,
    betano_timestamp TIMESTAMP,
    oddsportal_avg_home REAL,
    oddsportal_avg_draw REAL,
    oddsportal_avg_away REAL,
    oddsportal_timestamp TIMESTAMP,
    max_latency_seconds INTEGER,
    bookmakers_synced TEXT,
    valid_for_analysis BOOLEAN NOT NULL DEFAULT 1,
    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_match_time
    ON odds_snapshots(match_id, snapshot_timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_valid
    ON odds_snapshots(valid_for_analysis, snapshot_timestamp);

CREATE TABLE IF NOT EXISTS scraper_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_name TEXT NOT NULL,
    last_successful_run TIMESTAMP,
    last_data_collected TIMESTAMP,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    odds_stale BOOLEAN NOT NULL DEFAULT 0,
    divergence_detected BOOLEAN NOT NULL DEFAULT 0,
    status TEXT,
    last_alert_sent TIMESTAMP,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scraper_health_status
    ON scraper_health(scraper_name, status);

CREATE TABLE IF NOT EXISTS value_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT NOT NULL UNIQUE,
    match_id TEXT NOT NULL,
    snapshot_id INTEGER,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    true_probability REAL NOT NULL,
    offered_odds REAL NOT NULL,
    expected_value REAL NOT NULL,
    edge_percentage REAL NOT NULL,
    source TEXT NOT NULL,
    detection_method TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    paper_trading INTEGER NOT NULL DEFAULT 1,
    actionable INTEGER NOT NULL DEFAULT 0,
    bet_placed INTEGER NOT NULL DEFAULT 0,
    alerted INTEGER NOT NULL DEFAULT 0,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (snapshot_id) REFERENCES odds_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_value_detections_match_created
    ON value_detections(match_id, created_at);
CREATE INDEX IF NOT EXISTS idx_value_detections_safety_flags
    ON value_detections(is_simulated, paper_trading, actionable, bet_placed, alerted);

CREATE TABLE IF NOT EXISTS gemini_validation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id TEXT NOT NULL UNIQUE,
    opportunity_id TEXT NOT NULL,
    technical_verdict TEXT NOT NULL,
    confidence REAL NOT NULL,
    risk_factors_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    parser_status TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    paper_trading INTEGER NOT NULL DEFAULT 1,
    actionable INTEGER NOT NULL DEFAULT 0,
    bet_placed INTEGER NOT NULL DEFAULT 0,
    alerted INTEGER NOT NULL DEFAULT 0,
    not_operational_advice INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gemini_validation_reports_opportunity
    ON gemini_validation_reports(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_gemini_validation_reports_model_prompt
    ON gemini_validation_reports(provider, model_name, prompt_hash);
CREATE INDEX IF NOT EXISTS idx_gemini_validation_reports_created
    ON gemini_validation_reports(created_at);

CREATE TABLE IF NOT EXISTS simulated_signal_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classification_id TEXT NOT NULL UNIQUE,
    signal_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    simulation_label TEXT NOT NULL,
    calibrated_assertiveness REAL NOT NULL,
    confidence REAL NOT NULL,
    threshold_green REAL NOT NULL,
    learning_mode INTEGER NOT NULL DEFAULT 1,
    display INTEGER NOT NULL DEFAULT 1,
    rationale TEXT NOT NULL,
    risk_factors_json TEXT NOT NULL,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    paper_trading INTEGER NOT NULL DEFAULT 1,
    actionable INTEGER NOT NULL DEFAULT 0,
    bet_placed INTEGER NOT NULL DEFAULT 0,
    alerted INTEGER NOT NULL DEFAULT 0,
    not_operational_advice INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_simulated_signal_classifications_opportunity
    ON simulated_signal_classifications(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_simulated_signal_classifications_signal
    ON simulated_signal_classifications(signal_id);

CREATE TABLE IF NOT EXISTS simulated_signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outcome_id TEXT NOT NULL UNIQUE,
    signal_id TEXT NOT NULL,
    classification_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    outcome_status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    notes TEXT NOT NULL,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    paper_trading INTEGER NOT NULL DEFAULT 1,
    learning_mode INTEGER NOT NULL DEFAULT 1,
    actionable INTEGER NOT NULL DEFAULT 0,
    bet_placed INTEGER NOT NULL DEFAULT 0,
    alerted INTEGER NOT NULL DEFAULT 0,
    not_operational_advice INTEGER NOT NULL DEFAULT 1,
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_simulated_signal_outcomes_opportunity
    ON simulated_signal_outcomes(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_simulated_signal_outcomes_signal
    ON simulated_signal_outcomes(signal_id);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial PRD-01 OddsHistorian schema');
"""


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    configure_connection(connection)
    return connection


def configure_connection(connection: sqlite3.Connection) -> None:
    """Apply the SQLite PRAGMA profile required by PRD-01."""
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(f"PRAGMA busy_timeout={DEFAULT_BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE_PAGES}")
    connection.execute("PRAGMA foreign_keys=ON")


def ensure_schema(db_path: str) -> bool:
    """Apply the schema idempotently and configure the SQLite profile."""
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = _connect(db_path)
        try:
            connection.executescript(SCHEMA_SQL)
            version = get_schema_version_from_connection(connection)
            logger.info(f"Schema aplicado com sucesso. Versao atual: {version}")
        finally:
            connection.close()
        return True
    except (OSError, sqlite3.Error) as exc:
        logger.error(f"Erro ao aplicar schema: {exc}")
        return False


def verify_schema(db_path: str) -> dict[str, bool]:
    """Report whether each expected table exists."""
    try:
        connection = _connect(db_path)
        try:
            tables = set(get_existing_tables(connection))
        finally:
            connection.close()
    except sqlite3.Error:
        return {table: False for table in EXPECTED_TABLES}

    return {table: table in tables for table in EXPECTED_TABLES}


def get_schema_version(db_path: str) -> int | None:
    """Return the current schema version, if available."""
    try:
        connection = _connect(db_path)
        try:
            return get_schema_version_from_connection(connection)
        finally:
            connection.close()
    except sqlite3.Error:
        return None


def get_existing_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return tuple(row[0] for row in cursor.fetchall())


def get_schema_version_from_connection(connection: sqlite3.Connection) -> int | None:
    cursor = connection.execute("SELECT MAX(version) FROM schema_version")
    row = cursor.fetchone()
    return None if row is None else row[0]


def get_table_columns(db_path: str, table_name: str) -> tuple[str, ...]:
    """Return the ordered column names for a table."""
    connection = _connect(db_path)
    try:
        cursor = connection.execute(f"PRAGMA table_info({table_name})")
        return tuple(row[1] for row in cursor.fetchall())
    finally:
        connection.close()


def get_indexes(db_path: str) -> set[str]:
    """Return all explicit indexes currently present."""
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex_%'"
        )
        return {row[0] for row in cursor.fetchall()}
    finally:
        connection.close()


def get_pragma_profile(db_path: str) -> dict[str, Any]:
    """Return the PRAGMA values that define the required SQLite profile."""
    connection = _connect(db_path)
    try:
        return {
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            "busy_timeout": connection.execute("PRAGMA busy_timeout").fetchone()[0],
            "foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone()[0],
            "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
            "cache_size": connection.execute("PRAGMA cache_size").fetchone()[0],
        }
    finally:
        connection.close()
