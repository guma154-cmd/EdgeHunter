"""Documentation consistency checks for EdgeHunter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INLINE_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PRD_ACCEPTED_PATTERNS = (
    re.compile(r"^\s*[-*]\s*\*\*Status:?\*\*:?\s*Accepted\s*$", re.IGNORECASE),
    re.compile(r"^\|\s*\*\*Status\*\*\s*\|\s*Accepted\s*\|?\s*$", re.IGNORECASE),
)
PRD_STATUS_LINE_RE = (
    re.compile(r"^\s*[-*]\s*\*\*Status:?\*\*:?\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|?\s*$", re.IGNORECASE),
)
PROHIBITED_STORY_PATTERNS = (
    ("PostgreSQL", re.compile(r"\bPostgreSQL\b", re.IGNORECASE)),
    ("pg_dump", re.compile(r"\bpg_dump\b", re.IGNORECASE)),
    ("PL/pgSQL", re.compile(r"\bPL/pgSQL\b", re.IGNORECASE)),
    ("AWS S3", re.compile(r"\bAWS S3\b", re.IGNORECASE)),
    ("MLflow", re.compile(r"\bMLflow\b", re.IGNORECASE)),
    ("pg_", re.compile(r"\bpg_[A-Za-z0-9_]*\b")),
    ("psycopg", re.compile(r"\bpsycopg\b", re.IGNORECASE)),
)
TEMPLATE_LITERAL_ARTIFACT_RE = re.compile(r"`\s*\+\s*\"`\"\s*\+\s*``")
LEGACY_PRDS_PATH_RE = re.compile(r"/?docs/prds/", re.IGNORECASE)
LEGACY_PARENT_RE = re.compile(r"00_value_betting_pivot", re.IGNORECASE)
REFERENCE_HEADING_RE = re.compile(r"^#{1,6}\s+.*refer", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\ba ser criado\b", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    line: int
    check: str
    message: str


@dataclass(frozen=True)
class CheckerPaths:
    project_root: Path
    docs_root: Path
    prd_root: Path
    stories_root: Path


def build_paths(project_root: Path = PROJECT_ROOT) -> CheckerPaths:
    docs_root = project_root / "docs"
    return CheckerPaths(
        project_root=project_root,
        docs_root=docs_root,
        prd_root=docs_root / "prd",
        stories_root=docs_root / "stories",
    )


def _relative(path: Path, project_root: Path) -> str:
    return str(path.relative_to(project_root)).replace("\\", "/")


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _markdown_paths(paths: CheckerPaths) -> list[Path]:
    markdown_paths: list[Path] = []
    readme = paths.project_root / "README.md"
    if readme.exists():
        markdown_paths.append(readme)
    if paths.docs_root.exists():
        markdown_paths.extend(sorted(paths.docs_root.rglob("*.md")))
    return markdown_paths


def _story_paths(paths: CheckerPaths) -> list[Path]:
    if not paths.stories_root.exists():
        return []
    return sorted(paths.stories_root.rglob("*.md"))


def _finding(severity: str, path: Path, line: int, check: str, message: str) -> Finding:
    return Finding(severity=severity, path=path, line=line, check=check, message=message)


def _find_missing_required_paths(paths: CheckerPaths) -> list[Finding]:
    findings: list[Finding] = []
    required = (
        (paths.docs_root, "missing_path", "required docs directory not found"),
        (paths.prd_root, "missing_path", "required docs/prd directory not found"),
        (paths.stories_root, "missing_path", "required docs/stories directory not found"),
    )
    for path, check, message in required:
        if not path.exists():
            findings.append(_finding("ERROR", path, 1, check, message))
    return findings


def _find_file_read_issues(markdown_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_paths:
        if not path.exists():
            findings.append(_finding("ERROR", path, 1, "missing_file", "markdown file not found"))
            continue
        try:
            path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
    return findings


def _find_story_stack_issues(story_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in story_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        for line_no, line in enumerate(lines, start=1):
            for label, pattern in PROHIBITED_STORY_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        _finding(
                            "ERROR",
                            path,
                            line_no,
                            "stack_validation",
                            f"prohibited story stack term found: {label}",
                        )
                    )
    return findings


def _find_prd_status_issues(prd_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in prd_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        status_line_no: int | None = None
        status_value: str | None = None
        accepted = False

        for line_no, line in enumerate(lines, start=1):
            if any(pattern.match(line) for pattern in PRD_ACCEPTED_PATTERNS):
                accepted = True
                status_line_no = line_no
                status_value = "Accepted"
                break

            for pattern in PRD_STATUS_LINE_RE:
                match = pattern.match(line)
                if match:
                    status_line_no = line_no
                    status_value = match.group(1).strip().strip("|").strip()
                    break

            if status_line_no is not None:
                break

        if not accepted:
            if status_line_no is None:
                findings.append(
                    _finding(
                        "ERROR",
                        path,
                        1,
                        "prd_status_validation",
                        "missing status line; expected Status**: Accepted",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "ERROR",
                        path,
                        status_line_no,
                        "prd_status_validation",
                        f"PRD status must be Accepted, found: {status_value.lstrip(':').strip()}",
                    )
                )
    return findings


def _resolve_link_target(raw_target: str, source_path: Path, project_root: Path) -> Path:
    target = raw_target.split("#", 1)[0]
    if target.startswith("/"):
        return project_root / target.lstrip("/")
    return (source_path.parent / target).resolve()


def _find_link_issues(markdown_paths: Iterable[Path], project_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        for line_no, line in enumerate(lines, start=1):
            for match in INLINE_LINK_RE.finditer(line):
                raw_target = match.group(1).strip()
                if not raw_target or raw_target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if LEGACY_PARENT_RE.search(raw_target):
                    findings.append(
                        _finding(
                            "ERROR",
                            path,
                            line_no,
                            "link_validation",
                            f"legacy link target referenced: {raw_target}",
                        )
                    )
                    continue

                resolved = _resolve_link_target(raw_target, path, project_root)
                if not resolved.exists():
                    findings.append(
                        _finding(
                            "ERROR",
                            path,
                            line_no,
                            "link_validation",
                            f"broken markdown link target: {raw_target}",
                        )
                    )
    return findings


def _find_markdown_fence_issues(markdown_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        for line_no, line in enumerate(lines, start=1):
            if TEMPLATE_LITERAL_ARTIFACT_RE.search(line):
                findings.append(
                    _finding(
                        "ERROR",
                        path,
                        line_no,
                        "markdown_fence_validation",
                        "template-literal markdown fence artifact found",
                    )
                )
    return findings


def _find_legacy_docs_prds_issues(markdown_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        for line_no, line in enumerate(lines, start=1):
            if LEGACY_PRDS_PATH_RE.search(line):
                findings.append(
                    _finding(
                        "ERROR",
                        path,
                        line_no,
                        "cross_reference_validation",
                        "legacy docs/prds/ path still referenced",
                    )
                )
    return findings


def _find_placeholder_reference_issues(markdown_paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_paths:
        try:
            lines = _read_lines(path)
        except OSError as exc:
            findings.append(_finding("ERROR", path, 1, "read_error", f"unable to read file: {exc}"))
            continue

        in_reference_section = False
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                in_reference_section = bool(REFERENCE_HEADING_RE.match(stripped))
                continue
            if in_reference_section and PLACEHOLDER_RE.search(line):
                findings.append(
                    _finding(
                        "ERROR",
                        path,
                        line_no,
                        "cross_reference_validation",
                        "placeholder 'a ser criado' found inside references section",
                    )
                )
    return findings


def collect_findings(project_root: Path = PROJECT_ROOT) -> list[Finding]:
    paths = build_paths(project_root)
    markdown_paths = _markdown_paths(paths)

    findings: list[Finding] = []
    findings.extend(_find_missing_required_paths(paths))
    findings.extend(_find_file_read_issues(markdown_paths))
    findings.extend(_find_story_stack_issues(_story_paths(paths)))
    findings.extend(_find_prd_status_issues(sorted(paths.prd_root.glob("*.md"))))
    findings.extend(_find_link_issues(markdown_paths, paths.project_root))
    findings.extend(_find_markdown_fence_issues(markdown_paths))
    findings.extend(_find_legacy_docs_prds_issues(markdown_paths))
    findings.extend(_find_placeholder_reference_issues(markdown_paths))
    return sorted(findings, key=lambda item: (_relative(item.path, paths.project_root), item.line, item.check, item.message))


def format_finding(finding: Finding, project_root: Path = PROJECT_ROOT) -> str:
    return (
        f"{finding.severity} "
        f"{_relative(finding.path, project_root)}:{finding.line} "
        f"[{finding.check}] {finding.message}"
    )


def main() -> int:
    try:
        findings = collect_findings()
    except Exception as exc:  # pragma: no cover - defensive CLI fallback
        print(f"ERROR scripts/check_doc_consistency.py:1 [runtime] unexpected failure: {exc}")
        return 1

    for finding in findings:
        print(format_finding(finding))

    error_count = sum(1 for finding in findings if finding.severity == "ERROR")
    print(f"Summary: {error_count} error(s), {len(findings)} total finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
