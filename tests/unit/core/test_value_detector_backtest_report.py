"""Tests for STORY-04A-005 local paper trading backtest reports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect

import pytest

from src.edgehunter.core import value_detector_backtest as backtest_module
from src.edgehunter.core.value_detector_backtest import (
    BacktestMetrics,
    BacktestRunResult,
    BacktestSelectionResult,
    generate_paper_trading_report,
)


NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _selection(**overrides: object) -> BacktestSelectionResult:
    data: dict[str, object] = {
        "match_id": "match-001",
        "market": "1x2",
        "selection": "home",
        "source": "pinnacle_benchmark",
        "detection_method": "pinnacle_ev_v1",
        "predicted_probability": 0.60,
        "offered_odds": 2.0,
        "expected_value": 0.20,
        "edge_percentage": 20.0,
        "actual_result": "home_win",
        "is_hit": True,
        "is_false_positive": False,
        "evaluated_at": NOW,
    }
    data.update(overrides)
    return BacktestSelectionResult(**data)


def _metrics() -> BacktestMetrics:
    return BacktestMetrics(
        total_analyzed=3,
        total_opportunities=2,
        total_hits=1,
        total_false_positives=1,
        hit_rate=0.5,
        false_positive_rate=0.5,
        coverage_rate=2 / 3,
        average_expected_value=0.15,
        average_edge_percentage=15.0,
        by_source={
            "pinnacle_benchmark": {
                "total_opportunities": 2,
                "total_hits": 1,
                "total_false_positives": 1,
                "hit_rate": 0.5,
                "false_positive_rate": 0.5,
                "average_expected_value": 0.15,
                "average_edge_percentage": 15.0,
            },
        },
        by_detection_method={
            "pinnacle_ev_v1": {
                "total_opportunities": 2,
                "total_hits": 1,
                "total_false_positives": 1,
                "hit_rate": 0.5,
                "false_positive_rate": 0.5,
                "average_expected_value": 0.15,
                "average_edge_percentage": 15.0,
            },
        },
    )


def _run_result(selection_count: int = 2) -> BacktestRunResult:
    selections = [
        _selection(
            match_id=f"match-{index:03d}",
            is_hit=index % 2 == 0,
            is_false_positive=index % 2 == 1,
            actual_result="home_win" if index % 2 == 0 else "away_win",
            expected_value=0.10 + index / 100,
            edge_percentage=10.0 + index,
        )
        for index in range(selection_count)
    ]
    return BacktestRunResult(
        run_id="run-001",
        started_at=NOW - timedelta(minutes=5),
        finished_at=NOW,
        metrics=_metrics(),
        selections=selections,
        warnings=("synthetic_fixture",),
        reasons=("quality_check",),
    )


def test_generates_valid_dict_report() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["run_id"] == "run-001"
    assert report["started_at"] == "2026-05-31T11:55:00+00:00"
    assert report["finished_at"] == "2026-05-31T12:00:00+00:00"
    assert report["status"] == {
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
    }


def test_generates_valid_markdown_report() -> None:
    report = generate_paper_trading_report(_run_result(), format="markdown")

    assert isinstance(report, str)
    assert "# Relatorio local de paper trading" in report
    assert "Run ID: run-001" in report
    assert "Total analisado: 3" in report
    assert "pinnacle_benchmark" in report


def test_unknown_format_fails_clearly() -> None:
    with pytest.raises(ValueError, match="unsupported report format"):
        generate_paper_trading_report(_run_result(), format="html")


def test_invalid_object_fails_clearly() -> None:
    with pytest.raises(ValueError, match="result must be a BacktestRunResult"):
        generate_paper_trading_report(object())


def test_report_includes_main_metrics() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")
    metrics = report["metrics"]

    assert metrics["total_analyzed"] == 3
    assert metrics["total_opportunities"] == 2
    assert metrics["total_hits"] == 1
    assert metrics["total_false_positives"] == 1
    assert metrics["hit_rate"] == pytest.approx(0.5)
    assert metrics["false_positive_rate"] == pytest.approx(0.5)
    assert metrics["coverage_rate"] == pytest.approx(2 / 3)
    assert metrics["average_expected_value"] == pytest.approx(0.15)
    assert metrics["average_edge_percentage"] == pytest.approx(15.0)


def test_report_includes_grouping_by_source() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["by_source"] == report["metrics"]["by_source"]
    assert report["by_source"]["pinnacle_benchmark"]["total_opportunities"] == 2


def test_report_includes_grouping_by_detection_method() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["by_detection_method"] == report["metrics"]["by_detection_method"]
    assert report["by_detection_method"]["pinnacle_ev_v1"]["total_hits"] == 1


def test_report_includes_warnings_and_reasons() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["warnings"] == ["synthetic_fixture"]
    assert report["reasons"] == ["quality_check"]


def test_report_includes_paper_trading_declaration() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["safety"]["paper_trading"] == "paper trading local"
    assert report["safety"]["simulation"] == "simulacao tecnica"


def test_report_includes_no_operational_recommendation_declaration() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["safety"]["not_operational_recommendation"] == (
        "nao e recomendacao operacional"
    )
    assert report["safety"]["no_real_operation"] == "nao autoriza operacao real"


def test_report_includes_security_flags() -> None:
    report = generate_paper_trading_report(_run_result(), format="dict")

    assert report["is_simulated"] is True
    assert report["paper_trading"] is True
    assert report["actionable"] is False
    assert report["selection_sample"][0]["is_simulated"] is True
    assert report["selection_sample"][0]["paper_trading"] is True
    assert report["selection_sample"][0]["actionable"] is False
    assert report["selection_sample"][0]["bet_placed"] is False
    assert report["selection_sample"][0]["alerted"] is False


def test_selection_sample_is_limited() -> None:
    report = generate_paper_trading_report(_run_result(selection_count=8), format="dict")

    assert report["selection_sample_limit"] == 5
    assert report["total_selections"] == 8
    assert len(report["selection_sample"]) == 5
    assert [item["match_id"] for item in report["selection_sample"]] == [
        "match-000",
        "match-001",
        "match-002",
        "match-003",
        "match-004",
    ]


def test_output_is_deterministic() -> None:
    result = _run_result(selection_count=3)

    assert generate_paper_trading_report(result, format="dict") == (
        generate_paper_trading_report(result, format="dict")
    )
    assert generate_paper_trading_report(result, format="markdown") == (
        generate_paper_trading_report(result, format="markdown")
    )


def test_report_output_avoids_position_sizing_terms() -> None:
    report = generate_paper_trading_report(_run_result(), format="markdown").lower()

    assert "sta" + "ke" not in report
    assert "kel" + "ly" not in report
    assert "bank" + "roll" not in report


def test_report_module_does_not_access_sqlite_or_persist_files() -> None:
    source = inspect.getsource(backtest_module)

    assert "sqlite3" not in source
    assert "get_backtest_dataset" not in source
    assert "db_path" not in source
    assert "open(" not in source
    assert "Path(" not in source


def test_report_module_does_not_use_network_message_or_timing_services() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "tele" + "gram",
        "sched" + "uler",
    ):
        assert forbidden not in source


def test_report_module_does_not_implement_public_interface_or_execution() -> None:
    source = inspect.getsource(backtest_module).lower()

    for forbidden in (
        "fastapi",
        "flask",
        "endpoint",
        "route",
        "sta" + "ke",
        "kel" + "ly",
        "bank" + "roll",
        "place_" + "bet",
        "execute_" + "bet",
        "real_" + "money",
    ):
        assert forbidden not in source
