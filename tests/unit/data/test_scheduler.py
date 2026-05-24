"""Tests for scheduler transaction discipline refactor."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys
import time
import uuid


SCHEDULER_PATH = Path(__file__).resolve().parents[3] / "backend" / "app" / "data" / "scheduler.py"


def _load_scheduler_module():
    """Import scheduler.py without importing the Flask app package."""
    # Fake apscheduler modules expected by scheduler.py
    background = ModuleType("apscheduler.schedulers.background")
    interval = ModuleType("apscheduler.triggers.interval")
    cron = ModuleType("apscheduler.triggers.cron")

    class FakeBackgroundScheduler:
        def __init__(self, timezone=None):
            self.timezone = timezone
            self.jobs = []

        def add_job(self, *args, **kwargs):
            self.jobs.append((args, kwargs))

        def start(self):
            return None

        def get_jobs(self):
            return self.jobs

    class FakeIntervalTrigger:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class FakeCronTrigger:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    background.BackgroundScheduler = FakeBackgroundScheduler
    interval.IntervalTrigger = FakeIntervalTrigger
    cron.CronTrigger = FakeCronTrigger

    sys.modules["apscheduler.schedulers.background"] = background
    sys.modules["apscheduler.triggers.interval"] = interval
    sys.modules["apscheduler.triggers.cron"] = cron

    module_name = f"scheduler_under_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, SCHEDULER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeApp:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    @contextmanager
    def app_context(self):
        yield self


def test_fetch_odds_task_defers_telegram_and_returns_quickly(monkeypatch) -> None:
    scheduler = _load_scheduler_module()

    fake_flask = ModuleType("flask")
    fake_flask.current_app = SimpleNamespace(config={})
    sys.modules["flask"] = fake_flask

    fake_detector_module = ModuleType("app.detection.surebet_detector")

    class FakeDetector:
        def detect(self, _game_data):
            return [{
                "home_team": "A",
                "away_team": "B",
                "league": "League",
                "match_date": "2026-05-21 12:00:00",
                "bookmaker_A": "bet365",
                "bookmaker_B": "betano",
                "outcome_A": "home",
                "outcome_B": "away",
                "odds_A": 2.0,
                "odds_B": 2.1,
                "stake_A": 10.0,
                "stake_B": 10.0,
                "total_stake": 20.0,
                "profit_pct": 2.0,
                "guaranteed_profit": 0.4,
            }]

    fake_detector_module.SurebetDetector = FakeDetector
    sys.modules["app.detection.surebet_detector"] = fake_detector_module

    fake_bankroll_module = ModuleType("app.engine.bankroll_manager")

    class FakeBankrollManager:
        def can_cover(self, *args, **kwargs):
            return True

        def update(self, *args, **kwargs):
            return None

    fake_bankroll_module.BankrollManager = FakeBankrollManager
    sys.modules["app.engine.bankroll_manager"] = fake_bankroll_module

    fake_direct = ModuleType("app.data.direct_scrapers")
    fake_direct.fetch_direct_sync = lambda: [{"home_team": "A", "away_team": "B", "all_odds": {"bet365": {}, "betano": {}}}]
    sys.modules["app.data.direct_scrapers"] = fake_direct

    fake_b365 = ModuleType("app.data.bet365_scraper")
    fake_b365.fetch_bet365_sync = lambda: []
    sys.modules["app.data.bet365_scraper"] = fake_b365

    enqueued = []
    monkeypatch.setattr(
        scheduler,
        "_persist_confirmed_opportunities",
        lambda confirmed_opportunities, bankroll_manager: [(11, confirmed_opportunities[0])],
    )
    monkeypatch.setattr(
        scheduler,
        "_enqueue_surebet_alert",
        lambda app, surebet_id, opportunity: enqueued.append((surebet_id, opportunity)),
    )

    app = _FakeApp(config={})
    started = time.perf_counter()
    scheduler._fetch_odds_task(app)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert elapsed_ms < 50.0
    assert len(enqueued) == 1
    assert enqueued[0][0] == 11


def test_enqueue_surebet_alert_uses_scheduler_job(monkeypatch) -> None:
    scheduler = _load_scheduler_module()

    captured = {}

    class FakeScheduler:
        def add_job(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(scheduler, "get_scheduler", lambda: FakeScheduler())
    scheduler._enqueue_surebet_alert(_FakeApp(), 7, {"home_team": "A"})

    assert captured["func"] is scheduler._send_telegram_alert
    assert captured["args"][1] == 7
    assert captured["trigger"] == "date"


def test_send_telegram_alert_failure_does_not_mark_alert(monkeypatch) -> None:
    scheduler = _load_scheduler_module()

    fake_session = _FakeSession()
    fake_app_module = ModuleType("app")
    fake_app_module.db = SimpleNamespace(session=fake_session)
    sys.modules["app"] = fake_app_module

    fake_telegram = ModuleType("app.alerts.telegram_bot")
    fake_telegram.send_surebet_alert = lambda opportunity: False
    sys.modules["app.alerts.telegram_bot"] = fake_telegram

    mark_calls = []
    monkeypatch.setattr(scheduler, "_mark_surebet_alert_sent", lambda surebet_id: mark_calls.append(surebet_id))

    result = scheduler._send_telegram_alert(_FakeApp(), 9, {"home_team": "A"})

    assert result is False
    assert mark_calls == []
    assert fake_session.rollback_calls == 0

