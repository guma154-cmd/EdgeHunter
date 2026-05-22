"""Documentation consistency checks for EdgeHunter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"
ARCHITECTURE_ROOT = DOCS_ROOT / "architecture"
PRD_ROOT = DOCS_ROOT / "prd"
STORIES_ROOT = DOCS_ROOT / "stories"

MARKDOWN_PATHS = [
    PROJECT_ROOT / "README.md",
    DOCS_ROOT / "_index" / "PRDS_INDEX.md",
    DOCS_ROOT / "_index" / "ADRS_INDEX.md",
    *sorted(DOCS_ROOT.rglob("*.md")),
]
STORY_FILE_GLOB = "STORY-*.md"

INLINE_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
STORY_TOTAL_RE = re.compile(
    r"Total de stories(?:\s*\*+)?\s*[:|]\s*\**\s*(\d+)",
    re.IGNORECASE,
)
LEGACY_ADR_RE = re.compile(r"(ADR-\d{3}).*a ser criado", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    message: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _find_inline_link_issues(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in INLINE_LINK_RE.finditer(text):
        raw_target = match.group(1).strip()
        if not raw_target or raw_target.startswith(("http://", "https://", "mailto:", "#")):
            continue

        target = raw_target.split("#", 1)[0]
        if not target:
            continue

        if target.startswith("/"):
            resolved = PROJECT_ROOT / target.lstrip("/")
        else:
            resolved = (path.parent / target).resolve()

        if not resolved.exists():
            findings.append(
                Finding(
                    "ERROR",
                    path,
                    f"broken markdown link target: {raw_target}",
                )
            )
    return findings


def _find_legacy_path_issues(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    if "/docs/prds/" in text or "docs/prds/" in text:
        findings.append(Finding("ERROR", path, "legacy docs/prds path still referenced"))
    return findings


def _parse_story_total(path: Path) -> int | None:
    text = _read_text(path)
    for match in STORY_TOTAL_RE.finditer(text):
        return int(match.group(1))
    return None


def _find_story_count_issues() -> list[Finding]:
    findings: list[Finding] = []
    detailed = STORIES_ROOT / "stories_detalhadas.md"

    detailed_total = _parse_story_total(detailed)
    actual_story_files = len(list(STORIES_ROOT.rglob(STORY_FILE_GLOB)))

    if detailed_total is not None and detailed_total != actual_story_files:
        findings.append(
            Finding(
                "ERROR",
                detailed,
                f"story count mismatch: detailed={detailed_total}, actual_story_files={actual_story_files}",
            )
        )

    return findings


def _find_database_drift_issues() -> list[Finding]:
    findings: list[Finding] = []
    stories_detailed = STORIES_ROOT / "stories_detalhadas.md"
    text = _read_text(stories_detailed)

    sqlite_decided = "Chosen option" in _read_text(ARCHITECTURE_ROOT / "adr_004_database_choice.md")
    postgres_markers = ("PostgreSQL", "pg_dump", "PL/pgSQL")
    if sqlite_decided and any(marker in text for marker in postgres_markers):
        findings.append(
            Finding(
                "ERROR",
                stories_detailed,
                "stories_detalhadas still describes PostgreSQL-specific implementation despite SQLite ADR",
            )
        )
    return findings


def _find_stale_adr_placeholder_issues(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    existing_adrs = {path.stem.lower() for path in ARCHITECTURE_ROOT.glob("adr_*.md")}

    for path in paths:
        text = _read_text(path)
        for match in LEGACY_ADR_RE.finditer(text):
            adr_code = match.group(1).lower().replace("-", "_")
            adr_stem = f"{adr_code}"
            if adr_stem in existing_adrs:
                findings.append(
                    Finding(
                        "ERROR",
                        path,
                        f"stale placeholder says '{match.group(1)}' is 'a ser criado', but the ADR file exists",
                    )
                )
    return findings


def _find_draft_status_warnings(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        text = _read_text(path)
        if re.search(r"\b(Status|Status:)\b.*\b(Draft|Rascunho)\b", text, re.IGNORECASE):
            findings.append(Finding("WARN", path, "document status still Draft/Rascunho"))
    return findings


def collect_findings() -> list[Finding]:
    findings: list[Finding] = []
    for path in MARKDOWN_PATHS:
        text = _read_text(path)
        findings.extend(_find_inline_link_issues(path, text))
        findings.extend(_find_legacy_path_issues(path, text))

    findings.extend(_find_story_count_issues())
    findings.extend(_find_database_drift_issues())
    findings.extend(_find_stale_adr_placeholder_issues(MARKDOWN_PATHS))
    findings.extend(
        _find_draft_status_warnings(
            [
                *PRD_ROOT.glob("*.md"),
                DOCS_ROOT / "_index" / "PRDS_INDEX.md",
                DOCS_ROOT / "_index" / "ADRS_INDEX.md",
            ]
        )
    )
    return findings


def main() -> int:
    findings = collect_findings()
    error_count = 0
    warn_count = 0

    for finding in findings:
        if finding.severity == "ERROR":
            error_count += 1
        elif finding.severity == "WARN":
            warn_count += 1
        print(f"{finding.severity} {_relative(finding.path)}: {finding.message}")

    print(f"Summary: {error_count} error(s), {warn_count} warning(s)")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
