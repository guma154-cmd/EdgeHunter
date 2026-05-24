"""Tests for the transaction discipline static checker."""

from __future__ import annotations

from scripts.check_transaction_discipline import main, scan_paths


def test_transaction_discipline_script_reports_clean_repo() -> None:
    violations = scan_paths()
    assert violations == []


def test_transaction_discipline_cli_exit_code_is_zero() -> None:
    assert main() == 0
