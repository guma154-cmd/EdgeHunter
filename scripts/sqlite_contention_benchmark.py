"""
Controlled SQLite contention benchmark for EdgeHunter.

Runs two scenarios:
1. disciplined transactions with 6 logical writers
2. anti-pattern transaction holding the write lock past busy_timeout
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Thread
import json
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.edgehunter.database.sqlite_observability import (
    SQLiteWriteObserver,
    connect_sqlite,
    measured_write_transaction,
)


RESULTS_DIR = Path("_bmad-output/test-artifacts/sqlite-benchmark")
RESULTS_PATH = RESULTS_DIR / "sqlite_contention_results.json"


@dataclass(frozen=True)
class WriterSpec:
    name: str
    writes_per_round: int
    hold_ms: int = 0


SCRAPER_WRITES_PER_ROUND = 9
DISCIPLINED_ROUNDS = 12


DISCIPLINED_WRITERS = [
    WriterSpec("bet365_scraper", SCRAPER_WRITES_PER_ROUND),
    WriterSpec("betano_scraper", SCRAPER_WRITES_PER_ROUND),
    WriterSpec("pinnacle_scraper", SCRAPER_WRITES_PER_ROUND),
    WriterSpec("oddsportal_scraper", SCRAPER_WRITES_PER_ROUND),
    WriterSpec("apscheduler_jobs", 4),
    WriterSpec("telegram_callbacks", 1),
]

ANTIPATTERN_WRITERS = [
    WriterSpec("bet365_scraper", 1, hold_ms=0),
    WriterSpec("betano_scraper", 1, hold_ms=0),
    WriterSpec("pinnacle_scraper", 1, hold_ms=0),
    WriterSpec("oddsportal_scraper", 1, hold_ms=0),
    WriterSpec("apscheduler_jobs", 1, hold_ms=5500),
    WriterSpec("telegram_callbacks", 1, hold_ms=0),
]


def ensure_future_tables(db_path: str) -> None:
    connection = connect_sqlite(db_path)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            league TEXT NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            result TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT NOT NULL,
            snapshot_time TIMESTAMP NOT NULL,
            pinnacle_odds_1 REAL,
            bet365_odds_1 REAL,
            betano_odds_1 REAL,
            max_latency_seconds INTEGER,
            bookmakers_synced INTEGER,
            valid_for_analysis BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        );

        CREATE TABLE IF NOT EXISTS scraper_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraper_name TEXT NOT NULL,
            check_time TIMESTAMP NOT NULL,
            status TEXT NOT NULL,
            consecutive_failures INTEGER DEFAULT 0,
            odds_stale BOOLEAN DEFAULT 0,
            divergence_detected BOOLEAN DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS placed_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_id INTEGER,
            match_id TEXT,
            bookmaker TEXT,
            stake REAL,
            placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS evolution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            action_taken TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bankroll_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_bankroll REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bankroll_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            old_value REAL NOT NULL,
            new_value REAL NOT NULL,
            delta REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO bankroll_state (id, current_bankroll)
        VALUES (1, 50.0)
        """
    )
    connection.commit()
    connection.close()


def insert_snapshot(connection: sqlite3.Connection, writer_name: str, round_no: int, seq_no: int) -> None:
    match_id = f"{writer_name}_round_{round_no}_match_{seq_no}"
    connection.execute(
        """
        INSERT OR IGNORE INTO matches (
            match_id, home_team, away_team, league, scheduled_time, status
        ) VALUES (?, ?, ?, ?, datetime('now'), 'scheduled')
        """,
        (
            match_id,
            f"{writer_name}_home",
            f"{writer_name}_away",
            "benchmark_league",
        ),
    )
    connection.execute(
        """
        INSERT INTO odds_snapshots (
            match_id,
            snapshot_time,
            pinnacle_odds_1,
            bet365_odds_1,
            betano_odds_1,
            max_latency_seconds,
            bookmakers_synced,
            valid_for_analysis
        ) VALUES (?, datetime('now'), 2.05, 2.1, 2.0, 12, 3, 1)
        """,
        (match_id,),
    )


