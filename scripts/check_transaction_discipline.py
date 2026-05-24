"""Static checks for SQLite transaction discipline in EdgeHunter."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEDULER_PATH = PROJECT_ROOT / "backend" / "app" / "data" / "scheduler.py"
AUTOTUNER_PATH = PROJECT_ROOT / "backend" / "app" / "engine" / "autotuner.py"

FORBIDDEN_CALLS = {"send_message", "send_surebet_alert", "post"}
SHORT_TX_FUNCTIONS = {
    SCHEDULER_PATH: (
        "_persist_confirmed_opportunities",
        "_mark_surebet_alert_sent",
    ),
    AUTOTUNER_PATH: ("_log_experiment",),
}
ASYNC_ENTRYPOINT_GUARDS = {
    SCHEDULER_PATH: {
        "_fetch_odds_task": {"send_surebet_alert"},
    }
}


@dataclass(frozen=True)
class Violation:
    path: Path
    function_name: str
    message: str


def _function_calls(node: ast.FunctionDef) -> set[str]:
    return {
        ast.unparse(call.func).split(".")[-1]
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
    }


def _decorator_names(node: ast.FunctionDef) -> list[str]:
    return [ast.unparse(decorator) for decorator in node.decorator_list]


def scan_file(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    violations: list[Violation] = []

    for function_name in SHORT_TX_FUNCTIONS.get(path, ()):
        function = functions.get(function_name)
        if function is None:
            violations.append(Violation(path, function_name, "function not found"))
            continue

        decorators = _decorator_names(function)
        if not any(decorator.startswith("SHORT_TX") for decorator in decorators):
            violations.append(
                Violation(path, function_name, "missing SHORT_TX decorator")
            )

        calls = _function_calls(function)
        forbidden_hits = sorted(calls.intersection(FORBIDDEN_CALLS))
        if forbidden_hits:
            violations.append(
                Violation(
                    path,
                    function_name,
                    f"forbidden network-adjacent calls inside SHORT_TX: {', '.join(forbidden_hits)}",
                )
            )

    for function_name, forbidden_calls in ASYNC_ENTRYPOINT_GUARDS.get(path, {}).items():
        function = functions.get(function_name)
        if function is None:
            violations.append(Violation(path, function_name, "function not found"))
            continue

        calls = _function_calls(function)
        direct_hits = sorted(calls.intersection(forbidden_calls))
        if direct_hits:
            violations.append(
                Violation(
                    path,
                    function_name,
                    f"direct call bypasses async boundary: {', '.join(direct_hits)}",
                )
            )

    return violations


def scan_paths(paths: Iterable[Path] | None = None) -> list[Violation]:
    targets = tuple(paths or SHORT_TX_FUNCTIONS.keys())
    violations: list[Violation] = []
    for path in targets:
        violations.extend(scan_file(path))
    return violations


def main() -> int:
    violations = scan_paths()
    if not violations:
        print("transaction-discipline: ok")
        return 0

    for violation in violations:
        relative_path = violation.path.relative_to(PROJECT_ROOT)
        print(f"{relative_path}:{violation.function_name}: {violation.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
