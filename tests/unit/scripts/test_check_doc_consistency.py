"""Tests for the documentation consistency checker."""

from __future__ import annotations

import runpy
from pathlib import Path

from scripts import check_doc_consistency


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_clean_project(tmp_path: Path) -> Path:
    _write(tmp_path / "README.md", "# README\n")
    _write(
        tmp_path / "docs" / "prd" / "01_sample.md",
        "\n".join(
            [
                "# Sample PRD",
                "",
                "## Metadata",
                "- **Status**: Accepted",
                "",
                "## Referencias",
                "- [ADR](../architecture/adr_001_sample.md)",
            ]
        ),
    )
    _write(
        tmp_path / "docs" / "architecture" / "adr_001_sample.md",
        "\n".join(
            [
                "# Sample ADR",
                "",
                "## Referencias",
                "- [PRD](../prd/01_sample.md)",
            ]
        ),
    )
    _write(tmp_path / "docs" / "stories" / "story.md", "# Story limpa\n")
    return tmp_path


def test_doc_consistency_reports_clean_project(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)

    findings = check_doc_consistency.collect_findings(project_root)

    assert findings == []
    assert check_doc_consistency.collect_findings(project_root) == []


def test_stack_validation_flags_prohibited_story_term(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(project_root / "docs" / "stories" / "story.md", "Banco alvo: PostgreSQL\n")

    findings = check_doc_consistency.collect_findings(project_root)

    assert any(
        finding.check == "stack_validation" and "PostgreSQL" in finding.message
        for finding in findings
    )


def test_prd_status_validation_flags_non_accepted_status(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(
        project_root / "docs" / "prd" / "01_sample.md",
        "# Sample PRD\n\n- **Status**: Draft\n",
    )

    findings = check_doc_consistency.collect_findings(project_root)

    assert any(
        finding.check == "prd_status_validation" and "must be Accepted" in finding.message
        for finding in findings
    )


def test_link_validation_flags_missing_target(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(
        project_root / "README.md",
        "\n".join(
            [
                "# README",
                "[bad](./missing.md)",
            ]
        ),
    )

    findings = check_doc_consistency.collect_findings(project_root)

    assert any("broken markdown link target" in finding.message for finding in findings)


def test_link_validation_flags_legacy_parent_reference(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(
        project_root / "README.md",
        "\n".join(
            [
                "# README",
                "[legacy](docs/prd/00_value_betting_pivot.md)",
            ]
        ),
    )

    findings = check_doc_consistency.collect_findings(project_root)

    assert any("legacy link target referenced" in finding.message for finding in findings)


def test_markdown_fence_validation_flags_template_literal_artifact(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(project_root / "docs" / "architecture" / "adr_001_sample.md", '` + "`" + ``\n')

    findings = check_doc_consistency.collect_findings(project_root)

    assert any(
        finding.check == "markdown_fence_validation"
        for finding in findings
    )


def test_cross_reference_validation_flags_legacy_path_and_placeholder(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(
        project_root / "README.md",
        "Use docs/prds/sample.md\n",
    )
    _write(
        project_root / "docs" / "architecture" / "adr_001_sample.md",
        "\n".join(
            [
                "# ADR",
                "",
                "## Referencias",
                "- Documento auxiliar a ser criado",
            ]
        ),
    )

    findings = check_doc_consistency.collect_findings(project_root)

    assert any(
        finding.check == "cross_reference_validation"
        and "docs/prds" in finding.message
        for finding in findings
    )
    assert any(
        finding.check == "cross_reference_validation"
        and "a ser criado" in finding.message
        for finding in findings
    )


def test_all_problems_at_once_returns_findings_without_crashing(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(project_root / "docs" / "stories" / "story.md", "PostgreSQL\n")
    _write(project_root / "docs" / "prd" / "01_sample.md", "# Sample PRD\n\nSem status\n")
    _write(
        project_root / "README.md",
        "\n".join(
            [
                "Use docs/prds/sample.md",
                "[bad](./missing.md)",
                "[legacy](docs/prd/00_value_betting_pivot.md)",
                '` + "`" + ``',
            ]
        ),
    )
    _write(
        project_root / "docs" / "architecture" / "adr_001_sample.md",
        "\n".join(
            [
                "# ADR",
                "",
                "## Referencias",
                "- Documento auxiliar a ser criado",
            ]
        ),
    )

    findings = check_doc_consistency.collect_findings(project_root)

    checks = {finding.check for finding in findings}
    assert "stack_validation" in checks
    assert "prd_status_validation" in checks
    assert "link_validation" in checks
    assert "markdown_fence_validation" in checks
    assert "cross_reference_validation" in checks


def test_empty_project_returns_clear_missing_path_errors(tmp_path: Path) -> None:
    findings = check_doc_consistency.collect_findings(tmp_path)

    assert len(findings) == 3
    assert all(finding.check == "missing_path" for finding in findings)
    assert {finding.line for finding in findings} == {1}


def test_format_finding_includes_file_line_and_check(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    finding = check_doc_consistency.Finding(
        severity="ERROR",
        path=project_root / "README.md",
        line=7,
        check="sample_check",
        message="sample message",
    )

    formatted = check_doc_consistency.format_finding(finding, project_root)

    assert formatted == "ERROR README.md:7 [sample_check] sample message"


def test_main_returns_zero_when_no_findings(monkeypatch) -> None:
    monkeypatch.setattr(check_doc_consistency, "collect_findings", lambda project_root=check_doc_consistency.PROJECT_ROOT: [])

    assert check_doc_consistency.main() == 0


def test_main_returns_one_when_findings_exist(monkeypatch, tmp_path: Path) -> None:
    finding = check_doc_consistency.Finding(
        severity="ERROR",
        path=check_doc_consistency.PROJECT_ROOT / "README.md",
        line=3,
        check="sample_check",
        message="sample message",
    )
    monkeypatch.setattr(
        check_doc_consistency,
        "collect_findings",
        lambda project_root=check_doc_consistency.PROJECT_ROOT: [finding],
    )

    assert check_doc_consistency.main() == 1


def test_file_read_issue_reports_missing_file() -> None:
    missing = Path("C:/missing/doc.md")

    findings = check_doc_consistency._find_file_read_issues([missing])

    assert len(findings) == 1
    assert findings[0].check == "missing_file"


def test_file_read_issue_reports_oserror(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("# README\n", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", lambda self, encoding="utf-8": (_ for _ in ()).throw(OSError("boom")))

    findings = check_doc_consistency._find_file_read_issues([path])

    assert len(findings) == 1
    assert findings[0].check == "read_error"


def test_story_paths_returns_empty_when_directory_missing(tmp_path: Path) -> None:
    paths = check_doc_consistency.build_paths(tmp_path)

    assert check_doc_consistency._story_paths(paths) == []


def test_prd_status_validation_reports_missing_status_line(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(project_root / "docs" / "prd" / "01_sample.md", "# Sample PRD\n\nSem status\n")

    findings = check_doc_consistency.collect_findings(project_root)

    assert any("missing status line" in finding.message for finding in findings)


def test_link_validation_ignores_external_and_anchor_links(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(
        project_root / "README.md",
        "\n".join(
            [
                "[http](https://example.com)",
                "[mail](mailto:test@example.com)",
                "[anchor](#section)",
            ]
        ),
    )

    findings = check_doc_consistency.collect_findings(project_root)

    assert findings == []


def test_link_validation_supports_absolute_project_links(tmp_path: Path) -> None:
    project_root = _build_clean_project(tmp_path)
    _write(project_root / "README.md", "[abs](/docs/prd/01_sample.md)\n")

    findings = check_doc_consistency.collect_findings(project_root)

    assert findings == []


def test_read_error_branches_are_reported_for_all_scanners(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text("content\n", encoding="utf-8")
    monkeypatch.setattr(check_doc_consistency, "_read_lines", lambda target: (_ for _ in ()).throw(OSError("boom")))

    scanners = (
        check_doc_consistency._find_story_stack_issues([path]),
        check_doc_consistency._find_prd_status_issues([path]),
        check_doc_consistency._find_link_issues([path], tmp_path),
        check_doc_consistency._find_markdown_fence_issues([path]),
        check_doc_consistency._find_legacy_docs_prds_issues([path]),
        check_doc_consistency._find_placeholder_reference_issues([path]),
    )

    for findings in scanners:
        assert len(findings) == 1
        assert findings[0].check == "read_error"


def test_main_returns_one_on_unexpected_runtime_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        check_doc_consistency,
        "collect_findings",
        lambda project_root=check_doc_consistency.PROJECT_ROOT: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    assert check_doc_consistency.main() == 1


def test_module_entrypoint_executes_without_error() -> None:
    try:
        runpy.run_path(str(Path(check_doc_consistency.__file__)), run_name="__main__")
    except SystemExit as exc:
        assert exc.code in (0, 1)