def write_scheduler_state(connection: sqlite3.Connection, round_no: int, seq_no: int) -> None:
    connection.execute(
        """
        INSERT INTO scraper_health (
            scraper_name, check_time, status, consecutive_failures, odds_stale, divergence_detected
        ) VALUES (?, datetime('now'), 'healthy', 0, 0, 0)
        """,
        (f"scheduler_round_{round_no}_{seq_no}",),
    )
    connection.execute(
        """
        INSERT INTO evolution_history (action_type, action_taken)
        VALUES ('benchmark', ?)
        """,
        (f"round_{round_no}_seq_{seq_no}",),
    )
    connection.execute(
        """
        UPDATE bankroll_state
        SET current_bankroll = current_bankroll + 0.01,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """
    )
    connection.execute(
        """
        INSERT INTO bankroll_history (old_value, new_value, delta)
        VALUES (50.0, 50.01, 0.01)
        """
    )


def write_telegram_callback(connection: sqlite3.Connection, round_no: int, seq_no: int) -> None:
    connection.execute(
        """
        INSERT INTO placed_bets (detection_id, match_id, bookmaker, stake)
        VALUES (?, ?, ?, ?)
        """,
        (seq_no, f"telegram_match_{round_no}_{seq_no}", "bet365", 2.0),
    )
    connection.execute(
        """
        UPDATE bankroll_state
        SET current_bankroll = current_bankroll - 2.0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """
    )
    connection.execute(
        """
        INSERT INTO bankroll_history (old_value, new_value, delta)
        VALUES (50.0, 48.0, -2.0)
        """
    )


def make_operation(spec: WriterSpec, round_no: int, seq_no: int):
    def operation(connection: sqlite3.Connection) -> None:
        if spec.name.endswith("scraper"):
            insert_snapshot(connection, spec.name, round_no, seq_no)
        elif spec.name == "apscheduler_jobs":
            write_scheduler_state(connection, round_no, seq_no)
        elif spec.name == "telegram_callbacks":
            write_telegram_callback(connection, round_no, seq_no)
        else:
            raise ValueError(f"Unsupported writer: {spec.name}")

        # Deliberately emulate anti-pattern lock holding when requested.
        if spec.hold_ms > 0:
            time.sleep(spec.hold_ms / 1000.0)

    return operation


def run_writer(
    db_path: str,
    spec: WriterSpec,
    rounds: int,
    barrier: Barrier,
    observer: SQLiteWriteObserver,
) -> None:
    connection = connect_sqlite(db_path)
    try:
        for round_no in range(rounds):
            barrier.wait()
            for seq_no in range(spec.writes_per_round):
                measured_write_transaction(
                    connection=connection,
                    observer=observer,
                    writer_name=spec.name,
                    operation=make_operation(spec, round_no, seq_no),
                )
    finally:
        connection.close()


def run_scenario(db_path: str, writers: list[WriterSpec], rounds: int) -> dict:
    barrier = Barrier(len(writers))
    observer = SQLiteWriteObserver()
    threads = []
    start = time.perf_counter()

    for spec in writers:
        thread = Thread(
            target=run_writer,
            args=(db_path, spec, rounds, barrier, observer),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    elapsed_seconds = time.perf_counter() - start
    return observer.summary(elapsed_seconds=elapsed_seconds)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix="edgehunter-sqlite-bench-") as temp_dir:
        db_path = str(Path(temp_dir) / "benchmark.db")
        ensure_future_tables(db_path)

        disciplined = run_scenario(
            db_path=db_path,
            writers=DISCIPLINED_WRITERS,
            rounds=DISCIPLINED_ROUNDS,
        )
        antipattern = run_scenario(
            db_path=db_path,
            writers=ANTIPATTERN_WRITERS,
            rounds=1,
        )

    payload = {
        "environment": {
            "busy_timeout_ms": 5000,
            "journal_mode": "WAL",
            "disciplined_rounds": DISCIPLINED_ROUNDS,
        },
        "scenarios": {
            "disciplined_short_transactions": disciplined,
            "antipattern_long_transaction": antipattern,
        },
    }

    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
